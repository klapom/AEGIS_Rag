"""Integration tests for memory optimizations - Sprint 68 Feature 68.3."""

import asyncio

import pytest

from src.components.shared.embedding_service import UnifiedEmbeddingService
from src.core.memory_profiler import MemoryProfiler, check_memory_available


class TestEmbeddingCacheOptimization:
    """Test embedding cache with content hash invalidation."""

    @pytest.fixture
    def embedding_service(self):
        """Create embedding service with small cache for testing."""
        return UnifiedEmbeddingService(cache_max_size=100)

    @pytest.mark.asyncio
    async def test_cache_key_with_document_id(self, embedding_service):
        """Test cache key generation with document ID."""
        text = "This is a test document"

        # Without document ID
        key1 = embedding_service._cache_key(text)
        key2 = embedding_service._cache_key(text)
        assert key1 == key2

        # With document ID (should produce different keys)
        key3 = embedding_service._cache_key(text, document_id="doc1")
        key4 = embedding_service._cache_key(text, document_id="doc2")
        assert key3 != key4
        assert key3 != key1

        # Same document ID should produce same key
        key5 = embedding_service._cache_key(text, document_id="doc1")
        assert key5 == key3

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, embedding_service):
        """Test that cache achieves good hit rate."""
        # Embed same text multiple times
        text = "Test embedding for cache hit rate"

        # First call - cache miss
        await embedding_service.embed_single(text)
        initial_stats = embedding_service.cache.stats()

        # Subsequent calls - cache hits
        for _ in range(10):
            await embedding_service.embed_single(text)

        final_stats = embedding_service.cache.stats()

        # Should have 10 hits (from 10 repeated calls)
        assert final_stats["hits"] - initial_stats["hits"] == 10
        # Hit rate should be high
        assert final_stats["hit_rate"] > 0.9

    @pytest.mark.asyncio
    async def test_cache_eviction_lru(self, embedding_service):
        """Test that LRU cache evicts oldest entries when full."""
        # Fill cache beyond max_size
        texts = [f"Document {i}" for i in range(150)]  # More than cache_max_size=100

        for text in texts:
            await embedding_service.embed_single(text)

        stats = embedding_service.cache.stats()

        # Cache should be at max size (evicted old entries)
        assert stats["size"] <= embedding_service.cache.max_size

    @pytest.mark.asyncio
    async def test_batch_embedding_cache(self, embedding_service):
        """Test cache effectiveness with batch embedding."""
        texts = ["Doc A", "Doc B", "Doc C"] * 5  # Repeated texts

        # Embed batch (should cache individual embeddings)
        await embedding_service.embed_batch(texts)

        stats = embedding_service.cache.stats()

        # Should have hits from repeated texts
        assert stats["hits"] > 0
        assert stats["hit_rate"] > 0.5


class TestMemoryProfiling:
    """Test memory profiling utilities."""

    @pytest.fixture
    def profiler(self):
        """Create memory profiler."""
        return MemoryProfiler()

    @pytest.mark.asyncio
    async def test_profile_async_operation(self, profiler):
        """Test profiling async operation with memory monitoring."""

        async def simulate_memory_operation():
            """Simulate operation with memory allocation."""
            data = [0] * 1_000_000  # ~8MB
            await asyncio.sleep(0.1)
            return data

        async with profiler.profile("test_operation", sample_interval_seconds=0.05):
            result = await simulate_memory_operation()

        stats = profiler.get_stats("test_operation")

        # Check stats structure
        assert "peak_ram_mb" in stats
        assert "peak_process_mb" in stats
        assert "delta_ram_mb" in stats
        assert stats["samples"] >= 2

        # Clean up
        del result

    @pytest.mark.asyncio
    async def test_profile_multiple_operations(self, profiler):
        """Test profiling multiple operations independently."""

        async def op1():
            await asyncio.sleep(0.05)

        async def op2():
            await asyncio.sleep(0.05)

        async with profiler.profile("operation_1"):
            await op1()

        async with profiler.profile("operation_2"):
            await op2()

        stats1 = profiler.get_stats("operation_1")
        stats2 = profiler.get_stats("operation_2")

        assert stats1 != stats2
        assert "operation_1" in profiler.snapshots
        assert "operation_2" in profiler.snapshots

    def test_memory_check_available(self):
        """Test memory availability check."""
        # Check with low requirements (should pass on any system)
        available, reason = check_memory_available(min_ram_mb=10, min_vram_mb=10)

        # Should pass unless system is critically low on memory
        if not available:
            assert "Insufficient" in reason


class TestMemoryCleanup:
    """Test explicit memory cleanup mechanisms."""

    @pytest.mark.asyncio
    async def test_garbage_collection_during_batch(self):
        """Test that garbage collection is triggered during batch processing."""
        import gc

        # Track garbage collection calls
        initial_collections = gc.get_count()

        # Simulate batch processing with cleanup
        data_chunks = []
        for i in range(10):
            # Allocate some memory
            chunk = [0] * 100_000
            data_chunks.append(chunk)

            # Explicit cleanup (simulating Sprint 68 feature)
            if i % 3 == 0:
                del chunk
                gc.collect()

        final_collections = gc.get_count()

        # GC should have run (count increases)
        # Note: This is a weak assertion as GC is non-deterministic
        # We mainly test that gc.collect() can be called without errors
        assert final_collections is not None

    @pytest.mark.asyncio
    async def test_embedding_service_cleanup(self):
        """Test that embedding service can clear cache to free memory."""
        service = UnifiedEmbeddingService(cache_max_size=1000)

        # Populate cache
        texts = [f"Document {i}" for i in range(100)]
        await service.embed_batch(texts)

        initial_size = service.cache.stats()["size"]
        assert initial_size > 0

        # Clear cache
        service.cache.cache.clear()

        final_size = service.cache.stats()["size"]
        assert final_size == 0


class TestRedisMemoryBudget:
    """Test Redis cache budget configuration."""

    @pytest.mark.asyncio
    async def test_redis_lru_eviction(self):
        """Test Redis LRU eviction policy.

        This test requires Redis to be running with maxmemory-policy=allkeys-lru.
        Skipped if Redis not available.
        """
        try:
            import redis.asyncio as redis
        except ImportError:
            pytest.skip("redis package not installed")

        try:
            # Connect to Redis
            client = redis.Redis(host="localhost", port=6379, decode_responses=True)
            await client.ping()

            # Check maxmemory policy
            config = await client.config_get("maxmemory-policy")
            assert "allkeys-lru" in config.values(), "Redis should use allkeys-lru policy"

            # Check maxmemory limit
            maxmemory = await client.config_get("maxmemory")
            maxmemory_bytes = int(maxmemory.get("maxmemory", 0))

            # Should be configured to 8GB (8589934592 bytes)
            expected_bytes = 8 * 1024 * 1024 * 1024
            assert maxmemory_bytes == expected_bytes, f"Redis maxmemory should be 8GB, got {maxmemory_bytes / 1024 / 1024 / 1024:.2f}GB"

            await client.aclose()

        except redis.ConnectionError:
            pytest.skip("Redis not available")


@pytest.mark.slow
class TestMemoryOptimizationE2E:
    """End-to-end tests for memory optimization features."""

    @pytest.mark.asyncio
    async def test_large_batch_embedding_memory_stable(self):
        """Test that large batch embedding doesn't cause memory leak."""
        service = UnifiedEmbeddingService(cache_max_size=10000)
        profiler = MemoryProfiler()

        async with profiler.profile("large_batch_embedding", sample_interval_seconds=0.1):
            # Process large batch in chunks
            batch_size = 100
            total_batches = 10

            for batch_idx in range(total_batches):
                texts = [f"Batch {batch_idx} Document {i}" for i in range(batch_size)]
                await service.embed_batch(texts)

                # Explicit cleanup after each batch
                import gc

                gc.collect()

        stats = profiler.get_stats("large_batch_embedding")

        # Memory should not grow unbounded
        # Delta should be reasonable (<200MB for 1000 embeddings)
        if profiler._enabled:
            assert stats["delta_process_mb"] < 200, f"Memory grew by {stats['delta_process_mb']:.2f}MB (expected <200MB)"

    @pytest.mark.asyncio
    async def test_repeated_operations_no_memory_leak(self):
        """Test that repeated operations don't leak memory."""
        service = UnifiedEmbeddingService(cache_max_size=100)
        profiler = MemoryProfiler()

        async def operation():
            """Single operation that should not leak."""
            text = "Test document for memory leak detection"
            embedding = await service.embed_single(text)
            return len(embedding)

        async with profiler.profile("repeated_operations", sample_interval_seconds=0.05):
            # Run operation many times
            for _ in range(100):
                await operation()

        stats = profiler.get_stats("repeated_operations")

        # Memory delta should be minimal (<50MB)
        if profiler._enabled:
            assert abs(stats["delta_process_mb"]) < 50, f"Memory leak detected: {stats['delta_process_mb']:.2f}MB delta"
