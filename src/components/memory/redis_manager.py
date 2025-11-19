"""Redis Working Memory Manager for Layer 1 Short-Term Memory (Sprint 9 Feature 9.1).

This module provides Redis-based working memory with:
- Redis Connection Manager with Cluster Support
- Memory Entry Model (key-value, TTL, tags)
- Eviction Policies (LRU, TTL-based)
- Memory Capacity Monitoring
"""

import json
import time
from datetime import UTC, datetime
from typing import Any

import structlog
from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster
from redis.exceptions import RedisError

from src.components.memory.models import MemoryEntry
from src.core.config import settings
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


class RedisMemoryManager:
    """Redis-based working memory manager with cluster support and eviction policies.

    Features:
    - Cluster-ready (supports single node and cluster modes)
    - TTL-based auto-cleanup
    - Capacity monitoring with configurable thresholds
    - Automatic eviction at 80% capacity
    - Tag-based search
    - Access tracking for consolidation

    Performance Targets:
    - Memory Write/Read <10ms (p95)
    - TTL-based auto-cleanup
    - Eviction at 80% capacity
    """

    def __init__(
        self,
        redis_url: str | None = None,
        default_ttl_seconds: int | None = None,
        cluster_mode: bool = False,
        cluster_nodes: list[dict[str, Any]] | None = None,
        eviction_threshold: float = 0.8,
        max_memory_bytes: int | None = None,
    ) -> None:
        """Initialize Redis memory manager.

        Args:
            redis_url: Redis connection URL (default: from settings)
            default_ttl_seconds: Default TTL in seconds (default: from settings)
            cluster_mode: Enable cluster mode (default: False)
            cluster_nodes: list of cluster nodes [{host, port}, ...]
            eviction_threshold: Memory usage threshold for eviction (0.0-1.0, default: 0.8)
            max_memory_bytes: Maximum memory in bytes (None = use Redis config)
        """
        self.redis_url = redis_url or settings.redis_memory_url
        self.default_ttl = default_ttl_seconds or settings.redis_memory_ttl_seconds
        self.cluster_mode = cluster_mode
        self.cluster_nodes = cluster_nodes or []
        self.eviction_threshold = eviction_threshold
        self.max_memory_bytes = max_memory_bytes

        self._client: Redis | RedisCluster | None = None
        self._capacity_cache: dict[str, Any] = {}
        self._capacity_cache_ttl = 10  # Cache capacity info for 10 seconds

        logger.info(
            "Initialized RedisMemoryManager",
            redis_url=self.redis_url,
            default_ttl_seconds=self.default_ttl,
            cluster_mode=cluster_mode,
            eviction_threshold=eviction_threshold,
        )

    async def initialize(self) -> None:
        """Initialize Redis client connection.

        Raises:
            MemoryError: If connection fails
        """
        if self._client is not None:
            return

        try:
            if self.cluster_mode and self.cluster_nodes:
                # Initialize Redis Cluster
                self._client = RedisCluster(
                    startup_nodes=self.cluster_nodes,
                    decode_responses=True,
                )
            else:
                # Initialize single Redis instance
                self._client = await Redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )

            # Test connection
            await self._client.ping()
            logger.info("Redis client initialized and connected", cluster_mode=self.cluster_mode)

        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise MemoryError(f"Failed to connect to Redis: {e}", reason="connection_failed") from e

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis client closed")

    async def store(self, entry: MemoryEntry) -> bool:
        """Store memory entry with automatic expiration.

        Args:
            entry: MemoryEntry to store

        Returns:
            True if stored successfully

        Raises:
            MemoryError: If storage fails

        Performance: <10ms (p95)
        """
        start_time = time.time()

        try:
            await self.initialize()

            # Check capacity and evict if needed
            capacity = await self.get_capacity()
            if capacity >= self.eviction_threshold:
                evicted_count = await self.evict_old_entries()
                logger.info(
                    "Eviction triggered",
                    capacity=capacity,
                    threshold=self.eviction_threshold,
                    evicted_count=evicted_count,
                )

            # Prepare data for storage
            data = {
                "value": entry.value,
                "tags": entry.tags,
                "created_at": entry.created_at.isoformat(),
                "metadata": entry.metadata,
                "access_count": 0,
            }

            serialized = json.dumps(data)

            # Store with TTL
            if self._client is None:
                raise MemoryError("Redis client not initialized", reason="client_not_initialized")
            await self._client.setex(entry.namespaced_key, entry.ttl_seconds, serialized)

            # Store tags for searchability
            if entry.tags:
                await self._index_tags(entry)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Stored memory entry",
                key=entry.namespaced_key,
                ttl_seconds=entry.ttl_seconds,
                tags_count=len(entry.tags),
                elapsed_ms=round(elapsed_ms, 2),
            )

            return True

        except Exception as e:
            logger.error("Failed to store memory entry", key=entry.key, error=str(e))
            raise MemoryError(operation="store", reason=str(e)) from e

    async def retrieve(
        self, key: str, namespace: str = "memory", track_access: bool = True
    ) -> MemoryEntry | None:
        """Retrieve memory entry.

        Args:
            key: Entry key
            namespace: Key namespace (default: "memory")
            track_access: Increment access counter (default: True)

        Returns:
            MemoryEntry if found, None otherwise

        Raises:
            MemoryError: If retrieval fails

        Performance: <10ms (p95)
        """
        start_time = time.time()

        try:
            await self.initialize()

            namespaced_key = f"{namespace}:{key}"
            serialized = await self._client.get(namespaced_key)

            if not serialized:
                logger.debug("Memory entry not found", key=namespaced_key)
                return None

            # Deserialize
            data = json.loads(serialized)

            # Update access tracking
            if track_access:
                data["access_count"] = data.get("access_count", 0) + 1
                data["last_accessed_at"] = datetime.now(UTC).isoformat()

                # Update with same TTL
                ttl = await self._client.ttl(namespaced_key)
                if ttl > 0:
                    await self._client.setex(namespaced_key, ttl, json.dumps(data))

            # Reconstruct MemoryEntry
            entry = MemoryEntry(
                key=key,
                value=data["value"],
                ttl_seconds=await self._client.ttl(namespaced_key),
                tags=data.get("tags", []),
                created_at=datetime.fromisoformat(data["created_at"]),
                metadata=data.get("metadata", {}),
                namespace=namespace,
            )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Retrieved memory entry",
                key=namespaced_key,
                access_count=data.get("access_count"),
                elapsed_ms=round(elapsed_ms, 2),
            )

            return entry

        except RedisError as e:
            logger.error("Failed to retrieve memory entry", key=key, error=str(e))
            raise MemoryError(operation="Failed to retrieve memory entry", reason=str(e)) from e

    async def search(
        self, tags: list[str], namespace: str = "memory", limit: int = 100
    ) -> list[MemoryEntry]:
        """Search memory entries by tags.

        Args:
            tags: list of tags to search for
            namespace: Key namespace (default: "memory")
            limit: Maximum results to return

        Returns:
            list of matching MemoryEntry objects
        """
        try:
            await self.initialize()

            results = []
            tag_set = f"{namespace}:tags:{':'.join(sorted(tags))}"

            # Try to get from tag index
            keys = await self._client.smembers(tag_set)

            if not keys:
                # Fallback: scan all keys and filter
                pattern = f"{namespace}:*"
                async for key in self._client.scan_iter(match=pattern, count=100):
                    serialized = await self._client.get(key)
                    if not serialized:
                        continue

                    data = json.loads(serialized)
                    entry_tags = set(data.get("tags", []))

                    if set(tags).intersection(entry_tags):
                        entry_key = key.replace(f"{namespace}:", "")
                        entry = await self.retrieve(entry_key, namespace, track_access=False)
                        if entry:
                            results.append(entry)

                    if len(results) >= limit:
                        break
            else:
                # Get entries from tag index
                for key in list(keys)[:limit]:
                    entry_key = key.replace(f"{namespace}:", "")
                    entry = await self.retrieve(entry_key, namespace, track_access=False)
                    if entry:
                        results.append(entry)

            logger.info("Searched memory by tags", tags=tags, results_count=len(results))
            return results[:limit]

        except Exception as e:
            logger.error("Failed to search memory", tags=tags, error=str(e))
            return []

    async def get_capacity(self) -> float:
        """Get current memory capacity utilization.

        Returns:
            Capacity utilization (0.0-1.0)

        Uses caching to avoid expensive Redis INFO calls.
        """
        try:
            # Check cache
            now = time.time()
            if self._capacity_cache.get("timestamp", 0) + self._capacity_cache_ttl > now:
                return self._capacity_cache.get("capacity", 0.0)  # type: ignore[no-any-return]

            await self.initialize()

            # Get memory info from Redis
            info = await self._client.info("memory")
            used_memory = info.get("used_memory", 0)
            maxmemory = info.get("maxmemory", 0)

            # If no maxmemory set, use our configured max or assume unlimited
            if maxmemory == 0:
                if self.max_memory_bytes:
                    maxmemory = self.max_memory_bytes
                else:
                    # Assume unlimited, return low capacity
                    capacity = 0.0
                    self._capacity_cache = {"timestamp": now, "capacity": capacity}
                    return capacity

            capacity = used_memory / maxmemory if maxmemory > 0 else 0.0

            # Cache result
            self._capacity_cache = {"timestamp": now, "capacity": capacity}

            logger.debug(
                "Memory capacity checked",
                used_memory_mb=round(used_memory / 1024 / 1024, 2),
                max_memory_mb=round(maxmemory / 1024 / 1024, 2),
                capacity=round(capacity, 3),
            )

            return capacity

        except Exception as e:
            logger.error("Failed to get memory capacity", error=str(e))
            return 0.0

    async def evict_old_entries(self, namespace: str = "memory") -> int:
        """Evict old entries when capacity exceeds threshold.

        Args:
            namespace: Key namespace to evict from

        Returns:
            Number of evicted entries

        Strategy: Evict entries with lowest access count and oldest creation time.
        """
        try:
            await self.initialize()

            # Get all entries with metadata
            entries_metadata = []
            pattern = f"{namespace}:*"

            async for key in self._client.scan_iter(match=pattern, count=100):
                if ":tags:" in key:  # Skip tag index keys
                    continue

                serialized = await self._client.get(key)
                if not serialized:
                    continue

                data = json.loads(serialized)
                ttl = await self._client.ttl(key)

                entries_metadata.append(
                    {
                        "key": key,
                        "access_count": data.get("access_count", 0),
                        "created_at": data.get("created_at"),
                        "ttl": ttl,
                    }
                )

            if not entries_metadata:
                return 0

            # Sort by access_count (ascending) and created_at (oldest first)
            entries_metadata.sort(
                key=lambda x: (x["access_count"], x["created_at"] or "9999-99-99")
            )

            # Evict bottom 20% of entries
            evict_count = max(1, int(len(entries_metadata) * 0.2))
            evicted = 0

            for entry in entries_metadata[:evict_count]:
                try:
                    await self._client.delete(entry["key"])
                    evicted += 1
                except Exception as e:
                    logger.warning("Failed to evict entry", key=entry["key"], error=str(e))

            logger.info(
                "Evicted old entries",
                total_entries=len(entries_metadata),
                evicted_count=evicted,
            )

            # Clear capacity cache
            self._capacity_cache = {}

            return evicted

        except Exception as e:
            logger.error("Failed to evict entries", error=str(e))
            return 0

    async def delete(self, key: str, namespace: str = "memory") -> bool:
        """Delete memory entry.

        Args:
            key: Entry key
            namespace: Key namespace

        Returns:
            True if deleted, False if not found
        """
        try:
            await self.initialize()

            namespaced_key = f"{namespace}:{key}"
            deleted = await self._client.delete(namespaced_key)

            logger.debug("Deleted memory entry", key=namespaced_key, existed=bool(deleted))
            return bool(deleted)

        except Exception as e:
            logger.error("Failed to delete memory entry", key=key, error=str(e))
            return False

    async def get_stats(self, namespace: str = "memory") -> dict[str, Any]:
        """Get statistics for memory usage.

        Args:
            namespace: Key namespace

        Returns:
            Dictionary with memory statistics
        """
        try:
            await self.initialize()

            pattern = f"{namespace}:*"
            total_entries = 0
            total_access_count = 0
            avg_ttl = 0

            async for key in self._client.scan_iter(match=pattern, count=100):
                if ":tags:" in key:
                    continue

                total_entries += 1
                serialized = await self._client.get(key)
                if serialized:
                    data = json.loads(serialized)
                    total_access_count += data.get("access_count", 0)
                    ttl = await self._client.ttl(key)
                    avg_ttl += ttl if ttl > 0 else 0

            capacity = await self.get_capacity()

            stats = {
                "namespace": namespace,
                "total_entries": total_entries,
                "total_access_count": total_access_count,
                "avg_access_count": total_access_count / total_entries if total_entries > 0 else 0,
                "avg_ttl_seconds": avg_ttl / total_entries if total_entries > 0 else 0,
                "capacity": round(capacity, 3),
                "eviction_threshold": self.eviction_threshold,
            }

            logger.info("Memory statistics", **stats)
            return stats

        except Exception as e:
            logger.error("Failed to get memory stats", error=str(e))
            return {}

    async def _index_tags(self, entry: MemoryEntry) -> None:
        """Index tags for fast searching.

        Args:
            entry: Memory entry with tags
        """
        try:
            for tag in entry.tags:
                tag_set = f"{entry.namespace}:tags:{tag}"
                await self._client.sadd(tag_set, entry.namespaced_key)
                # set TTL on tag index to match entry TTL
                await self._client.expire(tag_set, entry.ttl_seconds)
        except Exception as e:
            logger.warning("Failed to index tags", key=entry.key, error=str(e))

    # Helper methods for E2E tests
    async def get(self, key: str, namespace: str = "memory") -> MemoryEntry | None:
        """Alias for retrieve() method for backward compatibility."""
        return await self.retrieve(key, namespace, track_access=True)

    async def count(self, namespace: str = "memory") -> int:
        """Count total entries in namespace."""
        try:
            await self.initialize()
            pattern = f"{namespace}:*"
            count = 0
            async for key in self._client.scan_iter(match=pattern, count=100):
                if ":tags:" not in key:  # Skip tag index keys
                    count += 1
            return count
        except Exception as e:
            logger.error("Failed to count entries", error=str(e))
            return 0

    async def clear_all(self, namespace: str = "memory") -> int:
        """Clear all entries in namespace."""
        try:
            await self.initialize()
            pattern = f"{namespace}:*"
            deleted = 0
            async for key in self._client.scan_iter(match=pattern, count=100):
                await self._client.delete(key)
                deleted += 1
            logger.info("Cleared all entries", namespace=namespace, deleted_count=deleted)
            return deleted
        except Exception as e:
            logger.error("Failed to clear entries", error=str(e))
            return 0

    async def get_capacity_info(self) -> dict[str, Any]:
        """Get detailed capacity information."""
        try:
            await self.initialize()
            info = await self._client.info("memory")
            used_memory = info.get("used_memory", 0)
            maxmemory = info.get("maxmemory", 0) or self.max_memory_bytes or 0

            return {
                "used_mb": used_memory / 1024 / 1024,
                "max_mb": maxmemory / 1024 / 1024,
                "usage_percent": (used_memory / maxmemory * 100) if maxmemory > 0 else 0,
            }
        except Exception as e:
            logger.error("Failed to get capacity info", error=str(e))
            return {"used_mb": 0, "max_mb": 0, "usage_percent": 0}

    async def evict_if_needed(self, namespace: str = "memory") -> dict[str, Any]:
        """Manually trigger eviction if needed."""
        try:
            capacity = await self.get_capacity()
            if capacity >= self.eviction_threshold:
                count = await self.evict_old_entries(namespace)
                return {"evicted": True, "count": count}
            return {"evicted": False, "count": 0}
        except Exception as e:
            logger.error("Failed to evict", error=str(e))
            return {"evicted": False, "count": 0, "error": str(e)}


# Global instance (singleton pattern)
_redis_manager: RedisMemoryManager | None = None


def get_redis_manager() -> RedisMemoryManager:
    """Get global Redis memory manager instance (singleton).

    Returns:
        RedisMemoryManager instance
    """
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisMemoryManager()
    return _redis_manager
