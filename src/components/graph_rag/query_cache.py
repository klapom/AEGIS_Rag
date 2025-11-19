"""Graph Query Cache with LRU Eviction and TTL Support.

This module provides a thread-safe cache for graph query results with:
- LRU (Least Recently Used) eviction policy
- TTL (Time-To-Live) based expiration
- Cache statistics and metrics
- Singleton pattern for global access
- Async-safe operations
"""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from typing import Any

import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)

class GraphQueryCache:
    """LRU cache for graph query results with TTL expiration.

    Thread-safe cache implementation with:
    - LRU eviction when max size reached
    - TTL-based expiration for stale data
    - Statistics tracking (hits, misses, evictions)
    - Cache key hashing from query + parameters

    Example:
        >>> cache = GraphQueryCache(max_size=100, ttl_seconds=300)
        >>> cache.set("MATCH (n) RETURN n", {}, results)
        >>> cached = cache.get("MATCH (n) RETURN n", {})
        >>> stats = cache.stats()
        >>> print(stats["hit_rate"])
    """

    def __init__(
        self,
        max_size: int | None = None,
        ttl_seconds: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        """Initialize query cache.

        Args:
            max_size: Maximum cache entries (default: from settings)
            ttl_seconds: Time-to-live in seconds (default: from settings)
            enabled: Enable caching (default: from settings)
        """
        self.max_size = max_size or settings.graph_query_cache_max_size
        self.ttl_seconds = ttl_seconds or settings.graph_query_cache_ttl_seconds
        self.enabled = enabled if enabled is not None else settings.graph_query_cache_enabled

        # Cache storage: OrderedDict maintains insertion order for LRU
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

        logger.info(
            "GraphQueryCache initialized",
            max_size=self.max_size,
            ttl_seconds=self.ttl_seconds,
            enabled=self.enabled,
        )

    def _generate_cache_key(self, query: str, parameters: dict[str, Any] | None = None) -> str:
        """Generate cache key from query and parameters.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            SHA-256 hash of query + sorted parameters
        """
        params = parameters or {}

        # Sort parameters for consistent hashing
        params_str = json.dumps(params, sort_keys=True)
        cache_input = f"{query}::{params_str}"

        # Generate hash
        cache_key = hashlib.sha256(cache_input.encode()).hexdigest()

        return cache_key

    def _is_expired(self, entry: dict[str, Any]) -> bool:
        """Check if cache entry is expired.

        Args:
            entry: Cache entry with timestamp

        Returns:
            True if entry is expired
        """
        if "timestamp" not in entry:
            return True

        age_seconds = time.time() - entry["timestamp"]
        return age_seconds > self.ttl_seconds

    async def get(self, query: str, parameters: dict[str, Any] | None = None) -> Any | None:
        """Get cached query result.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Cached result or None if not found/expired
        """
        if not self.enabled:
            return None

        cache_key = self._generate_cache_key(query, parameters)

        async with self._lock:
            # Check if key exists
            if cache_key not in self._cache:
                self._misses += 1
                logger.debug("Cache miss", query=query[:50])
                return None

            entry = self._cache[cache_key]

            # Check if expired
            if self._is_expired(entry):
                del self._cache[cache_key]
                self._misses += 1
                logger.debug("Cache miss (expired)", query=query[:50])
                return None

            # Move to end (mark as recently used)
            self._cache.move_to_end(cache_key)
            self._hits += 1

            logger.debug("Cache hit", query=query[:50])
            return entry["result"]  # type: ignore[no-any-return]

    async def set(
        self, query: str, parameters: dict[str, Any] | None = None, result: Any = None
    ) -> None:
        """set cached query result.

        Args:
            query: Cypher query string
            parameters: Query parameters
            result: Query result to cache
        """
        if not self.enabled:
            return

        cache_key = self._generate_cache_key(query, parameters)

        async with self._lock:
            # Check if we need to evict
            if cache_key not in self._cache and len(self._cache) >= self.max_size:
                # Remove oldest entry (first item in OrderedDict)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
                logger.debug("Cache eviction (LRU)", evicted_key=oldest_key[:16])

            # Store entry with timestamp
            self._cache[cache_key] = {"result": result, "timestamp": time.time()}

            # Move to end if already exists (update LRU order)
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)

            logger.debug("Cache set", query=query[:50], cache_size=len(self._cache))

    async def invalidate(self, query: str, parameters: dict[str, Any] | None = None) -> bool:
        """Invalidate a specific cache entry.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            True if entry was invalidated
        """
        if not self.enabled:
            return False

        cache_key = self._generate_cache_key(query, parameters)

        async with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                self._invalidations += 1
                logger.debug("Cache invalidated", query=query[:50])
                return True

            return False

    async def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Cache cleared", entries_removed=count)
            return count

    async def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

            return {
                "enabled": self.enabled,
                "max_size": self.max_size,
                "current_size": len(self._cache),
                "ttl_seconds": self.ttl_seconds,
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_rate": round(hit_rate, 2),
                "evictions": self._evictions,
                "invalidations": self._invalidations,
            }

    async def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if self._is_expired(entry)]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info("Cleaned up expired cache entries", count=len(expired_keys))

            return len(expired_keys)

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0
        logger.info("Cache statistics reset")

    def __len__(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def __contains__(self, query: str) -> bool:
        """Check if query is in cache (simplified check without parameters)."""
        # This is a simplified check - actual caching uses query + parameters
        cache_key = self._generate_cache_key(query, None)
        return cache_key in self._cache

# Global cache instance (singleton pattern)
_query_cache: GraphQueryCache | None = None
_cache_lock = asyncio.Lock()

async def get_query_cache() -> GraphQueryCache:
    """Get global query cache instance (singleton).

    Returns:
        GraphQueryCache instance
    """
    global _query_cache

    if _query_cache is None:
        async with _cache_lock:
            # Double-check pattern
            if _query_cache is None:
                _query_cache = GraphQueryCache()

    return _query_cache

def get_query_cache_sync() -> GraphQueryCache:
    """Get global query cache instance (synchronous, for testing).

    Returns:
        GraphQueryCache instance
    """
    global _query_cache

    if _query_cache is None:
        _query_cache = GraphQueryCache()

    return _query_cache
