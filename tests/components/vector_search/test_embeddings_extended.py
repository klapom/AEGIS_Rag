"""Extended Unit Tests for Embedding Service - Coverage Improvement.

Tests embedding service wrapper for validation, caching, and delegation.

Author: Claude Code
Date: 2025-10-27
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.vector_search.embeddings import EmbeddingService, get_embedding_service


# ============================================================================
# EmbeddingService Tests
# ============================================================================


@pytest.mark.unit
def test_embedding_service_initialization_defaults():
    """Test EmbeddingService initializes with correct defaults."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_get.return_value = mock_unified

        service = EmbeddingService()

        assert service.batch_size == 32
        assert service.enable_cache is True
        assert service.unified_service == mock_unified
        assert service.model_name == "nomic-embed-text"


@pytest.mark.unit
def test_embedding_service_initialization_custom_params():
    """Test EmbeddingService accepts custom parameters."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_get.return_value = mock_unified

        service = EmbeddingService(
            model_name="custom-model",
            base_url="http://custom:11434",
            batch_size=64,
            enable_cache=False,
        )

        assert service.batch_size == 64
        assert service.enable_cache is False
        assert service.model_name == "custom-model"
        assert service.base_url == "http://custom:11434"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_text_delegates_to_unified_service():
    """Test embed_text delegates to unified service."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_unified.embed_single = AsyncMock(return_value=[0.1] * 768)
        mock_get.return_value = mock_unified

        service = EmbeddingService()
        embedding = await service.embed_text("test text")

        assert len(embedding) == 768
        assert embedding[0] == 0.1
        mock_unified.embed_single.assert_called_once_with("test text")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_batch_delegates_to_unified_service():
    """Test embed_batch delegates to unified service."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_unified.embed_batch = AsyncMock(
            return_value=[[0.1] * 768, [0.2] * 768, [0.3] * 768]
        )
        mock_get.return_value = mock_unified

        service = EmbeddingService()
        embeddings = await service.embed_batch(["text1", "text2", "text3"])

        assert len(embeddings) == 3
        assert len(embeddings[0]) == 768
        assert embeddings[0][0] == 0.1
        assert embeddings[1][0] == 0.2
        mock_unified.embed_batch.assert_called_once_with(["text1", "text2", "text3"])


@pytest.mark.unit
def test_get_embedding_dimension():
    """Test get_embedding_dimension returns correct dimension."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_unified.embedding_dim = 768
        mock_get.return_value = mock_unified

        service = EmbeddingService()
        dimension = service.get_embedding_dimension()

        assert dimension == 768


@pytest.mark.unit
def test_clear_cache():
    """Test clear_cache clears unified service cache."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_cache_dict = MagicMock()
        mock_cache = MagicMock()
        mock_cache.cache = mock_cache_dict
        mock_cache._hits = 10
        mock_cache._misses = 5

        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_unified.cache = mock_cache
        mock_get.return_value = mock_unified

        service = EmbeddingService()
        service.clear_cache()

        assert mock_cache._hits == 0
        assert mock_cache._misses == 0
        mock_cache_dict.clear.assert_called_once()


@pytest.mark.unit
def test_get_cache_size():
    """Test get_cache_size returns correct cache size."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_cache = MagicMock()
        mock_cache.cache = {"key1": "val1", "key2": "val2", "key3": "val3"}

        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_unified.cache = mock_cache
        mock_get.return_value = mock_unified

        service = EmbeddingService()
        size = service.get_cache_size()

        assert size == 3


@pytest.mark.unit
def test_get_cache_stats():
    """Test get_cache_stats returns statistics."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_cache = MagicMock()
        mock_cache.stats.return_value = {
            "size": 10,
            "hits": 50,
            "misses": 25,
            "hit_rate": 0.67,
        }

        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_unified.cache = mock_cache
        mock_get.return_value = mock_unified

        service = EmbeddingService()
        stats = service.get_cache_stats()

        assert stats["size"] == 10
        assert stats["hits"] == 50
        assert stats["misses"] == 25
        assert stats["hit_rate"] == 0.67


@pytest.mark.unit
def test_model_info():
    """Test model_info returns complete information."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_cache = MagicMock()
        mock_cache.cache = {"key1": "val1"}

        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_unified.embedding_dim = 768
        mock_unified.cache = mock_cache
        mock_get.return_value = mock_unified

        service = EmbeddingService(batch_size=64, enable_cache=True)
        info = service.model_info

        assert info["model_name"] == "nomic-embed-text"
        assert info["base_url"] == "unified_service"
        assert info["embedding_dimension"] == 768
        assert info["batch_size"] == 64
        assert info["cache_enabled"] is True
        assert info["cached_embeddings"] == 1


@pytest.mark.unit
def test_cache_property_backward_compatibility():
    """Test _cache property for backward compatibility."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_cache_dict = {"key1": "val1"}
        mock_cache = MagicMock()
        mock_cache.cache = mock_cache_dict

        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_unified.cache = mock_cache
        mock_get.return_value = mock_unified

        service = EmbeddingService()

        assert service._cache == mock_cache_dict


@pytest.mark.unit
def test_embedding_model_property_lazy_load():
    """Test _embedding_model property for lazy loading."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        # No _model attribute initially (lazy loading)
        del mock_unified._model
        mock_get.return_value = mock_unified

        service = EmbeddingService()

        assert service._embedding_model is None


@pytest.mark.unit
def test_embedding_model_setter():
    """Test _embedding_model setter for test mocking."""
    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_get.return_value = mock_unified

        service = EmbeddingService()
        mock_model = MagicMock()
        service._embedding_model = mock_model

        assert mock_unified._model == mock_model


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


@pytest.mark.unit
def test_get_embedding_service_singleton():
    """Test get_embedding_service returns singleton instance."""
    # Reset global instance
    import src.components.vector_search.embeddings as emb_module

    emb_module._embedding_service = None

    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_get.return_value = mock_unified

        service1 = get_embedding_service()
        service2 = get_embedding_service()

        assert service1 is service2


@pytest.mark.unit
def test_get_embedding_service_creates_instance_once():
    """Test get_embedding_service creates instance only once."""
    # Reset global instance
    import src.components.vector_search.embeddings as emb_module

    emb_module._embedding_service = None

    with patch("src.components.vector_search.embeddings.get_unified_service") as mock_get:
        mock_unified = MagicMock()
        mock_unified.model_name = "nomic-embed-text"
        mock_get.return_value = mock_unified

        _ = get_embedding_service()
        _ = get_embedding_service()
        _ = get_embedding_service()

        # Should only call unified service once
        assert mock_get.call_count == 1
