"""Admin API endpoints for re-indexing and maintenance operations.

Sprint 16 Feature 16.3: Unified Re-Indexing Pipeline with SSE progress tracking.
Sprint 31 Feature 31.10a: Cost API Backend Implementation
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Literal

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client.models import Distance

from src.api.models.cost_stats import BudgetStatus, CostHistory, CostStats, ModelCost, ProviderCost
from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.llm_proxy.cost_tracker import get_cost_tracker
from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings
from src.core.exceptions import VectorSearchError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# TD-41: Enhanced logging for debugging 404 issue
# FIX: Changed prefix from "/api/v1/admin" to "/admin" to match other routers
# The full path will be constructed in main.py: app.include_router(admin_router, prefix="/api/v1")
logger.info(
    "admin_router_initialized",
    prefix="/admin",
    tags=["admin"],
    note="Sprint 18 TD-41: Router prefix fixed - will be combined with /api/v1 in main.py",
)


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
            bm25_cache_path = Path("data/cache/bm25_model.pkl")
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
                    error_msg = result.get("error", "Unknown error")
                    logger.error("reindex_document_failed", document_path=doc_path, error=error_msg)

                    # Continue with remaining documents
                    message = f"FAILED: {Path(doc_path).name} - {error_msg}"
                    yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 30 + (completed_docs / total_docs) * 30, 'message': message, 'completed_documents': completed_docs, 'total_documents': total_docs})}\n\n"

            points_indexed = total_chunks
            message = (
                f"Indexed {points_indexed} chunks from {completed_docs} documents into Qdrant + Neo4j"
            )
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
# Sprint 17 Feature 17.6: Admin Statistics API
# ============================================================================


class SystemStats(BaseModel):
    """System statistics for admin dashboard.

    Sprint 17 Feature 17.6: Admin Statistics API
    """

    # Qdrant statistics
    qdrant_total_chunks: int = Field(..., description="Total chunks indexed in Qdrant")
    qdrant_collection_name: str = Field(..., description="Qdrant collection name")
    qdrant_vector_dimension: int = Field(..., description="Vector dimension (BGE-M3: 1024)")

    # BM25 statistics (if available)
    bm25_corpus_size: int | None = Field(None, description="BM25 corpus size (number of documents)")

    # Neo4j / LightRAG statistics
    neo4j_total_entities: int | None = Field(None, description="Total entities in Neo4j graph")
    neo4j_total_relations: int | None = Field(
        None, description="Total relationships in Neo4j graph"
    )
    neo4j_total_chunks: int | None = Field(None, description="Total chunks stored in Neo4j")

    # System metadata
    last_reindex_timestamp: str | None = Field(
        None, description="Timestamp of last re-indexing operation"
    )
    embedding_model: str = Field(..., description="Current embedding model name")

    # Additional stats
    total_conversations: int | None = Field(None, description="Total active conversations in Redis")


@router.get("/stats", response_model=SystemStats)
async def get_system_stats() -> SystemStats:
    """Get comprehensive system statistics for admin dashboard.

    Sprint 17 Feature 17.6: Admin Statistics API

    Returns statistics from:
    - Qdrant (vector database)
    - BM25 (keyword search corpus)
    - Neo4j/LightRAG (knowledge graph)
    - Redis (conversation storage)
    - System configuration

    **Example Response:**
    ```json
    {
      "qdrant_total_chunks": 1523,
      "qdrant_collection_name": "aegis_documents",
      "qdrant_vector_dimension": 1024,
      "bm25_corpus_size": 342,
      "neo4j_total_entities": 856,
      "neo4j_total_relations": 1204,
      "neo4j_total_chunks": 1523,
      "last_reindex_timestamp": "2025-10-29T10:30:00Z",
      "embedding_model": "BAAI/bge-m3",
      "total_conversations": 15
    }
    ```

    Returns:
        SystemStats with comprehensive system statistics

    Raises:
        HTTPException: If statistics retrieval fails
    """
    # TD-41: Enhanced logging for request tracking
    logger.info(
        "admin_stats_endpoint_called",
        endpoint="/api/v1/admin/stats",
        method="GET",
        note="Sprint 18 TD-41: Tracking stats request",
    )

    try:
        # TD-41: Log stats collection start
        logger.info("stats_collection_started", phase="initialization")

        # Qdrant statistics
        logger.info("stats_collection_phase", phase="qdrant", status="starting")
        qdrant_client = get_qdrant_client()
        embedding_service = get_embedding_service()
        collection_name = settings.qdrant_collection
        logger.info("qdrant_clients_initialized", collection=collection_name)

        try:
            collection_info = await qdrant_client.get_collection(collection_name)
            qdrant_total_chunks = collection_info.points_count
            logger.info(
                "qdrant_stats_retrieved", chunks=qdrant_total_chunks, collection=collection_name
            )
        except Exception as e:
            logger.warning("failed_to_get_qdrant_stats", error=str(e), exc_info=True)
            qdrant_total_chunks = 0

        # BM25 statistics (optional - requires BM25 manager)
        logger.info("stats_collection_phase", phase="bm25", status="starting")
        bm25_corpus_size = None
        try:
            from src.components.vector_search.bm25_manager import get_bm25_manager

            bm25_manager = get_bm25_manager()
            if hasattr(bm25_manager, "get_corpus_size"):
                bm25_corpus_size = bm25_manager.get_corpus_size()
                logger.info("bm25_stats_retrieved", corpus_size=bm25_corpus_size)
            else:
                logger.debug("bm25_manager_missing_get_corpus_size_method")
        except Exception as e:
            logger.debug("bm25_stats_unavailable", error=str(e))

        # Neo4j / LightRAG statistics
        logger.info("stats_collection_phase", phase="neo4j", status="starting")
        neo4j_total_entities = None
        neo4j_total_relations = None
        neo4j_total_chunks = None

        try:
            lightrag = await get_lightrag_wrapper_async()
            logger.info("lightrag_wrapper_initialized")

            # Query Neo4j for statistics
            query_entities = "MATCH (e:Entity) RETURN count(e) as count"
            query_relations = "MATCH ()-[r]->() RETURN count(r) as count"
            query_chunks = "MATCH (c:Chunk) RETURN count(c) as count"

            # Execute queries
            logger.info("executing_neo4j_query", query="entities")
            entities_result = await lightrag.graph_storage_cls.execute_query(query_entities)
            if entities_result and len(entities_result) > 0:
                neo4j_total_entities = entities_result[0].get("count", 0)
                logger.info("neo4j_entities_retrieved", count=neo4j_total_entities)

            logger.info("executing_neo4j_query", query="relations")
            relations_result = await lightrag.graph_storage_cls.execute_query(query_relations)
            if relations_result and len(relations_result) > 0:
                neo4j_total_relations = relations_result[0].get("count", 0)
                logger.info("neo4j_relations_retrieved", count=neo4j_total_relations)

            logger.info("executing_neo4j_query", query="chunks")
            chunks_result = await lightrag.graph_storage_cls.execute_query(query_chunks)
            if chunks_result and len(chunks_result) > 0:
                neo4j_total_chunks = chunks_result[0].get("count", 0)
                logger.info("neo4j_chunks_retrieved", count=neo4j_total_chunks)

        except Exception as e:
            logger.warning("failed_to_get_neo4j_stats", error=str(e), exc_info=True)

        # Redis conversation statistics
        logger.info("stats_collection_phase", phase="redis", status="starting")
        total_conversations = None
        try:
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client
            logger.info("redis_client_initialized")

            # Count conversation keys
            conversation_count = 0
            cursor = 0
            scan_iterations = 0
            while True:
                cursor, keys = await redis_client.scan(
                    cursor=cursor, match="conversation:*", count=100
                )
                conversation_count += len(keys)
                scan_iterations += 1
                if cursor == 0:
                    break

            total_conversations = conversation_count
            logger.info(
                "redis_stats_retrieved",
                conversations=total_conversations,
                scan_iterations=scan_iterations,
            )
        except Exception as e:
            logger.warning("failed_to_get_redis_stats", error=str(e), exc_info=True)

        # Last reindex timestamp (TODO: Implement persistent storage for this)
        # For now, return None - could be stored in Redis or a separate metadata store
        last_reindex_timestamp = None

        # TD-41: Log final stats assembly
        logger.info("stats_collection_phase", phase="assembly", status="starting")

        stats = SystemStats(
            qdrant_total_chunks=qdrant_total_chunks,
            qdrant_collection_name=collection_name,
            qdrant_vector_dimension=embedding_service.embedding_dim,
            bm25_corpus_size=bm25_corpus_size,
            neo4j_total_entities=neo4j_total_entities,
            neo4j_total_relations=neo4j_total_relations,
            neo4j_total_chunks=neo4j_total_chunks,
            last_reindex_timestamp=last_reindex_timestamp,
            embedding_model=embedding_service.model_name,
            total_conversations=total_conversations,
        )

        logger.info(
            "admin_stats_successfully_retrieved",
            stats=stats.model_dump(),
            note="Sprint 18 TD-41: Stats successfully assembled and ready to return",
        )

        return stats

    except Exception as e:
        logger.error(
            "admin_stats_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
            note="Sprint 18 TD-41: Stats retrieval failed with exception",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system statistics: {str(e)}",
        ) from e


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
            bm25_cache_path = Path("data/cache/bm25_model.pkl")
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
            total_chunks = 0
            total_vlm_images = 0
            total_errors = 0

            yield f"data: {json.dumps({'status': 'ingestion', 'progress': 0.2, 'message': f'Starting VLM batch ingestion (batch_id={batch_id})...'})}\n\n"

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

                    yield f"data: {json.dumps({
                        'status': 'ingestion',
                        'progress': overall_progress,
                        'message': f'Processed {Path(doc_path).name}',
                        'document_id': doc_id,
                        'document_path': doc_path,
                        'completed_documents': completed_docs,
                        'total_documents': total_docs,
                        'batch_progress': batch_progress,
                        'chunks': chunk_count,
                        'vlm_images': vlm_count,
                        'errors': error_count,
                        'success': True,
                    })}\n\n"

                    logger.info(
                        "vlm_document_indexed",
                        document_id=doc_id,
                        chunks=chunk_count,
                        vlm_images=vlm_count,
                        batch_progress=batch_progress,
                    )
                else:
                    # Document failed
                    error_msg = result.get("error", "Unknown error")
                    total_errors += 1

                    yield f"data: {json.dumps({
                        'status': 'ingestion',
                        'progress': overall_progress,
                        'message': f'FAILED: {Path(doc_path).name}',
                        'document_id': doc_id,
                        'document_path': doc_path,
                        'completed_documents': completed_docs,
                        'total_documents': total_docs,
                        'batch_progress': batch_progress,
                        'success': False,
                        'error': error_msg,
                    })}\n\n"

                    logger.error(
                        "vlm_document_failed",
                        document_id=doc_id,
                        error=error_msg,
                    )

            # Phase 4: Validation
            yield f"data: {json.dumps({'status': 'validation', 'progress': 0.98, 'message': 'Validating indexes...'})}\n\n"

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

            # Completion
            total_time = time.time() - start_time

            yield f"data: {json.dumps({
                'status': 'completed',
                'progress': 1.0,
                'message': f'VLM re-indexing completed in {total_time:.1f}s',
                'total_documents': total_docs,
                'completed_documents': completed_docs,
                'total_chunks': total_chunks,
                'total_vlm_images': total_vlm_images,
                'total_errors': total_errors,
                'qdrant_points': qdrant_points,
                'neo4j_entities': neo4j_entities,
                'neo4j_relations': neo4j_relations,
                'duration_seconds': total_time,
            })}\n\n"

            logger.info(
                "vlm_reindex_completed",
                total_docs=total_docs,
                total_chunks=total_chunks,
                total_vlm_images=total_vlm_images,
                total_errors=total_errors,
                duration_seconds=total_time,
            )

        except Exception as e:
            logger.error("vlm_reindex_failed", error=str(e), exc_info=True)
            yield f"data: {json.dumps({'status': 'error', 'message': f'VLM re-indexing failed: {str(e)}'})}\n\n"

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
# Sprint 31 Feature 31.10a: Cost API Backend Implementation
# ============================================================================


@router.get("/costs/stats", response_model=CostStats)
async def get_cost_stats(
    time_range: Literal["7d", "30d", "all"] = Query(
        default="7d",
        description="Time range for cost statistics (7d=last 7 days, 30d=current month, all=all time)",
    )
) -> CostStats:
    """Get LLM cost statistics with budget tracking.

    **Sprint 31 Feature 31.10a: Cost Dashboard Backend**

    Returns comprehensive cost breakdown by provider, model, and budget status.
    Includes all LLM costs tracked by AegisLLMProxy via SQLite cost tracker.

    **Time Ranges:**
    - `7d`: Last 7 days (rolling window)
    - `30d`: Current month (from first day of month to now)
    - `all`: All time (entire cost tracking history)

    **Budget Status Thresholds:**
    - `ok`: <80% of budget used (green)
    - `warning`: 80-100% of budget used (yellow)
    - `critical`: >100% of budget used (red, over budget)

    **Provider Tracking:**
    - `local_ollama`: Always $0.00 (free local models)
    - `alibaba_cloud`: Qwen models (qwen3-vl, qwen-turbo, etc.)
    - `openai`: GPT models (if enabled)

    **Budget Configuration:**
    Budget limits are configured via environment variables:
    - `MONTHLY_BUDGET_ALIBABA_CLOUD`: Default $10.00/month
    - `MONTHLY_BUDGET_OPENAI`: Default $20.00/month

    **Example Response:**
    ```json
    {
      "total_cost_usd": 5.25,
      "total_tokens": 500000,
      "total_calls": 250,
      "avg_cost_per_call": 0.021,
      "by_provider": {
        "alibaba_cloud": {
          "cost_usd": 5.25,
          "tokens": 500000,
          "calls": 250,
          "avg_cost_per_call": 0.021
        }
      },
      "by_model": {
        "alibaba_cloud/qwen3-vl-30b": {
          "provider": "alibaba_cloud",
          "cost_usd": 3.50,
          "tokens": 300000,
          "calls": 150
        }
      },
      "budgets": {
        "alibaba_cloud": {
          "limit_usd": 10.0,
          "spent_usd": 5.25,
          "utilization_percent": 52.5,
          "status": "ok",
          "remaining_usd": 4.75
        }
      },
      "time_range": "7d"
    }
    ```

    Args:
        time_range: Time window for statistics (7d, 30d, all)

    Returns:
        CostStats: Comprehensive cost statistics

    Raises:
        HTTPException: If cost retrieval fails

    See Also:
        - GET /admin/costs/history: Daily cost history for charting
        - src/components/llm_proxy/cost_tracker.py: Cost tracking implementation
        - src/components/llm_proxy/aegis_llm_proxy.py: LLM proxy with cost tracking
    """
    try:
        tracker = get_cost_tracker()

        # Calculate time filter based on time_range
        start_date = None
        if time_range == "7d":
            start_date = (datetime.now() - timedelta(days=7)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif time_range == "30d":
            # Current month (from first day to now)
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get request stats from tracker
        # Note: CostTracker.get_request_stats expects days parameter, but we need custom date ranges
        # So we'll calculate directly from the database
        import sqlite3

        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()

            # Build WHERE clause
            conditions = []
            params = []
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date.isoformat())

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Aggregate by provider
            cursor.execute(
                f"""
                SELECT
                    provider,
                    SUM(cost_usd) as total_cost,
                    SUM(tokens_total) as total_tokens,
                    COUNT(*) as total_calls
                FROM llm_requests
                WHERE {where_clause}
                GROUP BY provider
            """,
                tuple(params),
            )

            provider_rows = cursor.fetchall()

            # Aggregate by model
            cursor.execute(
                f"""
                SELECT
                    provider,
                    model,
                    SUM(cost_usd) as total_cost,
                    SUM(tokens_total) as total_tokens,
                    COUNT(*) as total_calls
                FROM llm_requests
                WHERE {where_clause}
                GROUP BY provider, model
            """,
                tuple(params),
            )

            model_rows = cursor.fetchall()

        # Build provider cost breakdown
        by_provider: dict[str, ProviderCost] = {}
        for provider, cost, tokens, calls in provider_rows:
            avg_cost = cost / calls if calls > 0 else 0.0
            by_provider[provider] = ProviderCost(
                cost_usd=cost,
                tokens=tokens,
                calls=calls,
                avg_cost_per_call=avg_cost,
            )

        # Build model cost breakdown
        by_model: dict[str, ModelCost] = {}
        for provider, model, cost, tokens, calls in model_rows:
            model_key = f"{provider}/{model}"
            by_model[model_key] = ModelCost(
                provider=provider,
                cost_usd=cost,
                tokens=tokens,
                calls=calls,
            )

        # Calculate totals
        total_cost = sum(p.cost_usd for p in by_provider.values())
        total_tokens = sum(p.tokens for p in by_provider.values())
        total_calls = sum(p.calls for p in by_provider.values())
        avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0.0

        # Calculate budget status (only for current month)
        budgets: dict[str, BudgetStatus] = {}

        # Get current month spending for budget calculation
        current_month_spending = tracker.get_monthly_spending()

        # Ollama (always free)
        if "local_ollama" in by_provider:
            budgets["local_ollama"] = BudgetStatus(
                limit_usd=0.0,
                spent_usd=0.0,
                utilization_percent=0.0,
                status="ok",
                remaining_usd=0.0,
            )

        # Alibaba Cloud
        if "alibaba_cloud" in current_month_spending or "alibaba_cloud" in by_provider:
            alibaba_limit = float(settings.monthly_budget_alibaba_cloud or 10.0)
            alibaba_spent = current_month_spending.get("alibaba_cloud", 0.0)
            alibaba_util = (alibaba_spent / alibaba_limit * 100) if alibaba_limit > 0 else 0.0

            budgets["alibaba_cloud"] = BudgetStatus(
                limit_usd=alibaba_limit,
                spent_usd=alibaba_spent,
                utilization_percent=alibaba_util,
                status="ok" if alibaba_util < 80 else ("warning" if alibaba_util < 100 else "critical"),
                remaining_usd=max(0, alibaba_limit - alibaba_spent),
            )

        # OpenAI
        if "openai" in current_month_spending or "openai" in by_provider:
            openai_limit = float(settings.monthly_budget_openai or 20.0)
            openai_spent = current_month_spending.get("openai", 0.0)
            openai_util = (openai_spent / openai_limit * 100) if openai_limit > 0 else 0.0

            budgets["openai"] = BudgetStatus(
                limit_usd=openai_limit,
                spent_usd=openai_spent,
                utilization_percent=openai_util,
                status="ok" if openai_util < 80 else ("warning" if openai_util < 100 else "critical"),
                remaining_usd=max(0, openai_limit - openai_spent),
            )

        logger.info(
            "cost_stats_retrieved",
            time_range=time_range,
            total_cost=total_cost,
            total_calls=total_calls,
            providers=list(by_provider.keys()),
        )

        return CostStats(
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
            total_calls=total_calls,
            avg_cost_per_call=avg_cost_per_call,
            by_provider=by_provider,
            by_model=by_model,
            budgets=budgets,
            time_range=time_range,
        )

    except Exception as e:
        logger.error("cost_stats_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cost statistics: {str(e)}",
        ) from e


@router.get("/costs/history", response_model=List[CostHistory])
async def get_cost_history(
    time_range: Literal["7d", "30d", "all"] = Query(
        default="7d",
        description="Time range for cost history (7d=last 7 days, 30d=last 30 days, all=all time)",
    )
) -> List[CostHistory]:
    """Get historical cost data grouped by day for charting.

    **Sprint 31 Feature 31.10a: Cost Dashboard Backend**

    Returns daily aggregated cost data for time-series visualization.
    Used by frontend to render cost trend charts and budget burn-down graphs.

    **Time Ranges:**
    - `7d`: Last 7 days (7 data points)
    - `30d`: Last 30 days (up to 30 data points)
    - `all`: All time (daily aggregation since first tracked request)

    **Data Aggregation:**
    - Costs are grouped by date (YYYY-MM-DD)
    - Tokens include both input and output
    - Calls are the number of LLM requests per day
    - Results are sorted chronologically (oldest to newest)

    **Example Response:**
    ```json
    [
      {
        "date": "2025-11-14",
        "cost_usd": 1.25,
        "tokens": 50000,
        "calls": 25
      },
      {
        "date": "2025-11-15",
        "cost_usd": 2.50,
        "tokens": 100000,
        "calls": 50
      },
      {
        "date": "2025-11-16",
        "cost_usd": 1.75,
        "tokens": 75000,
        "calls": 35
      }
    ]
    ```

    **Use Cases:**
    - Render daily cost trend charts
    - Budget burn-down graphs
    - Usage pattern analysis
    - Cost forecasting

    Args:
        time_range: Time window for history (7d, 30d, all)

    Returns:
        List[CostHistory]: Daily cost data sorted by date

    Raises:
        HTTPException: If cost retrieval fails

    See Also:
        - GET /admin/costs/stats: Aggregated cost statistics
        - src/components/llm_proxy/cost_tracker.py: Cost tracking implementation
    """
    try:
        tracker = get_cost_tracker()

        # Calculate time filter
        start_date = None
        if time_range == "7d":
            start_date = (datetime.now() - timedelta(days=7)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif time_range == "30d":
            start_date = (datetime.now() - timedelta(days=30)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        # Query daily aggregates from database
        import sqlite3

        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()

            # Build WHERE clause
            conditions = []
            params = []
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date.isoformat())

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Aggregate by date
            cursor.execute(
                f"""
                SELECT
                    date(timestamp) as date,
                    SUM(cost_usd) as total_cost,
                    SUM(tokens_total) as total_tokens,
                    COUNT(*) as total_calls
                FROM llm_requests
                WHERE {where_clause}
                GROUP BY date(timestamp)
                ORDER BY date ASC
            """,
                tuple(params),
            )

            rows = cursor.fetchall()

        # Build response
        history = [
            CostHistory(
                date=row[0],
                cost_usd=row[1],
                tokens=row[2],
                calls=row[3],
            )
            for row in rows
        ]

        logger.info(
            "cost_history_retrieved",
            time_range=time_range,
            data_points=len(history),
            start_date=start_date.isoformat() if start_date else "all_time",
        )

        return history

    except Exception as e:
        logger.error("cost_history_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cost history: {str(e)}",
        ) from e
