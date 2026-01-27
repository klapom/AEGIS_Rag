#!/usr/bin/env python3
"""Benchmark for Sprint 121 Section Extraction Parallel Features (TD-078 Phase 2).

This script benchmarks:
1. Tokenizer initialization time (first call vs cached call)
2. Parallel vs sequential tokenization for 50-200 text blocks
3. Speedup factor for parallel tokenization

Sprint 121 Features:
- Feature 121.2a: Tokenizer singleton cache (_get_cached_tokenizer)
- Feature 121.2b: Parallel batch tokenization (_batch_tokenize_parallel)

Usage:
    PYTHONPATH=/home/admin/projects/aegisrag/AEGIS_Rag python3 scripts/benchmark_section_extraction_sprint121.py
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.ingestion.section_extraction import (
    _get_cached_tokenizer,
    _batch_tokenize_parallel,
    reset_profiling_stats,
)


def benchmark_tokenizer_caching():
    """Benchmark tokenizer initialization (first call vs cached call)."""
    print("\n" + "=" * 80)
    print("BENCHMARK 1: Tokenizer Initialization (Singleton Cache)")
    print("=" * 80)

    # Reset tokenizer cache (force reload)
    import src.components.ingestion.section_extraction as section_extraction_module
    section_extraction_module._TOKENIZER = None

    # First call: Should load tokenizer from disk
    start = time.perf_counter()
    tokenizer1 = _get_cached_tokenizer()
    first_call_time = (time.perf_counter() - start) * 1000

    # Second call: Should use cached tokenizer
    start = time.perf_counter()
    tokenizer2 = _get_cached_tokenizer()
    cached_call_time = (time.perf_counter() - start) * 1000

    # Verify they are the same object
    is_same_object = tokenizer1 is tokenizer2

    speedup = first_call_time / cached_call_time if cached_call_time > 0 else 0

    print(f"\nFirst call (load from disk):  {first_call_time:>8.2f} ms")
    print(f"Cached call (singleton):       {cached_call_time:>8.2f} ms")
    print(f"Speedup (first/cached):        {speedup:>8.1f}x")
    print(f"Same object instance:          {is_same_object}")
    print(f"Time saved per call:           {first_call_time - cached_call_time:>8.2f} ms")

    return {
        "first_call_ms": first_call_time,
        "cached_call_ms": cached_call_time,
        "speedup": speedup,
        "same_object": is_same_object,
    }


def benchmark_parallel_tokenization():
    """Benchmark parallel vs sequential tokenization for 50-200 text blocks."""
    print("\n" + "=" * 80)
    print("BENCHMARK 2: Parallel Tokenization (ThreadPoolExecutor)")
    print("=" * 80)

    # Generate synthetic text blocks (simulating document sections)
    text_sizes = [50, 100, 150, 200]  # Number of text blocks
    text_templates = [
        "This is a short section with minimal content.",
        "This section contains a moderate amount of text that might appear in a typical document paragraph. " * 5,
        "This is a long section with extensive content that would be typical for a research paper or technical documentation. " * 10,
        "Introduction\n\nThis document provides comprehensive coverage of the topic at hand. " * 8,
    ]

    results = []

    for size in text_sizes:
        print(f"\n--- Testing with {size} text blocks ---")

        # Generate test texts (cycle through templates)
        test_texts = [text_templates[i % len(text_templates)] for i in range(size)]

        # Benchmark sequential tokenization (baseline)
        tokenizer = _get_cached_tokenizer()
        if tokenizer is None:
            print("ERROR: Tokenizer not available!")
            return {}

        start = time.perf_counter()
        sequential_counts = {}
        for idx, text in enumerate(test_texts):
            tokens = tokenizer.encode(text, add_special_tokens=False)
            sequential_counts[idx] = len(tokens)
        sequential_time = (time.perf_counter() - start) * 1000

        # Benchmark parallel tokenization (Sprint 121.2b)
        start = time.perf_counter()
        parallel_counts = _batch_tokenize_parallel(test_texts, max_workers=4)
        parallel_time = (time.perf_counter() - start) * 1000

        # Verify correctness (counts should match)
        counts_match = all(
            sequential_counts.get(idx) == parallel_counts.get(idx)
            for idx in range(len(test_texts))
        )

        speedup = sequential_time / parallel_time if parallel_time > 0 else 0

        print(f"Sequential time:         {sequential_time:>8.2f} ms")
        print(f"Parallel time (4 cores): {parallel_time:>8.2f} ms")
        print(f"Speedup:                 {speedup:>8.2f}x")
        print(f"Counts match:            {counts_match}")
        print(f"Time saved:              {sequential_time - parallel_time:>8.2f} ms")

        results.append(
            {
                "text_count": size,
                "sequential_ms": sequential_time,
                "parallel_ms": parallel_time,
                "speedup": speedup,
                "counts_match": counts_match,
            }
        )

    return results


def print_summary(tokenizer_results, parallel_results):
    """Print summary of all benchmark results."""
    print("\n" + "=" * 80)
    print("SPRINT 121 BENCHMARK SUMMARY")
    print("=" * 80)

    print("\n1. TOKENIZER SINGLETON CACHE (Feature 121.2a):")
    print(f"   - First call: {tokenizer_results['first_call_ms']:.2f} ms")
    print(f"   - Cached call: {tokenizer_results['cached_call_ms']:.2f} ms")
    print(f"   - Speedup: {tokenizer_results['speedup']:.1f}x")
    print(f"   - Time saved: {tokenizer_results['first_call_ms'] - tokenizer_results['cached_call_ms']:.2f} ms per call")

    print("\n2. PARALLEL TOKENIZATION (Feature 121.2b):")
    for result in parallel_results:
        print(f"   - {result['text_count']} texts: {result['speedup']:.2f}x speedup "
              f"({result['sequential_ms']:.1f}ms → {result['parallel_ms']:.1f}ms)")

    # Calculate average speedup across all text sizes
    avg_speedup = sum(r['speedup'] for r in parallel_results) / len(parallel_results)
    print(f"\n   Average Speedup (50-200 texts): {avg_speedup:.2f}x")

    print("\n3. COMBINED IMPACT:")
    # Estimate total time saved for a typical document (100 texts)
    result_100 = next((r for r in parallel_results if r['text_count'] == 100), None)
    if result_100:
        tokenizer_savings = tokenizer_results['first_call_ms'] - tokenizer_results['cached_call_ms']
        parallel_savings = result_100['sequential_ms'] - result_100['parallel_ms']
        total_savings = tokenizer_savings + parallel_savings
        print(f"   - Tokenizer cache: {tokenizer_savings:.0f} ms saved")
        print(f"   - Parallel tokenization: {parallel_savings:.0f} ms saved")
        print(f"   - Total time saved (100 texts): {total_savings:.0f} ms")
        print(f"   - Overall speedup: {(result_100['sequential_ms'] + tokenizer_results['first_call_ms']) / (result_100['parallel_ms'] + tokenizer_results['cached_call_ms']):.2f}x")

    print("\n4. SPRINT 121 METRICS UPDATE:")
    print(f"   - Tokenizer Cache Speedup: {tokenizer_results['speedup']:.1f}x")
    print(f"   - Parallel Tokenization Speedup (avg): {avg_speedup:.2f}x")
    print(f"   - Status: MEASURED (replace 'awaiting benchmark' in Sprint 121 plan)")


def main():
    """Run all benchmarks and report results."""
    print("=" * 80)
    print("Sprint 121 Section Extraction Parallel Features Benchmark")
    print("TD-078 Phase 2: Tokenizer Singleton + Parallel Tokenization")
    print("=" * 80)

    try:
        # Benchmark 1: Tokenizer caching
        tokenizer_results = benchmark_tokenizer_caching()

        # Benchmark 2: Parallel tokenization
        parallel_results = benchmark_parallel_tokenization()

        # Print summary
        print_summary(tokenizer_results, parallel_results)

        print("\n" + "=" * 80)
        print("Benchmark completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\nERROR: Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
