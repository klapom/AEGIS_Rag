"""
AegisRAG LLM Proxy - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.proxy
OPL-006: These re-exports will be removed in Sprint 58.

Migrate to:
    from src.domains.llm_integration.proxy import AegisLLMProxy, get_aegis_llm_proxy
"""

# OPL-006: Re-export from new domain location
from src.domains.llm_integration.proxy.aegis_llm_proxy import (
    AegisLLMProxy,
    get_aegis_llm_proxy,
)

__all__ = [
    "AegisLLMProxy",
    "get_aegis_llm_proxy",
]
