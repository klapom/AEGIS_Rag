"""
Unit tests for PromptCacheService.

Sprint 63 Feature 63.3: Redis Prompt Caching

Tests cover:
    - Cache key generation (deterministic, model-specific)
    - Cache hit/miss tracking
    - Cache TTL enforcement
    - Namespace isolation
    - Cache invalidation
    - Statistics tracking
"""

import hashlib
from unittest.mock import AsyncMock

import pytest

from src.domains.llm_integration.cache.prompt_cache import PromptCacheService


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.scan = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.strlen = AsyncMock()
    return redis_mock


@pytest.fixture
def cache_service(mock_redis):
    """Create PromptCacheService with mocked Redis."""
    service = PromptCacheService(redis_client=mock_redis)
    return service


class TestCacheKeyGeneration:
    """Test cache key generation strategy."""

    def test_cache_key_format(self, cache_service):
        """Test that cache keys follow expected format."""
        namespace = "default"
        model = "llama3.2:8b"
        prompt = "Extract entities from text..."

        key = cache_service._generate_cache_key(namespace, model, prompt)

        # Check format: prompt_cache:namespace#model_hash#prompt_hash
        assert key.startswith("prompt_cache:default#")
        # Key should be long enough for model hash (16) + # + prompt hash (64)
        assert len(key) > 100

    def test_cache_key_deterministic(self, cache_service):
        """Test that same prompt produces same key."""
        namespace = "default"
        model = "llama3.2:8b"
        prompt = "Extract entities from text..."

        key1 = cache_service._generate_cache_key(namespace, model, prompt)
        key2 = cache_service._generate_cache_key(namespace, model, prompt)

        assert key1 == key2

    def test_cache_key_differs_by_prompt(self, cache_service):
        """Test that different prompts produce different keys."""
        namespace = "default"
        model = "llama3.2:8b"
        prompt1 = "Extract entities from text..."
        prompt2 = "Summarize the text..."

        key1 = cache_service._generate_cache_key(namespace, model, prompt1)
        key2 = cache_service._generate_cache_key(namespace, model, prompt2)

        assert key1 != key2

    def test_cache_key_differs_by_model(self, cache_service):
        """Test that different models produce different keys."""
        namespace = "default"
        prompt = "Extract entities from text..."
        model1 = "llama3.2:8b"
        model2 = "gpt-4o"

        key1 = cache_service._generate_cache_key(namespace, model1, prompt)
        key2 = cache_service._generate_cache_key(namespace, model2, prompt)

        assert key1 != key2

    def test_cache_key_differs_by_namespace(self, cache_service):
        """Test that different namespaces produce different keys."""
        model = "llama3.2:8b"
        prompt = "Extract entities from text..."
        namespace1 = "tenant-1"
        namespace2 = "tenant-2"

        key1 = cache_service._generate_cache_key(namespace1, model, prompt)
        key2 = cache_service._generate_cache_key(namespace2, model, prompt)

        assert key1 != key2

    def test_cache_key_uses_sha256(self, cache_service):
        """Test that cache key uses SHA256 hash of prompt."""
        namespace = "default"
        model = "llama3.2:8b"
        prompt = "Extract entities from text..."

        # Manually compute expected hashes
        model_hash = hashlib.sha256(model.encode("utf-8")).hexdigest()[:16]
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        key = cache_service._generate_cache_key(namespace, model, prompt)

        assert key == f"prompt_cache:{namespace}#{model_hash}#{prompt_hash}"


class TestCacheHitMiss:
    """Test cache hit/miss tracking."""

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache_service, mock_redis):
        """Test cache hit returns cached value."""
        prompt = "Extract entities..."
        model = "llama3.2:8b"
        namespace = "default"
        cached_value = "John Smith (Person), Acme Corp (Organization)"

        mock_redis.get.return_value = cached_value.encode("utf-8")

        result = await cache_service.get_cached_response(
            prompt=prompt,
            model=model,
            namespace=namespace,
        )

        assert result == cached_value
        assert cache_service._hits == 1
        assert cache_service._misses == 0

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_service, mock_redis):
        """Test cache miss returns None."""
        prompt = "Extract entities..."
        model = "llama3.2:8b"
        namespace = "default"

        mock_redis.get.return_value = None

        result = await cache_service.get_cached_response(
            prompt=prompt,
            model=model,
            namespace=namespace,
        )

        assert result is None
        assert cache_service._hits == 0
        assert cache_service._misses == 1

    @pytest.mark.asyncio
    async def test_multiple_hits_misses(self, cache_service, mock_redis):
        """Test multiple cache operations update statistics."""
        prompt = "Extract entities..."
        model = "llama3.2:8b"

        # First request: miss
        mock_redis.get.return_value = None
        await cache_service.get_cached_response(prompt=prompt, model=model, namespace="default")
        assert cache_service._hits == 0
        assert cache_service._misses == 1

        # Second request: hit
        mock_redis.get.return_value = b"cached response"
        await cache_service.get_cached_response(prompt=prompt, model=model, namespace="default")
        assert cache_service._hits == 1
        assert cache_service._misses == 1

        # Third request: miss
        mock_redis.get.return_value = None
        await cache_service.get_cached_response(prompt=prompt, model=model, namespace="default")
        assert cache_service._hits == 1
        assert cache_service._misses == 2


class TestCacheStorage:
    """Test cache storage operations."""

    @pytest.mark.asyncio
    async def test_cache_response(self, cache_service, mock_redis):
        """Test caching a response with TTL."""
        prompt = "Extract entities..."
        model = "llama3.2:8b"
        namespace = "default"
        response = "John Smith (Person), Acme Corp (Organization)"
        ttl = 3600

        await cache_service.cache_response(
            prompt=prompt,
            model=model,
            namespace=namespace,
            response=response,
            ttl=ttl,
        )

        # Verify Redis setex was called with correct parameters
        mock_redis.setex.assert_called_once()
        call_kwargs = mock_redis.setex.call_args[1]
        assert call_kwargs["time"] == ttl
        assert call_kwargs["value"] == response

    @pytest.mark.asyncio
    async def test_cache_response_default_ttl(self, cache_service, mock_redis):
        """Test caching with default TTL."""
        prompt = "Extract entities..."
        model = "llama3.2:8b"
        namespace = "default"
        response = "John Smith (Person), Acme Corp (Organization)"

        await cache_service.cache_response(
            prompt=prompt,
            model=model,
            namespace=namespace,
            response=response,
        )

        # Verify Redis setex was called with default TTL
        mock_redis.setex.assert_called_once()
        call_kwargs = mock_redis.setex.call_args[1]
        assert call_kwargs["time"] == 3600  # Default 1 hour

    @pytest.mark.asyncio
    async def test_cache_response_error_handling(self, cache_service, mock_redis):
        """Test that cache storage errors don't crash."""
        mock_redis.setex.side_effect = Exception("Redis connection error")

        # Should not raise exception
        await cache_service.cache_response(
            prompt="test",
            model="test-model",
            namespace="default",
            response="test response",
        )

    @pytest.mark.asyncio
    async def test_cache_hit_error_handling(self, cache_service, mock_redis):
        """Test that cache lookup errors are treated as misses."""
        mock_redis.get.side_effect = Exception("Redis connection error")

        result = await cache_service.get_cached_response(
            prompt="test",
            model="test-model",
            namespace="default",
        )

        assert result is None
        assert cache_service._misses == 1


class TestNamespaceIsolation:
    """Test namespace-based isolation."""

    @pytest.mark.asyncio
    async def test_namespace_isolation_different_keys(self, cache_service):
        """Test that different namespaces produce different cache keys."""
        prompt = "Test prompt"
        model = "test-model"

        key1 = cache_service._generate_cache_key("tenant-1", model, prompt)
        key2 = cache_service._generate_cache_key("tenant-2", model, prompt)

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_namespace_invalidation(self, cache_service, mock_redis):
        """Test invalidating all entries in a namespace."""
        namespace = "test-namespace"

        # Mock SCAN to return keys matching pattern
        mock_redis.scan.side_effect = [
            (
                0,
                [
                    f"prompt_cache:{namespace}:model1:hash1",
                    f"prompt_cache:{namespace}:model1:hash2",
                ],
            ),
        ]
        mock_redis.delete.return_value = 2

        deleted = await cache_service.invalidate_namespace(namespace)

        assert deleted == 2
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_namespace_invalidation_multiple_scans(self, cache_service, mock_redis):
        """Test namespace invalidation with multiple SCAN iterations."""
        namespace = "test-namespace"

        # Mock SCAN with pagination
        mock_redis.scan.side_effect = [
            (1, [f"prompt_cache:{namespace}:model1:hash1"]),
            (0, [f"prompt_cache:{namespace}:model1:hash2"]),
        ]
        mock_redis.delete.side_effect = [1, 1]

        deleted = await cache_service.invalidate_namespace(namespace)

        assert deleted == 2
        assert mock_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_namespace_invalidation_error_handling(self, cache_service, mock_redis):
        """Test that invalidation errors are handled gracefully."""
        mock_redis.scan.side_effect = Exception("Redis error")

        deleted = await cache_service.invalidate_namespace("test-namespace")

        assert deleted == 0


class TestCacheStatistics:
    """Test cache statistics tracking."""

    @pytest.mark.asyncio
    async def test_cache_stats_all_hits(self, cache_service, mock_redis):
        """Test statistics when all requests are hits."""
        mock_redis.get.return_value = b"cached"
        mock_redis.scan.return_value = (0, [])  # No keys scanned

        # Perform 10 hits
        for _ in range(10):
            await cache_service.get_cached_response(
                prompt="test",
                model="test-model",
                namespace="default",
            )

        stats = await cache_service.get_stats()

        assert stats.hits == 10
        assert stats.misses == 0
        assert stats.hit_rate == 1.0
        assert stats.total_requests == 10

    @pytest.mark.asyncio
    async def test_cache_stats_all_misses(self, cache_service, mock_redis):
        """Test statistics when all requests are misses."""
        mock_redis.get.return_value = None
        mock_redis.scan.return_value = (0, [])

        # Perform 10 misses
        for _ in range(10):
            await cache_service.get_cached_response(
                prompt="test",
                model="test-model",
                namespace="default",
            )

        stats = await cache_service.get_stats()

        assert stats.hits == 0
        assert stats.misses == 10
        assert stats.hit_rate == 0.0
        assert stats.total_requests == 10

    @pytest.mark.asyncio
    async def test_cache_stats_mixed(self, cache_service, mock_redis):
        """Test statistics with mixed hits and misses."""
        mock_redis.scan.return_value = (0, [])

        # 3 hits, 2 misses
        for i in range(5):
            mock_redis.get.return_value = b"cached" if i < 3 else None
            await cache_service.get_cached_response(
                prompt=f"test{i}",
                model="test-model",
                namespace="default",
            )

        stats = await cache_service.get_stats()

        assert stats.hits == 3
        assert stats.misses == 2
        assert abs(stats.hit_rate - 0.6) < 0.001
        assert stats.total_requests == 5

    @pytest.mark.asyncio
    async def test_cache_stats_size_estimation(self, cache_service, mock_redis):
        """Test cached size estimation."""
        keys = [
            b"prompt_cache:default:model1:hash1",
            b"prompt_cache:default:model1:hash2",
            b"prompt_cache:default:model2:hash3",
        ]
        mock_redis.scan.side_effect = [
            (0, keys),
        ]
        # Simulate different sizes for each key
        mock_redis.strlen.side_effect = [100, 200, 150]

        stats = await cache_service.get_stats()

        assert stats.cached_size_bytes == 450

    @pytest.mark.asyncio
    async def test_reset_stats(self, cache_service, mock_redis):
        """Test resetting cache statistics."""
        # Perform some operations
        mock_redis.get.return_value = b"cached"
        for _ in range(5):
            await cache_service.get_cached_response(
                prompt="test",
                model="test-model",
                namespace="default",
            )

        assert cache_service._hits == 5

        # Reset stats
        cache_service.reset_stats()

        assert cache_service._hits == 0
        assert cache_service._misses == 0


class TestCacheIntegration:
    """Integration tests for cache operations."""

    @pytest.mark.asyncio
    async def test_full_cache_workflow(self, cache_service, mock_redis):
        """Test full cache workflow: miss → store → hit."""
        prompt = "Extract entities from legal document..."
        model = "llama3.2:8b"
        namespace = "default"
        response = "John Smith (Person) works at Acme Corp (Organization)"

        # Step 1: Cache miss
        mock_redis.get.return_value = None
        result = await cache_service.get_cached_response(
            prompt=prompt, model=model, namespace=namespace
        )
        assert result is None
        assert cache_service._misses == 1

        # Step 2: Store response
        await cache_service.cache_response(
            prompt=prompt,
            model=model,
            namespace=namespace,
            response=response,
            ttl=3600,
        )
        mock_redis.setex.assert_called_once()

        # Step 3: Cache hit
        mock_redis.get.return_value = response.encode("utf-8")
        result = await cache_service.get_cached_response(
            prompt=prompt, model=model, namespace=namespace
        )
        assert result == response
        assert cache_service._hits == 1
        assert cache_service._misses == 1

    @pytest.mark.asyncio
    async def test_model_specific_caching(self, cache_service, mock_redis):
        """Test that different models maintain separate caches."""
        prompt = "Test prompt"
        response1 = "Response from model1"

        # Cache for model1
        mock_redis.get.return_value = None
        await cache_service.cache_response(
            prompt=prompt,
            model="model1",
            namespace="default",
            response=response1,
        )

        # Try to retrieve with model2 (should miss)
        mock_redis.get.return_value = None
        result = await cache_service.get_cached_response(
            prompt=prompt,
            model="model2",
            namespace="default",
        )
        assert result is None

        # Retrieve with model1 (should hit)
        mock_redis.get.return_value = response1.encode("utf-8")
        result = await cache_service.get_cached_response(
            prompt=prompt,
            model="model1",
            namespace="default",
        )
        assert result == response1
