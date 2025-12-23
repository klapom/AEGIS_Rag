"""Unit tests for section community service with visualization.

Sprint 63 Feature 63.5: Section-Based Community Detection with Visualization

Tests cover:
- Community visualization generation
- Centrality metrics calculation
- Layout coordinate generation
- Community comparison across sections
- Neo4j queries for community data
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domains.knowledge_graph.communities import (
    CommunityComparisonOverview,
    CommunityEdge,
    CommunityNode,
    CommunityVisualization,
    SectionCommunityService,
    SectionCommunityVisualizationResponse,
    get_section_community_service,
    reset_section_community_service,
)


class TestCommunityNode:
    """Tests for CommunityNode model."""

    def test_community_node_creation(self) -> None:
        """Test creating a community node."""
        node = CommunityNode(
            entity_id="ent_1",
            entity_name="Alice",
            entity_type="PERSON",
            centrality=0.85,
            degree=5,
            x=100.0,
            y=200.0,
        )

        assert node.entity_id == "ent_1"
        assert node.entity_name == "Alice"
        assert node.entity_type == "PERSON"
        assert node.centrality == 0.85
        assert node.degree == 5
        assert node.x == 100.0
        assert node.y == 200.0

    def test_community_node_defaults(self) -> None:
        """Test community node with default values."""
        node = CommunityNode(
            entity_id="ent_2",
            entity_name="Bob",
            entity_type="PERSON",
        )

        assert node.centrality == 0.0
        assert node.degree == 0
        assert node.x is None
        assert node.y is None

    def test_community_node_centrality_validation(self) -> None:
        """Test centrality score validation."""
        with pytest.raises(ValueError):
            CommunityNode(
                entity_id="ent_1",
                entity_name="Alice",
                entity_type="PERSON",
                centrality=1.5,  # Invalid: > 1.0
            )

    def test_community_node_json_schema(self) -> None:
        """Test JSON schema generation."""
        node = CommunityNode(
            entity_id="ent_1",
            entity_name="Alice",
            entity_type="PERSON",
        )

        schema = node.model_json_schema()
        assert "entity_id" in schema["properties"]
        assert "centrality" in schema["properties"]


class TestCommunityEdge:
    """Tests for CommunityEdge model."""

    def test_community_edge_creation(self) -> None:
        """Test creating a community edge."""
        edge = CommunityEdge(
            source="ent_1",
            target="ent_2",
            relationship_type="WORKS_WITH",
            weight=2.5,
        )

        assert edge.source == "ent_1"
        assert edge.target == "ent_2"
        assert edge.relationship_type == "WORKS_WITH"
        assert edge.weight == 2.5

    def test_community_edge_default_weight(self) -> None:
        """Test edge with default weight."""
        edge = CommunityEdge(
            source="ent_1",
            target="ent_2",
            relationship_type="RELATES_TO",
        )

        assert edge.weight == 1.0

    def test_community_edge_weight_validation(self) -> None:
        """Test weight validation."""
        with pytest.raises(ValueError):
            CommunityEdge(
                source="ent_1",
                target="ent_2",
                relationship_type="RELATES_TO",
                weight=-1.0,  # Invalid: < 0
            )


class TestCommunityVisualization:
    """Tests for CommunityVisualization model."""

    def test_visualization_creation(self) -> None:
        """Test creating a community visualization."""
        node = CommunityNode(
            entity_id="ent_1",
            entity_name="Alice",
            entity_type="PERSON",
            centrality=0.9,
        )
        edge = CommunityEdge(
            source="ent_1",
            target="ent_2",
            relationship_type="WORKS_WITH",
        )

        viz = CommunityVisualization(
            community_id="community_0",
            section_heading="Introduction",
            size=5,
            cohesion_score=0.75,
            nodes=[node],
            edges=[edge],
        )

        assert viz.community_id == "community_0"
        assert viz.section_heading == "Introduction"
        assert viz.size == 5
        assert viz.cohesion_score == 0.75
        assert len(viz.nodes) == 1
        assert len(viz.edges) == 1
        assert viz.layout_type == "force-directed"
        assert viz.algorithm == "louvain"

    def test_visualization_empty_nodes_edges(self) -> None:
        """Test visualization with empty nodes and edges."""
        viz = CommunityVisualization(
            community_id="community_1",
            section_heading="Methods",
            size=0,
            cohesion_score=0.0,
        )

        assert len(viz.nodes) == 0
        assert len(viz.edges) == 0

    def test_visualization_layout_types(self) -> None:
        """Test visualization with different layout types."""
        for layout_type in ["force-directed", "circular", "hierarchical"]:
            viz = CommunityVisualization(
                community_id=f"community_{layout_type}",
                section_heading="Test",
                size=3,
                cohesion_score=0.5,
                layout_type=layout_type,
            )

            assert viz.layout_type == layout_type


class TestSectionCommunityVisualizationResponse:
    """Tests for SectionCommunityVisualizationResponse."""

    def test_response_creation(self) -> None:
        """Test creating a visualization response."""
        response = SectionCommunityVisualizationResponse(
            document_id="doc_123",
            section_heading="Introduction",
            total_communities=2,
            total_entities=10,
            communities=[],
            generation_time_ms=250.0,
        )

        assert response.document_id == "doc_123"
        assert response.section_heading == "Introduction"
        assert response.total_communities == 2
        assert response.total_entities == 10
        assert response.generation_time_ms == 250.0

    def test_response_with_communities(self) -> None:
        """Test response with community data."""
        viz = CommunityVisualization(
            community_id="community_0",
            section_heading="Introduction",
            size=5,
            cohesion_score=0.75,
        )

        response = SectionCommunityVisualizationResponse(
            document_id="doc_123",
            section_heading="Introduction",
            total_communities=1,
            total_entities=5,
            communities=[viz],
            generation_time_ms=350.0,
        )

        assert len(response.communities) == 1
        assert response.communities[0].community_id == "community_0"


class TestCommunityComparisonOverview:
    """Tests for CommunityComparisonOverview."""

    def test_comparison_overview_creation(self) -> None:
        """Test creating a comparison overview."""
        overview = CommunityComparisonOverview(
            section_count=2,
            sections=["Introduction", "Methods"],
            total_shared_communities=1,
            overlap_matrix={
                "Introduction": {"Methods": 3},
                "Methods": {"Introduction": 3},
            },
            comparison_time_ms=450.0,
        )

        assert overview.section_count == 2
        assert len(overview.sections) == 2
        assert overview.total_shared_communities == 1
        assert overview.comparison_time_ms == 450.0

    def test_comparison_with_shared_entities(self) -> None:
        """Test comparison with shared entities."""
        overview = CommunityComparisonOverview(
            section_count=2,
            sections=["Introduction", "Methods"],
            total_shared_communities=1,
            shared_entities={
                "Introduction-Methods": ["ent_1", "ent_2", "ent_3"]
            },
            overlap_matrix={
                "Introduction": {"Methods": 3},
                "Methods": {"Introduction": 3},
            },
            comparison_time_ms=450.0,
        )

        assert "Introduction-Methods" in overview.shared_entities
        assert len(overview.shared_entities["Introduction-Methods"]) == 3


class TestSectionCommunityService:
    """Tests for SectionCommunityService."""

    @pytest.fixture
    def mock_neo4j_client(self) -> MagicMock:
        """Create mock Neo4j client."""
        return MagicMock()

    @pytest.fixture
    def mock_detector(self) -> MagicMock:
        """Create mock section community detector."""
        return MagicMock()

    @pytest.fixture
    async def service(
        self,
        mock_neo4j_client: MagicMock,
        mock_detector: MagicMock,
    ) -> SectionCommunityService:
        """Create service with mocked dependencies."""
        return SectionCommunityService(
            neo4j_client=mock_neo4j_client,
            section_community_detector=mock_detector,
        )

    @pytest.mark.asyncio
    async def test_service_initialization(
        self,
        mock_neo4j_client: MagicMock,
        mock_detector: MagicMock,
    ) -> None:
        """Test service initialization."""
        service = SectionCommunityService(
            neo4j_client=mock_neo4j_client,
            section_community_detector=mock_detector,
        )

        assert service.neo4j_client is not None
        assert service.section_community_detector is not None

    @pytest.mark.asyncio
    async def test_get_section_communities_with_visualization(
        self,
        service: SectionCommunityService,
        mock_detector: MagicMock,
    ) -> None:
        """Test getting section communities with visualization."""
        from src.domains.knowledge_graph.communities import (
            SectionCommunityMetadata,
            SectionCommunityResult,
        )

        # Mock detector response
        mock_metadata = SectionCommunityMetadata(
            community_id="community_0",
            section_heading="Introduction",
            entity_count=5,
            cohesion_score=0.75,
        )

        mock_result = SectionCommunityResult(
            section_heading="Introduction",
            communities=[mock_metadata],
            detection_time_ms=100.0,
            total_entities=5,
        )

        mock_detector.detect_communities_in_section = AsyncMock(
            return_value=mock_result
        )

        # Mock helper methods
        service._get_community_entities = AsyncMock(return_value=["ent_1", "ent_2"])
        service._build_community_nodes = AsyncMock(
            return_value=[
                CommunityNode(
                    entity_id="ent_1",
                    entity_name="Alice",
                    entity_type="PERSON",
                )
            ]
        )
        service._build_community_edges = AsyncMock(return_value=[])
        service._calculate_centrality_metrics = AsyncMock(
            return_value={"ent_1": 0.9}
        )
        service._add_layout_coordinates = AsyncMock()

        # Call method
        response = await service.get_section_communities_with_visualization(
            section_heading="Introduction",
            document_id="doc_123",
        )

        # Verify response
        assert response.section_heading == "Introduction"
        assert response.document_id == "doc_123"
        assert response.total_communities > 0
        assert response.generation_time_ms > 0

    @pytest.mark.asyncio
    async def test_compare_section_communities(
        self,
        service: SectionCommunityService,
        mock_detector: MagicMock,
    ) -> None:
        """Test comparing communities across sections."""
        from src.domains.knowledge_graph.communities import (
            CrossSectionCommunityComparison,
        )

        # Mock detector comparison result
        mock_comparison = CrossSectionCommunityComparison(
            section_specific_communities={
                "Introduction": ["community_0"],
                "Methods": ["community_1"],
            },
            shared_communities=["community_2"],
            community_overlap_matrix={
                "Introduction": {"Methods": 2},
                "Methods": {"Introduction": 2},
            },
            comparison_time_ms=200.0,
        )

        mock_detector.compare_communities_across_sections = AsyncMock(
            return_value=mock_comparison
        )

        # Mock helper method
        service._get_section_entities = AsyncMock(return_value=["ent_1", "ent_2"])

        # Call method
        result = await service.compare_section_communities(
            section_headings=["Introduction", "Methods"],
            document_id="doc_123",
        )

        # Verify result
        assert result.section_count == 2
        assert len(result.sections) == 2
        assert result.total_shared_communities > 0

    @pytest.mark.asyncio
    async def test_build_community_nodes(
        self,
        service: SectionCommunityService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test building community nodes from Neo4j."""
        # Mock Neo4j response
        mock_neo4j_client.execute_read = AsyncMock(
            return_value=[
                {
                    "entity_id": "ent_1",
                    "entity_name": "Alice",
                    "entity_type": "PERSON",
                },
                {
                    "entity_id": "ent_2",
                    "entity_name": "Bob",
                    "entity_type": "PERSON",
                },
            ]
        )

        # Call method
        nodes = await service._build_community_nodes(["ent_1", "ent_2"])

        # Verify nodes
        assert len(nodes) == 2
        assert nodes[0].entity_id == "ent_1"
        assert nodes[0].entity_name == "Alice"
        assert nodes[1].entity_id == "ent_2"
        assert nodes[1].entity_name == "Bob"

    @pytest.mark.asyncio
    async def test_build_community_edges(
        self,
        service: SectionCommunityService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test building community edges from Neo4j."""
        # Mock Neo4j response
        mock_neo4j_client.execute_read = AsyncMock(
            return_value=[
                {
                    "source": "ent_1",
                    "target": "ent_2",
                    "relationship_type": "WORKS_WITH",
                    "weight": 1.5,
                },
            ]
        )

        # Call method
        edges = await service._build_community_edges(["ent_1", "ent_2"])

        # Verify edges
        assert len(edges) == 1
        assert edges[0].source == "ent_1"
        assert edges[0].target == "ent_2"
        assert edges[0].relationship_type == "WORKS_WITH"
        assert edges[0].weight == 1.5

    @pytest.mark.asyncio
    async def test_calculate_centrality_metrics(
        self,
        service: SectionCommunityService,
    ) -> None:
        """Test calculating centrality metrics."""
        edges = [
            CommunityEdge(
                source="ent_1",
                target="ent_2",
                relationship_type="WORKS_WITH",
            ),
            CommunityEdge(
                source="ent_1",
                target="ent_3",
                relationship_type="WORKS_WITH",
            ),
        ]

        centrality = await service._calculate_centrality_metrics(
            ["ent_1", "ent_2", "ent_3"],
            edges,
        )

        # Verify centrality
        assert "ent_1" in centrality
        assert "ent_2" in centrality
        assert "ent_3" in centrality
        # ent_1 should have highest centrality (degree 2)
        assert centrality["ent_1"] >= centrality["ent_2"]
        assert centrality["ent_1"] >= centrality["ent_3"]

    @pytest.mark.asyncio
    async def test_add_layout_coordinates(
        self,
        service: SectionCommunityService,
    ) -> None:
        """Test adding layout coordinates to nodes."""
        nodes = [
            CommunityNode(
                entity_id="ent_1",
                entity_name="Alice",
                entity_type="PERSON",
            ),
            CommunityNode(
                entity_id="ent_2",
                entity_name="Bob",
                entity_type="PERSON",
            ),
        ]
        edges = [
            CommunityEdge(
                source="ent_1",
                target="ent_2",
                relationship_type="WORKS_WITH",
            ),
        ]

        await service._add_layout_coordinates(
            nodes,
            edges,
            layout_algorithm="force-directed",
        )

        # Verify all nodes have coordinates
        for node in nodes:
            assert node.x is not None
            assert node.y is not None
            assert isinstance(node.x, float)
            assert isinstance(node.y, float)

    @pytest.mark.asyncio
    async def test_get_section_entities(
        self,
        service: SectionCommunityService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test getting entities in a section."""
        # Mock Neo4j response
        mock_neo4j_client.execute_read = AsyncMock(
            return_value=[
                {"entity_id": "ent_1"},
                {"entity_id": "ent_2"},
                {"entity_id": "ent_3"},
            ]
        )

        # Call method
        entities = await service._get_section_entities(
            "Introduction",
            document_id="doc_123",
        )

        # Verify entities
        assert len(entities) == 3
        assert "ent_1" in entities
        assert "ent_2" in entities
        assert "ent_3" in entities

    @pytest.mark.asyncio
    async def test_get_section_entities_empty(
        self,
        service: SectionCommunityService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test getting entities for non-existent section."""
        # Mock empty response
        mock_neo4j_client.execute_read = AsyncMock(return_value=[])

        # Call method
        entities = await service._get_section_entities("NonExistent")

        # Verify empty result
        assert len(entities) == 0


class TestSectionCommunityServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_service_singleton(self) -> None:
        """Test getting service singleton."""
        reset_section_community_service()

        service1 = get_section_community_service()
        service2 = get_section_community_service()

        assert service1 is service2

    def test_reset_service_singleton(self) -> None:
        """Test resetting service singleton."""
        service1 = get_section_community_service()
        reset_section_community_service()
        service2 = get_section_community_service()

        assert service1 is not service2
