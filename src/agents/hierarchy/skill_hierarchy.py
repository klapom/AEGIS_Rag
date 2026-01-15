"""Hierarchical Agent Pattern - Manager/Worker Architecture with Skill Delegation.

Sprint 95 Feature 95.1: Hierarchical Agent Pattern (10 SP)

This module implements a three-level hierarchical agent architecture where agents
delegate tasks based on skill requirements. The hierarchy consists of:

1. **Executive Level**: Strategic planning and high-level coordination
2. **Manager Level**: Domain-specific coordination (research, analysis, synthesis)
3. **Worker Level**: Atomic skill execution

Architecture:
    ┌──────────────┐
    │   Executive  │ ← Strategic decisions, orchestration
    │   Director   │   Skills: [planner, orchestrator, reflection]
    └──────┬───────┘
           │
    ┌──────┴─────────────────┬────────────┐
    ▼                        ▼            ▼
┌──────────┐         ┌──────────┐  ┌──────────┐
│ Research │         │ Analysis │  │ Synthesis│ ← Task management
│ Manager  │         │ Manager  │  │ Manager  │   Delegates to workers
│[research]│         │[analysis]│  │[synthesis]│
└────┬─────┘         └────┬─────┘  └────┬─────┘
     │                    │             │
┌────┴────┐          ┌────┴────┐   ┌────┴────┐
▼    ▼    ▼          ▼    ▼    ▼   ▼    ▼    ▼
W1   W2   W3        W4   W5   W6  W7   W8   W9  ← Workers execute skills
ret  web  grp       val  ref  cmp sum  cit  fmt

Communication:
    - Top-down delegation: Executives → Managers → Workers
    - Bottom-up reporting: Workers → Managers → Executives
    - Context budget flows down hierarchy
    - Results aggregate up hierarchy

Integration:
    - Uses SkillLifecycleManager for skill activation/deactivation
    - Uses MessageBus for inter-agent communication
    - Compatible with LangGraph 1.0 create_react_agent patterns
    - Supports SharedMemoryProtocol for collaborative state

Example:
    >>> from src.agents.hierarchy.skill_hierarchy import ExecutiveAgent
    >>> from src.agents.skills.lifecycle import SkillLifecycleManager
    >>>
    >>> skill_manager = SkillLifecycleManager(skills_dir=Path("skills"))
    >>> orchestrator = SkillOrchestrator(skill_manager=skill_manager)
    >>>
    >>> executive = ExecutiveAgent(
    ...     agent_id="executive_001",
    ...     skill_manager=skill_manager,
    ...     orchestrator=orchestrator
    ... )
    >>>
    >>> # Execute strategic goal
    >>> result = await executive.set_goal(
    ...     goal="Research quantum computing and synthesize findings",
    ...     context_budget=10000
    ... )

See Also:
    - docs/sprints/SPRINT_95_PLAN.md (lines 99-511): Full specification
    - src/agents/skills/lifecycle.py: Skill lifecycle management
    - src/agents/orchestrator/skill_orchestrator.py: Multi-level orchestration
    - LangGraph Hierarchical Teams: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog
from langchain_core.language_models import BaseChatModel

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Data Models
# =============================================================================


class AgentLevel(Enum):
    """Hierarchical agent levels.

    Attributes:
        EXECUTIVE: Top-level strategic planning (Level 0)
        MANAGER: Mid-level domain coordination (Level 1)
        WORKER: Leaf-level skill execution (Level 2)

    Example:
        >>> level = AgentLevel.EXECUTIVE
        >>> level.value
        0
        >>> level.name
        'EXECUTIVE'
    """

    EXECUTIVE = 0  # Strategic decisions, high-level skills
    MANAGER = 1  # Task coordination, domain skills
    WORKER = 2  # Task execution, atomic skills


@dataclass
class SkillTask:
    """Task delegated through agent hierarchy.

    Represents a unit of work that flows down the hierarchy and
    results that flow back up.

    Attributes:
        id: Unique task identifier
        description: Human-readable task description
        required_skills: List of skill names needed to complete task
        context_budget: Token budget allocation for this task
        priority: Task priority (1-10, higher = more urgent)
        assigned_to: Agent ID currently handling this task
        parent_task_id: ID of parent task (for sub-tasks)
        status: Current status (pending, in_progress, completed, failed)
        result: Task execution result (populated on completion)
        sub_tasks: List of decomposed sub-tasks
        metadata: Additional task metadata

    Example:
        >>> task = SkillTask(
        ...     id="task_123",
        ...     description="Research quantum computing companies",
        ...     required_skills=["web_search", "retrieval"],
        ...     context_budget=5000,
        ...     priority=8
        ... )
        >>> task.status
        'pending'
    """

    id: str
    description: str
    required_skills: list[str]
    context_budget: int
    priority: int
    assigned_to: str | None = None
    parent_task_id: str | None = None
    status: str = "pending"
    result: Any = None
    sub_tasks: list[SkillTask] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegationResult:
    """Result of task delegation.

    Attributes:
        task: Original task delegated
        success: Whether delegation succeeded
        delegated_to: Agent ID task was delegated to
        sub_results: Results from sub-tasks (for managers)
        execution_time: Time taken to complete (seconds)
        context_used: Actual context tokens consumed
        errors: List of errors encountered

    Example:
        >>> result = DelegationResult(
        ...     task=task,
        ...     success=True,
        ...     delegated_to="worker_001",
        ...     execution_time=5.3,
        ...     context_used=2000
        ... )
    """

    task: SkillTask
    success: bool
    delegated_to: str
    sub_results: list[DelegationResult] = field(default_factory=list)
    execution_time: float = 0.0
    context_used: int = 0
    errors: list[str] = field(default_factory=list)


# =============================================================================
# Hierarchical Agent Base Class
# =============================================================================


class HierarchicalAgent(ABC):
    """Base class for hierarchical agents with skill delegation.

    Each agent level has different skill access and capabilities:
    - **Executive**: planner, orchestrator, high-level reasoning
    - **Manager**: domain-specific skills, coordination
    - **Worker**: atomic execution skills

    The agent manages its own skills through SkillLifecycleManager and
    delegates tasks to child agents based on skill requirements.

    Attributes:
        agent_id: Unique agent identifier
        level: Hierarchical level (EXECUTIVE, MANAGER, WORKER)
        skills: SkillLifecycleManager instance
        available_skills: List of skill names this agent can use
        parent: Parent agent in hierarchy (None for Executive)
        children: List of child agents

    Example:
        >>> from pathlib import Path
        >>> from src.agents.skills.lifecycle import SkillLifecycleManager
        >>>
        >>> skill_manager = SkillLifecycleManager(skills_dir=Path("skills"))
        >>> agent = ManagerAgent(
        ...     agent_id="research_manager",
        ...     domain="research",
        ...     skill_manager=skill_manager,
        ...     domain_skills=["web_search", "retrieval", "graph_query"]
        ... )
    """

    def __init__(
        self,
        agent_id: str,
        level: AgentLevel,
        skill_manager: Any,
        available_skills: list[str],
        parent: HierarchicalAgent | None = None,
    ) -> None:
        """Initialize hierarchical agent.

        Args:
            agent_id: Unique agent identifier
            level: Hierarchical level (EXECUTIVE, MANAGER, WORKER)
            skill_manager: SkillLifecycleManager instance
            available_skills: List of skill names this agent can use
            parent: Optional parent agent in hierarchy
        """
        self.agent_id = agent_id
        self.level = level
        self.skills = skill_manager
        self.available_skills = available_skills
        self.parent = parent
        self.children: list[HierarchicalAgent] = []
        self._active_skills: list[str] = []

        logger.info(
            "hierarchical_agent_initialized",
            agent_id=agent_id,
            level=level.name,
            skills_count=len(available_skills),
            skills=available_skills,
        )

    def add_child(self, child: HierarchicalAgent) -> None:
        """Add subordinate agent to hierarchy.

        Args:
            child: Child agent to add

        Example:
            >>> executive.add_child(research_manager)
            >>> executive.children
            [<ManagerAgent: research_manager>]
        """
        child.parent = self
        self.children.append(child)

        logger.debug(
            "child_agent_added",
            parent_id=self.agent_id,
            child_id=child.agent_id,
            child_level=child.level.name,
        )

    async def activate_my_skills(self, context_budget: int) -> None:
        """Activate this agent's skills with budget allocation.

        Distributes context budget evenly across available skills and
        activates them through SkillLifecycleManager.

        Args:
            context_budget: Total token budget to allocate

        Example:
            >>> await agent.activate_my_skills(context_budget=5000)
            >>> agent._active_skills
            ['web_search', 'retrieval']
        """
        budget_per_skill = context_budget // max(1, len(self.available_skills))

        for skill_name in self.available_skills:
            await self.skills.activate(skill_name, budget_per_skill)
            self._active_skills.append(skill_name)

        logger.debug(
            "agent_skills_activated",
            agent_id=self.agent_id,
            skills=self._active_skills,
            budget_per_skill=budget_per_skill,
        )

    async def deactivate_my_skills(self) -> None:
        """Deactivate all active skills.

        Frees context budget by deactivating skills through
        SkillLifecycleManager.

        Example:
            >>> await agent.deactivate_my_skills()
            >>> agent._active_skills
            []
        """
        for skill_name in self._active_skills:
            await self.skills.deactivate(skill_name)

        logger.debug(
            "agent_skills_deactivated",
            agent_id=self.agent_id,
            skills_count=len(self._active_skills),
        )

        self._active_skills = []

    async def receive_task(self, task: SkillTask) -> SkillTask:
        """Receive task from parent and execute or delegate.

        This is the main entry point for task execution in the hierarchy.
        Managers decompose and delegate to children, workers execute directly.

        Args:
            task: Task to execute

        Returns:
            Completed task with results

        Example:
            >>> task = SkillTask(
            ...     id="task_123",
            ...     description="Research quantum computing",
            ...     required_skills=["web_search"],
            ...     context_budget=2000,
            ...     priority=5
            ... )
            >>> completed = await agent.receive_task(task)
            >>> completed.status
            'completed'
        """
        task.status = "in_progress"
        task.assigned_to = self.agent_id

        logger.info(
            "task_received",
            agent_id=self.agent_id,
            task_id=task.id,
            description=task.description[:100],
            required_skills=task.required_skills,
        )

        # Activate skills for this task
        await self.activate_my_skills(task.context_budget)

        try:
            if self.level == AgentLevel.WORKER:
                # Workers execute directly
                return await self._execute_with_skills(task)
            else:
                # Managers/Executives delegate
                return await self._delegate_with_skills(task)

        except Exception as e:
            task.status = "failed"
            task.result = f"Task failed: {e!s}"

            logger.error(
                "task_execution_failed",
                agent_id=self.agent_id,
                task_id=task.id,
                error=str(e),
                exc_info=True,
            )

            return task

        finally:
            await self.deactivate_my_skills()

    async def _delegate_with_skills(self, task: SkillTask) -> SkillTask:
        """Decompose and delegate task to children using manager skills.

        Uses planner skill if available for intelligent decomposition,
        otherwise falls back to simple decomposition. Assigns sub-tasks
        to children based on skill matching.

        Args:
            task: Task to decompose and delegate

        Returns:
            Completed task with aggregated results

        Example:
            >>> task = SkillTask(
            ...     id="task_parent",
            ...     description="Research and analyze quantum computing",
            ...     required_skills=["web_search", "retrieval", "synthesis"],
            ...     context_budget=8000,
            ...     priority=8
            ... )
            >>> result = await manager._delegate_with_skills(task)
            >>> len(result.sub_tasks)
            3
        """
        # Use planner skill if available for decomposition
        if "planner" in self._active_skills:
            sub_tasks = await self._plan_subtasks(task)
        else:
            sub_tasks = self._simple_decompose(task)

        task.sub_tasks = sub_tasks

        logger.debug(
            "task_decomposed",
            agent_id=self.agent_id,
            task_id=task.id,
            sub_task_count=len(sub_tasks),
        )

        # Assign to children based on required skills
        assignments = self._assign_by_skills(sub_tasks)

        # Execute delegated tasks
        results = await self._execute_delegated(assignments)

        # Aggregate using synthesis skill if available
        if "synthesis" in self._active_skills:
            task.result = await self._synthesize_results(task, results)
        else:
            task.result = self._simple_aggregate(results)

        task.status = "completed"

        # Report to parent
        if self.parent:
            await self.parent.receive_report(task)

        logger.info(
            "task_delegation_completed",
            agent_id=self.agent_id,
            task_id=task.id,
            sub_tasks_completed=len(results),
        )

        return task

    async def _plan_subtasks(self, task: SkillTask) -> list[SkillTask]:
        """Use planner skill to decompose task intelligently.

        TODO: Integrate with LLM to use planner skill instructions for
        intelligent task decomposition. For now, uses simple decomposition.

        Args:
            task: Task to decompose

        Returns:
            List of sub-tasks
        """
        # Future: Use LLM with planner skill instructions for decomposition
        # For now, fallback to simple decomposition
        return self._simple_decompose(task)

    def _simple_decompose(self, task: SkillTask) -> list[SkillTask]:
        """Simple task decomposition without planner skill.

        Creates one sub-task per required skill, dividing context budget evenly.

        Args:
            task: Task to decompose

        Returns:
            List of sub-tasks
        """
        sub_tasks = []
        budget_per_sub = task.context_budget // max(1, len(task.required_skills))

        for i, skill in enumerate(task.required_skills):
            sub_tasks.append(
                SkillTask(
                    id=f"{task.id}_sub_{i}",
                    description=f"{task.description} (using {skill})",
                    required_skills=[skill],
                    context_budget=budget_per_sub,
                    priority=task.priority,
                    parent_task_id=task.id,
                )
            )

        return sub_tasks

    def _assign_by_skills(self, sub_tasks: list[SkillTask]) -> dict[str, list[SkillTask]]:
        """Assign tasks to children based on skill matching.

        Finds best child for each sub-task by matching required skills
        with child's available skills.

        Args:
            sub_tasks: List of sub-tasks to assign

        Returns:
            Dict mapping child agent_id to list of assigned tasks
        """
        assignments: dict[str, list[SkillTask]] = defaultdict(list)

        for task in sub_tasks:
            best_child = self._find_child_with_skills(task.required_skills)
            if best_child:
                task.assigned_to = best_child.agent_id
                assignments[best_child.agent_id].append(task)

        logger.debug(
            "tasks_assigned",
            agent_id=self.agent_id,
            assignments_count=len(assignments),
            total_tasks=len(sub_tasks),
        )

        return assignments

    def _find_child_with_skills(self, required_skills: list[str]) -> HierarchicalAgent | None:
        """Find child agent that has required skills.

        Args:
            required_skills: List of required skill names

        Returns:
            Best matching child agent or None

        Algorithm:
            1. First try to find child with ALL required skills
            2. If not found, find child with most matching skills
        """
        # Try exact match first
        for child in self.children:
            if all(s in child.available_skills for s in required_skills):
                return child

        # Fallback: find child with most matching skills
        best_child = None
        best_match = 0
        for child in self.children:
            matches = sum(1 for s in required_skills if s in child.available_skills)
            if matches > best_match:
                best_match = matches
                best_child = child

        return best_child

    async def _execute_delegated(
        self, assignments: dict[str, list[SkillTask]]
    ) -> dict[str, list[SkillTask]]:
        """Execute delegated tasks in parallel.

        Args:
            assignments: Dict mapping child_id to tasks

        Returns:
            Dict mapping child_id to completed tasks
        """
        results: dict[str, list[SkillTask]] = {}

        # Build list of (child, task) pairs for parallel execution
        tasks_to_run: list[tuple[HierarchicalAgent, SkillTask]] = []
        for child_id, tasks in assignments.items():
            child = next(c for c in self.children if c.agent_id == child_id)
            for task in tasks:
                tasks_to_run.append((child, task))

        # Execute in parallel
        completed = await asyncio.gather(
            *[child.receive_task(task) for child, task in tasks_to_run],
            return_exceptions=True,
        )

        # Collect results
        for i, result in enumerate(completed):
            if not isinstance(result, Exception):
                child_id = tasks_to_run[i][1].assigned_to
                if child_id:
                    if child_id not in results:
                        results[child_id] = []
                    results[child_id].append(result)

        logger.debug(
            "delegated_tasks_completed",
            agent_id=self.agent_id,
            tasks_completed=len([r for r in completed if not isinstance(r, Exception)]),
            tasks_failed=len([r for r in completed if isinstance(r, Exception)]),
        )

        return results

    async def _synthesize_results(
        self, parent_task: SkillTask, child_results: dict[str, list[SkillTask]]
    ) -> str:
        """Synthesize results using synthesis skill.

        TODO: Integrate with LLM to use synthesis skill instructions for
        intelligent result aggregation. For now, uses simple concatenation.

        Args:
            parent_task: Parent task
            child_results: Results from child tasks

        Returns:
            Synthesized result string
        """
        # Future: Use LLM with synthesis skill instructions
        # For now, simple concatenation
        return self._simple_aggregate(child_results)

    def _simple_aggregate(self, child_results: dict[str, list[SkillTask]]) -> str:
        """Simple result aggregation without synthesis skill.

        Concatenates all sub-task results with newlines.

        Args:
            child_results: Results from child tasks

        Returns:
            Aggregated result string
        """
        all_results = []
        for tasks in child_results.values():
            for task in tasks:
                if task.result:
                    all_results.append(str(task.result))

        return "\n\n".join(all_results)

    @abstractmethod
    async def _execute_with_skills(self, task: SkillTask) -> SkillTask:
        """Execute task using atomic skills (worker implementation).

        This method must be implemented by concrete agent classes,
        particularly WorkerAgent.

        Args:
            task: Task to execute

        Returns:
            Completed task
        """
        pass

    async def receive_report(self, task: SkillTask) -> None:
        """Receive completion report from child.

        Args:
            task: Completed task from child

        Example:
            >>> await manager.receive_report(completed_task)
        """
        logger.debug(
            "report_received",
            agent_id=self.agent_id,
            task_id=task.id,
            status=task.status,
        )


# =============================================================================
# Concrete Agent Classes
# =============================================================================


class ExecutiveAgent(HierarchicalAgent):
    """Top-level strategic agent with executive skills.

    Responsible for:
    - Strategic planning and goal setting
    - High-level workflow orchestration
    - Delegating to manager agents
    - Aggregating final results

    Skills:
        - planner: Strategic task decomposition
        - orchestrator: Workflow coordination
        - reflection: Self-critique and improvement

    Example:
        >>> executive = ExecutiveAgent(
        ...     agent_id="executive_001",
        ...     skill_manager=skill_manager,
        ...     orchestrator=orchestrator
        ... )
        >>>
        >>> result = await executive.set_goal(
        ...     goal="Research quantum computing and synthesize findings",
        ...     context_budget=10000
        ... )
    """

    def __init__(
        self,
        agent_id: str,
        skill_manager: Any,
        orchestrator: Any,
    ) -> None:
        """Initialize executive agent.

        Args:
            agent_id: Unique agent identifier
            skill_manager: SkillLifecycleManager instance
            orchestrator: SkillOrchestrator instance
        """
        super().__init__(
            agent_id,
            AgentLevel.EXECUTIVE,
            skill_manager,
            available_skills=["planner", "orchestrator", "reflection"],
        )
        self.orchestrator = orchestrator

        logger.info("executive_agent_created", agent_id=agent_id)

    async def _execute_with_skills(self, task: SkillTask) -> SkillTask:
        """Executives delegate, not execute directly.

        Raises:
            NotImplementedError: Executives always delegate
        """
        raise NotImplementedError("Executive agents delegate, not execute")

    async def set_goal(self, goal: str, context_budget: int = 10000) -> SkillTask:
        """Set strategic goal and initiate execution.

        Creates top-level task and delegates to manager agents.

        Args:
            goal: Strategic goal description
            context_budget: Total context budget for goal (default: 10000)

        Returns:
            Completed task with results

        Example:
            >>> result = await executive.set_goal(
            ...     goal="Research quantum computing companies",
            ...     context_budget=8000
            ... )
            >>> result.status
            'completed'
        """
        task = SkillTask(
            id=f"goal_{uuid.uuid4().hex[:8]}",
            description=goal,
            required_skills=["planner", "orchestrator"],
            context_budget=context_budget,
            priority=10,
        )

        logger.info(
            "executive_goal_set",
            agent_id=self.agent_id,
            goal=goal[:100],
            budget=context_budget,
        )

        return await self.receive_task(task)


class ManagerAgent(HierarchicalAgent):
    """Mid-level coordination agent with domain skills.

    Responsible for:
    - Domain-specific task coordination
    - Decomposing high-level tasks into worker tasks
    - Delegating to worker agents
    - Aggregating worker results

    Domains:
        - research: web_search, retrieval, graph_query
        - analysis: validation, reasoning, reflection
        - synthesis: summarization, answer_generation

    Example:
        >>> research_manager = ManagerAgent(
        ...     agent_id="research_manager",
        ...     domain="research",
        ...     skill_manager=skill_manager,
        ...     domain_skills=["web_search", "retrieval", "graph_query"]
        ... )
    """

    def __init__(
        self,
        agent_id: str,
        domain: str,
        skill_manager: Any,
        domain_skills: list[str],
    ) -> None:
        """Initialize manager agent.

        Args:
            agent_id: Unique agent identifier
            domain: Domain name (research, analysis, synthesis)
            skill_manager: SkillLifecycleManager instance
            domain_skills: List of domain-specific skill names
        """
        super().__init__(
            agent_id,
            AgentLevel.MANAGER,
            skill_manager,
            available_skills=domain_skills,
        )
        self.domain = domain

        logger.info("manager_agent_created", agent_id=agent_id, domain=domain)

    async def _execute_with_skills(self, task: SkillTask) -> SkillTask:
        """Managers coordinate, not execute directly.

        Delegates to child workers instead of executing.

        Args:
            task: Task to coordinate

        Returns:
            Completed task
        """
        return await self._delegate_with_skills(task)


class WorkerAgent(HierarchicalAgent):
    """Leaf-level execution agent with atomic skills.

    Responsible for:
    - Executing individual atomic skills
    - Directly invoking skill instructions with LLM
    - Returning concrete results

    Skills:
        Atomic execution skills like:
        - retrieval, web_search, graph_query (research)
        - validation, reasoning, reflection (analysis)
        - summarization, answer_generation (synthesis)

    Example:
        >>> retrieval_worker = WorkerAgent(
        ...     agent_id="retrieval_worker",
        ...     skill_manager=skill_manager,
        ...     atomic_skills=["retrieval"],
        ...     llm=llm
        ... )
    """

    def __init__(
        self,
        agent_id: str,
        skill_manager: Any,
        atomic_skills: list[str],
        llm: BaseChatModel,
    ) -> None:
        """Initialize worker agent.

        Args:
            agent_id: Unique agent identifier
            skill_manager: SkillLifecycleManager instance
            atomic_skills: List of atomic skill names
            llm: Language model for skill execution
        """
        super().__init__(
            agent_id,
            AgentLevel.WORKER,
            skill_manager,
            available_skills=atomic_skills,
        )
        self.llm = llm

        logger.info("worker_agent_created", agent_id=agent_id, skills=atomic_skills)

    async def _execute_with_skills(self, task: SkillTask) -> SkillTask:
        """Execute task using atomic skills.

        Activates skills, retrieves instructions, and executes with LLM.

        Args:
            task: Task to execute

        Returns:
            Completed task with result

        Example:
            >>> task = SkillTask(
            ...     id="task_123",
            ...     description="Retrieve documents about quantum computing",
            ...     required_skills=["retrieval"],
            ...     context_budget=2000,
            ...     priority=5
            ... )
            >>> result = await worker._execute_with_skills(task)
            >>> result.status
            'completed'
        """
        try:
            # Get skill instructions for all required skills
            skill_instructions = []
            for skill_name in task.required_skills:
                if skill_name in self._active_skills:
                    # Get instructions from loaded content
                    instructions = self.skills._loaded_content.get(skill_name, "")
                    if instructions:
                        skill_instructions.append(instructions)

            combined_instructions = "\n\n".join(skill_instructions)

            # Execute with LLM
            prompt = f"""{combined_instructions}

Task: {task.description}

Execute the task according to the skill instructions above.

Result:"""

            response = await self.llm.ainvoke(prompt)
            task.result = response.content
            task.status = "completed"

            logger.info(
                "worker_task_completed",
                agent_id=self.agent_id,
                task_id=task.id,
                skills_used=task.required_skills,
            )

        except Exception as e:
            task.status = "failed"
            task.result = f"Execution failed: {e!s}"

            logger.error(
                "worker_task_failed",
                agent_id=self.agent_id,
                task_id=task.id,
                error=str(e),
                exc_info=True,
            )

        return task
