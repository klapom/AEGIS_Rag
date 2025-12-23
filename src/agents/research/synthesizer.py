"""Result Synthesis Component.

Sprint 59 Feature 59.6: Synthesizes research findings into coherent answers.

This module combines results from multiple searches into a comprehensive,
well-structured answer to the user's question.
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def synthesize_findings(
    query: str,
    results: list[dict[str, Any]],
    max_context_length: int = 4000,
) -> str:
    """Synthesize search results into comprehensive answer.

    Args:
        query: Original research question
        results: List of search results from all queries
        max_context_length: Maximum context to send to LLM

    Returns:
        Synthesized answer

    Examples:
        >>> answer = await synthesize_findings(
        ...     "What is AI?",
        ...     [{"text": "AI is..."}, {"text": "Machine learning..."}]
        ... )
        >>> isinstance(answer, str)
        True
    """
    logger.info(
        "synthesizing_findings",
        query=query,
        num_results=len(results),
    )

    if not results:
        logger.warning("no_results_to_synthesize")
        return "No information found to answer the query."

    try:
        # Import LLM proxy
        from src.domains.llm_integration.proxy.aegis_llm_proxy import get_aegis_llm_proxy

        llm = get_aegis_llm_proxy()

        # Format results for context
        formatted_context = format_results_for_synthesis(
            results,
            max_length=max_context_length,
        )

        # Create synthesis prompt
        synthesis_prompt = f"""You are a research assistant synthesizing information to answer a question.

Question: {query}

Research Findings:
{formatted_context}

Task:
Synthesize the above research findings into a comprehensive, well-structured answer.
- Start with a direct answer to the question
- Provide supporting details from the research
- Cite specific sources using [Source #N] notation (e.g., "According to [Source #1], ...")
- Maintain accuracy - only state what is supported by the findings
- If the findings don't fully answer the question, acknowledge this
- Structure your answer with clear paragraphs

Comprehensive Answer:"""

        # Generate synthesis
        synthesis = await llm.generate(
            prompt=synthesis_prompt,
            temperature=0.3,  # Lower temperature for accuracy
            max_tokens=1500,
        )

        logger.info("synthesis_completed", length=len(synthesis))

        return synthesis.strip()

    except Exception as e:
        logger.error("synthesis_failed", error=str(e), exc_info=True)
        # Fallback: return concatenated results
        return _fallback_synthesis(query, results)


def format_results_for_synthesis(
    results: list[dict[str, Any]],
    max_length: int = 4000,
) -> str:
    """Format search results as context for synthesis.

    Args:
        results: Search results
        max_length: Maximum total length

    Returns:
        Formatted context string
    """
    formatted_lines = []
    current_length = 0

    for idx, result in enumerate(results, 1):
        text = result.get("text", "").strip()
        source = result.get("source", "unknown")
        score = result.get("score", 0.0)

        if not text:
            continue

        # Format: [Source #N | Score: X.XX] Text...
        line = f"[{source.capitalize()} #{idx} | Score: {score:.2f}]\n{text}\n"

        # Check if adding this would exceed max_length
        if current_length + len(line) > max_length:
            # Truncate text to fit
            remaining = max_length - current_length
            if remaining > 100:  # Only add if we have reasonable space
                truncated = text[: remaining - 50] + "..."
                line = f"[{source.capitalize()} #{idx} | Score: {score:.2f}]\n{truncated}\n"
                formatted_lines.append(line)
            break

        formatted_lines.append(line)
        current_length += len(line)

    return "\n".join(formatted_lines)


def _fallback_synthesis(query: str, results: list[dict[str, Any]]) -> str:
    """Fallback synthesis when LLM is unavailable.

    Args:
        query: Research question
        results: Search results

    Returns:
        Simple concatenation of top results
    """
    logger.warning("using_fallback_synthesis")

    # Take top 3 results by score
    top_results = sorted(
        results,
        key=lambda r: r.get("score", 0.0),
        reverse=True,
    )[:3]

    if not top_results:
        return "No information available."

    synthesis_parts = [f"Information found for: {query}\n"]

    for idx, result in enumerate(top_results, 1):
        text = result.get("text", "").strip()
        source = result.get("source", "unknown")

        if text:
            synthesis_parts.append(f"\n{idx}. [From {source}]\n{text}")

    return "\n".join(synthesis_parts)


async def create_structured_summary(
    query: str,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create structured summary of research findings.

    Args:
        query: Research question
        results: Search results

    Returns:
        Dict with structured summary components

    Examples:
        >>> summary = await create_structured_summary("What is AI?", results)
        >>> "key_points" in summary
        True
    """
    # Extract key information
    sources = list({r.get("source", "unknown") for r in results})
    top_results = sorted(
        results,
        key=lambda r: r.get("score", 0.0),
        reverse=True,
    )[:5]

    # Extract entities (from graph results)
    entities = []
    for r in results:
        if r.get("source") == "graph":
            entities.extend(r.get("entities", []))

    # Generate synthesis
    synthesis = await synthesize_findings(query, results)

    summary = {
        "query": query,
        "synthesis": synthesis,
        "num_results": len(results),
        "sources": sources,
        "key_findings": [
            {
                "text": r.get("text", "")[:200] + "...",
                "source": r.get("source", "unknown"),
                "score": r.get("score", 0.0),
            }
            for r in top_results
        ],
        "entities": list(set(entities))[:10],  # Top 10 unique entities
    }

    logger.info("structured_summary_created", query=query)

    return summary


def extract_citations(synthesis: str) -> list[int]:
    """Extract source citations from synthesis text.

    Args:
        synthesis: Synthesized text with citations

    Returns:
        List of cited source numbers

    Examples:
        >>> citations = extract_citations("According to [Source #1], AI is...")
        >>> citations
        [1]
    """
    import re

    # Find all [Source #N] patterns
    pattern = r"\[Source #(\d+)\]"
    matches = re.findall(pattern, synthesis)

    # Convert to integers and deduplicate
    cited_sources = sorted({int(match) for match in matches})

    logger.debug("citations_extracted", count=len(cited_sources), sources=cited_sources)

    return cited_sources


def extract_key_points(text: str, max_points: int = 5) -> list[str]:
    """Extract key points from synthesis text.

    Args:
        text: Synthesized text
        max_points: Maximum number of points

    Returns:
        List of key points
    """
    # Simple extraction: look for sentences with key indicators
    import re

    # Split into sentences
    sentences = re.split(r"[.!?]+", text)

    key_indicators = [
        "first",
        "second",
        "third",
        "importantly",
        "primarily",
        "mainly",
        "key",
        "critical",
        "essential",
    ]

    key_sentences = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Check for key indicators or high importance based on length and content
        if any(indicator in sentence.lower() for indicator in key_indicators) or (
            len(sentence) > 50 and len(sentence.split()) > 8
        ):
            key_sentences.append(sentence)

    # Return top N by position (earlier is more important)
    return key_sentences[:max_points]
