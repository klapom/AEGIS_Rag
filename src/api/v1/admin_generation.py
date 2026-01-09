"""Admin Generation Configuration API endpoints.

TD-097: Sprint 80 Settings UI/DB Integration

This module provides endpoints for managing answer generation configuration:
- GET /admin/generation/config - Get current configuration
- POST /admin/generation/config - Update configuration

RAGAS Evaluation Results (Sprint 80 Experiment #5):
| Mode            | Faithfulness | Answer Relevancy | Use Case                    |
|-----------------|--------------|------------------|-----------------------------||
| strict=False    | 0.520        | 0.859            | General Q&A, Customer Support|
| strict=True     | 0.693 (+33%) | 0.621 (-28%)     | Legal, Medical, Academic    |
"""

import structlog
from fastapi import APIRouter, HTTPException, status

from src.components.generation_config import GenerationConfig, get_generation_config_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-generation"])


@router.get(
    "/generation/config",
    response_model=GenerationConfig,
    summary="Get answer generation configuration",
    description="Get current answer generation configuration from Redis (with 60s cache).",
)
async def get_generation_config() -> GenerationConfig:
    """Get current answer generation configuration.

    Returns:
        GenerationConfig with current settings

    Example:
        GET /api/v1/admin/generation/config
        {
            "strict_faithfulness_enabled": false,
            "graph_vector_fallback_enabled": true,
            "updated_at": "2026-01-09T12:00:00Z"
        }
    """
    try:
        service = get_generation_config_service()
        config = await service.get_config()

        logger.info(
            "admin_generation_config_get",
            strict_faithfulness=config.strict_faithfulness_enabled,
            graph_vector_fallback=config.graph_vector_fallback_enabled,
        )

        return config

    except Exception as e:
        logger.error("admin_generation_config_get_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get generation configuration: {e}",
        )


@router.post(
    "/generation/config",
    response_model=GenerationConfig,
    summary="Update answer generation configuration",
    description="Update answer generation configuration (saved to Redis, takes effect within 60s).",
)
async def update_generation_config(config: GenerationConfig) -> GenerationConfig:
    """Update answer generation configuration.

    Args:
        config: New generation configuration

    Returns:
        Saved configuration with updated timestamp

    Raises:
        HTTPException: If save fails

    Example:
        POST /api/v1/admin/generation/config
        {
            "strict_faithfulness_enabled": true,
            "graph_vector_fallback_enabled": true
        }
    """
    try:
        service = get_generation_config_service()
        saved_config = await service.save_config(config)

        logger.info(
            "admin_generation_config_updated",
            strict_faithfulness=saved_config.strict_faithfulness_enabled,
            graph_vector_fallback=saved_config.graph_vector_fallback_enabled,
        )

        return saved_config

    except Exception as e:
        logger.error("admin_generation_config_update_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update generation configuration: {e}",
        )


@router.get(
    "/generation/use-cases",
    summary="Get use case guidance for generation settings",
    description="Get recommendations for different use cases (General Q&A, Legal, Medical, etc.).",
)
async def get_generation_use_cases() -> dict:
    """Get use case guidance for generation settings.

    Returns:
        Dictionary with use case recommendations

    Example:
        GET /api/v1/admin/generation/use-cases
        {
            "use_cases": [
                {"name": "General Q&A", "strict_faithfulness": false, ...},
                ...
            ]
        }
    """
    use_cases = [
        {
            "name": "General Q&A",
            "strict_faithfulness": False,
            "description": "Balance of Faithfulness (F=0.52) and Answer Relevancy (AR=0.86). Best for conversational queries.",
            "recommended_for": ["customer support", "chatbots", "general information"],
        },
        {
            "name": "Research / Academic",
            "strict_faithfulness": True,
            "description": "Higher Faithfulness (F=0.69), every claim cited. Essential for verifiable answers.",
            "recommended_for": ["research papers", "academic writing", "fact-checking"],
        },
        {
            "name": "Legal / Compliance",
            "strict_faithfulness": True,
            "description": "Faithfulness > Relevancy for risk mitigation. No unsourced claims allowed.",
            "recommended_for": ["legal documents", "compliance checks", "regulatory"],
        },
        {
            "name": "Medical / Healthcare",
            "strict_faithfulness": True,
            "description": "Patient safety requires cited sources only.",
            "recommended_for": ["medical literature", "patient information", "clinical"],
        },
        {
            "name": "Financial / Audit",
            "strict_faithfulness": True,
            "description": "Regulatory compliance requires traceable claims.",
            "recommended_for": ["financial reports", "audit trails", "investment"],
        },
        {
            "name": "Technical Documentation",
            "strict_faithfulness": True,
            "description": "Precise, verifiable technical information required.",
            "recommended_for": ["API docs", "technical manuals", "specifications"],
        },
    ]

    logger.info("admin_generation_use_cases_get", use_case_count=len(use_cases))

    return {"use_cases": use_cases}
