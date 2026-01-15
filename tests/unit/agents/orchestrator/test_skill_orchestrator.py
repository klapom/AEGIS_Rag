"""Unit tests for SkillOrchestrator.

Sprint 94 Feature 94.3: Skill Orchestrator (10 SP)

Test Coverage:
    1. Initialization and setup
    2. Supervisor hierarchy creation
    3. Workflow planning
    4. Execution plan generation
    5. Phase execution (parallel and sequential)
    6. Skill invocation
    7. Dynamic routing
    8. Error handling and recovery
    9. Context budget management
    10. Metrics and monitoring
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.orchestrator.skill_orchestrator import (
    ExecutionMode,
    ExecutionPlan,
    OrchestratorLevel,
    SkillInvocation,
    SkillOrchestrator,
    SupervisorNode,
    WorkflowDefinition,
    WorkflowResult,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_skill_manager():
    """Mock SkillLifecycleManager."""
    manager = MagicMock()
    manager.activate = AsyncMock(return_value="skill instructions")
    manager.deactivate = AsyncMock(return_value=True)
    manager.get_state = MagicMock(return_value="LOADED")
    manager.get_available_budget = MagicMock(return_value=8000)
    return manager


@pytest.fixture
def mock_message_bus():
    """Mock SkillAwareMessageBus."""
    bus = MagicMock()
    bus.request_skill = AsyncMock(return_value={"output": "skill result"})
    return bus


@pytest.fixture
def mock_llm():
    """Mock language model."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="LLM response"))
    return llm


@pytest.fixture
def orchestrator(mock_skill_manager, mock_message_bus, mock_llm):
    """Create SkillOrchestrator instance."""
    return SkillOrchestrator(
        skill_manager=mock_skill_manager,
        message_bus=mock_message_bus,
        llm=mock_llm,
        max_concurrent_skills=3,
    )


@pytest.fixture
def simple_workflow():
    """Simple sequential workflow."""
    return WorkflowDefinition(
        skills=["research", "synthesis"],
        dependencies={"synthesis": ["research"]},
        execution_mode=ExecutionMode.SEQUENTIAL,
        total_budget=5000,
    )


@pytest.fixture
def parallel_workflow():
    """Workflow with parallel execution."""
    return WorkflowDefinition(
        skills=["web_search", "retrieval", "graph_query"],
        parallel_groups=[["web_search", "retrieval", "graph_query"]],
        execution_mode=ExecutionMode.PARALLEL,
        total_budget=6000,
    )


@pytest.fixture
def complex_workflow():
    """Complex multi-phase workflow."""
    return WorkflowDefinition(
        skills=["research", "web_search", "synthesis", "reflection"],
        dependencies={
            "web_search": ["research"],
            "synthesis": ["web_search"],
            "reflection": ["synthesis"],
        },
        parallel_groups=[["research", "web_search"]],
        total_budget=10000,
    )


# =============================================================================
# Test Initialization
# =============================================================================


def test_orchestrator_initialization(orchestrator, mock_skill_manager, mock_message_bus):
    """Test orchestrator initializes correctly."""
    assert orchestrator.skills == mock_skill_manager
    assert orchestrator.bus == mock_message_bus
    assert orchestrator.max_concurrent == 3
    assert orchestrator.enable_recovery is True
    assert len(orchestrator._supervisors) > 0
    assert len(orchestrator._active_workflows) == 0


def test_orchestrator_without_message_bus(mock_skill_manager, mock_llm):
    """Test orchestrator works without message bus."""
    orchestrator = SkillOrchestrator(
        skill_manager=mock_skill_manager,
        message_bus=None,
        llm=mock_llm,
    )

    assert orchestrator.bus is None
    assert orchestrator.skills == mock_skill_manager


# =============================================================================
# Test Supervisor Hierarchy
# =============================================================================


def test_supervisor_hierarchy_setup(orchestrator):
    """Test supervisor hierarchy is set up correctly."""
    # Check executive exists
    assert "executive" in orchestrator._supervisors
    executive = orchestrator._supervisors["executive"]
    assert executive.level == OrchestratorLevel.EXECUTIVE
    assert len(executive.child_supervisors) == 3

    # Check managers exist
    assert "research_manager" in orchestrator._supervisors
    assert "analysis_manager" in orchestrator._supervisors
    assert "synthesis_manager" in orchestrator._supervisors

    research = orchestrator._supervisors["research_manager"]
    assert research.level == OrchestratorLevel.MANAGER
    assert len(research.child_skills) > 0


def test_supervisor_node_creation():
    """Test SupervisorNode dataclass."""
    supervisor = SupervisorNode(
        name="test_supervisor",
        level=OrchestratorLevel.MANAGER,
        capabilities=["test", "capability"],
        child_skills=["skill1", "skill2"],
    )

    assert supervisor.name == "test_supervisor"
    assert supervisor.level == OrchestratorLevel.MANAGER
    assert supervisor.capabilities == ["test", "capability"]
    assert supervisor.child_skills == ["skill1", "skill2"]


# =============================================================================
# Test Workflow Definitions
# =============================================================================


def test_workflow_definition_simple(simple_workflow):
    """Test simple workflow definition."""
    assert len(simple_workflow.skills) == 2
    assert simple_workflow.dependencies == {"synthesis": ["research"]}
    assert simple_workflow.execution_mode == ExecutionMode.SEQUENTIAL
    assert simple_workflow.total_budget == 5000


def test_workflow_definition_parallel(parallel_workflow):
    """Test parallel workflow definition."""
    assert len(parallel_workflow.skills) == 3
    assert len(parallel_workflow.parallel_groups) == 1
    assert len(parallel_workflow.parallel_groups[0]) == 3
    assert parallel_workflow.execution_mode == ExecutionMode.PARALLEL


def test_workflow_definition_complex(complex_workflow):
    """Test complex multi-phase workflow."""
    assert len(complex_workflow.skills) == 4
    assert len(complex_workflow.dependencies) == 3
    assert len(complex_workflow.parallel_groups) == 1
    assert complex_workflow.total_budget == 10000


# =============================================================================
# Test Execution Planning
# =============================================================================


@pytest.mark.asyncio
async def test_create_execution_plan_simple(orchestrator, simple_workflow):
    """Test execution plan creation for simple workflow."""
    context = {"query": "test query"}
    plan = await orchestrator._create_execution_plan(simple_workflow, context)

    assert isinstance(plan, ExecutionPlan)
    assert plan.plan_id.startswith("plan_")
    assert len(plan.phases) >= 1
    assert len(plan.skill_invocations) == 2
    assert "research" in plan.context_allocations
    assert "synthesis" in plan.context_allocations


@pytest.mark.asyncio
async def test_create_execution_plan_parallel(orchestrator, parallel_workflow):
    """Test execution plan for parallel workflow."""
    context = {"query": "test query"}
    plan = await orchestrator._create_execution_plan(parallel_workflow, context)

    assert len(plan.skill_invocations) == 3
    # All skills should be in same phase since they're parallel
    assert len(plan.phases) >= 1


@pytest.mark.asyncio
async def test_build_execution_phases_sequential(orchestrator, simple_workflow):
    """Test phase building for sequential workflow."""
    phases = orchestrator._build_execution_phases(simple_workflow)

    # Should have 2 phases (research first, then synthesis)
    assert len(phases) >= 2
    assert phases[0]["skills"] == ["research"]
    assert "synthesis" in phases[1]["skills"] or len(phases) > 2


@pytest.mark.asyncio
async def test_build_execution_phases_parallel(orchestrator, parallel_workflow):
    """Test phase building for parallel workflow."""
    phases = orchestrator._build_execution_phases(parallel_workflow)

    # All skills can run in parallel
    assert len(phases) >= 1
    first_phase = phases[0]
    assert len(first_phase["skills"]) == 3


# =============================================================================
# Test Skill Invocations
# =============================================================================


def test_skill_invocation_creation():
    """Test SkillInvocation dataclass."""
    invocation = SkillInvocation(
        skill_name="test_skill",
        action="execute",
        inputs={"query": "test"},
        output_key="result",
        context_budget=2000,
        timeout=30.0,
    )

    assert invocation.skill_name == "test_skill"
    assert invocation.action == "execute"
    assert invocation.inputs == {"query": "test"}
    assert invocation.context_budget == 2000
    assert invocation.timeout == 30.0
    assert invocation.optional is False


def test_skill_invocation_with_dependencies():
    """Test SkillInvocation with dependencies."""
    invocation = SkillInvocation(
        skill_name="synthesis",
        dependencies=["research", "web_search"],
        inputs={"data": "$research_result"},
    )

    assert invocation.dependencies == ["research", "web_search"]
    assert invocation.inputs["data"] == "$research_result"


# =============================================================================
# Test Input Resolution
# =============================================================================


def test_resolve_inputs_simple(orchestrator):
    """Test simple input resolution."""
    inputs = {"query": "$query", "limit": 10}
    context = {"query": "What is quantum computing?"}

    resolved = orchestrator._resolve_inputs(inputs, context)

    assert resolved["query"] == "What is quantum computing?"
    assert resolved["limit"] == 10


def test_resolve_inputs_nested(orchestrator):
    """Test nested input resolution."""
    inputs = {"title": "$document.title"}
    context = {"document": {"title": "Test Document", "id": "123"}}

    resolved = orchestrator._resolve_inputs(inputs, context)

    assert resolved["title"] == "Test Document"


def test_resolve_inputs_no_reference(orchestrator):
    """Test input resolution without references."""
    inputs = {"query": "direct query", "limit": 5}
    context = {}

    resolved = orchestrator._resolve_inputs(inputs, context)

    assert resolved["query"] == "direct query"
    assert resolved["limit"] == 5


def test_resolve_inputs_missing_reference(orchestrator):
    """Test input resolution with missing reference."""
    inputs = {"query": "$missing_var"}
    context = {"other_var": "value"}

    resolved = orchestrator._resolve_inputs(inputs, context)

    assert resolved["query"] is None


# =============================================================================
# Test Workflow Execution
# =============================================================================


@pytest.mark.asyncio
async def test_execute_workflow_simple(orchestrator, simple_workflow, mock_skill_manager, mock_message_bus):
    """Test simple workflow execution."""
    context = {"query": "test query"}

    result = await orchestrator.execute_workflow(
        workflow=simple_workflow,
        context=context,
    )

    assert isinstance(result, WorkflowResult)
    assert result.workflow_id.startswith("wf_")
    assert result.total_duration >= 0
    assert "query" in result.outputs

    # Skills should have been activated and deactivated
    assert mock_skill_manager.activate.call_count >= 2
    assert mock_skill_manager.deactivate.call_count >= 2


@pytest.mark.asyncio
async def test_execute_workflow_with_id(orchestrator, simple_workflow):
    """Test workflow execution with custom ID."""
    context = {"query": "test"}
    workflow_id = "custom_wf_123"

    result = await orchestrator.execute_workflow(
        workflow=simple_workflow,
        context=context,
        workflow_id=workflow_id,
    )

    assert result.workflow_id == workflow_id


@pytest.mark.asyncio
async def test_execute_workflow_tracks_active(orchestrator, simple_workflow):
    """Test workflow execution tracks active workflows."""
    context = {"query": "test"}

    # Mock to prevent actual execution
    with patch.object(orchestrator, "_execute_phase", new=AsyncMock(return_value={"outputs": {}, "errors": []})):
        result = await orchestrator.execute_workflow(
            workflow=simple_workflow,
            context=context,
        )

    # Should be in history after completion
    assert result.workflow_id in [r.workflow_id for r in orchestrator._execution_history]
    assert result.workflow_id not in orchestrator._active_workflows


# =============================================================================
# Test Phase Execution
# =============================================================================


@pytest.mark.asyncio
async def test_execute_parallel_phase(orchestrator):
    """Test parallel phase execution."""
    skills = ["skill1", "skill2", "skill3"]
    context = {"query": "test"}

    plan = ExecutionPlan(
        plan_id="test_plan",
        phases=[],
        skill_invocations={
            "skill1": SkillInvocation(skill_name="skill1", output_key="result1"),
            "skill2": SkillInvocation(skill_name="skill2", output_key="result2"),
            "skill3": SkillInvocation(skill_name="skill3", output_key="result3"),
        },
        context_allocations={"skill1": 1000, "skill2": 1000, "skill3": 1000},
    )

    result = await orchestrator._execute_parallel(skills, context, plan)

    assert result["phase"] == "parallel"
    assert "outputs" in result
    assert len(result["outputs"]) == 3


@pytest.mark.asyncio
async def test_execute_sequential_phase(orchestrator):
    """Test sequential phase execution."""
    skills = ["skill1", "skill2"]
    context = {"query": "test"}

    plan = ExecutionPlan(
        plan_id="test_plan",
        phases=[],
        skill_invocations={
            "skill1": SkillInvocation(skill_name="skill1", output_key="result1"),
            "skill2": SkillInvocation(skill_name="skill2", output_key="result2"),
        },
        context_allocations={"skill1": 1000, "skill2": 1000},
    )

    result = await orchestrator._execute_sequential(skills, context, plan)

    assert result["phase"] == "sequential"
    assert "outputs" in result
    assert len(result["outputs"]) == 2


@pytest.mark.asyncio
async def test_execute_sequential_with_error(orchestrator):
    """Test sequential execution handles errors."""
    skills = ["skill1", "skill2"]
    context = {"query": "test"}

    plan = ExecutionPlan(
        plan_id="test_plan",
        phases=[],
        skill_invocations={
            "skill1": SkillInvocation(skill_name="skill1", output_key="result1", optional=False),
            "skill2": SkillInvocation(skill_name="skill2", output_key="result2"),
        },
        context_allocations={"skill1": 1000, "skill2": 1000},
    )

    # Mock first skill to fail
    with patch.object(orchestrator, "_execute_skill", side_effect=Exception("Skill failed")):
        result = await orchestrator._execute_sequential(skills, context, plan)

    assert result["failed"] is True
    assert len(result["errors"]) > 0
    assert "Skill failed" in result["errors"][0]


# =============================================================================
# Test Skill Execution
# =============================================================================


@pytest.mark.asyncio
async def test_execute_skill_with_bus(orchestrator, mock_skill_manager, mock_message_bus):
    """Test skill execution via message bus."""
    invocation = SkillInvocation(
        skill_name="test_skill",
        action="execute",
        inputs={"query": "test"},
        context_budget=2000,
    )
    context = {"query": "test"}

    result = await orchestrator._execute_skill(invocation, context)

    # Should activate, execute via bus, and deactivate
    mock_skill_manager.activate.assert_called_once_with("test_skill", context_allocation=2000)
    mock_message_bus.request_skill.assert_called_once()
    mock_skill_manager.deactivate.assert_called_once_with("test_skill")

    assert result is not None


@pytest.mark.asyncio
async def test_execute_skill_without_bus(mock_skill_manager, mock_llm):
    """Test skill execution without message bus."""
    orchestrator = SkillOrchestrator(
        skill_manager=mock_skill_manager,
        message_bus=None,
        llm=mock_llm,
    )

    invocation = SkillInvocation(
        skill_name="test_skill",
        inputs={"query": "test"},
    )
    context = {"query": "test"}

    result = await orchestrator._execute_skill(invocation, context)

    # Should still activate and deactivate
    mock_skill_manager.activate.assert_called_once()
    mock_skill_manager.deactivate.assert_called_once()

    assert result is not None


@pytest.mark.asyncio
async def test_execute_skill_handles_error(orchestrator, mock_skill_manager, mock_message_bus):
    """Test skill execution handles errors."""
    invocation = SkillInvocation(
        skill_name="test_skill",
        inputs={"query": "test"},
    )
    context = {"query": "test"}

    # Mock bus to raise error
    mock_message_bus.request_skill.side_effect = Exception("Execution failed")

    with pytest.raises(Exception, match="Execution failed"):
        await orchestrator._execute_skill(invocation, context)

    # Should still deactivate on error
    mock_skill_manager.deactivate.assert_called_once()


# =============================================================================
# Test Complex Workflow Execution
# =============================================================================


@pytest.mark.asyncio
async def test_execute_complex_workflow(orchestrator):
    """Test complex workflow with dynamic planning."""
    query = "Research quantum computing companies"
    capabilities = ["web_search", "graph_query", "synthesis"]

    result = await orchestrator.execute_complex_workflow(
        query=query,
        required_capabilities=capabilities,
    )

    assert isinstance(result, WorkflowResult)
    assert result.outputs.get("query") == query
    assert result.outputs.get("required_capabilities") == capabilities


@pytest.mark.asyncio
async def test_execute_complex_workflow_with_context(orchestrator):
    """Test complex workflow with initial context."""
    query = "Analyze patent trends"
    capabilities = ["graph_query", "analysis"]
    context = {"domain": "technology"}

    result = await orchestrator.execute_complex_workflow(
        query=query,
        required_capabilities=capabilities,
        context=context,
    )

    assert result.outputs.get("domain") == "technology"


# =============================================================================
# Test Routing
# =============================================================================


def test_route_to_manager_research(orchestrator):
    """Test routing to research manager."""
    capabilities = ["web_search", "retrieval"]

    manager = orchestrator._route_to_manager(capabilities)

    assert manager.name == "research_manager"
    assert "research" in manager.capabilities


def test_route_to_manager_analysis(orchestrator):
    """Test routing to analysis manager."""
    capabilities = ["analysis", "reasoning"]

    manager = orchestrator._route_to_manager(capabilities)

    assert manager.name == "analysis_manager"
    assert "analysis" in manager.capabilities


def test_route_to_manager_synthesis(orchestrator):
    """Test routing to synthesis manager."""
    capabilities = ["synthesis", "summarization"]

    manager = orchestrator._route_to_manager(capabilities)

    assert manager.name == "synthesis_manager"
    assert "synthesis" in manager.capabilities


def test_route_to_manager_default(orchestrator):
    """Test default routing when no match."""
    capabilities = ["unknown_capability"]

    manager = orchestrator._route_to_manager(capabilities)

    # Should default to research manager
    assert manager.name == "research_manager"


# =============================================================================
# Test Workflow Planning
# =============================================================================


@pytest.mark.asyncio
async def test_plan_workflow_basic(orchestrator):
    """Test basic workflow planning."""
    query = "Test query"
    capabilities = ["research", "synthesis"]
    manager = orchestrator._supervisors["research_manager"]

    workflow = await orchestrator._plan_workflow(
        query=query,
        capabilities=capabilities,
        manager=manager,
    )

    assert isinstance(workflow, WorkflowDefinition)
    assert len(workflow.skills) > 0
    assert workflow.metadata["query"] == query
    assert workflow.metadata["manager"] == manager.name


# =============================================================================
# Test Workflow Status and Metrics
# =============================================================================


def test_get_active_workflows(orchestrator):
    """Test getting active workflows."""
    active = orchestrator.get_active_workflows()

    assert isinstance(active, list)
    assert len(active) == 0


def test_get_workflow_status_not_found(orchestrator):
    """Test getting status of non-existent workflow."""
    status = orchestrator.get_workflow_status("non_existent_id")

    assert status is None


@pytest.mark.asyncio
async def test_get_workflow_status_completed(orchestrator, simple_workflow):
    """Test getting status of completed workflow."""
    # Execute workflow
    result = await orchestrator.execute_workflow(simple_workflow, {"query": "test"})

    # Should be in history
    status = orchestrator.get_workflow_status(result.workflow_id)

    assert status is not None
    assert status.workflow_id == result.workflow_id
    assert status.total_duration >= 0


def test_get_metrics_empty(orchestrator):
    """Test metrics with no executions."""
    metrics = orchestrator.get_metrics()

    assert metrics["total_workflows"] == 0
    assert metrics["successful_workflows"] == 0
    assert metrics["failed_workflows"] == 0
    assert metrics["active_workflows"] == 0
    assert metrics["supervisors"] > 0


@pytest.mark.asyncio
async def test_get_metrics_after_execution(orchestrator, simple_workflow):
    """Test metrics after workflow execution."""
    await orchestrator.execute_workflow(simple_workflow, {"query": "test"})

    metrics = orchestrator.get_metrics()

    assert metrics["total_workflows"] == 1
    assert metrics["avg_duration"] > 0


# =============================================================================
# Test Error Handling
# =============================================================================


@pytest.mark.asyncio
async def test_workflow_handles_execution_error(orchestrator, simple_workflow):
    """Test workflow handles execution errors gracefully."""
    context = {"query": "test"}

    # Mock phase execution to fail
    with patch.object(orchestrator, "_execute_phase", side_effect=Exception("Phase failed")):
        result = await orchestrator.execute_workflow(simple_workflow, context)

    assert result.success is False
    assert len(result.errors) > 0
    assert "Phase failed" in result.errors[0]


@pytest.mark.asyncio
async def test_parallel_execution_handles_partial_failure(orchestrator):
    """Test parallel execution handles partial failures."""
    skills = ["skill1", "skill2", "skill3"]
    context = {"query": "test"}

    plan = ExecutionPlan(
        plan_id="test_plan",
        phases=[],
        skill_invocations={
            "skill1": SkillInvocation(skill_name="skill1", output_key="result1"),
            "skill2": SkillInvocation(skill_name="skill2", output_key="result2"),
            "skill3": SkillInvocation(skill_name="skill3", output_key="result3"),
        },
        context_allocations={"skill1": 1000, "skill2": 1000, "skill3": 1000},
    )

    # Mock one skill to fail
    call_count = 0

    async def mock_execute(inv, ctx):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("Skill 2 failed")
        return {"output": f"result_{call_count}"}

    with patch.object(orchestrator, "_execute_skill", side_effect=mock_execute):
        result = await orchestrator._execute_parallel(skills, context, plan)

    # Should have 2 successes and 1 failure
    assert len(result["outputs"]) == 2
    assert len(result["errors"]) == 1
    assert "Skill 2 failed" in result["errors"][0]


# =============================================================================
# Test Context Budget Management
# =============================================================================


@pytest.mark.asyncio
async def test_context_budget_allocation(orchestrator, simple_workflow):
    """Test context budget is allocated correctly."""
    context = {"query": "test"}
    plan = await orchestrator._create_execution_plan(simple_workflow, context)

    total_allocated = sum(plan.context_allocations.values())

    assert total_allocated <= simple_workflow.total_budget
    assert len(plan.context_allocations) == len(simple_workflow.skills)


@pytest.mark.asyncio
async def test_context_budget_per_skill(orchestrator, simple_workflow):
    """Test each skill gets fair context budget."""
    context = {"query": "test"}
    plan = await orchestrator._create_execution_plan(simple_workflow, context)

    expected_per_skill = simple_workflow.total_budget // len(simple_workflow.skills)

    for skill, budget in plan.context_allocations.items():
        assert budget == expected_per_skill


# =============================================================================
# Test Workflow Result
# =============================================================================


def test_workflow_result_creation():
    """Test WorkflowResult dataclass."""
    result = WorkflowResult(
        workflow_id="wf_123",
        success=True,
        outputs={"answer": "test answer"},
        total_duration=10.5,
        context_used=3000,
    )

    assert result.workflow_id == "wf_123"
    assert result.success is True
    assert result.outputs["answer"] == "test answer"
    assert result.total_duration == 10.5
    assert result.context_used == 3000
    assert len(result.errors) == 0


def test_workflow_result_with_errors():
    """Test WorkflowResult with errors."""
    result = WorkflowResult(
        workflow_id="wf_123",
        success=False,
        outputs={},
        errors=["Error 1", "Error 2"],
    )

    assert result.success is False
    assert len(result.errors) == 2


# =============================================================================
# Test Execution Modes
# =============================================================================


def test_execution_mode_enum():
    """Test ExecutionMode enum."""
    assert ExecutionMode.PARALLEL.value == "parallel"
    assert ExecutionMode.SEQUENTIAL.value == "sequential"
    assert ExecutionMode.CONDITIONAL.value == "conditional"


def test_orchestrator_level_enum():
    """Test OrchestratorLevel enum."""
    assert OrchestratorLevel.EXECUTIVE.value == "executive"
    assert OrchestratorLevel.MANAGER.value == "manager"
    assert OrchestratorLevel.WORKER.value == "worker"
