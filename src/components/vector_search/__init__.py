"""Vector Search Component - Qdrant Integration & Hybrid Search.

This module provides vector search capabilities using Qdrant vector database,
including hybrid search (Vector + BM25) and reciprocal rank fusion.
"""

from src.components.vector_search.qdrant_client import (
    QdrantClientWrapper,
    get_qdrant_client,
)
from src.components.vector_search.embeddings import (
    EmbeddingService,
    get_embedding_service,
)
from src.components.vector_search.bm25_search import BM25Search
from src.components.vector_search.hybrid_search import HybridSearch
from src.components.vector_search.ingestion import (
    DocumentIngestionPipeline,
    ingest_documents,
)

__all__ = [
    "QdrantClientWrapper",
    "get_qdrant_client",
    "EmbeddingService",
    "get_embedding_service",
    "BM25Search",
    "HybridSearch",
    "DocumentIngestionPipeline",
    "ingest_documents",
]
