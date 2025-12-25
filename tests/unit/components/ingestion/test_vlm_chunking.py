"""Unit tests for VLM-Chunking Integration (Sprint 64, Feature 64.1).

Tests the integration of VLM image descriptions into sections and chunks,
ensuring that image annotations are properly matched via BBox IoU and
propagated through the chunking pipeline.

Test Coverage:
- test_calculate_bbox_iou_perfect_overlap() - IoU = 1.0 for identical boxes
- test_calculate_bbox_iou_no_overlap() - IoU = 0.0 for non-overlapping boxes
- test_calculate_bbox_iou_partial_overlap() - IoU between 0 and 1 for partial overlap
- test_calculate_bbox_iou_edge_cases() - Edge cases (zero area, touching boxes)
- test_integrate_vlm_high_iou_match() - VLM matched to section with IoU > 0.5
- test_integrate_vlm_low_iou_fallback() - VLM fallback to first section on page
- test_integrate_vlm_no_bbox() - VLM without BBox appended to first section
- test_integrate_vlm_multiple_images() - Multiple VLM items integrated correctly
- test_integrate_vlm_empty_sections() - Handle empty sections list
- test_integrate_vlm_empty_metadata() - Handle empty VLM metadata
- test_merge_sections_with_image_annotations() - Image annotations preserved in merged chunks
- test_create_chunk_with_image_annotations() - Image annotations preserved in standalone chunks
"""

import pytest

from src.components.ingestion.nodes.adaptive_chunking import (
    _create_chunk,
    _integrate_vlm_descriptions,
    _merge_sections,
    calculate_bbox_iou,
)
from src.components.ingestion.nodes.models import SectionMetadata

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_vlm_bbox() -> dict:
    """Sample VLM BBox with normalized coordinates."""
    return {
        "bbox_normalized": {"left": 0.1, "top": 0.2, "right": 0.5, "bottom": 0.6},
        "page_context": {"page_no": 1, "page_width": 720, "page_height": 540},
    }


@pytest.fixture
def sample_section_bbox() -> dict:
    """Sample section BBox with normalized coordinates."""
    return {"l": 0.15, "t": 0.25, "r": 0.55, "b": 0.65}


@pytest.fixture
def sample_section(sample_section_bbox: dict) -> SectionMetadata:
    """Sample section for VLM integration testing."""
    return SectionMetadata(
        heading="Test Section",
        level=1,
        page_no=1,
        bbox=sample_section_bbox,
        text="This is a test section.",
        token_count=100,
        metadata={"source": "test.pdf", "file_type": "pdf"},
    )


@pytest.fixture
def sample_vlm_metadata(sample_vlm_bbox: dict) -> list[dict]:
    """Sample VLM metadata with BBox."""
    return [
        {
            "picture_ref": "#/pictures/0",
            "description": "A chart showing sales data",
            "bbox_full": sample_vlm_bbox,
        }
    ]


# =============================================================================
# TEST: CALCULATE_BBOX_IOU
# =============================================================================


def test_calculate_bbox_iou_perfect_overlap() -> None:
    """Test IoU calculation for perfectly overlapping bounding boxes.

    Expected: IoU = 1.0
    """
    bbox1 = {"bbox_normalized": {"left": 0.1, "top": 0.2, "right": 0.5, "bottom": 0.6}}
    bbox2 = {"l": 0.1, "t": 0.2, "r": 0.5, "b": 0.6}

    iou = calculate_bbox_iou(bbox1, bbox2)

    assert iou == pytest.approx(1.0, abs=1e-6), "Perfect overlap should yield IoU = 1.0"


def test_calculate_bbox_iou_no_overlap() -> None:
    """Test IoU calculation for non-overlapping bounding boxes.

    Expected: IoU = 0.0
    """
    bbox1 = {"bbox_normalized": {"left": 0.1, "top": 0.2, "right": 0.3, "bottom": 0.4}}
    bbox2 = {"l": 0.5, "t": 0.6, "r": 0.8, "b": 0.9}

    iou = calculate_bbox_iou(bbox1, bbox2)

    assert iou == 0.0, "Non-overlapping boxes should yield IoU = 0.0"


def test_calculate_bbox_iou_partial_overlap() -> None:
    """Test IoU calculation for partially overlapping bounding boxes.

    Scenario:
    - bbox1: [0.1, 0.2] to [0.5, 0.6] (width=0.4, height=0.4, area=0.16)
    - bbox2: [0.3, 0.4] to [0.7, 0.8] (width=0.4, height=0.4, area=0.16)
    - Intersection: [0.3, 0.4] to [0.5, 0.6] (width=0.2, height=0.2, area=0.04)
    - Union: 0.16 + 0.16 - 0.04 = 0.28
    - IoU: 0.04 / 0.28 ≈ 0.143

    Expected: IoU between 0 and 1
    """
    bbox1 = {"bbox_normalized": {"left": 0.1, "top": 0.2, "right": 0.5, "bottom": 0.6}}
    bbox2 = {"l": 0.3, "t": 0.4, "r": 0.7, "b": 0.8}

    iou = calculate_bbox_iou(bbox1, bbox2)

    assert 0.0 < iou < 1.0, "Partial overlap should yield 0 < IoU < 1"
    assert iou == pytest.approx(0.143, abs=0.01), f"Expected IoU ≈ 0.143, got {iou}"


def test_calculate_bbox_iou_high_overlap() -> None:
    """Test IoU calculation for high overlap (>0.5 threshold).

    Scenario:
    - bbox1: [0.1, 0.2] to [0.5, 0.6] (area=0.16)
    - bbox2: [0.15, 0.25] to [0.55, 0.65] (area=0.16)
    - High overlap should yield IoU > 0.5

    Expected: IoU > 0.5 (high confidence match)
    """
    bbox1 = {"bbox_normalized": {"left": 0.1, "top": 0.2, "right": 0.5, "bottom": 0.6}}
    bbox2 = {"l": 0.15, "t": 0.25, "r": 0.55, "b": 0.65}

    iou = calculate_bbox_iou(bbox1, bbox2)

    assert iou > 0.5, f"High overlap should yield IoU > 0.5, got {iou}"


def test_calculate_bbox_iou_edge_case_touching() -> None:
    """Test IoU calculation for touching but non-overlapping boxes.

    Expected: IoU = 0.0
    """
    bbox1 = {"bbox_normalized": {"left": 0.0, "top": 0.0, "right": 0.5, "bottom": 0.5}}
    bbox2 = {"l": 0.5, "t": 0.5, "r": 1.0, "b": 1.0}

    iou = calculate_bbox_iou(bbox1, bbox2)

    assert iou == 0.0, "Touching boxes should yield IoU = 0.0"


def test_calculate_bbox_iou_edge_case_zero_area() -> None:
    """Test IoU calculation for zero-area bounding boxes.

    Expected: IoU = 0.0 (union = 0, avoid division by zero)
    """
    bbox1 = {"bbox_normalized": {"left": 0.5, "top": 0.5, "right": 0.5, "bottom": 0.5}}
    bbox2 = {"l": 0.5, "t": 0.5, "r": 0.5, "b": 0.5}

    iou = calculate_bbox_iou(bbox1, bbox2)

    assert iou == 0.0, "Zero-area boxes should yield IoU = 0.0"


# =============================================================================
# TEST: INTEGRATE_VLM_DESCRIPTIONS
# =============================================================================


def test_integrate_vlm_high_iou_match(
    sample_section: SectionMetadata, sample_vlm_metadata: list[dict]
) -> None:
    """Test VLM integration with high IoU match (>0.5).

    Expected:
    - VLM description appended to section text
    - Image annotation stored in section.image_annotations
    """
    sections = [sample_section]

    updated_sections = _integrate_vlm_descriptions(sections, sample_vlm_metadata)

    # Verify VLM description integrated
    assert "[Image Description]:" in updated_sections[0].text
    assert "A chart showing sales data" in updated_sections[0].text

    # Verify image annotation stored
    assert hasattr(updated_sections[0], "image_annotations")
    assert len(updated_sections[0].image_annotations) == 1
    annotation = updated_sections[0].image_annotations[0]
    assert annotation["picture_ref"] == "#/pictures/0"
    assert annotation["iou_score"] > 0.5


def test_integrate_vlm_low_iou_fallback() -> None:
    """Test VLM integration with low IoU (fallback to first section on page).

    Scenario:
    - VLM BBox does not overlap well with any section
    - Should fallback to first section on same page

    Expected:
    - VLM description appended to first section on page
    - Image annotation has iou_score = 0.0 (fallback indicator)
    """
    # Section far from VLM BBox
    section = SectionMetadata(
        heading="Far Section",
        level=1,
        page_no=1,
        bbox={"l": 0.7, "t": 0.8, "r": 0.9, "b": 0.95},  # Far from VLM BBox
        text="Original text",
        token_count=50,
        metadata={"source": "test.pdf"},
    )

    vlm_metadata = [
        {
            "picture_ref": "#/pictures/0",
            "description": "Image description",
            "bbox_full": {
                "bbox_normalized": {"left": 0.1, "top": 0.1, "right": 0.3, "bottom": 0.3},
                "page_context": {"page_no": 1},
            },
        }
    ]

    updated_sections = _integrate_vlm_descriptions([section], vlm_metadata)

    # Verify fallback integration
    assert "[Image Description]:" in updated_sections[0].text
    assert hasattr(updated_sections[0], "image_annotations")
    annotation = updated_sections[0].image_annotations[0]
    assert annotation["iou_score"] == 0.0, "Fallback should have iou_score = 0.0"


def test_integrate_vlm_no_bbox() -> None:
    """Test VLM integration without BBox (append to first section).

    Expected:
    - VLM description appended to first section
    - Image annotation with bbox=None
    """
    section = SectionMetadata(
        heading="Test Section",
        level=1,
        page_no=1,
        bbox={"l": 0.0, "t": 0.0, "r": 1.0, "b": 1.0},
        text="Original text",
        token_count=50,
        metadata={"source": "test.pdf"},
    )

    vlm_metadata = [
        {
            "picture_ref": "#/pictures/0",
            "description": "No BBox image",
            "bbox_full": None,  # No BBox
        }
    ]

    updated_sections = _integrate_vlm_descriptions([section], vlm_metadata)

    # Verify integration
    assert "[Image Description]: No BBox image" in updated_sections[0].text
    assert hasattr(updated_sections[0], "image_annotations")
    annotation = updated_sections[0].image_annotations[0]
    assert annotation["bbox"] is None


def test_integrate_vlm_multiple_images() -> None:
    """Test VLM integration with multiple images in different sections.

    Expected:
    - Each VLM matched to best section
    - Multiple image_annotations per section if applicable

    Note: BBoxes must have IoU > 0.5 for high-confidence match.
    Section 2 bbox: [0.5, 0.5] to [1.0, 1.0] (area = 0.25)
    VLM 2 bbox: [0.55, 0.55] to [0.95, 0.95] (area = 0.16)
    Intersection: [0.55, 0.55] to [0.95, 0.95] = 0.16
    Union: 0.25 + 0.16 - 0.16 = 0.25
    IoU: 0.16 / 0.25 = 0.64 > 0.5 ✓
    """
    sections = [
        SectionMetadata(
            heading="Section 1",
            level=1,
            page_no=1,
            bbox={"l": 0.0, "t": 0.0, "r": 0.5, "b": 0.5},
            text="Section 1 text",
            token_count=50,
            metadata={"source": "test.pdf"},
        ),
        SectionMetadata(
            heading="Section 2",
            level=1,
            page_no=1,
            bbox={"l": 0.5, "t": 0.5, "r": 1.0, "b": 1.0},
            text="Section 2 text",
            token_count=50,
            metadata={"source": "test.pdf"},
        ),
    ]

    vlm_metadata = [
        {
            "picture_ref": "#/pictures/0",
            "description": "Image in section 1",
            "bbox_full": {
                "bbox_normalized": {"left": 0.1, "top": 0.1, "right": 0.4, "bottom": 0.4},
                "page_context": {"page_no": 1},
            },
        },
        {
            "picture_ref": "#/pictures/1",
            "description": "Image in section 2",
            "bbox_full": {
                # Adjusted to have high IoU with section 2 bbox
                "bbox_normalized": {"left": 0.55, "top": 0.55, "right": 0.95, "bottom": 0.95},
                "page_context": {"page_no": 1},
            },
        },
    ]

    updated_sections = _integrate_vlm_descriptions(sections, vlm_metadata)

    # Verify both images integrated
    assert "[Image Description]: Image in section 1" in updated_sections[0].text
    assert "[Image Description]: Image in section 2" in updated_sections[1].text

    # Verify annotations
    assert len(updated_sections[0].image_annotations) == 1
    assert len(updated_sections[1].image_annotations) == 1


def test_integrate_vlm_empty_sections() -> None:
    """Test VLM integration with empty sections list.

    Expected: No errors, sections list unchanged
    """
    vlm_metadata = [
        {
            "picture_ref": "#/pictures/0",
            "description": "Orphaned image",
            "bbox_full": None,
        }
    ]

    updated_sections = _integrate_vlm_descriptions([], vlm_metadata)

    assert updated_sections == [], "Empty sections should remain empty"


def test_integrate_vlm_empty_metadata() -> None:
    """Test VLM integration with empty VLM metadata.

    Expected: Sections unchanged
    """
    section = SectionMetadata(
        heading="Test Section",
        level=1,
        page_no=1,
        bbox={"l": 0.0, "t": 0.0, "r": 1.0, "b": 1.0},
        text="Original text",
        token_count=50,
        metadata={"source": "test.pdf"},
    )

    updated_sections = _integrate_vlm_descriptions([section], [])

    # Verify section unchanged
    assert updated_sections[0].text == "Original text"
    assert not hasattr(updated_sections[0], "image_annotations")


def test_integrate_vlm_different_pages() -> None:
    """Test VLM integration only matches sections on same page.

    Expected:
    - VLM on page 1 should NOT match section on page 2
    - VLM should fallback to first section on page 1 (if exists)
    """
    sections = [
        SectionMetadata(
            heading="Page 2 Section",
            level=1,
            page_no=2,  # Different page
            bbox={"l": 0.1, "t": 0.1, "r": 0.5, "b": 0.5},
            text="Page 2 text",
            token_count=50,
            metadata={"source": "test.pdf"},
        ),
    ]

    vlm_metadata = [
        {
            "picture_ref": "#/pictures/0",
            "description": "Page 1 image",
            "bbox_full": {
                "bbox_normalized": {"left": 0.1, "top": 0.1, "right": 0.5, "bottom": 0.5},
                "page_context": {"page_no": 1},  # Page 1
            },
        }
    ]

    updated_sections = _integrate_vlm_descriptions(sections, vlm_metadata)

    # VLM should NOT be integrated (different page, no fallback section on page 1)
    assert "[Image Description]:" not in updated_sections[0].text


# =============================================================================
# TEST: MERGE_SECTIONS WITH IMAGE_ANNOTATIONS
# =============================================================================


def test_merge_sections_with_image_annotations() -> None:
    """Test _merge_sections preserves image_annotations from sections.

    Expected:
    - Image annotations from all sections collected
    - Chunk has combined image_annotations
    """
    section1 = SectionMetadata(
        heading="Section 1",
        level=1,
        page_no=1,
        bbox={"l": 0.0, "t": 0.0, "r": 1.0, "b": 0.5},
        text="Section 1 text",
        token_count=400,
        metadata={"source": "test.pdf", "file_type": "pdf"},
    )
    section1.image_annotations = [
        {"picture_ref": "#/pictures/0", "bbox": {}, "iou_score": 0.8}
    ]

    section2 = SectionMetadata(
        heading="Section 2",
        level=1,
        page_no=1,
        bbox={"l": 0.0, "t": 0.5, "r": 1.0, "b": 1.0},
        text="Section 2 text",
        token_count=400,
        metadata={"source": "test.pdf", "file_type": "pdf"},
    )
    section2.image_annotations = [
        {"picture_ref": "#/pictures/1", "bbox": {}, "iou_score": 0.9}
    ]

    chunk = _merge_sections([section1, section2])

    # Verify image_annotations collected
    assert hasattr(chunk, "image_annotations")
    assert len(chunk.image_annotations) == 2
    assert chunk.image_annotations[0]["picture_ref"] == "#/pictures/0"
    assert chunk.image_annotations[1]["picture_ref"] == "#/pictures/1"


def test_merge_sections_without_image_annotations() -> None:
    """Test _merge_sections handles sections without image_annotations.

    Expected: Chunk has no image_annotations attribute
    """
    section = SectionMetadata(
        heading="Section",
        level=1,
        page_no=1,
        bbox={"l": 0.0, "t": 0.0, "r": 1.0, "b": 1.0},
        text="Section text",
        token_count=400,
        metadata={"source": "test.pdf", "file_type": "pdf"},
    )

    chunk = _merge_sections([section])

    # Verify no image_annotations
    assert not hasattr(chunk, "image_annotations")


# =============================================================================
# TEST: CREATE_CHUNK WITH IMAGE_ANNOTATIONS
# =============================================================================


def test_create_chunk_with_image_annotations() -> None:
    """Test _create_chunk preserves image_annotations from section.

    Expected:
    - Chunk has image_annotations copied from section
    """
    section = SectionMetadata(
        heading="Large Section",
        level=1,
        page_no=1,
        bbox={"l": 0.0, "t": 0.0, "r": 1.0, "b": 1.0},
        text="Large section text",
        token_count=1500,
        metadata={"source": "test.pdf", "file_type": "pdf"},
    )
    section.image_annotations = [
        {"picture_ref": "#/pictures/0", "bbox": {}, "iou_score": 0.85}
    ]

    chunk = _create_chunk(section)

    # Verify image_annotations preserved
    assert hasattr(chunk, "image_annotations")
    assert len(chunk.image_annotations) == 1
    assert chunk.image_annotations[0]["picture_ref"] == "#/pictures/0"


def test_create_chunk_without_image_annotations() -> None:
    """Test _create_chunk handles sections without image_annotations.

    Expected: Chunk has no image_annotations attribute
    """
    section = SectionMetadata(
        heading="Large Section",
        level=1,
        page_no=1,
        bbox={"l": 0.0, "t": 0.0, "r": 1.0, "b": 1.0},
        text="Large section text",
        token_count=1500,
        metadata={"source": "test.pdf", "file_type": "pdf"},
    )

    chunk = _create_chunk(section)

    # Verify no image_annotations
    assert not hasattr(chunk, "image_annotations")
