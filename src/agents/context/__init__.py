"""Context management modules for AegisRAG agents.

Sprint Context:
    - Sprint 92 (2026-01-14): Feature 92.1 - Recursive LLM Module (12 SP)

This package provides advanced context handling capabilities for processing
documents far exceeding the context window limit through recursive exploration.

Modules:
    - recursive_llm: Process large documents recursively with skill integration

Based on: Zhang et al. (2025) "Recursive Language Models" (arXiv:2512.24601)

Example:
    >>> from src.agents.context.recursive_llm import RecursiveLLMProcessor
    >>> from src.agents.skills import get_skill_registry
    >>> from src.core.config import settings
    >>>
    >>> processor = RecursiveLLMProcessor(
    ...     llm=llm,
    ...     skill_registry=get_skill_registry()
    ... )
    >>> result = await processor.process(
    ...     document=long_document,
    ...     query="What are the main findings?"
    ... )
    >>> print(result["answer"])

See Also:
    - docs/sprints/SPRINT_92_PLAN.md: Implementation details
    - docs/agents/AGENTS_HIGHLEVEL.md: Agent architecture overview
"""

from src.agents.context.recursive_llm import (
    DocumentSegment,
    RecursiveLLMProcessor,
)

__all__ = [
    "DocumentSegment",
    "RecursiveLLMProcessor",
]
