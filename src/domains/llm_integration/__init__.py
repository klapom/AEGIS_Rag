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
from src.domains.llm_integration.protocols import (
    LLMProvider,
    LLMRouter,
    CostTracker as CostTrackerProtocol,
    ToolExecutor,
    VLMProvider,
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

# Configuration
from src.domains.llm_integration.config import (
    LLMProxyConfig,
    get_llm_proxy_config,
)

# Main proxy
from src.domains.llm_integration.proxy import (
    AegisLLMProxy,
    get_aegis_llm_proxy,
)

# VLM Factory
from src.domains.llm_integration.proxy import (
    VLMBackend,
    VLMClient,
    get_vlm_client,
    get_vlm_backend_from_config,
    get_shared_vlm_client,
    close_shared_vlm_client,
)

# Cost tracking
from src.domains.llm_integration.cost import (
    CostTracker,
    get_cost_tracker,
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
