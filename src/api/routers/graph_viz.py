"""Graph Visualization API Router.

Sprint 12 Feature 12.8: Enhanced graph visualization endpoints.
Provides export, filtering, and community highlighting capabilities.
"""

from typing import Any, Literal

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.components.graph_rag.neo4j_client import get_neo4j_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/graph/viz", tags=["graph-visualization"])


# ============================================================================
# Request/Response Models
# ============================================================================


class GraphExportRequest(BaseModel):
    """Request model for graph export."""

    format: Literal["json", "graphml", "cytoscape"] = Field(
        default="json",
        description="Export format (json/graphml/cytoscape)",
    )
    entity_types: list[str] | None = Field(
        default=None,
        description="Filter by entity types (None = all)",
    )
    max_nodes: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum nodes to export",
    )
    include_communities: bool = Field(
        default=True,
        description="Include community detection results",
    )


class GraphFilterRequest(BaseModel):
    """Request model for graph filtering."""

    entity_types: list[str] = Field(
        description="Entity types to include",
    )
    min_degree: int | None = Field(
        default=None,
        ge=0,
        description="Minimum node degree (connections)",
    )
    community_id: str | None = Field(
        default=None,
        description="Filter by community ID",
    )


class CommunityHighlightRequest(BaseModel):
    """Request model for community highlighting."""

    community_ids: list[str] = Field(
        description="Community IDs to highlight",
    )
    include_neighbors: bool = Field(
        default=False,
        description="Include neighbor nodes",
    )


# ============================================================================
# Export Endpoints
# ============================================================================


@router.post("/export")
async def export_graph(request: GraphExportRequest) -> dict[str, Any]:
    """Export graph in specified format.

    Sprint 12: Supports JSON, GraphML, and Cytoscape formats.

    Args:
        request: Export configuration

    Returns:
        Exported graph data in requested format
    """
    try:
        neo4j = get_neo4j_client()

        # Build filter query
        type_filter = ""
        if request.entity_types:
            type_filter = f"WHERE n.entity_type IN {request.entity_types}"

        # Query nodes and relationships
        query = f"""
        MATCH (n:Entity)
        {type_filter}
        WITH n
        LIMIT {request.max_nodes}
        OPTIONAL MATCH (n)-[r]->(m:Entity)
        RETURN n, r, m
        """

        async with neo4j.get_driver().session() as session:
            result = await session.run(query)
            records = await result.data()

        # Format based on export type
        if request.format == "json":
            return _export_json(records, request.include_communities)
        elif request.format == "graphml":
            return _export_graphml(records)
        elif request.format == "cytoscape":
            return _export_cytoscape(records)

    except Exception as e:
        logger.error("graph_export_failed", error=str(e), format=request.format)
        raise HTTPException(status_code=500, detail=f"Export failed: {e}") from e


@router.get("/export/formats")
async def get_export_formats() -> dict[str, list[str]]:
    """Get supported export formats.

    Returns:
        List of supported formats with descriptions
    """
    return {
        "formats": [
            {"name": "json", "description": "JSON graph format (default)"},
            {"name": "graphml", "description": "GraphML XML format"},
            {"name": "cytoscape", "description": "Cytoscape.js format"},
        ]
    }


# ============================================================================
# Filter Endpoints
# ============================================================================


@router.post("/filter")
async def filter_graph(request: GraphFilterRequest) -> dict[str, Any]:
    """Filter graph by entity types and properties.

    Sprint 12: Advanced filtering with degree and community support.

    Args:
        request: Filter configuration

    Returns:
        Filtered subgraph
    """
    try:
        neo4j = get_neo4j_client()

        # Build query with filters
        filters = [f"n.entity_type IN {request.entity_types}"]

        if request.min_degree is not None:
            filters.append(f"size((n)--()) >= {request.min_degree}")

        if request.community_id:
            filters.append(f"n.community_id = '{request.community_id}'")

        where_clause = " AND ".join(filters)

        query = f"""
        MATCH (n:Entity)
        WHERE {where_clause}
        WITH n
        LIMIT 100
        OPTIONAL MATCH (n)-[r]->(m:Entity)
        RETURN n, r, m
        """

        async with neo4j.get_driver().session() as session:
            result = await session.run(query)
            records = await result.data()

        return _export_json(records, include_communities=True)

    except Exception as e:
        logger.error("graph_filter_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Filter failed: {e}") from e


# ============================================================================
# Community Endpoints
# ============================================================================


@router.post("/communities/highlight")
async def highlight_communities(
    request: CommunityHighlightRequest,
) -> dict[str, Any]:
    """Highlight specific communities in graph.

    Sprint 12: Community-based subgraph extraction.

    Args:
        request: Community highlight configuration

    Returns:
        Subgraph with highlighted communities
    """
    try:
        neo4j = get_neo4j_client()

        # Query nodes in specified communities
        query = f"""
        MATCH (n:Entity)
        WHERE n.community_id IN {request.community_ids}
        """

        if request.include_neighbors:
            query += """
            OPTIONAL MATCH (n)-[r]-(neighbor:Entity)
            RETURN n, r, neighbor
            """
        else:
            query += """
            WITH n
            OPTIONAL MATCH (n)-[r]->(m:Entity)
            WHERE m.community_id IN {request.community_ids}
            RETURN n, r, m
            """

        async with neo4j.get_driver().session() as session:
            result = await session.run(query, community_ids=request.community_ids)
            records = await result.data()

        return {
            "communities": request.community_ids,
            "include_neighbors": request.include_neighbors,
            "graph": _export_json(records, include_communities=True),
        }

    except Exception as e:
        logger.error("community_highlight_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Highlight failed: {e}") from e


# ============================================================================
# Helper Functions
# ============================================================================


def _export_json(records: list[dict], include_communities: bool = True) -> dict[str, Any]:
    """Export graph as JSON format."""
    nodes = {}
    edges = []

    for record in records:
        # Add node
        if "n" in record and record["n"]:
            node = record["n"]
            node_id = node.get("id") or node.element_id
            nodes[node_id] = {
                "id": node_id,
                "label": node.get("name", "Unknown"),
                "type": node.get("entity_type", "Entity"),
            }
            if include_communities and "community_id" in node:
                nodes[node_id]["community"] = node["community_id"]

        # Add relationship
        if "r" in record and record["r"]:
            rel = record["r"]
            edges.append({
                "source": rel.start_node.element_id,
                "target": rel.end_node.element_id,
                "type": rel.type,
            })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def _export_graphml(records: list[dict]) -> dict[str, str]:
    """Export graph as GraphML XML format."""
    # Simplified GraphML export
    graphml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    graphml += '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n'
    graphml += "  <graph edgedefault=\"directed\">\n"

    # Add nodes and edges (basic implementation)
    for record in records:
        if "n" in record and record["n"]:
            node = record["n"]
            node_id = node.get("id") or node.element_id
            graphml += f'    <node id="{node_id}"/>\n'

    graphml += "  </graph>\n</graphml>"

    return {"format": "graphml", "data": graphml}


def _export_cytoscape(records: list[dict]) -> dict[str, Any]:
    """Export graph as Cytoscape.js format."""
    elements = []

    for record in records:
        # Add node
        if "n" in record and record["n"]:
            node = record["n"]
            node_id = node.get("id") or node.element_id
            elements.append({
                "data": {
                    "id": node_id,
                    "label": node.get("name", "Unknown"),
                    "type": node.get("entity_type", "Entity"),
                }
            })

        # Add edge
        if "r" in record and record["r"]:
            rel = record["r"]
            elements.append({
                "data": {
                    "source": rel.start_node.element_id,
                    "target": rel.end_node.element_id,
                    "label": rel.type,
                }
            })

    return {"format": "cytoscape", "elements": elements}
