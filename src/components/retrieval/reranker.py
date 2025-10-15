"""Cross-encoder reranker for improving retrieval relevance.

This module implements reranking using HuggingFace cross-encoder models.
Reranking improves precision by scoring query-document pairs more accurately
than vector similarity alone.

Typical usage:
    reranker = CrossEncoderReranker()
    reranked_results = await reranker.rerank(
        query="What is hybrid search?",
        documents=search_results,
        top_k=5
    )
"""

from collections.abc import Sequence
from pathlib import Path

import structlog
from pydantic import BaseModel, Field
from sentence_transformers import CrossEncoder

from src.core.config import settings

logger = structlog.get_logger(__name__)


class RerankResult(BaseModel):
    """Result from reranking operation.

    Attributes:
        doc_id: Document ID
        text: Document text
        original_score: Original similarity score (vector/BM25/hybrid)
        rerank_score: Cross-encoder relevance score (-inf to +inf)
        final_score: Normalized score (0.0 to 1.0)
        original_rank: Position before reranking (0-indexed)
        final_rank: Position after reranking (0-indexed)
    """

    doc_id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text content")
    original_score: float = Field(..., description="Original similarity score")
    rerank_score: float = Field(..., description="Cross-encoder relevance score")
    final_score: float = Field(..., description="Normalized score (0.0 to 1.0)")
    original_rank: int = Field(..., description="Position before reranking")
    final_rank: int = Field(..., description="Position after reranking")
    metadata: dict = Field(default_factory=dict, description="Document metadata")


class CrossEncoderReranker:
    """Cross-encoder reranker using HuggingFace models.

    Uses a pre-trained cross-encoder model to score query-document pairs.
    Cross-encoders provide more accurate relevance scores than bi-encoders
    (vector similarity) by jointly encoding query and document.

    Default model: cross-encoder/ms-marco-MiniLM-L-6-v2 (80MB)
    - Trained on MS MARCO passage ranking dataset
    - Fast inference (~5-10ms per pair on CPU)
    - Good balance of speed and accuracy

    Attributes:
        model_name: HuggingFace model identifier
        batch_size: Batch size for reranking (default: 32)
        cache_dir: Directory for caching downloaded models
        model: Loaded CrossEncoder model (lazy-loaded)
    """

    def __init__(
        self,
        model_name: str | None = None,
        batch_size: int = 32,
        cache_dir: str | None = None,
    ):
        """Initialize reranker.

        Args:
            model_name: HuggingFace cross-encoder model name
                       Defaults to settings.reranker_model
            batch_size: Batch size for scoring (default: 32)
            cache_dir: Model cache directory (default: ./data/models)
        """
        self.model_name = model_name or settings.reranker_model
        self.batch_size = batch_size
        self.cache_dir = Path(cache_dir or settings.reranker_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._model: CrossEncoder | None = None

        logger.info(
            "initialized_reranker",
            model=self.model_name,
            batch_size=self.batch_size,
            cache_dir=str(self.cache_dir),
        )

    @property
    def model(self) -> CrossEncoder:
        """Lazy-load cross-encoder model.

        Returns:
            Loaded CrossEncoder model

        Note:
            First access will download model (~80MB) and may take 10-30s.
            Subsequent accesses use cached model.
        """
        if self._model is None:
            logger.info("loading_cross_encoder_model", model=self.model_name)
            # Note: sentence-transformers 3.4+ uses cache_dir instead of cache_folder
            try:
                self._model = CrossEncoder(
                    self.model_name,
                    max_length=512,  # Max sequence length for BERT-based models
                    device="cpu",  # Use CPU (sufficient for inference)
                    cache_dir=str(self.cache_dir),
                )
            except TypeError:
                # Fallback for older sentence-transformers versions
                self._model = CrossEncoder(  # type: ignore[call-arg]
                    self.model_name,
                    max_length=512,
                    device="cpu",
                    cache_folder=str(self.cache_dir),  # type: ignore[call-arg]
                )
            logger.info("cross_encoder_model_loaded", model=self.model_name)
        return self._model

    async def rerank(
        self,
        query: str,
        documents: Sequence[dict],
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[RerankResult]:
        """Rerank documents using cross-encoder model.

        Args:
            query: Search query
            documents: List of documents with 'text', 'score', 'id' keys
            top_k: Return top-k results after reranking (default: return all)
            score_threshold: Filter results below this score (default: no filter)

        Returns:
            Reranked results sorted by relevance (highest first)

        Example:
            >>> reranker = CrossEncoderReranker()
            >>> docs = [
            ...     {"id": "doc1", "text": "Vector search uses embeddings", "score": 0.8},
            ...     {"id": "doc2", "text": "BM25 is a keyword search", "score": 0.7},
            ... ]
            >>> results = await reranker.rerank(
            ...     query="What is vector search?",
            ...     documents=docs,
            ...     top_k=1
            ... )
            >>> results[0].doc_id
            'doc1'
        """
        if not documents:
            logger.warning("rerank_called_with_empty_documents")
            return []

        logger.info(
            "reranking_documents",
            query=query,
            num_documents=len(documents),
            top_k=top_k,
        )

        # Prepare query-document pairs for cross-encoder
        pairs = [(query, doc.get("text", "")) for doc in documents]

        # Score all pairs (blocking operation, but fast on CPU)
        # Note: sentence-transformers CrossEncoder.predict() is synchronous
        rerank_scores = self.model.predict(pairs, batch_size=self.batch_size)

        # Normalize scores to [0, 1] using sigmoid
        # Cross-encoder scores are unbounded (-inf to +inf)
        import numpy as np

        normalized_scores = 1 / (1 + np.exp(-np.array(rerank_scores)))

        # Build rerank results
        results = []
        for idx, (doc, rerank_score, norm_score) in enumerate(
            zip(documents, rerank_scores, normalized_scores, strict=False)
        ):
            result = RerankResult(
                doc_id=doc.get("id", f"doc_{idx}"),
                text=doc.get("text", ""),
                original_score=doc.get("score", 0.0),
                rerank_score=float(rerank_score),
                final_score=float(norm_score),
                original_rank=idx,
                final_rank=0,  # Will be updated after sorting
                metadata=doc.get("metadata", {}),
            )
            results.append(result)

        # Sort by rerank score (highest first)
        results.sort(key=lambda x: x.rerank_score, reverse=True)

        # Update final ranks
        for rank, result in enumerate(results):
            result.final_rank = rank

        # Apply score threshold filter
        if score_threshold is not None:
            results = [r for r in results if r.final_score >= score_threshold]
            logger.info(
                "applied_score_threshold",
                threshold=score_threshold,
                kept=len(results),
                filtered=len(documents) - len(results),
            )

        # Apply top-k limit
        if top_k is not None:
            results = results[:top_k]

        logger.info(
            "reranking_complete",
            total_documents=len(documents),
            returned=len(results),
            top_score=results[0].final_score if results else None,
        )

        return results

    def get_model_info(self) -> dict:
        """Get information about the loaded model.

        Returns:
            Dict with model name, cache location, and status
        """
        return {
            "model_name": self.model_name,
            "cache_dir": str(self.cache_dir),
            "batch_size": self.batch_size,
            "is_loaded": self._model is not None,
        }
