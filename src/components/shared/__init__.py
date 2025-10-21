"""Shared components for AEGIS RAG.

This package contains shared services and utilities used across multiple components.
"""

from src.components.shared.embedding_service import (
    UnifiedEmbeddingService,
    get_embedding_service,
)

__all__ = ["UnifiedEmbeddingService", "get_embedding_service"]
