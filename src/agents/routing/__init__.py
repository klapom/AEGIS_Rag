"""Context routing modules for AegisRAG agents.

Sprint Context:
    - Sprint 92 (2026-01-14): Feature 92.3 - RCR-Router + Skill Integration (8 SP)

This package provides role-aware context routing for intelligent distribution
of retrieved contexts to active skills based on their roles and capabilities.

Modules:
    - skill_rcr_router: Role-aware context router with skill integration

Based on: Liu et al. (2025) "RCR-Router" (Role-aware Context Routing)

Example:
    >>> from src.agents.routing.skill_rcr_router import SkillAwareRCRRouter
    >>> from src.agents.skills.lifecycle import SkillLifecycleManager
    >>> from src.components.shared.embedding_factory import get_embedding_service
    >>>
    >>> router = SkillAwareRCRRouter(
    ...     lifecycle_manager=lifecycle_manager,
    ...     embedding_model=get_embedding_service(),
    ...     skill_role_map={
    ...         "reflection": ["validate", "critique", "verify"],
    ...         "synthesis": ["aggregate", "combine", "summarize"]
    ...     }
    ... )
    >>>
    >>> assignments = await router.route_to_skills(
    ...     contexts=retrieved_contexts,
    ...     query="What are the main findings?",
    ...     required_skills=["synthesis"]
    ... )

See Also:
    - docs/sprints/SPRINT_92_PLAN.md: Implementation details
    - src/agents/skills/lifecycle.py: Skill lifecycle management
"""

from src.agents.routing.skill_rcr_router import SkillAwareRCRRouter

__all__ = [
    "SkillAwareRCRRouter",
]
