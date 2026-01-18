"""Research Search Execution - Reuses CoordinatorAgent.

Sprint 70: Deep Research & Tool Use Integration

This module executes research queries by reusing the existing CoordinatorAgent
infrastructure instead of duplicating search logic. This ensures consistency
and reduces code duplication.

Key Design:
- Reuses FourWayHybridSearch via CoordinatorAgent
- No duplicate imports of vector/graph search
- Leverages existing routing and retrieval logic
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def execute_research_queries(
    queries: list[str],
    namespace: str = "default",
    top_k_per_query: int = 5,
) -> list[dict[str, Any]]:
    """Execute multiple research queries using CoordinatorAgent.

    Instead of duplicating search logic, this function reuses the existing
    CoordinatorAgent which already handles:
    - Intent classification
    - FourWayHybridSearch (Vector + BM25 + Graph Local + Graph Global)
    - RRF fusion
    - Result deduplication

    Args:
        queries: List of search queries to execute
        namespace: Namespace to search in
        top_k_per_query: Number of results per query

    Returns:
        List of all retrieved contexts (deduplicated)

    Examples:
        >>> contexts = await execute_research_queries(["AI", "ML"], top_k_per_query=5)
        >>> len(contexts) >= 0
        True
    """
    logger.info(
        "executing_research_queries",
        num_queries=len(queries),
        namespace=namespace,
        top_k_per_query=top_k_per_query,
    )

    all_contexts = []

    # Import coordinator (lazy to avoid circular imports)
    from src.agents.coordinator import CoordinatorAgent

    # Create coordinator instance
    coordinator = CoordinatorAgent()

    for idx, query in enumerate(queries, 1):
        logger.debug(
            "executing_research_query",
            query_num=idx,
            total=len(queries),
            query=query,
        )

        try:
            # Use CoordinatorAgent to process query
            # This automatically handles:
            # - Intent classification (hybrid is best for research)
            # - FourWayHybridSearch execution
            # - Result fusion and ranking
            result = await coordinator.process_query(
                query=query,
                intent="hybrid",  # Always use hybrid for research
                namespaces=[namespace],  # CoordinatorAgent expects list of namespaces
            )

            # Extract retrieved contexts from result
            contexts = result.get("retrieved_contexts", [])

            # Add query metadata for tracking
            for ctx in contexts:
                ctx["research_query"] = query
                ctx["query_index"] = idx

            all_contexts.extend(contexts)

            logger.debug(
                "research_query_completed",
                query_num=idx,
                contexts_retrieved=len(contexts),
            )

        except Exception as e:
            logger.error(
                "research_query_failed",
                query_num=idx,
                query=query,
                error=str(e),
                exc_info=True,
            )
            # Continue with remaining queries

    # Deduplicate across all queries
    unique_contexts = deduplicate_contexts(all_contexts)

    logger.info(
        "research_queries_completed",
        total_contexts=len(all_contexts),
        unique_contexts=len(unique_contexts),
    )

    return unique_contexts


def deduplicate_contexts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate contexts based on text content.

    Args:
        contexts: List of context dicts

    Returns:
        Deduplicated list

    Examples:
        >>> contexts = [{"text": "A"}, {"text": "A"}, {"text": "B"}]
        >>> unique = deduplicate_contexts(contexts)
        >>> len(unique)
        2
    """
    seen_texts = set()
    unique_contexts = []

    for ctx in contexts:
        text = ctx.get("text", "")

        # Use first 200 chars as key to handle minor variations
        text_key = text[:200].strip().lower()

        if text_key and text_key not in seen_texts:
            seen_texts.add(text_key)
            unique_contexts.append(ctx)

    logger.debug(
        "contexts_deduplicated",
        original=len(contexts),
        unique=len(unique_contexts),
    )

    return unique_contexts


def evaluate_search_quality(contexts: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate the quality of search results.

    Args:
        contexts: Retrieved contexts

    Returns:
        Dict with quality metrics

    Examples:
        >>> metrics = evaluate_search_quality([{"text": "...", "score": 0.8}])
        >>> "sufficient" in metrics
        True
    """
    if not contexts:
        return {
            "num_results": 0,
            "avg_score": 0.0,
            "sufficient": False,
            "quality": "poor",
        }

    num_results = len(contexts)
    avg_score = sum(ctx.get("score", 0.0) for ctx in contexts) / num_results

    # Determine quality level
    if num_results >= 10 and avg_score > 0.7:
        quality = "excellent"
    elif num_results >= 5 and avg_score > 0.5:
        quality = "good"
    elif num_results >= 3:
        quality = "fair"
    else:
        quality = "poor"

    metrics = {
        "num_results": num_results,
        "avg_score": avg_score,
        "sufficient": num_results >= 5 and avg_score > 0.5,
        "quality": quality,
    }

    logger.debug("search_quality_evaluated", metrics=metrics)

    return metrics
