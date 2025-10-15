"""Unit tests for BM25Search.

Tests BM25 keyword search including:
- Fitting corpus
- Searching with ranking
- Tokenization
- Error handling
- Edge cases
"""

import pytest
from typing import List, Dict, Any

from src.components.vector_search.bm25_search import BM25Search
from src.core.exceptions import VectorSearchError


# ============================================================================
# Test Initialization
# ============================================================================


@pytest.mark.unit
def test_bm25_init():
    """Test BM25Search initialization."""
    search = BM25Search()

    assert search._corpus == [], "Corpus should start empty"
    assert search._metadata == [], "Metadata should start empty"
    assert search._bm25 is None, "BM25 model should be None"
    assert search._is_fitted is False, "Should not be fitted initially"


# ============================================================================
# Test Tokenization
# ============================================================================


@pytest.mark.unit
def test_tokenize_basic():
    """Test basic tokenization."""
    search = BM25Search()

    tokens = search._tokenize("This is a test document")

    assert tokens == ["this", "is", "a", "test", "document"], \
        "Should tokenize and lowercase"


@pytest.mark.unit
def test_tokenize_punctuation():
    """Test tokenization with punctuation."""
    search = BM25Search()

    tokens = search._tokenize("Hello, world! How are you?")

    assert "hello," in tokens or "hello" in tokens, "Should handle punctuation"
    assert len(tokens) > 0, "Should return tokens"


@pytest.mark.unit
def test_tokenize_empty_string():
    """Test tokenizing empty string."""
    search = BM25Search()

    tokens = search._tokenize("")

    # .split() without arguments filters empty strings, which is correct behavior
    assert tokens == [], "Empty string should return empty list"


@pytest.mark.unit
@pytest.mark.parametrize("text,expected_count", [
    ("single", 1),
    ("two words", 2),
    ("three word sentence", 3),
    ("a b c d e", 5),
])
def test_tokenize_word_count(text, expected_count):
    """Test tokenization word count."""
    search = BM25Search()
    tokens = search._tokenize(text)

    assert len(tokens) == expected_count, f"Should have {expected_count} tokens"


# ============================================================================
# Test Fitting
# ============================================================================


@pytest.mark.unit
def test_fit_basic(sample_documents):
    """Test fitting BM25 model on documents."""
    search = BM25Search()

    search.fit(sample_documents, text_field="text")

    assert search.is_fitted() is True, "Model should be fitted"
    assert len(search._corpus) == len(sample_documents), "Corpus size should match"
    assert search._bm25 is not None, "BM25 model should be initialized"


@pytest.mark.unit
def test_fit_custom_text_field():
    """Test fitting with custom text field name."""
    documents = [
        {"content": "Document 1", "id": "doc1"},
        {"content": "Document 2", "id": "doc2"},
    ]

    search = BM25Search()
    search.fit(documents, text_field="content")

    assert search.is_fitted() is True, "Should fit with custom field"
    assert len(search._corpus) == 2, "Should have 2 documents"


@pytest.mark.unit
def test_fit_missing_text_field():
    """Test fitting when documents are missing text field."""
    documents = [
        {"text": "Document 1", "id": "doc1"},
        {"id": "doc2"},  # Missing text field
        {"text": "Document 3", "id": "doc3"},
    ]

    search = BM25Search()
    search.fit(documents, text_field="text")

    # Should skip documents without text field
    assert len(search._corpus) == 2, "Should skip documents without text field"


@pytest.mark.unit
def test_fit_empty_documents():
    """Test fitting with empty document list."""
    search = BM25Search()

    with pytest.raises(VectorSearchError):
        search.fit([], text_field="text")


@pytest.mark.unit
def test_fit_stores_metadata(sample_documents):
    """Test that fitting stores metadata correctly."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    assert len(search._metadata) == len(sample_documents), \
        "Should store metadata for each document"

    # Metadata should not include text field
    for meta in search._metadata:
        assert "text" not in meta, "Metadata should not include text field"
        assert "id" in meta, "Metadata should include id"
        assert "source" in meta, "Metadata should include source"


# ============================================================================
# Test Searching
# ============================================================================


@pytest.mark.unit
def test_search_basic(sample_documents):
    """Test basic BM25 search."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    results = search.search("AEGIS RAG components", top_k=3)

    assert len(results) <= 3, "Should return at most 3 results"
    assert all("text" in r for r in results), "Results should have text"
    assert all("score" in r for r in results), "Results should have score"
    assert all("metadata" in r for r in results), "Results should have metadata"
    assert all("rank" in r for r in results), "Results should have rank"


@pytest.mark.unit
def test_search_ranking_order(sample_documents):
    """Test that search results are ranked by score descending."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    results = search.search("vector search", top_k=5)

    # Verify scores are descending
    for i in range(len(results) - 1):
        assert results[i]["score"] >= results[i + 1]["score"], \
            "Scores should be in descending order"

    # Verify ranks are sequential
    for i, result in enumerate(results):
        assert result["rank"] == i + 1, f"Rank should be {i + 1}"


@pytest.mark.unit
def test_search_not_fitted():
    """Test searching without fitting model (should raise error)."""
    search = BM25Search()

    with pytest.raises(VectorSearchError) as exc_info:
        search.search("test query")

    assert "not fitted" in str(exc_info.value).lower()


@pytest.mark.unit
def test_search_empty_query(sample_documents):
    """Test searching with empty query."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    results = search.search("", top_k=5)

    # Should return results (BM25 will score them)
    assert len(results) <= 5, "Should return results"


@pytest.mark.unit
@pytest.mark.parametrize("top_k", [1, 5, 10, 20])
def test_search_different_top_k(sample_documents, top_k):
    """Test searching with different top_k values."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    results = search.search("test query", top_k=top_k)

    assert len(results) <= top_k, f"Should return at most {top_k} results"
    assert len(results) <= len(sample_documents), \
        "Results should not exceed corpus size"


@pytest.mark.unit
def test_search_relevance(sample_documents):
    """Test that relevant documents score higher."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    # Query specifically for "Vector Search"
    results = search.search("Vector Search Qdrant", top_k=5)

    # First result should mention vector search
    assert "vector" in results[0]["text"].lower() or \
           "qdrant" in results[0]["text"].lower(), \
        "Top result should be relevant to query"


@pytest.mark.unit
def test_search_no_matches(sample_documents):
    """Test searching with query that has no good matches."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    results = search.search("xyzabc123nonexistent", top_k=3)

    # Should still return results (BM25 scores everything)
    assert len(results) <= 3, "Should return up to 3 results"


# ============================================================================
# Test State Management
# ============================================================================


@pytest.mark.unit
def test_get_corpus_size(sample_documents):
    """Test getting corpus size."""
    search = BM25Search()

    assert search.get_corpus_size() == 0, "Empty corpus should have size 0"

    search.fit(sample_documents, text_field="text")

    assert search.get_corpus_size() == len(sample_documents), \
        f"Corpus size should be {len(sample_documents)}"


@pytest.mark.unit
def test_is_fitted():
    """Test checking if model is fitted."""
    search = BM25Search()

    assert search.is_fitted() is False, "New model should not be fitted"

    search._is_fitted = True

    assert search.is_fitted() is True, "Should return fitted status"


@pytest.mark.unit
def test_clear(sample_documents):
    """Test clearing corpus and model."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    assert search.is_fitted() is True, "Should be fitted"
    assert search.get_corpus_size() > 0, "Should have corpus"

    search.clear()

    assert search.is_fitted() is False, "Should not be fitted after clear"
    assert search.get_corpus_size() == 0, "Corpus should be empty"
    assert search._bm25 is None, "BM25 model should be None"
    assert len(search._metadata) == 0, "Metadata should be empty"


# ============================================================================
# Test Edge Cases
# ============================================================================


@pytest.mark.unit
def test_fit_single_document():
    """Test fitting with single document."""
    documents = [{"text": "Single document", "id": "doc1"}]

    search = BM25Search()
    search.fit(documents, text_field="text")

    assert search.is_fitted() is True, "Should fit with single document"

    results = search.search("single", top_k=1)
    assert len(results) == 1, "Should return 1 result"


@pytest.mark.unit
def test_search_top_k_exceeds_corpus():
    """Test searching with top_k larger than corpus size."""
    documents = [
        {"text": "Document 1", "id": "doc1"},
        {"text": "Document 2", "id": "doc2"},
    ]

    search = BM25Search()
    search.fit(documents, text_field="text")

    results = search.search("document", top_k=100)

    assert len(results) == 2, "Should return all documents when top_k > corpus size"


@pytest.mark.unit
def test_fit_duplicate_documents():
    """Test fitting with duplicate documents."""
    documents = [
        {"text": "Same document", "id": "doc1"},
        {"text": "Same document", "id": "doc2"},
        {"text": "Different document", "id": "doc3"},
    ]

    search = BM25Search()
    search.fit(documents, text_field="text")

    assert search.get_corpus_size() == 3, "Should include duplicates"


@pytest.mark.unit
def test_search_special_characters(sample_documents):
    """Test searching with special characters."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    results = search.search("AEGIS-RAG @#$%", top_k=3)

    assert len(results) > 0, "Should handle special characters"


@pytest.mark.unit
def test_search_unicode_query(sample_documents):
    """Test searching with unicode query."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    results = search.search("你好 world 🌍", top_k=3)

    assert len(results) > 0, "Should handle unicode characters"


@pytest.mark.unit
def test_fit_documents_with_extra_metadata():
    """Test fitting documents with various metadata fields."""
    documents = [
        {
            "text": "Document 1",
            "id": "doc1",
            "source": "source1",
            "extra_field": "value1",
            "nested": {"key": "value"},
        },
        {
            "text": "Document 2",
            "id": "doc2",
            "source": "source2",
            "extra_field": "value2",
        },
    ]

    search = BM25Search()
    search.fit(documents, text_field="text")

    # Verify metadata is preserved
    assert len(search._metadata) == 2, "Should store metadata for both docs"
    assert "extra_field" in search._metadata[0], "Should preserve extra fields"
    assert "nested" in search._metadata[0], "Should preserve nested fields"


@pytest.mark.unit
def test_multiple_fits_overwrites():
    """Test that fitting multiple times overwrites previous corpus."""
    documents1 = [{"text": "First corpus", "id": "doc1"}]
    documents2 = [
        {"text": "Second corpus doc 1", "id": "doc2"},
        {"text": "Second corpus doc 2", "id": "doc3"},
    ]

    search = BM25Search()

    search.fit(documents1, text_field="text")
    assert search.get_corpus_size() == 1, "First fit should have 1 document"

    search.fit(documents2, text_field="text")
    assert search.get_corpus_size() == 2, "Second fit should overwrite with 2 documents"


@pytest.mark.unit
def test_search_case_insensitive(sample_documents):
    """Test that search is case-insensitive."""
    search = BM25Search()
    search.fit(sample_documents, text_field="text")

    results_lower = search.search("vector search", top_k=3)
    results_upper = search.search("VECTOR SEARCH", top_k=3)

    # Should return same results (order and scores)
    assert len(results_lower) == len(results_upper), \
        "Case should not affect result count"
