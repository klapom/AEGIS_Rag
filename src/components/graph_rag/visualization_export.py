"""Graph Visualization Export Module.

This module provides functionality to export subgraphs in various formats
for frontend visualization libraries (D3.js, Cytoscape.js, vis.js).

Features:
- Subgraph extraction from Neo4j
- Multiple output formats (D3, Cytoscape, vis.js)
- Node/edge limit enforcement
- Depth-based traversal
"""

from typing import Any, Literal

import structlog

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError

logger = structlog.get_logger(__name__)

# Type alias for visualization formats
VisualizationFormat = Literal["d3", "cytoscape", "visjs"]


class GraphVisualizationExporter:
    """Export graph data for frontend visualization."""

    def __init__(self, neo4j_client: Neo4jClient | None = None) -> None:
        """Initialize the exporter.

        Args:
            neo4j_client: Neo4j client instance (defaults to singleton)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.max_nodes = settings.graph_visualization_max_nodes
        self.default_depth = settings.graph_visualization_default_depth
        self.default_format = settings.graph_visualization_default_format

        logger.info(
            "GraphVisualizationExporter initialized",
            max_nodes=self.max_nodes,
            default_depth=self.default_depth,
            default_format=self.default_format,
        )

    async def export_subgraph(
        self,
        entity_ids: list[str],
        depth: int = 1,
        max_nodes: int | None = None,
        format: VisualizationFormat = "d3",
    ) -> dict[str, Any]:
        """Export a subgraph starting from given entity IDs.

        Args:
            entity_ids: list of entity IDs to start from
            depth: Traversal depth (1-5)
            max_nodes: Maximum nodes to return (defaults to config)
            format: Output format (d3, cytoscape, visjs)

        Returns:
            Dictionary with nodes, edges/links, and metadata

        Raises:
            DatabaseConnectionError: If Neo4j query fails
        """
        depth = max(1, min(depth, 5))  # Clamp to 1-5
        max_nodes = max_nodes or self.max_nodes

        logger.info(
            "Exporting subgraph",
            entity_ids=entity_ids,
            depth=depth,
            max_nodes=max_nodes,
            format=format,
        )

        # Fetch subgraph from Neo4j
        nodes, edges = await self._fetch_subgraph(entity_ids, depth, max_nodes)

        # Convert to requested format
        if format == "d3":
            result = self.export_for_d3js(nodes, edges)
        elif format == "cytoscape":
            result = self.export_for_cytoscape(nodes, edges)
        elif format == "visjs":
            result = self.export_for_visjs(nodes, edges)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Add metadata
        result["metadata"] = {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "truncated": len(nodes) >= max_nodes,
            "depth": depth,
            "format": format,
        }

        logger.info(
            "Subgraph exported",
            node_count=len(nodes),
            edge_count=len(edges),
            truncated=result["metadata"]["truncated"],
        )

        return result

    async def _fetch_subgraph(
        self, entity_ids: list[str], depth: int, max_nodes: int
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch subgraph from Neo4j using variable-length path traversal.

        Args:
            entity_ids: Starting entity IDs
            depth: Traversal depth
            max_nodes: Maximum nodes to return

        Returns:
            Tuple of (nodes, edges)

        Raises:
            DatabaseConnectionError: If query fails
        """
        # Cypher query with variable-length path pattern
        query = f"""
        MATCH (start)
        WHERE start.id IN $entity_ids
        CALL {{
            WITH start
            MATCH path = (start)-[*1..{depth}]-(connected)
            RETURN collect(nodes(path)) AS node_paths, collect(relationships(path)) AS rel_paths
        }}
        WITH node_paths, rel_paths
        UNWIND node_paths AS node_list
        UNWIND node_list AS node
        WITH DISTINCT node, rel_paths
        LIMIT $max_nodes
        WITH collect(DISTINCT {{
            id: node.id,
            name: COALESCE(node.name, node.id),
            type: COALESCE(labels(node)[0], 'Unknown'),
            description: COALESCE(node.description, ''),
            properties: properties(node)
        }}) AS nodes, rel_paths
        UNWIND rel_paths AS rel_list
        UNWIND rel_list AS rel
        RETURN nodes,
               collect(DISTINCT {{
                   id: id(rel),
                   source: startNode(rel).id,
                   target: endNode(rel).id,
                   type: type(rel),
                   properties: properties(rel)
               }}) AS edges
        """

        try:
            result = await self.neo4j_client.execute_query(
                query, parameters={"entity_ids": entity_ids, "max_nodes": max_nodes}
            )

            if not result:
                logger.warning("No subgraph data found", entity_ids=entity_ids)
                return [], []

            # Extract nodes and edges from result
            nodes = result[0].get("nodes", [])
            edges = result[0].get("edges", [])

            return nodes, edges

        except Exception as e:
            logger.error("Failed to fetch subgraph", error=str(e), entity_ids=entity_ids)
            raise DatabaseConnectionError("Neo4j", f"Failed to fetch subgraph: {e}") from e

    def export_for_d3js(
        self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Export graph data in D3.js force-directed graph format.

        D3.js format:
        {
          "nodes": [{"id": "1", "label": "Entity", "type": "Person", "group": 1}],
          "links": [{"source": "1", "target": "2", "type": "KNOWS", "value": 1}]
        }

        Args:
            nodes: list of node dictionaries
            edges: list of edge dictionaries

        Returns:
            D3.js formatted graph data
        """
        # Map entity types to numeric groups for coloring
        type_groups = {}
        next_group = 1

        d3_nodes = []
        for node in nodes:
            entity_type = node.get("type", "Unknown")
            if entity_type not in type_groups:
                type_groups[entity_type] = next_group
                next_group += 1

            d3_nodes.append(
                {
                    "id": node["id"],
                    "label": node["name"],
                    "type": entity_type,
                    "group": type_groups[entity_type],
                    "description": node.get("description", ""),
                    "properties": node.get("properties", {}),
                }
            )

        d3_links = []
        for edge in edges:
            d3_links.append(
                {
                    "source": edge["source"],
                    "target": edge["target"],
                    "type": edge["type"],
                    "value": 1,  # Weight for link strength
                    "properties": edge.get("properties", {}),
                }
            )

        return {"nodes": d3_nodes, "links": d3_links}

    def export_for_cytoscape(
        self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Export graph data in Cytoscape.js format.

        Cytoscape.js format:
        {
          "elements": {
            "nodes": [{"data": {"id": "1", "label": "Entity", "type": "Person"}}],
            "edges": [{"data": {"id": "e1", "source": "1", "target": "2", "label": "KNOWS"}}]
          }
        }

        Args:
            nodes: list of node dictionaries
            edges: list of edge dictionaries

        Returns:
            Cytoscape.js formatted graph data
        """
        cyto_nodes = []
        for node in nodes:
            cyto_nodes.append(
                {
                    "data": {
                        "id": node["id"],
                        "label": node["name"],
                        "type": node.get("type", "Unknown"),
                        "description": node.get("description", ""),
                        **node.get("properties", {}),
                    }
                }
            )

        cyto_edges = []
        for edge in edges:
            cyto_edges.append(
                {
                    "data": {
                        "id": f"edge_{edge['id']}",
                        "source": edge["source"],
                        "target": edge["target"],
                        "label": edge["type"],
                        **edge.get("properties", {}),
                    }
                }
            )

        return {"elements": {"nodes": cyto_nodes, "edges": cyto_edges}}

    def export_for_visjs(
        self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Export graph data in vis.js network format.

        vis.js format:
        {
          "nodes": [{"id": "1", "label": "Entity", "title": "Description", "group": "Person"}],
          "edges": [{"from": "1", "to": "2", "label": "KNOWS", "title": "Relationship"}]
        }

        Args:
            nodes: list of node dictionaries
            edges: list of edge dictionaries

        Returns:
            vis.js formatted graph data
        """
        vis_nodes = []
        for node in nodes:
            vis_nodes.append(
                {
                    "id": node["id"],
                    "label": node["name"],
                    "title": node.get("description", node["name"]),  # Hover tooltip
                    "group": node.get("type", "Unknown"),
                    "properties": node.get("properties", {}),
                }
            )

        vis_edges = []
        for edge in edges:
            vis_edges.append(
                {
                    "id": edge["id"],
                    "from": edge["source"],
                    "to": edge["target"],
                    "label": edge["type"],
                    "title": edge["type"],  # Hover tooltip
                    "properties": edge.get("properties", {}),
                }
            )

        return {"nodes": vis_nodes, "edges": vis_edges}


# Singleton instance
_visualization_exporter: GraphVisualizationExporter | None = None


def get_visualization_exporter() -> GraphVisualizationExporter:
    """Get singleton GraphVisualizationExporter instance.

    Returns:
        GraphVisualizationExporter instance
    """
    global _visualization_exporter
    if _visualization_exporter is None:
        _visualization_exporter = GraphVisualizationExporter()
    return _visualization_exporter
