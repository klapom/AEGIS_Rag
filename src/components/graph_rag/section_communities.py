"""Section Community Detection with Graph-Based Navigation.

Sprint 68 Feature 68.5: Section Community Detection (10 SP)

This module implements graph-based section community detection to improve
document structure understanding and navigation. It builds on Sprint 62's
section-based community detection by adding semantic clustering and
cross-document navigation capabilities.

Features:
- Section graph construction (PARENT_OF, SIMILAR_TO, REFERENCES, FOLLOWS)
- Louvain community detection for semantic clustering
- Neo4j schema for Community nodes and relationships
- Community-based retrieval for cross-document navigation

Architecture:
- Extends SectionCommunityDetector from Sprint 62 Feature 62.8
- Adds semantic similarity edges between sections
- Implements citation/reference detection
- Supports sequential section relationships
- Enables cross-document section queries

Performance Targets:
- Section graph construction: <1000ms for 100 sections
- Community detection: <500ms per document
- Community-based retrieval: <200ms
"""

import hashlib
import time
from typing import Any

import networkx as nx
import numpy as np
import structlog
from pydantic import BaseModel, Field

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.components.graph_rag.query_builder import CypherQueryBuilder
from src.core.models import Community

logger = structlog.get_logger(__name__)

# Constants
DEFAULT_SIMILARITY_THRESHOLD = 0.8
DEFAULT_TOP_K_COMMUNITIES = 5
DEFAULT_COMMUNITY_MIN_SIZE = 2


# =============================================================================
# MODELS
# =============================================================================


class SectionNode(BaseModel):
    """Section node for graph construction."""

    id: str = Field(..., description="Unique section ID")
    heading: str = Field(..., description="Section heading text")
    content: str = Field(..., description="Section content text")
    embedding: list[float] | None = Field(default=None, description="Section embedding vector")
    level: int = Field(..., ge=1, le=6, description="Heading level (1=title, 2=subtitle, etc.)")
    doc_id: str = Field(..., description="Document ID")
    page_no: int = Field(default=0, ge=0, description="Page number")
    sequence: int = Field(default=0, ge=0, description="Sequential position in document")


class SectionEdge(BaseModel):
    """Edge between sections in the graph."""

    source: str = Field(..., description="Source section ID")
    target: str = Field(..., description="Target section ID")
    edge_type: str = Field(
        ...,
        description="Edge type (PARENT_OF, SIMILAR_TO, REFERENCES, FOLLOWS)",
    )
    weight: float = Field(default=1.0, ge=0.0, description="Edge weight")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SectionGraph(BaseModel):
    """Complete section graph representation."""

    nodes: list[SectionNode] = Field(default_factory=list, description="Section nodes")
    edges: list[SectionEdge] = Field(default_factory=list, description="Section edges")
    node_count: int = Field(default=0, ge=0, description="Total number of nodes")
    edge_count: int = Field(default=0, ge=0, description="Total number of edges")
    construction_time_ms: float = Field(default=0.0, description="Graph construction time")


class CommunityDetectionResult(BaseModel):
    """Result of community detection on section graph."""

    communities: list[Community] = Field(default_factory=list, description="Detected communities")
    community_count: int = Field(default=0, ge=0, description="Number of communities")
    modularity: float = Field(
        default=0.0,
        description="Modularity score (quality metric)",
    )
    detection_time_ms: float = Field(default=0.0, description="Detection time in milliseconds")
    algorithm: str = Field(default="louvain", description="Algorithm used")


class CommunityRetrievalResult(BaseModel):
    """Result of community-based retrieval."""

    query: str = Field(..., description="Original query")
    communities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved communities",
    )
    sections: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Sections in communities",
    )
    retrieval_time_ms: float = Field(default=0.0, description="Retrieval time")
    total_sections: int = Field(default=0, ge=0, description="Total sections retrieved")


# =============================================================================
# SECTION GRAPH CONSTRUCTION
# =============================================================================


class SectionGraphBuilder:
    """Builder for constructing section graphs with relationships."""

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        """Initialize section graph builder.

        Args:
            neo4j_client: Neo4j client instance (uses singleton if None)
            similarity_threshold: Cosine similarity threshold for SIMILAR_TO edges
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.similarity_threshold = similarity_threshold
        logger.info(
            "section_graph_builder_initialized",
            similarity_threshold=similarity_threshold,
        )

    async def build_section_graph(
        self,
        document_id: str | None = None,
    ) -> SectionGraph:
        """Build section graph with all relationship types.

        Constructs a graph of sections with four edge types:
        1. PARENT_OF: Hierarchical relationship (heading → subsection)
        2. SIMILAR_TO: Semantic similarity (cosine > threshold)
        3. REFERENCES: Citation/link between sections
        4. FOLLOWS: Sequential relationship (section N → section N+1)

        Args:
            document_id: Optional document ID filter (None = all documents)

        Returns:
            SectionGraph with nodes and edges

        Example:
            >>> builder = SectionGraphBuilder()
            >>> graph = await builder.build_section_graph(document_id="doc_123")
            >>> print(f"Built graph with {graph.node_count} nodes")
        """
        start_time = time.perf_counter()

        logger.info("building_section_graph", document_id=document_id)

        # Step 1: Fetch all sections from Neo4j
        sections = await self._fetch_sections(document_id)

        if not sections:
            logger.warning("no_sections_found", document_id=document_id)
            return SectionGraph()

        # Step 2: Create section nodes
        nodes = self._create_section_nodes(sections)

        # Step 3: Create edges
        edges: list[SectionEdge] = []

        # 3.1: Hierarchical edges (PARENT_OF)
        hierarchical_edges = self._create_hierarchical_edges(sections)
        edges.extend(hierarchical_edges)

        # 3.2: Semantic similarity edges (SIMILAR_TO)
        similarity_edges = await self._create_similarity_edges(nodes)
        edges.extend(similarity_edges)

        # 3.3: Reference edges (REFERENCES)
        reference_edges = await self._create_reference_edges(sections)
        edges.extend(reference_edges)

        # 3.4: Sequential edges (FOLLOWS)
        sequential_edges = self._create_sequential_edges(sections)
        edges.extend(sequential_edges)

        construction_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "section_graph_built",
            nodes=len(nodes),
            edges=len(edges),
            hierarchical=len(hierarchical_edges),
            similarity=len(similarity_edges),
            references=len(reference_edges),
            sequential=len(sequential_edges),
            construction_time_ms=round(construction_time_ms, 2),
        )

        return SectionGraph(
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
            construction_time_ms=construction_time_ms,
        )

    async def _fetch_sections(
        self,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch sections from Neo4j.

        Args:
            document_id: Optional document ID filter

        Returns:
            List of section dictionaries
        """
        builder = CypherQueryBuilder()
        builder.match("(s:Section)")

        if document_id:
            builder.match("(d:Document)-[:HAS_SECTION]->(s)")
            builder.where("d.id = $document_id", document_id=document_id)

        builder.return_(
            "elementId(s) AS id",
            "s.heading AS heading",
            "s.text AS content",
            "s.embedding AS embedding",
            "s.level AS level",
            "s.document_id AS doc_id",
            "s.page_no AS page_no",
            "s.sequence AS sequence",
            "s.parent_id AS parent_id",
        )
        builder.order_by("s.document_id", "s.sequence")

        query_dict = builder.build()
        records = await self.neo4j_client.execute_read(
            query_dict["query"],
            query_dict["parameters"],
        )

        return records

    def _create_section_nodes(
        self,
        sections: list[dict[str, Any]],
    ) -> list[SectionNode]:
        """Create SectionNode objects from Neo4j records.

        Args:
            sections: List of section dictionaries

        Returns:
            List of SectionNode objects
        """
        nodes = []
        for section in sections:
            node = SectionNode(
                id=section["id"],
                heading=section.get("heading", ""),
                content=section.get("content", ""),
                embedding=section.get("embedding"),
                level=section.get("level", 1),
                doc_id=section.get("doc_id", ""),
                page_no=section.get("page_no", 0),
                sequence=section.get("sequence", 0),
            )
            nodes.append(node)

        return nodes

    def _create_hierarchical_edges(
        self,
        sections: list[dict[str, Any]],
    ) -> list[SectionEdge]:
        """Create PARENT_OF edges based on heading hierarchy.

        Args:
            sections: List of section dictionaries

        Returns:
            List of hierarchical edges
        """
        edges: list[SectionEdge] = []

        for section in sections:
            parent_id = section.get("parent_id")
            if parent_id:
                edge = SectionEdge(
                    source=parent_id,
                    target=section["id"],
                    edge_type="PARENT_OF",
                    weight=1.0,
                    metadata={"level_diff": 1},
                )
                edges.append(edge)

        return edges

    async def _create_similarity_edges(
        self,
        nodes: list[SectionNode],
    ) -> list[SectionEdge]:
        """Create SIMILAR_TO edges based on semantic similarity.

        Computes cosine similarity between section embeddings and creates
        edges for pairs exceeding the similarity threshold.

        Args:
            nodes: List of section nodes

        Returns:
            List of similarity edges
        """
        edges: list[SectionEdge] = []

        # Filter nodes with embeddings
        nodes_with_embeddings = [n for n in nodes if n.embedding is not None]

        if len(nodes_with_embeddings) < 2:
            logger.debug("insufficient_embeddings_for_similarity")
            return edges

        # Build embedding matrix
        embeddings = np.array([n.embedding for n in nodes_with_embeddings])

        # Compute pairwise cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-8)
        similarity_matrix = np.dot(normalized, normalized.T)

        # Create edges for pairs above threshold
        for i in range(len(nodes_with_embeddings)):
            for j in range(i + 1, len(nodes_with_embeddings)):
                similarity = float(similarity_matrix[i, j])

                if similarity >= self.similarity_threshold:
                    edge = SectionEdge(
                        source=nodes_with_embeddings[i].id,
                        target=nodes_with_embeddings[j].id,
                        edge_type="SIMILAR_TO",
                        weight=similarity,
                        metadata={"cosine_similarity": similarity},
                    )
                    edges.append(edge)

        logger.debug("similarity_edges_created", count=len(edges))
        return edges

    async def _create_reference_edges(
        self,
        sections: list[dict[str, Any]],
    ) -> list[SectionEdge]:
        """Create REFERENCES edges based on citations/links.

        Detects references to other sections in content (e.g., "see Section 3.2").

        Args:
            sections: List of section dictionaries

        Returns:
            List of reference edges
        """
        edges: list[SectionEdge] = []

        # Build heading-to-id map
        heading_map: dict[str, str] = {}
        for section in sections:
            heading_map[section["heading"].lower()] = section["id"]

        # Detect references in content
        for section in sections:
            content = section.get("content", "").lower()

            for heading, target_id in heading_map.items():
                if section["id"] == target_id:
                    continue  # Skip self-references

                # Simple heuristic: check if heading appears in content
                if heading in content and len(heading) > 3:  # Avoid short false matches
                    edge = SectionEdge(
                        source=section["id"],
                        target=target_id,
                        edge_type="REFERENCES",
                        weight=1.0,
                        metadata={"reference_type": "content_mention"},
                    )
                    edges.append(edge)

        logger.debug("reference_edges_created", count=len(edges))
        return edges

    def _create_sequential_edges(
        self,
        sections: list[dict[str, Any]],
    ) -> list[SectionEdge]:
        """Create FOLLOWS edges for sequential sections.

        Args:
            sections: List of section dictionaries (must be ordered by sequence)

        Returns:
            List of sequential edges
        """
        edges: list[SectionEdge] = []

        # Group sections by document
        doc_sections: dict[str, list[dict[str, Any]]] = {}
        for section in sections:
            doc_id = section.get("doc_id", "")
            if doc_id not in doc_sections:
                doc_sections[doc_id] = []
            doc_sections[doc_id].append(section)

        # Create sequential edges within each document
        for doc_id, doc_section_list in doc_sections.items():
            # Sort by sequence (should already be sorted, but ensure)
            sorted_sections = sorted(doc_section_list, key=lambda s: s.get("sequence", 0))

            for i in range(len(sorted_sections) - 1):
                edge = SectionEdge(
                    source=sorted_sections[i]["id"],
                    target=sorted_sections[i + 1]["id"],
                    edge_type="FOLLOWS",
                    weight=1.0,
                    metadata={"document_id": doc_id, "sequence_gap": 1},
                )
                edges.append(edge)

        logger.debug("sequential_edges_created", count=len(edges))
        return edges


# =============================================================================
# COMMUNITY DETECTION
# =============================================================================


class SectionCommunityDetector:
    """Louvain-based community detection for section graphs."""

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        min_community_size: int = DEFAULT_COMMUNITY_MIN_SIZE,
    ) -> None:
        """Initialize section community detector.

        Args:
            neo4j_client: Neo4j client instance (uses singleton if None)
            min_community_size: Minimum community size (filter smaller communities)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.min_community_size = min_community_size
        logger.info(
            "section_community_detector_initialized",
            min_community_size=min_community_size,
        )

    async def detect_communities(
        self,
        section_graph: SectionGraph,
        resolution: float = 1.0,
    ) -> CommunityDetectionResult:
        """Detect communities using Louvain algorithm.

        Args:
            section_graph: Section graph to analyze
            resolution: Resolution parameter (higher = more communities)

        Returns:
            CommunityDetectionResult with detected communities

        Example:
            >>> detector = SectionCommunityDetector()
            >>> result = await detector.detect_communities(graph, resolution=1.2)
            >>> print(f"Found {result.community_count} communities")
        """
        start_time = time.perf_counter()

        logger.info(
            "detecting_communities",
            nodes=section_graph.node_count,
            edges=section_graph.edge_count,
            resolution=resolution,
        )

        # Step 1: Build NetworkX graph
        graph_nx = self._build_networkx_graph(section_graph)

        if graph_nx.number_of_nodes() == 0:
            logger.warning("empty_graph_no_communities")
            return CommunityDetectionResult()

        # Step 2: Run Louvain community detection
        communities_generator = nx.community.louvain_communities(
            graph_nx,
            resolution=resolution,
            seed=42,
        )

        # Step 3: Convert to Community objects
        communities: list[Community] = []
        for idx, community_nodes in enumerate(communities_generator):
            entity_ids = list(community_nodes)
            size = len(entity_ids)

            # Filter by minimum size
            if size < self.min_community_size:
                continue

            # Calculate density
            subgraph = graph_nx.subgraph(entity_ids)
            density = nx.density(subgraph) if size > 1 else 0.0

            # Generate community ID
            community_id = self._generate_community_id(entity_ids)

            community = Community(
                id=community_id,
                label="",  # Will be labeled later if needed
                entity_ids=entity_ids,
                size=size,
                density=density,
                metadata={
                    "algorithm": "louvain",
                    "resolution": resolution,
                    "index": idx,
                },
            )
            communities.append(community)

        # Step 4: Calculate modularity
        # Only calculate if communities cover all nodes (valid partition)
        all_nodes = set(graph_nx.nodes())
        community_nodes = set()
        for community in communities:
            community_nodes.update(community.entity_ids)

        if community_nodes == all_nodes and len(communities) > 0:
            modularity = nx.community.modularity(graph_nx, [set(c.entity_ids) for c in communities])
        else:
            # Invalid partition (not all nodes covered) - skip modularity
            modularity = 0.0

        detection_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "communities_detected",
            community_count=len(communities),
            modularity=round(modularity, 4),
            detection_time_ms=round(detection_time_ms, 2),
        )

        return CommunityDetectionResult(
            communities=communities,
            community_count=len(communities),
            modularity=modularity,
            detection_time_ms=detection_time_ms,
            algorithm="louvain",
        )

    def _build_networkx_graph(self, section_graph: SectionGraph) -> nx.Graph:
        """Build NetworkX graph from section graph.

        Args:
            section_graph: Section graph

        Returns:
            NetworkX graph
        """
        G = nx.Graph()

        # Add nodes
        for node in section_graph.nodes:
            G.add_node(
                node.id,
                heading=node.heading,
                level=node.level,
                doc_id=node.doc_id,
            )

        # Add edges with weights
        for edge in section_graph.edges:
            G.add_edge(
                edge.source,
                edge.target,
                weight=edge.weight,
                edge_type=edge.edge_type,
            )

        logger.debug(
            "networkx_graph_built",
            nodes=G.number_of_nodes(),
            edges=G.number_of_edges(),
        )

        return G

    def _generate_community_id(self, entity_ids: list[str]) -> str:
        """Generate deterministic community ID from entity IDs.

        Args:
            entity_ids: List of entity IDs in community

        Returns:
            Community ID (e.g., "comm_abc123")
        """
        # Sort for determinism
        sorted_ids = sorted(entity_ids)
        # Hash to create stable ID
        hash_input = "|".join(sorted_ids).encode("utf-8")
        hash_digest = hashlib.sha256(hash_input).hexdigest()[:8]
        return f"comm_{hash_digest}"


# =============================================================================
# COMMUNITY STORAGE & RETRIEVAL
# =============================================================================


class SectionCommunityService:
    """Service for storing and retrieving section communities."""

    def __init__(self, neo4j_client: Neo4jClient | None = None) -> None:
        """Initialize section community service.

        Args:
            neo4j_client: Neo4j client instance (uses singleton if None)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.graph_builder = SectionGraphBuilder(neo4j_client=self.neo4j_client)
        self.community_detector = SectionCommunityDetector(neo4j_client=self.neo4j_client)
        logger.info("section_community_service_initialized")

    async def index_communities(
        self,
        document_id: str | None = None,
        resolution: float = 1.0,
    ) -> CommunityDetectionResult:
        """Build section graph, detect communities, and store in Neo4j.

        Args:
            document_id: Optional document ID filter
            resolution: Louvain resolution parameter

        Returns:
            CommunityDetectionResult

        Example:
            >>> service = SectionCommunityService()
            >>> result = await service.index_communities(document_id="doc_123")
        """
        logger.info("indexing_communities", document_id=document_id)

        # Step 1: Build section graph
        graph = await self.graph_builder.build_section_graph(document_id=document_id)

        # Step 2: Detect communities
        detection_result = await self.community_detector.detect_communities(
            graph,
            resolution=resolution,
        )

        # Step 3: Store communities in Neo4j
        await self._store_communities(detection_result.communities)

        logger.info(
            "communities_indexed",
            community_count=detection_result.community_count,
            document_id=document_id,
        )

        return detection_result

    async def retrieve_by_community(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K_COMMUNITIES,
    ) -> CommunityRetrievalResult:
        """Retrieve sections by finding relevant communities.

        Args:
            query: Search query
            top_k: Number of communities to retrieve

        Returns:
            CommunityRetrievalResult with communities and sections

        Example:
            >>> result = await service.retrieve_by_community("authentication", top_k=3)
        """
        start_time = time.perf_counter()

        logger.info("retrieving_by_community", query=query, top_k=top_k)

        # Step 1: Find relevant communities (semantic search on community labels/headings)
        communities = await self._find_relevant_communities(query, top_k)

        # Step 2: Get all sections in these communities
        sections: list[dict[str, Any]] = []
        for community in communities:
            community_sections = await self._get_community_sections(community["id"])
            sections.extend(community_sections)

        retrieval_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "community_retrieval_complete",
            communities_found=len(communities),
            sections_found=len(sections),
            retrieval_time_ms=round(retrieval_time_ms, 2),
        )

        return CommunityRetrievalResult(
            query=query,
            communities=communities,
            sections=sections,
            retrieval_time_ms=retrieval_time_ms,
            total_sections=len(sections),
        )

    async def _store_communities(self, communities: list[Community]) -> None:
        """Store communities and relationships in Neo4j.

        Creates:
        - Community nodes with metadata
        - BELONGS_TO relationships from sections to communities

        Args:
            communities: List of Community objects
        """
        logger.info("storing_communities", count=len(communities))

        for community in communities:
            # Create Community node and BELONGS_TO relationships
            cypher = """
            MERGE (c:Community {id: $community_id})
            SET c.size = $size,
                c.density = $density,
                c.algorithm = $algorithm,
                c.resolution = $resolution,
                c.updated_at = datetime()

            WITH c
            UNWIND $entity_ids AS section_id
            MATCH (s:Section)
            WHERE elementId(s) = section_id
            MERGE (s)-[r:BELONGS_TO]->(c)
            SET r.assigned_at = datetime()
            RETURN count(r) AS relationships_created
            """

            result = await self.neo4j_client.execute_write(
                cypher,
                {
                    "community_id": community.id,
                    "size": community.size,
                    "density": community.density,
                    "algorithm": community.metadata.get("algorithm", "louvain"),
                    "resolution": community.metadata.get("resolution", 1.0),
                    "entity_ids": community.entity_ids,
                },
            )

            relationships_count = result[0].get("relationships_created", 0) if result else 0

            logger.debug(
                "community_stored",
                community_id=community.id,
                relationships=relationships_count,
            )

    async def _find_relevant_communities(
        self,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Find communities relevant to query.

        Uses section headings within communities for matching.

        Args:
            query: Search query
            top_k: Number of communities to return

        Returns:
            List of community dictionaries
        """
        # Query for communities with sections matching query
        cypher = """
        MATCH (c:Community)<-[:BELONGS_TO]-(s:Section)
        WHERE s.heading CONTAINS $query OR s.text CONTAINS $query
        WITH c, count(s) AS matching_sections, collect(s.heading) AS headings
        RETURN
            c.id AS id,
            c.size AS size,
            c.density AS density,
            matching_sections,
            headings
        ORDER BY matching_sections DESC, c.density DESC
        LIMIT $top_k
        """

        records = await self.neo4j_client.execute_read(
            cypher,
            {"query": query.lower(), "top_k": top_k},
        )

        return records

    async def _get_community_sections(self, community_id: str) -> list[dict[str, Any]]:
        """Get all sections in a community.

        Args:
            community_id: Community ID

        Returns:
            List of section dictionaries
        """
        cypher = """
        MATCH (s:Section)-[:BELONGS_TO]->(c:Community {id: $community_id})
        RETURN
            elementId(s) AS id,
            s.heading AS heading,
            s.text AS content,
            s.level AS level,
            s.document_id AS doc_id,
            s.page_no AS page_no
        ORDER BY s.document_id, s.sequence
        """

        records = await self.neo4j_client.execute_read(
            cypher,
            {"community_id": community_id},
        )

        return records


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


# Export public API
__all__ = [
    "SectionNode",
    "SectionEdge",
    "SectionGraph",
    "CommunityDetectionResult",
    "CommunityRetrievalResult",
    "SectionGraphBuilder",
    "SectionCommunityDetector",
    "SectionCommunityService",
    "get_section_community_service",
    "reset_section_community_service",
]
