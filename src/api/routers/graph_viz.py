"""Graph Visualization API Router.

Sprint 12 Feature 12.8: Enhanced graph visualization endpoints.
Provides export, filtering, and community highlighting capabilities.

Sprint 29: Added 4 new endpoints for frontend graph visualization:
- POST /query-subgraph (Feature 29.2)
- GET /statistics (Feature 29.4)
- POST /node-documents (Feature 29.6)
- GET /communities/{community_id}/documents (Feature 29.7)
"""

from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.components.shared.embedding_service import UnifiedEmbeddingService
from src.components.vector_search.qdrant_client import QdrantClient

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
# Sprint 29: New Request/Response Models
# ============================================================================


class QuerySubgraphRequest(BaseModel):
    """Request model for query subgraph extraction (Feature 29.2)."""

    entity_names: list[str] = Field(
        description="list of entity names from query results",
        min_length=1,
    )


class GraphStatistics(BaseModel):
    """Response model for graph statistics (Feature 29.4)."""

    node_count: int = Field(description="Total number of nodes")
    edge_count: int = Field(description="Total number of edges")
    community_count: int = Field(description="Total number of communities")
    avg_degree: float = Field(description="Average node degree")
    entity_type_distribution: dict[str, int] = Field(description="Node count by entity type")
    orphaned_nodes: int = Field(description="Number of orphaned nodes (degree=0)")
    timestamp: str = Field(description="Timestamp of statistics")


class NodeDocumentsRequest(BaseModel):
    """Request model for node documents search (Feature 29.6)."""

    entity_name: str = Field(description="Entity name to search for", min_length=1)
    top_k: int = Field(default=10, ge=1, le=100, description="Number of top documents to return")


class RelatedDocument(BaseModel):
    """Related document with similarity score."""

    id: str = Field(description="Document ID")
    title: str = Field(description="Document title")
    excerpt: str = Field(description="Document excerpt (first 200 chars)")
    similarity: float = Field(description="Similarity score")
    chunk_id: str = Field(description="Chunk ID")
    source: str = Field(description="Document source")


class NodeDocumentsResponse(BaseModel):
    """Response model for node documents (Feature 29.6)."""

    entity_name: str = Field(description="Entity name searched")
    documents: list[RelatedDocument] = Field(description="Related documents")
    total: int = Field(description="Total documents found")


class CommunityDocument(BaseModel):
    """Document mentioning community entities."""

    id: str = Field(description="Document ID")
    title: str = Field(description="Document title")
    excerpt: str = Field(description="Document excerpt")
    entities: list[str] = Field(description="Entities mentioned in document")
    chunk_id: str = Field(description="Chunk ID")


class CommunityDocumentsResponse(BaseModel):
    """Response model for community documents (Feature 29.7)."""

    community_id: str = Field(description="Community ID")
    documents: list[CommunityDocument] = Field(description="Related documents")
    total: int = Field(description="Total documents found")


# ============================================================================
# Sprint 34: Multi-Hop Query Models
# ============================================================================


class MultiHopRequest(BaseModel):
    """Request for multi-hop graph traversal (Feature 34.5)."""

    entity_id: str = Field(..., description="Starting entity ID or name")
    max_hops: int = Field(default=2, ge=1, le=5, description="Maximum hops (1-5)")
    relationship_types: list[str] | None = Field(
        default=None, description="Filter by relationship types (e.g., ['RELATES_TO'])"
    )
    include_paths: bool = Field(default=False, description="Include full path information")


class GraphNode(BaseModel):
    """Graph node representation."""

    id: str = Field(description="Node ID")
    label: str = Field(description="Node label/name")
    type: str | None = Field(default=None, description="Node type")
    hops: int = Field(description="Distance from start entity")


class GraphEdge(BaseModel):
    """Graph edge representation."""

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    type: str = Field(description="Relationship type")
    weight: float | None = Field(default=None, description="Edge weight")
    description: str | None = Field(default=None, description="Edge description")


class MultiHopResponse(BaseModel):
    """Response with connected entities (Feature 34.5)."""

    start_entity: str = Field(description="Starting entity ID/name")
    max_hops: int = Field(description="Maximum hops used")
    nodes: list[GraphNode] = Field(description="Connected entities")
    edges: list[GraphEdge] = Field(description="Relationships")
    paths: list[list[str]] | None = Field(default=None, description="Full path info (optional)")


class ShortestPathRequest(BaseModel):
    """Request for shortest path between two entities (Feature 34.5)."""

    source_entity: str = Field(..., description="Source entity ID or name")
    target_entity: str = Field(..., description="Target entity ID or name")
    max_hops: int = Field(default=5, ge=1, le=10, description="Maximum hops (1-10)")


class PathRelationship(BaseModel):
    """Relationship in a path."""

    type: str = Field(description="Relationship type")
    weight: float | None = Field(default=None, description="Edge weight")


class ShortestPathResponse(BaseModel):
    """Response for shortest path query (Feature 34.5)."""

    found: bool = Field(description="Whether a path was found")
    path: list[str] | None = Field(default=None, description="Node names in path")
    relationships: list[PathRelationship] | None = Field(
        default=None, description="Relationships in path"
    )
    hops: int | None = Field(default=None, description="Path length")


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
        MATCH (n:base)
        {type_filter}
        WITH n
        LIMIT {request.max_nodes}
        OPTIONAL MATCH (n)-[r]->(m:base)
        RETURN n, r, m
        """

        async with neo4j.driver.session() as session:
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


# DEPRECATED: Not called from frontend (identified 2025-12-07)
# Export formats hardcoded in frontend - endpoint unnecessary
@router.get("/export/formats")
async def get_export_formats() -> dict[str, list[str]]:
    """Get supported export formats.

    DEPRECATED: This endpoint is not called from the frontend.
    Export formats are hardcoded in frontend code.
    Consider removal in next major version.

    Returns:
        list of supported formats with descriptions
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


# DEPRECATED: Not called from frontend (identified 2025-12-07)
# Graph filtering done client-side - server-side endpoint unnecessary
@router.post("/filter")
async def filter_graph(request: GraphFilterRequest) -> dict[str, Any]:
    """Filter graph by entity types and properties.

    DEPRECATED: This endpoint is not called from the frontend.
    Graph filtering is performed client-side in React components.
    Consider removal in next major version.

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
        MATCH (n:base)
        WHERE {where_clause}
        WITH n
        LIMIT 100
        OPTIONAL MATCH (n)-[r]->(m:base)
        RETURN n, r, m
        """

        async with neo4j.driver.session() as session:
            result = await session.run(query)
            records = await result.data()

        return _export_json(records, include_communities=True)

    except Exception as e:
        logger.error("graph_filter_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Filter failed: {e}") from e


# ============================================================================
# Community Endpoints
# ============================================================================


# DEPRECATED: Not called from frontend (identified 2025-12-07)
# Community highlighting done client-side - server-side endpoint unnecessary
@router.post("/communities/highlight")
async def highlight_communities(
    request: CommunityHighlightRequest,
) -> dict[str, Any]:
    """Highlight specific communities in graph.

    DEPRECATED: This endpoint is not called from the frontend.
    Community highlighting is performed client-side in React components.
    Consider removal in next major version.

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
        MATCH (n:base)
        WHERE n.community_id IN {request.community_ids}
        """

        if request.include_neighbors:
            query += """
            OPTIONAL MATCH (n)-[r]-(neighbor:base)
            RETURN n, r, neighbor
            """
        else:
            query += """
            WITH n
            OPTIONAL MATCH (n)-[r]->(m:base)
            WHERE m.community_id IN {request.community_ids}
            RETURN n, r, m
            """

        async with neo4j.driver.session() as session:
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
# Sprint 29: New Endpoints
# ============================================================================


@router.post("/query-subgraph")
async def get_query_subgraph(request: QuerySubgraphRequest) -> dict[str, Any]:
    """Get subgraph for specific entities from query results.

    Sprint 29 Feature 29.2: Extract subgraph containing entities and their
    1-hop relationships for visualization in query results.

    Args:
        request: Query subgraph request with entity names

    Returns:
        Subgraph containing entities and their relationships
    """
    try:
        neo4j = get_neo4j_client()

        query = """
        MATCH (n:base)
        WHERE n.entity_name IN $entity_names
        WITH n
        OPTIONAL MATCH (n)-[r]-(m:base)
        RETURN n, r, m
        """

        async with neo4j.driver.session() as session:
            result = await session.run(query, entity_names=request.entity_names)
            records = await result.data()

        logger.info(
            "query_subgraph_extracted",
            entity_count=len(request.entity_names),
            record_count=len(records),
        )

        return _export_json(records, include_communities=True)

    except Exception as e:
        logger.error("query_subgraph_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query subgraph failed: {e}") from e


@router.get("/statistics", response_model=GraphStatistics)
async def get_graph_statistics() -> GraphStatistics:
    """Get comprehensive graph statistics.

    Sprint 29 Feature 29.4: Provide high-level statistics about the knowledge graph
    including counts, distributions, and health metrics.

    Returns:
        Graph statistics including node/edge counts, entity type distribution,
        and health metrics
    """
    try:
        neo4j = get_neo4j_client()

        async with neo4j.driver.session() as session:
            # Node count
            node_result = await session.run("MATCH (n:base) RETURN count(n) as count")
            node_count = (await node_result.single())["count"]

            # Edge count
            edge_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            edge_count = (await edge_result.single())["count"]

            # Community count
            comm_result = await session.run(
                "MATCH (n:base) WHERE n.community_id IS NOT NULL "
                "RETURN count(DISTINCT n.community_id) as count"
            )
            community_count = (await comm_result.single())["count"]

            # Entity type distribution
            type_result = await session.run(
                "MATCH (n:base) RETURN n.entity_type as type, count(*) as count"
            )
            type_records = await type_result.data()
            entity_types = {record["type"]: record["count"] for record in type_records}

            # Orphaned nodes (degree = 0)
            orphan_result = await session.run(
                "MATCH (n:base) WHERE NOT (n)--() RETURN count(n) as count"
            )
            orphaned_nodes = (await orphan_result.single())["count"]

        avg_degree = (edge_count * 2) / node_count if node_count > 0 else 0.0

        logger.info(
            "graph_statistics_retrieved",
            node_count=node_count,
            edge_count=edge_count,
            community_count=community_count,
        )

        return GraphStatistics(
            node_count=node_count,
            edge_count=edge_count,
            community_count=community_count,
            avg_degree=avg_degree,
            entity_type_distribution=entity_types,
            orphaned_nodes=orphaned_nodes,
            timestamp=datetime.now(UTC).isoformat(),
        )

    except Exception as e:
        logger.error("graph_statistics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Statistics failed: {e}") from e


@router.post("/node-documents", response_model=NodeDocumentsResponse)
async def get_documents_by_node(request: NodeDocumentsRequest) -> NodeDocumentsResponse:
    """Get related documents for an entity using vector similarity.

    Sprint 29 Feature 29.6: Find documents related to a graph entity by
    embedding the entity name and searching Qdrant for similar chunks.

    Args:
        request: Node documents request with entity name and top_k

    Returns:
        list of related documents with similarity scores
    """
    try:
        # 1. Generate embedding for entity name
        embedding_service = UnifiedEmbeddingService()
        query_vector = await embedding_service.embed(request.entity_name)

        # 2. Search Qdrant
        qdrant = QdrantClient()
        results = await qdrant.search(
            collection_name="aegis-rag-documents",
            query_vector=query_vector,
            limit=request.top_k,
        )

        # 3. Format results
        documents = []
        for result in results:
            payload = result.payload or {}
            documents.append(
                RelatedDocument(
                    id=str(result.id),
                    title=payload.get("source", "Unknown"),
                    excerpt=payload.get("text", "")[:200],
                    similarity=result.score,
                    chunk_id=payload.get("chunk_id", ""),
                    source=payload.get("source", "Unknown"),
                )
            )

        logger.info(
            "node_documents_retrieved",
            entity_name=request.entity_name,
            document_count=len(documents),
        )

        return NodeDocumentsResponse(
            entity_name=request.entity_name,
            documents=documents,
            total=len(documents),
        )

    except Exception as e:
        logger.error("node_documents_failed", error=str(e), entity=request.entity_name)
        raise HTTPException(status_code=500, detail=f"Node documents search failed: {e}") from e


@router.get("/communities/{community_id}/documents", response_model=CommunityDocumentsResponse)
async def get_community_documents(community_id: str, limit: int = 50) -> CommunityDocumentsResponse:
    """Get all documents mentioning entities from a community.

    Sprint 29 Feature 29.7: Find documents that mention entities belonging to
    a specific community by searching Qdrant for chunks containing entity names.

    Args:
        community_id: Community ID
        limit: Maximum documents to return (default 50)

    Returns:
        Documents with entity mentions from the community
    """
    try:
        neo4j = get_neo4j_client()

        # 1. Get entities in community
        async with neo4j.driver.session() as session:
            entity_result = await session.run(
                "MATCH (n:base {community_id: $community_id}) "
                "RETURN collect(n.name) as entity_names",
                community_id=community_id,
            )
            entity_record = await entity_result.single()
            entity_names = entity_record["entity_names"] if entity_record else []

        if not entity_names:
            logger.warning("community_not_found", community_id=community_id)
            raise HTTPException(status_code=404, detail=f"Community {community_id} not found")

        # 2. Find documents mentioning these entities
        qdrant = QdrantClient()
        embedding_service = UnifiedEmbeddingService()
        documents: list[CommunityDocument] = []
        seen_doc_ids: set[str] = set()

        # Sample first 10 entities to avoid excessive queries
        for entity_name in entity_names[:10]:
            # Generate embedding for entity name
            query_vector = await embedding_service.embed(entity_name)

            # Search using vector similarity
            results = await qdrant.search(
                collection_name="aegis-rag-documents",
                query_vector=query_vector,
                limit=limit,
            )

            for result in results:
                payload = result.payload or {}
                doc_id = str(result.id)

                # Avoid duplicates
                if doc_id not in seen_doc_ids:
                    seen_doc_ids.add(doc_id)
                    documents.append(
                        CommunityDocument(
                            id=doc_id,
                            title=payload.get("source", "Unknown"),
                            excerpt=payload.get("text", "")[:200],
                            entities=[entity_name],
                            chunk_id=payload.get("chunk_id", ""),
                        )
                    )

                # Stop if we've reached limit
                if len(documents) >= limit:
                    break

            if len(documents) >= limit:
                break

        logger.info(
            "community_documents_retrieved",
            community_id=community_id,
            entity_count=len(entity_names),
            document_count=len(documents),
        )

        return CommunityDocumentsResponse(
            community_id=community_id,
            documents=documents[:limit],
            total=len(documents),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("community_documents_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Community documents search failed: {e}"
        ) from e


# ============================================================================
# Sprint 34: Multi-Hop Query Endpoints
# ============================================================================


# DEPRECATED: Not called from frontend (identified 2025-12-07)
# Sprint 34 Multi-Hop feature not integrated in frontend - endpoint unused
@router.post("/multi-hop", response_model=MultiHopResponse)
async def get_multi_hop_subgraph(request: MultiHopRequest) -> MultiHopResponse:
    """Get entities connected within N hops via RELATES_TO relationships.

    DEPRECATED: This endpoint is not called from the frontend.
    Sprint 34 Multi-Hop Query feature was implemented but never integrated in UI.
    Consider removal in next major version or complete UI integration.

    Sprint 34 Feature 34.5: Multi-Hop Query Support

    Traverses the knowledge graph starting from a given entity and finds all
    connected entities within N hops. Supports filtering by relationship types
    and optional path tracking.

    Args:
        request: Multi-hop request with entity_id, max_hops, and filters

    Returns:
        Subgraph with nodes, edges, and optional paths

    Raises:
        HTTPException: If query fails or entity not found
    """
    try:
        neo4j = get_neo4j_client()

        # Build relationship type filter
        rel_filter = ""
        if request.relationship_types:
            rel_types = "|".join(request.relationship_types)
            rel_filter = f":{rel_types}"

        # Query for n-hop connected entities
        # Note: Using entity_name for matching (standard in AegisRAG schema)
        query = f"""
        MATCH path = (start:base {{entity_name: $entity_id}})-[r{rel_filter}*1..{request.max_hops}]-(connected:base)
        WITH DISTINCT connected, path, length(path) as hops
        RETURN connected.entity_id AS entity_id,
               connected.entity_name AS entity_name,
               connected.entity_type AS entity_type,
               hops,
               [rel in relationships(path) | type(rel)] AS rel_types,
               [node in nodes(path) | node.entity_name] AS path_nodes
        ORDER BY hops, entity_name
        LIMIT 100
        """

        results = await neo4j.execute_query(query, {"entity_id": request.entity_id})

        # Build nodes and edges
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_nodes: set[str] = set()
        seen_edges: set[str] = set()
        paths: list[list[str]] = [] if request.include_paths else None

        # Add starting node
        nodes.append(
            GraphNode(
                id=request.entity_id,
                label=request.entity_id,
                type="start",
                hops=0,
            )
        )
        seen_nodes.add(request.entity_id)

        for record in results:
            # Add connected node
            node_id = record.get("entity_id") or record["entity_name"]
            if node_id not in seen_nodes:
                nodes.append(
                    GraphNode(
                        id=node_id,
                        label=record["entity_name"],
                        type=record.get("entity_type"),
                        hops=record["hops"],
                    )
                )
                seen_nodes.add(node_id)

            # Track paths
            if request.include_paths and record.get("path_nodes"):
                paths.append(record["path_nodes"])

        # Get edges between found nodes (separate query for clarity)
        if len(nodes) > 1:
            node_ids = [n.id for n in nodes]
            edge_query = """
            MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
            WHERE (e1.entity_id IN $node_ids OR e1.entity_name IN $node_ids)
              AND (e2.entity_id IN $node_ids OR e2.entity_name IN $node_ids)
            RETURN COALESCE(e1.entity_id, e1.entity_name) AS source,
                   COALESCE(e2.entity_id, e2.entity_name) AS target,
                   type(r) AS type,
                   r.weight AS weight,
                   r.description AS description
            """
            edge_results = await neo4j.execute_query(edge_query, {"node_ids": node_ids})

            for edge in edge_results:
                edge_key = f"{edge['source']}->{edge['target']}"
                if edge_key not in seen_edges:
                    edges.append(
                        GraphEdge(
                            source=edge["source"],
                            target=edge["target"],
                            type=edge["type"],
                            weight=edge.get("weight"),
                            description=edge.get("description"),
                        )
                    )
                    seen_edges.add(edge_key)

        logger.info(
            "multi_hop_query_executed",
            entity_id=request.entity_id,
            max_hops=request.max_hops,
            node_count=len(nodes),
            edge_count=len(edges),
        )

        return MultiHopResponse(
            start_entity=request.entity_id,
            max_hops=request.max_hops,
            nodes=nodes,
            edges=edges,
            paths=paths,
        )

    except Exception as e:
        logger.error("multi_hop_query_failed", error=str(e), entity=request.entity_id)
        raise HTTPException(
            status_code=500, detail=f"Multi-hop query failed: {e}"
        ) from e


# DEPRECATED: Not called from frontend (identified 2025-12-07)
# Sprint 34 Shortest Path feature not integrated in frontend - endpoint unused
@router.post("/shortest-path", response_model=ShortestPathResponse)
async def get_shortest_path(request: ShortestPathRequest) -> ShortestPathResponse:
    """Find shortest path between two entities via RELATES_TO.

    DEPRECATED: This endpoint is not called from the frontend.
    Sprint 34 Shortest Path feature was implemented but never integrated in UI.
    Consider removal in next major version or complete UI integration.

    Sprint 34 Feature 34.5: Multi-Hop Query Support

    Uses Neo4j's shortestPath algorithm to find the shortest path between
    two entities in the knowledge graph.

    Args:
        request: Shortest path request with source and target entities

    Returns:
        Shortest path with node names and relationships

    Raises:
        HTTPException: If query fails
    """
    try:
        neo4j = get_neo4j_client()

        # Cypher query for shortest path
        query = f"""
        MATCH (start:base {{entity_name: $source}}), (end:base {{entity_name: $target}})
        MATCH path = shortestPath((start)-[:RELATES_TO*1..{request.max_hops}]-(end))
        RETURN [node in nodes(path) | node.entity_name] AS path_nodes,
               [rel in relationships(path) | {{type: type(rel), weight: rel.weight}}] AS path_rels,
               length(path) AS hops
        """

        results = await neo4j.execute_query(
            query,
            {"source": request.source_entity, "target": request.target_entity},
        )

        if not results or len(results) == 0:
            logger.info(
                "shortest_path_not_found",
                source=request.source_entity,
                target=request.target_entity,
            )
            return ShortestPathResponse(found=False, path=None, relationships=None, hops=None)

        record = results[0]
        path_rels = [PathRelationship(**rel) for rel in record["path_rels"]]

        logger.info(
            "shortest_path_found",
            source=request.source_entity,
            target=request.target_entity,
            hops=record["hops"],
        )

        return ShortestPathResponse(
            found=True,
            path=record["path_nodes"],
            relationships=path_rels,
            hops=record["hops"],
        )

    except Exception as e:
        logger.error(
            "shortest_path_query_failed",
            error=str(e),
            source=request.source_entity,
            target=request.target_entity,
        )
        raise HTTPException(
            status_code=500, detail=f"Shortest path query failed: {e}"
        ) from e


# ============================================================================
# Helper Functions
# ============================================================================


def _export_json(records: list[dict], include_communities: bool = True) -> dict[str, Any]:
    """Export graph as JSON format.

    Note: Records from session.run().data() are already dicts, not Neo4j objects.
    Node properties are accessed via dict keys like node["name"], node["entity_type"].
    """
    nodes = {}
    edges = []

    for record in records:
        # Add node (n is a dict with node properties)
        if "n" in record and record["n"]:
            node = record["n"]
            # Use entity_id or entity_name as unique identifier (standard in AegisRAG schema)
            node_id = node.get("entity_id") or node.get("entity_name") or node.get("name") or node.get("id") or str(id(node))
            nodes[node_id] = {
                "id": node_id,
                "label": node.get("entity_name") or node.get("name") or "Unknown",
                "type": node.get("entity_type") or "Entity",
            }
            if include_communities and node.get("community_id"):
                nodes[node_id]["community"] = node["community_id"]

        # Add target node (m) if present
        if "m" in record and record["m"]:
            target_node = record["m"]
            target_id = target_node.get("entity_id") or target_node.get("entity_name") or target_node.get("name") or target_node.get("id") or str(id(target_node))
            if target_id not in nodes:
                nodes[target_id] = {
                    "id": target_id,
                    "label": target_node.get("entity_name") or target_node.get("name") or "Unknown",
                    "type": target_node.get("entity_type") or "Entity",
                }
                if include_communities and target_node.get("community_id"):
                    nodes[target_id]["community"] = target_node["community_id"]

        # Add relationship (r is a dict with rel properties or tuple for relationship)
        if "r" in record and record["r"]:
            rel = record["r"]
            # Get source and target from the relationship dict
            # When using .data(), relationships come as dicts with limited info
            # We need to get source/target from the node data in the same record
            source_node = record.get("n", {})
            target_node = record.get("m", {})
            source_id = source_node.get("entity_id") or source_node.get("entity_name") or source_node.get("name") or source_node.get("id") if source_node else None
            target_id = target_node.get("entity_id") or target_node.get("entity_name") or target_node.get("name") or target_node.get("id") if target_node else None

            if source_id and target_id:
                # Get relationship type - may be stored as 'type' or as a tuple with type info
                rel_type = rel[1] if isinstance(rel, tuple) else (rel.get("type") or "RELATES_TO")
                edges.append(
                    {
                        "source": source_id,
                        "target": target_id,
                        "type": rel_type,
                        "weight": rel.get("weight") if isinstance(rel, dict) else None,
                    }
                )

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def _export_graphml(records: list[dict]) -> dict[str, str]:
    """Export graph as GraphML XML format.

    Note: Records from session.run().data() are already dicts.
    """
    # Simplified GraphML export
    graphml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    graphml += '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n'
    graphml += '  <graph edgedefault="directed">\n'

    seen_nodes = set()
    # Add nodes and edges (basic implementation)
    for record in records:
        if "n" in record and record["n"]:
            node = record["n"]
            node_id = node.get("entity_id") or node.get("entity_name") or node.get("name") or node.get("id") or str(id(node))
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                graphml += f'    <node id="{node_id}"/>\n'

        if "m" in record and record["m"]:
            target_node = record["m"]
            target_id = target_node.get("entity_id") or target_node.get("entity_name") or target_node.get("name") or target_node.get("id") or str(id(target_node))
            if target_id not in seen_nodes:
                seen_nodes.add(target_id)
                graphml += f'    <node id="{target_id}"/>\n'

    graphml += "  </graph>\n</graphml>"

    return {"format": "graphml", "data": graphml}


def _export_cytoscape(records: list[dict]) -> dict[str, Any]:
    """Export graph as Cytoscape.js format.

    Note: Records from session.run().data() are already dicts.
    """
    elements = []
    seen_nodes = set()

    for record in records:
        # Add node
        if "n" in record and record["n"]:
            node = record["n"]
            node_id = node.get("entity_id") or node.get("entity_name") or node.get("name") or node.get("id") or str(id(node))
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                elements.append(
                    {
                        "data": {
                            "id": node_id,
                            "label": node.get("entity_name") or node.get("name") or "Unknown",
                            "type": node.get("entity_type") or "Entity",
                        }
                    }
                )

        # Add target node
        if "m" in record and record["m"]:
            target_node = record["m"]
            target_id = target_node.get("entity_id") or target_node.get("entity_name") or target_node.get("name") or target_node.get("id") or str(id(target_node))
            if target_id not in seen_nodes:
                seen_nodes.add(target_id)
                elements.append(
                    {
                        "data": {
                            "id": target_id,
                            "label": target_node.get("entity_name") or target_node.get("name") or "Unknown",
                            "type": target_node.get("entity_type") or "Entity",
                        }
                    }
                )

        # Add edge
        if "r" in record and record["r"]:
            source_node = record.get("n", {})
            target_node = record.get("m", {})
            source_id = source_node.get("entity_id") or source_node.get("entity_name") or source_node.get("name") or source_node.get("id") if source_node else None
            target_id = target_node.get("entity_id") or target_node.get("entity_name") or target_node.get("name") or target_node.get("id") if target_node else None

            if source_id and target_id:
                rel = record["r"]
                rel_type = rel[1] if isinstance(rel, tuple) else (rel.get("type") or "RELATES_TO")
                elements.append(
                    {
                        "data": {
                            "source": source_id,
                            "target": target_id,
                            "label": rel_type,
                        }
                    }
                )

    return {"format": "cytoscape", "elements": elements}
