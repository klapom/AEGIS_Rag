"""Full RAG Pipeline Profiling Script.

Sprint 68 Feature 68.2: Performance Profiling & Bottleneck Analysis

This script profiles all 5 stages of the RAG pipeline:
1. Intent Classification (~20-50ms target)
2. Query Rewriting (~80ms target)
3. Retrieval (4-Way Hybrid) (~180ms target)
4. Reranking (~50ms target)
5. Generation (~320ms target)

Usage:
    python scripts/profile_pipeline.py --query "What is the project architecture?"
    python scripts/profile_pipeline.py --mode intensive  # Profile 100 queries
    python scripts/profile_pipeline.py --output profile_results.json

Output:
    - Per-stage timing breakdown
    - Function-level hotspots (cProfile)
    - Bottleneck identification
    - Performance recommendations
"""

import argparse
import asyncio
import cProfile
import json
import pstats
import time
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Sample queries for intensive profiling
SAMPLE_QUERIES = [
    "What is OMNITRACKER?",
    "How does the authentication system work?",
    "JWT_TOKEN error 404",
    "Summarize the project architecture",
    "What are the main features?",
    "Explain the vector search implementation",
    "security policy violations 2024",
    "How do I configure the API?",
    "What is the database schema?",
    "List all available endpoints",
]


class PipelineProfiler:
    """RAG Pipeline Profiler with stage-level timing."""

    def __init__(self):
        """Initialize profiler."""
        self.results: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "stages": {},
            "total": {},
            "queries": [],
        }

    async def profile_stage_1_intent_classification(self, query: str) -> dict[str, Any]:
        """Profile Intent Classification stage.

        Target: ~20-50ms
        """
        from src.components.retrieval.intent_classifier import classify_intent

        start = time.perf_counter()
        result = await classify_intent(query)
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "latency_ms": latency_ms,
            "intent": result.intent.value,
            "confidence": result.confidence,
            "method": result.method,
            "target_ms": 50,
            "status": "PASS" if latency_ms < 50 else "FAIL",
        }

    async def profile_stage_2_query_rewriting(self, query: str) -> dict[str, Any]:
        """Profile Query Rewriting stage.

        Target: ~80ms
        Note: This is optional and not always executed in the pipeline.
        """
        # Query rewriting is typically done via LLM call
        # For now, we'll skip this as it's not a core bottleneck
        # Most queries go directly to retrieval without rewriting

        return {
            "latency_ms": 0,
            "skipped": True,
            "reason": "Query rewriting is optional and LLM-based (~2-10s)",
            "target_ms": 80,
            "status": "SKIPPED",
        }

    async def profile_stage_3_retrieval(
        self, query: str, top_k: int = 10
    ) -> dict[str, Any]:
        """Profile 4-Way Hybrid Retrieval stage.

        Target: ~180ms

        Breakdown:
        - Vector search: ~50-80ms
        - BM25 search: ~30-50ms
        - Graph local: ~40-60ms
        - Graph global: ~40-60ms
        - RRF fusion: ~10ms
        """
        from src.components.retrieval.four_way_hybrid_search import four_way_search

        start = time.perf_counter()
        result = await four_way_search(
            query=query, top_k=top_k, use_reranking=False  # Rerank in next stage
        )
        total_latency_ms = (time.perf_counter() - start) * 1000

        metadata = result["metadata"]

        return {
            "latency_ms": total_latency_ms,
            "intent": metadata.intent,
            "weights": metadata.weights,
            "channels": {
                "vector_count": metadata.vector_results_count,
                "bm25_count": metadata.bm25_results_count,
                "graph_local_count": metadata.graph_local_results_count,
                "graph_global_count": metadata.graph_global_results_count,
            },
            "target_ms": 180,
            "status": "PASS" if total_latency_ms < 180 else "FAIL",
        }

    async def profile_stage_4_reranking(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> dict[str, Any]:
        """Profile Reranking stage.

        Target: ~50ms
        """
        from src.components.retrieval.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker(use_adaptive_weights=True)

        start = time.perf_counter()
        reranked = await reranker.rerank(query=query, documents=documents, top_k=top_k)
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "latency_ms": latency_ms,
            "documents_scored": len(documents),
            "top_k": top_k,
            "adaptive_weights_enabled": True,
            "target_ms": 50,
            "status": "PASS" if latency_ms < 50 else "FAIL",
        }

    async def profile_stage_5_generation(
        self, query: str, contexts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Profile LLM Generation stage.

        Target: ~320ms (without streaming)
        Note: With streaming, TTFT (Time To First Token) is the key metric.
        """
        from src.agents.coordinator import get_coordinator

        coordinator = get_coordinator()

        # Measure non-streaming generation
        start = time.perf_counter()

        # Use process_query directly (not streaming)
        # This gives us the full generation time
        result = await coordinator.process_query(query=query, session_id=None)

        latency_ms = (time.perf_counter() - start) * 1000

        # Extract answer
        answer = result.get("answer", "")
        answer_length = len(answer)

        return {
            "latency_ms": latency_ms,
            "answer_length": answer_length,
            "tokens_estimated": answer_length // 4,  # Rough estimate
            "target_ms": 320,
            "status": "PASS" if latency_ms < 320 else "FAIL",
        }

    async def profile_full_pipeline(self, query: str) -> dict[str, Any]:
        """Profile complete pipeline end-to-end."""
        logger.info("profiling_pipeline", query=query[:50])

        pipeline_start = time.perf_counter()

        # Stage 1: Intent Classification
        stage1_result = await self.profile_stage_1_intent_classification(query)

        # Stage 2: Query Rewriting (skipped)
        stage2_result = await self.profile_stage_2_query_rewriting(query)

        # Stage 3: Retrieval
        stage3_result = await self.profile_stage_3_retrieval(query)

        # Stage 4: Reranking
        # Get documents from retrieval for reranking
        from src.components.retrieval.four_way_hybrid_search import four_way_search

        search_result = await four_way_search(query=query, top_k=20, use_reranking=False)
        documents = search_result["results"]

        stage4_result = await self.profile_stage_4_reranking(query, documents, top_k=10)

        # Stage 5: Generation (full pipeline)
        # This will re-run the entire pipeline, but it's the most realistic measurement
        stage5_result = await self.profile_stage_5_generation(query, documents[:10])

        total_latency_ms = (time.perf_counter() - pipeline_start) * 1000

        result = {
            "query": query,
            "total_latency_ms": total_latency_ms,
            "stages": {
                "1_intent_classification": stage1_result,
                "2_query_rewriting": stage2_result,
                "3_retrieval": stage3_result,
                "4_reranking": stage4_result,
                "5_generation": stage5_result,
            },
            "summary": {
                "total_target_ms": 680,  # Sum of all targets (50+80+180+50+320)
                "status": "PASS" if total_latency_ms < 1000 else "FAIL",  # p95 target
                "bottlenecks": self._identify_bottlenecks(
                    {
                        "intent": stage1_result,
                        "retrieval": stage3_result,
                        "reranking": stage4_result,
                        "generation": stage5_result,
                    }
                ),
            },
        }

        logger.info(
            "pipeline_profiled",
            query=query[:50],
            total_ms=total_latency_ms,
            status=result["summary"]["status"],
        )

        return result

    def _identify_bottlenecks(self, stages: dict[str, dict[str, Any]]) -> list[str]:
        """Identify pipeline bottlenecks.

        A stage is a bottleneck if:
        1. It exceeds its target latency
        2. It contributes >30% of total pipeline time
        """
        bottlenecks = []
        total_ms = sum(s.get("latency_ms", 0) for s in stages.values())

        for name, stage in stages.items():
            latency = stage.get("latency_ms", 0)
            target = stage.get("target_ms", 0)
            percentage = (latency / total_ms * 100) if total_ms > 0 else 0

            if latency > target:
                bottlenecks.append(
                    f"{name}: {latency:.1f}ms (target: {target}ms, {percentage:.1f}% of pipeline)"
                )
            elif percentage > 30:
                bottlenecks.append(
                    f"{name}: {percentage:.1f}% of pipeline time ({latency:.1f}ms)"
                )

        return bottlenecks

    def profile_with_cprofile(self, query: str) -> str:
        """Profile pipeline with cProfile for function-level analysis.

        Returns:
            String with profiling stats
        """
        profiler = cProfile.Profile()
        profiler.enable()

        # Run pipeline
        asyncio.run(self.profile_full_pipeline(query))

        profiler.disable()

        # Generate stats report
        s = StringIO()
        stats = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        stats.print_stats(30)  # Top 30 functions

        return s.getvalue()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Profile RAG pipeline performance")
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Single query to profile (default: use sample query)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["single", "intensive"],
        default="single",
        help="Profiling mode (single query or 100 queries)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for results (JSON format)",
    )
    parser.add_argument(
        "--cprofile",
        action="store_true",
        help="Enable cProfile function-level profiling",
    )

    args = parser.parse_args()

    profiler = PipelineProfiler()

    if args.mode == "single":
        # Profile single query
        query = args.query or SAMPLE_QUERIES[0]

        print(f"\n{'='*80}")
        print(f"Profiling Pipeline: {query}")
        print(f"{'='*80}\n")

        if args.cprofile:
            print("Running with cProfile (function-level profiling)...\n")
            cprofile_output = profiler.profile_with_cprofile(query)
            print(cprofile_output)
        else:
            result = await profiler.profile_full_pipeline(query)

            # Print results
            print(f"Total Latency: {result['total_latency_ms']:.2f}ms")
            print(f"Status: {result['summary']['status']}")
            print(f"\nStage Breakdown:")
            for stage_name, stage_data in result["stages"].items():
                latency = stage_data.get("latency_ms", 0)
                target = stage_data.get("target_ms", 0)
                status = stage_data.get("status", "UNKNOWN")
                print(f"  {stage_name:30s}: {latency:6.2f}ms (target: {target:3d}ms) [{status}]")

            print(f"\nBottlenecks:")
            for bottleneck in result["summary"]["bottlenecks"]:
                print(f"  - {bottleneck}")

            if args.output:
                output_path = Path(args.output)
                output_path.write_text(json.dumps(result, indent=2))
                print(f"\nResults saved to: {output_path}")

    elif args.mode == "intensive":
        # Profile 100 queries (10 sample queries x 10 iterations)
        print(f"\n{'='*80}")
        print("Intensive Profiling: 100 queries")
        print(f"{'='*80}\n")

        all_results = []
        for iteration in range(10):
            for idx, query in enumerate(SAMPLE_QUERIES):
                print(f"[{iteration * 10 + idx + 1}/100] {query[:50]}...", end=" ", flush=True)
                result = await profiler.profile_full_pipeline(query)
                all_results.append(result)
                print(f"{result['total_latency_ms']:.2f}ms [{result['summary']['status']}]")

        # Calculate statistics
        latencies = [r["total_latency_ms"] for r in all_results]
        latencies_sorted = sorted(latencies)

        p50 = latencies_sorted[len(latencies_sorted) // 2]
        p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
        p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]
        mean = sum(latencies) / len(latencies)

        print(f"\n{'='*80}")
        print("Statistics (100 queries)")
        print(f"{'='*80}")
        print(f"Mean:   {mean:.2f}ms")
        print(f"p50:    {p50:.2f}ms (target: <500ms)")
        print(f"p95:    {p95:.2f}ms (target: <1000ms)")
        print(f"p99:    {p99:.2f}ms")
        print(f"Min:    {min(latencies):.2f}ms")
        print(f"Max:    {max(latencies):.2f}ms")

        # Count bottlenecks
        bottleneck_counts: dict[str, int] = {}
        for result in all_results:
            for bottleneck in result["summary"]["bottlenecks"]:
                stage = bottleneck.split(":")[0]
                bottleneck_counts[stage] = bottleneck_counts.get(stage, 0) + 1

        print(f"\nBottleneck Frequency (out of 100 queries):")
        for stage, count in sorted(bottleneck_counts.items(), key=lambda x: -x[1]):
            print(f"  {stage:30s}: {count:3d} times ({count}%)")

        if args.output:
            output_path = Path(args.output)
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "mode": "intensive",
                "total_queries": len(all_results),
                "statistics": {
                    "mean_ms": mean,
                    "p50_ms": p50,
                    "p95_ms": p95,
                    "p99_ms": p99,
                    "min_ms": min(latencies),
                    "max_ms": max(latencies),
                },
                "bottleneck_frequency": bottleneck_counts,
                "all_results": all_results,
            }
            output_path.write_text(json.dumps(summary, indent=2))
            print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
