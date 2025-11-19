"""
Unit tests for embedding benchmark script.

Tests cover:
- BenchmarkConfig creation
- Synthetic corpus generation
- Latency measurement
- Memory estimation
- Results saving and comparison
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import asdict

# Mock qdrant_client before importing benchmark script
import sys
from unittest.mock import MagicMock

sys.modules["qdrant_client"] = MagicMock()
sys.modules["qdrant_client.models"] = MagicMock()

from scripts.benchmark_embeddings import (
    BenchmarkConfig,
    EmbeddingMetrics,
    EmbeddingBenchmark,
)


class TestBenchmarkConfig:
    """Test BenchmarkConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = BenchmarkConfig(models=["nomic-embed-text"], test_corpus_path="data/test.json")

        assert config.models == ["nomic-embed-text"]
        assert config.test_corpus_path == "data/test.json"
        assert config.num_documents == 100
        assert config.batch_size == 32
        assert config.output_path == "results/embedding_benchmark.json"

    def test_custom_config(self):
        """Test custom configuration."""
        config = BenchmarkConfig(
            models=["bge-m3", "nomic-embed-text"],
            test_corpus_path="/custom/path.json",
            num_documents=50,
            batch_size=16,
            output_path="/custom/output.json",
        )

        assert len(config.models) == 2
        assert config.num_documents == 50
        assert config.batch_size == 16


class TestEmbeddingMetrics:
    """Test EmbeddingMetrics dataclass."""

    def test_metrics_creation(self):
        """Test metrics dataclass creation."""
        metrics = EmbeddingMetrics(
            model_name="bge-m3",
            embedding_dim=1024,
            single_embedding_latency_ms=25.5,
            batch_embedding_latency_ms=15.2,
            p50_latency_ms=20.0,
            p95_latency_ms=30.0,
            p99_latency_ms=35.0,
            model_size_mb=2200,
            collection_size_mb=150.5,
        )

        assert metrics.model_name == "bge-m3"
        assert metrics.embedding_dim == 1024
        assert metrics.single_embedding_latency_ms == 25.5
        assert metrics.cross_layer_similarity_possible == False  # default

    def test_metrics_with_retrieval_quality(self):
        """Test metrics with retrieval quality scores."""
        metrics = EmbeddingMetrics(
            model_name="bge-m3",
            embedding_dim=1024,
            single_embedding_latency_ms=25.5,
            batch_embedding_latency_ms=15.2,
            p50_latency_ms=20.0,
            p95_latency_ms=30.0,
            p99_latency_ms=35.0,
            model_size_mb=2200,
            collection_size_mb=150.5,
            ndcg_at_10=0.85,
            mrr=0.78,
            precision_at_5=0.82,
        )

        assert metrics.ndcg_at_10 == 0.85
        assert metrics.mrr == 0.78
        assert metrics.precision_at_5 == 0.82

    def test_metrics_serialization(self):
        """Test metrics can be serialized to dict."""
        metrics = EmbeddingMetrics(
            model_name="bge-m3",
            embedding_dim=1024,
            single_embedding_latency_ms=25.5,
            batch_embedding_latency_ms=15.2,
            p50_latency_ms=20.0,
            p95_latency_ms=30.0,
            p99_latency_ms=35.0,
            model_size_mb=2200,
            collection_size_mb=150.5,
        )

        metrics_dict = asdict(metrics)
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["model_name"] == "bge-m3"
        assert metrics_dict["embedding_dim"] == 1024


class TestEmbeddingBenchmark:
    """Test EmbeddingBenchmark class."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client."""
        mock = Mock()
        mock.create_collection = Mock()
        mock.upsert = Mock()
        mock.get_collection = Mock(return_value=Mock(vectors_count=100, points_count=100))
        mock.delete_collection = Mock()
        return mock

    @pytest.fixture
    def benchmark_config(self, tmp_path):
        """Create benchmark config with temp paths."""
        return BenchmarkConfig(
            models=["nomic-embed-text"],
            test_corpus_path=str(tmp_path / "test_corpus.json"),
            num_documents=10,
            batch_size=5,
            output_path=str(tmp_path / "results.json"),
        )

    def test_benchmark_initialization(self, benchmark_config, mock_qdrant_client):
        """Test benchmark initialization."""
        with patch("scripts.benchmark_embeddings.QdrantClient", return_value=mock_qdrant_client):
            benchmark = EmbeddingBenchmark(benchmark_config)

            assert benchmark.config == benchmark_config
            assert benchmark.qdrant_client == mock_qdrant_client
            assert benchmark.results == {}

    def test_generate_synthetic_corpus(self, benchmark_config, mock_qdrant_client):
        """Test synthetic corpus generation."""
        with patch("scripts.benchmark_embeddings.QdrantClient", return_value=mock_qdrant_client):
            benchmark = EmbeddingBenchmark(benchmark_config)
            corpus = benchmark._generate_synthetic_corpus()

            assert len(corpus) == benchmark_config.num_documents
            assert all("id" in doc for doc in corpus)
            assert all("text" in doc for doc in corpus)
            assert all(len(doc["text"]) > 50 for doc in corpus)

    def test_load_test_corpus_fallback_to_synthetic(self, benchmark_config, mock_qdrant_client):
        """Test loading corpus falls back to synthetic when file not found."""
        with patch("scripts.benchmark_embeddings.QdrantClient", return_value=mock_qdrant_client):
            benchmark = EmbeddingBenchmark(benchmark_config)
            corpus = benchmark._load_test_corpus()

            assert len(corpus) == benchmark_config.num_documents
            assert corpus[0]["id"] == "doc_0"

    def test_load_test_corpus_from_file(self, benchmark_config, mock_qdrant_client, tmp_path):
        """Test loading corpus from JSON file."""
        # Create test corpus file
        test_corpus = [
            {"id": "test_1", "text": "Test document 1"},
            {"id": "test_2", "text": "Test document 2"},
        ]
        corpus_path = Path(benchmark_config.test_corpus_path)
        corpus_path.parent.mkdir(parents=True, exist_ok=True)
        with open(corpus_path, "w") as f:
            json.dump(test_corpus, f)

        with patch("scripts.benchmark_embeddings.QdrantClient", return_value=mock_qdrant_client):
            benchmark = EmbeddingBenchmark(benchmark_config)
            corpus = benchmark._load_test_corpus()

            assert len(corpus) == 2
            assert corpus[0]["id"] == "test_1"
            assert corpus[1]["text"] == "Test document 2"

    @pytest.mark.asyncio
    async def test_benchmark_latency(self, benchmark_config, mock_qdrant_client):
        """Test latency benchmarking."""
        mock_embedding_service = AsyncMock()
        mock_embedding_service.embed_text = AsyncMock(return_value=[0.1] * 768)
        mock_embedding_service.embed_batch = AsyncMock(return_value=[[0.1] * 768 for _ in range(5)])

        with patch("scripts.benchmark_embeddings.QdrantClient", return_value=mock_qdrant_client):
            benchmark = EmbeddingBenchmark(benchmark_config)
            texts = ["Test text 1", "Test text 2", "Test text 3", "Test text 4", "Test text 5"]

            metrics = await benchmark._benchmark_latency(mock_embedding_service, texts)

            assert "single_avg" in metrics
            assert "batch_avg" in metrics
            assert "p50" in metrics
            assert "p95" in metrics
            assert "p99" in metrics
            assert all(isinstance(v, float) for v in metrics.values())
            assert all(v > 0 for v in metrics.values())

    @pytest.mark.asyncio
    async def test_benchmark_memory(self, benchmark_config, mock_qdrant_client):
        """Test memory benchmarking."""
        mock_embedding_service = AsyncMock()
        mock_embedding_service.model_name = "nomic-embed-text"
        mock_embedding_service.embed_text = AsyncMock(return_value=[0.1] * 768)

        with patch("scripts.benchmark_embeddings.QdrantClient", return_value=mock_qdrant_client):
            benchmark = EmbeddingBenchmark(benchmark_config)
            texts = ["Test text 1", "Test text 2"]

            metrics = await benchmark._benchmark_memory(
                mock_embedding_service, texts, embedding_dim=768
            )

            assert "model_size_mb" in metrics
            assert "collection_size_mb" in metrics
            assert metrics["model_size_mb"] == 274  # nomic-embed-text size
            assert isinstance(metrics["collection_size_mb"], float)

            # Verify Qdrant operations called
            mock_qdrant_client.create_collection.assert_called_once()
            mock_qdrant_client.upsert.assert_called_once()
            mock_qdrant_client.delete_collection.assert_called_once()

    def test_save_results(self, benchmark_config, mock_qdrant_client, tmp_path):
        """Test results saving to JSON."""
        with patch("scripts.benchmark_embeddings.QdrantClient", return_value=mock_qdrant_client):
            benchmark = EmbeddingBenchmark(benchmark_config)

            # Add mock results
            benchmark.results = {
                "nomic-embed-text": EmbeddingMetrics(
                    model_name="nomic-embed-text",
                    embedding_dim=768,
                    single_embedding_latency_ms=15.0,
                    batch_embedding_latency_ms=10.0,
                    p50_latency_ms=12.0,
                    p95_latency_ms=18.0,
                    p99_latency_ms=20.0,
                    model_size_mb=274,
                    collection_size_mb=50.0,
                )
            }

            benchmark._save_results()

            # Verify file created
            output_path = Path(benchmark_config.output_path)
            assert output_path.exists()

            # Verify content
            with open(output_path, "r") as f:
                saved_results = json.load(f)

            assert "nomic-embed-text" in saved_results
            assert saved_results["nomic-embed-text"]["embedding_dim"] == 768

    def test_print_comparison_single_model(self, benchmark_config, mock_qdrant_client, capsys):
        """Test comparison printing for single model."""
        with patch("scripts.benchmark_embeddings.QdrantClient", return_value=mock_qdrant_client):
            benchmark = EmbeddingBenchmark(benchmark_config)

            benchmark.results = {
                "nomic-embed-text": EmbeddingMetrics(
                    model_name="nomic-embed-text",
                    embedding_dim=768,
                    single_embedding_latency_ms=15.0,
                    batch_embedding_latency_ms=10.0,
                    p50_latency_ms=12.0,
                    p95_latency_ms=18.0,
                    p99_latency_ms=20.0,
                    model_size_mb=274,
                    collection_size_mb=50.0,
                )
            }

            benchmark._print_comparison()

            captured = capsys.readouterr()
            assert "EMBEDDING MODEL BENCHMARK RESULTS" in captured.out
            assert "nomic-embed-text" in captured.out
            assert "768" in captured.out

    def test_print_comparison_two_models(self, benchmark_config, mock_qdrant_client, capsys):
        """Test comparison printing for two models."""
        with patch("scripts.benchmark_embeddings.QdrantClient", return_value=mock_qdrant_client):
            benchmark = EmbeddingBenchmark(benchmark_config)

            benchmark.results = {
                "nomic-embed-text": EmbeddingMetrics(
                    model_name="nomic-embed-text",
                    embedding_dim=768,
                    single_embedding_latency_ms=15.0,
                    batch_embedding_latency_ms=10.0,
                    p50_latency_ms=12.0,
                    p95_latency_ms=18.0,
                    p99_latency_ms=20.0,
                    model_size_mb=274,
                    collection_size_mb=50.0,
                ),
                "bge-m3": EmbeddingMetrics(
                    model_name="bge-m3",
                    embedding_dim=1024,
                    single_embedding_latency_ms=25.0,
                    batch_embedding_latency_ms=15.0,
                    p50_latency_ms=20.0,
                    p95_latency_ms=30.0,
                    p99_latency_ms=35.0,
                    model_size_mb=2200,
                    collection_size_mb=150.0,
                ),
            }

            benchmark._print_comparison()

            captured = capsys.readouterr()
            assert "COMPARISON SUMMARY" in captured.out
            assert "slower" in captured.out or "faster" in captured.out
            assert "dimensions" in captured.out


@pytest.mark.integration
class TestBenchmarkIntegration:
    """Integration tests for benchmark (require real Qdrant)."""

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    @pytest.mark.asyncio
    async def test_full_benchmark_nomic(self, tmp_path):
        """Test full benchmark with nomic-embed-text (real service)."""
        config = BenchmarkConfig(
            models=["nomic-embed-text"],
            test_corpus_path=str(tmp_path / "corpus.json"),
            num_documents=5,
            output_path=str(tmp_path / "results.json"),
        )

        benchmark = EmbeddingBenchmark(config)
        results = await benchmark.run()

        assert "nomic-embed-text" in results
        assert results["nomic-embed-text"].embedding_dim == 768
        assert results["nomic-embed-text"].single_embedding_latency_ms > 0

    @pytest.mark.skip(reason="Requires Qdrant and Ollama running")
    @pytest.mark.asyncio
    async def test_full_benchmark_comparison(self, tmp_path):
        """Test full benchmark comparing both models (real services)."""
        config = BenchmarkConfig(
            models=["nomic-embed-text", "bge-m3"],
            test_corpus_path=str(tmp_path / "corpus.json"),
            num_documents=5,
            output_path=str(tmp_path / "results.json"),
        )

        benchmark = EmbeddingBenchmark(config)
        results = await benchmark.run()

        assert len(results) == 2
        assert "nomic-embed-text" in results
        assert "bge-m3" in results
        assert results["nomic-embed-text"].embedding_dim == 768
        assert results["bge-m3"].embedding_dim == 1024
