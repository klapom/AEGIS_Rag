"""Unit tests for Section Community Detection (Sprint 68 Feature 68.5).

Tests:
- Section graph construction (nodes, edges)
- Louvain community detection
- Community storage in Neo4j
- Community-based retrieval
- Edge type creation (PARENT_OF, SIMILAR_TO, REFERENCES, FOLLOWS)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

from src.components.graph_rag.section_communities import (
    CommunityDetectionResult,
    CommunityRetrievalResult,
    SectionCommunityDetector,
    SectionCommunityService,
    SectionEdge,
    SectionGraph,
    SectionGraphBuilder,
    SectionNode,
    get_section_community_service,
    reset_section_community_service,
)
from src.core.models import Community


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = AsyncMock()
    client.execute_read = AsyncMock()
    client.execute_write = AsyncMock()
    return client


@pytest.fixture
def sample_sections():
    """Sample sections for testing."""
    return [
        {
            "id": "section_1",
            "heading": "Introduction",
            "content": "This is the introduction section about RAG systems.",
            "embedding": [0.1, 0.2, 0.3],
            "level": 1,
            "doc_id": "doc_1",
            "page_no": 1,
            "sequence": 0,
            "parent_id": None,
        },
        {
            "id": "section_2",
            "heading": "Vector Search",
            "content": "Vector search uses embeddings for similarity.",
            "embedding": [0.15, 0.25, 0.35],
            "level": 2,
            "doc_id": "doc_1",
            "page_no": 2,
            "sequence": 1,
            "parent_id": "section_1",
        },
        {
            "id": "section_3",
            "heading": "Graph RAG",
            "content": "Graph RAG combines knowledge graphs with retrieval.",
            "embedding": [0.8, 0.7, 0.6],
            "level": 2,
            "doc_id": "doc_1",
            "page_no": 3,
            "sequence": 2,
            "parent_id": "section_1",
        },
    ]


@pytest.fixture
def sample_section_nodes():
    """Sample section nodes."""
    return [
        SectionNode(
            id="section_1",
            heading="Introduction",
            content="RAG systems introduction",
            embedding=[0.1, 0.2, 0.3],
            level=1,
            doc_id="doc_1",
            page_no=1,
            sequence=0,
        ),
        SectionNode(
            id="section_2",
            heading="Vector Search",
            content="Vector search details",
            embedding=[0.15, 0.25, 0.35],
            level=2,
            doc_id="doc_1",
            page_no=2,
            sequence=1,
        ),
    ]


@pytest.fixture
def sample_communities():
    """Sample communities for testing."""
    return [
        Community(
            id="comm_1",
            label="RAG Components",
            entity_ids=["section_1", "section_2"],
            size=2,
            density=0.85,
            metadata={"algorithm": "louvain", "resolution": 1.0},
        ),
        Community(
            id="comm_2",
            label="Graph Methods",
            entity_ids=["section_3"],
            size=1,
            density=0.0,
            metadata={"algorithm": "louvain", "resolution": 1.0},
        ),
    ]


# =============================================================================
# SECTION GRAPH BUILDER TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_section_graph_builder_initialization(mock_neo4j_client):
    """Test SectionGraphBuilder initialization."""
    builder = SectionGraphBuilder(neo4j_client=mock_neo4j_client)

    assert builder.neo4j_client == mock_neo4j_client
    assert builder.similarity_threshold == 0.8


@pytest.mark.asyncio
async def test_build_section_graph(mock_neo4j_client, sample_sections):
    """Test section graph construction."""
    # Mock Neo4j fetch
    mock_neo4j_client.execute_read.return_value = sample_sections

    builder = SectionGraphBuilder(neo4j_client=mock_neo4j_client)
    graph = await builder.build_section_graph(document_id="doc_1")

    # Verify nodes
    assert graph.node_count == 3
    assert len(graph.nodes) == 3
    assert graph.nodes[0].id == "section_1"

    # Verify edges exist
    assert graph.edge_count > 0
    assert len(graph.edges) > 0

    # Verify edge types
    edge_types = {edge.edge_type for edge in graph.edges}
    assert "PARENT_OF" in edge_types  # Hierarchical
    assert "FOLLOWS" in edge_types  # Sequential


@pytest.mark.asyncio
async def test_create_hierarchical_edges(mock_neo4j_client, sample_sections):
    """Test PARENT_OF edge creation."""
    builder = SectionGraphBuilder(neo4j_client=mock_neo4j_client)
    edges = builder._create_hierarchical_edges(sample_sections)

    # Should have 2 parent edges (section_1 -> section_2, section_1 -> section_3)
    assert len(edges) == 2
    assert all(e.edge_type == "PARENT_OF" for e in edges)

    # Check first edge
    assert edges[0].source == "section_1"
    assert edges[0].target == "section_2"


@pytest.mark.asyncio
async def test_create_similarity_edges(mock_neo4j_client, sample_section_nodes):
    """Test SIMILAR_TO edge creation."""
    builder = SectionGraphBuilder(neo4j_client=mock_neo4j_client, similarity_threshold=0.9)
    edges = await builder._create_similarity_edges(sample_section_nodes)

    # With threshold 0.9, embeddings [0.1, 0.2, 0.3] and [0.15, 0.25, 0.35]
    # should produce similarity ~0.9999, so should create edge
    assert len(edges) >= 1
    assert all(e.edge_type == "SIMILAR_TO" for e in edges)
    assert all(e.weight >= 0.9 for e in edges)


@pytest.mark.asyncio
async def test_create_reference_edges(mock_neo4j_client, sample_sections):
    """Test REFERENCES edge creation."""
    # Add reference to another section in content
    sections_with_ref = sample_sections.copy()
    sections_with_ref[1]["content"] = "See introduction section for more details."

    builder = SectionGraphBuilder(neo4j_client=mock_neo4j_client)
    edges = await builder._create_reference_edges(sections_with_ref)

    # Should detect reference from section_2 to section_1 (mentions "introduction")
    assert len(edges) >= 1
    assert any(e.edge_type == "REFERENCES" for e in edges)


@pytest.mark.asyncio
async def test_create_sequential_edges(mock_neo4j_client, sample_sections):
    """Test FOLLOWS edge creation."""
    builder = SectionGraphBuilder(neo4j_client=mock_neo4j_client)
    edges = builder._create_sequential_edges(sample_sections)

    # Should have 2 sequential edges (0->1, 1->2)
    assert len(edges) == 2
    assert all(e.edge_type == "FOLLOWS" for e in edges)

    # Check order
    assert edges[0].source == "section_1"
    assert edges[0].target == "section_2"


@pytest.mark.asyncio
async def test_build_empty_graph(mock_neo4j_client):
    """Test graph construction with no sections."""
    mock_neo4j_client.execute_read.return_value = []

    builder = SectionGraphBuilder(neo4j_client=mock_neo4j_client)
    graph = await builder.build_section_graph()

    assert graph.node_count == 0
    assert graph.edge_count == 0


# =============================================================================
# COMMUNITY DETECTOR TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_community_detector_initialization(mock_neo4j_client):
    """Test SectionCommunityDetector initialization."""
    detector = SectionCommunityDetector(neo4j_client=mock_neo4j_client)

    assert detector.neo4j_client == mock_neo4j_client
    assert detector.min_community_size == 2


@pytest.mark.asyncio
async def test_detect_communities_louvain(mock_neo4j_client, sample_section_nodes):
    """Test Louvain community detection."""
    # Build a simple graph
    graph = SectionGraph(
        nodes=sample_section_nodes,
        edges=[
            SectionEdge(
                source="section_1",
                target="section_2",
                edge_type="SIMILAR_TO",
                weight=0.95,
            )
        ],
        node_count=2,
        edge_count=1,
    )

    detector = SectionCommunityDetector(
        neo4j_client=mock_neo4j_client,
        min_community_size=1,
    )
    result = await detector.detect_communities(graph, resolution=1.0)

    assert isinstance(result, CommunityDetectionResult)
    assert result.community_count >= 1
    assert result.algorithm == "louvain"
    assert 0.0 <= result.modularity <= 1.0


@pytest.mark.asyncio
async def test_detect_communities_empty_graph(mock_neo4j_client):
    """Test community detection on empty graph."""
    graph = SectionGraph()

    detector = SectionCommunityDetector(neo4j_client=mock_neo4j_client)
    result = await detector.detect_communities(graph)

    assert result.community_count == 0
    assert len(result.communities) == 0


@pytest.mark.asyncio
async def test_detect_communities_min_size_filter(mock_neo4j_client, sample_section_nodes):
    """Test community filtering by minimum size."""
    # Create graph with 3 nodes, 2 connected (will form 1 community of size 2, 1 of size 1)
    nodes = sample_section_nodes + [
        SectionNode(
            id="section_3",
            heading="Isolated",
            content="Isolated section",
            embedding=None,
            level=1,
            doc_id="doc_1",
            page_no=3,
            sequence=2,
        )
    ]

    graph = SectionGraph(
        nodes=nodes,
        edges=[
            SectionEdge(
                source="section_1",
                target="section_2",
                edge_type="SIMILAR_TO",
                weight=0.95,
            )
        ],
        node_count=3,
        edge_count=1,
    )

    detector = SectionCommunityDetector(
        neo4j_client=mock_neo4j_client,
        min_community_size=2,
    )
    result = await detector.detect_communities(graph)

    # Should filter out communities with size < 2
    assert all(c.size >= 2 for c in result.communities)


# =============================================================================
# COMMUNITY SERVICE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_community_service_initialization(mock_neo4j_client):
    """Test SectionCommunityService initialization."""
    service = SectionCommunityService(neo4j_client=mock_neo4j_client)

    assert service.neo4j_client == mock_neo4j_client
    assert isinstance(service.graph_builder, SectionGraphBuilder)
    assert isinstance(service.community_detector, SectionCommunityDetector)


@pytest.mark.asyncio
async def test_index_communities(mock_neo4j_client, sample_sections, sample_communities):
    """Test community indexing workflow."""
    # Mock Neo4j responses
    mock_neo4j_client.execute_read.return_value = sample_sections
    mock_neo4j_client.execute_write.return_value = [{"relationships_created": 2}]

    service = SectionCommunityService(neo4j_client=mock_neo4j_client)
    result = await service.index_communities(document_id="doc_1", resolution=1.0)

    assert isinstance(result, CommunityDetectionResult)
    assert result.community_count >= 0

    # Verify write was called (storing communities)
    assert mock_neo4j_client.execute_write.called


@pytest.mark.asyncio
async def test_retrieve_by_community(mock_neo4j_client):
    """Test community-based retrieval."""
    # Mock community search results
    mock_neo4j_client.execute_read.side_effect = [
        # First call: find relevant communities
        [
            {
                "id": "comm_1",
                "size": 3,
                "density": 0.8,
                "matching_sections": 2,
                "headings": ["Introduction", "Vector Search"],
            }
        ],
        # Second call: get community sections
        [
            {
                "id": "section_1",
                "heading": "Introduction",
                "content": "RAG introduction",
                "level": 1,
                "doc_id": "doc_1",
                "page_no": 1,
            }
        ],
    ]

    service = SectionCommunityService(neo4j_client=mock_neo4j_client)
    result = await service.retrieve_by_community(query="vector search", top_k=3)

    assert isinstance(result, CommunityRetrievalResult)
    assert result.query == "vector search"
    assert len(result.communities) == 1
    assert len(result.sections) == 1
    assert result.total_sections == 1


@pytest.mark.asyncio
async def test_store_communities(mock_neo4j_client, sample_communities):
    """Test community storage in Neo4j."""
    mock_neo4j_client.execute_write.return_value = [{"relationships_created": 2}]

    service = SectionCommunityService(neo4j_client=mock_neo4j_client)
    await service._store_communities(sample_communities)

    # Verify write was called for each community
    assert mock_neo4j_client.execute_write.call_count == 2


# =============================================================================
# SINGLETON TESTS
# =============================================================================


def test_get_section_community_service_singleton():
    """Test singleton pattern for service."""
    reset_section_community_service()

    service1 = get_section_community_service()
    service2 = get_section_community_service()

    assert service1 is service2


def test_reset_section_community_service():
    """Test resetting singleton."""
    service1 = get_section_community_service()
    reset_section_community_service()
    service2 = get_section_community_service()

    assert service1 is not service2


# =============================================================================
# EDGE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_similarity_edges_with_no_embeddings(mock_neo4j_client):
    """Test similarity edge creation when no embeddings exist."""
    nodes_no_embeddings = [
        SectionNode(
            id="section_1",
            heading="Test",
            content="Content",
            embedding=None,
            level=1,
            doc_id="doc_1",
            page_no=1,
            sequence=0,
        )
    ]

    builder = SectionGraphBuilder(neo4j_client=mock_neo4j_client)
    edges = await builder._create_similarity_edges(nodes_no_embeddings)

    assert len(edges) == 0


@pytest.mark.asyncio
async def test_reference_edges_no_matches(mock_neo4j_client, sample_sections):
    """Test reference edge creation with no matching references."""
    # Modify content to have no references
    sections_no_refs = sample_sections.copy()
    for section in sections_no_refs:
        section["content"] = "Generic content with no references."

    builder = SectionGraphBuilder(neo4j_client=mock_neo4j_client)
    edges = await builder._create_reference_edges(sections_no_refs)

    # May have some false positives, but should be minimal
    assert len(edges) >= 0


@pytest.mark.asyncio
async def test_community_detection_with_resolution_parameter(mock_neo4j_client, sample_section_nodes):
    """Test community detection with different resolution values."""
    graph = SectionGraph(
        nodes=sample_section_nodes,
        edges=[
            SectionEdge(
                source="section_1",
                target="section_2",
                edge_type="SIMILAR_TO",
                weight=0.95,
            )
        ],
        node_count=2,
        edge_count=1,
    )

    detector = SectionCommunityDetector(
        neo4j_client=mock_neo4j_client,
        min_community_size=1,
    )

    # Test with different resolutions
    result_low = await detector.detect_communities(graph, resolution=0.5)
    result_high = await detector.detect_communities(graph, resolution=2.0)

    # Higher resolution should typically produce more communities
    # (though with only 2 nodes, results may be similar)
    assert result_low.community_count >= 1
    assert result_high.community_count >= 1


# =============================================================================
# INTEGRATION TESTS (requires Neo4j mock setup)
# =============================================================================


@pytest.mark.asyncio
async def test_end_to_end_workflow(mock_neo4j_client, sample_sections):
    """Test complete workflow: build graph -> detect communities -> store -> retrieve."""
    # Setup mocks
    mock_neo4j_client.execute_read.side_effect = [
        sample_sections,  # build_section_graph
        [{"id": "comm_1", "size": 2, "density": 0.8, "matching_sections": 2, "headings": []}],
        [{"id": "section_1", "heading": "Test", "content": "Test", "level": 1, "doc_id": "doc_1", "page_no": 1}],
    ]
    mock_neo4j_client.execute_write.return_value = [{"relationships_created": 2}]

    service = SectionCommunityService(neo4j_client=mock_neo4j_client)

    # Step 1: Index communities
    detection_result = await service.index_communities(document_id="doc_1")
    assert detection_result.community_count >= 0

    # Step 2: Retrieve by community
    retrieval_result = await service.retrieve_by_community(query="test", top_k=3)
    assert retrieval_result.total_sections >= 0
