"""Query Rewriter for improved retrieval performance.

Sprint 67 Feature 67.9: Query Rewriter v1 for query expansion and refinement.

This module implements query rewriting strategies to improve retrieval coverage:
- Query expansion: Add synonyms and related terms for short queries
- Query refinement: Clarify ambiguous or vague queries
- Intent-aware rewriting: Different strategies based on query intent

The rewriter uses LLM-based expansion/refinement with low temperature for
deterministic results. Integration with IntentClassifier enables intent-aware
strategy selection.

Architecture:
    User Query → IntentClassifier → QueryRewriter → Rewritten Query → Retrieval

Example:
    rewriter = QueryRewriter()
    result = await rewriter.rewrite("API docs")
    # result.rewritten_query: "API documentation reference guide endpoints methods"
    # result.strategy: "expansion"
    # result.confidence: 0.85

Performance Target:
    - Latency: <200ms per rewrite
    - Improvement: +5-10% retrieval coverage vs baseline

References:
    - Paper 2512.16301: Tool-Level LLM Adaptation
    - TD-075: Intent Classification Improvement
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from src.domains.llm_integration.models import LLMTask, QualityRequirement, TaskType
from src.domains.llm_integration.proxy import get_aegis_llm_proxy

if TYPE_CHECKING:
    from src.components.retrieval.intent_classifier import IntentClassifier

logger = structlog.get_logger(__name__)


@dataclass
class RewriteResult:
    """Result of query rewriting operation.

    Attributes:
        original_query: Original user query
        rewritten_query: Rewritten query for improved retrieval
        strategy: Rewriting strategy used ("expansion", "refinement", "none")
        confidence: Confidence score for the rewrite (0.0-1.0)
        intent: Detected intent (if intent_classifier provided)
        latency_ms: Rewriting latency in milliseconds
    """

    original_query: str
    rewritten_query: str
    strategy: str  # "expansion", "refinement", "none"
    confidence: float
    intent: str | None = None
    latency_ms: float = 0.0


class QueryRewriter:
    """Query rewriter for improved retrieval (T2 adaptation).

    This class implements query rewriting strategies to improve retrieval
    coverage through expansion and refinement. It integrates with the
    IntentClassifier to select appropriate strategies based on query intent.

    Strategy Selection:
        - Short queries (<3 words): Expansion with synonyms
        - Vague queries (how/what/explain): Refinement for clarity
        - Technical queries: Expansion with domain terms
        - Otherwise: No rewriting

    Example:
        # Basic usage
        rewriter = QueryRewriter()
        result = await rewriter.rewrite("API docs")
        print(result.rewritten_query)  # "API documentation reference ..."

        # With intent classifier
        from src.components.retrieval.intent_classifier import get_intent_classifier
        classifier = get_intent_classifier()
        rewriter = QueryRewriter(intent_classifier=classifier)
        result = await rewriter.rewrite("How does auth work?")
        # result.intent: "exploratory"
        # result.strategy: "refinement"
    """

    def __init__(self, intent_classifier: IntentClassifier | None = None) -> None:
        """Initialize QueryRewriter.

        Args:
            intent_classifier: Optional intent classifier for intent-aware rewriting.
                             If provided, intent will be used to refine strategy selection.
        """
        self.logger = structlog.get_logger(__name__)
        self.llm = get_aegis_llm_proxy()
        self.intent_classifier = intent_classifier

        # Temperature for rewriting (low for deterministic results)
        self._temperature = 0.3

        # Max tokens for rewritten query
        self._max_tokens = 100

        self.logger.info(
            "query_rewriter_initialized",
            has_intent_classifier=intent_classifier is not None,
            temperature=self._temperature,
        )

    async def rewrite(self, query: str) -> RewriteResult:
        """Rewrite query based on intent and complexity.

        This is the main entry point for query rewriting. It:
        1. Classifies query intent (if intent_classifier provided)
        2. Selects rewriting strategy based on query characteristics
        3. Applies expansion or refinement
        4. Returns rewritten query with metadata

        Args:
            query: Original user query

        Returns:
            RewriteResult with rewritten query, strategy, and confidence

        Example:
            result = await rewriter.rewrite("API docs")
            # Short query → expansion
            # result.rewritten_query: "API documentation reference guide endpoints"
            # result.strategy: "expansion"
        """
        start_time = time.perf_counter()

        # Step 1: Classify intent (if classifier provided)
        intent: str | None = None
        if self.intent_classifier:
            try:
                intent_result = await self.intent_classifier.classify(query)
                intent = intent_result.intent.value
                self.logger.debug(
                    "intent_classified_for_rewrite",
                    query=query[:50],
                    intent=intent,
                    confidence=intent_result.confidence,
                )
            except Exception as e:
                self.logger.warning(
                    "intent_classification_failed",
                    query=query[:50],
                    error=str(e),
                    fallback="rule_based_strategy",
                )
                intent = None

        # Step 2: Determine rewrite strategy
        strategy = self._select_strategy(query, intent)

        # Step 3: Apply rewriting
        if strategy == "expansion":
            rewritten = await self._expand_query(query, intent)
            confidence = 0.85
        elif strategy == "refinement":
            rewritten = await self._refine_query(query, intent)
            confidence = 0.80
        else:
            # No rewriting needed
            rewritten = query
            confidence = 1.0

        latency_ms = (time.perf_counter() - start_time) * 1000

        self.logger.info(
            "query_rewrite_complete",
            original=query[:50],
            rewritten=rewritten[:50],
            strategy=strategy,
            intent=intent,
            confidence=confidence,
            latency_ms=round(latency_ms, 2),
        )

        return RewriteResult(
            original_query=query,
            rewritten_query=rewritten,
            strategy=strategy,
            confidence=confidence,
            intent=intent,
            latency_ms=latency_ms,
        )

    def _select_strategy(self, query: str, intent: str | None) -> str:
        """Select rewrite strategy based on query characteristics.

        Strategy Selection Rules (priority order):
            1. Vague queries (how/what/explain) with <=5 words: refinement
            2. Exploratory queries with <=4 words: refinement
            3. Short queries (<3 words): expansion
            4. Technical/factual queries with 3-5 words: expansion
            5. Otherwise: none (no rewriting)

        Args:
            query: User query
            intent: Detected intent (factual, keyword, exploratory, summary)

        Returns:
            Strategy name: "expansion", "refinement", or "none"
        """
        query_lower = query.lower().strip()
        word_count = len(query.split())

        # Rule 1: Vague queries → refinement (PRIORITY: must come before short query check)
        vague_keywords = [
            "how",
            "what",
            "explain",
            "tell me about",
            "describe",
            "wie",
            "was",
            "erkläre",
        ]
        if any(kw in query_lower for kw in vague_keywords) and word_count <= 5:
            self.logger.debug(
                "strategy_selected_vague_query",
                query=query[:50],
                word_count=word_count,
                strategy="refinement",
            )
            return "refinement"

        # Rule 2: Exploratory queries that are too broad → refinement
        if intent == "exploratory" and word_count <= 4:
            self.logger.debug(
                "strategy_selected_exploratory_query",
                query=query[:50],
                intent=intent,
                strategy="refinement",
            )
            return "refinement"

        # Rule 3: Short queries (<3 words) → expansion
        if word_count < 3:
            self.logger.debug(
                "strategy_selected_short_query",
                query=query[:50],
                word_count=word_count,
                strategy="expansion",
            )
            return "expansion"

        # Rule 4: Technical/factual queries with moderate length → expansion
        if intent == "factual" and word_count <= 5:
            self.logger.debug(
                "strategy_selected_factual_query",
                query=query[:50],
                intent=intent,
                strategy="expansion",
            )
            return "expansion"

        # Default: No rewriting
        self.logger.debug(
            "strategy_selected_no_rewrite",
            query=query[:50],
            word_count=word_count,
            intent=intent,
        )
        return "none"

    async def _expand_query(self, query: str, intent: str | None) -> str:
        """Expand query with synonyms and related terms.

        This method uses the LLM to generate an expanded version of the query
        that includes synonyms, related terms, and domain-specific keywords
        to improve retrieval coverage.

        Args:
            query: Original query
            intent: Detected intent (helps guide expansion)

        Returns:
            Expanded query string

        Example:
            original: "API docs"
            expanded: "API documentation reference guide endpoints methods"
        """
        # Build context-aware prompt
        intent_hint = f"Query intent: {intent}" if intent else ""

        prompt = f"""You are a query expansion assistant for hybrid retrieval systems.

Original query: "{query}"
{intent_hint}

Task: Expand this short query with:
- Synonyms and related terms
- Domain-specific keywords
- Common variations

Requirements:
- Keep the expansion concise (max 15 words)
- Focus on retrieval-relevant terms
- Maintain semantic coherence
- Do NOT add punctuation or formatting

Expanded query:"""

        # Create LLM task
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            quality_requirement=QualityRequirement.MEDIUM,
        )

        # Generate expansion
        try:
            response = await self.llm.generate(task)
            expanded = response.content.strip()

            # Remove quotes if LLM added them
            expanded = expanded.strip('"\'')

            # Fallback to original if expansion failed
            if not expanded or len(expanded) < len(query):
                self.logger.warning(
                    "expansion_failed_fallback",
                    query=query[:50],
                    expanded=expanded[:50],
                    reason="empty_or_shorter",
                )
                return query

            self.logger.info(
                "query_expanded",
                original=query[:50],
                expanded=expanded[:80],
                tokens=response.tokens_used,
                provider=response.provider,
            )

            return expanded

        except Exception as e:
            self.logger.error(
                "expansion_error_fallback",
                query=query[:50],
                error=str(e),
            )
            return query

    async def _refine_query(self, query: str, intent: str | None) -> str:
        """Refine vague query to be more specific.

        This method uses the LLM to generate a refined version of the query
        that clarifies the user's intent and makes it more specific and
        actionable for retrieval.

        Args:
            query: Original query
            intent: Detected intent (helps guide refinement)

        Returns:
            Refined query string

        Example:
            original: "How does auth work?"
            refined: "How does authentication and authorization work in the system?"
        """
        # Build context-aware prompt
        intent_hint = f"Query intent: {intent}" if intent else ""

        prompt = f"""You are a query refinement assistant for hybrid retrieval systems.

Original query: "{query}"
{intent_hint}

Task: Refine this vague query to be more specific and actionable:
- Clarify ambiguous terms
- Add context where needed
- Make the intent explicit
- Expand acronyms if relevant

Requirements:
- Keep the refinement concise (max 20 words)
- Maintain the original question type
- Do NOT add punctuation or formatting beyond the question
- Focus on retrieval clarity

Refined query:"""

        # Create LLM task
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            quality_requirement=QualityRequirement.MEDIUM,
        )

        # Generate refinement
        try:
            response = await self.llm.generate(task)
            refined = response.content.strip()

            # Remove quotes if LLM added them
            refined = refined.strip('"\'')

            # Fallback to original if refinement failed
            if not refined or len(refined) < len(query):
                self.logger.warning(
                    "refinement_failed_fallback",
                    query=query[:50],
                    refined=refined[:50],
                    reason="empty_or_shorter",
                )
                return query

            self.logger.info(
                "query_refined",
                original=query[:50],
                refined=refined[:80],
                tokens=response.tokens_used,
                provider=response.provider,
            )

            return refined

        except Exception as e:
            self.logger.error(
                "refinement_error_fallback",
                query=query[:50],
                error=str(e),
            )
            return query


# Singleton instance
_query_rewriter: QueryRewriter | None = None


def get_query_rewriter(
    intent_classifier: IntentClassifier | None = None,
) -> QueryRewriter:
    """Get singleton QueryRewriter instance.

    Args:
        intent_classifier: Optional intent classifier for intent-aware rewriting.
                         If None, will attempt to use global intent classifier.

    Returns:
        QueryRewriter instance

    Example:
        from src.adaptation.query_rewriter import get_query_rewriter

        rewriter = get_query_rewriter()
        result = await rewriter.rewrite("API docs")
    """
    global _query_rewriter

    # If classifier provided, create new instance
    if intent_classifier is not None:
        return QueryRewriter(intent_classifier=intent_classifier)

    # Otherwise use singleton
    if _query_rewriter is None:
        # Try to get global intent classifier
        try:
            from src.components.retrieval.intent_classifier import get_intent_classifier

            classifier = get_intent_classifier()
            _query_rewriter = QueryRewriter(intent_classifier=classifier)
            logger.info("query_rewriter_singleton_created", has_intent_classifier=True)
        except Exception as e:
            # Create without intent classifier
            logger.warning(
                "query_rewriter_singleton_created_without_classifier",
                error=str(e),
            )
            _query_rewriter = QueryRewriter(intent_classifier=None)

    return _query_rewriter


async def rewrite_query(query: str) -> RewriteResult:
    """Convenience function to rewrite a query.

    Args:
        query: Original user query

    Returns:
        RewriteResult with rewritten query and metadata

    Example:
        from src.adaptation.query_rewriter import rewrite_query

        result = await rewrite_query("API docs")
        print(result.rewritten_query)
        print(f"Strategy: {result.strategy}, Confidence: {result.confidence}")
    """
    rewriter = get_query_rewriter()
    return await rewriter.rewrite(query)
