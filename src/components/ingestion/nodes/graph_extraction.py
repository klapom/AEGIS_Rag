"""Graph Extraction Node for LangGraph Ingestion Pipeline.

Sprint 54 Feature 54.7: Extracted from langgraph_nodes.py

This module handles knowledge graph extraction and Neo4j storage:
- Extract entities/relations using ThreePhaseExtractor (SpaCy + Semantic Dedup + Gemma 3 4B)
- Store entities and relations in Neo4j via LightRAG wrapper
- Create RELATES_TO relationships between entities
- Create Section nodes for document structure
- Run Community Detection for 4-Way Hybrid RRF

Node: graph_extraction_node
"""

import asyncio
import time
from typing import Any

import structlog

from src.components.graph_rag.community_detector import get_community_detector
from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
)
from src.components.ingestion.progress_events import emit_progress
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)


async def graph_extraction_node(state: IngestionState) -> IngestionState:
    """Node 5: Extract entities/relations -> Neo4j with minimal provenance (Feature 21.6).

    Feature 21.6 Changes:
    - Handles enhanced chunks (with image_bboxes)
    - Adds minimal provenance: qdrant_point_id, has_image_annotation
    - Image page numbers for quick filtering
    - NO full BBox data (stored only in Qdrant)

    Uses ThreePhaseExtractor (SpaCy + Semantic Dedup + Gemma 3 4B)
    via LightRAG wrapper for Neo4j storage.

    Workflow:
    1. Get enhanced chunks from state
    2. Add minimal provenance to metadata
    3. Extract entities/relations via LightRAG
    4. Store in Neo4j graph database

    Args:
        state: Current ingestion state

    Returns:
        Updated state with graph extraction results

    Raises:
        IngestionError: If graph extraction fails

    Example:
        >>> state = await graph_extraction_node(state)
        >>> state["graph_status"]
        'completed'
    """
    graph_node_start = time.perf_counter()

    logger.info(
        "TIMING_graph_extraction_start",
        stage="graph_extraction",
        document_id=state["document_id"],
        chunks_available=len(state.get("chunks", [])),
        embedding_status=state.get("embedding_status"),
        chunking_status=state.get("chunking_status"),
    )

    state["graph_status"] = "running"
    state["graph_start_time"] = time.time()

    try:
        # Get enhanced chunks (Feature 21.6: list of {chunk, image_bboxes})
        chunk_data_list = state.get("chunks", [])
        if not chunk_data_list:
            raise IngestionError(
                document_id=state.get("document_id", "unknown"),
                reason="No chunks for graph extraction (chunks list is empty)",
            )

        # Get embedded chunk IDs (from embedding_node)
        embedded_chunk_ids = state.get("embedded_chunk_ids", [])

        # Get LightRAG wrapper
        lightrag = await get_lightrag_wrapper_async()

        # Sprint 42: Convert chunks to pre-chunked format with Qdrant chunk_ids
        # This ensures chunk IDs are aligned between Qdrant and Neo4j
        prechunked_docs = []
        for idx, chunk_data in enumerate(chunk_data_list):
            # Handle both enhanced and legacy chunk formats
            chunk = chunk_data["chunk"] if isinstance(chunk_data, dict) else chunk_data

            # Get chunk ID (from embedded_chunk_ids if available)
            chunk_id = embedded_chunk_ids[idx] if idx < len(embedded_chunk_ids) else f"chunk_{idx}"
            chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)

            prechunked_docs.append(
                {
                    "chunk_id": chunk_id,  # Sprint 42: Use Qdrant's chunk_id
                    "text": chunk_text,
                    "chunk_index": idx,
                }
            )

        # Sprint 42: Use insert_prechunked_documents to preserve chunk IDs
        lightrag_insert_start = time.perf_counter()
        total_chunks = len(prechunked_docs)
        logger.info(
            "TIMING_lightrag_insert_start",
            stage="graph_extraction",
            substage="lightrag_prechunked_insert",
            chunk_count=total_chunks,
            document_id=state["document_id"],
        )

        # Sprint 51: Emit progress event for entity extraction start
        await emit_progress(
            document_id=state["document_id"],
            phase="entity_extraction",
            current=0,
            total=total_chunks,
            message=f"Extracting entities from {total_chunks} chunks...",
            details={"stage": "lightrag_insert"},
        )

        # Sprint 76 Feature 76.1 (TD-084): Use namespace_id from state
        namespace_id = state.get("namespace_id", "default")

        graph_stats = await lightrag.insert_prechunked_documents(
            chunks=prechunked_docs,
            document_id=state["document_id"],
            document_path=state["document_path"],
            namespace_id=namespace_id,  # Multi-tenant isolation
        )

        # Sprint 51: Emit progress event for entity extraction complete
        entities_extracted = graph_stats.get("stats", {}).get("total_entities", 0)
        await emit_progress(
            document_id=state["document_id"],
            phase="entity_extraction",
            current=total_chunks,
            total=total_chunks,
            message=f"Extracted {entities_extracted} entities from {total_chunks} chunks",
            details={"total_entities": entities_extracted, "total_relations": 0},
        )
        lightrag_insert_end = time.perf_counter()
        lightrag_insert_ms = (lightrag_insert_end - lightrag_insert_start) * 1000

        logger.info(
            "TIMING_lightrag_insert_complete",
            stage="graph_extraction",
            substage="lightrag_prechunked_insert",
            duration_ms=round(lightrag_insert_ms, 2),
            chunks_processed=len(prechunked_docs),
            entities_extracted=graph_stats.get("stats", {}).get("total_entities", 0),
            relations_extracted=graph_stats.get("stats", {}).get("total_relations", 0),
        )

        # Sprint 33 FIX: Wait for Neo4j to commit the entities before querying
        # This prevents race conditions where MENTIONED_IN isn't visible yet
        await asyncio.sleep(1.0)
        logger.info(
            "neo4j_commit_wait_complete",
            stage="graph_extraction",
            wait_seconds=1.0,
        )

        # Sprint 34 Feature 34.1 & 34.2: Extract and store RELATES_TO relationships
        # After LightRAG stores entities, extract relations between them
        relation_extraction_start = time.perf_counter()
        total_relations_created = 0

        logger.info(
            "TIMING_relation_extraction_start",
            stage="graph_extraction",
            substage="relation_extraction",
            chunks_to_process=len(prechunked_docs),
        )

        # Import RelationExtractor
        from src.components.graph_rag.relation_extractor import RelationExtractor

        relation_extractor = RelationExtractor()

        # Sprint 33 FIX: Query Neo4j for entities per chunk
        # Get Neo4j client to query entities associated with each chunk via MENTIONED_IN
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        neo4j_client = get_neo4j_client()

        # Sprint 42: Query Neo4j for chunks that were just stored by insert_prechunked_documents
        # The chunk_ids should now match between Qdrant and Neo4j (unified ID)
        document_id = state["document_id"]
        chunks_query = """
        MATCH (c:chunk {document_id: $document_id})
        RETURN c.chunk_id AS chunk_id, c.text AS chunk_text
        ORDER BY c.chunk_index
        """
        try:
            neo4j_chunks = await neo4j_client.execute_read(
                chunks_query, {"document_id": document_id}
            )
            logger.info(
                "neo4j_chunks_queried_for_relations",
                document_id=document_id,
                chunks_found=len(neo4j_chunks),
            )
        except Exception as e:
            logger.error(
                "failed_to_query_neo4j_chunks",
                document_id=document_id,
                error=str(e),
            )
            neo4j_chunks = []

        # Sprint 51: Emit progress event for relation extraction start
        relation_chunks_total = len(neo4j_chunks)
        await emit_progress(
            document_id=document_id,
            phase="relation_extraction",
            current=0,
            total=relation_chunks_total,
            message=f"Starting relation extraction for {relation_chunks_total} chunks...",
            details={"stage": "relation_extraction_start"},
        )

        # Process each chunk from Neo4j: extract relations and store to Neo4j
        for chunk_idx, chunk_data in enumerate(neo4j_chunks):
            chunk_text = chunk_data.get("chunk_text", "")
            chunk_id = chunk_data.get("chunk_id", "")

            if not chunk_id or not chunk_text:
                continue

            # Sprint 33 FIX: Query Neo4j for entities that MENTIONED_IN this chunk
            # This replaces the broken empty entities list
            try:
                entity_query = """
                MATCH (e:base)-[:MENTIONED_IN]->(c:chunk {chunk_id: $chunk_id})
                RETURN e.entity_name AS name, e.entity_type AS type
                """
                entity_results = await neo4j_client.execute_read(
                    entity_query, {"chunk_id": chunk_id}
                )
                entities = [
                    {"name": r["name"], "type": r.get("type", "UNKNOWN")}
                    for r in entity_results
                    if r.get("name")  # Filter out None entity names
                ]

                logger.info(
                    "chunk_entities_queried",
                    chunk_id=chunk_id[:8] if len(chunk_id) > 8 else chunk_id,
                    entities_found=len(entities),
                    entity_names=[e["name"] for e in entities[:5]],  # Log first 5
                )

            except Exception as e:
                logger.warning(
                    "chunk_entity_query_failed",
                    chunk_id=chunk_id[:8] if len(chunk_id) > 8 else chunk_id,
                    error=str(e),
                )
                entities = []

            # Need at least 2 entities to find relations between them
            if len(entities) < 2:
                logger.debug(
                    "skipping_relation_extraction",
                    chunk_id=chunk_id[:8] if len(chunk_id) > 8 else chunk_id,
                    reason="less_than_2_entities",
                    entities_found=len(entities),
                )
                continue

            try:
                # Extract relations between entities in this chunk
                relations = await relation_extractor.extract(chunk_text, entities)

                # Store relations to Neo4j with RELATES_TO relationships
                # Sprint 76 Feature 76.1 (TD-084): Use namespace_id from state
                if relations:
                    relations_created = await lightrag._store_relations_to_neo4j(
                        relations=relations,
                        chunk_id=chunk_id,
                        namespace_id=namespace_id,  # Multi-tenant isolation from state
                    )
                    total_relations_created += relations_created

                    logger.debug(
                        "chunk_relations_stored",
                        chunk_id=chunk_id[:8],
                        relations_extracted=len(relations),
                        relations_created=relations_created,
                    )

                # Sprint 51: Emit progress event with extracted count
                await emit_progress(
                    document_id=document_id,
                    phase="relation_extraction",
                    current=chunk_idx + 1,
                    total=relation_chunks_total,
                    message=f"Extracted {len(relations) if relations else 0} relations (chunk {chunk_idx + 1}/{relation_chunks_total})",
                    details={
                        "chunk_id": chunk_id[:8] if chunk_id else "unknown",
                        "relations": len(relations) if relations else 0,
                        "total_entities": entities_extracted,  # From entity extraction phase
                        "total_relations": total_relations_created,
                    },
                )

            except Exception as e:
                logger.warning(
                    "chunk_relation_extraction_failed",
                    chunk_id=chunk_id[:8],
                    error=str(e),
                    action="continuing_with_next_chunk",
                )
                continue

        relation_extraction_end = time.perf_counter()
        relation_extraction_ms = (relation_extraction_end - relation_extraction_start) * 1000

        # Store relations count in state
        state["relations_count"] = total_relations_created

        logger.info(
            "TIMING_relation_extraction_complete",
            stage="graph_extraction",
            substage="relation_extraction",
            duration_ms=round(relation_extraction_ms, 2),
            chunks_processed=len(neo4j_chunks),  # Sprint 41: Use actual Neo4j chunks count
            total_relations_created=total_relations_created,
        )

        # Sprint 51: Emit relation extraction complete summary
        await emit_progress(
            document_id=document_id,
            phase="relation_extraction",
            current=relation_chunks_total,
            total=relation_chunks_total,
            message=f"Extracted {total_relations_created} relations total",
            details={
                "total_entities": entities_extracted,
                "total_relations": total_relations_created,
                "chunks_processed": len(neo4j_chunks),
            },
        )

        # Sprint 32 Feature 32.4: Create Section nodes in Neo4j (ADR-039)
        # Extract sections and chunks from state for section node creation
        sections = state.get("sections", [])
        adaptive_chunks = state.get("adaptive_chunks", [])

        section_nodes_ms = 0.0
        if sections and adaptive_chunks:
            try:
                section_nodes_start = time.perf_counter()
                logger.info(
                    "TIMING_section_nodes_start",
                    stage="graph_extraction",
                    substage="section_nodes",
                    document_id=state["document_id"],
                    sections_count=len(sections),
                    chunks_count=len(adaptive_chunks),
                )

                # Import Neo4j client
                from src.components.graph_rag.neo4j_client import get_neo4j_client

                neo4j_client = get_neo4j_client()

                # Create section nodes with hierarchical relationships
                section_stats = await neo4j_client.create_section_nodes(
                    document_id=state["document_id"],
                    sections=sections,
                    chunks=adaptive_chunks,
                )

                section_nodes_end = time.perf_counter()
                section_nodes_ms = (section_nodes_end - section_nodes_start) * 1000

                logger.info(
                    "TIMING_section_nodes_complete",
                    stage="graph_extraction",
                    substage="section_nodes",
                    duration_ms=round(section_nodes_ms, 2),
                    document_id=state["document_id"],
                    sections_created=section_stats["sections_created"],
                    has_section_rels=section_stats["has_section_rels"],
                    contains_chunk_rels=section_stats["contains_chunk_rels"],
                    defines_entity_rels=section_stats["defines_entity_rels"],
                )

                # Store section stats in state for analytics
                state["section_node_stats"] = section_stats

            except Exception as e:
                # Log error but don't fail entire ingestion (section nodes are optional enhancement)
                logger.warning(
                    "section_nodes_creation_failed",
                    document_id=state["document_id"],
                    error=str(e),
                    note="Continuing ingestion without section nodes",
                )
                state["section_node_stats"] = {"error": str(e)}
        else:
            logger.info(
                "section_nodes_skipped",
                document_id=state["document_id"],
                reason="no_sections_or_chunks_available",
                has_sections=bool(sections),
                has_chunks=bool(adaptive_chunks),
            )

        # =========================================================================
        # Sprint 42: Automatic Community Detection for 4-Way Hybrid RRF (TD-057)
        # Run Community Detection only if RELATES_TO relationships were created
        # This enables Global Graph Retrieval via Community -> Entity -> Chunk expansion
        # =========================================================================
        community_detection_stats: dict[str, Any] = {}
        community_detection_ms = 0.0

        relations_created = state.get("relations_count", 0)
        if relations_created > 0:
            try:
                community_start = time.perf_counter()
                logger.info(
                    "community_detection_starting",
                    document_id=state["document_id"],
                    relations_count=relations_created,
                )

                # Sprint 51: Emit progress event for community detection
                await emit_progress(
                    document_id=state["document_id"],
                    phase="community_detection",
                    current=0,
                    total=1,
                    message="Detecting entity communities...",
                    details={"relations_count": relations_created},
                )

                # Use singleton CommunityDetector (handles GDS vs NetworkX fallback)
                community_detector = get_community_detector()
                communities = await community_detector.detect_communities()

                community_detection_ms = (time.perf_counter() - community_start) * 1000

                community_detection_stats = {
                    "communities_detected": len(communities),
                    "algorithm": community_detector.algorithm,
                    "resolution": community_detector.resolution,
                    "min_size": community_detector.min_size,
                    "execution_time_ms": round(community_detection_ms, 2),
                }

                # Calculate total entities assigned to communities
                total_entities_in_communities = sum(c.size for c in communities)

                logger.info(
                    "TIMING_community_detection_complete",
                    stage="graph_extraction",
                    substage="community_detection",
                    duration_ms=round(community_detection_ms, 2),
                    document_id=state["document_id"],
                    communities_detected=len(communities),
                    entities_in_communities=total_entities_in_communities,
                    algorithm=community_detector.algorithm,
                )

            except Exception as e:
                # Log error but don't fail ingestion (community detection is optional enhancement)
                logger.warning(
                    "community_detection_failed",
                    document_id=state["document_id"],
                    error=str(e),
                    note="Continuing ingestion without community detection - 4-Way RRF Global will be unavailable",
                )
                community_detection_stats = {"error": str(e)}
        else:
            logger.info(
                "community_detection_skipped",
                document_id=state["document_id"],
                reason="no_relations_created",
                note="4-Way RRF Global retrieval will be unavailable for this document",
            )

        # Store community detection stats in state
        state["community_detection_stats"] = community_detection_stats

        # Store statistics
        state["entities"] = []  # Full entities stored in Neo4j
        state["relations"] = []  # Full relations stored in Neo4j
        state["graph_status"] = "completed"
        state["graph_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        # Extract stats from nested structure (Sprint 32 Fix)
        stats = graph_stats.get("stats", {})
        graph_node_end = time.perf_counter()
        total_graph_ms = (graph_node_end - graph_node_start) * 1000

        logger.info(
            "TIMING_graph_extraction_complete",
            stage="graph_extraction",
            duration_ms=round(total_graph_ms, 2),
            document_id=state["document_id"],
            total_entities=stats.get("total_entities", 0),
            total_relations=stats.get("total_relations", 0),
            total_chunks=stats.get("total_chunks", 0),
            chunks_with_images=sum(
                1
                for chunk_data in chunk_data_list
                if isinstance(chunk_data, dict) and chunk_data.get("image_bboxes")
            ),
            section_nodes_created=state.get("section_node_stats", {}).get("sections_created", 0),
            communities_detected=community_detection_stats.get("communities_detected", 0),
            timing_breakdown={
                "lightrag_insert_ms": round(lightrag_insert_ms, 2),
                "section_nodes_ms": round(section_nodes_ms, 2),
                "community_detection_ms": round(community_detection_ms, 2),
            },
        )

        # Sprint 51: Final summary with total entities and relations
        total_entities = stats.get("total_entities", 0)
        total_relations_final = state.get("relations_count", 0)
        await emit_progress(
            document_id=state["document_id"],
            phase="graph_complete",
            current=1,
            total=1,
            message=f"Extracted a total of {total_entities} entities and {total_relations_final} relations",
            details={
                "total_entities": total_entities,
                "total_relations": total_relations_final,
                "communities": community_detection_stats.get("communities_detected", 0),
            },
        )

        return state

    except Exception as e:
        logger.error("node_graph_extraction_error", document_id=state["document_id"], error=str(e))
        add_error(state, "graph_extraction", str(e), "error")
        state["graph_status"] = "failed"
        state["graph_end_time"] = time.time()
        raise
