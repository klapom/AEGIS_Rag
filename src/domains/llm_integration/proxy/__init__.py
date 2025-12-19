"""AegisLLMProxy - Multi-Cloud LLM Integration.

Sprint 56: Proxy subdomain of llm_integration.

Provides intelligent LLM routing with:
- Three-tier execution (Local → Alibaba Cloud → OpenAI)
- Data privacy enforcement (PII/HIPAA → local only)
- Cost optimization and tracking

Usage:
    from src.domains.llm_integration.proxy import get_aegis_llm_proxy, AegisLLMProxy
    from src.domains.llm_integration.proxy import get_vlm_client, VLMBackend

    proxy = get_aegis_llm_proxy()
    response = await proxy.generate(task)
"""

from src.domains.llm_integration.proxy.aegis_llm_proxy import (
    AegisLLMProxy,
    get_aegis_llm_proxy,
)
from src.domains.llm_integration.proxy.vlm_factory import (
    VLMBackend,
    close_shared_vlm_client,
    get_shared_vlm_client,
    get_vlm_backend_from_config,
    get_vlm_client,
    reset_vlm_client,
)
from src.domains.llm_integration.proxy.vlm_protocol import VLMClient

__all__ = [
    # Main proxy
    "AegisLLMProxy",
    "get_aegis_llm_proxy",
    # VLM Factory
    "VLMBackend",
    "VLMClient",
    "get_vlm_client",
    "get_vlm_backend_from_config",
    "get_shared_vlm_client",
    "close_shared_vlm_client",
    "reset_vlm_client",
]
