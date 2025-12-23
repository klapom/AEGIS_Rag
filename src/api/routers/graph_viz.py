"""Graph Visualization API Router.

Sprint 12 Feature 12.8: Enhanced graph visualization endpoints.
Provides graph export capabilities.

Sprint 29: Added 4 endpoints for frontend graph visualization:
- POST /query-subgraph (Feature 29.2): Extract subgraph for specific entities
- GET /statistics (Feature 29.4): Get comprehensive graph statistics
- POST /node-documents (Feature 29.6): Find documents related to entities
- GET /communities/{community_id}/documents (Feature 29.7): Find documents by community

Sprint 61 Feature 61.4: Removed 5 deprecated endpoints (not used by frontend):
- GET /export/formats (formats hardcoded in frontend)
- POST /filter (filtering done client-side)
- POST /communities/highlight (highlighting done client-side)
- POST /multi-hop (Sprint 34 feature never integrated in UI)
- POST /shortest-path (Sprint 34 feature never integrated in UI)
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

        # Build filter conditions (without WHERE keyword)
        type_condition = ""
        if request.entity_types:
            type_condition = f"n.entity_type IN {request.entity_types}"

        # Query nodes - entities
        node_query = f"""
        MATCH (n:base)
        {f'WHERE {type_condition}' if type_condition else ''}
        RETURN n
        LIMIT {request.max_nodes}
        """

        # Query entity-to-entity connections via shared chunks (co-occurrence)
        # Two entities are connected if they are MENTIONED_IN the same chunk
        co_occurs_condition = type_condition.replace("n.", "e1.") if type_condition else ""
        edge_query = f"""
        MATCH (e1:base)-[:MENTIONED_IN]->(c:chunk)<-[:MENTIONED_IN]-(e2:base)
        WHERE id(e1) < id(e2) {f'AND {co_occurs_condition}' if co_occurs_condition else ''}
        WITH e1, e2, count(c) as shared_chunks
        RETURN e1, e2, shared_chunks
        LIMIT 500
        """

        # Query MENTIONED_IN relationships (entity -> chunk)
        mentioned_query = f"""
        MATCH (n:base)-[r:MENTIONED_IN]->(c:chunk)
        {f'WHERE {type_condition}' if type_condition else ''}
        RETURN n, r, c
        LIMIT 500
        """

        async with neo4j.driver.session() as session:
            # Get nodes (entities)
            node_result = await session.run(node_query)
            node_records = await node_result.data()

            # Get CO_OCCURS edges (entity co-occurrence)
            edge_result = await session.run(edge_query)
            edge_records = await edge_result.data()

            # Get MENTIONED_IN edges (entity -> chunk)
            mentioned_result = await session.run(mentioned_query)
            mentioned_records = await mentioned_result.data()

        # Combine into records format expected by _export_json
        records = []
        for rec in node_records:
            records.append({"n": rec["n"], "r": None, "m": None})

        # Add CO_OCCURS edges (entity-to-entity via shared chunks)
        for rec in edge_records:
            records.append(
                {
                    "n": rec["e1"],
                    "r": {"type": "CO_OCCURS", "weight": min(1.0, rec["shared_chunks"] / 5.0)},
                    "m": rec["e2"],
                }
            )

        # Add MENTIONED_IN edges (entity -> chunk)
        for rec in mentioned_records:
            # Add chunk as a node too
            chunk = rec["c"]
            records.append(
                {
                    "n": rec["n"],
                    "r": {"type": "MENTIONED_IN"},
                    "m": {
                        "entity_name": chunk.get("chunk_id", chunk.get("id", "chunk")),
                        "entity_type": "CHUNK",
                        **chunk,
                    },
                }
            )

        # Format based on export type
        if request.format == "json":
            return _export_json(records, request.include_communities)
        elif request.format == "graphml":
            return _export_graphml(records)
        elif request.format == "cytoscape":
            return _export_cytoscape(records)

        # Fallback (should not reach here)
        return _export_json(records, request.include_communities)

    except Exception as e:
        logger.error("graph_export_failed", error=str(e), format=request.format)
        raise HTTPException(status_code=500, detail=f"Export failed: {e}") from e


# ============================================================================
# Sprint 29: Graph Visualization Endpoints
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
            node_id = (
                node.get("entity_id")
                or node.get("entity_name")
                or node.get("name")
                or node.get("id")
                or str(id(node))
            )
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
            target_id = (
                target_node.get("entity_id")
                or target_node.get("entity_name")
                or target_node.get("name")
                or target_node.get("id")
                or str(id(target_node))
            )
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
            source_id = (
                source_node.get("entity_id")
                or source_node.get("entity_name")
                or source_node.get("name")
                or source_node.get("id")
                if source_node
                else None
            )
            target_id = (
                target_node.get("entity_id")
                or target_node.get("entity_name")
                or target_node.get("name")
                or target_node.get("id")
                if target_node
                else None
            )

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
            node_id = (
                node.get("entity_id")
                or node.get("entity_name")
                or node.get("name")
                or node.get("id")
                or str(id(node))
            )
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                graphml += f'    <node id="{node_id}"/>\n'

        if "m" in record and record["m"]:
            target_node = record["m"]
            target_id = (
                target_node.get("entity_id")
                or target_node.get("entity_name")
                or target_node.get("name")
                or target_node.get("id")
                or str(id(target_node))
            )
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
            node_id = (
                node.get("entity_id")
                or node.get("entity_name")
                or node.get("name")
                or node.get("id")
                or str(id(node))
            )
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
            target_id = (
                target_node.get("entity_id")
                or target_node.get("entity_name")
                or target_node.get("name")
                or target_node.get("id")
                or str(id(target_node))
            )
            if target_id not in seen_nodes:
                seen_nodes.add(target_id)
                elements.append(
                    {
                        "data": {
                            "id": target_id,
                            "label": target_node.get("entity_name")
                            or target_node.get("name")
                            or "Unknown",
                            "type": target_node.get("entity_type") or "Entity",
                        }
                    }
                )

        # Add edge
        if "r" in record and record["r"]:
            source_node = record.get("n", {})
            target_node = record.get("m", {})
            source_id = (
                source_node.get("entity_id")
                or source_node.get("entity_name")
                or source_node.get("name")
                or source_node.get("id")
                if source_node
                else None
            )
            target_id = (
                target_node.get("entity_id")
                or target_node.get("entity_name")
                or target_node.get("name")
                or target_node.get("id")
                if target_node
                else None
            )

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
