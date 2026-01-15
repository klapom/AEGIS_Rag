"""Unit tests for Agent Monitoring APIs (Part 1: agents.py).

Sprint 99 Feature 99.2: Agent Monitoring APIs

Tests:
    - GET /api/v1/agents/blackboard: Blackboard state retrieval
    - GET /api/v1/agents/hierarchy: Agent hierarchy tree
    - GET /api/v1/agents/:id/details: Agent details and tasks
    - WebSocket /api/v1/agents/messages: Message streaming (integration test)

Note: WebSocket testing requires integration test environment.
"""

import json
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.agents import (
    AgentDetails,
    AgentHierarchyResponse,
    AgentLevel,
    AgentPerformance,
    AgentStatus,
    BlackboardEntry,
    BlackboardNamespace,
    BlackboardResponse,
    HierarchyEdge,
    HierarchyNode,
)
from src.agents.memory.shared_memory import MemoryScope
from src.agents.orchestrator.skill_orchestrator import OrchestratorLevel


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


# =============================================================================
# GET /api/v1/agents/blackboard
# =============================================================================


@pytest.mark.asyncio
async def test_get_blackboard_success(client):
    """Test successful blackboard state retrieval."""
    # Mock SharedMemoryProtocol
    mock_memory = MagicMock()
    mock_memory.list_keys = AsyncMock(return_value=["task_context", "research_findings"])
    mock_memory._redis = MagicMock()
    mock_memory._redis.client = AsyncMock()

    # Mock Redis scan_iter
    async def mock_scan_iter(*args, **kwargs):
        yield "shared_memory:shared:coordinator:task_context"
        yield "shared_memory:private:research:research_findings"

    mock_memory._redis.client.return_value.scan_iter = mock_scan_iter

    # Mock metadata and read
    mock_memory.get_metadata = AsyncMock(
        side_effect=[
            {
                "key": "task_context",
                "scope": "shared",
                "owner_skill": "coordinator",
                "timestamp": "2026-01-15T10:30:00Z",
                "ttl_seconds_remaining": 2400,
            },
            {
                "key": "research_findings",
                "scope": "private",
                "owner_skill": "research",
                "timestamp": "2026-01-15T10:35:00Z",
                "ttl_seconds_remaining": 1800,
            },
        ]
    )

    mock_memory.read = AsyncMock(
        side_effect=[
            {"query": "What is RAG?", "intent": "search"},
            {"papers": 10, "citations": 45},
        ]
    )

    mock_memory.aclose = AsyncMock()

    with patch("src.api.v1.agents.SharedMemoryProtocol", return_value=mock_memory):
        response = client.get("/api/v1/agents/blackboard")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "namespaces" in data
    assert "total_entries" in data
    assert data["total_entries"] == 2


@pytest.mark.asyncio
async def test_get_blackboard_empty(client):
    """Test blackboard retrieval with no entries."""
    mock_memory = MagicMock()
    mock_memory.list_keys = AsyncMock(return_value=[])
    mock_memory.aclose = AsyncMock()

    with patch("src.api.v1.agents.SharedMemoryProtocol", return_value=mock_memory):
        response = client.get("/api/v1/agents/blackboard")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_entries"] == 0
    assert len(data["namespaces"]) == 0


@pytest.mark.asyncio
async def test_get_blackboard_error(client):
    """Test blackboard retrieval with service error."""
    mock_memory = MagicMock()
    mock_memory.list_keys = AsyncMock(side_effect=Exception("Redis connection failed"))

    with patch("src.api.v1.agents.SharedMemoryProtocol", return_value=mock_memory):
        response = client.get("/api/v1/agents/blackboard")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Failed to retrieve blackboard state" in response.json()["detail"]


# =============================================================================
# GET /api/v1/agents/hierarchy
# =============================================================================


def test_get_agent_hierarchy_success(client):
    """Test successful agent hierarchy retrieval."""
    # Mock SkillOrchestrator
    mock_supervisor = MagicMock()
    mock_supervisor.name = "executive"
    mock_supervisor.level = MagicMock(value="executive")
    mock_supervisor.capabilities = ["planning", "coordination"]
    mock_supervisor.child_supervisors = ["research_manager", "analysis_manager"]
    mock_supervisor.child_skills = []

    mock_orchestrator = MagicMock()
    mock_orchestrator._supervisors = {"executive": mock_supervisor}

    with patch("src.api.v1.agents.SkillOrchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/agents/hierarchy")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 1
    assert len(data["edges"]) == 2  # 2 child supervisors


def test_get_agent_hierarchy_complex(client):
    """Test hierarchy with multiple levels."""
    # Mock supervisors
    executive = MagicMock()
    executive.name = "executive"
    executive.level = MagicMock(value="executive")
    executive.capabilities = ["planning"]
    executive.child_supervisors = ["research_manager"]
    executive.child_skills = []

    manager = MagicMock()
    manager.name = "research_manager"
    manager.level = MagicMock(value="manager")
    manager.capabilities = ["research"]
    manager.child_supervisors = []
    manager.child_skills = ["web_search", "retrieval"]

    mock_orchestrator = MagicMock()
    mock_orchestrator._supervisors = {"executive": executive, "research_manager": manager}

    with patch("src.api.v1.agents.SkillOrchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/agents/hierarchy")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert len(data["nodes"]) == 2
    # 1 supervisor edge + 2 skill edges
    assert len(data["edges"]) == 3


def test_get_agent_hierarchy_error(client):
    """Test hierarchy retrieval with error."""
    with patch("src.api.v1.agents.SkillOrchestrator", side_effect=Exception("Init failed")):
        response = client.get("/api/v1/agents/hierarchy")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Failed to retrieve agent hierarchy" in response.json()["detail"]


# =============================================================================
# GET /api/v1/agents/:id/details
# =============================================================================


@pytest.mark.asyncio
async def test_get_agent_details_success(client):
    """Test successful agent details retrieval."""
    # Mock supervisor
    mock_supervisor = MagicMock()
    mock_supervisor.name = "research_manager"
    mock_supervisor.level = MagicMock(value="manager")
    mock_supervisor.capabilities = ["research", "information_gathering"]
    mock_supervisor.child_supervisors = []
    mock_supervisor.child_skills = ["web_search", "retrieval", "graph_query"]

    mock_orchestrator = MagicMock()
    mock_orchestrator._supervisors = {"research_manager": mock_supervisor}
    mock_orchestrator.get_metrics = MagicMock(
        return_value={
            "total_workflows": 150,
            "successful_workflows": 142,
            "failed_workflows": 8,
            "avg_duration": 5.2,
        }
    )

    # Mock MessageBus
    mock_bus = MagicMock()
    mock_bus.get_queue_size = AsyncMock(return_value=3)
    mock_bus.close = AsyncMock()

    with patch("src.api.v1.agents.SkillOrchestrator", return_value=mock_orchestrator), patch(
        "src.api.v1.agents.MessageBus", return_value=mock_bus
    ):
        response = client.get("/api/v1/agents/research_manager/details")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["agent_id"] == "research_manager"
    assert data["level"] == "manager"
    assert data["status"] == "active"
    assert len(data["capabilities"]) == 2
    assert len(data["skills"]) == 3
    assert "performance" in data
    assert data["performance"]["queue_size"] == 3


def test_get_agent_details_not_found(client):
    """Test agent details for non-existent agent."""
    mock_orchestrator = MagicMock()
    mock_orchestrator._supervisors = {}

    with patch("src.api.v1.agents.SkillOrchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/agents/unknown_agent/details")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_agent_details_idle_status(client):
    """Test agent details with idle status (no children)."""
    mock_supervisor = MagicMock()
    mock_supervisor.name = "idle_agent"
    mock_supervisor.level = MagicMock(value="worker")
    mock_supervisor.capabilities = []
    mock_supervisor.child_supervisors = []
    mock_supervisor.child_skills = []

    mock_orchestrator = MagicMock()
    mock_orchestrator._supervisors = {"idle_agent": mock_supervisor}
    mock_orchestrator.get_metrics = MagicMock(
        return_value={"total_workflows": 0, "successful_workflows": 0, "failed_workflows": 0}
    )

    mock_bus = MagicMock()
    mock_bus.get_queue_size = AsyncMock(return_value=0)
    mock_bus.close = AsyncMock()

    with patch("src.api.v1.agents.SkillOrchestrator", return_value=mock_orchestrator), patch(
        "src.api.v1.agents.MessageBus", return_value=mock_bus
    ):
        response = client.get("/api/v1/agents/idle_agent/details")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "idle"
    assert data["performance"]["queue_size"] == 0


# =============================================================================
# Pydantic Model Validation Tests
# =============================================================================


def test_blackboard_entry_model():
    """Test BlackboardEntry model validation."""
    entry = BlackboardEntry(
        key="test_key",
        value={"data": "test"},
        owner_skill="test_skill",
        timestamp=datetime.now(UTC),
        ttl_remaining=3600,
    )

    assert entry.key == "test_key"
    assert entry.value["data"] == "test"
    assert entry.owner_skill == "test_skill"
    assert entry.ttl_remaining == 3600


def test_hierarchy_node_model():
    """Test HierarchyNode model validation."""
    node = HierarchyNode(
        agent_id="exec_001",
        name="Executive",
        level=AgentLevel.EXECUTIVE,
        status=AgentStatus.ACTIVE,
        capabilities=["planning"],
        child_count=3,
    )

    assert node.agent_id == "exec_001"
    assert node.level == AgentLevel.EXECUTIVE
    assert node.status == AgentStatus.ACTIVE
    assert node.child_count == 3


def test_agent_performance_model():
    """Test AgentPerformance model validation."""
    perf = AgentPerformance(
        tasks_completed=100, tasks_failed=5, success_rate=0.95, avg_duration_ms=5000, queue_size=2
    )

    assert perf.tasks_completed == 100
    assert perf.success_rate == 0.95
    assert perf.avg_duration_ms == 5000
    assert perf.queue_size == 2


def test_agent_details_model():
    """Test AgentDetails model validation."""
    details = AgentDetails(
        agent_id="test_agent",
        name="Test Agent",
        type="manager",
        level=AgentLevel.MANAGER,
        status=AgentStatus.ACTIVE,
        capabilities=["test"],
        skills=["skill1"],
        active_tasks=[],
        performance=AgentPerformance(
            tasks_completed=50, tasks_failed=2, success_rate=0.96, avg_duration_ms=3000, queue_size=1
        ),
    )

    assert details.agent_id == "test_agent"
    assert details.level == AgentLevel.MANAGER
    assert details.performance.success_rate == 0.96


# =============================================================================
# Edge Cases
# =============================================================================


def test_agent_hierarchy_empty():
    """Test hierarchy with no supervisors."""
    mock_orchestrator = MagicMock()
    mock_orchestrator._supervisors = {}

    with patch("src.api.v1.agents.SkillOrchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/agents/hierarchy")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["nodes"]) == 0
    assert len(data["edges"]) == 0


@pytest.mark.asyncio
async def test_blackboard_permission_error(client):
    """Test blackboard with permission errors (should skip entries)."""
    mock_memory = MagicMock()
    mock_memory.list_keys = AsyncMock(return_value=["private_key"])
    mock_memory._redis = MagicMock()
    mock_memory._redis.client = AsyncMock()

    async def mock_scan_iter(*args, **kwargs):
        yield "shared_memory:private:other_skill:private_key"

    mock_memory._redis.client.return_value.scan_iter = mock_scan_iter

    mock_memory.get_metadata = AsyncMock(
        return_value={
            "key": "private_key",
            "scope": "private",
            "owner_skill": "other_skill",
            "timestamp": "2026-01-15T10:30:00Z",
        }
    )

    # Raise PermissionError on read
    mock_memory.read = AsyncMock(side_effect=PermissionError("Access denied"))
    mock_memory.aclose = AsyncMock()

    with patch("src.api.v1.agents.SharedMemoryProtocol", return_value=mock_memory):
        response = client.get("/api/v1/agents/blackboard")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Should have 0 entries (permission denied)
    assert data["total_entries"] == 0
