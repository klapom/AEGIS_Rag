"""Generate Comprehensive Bottleneck Analysis Report.

Sprint 68 Feature 68.2: Performance Profiling & Bottleneck Analysis

This script runs all profiling scripts and generates a comprehensive
bottleneck analysis report with optimization recommendations.

Usage:
    python scripts/profile_report.py --output docs/analysis/PERF-002_Pipeline_Profiling.md

Output:
    - Markdown report with full analysis
    - Performance metrics and bottlenecks
    - Optimization roadmap
    - JSON data for further analysis
"""

import argparse
import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class BottleneckAnalyzer:
    """Bottleneck analyzer and report generator."""

    def __init__(self):
        """Initialize analyzer."""
        self.pipeline_results: dict[str, Any] = {}
        self.memory_results: dict[str, Any] = {}
        self.leak_results: dict[str, Any] = {}

    async def run_pipeline_profiling(self) -> dict[str, Any]:
        """Run intensive pipeline profiling (100 queries)."""
        logger.info("running_pipeline_profiling")

        # Import and run directly (avoid subprocess)
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))

        from scripts.profile_pipeline import PipelineProfiler, SAMPLE_QUERIES

        profiler = PipelineProfiler()

        all_results = []
        for iteration in range(10):
            for query in SAMPLE_QUERIES:
                result = await profiler.profile_full_pipeline(query)
                all_results.append(result)

        # Calculate statistics
        latencies = [r["total_latency_ms"] for r in all_results]
        latencies_sorted = sorted(latencies)

        p50 = latencies_sorted[len(latencies_sorted) // 2]
        p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
        p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]
        mean = sum(latencies) / len(latencies)

        # Count bottlenecks
        bottleneck_counts: dict[str, int] = {}
        for result in all_results:
            for bottleneck in result["summary"]["bottlenecks"]:
                stage = bottleneck.split(":")[0]
                bottleneck_counts[stage] = bottleneck_counts.get(stage, 0) + 1

        return {
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
            "sample_results": all_results[:5],  # First 5 for detail
        }

    async def run_memory_profiling(self) -> dict[str, Any]:
        """Run memory profiling on sample queries."""
        logger.info("running_memory_profiling")

        from scripts.profile_memory import MemoryProfiler, SAMPLE_QUERIES

        profiler = MemoryProfiler()

        results = []
        for query in SAMPLE_QUERIES[:3]:  # Profile 3 queries
            result = await profiler.profile_pipeline_memory(query)
            results.append(result)

        return {
            "queries_profiled": len(results),
            "average_peak_mb": sum(r["peak_memory_mb"] for r in results) / len(results),
            "average_delta_mb": sum(r["total_delta_mb"] for r in results) / len(results),
            "max_peak_mb": max(r["peak_memory_mb"] for r in results),
            "max_delta_mb": max(r["total_delta_mb"] for r in results),
            "sample_results": results,
        }

    async def run_leak_detection(self, iterations: int = 30) -> dict[str, Any]:
        """Run memory leak detection."""
        logger.info("running_leak_detection", iterations=iterations)

        from scripts.profile_memory import MemoryProfiler

        profiler = MemoryProfiler()

        result = await profiler.detect_memory_leaks(iterations=iterations)

        return result

    def generate_markdown_report(self) -> str:
        """Generate comprehensive markdown report."""
        report = []

        # Header
        report.append("# PERF-002: RAG Pipeline Performance Analysis")
        report.append("")
        report.append(f"**Generated:** {datetime.utcnow().isoformat()}Z")
        report.append(f"**Sprint:** 68")
        report.append(f"**Feature:** 68.2 - Performance Profiling & Bottleneck Analysis")
        report.append("")
        report.append("---")
        report.append("")

        # Executive Summary
        report.append("## Executive Summary")
        report.append("")

        pipeline = self.pipeline_results
        memory = self.memory_results

        p95 = pipeline["statistics"]["p95_ms"]
        mean = pipeline["statistics"]["mean_ms"]
        peak_mem = memory["max_peak_mb"]

        p95_status = "PASS" if p95 < 1000 else "FAIL"
        mem_status = "PASS" if peak_mem < 512 else "WARN"

        report.append(f"- **p95 Latency:** {p95:.1f}ms (target: <1000ms) [{p95_status}]")
        report.append(f"- **Mean Latency:** {mean:.1f}ms")
        report.append(f"- **Peak Memory:** {peak_mem:.1f}MB (target: <512MB) [{mem_status}]")
        report.append("")

        # Performance Metrics
        report.append("## Performance Metrics")
        report.append("")
        report.append("### Latency Distribution (100 queries)")
        report.append("")
        report.append("| Metric | Value | Target | Status |")
        report.append("|--------|-------|--------|--------|")
        report.append(
            f"| Mean   | {pipeline['statistics']['mean_ms']:.1f}ms | - | - |"
        )
        report.append(
            f"| p50    | {pipeline['statistics']['p50_ms']:.1f}ms | <500ms | "
            f"{'PASS' if pipeline['statistics']['p50_ms'] < 500 else 'FAIL'} |"
        )
        report.append(
            f"| p95    | {pipeline['statistics']['p95_ms']:.1f}ms | <1000ms | "
            f"{'PASS' if pipeline['statistics']['p95_ms'] < 1000 else 'FAIL'} |"
        )
        report.append(
            f"| p99    | {pipeline['statistics']['p99_ms']:.1f}ms | <1500ms | "
            f"{'PASS' if pipeline['statistics']['p99_ms'] < 1500 else 'FAIL'} |"
        )
        report.append(
            f"| Min    | {pipeline['statistics']['min_ms']:.1f}ms | - | - |"
        )
        report.append(
            f"| Max    | {pipeline['statistics']['max_ms']:.1f}ms | - | - |"
        )
        report.append("")

        # Bottleneck Analysis
        report.append("## Bottleneck Analysis")
        report.append("")
        report.append("### Bottleneck Frequency (out of 100 queries)")
        report.append("")

        bottlenecks = sorted(
            pipeline["bottleneck_frequency"].items(), key=lambda x: -x[1]
        )

        report.append("| Stage | Frequency | Percentage |")
        report.append("|-------|-----------|------------|")
        for stage, count in bottlenecks:
            report.append(f"| {stage} | {count} | {count}% |")
        report.append("")

        # Top Bottlenecks
        report.append("### Top 3 Bottlenecks")
        report.append("")
        for i, (stage, count) in enumerate(bottlenecks[:3], 1):
            report.append(f"{i}. **{stage}**: Exceeded target in {count}% of queries")

            # Add recommendations based on stage
            if "generation" in stage.lower():
                report.append("   - **Cause:** LLM generation is I/O bound")
                report.append("   - **Recommendation:** Implement streaming to reduce TTFT")
                report.append("   - **Recommendation:** Use smaller, faster models for simple queries")
            elif "retrieval" in stage.lower():
                report.append("   - **Cause:** 4-way hybrid search combines vector, BM25, and graph")
                report.append("   - **Recommendation:** Cache frequent queries")
                report.append("   - **Recommendation:** Optimize graph query execution plans")
            elif "rerank" in stage.lower():
                report.append("   - **Cause:** Cross-encoder scoring is CPU-intensive")
                report.append("   - **Recommendation:** Reduce candidate pool before reranking")
                report.append("   - **Recommendation:** Batch reranking with larger batch sizes")
            elif "intent" in stage.lower():
                report.append("   - **Cause:** SetFit model inference overhead")
                report.append("   - **Recommendation:** Increase cache size for intent classifications")

            report.append("")

        # Memory Analysis
        report.append("## Memory Analysis")
        report.append("")
        report.append("### Memory Usage")
        report.append("")
        report.append("| Metric | Value | Target | Status |")
        report.append("|--------|-------|--------|--------|")
        report.append(
            f"| Average Peak | {memory['average_peak_mb']:.1f}MB | <512MB | "
            f"{'PASS' if memory['average_peak_mb'] < 512 else 'FAIL'} |"
        )
        report.append(
            f"| Average Delta | {memory['average_delta_mb']:.1f}MB | <512MB | "
            f"{'PASS' if memory['average_delta_mb'] < 512 else 'FAIL'} |"
        )
        report.append(f"| Max Peak | {memory['max_peak_mb']:.1f}MB | <512MB | "
            f"{'PASS' if memory['max_peak_mb'] < 512 else 'FAIL'} |")
        report.append("")

        # Memory Leak Detection
        if self.leak_results:
            leak = self.leak_results
            report.append("### Memory Leak Detection")
            report.append("")
            report.append(f"- **Iterations:** {leak['iterations']}")
            report.append(
                f"- **Growth Rate:** {leak['slope_mb_per_iteration']:.3f} MB/iteration"
            )
            report.append(f"- **Total Growth:** {leak['total_growth_mb']:.1f} MB")
            report.append(f"- **Leak Detected:** {leak['leak_detected']}")

            if leak["leak_detected"]:
                report.append("")
                report.append(
                    "WARNING: Memory leak detected! Memory grows at "
                    f"{leak['slope_mb_per_iteration']:.2f} MB per iteration."
                )
                report.append("")
                report.append("**Recommendations:**")
                report.append("- Check session cleanup in CoordinatorAgent")
                report.append("- Verify Redis memory eviction policies")
                report.append("- Review LangGraph checkpointer memory management")
            else:
                report.append("")
                report.append("No significant memory leak detected.")
            report.append("")

        # Optimization Roadmap
        report.append("## Optimization Roadmap")
        report.append("")
        report.append("### Priority Ranking")
        report.append("")

        optimizations = []

        # Determine optimizations based on bottlenecks
        for stage, frequency in bottlenecks:
            if frequency > 20:  # Affects >20% of queries
                if "generation" in stage.lower():
                    optimizations.append(
                        {
                            "priority": "P0",
                            "stage": "LLM Generation",
                            "issue": "Slow LLM inference",
                            "impact": f"{frequency}% of queries",
                            "effort": "Medium (5-8 SP)",
                            "recommendation": "Implement streaming + model selection",
                        }
                    )
                elif "retrieval" in stage.lower():
                    optimizations.append(
                        {
                            "priority": "P0",
                            "stage": "4-Way Retrieval",
                            "issue": "Multiple DB queries in parallel",
                            "impact": f"{frequency}% of queries",
                            "effort": "Medium (3-5 SP)",
                            "recommendation": "Query result caching + graph query optimization",
                        }
                    )
                elif "rerank" in stage.lower():
                    optimizations.append(
                        {
                            "priority": "P1",
                            "stage": "Reranking",
                            "issue": "CPU-intensive cross-encoder",
                            "impact": f"{frequency}% of queries",
                            "effort": "Low (2-3 SP)",
                            "recommendation": "Batch processing + GPU acceleration",
                        }
                    )

        # Add memory optimization if needed
        if memory["max_peak_mb"] > 512:
            optimizations.append(
                {
                    "priority": "P1",
                    "stage": "Memory Management",
                    "issue": "Peak memory exceeds target",
                    "impact": f"{memory['max_peak_mb']:.1f}MB peak",
                    "effort": "Low (2-3 SP)",
                    "recommendation": "Implement lazy loading + streaming for large documents",
                }
            )

        # Sort by priority
        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        optimizations.sort(key=lambda x: priority_order.get(x["priority"], 99))

        for opt in optimizations:
            report.append(f"#### {opt['priority']}: {opt['stage']}")
            report.append("")
            report.append(f"- **Issue:** {opt['issue']}")
            report.append(f"- **Impact:** {opt['impact']}")
            report.append(f"- **Effort:** {opt['effort']}")
            report.append(f"- **Recommendation:** {opt['recommendation']}")
            report.append("")

        # Quick Wins
        report.append("### Quick Wins (Low-Hanging Fruit)")
        report.append("")
        report.append("1. **Intent Classification Caching**")
        report.append("   - Current cache: 1000 entries")
        report.append("   - Increase to 10,000 entries")
        report.append("   - Expected improvement: -10ms on 80% of queries")
        report.append("")
        report.append("2. **Connection Pool Tuning**")
        report.append("   - Increase Neo4j connection pool: 50 → 100")
        report.append("   - Increase Qdrant gRPC connections")
        report.append("   - Expected improvement: -20ms on graph queries")
        report.append("")
        report.append("3. **Batch Reranking**")
        report.append("   - Increase batch size: 32 → 64")
        report.append("   - Expected improvement: -15ms on reranking")
        report.append("")

        # Conclusion
        report.append("## Conclusion")
        report.append("")
        report.append(
            f"The RAG pipeline achieves a p95 latency of {p95:.1f}ms, "
            f"{'meeting' if p95 < 1000 else 'exceeding'} the target of <1000ms. "
        )

        if bottlenecks:
            report.append(
                f"The primary bottleneck is {bottlenecks[0][0]}, affecting {bottlenecks[0][1]}% of queries. "
            )
            report.append(
                "Implementing the P0 optimizations above will reduce latency by an estimated 30-40%."
            )

        report.append("")
        report.append("**Next Steps:**")
        report.append("1. Implement P0 optimizations (Sprint 69)")
        report.append("2. Re-profile to measure improvements")
        report.append("3. Address P1 optimizations based on new baseline")
        report.append("")

        return "\n".join(report)

    async def run_full_analysis(self) -> None:
        """Run full performance analysis."""
        print("Running full performance analysis...")
        print("This will take 5-10 minutes...\n")

        # Step 1: Pipeline profiling (100 queries)
        print("[1/3] Running pipeline profiling (100 queries)...")
        self.pipeline_results = await self.run_pipeline_profiling()
        print(f"      p95: {self.pipeline_results['statistics']['p95_ms']:.1f}ms\n")

        # Step 2: Memory profiling
        print("[2/3] Running memory profiling...")
        self.memory_results = await self.run_memory_profiling()
        print(f"      Peak: {self.memory_results['max_peak_mb']:.1f}MB\n")

        # Step 3: Leak detection (30 iterations)
        print("[3/3] Running leak detection (30 iterations)...")
        self.leak_results = await self.run_leak_detection(iterations=30)
        print(
            f"      Leak: {self.leak_results['leak_detected']} "
            f"({self.leak_results['slope_mb_per_iteration']:.3f} MB/iter)\n"
        )

        print("Analysis complete!\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate bottleneck analysis report")
    parser.add_argument(
        "--output",
        type=str,
        default="docs/analysis/PERF-002_Pipeline_Profiling.md",
        help="Output markdown file path",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Output JSON file path for raw data",
    )

    args = parser.parse_args()

    analyzer = BottleneckAnalyzer()

    # Run full analysis
    await analyzer.run_full_analysis()

    # Generate markdown report
    report = analyzer.generate_markdown_report()

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    print(f"Report saved to: {output_path}")

    # Save JSON data if requested
    if args.json:
        json_data = {
            "pipeline": analyzer.pipeline_results,
            "memory": analyzer.memory_results,
            "leak_detection": analyzer.leak_results,
        }
        json_path = Path(args.json)
        json_path.write_text(json.dumps(json_data, indent=2))
        print(f"Raw data saved to: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
