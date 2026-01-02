"""Admin Tools Configuration API endpoints.

Sprint 70 Feature 70.7: Tool Use Configuration Management
Sprint 70 Feature 70.11: LLM-based Tool Detection

This module provides endpoints for:
- Enabling/disabling tool use in Normal Chat
- Enabling/disabling tool use in Deep Research
- Configuring tool detection strategy (markers, LLM, hybrid)
- Managing explicit tool markers and action hint phrases
- Persisting configuration to Redis for hot-reload
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, status

from src.components.tools_config import ToolsConfig
from src.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-tools"])

# Redis key for tool configuration
REDIS_KEY_TOOLS_CONFIG = "admin:tools_config"


# ============================================================================
# Endpoints (using ToolsConfig from tools_config_service)
# ============================================================================


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/tools/config",
    response_model=ToolsConfig,
    summary="Get tool use configuration",
    description="Get current configuration for MCP tool use in chat and research modes",
)
async def get_tools_config() -> ToolsConfig:
    """Get current tool use configuration.

    **Sprint 70 Feature 70.7: Tool Use Configuration**

    Returns the configuration for whether MCP tools are enabled in:
    - Normal chat conversations (ReAct pattern)
    - Deep research mode (ReAct pattern in research graph)

    If not configured, returns defaults (both disabled for safety).

    Returns:
        ToolsConfig with current tool enablement settings

    Example Response:
        {
            "enable_chat_tools": true,
            "enable_research_tools": false,
            "updated_at": "2025-12-25T10:30:00Z",
            "version": 1
        }
    """
    import json

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
            logger.info(
                "tools_config_loaded",
                enable_chat=config_dict.get("enable_chat_tools"),
                enable_research=config_dict.get("enable_research_tools"),
            )
            return ToolsConfig(**config_dict)

        # Return default (tools disabled) if not configured
        logger.info("tools_config_using_default", enable_chat=False, enable_research=False)
        return ToolsConfig()

    except Exception as e:
        logger.warning("failed_to_load_tools_config", error=str(e))
        # Return safe defaults on error (tools disabled)
        return ToolsConfig()


@router.put(
    "/tools/config",
    response_model=ToolsConfig,
    summary="Update tool use configuration",
    description="Enable or disable MCP tool use in chat and research modes",
)
async def update_tools_config(config: ToolsConfig) -> ToolsConfig:
    """Update tool use configuration.

    **Sprint 70 Feature 70.7: Tool Use Configuration**

    Saves the tool enablement configuration to Redis. Changes take effect
    immediately for new graph instances (hot-reload, no service restart needed).

    This allows admins to:
    - Enable/disable tools in normal chat (e.g., web search, file access)
    - Enable/disable tools in deep research (e.g., external data fetching)
    - Control tool access without code changes

    Args:
        config: ToolsConfig with enablement flags

    Returns:
        Updated configuration (validated and persisted)

    Raises:
        HTTPException 500: If Redis save fails

    Example Request:
        PUT /api/v1/admin/tools/config
        {
            "enable_chat_tools": true,
            "enable_research_tools": true
        }

    Sprint 70 Context:
        After this call:
        - create_base_graph() will use enable_tools=config.enable_chat_tools
        - create_research_graph() will use enable_tools=config.enable_research_tools
        - Changes apply to new conversations immediately
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
            "tools_config_saved",
            enable_chat=config.enable_chat_tools,
            enable_research=config.enable_research_tools,
            updated_at=config.updated_at,
        )

        return config

    except Exception as e:
        logger.error("failed_to_save_tools_config", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save tool configuration: {str(e)}",
        ) from e
