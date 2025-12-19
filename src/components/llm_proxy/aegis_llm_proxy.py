"""
AegisRAG LLM Proxy - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.proxy

Recommended import:
    from src.domains.llm_integration.proxy import AegisLLMProxy, get_aegis_llm_proxy
"""

# Re-export from domain location
from src.domains.llm_integration.proxy.aegis_llm_proxy import (
    AegisLLMProxy,
    get_aegis_llm_proxy,
)

__all__ = [
    "AegisLLMProxy",
    "get_aegis_llm_proxy",
]
