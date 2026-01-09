"""Generation Configuration Module.

TD-097: Sprint 80 Settings UI/DB Integration

Provides centralized access to answer generation configuration with Redis persistence.

Usage:
    from src.components.generation_config import get_generation_config_service

    service = get_generation_config_service()
    config = await service.get_config()
"""

from src.components.generation_config.generation_config_service import (
    GenerationConfig,
    GenerationConfigService,
    get_generation_config_service,
)

__all__ = [
    "GenerationConfig",
    "GenerationConfigService",
    "get_generation_config_service",
]
