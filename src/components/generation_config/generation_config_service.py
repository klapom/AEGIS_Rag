"""Generation Configuration Service.

TD-097: Sprint 80 Settings UI/DB Integration

Provides centralized access to answer generation configuration with Redis persistence.

Architecture:
- Redis as single source of truth (key: "admin:generation_config")
- In-memory cache with TTL for performance (60s cache)
- Lazy loading on first access
- Thread-safe singleton pattern

RAGAS Evaluation Results (Sprint 80 Experiment #5):
| Metric          | strict=False | strict=True | Impact    |
|-----------------|--------------|-------------|-----------|
| Faithfulness    | 0.520        | 0.693       | +33% ⭐   |
| Answer Relevancy| 0.859        | 0.621       | -28%      |
| Context Precision| 0.717       | 0.717       | 0%        |
| Context Recall  | 1.000        | 1.000       | 0%        |

Usage:
    service = get_generation_config_service()
    config = await service.get_config()

    if config.strict_faithfulness_enabled:
        # Use strict citation prompt
        prompt = FAITHFULNESS_STRICT_PROMPT
"""

import json
from datetime import datetime, timedelta

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Redis key for generation configuration
REDIS_KEY_GENERATION_CONFIG = "admin:generation_config"

# Cache TTL (60 seconds for hot-reload)
CACHE_TTL_SECONDS = 60


class GenerationConfig(BaseModel):
    """Answer generation configuration schema.

    TD-097: Sprint 80 Settings UI/DB Integration

    Controls answer generation behavior including strict faithfulness mode
    and graph-to-vector fallback.

    Attributes:
        strict_faithfulness_enabled: Require citations for EVERY sentence (no general knowledge).
            When True, Faithfulness +33% but Answer Relevancy -28%.
        graph_vector_fallback_enabled: Fallback to vector search when graph returns empty.
            Improves Context Recall by ensuring contexts are always retrieved.
        updated_at: ISO timestamp of last update
    """

    strict_faithfulness_enabled: bool = Field(
        default=False,
        description=(
            "Require citations for EVERY sentence (no general knowledge). "
            "When True: Faithfulness +33%, Answer Relevancy -28%. "
            "Recommended for: Legal, Medical, Financial, Academic domains."
        ),
    )
    graph_vector_fallback_enabled: bool = Field(
        default=True,
        description=(
            "Enable automatic fallback to vector search when graph search returns empty. "
            "Improves Context Recall by ensuring contexts are always retrieved."
        ),
    )
    updated_at: str | None = Field(None, description="ISO timestamp of last update")

    model_config = {
        "json_schema_extra": {
            "example": {
                "strict_faithfulness_enabled": False,
                "graph_vector_fallback_enabled": True,
                "updated_at": "2026-01-09T12:00:00Z",
            }
        }
    }


class GenerationConfigService:
    """Service for managing answer generation configuration.

    Provides:
    - get_config(): Get current configuration (cached)
    - save_config(): Save configuration to Redis (invalidates cache)
    - clear_cache(): Force cache invalidation
    """

    def __init__(self) -> None:
        """Initialize service with empty cache."""
        self._cache: GenerationConfig | None = None
        self._cache_expires_at: datetime | None = None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None or self._cache_expires_at is None:
            return False
        return datetime.now() < self._cache_expires_at

    async def get_config(self) -> GenerationConfig:
        """Get current generation configuration.

        Returns cached config if valid, otherwise loads from Redis.
        Falls back to config.py defaults if Redis is empty.

        Returns:
            GenerationConfig with current settings

        Example:
            >>> service = get_generation_config_service()
            >>> config = await service.get_config()
            >>> print(config.strict_faithfulness_enabled)
            False
        """
        # Return cached config if valid
        if self._is_cache_valid() and self._cache is not None:
            logger.debug("generation_config_cache_hit")
            return self._cache

        # Load from Redis
        try:
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            config_json = await redis_client.get(REDIS_KEY_GENERATION_CONFIG)

            if config_json:
                config_str = (
                    config_json.decode("utf-8") if isinstance(config_json, bytes) else config_json
                )
                config_dict = json.loads(config_str)
                config = GenerationConfig(**config_dict)

                logger.info(
                    "generation_config_loaded_from_redis",
                    strict_faithfulness=config.strict_faithfulness_enabled,
                    graph_vector_fallback=config.graph_vector_fallback_enabled,
                )

                # Cache for 60 seconds
                self._cache = config
                self._cache_expires_at = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)

                return config

            # No config in Redis - try to load from config.py defaults
            logger.info("generation_config_using_defaults")

            # Create default config (optionally sync with config.py)
            try:
                from src.core.config import settings

                default_config = GenerationConfig(
                    strict_faithfulness_enabled=getattr(
                        settings, "strict_faithfulness_enabled", False
                    ),
                    graph_vector_fallback_enabled=getattr(
                        settings, "graph_vector_fallback_enabled", True
                    ),
                )
            except Exception:
                default_config = GenerationConfig()

            # Cache defaults
            self._cache = default_config
            self._cache_expires_at = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)

            return default_config

        except Exception as e:
            logger.error("failed_to_load_generation_config", error=str(e), exc_info=True)

            # Return defaults on error (fail-safe: strict mode OFF)
            return GenerationConfig()

    async def save_config(self, config: GenerationConfig) -> GenerationConfig:
        """Save generation configuration to Redis.

        Invalidates cache immediately so next read gets fresh config.

        Args:
            config: GenerationConfig to save

        Returns:
            Saved configuration with updated timestamp

        Raises:
            Exception: If Redis save fails

        Example:
            >>> service = get_generation_config_service()
            >>> config = GenerationConfig(strict_faithfulness_enabled=True)
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
            await redis_client.set(REDIS_KEY_GENERATION_CONFIG, config_json)

            logger.info(
                "generation_config_saved_to_redis",
                strict_faithfulness=config.strict_faithfulness_enabled,
                graph_vector_fallback=config.graph_vector_fallback_enabled,
                updated_at=config.updated_at,
            )

            # Invalidate cache
            self.clear_cache()

            return config

        except Exception as e:
            logger.error("failed_to_save_generation_config", error=str(e), exc_info=True)
            raise

    def clear_cache(self) -> None:
        """Clear configuration cache.

        Forces next get_config() call to reload from Redis.

        Example:
            >>> service = get_generation_config_service()
            >>> service.clear_cache()
        """
        self._cache = None
        self._cache_expires_at = None
        logger.debug("generation_config_cache_cleared")


# Singleton instance
_generation_config_service: GenerationConfigService | None = None


def get_generation_config_service() -> GenerationConfigService:
    """Get singleton GenerationConfigService instance.

    Returns:
        GenerationConfigService singleton

    Example:
        >>> service = get_generation_config_service()
        >>> service is get_generation_config_service()
        True
    """
    global _generation_config_service
    if _generation_config_service is None:
        _generation_config_service = GenerationConfigService()
    return _generation_config_service
