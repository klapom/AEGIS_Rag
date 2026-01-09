"""Chunking Configuration Service.

TD-096: Chunking Parameters UI Integration

Provides centralized access to chunking configuration with Redis persistence and caching.

Architecture:
- Redis as single source of truth (key: "admin:chunking_config")
- In-memory cache with TTL for performance (60s cache)
- Lazy loading on first access
- Thread-safe singleton pattern

References:
- GraphRAG Official Docs: https://microsoft.github.io/graphrag/
- "From Local to Global" paper: smaller chunks = 2× more entity references
- Bertelsmann GraphRAG: chunk 1200 / overlap 100

Usage:
    service = get_chunking_config_service()
    config = await service.get_config()

    # Use in adaptive chunking
    adaptive_chunks = adaptive_section_chunking(
        sections=sections,
        max_chunk=config.chunk_size,
        max_hard_limit=config.max_hard_limit,
    )
"""

import json
from datetime import datetime, timedelta

import structlog
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)

# Redis key for chunking configuration
REDIS_KEY_CHUNKING_CONFIG = "admin:chunking_config"

# Cache TTL (60 seconds for hot-reload)
CACHE_TTL_SECONDS = 60


class ChunkingConfig(BaseModel):
    """Chunking configuration schema.

    TD-096: Chunking Parameters UI Integration

    Based on GraphRAG best practices (Microsoft Research):
    - Chunk 200-400 + Gleaning 2: High precision, noisy PDFs
    - Chunk 800-1200 + Gleaning 1: Default (best recall/time ratio)
    - Chunk 1200-1500 + Gleaning 0-1: Fast throughput, structured domains
    - Chunk >1500: Not recommended (ER-Extraction timeouts)

    Attributes:
        chunk_size: Target chunk size in tokens (GraphRAG default: 1200)
        overlap: Overlap between chunks in tokens (GraphRAG default: 100)
        gleaning_steps: Entity extraction refinement passes (0=disabled)
        max_hard_limit: Hard limit for large sections (prevent ER-Extraction timeouts)
        updated_at: ISO timestamp of last update
    """

    chunk_size: int = Field(
        default=1200,
        ge=600,
        le=1500,
        description="Target chunk size in tokens (GraphRAG default: 1200)",
    )
    overlap: int = Field(
        default=100,
        ge=50,
        le=200,
        description="Overlap between chunks in tokens (GraphRAG default: 100)",
    )
    gleaning_steps: int = Field(
        default=0,
        ge=0,
        le=3,
        description="Entity extraction refinement passes (0=disabled)",
    )
    max_hard_limit: int = Field(
        default=1500,
        ge=1200,
        le=2000,
        description="Hard limit for large sections (prevent ER-Extraction timeouts)",
    )
    updated_at: str | None = Field(None, description="ISO timestamp of last update")

    @field_validator("max_hard_limit")
    @classmethod
    def validate_max_hard_limit(cls, v: int, info) -> int:
        """Ensure max_hard_limit >= chunk_size."""
        chunk_size = info.data.get("chunk_size", 1200)
        if v < chunk_size:
            raise ValueError(f"max_hard_limit ({v}) must be >= chunk_size ({chunk_size})")
        return v

    @field_validator("overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Ensure overlap < chunk_size / 2."""
        chunk_size = info.data.get("chunk_size", 1200)
        max_overlap = chunk_size // 2
        if v >= max_overlap:
            raise ValueError(f"overlap ({v}) must be < chunk_size/2 ({max_overlap})")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "chunk_size": 1200,
                "overlap": 100,
                "gleaning_steps": 0,
                "max_hard_limit": 1500,
                "updated_at": "2026-01-09T12:00:00Z",
            }
        }
    }


# Preset configurations based on GraphRAG best practices
CHUNKING_PRESETS = {
    "high_precision": ChunkingConfig(
        chunk_size=600,
        overlap=100,
        gleaning_steps=2,
        max_hard_limit=1200,
    ),
    "balanced": ChunkingConfig(
        chunk_size=1200,
        overlap=100,
        gleaning_steps=0,
        max_hard_limit=1500,
    ),
    "fast_throughput": ChunkingConfig(
        chunk_size=1500,
        overlap=80,
        gleaning_steps=0,
        max_hard_limit=1500,
    ),
}


class ChunkingConfigService:
    """Service for managing chunking configuration.

    Provides:
    - get_config(): Get current configuration (cached)
    - save_config(): Save configuration to Redis (invalidates cache)
    - get_presets(): Get preset configurations
    - clear_cache(): Force cache invalidation
    """

    def __init__(self) -> None:
        """Initialize service with empty cache."""
        self._cache: ChunkingConfig | None = None
        self._cache_expires_at: datetime | None = None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None or self._cache_expires_at is None:
            return False
        return datetime.now() < self._cache_expires_at

    async def get_config(self) -> ChunkingConfig:
        """Get current chunking configuration.

        Returns cached config if valid, otherwise loads from Redis.

        Returns:
            ChunkingConfig with current settings

        Example:
            >>> service = get_chunking_config_service()
            >>> config = await service.get_config()
            >>> print(config.chunk_size)
            1200
        """
        # Return cached config if valid
        if self._is_cache_valid() and self._cache is not None:
            logger.debug("chunking_config_cache_hit")
            return self._cache

        # Load from Redis
        try:
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            config_json = await redis_client.get(REDIS_KEY_CHUNKING_CONFIG)

            if config_json:
                config_str = (
                    config_json.decode("utf-8") if isinstance(config_json, bytes) else config_json
                )
                config_dict = json.loads(config_str)
                config = ChunkingConfig(**config_dict)

                logger.info(
                    "chunking_config_loaded_from_redis",
                    chunk_size=config.chunk_size,
                    overlap=config.overlap,
                    gleaning_steps=config.gleaning_steps,
                    max_hard_limit=config.max_hard_limit,
                )

                # Cache for 60 seconds
                self._cache = config
                self._cache_expires_at = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)

                return config

            # No config in Redis - return defaults
            logger.info("chunking_config_using_defaults")
            default_config = ChunkingConfig()

            # Cache defaults
            self._cache = default_config
            self._cache_expires_at = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)

            return default_config

        except Exception as e:
            logger.error("failed_to_load_chunking_config", error=str(e), exc_info=True)

            # Return defaults on error (fail-safe)
            return ChunkingConfig()

    async def save_config(self, config: ChunkingConfig) -> ChunkingConfig:
        """Save chunking configuration to Redis.

        Invalidates cache immediately so next read gets fresh config.

        Args:
            config: ChunkingConfig to save

        Returns:
            Saved configuration with updated timestamp

        Raises:
            Exception: If Redis save fails

        Example:
            >>> service = get_chunking_config_service()
            >>> config = ChunkingConfig(chunk_size=800)
            >>> await service.save_config(config)
        """
        try:
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            # Add timestamp
            config.updated_at = datetime.now().isoformat()

            # Save to Redis
            config_json = config.model_dump_json()
            await redis_client.set(REDIS_KEY_CHUNKING_CONFIG, config_json)

            logger.info(
                "chunking_config_saved_to_redis",
                chunk_size=config.chunk_size,
                overlap=config.overlap,
                gleaning_steps=config.gleaning_steps,
                max_hard_limit=config.max_hard_limit,
                updated_at=config.updated_at,
            )

            # Invalidate cache
            self.clear_cache()

            return config

        except Exception as e:
            logger.error("failed_to_save_chunking_config", error=str(e), exc_info=True)
            raise

    def get_presets(self) -> dict[str, dict]:
        """Get preset configurations.

        Returns:
            Dictionary of preset configurations

        Example:
            >>> service = get_chunking_config_service()
            >>> presets = service.get_presets()
            >>> presets["balanced"]["chunk_size"]
            1200
        """
        return {
            "high_precision": {
                "name": "High Precision",
                "description": "Small chunks, high gleaning (best recall, slower)",
                **CHUNKING_PRESETS["high_precision"].model_dump(exclude={"updated_at"}),
            },
            "balanced": {
                "name": "Balanced (Default)",
                "description": "GraphRAG recommended settings",
                **CHUNKING_PRESETS["balanced"].model_dump(exclude={"updated_at"}),
            },
            "fast_throughput": {
                "name": "Fast Throughput",
                "description": "Larger chunks, no gleaning (faster, lower recall)",
                **CHUNKING_PRESETS["fast_throughput"].model_dump(exclude={"updated_at"}),
            },
        }

    def clear_cache(self) -> None:
        """Clear configuration cache.

        Forces next get_config() call to reload from Redis.

        Example:
            >>> service = get_chunking_config_service()
            >>> service.clear_cache()
        """
        self._cache = None
        self._cache_expires_at = None
        logger.debug("chunking_config_cache_cleared")


# Singleton instance
_chunking_config_service: ChunkingConfigService | None = None


def get_chunking_config_service() -> ChunkingConfigService:
    """Get singleton ChunkingConfigService instance.

    Returns:
        ChunkingConfigService singleton

    Example:
        >>> service = get_chunking_config_service()
        >>> service is get_chunking_config_service()
        True
    """
    global _chunking_config_service
    if _chunking_config_service is None:
        _chunking_config_service = ChunkingConfigService()
    return _chunking_config_service
