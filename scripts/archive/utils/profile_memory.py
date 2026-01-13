"""Memory Profiling Script for RAG Pipeline.

Sprint 68 Feature 68.2: Performance Profiling & Bottleneck Analysis

This script profiles memory usage across the RAG pipeline to identify:
- Memory leaks in long-running processes
- Large object allocations (>100MB)
- Unnecessary data copying
- Peak memory usage per stage

Usage:
    python scripts/profile_memory.py --query "What is the project architecture?"
    python scripts/profile_memory.py --iterations 50  # Leak detection
    python scripts/profile_memory.py --snapshot  # Take memory snapshot

Output:
    - Peak memory usage per stage
    - Top memory allocations
    - Memory leak detection
    - Recommendations for optimization
"""

import argparse
import asyncio
import gc
import linecache
import os
import sys
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
import structlog

logger = structlog.get_logger(__name__)

# Sample queries for memory profiling
SAMPLE_QUERIES = [
    "What is OMNITRACKER?",
    "How does the authentication system work?",
    "Explain the vector search implementation",
    "Summarize the project architecture",
]


class MemoryProfiler:
    """Memory profiler for RAG pipeline."""

    def __init__(self):
        """Initialize memory profiler."""
        self.process = psutil.Process(os.getpid())
        self.baseline_memory_mb = 0
        self.snapshots: list[tuple[str, Any]] = []

    def get_memory_usage_mb(self) -> float:
        """Get current process memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def display_top(self, snapshot: Any, key_type: str = "lineno", limit: int = 10) -> str:
        """Display top memory allocations from tracemalloc snapshot."""
        snapshot = snapshot.filter_traces(
            (
                tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
                tracemalloc.Filter(False, "<unknown>"),
            )
        )
        top_stats = snapshot.statistics(key_type)

        output = f"\nTop {limit} memory allocations:\n"
        for index, stat in enumerate(top_stats[:limit], 1):
            frame = stat.traceback[0]
            output += f"#{index}: {frame.filename}:{frame.lineno}: {stat.size / 1024:.1f} KiB\n"
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                output += f"    {line}\n"

        total = sum(stat.size for stat in top_stats)
        output += f"\nTotal allocated size: {total / 1024 / 1024:.1f} MiB\n"

        return output

    async def profile_stage_memory(
        self, stage_name: str, coro: Any
    ) -> dict[str, Any]:
        """Profile memory usage for a single stage.

        Args:
            stage_name: Name of the stage
            coro: Async coroutine to profile

        Returns:
            Memory profiling results
        """
        # Force garbage collection before measuring
        gc.collect()

        # Measure baseline
        mem_before = self.get_memory_usage_mb()

        # Run stage
        result = await coro

        # Force garbage collection after
        gc.collect()

        # Measure after
        mem_after = self.get_memory_usage_mb()

        memory_delta = mem_after - mem_before

        return {
            "stage": stage_name,
            "memory_before_mb": mem_before,
            "memory_after_mb": mem_after,
            "memory_delta_mb": memory_delta,
            "status": "PASS" if memory_delta < 100 else "WARN",  # <100MB per stage
        }

    async def profile_pipeline_memory(self, query: str) -> dict[str, Any]:
        """Profile memory usage for full pipeline."""
        from src.agents.coordinator import get_coordinator

        logger.info("profiling_memory", query=query[:50])

        # Start tracemalloc
        tracemalloc.start()

        # Force initial garbage collection
        gc.collect()
        self.baseline_memory_mb = self.get_memory_usage_mb()

        stages = []

        # Stage 1: Intent Classification
        from src.components.retrieval.intent_classifier import classify_intent

        stage1 = await self.profile_stage_memory(
            "intent_classification", classify_intent(query)
        )
        stages.append(stage1)

        # Stage 2: Retrieval
        from src.components.retrieval.four_way_hybrid_search import four_way_search

        stage2 = await self.profile_stage_memory(
            "retrieval", four_way_search(query=query, top_k=20, use_reranking=False)
        )
        stages.append(stage2)

        # Stage 3: Reranking
        search_result = await four_way_search(query=query, top_k=20, use_reranking=False)
        documents = search_result["results"]

        from src.components.retrieval.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker(use_adaptive_weights=True)

        async def rerank_stage():
            return await reranker.rerank(query=query, documents=documents, top_k=10)

        stage3 = await self.profile_stage_memory("reranking", rerank_stage())
        stages.append(stage3)

        # Stage 4: Generation
        coordinator = get_coordinator()

        async def generation_stage():
            return await coordinator.process_query(query=query, session_id=None)

        stage4 = await self.profile_stage_memory("generation", generation_stage())
        stages.append(stage4)

        # Take final snapshot
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append((f"query_{len(self.snapshots)}", snapshot))

        # Get top allocations
        top_allocations = self.display_top(snapshot, limit=10)

        # Stop tracemalloc
        tracemalloc.stop()

        # Calculate totals
        peak_memory_mb = max(s["memory_after_mb"] for s in stages)
        total_delta_mb = peak_memory_mb - self.baseline_memory_mb

        result = {
            "query": query,
            "baseline_memory_mb": self.baseline_memory_mb,
            "peak_memory_mb": peak_memory_mb,
            "total_delta_mb": total_delta_mb,
            "target_delta_mb": 512,  # <512MB per request
            "status": "PASS" if total_delta_mb < 512 else "FAIL",
            "stages": stages,
            "top_allocations": top_allocations,
        }

        logger.info(
            "memory_profiled",
            query=query[:50],
            peak_mb=peak_memory_mb,
            delta_mb=total_delta_mb,
            status=result["status"],
        )

        return result

    async def detect_memory_leaks(self, iterations: int = 50) -> dict[str, Any]:
        """Detect memory leaks by running multiple iterations.

        A memory leak is suspected if memory usage grows linearly
        with the number of iterations.
        """
        from src.agents.coordinator import get_coordinator

        logger.info("detecting_memory_leaks", iterations=iterations)

        coordinator = get_coordinator()

        # Track memory over iterations
        memory_samples = []

        for i in range(iterations):
            gc.collect()
            mem_before = self.get_memory_usage_mb()

            # Run a query
            query = SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)]
            await coordinator.process_query(query=query, session_id=f"leak_test_{i}")

            gc.collect()
            mem_after = self.get_memory_usage_mb()

            memory_samples.append(
                {
                    "iteration": i,
                    "query": query,
                    "memory_mb": mem_after,
                    "delta_mb": mem_after - mem_before,
                }
            )

            if i % 10 == 0:
                print(f"Iteration {i}/{iterations}: {mem_after:.1f} MB")

        # Analyze trend
        # Linear regression: memory = a * iteration + b
        # If a > 1.0, we have a leak (>1MB per iteration)

        # Simple linear regression
        n = len(memory_samples)
        sum_x = sum(s["iteration"] for s in memory_samples)
        sum_y = sum(s["memory_mb"] for s in memory_samples)
        sum_xy = sum(s["iteration"] * s["memory_mb"] for s in memory_samples)
        sum_x2 = sum(s["iteration"] ** 2 for s in memory_samples)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
        intercept = (sum_y - slope * sum_x) / n

        leak_detected = slope > 1.0  # >1MB per iteration is a leak

        return {
            "iterations": iterations,
            "slope_mb_per_iteration": slope,
            "intercept_mb": intercept,
            "leak_detected": leak_detected,
            "initial_memory_mb": memory_samples[0]["memory_mb"],
            "final_memory_mb": memory_samples[-1]["memory_mb"],
            "total_growth_mb": memory_samples[-1]["memory_mb"]
            - memory_samples[0]["memory_mb"],
            "samples": memory_samples,
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Profile RAG pipeline memory usage")
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Single query to profile (default: use sample query)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Number of iterations for leak detection (default: 50)",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Take detailed memory snapshot",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for results",
    )

    args = parser.parse_args()

    profiler = MemoryProfiler()

    if args.iterations:
        # Memory leak detection
        print(f"\n{'='*80}")
        print(f"Memory Leak Detection: {args.iterations} iterations")
        print(f"{'='*80}\n")

        result = await profiler.detect_memory_leaks(iterations=args.iterations)

        print(f"\n{'='*80}")
        print("Leak Detection Results")
        print(f"{'='*80}")
        print(f"Initial Memory:    {result['initial_memory_mb']:.1f} MB")
        print(f"Final Memory:      {result['final_memory_mb']:.1f} MB")
        print(f"Total Growth:      {result['total_growth_mb']:.1f} MB")
        print(
            f"Growth Rate:       {result['slope_mb_per_iteration']:.3f} MB/iteration"
        )
        print(f"Leak Detected:     {result['leak_detected']}")

        if result["leak_detected"]:
            print(
                "\nWARNING: Memory leak detected! Memory grows at "
                f"{result['slope_mb_per_iteration']:.2f} MB per iteration."
            )
        else:
            print("\nNo significant memory leak detected.")

        if args.output:
            import json

            output_path = Path(args.output)
            output_path.write_text(json.dumps(result, indent=2))
            print(f"\nResults saved to: {output_path}")

    else:
        # Single query profiling
        query = args.query or SAMPLE_QUERIES[0]

        print(f"\n{'='*80}")
        print(f"Memory Profiling: {query}")
        print(f"{'='*80}\n")

        result = await profiler.profile_pipeline_memory(query)

        print(f"Baseline Memory:  {result['baseline_memory_mb']:.2f} MB")
        print(f"Peak Memory:      {result['peak_memory_mb']:.2f} MB")
        print(f"Total Delta:      {result['total_delta_mb']:.2f} MB")
        print(f"Target Delta:     {result['target_delta_mb']} MB")
        print(f"Status:           {result['status']}")

        print(f"\nStage Breakdown:")
        for stage in result["stages"]:
            print(
                f"  {stage['stage']:20s}: {stage['memory_delta_mb']:+7.2f} MB "
                f"(peak: {stage['memory_after_mb']:.1f} MB) [{stage['status']}]"
            )

        if args.snapshot:
            print(result["top_allocations"])

        if args.output:
            import json

            output_path = Path(args.output)
            # Don't include top_allocations in JSON (it's a string)
            output_result = {k: v for k, v in result.items() if k != "top_allocations"}
            output_path.write_text(json.dumps(output_result, indent=2))
            print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
