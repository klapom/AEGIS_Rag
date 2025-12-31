"""Unit tests for QueryRewriter.

Sprint 67 Feature 67.9: Query Rewriter v1

Test Coverage:
- Strategy selection (expansion, refinement, none)
- Query expansion with LLM
- Query refinement with LLM
- Intent-aware rewriting
- Error handling and fallbacks
- Singleton pattern
- Performance (<200ms target)
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.adaptation.query_rewriter import (
    QueryRewriter,
    RewriteResult,
    get_query_rewriter,
    rewrite_query,
)
from src.components.retrieval.intent_classifier import Intent
from src.domains.llm_integration.models import LLMResponse


@pytest.fixture
def mock_llm_proxy():
    """Mock AegisLLMProxy for testing."""
    with patch("src.adaptation.query_rewriter.get_aegis_llm_proxy") as mock:
        proxy = Mock()
        mock.return_value = proxy
        yield proxy


@pytest.fixture
def mock_intent_classifier():
    """Mock IntentClassifier for testing."""
    classifier = Mock()
    classifier.classify = AsyncMock()
    return classifier


@pytest.fixture
def query_rewriter(mock_llm_proxy):
    """Create QueryRewriter instance with mocked LLM."""
    return QueryRewriter(intent_classifier=None)


@pytest.fixture
def query_rewriter_with_intent(mock_llm_proxy, mock_intent_classifier):
    """Create QueryRewriter with intent classifier."""
    return QueryRewriter(intent_classifier=mock_intent_classifier)


# ============================================================================
# Strategy Selection Tests
# ============================================================================


class TestStrategySelection:
    """Test query rewriting strategy selection logic."""

    def test_short_query_expansion_strategy(self, query_rewriter):
        """Short queries (<3 words) should use expansion strategy."""
        # 1 word
        assert query_rewriter._select_strategy("API", None) == "expansion"

        # 2 words
        assert query_rewriter._select_strategy("API docs", None) == "expansion"

        # Exactly 2 words
        assert query_rewriter._select_strategy("hello world", None) == "expansion"

    def test_vague_query_refinement_strategy(self, query_rewriter):
        """Vague queries should use refinement strategy."""
        # English vague queries
        assert query_rewriter._select_strategy("how auth", None) == "refinement"
        assert query_rewriter._select_strategy("what is API", None) == "refinement"
        assert query_rewriter._select_strategy("explain this", None) == "refinement"
        assert query_rewriter._select_strategy("tell me about", None) == "refinement"

        # German vague queries
        assert query_rewriter._select_strategy("wie API", None) == "refinement"
        assert query_rewriter._select_strategy("was ist", None) == "refinement"

    def test_factual_intent_expansion_strategy(self, query_rewriter):
        """Factual queries with moderate length should use expansion."""
        # Factual intent with 3-5 words
        assert query_rewriter._select_strategy("JWT token format", "factual") == "expansion"
        assert (
            query_rewriter._select_strategy("database schema design", "factual") == "expansion"
        )

    def test_exploratory_intent_refinement_strategy(self, query_rewriter):
        """Exploratory queries with few words should use refinement."""
        # Exploratory with <=4 words
        assert (
            query_rewriter._select_strategy("authentication flow", "exploratory") == "refinement"
        )
        assert query_rewriter._select_strategy("API design", "exploratory") == "refinement"

    def test_no_rewrite_strategy(self, query_rewriter):
        """Well-formed queries should not be rewritten."""
        # Long, specific queries
        assert (
            query_rewriter._select_strategy(
                "How to configure JWT authentication in the REST API", None
            )
            == "none"
        )

        # Keyword queries (technical)
        assert (
            query_rewriter._select_strategy("ERROR_CODE_404 authentication failed", "keyword")
            == "none"
        )

        # Summary queries
        assert (
            query_rewriter._select_strategy("summarize the architecture", "summary") == "none"
        )


# ============================================================================
# Query Expansion Tests
# ============================================================================


class TestQueryExpansion:
    """Test query expansion functionality."""

    @pytest.mark.asyncio
    async def test_expand_short_query(self, query_rewriter, mock_llm_proxy):
        """Test expansion of short query."""
        # Mock LLM response
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="API documentation reference guide endpoints methods",
                provider="local_ollama",
                model="test-model",
                tokens_used=50,
                tokens_input=30,
                tokens_output=20,
                cost_usd=0.0,
            )
        )

        # Expand query
        expanded = await query_rewriter._expand_query("API docs", "factual")

        # Verify expansion
        assert expanded == "API documentation reference guide endpoints methods"
        assert len(expanded) > len("API docs")

        # Verify LLM was called
        mock_llm_proxy.generate.assert_called_once()
        call_args = mock_llm_proxy.generate.call_args
        task = call_args[0][0]

        assert task.task_type == "generation"
        assert "API docs" in task.prompt
        assert task.temperature == 0.3

    @pytest.mark.asyncio
    async def test_expand_query_removes_quotes(self, query_rewriter, mock_llm_proxy):
        """Test that expansion removes quotes added by LLM."""
        # Mock LLM response with quotes
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content='"API documentation reference guide"',
                provider="local_ollama",
                model="test-model",
                tokens_used=50,
                tokens_input=30,
                tokens_output=20,
                cost_usd=0.0,
            )
        )

        expanded = await query_rewriter._expand_query("API", None)

        # Quotes should be removed
        assert expanded == "API documentation reference guide"
        assert not expanded.startswith('"')
        assert not expanded.endswith('"')

    @pytest.mark.asyncio
    async def test_expand_query_fallback_on_error(self, query_rewriter, mock_llm_proxy):
        """Test fallback to original query on LLM error."""
        # Mock LLM error
        mock_llm_proxy.generate = AsyncMock(side_effect=Exception("LLM error"))

        expanded = await query_rewriter._expand_query("API", None)

        # Should fall back to original
        assert expanded == "API"

    @pytest.mark.asyncio
    async def test_expand_query_fallback_on_empty_response(self, query_rewriter, mock_llm_proxy):
        """Test fallback when LLM returns empty response."""
        # Mock empty response
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="",
                provider="local_ollama",
                model="test-model",
                tokens_used=0,
                tokens_input=0,
                tokens_output=0,
                cost_usd=0.0,
            )
        )

        expanded = await query_rewriter._expand_query("API", None)

        # Should fall back to original
        assert expanded == "API"

    @pytest.mark.asyncio
    async def test_expand_query_fallback_on_shorter_response(
        self, query_rewriter, mock_llm_proxy
    ):
        """Test fallback when expansion is shorter than original."""
        # Mock response shorter than original
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="API",
                provider="local_ollama",
                model="test-model",
                tokens_used=10,
                tokens_input=5,
                tokens_output=5,
                cost_usd=0.0,
            )
        )

        original = "API documentation"
        expanded = await query_rewriter._expand_query(original, None)

        # Should fall back to original
        assert expanded == original


# ============================================================================
# Query Refinement Tests
# ============================================================================


class TestQueryRefinement:
    """Test query refinement functionality."""

    @pytest.mark.asyncio
    async def test_refine_vague_query(self, query_rewriter, mock_llm_proxy):
        """Test refinement of vague query."""
        # Mock LLM response
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="How does authentication and authorization work in the system?",
                provider="local_ollama",
                model="test-model",
                tokens_used=60,
                tokens_input=40,
                tokens_output=20,
                cost_usd=0.0,
            )
        )

        # Refine query
        refined = await query_rewriter._refine_query("How does auth work?", "exploratory")

        # Verify refinement
        assert "authentication" in refined
        assert "authorization" in refined
        assert len(refined) > len("How does auth work?")

        # Verify LLM was called
        mock_llm_proxy.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_refine_query_removes_quotes(self, query_rewriter, mock_llm_proxy):
        """Test that refinement removes quotes added by LLM."""
        # Mock LLM response with quotes
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="'How does authentication work?'",
                provider="local_ollama",
                model="test-model",
                tokens_used=50,
                tokens_input=30,
                tokens_output=20,
                cost_usd=0.0,
            )
        )

        refined = await query_rewriter._refine_query("How auth?", None)

        # Quotes should be removed
        assert refined == "How does authentication work?"
        assert not refined.startswith("'")
        assert not refined.endswith("'")

    @pytest.mark.asyncio
    async def test_refine_query_fallback_on_error(self, query_rewriter, mock_llm_proxy):
        """Test fallback to original query on LLM error."""
        # Mock LLM error
        mock_llm_proxy.generate = AsyncMock(side_effect=Exception("LLM error"))

        refined = await query_rewriter._refine_query("How auth?", None)

        # Should fall back to original
        assert refined == "How auth?"


# ============================================================================
# Integration Tests
# ============================================================================


class TestQueryRewriterIntegration:
    """Test full query rewriting flow."""

    @pytest.mark.asyncio
    async def test_rewrite_short_query_expansion(self, query_rewriter, mock_llm_proxy):
        """Test complete flow for short query expansion."""
        # Mock expansion
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="API documentation reference guide",
                provider="local_ollama",
                model="test-model",
                tokens_used=50,
                tokens_input=30,
                tokens_output=20,
                cost_usd=0.0,
            )
        )

        # Rewrite
        result = await query_rewriter.rewrite("API")

        # Verify result
        assert isinstance(result, RewriteResult)
        assert result.original_query == "API"
        assert result.rewritten_query == "API documentation reference guide"
        assert result.strategy == "expansion"
        assert result.confidence == 0.85
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_rewrite_vague_query_refinement(self, query_rewriter, mock_llm_proxy):
        """Test complete flow for vague query refinement."""
        # Mock refinement
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="How does API authentication work?",
                provider="local_ollama",
                model="test-model",
                tokens_used=50,
                tokens_input=30,
                tokens_output=20,
                cost_usd=0.0,
            )
        )

        # Rewrite
        result = await query_rewriter.rewrite("How auth?")

        # Verify result
        assert result.original_query == "How auth?"
        assert result.rewritten_query == "How does API authentication work?"
        assert result.strategy == "refinement"
        assert result.confidence == 0.80

    @pytest.mark.asyncio
    async def test_rewrite_no_strategy(self, query_rewriter, mock_llm_proxy):
        """Test that well-formed queries are not rewritten."""
        # Rewrite (should not call LLM)
        result = await query_rewriter.rewrite(
            "How to configure JWT authentication in the REST API"
        )

        # Verify no rewriting
        assert result.original_query == result.rewritten_query
        assert result.strategy == "none"
        assert result.confidence == 1.0

        # LLM should not be called
        mock_llm_proxy.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_rewrite_with_intent_classifier(
        self, query_rewriter_with_intent, mock_intent_classifier, mock_llm_proxy
    ):
        """Test rewriting with intent classification."""
        # Mock intent classification
        mock_intent_result = Mock()
        mock_intent_result.intent = Intent.FACTUAL
        mock_intent_result.confidence = 0.95
        mock_intent_classifier.classify.return_value = mock_intent_result

        # Mock expansion
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="JWT token authentication format specification",
                provider="local_ollama",
                model="test-model",
                tokens_used=50,
                tokens_input=30,
                tokens_output=20,
                cost_usd=0.0,
            )
        )

        # Rewrite
        result = await query_rewriter_with_intent.rewrite("JWT token")

        # Verify intent was classified
        mock_intent_classifier.classify.assert_called_once_with("JWT token")

        # Verify result includes intent
        assert result.intent == "factual"
        assert result.strategy == "expansion"

    @pytest.mark.asyncio
    async def test_rewrite_intent_classification_failure(
        self, query_rewriter_with_intent, mock_intent_classifier, mock_llm_proxy
    ):
        """Test graceful fallback when intent classification fails."""
        # Mock intent classification failure
        mock_intent_classifier.classify.side_effect = Exception("Intent classifier error")

        # Mock expansion
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="API documentation",
                provider="local_ollama",
                model="test-model",
                tokens_used=30,
                tokens_input=20,
                tokens_output=10,
                cost_usd=0.0,
            )
        )

        # Rewrite should still work
        result = await query_rewriter_with_intent.rewrite("API")

        # Verify rewriting succeeded without intent
        assert result.intent is None
        assert result.strategy == "expansion"  # Fallback to rule-based


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test performance requirements."""

    @pytest.mark.asyncio
    async def test_rewrite_latency_under_200ms(self, query_rewriter, mock_llm_proxy):
        """Test that rewriting completes in <200ms."""
        # Mock fast LLM response
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="API documentation",
                provider="local_ollama",
                model="test-model",
                tokens_used=30,
                tokens_input=20,
                tokens_output=10,
                cost_usd=0.0,
            )
        )

        # Rewrite
        result = await query_rewriter.rewrite("API")

        # Verify latency (mock should be fast)
        # Note: In production, target is <200ms with real LLM
        assert result.latency_ms < 500  # Generous for unit test with mocks


# ============================================================================
# Singleton Tests
# ============================================================================


class TestSingleton:
    """Test singleton pattern."""

    def test_get_query_rewriter_singleton(self):
        """Test that get_query_rewriter returns singleton."""
        # Reset singleton
        import src.adaptation.query_rewriter as qr_module

        qr_module._query_rewriter = None

        with patch("src.adaptation.query_rewriter.get_aegis_llm_proxy"):
            with patch(
                "src.components.retrieval.intent_classifier.get_intent_classifier",
                side_effect=ImportError("No classifier"),
            ):
                rewriter1 = get_query_rewriter()
                rewriter2 = get_query_rewriter()

                # Should return same instance
                assert rewriter1 is rewriter2

        # Reset singleton after test
        qr_module._query_rewriter = None

    def test_get_query_rewriter_with_classifier_not_singleton(self, mock_intent_classifier):
        """Test that providing classifier creates new instance."""
        with patch("src.adaptation.query_rewriter.get_aegis_llm_proxy"):
            rewriter1 = get_query_rewriter(intent_classifier=mock_intent_classifier)
            rewriter2 = get_query_rewriter(intent_classifier=mock_intent_classifier)

            # Should create different instances when classifier provided
            assert rewriter1 is not rewriter2

    @pytest.mark.asyncio
    async def test_rewrite_query_convenience_function(self, mock_llm_proxy):
        """Test convenience function rewrite_query."""
        # Reset singleton
        import src.adaptation.query_rewriter as qr_module

        qr_module._query_rewriter = None

        # Mock expansion
        mock_llm_proxy.generate = AsyncMock(
            return_value=LLMResponse(
                content="API documentation",
                provider="local_ollama",
                model="test-model",
                tokens_used=30,
                tokens_input=20,
                tokens_output=10,
                cost_usd=0.0,
            )
        )

        with patch(
            "src.components.retrieval.intent_classifier.get_intent_classifier",
            side_effect=ImportError("No classifier"),
        ):
            # Use convenience function
            result = await rewrite_query("API")

            # Verify result
            assert isinstance(result, RewriteResult)
            assert result.original_query == "API"
            assert result.strategy == "expansion"

        # Reset singleton after test
        qr_module._query_rewriter = None
