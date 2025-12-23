"""Multi-Source Search Component.

Sprint 59 Feature 59.6: Executes searches across multiple sources.

This module handles search execution across:
- Vector search (Qdrant)
- Graph search (Neo4j)
- Hybrid search (RRF fusion)
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def execute_searches(
    queries: list[str],
    top_k: int = 5,
    use_graph: bool = True,
    use_vector: bool = True,
) -> list[dict[str, Any]]:
    """Execute multiple search queries across all sources.

    Args:
        queries: List of search queries to execute
        top_k: Number of results per query
        use_graph: Enable graph search
        use_vector: Enable vector search

    Returns:
        List of search results with metadata

    Examples:
        >>> results = await execute_searches(["AI", "ML"], top_k=3)
        >>> len(results) >= 0
        True
    """
    logger.info(
        "executing_searches",
        num_queries=len(queries),
        top_k=top_k,
        use_graph=use_graph,
        use_vector=use_vector,
    )

    all_results = []

    for query in queries:
        query_results = await execute_single_query(
            query=query,
            top_k=top_k,
            use_graph=use_graph,
            use_vector=use_vector,
        )
        all_results.extend(query_results)

    # Deduplicate results
    unique_results = deduplicate_results(all_results)

    logger.info(
        "searches_completed",
        total_results=len(all_results),
        unique_results=len(unique_results),
    )

    return unique_results


async def execute_single_query(
    query: str,
    top_k: int = 5,
    use_graph: bool = True,
    use_vector: bool = True,
) -> list[dict[str, Any]]:
    """Execute a single query across all enabled sources.

    Args:
        query: Search query
        top_k: Number of results
        use_graph: Enable graph search
        use_vector: Enable vector search

    Returns:
        List of results for this query
    """
    results = []

    try:
        # Vector search
        if use_vector:
            vector_results = await _execute_vector_search(query, top_k)
            results.extend(vector_results)

        # Graph search
        if use_graph:
            graph_results = await _execute_graph_search(query, top_k)
            results.extend(graph_results)

    except Exception as e:
        logger.error("query_execution_failed", query=query, error=str(e))

    return results


async def _execute_vector_search(query: str, top_k: int) -> list[dict[str, Any]]:
    """Execute vector search against Qdrant.

    Args:
        query: Search query
        top_k: Number of results

    Returns:
        List of vector search results
    """
    try:
        from src.components.vector_search.hybrid import search_hybrid

        results = await search_hybrid(
            query=query,
            top_k=top_k,
            alpha=0.5,  # Equal weighting for vector and BM25
        )

        # Format results
        formatted = [
            {
                "text": r.get("text", ""),
                "score": r.get("score", 0.0),
                "source": "vector",
                "metadata": r.get("metadata", {}),
                "query": query,
            }
            for r in results
        ]

        logger.debug("vector_search_completed", query=query, count=len(formatted))

        return formatted

    except Exception as e:
        logger.error("vector_search_failed", query=query, error=str(e))
        return []


async def _execute_graph_search(query: str, top_k: int) -> list[dict[str, Any]]:
    """Execute graph search against Neo4j.

    Args:
        query: Search query
        top_k: Number of results

    Returns:
        List of graph search results
    """
    try:
        from src.components.graph_rag.query import query_graph

        results = await query_graph(
            query=query,
            mode="hybrid",  # Use hybrid mode for best results
            top_k=top_k,
        )

        # Format results
        formatted = [
            {
                "text": r.get("text", ""),
                "score": r.get("score", 0.0),
                "source": "graph",
                "entities": r.get("entities", []),
                "relationships": r.get("relationships", []),
                "metadata": r.get("metadata", {}),
                "query": query,
            }
            for r in results
        ]

        logger.debug("graph_search_completed", query=query, count=len(formatted))

        return formatted

    except Exception as e:
        logger.error("graph_search_failed", query=query, error=str(e))
        return []


def deduplicate_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate results based on text content.

    Args:
        results: List of search results

    Returns:
        Deduplicated list
    """
    seen_texts = set()
    unique_results = []

    for result in results:
        text = result.get("text", "")
        # Use first 200 chars as key to handle minor variations
        text_key = text[:200].strip().lower()

        if text_key and text_key not in seen_texts:
            seen_texts.add(text_key)
            unique_results.append(result)

    logger.debug(
        "results_deduplicated",
        original=len(results),
        unique=len(unique_results),
    )

    return unique_results


def rank_results(
    results: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    """Re-rank results by relevance to original query.

    Args:
        results: Search results
        query: Original query

    Returns:
        Re-ranked results
    """
    # Simple ranking: prioritize by score and source diversity
    ranked = sorted(
        results,
        key=lambda r: (
            r.get("score", 0.0) * 2.0 if r.get("source") == "graph" else 1.0,
            r.get("score", 0.0),
        ),
        reverse=True,
    )

    logger.debug("results_ranked", count=len(ranked))

    return ranked


async def evaluate_results(
    results: list[dict[str, Any]],
    query: str,
) -> dict[str, Any]:
    """Evaluate search results quality and coverage.

    Args:
        results: Search results
        query: Original query

    Returns:
        Dict with evaluation metrics
    """
    if not results:
        return {
            "coverage": 0.0,
            "diversity": 0.0,
            "quality": 0.0,
            "sufficient": False,
        }

    # Calculate metrics
    num_results = len(results)
    sources = {r.get("source", "unknown") for r in results}
    avg_score = sum(r.get("score", 0.0) for r in results) / num_results

    metrics = {
        "num_results": num_results,
        "num_sources": len(sources),
        "avg_score": avg_score,
        "coverage": min(num_results / 10.0, 1.0),  # Ideal: 10+ results
        "diversity": min(len(sources) / 2.0, 1.0),  # Ideal: 2 sources (vector + graph)
        "quality": min(avg_score, 1.0),
        "sufficient": num_results >= 5 and avg_score > 0.5,
    }

    logger.info("results_evaluated", metrics=metrics)

    return metrics
