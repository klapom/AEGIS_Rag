"""
LLM Proxy Component - Backward Compatibility Layer.

Sprint 56: Re-exports from src.domains.llm_integration for backward compatibility.

Recommended import:
    from src.domains.llm_integration import get_aegis_llm_proxy, LLMTask
"""

# Re-export from domain location
from src.domains.llm_integration import (
    # Main proxy
    AegisLLMProxy,
    # Models
    Complexity,
    # Cost tracking
    CostTracker,
    DataClassification,
    ExecutionLocation,
    LLMResponse,
    LLMTask,
    QualityRequirement,
    TaskType,
    # VLM Factory
    VLMBackend,
    VLMClient,
    close_shared_vlm_client,
    get_aegis_llm_proxy,
    get_cost_tracker,
    get_shared_vlm_client,
    get_vlm_backend_from_config,
    get_vlm_client,
)

__all__ = [
    # Models
    "TaskType",
    "DataClassification",
    "QualityRequirement",
    "Complexity",
    "ExecutionLocation",
    "LLMTask",
    "LLMResponse",
    # Main proxy
    "AegisLLMProxy",
    "get_aegis_llm_proxy",
    # Cost tracking
    "CostTracker",
    "get_cost_tracker",
    # VLM Factory (Sprint 36 - Feature 36.1)
    "VLMBackend",
    "VLMClient",
    "get_vlm_client",
    "get_vlm_backend_from_config",
    "get_shared_vlm_client",
    "close_shared_vlm_client",
]
