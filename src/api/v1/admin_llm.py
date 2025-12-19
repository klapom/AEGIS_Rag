"""Admin LLM Configuration API endpoints.

Sprint 51: LLM Model Management
Sprint 52 Feature 52.1: Community Summary Model Configuration
Sprint 53 Feature 53.5: Extracted from admin.py

This module provides endpoints for:
- Listing available Ollama models
- Managing community summary model configuration
"""

from datetime import datetime

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.components.graph_rag.llm_config_provider import REDIS_KEY_SUMMARY_MODEL_CONFIG
from src.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-llm"])


# ============================================================================
# Pydantic Models
# ============================================================================


class OllamaModel(BaseModel):
    """Information about an Ollama model."""

    name: str = Field(..., description="Model name (e.g., 'qwen3:8b')")
    size: int = Field(..., description="Model size in bytes")
    digest: str = Field(..., description="Model digest/hash")
    modified_at: str = Field(..., description="Last modified timestamp")


class OllamaModelsResponse(BaseModel):
    """Response containing list of available Ollama models."""

    models: list[OllamaModel] = Field(default_factory=list, description="List of available models")
    ollama_available: bool = Field(..., description="Whether Ollama is reachable")
    error: str | None = Field(None, description="Error message if Ollama is not available")


class SummaryModelConfig(BaseModel):
    """Configuration for community summary generation model.

    Sprint 52 Feature 52.1: Admin LLM Config - Community Summary Model Selection

    This schema defines the model to use for generating community summaries
    in the LightRAG global search mode.
    """

    model_id: str = Field(
        default="ollama/qwen3:32b",
        description="Model ID for community summary generation (format: provider/model_name)",
    )
    updated_at: str | None = Field(None, description="ISO 8601 timestamp of last update")

    model_config = {
        "json_schema_extra": {
            "example": {
                "model_id": "ollama/qwen3:32b",
                "updated_at": "2025-12-18T10:30:00Z",
            }
        }
    }


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/llm/models",
    response_model=OllamaModelsResponse,
    summary="List available Ollama models",
    description="Fetch all locally installed Ollama models for LLM configuration",
)
async def list_ollama_models() -> OllamaModelsResponse:
    """List all available Ollama models.

    **Sprint 51: LLM Configuration Enhancement**

    Queries the local Ollama instance to get a list of all installed models.
    This endpoint is used by the LLM Configuration page to dynamically
    populate model selection dropdowns.

    Returns:
        OllamaModelsResponse with list of models or error info
    """
    ollama_url = settings.ollama_base_url or "http://localhost:11434"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            response.raise_for_status()
            data = response.json()

            models = [
                OllamaModel(
                    name=m.get("name", ""),
                    size=m.get("size", 0),
                    digest=m.get("digest", ""),
                    modified_at=m.get("modified_at", ""),
                )
                for m in data.get("models", [])
            ]

            logger.info("ollama_models_listed", count=len(models))

            return OllamaModelsResponse(
                models=models,
                ollama_available=True,
                error=None,
            )

    except httpx.ConnectError as e:
        logger.warning("ollama_not_reachable", error=str(e))
        return OllamaModelsResponse(
            models=[],
            ollama_available=False,
            error=f"Ollama not reachable at {ollama_url}",
        )
    except Exception as e:
        logger.error("ollama_models_fetch_failed", error=str(e), exc_info=True)
        return OllamaModelsResponse(
            models=[],
            ollama_available=False,
            error=str(e),
        )


@router.get(
    "/llm/summary-model",
    response_model=SummaryModelConfig,
    summary="Get community summary model configuration",
    description="Get the currently configured LLM model for community summary generation",
)
async def get_summary_model_config() -> SummaryModelConfig:
    """Get current community summary model configuration.

    **Sprint 52 Feature 52.1: Community Summary Model Selection**

    Returns the configured model for generating community summaries.
    If not configured, returns the default model (ollama/qwen3:32b).

    Returns:
        SummaryModelConfig with current model selection
    """
    import json

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
            logger.info("summary_model_config_loaded", model_id=config_dict.get("model_id"))
            return SummaryModelConfig(**config_dict)

        # Return default if not configured
        logger.info("summary_model_config_using_default")
        return SummaryModelConfig()

    except Exception as e:
        logger.warning("failed_to_load_summary_model_config", error=str(e))
        return SummaryModelConfig()


@router.put(
    "/llm/summary-model",
    response_model=SummaryModelConfig,
    summary="Update community summary model configuration",
    description="Set the LLM model to use for community summary generation",
)
async def update_summary_model_config(config: SummaryModelConfig) -> SummaryModelConfig:
    """Update community summary model configuration.

    **Sprint 52 Feature 52.1: Community Summary Model Selection**

    Saves the selected model for community summary generation to Redis.
    The configuration persists across restarts and is used by the
    CommunitySummarizer when generating summaries for LightRAG global mode.

    Args:
        config: SummaryModelConfig with model selection

    Returns:
        Updated configuration (validated and persisted)

    Raises:
        HTTPException 500: If Redis save fails
    """
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        redis_client = await redis_memory.client

        # Add timestamp
        config.updated_at = datetime.now().isoformat()

        # Save to Redis
        config_json = config.model_dump_json()
        await redis_client.set(REDIS_KEY_SUMMARY_MODEL_CONFIG, config_json)

        logger.info(
            "summary_model_config_saved",
            model_id=config.model_id,
            updated_at=config.updated_at,
        )

        return config

    except Exception as e:
        logger.error("failed_to_save_summary_model_config", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save summary model configuration: {str(e)}",
        ) from e
