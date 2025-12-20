#!/usr/bin/env python3
"""Verification script for sentence-transformers embedding service.

Sprint 35 Feature 35.8: Sentence-Transformers Migration

This script demonstrates:
1. Backend selection based on config
2. Single text embedding
3. Batch embedding with GPU acceleration
4. Cache hit rate tracking
5. Performance comparison (optional)

Usage:
    # Test with default backend (ollama)
    python scripts/verify_sentence_transformers_embedding.py

    # Test with sentence-transformers backend
    EMBEDDING_BACKEND=sentence-transformers python scripts/verify_sentence_transformers_embedding.py
"""

import os
import sys
import time

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def main():
    """Run verification tests."""
    print("=" * 80)
    print("Sentence-Transformers Embedding Service Verification")
    print("=" * 80)
    print()

    # Import after path setup
    from src.components.shared.embedding_factory import get_embedding_service
    from src.core.config import settings

    # Display current configuration
    backend = getattr(settings, "embedding_backend", "ollama")
    print("Current Configuration:")
    print(f"  Backend: {backend}")

    if backend == "sentence-transformers":
        model_name = getattr(settings, "st_model_name", "BAAI/bge-m3")
        device = getattr(settings, "st_device", "auto")
        batch_size = getattr(settings, "st_batch_size", 64)
        print(f"  Model: {model_name}")
        print(f"  Device: {device}")
        print(f"  Batch Size: {batch_size}")
    print()

    # Get embedding service
    print("1. Initializing embedding service...")
    service = get_embedding_service()
    print(f"   Service type: {type(service).__name__}")
    print()

    # Test single embedding
    print("2. Testing single text embedding...")
    start = time.perf_counter()
    embedding = service.embed_single("Hello world")
    duration_ms = (time.perf_counter() - start) * 1000
    print(f"   Embedding dimension: {len(embedding)}")
    print(f"   Duration: {duration_ms:.2f}ms")
    print()

    # Test batch embedding
    print("3. Testing batch embedding (100 texts)...")
    texts = [f"This is test text number {i}" for i in range(100)]
    start = time.perf_counter()
    embeddings = service.embed_batch(texts)
    duration_ms = (time.perf_counter() - start) * 1000
    throughput = len(texts) / (duration_ms / 1000)
    print(f"   Generated embeddings: {len(embeddings)}")
    print(f"   Duration: {duration_ms:.2f}ms")
    print(f"   Throughput: {throughput:.2f} embeddings/sec")
    print()

    # Test cache with duplicate texts
    print("4. Testing cache with duplicate texts...")
    duplicate_texts = ["duplicate text"] * 10 + [f"unique text {i}" for i in range(10)]
    start = time.perf_counter()
    embeddings = service.embed_batch(duplicate_texts)
    duration_ms = (time.perf_counter() - start) * 1000
    print(f"   Generated embeddings: {len(embeddings)}")
    print(f"   Duration: {duration_ms:.2f}ms")
    print()

    # Display statistics
    print("5. Service Statistics:")
    stats = service.get_stats()
    print(f"   Model: {stats.get('model', 'N/A')}")
    print(f"   Embedding dimension: {stats.get('embedding_dim', 'N/A')}")
    if "device" in stats:
        print(f"   Device: {stats['device']}")
    if "batch_size" in stats:
        print(f"   Batch size: {stats['batch_size']}")
    print()

    print("   Cache Statistics:")
    cache_stats = stats.get("cache", {})
    print(f"     Size: {cache_stats.get('size', 0)}/{cache_stats.get('max_size', 0)}")
    print(f"     Hits: {cache_stats.get('hits', 0)}")
    print(f"     Misses: {cache_stats.get('misses', 0)}")
    print(f"     Hit Rate: {cache_stats.get('hit_rate', 0):.2%}")
    print()

    print("=" * 80)
    print("Verification Complete!")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("  - For production deployment, set EMBEDDING_BACKEND=sentence-transformers")
    print("  - Tune ST_BATCH_SIZE based on GPU VRAM (32/64/128)")
    print("  - Monitor GPU utilization and throughput")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
