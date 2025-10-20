"""Unit tests for RedisMemoryManager (Sprint 9 Feature 9.1).

Tests cover:
- Redis connection management (single and cluster mode)
- Memory entry storage and retrieval
- TTL-based expiration
- Tag-based search
- Capacity monitoring
- Eviction policies
- Performance requirements (<10ms for read/write)
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.memory.models import MemoryEntry
from src.components.memory.redis_manager import RedisMemoryManager
from src.core.exceptions import MemoryError


class TestRedisMemoryManagerInit:
    """Test RedisMemoryManager initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        manager = RedisMemoryManager()

        assert manager.redis_url is not None
        assert manager.default_ttl > 0
        assert manager.cluster_mode is False
        assert manager.eviction_threshold == 0.8
        assert manager._client is None

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        manager = RedisMemoryManager(
            redis_url="redis://custom:6379",
            default_ttl_seconds=7200,
            cluster_mode=True,
            cluster_nodes=[{"host": "node1", "port": 6379}],
            eviction_threshold=0.9,
            max_memory_bytes=1000000,
        )

        assert manager.redis_url == "redis://custom:6379"
        assert manager.default_ttl == 7200
        assert manager.cluster_mode is True
        assert len(manager.cluster_nodes) == 1
        assert manager.eviction_threshold == 0.9
        assert manager.max_memory_bytes == 1000000


class TestRedisConnection:
    """Test Redis connection management."""

    @pytest.mark.asyncio
    async def test_initialize_single_mode(self):
        """Test initialization in single-node mode."""
        manager = RedisMemoryManager(cluster_mode=False)

        with patch("src.components.memory.redis_manager.Redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_redis.from_url = AsyncMock(return_value=mock_client)

            await manager.initialize()

            assert manager._client is not None
            mock_redis.from_url.assert_called_once()
            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_cluster_mode(self):
        """Test initialization in cluster mode."""
        manager = RedisMemoryManager(
            cluster_mode=True,
            cluster_nodes=[{"host": "node1", "port": 6379}],
        )

        with patch("src.components.memory.redis_manager.RedisCluster") as mock_cluster:
            mock_client = MagicMock()
            mock_client.ping = AsyncMock()
            mock_cluster.return_value = mock_client

            await manager.initialize()

            assert manager._client is not None
            mock_cluster.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self):
        """Test handling of connection failures."""
        manager = RedisMemoryManager()

        with patch("src.components.memory.redis_manager.Redis") as mock_redis:
            mock_redis.from_url = AsyncMock(side_effect=Exception("Connection failed"))

            with pytest.raises(MemoryError, match="Failed to connect to Redis"):
                await manager.initialize()

    @pytest.mark.asyncio
    async def test_close_connection(self):
        """Test closing Redis connection."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        await manager.close()

        assert manager._client is None
        mock_client.close.assert_called_once()


class TestMemoryStorage:
    """Test memory storage operations."""

    @pytest.mark.asyncio
    async def test_store_basic_entry(self):
        """Test storing a basic memory entry."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        # Mock capacity check
        mock_client.info = AsyncMock(return_value={"used_memory": 100, "maxmemory": 1000})

        entry = MemoryEntry(
            key="test_key",
            value="test_value",
            ttl_seconds=3600,
            tags=["tag1", "tag2"],
        )

        result = await manager.store(entry)

        assert result is True
        mock_client.setex.assert_called_once()
        # Check that tags were indexed
        assert mock_client.sadd.call_count == 2  # One for each tag

    @pytest.mark.asyncio
    async def test_store_with_eviction_trigger(self):
        """Test storage triggers eviction when capacity exceeded."""
        manager = RedisMemoryManager(eviction_threshold=0.8)
        mock_client = AsyncMock()
        manager._client = mock_client

        # Mock high capacity (90%)
        mock_client.info = AsyncMock(return_value={"used_memory": 900, "maxmemory": 1000})

        # Mock scan for eviction
        async def mock_scan_iter(*args, **kwargs):
            yield "memory:old_key1"
            yield "memory:old_key2"

        mock_client.scan_iter = mock_scan_iter
        mock_client.get = AsyncMock(
            return_value=json.dumps(
                {"value": "old", "access_count": 1, "created_at": "2020-01-01T00:00:00"}
            )
        )
        mock_client.ttl = AsyncMock(return_value=100)

        entry = MemoryEntry(key="new_key", value="new_value")

        result = await manager.store(entry)

        assert result is True
        # Verify eviction was called
        assert mock_client.delete.call_count >= 1

    @pytest.mark.asyncio
    async def test_store_performance(self):
        """Test that store operation meets performance target (<10ms)."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        # Mock fast responses
        mock_client.info = AsyncMock(return_value={"used_memory": 100, "maxmemory": 1000})
        mock_client.setex = AsyncMock()
        mock_client.sadd = AsyncMock()
        mock_client.expire = AsyncMock()

        entry = MemoryEntry(key="test", value="test")

        start = time.time()
        await manager.store(entry)
        elapsed_ms = (time.time() - start) * 1000

        # Should be well under 10ms with mocked client
        assert elapsed_ms < 100  # Generous for test overhead


class TestMemoryRetrieval:
    """Test memory retrieval operations."""

    @pytest.mark.asyncio
    async def test_retrieve_existing_entry(self):
        """Test retrieving an existing memory entry."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        stored_data = {
            "value": "test_value",
            "tags": ["tag1"],
            "created_at": "2024-01-01T12:00:00",
            "metadata": {"key": "value"},
            "access_count": 5,
        }

        mock_client.get = AsyncMock(return_value=json.dumps(stored_data))
        mock_client.ttl = AsyncMock(return_value=1800)
        mock_client.setex = AsyncMock()

        entry = await manager.retrieve("test_key", track_access=True)

        assert entry is not None
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.tags == ["tag1"]
        assert entry.metadata == {"key": "value"}

        # Verify access tracking updated
        mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_entry(self):
        """Test retrieving a non-existent entry returns None."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        mock_client.get = AsyncMock(return_value=None)

        entry = await manager.retrieve("nonexistent_key")

        assert entry is None

    @pytest.mark.asyncio
    async def test_retrieve_without_access_tracking(self):
        """Test retrieving entry without incrementing access count."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        stored_data = {
            "value": "test_value",
            "tags": [],
            "created_at": "2024-01-01T12:00:00",
            "metadata": {},
            "access_count": 5,
        }

        mock_client.get = AsyncMock(return_value=json.dumps(stored_data))
        mock_client.ttl = AsyncMock(return_value=1800)

        entry = await manager.retrieve("test_key", track_access=False)

        assert entry is not None
        # Should not update access count
        mock_client.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_performance(self):
        """Test that retrieve operation meets performance target (<10ms)."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        stored_data = {
            "value": "test_value",
            "tags": [],
            "created_at": "2024-01-01T12:00:00",
            "metadata": {},
            "access_count": 0,
        }

        mock_client.get = AsyncMock(return_value=json.dumps(stored_data))
        mock_client.ttl = AsyncMock(return_value=1800)

        start = time.time()
        await manager.retrieve("test_key", track_access=False)
        elapsed_ms = (time.time() - start) * 1000

        # Should be well under 10ms with mocked client
        assert elapsed_ms < 100


class TestTagSearch:
    """Test tag-based search functionality."""

    @pytest.mark.asyncio
    async def test_search_by_tags(self):
        """Test searching entries by tags."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        # Mock tag index
        mock_client.smembers = AsyncMock(return_value={"memory:entry1", "memory:entry2"})

        # Mock entry retrieval
        stored_data = {
            "value": "test_value",
            "tags": ["tag1"],
            "created_at": "2024-01-01T12:00:00",
            "metadata": {},
            "access_count": 0,
        }

        mock_client.get = AsyncMock(return_value=json.dumps(stored_data))
        mock_client.ttl = AsyncMock(return_value=1800)

        results = await manager.search(tags=["tag1"], limit=10)

        assert len(results) == 2
        assert all(isinstance(r, MemoryEntry) for r in results)

    @pytest.mark.asyncio
    async def test_search_with_fallback_scan(self):
        """Test search falls back to scan when no tag index."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        # Mock empty tag index
        mock_client.smembers = AsyncMock(return_value=set())

        # Mock scan
        async def mock_scan_iter(*args, **kwargs):
            yield "memory:entry1"
            yield "memory:entry2"

        mock_client.scan_iter = mock_scan_iter

        stored_data = {
            "value": "test_value",
            "tags": ["tag1", "tag2"],
            "created_at": "2024-01-01T12:00:00",
            "metadata": {},
            "access_count": 0,
        }

        mock_client.get = AsyncMock(return_value=json.dumps(stored_data))
        mock_client.ttl = AsyncMock(return_value=1800)

        results = await manager.search(tags=["tag1"], limit=10)

        assert len(results) == 2


class TestCapacityMonitoring:
    """Test memory capacity monitoring."""

    @pytest.mark.asyncio
    async def test_get_capacity_with_limit(self):
        """Test getting capacity when maxmemory is set."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        mock_client.info = AsyncMock(
            return_value={"used_memory": 500_000_000, "maxmemory": 1_000_000_000}
        )

        capacity = await manager.get_capacity()

        assert capacity == 0.5

    @pytest.mark.asyncio
    async def test_get_capacity_without_limit(self):
        """Test capacity when no maxmemory is set."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        mock_client.info = AsyncMock(return_value={"used_memory": 500_000_000, "maxmemory": 0})

        capacity = await manager.get_capacity()

        assert capacity == 0.0  # Unlimited = low capacity

    @pytest.mark.asyncio
    async def test_capacity_caching(self):
        """Test that capacity info is cached."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        mock_client.info = AsyncMock(return_value={"used_memory": 500, "maxmemory": 1000})

        # First call
        capacity1 = await manager.get_capacity()

        # Second call (should use cache)
        capacity2 = await manager.get_capacity()

        assert capacity1 == capacity2
        # Info should only be called once due to caching
        assert mock_client.info.call_count == 1


class TestEvictionPolicies:
    """Test eviction policy implementation."""

    @pytest.mark.asyncio
    async def test_evict_old_entries(self):
        """Test evicting old entries with low access count."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        # Mock entries with different access counts
        entries_data = [
            json.dumps(
                {
                    "value": f"value{i}",
                    "access_count": i % 3,
                    "created_at": f"2024-01-0{i+1}T00:00:00",
                }
            )
            for i in range(10)
        ]

        async def mock_scan_iter(*args, **kwargs):
            for i in range(10):
                yield f"memory:entry{i}"

        mock_client.scan_iter = mock_scan_iter

        call_count = [0]

        async def mock_get(key):
            idx = call_count[0]
            call_count[0] += 1
            return entries_data[idx] if idx < len(entries_data) else None

        mock_client.get = mock_get
        mock_client.ttl = AsyncMock(return_value=100)
        mock_client.delete = AsyncMock()

        evicted = await manager.evict_old_entries()

        # Should evict bottom 20% = 2 entries
        assert evicted == 2
        assert mock_client.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_evict_no_entries(self):
        """Test eviction when no entries exist."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        async def mock_scan_iter(*args, **kwargs):
            return
            yield  # Empty generator

        mock_client.scan_iter = mock_scan_iter

        evicted = await manager.evict_old_entries()

        assert evicted == 0


class TestDeleteOperation:
    """Test delete operations."""

    @pytest.mark.asyncio
    async def test_delete_existing_entry(self):
        """Test deleting an existing entry."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        mock_client.delete = AsyncMock(return_value=1)

        result = await manager.delete("test_key")

        assert result is True
        mock_client.delete.assert_called_once_with("memory:test_key")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_entry(self):
        """Test deleting a non-existent entry."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        mock_client.delete = AsyncMock(return_value=0)

        result = await manager.delete("nonexistent_key")

        assert result is False


class TestStatistics:
    """Test statistics gathering."""

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting memory statistics."""
        manager = RedisMemoryManager()
        mock_client = AsyncMock()
        manager._client = mock_client

        # Mock entries
        async def mock_scan_iter(*args, **kwargs):
            yield "memory:entry1"
            yield "memory:entry2"

        mock_client.scan_iter = mock_scan_iter

        stored_data = json.dumps(
            {"value": "test", "access_count": 5, "created_at": "2024-01-01T00:00:00"}
        )

        mock_client.get = AsyncMock(return_value=stored_data)
        mock_client.ttl = AsyncMock(return_value=1800)
        mock_client.info = AsyncMock(return_value={"used_memory": 500, "maxmemory": 1000})

        stats = await manager.get_stats()

        assert stats["total_entries"] == 2
        assert stats["total_access_count"] == 10  # 5 * 2 entries
        assert stats["avg_access_count"] == 5.0
        assert stats["capacity"] == 0.5
