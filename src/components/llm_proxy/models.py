"""
Pydantic models for LLM proxy component - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.models
OPL-006: These re-exports will be removed in Sprint 58.

Migrate to:
    from src.domains.llm_integration.models import LLMTask, TaskType
"""

# OPL-006: Re-export from new domain location
from src.domains.llm_integration.models import (
    Complexity,
    DataClassification,
    ExecutionLocation,
    LLMResponse,
    LLMTask,
    QualityRequirement,
    TaskType,
)

__all__ = [
    "TaskType",
    "DataClassification",
    "QualityRequirement",
    "Complexity",
    "ExecutionLocation",
    "LLMTask",
    "LLMResponse",
]
