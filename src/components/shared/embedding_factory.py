"""Factory for embedding service backend selection.

Sprint Context: Sprint 35 (2025-12-04) - Feature 35.8: Sentence-Transformers Migration

Provides unified interface for selecting embedding backend based on configuration.
Enables seamless switching between Ollama HTTP API and sentence-transformers GPU backend.

Architecture:
    - Factory pattern for backend selection
    - Configuration-driven (EMBEDDING_BACKEND env var)
    - Compatible API across all backends
    - Global singleton pattern for efficiency

Supported Backends:
    - 'ollama': Ollama HTTP API (default, backward compatible)
    - 'sentence-transformers': High-performance GPU batching (DGX Spark)

Example:
    >>> from src.components.shared.embedding_factory import get_embedding_service
    >>> service = get_embedding_service()
    >>> embedding = service.embed_single("Hello world")
    >>> len(embedding)
    1024

Configuration:
    # .env file
    EMBEDDING_BACKEND=sentence-transformers  # or 'ollama'
    ST_MODEL_NAME=BAAI/bge-m3
    ST_DEVICE=auto  # 'auto', 'cuda', 'cpu'
    ST_BATCH_SIZE=64

Notes:
    - Default backend is 'ollama' for backward compatibility
    - All backends implement same API: embed_single(), embed_batch()
    - Backend is selected once on first call (singleton pattern)
    - To change backend, modify .env and restart application

See Also:
    - src/components/shared/embedding_service.py: Ollama backend
    - src/components/shared/sentence_transformers_embedding.py: SentenceTransformers backend
    - src/core/config.py: Configuration settings
"""

import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)

# Type alias for embedding service interface
# All backends must implement: embed_single(text: str) -> list[float]
#                              embed_batch(texts: list[str]) -> list[list[float]]
#                              get_stats() -> dict[str, Any]
EmbeddingServiceProtocol = object

# Global singleton instance
_embedding_service: EmbeddingServiceProtocol | None = None


def get_embedding_service() -> EmbeddingServiceProtocol:
    """Get embedding service instance based on configuration.

    Factory function that selects embedding backend based on EMBEDDING_BACKEND env var.
    Returns singleton instance for efficiency (shared cache, model loading).

    Returns:
        Embedding service instance (UnifiedEmbeddingService or SentenceTransformersEmbeddingService)

    Raises:
        ValueError: If EMBEDDING_BACKEND is not 'ollama' or 'sentence-transformers'

    Example:
        >>> from src.components.shared.embedding_factory import get_embedding_service
        >>> service = get_embedding_service()
        >>> embedding = service.embed_single("Hello world")
        >>> len(embedding)
        1024

    Configuration:
        # Default: Ollama backend (backward compatible)
        EMBEDDING_BACKEND=ollama

        # High-performance: sentence-transformers (DGX Spark)
        EMBEDDING_BACKEND=sentence-transformers
        ST_MODEL_NAME=BAAI/bge-m3
        ST_DEVICE=auto
        ST_BATCH_SIZE=64

    Notes:
        - First call loads model and caches instance
        - Subsequent calls return cached instance (singleton)
        - Backend selection happens once at startup
        - To change backend, modify .env and restart
    """
    global _embedding_service

    if _embedding_service is not None:
        return _embedding_service

    # Get backend from config (default: ollama for backward compatibility)
    backend = getattr(settings, "embedding_backend", "ollama")

    if backend == "sentence-transformers":
        # Import lazily to avoid loading sentence-transformers when not needed
        from src.components.shared.sentence_transformers_embedding import (
            SentenceTransformersEmbeddingService,
        )

        # Get config values with defaults
        model_name = getattr(settings, "st_model_name", "BAAI/bge-m3")
        device = getattr(settings, "st_device", "auto")
        batch_size = getattr(settings, "st_batch_size", 64)

        logger.info(
            "embedding_backend_selected",
            backend="sentence-transformers",
            model=model_name,
            device=device,
            batch_size=batch_size,
        )

        _embedding_service = SentenceTransformersEmbeddingService(
            model_name=model_name,
            device=device,
            batch_size=batch_size,
        )

    elif backend == "ollama":
        # Import lazily to avoid circular imports
        from src.components.shared.embedding_service import (
            get_embedding_service as get_ollama_service,
        )

        logger.info("embedding_backend_selected", backend="ollama")

        _embedding_service = get_ollama_service()

    else:
        raise ValueError(
            f"Invalid embedding backend: {backend}. Must be 'ollama' or 'sentence-transformers'"
        )

    return _embedding_service


def reset_embedding_service() -> None:
    """Reset global embedding service instance.

    Used for testing to force reinitialization with different config.

    Example:
        >>> from src.components.shared.embedding_factory import (
        ...     reset_embedding_service,
        ...     get_embedding_service
        ... )
        >>> reset_embedding_service()
        >>> service = get_embedding_service()  # Forces reinitialization
    """
    global _embedding_service
    _embedding_service = None
    logger.debug("embedding_service_reset")
