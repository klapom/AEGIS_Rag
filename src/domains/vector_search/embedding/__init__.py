"""BGE-M3 Embedding Service.

Sprint 56: Embedding subdomain of vector_search.
Sprint 61: Native Sentence-Transformers implementation (Feature 61.1).
Sprint 65: Singleton pattern to prevent multiple model loads (Feature 65.1).
"""

from src.domains.vector_search.embedding.native_embedding_service import (
    NativeEmbeddingService,
    get_native_embedding_service,
)

__all__ = ["NativeEmbeddingService", "get_native_embedding_service"]
