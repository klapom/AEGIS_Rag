"""Retrieval components for advanced search capabilities.

This package contains advanced retrieval components that build on top of
the vector_search foundation:

- Reranker: Cross-encoder reranking for improved relevance (sentence-transformers)
- OllamaReranker: Ollama-based reranking (Sprint 48, TD-059, no sentence-transformers)
- Query Decomposition: Handle complex multi-part queries
- Metadata Filters: Filter results by date, source, document type
- Adaptive Chunking: Document-type specific chunking strategies
"""

from src.components.retrieval.chunking import AdaptiveChunker, ChunkingStrategy
from src.components.retrieval.filters import MetadataFilterEngine, MetadataFilters
from src.components.retrieval.ollama_reranker import OllamaReranker, get_ollama_reranker
from src.components.retrieval.query_decomposition import (
    DecompositionResult,
    QueryClassification,
    QueryDecomposer,
    QueryType,
    SubQuery,
)
from src.components.retrieval.reranker import CrossEncoderReranker, RerankResult

__all__ = [
    "CrossEncoderReranker",
    "RerankResult",
    "OllamaReranker",
    "get_ollama_reranker",
    "QueryDecomposer",
    "QueryType",
    "QueryClassification",
    "SubQuery",
    "DecompositionResult",
    "MetadataFilterEngine",
    "MetadataFilters",
    "AdaptiveChunker",
    "ChunkingStrategy",
]
