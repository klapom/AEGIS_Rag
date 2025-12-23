"""Unit tests for Section-Aware Graph Service.

Sprint 62 Feature 62.1: Section-Aware Graph Queries

Tests:
- Entity queries by section
- Multi-section queries
- Relationship queries by section
- Section hierarchy queries
- Performance validation (<100ms)
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domains.knowledge_graph.querying.section_graph_service import (
    EntityWithSection,
    RelationshipWithSection,
    SectionGraphQueryResult,
    SectionGraphService,
    SectionMetadataResult,
    get_section_graph_service,
    reset_section_graph_service,
)


@pytest.fixture
def mock_neo4j_client():
    """Create mock Neo4j client."""
    client = MagicMock()
    client.execute_read = AsyncMock()
    return client


@pytest.fixture
def section_service(mock_neo4j_client):
    """Create section graph service with mock client."""
    return SectionGraphService(neo4j_client=mock_neo4j_client)


@pytest.fixture
def sample_entity_records():
    """Sample entity records from Neo4j."""
    return [
        {
            "entity_id": "entity-1",
            "entity_name": "Neural Networks",
            "entity_type": "CONCEPT",
            "entity_description": "Machine learning concept",
            "section_heading": "Introduction",
            "section_level": 1,
            "section_page": 1,
            "section_order": 0,
        },
        {
            "entity_id": "entity-2",
            "entity_name": "Deep Learning",
            "entity_type": "CONCEPT",
            "entity_description": "Advanced ML technique",
            "section_heading": "Introduction",
            "section_level": 1,
            "section_page": 1,
            "section_order": 0,
        },
    ]


@pytest.fixture
def sample_relationship_records():
    """Sample relationship records from Neo4j."""
    return [
        {
            "source_id": "entity-1",
            "source_name": "Neural Networks",
            "target_id": "entity-2",
            "target_name": "Deep Learning",
            "relationship_type": "RELATES_TO",
            "relationship_description": "Neural networks are the foundation of deep learning",
            "section_heading": "Methods",
            "section_level": 1,
            "section_page": 2,
            "section_order": 1,
        },
    ]


@pytest.fixture
def sample_section_hierarchy():
    """Sample section hierarchy records."""
    return [
        {
            "heading": "Introduction",
            "level": 1,
            "page_no": 1,
            "order": 0,
            "token_count": 500,
            "text_preview": "This paper introduces...",
        },
        {
            "heading": "Methods",
            "level": 1,
            "page_no": 2,
            "order": 1,
            "token_count": 800,
            "text_preview": "We present a novel approach...",
        },
    ]


class TestSectionGraphService:
    """Test suite for SectionGraphService."""

    @pytest.mark.asyncio
    async def test_query_entities_in_section(
        self, section_service, mock_neo4j_client, sample_entity_records
    ):
        """Test querying entities in a specific section."""
        mock_neo4j_client.execute_read.return_value = sample_entity_records

        result = await section_service.query_entities_in_section(
            section_heading="Introduction",
            document_id="doc_123",
        )

        # Verify result structure
        assert isinstance(result, SectionGraphQueryResult)
        assert len(result.entities) == 2
        assert result.section_filters == ["Introduction"]
        assert result.query_time_ms > 0

        # Verify entity data
        entity = result.entities[0]
        assert isinstance(entity, EntityWithSection)
        assert entity.entity_name in ["Neural Networks", "Deep Learning"]
        assert entity.entity_type == "CONCEPT"
        assert len(entity.sections) > 0

        # Verify section metadata
        section = entity.sections[0]
        assert isinstance(section, SectionMetadataResult)
        assert section.section_heading == "Introduction"
        assert section.section_level == 1
        assert section.section_page == 1

        # Verify Neo4j was called
        mock_neo4j_client.execute_read.assert_called_once()
        call_args = mock_neo4j_client.execute_read.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "Section" in query
        assert "DEFINES" in query
        assert params["section_heading"] == "Introduction"
        assert params["document_id"] == "doc_123"

    @pytest.mark.asyncio
    async def test_query_entities_in_section_without_document(
        self, section_service, mock_neo4j_client, sample_entity_records
    ):
        """Test querying entities without document filter."""
        mock_neo4j_client.execute_read.return_value = sample_entity_records

        result = await section_service.query_entities_in_section(
            section_heading="Methods",
        )

        assert len(result.entities) == 2

        # Verify document filter not in query
        call_args = mock_neo4j_client.execute_read.call_args
        params = call_args[0][1]
        assert "document_id" not in params

    @pytest.mark.asyncio
    async def test_query_entities_in_sections(self, section_service, mock_neo4j_client):
        """Test querying entities in multiple sections."""
        mock_records = [
            {
                "entity_id": "entity-1",
                "entity_name": "Neural Networks",
                "entity_type": "CONCEPT",
                "entity_description": "ML concept",
                "sections": [
                    {"heading": "Introduction", "level": 1, "page": 1, "order": 0},
                    {"heading": "Methods", "level": 1, "page": 2, "order": 1},
                ],
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_records

        result = await section_service.query_entities_in_sections(
            section_headings=["Introduction", "Methods"],
            document_id="doc_123",
        )

        assert len(result.entities) == 1
        assert result.section_filters == ["Introduction", "Methods"]

        # Verify entity has multiple sections
        entity = result.entities[0]
        assert len(entity.sections) == 2
        section_headings = [s.section_heading for s in entity.sections]
        assert "Introduction" in section_headings
        assert "Methods" in section_headings

        # Verify query parameters
        call_args = mock_neo4j_client.execute_read.call_args
        params = call_args[0][1]
        assert params["section_headings"] == ["Introduction", "Methods"]

    @pytest.mark.asyncio
    async def test_query_relationships_in_section(
        self, section_service, mock_neo4j_client, sample_relationship_records
    ):
        """Test querying relationships in a section."""
        mock_neo4j_client.execute_read.return_value = sample_relationship_records

        result = await section_service.query_relationships_in_section(
            section_heading="Methods",
            document_id="doc_123",
        )

        assert len(result.relationships) == 1
        assert len(result.entities) == 0  # Only relationships requested
        assert result.section_filters == ["Methods"]

        # Verify relationship data
        rel = result.relationships[0]
        assert isinstance(rel, RelationshipWithSection)
        assert rel.source_name == "Neural Networks"
        assert rel.target_name == "Deep Learning"
        assert rel.relationship_type == "RELATES_TO"
        assert len(rel.sections) == 1

        # Verify section metadata
        section = rel.sections[0]
        assert section.section_heading == "Methods"
        assert section.section_level == 1

        # Verify query includes CONTAINS_CHUNK relationship
        call_args = mock_neo4j_client.execute_read.call_args
        query = call_args[0][0]
        assert "CONTAINS_CHUNK" in query
        assert "MENTIONED_IN" in query

    @pytest.mark.asyncio
    async def test_query_section_hierarchy(
        self, section_service, mock_neo4j_client, sample_section_hierarchy
    ):
        """Test querying section hierarchy."""
        mock_neo4j_client.execute_read.return_value = sample_section_hierarchy

        sections = await section_service.query_section_hierarchy(
            document_id="doc_123",
            max_level=2,
        )

        assert len(sections) == 2
        assert sections[0]["heading"] == "Introduction"
        assert sections[1]["heading"] == "Methods"

        # Verify query parameters
        call_args = mock_neo4j_client.execute_read.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "HAS_SECTION" in query
        assert params["document_id"] == "doc_123"
        assert params["max_level"] == 2

    @pytest.mark.asyncio
    async def test_query_section_hierarchy_all_levels(
        self, section_service, mock_neo4j_client, sample_section_hierarchy
    ):
        """Test querying section hierarchy without level limit."""
        mock_neo4j_client.execute_read.return_value = sample_section_hierarchy

        sections = await section_service.query_section_hierarchy(
            document_id="doc_123",
        )

        assert len(sections) == 2

        # Verify max_level not in parameters
        call_args = mock_neo4j_client.execute_read.call_args
        params = call_args[0][1]
        assert "max_level" not in params

    @pytest.mark.asyncio
    async def test_get_entity_sections(self, section_service, mock_neo4j_client):
        """Test getting sections for a specific entity."""
        mock_records = [
            {
                "section_heading": "Introduction",
                "section_level": 1,
                "section_page": 1,
                "section_order": 0,
            },
            {
                "section_heading": "Methods",
                "section_level": 1,
                "section_page": 2,
                "section_order": 1,
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_records

        sections = await section_service.get_entity_sections(entity_id="entity-123")

        assert len(sections) == 2
        assert all(isinstance(s, SectionMetadataResult) for s in sections)
        assert sections[0].section_heading == "Introduction"
        assert sections[1].section_heading == "Methods"

        # Verify query uses ID match
        call_args = mock_neo4j_client.execute_read.call_args
        params = call_args[0][1]
        assert params["entity_id"] == "entity-123"

    @pytest.mark.asyncio
    async def test_get_entity_sections_by_name(self, section_service, mock_neo4j_client):
        """Test getting sections by entity name."""
        mock_neo4j_client.execute_read.return_value = []

        await section_service.get_entity_sections(entity_id="Neural Networks")

        # Verify query uses name match
        call_args = mock_neo4j_client.execute_read.call_args
        query = call_args[0][0]
        assert "e.name = $entity_id" in query

    @pytest.mark.asyncio
    async def test_empty_results(self, section_service, mock_neo4j_client):
        """Test handling of empty query results."""
        mock_neo4j_client.execute_read.return_value = []

        result = await section_service.query_entities_in_section(
            section_heading="Nonexistent Section",
        )

        assert len(result.entities) == 0
        assert len(result.relationships) == 0
        assert result.query_time_ms > 0

    @pytest.mark.asyncio
    async def test_performance_target(self, section_service, mock_neo4j_client):
        """Test that section queries meet <100ms performance target."""
        # Simulate realistic Neo4j response time (10-50ms)
        async def mock_execute(*args, **kwargs):
            await AsyncMock(return_value=None)()
            return []

        mock_neo4j_client.execute_read.side_effect = mock_execute

        start = time.perf_counter()
        result = await section_service.query_entities_in_section(
            section_heading="Test Section",
        )
        duration_ms = (time.perf_counter() - start) * 1000

        # Verify performance target
        assert duration_ms < 100, f"Query took {duration_ms:.2f}ms, target is <100ms"
        assert result.query_time_ms < 100

    def test_singleton_pattern(self):
        """Test singleton pattern for service."""
        reset_section_graph_service()

        service1 = get_section_graph_service()
        service2 = get_section_graph_service()

        assert service1 is service2

        reset_section_graph_service()


class TestSectionGraphModels:
    """Test Pydantic models for section graph queries."""

    def test_section_metadata_result_creation(self):
        """Test SectionMetadataResult model."""
        section = SectionMetadataResult(
            section_heading="Introduction",
            section_level=1,
            section_page=1,
            section_order=0,
        )

        assert section.section_heading == "Introduction"
        assert section.section_level == 1
        assert section.section_page == 1
        assert section.section_order == 0

    def test_entity_with_section_creation(self):
        """Test EntityWithSection model."""
        section = SectionMetadataResult(
            section_heading="Methods",
            section_level=1,
        )

        entity = EntityWithSection(
            entity_id="entity-1",
            entity_name="Neural Networks",
            entity_type="CONCEPT",
            description="ML concept",
            sections=[section],
        )

        assert entity.entity_id == "entity-1"
        assert entity.entity_name == "Neural Networks"
        assert len(entity.sections) == 1
        assert entity.sections[0].section_heading == "Methods"

    def test_relationship_with_section_creation(self):
        """Test RelationshipWithSection model."""
        section = SectionMetadataResult(
            section_heading="Results",
            section_level=1,
        )

        rel = RelationshipWithSection(
            source_id="entity-1",
            source_name="Neural Networks",
            target_id="entity-2",
            target_name="Deep Learning",
            relationship_type="RELATES_TO",
            description="Foundation relationship",
            sections=[section],
        )

        assert rel.source_name == "Neural Networks"
        assert rel.target_name == "Deep Learning"
        assert rel.relationship_type == "RELATES_TO"
        assert len(rel.sections) == 1

    def test_section_graph_query_result(self):
        """Test SectionGraphQueryResult model."""
        entity = EntityWithSection(
            entity_id="entity-1",
            entity_name="Test",
            entity_type="CONCEPT",
        )

        result = SectionGraphQueryResult(
            entities=[entity],
            relationships=[],
            query_time_ms=42.5,
            section_filters=["Introduction", "Methods"],
        )

        assert len(result.entities) == 1
        assert len(result.relationships) == 0
        assert result.query_time_ms == 42.5
        assert result.section_filters == ["Introduction", "Methods"]


class TestQueryTemplates:
    """Test section-aware query templates."""

    def test_entities_in_section_template(self):
        """Test entities_in_section query template."""
        from src.components.graph_rag.query_templates import GraphQueryTemplates

        templates = GraphQueryTemplates()
        builder = templates.entities_in_section(
            section_heading="Introduction",
            document_id="doc_123",
            limit=50,
        )

        query_dict = builder.build()
        query = query_dict["query"]
        params = query_dict["parameters"]

        assert "Section" in query
        assert "DEFINES" in query
        assert params["section_heading"] == "Introduction"
        assert params["document_id"] == "doc_123"
        assert "LIMIT 50" in query

    def test_entities_in_sections_template(self):
        """Test entities_in_sections query template."""
        from src.components.graph_rag.query_templates import GraphQueryTemplates

        templates = GraphQueryTemplates()
        builder = templates.entities_in_sections(
            section_headings=["Introduction", "Methods"],
            document_id="doc_123",
        )

        query_dict = builder.build()
        query = query_dict["query"]
        params = query_dict["parameters"]

        assert "Section" in query
        assert "IN $section_headings" in query
        assert params["section_headings"] == ["Introduction", "Methods"]

    def test_section_hierarchy_template(self):
        """Test section_hierarchy query template."""
        from src.components.graph_rag.query_templates import GraphQueryTemplates

        templates = GraphQueryTemplates()
        builder = templates.section_hierarchy(
            document_id="doc_123",
            max_level=3,
        )

        query_dict = builder.build()
        query = query_dict["query"]
        params = query_dict["parameters"]

        assert "HAS_SECTION" in query
        assert params["document_id"] == "doc_123"
        assert params["max_level"] == 3

    def test_entity_sections_template(self):
        """Test entity_sections query template."""
        from src.components.graph_rag.query_templates import GraphQueryTemplates

        templates = GraphQueryTemplates()
        builder = templates.entity_sections(entity_id="entity-123")

        query_dict = builder.build()
        query = query_dict["query"]
        params = query_dict["parameters"]

        assert "DEFINES" in query
        assert "e.id = $entity_id" in query
        assert params["entity_id"] == "entity-123"

    def test_section_entities_count_template(self):
        """Test section_entities_count query template."""
        from src.components.graph_rag.query_templates import GraphQueryTemplates

        templates = GraphQueryTemplates()
        builder = templates.section_entities_count(document_id="doc_123")

        query_dict = builder.build()
        query = query_dict["query"]
        params = query_dict["parameters"]

        assert "count(e)" in query
        assert "DEFINES" in query
        assert params["document_id"] == "doc_123"
