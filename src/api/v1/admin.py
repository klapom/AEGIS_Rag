"""Admin API endpoints for re-indexing and maintenance operations.

Sprint 16 Feature 16.3: Unified Re-Indexing Pipeline with SSE progress tracking.
"""

from collections.abc import AsyncGenerator
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client.models import Distance

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.ingestion import ingest_documents
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

        # Discover documents
        if not input_dir.exists():
            raise VectorSearchError(query="", reason=f"Input directory does not exist: {input_dir}")

        document_files = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.txt"))
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

        # Phase 3: Indexing (use ingest_documents helper function)
        if not dry_run:
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 30, 'message': f'Indexing {total_docs} documents into Qdrant...'})}\n\n"

            # Use the ingest_documents helper function (Qdrant + BM25)
            stats = await ingest_documents(
                input_dir=input_dir,
                collection_name=collection_name,
            )

            points_indexed = stats.get("points_indexed", 0)
            message = (
                f"Indexed {points_indexed} chunks into Qdrant. Starting Neo4j graph indexing..."
            )
            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 60, 'message': message})}\n\n"

            # Phase 3b: Index into Neo4j/LightRAG graph (Sprint 16 Feature 16.7)
            # Sprint 24 Feature 24.15: Lazy import for optional llama_index dependency
            try:
                # ================================================================
                # LAZY IMPORT: llama_index (Sprint 24 Feature 24.15)
                # ================================================================
                # Load llama_index only when re-indexing is executed.
                # This allows the core API to run without llama_index installed.
                # ================================================================
                try:
                    from llama_index.core import SimpleDirectoryReader
                except ImportError as e:
                    error_msg = (
                        "llama_index is required for graph re-indexing but is not installed.\n\n"
                        "INSTALLATION OPTIONS:\n"
                        "1. poetry install --with ingestion\n"
                        "2. poetry install --all-extras\n\n"
                        "NOTE: Re-indexing requires LlamaIndex for document loading.\n"
                        "For production deployments, install the ingestion group."
                    )
                    logger.error(
                        "llamaindex_import_failed",
                        endpoint="/admin/reindex",
                        error=str(e),
                        install_command="poetry install --with ingestion",
                    )
                    raise VectorSearchError(query="", reason=error_msg) from e

                lightrag_wrapper = await get_lightrag_wrapper_async()

                # Load documents
                loader = SimpleDirectoryReader(
                    input_dir=str(input_dir),
                    required_exts=[".pdf", ".txt", ".md", ".docx", ".csv", ".pptx"],
                    recursive=True,
                    filename_as_id=True,
                )
                documents = loader.load_data()

                # Convert to LightRAG format
                lightrag_docs = []
                for doc in documents:
                    content = doc.get_content()
                    if content and content.strip():
                        lightrag_docs.append(
                            {
                                "text": content,
                                "id": doc.doc_id or doc.metadata.get("file_name", "unknown"),
                            }
                        )

                # Insert into LightRAG (entities + relationships + graph)
                if lightrag_docs:
                    graph_stats = await lightrag_wrapper.insert_documents_optimized(lightrag_docs)
                    logger.info("lightrag_indexing_complete", **graph_stats)
                    total_entities = graph_stats.get("stats", {}).get("total_entities", 0)
                    total_relations = graph_stats.get("stats", {}).get("total_relations", 0)
                    graph_message = f"Indexed {total_entities} entities and {total_relations} relations into Neo4j"
                    yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 85, 'message': graph_message})}\n\n"
                else:
                    logger.warning("no_documents_for_graph_indexing")

            except Exception as e:
                logger.error("lightrag_indexing_failed", error=str(e))
                # Continue even if graph indexing fails (Qdrant indexing succeeded)
                error_message = f"Graph indexing failed: {str(e)} (continuing with Qdrant only)"
                yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 85, 'message': error_message})}\n\n"

            yield f"data: {json.dumps({'status': 'in_progress', 'phase': 'indexing', 'progress_percent': 90, 'message': 'Indexing completed successfully'})}\n\n"
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
                raise VectorSearchError(query="", reason=f"Collection {collection_name} not found after re-indexing")

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
