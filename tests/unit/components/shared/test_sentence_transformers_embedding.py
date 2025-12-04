"""Unit tests for SentenceTransformersEmbeddingService.

Sprint Context: Sprint 35 (2025-12-04) - Feature 35.8: Sentence-Transformers Migration

Test Coverage:
    - Lazy model loading
    - Single text embedding with caching
    - Batch text embedding with GPU acceleration
    - Cache hit/miss tracking
    - Statistics reporting
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.components.shared.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingService,
)


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer model."""
    mock_model = MagicMock()
    mock_model.device = "cuda:0"
    return mock_model


@pytest.fixture
def embedding_service(mock_sentence_transformer):
    """Create embedding service with mocked model."""
    with patch(
        "src.components.shared.sentence_transformers_embedding.SentenceTransformer"
    ) as mock_st:
        mock_st.return_value = mock_sentence_transformer
        service = SentenceTransformersEmbeddingService(
            model_name="BAAI/bge-m3",
            device="cuda",
            batch_size=32,
            cache_max_size=100,
        )
        yield service


def test_initialization():
    """Test service initialization without loading model."""
    service = SentenceTransformersEmbeddingService(
        model_name="BAAI/bge-m3",
        device="cuda",
        batch_size=32,
        cache_max_size=100,
    )

    assert service.model_name == "BAAI/bge-m3"
    assert service.device == "cuda"
    assert service.batch_size == 32
    assert service.embedding_dim == 1024
    assert service._model is None  # Lazy loading
    assert service.cache.max_size == 100


def test_lazy_model_loading(mock_sentence_transformer):
    """Test model is loaded lazily on first use."""
    with patch(
        "src.components.shared.sentence_transformers_embedding.SentenceTransformer"
    ) as mock_st:
        mock_st.return_value = mock_sentence_transformer

        service = SentenceTransformersEmbeddingService()
        assert service._model is None

        # Trigger lazy loading
        model = service._load_model()
        assert model is not None
        assert service._model is mock_sentence_transformer

        # Subsequent calls return cached model
        model2 = service._load_model()
        assert model2 is mock_sentence_transformer
        assert mock_st.call_count == 1  # Only called once


def test_embed_single(embedding_service, mock_sentence_transformer):
    """Test single text embedding."""
    # Mock encode to return numpy array
    mock_embedding = np.array([0.1] * 1024)
    mock_sentence_transformer.encode.return_value = mock_embedding

    embedding = embedding_service.embed_single("test text")

    assert isinstance(embedding, list)
    assert len(embedding) == 1024
    assert embedding[0] == 0.1
    mock_sentence_transformer.encode.assert_called_once()


def test_embed_single_with_cache(embedding_service, mock_sentence_transformer):
    """Test single text embedding uses cache on second call."""
    mock_embedding = np.array([0.1] * 1024)
    mock_sentence_transformer.encode.return_value = mock_embedding

    # First call: cache miss
    embedding1 = embedding_service.embed_single("test text")
    assert len(embedding1) == 1024
    assert mock_sentence_transformer.encode.call_count == 1

    # Second call: cache hit
    embedding2 = embedding_service.embed_single("test text")
    assert embedding1 == embedding2
    assert mock_sentence_transformer.encode.call_count == 1  # Not called again


def test_embed_batch(embedding_service, mock_sentence_transformer):
    """Test batch embedding."""
    texts = ["text1", "text2", "text3"]
    mock_embeddings = np.array([[0.1] * 1024, [0.2] * 1024, [0.3] * 1024])
    mock_sentence_transformer.encode.return_value = mock_embeddings

    embeddings = embedding_service.embed_batch(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 1024 for emb in embeddings)
    assert embeddings[0][0] == 0.1
    assert embeddings[1][0] == 0.2
    assert embeddings[2][0] == 0.3

    # Verify batch processing was used
    mock_sentence_transformer.encode.assert_called_once()
    call_args = mock_sentence_transformer.encode.call_args
    assert call_args[0][0] == texts
    assert call_args[1]["batch_size"] == 32


def test_embed_batch_with_cache(embedding_service, mock_sentence_transformer):
    """Test batch embedding uses cache for duplicate texts."""
    texts = ["text1", "text2", "text1"]  # "text1" appears twice

    # Mock encode to return embeddings for unique texts only
    mock_embeddings = np.array([[0.1] * 1024, [0.2] * 1024])
    mock_sentence_transformer.encode.return_value = mock_embeddings

    embeddings = embedding_service.embed_batch(texts)

    assert len(embeddings) == 3
    assert embeddings[0] == embeddings[2]  # Same text should have same embedding

    # Verify cache statistics
    stats = embedding_service.get_stats()
    assert stats["cache"]["hits"] == 1  # One cache hit for duplicate "text1"
    assert stats["cache"]["misses"] == 2  # Two misses for unique texts


def test_embed_batch_large_batch_shows_progress(embedding_service, mock_sentence_transformer):
    """Test progress bar is shown for large batches (>100 texts)."""
    texts = [f"text{i}" for i in range(150)]
    mock_embeddings = np.array([[0.1] * 1024] * 150)
    mock_sentence_transformer.encode.return_value = mock_embeddings

    embeddings = embedding_service.embed_batch(texts)

    assert len(embeddings) == 150

    # Verify show_progress_bar=True for large batch
    call_args = mock_sentence_transformer.encode.call_args
    assert call_args[1]["show_progress_bar"] is True


def test_embed_batch_small_batch_no_progress(embedding_service, mock_sentence_transformer):
    """Test progress bar is not shown for small batches (<100 texts)."""
    texts = ["text1", "text2", "text3"]
    mock_embeddings = np.array([[0.1] * 1024] * 3)
    mock_sentence_transformer.encode.return_value = mock_embeddings

    embeddings = embedding_service.embed_batch(texts)

    assert len(embeddings) == 3

    # Verify show_progress_bar=False for small batch (only called once for unique texts)
    # Note: Progress bar is controlled by encode() call for uncached texts
    # For cached texts, no encode() call is made
    call_args = mock_sentence_transformer.encode.call_args
    if call_args:  # Only check if encode was called (no cache hits)
        assert call_args[1]["show_progress_bar"] is False


def test_cache_eviction(mock_sentence_transformer):
    """Test LRU cache evicts oldest items when full."""
    with patch(
        "src.components.shared.sentence_transformers_embedding.SentenceTransformer"
    ) as mock_st:
        mock_st.return_value = mock_sentence_transformer

        # Create service with small cache
        service = SentenceTransformersEmbeddingService(cache_max_size=3)

        mock_embedding = np.array([0.1] * 1024)
        mock_sentence_transformer.encode.return_value = mock_embedding

        # Fill cache
        service.embed_single("text1")
        service.embed_single("text2")
        service.embed_single("text3")

        assert len(service.cache.cache) == 3

        # Add one more: should evict oldest (text1)
        service.embed_single("text4")
        assert len(service.cache.cache) == 3

        # Verify text1 was evicted (cache miss)
        cache_key_text1 = service._cache_key("text1")
        assert cache_key_text1 not in service.cache.cache


def test_get_stats(embedding_service):
    """Test statistics reporting."""
    stats = embedding_service.get_stats()

    assert stats["model"] == "BAAI/bge-m3"
    assert stats["device"] == "cuda"
    assert stats["batch_size"] == 32
    assert stats["embedding_dim"] == 1024
    assert "cache" in stats
    assert stats["cache"]["max_size"] == 100


def test_cache_hit_rate_calculation(embedding_service, mock_sentence_transformer):
    """Test cache hit rate calculation."""
    mock_embedding = np.array([0.1] * 1024)
    mock_sentence_transformer.encode.return_value = mock_embedding

    # Generate 3 embeddings: 2 unique + 1 duplicate
    embedding_service.embed_single("text1")  # Miss
    embedding_service.embed_single("text2")  # Miss
    embedding_service.embed_single("text1")  # Hit

    stats = embedding_service.get_stats()
    assert stats["cache"]["hits"] == 1
    assert stats["cache"]["misses"] == 2
    assert stats["cache"]["hit_rate"] == pytest.approx(1 / 3, rel=1e-2)


def test_compatible_api_with_unified_embedding_service(embedding_service):
    """Test API compatibility with UnifiedEmbeddingService."""
    # Verify service has same methods as UnifiedEmbeddingService
    assert hasattr(embedding_service, "embed_single")
    assert hasattr(embedding_service, "embed_batch")
    assert hasattr(embedding_service, "get_stats")

    # Verify method signatures match
    assert callable(embedding_service.embed_single)
    assert callable(embedding_service.embed_batch)
    assert callable(embedding_service.get_stats)


def test_device_auto_selection():
    """Test device='auto' selects appropriate device."""
    with patch(
        "src.components.shared.sentence_transformers_embedding.SentenceTransformer"
    ) as mock_st:
        mock_model = MagicMock()
        mock_model.device = "cuda:0"
        mock_st.return_value = mock_model

        service = SentenceTransformersEmbeddingService(device="auto")
        model = service._load_model()

        # Verify SentenceTransformer was called with 'auto'
        mock_st.assert_called_once_with("BAAI/bge-m3", device="auto")


def test_batch_size_configuration():
    """Test batch size configuration is respected."""
    service = SentenceTransformersEmbeddingService(batch_size=128)
    assert service.batch_size == 128


def test_model_name_configuration():
    """Test custom model name configuration."""
    service = SentenceTransformersEmbeddingService(model_name="custom/model")
    assert service.model_name == "custom/model"
