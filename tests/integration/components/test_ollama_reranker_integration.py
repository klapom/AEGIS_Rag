"""Integration tests for OllamaReranker with real Ollama service.

Sprint 48 Feature 48.8: TD-059 Ollama Reranker Implementation

These tests require:
1. Ollama server running at localhost:11434
2. bge-reranker-v2-m3 model pulled (ollama pull bge-reranker-v2-m3)

To run these tests:
    pytest tests/integration/components/test_ollama_reranker_integration.py -v

Skip if Ollama not available:
    pytest tests/integration/components/test_ollama_reranker_integration.py -v -m "not requires_ollama"
"""

import aiohttp
import pytest

from src.components.retrieval.ollama_reranker import OllamaReranker
from src.core.config import settings


async def check_ollama_available() -> bool:
    """Check if Ollama is available and responsive."""
    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                f"{settings.ollama_base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp,
        ):
            return resp.status == 200
    except Exception:
        return False


async def check_model_available(model: str = "bge-reranker-v2-m3") -> bool:
    """Check if the reranker model is available in Ollama."""
    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                f"{settings.ollama_base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp,
        ):
            if resp.status != 200:
                return False
            data = await resp.json()
            models = data.get("models", [])
            return any(m.get("name", "").startswith(model) for m in models)
    except Exception:
        return False


@pytest.fixture(scope="module")
async def ollama_available():
    """Check if Ollama is available before running tests."""
    available = await check_ollama_available()
    if not available:
        pytest.skip("Ollama server not available at localhost:11434")
    return available


@pytest.fixture(scope="module")
async def model_available():
    """Check if bge-reranker-v2-m3 model is available."""
    available = await check_model_available()
    if not available:
        pytest.skip(
            "bge-reranker-v2-m3 model not available. " "Pull with: ollama pull bge-reranker-v2-m3"
        )
    return available


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_ollama
class TestOllamaRerankerRealAPI:
    """Integration tests with real Ollama API."""

    async def test_rerank_with_real_ollama(self, ollama_available, model_available):
        """Test reranking with real Ollama service."""
        reranker = OllamaReranker(model="bge-reranker-v2-m3", top_k=3)

        query = "What is vector search?"
        documents = [
            "Vector search uses embeddings to find semantically similar documents",
            "BM25 is a probabilistic keyword-based ranking algorithm",
            "Hybrid search combines vector and keyword approaches",
            "The weather today is sunny and warm",
        ]

        ranked = await reranker.rerank(query, documents, top_k=3)

        # Verify results
        assert len(ranked) == 3
        assert all(isinstance(idx, int) for idx, _ in ranked)
        assert all(isinstance(score, float) for _, score in ranked)
        assert all(0.0 <= score <= 1.0 for _, score in ranked)

        # First result should be most relevant (vector search doc)
        assert ranked[0][0] == 0  # Document about vector search

        # Scores should be in descending order
        scores = [score for _, score in ranked]
        assert scores == sorted(scores, reverse=True)

    async def test_rerank_multilingual(self, ollama_available, model_available):
        """Test reranking with multilingual content (BGE-M3 is multilingual)."""
        reranker = OllamaReranker(model="bge-reranker-v2-m3", top_k=2)

        query = "machine learning algorithms"
        documents = [
            "Machine learning algorithms learn patterns from data",
            "深度学习是机器学习的子领域",  # Chinese: Deep learning is a subfield of ML
            "Random recipe for chocolate cake",
        ]

        ranked = await reranker.rerank(query, documents, top_k=2)

        # Verify results
        assert len(ranked) == 2

        # English doc about ML should be most relevant
        assert ranked[0][0] == 0

    async def test_rerank_empty_query(self, ollama_available, model_available):
        """Test reranking with empty query."""
        reranker = OllamaReranker(model="bge-reranker-v2-m3")

        documents = ["doc1", "doc2", "doc3"]

        ranked = await reranker.rerank("", documents, top_k=2)

        # Should still return results (though scores may be low)
        assert len(ranked) == 2

    async def test_rerank_single_document(self, ollama_available, model_available):
        """Test reranking with a single document."""
        reranker = OllamaReranker(model="bge-reranker-v2-m3")

        ranked = await reranker.rerank("test query", ["single document about testing"], top_k=1)

        assert len(ranked) == 1
        assert ranked[0][0] == 0

    async def test_rerank_latency(self, ollama_available, model_available):
        """Test reranking latency with real API."""
        import time

        reranker = OllamaReranker(model="bge-reranker-v2-m3", top_k=5)

        query = "vector search"
        documents = [f"Document {i} about vector search" for i in range(5)]

        start = time.perf_counter()
        ranked = await reranker.rerank(query, documents)
        elapsed = time.perf_counter() - start

        # Verify results
        assert len(ranked) == 5

        # Latency check (should be reasonable, adjust based on hardware)
        # On DGX Spark: ~50-100ms per document, so 5 docs = ~250-500ms
        assert elapsed < 2.0, f"Reranking took {elapsed:.2f}s (expected <2s)"

        print(f"Reranking 5 documents took {elapsed*1000:.1f}ms")


@pytest.mark.asyncio
@pytest.mark.integration
class TestOllamaRerankerModelNotFound:
    """Test behavior when model is not available."""

    async def test_rerank_with_missing_model(self, ollama_available):
        """Test graceful handling when model is not found."""
        reranker = OllamaReranker(model="nonexistent-model-xyz", top_k=2)

        query = "test query"
        documents = ["doc1", "doc2", "doc3"]

        # Should handle error gracefully (either skip or raise clear error)
        try:
            ranked = await reranker.rerank(query, documents)
            # If it doesn't raise, check results are reasonable
            assert len(ranked) <= 2
        except Exception as e:
            # Expected to fail with model not found
            assert "model" in str(e).lower() or "404" in str(e)


@pytest.mark.asyncio
@pytest.mark.integration
class TestOllamaRerankerPerformance:
    """Performance tests for OllamaReranker."""

    async def test_rerank_many_documents(self, ollama_available, model_available):
        """Test reranking with many documents."""
        import time

        reranker = OllamaReranker(model="bge-reranker-v2-m3", top_k=10)

        query = "machine learning"
        documents = [f"Document {i} about machine learning and AI" for i in range(20)]

        start = time.perf_counter()
        ranked = await reranker.rerank(query, documents, top_k=10)
        elapsed = time.perf_counter() - start

        # Verify results
        assert len(ranked) == 10

        # Performance check (20 documents should take <4s on DGX Spark)
        assert elapsed < 10.0, f"Reranking 20 docs took {elapsed:.2f}s (expected <10s)"

        print(f"Reranking 20 documents (returned top 10) took {elapsed*1000:.1f}ms")
        print(f"Average per document: {elapsed*1000/20:.1f}ms")
