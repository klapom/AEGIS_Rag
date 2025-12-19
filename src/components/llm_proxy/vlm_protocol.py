"""VLM Client Protocol Definition - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.proxy

Recommended import:
    from src.domains.llm_integration.proxy import VLMClient
"""

# Re-export from domain location
from src.domains.llm_integration.proxy.vlm_protocol import VLMClient

__all__ = ["VLMClient"]
