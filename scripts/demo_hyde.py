#!/usr/bin/env python3
"""Demo script for HyDE (Hypothetical Document Embeddings) Query Expansion.

Sprint 128 Feature 128.4: HyDE Demo

This script demonstrates HyDE functionality:
1. Generate hypothetical documents from queries
2. Search using HyDE embeddings
3. Compare HyDE results with standard dense search
4. Show cache performance

Usage:
    poetry run python scripts/demo_hyde.py
"""

import asyncio
import time

# Mock services for demo (replace with real services in production)
from unittest.mock import AsyncMock, MagicMock, patch


async def demo_hypothetical_generation():
    """Demo: Generate hypothetical documents from queries."""
    print("\n" + "=" * 80)
    print("DEMO 1: Hypothetical Document Generation")
    print("=" * 80)

    # Import HyDE generator
    from src.components.retrieval.hyde import HyDEGenerator

    # Mock LLM proxy for demo
    mock_llm_proxy = MagicMock()
    mock_llm_proxy.generate = AsyncMock()
    mock_llm_proxy.generate.return_value = MagicMock(
        content=(
            "Amsterdam is the capital and most populous city of the Netherlands. "
            "It is known for its artistic heritage, elaborate canal system, "
            "narrow houses with gabled facades, and vibrant cultural scene. "
            "The city has a rich history dating back to the 12th century "
            "and is famous for its museums including the Rijksmuseum and Van Gogh Museum."
        ),
        provider="local_ollama",
        tokens_used=85,
        latency_ms=120.0,
    )

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)  # Cache miss
    mock_redis.setex = AsyncMock()

    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch("src.components.retrieval.hyde.get_embedding_service"),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis

        queries = [
            "What is Amsterdam?",
            "How does climate change affect biodiversity?",
            "Explain quantum computing in simple terms",
        ]

        for query in queries:
            print(f"\n📝 Query: {query}")

            start = time.perf_counter()
            hypothetical_doc = await hyde.generate_hypothetical_document(query)
            latency_ms = (time.perf_counter() - start) * 1000

            print(f"✅ Hypothetical Document ({len(hypothetical_doc)} chars, {latency_ms:.1f}ms):")
            print(f"   {hypothetical_doc}")


async def demo_hyde_search():
    """Demo: Search using HyDE embeddings."""
    print("\n" + "=" * 80)
    print("DEMO 2: HyDE Search")
    print("=" * 80)

    from src.components.retrieval.hyde import HyDEGenerator

    # Mock services
    mock_llm_proxy = MagicMock()
    mock_llm_proxy.generate = AsyncMock(
        return_value=MagicMock(
            content="Amsterdam is the capital of the Netherlands, known for its canals.",
            provider="local_ollama",
            tokens_used=20,
            latency_ms=80.0,
        )
    )

    mock_embedding_service = MagicMock()
    mock_embedding_service.embed_single = AsyncMock(return_value=[0.1] * 1024)

    mock_qdrant = MagicMock()
    mock_qdrant.search = MagicMock(
        return_value=[
            MagicMock(
                id="chunk_1",
                score=0.92,
                payload={
                    "content": "Amsterdam is the capital and largest city of the Netherlands.",
                    "document_id": "doc_amsterdam",
                },
            ),
            MagicMock(
                id="chunk_2",
                score=0.88,
                payload={
                    "content": "The city is famous for its artistic heritage and canal system.",
                    "document_id": "doc_amsterdam",
                },
            ),
        ]
    )

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch(
            "src.components.retrieval.hyde.get_embedding_service",
            return_value=mock_embedding_service,
        ),
        patch("qdrant_client.QdrantClient", return_value=mock_qdrant),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis

        query = "What is Amsterdam?"
        print(f"\n📝 Query: {query}")

        start = time.perf_counter()
        results = await hyde.hyde_search(query, top_k=10)
        latency_ms = (time.perf_counter() - start) * 1000

        print(f"\n✅ HyDE Search Results ({len(results)} results, {latency_ms:.1f}ms):")
        for i, result in enumerate(results, 1):
            print(f"   {i}. [Score: {result['score']:.3f}] {result['content'][:100]}...")


async def demo_cache_performance():
    """Demo: Cache performance for repeated queries."""
    print("\n" + "=" * 80)
    print("DEMO 3: Cache Performance")
    print("=" * 80)

    from src.components.retrieval.hyde import HyDEGenerator

    # Mock services
    hypothetical_doc = "Amsterdam is the capital of the Netherlands, known for its canals."

    mock_llm_proxy = MagicMock()
    mock_llm_proxy.generate = AsyncMock(
        return_value=MagicMock(
            content=hypothetical_doc,
            provider="local_ollama",
            tokens_used=20,
            latency_ms=100.0,
        )
    )

    # Simulate cache hit on second call
    cache_data = {"call_count": 0}

    async def mock_redis_get(key):
        cache_data["call_count"] += 1
        if cache_data["call_count"] == 1:
            return None  # Cache miss
        return hypothetical_doc  # Cache hit

    mock_redis = AsyncMock()
    mock_redis.get = mock_redis_get
    mock_redis.setex = AsyncMock()

    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch("src.components.retrieval.hyde.get_embedding_service"),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis

        query = "What is Amsterdam?"

        # First call - cache miss
        print(f"\n📝 Query (1st call - cache miss): {query}")
        start = time.perf_counter()
        doc1 = await hyde.generate_hypothetical_document(query)
        latency1_ms = (time.perf_counter() - start) * 1000
        print(f"   ⏱️  Latency: {latency1_ms:.1f}ms (LLM generation)")
        print(f"   🔴 Cache status: MISS")

        # Second call - cache hit
        print(f"\n📝 Query (2nd call - cache hit): {query}")
        start = time.perf_counter()
        doc2 = await hyde.generate_hypothetical_document(query)
        latency2_ms = (time.perf_counter() - start) * 1000
        print(f"   ⏱️  Latency: {latency2_ms:.1f}ms (Redis lookup)")
        print(f"   🟢 Cache status: HIT")

        speedup = latency1_ms / latency2_ms if latency2_ms > 0 else 0
        print(f"\n⚡ Speedup: {speedup:.1f}x faster with cache")


async def demo_maximum_hybrid_search():
    """Demo: HyDE integration with Maximum Hybrid Search."""
    print("\n" + "=" * 80)
    print("DEMO 4: HyDE in Maximum Hybrid Search")
    print("=" * 80)

    print(
        """
This demo shows how HyDE integrates into the Maximum Hybrid Search pipeline:

1. Query: "What are the benefits of meditation?"

2. Parallel Signal Execution (5 signals):
   - Qdrant Dense Search       : 10 results (120ms)
   - HyDE Search (NEW)          : 10 results (150ms) ← Hypothetical document
   - BM25 Keyword Search        : 8 results (80ms)
   - Graph Local Search         : 5 entities (200ms)
   - Graph Global Search        : 3 communities (180ms)

3. RRF Fusion:
   - Rankings: [qdrant_chunks, hyde_chunks, bm25_chunks]
   - HyDE weight: 0.5 (configurable via HYDE_WEIGHT)
   - Fused: 25 unique chunks

4. Cross-Modal Fusion:
   - Align entities to chunks via MENTIONED_IN
   - Boost 8 chunks (32% boost rate)

5. Final Results:
   - Top 10 chunks (sorted by fused score)
   - HyDE contributed to 4/10 top results
   - Total latency: 320ms (parallel execution)

6. Metadata:
   - hyde_enabled: true
   - hyde_results_count: 10
   - hypothetical_document: "Meditation is a practice..."
   - hyde_latency_ms: 150.0

Configuration:
   HYDE_ENABLED=true
   HYDE_WEIGHT=0.5
   HYDE_MAX_TOKENS=512
"""
    )


async def main():
    """Run all demos."""
    print("\n🎯 HyDE (Hypothetical Document Embeddings) Demo")
    print("Sprint 128 Feature 128.4\n")

    await demo_hypothetical_generation()
    await demo_hyde_search()
    await demo_cache_performance()
    await demo_maximum_hybrid_search()

    print("\n" + "=" * 80)
    print("✅ Demo Complete!")
    print("=" * 80)
    print(
        """
Next Steps:
1. Enable HyDE in .env: HYDE_ENABLED=true
2. Configure weight: HYDE_WEIGHT=0.5 (0.0-1.0)
3. Monitor cache hit rate: Should be >90% in production
4. Adjust for query types: Disable for keyword-heavy queries

Documentation:
- User Guide: docs/features/HYDE_QUERY_EXPANSION.md
- Implementation: src/components/retrieval/hyde.py
- Tests: tests/unit/components/retrieval/test_hyde.py
"""
    )


if __name__ == "__main__":
    asyncio.run(main())
