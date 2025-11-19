"""Unit tests for CommunitySearch.

Tests community-filtered search and related community discovery.

Sprint 6.3: Feature - Community Detection & Clustering
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.components.graph_rag.community_search import CommunitySearch
from src.core.models import Community, CommunitySearchResult, GraphEntity


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_aegis_llm_proxy():
    """Mock AegisLLMProxy."""
    proxy = AsyncMock()
    return proxy


@pytest.fixture
def search(mock_neo4j_client, mock_aegis_llm_proxy):
    """Create CommunitySearch instance with mocked clients."""
    from unittest.mock import patch

    # Mock get_aegis_llm_proxy to return our mock
    with patch("src.components.graph_rag.dual_level_search.get_aegis_llm_proxy") as mock_get_proxy:
        mock_get_proxy.return_value = mock_aegis_llm_proxy
        search_instance = CommunitySearch(neo4j_client=mock_neo4j_client)
        # Store mock proxy for access in tests
        search_instance._mock_proxy = mock_aegis_llm_proxy
        yield search_instance


class TestCommunitySearchInit:
    """Tests for CommunitySearch initialization."""

    def test_init(self, mock_neo4j_client):
        """Test initialization."""
        search = CommunitySearch(neo4j_client=mock_neo4j_client)
        assert search.neo4j_client == mock_neo4j_client


class TestSearchByCommunity:
    """Tests for community-filtered search."""

    @pytest.mark.asyncio
    async def test_search_all_communities(self, search, mock_neo4j_client):
        """Test search across all communities."""
        from src.components.llm_proxy.models import LLMResponse

        mock_neo4j_client.execute_read.return_value = [
            {
                "id": "e1",
                "name": "Neural Networks",
                "type": "CONCEPT",
                "description": "Deep learning",
                "properties": {},
                "source_document": None,
                "confidence": 0.95,
                "community_id": "comm_1",
                "community_label": "Machine Learning",
            },
            {
                "id": "e2",
                "name": "Transformers",
                "type": "CONCEPT",
                "description": "Attention mechanism",
                "properties": {},
                "source_document": None,
                "confidence": 0.93,
                "community_id": "comm_1",
                "community_label": "Machine Learning",
            },
        ]

        # Mock proxy.generate to return LLMResponse
        search._mock_proxy.generate.return_value = LLMResponse(
            content="Test answer",
            provider="mock",
            model="mock-model",
            tokens_used=50,
            cost_usd=0.0,
            latency_ms=100,
        )

        result = await search.search_by_community(query="neural networks", top_k=5)

        assert isinstance(result, CommunitySearchResult)
        assert len(result.entities) == 2
        assert len(result.communities) == 1
        assert result.communities[0].id == "comm_1"
        assert result.answer == "Test answer"

    @pytest.mark.asyncio
    async def test_search_filtered_communities(self, search, mock_neo4j_client):
        """Test search filtered by specific communities."""
        from src.components.llm_proxy.models import LLMResponse

        mock_neo4j_client.execute_read.return_value = [
            {
                "id": "e1",
                "name": "Entity 1",
                "type": "CONCEPT",
                "description": "Test",
                "properties": {},
                "source_document": None,
                "confidence": 1.0,
                "community_id": "comm_1",
                "community_label": "Community 1",
            },
        ]

        # Mock proxy.generate to return LLMResponse
        search._mock_proxy.generate.return_value = LLMResponse(
            content="Test answer",
            provider="mock",
            model="mock-model",
            tokens_used=50,
            cost_usd=0.0,
            latency_ms=100,
        )

        result = await search.search_by_community(
            query="test",
            community_ids=["comm_1"],
            top_k=5,
        )

        assert result.metadata["filtered_by_communities"] is True
        assert len(result.entities) == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, search, mock_neo4j_client):
        """Test search with no results."""
        from src.components.llm_proxy.models import LLMResponse

        mock_neo4j_client.execute_read.return_value = []

        # Mock proxy.generate to return LLMResponse
        search._mock_proxy.generate.return_value = LLMResponse(
            content="No results found",
            provider="mock",
            model="mock-model",
            tokens_used=50,
            cost_usd=0.0,
            latency_ms=100,
        )

        result = await search.search_by_community(query="nonexistent", top_k=5)

        assert len(result.entities) == 0
        assert len(result.communities) == 0

    @pytest.mark.asyncio
    async def test_search_multiple_communities(self, search, mock_neo4j_client):
        """Test search returning entities from multiple communities."""
        from src.components.llm_proxy.models import LLMResponse

        mock_neo4j_client.execute_read.return_value = [
            {
                "id": "e1",
                "name": "Entity 1",
                "type": "CONCEPT",
                "description": "Test",
                "properties": {},
                "source_document": None,
                "confidence": 1.0,
                "community_id": "comm_1",
                "community_label": "Community 1",
            },
            {
                "id": "e2",
                "name": "Entity 2",
                "type": "CONCEPT",
                "description": "Test",
                "properties": {},
                "source_document": None,
                "confidence": 1.0,
                "community_id": "comm_2",
                "community_label": "Community 2",
            },
        ]

        # Mock proxy.generate to return LLMResponse
        search._mock_proxy.generate.return_value = LLMResponse(
            content="Test answer",
            provider="mock",
            model="mock-model",
            tokens_used=50,
            cost_usd=0.0,
            latency_ms=100,
        )

        result = await search.search_by_community(query="test", top_k=5)

        assert len(result.communities) == 2
        assert result.communities[0].id == "comm_1"
        assert result.communities[1].id == "comm_2"


class TestFindRelatedCommunities:
    """Tests for finding related communities."""

    @pytest.mark.asyncio
    async def test_find_related_success(self, search, mock_neo4j_client):
        """Test finding related communities."""
        mock_neo4j_client.execute_read.return_value = [
            {
                "related_community_id": "comm_2",
                "label": "Related Community",
                "entity_ids": ["e1", "e2", "e3"],
                "size": 3,
            },
            {
                "related_community_id": "comm_3",
                "label": "Another Community",
                "entity_ids": ["e4", "e5"],
                "size": 2,
            },
        ]

        communities = await search.find_related_communities("comm_1", top_k=5)

        assert len(communities) == 2
        assert all(isinstance(c, Community) for c in communities)
        assert communities[0].id == "comm_2"
        assert communities[1].id == "comm_3"

    @pytest.mark.asyncio
    async def test_find_related_no_results(self, search, mock_neo4j_client):
        """Test finding related communities with no results."""
        mock_neo4j_client.execute_read.return_value = []

        communities = await search.find_related_communities("comm_1", top_k=5)

        assert communities == []

    @pytest.mark.asyncio
    async def test_find_related_error(self, search, mock_neo4j_client):
        """Test error handling when finding related communities."""
        mock_neo4j_client.execute_read.side_effect = Exception("Query failed")

        communities = await search.find_related_communities("comm_1", top_k=5)

        assert communities == []

    @pytest.mark.asyncio
    async def test_find_related_custom_top_k(self, search, mock_neo4j_client):
        """Test finding related communities with custom top_k."""
        mock_neo4j_client.execute_read.return_value = [
            {
                "related_community_id": f"comm_{i}",
                "label": f"Community {i}",
                "entity_ids": ["e1"],
                "size": 1,
            }
            for i in range(3)
        ]

        communities = await search.find_related_communities("comm_1", top_k=3)

        assert len(communities) <= 3


class TestGetCommunityStatistics:
    """Tests for community statistics."""

    @pytest.mark.asyncio
    async def test_get_statistics_success(self, search, mock_neo4j_client):
        """Test getting community statistics."""
        mock_neo4j_client.execute_read.return_value = [
            {
                "community_id": "comm_1",
                "label": "Test Community",
                "size": 5,
                "types": ["CONCEPT", "CONCEPT", "PERSON", "PERSON", "ORGANIZATION"],
                "internal_edges": 8,
            }
        ]

        stats = await search.get_community_statistics("comm_1")

        assert stats["community_id"] == "comm_1"
        assert stats["label"] == "Test Community"
        assert stats["size"] == 5
        assert stats["internal_edges"] == 8
        assert "density" in stats
        assert "entity_types" in stats
        assert stats["entity_types"]["CONCEPT"] == 2
        assert stats["entity_types"]["PERSON"] == 2

    @pytest.mark.asyncio
    async def test_get_statistics_not_found(self, search, mock_neo4j_client):
        """Test getting statistics for nonexistent community."""
        mock_neo4j_client.execute_read.return_value = []

        stats = await search.get_community_statistics("nonexistent")

        assert "error" in stats
        assert stats["community_id"] == "nonexistent"

    @pytest.mark.asyncio
    async def test_get_statistics_density_calculation(self, search, mock_neo4j_client):
        """Test density calculation in statistics."""
        # Community with 4 nodes, 3 edges
        # Max edges = 4 * 3 / 2 = 6
        # Density = 3 / 6 = 0.5
        mock_neo4j_client.execute_read.return_value = [
            {
                "community_id": "comm_1",
                "label": "Test",
                "size": 4,
                "types": ["CONCEPT"] * 4,
                "internal_edges": 3,
            }
        ]

        stats = await search.get_community_statistics("comm_1")

        assert stats["density"] == 0.5

    @pytest.mark.asyncio
    async def test_get_statistics_single_node(self, search, mock_neo4j_client):
        """Test statistics for single-node community."""
        mock_neo4j_client.execute_read.return_value = [
            {
                "community_id": "comm_1",
                "label": "Single Node",
                "size": 1,
                "types": ["CONCEPT"],
                "internal_edges": 0,
            }
        ]

        stats = await search.get_community_statistics("comm_1")

        assert stats["size"] == 1
        assert stats["density"] == 0.0

    @pytest.mark.asyncio
    async def test_get_statistics_error(self, search, mock_neo4j_client):
        """Test error handling when getting statistics."""
        mock_neo4j_client.execute_read.side_effect = Exception("Query failed")

        stats = await search.get_community_statistics("comm_1")

        assert "error" in stats
        assert "Query failed" in stats["error"]


class TestInheritedFunctionality:
    """Tests for inherited DualLevelSearch functionality."""

    @pytest.mark.asyncio
    async def test_inherits_dual_level_search(self, search):
        """Test that CommunitySearch inherits from DualLevelSearch."""
        from src.components.graph_rag.dual_level_search import DualLevelSearch

        assert isinstance(search, DualLevelSearch)
        assert hasattr(search, "local_search")
        assert hasattr(search, "global_search")
        assert hasattr(search, "hybrid_search")

    @pytest.mark.asyncio
    async def test_can_use_local_search(self, search, mock_neo4j_client):
        """Test that local_search is available."""
        mock_neo4j_client.execute_read.return_value = []

        entities = await search.local_search("test query", top_k=5)

        assert isinstance(entities, list)
