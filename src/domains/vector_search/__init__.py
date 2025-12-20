"""Vector Search Domain - Public API.

Sprint 56: Domain boundary for vector-based retrieval.

Subdomains:
- qdrant: Qdrant client and operations
- hybrid: Hybrid search (vector + BM25 + RRF)
- embedding: BGE-M3 embedding service

Usage:
    from src.domains.vector_search import (
        EmbeddingService,
        VectorStore,
        HybridSearchService,
    )
"""

# Protocols (Sprint 57)
from src.domains.vector_search.protocols import (
    EmbeddingService,
    HybridSearchService,
    RerankingService,
    VectorStore,
)

__all__ = [
    # Protocols (Sprint 57)
    "EmbeddingService",
    "VectorStore",
    "HybridSearchService",
    "RerankingService",
]
