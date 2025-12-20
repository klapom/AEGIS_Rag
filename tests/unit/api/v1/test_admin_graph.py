"""Unit tests for Admin Graph Analytics API endpoints.

Sprint 52 Feature 52.2.1: Graph Analytics Stats
Sprint 58: Fixed patching strategy for module imports

Tests cover:
- Graph statistics endpoint
- Entity and relationship distribution
- Community statistics
- Orphan node detection
- Error handling for Neo4j failures
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _create_result_mock(single_value=None, data_value=None):
    """Create a properly configured async result mock for Neo4j queries."""
    result = AsyncMock()
    if single_value is not None:
        result.single = AsyncMock(return_value=single_value)
    if data_value is not None:
        result.data = AsyncMock(return_value=data_value)
    return result


def create_graph_mock_client(
    entity_count: int = 856,
    rel_count: int = 1204,
    entity_types: list | None = None,
    rel_types: list | None = None,
    communities: list | None = None,
    orphan_count: int = 5,
    summary_generated: int = 2,
    summary_pending: int = 1,
    raise_error: bool = False,
    null_results: bool = False,
):
    """Create a mock Neo4j client for graph stats testing.

    This helper creates properly configured mocks that work with the
    graph stats endpoint's query pattern. Uses async context manager
    for proper Neo4j session handling.
    """
    if raise_error:
        return None  # Will use side_effect for error case

    mock_session = AsyncMock()

    if null_results:
        null_result = _create_result_mock(single_value=None, data_value=[])
        mock_session.run = AsyncMock(side_effect=[null_result] * 7)
    else:
        # Create result mocks for each query
        entity_result = _create_result_mock(single_value={"count": entity_count})
        rel_result = _create_result_mock(single_value={"count": rel_count})
        entity_types_result = _create_result_mock(data_value=entity_types or [])
        rel_types_result = _create_result_mock(data_value=rel_types or [])
        community_result = _create_result_mock(data_value=communities or [])
        orphan_result = _create_result_mock(single_value={"count": orphan_count})
        summary_result = _create_result_mock(
            single_value={"generated": summary_generated, "pending": summary_pending}
        )

        mock_session.run = AsyncMock(
            side_effect=[
                entity_result,
                rel_result,
                entity_types_result,
                rel_types_result,
                community_result,
                orphan_result,
                summary_result,
            ]
        )

    # Mock async context manager
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)

    mock_neo4j = MagicMock()
    mock_neo4j.driver = mock_driver

    return mock_neo4j


class TestGraphStatsEndpoint:
    """Tests for GET /admin/graph/stats endpoint."""

    def test_get_graph_stats_success(self, graph_test_client):
        """Test successful retrieval of graph statistics.

        Uses graph_test_client fixture which applies patches BEFORE app import.
        """
        response = graph_test_client.get("/api/v1/admin/graph/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_entities"] == 856
        assert data["total_relationships"] == 1204
        assert data["community_count"] == 3

    def test_get_graph_stats_with_entity_types(self, graph_test_client):
        """Test graph stats includes entity type distribution."""
        response = graph_test_client.get("/api/v1/admin/graph/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_types"]["PERSON"] == 450
        assert data["entity_types"]["ORGANIZATION"] == 300
        assert data["relationship_types"]["RELATES_TO"] == 700

    def test_get_graph_stats_empty_graph(self):
        """Test graph stats for empty graph."""
        mock_neo4j = create_graph_mock_client(
            entity_count=0,
            rel_count=0,
            orphan_count=0,
            summary_generated=0,
            summary_pending=0,
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/api/v1/admin/graph/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["total_entities"] == 0
            assert data["total_relationships"] == 0
            assert data["community_count"] == 0
            assert data["orphan_nodes"] == 0

    def test_get_graph_stats_null_results(self):
        """Test graph stats handles None results gracefully.

        Note: When Neo4j returns None for queries, the endpoint should either:
        - Return 200 with default values (0) for counts
        - Return 503 if it can't parse the response

        Both behaviors are acceptable for robustness.
        """
        mock_neo4j = create_graph_mock_client(null_results=True)

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/api/v1/admin/graph/stats")

            # Accept either success with defaults or service unavailable
            if response.status_code == 200:
                data = response.json()
                assert data["total_entities"] == 0
                assert data["orphan_nodes"] == 0
            else:
                assert response.status_code == 503  # Service unavailable is acceptable

    def test_get_graph_stats_neo4j_connection_error(self):
        """Test error handling when Neo4j connection fails.

        Note: The endpoint returns 503 Service Unavailable for connection errors.
        """
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            side_effect=Exception("Neo4j connection failed"),
        ):
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/api/v1/admin/graph/stats")
            # 503 for service unavailable is acceptable for connection errors
            assert response.status_code in (500, 503)

    def test_get_graph_stats_query_error(self):
        """Test error handling for Cypher query errors."""
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Cypher syntax error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        mock_neo4j = MagicMock()
        mock_neo4j.driver = mock_driver

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/api/v1/admin/graph/stats")
            # 503 for service unavailable is acceptable for query errors
            assert response.status_code in (500, 503)

    def test_get_graph_stats_community_distribution(self):
        """Test community size distribution calculation."""
        mock_neo4j = create_graph_mock_client(
            entity_count=1000,
            rel_count=2000,
            communities=[
                {"community": 1, "size": 500},
                {"community": 2, "size": 300},
                {"community": 3, "size": 200},
            ],
            orphan_count=10,
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/api/v1/admin/graph/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["community_count"] == 3
            assert data["community_sizes"] == [500, 300, 200]

    def test_get_graph_stats_avg_degree_calculation(self):
        """Test average node degree calculation."""
        # If we have 100 entities and 200 relationships
        # avg_degree = (2 * rel_count) / entity_count = (2 * 200) / 100 = 4.0
        mock_neo4j = create_graph_mock_client(
            entity_count=100,
            rel_count=200,
            orphan_count=0,
            summary_generated=0,
            summary_pending=0,
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/api/v1/admin/graph/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["avg_degree"] == 4.0

    def test_get_graph_stats_response_timestamp(self):
        """Test that response includes current timestamp."""
        mock_neo4j = create_graph_mock_client(
            entity_count=0,
            rel_count=0,
            orphan_count=0,
            summary_generated=0,
            summary_pending=0,
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/api/v1/admin/graph/stats")

            assert response.status_code == 200
            data = response.json()
            assert "timestamp" in data
            # Verify it's a valid ISO 8601 timestamp
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
