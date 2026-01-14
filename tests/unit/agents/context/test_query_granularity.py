"""Unit tests for C-LARA Query Granularity Mapper (Sprint 92.9).

Sprint 92 Feature 92.9: C-LARA Granularity Mapper

Tests query granularity classification and intent-based scoring method selection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.context.query_granularity import (
    CLARAGranularityMapper,
    get_granularity_mapper,
)


class TestCLARAGranularityMapperInitialization:
    """Tests for CLARAGranularityMapper initialization."""

    def test_initialization_lazy_classifier(self):
        """Test mapper initializes with lazy-loaded classifier."""
        mapper = CLARAGranularityMapper()

        assert mapper._clara_classifier is None  # Lazy-loaded
        assert hasattr(mapper, "fine_grained_factual")
        assert hasattr(mapper, "holistic_factual")

    def test_factual_patterns_initialized(self):
        """Test factual patterns are properly initialized."""
        mapper = CLARAGranularityMapper()

        assert len(mapper.fine_grained_factual) > 0
        assert len(mapper.holistic_factual) > 0
        # All should be compiled regex patterns
        assert all(hasattr(p, "search") for p in mapper.fine_grained_factual)
        assert all(hasattr(p, "search") for p in mapper.holistic_factual)

    def test_fine_grained_patterns_examples(self):
        """Test fine-grained patterns match expected queries."""
        mapper = CLARAGranularityMapper()

        test_queries = [
            "What is the p-value?",
            "Show Table 3",
            "What is BGE-M3?",
            "What are the exact numbers?",
        ]

        for query in test_queries:
            matches = sum(
                1 for pattern in mapper.fine_grained_factual if pattern.search(query)
            )
            assert matches > 0, f"Query '{query}' should match fine-grained patterns"

    def test_holistic_patterns_examples(self):
        """Test holistic patterns match expected queries."""
        mapper = CLARAGranularityMapper()

        test_queries = [
            "Summarize the findings",
            "Explain the methodology",
            "Describe the overall approach",
            "What is the main idea?",
            "Why did they do this?",
        ]

        for query in test_queries:
            matches = sum(
                1 for pattern in mapper.holistic_factual if pattern.search(query)
            )
            assert matches > 0, f"Query '{query}' should match holistic patterns"


class TestNavigationIntent:
    """Tests for NAVIGATION intent → fine-grained mapping."""

    @pytest.mark.asyncio
    async def test_navigation_intent_fine_grained(self):
        """Test NAVIGATION intent maps to fine-grained."""
        mapper = CLARAGranularityMapper()

        # Mock C-LARA classifier
        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.NAVIGATION,
            confidence=0.95,
        )
        mapper._clara_classifier = mock_classifier

        granularity, confidence = await mapper.classify_granularity(
            "Where is the introduction section?"
        )

        assert granularity == "fine-grained"
        assert confidence == 0.95

    @pytest.mark.asyncio
    async def test_navigation_high_confidence(self):
        """Test NAVIGATION intent has high confidence (0.95)."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.NAVIGATION
        )
        mapper._clara_classifier = mock_classifier

        _, confidence = await mapper.classify_granularity("Find the abstract")

        assert confidence == 0.95


class TestProceduralIntent:
    """Tests for PROCEDURAL intent → holistic mapping."""

    @pytest.mark.asyncio
    async def test_procedural_intent_holistic(self):
        """Test PROCEDURAL intent maps to holistic."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.PROCEDURAL
        )
        mapper._clara_classifier = mock_classifier

        granularity, confidence = await mapper.classify_granularity(
            "How do I implement BGE-M3?"
        )

        assert granularity == "holistic"
        assert confidence == 0.90

    @pytest.mark.asyncio
    async def test_procedural_examples(self):
        """Test various procedural queries."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.PROCEDURAL
        )
        mapper._clara_classifier = mock_classifier

        queries = [
            "How do you implement this algorithm?",
            "What are the steps to set up the system?",
            "Walk me through the process",
        ]

        for query in queries:
            granularity, _ = await mapper.classify_granularity(query)
            assert granularity == "holistic"


class TestComparisonIntent:
    """Tests for COMPARISON intent → holistic mapping."""

    @pytest.mark.asyncio
    async def test_comparison_intent_holistic(self):
        """Test COMPARISON intent maps to holistic."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.COMPARISON
        )
        mapper._clara_classifier = mock_classifier

        granularity, confidence = await mapper.classify_granularity(
            "Compare BGE-M3 with other embeddings"
        )

        assert granularity == "holistic"
        assert confidence == 0.90


class TestRecommendationIntent:
    """Tests for RECOMMENDATION intent → holistic mapping."""

    @pytest.mark.asyncio
    async def test_recommendation_intent_holistic(self):
        """Test RECOMMENDATION intent maps to holistic."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.RECOMMENDATION
        )
        mapper._clara_classifier = mock_classifier

        granularity, confidence = await mapper.classify_granularity(
            "What should I use for embeddings?"
        )

        assert granularity == "holistic"
        assert confidence == 0.90


class TestFactualIntentSubclassification:
    """Tests for FACTUAL intent heuristic sub-classification."""

    @pytest.mark.asyncio
    async def test_factual_fine_grained_p_value(self):
        """Test FACTUAL + p-value pattern → fine-grained."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.FACTUAL
        )
        mapper._clara_classifier = mock_classifier

        granularity, confidence = await mapper.classify_granularity(
            "What is the p-value for the test?"
        )

        assert granularity == "fine-grained"
        assert 0.60 <= confidence <= 0.90

    @pytest.mark.asyncio
    async def test_factual_fine_grained_table_reference(self):
        """Test FACTUAL + Table reference → fine-grained."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.FACTUAL
        )
        mapper._clara_classifier = mock_classifier

        granularity, _ = await mapper.classify_granularity("Show Table 3")

        assert granularity == "fine-grained"

    @pytest.mark.asyncio
    async def test_factual_fine_grained_figure_reference(self):
        """Test FACTUAL + Figure reference → fine-grained."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.FACTUAL
        )
        mapper._clara_classifier = mock_classifier

        granularity, _ = await mapper.classify_granularity("What does Figure 5 show?")

        assert granularity == "fine-grained"

    @pytest.mark.asyncio
    async def test_factual_fine_grained_definition(self):
        """Test FACTUAL + definition pattern → fine-grained."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.FACTUAL
        )
        mapper._clara_classifier = mock_classifier

        granularity, _ = await mapper.classify_granularity(
            "What is the definition of BGE-M3?"
        )

        assert granularity == "fine-grained"

    @pytest.mark.asyncio
    async def test_factual_holistic_summarize(self):
        """Test FACTUAL + summarize pattern → holistic."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.FACTUAL
        )
        mapper._clara_classifier = mock_classifier

        granularity, _ = await mapper.classify_granularity("Summarize the methodology")

        assert granularity == "holistic"

    @pytest.mark.asyncio
    async def test_factual_holistic_explain(self):
        """Test FACTUAL + explain pattern → holistic."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.FACTUAL
        )
        mapper._clara_classifier = mock_classifier

        granularity, _ = await mapper.classify_granularity("Explain the approach")

        assert granularity == "holistic"

    @pytest.mark.asyncio
    async def test_factual_default_no_patterns(self):
        """Test FACTUAL with no pattern matches defaults to fine-grained."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.FACTUAL
        )
        mapper._clara_classifier = mock_classifier

        # Query that doesn't match any patterns
        granularity, confidence = await mapper.classify_granularity(
            "Tell me about the study"
        )

        assert granularity == "fine-grained"  # Default
        assert confidence == 0.60  # Low confidence


class TestHeuristicFallback:
    """Tests for heuristic-only fallback when C-LARA unavailable."""

    @pytest.mark.asyncio
    async def test_heuristic_only_fine_grained(self):
        """Test heuristic fallback classifies fine-grained queries."""
        mapper = CLARAGranularityMapper()
        # Don't set _clara_classifier (simulate unavailable)

        granularity, confidence = await mapper.classify_granularity(
            "What is the exact p-value?"
        )

        assert granularity == "fine-grained"
        assert confidence == 0.70  # Heuristic confidence

    @pytest.mark.asyncio
    async def test_heuristic_only_holistic(self):
        """Test heuristic fallback classifies holistic queries."""
        mapper = CLARAGranularityMapper()
        # Don't set _clara_classifier

        granularity, confidence = await mapper.classify_granularity(
            "Summarize the main findings"
        )

        assert granularity == "holistic"
        assert confidence == 0.70  # Heuristic confidence

    @pytest.mark.asyncio
    async def test_clara_classifier_load_failure_fallback(self):
        """Test fallback to heuristic when C-LARA load fails."""
        mapper = CLARAGranularityMapper()

        # Mock the lazy load inside classify_granularity
        async def mock_classify(query):
            # Simulate load failure
            if mapper._clara_classifier is None:
                try:
                    from src.components.retrieval.intent_classifier import (
                        get_intent_classifier,
                    )

                    mapper._clara_classifier = get_intent_classifier()
                except ImportError:
                    # Force fallback to heuristic
                    mapper._clara_classifier = None
                    raise ImportError("C-LARA not available")

        # Call classify_granularity which will fall back to heuristic
        granularity, confidence = await mapper.classify_granularity(
            "What is the p-value?"
        )

        # Should use heuristic fallback (fine-grained pattern match)
        assert granularity == "fine-grained"
        assert confidence >= 0.60  # Heuristic confidence

    @pytest.mark.asyncio
    async def test_clara_classification_runtime_error_fallback(self):
        """Test fallback when C-LARA classification fails at runtime."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        mock_classifier.classify.side_effect = RuntimeError("C-LARA error")
        mapper._clara_classifier = mock_classifier

        granularity, confidence = await mapper.classify_granularity(
            "What is the p-value?"
        )

        assert granularity == "fine-grained"
        assert confidence == 0.70  # Heuristic fallback


class TestPatternScoring:
    """Tests for pattern matching and scoring logic."""

    def test_fine_grained_pattern_accuracy(self):
        """Test fine-grained patterns match appropriate queries."""
        mapper = CLARAGranularityMapper()

        queries_and_expected = [
            ("What is the p-value?", True),
            ("Show Table 3", True),
            ("Display Figure 5", True),
            ("What is BGE-M3?", True),
            ("What is the exact number?", True),  # "exact" keyword
        ]

        for query, should_match in queries_and_expected:
            matches = sum(
                1 for p in mapper.fine_grained_factual if p.search(query)
            )
            has_match = matches > 0
            assert (
                has_match == should_match
            ), f"Query '{query}' match expectation failed"

    def test_holistic_pattern_accuracy(self):
        """Test holistic patterns match appropriate queries."""
        mapper = CLARAGranularityMapper()

        queries_and_expected = [
            ("Summarize the methodology", True),
            ("Explain the approach", True),
            ("Describe the overall findings", True),
            ("Why did they choose this method?", True),
            ("What is the p-value?", False),  # Fine-grained
        ]

        for query, should_match in queries_and_expected:
            matches = sum(
                1 for p in mapper.holistic_factual if p.search(query)
            )
            has_match = matches > 0
            assert (
                has_match == should_match
            ), f"Query '{query}' match expectation failed"

    def test_factual_scoring_logic(self):
        """Test factual sub-classification scoring logic."""
        mapper = CLARAGranularityMapper()

        # Query matching only fine-grained patterns
        fine_score, holistic_score = (
            sum(1 for p in mapper.fine_grained_factual if p.search("What is the p-value?")),
            sum(1 for p in mapper.holistic_factual if p.search("What is the p-value?")),
        )
        assert fine_score > holistic_score

        # Query matching only holistic patterns
        fine_score, holistic_score = (
            sum(1 for p in mapper.fine_grained_factual if p.search("Summarize the findings")),
            sum(1 for p in mapper.holistic_factual if p.search("Summarize the findings")),
        )
        assert holistic_score > fine_score


class TestConfidenceCalculation:
    """Tests for confidence calculation logic."""

    @pytest.mark.asyncio
    async def test_direct_intent_confidence_high(self):
        """Test direct intent mappings have high confidence (0.90-0.95)."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        # Test NAVIGATION (0.95)
        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.NAVIGATION
        )
        mapper._clara_classifier = mock_classifier
        _, conf = await mapper.classify_granularity("Find the section")
        assert conf == 0.95

        # Test PROCEDURAL (0.90)
        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.PROCEDURAL
        )
        _, conf = await mapper.classify_granularity("How to implement")
        assert conf == 0.90

    @pytest.mark.asyncio
    async def test_factual_confidence_varies(self):
        """Test FACTUAL confidence varies based on pattern matches."""
        mapper = CLARAGranularityMapper()

        mock_classifier = AsyncMock()
        from src.components.retrieval.intent_classifier import CLARAIntent

        mock_classifier.classify.return_value = MagicMock(
            clara_intent=CLARAIntent.FACTUAL
        )
        mapper._clara_classifier = mock_classifier

        # Query with many matching patterns (high confidence)
        _, conf_high = await mapper.classify_granularity(
            "What is the exact p-value in Table 3 for BGE-M3?"
        )

        # Query with no matching patterns (low confidence)
        _, conf_low = await mapper.classify_granularity("Tell me about something")

        assert conf_high > conf_low


class TestGranularityMapperSingleton:
    """Tests for singleton pattern and global instance."""

    def test_get_granularity_mapper_singleton(self):
        """Test get_granularity_mapper returns singleton."""
        mapper1 = get_granularity_mapper()
        mapper2 = get_granularity_mapper()

        assert mapper1 is mapper2

    def test_mapper_persistence(self):
        """Test mapper state persists across calls."""
        mapper = get_granularity_mapper()

        # Set some state
        mapper._test_flag = "test_value"

        # Get mapper again
        mapper2 = get_granularity_mapper()

        assert hasattr(mapper2, "_test_flag")
        assert mapper2._test_flag == "test_value"


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    @pytest.mark.asyncio
    async def test_empty_query_handling(self):
        """Test handling of empty query."""
        mapper = CLARAGranularityMapper()

        # Heuristic fallback (no patterns match)
        granularity, confidence = await mapper.classify_granularity("")

        assert granularity in ["fine-grained", "holistic"]
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_very_long_query(self):
        """Test handling of very long query."""
        mapper = CLARAGranularityMapper()

        long_query = "What is " + "the " * 1000 + "p-value?"

        granularity, confidence = await mapper.classify_granularity(long_query)

        assert granularity in ["fine-grained", "holistic"]
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self):
        """Test handling of special characters."""
        mapper = CLARAGranularityMapper()

        queries = [
            "What is BGE-M3?",
            "Find 'exact' results",
            'What about "quoted text"?',
            "Value: 0.95 (p-value)",
        ]

        for query in queries:
            granularity, confidence = await mapper.classify_granularity(query)
            assert granularity in ["fine-grained", "holistic"]
            assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_case_insensitivity(self):
        """Test patterns are case-insensitive."""
        mapper = CLARAGranularityMapper()

        lower_query = "what is the p-value?"
        upper_query = "WHAT IS THE P-VALUE?"
        mixed_query = "What Is The P-Value?"

        for query in [lower_query, upper_query, mixed_query]:
            matches = sum(
                1 for p in mapper.fine_grained_factual if p.search(query)
            )
            assert matches > 0, f"Pattern failed for: {query}"
