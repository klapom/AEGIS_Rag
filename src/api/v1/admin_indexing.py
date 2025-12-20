"""Admin Indexing API endpoints.

Sprint 53 Feature 53.3: Extracted from admin.py

This module provides endpoints for:
- Document re-indexing (full and VLM-enhanced)
- Document addition (incremental indexing)
- File upload for indexing
- Parallel batch indexing
- Directory scanning
- Ingestion job tracking
- Pipeline configuration
- Index consistency validation
"""

import asyncio
import contextlib
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Literal

import structlog
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client.models import Distance

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings
from src.core.exceptions import VectorSearchError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-indexing"])

# ============================================================================
# Sprint 33: Last Re-Index Timestamp (Redis-based persistence)
# ============================================================================

REDIS_KEY_LAST_REINDEX = "admin:last_reindex_timestamp"


async def save_last_reindex_timestamp() -> None:
    """Save the current timestamp as last re-index time to Redis.

    Sprint 33: Persistent storage for last re-index timestamp.
    Uses Redis key 'admin:last_reindex_timestamp'.
    """
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        redis_client = await redis_memory.client

        timestamp = datetime.now().isoformat()
        await redis_client.set(REDIS_KEY_LAST_REINDEX, timestamp)

        logger.info("last_reindex_timestamp_saved", timestamp=timestamp)
    except Exception as e:
        logger.warning("failed_to_save_reindex_timestamp", error=str(e))


async def get_last_reindex_timestamp() -> str | None:
    """Get the last re-index timestamp from Redis.

    Sprint 33: Fetch persistent last re-index timestamp.

    Returns:
        ISO 8601 formatted timestamp or None if not set.
    """
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        redis_client = await redis_memory.client

        timestamp = await redis_client.get(REDIS_KEY_LAST_REINDEX)

        if timestamp:
            # Redis returns bytes, decode to string
            return timestamp.decode("utf-8") if isinstance(timestamp, bytes) else timestamp

        return None
    except Exception as e:
        logger.warning("failed_to_get_reindex_timestamp", error=str(e))
        return None


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

    # Sprint 51: Helper for consistent timestamps
    def _ts() -> str:
        return time.strftime("%H:%M:%S", time.localtime())

    try:
        # Phase 1: Initialization
        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'initialization', 'progress_percent': 0, 'message': f'[{_ts()}] Initializing re-indexing pipeline...'})}\n\n"

        # Initialize services
        embedding_service = get_embedding_service()
        qdrant_client = get_qdrant_client()

        # Discover documents (all 30 supported formats from FormatRouter)
        if not input_dir.exists():
            raise VectorSearchError(query="", reason=f"Input directory does not exist: {input_dir}")

        # Import all supported formats from FormatRouter (Sprint 22.3)
        from src.components.ingestion.format_router import ALL_FORMATS

        # Glob all supported document formats (30 total: .pdf, .docx, .pptx, .xlsx, .md, etc.)
        document_files = []
        for ext in ALL_FORMATS:
            # Remove leading dot from extension for glob pattern
            pattern = f"*{ext}"
            document_files.extend(input_dir.glob(pattern))

        total_docs = len(document_files)

        if total_docs == 0:
            raise VectorSearchError(query="", reason=f"No documents found in {input_dir}")

        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'initialization', 'progress_percent': 5, 'message': f'Found {total_docs} documents to index'})}\n\n"

        # Phase 2: Deletion (Atomic)
        if not dry_run:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'deletion', 'progress_percent': 10, 'message': 'Deleting old indexes...'})}\n\n"

            # Delete Qdrant collection
            collection_name = settings.qdrant_collection
            await qdrant_client.delete_collection(collection_name)
            logger.info("deleted_qdrant_collection", collection=collection_name)

            # Recreate collection with BGE-M3 dimensions
            embedding_dim = embedding_service.embedding_dim
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
            # Note: BM25Search uses "bm25_index.pkl" (not "bm25_model.pkl")
            bm25_cache_path = Path("data/cache/bm25_index.pkl")
            if bm25_cache_path.exists():
                bm25_cache_path.unlink()
                logger.info("cleared_bm25_cache")

            # Clear Neo4j graph data (Sprint 16 Feature 16.7: Simultaneous Qdrant + Neo4j indexing)
            try:
                lightrag_wrapper = await get_lightrag_wrapper_async()
                await lightrag_wrapper._clear_neo4j_database()
                logger.info("cleared_neo4j_database")
                yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'deletion', 'progress_percent': 15, 'message': 'Clearing Neo4j graph database...'})}\n\n"
            except Exception as e:
                logger.warning("neo4j_clear_failed", error=str(e))
                # Continue even if Neo4j clearing fails (might not be available)

            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'deletion', 'progress_percent': 20, 'message': 'Old indexes deleted successfully'})}\n\n"
        else:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'deletion', 'progress_percent': 20, 'message': '[DRY RUN] Skipped deletion'})}\n\n"

        # Phase 3: Indexing (use LangGraph pipeline with Docling)
        if not dry_run:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 30, 'message': f'Indexing {total_docs} documents into Qdrant...'})}\n\n"

            # Sprint 31 Feature 31.11: Use LangGraph pipeline instead of deprecated ingest_documents()
            # Import LangGraph pipeline (lazy import to avoid circular dependencies)
            from src.components.ingestion.langgraph_pipeline import run_batch_ingestion

            # Run batch ingestion with Docling + VLM + BGE-M3 + Neo4j
            batch_id = f"reindex_batch_{int(time.time())}"
            total_chunks = 0
            completed_docs = 0
            failed_docs = 0  # Track failed documents

            async for result in run_batch_ingestion(
                document_paths=[str(p) for p in document_files],
                batch_id=batch_id,
            ):
                completed_docs += 1
                doc_path = result["document_path"]
                success = result["success"]

                if success and result.get("state"):
                    state = result["state"]
                    chunk_count = len(state.get("chunks", []))
                    total_chunks += chunk_count

                    # Calculate progress (30% → 60%)
                    doc_progress = (completed_docs / total_docs) * 0.3  # 30% of total
                    overall_progress = 30 + doc_progress

                    message = f"Indexed {Path(doc_path).name}: {chunk_count} chunks"
                    yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': overall_progress, 'message': message, 'completed_documents': completed_docs, 'total_documents': total_docs})}\n\n"

                    logger.info(
                        "reindex_document_indexed",
                        document_path=doc_path,
                        chunks=chunk_count,
                        completed=completed_docs,
                        total=total_docs,
                    )
                else:
                    # Document failed
                    failed_docs += 1  # Increment failed counter
                    error_msg = result.get("error", "Unknown error")
                    logger.error("reindex_document_failed", document_path=doc_path, error=error_msg)

                    # Continue with remaining documents
                    message = f"[{_ts()}] FAILED: {Path(doc_path).name} - {error_msg}"
                    yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 30 + (completed_docs / total_docs) * 30, 'message': message, 'completed_documents': completed_docs, 'total_documents': total_docs})}\n\n"

            points_indexed = total_chunks
            message = f"Indexed {points_indexed} chunks from {completed_docs} documents into Qdrant + Neo4j"
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 90, 'message': message})}\n\n"

            # NOTE: Neo4j graph indexing is handled automatically by LangGraph pipeline
            # (graph_extraction_node in run_batch_ingestion)
            # No need for separate LlamaIndex + LightRAG processing
        else:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 90, 'message': '[DRY RUN] Skipped indexing'})}\n\n"

        # Phase 4: Validation
        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 95, 'message': 'Validating index consistency...'})}\n\n"

        if not dry_run:
            # Validate Qdrant collection
            collection_info = await qdrant_client.get_collection_info(collection_name)
            if collection_info:
                point_count = collection_info.points_count
                logger.info(
                    "qdrant_validation_complete", collection=collection_name, points=point_count
                )
            else:
                raise VectorSearchError(
                    query="", reason=f"Collection {collection_name} not found after re-indexing"
                )

            # Validate Neo4j graph
            try:
                lightrag_wrapper = await get_lightrag_wrapper_async()
                graph_stats = await lightrag_wrapper.get_stats()
                entity_count = graph_stats.get("entity_count", 0)
                relationship_count = graph_stats.get("relationship_count", 0)
                logger.info(
                    "neo4j_validation_complete",
                    entities=entity_count,
                    relationships=relationship_count,
                )
                yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 98, 'message': f'Validation successful: Qdrant={point_count} chunks, Neo4j={entity_count} entities + {relationship_count} relations'})}\n\n"
            except Exception as e:
                logger.warning("neo4j_validation_failed", error=str(e))
                yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 98, 'message': f'Validation: Qdrant={point_count} chunks (Neo4j validation skipped)'})}\n\n"
        else:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 98, 'message': '[DRY RUN] Validation skipped'})}\n\n"

        # Sprint 33: Refresh BM25 index after reindexing
        if not dry_run and total_chunks > 0:
            try:
                yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 99, 'message': 'Refreshing BM25 keyword index...'})}\n\n"

                from src.api.v1.retrieval import get_hybrid_search

                hybrid_search = get_hybrid_search()
                bm25_stats = await hybrid_search.prepare_bm25_index()
                bm25_corpus_size = bm25_stats.get("bm25_corpus_size", 0)

                logger.info(
                    "bm25_index_refreshed",
                    corpus_size=bm25_corpus_size,
                    documents_indexed=bm25_stats.get("documents_indexed", 0),
                )
            except Exception as e:
                logger.warning("bm25_refresh_failed", error=str(e))

        # Completion
        total_time = time.time() - start_time

        # Determine completion status based on failures
        if not dry_run and failed_docs > 0:
            # Some documents failed - report partial success
            success_docs = total_docs - failed_docs
            completion_message = f"Re-indexing completed with {failed_docs} failed document(s). Successfully indexed: {success_docs}/{total_docs} documents in {total_time:.1f}s"
            completion_status = "completed_with_errors"
        else:
            # All documents succeeded (or dry run)
            completion_message = f"Re-indexing completed successfully in {total_time:.1f}s"
            completion_status = "completed"

        yield f"data: {json.dumps({'status': completion_status, 'phase': 'completed', 'progress_percent': 100, 'documents_processed': total_docs, 'documents_total': total_docs, 'documents_failed': failed_docs if not dry_run else 0, 'message': completion_message})}\n\n"

        # Sprint 33: Save last reindex timestamp
        if not dry_run:
            await save_last_reindex_timestamp()

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
    **Sprint 31 Feature 31.11: Migrated to LangGraph Pipeline**

    This endpoint:
    1. Atomically deletes old indexes (Qdrant, BM25 cache, Neo4j)
    2. Reloads all documents from input directory
    3. Uses LangGraph pipeline (Docling → Chunking → Embedding → Graph Extraction)
    4. Chunks using 1800-token strategy with semantic boundaries
    5. Embeds using BGE-M3 1024-dim vectors
    6. Indexes into Qdrant + Neo4j simultaneously
    7. Validates consistency

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


# ============================================================================
# Sprint 33: ADD Documents Endpoint (no deletion)
# ============================================================================


def _build_detailed_progress(
    file_path: str,
    file_size: int,
    state: dict,
    pipeline_phase: str,
    pipeline_status: str,
) -> dict:
    """Build detailed_progress object for SSE stream.

    Args:
        file_path: Path to current file
        file_size: File size in bytes
        state: LangGraph pipeline state with chunks, entities, etc.
        pipeline_phase: Current pipeline phase name
        pipeline_status: Status of current phase

    Returns:
        DetailedProgress dict matching frontend type
    """
    from pathlib import Path

    file_name = Path(file_path).name
    file_ext = Path(file_path).suffix.lower().lstrip(".")

    # Build current_file info
    current_file = {
        "file_path": file_path,
        "file_name": file_name,
        "file_extension": file_ext,
        "file_size_bytes": file_size,
        "parser_type": "docling",  # Default to docling
        "is_supported": True,
    }

    # Extract chunks info
    chunks = state.get("chunks", [])
    chunk_infos = []
    for i, chunk in enumerate(chunks[:10]):  # Limit to first 10 chunks for display
        chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
        chunk_infos.append(
            {
                "chunk_id": f"chunk_{i}",
                "text_preview": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text,
                "token_count": len(chunk_text.split()) * 1.3,  # Rough token estimate
                "section_name": chunk.get("section", "Main") if isinstance(chunk, dict) else "Main",
                "has_image": False,
            }
        )

    # Extract entities info
    entities = state.get("entities", [])
    relations = state.get("relations", [])

    # Build pipeline status
    phases = ["docling", "chunking", "embedding", "graph_extraction", "validation"]
    pipeline_statuses = []
    for phase in phases:
        if phase == pipeline_phase:
            status = pipeline_status
        elif (
            phases.index(phase) < phases.index(pipeline_phase)
            if pipeline_phase in phases
            else False
        ):
            status = "completed"
        else:
            status = "pending"
        pipeline_statuses.append(
            {
                "phase": phase,
                "status": status,
                "duration_ms": None,
            }
        )

    # Sprint 33 Fix: Read actual detected elements from Docling parsing state
    parsed_tables = state.get("parsed_tables", [])
    parsed_images = state.get("parsed_images", [])
    page_dimensions = state.get("page_dimensions", {})
    parsed_content = state.get("parsed_content", "")

    # Try to get actual picture count from document object (more accurate for VLM)
    document = state.get("document")
    try:
        if document and hasattr(document, "pictures"):
            total_pictures = len(document.pictures)
        else:
            total_pictures = len(parsed_images)
    except Exception:
        total_pictures = len(parsed_images)

    # Calculate word count from parsed content (more accurate than chunk-based)
    word_count = (
        len(parsed_content.split())
        if parsed_content
        else sum(len(c.get("text", "").split()) if isinstance(c, dict) else 0 for c in chunks)
    )

    # Build VLM images status from vlm_metadata in state
    vlm_metadata = state.get("vlm_metadata", [])
    enrichment_status = state.get("enrichment_status", "pending")
    vlm_images = []

    # Use total_pictures for accurate VLM tracking
    total_vlm_images = total_pictures

    for idx, meta in enumerate(vlm_metadata):
        vlm_images.append(
            {
                "image_id": f"img_{idx:03d}",
                "thumbnail_url": None,  # Thumbnails not generated yet
                "status": "completed",
                "description": (
                    meta.get("description", "")[:100] if meta.get("description") else None
                ),
            }
        )

    # Add pending images that haven't been processed yet
    if enrichment_status == "running" and total_vlm_images > len(vlm_metadata):
        for idx in range(len(vlm_metadata), total_vlm_images):
            vlm_images.append(
                {
                    "image_id": f"img_{idx:03d}",
                    "thumbnail_url": None,
                    "status": "pending",
                    "description": None,
                }
            )

    # Sprint 36: Chunk-level extraction progress for entity/relation extraction
    # During graph_extraction phase, chunks_processed = total (extraction is already done)
    # The LangGraph pipeline extracts entities per-chunk internally
    chunks_total = len(chunks)
    chunks_processed = chunks_total if pipeline_phase in ["graph_extraction", "validation"] else 0

    return {
        "current_file": current_file,
        "current_page": 1,
        "total_pages": len(page_dimensions) if page_dimensions else 1,
        "page_thumbnail_url": None,
        "page_elements": {
            "tables": len(parsed_tables),
            "images": total_pictures,  # Use document.pictures count for accuracy
            "word_count": word_count,
        },
        "vlm_images": vlm_images,
        "current_chunk": chunk_infos[0] if chunk_infos else None,
        "pipeline_status": pipeline_statuses,
        "entities": {
            "new_entities": [e.get("name", str(e))[:30] for e in entities[:5]] if entities else [],
            "new_relations": (
                [r.get("type", str(r))[:30] for r in relations[:5]] if relations else []
            ),
            "total_entities": len(entities),
            "total_relations": len(relations),
        },
        # Sprint 36: Chunk-level extraction progress
        "chunks_total": chunks_total,
        "chunks_processed": chunks_processed,
    }


async def add_documents_stream(
    file_paths: list[str],
    dry_run: bool = False,
) -> AsyncGenerator[str, None]:
    """Stream progress updates during document addition (ADD-only, no deletion).

    Args:
        file_paths: List of file paths to add to index
        dry_run: If True, simulate operation without making changes

    Yields:
        SSE-formatted progress messages (JSON)
    """
    import json
    import os
    import time

    start_time = time.time()
    total_docs = len(file_paths)

    # Sprint 51: Helper for consistent timestamps
    def _ts() -> str:
        return time.strftime("%H:%M:%S", time.localtime())

    try:
        # Phase 1: Initialization
        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'initialization', 'progress_percent': 0, 'message': f'[{_ts()}] Adding {total_docs} document(s) to index...'})}\n\n"

        if total_docs == 0:
            yield f"data: {json.dumps({'status': 'completed', 'phase': 'completed', 'progress_percent': 100, 'message': f'[{_ts()}] No documents to add', 'documents_processed': 0, 'documents_total': 0})}\n\n"
            return

        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'initialization', 'progress_percent': 5, 'message': f'[{_ts()}] Preparing to index {total_docs} document(s)'})}\n\n"

        # Phase 2: Indexing (use LangGraph pipeline with Docling) - NO DELETION
        # Sprint 33: Use streaming pipeline for granular progress updates
        if not dry_run:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 10, 'message': f'[{_ts()}] Indexing {total_docs} document(s)...'})}\n\n"

            # Import LangGraph streaming pipeline (lazy import)
            import hashlib

            from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline_streaming
            from src.components.ingestion.progress_events import (
                cleanup_progress_queue,
                drain_progress_events,
                get_or_create_progress_queue,
            )

            # Sprint 51: Helper for real-time progress polling during pipeline execution
            async def stream_with_progress_polling(
                pipeline_stream,
                document_id: str,
                poll_interval: float = 1.0,
            ):
                """Merge pipeline events with periodic progress polling (every poll_interval seconds).

                This allows progress events to be sent to the frontend in real-time,
                rather than waiting for LangGraph node completion.
                """
                output_queue: asyncio.Queue = asyncio.Queue()
                stop_polling = asyncio.Event()

                async def progress_poller():
                    """Background task: poll progress queue every poll_interval seconds."""
                    while not stop_polling.is_set():
                        try:
                            events = await drain_progress_events(document_id)
                            for event in events:
                                await output_queue.put({"type": "progress", "event": event})
                        except Exception as e:
                            logger.warning("progress_polling_error", error=str(e))
                        # Wait for poll_interval or until stopped
                        with contextlib.suppress(TimeoutError):
                            await asyncio.wait_for(stop_polling.wait(), timeout=poll_interval)

                async def pipeline_consumer():
                    """Consume pipeline stream and forward to output queue."""
                    try:
                        async for update in pipeline_stream:
                            await output_queue.put({"type": "pipeline", "update": update})
                    finally:
                        await output_queue.put({"type": "done"})

                # Start background tasks
                poller_task = asyncio.create_task(progress_poller())
                consumer_task = asyncio.create_task(pipeline_consumer())

                try:
                    while True:
                        item = await output_queue.get()
                        if item["type"] == "done":
                            break
                        yield item
                finally:
                    # Cleanup: stop poller and cancel tasks
                    stop_polling.set()
                    poller_task.cancel()
                    consumer_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await poller_task
                    with contextlib.suppress(asyncio.CancelledError):
                        await consumer_task
                    # Drain any remaining progress events
                    final_events = await drain_progress_events(document_id)
                    for event in final_events:
                        yield {"type": "progress", "event": event}

            batch_id = f"add_batch_{int(time.time())}"
            total_chunks = 0
            completed_docs = 0
            failed_docs = 0
            all_entities: list[dict] = []
            all_relations: list[dict] = []

            # Node name to human-readable phase mapping
            # NOTE: Node names from LangGraph have NO "_node" suffix!
            # See langgraph_pipeline.py: graph.add_node("memory_check", ...)
            # Sprint 51: Added *_progress variants for granular extraction updates
            node_phases = {
                "memory_check": ("memory_check", "Checking document memory..."),
                "parse": ("parse", "Parsing document..."),
                "image_enrichment": ("image_enrichment", "Processing images with VLM..."),
                "chunking": ("chunking", "Creating text chunks..."),
                "embedding": ("embedding", "Generating embeddings..."),
                "graph": ("graph", "Extracting entities and relations..."),
                # Sprint 51: Progress events for granular extraction feedback
                "graph_progress": ("graph", None),  # Will use progress_event message
            }

            def _format_timestamp() -> str:
                """Get current timestamp in HH:MM:SS format."""
                return time.strftime("%H:%M:%S", time.localtime())

            # Node name to progress percentage (within document: 10% to 90% of doc's share)
            node_progress = {
                "memory_check": 0.05,
                "parse": 0.25,
                "image_enrichment": 0.40,
                "chunking": 0.55,
                "embedding": 0.75,
                "graph": 1.0,
            }

            # Process each document with streaming progress
            for doc_index, doc_path in enumerate(file_paths):
                # Generate document ID
                document_id = hashlib.sha256(doc_path.encode()).hexdigest()[:16]

                # Calculate base progress for this document (10% to 90% total range)
                doc_base_progress = 10 + (doc_index / total_docs) * 80
                doc_progress_range = 80 / total_docs  # Each doc gets equal share

                try:
                    # Get file size
                    try:
                        file_size = os.path.getsize(doc_path)
                    except OSError:
                        file_size = 0

                    last_state = None

                    # Sprint 51: Create progress queue for real-time polling
                    await get_or_create_progress_queue(document_id)

                    # Create pipeline stream
                    pipeline_stream = run_ingestion_pipeline_streaming(
                        document_path=doc_path,
                        document_id=document_id,
                        batch_id=batch_id,
                        batch_index=doc_index,
                        total_documents=total_docs,
                    )

                    # Sprint 51: Stream with real-time progress polling (every 1 second)
                    async for item in stream_with_progress_polling(
                        pipeline_stream, document_id, poll_interval=1.0
                    ):
                        # Handle real-time progress events from background poller
                        if item["type"] == "progress":
                            progress_event = item["event"].to_dict()
                            event_timestamp = progress_event.get("timestamp", _format_timestamp())
                            event_message = progress_event.get("message", "Processing...")
                            event_phase = progress_event.get("phase", "graph")

                            # Calculate progress based on extraction phase
                            event_current = progress_event.get("current", 0)
                            event_total = progress_event.get("total", 1)
                            if event_phase == "entity_extraction":
                                phase_progress = 0.70 + (event_current / max(event_total, 1)) * 0.10
                            elif event_phase == "relation_extraction":
                                phase_progress = 0.80 + (event_current / max(event_total, 1)) * 0.10
                            elif event_phase == "community_detection":
                                phase_progress = 0.90 + (event_current / max(event_total, 1)) * 0.05
                            else:
                                phase_progress = 0.75

                            overall_progress = doc_base_progress + (phase_progress * doc_progress_range)
                            message = f"[{event_timestamp}] {Path(doc_path).name}: {event_message}"

                            # Sprint 51: Include entity/relation counts for Live Metrics
                            event_details = progress_event.get("details", {})
                            detailed_progress = {
                                "current_file": Path(doc_path).name,
                                "entities": {
                                    "total_entities": event_details.get("total_entities", 0),
                                    "total_relations": event_details.get("total_relations", 0),
                                },
                            }

                            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': overall_progress, 'message': message, 'documents_processed': doc_index, 'documents_total': total_docs, 'current_document': Path(doc_path).name, 'extraction_phase': event_phase, 'detailed_progress': detailed_progress})}\n\n"

                            logger.debug(
                                "realtime_progress_event",
                                document_path=doc_path,
                                phase=event_phase,
                                current=event_current,
                                total=event_total,
                            )
                            continue

                        # Handle pipeline events (node completions)
                        update = item["update"]
                        node_name = update.get("node", "unknown")
                        state = update.get("state", {})
                        last_state = state
                        progress_event = update.get("progress_event")

                        # Get phase info
                        phase_info = node_phases.get(
                            node_name, ("indexing", f"Processing {node_name}...")
                        )

                        # Skip progress events from pipeline (already handled by real-time poller)
                        if progress_event:
                            # Progress events are now handled by the background poller
                            # Skip to avoid duplicates
                            continue

                        # Regular node completion - add timestamp
                        node_progress_val = node_progress.get(node_name, 0.5)

                        # Calculate overall progress
                        overall_progress = doc_base_progress + (
                            node_progress_val * doc_progress_range
                        )

                        # Build detailed progress
                        detailed_progress = _build_detailed_progress(
                            file_path=doc_path,
                            file_size=file_size,
                            state=state,
                            pipeline_phase=phase_info[0],
                            pipeline_status="in_progress",
                        )

                        # Sprint 51: Add timestamp to all messages
                        timestamp = _format_timestamp()
                        message = f"[{timestamp}] {Path(doc_path).name}: {phase_info[1]}"
                        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': overall_progress, 'message': message, 'documents_processed': doc_index, 'documents_total': total_docs, 'current_document': Path(doc_path).name, 'detailed_progress': detailed_progress})}\n\n"

                        logger.debug(
                            "add_document_node_progress",
                            document_path=doc_path,
                            node=node_name,
                            progress=overall_progress,
                        )

                    # Document completed - check for errors
                    if last_state and last_state.get("errors"):
                        failed_docs += 1
                        error_list = last_state.get("errors", [])
                        error_msg = (
                            error_list[0].get("message", "Unknown error")
                            if error_list
                            else "Unknown error"
                        )
                        logger.error("add_document_failed", document_path=doc_path, error=error_msg)

                        error_info = {
                            "type": "error",
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "file_name": Path(doc_path).name,
                            "message": error_msg,
                            "details": str(error_list),
                        }

                        message = f"[{_ts()}] FAILED: {Path(doc_path).name} - {error_msg}"
                        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': doc_base_progress + doc_progress_range, 'message': message, 'documents_processed': doc_index + 1, 'documents_total': total_docs, 'errors': [error_info]})}\n\n"
                    else:
                        # Success - count chunks
                        completed_docs += 1
                        if last_state:
                            chunk_count = len(last_state.get("chunks", []))
                            total_chunks += chunk_count
                            all_entities.extend(last_state.get("entities", []))
                            all_relations.extend(last_state.get("relations", []))

                            detailed_progress = _build_detailed_progress(
                                file_path=doc_path,
                                file_size=file_size,
                                state=last_state,
                                pipeline_phase="graph_extraction",
                                pipeline_status="completed",
                            )

                            message = f"[{_ts()}] Added {Path(doc_path).name}: {chunk_count} chunks"
                            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': doc_base_progress + doc_progress_range, 'message': message, 'documents_processed': doc_index + 1, 'documents_total': total_docs, 'current_document': Path(doc_path).name, 'detailed_progress': detailed_progress})}\n\n"

                            logger.info(
                                "add_document_indexed",
                                document_path=doc_path,
                                chunks=chunk_count,
                                completed=completed_docs,
                                total=total_docs,
                            )

                    # Sprint 51: Cleanup progress queue after document
                    await cleanup_progress_queue(document_id)

                except Exception as e:
                    failed_docs += 1
                    error_msg = str(e)
                    logger.error("add_document_exception", document_path=doc_path, error=error_msg)

                    error_info = {
                        "type": "error",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "file_name": Path(doc_path).name,
                        "message": error_msg,
                        "details": "",
                    }

                    message = f"[{_ts()}] FAILED: {Path(doc_path).name} - {error_msg}"
                    yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': doc_base_progress + doc_progress_range, 'message': message, 'documents_processed': doc_index + 1, 'documents_total': total_docs, 'errors': [error_info]})}\n\n"

                    # Sprint 51: Cleanup progress queue even on error
                    await cleanup_progress_queue(document_id)

            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 90, 'message': f'[{_ts()}] Added {total_chunks} chunks from {completed_docs} document(s)'})}\n\n"
        else:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 90, 'message': f'[{_ts()}] [DRY RUN] Skipped indexing'})}\n\n"
            completed_docs = total_docs
            failed_docs = 0
            total_chunks = 0

        # Phase 3: Validation + BM25 Refresh
        yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 92, 'message': f'[{_ts()}] Validating index...'})}\n\n"

        # Sprint 33: Refresh BM25 index after adding documents
        # This ensures BM25 keyword search is synchronized with Qdrant vector store
        if not dry_run and completed_docs > 0:
            try:
                yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 95, 'message': f'[{_ts()}] Refreshing BM25 keyword index...'})}\n\n"

                from src.api.v1.retrieval import get_hybrid_search

                hybrid_search = get_hybrid_search()
                bm25_stats = await hybrid_search.prepare_bm25_index()
                bm25_corpus_size = bm25_stats.get("bm25_corpus_size", 0)

                logger.info(
                    "bm25_index_refreshed",
                    corpus_size=bm25_corpus_size,
                    documents_indexed=bm25_stats.get("documents_indexed", 0),
                )

                yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 98, 'message': f'[{_ts()}] BM25 index refreshed ({bm25_corpus_size} documents)'})}\n\n"
            except Exception as e:
                logger.warning("bm25_refresh_failed", error=str(e))
                yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'validation', 'progress_percent': 98, 'message': f'[{_ts()}] BM25 refresh failed: {str(e)} (non-critical)'})}\n\n"

        # Completion
        elapsed_time = time.time() - start_time
        success_count = completed_docs

        # Sprint 49 Feature 49.4: Determine status based on success/failure counts
        # Sprint 51: Include entity/relation totals in completion message
        total_entities_count = len(all_entities)
        total_relations_count = len(all_relations)
        entity_info = f", {total_entities_count} entities, {total_relations_count} relations" if total_entities_count > 0 else ""

        if failed_docs == 0:
            # All succeeded
            completion_message = f"[{_ts()}] Successfully added {success_count} document(s) ({total_chunks} chunks{entity_info}) in {elapsed_time:.1f}s"
        elif success_count == 0:
            # All failed
            completion_message = f"[{_ts()}] Failed to add {failed_docs} document(s) in {elapsed_time:.1f}s"
        else:
            # Partial success
            completion_message = f"[{_ts()}] Partially completed: {success_count} document(s) indexed ({total_chunks} chunks{entity_info}), {failed_docs} failed in {elapsed_time:.1f}s"

        yield f"data: {json.dumps({'status': 'completed', 'phase': 'completed', 'progress_percent': 100, 'message': completion_message, 'documents_processed': success_count, 'documents_total': total_docs, 'chunks_created': total_chunks, 'failed_documents': failed_docs})}\n\n"

        logger.info(
            "add_documents_completed",
            total_docs=total_docs,
            success_count=success_count,
            failed_count=failed_docs,
            total_chunks=total_chunks,
            elapsed_seconds=elapsed_time,
        )

        # Sprint 33: Save last reindex timestamp
        if not dry_run and success_count > 0:
            await save_last_reindex_timestamp()

    except Exception as e:
        logger.error("add_documents_error", error=str(e), exc_info=True)
        yield f"data: {json.dumps({'status': 'error', 'phase': 'error', 'progress_percent': 0, 'message': f'Error: {str(e)}', 'error': str(e)})}\n\n"


@router.post(
    "/indexing/add",
    summary="Add documents to index (no deletion)",
    description="Add selected documents to the existing index without deleting anything. Progress tracked via SSE.",
)
async def add_documents_to_index(
    file_paths: list[str] = Query(
        default=[],
        description="List of file paths to add to index",
    ),
    dry_run: bool = Query(
        default=False,
        description="Simulate operation without making changes",
    ),
) -> StreamingResponse:
    """Add documents to existing index without deletion.

    **Sprint 33: ADD-only indexing (no deletion)**

    This endpoint:
    1. Takes a list of file paths to add
    2. Uses LangGraph pipeline (Docling → Chunking → Embedding → Graph Extraction)
    3. Adds documents to existing Qdrant + Neo4j indexes
    4. Does NOT delete any existing data

    **Use Cases:**
    - Adding new documents to existing knowledge base
    - Incremental updates without full re-index
    - Selective file indexing from directory scan

    **Progress Tracking:**
    - Returns SSE (Server-Sent Events) stream
    - Real-time progress updates with percentage
    - Final message indicates completion or error

    **Example Usage:**
    ```bash
    curl -N "http://localhost:8000/api/v1/admin/indexing/add?file_paths=doc1.pdf&file_paths=doc2.pdf" \\
      -H "Accept: text/event-stream"
    ```

    Args:
        file_paths: List of file paths to add
        dry_run: If True, simulate operation without making changes

    Returns:
        StreamingResponse with SSE progress updates
    """
    # Validate file paths exist
    valid_paths = []
    for fp in file_paths:
        path = Path(fp)
        if path.exists() and path.is_file():
            valid_paths.append(str(path))
        else:
            logger.warning("add_documents_invalid_path", path=fp)

    if not valid_paths and not dry_run:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid file paths provided",
        )

    logger.info(
        "add_documents_started",
        file_count=len(valid_paths),
        dry_run=dry_run,
    )

    return StreamingResponse(
        add_documents_stream(valid_paths, dry_run=dry_run),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Sprint 35 Feature 35.10: File Upload Endpoint
# ============================================================================


class UploadFileInfo(BaseModel):
    """Information about an uploaded file."""

    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Server path to uploaded file")
    file_size_bytes: int = Field(..., description="File size in bytes")
    file_extension: str = Field(..., description="File extension (e.g., 'pdf', 'docx')")


class UploadResponse(BaseModel):
    """Response from file upload endpoint."""

    upload_dir: str = Field(..., description="Directory where files were uploaded")
    files: list[UploadFileInfo] = Field(..., description="List of uploaded files")
    total_size_bytes: int = Field(..., description="Total size of all uploaded files")


# File size limit: 100MB per file
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB


@router.post(
    "/indexing/upload",
    response_model=UploadResponse,
    summary="Upload files for indexing",
    description="Upload one or more files to the server for subsequent indexing. Files are stored in data/uploads/{session_id}/",
)
async def upload_files(
    files: list[UploadFile] = File(..., description="Files to upload")
) -> UploadResponse:
    """Upload files to server for indexing.

    **Sprint 35 Feature 35.10: File Upload for Admin Indexing**

    This endpoint:
    1. Accepts multiple files via multipart/form-data
    2. Validates file sizes (max 100MB per file)
    3. Creates a unique upload directory (data/uploads/{uuid})
    4. Saves files to the upload directory
    5. Returns file paths for use with /indexing/add endpoint

    **Workflow:**
    1. User selects files in frontend
    2. Frontend uploads files to this endpoint
    3. Frontend receives upload_dir and file paths
    4. Frontend calls /indexing/add with returned file paths
    5. Backend indexes files via LangGraph pipeline

    **Security:**
    - File size validation (max 100MB per file)
    - Files stored in isolated directory (data/uploads/{uuid})
    - No filename validation (backend handles all file types)

    **Example Usage:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/admin/indexing/upload" \\
      -F "files=@document1.pdf" \\
      -F "files=@document2.docx"
    ```

    Args:
        files: List of files to upload (UploadFile objects)

    Returns:
        UploadResponse with upload directory and file information

    Raises:
        HTTPException 400: If no files provided or file too large
        HTTPException 500: If upload fails
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    # Create unique upload directory
    upload_session_id = str(uuid.uuid4())
    upload_dir = Path("data/uploads") / upload_session_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "file_upload_started",
        session_id=upload_session_id,
        file_count=len(files),
        feature="sprint_35_feature_35.10",
    )

    uploaded_files = []
    total_size = 0

    try:
        for file in files:
            # Validate file size
            file_content = await file.read()
            file_size = len(file_content)

            if file_size > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f}MB",
                )

            # Save file
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Get file extension
            file_ext = Path(file.filename).suffix.lower().lstrip(".")

            uploaded_files.append(
                UploadFileInfo(
                    filename=file.filename,
                    file_path=str(file_path),
                    file_size_bytes=file_size,
                    file_extension=file_ext,
                )
            )
            total_size += file_size

            logger.info(
                "file_uploaded",
                filename=file.filename,
                size_bytes=file_size,
                path=str(file_path),
            )

        logger.info(
            "file_upload_completed",
            session_id=upload_session_id,
            file_count=len(uploaded_files),
            total_size_bytes=total_size,
        )

        return UploadResponse(
            upload_dir=str(upload_dir),
            files=uploaded_files,
            total_size_bytes=total_size,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "file_upload_failed", session_id=upload_session_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}",
        ) from e


# ============================================================================
# Sprint 37 Feature 37.8: Parallel Batch Indexing
# ============================================================================


class BatchIndexingRequest(BaseModel):
    """Request model for parallel batch indexing.

    Sprint 37 Feature 37.8: Multi-Document Parallelization
    """

    file_paths: list[str] = Field(..., description="List of file paths to index")


class BatchIndexingResponse(BaseModel):
    """Response model for batch indexing job.

    Sprint 37 Feature 37.8: Multi-Document Parallelization
    """

    batch_id: str = Field(..., description="Unique batch identifier")
    total_documents: int = Field(..., description="Total number of documents to process")
    parallel_limit: int = Field(..., description="Maximum concurrent documents (default 3)")
    status: str = Field(..., description="Batch status (started, in_progress, completed, error)")


@router.post(
    "/indexing/batch",
    response_model=BatchIndexingResponse,
    summary="Start parallel batch indexing",
    description="Process multiple documents concurrently (up to 3 at a time) using ParallelIngestionOrchestrator.",
)
async def start_batch_indexing(
    request: BatchIndexingRequest,
) -> BatchIndexingResponse:
    """Start parallel batch indexing for multiple documents.

    **Sprint 37 Feature 37.8: Multi-Document Parallelization**

    This endpoint:
    1. Accepts a list of file paths to index
    2. Uses ParallelIngestionOrchestrator to process up to 3 documents concurrently
    3. Tracks per-document progress via MultiDocProgressManager
    4. Returns batch ID for progress streaming via /indexing/batch/{batch_id}/stream

    **Parallelization:**
    - File-level: Process 3 files concurrently (PARALLEL_FILES=3)
    - Chunk-level: Generate 10 embeddings concurrently (PARALLEL_CHUNKS=10)
    - Error isolation: One file error doesn't stop others

    **Example Request:**
    ```json
    {
      "file_paths": [
        "/data/uploads/abc123/report.pdf",
        "/data/uploads/abc123/slides.pptx",
        "/data/uploads/abc123/notes.docx"
      ]
    }
    ```

    **Example Response:**
    ```json
    {
      "batch_id": "batch-xyz789",
      "total_documents": 3,
      "parallel_limit": 3,
      "status": "started"
    }
    ```

    **Next Steps:**
    - Poll /indexing/batch/{batch_id}/stream for progress updates

    Args:
        request: BatchIndexingRequest with file paths

    Returns:
        BatchIndexingResponse with batch ID and status

    Raises:
        HTTPException 400: If no valid file paths provided
        HTTPException 500: If batch initialization fails
    """
    # Validate file paths exist
    valid_paths = []
    for fp in request.file_paths:
        path = Path(fp)
        if path.exists() and path.is_file():
            valid_paths.append(str(path))
        else:
            logger.warning("batch_indexing_invalid_path", path=fp)

    if not valid_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid file paths provided",
        )

    batch_id = str(uuid.uuid4())

    logger.info(
        "batch_indexing_started",
        batch_id=batch_id,
        total_documents=len(valid_paths),
        parallel_limit=3,
        feature="sprint_37_feature_37.8",
    )

    # Initialize multi-doc progress tracking
    from src.components.ingestion.multi_doc_progress import get_multi_doc_progress_manager

    progress_manager = get_multi_doc_progress_manager()
    documents = [
        {"id": f"{batch_id}-{i}", "name": Path(p).name, "path": p}
        for i, p in enumerate(valid_paths)
    ]
    progress_manager.start_batch(batch_id, documents, parallel_limit=3)

    # Start parallel processing in background
    asyncio.create_task(_run_parallel_batch(batch_id, valid_paths, progress_manager))

    return BatchIndexingResponse(
        batch_id=batch_id,
        total_documents=len(valid_paths),
        parallel_limit=3,
        status="started",
    )


async def _run_parallel_batch(
    batch_id: str,
    file_paths: list[str],
    progress_manager,
) -> None:
    """Background task to run parallel document processing.

    Sprint 37 Feature 37.8: Multi-Document Parallelization

    Args:
        batch_id: Unique batch identifier
        file_paths: List of file paths to process
        progress_manager: MultiDocProgressManager instance

    Notes:
        - Uses ParallelIngestionOrchestrator for concurrent processing
        - Updates progress_manager with per-document progress
        - Errors in one document don't stop others
    """
    from src.components.ingestion.job_tracker import get_job_tracker
    from src.components.ingestion.parallel_orchestrator import get_parallel_orchestrator

    orchestrator = get_parallel_orchestrator()
    job_tracker = get_job_tracker()
    files = [Path(p) for p in file_paths]

    # Create ingestion job for tracking
    job_id = await job_tracker.create_job(
        directory_path=str(files[0].parent),
        recursive=False,
        total_files=len(files),
    )

    try:
        async for progress in orchestrator.process_files_parallel(
            files, job_tracker=job_tracker, job_id=job_id
        ):
            # Extract file index from progress
            file_path = progress.get("file_path", "")
            doc_id = None
            for i, fp in enumerate(file_paths):
                if fp == file_path:
                    doc_id = f"{batch_id}-{i}"
                    break

            if not doc_id:
                continue

            # Determine status from progress
            if progress.get("status") == "completed":
                status = "completed"
            elif progress.get("status") == "error":
                status = "error"
            else:
                status = "processing"

            # Update document progress
            progress_manager.update_document(
                batch_id=batch_id,
                document_id=doc_id,
                status=status,
                progress_percent=progress.get("progress_percent", 0),
                chunks_created=progress.get("chunks_created"),
                entities_extracted=progress.get("entities_extracted"),
                relations_extracted=progress.get("relations_extracted"),
                error=progress.get("error"),
            )

            logger.debug(
                "batch_document_progress",
                batch_id=batch_id,
                document_id=doc_id,
                status=status,
                progress_percent=progress.get("progress_percent", 0),
            )

    except Exception as e:
        logger.error("batch_processing_failed", batch_id=batch_id, error=str(e), exc_info=True)
        # Mark all pending/processing documents as error
        batch = progress_manager.get_batch(batch_id)
        if batch:
            for doc in batch.documents.values():
                if doc.status in ("pending", "processing"):
                    progress_manager.update_document(
                        batch_id=batch_id,
                        document_id=doc.document_id,
                        status="error",
                        error=str(e),
                    )


@router.get(
    "/indexing/batch/{batch_id}/stream",
    summary="Stream batch progress via SSE",
    description="Stream real-time progress updates for a batch indexing job via Server-Sent Events.",
)
async def stream_batch_progress(
    batch_id: str,
    request: Request,
) -> StreamingResponse:
    """Stream batch progress via SSE.

    **Sprint 37 Feature 37.8: Multi-Document Parallelization**

    This endpoint:
    1. Streams real-time progress updates via Server-Sent Events (SSE)
    2. Sends batch_progress events with aggregated statistics
    3. Sends complete event when all documents finished
    4. Auto-disconnects if client disconnects

    **SSE Event Format:**
    ```
    event: batch_progress
    data: {
      "batch_id": "batch-xyz789",
      "total_documents": 3,
      "parallel_limit": 3,
      "completed": 1,
      "in_progress": 2,
      "failed": 0,
      "overall_progress_percent": 33.3,
      "documents": [
        {
          "document_id": "batch-xyz789-0",
          "document_name": "report.pdf",
          "status": "completed",
          "progress_percent": 100.0,
          "chunks_created": 42,
          "entities_extracted": 15,
          "error": null
        },
        ...
      ]
    }

    event: complete
    data: {}
    ```

    **Example Usage:**
    ```javascript
    const eventSource = new EventSource('/api/v1/admin/indexing/batch/batch-xyz789/stream');
    eventSource.addEventListener('batch_progress', (e) => {
      const data = JSON.parse(e.data);
      console.log(`Overall: ${data.overall_progress_percent}%`);
    });
    eventSource.addEventListener('complete', () => {
      eventSource.close();
    });
    ```

    Args:
        batch_id: Batch identifier from /indexing/batch response
        request: FastAPI Request object (for disconnect detection)

    Returns:
        StreamingResponse with text/event-stream content type

    Raises:
        HTTPException 404: If batch ID not found
    """
    import json

    from src.components.ingestion.multi_doc_progress import get_multi_doc_progress_manager

    progress_manager = get_multi_doc_progress_manager()

    # Verify batch exists
    batch = progress_manager.get_batch(batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found",
        )

    async def event_generator():
        """Generate SSE events for batch progress."""
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("batch_stream_disconnected", batch_id=batch_id)
                    break

                # Get current batch state
                batch = progress_manager.get_batch(batch_id)
                if batch:
                    event = batch.to_sse_event()
                    yield f"event: {event['type']}\n"
                    yield f"data: {json.dumps(event['data'])}\n\n"

                    # Check if batch completed
                    if batch.overall_progress_percent >= 100:
                        yield "event: complete\ndata: {}\n\n"
                        logger.info(
                            "batch_completed",
                            batch_id=batch_id,
                            completed=batch.completed_count,
                            failed=batch.failed_count,
                        )
                        break
                else:
                    # Batch removed (likely completed and cleaned up)
                    yield "event: complete\ndata: {}\n\n"
                    break

                # Wait before next update (2 updates per second)
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error("batch_stream_error", batch_id=batch_id, error=str(e), exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ============================================================================
# Sprint 30: VLM-Enhanced Re-Indexing with Image Descriptions
# ============================================================================


@router.post(
    "/reindex_with_vlm",
    response_class=StreamingResponse,
    summary="Re-index documents with VLM image enrichment",
    description="Full LangGraph pipeline: Docling + Qwen3-VL + BGE-M3 + Neo4j. Progress via SSE.",
)
async def reindex_with_vlm_enrichment(
    input_dir: str = Query(
        default="data/sample_documents",
        description="Directory containing documents to index with VLM image enrichment",
    ),
    confirm: bool = Query(
        default=False,
        description="Confirmation required to execute (safety check)",
    ),
) -> StreamingResponse:
    """Re-index documents with VLM image enrichment (Sprint 30).

    **Full LangGraph Pipeline:**
    1. Docling CUDA Container → Parse PDF/PPTX + extract images
    2. Qwen3-VL Image Enrichment → Generate descriptions for all images
    3. Chunking → 1800-token chunks with image context
    4. BGE-M3 Embeddings → Index to Qdrant
    5. Graph Extraction → Entities + Relations to Neo4j

    **Supported Formats:**
    - PDF (with embedded images)
    - PPTX (PowerPoint with images)
    - DOCX, TXT, MD, CSV

    **VLM Configuration:**
    - Local: Qwen3-VL via Ollama (5-6GB VRAM)
    - Cloud Fallback: Alibaba DashScope qwen3-vl models
    - Image Filtering: Min size 100px, aspect ratio 0.1-10.0

    **Progress Tracking:**
    - Real-time SSE stream
    - Per-document progress (6 nodes each)
    - VLM image count tracking
    - Cost tracking via AegisLLMProxy

    **Safety:**
    - `confirm=true` required (prevents accidental deletion)
    - Old indexes deleted before re-indexing
    - Batch processing (one document at a time for memory optimization)

    **Example Usage:**
    ```bash
    # PowerShell
    $dir = "C:\\path\\to\\documents"
    curl -N "http://localhost:8000/api/v1/admin/reindex_with_vlm?input_dir=$([Uri]::EscapeDataString($dir))&confirm=true" `
      -H "Accept: text/event-stream"
    ```

    Args:
        input_dir: Directory containing documents to index
        confirm: Must be True to execute (safety check)

    Returns:
        StreamingResponse with SSE progress updates

    Raises:
        HTTPException: If confirm=false or directory not found
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required: set confirm=true to execute VLM re-indexing. This will delete all existing indexes!",
        )

    input_path = Path(input_dir)

    if not input_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Directory not found: {input_dir}",
        )

    logger.info(
        "vlm_reindex_started",
        input_dir=str(input_path),
        confirm=confirm,
        feature="sprint_30_vlm_enrichment",
    )

    # Import LangGraph pipeline (lazy import to avoid circular dependencies)
    from src.components.ingestion.langgraph_pipeline import run_batch_ingestion

    async def vlm_reindex_stream():
        """Stream VLM re-indexing progress via SSE."""
        import json
        import time

        start_time = time.time()

        try:
            # Phase 1: Discover documents
            yield f"data: {json.dumps({'status': 'discovery', 'progress': 0.0, 'message': 'Discovering documents...'})}\n\n"

            doc_paths = []
            for ext in [".pdf", ".pptx", ".docx", ".txt", ".md", ".csv"]:
                doc_paths.extend([str(p) for p in input_path.glob(f"*{ext}")])

            if not doc_paths:
                raise VectorSearchError(
                    query="",
                    reason=f"No documents found in {input_dir}",
                )

            total_docs = len(doc_paths)
            yield f"data: {json.dumps({'status': 'discovery', 'progress': 0.05, 'message': f'Found {total_docs} documents', 'total_documents': total_docs})}\n\n"

            # Phase 2: Clear old indexes (same as /reindex endpoint)
            yield f"data: {json.dumps({'status': 'deletion', 'progress': 0.1, 'message': 'Deleting old indexes...'})}\n\n"

            # Delete Qdrant collection
            qdrant_client = get_qdrant_client()
            embedding_service = get_embedding_service()
            collection_name = settings.qdrant_collection

            await qdrant_client.delete_collection(collection_name)
            logger.info("deleted_qdrant_collection", collection=collection_name)

            # Recreate collection
            await qdrant_client.create_collection(
                collection_name=collection_name,
                vector_size=embedding_service.embedding_dim,
                distance=Distance.COSINE,
            )
            logger.info("recreated_qdrant_collection", collection=collection_name)

            # Clear BM25 cache
            # Note: BM25Search uses "bm25_index.pkl" (not "bm25_model.pkl")
            bm25_cache_path = Path("data/cache/bm25_index.pkl")
            if bm25_cache_path.exists():
                bm25_cache_path.unlink()
                logger.info("cleared_bm25_cache")

            # Clear Neo4j graph
            try:
                lightrag_wrapper = await get_lightrag_wrapper_async()
                await lightrag_wrapper._clear_neo4j_database()
                logger.info("cleared_neo4j_database")
            except Exception as e:
                logger.warning("neo4j_clear_failed", error=str(e))

            yield f"data: {json.dumps({'status': 'deletion', 'progress': 0.15, 'message': 'Old indexes deleted'})}\n\n"

            # Phase 3: Batch ingestion with VLM enrichment
            batch_id = f"vlm_batch_{int(time.time())}"
            completed_docs = 0
            failed_docs = 0  # Track failed documents
            total_chunks = 0
            total_vlm_images = 0
            total_errors = 0

            msg = f"Starting VLM batch ingestion (batch_id={batch_id})..."
            yield f'data: {json.dumps({"status": "ingestion", "progress": 0.2, "message": msg})}\n\n'

            async for result in run_batch_ingestion(doc_paths, batch_id):
                completed_docs += 1
                doc_id = result["document_id"]
                doc_path = result["document_path"]
                success = result["success"]
                batch_progress = result["batch_progress"]

                # Calculate overall progress (15% for deletion, 80% for ingestion, 5% for validation)
                overall_progress = 0.15 + (batch_progress * 0.8)

                if success and result.get("state"):
                    state = result["state"]
                    chunk_count = len(state.get("chunks", []))
                    vlm_count = len(state.get("vlm_metadata", []))
                    error_count = len(state.get("errors", []))

                    total_chunks += chunk_count
                    total_vlm_images += vlm_count
                    total_errors += error_count

                    doc_name = Path(doc_path).name
                    data = {
                        "status": "ingestion",
                        "progress": overall_progress,
                        "message": f"Processed {doc_name}",
                        "document_id": doc_id,
                        "document_path": doc_path,
                        "completed_documents": completed_docs,
                        "total_documents": total_docs,
                        "batch_progress": batch_progress,
                        "chunks": chunk_count,
                        "vlm_images": vlm_count,
                        "errors": error_count,
                        "success": True,
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                    logger.info(
                        "vlm_document_indexed",
                        document_id=doc_id,
                        chunks=chunk_count,
                        vlm_images=vlm_count,
                        batch_progress=batch_progress,
                    )
                else:
                    # Document failed
                    failed_docs += 1  # Increment failed counter
                    error_msg = result.get("error", "Unknown error")
                    total_errors += 1

                    doc_name = Path(doc_path).name
                    error_data = {
                        "status": "ingestion",
                        "progress": overall_progress,
                        "message": f"FAILED: {doc_name}",
                        "document_id": doc_id,
                        "document_path": doc_path,
                        "completed_documents": completed_docs,
                        "total_documents": total_docs,
                        "batch_progress": batch_progress,
                        "success": False,
                        "error": error_msg,
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"

                    logger.error(
                        "vlm_document_failed",
                        document_id=doc_id,
                        error=error_msg,
                    )

            # Phase 4: Validation
            validation_data = {
                "status": "validation",
                "progress": 0.98,
                "message": "Validating indexes...",
            }
            yield f"data: {json.dumps(validation_data)}\n\n"

            # Get final stats
            collection_info = await qdrant_client.get_collection_info(collection_name)
            qdrant_points = collection_info.points_count if collection_info else 0

            try:
                lightrag_wrapper = await get_lightrag_wrapper_async()
                graph_stats = await lightrag_wrapper.get_stats()
                neo4j_entities = graph_stats.get("entity_count", 0)
                neo4j_relations = graph_stats.get("relationship_count", 0)
            except Exception as e:
                logger.warning("neo4j_validation_failed", error=str(e))
                neo4j_entities = 0
                neo4j_relations = 0

            # Sprint 33: Refresh BM25 index after VLM reindexing
            if total_chunks > 0:
                try:
                    yield f"data: {json.dumps({'status': 'validation', 'progress': 0.99, 'message': 'Refreshing BM25 keyword index...'})}\n\n"

                    from src.api.v1.retrieval import get_hybrid_search

                    hybrid_search = get_hybrid_search()
                    bm25_stats = await hybrid_search.prepare_bm25_index()
                    bm25_corpus_size = bm25_stats.get("bm25_corpus_size", 0)

                    logger.info(
                        "bm25_index_refreshed",
                        corpus_size=bm25_corpus_size,
                        documents_indexed=bm25_stats.get("documents_indexed", 0),
                    )
                except Exception as e:
                    logger.warning("bm25_refresh_failed", error=str(e))

            # Completion
            total_time = time.time() - start_time

            # Determine completion status based on failures
            if failed_docs > 0:
                # Some documents failed - report partial success
                success_docs = total_docs - failed_docs
                completion_message = f"VLM re-indexing completed with {failed_docs} failed document(s). Successfully indexed: {success_docs}/{total_docs} documents in {total_time:.1f}s"
                completion_status = "completed_with_errors"
            else:
                # All documents succeeded
                completion_message = f"VLM re-indexing completed successfully in {total_time:.1f}s"
                completion_status = "completed"

            final_data = {
                "status": completion_status,
                "progress": 1.0,
                "message": completion_message,
                "total_documents": total_docs,
                "completed_documents": completed_docs,
                "documents_failed": failed_docs,
                "total_chunks": total_chunks,
                "total_vlm_images": total_vlm_images,
                "total_errors": total_errors,
                "qdrant_points": qdrant_points,
                "neo4j_entities": neo4j_entities,
                "neo4j_relations": neo4j_relations,
                "duration_seconds": total_time,
            }
            yield f"data: {json.dumps(final_data)}\n\n"

            logger.info(
                "vlm_reindex_completed",
                total_docs=total_docs,
                total_chunks=total_chunks,
                total_vlm_images=total_vlm_images,
                total_errors=total_errors,
                duration_seconds=total_time,
            )

            # Sprint 33: Save last reindex timestamp
            if total_chunks > 0:
                await save_last_reindex_timestamp()

        except Exception as e:
            logger.error("vlm_reindex_failed", error=str(e), exc_info=True)
            error_msg = f"VLM re-indexing failed: {str(e)}"
            error_response = {"status": "error", "message": error_msg}
            yield f"data: {json.dumps(error_response)}\n\n"

    return StreamingResponse(
        vlm_reindex_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ============================================================================
# Sprint 33: Enhanced Directory Indexing
# Feature 33.1: Directory Scanning API
# ============================================================================


class FileInfo(BaseModel):
    """Information about a single file in a directory scan.

    Sprint 33 Feature 33.1: Directory Selector
    """

    file_path: str = Field(..., description="Full path to the file")
    file_name: str = Field(..., description="File name without path")
    file_extension: str = Field(..., description="File extension (e.g., '.pdf')")
    file_size_bytes: int = Field(..., description="File size in bytes")
    parser_type: Literal["docling", "llamaindex", "unsupported"] = Field(
        ..., description="Which parser will handle this file"
    )
    is_supported: bool = Field(..., description="Whether this file type is supported")


class DirectoryScanStatistics(BaseModel):
    """Statistics about files found in a directory scan.

    Sprint 33 Feature 33.1: Directory Selector
    """

    total: int = Field(..., description="Total number of files found")
    docling_supported: int = Field(..., description="Files supported by Docling parser")
    llamaindex_supported: int = Field(..., description="Files supported by LlamaIndex parser")
    unsupported: int = Field(..., description="Files not supported (will be skipped)")
    total_size_bytes: int = Field(..., description="Total size of all files in bytes")
    docling_size_bytes: int = Field(..., description="Size of Docling-supported files")
    llamaindex_size_bytes: int = Field(..., description="Size of LlamaIndex-supported files")


class ScanDirectoryRequest(BaseModel):
    """Request model for directory scanning.

    Sprint 33 Feature 33.1: Directory Selector
    """

    path: str = Field(..., description="Path to the directory to scan")
    recursive: bool = Field(default=False, description="Whether to scan subdirectories")


class ScanDirectoryResponse(BaseModel):
    """Response model for directory scanning.

    Sprint 33 Feature 33.1: Directory Selector
    """

    path: str = Field(..., description="Scanned directory path")
    recursive: bool = Field(..., description="Whether scan was recursive")
    files: list[FileInfo] = Field(..., description="List of files found")
    statistics: DirectoryScanStatistics = Field(..., description="Aggregated statistics")


@router.post(
    "/indexing/scan-directory",
    response_model=ScanDirectoryResponse,
    summary="Scan directory for indexable files",
    description="Scans a directory and returns a list of files with their support status (Docling/LlamaIndex/unsupported).",
)
async def scan_directory(request: ScanDirectoryRequest) -> ScanDirectoryResponse:
    """Scan a directory for files that can be indexed.

    **Sprint 33 Feature 33.1: Directory Selector**

    Scans the specified directory and categorizes files by their parser support:
    - **Docling** (dark green): GPU-accelerated OCR, optimal for PDF, DOCX, PPTX, XLSX, PNG, JPG
    - **LlamaIndex** (light green): Fallback parser for TXT, MD, HTML, JSON, CSV, RTF
    - **Unsupported** (red): Files that cannot be indexed (EXE, ZIP, MP4, etc.)

    **Supported Formats (27 total - Sprint 33 update):**
    - Docling (14): .pdf, .docx, .pptx, .xlsx, .png, .jpg, .jpeg, .tiff, .bmp, .html, .xml, .json, .csv, .ipynb
    - LlamaIndex exclusive (9): .epub, .rtf, .tex, .md, .rst, .adoc, .org, .odt, .msg
    - Shared (4): .txt, .htm, .mhtml, .eml

    **NOT Supported (Legacy Office - require conversion):**
    - .doc → convert to .docx
    - .xls → convert to .xlsx
    - .ppt → convert to .pptx

    **Example Request:**
    ```json
    {
      "path": "C:/data/documents",
      "recursive": true
    }
    ```

    **Example Response:**
    ```json
    {
      "path": "C:/data/documents",
      "recursive": true,
      "files": [
        {
          "file_path": "C:/data/documents/report.pdf",
          "file_name": "report.pdf",
          "file_extension": ".pdf",
          "file_size_bytes": 2457600,
          "parser_type": "docling",
          "is_supported": true
        }
      ],
      "statistics": {
        "total": 23,
        "docling_supported": 15,
        "llamaindex_supported": 6,
        "unsupported": 2,
        "total_size_bytes": 45678900,
        "docling_size_bytes": 35000000,
        "llamaindex_size_bytes": 10000000
      }
    }
    ```

    Args:
        request: Directory path and recursive flag

    Returns:
        ScanDirectoryResponse with file list and statistics

    Raises:
        HTTPException: If directory does not exist or is not readable
    """
    # Import format definitions (lazy import to avoid circular dependencies)
    from src.components.ingestion.format_router import (
        DOCLING_FORMATS,
        LEGACY_UNSUPPORTED,
        LLAMAINDEX_EXCLUSIVE,
        SHARED_FORMATS,
    )

    dir_path = Path(request.path)

    # Validate directory exists
    if not dir_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Directory does not exist: {request.path}",
        )

    if not dir_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a directory: {request.path}",
        )

    logger.info(
        "scan_directory_started",
        path=str(dir_path),
        recursive=request.recursive,
        feature="sprint_33_feature_33.1",
    )

    try:
        # Scan directory for files
        files: list[FileInfo] = []
        stats = {
            "total": 0,
            "docling_supported": 0,
            "llamaindex_supported": 0,
            "unsupported": 0,
            "total_size_bytes": 0,
            "docling_size_bytes": 0,
            "llamaindex_size_bytes": 0,
        }

        # Get file iterator based on recursive flag
        file_iterator = dir_path.rglob("*") if request.recursive else dir_path.glob("*")

        for file_path in file_iterator:
            # Skip directories
            if not file_path.is_file():
                continue

            file_extension = file_path.suffix.lower()
            file_size = file_path.stat().st_size

            # Determine parser type
            # Sprint 33: Check legacy formats FIRST (before LLAMAINDEX_EXCLUSIVE check)
            if file_extension in LEGACY_UNSUPPORTED:
                # Legacy Office formats - explicitly unsupported
                parser_type = "unsupported"
                is_supported = False
                stats["unsupported"] += 1
            elif file_extension in DOCLING_FORMATS:
                parser_type = "docling"
                is_supported = True
                stats["docling_supported"] += 1
                stats["docling_size_bytes"] += file_size
            elif file_extension in LLAMAINDEX_EXCLUSIVE:
                parser_type = "llamaindex"
                is_supported = True
                stats["llamaindex_supported"] += 1
                stats["llamaindex_size_bytes"] += file_size
            elif file_extension in SHARED_FORMATS:
                # Shared formats use Docling by default
                parser_type = "docling"
                is_supported = True
                stats["docling_supported"] += 1
                stats["docling_size_bytes"] += file_size
            else:
                parser_type = "unsupported"
                is_supported = False
                stats["unsupported"] += 1

            stats["total"] += 1
            stats["total_size_bytes"] += file_size

            files.append(
                FileInfo(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    file_extension=file_extension,
                    file_size_bytes=file_size,
                    parser_type=parser_type,
                    is_supported=is_supported,
                )
            )

        # Sort files: supported first (docling, then llamaindex), then unsupported
        parser_priority = {"docling": 0, "llamaindex": 1, "unsupported": 2}
        files.sort(key=lambda f: (parser_priority.get(f.parser_type, 3), f.file_name.lower()))

        logger.info(
            "scan_directory_completed",
            path=str(dir_path),
            total_files=stats["total"],
            docling_files=stats["docling_supported"],
            llamaindex_files=stats["llamaindex_supported"],
            unsupported_files=stats["unsupported"],
        )

        return ScanDirectoryResponse(
            path=str(dir_path),
            recursive=request.recursive,
            files=files,
            statistics=DirectoryScanStatistics(**stats),
        )

    except PermissionError as e:
        logger.error("scan_directory_permission_error", path=str(dir_path), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: Cannot read directory {request.path}",
        ) from e

    except Exception as e:
        logger.error("scan_directory_failed", path=str(dir_path), error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan directory: {str(e)}",
        ) from e


# ============================================================================
# Sprint 33: Job Tracking API (Feature 33.7)
# ============================================================================


class IngestionJobResponse(BaseModel):
    """Response model for ingestion job details.

    Sprint 33 Feature 33.7: Persistent Job Tracking
    """

    id: str = Field(..., description="Job ID")
    started_at: str = Field(..., description="Job start timestamp (ISO 8601)")
    completed_at: str | None = Field(None, description="Job completion timestamp (ISO 8601)")
    status: Literal["running", "completed", "failed", "cancelled"] = Field(
        ..., description="Job status"
    )
    directory_path: str = Field(..., description="Directory being indexed")
    recursive: bool = Field(..., description="Whether scan is recursive")
    total_files: int = Field(..., description="Total number of files")
    processed_files: int = Field(..., description="Number of files processed")
    total_errors: int = Field(..., description="Total error count")
    total_warnings: int = Field(..., description="Total warning count")
    config: dict | None = Field(None, description="Job configuration metadata")


class IngestionEventResponse(BaseModel):
    """Response model for ingestion events.

    Sprint 33 Feature 33.7: Event Logging
    """

    id: int = Field(..., description="Event ID")
    job_id: str = Field(..., description="Job ID")
    timestamp: str = Field(..., description="Event timestamp (ISO 8601)")
    level: Literal["INFO", "DEBUG", "WARN", "ERROR"] = Field(..., description="Event level")
    phase: str | None = Field(None, description="Pipeline phase")
    file_name: str | None = Field(None, description="File name")
    page_number: int | None = Field(None, description="Page number")
    chunk_id: str | None = Field(None, description="Chunk ID")
    message: str = Field(..., description="Event message")
    details: dict | None = Field(None, description="Additional details")


class IngestionFileResponse(BaseModel):
    """Response model for ingestion file details.

    Sprint 33 Feature 33.7: File-Level Tracking
    """

    id: int = Field(..., description="File record ID")
    job_id: str = Field(..., description="Job ID")
    file_path: str = Field(..., description="Full file path")
    file_name: str = Field(..., description="File name")
    file_type: str = Field(..., description="File extension")
    file_size_bytes: int | None = Field(None, description="File size in bytes")
    parser_used: str | None = Field(None, description="Parser type (docling/llamaindex)")
    status: Literal["pending", "processing", "completed", "failed", "skipped"] = Field(
        ..., description="File status"
    )
    pages_total: int | None = Field(None, description="Total pages")
    pages_processed: int = Field(..., description="Pages processed")
    chunks_created: int = Field(..., description="Chunks created")
    entities_extracted: int = Field(..., description="Entities extracted")
    relations_extracted: int = Field(..., description="Relations extracted")
    vlm_images_total: int = Field(..., description="Total VLM images")
    vlm_images_processed: int = Field(..., description="VLM images processed")
    processing_time_ms: int | None = Field(None, description="Processing time in milliseconds")
    error_message: str | None = Field(None, description="Error message if failed")
    started_at: str | None = Field(None, description="File processing start timestamp")
    completed_at: str | None = Field(None, description="File processing completion timestamp")


@router.get("/ingestion/jobs", response_model=list[IngestionJobResponse])
async def list_ingestion_jobs(
    status_filter: Literal["running", "completed", "failed", "cancelled"] | None = Query(
        None, alias="status", description="Filter by job status"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[IngestionJobResponse]:
    """List all ingestion jobs with optional filtering.

    **Sprint 33 Feature 33.7: Job Tracking API**

    Returns list of ingestion jobs sorted by start time (newest first).
    Supports filtering by status and pagination.

    **Example Request:**
    ```bash
    # Get all running jobs
    curl "http://localhost:8000/api/v1/admin/ingestion/jobs?status=running"

    # Get last 10 completed jobs
    curl "http://localhost:8000/api/v1/admin/ingestion/jobs?status=completed&limit=10"
    ```

    **Example Response:**
    ```json
    [
      {
        "id": "job_2025-11-27_123456",
        "started_at": "2025-11-27T12:34:56",
        "completed_at": "2025-11-27T12:45:00",
        "status": "completed",
        "directory_path": "/data/documents",
        "recursive": true,
        "total_files": 10,
        "processed_files": 10,
        "total_errors": 0,
        "total_warnings": 2,
        "config": {"vlm_enabled": true}
      }
    ]
    ```

    Args:
        status_filter: Filter by status (optional)
        limit: Maximum results (default 100)
        offset: Pagination offset (default 0)

    Returns:
        List of IngestionJobResponse

    Raises:
        HTTPException: If database query fails
    """
    from src.components.ingestion.job_tracker import get_job_tracker

    try:
        tracker = get_job_tracker()
        jobs = await tracker.get_jobs(status=status_filter, limit=limit, offset=offset)

        return [IngestionJobResponse(**job) for job in jobs]

    except Exception as e:
        logger.error("list_jobs_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list ingestion jobs: {str(e)}",
        ) from e


@router.get("/ingestion/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(job_id: str) -> IngestionJobResponse:
    """Get ingestion job details by ID.

    **Sprint 33 Feature 33.7: Job Tracking API**

    Returns detailed information about a specific ingestion job,
    including configuration, file counts, and error statistics.

    **Example Request:**
    ```bash
    curl "http://localhost:8000/api/v1/admin/ingestion/jobs/job_2025-11-27_123456"
    ```

    **Example Response:**
    ```json
    {
      "id": "job_2025-11-27_123456",
      "started_at": "2025-11-27T12:34:56",
      "completed_at": "2025-11-27T12:45:00",
      "status": "completed",
      "directory_path": "/data/documents",
      "recursive": true,
      "total_files": 10,
      "processed_files": 10,
      "total_errors": 0,
      "total_warnings": 2,
      "config": {"vlm_enabled": true}
    }
    ```

    Args:
        job_id: Job ID

    Returns:
        IngestionJobResponse

    Raises:
        HTTPException: If job not found or database query fails
    """
    from src.components.ingestion.job_tracker import get_job_tracker

    try:
        tracker = get_job_tracker()
        job = await tracker.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}",
            )

        return IngestionJobResponse(**job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_job_failed", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {str(e)}",
        ) from e


@router.get("/ingestion/jobs/{job_id}/events", response_model=list[IngestionEventResponse])
async def get_job_events(
    job_id: str,
    level_filter: Literal["INFO", "DEBUG", "WARN", "ERROR"] | None = Query(
        None, alias="level", description="Filter by event level"
    ),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of events"),
) -> list[IngestionEventResponse]:
    """Get ingestion events for job.

    **Sprint 33 Feature 33.7: Event Logging API**

    Returns event log for specific job, sorted chronologically.
    Useful for debugging and replaying ingestion pipeline execution.

    **Example Request:**
    ```bash
    # Get all events
    curl "http://localhost:8000/api/v1/admin/ingestion/jobs/job_123/events"

    # Get only errors
    curl "http://localhost:8000/api/v1/admin/ingestion/jobs/job_123/events?level=ERROR"
    ```

    **Example Response:**
    ```json
    [
      {
        "id": 1,
        "job_id": "job_123",
        "timestamp": "2025-11-27T12:35:00",
        "level": "INFO",
        "phase": "parsing",
        "file_name": "report.pdf",
        "page_number": null,
        "chunk_id": null,
        "message": "Parsing started",
        "details": {"parser": "docling"}
      }
    ]
    ```

    Args:
        job_id: Job ID
        level_filter: Filter by level (optional)
        limit: Maximum events (default 1000)

    Returns:
        List of IngestionEventResponse

    Raises:
        HTTPException: If database query fails
    """
    from src.components.ingestion.job_tracker import get_job_tracker

    try:
        tracker = get_job_tracker()
        events = await tracker.get_events(job_id, level=level_filter, limit=limit)

        return [IngestionEventResponse(**event) for event in events]

    except Exception as e:
        logger.error("get_events_failed", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get events: {str(e)}",
        ) from e


@router.get("/ingestion/jobs/{job_id}/errors", response_model=list[IngestionEventResponse])
async def get_job_errors(job_id: str) -> list[IngestionEventResponse]:
    """Get only ERROR-level events for job.

    **Sprint 33 Feature 33.7: Error Logging API**

    Convenience endpoint that returns only ERROR events for debugging.

    **Example Request:**
    ```bash
    curl "http://localhost:8000/api/v1/admin/ingestion/jobs/job_123/errors"
    ```

    **Example Response:**
    ```json
    [
      {
        "id": 5,
        "job_id": "job_123",
        "timestamp": "2025-11-27T12:40:00",
        "level": "ERROR",
        "phase": "parsing",
        "file_name": "corrupted.pdf",
        "page_number": null,
        "chunk_id": null,
        "message": "Parsing failed: Invalid PDF structure",
        "details": {"error_code": "PDF_PARSE_ERROR"}
      }
    ]
    ```

    Args:
        job_id: Job ID

    Returns:
        List of ERROR-level IngestionEventResponse

    Raises:
        HTTPException: If database query fails
    """
    from src.components.ingestion.job_tracker import get_job_tracker

    try:
        tracker = get_job_tracker()
        errors = await tracker.get_errors(job_id)

        return [IngestionEventResponse(**error) for error in errors]

    except Exception as e:
        logger.error("get_errors_failed", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get errors: {str(e)}",
        ) from e


@router.post("/ingestion/jobs/{job_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_ingestion_job(job_id: str) -> dict:
    """Cancel running ingestion job.

    **Sprint 33 Feature 33.7: Job Cancellation API**

    Marks job as cancelled. Note: This only updates database status,
    actual cancellation of running tasks requires implementation in orchestrator.

    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/admin/ingestion/jobs/job_123/cancel"
    ```

    **Example Response:**
    ```json
    {
      "message": "Job cancelled successfully",
      "job_id": "job_123"
    }
    ```

    Args:
        job_id: Job ID to cancel

    Returns:
        Success message

    Raises:
        HTTPException: If job not found or already completed
    """
    from src.components.ingestion.job_tracker import get_job_tracker

    try:
        tracker = get_job_tracker()

        # Check job exists and is running
        job = await tracker.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}",
            )

        if job["status"] != "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {job['status']}",
            )

        # Update status to cancelled
        await tracker.update_job_status(job_id, "cancelled")

        logger.info("job_cancelled", job_id=job_id)

        return {"message": "Job cancelled successfully", "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("cancel_job_failed", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}",
        ) from e


@router.delete("/ingestion/jobs/{job_id}", status_code=status.HTTP_200_OK)
async def delete_ingestion_job(job_id: str) -> dict:
    """Delete ingestion job and all associated data.

    **Sprint 33 Feature 33.7: Job Deletion API**

    Deletes job from database including all events and file records (CASCADE).
    Use with caution - this operation is irreversible.

    **Example Request:**
    ```bash
    curl -X DELETE "http://localhost:8000/api/v1/admin/ingestion/jobs/job_123"
    ```

    **Example Response:**
    ```json
    {
      "message": "Job deleted successfully",
      "job_id": "job_123"
    }
    ```

    Args:
        job_id: Job ID to delete

    Returns:
        Success message

    Raises:
        HTTPException: If job not found or database operation fails
    """
    from src.components.ingestion.job_tracker import get_job_tracker

    try:
        tracker = get_job_tracker()

        # Check job exists
        job = await tracker.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}",
            )

        # Delete job (CASCADE deletes events and files)
        import sqlite3

        def delete_job(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ingestion_jobs WHERE id = ?", (job_id,))
            conn.commit()

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: delete_job(sqlite3.connect(tracker.db_path, check_same_thread=False))
        )

        logger.info("job_deleted", job_id=job_id)

        return {"message": "Job deleted successfully", "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_job_failed", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}",
        ) from e


@router.get("/ingestion/jobs/{job_id}/progress")
async def stream_pipeline_progress(
    job_id: str,
    request: Request,
) -> StreamingResponse:
    """Stream pipeline progress via SSE.

    **Sprint 37 Feature 37.5: Backend SSE Streaming Updates**

    Returns Server-Sent Events with real-time pipeline progress including:
    - Stage progress (parsing, vlm, chunking, embedding, extraction)
    - Worker pool status (active workers, queue depth)
    - Live metrics (entities, relations, Neo4j/Qdrant writes)
    - Timing (elapsed, estimated remaining)

    **Event Format:**
    ```
    event: pipeline_progress
    data: {"document_id": "...", "stages": {...}, "worker_pool": {...}, ...}

    event: complete
    data: {}
    ```

    **Example Request:**
    ```bash
    curl -N "http://localhost:8000/api/v1/admin/ingestion/jobs/job_123/progress" \
      -H "Accept: text/event-stream"
    ```

    **Frontend Integration:**
    ```typescript
    const eventSource = new EventSource(
      `/api/v1/admin/ingestion/jobs/${jobId}/progress`
    );

    eventSource.addEventListener('pipeline_progress', (event) => {
      const data: PipelineProgressData = JSON.parse(event.data);
      // Update UI with progress data
    });

    eventSource.addEventListener('complete', () => {
      eventSource.close();
    });
    ```

    Args:
        job_id: Job ID to stream progress for
        request: FastAPI request object (for disconnect detection)

    Returns:
        StreamingResponse with text/event-stream content type

    Raises:
        HTTPException: If job not found in progress manager
    """
    import json

    from src.components.ingestion.progress_manager import get_progress_manager

    async def event_generator():
        """Generate SSE events for pipeline progress."""
        progress_manager = get_progress_manager()

        # Check if job exists
        initial_event = progress_manager.get_sse_event(job_id)
        if not initial_event:
            # Job not found in progress manager
            # Return error event and close stream
            error_event = {
                "type": "error",
                "data": {
                    "message": f"Job not found: {job_id}",
                    "job_id": job_id,
                },
            }
            yield "event: error\n"
            yield f"data: {json.dumps(error_event['data'])}\n\n"
            return

        logger.info(
            "sse_stream_started",
            job_id=job_id,
            client_ip=request.client.host if request.client else "unknown",
        )

        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("sse_client_disconnected", job_id=job_id)
                    break

                # Get current progress
                event = progress_manager.get_sse_event(job_id)

                if event:
                    # Format as SSE (event type + data)
                    yield f"event: {event['type']}\n"
                    yield f"data: {json.dumps(event['data'])}\n\n"

                    # Check if complete (100% progress)
                    overall_progress = event["data"].get("overall_progress_percent", 0)
                    if overall_progress >= 100:
                        logger.info(
                            "sse_stream_completed",
                            job_id=job_id,
                            overall_progress=overall_progress,
                        )
                        # Send complete event
                        yield "event: complete\n"
                        yield "data: {}\n\n"
                        break

                # Throttle updates (~500ms interval)
                # Progress manager already throttles at 500ms, but we add a small
                # sleep to prevent tight loop when no updates available
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("sse_stream_cancelled", job_id=job_id)
            raise
        except Exception as e:
            logger.error("sse_stream_error", job_id=job_id, error=str(e), exc_info=True)
            # Send error event
            error_data = {
                "message": f"Stream error: {str(e)}",
                "job_id": job_id,
            }
            yield "event: error\n"
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",  # CORS for SSE
        },
    )


# ============================================================================
# Sprint 37 Feature 37.7: Pipeline Worker Pool Configuration
# ============================================================================

REDIS_KEY_PIPELINE_CONFIG = "admin:pipeline_config"


class PipelineConfigSchema(BaseModel):
    """Pipeline configuration schema for worker pool settings.

    Sprint 37 Feature 37.7: Admin UI for Worker Pool Configuration

    This schema defines all configurable parameters for the parallel
    ingestion pipeline worker pools, including:
    - VLM Workers (GPU-bound, 1-2 workers)
    - Embedding Workers (1-4 workers)
    - Extraction Workers (LLM calls, 1-8 workers)
    - Resource limits and timeouts

    All fields have Pydantic validation ranges matching frontend sliders.
    """

    # Document Processing
    parallel_documents: int = Field(
        default=2, ge=1, le=4, description="Number of documents to process in parallel"
    )
    max_queue_size: int = Field(
        default=10, ge=5, le=50, description="Maximum number of chunks in processing queue"
    )

    # VLM Workers (GPU-bound)
    vlm_workers: int = Field(
        default=1, ge=1, le=2, description="Number of parallel VLM workers (GPU memory limited)"
    )
    vlm_batch_size: int = Field(
        default=4, ge=1, le=8, description="Number of images processed per batch"
    )
    vlm_timeout: int = Field(
        default=180, ge=60, le=300, description="Timeout for VLM processing per image (seconds)"
    )

    # Embedding Workers
    embedding_workers: int = Field(
        default=2, ge=1, le=4, description="Number of parallel embedding workers"
    )
    embedding_batch_size: int = Field(
        default=8, ge=4, le=32, description="Number of chunks embedded per batch"
    )
    embedding_timeout: int = Field(
        default=60, ge=30, le=120, description="Timeout for embedding generation (seconds)"
    )

    # Extraction Workers (LLM calls)
    extraction_workers: int = Field(
        default=4, ge=1, le=8, description="Number of parallel entity/relation extraction workers"
    )
    extraction_timeout: int = Field(
        default=120, ge=60, le=300, description="Timeout for LLM extraction calls (seconds)"
    )
    extraction_max_retries: int = Field(
        default=2, ge=0, le=3, description="Maximum retry attempts for failed extractions"
    )

    # Resource Limits
    max_concurrent_llm: int = Field(
        default=8, ge=4, le=16, description="Global limit for concurrent LLM API calls"
    )
    max_vram_mb: int = Field(
        default=5500, ge=4000, le=8000, description="Maximum VRAM allocation for VLM workers (MB)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "parallel_documents": 2,
                "max_queue_size": 10,
                "vlm_workers": 1,
                "vlm_batch_size": 4,
                "vlm_timeout": 180,
                "embedding_workers": 2,
                "embedding_batch_size": 8,
                "embedding_timeout": 60,
                "extraction_workers": 4,
                "extraction_timeout": 120,
                "extraction_max_retries": 2,
                "max_concurrent_llm": 8,
                "max_vram_mb": 5500,
            }
        }
    }


@router.get("/pipeline/config", response_model=PipelineConfigSchema)
async def get_pipeline_config() -> PipelineConfigSchema:
    """Get current pipeline worker pool configuration.

    **Sprint 37 Feature 37.7: Pipeline Configuration API**

    Loads configuration from Redis or returns defaults if not set.
    Configuration controls parallel worker pools for VLM, Embedding,
    and Extraction operations.

    **Example Request:**
    ```bash
    curl "http://localhost:8000/api/v1/admin/pipeline/config"
    ```

    **Example Response:**
    ```json
    {
      "parallel_documents": 2,
      "max_queue_size": 10,
      "vlm_workers": 1,
      "vlm_batch_size": 4,
      "vlm_timeout": 180,
      "embedding_workers": 2,
      "embedding_batch_size": 8,
      "embedding_timeout": 60,
      "extraction_workers": 4,
      "extraction_timeout": 120,
      "extraction_max_retries": 2,
      "max_concurrent_llm": 8,
      "max_vram_mb": 5500
    }
    ```

    Returns:
        Current pipeline configuration (from Redis or defaults)
    """
    import json

    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        redis_client = await redis_memory.client

        # Try to load from Redis
        config_json = await redis_client.get(REDIS_KEY_PIPELINE_CONFIG)

        if config_json:
            # Redis returns bytes, decode to string
            config_str = (
                config_json.decode("utf-8") if isinstance(config_json, bytes) else config_json
            )
            config_dict = json.loads(config_str)
            logger.info("pipeline_config_loaded_from_redis", config=config_dict)
            return PipelineConfigSchema(**config_dict)

        # Return defaults if not in Redis
        logger.info("pipeline_config_using_defaults")
        return PipelineConfigSchema()

    except Exception as e:
        logger.warning("failed_to_load_pipeline_config", error=str(e))
        # Return defaults on error
        return PipelineConfigSchema()


@router.post("/pipeline/config", response_model=PipelineConfigSchema)
async def update_pipeline_config(config: PipelineConfigSchema) -> PipelineConfigSchema:
    """Update pipeline worker pool configuration.

    **Sprint 37 Feature 37.7: Pipeline Configuration API**

    Validates and persists configuration to Redis.
    Configuration is immediately active for new indexing jobs.

    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/admin/pipeline/config" \\
      -H "Content-Type: application/json" \\
      -d '{
        "parallel_documents": 3,
        "extraction_workers": 6,
        "max_concurrent_llm": 12
      }'
    ```

    **Example Response:**
    ```json
    {
      "parallel_documents": 3,
      "max_queue_size": 10,
      "vlm_workers": 1,
      "vlm_batch_size": 4,
      "vlm_timeout": 180,
      "embedding_workers": 2,
      "embedding_batch_size": 8,
      "embedding_timeout": 60,
      "extraction_workers": 6,
      "extraction_timeout": 120,
      "extraction_max_retries": 2,
      "max_concurrent_llm": 12,
      "max_vram_mb": 5500
    }
    ```

    Args:
        config: Pipeline configuration to save

    Returns:
        Saved configuration (validated and persisted)

    Raises:
        HTTPException: If validation fails or Redis save fails
    """

    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        redis_client = await redis_memory.client

        # Save to Redis
        config_json = config.model_dump_json()
        await redis_client.set(REDIS_KEY_PIPELINE_CONFIG, config_json)

        logger.info("pipeline_config_saved", config=config.model_dump())

        return config

    except Exception as e:
        logger.error("failed_to_save_pipeline_config", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save pipeline configuration: {str(e)}",
        ) from e


@router.post("/pipeline/config/preset/{preset_name}", response_model=PipelineConfigSchema)
async def apply_config_preset(
    preset_name: Literal["conservative", "balanced", "aggressive"]
) -> PipelineConfigSchema:
    """Apply a predefined configuration preset.

    **Sprint 37 Feature 37.7: Configuration Presets**

    Applies one of three predefined configurations:
    - **conservative**: Minimal resources, stable (1 parallel doc, 2 extraction workers)
    - **balanced**: Default, recommended (2 parallel docs, 4 extraction workers)
    - **aggressive**: Maximum performance (3 parallel docs, 6 extraction workers)

    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/admin/pipeline/config/preset/aggressive"
    ```

    **Example Response:**
    ```json
    {
      "parallel_documents": 3,
      "extraction_workers": 6,
      "embedding_workers": 3,
      "vlm_workers": 1,
      "max_concurrent_llm": 12,
      "vlm_batch_size": 6,
      "embedding_batch_size": 16,
      ...
    }
    ```

    Args:
        preset_name: Preset to apply (conservative, balanced, aggressive)

    Returns:
        Applied configuration

    Raises:
        HTTPException: If preset is invalid or save fails
    """

    presets = {
        "conservative": PipelineConfigSchema(
            parallel_documents=1,
            extraction_workers=2,
            embedding_workers=1,
            vlm_workers=1,
            max_concurrent_llm=4,
            vlm_batch_size=2,
            embedding_batch_size=4,
        ),
        "balanced": PipelineConfigSchema(),  # defaults
        "aggressive": PipelineConfigSchema(
            parallel_documents=3,
            extraction_workers=6,
            embedding_workers=3,
            vlm_workers=1,
            max_concurrent_llm=12,
            vlm_batch_size=6,
            embedding_batch_size=16,
        ),
    }

    config = presets.get(preset_name)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid preset: {preset_name}. Must be one of: conservative, balanced, aggressive",
        )

    # Save the preset
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        redis_client = await redis_memory.client

        config_json = config.model_dump_json()
        await redis_client.set(REDIS_KEY_PIPELINE_CONFIG, config_json)

        logger.info(
            "pipeline_config_preset_applied", preset=preset_name, config=config.model_dump()
        )

        return config

    except Exception as e:
        logger.error("failed_to_apply_preset", preset=preset_name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply preset: {str(e)}",
        ) from e


# ============================================================================
# Sprint 49 Feature 49.6: Index Consistency Validation
# ============================================================================


@router.get("/validation/index-consistency")
async def validate_index_consistency(
    include_chunk_check: bool = Query(True, description="Whether to check orphaned chunks"),
    max_issues: int = Query(1000, description="Maximum number of issues to report"),
) -> dict:
    """Validate consistency across Qdrant, Neo4j, and source chunks.

    Sprint 49 Feature 49.6: Index Consistency Validation (TD-048)

    This endpoint validates the consistency between:
    - Qdrant vector store (chunks)
    - Neo4j knowledge graph (entities, relationships)
    - BM25 keyword index (corpus)

    It detects:
    - Orphaned entities (entities without source chunks)
    - Orphaned chunks (chunks with no entities extracted)
    - Missing source_chunk_id properties on relationships

    Returns a detailed validation report with consistency score (0.0 to 1.0).

    Args:
        include_chunk_check: Whether to check for orphaned chunks (slower)
        max_issues: Maximum number of issues to report (prevents huge reports)

    Returns:
        ValidationReport with:
        - consistency_score: float (0.0 = bad, 1.0 = perfect)
        - total_chunks: int (total chunks in Qdrant)
        - total_entities: int (total entities in Neo4j)
        - total_relationships: int (total relationships in Neo4j)
        - orphaned_entities_count: int
        - orphaned_chunks_count: int
        - missing_source_chunk_id_count: int
        - issues: List[ValidationIssue] (detailed issue list)
        - execution_time_ms: float
        - timestamp: str (ISO 8601)

    Example:
        ```
        GET /api/v1/admin/validation/index-consistency?include_chunk_check=true&max_issues=100

        Response:
        {
            "consistency_score": 0.98,
            "total_chunks": 10234,
            "total_entities": 1353,
            "total_relationships": 2289,
            "orphaned_entities_count": 0,
            "orphaned_chunks_count": 12,
            "missing_source_chunk_id_count": 0,
            "issues": [
                {
                    "issue_type": "orphaned_chunk",
                    "severity": "warning",
                    "chunk_id": "chunk_abc123...",
                    "message": "Chunk has no entities extracted",
                    "metadata": {...}
                },
                ...
            ],
            "execution_time_ms": 15234.5,
            "timestamp": "2025-12-16T10:30:00Z"
        }
        ```
    """
    try:
        from src.components.validation import validate_index_consistency as validate

        logger.info(
            "index_consistency_validation_requested",
            include_chunk_check=include_chunk_check,
            max_issues=max_issues,
        )

        # Run validation
        report = await validate(
            include_chunk_check=include_chunk_check,
            max_issues=max_issues,
        )

        logger.info(
            "index_consistency_validation_completed",
            consistency_score=report.consistency_score,
            total_chunks=report.total_chunks,
            total_entities=report.total_entities,
            orphaned_entities=report.orphaned_entities_count,
            orphaned_chunks=report.orphaned_chunks_count,
            execution_time_ms=report.execution_time_ms,
        )

        return report.to_dict()

    except Exception as e:
        logger.error(
            "index_consistency_validation_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate index consistency: {str(e)}",
        ) from e

