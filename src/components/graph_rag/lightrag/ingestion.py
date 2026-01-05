"""LightRAG ingestion operations.

Sprint 55 Feature 55.4: Document ingestion functionality extracted from lightrag_wrapper.py

This module handles:
- Per-chunk entity/relation extraction
- Document insertion (basic and optimized)
- Pre-chunked document insertion
- Deduplication integration
"""

import time
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.graph_rag.extraction_factory import create_extraction_pipeline_from_config
from src.components.graph_rag.lightrag.converters import (
    chunk_text_with_metadata,
    convert_chunks_to_lightrag_format,
    convert_entities_to_lightrag_format,
    convert_relations_to_lightrag_format,
)
from src.components.graph_rag.lightrag.neo4j_storage import store_chunks_and_provenance
from src.components.graph_rag.relation_deduplicator import create_relation_deduplicator_from_config
from src.components.graph_rag.semantic_deduplicator import create_deduplicator_from_config
from src.core.config import settings
from src.monitoring.metrics import record_deduplication_detail, record_extraction_by_type

logger = structlog.get_logger(__name__)


async def extract_per_chunk(
    document_text: str,
    document_id: str,
    chunk_token_size: int = 1800,
    chunk_overlap_token_size: int = 300,
) -> dict[str, Any]:
    """Extract entities and relations per-chunk using LLM Extraction Pipeline.

    Sprint 14 Feature 14.1 - Phase 2: Per-Chunk Extraction

    Process:
    1. Chunk document with tiktoken
    2. For each chunk: Run LLM Extraction Pipeline
    3. Annotate all entities/relations with chunk_id for provenance

    Args:
        document_text: Full document text
        document_id: Source document ID
        chunk_token_size: Target chunk size in tokens (default: 1800, aligned with Qdrant)
        chunk_overlap_token_size: Overlap between chunks (default: 300)

    Returns:
        Dictionary with:
        - chunks: List of chunk metadata
        - entities: List of all entities from all chunks
        - relations: List of all relations from all chunks
        - stats: Extraction statistics
    """
    start_time = time.time()

    logger.info(
        "per_chunk_extraction_start",
        document_id=document_id,
        text_length=len(document_text),
    )

    # Step 1: Chunk the document
    chunks = chunk_text_with_metadata(
        text=document_text,
        document_id=document_id,
        chunk_token_size=chunk_token_size,
        chunk_overlap_token_size=chunk_overlap_token_size,
    )

    logger.info(
        "chunking_complete",
        document_id=document_id,
        total_chunks=len(chunks),
    )

    # Step 2: Initialize Extraction Pipeline
    extractor = create_extraction_pipeline_from_config()
    logger.info("extraction_pipeline_initialized", pipeline_type="llm_extraction")

    # Step 3: Extract entities and relations per chunk
    all_entities = []
    all_relations = []

    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        chunk_text = chunk["text"]
        chunk_index = chunk["chunk_index"]

        logger.info(
            "extracting_chunk",
            document_id=document_id,
            chunk_id=chunk_id[:8],
            chunk_index=chunk_index,
            chunk_tokens=chunk["tokens"],
        )

        try:
            # Sprint 76 Feature 76.2 (TD-085): Pass domain for optimized prompts
            entities, relations = await extractor.extract(
                text=chunk_text, document_id=f"{document_id}#{chunk_index}", domain=domain_id
            )

            # Annotate entities with chunk metadata
            tokens = chunk.get("tokens", chunk.get("token_count", 0))
            start_token = chunk.get("start_token", 0)
            end_token = chunk.get("end_token", tokens)

            for entity in entities:
                entity["chunk_id"] = chunk_id
                entity["document_id"] = document_id
                entity["chunk_index"] = chunk_index
                entity["start_token"] = start_token
                entity["end_token"] = end_token

            for relation in relations:
                relation["chunk_id"] = chunk_id
                relation["document_id"] = document_id
                relation["chunk_index"] = chunk_index
                relation["start_token"] = start_token
                relation["end_token"] = end_token

            all_entities.extend(entities)
            all_relations.extend(relations)

            logger.info(
                "chunk_extraction_complete",
                chunk_id=chunk_id[:8],
                entities_found=len(entities),
                relations_found=len(relations),
            )

        except Exception as e:
            logger.error(
                "chunk_extraction_failed",
                chunk_id=chunk_id[:8],
                chunk_index=chunk_index,
                error=str(e),
            )
            continue

    # Step 4: Calculate statistics
    extraction_time = time.time() - start_time

    stats = {
        "total_chunks": len(chunks),
        "total_entities": len(all_entities),
        "total_relations": len(all_relations),
        "avg_entities_per_chunk": len(all_entities) / len(chunks) if chunks else 0,
        "avg_relations_per_chunk": len(all_relations) / len(chunks) if chunks else 0,
        "extraction_time_seconds": extraction_time,
    }

    logger.info(
        "per_chunk_extraction_complete",
        document_id=document_id,
        **stats,
    )

    return {
        "chunks": chunks,
        "entities": all_entities,
        "relations": all_relations,
        "stats": stats,
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def insert_documents(
    rag: Any,
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Insert multiple documents into knowledge graph (basic method).

    Args:
        rag: Initialized LightRAG instance
        documents: List of documents with 'text' and optional 'metadata' fields

    Returns:
        Batch insertion result with success/failure counts
    """
    logger.info("insert_documents_start", count=len(documents))

    results = []
    for i, doc in enumerate(documents):
        try:
            text = doc.get("text", "")
            if not text:
                logger.warning("empty_document", index=i)
                results.append({"index": i, "status": "skipped", "reason": "empty_text"})
                continue

            result = await rag.ainsert(text)
            results.append({"index": i, "status": "success", "result": result})
            logger.debug("document_inserted", index=i, result=result)

        except Exception as e:
            logger.error("document_insert_failed", index=i, error=str(e))
            results.append({"index": i, "status": "error", "error": str(e)})

    success_count = sum(1 for r in results if r["status"] == "success")
    logger.info(
        "insert_documents_complete",
        total=len(documents),
        success=success_count,
        failed=len(documents) - success_count,
    )

    return {
        "total": len(documents),
        "success": success_count,
        "failed": len(documents) - success_count,
        "results": results,
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def insert_documents_optimized(
    rag: Any,
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Insert documents using LLM Extraction Pipeline with Graph-based Provenance.

    Sprint 14 Feature 14.1 - Phase 7: Main Integration Method

    This method provides an optimized alternative to insert_documents() that:
    1. Uses LLM Extraction Pipeline for fast extraction
    2. Chunks documents for precise provenance tracking
    3. Stores chunk nodes and MENTIONED_IN relationships in Neo4j
    4. Leverages LightRAG embeddings for query compatibility

    Args:
        rag: Initialized LightRAG instance
        documents: List of documents with 'text' and optional 'id' fields

    Returns:
        Batch insertion result with stats and per-document results
    """
    logger.info("insert_documents_optimized_start", count=len(documents))

    total_start = time.time()
    results = []
    aggregate_stats = {
        "total_chunks": 0,
        "total_entities": 0,
        "total_relations": 0,
        "total_mentioned_in": 0,
    }

    for i, doc in enumerate(documents):
        doc_start = time.time()

        try:
            text = doc.get("text", "")
            doc_id = doc.get("id", f"doc_{i}")

            if not text:
                logger.warning("empty_document", index=i, doc_id=doc_id)
                results.append(
                    {
                        "index": i,
                        "doc_id": doc_id,
                        "status": "skipped",
                        "reason": "empty_text",
                    }
                )
                continue

            logger.info(
                "processing_document",
                index=i,
                doc_id=doc_id,
                text_length=len(text),
            )

            # PHASE 1-2: Extract per-chunk
            extraction_result = await extract_per_chunk(
                document_text=text,
                document_id=doc_id,
            )

            chunks = extraction_result["chunks"]
            entities = extraction_result["entities"]
            relations = extraction_result["relations"]

            # PHASE 3-4: Convert to LightRAG format
            lightrag_entities = convert_entities_to_lightrag_format(entities)
            lightrag_relations = convert_relations_to_lightrag_format(relations)
            lightrag_chunks = convert_chunks_to_lightrag_format(chunks, doc_id)

            # PHASE 6: Insert into LightRAG
            if hasattr(rag, "ainsert_custom_kg"):
                await rag.ainsert_custom_kg(
                    custom_kg={
                        "chunks": lightrag_chunks,
                        "entities": lightrag_entities,
                        "relations": lightrag_relations,
                    },
                    full_doc_id=doc_id,
                )
                logger.info(
                    "lightrag_custom_kg_inserted",
                    chunks=len(lightrag_chunks),
                    entities=len(lightrag_entities),
                    relations=len(lightrag_relations),
                )
            else:
                logger.warning("ainsert_custom_kg_unavailable", fallback="using_regular_ainsert")
                await rag.ainsert(text)

            # PHASE 5: Store chunks and provenance in Neo4j
            await store_chunks_and_provenance(
                rag=rag,
                chunks=chunks,
                entities=lightrag_entities,
            )

            doc_time = time.time() - doc_start

            doc_result = {
                "index": i,
                "doc_id": doc_id,
                "status": "success",
                "chunks": len(chunks),
                "entities": len(entities),
                "relations": len(relations),
                "time_seconds": doc_time,
            }

            results.append(doc_result)

            aggregate_stats["total_chunks"] += len(chunks)
            aggregate_stats["total_entities"] += len(entities)
            aggregate_stats["total_relations"] += len(relations)
            aggregate_stats["total_mentioned_in"] += len(entities)

            logger.info("document_processed_successfully", **doc_result)

        except Exception as e:
            logger.error(
                "document_processing_failed",
                index=i,
                doc_id=doc.get("id", f"doc_{i}"),
                error=str(e),
            )
            results.append(
                {
                    "index": i,
                    "doc_id": doc.get("id", f"doc_{i}"),
                    "status": "error",
                    "error": str(e),
                }
            )

    total_time = time.time() - total_start
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = len(documents) - success_count

    logger.info(
        "insert_documents_optimized_complete",
        total=len(documents),
        success=success_count,
        failed=failed_count,
        total_time_seconds=total_time,
        **aggregate_stats,
    )

    return {
        "total": len(documents),
        "success": success_count,
        "failed": failed_count,
        "stats": aggregate_stats,
        "total_time_seconds": total_time,
        "results": results,
    }


async def insert_prechunked_documents(
    rag: Any,
    chunks: list[dict[str, Any]],
    document_id: str,
    document_path: str = "",
    namespace_id: str = "default",
    domain_id: str | None = None,
) -> dict[str, Any]:
    """Insert pre-chunked documents with existing chunk_ids.

    Sprint 42: Unified chunk IDs between Qdrant and Neo4j for true hybrid search.
    Sprint 51: Added namespace_id for multi-tenant isolation.
    Sprint 75 Fix: Added document_path for Neo4j source attribution.
    Sprint 76 TD-085: Added domain_id for DSPy-optimized extraction prompts.

    Args:
        rag: Initialized LightRAG instance
        chunks: List of pre-chunked documents with chunk_id, text, chunk_index
        document_id: Source document ID for provenance tracking
        document_path: Source document path for attribution (default: "")
        namespace_id: Namespace for multi-tenant isolation
        domain_id: Domain for DSPy-optimized prompts (Sprint 76 TD-085)

    Returns:
        Batch insertion result with entities/relations extracted
    """
    logger.info(
        "insert_prechunked_documents_start",
        chunk_count=len(chunks),
        document_id=document_id,
    )

    total_start = time.time()
    aggregate_stats = {
        "total_chunks": 0,
        "total_entities": 0,
        "total_relations": 0,
        "total_mentioned_in": 0,
    }

    extractor = create_extraction_pipeline_from_config()

    all_entities = []
    all_relations = []
    converted_chunks = []

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", f"chunk_{chunk.get('chunk_index', 0)}")
        chunk_text = chunk.get("text", "")
        chunk_index = chunk.get("chunk_index", 0)

        if not chunk_text:
            logger.warning("empty_chunk_skipped", chunk_id=chunk_id)
            continue

        logger.info(
            "extracting_prechunked",
            chunk_id=chunk_id[:16] if len(chunk_id) > 16 else chunk_id,
            chunk_index=chunk_index,
            text_length=len(chunk_text),
        )

        try:
            # Sprint 76 Feature 76.2 (TD-085): Pass domain for optimized prompts
            entities, relations = await extractor.extract(
                text=chunk_text, document_id=f"{document_id}#{chunk_index}", domain=domain_id
            )

            for entity in entities:
                entity["chunk_id"] = chunk_id
                entity["document_id"] = document_id
                entity["chunk_index"] = chunk_index

            for relation in relations:
                relation["chunk_id"] = chunk_id
                relation["document_id"] = document_id
                relation["chunk_index"] = chunk_index

            all_entities.extend(entities)
            all_relations.extend(relations)

            converted_chunks.append(
                {
                    "content": chunk_text,
                    "source_id": chunk_id,
                    "file_path": document_id,
                }
            )

            logger.info(
                "chunk_extraction_complete",
                chunk_id=chunk_id[:16] if len(chunk_id) > 16 else chunk_id,
                entities=len(entities),
                relations=len(relations),
            )

        except Exception as e:
            logger.error("chunk_extraction_failed", chunk_id=chunk_id, error=str(e))
            continue

    # Apply entity deduplication
    entities_before_dedup = len(all_entities)
    relations_before_dedup = len(all_relations)
    entity_mapping: dict[str, str] = {}

    if settings.enable_multi_criteria_dedup and all_entities:
        try:
            deduplicator = create_deduplicator_from_config()
            deduplicated_entities, entity_mapping = await deduplicator.deduplicate_with_mapping(
                all_entities
            )
            entities_after_dedup = len(deduplicated_entities)

            reduction_percent = (
                round((1 - entities_after_dedup / entities_before_dedup) * 100, 1)
                if entities_before_dedup > 0
                else 0
            )

            record_deduplication_detail(
                document_id=document_id,
                entities_before=entities_before_dedup,
                entities_after=entities_after_dedup,
                criterion_matches=None,
            )

            logger.info(
                "entity_deduplication_complete",
                document_id=document_id,
                entities_before=entities_before_dedup,
                entities_after=entities_after_dedup,
                reduction_percent=reduction_percent,
            )

            all_entities = deduplicated_entities
        except Exception as e:
            logger.warning(
                "deduplication_failed_fallback_to_raw", document_id=document_id, error=str(e)
            )

    # Apply relation deduplication
    if settings.enable_relation_dedup and all_relations:
        try:
            relation_deduplicator = create_relation_deduplicator_from_config(settings)
            if relation_deduplicator:
                deduplicated_relations = relation_deduplicator.deduplicate(
                    all_relations,
                    entity_mapping=entity_mapping,
                )
                relations_after_dedup = len(deduplicated_relations)

                relation_reduction_percent = (
                    round((1 - relations_after_dedup / relations_before_dedup) * 100, 1)
                    if relations_before_dedup > 0
                    else 0
                )

                logger.info(
                    "relation_deduplication_complete",
                    document_id=document_id,
                    relations_before=relations_before_dedup,
                    relations_after=relations_after_dedup,
                    reduction_percent=relation_reduction_percent,
                )

                all_relations = deduplicated_relations
        except Exception as e:
            logger.warning(
                "relation_deduplication_failed_fallback_to_raw",
                document_id=document_id,
                error=str(e),
            )

    # Record entity/relation types for monitoring
    entity_type_counts: dict[str, int] = {}
    for entity in all_entities:
        ent_type = entity.get("type", entity.get("entity_type", "UNKNOWN"))
        entity_type_counts[ent_type] = entity_type_counts.get(ent_type, 0) + 1

    relation_type_counts: dict[str, int] = {}
    for relation in all_relations:
        rel_type = relation.get("type", relation.get("relation_type", "RELATES_TO"))
        relation_type_counts[rel_type] = relation_type_counts.get(rel_type, 0) + 1

    record_extraction_by_type(
        entity_types=entity_type_counts,
        relation_types=relation_type_counts,
        model=settings.lightrag_llm_model,
    )

    # Convert to LightRAG format
    lightrag_entities = convert_entities_to_lightrag_format(all_entities)
    lightrag_relations = convert_relations_to_lightrag_format(all_relations)

    logger.info(
        "prechunked_extraction_complete",
        document_id=document_id,
        chunks=len(converted_chunks),
        entities_raw=entities_before_dedup,
        entities_deduplicated=len(lightrag_entities),
        relations=len(lightrag_relations),
    )

    # Insert into LightRAG
    if hasattr(rag, "ainsert_custom_kg"):
        await rag.ainsert_custom_kg(
            custom_kg={
                "chunks": converted_chunks,
                "entities": lightrag_entities,
                "relations": lightrag_relations,
            },
            full_doc_id=document_id,
        )
        logger.info(
            "lightrag_prechunked_kg_inserted",
            chunks=len(converted_chunks),
            entities=len(lightrag_entities),
            relations=len(lightrag_relations),
        )
    else:
        logger.warning("ainsert_custom_kg_unavailable", fallback="entities_relations_not_stored")

    # Store chunks and provenance in Neo4j
    await store_chunks_and_provenance(
        rag=rag,
        chunks=[
            {
                "chunk_id": c["source_id"],
                "text": c["content"],
                "document_id": document_id,
                "document_path": document_path,
                "chunk_index": i,
            }
            for i, c in enumerate(converted_chunks)
        ],
        entities=lightrag_entities,
        namespace_id=namespace_id,
    )

    aggregate_stats["total_chunks"] = len(converted_chunks)
    aggregate_stats["total_entities"] = len(lightrag_entities)
    aggregate_stats["total_relations"] = len(lightrag_relations)

    total_time = time.time() - total_start

    logger.info(
        "insert_prechunked_documents_complete",
        document_id=document_id,
        total_time_seconds=total_time,
        **aggregate_stats,
    )

    return {
        "document_id": document_id,
        "status": "success",
        "stats": aggregate_stats,
        "total_time_seconds": total_time,
    }


__all__ = [
    "extract_per_chunk",
    "insert_documents",
    "insert_documents_optimized",
    "insert_prechunked_documents",
]
