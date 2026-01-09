"""Chunking Configuration Module.

TD-096: Chunking Parameters UI Integration

Provides centralized access to chunking configuration with Redis persistence and caching.

Usage:
    from src.components.chunking_config import get_chunking_config_service

    service = get_chunking_config_service()
    config = await service.get_config()
"""

from src.components.chunking_config.chunking_config_service import (
    ChunkingConfig,
    ChunkingConfigService,
    get_chunking_config_service,
)

__all__ = [
    "ChunkingConfig",
    "ChunkingConfigService",
    "get_chunking_config_service",
]
