"""Skill-Aware Role-aware Context Router (RCR-Router).

Sprint Context:
    - Sprint 92 (2026-01-14): Feature 92.3 - RCR-Router + Skill Integration (8 SP)

Role-aware Context Router integrated with skill system for intelligent context
distribution to active skills based on their roles and capabilities.

Based on: Liu et al. (2025) "RCR-Router"

Architecture:
    Query + Contexts + Active Skills
              │
              ▼
    ┌─────────────────────┐
    │  Ensure Skills      │ → Activate required skills
    │  Are Active         │
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  Calculate          │ → Per-skill context budgets
    │  Context Budgets    │
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  Embed Contexts     │ → Dense vectors (BGE-M3)
    │  and Skill Roles    │
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  Score Contexts     │ → Cosine similarity
    │  per Skill          │   (context vs skill+role)
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  Select Within      │ → Top contexts per skill
    │  Budget             │   (respect token limits)
    └─────────────────────┘
              │
              ▼
    Skill → Context Assignments

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
    ...     contexts=["Context 1...", "Context 2..."],
    ...     query="What are the main findings?",
    ...     required_skills=["synthesis", "reflection"]
    ... )
    >>> assignments
    {'synthesis': ['Context 1...'], 'reflection': ['Context 2...']}

Notes:
    - Uses BGE-M3 embeddings for semantic matching
    - Budget-aware context assignment
    - Role-based routing for skill specialization
    - Automatic skill activation if needed

See Also:
    - docs/sprints/SPRINT_92_PLAN.md: Feature specification
    - src/agents/skills/lifecycle.py: Skill lifecycle API
    - src/agents/skills/context_budget.py: Context budget manager
"""

from typing import Any, Optional

import numpy as np
import structlog

from src.agents.skills.lifecycle import SkillLifecycleManager, SkillState

logger = structlog.get_logger(__name__)


class SkillAwareRCRRouter:
    """Role-aware Context Router with Skill Integration.

    Distributes context to active skills based on their roles,
    respecting context budgets and skill capabilities.

    Based on: Liu et al. (2025) "RCR-Router"

    Attributes:
        lifecycle: Skill lifecycle manager
        embeddings: Embedding service (BGE-M3)
        skill_roles: Mapping of skill names to role descriptions

    Example:
        >>> from src.components.shared.embedding_factory import get_embedding_service
        >>> router = SkillAwareRCRRouter(
        ...     lifecycle_manager=lifecycle_manager,
        ...     embedding_model=get_embedding_service(),
        ...     skill_role_map={
        ...         "reflection": ["validate", "critique"],
        ...         "synthesis": ["aggregate", "summarize"]
        ...     }
        ... )
        >>>
        >>> assignments = await router.route_to_skills(
        ...     contexts=contexts,
        ...     query="What are the results?",
        ...     required_skills=["synthesis"]
        ... )
    """

    def __init__(
        self,
        lifecycle_manager: SkillLifecycleManager,
        embedding_model: Any,
        skill_role_map: dict[str, list[str]],
    ):
        """Initialize skill-aware RCR router.

        Args:
            lifecycle_manager: Skill lifecycle manager
            embedding_model: Embedding service (must support embed_single/embed_batch)
            skill_role_map: Mapping of skill names to role descriptions
        """
        self.lifecycle = lifecycle_manager
        self.embeddings = embedding_model
        self.skill_roles = skill_role_map

        logger.info(
            "skill_aware_rcr_router_initialized",
            skills=list(skill_role_map.keys()),
        )

    async def route_to_skills(
        self,
        contexts: list[str],
        query: str,
        required_skills: list[str],
    ) -> dict[str, list[str]]:
        """Route contexts to active skills based on roles.

        Args:
            contexts: Retrieved context chunks
            query: User's query
            required_skills: Skills that must receive context

        Returns:
            Dict mapping skill_name -> assigned contexts

        Example:
            >>> assignments = await router.route_to_skills(
            ...     contexts=["Context 1", "Context 2", "Context 3"],
            ...     query="Summarize the findings",
            ...     required_skills=["synthesis", "reflection"]
            ... )
            >>> assignments
            {'synthesis': ['Context 1', 'Context 3'], 'reflection': ['Context 2']}
        """
        if not contexts:
            logger.warning("no_contexts_to_route")
            return {skill: [] for skill in required_skills}

        logger.info(
            "routing_contexts_to_skills",
            context_count=len(contexts),
            required_skills=required_skills,
        )

        # Ensure required skills are active
        for skill in required_skills:
            state = self.lifecycle.get_state(skill)
            if state != SkillState.ACTIVE:
                await self.lifecycle.activate(skill)
                logger.info("activated_skill_for_routing", skill_name=skill)

        # Get available context budget per skill
        budgets = self._calculate_budgets(required_skills)
        logger.debug("context_budgets_calculated", budgets=budgets)

        # Embed contexts and skill-role combinations
        context_embeddings = await self._embed_contexts(contexts)
        skill_embeddings = await self._embed_skill_roles(required_skills, query)

        # Score and assign
        assignments = {}
        for skill in required_skills:
            scores = self._score_contexts(
                context_embeddings,
                skill_embeddings[skill],
            )

            # Select top contexts within budget
            selected = self._select_within_budget(
                contexts,
                scores,
                budgets[skill],
            )
            assignments[skill] = selected

            logger.info(
                "contexts_assigned_to_skill",
                skill_name=skill,
                assigned_count=len(selected),
                budget=budgets[skill],
            )

        return assignments

    def _calculate_budgets(
        self,
        skills: list[str],
    ) -> dict[str, int]:
        """Calculate context budget per skill.

        Uses existing allocation or divides remaining budget equally.

        Args:
            skills: List of skill names

        Returns:
            Dict mapping skill name to token budget

        Example:
            >>> budgets = router._calculate_budgets(["skill1", "skill2"])
            >>> budgets
            {'skill1': 2000, 'skill2': 1500}
        """
        total_budget = self.lifecycle.get_available_budget()
        usage = self.lifecycle.get_context_usage()

        budgets = {}
        for skill in skills:
            # Use existing allocation or divide remaining
            if skill in usage:
                budgets[skill] = usage[skill]
            else:
                remaining = total_budget - sum(budgets.values())
                unallocated = len(skills) - len(budgets)
                budgets[skill] = remaining // max(1, unallocated)

        return budgets

    async def _embed_contexts(self, contexts: list[str]) -> list[list[float]]:
        """Embed context chunks using embedding service.

        Args:
            contexts: List of context strings

        Returns:
            List of embedding vectors

        Example:
            >>> embeddings = await router._embed_contexts(["Context 1", "Context 2"])
            >>> len(embeddings)
            2
            >>> len(embeddings[0])
            1024
        """
        # Use embedding service (handles batching internally)
        embeddings = []
        for context in contexts:
            result = self.embeddings.embed_single(context)
            # Handle multi-vector backend (flag-embedding)
            if isinstance(result, dict):
                embeddings.append(result["dense"])
            else:
                embeddings.append(result)

        logger.debug("contexts_embedded", count=len(embeddings))
        return embeddings

    async def _embed_skill_roles(
        self,
        skills: list[str],
        query: str,
    ) -> dict[str, list[float]]:
        """Embed skill+role combinations with query.

        Args:
            skills: List of skill names
            query: User's query

        Returns:
            Dict mapping skill name to embedding vector

        Example:
            >>> embeddings = await router._embed_skill_roles(
            ...     ["synthesis"],
            ...     "Summarize the findings"
            ... )
            >>> embeddings
            {'synthesis': [0.1, 0.2, ...]}
        """
        embeddings = {}
        for skill in skills:
            roles = self.skill_roles.get(skill, [skill])
            role_text = f"{', '.join(roles)}. Query: {query}"

            result = self.embeddings.embed_single(role_text)
            # Handle multi-vector backend
            if isinstance(result, dict):
                embeddings[skill] = result["dense"]
            else:
                embeddings[skill] = result

        logger.debug("skill_roles_embedded", skills=list(embeddings.keys()))
        return embeddings

    def _score_contexts(
        self,
        context_embeddings: list[list[float]],
        skill_embedding: list[float],
    ) -> list[float]:
        """Score contexts for relevance to skill using cosine similarity.

        Args:
            context_embeddings: List of context embedding vectors
            skill_embedding: Skill+role embedding vector

        Returns:
            List of similarity scores (0.0-1.0)

        Example:
            >>> scores = router._score_contexts(
            ...     context_embeddings=[[0.1, 0.2], [0.3, 0.4]],
            ...     skill_embedding=[0.5, 0.6]
            ... )
            >>> scores
            [0.85, 0.92]
        """
        scores = []
        skill_vec = np.array(skill_embedding)

        for context_emb in context_embeddings:
            context_vec = np.array(context_emb)
            # Cosine similarity
            similarity = float(
                np.dot(context_vec, skill_vec)
                / (np.linalg.norm(context_vec) * np.linalg.norm(skill_vec))
            )
            scores.append(similarity)

        return scores

    def _select_within_budget(
        self,
        contexts: list[str],
        scores: list[float],
        budget: int,
    ) -> list[str]:
        """Select top contexts within budget.

        Args:
            contexts: List of context strings
            scores: List of relevance scores
            budget: Token budget for this skill

        Returns:
            Selected contexts within budget

        Example:
            >>> selected = router._select_within_budget(
            ...     contexts=["Context 1", "Context 2", "Context 3"],
            ...     scores=[0.9, 0.5, 0.8],
            ...     budget=2000
            ... )
            >>> selected
            ['Context 1', 'Context 3']  # Top 2 by score
        """
        # Sort by score (highest first)
        scored_contexts = list(zip(contexts, scores))
        scored_contexts.sort(key=lambda x: x[1], reverse=True)

        # Select contexts within budget (rough estimate: 4 chars = 1 token)
        selected = []
        tokens_used = 0

        for context, score in scored_contexts:
            context_tokens = len(context) // 4
            if tokens_used + context_tokens <= budget:
                selected.append(context)
                tokens_used += context_tokens
            else:
                break

        logger.debug(
            "contexts_selected_within_budget",
            selected_count=len(selected),
            tokens_used=tokens_used,
            budget=budget,
        )

        return selected
