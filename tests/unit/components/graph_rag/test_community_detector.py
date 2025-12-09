"""Unit tests for CommunityDetector.

Tests community detection algorithms (Leiden, Louvain) using both
Neo4j GDS and NetworkX fallback.

Sprint 6.3: Feature - Community Detection & Clustering
"""

from unittest.mock import AsyncMock

import pytest
from neo4j.exceptions import ClientError

from src.components.graph_rag.community_detector import CommunityDetector
from src.core.models import Community


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = AsyncMock()
    return client


@pytest.fixture
def detector(mock_neo4j_client):
    """Create CommunityDetector instance with mocked client."""
    return CommunityDetector(
        neo4j_client=mock_neo4j_client,
        algorithm="leiden",
        resolution=1.0,
        min_size=3,
        use_gds=True,
    )


class TestCommunityDetectorInit:
    """Tests for CommunityDetector initialization."""

    def test_init_default_settings(self, mock_neo4j_client):
        """Test initialization with default settings."""
        detector = CommunityDetector(neo4j_client=mock_neo4j_client)
        assert detector.algorithm == "leiden"
        assert detector.resolution == 1.0
        assert detector.min_size == 3

    def test_init_custom_settings(self, mock_neo4j_client):
        """Test initialization with custom settings."""
        detector = CommunityDetector(
            neo4j_client=mock_neo4j_client,
            algorithm="louvain",
            resolution=0.5,
            min_size=5,
            use_gds=False,
        )
        assert detector.algorithm == "louvain"
        assert detector.resolution == 0.5
        assert detector.min_size == 5
        assert detector.use_gds is False


class TestGDSAvailability:
    """Tests for GDS availability checking."""

    @pytest.mark.asyncio
    async def test_gds_available(self, detector, mock_neo4j_client):
        """Test when GDS is available."""
        mock_neo4j_client.execute_read.return_value = [{"gdsVersion": "2.5.0"}]

        available = await detector._check_gds_availability()

        assert available is True
        assert detector._gds_available is True
        mock_neo4j_client.execute_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_gds_not_available(self, detector, mock_neo4j_client):
        """Test when GDS is not available."""
        mock_neo4j_client.execute_read.side_effect = ClientError("GDS not found")

        available = await detector._check_gds_availability()

        assert available is False
        assert detector._gds_available is False

    @pytest.mark.asyncio
    async def test_gds_availability_cached(self, detector):
        """Test that GDS availability is cached."""
        detector._gds_available = True

        available = await detector._check_gds_availability()

        assert available is True
        # Should not call Neo4j since it's cached


class TestDetectCommunities:
    """Tests for detect_communities method."""

    @pytest.mark.asyncio
    async def test_detect_with_gds(self, detector, mock_neo4j_client):
        """Test community detection using GDS."""
        # Mock GDS availability
        detector._gds_available = True

        # Mock GDS calls
        mock_neo4j_client.execute_query.return_value = None  # projection creation
        mock_neo4j_client.execute_read.return_value = [
            {"entity_id": "e1", "communityId": 1},
            {"entity_id": "e2", "communityId": 1},
            {"entity_id": "e3", "communityId": 1},
            {"entity_id": "e4", "communityId": 2},
            {"entity_id": "e5", "communityId": 2},
        ]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": 5}]

        communities = await detector.detect_communities()

        assert len(communities) >= 1
        assert all(isinstance(c, Community) for c in communities)
        assert all(c.size >= detector.min_size for c in communities)

    @pytest.mark.asyncio
    async def test_detect_with_networkx(self, detector, mock_neo4j_client):
        """Test community detection using NetworkX fallback."""
        # Mock GDS not available
        detector._gds_available = False

        # Mock NetworkX graph data
        mock_neo4j_client.execute_read.side_effect = [
            # Entities
            [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}, {"id": "e4"}, {"id": "e5"}],
            # Relationships
            [
                {"source": "e1", "target": "e2"},
                {"source": "e2", "target": "e3"},
                {"source": "e4", "target": "e5"},
            ],
        ]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": 5}]

        communities = await detector.detect_communities()

        assert isinstance(communities, list)
        assert all(isinstance(c, Community) for c in communities)

    @pytest.mark.asyncio
    async def test_detect_with_louvain(self, detector, mock_neo4j_client):
        """Test detection with Louvain algorithm."""
        detector._gds_available = True
        detector.algorithm = "louvain"

        mock_neo4j_client.execute_query.return_value = None
        mock_neo4j_client.execute_read.return_value = [
            {"entity_id": "e1", "communityId": 1},
            {"entity_id": "e2", "communityId": 1},
            {"entity_id": "e3", "communityId": 1},
        ]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": 3}]

        communities = await detector.detect_communities(algorithm="louvain")

        assert len(communities) >= 1
        assert communities[0].metadata["algorithm"] == "louvain"

    @pytest.mark.asyncio
    async def test_detect_filters_by_min_size(self, detector, mock_neo4j_client):
        """Test that communities are filtered by minimum size."""
        detector._gds_available = True
        detector.min_size = 3

        mock_neo4j_client.execute_query.return_value = None
        mock_neo4j_client.execute_read.return_value = [
            {"entity_id": "e1", "communityId": 1},
            {"entity_id": "e2", "communityId": 1},  # Size 2 - should be filtered
            {"entity_id": "e3", "communityId": 2},
            {"entity_id": "e4", "communityId": 2},
            {"entity_id": "e5", "communityId": 2},  # Size 3 - should be kept
        ]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": 5}]

        communities = await detector.detect_communities()

        # Should only have communities with size >= 3
        assert all(c.size >= 3 for c in communities)

    @pytest.mark.asyncio
    async def test_detect_with_custom_resolution(self, detector, mock_neo4j_client):
        """Test detection with custom resolution parameter."""
        detector._gds_available = True

        mock_neo4j_client.execute_query.return_value = None
        mock_neo4j_client.execute_read.return_value = [
            {"entity_id": "e1", "communityId": 1},
            {"entity_id": "e2", "communityId": 1},
            {"entity_id": "e3", "communityId": 1},
        ]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": 3}]

        communities = await detector.detect_communities(resolution=0.5)

        assert len(communities) >= 1
        assert communities[0].metadata["resolution"] == 0.5


class TestStoreCommunities:
    """Tests for community storage."""

    @pytest.mark.asyncio
    async def test_store_communities(self, detector, mock_neo4j_client):
        """Test storing community IDs on entities."""
        communities = [
            Community(
                id="community_1",
                label="Test Community",
                entity_ids=["e1", "e2", "e3"],
                size=3,
            ),
        ]

        mock_neo4j_client.execute_write.return_value = [{"updated_count": 3}]

        await detector._store_communities(communities)

        mock_neo4j_client.execute_write.assert_called()
        call_args = mock_neo4j_client.execute_write.call_args[0]
        assert "SET e.community_id" in call_args[0]

    @pytest.mark.asyncio
    async def test_store_multiple_communities(self, detector, mock_neo4j_client):
        """Test storing multiple communities."""
        communities = [
            Community(id="comm_1", label="C1", entity_ids=["e1", "e2"], size=2),
            Community(id="comm_2", label="C2", entity_ids=["e3", "e4"], size=2),
        ]

        mock_neo4j_client.execute_write.return_value = [{"updated_count": 2}]

        await detector._store_communities(communities)

        assert mock_neo4j_client.execute_write.call_count == 2


class TestGetCommunity:
    """Tests for get_community method."""

    @pytest.mark.asyncio
    async def test_get_existing_community(self, detector, mock_neo4j_client):
        """Test getting an existing community."""
        mock_neo4j_client.execute_read.return_value = [
            {"entity_id": "e1", "label": "Test Community"},
            {"entity_id": "e2", "label": "Test Community"},
            {"entity_id": "e3", "label": "Test Community"},
        ]

        community = await detector.get_community("community_1")

        assert community is not None
        assert community.id == "community_1"
        assert community.label == "Test Community"
        assert community.size == 3

    @pytest.mark.asyncio
    async def test_get_nonexistent_community(self, detector, mock_neo4j_client):
        """Test getting a community that doesn't exist."""
        mock_neo4j_client.execute_read.return_value = []

        community = await detector.get_community("nonexistent")

        assert community is None


class TestGetEntityCommunity:
    """Tests for get_entity_community method."""

    @pytest.mark.asyncio
    async def test_get_entity_with_community(self, detector, mock_neo4j_client):
        """Test getting community ID for an entity."""
        mock_neo4j_client.execute_read.return_value = [{"community_id": "community_1"}]

        community_id = await detector.get_entity_community("e1")

        assert community_id == "community_1"

    @pytest.mark.asyncio
    async def test_get_entity_without_community(self, detector, mock_neo4j_client):
        """Test entity with no community assigned."""
        mock_neo4j_client.execute_read.return_value = [{"community_id": None}]

        community_id = await detector.get_entity_community("e1")

        assert community_id is None


class TestListCommunities:
    """Tests for list_communities method."""

    @pytest.mark.asyncio
    async def test_list_all_communities(self, detector, mock_neo4j_client):
        """Test listing all communities."""
        mock_neo4j_client.execute_read.return_value = [
            {
                "community_id": "comm_1",
                "label": "Community 1",
                "entity_ids": ["e1", "e2", "e3"],
                "size": 3,
            },
            {
                "community_id": "comm_2",
                "label": "Community 2",
                "entity_ids": ["e4", "e5", "e6", "e7"],
                "size": 4,
            },
        ]

        communities = await detector.list_communities()

        assert len(communities) == 2
        assert all(isinstance(c, Community) for c in communities)
        assert communities[0].size == 3
        assert communities[1].size == 4

    @pytest.mark.asyncio
    async def test_list_with_min_size_filter(self, detector, mock_neo4j_client):
        """Test listing communities with min_size filter."""
        mock_neo4j_client.execute_read.return_value = [
            {
                "community_id": "comm_1",
                "label": "Large Community",
                "entity_ids": ["e1", "e2", "e3", "e4", "e5"],
                "size": 5,
            },
        ]

        communities = await detector.list_communities(min_size=5)

        assert len(communities) == 1
        assert communities[0].size >= 5

    @pytest.mark.asyncio
    async def test_list_empty_graph(self, detector, mock_neo4j_client):
        """Test listing communities in an empty graph."""
        mock_neo4j_client.execute_read.return_value = []

        communities = await detector.list_communities()

        assert communities == []


class TestNetworkXFallback:
    """Tests for NetworkX fallback functionality."""

    @pytest.mark.asyncio
    async def test_networkx_density_calculation(self, detector):
        """Test density calculation for NetworkX communities."""
        import networkx as nx

        G = nx.Graph()
        G.add_edges_from([("e1", "e2"), ("e2", "e3"), ("e1", "e3")])

        density = detector._calculate_density(G, ["e1", "e2", "e3"])

        assert 0.0 <= density <= 1.0

    @pytest.mark.asyncio
    async def test_networkx_empty_community(self, detector):
        """Test density calculation for empty community."""
        import networkx as nx

        G = nx.Graph()
        G.add_node("e1")

        density = detector._calculate_density(G, ["e1"])

        assert density == 0.0


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_detect_with_neo4j_error_fallback(self, detector, mock_neo4j_client):
        """Test fallback to NetworkX when GDS fails."""
        detector._gds_available = True
        # GDS fails, then NetworkX queries succeed
        mock_neo4j_client.execute_query.side_effect = Exception("Neo4j error")
        mock_neo4j_client.execute_read.side_effect = [
            # Entities for NetworkX
            [{"id": "e1"}, {"id": "e2"}],
            # Relationships for NetworkX
            [{"source": "e1", "target": "e2"}],
        ]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": 2}]

        # Should fallback to NetworkX instead of raising
        communities = await detector.detect_communities()
        assert isinstance(communities, list)

    @pytest.mark.asyncio
    async def test_get_community_with_error(self, detector, mock_neo4j_client):
        """Test error handling when getting community."""
        mock_neo4j_client.execute_read.side_effect = Exception("Query failed")

        community = await detector.get_community("comm_1")

        assert community is None
