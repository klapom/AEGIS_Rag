"""Agent Skills module for AegisRAG.

Sprint Context:
    - Sprint 90 (2026-01-14): Features 90.1, 90.2, 90.3 - Agent Skills Foundation
    - Sprint 92 (2026-01-14): Features 92.2, 92.4 - Lifecycle & Context Budget

This module implements the Anthropic Agent Skills standard for AegisRAG.

Skills are modular capability containers that can be:
- Discovered from filesystem
- Loaded on-demand based on intent
- Unloaded to save context tokens
- Versioned and updated independently

Based on: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

Example:
    >>> from src.agents.skills import get_skill_registry, SkillLifecycleManager
    >>> from pathlib import Path
    >>>
    >>> # Registry usage
    >>> registry = get_skill_registry()
    >>> registry.discover()
    >>> registry.activate("reflection")
    >>> instructions = registry.get_active_instructions()
    >>>
    >>> # Lifecycle management (Sprint 92)
    >>> lifecycle = SkillLifecycleManager(
    ...     skills_dir=Path("skills"),
    ...     max_loaded_skills=20,
    ...     max_active_skills=5
    ... )
    >>> await lifecycle.load("reflection")
    >>> await lifecycle.activate("reflection", context_allocation=2000)

See Also:
    - docs/sprints/SPRINT_90_PLAN.md: Sprint 90 implementation plan
    - docs/sprints/SPRINT_92_PLAN.md: Sprint 92 implementation plan
    - docs/adr/ADR-049-agentic-framework-architecture.md: Architecture decisions
"""

from src.agents.skills.context_budget import (
    ContextBudgetManager,
    SkillContextBudget,
)
from src.agents.skills.hallucination_monitor import (
    Claim,
    ClaimVerification,
    HallucinationMonitor,
    HallucinationReport,
)
from src.agents.skills.lifecycle import (
    SkillLifecycleEvent,
    SkillLifecycleManager,
    SkillState,
    SkillVersion,
)
from src.agents.skills.reflection import ReflectionResult, ReflectionSkill
from src.agents.skills.registry import (
    LoadedSkill,
    SkillMetadata,
    SkillRegistry,
    get_skill_registry,
)

__all__ = [
    # Registry (Sprint 90)
    "SkillMetadata",
    "LoadedSkill",
    "SkillRegistry",
    "get_skill_registry",
    # Lifecycle (Sprint 92)
    "SkillLifecycleManager",
    "SkillState",
    "SkillVersion",
    "SkillLifecycleEvent",
    # Context Budget (Sprint 92)
    "ContextBudgetManager",
    "SkillContextBudget",
    # Reflection (Sprint 90)
    "ReflectionSkill",
    "ReflectionResult",
    # Hallucination Monitor (Sprint 90)
    "HallucinationMonitor",
    "HallucinationReport",
    "Claim",
    "ClaimVerification",
]
