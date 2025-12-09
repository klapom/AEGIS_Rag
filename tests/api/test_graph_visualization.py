"""Tests for Graph Visualization API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

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


# ============================================================================
# Sprint 29: Tests for New Endpoints
# ============================================================================


class TestQuerySubgraphEndpoint:
    """Tests for POST /api/v1/graph/viz/query-subgraph (Feature 29.2)."""

    @patch("src.api.routers.graph_viz.get_neo4j_client")
    def test_query_subgraph_success(self, mock_get_neo4j, client):
        """Test successful query subgraph extraction."""
        # Mock Neo4j response
        mock_neo4j = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(
            return_value=[
                {
                    "n": {
                        "id": "entity_1",
                        "name": "Transformer",
                        "entity_type": "CONCEPT",
                        "community_id": "comm_1",
                    },
                    "r": None,
                    "m": None,
                }
            ]
        )
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j.get_driver.return_value.session = AsyncMock(return_value=mock_session)
        mock_get_neo4j.return_value = mock_neo4j

        response = client.post(
            "/api/v1/graph/viz/query-subgraph",
            json={"entity_names": ["Transformer", "Attention Mechanism"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    @patch("src.api.routers.graph_viz.get_neo4j_client")
    def test_query_subgraph_empty_entities(self, mock_get_neo4j, client):
        """Test query subgraph with empty entity list."""
        response = client.post("/api/v1/graph/viz/query-subgraph", json={"entity_names": []})

        assert response.status_code == 422  # Validation error

    @patch("src.api.routers.graph_viz.get_neo4j_client")
    def test_query_subgraph_database_error(self, mock_get_neo4j, client):
        """Test query subgraph with database error."""
        mock_neo4j = AsyncMock()
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Database error"))
        mock_neo4j.get_driver.return_value.session = AsyncMock(return_value=mock_session)
        mock_get_neo4j.return_value = mock_neo4j

        response = client.post(
            "/api/v1/graph/viz/query-subgraph",
            json={"entity_names": ["Transformer"]},
        )

        assert response.status_code == 500


class TestGraphStatisticsEndpoint:
    """Tests for GET /api/v1/graph/viz/statistics (Feature 29.4)."""

    @patch("src.api.routers.graph_viz.get_neo4j_client")
    def test_statistics_success(self, mock_get_neo4j, client):
        """Test successful graph statistics retrieval."""
        # Mock Neo4j responses
        mock_neo4j = AsyncMock()
        mock_session = AsyncMock()

        # Mock node count
        mock_node_result = AsyncMock()
        mock_node_result.single = AsyncMock(return_value={"count": 100})

        # Mock edge count
        mock_edge_result = AsyncMock()
        mock_edge_result.single = AsyncMock(return_value={"count": 200})

        # Mock community count
        mock_comm_result = AsyncMock()
        mock_comm_result.single = AsyncMock(return_value={"count": 10})

        # Mock entity type distribution
        mock_type_result = AsyncMock()
        mock_type_result.data = AsyncMock(
            return_value=[
                {"type": "PERSON", "count": 30},
                {"type": "ORGANIZATION", "count": 20},
                {"type": "CONCEPT", "count": 50},
            ]
        )

        # Mock orphaned nodes
        mock_orphan_result = AsyncMock()
        mock_orphan_result.single = AsyncMock(return_value={"count": 5})

        # Setup run to return different results based on query
        async def run_side_effect(query, **kwargs):
            if "MATCH (n:base) RETURN count(n)" in query:
                return mock_node_result
            elif "MATCH ()-[r]->()" in query:
                return mock_edge_result
            elif "count(DISTINCT n.community_id)" in query:
                return mock_comm_result
            elif "n.entity_type as type" in query:
                return mock_type_result
            elif "WHERE NOT (n)--() RETURN count(n)" in query:
                return mock_orphan_result

        mock_session.run = AsyncMock(side_effect=run_side_effect)
        mock_neo4j.get_driver.return_value.session = AsyncMock(return_value=mock_session)
        mock_get_neo4j.return_value = mock_neo4j

        response = client.get("/api/v1/graph/viz/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["node_count"] == 100
        assert data["edge_count"] == 200
        assert data["community_count"] == 10
        assert data["avg_degree"] == 4.0  # (200 * 2) / 100
        assert "entity_type_distribution" in data
        assert data["orphaned_nodes"] == 5
        assert "timestamp" in data

    @patch("src.api.routers.graph_viz.get_neo4j_client")
    def test_statistics_zero_nodes(self, mock_get_neo4j, client):
        """Test statistics with empty graph."""
        mock_neo4j = AsyncMock()
        mock_session = AsyncMock()

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"count": 0})
        mock_result.data = AsyncMock(return_value=[])

        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j.get_driver.return_value.session = AsyncMock(return_value=mock_session)
        mock_get_neo4j.return_value = mock_neo4j

        response = client.get("/api/v1/graph/viz/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["node_count"] == 0
        assert data["avg_degree"] == 0.0


class TestNodeDocumentsEndpoint:
    """Tests for POST /api/v1/graph/viz/node-documents (Feature 29.6)."""

    @patch("src.api.routers.graph_viz.QdrantClient")
    @patch("src.api.routers.graph_viz.UnifiedEmbeddingService")
    def test_node_documents_success(self, mock_embedding_service, mock_qdrant_client, client):
        """Test successful node documents retrieval."""
        # Mock embedding service
        mock_embed_service = AsyncMock()
        mock_embed_service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_embedding_service.return_value = mock_embed_service

        # Mock Qdrant search results
        mock_qdrant = AsyncMock()
        mock_result = AsyncMock()
        mock_result.id = "doc_1"
        mock_result.score = 0.95
        mock_result.payload = {
            "source": "research_paper.pdf",
            "text": "Transformers are neural network architectures...",
            "chunk_id": "chunk_001",
        }
        mock_qdrant.search = AsyncMock(return_value=[mock_result])
        mock_qdrant_client.return_value = mock_qdrant

        response = client.post(
            "/api/v1/graph/viz/node-documents",
            json={"entity_name": "Transformer", "top_k": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_name"] == "Transformer"
        assert len(data["documents"]) == 1
        assert data["documents"][0]["id"] == "doc_1"
        assert data["documents"][0]["similarity"] == 0.95
        assert data["total"] == 1

    @patch("src.api.routers.graph_viz.QdrantClient")
    @patch("src.api.routers.graph_viz.UnifiedEmbeddingService")
    def test_node_documents_empty_results(self, mock_embedding_service, mock_qdrant_client, client):
        """Test node documents with no results."""
        mock_embed_service = AsyncMock()
        mock_embed_service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_embedding_service.return_value = mock_embed_service

        mock_qdrant = AsyncMock()
        mock_qdrant.search = AsyncMock(return_value=[])
        mock_qdrant_client.return_value = mock_qdrant

        response = client.post(
            "/api/v1/graph/viz/node-documents",
            json={"entity_name": "NonexistentEntity", "top_k": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 0
        assert data["total"] == 0

    def test_node_documents_invalid_top_k(self, client):
        """Test node documents with invalid top_k."""
        response = client.post(
            "/api/v1/graph/viz/node-documents",
            json={"entity_name": "Transformer", "top_k": 1000},  # Exceeds limit
        )

        assert response.status_code == 422  # Validation error


class TestCommunityDocumentsEndpoint:
    """Tests for GET /api/v1/graph/viz/communities/{id}/documents (Feature 29.7)."""

    @patch("src.api.routers.graph_viz.QdrantClient")
    @patch("src.api.routers.graph_viz.UnifiedEmbeddingService")
    @patch("src.api.routers.graph_viz.get_neo4j_client")
    def test_community_documents_success(
        self, mock_get_neo4j, mock_embedding_service, mock_qdrant_client, client
    ):
        """Test successful community documents retrieval."""
        # Mock Neo4j entity retrieval
        mock_neo4j = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"entity_names": ["Transformer", "Attention"]})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j.get_driver.return_value.session = AsyncMock(return_value=mock_session)
        mock_get_neo4j.return_value = mock_neo4j

        # Mock embedding service
        mock_embed_service = AsyncMock()
        mock_embed_service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_embedding_service.return_value = mock_embed_service

        # Mock Qdrant search
        mock_qdrant = AsyncMock()
        mock_search_result = AsyncMock()
        mock_search_result.id = "doc_1"
        mock_search_result.payload = {
            "source": "paper.pdf",
            "text": "Transformers use attention mechanisms...",
            "chunk_id": "chunk_001",
        }
        mock_qdrant.search = AsyncMock(return_value=[mock_search_result])
        mock_qdrant_client.return_value = mock_qdrant

        response = client.get("/api/v1/graph/viz/communities/comm_1/documents?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert data["community_id"] == "comm_1"
        assert len(data["documents"]) >= 1
        assert "entities" in data["documents"][0]

    @patch("src.api.routers.graph_viz.get_neo4j_client")
    def test_community_documents_not_found(self, mock_get_neo4j, client):
        """Test community documents with nonexistent community."""
        mock_neo4j = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j.get_driver.return_value.session = AsyncMock(return_value=mock_session)
        mock_get_neo4j.return_value = mock_neo4j

        response = client.get("/api/v1/graph/viz/communities/nonexistent/documents")

        assert response.status_code == 404

    @patch("src.api.routers.graph_viz.QdrantClient")
    @patch("src.api.routers.graph_viz.UnifiedEmbeddingService")
    @patch("src.api.routers.graph_viz.get_neo4j_client")
    def test_community_documents_custom_limit(
        self, mock_get_neo4j, mock_embedding_service, mock_qdrant_client, client
    ):
        """Test community documents with custom limit."""
        # Mock Neo4j
        mock_neo4j = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"entity_names": ["Entity1", "Entity2"]})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j.get_driver.return_value.session = AsyncMock(return_value=mock_session)
        mock_get_neo4j.return_value = mock_neo4j

        # Mock embedding and search
        mock_embed_service = AsyncMock()
        mock_embed_service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_embedding_service.return_value = mock_embed_service

        mock_qdrant = AsyncMock()
        mock_qdrant.search = AsyncMock(return_value=[])
        mock_qdrant_client.return_value = mock_qdrant

        response = client.get("/api/v1/graph/viz/communities/comm_1/documents?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) <= 10
