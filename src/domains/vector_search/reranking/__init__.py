"""Cross-Encoder Reranking Service.

Sprint 61 Feature 61.2: Cross-encoder reranking subdomain.
50x faster than LLM reranking (120ms vs 2000ms).
"""

from src.domains.vector_search.reranking.cross_encoder_reranker import (
    CrossEncoderReranker,
)

__all__ = ["CrossEncoderReranker"]
