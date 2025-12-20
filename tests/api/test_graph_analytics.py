"""Tests for Graph Analytics API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.models import CentralityMetrics, GraphEntity, GraphStatistics, Recommendation


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_centrality_metrics():
    """Sample centrality metrics."""
    return CentralityMetrics(
        entity_id="entity_1",
        degree=15.0,
        betweenness=0.35,
        closeness=0.68,
        eigenvector=0.42,
        pagerank=0.08,
    )


@pytest.fixture
def sample_graph_statistics():
    """Sample graph statistics."""
    return GraphStatistics(
        total_entities=1000,
        total_relationships=2500,
        entity_types={"PERSON": 400, "ORGANIZATION": 600},
        relationship_types={"WORKS_AT": 1500, "KNOWS": 1000},
        avg_degree=5.0,
        density=0.0025,
        communities=50,
    )


@pytest.fixture
def sample_recommendations():
    """Sample recommendations."""
    return [
        Recommendation(
            entity=GraphEntity(
                id="entity_2",
                name="Jane Doe",
                type="PERSON",
                description="Data scientist",
                confidence=0.95,
            ),
            score=0.85,
            reason="similar_community",
        )
    ]


class TestGraphAnalyticsAPI:
    """Test graph analytics API endpoints."""

    @patch("src.api.graph_analytics.get_analytics_engine")
    def test_get_entity_centrality_success(
        self, mock_get_engine, client, sample_centrality_metrics
    ):
        """Test successful centrality calculation."""
        mock_engine = AsyncMock()
        mock_engine.calculate_centrality = AsyncMock(return_value=sample_centrality_metrics)
        mock_get_engine.return_value = mock_engine

        response = client.get("/api/v1/graph/analytics/centrality/entity_1?metric=degree")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "entity_1"
        assert data["degree"] == 15.0

    @patch("src.api.graph_analytics.get_analytics_engine")
    def test_get_pagerank_scores_success(self, mock_get_engine, client):
        """Test successful PageRank calculation."""
        mock_engine = AsyncMock()
        mock_engine.calculate_pagerank = AsyncMock(
            return_value=[
                {"entity_id": "entity_1", "score": 0.15},
                {"entity_id": "entity_2", "score": 0.12},
            ]
        )
        mock_get_engine.return_value = mock_engine

        response = client.get("/api/v1/graph/analytics/pagerank?top_k=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["entity_id"] == "entity_1"

    @patch("src.api.graph_analytics.get_analytics_engine")
    def test_get_influential_entities_success(self, mock_get_engine, client):
        """Test successful influential entity detection."""
        mock_engine = AsyncMock()
        mock_engine.find_influential_entities = AsyncMock(
            return_value=[{"entity_id": "entity_1", "score": 0.2}]
        )
        mock_get_engine.return_value = mock_engine

        response = client.get("/api/v1/graph/analytics/influential?top_k=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @patch("src.api.graph_analytics.get_analytics_engine")
    def test_detect_knowledge_gaps_success(self, mock_get_engine, client):
        """Test successful knowledge gap detection."""
        mock_engine = AsyncMock()
        mock_engine.detect_knowledge_gaps = AsyncMock(
            return_value={
                "orphan_entities": [{"entity_id": "orphan_1", "name": "Orphan"}],
                "sparse_entities": [{"entity_id": "sparse_1", "name": "Sparse", "degree": 1}],
                "isolated_components": 5,
            }
        )
        mock_get_engine.return_value = mock_engine

        response = client.get("/api/v1/graph/analytics/gaps")

        assert response.status_code == 200
        data = response.json()
        assert "orphan_entities" in data
        assert "sparse_entities" in data
        assert "isolated_components" in data

    @patch("src.api.graph_analytics.get_recommendation_engine")
    def test_get_entity_recommendations_success(
        self, mock_get_engine, client, sample_recommendations
    ):
        """Test successful entity recommendations."""
        mock_engine = AsyncMock()
        mock_engine.recommend_similar_entities = AsyncMock(return_value=sample_recommendations)
        mock_get_engine.return_value = mock_engine

        response = client.get(
            "/api/v1/graph/analytics/recommendations/entity_1?method=collaborative&top_k=5"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["entity"]["id"] == "entity_2"

    @patch("src.api.graph_analytics.get_analytics_engine")
    def test_get_graph_statistics_success(self, mock_get_engine, client, sample_graph_statistics):
        """Test successful graph statistics calculation."""
        mock_engine = AsyncMock()
        mock_engine.get_graph_statistics = AsyncMock(return_value=sample_graph_statistics)
        mock_get_engine.return_value = mock_engine

        response = client.get("/api/v1/graph/analytics/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_entities"] == 1000
        assert data["total_relationships"] == 2500

    @patch("src.api.graph_analytics.get_analytics_engine")
    def test_get_centrality_database_error(self, mock_get_engine, client):
        """Test centrality calculation with database error."""
        from src.core.exceptions import DatabaseConnectionError

        mock_engine = AsyncMock()
        mock_engine.calculate_centrality = AsyncMock(
            side_effect=DatabaseConnectionError(database="Neo4j", reason="Connection failed")
        )
        mock_get_engine.return_value = mock_engine

        response = client.get("/api/v1/graph/analytics/centrality/entity_1")

        assert response.status_code == 503

    @patch("src.api.graph_analytics.get_analytics_engine")
    def test_get_pagerank_generic_error(self, mock_get_engine, client):
        """Test PageRank calculation with generic error."""
        mock_engine = AsyncMock()
        mock_engine.calculate_pagerank = AsyncMock(side_effect=Exception("Unexpected error"))
        mock_get_engine.return_value = mock_engine

        response = client.get("/api/v1/graph/analytics/pagerank")

        assert response.status_code == 500

    def test_get_centrality_invalid_metric(self, client):
        """Test centrality with invalid metric parameter."""
        response = client.get("/api/v1/graph/analytics/centrality/entity_1?metric=invalid")

        assert response.status_code == 422  # Validation error

    def test_get_recommendations_invalid_method(self, client):
        """Test recommendations with invalid method parameter."""
        response = client.get("/api/v1/graph/analytics/recommendations/entity_1?method=invalid")

        assert response.status_code == 422  # Validation error
