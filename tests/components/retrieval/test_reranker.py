"""Unit tests for CrossEncoderReranker (Sprint 3).

Tests cover:
- Reranker initialization and configuration
- Lazy model loading
- Reranking with mocked cross-encoder
- Score normalization (sigmoid)
- Top-k filtering
- Score threshold filtering
- Empty document handling
- Error handling
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
import numpy as np

from src.components.retrieval.reranker import CrossEncoderReranker, RerankResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_cross_encoder():
    """Mock CrossEncoder model."""
    mock_model = MagicMock()
    mock_model.predict = MagicMock(
        return_value=np.array([2.5, 1.0, 0.5, -0.5, -1.0])  # Simulated scores
    )
    return mock_model


@pytest.fixture
def sample_documents():
    """Sample documents for reranking."""
    return [
        {
            "id": "doc1",
            "text": "Vector search uses embeddings to find semantically similar documents.",
            "score": 0.85,
            "metadata": {"source": "docs.rag.com"},
        },
        {
            "id": "doc2",
            "text": "BM25 is a keyword-based search algorithm.",
            "score": 0.75,
            "metadata": {"source": "wikipedia.org"},
        },
        {
            "id": "doc3",
            "text": "Hybrid search combines vector and keyword approaches.",
            "score": 0.70,
            "metadata": {"source": "blog.ai.com"},
        },
        {
            "id": "doc4",
            "text": "Reranking improves precision by rescoring candidates.",
            "score": 0.60,
            "metadata": {"source": "arxiv.org"},
        },
        {
            "id": "doc5",
            "text": "Cross-encoders jointly encode query and document.",
            "score": 0.55,
            "metadata": {"source": "huggingface.co"},
        },
    ]


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.unit
def test_reranker_initialization_defaults():
    """Test reranker initialization with default settings."""
    reranker = CrossEncoderReranker()

    assert reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert reranker.batch_size == 32
    assert "models" in str(reranker.cache_dir)  # Platform-independent path check
    assert reranker._model is None  # Lazy-loaded


@pytest.mark.unit
def test_reranker_initialization_custom():
    """Test reranker initialization with custom settings."""
    reranker = CrossEncoderReranker(
        model_name="custom-model", batch_size=16, cache_dir="./custom_cache"
    )

    assert reranker.model_name == "custom-model"
    assert reranker.batch_size == 16
    assert "custom_cache" in str(reranker.cache_dir)


@pytest.mark.unit
@patch("src.components.retrieval.reranker.CrossEncoder")
def test_lazy_model_loading(mock_ce_class):
    """Test that model is only loaded on first access."""
    mock_model = MagicMock()
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    assert reranker._model is None

    # Access model property
    _ = reranker.model
    assert reranker._model is mock_model

    # Verify model was instantiated correctly
    # Note: sentence-transformers 3.4+ uses cache_dir instead of cache_folder
    mock_ce_class.assert_called_once_with(
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        max_length=512,
        device="cpu",
        cache_dir=str(reranker.cache_dir),
    )


# ============================================================================
# Reranking Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_basic(mock_ce_class, sample_documents):
    """Test basic reranking functionality."""
    mock_model = MagicMock()
    # Scores that will reorder documents
    mock_model.predict.return_value = np.array([1.0, 3.0, 2.0, 0.5, -1.0])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(
        query="What is hybrid search?", documents=sample_documents
    )

    assert len(results) == 5
    assert isinstance(results[0], RerankResult)

    # Check reordering: doc2 should be first (score 3.0)
    assert results[0].doc_id == "doc2"
    assert results[1].doc_id == "doc3"  # score 2.0
    assert results[2].doc_id == "doc1"  # score 1.0

    # Verify ranks are updated
    assert results[0].final_rank == 0
    assert results[1].final_rank == 1
    assert results[2].final_rank == 2


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_top_k(mock_ce_class, sample_documents):
    """Test top-k filtering in reranking."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1.0, 3.0, 2.0, 0.5, -1.0])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(
        query="What is hybrid search?", documents=sample_documents, top_k=3
    )

    assert len(results) == 3
    assert results[0].doc_id == "doc2"  # Highest score
    assert results[1].doc_id == "doc3"
    assert results[2].doc_id == "doc1"


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_score_threshold(mock_ce_class, sample_documents):
    """Test score threshold filtering."""
    mock_model = MagicMock()
    # Scores: [1.0, 3.0, 2.0, 0.5, -1.0]
    # After sigmoid: [0.73, 0.95, 0.88, 0.62, 0.27]
    mock_model.predict.return_value = np.array([1.0, 3.0, 2.0, 0.5, -1.0])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(
        query="What is hybrid search?",
        documents=sample_documents,
        score_threshold=0.70,  # Filter out scores < 0.70
    )

    # Only 3 docs should pass threshold (0.95, 0.88, 0.73)
    assert len(results) == 3
    assert all(r.final_score >= 0.70 for r in results)


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_score_normalization(mock_ce_class, sample_documents):
    """Test that rerank scores are normalized with sigmoid."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([0.0, 2.0, -2.0])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(
        query="test", documents=sample_documents[:3], top_k=3
    )

    # Sigmoid(0.0) ≈ 0.5, Sigmoid(2.0) ≈ 0.88, Sigmoid(-2.0) ≈ 0.12
    assert results[0].rerank_score == 2.0
    assert 0.87 < results[0].final_score < 0.89

    assert results[1].rerank_score == 0.0
    assert 0.49 < results[1].final_score < 0.51

    assert results[2].rerank_score == -2.0
    assert 0.11 < results[2].final_score < 0.13


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_preserves_metadata(mock_ce_class, sample_documents):
    """Test that metadata is preserved through reranking."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1.0, 2.0, 0.5, 0.0, -1.0])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(query="test", documents=sample_documents)

    # Check metadata is preserved
    assert results[0].metadata["source"] == "wikipedia.org"  # doc2 (score 2.0)
    assert results[1].metadata["source"] == "docs.rag.com"  # doc1 (score 1.0)


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_original_scores_preserved(mock_ce_class, sample_documents):
    """Test that original scores are preserved."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1.0, 2.0, 0.5, 0.0, -1.0])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(query="test", documents=sample_documents)

    # Original scores should be preserved
    assert results[0].original_score == 0.75  # doc2
    assert results[1].original_score == 0.85  # doc1
    assert results[2].original_score == 0.70  # doc3


# ============================================================================
# Edge Cases & Error Handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_empty_documents(mock_ce_class):
    """Test reranking with empty document list."""
    mock_model = MagicMock()
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(query="test", documents=[])

    assert results == []
    mock_model.predict.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_single_document(mock_ce_class):
    """Test reranking with single document."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1.5])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(
        query="test",
        documents=[
            {
                "id": "doc1",
                "text": "Test document",
                "score": 0.8,
                "metadata": {},
            }
        ],
    )

    assert len(results) == 1
    assert results[0].doc_id == "doc1"
    assert results[0].final_rank == 0


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_top_k_larger_than_docs(mock_ce_class, sample_documents):
    """Test top-k larger than number of documents."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1.0, 2.0, 0.5, 0.0, -1.0])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(
        query="test", documents=sample_documents, top_k=100  # More than 5 docs
    )

    # Should return all documents
    assert len(results) == 5


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_missing_text_field(mock_ce_class):
    """Test reranking with documents missing text field."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1.0, 2.0])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker()
    results = await reranker.rerank(
        query="test",
        documents=[
            {"id": "doc1", "score": 0.8},  # Missing 'text'
            {"id": "doc2", "text": "Valid text", "score": 0.7},
        ],
    )

    # Should handle missing text gracefully (empty string)
    assert len(results) == 2
    mock_model.predict.assert_called_once()
    # Check that pairs were created (even with empty text)
    call_args = mock_model.predict.call_args[0][0]
    assert call_args[0] == ("test", "")  # doc1 has no text
    assert call_args[1] == ("test", "Valid text")  # doc2 has text


# ============================================================================
# Model Info Tests
# ============================================================================


@pytest.mark.unit
def test_get_model_info_before_loading():
    """Test get_model_info before model is loaded."""
    reranker = CrossEncoderReranker(model_name="test-model", batch_size=16)
    info = reranker.get_model_info()

    assert info["model_name"] == "test-model"
    assert info["batch_size"] == 16
    assert info["is_loaded"] is False
    assert "cache_dir" in info


@pytest.mark.unit
@patch("src.components.retrieval.reranker.CrossEncoder")
def test_get_model_info_after_loading(mock_ce_class):
    """Test get_model_info after model is loaded."""
    mock_model = MagicMock()
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker(model_name="test-model")
    _ = reranker.model  # Trigger lazy loading

    info = reranker.get_model_info()
    assert info["is_loaded"] is True


# ============================================================================
# Batch Processing Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.components.retrieval.reranker.CrossEncoder")
async def test_rerank_batch_size_respected(mock_ce_class, sample_documents):
    """Test that batch_size parameter is passed to model.predict."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1.0, 2.0, 0.5, 0.0, -1.0])
    mock_ce_class.return_value = mock_model

    reranker = CrossEncoderReranker(batch_size=2)
    await reranker.rerank(query="test", documents=sample_documents)

    # Verify batch_size was passed to predict
    mock_model.predict.assert_called_once()
    call_kwargs = mock_model.predict.call_args[1]
    assert call_kwargs["batch_size"] == 2
