"""Relevance Scorer for Memory Consolidation.

This module provides importance calculation for memory items based on:
- Frequency: How often the memory is accessed
- Recency: How recent the memory is
- User feedback: Explicit user ratings (if available)
"""

import math
from dataclasses import dataclass
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RelevanceScore:
    """Relevance score breakdown for a memory item.

    Attributes:
        frequency_score: Normalized score based on access frequency (0-1)
        recency_score: Normalized score based on recency (0-1)
        user_feedback: User-provided rating (0-1), defaults to 0.5
        total_score: Weighted combination of all scores (0-1)
    """

    frequency_score: float
    recency_score: float
    user_feedback: float
    total_score: float

    def __post_init__(self):
        """Validate score ranges."""
        for field in ["frequency_score", "recency_score", "user_feedback", "total_score"]:
            value = getattr(self, field)
            if not 0 <= value <= 1:
                raise ValueError(f"{field} must be between 0 and 1, got {value}")


class RelevanceScorer:
    """Calculate relevance scores for memory consolidation.

    Uses a weighted combination of:
    - Frequency score: Logarithmic scale based on access count
    - Recency score: Exponential decay based on age
    - User feedback: Direct rating if available

    Default weights:
    - Frequency: 30%
    - Recency: 40%
    - User feedback: 30%
    """

    def __init__(
        self,
        frequency_weight: float = 0.3,
        recency_weight: float = 0.4,
        feedback_weight: float = 0.3,
        max_access_count: int = 100,
        decay_half_life_days: float = 30.0,
    ):
        """Initialize relevance scorer.

        Args:
            frequency_weight: Weight for frequency score (0-1)
            recency_weight: Weight for recency score (0-1)
            feedback_weight: Weight for user feedback score (0-1)
            max_access_count: Access count for max frequency score (normalization)
            decay_half_life_days: Days for recency score to decay to 0.5

        Raises:
            ValueError: If weights don't sum to 1.0 or are invalid
        """
        total_weight = frequency_weight + recency_weight + feedback_weight
        if not math.isclose(total_weight, 1.0, abs_tol=1e-6):
            raise ValueError(
                f"Weights must sum to 1.0, got {total_weight} "
                f"({frequency_weight} + {recency_weight} + {feedback_weight})"
            )

        if any(w < 0 or w > 1 for w in [frequency_weight, recency_weight, feedback_weight]):
            raise ValueError("All weights must be between 0 and 1")

        self.frequency_weight = frequency_weight
        self.recency_weight = recency_weight
        self.feedback_weight = feedback_weight
        self.max_access_count = max_access_count
        self.decay_half_life_days = decay_half_life_days

        logger.info(
            "Initialized RelevanceScorer",
            frequency_weight=frequency_weight,
            recency_weight=recency_weight,
            feedback_weight=feedback_weight,
            max_access_count=max_access_count,
            decay_half_life_days=decay_half_life_days,
        )

    def calculate_frequency_score(self, access_count: int) -> float:
        """Calculate frequency score using logarithmic scale.

        Args:
            access_count: Number of times the memory was accessed

        Returns:
            Normalized frequency score (0-1)
        """
        if access_count <= 0:
            return 0.0

        # Log scale: log(access_count + 1) / log(max_access_count + 1)
        # +1 to handle access_count=0 case
        score = math.log(access_count + 1) / math.log(self.max_access_count + 1)

        # Cap at 1.0
        return min(score, 1.0)

    def calculate_recency_score(self, days_old: float) -> float:
        """Calculate recency score using exponential decay.

        Uses half-life decay: score = 2^(-days_old / half_life)

        Args:
            days_old: Age of memory in days (fractional)

        Returns:
            Normalized recency score (0-1)
        """
        if days_old < 0:
            raise ValueError(f"days_old must be non-negative, got {days_old}")

        if days_old == 0:
            return 1.0

        # Exponential decay with configurable half-life
        # score = 2^(-days_old / half_life)
        score = math.pow(2, -days_old / self.decay_half_life_days)

        return score

    def calculate_score(
        self,
        access_count: int,
        stored_at: str | datetime,
        user_rating: float | None = None,
        current_time: datetime | None = None,
    ) -> RelevanceScore:
        """Calculate comprehensive relevance score for a memory item.

        Args:
            access_count: Number of times accessed
            stored_at: Storage timestamp (ISO format string or datetime)
            user_rating: Optional user rating (0-1), defaults to 0.5
            current_time: Current time for age calculation (defaults to now)

        Returns:
            RelevanceScore with breakdown of all components

        Raises:
            ValueError: If inputs are invalid
        """
        # Parse stored_at timestamp
        if isinstance(stored_at, str):
            try:
                stored_time = datetime.fromisoformat(stored_at.replace("Z", "+00:00"))
            except Exception as e:
                raise ValueError(f"Invalid stored_at timestamp: {stored_at}") from e
        elif isinstance(stored_at, datetime):
            stored_time = stored_at
        else:
            raise ValueError(f"stored_at must be str or datetime, got {type(stored_at)}")

        # Calculate age in days
        now = current_time or datetime.utcnow()
        age_delta = now - stored_time
        days_old = age_delta.total_seconds() / 86400.0  # 86400 seconds in a day

        if days_old < 0:
            raise ValueError(
                f"stored_at is in the future: {stored_time} > {now}"
            )

        # Calculate individual scores
        frequency_score = self.calculate_frequency_score(access_count)
        recency_score = self.calculate_recency_score(days_old)
        user_feedback = user_rating if user_rating is not None else 0.5

        # Validate user_rating if provided
        if user_rating is not None and not 0 <= user_rating <= 1:
            raise ValueError(f"user_rating must be between 0 and 1, got {user_rating}")

        # Calculate weighted total
        total_score = (
            frequency_score * self.frequency_weight
            + recency_score * self.recency_weight
            + user_feedback * self.feedback_weight
        )

        logger.debug(
            "Calculated relevance score",
            access_count=access_count,
            days_old=round(days_old, 2),
            frequency_score=round(frequency_score, 3),
            recency_score=round(recency_score, 3),
            user_feedback=round(user_feedback, 3),
            total_score=round(total_score, 3),
        )

        return RelevanceScore(
            frequency_score=frequency_score,
            recency_score=recency_score,
            user_feedback=user_feedback,
            total_score=total_score,
        )

    def calculate_score_from_metadata(
        self,
        metadata: dict,
        current_time: datetime | None = None,
    ) -> RelevanceScore:
        """Calculate score from memory metadata dictionary.

        Convenience method for working with Redis metadata.

        Args:
            metadata: Dictionary with keys: access_count, stored_at, user_rating (optional)
            current_time: Current time for age calculation (defaults to now)

        Returns:
            RelevanceScore

        Raises:
            ValueError: If required metadata is missing
        """
        if "access_count" not in metadata:
            raise ValueError("metadata must contain 'access_count'")
        if "stored_at" not in metadata:
            raise ValueError("metadata must contain 'stored_at'")

        return self.calculate_score(
            access_count=metadata["access_count"],
            stored_at=metadata["stored_at"],
            user_rating=metadata.get("user_rating"),
            current_time=current_time,
        )


def get_relevance_scorer() -> RelevanceScorer:
    """Get default relevance scorer instance.

    Returns:
        RelevanceScorer with default weights
    """
    return RelevanceScorer()
