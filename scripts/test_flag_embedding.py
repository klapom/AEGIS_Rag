#!/usr/bin/env python3
"""Test script for FlagEmbedding service (Sprint 87 Feature 87.1).

Sprint Context: Sprint 87 (2026-01-13) - Feature 87.1: FlagEmbedding Service

Demonstrates FlagEmbedding multi-vector embedding generation:
    1. Dense + sparse vectors in single call
    2. Backward compatibility with SentenceTransformers API
    3. LRU cache performance
    4. Batch processing efficiency
    5. Sparse vector filtering (min_weight, top_k)

Usage:
    # Basic test
    python scripts/test_flag_embedding.py

    # Custom parameters
    python scripts/test_flag_embedding.py --batch-size 64 --sparse-top-k 50

    # Benchmark mode
    python scripts/test_flag_embedding.py --benchmark --num-texts 1000

Example Output:
    ========================================
    FlagEmbedding Service Test - Sprint 87.1
    ========================================

    Test 1: Single Text Embedding
    ------------------------------
    Text: "Hello world, this is a test of BGE-M3 embeddings."
    Dense vector: 1024 dimensions
    Sparse tokens: 42 tokens
    Top-5 tokens: [(12345, 0.850), (67890, 0.720), ...]

    Test 2: Batch Embedding
    -----------------------
    Batch size: 10 texts
    Avg dense dim: 1024
    Avg sparse tokens: 38.5
    Total duration: 1.23s (8.1 texts/sec)
    Cache hit rate: 0.0%

    Test 3: Cache Performance
    -------------------------
    Second batch (same texts): 0.01s (1000 texts/sec)
    Cache hit rate: 100.0%
    Speedup: 123x

See Also:
    - src/components/shared/flag_embedding_service.py: FlagEmbedding service
    - src/components/shared/sparse_vector_utils.py: Sparse vector utils
    - docs/sprints/SPRINT_87_PLAN.md: Sprint 87 plan
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.shared.flag_embedding_service import FlagEmbeddingService


def test_single_embedding(service: FlagEmbeddingService) -> None:
    """Test single text embedding."""
    print("\nTest 1: Single Text Embedding")
    print("-" * 30)

    text = "Hello world, this is a test of BGE-M3 multi-vector embeddings."
    result = service.embed_single(text)

    print(f"Text: {repr(text)}")
    print(f"Dense vector: {len(result['dense'])} dimensions")
    print(f"Sparse tokens: {len(result['sparse'])} tokens")

    # Show top-5 sparse tokens
    top_tokens = sorted(result["sparse"].items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"Top-5 sparse tokens: {[(idx, round(weight, 3)) for idx, weight in top_tokens]}")

    # Verify sparse_vector matches sparse dict
    sparse_indices = set(result["sparse_vector"].indices)
    sparse_dict_indices = set(result["sparse"].keys())
    assert sparse_indices == sparse_dict_indices, "Sparse vector indices mismatch!"

    print("\u2713 Test passed")


def test_batch_embedding(service: FlagEmbeddingService, batch_size: int = 10) -> None:
    """Test batch embedding."""
    print(f"\nTest 2: Batch Embedding ({batch_size} texts)")
    print("-" * 30)

    texts = [
        f"This is test document number {i} with some unique content." for i in range(batch_size)
    ]

    start = time.perf_counter()
    results = service.embed_batch(texts)
    duration = time.perf_counter() - start

    avg_dense_dim = sum(len(r["dense"]) for r in results) / len(results)
    avg_sparse_tokens = sum(len(r["sparse"]) for r in results) / len(results)

    print(f"Batch size: {len(texts)} texts")
    print(f"Avg dense dim: {avg_dense_dim:.0f}")
    print(f"Avg sparse tokens: {avg_sparse_tokens:.1f}")
    print(f"Total duration: {duration:.2f}s ({len(texts) / duration:.1f} texts/sec)")
    print(f"Cache hit rate: {service.cache.hit_rate() * 100:.1f}%")

    print("\u2713 Test passed")


def test_cache_performance(service: FlagEmbeddingService, batch_size: int = 10) -> None:
    """Test cache performance."""
    print(f"\nTest 3: Cache Performance ({batch_size} texts)")
    print("-" * 30)

    texts = [f"Test document {i}" for i in range(batch_size)]

    # First batch (cache miss)
    start1 = time.perf_counter()
    results1 = service.embed_batch(texts)
    duration1 = time.perf_counter() - start1

    # Second batch (cache hit)
    start2 = time.perf_counter()
    results2 = service.embed_batch(texts)
    duration2 = time.perf_counter() - start2

    # Verify results match
    for r1, r2 in zip(results1, results2):
        assert r1["dense"] == r2["dense"], "Dense vectors don't match!"
        assert r1["sparse"] == r2["sparse"], "Sparse vectors don't match!"

    speedup = duration1 / duration2 if duration2 > 0 else 0

    print(f"First batch (cache miss): {duration1:.3f}s ({len(texts) / duration1:.1f} texts/sec)")
    print(f"Second batch (cache hit): {duration2:.3f}s ({len(texts) / duration2:.1f} texts/sec)")
    print(f"Cache hit rate: {service.cache.hit_rate() * 100:.1f}%")
    print(f"Speedup: {speedup:.0f}x")

    print("\u2713 Test passed")


def test_backward_compatibility(service: FlagEmbeddingService) -> None:
    """Test backward compatibility with SentenceTransformers API."""
    print("\nTest 4: Backward Compatibility")
    print("-" * 30)

    text = "Test backward compatibility"

    # Multi-vector API
    result_multi = service.embed_single(text)
    dense_multi = result_multi["dense"]

    # Dense-only API (backward compat)
    dense_only = service.embed_single_dense(text)

    # Verify they match
    assert dense_multi == dense_only, "Dense vectors don't match!"

    print("embed_single() returns dict with dense + sparse")
    print("embed_single_dense() returns list[float] (backward compat)")
    print("Both methods return same dense vector: \u2713")

    # Batch API
    texts = ["Test 1", "Test 2", "Test 3"]
    results_multi = service.embed_batch(texts)
    results_dense = service.embed_batch_dense(texts)

    for i, (r_multi, r_dense) in enumerate(zip(results_multi, results_dense)):
        assert r_multi["dense"] == r_dense, f"Batch {i} dense vectors don't match!"

    print("embed_batch_dense() backward compatibility: \u2713")
    print("\u2713 Test passed")


def test_sparse_filtering(service: FlagEmbeddingService) -> None:
    """Test sparse vector filtering."""
    print("\nTest 5: Sparse Vector Filtering")
    print("-" * 30)

    text = "This is a longer text with many tokens to demonstrate sparse filtering."

    # No filtering
    service_no_filter = FlagEmbeddingService(
        sparse_min_weight=0.0, sparse_top_k=None, cache_max_size=100
    )
    result_no_filter = service_no_filter.embed_single(text)

    # Min weight filtering
    service_min_weight = FlagEmbeddingService(
        sparse_min_weight=0.3, sparse_top_k=None, cache_max_size=100
    )
    result_min_weight = service_min_weight.embed_single(text)

    # Top-k filtering
    service_top_k = FlagEmbeddingService(
        sparse_min_weight=0.0, sparse_top_k=20, cache_max_size=100
    )
    result_top_k = service_top_k.embed_single(text)

    print(f"No filtering: {len(result_no_filter['sparse'])} tokens")
    print(f"Min weight 0.3: {len(result_min_weight['sparse'])} tokens")
    print(f"Top-k 20: {len(result_top_k['sparse'])} tokens")

    # Verify filtering reduces token count
    assert len(result_min_weight["sparse"]) < len(result_no_filter["sparse"])
    assert len(result_top_k["sparse"]) <= 20

    print("\u2713 Test passed")


def benchmark(
    service: FlagEmbeddingService, num_texts: int = 1000, batch_size: int = 32
) -> None:
    """Benchmark embedding performance."""
    print(f"\nBenchmark: {num_texts} texts, batch_size={batch_size}")
    print("-" * 50)

    texts = [f"Benchmark document {i} with some test content." for i in range(num_texts)]

    # Warmup
    _ = service.embed_single("Warmup")

    # Benchmark
    start = time.perf_counter()
    results = service.embed_batch(texts)
    duration = time.perf_counter() - start

    # Calculate metrics
    throughput = num_texts / duration
    avg_sparse_tokens = sum(len(r["sparse"]) for r in results) / len(results)
    total_chars = sum(len(t) for t in texts)
    chars_per_sec = total_chars / duration

    print(f"Total duration: {duration:.2f}s")
    print(f"Throughput: {throughput:.1f} texts/sec")
    print(f"Chars/sec: {chars_per_sec:.0f}")
    print(f"Avg sparse tokens: {avg_sparse_tokens:.1f}")
    print(f"Cache hit rate: {service.cache.hit_rate() * 100:.1f}%")

    # Per-text latency
    avg_latency_ms = (duration / num_texts) * 1000
    print(f"Avg latency: {avg_latency_ms:.2f}ms/text")


def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(description="Test FlagEmbedding service")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--sparse-top-k", type=int, default=None, help="Sparse top-k")
    parser.add_argument("--sparse-min-weight", type=float, default=0.0, help="Sparse min weight")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark")
    parser.add_argument("--num-texts", type=int, default=1000, help="Benchmark texts")
    args = parser.parse_args()

    print("=" * 60)
    print("FlagEmbedding Service Test - Sprint 87.1")
    print("=" * 60)

    # Initialize service
    print("\nInitializing FlagEmbedding service...")
    service = FlagEmbeddingService(
        model_name="BAAI/bge-m3",
        device="auto",
        use_fp16=True,
        batch_size=args.batch_size,
        sparse_min_weight=args.sparse_min_weight,
        sparse_top_k=args.sparse_top_k,
    )
    print(f"Model: {service.model_name}")
    print(f"Device: {service.device}")
    print(f"Batch size: {service.batch_size}")
    print(f"Sparse min weight: {service.sparse_min_weight}")
    print(f"Sparse top-k: {service.sparse_top_k}")

    try:
        if args.benchmark:
            # Benchmark mode
            benchmark(service, num_texts=args.num_texts, batch_size=args.batch_size)
        else:
            # Test mode
            test_single_embedding(service)
            test_batch_embedding(service, batch_size=10)
            test_cache_performance(service, batch_size=10)
            test_backward_compatibility(service)
            test_sparse_filtering(service)

        print("\n" + "=" * 60)
        print("All tests passed! \u2713")
        print("=" * 60)

        # Print final stats
        stats = service.get_stats()
        print("\nFinal Statistics:")
        print(f"  Cache size: {stats['cache']['size']}/{stats['cache']['max_size']}")
        print(f"  Cache hits: {stats['cache']['hits']}")
        print(f"  Cache misses: {stats['cache']['misses']}")
        print(f"  Cache hit rate: {stats['cache']['hit_rate'] * 100:.1f}%")

    except ImportError as e:
        print(f"\n\u2717 Import error: {e}")
        print("Install FlagEmbedding with: pip install FlagEmbedding")
        sys.exit(1)
    except Exception as e:
        print(f"\n\u2717 Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
