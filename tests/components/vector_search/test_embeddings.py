"""Unit tests for EmbeddingService.

Tests embedding generation including:
- Single text embedding
- Batch embedding with batching logic
- Cache hit/miss scenarios
- Error handling and retries
- Service configuration
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.components.vector_search.embeddings import EmbeddingService, get_embedding_service

# ============================================================================
# Test Initialization
# ============================================================================


@pytest.mark.unit
def test_embedding_service_init_default():
    """Test EmbeddingService initialization with default settings."""
    service = EmbeddingService()

    assert service.model_name is not None, "Model name should be set"
    assert service.base_url is not None, "Base URL should be set"
    assert service.batch_size == 32, "Default batch size should be 32"
    assert service.enable_cache is True, "Cache should be enabled by default"
    assert len(service._cache) == 0, "Cache should start empty"


@pytest.mark.unit
def test_embedding_service_init_custom():
    """Test EmbeddingService initialization with custom parameters."""
    service = EmbeddingService(
        model_name="custom-model",
        base_url="http://custom:11434",
        batch_size=64,
        enable_cache=False,
    )

    assert service.model_name == "custom-model"
    assert service.base_url == "http://custom:11434"
    assert service.batch_size == 64
    assert service.enable_cache is False


@pytest.mark.unit
def test_embedding_dimension():
    """Test getting embedding dimension."""
    service = EmbeddingService()
    dim = service.get_embedding_dimension()

    assert dim == 768, "nomic-embed-text should have 768 dimensions"


# ============================================================================
# Test Single Text Embedding
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_text_success(mock_embedding_service, sample_embedding):
    """Test successful single text embedding."""
    text = "This is a test document."

    embedding = await mock_embedding_service.embed_text(text)

    assert len(embedding) == 768, "Embedding should have 768 dimensions"
    assert all(isinstance(x, float) for x in embedding), "All values should be floats"
    mock_embedding_service.embed_text.assert_called_once_with(text)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_text_cache_hit():
    """Test embedding cache hit (should not call API)."""
    service = EmbeddingService()
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding = AsyncMock(return_value=[0.1] * 768)

    text = "Test document"

    # First call - cache miss
    embedding1 = await service.embed_text(text)
    assert service._embedding_model.aget_text_embedding.call_count == 1

    # Second call - cache hit
    embedding2 = await service.embed_text(text)
    assert (
        service._embedding_model.aget_text_embedding.call_count == 1
    ), "Should not call API on cache hit"

    assert embedding1 == embedding2, "Cached embedding should match"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_text_cache_disabled():
    """Test embedding with cache disabled."""
    service = EmbeddingService(enable_cache=False)
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding = AsyncMock(return_value=[0.1] * 768)

    text = "Test document"

    # Both calls should hit API
    await service.embed_text(text)
    await service.embed_text(text)

    assert (
        service._embedding_model.aget_text_embedding.call_count == 2
    ), "Should call API twice with cache disabled"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_text_failure():
    """Test embedding generation failure."""
    from tenacity import RetryError

    service = EmbeddingService()
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding.side_effect = Exception("API Error")

    # With retry decorator, we get RetryError wrapping the LLMError
    with pytest.raises(RetryError):
        await service.embed_text("Test text")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_text_retry_logic():
    """Test embedding retry on transient failures."""
    service = EmbeddingService()
    service._embedding_model = AsyncMock()

    # Fail twice, then succeed
    service._embedding_model.aget_text_embedding.side_effect = [
        Exception("Timeout"),
        Exception("Timeout"),
        [0.1] * 768,
    ]

    embedding = await service.embed_text("Test text")

    assert len(embedding) == 768, "Should succeed after retries"
    assert service._embedding_model.aget_text_embedding.call_count == 3


# ============================================================================
# Test Batch Embedding
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_batch_success(sample_texts):
    """Test successful batch embedding."""
    service = EmbeddingService()
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding_batch = AsyncMock(
        return_value=[[0.1 + i * 0.01] * 768 for i in range(len(sample_texts))]
    )

    embeddings = await service.embed_batch(sample_texts)

    assert len(embeddings) == len(sample_texts), "Should return embedding for each text"
    assert all(len(emb) == 768 for emb in embeddings), "All embeddings should be 768-dim"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_batch_empty_list():
    """Test batch embedding with empty list."""
    service = EmbeddingService()

    embeddings = await service.embed_batch([])

    assert embeddings == [], "Empty input should return empty list"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_batch_with_cache():
    """Test batch embedding with partial cache hits."""
    service = EmbeddingService(batch_size=32)
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding_batch = AsyncMock(
        return_value=[[0.1] * 768, [0.2] * 768]
    )

    texts = ["text1", "text2", "text3"]

    # Pre-populate cache with one text using .set() method
    service._cache.set("hash1", [0.9] * 768)

    # _get_cache_key is called 2x per uncached text: once for lookup, once for caching result
    # text1 (cached): 1 call, text2 (uncached): 2 calls, text3 (uncached): 2 calls = 5 total
    with patch.object(
        service, "_get_cache_key", side_effect=["hash1", "hash2", "hash3", "hash2", "hash3"]
    ):
        embeddings = await service.embed_batch(texts)

    assert len(embeddings) == 3, "Should return 3 embeddings"
    # First should be from cache
    assert embeddings[0] == [0.9] * 768, "First should be cache hit"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_batch_batching():
    """Test that large batches are split correctly."""
    service = EmbeddingService(batch_size=10)
    service._embedding_model = AsyncMock()

    # Mock to return different embeddings for each batch
    def mock_batch_embed(texts):
        return [[0.1 + i * 0.001] * 768 for i in range(len(texts))]

    service._embedding_model.aget_text_embedding_batch = AsyncMock(side_effect=mock_batch_embed)

    # Create 25 texts (should be split into 3 batches: 10, 10, 5)
    texts = [f"text_{i}" for i in range(25)]

    embeddings = await service.embed_batch(texts)

    assert len(embeddings) == 25, "Should return 25 embeddings"
    # Check that batching happened (3 API calls)
    assert service._embedding_model.aget_text_embedding_batch.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_batch_failure():
    """Test batch embedding failure."""
    from tenacity import RetryError

    service = EmbeddingService()
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding_batch.side_effect = Exception("Batch failed")

    # With retry decorator, we get RetryError wrapping the LLMError
    with pytest.raises(RetryError):
        await service.embed_batch(["text1", "text2"])


# ============================================================================
# Test Cache Management
# ============================================================================


@pytest.mark.unit
def test_get_cache_key():
    """Test cache key generation (SHA-256 hash)."""
    service = EmbeddingService()

    key1 = service._get_cache_key("test text")
    key2 = service._get_cache_key("test text")
    key3 = service._get_cache_key("different text")

    assert key1 == key2, "Same text should generate same key"
    assert key1 != key3, "Different text should generate different key"
    assert len(key1) == 64, "SHA-256 hash should be 64 characters (hex digest)"


@pytest.mark.unit
def test_clear_cache():
    """Test cache clearing."""
    service = EmbeddingService()
    # Use LRUCache.set() method to populate cache
    service._cache.set("key1", [0.1] * 768)
    service._cache.set("key2", [0.2] * 768)

    assert service.get_cache_size() == 2, "Cache should have 2 entries"

    service.clear_cache()

    assert service.get_cache_size() == 0, "Cache should be empty"
    assert len(service._cache) == 0, "Cache dict should be empty"


@pytest.mark.unit
def test_get_cache_size():
    """Test getting cache size."""
    service = EmbeddingService()

    assert service.get_cache_size() == 0, "New cache should be empty"

    service._cache.set("key1", [0.1] * 768)
    assert service.get_cache_size() == 1, "Cache should have 1 entry"

    service._cache.set("key2", [0.2] * 768)
    assert service.get_cache_size() == 2, "Cache should have 2 entries"


# ============================================================================
# Test Model Info
# ============================================================================


@pytest.mark.unit
def test_model_info():
    """Test getting model information."""
    service = EmbeddingService()
    service._cache.set("test_key", [0.1] * 768)

    info = service.model_info

    assert "model_name" in info, "Should include model name"
    assert "base_url" in info, "Should include base URL"
    assert "embedding_dimension" in info, "Should include dimension"
    assert info["embedding_dimension"] == 768, "Dimension should be 768"
    assert "batch_size" in info, "Should include batch size"
    assert "cache_enabled" in info, "Should include cache status"
    assert "cached_embeddings" in info, "Should include cache size"
    assert info["cached_embeddings"] == 1, "Should show 1 cached embedding"


# ============================================================================
# Test Singleton Pattern
# ============================================================================


@pytest.mark.unit
def test_get_embedding_service_singleton():
    """Test that get_embedding_service returns singleton instance."""
    service1 = get_embedding_service()
    service2 = get_embedding_service()

    assert service1 is service2, "Should return same instance"


# ============================================================================
# Test Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_text_empty_string():
    """Test embedding empty string."""
    service = EmbeddingService()
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding = AsyncMock(return_value=[0.0] * 768)

    embedding = await service.embed_text("")

    assert len(embedding) == 768, "Should return 768-dim embedding even for empty string"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_text_very_long():
    """Test embedding very long text."""
    service = EmbeddingService()
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding = AsyncMock(return_value=[0.1] * 768)

    long_text = "word " * 10000  # Very long text

    embedding = await service.embed_text(long_text)

    assert len(embedding) == 768, "Should handle long text"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_batch_single_item():
    """Test batch embedding with single item."""
    service = EmbeddingService()
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding_batch = AsyncMock(return_value=[[0.1] * 768])

    embeddings = await service.embed_batch(["single text"])

    assert len(embeddings) == 1, "Should return 1 embedding"
    assert len(embeddings[0]) == 768, "Embedding should be 768-dim"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("batch_size", [1, 10, 32, 100])
async def test_different_batch_sizes(batch_size):
    """Test embedding service with different batch sizes."""
    service = EmbeddingService(batch_size=batch_size)

    assert service.batch_size == batch_size, f"Batch size should be {batch_size}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_batch_unicode_text():
    """Test embedding text with unicode characters."""
    service = EmbeddingService()
    service._embedding_model = AsyncMock()
    service._embedding_model.aget_text_embedding_batch = AsyncMock(
        return_value=[[0.1] * 768, [0.2] * 768]
    )

    texts = ["Hello 世界", "Héllo Wörld 🌍"]

    embeddings = await service.embed_batch(texts)

    assert len(embeddings) == 2, "Should handle unicode text"
