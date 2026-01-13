"""Vector Search Component - Qdrant Integration & Hybrid Search.

This module provides vector search capabilities using Qdrant vector database,
including hybrid search (Vector + BM25) and reciprocal rank fusion.

Sprint 87 Update: Added MultiVectorHybridSearch using Qdrant Query API with
server-side RRF fusion for BGE-M3 native hybrid search.
"""

from src.components.vector_search.bm25_search import BM25Search
from src.components.vector_search.embeddings import (
    EmbeddingService,
    get_embedding_service,
)
from src.components.vector_search.hybrid_search import HybridSearch
from src.components.vector_search.ingestion import (
    DocumentIngestionPipeline,
    ingest_documents,
)
from src.components.vector_search.multi_vector_search import (
    MultiVectorHybridSearch,
    get_multi_vector_search,
    reset_multi_vector_search,
)
from src.components.vector_search.qdrant_client import (
    QdrantClientWrapper,
    get_qdrant_client,
)

__all__ = [
    "QdrantClientWrapper",
    "get_qdrant_client",
    "EmbeddingService",
    "get_embedding_service",
    "BM25Search",
    "HybridSearch",
    "MultiVectorHybridSearch",
    "get_multi_vector_search",
    "reset_multi_vector_search",
    "DocumentIngestionPipeline",
    "ingest_documents",
]
