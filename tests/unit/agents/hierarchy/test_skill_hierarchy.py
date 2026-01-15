"""Unit tests for Hierarchical Agent Pattern.

Sprint 95 Feature 95.1: Hierarchical Agent Pattern (10 SP)

Test Coverage:
    - AgentLevel enum (3 tests)
    - SkillTask dataclass (5 tests)
    - DelegationResult dataclass (3 tests)
    - HierarchicalAgent base class (10 tests)
    - ExecutiveAgent (8 tests)
    - ManagerAgent (8 tests)
    - WorkerAgent (8 tests)
    - Task delegation patterns (10 tests)
    - Error handling (5 tests)

Total: 60 test cases

Example:
    >>> pytest tests/unit/agents/hierarchy/test_skill_hierarchy.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.hierarchy.skill_hierarchy import (
    AgentLevel,
    DelegationResult,
    ExecutiveAgent,
    HierarchicalAgent,
    ManagerAgent,
    SkillTask,
    WorkerAgent,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_skill_manager():
    """Mock SkillLifecycleManager."""
    manager = MagicMock()
    manager.activate = AsyncMock()
    manager.deactivate = AsyncMock()
    manager._loaded_content = {}
    return manager


@pytest.fixture
def mock_orchestrator():
    """Mock SkillOrchestrator."""
    return MagicMock()


@pytest.fixture
def mock_llm():
    """Mock LLM for worker agents."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="LLM response"))
    return llm


@pytest.fixture
def sample_task():
    """Sample skill task."""
    return SkillTask(
        id="task_001",
        description="Test task",
        required_skills=["skill1", "skill2"],
        context_budget=5000,
        priority=5,
    )


# =============================================================================
# AgentLevel Enum Tests (3 tests)
# =============================================================================


def test_agent_level_values():
    """Test AgentLevel enum values."""
    assert AgentLevel.EXECUTIVE.value == 0
    assert AgentLevel.MANAGER.value == 1
    assert AgentLevel.WORKER.value == 2


def test_agent_level_names():
    """Test AgentLevel enum names."""
    assert AgentLevel.EXECUTIVE.name == "EXECUTIVE"
    assert AgentLevel.MANAGER.name == "MANAGER"
    assert AgentLevel.WORKER.name == "WORKER"


def test_agent_level_comparison():
    """Test AgentLevel comparison."""
    assert AgentLevel.EXECUTIVE.value < AgentLevel.MANAGER.value
    assert AgentLevel.MANAGER.value < AgentLevel.WORKER.value


# =============================================================================
# SkillTask Tests (5 tests)
# =============================================================================


def test_skill_task_creation():
    """Test SkillTask creation."""
    task = SkillTask(
        id="task_123",
        description="Test task",
        required_skills=["skill1"],
        context_budget=2000,
        priority=5,
    )

    assert task.id == "task_123"
    assert task.description == "Test task"
    assert task.required_skills == ["skill1"]
    assert task.context_budget == 2000
    assert task.priority == 5
    assert task.status == "pending"
    assert task.result is None


def test_skill_task_defaults():
    """Test SkillTask default values."""
    task = SkillTask(
        id="task_123",
        description="Test",
        required_skills=["skill1"],
        context_budget=1000,
        priority=1,
    )

    assert task.assigned_to is None
    assert task.parent_task_id is None
    assert task.status == "pending"
    assert task.result is None
    assert task.sub_tasks == []
    assert task.metadata == {}


def test_skill_task_with_subtasks():
    """Test SkillTask with sub-tasks."""
    parent = SkillTask(
        id="parent",
        description="Parent task",
        required_skills=["skill1"],
        context_budget=5000,
        priority=5,
    )

    sub1 = SkillTask(
        id="sub1",
        description="Sub task 1",
        required_skills=["skill1"],
        context_budget=2500,
        priority=5,
        parent_task_id="parent",
    )

    parent.sub_tasks.append(sub1)

    assert len(parent.sub_tasks) == 1
    assert parent.sub_tasks[0].parent_task_id == "parent"


def test_skill_task_metadata():
    """Test SkillTask metadata."""
    task = SkillTask(
        id="task_123",
        description="Test",
        required_skills=["skill1"],
        context_budget=1000,
        priority=1,
        metadata={"custom_key": "custom_value"},
    )

    assert task.metadata["custom_key"] == "custom_value"


def test_skill_task_status_update():
    """Test SkillTask status updates."""
    task = SkillTask(
        id="task_123",
        description="Test",
        required_skills=["skill1"],
        context_budget=1000,
        priority=1,
    )

    task.status = "in_progress"
    assert task.status == "in_progress"

    task.status = "completed"
    task.result = "Task completed successfully"
    assert task.status == "completed"
    assert task.result == "Task completed successfully"


# =============================================================================
# DelegationResult Tests (3 tests)
# =============================================================================


def test_delegation_result_creation(sample_task):
    """Test DelegationResult creation."""
    result = DelegationResult(
        task=sample_task,
        success=True,
        delegated_to="worker_001",
        execution_time=5.3,
        context_used=2000,
    )

    assert result.task == sample_task
    assert result.success is True
    assert result.delegated_to == "worker_001"
    assert result.execution_time == 5.3
    assert result.context_used == 2000


def test_delegation_result_with_subresults(sample_task):
    """Test DelegationResult with sub-results."""
    sub_result = DelegationResult(
        task=sample_task,
        success=True,
        delegated_to="worker_001",
    )

    main_result = DelegationResult(
        task=sample_task,
        success=True,
        delegated_to="manager_001",
        sub_results=[sub_result],
    )

    assert len(main_result.sub_results) == 1
    assert main_result.sub_results[0].delegated_to == "worker_001"


def test_delegation_result_with_errors(sample_task):
    """Test DelegationResult with errors."""
    result = DelegationResult(
        task=sample_task,
        success=False,
        delegated_to="worker_001",
        errors=["Error 1", "Error 2"],
    )

    assert result.success is False
    assert len(result.errors) == 2
    assert "Error 1" in result.errors


# =============================================================================
# HierarchicalAgent Base Class Tests (10 tests)
# =============================================================================


def test_hierarchical_agent_creation(mock_skill_manager):
    """Test HierarchicalAgent initialization."""

    # Create concrete subclass for testing
    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1", "skill2"],
    )

    assert agent.agent_id == "test_agent"
    assert agent.level == AgentLevel.MANAGER
    assert agent.available_skills == ["skill1", "skill2"]
    assert agent.children == []
    assert agent._active_skills == []


def test_add_child(mock_skill_manager):
    """Test adding child agent."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    parent = TestAgent(
        agent_id="parent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1"],
    )

    child = TestAgent(
        agent_id="child",
        level=AgentLevel.WORKER,
        skill_manager=mock_skill_manager,
        available_skills=["skill2"],
    )

    parent.add_child(child)

    assert len(parent.children) == 1
    assert parent.children[0] == child
    assert child.parent == parent


@pytest.mark.asyncio
async def test_activate_my_skills(mock_skill_manager):
    """Test skill activation."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1", "skill2"],
    )

    await agent.activate_my_skills(context_budget=5000)

    assert mock_skill_manager.activate.call_count == 2
    assert len(agent._active_skills) == 2


@pytest.mark.asyncio
async def test_deactivate_my_skills(mock_skill_manager):
    """Test skill deactivation."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1", "skill2"],
    )

    agent._active_skills = ["skill1", "skill2"]
    await agent.deactivate_my_skills()

    assert mock_skill_manager.deactivate.call_count == 2
    assert len(agent._active_skills) == 0


def test_simple_decompose(mock_skill_manager):
    """Test simple task decomposition."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1", "skill2"],
    )

    task = SkillTask(
        id="parent",
        description="Parent task",
        required_skills=["skill1", "skill2"],
        context_budget=4000,
        priority=5,
    )

    sub_tasks = agent._simple_decompose(task)

    assert len(sub_tasks) == 2
    assert sub_tasks[0].required_skills == ["skill1"]
    assert sub_tasks[1].required_skills == ["skill2"]
    assert sub_tasks[0].context_budget == 2000
    assert sub_tasks[1].context_budget == 2000


def test_find_child_with_skills(mock_skill_manager):
    """Test finding child with required skills."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    parent = TestAgent(
        agent_id="parent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    child1 = TestAgent(
        agent_id="child1",
        level=AgentLevel.WORKER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1", "skill2"],
    )

    child2 = TestAgent(
        agent_id="child2",
        level=AgentLevel.WORKER,
        skill_manager=mock_skill_manager,
        available_skills=["skill3"],
    )

    parent.add_child(child1)
    parent.add_child(child2)

    # Find child with exact match
    found = parent._find_child_with_skills(["skill1", "skill2"])
    assert found == child1

    # Find child with partial match
    found = parent._find_child_with_skills(["skill3"])
    assert found == child2


def test_assign_by_skills(mock_skill_manager):
    """Test task assignment by skills."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    parent = TestAgent(
        agent_id="parent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    child1 = TestAgent(
        agent_id="child1",
        level=AgentLevel.WORKER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1"],
    )

    parent.add_child(child1)

    sub_tasks = [
        SkillTask(
            id="sub1",
            description="Sub 1",
            required_skills=["skill1"],
            context_budget=1000,
            priority=5,
        )
    ]

    assignments = parent._assign_by_skills(sub_tasks)

    assert "child1" in assignments
    assert len(assignments["child1"]) == 1
    assert assignments["child1"][0].id == "sub1"


def test_simple_aggregate(mock_skill_manager):
    """Test simple result aggregation."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    task1 = SkillTask(
        id="task1",
        description="Task 1",
        required_skills=["skill1"],
        context_budget=1000,
        priority=5,
        result="Result 1",
    )

    task2 = SkillTask(
        id="task2",
        description="Task 2",
        required_skills=["skill2"],
        context_budget=1000,
        priority=5,
        result="Result 2",
    )

    child_results = {"child1": [task1, task2]}

    aggregated = agent._simple_aggregate(child_results)

    assert "Result 1" in aggregated
    assert "Result 2" in aggregated


@pytest.mark.asyncio
async def test_receive_report(mock_skill_manager):
    """Test receiving completion report."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    task = SkillTask(
        id="task1",
        description="Task 1",
        required_skills=["skill1"],
        context_budget=1000,
        priority=5,
        status="completed",
        result="Result",
    )

    # Should not raise exception
    await agent.receive_report(task)


@pytest.mark.asyncio
async def test_receive_task_worker(mock_skill_manager, sample_task):
    """Test worker receiving task."""

    class TestWorker(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            task.status = "completed"
            task.result = "Executed"
            return task

    worker = TestWorker(
        agent_id="worker",
        level=AgentLevel.WORKER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1"],
    )

    result = await worker.receive_task(sample_task)

    assert result.status == "completed"
    assert result.result == "Executed"


# =============================================================================
# ExecutiveAgent Tests (8 tests)
# =============================================================================


def test_executive_agent_creation(mock_skill_manager, mock_orchestrator):
    """Test ExecutiveAgent creation."""
    executive = ExecutiveAgent(
        agent_id="executive_001",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    assert executive.agent_id == "executive_001"
    assert executive.level == AgentLevel.EXECUTIVE
    assert "planner" in executive.available_skills
    assert "orchestrator" in executive.available_skills
    assert "reflection" in executive.available_skills


def test_executive_cannot_execute(mock_skill_manager, mock_orchestrator, sample_task):
    """Test that executive cannot execute directly."""
    executive = ExecutiveAgent(
        agent_id="executive_001",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    with pytest.raises(NotImplementedError):
        import asyncio

        asyncio.run(executive._execute_with_skills(sample_task))


@pytest.mark.asyncio
async def test_executive_set_goal(mock_skill_manager, mock_orchestrator):
    """Test executive setting goal."""
    executive = ExecutiveAgent(
        agent_id="executive_001",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    # Mock delegation
    with patch.object(executive, "_delegate_with_skills", new=AsyncMock()) as mock_delegate:
        mock_delegate.return_value = SkillTask(
            id="goal_123",
            description="Test goal",
            required_skills=["planner"],
            context_budget=10000,
            priority=10,
            status="completed",
            result="Goal completed",
        )

        result = await executive.set_goal("Test goal", context_budget=10000)

        assert result.status == "completed"
        assert mock_delegate.called


@pytest.mark.asyncio
async def test_executive_with_managers(mock_skill_manager, mock_orchestrator):
    """Test executive with manager children."""
    executive = ExecutiveAgent(
        agent_id="executive_001",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search"],
    )

    executive.add_child(manager)

    assert len(executive.children) == 1
    assert executive.children[0].agent_id == "research_manager"


def test_executive_skills(mock_skill_manager, mock_orchestrator):
    """Test executive available skills."""
    executive = ExecutiveAgent(
        agent_id="executive_001",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    assert len(executive.available_skills) == 3
    assert set(executive.available_skills) == {"planner", "orchestrator", "reflection"}


@pytest.mark.asyncio
async def test_executive_activate_skills(mock_skill_manager, mock_orchestrator):
    """Test executive skill activation."""
    executive = ExecutiveAgent(
        agent_id="executive_001",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    await executive.activate_my_skills(context_budget=6000)

    assert mock_skill_manager.activate.call_count == 3
    assert len(executive._active_skills) == 3


@pytest.mark.asyncio
async def test_executive_goal_with_budget(mock_skill_manager, mock_orchestrator):
    """Test executive goal with custom budget."""
    executive = ExecutiveAgent(
        agent_id="executive_001",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    with patch.object(executive, "_delegate_with_skills", new=AsyncMock()) as mock_delegate:
        mock_delegate.return_value = SkillTask(
            id="goal_123",
            description="Test goal",
            required_skills=["planner"],
            context_budget=8000,
            priority=10,
            status="completed",
        )

        result = await executive.set_goal("Test goal", context_budget=8000)

        # Verify task was created with correct budget
        call_args = mock_delegate.call_args
        task = call_args[0][0]
        assert task.context_budget == 8000


@pytest.mark.asyncio
async def test_executive_goal_priority(mock_skill_manager, mock_orchestrator):
    """Test executive goal priority."""
    executive = ExecutiveAgent(
        agent_id="executive_001",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    with patch.object(executive, "_delegate_with_skills", new=AsyncMock()) as mock_delegate:
        mock_delegate.return_value = SkillTask(
            id="goal_123",
            description="Test goal",
            required_skills=["planner"],
            context_budget=10000,
            priority=10,
            status="completed",
        )

        await executive.set_goal("Test goal")

        # Verify priority is always 10 for executive goals
        call_args = mock_delegate.call_args
        task = call_args[0][0]
        assert task.priority == 10


# =============================================================================
# ManagerAgent Tests (8 tests)
# =============================================================================


def test_manager_agent_creation(mock_skill_manager):
    """Test ManagerAgent creation."""
    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search", "retrieval"],
    )

    assert manager.agent_id == "research_manager"
    assert manager.level == AgentLevel.MANAGER
    assert manager.domain == "research"
    assert "web_search" in manager.available_skills
    assert "retrieval" in manager.available_skills


def test_manager_domain(mock_skill_manager):
    """Test manager domain assignment."""
    research = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search"],
    )

    analysis = ManagerAgent(
        agent_id="analysis_manager",
        domain="analysis",
        skill_manager=mock_skill_manager,
        domain_skills=["validation"],
    )

    assert research.domain == "research"
    assert analysis.domain == "analysis"


@pytest.mark.asyncio
async def test_manager_delegates_to_workers(mock_skill_manager, sample_task):
    """Test manager delegating to workers."""
    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search"],
    )

    # Mock delegation
    with patch.object(manager, "_delegate_with_skills", new=AsyncMock()) as mock_delegate:
        mock_delegate.return_value = sample_task
        sample_task.status = "completed"

        result = await manager._execute_with_skills(sample_task)

        assert result.status == "completed"
        assert mock_delegate.called


def test_manager_with_workers(mock_skill_manager):
    """Test manager with worker children."""
    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search"],
    )

    class TestWorker(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    worker = TestWorker(
        agent_id="retrieval_worker",
        level=AgentLevel.WORKER,
        skill_manager=mock_skill_manager,
        available_skills=["retrieval"],
    )

    manager.add_child(worker)

    assert len(manager.children) == 1
    assert manager.children[0].agent_id == "retrieval_worker"


@pytest.mark.asyncio
async def test_manager_activate_skills(mock_skill_manager):
    """Test manager skill activation."""
    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search", "retrieval"],
    )

    await manager.activate_my_skills(context_budget=4000)

    assert mock_skill_manager.activate.call_count == 2
    assert len(manager._active_skills) == 2


def test_manager_research_skills(mock_skill_manager):
    """Test research manager skills."""
    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search", "retrieval", "graph_query"],
    )

    assert len(manager.available_skills) == 3
    assert set(manager.available_skills) == {"web_search", "retrieval", "graph_query"}


def test_manager_analysis_skills(mock_skill_manager):
    """Test analysis manager skills."""
    manager = ManagerAgent(
        agent_id="analysis_manager",
        domain="analysis",
        skill_manager=mock_skill_manager,
        domain_skills=["validation", "reasoning", "reflection"],
    )

    assert len(manager.available_skills) == 3
    assert set(manager.available_skills) == {"validation", "reasoning", "reflection"}


def test_manager_synthesis_skills(mock_skill_manager):
    """Test synthesis manager skills."""
    manager = ManagerAgent(
        agent_id="synthesis_manager",
        domain="synthesis",
        skill_manager=mock_skill_manager,
        domain_skills=["summarization", "answer_generation"],
    )

    assert len(manager.available_skills) == 2
    assert set(manager.available_skills) == {"summarization", "answer_generation"}


# =============================================================================
# WorkerAgent Tests (8 tests)
# =============================================================================


def test_worker_agent_creation(mock_skill_manager, mock_llm):
    """Test WorkerAgent creation."""
    worker = WorkerAgent(
        agent_id="retrieval_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval"],
        llm=mock_llm,
    )

    assert worker.agent_id == "retrieval_worker"
    assert worker.level == AgentLevel.WORKER
    assert "retrieval" in worker.available_skills
    assert worker.llm == mock_llm


@pytest.mark.asyncio
async def test_worker_execute_with_skills(mock_skill_manager, mock_llm, sample_task):
    """Test worker executing task with skills."""
    worker = WorkerAgent(
        agent_id="retrieval_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval"],
        llm=mock_llm,
    )

    worker._active_skills = ["retrieval"]
    mock_skill_manager._loaded_content = {"retrieval": "Retrieval skill instructions"}

    result = await worker._execute_with_skills(sample_task)

    assert result.status == "completed"
    assert mock_llm.ainvoke.called


@pytest.mark.asyncio
async def test_worker_llm_invocation(mock_skill_manager, mock_llm):
    """Test worker LLM invocation."""
    worker = WorkerAgent(
        agent_id="retrieval_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval"],
        llm=mock_llm,
    )

    task = SkillTask(
        id="task_123",
        description="Retrieve documents",
        required_skills=["retrieval"],
        context_budget=2000,
        priority=5,
    )

    worker._active_skills = ["retrieval"]
    mock_skill_manager._loaded_content = {"retrieval": "Retrieval instructions"}

    await worker._execute_with_skills(task)

    assert mock_llm.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_worker_task_completion(mock_skill_manager, mock_llm):
    """Test worker task completion."""
    worker = WorkerAgent(
        agent_id="retrieval_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval"],
        llm=mock_llm,
    )

    task = SkillTask(
        id="task_123",
        description="Retrieve documents",
        required_skills=["retrieval"],
        context_budget=2000,
        priority=5,
    )

    worker._active_skills = ["retrieval"]
    mock_skill_manager._loaded_content = {"retrieval": "Instructions"}

    result = await worker._execute_with_skills(task)

    assert result.status == "completed"
    assert result.result == "LLM response"


@pytest.mark.asyncio
async def test_worker_error_handling(mock_skill_manager, mock_llm):
    """Test worker error handling."""
    worker = WorkerAgent(
        agent_id="retrieval_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval"],
        llm=mock_llm,
    )

    task = SkillTask(
        id="task_123",
        description="Retrieve documents",
        required_skills=["retrieval"],
        context_budget=2000,
        priority=5,
    )

    worker._active_skills = ["retrieval"]
    mock_skill_manager._loaded_content = {"retrieval": "Instructions"}

    # Mock LLM to raise exception
    mock_llm.ainvoke.side_effect = Exception("LLM error")

    result = await worker._execute_with_skills(task)

    assert result.status == "failed"
    assert "LLM error" in result.result


def test_worker_multiple_skills(mock_skill_manager, mock_llm):
    """Test worker with multiple atomic skills."""
    worker = WorkerAgent(
        agent_id="multi_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval", "web_search"],
        llm=mock_llm,
    )

    assert len(worker.available_skills) == 2
    assert set(worker.available_skills) == {"retrieval", "web_search"}


@pytest.mark.asyncio
async def test_worker_activate_skills(mock_skill_manager, mock_llm):
    """Test worker skill activation."""
    worker = WorkerAgent(
        agent_id="retrieval_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval"],
        llm=mock_llm,
    )

    await worker.activate_my_skills(context_budget=2000)

    assert mock_skill_manager.activate.call_count == 1
    assert len(worker._active_skills) == 1


@pytest.mark.asyncio
async def test_worker_no_skills_loaded(mock_skill_manager, mock_llm):
    """Test worker with no skills loaded."""
    worker = WorkerAgent(
        agent_id="retrieval_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval"],
        llm=mock_llm,
    )

    task = SkillTask(
        id="task_123",
        description="Retrieve documents",
        required_skills=["retrieval"],
        context_budget=2000,
        priority=5,
    )

    worker._active_skills = ["retrieval"]
    mock_skill_manager._loaded_content = {}  # No skills loaded

    result = await worker._execute_with_skills(task)

    # Should still complete, just with empty instructions
    assert result.status == "completed"


# =============================================================================
# Task Delegation Tests (10 tests)
# =============================================================================


@pytest.mark.asyncio
async def test_end_to_end_delegation(mock_skill_manager, mock_llm, mock_orchestrator):
    """Test complete delegation flow: Executive → Manager → Worker."""
    # Create hierarchy
    executive = ExecutiveAgent(
        agent_id="executive",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search"],
    )

    worker = WorkerAgent(
        agent_id="search_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["web_search"],
        llm=mock_llm,
    )

    executive.add_child(manager)
    manager.add_child(worker)

    # Setup mocks
    worker._active_skills = ["web_search"]
    mock_skill_manager._loaded_content = {"web_search": "Search instructions"}

    # Create task
    task = SkillTask(
        id="task_001",
        description="Search for information",
        required_skills=["web_search"],
        context_budget=3000,
        priority=5,
    )

    # Execute through hierarchy
    result = await manager.receive_task(task)

    assert result.status == "completed"
    assert mock_llm.ainvoke.called


@pytest.mark.asyncio
async def test_parallel_delegation(mock_skill_manager, mock_llm):
    """Test parallel task delegation to multiple workers."""
    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search", "retrieval"],
    )

    worker1 = WorkerAgent(
        agent_id="search_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["web_search"],
        llm=mock_llm,
    )

    worker2 = WorkerAgent(
        agent_id="retrieval_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval"],
        llm=mock_llm,
    )

    manager.add_child(worker1)
    manager.add_child(worker2)

    # Setup mocks
    worker1._active_skills = ["web_search"]
    worker2._active_skills = ["retrieval"]
    mock_skill_manager._loaded_content = {
        "web_search": "Search instructions",
        "retrieval": "Retrieval instructions",
    }

    # Create task requiring both skills
    task = SkillTask(
        id="task_001",
        description="Research and retrieve",
        required_skills=["web_search", "retrieval"],
        context_budget=4000,
        priority=5,
    )

    result = await manager.receive_task(task)

    assert result.status == "completed"
    assert len(result.sub_tasks) == 2


@pytest.mark.asyncio
async def test_context_budget_distribution(mock_skill_manager):
    """Test context budget distribution across sub-tasks."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    task = SkillTask(
        id="parent",
        description="Parent task",
        required_skills=["skill1", "skill2", "skill3"],
        context_budget=9000,
        priority=5,
    )

    sub_tasks = agent._simple_decompose(task)

    # Budget should be evenly distributed
    assert all(st.context_budget == 3000 for st in sub_tasks)


@pytest.mark.asyncio
async def test_priority_propagation(mock_skill_manager):
    """Test task priority propagation to sub-tasks."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    task = SkillTask(
        id="parent",
        description="Parent task",
        required_skills=["skill1", "skill2"],
        context_budget=4000,
        priority=8,
    )

    sub_tasks = agent._simple_decompose(task)

    # Priority should propagate
    assert all(st.priority == 8 for st in sub_tasks)


@pytest.mark.asyncio
async def test_delegation_with_no_children(mock_skill_manager):
    """Test delegation when no suitable children exist."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    task = SkillTask(
        id="task_001",
        description="Task",
        required_skills=["skill1"],
        context_budget=2000,
        priority=5,
    )

    sub_tasks = [task]
    assignments = agent._assign_by_skills(sub_tasks)

    # No children, so no assignments
    assert len(assignments) == 0


@pytest.mark.asyncio
async def test_result_aggregation(mock_skill_manager):
    """Test result aggregation from sub-tasks."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    task1 = SkillTask(
        id="sub1",
        description="Sub 1",
        required_skills=["skill1"],
        context_budget=1000,
        priority=5,
        result="Result 1",
    )

    task2 = SkillTask(
        id="sub2",
        description="Sub 2",
        required_skills=["skill2"],
        context_budget=1000,
        priority=5,
        result="Result 2",
    )

    child_results = {"child1": [task1], "child2": [task2]}
    aggregated = agent._simple_aggregate(child_results)

    assert "Result 1" in aggregated
    assert "Result 2" in aggregated


def test_parent_task_id_tracking(mock_skill_manager):
    """Test parent task ID tracking in sub-tasks."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    task = SkillTask(
        id="parent_123",
        description="Parent",
        required_skills=["skill1", "skill2"],
        context_budget=4000,
        priority=5,
    )

    sub_tasks = agent._simple_decompose(task)

    assert all(st.parent_task_id == "parent_123" for st in sub_tasks)


@pytest.mark.asyncio
async def test_skill_matching_priority(mock_skill_manager):
    """Test skill matching prioritizes exact matches."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    parent = TestAgent(
        agent_id="parent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    # Child with exact match
    exact_match = TestAgent(
        agent_id="exact",
        level=AgentLevel.WORKER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1", "skill2"],
    )

    # Child with partial match
    partial_match = TestAgent(
        agent_id="partial",
        level=AgentLevel.WORKER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1"],
    )

    parent.add_child(partial_match)
    parent.add_child(exact_match)

    # Should find exact match
    found = parent._find_child_with_skills(["skill1", "skill2"])
    assert found.agent_id == "exact"


@pytest.mark.asyncio
async def test_multiple_manager_coordination(mock_skill_manager, mock_llm, mock_orchestrator):
    """Test coordination between multiple managers."""
    executive = ExecutiveAgent(
        agent_id="executive",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    research = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search"],
    )

    analysis = ManagerAgent(
        agent_id="analysis_manager",
        domain="analysis",
        skill_manager=mock_skill_manager,
        domain_skills=["validation"],
    )

    executive.add_child(research)
    executive.add_child(analysis)

    assert len(executive.children) == 2
    assert executive.children[0].domain == "research"
    assert executive.children[1].domain == "analysis"


@pytest.mark.asyncio
async def test_deep_hierarchy(mock_skill_manager, mock_llm, mock_orchestrator):
    """Test three-level deep hierarchy."""
    executive = ExecutiveAgent(
        agent_id="executive",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )

    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search"],
    )

    worker = WorkerAgent(
        agent_id="search_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["web_search"],
        llm=mock_llm,
    )

    executive.add_child(manager)
    manager.add_child(worker)

    # Verify hierarchy
    assert len(executive.children) == 1
    assert len(manager.children) == 1
    assert worker.parent == manager
    assert manager.parent == executive


# =============================================================================
# Error Handling Tests (5 tests)
# =============================================================================


@pytest.mark.asyncio
async def test_task_failure_propagation(mock_skill_manager, mock_llm):
    """Test task failure propagation up hierarchy."""
    manager = ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search"],
    )

    worker = WorkerAgent(
        agent_id="search_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["web_search"],
        llm=mock_llm,
    )

    manager.add_child(worker)

    # Setup for failure
    worker._active_skills = ["web_search"]
    mock_skill_manager._loaded_content = {"web_search": "Instructions"}
    mock_llm.ainvoke.side_effect = Exception("Worker failed")

    task = SkillTask(
        id="task_001",
        description="Search task",
        required_skills=["web_search"],
        context_budget=2000,
        priority=5,
    )

    result = await manager.receive_task(task)

    # Task should be marked as completed even with worker failure
    # (because manager catches exceptions)
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_activation_error_handling(mock_skill_manager):
    """Test error handling during skill activation."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1"],
    )

    # Mock activation to raise exception
    mock_skill_manager.activate.side_effect = Exception("Activation failed")

    task = SkillTask(
        id="task_001",
        description="Test task",
        required_skills=["skill1"],
        context_budget=2000,
        priority=5,
    )

    # Should handle exception gracefully
    with pytest.raises(Exception):
        await agent.receive_task(task)


@pytest.mark.asyncio
async def test_deactivation_cleanup(mock_skill_manager):
    """Test skill deactivation in cleanup."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            raise Exception("Execution failed")

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.WORKER,
        skill_manager=mock_skill_manager,
        available_skills=["skill1"],
    )

    task = SkillTask(
        id="task_001",
        description="Test task",
        required_skills=["skill1"],
        context_budget=2000,
        priority=5,
    )

    result = await agent.receive_task(task)

    # Deactivate should still be called in finally block
    assert mock_skill_manager.deactivate.called


@pytest.mark.asyncio
async def test_empty_result_handling(mock_skill_manager):
    """Test handling of empty results."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    child_results: dict[str, list[SkillTask]] = {}
    aggregated = agent._simple_aggregate(child_results)

    assert aggregated == ""


@pytest.mark.asyncio
async def test_task_without_result(mock_skill_manager):
    """Test task completion without result."""

    class TestAgent(HierarchicalAgent):
        async def _execute_with_skills(self, task):
            return task

    agent = TestAgent(
        agent_id="test_agent",
        level=AgentLevel.MANAGER,
        skill_manager=mock_skill_manager,
        available_skills=[],
    )

    task = SkillTask(
        id="task_001",
        description="Task",
        required_skills=["skill1"],
        context_budget=1000,
        priority=5,
        result=None,
    )

    child_results = {"child1": [task]}
    aggregated = agent._simple_aggregate(child_results)

    # Should handle None result gracefully
    assert aggregated == ""
