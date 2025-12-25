"""LLM Configuration Service.

Sprint 64 Feature 64.6: Centralized LLM Configuration Management

This module provides centralized LLM model configuration with Redis persistence,
eliminating the disconnect between Admin UI settings and backend usage.

Architecture:
    Admin UI (React) → HTTP API → LLMConfigService → Redis
                                       ↓ (fallback)
                                   config.py defaults

Components:
    - llm_config_service.py: Core service with Redis persistence and caching
    - LLMUseCase enum: Use case identifiers (intent_classification, entity_extraction, etc.)
    - LLMConfigService: Singleton service for config access

Example:
    >>> from src.components.llm_config import get_llm_config_service, LLMUseCase
    >>> service = get_llm_config_service()
    >>> model = await service.get_model_for_use_case(LLMUseCase.ENTITY_EXTRACTION)
    >>> print(model)  # "qwen3:32b" (from Admin UI config)

Features:
    - Redis persistence (hot-reloadable, no restart needed)
    - 60-second in-memory cache for performance
    - Automatic fallback to config.py if Redis unavailable
    - Atomic config updates
    - Migration from localStorage to backend

Sprint Context:
    - Sprint 64 Feature 64.6: Fix critical bug where domain training ignored Admin UI config
    - Replaces hardcoded settings.* with centralized config service
    - Affects 12+ backend files (router, answer generator, domain training, etc.)
"""

from src.components.llm_config.llm_config_service import (
    LLMConfigService,
    LLMUseCase,
    get_llm_config_service,
)

__all__ = [
    "LLMConfigService",
    "LLMUseCase",
    "get_llm_config_service",
]
