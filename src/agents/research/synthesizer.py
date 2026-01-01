"""Result Synthesis Component - Reuses AnswerGenerator.

Sprint 70: Deep Research & Tool Use Integration

This module synthesizes research findings by reusing the existing AnswerGenerator
infrastructure instead of duplicating LLM logic. This ensures consistency with
normal chat answers and reduces code duplication.

Key Design:
- Reuses AnswerGenerator for LLM synthesis
- Uses correct LLMTask API
- Generates citations automatically
- Consistent answer quality across all modes
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def synthesize_research_findings(
    query: str,
    contexts: list[dict[str, Any]],
    namespace: str = "default",
) -> dict[str, Any]:
    """Synthesize research findings into comprehensive answer.

    Instead of duplicating LLM logic, this function reuses the existing
    AnswerGenerator which already handles:
    - LLM-based synthesis
    - Source citations
    - Quality control
    - Model selection

    Args:
        query: Original research question
        contexts: List of retrieved contexts from all research queries
        namespace: Namespace for context

    Returns:
        Dict with synthesis results:
        {
            "answer": str,  # Synthesized answer
            "sources": list[dict],  # Cited sources
            "metadata": dict,  # Additional info
        }

    Examples:
        >>> result = await synthesize_research_findings(
        ...     "What is AI?",
        ...     [{"text": "AI is...", "source": "vector"}]
        ... )
        >>> "answer" in result
        True
    """
    logger.info(
        "synthesizing_research_findings",
        query=query,
        num_contexts=len(contexts),
        namespace=namespace,
    )

    if not contexts:
        logger.warning("no_contexts_to_synthesize")
        return {
            "answer": "No information found to answer the query.",
            "sources": [],
            "metadata": {"num_contexts": 0},
        }

    try:
        # Import AnswerGenerator (lazy to avoid circular imports)
        from src.agents.answer_generator import AnswerGenerator

        # Create answer generator instance
        # Use slightly lower temperature for research synthesis (more factual)
        generator = AnswerGenerator(temperature=0.2)

        # Generate comprehensive answer with citations
        # AnswerGenerator automatically handles:
        # - Context formatting
        # - LLM synthesis via AegisLLMProxy
        # - Citation generation
        # - Quality control
        answer_with_citations = await generator.generate_with_citations(
            query=query,
            contexts=contexts,
            intent="hybrid",  # Research uses hybrid intent
            namespace=namespace,
        )

        # Extract answer and sources
        answer = answer_with_citations.get("answer", "")
        sources = answer_with_citations.get("sources", [])

        # Calculate synthesis metadata
        metadata = {
            "num_contexts": len(contexts),
            "num_sources_cited": len(sources),
            "answer_length": len(answer),
            "synthesis_method": "AnswerGenerator",
        }

        logger.info(
            "synthesis_completed",
            answer_length=len(answer),
            num_sources_cited=len(sources),
        )

        return {
            "answer": answer,
            "sources": sources,
            "metadata": metadata,
        }

    except Exception as e:
        logger.error("synthesis_failed", error=str(e), exc_info=True)
        # Fallback: return simple concatenation
        return _fallback_synthesis(query, contexts)


def _fallback_synthesis(query: str, contexts: list[dict[str, Any]]) -> dict[str, Any]:
    """Fallback synthesis when AnswerGenerator fails.

    Args:
        query: Research question
        contexts: Retrieved contexts

    Returns:
        Dict with fallback synthesis
    """
    logger.warning("using_fallback_synthesis")

    # Take top 5 results by score
    top_contexts = sorted(
        contexts,
        key=lambda c: c.get("score", 0.0),
        reverse=True,
    )[:5]

    if not top_contexts:
        return {
            "answer": "No information available.",
            "sources": [],
            "metadata": {"fallback": True},
        }

    # Build simple answer from top contexts
    answer_parts = [f"Research findings for: {query}\n"]

    sources = []
    for idx, ctx in enumerate(top_contexts, 1):
        text = ctx.get("text", "").strip()
        source_type = ctx.get("source_channel", ctx.get("source", "unknown"))

        if text:
            # Truncate long texts
            if len(text) > 300:
                text = text[:297] + "..."

            answer_parts.append(f"\n[{idx}] {text}")

            # Add to sources
            sources.append(
                {
                    "index": idx,
                    "text": text,
                    "source_type": source_type,
                    "score": ctx.get("score", 0.0),
                }
            )

    answer = "\n".join(answer_parts)

    return {
        "answer": answer,
        "sources": sources,
        "metadata": {
            "num_contexts": len(contexts),
            "fallback": True,
        },
    }


def evaluate_synthesis_quality(result: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the quality of synthesis.

    Args:
        result: Synthesis result dict

    Returns:
        Dict with quality metrics

    Examples:
        >>> metrics = evaluate_synthesis_quality({
        ...     "answer": "AI is...",
        ...     "sources": [{"index": 1}],
        ...     "metadata": {"num_contexts": 10}
        ... })
        >>> "quality_score" in metrics
        True
    """
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    metadata = result.get("metadata", {})

    num_contexts = metadata.get("num_contexts", 0)
    num_sources_cited = len(sources)

    # Calculate quality metrics
    answer_length = len(answer)
    has_citations = num_sources_cited > 0
    citation_rate = num_sources_cited / max(num_contexts, 1)

    # Quality score (0-1)
    quality_score = 0.0

    # Answer length (30%)
    if answer_length > 500:
        quality_score += 0.3
    elif answer_length > 200:
        quality_score += 0.15

    # Citations (40%)
    if has_citations:
        quality_score += 0.2
        if citation_rate > 0.3:  # Good citation coverage
            quality_score += 0.2

    # Context coverage (30%)
    if num_contexts >= 10:
        quality_score += 0.3
    elif num_contexts >= 5:
        quality_score += 0.15

    metrics = {
        "quality_score": quality_score,
        "answer_length": answer_length,
        "num_contexts": num_contexts,
        "num_sources_cited": num_sources_cited,
        "citation_rate": citation_rate,
        "has_citations": has_citations,
        "has_fallback": metadata.get("fallback", False),
    }

    logger.debug("synthesis_quality_evaluated", metrics=metrics)

    return metrics
