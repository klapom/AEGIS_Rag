"""Section-Based Community Detection Service.

Sprint 62 Feature 62.8: Section-Based Community Detection (3 SP)

This module applies graph community detection algorithms to section-level entities
to discover thematic clusters within specific sections.

Features:
- Louvain community detection for Neo4j
- Section-scoped community detection
- Cross-section community comparison
- Community metadata storage (id, size, cohesion score)
- BELONGS_TO_COMMUNITY relationships in Neo4j

Architecture:
- Leverages existing CommunityDetector (Louvain/Leiden algorithms)
- Extends with section-scoped queries
- Stores community metadata on Section nodes
- Creates BELONGS_TO_COMMUNITY relationships
- Supports community comparison across sections

Performance Target:
- Community detection per section: <500ms
- Cross-section comparison: <1000ms
"""

import time
from typing import Any

import networkx as nx
import structlog
from pydantic import BaseModel, Field

from src.components.graph_rag.community_detector import CommunityDetector
from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.components.graph_rag.query_builder import CypherQueryBuilder
from src.core.models import Community

logger = structlog.get_logger(__name__)


# =============================================================================
# MODELS
# =============================================================================


class SectionCommunityMetadata(BaseModel):
    """Community metadata for a section."""

    community_id: str = Field(..., description="Community ID (e.g., 'community_0')")
    section_heading: str = Field(..., description="Section heading")
    section_id: str | None = Field(default=None, description="Neo4j section node ID")
    entity_count: int = Field(..., ge=0, description="Number of entities in community")
    cohesion_score: float = Field(..., ge=0.0, le=1.0, description="Community cohesion (density)")
    is_section_specific: bool = Field(
        default=True,
        description="True if community is specific to this section only",
    )


class SectionCommunityResult(BaseModel):
    """Result of section-based community detection."""

    section_heading: str = Field(..., description="Section heading")
    section_id: str | None = Field(default=None, description="Neo4j section node ID")
    communities: list[SectionCommunityMetadata] = Field(
        default_factory=list,
        description="Communities detected in this section",
    )
    detection_time_ms: float = Field(..., description="Detection time in milliseconds")
    total_entities: int = Field(..., ge=0, description="Total entities in section")
    algorithm: str = Field(default="louvain", description="Detection algorithm used")
    resolution: float = Field(default=1.0, description="Resolution parameter")


class CrossSectionCommunityComparison(BaseModel):
    """Comparison of communities across sections."""

    section_specific_communities: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Map of section heading to section-specific community IDs",
    )
    shared_communities: list[str] = Field(
        default_factory=list,
        description="Community IDs that span multiple sections",
    )
    community_overlap_matrix: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Overlap matrix: section -> section -> shared entity count",
    )
    comparison_time_ms: float = Field(..., description="Comparison time in milliseconds")


# =============================================================================
# SERVICE
# =============================================================================


class SectionCommunityDetector:
    """Service for section-based community detection.

    This service extends community detection to work at the section level:
    - Detect communities within specific sections
    - Compare communities across sections
    - Identify section-specific vs. cross-section communities
    - Store community metadata and relationships

    Example:
        >>> detector = SectionCommunityDetector()
        >>> result = await detector.detect_communities_in_section(
        ...     section_heading="Introduction",
        ...     document_id="doc_123"
        ... )
        >>> print(f"Found {len(result.communities)} communities")
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        community_detector: CommunityDetector | None = None,
    ) -> None:
        """Initialize section community detector.

        Args:
            neo4j_client: Neo4j client instance (uses singleton if None)
            community_detector: Community detector instance (uses singleton if None)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.community_detector = community_detector or CommunityDetector(
            neo4j_client=self.neo4j_client
        )
        logger.info("section_community_detector_initialized")

    async def detect_communities_in_section(
        self,
        section_heading: str,
        document_id: str | None = None,
        algorithm: str = "louvain",
        resolution: float = 1.0,
        min_size: int = 2,
    ) -> SectionCommunityResult:
        """Detect communities within a specific section.

        Args:
            section_heading: Section heading to analyze
            document_id: Optional document ID filter
            algorithm: Detection algorithm ('louvain' or 'leiden')
            resolution: Resolution parameter (higher = more communities)
            min_size: Minimum community size (default: 2)

        Returns:
            SectionCommunityResult with detected communities

        Example:
            >>> result = await detector.detect_communities_in_section(
            ...     section_heading="Methods",
            ...     document_id="doc_123",
            ...     resolution=1.5
            ... )
        """
        start_time = time.perf_counter()

        logger.info(
            "detecting_section_communities",
            section_heading=section_heading,
            document_id=document_id,
            algorithm=algorithm,
        )

        # Step 1: Get all entities in this section
        entities = await self._get_section_entities(section_heading, document_id)

        if not entities:
            logger.warning("no_entities_in_section", section_heading=section_heading)
            return SectionCommunityResult(
                section_heading=section_heading,
                section_id=None,
                communities=[],
                detection_time_ms=0.0,
                total_entities=0,
                algorithm=algorithm,
                resolution=resolution,
            )

        # Step 2: Get section ID
        section_id = await self._get_section_id(section_heading, document_id)

        # Step 3: Build subgraph for this section
        graph = await self._build_section_subgraph(entities)

        # Step 4: Run community detection on subgraph
        communities = await self._detect_communities_networkx(graph, algorithm, resolution)

        # Step 5: Filter by minimum size
        communities = [c for c in communities if c.size >= min_size]

        # Step 6: Store communities in Neo4j
        await self._store_section_communities(communities, section_heading, section_id)

        # Step 7: Create community metadata
        community_metadata_list = []
        for community in communities:
            cohesion_score = self._calculate_cohesion(graph, community.entity_ids)

            metadata = SectionCommunityMetadata(
                community_id=community.id,
                section_heading=section_heading,
                section_id=section_id,
                entity_count=community.size,
                cohesion_score=cohesion_score,
                is_section_specific=True,  # Will be updated in cross-section comparison
            )
            community_metadata_list.append(metadata)

        detection_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "section_communities_detected",
            section_heading=section_heading,
            communities_count=len(communities),
            total_entities=len(entities),
            detection_time_ms=round(detection_time_ms, 2),
        )

        return SectionCommunityResult(
            section_heading=section_heading,
            section_id=section_id,
            communities=community_metadata_list,
            detection_time_ms=detection_time_ms,
            total_entities=len(entities),
            algorithm=algorithm,
            resolution=resolution,
        )

    async def compare_communities_across_sections(
        self,
        section_headings: list[str],
        document_id: str | None = None,
        algorithm: str = "louvain",
        resolution: float = 1.0,
    ) -> CrossSectionCommunityComparison:
        """Compare communities across multiple sections.

        Identifies which communities are section-specific vs. shared across sections.

        Args:
            section_headings: List of section headings to compare
            document_id: Optional document ID filter
            algorithm: Detection algorithm
            resolution: Resolution parameter

        Returns:
            CrossSectionCommunityComparison with overlap analysis

        Example:
            >>> comparison = await detector.compare_communities_across_sections(
            ...     section_headings=["Introduction", "Methods", "Results"],
            ...     document_id="doc_123"
            ... )
        """
        start_time = time.perf_counter()

        logger.info(
            "comparing_section_communities",
            section_count=len(section_headings),
            document_id=document_id,
        )

        # Step 1: Detect communities in each section
        section_results: dict[str, SectionCommunityResult] = {}

        for section_heading in section_headings:
            result = await self.detect_communities_in_section(
                section_heading=section_heading,
                document_id=document_id,
                algorithm=algorithm,
                resolution=resolution,
            )
            section_results[section_heading] = result

        # Step 2: Build entity-to-sections mapping
        entity_sections: dict[str, set[str]] = {}

        for section_heading, result in section_results.items():
            for community in result.communities:
                # Get entities in this community
                entities = await self._get_community_entities(community.community_id)
                for entity_id in entities:
                    if entity_id not in entity_sections:
                        entity_sections[entity_id] = set()
                    entity_sections[entity_id].add(section_heading)

        # Step 3: Identify section-specific vs. shared communities
        section_specific_communities: dict[str, list[str]] = {s: [] for s in section_headings}
        shared_communities: list[str] = []

        for section_heading, result in section_results.items():
            for community in result.communities:
                entities = await self._get_community_entities(community.community_id)

                # Check if all entities are only in this section
                is_section_specific = all(
                    entity_sections.get(entity_id, set()) == {section_heading}
                    for entity_id in entities
                )

                if is_section_specific:
                    section_specific_communities[section_heading].append(community.community_id)
                else:
                    if community.community_id not in shared_communities:
                        shared_communities.append(community.community_id)

        # Step 4: Build overlap matrix
        overlap_matrix: dict[str, dict[str, int]] = {}

        for section1 in section_headings:
            overlap_matrix[section1] = {}
            for section2 in section_headings:
                if section1 == section2:
                    overlap_matrix[section1][section2] = 0
                    continue

                # Count entities that appear in both sections
                entities1 = set()
                for community in section_results[section1].communities:
                    entities = await self._get_community_entities(community.community_id)
                    entities1.update(entities)

                entities2 = set()
                for community in section_results[section2].communities:
                    entities = await self._get_community_entities(community.community_id)
                    entities2.update(entities)

                overlap_count = len(entities1 & entities2)
                overlap_matrix[section1][section2] = overlap_count

        comparison_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "section_communities_compared",
            section_count=len(section_headings),
            shared_communities_count=len(shared_communities),
            comparison_time_ms=round(comparison_time_ms, 2),
        )

        return CrossSectionCommunityComparison(
            section_specific_communities=section_specific_communities,
            shared_communities=shared_communities,
            community_overlap_matrix=overlap_matrix,
            comparison_time_ms=comparison_time_ms,
        )

    async def _get_section_entities(
        self, section_heading: str, document_id: str | None = None
    ) -> list[str]:
        """Get all entity IDs in a section.

        Args:
            section_heading: Section heading
            document_id: Optional document ID filter

        Returns:
            List of entity IDs
        """
        builder = CypherQueryBuilder()
        builder.match("(s:Section)-[:DEFINES]->(e:base)")
        builder.where("s.heading = $section_heading", section_heading=section_heading)

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        builder.return_("e.entity_id AS entity_id")

        query_dict = builder.build()

        records = await self.neo4j_client.execute_read(
            query_dict["query"], query_dict["parameters"]
        )

        return [r["entity_id"] for r in records if r.get("entity_id")]

    async def _get_section_id(
        self, section_heading: str, document_id: str | None = None
    ) -> str | None:
        """Get Neo4j section node ID.

        Args:
            section_heading: Section heading
            document_id: Optional document ID filter

        Returns:
            Section node ID or None
        """
        builder = CypherQueryBuilder()
        builder.match("(s:Section)")
        builder.where("s.heading = $section_heading", section_heading=section_heading)

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        builder.return_("elementId(s) AS section_id")
        builder.limit(1)

        query_dict = builder.build()

        records = await self.neo4j_client.execute_read(
            query_dict["query"], query_dict["parameters"]
        )

        if records and records[0].get("section_id"):
            return str(records[0]["section_id"])

        return None

    async def _build_section_subgraph(self, entity_ids: list[str]) -> nx.Graph:
        """Build NetworkX subgraph for entities in a section.

        Args:
            entity_ids: List of entity IDs

        Returns:
            NetworkX graph containing only section entities
        """
        graph = nx.Graph()

        # Add nodes
        graph.add_nodes_from(entity_ids)

        # Get relationships between these entities
        builder = CypherQueryBuilder()
        builder.match("(e1:base)-[r:RELATES_TO]-(e2:base)")
        builder.where("e1.entity_id IN $entity_ids", entity_ids=entity_ids)
        builder.where("e2.entity_id IN $entity_ids")
        builder.return_("DISTINCT e1.entity_id AS source", "e2.entity_id AS target")

        query_dict = builder.build()

        records = await self.neo4j_client.execute_read(
            query_dict["query"], query_dict["parameters"]
        )

        # Add edges
        for record in records:
            source = record.get("source")
            target = record.get("target")
            if source and target and source != target:
                graph.add_edge(source, target)

        logger.debug(
            "section_subgraph_built",
            nodes=graph.number_of_nodes(),
            edges=graph.number_of_edges(),
        )

        return graph

    async def _detect_communities_networkx(
        self, graph: nx.Graph, algorithm: str, resolution: float
    ) -> list[Community]:
        """Run community detection on NetworkX graph.

        Args:
            graph: NetworkX graph
            algorithm: 'louvain' or 'leiden'
            resolution: Resolution parameter

        Returns:
            List of Community objects
        """
        # Use Louvain algorithm (NetworkX doesn't have Leiden)
        if algorithm.lower() == "leiden":
            logger.warning("leiden_not_available_using_louvain")
            algorithm = "louvain"

        communities_generator = nx.community.louvain_communities(
            graph, resolution=resolution, seed=42
        )

        communities = []
        for idx, community_nodes in enumerate(communities_generator):
            entity_ids = list(community_nodes)
            density = self._calculate_density(graph, entity_ids)

            community = Community(
                id=f"section_community_{idx}",
                label="",  # Will be filled by labeler if needed
                entity_ids=entity_ids,
                size=len(entity_ids),
                density=density,
                metadata={
                    "algorithm": algorithm,
                    "resolution": resolution,
                    "method": "networkx",
                    "scope": "section",
                },
            )
            communities.append(community)

        logger.debug("communities_detected_networkx", count=len(communities))

        return communities

    def _calculate_density(self, graph: nx.Graph, nodes: list[str]) -> float:
        """Calculate density of a subgraph.

        Args:
            graph: NetworkX graph
            nodes: Nodes in the community

        Returns:
            Density (0.0 to 1.0)
        """
        if len(nodes) < 2:
            return 0.0

        subgraph = graph.subgraph(nodes)
        return nx.density(subgraph)

    def _calculate_cohesion(self, graph: nx.Graph, nodes: list[str]) -> float:
        """Calculate community cohesion score (same as density).

        Args:
            graph: NetworkX graph
            nodes: Nodes in the community

        Returns:
            Cohesion score (0.0 to 1.0)
        """
        return self._calculate_density(graph, nodes)

    async def _store_section_communities(
        self,
        communities: list[Community],
        section_heading: str,
        section_id: str | None,
    ) -> None:
        """Store community information in Neo4j.

        Creates BELONGS_TO_COMMUNITY relationships and stores metadata.

        Args:
            communities: List of Community objects
            section_heading: Section heading
            section_id: Neo4j section node ID
        """
        logger.info(
            "storing_section_communities",
            count=len(communities),
            section_heading=section_heading,
        )

        try:
            for community in communities:
                # Create BELONGS_TO_COMMUNITY relationships
                cypher = """
                UNWIND $entity_ids AS entity_id
                MATCH (e:base {entity_id: entity_id})
                MATCH (s:Section {heading: $section_heading})
                MERGE (e)-[r:BELONGS_TO_COMMUNITY]->(c:Community {
                    community_id: $community_id,
                    section_heading: $section_heading
                })
                ON CREATE SET
                    c.created_at = datetime(),
                    c.size = $size,
                    c.density = $density,
                    c.algorithm = $algorithm,
                    c.resolution = $resolution
                ON MATCH SET
                    c.updated_at = datetime(),
                    c.size = $size,
                    c.density = $density
                SET r.assigned_at = datetime()
                RETURN count(r) AS relationships_created
                """

                result = await self.neo4j_client.execute_write(
                    cypher,
                    {
                        "entity_ids": community.entity_ids,
                        "section_heading": section_heading,
                        "community_id": community.id,
                        "size": community.size,
                        "density": community.density,
                        "algorithm": community.metadata.get("algorithm", "unknown"),
                        "resolution": community.metadata.get("resolution", 1.0),
                    },
                )

                relationships_count = result[0].get("relationships_created", 0) if result else 0

                logger.debug(
                    "community_stored",
                    community_id=community.id,
                    relationships_created=relationships_count,
                )

                # Update section node with community metadata
                if section_id:
                    await self._update_section_community_metadata(section_heading, len(communities))

        except Exception as e:
            logger.error(
                "store_section_communities_failed",
                section_heading=section_heading,
                error=str(e),
            )
            raise

    async def _update_section_community_metadata(
        self, section_heading: str, community_count: int
    ) -> None:
        """Update section node with community metadata.

        Args:
            section_heading: Section heading
            community_count: Number of communities detected
        """
        cypher = """
        MATCH (s:Section {heading: $section_heading})
        SET s.community_count = $community_count,
            s.last_community_detection = datetime()
        RETURN s.heading AS heading
        """

        await self.neo4j_client.execute_write(
            cypher,
            {
                "section_heading": section_heading,
                "community_count": community_count,
            },
        )

    async def _get_community_entities(self, community_id: str) -> list[str]:
        """Get entity IDs in a community.

        Args:
            community_id: Community ID

        Returns:
            List of entity IDs
        """
        cypher = """
        MATCH (e:base)-[:BELONGS_TO_COMMUNITY]->(c:Community {community_id: $community_id})
        RETURN e.entity_id AS entity_id
        """

        records = await self.neo4j_client.execute_read(cypher, {"community_id": community_id})

        return [r["entity_id"] for r in records if r.get("entity_id")]

    async def get_section_communities(
        self, section_heading: str, document_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all communities for a section.

        Args:
            section_heading: Section heading
            document_id: Optional document ID filter

        Returns:
            List of community dictionaries with metadata
        """
        builder = CypherQueryBuilder()
        builder.match("(s:Section {heading: $section_heading})")
        builder.match("(e:base)-[:BELONGS_TO_COMMUNITY]->(c:Community)")
        builder.match("(s)-[:DEFINES]->(e)")

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        builder.return_(
            "c.community_id AS community_id",
            "c.size AS size",
            "c.density AS density",
            "c.algorithm AS algorithm",
            "collect(e.entity_id) AS entity_ids",
        )

        params = {"section_heading": section_heading}
        if document_id:
            params["document_id"] = document_id

        query_dict = builder.build()

        records = await self.neo4j_client.execute_read(
            query_dict["query"], {**query_dict["parameters"], **params}
        )

        return records


# =============================================================================
# SINGLETON
# =============================================================================

_section_community_detector: SectionCommunityDetector | None = None


def get_section_community_detector(
    neo4j_client: Neo4jClient | None = None,
) -> SectionCommunityDetector:
    """Get section community detector instance (singleton).

    Args:
        neo4j_client: Optional Neo4j client (uses singleton if None)

    Returns:
        SectionCommunityDetector instance
    """
    global _section_community_detector

    if _section_community_detector is None:
        _section_community_detector = SectionCommunityDetector(neo4j_client)

    return _section_community_detector


def reset_section_community_detector() -> None:
    """Reset singleton (for testing)."""
    global _section_community_detector
    _section_community_detector = None
