"""DashScope VLM Client - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.proxy
OPL-006: These re-exports will be removed in Sprint 58.

Migrate to:
    from src.domains.llm_integration.proxy.dashscope_vlm import (
        DashScopeVLMClient, get_dashscope_vlm_client
    )
"""

# OPL-006: Re-export from new domain location
from src.domains.llm_integration.proxy.dashscope_vlm import (
    DashScopeVLMClient,
    get_dashscope_vlm_client,
)

__all__ = [
    "DashScopeVLMClient",
    "get_dashscope_vlm_client",
]
