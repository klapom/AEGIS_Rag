"""
LLM Proxy Component - Mozilla ANY-LLM Integration.

This module provides AegisRAG-specific LLM routing on top of Mozilla's
ANY-LLM framework, enabling three-tier execution (Local → Ollama Cloud → OpenAI).

Sprint Context: Sprint 23 (2025-11-11+) - Feature 23.4
Related ADR: ADR-033 (Mozilla ANY-LLM Integration)

Components:
    - AegisLLMProxy: Main proxy class with routing logic
    - LLMTask, LLMResponse: Pydantic models for requests/responses
    - LLMProxyConfig: Configuration management

Usage:
    from src.components.llm_proxy import get_aegis_llm_proxy, LLMTask

    proxy = get_aegis_llm_proxy()
    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Extract entities from text...",
        quality_requirement=QualityRequirement.HIGH,
    )
    response = await proxy.generate(task)
"""

# AegisLLMProxy (ready to use once ANY-LLM SDK is installed)
from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy, get_aegis_llm_proxy

# Cost tracking (Sprint 23 - persistent SQLite tracking)
from src.components.llm_proxy.cost_tracker import CostTracker
from src.components.llm_proxy.models import (
    Complexity,
    DataClassification,
    ExecutionLocation,
    LLMResponse,
    LLMTask,
    QualityRequirement,
    TaskType,
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
]
