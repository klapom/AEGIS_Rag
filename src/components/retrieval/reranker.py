"""Cross-encoder reranker for improving retrieval relevance.

This module implements reranking using HuggingFace cross-encoder models.
Reranking improves precision by scoring query-document pairs more accurately
than vector similarity alone.

Sprint 67 Feature 67.8: Adaptive Reranker v1 with intent-aware weights.

Typical usage:
    reranker = CrossEncoderReranker()
    reranked_results = await reranker.rerank(
        query="What is hybrid search?",
        documents=search_results,
        top_k=5
    )
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

from src.core.config import settings

# Sprint 24 Feature 24.15: Lazy import for optional reranking dependency
if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = structlog.get_logger(__name__)


# ============================================================================
# ADAPTIVE RERANKING (Sprint 67, Feature 67.8)
# ============================================================================


@dataclass(frozen=True)
class AdaptiveWeights:
    """Adaptive reranking weights based on query intent.

    Sprint 67 Feature 67.8: Intent-aware reranking with adaptive weights.

    Attributes:
        semantic_weight: Weight for semantic similarity (cross-encoder score)
        keyword_weight: Weight for keyword matching (BM25 score)
        recency_weight: Weight for document recency
    """

    semantic_weight: float
    keyword_weight: float
    recency_weight: float

    def __post_init__(self) -> None:
        """Validate that weights sum to 1.0."""
        total = self.semantic_weight + self.keyword_weight + self.recency_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


# Intent-specific weight profiles (Sprint 67.8, updated Sprint 69.4)
# Based on query intent, different retrieval signals are emphasized
# These are default weights - can be overridden by learned weights from file
DEFAULT_INTENT_RERANK_WEIGHTS: dict[str, AdaptiveWeights] = {
    # Factual: High semantic precision, low keyword, minimal recency
    # Example: "What is OMNITRACKER?" → Need precise definition
    "factual": AdaptiveWeights(semantic_weight=0.7, keyword_weight=0.2, recency_weight=0.1),
    # Keyword: High keyword matching, moderate semantic, low recency
    # Example: "JWT_TOKEN error 404" → Exact term matching critical
    "keyword": AdaptiveWeights(semantic_weight=0.3, keyword_weight=0.6, recency_weight=0.1),
    # Exploratory: Balanced semantic and keyword, moderate recency
    # Example: "How does authentication work?" → Broad exploration
    "exploratory": AdaptiveWeights(semantic_weight=0.5, keyword_weight=0.3, recency_weight=0.2),
    # Summary: High semantic, low keyword, high recency
    # Example: "Summarize recent project changes" → Recency matters
    "summary": AdaptiveWeights(semantic_weight=0.5, keyword_weight=0.2, recency_weight=0.3),
    # Default fallback (balanced)
    "default": AdaptiveWeights(semantic_weight=0.6, keyword_weight=0.3, recency_weight=0.1),
}

# Sprint 69.4: Learned weights (loaded at startup if available)
INTENT_RERANK_WEIGHTS: dict[str, AdaptiveWeights] = {}


def _load_learned_weights(weights_path: str = "data/learned_rerank_weights.json") -> None:
    """Load learned reranking weights from JSON file.

    Sprint 69 Feature 69.4: Learned Adaptive Reranker Weights

    This function loads optimized weights trained on trace data. If the file
    exists, learned weights override default weights. Otherwise, defaults are used.

    Args:
        weights_path: Path to learned weights JSON file

    Side Effects:
        Updates global INTENT_RERANK_WEIGHTS dictionary

    Example:
        >>> _load_learned_weights()
        # Loads weights from data/learned_rerank_weights.json
    """
    global INTENT_RERANK_WEIGHTS

    weights_file = Path(weights_path)

    if not weights_file.exists():
        logger.info(
            "learned_weights_not_found_using_defaults",
            weights_path=weights_path,
        )
        # Use default weights
        INTENT_RERANK_WEIGHTS = DEFAULT_INTENT_RERANK_WEIGHTS.copy()
        return

    try:
        import json

        with open(weights_file, encoding="utf-8") as f:
            learned_weights_dict = json.load(f)

        # Convert JSON to AdaptiveWeights objects
        loaded_weights: dict[str, AdaptiveWeights] = {}
        for intent, weight_config in learned_weights_dict.items():
            try:
                weights = AdaptiveWeights(
                    semantic_weight=weight_config["semantic_weight"],
                    keyword_weight=weight_config["keyword_weight"],
                    recency_weight=weight_config["recency_weight"],
                )
                loaded_weights[intent] = weights
                logger.info(
                    "loaded_learned_weights_for_intent",
                    intent=intent,
                    semantic=weights.semantic_weight,
                    keyword=weights.keyword_weight,
                    recency=weights.recency_weight,
                    ndcg_at_5=weight_config.get("ndcg_at_5"),
                )
            except (KeyError, ValueError) as e:
                logger.warning(
                    "skipping_invalid_learned_weights",
                    intent=intent,
                    error=str(e),
                )
                continue

        # Merge learned weights with defaults (learned takes precedence)
        INTENT_RERANK_WEIGHTS = DEFAULT_INTENT_RERANK_WEIGHTS.copy()
        INTENT_RERANK_WEIGHTS.update(loaded_weights)

        logger.info(
            "learned_weights_loaded",
            weights_path=weights_path,
            num_learned_intents=len(loaded_weights),
            total_intents=len(INTENT_RERANK_WEIGHTS),
        )

    except (json.JSONDecodeError, OSError) as e:
        logger.error(
            "failed_to_load_learned_weights_using_defaults",
            weights_path=weights_path,
            error=str(e),
        )
        # Fallback to defaults
        INTENT_RERANK_WEIGHTS = DEFAULT_INTENT_RERANK_WEIGHTS.copy()


# Sprint 69.4: Load learned weights at module import time
_load_learned_weights()


class RerankResult(BaseModel):
    """Result from reranking operation.

    Attributes:
        doc_id: Document ID
        text: Document text
        original_score: Original similarity score (vector/BM25/hybrid)
        rerank_score: Cross-encoder relevance score (-inf to +inf)
        final_score: Normalized score (0.0 to 1.0)
        original_rank: Position before reranking (0-indexed)
        final_rank: Position after reranking (1-indexed, rank 1 = best) - Sprint 92 Fix
        adaptive_score: Intent-aware weighted score (Sprint 67.8)
        bm25_score: BM25 keyword score (Sprint 67.8)
        recency_score: Document recency score (Sprint 67.8)
    """

    doc_id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text content")
    original_score: float = Field(..., description="Original similarity score")
    rerank_score: float = Field(..., description="Cross-encoder relevance score")
    final_score: float = Field(..., description="Normalized score (0.0 to 1.0)")
    original_rank: int = Field(..., description="Position before reranking")
    final_rank: int = Field(..., description="Position after reranking")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    # Sprint 67.8: Adaptive reranking scores
    adaptive_score: float | None = Field(
        default=None, description="Intent-aware weighted score (Sprint 67.8)"
    )
    bm25_score: float | None = Field(default=None, description="BM25 keyword score (Sprint 67.8)")
    recency_score: float | None = Field(
        default=None, description="Document recency score (Sprint 67.8)"
    )


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
        use_adaptive_weights: bool = True,
    ) -> None:
        """Initialize reranker.

        Args:
            model_name: HuggingFace cross-encoder model name
                       Defaults to settings.reranker_model
            batch_size: Batch size for scoring (default: 32)
            cache_dir: Model cache directory (default: ./data/models)
            use_adaptive_weights: Enable intent-aware adaptive weights (Sprint 67.8)
        """
        self.model_name = model_name or settings.reranker_model
        self.batch_size = batch_size
        self.cache_dir = Path(cache_dir or settings.reranker_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Sprint 67.8: Adaptive reranking configuration
        self.use_adaptive_weights = use_adaptive_weights
        self._intent_classifier: Any = None  # Lazy-loaded

        self._model: CrossEncoder | None = None

        logger.info(
            "initialized_reranker",
            model=self.model_name,
            batch_size=self.batch_size,
            cache_dir=str(self.cache_dir),
            adaptive_weights=self.use_adaptive_weights,
        )

    @property
    def model(self) -> CrossEncoder:
        """Lazy-load cross-encoder model.

        Returns:
            Loaded CrossEncoder model

        Note:
            First access will download model (~80MB) and may take 10-30s.
            Subsequent accesses use cached model.

        Raises:
            ImportError: If sentence-transformers not installed (optional reranking dependency)
        """
        if self._model is None:
            # Lazy import: Only load sentence_transformers when actually using reranker
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers is required for reranking. "
                    "Install with: poetry install --with reranking"
                ) from e

            # Sprint 120: Use CUDA for cross-encoder inference.
            # On DGX Spark (128GB unified memory), GPU inference is ~100x faster
            # than CPU for bge-reranker-v2-m3 (17.8s CPU → ~200ms GPU).
            # The cross-encoder (~560MB) coexists with BGE-M3 (~1.5GB) easily.
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(
                "loading_cross_encoder_model", model=self.model_name, device=device
            )
            # Note: sentence-transformers 3.4+ uses cache_dir instead of cache_folder
            try:
                self._model = CrossEncoder(
                    self.model_name,
                    max_length=512,  # Max sequence length for BERT-based models
                    device=device,
                    cache_dir=str(self.cache_dir),
                )
            except TypeError:
                # Fallback for older sentence-transformers versions
                self._model = CrossEncoder(  # type: ignore[call-arg]
                    self.model_name,
                    max_length=512,
                    device=device,
                    cache_folder=str(self.cache_dir),
                )
            logger.info("cross_encoder_model_loaded", model=self.model_name)
        return self._model

    def _get_intent_classifier(self) -> Any:
        """Lazy-load intent classifier for adaptive reranking.

        Sprint 67.8: Intent classifier used for adaptive weight selection.

        Returns:
            IntentClassifier instance
        """
        if self._intent_classifier is None:
            from src.components.retrieval.intent_classifier import get_intent_classifier

            self._intent_classifier = get_intent_classifier()
        return self._intent_classifier

    def _compute_recency_score(self, result: dict[str, Any]) -> float:
        """Compute recency score from document timestamp.

        Sprint 67.8: Recency score based on document creation/modification time.

        Args:
            result: Document result with metadata

        Returns:
            Recency score between 0.0 and 1.0
        """
        import datetime

        # Try to extract timestamp from metadata
        metadata = result.get("metadata", {})
        timestamp_str = metadata.get("created_at") or metadata.get("modified_at")

        if not timestamp_str:
            # No timestamp available → neutral score
            return 0.5

        try:
            # Parse timestamp (ISO 8601 format)
            if isinstance(timestamp_str, str):
                doc_time = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                # Assume Unix timestamp
                doc_time = datetime.datetime.fromtimestamp(timestamp_str, tz=datetime.timezone.utc)

            # Calculate age in days
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            age_days = (now - doc_time).total_seconds() / 86400

            # Decay function: exp(-age/180) → 0.5 score at ~125 days, 0.1 at ~415 days
            # Recent documents (< 30 days) get high scores (0.8-1.0)
            # Older documents (> 365 days) get low scores (0.0-0.2)
            import math

            recency = math.exp(-age_days / 180)
            return max(0.0, min(1.0, recency))

        except (ValueError, TypeError) as e:
            logger.debug("recency_score_parse_failed", error=str(e), timestamp=timestamp_str)
            return 0.5  # Neutral score on parse failure

    async def rerank(
        self,
        query: str,
        documents: Sequence[dict[str, Any]],
        top_k: int | None = None,
        score_threshold: float | None = None,
        section_filter: str | list[str] | None = None,
        section_boost: float = 0.1,
    ) -> list[RerankResult]:
        """Rerank documents using cross-encoder model with optional section boost.

        Sprint 62 Feature 62.5: Section-aware reranking integration.

        Args:
            query: Search query
            documents: List of documents with 'text', 'score', 'id' keys
            top_k: Return top-k results after reranking (default: return all)
            score_threshold: Filter results below this score (default: no filter)
            section_filter: Section ID(s) to boost (Sprint 62.5)
                - Single section: "1.2"
                - Multiple sections: ["1.1", "1.2", "2.1"]
            section_boost: Boost to add for matching sections (0.0 - 0.5, default: 0.1)

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

        rerank_start = time.perf_counter()

        logger.info(
            "reranking_documents",
            query=query,
            num_documents=len(documents),
            top_k=top_k,
            adaptive_weights=self.use_adaptive_weights,
        )

        # Sprint 67.8: Classify query intent for adaptive weighting
        intent_str = "default"
        weights = INTENT_RERANK_WEIGHTS["default"]
        intent_latency_ms = 0.0

        if self.use_adaptive_weights:
            try:
                intent_start = time.perf_counter()
                classifier = self._get_intent_classifier()
                intent_result = await classifier.classify(query)
                intent_latency_ms = (time.perf_counter() - intent_start) * 1000

                # Map intent classifier result to rerank weight profile
                intent_str = intent_result.intent.value
                weights = INTENT_RERANK_WEIGHTS.get(intent_str, INTENT_RERANK_WEIGHTS["default"])

                logger.info(
                    "adaptive_intent_classified",
                    query=query[:50],
                    intent=intent_str,
                    weights={
                        "semantic": weights.semantic_weight,
                        "keyword": weights.keyword_weight,
                        "recency": weights.recency_weight,
                    },
                    latency_ms=round(intent_latency_ms, 2),
                )
            except Exception as e:
                logger.warning(
                    "adaptive_intent_classification_failed",
                    error=str(e),
                    fallback="default weights",
                )
                # Continue with default weights on failure

        # Prepare query-document pairs for cross-encoder
        pairs = [(query, doc.get("text", "")) for doc in documents]

        # Score all pairs (blocking operation, but fast on CPU)
        # Note: sentence-transformers CrossEncoder.predict() is synchronous
        crossenc_start = time.perf_counter()
        rerank_scores = self.model.predict(pairs, batch_size=self.batch_size)
        crossenc_latency_ms = (time.perf_counter() - crossenc_start) * 1000

        # Apply section boost if section_filter provided (Sprint 62.5)
        if section_filter is not None:
            # Normalize section_filter to list
            target_sections = (
                [section_filter] if isinstance(section_filter, str) else section_filter
            )

            # Clamp boost to valid range [0.0, 0.5]
            clamped_boost = max(0.0, min(0.5, section_boost))

            for idx, doc in enumerate(documents):
                # Get document's section_id (try multiple field locations)
                doc_section_id = (
                    doc.get("section_id") or doc.get("metadata", {}).get("section_id") or ""
                )

                # Apply boost if document is from target section
                if doc_section_id and doc_section_id in target_sections:
                    original_score = float(rerank_scores[idx])
                    rerank_scores[idx] = original_score + clamped_boost

                    logger.debug(
                        "section_boost_applied",
                        doc_id=doc.get("id"),
                        section_id=doc_section_id,
                        original_score=original_score,
                        boosted_score=float(rerank_scores[idx]),
                        boost=clamped_boost,
                    )

        # Normalize scores to [0, 1] using sigmoid
        # Cross-encoder scores are unbounded (-inf to +inf)
        import numpy as np

        normalized_scores = 1 / (1 + np.exp(-np.array(rerank_scores)))

        # Sprint 67.8: Compute adaptive scores if enabled
        adaptive_scores: list[dict[str, float | None]] = []
        if self.use_adaptive_weights:
            for idx, doc in enumerate(documents):
                # 1. Semantic score (normalized cross-encoder score)
                semantic_score = float(normalized_scores[idx])

                # 2. Keyword score (BM25 score from document)
                # Try multiple locations: bm25_score, keyword_score, or fallback to original_score
                keyword_score_raw = (
                    doc.get("bm25_score")
                    or doc.get("keyword_score")
                    or doc.get("score", 0.0) * 0.5  # Fallback: assume original is hybrid
                )
                # Normalize keyword score to [0, 1] if needed
                keyword_score = max(0.0, min(1.0, float(keyword_score_raw)))

                # 3. Recency score (computed from timestamp)
                recency_score = self._compute_recency_score(doc)

                # 4. Compute weighted adaptive score
                adaptive_score = (
                    weights.semantic_weight * semantic_score
                    + weights.keyword_weight * keyword_score
                    + weights.recency_weight * recency_score
                )

                adaptive_scores.append(
                    {
                        "adaptive_score": adaptive_score,
                        "keyword_score": keyword_score,
                        "recency_score": recency_score,
                    }
                )

                logger.debug(
                    "adaptive_score_computed",
                    doc_id=doc.get("id"),
                    semantic=round(semantic_score, 3),
                    keyword=round(keyword_score, 3),
                    recency=round(recency_score, 3),
                    adaptive=round(adaptive_score, 3),
                )
        else:
            # No adaptive weighting → use normalized scores only
            adaptive_scores = [
                {"adaptive_score": None, "keyword_score": None, "recency_score": None}
                for _ in documents
            ]

        # Build rerank results
        results = []
        for idx, (doc, rerank_score, norm_score, adaptive_data) in enumerate(
            zip(documents, rerank_scores, normalized_scores, adaptive_scores, strict=False)
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
                # Sprint 67.8: Adaptive reranking scores
                adaptive_score=adaptive_data["adaptive_score"],
                bm25_score=adaptive_data["keyword_score"],
                recency_score=adaptive_data["recency_score"],
            )
            results.append(result)

        # Sort by adaptive score if enabled, else by rerank score
        if self.use_adaptive_weights:
            results.sort(
                key=lambda x: x.adaptive_score if x.adaptive_score is not None else x.final_score,
                reverse=True,
            )
            logger.info(
                "adaptive_reranking_applied",
                intent=intent_str,
                weights={
                    "semantic": weights.semantic_weight,
                    "keyword": weights.keyword_weight,
                    "recency": weights.recency_weight,
                },
            )
        else:
            # Sort by rerank score (highest first)
            results.sort(key=lambda x: x.rerank_score, reverse=True)

        # Update final ranks
        # Sprint 92 Fix: Use 1-indexed ranks for consistency (rank 1 = best)
        for rank, result in enumerate(results, start=1):
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

        # Calculate total latency
        total_latency_ms = (time.perf_counter() - rerank_start) * 1000

        logger.info(
            "reranking_complete",
            total_documents=len(documents),
            returned=len(results),
            top_score=results[0].final_score if results else None,
            adaptive_enabled=self.use_adaptive_weights,
            intent=intent_str if self.use_adaptive_weights else None,
            latency_breakdown={
                "total_ms": round(total_latency_ms, 2),
                "intent_classification_ms": round(intent_latency_ms, 2),
                "cross_encoder_ms": round(crossenc_latency_ms, 2),
            },
        )

        return results

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model.

        Returns:
            Dict with model name, cache location, and status
        """
        return {
            "model_name": self.model_name,
            "cache_dir": str(self.cache_dir),
            "batch_size": self.batch_size,
            "is_loaded": self._model is not None,
            "adaptive_weights_enabled": self.use_adaptive_weights,
            "intent_classifier_loaded": self._intent_classifier is not None,
        }
