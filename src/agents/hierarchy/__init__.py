"""Hierarchical Agent Pattern - Manager/Worker Architecture with Skill Delegation.

Sprint 95 Feature 95.1: Hierarchical Agent Pattern (10 SP)

This package implements a three-level hierarchical agent architecture:

1. **Executive Level**: Strategic planning and high-level coordination
2. **Manager Level**: Domain-specific coordination (research, analysis, synthesis)
3. **Worker Level**: Atomic skill execution

Example:
    >>> from src.agents.hierarchy import (
    ...     ExecutiveAgent,
    ...     ManagerAgent,
    ...     WorkerAgent,
    ...     SkillTask,
    ...     AgentLevel
    ... )
    >>> from src.agents.skills.lifecycle import SkillLifecycleManager
    >>> from pathlib import Path
    >>>
    >>> # Setup
    >>> skill_manager = SkillLifecycleManager(skills_dir=Path("skills"))
    >>> executive = ExecutiveAgent(
    ...     agent_id="executive_001",
    ...     skill_manager=skill_manager,
    ...     orchestrator=None
    ... )
    >>>
    >>> # Execute strategic goal
    >>> result = await executive.set_goal(
    ...     goal="Research quantum computing",
    ...     context_budget=10000
    ... )

See Also:
    - docs/sprints/SPRINT_95_PLAN.md: Full specification
    - src/agents/hierarchy/skill_hierarchy.py: Implementation
"""

from src.agents.hierarchy.skill_hierarchy import (
    AgentLevel,
    DelegationResult,
    ExecutiveAgent,
    HierarchicalAgent,
    ManagerAgent,
    SkillTask,
    WorkerAgent,
)

__all__ = [
    "AgentLevel",
    "DelegationResult",
    "ExecutiveAgent",
    "HierarchicalAgent",
    "ManagerAgent",
    "SkillTask",
    "WorkerAgent",
]
