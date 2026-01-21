"""Skill Router for Intent-Based Skill Activation.

Sprint Context:
    - Sprint 91 (2026-01-14): Feature 91.1 - Intent Router Integration (10 SP)

Implements intelligent skill activation based on intent classification:
1. Maps intents to required/optional skills
2. Filters by skill availability
3. Enforces permission policies
4. Respects context budget limits

Architecture:
    Intent (C-LARA) → Skill Mapping → Permission Check → Load Skills → Context

Integration Points:
    - C-LARA SetFit classifier (95.22% accuracy, Sprint 81)
    - Skill Registry (Sprint 90)
    - Permission Engine (Sprint 91.3)

Based on: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

Example:
    >>> from src.agents.routing import SkillRouter
    >>> from src.agents.skills import get_skill_registry
    >>> from src.agents.security import PermissionEngine
    >>> from src.components.retrieval.intent_classifier import get_intent_classifier
    >>>
    >>> classifier = get_intent_classifier()
    >>> registry = get_skill_registry()
    >>> permissions = PermissionEngine()
    >>> router = SkillRouter(classifier, registry, permissions)
    >>>
    >>> # Route query to skill activation plan
    >>> plan = await router.route("How does authentication work?")
    >>> plan.intent  # Intent.EXPLORATORY
    >>> plan.required_skills  # ['retrieval', 'reflection']
    >>> plan.context_budget  # 4000 tokens
    >>>
    >>> # Activate skills and get instructions
    >>> instructions = await router.activate_skills(plan)
    >>> # Returns combined skill instructions for agent context
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

import structlog
from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.security.permission_engine import PermissionEngine
from src.agents.skills.registry import SkillRegistry
from src.components.retrieval.intent_classifier import (
    CLARAIntent,
    IntentClassifier,
)

logger = structlog.get_logger(__name__)


class Intent(str, Enum):
    """Intent types for skill routing.

    Maps to C-LARA 5-class intents but provides simplified routing categories.
    Used for skill activation decisions and context budget allocation.

    Attributes:
        VECTOR: Vector search only (factual lookups)
        GRAPH: Graph reasoning (entity/relation queries)
        HYBRID: Combined vector + graph (complex queries)
        MEMORY: Memory retrieval (conversation history)
        RESEARCH: Multi-step research (requires planner)
    """

    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"
    MEMORY = "memory"
    RESEARCH = "research"


@dataclass
class SkillActivationPlan:
    """Plan for which skills to activate.

    Represents the routing decision from intent classification to skill loading.
    Contains all information needed to activate skills and build agent context.

    Attributes:
        intent: Classified routing intent
        required_skills: Skills that must be loaded (critical for query)
        optional_skills: Skills that should be loaded if budget allows
        permissions_needed: Set of permissions required by all skills
        context_budget: Maximum tokens for skill instructions
        clara_intent: Original C-LARA 5-class intent (for analytics)

    Example:
        >>> plan = SkillActivationPlan(
        ...     intent=Intent.RESEARCH,
        ...     required_skills=["retrieval", "reflection", "planner"],
        ...     optional_skills=["web_search", "synthesis"],
        ...     permissions_needed={"read_documents", "invoke_llm", "web_access"},
        ...     context_budget=5000,
        ...     clara_intent=CLARAIntent.PROCEDURAL
        ... )
    """

    intent: Intent
    required_skills: List[str]
    optional_skills: List[str]
    permissions_needed: Set[str]
    context_budget: int  # Max tokens for skill instructions
    clara_intent: Optional[CLARAIntent] = None


class SkillRouter:
    """Route intents to skill activation decisions.

    Integrates with:
    - C-LARA SetFit classifier (95.22% accuracy, Sprint 81)
    - Skill Registry for skill loading (Sprint 90)
    - Permission Engine for access control (Sprint 91.3)

    The router implements the core skill activation logic:
    1. Classify query intent using C-LARA
    2. Map intent to skill requirements
    3. Filter skills by availability
    4. Check user permissions
    5. Build activation plan with context budget

    Attributes:
        classifier: Intent classifier (C-LARA SetFit)
        registry: Skill registry for loading skills
        permissions: Permission engine for access control
        INTENT_SKILL_MAP: Configuration mapping intents to skills

    Example:
        >>> router = SkillRouter(classifier, registry, permissions)
        >>> plan = await router.route("Explain how RAG works", user_context={"user_id": "user123"})
        >>> instructions = await router.activate_skills(plan)
    """

    # Intent → Skill mapping configuration
    # Each intent specifies required skills, optional skills, and context budget
    INTENT_SKILL_MAP: Dict[Intent, Dict] = {
        Intent.VECTOR: {
            "required": ["retrieval"],
            "optional": ["synthesis"],
            "context_budget": 2000,
        },
        Intent.GRAPH: {
            "required": ["retrieval", "graph_reasoning"],
            "optional": ["reflection"],
            "context_budget": 3000,
        },
        Intent.HYBRID: {
            "required": ["retrieval", "graph_reasoning"],
            "optional": ["reflection", "synthesis"],
            "context_budget": 4000,
        },
        Intent.MEMORY: {
            "required": ["memory", "retrieval"],
            "optional": [],
            "context_budget": 2000,
        },
        Intent.RESEARCH: {
            "required": ["retrieval", "reflection", "planner"],
            "optional": ["web_search", "synthesis"],
            "context_budget": 5000,
        },
    }

    # C-LARA 5-class → Routing intent mapping
    # Maps fine-grained C-LARA intents to simplified routing categories
    CLARA_TO_ROUTING_INTENT: Dict[CLARAIntent, Intent] = {
        CLARAIntent.FACTUAL: Intent.VECTOR,  # Simple fact lookup
        CLARAIntent.PROCEDURAL: Intent.RESEARCH,  # How-to queries need planning
        CLARAIntent.COMPARISON: Intent.HYBRID,  # Compare entities/concepts
        CLARAIntent.RECOMMENDATION: Intent.HYBRID,  # Suggest options
        CLARAIntent.NAVIGATION: Intent.VECTOR,  # Find specific documents
    }

    def __init__(
        self,
        classifier: IntentClassifier,
        skill_registry: SkillRegistry,
        permission_engine: PermissionEngine,
    ):
        """Initialize skill router.

        Args:
            classifier: Intent classifier (C-LARA SetFit)
            skill_registry: Skill registry for loading skills
            permission_engine: Permission engine for access control
        """
        self.classifier = classifier
        self.registry = skill_registry
        self.permissions = permission_engine

        logger.info(
            "skill_router_initialized",
            available_skills=self.registry.list_available(),
            intent_mappings=list(self.INTENT_SKILL_MAP.keys()),
        )

    async def route(self, query: str, user_context: Optional[Dict] = None) -> SkillActivationPlan:
        """Determine which skills to activate for a query.

        Process:
        1. Classify intent using C-LARA SetFit
        2. Map C-LARA intent to routing intent
        3. Get skill requirements from mapping
        4. Filter by skill availability
        5. Add pattern-matched skills
        6. Collect required permissions
        7. Filter by user permissions

        Args:
            query: User's input query
            user_context: Optional context (e.g., user_id for permissions)

        Returns:
            SkillActivationPlan with skills to load and context budget

        Example:
            >>> plan = await router.route("How does authentication work?")
            >>> plan.intent  # Intent.RESEARCH
            >>> plan.required_skills  # ['retrieval', 'reflection', 'planner']
            >>> plan.context_budget  # 5000
        """
        # Step 1: Classify intent using C-LARA
        classification_result = await self.classifier.classify(query)
        clara_intent = classification_result.clara_intent

        logger.debug(
            "intent_classified",
            query=query[:50],
            clara_intent=clara_intent.value if clara_intent else None,
            legacy_intent=classification_result.intent.value,
            confidence=classification_result.confidence,
            method=classification_result.method,
        )

        # Step 2: Map C-LARA intent to routing intent
        if clara_intent:
            routing_intent = self.CLARA_TO_ROUTING_INTENT.get(clara_intent, Intent.HYBRID)
        else:
            # Fallback: Map legacy Intent to routing intent
            legacy_to_routing = {
                "factual": Intent.VECTOR,
                "keyword": Intent.VECTOR,
                "exploratory": Intent.HYBRID,
                "summary": Intent.RESEARCH,
            }
            routing_intent = Intent(
                legacy_to_routing.get(classification_result.intent.value, Intent.HYBRID)
            )

        # Step 3: Get skill mapping for routing intent
        mapping = self.INTENT_SKILL_MAP.get(routing_intent, self.INTENT_SKILL_MAP[Intent.HYBRID])

        # Step 4: Filter by availability (only load skills that exist)
        available_skills = set(self.registry.list_available())
        required = [s for s in mapping["required"] if s in available_skills]
        optional = [s for s in mapping["optional"] if s in available_skills]

        # Step 5: Additional skills from query pattern matching
        pattern_matches = self.registry.match_intent(query)
        for skill in pattern_matches:
            if skill not in required and skill not in optional:
                optional.append(skill)

        logger.debug(
            "skills_matched",
            query=query[:50],
            routing_intent=routing_intent.value,
            required_skills=required,
            optional_skills=optional,
            pattern_matches=pattern_matches,
        )

        # Step 6: Collect permissions needed by all skills
        permissions_needed: Set[str] = set()
        for skill_name in required + optional:
            metadata = self.registry.get_metadata(skill_name)
            if metadata:
                permissions_needed.update(metadata.permissions)

        # Step 7: Permission check (filter by user permissions)
        if user_context and "user_id" in user_context:
            user_id = user_context["user_id"]

            # Filter required skills by permissions
            filtered_required = []
            for skill in required:
                allowed, reason = self.permissions.check_skill_permission(user_id, skill)
                if allowed:
                    filtered_required.append(skill)
                else:
                    logger.warning(
                        "skill_permission_denied",
                        user_id=user_id,
                        skill=skill,
                        reason=reason,
                    )
            required = filtered_required

            # Filter optional skills by permissions
            filtered_optional = []
            for skill in optional:
                allowed, reason = self.permissions.check_skill_permission(user_id, skill)
                if allowed:
                    filtered_optional.append(skill)
            optional = filtered_optional

        plan = SkillActivationPlan(
            intent=routing_intent,
            required_skills=required,
            optional_skills=optional,
            permissions_needed=permissions_needed,
            context_budget=mapping["context_budget"],
            clara_intent=clara_intent,
        )

        logger.info(
            "routing_plan_created",
            query=query[:50],
            routing_intent=routing_intent.value,
            clara_intent=clara_intent.value if clara_intent else None,
            required_count=len(required),
            optional_count=len(optional),
            context_budget=plan.context_budget,
        )

        return plan

    async def activate_skills(self, plan: SkillActivationPlan) -> str:
        """Activate skills according to plan and return combined instructions.

        Respects context_budget by prioritizing required skills first.
        Optional skills are loaded only if budget allows.

        Token estimation: ~4 characters per token (rough approximation)

        Args:
            plan: Skill activation plan from route()

        Returns:
            Combined skill instructions for agent context

        Example:
            >>> plan = await router.route("How does RAG work?")
            >>> instructions = await router.activate_skills(plan)
            >>> # instructions contains concatenated skill instructions
            >>> # separated by "\\n\\n---\\n\\n"
        """
        instructions = []
        current_tokens = 0

        # Activate required skills first (highest priority)
        for skill_name in plan.required_skills:
            try:
                skill_instructions = self.registry.activate(skill_name)
                skill_tokens = len(skill_instructions) // 4  # Rough estimate

                if current_tokens + skill_tokens <= plan.context_budget:
                    instructions.append(skill_instructions)
                    current_tokens += skill_tokens
                    logger.debug(
                        "skill_activated",
                        skill=skill_name,
                        tokens_used=skill_tokens,
                        total_tokens=current_tokens,
                        budget=plan.context_budget,
                    )
                else:
                    logger.warning(
                        "skill_skipped_budget_exceeded",
                        skill=skill_name,
                        required=True,
                        tokens_needed=skill_tokens,
                        tokens_available=plan.context_budget - current_tokens,
                    )
            except Exception as e:
                logger.error(
                    "skill_activation_failed",
                    skill=skill_name,
                    required=True,
                    error=str(e),
                )

        # Add optional skills if budget allows
        for skill_name in plan.optional_skills:
            try:
                skill_instructions = self.registry.activate(skill_name)
                skill_tokens = len(skill_instructions) // 4

                if current_tokens + skill_tokens <= plan.context_budget:
                    instructions.append(skill_instructions)
                    current_tokens += skill_tokens
                    logger.debug(
                        "skill_activated",
                        skill=skill_name,
                        tokens_used=skill_tokens,
                        total_tokens=current_tokens,
                        budget=plan.context_budget,
                    )
                else:
                    logger.debug(
                        "optional_skill_skipped_budget_limit",
                        skill=skill_name,
                        tokens_needed=skill_tokens,
                        tokens_available=plan.context_budget - current_tokens,
                    )
                    break  # Budget exhausted, stop loading optional skills
            except Exception as e:
                logger.warning(
                    "optional_skill_activation_failed",
                    skill=skill_name,
                    error=str(e),
                )

        combined_instructions = "\n\n---\n\n".join(instructions)

        logger.info(
            "skills_activated",
            intent=plan.intent.value,
            skills_loaded=len(instructions),
            tokens_used=current_tokens,
            budget=plan.context_budget,
            utilization_pct=round((current_tokens / plan.context_budget) * 100, 1),
        )

        return combined_instructions


class SkillAwareCoordinator:
    """Coordinator that uses skill-based activation.

    Integrates skill routing with LLM invocation. Routes queries through
    the skill activation pipeline before sending to the LLM.

    Workflow:
        Query → Route → Activate Skills → Build Prompt → LLM → Response

    Attributes:
        router: Skill router for activation decisions
        llm: LLM for generating responses

    Example:
        >>> from langchain_ollama import ChatOllama
        >>> llm = ChatOllama(model="llama3.2:8b")
        >>> coordinator = SkillAwareCoordinator(router, llm)
        >>> response = await coordinator.process("How does RAG work?")
    """

    def __init__(self, router: SkillRouter, llm: BaseChatModel):
        """Initialize skill-aware coordinator.

        Args:
            router: Skill router for activation decisions
            llm: LLM for generating responses
        """
        self.router = router
        self.llm = llm

        logger.info(
            "skill_aware_coordinator_initialized",
            llm_model=getattr(llm, "model", "unknown"),
        )

    async def process(self, query: str, user_context: Optional[Dict] = None) -> str:
        """Process query with skill-aware context.

        Args:
            query: User query
            user_context: Optional user context for permissions

        Returns:
            LLM response string

        Example:
            >>> response = await coordinator.process(
            ...     "What is the capital of France?",
            ...     user_context={"user_id": "user123"}
            ... )
        """
        # Get activation plan
        plan = await self.router.route(query, user_context)

        # Activate skills
        skill_instructions = await self.router.activate_skills(plan)

        # Build prompt with skill context
        prompt = f"""You are an AI assistant with the following specialized skills activated:

{skill_instructions}

---

User Query: {query}

Use your activated skills to provide the best possible answer.
"""

        logger.debug(
            "coordinator_processing_query",
            query=query[:50],
            intent=plan.intent.value,
            skills_count=len(plan.required_skills) + len(plan.optional_skills),
            prompt_length=len(prompt),
        )

        # Invoke LLM
        response = await self.llm.ainvoke(prompt)

        logger.info(
            "coordinator_response_generated",
            query=query[:50],
            response_length=len(response.content),
        )

        return response.content
