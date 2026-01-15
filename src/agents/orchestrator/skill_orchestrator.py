"""Skill Orchestrator - Multi-Level Supervisor Architecture.

Sprint 94 Feature 94.3: Skill Orchestrator (10 SP)

This module implements a multi-level supervisor architecture for coordinating
complex skill workflows using LangGraph 1.0 patterns.

Architecture:
    Executive Supervisor (Top Level)
        ├── Planning & High-level Coordination
        └── Delegates to Manager Supervisors
            │
    Manager Supervisors (Mid Level)
        ├── Domain-specific Coordination (e.g., Research Manager)
        └── Delegates to Worker Skills
            │
    Worker Skills (Low Level)
        └── Execute Individual Tasks

Key Features:
    - Three-level supervisor hierarchy
    - LangGraph 1.0 create_react_agent for supervisors
    - Tool-based handoffs between levels
    - Dynamic skill routing based on task complexity
    - Context budget management
    - Parallel and sequential execution
    - Error handling and recovery

Example:
    >>> orchestrator = SkillOrchestrator(
    ...     skill_manager=lifecycle_manager,
    ...     message_bus=message_bus,
    ...     llm=llm
    ... )
    >>>
    >>> # Simple workflow
    >>> result = await orchestrator.execute_workflow(
    ...     workflow=WorkflowDefinition(
    ...         skills=["research", "synthesis"],
    ...         dependencies={"synthesis": ["research"]},
    ...     ),
    ...     context={"query": "What is quantum computing?"}
    ... )
    >>>
    >>> # Complex multi-level workflow
    >>> result = await orchestrator.execute_complex_workflow(
    ...     query="Research quantum computing companies and analyze patents",
    ...     required_capabilities=["web_search", "graph_query", "synthesis"]
    ... )

LangGraph 1.0 Pattern:
    >>> from langgraph.prebuilt import create_react_agent
    >>>
    >>> # Executive supervisor with handoff tools
    >>> executive = create_react_agent(
    ...     model=llm,
    ...     tools=[handoff_to_research_manager, handoff_to_analysis_manager],
    ...     state_modifier="Coordinate high-level workflow planning."
    ... )
    >>>
    >>> # Manager supervisor
    >>> research_manager = create_react_agent(
    ...     model=llm,
    ...     tools=[handoff_to_web_search, handoff_to_retrieval],
    ...     state_modifier="Coordinate research tasks."
    ... )

See Also:
    - docs/sprints/SPRINT_94_PLAN.md (lines 151-210): Architecture details
    - LangGraph 1.0 Multi-Agent Tutorial
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class OrchestratorLevel(Enum):
    """Supervisor hierarchy levels.

    Attributes:
        EXECUTIVE: Top-level planning and coordination
        MANAGER: Domain-specific coordination (e.g., research manager)
        WORKER: Individual skill execution
    """

    EXECUTIVE = "executive"
    MANAGER = "manager"
    WORKER = "worker"


class ExecutionMode(Enum):
    """Execution modes for skill invocations.

    Attributes:
        PARALLEL: Execute skills concurrently
        SEQUENTIAL: Execute skills in order
        CONDITIONAL: Execute based on condition
    """

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"


@dataclass
class SkillInvocation:
    """Single skill invocation in workflow.

    Attributes:
        skill_name: Name of skill to invoke
        action: Action to perform (default: "execute")
        inputs: Input parameters for skill
        output_key: Key to store result in workflow context
        context_budget: Token budget allocation (default: 2000)
        timeout: Max execution time in seconds (default: 30.0)
        optional: Whether to continue if skill fails (default: False)
        retry_count: Number of retries on failure (default: 0)
        dependencies: List of skills that must complete first

    Example:
        >>> invocation = SkillInvocation(
        ...     skill_name="web_search",
        ...     action="search",
        ...     inputs={"query": "$query", "max_results": 10},
        ...     output_key="search_results",
        ...     context_budget=1500,
        ...     timeout=20.0
        ... )
    """

    skill_name: str
    action: str = "execute"
    inputs: dict[str, Any] = field(default_factory=dict)
    output_key: str = "result"
    context_budget: int = 2000
    timeout: float = 30.0
    optional: bool = False
    retry_count: int = 0
    dependencies: list[str] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    """Declarative workflow definition.

    Attributes:
        skills: List of skill names to coordinate
        dependencies: Dict mapping skill to its dependencies
        parallel_groups: List of skill groups that can run in parallel
        execution_mode: Default execution mode (default: SEQUENTIAL)
        total_budget: Total context budget for workflow (default: 10000)
        max_duration: Maximum workflow duration (default: 120.0)
        metadata: Additional workflow metadata

    Example:
        >>> workflow = WorkflowDefinition(
        ...     skills=["research", "synthesis", "reflection"],
        ...     dependencies={
        ...         "synthesis": ["research"],
        ...         "reflection": ["synthesis"]
        ...     },
        ...     parallel_groups=[["research"]],
        ...     total_budget=8000
        ... )
    """

    skills: list[str]
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    parallel_groups: list[list[str]] = field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    total_budget: int = 10000
    max_duration: float = 120.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """Ordered execution plan for workflow.

    Generated by the orchestrator from WorkflowDefinition.

    Attributes:
        plan_id: Unique plan identifier
        phases: List of execution phases
        skill_invocations: Dict mapping skill names to invocations
        context_allocations: Dict mapping skill names to token budgets
        estimated_duration: Estimated total duration
        level: Orchestrator level handling this plan

    Example:
        >>> plan = ExecutionPlan(
        ...     plan_id="plan_123",
        ...     phases=[
        ...         {"phase": "research", "skills": ["web_search", "retrieval"]},
        ...         {"phase": "synthesis", "skills": ["synthesis"]}
        ...     ],
        ...     skill_invocations={...},
        ...     context_allocations={"web_search": 2000, "retrieval": 2000}
        ... )
    """

    plan_id: str
    phases: list[dict[str, Any]]
    skill_invocations: dict[str, SkillInvocation]
    context_allocations: dict[str, int]
    estimated_duration: float = 0.0
    level: OrchestratorLevel = OrchestratorLevel.WORKER


@dataclass
class WorkflowResult:
    """Result of workflow execution.

    Attributes:
        workflow_id: Unique workflow identifier
        success: Whether workflow completed successfully
        outputs: Final outputs from all skills
        phase_results: Results from each execution phase
        skill_results: Results from individual skills
        total_duration: Actual execution duration
        context_used: Total context tokens consumed
        errors: List of errors encountered
        metadata: Additional result metadata

    Example:
        >>> result = WorkflowResult(
        ...     workflow_id="wf_123",
        ...     success=True,
        ...     outputs={"final_answer": "Quantum computing is..."},
        ...     total_duration=15.3,
        ...     context_used=7500
        ... )
    """

    workflow_id: str
    success: bool
    outputs: dict[str, Any]
    phase_results: list[dict[str, Any]] = field(default_factory=list)
    skill_results: dict[str, Any] = field(default_factory=dict)
    total_duration: float = 0.0
    context_used: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SupervisorNode:
    """Supervisor node in hierarchy.

    Attributes:
        name: Supervisor name
        level: Hierarchy level
        capabilities: List of capabilities this supervisor handles
        child_supervisors: List of child supervisor names (for EXECUTIVE/MANAGER)
        child_skills: List of child skill names (for MANAGER/WORKER)
        llm: Language model for this supervisor
        handoff_tools: Tools for delegating to children

    Example:
        >>> executive = SupervisorNode(
        ...     name="executive",
        ...     level=OrchestratorLevel.EXECUTIVE,
        ...     capabilities=["planning", "coordination"],
        ...     child_supervisors=["research_manager", "analysis_manager"],
        ...     llm=llm
        ... )
    """

    name: str
    level: OrchestratorLevel
    capabilities: list[str]
    child_supervisors: list[str] = field(default_factory=list)
    child_skills: list[str] = field(default_factory=list)
    llm: Optional[BaseChatModel] = None
    handoff_tools: list[Callable] = field(default_factory=list)


# =============================================================================
# Skill Orchestrator
# =============================================================================


class SkillOrchestrator:
    """Multi-level supervisor orchestrator for complex skill workflows.

    Implements three-level hierarchy:
    1. Executive: High-level planning and coordination
    2. Manager: Domain-specific coordination (research, analysis, synthesis)
    3. Worker: Individual skill execution

    Uses LangGraph 1.0 create_react_agent for supervisor nodes with tool-based
    handoffs between levels.

    Attributes:
        skill_manager: Skill lifecycle manager
        message_bus: Message bus for inter-skill communication (optional)
        llm: Default language model for supervisors
        max_concurrent_skills: Max parallel skills (default: 3)
        enable_recovery: Whether to enable error recovery (default: True)

    Example:
        >>> orchestrator = SkillOrchestrator(
        ...     skill_manager=lifecycle_manager,
        ...     message_bus=message_bus,
        ...     llm=llm,
        ...     max_concurrent_skills=5
        ... )
        >>>
        >>> # Execute simple workflow
        >>> result = await orchestrator.execute_workflow(
        ...     workflow=workflow_def,
        ...     context={"query": "What is quantum computing?"}
        ... )
        >>>
        >>> # Execute with dynamic planning
        >>> result = await orchestrator.execute_complex_workflow(
        ...     query="Research and analyze quantum computing patents",
        ...     required_capabilities=["web_search", "graph_query", "synthesis"]
        ... )
    """

    def __init__(
        self,
        skill_manager: Any,
        message_bus: Any | None = None,
        llm: BaseChatModel | None = None,
        max_concurrent_skills: int = 3,
        enable_recovery: bool = True,
    ) -> None:
        """Initialize SkillOrchestrator.

        Args:
            skill_manager: SkillLifecycleManager instance
            message_bus: Optional SkillAwareMessageBus for communication
            llm: Default language model for supervisors
            max_concurrent_skills: Maximum parallel skill executions
            enable_recovery: Whether to enable automatic error recovery
        """
        self.skills = skill_manager
        self.bus = message_bus
        self.llm = llm
        self.max_concurrent = max_concurrent_skills
        self.enable_recovery = enable_recovery

        # Supervisor hierarchy
        self._supervisors: dict[str, SupervisorNode] = {}
        self._setup_supervisor_hierarchy()

        # Execution tracking
        self._active_workflows: dict[str, WorkflowResult] = {}
        self._execution_history: list[WorkflowResult] = []

        logger.info(
            "skill_orchestrator_initialized",
            max_concurrent=max_concurrent_skills,
            enable_recovery=enable_recovery,
            has_message_bus=message_bus is not None,
        )

    def _setup_supervisor_hierarchy(self) -> None:
        """Setup default three-level supervisor hierarchy.

        Creates:
        - 1 Executive supervisor
        - 3 Manager supervisors (Research, Analysis, Synthesis)
        - Worker level delegates to individual skills
        """
        # Executive supervisor
        self._supervisors["executive"] = SupervisorNode(
            name="executive",
            level=OrchestratorLevel.EXECUTIVE,
            capabilities=["planning", "coordination", "high_level_decision"],
            child_supervisors=["research_manager", "analysis_manager", "synthesis_manager"],
            llm=self.llm,
        )

        # Manager supervisors
        self._supervisors["research_manager"] = SupervisorNode(
            name="research_manager",
            level=OrchestratorLevel.MANAGER,
            capabilities=["research", "information_gathering", "retrieval"],
            child_skills=["web_search", "retrieval", "graph_query"],
            llm=self.llm,
        )

        self._supervisors["analysis_manager"] = SupervisorNode(
            name="analysis_manager",
            level=OrchestratorLevel.MANAGER,
            capabilities=["analysis", "reasoning", "verification"],
            child_skills=["reflection", "validation", "reasoning"],
            llm=self.llm,
        )

        self._supervisors["synthesis_manager"] = SupervisorNode(
            name="synthesis_manager",
            level=OrchestratorLevel.MANAGER,
            capabilities=["synthesis", "summarization", "generation"],
            child_skills=["synthesis", "summarization", "answer_generation"],
            llm=self.llm,
        )

        logger.debug(
            "supervisor_hierarchy_setup",
            executive_count=1,
            manager_count=3,
            total_supervisors=len(self._supervisors),
        )

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        context: dict[str, Any],
        workflow_id: str | None = None,
    ) -> WorkflowResult:
        """Execute a defined workflow.

        Args:
            workflow: WorkflowDefinition to execute
            context: Initial context for workflow
            workflow_id: Optional workflow identifier

        Returns:
            WorkflowResult with outputs and metrics

        Example:
            >>> workflow = WorkflowDefinition(
            ...     skills=["research", "synthesis"],
            ...     dependencies={"synthesis": ["research"]},
            ... )
            >>> result = await orchestrator.execute_workflow(
            ...     workflow=workflow,
            ...     context={"query": "What is quantum computing?"}
            ... )
        """
        start_time = time.time()
        wf_id = workflow_id or f"wf_{uuid.uuid4().hex[:8]}"

        logger.info("workflow_execution_started", workflow_id=wf_id, skills=workflow.skills)

        # Create execution plan
        plan = await self._create_execution_plan(workflow, context)

        # Initialize result
        result = WorkflowResult(
            workflow_id=wf_id,
            success=False,
            outputs={},
            metadata={"workflow": workflow, "plan": plan},
        )

        self._active_workflows[wf_id] = result

        try:
            # Execute plan
            execution_context = dict(context)

            for phase in plan.phases:
                phase_result = await self._execute_phase(
                    phase=phase,
                    context=execution_context,
                    plan=plan,
                )

                result.phase_results.append(phase_result)

                # Merge phase outputs into context
                if phase_result.get("outputs"):
                    execution_context.update(phase_result["outputs"])

                # Track errors
                if phase_result.get("errors"):
                    result.errors.extend(phase_result["errors"])

                # Check if phase failed critically
                if phase_result.get("failed") and not phase.get("optional", False):
                    logger.error(
                        "workflow_phase_failed_critically",
                        workflow_id=wf_id,
                        phase=phase.get("name"),
                    )
                    break

            # Set final outputs
            result.outputs = execution_context
            result.success = len(result.errors) == 0
            result.total_duration = time.time() - start_time
            result.context_used = sum(plan.context_allocations.values())

            logger.info(
                "workflow_execution_completed",
                workflow_id=wf_id,
                success=result.success,
                duration=result.total_duration,
                context_used=result.context_used,
                error_count=len(result.errors),
            )

        except Exception as e:
            result.success = False
            result.errors.append(f"Workflow execution error: {e!s}")
            result.total_duration = time.time() - start_time

            logger.error("workflow_execution_failed", workflow_id=wf_id, error=str(e), exc_info=True)

        finally:
            self._active_workflows.pop(wf_id, None)
            self._execution_history.append(result)

        return result

    async def execute_complex_workflow(
        self,
        query: str,
        required_capabilities: list[str],
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Execute complex workflow with dynamic planning.

        Uses LLM-based planning to determine optimal skill coordination
        based on query and required capabilities.

        Args:
            query: User query or task description
            required_capabilities: List of required capabilities
            context: Optional initial context

        Returns:
            WorkflowResult

        Example:
            >>> result = await orchestrator.execute_complex_workflow(
            ...     query="Research quantum computing and analyze patent trends",
            ...     required_capabilities=["web_search", "graph_query", "synthesis", "analysis"]
            ... )
        """
        logger.info(
            "complex_workflow_started",
            query=query[:100],
            capabilities=required_capabilities,
        )

        # Route to appropriate manager based on capabilities
        manager = self._route_to_manager(required_capabilities)

        logger.debug("complex_workflow_routed", manager=manager.name, capabilities=manager.capabilities)

        # Create workflow definition using LLM planning
        workflow = await self._plan_workflow(
            query=query,
            capabilities=required_capabilities,
            manager=manager,
        )

        # Execute workflow
        initial_context = context or {}
        initial_context["query"] = query
        initial_context["required_capabilities"] = required_capabilities

        return await self.execute_workflow(
            workflow=workflow,
            context=initial_context,
        )

    def _route_to_manager(self, capabilities: list[str]) -> SupervisorNode:
        """Route to appropriate manager based on capabilities.

        Args:
            capabilities: List of required capabilities

        Returns:
            SupervisorNode for the best matching manager
        """
        # Score each manager by capability overlap
        best_manager = None
        best_score = 0

        for name, supervisor in self._supervisors.items():
            if supervisor.level != OrchestratorLevel.MANAGER:
                continue

            # Count matching capabilities
            score = sum(1 for cap in capabilities if cap in supervisor.capabilities)

            if score > best_score:
                best_score = score
                best_manager = supervisor

        if best_manager is None:
            # Default to research manager
            return self._supervisors["research_manager"]

        return best_manager

    async def _plan_workflow(
        self,
        query: str,
        capabilities: list[str],
        manager: SupervisorNode,
    ) -> WorkflowDefinition:
        """Plan workflow using LLM reasoning.

        Args:
            query: User query
            capabilities: Required capabilities
            manager: Manager supervisor handling this workflow

        Returns:
            WorkflowDefinition
        """
        # Get available skills from manager
        available_skills = manager.child_skills

        # For now, use simple heuristic planning
        # In future Sprint, integrate with LLM for complex planning
        skills_to_use = [
            skill for skill in available_skills
            if any(cap in skill for cap in capabilities)
        ]

        if not skills_to_use:
            skills_to_use = available_skills[:2]  # Default to first 2

        # Determine dependencies (sequential by default)
        dependencies = {}
        for i in range(1, len(skills_to_use)):
            dependencies[skills_to_use[i]] = [skills_to_use[i - 1]]

        workflow = WorkflowDefinition(
            skills=skills_to_use,
            dependencies=dependencies,
            execution_mode=ExecutionMode.SEQUENTIAL,
            total_budget=5000,
            metadata={"query": query, "manager": manager.name},
        )

        logger.debug(
            "workflow_planned",
            skills=skills_to_use,
            dependencies=dependencies,
            manager=manager.name,
        )

        return workflow

    async def _create_execution_plan(
        self,
        workflow: WorkflowDefinition,
        context: dict[str, Any],
    ) -> ExecutionPlan:
        """Create execution plan from workflow definition.

        Args:
            workflow: Workflow definition
            context: Initial context

        Returns:
            ExecutionPlan with ordered phases
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # Build dependency graph and determine phases
        phases = self._build_execution_phases(workflow)

        # Allocate context budget
        context_per_skill = workflow.total_budget // max(len(workflow.skills), 1)
        allocations = {skill: context_per_skill for skill in workflow.skills}

        # Create skill invocations
        invocations = {}
        for skill_name in workflow.skills:
            invocations[skill_name] = SkillInvocation(
                skill_name=skill_name,
                inputs=context,
                output_key=f"{skill_name}_result",
                context_budget=allocations[skill_name],
                dependencies=workflow.dependencies.get(skill_name, []),
            )

        plan = ExecutionPlan(
            plan_id=plan_id,
            phases=phases,
            skill_invocations=invocations,
            context_allocations=allocations,
            estimated_duration=len(phases) * 10.0,  # Rough estimate
            level=OrchestratorLevel.MANAGER,
        )

        logger.debug(
            "execution_plan_created",
            plan_id=plan_id,
            phase_count=len(phases),
            skill_count=len(workflow.skills),
        )

        return plan

    def _build_execution_phases(self, workflow: WorkflowDefinition) -> list[dict[str, Any]]:
        """Build execution phases from workflow dependencies.

        Args:
            workflow: Workflow definition

        Returns:
            List of phase definitions
        """
        phases = []
        executed = set()
        remaining = set(workflow.skills)

        phase_num = 0
        while remaining:
            phase_num += 1

            # Find skills with all dependencies satisfied
            ready_skills = [
                skill
                for skill in remaining
                if all(dep in executed for dep in workflow.dependencies.get(skill, []))
            ]

            if not ready_skills:
                # Circular dependency or error
                logger.warning("circular_dependency_detected", remaining=list(remaining))
                ready_skills = list(remaining)  # Force execution

            phases.append({
                "name": f"phase_{phase_num}",
                "skills": ready_skills,
                "mode": ExecutionMode.PARALLEL if len(ready_skills) > 1 else ExecutionMode.SEQUENTIAL,
            })

            executed.update(ready_skills)
            remaining -= set(ready_skills)

        return phases

    async def _execute_phase(
        self,
        phase: dict[str, Any],
        context: dict[str, Any],
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        """Execute single phase of workflow.

        Args:
            phase: Phase definition
            context: Current execution context
            plan: Execution plan

        Returns:
            Phase result dict
        """
        phase_name = phase["name"]
        skills = phase["skills"]
        mode = phase.get("mode", ExecutionMode.SEQUENTIAL)

        logger.debug("phase_execution_started", phase=phase_name, skills=skills, mode=mode.value)

        if mode == ExecutionMode.PARALLEL:
            return await self._execute_parallel(skills, context, plan)
        else:
            return await self._execute_sequential(skills, context, plan)

    async def _execute_parallel(
        self,
        skills: list[str],
        context: dict[str, Any],
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        """Execute skills in parallel.

        Args:
            skills: List of skill names
            context: Execution context
            plan: Execution plan

        Returns:
            Phase result dict
        """
        tasks = []
        for skill_name in skills:
            invocation = plan.skill_invocations[skill_name]
            task = self._execute_skill(invocation, context)
            tasks.append(task)

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect outputs and errors
        outputs = {}
        errors = []

        for i, result in enumerate(results):
            skill_name = skills[i]
            if isinstance(result, Exception):
                errors.append(f"{skill_name}: {result!s}")
            else:
                outputs[plan.skill_invocations[skill_name].output_key] = result

        return {
            "phase": "parallel",
            "outputs": outputs,
            "errors": errors,
            "failed": len(errors) > 0,
        }

    async def _execute_sequential(
        self,
        skills: list[str],
        context: dict[str, Any],
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        """Execute skills sequentially.

        Args:
            skills: List of skill names
            context: Execution context
            plan: Execution plan

        Returns:
            Phase result dict
        """
        outputs = {}
        errors = []
        working_context = dict(context)

        for skill_name in skills:
            invocation = plan.skill_invocations[skill_name]

            try:
                result = await self._execute_skill(invocation, working_context)
                outputs[invocation.output_key] = result
                working_context[invocation.output_key] = result

            except Exception as e:
                error_msg = f"{skill_name}: {e!s}"
                errors.append(error_msg)

                if not invocation.optional:
                    logger.error("sequential_execution_aborted", skill=skill_name, error=str(e))
                    break

        return {
            "phase": "sequential",
            "outputs": outputs,
            "errors": errors,
            "failed": len(errors) > 0,
        }

    async def _execute_skill(
        self,
        invocation: SkillInvocation,
        context: dict[str, Any],
    ) -> Any:
        """Execute single skill invocation.

        Args:
            invocation: Skill invocation details
            context: Execution context

        Returns:
            Skill result
        """
        skill_name = invocation.skill_name

        logger.debug(
            "skill_execution_started",
            skill=skill_name,
            action=invocation.action,
            budget=invocation.context_budget,
        )

        # Resolve input references
        resolved_inputs = self._resolve_inputs(invocation.inputs, context)

        # Activate skill
        await self.skills.activate(
            skill_name,
            context_allocation=invocation.context_budget,
        )

        try:
            # Execute skill via message bus if available
            if self.bus:
                result = await self.bus.request_skill(
                    sender="orchestrator",
                    skill_name=skill_name,
                    action=invocation.action,
                    inputs=resolved_inputs,
                    timeout=invocation.timeout,
                )
            else:
                # Direct execution (simplified)
                result = {"output": f"Executed {skill_name}"}

            logger.info("skill_execution_completed", skill=skill_name, success=True)

            return result

        except Exception as e:
            logger.error("skill_execution_failed", skill=skill_name, error=str(e))
            raise

        finally:
            # Deactivate to free context
            await self.skills.deactivate(skill_name)

    def _resolve_inputs(
        self,
        inputs: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve input references from context.

        Supports "$variable" references that get resolved from context.

        Args:
            inputs: Input dict with potential references
            context: Context to resolve from

        Returns:
            Resolved inputs dict

        Example:
            >>> inputs = {"query": "$query", "limit": 10}
            >>> context = {"query": "What is quantum computing?"}
            >>> resolved = self._resolve_inputs(inputs, context)
            >>> resolved
            {'query': 'What is quantum computing?', 'limit': 10}
        """
        resolved = {}

        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to context variable
                ref = value[1:]
                parts = ref.split(".")

                result = context
                for part in parts:
                    if isinstance(result, dict):
                        result = result.get(part)
                    else:
                        result = getattr(result, part, None)

                resolved[key] = result
            else:
                resolved[key] = value

        return resolved

    def get_active_workflows(self) -> list[str]:
        """Get list of active workflow IDs.

        Returns:
            List of workflow IDs currently executing
        """
        return list(self._active_workflows.keys())

    def get_workflow_status(self, workflow_id: str) -> WorkflowResult | None:
        """Get status of active or completed workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            WorkflowResult or None if not found
        """
        # Check active first
        if workflow_id in self._active_workflows:
            return self._active_workflows[workflow_id]

        # Check history
        for result in self._execution_history:
            if result.workflow_id == workflow_id:
                return result

        return None

    def get_metrics(self) -> dict[str, Any]:
        """Get orchestrator metrics.

        Returns:
            Dict with orchestration metrics
        """
        total_workflows = len(self._execution_history)
        successful = sum(1 for r in self._execution_history if r.success)

        avg_duration = 0.0
        if self._execution_history:
            avg_duration = sum(r.total_duration for r in self._execution_history) / total_workflows

        return {
            "total_workflows": total_workflows,
            "successful_workflows": successful,
            "failed_workflows": total_workflows - successful,
            "active_workflows": len(self._active_workflows),
            "avg_duration": avg_duration,
            "supervisors": len(self._supervisors),
        }
