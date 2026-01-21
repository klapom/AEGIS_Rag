"""Importance Scoring for Episodic Memory Facts.

Sprint 68 Feature 68.6: Memory-Write Policy + Forgetting

This module implements multi-factor importance scoring to determine
which facts should be written to episodic memory (Graphiti).

Factors:
- Novelty: Is this new information? (0-1)
- Relevance: Related to user's domain/context? (0-1)
- Frequency: How often referenced/accessed? (0-1)
- Recency: When was it created? (0-1)

Reference: Paper 2512.16301 (Tool-Level Adaptation)
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


@dataclass
class ImportanceScore:
    """Multi-factor importance score for a memory fact.

    Attributes:
        novelty: Novelty score (0-1)
        relevance: Relevance score (0-1)
        frequency: Frequency score (0-1)
        recency: Recency score (0-1)
        total_score: Weighted combination (0-1)
        breakdown: Component scores for debugging
    """

    novelty: float
    relevance: float
    frequency: float
    recency: float
    total_score: float
    breakdown: dict[str, float]

    def __post_init__(self) -> None:
        """Validate score ranges."""
        for field in ["novelty", "relevance", "frequency", "recency", "total_score"]:
            value = getattr(self, field)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field} must be between 0.0 and 1.0, got {value}")


class ImportanceScorer:
    """Multi-factor importance scorer for episodic facts.

    Determines whether facts should be written to memory based on:
    1. Novelty: New vs. redundant information
    2. Relevance: Domain/context alignment
    3. Frequency: Reference count
    4. Recency: Temporal importance

    Example:
        scorer = ImportanceScorer()
        fact = {"content": "...", "created_at": "...", "metadata": {...}}
        score = await scorer.score_fact(fact)
        if scorer.should_remember(score):
            await memory.add_fact(fact)
    """

    def __init__(
        self,
        novelty_weight: float = 0.3,
        relevance_weight: float = 0.3,
        frequency_weight: float = 0.2,
        recency_weight: float = 0.2,
        importance_threshold: float = 0.6,
        recency_half_life_days: int = 7,
    ) -> None:
        """Initialize importance scorer.

        Args:
            novelty_weight: Weight for novelty score (default: 0.3)
            relevance_weight: Weight for relevance score (default: 0.3)
            frequency_weight: Weight for frequency score (default: 0.2)
            recency_weight: Weight for recency score (default: 0.2)
            importance_threshold: Minimum score to remember (default: 0.6)
            recency_half_life_days: Half-life for recency decay (default: 7)
        """
        # Validate weights sum to 1.0
        total_weight = novelty_weight + relevance_weight + frequency_weight + recency_weight
        if not 0.99 <= total_weight <= 1.01:  # Allow small floating-point error
            raise ValueError(
                f"Weights must sum to 1.0, got {total_weight}. "
                f"Weights: novelty={novelty_weight}, relevance={relevance_weight}, "
                f"frequency={frequency_weight}, recency={recency_weight}"
            )

        self.novelty_weight = novelty_weight
        self.relevance_weight = relevance_weight
        self.frequency_weight = frequency_weight
        self.recency_weight = recency_weight
        self.importance_threshold = importance_threshold
        self.recency_half_life_days = recency_half_life_days

        logger.info(
            "Initialized ImportanceScorer",
            weights={
                "novelty": novelty_weight,
                "relevance": relevance_weight,
                "frequency": frequency_weight,
                "recency": recency_weight,
            },
            threshold=importance_threshold,
            recency_half_life_days=recency_half_life_days,
        )

    async def score_fact(
        self,
        fact: dict[str, Any],
        existing_facts: list[dict[str, Any]] | None = None,
        domain_context: str | None = None,
    ) -> ImportanceScore:
        """Calculate importance score for a fact.

        Args:
            fact: Fact dictionary with 'content', 'created_at', 'metadata'
            existing_facts: Existing facts for novelty calculation (optional)
            domain_context: User's domain/context for relevance (optional)

        Returns:
            ImportanceScore with breakdown

        Raises:
            MemoryError: If scoring fails
        """
        try:
            # 1. Novelty: Check if this is new information
            novelty = await self._compute_novelty(fact, existing_facts or [])

            # 2. Relevance: Check domain/context alignment
            relevance = await self._compute_relevance(fact, domain_context)

            # 3. Frequency: Check reference count
            frequency = self._compute_frequency(fact)

            # 4. Recency: Check temporal importance
            recency = self._compute_recency(fact)

            # Weighted combination
            total_score = (
                self.novelty_weight * novelty
                + self.relevance_weight * relevance
                + self.frequency_weight * frequency
                + self.recency_weight * recency
            )

            score = ImportanceScore(
                novelty=novelty,
                relevance=relevance,
                frequency=frequency,
                recency=recency,
                total_score=total_score,
                breakdown={
                    "novelty": novelty,
                    "relevance": relevance,
                    "frequency": frequency,
                    "recency": recency,
                    "weights": {
                        "novelty": self.novelty_weight,
                        "relevance": self.relevance_weight,
                        "frequency": self.frequency_weight,
                        "recency": self.recency_weight,
                    },
                },
            )

            logger.debug(
                "Scored fact",
                total_score=round(total_score, 3),
                novelty=round(novelty, 3),
                relevance=round(relevance, 3),
                frequency=round(frequency, 3),
                recency=round(recency, 3),
                content_preview=fact.get("content", "")[:50],
            )

            return score

        except Exception as e:
            logger.error("Failed to score fact", error=str(e))
            raise MemoryError(operation="importance_scoring", reason=str(e)) from e

    async def _compute_novelty(
        self, fact: dict[str, Any], existing_facts: list[dict[str, Any]]
    ) -> float:
        """Compute novelty score (0-1).

        Novelty = 1.0 - max_similarity_to_existing_facts

        Args:
            fact: New fact to score
            existing_facts: Existing facts in memory

        Returns:
            Novelty score (0-1), where 1.0 = completely novel
        """
        if not existing_facts:
            # No existing facts, completely novel
            return 1.0

        content = fact.get("content", "")
        if not content:
            return 0.5  # Neutral score for missing content

        # Simple text-based novelty (placeholder)
        # TODO Sprint 69: Use embeddings + cosine similarity for better novelty detection
        max_similarity = 0.0
        for existing in existing_facts:
            existing_content = existing.get("content", "")
            if not existing_content:
                continue

            # Jaccard similarity (simple approximation)
            words1 = set(content.lower().split())
            words2 = set(existing_content.lower().split())
            if not words1 or not words2:
                continue

            intersection = len(words1 & words2)
            union = len(words1 | words2)
            similarity = intersection / union if union > 0 else 0.0
            max_similarity = max(max_similarity, similarity)

        novelty = 1.0 - max_similarity
        return novelty

    async def _compute_relevance(self, fact: dict[str, Any], domain_context: str | None) -> float:
        """Compute relevance score (0-1).

        Relevance = similarity to user's domain/context

        Args:
            fact: Fact to score
            domain_context: User's domain or context string

        Returns:
            Relevance score (0-1)
        """
        if not domain_context:
            # No domain context, assume neutral relevance
            return 0.7  # Default high relevance

        content = fact.get("content", "")
        if not content:
            return 0.5  # Neutral score for missing content

        # Simple keyword-based relevance (placeholder)
        # TODO Sprint 69: Use embeddings + semantic similarity for better relevance
        content_lower = content.lower()
        domain_lower = domain_context.lower()

        # Check for domain keywords
        domain_words = set(domain_lower.split())
        content_words = set(content_lower.split())

        if not domain_words or not content_words:
            return 0.5

        # Jaccard similarity
        intersection = len(domain_words & content_words)
        union = len(domain_words | content_words)
        relevance = intersection / union if union > 0 else 0.0

        # Boost if domain appears in content
        if domain_lower in content_lower:
            relevance = min(1.0, relevance + 0.3)

        return relevance

    def _compute_frequency(self, fact: dict[str, Any]) -> float:
        """Compute frequency score (0-1).

        Frequency = normalized reference count

        Args:
            fact: Fact with metadata containing reference_count

        Returns:
            Frequency score (0-1)
        """
        metadata = fact.get("metadata", {})
        reference_count = metadata.get("reference_count", 0)

        # Normalize with sigmoid-like function
        # reference_count=0 → 0.1, reference_count=10 → 0.9
        max_references = 20  # Reference count that yields ~0.95 score
        frequency = 1.0 - (1.0 / (1.0 + (reference_count / max_references) ** 2))

        return max(0.0, min(1.0, frequency))

    def _compute_recency(self, fact: dict[str, Any]) -> float:
        """Compute recency score (0-1).

        Recency = exponential decay based on age
        Uses half-life decay: score(t) = 2^(-t/half_life)

        Args:
            fact: Fact with created_at timestamp

        Returns:
            Recency score (0-1), where 1.0 = just created
        """
        created_at = fact.get("created_at")
        if not created_at:
            return 0.5  # Neutral score for missing timestamp

        try:
            # Parse timestamp
            if isinstance(created_at, str):
                created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            elif isinstance(created_at, datetime):
                created_time = created_at
            else:
                return 0.5  # Unknown format

            # Calculate age
            age = datetime.now(UTC) - created_time
            age_days = age.total_seconds() / 86400  # Convert to days

            # Exponential decay with half-life
            recency = 2 ** (-age_days / self.recency_half_life_days)

            return max(0.0, min(1.0, recency))

        except Exception as e:
            logger.warning("Failed to parse created_at", created_at=created_at, error=str(e))
            return 0.5  # Neutral score on error

    def should_remember(self, score: ImportanceScore) -> bool:
        """Determine if fact should be written to memory.

        Args:
            score: ImportanceScore from score_fact()

        Returns:
            True if total_score >= threshold
        """
        return score.total_score >= self.importance_threshold

    async def batch_score_facts(
        self,
        facts: list[dict[str, Any]],
        domain_context: str | None = None,
    ) -> list[tuple[dict[str, Any], ImportanceScore]]:
        """Score multiple facts in batch.

        Args:
            facts: List of facts to score
            domain_context: User's domain/context

        Returns:
            List of (fact, score) tuples
        """
        results = []
        for i, fact in enumerate(facts):
            # For novelty, use facts scored so far as existing context
            existing_facts = [f for f, _ in results]
            score = await self.score_fact(fact, existing_facts, domain_context)
            results.append((fact, score))

        logger.info(
            "Batch scored facts",
            total_facts=len(facts),
            avg_score=(
                round(sum(s.total_score for _, s in results) / len(results), 3) if results else 0.0
            ),
            above_threshold=sum(1 for _, s in results if self.should_remember(s)),
        )

        return results


# Global singleton instance
_importance_scorer: ImportanceScorer | None = None


def get_importance_scorer() -> ImportanceScorer:
    """Get global ImportanceScorer instance (singleton).

    Returns:
        ImportanceScorer instance with default configuration
    """
    global _importance_scorer
    if _importance_scorer is None:
        _importance_scorer = ImportanceScorer()
    return _importance_scorer
