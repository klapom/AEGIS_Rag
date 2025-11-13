"""Unit tests for CommunityLabeler.

Tests LLM-based community labeling functionality.

Sprint 6.3: Feature - Community Detection & Clustering
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.community_labeler import CommunityLabeler
from src.core.models import Community, GraphEntity


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_llm_proxy():
    """Mock AegisLLMProxy."""
    proxy = AsyncMock()
    return proxy


@pytest.fixture
def labeler(mock_neo4j_client, mock_llm_proxy):
    """Create CommunityLabeler instance with mocked clients."""
    with patch("src.components.graph_rag.community_labeler.get_aegis_llm_proxy") as mock_get_proxy:
        mock_get_proxy.return_value = mock_llm_proxy
        labeler = CommunityLabeler(
            neo4j_client=mock_neo4j_client,
            llm_model="llama3.2:3b",
            enabled=True,
        )
        labeler.proxy = mock_llm_proxy  # Ensure proxy is set
        return labeler


@pytest.fixture
def sample_entities():
    """Sample entities for testing."""
    return [
        GraphEntity(
            id="e1",
            name="Neural Networks",
            type="CONCEPT",
            description="Deep learning architecture",
            properties={},
            confidence=0.95,
        ),
        GraphEntity(
            id="e2",
            name="Machine Learning",
            type="CONCEPT",
            description="AI and ML research",
            properties={},
            confidence=0.93,
        ),
        GraphEntity(
            id="e3",
            name="Deep Learning",
            type="CONCEPT",
            description="Advanced neural networks",
            properties={},
            confidence=0.92,
        ),
    ]


@pytest.fixture
def sample_community(sample_entities):
    """Sample community for testing."""
    return Community(
        id="community_1",
        label="",
        entity_ids=[e.id for e in sample_entities],
        size=len(sample_entities),
    )


class TestCommunityLabelerInit:
    """Tests for CommunityLabeler initialization."""

    def test_init_default_settings(self, mock_neo4j_client):
        """Test initialization with default settings."""
        labeler = CommunityLabeler(neo4j_client=mock_neo4j_client)
        assert labeler.llm_model == "llama3.2:3b"
        assert labeler.enabled is True

    def test_init_custom_settings(self, mock_neo4j_client):
        """Test initialization with custom settings."""
        labeler = CommunityLabeler(
            neo4j_client=mock_neo4j_client,
            llm_model="llama3.1:8b",
            enabled=False,
        )
        assert labeler.llm_model == "llama3.1:8b"
        assert labeler.enabled is False


class TestFetchCommunityEntities:
    """Tests for fetching community entities."""

    @pytest.mark.asyncio
    async def test_fetch_entities(self, labeler, mock_neo4j_client, sample_community):
        """Test fetching entities for a community."""
        mock_neo4j_client.execute_read.return_value = [
            {
                "id": "e1",
                "name": "Neural Networks",
                "type": "CONCEPT",
                "description": "Deep learning",
                "properties": {},
                "source_document": None,
                "confidence": 0.95,
            },
            {
                "id": "e2",
                "name": "Machine Learning",
                "type": "CONCEPT",
                "description": "AI research",
                "properties": {},
                "source_document": None,
                "confidence": 0.93,
            },
        ]

        entities = await labeler._fetch_community_entities(sample_community)

        assert len(entities) == 2
        assert all(isinstance(e, GraphEntity) for e in entities)
        assert entities[0].name == "Neural Networks"

    @pytest.mark.asyncio
    async def test_fetch_entities_error(self, labeler, mock_neo4j_client, sample_community):
        """Test error handling when fetching entities."""
        mock_neo4j_client.execute_read.side_effect = Exception("Query failed")

        entities = await labeler._fetch_community_entities(sample_community)

        assert entities == []


class TestGenerateLabel:
    """Tests for label generation."""

    @pytest.mark.asyncio
    async def test_generate_label_success(self, labeler, sample_entities):
        """Test successful label generation via AegisLLMProxy."""
        # Mock proxy response
        mock_result = MagicMock()
        mock_result.content = "Machine Learning Research"
        mock_result.provider = "local_ollama"
        mock_result.model = "llama3.2:3b"
        mock_result.cost_usd = 0.0
        mock_result.latency_ms = 50
        labeler.proxy.generate.return_value = mock_result

        label = await labeler.generate_label(sample_entities)

        assert label == "Machine Learning Research"
        labeler.proxy.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_label_with_quotes(self, labeler, sample_entities):
        """Test label generation with quotes in response."""
        mock_result = MagicMock()
        mock_result.content = '"Software Engineering"'
        labeler.proxy.generate.return_value = mock_result

        label = await labeler.generate_label(sample_entities)

        assert label == "Software Engineering"

    @pytest.mark.asyncio
    async def test_generate_label_too_long(self, labeler, sample_entities):
        """Test label truncation when too long."""
        mock_result = MagicMock()
        mock_result.content = "This Is A Very Long Label That Exceeds Five Words"
        labeler.proxy.generate.return_value = mock_result

        label = await labeler.generate_label(sample_entities)

        # Should be truncated to 5 words
        assert len(label.split()) <= 5

    @pytest.mark.asyncio
    async def test_generate_label_too_short(self, labeler, sample_entities):
        """Test label handling when too short."""
        mock_result = MagicMock()
        mock_result.content = "AI"
        labeler.proxy.generate.return_value = mock_result

        label = await labeler.generate_label(sample_entities)

        # Should default to "Unlabeled Community" for single word
        assert label == "Unlabeled Community"

    @pytest.mark.asyncio
    async def test_generate_label_empty_entities(self, labeler):
        """Test label generation with empty entities list."""
        label = await labeler.generate_label([])

        assert label == "Empty Community"

    @pytest.mark.asyncio
    async def test_generate_label_disabled(self, mock_neo4j_client, sample_entities):
        """Test label generation when disabled."""
        labeler = CommunityLabeler(neo4j_client=mock_neo4j_client, enabled=False)

        label = await labeler.generate_label(sample_entities)

        assert label == "Unlabeled Community"

    @pytest.mark.asyncio
    async def test_generate_label_llm_error(self, labeler, sample_entities):
        """Test error handling during LLM call."""
        labeler.proxy.generate.side_effect = Exception("LLM proxy error")

        label = await labeler.generate_label(sample_entities)

        assert label == "Unlabeled Community"


class TestLabelAllCommunities:
    """Tests for labeling all communities."""

    @pytest.mark.asyncio
    async def test_label_all_success(self, labeler, mock_neo4j_client):
        """Test labeling all communities successfully."""
        communities = [
            Community(id="comm_1", label="", entity_ids=["e1", "e2"], size=2),
            Community(id="comm_2", label="", entity_ids=["e3", "e4"], size=2),
        ]

        mock_neo4j_client.execute_read.return_value = [
            {
                "id": "e1",
                "name": "Entity 1",
                "type": "CONCEPT",
                "description": "Test",
                "properties": {},
                "source_document": None,
                "confidence": 1.0,
            },
        ]

        mock_neo4j_client.execute_write.return_value = [{"updated_count": 2}]

        mock_result = MagicMock()
        mock_result.content = "Test Community"
        labeler.proxy.generate.return_value = mock_result

        labeled = await labeler.label_all_communities(communities)

        assert len(labeled) == 2
        assert all(c.label != "" for c in labeled)

    @pytest.mark.asyncio
    async def test_label_all_disabled(self, mock_neo4j_client):
        """Test labeling when disabled."""
        labeler = CommunityLabeler(neo4j_client=mock_neo4j_client, enabled=False)
        communities = [Community(id="comm_1", label="", entity_ids=["e1"], size=1)]

        labeled = await labeler.label_all_communities(communities)

        assert labeled == communities

    @pytest.mark.asyncio
    async def test_label_all_with_errors(self, labeler, mock_neo4j_client):
        """Test labeling with some errors."""
        communities = [
            Community(id="comm_1", label="", entity_ids=["e1"], size=1),
            Community(id="comm_2", label="", entity_ids=["e2"], size=1),
        ]

        # First succeeds, second fails (returns empty list = no entities found)
        mock_neo4j_client.execute_read.side_effect = [
            [
                {
                    "id": "e1",
                    "name": "E1",
                    "type": "CONCEPT",
                    "description": "",
                    "properties": {},
                    "source_document": None,
                    "confidence": 1.0,
                }
            ],
            [],  # No entities found triggers "Empty Community"
        ]

        mock_neo4j_client.execute_write.return_value = [{"updated_count": 1}]

        mock_result = MagicMock()
        mock_result.content = "Test Label"
        labeler.proxy.generate.return_value = mock_result

        labeled = await labeler.label_all_communities(communities)

        assert len(labeled) == 2
        # First should be labeled, second should be "Empty Community" (no entities found)
        assert labeled[1].label == "Empty Community"


class TestUpdateCommunityLabel:
    """Tests for updating community labels."""

    @pytest.mark.asyncio
    async def test_update_label_success(self, labeler, mock_neo4j_client):
        """Test successful label update."""
        mock_neo4j_client.execute_write.return_value = [{"updated_count": 3}]

        success = await labeler.update_community_label("comm_1", "Test Label")

        assert success is True
        mock_neo4j_client.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_label_no_entities(self, labeler, mock_neo4j_client):
        """Test updating label when no entities found."""
        mock_neo4j_client.execute_write.return_value = [{"updated_count": 0}]

        success = await labeler.update_community_label("nonexistent", "Label")

        assert success is False

    @pytest.mark.asyncio
    async def test_update_label_error(self, labeler, mock_neo4j_client):
        """Test error handling during label update."""
        mock_neo4j_client.execute_write.side_effect = Exception("Write failed")

        success = await labeler.update_community_label("comm_1", "Label")

        assert success is False


class TestGetCommunityLabel:
    """Tests for getting community labels."""

    @pytest.mark.asyncio
    async def test_get_label_exists(self, labeler, mock_neo4j_client):
        """Test getting existing label."""
        mock_neo4j_client.execute_read.return_value = [{"label": "Test Label"}]

        label = await labeler.get_community_label("comm_1")

        assert label == "Test Label"

    @pytest.mark.asyncio
    async def test_get_label_not_found(self, labeler, mock_neo4j_client):
        """Test getting label when community doesn't exist."""
        mock_neo4j_client.execute_read.return_value = []

        label = await labeler.get_community_label("nonexistent")

        assert label is None

    @pytest.mark.asyncio
    async def test_get_label_error(self, labeler, mock_neo4j_client):
        """Test error handling when getting label."""
        mock_neo4j_client.execute_read.side_effect = Exception("Query failed")

        label = await labeler.get_community_label("comm_1")

        assert label is None
