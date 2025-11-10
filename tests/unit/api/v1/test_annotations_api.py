"""Unit tests for Annotations API - Sprint 21 Feature 21.6.

Tests cover:
- GET /api/v1/annotations/document/{document_id}
- GET /api/v1/annotations/chunk/{chunk_id}
- Response models and validation
- Error handling
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from qdrant_client.models import PointStruct, ScoredPoint

from src.api.v1.annotations import (
    BBoxAbsolute,
    BBoxNormalized,
    DocumentAnnotationsResponse,
    ImageAnnotation,
    PageAnnotations,
    PageContext,
    PageDimensions,
    get_chunk_annotations,
    get_document_annotations,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_qdrant_point():
    """Create mock Qdrant point with image annotations."""
    point = Mock(spec=ScoredPoint)
    point.id = "test-chunk-123"
    point.payload = {
        "document_id": "test-doc-123",
        "chunk_id": "test-chunk-123",
        "page_no": 1,
        "contains_images": True,
        "page_dimensions": {"width": 595.0, "height": 842.0, "unit": "pt", "dpi": 72},
        "image_annotations": [
            {
                "description": "A red diagram showing system architecture",
                "vlm_model": "qwen3-vl:4b-instruct",
                "bbox_absolute": {"left": 50.0, "top": 100.0, "right": 250.0, "bottom": 300.0},
                "page_context": {
                    "page_no": 1,
                    "page_width": 595.0,
                    "page_height": 842.0,
                    "unit": "pt",
                    "dpi": 72,
                    "coord_origin": "TOPLEFT",
                },
                "bbox_normalized": {
                    "left": 0.084,
                    "top": 0.119,
                    "right": 0.420,
                    "bottom": 0.356,
                },
            }
        ],
    }
    return point


@pytest.fixture
def mock_qdrant_client():
    """Create mock QdrantClientWrapper."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user."""
    return {"user_id": "test-user-123", "username": "testuser"}


# =============================================================================
# RESPONSE MODEL TESTS
# =============================================================================


def test_bbox_absolute__valid_data__creates_successfully():
    """Test BBoxAbsolute model creation."""
    bbox = BBoxAbsolute(left=50.0, top=100.0, right=250.0, bottom=300.0)

    assert bbox.left == 50.0
    assert bbox.top == 100.0
    assert bbox.right == 250.0
    assert bbox.bottom == 300.0


def test_page_context__valid_data__creates_successfully():
    """Test PageContext model creation."""
    ctx = PageContext(
        page_no=1,
        page_width=595.0,
        page_height=842.0,
        unit="pt",
        dpi=72,
        coord_origin="TOPLEFT",
    )

    assert ctx.page_no == 1
    assert ctx.page_width == 595.0
    assert ctx.coord_origin == "TOPLEFT"


def test_bbox_normalized__valid_data__creates_successfully():
    """Test BBoxNormalized model with range validation."""
    bbox = BBoxNormalized(left=0.1, top=0.2, right=0.8, bottom=0.9)

    assert bbox.left == 0.1
    assert bbox.right == 0.8


def test_bbox_normalized__out_of_range__validation_error():
    """Test that BBoxNormalized validates range (0.0-1.0)."""
    with pytest.raises(ValueError):
        BBoxNormalized(left=-0.1, top=0.2, right=0.8, bottom=0.9)

    with pytest.raises(ValueError):
        BBoxNormalized(left=0.1, top=0.2, right=1.5, bottom=0.9)


def test_image_annotation__complete_data__creates_successfully():
    """Test ImageAnnotation model with all fields."""
    bbox_abs = BBoxAbsolute(left=50.0, top=100.0, right=250.0, bottom=300.0)
    page_ctx = PageContext(
        page_no=1,
        page_width=595.0,
        page_height=842.0,
        unit="pt",
        dpi=72,
        coord_origin="TOPLEFT",
    )
    bbox_norm = BBoxNormalized(left=0.084, top=0.119, right=0.420, bottom=0.356)

    annotation = ImageAnnotation(
        description="Test description",
        vlm_model="qwen3-vl:4b-instruct",
        bbox_absolute=bbox_abs,
        page_context=page_ctx,
        bbox_normalized=bbox_norm,
    )

    assert annotation.description == "Test description"
    assert annotation.vlm_model == "qwen3-vl:4b-instruct"
    assert annotation.bbox_absolute.left == 50.0


def test_page_dimensions__valid_data__creates_successfully():
    """Test PageDimensions model."""
    dims = PageDimensions(width=595.0, height=842.0, unit="pt", dpi=72)

    assert dims.width == 595.0
    assert dims.height == 842.0
    assert dims.unit == "pt"


def test_page_annotations__with_annotations__creates_successfully():
    """Test PageAnnotations model."""
    dims = PageDimensions(width=595.0, height=842.0)
    annotation = ImageAnnotation(
        description="Test", vlm_model="qwen3-vl:4b-instruct"
    )

    page_annots = PageAnnotations(page_dimensions=dims, annotations=[annotation])

    assert len(page_annots.annotations) == 1
    assert page_annots.page_dimensions.width == 595.0


# =============================================================================
# GET DOCUMENT ANNOTATIONS TESTS
# =============================================================================


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_document_annotations__success(
    mock_settings, mock_qdrant_class, mock_qdrant_point, mock_current_user
):
    """Test successful retrieval of document annotations."""
    mock_settings.qdrant_collection = "test_collection"

    # Mock Qdrant client
    client = AsyncMock()
    client.scroll.return_value = ([mock_qdrant_point], None)
    mock_qdrant_class.return_value = client

    # Call endpoint
    response = await get_document_annotations(
        document_id="test-doc-123",
        chunk_ids=None,
        page_no=None,
        _current_user=mock_current_user,
    )

    # Verify response
    assert isinstance(response, DocumentAnnotationsResponse)
    assert response.document_id == "test-doc-123"
    assert response.total_annotations == 1
    assert "1" in response.annotations_by_page
    assert len(response.annotations_by_page["1"].annotations) == 1


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_document_annotations__filter_by_chunk_ids(
    mock_settings, mock_qdrant_class, mock_qdrant_point, mock_current_user
):
    """Test filtering by specific chunk IDs."""
    mock_settings.qdrant_collection = "test_collection"

    client = AsyncMock()
    client.scroll.return_value = ([mock_qdrant_point], None)
    mock_qdrant_class.return_value = client

    # Call with chunk_ids filter
    response = await get_document_annotations(
        document_id="test-doc-123",
        chunk_ids=["test-chunk-123", "test-chunk-456"],
        page_no=None,
        _current_user=mock_current_user,
    )

    # Verify Qdrant filter was constructed correctly
    client.scroll.assert_called_once()
    # Should have filter conditions for document_id, chunk_ids, contains_images


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_document_annotations__filter_by_page_no(
    mock_settings, mock_qdrant_class, mock_qdrant_point, mock_current_user
):
    """Test filtering by specific page number."""
    mock_settings.qdrant_collection = "test_collection"

    client = AsyncMock()
    client.scroll.return_value = ([mock_qdrant_point], None)
    mock_qdrant_class.return_value = client

    # Call with page_no filter
    response = await get_document_annotations(
        document_id="test-doc-123",
        chunk_ids=None,
        page_no=1,
        _current_user=mock_current_user,
    )

    # Verify response contains only page 1
    assert "1" in response.annotations_by_page


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_document_annotations__no_annotations__returns_empty(
    mock_settings, mock_qdrant_class, mock_current_user
):
    """Test behavior when no annotations found."""
    mock_settings.qdrant_collection = "test_collection"

    client = AsyncMock()
    client.scroll.return_value = ([], None)  # No points found
    mock_qdrant_class.return_value = client

    response = await get_document_annotations(
        document_id="test-doc-123",
        chunk_ids=None,
        page_no=None,
        _current_user=mock_current_user,
    )

    assert response.total_annotations == 0
    assert len(response.annotations_by_page) == 0


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_document_annotations__qdrant_error__raises_http_exception(
    mock_settings, mock_qdrant_class, mock_current_user
):
    """Test error handling when Qdrant query fails."""
    mock_settings.qdrant_collection = "test_collection"

    client = AsyncMock()
    client.scroll.side_effect = Exception("Qdrant connection error")
    mock_qdrant_class.return_value = client

    with pytest.raises(HTTPException) as exc_info:
        await get_document_annotations(
            document_id="test-doc-123",
            chunk_ids=None,
            page_no=None,
            _current_user=mock_current_user,
        )

    assert exc_info.value.status_code == 500
    assert "Failed to retrieve annotations" in exc_info.value.detail


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_document_annotations__multiple_pages__groups_correctly(
    mock_settings, mock_qdrant_class, mock_current_user
):
    """Test that annotations from multiple pages are grouped correctly."""
    mock_settings.qdrant_collection = "test_collection"

    # Create points for different pages
    point1 = Mock(spec=ScoredPoint)
    point1.payload = {
        "page_no": 1,
        "page_dimensions": {"width": 595.0, "height": 842.0, "unit": "pt", "dpi": 72},
        "image_annotations": [
            {
                "description": "Page 1 image",
                "vlm_model": "qwen3-vl:4b-instruct",
                "bbox_absolute": None,
                "page_context": None,
                "bbox_normalized": None,
            }
        ],
    }

    point2 = Mock(spec=ScoredPoint)
    point2.payload = {
        "page_no": 2,
        "page_dimensions": {"width": 595.0, "height": 842.0, "unit": "pt", "dpi": 72},
        "image_annotations": [
            {
                "description": "Page 2 image",
                "vlm_model": "qwen3-vl:4b-instruct",
                "bbox_absolute": None,
                "page_context": None,
                "bbox_normalized": None,
            }
        ],
    }

    client = AsyncMock()
    client.scroll.return_value = ([point1, point2], None)
    mock_qdrant_class.return_value = client

    response = await get_document_annotations(
        document_id="test-doc-123",
        chunk_ids=None,
        page_no=None,
        _current_user=mock_current_user,
    )

    assert len(response.annotations_by_page) == 2
    assert "1" in response.annotations_by_page
    assert "2" in response.annotations_by_page
    assert response.total_annotations == 2


# =============================================================================
# GET CHUNK ANNOTATIONS TESTS
# =============================================================================


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_chunk_annotations__success(
    mock_settings, mock_qdrant_class, mock_qdrant_point, mock_current_user
):
    """Test successful retrieval of chunk annotations."""
    mock_settings.qdrant_collection = "test_collection"

    client = AsyncMock()
    client.retrieve.return_value = [mock_qdrant_point]
    mock_qdrant_class.return_value = client

    # Call endpoint
    response = await get_chunk_annotations(
        chunk_id="test-chunk-123", _current_user=mock_current_user
    )

    # Verify response
    assert isinstance(response, list)
    assert len(response) == 1
    assert isinstance(response[0], ImageAnnotation)
    assert response[0].description == "A red diagram showing system architecture"


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_chunk_annotations__chunk_not_found__raises_404(
    mock_settings, mock_qdrant_class, mock_current_user
):
    """Test 404 error when chunk not found."""
    mock_settings.qdrant_collection = "test_collection"

    client = AsyncMock()
    client.retrieve.return_value = []  # Empty result
    mock_qdrant_class.return_value = client

    with pytest.raises(HTTPException) as exc_info:
        await get_chunk_annotations(
            chunk_id="non-existent-chunk", _current_user=mock_current_user
        )

    assert exc_info.value.status_code == 404
    assert "Chunk not found" in exc_info.value.detail


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_chunk_annotations__no_images__returns_empty_list(
    mock_settings, mock_qdrant_class, mock_current_user
):
    """Test chunk with no image annotations returns empty list."""
    mock_settings.qdrant_collection = "test_collection"

    point = Mock(spec=ScoredPoint)
    point.payload = {"image_annotations": []}  # No annotations

    client = AsyncMock()
    client.retrieve.return_value = [point]
    mock_qdrant_class.return_value = client

    response = await get_chunk_annotations(
        chunk_id="test-chunk-123", _current_user=mock_current_user
    )

    assert isinstance(response, list)
    assert len(response) == 0


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_chunk_annotations__qdrant_error__raises_http_exception(
    mock_settings, mock_qdrant_class, mock_current_user
):
    """Test error handling when Qdrant retrieve fails."""
    mock_settings.qdrant_collection = "test_collection"

    client = AsyncMock()
    client.retrieve.side_effect = Exception("Qdrant connection error")
    mock_qdrant_class.return_value = client

    with pytest.raises(HTTPException) as exc_info:
        await get_chunk_annotations(
            chunk_id="test-chunk-123", _current_user=mock_current_user
        )

    assert exc_info.value.status_code == 500


# =============================================================================
# EDGE CASES & VALIDATION TESTS
# =============================================================================


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_document_annotations__missing_page_no__uses_fallback_dims(
    mock_settings, mock_qdrant_class, mock_current_user
):
    """Test fallback page dimensions when page_no is missing."""
    mock_settings.qdrant_collection = "test_collection"

    point = Mock(spec=ScoredPoint)
    point.payload = {
        "page_no": None,  # Missing page number
        "image_annotations": [
            {
                "description": "Test",
                "vlm_model": "qwen3-vl:4b-instruct",
                "bbox_absolute": None,
                "page_context": None,
                "bbox_normalized": None,
            }
        ],
    }

    client = AsyncMock()
    client.scroll.return_value = ([point], None)
    mock_qdrant_class.return_value = client

    response = await get_document_annotations(
        document_id="test-doc-123",
        chunk_ids=None,
        page_no=None,
        _current_user=mock_current_user,
    )

    # Should skip points without page_no
    assert response.total_annotations == 0


@pytest.mark.asyncio
@patch("src.api.v1.annotations.QdrantClientWrapper")
@patch("src.api.v1.annotations.settings")
async def test_get_document_annotations__missing_page_dimensions__uses_fallback(
    mock_settings, mock_qdrant_class, mock_current_user
):
    """Test fallback when page_dimensions is missing."""
    mock_settings.qdrant_collection = "test_collection"

    point = Mock(spec=ScoredPoint)
    point.payload = {
        "page_no": 1,
        "page_dimensions": None,  # Missing dimensions
        "image_annotations": [
            {
                "description": "Test",
                "vlm_model": "qwen3-vl:4b-instruct",
                "bbox_absolute": None,
                "page_context": None,
                "bbox_normalized": None,
            }
        ],
    }

    client = AsyncMock()
    client.scroll.return_value = ([point], None)
    mock_qdrant_class.return_value = client

    response = await get_document_annotations(
        document_id="test-doc-123",
        chunk_ids=None,
        page_no=None,
        _current_user=mock_current_user,
    )

    # Should use fallback dimensions (595x842)
    assert response.total_annotations == 1
    page_dims = response.annotations_by_page["1"].page_dimensions
    assert page_dims.width == 595.0
    assert page_dims.height == 842.0
