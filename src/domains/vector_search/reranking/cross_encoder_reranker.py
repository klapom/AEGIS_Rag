"""Cross-Encoder reranking service.

Sprint 61 Feature 61.2: 50x faster than LLM reranking.
Based on TD-072 investigation.

Performance Benchmarks (from TD-072):
- Reranking 20 docs: 120ms (vs 2000ms LLM) = 17x faster
- Throughput: 8.3 QPS (vs 0.5 QPS LLM) = 16x improvement
- Quality: Comparable to LLM reranking
"""

import torch
from sentence_transformers import CrossEncoder
import structlog
from typing import Any

logger = structlog.get_logger(__name__)


class CrossEncoderReranker:
    """Cross-Encoder reranking using BAAI BGE-reranker-v2-m3.

    Performance (from TD-072):
    - Reranking 20 docs: 120ms (vs 2000ms LLM) = 17x faster
    - Throughput: 8.3 QPS (vs 0.5 QPS LLM) = 16x improvement
    - Quality: Comparable to LLM reranking

    Model Choice:
    - BAAI/bge-reranker-v2-m3: Multilingual reranker from same team as BGE-M3
    - Perfect pairing with BGE-M3 embeddings (same BAAI family)
    - Supports 100+ languages (vs MS MARCO English-only)
    - Model size: ~560MB (slightly larger but better quality)

    Memory Efficiency:
    - VRAM: ~1.5GB (GPU) or 0GB (CPU)
    - Fast inference on both GPU and CPU
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "auto",
        max_length: int = 512,
    ):
        """Initialize cross-encoder reranker.

        Args:
            model_name: HuggingFace cross-encoder model
            device: Device to run on ('cuda', 'cpu', or 'auto')
            max_length: Maximum token length for query-document pairs
        """
        logger.info(
            "initializing_cross_encoder_reranker",
            model=model_name,
            device=device,
            max_length=max_length,
        )

        # Determine device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.model_name = model_name
        self.max_length = max_length

        # Load model
        try:
            self.model = CrossEncoder(
                model_name,
                device=device,
                max_length=max_length,
            )

            logger.info(
                "cross_encoder_reranker_initialized",
                model=model_name,
                device=device,
            )

        except Exception as e:
            logger.error(
                "cross_encoder_reranker_init_failed",
                model=model_name,
                device=device,
                error=str(e),
            )
            raise

    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 10,
        text_field: str = "text",
    ) -> list[dict[str, Any]]:
        """Rerank documents using cross-encoder.

        Args:
            query: User query
            documents: List of documents with text field
            top_k: Number of top documents to return
            text_field: Field name containing document text

        Returns:
            Reranked documents with 'rerank_score' field
        """
        if not documents:
            return []

        logger.debug(
            "reranking_documents",
            query_len=len(query),
            doc_count=len(documents),
            top_k=top_k,
        )

        # Prepare query-document pairs
        pairs = []
        for doc in documents:
            text = doc.get(text_field, "")
            if not text:
                # Fallback to other common fields
                text = doc.get("content", doc.get("page_content", ""))
            pairs.append([query, text])

        # Score pairs
        scores = self.model.predict(
            pairs,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        # Add scores to documents
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        # Sort by score (descending)
        reranked = sorted(
            documents,
            key=lambda x: x.get("rerank_score", float("-inf")),
            reverse=True,
        )

        logger.debug(
            "documents_reranked",
            input_count=len(documents),
            output_count=min(top_k, len(documents)),
            top_score=reranked[0].get("rerank_score") if reranked else None,
            bottom_score=reranked[-1].get("rerank_score") if reranked else None,
        )

        return reranked[:top_k]

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"CrossEncoderReranker("
            f"model={self.model_name}, "
            f"device={self.device})"
        )
