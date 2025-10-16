"""Graph Analytics Engine.

This module provides graph analytics capabilities including centrality metrics,
PageRank, influential entity detection, and knowledge gap analysis.

Features:
- Multiple centrality metrics (degree, betweenness, closeness, eigenvector)
- PageRank calculation
- Influential entity detection
- Knowledge gap identification
- Uses Neo4j GDS when available, falls back to NetworkX
- Result caching for expensive calculations
"""

import time
from typing import Any, Literal

import networkx as nx
import structlog

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError
from src.core.models import CentralityMetrics, GraphStatistics

logger = structlog.get_logger(__name__)

# Type alias for centrality metrics
CentralityMetric = Literal["degree", "betweenness", "closeness", "eigenvector"]


class GraphAnalyticsEngine:
    """Graph analytics engine with GDS and NetworkX support."""

    def __init__(self, neo4j_client: Neo4jClient | None = None):
        """Initialize the analytics engine.

        Args:
            neo4j_client: Neo4j client instance (defaults to singleton)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.use_gds = settings.graph_analytics_use_gds
        self.pagerank_iterations = settings.graph_analytics_pagerank_iterations
        self.cache_ttl = settings.graph_analytics_cache_ttl_seconds

        # Simple in-memory cache for analytics results
        self._cache: dict[str, tuple[float, Any]] = {}

        logger.info(
            "GraphAnalyticsEngine initialized",
            use_gds=self.use_gds,
            pagerank_iterations=self.pagerank_iterations,
            cache_ttl=self.cache_ttl,
        )

    def _get_cached(self, key: str) -> Any | None:
        """Get cached result if still valid.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug("Cache hit", key=key)
                return value
            else:
                logger.debug("Cache expired", key=key)
                del self._cache[key]
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        """Store value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (time.time(), value)
        logger.debug("Value cached", key=key)

    async def _check_gds_availability(self) -> bool:
        """Check if Neo4j GDS plugin is available.

        Returns:
            True if GDS is available
        """
        try:
            result = await self.neo4j_client.execute_query("CALL gds.version() YIELD version")
            if result:
                logger.info("Neo4j GDS available", version=result[0].get("version"))
                return True
        except Exception as e:
            logger.warning("Neo4j GDS not available, will use NetworkX", error=str(e))
        return False

    async def calculate_centrality(
        self, entity_id: str, metric: CentralityMetric = "degree"
    ) -> CentralityMetrics:
        """Calculate centrality metrics for a specific entity.

        Args:
            entity_id: Entity ID to analyze
            metric: Centrality metric to calculate (degree, betweenness, closeness, eigenvector)

        Returns:
            CentralityMetrics with calculated values

        Raises:
            DatabaseConnectionError: If calculation fails
        """
        cache_key = f"centrality:{entity_id}:{metric}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        logger.info("Calculating centrality", entity_id=entity_id, metric=metric)

        try:
            # Start with degree centrality (always available)
            degree = await self._calculate_degree_centrality(entity_id)

            metrics = CentralityMetrics(
                entity_id=entity_id,
                degree=degree,
                betweenness=0.0,
                closeness=0.0,
                eigenvector=0.0,
                pagerank=0.0,
            )

            # Calculate requested metric
            if metric == "betweenness":
                metrics.betweenness = await self._calculate_betweenness_centrality(entity_id)
            elif metric == "closeness":
                metrics.closeness = await self._calculate_closeness_centrality(entity_id)
            elif metric == "eigenvector":
                metrics.eigenvector = await self._calculate_eigenvector_centrality(entity_id)

            # Also include PageRank
            pagerank_scores = await self.calculate_pagerank([entity_id])
            if pagerank_scores:
                metrics.pagerank = pagerank_scores[0].get("score", 0.0)

            self._set_cached(cache_key, metrics)
            return metrics

        except Exception as e:
            logger.error("Failed to calculate centrality", error=str(e), entity_id=entity_id)
            raise DatabaseConnectionError(f"Centrality calculation failed: {e}") from e

    async def _calculate_degree_centrality(self, entity_id: str) -> float:
        """Calculate degree centrality (number of connections).

        Args:
            entity_id: Entity ID

        Returns:
            Degree (number of connected nodes)
        """
        query = """
        MATCH (n {id: $entity_id})-[r]-(connected)
        RETURN count(DISTINCT connected) AS degree
        """
        result = await self.neo4j_client.execute_query(query, {"entity_id": entity_id})
        return float(result[0].get("degree", 0)) if result else 0.0

    async def _calculate_betweenness_centrality(self, entity_id: str) -> float:
        """Calculate betweenness centrality using GDS or NetworkX.

        Args:
            entity_id: Entity ID

        Returns:
            Normalized betweenness centrality (0-1)
        """
        if self.use_gds and await self._check_gds_availability():
            try:
                # Use Neo4j GDS for betweenness
                query = """
                CALL gds.betweenness.stream('entity-graph')
                YIELD nodeId, score
                WITH gds.util.asNode(nodeId) AS node, score
                WHERE node.id = $entity_id
                RETURN score
                """
                result = await self.neo4j_client.execute_query(query, {"entity_id": entity_id})
                if result:
                    return float(result[0].get("score", 0.0))
            except Exception as e:
                logger.warning("GDS betweenness failed, using NetworkX", error=str(e))

        # Fallback to NetworkX
        G = await self._build_networkx_graph()
        betweenness = nx.betweenness_centrality(G)
        return betweenness.get(entity_id, 0.0)

    async def _calculate_closeness_centrality(self, entity_id: str) -> float:
        """Calculate closeness centrality using NetworkX.

        Args:
            entity_id: Entity ID

        Returns:
            Normalized closeness centrality (0-1)
        """
        G = await self._build_networkx_graph()
        closeness = nx.closeness_centrality(G)
        return closeness.get(entity_id, 0.0)

    async def _calculate_eigenvector_centrality(self, entity_id: str) -> float:
        """Calculate eigenvector centrality using NetworkX.

        Args:
            entity_id: Entity ID

        Returns:
            Eigenvector centrality (0-1)
        """
        G = await self._build_networkx_graph()
        try:
            eigenvector = nx.eigenvector_centrality(G, max_iter=100)
            return eigenvector.get(entity_id, 0.0)
        except nx.PowerIterationFailedConvergence:
            logger.warning("Eigenvector centrality failed to converge", entity_id=entity_id)
            return 0.0

    async def calculate_pagerank(
        self, entity_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Calculate PageRank scores for entities.

        Args:
            entity_ids: Specific entity IDs to calculate (None = all entities)

        Returns:
            List of {"entity_id": str, "score": float} dictionaries

        Raises:
            DatabaseConnectionError: If calculation fails
        """
        cache_key = f"pagerank:{','.join(entity_ids) if entity_ids else 'all'}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        logger.info("Calculating PageRank", entity_count=len(entity_ids) if entity_ids else "all")

        try:
            if self.use_gds and await self._check_gds_availability():
                # Use Neo4j GDS for PageRank
                query = """
                CALL gds.pageRank.stream('entity-graph', {maxIterations: $iterations})
                YIELD nodeId, score
                WITH gds.util.asNode(nodeId) AS node, score
                """
                if entity_ids:
                    query += "WHERE node.id IN $entity_ids\n"
                query += "RETURN node.id AS entity_id, score ORDER BY score DESC"

                result = await self.neo4j_client.execute_query(
                    query, {"iterations": self.pagerank_iterations, "entity_ids": entity_ids}
                )
            else:
                # Fallback to NetworkX
                G = await self._build_networkx_graph()
                pagerank = nx.pagerank(G, max_iter=self.pagerank_iterations)

                if entity_ids:
                    result = [
                        {"entity_id": eid, "score": pagerank.get(eid, 0.0)} for eid in entity_ids
                    ]
                else:
                    result = [
                        {"entity_id": eid, "score": score}
                        for eid, score in sorted(
                            pagerank.items(), key=lambda x: x[1], reverse=True
                        )
                    ]

            self._set_cached(cache_key, result)
            return result

        except Exception as e:
            logger.error("Failed to calculate PageRank", error=str(e))
            raise DatabaseConnectionError(f"PageRank calculation failed: {e}") from e

    async def find_influential_entities(self, top_k: int = 10) -> list[dict[str, Any]]:
        """Find the most influential entities by PageRank.

        Args:
            top_k: Number of top entities to return

        Returns:
            List of entities with PageRank scores

        Raises:
            DatabaseConnectionError: If calculation fails
        """
        logger.info("Finding influential entities", top_k=top_k)

        pagerank_scores = await self.calculate_pagerank()
        top_entities = pagerank_scores[:top_k]

        logger.info("Found influential entities", count=len(top_entities))
        return top_entities

    async def detect_knowledge_gaps(self) -> dict[str, Any]:
        """Detect knowledge gaps in the graph (orphans, sparse areas).

        Returns:
            Dictionary with gap analysis:
            {
                "orphan_entities": [...],  # Nodes with no connections
                "sparse_entities": [...],  # Nodes with only 1-2 connections
                "isolated_components": int,  # Number of disconnected subgraphs
            }

        Raises:
            DatabaseConnectionError: If analysis fails
        """
        cache_key = "knowledge_gaps"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        logger.info("Detecting knowledge gaps")

        try:
            # Find orphan entities (degree = 0)
            orphan_query = """
            MATCH (n)
            WHERE NOT (n)--()
            RETURN n.id AS entity_id, n.name AS name
            LIMIT 100
            """
            orphans = await self.neo4j_client.execute_query(orphan_query)

            # Find sparse entities (degree 1-2)
            sparse_query = """
            MATCH (n)-[r]-(connected)
            WITH n, count(DISTINCT connected) AS degree
            WHERE degree <= 2
            RETURN n.id AS entity_id, n.name AS name, degree
            ORDER BY degree ASC
            LIMIT 100
            """
            sparse = await self.neo4j_client.execute_query(sparse_query)

            # Count connected components using NetworkX
            G = await self._build_networkx_graph()
            num_components = nx.number_connected_components(G.to_undirected())

            result = {
                "orphan_entities": orphans,
                "sparse_entities": sparse,
                "isolated_components": num_components,
            }

            self._set_cached(cache_key, result)

            logger.info(
                "Knowledge gaps detected",
                orphans=len(orphans),
                sparse=len(sparse),
                components=num_components,
            )

            return result

        except Exception as e:
            logger.error("Failed to detect knowledge gaps", error=str(e))
            raise DatabaseConnectionError(f"Knowledge gap detection failed: {e}") from e

    async def get_graph_statistics(self) -> GraphStatistics:
        """Get overall graph statistics and metrics.

        Returns:
            GraphStatistics with graph-level metrics

        Raises:
            DatabaseConnectionError: If query fails
        """
        cache_key = "graph_statistics"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        logger.info("Calculating graph statistics")

        try:
            # Count entities and relationships
            count_query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-()
            WITH count(DISTINCT n) AS entities, count(DISTINCT r) AS relationships
            RETURN entities, relationships
            """
            counts = await self.neo4j_client.execute_query(count_query)
            total_entities = counts[0].get("entities", 0) if counts else 0
            total_relationships = counts[0].get("relationships", 0) if counts else 0

            # Entity types distribution
            entity_types_query = """
            MATCH (n)
            RETURN labels(n)[0] AS type, count(*) AS count
            ORDER BY count DESC
            """
            entity_types_result = await self.neo4j_client.execute_query(entity_types_query)
            entity_types = {row["type"]: row["count"] for row in entity_types_result}

            # Relationship types distribution
            rel_types_query = """
            MATCH ()-[r]->()
            RETURN type(r) AS type, count(*) AS count
            ORDER BY count DESC
            """
            rel_types_result = await self.neo4j_client.execute_query(rel_types_query)
            relationship_types = {row["type"]: row["count"] for row in rel_types_result}

            # Calculate average degree and density
            avg_degree = (
                (2.0 * total_relationships / total_entities) if total_entities > 0 else 0.0
            )
            max_edges = total_entities * (total_entities - 1) / 2
            density = total_relationships / max_edges if max_edges > 0 else 0.0

            # Count communities (if available)
            try:
                community_query = "MATCH (n) RETURN count(DISTINCT n.community_id) AS communities"
                community_result = await self.neo4j_client.execute_query(community_query)
                communities = community_result[0].get("communities", 0) if community_result else 0
            except Exception:
                communities = 0

            stats = GraphStatistics(
                total_entities=total_entities,
                total_relationships=total_relationships,
                entity_types=entity_types,
                relationship_types=relationship_types,
                avg_degree=avg_degree,
                density=density,
                communities=communities,
            )

            self._set_cached(cache_key, stats)

            logger.info(
                "Graph statistics calculated",
                entities=total_entities,
                relationships=total_relationships,
                avg_degree=avg_degree,
            )

            return stats

        except Exception as e:
            logger.error("Failed to calculate graph statistics", error=str(e))
            raise DatabaseConnectionError(f"Graph statistics calculation failed: {e}") from e

    async def _build_networkx_graph(self) -> nx.DiGraph:
        """Build a NetworkX graph from Neo4j data for fallback algorithms.

        Returns:
            NetworkX DiGraph

        Raises:
            DatabaseConnectionError: If graph construction fails
        """
        cache_key = "networkx_graph"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        logger.info("Building NetworkX graph from Neo4j")

        try:
            # Fetch all nodes and relationships
            query = """
            MATCH (n)-[r]->(m)
            RETURN n.id AS source, m.id AS target, type(r) AS rel_type
            """
            result = await self.neo4j_client.execute_query(query)

            # Build NetworkX graph
            G = nx.DiGraph()
            for row in result:
                G.add_edge(row["source"], row["target"], type=row["rel_type"])

            logger.info(
                "NetworkX graph built", nodes=G.number_of_nodes(), edges=G.number_of_edges()
            )

            # Cache for shorter duration (graph changes frequently)
            self._set_cached(cache_key, G)

            return G

        except Exception as e:
            logger.error("Failed to build NetworkX graph", error=str(e))
            raise DatabaseConnectionError(f"NetworkX graph construction failed: {e}") from e


# Singleton instance
_analytics_engine: GraphAnalyticsEngine | None = None


def get_analytics_engine() -> GraphAnalyticsEngine:
    """Get singleton GraphAnalyticsEngine instance.

    Returns:
        GraphAnalyticsEngine instance
    """
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = GraphAnalyticsEngine()
    return _analytics_engine
