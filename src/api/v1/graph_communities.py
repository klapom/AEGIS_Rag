"""Community Visualization API endpoints.

Sprint 63 Feature 63.5: Section-Based Community Detection with Visualization
Sprint 71 Feature 71.17: Document and Section Selection API

Provides REST endpoints for:
- Section community detection with visualization data
- Community comparison across sections
- Community overlap analysis
- Visualization-ready JSON responses
- Document listing for selection
- Section listing per document
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.components.vector_search.qdrant_client import QdrantClient
from src.core.config import settings
from src.domains.knowledge_graph.communities import (
    CommunityComparisonOverview,
    SectionCommunityVisualizationResponse,
    get_section_community_service,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/graph", tags=["graph-communities"])


# =============================================================================
# Sprint 71 Feature 71.17: Pydantic Models for Document/Section Selection
# =============================================================================


class DocumentMetadata(BaseModel):
    """Document metadata for selection dropdown."""

    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class DocumentsResponse(BaseModel):
    """Response for GET /graph/documents."""

    documents: list[DocumentMetadata] = Field(..., description="List of all documents")


class DocumentSection(BaseModel):
    """Section metadata for selection dropdown."""

    id: str = Field(..., description="Section ID")
    heading: str = Field(..., description="Section heading")
    level: int = Field(..., description="Section level (1=top-level)")
    entity_count: int = Field(default=0, description="Number of entities in section")
    chunk_count: int = Field(default=0, description="Number of chunks in section")


class SectionsResponse(BaseModel):
    """Response for GET /graph/documents/{doc_id}/sections."""

    document_id: str = Field(..., description="Document ID")
    sections: list[DocumentSection] = Field(..., description="List of sections in document")


# =============================================================================
# Sprint 71 Feature 71.17: Document & Section Selection Endpoints
# =============================================================================


@router.get(
    "/documents",
    response_model=DocumentsResponse,
    summary="Get all documents",
    description="Retrieve all documents for selection dropdown in community analysis dialogs.",
    responses={
        200: {
            "description": "List of all documents",
            "content": {
                "application/json": {
                    "example": {
                        "documents": [
                            {
                                "id": "doc_123",
                                "title": "Machine Learning Basics",
                                "created_at": "2026-01-01T12:00:00Z",
                                "updated_at": "2026-01-02T15:30:00Z",
                            }
                        ]
                    }
                }
            },
        },
        500: {"description": "Server error"},
    },
)
async def get_documents() -> DocumentsResponse:
    """Get all documents for selection dropdown.

    **Sprint 71 Feature 71.17: Document Selection API**

    This endpoint returns all documents stored in Qdrant with their original filenames
    extracted from the document_path payload field.

    ### Response Structure:
    - List of documents with id, title (filename), created_at, updated_at
    - Sorted by creation date (newest first)

    ### Example Usage:
    ```
    GET /api/v1/graph/documents

    Response:
    {
        "documents": [
            {
                "id": "doc_123",
                "title": "Machine_Learning_Basics.pdf",
                "created_at": "2026-01-01T12:00:00Z",
                "updated_at": "2026-01-02T15:30:00Z"
            },
            {
                "id": "doc_456",
                "title": "Deep_Learning_Advanced.pdf",
                "created_at": "2025-12-15T10:00:00Z",
                "updated_at": "2025-12-20T14:00:00Z"
            }
        ]
    }
    ```

    Returns:
        DocumentsResponse with list of all documents

    Raises:
        HTTPException: If database query fails
    """
    try:
        logger.info("documents_list_requested")

        # Get Qdrant client
        qdrant_client = QdrantClient()

        # Collection name from settings (default: documents_v1)
        collection_name = settings.qdrant_collection

        # Scroll through all points to get unique documents
        # We need to scroll because there's no direct "get unique documents" query
        unique_docs: dict[str, dict[str, Any]] = {}
        offset = None
        batch_size = 100

        logger.info("scrolling_qdrant_for_documents", collection=collection_name)

        while True:
            # Scroll through points
            scroll_result = await qdrant_client.async_client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,  # We don't need vectors, just metadata
            )

            points, next_offset = scroll_result

            # Extract unique documents from payloads
            for point in points:
                payload = point.payload
                if not payload:
                    continue

                doc_id = payload.get("document_id")
                doc_path = payload.get("document_path")
                ingestion_ts = payload.get("ingestion_timestamp")

                if not doc_id or not doc_path:
                    continue

                # Extract filename from full path
                filename = Path(doc_path).name

                # Track earliest ingestion time for each document
                if doc_id not in unique_docs:
                    unique_docs[doc_id] = {
                        "id": doc_id,
                        "filename": filename,
                        "path": doc_path,
                        "ingestion_timestamp": ingestion_ts or 0,
                    }
                else:
                    # Update if we found an earlier chunk
                    if ingestion_ts and ingestion_ts < unique_docs[doc_id]["ingestion_timestamp"]:
                        unique_docs[doc_id]["ingestion_timestamp"] = ingestion_ts

            # Check if there are more points
            if next_offset is None:
                break

            offset = next_offset

        logger.info("unique_documents_extracted", count=len(unique_docs))

        # Convert to Pydantic models
        documents = []
        for doc_data in unique_docs.values():
            # Convert Unix timestamp to datetime
            created_at = datetime.fromtimestamp(doc_data["ingestion_timestamp"])

            documents.append(
                DocumentMetadata(
                    id=doc_data["id"],
                    title=doc_data["filename"],  # Original filename from document_path
                    created_at=created_at,
                    updated_at=created_at,  # Use same timestamp for both
                )
            )

        # Sort by creation date (newest first)
        documents.sort(key=lambda d: d.created_at, reverse=True)

        # Limit to 100 most recent documents
        documents = documents[:100]

        logger.info("documents_list_returned", count=len(documents))

        return DocumentsResponse(documents=documents)

    except Exception as e:
        logger.error("documents_list_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents",
        ) from e


@router.get(
    "/documents/{doc_id}/sections",
    response_model=SectionsResponse,
    summary="Get sections for a document",
    description="Retrieve all sections for a specific document for cascading selection.",
    responses={
        200: {
            "description": "List of sections in document",
            "content": {
                "application/json": {
                    "example": {
                        "document_id": "doc_123",
                        "sections": [
                            {
                                "id": "sec_1",
                                "heading": "Introduction",
                                "level": 1,
                                "entity_count": 15,
                                "chunk_count": 8,
                            }
                        ],
                    }
                }
            },
        },
        404: {"description": "Document not found"},
        500: {"description": "Server error"},
    },
)
async def get_document_sections(doc_id: str) -> SectionsResponse:
    """Get all sections for a specific document.

    **Sprint 71 Feature 71.17: Section Selection API**

    This endpoint returns all sections for a document to enable cascading
    selection in the frontend (select document → sections load automatically).

    ### Response Structure:
    - Document ID
    - List of sections with heading, level, entity/chunk counts
    - Sorted by level (top-level first), then by heading

    ### Example Usage:
    ```
    GET /api/v1/graph/documents/doc_123/sections

    Response:
    {
        "document_id": "doc_123",
        "sections": [
            {
                "id": "sec_1",
                "heading": "Introduction",
                "level": 1,
                "entity_count": 15,
                "chunk_count": 8
            },
            {
                "id": "sec_2",
                "heading": "Methods",
                "level": 1,
                "entity_count": 23,
                "chunk_count": 12
            }
        ]
    }
    ```

    Args:
        doc_id: Document ID to get sections for

    Returns:
        SectionsResponse with list of sections

    Raises:
        HTTPException: If document not found or query fails
    """
    try:
        logger.info("document_sections_requested", document_id=doc_id)

        # Get Neo4j client
        neo4j_client = get_neo4j_client()

        # First check if document exists (check for chunks with this document_id)
        doc_check_query = """
        MATCH (c:chunk {document_id: $doc_id})
        RETURN c.document_id AS id
        LIMIT 1
        """
        doc_results = await neo4j_client.execute_query(
            doc_check_query, parameters={"doc_id": doc_id}
        )

        if not doc_results:
            logger.warning("document_not_found", document_id=doc_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{doc_id}' not found",
            )

        # Query sections from chunks
        # Note: Current ingestion pipeline doesn't create Section nodes
        # This returns a single "Complete Document" section as fallback
        query = """
        MATCH (c:chunk {document_id: $doc_id})
        WITH count(c) AS total_chunks
        OPTIONAL MATCH (e:base)
        WHERE EXISTS {
            MATCH (e)<-[:MENTIONS]-(c2:chunk {document_id: $doc_id})
        }
        WITH total_chunks, count(DISTINCT e) AS entity_count
        RETURN
            'complete' AS id,
            'Complete Document' AS heading,
            1 AS level,
            entity_count,
            total_chunks AS chunk_count
        """

        results = await neo4j_client.execute_query(query, parameters={"doc_id": doc_id})

        # Convert to Pydantic models
        sections = []
        for record in results:
            sections.append(
                DocumentSection(
                    id=record["id"],
                    heading=record["heading"],
                    level=record["level"],
                    entity_count=record["entity_count"],
                    chunk_count=record["chunk_count"],
                )
            )

        logger.info(
            "document_sections_returned",
            document_id=doc_id,
            section_count=len(sections),
        )

        return SectionsResponse(document_id=doc_id, sections=sections)

    except HTTPException:
        # Re-raise HTTPException (404)
        raise

    except Exception as e:
        logger.error(
            "document_sections_error",
            document_id=doc_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document sections",
        ) from e


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
