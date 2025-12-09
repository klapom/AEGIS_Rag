"""Extended Unit Tests for Cross-Encoder Reranker - Coverage Improvement.

Tests reranking logic, lazy loading, and score normalization.

Author: Claude Code
Date: 2025-10-27
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Skip entire module if sentence-transformers not installed
pytest.importorskip(
    "sentence_transformers", reason="sentence-transformers not installed (optional reranking group)"
)

from src.components.retrieval.reranker import CrossEncoderReranker, RerankResult

# ============================================================================
# RerankResult Tests
# ============================================================================


@pytest.mark.unit
def test_rerank_result_creation_valid():
    """Test RerankResult creation with valid data."""
    result = RerankResult(
        doc_id="doc123",
        text="Sample document text",
        original_score=0.75,
        rerank_score=2.5,
        final_score=0.92,
        original_rank=5,
        final_rank=1,
        metadata={"source": "test"},
    )

    assert result.doc_id == "doc123"
    assert result.text == "Sample document text"
    assert result.original_score == 0.75
    assert result.rerank_score == 2.5
    assert result.final_score == 0.92
    assert result.original_rank == 5
    assert result.final_rank == 1
    assert result.metadata["source"] == "test"


@pytest.mark.unit
def test_rerank_result_defaults():
    """Test RerankResult uses correct defaults."""
    result = RerankResult(
        doc_id="doc1",
        text="text",
        original_score=0.5,
        rerank_score=1.0,
        final_score=0.7,
        original_rank=0,
        final_rank=0,
    )

    assert result.metadata == {}


# ============================================================================
# CrossEncoderReranker Tests
# ============================================================================


@pytest.mark.unit
def test_reranker_initialization_defaults():
    """Test CrossEncoderReranker initializes with defaults."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        assert reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert reranker.batch_size == 32
        assert reranker.cache_dir == Path("./data/models")
        assert reranker._model is None  # Lazy loading


@pytest.mark.unit
def test_reranker_initialization_custom_params():
    """Test CrossEncoderReranker accepts custom parameters."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "default-model"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker(
            model_name="custom-model", batch_size=64, cache_dir="/custom/cache"
        )

        assert reranker.model_name == "custom-model"
        assert reranker.batch_size == 64
        assert reranker.cache_dir == Path("/custom/cache")


@pytest.mark.unit
def test_reranker_model_lazy_loading():
    """Test model is lazy-loaded on first access."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        assert reranker._model is None

        with patch("src.components.retrieval.reranker.CrossEncoder") as mock_ce:
            mock_model = MagicMock()
            mock_ce.return_value = mock_model

            model = reranker.model

            assert model == mock_model
            assert reranker._model == mock_model
            mock_ce.assert_called_once()


@pytest.mark.unit
def test_reranker_model_loaded_once():
    """Test model is loaded only once (cached)."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        with patch("src.components.retrieval.reranker.CrossEncoder") as mock_ce:
            mock_model = MagicMock()
            mock_ce.return_value = mock_model

            _ = reranker.model
            _ = reranker.model
            _ = reranker.model

            # Should only call CrossEncoder constructor once
            assert mock_ce.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rerank_empty_documents():
    """Test rerank with empty document list."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()
        results = await reranker.rerank(query="test query", documents=[])

        assert results == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rerank_sorts_by_score():
    """Test rerank sorts documents by relevance score."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        # Mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1.0, 3.0, 2.0])  # Scores
        reranker._model = mock_model

        documents = [
            {"id": "doc1", "text": "Low relevance", "score": 0.5},
            {"id": "doc2", "text": "High relevance", "score": 0.7},
            {"id": "doc3", "text": "Medium relevance", "score": 0.6},
        ]

        results = await reranker.rerank(query="test query", documents=documents)

        # Should be sorted: doc2 (3.0) > doc3 (2.0) > doc1 (1.0)
        assert results[0].doc_id == "doc2"
        assert results[1].doc_id == "doc3"
        assert results[2].doc_id == "doc1"

        # Check ranks updated correctly
        assert results[0].final_rank == 0
        assert results[1].final_rank == 1
        assert results[2].final_rank == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rerank_top_k_limit():
    """Test rerank respects top_k parameter."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        # Mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([3.0, 1.0, 2.0, 4.0, 0.5])
        reranker._model = mock_model

        documents = [{"id": f"doc{i}", "text": f"Text {i}", "score": 0.5} for i in range(5)]

        results = await reranker.rerank(query="test", documents=documents, top_k=2)

        assert len(results) == 2
        assert results[0].doc_id == "doc3"  # Highest score (4.0)
        assert results[1].doc_id == "doc0"  # Second highest (3.0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rerank_score_threshold():
    """Test rerank filters by score threshold."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        # Mock model - scores that normalize to different values
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([2.0, -2.0, 0.0])
        reranker._model = mock_model

        documents = [
            {"id": "doc1", "text": "High relevance", "score": 0.8},
            {"id": "doc2", "text": "Low relevance", "score": 0.3},
            {"id": "doc3", "text": "Medium relevance", "score": 0.5},
        ]

        # Sigmoid normalization:
        # 2.0 -> 0.88
        # -2.0 -> 0.12
        # 0.0 -> 0.5
        results = await reranker.rerank(query="test", documents=documents, score_threshold=0.6)

        # Only doc1 (0.88) should pass threshold
        assert len(results) == 1
        assert results[0].doc_id == "doc1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rerank_preserves_metadata():
    """Test rerank preserves document metadata."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        # Mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1.0])
        reranker._model = mock_model

        documents = [
            {
                "id": "doc1",
                "text": "Sample text",
                "score": 0.7,
                "metadata": {"source": "wikipedia", "timestamp": "2025-10-27"},
            }
        ]

        results = await reranker.rerank(query="test", documents=documents)

        assert results[0].metadata["source"] == "wikipedia"
        assert results[0].metadata["timestamp"] == "2025-10-27"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rerank_score_normalization():
    """Test rerank normalizes scores using sigmoid."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        # Mock model with known scores
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.0])  # Sigmoid(0) = 0.5
        reranker._model = mock_model

        documents = [{"id": "doc1", "text": "Text", "score": 0.5}]

        results = await reranker.rerank(query="test", documents=documents)

        # Sigmoid(0.0) should be 0.5
        assert abs(results[0].final_score - 0.5) < 0.01


@pytest.mark.unit
def test_get_model_info():
    """Test get_model_info returns correct information."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker(batch_size=64, cache_dir="/custom/cache")

        info = reranker.get_model_info()

        assert info["model_name"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert info["cache_dir"] == str(Path("/custom/cache"))
        assert info["batch_size"] == 64
        assert info["is_loaded"] is False


@pytest.mark.unit
def test_get_model_info_after_loading():
    """Test get_model_info reports loaded status correctly."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        with patch("src.components.retrieval.reranker.CrossEncoder") as mock_ce:
            mock_model = MagicMock()
            mock_ce.return_value = mock_model

            _ = reranker.model  # Load model

            info = reranker.get_model_info()
            assert info["is_loaded"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rerank_handles_missing_doc_fields():
    """Test rerank handles documents with missing fields gracefully."""
    with patch("src.components.retrieval.reranker.settings") as mock_settings:
        mock_settings.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.reranker_cache_dir = "./data/models"

        reranker = CrossEncoderReranker()

        # Mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1.0])
        reranker._model = mock_model

        # Document missing optional fields
        documents = [{"text": "Only text field"}]

        results = await reranker.rerank(query="test", documents=documents)

        # Should use defaults for missing fields
        assert results[0].doc_id.startswith("doc_")  # Generated ID
        assert results[0].original_score == 0.0  # Default score
        assert results[0].metadata == {}  # Default empty metadata
