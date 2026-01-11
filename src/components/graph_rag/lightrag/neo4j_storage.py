"""Neo4j storage operations for LightRAG.

Sprint 55 Feature 55.6: Neo4j storage operations extracted from lightrag_wrapper.py

This module handles all Neo4j operations:
- Chunk node creation
- Entity node creation
- MENTIONED_IN relationship creation
- RELATES_TO relationship creation
- Database cleanup
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _sanitize_cypher_label(label: str) -> str:
    """Sanitize label for Cypher query safety.

    Sprint 84 Feature 84.7: Neo4j Cypher Escaping Bug Fix

    Neo4j Cypher requires backticks (`) for labels/identifiers with special characters:
    - Spaces: "Dataset Processing" → `Dataset Processing`
    - Colons: "Work: Title" → `Work: Title`
    - Slashes: "Path/To/File" → `Path/To/File`

    Args:
        label: Raw label string (e.g., entity_type, entity_name)

    Returns:
        Sanitized label ready for Cypher query

    Examples:
        >>> _sanitize_cypher_label("Dataset Processing")
        '`Dataset Processing`'
        >>> _sanitize_cypher_label("SimpleLabel")
        '`SimpleLabel`'
    """
    # Escape existing backticks to prevent injection
    sanitized = label.replace("`", "\\`")

    # Always wrap in backticks for safety (no performance cost)
    return f"`{sanitized}`"


async def store_chunks_and_provenance(
    rag: Any,
    chunks: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    namespace_id: str = "default",
) -> dict[str, int]:
    """Store chunk nodes and MENTIONED_IN relationships in Neo4j.

    Sprint 14 Feature 14.1 - Phase 5: Neo4j Integration
    Sprint 51: Added namespace_id for multi-tenant isolation.

    Creates Neo4j schema:
    - :chunk nodes with text, tokens, document_id, chunk_index, namespace_id metadata
    - :base entity nodes with namespace_id for isolation
    - MENTIONED_IN relationships from :base entities to :chunk nodes

    Args:
        rag: LightRAG instance with initialized Neo4j connection
        chunks: List of chunk metadata
        entities: List of entities in LightRAG format (with source_id=chunk_id)
        namespace_id: Namespace for multi-tenant isolation (default: "default")

    Returns:
        Dictionary with counts: chunks_created, entities_created, mentioned_in_created

    Raises:
        RuntimeError: If Neo4j storage not initialized
    """
    if not rag or not rag.chunk_entity_relation_graph:
        logger.error("neo4j_storage_not_initialized")
        raise RuntimeError("Neo4j storage not initialized")

    logger.info(
        "storing_chunks_and_provenance",
        total_chunks=len(chunks),
        total_entities=len(entities),
        namespace_id=namespace_id,
    )

    stats = {
        "chunks_created": 0,
        "entities_created": 0,
        "mentioned_in_created": 0,
    }

    try:
        # Get Neo4j driver from LightRAG
        graph = rag.chunk_entity_relation_graph
        if not hasattr(graph, "_driver"):
            logger.error("neo4j_driver_not_found")
            raise RuntimeError("Neo4j driver not available")

        async with graph._driver.session() as session:
            # Step 1: Create :chunk nodes
            for chunk in chunks:
                chunk_id = chunk["chunk_id"]
                tokens = chunk.get("tokens", chunk.get("token_count", 0))
                start_token = chunk.get("start_token", 0)
                end_token = chunk.get("end_token", tokens)

                await session.run(
                    """
                    MERGE (c:chunk {chunk_id: $chunk_id})
                    SET c.text = $text,
                        c.document_id = $document_id,
                        c.document_path = $document_path,
                        c.chunk_index = $chunk_index,
                        c.tokens = $tokens,
                        c.start_token = $start_token,
                        c.end_token = $end_token,
                        c.namespace_id = $namespace_id,
                        c.created_at = datetime()
                    """,
                    chunk_id=chunk_id,
                    text=chunk.get("text", chunk.get("content", "")),
                    document_id=chunk["document_id"],
                    document_path=chunk.get("document_path", ""),
                    chunk_index=chunk["chunk_index"],
                    tokens=tokens,
                    start_token=start_token,
                    end_token=end_token,
                    namespace_id=namespace_id,
                )
                stats["chunks_created"] += 1

            logger.info("chunk_nodes_created", count=stats["chunks_created"])

            # Step 2: Create :base entity nodes
            entities_created = 0
            entities_skipped = 0

            for entity in entities:
                entity_id = entity.get("entity_id", "")
                entity_name = entity.get("entity_name", entity_id)
                entity_type = entity.get("entity_type", "UNKNOWN")

                if not entity_id:
                    logger.warning("entity_missing_id_skipped", entity=entity)
                    entities_skipped += 1
                    continue

                # Sprint 84 Feature 84.7: Sanitize entity_type label for Cypher safety
                sanitized_type = _sanitize_cypher_label(entity_type)
                labels_str = f"base:{sanitized_type}"

                try:
                    await session.run(
                        f"""
                        MERGE (e:{labels_str} {{entity_id: $entity_id}})
                        SET e.entity_name = $entity_name,
                            e.entity_type = $entity_type,
                            e.description = $description,
                            e.source_id = $source_id,
                            e.file_path = $file_path,
                            e.chunk_index = $chunk_index,
                            e.namespace_id = $namespace_id,
                            e.created_at = datetime()
                        """,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        entity_type=entity_type,
                        description=entity.get("description", ""),
                        source_id=entity.get("source_id", ""),
                        file_path=entity.get("file_path", ""),
                        chunk_index=entity.get("chunk_index", 0),
                        namespace_id=namespace_id,
                    )
                    entities_created += 1
                except Exception as e:
                    logger.error(
                        "entity_creation_failed",
                        entity_id=entity_id,
                        error=str(e),
                    )
                    entities_skipped += 1

            stats["entities_created"] = entities_created
            logger.info(
                "entity_nodes_created",
                created=entities_created,
                skipped=entities_skipped,
            )

            # Step 3: Create MENTIONED_IN relationships
            entities_by_chunk = {}
            for entity in entities:
                chunk_id = entity.get("source_id", "")
                if chunk_id:
                    if chunk_id not in entities_by_chunk:
                        entities_by_chunk[chunk_id] = []
                    entities_by_chunk[chunk_id].append(entity["entity_id"])

            mentioned_in_count = 0
            for chunk_id, entity_ids in entities_by_chunk.items():
                await session.run(
                    """
                    UNWIND $entity_ids AS entity_id
                    MATCH (e:base {entity_id: entity_id})
                    MATCH (c:chunk {chunk_id: $chunk_id})
                    MERGE (e)-[r:MENTIONED_IN]->(c)
                    SET r.created_at = datetime(),
                        r.source_chunk_id = $chunk_id,
                        r.namespace_id = $namespace_id
                    """,
                    chunk_id=chunk_id,
                    entity_ids=entity_ids,
                    namespace_id=namespace_id,
                )
                mentioned_in_count += len(entity_ids)

            stats["mentioned_in_created"] = mentioned_in_count
            logger.info("mentioned_in_relationships_created", count=mentioned_in_count)

        logger.info(
            "chunks_and_provenance_stored_successfully",
            **stats,
        )

        return stats

    except Exception as e:
        logger.error(
            "store_chunks_and_provenance_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def store_relates_to_relationships(
    rag: Any,
    relations: list[dict[str, Any]],
    chunk_id: str,
    namespace_id: str = "default",
) -> int:
    """Store RELATES_TO relationships between entities in Neo4j.

    Sprint 34 Feature 34.1: LightRAG Schema Alignment (ADR-040)
    Sprint 51: Added namespace_id for multi-tenant isolation.

    Args:
        rag: LightRAG instance with initialized Neo4j connection
        relations: List of relations with source, target, description, strength
        chunk_id: Source chunk ID for provenance
        namespace_id: Namespace for multi-tenant isolation

    Returns:
        Number of relationships created

    Raises:
        RuntimeError: If Neo4j storage not initialized
    """
    if not relations:
        return 0

    if not rag or not rag.chunk_entity_relation_graph:
        logger.error("neo4j_storage_not_initialized")
        raise RuntimeError("Neo4j storage not initialized")

    logger.info(
        "storing_relates_to_relationships",
        total_relations=len(relations),
        chunk_id=chunk_id[:8] if len(chunk_id) > 8 else chunk_id,
    )

    try:
        graph = rag.chunk_entity_relation_graph
        if not hasattr(graph, "_driver"):
            logger.error("neo4j_driver_not_found")
            raise RuntimeError("Neo4j driver not available")

        async with graph._driver.session() as session:
            result = await session.run(
                """
                UNWIND $relations AS rel
                MATCH (e1:base {entity_name: rel.source})
                MATCH (e2:base {entity_name: rel.target})
                WHERE e1 <> e2
                MERGE (e1)-[r:RELATES_TO]->(e2)
                SET r.weight = toFloat(rel.strength) / 10.0,
                    r.description = rel.description,
                    r.source_chunk_id = $chunk_id,
                    r.namespace_id = $namespace_id,
                    r.created_at = datetime()
                RETURN count(r) AS created
                """,
                relations=[
                    {
                        "source": r["source"],
                        "target": r["target"],
                        "description": r.get("description", ""),
                        "strength": r.get("strength", 5),
                    }
                    for r in relations
                ],
                chunk_id=chunk_id,
                namespace_id=namespace_id,
            )
            record = await result.single()
            created = record["created"] if record else 0

            logger.info(
                "relates_to_relationships_created",
                count=created,
                input_relations=len(relations),
            )

            return created

    except Exception as e:
        logger.error(
            "store_relations_to_neo4j_failed",
            error=str(e),
            chunk_id=chunk_id[:8] if len(chunk_id) > 8 else chunk_id,
        )
        raise


async def clear_neo4j_database(rag: Any) -> None:
    """Clear all data from Neo4j database (for test cleanup).

    Sprint 11: Used by pytest fixtures to ensure test isolation.

    Args:
        rag: LightRAG instance with initialized Neo4j connection
    """
    if not rag or not rag.chunk_entity_relation_graph:
        logger.warning("neo4j_clear_skipped", reason="graph_not_initialized")
        return

    try:
        graph = rag.chunk_entity_relation_graph
        if hasattr(graph, "_driver"):
            async with graph._driver.session() as session:
                await session.run("MATCH (n) DETACH DELETE n")
                logger.info("neo4j_database_cleared")
        else:
            logger.warning("neo4j_clear_skipped", reason="no_driver_found")
    except Exception as e:
        logger.error("neo4j_clear_failed", error=str(e))
        # Don't raise - cleanup is best-effort


async def get_neo4j_stats(neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> dict[str, Any]:
    """Get graph statistics (entity count, relationship count).

    Args:
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password

    Returns:
        Dictionary with entity_count and relationship_count
    """
    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )

        async with driver.session() as session:
            # Get entity count (LightRAG uses 'base' label)
            entity_result = await session.run("MATCH (e:base) RETURN count(e) AS count")
            entity_record = await entity_result.single()
            entity_count = entity_record["count"] if entity_record else 0

            # Get relationship count
            rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            rel_record = await rel_result.single()
            relationship_count = rel_record["count"] if rel_record else 0

        await driver.close()

        stats = {
            "entity_count": entity_count,
            "relationship_count": relationship_count,
        }

        logger.info("neo4j_stats", **stats)
        return stats

    except Exception as e:
        logger.error("neo4j_stats_failed", error=str(e))
        return {
            "entity_count": 0,
            "relationship_count": 0,
            "error": str(e),
        }


async def check_neo4j_health(neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> bool:
    """Check health of Neo4j connection.

    Args:
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password

    Returns:
        True if healthy, False otherwise
    """
    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )

        async with driver.session() as session:
            result = await session.run("RETURN 1 AS health")
            record = await result.single()
            healthy: bool = bool(record and record["health"] == 1)

        await driver.close()

        logger.info("neo4j_health_check", healthy=healthy)
        return healthy

    except Exception as e:
        logger.error("neo4j_health_check_failed", error=str(e))
        return False


__all__ = [
    "store_chunks_and_provenance",
    "store_relates_to_relationships",
    "clear_neo4j_database",
    "get_neo4j_stats",
    "check_neo4j_health",
]
