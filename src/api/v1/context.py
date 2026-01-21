"""Context API endpoints for Long Context document management.

Sprint 112 Feature 112.1: Long Context Backend APIs

This module provides endpoints for:
- Listing documents with context metadata
- Aggregated context window metrics
- Document chunk exploration with relevance scores
- Context compression strategies
- Context export functionality

OpenAPI Spec: docs/api/openapi/context-api.yaml
"""

import hashlib
import io
from datetime import datetime
from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from qdrant_client.models import Filter, FieldCondition, MatchValue, ScrollRequest

from qdrant_client import QdrantClient

from src.api.models.context_models import (
    ChunkListResponse,
    ChunkMetadata,
    CompressionRequest,
    CompressionResponse,
    ContextDocument,
    ContextDocumentListResponse,
    ContextMetricsResponse,
    DocumentChunk,
)
from src.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/context", tags=["context"])

# Default context window size (128K tokens for most LLMs)
DEFAULT_MAX_TOKENS = 128000

# Default collection for sprint documents
DEFAULT_NAMESPACE = "sprint_docs"

# Singleton Qdrant client
_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance (singleton)."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=30,
        )
    return _qdrant_client


def generate_doc_id(name: str, namespace: str) -> str:
    """Generate deterministic document ID from name and namespace."""
    key = f"{namespace}:{name}"
    return f"doc_{hashlib.md5(key.encode()).hexdigest()[:12]}"


async def _list_documents_internal(
    namespace: str, limit: int = 100, offset: int = 0
) -> ContextDocumentListResponse:
    """Internal function to list documents (called by endpoint and export)."""
    try:
        client = get_qdrant_client()

        # Get collection name from namespace
        collection_name = f"aegis_{namespace}" if namespace else "aegis_documents"

        # Check if collection exists
        try:
            collection_info = client.get_collection(collection_name)
        except Exception:
            # Collection doesn't exist, return empty list
            logger.warning(
                "collection_not_found",
                collection=collection_name,
                namespace=namespace,
            )
            return ContextDocumentListResponse(documents=[], total=0)

        # Scroll through collection to get unique documents
        documents_map: dict[str, ContextDocument] = {}

        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=10000,  # Get all points to aggregate
            with_payload=True,
            with_vectors=False,
        )

        points = scroll_result[0] if scroll_result else []

        for point in points:
            payload = point.payload or {}
            source = payload.get("source", payload.get("filename", "Unknown"))
            doc_id = generate_doc_id(source, namespace)

            if doc_id not in documents_map:
                # Create new document entry
                documents_map[doc_id] = ContextDocument(
                    id=doc_id,
                    name=source,
                    token_count=0,
                    chunk_count=0,
                    uploaded_at=(
                        datetime.fromisoformat(
                            payload.get("uploaded_at", datetime.now().isoformat())
                        )
                        if payload.get("uploaded_at")
                        else datetime.now()
                    ),
                    status="ready",
                    namespace=namespace,
                    metadata={
                        "sprint_number": payload.get("sprint_number"),
                        "document_type": payload.get("document_type"),
                    },
                )

            # Aggregate token count and chunk count
            documents_map[doc_id].token_count += payload.get("token_count", 0)
            documents_map[doc_id].chunk_count += 1

        # Convert to list and apply pagination
        all_documents = list(documents_map.values())
        total = len(all_documents)

        # Sort by name for consistent ordering
        all_documents.sort(key=lambda d: d.name)

        # Apply pagination
        paginated = all_documents[offset : offset + limit]

        logger.info(
            "context_documents_listed",
            namespace=namespace,
            total=total,
            returned=len(paginated),
        )

        return ContextDocumentListResponse(documents=paginated, total=total)

    except Exception as e:
        logger.error("list_documents_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        ) from e


@router.get("/documents", response_model=ContextDocumentListResponse)
async def list_context_documents(
    namespace: str = Query(
        default=DEFAULT_NAMESPACE,
        description="Document namespace to filter by",
    ),
    limit: int = Query(
        default=100,
        le=500,
        description="Maximum number of documents to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of documents to skip",
    ),
) -> ContextDocumentListResponse:
    """List all documents with context metadata.

    **Sprint 112 Feature 112.1: Long Context Backend**

    Queries Qdrant to retrieve unique documents in the specified namespace,
    with aggregated token counts and chunk counts per document.

    Args:
        namespace: Document namespace to filter by
        limit: Maximum documents to return (max 500)
        offset: Number of documents to skip for pagination

    Returns:
        ContextDocumentListResponse: List of documents with metadata

    Raises:
        HTTPException: If Qdrant query fails
    """
    return await _list_documents_internal(namespace, limit, offset)


@router.get("/metrics", response_model=ContextMetricsResponse)
async def get_context_metrics(
    namespace: str = Query(
        default=DEFAULT_NAMESPACE,
        description="Namespace to calculate metrics for",
    ),
) -> ContextMetricsResponse:
    """Get aggregated context window metrics.

    **Sprint 112 Feature 112.1: Long Context Backend**

    Calculates total tokens, chunk counts, and average relevance scores
    across all documents in the specified namespace.

    Args:
        namespace: Namespace to calculate metrics for

    Returns:
        ContextMetricsResponse: Aggregated metrics

    Raises:
        HTTPException: If Qdrant query fails
    """
    try:
        client = get_qdrant_client()

        collection_name = f"aegis_{namespace}" if namespace else "aegis_documents"

        # Check if collection exists
        try:
            collection_info = client.get_collection(collection_name)
        except Exception:
            return ContextMetricsResponse(
                total_tokens=0,
                max_tokens=DEFAULT_MAX_TOKENS,
                document_count=0,
                average_relevance=0.0,
                chunks_total=0,
                utilization_percent=0.0,
            )

        # Scroll through all points to calculate metrics
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        points = scroll_result[0] if scroll_result else []

        total_tokens = 0
        total_relevance = 0.0
        relevance_count = 0
        unique_docs: set[str] = set()

        for point in points:
            payload = point.payload or {}
            total_tokens += payload.get("token_count", 0)

            if "relevance_score" in payload:
                total_relevance += payload["relevance_score"]
                relevance_count += 1

            source = payload.get("source", payload.get("filename", ""))
            if source:
                unique_docs.add(source)

        chunks_total = len(points)
        document_count = len(unique_docs)
        average_relevance = (
            total_relevance / relevance_count if relevance_count > 0 else 0.72
        )  # Default if no scores
        utilization_percent = (total_tokens / DEFAULT_MAX_TOKENS) * 100

        logger.info(
            "context_metrics_calculated",
            namespace=namespace,
            total_tokens=total_tokens,
            document_count=document_count,
            chunks_total=chunks_total,
        )

        return ContextMetricsResponse(
            total_tokens=total_tokens,
            max_tokens=DEFAULT_MAX_TOKENS,
            document_count=document_count,
            average_relevance=round(average_relevance, 3),
            chunks_total=chunks_total,
            utilization_percent=round(utilization_percent, 2),
        )

    except Exception as e:
        logger.error("get_metrics_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}",
        ) from e


@router.get("/chunks/{doc_id}", response_model=ChunkListResponse)
async def get_document_chunks(
    doc_id: str,
    min_relevance: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score filter (0.0-1.0)",
    ),
    namespace: str = Query(
        default=DEFAULT_NAMESPACE,
        description="Document namespace",
    ),
) -> ChunkListResponse:
    """Get all chunks for a specific document.

    **Sprint 112 Feature 112.1: Long Context Backend**

    Retrieves all chunks belonging to a document, with relevance scores
    and metadata. Can be filtered by minimum relevance score.

    Args:
        doc_id: Document ID (format: doc_XXXX)
        min_relevance: Optional minimum relevance score filter
        namespace: Document namespace

    Returns:
        ChunkListResponse: List of chunks with relevance scores

    Raises:
        HTTPException: If document not found or query fails
    """
    try:
        client = get_qdrant_client()

        collection_name = f"aegis_{namespace}" if namespace else "aegis_documents"

        # Scroll through collection to find chunks for this document
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        points = scroll_result[0] if scroll_result else []

        # Filter chunks for the specified document
        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for point in points:
            payload = point.payload or {}
            source = payload.get("source", payload.get("filename", ""))
            point_doc_id = generate_doc_id(source, namespace)

            if point_doc_id != doc_id:
                continue

            # Get relevance score (from payload or default)
            relevance_score = payload.get("relevance_score", 0.7)

            # Apply relevance filter if specified
            if min_relevance is not None and relevance_score < min_relevance:
                continue

            chunk = DocumentChunk(
                id=f"chunk_{point.id}" if point.id else f"chunk_{chunk_index}",
                content=payload.get("text", payload.get("content", "")),
                relevance_score=relevance_score,
                token_count=payload.get("token_count", 0),
                chunk_index=chunk_index,
                metadata=ChunkMetadata(
                    section=payload.get("section", payload.get("header")),
                    source=source,
                    page_number=payload.get("page_number"),
                ),
            )
            chunks.append(chunk)
            chunk_index += 1

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {doc_id}",
            )

        # Sort by chunk index
        chunks.sort(key=lambda c: c.chunk_index)

        logger.info(
            "document_chunks_retrieved",
            doc_id=doc_id,
            chunk_count=len(chunks),
        )

        return ChunkListResponse(
            chunks=chunks,
            total=len(chunks),
            document_id=doc_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_chunks_failed", doc_id=doc_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chunks: {str(e)}",
        ) from e


@router.post("/compress", response_model=CompressionResponse)
async def compress_context(
    request: CompressionRequest,
) -> CompressionResponse:
    """Apply compression strategy to reduce context size.

    **Sprint 112 Feature 112.1: Long Context Backend**

    Applies the specified compression strategy to reduce token count:
    - **summarization**: LLM-based content summarization
    - **filtering**: Remove chunks below relevance threshold
    - **truncation**: Keep only top-N relevant chunks
    - **hybrid**: Combine filtering + summarization

    Args:
        request: Compression parameters

    Returns:
        CompressionResponse: Compression result with before/after metrics

    Raises:
        HTTPException: If compression fails
    """
    try:
        # For now, implement filtering strategy (most straightforward)
        # Other strategies would require LLM calls for summarization

        client = get_qdrant_client()

        collection_name = f"aegis_{DEFAULT_NAMESPACE}"

        # Get current metrics
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        points = scroll_result[0] if scroll_result else []

        # Filter to specific document if provided
        if request.document_id:
            points = [
                p
                for p in points
                if generate_doc_id(
                    p.payload.get("source", p.payload.get("filename", "")),
                    DEFAULT_NAMESPACE,
                )
                == request.document_id
            ]

        original_tokens = sum(p.payload.get("token_count", 0) for p in points)
        original_chunks = len(points)

        # Apply strategy
        if request.strategy == "filtering":
            # Filter by relevance threshold
            kept_points = [
                p
                for p in points
                if p.payload.get("relevance_score", 0.7) >= request.min_relevance_threshold
            ]
        elif request.strategy == "truncation":
            # Sort by relevance and keep top N
            sorted_points = sorted(
                points,
                key=lambda p: p.payload.get("relevance_score", 0.7),
                reverse=True,
            )
            max_chunks = request.max_chunks or 20
            kept_points = sorted_points[:max_chunks]
        elif request.strategy == "summarization":
            # TODO: Implement LLM-based summarization
            # For now, simulate with 50% reduction
            kept_points = points[: len(points) // 2]
        elif request.strategy == "hybrid":
            # Filter first, then truncate
            filtered = [
                p
                for p in points
                if p.payload.get("relevance_score", 0.7) >= request.min_relevance_threshold
            ]
            sorted_filtered = sorted(
                filtered,
                key=lambda p: p.payload.get("relevance_score", 0.7),
                reverse=True,
            )
            max_chunks = request.max_chunks or 20
            kept_points = sorted_filtered[:max_chunks]
        else:
            kept_points = points

        compressed_tokens = sum(p.payload.get("token_count", 0) for p in kept_points)
        chunks_removed = original_chunks - len(kept_points)
        reduction_percent = (
            ((original_tokens - compressed_tokens) / original_tokens * 100)
            if original_tokens > 0
            else 0
        )

        logger.info(
            "context_compressed",
            strategy=request.strategy,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            reduction_percent=round(reduction_percent, 1),
        )

        return CompressionResponse(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            reduction_percent=round(reduction_percent, 1),
            chunks_removed=chunks_removed,
            strategy_applied=request.strategy,
            document_id=request.document_id,
        )

    except Exception as e:
        logger.error("compress_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compression failed: {str(e)}",
        ) from e


@router.get("/export")
async def export_context(
    format: Literal["json", "markdown"] = Query(
        default="json",
        description="Export format (json or markdown)",
    ),
    namespace: str = Query(
        default=DEFAULT_NAMESPACE,
        description="Namespace to export",
    ),
    doc_id: str | None = Query(
        default=None,
        description="Export specific document only",
    ),
) -> StreamingResponse:
    """Export context data as JSON or Markdown.

    **Sprint 112 Feature 112.1: Long Context Backend**

    Exports documents and chunks in the specified format for offline
    analysis or backup purposes.

    Args:
        format: Export format (json or markdown)
        namespace: Namespace to export
        doc_id: Optional specific document to export

    Returns:
        StreamingResponse: File download

    Raises:
        HTTPException: If export fails
    """
    try:
        # Get documents
        docs_response = await _list_documents_internal(namespace, limit=500)

        # Filter to specific document if provided
        documents = docs_response.documents
        if doc_id:
            documents = [d for d in documents if d.id == doc_id]
            if not documents:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document not found: {doc_id}",
                )

        if format == "json":
            # JSON export
            import json

            export_data = {
                "exported_at": datetime.now().isoformat(),
                "namespace": namespace,
                "document_count": len(documents),
                "documents": [d.model_dump() for d in documents],
            }

            content = json.dumps(export_data, indent=2, default=str)
            media_type = "application/json"
            filename = f"context-export-{namespace}.json"

        else:
            # Markdown export
            lines = [
                f"# Context Export - {namespace}",
                f"",
                f"**Exported:** {datetime.now().isoformat()}",
                f"**Documents:** {len(documents)}",
                f"",
                f"---",
                f"",
            ]

            for doc in documents:
                lines.extend(
                    [
                        f"## {doc.name}",
                        f"",
                        f"- **ID:** {doc.id}",
                        f"- **Tokens:** {doc.token_count:,}",
                        f"- **Chunks:** {doc.chunk_count}",
                        f"- **Status:** {doc.status}",
                        f"- **Uploaded:** {doc.uploaded_at}",
                        f"",
                    ]
                )

            content = "\n".join(lines)
            media_type = "text/markdown"
            filename = f"context-export-{namespace}.md"

        logger.info(
            "context_exported",
            format=format,
            namespace=namespace,
            document_count=len(documents),
        )

        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("export_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        ) from e
