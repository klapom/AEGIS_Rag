"""Vector Search Domain - Public API.

Sprint 56: Domain boundary for vector-based retrieval.

Subdomains:
- qdrant: Qdrant client and operations
- hybrid: Hybrid search (vector + BM25 + RRF)
- embedding: BGE-M3 embedding service

Usage:
    from src.domains.vector_search import (
        hybrid_search,
        QdrantClientWrapper,
        get_embedding_service,
    )
"""

__all__ = []
