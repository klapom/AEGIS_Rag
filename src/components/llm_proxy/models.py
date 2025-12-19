"""
Pydantic models for LLM proxy component - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.models

Recommended import:
    from src.domains.llm_integration.models import LLMTask, TaskType
"""

# Re-export from domain location
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
