"""Unit tests for Reciprocal Rank Fusion (RRF) utilities.

Tests the RRF algorithm implementation including:
- Basic RRF calculation
- Weighted RRF
- Ranking diversity analysis
- Edge cases (empty rankings, single ranking, duplicate documents)
"""

import pytest
from typing import List, Dict, Any

from src.utils.fusion import (
    reciprocal_rank_fusion,
    weighted_reciprocal_rank_fusion,
    analyze_ranking_diversity,
)


# ============================================================================
# Test Data
# ============================================================================


@pytest.fixture
def vector_results() -> List[Dict[str, Any]]:
    """Mock vector search results."""
    return [
        {"id": "doc1", "text": "Vector result 1", "score": 0.95},
        {"id": "doc2", "text": "Vector result 2", "score": 0.87},
        {"id": "doc3", "text": "Vector result 3", "score": 0.75},
        {"id": "doc4", "text": "Vector result 4", "score": 0.68},
        {"id": "doc5", "text": "Vector result 5", "score": 0.55},
    ]


@pytest.fixture
def bm25_results() -> List[Dict[str, Any]]:
    """Mock BM25 search results."""
    return [
        {"id": "doc3", "text": "BM25 result 1", "score": 15.3},
        {"id": "doc1", "text": "BM25 result 2", "score": 12.8},
        {"id": "doc6", "text": "BM25 result 3", "score": 10.5},
        {"id": "doc7", "text": "BM25 result 4", "score": 8.2},
        {"id": "doc2", "text": "BM25 result 5", "score": 6.1},
    ]


# ============================================================================
# Test reciprocal_rank_fusion()
# ============================================================================


@pytest.mark.unit
def test_rrf_basic_fusion(vector_results, bm25_results):
    """Test basic RRF fusion of two rankings."""
    fused = reciprocal_rank_fusion([vector_results, bm25_results], k=60)

    # Verify output structure
    assert len(fused) > 0, "RRF should return results"
    assert "rrf_score" in fused[0], "Results should have rrf_score"
    assert "rrf_rank" in fused[0], "Results should have rrf_rank"
    assert "id" in fused[0], "Results should have id"

    # Verify ranking order (descending RRF scores)
    for i in range(len(fused) - 1):
        assert (
            fused[i]["rrf_score"] >= fused[i + 1]["rrf_score"]
        ), "Results should be sorted by RRF score descending"

    # doc1 and doc3 appear in both rankings, should rank higher
    top_ids = [doc["id"] for doc in fused[:3]]
    assert "doc1" in top_ids or "doc3" in top_ids, "Documents in both rankings should rank highly"


@pytest.mark.unit
def test_rrf_score_calculation(vector_results, bm25_results):
    """Test RRF score calculation formula: 1/(k + rank)."""
    k = 60
    fused = reciprocal_rank_fusion([vector_results, bm25_results], k=k)

    # doc1 is rank 1 in vector, rank 2 in BM25
    doc1_result = next(doc for doc in fused if doc["id"] == "doc1")
    expected_score = (1 / (k + 1)) + (1 / (k + 2))
    assert (
        abs(doc1_result["rrf_score"] - expected_score) < 0.0001
    ), f"RRF score mismatch: {doc1_result['rrf_score']} != {expected_score}"


@pytest.mark.unit
def test_rrf_empty_rankings():
    """Test RRF with empty rankings list."""
    fused = reciprocal_rank_fusion([])
    assert fused == [], "Empty rankings should return empty list"


@pytest.mark.unit
def test_rrf_single_ranking(vector_results):
    """Test RRF with single ranking (should preserve order with RRF scores)."""
    fused = reciprocal_rank_fusion([vector_results], k=60)

    assert len(fused) == len(vector_results), "Single ranking should preserve all results"

    # Verify order is preserved
    for i, result in enumerate(fused):
        assert (
            result["id"] == vector_results[i]["id"]
        ), f"Order should be preserved: {result['id']} != {vector_results[i]['id']}"


@pytest.mark.unit
@pytest.mark.parametrize("k", [10, 60, 100, 200])
def test_rrf_different_k_values(vector_results, bm25_results, k):
    """Test RRF with different k parameter values."""
    fused = reciprocal_rank_fusion([vector_results, bm25_results], k=k)

    assert len(fused) > 0, f"RRF should work with k={k}"
    assert all("rrf_score" in doc for doc in fused), "All results should have RRF scores"

    # Higher k = lower contribution from low ranks
    first_score = fused[0]["rrf_score"]
    assert first_score > 0, "RRF scores should be positive"


@pytest.mark.unit
def test_rrf_no_overlap():
    """Test RRF with rankings that have no overlap."""
    ranking1 = [{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}]
    ranking2 = [{"id": "doc4"}, {"id": "doc5"}, {"id": "doc6"}]

    fused = reciprocal_rank_fusion([ranking1, ranking2], k=60)

    # All documents should appear in result
    assert len(fused) == 6, "All unique documents should be included"

    # All should have RRF scores
    assert all("rrf_score" in doc for doc in fused), "All docs should have RRF scores"


@pytest.mark.unit
def test_rrf_complete_overlap():
    """Test RRF with identical rankings."""
    ranking1 = [{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}]
    ranking2 = [{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}]

    fused = reciprocal_rank_fusion([ranking1, ranking2], k=60)

    # Should have 3 unique documents
    assert len(fused) == 3, "Should have 3 unique documents"

    # Verify doc1 has highest score (rank 1 in both)
    assert fused[0]["id"] == "doc1", "doc1 should rank first"


@pytest.mark.unit
def test_rrf_custom_id_field():
    """Test RRF with custom ID field name."""
    ranking1 = [{"doc_id": "A"}, {"doc_id": "B"}]
    ranking2 = [{"doc_id": "B"}, {"doc_id": "C"}]

    fused = reciprocal_rank_fusion([ranking1, ranking2], k=60, id_field="doc_id")

    assert len(fused) == 3, "Should have 3 unique documents"
    assert all("doc_id" in doc for doc in fused), "Custom ID field should be preserved"


@pytest.mark.unit
def test_rrf_preserves_document_data(vector_results, bm25_results):
    """Test that RRF preserves original document data."""
    fused = reciprocal_rank_fusion([vector_results, bm25_results], k=60)

    # Check that original fields are preserved
    for doc in fused:
        assert "text" in doc, "Original text field should be preserved"
        assert "score" in doc, "Original score field should be preserved"


# ============================================================================
# Test weighted_reciprocal_rank_fusion()
# ============================================================================


@pytest.mark.unit
def test_weighted_rrf_basic(vector_results, bm25_results):
    """Test basic weighted RRF."""
    weights = [0.7, 0.3]  # 70% vector, 30% BM25
    fused = weighted_reciprocal_rank_fusion(
        [vector_results, bm25_results],
        weights=weights,
        k=60,
    )

    assert len(fused) > 0, "Weighted RRF should return results"
    assert "weighted_rrf_score" in fused[0], "Should have weighted_rrf_score"
    assert "rrf_rank" in fused[0], "Should have rrf_rank"


@pytest.mark.unit
def test_weighted_rrf_default_weights(vector_results, bm25_results):
    """Test weighted RRF with default equal weights."""
    fused = weighted_reciprocal_rank_fusion([vector_results, bm25_results], k=60)

    assert len(fused) > 0, "Should work with default weights"
    # Default weights should be [0.5, 0.5]


@pytest.mark.unit
def test_weighted_rrf_weight_normalization():
    """Test that weights are normalized to sum to 1.0."""
    ranking1 = [{"id": "doc1"}, {"id": "doc2"}]
    ranking2 = [{"id": "doc2"}, {"id": "doc3"}]

    # Weights that don't sum to 1
    weights = [2.0, 4.0]  # Should be normalized to [0.33, 0.67]
    fused = weighted_reciprocal_rank_fusion(
        [ranking1, ranking2],
        weights=weights,
        k=60,
    )

    assert len(fused) > 0, "Should normalize weights automatically"


@pytest.mark.unit
def test_weighted_rrf_extreme_weights(vector_results, bm25_results):
    """Test weighted RRF with extreme weight values."""
    # Give almost all weight to vector search
    weights = [0.99, 0.01]
    fused = weighted_reciprocal_rank_fusion(
        [vector_results, bm25_results],
        weights=weights,
        k=60,
    )

    # Top result should be similar to vector-only ranking
    assert (
        fused[0]["id"] == vector_results[0]["id"]
    ), "Heavy vector weight should prioritize vector results"


@pytest.mark.unit
def test_weighted_rrf_empty_rankings():
    """Test weighted RRF with empty rankings."""
    fused = weighted_reciprocal_rank_fusion([], weights=[], k=60)
    assert fused == [], "Empty rankings should return empty list"


# ============================================================================
# Test analyze_ranking_diversity()
# ============================================================================


@pytest.mark.unit
def test_diversity_basic(vector_results, bm25_results):
    """Test basic ranking diversity analysis."""
    stats = analyze_ranking_diversity([vector_results, bm25_results], top_k=5)

    assert "total_unique_documents" in stats, "Should include total unique docs"
    assert "common_documents" in stats, "Should include common docs"
    assert "common_percentage" in stats, "Should include common percentage"
    assert "average_pairwise_overlap" in stats, "Should include average overlap"
    assert "ranking_count" in stats, "Should include ranking count"
    assert "analyzed_top_k" in stats, "Should include analyzed_top_k"

    assert stats["ranking_count"] == 2, "Should detect 2 rankings"
    assert stats["analyzed_top_k"] == 5, "Should analyze top 5"


@pytest.mark.unit
def test_diversity_no_overlap():
    """Test diversity with rankings that have no overlap."""
    ranking1 = [{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}]
    ranking2 = [{"id": "doc4"}, {"id": "doc5"}, {"id": "doc6"}]

    stats = analyze_ranking_diversity([ranking1, ranking2], top_k=3)

    assert stats["total_unique_documents"] == 6, "Should have 6 unique docs"
    assert stats["common_documents"] == 0, "Should have no common docs"
    assert stats["common_percentage"] == 0.0, "Common percentage should be 0"
    assert stats["average_pairwise_overlap"] == 0.0, "Overlap should be 0"


@pytest.mark.unit
def test_diversity_complete_overlap():
    """Test diversity with identical rankings."""
    ranking1 = [{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}]
    ranking2 = [{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}]

    stats = analyze_ranking_diversity([ranking1, ranking2], top_k=3)

    assert stats["total_unique_documents"] == 3, "Should have 3 unique docs"
    assert stats["common_documents"] == 3, "All docs should be common"
    assert stats["common_percentage"] == 100.0, "Common percentage should be 100%"
    assert stats["average_pairwise_overlap"] == 100.0, "Overlap should be 100%"


@pytest.mark.unit
def test_diversity_partial_overlap(vector_results, bm25_results):
    """Test diversity with partial overlap."""
    stats = analyze_ranking_diversity([vector_results, bm25_results], top_k=5)

    # doc1, doc2, doc3 are in both rankings
    assert stats["common_documents"] >= 2, "Should have some common documents"
    assert 0 < stats["common_percentage"] < 100, "Should have partial overlap"


@pytest.mark.unit
def test_diversity_empty_rankings():
    """Test diversity analysis with empty rankings."""
    stats = analyze_ranking_diversity([], top_k=10)
    assert stats == {}, "Empty rankings should return empty stats"


@pytest.mark.unit
def test_diversity_single_ranking():
    """Test diversity analysis with single ranking."""
    ranking = [{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}]
    stats = analyze_ranking_diversity([ranking], top_k=3)

    assert stats["total_unique_documents"] == 3, "Should have 3 unique docs"
    assert stats["common_documents"] == 3, "All docs should be common in single ranking"
    assert stats["ranking_count"] == 1, "Should detect 1 ranking"


@pytest.mark.unit
def test_diversity_multiple_rankings():
    """Test diversity analysis with 3+ rankings."""
    ranking1 = [{"id": "doc1"}, {"id": "doc2"}]
    ranking2 = [{"id": "doc2"}, {"id": "doc3"}]
    ranking3 = [{"id": "doc1"}, {"id": "doc3"}]

    stats = analyze_ranking_diversity([ranking1, ranking2, ranking3], top_k=2)

    assert stats["ranking_count"] == 3, "Should detect 3 rankings"
    assert stats["total_unique_documents"] == 3, "Should have 3 unique docs"


@pytest.mark.unit
@pytest.mark.parametrize("top_k", [1, 5, 10, 20])
def test_diversity_different_top_k(vector_results, bm25_results, top_k):
    """Test diversity analysis with different top_k values."""
    stats = analyze_ranking_diversity([vector_results, bm25_results], top_k=top_k)

    assert stats["analyzed_top_k"] == top_k, f"Should analyze top {top_k}"
    assert stats["total_unique_documents"] <= top_k * 2, "Unique docs should be at most 2 * top_k"


# ============================================================================
# Edge Cases & Error Handling
# ============================================================================


@pytest.mark.unit
def test_rrf_with_missing_id_field():
    """Test RRF when documents don't have ID field (should use text or rank)."""
    ranking1 = [{"text": "doc1 text"}, {"text": "doc2 text"}]
    ranking2 = [{"text": "doc2 text"}, {"text": "doc3 text"}]

    # Should fall back to "text" field for ID
    fused = reciprocal_rank_fusion([ranking1, ranking2], k=60, id_field="id")

    assert len(fused) > 0, "Should handle missing ID field"


@pytest.mark.unit
def test_rrf_preserves_rank_order():
    """Test that RRF ranks are sequential from 1."""
    ranking1 = [{"id": f"doc{i}"} for i in range(10)]
    ranking2 = [{"id": f"doc{i}"} for i in range(10, 20)]

    fused = reciprocal_rank_fusion([ranking1, ranking2], k=60)

    # Verify ranks are sequential
    for i, doc in enumerate(fused):
        assert doc["rrf_rank"] == i + 1, f"RRF rank should be {i + 1}, got {doc['rrf_rank']}"


@pytest.mark.unit
def test_weighted_rrf_zero_weight():
    """Test weighted RRF with zero weight (should ignore that ranking)."""
    ranking1 = [{"id": "doc1"}, {"id": "doc2"}]
    ranking2 = [{"id": "doc3"}, {"id": "doc4"}]

    weights = [1.0, 0.0]  # Ignore second ranking
    fused = weighted_reciprocal_rank_fusion(
        [ranking1, ranking2],
        weights=weights,
        k=60,
    )

    # Top results should be from ranking1
    top_ids = [doc["id"] for doc in fused[:2]]
    assert "doc1" in top_ids, "Zero weight should ignore ranking2"
    assert "doc2" in top_ids, "Zero weight should ignore ranking2"
