"""Tests for Graph Analytics Engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import networkx as nx

from src.components.graph_rag.analytics_engine import (
    GraphAnalyticsEngine,
    get_analytics_engine,
)
from src.core.exceptions import DatabaseConnectionError
from src.core.models import CentralityMetrics, GraphStatistics


@pytest.fixture
def mock_neo4j_client():
    """Create mock Neo4j client."""
    client = MagicMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def engine(mock_neo4j_client):
    """Create GraphAnalyticsEngine instance."""
    return GraphAnalyticsEngine(neo4j_client=mock_neo4j_client)


@pytest.fixture
def sample_graph():
    """Create sample NetworkX graph."""
    G = nx.DiGraph()
    G.add_edges_from(
        [
            ("entity_1", "entity_2"),
            ("entity_2", "entity_3"),
            ("entity_3", "entity_1"),
        ]
    )
    return G


class TestGraphAnalyticsEngine:
    """Test GraphAnalyticsEngine class."""

    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine is not None
        assert engine.use_gds is True
        assert engine.pagerank_iterations == 20

    @pytest.mark.asyncio
    async def test_check_gds_availability_success(self, engine, mock_neo4j_client):
        """Test GDS availability check when available."""
        mock_neo4j_client.execute_query.return_value = [{"version": "2.5.0"}]
        result = await engine._check_gds_availability()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_gds_availability_failure(self, engine, mock_neo4j_client):
        """Test GDS availability check when not available."""
        mock_neo4j_client.execute_query.side_effect = Exception("GDS not installed")
        result = await engine._check_gds_availability()
        assert result is False

    @pytest.mark.asyncio
    async def test_calculate_degree_centrality(self, engine, mock_neo4j_client):
        """Test degree centrality calculation."""
        mock_neo4j_client.execute_query.return_value = [{"degree": 5}]
        degree = await engine._calculate_degree_centrality("entity_1")
        assert degree == 5.0

    @pytest.mark.asyncio
    async def test_calculate_centrality_degree(self, engine, mock_neo4j_client):
        """Test calculate_centrality with degree metric."""
        mock_neo4j_client.execute_query.return_value = [{"degree": 10}]
        metrics = await engine.calculate_centrality("entity_1", "degree")
        assert isinstance(metrics, CentralityMetrics)
        assert metrics.entity_id == "entity_1"
        assert metrics.degree == 10.0

    @pytest.mark.asyncio
    async def test_calculate_centrality_caching(self, engine, mock_neo4j_client):
        """Test that centrality results are cached."""
        mock_neo4j_client.execute_query.return_value = [{"degree": 10}]

        # First call - makes 3 queries: degree + pagerank (2 queries)
        metrics1 = await engine.calculate_centrality("entity_1", "degree")
        first_call_count = mock_neo4j_client.execute_query.call_count

        # Second call (should use cache)
        metrics2 = await engine.calculate_centrality("entity_1", "degree")

        assert metrics1 == metrics2
        # Second call should not make any new queries (cache hit)
        assert mock_neo4j_client.execute_query.call_count == first_call_count

    @pytest.mark.asyncio
    async def test_calculate_pagerank_networkx(self, engine, mock_neo4j_client):
        """Test PageRank calculation using NetworkX."""
        engine.use_gds = False
        mock_neo4j_client.execute_query.return_value = [
            {"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"},
            {"source": "entity_2", "target": "entity_3", "rel_type": "KNOWS"},
        ]

        scores = await engine.calculate_pagerank()
        assert isinstance(scores, list)
        assert len(scores) > 0

    @pytest.mark.asyncio
    async def test_calculate_pagerank_specific_entities(self, engine, mock_neo4j_client):
        """Test PageRank for specific entity IDs."""
        engine.use_gds = False
        mock_neo4j_client.execute_query.return_value = [
            {"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"},
        ]

        scores = await engine.calculate_pagerank(["entity_1", "entity_2"])
        assert len(scores) == 2

    @pytest.mark.asyncio
    async def test_calculate_pagerank_caching(self, engine, mock_neo4j_client):
        """Test that PageRank results are cached."""
        engine.use_gds = False
        mock_neo4j_client.execute_query.return_value = [
            {"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"},
        ]

        scores1 = await engine.calculate_pagerank()
        scores2 = await engine.calculate_pagerank()

        assert scores1 == scores2

    @pytest.mark.asyncio
    async def test_find_influential_entities(self, engine, mock_neo4j_client):
        """Test finding influential entities."""
        engine.use_gds = False
        mock_neo4j_client.execute_query.return_value = [
            {"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"},
        ]

        entities = await engine.find_influential_entities(top_k=5)
        assert isinstance(entities, list)
        assert len(entities) <= 5

    @pytest.mark.asyncio
    async def test_detect_knowledge_gaps(self, engine, mock_neo4j_client):
        """Test knowledge gap detection."""
        mock_neo4j_client.execute_query.side_effect = [
            [{"entity_id": "orphan_1", "name": "Orphan"}],  # Orphans
            [{"entity_id": "sparse_1", "name": "Sparse", "degree": 1}],  # Sparse
            [{"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"}],  # For NetworkX
        ]

        gaps = await engine.detect_knowledge_gaps()
        assert "orphan_entities" in gaps
        assert "sparse_entities" in gaps
        assert "isolated_components" in gaps

    @pytest.mark.asyncio
    async def test_detect_knowledge_gaps_caching(self, engine, mock_neo4j_client):
        """Test that knowledge gaps are cached."""
        mock_neo4j_client.execute_query.side_effect = [
            [{"entity_id": "orphan_1", "name": "Orphan"}],
            [{"entity_id": "sparse_1", "name": "Sparse", "degree": 1}],
            [{"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"}],
        ]

        gaps1 = await engine.detect_knowledge_gaps()
        gaps2 = await engine.detect_knowledge_gaps()

        assert gaps1 == gaps2

    @pytest.mark.asyncio
    async def test_get_graph_statistics(self, engine, mock_neo4j_client):
        """Test graph statistics calculation."""
        mock_neo4j_client.execute_query.side_effect = [
            [{"entities": 1000, "relationships": 2500}],  # Counts
            [
                {"type": "PERSON", "count": 400},
                {"type": "ORGANIZATION", "count": 600},
            ],  # Entity types
            [{"type": "WORKS_AT", "count": 1500}, {"type": "KNOWS", "count": 1000}],  # Rel types
            [{"communities": 50}],  # Communities
        ]

        stats = await engine.get_graph_statistics()
        assert isinstance(stats, GraphStatistics)
        assert stats.total_entities == 1000
        assert stats.total_relationships == 2500
        assert "PERSON" in stats.entity_types
        assert "WORKS_AT" in stats.relationship_types

    @pytest.mark.asyncio
    async def test_get_graph_statistics_caching(self, engine, mock_neo4j_client):
        """Test that graph statistics are cached."""
        mock_neo4j_client.execute_query.side_effect = [
            [{"entities": 1000, "relationships": 2500}],
            [{"type": "PERSON", "count": 400}],
            [{"type": "WORKS_AT", "count": 1500}],
            [{"communities": 50}],
        ]

        stats1 = await engine.get_graph_statistics()
        stats2 = await engine.get_graph_statistics()

        assert stats1 == stats2

    @pytest.mark.asyncio
    async def test_build_networkx_graph(self, engine, mock_neo4j_client):
        """Test NetworkX graph construction."""
        mock_neo4j_client.execute_query.return_value = [
            {"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"},
            {"source": "entity_2", "target": "entity_3", "rel_type": "KNOWS"},
        ]

        G = await engine._build_networkx_graph()
        assert isinstance(G, nx.DiGraph)
        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 2

    @pytest.mark.asyncio
    async def test_build_networkx_graph_caching(self, engine, mock_neo4j_client):
        """Test that NetworkX graph is cached."""
        mock_neo4j_client.execute_query.return_value = [
            {"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"},
        ]

        G1 = await engine._build_networkx_graph()
        G2 = await engine._build_networkx_graph()

        assert G1 is G2

    @pytest.mark.asyncio
    async def test_calculate_betweenness_centrality_networkx(self, engine, mock_neo4j_client):
        """Test betweenness centrality using NetworkX."""
        engine.use_gds = False
        mock_neo4j_client.execute_query.return_value = [
            {"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"},
            {"source": "entity_2", "target": "entity_3", "rel_type": "KNOWS"},
        ]

        betweenness = await engine._calculate_betweenness_centrality("entity_2")
        assert isinstance(betweenness, float)
        assert 0.0 <= betweenness <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_closeness_centrality(self, engine, mock_neo4j_client):
        """Test closeness centrality calculation."""
        mock_neo4j_client.execute_query.return_value = [
            {"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"},
            {"source": "entity_2", "target": "entity_3", "rel_type": "KNOWS"},
        ]

        closeness = await engine._calculate_closeness_centrality("entity_1")
        assert isinstance(closeness, float)
        assert 0.0 <= closeness <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_eigenvector_centrality(self, engine, mock_neo4j_client):
        """Test eigenvector centrality calculation."""
        mock_neo4j_client.execute_query.return_value = [
            {"source": "entity_1", "target": "entity_2", "rel_type": "KNOWS"},
            {"source": "entity_2", "target": "entity_3", "rel_type": "KNOWS"},
            {"source": "entity_3", "target": "entity_1", "rel_type": "KNOWS"},
        ]

        eigenvector = await engine._calculate_eigenvector_centrality("entity_1")
        assert isinstance(eigenvector, float)
        assert 0.0 <= eigenvector <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_centrality_database_error(self, engine, mock_neo4j_client):
        """Test centrality calculation with database error."""
        mock_neo4j_client.execute_query.side_effect = Exception("Connection failed")

        with pytest.raises(DatabaseConnectionError):
            await engine.calculate_centrality("entity_1")

    @pytest.mark.asyncio
    async def test_calculate_pagerank_database_error(self, engine, mock_neo4j_client):
        """Test PageRank calculation with database error."""
        mock_neo4j_client.execute_query.side_effect = Exception("Connection failed")

        with pytest.raises(DatabaseConnectionError):
            await engine.calculate_pagerank()

    @pytest.mark.asyncio
    async def test_get_cached_with_expired_cache(self, engine):
        """Test cache retrieval with expired entry."""
        import time

        engine._cache["test_key"] = (time.time() - 1000, "old_value")
        engine.cache_ttl = 500

        result = engine._get_cached("test_key")
        assert result is None

    def test_get_analytics_engine_singleton(self):
        """Test singleton pattern for get_analytics_engine."""
        engine1 = get_analytics_engine()
        engine2 = get_analytics_engine()
        assert engine1 is engine2
