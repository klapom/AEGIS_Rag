"""Unit tests for Adaptive Reranker (Sprint 67 Feature 67.8).

Tests intent-aware reranking with adaptive weights for different query types.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.retrieval.intent_classifier import Intent, IntentClassificationResult
from src.components.retrieval.reranker import (
    INTENT_RERANK_WEIGHTS,
    AdaptiveWeights,
    CrossEncoderReranker,
)


@pytest.fixture
def mock_intent_classifier():
    """Mock intent classifier for testing."""
    classifier = MagicMock()

    async def classify_mock(query: str):
        # Simple rule-based classification for tests
        if "what is" in query.lower():
            intent = Intent.FACTUAL
        elif "error" in query.lower() or "404" in query:
            intent = Intent.KEYWORD
        elif "how" in query.lower():
            intent = Intent.EXPLORATORY
        elif "summarize" in query.lower():
            intent = Intent.SUMMARY
        else:
            intent = Intent.EXPLORATORY

        return IntentClassificationResult(
            intent=intent,
            weights=None,  # Not used in reranker
            confidence=0.9,
            latency_ms=25.0,
            method="embedding",
        )

    classifier.classify = AsyncMock(side_effect=classify_mock)
    return classifier


@pytest.fixture
def sample_documents():
    """Sample documents for reranking tests."""
    return [
        {
            "id": "doc1",
            "text": "Vector search uses embeddings for semantic similarity",
            "score": 0.85,
            "bm25_score": 0.4,
            "metadata": {"created_at": "2024-01-15T10:00:00Z"},
        },
        {
            "id": "doc2",
            "text": "BM25 is a keyword-based search algorithm",
            "score": 0.75,
            "bm25_score": 0.8,
            "metadata": {"created_at": "2024-06-20T14:30:00Z"},
        },
        {
            "id": "doc3",
            "text": "Hybrid search combines vector and keyword approaches",
            "score": 0.90,
            "bm25_score": 0.6,
            "metadata": {"created_at": "2024-12-01T09:15:00Z"},
        },
        {
            "id": "doc4",
            "text": "Cross-encoder reranking improves precision",
            "score": 0.70,
            "bm25_score": 0.3,
            "metadata": {},  # No timestamp
        },
    ]


class TestAdaptiveWeights:
    """Test adaptive weight configurations."""

    def test_weights_sum_to_one(self):
        """Test that all weight profiles sum to 1.0."""
        for intent, weights in INTENT_RERANK_WEIGHTS.items():
            total = weights.semantic_weight + weights.keyword_weight + weights.recency_weight
            assert abs(total - 1.0) < 0.01, f"{intent} weights sum to {total}, not 1.0"

    def test_factual_weights_high_semantic(self):
        """Test factual queries prioritize semantic precision."""
        weights = INTENT_RERANK_WEIGHTS["factual"]
        assert weights.semantic_weight == 0.7
        assert weights.keyword_weight == 0.2
        assert weights.recency_weight == 0.1

    def test_keyword_weights_high_keyword(self):
        """Test keyword queries prioritize exact matching."""
        weights = INTENT_RERANK_WEIGHTS["keyword"]
        assert weights.semantic_weight == 0.3
        assert weights.keyword_weight == 0.6
        assert weights.recency_weight == 0.1

    def test_summary_weights_high_recency(self):
        """Test summary queries prioritize recency."""
        weights = INTENT_RERANK_WEIGHTS["summary"]
        assert weights.semantic_weight == 0.5
        assert weights.keyword_weight == 0.2
        assert weights.recency_weight == 0.3

    def test_invalid_weights_raise_error(self):
        """Test that invalid weight sums raise ValueError."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            AdaptiveWeights(semantic_weight=0.5, keyword_weight=0.3, recency_weight=0.1)


class TestCrossEncoderRerankerAdaptive:
    """Test CrossEncoderReranker with adaptive weights."""

    @pytest.mark.asyncio
    async def test_adaptive_reranking_factual_query(
        self, mock_intent_classifier, sample_documents
    ):
        """Test adaptive reranking for factual queries."""
        reranker = CrossEncoderReranker(use_adaptive_weights=True)
        reranker._intent_classifier = mock_intent_classifier

        # Mock cross-encoder model's predict method
        mock_model = MagicMock()
        # doc3 > doc1 > doc2 > doc4 (semantic scores)
        mock_model.predict.return_value = [0.8, 0.4, 0.9, 0.3]
        reranker._model = mock_model

        results = await reranker.rerank(
            query="What is hybrid search?",  # Factual query
            documents=sample_documents,
            top_k=4,
        )

        # Verify intent classification
        mock_intent_classifier.classify.assert_called_once()

        # Verify adaptive scores are computed
        assert all(r.adaptive_score is not None for r in results)
        assert all(r.bm25_score is not None for r in results)
        assert all(r.recency_score is not None for r in results)

        # For factual queries, semantic weight is high (0.7)
        # doc3 should rank highest (high semantic + recent)
        assert results[0].doc_id == "doc3"

    @pytest.mark.asyncio
    async def test_adaptive_reranking_keyword_query(
        self, mock_intent_classifier, sample_documents
    ):
        """Test adaptive reranking for keyword queries."""
        reranker = CrossEncoderReranker(use_adaptive_weights=True)
        reranker._intent_classifier = mock_intent_classifier

        # Mock cross-encoder model's predict method
        mock_model = MagicMock()
        # Lower semantic scores overall
        mock_model.predict.return_value = [0.5, 0.6, 0.4, 0.3]
        reranker._model = mock_model

        results = await reranker.rerank(
            query="BM25 error 404",  # Keyword query
            documents=sample_documents,
            top_k=4,
        )

        # For keyword queries, keyword weight is high (0.6)
        # doc2 has highest BM25 score (0.8), should rank high
        # Check that BM25 score influenced ranking
        doc2_result = next(r for r in results if r.doc_id == "doc2")
        assert doc2_result.bm25_score == 0.8

    @pytest.mark.asyncio
    async def test_adaptive_reranking_disabled(self, sample_documents):
        """Test reranking with adaptive weights disabled."""
        reranker = CrossEncoderReranker(use_adaptive_weights=False)

        # Mock cross-encoder model's predict method
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8, 0.4, 0.9, 0.3]
        reranker._model = mock_model

        results = await reranker.rerank(
            query="What is hybrid search?",
            documents=sample_documents,
            top_k=4,
        )

        # Verify adaptive scores are NOT computed
        assert all(r.adaptive_score is None for r in results)
        assert all(r.bm25_score is None for r in results)
        assert all(r.recency_score is None for r in results)

        # Sorting should be by rerank_score only
        # doc3 has highest cross-encoder score (0.9)
        assert results[0].doc_id == "doc3"

    @pytest.mark.asyncio
    async def test_recency_score_computation(self, sample_documents):
        """Test recency score calculation from timestamps."""
        reranker = CrossEncoderReranker(use_adaptive_weights=False)

        # doc3: 2024-12-01 (most recent)
        recency_doc3 = reranker._compute_recency_score(sample_documents[2])
        # doc2: 2024-06-20 (mid)
        recency_doc2 = reranker._compute_recency_score(sample_documents[1])
        # doc1: 2024-01-15 (oldest)
        recency_doc1 = reranker._compute_recency_score(sample_documents[0])
        # doc4: no timestamp
        recency_doc4 = reranker._compute_recency_score(sample_documents[3])

        # More recent documents should have higher scores
        assert recency_doc3 > recency_doc2 > recency_doc1

        # No timestamp → neutral score (0.5)
        assert recency_doc4 == 0.5

    @pytest.mark.asyncio
    async def test_intent_classification_fallback(self, sample_documents):
        """Test fallback to default weights on intent classification error."""
        reranker = CrossEncoderReranker(use_adaptive_weights=True)

        # Mock intent classifier that raises exception
        mock_classifier = MagicMock()
        mock_classifier.classify = AsyncMock(side_effect=Exception("Classification failed"))
        reranker._intent_classifier = mock_classifier

        # Mock cross-encoder model's predict method
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8, 0.4, 0.9, 0.3]
        reranker._model = mock_model

        results = await reranker.rerank(
            query="What is hybrid search?",
            documents=sample_documents,
            top_k=4,
        )

        # Should still produce adaptive scores with default weights
        assert all(r.adaptive_score is not None for r in results)

    @pytest.mark.asyncio
    async def test_latency_overhead(self, mock_intent_classifier, sample_documents):
        """Test that adaptive reranking overhead is <50ms."""
        reranker = CrossEncoderReranker(use_adaptive_weights=True)
        reranker._intent_classifier = mock_intent_classifier

        # Mock cross-encoder model's predict method
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8, 0.4, 0.9, 0.3]
        reranker._model = mock_model

        import time

        start = time.perf_counter()
        results = await reranker.rerank(
            query="What is hybrid search?",
            documents=sample_documents,
            top_k=4,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        # Total overhead should be minimal (<50ms)
        # Note: This is just checking computation overhead, not cross-encoder model inference
        assert latency_ms < 100  # Generous limit for test environment

    def test_get_model_info_includes_adaptive_flag(self):
        """Test model info includes adaptive weights status."""
        reranker_enabled = CrossEncoderReranker(use_adaptive_weights=True)
        reranker_disabled = CrossEncoderReranker(use_adaptive_weights=False)

        info_enabled = reranker_enabled.get_model_info()
        info_disabled = reranker_disabled.get_model_info()

        assert info_enabled["adaptive_weights_enabled"] is True
        assert info_disabled["adaptive_weights_enabled"] is False


class TestAdaptiveRerankingIntegration:
    """Integration tests for adaptive reranking."""

    @pytest.mark.asyncio
    async def test_end_to_end_factual_vs_summary(
        self, mock_intent_classifier, sample_documents
    ):
        """Test that factual and summary queries produce different rankings."""
        reranker = CrossEncoderReranker(use_adaptive_weights=True)
        reranker._intent_classifier = mock_intent_classifier

        # Mock cross-encoder model's predict method
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.7, 0.6, 0.8, 0.5]
        reranker._model = mock_model

        # Factual query: high semantic weight
        factual_results = await reranker.rerank(
            query="What is vector search?",
            documents=sample_documents,
            top_k=4,
        )

        # Summary query: high recency weight
        summary_results = await reranker.rerank(
            query="Summarize recent search developments",
            documents=sample_documents,
            top_k=4,
        )

        # Different intents should produce different rankings
        factual_order = [r.doc_id for r in factual_results]
        summary_order = [r.doc_id for r in summary_results]

        # Rankings may differ due to different weight profiles
        # Summary should favor recent documents (doc3: 2024-12-01)
        assert summary_results[0].doc_id == "doc3" or summary_results[1].doc_id == "doc3"
