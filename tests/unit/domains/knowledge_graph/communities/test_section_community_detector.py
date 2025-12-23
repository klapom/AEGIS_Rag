"""Unit tests for Section-Based Community Detection.

Sprint 62 Feature 62.8: Section-Based Community Detection (3 SP)

Tests cover:
- Community detection on sample graph
- Section-scoped communities
- Community metadata storage
- Cross-section community comparison
- BELONGS_TO_COMMUNITY relationships
- Coverage >80%
"""

from unittest.mock import AsyncMock, MagicMock

import networkx as nx
import pytest

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.core.models import Community
from src.domains.knowledge_graph.communities.section_community_detector import (
    CrossSectionCommunityComparison,
    SectionCommunityDetector,
    SectionCommunityMetadata,
    SectionCommunityResult,
    get_section_community_detector,
    reset_section_community_detector,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create mock Neo4j client."""
    client = MagicMock(spec=Neo4jClient)
    client.execute_read = AsyncMock()
    client.execute_write = AsyncMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def sample_entities() -> list[str]:
    """Sample entity IDs for testing."""
    return [
        "entity-1",
        "entity-2",
        "entity-3",
        "entity-4",
        "entity-5",
        "entity-6",
    ]


@pytest.fixture
def sample_graph() -> nx.Graph:
    """Create a sample NetworkX graph for testing.

    Graph structure:
    - Community 1: entity-1, entity-2, entity-3 (densely connected)
    - Community 2: entity-4, entity-5, entity-6 (densely connected)
    - Sparse connections between communities
    """
    graph = nx.Graph()

    # Add nodes
    graph.add_nodes_from(["entity-1", "entity-2", "entity-3", "entity-4", "entity-5", "entity-6"])

    # Add edges - Community 1 (dense)
    graph.add_edge("entity-1", "entity-2")
    graph.add_edge("entity-1", "entity-3")
    graph.add_edge("entity-2", "entity-3")

    # Add edges - Community 2 (dense)
    graph.add_edge("entity-4", "entity-5")
    graph.add_edge("entity-4", "entity-6")
    graph.add_edge("entity-5", "entity-6")

    # Sparse connection between communities
    graph.add_edge("entity-3", "entity-4")

    return graph


@pytest.fixture
def section_community_detector(mock_neo4j_client: MagicMock) -> SectionCommunityDetector:
    """Create SectionCommunityDetector instance with mocked dependencies."""
    # Reset singleton
    reset_section_community_detector()

    detector = SectionCommunityDetector(neo4j_client=mock_neo4j_client)
    return detector


@pytest.fixture(autouse=True)
def cleanup_singleton():
    """Clean up singleton after each test."""
    yield
    reset_section_community_detector()


# =============================================================================
# TESTS: INITIALIZATION
# =============================================================================


def test_section_community_detector_initialization(mock_neo4j_client: MagicMock):
    """Test SectionCommunityDetector initialization."""
    detector = SectionCommunityDetector(neo4j_client=mock_neo4j_client)

    assert detector.neo4j_client is mock_neo4j_client
    assert detector.community_detector is not None


def test_get_section_community_detector_singleton():
    """Test singleton pattern for get_section_community_detector."""
    reset_section_community_detector()

    detector1 = get_section_community_detector()
    detector2 = get_section_community_detector()

    assert detector1 is detector2


def test_reset_section_community_detector():
    """Test resetting singleton."""
    detector1 = get_section_community_detector()
    reset_section_community_detector()
    detector2 = get_section_community_detector()

    assert detector1 is not detector2


# =============================================================================
# TESTS: SECTION ENTITY RETRIEVAL
# =============================================================================


@pytest.mark.asyncio
async def test_get_section_entities(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
    sample_entities: list[str],
):
    """Test retrieving entities in a section."""
    # Mock Neo4j response
    mock_neo4j_client.execute_read.return_value = [
        {"entity_id": entity_id} for entity_id in sample_entities
    ]

    entities = await section_community_detector._get_section_entities(
        section_heading="Introduction", document_id="doc_123"
    )

    assert entities == sample_entities
    assert mock_neo4j_client.execute_read.call_count == 1

    # Verify query contains section filtering
    call_args = mock_neo4j_client.execute_read.call_args
    query = call_args[0][0]
    params = call_args[0][1]

    assert "Section" in query
    assert "DEFINES" in query
    assert params["section_heading"] == "Introduction"
    assert params["document_id"] == "doc_123"


@pytest.mark.asyncio
async def test_get_section_entities_no_results(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test retrieving entities when section has no entities."""
    mock_neo4j_client.execute_read.return_value = []

    entities = await section_community_detector._get_section_entities(
        section_heading="Empty Section"
    )

    assert entities == []


@pytest.mark.asyncio
async def test_get_section_entities_filters_none(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test that None entity IDs are filtered out."""
    mock_neo4j_client.execute_read.return_value = [
        {"entity_id": "entity-1"},
        {"entity_id": None},
        {"entity_id": "entity-2"},
    ]

    entities = await section_community_detector._get_section_entities(
        section_heading="Introduction"
    )

    assert entities == ["entity-1", "entity-2"]


# =============================================================================
# TESTS: SUBGRAPH BUILDING
# =============================================================================


@pytest.mark.asyncio
async def test_build_section_subgraph(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test building NetworkX subgraph for section entities."""
    entity_ids = ["entity-1", "entity-2", "entity-3"]

    # Mock relationships
    mock_neo4j_client.execute_read.return_value = [
        {"source": "entity-1", "target": "entity-2"},
        {"source": "entity-2", "target": "entity-3"},
    ]

    graph = await section_community_detector._build_section_subgraph(entity_ids)

    assert isinstance(graph, nx.Graph)
    assert set(graph.nodes()) == set(entity_ids)
    assert graph.number_of_edges() == 2
    assert graph.has_edge("entity-1", "entity-2")
    assert graph.has_edge("entity-2", "entity-3")


@pytest.mark.asyncio
async def test_build_section_subgraph_filters_self_loops(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test that self-loops are filtered out."""
    entity_ids = ["entity-1", "entity-2"]

    # Mock relationships including self-loop
    mock_neo4j_client.execute_read.return_value = [
        {"source": "entity-1", "target": "entity-1"},  # Self-loop
        {"source": "entity-1", "target": "entity-2"},
    ]

    graph = await section_community_detector._build_section_subgraph(entity_ids)

    assert graph.number_of_edges() == 1
    assert not graph.has_edge("entity-1", "entity-1")
    assert graph.has_edge("entity-1", "entity-2")


# =============================================================================
# TESTS: COMMUNITY DETECTION
# =============================================================================


@pytest.mark.asyncio
async def test_detect_communities_networkx(
    section_community_detector: SectionCommunityDetector,
    sample_graph: nx.Graph,
):
    """Test NetworkX community detection on sample graph."""
    communities = await section_community_detector._detect_communities_networkx(
        graph=sample_graph, algorithm="louvain", resolution=1.0
    )

    assert isinstance(communities, list)
    assert len(communities) >= 1  # At least one community

    # Verify community structure
    for community in communities:
        assert isinstance(community, Community)
        assert community.id.startswith("section_community_")
        assert community.size >= 1
        assert 0.0 <= community.density <= 1.0
        assert community.metadata["algorithm"] == "louvain"
        assert community.metadata["scope"] == "section"


@pytest.mark.asyncio
async def test_detect_communities_networkx_leiden_fallback(
    section_community_detector: SectionCommunityDetector,
    sample_graph: nx.Graph,
):
    """Test that Leiden algorithm falls back to Louvain."""
    communities = await section_community_detector._detect_communities_networkx(
        graph=sample_graph, algorithm="leiden", resolution=1.0
    )

    assert len(communities) >= 1
    # Algorithm should be louvain (fallback)
    assert communities[0].metadata["algorithm"] == "louvain"


# =============================================================================
# TESTS: DENSITY CALCULATION
# =============================================================================


def test_calculate_density_full_graph(section_community_detector: SectionCommunityDetector):
    """Test density calculation for fully connected graph."""
    graph = nx.Graph()
    graph.add_nodes_from(["a", "b", "c"])
    graph.add_edges_from([("a", "b"), ("b", "c"), ("a", "c")])

    density = section_community_detector._calculate_density(graph, ["a", "b", "c"])

    assert density == 1.0  # Fully connected


def test_calculate_density_sparse_graph(section_community_detector: SectionCommunityDetector):
    """Test density calculation for sparse graph."""
    graph = nx.Graph()
    graph.add_nodes_from(["a", "b", "c"])
    graph.add_edge("a", "b")  # Only one edge out of 3 possible

    density = section_community_detector._calculate_density(graph, ["a", "b", "c"])

    assert 0.0 < density < 1.0


def test_calculate_density_single_node(section_community_detector: SectionCommunityDetector):
    """Test density calculation for single node."""
    graph = nx.Graph()
    graph.add_node("a")

    density = section_community_detector._calculate_density(graph, ["a"])

    assert density == 0.0


def test_calculate_cohesion(section_community_detector: SectionCommunityDetector):
    """Test that cohesion equals density."""
    graph = nx.Graph()
    graph.add_nodes_from(["a", "b", "c"])
    graph.add_edges_from([("a", "b"), ("b", "c")])

    density = section_community_detector._calculate_density(graph, ["a", "b", "c"])
    cohesion = section_community_detector._calculate_cohesion(graph, ["a", "b", "c"])

    assert cohesion == density


# =============================================================================
# TESTS: DETECT COMMUNITIES IN SECTION
# =============================================================================


@pytest.mark.asyncio
async def test_detect_communities_in_section(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test full community detection workflow for a section."""
    section_heading = "Introduction"
    document_id = "doc_123"

    # Mock _get_section_entities
    mock_neo4j_client.execute_read.side_effect = [
        # First call: _get_section_entities
        [{"entity_id": f"entity-{i}"} for i in range(1, 7)],
        # Second call: _get_section_id
        [{"section_id": "section-123"}],
        # Third call: _build_section_subgraph
        [
            {"source": "entity-1", "target": "entity-2"},
            {"source": "entity-2", "target": "entity-3"},
            {"source": "entity-4", "target": "entity-5"},
        ],
    ]

    # Mock _store_section_communities
    mock_neo4j_client.execute_write.return_value = [{"relationships_created": 6}]

    result = await section_community_detector.detect_communities_in_section(
        section_heading=section_heading,
        document_id=document_id,
        algorithm="louvain",
        resolution=1.0,
        min_size=2,
    )

    assert isinstance(result, SectionCommunityResult)
    assert result.section_heading == section_heading
    assert result.section_id == "section-123"
    assert result.total_entities == 6
    assert result.algorithm == "louvain"
    assert result.resolution == 1.0
    assert result.detection_time_ms > 0

    # Communities should be detected
    assert len(result.communities) >= 1

    for community in result.communities:
        assert isinstance(community, SectionCommunityMetadata)
        assert community.section_heading == section_heading
        assert community.entity_count >= 2  # min_size filter
        assert 0.0 <= community.cohesion_score <= 1.0


@pytest.mark.asyncio
async def test_detect_communities_in_section_no_entities(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test community detection when section has no entities."""
    mock_neo4j_client.execute_read.return_value = []

    result = await section_community_detector.detect_communities_in_section(
        section_heading="Empty Section",
        algorithm="louvain",
    )

    assert result.total_entities == 0
    assert len(result.communities) == 0
    assert result.section_id is None


# =============================================================================
# TESTS: COMMUNITY STORAGE
# =============================================================================


@pytest.mark.asyncio
async def test_store_section_communities(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test storing communities in Neo4j."""
    communities = [
        Community(
            id="section_community_0",
            label="Test Community",
            entity_ids=["entity-1", "entity-2", "entity-3"],
            size=3,
            density=0.8,
            metadata={"algorithm": "louvain", "resolution": 1.0},
        )
    ]

    mock_neo4j_client.execute_write.return_value = [{"relationships_created": 3}]

    await section_community_detector._store_section_communities(
        communities=communities,
        section_heading="Introduction",
        section_id="section-123",
    )

    # Verify Neo4j write was called
    assert mock_neo4j_client.execute_write.call_count >= 1

    # Verify query creates BELONGS_TO_COMMUNITY relationships
    call_args = mock_neo4j_client.execute_write.call_args_list[0]
    query = call_args[0][0]
    params = call_args[0][1]

    assert "BELONGS_TO_COMMUNITY" in query
    assert "Community" in query
    assert params["community_id"] == "section_community_0"
    assert params["entity_ids"] == ["entity-1", "entity-2", "entity-3"]
    assert params["section_heading"] == "Introduction"


@pytest.mark.asyncio
async def test_update_section_community_metadata(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test updating section node with community metadata."""
    mock_neo4j_client.execute_write.return_value = [{"heading": "Introduction"}]

    await section_community_detector._update_section_community_metadata(
        section_heading="Introduction", community_count=3
    )

    # Verify write call
    assert mock_neo4j_client.execute_write.call_count == 1

    call_args = mock_neo4j_client.execute_write.call_args
    query = call_args[0][0]
    params = call_args[0][1]

    assert "Section" in query
    assert "community_count" in query
    assert params["section_heading"] == "Introduction"
    assert params["community_count"] == 3


# =============================================================================
# TESTS: GET COMMUNITY ENTITIES
# =============================================================================


@pytest.mark.asyncio
async def test_get_community_entities(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test retrieving entities in a community."""
    mock_neo4j_client.execute_read.return_value = [
        {"entity_id": "entity-1"},
        {"entity_id": "entity-2"},
        {"entity_id": "entity-3"},
    ]

    entities = await section_community_detector._get_community_entities(
        community_id="section_community_0"
    )

    assert entities == ["entity-1", "entity-2", "entity-3"]

    # Verify query
    call_args = mock_neo4j_client.execute_read.call_args
    query = call_args[0][0]
    params = call_args[0][1]

    assert "BELONGS_TO_COMMUNITY" in query
    assert params["community_id"] == "section_community_0"


# =============================================================================
# TESTS: CROSS-SECTION COMPARISON
# =============================================================================


@pytest.mark.asyncio
async def test_compare_communities_across_sections(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test comparing communities across multiple sections."""
    # Create a list to cycle through mock responses
    mock_responses = [
        # Section 1 - get entities
        [{"entity_id": f"entity-{i}"} for i in range(1, 4)],
        # Section 1 - get section ID
        [{"section_id": "section-1"}],
        # Section 1 - build subgraph
        [{"source": "entity-1", "target": "entity-2"}],
        # Section 2 - get entities
        [{"entity_id": f"entity-{i}"} for i in range(3, 6)],
        # Section 2 - get section ID
        [{"section_id": "section-2"}],
        # Section 2 - build subgraph
        [{"source": "entity-4", "target": "entity-5"}],
    ]

    # Add many get_community_entities responses (we need many for the comparison logic)
    for _ in range(20):
        mock_responses.append([{"entity_id": "entity-1"}, {"entity_id": "entity-2"}])
        mock_responses.append([{"entity_id": "entity-3"}, {"entity_id": "entity-4"}])

    mock_neo4j_client.execute_read.side_effect = mock_responses
    mock_neo4j_client.execute_write.return_value = [{"relationships_created": 2}]

    comparison = await section_community_detector.compare_communities_across_sections(
        section_headings=["Introduction", "Methods"],
        document_id="doc_123",
    )

    assert isinstance(comparison, CrossSectionCommunityComparison)
    assert "Introduction" in comparison.section_specific_communities
    assert "Methods" in comparison.section_specific_communities
    assert comparison.comparison_time_ms > 0


@pytest.mark.asyncio
async def test_compare_communities_overlap_matrix(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test overlap matrix calculation in cross-section comparison."""
    # Mock minimal responses
    mock_neo4j_client.execute_read.side_effect = [
        # Section 1
        [{"entity_id": "entity-1"}],
        [{"section_id": "section-1"}],
        [],
        # Section 2
        [{"entity_id": "entity-2"}],
        [{"section_id": "section-2"}],
        [],
        # Get community entities
        [{"entity_id": "entity-1"}],
        [{"entity_id": "entity-2"}],
        [{"entity_id": "entity-1"}],
        [{"entity_id": "entity-2"}],
    ]

    mock_neo4j_client.execute_write.return_value = []

    comparison = await section_community_detector.compare_communities_across_sections(
        section_headings=["Section1", "Section2"],
    )

    # Verify overlap matrix structure
    assert "Section1" in comparison.community_overlap_matrix
    assert "Section2" in comparison.community_overlap_matrix
    assert "Section2" in comparison.community_overlap_matrix["Section1"]
    assert "Section1" in comparison.community_overlap_matrix["Section2"]

    # Diagonal should be 0
    assert comparison.community_overlap_matrix["Section1"]["Section1"] == 0
    assert comparison.community_overlap_matrix["Section2"]["Section2"] == 0


# =============================================================================
# TESTS: GET SECTION COMMUNITIES
# =============================================================================


@pytest.mark.asyncio
async def test_get_section_communities(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test retrieving all communities for a section."""
    mock_neo4j_client.execute_read.return_value = [
        {
            "community_id": "section_community_0",
            "size": 3,
            "density": 0.8,
            "algorithm": "louvain",
            "entity_ids": ["entity-1", "entity-2", "entity-3"],
        },
        {
            "community_id": "section_community_1",
            "size": 2,
            "density": 0.5,
            "algorithm": "louvain",
            "entity_ids": ["entity-4", "entity-5"],
        },
    ]

    communities = await section_community_detector.get_section_communities(
        section_heading="Introduction", document_id="doc_123"
    )

    assert len(communities) == 2
    assert communities[0]["community_id"] == "section_community_0"
    assert communities[0]["size"] == 3
    assert communities[1]["community_id"] == "section_community_1"

    # Verify query
    call_args = mock_neo4j_client.execute_read.call_args
    query = call_args[0][0]

    assert "BELONGS_TO_COMMUNITY" in query
    assert "Section" in query


# =============================================================================
# TESTS: ERROR HANDLING
# =============================================================================


@pytest.mark.asyncio
async def test_store_communities_handles_error(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test error handling in community storage."""
    communities = [
        Community(
            id="test_community",
            label="Test",
            entity_ids=["entity-1"],
            size=1,
            density=0.0,
            metadata={},
        )
    ]

    mock_neo4j_client.execute_write.side_effect = Exception("Database error")

    with pytest.raises(Exception, match="Database error"):
        await section_community_detector._store_section_communities(
            communities=communities,
            section_heading="Test Section",
            section_id="section-123",
        )


# =============================================================================
# TESTS: INTEGRATION SCENARIOS
# =============================================================================


@pytest.mark.asyncio
async def test_full_section_community_workflow(
    section_community_detector: SectionCommunityDetector,
    mock_neo4j_client: MagicMock,
):
    """Test complete workflow: detect, store, retrieve communities."""
    # Setup mocks for detection
    mock_neo4j_client.execute_read.side_effect = [
        # _get_section_entities
        [{"entity_id": f"entity-{i}"} for i in range(1, 5)],
        # _get_section_id
        [{"section_id": "section-123"}],
        # _build_section_subgraph
        [
            {"source": "entity-1", "target": "entity-2"},
            {"source": "entity-3", "target": "entity-4"},
        ],
        # _get_section_communities (retrieve)
        [
            {
                "community_id": "section_community_0",
                "size": 2,
                "density": 0.5,
                "algorithm": "louvain",
                "entity_ids": ["entity-1", "entity-2"],
            }
        ],
    ]

    mock_neo4j_client.execute_write.return_value = [{"relationships_created": 2}]

    # Step 1: Detect communities
    result = await section_community_detector.detect_communities_in_section(
        section_heading="Introduction", document_id="doc_123"
    )

    assert len(result.communities) >= 1

    # Step 2: Retrieve stored communities
    communities = await section_community_detector.get_section_communities(
        section_heading="Introduction", document_id="doc_123"
    )

    assert len(communities) >= 1
    assert communities[0]["community_id"] == "section_community_0"
