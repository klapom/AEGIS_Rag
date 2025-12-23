"""Section-Aware Graph Query Service.

Sprint 62 Feature 62.1: Section-Aware Graph Queries
This module extends graph querying to leverage section metadata from Sprint 32.

Capabilities:
- Query entities/relationships within specific sections
- Support section hierarchy (document → section → subsection)
- Multi-section queries (e.g., "entities in sections 1.1 and 1.2")
- Optimized Cypher queries with section filtering

Architecture:
- Uses Section nodes created in Sprint 32 (create_section_nodes)
- Leverages DEFINES relationships (Section → Entity)
- Supports CONTAINS_CHUNK relationships (Section → Chunk)
- Performance target: <100ms for section queries
"""

import time
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.components.graph_rag.query_builder import CypherQueryBuilder

logger = structlog.get_logger(__name__)


# =============================================================================
# MODELS
# =============================================================================


class SectionMetadataResult(BaseModel):
    """Section metadata in query results."""

    section_heading: str = Field(..., description="Section heading text")
    section_level: int = Field(default=1, ge=1, le=6, description="Heading level")
    section_id: str | None = Field(default=None, description="Section node ID from Neo4j")
    section_page: int | None = Field(default=None, description="Page number")
    section_order: int | None = Field(default=None, description="Section order in document")


class EntityWithSection(BaseModel):
    """Entity result with section metadata."""

    entity_id: str = Field(..., description="Entity ID")
    entity_name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Entity type")
    description: str | None = Field(None, description="Entity description")
    sections: list[SectionMetadataResult] = Field(
        default_factory=list,
        description="Sections where this entity is defined",
    )


class RelationshipWithSection(BaseModel):
    """Relationship result with section metadata."""

    source_id: str = Field(..., description="Source entity ID")
    source_name: str = Field(..., description="Source entity name")
    target_id: str = Field(..., description="Target entity ID")
    target_name: str = Field(..., description="Target entity name")
    relationship_type: str = Field(..., description="Relationship type")
    description: str | None = Field(None, description="Relationship description")
    sections: list[SectionMetadataResult] = Field(
        default_factory=list,
        description="Sections where this relationship is mentioned",
    )


class SectionGraphQueryResult(BaseModel):
    """Result of section-aware graph query."""

    entities: list[EntityWithSection] = Field(default_factory=list)
    relationships: list[RelationshipWithSection] = Field(default_factory=list)
    query_time_ms: float = Field(..., description="Query execution time in ms")
    section_filters: list[str] = Field(
        default_factory=list,
        description="Section filters applied",
    )


# =============================================================================
# SERVICE
# =============================================================================


class SectionGraphService:
    """Service for section-aware graph queries.

    This service extends graph querying to leverage section metadata:
    - Query entities within specific sections
    - Query relationships within specific sections
    - Support multi-section queries
    - Traverse section hierarchy

    Example:
        >>> service = SectionGraphService()
        >>> result = await service.query_entities_in_section(
        ...     section_heading="Introduction",
        ...     document_id="doc_123"
        ... )
        >>> print(f"Found {len(result.entities)} entities")
    """

    def __init__(self, neo4j_client: Neo4jClient | None = None) -> None:
        """Initialize section graph service.

        Args:
            neo4j_client: Neo4j client instance (uses singleton if None)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        logger.info("section_graph_service_initialized")

    async def query_entities_in_section(
        self,
        section_heading: str,
        document_id: str | None = None,
        limit: int = 100,
    ) -> SectionGraphQueryResult:
        """Query entities defined in a specific section.

        Args:
            section_heading: Section heading to filter by
            document_id: Optional document ID filter
            limit: Maximum entities to return (default: 100)

        Returns:
            SectionGraphQueryResult with entities and metadata

        Example:
            >>> result = await service.query_entities_in_section(
            ...     section_heading="Methods",
            ...     document_id="doc_123"
            ... )
        """
        start_time = time.perf_counter()

        # Build Cypher query
        builder = CypherQueryBuilder()
        builder.match("(s:Section)-[:DEFINES]->(e:base)")
        builder.where("s.heading = $section_heading", section_heading=section_heading)

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        builder.return_(
            "e.id as entity_id",
            "e.name as entity_name",
            "e.type as entity_type",
            "e.description as entity_description",
            "s.heading as section_heading",
            "s.level as section_level",
            "s.page_no as section_page",
            "s.order as section_order",
        )
        builder.limit(limit)

        query_dict = builder.build()

        # Execute query
        logger.debug(
            "executing_section_entity_query",
            section_heading=section_heading,
            document_id=document_id,
        )
        records = await self.neo4j_client.execute_read(
            query_dict["query"],
            query_dict["parameters"],
        )

        # Parse results
        entities_map: dict[str, EntityWithSection] = {}

        for record in records:
            entity_id = record["entity_id"]

            # Create or update entity
            if entity_id not in entities_map:
                entities_map[entity_id] = EntityWithSection(
                    entity_id=entity_id,
                    entity_name=record["entity_name"],
                    entity_type=record["entity_type"],
                    description=record.get("entity_description"),
                    sections=[],
                )

            # Add section metadata
            section_metadata = SectionMetadataResult(
                section_heading=record["section_heading"],
                section_level=record.get("section_level", 1),
                section_page=record.get("section_page"),
                section_order=record.get("section_order"),
            )
            entities_map[entity_id].sections.append(section_metadata)

        query_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "section_entity_query_complete",
            section_heading=section_heading,
            entities_found=len(entities_map),
            query_time_ms=round(query_time_ms, 2),
        )

        return SectionGraphQueryResult(
            entities=list(entities_map.values()),
            relationships=[],
            query_time_ms=query_time_ms,
            section_filters=[section_heading],
        )

    async def query_entities_in_sections(
        self,
        section_headings: list[str],
        document_id: str | None = None,
        limit: int = 100,
    ) -> SectionGraphQueryResult:
        """Query entities in multiple sections.

        Args:
            section_headings: List of section headings to filter by
            document_id: Optional document ID filter
            limit: Maximum entities to return (default: 100)

        Returns:
            SectionGraphQueryResult with entities and metadata

        Example:
            >>> result = await service.query_entities_in_sections(
            ...     section_headings=["Introduction", "Methods"],
            ...     document_id="doc_123"
            ... )
        """
        start_time = time.perf_counter()

        # Build Cypher query
        builder = CypherQueryBuilder()
        builder.match("(s:Section)-[:DEFINES]->(e:base)")
        builder.where("s.heading IN $section_headings", section_headings=section_headings)

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        builder.return_(
            "e.id as entity_id",
            "e.name as entity_name",
            "e.type as entity_type",
            "e.description as entity_description",
            "collect(DISTINCT {heading: s.heading, level: s.level, page: s.page_no, order: s.order}) as sections",
        )
        builder.limit(limit)

        query_dict = builder.build()

        # Execute query
        logger.debug(
            "executing_multi_section_entity_query",
            section_headings=section_headings,
            document_id=document_id,
        )
        records = await self.neo4j_client.execute_read(
            query_dict["query"],
            query_dict["parameters"],
        )

        # Parse results
        entities = []

        for record in records:
            sections_list = []
            for section_dict in record.get("sections", []):
                sections_list.append(
                    SectionMetadataResult(
                        section_heading=section_dict["heading"],
                        section_level=section_dict.get("level", 1),
                        section_page=section_dict.get("page"),
                        section_order=section_dict.get("order"),
                    )
                )

            entities.append(
                EntityWithSection(
                    entity_id=record["entity_id"],
                    entity_name=record["entity_name"],
                    entity_type=record["entity_type"],
                    description=record.get("entity_description"),
                    sections=sections_list,
                )
            )

        query_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "multi_section_entity_query_complete",
            section_count=len(section_headings),
            entities_found=len(entities),
            query_time_ms=round(query_time_ms, 2),
        )

        return SectionGraphQueryResult(
            entities=entities,
            relationships=[],
            query_time_ms=query_time_ms,
            section_filters=section_headings,
        )

    async def query_relationships_in_section(
        self,
        section_heading: str,
        document_id: str | None = None,
        limit: int = 100,
    ) -> SectionGraphQueryResult:
        """Query relationships mentioned in a specific section.

        Args:
            section_heading: Section heading to filter by
            document_id: Optional document ID filter
            limit: Maximum relationships to return (default: 100)

        Returns:
            SectionGraphQueryResult with relationships and metadata

        Example:
            >>> result = await service.query_relationships_in_section(
            ...     section_heading="Results",
            ...     document_id="doc_123"
            ... )
        """
        start_time = time.perf_counter()

        # Build Cypher query to find relationships via chunks in sections
        builder = CypherQueryBuilder()
        builder.match("(s:Section)-[:CONTAINS_CHUNK]->(c:chunk)")
        builder.match("(source:base)-[r]->(target:base)")
        builder.match("(r)-[:MENTIONED_IN]->(c)")
        builder.where("s.heading = $section_heading", section_heading=section_heading)

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        builder.return_(
            "source.id as source_id",
            "source.name as source_name",
            "target.id as target_id",
            "target.name as target_name",
            "type(r) as relationship_type",
            "r.description as relationship_description",
            "s.heading as section_heading",
            "s.level as section_level",
            "s.page_no as section_page",
            "s.order as section_order",
        )
        builder.limit(limit)

        query_dict = builder.build()

        # Execute query
        logger.debug(
            "executing_section_relationship_query",
            section_heading=section_heading,
            document_id=document_id,
        )
        records = await self.neo4j_client.execute_read(
            query_dict["query"],
            query_dict["parameters"],
        )

        # Parse results
        relationships = []

        for record in records:
            section_metadata = SectionMetadataResult(
                section_heading=record["section_heading"],
                section_level=record.get("section_level", 1),
                section_page=record.get("section_page"),
                section_order=record.get("section_order"),
            )

            relationships.append(
                RelationshipWithSection(
                    source_id=record["source_id"],
                    source_name=record["source_name"],
                    target_id=record["target_id"],
                    target_name=record["target_name"],
                    relationship_type=record["relationship_type"],
                    description=record.get("relationship_description"),
                    sections=[section_metadata],
                )
            )

        query_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "section_relationship_query_complete",
            section_heading=section_heading,
            relationships_found=len(relationships),
            query_time_ms=round(query_time_ms, 2),
        )

        return SectionGraphQueryResult(
            entities=[],
            relationships=relationships,
            query_time_ms=query_time_ms,
            section_filters=[section_heading],
        )

    async def query_section_hierarchy(
        self,
        document_id: str,
        max_level: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query section hierarchy for a document.

        Args:
            document_id: Document ID
            max_level: Maximum heading level to return (default: all levels)

        Returns:
            List of section dictionaries with hierarchy information

        Example:
            >>> sections = await service.query_section_hierarchy("doc_123", max_level=3)
        """
        start_time = time.perf_counter()

        # Build Cypher query
        builder = CypherQueryBuilder()
        builder.match("(d:Document)-[:HAS_SECTION]->(s:Section)")
        builder.where("d.id = $document_id", document_id=document_id)

        if max_level:
            builder.where("s.level <= $max_level", max_level=max_level)

        builder.return_(
            "s.heading as heading",
            "s.level as level",
            "s.page_no as page_no",
            "s.order as order",
            "s.token_count as token_count",
            "s.text_preview as text_preview",
        )
        builder.order_by("s.order ASC")

        query_dict = builder.build()

        # Execute query
        logger.debug(
            "executing_section_hierarchy_query",
            document_id=document_id,
            max_level=max_level,
        )
        records = await self.neo4j_client.execute_read(
            query_dict["query"],
            query_dict["parameters"],
        )

        query_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "section_hierarchy_query_complete",
            document_id=document_id,
            sections_found=len(records),
            query_time_ms=round(query_time_ms, 2),
        )

        return records

    async def get_entity_sections(
        self,
        entity_id: str,
    ) -> list[SectionMetadataResult]:
        """Get all sections where an entity is defined.

        Args:
            entity_id: Entity ID or name

        Returns:
            List of section metadata

        Example:
            >>> sections = await service.get_entity_sections("entity-123")
        """
        start_time = time.perf_counter()

        # Build Cypher query
        builder = CypherQueryBuilder()
        builder.match("(s:Section)-[:DEFINES]->(e:base)")

        # Match by ID or name
        if entity_id.startswith("entity-") or entity_id.startswith("id-"):
            builder.where("e.id = $entity_id", entity_id=entity_id)
        else:
            builder.where("e.name = $entity_id", entity_id=entity_id)

        builder.return_(
            "s.heading as section_heading",
            "s.level as section_level",
            "s.page_no as section_page",
            "s.order as section_order",
        )
        builder.order_by("s.order ASC")

        query_dict = builder.build()

        # Execute query
        logger.debug("executing_entity_sections_query", entity_id=entity_id)
        records = await self.neo4j_client.execute_read(
            query_dict["query"],
            query_dict["parameters"],
        )

        sections = [
            SectionMetadataResult(
                section_heading=record["section_heading"],
                section_level=record.get("section_level", 1),
                section_page=record.get("section_page"),
                section_order=record.get("section_order"),
            )
            for record in records
        ]

        query_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "entity_sections_query_complete",
            entity_id=entity_id,
            sections_found=len(sections),
            query_time_ms=round(query_time_ms, 2),
        )

        return sections

    async def create_section_hierarchy(
        self,
        document_id: str,
    ) -> dict[str, int]:
        """Create HAS_SUBSECTION relationships between parent and child sections.

        Sprint 62 Feature 62.6: Hierarchical section links.

        Detects parent-child relationships based on section headings:
        - "1" → parent of "1.1", "1.2", ...
        - "1.1" → parent of "1.1.1", "1.1.2", ...
        - Supports multi-level hierarchy (section → subsection → subsubsection)

        Args:
            document_id: Document ID to create hierarchy for

        Returns:
            Dictionary with creation statistics:
            - hierarchical_relationships_created: Number of HAS_SUBSECTION relationships

        Example:
            >>> service = SectionGraphService()
            >>> stats = await service.create_section_hierarchy("doc_123")
            >>> stats["hierarchical_relationships_created"]
            12
        """
        start_time = time.perf_counter()

        logger.info("creating_section_hierarchy", document_id=document_id)

        # Cypher query to create HAS_SUBSECTION relationships
        # Strategy: For each section, find its parent by matching heading patterns
        # E.g., "1.2.3" should have parent "1.2"
        cypher = """
        MATCH (d:Document {id: $document_id})-[:HAS_SECTION]->(child:Section)
        WHERE child.heading =~ '.*\\..*'  // Has at least one dot (e.g., "1.2")
        WITH child,
             // Extract parent heading by removing last segment
             // "1.2.3" → "1.2", "1.2" → "1"
             substring(child.heading, 0,
                       size(child.heading) - size(split(child.heading, '.')[-1]) - 1
             ) AS parent_heading
        WHERE parent_heading <> ''
        MATCH (d:Document {id: $document_id})-[:HAS_SECTION]->(parent:Section)
        WHERE parent.heading = parent_heading
        MERGE (parent)-[:HAS_SUBSECTION {created_at: datetime()}]->(child)
        RETURN count(*) AS relationships_created
        """

        try:
            result = await self.neo4j_client.execute_write(
                cypher,
                {"document_id": document_id},
            )

            relationships_created = result.get("relationships_created", 0)

            query_time_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "section_hierarchy_created",
                document_id=document_id,
                relationships_created=relationships_created,
                query_time_ms=round(query_time_ms, 2),
            )

            return {
                "hierarchical_relationships_created": relationships_created,
            }

        except Exception as e:
            logger.error(
                "section_hierarchy_creation_failed",
                document_id=document_id,
                error=str(e),
            )
            raise

    async def get_parent_section(
        self,
        section_heading: str,
        document_id: str,
    ) -> SectionMetadataResult | None:
        """Get parent section of a given section.

        Sprint 62 Feature 62.6: Traverse HAS_SUBSECTION upwards.

        Args:
            section_heading: Child section heading
            document_id: Document ID

        Returns:
            Parent section metadata, or None if no parent exists

        Example:
            >>> parent = await service.get_parent_section("1.2.3", "doc_123")
            >>> parent.section_heading
            "1.2"
        """
        start_time = time.perf_counter()

        cypher = """
        MATCH (d:Document {id: $document_id})-[:HAS_SECTION]->(child:Section {heading: $section_heading})
        MATCH (parent:Section)-[:HAS_SUBSECTION]->(child)
        RETURN parent.heading as section_heading,
               parent.level as section_level,
               parent.page_no as section_page,
               parent.order as section_order
        LIMIT 1
        """

        records = await self.neo4j_client.execute_read(
            cypher,
            {"document_id": document_id, "section_heading": section_heading},
        )

        query_time_ms = (time.perf_counter() - start_time) * 1000

        if not records:
            logger.debug(
                "no_parent_section_found",
                section_heading=section_heading,
                document_id=document_id,
                query_time_ms=round(query_time_ms, 2),
            )
            return None

        record = records[0]
        parent = SectionMetadataResult(
            section_heading=record["section_heading"],
            section_level=record.get("section_level", 1),
            section_page=record.get("section_page"),
            section_order=record.get("section_order"),
        )

        logger.info(
            "parent_section_found",
            child_heading=section_heading,
            parent_heading=parent.section_heading,
            query_time_ms=round(query_time_ms, 2),
        )

        return parent

    async def get_child_sections(
        self,
        section_heading: str,
        document_id: str,
    ) -> list[SectionMetadataResult]:
        """Get all direct child sections (subsections) of a given section.

        Sprint 62 Feature 62.6: Traverse HAS_SUBSECTION downwards.

        Args:
            section_heading: Parent section heading
            document_id: Document ID

        Returns:
            List of child section metadata (ordered by section order)

        Example:
            >>> children = await service.get_child_sections("1.2", "doc_123")
            >>> [c.section_heading for c in children]
            ["1.2.1", "1.2.2", "1.2.3"]
        """
        start_time = time.perf_counter()

        cypher = """
        MATCH (d:Document {id: $document_id})-[:HAS_SECTION]->(parent:Section {heading: $section_heading})
        MATCH (parent)-[:HAS_SUBSECTION]->(child:Section)
        RETURN child.heading as section_heading,
               child.level as section_level,
               child.page_no as section_page,
               child.order as section_order
        ORDER BY child.order ASC
        """

        records = await self.neo4j_client.execute_read(
            cypher,
            {"document_id": document_id, "section_heading": section_heading},
        )

        children = [
            SectionMetadataResult(
                section_heading=record["section_heading"],
                section_level=record.get("section_level", 1),
                section_page=record.get("section_page"),
                section_order=record.get("section_order"),
            )
            for record in records
        ]

        query_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "child_sections_found",
            parent_heading=section_heading,
            children_count=len(children),
            query_time_ms=round(query_time_ms, 2),
        )

        return children

    async def get_section_ancestry(
        self,
        section_heading: str,
        document_id: str,
    ) -> list[SectionMetadataResult]:
        """Get full ancestry path from root to given section.

        Sprint 62 Feature 62.6: Traverse HAS_SUBSECTION upwards to root.

        Returns the full path from the root section to the target section,
        ordered from root to leaf (e.g., ["1", "1.2", "1.2.3"]).

        Args:
            section_heading: Target section heading
            document_id: Document ID

        Returns:
            List of section metadata representing the ancestry path
            (ordered from root to leaf)

        Example:
            >>> ancestry = await service.get_section_ancestry("1.2.3", "doc_123")
            >>> [s.section_heading for s in ancestry]
            ["1", "1.2", "1.2.3"]
        """
        start_time = time.perf_counter()

        # Use Cypher variable-length path matching to traverse upwards
        # The path goes: (root)-[:HAS_SUBSECTION*]->(target)
        cypher = """
        MATCH (d:Document {id: $document_id})-[:HAS_SECTION]->(target:Section {heading: $section_heading})
        MATCH path = (root:Section)-[:HAS_SUBSECTION*0..]->(target)
        WHERE NOT EXISTS((other:Section)-[:HAS_SUBSECTION]->(root))
        RETURN nodes(path) as ancestry_nodes
        ORDER BY length(path) DESC
        LIMIT 1
        """

        records = await self.neo4j_client.execute_read(
            cypher,
            {"document_id": document_id, "section_heading": section_heading},
        )

        if not records:
            # No ancestry found - this is a root section
            logger.debug(
                "no_ancestry_found",
                section_heading=section_heading,
                document_id=document_id,
            )
            # Return just the section itself
            cypher_self = """
            MATCH (d:Document {id: $document_id})-[:HAS_SECTION]->(s:Section {heading: $section_heading})
            RETURN s.heading as section_heading,
                   s.level as section_level,
                   s.page_no as section_page,
                   s.order as section_order
            """
            self_records = await self.neo4j_client.execute_read(
                cypher_self,
                {"document_id": document_id, "section_heading": section_heading},
            )
            if self_records:
                record = self_records[0]
                return [
                    SectionMetadataResult(
                        section_heading=record["section_heading"],
                        section_level=record.get("section_level", 1),
                        section_page=record.get("section_page"),
                        section_order=record.get("section_order"),
                    )
                ]
            return []

        # Parse ancestry nodes from path
        ancestry_nodes = records[0]["ancestry_nodes"]
        ancestry = []

        for node in ancestry_nodes:
            ancestry.append(
                SectionMetadataResult(
                    section_heading=node["heading"],
                    section_level=node.get("level", 1),
                    section_page=node.get("page_no"),
                    section_order=node.get("order"),
                )
            )

        query_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "section_ancestry_retrieved",
            section_heading=section_heading,
            ancestry_depth=len(ancestry),
            ancestry_path=" → ".join([s.section_heading for s in ancestry]),
            query_time_ms=round(query_time_ms, 2),
        )

        return ancestry


# =============================================================================
# SINGLETON
# =============================================================================

_section_graph_service: SectionGraphService | None = None


def get_section_graph_service(
    neo4j_client: Neo4jClient | None = None,
) -> SectionGraphService:
    """Get section graph service instance (singleton).

    Args:
        neo4j_client: Optional Neo4j client (uses singleton if None)

    Returns:
        SectionGraphService instance
    """
    global _section_graph_service

    if _section_graph_service is None:
        _section_graph_service = SectionGraphService(neo4j_client)

    return _section_graph_service


def reset_section_graph_service() -> None:
    """Reset singleton (for testing)."""
    global _section_graph_service
    _section_graph_service = None
