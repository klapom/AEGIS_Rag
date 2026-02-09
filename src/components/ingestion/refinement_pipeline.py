"""Refinement Pipeline for Two-Phase Document Upload (Sprint 83 Feature 83.4).

This module provides Phase 2: Background Refinement (30-60s async processing).

Phase 2 Workflow:
    1. Load document chunks from Qdrant
    2. Full LLM extraction with gleaning (entities + relations)
    3. Neo4j graph indexing (entities + relations)
    4. Replace Qdrant metadata with LLM entities (higher quality)
    5. Update Redis status to "ready"

Performance Target: 30-60s total processing time

Example:
    >>> from refinement_pipeline import run_background_refinement
    >>> await run_background_refinement(
    ...     document_id="doc_abc123",
    ...     namespace="research",
    ...     domain="ai_papers",
    ... )
    >>> # Completes after ~30-60s, updates status to "ready"
"""

import time
from typing import Any

import structlog

from src.components.graph_rag.extraction_pipeline import extract_and_store_entities
from src.components.ingestion.background_jobs import get_background_job_queue
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)


async def load_chunks_from_qdrant(
    document_id: str,
    namespace: str,
) -> list[dict[str, Any]]:
    """Load document chunks from Qdrant.

    Args:
        document_id: Document ID
        namespace: Document namespace

    Returns:
        List of chunk payloads with content and metadata

    Raises:
        IngestionError: If loading fails
    """
    try:
        qdrant = QdrantClientWrapper()
        collection_name = settings.qdrant_collection

        # Scroll through all points for this document
        points = []
        offset = None

        while True:
            result = await qdrant.async_client.scroll(
                collection_name=collection_name,
                scroll_filter={
                    "must": [
                        {"key": "document_id", "match": {"value": document_id}},
                        {"key": "namespace_id", "match": {"value": namespace}},
                    ]
                },
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            batch_points, next_offset = result

            if not batch_points:
                break

            points.extend(batch_points)

            if next_offset is None:
                break

            offset = next_offset

        logger.info(
            "refinement_chunks_loaded_from_qdrant",
            document_id=document_id,
            chunks_count=len(points),
        )

        return [point.payload for point in points]

    except Exception as e:
        logger.error(
            "refinement_load_chunks_failed",
            document_id=document_id,
            error=str(e),
        )
        raise IngestionError(
            document_id=document_id,
            reason=f"Failed to load chunks from Qdrant: {e}",
        ) from e


async def extract_entities_and_relations_llm(
    chunks: list[dict[str, Any]],
    document_id: str,
    domain: str,
) -> tuple[int, int]:
    """Extract entities and relations using extraction pipeline.

    Args:
        chunks: List of chunk payloads from Qdrant
        document_id: Document ID
        domain: Document domain (for domain-specific prompts)

    Returns:
        Tuple of (entity_count, relation_count)

    Performance: 20-40s for 10 chunks with gleaning
    """
    start_time = time.perf_counter()

    try:
        # Prepare chunks for extraction
        chunks_for_extraction = [
            {
                "chunk_id": chunk.get("chunk_id", f"{document_id}_chunk_{i}"),
                "text": chunk.get("content", ""),
                "chunk_index": i,
            }
            for i, chunk in enumerate(chunks)
        ]

        # Extract and store entities using extraction_pipeline
        result = await extract_and_store_entities(
            chunks=chunks_for_extraction,
            document_id=document_id,
            document_path=f"{document_id}.txt",
            namespace_id=chunks[0].get("namespace_id", "default") if chunks else "default",
            domain_id=domain,
        )

        entity_count = result.get("entity_count", 0)
        relation_count = result.get("relation_count", 0)

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "refinement_llm_extraction_complete",
            document_id=document_id,
            chunks_processed=len(chunks),
            entities_extracted=entity_count,
            relations_extracted=relation_count,
            duration_ms=round(duration_ms, 2),
        )

        return entity_count, relation_count

    except Exception as e:
        logger.error(
            "refinement_llm_extraction_failed",
            document_id=document_id,
            error=str(e),
        )
        raise IngestionError(
            document_id=document_id,
            reason=f"LLM extraction failed: {e}",
        ) from e


async def update_neo4j_graph(
    entity_count: int,
    relation_count: int,
    document_id: str,
    namespace: str,
) -> None:
    """Log Neo4j graph indexing completion.

    Note: Entity/relation storage is now handled by extract_and_store_entities().

    Args:
        entity_count: Number of entities indexed
        relation_count: Number of relations indexed
        document_id: Document ID
        namespace: Document namespace

    Raises:
        IngestionError: If Neo4j indexing fails
    """
    start_time = time.perf_counter()
    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "refinement_neo4j_indexing_complete",
        document_id=document_id,
        entities_indexed=entity_count,
        relations_indexed=relation_count,
        duration_ms=round(duration_ms, 2),
    )


async def update_qdrant_metadata(
    document_id: str,
    namespace: str,
) -> None:
    """Mark Qdrant chunks as refined.

    Note: Entity metadata is now stored during extraction pipeline.

    Args:
        document_id: Document ID
        namespace: Document namespace

    Raises:
        IngestionError: If Qdrant update fails
    """
    start_time = time.perf_counter()

    try:
        qdrant = QdrantClientWrapper()
        collection_name = settings.qdrant_collection

        # Get all chunks for this document
        points = []
        offset = None

        while True:
            result = await qdrant.async_client.scroll(
                collection_name=collection_name,
                scroll_filter={
                    "must": [
                        {"key": "document_id", "match": {"value": document_id}},
                        {"key": "namespace_id", "match": {"value": namespace}},
                    ]
                },
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )

            batch_points, next_offset = result

            if not batch_points:
                break

            points.extend([p.id for p in batch_points])

            if next_offset is None:
                break

            offset = next_offset

        # Mark all chunks as refined
        if points:
            await qdrant.async_client.set_payload(
                collection_name=collection_name,
                payload={
                    "refinement_pending": False,
                    "refinement_timestamp": time.time(),
                },
                points=points,
            )

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "refinement_qdrant_metadata_updated",
            document_id=document_id,
            chunks_updated=len(points),
            duration_ms=round(duration_ms, 2),
        )

    except Exception as e:
        logger.error(
            "refinement_qdrant_metadata_update_failed",
            document_id=document_id,
            error=str(e),
        )
        raise IngestionError(
            document_id=document_id,
            reason=f"Qdrant metadata update failed: {e}",
        ) from e


async def run_background_refinement(
    document_id: str,
    namespace: str,
    domain: str,
) -> None:
    """Run Phase 2: Background Refinement Pipeline (30-60s async).

    Workflow:
        1. Load document chunks from Qdrant
        2. Full LLM extraction with gleaning (entities + relations)
        3. Neo4j graph indexing (entities + relations)
        4. Replace Qdrant metadata with LLM entities
        5. Update Redis status to "ready"

    Args:
        document_id: Document ID
        namespace: Document namespace
        domain: Document domain

    Raises:
        IngestionError: If refinement fails

    Performance Target: 30-60s
    """
    start_time = time.perf_counter()

    logger.info(
        "refinement_pipeline_start",
        document_id=document_id,
        namespace=namespace,
        domain=domain,
    )

    # Get background job queue
    job_queue = get_background_job_queue()
    await job_queue.initialize()

    try:
        # Step 1: Load chunks from Qdrant
        await job_queue.set_status(
            document_id=document_id,
            status="processing_background",
            progress_pct=10.0,
            current_phase="loading_chunks",
            namespace=namespace,
            domain=domain,
        )

        chunks = await load_chunks_from_qdrant(document_id, namespace)

        if not chunks:
            raise IngestionError(
                document_id=document_id,
                reason="No chunks found in Qdrant",
            )

        # Step 2: Full LLM extraction
        await job_queue.set_status(
            document_id=document_id,
            status="processing_background",
            progress_pct=30.0,
            current_phase="llm_extraction",
            namespace=namespace,
            domain=domain,
        )

        entity_count, relation_count = await extract_entities_and_relations_llm(
            chunks=chunks,
            document_id=document_id,
            domain=domain,
        )

        # Step 3: Neo4j graph indexing
        await job_queue.set_status(
            document_id=document_id,
            status="processing_background",
            progress_pct=60.0,
            current_phase="graph_indexing",
            namespace=namespace,
            domain=domain,
        )

        await update_neo4j_graph(
            entity_count=entity_count,
            relation_count=relation_count,
            document_id=document_id,
            namespace=namespace,
        )

        # Step 4: Update Qdrant metadata
        await job_queue.set_status(
            document_id=document_id,
            status="processing_background",
            progress_pct=80.0,
            current_phase="metadata_update",
            namespace=namespace,
            domain=domain,
        )

        await update_qdrant_metadata(
            document_id=document_id,
            namespace=namespace,
        )

        # Step 5: Mark as ready
        await job_queue.set_status(
            document_id=document_id,
            status="ready",
            progress_pct=100.0,
            current_phase="completed",
            namespace=namespace,
            domain=domain,
        )

        total_duration = (time.perf_counter() - start_time) * 1000

        logger.info(
            "refinement_pipeline_complete",
            document_id=document_id,
            total_duration_ms=round(total_duration, 2),
            chunks_processed=len(chunks),
            entities_extracted=entity_count,
            relations_extracted=relation_count,
        )

        # Check if target met (30-60s)
        if total_duration > 60000:
            logger.warning(
                "refinement_target_exceeded",
                document_id=document_id,
                target_ms=60000,
                actual_ms=round(total_duration, 2),
            )

    except Exception as e:
        # Mark as failed
        await job_queue.set_status(
            document_id=document_id,
            status="failed",
            progress_pct=0.0,
            current_phase="refinement_failed",
            error_message=str(e),
            namespace=namespace,
            domain=domain,
        )

        logger.error(
            "refinement_pipeline_failed",
            document_id=document_id,
            error=str(e),
        )
        raise
