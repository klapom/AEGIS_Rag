"""4-Way Hybrid Retrieval with Intent-Weighted RRF.

Sprint 42 - Feature: 4-Way Hybrid RRF (TD-057)

This module implements a 4-channel hybrid retrieval system:
1. Vector (Qdrant): Semantic similarity search
2. BM25: Keyword matching search
3. Graph Local: Entity → Chunk expansion (MENTIONED_IN relationships)
4. Graph Global: Community → Entity → Chunk expansion

Each channel is weighted based on the classified query intent:
- factual: High local, balanced vector/bm25, no global
- keyword: High bm25, medium local, low vector
- exploratory: Balanced with emphasis on global
- summary: High global, low others

Academic References:
- GraphRAG (Edge et al., 2024) - arXiv:2404.16130
- LightRAG (Guo et al., EMNLP 2025) - arXiv:2410.05779
- HybridRAG (2024) - arXiv:2408.04948
- Adaptive-RAG (Jeong et al., NAACL 2024) - arXiv:2403.14403
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import structlog
from qdrant_client.models import FieldCondition, Filter, MatchAny

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.components.retrieval.filters import MetadataFilters
from src.components.retrieval.intent_classifier import (
    Intent,
    IntentClassificationResult,
    classify_intent,
)
from src.components.vector_search.hybrid_search import HybridSearch
from src.core.namespace import DEFAULT_NAMESPACE
from src.utils.fusion import weighted_reciprocal_rank_fusion

logger = structlog.get_logger(__name__)


@dataclass
class FourWaySearchMetadata:
    """Metadata from 4-Way Hybrid Search execution."""

    vector_results_count: int
    bm25_results_count: int
    graph_local_results_count: int
    graph_global_results_count: int
    intent: str
    intent_confidence: float
    intent_method: str
    intent_latency_ms: float
    weights: dict[str, float]
    total_latency_ms: float
    channels_executed: list[str]
    namespaces_searched: list[str]


class FourWayHybridSearch:
    """4-Way Hybrid Retrieval with Intent-Weighted RRF.

    This engine combines four retrieval channels:
    1. Vector Search (Qdrant) - Semantic similarity
    2. BM25 Search - Keyword matching
    3. Graph Local - Entity facts (MENTIONED_IN relationships)
    4. Graph Global - Community/theme context

    The weights for each channel are dynamically determined by
    classifying the query intent (factual, keyword, exploratory, summary).

    Example:
        search = FourWayHybridSearch()
        results = await search.search("What is the project architecture?", top_k=10)
        # Results are ranked using intent-weighted RRF
    """

    def __init__(
        self,
        hybrid_search: HybridSearch | None = None,
        neo4j_client: Neo4jClient | None = None,
        rrf_k: int = 60,
    ):
        """Initialize 4-Way Hybrid Search.

        Args:
            hybrid_search: Existing HybridSearch instance (for Vector + BM25)
            neo4j_client: Neo4j client for graph queries
            rrf_k: RRF constant (default: 60)
        """
        self.hybrid_search = hybrid_search or HybridSearch()
        self.neo4j_client = neo4j_client or Neo4jClient()
        self.rrf_k = rrf_k

        logger.info(
            "FourWayHybridSearch initialized",
            rrf_k=rrf_k,
        )

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: MetadataFilters | None = None,
        use_reranking: bool = False,
        intent_override: Intent | None = None,
        allowed_namespaces: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute 4-Way Hybrid Search with Intent-Weighted RRF.

        Args:
            query: User query string
            top_k: Number of final results to return
            filters: Metadata filters (applied to vector search only)
            use_reranking: Whether to apply cross-encoder reranking
            intent_override: Force specific intent (bypass classifier)
            allowed_namespaces: List of namespaces to search in. If None, defaults to ["default", "general"]

        Returns:
            Dictionary with results and metadata:
            {
                "query": str,
                "results": list[dict],
                "intent": str,
                "weights": dict,
                "metadata": FourWaySearchMetadata
            }
        """
        start_time = time.perf_counter()

        # Step 0: Resolve namespaces (default to ["default", "general"] if not provided)
        if allowed_namespaces is None:
            allowed_namespaces = [DEFAULT_NAMESPACE, "general"]

        logger.debug(
            "four_way_search_namespaces",
            query=query[:50],
            namespaces=allowed_namespaces,
        )

        # Step 1: Classify query intent (or use override)
        if intent_override:
            from src.components.retrieval.intent_classifier import INTENT_WEIGHT_PROFILES

            intent_result = IntentClassificationResult(
                intent=intent_override,
                weights=INTENT_WEIGHT_PROFILES[intent_override],
                confidence=1.0,
                latency_ms=0.0,
                method="override",
            )
        else:
            intent_result = await classify_intent(query)

        intent = intent_result.intent
        weights = intent_result.weights

        logger.info(
            "four_way_search_intent_classified",
            query=query[:50],
            intent=intent.value,
            confidence=intent_result.confidence,
            weights={
                "vector": weights.vector,
                "bm25": weights.bm25,
                "local": weights.local,
                "global": weights.global_,
            },
        )

        # Step 2: Execute all 4 channels in parallel
        # Only execute channels with non-zero weights
        tasks = []
        channels_executed = []

        # Vector search (always execute if weight > 0)
        if weights.vector > 0:
            tasks.append(self._vector_search(query, top_k * 3, filters, allowed_namespaces))
            channels_executed.append("vector")

        # BM25 search (always execute if weight > 0)
        if weights.bm25 > 0:
            tasks.append(self._bm25_search(query, top_k * 3, allowed_namespaces))
            channels_executed.append("bm25")

        # Graph Local search (Entity → Chunk)
        if weights.local > 0:
            tasks.append(self._graph_local_search(query, top_k * 3, allowed_namespaces))
            channels_executed.append("graph_local")

        # Graph Global search (Community → Entity → Chunk)
        if weights.global_ > 0:
            tasks.append(self._graph_global_search(query, top_k * 3, allowed_namespaces))
            channels_executed.append("graph_global")

        # Execute all tasks in parallel
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle errors
        channel_results = {}
        for i, channel in enumerate(channels_executed):
            result = results_list[i]
            if isinstance(result, Exception):
                logger.warning(
                    "channel_search_failed",
                    channel=channel,
                    error=str(result),
                )
                channel_results[channel] = []
            else:
                channel_results[channel] = result

        # Step 3: Prepare rankings and weights for RRF
        rankings = []
        weight_values = []

        if "vector" in channel_results:
            rankings.append(channel_results["vector"])
            weight_values.append(weights.vector)

        if "bm25" in channel_results:
            rankings.append(channel_results["bm25"])
            weight_values.append(weights.bm25)

        if "graph_local" in channel_results:
            rankings.append(channel_results["graph_local"])
            weight_values.append(weights.local)

        if "graph_global" in channel_results:
            rankings.append(channel_results["graph_global"])
            weight_values.append(weights.global_)

        # Step 4: Apply Intent-Weighted RRF
        if rankings:
            fused_results = weighted_reciprocal_rank_fusion(
                rankings=rankings,
                weights=weight_values,
                k=self.rrf_k,
                id_field="id",
            )
        else:
            fused_results = []
            logger.warning("four_way_search_no_results", query=query[:50])

        # Step 5: Apply reranking if requested
        if use_reranking and fused_results:
            reranked = await self.hybrid_search.reranker.rerank(
                query=query,
                documents=fused_results[:top_k * 2],
                top_k=top_k,
            )
            final_results = []
            for rerank_result in reranked:
                original = next(
                    (d for d in fused_results if d.get("id") == rerank_result.doc_id),
                    None,
                )
                if original:
                    final_results.append({
                        **original,
                        "rerank_score": rerank_result.rerank_score,
                        "final_rank": rerank_result.final_rank,
                    })
        else:
            final_results = fused_results[:top_k]

        total_latency_ms = (time.perf_counter() - start_time) * 1000

        # Build metadata
        metadata = FourWaySearchMetadata(
            vector_results_count=len(channel_results.get("vector", [])),
            bm25_results_count=len(channel_results.get("bm25", [])),
            graph_local_results_count=len(channel_results.get("graph_local", [])),
            graph_global_results_count=len(channel_results.get("graph_global", [])),
            intent=intent.value,
            intent_confidence=intent_result.confidence,
            intent_method=intent_result.method,
            intent_latency_ms=intent_result.latency_ms,
            weights={
                "vector": weights.vector,
                "bm25": weights.bm25,
                "local": weights.local,
                "global": weights.global_,
            },
            total_latency_ms=total_latency_ms,
            channels_executed=channels_executed,
            namespaces_searched=allowed_namespaces,
        )

        logger.info(
            "four_way_search_completed",
            query=query[:50],
            intent=intent.value,
            total_results=len(fused_results),
            final_results=len(final_results),
            latency_ms=round(total_latency_ms, 2),
            vector_count=metadata.vector_results_count,
            bm25_count=metadata.bm25_results_count,
            local_count=metadata.graph_local_results_count,
            global_count=metadata.graph_global_results_count,
        )

        return {
            "query": query,
            "results": final_results,
            "intent": intent.value,
            "weights": metadata.weights,
            "metadata": metadata,
        }

    async def _vector_search(
        self,
        query: str,
        top_k: int,
        filters: MetadataFilters | None = None,
        allowed_namespaces: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute vector search via existing HybridSearch with namespace filtering.

        Args:
            query: Search query
            top_k: Number of results
            filters: Additional metadata filters
            allowed_namespaces: Namespaces to search in

        Returns:
            List of search results with namespace info
        """
        # Build namespace filter for Qdrant
        namespace_filter = None
        if allowed_namespaces:
            namespace_filter = Filter(
                must=[
                    FieldCondition(
                        key="namespace_id",
                        match=MatchAny(any=allowed_namespaces),
                    )
                ]
            )

            # If additional filters provided, merge them
            if filters is not None:
                # Build existing filter from MetadataFilters
                existing_filter = self.hybrid_search.filter_engine.build_qdrant_filter(filters)
                if existing_filter and existing_filter.must:
                    # Combine namespace filter with existing filters
                    namespace_filter = Filter(
                        must=[
                            *namespace_filter.must,
                            *existing_filter.must,
                        ]
                    )

        # Use raw Qdrant search with namespace filter
        # (HybridSearch.vector_search uses MetadataFilters which we need to bypass)
        from src.components.shared.embedding_service import get_embedding_service

        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.embed_single(query)

        # Search with namespace filter
        results = await self.hybrid_search.qdrant_client.search(
            collection_name=self.hybrid_search.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=namespace_filter,
        )

        # Format results
        formatted_results = []
        for rank, result in enumerate(results, start=1):
            formatted_results.append({
                "id": str(result["id"]),
                "text": result["payload"].get("content", result["payload"].get("text", "")),
                "score": result["score"],
                "source": result["payload"].get("document_path", result["payload"].get("source", "unknown")),
                "document_id": result["payload"].get("document_id", ""),
                "namespace_id": result["payload"].get("namespace_id", DEFAULT_NAMESPACE),
                "rank": rank,
                "search_type": "vector",
                "source_channel": "vector",
            })

        logger.debug(
            "vector_search_with_namespaces",
            query=query[:50],
            namespaces=allowed_namespaces,
            results=len(formatted_results),
        )

        return formatted_results

    async def _bm25_search(
        self,
        query: str,
        top_k: int,
        allowed_namespaces: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute BM25 search via existing HybridSearch with namespace filtering.

        Args:
            query: Search query
            top_k: Number of results (before filtering)
            allowed_namespaces: Namespaces to filter by

        Returns:
            List of BM25 search results filtered by namespace
        """
        # Get BM25 results (retrieve more to account for filtering)
        results = await self.hybrid_search.keyword_search(
            query=query,
            top_k=top_k * 2,  # Get extra results since we'll filter by namespace
        )

        # Filter by namespace if provided
        if allowed_namespaces:
            filtered_results = []
            for result in results:
                # Check namespace_id in metadata
                namespace_id = result.get("metadata", {}).get("namespace_id", DEFAULT_NAMESPACE)
                if namespace_id in allowed_namespaces:
                    result["namespace_id"] = namespace_id
                    filtered_results.append(result)
            results = filtered_results[:top_k]  # Limit to requested count
        else:
            # No filtering, add default namespace
            for result in results:
                result["namespace_id"] = result.get("metadata", {}).get("namespace_id", DEFAULT_NAMESPACE)

        # Add source channel marker
        for r in results:
            r["source_channel"] = "bm25"

        logger.debug(
            "bm25_search_with_namespaces",
            query=query[:50],
            namespaces=allowed_namespaces,
            results_after_filter=len(results),
        )

        return results

    async def _graph_local_search(
        self, query: str, top_k: int, allowed_namespaces: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Execute Graph Local search: Entity → Chunk expansion.

        This retrieves chunks that mention entities matching the query.
        Uses the MENTIONED_IN relationship from TD-057.

        Sprint 41 Feature 41.3: Added namespace filtering for multi-tenant isolation.

        Cypher pattern:
            MATCH (e:base)-[:MENTIONED_IN]->(c:chunk)
            WHERE e.namespace_id IN allowed_namespaces AND e.entity_name matches query
            RETURN chunks ordered by mention count

        Args:
            query: Search query
            top_k: Number of results to return
            allowed_namespaces: List of namespaces to filter by (Sprint 41.3)
        """
        try:
            # Extract potential entity names from query (simple approach)
            # More sophisticated: use NER or entity linking
            query_terms = query.lower().split()

            # Search for entities matching query terms with namespace filtering
            if allowed_namespaces:
                cypher = """
                WITH $query_terms AS terms
                MATCH (e:base)
                WHERE e.namespace_id IN $allowed_namespaces
                  AND (any(term IN terms WHERE toLower(e.entity_name) CONTAINS term)
                       OR any(term IN terms WHERE toLower(e.description) CONTAINS term))
                WITH e
                MATCH (e)-[:MENTIONED_IN]->(c:chunk)
                WHERE c.namespace_id IN $allowed_namespaces
                WITH c, count(DISTINCT e) AS entity_matches, collect(DISTINCT e.entity_name) AS matched_entities
                RETURN c.chunk_id AS id,
                       c.text AS text,
                       c.document_id AS document_id,
                       c.document_path AS source,
                       c.namespace_id AS namespace_id,
                       entity_matches AS relevance,
                       matched_entities AS entities
                ORDER BY entity_matches DESC
                LIMIT $top_k
                """
                params = {
                    "query_terms": query_terms,
                    "top_k": top_k,
                    "allowed_namespaces": allowed_namespaces,
                }
            else:
                # Fallback: No namespace filtering (for backward compatibility)
                cypher = """
                WITH $query_terms AS terms
                MATCH (e:base)
                WHERE any(term IN terms WHERE toLower(e.entity_name) CONTAINS term)
                   OR any(term IN terms WHERE toLower(e.description) CONTAINS term)
                WITH e
                MATCH (e)-[:MENTIONED_IN]->(c:chunk)
                WITH c, count(DISTINCT e) AS entity_matches, collect(DISTINCT e.entity_name) AS matched_entities
                RETURN c.chunk_id AS id,
                       c.text AS text,
                       c.document_id AS document_id,
                       c.document_path AS source,
                       entity_matches AS relevance,
                       matched_entities AS entities
                ORDER BY entity_matches DESC
                LIMIT $top_k
                """
                params = {"query_terms": query_terms, "top_k": top_k}

            results = await self.neo4j_client.execute_read(cypher, params)

            # Format results for RRF
            formatted = []
            for rank, record in enumerate(results, start=1):
                formatted.append({
                    "id": record["id"],
                    "text": record["text"] or "",
                    "document_id": record.get("document_id", ""),
                    "source": record.get("source", ""),
                    "namespace_id": record.get("namespace_id", DEFAULT_NAMESPACE),
                    "score": record.get("relevance", 1),  # Entity match count as score
                    "rank": rank,
                    "search_type": "graph_local",
                    "source_channel": "graph_local",
                    "matched_entities": record.get("entities", []),
                })

            logger.debug(
                "graph_local_search_completed",
                query=query[:50],
                namespaces=allowed_namespaces,
                results=len(formatted),
            )

            return formatted

        except Exception as e:
            logger.warning("graph_local_search_failed", error=str(e))
            return []

    async def _graph_global_search(
        self,
        query: str,
        top_k: int,
        allowed_namespaces: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute Graph Global search: Community → Entity → Chunk expansion.

        This retrieves chunks related to communities/themes matching the query.
        Uses community_id from Community Detection (TD-057).

        Sprint 41 Feature 41.3: Added namespace filtering for multi-tenant isolation.

        Cypher pattern:
            MATCH (e:base {community_id: ...})-[:MENTIONED_IN]->(c:chunk)
            WHERE e.namespace_id IN allowed_namespaces AND community relates to query
            RETURN chunks ordered by community relevance

        Args:
            query: Search query
            top_k: Number of results to return
            allowed_namespaces: List of namespaces to filter by (Sprint 41.3)
        """
        try:
            # First, find communities whose entities match the query
            query_terms = query.lower().split()

            if allowed_namespaces:
                cypher = """
                WITH $query_terms AS terms
                // Find entities matching query that have community assignments
                MATCH (e:base)
                WHERE e.namespace_id IN $allowed_namespaces
                  AND e.community_id IS NOT NULL
                  AND (any(term IN terms WHERE toLower(e.entity_name) CONTAINS term)
                       OR any(term IN terms WHERE toLower(e.description) CONTAINS term))
                WITH e.community_id AS community, count(e) AS match_score
                ORDER BY match_score DESC
                LIMIT 3

                // Expand from matched communities to their entities to chunks
                MATCH (e2:base {community_id: community})
                WHERE e2.namespace_id IN $allowed_namespaces
                MATCH (e2)-[:MENTIONED_IN]->(c:chunk)
                WHERE c.namespace_id IN $allowed_namespaces
                WITH c, community, count(DISTINCT e2) AS community_entities
                RETURN c.chunk_id AS id,
                       c.text AS text,
                       c.document_id AS document_id,
                       c.document_path AS source,
                       c.namespace_id AS namespace_id,
                       community AS community_id,
                       community_entities AS relevance
                ORDER BY community_entities DESC
                LIMIT $top_k
                """
                params = {
                    "query_terms": query_terms,
                    "top_k": top_k,
                    "allowed_namespaces": allowed_namespaces,
                }
            else:
                # Fallback: No namespace filtering (for backward compatibility)
                cypher = """
                WITH $query_terms AS terms
                // Find entities matching query that have community assignments
                MATCH (e:base)
                WHERE e.community_id IS NOT NULL
                  AND (any(term IN terms WHERE toLower(e.entity_name) CONTAINS term)
                       OR any(term IN terms WHERE toLower(e.description) CONTAINS term))
                WITH e.community_id AS community, count(e) AS match_score
                ORDER BY match_score DESC
                LIMIT 3

                // Expand from matched communities to their entities to chunks
                MATCH (e2:base {community_id: community})-[:MENTIONED_IN]->(c:chunk)
                WITH c, community, count(DISTINCT e2) AS community_entities
                RETURN c.chunk_id AS id,
                       c.text AS text,
                       c.document_id AS document_id,
                       c.document_path AS source,
                       community AS community_id,
                       community_entities AS relevance
                ORDER BY community_entities DESC
                LIMIT $top_k
                """
                params = {"query_terms": query_terms, "top_k": top_k}

            results = await self.neo4j_client.execute_read(cypher, params)

            # Format results for RRF
            formatted = []
            for rank, record in enumerate(results, start=1):
                formatted.append({
                    "id": record["id"],
                    "text": record["text"] or "",
                    "document_id": record.get("document_id", ""),
                    "source": record.get("source", ""),
                    "namespace_id": record.get("namespace_id", DEFAULT_NAMESPACE),
                    "score": record.get("relevance", 1),
                    "rank": rank,
                    "search_type": "graph_global",
                    "source_channel": "graph_global",
                    "community_id": record.get("community_id"),
                })

            logger.debug(
                "graph_global_search_completed",
                query=query[:50],
                namespaces=allowed_namespaces,
                results=len(formatted),
            )

            return formatted

        except Exception as e:
            logger.warning("graph_global_search_failed", error=str(e))
            return []


# Singleton instance
_four_way_search: FourWayHybridSearch | None = None


def get_four_way_hybrid_search() -> FourWayHybridSearch:
    """Get global FourWayHybridSearch instance (singleton).

    Returns:
        FourWayHybridSearch instance
    """
    global _four_way_search
    if _four_way_search is None:
        _four_way_search = FourWayHybridSearch()
    return _four_way_search


async def four_way_search(
    query: str,
    top_k: int = 10,
    filters: MetadataFilters | None = None,
    use_reranking: bool = False,
    allowed_namespaces: list[str] | None = None,
) -> dict[str, Any]:
    """Convenience function for 4-Way Hybrid Search.

    Args:
        query: User query string
        top_k: Number of results to return
        filters: Optional metadata filters
        use_reranking: Whether to apply reranking
        allowed_namespaces: List of namespaces to search in

    Returns:
        Search results with intent-weighted RRF fusion

    Example:
        results = await four_way_search(
            "What is the authentication flow?",
            allowed_namespaces=["general", "user_proj_123"]
        )
        for r in results["results"][:3]:
            print(f"{r['rank']}: {r['text'][:100]}")
    """
    search_engine = get_four_way_hybrid_search()
    return await search_engine.search(
        query=query,
        top_k=top_k,
        filters=filters,
        use_reranking=use_reranking,
        allowed_namespaces=allowed_namespaces,
    )
