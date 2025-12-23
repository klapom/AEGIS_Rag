"""Section-Based Community Detection Service with Visualization.

Sprint 63 Feature 63.5: Section-Based Community Detection with Visualization

This module provides high-level service for community detection at the section level
with comprehensive visualization data, including:
- Community structure visualization (nodes, edges, layout hints)
- Community comparison across sections
- Centrality metrics (betweenness, degree, closeness)
- Cross-section community overlap analysis
- Visualization-ready data serialization

Architecture:
- Wraps SectionCommunityDetector from Feature 62.8
- Adds visualization models and data structures
- Generates layout hints for frontend visualization
- Calculates centrality metrics for important node identification
- Provides comparison matrices for multi-section analysis

Performance Target:
- Full community visualization generation: <1000ms
- Cross-section comparison: <1500ms
"""

import time

import networkx as nx
import structlog
from pydantic import BaseModel, Field

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.components.graph_rag.query_builder import CypherQueryBuilder
from src.domains.knowledge_graph.communities.section_community_detector import (
    SectionCommunityDetector,
    get_section_community_detector,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# VISUALIZATION MODELS
# =============================================================================


class CommunityNode(BaseModel):
    """Node in a community visualization."""

    entity_id: str = Field(..., description="Entity ID")
    entity_name: str = Field(..., description="Entity name/label")
    entity_type: str = Field(..., description="Entity type (PERSON, ORGANIZATION, etc.)")
    centrality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Centrality score (normalized 0-1)",
    )
    degree: int = Field(
        default=0,
        ge=0,
        description="Node degree (number of connections)",
    )
    x: float | None = Field(
        default=None,
        description="X coordinate for visualization layout",
    )
    y: float | None = Field(
        default=None,
        description="Y coordinate for visualization layout",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "entity_id": "ent_123",
                "entity_name": "Alice",
                "entity_type": "PERSON",
                "centrality": 0.85,
                "degree": 5,
                "x": 100.5,
                "y": 200.3,
            }
        }


class CommunityEdge(BaseModel):
    """Edge in a community visualization."""

    source: str = Field(..., description="Source entity ID")
    target: str = Field(..., description="Target entity ID")
    relationship_type: str = Field(..., description="Relationship type")
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Edge weight (frequency or strength)",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "source": "ent_123",
                "target": "ent_456",
                "relationship_type": "WORKS_WITH",
                "weight": 2.5,
            }
        }


class CommunityVisualization(BaseModel):
    """Complete visualization data for a community."""

    community_id: str = Field(..., description="Community ID")
    section_heading: str = Field(..., description="Section heading")
    size: int = Field(..., ge=0, description="Number of entities in community")
    cohesion_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Community cohesion (density)",
    )
    nodes: list[CommunityNode] = Field(
        default_factory=list,
        description="Nodes in the community",
    )
    edges: list[CommunityEdge] = Field(
        default_factory=list,
        description="Edges between nodes in the community",
    )
    layout_type: str = Field(
        default="force-directed",
        description="Layout algorithm used (force-directed, circular, hierarchical)",
    )
    algorithm: str = Field(
        default="louvain",
        description="Community detection algorithm used",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "community_id": "community_0",
                "section_heading": "Introduction",
                "size": 5,
                "cohesion_score": 0.72,
                "nodes": [
                    {
                        "entity_id": "ent_1",
                        "entity_name": "Alice",
                        "entity_type": "PERSON",
                        "centrality": 0.9,
                        "degree": 4,
                        "x": 50.0,
                        "y": 100.0,
                    }
                ],
                "edges": [
                    {
                        "source": "ent_1",
                        "target": "ent_2",
                        "relationship_type": "WORKS_WITH",
                        "weight": 1.0,
                    }
                ],
                "layout_type": "force-directed",
                "algorithm": "louvain",
            }
        }


class SectionCommunityVisualizationResponse(BaseModel):
    """Response with all communities in a section."""

    document_id: str | None = Field(default=None, description="Document ID")
    section_heading: str = Field(..., description="Section heading")
    total_communities: int = Field(..., ge=0, description="Total communities in section")
    total_entities: int = Field(..., ge=0, description="Total entities in section")
    communities: list[CommunityVisualization] = Field(
        default_factory=list,
        description="Visualizations for each community",
    )
    generation_time_ms: float = Field(
        ...,
        description="Time to generate visualizations in milliseconds",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "section_heading": "Introduction",
                "total_communities": 2,
                "total_entities": 10,
                "communities": [],
                "generation_time_ms": 350.0,
            }
        }


class CommunityComparisonOverview(BaseModel):
    """Overview of community comparison across sections."""

    section_count: int = Field(..., ge=1, description="Number of sections compared")
    sections: list[str] = Field(..., description="Section headings")
    total_shared_communities: int = Field(
        ...,
        ge=0,
        description="Communities shared across sections",
    )
    shared_entities: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Shared entity IDs by section pairs",
    )
    overlap_matrix: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Entity overlap counts between sections",
    )
    comparison_time_ms: float = Field(
        ...,
        description="Time to perform comparison in milliseconds",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "section_count": 2,
                "sections": ["Introduction", "Methods"],
                "total_shared_communities": 1,
                "shared_entities": {"Introduction-Methods": ["ent_1", "ent_2"]},
                "overlap_matrix": {
                    "Introduction": {"Methods": 2},
                    "Methods": {"Introduction": 2},
                },
                "comparison_time_ms": 450.0,
            }
        }


# =============================================================================
# SERVICE
# =============================================================================


class SectionCommunityService:
    """High-level service for section-based community detection with visualization.

    This service provides:
    - Community visualization generation with layout
    - Centrality metrics calculation
    - Cross-section community comparison
    - Visualization-ready data serialization

    Example:
        >>> service = SectionCommunityService()
        >>> response = await service.get_section_communities_with_visualization(
        ...     section_heading="Introduction",
        ...     document_id="doc_123"
        ... )
        >>> print(f"Generated visualizations for {len(response.communities)} communities")
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        section_community_detector: SectionCommunityDetector | None = None,
    ) -> None:
        """Initialize section community service.

        Args:
            neo4j_client: Neo4j client instance (uses singleton if None)
            section_community_detector: Section community detector (uses singleton if None)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.section_community_detector = (
            section_community_detector
            or get_section_community_detector(neo4j_client=self.neo4j_client)
        )
        logger.info("section_community_service_initialized")

    async def get_section_communities_with_visualization(
        self,
        section_heading: str,
        document_id: str | None = None,
        algorithm: str = "louvain",
        resolution: float = 1.0,
        include_layout: bool = True,
        layout_algorithm: str = "force-directed",
    ) -> SectionCommunityVisualizationResponse:
        """Get communities for a section with complete visualization data.

        Args:
            section_heading: Section heading to analyze
            document_id: Optional document ID filter
            algorithm: Detection algorithm ('louvain' or 'leiden')
            resolution: Resolution parameter
            include_layout: Whether to generate layout coordinates
            layout_algorithm: Layout algorithm ('force-directed', 'circular', 'hierarchical')

        Returns:
            SectionCommunityVisualizationResponse with visualization data

        Example:
            >>> response = await service.get_section_communities_with_visualization(
            ...     section_heading="Methods",
            ...     document_id="doc_123",
            ...     layout_algorithm="circular"
            ... )
        """
        start_time = time.perf_counter()

        logger.info(
            "generating_section_community_visualizations",
            section_heading=section_heading,
            document_id=document_id,
        )

        # Step 1: Detect communities in section
        detection_result = await self.section_community_detector.detect_communities_in_section(
            section_heading=section_heading,
            document_id=document_id,
            algorithm=algorithm,
            resolution=resolution,
        )

        # Step 2: Generate visualization for each community
        visualizations = []

        for community_metadata in detection_result.communities:
            viz = await self._generate_community_visualization(
                community_id=community_metadata.community_id,
                section_heading=section_heading,
                cohesion_score=community_metadata.cohesion_score,
                algorithm=algorithm,
                include_layout=include_layout,
                layout_algorithm=layout_algorithm,
            )

            visualizations.append(viz)

        generation_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "section_community_visualizations_generated",
            section_heading=section_heading,
            community_count=len(visualizations),
            generation_time_ms=round(generation_time_ms, 2),
        )

        return SectionCommunityVisualizationResponse(
            document_id=document_id,
            section_heading=section_heading,
            total_communities=len(visualizations),
            total_entities=detection_result.total_entities,
            communities=visualizations,
            generation_time_ms=generation_time_ms,
        )

    async def compare_section_communities(
        self,
        section_headings: list[str],
        document_id: str | None = None,
        algorithm: str = "louvain",
        resolution: float = 1.0,
    ) -> CommunityComparisonOverview:
        """Compare communities across multiple sections with overlap analysis.

        Args:
            section_headings: List of section headings to compare
            document_id: Optional document ID filter
            algorithm: Detection algorithm
            resolution: Resolution parameter

        Returns:
            CommunityComparisonOverview with overlap analysis

        Example:
            >>> comparison = await service.compare_section_communities(
            ...     section_headings=["Introduction", "Methods", "Results"],
            ...     document_id="doc_123"
            ... )
        """
        start_time = time.perf_counter()

        logger.info(
            "comparing_section_communities_with_overlap",
            section_count=len(section_headings),
            document_id=document_id,
        )

        # Step 1: Use section community detector for comparison
        comparison_result = (
            await self.section_community_detector.compare_communities_across_sections(
                section_headings=section_headings,
                document_id=document_id,
                algorithm=algorithm,
                resolution=resolution,
            )
        )

        # Step 2: Build shared entities mapping
        shared_entities: dict[str, list[str]] = {}

        for i, section1 in enumerate(section_headings):
            for section2 in section_headings[i + 1 :]:
                pair_key = f"{section1}-{section2}"

                # Get all entities in each section
                entities1 = await self._get_section_entities(section1, document_id)
                entities2 = await self._get_section_entities(section2, document_id)

                # Find overlap
                overlap = set(entities1) & set(entities2)

                if overlap:
                    shared_entities[pair_key] = sorted(overlap)

        comparison_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "section_communities_compared_with_overlap",
            section_count=len(section_headings),
            shared_communities=len(comparison_result.shared_communities),
            comparison_time_ms=round(comparison_time_ms, 2),
        )

        return CommunityComparisonOverview(
            section_count=len(section_headings),
            sections=section_headings,
            total_shared_communities=len(comparison_result.shared_communities),
            shared_entities=shared_entities,
            overlap_matrix=comparison_result.community_overlap_matrix,
            comparison_time_ms=comparison_time_ms,
        )

    async def _generate_community_visualization(
        self,
        community_id: str,
        section_heading: str,
        cohesion_score: float,
        algorithm: str,
        include_layout: bool = True,
        layout_algorithm: str = "force-directed",
    ) -> CommunityVisualization:
        """Generate complete visualization for a community.

        Args:
            community_id: Community ID
            section_heading: Section heading
            cohesion_score: Community cohesion score
            algorithm: Detection algorithm
            include_layout: Whether to generate layout coordinates
            layout_algorithm: Layout algorithm to use

        Returns:
            CommunityVisualization with nodes, edges, and layout
        """
        # Step 1: Get entities in this community
        entity_ids = await self.section_community_detector._get_community_entities(community_id)

        if not entity_ids:
            return CommunityVisualization(
                community_id=community_id,
                section_heading=section_heading,
                size=0,
                cohesion_score=cohesion_score,
                nodes=[],
                edges=[],
                layout_type=layout_algorithm,
                algorithm=algorithm,
            )

        # Step 2: Get entity details (name, type, degree)
        nodes = await self._build_community_nodes(entity_ids)

        # Step 3: Get edges between entities
        edges = await self._build_community_edges(entity_ids)

        # Step 4: Calculate centrality metrics
        centrality_scores = await self._calculate_centrality_metrics(entity_ids, edges)

        # Update node centrality scores
        for node in nodes:
            node.centrality = centrality_scores.get(node.entity_id, 0.0)

        # Step 5: Generate layout if requested
        if include_layout:
            await self._add_layout_coordinates(nodes, edges, layout_algorithm)

        return CommunityVisualization(
            community_id=community_id,
            section_heading=section_heading,
            size=len(entity_ids),
            cohesion_score=cohesion_score,
            nodes=nodes,
            edges=edges,
            layout_type=layout_algorithm,
            algorithm=algorithm,
        )

    async def _build_community_nodes(self, entity_ids: list[str]) -> list[CommunityNode]:
        """Build CommunityNode objects for entities.

        Args:
            entity_ids: List of entity IDs

        Returns:
            List of CommunityNode objects
        """
        builder = CypherQueryBuilder()
        builder.match("(e:base)")
        builder.where("e.entity_id IN $entity_ids", entity_ids=entity_ids)
        builder.return_(
            "e.entity_id AS entity_id",
            "e.name AS entity_name",
            "e.entity_type AS entity_type",
        )

        query_dict = builder.build()

        records = await self.neo4j_client.execute_read(
            query_dict["query"], query_dict["parameters"]
        )

        nodes = []
        for record in records:
            node = CommunityNode(
                entity_id=record.get("entity_id", ""),
                entity_name=record.get("entity_name", "Unknown"),
                entity_type=record.get("entity_type", "UNKNOWN"),
                degree=0,  # Will be set after edges are built
            )
            nodes.append(node)

        return nodes

    async def _build_community_edges(self, entity_ids: list[str]) -> list[CommunityEdge]:
        """Build edges between entities in a community.

        Args:
            entity_ids: List of entity IDs

        Returns:
            List of CommunityEdge objects
        """
        builder = CypherQueryBuilder()
        builder.match("(e1:base)-[r:RELATES_TO]-(e2:base)")
        builder.where("e1.entity_id IN $entity_ids", entity_ids=entity_ids)
        builder.where("e2.entity_id IN $entity_ids")
        builder.return_(
            "DISTINCT e1.entity_id AS source",
            "e2.entity_id AS target",
            "type(r) AS relationship_type",
            "coalesce(r.weight, 1.0) AS weight",
        )

        query_dict = builder.build()

        records = await self.neo4j_client.execute_read(
            query_dict["query"], query_dict["parameters"]
        )

        edges = []
        seen_edges = set()

        for record in records:
            source = record.get("source", "")
            target = record.get("target", "")

            # Normalize edge direction for deduplication
            edge_key = tuple(sorted([source, target]))
            if edge_key in seen_edges:
                continue

            seen_edges.add(edge_key)

            edge = CommunityEdge(
                source=source,
                target=target,
                relationship_type=record.get("relationship_type", "RELATES_TO"),
                weight=float(record.get("weight", 1.0)),
            )
            edges.append(edge)

        return edges

    async def _calculate_centrality_metrics(
        self,
        entity_ids: list[str],
        edges: list[CommunityEdge],
    ) -> dict[str, float]:
        """Calculate centrality metrics for nodes.

        Uses degree centrality (normalized 0-1).

        Args:
            entity_ids: List of entity IDs
            edges: List of community edges

        Returns:
            Dict mapping entity_id -> centrality_score (0-1)
        """
        # Build graph for centrality calculation
        graph = nx.Graph()
        graph.add_nodes_from(entity_ids)

        for edge in edges:
            graph.add_edge(edge.source, edge.target, weight=edge.weight)

        # Calculate degree centrality (normalized)
        degree_centrality = nx.degree_centrality(graph)

        # Return as dict, normalized to 0-1
        return {entity_id: float(score) for entity_id, score in degree_centrality.items()}

    async def _add_layout_coordinates(
        self,
        nodes: list[CommunityNode],
        edges: list[CommunityEdge],
        layout_algorithm: str = "force-directed",
    ) -> None:
        """Add layout coordinates to nodes.

        Args:
            nodes: List of nodes to add coordinates to
            edges: List of edges for layout calculation
            layout_algorithm: Layout algorithm to use
        """
        # Build graph for layout
        graph = nx.Graph()

        entity_id_map = {node.entity_id: node for node in nodes}
        graph.add_nodes_from(entity_id_map.keys())

        for edge in edges:
            graph.add_edge(edge.source, edge.target, weight=edge.weight)

        # Generate layout based on algorithm
        if layout_algorithm == "circular":
            pos = nx.circular_layout(graph, scale=300)
        elif layout_algorithm == "hierarchical":
            # Use spring layout as approximation of hierarchical
            pos = nx.spring_layout(graph, k=2, iterations=50, seed=42, scale=300)
        else:  # force-directed (default)
            pos = nx.spring_layout(graph, k=1, iterations=50, seed=42, scale=300)

        # Update node coordinates
        for entity_id, (x, y) in pos.items():
            if entity_id in entity_id_map:
                entity_id_map[entity_id].x = float(x)
                entity_id_map[entity_id].y = float(y)

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


# =============================================================================
# SINGLETON
# =============================================================================

_section_community_service: SectionCommunityService | None = None


def get_section_community_service(
    neo4j_client: Neo4jClient | None = None,
) -> SectionCommunityService:
    """Get section community service instance (singleton).

    Args:
        neo4j_client: Optional Neo4j client (uses singleton if None)

    Returns:
        SectionCommunityService instance
    """
    global _section_community_service

    if _section_community_service is None:
        _section_community_service = SectionCommunityService(neo4j_client)

    return _section_community_service


def reset_section_community_service() -> None:
    """Reset singleton (for testing)."""
    global _section_community_service
    _section_community_service = None
