"""Graph Visualization API Router.

This module provides FastAPI endpoints for graph visualization:
- Entity neighborhood visualization
- Custom subgraph visualization
- Community graph visualization

Supports multiple output formats (D3.js, Cytoscape.js, vis.js).
"""

from typing import Annotated, Any, Dict

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.components.graph_rag.visualization_export import (
    VisualizationFormat,
    get_visualization_exporter,
)
from src.core.exceptions import DatabaseConnectionError
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/graph", tags=["visualization"])


# Response Models
class VisualizationResponse(BaseModel):
    """Graph visualization response."""

    data: Dict[str, Any] = Field(..., description="Visualization data in requested format")
    metadata: Dict[str, Any] = Field(..., description="Metadata (node_count, edge_count, etc.)")


# Endpoints
# NOTE: Specific routes MUST be defined BEFORE generic catch-all routes with path parameters
# to ensure proper routing (e.g., /visualize/subgraph must come before /visualize/{entity_id})


@router.get(
    "/visualize/subgraph",
    response_model=VisualizationResponse,
    summary="Get custom subgraph visualization",
    description="Retrieve a visualization of a custom subgraph starting from multiple entities",
)
async def visualize_custom_subgraph(
    entity_ids: Annotated[list[str], Query(description="List of entity IDs")],
    depth: Annotated[int, Query(ge=1, le=5, description="Traversal depth")] = 1,
    max_nodes: Annotated[int, Query(ge=1, le=1000, description="Maximum nodes to return")] = 100,
    format: Annotated[
        VisualizationFormat, Query(description="Output format (d3, cytoscape, visjs)")
    ] = "d3",
) -> VisualizationResponse:
    """Get visualization of a custom subgraph.

    Args:
        entity_ids: List of entity IDs to start from
        depth: Graph traversal depth (1-5)
        max_nodes: Maximum number of nodes (1-1000)
        format: Output format (d3, cytoscape, visjs)

    Returns:
        VisualizationResponse with graph data

    Raises:
        HTTPException: If visualization fails
    """
    logger.info(
        "Visualizing custom subgraph",
        entity_count=len(entity_ids),
        depth=depth,
        max_nodes=max_nodes,
        format=format,
    )

    if not entity_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one entity_id is required",
        )

    try:
        exporter = get_visualization_exporter()
        result = await exporter.export_subgraph(
            entity_ids=entity_ids, depth=depth, max_nodes=max_nodes, format=format
        )

        # Extract metadata from result
        metadata = result.pop("metadata", {})

        return VisualizationResponse(data=result, metadata=metadata)

    except DatabaseConnectionError as e:
        logger.error("Database error visualizing subgraph", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to visualize subgraph", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visualization failed: {str(e)}",
        ) from e


@router.get(
    "/visualize/{entity_id}",
    response_model=VisualizationResponse,
    summary="Get entity neighborhood visualization",
    description="Retrieve a visualization of the entity's neighborhood graph",
)
async def visualize_entity_neighborhood(
    entity_id: str,
    depth: Annotated[int, Query(ge=1, le=5, description="Traversal depth")] = 1,
    max_nodes: Annotated[int, Query(ge=1, le=1000, description="Maximum nodes to return")] = 100,
    format: Annotated[
        VisualizationFormat, Query(description="Output format (d3, cytoscape, visjs)")
    ] = "d3",
) -> VisualizationResponse:
    """Get visualization of an entity's neighborhood.

    Args:
        entity_id: Entity ID to visualize
        depth: Graph traversal depth (1-5)
        max_nodes: Maximum number of nodes (1-1000)
        format: Output format (d3, cytoscape, visjs)

    Returns:
        VisualizationResponse with graph data

    Raises:
        HTTPException: If visualization fails
    """
    logger.info(
        "Visualizing entity neighborhood",
        entity_id=entity_id,
        depth=depth,
        max_nodes=max_nodes,
        format=format,
    )

    try:
        exporter = get_visualization_exporter()
        result = await exporter.export_subgraph(
            entity_ids=[entity_id], depth=depth, max_nodes=max_nodes, format=format
        )

        # Extract metadata from result
        metadata = result.pop("metadata", {})

        return VisualizationResponse(data=result, metadata=metadata)

    except DatabaseConnectionError as e:
        logger.error("Database error visualizing entity", error=str(e), entity_id=entity_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to visualize entity", error=str(e), entity_id=entity_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visualization failed: {str(e)}",
        ) from e


@router.get(
    "/visualize/community/{community_id}",
    response_model=VisualizationResponse,
    summary="Get community graph visualization",
    description="Retrieve a visualization of entities within a specific community",
)
async def visualize_community(
    community_id: str,
    max_nodes: Annotated[int, Query(ge=1, le=1000, description="Maximum nodes to return")] = 100,
    format: Annotated[
        VisualizationFormat, Query(description="Output format (d3, cytoscape, visjs)")
    ] = "d3",
) -> VisualizationResponse:
    """Get visualization of a community.

    Args:
        community_id: Community ID to visualize
        max_nodes: Maximum number of nodes (1-1000)
        format: Output format (d3, cytoscape, visjs)

    Returns:
        VisualizationResponse with graph data

    Raises:
        HTTPException: If visualization fails
    """
    logger.info(
        "Visualizing community", community_id=community_id, max_nodes=max_nodes, format=format
    )

    try:
        exporter = get_visualization_exporter()

        # Get entity IDs in the community
        neo4j_client = exporter.neo4j_client
        query = """
        MATCH (n)
        WHERE n.community_id = $community_id
        RETURN n.id AS entity_id
        LIMIT $max_nodes
        """
        result = await neo4j_client.execute_query(
            query, {"community_id": community_id, "max_nodes": max_nodes}
        )

        entity_ids = [row["entity_id"] for row in result]

        if not entity_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Community {community_id} not found or has no entities",
            )

        # Export subgraph for these entities
        viz_result = await exporter.export_subgraph(
            entity_ids=entity_ids, depth=1, max_nodes=max_nodes, format=format
        )

        # Extract metadata from result
        metadata = viz_result.pop("metadata", {})
        metadata["community_id"] = community_id

        return VisualizationResponse(data=viz_result, metadata=metadata)

    except HTTPException:
        raise
    except DatabaseConnectionError as e:
        logger.error(
            "Database error visualizing community", error=str(e), community_id=community_id
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to visualize community", error=str(e), community_id=community_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visualization failed: {str(e)}",
        ) from e
