#!/usr/bin/env python3
"""Benchmark query latency for Sprint 68 Feature 68.4.

This script measures P50, P95, and P99 latency for various query types:
- Simple queries (vector only)
- Hybrid queries (vector + BM25 + graph)
- Cached queries (second execution)

Performance Targets:
- Simple Query (Vector Only): <200ms (p95)
- Hybrid Query (Vector + Graph): <500ms (p95)
- Complex Multi-Hop: <1000ms (p95)
- Memory Retrieval: <100ms (p95)

Usage:
    python scripts/benchmark_query_latency.py
    python scripts/benchmark_query_latency.py --iterations 50
    python scripts/benchmark_query_latency.py --query-type hybrid
"""

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass

import structlog

from src.components.retrieval.four_way_hybrid_search import FourWayHybridSearch
from src.components.retrieval.query_cache import get_query_cache

logger = structlog.get_logger(__name__)


@dataclass
class LatencyStats:
    """Latency statistics."""

    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    std_dev_ms: float


# Test queries for benchmarking
SIMPLE_QUERIES = [
    "What is AEGIS RAG?",
    "Explain the architecture",
    "How does vector search work?",
    "What is LangGraph?",
    "Describe the ingestion pipeline",
]

HYBRID_QUERIES = [
    "What is the revenue growth strategy and how does it relate to technical architecture?",
    "Explain the authentication flow and its compliance requirements",
    "How does the system handle multi-tenant data isolation across components?",
    "Describe the relationship between document processing and knowledge graph extraction",
    "What are the performance targets and how are they measured?",
]

COMPLEX_QUERIES = [
    "What is the complete data flow from document upload through retrieval to answer generation?",
    "How do the different agents coordinate to process a complex multi-hop query?",
    "Explain the relationship between vector search, graph reasoning, and memory retrieval",
    "What are all the performance optimization techniques used across the system?",
    "How does the system maintain consistency between Qdrant, Neo4j, and Redis?",
]


async def measure_query_latency(
    search_engine: FourWayHybridSearch,
    query: str,
    use_cache: bool = False,
) -> float:
    """Measure latency for a single query.

    Args:
        search_engine: FourWayHybridSearch instance
        query: Query string
        use_cache: Whether to enable caching

    Returns:
        Latency in milliseconds
    """
    start_time = time.perf_counter()

    result = await search_engine.search(
        query=query,
        top_k=10,
        use_cache=use_cache,
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    return latency_ms


def calculate_stats(latencies: list[float]) -> LatencyStats:
    """Calculate latency statistics.

    Args:
        latencies: List of latency measurements in milliseconds

    Returns:
        LatencyStats object
    """
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    return LatencyStats(
        min_ms=min(sorted_latencies),
        max_ms=max(sorted_latencies),
        mean_ms=statistics.mean(sorted_latencies),
        median_ms=statistics.median(sorted_latencies),
        p50_ms=sorted_latencies[int(n * 0.50)],
        p95_ms=sorted_latencies[int(n * 0.95)],
        p99_ms=sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1],
        std_dev_ms=statistics.stdev(sorted_latencies) if len(sorted_latencies) > 1 else 0.0,
    )


async def benchmark_query_type(
    query_type: str,
    queries: list[str],
    iterations: int = 30,
    use_cache: bool = False,
) -> LatencyStats:
    """Benchmark a specific query type.

    Args:
        query_type: Type of query (simple, hybrid, complex)
        queries: List of queries to test
        iterations: Number of iterations per query
        use_cache: Whether to enable caching

    Returns:
        LatencyStats for this query type
    """
    search_engine = FourWayHybridSearch()
    all_latencies = []

    logger.info(
        "benchmarking_query_type",
        query_type=query_type,
        queries_count=len(queries),
        iterations=iterations,
        use_cache=use_cache,
    )

    for query in queries:
        query_latencies = []

        for i in range(iterations):
            latency_ms = await measure_query_latency(
                search_engine=search_engine,
                query=query,
                use_cache=use_cache,
            )

            query_latencies.append(latency_ms)
            all_latencies.append(latency_ms)

            # Log progress every 10 iterations
            if (i + 1) % 10 == 0:
                logger.debug(
                    "benchmark_progress",
                    query=query[:50],
                    iteration=i + 1,
                    latency_ms=latency_ms,
                )

        # Log stats for this query
        query_stats = calculate_stats(query_latencies)
        logger.info(
            "query_benchmark_complete",
            query=query[:50],
            p50_ms=round(query_stats.p50_ms, 2),
            p95_ms=round(query_stats.p95_ms, 2),
            mean_ms=round(query_stats.mean_ms, 2),
        )

    # Calculate overall stats
    stats = calculate_stats(all_latencies)

    logger.info(
        "query_type_benchmark_complete",
        query_type=query_type,
        total_queries=len(all_latencies),
        p50_ms=round(stats.p50_ms, 2),
        p95_ms=round(stats.p95_ms, 2),
        p99_ms=round(stats.p99_ms, 2),
        mean_ms=round(stats.mean_ms, 2),
    )

    return stats


async def benchmark_cache_performance(iterations: int = 50) -> dict[str, LatencyStats]:
    """Benchmark cache hit vs miss performance.

    Args:
        iterations: Number of iterations

    Returns:
        Dict with cache_miss and cache_hit stats
    """
    search_engine = FourWayHybridSearch()
    cache = get_query_cache()

    # Clear cache first
    cache.clear()

    query = "What is AEGIS RAG?"

    # Measure cache miss latency (first execution)
    miss_latencies = []
    for _ in range(iterations):
        cache.clear()  # Force cache miss
        latency_ms = await measure_query_latency(
            search_engine=search_engine,
            query=query,
            use_cache=True,
        )
        miss_latencies.append(latency_ms)

    # Measure cache hit latency (second execution)
    hit_latencies = []
    cache.clear()
    for _ in range(iterations):
        latency_ms = await measure_query_latency(
            search_engine=search_engine,
            query=query,
            use_cache=True,
        )
        hit_latencies.append(latency_ms)

    miss_stats = calculate_stats(miss_latencies)
    hit_stats = calculate_stats(hit_latencies)

    # Calculate speedup
    speedup = miss_stats.p95_ms / hit_stats.p95_ms if hit_stats.p95_ms > 0 else 0

    logger.info(
        "cache_benchmark_complete",
        cache_miss_p95_ms=round(miss_stats.p95_ms, 2),
        cache_hit_p95_ms=round(hit_stats.p95_ms, 2),
        speedup=round(speedup, 2),
        cache_hit_rate=cache.hit_rate,
    )

    return {
        "cache_miss": miss_stats,
        "cache_hit": hit_stats,
    }


def print_report(results: dict[str, LatencyStats], targets: dict[str, float]) -> None:
    """Print benchmark report.

    Args:
        results: Benchmark results
        targets: Performance targets (p95 ms)
    """
    print("\n" + "=" * 80)
    print("QUERY LATENCY BENCHMARK REPORT")
    print("Sprint 68 Feature 68.4: Query Latency Optimization")
    print("=" * 80)

    for query_type, stats in results.items():
        target_p95 = targets.get(query_type, 500)  # Default: 500ms
        status = "✓ PASS" if stats.p95_ms < target_p95 else "✗ FAIL"

        print(f"\n{query_type.upper()}:")
        print(f"  P50:        {stats.p50_ms:>8.2f} ms")
        print(f"  P95:        {stats.p95_ms:>8.2f} ms  (target: {target_p95} ms)  {status}")
        print(f"  P99:        {stats.p99_ms:>8.2f} ms")
        print(f"  Mean:       {stats.mean_ms:>8.2f} ms")
        print(f"  Std Dev:    {stats.std_dev_ms:>8.2f} ms")
        print(f"  Min:        {stats.min_ms:>8.2f} ms")
        print(f"  Max:        {stats.max_ms:>8.2f} ms")

    print("\n" + "=" * 80)


async def main():
    """Main benchmark entry point."""
    parser = argparse.ArgumentParser(description="Benchmark query latency")
    parser.add_argument(
        "--iterations",
        type=int,
        default=30,
        help="Number of iterations per query (default: 30)",
    )
    parser.add_argument(
        "--query-type",
        choices=["simple", "hybrid", "complex", "cache", "all"],
        default="all",
        help="Query type to benchmark (default: all)",
    )
    args = parser.parse_args()

    results = {}
    targets = {
        "simple": 200,  # Vector only
        "hybrid": 500,  # Vector + Graph
        "complex": 1000,  # Multi-hop
        "cache_miss": 500,
        "cache_hit": 50,
    }

    logger.info(
        "benchmark_starting",
        iterations=args.iterations,
        query_type=args.query_type,
    )

    if args.query_type in ["simple", "all"]:
        results["simple"] = await benchmark_query_type(
            query_type="simple",
            queries=SIMPLE_QUERIES,
            iterations=args.iterations,
            use_cache=False,
        )

    if args.query_type in ["hybrid", "all"]:
        results["hybrid"] = await benchmark_query_type(
            query_type="hybrid",
            queries=HYBRID_QUERIES,
            iterations=args.iterations,
            use_cache=False,
        )

    if args.query_type in ["complex", "all"]:
        results["complex"] = await benchmark_query_type(
            query_type="complex",
            queries=COMPLEX_QUERIES,
            iterations=args.iterations,
            use_cache=False,
        )

    if args.query_type in ["cache", "all"]:
        cache_results = await benchmark_cache_performance(iterations=args.iterations)
        results.update(cache_results)

    # Print report
    print_report(results, targets)

    # Get cache stats
    cache = get_query_cache()
    cache_stats = cache.get_stats()

    print("\nCACHE STATISTICS:")
    print(f"  Hit Rate:         {cache_stats['hit_rate']:.2%}")
    print(f"  Exact Hits:       {cache_stats['hits_exact']}")
    print(f"  Semantic Hits:    {cache_stats['hits_semantic']}")
    print(f"  Misses:           {cache_stats['misses']}")
    print(f"  Cache Size:       {cache_stats['exact_cache_size']} / {cache_stats['exact_cache_maxsize']}")


if __name__ == "__main__":
    asyncio.run(main())
