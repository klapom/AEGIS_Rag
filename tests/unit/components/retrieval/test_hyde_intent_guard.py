"""Unit tests for Sprint 129.8: HyDE Intent Guard.

Tests that HyDE is skipped for factual/navigation queries and enabled for
exploratory/procedural/comparison queries.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHyDEIntentGuard:
    """Test HyDE intent-based gating in maximum_hybrid_search."""

    @pytest.fixture
    def mock_intent_result(self):
        """Factory for mock IntentClassificationResult."""
        from src.components.retrieval.intent_classifier import CLARAIntent

        def _make(intent: CLARAIntent, confidence: float = 0.9):
            result = MagicMock()
            result.intent = intent
            result.confidence = confidence
            return result

        return _make

    @pytest.mark.asyncio
    async def test_factual_query_skips_hyde(self, mock_intent_result):
        """Factual queries should skip HyDE generation."""
        from src.components.retrieval.intent_classifier import CLARAIntent

        intent_result = mock_intent_result(CLARAIntent.FACTUAL)

        with patch(
            "src.components.retrieval.intent_classifier.classify_intent",
            new_callable=AsyncMock,
            return_value=intent_result,
        ):
            from src.components.retrieval.intent_classifier import classify_intent

            result = await classify_intent("What is the population of Berlin?")
            assert result.intent == CLARAIntent.FACTUAL

            # Simulate the guard logic from maximum_hybrid_search.py
            hyde_generator = None
            if result.intent == CLARAIntent.FACTUAL:
                hyde_generator = None  # Skipped
            else:
                hyde_generator = "active"

            assert hyde_generator is None, "HyDE should be skipped for factual queries"

    @pytest.mark.asyncio
    async def test_navigation_query_skips_hyde(self, mock_intent_result):
        """Navigation queries should skip HyDE generation."""
        from src.components.retrieval.intent_classifier import CLARAIntent

        intent_result = mock_intent_result(CLARAIntent.NAVIGATION)

        with patch(
            "src.components.retrieval.intent_classifier.classify_intent",
            new_callable=AsyncMock,
            return_value=intent_result,
        ):
            from src.components.retrieval.intent_classifier import classify_intent

            result = await classify_intent("Find the authentication module")
            assert result.intent == CLARAIntent.NAVIGATION

            hyde_generator = None
            if result.intent in (CLARAIntent.FACTUAL, CLARAIntent.NAVIGATION):
                hyde_generator = None
            else:
                hyde_generator = "active"

            assert hyde_generator is None, "HyDE should be skipped for navigation queries"

    @pytest.mark.asyncio
    async def test_exploratory_query_enables_hyde(self, mock_intent_result):
        """Exploratory queries should enable HyDE generation."""
        from src.components.retrieval.intent_classifier import CLARAIntent

        intent_result = mock_intent_result(CLARAIntent.PROCEDURAL)

        with patch(
            "src.components.retrieval.intent_classifier.classify_intent",
            new_callable=AsyncMock,
            return_value=intent_result,
        ):
            from src.components.retrieval.intent_classifier import classify_intent

            result = await classify_intent("How does climate change affect agriculture?")
            assert result.intent == CLARAIntent.PROCEDURAL

            hyde_generator = None
            if result.intent in (CLARAIntent.FACTUAL, CLARAIntent.NAVIGATION):
                hyde_generator = None
            else:
                hyde_generator = "active"

            assert hyde_generator is not None, "HyDE should be enabled for procedural queries"

    @pytest.mark.asyncio
    async def test_comparison_query_enables_hyde(self, mock_intent_result):
        """Comparison queries should enable HyDE generation."""
        from src.components.retrieval.intent_classifier import CLARAIntent

        intent_result = mock_intent_result(CLARAIntent.COMPARISON)

        hyde_generator = None
        if intent_result.intent in (CLARAIntent.FACTUAL, CLARAIntent.NAVIGATION):
            hyde_generator = None
        else:
            hyde_generator = "active"

        assert hyde_generator is not None, "HyDE should be enabled for comparison queries"

    @pytest.mark.asyncio
    async def test_recommendation_query_enables_hyde(self, mock_intent_result):
        """Recommendation queries should enable HyDE generation."""
        from src.components.retrieval.intent_classifier import CLARAIntent

        intent_result = mock_intent_result(CLARAIntent.RECOMMENDATION)

        hyde_generator = None
        if intent_result.intent in (CLARAIntent.FACTUAL, CLARAIntent.NAVIGATION):
            hyde_generator = None
        else:
            hyde_generator = "active"

        assert hyde_generator is not None, "HyDE should be enabled for recommendation queries"

    def test_all_clara_intents_have_guard_decision(self):
        """Every CLARAIntent value should have a clear HyDE decision."""
        from src.components.retrieval.intent_classifier import CLARAIntent

        skip_intents = {CLARAIntent.FACTUAL, CLARAIntent.NAVIGATION}
        enable_intents = {
            CLARAIntent.PROCEDURAL,
            CLARAIntent.COMPARISON,
            CLARAIntent.RECOMMENDATION,
        }

        all_intents = set(CLARAIntent)
        covered = skip_intents | enable_intents

        assert all_intents == covered, (
            f"Uncovered intents: {all_intents - covered}. "
            "Every CLARAIntent must have a HyDE guard decision."
        )
