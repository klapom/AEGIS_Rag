# Multi-Hop Graph Traversal Endpoints

**Sprint 34 Feature 34.5**

Quick reference for the new multi-hop graph traversal API endpoints.

---

## Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/graph/viz/multi-hop` | POST | Find all entities within N hops |
| `/api/v1/graph/viz/shortest-path` | POST | Find shortest path between entities |

---

## 1. Multi-Hop Traversal

### Endpoint
```
POST /api/v1/graph/viz/multi-hop
```

### Description
Traverses the knowledge graph from a starting entity and finds all connected entities within N hops via RELATES_TO relationships.

### Request Body
```json
{
  "entity_id": "string",              // Required: Starting entity name
  "max_hops": 2,                      // Optional: 1-5 (default: 2)
  "relationship_types": ["RELATES_TO"], // Optional: filter by rel types
  "include_paths": false              // Optional: include full paths
}
```

### Response (200 OK)
```json
{
  "start_entity": "string",
  "max_hops": 2,
  "nodes": [
    {
      "id": "string",
      "label": "string",
      "type": "string",
      "hops": 0
    }
  ],
  "edges": [
    {
      "source": "string",
      "target": "string",
      "type": "RELATES_TO",
      "weight": 0.9,
      "description": "string"
    }
  ],
  "paths": null  // or array of string arrays if include_paths=true
}
```

### Examples

#### Basic 2-Hop Query
```bash
curl -X POST "http://localhost:8000/api/v1/graph/viz/multi-hop" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "AegisRAG"
  }'
```

#### With Path Tracking
```bash
curl -X POST "http://localhost:8000/api/v1/graph/viz/multi-hop" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "Vector Search",
    "max_hops": 3,
    "include_paths": true
  }'
```

#### With Relationship Filter
```bash
curl -X POST "http://localhost:8000/api/v1/graph/viz/multi-hop" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "Neo4j",
    "max_hops": 2,
    "relationship_types": ["RELATES_TO"]
  }'
```

---

## 2. Shortest Path

### Endpoint
```
POST /api/v1/graph/viz/shortest-path
```

### Description
Finds the shortest path between two entities using Neo4j's shortestPath algorithm.

### Request Body
```json
{
  "source_entity": "string",  // Required: Source entity name
  "target_entity": "string",  // Required: Target entity name
  "max_hops": 5               // Optional: 1-10 (default: 5)
}
```

### Response (200 OK) - Path Found
```json
{
  "found": true,
  "path": ["Entity A", "Entity B", "Entity C"],
  "relationships": [
    {
      "type": "RELATES_TO",
      "weight": 0.9
    },
    {
      "type": "RELATES_TO",
      "weight": 0.85
    }
  ],
  "hops": 2
}
```

### Response (200 OK) - No Path
```json
{
  "found": false,
  "path": null,
  "relationships": null,
  "hops": null
}
```

### Examples

#### Find Shortest Path
```bash
curl -X POST "http://localhost:8000/api/v1/graph/viz/shortest-path" \
  -H "Content-Type: application/json" \
  -d '{
    "source_entity": "LangGraph",
    "target_entity": "Neo4j"
  }'
```

#### With Custom Max Hops
```bash
curl -X POST "http://localhost:8000/api/v1/graph/viz/shortest-path" \
  -H "Content-Type: application/json" \
  -d '{
    "source_entity": "Docling",
    "target_entity": "Qdrant",
    "max_hops": 3
  }'
```

---

## Error Responses

### 400 Bad Request
Invalid input (validation errors)
```json
{
  "detail": [
    {
      "loc": ["body", "max_hops"],
      "msg": "ensure this value is less than or equal to 5",
      "type": "value_error.number.not_le"
    }
  ]
}
```

### 500 Internal Server Error
Query execution failed
```json
{
  "detail": "Multi-hop query failed: Neo4j connection error"
}
```

---

## Performance Tips

1. **Limit Hops:**
   - Keep `max_hops <= 3` for large graphs
   - Higher hops increase query time exponentially

2. **Use Relationship Filters:**
   - Filter by specific relationship types to reduce search space
   - Example: `["RELATES_TO"]` instead of all relationship types

3. **Disable Path Tracking:**
   - Set `include_paths: false` (default) for better performance
   - Only enable when paths are needed for visualization

4. **Index Optimization:**
   - Ensure `entity_name` is indexed in Neo4j:
     ```cypher
     CREATE INDEX entity_name_idx IF NOT EXISTS FOR (n:base) ON (n.entity_name)
     ```

---

## Use Cases

### 1. Entity Exploration
Find all related concepts within 2 hops:
```json
{
  "entity_id": "Machine Learning",
  "max_hops": 2
}
```

### 2. Relationship Discovery
Discover how two concepts are connected:
```json
{
  "source_entity": "RAG",
  "target_entity": "LLM"
}
```

### 3. Knowledge Graph Visualization
Get subgraph for interactive exploration:
```json
{
  "entity_id": "Knowledge Graph",
  "max_hops": 3,
  "include_paths": true
}
```

### 4. Path Analysis
Find all paths between entities:
```json
{
  "entity_id": "Source",
  "max_hops": 4,
  "include_paths": true
}
```

---

## Integration with Frontend

### React Example (Multi-Hop)
```typescript
const fetchMultiHop = async (entityId: string, maxHops: number = 2) => {
  const response = await fetch('/api/v1/graph/viz/multi-hop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      entity_id: entityId,
      max_hops: maxHops,
      include_paths: false,
    }),
  });

  const data = await response.json();
  return {
    nodes: data.nodes,
    edges: data.edges,
  };
};
```

### React Example (Shortest Path)
```typescript
const fetchShortestPath = async (source: string, target: string) => {
  const response = await fetch('/api/v1/graph/viz/shortest-path', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_entity: source,
      target_entity: target,
      max_hops: 5,
    }),
  });

  const data = await response.json();
  if (data.found) {
    return {
      path: data.path,
      relationships: data.relationships,
      hops: data.hops,
    };
  }
  return null;
};
```

---

## Testing

### Manual Testing (Swagger UI)
1. Start API: `uvicorn src.api.main:app --reload`
2. Open: `http://localhost:8000/docs`
3. Navigate to "graph-visualization" section
4. Test endpoints with sample data

### Unit Testing
```python
# tests/unit/api/test_multi_hop_api.py

def test_multi_hop_request_validation():
    """Test request validation."""
    # Valid request
    request = MultiHopRequest(entity_id="test", max_hops=2)
    assert request.max_hops == 2

    # Invalid max_hops (too high)
    with pytest.raises(ValidationError):
        MultiHopRequest(entity_id="test", max_hops=10)

def test_shortest_path_response():
    """Test response structure."""
    response = ShortestPathResponse(
        found=True,
        path=["A", "B", "C"],
        relationships=[{"type": "RELATES_TO", "weight": 0.9}],
        hops=2
    )
    assert response.found is True
    assert len(response.path) == 3
```

---

## Limitations

1. **Node Limit:** Multi-hop queries limited to 100 nodes
2. **Hop Limits:**
   - Multi-hop: Maximum 5 hops
   - Shortest path: Maximum 10 hops
3. **Relationship Types:** Only `RELATES_TO` relationships traversed
4. **Performance:** Large graphs may require longer query times

---

## Related Endpoints

- **GET** `/api/v1/graph/viz/visualize/{entity_id}` - Entity neighborhood
- **POST** `/api/v1/graph/viz/query-subgraph` - Query-specific subgraph
- **GET** `/api/v1/graph/viz/statistics` - Graph statistics

---

## OpenAPI Documentation

Full API specification available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## Support

For issues or questions:
- **GitHub Issues:** https://github.com/klapom/aegis-rag/issues
- **Documentation:** `docs/api/`
- **Sprint Documentation:** `SPRINT_34_FEATURE_34.5_MULTI_HOP_API.md`
