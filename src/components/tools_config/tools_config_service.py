"""Tools Configuration Service.

Sprint 70 Feature 70.7: Tool Use Configuration Service

Provides centralized access to tool configuration with Redis persistence and caching.

Architecture:
- Redis as single source of truth (key: "admin:tools_config")
- In-memory cache with TTL for performance (60s cache)
- Lazy loading on first access
- Thread-safe singleton pattern

Usage:
    service = get_tools_config_service()
    config = await service.get_config()

    if config.enable_chat_tools:
        graph = create_base_graph(enable_tools=True)
"""

import json
from datetime import datetime, timedelta
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.core.config import settings

logger = structlog.get_logger(__name__)

# Redis key for tool configuration (matches admin_tools.py)
REDIS_KEY_TOOLS_CONFIG = "admin:tools_config"

# Cache TTL (60 seconds for hot-reload)
CACHE_TTL_SECONDS = 60


class ToolsConfig(BaseModel):
    """Tool use configuration schema.

    Sprint 70 Feature 70.11: LLM-based Tool Detection

    Attributes:
        enable_chat_tools: Enable MCP tool use in normal chat
        enable_research_tools: Enable MCP tool use in deep research
        tool_detection_strategy: Strategy for detecting when to use tools
            - "markers": Fast marker-based detection (legacy, ~0ms)
            - "llm": LLM-based intelligent detection (smart, +50-200ms)
            - "hybrid": Markers first, LLM fallback (balanced)
        explicit_tool_markers: List of explicit markers triggering tool use (e.g., "[TOOL:", "[SEARCH:")
        action_hint_phrases: List of phrases suggesting tool use (for hybrid mode)
        updated_at: ISO 8601 timestamp of last update
        version: Config schema version
    """

    enable_chat_tools: bool = Field(default=False, description="Enable tools in chat")
    enable_research_tools: bool = Field(default=False, description="Enable tools in research")

    # Sprint 70 Feature 70.11: Tool Detection Strategy
    tool_detection_strategy: str = Field(
        default="markers", description="Detection strategy: 'markers', 'llm', or 'hybrid'"
    )
    explicit_tool_markers: list[str] = Field(
        default_factory=lambda: ["[TOOL:", "[SEARCH:", "[FETCH:"],
        description="Explicit markers triggering immediate tool use",
    )
    action_hint_phrases: list[str] = Field(
        default_factory=lambda: [
            "need to",
            "haben zu",
            "muss",  # Multilingual support
            "check",
            "search",
            "look up",
            "prüfen",
            "suchen",
            "current",
            "latest",
            "aktuell",
            "aktuell",
            "I'll need to access",
            "Let me check",
        ],
        description="Phrases suggesting potential tool use (triggers LLM decision in hybrid mode)",
    )

    updated_at: str | None = Field(None, description="Last update timestamp")
    version: int = Field(default=2, description="Config version")


class ToolsConfigService:
    """Service for managing tool use configuration.

    Provides:
    - get_config(): Get current configuration (cached)
    - save_config(): Save configuration to Redis (invalidates cache)
    - clear_cache(): Force cache invalidation
    """

    def __init__(self) -> None:
        """Initialize service with empty cache."""
        self._cache: ToolsConfig | None = None
        self._cache_expires_at: datetime | None = None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None or self._cache_expires_at is None:
            return False
        return datetime.now() < self._cache_expires_at

    async def get_config(self) -> ToolsConfig:
        """Get current tool configuration.

        Returns cached config if valid, otherwise loads from Redis.

        Returns:
            ToolsConfig with current settings

        Example:
            >>> service = get_tools_config_service()
            >>> config = await service.get_config()
            >>> print(config.enable_chat_tools)
            False
        """
        # Return cached config if valid
        if self._is_cache_valid() and self._cache is not None:
            logger.debug("tools_config_cache_hit")
            return self._cache

        # Load from Redis
        try:
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            config_json = await redis_client.get(REDIS_KEY_TOOLS_CONFIG)

            if config_json:
                config_str = (
                    config_json.decode("utf-8") if isinstance(config_json, bytes) else config_json
                )
                config_dict = json.loads(config_str)
                config = ToolsConfig(**config_dict)

                logger.info(
                    "tools_config_loaded_from_redis",
                    enable_chat=config.enable_chat_tools,
                    enable_research=config.enable_research_tools,
                )

                # Cache for 60 seconds
                self._cache = config
                self._cache_expires_at = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)

                return config

            # No config in Redis - return defaults
            logger.info("tools_config_using_defaults")
            default_config = ToolsConfig()

            # Cache defaults
            self._cache = default_config
            self._cache_expires_at = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)

            return default_config

        except Exception as e:
            logger.error("failed_to_load_tools_config", error=str(e), exc_info=True)

            # Return defaults on error (fail-safe: tools disabled)
            return ToolsConfig()

    async def save_config(self, config: ToolsConfig) -> ToolsConfig:
        """Save tool configuration to Redis.

        Invalidates cache immediately so next read gets fresh config.

        Args:
            config: ToolsConfig to save

        Returns:
            Saved configuration with updated timestamp

        Raises:
            Exception: If Redis save fails

        Example:
            >>> service = get_tools_config_service()
            >>> config = ToolsConfig(enable_chat_tools=True)
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
            await redis_client.set(REDIS_KEY_TOOLS_CONFIG, config_json)

            logger.info(
                "tools_config_saved_to_redis",
                enable_chat=config.enable_chat_tools,
                enable_research=config.enable_research_tools,
                updated_at=config.updated_at,
            )

            # Invalidate cache
            self.clear_cache()

            return config

        except Exception as e:
            logger.error("failed_to_save_tools_config", error=str(e), exc_info=True)
            raise

    def clear_cache(self) -> None:
        """Clear configuration cache.

        Forces next get_config() call to reload from Redis.

        Example:
            >>> service = get_tools_config_service()
            >>> service.clear_cache()
        """
        self._cache = None
        self._cache_expires_at = None
        logger.debug("tools_config_cache_cleared")


# Singleton instance
_tools_config_service: ToolsConfigService | None = None


def get_tools_config_service() -> ToolsConfigService:
    """Get singleton ToolsConfigService instance.

    Returns:
        ToolsConfigService singleton

    Example:
        >>> service = get_tools_config_service()
        >>> service is get_tools_config_service()
        True
    """
    global _tools_config_service
    if _tools_config_service is None:
        _tools_config_service = ToolsConfigService()
    return _tools_config_service
