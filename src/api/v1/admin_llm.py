"""Admin LLM Configuration API endpoints.

Sprint 51: LLM Model Management
Sprint 52 Feature 52.1: Community Summary Model Configuration
Sprint 53 Feature 53.5: Extracted from admin.py

This module provides endpoints for:
- Listing available Ollama models
- Managing community summary model configuration
"""

from datetime import datetime
from enum import Enum

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


# Sprint 64 Feature 64.6: Full LLM Configuration Models
# Centralized LLM config for all use cases (replaces localStorage-only approach)


class LLMUseCase(str, Enum):
    """LLM use case identifiers.

    Sprint 64 Feature 64.6: Use case enum matching frontend AdminLLMConfigPage.tsx

    These values MUST match frontend exactly for proper sync.
    """

    INTENT_CLASSIFICATION = "intent_classification"
    ENTITY_EXTRACTION = "entity_extraction"
    ANSWER_GENERATION = "answer_generation"
    FOLLOWUP_TITLES = "followup_titles"
    QUERY_DECOMPOSITION = "query_decomposition"
    VISION_VLM = "vision_vlm"


class UseCaseModelConfigAPI(BaseModel):
    """Model configuration for a specific use case (API schema).

    Sprint 64 Feature 64.6: Pydantic schema for API validation

    This is the API-layer version (with Pydantic validation).
    The service layer uses a lighter version to avoid circular imports.

    Attributes:
        use_case: Use case identifier (enum)
        model_id: Model ID in format "provider/model_name" (e.g., "ollama/qwen3:32b")
        enabled: Whether this use case is active
        updated_at: ISO 8601 timestamp of last update
    """

    use_case: LLMUseCase = Field(..., description="Use case identifier")
    model_id: str = Field(
        ...,
        description="Model ID (format: provider/model_name, e.g., 'ollama/qwen3:32b')",
    )
    enabled: bool = Field(default=True, description="Whether use case is enabled")
    updated_at: str | None = Field(None, description="ISO 8601 timestamp of last update")

    model_config = {
        "json_schema_extra": {
            "example": {
                "use_case": "entity_extraction",
                "model_id": "ollama/qwen3:32b",
                "enabled": True,
                "updated_at": "2025-12-25T10:30:00Z",
            }
        }
    }


class LLMConfigAPI(BaseModel):
    """Complete LLM configuration for all use cases (API schema).

    Sprint 64 Feature 64.6: Unified config for all 6 use cases

    This replaces the fragmented approach where:
    - Frontend stored config in localStorage (not persisted)
    - Backend used hardcoded settings.* values (ignored Admin UI)

    Now all use cases are managed centrally:
    - Persisted in Redis (key: "admin:llm_config")
    - Hot-reloadable (no restart needed)
    - 60s cache for performance

    Attributes:
        use_cases: Dict mapping use case to model config (all 6 use cases)
        version: Config schema version (for future migrations)
        updated_at: ISO 8601 timestamp of last update
    """

    use_cases: dict[LLMUseCase, UseCaseModelConfigAPI] = Field(
        ...,
        description="Map of use case to model configuration (6 use cases total)",
    )
    version: int = Field(default=1, description="Config schema version")
    updated_at: str | None = Field(None, description="ISO 8601 timestamp of last config update")

    model_config = {
        "json_schema_extra": {
            "example": {
                "use_cases": {
                    "intent_classification": {
                        "use_case": "intent_classification",
                        "model_id": "ollama/qwen3:32b",
                        "enabled": True,
                    },
                    "entity_extraction": {
                        "use_case": "entity_extraction",
                        "model_id": "ollama/qwen3:32b",
                        "enabled": True,
                    },
                    # ... (4 more use cases)
                },
                "version": 1,
                "updated_at": "2025-12-25T10:30:00Z",
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


# Sprint 64 Feature 64.6: Full LLM Configuration Endpoints
# Centralized config API for all use cases


@router.get(
    "/llm/config",
    response_model=LLMConfigAPI,
    summary="Get full LLM configuration",
    description="Get LLM model configuration for all 6 use cases (persisted in Redis)",
)
async def get_llm_config() -> LLMConfigAPI:
    """Get complete LLM configuration for all use cases.

    **Sprint 64 Feature 64.6: Full LLM Config API**

    Returns all use case model configurations from Redis. If not configured,
    returns defaults migrated from config.py settings.

    This endpoint fixes the critical disconnect where:
    - Admin UI stored config in localStorage (browser-only, not persisted)
    - Backend used hardcoded settings.* values (ignored Admin UI selections)

    Now backend reads from the same source as Admin UI configures.

    Returns:
        LLMConfigAPI with all 6 use case configurations

    Example Response:
        {
            "use_cases": {
                "intent_classification": {"model_id": "ollama/qwen3:32b", ...},
                "entity_extraction": {"model_id": "ollama/qwen3:32b", ...},
                "answer_generation": {"model_id": "ollama/qwen3:32b", ...},
                "followup_titles": {"model_id": "ollama/qwen3:32b", ...},
                "query_decomposition": {"model_id": "ollama/qwen3:32b", ...},
                "vision_vlm": {"model_id": "ollama/qwen3-vl:32b", ...}
            },
            "version": 1,
            "updated_at": "2025-12-25T10:30:00Z"
        }
    """
    try:
        from src.components.llm_config import get_llm_config_service

        service = get_llm_config_service()
        config = await service.get_config()

        # Convert service model to API model
        use_cases_api = {
            uc: UseCaseModelConfigAPI(
                use_case=LLMUseCase(uc_config.use_case.value),
                model_id=uc_config.model_id,
                enabled=uc_config.enabled,
                updated_at=uc_config.updated_at,
            )
            for uc, uc_config in config.use_cases.items()
        }

        logger.info("llm_config_retrieved", use_cases_count=len(use_cases_api))

        return LLMConfigAPI(
            use_cases=use_cases_api,
            version=config.version,
            updated_at=config.updated_at,
        )

    except Exception as e:
        logger.error("llm_config_get_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve LLM configuration: {str(e)}",
        ) from e


@router.put(
    "/llm/config",
    response_model=LLMConfigAPI,
    summary="Update full LLM configuration",
    description="Update LLM model configuration for all 6 use cases (persists to Redis)",
)
async def update_llm_config(config_update: LLMConfigAPI) -> LLMConfigAPI:
    """Update complete LLM configuration for all use cases.

    **Sprint 64 Feature 64.6: Full LLM Config API**

    Validates and saves all use case configurations to Redis. Config takes
    effect immediately via cache invalidation (no service restart needed).

    This endpoint enables Admin UI to persist config to backend, fixing the
    critical bug where backend ignored Admin UI selections.

    Args:
        config_update: Complete LLM configuration with all 6 use cases

    Returns:
        Updated configuration with timestamps

    Raises:
        HTTPException 500: If Redis save fails

    Example Request:
        PUT /api/v1/admin/llm/config
        {
            "use_cases": {
                "entity_extraction": {
                    "use_case": "entity_extraction",
                    "model_id": "ollama/llama3.2:8b",  // Change from qwen3:32b
                    "enabled": true
                }
                // ... other 5 use cases
            },
            "version": 1
        }

    Sprint 64 Context:
        After this call, domain training will use "llama3.2:8b" instead of
        hardcoded "nemotron-3-nano" from config.py. Config takes effect within 60s.
    """
    try:
        from src.components.llm_config import get_llm_config_service
        from src.components.llm_config.llm_config_service import (
            LLMConfig,
            UseCaseModelConfig,
        )
        from src.components.llm_config.llm_config_service import (
            LLMUseCase as ServiceLLMUseCase,
        )

        service = get_llm_config_service()

        # Convert API model to service model
        use_cases_service = {
            ServiceLLMUseCase(uc.value): UseCaseModelConfig(
                use_case=ServiceLLMUseCase(uc_config.use_case.value),
                model_id=uc_config.model_id,
                enabled=uc_config.enabled,
                updated_at=uc_config.updated_at,
            )
            for uc, uc_config in config_update.use_cases.items()
        }

        service_config = LLMConfig(
            use_cases=use_cases_service,
            version=config_update.version,
            updated_at=config_update.updated_at,
        )

        # Save to Redis (invalidates cache immediately)
        await service.save_config(service_config)

        logger.info(
            "llm_config_updated",
            use_cases_count=len(service_config.use_cases),
            version=service_config.version,
        )

        # Convert back to API model for response
        use_cases_api = {
            uc: UseCaseModelConfigAPI(
                use_case=LLMUseCase(uc_config.use_case.value),
                model_id=uc_config.model_id,
                enabled=uc_config.enabled,
                updated_at=uc_config.updated_at,
            )
            for uc, uc_config in service_config.use_cases.items()
        }

        return LLMConfigAPI(
            use_cases=use_cases_api,
            version=service_config.version,
            updated_at=service_config.updated_at,
        )

    except Exception as e:
        logger.error("llm_config_update_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update LLM configuration: {str(e)}",
        ) from e
