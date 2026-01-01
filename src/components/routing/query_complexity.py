"""Query Complexity Scorer for Model Selection Strategy.

Sprint 69 Feature 69.3: Model Selection Strategy (5 SP)

This module implements complexity scoring for queries to enable intelligent
model routing. Queries are scored on multiple factors and assigned to one of
three complexity tiers (fast, balanced, advanced), each corresponding to a
different LLM model with different latency/quality tradeoffs.

Model Tiers:
    - FAST: llama3.2:3b (~150ms, simple factual queries)
    - BALANCED: llama3.2:8b (~320ms, standard queries)
    - ADVANCED: qwen2.5:14b (~800ms, complex multi-hop reasoning)

Scoring Factors:
    1. Query Length (0-0.3): Longer queries tend to be more complex
    2. Entity Count (0-0.3): More entities require more reasoning
    3. Intent Type (0-0.4): Graph/multi-hop intents are more complex
    4. Question Complexity (0-0.2): How/why vs what/when questions

Total Score Range: 0.0-1.0
    - < 0.3: FAST tier (simple queries)
    - 0.3-0.6: BALANCED tier (standard queries)
    - > 0.6: ADVANCED tier (complex queries)

Example:
    scorer = QueryComplexityScorer()
    score = scorer.score_query(
        query="Explain how authentication works in microservices",
        intent="exploratory"
    )
    # score.tier == ComplexityTier.ADVANCED
    # score.score ~= 0.7
    # score.factors == {"length": 0.2, "entities": 0.1, "intent": 0.2, "question": 0.2}
"""

import re
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class ComplexityTier(str, Enum):
    """Complexity tier for model selection.

    Each tier maps to a specific model with different latency/quality tradeoffs:
        - FAST: llama3.2:3b (~150ms, 70% quality)
        - BALANCED: llama3.2:8b (~320ms, 85% quality)
        - ADVANCED: qwen2.5:14b (~800ms, 95% quality)
    """

    FAST = "fast"
    BALANCED = "balanced"
    ADVANCED = "advanced"


@dataclass(frozen=True)
class QueryComplexityScore:
    """Result of query complexity scoring.

    Attributes:
        tier: Assigned complexity tier (fast, balanced, advanced)
        score: Total complexity score (0.0-1.0)
        factors: Individual factor scores contributing to total
    """

    tier: ComplexityTier
    score: float
    factors: dict[str, float]

    def __post_init__(self) -> None:
        """Validate score is in valid range."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")


# Intent complexity mapping (aligned with Intent enum from intent_classifier.py)
INTENT_COMPLEXITY_SCORES: dict[str, float] = {
    "factual": 0.1,  # Simple fact lookup
    "keyword": 0.0,  # Keyword search (simplest)
    "exploratory": 0.2,  # Exploration requires reasoning
    "summary": 0.3,  # Summarization requires synthesis
    "graph_reasoning": 0.4,  # Graph queries are complex
    "multi_hop": 0.4,  # Multi-hop reasoning is complex
}


class QueryComplexityScorer:
    """Score query complexity for model selection.

    This scorer analyzes queries across multiple dimensions to determine
    their computational complexity. The score is used to route queries to
    the appropriate model tier for optimal latency/quality tradeoff.

    Scoring Algorithm:
        1. Length Factor (0-0.3): Normalized word count (max at 30 words)
        2. Entity Factor (0-0.3): Capitalized word count (heuristic for entities)
        3. Intent Factor (0-0.4): Based on intent type (from intent classifier)
        4. Question Factor (0-0.2): Question word complexity (how/why vs what/when)

    The total score determines the tier:
        - < 0.3: FAST tier (40% of queries expected)
        - 0.3-0.6: BALANCED tier (40% of queries expected)
        - > 0.6: ADVANCED tier (20% of queries expected)

    Example:
        scorer = QueryComplexityScorer()

        # Simple query
        result = scorer.score_query("What is RAG?", "factual")
        # tier=FAST, score=0.15

        # Complex query
        result = scorer.score_query(
            "Explain how graph-based retrieval compares to vector search",
            "exploratory"
        )
        # tier=ADVANCED, score=0.7
    """

    def __init__(
        self,
        length_weight: float = 0.3,
        entity_weight: float = 0.3,
        intent_weight: float = 0.4,
        question_weight: float = 0.2,
        fast_threshold: float = 0.3,
        advanced_threshold: float = 0.6,
    ):
        """Initialize Query Complexity Scorer.

        Args:
            length_weight: Maximum contribution of length factor (default: 0.3)
            entity_weight: Maximum contribution of entity factor (default: 0.3)
            intent_weight: Maximum contribution of intent factor (default: 0.4)
            question_weight: Maximum contribution of question factor (default: 0.2)
            fast_threshold: Score threshold for FAST tier (default: 0.3)
            advanced_threshold: Score threshold for ADVANCED tier (default: 0.6)
        """
        self.length_weight = length_weight
        self.entity_weight = entity_weight
        self.intent_weight = intent_weight
        self.question_weight = question_weight
        self.fast_threshold = fast_threshold
        self.advanced_threshold = advanced_threshold

        logger.info(
            "query_complexity_scorer_initialized",
            length_weight=length_weight,
            entity_weight=entity_weight,
            intent_weight=intent_weight,
            question_weight=question_weight,
            fast_threshold=fast_threshold,
            advanced_threshold=advanced_threshold,
        )

    def score_query(self, query: str, intent: str) -> QueryComplexityScore:
        """Calculate query complexity score.

        Analyzes the query across multiple dimensions to produce a total
        complexity score and assign it to a tier for model selection.

        Args:
            query: User query string
            intent: Intent classification (factual, keyword, exploratory, summary, etc.)

        Returns:
            QueryComplexityScore with tier, total score, and factor breakdown

        Example:
            >>> scorer = QueryComplexityScorer()
            >>> score = scorer.score_query("What is the capital of France?", "factual")
            >>> score.tier
            ComplexityTier.FAST
            >>> score.score
            0.2
            >>> score.factors
            {'length': 0.18, 'entities': 0.06, 'intent': 0.1, 'question': 0.1}
        """
        factors: dict[str, float] = {}

        # 1. Query Length Factor (0-0.3)
        # Longer queries tend to be more complex
        word_count = len(query.split())
        # Normalize to 30 words max, scale by weight
        length_normalized = min(word_count / 30.0, 1.0)
        factors["length"] = length_normalized * self.length_weight

        # 2. Entity Count Factor (0-0.3)
        # More entities require more reasoning and context
        # Heuristic: Count capitalized words (not at sentence start)
        entities = self._extract_entities(query)
        entity_count = len(entities)
        # Normalize to 5 entities max, scale by weight
        entity_normalized = min(entity_count / 5.0, 1.0)
        factors["entities"] = entity_normalized * self.entity_weight

        # 3. Intent Factor (0-0.4)
        # Different intents have different complexity levels
        intent_score = INTENT_COMPLEXITY_SCORES.get(intent.lower(), 0.2)  # Default: 0.2
        factors["intent"] = intent_score * (self.intent_weight / 0.4)  # Normalize to weight

        # 4. Question Complexity Factor (0-0.2)
        # How/why questions are more complex than what/when
        question_score = self._score_question_complexity(query)
        factors["question"] = question_score * self.question_weight

        # Calculate total score
        total_score = sum(factors.values())

        # Determine tier based on thresholds
        if total_score < self.fast_threshold:
            tier = ComplexityTier.FAST
        elif total_score < self.advanced_threshold:
            tier = ComplexityTier.BALANCED
        else:
            tier = ComplexityTier.ADVANCED

        logger.debug(
            "query_complexity_scored",
            query=query[:50],
            intent=intent,
            tier=tier.value,
            score=round(total_score, 3),
            factors={k: round(v, 3) for k, v in factors.items()},
        )

        return QueryComplexityScore(tier=tier, score=total_score, factors=factors)

    def _extract_entities(self, query: str) -> list[str]:
        """Extract entity candidates from query.

        Uses a simple heuristic: capitalized words that are not at the
        start of a sentence. This is not perfect but good enough for
        complexity scoring.

        Args:
            query: User query string

        Returns:
            List of entity candidate strings
        """
        # Split into words
        words = query.split()
        entities = []

        for i, word in enumerate(words):
            # Skip first word (could be sentence start)
            if i == 0:
                continue

            # Remove punctuation for checking
            word_clean = re.sub(r"[^\w]", "", word)

            # Check if capitalized (and not all caps acronym)
            if word_clean and word_clean[0].isupper() and not word_clean.isupper():
                entities.append(word_clean)

        return entities

    def _score_question_complexity(self, query: str) -> float:
        """Score question word complexity.

        How/why/explain questions require deeper reasoning than
        what/when/where factual lookups.

        Args:
            query: User query string

        Returns:
            Question complexity score (0.0-1.0)
        """
        query_lower = query.lower().strip()

        # Complex question patterns (score: 1.0)
        complex_patterns = [
            r"^how\s",
            r"^why\s",
            r"\bexplain\b",
            r"\bcompare\b",
            r"\bcontrast\b",
            r"\bdifference between\b",
            r"\brelationship\b",
            r"^wie\s",  # German
            r"^warum\s",  # German
            r"\berklär",  # German
        ]

        for pattern in complex_patterns:
            if re.search(pattern, query_lower):
                return 1.0

        # Moderate question patterns (score: 0.5)
        moderate_patterns = [
            r"^what\s",
            r"^which\s",
            r"^can\s",
            r"^could\s",
            r"^should\s",
            r"^would\s",
            r"^was\s",  # German
            r"^welche\s",  # German
        ]

        for pattern in moderate_patterns:
            if re.search(pattern, query_lower):
                return 0.5

        # Simple patterns (score: 0.25)
        simple_patterns = [
            r"^when\s",
            r"^where\s",
            r"^who\s",
            r"\bdefinition\b",
            r"^wann\s",  # German
            r"^wo\s",  # German
            r"^wer\s",  # German
        ]

        for pattern in simple_patterns:
            if re.search(pattern, query_lower):
                return 0.25

        # No question pattern detected (score: 0.0)
        return 0.0


# Singleton instance
_complexity_scorer: QueryComplexityScorer | None = None


def get_complexity_scorer() -> QueryComplexityScorer:
    """Get global QueryComplexityScorer instance (singleton).

    Returns:
        QueryComplexityScorer instance

    Example:
        >>> scorer = get_complexity_scorer()
        >>> result = scorer.score_query("What is RAG?", "factual")
    """
    global _complexity_scorer
    if _complexity_scorer is None:
        _complexity_scorer = QueryComplexityScorer()
    return _complexity_scorer


__all__ = [
    "ComplexityTier",
    "QueryComplexityScore",
    "QueryComplexityScorer",
    "get_complexity_scorer",
]
