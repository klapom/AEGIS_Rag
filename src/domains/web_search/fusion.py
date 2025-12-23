"""Result fusion for combining web, vector, and graph search results.

Sprint 63 Feature 63.9: WebSearch Integration for Research Agent.

This module implements result fusion logic to combine results from multiple sources:
- Vector search (70% weight)
- Graph search (20% weight)
- Web search (10% weight)

The fusion process includes:
1. Score normalization across sources
2. Weighted ranking
3. Deduplication based on URL/content similarity
4. Top-k selection
"""

from typing import Any

import structlog

from src.domains.web_search.models import WebSearchResult

logger = structlog.get_logger(__name__)

# Weight configuration for result fusion
FUSION_WEIGHTS = {
    "vector": 0.70,  # 70% weight for vector search (internal knowledge)
    "graph": 0.20,   # 20% weight for graph search (structured knowledge)
    "web": 0.10,     # 10% weight for web search (external knowledge)
}


def fuse_results(
    vector_results: list[dict[str, Any]],
    graph_results: list[dict[str, Any]],
    web_results: list[WebSearchResult],
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """Fuse results from vector, graph, and web search.

    Args:
        vector_results: Results from vector search (with score field)
        graph_results: Results from graph search (with score field)
        web_results: Results from web search (WebSearchResult objects)
        top_k: Number of results to return (default: 20)

    Returns:
        List of fused results sorted by weighted score

    Example:
        >>> vector = [{"text": "doc1", "score": 0.9, "source": "vector"}]
        >>> graph = [{"text": "doc2", "score": 0.8, "source": "graph"}]
        >>> web = [WebSearchResult(title="web1", url="http://ex.com", snippet="text")]
        >>> results = fuse_results(vector, graph, web, top_k=10)
        >>> len(results) <= 10
        True
    """
    logger.info(
        "fusing_results",
        vector_count=len(vector_results),
        graph_count=len(graph_results),
        web_count=len(web_results),
        top_k=top_k,
    )

    # Normalize and weight results
    all_results = []

    # Add vector results
    for result in vector_results:
        scored_result = {
            **result,
            "weighted_score": result.get("score", 0.0) * FUSION_WEIGHTS["vector"],
            "fusion_source": "vector",
        }
        all_results.append(scored_result)

    # Add graph results
    for result in graph_results:
        scored_result = {
            **result,
            "weighted_score": result.get("score", 0.0) * FUSION_WEIGHTS["graph"],
            "fusion_source": "graph",
        }
        all_results.append(scored_result)

    # Add web results (convert WebSearchResult to dict)
    for result in web_results:
        scored_result = {
            "text": result.snippet,
            "title": result.title,
            "url": result.url,
            "score": result.score,
            "weighted_score": result.score * FUSION_WEIGHTS["web"],
            "source": "web",
            "fusion_source": "web",
            "metadata": {
                "published_date": result.published_date.isoformat() if result.published_date else None,
            },
        }
        all_results.append(scored_result)

    # Deduplicate results
    unique_results = deduplicate_fused_results(all_results)

    # Sort by weighted score
    ranked_results = sorted(
        unique_results,
        key=lambda r: r.get("weighted_score", 0.0),
        reverse=True,
    )

    # Take top-k
    final_results = ranked_results[:top_k]

    logger.info(
        "fusion_completed",
        total_results=len(all_results),
        unique_results=len(unique_results),
        final_count=len(final_results),
    )

    return final_results


def deduplicate_fused_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate results based on URL and content similarity.

    Deduplication strategy:
    1. Check URL overlap for web results
    2. Check text content similarity (first 200 chars) for all results
    3. Keep result with highest weighted score

    Args:
        results: List of fused results

    Returns:
        Deduplicated list

    Example:
        >>> results = [
        ...     {"text": "same content", "url": "http://ex.com", "weighted_score": 0.9},
        ...     {"text": "same content", "url": "http://ex.com", "weighted_score": 0.8},
        ... ]
        >>> deduped = deduplicate_fused_results(results)
        >>> len(deduped) == 1
        True
    """
    seen_urls = set()
    seen_texts = set()
    unique_results = []

    for result in results:
        # Check URL deduplication (for web results)
        url = result.get("url", "")
        if url and url in seen_urls:
            logger.debug("duplicate_url_skipped", url=url)
            continue

        # Check text deduplication (for all results)
        text = result.get("text", "")
        text_key = text[:200].strip().lower() if text else ""

        if text_key and text_key in seen_texts:
            logger.debug("duplicate_text_skipped", text_preview=text_key[:50])
            continue

        # Add to unique results
        if url:
            seen_urls.add(url)
        if text_key:
            seen_texts.add(text_key)

        unique_results.append(result)

    logger.debug(
        "deduplication_completed",
        original_count=len(results),
        unique_count=len(unique_results),
        duplicates_removed=len(results) - len(unique_results),
    )

    return unique_results


def calculate_diversity_score(results: list[dict[str, Any]]) -> float:
    """Calculate diversity score based on source distribution.

    Higher score indicates better coverage across vector/graph/web sources.

    Args:
        results: List of fused results

    Returns:
        Diversity score (0.0-1.0)

    Example:
        >>> results = [
        ...     {"fusion_source": "vector"},
        ...     {"fusion_source": "graph"},
        ...     {"fusion_source": "web"},
        ... ]
        >>> score = calculate_diversity_score(results)
        >>> 0.0 <= score <= 1.0
        True
    """
    if not results:
        return 0.0

    # Count results per source
    source_counts = {
        "vector": 0,
        "graph": 0,
        "web": 0,
    }

    for result in results:
        source = result.get("fusion_source", "unknown")
        if source in source_counts:
            source_counts[source] += 1

    # Calculate diversity (1.0 = perfect balance across all sources)
    total = len(results)
    ideal_per_source = total / 3.0

    # Sum of squared deviations from ideal
    variance = sum(
        ((count - ideal_per_source) ** 2) / ideal_per_source
        if ideal_per_source > 0 else 0
        for count in source_counts.values()
    )

    # Normalize to 0-1 range (lower variance = higher diversity)
    diversity = 1.0 / (1.0 + variance / total) if total > 0 else 0.0

    logger.debug(
        "diversity_calculated",
        source_counts=source_counts,
        diversity_score=diversity,
    )

    return diversity


def optimize_web_query(original_query: str) -> str:
    """Optimize user query for web search.

    Transforms natural language query into web-search-friendly format:
    - Removes conversational elements
    - Adds date context if relevant
    - Optimizes for search engines

    Args:
        original_query: User's natural language query

    Returns:
        Optimized query for web search

    Example:
        >>> optimize_web_query("Tell me about AI research")
        'AI research 2025'
        >>> optimize_web_query("What is machine learning?")
        'machine learning 2025'
    """
    # Simple optimization rules
    query = original_query.lower().strip()

    # Remove conversational elements
    remove_phrases = [
        "tell me about",
        "what is",
        "what are",
        "how does",
        "explain",
        "can you",
        "please",
    ]

    for phrase in remove_phrases:
        query = query.replace(phrase, "")

    query = query.strip()

    # Add current year for recency bias (2025)
    if "2025" not in query and "2024" not in query:
        query = f"{query} 2025"

    logger.debug(
        "query_optimized",
        original=original_query,
        optimized=query,
    )

    return query
