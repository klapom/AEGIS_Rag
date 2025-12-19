"""VLM Factory Pattern - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.proxy
OPL-006: These re-exports will be removed in Sprint 58.

Migrate to:
    from src.domains.llm_integration.proxy import get_vlm_client, VLMBackend
"""

# OPL-006: Re-export from new domain location
from src.domains.llm_integration.proxy import (
    VLMBackend,
    VLMClient,
    close_shared_vlm_client,
    get_shared_vlm_client,
    get_vlm_backend_from_config,
    get_vlm_client,
    reset_vlm_client,
)

__all__ = [
    "VLMBackend",
    "VLMClient",
    "get_vlm_client",
    "get_vlm_backend_from_config",
    "get_shared_vlm_client",
    "close_shared_vlm_client",
    "reset_vlm_client",
]
