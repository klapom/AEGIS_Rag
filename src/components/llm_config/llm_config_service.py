"""LLM Configuration Service with Redis Persistence.

Sprint 64 Feature 64.6: Centralized LLM Configuration Management

This service provides centralized access to LLM model configuration across all
backend services, eliminating the critical disconnect between Admin UI settings
and backend model usage.

Key Features:
    - Redis persistence (key: "admin:llm_config")
    - 60-second in-memory cache (reduces Redis load)
    - Automatic fallback to config.py defaults
    - Hot-reloadable (no service restart needed)
    - Atomic configuration updates

Architecture:
    ┌─────────────┐
    │  Admin UI   │ (React, localStorage migration)
    └──────┬──────┘
           │ HTTP PUT/GET /admin/llm/config
           ▼
    ┌──────────────────┐
    │ LLMConfigService │ (This module, Singleton)
    └────┬────┬────┬───┘
         │    │    │
         │    │    └─► config.py (fallback)
         │    └─────► Redis Cache (60s TTL)
         └──────────► Redis (persistent storage)

Use Cases Managed:
    1. intent_classification - Query routing (router agent)
    2. entity_extraction - Domain training & graph extraction (THE CRITICAL BUG FIX!)
    3. answer_generation - Final answer synthesis
    4. followup_titles - Follow-up question generation
    5. query_decomposition - Complex query breakdown
    6. vision_vlm - Image description generation

Example:
    >>> from src.components.llm_config import get_llm_config_service, LLMUseCase
    >>> service = get_llm_config_service()
    >>> model = await service.get_model_for_use_case(LLMUseCase.ENTITY_EXTRACTION)
    >>> print(model)  # "qwen3:32b" (from Admin UI, not hardcoded!)

Sprint Context:
    Sprint 64 Feature 64.6 fixes the critical bug where:
    - Admin UI shows: "entity_extraction = qwen3:32b"
    - Backend uses: settings.lightrag_llm_model = "nemotron-3-nano" (WRONG!)

    This service ensures backend respects Admin UI configuration.
"""

import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Redis key for unified LLM configuration
REDIS_KEY_LLM_CONFIG = "admin:llm_config"

# In-memory cache with TTL (reduces Redis load)
_config_cache: "LLMConfig | None" = None
_cache_timestamp: datetime | None = None
_CACHE_TTL_SECONDS = 60  # 60s cache balances freshness vs performance


class LLMUseCase(str, Enum):
    """LLM use case identifiers matching frontend AdminLLMConfigPage.tsx.

    These enum values MUST match the frontend UseCaseType definition exactly.
    Each use case maps to specific backend services.

    Mapping to Backend Services:
        INTENT_CLASSIFICATION → src/agents/router.py (ollama_model_router)
        ENTITY_EXTRACTION → src/components/domain_training/* (lightrag_llm_model)
        ANSWER_GENERATION → src/agents/answer_generator.py (ollama_model_generation)
        FOLLOWUP_TITLES → src/agents/multi_turn/* (TBD)
        QUERY_DECOMPOSITION → src/agents/multi_turn/* (TBD)
        VISION_VLM → src/components/ingestion/image_processor.py (qwen3vl_model)
    """

    INTENT_CLASSIFICATION = "intent_classification"
    ENTITY_EXTRACTION = "entity_extraction"
    ANSWER_GENERATION = "answer_generation"
    FOLLOWUP_TITLES = "followup_titles"
    QUERY_DECOMPOSITION = "query_decomposition"
    VISION_VLM = "vision_vlm"


class UseCaseModelConfig:
    """Model configuration for a specific use case.

    Lightweight class (not Pydantic) to avoid circular imports with API models.
    The API layer (admin_llm.py) defines the Pydantic version for validation.

    Attributes:
        use_case: Use case identifier
        model_id: Model ID in format "provider/model_name" (e.g., "ollama/qwen3:32b")
        enabled: Whether this use case is active
        updated_at: ISO 8601 timestamp of last update
    """

    def __init__(
        self,
        use_case: LLMUseCase,
        model_id: str,
        enabled: bool = True,
        updated_at: str | None = None,
    ):
        self.use_case = use_case
        self.model_id = model_id
        self.enabled = enabled
        self.updated_at = updated_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "use_case": self.use_case.value,
            "model_id": self.model_id,
            "enabled": self.enabled,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UseCaseModelConfig":
        """Create from dictionary (Redis deserialization)."""
        return cls(
            use_case=LLMUseCase(data["use_case"]),
            model_id=data["model_id"],
            enabled=data.get("enabled", True),
            updated_at=data.get("updated_at"),
        )


class LLMConfig:
    """Complete LLM configuration for all use cases.

    This class manages the unified configuration for all 6 use cases.
    Stored as a single JSON object in Redis for atomic updates.

    Attributes:
        use_cases: Dict mapping use case to model configuration
        version: Config schema version (for future migrations)
        updated_at: ISO 8601 timestamp of last update
    """

    def __init__(
        self,
        use_cases: dict[LLMUseCase, UseCaseModelConfig] | None = None,
        version: int = 1,
        updated_at: str | None = None,
    ):
        self.use_cases = use_cases or {}
        self.version = version
        self.updated_at = updated_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "use_cases": {uc.value: config.to_dict() for uc, config in self.use_cases.items()},
            "version": self.version,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMConfig":
        """Create from dictionary (Redis deserialization)."""
        use_cases = {
            LLMUseCase(uc_key): UseCaseModelConfig.from_dict(uc_data)
            for uc_key, uc_data in data.get("use_cases", {}).items()
        }
        return cls(
            use_cases=use_cases,
            version=data.get("version", 1),
            updated_at=data.get("updated_at"),
        )


class LLMConfigService:
    """Service for managing LLM configuration across all use cases.

    This service provides centralized config access with:
    - Redis persistence (key: "admin:llm_config")
    - 60-second in-memory cache
    - Automatic fallback to config.py defaults
    - Hot-reload support (no restart needed)

    Usage Pattern:
        >>> service = get_llm_config_service()
        >>> model = await service.get_model_for_use_case(LLMUseCase.ENTITY_EXTRACTION)
        >>> # Returns "qwen3:32b" from Admin UI config (not hardcoded!)

    Cache Strategy:
        - First call: Fetch from Redis, populate cache
        - Subsequent calls (< 60s): Return cached value
        - After 60s: Re-fetch from Redis
        - On save: Immediately update cache

    Fallback Chain:
        1. Check in-memory cache (if < 60s old)
        2. Fetch from Redis
        3. Fall back to config.py defaults (if Redis unavailable)
        4. Never fail - always return a valid model name
    """

    async def get_config(self) -> LLMConfig:
        """Get full LLM configuration from Redis or defaults.

        Returns cached config if fresh (< 60s old), otherwise fetches from Redis.
        Falls back to config.py defaults if Redis unavailable.

        Returns:
            LLMConfig with all use case configurations

        Example:
            >>> service = LLMConfigService()
            >>> config = await service.get_config()
            >>> print(len(config.use_cases))  # 6 use cases
        """
        global _config_cache, _cache_timestamp

        # Check cache freshness
        if _config_cache and _cache_timestamp:
            age = datetime.now() - _cache_timestamp
            if age < timedelta(seconds=_CACHE_TTL_SECONDS):
                logger.debug("llm_config_cache_hit", age_seconds=age.total_seconds())
                return _config_cache

        # Cache miss - fetch from Redis
        try:
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            config_json = await redis_client.get(REDIS_KEY_LLM_CONFIG)

            if config_json:
                config_str = (
                    config_json.decode("utf-8") if isinstance(config_json, bytes) else config_json
                )
                config_dict = json.loads(config_str)
                config = LLMConfig.from_dict(config_dict)

                # Update cache
                _config_cache = config
                _cache_timestamp = datetime.now()

                logger.info("llm_config_loaded_from_redis", version=config.version)
                return config
            else:
                # No config in Redis - migrate from config.py defaults
                logger.info("llm_config_not_found_migrating_from_settings")
                default_config = self._build_default_config_from_settings()

                # Save defaults to Redis for future use
                await self.save_config(default_config)

                return default_config

        except Exception as e:
            logger.error("llm_config_load_failed_using_fallback", error=str(e), exc_info=True)
            return self._build_default_config_from_settings()

    async def get_model_for_use_case(self, use_case: LLMUseCase) -> str:
        """Get the configured model for a specific use case.

        This is the primary method used by backend services to get their model.
        Returns model name without provider prefix (e.g., "qwen3:32b" not "ollama/qwen3:32b").

        Args:
            use_case: Use case enum (e.g., LLMUseCase.ENTITY_EXTRACTION)

        Returns:
            Model name without provider prefix (e.g., "qwen3:32b")

        Example:
            >>> service = LLMConfigService()
            >>> model = await service.get_model_for_use_case(LLMUseCase.ENTITY_EXTRACTION)
            >>> print(model)  # "qwen3:32b" (from Admin UI)

        Sprint 64 Context:
            This method fixes the critical bug where domain training used
            settings.lightrag_llm_model="nemotron-3-nano" instead of
            admin-configured "qwen3:32b".
        """
        config = await self.get_config()

        if use_case not in config.use_cases:
            logger.warning(
                "use_case_not_configured_using_fallback",
                use_case=use_case.value,
            )
            return self._get_fallback_model(use_case)

        use_case_config = config.use_cases[use_case]

        # Extract model name (remove "ollama/" or "alibaba/" prefix)
        model_id = use_case_config.model_id
        if "/" in model_id:
            provider, model_name = model_id.split("/", 1)
            logger.debug(
                "model_resolved_for_use_case",
                use_case=use_case.value,
                model=model_name,
                provider=provider,
            )
        else:
            model_name = model_id
            logger.debug(
                "model_resolved_for_use_case",
                use_case=use_case.value,
                model=model_name,
                provider="unknown",
            )

        return model_name

    async def save_config(self, config: LLMConfig) -> None:
        """Save LLM configuration to Redis and invalidate cache.

        Updates all use case configurations atomically and immediately
        invalidates the cache so new config takes effect within 1 second.

        Args:
            config: Complete LLM configuration to save

        Raises:
            Exception: If Redis save fails (caller should handle)

        Example:
            >>> service = LLMConfigService()
            >>> config = await service.get_config()
            >>> config.use_cases[LLMUseCase.ENTITY_EXTRACTION].model_id = "ollama/llama3.2:8b"
            >>> await service.save_config(config)
            >>> # Config takes effect immediately (cache updated)
        """
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        redis_client = await redis_memory.client

        # Update timestamp
        config.updated_at = datetime.now().isoformat()

        # Save to Redis
        config_json = json.dumps(config.to_dict())
        await redis_client.set(REDIS_KEY_LLM_CONFIG, config_json)

        # Invalidate cache immediately (hot-reload)
        global _config_cache, _cache_timestamp
        _config_cache = config
        _cache_timestamp = datetime.now()

        logger.info(
            "llm_config_saved",
            version=config.version,
            use_cases_count=len(config.use_cases),
            updated_at=config.updated_at,
        )

    def _build_default_config_from_settings(self) -> LLMConfig:
        """Build default config from config.py settings.

        Migration path: config.py → Redis (first-time initialization)

        This ensures backwards compatibility: existing deployments that never
        configured via Admin UI will get sensible defaults from config.py.

        Returns:
            LLMConfig with defaults from config.py settings
        """
        from src.core.config import settings

        return LLMConfig(
            use_cases={
                LLMUseCase.INTENT_CLASSIFICATION: UseCaseModelConfig(
                    use_case=LLMUseCase.INTENT_CLASSIFICATION,
                    model_id=f"ollama/{settings.ollama_model_router}",
                ),
                LLMUseCase.ENTITY_EXTRACTION: UseCaseModelConfig(
                    use_case=LLMUseCase.ENTITY_EXTRACTION,
                    model_id=f"ollama/{settings.lightrag_llm_model}",
                ),
                LLMUseCase.ANSWER_GENERATION: UseCaseModelConfig(
                    use_case=LLMUseCase.ANSWER_GENERATION,
                    model_id=f"ollama/{settings.ollama_model_generation}",
                ),
                LLMUseCase.FOLLOWUP_TITLES: UseCaseModelConfig(
                    use_case=LLMUseCase.FOLLOWUP_TITLES,
                    model_id=f"ollama/{settings.ollama_model_generation}",
                ),
                LLMUseCase.QUERY_DECOMPOSITION: UseCaseModelConfig(
                    use_case=LLMUseCase.QUERY_DECOMPOSITION,
                    model_id=f"ollama/{settings.ollama_model_router}",
                ),
                LLMUseCase.VISION_VLM: UseCaseModelConfig(
                    use_case=LLMUseCase.VISION_VLM,
                    model_id=f"ollama/{settings.qwen3vl_model}",
                ),
            },
            version=1,
        )

    def _get_fallback_model(self, use_case: LLMUseCase) -> str:
        """Get fallback model from config.py when use case not configured.

        Safety net: If Redis config is corrupted or missing a use case,
        fall back to config.py defaults instead of crashing.

        Args:
            use_case: Use case enum

        Returns:
            Model name from config.py settings
        """
        from src.core.config import settings

        fallback_map = {
            LLMUseCase.INTENT_CLASSIFICATION: settings.ollama_model_router,
            LLMUseCase.ENTITY_EXTRACTION: settings.lightrag_llm_model,
            LLMUseCase.ANSWER_GENERATION: settings.ollama_model_generation,
            LLMUseCase.FOLLOWUP_TITLES: settings.ollama_model_generation,
            LLMUseCase.QUERY_DECOMPOSITION: settings.ollama_model_router,
            LLMUseCase.VISION_VLM: settings.qwen3vl_model,
        }
        return fallback_map.get(use_case, settings.ollama_model_generation)


# Singleton instance
_llm_config_service: LLMConfigService | None = None


def get_llm_config_service() -> LLMConfigService:
    """Get global LLM config service instance (singleton).

    Returns the same instance across all imports, ensuring config
    cache is shared and not duplicated.

    Returns:
        LLMConfigService singleton instance

    Example:
        >>> from src.components.llm_config import get_llm_config_service
        >>> service = get_llm_config_service()
        >>> model = await service.get_model_for_use_case(...)
    """
    global _llm_config_service
    if _llm_config_service is None:
        _llm_config_service = LLMConfigService()
    return _llm_config_service
