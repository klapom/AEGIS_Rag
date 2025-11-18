"""Extended integration tests for Hybrid Search (Sprint 27 Feature 27.2).

This module provides comprehensive coverage for hybrid search functionality.

Tests cover:
- Reciprocal Rank Fusion (RRF) algorithm
- Vector + BM25 combination
- Empty result handling
- Performance characteristics
- Reranking integration
- Diversity analysis
- Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.components.vector_search.hybrid_search import HybridSearch
from src.components.retrieval.filters import MetadataFilters
from src.core.exceptions import VectorSearchError


@pytest.fixture
def mock_vector_results():
    """Mock vector search results."""
    return [
        {
            "id": "doc1",
            "text": "Vector result 1",
            "score": 0.95,
            "source": "docs.md",
            "document_id": "doc1",
            "rank": 1,
            "search_type": "vector"
        },
        {
            "id": "doc2",
            "text": "Vector result 2",
            "score": 0.87,
            "source": "tech.md",
            "document_id": "doc2",
            "rank": 2,
            "search_type": "vector"
        },
        {
            "id": "doc3",
            "text": "Vector result 3",
            "score": 0.75,
            "source": "arch.md",
            "document_id": "doc3",
            "rank": 3,
            "search_type": "vector"
        }
    ]


@pytest.fixture
def mock_bm25_results():
    """Mock BM25 search results."""
    return [
        {
            "id": "doc2",  # Overlap with vector
            "text": "BM25 result 1",
            "score": 8.5,
            "source": "tech.md",
            "document_id": "doc2",
            "rank": 1,
            "search_type": "bm25"
        },
        {
            "id": "doc4",  # Unique to BM25
            "text": "BM25 result 2",
            "score": 7.2,
            "source": "guide.md",
            "document_id": "doc4",
            "rank": 2,
            "search_type": "bm25"
        },
        {
            "id": "doc5",  # Unique to BM25
            "text": "BM25 result 3",
            "score": 6.1,
            "source": "api.md",
            "document_id": "doc5",
            "rank": 3,
            "search_type": "bm25"
        }
    ]


@pytest.fixture
async def hybrid_search_instance(mock_qdrant_client, mock_embedding_service, mock_bm25_search):
    """HybridSearch instance with mocked dependencies."""
    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search
    )
    return search


# ============================================================================
# RRF Algorithm Tests
# ============================================================================

def test_reciprocal_rank_fusion():
    """Test RRF algorithm with overlapping results."""
    from src.utils.fusion import reciprocal_rank_fusion

    vector_results = [
        {"id": "doc1", "score": 0.95},
        {"id": "doc2", "score": 0.87},
        {"id": "doc3", "score": 0.75}
    ]

    bm25_results = [
        {"id": "doc2", "score": 8.5},  # Overlaps with vector
        {"id": "doc4", "score": 7.2},
        {"id": "doc5", "score": 6.1}
    ]

    fused = reciprocal_rank_fusion(
        rankings=[vector_results, bm25_results],
        k=60,
        id_field="id"
    )

    # doc2 should rank highest (appears in both)
    assert fused[0]["id"] == "doc2"
    assert "rrf_score" in fused[0]


def test_reciprocal_rank_fusion_no_overlap():
    """Test RRF with completely disjoint result sets."""
    from src.utils.fusion import reciprocal_rank_fusion

    vector_results = [
        {"id": "doc1", "score": 0.9},
        {"id": "doc2", "score": 0.8}
    ]

    bm25_results = [
        {"id": "doc3", "score": 7.0},
        {"id": "doc4", "score": 6.0}
    ]

    fused = reciprocal_rank_fusion(
        rankings=[vector_results, bm25_results],
        k=60,
        id_field="id"
    )

    # All documents should be present
    assert len(fused) == 4
    fused_ids = {doc["id"] for doc in fused}
    assert fused_ids == {"doc1", "doc2", "doc3", "doc4"}


def test_reciprocal_rank_fusion_single_ranking():
    """Test RRF with only one ranking (edge case)."""
    from src.utils.fusion import reciprocal_rank_fusion

    results = [
        {"id": "doc1", "score": 0.9},
        {"id": "doc2", "score": 0.8}
    ]

    fused = reciprocal_rank_fusion(
        rankings=[results],
        k=60,
        id_field="id"
    )

    # Should preserve original order
    assert fused[0]["id"] == "doc1"
    assert fused[1]["id"] == "doc2"


# ============================================================================
# Hybrid Search Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_hybrid_search_empty_results(hybrid_search_instance):
    """Test hybrid search when both sources return empty."""
    # Mock empty results
    hybrid_search_instance.qdrant_client.search = AsyncMock(return_value=[])
    hybrid_search_instance.bm25_search.search = MagicMock(return_value=[])

    result = await hybrid_search_instance.hybrid_search("test query")

    assert result["returned_results"] == 0
    assert len(result["results"]) == 0


@pytest.mark.asyncio
async def test_hybrid_search_vector_only(hybrid_search_instance, mock_vector_results):
    """Test hybrid search when only vector returns results."""
    hybrid_search_instance.vector_search = AsyncMock(return_value=mock_vector_results)
    hybrid_search_instance.keyword_search = AsyncMock(return_value=[])

    result = await hybrid_search_instance.hybrid_search("test query", use_reranking=False)

    assert result["returned_results"] > 0
    assert result["search_metadata"]["vector_results_count"] == 3
    assert result["search_metadata"]["bm25_results_count"] == 0


@pytest.mark.asyncio
async def test_hybrid_search_bm25_only(hybrid_search_instance, mock_bm25_results):
    """Test hybrid search when only BM25 returns results."""
    hybrid_search_instance.vector_search = AsyncMock(return_value=[])
    hybrid_search_instance.keyword_search = AsyncMock(return_value=mock_bm25_results)

    result = await hybrid_search_instance.hybrid_search("test query", use_reranking=False)

    assert result["returned_results"] > 0
    assert result["search_metadata"]["bm25_results_count"] == 3


@pytest.mark.asyncio
async def test_hybrid_search_performance(hybrid_search_instance, mock_vector_results, mock_bm25_results):
    """Test hybrid search latency within acceptable bounds."""
    import time

    hybrid_search_instance.vector_search = AsyncMock(return_value=mock_vector_results)
    hybrid_search_instance.keyword_search = AsyncMock(return_value=mock_bm25_results)

    start = time.time()
    result = await hybrid_search_instance.hybrid_search("test query", use_reranking=False)
    elapsed = time.time() - start

    # Should complete within 1 second for mocked operations
    assert elapsed < 1.0
    assert result["returned_results"] > 0


@pytest.mark.asyncio
async def test_hybrid_search_with_filters(hybrid_search_instance):
    """Test hybrid search with metadata filters."""
    filters = MetadataFilters(
        source=["docs.md", "tech.md"],
        date_range={"start": "2025-01-01", "end": "2025-12-31"}
    )

    # Mock filtered results
    filtered_results = [
        {"id": "doc1", "text": "Filtered result", "score": 0.9, "source": "docs.md"}
    ]
    hybrid_search_instance.vector_search = AsyncMock(return_value=filtered_results)
    hybrid_search_instance.keyword_search = AsyncMock(return_value=[])

    result = await hybrid_search_instance.hybrid_search(
        "test query",
        filters=filters,
        use_reranking=False
    )

    assert result["returned_results"] > 0


@pytest.mark.asyncio
async def test_hybrid_search_diversity_analysis(hybrid_search_instance, mock_vector_results, mock_bm25_results):
    """Test diversity analysis between vector and BM25 results."""
    hybrid_search_instance.vector_search = AsyncMock(return_value=mock_vector_results)
    hybrid_search_instance.keyword_search = AsyncMock(return_value=mock_bm25_results)

    result = await hybrid_search_instance.hybrid_search("test query", use_reranking=False)

    # Check diversity stats
    diversity_stats = result["search_metadata"]["diversity_stats"]
    assert "common_percentage" in diversity_stats
    assert "unique_to_first" in diversity_stats
    assert "unique_to_second" in diversity_stats


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_hybrid_search_vector_failure(hybrid_search_instance, mock_bm25_results):
    """Test fallback when vector search fails."""
    hybrid_search_instance.vector_search = AsyncMock(
        side_effect=VectorSearchError("Vector search failed")
    )
    hybrid_search_instance.keyword_search = AsyncMock(return_value=mock_bm25_results)

    with pytest.raises(VectorSearchError):
        await hybrid_search_instance.hybrid_search("test query")


@pytest.mark.asyncio
async def test_hybrid_search_bm25_failure(hybrid_search_instance, mock_vector_results):
    """Test fallback when BM25 search fails."""
    hybrid_search_instance.vector_search = AsyncMock(return_value=mock_vector_results)
    hybrid_search_instance.keyword_search = AsyncMock(
        side_effect=VectorSearchError("BM25 search failed")
    )

    with pytest.raises(VectorSearchError):
        await hybrid_search_instance.hybrid_search("test query")


@pytest.mark.asyncio
async def test_hybrid_search_invalid_filters(hybrid_search_instance):
    """Test error handling for invalid metadata filters."""
    invalid_filters = MetadataFilters(
        source=None,
        date_range={"start": "invalid-date"}
    )

    # Should raise validation error
    with pytest.raises(VectorSearchError):
        await hybrid_search_instance.hybrid_search(
            "test query",
            filters=invalid_filters
        )
