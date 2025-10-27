"""Embedding Service for nomic-embed-text via Ollama.

This module provides embedding generation using Ollama's nomic-embed-text model
with automatic batching, caching, and error handling.

Sprint 11 Update: Now uses UnifiedEmbeddingService for shared cache across components.
"""

from typing import Any

import structlog

from src.components.shared.embedding_service import get_embedding_service as get_unified_service

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """Wrapper around UnifiedEmbeddingService for backward compatibility.

    Sprint 11: This class now delegates to UnifiedEmbeddingService to enable
    shared caching between Qdrant and LightRAG pipelines.
    """

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        batch_size: int = 32,
        enable_cache: bool = True,
    ):
        """Initialize embedding service.

        Args:
            model_name: Ollama model name (default: from settings)
            base_url: Ollama server URL (default: from settings)
            batch_size: Number of texts to embed in one batch (default: 32)
            enable_cache: Enable in-memory caching (default: True)

        Note: model_name and base_url are ignored as UnifiedEmbeddingService
        uses settings.ollama_base_url and "nomic-embed-text" by default.
        """
        self.unified_service = get_unified_service()
        self.batch_size = batch_size
        self.enable_cache = enable_cache
        # Store parameters for backward compatibility with tests
        self.model_name = model_name or self.unified_service.model_name
        self.base_url = base_url or "unified_service"

        logger.info(
            "embedding_service_initialized",
            using_unified_service=True,
            model=self.unified_service.model_name,
            cache_enabled=enable_cache,
        )

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (768-dim for nomic-embed-text)
        """
        return await self.unified_service.embed_single(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors in same order as input
        """
        return await self.unified_service.embed_batch(texts)

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for the model.

        Returns:
            Embedding dimension (768 for nomic-embed-text)
        """
        return self.unified_service.embedding_dim

    @property
    def _cache(self):
        """Get underlying cache for backward compatibility with tests."""
        return self.unified_service.cache.cache

    @property
    def _embedding_model(self):
        """Get underlying embedding model for backward compatibility with tests."""
        # Check if unified_service has _model attribute (lazy initialization)
        if not hasattr(self.unified_service, "_model"):
            return None
        return self.unified_service._model

    @_embedding_model.setter
    def _embedding_model(self, value):
        """Set underlying embedding model for test mocking."""
        self.unified_service._model = value

    def clear_cache(self):
        """Clear embedding cache."""
        # Note: This clears the shared cache used by all components
        self.unified_service.cache.cache.clear()
        self.unified_service.cache._hits = 0
        self.unified_service.cache._misses = 0
        logger.info("embedding_cache_cleared")

    def get_cache_size(self) -> int:
        """Get number of cached embeddings.

        Returns:
            Number of cached embeddings
        """
        return len(self.unified_service.cache.cache)

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats (size, hits, misses, hit_rate)
        """
        return self.unified_service.cache.stats()

    @property
    def model_info(self) -> dict[str, Any]:
        """Get model information.

        Returns:
            Dictionary with model metadata
        """
        return {
            "model_name": self.unified_service.model_name,
            "base_url": "unified_service",
            "embedding_dimension": self.get_embedding_dimension(),
            "batch_size": self.batch_size,
            "cache_enabled": self.enable_cache,
            "cached_embeddings": self.get_cache_size(),
        }


# Global embedding service instance (singleton pattern)
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get global embedding service instance (singleton).

    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
