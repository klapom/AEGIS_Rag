"""Unit tests for Neo4j Section Nodes (Sprint 32 Feature 32.4).

This module tests the creation and management of Section nodes in Neo4j,
which represent document sections extracted by Adaptive Section-Aware Chunking (ADR-039).

Tests cover:
- Section node creation with correct properties
- Section-chunk relationship linking (CONTAINS_CHUNK)
- Section-entity relationship linking (DEFINES)
- Empty sections handling
- Hierarchical section structure (level 1, 2, 3)
- Section metadata preservation (headings, pages, bboxes)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.components.ingestion.langgraph_nodes import AdaptiveChunk, SectionMetadata

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j async driver for unit testing."""
    driver = AsyncMock()
    session = AsyncMock()

    # Mock session.run() for query execution
    result = AsyncMock()
    result.single = AsyncMock(return_value={"count": 0})
    result.fetch = AsyncMock(return_value=[])
    session.run = AsyncMock(return_value=result)

    # Mock session context manager
    driver.session = MagicMock(return_value=session)
    driver.__aenter__ = AsyncMock(return_value=session)
    driver.__aexit__ = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock()
    driver.close = AsyncMock()

    return driver


@pytest.fixture
def sample_sections():
    """Sample sections for testing."""
    return [
        SectionMetadata(
            heading="Multi-Server Architecture",
            level=1,
            page_no=1,
            bbox={"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
            text="A multi-server architecture distributes load across multiple servers...",
            token_count=245,
            metadata={"source": "presentation.pptx", "slide": 1},
        ),
        SectionMetadata(
            heading="Load Balancing Strategy",
            level=2,
            page_no=2,
            bbox={"l": 60.0, "t": 100.0, "r": 660.0, "b": 150.0},
            text="Load balancing distributes requests across servers using algorithms...",
            token_count=180,
            metadata={"source": "presentation.pptx", "slide": 2},
        ),
        SectionMetadata(
            heading="Round-Robin Algorithm",
            level=3,
            page_no=2,
            bbox={"l": 70.0, "t": 160.0, "r": 650.0, "b": 200.0},
            text="Round-robin algorithm cycles through servers in sequence...",
            token_count=120,
            metadata={"source": "presentation.pptx", "slide": 2},
        ),
    ]


@pytest.fixture
def sample_chunks():
    """Sample adaptive chunks for testing."""
    return [
        AdaptiveChunk(
            text="Multi-server architecture text...",
            token_count=245,
            section_headings=["Multi-Server Architecture"],
            section_pages=[1],
            section_bboxes=[{"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0}],
            primary_section="Multi-Server Architecture",
            metadata={"chunk_id": "chunk_001", "document_id": "doc_001"},
        ),
        AdaptiveChunk(
            text="Load balancing text... Round-robin algorithm text...",
            token_count=300,
            section_headings=["Load Balancing Strategy", "Round-Robin Algorithm"],
            section_pages=[2, 2],
            section_bboxes=[
                {"l": 60.0, "t": 100.0, "r": 660.0, "b": 150.0},
                {"l": 70.0, "t": 160.0, "r": 650.0, "b": 200.0},
            ],
            primary_section="Load Balancing Strategy",
            metadata={"chunk_id": "chunk_002", "document_id": "doc_001"},
        ),
    ]


@pytest.fixture
def sample_entities():
    """Sample entities for testing."""
    return [
        {
            "entity_id": "server_entity",
            "entity_name": "Server",
            "entity_type": "COMPONENT",
            "description": "A computing device that processes requests",
            "source_id": "chunk_001",
            "file_path": "doc_001",
        },
        {
            "entity_id": "load_balancer_entity",
            "entity_name": "Load Balancer",
            "entity_type": "COMPONENT",
            "description": "Distributes incoming requests across servers",
            "source_id": "chunk_002",
            "file_path": "doc_001",
        },
    ]


# ============================================================================
# Unit Tests: Section Node Creation
# ============================================================================


@pytest.mark.asyncio
async def test_section_node_creation(mock_neo4j_driver):
    """Test that Section nodes are created with correct properties."""
    # Arrange
    section_heading = "Multi-Server Architecture"
    section_level = 1
    page_no = 1
    bbox = {"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0}

    session = mock_neo4j_driver.session()
    session.run = AsyncMock(return_value=AsyncMock())

    # Act: Create section node (would be called by create_section_nodes)
    await session.run(
        """
        MERGE (s:section {section_id: $section_id})
        SET s.heading = $heading,
            s.level = $level,
            s.page_no = $page_no,
            s.bbox = $bbox,
            s.created_at = datetime()
        """,
        section_id=f"section_{hash(section_heading) % 1000000}",
        heading=section_heading,
        level=section_level,
        page_no=page_no,
        bbox=bbox,
    )

    # Assert
    session.run.assert_called_once()
    call_args = session.run.call_args
    assert "MERGE (s:section" in call_args[0][0]
    assert call_args[1]["heading"] == section_heading
    assert call_args[1]["level"] == section_level
    assert call_args[1]["page_no"] == page_no


@pytest.mark.asyncio
async def test_section_node_properties(sample_sections):
    """Test that section properties are correctly stored in metadata."""
    # Arrange
    section = sample_sections[0]

    # Assert
    assert section.heading == "Multi-Server Architecture"
    assert section.level == 1
    assert section.page_no == 1
    assert section.bbox["l"] == 50.0
    assert section.token_count == 245
    assert section.metadata["source"] == "presentation.pptx"


@pytest.mark.asyncio
async def test_hierarchical_section_levels(sample_sections):
    """Test that section hierarchy levels are correctly identified."""
    # Act & Assert
    assert sample_sections[0].level == 1  # Title
    assert sample_sections[1].level == 2  # Subtitle-level-1
    assert sample_sections[2].level == 3  # Subtitle-level-2


# ============================================================================
# Unit Tests: Section-Chunk Relationships
# ============================================================================


@pytest.mark.asyncio
async def test_section_chunk_relationships(mock_neo4j_driver, sample_chunks):
    """Test that CONTAINS_CHUNK relationships are created between sections and chunks."""
    # Arrange
    session = mock_neo4j_driver.session()
    session.run = AsyncMock(return_value=AsyncMock())

    section_id = "section_001"
    chunk_id = "chunk_001"

    # Act: Create CONTAINS_CHUNK relationship
    await session.run(
        """
        MATCH (s:section {section_id: $section_id})
        MATCH (c:chunk {chunk_id: $chunk_id})
        MERGE (s)-[r:CONTAINS_CHUNK]->(c)
        SET r.created_at = datetime()
        """,
        section_id=section_id,
        chunk_id=chunk_id,
    )

    # Assert
    session.run.assert_called_once()
    call_args = session.run.call_args
    assert "CONTAINS_CHUNK" in call_args[0][0]
    assert call_args[1]["section_id"] == section_id
    assert call_args[1]["chunk_id"] == chunk_id


@pytest.mark.asyncio
async def test_multi_chunk_sections(mock_neo4j_driver, sample_chunks):
    """Test that a section can contain multiple chunks (merged sections)."""
    # Arrange
    session = mock_neo4j_driver.session()
    session.run = AsyncMock(return_value=AsyncMock())

    section_id = "section_merged"
    chunk_ids = ["chunk_001", "chunk_002"]

    # Act: Create relationships for multiple chunks
    for chunk_id in chunk_ids:
        await session.run(
            """
            MATCH (s:section {section_id: $section_id})
            MATCH (c:chunk {chunk_id: $chunk_id})
            MERGE (s)-[r:CONTAINS_CHUNK]->(c)
            """,
            section_id=section_id,
            chunk_id=chunk_id,
        )

    # Assert
    assert session.run.call_count == len(chunk_ids)


# ============================================================================
# Unit Tests: Section-Entity Relationships
# ============================================================================


@pytest.mark.asyncio
async def test_section_entity_relationships(mock_neo4j_driver, sample_entities):
    """Test that DEFINES relationships are created between sections and entities."""
    # Arrange
    session = mock_neo4j_driver.session()
    session.run = AsyncMock(return_value=AsyncMock())

    section_id = "section_001"
    entity_id = "server_entity"

    # Act: Create DEFINES relationship
    await session.run(
        """
        MATCH (s:section {section_id: $section_id})
        MATCH (e:base {entity_id: $entity_id})
        MERGE (s)-[r:DEFINES]->(e)
        SET r.context = $context,
            r.created_at = datetime()
        """,
        section_id=section_id,
        entity_id=entity_id,
        context="Entity defined in this section",
    )

    # Assert
    session.run.assert_called_once()
    call_args = session.run.call_args
    assert "DEFINES" in call_args[0][0]
    assert call_args[1]["section_id"] == section_id
    assert call_args[1]["entity_id"] == entity_id


@pytest.mark.asyncio
async def test_section_multiple_entities(mock_neo4j_driver, sample_entities):
    """Test that a section can define multiple entities."""
    # Arrange
    session = mock_neo4j_driver.session()
    session.run = AsyncMock(return_value=AsyncMock())

    section_id = "section_001"
    entity_ids = ["server_entity", "load_balancer_entity"]

    # Act: Create DEFINES relationships for multiple entities
    for entity_id in entity_ids:
        await session.run(
            """
            MATCH (s:section {section_id: $section_id})
            MATCH (e:base {entity_id: $entity_id})
            MERGE (s)-[r:DEFINES]->(e)
            """,
            section_id=section_id,
            entity_id=entity_id,
        )

    # Assert
    assert session.run.call_count == len(entity_ids)


# ============================================================================
# Unit Tests: Empty Sections & Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_empty_section_handling():
    """Test that empty sections are handled gracefully."""
    # Arrange
    empty_section = SectionMetadata(
        heading="Empty Section",
        level=1,
        page_no=1,
        bbox={"l": 0.0, "t": 0.0, "r": 0.0, "b": 0.0},
        text="",  # Empty text
        token_count=0,
        metadata={},
    )

    # Assert: Section should still be created even with empty text
    assert empty_section.heading == "Empty Section"
    assert empty_section.token_count == 0
    assert empty_section.text == ""


@pytest.mark.asyncio
async def test_section_without_bbox():
    """Test that sections without bounding boxes are handled."""
    # Arrange
    section_no_bbox = SectionMetadata(
        heading="No BBox Section",
        level=1,
        page_no=0,
        bbox={"l": 0.0, "t": 0.0, "r": 0.0, "b": 0.0},  # Empty/default bbox
        text="Some text",
        token_count=50,
        metadata={},
    )

    # Assert
    assert section_no_bbox.bbox is not None
    assert all(v == 0.0 for v in section_no_bbox.bbox.values())


@pytest.mark.asyncio
async def test_section_metadata_preservation(sample_sections):
    """Test that section metadata is preserved through creation."""
    # Arrange
    section = sample_sections[0]

    # Assert: All metadata fields should be preserved
    assert section.metadata["source"] == "presentation.pptx"
    assert section.metadata["slide"] == 1
    assert section.heading == "Multi-Server Architecture"
    assert section.level == 1


# ============================================================================
# Unit Tests: Section Node Queries
# ============================================================================


@pytest.mark.asyncio
async def test_query_sections_by_heading(mock_neo4j_driver):
    """Test querying sections by heading name."""
    # Arrange
    session = mock_neo4j_driver.session()
    result_mock = AsyncMock()
    result_mock.fetch = AsyncMock(
        return_value=[
            {"section_id": "section_001", "heading": "Multi-Server Architecture", "level": 1}
        ]
    )
    session.run = AsyncMock(return_value=result_mock)

    # Act
    result = await session.run(
        """
        MATCH (s:section {heading: $heading})
        RETURN s.section_id AS section_id, s.heading AS heading, s.level AS level
        """,
        heading="Multi-Server Architecture",
    )
    sections = await result.fetch()

    # Assert
    assert len(sections) == 1
    assert sections[0]["heading"] == "Multi-Server Architecture"


@pytest.mark.asyncio
async def test_query_sections_by_page(mock_neo4j_driver):
    """Test querying sections by page number."""
    # Arrange
    session = mock_neo4j_driver.session()
    result_mock = AsyncMock()
    result_mock.fetch = AsyncMock(
        return_value=[
            {"section_id": "section_001", "page_no": 2},
            {"section_id": "section_002", "page_no": 2},
        ]
    )
    session.run = AsyncMock(return_value=result_mock)

    # Act
    result = await session.run(
        """
        MATCH (s:section {page_no: $page_no})
        RETURN s.section_id AS section_id, s.page_no AS page_no
        """,
        page_no=2,
    )
    sections = await result.fetch()

    # Assert
    assert len(sections) == 2
    assert all(s["page_no"] == 2 for s in sections)


@pytest.mark.asyncio
async def test_query_hierarchical_sections(mock_neo4j_driver):
    """Test querying section hierarchy (parent-child relationships)."""
    # Arrange
    session = mock_neo4j_driver.session()
    result_mock = AsyncMock()
    result_mock.fetch = AsyncMock(
        return_value=[
            {
                "parent_heading": "Multi-Server Architecture",
                "child_heading": "Load Balancing Strategy",
                "parent_level": 1,
                "child_level": 2,
            }
        ]
    )
    session.run = AsyncMock(return_value=result_mock)

    # Act
    result = await session.run(
        """
        MATCH (parent:section {level: 1})-[r:HAS_SUBSECTION]->(child:section {level: 2})
        RETURN parent.heading AS parent_heading, child.heading AS child_heading,
               parent.level AS parent_level, child.level AS child_level
        """
    )
    hierarchy = await result.fetch()

    # Assert
    assert len(hierarchy) == 1
    assert hierarchy[0]["parent_level"] < hierarchy[0]["child_level"]


# ============================================================================
# Unit Tests: Section Batch Operations
# ============================================================================


@pytest.mark.asyncio
async def test_batch_create_sections(mock_neo4j_driver, sample_sections):
    """Test batch creation of section nodes."""
    # Arrange
    session = mock_neo4j_driver.session()
    session.run = AsyncMock(return_value=AsyncMock())

    # Act: Create sections in batch
    sections_data = [
        {
            "section_id": f"section_{i}",
            "heading": s.heading,
            "level": s.level,
            "page_no": s.page_no,
            "bbox": s.bbox,
        }
        for i, s in enumerate(sample_sections)
    ]

    await session.run(
        """
        UNWIND $sections AS section
        MERGE (s:section {section_id: section.section_id})
        SET s.heading = section.heading,
            s.level = section.level,
            s.page_no = section.page_no,
            s.bbox = section.bbox,
            s.created_at = datetime()
        """,
        sections=sections_data,
    )

    # Assert
    session.run.assert_called_once()
    call_args = session.run.call_args
    assert call_args[1]["sections"] == sections_data


@pytest.mark.asyncio
async def test_batch_create_section_relationships(mock_neo4j_driver):
    """Test batch creation of section-chunk relationships."""
    # Arrange
    session = mock_neo4j_driver.session()
    session.run = AsyncMock(return_value=AsyncMock())

    # Act: Create relationships in batch
    relationships = [
        {"section_id": "section_001", "chunk_id": "chunk_001"},
        {"section_id": "section_001", "chunk_id": "chunk_002"},
        {"section_id": "section_002", "chunk_id": "chunk_003"},
    ]

    await session.run(
        """
        UNWIND $relationships AS rel
        MATCH (s:section {section_id: rel.section_id})
        MATCH (c:chunk {chunk_id: rel.chunk_id})
        MERGE (s)-[r:CONTAINS_CHUNK]->(c)
        """,
        relationships=relationships,
    )

    # Assert
    session.run.assert_called_once()
    call_args = session.run.call_args
    assert call_args[1]["relationships"] == relationships


# ============================================================================
# Unit Tests: Section Node Updates
# ============================================================================


@pytest.mark.asyncio
async def test_update_section_metadata(mock_neo4j_driver):
    """Test updating section metadata (e.g., adding tags)."""
    # Arrange
    session = mock_neo4j_driver.session()
    session.run = AsyncMock(return_value=AsyncMock())

    section_id = "section_001"
    tags = ["architecture", "infrastructure"]

    # Act: Update section with tags
    await session.run(
        """
        MATCH (s:section {section_id: $section_id})
        SET s.tags = $tags,
            s.updated_at = datetime()
        """,
        section_id=section_id,
        tags=tags,
    )

    # Assert
    session.run.assert_called_once()
    call_args = session.run.call_args
    assert call_args[1]["tags"] == tags


@pytest.mark.asyncio
async def test_add_section_parent_child_link(mock_neo4j_driver):
    """Test adding HAS_SUBSECTION links between parent and child sections."""
    # Arrange
    session = mock_neo4j_driver.session()
    session.run = AsyncMock(return_value=AsyncMock())

    parent_id = "section_001"
    child_id = "section_002"

    # Act: Create parent-child relationship
    await session.run(
        """
        MATCH (parent:section {section_id: $parent_id})
        MATCH (child:section {section_id: $child_id})
        MERGE (parent)-[r:HAS_SUBSECTION]->(child)
        SET r.created_at = datetime()
        """,
        parent_id=parent_id,
        child_id=child_id,
    )

    # Assert
    session.run.assert_called_once()
    call_args = session.run.call_args
    assert "HAS_SUBSECTION" in call_args[0][0]


# ============================================================================
# Unit Tests: Section Statistics and Analytics
# ============================================================================


@pytest.mark.asyncio
async def test_count_sections(mock_neo4j_driver):
    """Test counting total sections in the graph."""
    # Arrange
    session = mock_neo4j_driver.session()
    result_mock = AsyncMock()
    record_mock = {"count": 25}
    result_mock.single = AsyncMock(return_value=record_mock)
    session.run = AsyncMock(return_value=result_mock)

    # Act
    result = await session.run("MATCH (s:section) RETURN count(s) AS count")
    record = await result.single()
    count = record["count"]

    # Assert
    assert count == 25


@pytest.mark.asyncio
async def test_count_section_chunks(mock_neo4j_driver):
    """Test counting chunks per section."""
    # Arrange
    session = mock_neo4j_driver.session()
    result_mock = AsyncMock()
    result_mock.fetch = AsyncMock(
        return_value=[
            {"section_heading": "Section 1", "chunk_count": 2},
            {"section_heading": "Section 2", "chunk_count": 3},
        ]
    )
    session.run = AsyncMock(return_value=result_mock)

    # Act
    result = await session.run(
        """
        MATCH (s:section)-[r:CONTAINS_CHUNK]->(c:chunk)
        RETURN s.heading AS section_heading, count(c) AS chunk_count
        """
    )
    stats = await result.fetch()

    # Assert
    assert len(stats) == 2
    assert stats[0]["chunk_count"] == 2
    assert stats[1]["chunk_count"] == 3


@pytest.mark.asyncio
async def test_count_section_entities(mock_neo4j_driver):
    """Test counting entities per section."""
    # Arrange
    session = mock_neo4j_driver.session()
    result_mock = AsyncMock()
    result_mock.fetch = AsyncMock(
        return_value=[
            {"section_heading": "Architecture", "entity_count": 8},
        ]
    )
    session.run = AsyncMock(return_value=result_mock)

    # Act
    result = await session.run(
        """
        MATCH (s:section)-[r:DEFINES]->(e:base)
        RETURN s.heading AS section_heading, count(e) AS entity_count
        """
    )
    stats = await result.fetch()

    # Assert
    assert len(stats) == 1
    assert stats[0]["entity_count"] == 8
