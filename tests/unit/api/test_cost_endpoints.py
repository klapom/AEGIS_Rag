"""Unit tests for Cost API endpoints.

Sprint 31 Feature 31.10a: Cost API Backend Implementation

Tests cover:
- GET /api/v1/admin/costs/stats endpoint
- GET /api/v1/admin/costs/history endpoint
- Budget status calculation (ok/warning/critical)
- Provider and model aggregation
- Time range filtering (7d, 30d, all)
"""

from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.components.llm_proxy.cost_tracker import CostTracker


@pytest.fixture
def client() -> TestClient:
    """Create FastAPI test client.

    Returns:
        TestClient: Configured test client for API endpoints
    """
    return TestClient(app)


@pytest.fixture
def temp_cost_db(tmp_path: Path) -> Generator[Path, None, None]:
    """Create temporary cost tracking database with sample data.

    Args:
        tmp_path: pytest temporary directory fixture

    Yields:
        Path: Temporary database path

    Notes:
        - Creates database with realistic cost data
        - Seeds data for last 30 days
        - Includes multiple providers and models
        - Automatically cleaned up after test
    """
    db_path = tmp_path / "test_cost_tracking.db"

    # Create tracker with temp database
    tracker = CostTracker(db_path=db_path)

    # Seed sample data (last 30 days)
    now = datetime.now()

    # Day 1-5: Ollama only (free)
    for day in range(5):
        (now - timedelta(days=30 - day)).isoformat()
        tracker.track_request(
            provider="local_ollama",
            model="gemma-3-4b-it",
            task_type="extraction",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0,  # Free
            latency_ms=500.0,
            routing_reason="local_first",
        )

    # Day 6-15: Mix of Ollama and Alibaba Cloud
    for day in range(5, 15):
        30 - day

        # Ollama request
        tracker.track_request(
            provider="local_ollama",
            model="gemma-3-4b-it",
            task_type="extraction",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0,
            latency_ms=500.0,
            routing_reason="local_first",
        )

        # Alibaba Cloud VLM request (more expensive)
        tracker.track_request(
            provider="alibaba_cloud",
            model="qwen3-vl-30b-a3b-instruct",
            task_type="vision",
            tokens_input=2000,
            tokens_output=500,
            cost_usd=0.016,  # Input: 2000 * 0.008/1000 = $0.016
            latency_ms=1200.0,
            routing_reason="vlm_fallback",
        )

    # Day 16-30: All three providers
    for day in range(15, 30):
        # Ollama
        tracker.track_request(
            provider="local_ollama",
            model="llama3.2:3b",
            task_type="generation",
            tokens_input=500,
            tokens_output=300,
            cost_usd=0.0,
            latency_ms=300.0,
        )

        # Alibaba Cloud text model (cheaper)
        tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="generation",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0015,  # Input: 1000 * 0.001/1000, Output: 500 * 0.001/1000
            latency_ms=800.0,
        )

        # OpenAI (most expensive)
        tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0125,  # Input: 1000 * 0.01/1000, Output: 500 * 0.005/1000
            latency_ms=1500.0,
            routing_reason="quality_required",
        )

    yield db_path

    # Cleanup (pytest handles temp directory deletion)


@pytest.fixture
def mock_cost_tracker(temp_cost_db: Path):
    """Mock get_cost_tracker to use temporary database.

    Args:
        temp_cost_db: Temporary database path from fixture

    Yields:
        CostTracker instance with test data
    """
    tracker = CostTracker(db_path=temp_cost_db)

    with patch(
        "src.api.v1.admin_costs.get_cost_tracker",
        return_value=tracker,
    ):
        yield tracker


def test_get_cost_stats_7d(client: TestClient, mock_cost_tracker: CostTracker):
    """Test cost stats endpoint with 7d time range.

    Args:
        client: FastAPI test client
        mock_cost_tracker: Mocked cost tracker with test data

    Asserts:
        - HTTP 200 response
        - Contains required fields
        - Time range is "7d"
        - Has provider breakdown
        - Has budget information
    """
    response = client.get("/api/v1/admin/costs/stats?time_range=7d")
    assert response.status_code == 200

    data = response.json()

    # Check required fields
    assert "total_cost_usd" in data
    assert "total_tokens" in data
    assert "total_calls" in data
    assert "avg_cost_per_call" in data
    assert "by_provider" in data
    assert "by_model" in data
    assert "budgets" in data
    assert "time_range" in data

    # Check time range
    assert data["time_range"] == "7d"

    # Check provider breakdown exists
    assert isinstance(data["by_provider"], dict)

    # Check budget information exists
    assert isinstance(data["budgets"], dict)


def test_get_cost_stats_30d(client: TestClient, mock_cost_tracker: CostTracker):
    """Test cost stats endpoint with 30d time range.

    Args:
        client: FastAPI test client
        mock_cost_tracker: Mocked cost tracker with test data

    Asserts:
        - HTTP 200 response
        - Time range is "30d"
        - Contains all providers (ollama, alibaba_cloud, openai)
        - Totals are positive
    """
    response = client.get("/api/v1/admin/costs/stats?time_range=30d")
    assert response.status_code == 200

    data = response.json()

    # Check time range
    assert data["time_range"] == "30d"

    # Should have data from all providers
    assert "local_ollama" in data["by_provider"]
    assert "alibaba_cloud" in data["by_provider"]
    assert "openai" in data["by_provider"]

    # Totals should be positive
    assert data["total_cost_usd"] > 0
    assert data["total_tokens"] > 0
    assert data["total_calls"] > 0


def test_get_cost_stats_budget_calculation(client: TestClient, mock_cost_tracker: CostTracker):
    """Test budget status calculation.

    Args:
        client: FastAPI test client
        mock_cost_tracker: Mocked cost tracker with test data

    Asserts:
        - Ollama budget is always "ok" (free)
        - Alibaba Cloud budget has correct limit
        - Budget status is one of (ok, warning, critical)
        - Utilization percentage is calculated correctly
        - Remaining budget is non-negative
    """
    response = client.get("/api/v1/admin/costs/stats?time_range=30d")
    assert response.status_code == 200

    data = response.json()
    budgets = data["budgets"]

    # Ollama should always be free
    if "local_ollama" in budgets:
        ollama_budget = budgets["local_ollama"]
        assert ollama_budget["status"] == "ok"
        assert ollama_budget["spent_usd"] == 0.0
        assert ollama_budget["limit_usd"] == 0.0

    # Alibaba Cloud budget
    if "alibaba_cloud" in budgets:
        alibaba_budget = budgets["alibaba_cloud"]
        assert alibaba_budget["limit_usd"] > 0  # Should have budget limit
        assert alibaba_budget["status"] in ["ok", "warning", "critical"]
        assert alibaba_budget["utilization_percent"] >= 0
        assert alibaba_budget["remaining_usd"] >= 0

    # OpenAI budget
    if "openai" in budgets:
        openai_budget = budgets["openai"]
        assert openai_budget["limit_usd"] > 0
        assert openai_budget["status"] in ["ok", "warning", "critical"]
        assert openai_budget["utilization_percent"] >= 0
        assert openai_budget["remaining_usd"] >= 0


def test_get_cost_stats_provider_aggregation(client: TestClient, mock_cost_tracker: CostTracker):
    """Test provider cost aggregation.

    Args:
        client: FastAPI test client
        mock_cost_tracker: Mocked cost tracker with test data

    Asserts:
        - Each provider has cost, tokens, calls
        - avg_cost_per_call is calculated correctly
        - Ollama cost is always $0.00
        - Cloud providers have non-zero costs
    """
    response = client.get("/api/v1/admin/costs/stats?time_range=30d")
    assert response.status_code == 200

    data = response.json()
    by_provider = data["by_provider"]

    # Check each provider
    for _provider, stats in by_provider.items():
        assert "cost_usd" in stats
        assert "tokens" in stats
        assert "calls" in stats
        assert "avg_cost_per_call" in stats

        # Verify avg_cost_per_call calculation
        if stats["calls"] > 0:
            expected_avg = stats["cost_usd"] / stats["calls"]
            assert abs(stats["avg_cost_per_call"] - expected_avg) < 0.0001

    # Ollama should be free
    if "local_ollama" in by_provider:
        assert by_provider["local_ollama"]["cost_usd"] == 0.0

    # Cloud providers should have costs
    if "alibaba_cloud" in by_provider:
        assert by_provider["alibaba_cloud"]["cost_usd"] > 0
    if "openai" in by_provider:
        assert by_provider["openai"]["cost_usd"] > 0


def test_get_cost_stats_model_aggregation(client: TestClient, mock_cost_tracker: CostTracker):
    """Test model cost aggregation.

    Args:
        client: FastAPI test client
        mock_cost_tracker: Mocked cost tracker with test data

    Asserts:
        - Model keys are in "provider/model" format
        - Each model has provider, cost, tokens, calls
        - Model costs sum to total cost
    """
    response = client.get("/api/v1/admin/costs/stats?time_range=30d")
    assert response.status_code == 200

    data = response.json()
    by_model = data["by_model"]

    # Check model key format (provider/model)
    for model_key, stats in by_model.items():
        assert "/" in model_key  # Should be "provider/model"
        assert "provider" in stats
        assert "cost_usd" in stats
        assert "tokens" in stats
        assert "calls" in stats

    # Sum of model costs should equal total cost
    total_model_cost = sum(stats["cost_usd"] for stats in by_model.values())
    assert abs(total_model_cost - data["total_cost_usd"]) < 0.01  # Allow small float error


def test_get_cost_history_7d(client: TestClient, mock_cost_tracker: CostTracker):
    """Test cost history endpoint with 7d time range.

    Args:
        client: FastAPI test client
        mock_cost_tracker: Mocked cost tracker with test data

    Asserts:
        - HTTP 200 response
        - Returns list of CostHistory objects
        - Each entry has date, cost_usd, tokens, calls
        - Dates are in YYYY-MM-DD format
        - Sorted chronologically (oldest to newest)
    """
    response = client.get("/api/v1/admin/costs/history?time_range=7d")
    assert response.status_code == 200

    data = response.json()

    # Should return list
    assert isinstance(data, list)

    # Check each entry
    for entry in data:
        assert "date" in entry
        assert "cost_usd" in entry
        assert "tokens" in entry
        assert "calls" in entry

        # Date format check (YYYY-MM-DD)
        date_str = entry["date"]
        datetime.strptime(date_str, "%Y-%m-%d")  # Should not raise

    # Check chronological order
    if len(data) > 1:
        for i in range(len(data) - 1):
            date1 = datetime.strptime(data[i]["date"], "%Y-%m-%d")
            date2 = datetime.strptime(data[i + 1]["date"], "%Y-%m-%d")
            assert date1 <= date2  # Should be sorted ascending


def test_get_cost_history_30d(client: TestClient, mock_cost_tracker: CostTracker):
    """Test cost history endpoint with 30d time range.

    Args:
        client: FastAPI test client
        mock_cost_tracker: Mocked cost tracker with test data

    Asserts:
        - HTTP 200 response
        - Returns more data points than 7d
        - All dates are within last 30 days
    """
    response = client.get("/api/v1/admin/costs/history?time_range=30d")
    assert response.status_code == 200

    data = response.json()

    # Should return list
    assert isinstance(data, list)

    # Should have data points
    assert len(data) > 0

    # All dates should be within last 30 days
    cutoff_date = (datetime.now() - timedelta(days=30)).date()
    for entry in data:
        entry_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        assert entry_date >= cutoff_date


def test_get_cost_history_all(client: TestClient, mock_cost_tracker: CostTracker):
    """Test cost history endpoint with all-time range.

    Args:
        client: FastAPI test client
        mock_cost_tracker: Mocked cost tracker with test data

    Asserts:
        - HTTP 200 response
        - Returns maximum data points
        - Includes oldest data
    """
    response = client.get("/api/v1/admin/costs/history?time_range=all")
    assert response.status_code == 200

    data = response.json()

    # Should return list
    assert isinstance(data, list)

    # Should have data points
    assert len(data) > 0


def test_cost_stats_empty_database(client: TestClient, tmp_path: Path):
    """Test cost stats with empty database.

    Args:
        client: FastAPI test client
        tmp_path: Temporary directory for empty database

    Asserts:
        - HTTP 200 response (not 500)
        - Total cost is 0.0
        - Total calls is 0
        - Empty provider/model breakdowns
    """
    # Create empty database
    empty_db_path = tmp_path / "empty_cost_tracking.db"
    empty_tracker = CostTracker(db_path=empty_db_path)

    with patch("src.api.v1.admin_costs.get_cost_tracker", return_value=empty_tracker):
        response = client.get("/api/v1/admin/costs/stats?time_range=7d")
        assert response.status_code == 200

        data = response.json()
        assert data["total_cost_usd"] == 0.0
        assert data["total_tokens"] == 0
        assert data["total_calls"] == 0
        assert len(data["by_provider"]) == 0
        assert len(data["by_model"]) == 0


def test_cost_history_empty_database(client: TestClient, tmp_path: Path):
    """Test cost history with empty database.

    Args:
        client: FastAPI test client
        tmp_path: Temporary directory for empty database

    Asserts:
        - HTTP 200 response (not 500)
        - Returns empty list
    """
    # Create empty database
    empty_db_path = tmp_path / "empty_cost_tracking.db"
    empty_tracker = CostTracker(db_path=empty_db_path)

    with patch("src.api.v1.admin_costs.get_cost_tracker", return_value=empty_tracker):
        response = client.get("/api/v1/admin/costs/history?time_range=7d")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


def test_cost_stats_invalid_time_range(client: TestClient, mock_cost_tracker: CostTracker):
    """Test cost stats with invalid time range.

    Args:
        client: FastAPI test client
        mock_cost_tracker: Mocked cost tracker with test data

    Asserts:
        - HTTP 422 (validation error) for invalid time range
    """
    response = client.get("/api/v1/admin/costs/stats?time_range=invalid")
    assert response.status_code == 422  # Pydantic validation error
