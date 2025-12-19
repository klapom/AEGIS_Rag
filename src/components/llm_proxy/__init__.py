"""
LLM Proxy Component - Backward Compatibility Layer.

Sprint 56: Re-exports from src.domains.llm_integration for backward compatibility.
OPL-006: These re-exports will be removed in Sprint 58.

Migrate to:
    from src.domains.llm_integration import get_aegis_llm_proxy, LLMTask

See: docs/refactoring/REFACTORING_OPL.md
"""

# OPL-006: Re-export from new domain location
# DC-004: These re-exports will be removed in Sprint 58
from src.domains.llm_integration import (
    # Models
    Complexity,
    DataClassification,
    ExecutionLocation,
    LLMResponse,
    LLMTask,
    QualityRequirement,
    TaskType,
    # Main proxy
    AegisLLMProxy,
    get_aegis_llm_proxy,
    # Cost tracking
    CostTracker,
    get_cost_tracker,
    # VLM Factory
    VLMBackend,
    VLMClient,
    close_shared_vlm_client,
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
