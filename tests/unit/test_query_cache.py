"""Unit tests for query caching (Sprint 68 Feature 68.4).

Tests the two-tier caching strategy:
1. Exact match cache
2. Semantic cache
"""

import pytest

from src.components.retrieval.query_cache import QueryCache


class TestQueryCache:
    """Test QueryCache functionality."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance for each test."""
        return QueryCache(ttl_seconds=60)

    def test_normalize_query(self, cache):
        """Test query normalization."""
        # Lowercase
        assert cache.normalize_query("WHAT IS AEGIS RAG?") == "what is aegis rag"

        # Extra whitespace
        assert cache.normalize_query("what  is   aegis") == "what is aegis"

        # Punctuation (except ?)
        assert cache.normalize_query("What is AEGIS RAG?!") == "what is aegis rag"

        # Leading/trailing whitespace
        assert cache.normalize_query("  what is aegis  ") == "what is aegis"

    @pytest.mark.asyncio
    async def test_exact_cache_hit(self, cache):
        """Test exact match cache hit."""
        # Store result
        query = "What is AEGIS RAG?"
        results = [{"id": "1", "text": "AEGIS is a RAG system"}]
        metadata = {"intent": "vector", "latency_ms": 100}

        await cache.set(query, results, metadata, namespaces=["default"])

        # Retrieve (should hit exact cache)
        cached = await cache.get(query, namespaces=["default"])

        assert cached is not None
        assert cached["results"] == results
        assert cached["metadata"] == metadata
        assert cached["cache_hit"] == "exact"

        # Check stats
        assert cache.hits_exact == 1
        assert cache.hits_semantic == 0
        assert cache.misses == 0
        assert cache.hit_rate == 1.0

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss."""
        # Query without storing
        cached = await cache.get("What is AEGIS RAG?", namespaces=["default"])

        assert cached is None
        assert cache.misses == 1
        assert cache.hit_rate == 0.0

    @pytest.mark.asyncio
    async def test_normalized_exact_match(self, cache):
        """Test that different capitalizations hit the same cache entry."""
        # Store with one capitalization
        await cache.set(
            "What is AEGIS RAG?",
            [{"id": "1", "text": "AEGIS is a RAG system"}],
            {"intent": "vector"},
            namespaces=["default"],
        )

        # Retrieve with different capitalization
        cached = await cache.get("what is aegis rag?", namespaces=["default"])

        assert cached is not None
        assert cached["cache_hit"] == "exact"

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, cache):
        """Test that namespaces are isolated."""
        # Store in namespace "default"
        await cache.set(
            "What is AEGIS RAG?",
            [{"id": "1", "text": "AEGIS is a RAG system"}],
            {"intent": "vector"},
            namespaces=["default"],
        )

        # Query in namespace "general" (should miss)
        cached = await cache.get("What is AEGIS RAG?", namespaces=["general"])

        assert cached is None
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache):
        """Test cache statistics."""
        # Initial stats
        stats = cache.get_stats()
        assert stats["hits_exact"] == 0
        assert stats["hits_semantic"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

        # Store and retrieve
        await cache.set(
            "What is AEGIS RAG?",
            [{"id": "1", "text": "AEGIS"}],
            {"intent": "vector"},
            namespaces=["default"],
        )

        await cache.get("What is AEGIS RAG?", namespaces=["default"])  # Hit
        await cache.get("What is LangGraph?", namespaces=["default"])  # Miss

        # Check updated stats
        stats = cache.get_stats()
        assert stats["hits_exact"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache):
        """Test cache clearing."""
        # Store result
        await cache.set(
            "What is AEGIS RAG?",
            [{"id": "1", "text": "AEGIS"}],
            {"intent": "vector"},
            namespaces=["default"],
        )

        # Clear cache
        cache.clear()

        # Should miss after clear
        cached = await cache.get("What is AEGIS RAG?", namespaces=["default"])
        assert cached is None

        # Stats should be reset
        stats = cache.get_stats()
        assert stats["hits_exact"] == 0
        assert stats["hits_semantic"] == 0
        assert stats["misses"] == 1

    def test_cosine_similarity(self, cache):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]

        # Identical vectors
        assert cache._cosine_similarity(vec1, vec2) == pytest.approx(1.0)

        # Orthogonal vectors
        assert cache._cosine_similarity(vec1, vec3) == pytest.approx(0.0)

        # Partially similar
        vec4 = [0.5, 0.5, 0.0]
        similarity = cache._cosine_similarity(vec1, vec4)
        assert 0 < similarity < 1

    @pytest.mark.asyncio
    async def test_multiple_namespaces(self, cache):
        """Test caching with multiple namespaces."""
        # Store with multiple namespaces
        await cache.set(
            "What is AEGIS RAG?",
            [{"id": "1", "text": "AEGIS"}],
            {"intent": "vector"},
            namespaces=["default", "general"],
        )

        # Should hit with exact same namespaces
        cached = await cache.get("What is AEGIS RAG?", namespaces=["default", "general"])
        assert cached is not None

        # Should hit even if order is different (sorted internally)
        cached = await cache.get("What is AEGIS RAG?", namespaces=["general", "default"])
        assert cached is not None

        # Should miss with different namespaces
        cached = await cache.get("What is AEGIS RAG?", namespaces=["default"])
        assert cached is None
