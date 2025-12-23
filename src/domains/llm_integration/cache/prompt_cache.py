"""
Redis-based LLM prompt caching service.

Sprint 63 Feature 63.3: Redis Prompt Caching

This module provides efficient caching of LLM prompt results using Redis,
reducing latency and costs for repeated queries across multi-tenant environments.

Architecture:
    PromptCacheService → Redis → LLM Response Cache
                              → Cache Statistics

Features:
    - Deterministic cache keys using SHA256 hashing of prompts
    - Model-specific caching (avoid cross-model cache hits)
    - Namespace isolation (multi-tenant support)
    - Configurable TTL per query type
    - Cache statistics tracking (hits, misses, hit rate)
    - Automatic cache invalidation per namespace

Cache Key Strategy:
    Format: prompt_cache:{namespace}:{model}:{sha256_hash(prompt)}
    Example: prompt_cache:default:llama3.2:8b:a1b2c3d4...

TTL Strategy:
    - Research queries: 30 min (1800s)
    - Extraction queries: 24 hour (86400s)
    - Chat queries: 1 hour (3600s)
    - Default: 1 hour (3600s)

Multi-Tenant Support:
    Each namespace has isolated cache space. Invalidating a namespace
    clears all cached prompts for that tenant without affecting others.
"""

from __future__ import annotations

import hashlib
import time
from typing import TYPE_CHECKING, Optional

import redis.asyncio as redis
import structlog

from src.core.config import settings
from src.domains.llm_integration.cache.models import CacheStats

logger = structlog.get_logger(__name__)


class PromptCacheService:
    """
    Redis-based LLM prompt caching service.

    Caches LLM prompt results to reduce latency and costs for repeated queries.
    Supports multi-tenant isolation, configurable TTL, and cache statistics.

    Example:
        cache = PromptCacheService()

        # Check cache before LLM call
        cached_response = await cache.get_cached_response(
            prompt="What is machine learning?",
            model="llama3.2:8b",
            namespace="default"
        )

        if cached_response:
            return cached_response

        # Call LLM...
        response = await llm.generate(prompt)

        # Cache the response
        await cache.cache_response(
            prompt="What is machine learning?",
            model="llama3.2:8b",
            namespace="default",
            response=response,
            ttl=3600  # 1 hour
        )
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        """
        Initialize PromptCacheService.

        Args:
            redis_client: Optional Redis client (creates default from settings if None)

        Example:
            # Use default Redis connection from settings
            cache = PromptCacheService()

            # Use custom Redis client
            custom_redis = redis.from_url("redis://localhost:6379/1")
            cache = PromptCacheService(redis_client=custom_redis)
        """
        self._redis = redis_client or redis.from_url(
            settings.redis_url, decode_responses=True
        )
        self._cache_prefix = "prompt_cache"

        # Statistics tracking (per-instance)
        self._hits = 0
        self._misses = 0

        logger.info("prompt_cache_service_initialized", prefix=self._cache_prefix, redis_url=settings.redis_url)

    def _generate_cache_key(self, namespace: str, model: str, prompt: str) -> str:
        """
        Generate deterministic cache key using SHA256.

        Uses SHA256 hash of prompt to ensure:
        - Deterministic keys (same prompt → same key)
        - Fixed-length keys (regardless of prompt length)
        - Collision-free (extremely low collision probability)

        Key Format: prompt_cache:{namespace}#{model_hash}#{prompt_hash}
        Uses # as separator to avoid conflicts with : in model names (e.g., llama3.2:8b)

        Args:
            namespace: Tenant namespace for isolation
            model: LLM model name (e.g., "llama3.2:8b")
            prompt: Full prompt text

        Returns:
            Cache key: prompt_cache:{namespace}#{model_hash}#{prompt_hash}

        Example:
            key = cache._generate_cache_key(
                namespace="default",
                model="llama3.2:8b",
                prompt="Extract entities from text..."
            )
            # → "prompt_cache:default#a1b2c3d4#e5f6g7h8..."
        """
        # Hash model and prompt to fixed-length deterministic keys
        model_hash = hashlib.sha256(model.encode("utf-8")).hexdigest()[:16]  # First 16 chars for brevity
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

        # Construct key: prefix:namespace#model_hash#prompt_hash
        # Uses # as separator to avoid conflicts with : in model names
        key = f"{self._cache_prefix}:{namespace}#{model_hash}#{prompt_hash}"

        return key

    async def get_cached_response(
        self, prompt: str, model: str, namespace: str = "default"
    ) -> Optional[str]:
        """
        Get cached LLM response from Redis.

        Performs lookup in Redis with tracking of hits/misses for statistics.

        Args:
            prompt: Full prompt text
            model: LLM model name (e.g., "llama3.2:8b")
            namespace: Tenant namespace for isolation (default: "default")

        Returns:
            Cached response string if found, None otherwise

        Example:
            cached = await cache.get_cached_response(
                prompt="What is machine learning?",
                model="llama3.2:8b",
                namespace="default"
            )
            if cached:
                print(f"Cache hit: {cached}")
        """
        cache_key = self._generate_cache_key(namespace, model, prompt)

        try:
            # Attempt Redis lookup
            cached_value = await self._redis.get(cache_key)

            if cached_value:
                # Cache hit
                self._hits += 1
                logger.info(
                    "prompt_cache_hit",
                    namespace=namespace,
                    model=model,
                    key=cache_key,
                    hits=self._hits,
                )
                return cached_value.decode("utf-8") if isinstance(cached_value, bytes) else cached_value

            else:
                # Cache miss
                self._misses += 1
                logger.debug(
                    "prompt_cache_miss",
                    namespace=namespace,
                    model=model,
                    key=cache_key,
                    misses=self._misses,
                )
                return None

        except Exception as e:
            # Redis error → treat as miss and continue
            self._misses += 1
            logger.warning(
                "prompt_cache_lookup_failed",
                namespace=namespace,
                model=model,
                error=str(e),
            )
            return None

    async def cache_response(
        self,
        prompt: str,
        model: str,
        namespace: str,
        response: str,
        ttl: int = 3600,
    ) -> None:
        """
        Cache LLM response in Redis.

        Stores response with configurable TTL for automatic expiration.
        Supports multi-tenant isolation via namespace.

        Args:
            prompt: Full prompt text
            model: LLM model name (e.g., "llama3.2:8b")
            namespace: Tenant namespace for isolation
            response: LLM response text to cache
            ttl: Time-to-live in seconds (default: 3600 = 1 hour)

        Example:
            await cache.cache_response(
                prompt="What is machine learning?",
                model="llama3.2:8b",
                namespace="default",
                response="Machine learning is...",
                ttl=3600  # Cache for 1 hour
            )

        TTL Guidelines:
            - Research queries: 1800 (30 min) - may become stale quickly
            - Extraction queries: 86400 (24 hours) - stable results
            - Chat queries: 3600 (1 hour) - balanced freshness/cache hit
        """
        cache_key = self._generate_cache_key(namespace, model, prompt)

        try:
            # Store in Redis with TTL
            await self._redis.setex(
                name=cache_key,
                time=ttl,
                value=response,
            )

            logger.info(
                "prompt_cached",
                namespace=namespace,
                model=model,
                key=cache_key,
                ttl=ttl,
                response_length=len(response),
            )

        except Exception as e:
            # Redis error → log warning and continue
            logger.warning(
                "prompt_cache_store_failed",
                namespace=namespace,
                model=model,
                error=str(e),
            )

    async def invalidate_namespace(self, namespace: str) -> int:
        """
        Invalidate all cached prompts for a namespace.

        Removes all cache entries for specified namespace without affecting
        other namespaces. Returns count of invalidated entries.

        Args:
            namespace: Namespace to invalidate

        Returns:
            Number of cache entries removed

        Example:
            removed = await cache.invalidate_namespace(namespace="default")
            print(f"Invalidated {removed} cache entries")
        """
        # Pattern: prompt_cache:{namespace}:*
        pattern = f"{self._cache_prefix}:{namespace}:*"

        try:
            # Use SCAN to find and delete keys (safer than KEYS for production)
            cursor = 0
            deleted_count = 0

            while True:
                # SCAN returns (cursor, [keys])
                cursor, keys = await self._redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100,  # Batch size
                )

                # Delete found keys
                if keys:
                    deleted_count += await self._redis.delete(*keys)

                # Continue scanning if cursor != 0
                if cursor == 0:
                    break

            logger.info(
                "namespace_invalidated",
                namespace=namespace,
                deleted_count=deleted_count,
            )

            return deleted_count

        except Exception as e:
            logger.error(
                "namespace_invalidation_failed",
                namespace=namespace,
                error=str(e),
            )
            return 0

    async def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns cache hit/miss statistics and estimated size.

        Returns:
            CacheStats with hits, misses, hit_rate, and total_requests

        Example:
            stats = await cache.get_stats()
            print(f"Hit rate: {stats.hit_rate:.1%}")
            print(f"Total requests: {stats.total_requests}")
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        # Estimate cached size by scanning all prompt_cache keys
        cached_size_bytes = 0
        pattern = f"{self._cache_prefix}:*"

        try:
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100,
                )

                # Get size of each key
                for key in keys:
                    # Redis STRLEN returns length in bytes
                    size = await self._redis.strlen(key)
                    cached_size_bytes += size

                if cursor == 0:
                    break

        except Exception as e:
            logger.warning(
                "cache_size_estimation_failed",
                error=str(e),
            )

        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            hit_rate=hit_rate,
            total_requests=total_requests,
            cached_size_bytes=cached_size_bytes,
        )

    def reset_stats(self) -> None:
        """
        Reset cache statistics.

        Clears in-memory hit/miss counters. Useful for fresh statistics
        after metrics reporting.

        Example:
            stats = await cache.get_stats()
            print(f"Stats: {stats}")
            cache.reset_stats()
        """
        self._hits = 0
        self._misses = 0
        logger.info("cache_stats_reset")


# Singleton instance (lazy initialization)
_cache_instance: PromptCacheService | None = None


async def get_prompt_cache_service() -> PromptCacheService:
    """
    Get singleton instance of PromptCacheService.

    Lazily initializes on first call to avoid Redis connection during imports.

    Returns:
        PromptCacheService instance

    Example:
        cache = await get_prompt_cache_service()
        cached = await cache.get_cached_response(
            prompt="...",
            model="llama3.2:8b"
        )
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = PromptCacheService()

    return _cache_instance
