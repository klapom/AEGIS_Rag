"""Tests for Graph Visualization API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_visualization_data():
    """Sample visualization response data."""
    return {
        "nodes": [
            {"id": "entity_1", "label": "John Smith", "type": "PERSON", "group": 1},
            {"id": "entity_2", "label": "Google", "type": "ORGANIZATION", "group": 2},
        ],
        "links": [{"source": "entity_1", "target": "entity_2", "type": "WORKS_AT", "value": 1}],
    }


@pytest.fixture
def sample_metadata():
    """Sample metadata."""
    return {
        "node_count": 2,
        "edge_count": 1,
        "truncated": False,
        "depth": 1,
        "format": "d3",
    }


class TestGraphVisualizationAPI:
    """Test graph visualization API endpoints."""

    @patch("src.api.graph_visualization.get_visualization_exporter")
    def test_visualize_entity_neighborhood_success(
        self, mock_get_exporter, client, sample_visualization_data, sample_metadata
    ):
        """Test successful entity neighborhood visualization."""
        mock_exporter = AsyncMock()
        mock_exporter.export_subgraph = AsyncMock(
            return_value={**sample_visualization_data, "metadata": sample_metadata}
        )
        mock_get_exporter.return_value = mock_exporter

        response = client.get("/api/v1/graph/visualize/entity_1?depth=1&max_nodes=100&format=d3")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "metadata" in data
        assert data["data"]["nodes"][0]["id"] == "entity_1"

    @patch("src.api.graph_visualization.get_visualization_exporter")
    def test_visualize_entity_neighborhood_custom_params(self, mock_get_exporter, client):
        """Test entity visualization with custom parameters."""
        mock_exporter = AsyncMock()
        mock_exporter.export_subgraph = AsyncMock(
            return_value={
                "nodes": [],
                "links": [],
                "metadata": {
                    "node_count": 0,
                    "edge_count": 0,
                    "truncated": False,
                    "depth": 2,
                    "format": "cytoscape",
                },
            }
        )
        mock_get_exporter.return_value = mock_exporter

        response = client.get(
            "/api/v1/graph/visualize/entity_1?depth=2&max_nodes=50&format=cytoscape"
        )

        assert response.status_code == 200

    @patch("src.api.graph_visualization.get_visualization_exporter")
    def test_visualize_custom_subgraph_success(
        self, mock_get_exporter, client, sample_visualization_data, sample_metadata
    ):
        """Test successful custom subgraph visualization."""
        mock_exporter = AsyncMock()
        mock_exporter.export_subgraph = AsyncMock(
            return_value={**sample_visualization_data, "metadata": sample_metadata}
        )
        mock_get_exporter.return_value = mock_exporter

        response = client.get(
            "/api/v1/graph/visualize/subgraph?entity_ids=entity_1&entity_ids=entity_2&depth=1&format=d3"
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "metadata" in data

    @patch("src.api.graph_visualization.get_visualization_exporter")
    def test_visualize_custom_subgraph_empty_entity_ids(self, mock_get_exporter, client):
        """Test custom subgraph with no entity IDs."""
        response = client.get("/api/v1/graph/visualize/subgraph")

        assert response.status_code == 422  # Validation error

    @patch("src.api.graph_visualization.get_visualization_exporter")
    def test_visualize_community_success(
        self, mock_get_exporter, client, sample_visualization_data, sample_metadata
    ):
        """Test successful community visualization."""
        mock_exporter = AsyncMock()
        mock_exporter.neo4j_client = AsyncMock()
        mock_exporter.neo4j_client.execute_query = AsyncMock(
            return_value=[{"entity_id": "entity_1"}, {"entity_id": "entity_2"}]
        )
        mock_exporter.export_subgraph = AsyncMock(
            return_value={**sample_visualization_data, "metadata": sample_metadata}
        )
        mock_get_exporter.return_value = mock_exporter

        response = client.get(
            "/api/v1/graph/visualize/community/community_1?max_nodes=100&format=d3"
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "metadata" in data

    @patch("src.api.graph_visualization.get_visualization_exporter")
    def test_visualize_community_not_found(self, mock_get_exporter, client):
        """Test community visualization when community not found."""
        mock_exporter = AsyncMock()
        mock_exporter.neo4j_client = AsyncMock()
        mock_exporter.neo4j_client.execute_query = AsyncMock(return_value=[])
        mock_get_exporter.return_value = mock_exporter

        response = client.get("/api/v1/graph/visualize/community/nonexistent")

        assert response.status_code == 404

    @patch("src.api.graph_visualization.get_visualization_exporter")
    def test_visualize_entity_database_error(self, mock_get_exporter, client):
        """Test entity visualization with database error."""
        from src.core.exceptions import DatabaseConnectionError

        mock_exporter = AsyncMock()
        mock_exporter.export_subgraph = AsyncMock(
            side_effect=DatabaseConnectionError("Connection failed")
        )
        mock_get_exporter.return_value = mock_exporter

        response = client.get("/api/v1/graph/visualize/entity_1")

        assert response.status_code == 503

    @patch("src.api.graph_visualization.get_visualization_exporter")
    def test_visualize_entity_generic_error(self, mock_get_exporter, client):
        """Test entity visualization with generic error."""
        mock_exporter = AsyncMock()
        mock_exporter.export_subgraph = AsyncMock(side_effect=Exception("Unexpected error"))
        mock_get_exporter.return_value = mock_exporter

        response = client.get("/api/v1/graph/visualize/entity_1")

        assert response.status_code == 500

    def test_visualize_entity_invalid_depth(self, client):
        """Test entity visualization with invalid depth parameter."""
        response = client.get("/api/v1/graph/visualize/entity_1?depth=10")

        assert response.status_code == 422  # Validation error
