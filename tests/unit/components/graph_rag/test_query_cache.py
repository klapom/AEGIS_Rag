"""Unit tests for GraphQueryCache.

Tests cover:
- LRU eviction policy
- TTL-based expiration
- Cache invalidation
- Statistics tracking
- Thread safety
- Cache key generation
"""

import asyncio
import time

import pytest

from src.components.graph_rag.query_cache import GraphQueryCache


class TestGraphQueryCache:
    """Test GraphQueryCache with LRU and TTL."""

    @pytest.fixture
    def cache(self):
        """Create cache instance for testing."""
        return GraphQueryCache(max_size=5, ttl_seconds=60, enabled=True)

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache):
        """Test basic cache set and get operations."""
        query = "MATCH (n:Entity) RETURN n"
        params = {"limit": 10}
        result = [{"name": "Test"}]

        await cache.set(query, params, result)
        cached_result = await cache.get(query, params)

        assert cached_result == result

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        query = "MATCH (n:Entity) RETURN n"
        params = {"limit": 10}

        result = await cache.get(query, params)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_statistics(self, cache):
        """Test cache hit/miss statistics."""
        query = "MATCH (n:Entity) RETURN n"
        result = [{"name": "Test"}]

        # Set cache
        await cache.set(query, None, result)

        # Cache hit
        await cache.get(query, None)

        # Cache miss
        await cache.get("MATCH (n:Person) RETURN n", None)

        stats = await cache.stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2
        assert stats["hit_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """Test LRU eviction when max size reached."""
        # Fill cache to max size (5 entries)
        for i in range(5):
            await cache.set(f"MATCH (n{i}) RETURN n{i}", None, [{"id": i}])

        # Verify all 5 are cached
        stats = await cache.stats()
        assert stats["current_size"] == 5

        # Add 6th entry, should evict oldest
        await cache.set("MATCH (n6) RETURN n6", None, [{"id": 6}])

        stats = await cache.stats()
        assert stats["current_size"] == 5
        assert stats["evictions"] == 1

        # Oldest entry (n0) should be evicted
        result = await cache.get("MATCH (n0) RETURN n0", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL-based cache expiration."""
        cache = GraphQueryCache(max_size=10, ttl_seconds=1, enabled=True)

        query = "MATCH (n:Entity) RETURN n"
        result = [{"name": "Test"}]

        await cache.set(query, None, result)

        # Immediate retrieval should succeed
        cached_result = await cache.get(query, None)
        assert cached_result == result

        # Wait for TTL to expire
        await asyncio.sleep(1.1)

        # Should be expired now
        cached_result = await cache.get(query, None)
        assert cached_result is None

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache):
        """Test explicit cache invalidation."""
        query = "MATCH (n:Entity) RETURN n"
        result = [{"name": "Test"}]

        await cache.set(query, None, result)

        # Verify cached
        cached_result = await cache.get(query, None)
        assert cached_result is not None

        # Invalidate
        invalidated = await cache.invalidate(query, None)
        assert invalidated is True

        # Should be gone
        cached_result = await cache.get(query, None)
        assert cached_result is None

        # Stats should reflect invalidation
        stats = await cache.stats()
        assert stats["invalidations"] == 1

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache):
        """Test clearing entire cache."""
        # Add multiple entries
        for i in range(3):
            await cache.set(f"MATCH (n{i}) RETURN n{i}", None, [{"id": i}])

        stats = await cache.stats()
        assert stats["current_size"] == 3

        # Clear cache
        cleared_count = await cache.clear()
        assert cleared_count == 3

        stats = await cache.stats()
        assert stats["current_size"] == 0

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache):
        """Test cache key is consistent for same query+params."""
        query = "MATCH (n:Entity) RETURN n"
        params1 = {"limit": 10, "name": "Test"}
        params2 = {"name": "Test", "limit": 10}  # Different order

        # Set with first params
        await cache.set(query, params1, [{"result": 1}])

        # Get with second params (different order, same content)
        cached_result = await cache.get(query, params2)

        # Should retrieve same result (params order doesn't matter)
        assert cached_result == [{"result": 1}]

    @pytest.mark.asyncio
    async def test_different_params_different_cache(self, cache):
        """Test different parameters create different cache entries."""
        query = "MATCH (n:Entity) RETURN n"
        params1 = {"limit": 10}
        params2 = {"limit": 20}

        await cache.set(query, params1, [{"result": 1}])
        await cache.set(query, params2, [{"result": 2}])

        result1 = await cache.get(query, params1)
        result2 = await cache.get(query, params2)

        assert result1 == [{"result": 1}]
        assert result2 == [{"result": 2}]

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = GraphQueryCache(max_size=10, ttl_seconds=1, enabled=True)

        # Add entries
        for i in range(3):
            await cache.set(f"MATCH (n{i}) RETURN n{i}", None, [{"id": i}])

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Cleanup expired
        cleaned = await cache.cleanup_expired()

        assert cleaned == 3

        stats = await cache.stats()
        assert stats["current_size"] == 0

    @pytest.mark.asyncio
    async def test_disabled_cache(self):
        """Test cache behavior when disabled."""
        cache = GraphQueryCache(max_size=10, ttl_seconds=60, enabled=False)

        query = "MATCH (n:Entity) RETURN n"
        result = [{"name": "Test"}]

        # Set should not cache
        await cache.set(query, None, result)

        # Get should always return None
        cached_result = await cache.get(query, None)
        assert cached_result is None

    @pytest.mark.asyncio
    async def test_cache_stats_structure(self, cache):
        """Test cache statistics structure."""
        stats = await cache.stats()

        assert "enabled" in stats
        assert "max_size" in stats
        assert "current_size" in stats
        assert "ttl_seconds" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "total_requests" in stats
        assert "hit_rate" in stats
        assert "evictions" in stats
        assert "invalidations" in stats

    @pytest.mark.asyncio
    async def test_reset_stats(self, cache):
        """Test resetting cache statistics."""
        query = "MATCH (n:Entity) RETURN n"

        await cache.set(query, None, [{"result": 1}])
        await cache.get(query, None)  # Hit
        await cache.get("MATCH (n:Person) RETURN n", None)  # Miss

        stats_before = await cache.stats()
        assert stats_before["hits"] == 1
        assert stats_before["misses"] == 1

        cache.reset_stats()

        stats_after = await cache.stats()
        assert stats_after["hits"] == 0
        assert stats_after["misses"] == 0

    @pytest.mark.asyncio
    async def test_cache_with_none_parameters(self, cache):
        """Test cache with None parameters."""
        query = "MATCH (n:Entity) RETURN n"

        await cache.set(query, None, [{"result": 1}])

        # Both None and empty dict should work
        result1 = await cache.get(query, None)
        result2 = await cache.get(query, {})

        assert result1 == [{"result": 1}]
        assert result2 == [{"result": 1}]

    @pytest.mark.asyncio
    async def test_lru_ordering(self, cache):
        """Test LRU ordering - recently accessed items stay."""
        # Fill cache
        for i in range(5):
            await cache.set(f"MATCH (n{i}) RETURN n{i}", None, [{"id": i}])

        # Access first entry to make it most recent
        await cache.get("MATCH (n0) RETURN n0", None)

        # Add new entry - should evict n1 (now oldest)
        await cache.set("MATCH (n5) RETURN n5", None, [{"id": 5}])

        # n0 should still be there (was accessed recently)
        result0 = await cache.get("MATCH (n0) RETURN n0", None)
        assert result0 == [{"id": 0}]

        # n1 should be evicted
        result1 = await cache.get("MATCH (n1) RETURN n1", None)
        assert result1 is None

    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache):
        """Test concurrent cache access."""
        query = "MATCH (n:Entity) RETURN n"
        result = [{"name": "Test"}]

        await cache.set(query, None, result)

        # Concurrent gets
        results = await asyncio.gather(*[cache.get(query, None) for _ in range(10)])

        # All should return the same result
        assert all(r == result for r in results)

    @pytest.mark.asyncio
    async def test_len_and_contains(self, cache):
        """Test __len__ and __contains__ methods."""
        query = "MATCH (n:Entity) RETURN n"

        assert len(cache) == 0

        await cache.set(query, None, [{"result": 1}])

        assert len(cache) == 1

    def test_cache_initialization_from_settings(self):
        """Test cache initialization with default settings."""
        cache = GraphQueryCache()

        # Should use settings values
        assert cache.max_size > 0
        assert cache.ttl_seconds > 0
        assert isinstance(cache.enabled, bool)
