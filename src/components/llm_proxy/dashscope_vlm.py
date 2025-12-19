"""DashScope VLM Client - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.proxy

Recommended import:
    from src.domains.llm_integration.proxy.dashscope_vlm import (
        DashScopeVLMClient, get_dashscope_vlm_client
    )
"""

# Re-export from domain location
from src.domains.llm_integration.proxy.dashscope_vlm import (
    DashScopeVLMClient,
    get_dashscope_vlm_client,
)

__all__ = [
    "DashScopeVLMClient",
    "get_dashscope_vlm_client",
]
