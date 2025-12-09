"""Unit tests for Section Extraction (Sprint 32 Feature 32.1).

Tests cover:
- Section hierarchy extraction from DoclingDocument
- Heading level mapping (title, subtitle-level-1, subtitle-level-2)
- Bounding box extraction
- Token counting
- Edge cases (empty sections, no body, None document)
"""

from unittest.mock import Mock

import pytest

from src.components.ingestion.langgraph_nodes import SectionMetadata
from src.components.ingestion.section_extraction import (
    _get_heading_level,
    extract_section_hierarchy,
)

# =============================================================================
# TEST: HEADING LEVEL MAPPING
# =============================================================================


def test_get_heading_level__title__returns_level_1():
    """Test that 'title' maps to level 1."""
    assert _get_heading_level("title") == 1


def test_get_heading_level__subtitle_level_1__returns_level_2():
    """Test that 'subtitle-level-1' maps to level 2."""
    assert _get_heading_level("subtitle-level-1") == 2


def test_get_heading_level__subtitle_level_2__returns_level_3():
    """Test that 'subtitle-level-2' maps to level 3."""
    assert _get_heading_level("subtitle-level-2") == 3


def test_get_heading_level__unknown_type__returns_level_1():
    """Test that unknown heading type defaults to level 1."""
    assert _get_heading_level("unknown-heading") == 1
    assert _get_heading_level("") == 1


# =============================================================================
# TEST: SECTION HIERARCHY EXTRACTION - POWERPOINT
# =============================================================================


@pytest.fixture
def mock_powerpoint_document():
    """Create mock DoclingDocument for PowerPoint with 3 slides."""
    doc = Mock()

    # Slide 1: Title slide
    slide1_heading = Mock()
    slide1_heading.label = Mock()
    slide1_heading.label.value = "title"
    slide1_heading.text = "Multi-Server Architecture"
    slide1_heading.prov = [Mock()]
    slide1_heading.prov[0].page_no = 1
    slide1_heading.prov[0].bbox = Mock()
    slide1_heading.prov[0].bbox.l = 50.0
    slide1_heading.prov[0].bbox.t = 30.0
    slide1_heading.prov[0].bbox.r = 670.0
    slide1_heading.prov[0].bbox.b = 80.0
    slide1_heading.children = []

    slide1_text = Mock()
    slide1_text.label = Mock()
    slide1_text.label.value = "text"
    slide1_text.text = "A multi-server architecture distributes load across multiple servers."
    slide1_text.prov = []
    slide1_text.children = []

    # Slide 2: Subtitle slide
    slide2_heading = Mock()
    slide2_heading.label = Mock()
    slide2_heading.label.value = "subtitle-level-1"
    slide2_heading.text = "Load Balancing Strategies"
    slide2_heading.prov = [Mock()]
    slide2_heading.prov[0].page_no = 2
    slide2_heading.prov[0].bbox = Mock()
    slide2_heading.prov[0].bbox.l = 50.0
    slide2_heading.prov[0].bbox.t = 30.0
    slide2_heading.prov[0].bbox.r = 670.0
    slide2_heading.prov[0].bbox.b = 80.0
    slide2_heading.children = []

    slide2_text = Mock()
    slide2_text.label = Mock()
    slide2_text.label.value = "text"
    slide2_text.text = "Round-robin algorithm distributes requests evenly across servers."
    slide2_text.prov = []
    slide2_text.children = []

    # Slide 3: Another subtitle
    slide3_heading = Mock()
    slide3_heading.label = Mock()
    slide3_heading.label.value = "subtitle-level-2"
    slide3_heading.text = "Caching Optimization"
    slide3_heading.prov = [Mock()]
    slide3_heading.prov[0].page_no = 3
    slide3_heading.prov[0].bbox = Mock()
    slide3_heading.prov[0].bbox.l = 50.0
    slide3_heading.prov[0].bbox.t = 30.0
    slide3_heading.prov[0].bbox.r = 670.0
    slide3_heading.prov[0].bbox.b = 80.0
    slide3_heading.children = []

    slide3_text = Mock()
    slide3_text.label = Mock()
    slide3_text.label.value = "text"
    slide3_text.text = "Redis caching reduces database load by 80%."
    slide3_text.prov = []
    slide3_text.children = []

    # Document body (flat structure for PowerPoint)
    doc.body = Mock()
    doc.body.children = [
        slide1_heading,
        slide1_text,
        slide2_heading,
        slide2_text,
        slide3_heading,
        slide3_text,
    ]

    return doc


def test_extract_sections_from_docling_json__powerpoint__extracts_all_sections(
    mock_powerpoint_document,
):
    """Test extraction of all sections from PowerPoint document."""
    sections = extract_section_hierarchy(mock_powerpoint_document, SectionMetadata)

    # Should extract 3 sections (1 per slide)
    assert len(sections) == 3

    # Verify first section (slide 1)
    section1 = sections[0]
    assert section1.heading == "Multi-Server Architecture"
    assert section1.level == 1  # title
    assert section1.page_no == 1
    assert section1.bbox == {"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0}
    assert "multi-server architecture" in section1.text.lower()
    assert section1.token_count > 0

    # Verify second section (slide 2)
    section2 = sections[1]
    assert section2.heading == "Load Balancing Strategies"
    assert section2.level == 2  # subtitle-level-1
    assert section2.page_no == 2
    assert "round-robin" in section2.text.lower()

    # Verify third section (slide 3)
    section3 = sections[2]
    assert section3.heading == "Caching Optimization"
    assert section3.level == 3  # subtitle-level-2
    assert section3.page_no == 3
    assert "redis" in section3.text.lower()


def test_section_hierarchy_levels__powerpoint__validates_levels(mock_powerpoint_document):
    """Test that heading levels are correctly assigned."""
    sections = extract_section_hierarchy(mock_powerpoint_document, SectionMetadata)

    assert sections[0].level == 1  # title
    assert sections[1].level == 2  # subtitle-level-1
    assert sections[2].level == 3  # subtitle-level-2


def test_bbox_extraction__powerpoint__extracts_coordinates(mock_powerpoint_document):
    """Test that bounding box coordinates are extracted correctly."""
    sections = extract_section_hierarchy(mock_powerpoint_document, SectionMetadata)

    for section in sections:
        assert "l" in section.bbox
        assert "t" in section.bbox
        assert "r" in section.bbox
        assert "b" in section.bbox
        assert section.bbox["l"] == 50.0
        assert section.bbox["t"] == 30.0
        assert section.bbox["r"] == 670.0
        assert section.bbox["b"] == 80.0


# =============================================================================
# TEST: EDGE CASES
# =============================================================================


def test_extract_sections__empty_document__returns_empty_list():
    """Test extraction from document with no sections."""
    doc = Mock()
    doc.body = Mock()
    doc.body.children = []

    sections = extract_section_hierarchy(doc, SectionMetadata)

    assert sections == []


def test_extract_sections__none_document__raises_value_error():
    """Test that None document raises ValueError."""
    with pytest.raises(ValueError, match="docling_document is None"):
        extract_section_hierarchy(None, SectionMetadata)


def test_extract_sections__no_body__returns_empty_list():
    """Test extraction from document with no body."""
    doc = Mock()
    doc.body = None

    sections = extract_section_hierarchy(doc, SectionMetadata)

    assert sections == []


def test_extract_sections__section_without_provenance__uses_defaults():
    """Test that sections without provenance use default values."""
    doc = Mock()

    # Heading with no provenance
    heading = Mock()
    heading.label = Mock()
    heading.label.value = "title"
    heading.text = "Test Heading"
    heading.prov = []  # No provenance
    heading.children = []

    text_node = Mock()
    text_node.label = Mock()
    text_node.label.value = "text"
    text_node.text = "Test content"
    text_node.prov = []
    text_node.children = []

    doc.body = Mock()
    doc.body.children = [heading, text_node]

    sections = extract_section_hierarchy(doc, SectionMetadata)

    assert len(sections) == 1
    assert sections[0].page_no == 0  # Default
    assert sections[0].bbox == {"l": 0.0, "t": 0.0, "r": 0.0, "b": 0.0}  # Default


def test_extract_sections__empty_section_text__creates_section():
    """Test that sections with no body text are still created."""
    doc = Mock()

    # Heading with no body text
    heading = Mock()
    heading.label = Mock()
    heading.label.value = "title"
    heading.text = "Empty Section"
    heading.prov = [Mock()]
    heading.prov[0].page_no = 1
    heading.prov[0].bbox = Mock()
    heading.prov[0].bbox.l = 50.0
    heading.prov[0].bbox.t = 30.0
    heading.prov[0].bbox.r = 670.0
    heading.prov[0].bbox.b = 80.0
    heading.children = []

    # Another heading (no text in between)
    heading2 = Mock()
    heading2.label = Mock()
    heading2.label.value = "subtitle-level-1"
    heading2.text = "Another Section"
    heading2.prov = [Mock()]
    heading2.prov[0].page_no = 2
    heading2.prov[0].bbox = Mock()
    heading2.prov[0].bbox.l = 50.0
    heading2.prov[0].bbox.t = 30.0
    heading2.prov[0].bbox.r = 670.0
    heading2.prov[0].bbox.b = 80.0
    heading2.children = []

    doc.body = Mock()
    doc.body.children = [heading, heading2]

    sections = extract_section_hierarchy(doc, SectionMetadata)

    assert len(sections) == 2
    assert sections[0].text == ""  # No body text
    assert sections[0].token_count == 0  # Empty section has 0 tokens


# =============================================================================
# TEST: NESTED STRUCTURES (PDF-like hierarchies)
# =============================================================================


@pytest.fixture
def mock_nested_document():
    """Create mock DoclingDocument with nested structure (like PDF)."""
    doc = Mock()

    # H1: Chapter heading
    chapter_heading = Mock()
    chapter_heading.label = Mock()
    chapter_heading.label.value = "title"
    chapter_heading.text = "Chapter 1: Introduction"
    chapter_heading.prov = [Mock()]
    chapter_heading.prov[0].page_no = 1
    chapter_heading.prov[0].bbox = Mock()
    chapter_heading.prov[0].bbox.l = 50.0
    chapter_heading.prov[0].bbox.t = 30.0
    chapter_heading.prov[0].bbox.r = 550.0
    chapter_heading.prov[0].bbox.b = 80.0

    # H2: Section heading (nested under chapter)
    section_heading = Mock()
    section_heading.label = Mock()
    section_heading.label.value = "subtitle-level-1"
    section_heading.text = "1.1 Background"
    section_heading.prov = [Mock()]
    section_heading.prov[0].page_no = 2
    section_heading.prov[0].bbox = Mock()
    section_heading.prov[0].bbox.l = 70.0
    section_heading.prov[0].bbox.t = 100.0
    section_heading.prov[0].bbox.r = 550.0
    section_heading.prov[0].bbox.b = 130.0
    section_heading.children = []

    # Body text under section
    text_node = Mock()
    text_node.label = Mock()
    text_node.label.value = "text"
    text_node.text = "This section provides background on the topic."
    text_node.prov = []
    text_node.children = []

    # Nest section under chapter
    chapter_heading.children = [section_heading, text_node]

    doc.body = Mock()
    doc.body.children = [chapter_heading]

    return doc


def test_extract_sections__nested_structure__extracts_all_levels(mock_nested_document):
    """Test extraction from nested document structure (PDF-like)."""
    sections = extract_section_hierarchy(mock_nested_document, SectionMetadata)

    # Should extract 2 sections (H1 and H2)
    assert len(sections) == 2

    # Verify H1 (chapter)
    assert sections[0].heading == "Chapter 1: Introduction"
    assert sections[0].level == 1
    assert sections[0].page_no == 1

    # Verify H2 (section)
    assert sections[1].heading == "1.1 Background"
    assert sections[1].level == 2
    assert sections[1].page_no == 2
    assert "background" in sections[1].text.lower()


# =============================================================================
# TEST: TOKEN COUNTING
# =============================================================================


def test_extract_sections__token_count__counts_correctly(mock_powerpoint_document):
    """Test that token counts are calculated for each section."""
    sections = extract_section_hierarchy(mock_powerpoint_document, SectionMetadata)

    for section in sections:
        # All sections should have token counts > 0
        assert section.token_count > 0
        # Token count should be reasonable (not more than text length)
        assert section.token_count <= len(section.text)


# =============================================================================
# TEST: LABEL VARIATIONS (string vs enum)
# =============================================================================


def test_extract_sections__label_as_string__extracts_correctly():
    """Test extraction when label is a plain string."""
    doc = Mock()

    heading = Mock()
    heading.label = "title"  # Plain string (not enum)
    heading.text = "Test Heading"
    heading.prov = [Mock()]
    heading.prov[0].page_no = 1
    heading.prov[0].bbox = Mock()
    heading.prov[0].bbox.l = 50.0
    heading.prov[0].bbox.t = 30.0
    heading.prov[0].bbox.r = 670.0
    heading.prov[0].bbox.b = 80.0
    heading.children = []

    text_node = Mock()
    text_node.label = "text"
    text_node.text = "Test content"
    text_node.prov = []
    text_node.children = []

    doc.body = Mock()
    doc.body.children = [heading, text_node]

    sections = extract_section_hierarchy(doc, SectionMetadata)

    assert len(sections) == 1
    assert sections[0].heading == "Test Heading"
    assert sections[0].level == 1


def test_extract_sections__label_as_enum__extracts_correctly():
    """Test extraction when label is an enum with .value attribute."""
    doc = Mock()

    heading = Mock()
    heading.label = Mock()
    heading.label.value = "subtitle-level-1"  # Enum with .value
    heading.text = "Test Heading"
    heading.prov = [Mock()]
    heading.prov[0].page_no = 1
    heading.prov[0].bbox = Mock()
    heading.prov[0].bbox.l = 50.0
    heading.prov[0].bbox.t = 30.0
    heading.prov[0].bbox.r = 670.0
    heading.prov[0].bbox.b = 80.0
    heading.children = []

    text_node = Mock()
    text_node.label = Mock()
    text_node.label.value = "text"
    text_node.text = "Test content"
    text_node.prov = []
    text_node.children = []

    doc.body = Mock()
    doc.body.children = [heading, text_node]

    sections = extract_section_hierarchy(doc, SectionMetadata)

    assert len(sections) == 1
    assert sections[0].heading == "Test Heading"
    assert sections[0].level == 2  # subtitle-level-1 → level 2
