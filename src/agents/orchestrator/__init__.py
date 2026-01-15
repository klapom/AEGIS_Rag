"""Skill Orchestration Module.

Sprint 94 Feature 94.3: Skill Orchestrator (10 SP)

This module provides multi-level orchestration for complex skill workflows:
- Multi-level supervisor architecture (Executive → Manager → Worker)
- Dynamic skill routing based on task requirements
- Parallel and sequential execution patterns
- Context budget management across skills
- Error handling and recovery

Key Components:
    - SkillOrchestrator: Main coordinator for multi-skill workflows
    - OrchestratorLevel: Hierarchy levels (EXECUTIVE, MANAGER, WORKER)
    - WorkflowDefinition: Declarative workflow definitions
    - ExecutionPlan: Ordered skill invocation plans

Example:
    >>> from src.agents.orchestrator import SkillOrchestrator, OrchestratorLevel
    >>> from src.agents.orchestrator import WorkflowDefinition, SkillInvocation
    >>>
    >>> orchestrator = SkillOrchestrator(
    ...     skill_manager=lifecycle_manager,
    ...     message_bus=message_bus,
    ...     llm=llm
    ... )
    >>>
    >>> # Define workflow
    >>> workflow = WorkflowDefinition(
    ...     skills=["research", "synthesis", "reflection"],
    ...     dependencies={"synthesis": ["research"], "reflection": ["synthesis"]},
    ...     parallel_groups=[["research"]]
    ... )
    >>>
    >>> # Execute workflow
    >>> result = await orchestrator.execute_workflow(
    ...     workflow=workflow,
    ...     context={"query": "Analyze quantum computing trends"}
    ... )

See Also:
    - docs/sprints/SPRINT_94_PLAN.md: Feature specification
    - src/agents/skills/lifecycle.py: Skill lifecycle management
    - src/agents/messaging/message_bus.py: Inter-agent messaging
"""

from src.agents.orchestrator.skill_orchestrator import (
    ExecutionPlan,
    OrchestratorLevel,
    SkillInvocation,
    SkillOrchestrator,
    SupervisorNode,
    WorkflowDefinition,
    WorkflowResult,
)

__all__ = [
    "SkillOrchestrator",
    "OrchestratorLevel",
    "WorkflowDefinition",
    "SkillInvocation",
    "ExecutionPlan",
    "WorkflowResult",
    "SupervisorNode",
]
