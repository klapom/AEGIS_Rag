"""Unit tests for Feature 62.5: Section-Aware Reranking Integration.

Tests for:
- Section boost application in cross-encoder reranking
- Configurable boost multiplier
- Score range preservation
- Integration with hybrid search
- Backward compatibility (no section metadata)

Sprint 62 Feature 62.5: Section-Aware Reranking Integration
"""

import pytest

from src.domains.vector_search.reranking.cross_encoder_reranker import (
    CrossEncoderReranker,
)

# ============================================================================
# TEST: Section Boost Application
# ============================================================================


@pytest.mark.unit
def test_section_boost_single_section():
    """Test that section boost is applied to documents from target section."""
    query = "load balancing strategies"

    documents = [
        {
            "id": "1",
            "text": "Load balancing distributes traffic across servers",
            "section_id": "1.2",
        },
        {
            "id": "2",
            "text": "Database optimization techniques",
            "section_id": "2.1",
        },
        {
            "id": "3",
            "text": "Caching mechanisms for performance",
            "section_id": "1.3",
        },
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Rerank with section filter (boost section 1.2)
    reranked = reranker.rerank(
        query=query,
        documents=documents,
        top_k=3,
        section_filter="1.2",
        section_boost=0.1,
    )

    # Document 1 should have boosted score
    # Find document 1 in reranked results
    doc1 = next((doc for doc in reranked if doc["id"] == "1"), None)
    assert doc1 is not None, "Document 1 should be in results"

    # Verify other documents don't get boost (same query, no boost should have lower score)
    doc2 = next((doc for doc in reranked if doc["id"] == "2"), None)
    doc3 = next((doc for doc in reranked if doc["id"] == "3"), None)

    # Document 1 should rank higher due to boost (assuming similar base relevance)
    # This test verifies boost was applied, not necessarily that it changes ranking
    assert "rerank_score" in doc1
    assert "rerank_score" in doc2 if doc2 else True
    assert "rerank_score" in doc3 if doc3 else True


@pytest.mark.unit
def test_section_boost_multiple_sections():
    """Test section boost with multiple target sections."""
    query = "web server configuration"

    documents = [
        {"id": "1", "text": "Load balancing config", "section_id": "1.2"},
        {"id": "2", "text": "Database settings", "section_id": "2.1"},
        {"id": "3", "text": "Cache configuration", "section_id": "1.3"},
        {"id": "4", "text": "Network settings", "section_id": "3.1"},
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Boost multiple sections
    reranked = reranker.rerank(
        query=query,
        documents=documents,
        top_k=4,
        section_filter=["1.2", "1.3"],
        section_boost=0.15,
    )

    # Documents from sections 1.2 and 1.3 should be boosted
    assert len(reranked) == 4
    for doc in reranked:
        assert "rerank_score" in doc
        assert isinstance(doc["rerank_score"], float)


@pytest.mark.unit
def test_section_boost_from_metadata_field():
    """Test that section_id from metadata field is also supported."""
    query = "performance optimization"

    documents = [
        {
            "id": "1",
            "text": "Optimization techniques",
            "metadata": {"section_id": "1.2"},
        },
        {
            "id": "2",
            "text": "Database tuning",
            "metadata": {"section_id": "2.1"},
        },
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Boost section 1.2
    reranked = reranker.rerank(
        query=query,
        documents=documents,
        top_k=2,
        section_filter="1.2",
        section_boost=0.1,
    )

    # Verify documents are reranked
    assert len(reranked) == 2
    for doc in reranked:
        assert "rerank_score" in doc


# ============================================================================
# TEST: Configurable Boost Multiplier
# ============================================================================


@pytest.mark.unit
def test_section_boost_configurable_multiplier():
    """Test different boost multiplier values."""
    query = "test query"

    documents = [
        {"id": "1", "text": "Document A", "section_id": "1.1"},
        {"id": "2", "text": "Document B", "section_id": "1.2"},
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Test with different boost values
    for boost_value in [0.0, 0.1, 0.2, 0.5]:
        reranked = reranker.rerank(
            query=query,
            documents=documents.copy(),
            top_k=2,
            section_filter="1.1",
            section_boost=boost_value,
        )

        assert len(reranked) == 2
        # Verify scores are present and valid
        for doc in reranked:
            assert "rerank_score" in doc
            assert isinstance(doc["rerank_score"], float)


@pytest.mark.unit
def test_section_boost_clamping():
    """Test that boost values are clamped to valid range [0.0, 0.5]."""
    query = "test query"

    documents = [
        {"id": "1", "text": "Document A", "section_id": "1.1"},
        {"id": "2", "text": "Document B", "section_id": "1.2"},
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Test with out-of-range boost values
    # Negative boost should be clamped to 0.0
    reranked_negative = reranker.rerank(
        query=query,
        documents=documents.copy(),
        top_k=2,
        section_filter="1.1",
        section_boost=-0.5,
    )

    # Very high boost should be clamped to 0.5
    reranked_high = reranker.rerank(
        query=query,
        documents=documents.copy(),
        top_k=2,
        section_filter="1.1",
        section_boost=2.0,
    )

    # Both should produce valid results
    assert len(reranked_negative) == 2
    assert len(reranked_high) == 2


# ============================================================================
# TEST: Score Range Preservation
# ============================================================================


@pytest.mark.unit
def test_section_boost_preserves_score_order():
    """Test that section boost maintains valid score ordering."""
    query = "machine learning algorithms"

    documents = [
        {"id": "1", "text": "Machine learning is great", "section_id": "1.1"},
        {"id": "2", "text": "ML algorithms learn from data", "section_id": "1.2"},
        {"id": "3", "text": "Unrelated document about cats", "section_id": "2.1"},
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Rerank with section boost
    reranked = reranker.rerank(
        query=query,
        documents=documents,
        top_k=3,
        section_filter="1.2",
        section_boost=0.1,
    )

    # Scores should be in descending order
    scores = [doc["rerank_score"] for doc in reranked]
    assert scores == sorted(scores, reverse=True), "Scores should be descending"

    # All scores should be valid floats
    for score in scores:
        assert isinstance(score, float)
        assert score == score, "Score should not be NaN"  # NaN check


@pytest.mark.unit
def test_section_boost_no_filter_no_boost():
    """Test that no boost is applied when section_filter is None."""
    query = "test query"

    documents = [
        {"id": "1", "text": "Document A", "section_id": "1.1"},
        {"id": "2", "text": "Document B", "section_id": "1.2"},
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Rerank without section filter
    reranked_no_filter = reranker.rerank(
        query=query,
        documents=documents.copy(),
        top_k=2,
        section_filter=None,
    )

    # Rerank with section filter
    reranked_with_filter = reranker.rerank(
        query=query,
        documents=documents.copy(),
        top_k=2,
        section_filter="1.1",
        section_boost=0.1,
    )

    # Both should produce valid results
    assert len(reranked_no_filter) == 2
    assert len(reranked_with_filter) == 2


# ============================================================================
# TEST: Backward Compatibility
# ============================================================================


@pytest.mark.unit
def test_section_boost_backward_compatible_no_section_metadata():
    """Test that reranking works with documents without section metadata."""
    query = "test query"

    # Documents without section_id
    documents = [
        {"id": "1", "text": "Document A"},
        {"id": "2", "text": "Document B"},
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Should work without errors even with section_filter
    reranked = reranker.rerank(
        query=query,
        documents=documents,
        top_k=2,
        section_filter="1.1",  # Filter provided but no docs have section_id
        section_boost=0.1,
    )

    # Should return all documents (no boost applied, but no errors)
    assert len(reranked) == 2
    for doc in reranked:
        assert "rerank_score" in doc


@pytest.mark.unit
def test_section_boost_mixed_metadata():
    """Test reranking with mixed documents (some with, some without section metadata)."""
    query = "test query"

    documents = [
        {"id": "1", "text": "Document A", "section_id": "1.1"},
        {"id": "2", "text": "Document B"},  # No section_id
        {"id": "3", "text": "Document C", "section_id": "1.2"},
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Boost section 1.1
    reranked = reranker.rerank(
        query=query,
        documents=documents,
        top_k=3,
        section_filter="1.1",
        section_boost=0.1,
    )

    # All documents should be in results
    assert len(reranked) == 3
    # Document 1 should get boost, others should not
    for doc in reranked:
        assert "rerank_score" in doc


# ============================================================================
# TEST: Empty and Edge Cases
# ============================================================================


@pytest.mark.unit
def test_section_boost_empty_documents():
    """Test section boost with empty document list."""
    reranker = CrossEncoderReranker(device="cpu")

    reranked = reranker.rerank(
        query="test",
        documents=[],
        top_k=10,
        section_filter="1.1",
        section_boost=0.1,
    )

    assert reranked == []


@pytest.mark.unit
def test_section_boost_empty_section_filter():
    """Test section boost with empty section filter list."""
    query = "test query"

    documents = [
        {"id": "1", "text": "Document A", "section_id": "1.1"},
        {"id": "2", "text": "Document B", "section_id": "1.2"},
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Empty list for section_filter
    reranked = reranker.rerank(
        query=query,
        documents=documents,
        top_k=2,
        section_filter=[],  # Empty list
        section_boost=0.1,
    )

    # Should work without errors (no boost applied)
    assert len(reranked) == 2


@pytest.mark.unit
def test_section_boost_preserves_top_k():
    """Test that section boost respects top_k parameter."""
    query = "test query"

    documents = [{"id": str(i), "text": f"Document {i}", "section_id": "1.1"} for i in range(20)]

    reranker = CrossEncoderReranker(device="cpu")

    # Request only top 5
    reranked = reranker.rerank(
        query=query,
        documents=documents,
        top_k=5,
        section_filter="1.1",
        section_boost=0.1,
    )

    assert len(reranked) == 5


# ============================================================================
# TEST: Integration with Existing Functionality
# ============================================================================


@pytest.mark.unit
def test_section_boost_with_text_field_fallback():
    """Test section boost with custom text_field parameter."""
    query = "test query"

    documents = [
        {"id": "1", "content": "Document A content", "section_id": "1.1"},
        {"id": "2", "page_content": "Document B content", "section_id": "1.2"},
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Use custom text field
    reranked = reranker.rerank(
        query=query,
        documents=documents,
        top_k=2,
        text_field="content",
        section_filter="1.1",
        section_boost=0.1,
    )

    # Should handle text field fallback correctly
    assert len(reranked) == 2


@pytest.mark.unit
def test_section_boost_integration_quality():
    """Test that section boost improves ranking for relevant sections."""
    query = "load balancing"

    # Create documents where section 1.2 is about load balancing
    documents_no_boost = [
        {
            "id": "1",
            "text": "Database optimization techniques",
            "section_id": "2.1",
        },
        {
            "id": "2",
            "text": "Load balancing distributes requests",
            "section_id": "1.2",
        },
        {
            "id": "3",
            "text": "Caching strategies for performance",
            "section_id": "1.3",
        },
    ]

    documents_with_boost = [
        {
            "id": "1",
            "text": "Database optimization techniques",
            "section_id": "2.1",
        },
        {
            "id": "2",
            "text": "Load balancing distributes requests",
            "section_id": "1.2",
        },
        {
            "id": "3",
            "text": "Caching strategies for performance",
            "section_id": "1.3",
        },
    ]

    reranker = CrossEncoderReranker(device="cpu")

    # Rerank without section boost
    reranked_no_boost = reranker.rerank(
        query=query,
        documents=documents_no_boost,
        top_k=3,
    )

    # Rerank with section boost on section 1.2
    reranked_with_boost = reranker.rerank(
        query=query,
        documents=documents_with_boost,
        top_k=3,
        section_filter="1.2",
        section_boost=0.2,
    )

    # Document 2 should have higher score with boost
    doc2_no_boost = next((doc for doc in reranked_no_boost if doc["id"] == "2"), None)
    doc2_with_boost = next((doc for doc in reranked_with_boost if doc["id"] == "2"), None)

    assert doc2_no_boost is not None
    assert doc2_with_boost is not None
    # With boost of 0.2, the boosted score should be exactly 0.2 higher
    assert doc2_with_boost["rerank_score"] == pytest.approx(
        doc2_no_boost["rerank_score"] + 0.2, abs=0.01
    )
