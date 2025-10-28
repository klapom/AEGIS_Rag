"""
E2E tests for embedding benchmark script.

These tests require:
- Qdrant running on localhost:6333
- Ollama running with nomic-embed-text and bge-m3 models
"""

import pytest
import json
import asyncio
from pathlib import Path
import tempfile

# Mock qdrant_client import for unit test environment
import sys
from unittest.mock import MagicMock

if "qdrant_client" not in sys.modules:
    sys.modules["qdrant_client"] = MagicMock()
    sys.modules["qdrant_client.models"] = MagicMock()

from scripts.benchmark_embeddings import (
    BenchmarkConfig,
    EmbeddingBenchmark,
)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestBenchmarkE2E:
    """E2E tests for complete benchmark workflow."""

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_benchmark_nomic_embed_text(self, tmp_path):
        """
        E2E Test: Benchmark nomic-embed-text model.

        Prerequisites:
        - Qdrant running on localhost:6333
        - Ollama running with nomic-embed-text model
        """
        output_path = tmp_path / "benchmark_nomic.json"

        config = BenchmarkConfig(
            models=["nomic-embed-text"],
            test_corpus_path="nonexistent.json",  # Will use synthetic
            num_documents=20,
            batch_size=10,
            output_path=str(output_path),
        )

        benchmark = EmbeddingBenchmark(config)
        results = await benchmark.run()

        # Verify results structure
        assert "nomic-embed-text" in results
        metrics = results["nomic-embed-text"]

        # Verify dimension
        assert metrics.embedding_dim == 768

        # Verify latency metrics exist and are reasonable
        assert 0 < metrics.single_embedding_latency_ms < 1000  # <1s
        assert 0 < metrics.batch_embedding_latency_ms < 500  # <500ms
        assert 0 < metrics.p50_latency_ms < 1000
        assert 0 < metrics.p95_latency_ms < 1000
        assert 0 < metrics.p99_latency_ms < 1000

        # Verify memory metrics
        assert metrics.model_size_mb == 274  # nomic-embed-text size
        assert metrics.collection_size_mb > 0

        # Verify cross-layer compatibility
        assert metrics.cross_layer_similarity_possible == False  # 768-dim not compatible with Graphiti

        # Verify output file created
        assert output_path.exists()
        with open(output_path, "r") as f:
            saved_data = json.load(f)
        assert "nomic-embed-text" in saved_data

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_benchmark_bge_m3(self, tmp_path):
        """
        E2E Test: Benchmark BGE-M3 model.

        Prerequisites:
        - Qdrant running on localhost:6333
        - Ollama running with bge-m3 model
        """
        output_path = tmp_path / "benchmark_bge.json"

        config = BenchmarkConfig(
            models=["bge-m3"],
            test_corpus_path="nonexistent.json",
            num_documents=20,
            batch_size=10,
            output_path=str(output_path),
        )

        benchmark = EmbeddingBenchmark(config)
        results = await benchmark.run()

        # Verify results
        assert "bge-m3" in results
        metrics = results["bge-m3"]

        # Verify dimension
        assert metrics.embedding_dim == 1024

        # Verify latency metrics
        assert 0 < metrics.single_embedding_latency_ms < 2000  # BGE-M3 is slower
        assert 0 < metrics.batch_embedding_latency_ms < 1000

        # Verify memory metrics
        assert metrics.model_size_mb == 2200  # BGE-M3 size
        assert metrics.collection_size_mb > 0

        # Verify cross-layer compatibility
        assert metrics.cross_layer_similarity_possible == True  # 1024-dim compatible with Graphiti

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_benchmark_comparison(self, tmp_path):
        """
        E2E Test: Compare nomic-embed-text vs BGE-M3.

        Prerequisites:
        - Qdrant running on localhost:6333
        - Ollama running with both models
        """
        output_path = tmp_path / "benchmark_comparison.json"

        config = BenchmarkConfig(
            models=["nomic-embed-text", "bge-m3"],
            test_corpus_path="nonexistent.json",
            num_documents=15,
            batch_size=8,
            output_path=str(output_path),
        )

        benchmark = EmbeddingBenchmark(config)
        results = await benchmark.run()

        # Verify both models benchmarked
        assert len(results) == 2
        assert "nomic-embed-text" in results
        assert "bge-m3" in results

        nomic_metrics = results["nomic-embed-text"]
        bge_metrics = results["bge-m3"]

        # Verify dimension difference
        assert nomic_metrics.embedding_dim == 768
        assert bge_metrics.embedding_dim == 1024

        # Verify BGE-M3 is slower (expected)
        assert bge_metrics.single_embedding_latency_ms > nomic_metrics.single_embedding_latency_ms

        # Verify BGE-M3 uses more memory (expected)
        assert bge_metrics.model_size_mb > nomic_metrics.model_size_mb

        # Verify cross-layer compatibility difference
        assert nomic_metrics.cross_layer_similarity_possible == False
        assert bge_metrics.cross_layer_similarity_possible == True

        # Verify output file has both results
        assert output_path.exists()
        with open(output_path, "r") as f:
            saved_data = json.load(f)
        assert len(saved_data) == 2

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_benchmark_with_real_corpus(self, tmp_path):
        """
        E2E Test: Benchmark with actual document corpus.

        Prerequisites:
        - Qdrant running
        - Ollama running
        - Test corpus file
        """
        # Create test corpus
        corpus = []
        for i in range(10):
            corpus.append({
                "id": f"omnitracker_doc_{i}",
                "text": f"OMNITRACKER ITSM document {i}. This document contains information about "
                       f"IT service management, ticket handling, and workflow automation. "
                       f"It includes technical details about configuration, deployment, and best practices.",
            })

        corpus_path = tmp_path / "test_corpus.json"
        with open(corpus_path, "w") as f:
            json.dump(corpus, f)

        output_path = tmp_path / "benchmark_real_corpus.json"

        config = BenchmarkConfig(
            models=["bge-m3"],
            test_corpus_path=str(corpus_path),
            num_documents=10,
            batch_size=5,
            output_path=str(output_path),
        )

        benchmark = EmbeddingBenchmark(config)
        results = await benchmark.run()

        # Verify corpus was used
        assert "bge-m3" in results
        metrics = results["bge-m3"]

        # Verify metrics
        assert metrics.embedding_dim == 1024
        assert metrics.single_embedding_latency_ms > 0
        assert metrics.collection_size_mb > 0

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_benchmark_stress_large_corpus(self, tmp_path):
        """
        E2E Test: Benchmark with large corpus (100 documents).

        This tests performance with realistic document count.

        Prerequisites:
        - Qdrant running
        - Ollama running
        - Sufficient memory
        """
        output_path = tmp_path / "benchmark_stress.json"

        config = BenchmarkConfig(
            models=["bge-m3"],
            test_corpus_path="nonexistent.json",  # Synthetic
            num_documents=100,
            batch_size=32,
            output_path=str(output_path),
        )

        benchmark = EmbeddingBenchmark(config)
        results = await benchmark.run()

        # Verify completion
        assert "bge-m3" in results
        metrics = results["bge-m3"]

        # Verify collection size increased
        assert metrics.collection_size_mb > 50  # 100 docs should be >50MB

        # Verify latency metrics
        assert metrics.p99_latency_ms > 0

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_benchmark_qdrant_cleanup(self, tmp_path):
        """
        E2E Test: Verify Qdrant collections are cleaned up after benchmark.

        Prerequisites:
        - Qdrant running
        - Ollama running
        """
        from qdrant_client import QdrantClient

        qdrant = QdrantClient(host="localhost", port=6333)

        # Get collection count before
        collections_before = qdrant.get_collections().collections
        count_before = len(collections_before)

        # Run benchmark
        config = BenchmarkConfig(
            models=["bge-m3"],
            test_corpus_path="nonexistent.json",
            num_documents=5,
            output_path=str(tmp_path / "results.json"),
        )

        benchmark = EmbeddingBenchmark(config)
        await benchmark.run()

        # Get collection count after
        collections_after = qdrant.get_collections().collections
        count_after = len(collections_after)

        # Verify no leftover benchmark collections
        assert count_after == count_before, "Benchmark collections were not cleaned up"

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_benchmark_error_handling_missing_model(self, tmp_path):
        """
        E2E Test: Benchmark handles missing model gracefully.

        Prerequisites:
        - Qdrant running
        - Ollama running (but without specific model)
        """
        output_path = tmp_path / "benchmark_error.json"

        config = BenchmarkConfig(
            models=["nonexistent-model"],
            test_corpus_path="nonexistent.json",
            num_documents=5,
            output_path=str(output_path),
        )

        benchmark = EmbeddingBenchmark(config)

        # Should raise error or handle gracefully
        with pytest.raises(Exception):
            await benchmark.run()

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_benchmark_output_format(self, tmp_path):
        """
        E2E Test: Verify benchmark output JSON format is valid.

        Prerequisites:
        - Qdrant running
        - Ollama running
        """
        output_path = tmp_path / "benchmark_format.json"

        config = BenchmarkConfig(
            models=["bge-m3"],
            test_corpus_path="nonexistent.json",
            num_documents=5,
            output_path=str(output_path),
        )

        benchmark = EmbeddingBenchmark(config)
        await benchmark.run()

        # Verify JSON structure
        with open(output_path, "r") as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "bge-m3" in data

        model_data = data["bge-m3"]
        required_fields = [
            "model_name",
            "embedding_dim",
            "single_embedding_latency_ms",
            "batch_embedding_latency_ms",
            "p50_latency_ms",
            "p95_latency_ms",
            "p99_latency_ms",
            "model_size_mb",
            "collection_size_mb",
            "cross_layer_similarity_possible",
        ]

        for field in required_fields:
            assert field in model_data, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestBenchmarkCLI:
    """E2E tests for CLI interface."""

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_cli_default_args(self, tmp_path):
        """Test CLI with default arguments."""
        import sys
        from scripts.benchmark_embeddings import main

        # Mock sys.argv
        sys.argv = [
            "benchmark_embeddings.py",
            "--output",
            str(tmp_path / "cli_test.json"),
        ]

        await main()

        # Verify output created
        assert (tmp_path / "cli_test.json").exists()

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    async def test_cli_custom_models(self, tmp_path):
        """Test CLI with custom model list."""
        import sys
        from scripts.benchmark_embeddings import main

        sys.argv = [
            "benchmark_embeddings.py",
            "--models",
            "bge-m3",
            "--num-documents",
            "10",
            "--output",
            str(tmp_path / "cli_custom.json"),
        ]

        await main()

        # Verify only bge-m3 results
        with open(tmp_path / "cli_custom.json", "r") as f:
            data = json.load(f)
        assert len(data) == 1
        assert "bge-m3" in data
