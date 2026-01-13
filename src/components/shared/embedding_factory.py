"""Factory for embedding service backend selection.

Sprint Context:
    - Sprint 35 (2025-12-04): Feature 35.8 - Sentence-Transformers Migration
    - Sprint 87 (2026-01-13): Feature 87.1 - FlagEmbedding Service

Provides unified interface for selecting embedding backend based on configuration.
Enables seamless switching between Ollama HTTP API, sentence-transformers GPU backend,
and FlagEmbedding multi-vector backend (dense + sparse).

Architecture:
    - Factory pattern for backend selection
    - Configuration-driven (EMBEDDING_BACKEND env var)
    - Compatible API across all backends
    - Global singleton pattern for efficiency

Supported Backends:
    - 'ollama': Ollama HTTP API (default, backward compatible)
    - 'sentence-transformers': High-performance GPU batching (dense-only)
    - 'flag-embedding': Multi-vector (dense + sparse) for hybrid search

Example:
    >>> from src.components.shared.embedding_factory import get_embedding_service
    >>> service = get_embedding_service()
    >>>
    >>> # Dense-only backends (ollama, sentence-transformers)
    >>> embedding = service.embed_single("Hello world")
    >>> len(embedding)
    1024
    >>>
    >>> # Multi-vector backend (flag-embedding)
    >>> result = service.embed_single("Hello world")
    >>> result.keys()
    dict_keys(['dense', 'sparse', 'sparse_vector'])

Configuration:
    # .env file
    EMBEDDING_BACKEND=flag-embedding  # or 'sentence-transformers', 'ollama'
    ST_MODEL_NAME=BAAI/bge-m3
    ST_DEVICE=auto  # 'auto', 'cuda', 'cpu'
    ST_BATCH_SIZE=32
    ST_USE_FP16=true
    ST_SPARSE_MIN_WEIGHT=0.0
    ST_SPARSE_TOP_K=100

Notes:
    - Default backend is 'ollama' for backward compatibility
    - All backends implement: embed_single(), embed_batch(), get_stats()
    - flag-embedding returns dict with dense + sparse (others return list[float])
    - Backend is selected once on first call (singleton pattern)
    - To change backend, modify .env and restart application

See Also:
    - src/components/shared/embedding_service.py: Ollama backend
    - src/components/shared/sentence_transformers_embedding.py: SentenceTransformers backend
    - src/components/shared/flag_embedding_service.py: FlagEmbedding backend
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
        Embedding service instance (supports multiple backends)

    Raises:
        ValueError: If EMBEDDING_BACKEND is invalid

    Example:
        >>> from src.components.shared.embedding_factory import get_embedding_service
        >>> service = get_embedding_service()
        >>>
        >>> # Dense-only backends (ollama, sentence-transformers)
        >>> embedding = service.embed_single("Hello world")
        >>> len(embedding)
        1024
        >>>
        >>> # Multi-vector backend (flag-embedding)
        >>> result = service.embed_single("Hello world")
        >>> result["dense"]  # 1024D vector
        >>> result["sparse"]  # {token_id: weight}

    Configuration:
        # Default: Ollama backend (backward compatible)
        EMBEDDING_BACKEND=ollama

        # High-performance dense-only: sentence-transformers
        EMBEDDING_BACKEND=sentence-transformers
        ST_MODEL_NAME=BAAI/bge-m3
        ST_DEVICE=auto
        ST_BATCH_SIZE=64

        # Multi-vector hybrid: flag-embedding (Sprint 87)
        EMBEDDING_BACKEND=flag-embedding
        ST_MODEL_NAME=BAAI/bge-m3
        ST_DEVICE=auto
        ST_BATCH_SIZE=32
        ST_USE_FP16=true
        ST_SPARSE_MIN_WEIGHT=0.0
        ST_SPARSE_TOP_K=100

    Notes:
        - First call loads model and caches instance
        - Subsequent calls return cached instance (singleton)
        - Backend selection happens once at startup
        - To change backend, modify .env and restart
        - flag-embedding returns dict, others return list[float]
    """
    global _embedding_service

    if _embedding_service is not None:
        return _embedding_service

    # Get backend from config (default: ollama for backward compatibility)
    backend = getattr(settings, "embedding_backend", "ollama")

    if backend == "flag-embedding":
        # Sprint 87: Multi-vector backend (dense + sparse)
        from src.components.shared.flag_embedding_service import FlagEmbeddingService

        # Get config values with defaults
        model_name = getattr(settings, "st_model_name", "BAAI/bge-m3")
        device = getattr(settings, "st_device", "auto")
        batch_size = getattr(settings, "st_batch_size", 32)
        use_fp16 = getattr(settings, "st_use_fp16", True)
        sparse_min_weight = getattr(settings, "st_sparse_min_weight", 0.0)
        sparse_top_k = getattr(settings, "st_sparse_top_k", None)

        logger.info(
            "embedding_backend_selected",
            backend="flag-embedding",
            model=model_name,
            device=device,
            batch_size=batch_size,
            use_fp16=use_fp16,
            sparse_min_weight=sparse_min_weight,
            sparse_top_k=sparse_top_k,
        )

        _embedding_service = FlagEmbeddingService(
            model_name=model_name,
            device=device,
            use_fp16=use_fp16,
            batch_size=batch_size,
            sparse_min_weight=sparse_min_weight,
            sparse_top_k=sparse_top_k,
        )

    elif backend == "sentence-transformers":
        # Sprint 35: Dense-only backend
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
        # Default: Ollama HTTP API backend
        from src.components.shared.embedding_service import (
            get_embedding_service as get_ollama_service,
        )

        logger.info("embedding_backend_selected", backend="ollama")

        _embedding_service = get_ollama_service()

    else:
        raise ValueError(
            f"Invalid embedding backend: {backend}. "
            "Must be 'ollama', 'sentence-transformers', or 'flag-embedding'"
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
