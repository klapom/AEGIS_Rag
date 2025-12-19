"""
Configuration management for LLM proxy - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.config
OPL-006: These re-exports will be removed in Sprint 58.

Migrate to:
    from src.domains.llm_integration.config import LLMProxyConfig, get_llm_proxy_config
"""

# OPL-006: Re-export from new domain location
from src.domains.llm_integration.config import (
    LLMProxyConfig,
    get_llm_proxy_config,
)

__all__ = [
    "LLMProxyConfig",
    "get_llm_proxy_config",
]
