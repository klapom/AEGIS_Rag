"""Pre-built Graph Query Templates for Common Operations.

This module provides 15+ parameterized query templates for:
- Entity lookup and search
- Relationship traversal
- Path finding
- Subgraph extraction
- Graph statistics and analytics
- Community detection
- Entity evolution tracking
- Section-aware queries (Sprint 62.1)
"""

import structlog

from src.components.graph_rag.query_builder import CypherQueryBuilder

logger = structlog.get_logger(__name__)


class GraphQueryTemplates:
    """Collection of pre-built query templates for common graph operations.

    All templates return CypherQueryBuilder instances for further customization.
    All inputs are parameterized to prevent injection attacks.

    Example:
        >>> templates = GraphQueryTemplates()
        >>> query_dict = templates.entity_lookup("John Doe").build()
        >>> print(query_dict["query"])
        >>> print(query_dict["parameters"])
    """

    def __init__(self) -> None:
        """Initialize query templates."""
        logger.debug("GraphQueryTemplates initialized")

    def entity_lookup(self, name: str) -> CypherQueryBuilder:
        """Find entity by exact name match.

        Args:
            name: Entity name to search for

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_lookup("John Doe").limit(1).build()
        """
        return (
            CypherQueryBuilder().match("(e:base)").where("e.name = $name", name=name).return_("e")
        )

    def entity_neighbors(
        self, entity_id: str, depth: int = 1, rel_type: str | None = None
    ) -> CypherQueryBuilder:
        """Get entity's neighborhood up to specified depth.

        Args:
            entity_id: Entity ID or name
            depth: Maximum traversal depth (default: 1)
            rel_type: Optional relationship type filter

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_neighbors("entity-123", depth=2).build()
            >>> templates.entity_neighbors("entity-123", depth=1, rel_type="RELATES_TO").build()
        """
        builder = CypherQueryBuilder().match("(e:base)")

        # Match source entity
        if entity_id.startswith("entity-") or entity_id.startswith("id-"):
            builder.where("e.id = $entity_id", entity_id=entity_id)
        else:
            builder.where("e.name = $entity_id", entity_id=entity_id)

        # Add relationship pattern with depth
        if rel_type:
            builder.match(f"(e)-[r:{rel_type}*1..{depth}]-(neighbor:base)").param(
                "rel_type", rel_type
            )
        else:
            builder.match(f"(e)-[r*1..{depth}]-(neighbor:base)")

        builder.param("depth", depth)

        return builder.return_("DISTINCT neighbor", "r")

    def shortest_path(
        self, source_id: str, target_id: str, max_hops: int = 5
    ) -> CypherQueryBuilder:
        """Find shortest path between two entities.

        Args:
            source_id: Source entity ID or name
            target_id: Target entity ID or name
            max_hops: Maximum path length (default: 5)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.shortest_path("entity-1", "entity-2", max_hops=3).build()
        """
        builder = CypherQueryBuilder()

        # Match source and target
        builder.match("(source:base), (target:base)")

        # Determine if using ID or name for source
        if source_id.startswith("entity-") or source_id.startswith("id-"):
            builder.where("source.id = $source_id", source_id=source_id)
        else:
            builder.where("source.name = $source_id", source_id=source_id)

        # Determine if using ID or name for target
        if target_id.startswith("entity-") or target_id.startswith("id-"):
            builder.where("target.id = $target_id", target_id=target_id)
        else:
            builder.where("target.name = $target_id", target_id=target_id)

        # Use shortestPath function
        builder.match(f"p = shortestPath((source)-[*..{max_hops}]-(target))")
        builder.param("max_hops", max_hops)

        return builder.return_("p", "length(p) as path_length")

    def entity_relationships(
        self, entity_id: str, rel_type: str | None = None, direction: str = "both"
    ) -> CypherQueryBuilder:
        """Get all relationships for an entity.

        Args:
            entity_id: Entity ID or name
            rel_type: Optional relationship type filter
            direction: Relationship direction ("outgoing", "incoming", "both")

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_relationships("entity-123").build()
            >>> templates.entity_relationships("entity-123", rel_type="RELATES_TO", direction="outgoing").build()
        """
        builder = CypherQueryBuilder().match("(e:base)")

        # Match entity
        if entity_id.startswith("entity-") or entity_id.startswith("id-"):
            builder.where("e.id = $entity_id", entity_id=entity_id)
        else:
            builder.where("e.name = $entity_id", entity_id=entity_id)

        # Build relationship pattern based on direction
        if direction == "outgoing":
            rel_pattern = f"(e)-[r{':' + rel_type if rel_type else ''}]->(other:base)"
        elif direction == "incoming":
            rel_pattern = f"(e)<-[r{':' + rel_type if rel_type else ''}]-(other:base)"
        else:  # both
            rel_pattern = f"(e)-[r{':' + rel_type if rel_type else ''}]-(other:base)"

        builder.match(rel_pattern)

        if rel_type:
            builder.param("rel_type", rel_type)

        return builder.return_("r", "other", "type(r) as relationship_type")

    def subgraph_extraction(self, entity_ids: list[str], depth: int = 1) -> CypherQueryBuilder:
        """Extract subgraph around specified entities.

        Args:
            entity_ids: List of entity IDs or names
            depth: Maximum traversal depth (default: 1)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.subgraph_extraction(["entity-1", "entity-2"], depth=2).build()
        """
        builder = CypherQueryBuilder()

        # Match seed entities
        builder.match("(seed:base)").where(
            "seed.id IN $entity_ids OR seed.name IN $entity_ids", entity_ids=entity_ids
        )

        # Expand to neighbors
        builder.match(f"(seed)-[r*0..{depth}]-(node:base)")
        builder.param("depth", depth)

        return builder.return_("DISTINCT node", "r")

    def entity_by_type(self, entity_type: str, limit: int = 100) -> CypherQueryBuilder:
        """Find entities by type.

        Args:
            entity_type: Entity type (e.g., "Person", "Organization")
            limit: Maximum results (default: 100)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_by_type("Person", limit=50).build()
        """
        return (
            CypherQueryBuilder()
            .match("(e:base)")
            .where("e.type = $entity_type", entity_type=entity_type)
            .return_("e")
            .order_by("e.name")
            .limit(limit)
        )

    def relationship_by_type(self, rel_type: str, limit: int = 100) -> CypherQueryBuilder:
        """Find relationships by type.

        Args:
            rel_type: Relationship type (e.g., "RELATES_TO", "KNOWS")
            limit: Maximum results (default: 100)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.relationship_by_type("KNOWS", limit=50).build()
        """
        return (
            CypherQueryBuilder()
            .match(f"(source)-[r:{rel_type}]->(target)")
            .param("rel_type", rel_type)
            .return_("source", "r", "target")
            .limit(limit)
        )

    def entity_search(self, text_query: str, limit: int = 10) -> CypherQueryBuilder:
        """Full-text search for entities.

        Args:
            text_query: Search text
            limit: Maximum results (default: 10)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_search("machine learning", limit=5).build()
        """
        # Using CONTAINS for simple text search
        # Note: For production, use full-text indexes
        return (
            CypherQueryBuilder()
            .match("(e:base)")
            .where(
                "toLower(e.name) CONTAINS toLower($text_query) OR toLower(e.description) CONTAINS toLower($text_query)",
                text_query=text_query,
            )
            .return_("e", "e.name as name", "e.type as type")
            .order_by("e.name")
            .limit(limit)
        )

    def entity_statistics(self) -> CypherQueryBuilder:
        """Get entity count statistics by type.

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_statistics().build()
        """
        return (
            CypherQueryBuilder()
            .match("(e:base)")
            .return_("e.type as entity_type", "count(e) as count")
            .order_by("count DESC")
        )

    def relationship_statistics(self) -> CypherQueryBuilder:
        """Get relationship count statistics by type.

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.relationship_statistics().build()
        """
        return (
            CypherQueryBuilder()
            .match("()-[r]->()")
            .return_("type(r) as relationship_type", "count(r) as count")
            .order_by("count DESC")
        )

    def orphan_entities(self) -> CypherQueryBuilder:
        """Find entities with no relationships.

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.orphan_entities().limit(50).build()
        """
        return (
            CypherQueryBuilder()
            .match("(e:base)")
            .where("NOT (e)-[]-() ")
            .return_("e", "e.name as name", "e.type as type")
            .order_by("e.name")
        )

    def highly_connected(self, min_degree: int = 5) -> CypherQueryBuilder:
        """Find highly connected entities (hubs).

        Args:
            min_degree: Minimum number of connections (default: 5)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.highly_connected(min_degree=10).build()
        """
        return (
            CypherQueryBuilder()
            .match("(e:base)-[r]-()")
            .with_("e", "count(r) as degree")
            .where("degree >= $min_degree", min_degree=min_degree)
            .return_("e", "e.name as name", "degree")
            .order_by("degree DESC")
        )

    def recent_entities(self, days: int = 7) -> CypherQueryBuilder:
        """Find recently added entities.

        Args:
            days: Number of days to look back (default: 7)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.recent_entities(days=30).build()
        """
        return (
            CypherQueryBuilder()
            .match("(e:base)")
            .where(
                "e.created_at >= datetime() - duration({days: $days})",
                days=days,
            )
            .return_("e", "e.name as name", "e.created_at as created")
            .order_by("e.created_at DESC")
        )

    def entity_evolution(self, entity_id: str) -> CypherQueryBuilder:
        """Get version history for an entity.

        Args:
            entity_id: Entity ID or name

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_evolution("entity-123").build()
        """
        builder = CypherQueryBuilder().match("(e:base)")

        # Match entity
        if entity_id.startswith("entity-") or entity_id.startswith("id-"):
            builder.where("e.id = $entity_id", entity_id=entity_id)
        else:
            builder.where("e.name = $entity_id", entity_id=entity_id)

        # Match version history if available
        builder.match("(e)-[:HAS_VERSION]->(v:EntityVersion)")

        return builder.return_("e", "v", "v.timestamp as version_time").order_by("v.timestamp DESC")

    def community_entities(self, community_id: str | int) -> CypherQueryBuilder:
        """Get all entities in a community.

        Args:
            community_id: Community identifier

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.community_entities("community-1").build()
            >>> templates.community_entities(42).build()
        """
        return (
            CypherQueryBuilder()
            .match("(e:base)")
            .where("e.community_id = $community_id", community_id=community_id)
            .return_("e", "e.name as name", "e.type as type")
            .order_by("e.name")
        )

    def entity_similarity(
        self, entity_id: str, min_common_neighbors: int = 2, limit: int = 10
    ) -> CypherQueryBuilder:
        """Find similar entities based on common neighbors.

        Args:
            entity_id: Source entity ID or name
            min_common_neighbors: Minimum shared neighbors (default: 2)
            limit: Maximum results (default: 10)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_similarity("entity-123", min_common_neighbors=3).build()
        """
        builder = CypherQueryBuilder().match("(e:base)")

        # Match source entity
        if entity_id.startswith("entity-") or entity_id.startswith("id-"):
            builder.where("e.id = $entity_id", entity_id=entity_id)
        else:
            builder.where("e.name = $entity_id", entity_id=entity_id)

        # Find entities with common neighbors
        builder.match("(e)-[]-(common)-[]-(similar:base)")
        builder.where("e <> similar")

        # Count common neighbors
        builder.with_("similar", "count(DISTINCT common) as common_count")
        builder.where(
            "common_count >= $min_common_neighbors", min_common_neighbors=min_common_neighbors
        )

        return (
            builder.return_("similar", "similar.name as name", "common_count")
            .order_by("common_count DESC")
            .limit(limit)
        )

    def relationship_path(
        self, source_id: str, target_id: str, rel_types: list[str], max_hops: int = 5
    ) -> CypherQueryBuilder:
        """Find path with specific relationship types.

        Args:
            source_id: Source entity ID or name
            target_id: Target entity ID or name
            rel_types: List of allowed relationship types
            max_hops: Maximum path length (default: 5)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.relationship_path("e1", "e2", ["KNOWS", "WORKS_WITH"], max_hops=3).build()
        """
        builder = CypherQueryBuilder()

        # Match source and target
        builder.match("(source:base), (target:base)")

        # Match source
        if source_id.startswith("entity-") or source_id.startswith("id-"):
            builder.where("source.id = $source_id", source_id=source_id)
        else:
            builder.where("source.name = $source_id", source_id=source_id)

        # Match target
        if target_id.startswith("entity-") or target_id.startswith("id-"):
            builder.where("target.id = $target_id", target_id=target_id)
        else:
            builder.where("target.name = $target_id", target_id=target_id)

        # Build relationship type filter
        rel_type_filter = "|".join(rel_types)
        builder.match(f"p = (source)-[:{rel_type_filter}*1..{max_hops}]-(target)")
        builder.param("rel_types", rel_types)
        builder.param("max_hops", max_hops)

        return builder.return_("p", "length(p) as path_length").order_by("path_length ASC").limit(1)

    def entity_degree_distribution(self) -> CypherQueryBuilder:
        """Get degree distribution of entities.

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_degree_distribution().build()
        """
        return (
            CypherQueryBuilder()
            .match("(e:base)")
            .with_("e", "size((e)-[]-()) as degree")
            .return_("degree", "count(*) as entity_count")
            .order_by("degree ASC")
        )

    def connected_components(self, min_size: int = 2) -> CypherQueryBuilder:
        """Find connected components in the graph.

        Args:
            min_size: Minimum component size (default: 2)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.connected_components(min_size=5).build()
        """
        # Note: This requires graph algorithms plugin in production
        # Simplified version using manual traversal
        return (
            CypherQueryBuilder()
            .match("(e:base)")
            .where("e.component_id IS NOT NULL")
            .with_("e.component_id as component", "collect(e) as entities")
            .where("size(entities) >= $min_size", min_size=min_size)
            .return_("component", "size(entities) as component_size", "entities")
            .order_by("component_size DESC")
        )

    # ==========================================================================
    # SECTION-AWARE QUERIES (Sprint 62.1)
    # ==========================================================================

    def entities_in_section(
        self,
        section_heading: str,
        document_id: str | None = None,
        limit: int = 100,
    ) -> CypherQueryBuilder:
        """Find entities defined in a specific section.

        Args:
            section_heading: Section heading to filter by
            document_id: Optional document ID filter
            limit: Maximum results (default: 100)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entities_in_section("Introduction", document_id="doc_123").build()
        """
        builder = CypherQueryBuilder()
        builder.match("(s:Section)-[:DEFINES]->(e:base)")
        builder.where("s.heading = $section_heading", section_heading=section_heading)

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        return (
            builder.return_(
                "e",
                "e.name as name",
                "e.type as type",
                "s.heading as section",
                "s.level as level",
            )
            .order_by("e.name")
            .limit(limit)
        )

    def entities_in_sections(
        self,
        section_headings: list[str],
        document_id: str | None = None,
        limit: int = 100,
    ) -> CypherQueryBuilder:
        """Find entities in multiple sections.

        Args:
            section_headings: List of section headings
            document_id: Optional document ID filter
            limit: Maximum results (default: 100)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entities_in_sections(
            ...     ["Introduction", "Methods"],
            ...     document_id="doc_123"
            ... ).build()
        """
        builder = CypherQueryBuilder()
        builder.match("(s:Section)-[:DEFINES]->(e:base)")
        builder.where("s.heading IN $section_headings", section_headings=section_headings)

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        return (
            builder.return_(
                "e",
                "e.name as name",
                "collect(DISTINCT s.heading) as sections",
            )
            .order_by("e.name")
            .limit(limit)
        )

    def section_hierarchy(
        self,
        document_id: str,
        max_level: int | None = None,
    ) -> CypherQueryBuilder:
        """Get section hierarchy for a document.

        Args:
            document_id: Document ID
            max_level: Maximum heading level (default: all levels)

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.section_hierarchy("doc_123", max_level=3).build()
        """
        builder = CypherQueryBuilder()
        builder.match("(d:Document)-[:HAS_SECTION]->(s:Section)")
        builder.where("d.id = $document_id", document_id=document_id)

        if max_level:
            builder.where("s.level <= $max_level", max_level=max_level)

        return (
            builder.return_(
                "s.heading as heading",
                "s.level as level",
                "s.page_no as page",
                "s.order as order",
            )
            .order_by("s.order ASC")
        )

    def entity_sections(
        self,
        entity_id: str,
    ) -> CypherQueryBuilder:
        """Get sections where entity is defined.

        Args:
            entity_id: Entity ID or name

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.entity_sections("entity-123").build()
        """
        builder = CypherQueryBuilder()
        builder.match("(s:Section)-[:DEFINES]->(e:base)")

        # Match by ID or name
        if entity_id.startswith("entity-") or entity_id.startswith("id-"):
            builder.where("e.id = $entity_id", entity_id=entity_id)
        else:
            builder.where("e.name = $entity_id", entity_id=entity_id)

        return (
            builder.return_(
                "s.heading as heading",
                "s.level as level",
                "s.page_no as page",
                "s.order as order",
            )
            .order_by("s.order ASC")
        )

    def section_entities_count(
        self,
        document_id: str | None = None,
    ) -> CypherQueryBuilder:
        """Count entities per section.

        Args:
            document_id: Optional document ID filter

        Returns:
            CypherQueryBuilder instance

        Example:
            >>> templates.section_entities_count(document_id="doc_123").build()
        """
        builder = CypherQueryBuilder()
        builder.match("(s:Section)-[:DEFINES]->(e:base)")

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        return (
            builder.return_(
                "s.heading as section",
                "s.level as level",
                "count(e) as entity_count",
            )
            .order_by("entity_count DESC")
        )
