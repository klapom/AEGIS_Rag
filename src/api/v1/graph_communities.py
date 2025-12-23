"""Community Visualization API endpoints.

Sprint 63 Feature 63.5: Section-Based Community Detection with Visualization

Provides REST endpoints for:
- Section community detection with visualization data
- Community comparison across sections
- Community overlap analysis
- Visualization-ready JSON responses
"""

from typing import Any

import structlog
from fastapi import APIRouter, Body, HTTPException, Query, status

from src.domains.knowledge_graph.communities import (
    CommunityComparisonOverview,
    SectionCommunityVisualizationResponse,
    get_section_community_service,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/graph", tags=["graph-communities"])


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/communities/{document_id}/sections/{section_id}",
    response_model=SectionCommunityVisualizationResponse,
    summary="Get section communities with visualization",
    description="Retrieve all communities for a section with visualization-ready data including nodes, edges, and layout coordinates.",
    responses={
        200: {
            "description": "Communities with visualization data",
            "content": {
                "application/json": {
                    "example": {
                        "document_id": "doc_123",
                        "section_heading": "Introduction",
                        "total_communities": 2,
                        "total_entities": 15,
                        "communities": [],
                        "generation_time_ms": 250.0,
                    }
                }
            },
        },
        404: {"description": "Document or section not found"},
        500: {"description": "Server error during community detection"},
    },
)
async def get_section_communities_visualization(
    document_id: str,
    section_id: str,
    algorithm: str = Query(
        default="louvain",
        regex="^(louvain|leiden)$",
        description="Community detection algorithm",
    ),
    resolution: float = Query(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="Algorithm resolution parameter (higher = more communities)",
    ),
    include_layout: bool = Query(
        default=True,
        description="Include layout coordinates for visualization",
    ),
    layout_algorithm: str = Query(
        default="force-directed",
        regex="^(force-directed|circular|hierarchical)$",
        description="Layout algorithm for node positioning",
    ),
) -> SectionCommunityVisualizationResponse:
    """Get communities for a section with complete visualization data.

    **Sprint 63 Feature 63.5: Section-Based Community Detection with Visualization**

    This endpoint returns:
    - All communities detected in the section
    - Community membership (nodes)
    - Relationships between nodes (edges)
    - Centrality metrics for node importance
    - Layout coordinates for frontend visualization
    - Cohesion scores for community quality

    ### Query Parameters:
    - **algorithm**: Community detection algorithm (louvain or leiden)
    - **resolution**: Resolution parameter (1.0 = balanced, >1.0 = more communities)
    - **include_layout**: Whether to compute layout coordinates
    - **layout_algorithm**: Node positioning algorithm for visualization

    ### Response Structure:
    - Communities list with visualization data
    - Node data with centrality scores and positions
    - Edge data with relationship types and weights
    - Generation time for performance monitoring

    ### Example Usage:
    ```
    GET /api/v1/graph/communities/doc_123/sections/Introduction
        ?algorithm=louvain&resolution=1.0&layout_algorithm=force-directed

    Response:
    {
        "document_id": "doc_123",
        "section_heading": "Introduction",
        "total_communities": 2,
        "total_entities": 15,
        "communities": [
            {
                "community_id": "community_0",
                "section_heading": "Introduction",
                "size": 8,
                "cohesion_score": 0.75,
                "nodes": [
                    {
                        "entity_id": "ent_1",
                        "entity_name": "Alice",
                        "entity_type": "PERSON",
                        "centrality": 0.85,
                        "degree": 5,
                        "x": 100.0,
                        "y": 200.0
                    }
                ],
                "edges": [
                    {
                        "source": "ent_1",
                        "target": "ent_2",
                        "relationship_type": "WORKS_WITH",
                        "weight": 1.0
                    }
                ],
                "layout_type": "force-directed",
                "algorithm": "louvain"
            }
        ],
        "generation_time_ms": 350.0
    }
    ```

    Args:
        document_id: Document ID
        section_id: Section heading to analyze
        algorithm: Community detection algorithm
        resolution: Resolution parameter
        include_layout: Generate layout coordinates
        layout_algorithm: Layout algorithm

    Returns:
        SectionCommunityVisualizationResponse with visualization data

    Raises:
        HTTPException: If document/section not found or detection fails
    """
    try:
        logger.info(
            "section_communities_visualization_requested",
            document_id=document_id,
            section_id=section_id,
            algorithm=algorithm,
            resolution=resolution,
        )

        # Get service instance
        service = get_section_community_service()

        # Generate visualization
        response = await service.get_section_communities_with_visualization(
            section_heading=section_id,
            document_id=document_id,
            algorithm=algorithm,
            resolution=resolution,
            include_layout=include_layout,
            layout_algorithm=layout_algorithm,
        )

        logger.info(
            "section_communities_visualization_returned",
            document_id=document_id,
            section_id=section_id,
            community_count=response.total_communities,
            generation_time_ms=response.generation_time_ms,
        )

        return response

    except ValueError as e:
        logger.warning(
            "section_not_found",
            document_id=document_id,
            section_id=section_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found in document '{document_id}'",
        ) from e

    except Exception as e:
        logger.error(
            "section_communities_visualization_error",
            document_id=document_id,
            section_id=section_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate section community visualizations",
        ) from e


@router.post(
    "/communities/compare",
    response_model=CommunityComparisonOverview,
    summary="Compare communities across sections",
    description="Analyze community overlap and sharing across multiple sections.",
    responses={
        200: {"description": "Community comparison results"},
        400: {"description": "Invalid request parameters"},
        404: {"description": "Document not found"},
        500: {"description": "Server error during comparison"},
    },
)
async def compare_section_communities(
    request: dict[str, Any] = Body(
        ...,
        example={
            "document_id": "doc_123",
            "sections": ["Introduction", "Methods", "Results"],
            "algorithm": "louvain",
            "resolution": 1.0,
        },
    ),
) -> CommunityComparisonOverview:
    """Compare communities across multiple sections.

    **Sprint 63 Feature 63.5: Community Comparison**

    Analyzes how communities differ and overlap across sections:
    - Identifies section-specific communities
    - Finds shared entities across sections
    - Builds overlap matrix showing cross-section entity sharing
    - Calculates community similarity metrics

    ### Request Body:
    ```json
    {
        "document_id": "doc_123",
        "sections": ["Introduction", "Methods", "Results"],
        "algorithm": "louvain",
        "resolution": 1.0
    }
    ```

    ### Response:
    - Section-specific communities
    - Shared communities spanning multiple sections
    - Overlap matrix (entity count between sections)
    - Shared entity lists

    ### Example Usage:
    ```
    POST /api/v1/graph/communities/compare

    Request:
    {
        "document_id": "doc_123",
        "sections": ["Introduction", "Methods"],
        "algorithm": "louvain"
    }

    Response:
    {
        "section_count": 2,
        "sections": ["Introduction", "Methods"],
        "total_shared_communities": 1,
        "shared_entities": {
            "Introduction-Methods": ["ent_1", "ent_2", "ent_3"]
        },
        "overlap_matrix": {
            "Introduction": {"Methods": 3},
            "Methods": {"Introduction": 3}
        },
        "comparison_time_ms": 450.0
    }
    ```

    Args:
        request: Comparison request with document_id, sections list, algorithm, resolution

    Returns:
        CommunityComparisonOverview with overlap analysis

    Raises:
        HTTPException: If document not found or comparison fails
    """
    try:
        document_id = request.get("document_id")
        sections = request.get("sections", [])
        algorithm = request.get("algorithm", "louvain")
        resolution = request.get("resolution", 1.0)

        if not document_id:
            raise ValueError("document_id is required")

        if not sections or len(sections) < 2:
            raise ValueError("At least 2 sections are required for comparison")

        logger.info(
            "section_communities_comparison_requested",
            document_id=document_id,
            section_count=len(sections),
            algorithm=algorithm,
        )

        # Get service instance
        service = get_section_community_service()

        # Perform comparison
        response = await service.compare_section_communities(
            section_headings=sections,
            document_id=document_id,
            algorithm=algorithm,
            resolution=resolution,
        )

        logger.info(
            "section_communities_comparison_returned",
            document_id=document_id,
            section_count=len(sections),
            shared_communities=response.total_shared_communities,
            comparison_time_ms=response.comparison_time_ms,
        )

        return response

    except ValueError as e:
        logger.warning(
            "invalid_comparison_request",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.error(
            "section_communities_comparison_error",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare section communities",
        ) from e
