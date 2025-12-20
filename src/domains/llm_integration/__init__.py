"""LLM Integration Domain - Public API.

Sprint 56: Domain boundary for LLM provisioning.

Subdomains:
- proxy: AegisLLMProxy (multi-cloud routing)
- cost: Cost tracking and budget management

Usage:
    from src.domains.llm_integration import (
        get_aegis_llm_proxy,
        AegisLLMProxy,
        LLMTask,
        LLMResponse,
        TaskType,
    )

    proxy = get_aegis_llm_proxy()
    task = LLMTask(task_type=TaskType.EXTRACTION, prompt="...")
    response = await proxy.generate(task)
"""

# Protocols (Sprint 57)
# Configuration
from src.domains.llm_integration.config import (
    LLMProxyConfig,
    get_llm_proxy_config,
)

# Cost tracking
from src.domains.llm_integration.cost import (
    CostTracker,
    get_cost_tracker,
)

# Models (data structures)
from src.domains.llm_integration.models import (
    Complexity,
    DataClassification,
    ExecutionLocation,
    LLMResponse,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.domains.llm_integration.protocols import (
    CostTracker as CostTrackerProtocol,
)
from src.domains.llm_integration.protocols import (
    LLMProvider,
    LLMRouter,
    ToolExecutor,
    VLMProvider,
)

# Main proxy
# VLM Factory
from src.domains.llm_integration.proxy import (
    AegisLLMProxy,
    VLMBackend,
    VLMClient,
    close_shared_vlm_client,
    get_aegis_llm_proxy,
    get_shared_vlm_client,
    get_vlm_backend_from_config,
    get_vlm_client,
)

__all__ = [
    # Protocols (Sprint 57)
    "LLMProvider",
    "LLMRouter",
    "CostTrackerProtocol",
    "ToolExecutor",
    "VLMProvider",
    # Models
    "TaskType",
    "DataClassification",
    "QualityRequirement",
    "Complexity",
    "ExecutionLocation",
    "LLMTask",
    "LLMResponse",
    # Config
    "LLMProxyConfig",
    "get_llm_proxy_config",
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
    # Cost tracking
    "CostTracker",
    "get_cost_tracker",
]
