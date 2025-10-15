"""Hybrid Search: Vector Search + BM25 with Reciprocal Rank Fusion.

This module combines vector-based semantic search (Qdrant) with
keyword-based BM25 search using Reciprocal Rank Fusion for optimal retrieval.
"""

import asyncio
from typing import Any

import structlog

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
        collection_name: str | None = None,
    ):
        """Initialize hybrid search.

        Args:
            qdrant_client: Qdrant client for vector search
            embedding_service: Embedding service
            bm25_search: BM25 search instance
            collection_name: Qdrant collection name
        """
        self.qdrant_client = qdrant_client or QdrantClientWrapper()
        self.embedding_service = embedding_service or EmbeddingService()
        self.bm25_search = bm25_search or BM25Search()
        self.collection_name = collection_name or settings.qdrant_collection

        logger.info(
            "Hybrid search initialized",
            collection=self.collection_name,
        )

    async def vector_search(
        self,
        query: str,
        top_k: int = 20,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Perform vector-based semantic search.

        Args:
            query: Search query
            top_k: Number of results (default: 20)
            score_threshold: Minimum similarity score

        Returns:
            List of results with text, score, and metadata
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.embed_text(query)

            # Search in Qdrant
            results = await self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
            )

            # Format results
            formatted_results = []
            for rank, result in enumerate(results, start=1):
                formatted_results.append({
                    "id": str(result["id"]),
                    "text": result["payload"].get("text", ""),
                    "score": result["score"],
                    "source": result["payload"].get("source", "unknown"),
                    "document_id": result["payload"].get("document_id", ""),
                    "rank": rank,
                    "search_type": "vector",
                })

            logger.debug(
                "Vector search completed",
                query_length=len(query),
                results_count=len(formatted_results),
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
                formatted_results.append({
                    "id": result.get("metadata", {}).get("id", ""),
                    "text": result["text"],
                    "score": result["score"],
                    "source": result.get("metadata", {}).get("source", "unknown"),
                    "document_id": result.get("metadata", {}).get("document_id", ""),
                    "rank": result["rank"],
                    "search_type": "bm25",
                })

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
    ) -> dict[str, Any]:
        """Perform hybrid search combining vector and BM25 with RRF.

        Args:
            query: Search query
            top_k: Final number of results after fusion (default: 10)
            vector_top_k: Results from vector search (default: 20)
            bm25_top_k: Results from BM25 search (default: 20)
            rrf_k: RRF constant (default: 60)
            score_threshold: Minimum vector similarity score

        Returns:
            Dictionary with fused results and metadata

        Example:
            >>> results = await hybrid_search.hybrid_search("What is RAG?")
            >>> for doc in results['results'][:5]:
            ...     print(f"{doc['rrf_rank']}: {doc['text'][:100]}")
        """
        try:
            # Run vector and BM25 search in parallel
            vector_results, bm25_results = await asyncio.gather(
                self.vector_search(
                    query=query,
                    top_k=vector_top_k,
                    score_threshold=score_threshold,
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

            # Limit to top_k
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
                        "document_id": point.payload.get("document_id", point.payload.get("doc_id", "")),
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
