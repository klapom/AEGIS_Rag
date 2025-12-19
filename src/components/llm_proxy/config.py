"""
Configuration management for LLM proxy - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.config

Recommended import:
    from src.domains.llm_integration.config import LLMProxyConfig, get_llm_proxy_config
"""

# Re-export from domain location
from src.domains.llm_integration.config import (
    LLMProxyConfig,
    get_llm_proxy_config,
)

__all__ = [
    "LLMProxyConfig",
    "get_llm_proxy_config",
]
