"""Graph extraction pipeline — entity/relation extraction, dedup, hygiene, and Neo4j storage.

Sprint 128: Extracted from lightrag/ingestion.py to eliminate LightRAG dependency.
All extraction logic is 100% AegisRAG code — only the storage path changed
(Neo4jClient instead of rag._driver).

This module handles:
- Per-chunk entity/relation extraction via ExtractionService (3-Rank Cascade)
- Multi-criteria entity deduplication
- Relation deduplication
- KG hygiene validation (self-loops, missing evidence)
- DSPy training data collection
- Extraction metrics tracking
- Neo4j storage via Neo4jClient (chunks, entities, MENTIONED_IN relationships)
"""

import time
from typing import Any

import structlog

from src.components.graph_rag.extraction_factory import create_extraction_pipeline_from_config
from src.components.graph_rag.extraction_metrics import (
    create_metrics_from_extraction,
    log_extraction_metrics,
)
from src.components.graph_rag.kg_hygiene import KGHygieneService
from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.components.graph_rag.relation_deduplicator import create_relation_deduplicator_from_config
from src.components.graph_rag.semantic_deduplicator import create_deduplicator_from_config
from src.components.domain_training.training_data_collector import get_training_data_collector
from src.core.config import settings
from src.monitoring.metrics import record_deduplication_detail, record_extraction_by_type

logger = structlog.get_logger(__name__)

# Sprint 129.2: Metadata artifact blocklist
# Document structure tokens that the LLM sometimes extracts as entities.
# Case-insensitive matching. Configurable via AEGIS_ENTITY_BLOCKLIST env var.
import os

_DEFAULT_ENTITY_BLOCKLIST = {
    "clean_text",
    "doc type",
    "document",
    "chunk",
    "text",
    "content",
    "file",
    "section",
    "paragraph",
    "title",
    "metadata",
    "header",
    "footer",
    "abstract",
    "summary",
    "reference",
    "bibliography",
    "appendix",
    "table of contents",
}

_env_blocklist = os.environ.get("AEGIS_ENTITY_BLOCKLIST", "")
ENTITY_BLOCKLIST: set[str] = (
    {name.strip().lower() for name in _env_blocklist.split(",") if name.strip()}
    if _env_blocklist
    else _DEFAULT_ENTITY_BLOCKLIST
)


def filter_metadata_artifacts(
    entities: list[dict],
    relations: list[dict],
    blocklist: set[str] | None = None,
) -> tuple[list[dict], list[dict], int, int]:
    """Remove metadata artifacts from extracted entities and relations.

    Sprint 129.2: Filters out document structure tokens (clean_text, Doc Type, etc.)
    that the LLM incorrectly extracts as domain entities.

    Args:
        entities: List of entity dicts (with "name" or "entity_name" key)
        relations: List of relation dicts (with "subject"/"object" or "source"/"target" keys)
        blocklist: Optional custom blocklist (defaults to ENTITY_BLOCKLIST)

    Returns:
        Tuple of (filtered_entities, filtered_relations, entities_removed, relations_removed)
    """
    if blocklist is None:
        blocklist = ENTITY_BLOCKLIST

    if not blocklist:
        return entities, relations, 0, 0

    # Filter entities
    filtered_entities = []
    removed_entity_names: set[str] = set()
    for entity in entities:
        name = entity.get("name", entity.get("entity_name", "")).strip()
        if name.lower() in blocklist:
            removed_entity_names.add(name)
        else:
            filtered_entities.append(entity)

    # Filter relations where BOTH subject and object are artifacts
    filtered_relations = []
    relations_removed = 0
    for rel in relations:
        subj = rel.get("subject", rel.get("source", "")).strip().lower()
        obj = rel.get("object", rel.get("target", "")).strip().lower()
        if subj in blocklist and obj in blocklist:
            relations_removed += 1
        else:
            filtered_relations.append(rel)

    entities_removed = len(entities) - len(filtered_entities)

    if entities_removed > 0 or relations_removed > 0:
        logger.info(
            "metadata_artifacts_filtered",
            entities_removed=entities_removed,
            relations_removed=relations_removed,
            removed_names=sorted(removed_entity_names)[:10],
        )

    return filtered_entities, filtered_relations, entities_removed, relations_removed


async def extract_and_store_entities(
    chunks: list[dict[str, Any]],
    document_id: str,
    document_path: str = "",
    namespace_id: str = "default",
    domain_id: str | None = None,
) -> dict[str, Any]:
    """Extract entities/relations from pre-chunked documents and store in Neo4j.

    Sprint 128: Direct replacement for lightrag/ingestion.py:insert_prechunked_documents().
    Removes the redundant ainsert_custom_kg() call that caused 92% overhead and
    overwrote typed relations with generic RELATED_TO.

    Pipeline:
    1. Extract entities/relations per chunk via ExtractionService (3-Rank Cascade)
    2. Deduplicate entities (multi-criteria)
    3. Deduplicate relations
    4. KG hygiene validation (filter self-loops)
    5. DSPy training data collection (optional)
    6. Store chunks + entities + MENTIONED_IN in Neo4j via Neo4jClient

    Args:
        chunks: List of pre-chunked documents with chunk_id, text, chunk_index
        document_id: Source document ID for provenance tracking
        document_path: Source document path for attribution
        namespace_id: Namespace for multi-tenant isolation
        domain_id: Domain for DSPy-optimized prompts

    Returns:
        Result dict with document_id, status, stats, total_time_seconds
    """
    logger.info(
        "extract_and_store_start",
        chunk_count=len(chunks),
        document_id=document_id,
        namespace_id=namespace_id,
        domain_id=domain_id,
    )

    total_start = time.time()
    aggregate_stats = {
        "total_chunks": 0,
        "total_entities": 0,
        "total_relations": 0,
        "total_mentioned_in": 0,
    }

    extractor = create_extraction_pipeline_from_config()

    all_entities: list[dict[str, Any]] = []
    all_relations: list[dict[str, Any]] = []
    converted_chunks: list[dict[str, Any]] = []

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", f"chunk_{chunk.get('chunk_index', 0)}")
        chunk_text = chunk.get("text", "")
        chunk_index = chunk.get("chunk_index", 0)

        if not chunk_text:
            logger.warning("empty_chunk_skipped", chunk_id=chunk_id)
            continue

        logger.info(
            "extracting_chunk",
            chunk_id=chunk_id[:16] if len(chunk_id) > 16 else chunk_id,
            chunk_index=chunk_index,
            text_length=len(chunk_text),
        )

        try:
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
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "document_id": document_id,
                    "document_path": document_path,
                    "chunk_index": chunk_index,
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

    # Sprint 129.2: Filter metadata artifacts before dedup
    all_entities, all_relations, artifacts_removed, rel_artifacts_removed = (
        filter_metadata_artifacts(all_entities, all_relations)
    )

    # Apply entity deduplication
    entities_before_dedup = len(all_entities)
    entity_mapping: dict[str, str] = {}

    if settings.enable_multi_criteria_dedup and all_entities:
        try:
            deduplicator = create_deduplicator_from_config(settings)
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
    relations_before_dedup = len(all_relations)
    if settings.enable_relation_dedup and all_relations:
        try:
            relation_deduplicator = create_relation_deduplicator_from_config(settings)
            if relation_deduplicator:
                deduplicated_relations = relation_deduplicator.deduplicate(
                    all_relations,
                    entity_mapping=entity_mapping,
                )

                logger.info(
                    "relation_deduplication_complete",
                    document_id=document_id,
                    relations_before=relations_before_dedup,
                    relations_after=len(deduplicated_relations),
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
        model=settings.extraction_llm_model,
    )

    # KG Hygiene Validation — filter self-loops, missing evidence
    hygiene_service = KGHygieneService()
    validated_relations = []
    hygiene_violations = 0

    for relation in all_relations:
        is_valid, reason = hygiene_service.validate_relation(
            relation,
            require_evidence=False,
        )
        if is_valid:
            validated_relations.append(relation)
        else:
            hygiene_violations += 1
            logger.debug(
                "relation_hygiene_violation",
                source=relation.get("source_entity", "")[:20],
                target=relation.get("target_entity", "")[:20],
                reason=reason,
            )

    if hygiene_violations > 0:
        logger.info(
            "kg_hygiene_validation_complete",
            document_id=document_id,
            relations_before=len(all_relations),
            relations_after=len(validated_relations),
            violations_filtered=hygiene_violations,
        )
        all_relations = validated_relations

    # Extraction Metrics
    extraction_time_ms = (time.time() - total_start) * 1000
    extraction_metrics = create_metrics_from_extraction(
        entities=all_entities,
        relations=all_relations,
        spacy_count=0,
        llm_count=len(all_entities),
        duplicates_removed=entities_before_dedup - len(all_entities),
        llm_latency_ms=extraction_time_ms,
        languages=[],
        extraction_method="llm_cascade",
        cascade_rank=1,
        gleaning_rounds=0,
    )

    log_extraction_metrics(
        metrics=extraction_metrics,
        document_id=document_id,
    )

    # DSPy Training Data Collection
    if settings.enable_dspy_training_collection:
        try:
            training_collector = get_training_data_collector()

            for chunk in chunks:
                chunk_id = chunk.get("chunk_id", "")
                chunk_text = chunk.get("text", "")
                chunk_entities = [e for e in all_entities if e.get("chunk_id") == chunk_id]
                chunk_relations = [r for r in all_relations if r.get("chunk_id") == chunk_id]

                if chunk_entities and chunk_relations:
                    training_collector.collect(
                        text=chunk_text,
                        entities=chunk_entities,
                        relations=chunk_relations,
                        metadata={
                            "doc_type": "pdf_text",
                            "language": "en",
                            "document_id": document_id,
                            "chunk_id": chunk_id,
                            "domain": domain_id,
                        },
                    )
        except Exception as e:
            logger.warning(
                "dspy_training_collection_failed",
                document_id=document_id,
                error=str(e),
            )

    # Convert entities to storage format (entity_id = entity_name, source_id = chunk_id)
    storage_entities = []
    for entity in all_entities:
        storage_entities.append(
            {
                "entity_id": entity.get(
                    "name", entity.get("entity_name", entity.get("entity_id", ""))
                ),
                "entity_name": entity.get("name", entity.get("entity_name", "")),
                "entity_type": entity.get("type", entity.get("entity_type", "UNKNOWN")),
                "entity_sub_type": entity.get("sub_type", entity.get("entity_sub_type")),
                "description": entity.get("description", ""),
                "source_id": entity.get("chunk_id", ""),
                "file_path": document_id,
                "chunk_index": entity.get("chunk_index", 0),
                "domain_id": domain_id,
            }
        )

    # Store chunks + entities + MENTIONED_IN in Neo4j (NO ainsert_custom_kg!)
    neo4j_client = get_neo4j_client()
    provenance_stats = await neo4j_client.store_chunks_and_provenance(
        chunks=converted_chunks,
        entities=storage_entities,
        namespace_id=namespace_id,
    )
    aggregate_stats["total_mentioned_in"] = provenance_stats.get("mentioned_in_created", 0)

    # Store relations grouped by chunk_id
    total_relations_stored = 0
    relations_by_chunk: dict[str, list[dict[str, Any]]] = {}
    for rel in all_relations:
        cid = rel.get("chunk_id", "unknown")
        relations_by_chunk.setdefault(cid, []).append(rel)

    for cid, rels in relations_by_chunk.items():
        stored = await neo4j_client.store_relations(
            relations=rels,
            chunk_id=cid,
            namespace_id=namespace_id,
        )
        total_relations_stored += stored

    logger.info(
        "relations_storage_complete",
        document_id=document_id,
        relations_extracted=len(all_relations),
        relations_stored=total_relations_stored,
        chunks_with_relations=len(relations_by_chunk),
    )

    aggregate_stats["total_chunks"] = len(converted_chunks)
    aggregate_stats["total_entities"] = len(storage_entities)
    aggregate_stats["total_relations"] = len(all_relations)

    total_time = time.time() - total_start

    logger.info(
        "extract_and_store_complete",
        document_id=document_id,
        total_time_seconds=round(total_time, 1),
        **aggregate_stats,
    )

    return {
        "document_id": document_id,
        "status": "success",
        "stats": aggregate_stats,
        "total_time_seconds": total_time,
    }
