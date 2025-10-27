"""Tests for Graph Visualization Export Module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.graph_rag.visualization_export import (
    GraphVisualizationExporter,
    get_visualization_exporter,
)
from src.core.exceptions import DatabaseConnectionError


@pytest.fixture
def mock_neo4j_client():
    """Create mock Neo4j client."""
    client = MagicMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def exporter(mock_neo4j_client):
    """Create GraphVisualizationExporter instance."""
    return GraphVisualizationExporter(neo4j_client=mock_neo4j_client)


@pytest.fixture
def sample_nodes():
    """Sample node data."""
    return [
        {
            "id": "entity_1",
            "name": "John Smith",
            "type": "PERSON",
            "description": "Software engineer",
            "properties": {"age": 30},
        },
        {
            "id": "entity_2",
            "name": "Google",
            "type": "ORGANIZATION",
            "description": "Technology company",
            "properties": {},
        },
    ]


@pytest.fixture
def sample_edges():
    """Sample edge data."""
    return [
        {
            "id": 1,
            "source": "entity_1",
            "target": "entity_2",
            "type": "WORKS_AT",
            "properties": {"since": "2020"},
        }
    ]


class TestGraphVisualizationExporter:
    """Test GraphVisualizationExporter class."""

    @pytest.mark.asyncio
    async def test_initialization(self, exporter):
        """Test exporter initialization."""
        assert exporter is not None
        assert exporter.max_nodes == 100
        assert exporter.default_depth == 1
        assert exporter.default_format == "d3"

    @pytest.mark.asyncio
    async def test_export_subgraph_d3_format(
        self, exporter, mock_neo4j_client, sample_nodes, sample_edges
    ):
        """Test export_subgraph with D3.js format."""
        mock_neo4j_client.execute_query.return_value = [
            {"nodes": sample_nodes, "edges": sample_edges}
        ]

        result = await exporter.export_subgraph(["entity_1"], depth=1, format="d3")

        assert "nodes" in result
        assert "links" in result
        assert "metadata" in result
        assert len(result["nodes"]) == 2
        assert len(result["links"]) == 1
        assert result["metadata"]["node_count"] == 2
        assert result["metadata"]["edge_count"] == 1

    @pytest.mark.asyncio
    async def test_export_subgraph_cytoscape_format(
        self, exporter, mock_neo4j_client, sample_nodes, sample_edges
    ):
        """Test export_subgraph with Cytoscape format."""
        mock_neo4j_client.execute_query.return_value = [
            {"nodes": sample_nodes, "edges": sample_edges}
        ]

        result = await exporter.export_subgraph(["entity_1"], depth=1, format="cytoscape")

        assert "elements" in result
        assert "nodes" in result["elements"]
        assert "edges" in result["elements"]
        assert len(result["elements"]["nodes"]) == 2
        assert len(result["elements"]["edges"]) == 1

    @pytest.mark.asyncio
    async def test_export_subgraph_visjs_format(
        self, exporter, mock_neo4j_client, sample_nodes, sample_edges
    ):
        """Test export_subgraph with vis.js format."""
        mock_neo4j_client.execute_query.return_value = [
            {"nodes": sample_nodes, "edges": sample_edges}
        ]

        result = await exporter.export_subgraph(["entity_1"], depth=1, format="visjs")

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    @pytest.mark.asyncio
    async def test_export_subgraph_invalid_format(self, exporter, mock_neo4j_client):
        """Test export_subgraph with invalid format."""
        mock_neo4j_client.execute_query.return_value = [{"nodes": [], "edges": []}]

        with pytest.raises(ValueError, match="Unsupported format"):
            await exporter.export_subgraph(["entity_1"], format="invalid")

    @pytest.mark.asyncio
    async def test_export_subgraph_depth_clamping(
        self, exporter, mock_neo4j_client, sample_nodes, sample_edges
    ):
        """Test depth parameter is clamped to valid range (1-5)."""
        mock_neo4j_client.execute_query.return_value = [
            {"nodes": sample_nodes, "edges": sample_edges}
        ]

        # Test depth < 1
        result1 = await exporter.export_subgraph(["entity_1"], depth=0)
        assert result1["metadata"]["depth"] == 1

        # Test depth > 5
        result2 = await exporter.export_subgraph(["entity_1"], depth=10)
        assert result2["metadata"]["depth"] == 5

    @pytest.mark.asyncio
    async def test_export_subgraph_max_nodes_limit(
        self, exporter, mock_neo4j_client, sample_nodes, sample_edges
    ):
        """Test max_nodes limit is enforced."""
        # Create more nodes than limit
        many_nodes = sample_nodes * 60  # 120 nodes
        mock_neo4j_client.execute_query.return_value = [
            {"nodes": many_nodes, "edges": sample_edges}
        ]

        result = await exporter.export_subgraph(["entity_1"], max_nodes=100)

        assert result["metadata"]["truncated"] is True

    @pytest.mark.asyncio
    async def test_export_for_d3js(self, exporter, sample_nodes, sample_edges):
        """Test D3.js format conversion."""
        result = exporter.export_for_d3js(sample_nodes, sample_edges)

        assert "nodes" in result
        assert "links" in result
        node = result["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "group" in node
        link = result["links"][0]
        assert "source" in link
        assert "target" in link
        assert "value" in link

    @pytest.mark.asyncio
    async def test_export_for_cytoscape(self, exporter, sample_nodes, sample_edges):
        """Test Cytoscape.js format conversion."""
        result = exporter.export_for_cytoscape(sample_nodes, sample_edges)

        assert "elements" in result
        assert "nodes" in result["elements"]
        assert "edges" in result["elements"]
        node = result["elements"]["nodes"][0]
        assert "data" in node
        assert "id" in node["data"]
        edge = result["elements"]["edges"][0]
        assert "data" in edge
        assert "source" in edge["data"]

    @pytest.mark.asyncio
    async def test_export_for_visjs(self, exporter, sample_nodes, sample_edges):
        """Test vis.js format conversion."""
        result = exporter.export_for_visjs(sample_nodes, sample_edges)

        assert "nodes" in result
        assert "edges" in result
        node = result["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "title" in node
        edge = result["edges"][0]
        assert "from" in edge
        assert "to" in edge

    @pytest.mark.asyncio
    async def test_export_subgraph_empty_result(self, exporter, mock_neo4j_client):
        """Test export_subgraph with no data."""
        mock_neo4j_client.execute_query.return_value = []

        result = await exporter.export_subgraph(["nonexistent"])

        assert result["metadata"]["node_count"] == 0
        assert result["metadata"]["edge_count"] == 0

    @pytest.mark.asyncio
    async def test_export_subgraph_database_error(self, exporter, mock_neo4j_client):
        """Test export_subgraph with database error."""
        mock_neo4j_client.execute_query.side_effect = Exception("Connection failed")

        with pytest.raises(DatabaseConnectionError):
            await exporter.export_subgraph(["entity_1"])

    @pytest.mark.asyncio
    async def test_get_visualization_exporter_singleton(self):
        """Test singleton pattern for get_visualization_exporter."""
        exporter1 = get_visualization_exporter()
        exporter2 = get_visualization_exporter()
        assert exporter1 is exporter2

    @pytest.mark.asyncio
    async def test_export_subgraph_multiple_entity_ids(
        self, exporter, mock_neo4j_client, sample_nodes, sample_edges
    ):
        """Test export_subgraph with multiple starting entity IDs."""
        mock_neo4j_client.execute_query.return_value = [
            {"nodes": sample_nodes, "edges": sample_edges}
        ]

        result = await exporter.export_subgraph(["entity_1", "entity_2"], depth=2)

        assert result["metadata"]["node_count"] == 2
        mock_neo4j_client.execute_query.assert_called_once()
