"""Unit Tests for Sprint 32 Feature 32.3: Multi-Section Metadata.

Tests for:
- AdaptiveChunk dataclass model
- Section metadata storage in Qdrant
- Section-based re-ranking
- Citation generation with section names

Sprint 32 Feature 32.3: Multi-Section Metadata in Qdrant
ADR-039: Adaptive Section-Aware Chunking
"""

import pytest

from src.components.retrieval.chunking import AdaptiveChunk
from src.components.vector_search.hybrid_search import section_based_reranking

# ============================================================================
# TEST: AdaptiveChunk Model
# ============================================================================


def test_adaptive_chunk_creation():
    """Test AdaptiveChunk dataclass instantiation."""
    chunk = AdaptiveChunk(
        text="Multi-Server Architecture\n\nLoad Balancing Strategies",
        token_count=1050,
        section_headings=["Multi-Server Architecture", "Load Balancing Strategies"],
        section_pages=[1, 2],
        section_bboxes=[
            {"l": 50, "t": 30, "r": 670, "b": 80},
            {"l": 50, "t": 30, "r": 670, "b": 80},
        ],
        primary_section="Multi-Server Architecture",
        metadata={"source": "PerformanceTuning.pptx", "num_sections": 2},
    )

    assert chunk.text == "Multi-Server Architecture\n\nLoad Balancing Strategies"
    assert chunk.token_count == 1050
    assert len(chunk.section_headings) == 2
    assert chunk.section_headings[0] == "Multi-Server Architecture"
    assert len(chunk.section_pages) == 2
    assert len(chunk.section_bboxes) == 2
    assert chunk.primary_section == "Multi-Server Architecture"
    assert chunk.metadata["source"] == "PerformanceTuning.pptx"
    assert chunk.metadata["num_sections"] == 2


def test_adaptive_chunk_to_dict():
    """Test AdaptiveChunk.to_dict() method for Qdrant payload."""
    chunk = AdaptiveChunk(
        text="Test content",
        token_count=100,
        section_headings=["Section 1", "Section 2"],
        section_pages=[1, 2],
        section_bboxes=[{"l": 0, "t": 0, "r": 100, "b": 100}],
        primary_section="Section 1",
        metadata={"source": "doc.pdf", "file_type": "pdf"},
    )

    chunk_dict = chunk.to_dict()

    assert chunk_dict["text"] == "Test content"
    assert chunk_dict["token_count"] == 100
    assert chunk_dict["section_headings"] == ["Section 1", "Section 2"]
    assert chunk_dict["section_pages"] == [1, 2]
    assert chunk_dict["primary_section"] == "Section 1"
    assert chunk_dict["source"] == "doc.pdf"
    assert chunk_dict["file_type"] == "pdf"


def test_adaptive_chunk_default_values():
    """Test AdaptiveChunk with default values (backward compatibility)."""
    chunk = AdaptiveChunk(
        text="Simple chunk without sections",
        token_count=200,
    )

    assert chunk.section_headings == []
    assert chunk.section_pages == []
    assert chunk.section_bboxes == []
    assert chunk.primary_section == ""
    assert chunk.metadata == {}


# ============================================================================
# TEST: Section-Based Re-Ranking
# ============================================================================


def test_section_based_reranking_boosts_matching_sections():
    """Test that section-based re-ranking boosts results matching query."""
    results = [
        {
            "id": "1",
            "score": 0.85,
            "section_headings": ["Multi-Server Architecture", "Load Balancing", "Caching"],
        },
        {
            "id": "2",
            "score": 0.82,
            "section_headings": ["Database Optimization"],
        },
        {
            "id": "3",
            "score": 0.88,
            "section_headings": ["Monitoring", "Alerts"],
        },
    ]

    query = "What is load balancing?"

    reranked = section_based_reranking(results, query)

    # Result 1 should get +0.10 boost (1/3 sections match * 0.3 = 0.10)
    # Original: 0.85 → After boost: 0.95
    # This should now be top result (0.95 > 0.88)
    assert reranked[0]["id"] == "1"
    assert abs(reranked[0]["score"] - 0.95) < 0.01  # Floating point tolerance

    # Result 3 should be second (0.88, no boost)
    assert reranked[1]["id"] == "3"
    assert abs(reranked[1]["score"] - 0.88) < 0.01

    # Result 2 should be last (0.82, no boost)
    assert reranked[2]["id"] == "2"
    assert abs(reranked[2]["score"] - 0.82) < 0.01

    # Verify that result 1 moved from position 2 to position 1 due to boost
    original_order = [r["id"] for r in results]
    reranked_order = [r["id"] for r in reranked]
    assert original_order == ["1", "2", "3"]  # Input order (sorted by original score)
    assert reranked_order == ["1", "3", "2"]  # Output order (after boost)


def test_section_based_reranking_case_insensitive():
    """Test case-insensitive section matching."""
    results = [
        {
            "id": "1",
            "score": 0.80,
            "section_headings": ["Load Balancing Strategies"],
        },
    ]

    # Query with different case
    query = "LOAD BALANCING"

    reranked = section_based_reranking(results, query)

    # Should still get boost (case-insensitive)
    assert reranked[0]["score"] > 0.80


def test_section_based_reranking_multiple_matches():
    """Test boost calculation when multiple sections match."""
    results = [
        {
            "id": "1",
            "score": 0.70,
            "section_headings": [
                "Load Balancing Introduction",
                "Load Balancing Algorithms",
                "Load Balancing Best Practices",
            ],
        },
    ]

    query = "load balancing"

    reranked = section_based_reranking(results, query)

    # All 3 sections match → 3/3 * 0.3 = 0.3 boost
    # Original: 0.70 → After boost: 1.00
    assert abs(reranked[0]["score"] - 1.00) < 0.01


def test_section_based_reranking_no_sections():
    """Test backward compatibility with results without section metadata."""
    results = [
        {
            "id": "1",
            "score": 0.85,
            # No section_headings field
        },
        {
            "id": "2",
            "score": 0.82,
            "section_headings": [],  # Empty list
        },
    ]

    query = "load balancing"

    reranked = section_based_reranking(results, query)

    # No boost applied (backward compatible)
    assert reranked[0]["score"] == 0.85
    assert reranked[1]["score"] == 0.82


def test_section_based_reranking_payload_structure():
    """Test section_based_reranking with nested payload structure."""
    results = [
        {
            "id": "1",
            "score": 0.85,
            "payload": {
                "section_headings": ["Load Balancing", "Caching"],
            },
        },
    ]

    query = "load balancing"

    reranked = section_based_reranking(results, query)

    # Should extract from payload and apply boost
    # 1/2 sections match → 0.5 * 0.3 = 0.15 boost
    assert abs(reranked[0]["score"] - 1.00) < 0.01  # 0.85 + 0.15


def test_section_based_reranking_empty_results():
    """Test section_based_reranking with empty results list."""
    results = []
    query = "load balancing"

    reranked = section_based_reranking(results, query)

    assert reranked == []


# ============================================================================
# TEST: Qdrant Section Metadata Ingestion
# ============================================================================


@pytest.mark.asyncio
async def test_ingest_adaptive_chunks_creates_correct_payload():
    """Test that ingest_adaptive_chunks creates Qdrant payloads with section metadata."""
    from unittest.mock import AsyncMock, MagicMock, patch

    # Create test chunks
    chunks = [
        AdaptiveChunk(
            text="Multi-Server Architecture\n\nLoad Balancing",
            token_count=1050,
            section_headings=["Multi-Server Architecture", "Load Balancing"],
            section_pages=[1, 2],
            section_bboxes=[
                {"l": 50, "t": 30, "r": 670, "b": 80},
                {"l": 50, "t": 30, "r": 670, "b": 80},
            ],
            primary_section="Multi-Server Architecture",
            metadata={"source": "PerformanceTuning.pptx", "num_sections": 2},
        ),
    ]

    # Mock embedding service (patch at the source module)
    with patch("src.components.shared.embedding_service.get_embedding_service") as mock_get_svc:
        # Create mock embedding service
        mock_embedding = MagicMock()
        mock_embedding.embed_single = AsyncMock(return_value=[0.1] * 1024)
        mock_get_svc.return_value = mock_embedding

        # Import and test
        from src.components.vector_search.qdrant_client import QdrantClient

        client = QdrantClient()

        # Mock the upsert_points method to capture payload
        captured_points = []

        async def mock_upsert(collection_name, points, batch_size):
            captured_points.extend(points)
            return True

        client.upsert_points = mock_upsert

        # Execute ingestion
        await client.ingest_adaptive_chunks(chunks, "test_collection")

        # Verify points were created
        assert len(captured_points) == 1
        point = captured_points[0]

        # Check payload contains section metadata
        assert "section_headings" in point.payload
        assert "section_pages" in point.payload
        assert "section_bboxes" in point.payload
        assert "primary_section" in point.payload

        assert point.payload["section_headings"] == [
            "Multi-Server Architecture",
            "Load Balancing",
        ]
        assert point.payload["section_pages"] == [1, 2]
        assert point.payload["primary_section"] == "Multi-Server Architecture"
        assert point.payload["source"] == "PerformanceTuning.pptx"
        assert point.payload["token_count"] == 1050


# ============================================================================
# TEST: Citation Generation with Sections
# ============================================================================


def test_extract_sources_with_section_metadata():
    """Test _extract_sources includes section names in citations."""
    from src.api.v1.chat import _extract_sources

    result = {
        "retrieved_contexts": [
            {
                "text": "Multi-Server Architecture content...",
                "title": "PerformanceTuning.pptx",
                "source": "PerformanceTuning.pptx",
                "score": 0.92,
                "section_headings": ["Multi-Server Architecture", "Load Balancing"],
                "section_pages": [1, 2],
                "primary_section": "Multi-Server Architecture",
                "metadata": {},
            },
        ],
    }

    sources = _extract_sources(result)

    assert len(sources) == 1
    source = sources[0]

    # Citation should include section name and page
    assert "Section: 'Multi-Server Architecture'" in source.title
    assert "(Page 1)" in source.title
    assert "PerformanceTuning.pptx" in source.title

    # Metadata should include section info
    assert "section_headings" in source.metadata
    assert "primary_section" in source.metadata
    assert source.metadata["primary_section"] == "Multi-Server Architecture"


def test_extract_sources_without_section_metadata():
    """Test _extract_sources backward compatibility without section metadata."""
    from src.api.v1.chat import _extract_sources

    result = {
        "retrieved_contexts": [
            {
                "text": "Content without sections...",
                "title": "document.pdf",
                "source": "document.pdf",
                "score": 0.85,
                "metadata": {},
            },
        ],
    }

    sources = _extract_sources(result)

    assert len(sources) == 1
    source = sources[0]

    # No section info in title (backward compatible)
    assert source.title == "document.pdf"
    assert "Section:" not in source.title


def test_extract_sources_with_primary_section_only():
    """Test citation format when only primary_section available (no pages)."""
    from src.api.v1.chat import _extract_sources

    result = {
        "retrieved_contexts": [
            {
                "text": "Content...",
                "title": "doc.pdf",
                "source": "doc.pdf",
                "score": 0.88,
                "primary_section": "Load Balancing",
                "metadata": {},
            },
        ],
    }

    sources = _extract_sources(result)

    assert len(sources) == 1
    source = sources[0]

    # Citation should include section (no page number)
    assert "Section: 'Load Balancing'" in source.title
    assert "(Page" not in source.title  # No page number


# ============================================================================
# TEST: Integration Tests
# ============================================================================


def test_adaptive_chunk_backward_compatibility():
    """Test that existing code works with AdaptiveChunk (backward compatibility)."""
    # Create chunk without section metadata (like existing chunks)
    chunk = AdaptiveChunk(
        text="Simple chunk",
        token_count=100,
    )

    # to_dict() should still work
    chunk_dict = chunk.to_dict()

    assert chunk_dict["text"] == "Simple chunk"
    assert chunk_dict["section_headings"] == []
    assert chunk_dict["section_pages"] == []


def test_section_based_reranking_preserves_order_when_no_boost():
    """Test that re-ranking preserves original order when no sections match."""
    results = [
        {"id": "1", "score": 0.90, "section_headings": ["Database"]},
        {"id": "2", "score": 0.85, "section_headings": ["Monitoring"]},
        {"id": "3", "score": 0.80, "section_headings": ["Alerts"]},
    ]

    query = "load balancing"  # No matches

    reranked = section_based_reranking(results, query)

    # Order should be preserved (no boost applied)
    assert reranked[0]["id"] == "1"
    assert reranked[1]["id"] == "2"
    assert reranked[2]["id"] == "3"
