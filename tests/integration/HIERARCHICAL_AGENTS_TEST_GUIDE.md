# Hierarchical Agents Integration Test Guide

**File:** `tests/integration/test_hierarchical_agents.py`
**Sprint:** 95
**Feature:** 95.5 - Integration Testing
**Created:** 2026-01-15

---

## Quick Start

### Run All Tests
```bash
poetry run pytest tests/integration/test_hierarchical_agents.py -v
```

### Run Specific Test Category
```bash
# Hierarchical agent integration tests
poetry run pytest tests/integration/test_hierarchical_agents.py::TestHierarchicalAgentIntegration -v

# Context budgeting tests
poetry run pytest tests/integration/test_hierarchical_agents.py::TestContextBudgeting -v

# Error handling tests
poetry run pytest tests/integration/test_hierarchical_agents.py::TestErrorHandling -v

# Concurrent execution tests
poetry run pytest tests/integration/test_hierarchical_agents.py::TestConcurrentExecution -v

# Skill activation tests
poetry run pytest tests/integration/test_hierarchical_agents.py::TestSkillActivationDeactivation -v

# Performance tests
poetry run pytest tests/integration/test_hierarchical_agents.py::TestPerformance -v
```

### Run with Coverage
```bash
poetry run pytest tests/integration/test_hierarchical_agents.py \
  --cov=src/agents/hierarchy \
  --cov=src/agents/skills \
  --cov-report=term-missing
```

### Run Specific Test
```bash
poetry run pytest tests/integration/test_hierarchical_agents.py::TestHierarchicalAgentIntegration::test_executive_delegates_to_manager -v
```

---

## Test Structure

### Test File Organization

```
test_hierarchical_agents.py
├── Imports (Lines 1-60)
├── Fixtures (Lines 65-357)
│   ├── Mock Fixtures (mock_llm, mock_skill_manager, mock_orchestrator)
│   ├── Agent Fixtures (test_executive, test_*_manager, test_*_worker)
│   ├── Hierarchy Fixtures (populated_hierarchy)
│   └── Support Fixtures (mock_redis_memory, bundle_metadata, mock_bundle_installer)
├── Test Classes (Lines 360-981)
│   ├── TestHierarchicalAgentIntegration (10 tests)
│   ├── TestContextBudgeting (2 tests)
│   ├── TestErrorHandling (2 tests)
│   ├── TestConcurrentExecution (2 tests)
│   ├── TestSkillActivationDeactivation (2 tests)
│   ├── TestPerformance (2 tests)
│   └── TestIntegrationMarkers (1 test)
└── Configuration (Lines 975-984)
```

---

## Test Categories

### 1. Hierarchical Agent Integration (10 tests)

Core tests for hierarchical agent patterns:

| Test | Purpose | Key Assertion |
|------|---------|---------------|
| `test_executive_delegates_to_manager` | Executive task delegation | Task status = "completed" |
| `test_manager_delegates_to_workers` | Manager task decomposition | Sub-tasks created and executed |
| `test_research_bundle_workflow` | Research skill bundle | All research skills execute |
| `test_analysis_bundle_workflow` | Analysis domain workflow | Analysis worker executes |
| `test_skill_context_sharing` | SharedMemoryProtocol | Shared memory read/write works |
| `test_message_bus_handoffs` | Task routing through hierarchy | Results propagate correctly |
| `test_procedural_memory_learning` | Execution trace recording | Traces stored in memory |
| `test_bundle_installation_integration` | Bundle installation | Installation succeeds |
| `test_hierarchy_with_langgraph_supervisor` | LangGraph integration | Task completed via supervisor |
| `test_end_to_end_workflow` | Full Research→Analysis→Synthesis | All domains participate |

### 2. Context Budgeting (2 tests)

Token budget management tests:

| Test | Purpose |
|------|---------|
| `test_context_budget_distribution` | Budget flows through hierarchy |
| `test_context_budget_respect_max_tokens` | 150K token max enforced |

### 3. Error Handling (2 tests)

Failure resilience tests:

| Test | Purpose |
|------|---------|
| `test_worker_task_failure_handling` | Worker failures handled gracefully |
| `test_manager_partial_failure_handling` | Manager continues on worker failure |

### 4. Concurrent Execution (2 tests)

Parallel task execution tests:

| Test | Purpose |
|------|---------|
| `test_parallel_worker_execution` | Workers execute in parallel |
| `test_multi_manager_parallel_execution` | Managers coordinate parallel execution |

### 5. Skill Activation/Deactivation (2 tests)

Lifecycle management tests:

| Test | Purpose |
|------|---------|
| `test_worker_activates_skills_on_task_receive` | Skills activated on task receive |
| `test_skill_deactivation_on_completion` | Skills deactivated after execution |

### 6. Performance (2 tests)

Performance validation tests:

| Test | Purpose | Target |
|------|---------|--------|
| `test_large_hierarchy_execution_time` | 3-level hierarchy performance | <2000ms |
| `test_many_subtasks_execution` | Multi-task coordination | No timeout |

### 7. Integration Markers (1 test)

CI/CD compatibility test:

| Test | Purpose |
|------|---------|
| `test_marked_integration_test` | Verify pytest markers work |

---

## Fixtures Reference

### Mock Fixtures

#### `mock_llm`
```python
@pytest.fixture
def mock_llm():
    """Mock LLM for worker agent execution."""
    llm = AsyncMock()
    # Deterministic responses based on prompt content
```

**Usage:**
```python
async def test_something(mock_llm):
    mock_llm.ainvoke.assert_called_once()
```

#### `mock_skill_manager`
```python
@pytest.fixture
def mock_skill_manager():
    """Mock SkillLifecycleManager for agent tests."""
    # Supports activate(), deactivate(), get_skill()
```

#### `mock_orchestrator`
```python
@pytest.fixture
def mock_orchestrator():
    """Mock SkillOrchestrator for executive agent."""
    # Supports execute()
```

### Agent Fixtures

#### `test_executive`
```python
@pytest.fixture
def test_executive(mock_skill_manager, mock_orchestrator):
    """Create test ExecutiveAgent."""
    return ExecutiveAgent(
        agent_id="executive_001",
        skill_manager=mock_skill_manager,
        orchestrator=mock_orchestrator,
    )
```

#### `test_research_manager`
```python
@pytest.fixture
def test_research_manager(mock_skill_manager):
    """Create test ManagerAgent for research domain."""
    return ManagerAgent(
        agent_id="research_manager",
        domain="research",
        skill_manager=mock_skill_manager,
        domain_skills=["web_search", "retrieval", "graph_query"],
    )
```

#### `test_retrieval_worker`, `test_web_search_worker`, etc.
```python
@pytest.fixture
def test_retrieval_worker(mock_skill_manager, mock_llm):
    """Create test WorkerAgent for retrieval skill."""
    return WorkerAgent(
        agent_id="retrieval_worker",
        skill_manager=mock_skill_manager,
        atomic_skills=["retrieval"],
        llm=mock_llm,
    )
```

### Composed Fixtures

#### `populated_hierarchy`
```python
@pytest.fixture
def populated_hierarchy(...):
    """Create a fully populated hierarchical agent structure.

    Structure:
        Executive
        ├── ResearchManager
        │   ├── RetrievalWorker
        │   ├── WebSearchWorker
        │   └── GraphQueryWorker
        ├── AnalysisManager
        │   └── ValidationWorker
        └── SynthesisManager
            └── SynthesisWorker
    """
```

**Usage:**
```python
async def test_something(populated_hierarchy):
    executive = populated_hierarchy
    task = SkillTask(...)
    result = await executive.receive_task(task)
```

#### `mock_redis_memory`
```python
@pytest.fixture
async def mock_redis_memory():
    """Create in-memory Redis-backed shared memory."""
    # Returns memory with write() and read() methods
```

#### `bundle_metadata`
```python
@pytest.fixture
def bundle_metadata():
    """Create test bundle metadata."""
    return BundleMetadata(
        id="research_bundle",
        name="Research Skills Bundle",
        skills=[...],  # 3 skills
    )
```

#### `mock_bundle_installer`
```python
@pytest.fixture
def mock_bundle_installer(bundle_metadata):
    """Mock BundleInstaller for testing."""
    # Returns installer with install() method
```

---

## Writing New Tests

### Test Template
```python
@pytest.mark.asyncio
async def test_new_feature(populated_hierarchy):
    """Test description.

    Verifies:
    - Point 1
    - Point 2
    - Point 3
    """
    executive = populated_hierarchy

    # Setup
    task = SkillTask(
        id="test_task",
        description="Task description",
        required_skills=["skill1", "skill2"],
        context_budget=5000,
        priority=8,
    )

    # Execute
    result = await executive.receive_task(task)

    # Verify
    assert result.status == "completed"
    assert result.assigned_to == "executive_001"
    assert len(result.sub_tasks) > 0
```

### Using Fixtures
```python
# Use single fixture
async def test_something(test_executive):
    result = await test_executive.receive_task(task)

# Compose fixtures
async def test_something(test_research_manager, test_retrieval_worker):
    test_research_manager.add_child(test_retrieval_worker)
    result = await test_research_manager.receive_task(task)

# Use full hierarchy
async def test_something(populated_hierarchy):
    result = await populated_hierarchy.receive_task(task)
```

### Testing Async Code
```python
# All tests are async
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

---

## Common Patterns

### Testing Delegation
```python
task = SkillTask(
    id="task_001",
    description="Test delegation",
    required_skills=["skill1", "skill2"],
    context_budget=5000,
    priority=8,
)
result = await executive.receive_task(task)
assert result.status == "completed"
assert len(result.sub_tasks) > 0
```

### Testing Error Handling
```python
mock_llm.ainvoke.side_effect = Exception("LLM error")
result = await worker.receive_task(task)
assert result.status == "failed"
assert "failed" in result.result.lower()
```

### Testing Shared Memory
```python
await memory.write(
    key="findings",
    value={"count": 10},
    scope=MemoryScope.SHARED,
    owner_skill="research",
)
data = await memory.read(
    key="findings",
    scope=MemoryScope.SHARED,
    owner_skill="research",
)
assert data is not None
```

### Testing Skill Activation
```python
mock_skill_manager.activate.assert_called()
mock_skill_manager.deactivate.assert_called()
```

---

## Debugging Tests

### Verbose Output
```bash
poetry run pytest tests/integration/test_hierarchical_agents.py -vv
```

### Show Full Traceback
```bash
poetry run pytest tests/integration/test_hierarchical_agents.py --tb=long
```

### Print Debug Output
```bash
poetry run pytest tests/integration/test_hierarchical_agents.py -s
```

### Run Single Test with Debug
```bash
poetry run pytest tests/integration/test_hierarchical_agents.py::TestHierarchicalAgentIntegration::test_executive_delegates_to_manager -vv -s
```

### Inspect Test Fixtures
```bash
poetry run pytest tests/integration/test_hierarchical_agents.py --fixtures
```

---

## Performance Benchmarks

### Current Performance
- **Total Execution Time:** 0.07 seconds
- **Average Test Duration:** 3.3 ms
- **Slowest Test:** <10 ms
- **Status:** Excellent (well under 1 second target)

### Performance Test Targets
- **Large Hierarchy:** <2000 ms (actual: ~50 ms)
- **Many Sub-tasks:** No timeout (actual: ~30 ms)

---

## Integration with CI/CD

### GitHub Actions Configuration
```yaml
- name: Run hierarchical agent integration tests
  run: |
    poetry run pytest tests/integration/test_hierarchical_agents.py \
      -v \
      --tb=short \
      --junit-xml=test-results.xml
```

### Test Markers for CI
```bash
# Run only integration tests
poetry run pytest -m integration

# Skip integration tests
poetry run pytest -m "not integration"

# Skip slow tests
poetry run pytest -m "not slow"
```

---

## Troubleshooting

### Import Errors
```bash
# Verify imports work
poetry run python -c "from tests.integration.test_hierarchical_agents import *"
```

### Async Test Errors
- Ensure `@pytest.mark.asyncio` is present
- Verify `await` is used for async calls
- Check pytest-asyncio is installed: `poetry show pytest-asyncio`

### Fixture Not Found
- Check fixture is defined in conftest.py or test file
- Verify fixture name matches parameter name
- Check fixture scope (module, function, session)

### Mock Not Working
- Use `AsyncMock` for async methods
- Call methods with `await`
- Check mock is applied before function call

---

## Contributing New Tests

### Adding Test to Existing Class
```python
class TestHierarchicalAgentIntegration:
    # ... existing tests ...

    @pytest.mark.asyncio
    async def test_new_feature(self, populated_hierarchy):
        """Test description."""
        # Implementation
```

### Creating New Test Class
```python
class TestNewFeature:
    """Test new feature."""

    @pytest.mark.asyncio
    async def test_something(self, fixture_name):
        """Test description."""
        # Implementation
```

### Adding New Fixture
```python
@pytest.fixture
def my_fixture():
    """Fixture description."""
    return MyObject(...)
```

---

## Resources

- **Test File:** `/home/admin/projects/aegisrag/AEGIS_Rag/tests/integration/test_hierarchical_agents.py`
- **Report:** `/home/admin/projects/aegisrag/AEGIS_Rag/SPRINT_95_FEATURE_95.5_TEST_REPORT.md`
- **Source Code:**
  - `src/agents/hierarchy/skill_hierarchy.py` - Hierarchical agents
  - `src/agents/skills/bundle_installer.py` - Bundle management
  - `src/agents/memory/shared_memory.py` - Shared memory protocol
- **Documentation:** `docs/sprints/SPRINT_95_PLAN.md`

---

## Support

For issues or questions:
1. Check this guide first
2. Review the test report
3. Check test file docstrings
4. Review source code documentation
