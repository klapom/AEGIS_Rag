"""4-Way Hybrid Retrieval with Intent-Weighted RRF.

Sprint 42 - Feature: 4-Way Hybrid RRF (TD-057)
Sprint 88 - Feature: BGE-M3 Native Hybrid Search (replaces BM25 with sparse vectors)
Sprint 115 - Feature 115.6: Vector-First Graph-Augment (ADR-057 Option 3)

This module implements a 4-channel hybrid retrieval system:
1. Multi-Vector (Qdrant): Dense + Sparse search with server-side RRF
   - Sprint 88: Replaces separate Vector + BM25 channels
   - Uses BGE-M3 sparse vectors instead of pickle-based BM25
   - Server-side fusion eliminates desync issues
2. Graph Local: Entity → Chunk expansion (MENTIONED_IN relationships)
3. Graph Global: Community → Entity → Chunk expansion

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
- BGE-M3 (Chen et al., 2024) - arXiv:2402.03216
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
from src.components.vector_search.multi_vector_search import MultiVectorHybridSearch
from src.core.namespace import DEFAULT_NAMESPACE
from src.utils.fusion import weighted_reciprocal_rank_fusion

logger = structlog.get_logger(__name__)


# Sprint 92.21: Reuse multilingual stopwords from BM25 module (stop-words package)
# These common words don't help users understand why a document matched
from src.components.vector_search.bm25_search import MULTILINGUAL_STOPWORDS


def filter_stop_words(terms: list[str], min_length: int = 2) -> list[str]:
    """Filter stop words and very short terms from query terms.

    Args:
        terms: List of query terms
        min_length: Minimum term length to keep (default: 2)

    Returns:
        Filtered list with meaningful terms only

    Note:
        Uses MULTILINGUAL_STOPWORDS from bm25_search.py which loads from
        the stop-words package (55+ languages supported).
    """
    return [t for t in terms if t.lower() not in MULTILINGUAL_STOPWORDS and len(t) >= min_length]


@dataclass
class ChannelSample:
    """Sample result from a search channel for display."""

    text: str
    score: float
    document_id: str
    title: str
    keywords: list[str] | None = None  # For BM25 samples
    matched_entities: list[str] | None = None  # For Graph samples
    community_id: str | int | None = None  # For Graph Global samples


@dataclass
class FourWaySearchMetadata:
    """Metadata from 4-Way Hybrid Search execution.

    Sprint 92: Updated to expose dense/sparse counts instead of vector/bm25.
    Sprint 115: Added entity_expansion_results_count for Vector-First Graph-Augment.
    BGE-M3 provides both dense (1024-dim semantic) and sparse (lexical) vectors.
    """

    # Sprint 92: Expose dense/sparse counts from multi-vector search
    dense_results_count: int  # Dense vector (semantic) search results
    sparse_results_count: int  # Sparse vector (lexical) search results
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
    # Sprint 52: Channel samples for UI display (extracted before fusion)
    channel_samples: dict[str, list[dict[str, Any]]] | None = None
    # Sprint 115: Vector-First Graph-Augment (ADR-057 Option 3)
    entity_expansion_results_count: int = 0  # Chunks found via entity overlap
    entity_expansion_latency_ms: float = 0.0  # Entity expansion latency
    # Deprecated fields (kept for backward compatibility)
    vector_results_count: int = 0  # DEPRECATED: Use dense_results_count
    bm25_results_count: int = 0  # DEPRECATED: Use sparse_results_count


class FourWayHybridSearch:
    """4-Way Hybrid Retrieval with Intent-Weighted RRF.

    Sprint 88: Updated to use BGE-M3 multi-vector search (dense + sparse).

    This engine combines retrieval channels:
    1. Multi-Vector Search (Qdrant) - Dense (semantic) + Sparse (lexical) with server-side RRF
       - Replaces separate Vector + BM25 channels (Sprint 88)
       - Uses BGE-M3 sparse vectors instead of pickle-based BM25
    2. Graph Local - Entity facts (MENTIONED_IN relationships)
    3. Graph Global - Community/theme context

    The weights for each channel are dynamically determined by
    classifying the query intent (factual, keyword, exploratory, summary).
    Vector and BM25 weights are combined for multi-vector search.

    Example:
        search = FourWayHybridSearch()
        results = await search.search("What is the project architecture?", top_k=10)
        # Results are ranked using intent-weighted RRF
    """

    def __init__(
        self,
        hybrid_search: HybridSearch | None = None,
        multi_vector_search: MultiVectorHybridSearch | None = None,
        neo4j_client: Neo4jClient | None = None,
        rrf_k: int = 60,
    ):
        """Initialize 4-Way Hybrid Search.

        Args:
            hybrid_search: Existing HybridSearch instance (legacy, for fallback)
            multi_vector_search: MultiVectorHybridSearch instance (Sprint 88)
            neo4j_client: Neo4j client for graph queries
            rrf_k: RRF constant (default: 60)
        """
        self.hybrid_search = hybrid_search or HybridSearch()
        self.multi_vector_search = multi_vector_search or MultiVectorHybridSearch()
        self.neo4j_client = neo4j_client or Neo4jClient()
        self.rrf_k = rrf_k

        logger.info(
            "FourWayHybridSearch initialized",
            rrf_k=rrf_k,
            multi_vector_enabled=True,
        )

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: MetadataFilters | None = None,
        use_reranking: bool = False,
        intent_override: Intent | None = None,
        allowed_namespaces: list[str] | None = None,
        use_cache: bool = True,
        use_entity_expansion: bool = True,
    ) -> dict[str, Any]:
        """Execute 4-Way Hybrid Search with Intent-Weighted RRF.

        Sprint 68 Feature 68.4: Added query caching for latency optimization.
        Sprint 115 Feature 115.6: Added Vector-First Graph-Augment (ADR-057 Option 3).

        Args:
            query: User query string
            top_k: Number of final results to return
            filters: Metadata filters (applied to vector search only)
            use_reranking: Whether to apply cross-encoder reranking
            intent_override: Force specific intent (bypass classifier)
            allowed_namespaces: List of namespaces to search in. If None, defaults to ["default", "general"]
            use_cache: Whether to use query cache (default: True)
            use_entity_expansion: Whether to expand vector results via entity overlap (default: True)
                                  Sprint 115 ADR-057: Uses Neo4j to find related chunks via shared entities.
                                  Adds ~100ms latency but improves recall without LLM calls.

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

        # Sprint 68 Feature 68.4: Check query cache first
        if use_cache:
            from src.components.retrieval.query_cache import get_query_cache

            cache = get_query_cache()
            cached_result = await cache.get(query, namespaces=allowed_namespaces)

            if cached_result:
                cache_latency_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "four_way_search_cache_hit",
                    query=query[:50],
                    cache_type=cached_result["cache_hit"],
                    latency_ms=round(cache_latency_ms, 2),
                )

                # Return cached results with updated metadata
                metadata = cached_result["metadata"]
                if hasattr(metadata, "total_latency_ms"):
                    # Update to include cache lookup time
                    metadata.total_latency_ms = cache_latency_ms

                return {
                    "query": query,
                    "results": cached_result["results"],
                    "intent": metadata.intent if hasattr(metadata, "intent") else "cached",
                    "weights": metadata.weights if hasattr(metadata, "weights") else {},
                    "metadata": metadata,
                }

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

        # Step 2: Execute all channels in parallel
        # Sprint 88: Vector + BM25 combined into multi-vector search
        tasks = []
        channels_executed = []

        # Multi-Vector search (Sprint 88: replaces separate Vector + BM25)
        # Execute if either vector or bm25 weight > 0
        multivector_weight = max(weights.vector, weights.bm25)
        if multivector_weight > 0:
            tasks.append(self._multivector_search(query, top_k * 3, allowed_namespaces))
            channels_executed.append("multivector")

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

        # Sprint 92.21: Filter stop words for keyword display
        query_terms = filter_stop_words(query.lower().split())

        # Sprint 115 ADR-057 Option 3: Vector-First Graph-Augment
        # Expand vector results via entity overlap in Neo4j (~100ms, no LLM calls)
        entity_expansion_results: list[dict[str, Any]] = []
        entity_expansion_latency_ms = 0.0
        if use_entity_expansion and "multivector" in channel_results and channel_results["multivector"]:
            expansion_start = time.perf_counter()
            entity_expansion_results = await self._expand_via_vector_results(
                vector_results=channel_results["multivector"],
                allowed_namespaces=allowed_namespaces,
                max_expansion_chunks=top_k,  # Match top_k for balanced fusion
            )
            entity_expansion_latency_ms = (time.perf_counter() - expansion_start) * 1000

            if entity_expansion_results:
                channel_results["entity_expansion"] = entity_expansion_results
                channels_executed.append("entity_expansion")

        # Sprint 52: Extract channel samples BEFORE fusion for UI display
        # Sprint 115: Moved after entity expansion to include all channels
        # This preserves the source_channel information that would be lost after RRF
        channel_samples = self._extract_channel_samples(
            channel_results, query_terms, max_per_channel=3
        )

        # Step 3: Prepare rankings and weights for RRF
        # Sprint 88: Multi-vector replaces separate vector + bm25
        rankings = []
        weight_values = []

        if "multivector" in channel_results:
            rankings.append(channel_results["multivector"])
            # Combined weight: max of vector + bm25 (since they're now fused)
            weight_values.append(max(weights.vector, weights.bm25))

        if "graph_local" in channel_results:
            rankings.append(channel_results["graph_local"])
            weight_values.append(weights.local)

        if "graph_global" in channel_results:
            rankings.append(channel_results["graph_global"])
            weight_values.append(weights.global_)

        # Sprint 115: Add entity expansion results to fusion
        if "entity_expansion" in channel_results and channel_results["entity_expansion"]:
            rankings.append(channel_results["entity_expansion"])
            # Weight entity expansion similar to graph_local (entity-based discovery)
            weight_values.append(weights.local * 0.5)  # Slightly lower weight than direct graph_local

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

        # Step 5: Apply reranking if requested (Sprint 48 Feature 48.8: Ollama Reranker)
        if use_reranking and fused_results:
            from src.core.config import settings

            # Choose reranker backend (Ollama or sentence-transformers)
            if settings.reranker_backend == "ollama":
                # Use Ollama reranker (TD-059: No sentence-transformers dependency)
                from src.components.retrieval.ollama_reranker import OllamaReranker

                ollama_reranker = OllamaReranker(
                    model=settings.reranker_ollama_model,
                    top_k=top_k,
                )

                # Extract document texts for reranking
                doc_texts = [d.get("text", "") for d in fused_results[: top_k * 2]]

                # Rerank: returns list of (doc_index, score) tuples
                reranked_indices = await ollama_reranker.rerank(
                    query=query,
                    documents=doc_texts,
                    top_k=top_k,
                )

                # Reorder results based on reranking
                # Sprint 92 Fix: Use 1-indexed ranks for consistency with RRF (rank 1 = best)
                final_results = []
                for rank, (doc_idx, score) in enumerate(reranked_indices, start=1):
                    original = fused_results[doc_idx]
                    final_results.append(
                        {
                            **original,
                            "rerank_score": score,
                            "final_rank": rank,
                        }
                    )

            else:
                # Use sentence-transformers reranker (legacy)
                reranked = await self.hybrid_search.reranker.rerank(
                    query=query,
                    documents=fused_results[: top_k * 2],
                    top_k=top_k,
                )
                final_results = []
                for rerank_result in reranked:
                    original = next(
                        (d for d in fused_results if d.get("id") == rerank_result.doc_id),
                        None,
                    )
                    if original:
                        final_results.append(
                            {
                                **original,
                                "rerank_score": rerank_result.rerank_score,
                                "final_rank": rerank_result.final_rank,
                            }
                        )
        else:
            final_results = fused_results[:top_k]

        total_latency_ms = (time.perf_counter() - start_time) * 1000

        # Build metadata
        # Sprint 92: Expose dense/sparse counts separately for UI display
        multivector_count = len(channel_results.get("multivector", []))
        entity_expansion_count = len(channel_results.get("entity_expansion", []))
        metadata = FourWaySearchMetadata(
            # Sprint 92: BGE-M3 provides both dense (semantic) and sparse (lexical) vectors
            # We report the same count for both since they're fused server-side in Qdrant
            dense_results_count=multivector_count,  # Dense vector (1024-dim semantic)
            sparse_results_count=multivector_count,  # Sparse vector (learned lexical weights)
            graph_local_results_count=len(channel_results.get("graph_local", [])),
            graph_global_results_count=len(channel_results.get("graph_global", [])),
            intent=intent.value,
            intent_confidence=intent_result.confidence,
            intent_method=intent_result.method,
            intent_latency_ms=intent_result.latency_ms,
            weights={
                "vector": weights.vector,
                "bm25": weights.bm25,
                "dense": weights.vector,  # Sprint 92: Map vector weight to dense
                "sparse": weights.bm25,  # Sprint 92: Map bm25 weight to sparse
                "local": weights.local,
                "global": weights.global_,
                "multivector": max(weights.vector, weights.bm25),  # Sprint 88 (legacy)
                "entity_expansion": weights.local * 0.5,  # Sprint 115: Entity expansion weight
            },
            total_latency_ms=total_latency_ms,
            channels_executed=channels_executed,
            namespaces_searched=allowed_namespaces,
            channel_samples=channel_samples,  # Sprint 52: Pass through for UI display
            # Sprint 115: Vector-First Graph-Augment stats (ADR-057 Option 3)
            entity_expansion_results_count=entity_expansion_count,
            entity_expansion_latency_ms=entity_expansion_latency_ms,
            # Deprecated fields (for backward compatibility)
            vector_results_count=multivector_count,
            bm25_results_count=0,  # Deprecated: sparse vectors replace BM25
        )

        logger.info(
            "four_way_search_completed",
            query=query[:50],
            intent=intent.value,
            total_results=len(fused_results),
            final_results=len(final_results),
            latency_ms=round(total_latency_ms, 2),
            multivector_count=multivector_count,  # Sprint 88: dense + sparse combined
            local_count=metadata.graph_local_results_count,
            global_count=metadata.graph_global_results_count,
            entity_expansion_count=entity_expansion_count,  # Sprint 115: Entity expansion
            entity_expansion_ms=round(entity_expansion_latency_ms, 2),
        )

        # Sprint 68 Feature 68.4: Store results in cache
        if use_cache:
            from src.components.retrieval.query_cache import get_query_cache

            cache = get_query_cache()
            await cache.set(
                query=query,
                results=final_results,
                metadata=metadata,
                namespaces=allowed_namespaces,
            )

        return {
            "query": query,
            "results": final_results,
            "intent": intent.value,
            "weights": metadata.weights,
            "metadata": metadata,
        }

    async def _multivector_search(
        self,
        query: str,
        top_k: int,
        allowed_namespaces: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute multi-vector search (dense + sparse) via Qdrant Query API.

        Sprint 88: Replaces separate _vector_search and _bm25_search methods.
        Uses BGE-M3 embeddings with server-side RRF fusion in Qdrant.

        Args:
            query: Search query
            top_k: Number of results
            allowed_namespaces: Namespaces to search in

        Returns:
            List of search results with namespace info
        """
        try:
            # Execute multi-vector hybrid search with first namespace
            # MultiVectorHybridSearch handles both dense + sparse in one call
            namespace_filter = allowed_namespaces[0] if allowed_namespaces else None

            results = await self.multi_vector_search.hybrid_search(
                query=query,
                top_k=top_k,
                prefetch_limit=min(top_k * 2, 100),  # Prefetch more for better recall
                namespace_filter=namespace_filter,
            )

            # Format results for RRF compatibility
            formatted_results = []
            for rank, result in enumerate(results, start=1):
                formatted_results.append(
                    {
                        "id": str(result.get("id", "")),
                        "text": result.get("text", ""),
                        "score": result.get("score", 0.0),
                        "source": result.get("source", "unknown"),
                        "document_id": result.get("document_id", ""),
                        "namespace_id": result.get("namespace_id", DEFAULT_NAMESPACE),
                        "rank": rank,
                        "search_type": "multivector",  # Sprint 88: dense + sparse combined
                        "source_channel": "multivector",
                    }
                )

            logger.debug(
                "multivector_search_with_namespaces",
                query=query[:50],
                namespaces=allowed_namespaces,
                results=len(formatted_results),
            )

            return formatted_results

        except Exception as e:
            logger.warning(
                "multivector_search_failed_falling_back",
                error=str(e),
                query=query[:50],
            )
            # Fallback to legacy vector search
            return await self._vector_search_legacy(query, top_k, None, allowed_namespaces)

    async def _vector_search_legacy(
        self,
        query: str,
        top_k: int,
        filters: MetadataFilters | None = None,
        allowed_namespaces: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Legacy vector search (dense only) via HybridSearch.

        Sprint 88: Fallback for when multi-vector search fails.

        Args:
            query: Search query
            top_k: Number of results
            filters: Additional metadata filters
            allowed_namespaces: Namespaces to search in

        Returns:
            List of search results with namespace info
        """
        # Build namespace filter for Qdrant
        # TD-099 FIX: Use "namespace_id" to match Qdrant payload field (Sprint 81)
        namespace_filter = None
        if allowed_namespaces:
            namespace_filter = Filter(
                must=[
                    FieldCondition(
                        key="namespace_id",  # Fixed: was "namespace", now matches ingestion payload
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
        # Sprint 92 Fix: Handle both list (Ollama/ST) and dict (FlagEmbedding) returns
        embedding_result = await embedding_service.embed_single(query)
        query_embedding = (
            embedding_result["dense"]
            if isinstance(embedding_result, dict)
            else embedding_result
        )

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
            formatted_results.append(
                {
                    "id": str(result["id"]),
                    "text": result["payload"].get("content", result["payload"].get("text", "")),
                    "score": result["score"],
                    "source": result["payload"].get(
                        "document_path", result["payload"].get("source", "unknown")
                    ),
                    "document_id": result["payload"].get("document_id", ""),
                    "namespace_id": result["payload"].get("namespace_id", DEFAULT_NAMESPACE),
                    "rank": rank,
                    "search_type": "vector",
                    "source_channel": "vector",
                }
            )

        logger.debug(
            "vector_search_legacy_with_namespaces",
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
        """[DEPRECATED] Execute BM25 search via existing HybridSearch.

        Sprint 88: DEPRECATED - Use _multivector_search instead.
        BM25 has been replaced by BGE-M3 sparse vectors in Qdrant.
        This method is kept for backward compatibility only.

        Args:
            query: Search query
            top_k: Number of results (before filtering)
            allowed_namespaces: Namespaces to filter by

        Returns:
            List of BM25 search results filtered by namespace
        """
        logger.warning(
            "bm25_search_deprecated",
            message="BM25 search is deprecated. Use multivector search with sparse vectors.",
        )
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
                result["namespace_id"] = result.get("metadata", {}).get(
                    "namespace_id", DEFAULT_NAMESPACE
                )

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
            query_terms = filter_stop_words(query.lower().split())

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
                formatted.append(
                    {
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
                    }
                )

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
            query_terms = filter_stop_words(query.lower().split())

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
                formatted.append(
                    {
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
                    }
                )

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

    def _extract_channel_samples(
        self,
        channel_results: dict[str, list[dict[str, Any]]],
        query_terms: list[str],
        max_per_channel: int = 3,
    ) -> dict[str, list[dict[str, Any]]]:
        """Extract sample results from each channel before RRF fusion.

        Sprint 52: This preserves source_channel info that would be lost after fusion.
        Sprint 92: Updated to expose dense/sparse channels instead of vector/bm25.
        Used to display channel-specific samples in the UI ReasoningPanel.

        Args:
            channel_results: Results from each channel (multivector, graph_local, graph_global)
            query_terms: Query terms for sparse vector keyword display
            max_per_channel: Maximum samples per channel (default: 3)

        Returns:
            Dictionary mapping channel names to sample lists with channel-specific metadata
            Keys: "dense", "sparse", "graph_local", "graph_global"
        """
        samples: dict[str, list[dict[str, Any]]] = {}

        for channel, results in channel_results.items():
            channel_samples = []
            for result in results[:max_per_channel]:
                # Base sample info
                sample: dict[str, Any] = {
                    "text": (result.get("text", "") or "")[:200],  # Truncate for UI
                    "score": round(result.get("score", 0.0), 3),
                    "document_id": result.get("document_id", ""),
                    "title": result.get("source", result.get("document_path", "Unknown")),
                }

                # Add channel-specific metadata
                if channel == "multivector":
                    # Sprint 92: Split multivector into dense + sparse for UI display
                    # Both get the same samples since they're fused server-side
                    sample_dense = {**sample, "search_type": "dense"}
                    sample_sparse = {**sample, "search_type": "sparse", "keywords": query_terms[:5]}

                    # Add to both dense and sparse channels
                    if "dense" not in samples:
                        samples["dense"] = []
                    if "sparse" not in samples:
                        samples["sparse"] = []
                    samples["dense"].append(sample_dense)
                    samples["sparse"].append(sample_sparse)
                    continue  # Skip appending to channel_samples

                elif channel == "bm25":
                    # [DEPRECATED] Legacy BM25: Map to sparse channel
                    sample["keywords"] = query_terms[:5]
                    if "sparse" not in samples:
                        samples["sparse"] = []
                    samples["sparse"].append(sample)
                    continue

                elif channel == "graph_local":
                    # For Graph Local: Show matched entities
                    sample["matched_entities"] = result.get("matched_entities", [])[:5]

                elif channel == "graph_global":
                    # For Graph Global: Show community ID
                    sample["community_id"] = result.get("community_id")

                elif channel == "entity_expansion":
                    # Sprint 115: For Entity Expansion: Show shared entities
                    sample["shared_entities"] = result.get("shared_entities", [])[:5]

                channel_samples.append(sample)

            if channel_samples:
                samples[channel] = channel_samples

        logger.debug(
            "channel_samples_extracted",
            channels=list(samples.keys()),
            counts={k: len(v) for k, v in samples.items()},
        )

        return samples

    async def _expand_via_vector_results(
        self,
        vector_results: list[dict[str, Any]],
        allowed_namespaces: list[str] | None = None,
        max_expansion_chunks: int = 10,
    ) -> list[dict[str, Any]]:
        """Vector-First Graph-Augment: Expand vector results via entity overlap.

        Sprint 115 Feature 115.6 (ADR-057 Option 3):
        Uses chunk_ids from vector search to find related chunks via shared entities.
        No LLM calls - pure Cypher queries (~100ms).

        This approach:
        - Uses vector search results as semantic "anchors"
        - Finds related chunks via entity overlap in Neo4j
        - Adds context that may have been missed by vector similarity alone

        Args:
            vector_results: Results from multi-vector search (top 10 used as anchors)
            allowed_namespaces: Namespaces to filter by
            max_expansion_chunks: Maximum chunks to return (default: 10)

        Returns:
            List of expanded chunks with entity_overlap scores
        """
        try:
            # Use top 10 vector results as semantic anchors
            chunk_ids = [r.get("id") for r in vector_results[:10] if r.get("id")]

            if not chunk_ids:
                logger.debug("entity_expansion_skipped", reason="no_vector_results")
                return []

            # Build namespace-aware Cypher query
            if allowed_namespaces:
                cypher = """
                // Sprint 115 ADR-057 Option 3: Vector-First Graph-Augment
                // Stage 1: Get entities from vector result chunks
                MATCH (c:chunk)<-[:MENTIONED_IN]-(e:base)
                WHERE c.chunk_id IN $chunk_ids
                  AND c.namespace_id IN $allowed_namespaces
                WITH collect(DISTINCT e.entity_name) AS entities, collect(DISTINCT c.chunk_id) AS anchor_ids

                // Stage 2: Find related chunks via shared entities
                MATCH (e2:base)-[:MENTIONED_IN]->(c2:chunk)
                WHERE e2.entity_name IN entities
                  AND c2.namespace_id IN $allowed_namespaces
                  AND NOT c2.chunk_id IN anchor_ids
                WITH c2, count(DISTINCT e2) AS entity_overlap, collect(DISTINCT e2.entity_name)[..5] AS shared_entities
                RETURN c2.chunk_id AS id,
                       c2.text AS text,
                       c2.document_id AS document_id,
                       c2.document_path AS source,
                       c2.namespace_id AS namespace_id,
                       entity_overlap,
                       shared_entities
                ORDER BY entity_overlap DESC
                LIMIT $max_expansion
                """
                params = {
                    "chunk_ids": chunk_ids,
                    "allowed_namespaces": allowed_namespaces,
                    "max_expansion": max_expansion_chunks,
                }
            else:
                # Fallback: No namespace filtering
                cypher = """
                // Sprint 115 ADR-057 Option 3: Vector-First Graph-Augment
                // Stage 1: Get entities from vector result chunks
                MATCH (c:chunk)<-[:MENTIONED_IN]-(e:base)
                WHERE c.chunk_id IN $chunk_ids
                WITH collect(DISTINCT e.entity_name) AS entities, collect(DISTINCT c.chunk_id) AS anchor_ids

                // Stage 2: Find related chunks via shared entities
                MATCH (e2:base)-[:MENTIONED_IN]->(c2:chunk)
                WHERE e2.entity_name IN entities
                  AND NOT c2.chunk_id IN anchor_ids
                WITH c2, count(DISTINCT e2) AS entity_overlap, collect(DISTINCT e2.entity_name)[..5] AS shared_entities
                RETURN c2.chunk_id AS id,
                       c2.text AS text,
                       c2.document_id AS document_id,
                       c2.document_path AS source,
                       c2.namespace_id AS namespace_id,
                       entity_overlap,
                       shared_entities
                ORDER BY entity_overlap DESC
                LIMIT $max_expansion
                """
                params = {
                    "chunk_ids": chunk_ids,
                    "max_expansion": max_expansion_chunks,
                }

            results = await self.neo4j_client.execute_read(cypher, params)

            # Format results for RRF
            formatted = []
            for rank, record in enumerate(results, start=1):
                formatted.append(
                    {
                        "id": record["id"],
                        "text": record["text"] or "",
                        "document_id": record.get("document_id", ""),
                        "source": record.get("source", ""),
                        "namespace_id": record.get("namespace_id", DEFAULT_NAMESPACE),
                        "score": record.get("entity_overlap", 1),
                        "rank": rank,
                        "search_type": "entity_expansion",
                        "source_channel": "entity_expansion",
                        "shared_entities": record.get("shared_entities", []),
                    }
                )

            logger.info(
                "entity_expansion_completed",
                anchor_chunks=len(chunk_ids),
                expanded_chunks=len(formatted),
                namespaces=allowed_namespaces,
            )

            return formatted

        except Exception as e:
            logger.warning("entity_expansion_failed", error=str(e))
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
