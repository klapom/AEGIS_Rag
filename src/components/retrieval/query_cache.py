"""Semantic Query Cache for retrieval optimization.

Sprint 68 Feature 68.4: Query Latency Optimization

This module implements a two-tier caching strategy:
1. Exact match cache: Normalized query strings (lowercase, stemmed)
2. Semantic cache: Embed query and find similar queries (cosine similarity > 0.95)

Cache hit rate target: >50%
Expected latency reduction: 50-80% for cached queries
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import structlog
from cachetools import TTLCache

logger = structlog.get_logger(__name__)

# Cache configuration
EXACT_CACHE_SIZE = 1000  # Number of exact query matches
SEMANTIC_CACHE_SIZE = 500  # Number of semantic embeddings
DEFAULT_TTL = 3600  # 1 hour TTL
SEMANTIC_THRESHOLD = 0.95  # Cosine similarity threshold for semantic match


@dataclass
class CachedResult:
    """Cached retrieval result."""

    results: list[dict[str, Any]]
    metadata: dict[str, Any]
    query_normalized: str
    timestamp: float
    hit_count: int = 0


class QueryCache:
    """Two-tier query cache for retrieval optimization.

    Tier 1: Exact match cache (normalized queries)
    Tier 2: Semantic cache (embedding-based similarity)

    Example:
        cache = QueryCache()

        # Try cache first
        cached = await cache.get("What is AEGIS RAG?", namespaces=["default"])
        if cached:
            return cached

        # Execute search
        results = await four_way_search(...)

        # Store in cache
        await cache.set(query, results, namespaces=["default"])
    """

    def __init__(
        self,
        exact_cache_size: int = EXACT_CACHE_SIZE,
        semantic_cache_size: int = SEMANTIC_CACHE_SIZE,
        ttl_seconds: int = DEFAULT_TTL,
        semantic_threshold: float = SEMANTIC_THRESHOLD,
    ):
        """Initialize query cache.

        Args:
            exact_cache_size: Size of exact match cache
            semantic_cache_size: Size of semantic cache
            ttl_seconds: Time-to-live for cache entries
            semantic_threshold: Cosine similarity threshold for semantic matches
        """
        # Tier 1: Exact match cache (normalized query → results)
        self.exact_cache: TTLCache = TTLCache(maxsize=exact_cache_size, ttl=ttl_seconds)

        # Tier 2: Semantic cache (query embedding → results)
        self.semantic_cache: TTLCache = TTLCache(maxsize=semantic_cache_size, ttl=ttl_seconds)

        # Embedding cache (query → embedding vector)
        self.embedding_cache: dict[str, list[float]] = {}

        self.ttl_seconds = ttl_seconds
        self.semantic_threshold = semantic_threshold

        # Metrics
        self.hits_exact = 0
        self.hits_semantic = 0
        self.misses = 0

        logger.info(
            "query_cache_initialized",
            exact_cache_size=exact_cache_size,
            semantic_cache_size=semantic_cache_size,
            ttl_seconds=ttl_seconds,
            semantic_threshold=semantic_threshold,
        )

    def normalize_query(self, query: str) -> str:
        """Normalize query for exact matching.

        Normalization steps:
        1. Lowercase
        2. Remove extra whitespace
        3. Remove punctuation (except question marks)
        4. Strip leading/trailing whitespace

        Args:
            query: Raw query string

        Returns:
            Normalized query string
        """
        # Lowercase
        normalized = query.lower()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Remove most punctuation (keep question marks for intent)
        normalized = re.sub(r"[^\w\s?]", "", normalized)

        # Strip
        normalized = normalized.strip()

        return normalized

    def _build_cache_key(self, query: str, namespaces: list[str] | None = None) -> str:
        """Build cache key from query and namespaces.

        Args:
            query: Normalized query
            namespaces: Namespace list (sorted for consistency)

        Returns:
            Cache key string
        """
        ns_str = ",".join(sorted(namespaces)) if namespaces else "default"
        return f"{query}|{ns_str}"

    async def get(
        self,
        query: str,
        namespaces: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Get cached results for query.

        Tries exact match first, then semantic match.

        Args:
            query: User query
            namespaces: Namespaces to search in

        Returns:
            Cached results dict or None if not found
        """
        # Normalize query
        normalized = self.normalize_query(query)
        cache_key = self._build_cache_key(normalized, namespaces)

        # Tier 1: Exact match
        if cache_key in self.exact_cache:
            cached = self.exact_cache[cache_key]
            cached.hit_count += 1
            self.hits_exact += 1

            logger.info(
                "query_cache_hit_exact",
                query=query[:50],
                namespaces=namespaces,
                hit_count=cached.hit_count,
            )

            return {
                "results": cached.results,
                "metadata": cached.metadata,
                "cache_hit": "exact",
            }

        # Tier 2: Semantic match (if embedding service available)
        semantic_result = await self._semantic_match(query, namespaces)
        if semantic_result:
            self.hits_semantic += 1
            logger.info(
                "query_cache_hit_semantic",
                query=query[:50],
                namespaces=namespaces,
                similarity=semantic_result.get("similarity"),
            )
            return {
                "results": semantic_result["results"],
                "metadata": semantic_result["metadata"],
                "cache_hit": "semantic",
            }

        # Cache miss
        self.misses += 1
        logger.debug(
            "query_cache_miss",
            query=query[:50],
            namespaces=namespaces,
            hit_rate=self.hit_rate,
        )

        return None

    async def set(
        self,
        query: str,
        results: list[dict[str, Any]],
        metadata: dict[str, Any],
        namespaces: list[str] | None = None,
    ) -> None:
        """Store results in cache.

        Args:
            query: User query
            results: Search results
            metadata: Search metadata
            namespaces: Namespaces searched
        """
        import time

        # Normalize query
        normalized = self.normalize_query(query)
        cache_key = self._build_cache_key(normalized, namespaces)

        # Create cached entry
        cached = CachedResult(
            results=results,
            metadata=metadata,
            query_normalized=normalized,
            timestamp=time.time(),
        )

        # Store in exact cache
        self.exact_cache[cache_key] = cached

        # Store embedding in semantic cache
        await self._store_semantic(query, cached, namespaces)

        logger.debug(
            "query_cache_set",
            query=query[:50],
            namespaces=namespaces,
            results_count=len(results),
        )

    async def _semantic_match(
        self,
        query: str,
        namespaces: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Find semantically similar cached query.

        Args:
            query: User query
            namespaces: Namespaces to match

        Returns:
            Cached results if similar query found, else None
        """
        try:
            # Get query embedding
            from src.components.shared.embedding_service import get_embedding_service

            embedding_service = get_embedding_service()
            # Sprint 92 Fix: Handle both list (Ollama/ST) and dict (FlagEmbedding) returns
            embedding_result = await embedding_service.embed_single(query)
            query_embedding = (
                embedding_result["dense"]
                if isinstance(embedding_result, dict)
                else embedding_result
            )

            # Find most similar cached query
            best_similarity = 0.0
            best_cached = None

            for cached_key, cached_entry in self.semantic_cache.items():
                # Check namespace match
                if namespaces:
                    cached_ns = cached_key.split("|")[1] if "|" in cached_key else "default"
                    current_ns = ",".join(sorted(namespaces))
                    if cached_ns != current_ns:
                        continue

                # Compute cosine similarity
                cached_embedding = self.embedding_cache.get(cached_key)
                if not cached_embedding:
                    continue

                similarity = self._cosine_similarity(query_embedding, cached_embedding)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cached = cached_entry

            # Return if above threshold
            if best_similarity >= self.semantic_threshold and best_cached:
                return {
                    "results": best_cached.results,
                    "metadata": best_cached.metadata,
                    "similarity": best_similarity,
                }

            return None

        except Exception as e:
            logger.warning("semantic_cache_lookup_failed", error=str(e))
            return None

    async def _store_semantic(
        self,
        query: str,
        cached: CachedResult,
        namespaces: list[str] | None = None,
    ) -> None:
        """Store query embedding in semantic cache.

        Args:
            query: User query
            cached: Cached result entry
            namespaces: Namespaces
        """
        try:
            # Get query embedding
            from src.components.shared.embedding_service import get_embedding_service

            embedding_service = get_embedding_service()
            # Sprint 92 Fix: Handle both list (Ollama/ST) and dict (FlagEmbedding) returns
            embedding_result = await embedding_service.embed_single(query)
            query_embedding = (
                embedding_result["dense"]
                if isinstance(embedding_result, dict)
                else embedding_result
            )

            # Build cache key
            cache_key = self._build_cache_key(cached.query_normalized, namespaces)

            # Store in semantic cache
            self.semantic_cache[cache_key] = cached
            self.embedding_cache[cache_key] = query_embedding

        except Exception as e:
            logger.warning("semantic_cache_store_failed", error=str(e))

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        import math

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        # Cosine similarity
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate (0-1)
        """
        total = self.hits_exact + self.hits_semantic + self.misses
        if total == 0:
            return 0.0
        return (self.hits_exact + self.hits_semantic) / total

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Stats dict with hit rates and cache sizes
        """
        return {
            "hits_exact": self.hits_exact,
            "hits_semantic": self.hits_semantic,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "exact_cache_size": len(self.exact_cache),
            "semantic_cache_size": len(self.semantic_cache),
            "exact_cache_maxsize": self.exact_cache.maxsize,
            "semantic_cache_maxsize": self.semantic_cache.maxsize,
        }

    def clear(self) -> None:
        """Clear all caches."""
        self.exact_cache.clear()
        self.semantic_cache.clear()
        self.embedding_cache.clear()
        self.hits_exact = 0
        self.hits_semantic = 0
        self.misses = 0
        logger.info("query_cache_cleared")


# Global singleton
_query_cache: QueryCache | None = None


def get_query_cache() -> QueryCache:
    """Get global QueryCache instance (singleton).

    Returns:
        QueryCache instance
    """
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache
