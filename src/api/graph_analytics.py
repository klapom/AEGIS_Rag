"""Graph Analytics API Router.

This module provides FastAPI endpoints for graph analytics:
- Centrality metrics
- PageRank scores
- Influential entity detection
- Knowledge gap analysis
- Entity recommendations
- Graph statistics
"""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status

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
    summary="Get centrality metrics for entity",
    description="Calculate centrality metrics (degree, betweenness, closeness, eigenvector) for an entity",
)
async def get_entity_centrality(
    entity_id: str,
    metric: Annotated[
        CentralityMetric, Query(description="Centrality metric to calculate")
    ] = "degree",
) -> CentralityMetrics:
    """Get centrality metrics for an entity.

    Args:
        entity_id: Entity ID to analyze
        metric: Centrality metric (degree, betweenness, closeness, eigenvector)

    Returns:
        CentralityMetrics with calculated values

    Raises:
        HTTPException: If calculation fails
    """
    logger.info("Calculating centrality", entity_id=entity_id, metric=metric)

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
    summary="Get PageRank scores",
    description="Calculate PageRank scores for top entities",
)
async def get_pagerank_scores(
    top_k: Annotated[int, Query(ge=1, le=100, description="Number of top entities")] = 10,
) -> list[dict[str, Any]]:
    """Get PageRank scores for top entities.

    Args:
        top_k: Number of top entities to return (1-100)

    Returns:
        List of {"entity_id": str, "score": float} dictionaries

    Raises:
        HTTPException: If calculation fails
    """
    logger.info("Calculating PageRank scores", top_k=top_k)

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
    summary="Get most influential entities",
    description="Find the most influential entities by PageRank",
)
async def get_influential_entities(
    top_k: Annotated[int, Query(ge=1, le=100, description="Number of top entities")] = 10,
) -> list[dict[str, Any]]:
    """Get most influential entities.

    Args:
        top_k: Number of top entities to return (1-100)

    Returns:
        List of {"entity_id": str, "score": float} dictionaries

    Raises:
        HTTPException: If calculation fails
    """
    logger.info("Finding influential entities", top_k=top_k)

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
    summary="Detect knowledge gaps",
    description="Identify knowledge gaps (orphan entities, sparse areas, isolated components)",
)
async def detect_knowledge_gaps() -> dict[str, Any]:
    """Detect knowledge gaps in the graph.

    Returns:
        Dictionary with:
        - orphan_entities: Entities with no connections
        - sparse_entities: Entities with 1-2 connections
        - isolated_components: Number of disconnected subgraphs

    Raises:
        HTTPException: If detection fails
    """
    logger.info("Detecting knowledge gaps")

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
    summary="Get entity recommendations",
    description="Get recommendations for similar or related entities",
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
) -> list[Recommendation]:
    """Get entity recommendations.

    Args:
        entity_id: Source entity ID
        method: Recommendation method (collaborative, community, relationships, attributes)
        top_k: Number of recommendations (1-50)

    Returns:
        List of Recommendation objects

    Raises:
        HTTPException: If recommendation fails
    """
    logger.info("Getting entity recommendations", entity_id=entity_id, method=method, top_k=top_k)

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
    summary="Get graph statistics",
    description="Get overall graph statistics and metrics",
)
async def get_graph_statistics() -> GraphStatistics:
    """Get overall graph statistics.

    Returns:
        GraphStatistics with graph-level metrics

    Raises:
        HTTPException: If calculation fails
    """
    logger.info("Getting graph statistics")

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
