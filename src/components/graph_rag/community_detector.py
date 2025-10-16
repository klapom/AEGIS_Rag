"""Community Detection for Knowledge Graphs.

This module provides community detection capabilities using both Neo4j GDS
(Graph Data Science) plugin and NetworkX as a fallback. Communities are
clusters of densely connected entities that share common characteristics.

Sprint 6.3: Feature - Community Detection & Clustering

Supports:
- Leiden algorithm (primary)
- Louvain algorithm (alternative)
- Auto-detection of GDS availability
- NetworkX fallback for environments without GDS
- Community storage in Neo4j (community_id property)
"""

import time
import uuid
from datetime import datetime

import networkx as nx
import structlog
from neo4j.exceptions import ClientError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError
from src.core.models import Community

logger = structlog.get_logger(__name__)


class CommunityDetector:
    """Community detection using Neo4j GDS or NetworkX fallback.

    Provides community detection algorithms to identify clusters of
    densely connected entities in the knowledge graph.

    Features:
    - Leiden and Louvain algorithms
    - Auto-detection of Neo4j GDS availability
    - NetworkX fallback when GDS unavailable
    - Community storage on entity nodes
    - Community retrieval and statistics
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        algorithm: str | None = None,
        resolution: float | None = None,
        min_size: int | None = None,
        use_gds: bool | None = None,
    ):
        """Initialize community detector.

        Args:
            neo4j_client: Neo4j client instance (default: global singleton)
            algorithm: Detection algorithm ('leiden' or 'louvain')
            resolution: Resolution parameter for detection (higher = more communities)
            min_size: Minimum community size to include
            use_gds: Try Neo4j GDS first (default: True)
        """
        self.neo4j_client = neo4j_client or Neo4jClient()
        self.algorithm = algorithm or settings.graph_community_algorithm
        self.resolution = resolution or settings.graph_community_resolution
        self.min_size = min_size or settings.graph_community_min_size
        self.use_gds = use_gds if use_gds is not None else settings.graph_community_use_gds

        # Cache for GDS availability check
        self._gds_available: bool | None = None

        logger.info(
            "community_detector_initialized",
            algorithm=self.algorithm,
            resolution=self.resolution,
            min_size=self.min_size,
            use_gds=self.use_gds,
        )

    async def _check_gds_availability(self) -> bool:
        """Check if Neo4j GDS plugin is available.

        Returns:
            True if GDS plugin is installed and accessible
        """
        if self._gds_available is not None:
            return self._gds_available

        try:
            # Try to call GDS version procedure
            result = await self.neo4j_client.execute_read("CALL gds.version()")
            if result:
                version = result[0].get("gdsVersion", "unknown")
                logger.info("neo4j_gds_available", version=version)
                self._gds_available = True
                return True
        except (ClientError, DatabaseConnectionError) as e:
            logger.info("neo4j_gds_not_available", reason=str(e)[:100])

        self._gds_available = False
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def detect_communities(
        self,
        algorithm: str | None = None,
        resolution: float | None = None,
    ) -> list[Community]:
        """Run community detection on the knowledge graph.

        Args:
            algorithm: Detection algorithm ('leiden' or 'louvain')
            resolution: Resolution parameter (default: from settings)

        Returns:
            List of detected Community objects

        Raises:
            DatabaseConnectionError: If detection fails
        """
        start_time = time.time()
        algo = algorithm or self.algorithm
        res = resolution or self.resolution

        logger.info("community_detection_started", algorithm=algo, resolution=res)

        try:
            # Check if GDS is available
            gds_available = await self._check_gds_availability() if self.use_gds else False

            if gds_available:
                communities = await self._detect_with_gds(algo, res)
            else:
                logger.info("using_networkx_fallback", reason="GDS not available")
                communities = await self._detect_with_networkx(algo, res)

            # Store community IDs on entity nodes
            await self._store_communities(communities)

            # Filter by minimum size
            communities = [c for c in communities if c.size >= self.min_size]

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                "community_detection_completed",
                algorithm=algo,
                communities_found=len(communities),
                execution_time_ms=execution_time,
            )

            return communities

        except Exception as e:
            logger.error("community_detection_failed", algorithm=algo, error=str(e))
            raise

    async def _detect_with_gds(self, algorithm: str, resolution: float) -> list[Community]:
        """Run community detection using Neo4j GDS.

        Args:
            algorithm: 'leiden' or 'louvain'
            resolution: Resolution parameter

        Returns:
            List of Community objects
        """
        logger.info("running_gds_community_detection", algorithm=algorithm)

        try:
            # Create in-memory graph projection
            projection_name = f"community_graph_{uuid.uuid4().hex[:8]}"

            # Project graph
            await self.neo4j_client.execute_query(
                """
                CALL gds.graph.project(
                    $projectionName,
                    'Entity',
                    {
                        RELATED_TO: {
                            orientation: 'UNDIRECTED'
                        }
                    }
                )
                """,
                {"projectionName": projection_name},
            )

            # Run community detection based on algorithm
            if algorithm.lower() == "leiden":
                cypher = """
                CALL gds.leiden.stream($projectionName, {
                    relationshipWeightProperty: null,
                    includeIntermediateCommunities: false,
                    gamma: $resolution
                })
                YIELD nodeId, communityId
                RETURN gds.util.asNode(nodeId).id AS entity_id, communityId
                """
            else:  # louvain
                cypher = """
                CALL gds.louvain.stream($projectionName, {
                    relationshipWeightProperty: null,
                    includeIntermediateCommunities: false
                })
                YIELD nodeId, communityId
                RETURN gds.util.asNode(nodeId).id AS entity_id, communityId
                """

            results = await self.neo4j_client.execute_read(
                cypher,
                {"projectionName": projection_name, "resolution": resolution},
            )

            # Group entities by community
            communities_dict: dict[int, list[str]] = {}
            for record in results:
                community_id = record["communityId"]
                entity_id = record["entity_id"]
                if community_id not in communities_dict:
                    communities_dict[community_id] = []
                communities_dict[community_id].append(entity_id)

            # Create Community objects
            communities = []
            for comm_id, entity_ids in communities_dict.items():
                community = Community(
                    id=f"community_{comm_id}",
                    label="",  # Will be filled by labeler
                    entity_ids=entity_ids,
                    size=len(entity_ids),
                    density=0.0,  # Calculate separately if needed
                    created_at=datetime.utcnow(),
                    metadata={
                        "algorithm": algorithm,
                        "resolution": resolution,
                        "method": "neo4j_gds",
                    },
                )
                communities.append(community)

            # Drop the projection
            await self.neo4j_client.execute_query(
                "CALL gds.graph.drop($projectionName)",
                {"projectionName": projection_name},
            )

            return communities

        except Exception as e:
            logger.error("gds_community_detection_failed", error=str(e))
            # Fallback to NetworkX
            return await self._detect_with_networkx(algorithm, resolution)

    async def _detect_with_networkx(self, algorithm: str, resolution: float) -> list[Community]:
        """Run community detection using NetworkX.

        Args:
            algorithm: 'leiden' or 'louvain'
            resolution: Resolution parameter

        Returns:
            List of Community objects
        """
        logger.info("running_networkx_community_detection", algorithm=algorithm)

        try:
            # Fetch all entities and relationships
            entities_query = "MATCH (e:Entity) RETURN e.id AS id"
            entities = await self.neo4j_client.execute_read(entities_query)

            relationships_query = """
            MATCH (e1:Entity)-[r:RELATED_TO]-(e2:Entity)
            RETURN DISTINCT e1.id AS source, e2.id AS target
            """
            relationships = await self.neo4j_client.execute_read(relationships_query)

            # Build NetworkX graph
            graph = nx.Graph()

            for entity in entities:
                graph.add_node(entity["id"])

            for rel in relationships:
                graph.add_edge(rel["source"], rel["target"])

            logger.info("networkx_graph_built", nodes=graph.number_of_nodes(), edges=graph.number_of_edges())

            # Run community detection
            if algorithm.lower() == "leiden":
                # NetworkX doesn't have Leiden, use Louvain instead
                logger.warning("leiden_not_available_in_networkx", using="louvain")
                communities_generator = nx.community.louvain_communities(
                    graph, resolution=resolution, seed=42
                )
            else:  # louvain
                communities_generator = nx.community.louvain_communities(
                    graph, resolution=resolution, seed=42
                )

            # Convert to Community objects
            communities = []
            for idx, community_nodes in enumerate(communities_generator):
                entity_ids = list(community_nodes)
                community = Community(
                    id=f"community_{idx}",
                    label="",  # Will be filled by labeler
                    entity_ids=entity_ids,
                    size=len(entity_ids),
                    density=self._calculate_density(G, entity_ids),
                    created_at=datetime.utcnow(),
                    metadata={
                        "algorithm": "louvain",  # NetworkX uses Louvain
                        "resolution": resolution,
                        "method": "networkx",
                    },
                )
                communities.append(community)

            return communities

        except Exception as e:
            logger.error("networkx_community_detection_failed", error=str(e))
            raise

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

    async def _store_communities(self, communities: list[Community]) -> None:
        """Store community IDs on entity nodes in Neo4j.

        Args:
            communities: List of Community objects
        """
        logger.info("storing_communities", count=len(communities))

        try:
            for community in communities:
                # Update all entities in this community
                cypher = """
                UNWIND $entity_ids AS entity_id
                MATCH (e:Entity {id: entity_id})
                SET e.community_id = $community_id
                RETURN count(e) AS updated_count
                """

                result = await self.neo4j_client.execute_write(
                    cypher,
                    {
                        "entity_ids": community.entity_ids,
                        "community_id": community.id,
                    },
                )

                logger.debug(
                    "community_stored",
                    community_id=community.id,
                    entities_updated=result[0].get("updated_count", 0),
                )

        except Exception as e:
            logger.error("store_communities_failed", error=str(e))
            raise

    async def get_community(self, community_id: str) -> Community | None:
        """Get community details by ID.

        Args:
            community_id: Community ID

        Returns:
            Community object or None if not found
        """
        try:
            cypher = """
            MATCH (e:Entity {community_id: $community_id})
            RETURN e.id AS entity_id, e.community_label AS label
            """

            results = await self.neo4j_client.execute_read(
                cypher,
                {"community_id": community_id},
            )

            if not results:
                return None

            entity_ids = [r["entity_id"] for r in results]
            label = results[0].get("label", "")

            return Community(
                id=community_id,
                label=label,
                entity_ids=entity_ids,
                size=len(entity_ids),
                density=0.0,
                created_at=datetime.utcnow(),
                metadata={},
            )

        except Exception as e:
            logger.error("get_community_failed", community_id=community_id, error=str(e))
            return None

    async def get_entity_community(self, entity_id: str) -> str | None:
        """Get the community ID for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Community ID or None if not assigned
        """
        try:
            cypher = "MATCH (e:Entity {id: $entity_id}) RETURN e.community_id AS community_id"
            result = await self.neo4j_client.execute_read(cypher, {"entity_id": entity_id})

            if result and result[0].get("community_id"):
                return result[0]["community_id"]

            return None

        except Exception as e:
            logger.error("get_entity_community_failed", entity_id=entity_id, error=str(e))
            return None

    async def list_communities(self, min_size: int | None = None) -> list[Community]:
        """List all communities in the graph.

        Args:
            min_size: Minimum community size (default: from settings)

        Returns:
            List of Community objects
        """
        min_size = min_size or self.min_size

        try:
            cypher = """
            MATCH (e:Entity)
            WHERE e.community_id IS NOT NULL
            WITH e.community_id AS community_id,
                 e.community_label AS label,
                 collect(e.id) AS entity_ids
            WHERE size(entity_ids) >= $min_size
            RETURN community_id, label, entity_ids, size(entity_ids) AS size
            """

            results = await self.neo4j_client.execute_read(cypher, {"min_size": min_size})

            communities = []
            for record in results:
                community = Community(
                    id=record["community_id"],
                    label=record.get("label", ""),
                    entity_ids=record["entity_ids"],
                    size=record["size"],
                    density=0.0,
                    created_at=datetime.utcnow(),
                    metadata={},
                )
                communities.append(community)

            logger.info("list_communities", count=len(communities), min_size=min_size)
            return communities

        except Exception as e:
            logger.error("list_communities_failed", error=str(e))
            return []


# Singleton instance
_community_detector: CommunityDetector | None = None


def get_community_detector() -> CommunityDetector:
    """Get global CommunityDetector instance (singleton).

    Returns:
        CommunityDetector instance
    """
    global _community_detector
    if _community_detector is None:
        _community_detector = CommunityDetector()
    return _community_detector
