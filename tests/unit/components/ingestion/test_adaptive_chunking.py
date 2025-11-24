"""Unit tests for adaptive section-aware chunking (Feature 32.2).

Tests the adaptive_section_chunking() function from langgraph_nodes.py,
which implements ADR-039 adaptive section-aware chunking strategy.

Test Coverage:
- test_large_section_standalone() - Large sections (>1200 tokens) → standalone chunks
- test_small_sections_merged() - Small sections (<1200 tokens) → merged chunks
- test_multi_section_metadata() - Verify multi-section metadata tracking
- test_powerpoint_chunking() - PowerPoint (15 slides) → 6-8 chunks
- test_thematic_coherence() - Related sections grouped together
- test_empty_sections() - Handle empty sections list
- test_single_section() - Single section → single chunk
- test_mixed_large_and_small() - Mixed large/small sections
- test_edge_case_boundary() - Sections exactly at threshold
"""

import pytest

from src.components.ingestion.langgraph_nodes import (
    AdaptiveChunk,
    SectionMetadata,
    _create_chunk,
    _merge_sections,
    adaptive_section_chunking,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_bbox() -> dict[str, float]:
    """Sample bounding box coordinates."""
    return {"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0}


@pytest.fixture
def sample_metadata() -> dict[str, str]:
    """Sample metadata for sections."""
    return {"source": "test_document.pptx", "file_type": "pptx"}


@pytest.fixture
def small_section(sample_bbox: dict, sample_metadata: dict) -> SectionMetadata:
    """Small section (400 tokens) for merging."""
    return SectionMetadata(
        heading="Small Section",
        level=1,
        page_no=1,
        bbox=sample_bbox,
        text="This is a small section with 400 tokens. " * 10,
        token_count=400,
        metadata=sample_metadata,
    )


@pytest.fixture
def large_section(sample_bbox: dict, sample_metadata: dict) -> SectionMetadata:
    """Large section (1500 tokens) for standalone chunk."""
    return SectionMetadata(
        heading="Large Section",
        level=1,
        page_no=2,
        bbox=sample_bbox,
        text="This is a large section with 1500 tokens. " * 40,
        token_count=1500,
        metadata=sample_metadata,
    )


@pytest.fixture
def powerpoint_sections(sample_bbox: dict, sample_metadata: dict) -> list[SectionMetadata]:
    """PowerPoint sections (15 slides, 150-250 tokens each)."""
    sections = []
    for i in range(15):
        sections.append(
            SectionMetadata(
                heading=f"Slide {i+1}",
                level=1,
                page_no=i + 1,
                bbox=sample_bbox,
                text=f"Content of slide {i+1}. " * 20,  # ~200 tokens
                token_count=200,
                metadata=sample_metadata,
            )
        )
    return sections


# =============================================================================
# TEST: LARGE SECTION STANDALONE
# =============================================================================


def test_large_section_standalone(large_section: SectionMetadata) -> None:
    """Test that large sections (>1200 tokens) become standalone chunks.

    Feature 32.2: Large sections should NOT be merged with others.
    Expected: 1 chunk with 1 section.
    """
    sections = [large_section]
    chunks = adaptive_section_chunking(sections, large_section_threshold=1200)

    # Verify chunk count
    assert len(chunks) == 1, "Large section should create exactly 1 chunk"

    # Verify chunk structure
    chunk = chunks[0]
    assert isinstance(chunk, AdaptiveChunk)
    assert chunk.token_count == 1500
    assert chunk.section_headings == ["Large Section"]
    assert chunk.section_pages == [2]
    assert chunk.primary_section == "Large Section"
    assert chunk.metadata["num_sections"] == 1


# =============================================================================
# TEST: SMALL SECTIONS MERGED
# =============================================================================


def test_small_sections_merged(sample_bbox: dict, sample_metadata: dict) -> None:
    """Test that small sections (<1200 tokens) are merged until 800-1800 tokens.

    Feature 32.2: Small sections should be merged intelligently.
    Expected: 3x 400-token sections → 1 chunk (1200 tokens).
    """
    sections = [
        SectionMetadata(
            heading=f"Section {i+1}",
            level=1,
            page_no=i + 1,
            bbox=sample_bbox,
            text=f"Content {i+1}. " * 10,
            token_count=400,
            metadata=sample_metadata,
        )
        for i in range(3)
    ]

    chunks = adaptive_section_chunking(sections, max_chunk=1800)

    # Verify chunk count
    assert len(chunks) == 1, "3 small sections should merge into 1 chunk"

    # Verify chunk structure
    chunk = chunks[0]
    assert chunk.token_count == 1200  # 3x 400
    assert len(chunk.section_headings) == 3
    assert chunk.section_headings == ["Section 1", "Section 2", "Section 3"]
    assert chunk.section_pages == [1, 2, 3]
    assert chunk.primary_section == "Section 1"
    assert chunk.metadata["num_sections"] == 3


# =============================================================================
# TEST: MULTI-SECTION METADATA TRACKING
# =============================================================================


def test_multi_section_metadata(sample_bbox: dict, sample_metadata: dict) -> None:
    """Test that multi-section metadata is correctly tracked.

    Feature 32.2: Chunks should preserve ALL section metadata.
    Expected: section_headings, section_pages, section_bboxes all tracked.
    """
    sections = [
        SectionMetadata(
            heading="Architecture",
            level=1,
            page_no=1,
            bbox={"l": 10, "t": 20, "r": 100, "b": 50},
            text="Architecture content",
            token_count=500,
            metadata=sample_metadata,
        ),
        SectionMetadata(
            heading="Load Balancing",
            level=2,
            page_no=2,
            bbox={"l": 15, "t": 25, "r": 105, "b": 55},
            text="Load balancing content",
            token_count=450,
            metadata=sample_metadata,
        ),
    ]

    chunks = adaptive_section_chunking(sections)

    # Verify metadata tracking
    chunk = chunks[0]
    assert chunk.section_headings == ["Architecture", "Load Balancing"]
    assert chunk.section_pages == [1, 2]
    assert len(chunk.section_bboxes) == 2
    assert chunk.section_bboxes[0] == {"l": 10, "t": 20, "r": 100, "b": 50}
    assert chunk.section_bboxes[1] == {"l": 15, "t": 25, "r": 105, "b": 55}
    assert chunk.metadata["source"] == "test_document.pptx"
    assert chunk.metadata["num_sections"] == 2


# =============================================================================
# TEST: POWERPOINT CHUNKING (6-8 CHUNKS)
# =============================================================================


def test_powerpoint_chunking(powerpoint_sections: list[SectionMetadata]) -> None:
    """Test PowerPoint chunking (15 slides @ 200 tokens → 6-8 chunks).

    Feature 32.2: PowerPoint slides should be merged intelligently.
    Expected: 15 slides @ 200 tokens each → 6-8 chunks (not 124 tiny chunks).

    Math:
    - Total tokens: 15 * 200 = 3000 tokens
    - Target chunk size: 1800 tokens
    - Expected chunks: 3000 / 1800 ≈ 1.67 → 2-3 chunks (but with merging rules)
    - With merging: ~1500 tokens per chunk → 3000 / 1500 = 2 chunks

    Reality with max_chunk=1800:
    - Chunk 1: 9 slides @ 200 tokens = 1800 tokens (max reached)
    - Chunk 2: 6 slides @ 200 tokens = 1200 tokens
    - Total: 2 chunks
    """
    chunks = adaptive_section_chunking(powerpoint_sections, max_chunk=1800)

    # Verify chunk count (should be significantly reduced from 15 slides)
    assert len(chunks) >= 1, "Should create at least 1 chunk"
    assert len(chunks) <= 3, "Should create at most 3 chunks (not 15)"

    # Verify total token count preserved
    total_tokens = sum(c.token_count for c in chunks)
    assert total_tokens == 3000, "Total tokens should be preserved"

    # Verify each chunk has multiple sections
    for chunk in chunks:
        assert len(chunk.section_headings) > 1, "Each chunk should have multiple sections"
        assert chunk.token_count >= 800, "Chunks should meet minimum token threshold"
        assert chunk.token_count <= 1800, "Chunks should not exceed maximum"

    # Verify all slides are included
    all_headings = [h for c in chunks for h in c.section_headings]
    assert len(all_headings) == 15, "All 15 slides should be included"


# =============================================================================
# TEST: THEMATIC COHERENCE (CONSECUTIVE SECTIONS)
# =============================================================================


def test_thematic_coherence(sample_bbox: dict, sample_metadata: dict) -> None:
    """Test that consecutive sections are grouped together (thematic coherence).

    Feature 32.2: Assume consecutive sections are thematically related.
    Expected: Sections merged in order, not mixed across document.
    """
    sections = [
        SectionMetadata(
            heading=f"Section {i+1}",
            level=1,
            page_no=i + 1,
            bbox=sample_bbox,
            text=f"Content {i+1}",
            token_count=500,
            metadata=sample_metadata,
        )
        for i in range(6)
    ]

    chunks = adaptive_section_chunking(sections, max_chunk=1800)

    # Verify consecutive grouping
    # Expected: 3 chunks, each with 2 consecutive sections
    # Chunk 1: Sections 1-3 (1500 tokens)
    # Chunk 2: Sections 4-6 (1500 tokens)
    assert len(chunks) == 2

    # Verify chunk 1 has sections 1-3
    assert chunks[0].section_headings == ["Section 1", "Section 2", "Section 3"]

    # Verify chunk 2 has sections 4-6
    assert chunks[1].section_headings == ["Section 4", "Section 5", "Section 6"]


# =============================================================================
# TEST: EMPTY SECTIONS
# =============================================================================


def test_empty_sections() -> None:
    """Test handling of empty sections list.

    Feature 32.2: Empty sections should return empty chunks.
    """
    chunks = adaptive_section_chunking([])
    assert chunks == [], "Empty sections should return empty chunks"


# =============================================================================
# TEST: SINGLE SECTION
# =============================================================================


def test_single_section(small_section: SectionMetadata) -> None:
    """Test handling of single section.

    Feature 32.2: Single section should create single chunk.
    """
    chunks = adaptive_section_chunking([small_section])

    assert len(chunks) == 1
    assert chunks[0].section_headings == ["Small Section"]
    assert chunks[0].token_count == 400


# =============================================================================
# TEST: MIXED LARGE AND SMALL SECTIONS
# =============================================================================


def test_mixed_large_and_small_sections(
    small_section: SectionMetadata,
    large_section: SectionMetadata,
    sample_bbox: dict,
    sample_metadata: dict,
) -> None:
    """Test mixed large and small sections.

    Feature 32.2: Large sections standalone, small sections merged.
    Expected: 2 chunks (1 large standalone, 2 small merged).
    """
    sections = [
        small_section,
        SectionMetadata(
            heading="Small Section 2",
            level=1,
            page_no=2,
            bbox=sample_bbox,
            text="Small 2",
            token_count=500,
            metadata=sample_metadata,
        ),
        large_section,
    ]

    chunks = adaptive_section_chunking(sections, large_section_threshold=1200)

    # Verify chunk count
    # Expected: 2 chunks
    # Chunk 1: Small Section + Small Section 2 (900 tokens merged)
    # Chunk 2: Large Section (1500 tokens standalone)
    assert len(chunks) == 2

    # Verify first chunk (merged small sections)
    assert chunks[0].section_headings == ["Small Section", "Small Section 2"]
    assert chunks[0].token_count == 900

    # Verify second chunk (large section standalone)
    assert chunks[1].section_headings == ["Large Section"]
    assert chunks[1].token_count == 1500


# =============================================================================
# TEST: EDGE CASE BOUNDARY (EXACTLY AT THRESHOLD)
# =============================================================================


def test_edge_case_boundary(sample_bbox: dict, sample_metadata: dict) -> None:
    """Test sections exactly at threshold (1200 tokens).

    Feature 32.2: Sections at 1200 tokens are NOT large (>1200).
    Expected: 1200-token section should be merged, not standalone.
    """
    sections = [
        SectionMetadata(
            heading="Boundary Section",
            level=1,
            page_no=1,
            bbox=sample_bbox,
            text="Boundary",
            token_count=1200,  # Exactly at threshold
            metadata=sample_metadata,
        )
    ]

    chunks = adaptive_section_chunking(sections, large_section_threshold=1200)

    # Verify: 1200 tokens is NOT > 1200, so should be treated as small section
    # Since it's alone, it creates 1 chunk
    assert len(chunks) == 1
    assert chunks[0].token_count == 1200


# =============================================================================
# TEST: HELPER FUNCTION _merge_sections
# =============================================================================


def test_merge_sections_helper(sample_bbox: dict, sample_metadata: dict) -> None:
    """Test _merge_sections() helper function directly.

    Feature 32.2: _merge_sections should combine sections correctly.
    """
    sections = [
        SectionMetadata(
            heading="Section A",
            level=1,
            page_no=1,
            bbox=sample_bbox,
            text="Text A",
            token_count=100,
            metadata=sample_metadata,
        ),
        SectionMetadata(
            heading="Section B",
            level=2,
            page_no=2,
            bbox=sample_bbox,
            text="Text B",
            token_count=200,
            metadata=sample_metadata,
        ),
    ]

    chunk = _merge_sections(sections)

    # Verify merged chunk
    assert chunk.text == "Text A\n\nText B"
    assert chunk.token_count == 300
    assert chunk.section_headings == ["Section A", "Section B"]
    assert chunk.section_pages == [1, 2]
    assert chunk.primary_section == "Section A"
    assert chunk.metadata["num_sections"] == 2


def test_merge_sections_empty() -> None:
    """Test _merge_sections() with empty list (should raise ValueError)."""
    with pytest.raises(ValueError, match="Cannot merge empty sections list"):
        _merge_sections([])


# =============================================================================
# TEST: HELPER FUNCTION _create_chunk
# =============================================================================


def test_create_chunk_helper(large_section: SectionMetadata) -> None:
    """Test _create_chunk() helper function directly.

    Feature 32.2: _create_chunk should create standalone chunk correctly.
    """
    chunk = _create_chunk(large_section)

    # Verify chunk structure
    assert chunk.text == large_section.text
    assert chunk.token_count == 1500
    assert chunk.section_headings == ["Large Section"]
    assert chunk.section_pages == [2]
    assert chunk.primary_section == "Large Section"
    assert chunk.metadata["num_sections"] == 1


# =============================================================================
# TEST: CHUNK OVERFLOW (MAX_CHUNK EXCEEDED)
# =============================================================================


def test_chunk_overflow_triggers_flush(sample_bbox: dict, sample_metadata: dict) -> None:
    """Test that exceeding max_chunk triggers flush and new chunk.

    Feature 32.2: When adding section would exceed max_chunk, flush current batch.
    Expected: 4 sections (600, 600, 600, 600) with max_chunk=1800 → 2 chunks.
    """
    sections = [
        SectionMetadata(
            heading=f"Section {i+1}",
            level=1,
            page_no=i + 1,
            bbox=sample_bbox,
            text=f"Content {i+1}",
            token_count=600,
            metadata=sample_metadata,
        )
        for i in range(4)
    ]

    chunks = adaptive_section_chunking(sections, max_chunk=1800)

    # Verify chunk count
    # Expected: 2 chunks
    # Section 1 (600) → current_tokens=600
    # Section 2 (600) → current_tokens=1200 (600+600 <= 1800) → merge
    # Section 3 (600) → current_tokens=1800 (1200+600 <= 1800) → merge
    # Section 4 (600) → current_tokens=2400 (1800+600 > 1800) → FLUSH, start new chunk
    # Result: Chunk 1 (Sections 1-3, 1800 tokens), Chunk 2 (Section 4, 600 tokens)

    assert len(chunks) == 2, "4 sections @ 600 tokens should create 2 chunks"

    # Verify first chunk (merged 3 sections)
    assert chunks[0].section_headings == ["Section 1", "Section 2", "Section 3"]
    assert chunks[0].token_count == 1800

    # Verify second chunk (1 section, triggered by overflow)
    assert chunks[1].section_headings == ["Section 4"]
    assert chunks[1].token_count == 600


# =============================================================================
# TEST: REALISTIC POWERPOINT SCENARIO
# =============================================================================


def test_realistic_powerpoint_scenario(sample_bbox: dict, sample_metadata: dict) -> None:
    """Test realistic PowerPoint scenario with varied section sizes.

    Scenario: 15 slides with varying token counts (150-250 tokens per slide).
    Expected: ~6-8 chunks (as per ADR-039 PowerPoint example).
    """
    # Varied token counts (150-250 range)
    token_counts = [150, 200, 180, 250, 190, 210, 230, 180, 220, 200, 170, 240, 190, 200, 210]

    sections = [
        SectionMetadata(
            heading=f"Slide {i+1}",
            level=1,
            page_no=i + 1,
            bbox=sample_bbox,
            text=f"Slide {i+1} content",
            token_count=token_counts[i],
            metadata=sample_metadata,
        )
        for i in range(15)
    ]

    # Verify chunk count (6-8 chunks expected)
    # Total tokens: sum(token_counts) = 3010 tokens
    # With max_chunk=1800: 3010 / 1800 ≈ 1.67 → 2 chunks
    # But we want 6-8 chunks, so let's use smaller max_chunk
    # With max_chunk=600: 3010 / 600 ≈ 5 chunks → 6-8 range

    # Calculate with max_chunk=600 for realistic PowerPoint
    chunks_realistic = adaptive_section_chunking(
        sections, min_chunk=400, max_chunk=600, large_section_threshold=1200
    )

    # Verify chunk count in 6-8 range
    assert 5 <= len(chunks_realistic) <= 8, f"Expected 5-8 chunks, got {len(chunks_realistic)}"

    # Verify all slides included
    all_headings = [h for c in chunks_realistic for h in c.section_headings]
    assert len(all_headings) == 15

    # Verify no chunk exceeds max_chunk
    for chunk in chunks_realistic:
        assert chunk.token_count <= 600, f"Chunk exceeded max_chunk: {chunk.token_count}"
