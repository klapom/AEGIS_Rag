"""Admin Chunking Configuration API endpoints.

TD-096: Chunking Parameters UI Integration

This module provides endpoints for managing chunking configuration:
- GET /admin/chunking/config - Get current configuration
- POST /admin/chunking/config - Update configuration
- GET /admin/chunking/presets - Get preset configurations

Based on GraphRAG best practices:
- Chunk 200-400 + Gleaning 2: High precision, noisy PDFs
- Chunk 800-1200 + Gleaning 1: Default (best recall/time ratio)
- Chunk 1200-1500 + Gleaning 0-1: Fast throughput, structured domains
"""

import structlog
from fastapi import APIRouter, HTTPException, status

from src.components.chunking_config import ChunkingConfig, get_chunking_config_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-chunking"])


@router.get(
    "/chunking/config",
    response_model=ChunkingConfig,
    summary="Get chunking configuration",
    description="Get current chunking configuration from Redis (with 60s cache).",
)
async def get_chunking_config() -> ChunkingConfig:
    """Get current chunking configuration.

    Returns:
        ChunkingConfig with current settings

    Example:
        GET /api/v1/admin/chunking/config
        {
            "chunk_size": 1200,
            "overlap": 100,
            "gleaning_steps": 0,
            "max_hard_limit": 1500,
            "updated_at": "2026-01-09T12:00:00Z"
        }
    """
    try:
        service = get_chunking_config_service()
        config = await service.get_config()

        logger.info(
            "admin_chunking_config_get",
            chunk_size=config.chunk_size,
            overlap=config.overlap,
        )

        return config

    except Exception as e:
        logger.error("admin_chunking_config_get_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chunking configuration: {e}",
        )


@router.post(
    "/chunking/config",
    response_model=ChunkingConfig,
    summary="Update chunking configuration",
    description="Update chunking configuration (saved to Redis, takes effect within 60s).",
)
async def update_chunking_config(config: ChunkingConfig) -> ChunkingConfig:
    """Update chunking configuration.

    Args:
        config: New chunking configuration

    Returns:
        Saved configuration with updated timestamp

    Raises:
        HTTPException: If validation or save fails

    Example:
        POST /api/v1/admin/chunking/config
        {
            "chunk_size": 800,
            "overlap": 100,
            "gleaning_steps": 1,
            "max_hard_limit": 1200
        }
    """
    try:
        service = get_chunking_config_service()
        saved_config = await service.save_config(config)

        logger.info(
            "admin_chunking_config_updated",
            chunk_size=saved_config.chunk_size,
            overlap=saved_config.overlap,
            gleaning_steps=saved_config.gleaning_steps,
            max_hard_limit=saved_config.max_hard_limit,
        )

        return saved_config

    except ValueError as e:
        logger.warning("admin_chunking_config_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error("admin_chunking_config_update_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chunking configuration: {e}",
        )


@router.get(
    "/chunking/presets",
    summary="Get chunking presets",
    description="Get preset configurations based on GraphRAG best practices.",
)
async def get_chunking_presets() -> dict:
    """Get preset configurations.

    Returns:
        Dictionary with preset configurations:
        - high_precision: Small chunks, high gleaning (best recall, slower)
        - balanced: GraphRAG recommended settings
        - fast_throughput: Larger chunks, no gleaning (faster, lower recall)

    Example:
        GET /api/v1/admin/chunking/presets
        {
            "presets": {
                "high_precision": {...},
                "balanced": {...},
                "fast_throughput": {...}
            }
        }
    """
    try:
        service = get_chunking_config_service()
        presets = service.get_presets()

        logger.info("admin_chunking_presets_get", preset_count=len(presets))

        return {"presets": presets}

    except Exception as e:
        logger.error("admin_chunking_presets_get_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chunking presets: {e}",
        )
