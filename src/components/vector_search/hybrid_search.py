"""Hybrid Search: Vector Search + BM25 with Reciprocal Rank Fusion.

This module combines vector-based semantic search (Qdrant) with
keyword-based BM25 search using Reciprocal Rank Fusion for optimal retrieval.
"""

import asyncio
from typing import Any

import structlog

from src.components.retrieval.filters import MetadataFilterEngine, MetadataFilters
from src.components.retrieval.reranker import CrossEncoderReranker
from src.components.vector_search.bm25_search import BM25Search
from src.components.vector_search.embeddings import EmbeddingService
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings
from src.core.exceptions import VectorSearchError
from src.utils.fusion import analyze_ranking_diversity, reciprocal_rank_fusion

logger = structlog.get_logger(__name__)


class HybridSearch:
    """Hybrid search combining vector and keyword retrieval."""

    def __init__(
        self,
        qdrant_client: QdrantClientWrapper | None = None,
        embedding_service: EmbeddingService | None = None,
        bm25_search: BM25Search | None = None,
        reranker: CrossEncoderReranker | None = None,
        collection_name: str | None = None,
    ):
        """Initialize hybrid search.

        Args:
            qdrant_client: Qdrant client for vector search
            embedding_service: Embedding service
            bm25_search: BM25 search instance
            reranker: Cross-encoder reranker (optional, lazy-loaded if needed)
            collection_name: Qdrant collection name
        """
        self.qdrant_client = qdrant_client or QdrantClientWrapper()
        self.embedding_service = embedding_service or EmbeddingService()
        self.bm25_search = bm25_search or BM25Search()
        self._reranker = reranker  # Lazy-loaded on first use
        self.collection_name = collection_name or settings.qdrant_collection
        self.filter_engine = MetadataFilterEngine()

        logger.info(
            "Hybrid search initialized",
            collection=self.collection_name,
            reranker_enabled=reranker is not None,
        )

    @property
    def reranker(self) -> CrossEncoderReranker:
        """Lazy-load reranker instance.

        Returns:
            CrossEncoderReranker instance
        """
        if self._reranker is None:
            self._reranker = CrossEncoderReranker()
        return self._reranker

    async def vector_search(
        self,
        query: str,
        top_k: int = 20,
        score_threshold: float | None = None,
        filters: MetadataFilters | None = None,
    ) -> list[dict[str, Any]]:
        """Perform vector-based semantic search.

        Args:
            query: Search query
            top_k: Number of results (default: 20)
            score_threshold: Minimum similarity score
            filters: Metadata filters for targeted search

        Returns:
            List of results with text, score, and metadata
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.embed_text(query)

            # Build Qdrant filter from metadata filters
            qdrant_filter = None
            if filters is not None:
                qdrant_filter = self.filter_engine.build_qdrant_filter(filters)
                if qdrant_filter is not None:
                    logger.info(
                        "applying_metadata_filters_vector_search",
                        active_filters=filters.get_active_filters(),
                        selectivity=self.filter_engine.estimate_selectivity(filters),
                    )

            # Search in Qdrant
            results = await self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
            )

            # Format results
            formatted_results = []
            for rank, result in enumerate(results, start=1):
                formatted_results.append(
                    {
                        "id": str(result["id"]),
                        "text": result["payload"].get("text", ""),
                        "score": result["score"],
                        "source": result["payload"].get("source", "unknown"),
                        "document_id": result["payload"].get("document_id", ""),
                        "rank": rank,
                        "search_type": "vector",
                    }
                )

            logger.debug(
                "Vector search completed",
                query_length=len(query),
                results_count=len(formatted_results),
                filters_applied=qdrant_filter is not None,
            )

            return formatted_results

        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise VectorSearchError(f"Vector search failed: {e}") from e

    async def keyword_search(
        self,
        query: str,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Perform BM25 keyword search.

        Args:
            query: Search query
            top_k: Number of results (default: 20)

        Returns:
            List of results with text, score, and metadata
        """
        try:
            results = self.bm25_search.search(query=query, top_k=top_k)

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "id": result.get("metadata", {}).get("id", ""),
                        "text": result["text"],
                        "score": result["score"],
                        "source": result.get("metadata", {}).get("source", "unknown"),
                        "document_id": result.get("metadata", {}).get("document_id", ""),
                        "rank": result["rank"],
                        "search_type": "bm25",
                    }
                )

            logger.debug(
                "BM25 search completed",
                query_length=len(query),
                results_count=len(formatted_results),
            )

            return formatted_results

        except Exception as e:
            logger.error("BM25 search failed", error=str(e))
            raise VectorSearchError(f"BM25 search failed: {e}") from e

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        vector_top_k: int = 20,
        bm25_top_k: int = 20,
        rrf_k: int = 60,
        score_threshold: float | None = None,
        use_reranking: bool = True,
        rerank_top_k: int | None = None,
        filters: MetadataFilters | None = None,
    ) -> dict[str, Any]:
        """Perform hybrid search combining vector and BM25 with RRF.

        Args:
            query: Search query
            top_k: Final number of results after fusion (default: 10)
            vector_top_k: Results from vector search (default: 20)
            bm25_top_k: Results from BM25 search (default: 20)
            rrf_k: RRF constant (default: 60)
            score_threshold: Minimum vector similarity score
            use_reranking: Apply cross-encoder reranking (default: True)
            rerank_top_k: Number of candidates to rerank (default: 2*top_k)
            filters: Metadata filters for targeted search

        Returns:
            Dictionary with fused results and metadata

        Example:
            >>> results = await hybrid_search.hybrid_search(
            ...     "What is RAG?",
            ...     use_reranking=True
            ... )
            >>> for doc in results['results'][:5]:
            ...     print(f"{doc['rank']}: {doc['text'][:100]}")
        """
        try:
            # Validate filters if provided
            if filters is not None and not filters.is_empty():
                is_valid, error_msg = self.filter_engine.validate_filter(filters)
                if not is_valid:
                    raise VectorSearchError(f"Invalid filters: {error_msg}")
                logger.info(
                    "hybrid_search_with_filters",
                    active_filters=filters.get_active_filters(),
                    estimated_selectivity=self.filter_engine.estimate_selectivity(filters),
                )

            # Run vector and BM25 search in parallel
            vector_results, bm25_results = await asyncio.gather(
                self.vector_search(
                    query=query,
                    top_k=vector_top_k,
                    score_threshold=score_threshold,
                    filters=filters,
                ),
                self.keyword_search(
                    query=query,
                    top_k=bm25_top_k,
                ),
            )

            # Perform Reciprocal Rank Fusion
            fused_results = reciprocal_rank_fusion(
                rankings=[vector_results, bm25_results],
                k=rrf_k,
                id_field="id",
            )

            # Apply reranking if enabled
            reranking_applied = False
            if use_reranking and fused_results:
                # Determine how many candidates to rerank
                rerank_candidates = rerank_top_k or min(top_k * 2, len(fused_results))
                candidates = fused_results[:rerank_candidates]

                logger.info(
                    "applying_reranking",
                    candidates=len(candidates),
                    top_k=top_k,
                )

                # Rerank candidates
                reranked = await self.reranker.rerank(
                    query=query, documents=candidates, top_k=top_k
                )

                # Convert reranked results back to original format
                final_results = []
                for rerank_result in reranked:
                    # Find original doc by ID
                    original_doc = next(
                        (doc for doc in candidates if doc.get("id") == rerank_result.doc_id),
                        None,
                    )
                    if original_doc:
                        result = {
                            **original_doc,
                            "rerank_score": rerank_result.rerank_score,
                            "normalized_rerank_score": rerank_result.final_score,
                            "original_rrf_rank": rerank_result.original_rank,
                            "final_rank": rerank_result.final_rank,
                        }
                        final_results.append(result)

                reranking_applied = True
                logger.info(
                    "reranking_completed",
                    original_top=candidates[0].get("id") if candidates else None,
                    reranked_top=final_results[0].get("id") if final_results else None,
                    rank_changed=(
                        candidates[0].get("id") != final_results[0].get("id")
                        if candidates and final_results
                        else False
                    ),
                )
            else:
                # No reranking, just limit to top_k
                final_results = fused_results[:top_k]

            # Analyze ranking diversity
            diversity_stats = analyze_ranking_diversity(
                rankings=[vector_results, bm25_results],
                top_k=min(vector_top_k, bm25_top_k),
                id_field="id",
            )

            logger.info(
                "Hybrid search completed",
                query_length=len(query),
                vector_results=len(vector_results),
                bm25_results=len(bm25_results),
                fused_results=len(fused_results),
                final_results=len(final_results),
                reranking_applied=reranking_applied,
                common_percentage=diversity_stats.get("common_percentage", 0),
            )

            return {
                "query": query,
                "results": final_results,
                "total_results": len(fused_results),
                "returned_results": len(final_results),
                "search_metadata": {
                    "vector_results_count": len(vector_results),
                    "bm25_results_count": len(bm25_results),
                    "rrf_k": rrf_k,
                    "reranking_applied": reranking_applied,
                    "diversity_stats": diversity_stats,
                },
            }

        except Exception as e:
            logger.error("Hybrid search failed", error=str(e))
            raise VectorSearchError(f"Hybrid search failed: {e}") from e

    async def prepare_bm25_index(self) -> dict[str, Any]:
        """Prepare BM25 index from Qdrant collection.

        This loads all documents from Qdrant and fits the BM25 model.
        Should be called once after document ingestion.

        Returns:
            Dictionary with indexing statistics
        """
        try:
            logger.info("Preparing BM25 index from Qdrant collection")

            # Get all points from Qdrant (scroll through collection)
            documents = []
            offset = None
            batch_count = 0

            while True:
                # Scroll through collection
                scroll_result = await self.qdrant_client.async_client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                points, next_offset = scroll_result
                batch_count += 1

                logger.debug(
                    "Scroll batch retrieved",
                    batch=batch_count,
                    points_in_batch=len(points),
                    total_documents=len(documents),
                )

                for point in points:
                    # Extract text from payload
                    # Check multiple possible text fields (LlamaIndex vs custom format)
                    text = ""

                    if "_node_content" in point.payload:
                        # LlamaIndex format - parse JSON
                        import json

                        try:
                            node_content = json.loads(point.payload["_node_content"])
                            text = node_content.get("text", "")
                        except (json.JSONDecodeError, KeyError):
                            logger.warning("Failed to parse _node_content", point_id=str(point.id))
                    elif "text" in point.payload:
                        # Direct text field
                        text = point.payload.get("text", "")

                    doc = {
                        "id": str(point.id),
                        "text": text,
                        "source": point.payload.get("file_name", point.payload.get("source", "")),
                        "document_id": point.payload.get(
                            "document_id", point.payload.get("doc_id", "")
                        ),
                    }
                    documents.append(doc)

                if next_offset is None:
                    break

                offset = next_offset

            logger.info(
                "All documents retrieved from Qdrant",
                total_documents=len(documents),
                batches=batch_count,
            )

            # Safety check for empty collection
            if not documents:
                raise VectorSearchError(
                    f"No documents found in collection '{self.collection_name}'. "
                    "Please ingest documents first."
                )

            # Fit BM25 model
            self.bm25_search.fit(documents, text_field="text")

            stats = {
                "documents_indexed": len(documents),
                "bm25_corpus_size": self.bm25_search.get_corpus_size(),
                "collection_name": self.collection_name,
            }

            logger.info("BM25 index prepared", **stats)

            return stats

        except Exception as e:
            logger.error("Failed to prepare BM25 index", error=str(e))
            raise VectorSearchError(f"Failed to prepare BM25 index: {e}") from e
