"""Unit tests for Agent Monitoring APIs (Part 2: orchestration.py).

Sprint 99 Feature 99.2: Agent Monitoring APIs

Tests:
    - GET /api/v1/orchestration/active: List active orchestrations
    - GET /api/v1/orchestration/:id/trace: Get orchestration timeline
    - GET /api/v1/orchestration/metrics: Get performance metrics
"""

from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.agents import (
    OrchestrationListResponse,
    OrchestrationMetrics,
    OrchestrationStatus,
    OrchestrationSummary,
    OrchestrationTrace,
    TraceEvent,
)
from src.agents.orchestrator.skill_orchestrator import WorkflowResult


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_orchestrator():
    """Mock SkillOrchestrator fixture."""
    orchestrator = MagicMock()
    orchestrator._active_workflows = {}
    orchestrator._execution_history = []
    return orchestrator


# =============================================================================
# GET /api/v1/orchestration/active
# =============================================================================


def test_list_active_orchestrations_success(client, mock_orchestrator):
    """Test successful listing of active orchestrations."""
    # Create mock workflow result
    workflow_result = MagicMock()
    workflow_result.workflow_id = "wf_123"
    workflow_result.success = True
    workflow_result.total_duration = 15.3
    workflow_result.phase_results = [{"phase": "research"}, {"phase": "synthesis"}]
    workflow_result.errors = []

    # Mock workflow definition
    mock_workflow_def = MagicMock()
    mock_workflow_def.skills = ["web_search", "synthesis"]
    workflow_result.metadata = {
        "workflow": mock_workflow_def,
        "start_time": datetime.now(UTC),
    }

    # Active workflow
    mock_orchestrator._active_workflows = {"wf_123": workflow_result}

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/active")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["orchestration_id"] == "wf_123"
    assert data["items"][0]["status"] == "running"


def test_list_active_orchestrations_pagination(client, mock_orchestrator):
    """Test orchestration list pagination."""
    # Create 25 mock workflows in history
    for i in range(25):
        workflow_result = MagicMock()
        workflow_result.workflow_id = f"wf_{i}"
        workflow_result.success = True
        workflow_result.total_duration = 10.0
        workflow_result.phase_results = []
        workflow_result.errors = []

        mock_workflow_def = MagicMock()
        mock_workflow_def.skills = ["test_skill"]
        workflow_result.metadata = {
            "workflow": mock_workflow_def,
            "start_time": datetime.now(UTC),
        }

        mock_orchestrator._execution_history.append(workflow_result)

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        # Page 1
        response = client.get("/api/v1/orchestration/active?page=1&page_size=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] == 3
        assert len(data["items"]) == 10

        # Page 2
        response = client.get("/api/v1/orchestration/active?page=2&page_size=10")
        data = response.json()
        assert data["page"] == 2
        assert len(data["items"]) == 10


def test_list_active_orchestrations_filter_by_skill(client, mock_orchestrator):
    """Test filtering orchestrations by skill name."""
    # Create workflows with different skills
    for skill in ["web_search", "synthesis", "web_search"]:
        workflow_result = MagicMock()
        workflow_result.workflow_id = f"wf_{skill}"
        workflow_result.success = True
        workflow_result.total_duration = 10.0
        workflow_result.phase_results = []
        workflow_result.errors = []

        mock_workflow_def = MagicMock()
        mock_workflow_def.skills = [skill]
        workflow_result.metadata = {
            "workflow": mock_workflow_def,
            "start_time": datetime.now(UTC),
        }

        mock_orchestrator._execution_history.append(workflow_result)

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/active?skill=web_search")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2  # 2 web_search workflows
    assert all(item["skill_name"] == "web_search" for item in data["items"])


def test_list_active_orchestrations_filter_by_status(client, mock_orchestrator):
    """Test filtering orchestrations by status."""
    # Active workflow
    active_result = MagicMock()
    active_result.workflow_id = "wf_active"
    active_result.success = True
    active_result.phase_results = []
    active_result.errors = []
    mock_workflow_def = MagicMock()
    mock_workflow_def.skills = ["test"]
    active_result.metadata = {"workflow": mock_workflow_def, "start_time": datetime.now(UTC)}
    mock_orchestrator._active_workflows = {"wf_active": active_result}

    # Completed workflow
    completed_result = MagicMock()
    completed_result.workflow_id = "wf_completed"
    completed_result.success = True
    completed_result.total_duration = 10.0
    completed_result.phase_results = []
    completed_result.errors = []
    completed_result.metadata = {"workflow": mock_workflow_def, "start_time": datetime.now(UTC)}
    mock_orchestrator._execution_history = [completed_result]

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        # Filter by running
        response = client.get("/api/v1/orchestration/active?status_filter=running")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "running"

        # Filter by completed
        response = client.get("/api/v1/orchestration/active?status_filter=completed")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "completed"


def test_list_active_orchestrations_empty(client, mock_orchestrator):
    """Test listing with no orchestrations."""
    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/active")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


# =============================================================================
# GET /api/v1/orchestration/:id/trace
# =============================================================================


def test_get_orchestration_trace_success(client, mock_orchestrator):
    """Test successful orchestration trace retrieval."""
    # Mock workflow result
    workflow_result = MagicMock()
    workflow_result.workflow_id = "wf_trace_123"
    workflow_result.success = True
    workflow_result.total_duration = 15.3
    workflow_result.errors = []

    # Mock phase results
    workflow_result.phase_results = [
        {
            "phase": "research",
            "outputs": {"web_search_result": {"data": "test"}},
            "errors": [],
            "failed": False,
        },
        {
            "phase": "synthesis",
            "outputs": {"synthesis_result": {"summary": "test"}},
            "errors": [],
            "failed": False,
        },
    ]

    mock_workflow_def = MagicMock()
    mock_workflow_def.skills = ["web_search", "synthesis"]
    workflow_result.metadata = {
        "workflow": mock_workflow_def,
        "start_time": datetime.now(UTC),
    }

    mock_orchestrator.get_workflow_status = MagicMock(return_value=workflow_result)

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/wf_trace_123/trace")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["orchestration_id"] == "wf_trace_123"
    assert "events" in data
    assert len(data["events"]) >= 3  # start + skill events + end
    assert data["total_duration_ms"] == 15300
    assert data["skill_count"] == 2
    assert data["success_rate"] == 1.0


def test_get_orchestration_trace_with_errors(client, mock_orchestrator):
    """Test orchestration trace with errors."""
    workflow_result = MagicMock()
    workflow_result.workflow_id = "wf_error"
    workflow_result.success = False
    workflow_result.total_duration = 5.0
    workflow_result.errors = ["Network timeout"]

    workflow_result.phase_results = [
        {
            "phase": "research",
            "outputs": {"web_search_result": None},
            "errors": ["Network timeout"],
            "failed": True,
        }
    ]

    mock_workflow_def = MagicMock()
    mock_workflow_def.skills = ["web_search"]
    workflow_result.metadata = {
        "workflow": mock_workflow_def,
        "start_time": datetime.now(UTC),
    }

    mock_orchestrator.get_workflow_status = MagicMock(return_value=workflow_result)

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/wf_error/trace")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success_rate"] == 0.0


def test_get_orchestration_trace_not_found(client, mock_orchestrator):
    """Test trace for non-existent orchestration."""
    mock_orchestrator.get_workflow_status = MagicMock(return_value=None)

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/nonexistent/trace")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


# =============================================================================
# GET /api/v1/orchestration/metrics
# =============================================================================


def test_get_orchestration_metrics_success(client, mock_orchestrator):
    """Test successful orchestration metrics retrieval."""
    # Mock metrics
    mock_orchestrator.get_metrics = MagicMock(
        return_value={
            "total_workflows": 150,
            "successful_workflows": 142,
            "failed_workflows": 8,
            "avg_duration": 8.5,
        }
    )

    # Mock history for P95 calculation
    mock_history = []
    for i in range(100):
        result = MagicMock()
        result.total_duration = 5.0 + (i * 0.1)  # 5.0 to 14.9 seconds
        mock_history.append(result)

    mock_orchestrator._execution_history = mock_history

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/metrics")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_count"] == 150
    assert data["success_count"] == 142
    assert data["success_rate"] == pytest.approx(0.947, rel=1e-3)
    assert data["avg_duration_ms"] == 8500.0
    assert data["error_rate"] == pytest.approx(0.053, rel=1e-3)
    assert "p95_latency_ms" in data


def test_get_orchestration_metrics_empty(client, mock_orchestrator):
    """Test metrics with no orchestration history."""
    mock_orchestrator.get_metrics = MagicMock(
        return_value={
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "avg_duration": 0.0,
        }
    )

    mock_orchestrator._execution_history = []

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/metrics")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_count"] == 0
    assert data["success_rate"] == 0.0
    assert data["p95_latency_ms"] == 0.0


def test_get_orchestration_metrics_all_failures(client, mock_orchestrator):
    """Test metrics with all failed orchestrations."""
    mock_orchestrator.get_metrics = MagicMock(
        return_value={
            "total_workflows": 10,
            "successful_workflows": 0,
            "failed_workflows": 10,
            "avg_duration": 3.0,
        }
    )

    mock_history = []
    for i in range(10):
        result = MagicMock()
        result.total_duration = 3.0
        mock_history.append(result)

    mock_orchestrator._execution_history = mock_history

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/metrics")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["success_rate"] == 0.0
    assert data["error_rate"] == 1.0


# =============================================================================
# Pydantic Model Validation Tests
# =============================================================================


def test_orchestration_summary_model():
    """Test OrchestrationSummary model validation."""
    summary = OrchestrationSummary(
        orchestration_id="orch_123",
        skill_name="test_skill",
        status=OrchestrationStatus.RUNNING,
        started_at=datetime.now(UTC),
        duration_ms=None,
        phase="synthesis",
        progress_percent=65,
    )

    assert summary.orchestration_id == "orch_123"
    assert summary.status == OrchestrationStatus.RUNNING
    assert summary.progress_percent == 65


def test_trace_event_model():
    """Test TraceEvent model validation."""
    event = TraceEvent(
        timestamp=datetime.now(UTC),
        event_type="skill_started",
        skill_name="web_search",
        duration_ms=1200,
        success=True,
    )

    assert event.event_type == "skill_started"
    assert event.skill_name == "web_search"
    assert event.duration_ms == 1200


def test_orchestration_metrics_model():
    """Test OrchestrationMetrics model validation."""
    metrics = OrchestrationMetrics(
        total_count=150,
        success_count=142,
        success_rate=0.947,
        avg_duration_ms=8500.0,
        p95_latency_ms=15000.0,
        error_rate=0.053,
    )

    assert metrics.total_count == 150
    assert metrics.success_rate == 0.947
    assert metrics.p95_latency_ms == 15000.0


# =============================================================================
# Edge Cases
# =============================================================================


def test_list_orchestrations_max_page_size(client, mock_orchestrator):
    """Test maximum page size limit (100)."""
    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/active?page_size=200")

    # Should be rejected by Pydantic validation (max 100)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_orchestration_trace_empty_phases(client, mock_orchestrator):
    """Test trace with no phase results."""
    workflow_result = MagicMock()
    workflow_result.workflow_id = "wf_empty"
    workflow_result.success = True
    workflow_result.total_duration = 1.0
    workflow_result.phase_results = []
    workflow_result.errors = []

    mock_workflow_def = MagicMock()
    mock_workflow_def.skills = []
    workflow_result.metadata = {
        "workflow": mock_workflow_def,
        "start_time": datetime.now(UTC),
    }

    mock_orchestrator.get_workflow_status = MagicMock(return_value=workflow_result)

    with patch("src.api.v1.orchestration.get_orchestrator", return_value=mock_orchestrator):
        response = client.get("/api/v1/orchestration/wf_empty/trace")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["skill_count"] == 0
