"""Neo4j Client Wrapper with Connection Pooling and Error Handling.

This module provides a production-ready wrapper around the Neo4j driver with:
- Connection pooling
- Automatic retry logic
- Health checks
- Async context manager support
- Query execution methods
"""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError

logger = structlog.get_logger(__name__)

# Constants
DEFAULT_POOL_SIZE = 10
DEFAULT_CONNECTION_TIMEOUT = 30
DEFAULT_MAX_RETRY_ATTEMPTS = 3


class Neo4jClient:
    """Production-ready Neo4j client with connection pooling and error handling."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        max_connection_pool_size: int = DEFAULT_POOL_SIZE,
        connection_timeout: int = DEFAULT_CONNECTION_TIMEOUT,
    ) -> None:
        """Initialize Neo4j client wrapper.

        Args:
            uri: Neo4j connection URI (default: from settings)
            user: Neo4j username (default: from settings)
            password: Neo4j password (default: from settings)
            database: Neo4j database name (default: from settings)
            max_connection_pool_size: Maximum connection pool size (default: 10)
            connection_timeout: Connection timeout in seconds (default: 30)
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password.get_secret_value()
        self.database = database or settings.neo4j_database
        self.max_connection_pool_size = max_connection_pool_size
        self.connection_timeout = connection_timeout

        self._driver: AsyncDriver | None = None

        logger.info(
            "Initializing Neo4j client",
            uri=self.uri,
            user=self.user,
            database=self.database,
            max_pool_size=self.max_connection_pool_size,
        )

    @property
    def driver(self) -> AsyncDriver:
        """Get Neo4j driver (lazy initialization).

        Returns:
            AsyncDriver instance

        Raises:
            DatabaseConnectionError: If driver initialization fails
        """
        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_pool_size=self.max_connection_pool_size,
                    connection_timeout=self.connection_timeout,
                )
                logger.info("Neo4j driver initialized")
            except Exception as e:
                logger.error("Failed to initialize Neo4j driver", error=str(e))
                raise DatabaseConnectionError(
                    "Neo4j", f"Failed to initialize Neo4j driver: {e}"
                ) from e
        return self._driver

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ServiceUnavailable),
    )
    async def health_check(self) -> bool:
        """Check if Neo4j server is healthy.

        Returns:
            True if server is healthy

        Raises:
            DatabaseConnectionError: If connection fails after retries
        """
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 AS health")
                record = await result.single()
                if record and record["health"] == 1:
                    logger.info("Neo4j health check passed")
                    return True
                return False
        except ServiceUnavailable:
            # Let tenacity retry on ServiceUnavailable
            raise
        except Exception as e:
            logger.error("Neo4j health check failed", error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Neo4j health check failed: {e}") from e

    async def verify_connectivity(self) -> bool:
        """Verify Neo4j connection is active.

        Sprint 107 Issue 107.0A: Added method to fix Memory Management UI.

        Uses Neo4j driver's native verify_connectivity() for lightweight check.

        Returns:
            True if connection is active, False otherwise
        """
        try:
            await self.driver.verify_connectivity()
            logger.debug("Neo4j connectivity verified")
            return True
        except Exception as e:
            logger.warning("Neo4j connectivity check failed", error=str(e))
            return False

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, Neo4jError)),
    )
    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters (default: None)
            database: Database name (default: from settings)

        Returns:
            list of result records as dictionaries

        Raises:
            DatabaseConnectionError: If query execution fails
        """
        import time

        query_start = time.perf_counter()
        db = database or self.database
        params = parameters or {}

        try:
            async with self.driver.session(database=db) as session:
                result = await session.run(query, params)
                records = await result.data()

                query_duration_ms = (time.perf_counter() - query_start) * 1000
                logger.debug(
                    "TIMING_neo4j_query",
                    stage="neo4j",
                    duration_ms=round(query_duration_ms, 2),
                    query_preview=query[:100],
                    record_count=len(records),
                )
                return records
        except (ServiceUnavailable, Neo4jError):
            # Let tenacity retry on these exceptions
            raise
        except Exception as e:
            logger.error("Query execution failed", query=query[:100], error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Query execution failed: {e}") from e

    async def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read-only Cypher query and return results.

        Alias for execute_query for consistency with Neo4j terminology.

        Args:
            query: Cypher query string
            parameters: Query parameters (default: None)
            database: Database name (default: from settings)

        Returns:
            list of result records as dictionaries

        Raises:
            DatabaseConnectionError: If query execution fails
        """
        return await self.execute_query(query, parameters, database)

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, Neo4jError)),
    )
    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Execute a write transaction.

        Args:
            query: Cypher write query string
            parameters: Query parameters (default: None)
            database: Database name (default: from settings)

        Returns:
            Dictionary with transaction summary

        Raises:
            DatabaseConnectionError: If write transaction fails
        """
        import time

        write_start = time.perf_counter()
        db = database or self.database
        params = parameters or {}

        try:
            async with self.driver.session(database=db) as session:
                result = await session.run(query, params)
                summary = await result.consume()

                write_duration_ms = (time.perf_counter() - write_start) * 1000
                result_summary = {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                }

                logger.debug(
                    "TIMING_neo4j_write",
                    stage="neo4j",
                    duration_ms=round(write_duration_ms, 2),
                    query_preview=query[:100],
                    nodes_created=result_summary["nodes_created"],
                    relationships_created=result_summary["relationships_created"],
                )

                return result_summary
        except (ServiceUnavailable, Neo4jError):
            # Let tenacity retry on these exceptions
            raise
        except Exception as e:
            logger.error("Write transaction failed", query=query[:100], error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Write transaction failed: {e}") from e

    async def create_temporal_indexes(self) -> dict[str, bool]:
        """Create indexes on temporal properties for performance.

        Returns:
            Dictionary with index creation status

        Raises:
            DatabaseConnectionError: If index creation fails
        """
        indexes = {
            "entity_valid_from": "CREATE INDEX entity_valid_from IF NOT EXISTS FOR (e:base) ON (e.valid_from)",
            "entity_valid_to": "CREATE INDEX entity_valid_to IF NOT EXISTS FOR (e:base) ON (e.valid_to)",
            "entity_transaction_from": "CREATE INDEX entity_transaction_from IF NOT EXISTS FOR (e:base) ON (e.transaction_from)",
            "entity_transaction_to": "CREATE INDEX entity_transaction_to IF NOT EXISTS FOR (e:base) ON (e.transaction_to)",
            "entity_version_id": "CREATE INDEX entity_version_id IF NOT EXISTS FOR (e:base) ON (e.version_id)",
            "entity_version_number": "CREATE INDEX entity_version_number IF NOT EXISTS FOR (e:base) ON (e.version_number)",
            # Sprint 125 Feature 125.9b: Domain-aware indexing
            "entity_domain_id": "CREATE INDEX entity_domain_id IF NOT EXISTS FOR (e:base) ON (e.domain_id)",
            "chunk_domain_id": "CREATE INDEX chunk_domain_id IF NOT EXISTS FOR (c:chunk) ON (c.domain_id)",
        }

        results = {}
        for index_name, query in indexes.items():
            try:
                await self.execute_write(query)
                results[index_name] = True
                logger.info("Created temporal index", index_name=index_name)
            except Exception as e:
                logger.warning("Failed to create index", index_name=index_name, error=str(e))
                results[index_name] = False

        return results

    async def create_section_nodes(
        self,
        document_id: str,
        sections: list[Any],
        chunks: list[Any],
    ) -> dict[str, int]:
        """Create Section nodes with hierarchical relationships (Sprint 32 Feature 32.4).

        Sprint 33 Performance Fix: Uses batched UNWIND queries for 5-10x speedup.
        Sprint 62 Feature 62.6: Adds HAS_SUBSECTION hierarchical relationships.

        Implements ADR-039 section-aware graph schema:
        - Creates Section nodes with heading, page_no, order, bbox
        - Creates Document-[:HAS_SECTION]->Section relationships
        - Creates Section-[:CONTAINS_CHUNK]->Chunk relationships
        - Creates Section-[:DEFINES]->Entity relationships (for entities in section)
        - Creates Section-[:HAS_SUBSECTION]->Section relationships (parent-child hierarchy)

        Args:
            document_id: Source document ID
            sections: List of SectionMetadata from extract_section_hierarchy()
            chunks: List of AdaptiveChunk from adaptive_section_chunking()

        Returns:
            Dictionary with creation statistics:
            - sections_created: Number of Section nodes created
            - has_section_rels: Number of HAS_SECTION relationships
            - contains_chunk_rels: Number of CONTAINS_CHUNK relationships
            - defines_entity_rels: Number of DEFINES relationships
            - hierarchy_rels: Number of HAS_SUBSECTION relationships (Sprint 62.6)

        Example:
            >>> client = get_neo4j_client()
            >>> stats = await client.create_section_nodes(
            ...     document_id="doc123",
            ...     sections=[SectionMetadata(...)],
            ...     chunks=[AdaptiveChunk(...)]
            ... )
            >>> stats["sections_created"]
            5
            >>> stats["hierarchy_rels"]
            3
        """
        import time

        batch_start_time = time.time()

        logger.info(
            "creating_section_nodes_batched",
            document_id=document_id,
            sections_count=len(sections),
            chunks_count=len(chunks),
        )

        try:
            async with self.driver.session(database=self.database) as session:
                # Step 1: Create/Merge Document node
                await session.run(
                    """
                    MERGE (d:Document {id: $document_id})
                    SET d.updated_at = datetime()
                    """,
                    document_id=document_id,
                )

                # Sprint 33 Performance Fix: BATCH Section Node Creation using UNWIND
                # Prepare section data for batch insert
                section_data = [
                    {
                        "heading": section.heading,
                        "level": section.level,
                        "page_no": section.page_no,
                        "order": idx,
                        "bbox_left": section.bbox.get("l", 0.0),
                        "bbox_top": section.bbox.get("t", 0.0),
                        "bbox_right": section.bbox.get("r", 0.0),
                        "bbox_bottom": section.bbox.get("b", 0.0),
                        "token_count": section.token_count,
                        "text_preview": section.text[:200] if section.text else "",
                    }
                    for idx, section in enumerate(sections)
                ]

                # Step 2: Batch create all Section nodes + HAS_SECTION relationships
                section_create_result = await session.run(
                    """
                    UNWIND $sections AS section
                    CREATE (s:Section {
                        heading: section.heading,
                        level: section.level,
                        page_no: section.page_no,
                        order: section.order,
                        bbox_left: section.bbox_left,
                        bbox_top: section.bbox_top,
                        bbox_right: section.bbox_right,
                        bbox_bottom: section.bbox_bottom,
                        token_count: section.token_count,
                        text_preview: section.text_preview,
                        created_at: datetime()
                    })
                    WITH s, section
                    MATCH (d:Document {id: $document_id})
                    MERGE (d)-[:HAS_SECTION {order: section.order}]->(s)
                    RETURN count(s) AS sections_created
                    """,
                    sections=section_data,
                    document_id=document_id,
                )
                section_record = await section_create_result.single()
                sections_created = (
                    section_record["sections_created"] if section_record else len(sections)
                )
                has_section_rels = sections_created  # One HAS_SECTION per section

                logger.info(
                    "section_nodes_batch_created",
                    sections_created=sections_created,
                    has_section_relationships=has_section_rels,
                    batch_time_ms=round((time.time() - batch_start_time) * 1000, 2),
                )

                # Sprint 33 Performance Fix: BATCH CONTAINS_CHUNK relationships
                # Prepare chunk-to-section mapping for batch insert
                chunk_section_mappings = []
                for chunk in chunks:
                    for section_heading in chunk.section_headings:
                        chunk_section_mappings.append(
                            {
                                "section_heading": section_heading,
                                "chunk_text_preview": chunk.text[:100] if chunk.text else "",
                            }
                        )

                if chunk_section_mappings:
                    contains_result = await session.run(
                        """
                        UNWIND $mappings AS mapping
                        MATCH (s:Section {heading: mapping.section_heading})
                        MATCH (c:chunk)
                        WHERE c.text CONTAINS mapping.chunk_text_preview
                        MERGE (s)-[:CONTAINS_CHUNK]->(c)
                        RETURN count(*) AS rels_created
                        """,
                        mappings=chunk_section_mappings,
                    )
                    contains_record = await contains_result.single()
                    contains_chunk_rels = contains_record["rels_created"] if contains_record else 0
                else:
                    contains_chunk_rels = 0

                logger.info(
                    "contains_chunk_batch_created",
                    contains_chunk_rels=contains_chunk_rels,
                    mappings_attempted=len(chunk_section_mappings),
                )

                # Sprint 33 Performance Fix: BATCH DEFINES relationships
                # Create all DEFINES relationships in one query
                defines_result = await session.run(
                    """
                    MATCH (s:Section)-[:CONTAINS_CHUNK]->(c:chunk)
                    MATCH (e:base)-[:MENTIONED_IN]->(c)
                    MERGE (s)-[:DEFINES]->(e)
                    RETURN count(*) AS defines_created
                    """,
                )
                defines_record = await defines_result.single()
                defines_entity_rels = defines_record["defines_created"] if defines_record else 0

                logger.info(
                    "defines_entity_batch_created",
                    defines_entity_rels=defines_entity_rels,
                )

                # Sprint 62 Feature 62.6: Create HAS_SUBSECTION hierarchical relationships
                # Detect parent-child relationships based on section heading patterns
                # E.g., "1.2.3" → parent "1.2", "1.2" → parent "1"
                hierarchy_result = await session.run(
                    """
                    MATCH (d:Document {id: $document_id})-[:HAS_SECTION]->(child:Section)
                    WHERE child.heading =~ '.*\\..*'
                    WITH child,
                         substring(child.heading, 0,
                                   size(child.heading) - size(split(child.heading, '.')[-1]) - 1
                         ) AS parent_heading
                    WHERE parent_heading <> ''
                    MATCH (d:Document {id: $document_id})-[:HAS_SECTION]->(parent:Section)
                    WHERE parent.heading = parent_heading
                    MERGE (parent)-[:HAS_SUBSECTION {created_at: datetime()}]->(child)
                    RETURN count(*) AS hierarchy_rels_created
                    """,
                    document_id=document_id,
                )
                hierarchy_record = await hierarchy_result.single()
                hierarchy_rels = (
                    hierarchy_record["hierarchy_rels_created"] if hierarchy_record else 0
                )

                logger.info(
                    "has_subsection_hierarchy_created",
                    hierarchy_rels=hierarchy_rels,
                )

                batch_duration = time.time() - batch_start_time
                stats = {
                    "sections_created": sections_created,
                    "has_section_rels": has_section_rels,
                    "contains_chunk_rels": contains_chunk_rels,
                    "defines_entity_rels": defines_entity_rels,
                    "hierarchy_rels": hierarchy_rels,
                }

                logger.info(
                    "TIMING_neo4j_section_nodes_complete",
                    stage="neo4j",
                    substage="section_nodes",
                    duration_ms=round(batch_duration * 1000, 2),
                    document_id=document_id,
                    sections_count=len(sections),
                    chunks_count=len(chunks),
                    **stats,
                )

                return stats

        except Exception as e:
            logger.error(
                "section_nodes_creation_failed",
                document_id=document_id,
                error=str(e),
            )
            raise DatabaseConnectionError("Neo4j", f"Section nodes creation failed: {e}") from e

    async def store_chunks_and_provenance(
        self,
        chunks: list[dict[str, Any]],
        entities: list[dict[str, Any]],
        namespace_id: str = "default",
    ) -> dict[str, int]:
        """Store chunk nodes, entity nodes, and MENTIONED_IN relationships in Neo4j.

        Sprint 128: Migrated from lightrag/neo4j_storage.py to use Neo4jClient directly.
        Replaces the LightRAG rag._driver dependency.

        Creates Neo4j schema:
        - :chunk nodes with text, document_id, chunk_index, namespace_id metadata
        - :base entity nodes with namespace_id for isolation
        - MENTIONED_IN relationships from :base entities to :chunk nodes

        Args:
            chunks: List of chunk metadata dicts with chunk_id, text, document_id, etc.
            entities: List of entities with entity_id, entity_name, entity_type, source_id
            namespace_id: Namespace for multi-tenant isolation (default: "default")

        Returns:
            Dictionary with counts: chunks_created, entities_created, mentioned_in_created
        """
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
            async with self.driver.session() as session:
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
                            c.domain_id = $domain_id,
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
                        domain_id=chunk.get("domain_id"),
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
                        entities_skipped += 1
                        continue

                    # Sanitize entity_type label for Cypher safety
                    sanitized_type = entity_type.replace("`", "\\`")
                    labels_str = f"base:`{sanitized_type}`"

                    entity_sub_type = entity.get("entity_sub_type")

                    try:
                        if entity_sub_type:
                            await session.run(
                                f"""
                                MERGE (e:{labels_str} {{entity_id: $entity_id}})
                                SET e.entity_name = $entity_name,
                                    e.entity_type = $entity_type,
                                    e.entity_sub_type = $entity_sub_type,
                                    e.description = $description,
                                    e.source_id = $source_id,
                                    e.file_path = $file_path,
                                    e.chunk_index = $chunk_index,
                                    e.namespace_id = $namespace_id,
                                    e.domain_id = $domain_id,
                                    e.created_at = datetime()
                                """,
                                entity_id=entity_id,
                                entity_name=entity_name,
                                entity_type=entity_type,
                                entity_sub_type=entity_sub_type,
                                description=entity.get("description", ""),
                                source_id=entity.get("source_id", ""),
                                file_path=entity.get("file_path", ""),
                                chunk_index=entity.get("chunk_index", 0),
                                namespace_id=namespace_id,
                                domain_id=entity.get("domain_id"),
                            )
                        else:
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
                                    e.domain_id = $domain_id,
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
                                domain_id=entity.get("domain_id"),
                            )
                        entities_created += 1
                    except Exception as e:
                        logger.error("entity_creation_failed", entity_id=entity_id, error=str(e))
                        entities_skipped += 1

                stats["entities_created"] = entities_created
                logger.info(
                    "entity_nodes_created", created=entities_created, skipped=entities_skipped
                )

                # Step 3: Create MENTIONED_IN relationships
                entities_by_chunk: dict[str, list[str]] = {}
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

            logger.info("chunks_and_provenance_stored_successfully", **stats)
            return stats

        except Exception as e:
            logger.error("store_chunks_and_provenance_failed", error=str(e))
            raise

    async def store_relations(
        self,
        relations: list[dict[str, Any]],
        chunk_id: str,
        namespace_id: str = "default",
    ) -> int:
        """Store RELATES_TO relationships between entities in Neo4j.

        Sprint 128: Migrated from lightrag/neo4j_storage.py to use Neo4jClient directly.

        Args:
            relations: List of relations with source, target, description, strength
            chunk_id: Source chunk ID for provenance
            namespace_id: Namespace for multi-tenant isolation

        Returns:
            Number of relationships created
        """
        if not relations:
            return 0

        logger.info(
            "storing_relations",
            total_relations=len(relations),
            chunk_id=chunk_id[:8] if len(chunk_id) > 8 else chunk_id,
        )

        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    UNWIND $relations AS rel
                    MATCH (e1:base {entity_name: rel.source})
                    MATCH (e2:base {entity_name: rel.target})
                    WHERE e1 <> e2
                    MERGE (e1)-[r:RELATES_TO]->(e2)
                    SET r.weight = toFloat(rel.strength) / 10.0,
                        r.description = rel.description,
                        r.relation_type = CASE
                            WHEN rel.relation_type <> 'RELATES_TO' THEN rel.relation_type
                            WHEN r.relation_type IS NOT NULL AND r.relation_type <> 'RELATES_TO' THEN r.relation_type
                            ELSE rel.relation_type
                        END,
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
                            "relation_type": r.get("type")
                            or r.get("relation_type")
                            or r.get("relation", "RELATES_TO"),
                        }
                        for r in relations
                    ],
                    chunk_id=chunk_id,
                    namespace_id=namespace_id,
                )
                record = await result.single()
                created = record["created"] if record else 0

            logger.info(
                "relations_stored",
                count=created,
                input_relations=len(relations),
            )
            return created

        except Exception as e:
            logger.error(
                "store_relations_failed",
                error=str(e),
                chunk_id=chunk_id[:8] if len(chunk_id) > 8 else chunk_id,
            )
            raise

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")

    async def __aenter__(self) -> "Neo4jClient":
        """Async context manager entry.

        Returns:
            Neo4jClient instance
        """
        # Driver is initialized lazily on first use
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        """Async context manager exit.

        Args:
            _exc_type: Exception type (unused, required by protocol)
            _exc_val: Exception value (unused, required by protocol)
            _exc_tb: Exception traceback (unused, required by protocol)
        """
        await self.close()


# Global client instance (singleton pattern)
_neo4j_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    """Get global Neo4j client instance (singleton).

    Returns:
        Neo4jClient instance
    """
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client


@asynccontextmanager
async def get_neo4j_client_async() -> None:
    """Async context manager for Neo4j client.

    Usage:
        async with get_neo4j_client_async() as client:
            await client.health_check()

    Yields:
        Neo4jClient instance
    """
    client = get_neo4j_client()
    try:
        yield client
    finally:
        # Connection is pooled, no need to close here
        pass
