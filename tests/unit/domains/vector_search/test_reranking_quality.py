"""Verify Cross-Encoder reranking quality.

Sprint 61 Feature 61.2: Ensure comparable quality to LLM reranking.
"""

import pytest
from src.domains.vector_search.reranking import CrossEncoderReranker


@pytest.mark.unit
def test_reranking_quality():
    """Test that Cross-Encoder produces reasonable ranking."""
    query = "What is machine learning?"

    documents = [
        {"text": "Machine learning is a subset of AI.", "id": 1},
        {"text": "The weather is nice today.", "id": 2},
        {"text": "ML algorithms learn from data.", "id": 3},
        {"text": "Unrelated document about cats.", "id": 4},
    ]

    reranker = CrossEncoderReranker(device="cpu")
    reranked = reranker.rerank(query, documents, top_k=4)

    # Top 2 should be relevant documents (ID 1, 3)
    top_ids = {reranked[0]["id"], reranked[1]["id"]}
    assert top_ids == {1, 3}, f"Expected IDs 1,3 in top 2, got {top_ids}"

    # Scores should be descending
    scores = [doc["rerank_score"] for doc in reranked]
    assert scores == sorted(scores, reverse=True), "Scores not in descending order"

    # Relevant docs should have higher scores than irrelevant
    relevant_scores = [reranked[0]["rerank_score"], reranked[1]["rerank_score"]]
    irrelevant_scores = [reranked[2]["rerank_score"], reranked[3]["rerank_score"]]
    assert min(relevant_scores) > max(irrelevant_scores), \
        "Relevant docs should score higher than irrelevant"


@pytest.mark.unit
def test_reranking_empty_documents():
    """Test that reranker handles empty document list."""
    reranker = CrossEncoderReranker(device="cpu")
    result = reranker.rerank("test query", [], top_k=10)
    assert result == [], "Empty documents should return empty list"


@pytest.mark.unit
def test_reranking_top_k_limit():
    """Test that reranker respects top_k parameter."""
    query = "machine learning"
    documents = [{"text": f"Document {i} about ML.", "id": i} for i in range(20)]

    reranker = CrossEncoderReranker(device="cpu")
    reranked = reranker.rerank(query, documents, top_k=5)

    assert len(reranked) == 5, f"Expected 5 documents, got {len(reranked)}"


@pytest.mark.unit
def test_reranking_adds_score_field():
    """Test that reranker adds rerank_score to each document."""
    query = "test query"
    documents = [
        {"text": "Document 1", "id": 1},
        {"text": "Document 2", "id": 2},
    ]

    reranker = CrossEncoderReranker(device="cpu")
    reranked = reranker.rerank(query, documents, top_k=10)

    for doc in reranked:
        assert "rerank_score" in doc, "Document should have rerank_score field"
        assert isinstance(doc["rerank_score"], float), "Score should be float"


@pytest.mark.unit
def test_reranking_fallback_text_fields():
    """Test that reranker uses fallback text fields if 'text' is missing."""
    query = "machine learning"
    documents = [
        {"content": "ML is great", "id": 1},  # 'content' field
        {"page_content": "AI systems", "id": 2},  # 'page_content' field
        {"text": "Data science", "id": 3},  # 'text' field (standard)
    ]

    reranker = CrossEncoderReranker(device="cpu")
    reranked = reranker.rerank(query, documents, top_k=10)

    # All documents should have scores
    assert len(reranked) == 3
    for doc in reranked:
        assert "rerank_score" in doc
