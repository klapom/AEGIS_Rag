"""Research Planning Component.

Sprint 59 Feature 59.6: Creates research strategies from user queries.

This module analyzes user queries and generates structured research plans
with specific search queries to execute.
"""

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def plan_research(query: str, max_queries: int = 5) -> list[str]:
    """Create a research plan for the given query.

    Generates 3-5 specific search queries that decompose the original
    question into targeted searches.

    Args:
        query: User's research question
        max_queries: Maximum number of search queries to generate

    Returns:
        List of search queries

    Examples:
        >>> plan = await plan_research("What is transformer architecture?")
        >>> len(plan)
        3
        >>> "transformer" in plan[0].lower()
        True
    """
    logger.info("planning_research", query=query, max_queries=max_queries)

    try:
        # Import LLM proxy
        from src.domains.llm_integration.proxy.aegis_llm_proxy import get_aegis_llm_proxy

        llm = get_aegis_llm_proxy()

        # Generate research plan
        planning_prompt = f"""Create a research plan to answer this question: "{query}"

Generate 3-5 specific search queries that will help find information to answer this question.
Each query should focus on a different aspect or approach.

Format your response as a numbered list:
1. [First search query]
2. [Second search query]
3. [Third search query]
etc.

Research plan:"""

        response = await llm.generate(
            prompt=planning_prompt,
            temperature=0.7,
            max_tokens=500,
        )

        # Parse the plan into individual queries
        queries = parse_plan(response)

        # Limit to max_queries
        queries = queries[:max_queries]

        logger.info("research_plan_created", num_queries=len(queries))

        return queries

    except Exception as e:
        logger.error("planning_failed", error=str(e), exc_info=True)
        # Fallback: use original query
        return [query]


def parse_plan(plan_text: str) -> list[str]:
    """Parse research plan text into list of queries.

    Args:
        plan_text: LLM-generated plan text

    Returns:
        List of parsed search queries

    Examples:
        >>> plan = "1. Search for X\\n2. Search for Y\\n3. Search for Z"
        >>> queries = parse_plan(plan)
        >>> len(queries)
        3
    """
    queries = []

    # Try numbered list format (1. 2. 3.)
    numbered_pattern = r"^\s*\d+\.\s*(.+)$"
    for line in plan_text.splitlines():
        match = re.match(numbered_pattern, line.strip())
        if match:
            query = match.group(1).strip()
            if query:
                queries.append(query)

    # Try bullet list format (- * •)
    if not queries:
        bullet_pattern = r"^\s*[-*•]\s*(.+)$"
        for line in plan_text.splitlines():
            match = re.match(bullet_pattern, line.strip())
            if match:
                query = match.group(1).strip()
                if query:
                    queries.append(query)

    # Try line-by-line (if no structure found)
    if not queries:
        for line in plan_text.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 10:
                queries.append(line)

    logger.debug("plan_parsed", num_queries=len(queries))

    return queries


def refine_query(original_query: str, previous_results: list[dict[str, Any]]) -> str:
    """Refine research query based on previous results.

    Args:
        original_query: Original user query
        previous_results: Results from previous searches

    Returns:
        Refined query string

    Examples:
        >>> refined = refine_query("What is AI?", [{"text": "AI is..."}])
        >>> isinstance(refined, str)
        True
    """
    # Simple refinement: add context from previous results
    if not previous_results:
        return original_query

    # Extract key terms from results
    result_texts = [r.get("text", "") for r in previous_results[:3]]
    combined_text = " ".join(result_texts)

    # Check if we have enough information
    if len(combined_text) > 500:
        # Add "more details" to dig deeper
        return f"{original_query} - provide more specific details"
    else:
        # Need more breadth
        return f"{original_query} - related concepts and background"


async def evaluate_plan_quality(
    query: str,
    plan: list[str],
) -> dict[str, Any]:
    """Evaluate the quality of a research plan.

    Args:
        query: Original query
        plan: List of search queries

    Returns:
        Dict with quality metrics

    Examples:
        >>> quality = await evaluate_plan_quality("What is AI?", ["AI definition", "AI history"])
        >>> quality["num_queries"]
        2
    """
    metrics = {
        "num_queries": len(plan),
        "avg_query_length": sum(len(q) for q in plan) / len(plan) if plan else 0,
        "coverage_score": min(len(plan) / 3.0, 1.0),  # Ideal: 3-5 queries
        "diversity_score": len(set(plan)) / len(plan) if plan else 0,
    }

    # Overall quality score (0-1)
    metrics["quality_score"] = metrics["coverage_score"] * 0.5 + metrics["diversity_score"] * 0.5

    logger.debug("plan_quality_evaluated", metrics=metrics)

    return metrics
