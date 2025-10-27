"""Unit tests for RelevanceScorer (Feature 9.3).

Tests:
1. test_relevance_scorer_initialization - Validate scorer configuration
2. test_frequency_score_calculation - Test logarithmic frequency scoring
3. test_recency_score_calculation - Test exponential decay for recency
4. test_comprehensive_score_calculation - Test weighted combination
5. test_score_from_metadata - Test metadata-based scoring
"""

import math
from datetime import datetime, timedelta

import pytest

from src.components.memory.relevance_scorer import RelevanceScore, RelevanceScorer


class TestRelevanceScorer:
    """Test suite for RelevanceScorer."""

    def test_relevance_scorer_initialization(self):
        """Test 1: Validate scorer initialization and weight validation."""
        # Valid initialization
        scorer = RelevanceScorer(
            frequency_weight=0.3,
            recency_weight=0.4,
            feedback_weight=0.3,
        )
        assert scorer.frequency_weight == 0.3
        assert scorer.recency_weight == 0.4
        assert scorer.feedback_weight == 0.3

        # Test weight validation - weights must sum to 1.0
        with pytest.raises(ValueError, match="must sum to 1.0"):
            RelevanceScorer(
                frequency_weight=0.5,
                recency_weight=0.5,
                feedback_weight=0.5,  # Sum = 1.5, invalid
            )

        # Test individual weight validation
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            RelevanceScorer(
                frequency_weight=-0.1,  # Negative, invalid
                recency_weight=0.6,
                feedback_weight=0.5,
            )

        # Test custom parameters
        scorer = RelevanceScorer(
            max_access_count=200,
            decay_half_life_days=60.0,
        )
        assert scorer.max_access_count == 200
        assert scorer.decay_half_life_days == 60.0

    def test_frequency_score_calculation(self):
        """Test 2: Test logarithmic frequency scoring."""
        scorer = RelevanceScorer(max_access_count=100)

        # Zero accesses
        assert scorer.calculate_frequency_score(0) == 0.0

        # Single access
        score_1 = scorer.calculate_frequency_score(1)
        assert 0.0 < score_1 < 1.0

        # Multiple accesses (logarithmic scale)
        score_10 = scorer.calculate_frequency_score(10)
        score_50 = scorer.calculate_frequency_score(50)
        score_100 = scorer.calculate_frequency_score(100)

        # Verify logarithmic growth (diminishing returns)
        assert score_10 > score_1
        assert score_50 > score_10
        assert score_100 > score_50

        # At max_access_count, score should be 1.0
        assert math.isclose(score_100, 1.0, abs_tol=0.01)

        # Beyond max_access_count, capped at 1.0
        score_200 = scorer.calculate_frequency_score(200)
        assert score_200 == 1.0

    def test_recency_score_calculation(self):
        """Test 3: Test exponential decay for recency scoring."""
        scorer = RelevanceScorer(decay_half_life_days=30.0)

        # Just created (0 days old)
        assert scorer.calculate_recency_score(0.0) == 1.0

        # Recent (1 day old)
        score_1day = scorer.calculate_recency_score(1.0)
        assert 0.9 < score_1day < 1.0

        # Half-life (30 days old) - should be ~0.5
        score_30days = scorer.calculate_recency_score(30.0)
        assert math.isclose(score_30days, 0.5, abs_tol=0.01)

        # Old (90 days) - significant decay
        score_90days = scorer.calculate_recency_score(90.0)
        assert 0.0 < score_90days < 0.2

        # Very old (365 days) - near zero
        score_1year = scorer.calculate_recency_score(365.0)
        assert 0.0 < score_1year < 0.01

        # Test negative days (invalid)
        with pytest.raises(ValueError, match="must be non-negative"):
            scorer.calculate_recency_score(-1.0)

    def test_comprehensive_score_calculation(self):
        """Test 4: Test weighted combination of all scores."""
        scorer = RelevanceScorer(
            frequency_weight=0.3,
            recency_weight=0.4,
            feedback_weight=0.3,
            max_access_count=100,
            decay_half_life_days=30.0,
        )

        # Recent, frequently accessed memory with good rating
        now = datetime.utcnow()
        stored_at = now - timedelta(days=1)  # 1 day old

        score = scorer.calculate_score(
            access_count=50,
            stored_at=stored_at,
            user_rating=0.9,
            current_time=now,
        )

        # Validate score structure
        assert isinstance(score, RelevanceScore)
        assert 0.0 <= score.frequency_score <= 1.0
        assert 0.0 <= score.recency_score <= 1.0
        assert 0.0 <= score.user_feedback <= 1.0
        assert 0.0 <= score.total_score <= 1.0

        # Total score should be weighted average
        expected_total = (
            score.frequency_score * 0.3 + score.recency_score * 0.4 + score.user_feedback * 0.3
        )
        assert math.isclose(score.total_score, expected_total, abs_tol=0.001)

        # High-value memory should have high score
        assert score.total_score > 0.7

        # Test with old, rarely accessed memory
        old_stored_at = now - timedelta(days=100)
        old_score = scorer.calculate_score(
            access_count=1,
            stored_at=old_stored_at,
            user_rating=0.3,
            current_time=now,
        )

        # Should have lower score
        assert old_score.total_score < score.total_score
        assert old_score.total_score < 0.3

        # Test ISO format timestamp string
        iso_timestamp = stored_at.isoformat()
        score_from_iso = scorer.calculate_score(
            access_count=50,
            stored_at=iso_timestamp,
            user_rating=0.9,
            current_time=now,
        )
        assert math.isclose(score_from_iso.total_score, score.total_score, abs_tol=0.01)

        # Test future timestamp (invalid)
        future_time = now + timedelta(days=1)
        with pytest.raises(ValueError, match="in the future"):
            scorer.calculate_score(
                access_count=10,
                stored_at=future_time,
                current_time=now,
            )

        # Test invalid user rating
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            scorer.calculate_score(
                access_count=10,
                stored_at=stored_at,
                user_rating=1.5,  # Invalid
                current_time=now,
            )

    def test_score_from_metadata(self):
        """Test 5: Test scoring from metadata dictionary."""
        scorer = RelevanceScorer()

        now = datetime.utcnow()
        metadata = {
            "access_count": 25,
            "stored_at": (now - timedelta(days=5)).isoformat(),
            "user_rating": 0.8,
        }

        score = scorer.calculate_score_from_metadata(metadata, current_time=now)

        assert isinstance(score, RelevanceScore)
        assert score.user_feedback == 0.8
        assert score.total_score > 0.5

        # Test without user_rating (should default to 0.5)
        metadata_no_rating = {
            "access_count": 25,
            "stored_at": (now - timedelta(days=5)).isoformat(),
        }

        score_no_rating = scorer.calculate_score_from_metadata(metadata_no_rating, current_time=now)
        assert score_no_rating.user_feedback == 0.5

        # Test missing required fields
        with pytest.raises(ValueError, match="must contain 'access_count'"):
            scorer.calculate_score_from_metadata({"stored_at": now.isoformat()})

        with pytest.raises(ValueError, match="must contain 'stored_at'"):
            scorer.calculate_score_from_metadata({"access_count": 10})


class TestRelevanceScore:
    """Test suite for RelevanceScore dataclass."""

    def test_relevance_score_validation(self):
        """Test RelevanceScore validation."""
        # Valid score
        score = RelevanceScore(
            frequency_score=0.5,
            recency_score=0.8,
            user_feedback=0.6,
            total_score=0.65,
        )
        assert score.frequency_score == 0.5
        assert score.total_score == 0.65

        # Invalid score (out of range)
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            RelevanceScore(
                frequency_score=1.5,  # Invalid
                recency_score=0.8,
                user_feedback=0.6,
                total_score=0.9,
            )

        with pytest.raises(ValueError, match="must be between 0 and 1"):
            RelevanceScore(
                frequency_score=0.5,
                recency_score=-0.1,  # Invalid
                user_feedback=0.6,
                total_score=0.4,
            )
