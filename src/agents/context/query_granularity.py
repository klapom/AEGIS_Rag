"""Query Granularity Classification for Recursive LLM.

Sprint 92 Feature 92.9: C-LARA Granularity Mapper

This module maps C-LARA intent classification to query granularity for
optimal scoring method selection in recursive LLM processing.

Architecture:
    Query
      ↓
    C-LARA Intent Classifier (Sprint 81, 95.22% accuracy)
      ↓
    Granularity Mapping:
      - NAVIGATION → fine-grained (95% confidence)
      - PROCEDURAL → holistic (90% confidence)
      - COMPARISON → holistic (90% confidence)
      - RECOMMENDATION → holistic (90% confidence)
      - FACTUAL → Heuristic sub-classification (85% confidence)
      ↓
    Granularity Decision (fine-grained vs holistic)
      ↓
    Scoring Method Selection (multi-vector vs LLM)

Granularity Types:
    - fine-grained: Token-level precision needed
        Examples: "What is the p-value?", "Show Table 3", "Define BGE-M3"
        → Use BGE-M3 multi-vector scoring (ColBERT-style)

    - holistic: Document-level understanding needed
        Examples: "Summarize methodology", "Explain the approach", "Why X?"
        → Use LLM scoring (deep reasoning)

Example:
    >>> from src.agents.context.query_granularity import get_granularity_mapper
    >>> mapper = get_granularity_mapper()
    >>>
    >>> # Fine-grained query
    >>> granularity, conf = await mapper.classify_granularity(
    ...     "What is the p-value for BGE-M3?"
    ... )
    >>> granularity
    'fine-grained'
    >>> conf
    0.85
    >>>
    >>> # Holistic query
    >>> granularity, conf = await mapper.classify_granularity(
    ...     "Summarize the main findings"
    ... )
    >>> granularity
    'holistic'
    >>> conf
    0.85

See Also:
    - docs/sprints/SPRINT_92_CLARA_GRANULARITY_MAPPING.md: Design doc
    - src/components/retrieval/intent_classifier.py: C-LARA classifier
    - Sprint 81: C-LARA SetFit Integration (95.22% accuracy)
"""

import re
from typing import Literal, Optional

import structlog

logger = structlog.get_logger(__name__)


class CLARAGranularityMapper:
    """Map C-LARA intents to query granularity using existing classifier.

    Sprint 92 Feature 92.9: Reuses Sprint 81 C-LARA (95.22% accuracy)

    Only FACTUAL intent requires heuristic sub-classification (30% of queries).
    All other intents (70%) map directly to granularity with high confidence.

    Attributes:
        clara_classifier: C-LARA intent classifier from Sprint 81
        fine_grained_factual: Regex patterns for fine-grained FACTUAL queries
        holistic_factual: Regex patterns for holistic FACTUAL queries

    Example:
        >>> mapper = CLARAGranularityMapper()
        >>> granularity, conf = await mapper.classify_granularity(
        ...     "What is the p-value for BGE-M3?"
        ... )
        >>> granularity
        'fine-grained'
    """

    def __init__(self):
        """Initialize C-LARA granularity mapper."""
        # Lazy-load C-LARA classifier
        self._clara_classifier = None
        self._init_factual_patterns()

    def _init_factual_patterns(self):
        """Initialize patterns for FACTUAL sub-classification."""
        # Fine-grained FACTUAL indicators
        self.fine_grained_factual = [
            re.compile(r"\b(what|which) (is|are) the\b", re.IGNORECASE),
            re.compile(r"\b(p-value|score|metric|number|count|percentage)\b", re.IGNORECASE),
            re.compile(r"\bTable \d+\b", re.IGNORECASE),
            re.compile(r"\bFigure \d+\b", re.IGNORECASE),
            re.compile(r"\bEquation \d+\b", re.IGNORECASE),
            re.compile(r"\b(formula|equation|definition) (for|of)\b", re.IGNORECASE),
            re.compile(r"\b(exact|specific|precise) (value|number)\b", re.IGNORECASE),
            re.compile(r"\b[A-Z]{2,}-[A-Z]\d+\b"),  # BGE-M3, GPT-4, etc.
            re.compile(r"\b\d+(\.\d+)?%\b"),  # Percentages
            re.compile(r"\bin (Table|Figure|Section|Chapter|Appendix)\b", re.IGNORECASE),
        ]

        # Holistic FACTUAL indicators
        self.holistic_factual = [
            re.compile(r"\b(summarize|overview|describe)\b", re.IGNORECASE),
            re.compile(r"\b(main|key|primary) (idea|finding|result)\b", re.IGNORECASE),
            re.compile(r"\b(explain|elaborate|detail)\b", re.IGNORECASE),
            re.compile(r"\b(overall|general|broad)\b", re.IGNORECASE),
            re.compile(r"\b(why|reason|rationale|motivation)\b", re.IGNORECASE),
        ]

    async def classify_granularity(
        self, query: str
    ) -> tuple[Literal["fine-grained", "holistic"], float]:
        """Classify query granularity using C-LARA + heuristics.

        Args:
            query: User query string

        Returns:
            Tuple of (granularity, confidence)

        Example:
            >>> mapper = CLARAGranularityMapper()
            >>> granularity, conf = await mapper.classify_granularity(
            ...     "What is the p-value for BGE-M3?"
            ... )
            >>> granularity
            'fine-grained'
            >>> conf
            0.85
        """
        # Lazy-load C-LARA classifier
        if self._clara_classifier is None:
            try:
                from src.components.retrieval.intent_classifier import get_intent_classifier

                self._clara_classifier = get_intent_classifier()
                logger.info("clara_classifier_loaded")
            except Exception as e:
                logger.warning(
                    "clara_classifier_load_failed",
                    error=str(e),
                    message="Falling back to heuristic-only classification",
                )

        # Try C-LARA classification
        if self._clara_classifier is not None:
            try:
                result = await self._clara_classifier.classify(query)
                clara_intent = result.clara_intent

                if clara_intent is not None:
                    return self._map_clara_to_granularity(clara_intent, query)
                else:
                    logger.warning(
                        "clara_intent_null",
                        query=query[:100],
                        fallback="heuristic",
                    )
            except Exception as e:
                logger.warning(
                    "clara_classification_failed",
                    error=str(e),
                    query=query[:100],
                    fallback="heuristic",
                )

        # Fallback to heuristic-only
        return self._heuristic_only_fallback(query)

    def _map_clara_to_granularity(
        self, clara_intent, query: str
    ) -> tuple[Literal["fine-grained", "holistic"], float]:
        """Map C-LARA intent to granularity.

        Direct mapping for 4/5 intents (80% coverage).
        Heuristic sub-classification for FACTUAL (20% coverage).

        Args:
            clara_intent: C-LARA intent enum
            query: User query string

        Returns:
            Tuple of (granularity, confidence)
        """
        from src.components.retrieval.intent_classifier import CLARAIntent

        # Direct mapping for non-ambiguous intents
        if clara_intent == CLARAIntent.NAVIGATION:
            # Find specific docs → keyword-based → fine-grained
            logger.debug(
                "clara_granularity_mapped",
                clara_intent="navigation",
                granularity="fine-grained",
                confidence=0.95,
            )
            return "fine-grained", 0.95

        elif clara_intent in [
            CLARAIntent.PROCEDURAL,
            CLARAIntent.COMPARISON,
            CLARAIntent.RECOMMENDATION,
        ]:
            # How-to, Compare, Recommend → reasoning needed → holistic
            logger.debug(
                "clara_granularity_mapped",
                clara_intent=clara_intent.value,
                granularity="holistic",
                confidence=0.90,
            )
            return "holistic", 0.90

        elif clara_intent == CLARAIntent.FACTUAL:
            # FACTUAL is ambiguous → use heuristic sub-classification
            return self._classify_factual_granularity(query)

        else:
            # Unknown intent → fallback to heuristic
            logger.warning("unknown_clara_intent", intent=str(clara_intent), fallback="heuristic")
            return self._heuristic_only_fallback(query)

    def _classify_factual_granularity(
        self, query: str
    ) -> tuple[Literal["fine-grained", "holistic"], float]:
        """Sub-classify FACTUAL intent into fine-grained vs holistic.

        Uses pattern matching on query text.

        Args:
            query: User query string

        Returns:
            Tuple of (granularity, confidence)
        """
        fine_score = sum(1 for pattern in self.fine_grained_factual if pattern.search(query))

        holistic_score = sum(1 for pattern in self.holistic_factual if pattern.search(query))

        logger.debug(
            "factual_subclassification",
            query=query[:100],
            fine_score=fine_score,
            holistic_score=holistic_score,
        )

        # Decision logic
        if fine_score == 0 and holistic_score == 0:
            # No patterns matched → default to fine-grained (faster & safer)
            return "fine-grained", 0.60

        total_score = fine_score + holistic_score
        if fine_score >= holistic_score:
            confidence = 0.70 + (fine_score / max(total_score, 1)) * 0.20
            return "fine-grained", min(confidence, 0.90)
        else:
            confidence = 0.70 + (holistic_score / max(total_score, 1)) * 0.20
            return "holistic", min(confidence, 0.90)

    def _heuristic_only_fallback(
        self, query: str
    ) -> tuple[Literal["fine-grained", "holistic"], float]:
        """Pure heuristic fallback if C-LARA not available.

        Combines all patterns for direct classification.

        Args:
            query: User query string

        Returns:
            Tuple of (granularity, confidence)
        """
        fine_score = sum(1 for p in self.fine_grained_factual if p.search(query))
        holistic_score = sum(1 for p in self.holistic_factual if p.search(query))

        logger.debug(
            "heuristic_only_classification",
            query=query[:100],
            fine_score=fine_score,
            holistic_score=holistic_score,
        )

        if fine_score >= holistic_score:
            return "fine-grained", 0.70
        else:
            return "holistic", 0.70


# Global singleton instance
_granularity_mapper: Optional[CLARAGranularityMapper] = None


def get_granularity_mapper() -> CLARAGranularityMapper:
    """Get global singleton granularity mapper instance.

    Returns:
        CLARAGranularityMapper: Singleton instance

    Example:
        >>> from src.agents.context.query_granularity import get_granularity_mapper
        >>> mapper = get_granularity_mapper()
        >>> granularity, conf = await mapper.classify_granularity("What is X?")
    """
    global _granularity_mapper

    if _granularity_mapper is None:
        _granularity_mapper = CLARAGranularityMapper()
        logger.info("granularity_mapper_initialized")

    return _granularity_mapper
