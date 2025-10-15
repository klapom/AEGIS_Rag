"""Retrieval components for advanced search capabilities.

This package contains advanced retrieval components that build on top of
the vector_search foundation:

- Reranker: Cross-encoder reranking for improved relevance
- Query Decomposition: Handle complex multi-part queries
- Metadata Filters: Filter results by date, source, document type
- Adaptive Chunking: Document-type specific chunking strategies
"""

from src.components.retrieval.reranker import CrossEncoderReranker

__all__ = ["CrossEncoderReranker"]
