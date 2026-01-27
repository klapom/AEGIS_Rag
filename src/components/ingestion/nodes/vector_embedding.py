"""Vector Embedding Node for LangGraph Ingestion Pipeline.

Sprint 54 Feature 54.6: Extracted from langgraph_nodes.py
Sprint 87 Feature 87.4: FlagEmbedding multi-vector integration

This module handles embedding generation and Qdrant upload:
- Generate BGE-M3 embeddings (dense + sparse) via FlagEmbedding
- Create Qdrant payloads with full provenance
- Upload to Qdrant vector database (multi-vector or dense-only)

Multi-Vector Architecture (Sprint 87):
    - FlagEmbedding backend: Generates both dense and sparse vectors in single call
    - MultiVectorCollectionManager: Handles collections with named vectors
    - Backward compatibility: Detects collection type and uses appropriate storage
    - Feature flag: EMBEDDING_BACKEND=flag-embedding

Node: embedding_node
"""

import hashlib
import time
import uuid

import structlog
from qdrant_client import models
from qdrant_client.models import NamedVector, PointStruct

from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
)
from src.components.ingestion.logging_utils import log_phase_summary
from src.components.shared.embedding_factory import get_embedding_service
from src.components.vector_search.multi_vector_collection import get_multi_vector_manager
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)


async def embedding_node(state: IngestionState) -> IngestionState:
    """Node 4: Generate embeddings + upload to Qdrant with full provenance (Feature 21.6).

    Feature 21.6 Changes:
    - Handles enhanced chunks (with image_bboxes)
    - Uses chunk.contextualize() for hierarchical context
    - Stores full BBox provenance in Qdrant payload
    - Includes page dimensions for frontend rendering

    Workflow:
    1. Extract contextualized text from chunks
    2. Generate BGE-M3 embeddings (1024D) via Ollama
    3. Create Qdrant payloads with full provenance
    4. Upload to Qdrant vector database

    Args:
        state: Current ingestion state

    Returns:
        Updated state with embedded chunk IDs

    Raises:
        IngestionError: If embedding or upload fails

    Example:
        >>> state = await embedding_node(state)
        >>> len(state["embedded_chunk_ids"])
        8  # 8 chunks uploaded to Qdrant
        >>> state["embedding_status"]
        'completed'
    """
    embedding_node_start = time.perf_counter()
    logger.info(
        "TIMING_embedding_start",
        stage="embedding",
        document_id=state["document_id"],
    )

    state["embedding_status"] = "running"
    state["embedding_start_time"] = time.time()

    try:
        # Get enhanced chunks (Feature 21.6: list of {chunk, image_bboxes})
        chunk_data_list = state.get("chunks", [])
        if not chunk_data_list:
            raise IngestionError(
                document_id=state.get("document_id", "unknown"),
                reason="No chunks to embed (chunks list is empty)",
            )

        # Get embedding service (BGE-M3, 1024D)
        embedding_service = get_embedding_service()

        # Feature 21.6: Extract contextualized text (includes headings, captions, page)
        texts = []
        for chunk_data in chunk_data_list:
            chunk = chunk_data["chunk"] if isinstance(chunk_data, dict) else chunk_data
            # Use contextualize() for hierarchical context
            if hasattr(chunk, "contextualize"):
                contextualized_text = chunk.contextualize()
                texts.append(contextualized_text)
            else:
                # Sprint 76: All chunks MUST be Pydantic Chunk with .content field
                # If this fails, there's a bug in chunking_node or document_parsers
                if hasattr(chunk, "content"):
                    texts.append(chunk.content)
                elif hasattr(chunk, "text"):
                    # Legacy fallback (should not happen after Sprint 76)
                    texts.append(chunk.text)
                    logger.warning(
                        "chunk_has_text_not_content_embedding",
                        chunk_type=type(chunk).__name__,
                        note="Found .text instead of .content - check chunking_node for legacy code path",
                    )
                else:
                    # HARD FAILURE: This should NEVER happen
                    # If you see this error, a chunk was created incorrectly somewhere.
                    # Possible sources:
                    # - src/components/ingestion/nodes/adaptive_chunking.py (Docling path)
                    # - src/components/ingestion/nodes/document_parsers.py (legacy path)
                    # - (ChunkingService removed in Sprint 121, TD-054)
                    # FIX: Ensure all chunking code paths create Pydantic Chunk objects
                    logger.error(
                        "chunk_missing_content_and_text_embedding",
                        chunk_type=type(chunk).__name__,
                        chunk_attributes=dir(chunk),
                        note="CRITICAL: Chunk has neither .content nor .text attribute",
                    )
                    raise ValueError(
                        f"Chunk has neither 'content' nor 'text' attribute. "
                        f"Type: {type(chunk).__name__}. "
                        f"This indicates a bug in the chunking pipeline. "
                        f"Check: adaptive_chunking.py or document_parsers.py"
                    )

        # Generate embeddings (Sprint 87: Dense + sparse if FlagEmbedding backend)
        embedding_gen_start = time.perf_counter()
        logger.info(
            "TIMING_embedding_generation_start",
            stage="embedding",
            substage="embedding_generation",
            chunk_count=len(texts),
            total_chars=sum(len(t) for t in texts),
        )
        embeddings = await embedding_service.embed_batch(texts)
        embedding_gen_end = time.perf_counter()
        embedding_gen_ms = (embedding_gen_end - embedding_gen_start) * 1000
        embeddings_per_sec = len(texts) / (embedding_gen_ms / 1000) if embedding_gen_ms > 0 else 0

        # Detect backend type (Sprint 87: FlagEmbedding returns dict, others return list)
        is_multi_vector = isinstance(embeddings[0], dict) if embeddings else False
        embedding_dim = (
            len(embeddings[0]["dense"])
            if is_multi_vector
            else len(embeddings[0]) if embeddings else 0
        )
        avg_sparse_tokens = (
            sum(len(e["sparse_vector"].indices) for e in embeddings) / len(embeddings)
            if is_multi_vector and embeddings
            else 0
        )

        logger.info(
            "TIMING_embedding_generation_complete",
            stage="embedding",
            substage="embedding_generation",
            duration_ms=round(embedding_gen_ms, 2),
            embeddings_generated=len(embeddings),
            throughput_embeddings_per_sec=round(embeddings_per_sec, 2),
            embedding_dim=embedding_dim,
            is_multi_vector=is_multi_vector,
            avg_sparse_tokens=round(avg_sparse_tokens, 0) if is_multi_vector else None,
        )

        # Upload to Qdrant (Sprint 87: Multi-vector or dense-only)
        qdrant = QdrantClientWrapper()
        collection_name = settings.qdrant_collection

        # Sprint 87: Check if multi-vector backend and create appropriate collection
        multi_vector_manager = get_multi_vector_manager()

        if is_multi_vector:
            # Create multi-vector collection (dense + sparse)
            await multi_vector_manager.create_multi_vector_collection(
                collection_name=collection_name,
                dense_dim=embedding_dim,
            )
            logger.info(
                "multi_vector_collection_ensured",
                collection=collection_name,
                dense_dim=embedding_dim,
            )
        else:
            # Create legacy dense-only collection
            await qdrant.create_collection(
                collection_name=collection_name,
                vector_size=embedding_dim,
            )
            logger.info(
                "dense_only_collection_ensured",
                collection=collection_name,
                vector_size=embedding_dim,
            )

        # Check collection capabilities for backward compatibility
        has_sparse = await multi_vector_manager.collection_has_sparse(collection_name)

        # Create Qdrant points with full provenance
        page_dimensions = state.get("page_dimensions", {})
        points = []
        chunk_ids = []

        for chunk_data, embedding, contextualized_text in zip(
            chunk_data_list, embeddings, texts, strict=False
        ):
            # Handle both enhanced and legacy chunk formats
            if isinstance(chunk_data, dict):
                chunk = chunk_data["chunk"]
                image_bboxes = chunk_data.get("image_bboxes", [])
            else:
                chunk = chunk_data
                image_bboxes = []

            # Generate deterministic chunk ID (Sprint 30: Use UUID format for Qdrant)
            # Sprint 76: All chunks MUST be Pydantic Chunk with .content field
            if hasattr(chunk, "content"):
                chunk_text = chunk.content
            elif hasattr(chunk, "text"):
                # Legacy fallback (should not happen after Sprint 76)
                chunk_text = chunk.text
                logger.warning(
                    "chunk_id_has_text_not_content",
                    chunk_type=type(chunk).__name__,
                    note="Found .text instead of .content - check chunking_node for legacy code path",
                )
            else:
                # HARD FAILURE: This should NEVER happen
                # If you see this error, a chunk was created incorrectly somewhere.
                # Possible sources:
                # - src/components/ingestion/nodes/adaptive_chunking.py (Docling path)
                # - src/components/ingestion/nodes/document_parsers.py (legacy path)
                # - src/core/chunking_service.py (ChunkingService)
                # FIX: Ensure all chunking code paths create Pydantic Chunk objects
                logger.error(
                    "chunk_id_missing_content_and_text",
                    chunk_type=type(chunk).__name__,
                    chunk_attributes=dir(chunk),
                    note="CRITICAL: Chunk has neither .content nor .text attribute",
                )
                raise ValueError(
                    f"Chunk has neither 'content' nor 'text' attribute for ID generation. "
                    f"Type: {type(chunk).__name__}. "
                    f"This indicates a bug in the chunking pipeline. "
                    f"Check: adaptive_chunking.py or document_parsers.py"
                )

            chunk_name = f"{state['document_id']}_chunk_{hashlib.sha256(chunk_text.encode()).hexdigest()[:8]}"
            # Convert to UUID using uuid5 (deterministic, namespace-based)
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_name))
            chunk_ids.append(chunk_id)

            # Feature 21.6: Create payload with full provenance
            page_no = (
                chunk.meta.page_no
                if hasattr(chunk, "meta") and hasattr(chunk.meta, "page_no")
                else None
            )
            headings = (
                chunk.meta.headings
                if hasattr(chunk, "meta") and hasattr(chunk.meta, "headings")
                else []
            )

            payload = {
                # Content
                "content": chunk_text,
                "contextualized_content": contextualized_text,
                # Document Provenance
                "document_id": state["document_id"],
                "document_path": str(state["document_path"]),
                "page_no": page_no,
                "headings": headings,
                "chunk_id": chunk_id,
                # Page Dimensions (for frontend rendering)
                "page_dimensions": page_dimensions.get(page_no) if page_no else None,
                # Image Annotations with BBox (CRITICAL for Feature 21.6!)
                "contains_images": len(image_bboxes) > 0,
                "image_annotations": [
                    {
                        "description": img["description"],
                        "vlm_model": img["vlm_model"],
                        "bbox_absolute": (
                            img["bbox_full"]["bbox_absolute"] if img["bbox_full"] else None
                        ),
                        "page_context": (
                            img["bbox_full"]["page_context"] if img["bbox_full"] else None
                        ),
                        "bbox_normalized": (
                            img["bbox_full"]["bbox_normalized"] if img["bbox_full"] else None
                        ),
                    }
                    for img in image_bboxes
                ],
                # Timestamps
                "ingestion_timestamp": time.time(),
                # Sprint 76 Feature 76.1 (TD-084): Multi-tenant namespace isolation
                # FIXED: Use "namespace_id" (not "namespace") to match retrieval filters
                "namespace_id": state.get("namespace_id", "default"),
            }

            # Sprint 87: Create point with multi-vector or dense-only format
            if is_multi_vector and has_sparse:
                # Multi-vector point: Named vectors (dense + sparse)
                point = PointStruct(
                    id=chunk_id,
                    vector={
                        "dense": embedding["dense"],
                        "sparse": embedding["sparse_vector"],
                    },
                    payload=payload,
                )
                logger.debug(
                    "multi_vector_point_created",
                    chunk_id=chunk_id,
                    dense_dim=len(embedding["dense"]),
                    sparse_tokens=len(embedding["sparse_vector"].indices),
                )
            elif is_multi_vector and not has_sparse:
                # Fallback: Multi-vector backend but dense-only collection
                # Extract dense vector only (backward compatibility)
                point = PointStruct(
                    id=chunk_id,
                    vector=embedding["dense"],
                    payload=payload,
                )
                logger.warning(
                    "multi_vector_backend_dense_only_collection",
                    chunk_id=chunk_id,
                    note="FlagEmbedding backend detected but collection does not support sparse vectors. Using dense-only.",
                )
            else:
                # Dense-only point (legacy format)
                point = PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=payload,
                )

            points.append(point)

        # Upload batch
        qdrant_upsert_start = time.perf_counter()
        await qdrant.upsert_points(
            collection_name=collection_name,
            points=points,
            batch_size=100,
        )
        qdrant_upsert_end = time.perf_counter()
        qdrant_upsert_ms = (qdrant_upsert_end - qdrant_upsert_start) * 1000

        logger.info(
            "TIMING_qdrant_upsert_complete",
            stage="embedding",
            substage="qdrant_upsert",
            duration_ms=round(qdrant_upsert_ms, 2),
            points_uploaded=len(points),
            batch_size=100,
            collection=collection_name,
        )

        # Sprint 77 Feature 77.3 (TD-093): Trigger Qdrant index optimization
        # User request: "Nach jedem Ingestion sollten QDRANT Indexed Vectors upgedatet werden"
        if settings.qdrant_optimize_after_ingestion:
            try:
                logger.info(
                    "triggering_qdrant_index_optimization",
                    collection=collection_name,
                    indexing_threshold=settings.qdrant_indexing_threshold,
                )

                optimize_start = time.perf_counter()

                # Update collection to force immediate indexing
                await qdrant.async_client.update_collection(
                    collection_name=collection_name,
                    optimizer_config=models.OptimizersConfigDiff(
                        indexing_threshold=settings.qdrant_indexing_threshold
                    ),
                )

                optimize_end = time.perf_counter()
                optimize_ms = (optimize_end - optimize_start) * 1000

                logger.info(
                    "qdrant_index_optimization_triggered",
                    collection=collection_name,
                    duration_ms=round(optimize_ms, 2),
                    indexing_threshold=settings.qdrant_indexing_threshold,
                )

            except Exception as e:
                # Log but don't fail ingestion if optimization fails
                logger.warning(
                    "qdrant_index_optimization_failed",
                    collection=collection_name,
                    error=str(e),
                )

        # Store point IDs
        state["embedded_chunk_ids"] = chunk_ids
        state["embedding_status"] = "completed"
        state["embedding_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        embedding_node_end = time.perf_counter()
        total_embedding_ms = (embedding_node_end - embedding_node_start) * 1000

        logger.info(
            "TIMING_embedding_complete",
            stage="embedding",
            duration_ms=round(total_embedding_ms, 2),
            document_id=state["document_id"],
            points_uploaded=len(points),
            points_with_images=sum(1 for p in points if p.payload.get("contains_images")),
            collection=collection_name,
            timing_breakdown={
                "embedding_generation_ms": round(embedding_gen_ms, 2),
                "qdrant_upsert_ms": round(qdrant_upsert_ms, 2),
            },
        )

        # Sprint 83 Feature 83.1: Log embedding phase summary with percentile metrics
        log_phase_summary(
            phase="embedding",
            total_time_ms=total_embedding_ms,
            items_processed=len(points),
            points_with_images=sum(1 for p in points if p.payload.get("contains_images")),
            embedding_dim=len(embeddings[0]) if embeddings else 0,
            throughput_embeddings_per_sec=round(embeddings_per_sec, 2),
        )

        return state

    except Exception as e:
        logger.error("node_embedding_error", document_id=state["document_id"], error=str(e))
        add_error(state, "embedding", str(e), "error")
        state["embedding_status"] = "failed"
        state["embedding_end_time"] = time.time()
        raise
