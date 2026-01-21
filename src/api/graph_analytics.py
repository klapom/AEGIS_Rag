"""Graph Analytics API Router.

⚠️ **DEPRECATED as of Sprint 72** ⚠️

This module will be REMOVED in Sprint 73.

Reason: Endpoints implemented but never integrated into frontend (dead code).

Migration Guide: docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md

Replacement:
- For statistics: Use /api/v1/graph/viz/statistics instead
- For other endpoints: No replacement (unused features)

---

This module provides FastAPI endpoints for graph analytics:
- Centrality metrics
- PageRank scores
- Influential entity detection
- Knowledge gap analysis
- Entity recommendations
- Graph statistics
"""

import warnings
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Response, status

# Issue deprecation warning at module level
warnings.warn(
    "graph_analytics module is deprecated and will be removed in Sprint 73. "
    "See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md",
    DeprecationWarning,
    stacklevel=2,
)

from src.components.graph_rag.analytics_engine import (
    CentralityMetric,
    get_analytics_engine,
)
from src.components.graph_rag.recommendation_engine import (
    RecommendationMethod,
    get_recommendation_engine,
)
from src.core.exceptions import DatabaseConnectionError
from src.core.logging import get_logger
from src.core.models import CentralityMetrics, GraphStatistics, Recommendation

logger = get_logger(__name__)

router = APIRouter(prefix="/graph/analytics", tags=["analytics"])


# Endpoints


@router.get(
    "/centrality/{entity_id}",
    response_model=CentralityMetrics,
    summary="[DEPRECATED] Get centrality metrics for entity",
    description="⚠️ DEPRECATED: This endpoint will be removed in Sprint 73. No replacement available (unused feature).",
    deprecated=True,
)
async def get_entity_centrality(
    entity_id: str,
    metric: Annotated[
        CentralityMetric, Query(description="Centrality metric to calculate")
    ] = "degree",
    response: Response = None,
) -> CentralityMetrics:
    """Get centrality metrics for an entity.

    ⚠️ DEPRECATED: This endpoint will be removed in Sprint 73.
    See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md

    Args:
        entity_id: Entity ID to analyze
        metric: Centrality metric (degree, betweenness, closeness, eigenvector)

    Returns:
        CentralityMetrics with calculated values

    Raises:
        HTTPException: If calculation fails
    """
    # Add deprecation headers
    if response:
        response.headers["Warning"] = (
            '299 - "DEPRECATED: This endpoint will be removed in Sprint 73. '
            'See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md"'
        )
        response.headers["X-Deprecation-Date"] = "2026-01-06"
        response.headers["X-Removal-Sprint"] = "73"

    logger.warning("Using deprecated endpoint", entity_id=entity_id, metric=metric)

    try:
        engine = get_analytics_engine()
        metrics = await engine.calculate_centrality(entity_id, metric)
        return metrics

    except DatabaseConnectionError as e:
        logger.error("Database error calculating centrality", error=str(e), entity_id=entity_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to calculate centrality", error=str(e), entity_id=entity_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Centrality calculation failed: {str(e)}",
        ) from e


@router.get(
    "/pagerank",
    response_model=list[dict[str, Any]],
    summary="[DEPRECATED] Get PageRank scores",
    description="⚠️ DEPRECATED: This endpoint will be removed in Sprint 73. No replacement available (unused feature).",
    deprecated=True,
)
async def get_pagerank_scores(
    top_k: Annotated[int, Query(ge=1, le=100, description="Number of top entities")] = 10,
    response: Response = None,
) -> list[dict[str, Any]]:
    """Get PageRank scores for top entities.

    ⚠️ DEPRECATED: This endpoint will be removed in Sprint 73.
    See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md

    Args:
        top_k: Number of top entities to return (1-100)

    Returns:
        List of {"entity_id": str, "score": float} dictionaries

    Raises:
        HTTPException: If calculation fails
    """
    # Add deprecation headers
    if response:
        response.headers["Warning"] = (
            '299 - "DEPRECATED: This endpoint will be removed in Sprint 73. '
            'See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md"'
        )
        response.headers["X-Deprecation-Date"] = "2026-01-06"
        response.headers["X-Removal-Sprint"] = "73"

    logger.warning("Using deprecated endpoint", top_k=top_k)

    try:
        engine = get_analytics_engine()
        scores = await engine.calculate_pagerank()
        return scores[:top_k]

    except DatabaseConnectionError as e:
        logger.error("Database error calculating PageRank", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to calculate PageRank", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PageRank calculation failed: {str(e)}",
        ) from e


@router.get(
    "/influential",
    response_model=list[dict[str, Any]],
    summary="[DEPRECATED] Get most influential entities",
    description="⚠️ DEPRECATED: This endpoint will be removed in Sprint 73. No replacement available (unused feature).",
    deprecated=True,
)
async def get_influential_entities(
    top_k: Annotated[int, Query(ge=1, le=100, description="Number of top entities")] = 10,
    response: Response = None,
) -> list[dict[str, Any]]:
    """Get most influential entities.

    ⚠️ DEPRECATED: This endpoint will be removed in Sprint 73.
    See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md

    Args:
        top_k: Number of top entities to return (1-100)

    Returns:
        List of {"entity_id": str, "score": float} dictionaries

    Raises:
        HTTPException: If calculation fails
    """
    # Add deprecation headers
    if response:
        response.headers["Warning"] = (
            '299 - "DEPRECATED: This endpoint will be removed in Sprint 73. '
            'See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md"'
        )
        response.headers["X-Deprecation-Date"] = "2026-01-06"
        response.headers["X-Removal-Sprint"] = "73"

    logger.warning("Using deprecated endpoint", top_k=top_k)

    try:
        engine = get_analytics_engine()
        entities = await engine.find_influential_entities(top_k)
        return entities

    except DatabaseConnectionError as e:
        logger.error("Database error finding influential entities", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to find influential entities", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Influential entity detection failed: {str(e)}",
        ) from e


@router.get(
    "/gaps",
    response_model=dict[str, Any],
    summary="[DEPRECATED] Detect knowledge gaps",
    description="⚠️ DEPRECATED: This endpoint will be removed in Sprint 73. No replacement available (unused feature).",
    deprecated=True,
)
async def detect_knowledge_gaps(response: Response = None) -> dict[str, Any]:
    """Detect knowledge gaps in the graph.

    ⚠️ DEPRECATED: This endpoint will be removed in Sprint 73.
    See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md

    Returns:
        Dictionary with:
        - orphan_entities: Entities with no connections
        - sparse_entities: Entities with 1-2 connections
        - isolated_components: Number of disconnected subgraphs

    Raises:
        HTTPException: If detection fails
    """
    # Add deprecation headers
    if response:
        response.headers["Warning"] = (
            '299 - "DEPRECATED: This endpoint will be removed in Sprint 73. '
            'See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md"'
        )
        response.headers["X-Deprecation-Date"] = "2026-01-06"
        response.headers["X-Removal-Sprint"] = "73"

    logger.warning("Using deprecated endpoint")

    try:
        engine = get_analytics_engine()
        gaps = await engine.detect_knowledge_gaps()
        return gaps

    except DatabaseConnectionError as e:
        logger.error("Database error detecting knowledge gaps", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to detect knowledge gaps", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge gap detection failed: {str(e)}",
        ) from e


@router.get(
    "/recommendations/{entity_id}",
    response_model=list[Recommendation],
    summary="[DEPRECATED] Get entity recommendations",
    description="⚠️ DEPRECATED: This endpoint will be removed in Sprint 73. No replacement available (unused feature).",
    deprecated=True,
)
async def get_entity_recommendations(
    entity_id: str,
    method: Annotated[
        RecommendationMethod,
        Query(
            description="Recommendation method (collaborative, community, relationships, attributes)"
        ),
    ] = "collaborative",
    top_k: Annotated[int, Query(ge=1, le=50, description="Number of recommendations")] = 5,
    response: Response = None,
) -> list[Recommendation]:
    """Get entity recommendations.

    ⚠️ DEPRECATED: This endpoint will be removed in Sprint 73.
    See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md

    Args:
        entity_id: Source entity ID
        method: Recommendation method (collaborative, community, relationships, attributes)
        top_k: Number of recommendations (1-50)

    Returns:
        List of Recommendation objects

    Raises:
        HTTPException: If recommendation fails
    """
    # Add deprecation headers
    if response:
        response.headers["Warning"] = (
            '299 - "DEPRECATED: This endpoint will be removed in Sprint 73. '
            'See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md"'
        )
        response.headers["X-Deprecation-Date"] = "2026-01-06"
        response.headers["X-Removal-Sprint"] = "73"

    logger.warning("Using deprecated endpoint", entity_id=entity_id, method=method, top_k=top_k)

    try:
        engine = get_recommendation_engine()
        recommendations = await engine.recommend_similar_entities(entity_id, method, top_k)
        return recommendations

    except DatabaseConnectionError as e:
        logger.error("Database error getting recommendations", error=str(e), entity_id=entity_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to get recommendations", error=str(e), entity_id=entity_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendation generation failed: {str(e)}",
        ) from e


@router.get(
    "/statistics",
    response_model=GraphStatistics,
    summary="[DEPRECATED] Get graph statistics",
    description="⚠️ DEPRECATED: This endpoint will be removed in Sprint 73. Use /api/v1/graph/viz/statistics instead.",
    deprecated=True,
)
async def get_graph_statistics(response: Response = None) -> GraphStatistics:
    """Get overall graph statistics.

    ⚠️ DEPRECATED: This endpoint will be removed in Sprint 73.
    Use /api/v1/graph/viz/statistics instead.
    See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md

    Returns:
        GraphStatistics with graph-level metrics

    Raises:
        HTTPException: If calculation fails
    """
    # Add deprecation headers
    if response:
        response.headers["Warning"] = (
            '299 - "DEPRECATED: This endpoint will be removed in Sprint 73. '
            "Use /api/v1/graph/viz/statistics instead. "
            'See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md"'
        )
        response.headers["X-Deprecation-Date"] = "2026-01-06"
        response.headers["X-Removal-Sprint"] = "73"
        response.headers["X-Replacement"] = "/api/v1/graph/viz/statistics"

    logger.warning("Using deprecated endpoint")

    try:
        engine = get_analytics_engine()
        stats = await engine.get_graph_statistics()
        return stats

    except DatabaseConnectionError as e:
        logger.error("Database error getting graph statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to get graph statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph statistics calculation failed: {str(e)}",
        ) from e
