#!/usr/bin/env python3
"""Example integration of UnifiedTracer with RAG pipeline.

Sprint 67 Feature 67.5: Unified Trace & Telemetry (8 SP)

This script demonstrates how to integrate UnifiedTracer into the RAG pipeline
for comprehensive performance monitoring and quality tracking.

Usage:
    python scripts/trace_telemetry_example.py

Output:
    - Trace events logged to data/traces/example_run.jsonl
    - Metrics aggregated and printed to console

Integration Points:
    1. Intent Classification (45ms)
    2. Query Rewriting (80ms)
    3. Retrieval (180ms)
    4. Reranking (50ms)
    5. Generation (320ms)
"""

import asyncio
import time
from datetime import datetime, timedelta

from src.adaptation import PipelineStage, TraceEvent, UnifiedTracer


async def simulate_rag_pipeline():
    """Simulate a complete RAG pipeline with tracing."""
    print("=" * 70)
    print("UnifiedTracer Integration Example")
    print("=" * 70)

    # Initialize tracer
    tracer = UnifiedTracer(log_path="data/traces/example_run.jsonl")
    print("\nTracer initialized: data/traces/example_run.jsonl\n")

    # Simulate user query
    query = "What are the new features in OMNITRACKER 2025?"
    request_id = "req_example_001"

    print(f"Query: {query}")
    print(f"Request ID: {request_id}\n")

    # 1. Intent Classification
    print("[1/5] Intent Classification...")
    start = time.perf_counter()
    await asyncio.sleep(0.045)  # Simulate 45ms latency
    latency_ms = (time.perf_counter() - start) * 1000

    await tracer.log_event(
        TraceEvent(
            timestamp=datetime.now(),
            stage=PipelineStage.INTENT_CLASSIFICATION,
            latency_ms=latency_ms,
            metadata={
                "intent": "exploratory",
                "confidence": 0.92,
                "classifier": "llm_trained_setfit",
            },
            request_id=request_id,
        )
    )
    print(f"  -> Completed in {latency_ms:.2f}ms (intent: exploratory, confidence: 0.92)\n")

    # 2. Query Rewriting
    print("[2/5] Query Rewriting...")
    start = time.perf_counter()
    await asyncio.sleep(0.080)  # Simulate 80ms latency
    latency_ms = (time.perf_counter() - start) * 1000

    await tracer.log_event(
        TraceEvent(
            timestamp=datetime.now(),
            stage=PipelineStage.QUERY_REWRITING,
            latency_ms=latency_ms,
            tokens_used=50,
            metadata={
                "original_query": query,
                "rewritten_query": "OMNITRACKER 2025 neue Features Liste Innovationen",
                "model": "qwen2.5:7b",
            },
            request_id=request_id,
        )
    )
    print(f"  -> Completed in {latency_ms:.2f}ms (tokens: 50)\n")

    # 3. Retrieval (4-Way Hybrid)
    print("[3/5] Retrieval (4-Way Hybrid: Vector + BM25 + Graph Local + Graph Global)...")
    start = time.perf_counter()
    await asyncio.sleep(0.180)  # Simulate 180ms latency
    latency_ms = (time.perf_counter() - start) * 1000

    await tracer.log_event(
        TraceEvent(
            timestamp=datetime.now(),
            stage=PipelineStage.RETRIEVAL,
            latency_ms=latency_ms,
            cache_hit=False,
            metadata={
                "top_k": 10,
                "vector_results": 10,
                "bm25_results": 8,
                "graph_local_results": 5,
                "graph_global_results": 3,
                "rrf_score": 0.89,
                "intent_weights": {
                    "vector": 0.15,
                    "bm25": 0.05,
                    "local": 0.30,
                    "global": 0.50,
                },
            },
            request_id=request_id,
        )
    )
    print(f"  -> Completed in {latency_ms:.2f}ms (RRF score: 0.89, cache: MISS)\n")

    # 4. Reranking
    print("[4/5] Reranking (Cross-Encoder)...")
    start = time.perf_counter()
    await asyncio.sleep(0.050)  # Simulate 50ms latency
    latency_ms = (time.perf_counter() - start) * 1000

    await tracer.log_event(
        TraceEvent(
            timestamp=datetime.now(),
            stage=PipelineStage.RERANKING,
            latency_ms=latency_ms,
            metadata={
                "model": "bge-reranker-v2-m3",
                "input_count": 10,
                "output_count": 5,
                "top_score": 0.94,
            },
            request_id=request_id,
        )
    )
    print(f"  -> Completed in {latency_ms:.2f}ms (top score: 0.94)\n")

    # 5. Generation
    print("[5/5] Answer Generation...")
    start = time.perf_counter()
    await asyncio.sleep(0.320)  # Simulate 320ms latency
    latency_ms = (time.perf_counter() - start) * 1000

    await tracer.log_event(
        TraceEvent(
            timestamp=datetime.now(),
            stage=PipelineStage.GENERATION,
            latency_ms=latency_ms,
            tokens_used=250,
            metadata={
                "model": "qwen2.5:7b",
                "evidence_chunks": 5,
                "citations": ["c1", "c3", "c7"],
                "citation_coverage": 0.95,
            },
            request_id=request_id,
        )
    )
    print(f"  -> Completed in {latency_ms:.2f}ms (tokens: 250, citations: 3)\n")

    print("=" * 70)
    print("Pipeline Execution Complete")
    print("=" * 70)

    # Aggregate metrics
    print("\nAggregating metrics for last 1 hour...\n")
    now = datetime.now()
    metrics = await tracer.get_metrics((now - timedelta(hours=1), now + timedelta(minutes=1)))

    print("Metrics Summary:")
    print("-" * 70)
    print(f"Total Events:        {metrics['total_events']}")
    print(f"Avg Latency:         {metrics['avg_latency_ms']:.2f}ms")
    print(f"P95 Latency:         {metrics['p95_latency_ms']:.2f}ms")
    print(f"Total Tokens:        {metrics['total_tokens']}")
    print(f"Cache Hit Rate:      {metrics['cache_hit_rate']:.2%}")
    print()

    print("Stage Breakdown:")
    print("-" * 70)
    for stage, data in metrics["stage_breakdown"].items():
        tokens_info = f", tokens: {data['avg_tokens']:.0f}" if data["avg_tokens"] else ""
        print(
            f"  {stage:25s}: {data['count']:2d} events, "
            f"avg: {data['avg_latency_ms']:6.2f}ms{tokens_info}"
        )

    print("\n" + "=" * 70)
    print(f"Trace file: data/traces/example_run.jsonl")
    print("=" * 70)


async def demonstrate_time_range_queries():
    """Demonstrate time-range metrics queries."""
    print("\n\n" + "=" * 70)
    print("Time-Range Queries Example")
    print("=" * 70)

    tracer = UnifiedTracer(log_path="data/traces/example_run.jsonl")

    # Last 5 minutes
    now = datetime.now()
    metrics_5min = await tracer.get_metrics((now - timedelta(minutes=5), now))
    print(f"\nLast 5 minutes: {metrics_5min['total_events']} events")

    # Last hour
    metrics_1hr = await tracer.get_metrics((now - timedelta(hours=1), now))
    print(f"Last 1 hour:    {metrics_1hr['total_events']} events")


async def demonstrate_event_filtering():
    """Demonstrate event filtering by stage."""
    print("\n\n" + "=" * 70)
    print("Event Filtering Example")
    print("=" * 70)

    tracer = UnifiedTracer(log_path="data/traces/example_run.jsonl")

    # Get all retrieval events
    retrieval_events = await tracer.get_events(stage=PipelineStage.RETRIEVAL, limit=10)
    print(f"\nRetrieved {len(retrieval_events)} RETRIEVAL events:")
    for i, event in enumerate(retrieval_events, 1):
        cache_status = "HIT" if event.cache_hit else "MISS"
        rrf_score = event.metadata.get("rrf_score", "N/A")
        print(
            f"  {i}. {event.timestamp.strftime('%H:%M:%S')} - "
            f"{event.latency_ms:.2f}ms, RRF: {rrf_score}, Cache: {cache_status}"
        )

    # Get all generation events
    generation_events = await tracer.get_events(stage=PipelineStage.GENERATION, limit=10)
    print(f"\nRetrieved {len(generation_events)} GENERATION events:")
    for i, event in enumerate(generation_events, 1):
        print(
            f"  {i}. {event.timestamp.strftime('%H:%M:%S')} - "
            f"{event.latency_ms:.2f}ms, Tokens: {event.tokens_used}"
        )


async def main():
    """Run all examples."""
    await simulate_rag_pipeline()
    await demonstrate_time_range_queries()
    await demonstrate_event_filtering()

    print("\n\n" + "=" * 70)
    print("Integration Example Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("  1. Integrate UnifiedTracer into your RAG pipeline")
    print("  2. Add tracer.log_event() calls at key stages")
    print("  3. Use tracer.get_metrics() for monitoring dashboards")
    print("  4. Filter events by stage for component-specific analysis")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
