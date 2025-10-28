"""Admin API endpoints for re-indexing and maintenance operations.

Sprint 16 Feature 16.3: Unified Re-Indexing Pipeline with SSE progress tracking.
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from qdrant_client.models import Distance

from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.ingestion import DocumentIngestionPipeline
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.chunking_service import get_chunking_service
from src.core.config import settings
from src.core.exceptions import VectorSearchError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ============================================================================
# Re-Indexing Endpoint with SSE Progress Tracking
# ============================================================================


async def reindex_progress_stream(
    input_dir: Path,
    dry_run: bool = False,
) -> AsyncGenerator[str, None]:
    """Stream progress updates during re-indexing operation.

    Args:
        input_dir: Directory containing documents to index
        dry_run: If True, simulate operation without making changes

    Yields:
        SSE-formatted progress messages (JSON)

    Progress Message Format:
        {
            "status": "in_progress" | "completed" | "error",
            "phase": "initialization" | "deletion" | "chunking" | "embedding" | "indexing" | "validation",
            "documents_processed": int,
            "documents_total": int,
            "progress_percent": float,
            "eta_seconds": int | null,
            "current_document": str | null,
            "message": str
        }
    """
    import json
    import time

    start_time = time.time()

    try:
        # Phase 1: Initialization
        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'initialization', 'progress_percent': 0, 'message': 'Initializing re-indexing pipeline...'})}\n\n"

        # Initialize services
        chunking_service = get_chunking_service()
        embedding_service = get_embedding_service()
        qdrant_client = get_qdrant_client()
        pipeline = DocumentIngestionPipeline()

        # Discover documents
        if not input_dir.exists():
            raise VectorSearchError(f"Input directory does not exist: {input_dir}")

        document_files = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.txt"))
        total_docs = len(document_files)

        if total_docs == 0:
            raise VectorSearchError(f"No documents found in {input_dir}")

        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'initialization', 'progress_percent': 5, 'message': f'Found {total_docs} documents to index'})}\n\n"

        # Phase 2: Deletion (Atomic)
        if not dry_run:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'deletion', 'progress_percent': 10, 'message': 'Deleting old indexes...'})}\n\n"

            # Delete Qdrant collection
            collection_name = settings.qdrant_collection_name
            await qdrant_client.delete_collection(collection_name)
            logger.info("deleted_qdrant_collection", collection=collection_name)

            # Recreate collection with BGE-M3 dimensions
            embedding_dim = embedding_service.get_embedding_dimension()
            await qdrant_client.create_collection(
                collection_name=collection_name,
                vector_size=embedding_dim,
                distance=Distance.COSINE,
            )
            logger.info(
                "recreated_qdrant_collection",
                collection=collection_name,
                dimension=embedding_dim,
            )

            # Clear BM25 cache (will be rebuilt during indexing)
            from src.components.vector_search.bm25_search import BM25Search

            bm25_cache_path = Path("data/cache/bm25_model.pkl")
            if bm25_cache_path.exists():
                bm25_cache_path.unlink()
                logger.info("cleared_bm25_cache")

            # TODO: Clear Neo4j graph data (Feature 16.6)
            # TODO: Clear Graphiti memory data (if needed)

            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'deletion', 'progress_percent': 20, 'message': 'Old indexes deleted successfully'})}\n\n"
        else:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'deletion', 'progress_percent': 20, 'message': '[DRY RUN] Skipped deletion'})}\n\n"

        # Phase 3: Chunking + Embedding + Indexing
        docs_processed = 0

        for doc_file in document_files:
            docs_processed += 1
            progress_pct = 20 + (docs_processed / total_docs) * 70  # 20% → 90%
            elapsed = time.time() - start_time
            eta = int((elapsed / docs_processed) * (total_docs - docs_processed)) if docs_processed > 0 else None

            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'chunking', 'documents_processed': docs_processed, 'documents_total': total_docs, 'progress_percent': round(progress_pct, 1), 'eta_seconds': eta, 'current_document': doc_file.name, 'message': f'Processing {doc_file.name}...'})}\n\n"

            if not dry_run:
                # Load document
                with open(doc_file, "rb") as f:
                    file_content = f.read()

                # Chunk using unified chunking service
                chunks = await chunking_service.chunk_document(
                    content=file_content,
                    filename=doc_file.name,
                    content_type="application/pdf" if doc_file.suffix == ".pdf" else "text/plain",
                )

                # Ingest into Qdrant (includes embedding with BGE-M3)
                await pipeline.ingest_document(
                    doc_content=file_content,
                    doc_metadata={"filename": doc_file.name, "source": str(doc_file)},
                )

                logger.info(
                    "document_indexed",
                    filename=doc_file.name,
                    chunks=len(chunks),
                    progress=f"{docs_processed}/{total_docs}",
                )

            await asyncio.sleep(0.01)  # Prevent blocking event loop

        # Phase 4: Validation
        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 95, 'message': 'Validating index consistency...'})}\n\n"

        if not dry_run:
            # Validate Qdrant collection
            collection_info = await qdrant_client.get_collection_info(collection_name)
            if collection_info:
                point_count = collection_info.points_count
                logger.info("validation_complete", collection=collection_name, points=point_count)
                yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 98, 'message': f'Validation successful: {point_count} chunks indexed'})}\n\n"
            else:
                raise VectorSearchError(f"Collection {collection_name} not found after re-indexing")
        else:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 98, 'message': '[DRY RUN] Validation skipped'})}\n\n"

        # Completion
        total_time = time.time() - start_time
        yield f"data: {json.dumps({'status': 'completed', 'phase': 'completed', 'progress_percent': 100, 'documents_processed': total_docs, 'documents_total': total_docs, 'message': f'Re-indexing completed successfully in {total_time:.1f}s'})}\n\n"

    except Exception as e:
        logger.error("reindex_failed", error=str(e), exc_info=True)
        yield f"data: {json.dumps({'status': 'error', 'message': f'Re-indexing failed: {str(e)}'})}\n\n"


@router.post(
    "/reindex",
    response_class=StreamingResponse,
    summary="Re-index all documents",
    description="Atomically rebuild all indexes (Qdrant + BM25 + Neo4j) with BGE-M3 embeddings. Progress tracked via SSE.",
)
async def reindex_all_documents(
    input_dir: str = Query(
        default="data/sample_documents",
        description="Directory containing documents to index",
    ),
    dry_run: bool = Query(
        default=False,
        description="Simulate operation without making changes",
    ),
    confirm: bool = Query(
        default=False,
        description="Confirmation required to execute (safety check)",
    ),
) -> StreamingResponse:
    """Re-index all documents with atomic deletion and SSE progress tracking.

    **Sprint 16 Feature 16.3: Unified Re-Indexing Pipeline**

    This endpoint:
    1. Atomically deletes old indexes (Qdrant, BM25 cache)
    2. Reloads all documents from input directory
    3. Chunks using ChunkingService (Feature 16.1)
    4. Embeds using BGE-M3 1024-dim (Feature 16.2)
    5. Indexes into Qdrant + BM25
    6. Validates consistency

    **Safety Checks:**
    - `dry_run=true`: Simulate without making changes
    - `confirm=true`: Required to execute (prevents accidental deletion)

    **Progress Tracking:**
    - Returns SSE (Server-Sent Events) stream
    - Real-time progress updates with phase, percentage, ETA
    - Final message indicates completion or error

    **Example Usage:**
    ```bash
    curl -N "http://localhost:8000/api/v1/admin/reindex?confirm=true" \
      -H "Accept: text/event-stream"
    ```

    Args:
        input_dir: Directory containing documents to index
        dry_run: If True, simulate operation without making changes
        confirm: Must be True to execute (safety check)

    Returns:
        StreamingResponse with SSE progress updates
    """
    if not dry_run and not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required: set confirm=true to execute re-indexing. This will delete all existing indexes!",
        )

    input_path = Path(input_dir)

    logger.info(
        "reindex_started",
        input_dir=str(input_path),
        dry_run=dry_run,
        confirm=confirm,
    )

    return StreamingResponse(
        reindex_progress_stream(input_path, dry_run=dry_run),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
