#!/usr/bin/env python3
"""GPU performance benchmarking for AEGIS RAG.

Sprint 12 Feature 12.11: Measure and document GPU performance metrics.

This script benchmarks:
1. LightRAG entity extraction (llama3.2:3b)
2. Answer generation (llama3.2:8b)
3. GPU utilization metrics

Usage:
    python scripts/benchmark_gpu.py
    python scripts/benchmark_gpu.py --runs 10
    python scripts/benchmark_gpu.py --output results.json

Requirements:
- NVIDIA GPU with CUDA
- Ollama running with GPU support
- docker-compose.yml configured for GPU
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Any

import structlog
import typer

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger(__name__)
app = typer.Typer()


# ============================================================================
# GPU Metrics Collection
# ============================================================================


def get_gpu_metrics() -> dict[str, Any] | None:
    """Get current GPU metrics using nvidia-smi.

    Returns:
        GPU metrics dict or None if nvidia-smi not available
    """
    try:
        import subprocess

        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None

        # Parse nvidia-smi output
        # Format: "name, gpu_util, mem_util, mem_used, mem_total, temp"
        parts = result.stdout.strip().split(", ")

        return {
            "gpu_name": parts[0],
            "gpu_utilization_pct": float(parts[1]),
            "memory_utilization_pct": float(parts[2]),
            "memory_used_mb": int(parts[3]),
            "memory_total_mb": int(parts[4]),
            "temperature_c": int(parts[5]),
            "vram_usage_pct": (int(parts[3]) / int(parts[4])) * 100,
        }

    except Exception as e:
        logger.warning("gpu_metrics_unavailable", error=str(e))
        return None


# ============================================================================
# Entity Extraction Benchmark (LightRAG)
# ============================================================================


async def benchmark_entity_extraction(runs: int = 10) -> dict[str, Any]:
    """Benchmark LightRAG entity extraction (llama3.2:3b).

    Args:
        runs: Number of benchmark runs

    Returns:
        Benchmark results with timing and GPU metrics
    """
    logger.info("benchmark_entity_extraction_start", runs=runs)

    from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async

    wrapper = await get_lightrag_wrapper_async()

    test_text = """
    LangGraph is a powerful framework for building multi-agent systems with LLM orchestration.
    It provides state management, conditional routing, and checkpointing capabilities.
    AEGIS RAG uses LangGraph for coordinating retrieval agents across vector, graph, and memory systems.
    The system supports hybrid search combining semantic similarity with graph traversal.
    """

    times = []
    gpu_metrics_list = []

    for i in range(runs):
        # Capture GPU before
        gpu_before = get_gpu_metrics()

        start = time.time()

        # Run entity extraction
        result = await wrapper.rag.ainsert(test_text)

        elapsed = time.time() - start
        times.append(elapsed)

        # Capture GPU after
        gpu_after = get_gpu_metrics()
        if gpu_after:
            gpu_metrics_list.append(gpu_after)

        logger.debug("run_complete", run=i + 1, time=elapsed)

        # Small delay between runs
        await asyncio.sleep(0.5)

    return {
        "benchmark": "entity_extraction",
        "model": "llama3.2:3b",
        "runs": runs,
        "mean_time_s": mean(times),
        "stdev_s": stdev(times) if len(times) > 1 else 0,
        "min_time_s": min(times),
        "max_time_s": max(times),
        "times": times,
        "gpu_metrics": gpu_metrics_list[-1] if gpu_metrics_list else None,
    }


# ============================================================================
# Answer Generation Benchmark
# ============================================================================


async def benchmark_answer_generation(runs: int = 10) -> dict[str, Any]:
    """Benchmark answer generation (llama3.2:8b).

    Args:
        runs: Number of benchmark runs

    Returns:
        Benchmark results with timing and GPU metrics
    """
    logger.info("benchmark_answer_generation_start", runs=runs)

    from src.agents.answer_generator import get_answer_generator

    generator = get_answer_generator()

    contexts = [
        {"text": "LangGraph provides state management for multi-agent systems.", "source": "doc1"},
        {"text": "AEGIS RAG uses LangGraph for orchestration of retrieval agents.", "source": "doc2"},
        {"text": "The system supports hybrid search across vector and graph databases.", "source": "doc3"},
    ]

    query = "What framework does AEGIS RAG use for orchestration?"

    times = []
    gpu_metrics_list = []
    answer_lengths = []

    for i in range(runs):
        # Capture GPU before
        gpu_before = get_gpu_metrics()

        start = time.time()

        # Generate answer
        answer = await generator.generate_answer(query, contexts)

        elapsed = time.time() - start
        times.append(elapsed)
        answer_lengths.append(len(answer))

        # Capture GPU after
        gpu_after = get_gpu_metrics()
        if gpu_after:
            gpu_metrics_list.append(gpu_after)

        logger.debug("run_complete", run=i + 1, time=elapsed, answer_length=len(answer))

        # Small delay between runs
        await asyncio.sleep(0.5)

    return {
        "benchmark": "answer_generation",
        "model": "llama3.2:8b",
        "runs": runs,
        "mean_time_s": mean(times),
        "stdev_s": stdev(times) if len(times) > 1 else 0,
        "min_time_s": min(times),
        "max_time_s": max(times),
        "times": times,
        "mean_answer_length": mean(answer_lengths),
        "gpu_metrics": gpu_metrics_list[-1] if gpu_metrics_list else None,
    }


# ============================================================================
# Main Benchmark Runner
# ============================================================================


@app.command()
def run_benchmarks(
    runs: int = typer.Option(10, help="Number of runs per benchmark"),
    output: Path = typer.Option(Path("benchmark_results.json"), help="Output JSON file"),
):
    """Run all GPU performance benchmarks.

    Sprint 12: Measures entity extraction and answer generation performance.
    """

    async def _run():
        results = {
            "timestamp": datetime.now().isoformat(),
            "runs_per_benchmark": runs,
            "gpu_info": get_gpu_metrics(),
        }

        print("\n=== AEGIS RAG GPU Performance Benchmarks ===\n")

        # Entity Extraction (llama3.2:3b)
        print("Running entity extraction benchmark (llama3.2:3b)...")
        results["entity_extraction"] = await benchmark_entity_extraction(runs=runs)
        print(f"  Mean: {results['entity_extraction']['mean_time_s']:.2f}s")
        print(f"  Std Dev: {results['entity_extraction']['stdev_s']:.2f}s")

        # Answer Generation (llama3.2:8b)
        print("\nRunning answer generation benchmark (llama3.2:8b)...")
        results["answer_generation"] = await benchmark_answer_generation(runs=runs)
        print(f"  Mean: {results['answer_generation']['mean_time_s']:.2f}s")
        print(f"  Std Dev: {results['answer_generation']['stdev_s']:.2f}s")

        # GPU Summary
        if results["gpu_info"]:
            print(f"\n=== GPU Metrics ===")
            print(f"GPU: {results['gpu_info']['gpu_name']}")
            print(f"VRAM Usage: {results['gpu_info']['vram_usage_pct']:.1f}%")
            print(f"Temperature: {results['gpu_info']['temperature_c']}°C")

        # Save results
        with open(output, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ Results saved to {output}")
        return results

    # Run async benchmarks
    asyncio.run(_run())


if __name__ == "__main__":
    app()
