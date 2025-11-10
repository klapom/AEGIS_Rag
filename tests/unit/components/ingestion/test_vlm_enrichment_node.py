"""Unit tests for VLM Image Enrichment Node - Sprint 21 Feature 21.6.

Tests cover:
- Node execution with DoclingDocument
- BBox extraction and normalization
- VLM description insertion into document
- Error handling and graceful degradation
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from PIL import Image

from src.components.ingestion.ingestion_state import IngestionState
from src.components.ingestion.langgraph_nodes import image_enrichment_node


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def base_state():
    """Create base ingestion state."""
    return {
        "document_id": "test-doc-123",
        "document_path": "/path/to/test.pdf",
        "batch_index": 0,
        "errors": [],
        "overall_progress": 0.0,
    }


@pytest.fixture
def mock_docling_document():
    """Create mock DoclingDocument with pictures."""
    doc = Mock()

    # Mock picture items
    picture1 = Mock()
    picture1.get_image.return_value = Image.new("RGB", (200, 200), color=(255, 0, 0))
    picture1.caption = "Figure 1"
    picture1.text = None  # Will be set by VLM

    # Mock provenance (BBox)
    prov1 = Mock()
    prov1.page_no = 1
    prov1.bbox = Mock()
    prov1.bbox.l = 50.0
    prov1.bbox.t = 100.0
    prov1.bbox.r = 250.0
    prov1.bbox.b = 300.0
    prov1.bbox.coord_origin = Mock()
    prov1.bbox.coord_origin.value = "TOPLEFT"
    picture1.prov = [prov1]

    picture2 = Mock()
    picture2.get_image.return_value = Image.new("RGB", (200, 200), color=(0, 255, 0))
    picture2.caption = None
    picture2.text = None

    prov2 = Mock()
    prov2.page_no = 2
    prov2.bbox = Mock()
    prov2.bbox.l = 100.0
    prov2.bbox.t = 150.0
    prov2.bbox.r = 300.0
    prov2.bbox.b = 350.0
    prov2.bbox.coord_origin = Mock()
    prov2.bbox.coord_origin.value = "TOPLEFT"
    picture2.prov = [prov2]

    doc.pictures = [picture1, picture2]

    return doc


@pytest.fixture
def page_dimensions():
    """Create page dimensions dict."""
    return {
        1: {"width": 595.0, "height": 842.0, "unit": "pt", "dpi": 72},
        2: {"width": 595.0, "height": 842.0, "unit": "pt", "dpi": 72},
    }


@pytest.fixture
def mock_image_processor():
    """Create mock ImageProcessor."""
    processor = Mock()
    processor.process_image.side_effect = [
        "This is a red diagram showing system architecture.",
        "This is a green flowchart depicting the process flow.",
    ]
    processor.cleanup = Mock()
    return processor


# =============================================================================
# NODE EXECUTION TESTS
# =============================================================================


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__valid_document__enriches_successfully(
    mock_processor_class, base_state, mock_docling_document, page_dimensions, mock_image_processor
):
    """Test successful VLM enrichment of document with images."""
    mock_processor_class.return_value = mock_image_processor

    # Setup state
    state = base_state.copy()
    state["document"] = mock_docling_document
    state["page_dimensions"] = page_dimensions

    # Execute node
    result_state = await image_enrichment_node(state)

    # Verify status
    assert result_state["enrichment_status"] == "completed"
    assert len(result_state["vlm_metadata"]) == 2

    # Verify VLM descriptions were inserted into document
    assert mock_docling_document.pictures[0].text == "Figure 1\n\nThis is a red diagram showing system architecture."
    assert mock_docling_document.pictures[1].text == "This is a green flowchart depicting the process flow."

    # Verify cleanup was called
    mock_image_processor.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_image_enrichment_node__no_document__skips_gracefully(base_state):
    """Test that node skips gracefully when no document is present."""
    state = base_state.copy()
    state["document"] = None

    result_state = await image_enrichment_node(state)

    assert result_state["enrichment_status"] == "skipped"
    assert result_state["vlm_metadata"] == []
    assert "overall_progress" in result_state


@pytest.mark.asyncio
async def test_image_enrichment_node__no_pictures__skips_gracefully(base_state):
    """Test that node skips when document has no pictures."""
    state = base_state.copy()

    mock_doc = Mock()
    mock_doc.pictures = []
    state["document"] = mock_doc

    result_state = await image_enrichment_node(state)

    assert result_state["enrichment_status"] == "skipped"
    assert result_state["vlm_metadata"] == []


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__no_page_dimensions__still_processes(
    mock_processor_class, base_state, mock_docling_document, mock_image_processor
):
    """Test that enrichment works even without page dimensions."""
    mock_processor_class.return_value = mock_image_processor

    state = base_state.copy()
    state["document"] = mock_docling_document
    state["page_dimensions"] = {}  # Empty dimensions

    result_state = await image_enrichment_node(state)

    assert result_state["enrichment_status"] == "completed"
    assert len(result_state["vlm_metadata"]) == 2

    # BBox should be None when page dimensions missing
    for metadata in result_state["vlm_metadata"]:
        assert metadata["bbox_full"] is None


# =============================================================================
# BBOX EXTRACTION TESTS
# =============================================================================


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__bbox_extraction__correct_structure(
    mock_processor_class, base_state, mock_docling_document, page_dimensions, mock_image_processor
):
    """Test that BBox is extracted with correct structure."""
    mock_processor_class.return_value = mock_image_processor

    state = base_state.copy()
    state["document"] = mock_docling_document
    state["page_dimensions"] = page_dimensions

    result_state = await image_enrichment_node(state)

    # Check first image BBox
    bbox1 = result_state["vlm_metadata"][0]["bbox_full"]
    assert bbox1 is not None

    # Check absolute coordinates
    assert bbox1["bbox_absolute"]["left"] == 50.0
    assert bbox1["bbox_absolute"]["top"] == 100.0
    assert bbox1["bbox_absolute"]["right"] == 250.0
    assert bbox1["bbox_absolute"]["bottom"] == 300.0

    # Check page context
    assert bbox1["page_context"]["page_no"] == 1
    assert bbox1["page_context"]["page_width"] == 595.0
    assert bbox1["page_context"]["page_height"] == 842.0
    assert bbox1["page_context"]["unit"] == "pt"
    assert bbox1["page_context"]["dpi"] == 72

    # Check normalized coordinates
    assert bbox1["bbox_normalized"]["left"] == pytest.approx(50.0 / 595.0)
    assert bbox1["bbox_normalized"]["top"] == pytest.approx(100.0 / 842.0)
    assert bbox1["bbox_normalized"]["right"] == pytest.approx(250.0 / 595.0)
    assert bbox1["bbox_normalized"]["bottom"] == pytest.approx(300.0 / 842.0)


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__no_provenance__no_bbox(
    mock_processor_class, base_state, page_dimensions, mock_image_processor
):
    """Test that images without provenance have no BBox."""
    mock_processor_class.return_value = mock_image_processor

    # Create document with picture without provenance
    mock_doc = Mock()
    picture = Mock()
    picture.get_image.return_value = Image.new("RGB", (200, 200))
    picture.caption = None
    picture.text = None
    picture.prov = []  # No provenance
    mock_doc.pictures = [picture]

    state = base_state.copy()
    state["document"] = mock_doc
    state["page_dimensions"] = page_dimensions

    result_state = await image_enrichment_node(state)

    assert result_state["vlm_metadata"][0]["bbox_full"] is None


# =============================================================================
# VLM METADATA TESTS
# =============================================================================


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__metadata_structure__complete(
    mock_processor_class, base_state, mock_docling_document, page_dimensions, mock_image_processor
):
    """Test that VLM metadata has complete structure."""
    mock_processor_class.return_value = mock_image_processor

    state = base_state.copy()
    state["document"] = mock_docling_document
    state["page_dimensions"] = page_dimensions

    result_state = await image_enrichment_node(state)

    metadata = result_state["vlm_metadata"][0]

    # Check required fields
    assert "picture_index" in metadata
    assert metadata["picture_index"] == 0

    assert "picture_ref" in metadata
    assert metadata["picture_ref"] == "#/pictures/0"

    assert "description" in metadata
    assert len(metadata["description"]) > 0

    assert "bbox_full" in metadata

    assert "vlm_model" in metadata
    assert metadata["vlm_model"] == "qwen3-vl:4b-instruct"

    assert "timestamp" in metadata
    assert isinstance(metadata["timestamp"], float)


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__vlm_error_on_one_image__continues(
    mock_processor_class, base_state, mock_docling_document, page_dimensions
):
    """Test that node continues processing if one image fails."""
    # Mock processor that fails on first image, succeeds on second
    processor = Mock()
    processor.process_image.side_effect = [
        Exception("VLM timeout"),
        "Second image processed successfully",
    ]
    processor.cleanup = Mock()
    mock_processor_class.return_value = processor

    state = base_state.copy()
    state["document"] = mock_docling_document
    state["page_dimensions"] = page_dimensions

    result_state = await image_enrichment_node(state)

    # Should complete with partial results
    assert result_state["enrichment_status"] == "completed"
    assert len(result_state["vlm_metadata"]) == 1  # Only second image succeeded

    # Second picture should be enriched
    assert mock_docling_document.pictures[1].text == "Second image processed successfully"


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__filtered_image__skips_gracefully(
    mock_processor_class, base_state, mock_docling_document, page_dimensions
):
    """Test that filtered images (None returned) are skipped."""
    processor = Mock()
    processor.process_image.side_effect = [
        None,  # First image filtered out
        "Second image description",
    ]
    processor.cleanup = Mock()
    mock_processor_class.return_value = processor

    state = base_state.copy()
    state["document"] = mock_docling_document
    state["page_dimensions"] = page_dimensions

    result_state = await image_enrichment_node(state)

    assert result_state["enrichment_status"] == "completed"
    assert len(result_state["vlm_metadata"]) == 1  # Only non-filtered image


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__critical_error__fails_gracefully(
    mock_processor_class, base_state, mock_docling_document, page_dimensions
):
    """Test that critical errors are handled gracefully (no raise)."""
    processor = Mock()
    processor.cleanup = Mock()
    # Simulate critical error in processor initialization
    mock_processor_class.side_effect = Exception("Critical VLM initialization error")

    state = base_state.copy()
    state["document"] = mock_docling_document
    state["page_dimensions"] = page_dimensions

    # Should not raise - node designed for graceful degradation
    result_state = await image_enrichment_node(state)

    assert result_state["enrichment_status"] == "failed"
    assert result_state["vlm_metadata"] == []
    assert len(result_state["errors"]) > 0


# =============================================================================
# CAPTION HANDLING TESTS
# =============================================================================


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__with_caption__combines_caption_and_description(
    mock_processor_class, base_state, page_dimensions, mock_image_processor
):
    """Test that VLM description is appended to existing caption."""
    mock_processor_class.return_value = mock_image_processor

    # Create picture with caption
    mock_doc = Mock()
    picture = Mock()
    picture.get_image.return_value = Image.new("RGB", (200, 200))
    picture.caption = "Figure 1: System Overview"
    picture.text = None
    picture.prov = []
    mock_doc.pictures = [picture]

    state = base_state.copy()
    state["document"] = mock_doc
    state["page_dimensions"] = page_dimensions

    result_state = await image_enrichment_node(state)

    # Caption + VLM description combined
    assert picture.text == "Figure 1: System Overview\n\nThis is a red diagram showing system architecture."


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__no_caption__uses_description_only(
    mock_processor_class, base_state, page_dimensions, mock_image_processor
):
    """Test that VLM description is used alone when no caption exists."""
    mock_processor_class.return_value = mock_image_processor

    # Create picture without caption
    mock_doc = Mock()
    picture = Mock()
    picture.get_image.return_value = Image.new("RGB", (200, 200))
    picture.caption = None
    picture.text = None
    picture.prov = []
    mock_doc.pictures = [picture]

    state = base_state.copy()
    state["document"] = mock_doc
    state["page_dimensions"] = page_dimensions

    result_state = await image_enrichment_node(state)

    # Only VLM description
    assert picture.text == "This is a red diagram showing system architecture."


# =============================================================================
# PROGRESS TRACKING TESTS
# =============================================================================


@pytest.mark.asyncio
@patch("src.components.ingestion.langgraph_nodes.ImageProcessor")
async def test_image_enrichment_node__updates_overall_progress(
    mock_processor_class, base_state, mock_docling_document, page_dimensions, mock_image_processor
):
    """Test that overall progress is updated after enrichment."""
    mock_processor_class.return_value = mock_image_processor

    state = base_state.copy()
    state["document"] = mock_docling_document
    state["page_dimensions"] = page_dimensions
    state["overall_progress"] = 0.3  # Previous progress

    result_state = await image_enrichment_node(state)

    # Progress should be updated
    assert "overall_progress" in result_state
    # Note: actual value depends on calculate_progress() implementation
