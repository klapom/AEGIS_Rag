"""Annotation API Endpoints - Sprint 21 Feature 21.6.

FastAPI endpoints for retrieving image annotations with BBox coordinates
for PDF rendering (on-demand, not in search results).
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from src.api.auth.jwt import get_current_user
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/annotations", tags=["annotations"])

settings = get_settings()


# Response Models
class BBoxAbsolute(BaseModel):
    """Absolute BBox coordinates in points."""

    left: float = Field(..., description="Left coordinate (pt)")
    top: float = Field(..., description="Top coordinate (pt)")
    right: float = Field(..., description="Right coordinate (pt)")
    bottom: float = Field(..., description="Bottom coordinate (pt)")


class PageContext(BaseModel):
    """Page context for BBox."""

    page_no: int = Field(..., description="Page number (1-indexed)")
    page_width: float = Field(..., description="Page width (pt)")
    page_height: float = Field(..., description="Page height (pt)")
    unit: str = Field(default="pt", description="Coordinate unit")
    dpi: int = Field(default=72, description="DPI")
    coord_origin: str = Field(..., description="Coordinate origin (e.g., 'TOPLEFT')")


class BBoxNormalized(BaseModel):
    """Normalized BBox coordinates (0.0-1.0)."""

    left: float = Field(..., ge=0.0, le=1.0, description="Left (normalized)")
    top: float = Field(..., ge=0.0, le=1.0, description="Top (normalized)")
    right: float = Field(..., ge=0.0, le=1.0, description="Right (normalized)")
    bottom: float = Field(..., ge=0.0, le=1.0, description="Bottom (normalized)")


class ImageAnnotation(BaseModel):
    """Single image annotation with VLM description + BBox."""

    description: str = Field(..., description="VLM-generated image description")
    vlm_model: str = Field(..., description="VLM model used (e.g., qwen3-vl:4b-instruct)")
    bbox_absolute: BBoxAbsolute | None = Field(None, description="Absolute BBox in points")
    page_context: PageContext | None = Field(None, description="Page context for BBox")
    bbox_normalized: BBoxNormalized | None = Field(
        None, description="Normalized BBox (0.0-1.0)"
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class PageDimensions(BaseModel):
    """Page dimensions metadata."""

    width: float = Field(..., description="Page width (pt)")
    height: float = Field(..., description="Page height (pt)")
    unit: str = Field(default="pt", description="Unit")
    dpi: int = Field(default=72, description="DPI")


class PageAnnotations(BaseModel):
    """Annotations for a single page."""

    page_dimensions: PageDimensions
    annotations: list[ImageAnnotation] = Field(
        default_factory=list, description="Image annotations on this page"
    )


class DocumentAnnotationsResponse(BaseModel):
    """Response model for document annotations."""

    document_id: str = Field(..., description="Document identifier")
    annotations_by_page: dict[str, PageAnnotations] = Field(
        ...,
        description="Annotations grouped by page number (e.g., '1', '2', '3')",
    )
    total_annotations: int = Field(..., description="Total number of annotations")

    model_config = ConfigDict(str_strip_whitespace=True)


# API Endpoints
@router.get(
    "/document/{document_id}",
    response_model=DocumentAnnotationsResponse,
    summary="Get document annotations (on-demand)",
    description="""
    Retrieve image annotations with BBox coordinates for PDF rendering.

    **Feature 21.6**: On-demand annotation retrieval (not included in search results).

    **Use Case**: Frontend PDF viewer requests annotations for specific pages when rendering.

    **Performance**: < 50ms latency (Qdrant query only, no VLM processing).
    """,
)
async def get_document_annotations(
    document_id: str,
    chunk_ids: list[str] | None = Query(
        None, description="Filter by specific chunk IDs (from search results)"
    ),
    page_no: int | None = Query(None, ge=1, description="Filter by page number"),
    _current_user: dict = Depends(get_current_user),  # JWT authentication
) -> DocumentAnnotationsResponse:
    """Get image annotations for a document (on-demand).

    Args:
        document_id: Document identifier
        chunk_ids: Optional list of chunk IDs to filter (from search results)
        page_no: Optional page number to filter
        _current_user: Authenticated user (JWT)

    Returns:
        DocumentAnnotationsResponse with annotations grouped by page

    Raises:
        HTTPException: If document not found or Qdrant query fails
    """
    logger.info(
        "get_document_annotations",
        document_id=document_id,
        chunk_ids=chunk_ids,
        page_no=page_no,
    )

    try:
        # Initialize Qdrant client
        qdrant = QdrantClientWrapper()
        collection_name = settings.qdrant_collection

        # Build Qdrant filter
        filter_conditions: list[dict[str, Any]] = [{"key": "document_id", "match": {"value": document_id}}]

        if chunk_ids:
            # Filter by specific chunk IDs
            filter_conditions.append({"key": "chunk_id", "match": {"any": chunk_ids}})

        if page_no is not None:
            # Filter by page number
            filter_conditions.append({"key": "page_no", "match": {"value": page_no}})

        # Add filter for chunks with images
        filter_conditions.append({"key": "contains_images", "match": {"value": True}})

        # Query Qdrant for chunks with image annotations
        # Note: We use scroll instead of search since we don't need vector similarity
        from qdrant_client.models import FieldCondition, Filter

        qdrant_filter = Filter(
            must=[
                FieldCondition(
                    key=cond["key"],
                    match=cond.get("match"),
                )
                for cond in filter_conditions
            ]
        )

        # Scroll through points (no vector search needed)
        points, _ = await qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=qdrant_filter,
            limit=100,  # Max 100 chunks per document
            with_payload=True,
            with_vectors=False,  # Don't need vectors
        )

        # Group annotations by page
        annotations_by_page: dict[str, PageAnnotations] = {}

        for point in points:
            payload = point.payload
            page_number = payload.get("page_no")

            if page_number is None:
                continue

            page_key = str(page_number)

            # Initialize page if not exists
            if page_key not in annotations_by_page:
                page_dims_data = payload.get("page_dimensions")
                if page_dims_data:
                    page_dims = PageDimensions(**page_dims_data)
                else:
                    # Fallback dimensions if not available
                    page_dims = PageDimensions(width=595, height=842, unit="pt", dpi=72)

                annotations_by_page[page_key] = PageAnnotations(
                    page_dimensions=page_dims,
                    annotations=[],
                )

            # Extract image annotations
            image_annotations_data = payload.get("image_annotations", [])

            for img_data in image_annotations_data:
                # Parse BBox data
                bbox_abs = None
                if img_data.get("bbox_absolute"):
                    bbox_abs = BBoxAbsolute(**img_data["bbox_absolute"])

                page_ctx = None
                if img_data.get("page_context"):
                    page_ctx = PageContext(**img_data["page_context"])

                bbox_norm = None
                if img_data.get("bbox_normalized"):
                    bbox_norm = BBoxNormalized(**img_data["bbox_normalized"])

                annotation = ImageAnnotation(
                    description=img_data.get("description", ""),
                    vlm_model=img_data.get("vlm_model", "unknown"),
                    bbox_absolute=bbox_abs,
                    page_context=page_ctx,
                    bbox_normalized=bbox_norm,
                )

                annotations_by_page[page_key].annotations.append(annotation)

        # Calculate total annotations
        total_annotations = sum(len(page.annotations) for page in annotations_by_page.values())

        logger.info(
            "get_document_annotations_success",
            document_id=document_id,
            total_pages=len(annotations_by_page),
            total_annotations=total_annotations,
        )

        return DocumentAnnotationsResponse(
            document_id=document_id,
            annotations_by_page=annotations_by_page,
            total_annotations=total_annotations,
        )

    except Exception as e:
        logger.error(
            "get_document_annotations_error",
            document_id=document_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve annotations: {str(e)}",
        ) from e


@router.get(
    "/chunk/{chunk_id}",
    response_model=list[ImageAnnotation],
    summary="Get annotations for specific chunk",
    description="""
    Retrieve image annotations for a specific chunk.

    **Use Case**: Frontend needs annotations for a single search result chunk.
    """,
)
async def get_chunk_annotations(
    chunk_id: str,
    _current_user: dict = Depends(get_current_user),
) -> list[ImageAnnotation]:
    """Get image annotations for a specific chunk.

    Args:
        chunk_id: Chunk identifier (Qdrant point ID)
        _current_user: Authenticated user (JWT)

    Returns:
        List of ImageAnnotation objects

    Raises:
        HTTPException: If chunk not found or Qdrant query fails
    """
    logger.info("get_chunk_annotations", chunk_id=chunk_id)

    try:
        # Initialize Qdrant client
        qdrant = QdrantClientWrapper()
        collection_name = settings.qdrant_collection

        # Retrieve specific point
        point = await qdrant.retrieve(
            collection_name=collection_name,
            ids=[chunk_id],
            with_payload=True,
            with_vectors=False,
        )

        if not point or len(point) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk not found: {chunk_id}",
            )

        payload = point[0].payload
        image_annotations_data = payload.get("image_annotations", [])

        annotations = []
        for img_data in image_annotations_data:
            bbox_abs = BBoxAbsolute(**img_data["bbox_absolute"]) if img_data.get("bbox_absolute") else None
            page_ctx = PageContext(**img_data["page_context"]) if img_data.get("page_context") else None
            bbox_norm = BBoxNormalized(**img_data["bbox_normalized"]) if img_data.get("bbox_normalized") else None

            annotation = ImageAnnotation(
                description=img_data.get("description", ""),
                vlm_model=img_data.get("vlm_model", "unknown"),
                bbox_absolute=bbox_abs,
                page_context=page_ctx,
                bbox_normalized=bbox_norm,
            )
            annotations.append(annotation)

        logger.info(
            "get_chunk_annotations_success",
            chunk_id=chunk_id,
            annotations_count=len(annotations),
        )

        return annotations

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_chunk_annotations_error", chunk_id=chunk_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chunk annotations: {str(e)}",
        ) from e
