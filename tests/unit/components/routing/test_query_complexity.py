"""Unit tests for Query Complexity Scorer.

Sprint 69 Feature 69.3: Model Selection Strategy
"""

import pytest

from src.components.routing.query_complexity import (
    ComplexityTier,
    QueryComplexityScore,
    QueryComplexityScorer,
)


class TestQueryComplexityScorer:
    """Test suite for QueryComplexityScorer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = QueryComplexityScorer()

    def test_simple_factual_query_fast_tier(self):
        """Test that simple factual queries are routed to FAST tier."""
        query = "What is RAG?"
        intent = "factual"

        result = self.scorer.score_query(query, intent)

        assert isinstance(result, QueryComplexityScore)
        assert result.tier == ComplexityTier.FAST
        assert result.score < 0.3
        assert "length" in result.factors
        assert "entities" in result.factors
        assert "intent" in result.factors
        assert "question" in result.factors

    def test_keyword_query_fast_tier(self):
        """Test that keyword queries are routed to FAST tier."""
        query = "API_KEY error 404"
        intent = "keyword"

        result = self.scorer.score_query(query, intent)

        assert result.tier == ComplexityTier.FAST
        assert result.score < 0.3  # Keyword intent has lowest complexity score

    def test_exploratory_query_balanced_tier(self):
        """Test that exploratory queries are routed to BALANCED tier."""
        query = "How does authentication work in microservices?"
        intent = "exploratory"

        result = self.scorer.score_query(query, intent)

        assert result.tier == ComplexityTier.BALANCED
        assert 0.3 <= result.score < 0.6

    def test_complex_multi_hop_query_advanced_tier(self):
        """Test that complex multi-hop queries are routed to ADVANCED tier."""
        query = "Explain how graph-based retrieval compares to vector search and when should I use each approach for entity-centric queries"
        intent = "multi_hop"

        result = self.scorer.score_query(query, intent)

        assert result.tier == ComplexityTier.ADVANCED
        assert result.score >= 0.6

    def test_summary_query_advanced_tier(self):
        """Test that summary queries tend toward ADVANCED tier."""
        query = "Summarize the main differences between vector search, BM25, and graph traversal approaches"
        intent = "summary"

        result = self.scorer.score_query(query, intent)

        # Summary queries should be BALANCED or ADVANCED depending on length
        assert result.tier in [ComplexityTier.BALANCED, ComplexityTier.ADVANCED]
        assert result.score >= 0.3

    def test_length_factor_scaling(self):
        """Test that query length correctly influences score."""
        short_query = "What is X?"
        long_query = " ".join(["word"] * 30)  # 30 words (max for normalization)

        short_result = self.scorer.score_query(short_query, "factual")
        long_result = self.scorer.score_query(long_query, "factual")

        # Longer query should have higher length factor
        assert long_result.factors["length"] > short_result.factors["length"]

    def test_entity_count_factor(self):
        """Test that entity count correctly influences score."""
        no_entities = "what is the definition"
        many_entities = "How does Microsoft Azure compare to Amazon AWS and Google Cloud"

        no_entities_result = self.scorer.score_query(no_entities, "factual")
        many_entities_result = self.scorer.score_query(many_entities, "factual")

        # More entities should have higher entity factor
        assert many_entities_result.factors["entities"] > no_entities_result.factors["entities"]

    def test_question_complexity_how_why(self):
        """Test that how/why questions have higher complexity."""
        how_query = "How does graph reasoning work?"
        what_query = "What is graph reasoning?"

        how_result = self.scorer.score_query(how_query, "exploratory")
        what_result = self.scorer.score_query(what_query, "factual")

        # How questions should have higher question complexity
        assert how_result.factors["question"] > what_result.factors["question"]

    def test_intent_factor_scores(self):
        """Test that different intents have appropriate scores."""
        query = "test query"  # Keep query constant

        keyword_result = self.scorer.score_query(query, "keyword")
        factual_result = self.scorer.score_query(query, "factual")
        exploratory_result = self.scorer.score_query(query, "exploratory")
        summary_result = self.scorer.score_query(query, "summary")
        graph_result = self.scorer.score_query(query, "graph_reasoning")

        # Verify intent score ordering (keyword < factual < exploratory < summary < graph)
        assert keyword_result.factors["intent"] < factual_result.factors["intent"]
        assert factual_result.factors["intent"] < exploratory_result.factors["intent"]
        assert exploratory_result.factors["intent"] < summary_result.factors["intent"]
        # Graph reasoning and multi-hop should have highest complexity (0.4)
        assert graph_result.factors["intent"] >= summary_result.factors["intent"]

    def test_score_validation(self):
        """Test that scores are within valid range [0, 1]."""
        queries = [
            ("What?", "factual"),
            ("How does X work?", "exploratory"),
            (" ".join(["word"] * 50), "multi_hop"),  # Very long query
        ]

        for query, intent in queries:
            result = self.scorer.score_query(query, intent)
            assert 0.0 <= result.score <= 1.0

    def test_factors_sum_to_score(self):
        """Test that individual factors sum to total score."""
        query = "How does graph-based retrieval work?"
        intent = "exploratory"

        result = self.scorer.score_query(query, intent)

        # Total score should equal sum of all factors
        factors_sum = sum(result.factors.values())
        assert abs(result.score - factors_sum) < 0.001  # Allow floating point precision

    def test_tier_thresholds(self):
        """Test that tier assignment respects thresholds."""
        # Create scorer with custom thresholds for testing
        scorer = QueryComplexityScorer(fast_threshold=0.2, advanced_threshold=0.7)

        # Low score → FAST
        low_score_query = "X"
        low_result = scorer.score_query(low_score_query, "keyword")
        if low_result.score < 0.2:
            assert low_result.tier == ComplexityTier.FAST

        # Mid score → BALANCED
        mid_query = "What is X and Y?"
        mid_result = scorer.score_query(mid_query, "factual")
        if 0.2 <= mid_result.score < 0.7:
            assert mid_result.tier == ComplexityTier.BALANCED

    def test_german_question_words(self):
        """Test that German question words are recognized."""
        german_queries = [
            ("Wie funktioniert RAG?", "exploratory"),  # How
            ("Warum ist das wichtig?", "exploratory"),  # Why
            ("Was ist das?", "factual"),  # What
            ("Wann wurde das erstellt?", "factual"),  # When
        ]

        for query, intent in german_queries:
            result = self.scorer.score_query(query, intent)
            # Should recognize question words and assign appropriate scores
            assert result.factors["question"] > 0.0

    def test_unknown_intent_fallback(self):
        """Test that unknown intents use default score."""
        query = "Test query"
        unknown_intent = "unknown_intent_type"

        result = self.scorer.score_query(query, unknown_intent)

        # Should not crash, should use default intent score (0.2)
        assert result.factors["intent"] > 0.0
        assert result.tier in [ComplexityTier.FAST, ComplexityTier.BALANCED, ComplexityTier.ADVANCED]

    def test_custom_weights(self):
        """Test scorer with custom factor weights."""
        # Create scorer that heavily weights intent
        custom_scorer = QueryComplexityScorer(
            length_weight=0.1,
            entity_weight=0.1,
            intent_weight=0.7,
            question_weight=0.1,
        )

        # Same query, different intents should have different tiers
        query = "test"
        keyword_result = custom_scorer.score_query(query, "keyword")
        multi_hop_result = custom_scorer.score_query(query, "multi_hop")

        # Multi-hop should have much higher score due to high intent weight
        assert multi_hop_result.score > keyword_result.score

    def test_empty_query(self):
        """Test handling of empty query."""
        result = self.scorer.score_query("", "factual")

        # Should not crash, should return valid result
        assert isinstance(result, QueryComplexityScore)
        assert result.tier in [ComplexityTier.FAST, ComplexityTier.BALANCED, ComplexityTier.ADVANCED]

    def test_very_long_query(self):
        """Test handling of very long query (>30 words)."""
        # Create query with 100 words (exceeds normalization threshold)
        long_query = " ".join(["word"] * 100)
        result = self.scorer.score_query(long_query, "factual")

        # Length factor should be capped at max weight (0.3)
        assert result.factors["length"] <= self.scorer.length_weight

    def test_consistency(self):
        """Test that same query produces same result."""
        query = "How does vector search work?"
        intent = "exploratory"

        result1 = self.scorer.score_query(query, intent)
        result2 = self.scorer.score_query(query, intent)

        assert result1.tier == result2.tier
        assert result1.score == result2.score
        assert result1.factors == result2.factors


class TestQueryComplexityScore:
    """Test suite for QueryComplexityScore dataclass."""

    def test_valid_score(self):
        """Test creation with valid score."""
        score = QueryComplexityScore(
            tier=ComplexityTier.BALANCED,
            score=0.5,
            factors={"length": 0.15, "entities": 0.15, "intent": 0.15, "question": 0.05},
        )
        assert score.tier == ComplexityTier.BALANCED
        assert score.score == 0.5

    def test_invalid_score_too_high(self):
        """Test that score > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
            QueryComplexityScore(
                tier=ComplexityTier.ADVANCED,
                score=1.5,  # Invalid
                factors={},
            )

    def test_invalid_score_negative(self):
        """Test that score < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
            QueryComplexityScore(
                tier=ComplexityTier.FAST,
                score=-0.1,  # Invalid
                factors={},
            )

    def test_immutable(self):
        """Test that QueryComplexityScore is immutable (frozen=True)."""
        score = QueryComplexityScore(
            tier=ComplexityTier.BALANCED,
            score=0.5,
            factors={},
        )

        with pytest.raises(AttributeError):
            score.tier = ComplexityTier.ADVANCED  # type: ignore


class TestComplexityTier:
    """Test suite for ComplexityTier enum."""

    def test_tier_values(self):
        """Test that tier values are correct."""
        assert ComplexityTier.FAST.value == "fast"
        assert ComplexityTier.BALANCED.value == "balanced"
        assert ComplexityTier.ADVANCED.value == "advanced"

    def test_tier_membership(self):
        """Test tier enum membership."""
        assert ComplexityTier.FAST in ComplexityTier
        assert ComplexityTier.BALANCED in ComplexityTier
        assert ComplexityTier.ADVANCED in ComplexityTier

    def test_tier_string_comparison(self):
        """Test that tier can be compared with strings."""
        assert ComplexityTier.FAST == "fast"
        assert ComplexityTier.BALANCED == "balanced"
        assert ComplexityTier.ADVANCED == "advanced"
