"""LLM Configuration Provider for Graph Components.

Sprint 53 Feature 53.1: Extract LLM config logic from admin.py to break
circular dependency: admin -> community_summarizer -> admin.

This module provides functions to read LLM configuration from Redis,
used primarily by CommunitySummarizer for model selection.

Author: Claude Code
Date: 2025-12-19
"""

import json

import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)

# Redis key for community summary model configuration
REDIS_KEY_SUMMARY_MODEL_CONFIG = "admin:summary_model_config"


async def get_configured_summary_model() -> str:
    """Get the configured summary model name for use in CommunitySummarizer.

    Sprint 52 Feature 52.1: Community Summary Model Selection
    Sprint 53 Feature 53.1: Moved from admin.py to break circular dependency

    This function reads the summary model configuration from Redis.
    Returns just the model name without the provider prefix
    (e.g., "qwen3:32b" instead of "ollama/qwen3:32b").

    Returns:
        Model name string (without provider prefix)

    Example:
        >>> model = await get_configured_summary_model()
        >>> print(model)  # "llama3.2:8b"
    """
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        redis_client = await redis_memory.client

        config_json = await redis_client.get(REDIS_KEY_SUMMARY_MODEL_CONFIG)

        if config_json:
            config_str = (
                config_json.decode("utf-8") if isinstance(config_json, bytes) else config_json
            )
            config_dict = json.loads(config_str)
            model_id = config_dict.get("model_id", "")

            # Extract model name (remove provider prefix like "ollama/")
            if "/" in model_id:
                return model_id.split("/", 1)[1]
            return model_id

        # Return default from settings
        return settings.ollama_model_generation

    except Exception as e:
        logger.warning("failed_to_get_configured_summary_model", error=str(e))
        return settings.ollama_model_generation


async def get_configured_extraction_model() -> str:
    """Get the configured model for entity extraction.

    Sprint 53 Feature 53.1: Placeholder for future expansion.
    Currently returns default from settings.

    Returns:
        Model name string for extraction tasks
    """
    # TODO: Implement Redis-based config when needed
    return settings.ollama_model_generation
