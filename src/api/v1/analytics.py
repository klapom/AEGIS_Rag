"""Analytics API Endpoints for AegisRAG.

Sprint 62 Feature 62.9: Section Analytics Endpoint

This module provides API endpoints for analytics:
- POST /api/v1/analytics/sections - Retrieve section-level statistics

Architecture:
- Uses SectionAnalyticsService for data aggregation
- Caches results in Redis (5 min TTL)
- Returns comprehensive section statistics
- Performance target: <200ms with caching
"""

import structlog
from fastapi import APIRouter, HTTPException, status

from src.api.models.analytics import (
    SectionAnalyticsRequest,
    SectionAnalyticsResponse,
)
from src.domains.knowledge_graph.analytics import get_section_analytics_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post(
    "/sections",
    response_model=SectionAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve section-level analytics",
    description="""
    Get comprehensive statistics about document sections.

    **Returns:**
    - Total section count
    - Distribution by hierarchy level (level 1, 2, 3, etc.)
    - Average entities per section
    - Average chunks per section
    - Top 10 sections ranked by relationship count

    **Performance:**
    - Results are cached in Redis (5 min TTL)
    - Response time: <200ms with caching, <500ms without

    **Sprint 62 Feature 62.9**
    """,
    responses={
        200: {
            "description": "Successful analytics retrieval",
            "model": SectionAnalyticsResponse,
        },
        400: {"description": "Invalid request parameters"},
        404: {"description": "Document not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_section_analytics(
    request: SectionAnalyticsRequest,
) -> SectionAnalyticsResponse:
    """Get section-level analytics for a document.

    This endpoint provides comprehensive statistics about all sections
    in a document, including entity counts, chunk counts, and relationship
    metrics.

    **Example Request:**
    ```json
    {
      "document_id": "doc_123",
      "namespace": "default"
    }
    ```

    **Example Response:**
    ```json
    {
      "document_id": "doc_123",
      "total_sections": 15,
      "level_distribution": {
        "1": 3,
        "2": 8,
        "3": 4
      },
      "avg_entities_per_section": 12.5,
      "avg_chunks_per_section": 8.3,
      "top_sections": [
        {
          "section_id": "4:abc123:0",
          "section_title": "Introduction",
          "section_level": 1,
          "entity_count": 25,
          "chunk_count": 15,
          "relationship_count": 42
        },
        ...
      ]
    }
    ```

    Args:
        request: SectionAnalyticsRequest with document_id and namespace

    Returns:
        SectionAnalyticsResponse with aggregated statistics

    Raises:
        HTTPException 400: If request parameters are invalid
        HTTPException 404: If document is not found
        HTTPException 500: If analytics retrieval fails
    """
    logger.info(
        "section_analytics_endpoint_called",
        document_id=request.document_id,
        namespace=request.namespace,
    )

    try:
        # Validate document_id
        if not request.document_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="document_id cannot be empty",
            )

        # Get analytics service
        analytics_service = get_section_analytics_service()

        # Retrieve section analytics
        response = await analytics_service.get_section_analytics(
            document_id=request.document_id,
            namespace=request.namespace,
        )

        # Check if document has any sections
        if response.total_sections == 0:
            logger.warning(
                "no_sections_found",
                document_id=request.document_id,
                namespace=request.namespace,
            )
            # Return 404 if document not found (no sections)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No sections found for document: {request.document_id}",
            )

        logger.info(
            "section_analytics_retrieved",
            document_id=request.document_id,
            namespace=request.namespace,
            total_sections=response.total_sections,
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "section_analytics_failed",
            document_id=request.document_id,
            namespace=request.namespace,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve section analytics: {str(e)}",
        ) from e
