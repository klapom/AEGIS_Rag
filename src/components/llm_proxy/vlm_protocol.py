"""VLM Client Protocol Definition - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.proxy
OPL-006: These re-exports will be removed in Sprint 58.

Migrate to:
    from src.domains.llm_integration.proxy import VLMClient
"""

# OPL-006: Re-export from new domain location
from src.domains.llm_integration.proxy.vlm_protocol import VLMClient

__all__ = ["VLMClient"]
