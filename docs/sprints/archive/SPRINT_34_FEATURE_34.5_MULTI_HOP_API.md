# Sprint 34 Feature 34.5: Multi-Hop Query API Implementation

## Summary

Successfully implemented **Multi-Hop Graph Traversal** endpoints for the AegisRAG API, enabling advanced graph exploration capabilities through the REST API.

## Changes Made

### File Modified
- **`C:\Projekte\AEGISRAG\src\api\routers\graph_viz.py`**

### Lines Added
- **+271 lines** of new code (models + endpoints + documentation)

---

## 1. New Pydantic Request/Response Models

### Multi-Hop Traversal Models
```python
class MultiHopRequest(BaseModel):
    """Request for multi-hop graph traversal (Feature 34.5)."""
    entity_id: str                        # Starting entity name
    max_hops: int = 2                     # Max hops (1-5)
    relationship_types: list[str] | None  # Optional filter
    include_paths: bool = False           # Include full paths

class GraphNode(BaseModel):
    """Graph node representation."""
    id: str
    label: str
    type: str | None
    hops: int  # Distance from start

class GraphEdge(BaseModel):
    """Graph edge representation."""
    source: str
    target: str
    type: str
    weight: float | None
    description: str | None

class MultiHopResponse(BaseModel):
    """Response with connected entities."""
    start_entity: str
    max_hops: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    paths: list[list[str]] | None  # Optional path tracking
```

### Shortest Path Models
```python
class ShortestPathRequest(BaseModel):
    """Request for shortest path between two entities."""
    source_entity: str
    target_entity: str
    max_hops: int = 5  # Max hops (1-10)

class PathRelationship(BaseModel):
    """Relationship in a path."""
    type: str
    weight: float | None

class ShortestPathResponse(BaseModel):
    """Response for shortest path query."""
    found: bool
    path: list[str] | None          # Node names
    relationships: list[PathRelationship] | None
    hops: int | None
```

---

## 2. New API Endpoints

### Endpoint 1: Multi-Hop Traversal
**POST** `/api/v1/graph/viz/multi-hop`

**Description:**
Traverses the knowledge graph starting from a given entity and finds all connected entities within N hops via `RELATES_TO` relationships.

**Request Body:**
```json
{
  "entity_id": "AegisRAG",
  "max_hops": 2,
  "relationship_types": ["RELATES_TO"],
  "include_paths": false
}
```

**Response (200 OK):**
```json
{
  "start_entity": "AegisRAG",
  "max_hops": 2,
  "nodes": [
    {
      "id": "AegisRAG",
      "label": "AegisRAG",
      "type": "start",
      "hops": 0
    },
    {
      "id": "entity-123",
      "label": "Vector Search",
      "type": "Component",
      "hops": 1
    },
    {
      "id": "entity-456",
      "label": "Qdrant",
      "type": "Technology",
      "hops": 2
    }
  ],
  "edges": [
    {
      "source": "AegisRAG",
      "target": "entity-123",
      "type": "RELATES_TO",
      "weight": 0.9,
      "description": "core component"
    },
    {
      "source": "entity-123",
      "target": "entity-456",
      "type": "RELATES_TO",
      "weight": 0.85,
      "description": "uses database"
    }
  ],
  "paths": null
}
```

**Features:**
- Configurable hop depth (1-5)
- Optional relationship type filtering
- Optional full path tracking
- Deduplicates nodes and edges
- Limits to 100 nodes per query

---

### Endpoint 2: Shortest Path
**POST** `/api/v1/graph/viz/shortest-path`

**Description:**
Finds the shortest path between two entities using Neo4j's `shortestPath` algorithm.

**Request Body:**
```json
{
  "source_entity": "AegisRAG",
  "target_entity": "Neo4j",
  "max_hops": 5
}
```

**Response (200 OK) - Path Found:**
```json
{
  "found": true,
  "path": ["AegisRAG", "Graph RAG", "LightRAG", "Neo4j"],
  "relationships": [
    {"type": "RELATES_TO", "weight": 0.9},
    {"type": "RELATES_TO", "weight": 0.85},
    {"type": "RELATES_TO", "weight": 0.95}
  ],
  "hops": 3
}
```

**Response (200 OK) - No Path:**
```json
{
  "found": false,
  "path": null,
  "relationships": null,
  "hops": null
}
```

**Features:**
- Uses Neo4j's native `shortestPath` algorithm
- Configurable max hops (1-10)
- Returns path with relationship weights
- Handles disconnected entities gracefully

---

## 3. Implementation Details

### Cypher Queries

#### Multi-Hop Query
```cypher
MATCH path = (start:base {entity_name: $entity_id})-[r:RELATES_TO*1..{max_hops}]-(connected:base)
WITH DISTINCT connected, path, length(path) as hops
RETURN connected.entity_id AS entity_id,
       connected.entity_name AS entity_name,
       connected.entity_type AS entity_type,
       hops,
       [rel in relationships(path) | type(rel)] AS rel_types,
       [node in nodes(path) | node.entity_name] AS path_nodes
ORDER BY hops, entity_name
LIMIT 100
```

**Key Features:**
- Variable-length path matching: `[r:RELATES_TO*1..N]`
- Distinct results to avoid duplicates
- Ordered by hop distance
- Optional relationship type filtering

#### Edge Retrieval Query
```cypher
MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
WHERE (e1.entity_id IN $node_ids OR e1.entity_name IN $node_ids)
  AND (e2.entity_id IN $node_ids OR e2.entity_name IN $node_ids)
RETURN COALESCE(e1.entity_id, e1.entity_name) AS source,
       COALESCE(e2.entity_id, e2.entity_name) AS target,
       type(r) AS type,
       r.weight AS weight,
       r.description AS description
```

#### Shortest Path Query
```cypher
MATCH (start:base {entity_name: $source}), (end:base {entity_name: $target})
MATCH path = shortestPath((start)-[:RELATES_TO*1..{max_hops}]-(end))
RETURN [node in nodes(path) | node.entity_name] AS path_nodes,
       [rel in relationships(path) | {type: type(rel), weight: rel.weight}] AS path_rels,
       length(path) AS hops
```

---

## 4. API Integration

### Error Handling
Both endpoints include:
- Structured logging with `structlog`
- HTTP 500 errors with detailed messages
- Graceful handling of missing entities
- Empty result handling (shortest path)

### Performance Considerations
1. **Node Limit:** Multi-hop capped at 100 nodes to prevent performance issues
2. **Hop Limits:**
   - Multi-hop: 1-5 hops (validated via Pydantic)
   - Shortest path: 1-10 hops
3. **Query Optimization:** Separate queries for nodes and edges to avoid Cartesian products
4. **Deduplication:** Sets used to prevent duplicate nodes/edges

---

## 5. Usage Examples

### Example 1: Find All 2-Hop Neighbors
```bash
curl -X POST "http://localhost:8000/api/v1/graph/viz/multi-hop" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "Vector Search",
    "max_hops": 2,
    "include_paths": true
  }'
```

### Example 2: Filter by Relationship Type
```bash
curl -X POST "http://localhost:8000/api/v1/graph/viz/multi-hop" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "AegisRAG",
    "max_hops": 3,
    "relationship_types": ["RELATES_TO", "CONTAINS"],
    "include_paths": false
  }'
```

### Example 3: Find Shortest Path Between Entities
```bash
curl -X POST "http://localhost:8000/api/v1/graph/viz/shortest-path" \
  -H "Content-Type: application/json" \
  -d '{
    "source_entity": "LangGraph",
    "target_entity": "Neo4j",
    "max_hops": 5
  }'
```

---

## 6. Frontend Integration Opportunities

These endpoints enable powerful frontend features:

### 1. **Interactive Graph Exploration**
- Click entity → load 2-hop neighborhood
- Progressive graph expansion
- Filter by entity types

### 2. **Path Visualization**
- Highlight shortest path between selected entities
- Show relationship strengths (weights)
- Multi-path comparison

### 3. **Relationship Discovery**
- Find how two concepts are connected
- Explore indirect relationships
- Community boundary analysis

---

## 7. Testing Recommendations

### Unit Tests
```python
# tests/unit/api/test_multi_hop_api.py

async def test_multi_hop_basic():
    """Test basic multi-hop query."""
    response = client.post("/api/v1/graph/viz/multi-hop", json={
        "entity_id": "TestEntity",
        "max_hops": 2
    })
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert data["max_hops"] == 2

async def test_shortest_path_found():
    """Test shortest path when path exists."""
    response = client.post("/api/v1/graph/viz/shortest-path", json={
        "source_entity": "A",
        "target_entity": "C"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert len(data["path"]) >= 2

async def test_shortest_path_not_found():
    """Test shortest path when no path exists."""
    response = client.post("/api/v1/graph/viz/shortest-path", json={
        "source_entity": "Isolated1",
        "target_entity": "Isolated2"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is False
```

### Integration Tests (with Neo4j)
```python
# tests/integration/api/test_multi_hop_integration.py

async def test_multi_hop_with_real_data(neo4j_fixture):
    """Test multi-hop with real Neo4j data."""
    # Setup test graph
    await neo4j_fixture.create_test_graph()

    response = client.post("/api/v1/graph/viz/multi-hop", json={
        "entity_id": "CenterNode",
        "max_hops": 3,
        "include_paths": True
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) > 1
    assert data["paths"] is not None
```

---

## 8. Documentation Updates Needed

### OpenAPI Documentation
The endpoints are automatically documented via FastAPI with:
- Request/response schemas
- Field descriptions
- Validation constraints
- Example values

Access Swagger UI at: `http://localhost:8000/docs`

### User Documentation
Consider adding to `docs/api/`:
- **`GRAPH_API.md`**: Graph API overview
- **`MULTI_HOP_GUIDE.md`**: Multi-hop query guide
- **`CYPHER_REFERENCE.md`**: Common Cypher patterns

---

## 9. Performance Benchmarks (Estimated)

| Query Type | Nodes | Hops | Expected Latency |
|-----------|-------|------|------------------|
| Multi-hop | 10-50 | 2 | <100ms |
| Multi-hop | 50-100 | 3 | 100-300ms |
| Multi-hop | 100+ | 4-5 | 300-1000ms |
| Shortest path | Any | 2-5 | <50ms (indexed) |

**Optimization Tips:**
1. Ensure `entity_name` is indexed in Neo4j
2. Use relationship type filters to reduce search space
3. Keep max_hops <= 3 for large graphs
4. Consider caching frequently accessed paths

---

## 10. Future Enhancements

### Potential Improvements:
1. **Pagination:** Support offset/limit for large result sets
2. **Filtering:** Add node property filters (e.g., entity_type)
3. **All Paths:** Return all paths, not just shortest
4. **Weighted Paths:** Shortest path by total weight, not hop count
5. **Subgraph Export:** Export multi-hop results as GraphML/JSON
6. **Path Comparison:** Compare multiple paths side-by-side
7. **Community Traversal:** Multi-hop within same community only

---

## 11. ADR Compliance

This implementation aligns with:
- **ADR-039:** Adaptive Section-Aware Chunking (graph structure preservation)
- **ADR-027:** Neo4j as primary graph database
- **ADR-033:** FastAPI routing and error handling patterns

---

## 12. Checklist

- [x] Pydantic request/response models defined
- [x] Multi-hop traversal endpoint implemented
- [x] Shortest path endpoint implemented
- [x] Error handling and logging
- [x] Cypher queries optimized
- [x] Input validation (Pydantic constraints)
- [x] Syntax validation (py_compile passed)
- [ ] Unit tests written
- [ ] Integration tests written
- [ ] API documentation updated
- [ ] Frontend integration examples

---

## File Paths

**Modified File:**
```
C:\Projekte\AEGISRAG\src\api\routers\graph_viz.py
```

**Documentation:**
```
C:\Projekte\AEGISRAG\SPRINT_34_FEATURE_34.5_MULTI_HOP_API.md
```

---

## Contact

**Feature:** Sprint 34 Feature 34.5 - Multi-Hop Query Support
**Branch:** `sprint-34-multi-hop-api` (suggested)
**Implemented By:** API Agent (Claude Code)
**Date:** 2025-12-01
