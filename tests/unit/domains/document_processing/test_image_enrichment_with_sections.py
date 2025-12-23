"""Integration tests for Image Enrichment Node with Section Tracking - Feature 62.3.

Tests cover:
- Section mapping from chunks
- Image-to-section association
- Complete enrichment pipeline with sections
- Error handling in section detection
- Batch image processing with sections
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.components.ingestion.nodes.image_enrichment_with_sections import (
    image_enrichment_node_with_sections,
    _build_section_map_from_chunks,
    _identify_image_section,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_chunk():
    """Create a mock Chunk object with section metadata."""

    class MockChunk:
        def __init__(self, section_id, section_heading, section_level, pages):
            self.metadata = {
                "section_id": section_id,
                "section_heading": section_heading,
                "section_level": section_level,
                "pages": pages,
            }

    return MockChunk


@pytest.fixture
def mock_picture_item():
    """Create a mock picture item from DoclingDocument."""
    item = MagicMock()
    item.get_image = MagicMock(return_value=MagicMock(size=(500, 500)))
    item.prov = [MagicMock()]
    item.prov[0].page_no = 5
    item.prov[0].bbox = MagicMock()
    item.prov[0].bbox.l = 10
    item.prov[0].bbox.t = 20
    item.prov[0].bbox.r = 100
    item.prov[0].bbox.b = 200
    item.prov[0].bbox.coord_origin = MagicMock(value="top-left")
    item.caption = None
    item.text = ""
    return item


@pytest.fixture
def mock_document(mock_picture_item):
    """Create a mock DoclingDocument."""
    doc = MagicMock()
    doc.pictures = [mock_picture_item]
    return doc


@pytest.fixture
def ingestion_state_with_document(mock_document):
    """Create a mock IngestionState with document."""
    return {
        "document_id": "doc_001",
        "document": mock_document,
        "chunks": [],
        "page_dimensions": {5: {"width": 800, "height": 600}},
        "enrichment_status": "pending",
        "vlm_metadata": [],
        "overall_progress": 0.0,
    }


@pytest.fixture
def section_map():
    """Create a section map for testing."""
    return {
        1: {"section_id": "section_1", "section_heading": "Introduction", "section_level": 1},
        5: {
            "section_id": "section_3.2",
            "section_heading": "Multi-Server Architecture",
            "section_level": 2,
        },
        10: {"section_id": "section_5", "section_heading": "Conclusion", "section_level": 1},
    }


# =============================================================================
# Tests: Section Map Building
# =============================================================================


class TestSectionMapBuilding:
    """Test building section maps from chunks."""

    def test_build_section_map_single_chunk(self, mock_chunk):
        """Test building section map from a single chunk."""
        chunks = [mock_chunk("section_1", "Introduction", 1, [1, 2, 3])]

        section_map = _build_section_map_from_chunks(chunks)

        assert 1 in section_map
        assert 2 in section_map
        assert 3 in section_map
        assert section_map[1]["section_id"] == "section_1"
        assert section_map[1]["section_heading"] == "Introduction"

    def test_build_section_map_multiple_chunks(self, mock_chunk):
        """Test building section map from multiple chunks."""
        chunks = [
            mock_chunk("section_1", "Introduction", 1, [1, 2]),
            mock_chunk("section_2", "Architecture", 2, [3, 4, 5]),
            mock_chunk("section_3", "Conclusion", 1, [6]),
        ]

        section_map = _build_section_map_from_chunks(chunks)

        assert len(section_map) == 6
        assert section_map[1]["section_id"] == "section_1"
        assert section_map[3]["section_id"] == "section_2"
        assert section_map[6]["section_id"] == "section_3"

    def test_build_section_map_overlapping_pages(self, mock_chunk):
        """Test section map building with overlapping page numbers."""
        chunks = [
            mock_chunk("section_1", "Intro", 1, [1, 2, 3]),
            mock_chunk("section_2", "Main", 1, [3, 4, 5]),  # Overlaps at page 3
        ]

        section_map = _build_section_map_from_chunks(chunks)

        # Page 3 should map to the last chunk processed (section_2)
        assert section_map[3]["section_id"] == "section_2"

    def test_build_section_map_missing_metadata(self):
        """Test section map building with chunks missing metadata."""
        chunk = MagicMock()
        chunk.metadata = None

        section_map = _build_section_map_from_chunks([chunk])

        assert section_map == {}

    def test_build_section_map_missing_pages(self):
        """Test section map with missing pages in metadata."""
        chunk = MagicMock()
        chunk.metadata = {
            "section_id": "section_1",
            "section_heading": "Intro",
            "section_level": 1,
            # pages is missing
        }

        section_map = _build_section_map_from_chunks([chunk])

        # Should still create map if fallback works
        assert isinstance(section_map, dict)

    def test_build_section_map_empty_chunks(self):
        """Test section map building with empty chunk list."""
        section_map = _build_section_map_from_chunks([])

        assert section_map == {}


# =============================================================================
# Tests: Image Section Identification
# =============================================================================


class TestIdentifyImageSection:
    """Test identifying which section an image belongs to."""

    def test_identify_exact_page_match(self, section_map):
        """Test identifying section with exact page match."""
        section_info = _identify_image_section(5, section_map)

        assert section_info["section_id"] == "section_3.2"
        assert section_info["section_heading"] == "Multi-Server Architecture"
        assert section_info["section_level"] == 2

    def test_identify_section_backward_search(self, section_map):
        """Test identifying section with backward search (no exact match)."""
        section_info = _identify_image_section(7, section_map)

        # Should find section_3.2 from page 5
        assert section_info["section_id"] == "section_3.2"
        assert section_info["section_heading"] == "Multi-Server Architecture"

    def test_identify_section_no_match(self, section_map):
        """Test identifying section when no section found."""
        empty_map = {}
        section_info = _identify_image_section(5, empty_map)

        assert section_info["section_id"] == "unknown"
        assert section_info["section_heading"] == "Unknown Section"
        assert section_info["section_level"] == 0

    def test_identify_section_none_page(self, section_map):
        """Test identifying section with None page number."""
        section_info = _identify_image_section(None, section_map)

        assert section_info["section_id"] == "unknown"
        assert section_info["section_heading"] == "Unknown Section"

    def test_identify_section_first_page(self, section_map):
        """Test identifying section on first page."""
        section_info = _identify_image_section(1, section_map)

        assert section_info["section_id"] == "section_1"
        assert section_info["section_heading"] == "Introduction"

    def test_identify_section_large_page_number(self, section_map):
        """Test identifying section with large page number."""
        section_info = _identify_image_section(100, section_map)

        # Should find closest section backward (conclusion at page 10)
        assert section_info["section_id"] == "section_5"


# =============================================================================
# Tests: Image Enrichment Node with Sections
# =============================================================================


class TestImageEnrichmentNodeWithSections:
    """Test the image enrichment node with section integration."""

    @pytest.mark.asyncio
    async def test_enrichment_node_success(self, ingestion_state_with_document):
        """Test successful enrichment with section metadata."""
        with patch(
            "src.components.ingestion.nodes.image_enrichment_with_sections.ImageProcessor"
        ) as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_image = AsyncMock(return_value="Image description")
            mock_processor.cleanup = MagicMock()
            mock_processor_class.return_value = mock_processor

            state = await image_enrichment_node_with_sections(ingestion_state_with_document)

            assert state["enrichment_status"] == "completed"
            assert len(state["vlm_metadata"]) > 0
            assert state["document"] is not None

    @pytest.mark.asyncio
    async def test_enrichment_with_section_metadata(
        self, ingestion_state_with_document, mock_chunk
    ):
        """Test enrichment preserves section metadata."""
        # Add chunk with section info
        chunk = mock_chunk("section_3.2", "Multi-Server Architecture", 2, [5])
        ingestion_state_with_document["chunks"] = [chunk]

        with patch(
            "src.components.ingestion.nodes.image_enrichment_with_sections.ImageProcessor"
        ) as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_image = AsyncMock(return_value="Architecture diagram")
            mock_processor.cleanup = MagicMock()
            mock_processor_class.return_value = mock_processor

            state = await image_enrichment_node_with_sections(ingestion_state_with_document)

            assert len(state["vlm_metadata"]) == 1
            vlm_metadata = state["vlm_metadata"][0]
            assert vlm_metadata["section_id"] == "section_3.2"
            assert vlm_metadata["section_heading"] == "Multi-Server Architecture"
            assert vlm_metadata["section_level"] == 2

    @pytest.mark.asyncio
    async def test_enrichment_no_document(self):
        """Test enrichment skips when no document."""
        state = {
            "document_id": "doc_001",
            "document": None,
            "enrichment_status": "pending",
        }

        result = await image_enrichment_node_with_sections(state)

        assert result["enrichment_status"] == "skipped"
        assert result["vlm_metadata"] == []

    @pytest.mark.asyncio
    async def test_enrichment_no_pictures(self, mock_document):
        """Test enrichment skips when document has no pictures."""
        mock_document.pictures = []

        state = {
            "document_id": "doc_001",
            "document": mock_document,
            "chunks": [],
            "enrichment_status": "pending",
        }

        result = await image_enrichment_node_with_sections(state)

        assert result["enrichment_status"] == "skipped"

    @pytest.mark.asyncio
    async def test_enrichment_error_handling(self, ingestion_state_with_document):
        """Test enrichment error handling - errors in parallel tasks are caught and skipped."""
        with patch(
            "src.components.ingestion.nodes.image_enrichment_with_sections.ImageProcessor"
        ) as mock_processor_class:
            mock_processor = AsyncMock()
            # Errors in asyncio.gather are caught and returned as exceptions
            # The node continues processing and marks as completed
            mock_processor.process_image = AsyncMock(side_effect=RuntimeError("VLM error"))
            mock_processor.cleanup = MagicMock()
            mock_processor_class.return_value = mock_processor

            state = await image_enrichment_node_with_sections(ingestion_state_with_document)

            # With error handling in gather, enrichment completes but no images processed
            assert state["enrichment_status"] == "completed"
            assert len(state["vlm_metadata"]) == 0  # No images processed due to error

    @pytest.mark.asyncio
    async def test_enrichment_updates_document_text(self, ingestion_state_with_document):
        """Test that enrichment updates picture_item.text with description."""
        description = "Detailed architecture diagram"

        with patch(
            "src.components.ingestion.nodes.image_enrichment_with_sections.ImageProcessor"
        ) as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_image = AsyncMock(return_value=description)
            mock_processor.cleanup = MagicMock()
            mock_processor_class.return_value = mock_processor

            state = await image_enrichment_node_with_sections(ingestion_state_with_document)

            # Verify document was updated
            assert state["document"].pictures[0].text == description

    @pytest.mark.asyncio
    async def test_enrichment_with_caption(self, ingestion_state_with_document, mock_picture_item):
        """Test enrichment preserves existing caption."""
        mock_picture_item.caption = "Existing caption"
        description = "New description"

        with patch(
            "src.components.ingestion.nodes.image_enrichment_with_sections.ImageProcessor"
        ) as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_image = AsyncMock(return_value=description)
            mock_processor.cleanup = MagicMock()
            mock_processor_class.return_value = mock_processor

            state = await image_enrichment_node_with_sections(ingestion_state_with_document)

            # Caption and description should be combined
            expected_text = f"Existing caption\n\n{description}"
            assert state["document"].pictures[0].text == expected_text


# =============================================================================
# Tests: Multiple Images with Sections
# =============================================================================


class TestMultipleImagesWithSections:
    """Test processing multiple images with different sections."""

    @pytest.mark.asyncio
    async def test_multiple_images_different_sections(self, mock_document, mock_chunk):
        """Test processing images from different sections."""
        # Create multiple picture items on different pages
        picture1 = MagicMock()
        picture1.get_image = MagicMock(return_value=MagicMock(size=(500, 500)))
        picture1.prov = [MagicMock(page_no=2, bbox=MagicMock(l=0, t=0, r=100, b=100))]
        picture1.prov[0].bbox.coord_origin = MagicMock(value="top-left")
        picture1.caption = None
        picture1.text = ""

        picture2 = MagicMock()
        picture2.get_image = MagicMock(return_value=MagicMock(size=(600, 400)))
        picture2.prov = [MagicMock(page_no=5, bbox=MagicMock(l=50, t=50, r=150, b=150))]
        picture2.prov[0].bbox.coord_origin = MagicMock(value="top-left")
        picture2.caption = None
        picture2.text = ""

        mock_document.pictures = [picture1, picture2]

        chunks = [
            mock_chunk("section_1", "Introduction", 1, [1, 2, 3]),
            mock_chunk("section_3.2", "Architecture", 2, [5, 6]),
        ]

        state = {
            "document_id": "doc_001",
            "document": mock_document,
            "chunks": chunks,
            "page_dimensions": {
                2: {"width": 800, "height": 600},
                5: {"width": 800, "height": 600},
            },
            "enrichment_status": "pending",
            "vlm_metadata": [],
        }

        with patch(
            "src.components.ingestion.nodes.image_enrichment_with_sections.ImageProcessor"
        ) as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_image = AsyncMock(side_effect=["Description 1", "Description 2"])
            mock_processor.cleanup = MagicMock()
            mock_processor_class.return_value = mock_processor

            result = await image_enrichment_node_with_sections(state)

            assert len(result["vlm_metadata"]) == 2
            assert result["vlm_metadata"][0]["section_id"] == "section_1"
            assert result["vlm_metadata"][1]["section_id"] == "section_3.2"


# =============================================================================
# Tests: Metadata Completeness
# =============================================================================


class TestMetadataCompleteness:
    """Test that all metadata is complete and properly structured."""

    @pytest.mark.asyncio
    async def test_vlm_metadata_structure(self, ingestion_state_with_document):
        """Test that VLM metadata has all required fields."""
        with patch(
            "src.components.ingestion.nodes.image_enrichment_with_sections.ImageProcessor"
        ) as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_image = AsyncMock(return_value="Description")
            mock_processor.cleanup = MagicMock()
            mock_processor_class.return_value = mock_processor

            state = await image_enrichment_node_with_sections(ingestion_state_with_document)

            vlm_metadata = state["vlm_metadata"][0]

            # Check all required fields
            required_fields = [
                "picture_index",
                "picture_ref",
                "description",
                "bbox_full",
                "section_id",
                "section_heading",
                "section_level",
                "vlm_model",
                "timestamp",
            ]

            for field in required_fields:
                assert field in vlm_metadata, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_progress_update(self, ingestion_state_with_document):
        """Test that progress is updated after enrichment."""
        with patch(
            "src.components.ingestion.nodes.image_enrichment_with_sections.ImageProcessor"
        ) as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_image = AsyncMock(return_value="Description")
            mock_processor.cleanup = MagicMock()
            mock_processor_class.return_value = mock_processor

            state = await image_enrichment_node_with_sections(ingestion_state_with_document)

            assert state["overall_progress"] >= 0
            assert state["overall_progress"] <= 1.0
