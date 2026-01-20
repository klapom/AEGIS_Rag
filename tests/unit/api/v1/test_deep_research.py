"""Unit Tests for Deep Research API Endpoints.

Sprint 116.10: Deep Research Multi-Step (13 SP)

Tests for deep research API endpoints with mocked dependencies.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.deep_research import DeepResearchResponse
from src.api.models.research import Source


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_research_graph():
    """Mock research graph fixture."""
    with patch("src.api.v1.deep_research.get_research_graph_with_config") as mock:
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "original_query": "What is ML?",
                "sub_queries": ["ML definition", "ML applications"],
                "all_contexts": [
                    {
                        "text": "ML is AI subset",
                        "score": 0.9,
                        "source": "vector",
                        "metadata": {},
                        "entities": [],
                        "relationships": [],
                        "research_query": "ML definition",
                        "query_index": 1,
                    }
                ],
                "synthesis": "Machine learning is a subset of AI...",
                "iteration": 1,
                "current_step": "complete",
                "execution_steps": [],
                "intermediate_answers": {},
                "metadata": {},
            }
        )
        mock.return_value = mock_graph
        yield mock


class TestStartDeepResearch:
    """Tests for POST /api/v1/research/deep endpoint."""

    @pytest.mark.asyncio
    async def test_start_research_success(self, client, mock_research_graph):
        """Test starting deep research successfully."""
        response = client.post(
            "/api/v1/research/deep",
            json={
                "query": "What is machine learning?",
                "namespace": "ml_docs",
                "max_iterations": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "What is machine learning?"
        assert data["status"] == "pending"
        assert "id" in data
        assert data["id"].startswith("research_")

    @pytest.mark.asyncio
    async def test_start_research_empty_query(self, client):
        """Test starting research with empty query fails."""
        response = client.post(
            "/api/v1/research/deep",
            json={
                "query": "",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_start_research_invalid_max_iterations(self, client):
        """Test starting research with invalid max_iterations."""
        response = client.post(
            "/api/v1/research/deep",
            json={
                "query": "Test",
                "max_iterations": 10,  # Max is 5
            },
        )

        assert response.status_code == 422  # Validation error


class TestGetResearchStatus:
    """Tests for GET /api/v1/research/deep/{id}/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client):
        """Test getting status for non-existent research."""
        response = client.get("/api/v1/research/deep/nonexistent/status")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_status_success(self, client, mock_research_graph):
        """Test getting research status successfully."""
        # Start research first
        start_response = client.post(
            "/api/v1/research/deep",
            json={"query": "Test query"},
        )
        research_id = start_response.json()["id"]

        # Get status
        response = client.get(f"/api/v1/research/deep/{research_id}/status")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == research_id
        assert "status" in data
        assert "current_step" in data
        assert "progress_percent" in data
        assert 0 <= data["progress_percent"] <= 100


class TestGetResearchResult:
    """Tests for GET /api/v1/research/deep/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, client):
        """Test getting result for non-existent research."""
        response = client.get("/api/v1/research/deep/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_result_success(self, client, mock_research_graph):
        """Test getting research result successfully."""
        # Start research
        start_response = client.post(
            "/api/v1/research/deep",
            json={"query": "Test query"},
        )
        research_id = start_response.json()["id"]

        # Get result
        response = client.get(f"/api/v1/research/deep/{research_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == research_id
        assert data["query"] == "Test query"
        assert "status" in data
        assert "execution_steps" in data


class TestCancelResearch:
    """Tests for POST /api/v1/research/deep/{id}/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_not_found(self, client):
        """Test cancelling non-existent research."""
        response = client.post(
            "/api/v1/research/deep/nonexistent/cancel",
            json={"reason": "Test"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_success(self, client, mock_research_graph):
        """Test cancelling research successfully."""
        # Start research
        start_response = client.post(
            "/api/v1/research/deep",
            json={"query": "Test query"},
        )
        research_id = start_response.json()["id"]

        # Cancel research
        response = client.post(
            f"/api/v1/research/deep/{research_id}/cancel",
            json={"reason": "User cancelled"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_without_reason(self, client, mock_research_graph):
        """Test cancelling research without reason."""
        # Start research
        start_response = client.post(
            "/api/v1/research/deep",
            json={"query": "Test query"},
        )
        research_id = start_response.json()["id"]

        # Cancel without reason
        response = client.post(f"/api/v1/research/deep/{research_id}/cancel")

        assert response.status_code == 200


class TestExportResearch:
    """Tests for GET /api/v1/research/deep/{id}/export endpoint."""

    @pytest.mark.asyncio
    async def test_export_not_found(self, client):
        """Test exporting non-existent research."""
        response = client.get("/api/v1/research/deep/nonexistent/export?format=markdown")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_markdown_success(self, client, mock_research_graph):
        """Test exporting research as markdown."""
        # Start research
        start_response = client.post(
            "/api/v1/research/deep",
            json={"query": "Test query"},
        )
        research_id = start_response.json()["id"]

        # Export as markdown
        response = client.get(
            f"/api/v1/research/deep/{research_id}/export?format=markdown"
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert "Content-Disposition" in response.headers
        assert "research_" in response.headers["Content-Disposition"]

    @pytest.mark.asyncio
    async def test_export_pdf_not_implemented(self, client, mock_research_graph):
        """Test that PDF export is not yet implemented."""
        # Start research
        start_response = client.post(
            "/api/v1/research/deep",
            json={"query": "Test query"},
        )
        research_id = start_response.json()["id"]

        # Try to export as PDF
        response = client.get(f"/api/v1/research/deep/{research_id}/export?format=pdf")

        assert response.status_code == 501  # Not implemented

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, client, mock_research_graph):
        """Test exporting with invalid format."""
        # Start research
        start_response = client.post(
            "/api/v1/research/deep",
            json={"query": "Test query"},
        )
        research_id = start_response.json()["id"]

        # Try invalid format
        response = client.get(f"/api/v1/research/deep/{research_id}/export?format=json")

        assert response.status_code == 400  # Bad request


class TestDeepResearchHealth:
    """Tests for GET /api/v1/research/deep/health endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/research/deep/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "deep_research"
