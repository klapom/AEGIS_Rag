"""BGE-M3 Embedding Service.

Sprint 56: Embedding subdomain of vector_search.
Sprint 61: Native Sentence-Transformers implementation (Feature 61.1).
"""

from src.domains.vector_search.embedding.native_embedding_service import (
    NativeEmbeddingService,
)

__all__ = ["NativeEmbeddingService"]
