"""Retrieval components for advanced search capabilities.

This package contains advanced retrieval components that build on top of
the vector_search foundation:

- Reranker: Cross-encoder reranking for improved relevance (sentence-transformers)
- OllamaReranker: Ollama-based reranking (Sprint 48, TD-059, no sentence-transformers)
- Query Decomposition: Handle complex multi-part queries
- Metadata Filters: Filter results by date, source, document type
- Adaptive Chunking: Document-type specific chunking strategies
- Maximum Hybrid Search: 4-signal fusion (Sprint 51 Feature 51.7)
"""

from src.components.retrieval.chunking import AdaptiveChunker, ChunkingStrategy
from src.components.retrieval.cross_modal_fusion import (
    cross_modal_fusion,
    get_chunks_for_entities,
)
from src.components.retrieval.filters import MetadataFilterEngine, MetadataFilters
from src.components.retrieval.lightrag_context_parser import (
    extract_entity_names,
    parse_lightrag_global_context,
    parse_lightrag_local_context,
)
from src.components.retrieval.maximum_hybrid_search import (
    MaximumHybridResult,
    maximum_hybrid_search,
)
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
    # Sprint 51 Feature 51.7: Maximum Hybrid Search
    "maximum_hybrid_search",
    "MaximumHybridResult",
    "cross_modal_fusion",
    "get_chunks_for_entities",
    "parse_lightrag_local_context",
    "parse_lightrag_global_context",
    "extract_entity_names",
]
