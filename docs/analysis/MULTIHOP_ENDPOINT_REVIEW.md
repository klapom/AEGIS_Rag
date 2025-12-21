# Multi-Hop Endpoint Review (TD-069)

**Sprint:** 60
**Feature:** 60.4
**Story Points:** 3
**Review Date:** 2025-12-21
**Status:** ✅ COMPLETE

---

## Executive Summary

**Status:** 🔴 **DEPRECATED - RECOMMEND REMOVAL**

The Multi-Hop Query endpoints (`/api/v1/graph/viz/multi-hop` and `/api/v1/graph/viz/shortest-path`) were implemented in **Sprint 34 Feature 34.5** but **never integrated into the frontend**. Both endpoints were marked `DEPRECATED` on **2025-12-07** after analysis revealed zero usage.

**Recommendation:** **Remove in Sprint 61** to reduce API surface area and maintenance burden.

---

## Implementation Status

### 1. Backend Implementation

**File:** `src/api/routers/graph_viz.py`

**Endpoints Implemented:**

| Endpoint | Lines | Status | Sprint |
|----------|-------|--------|--------|
| `POST /api/v1/graph/viz/multi-hop` | 752-884 | DEPRECATED | 34.5 |
| `POST /api/v1/graph/viz/shortest-path` | 889-960 | DEPRECATED | 34.5 |

**Implementation Quality:**
- ✅ **Fully functional** - Production-ready Cypher queries
- ✅ **Comprehensive models** - Pydantic request/response models (lines 160-224)
- ✅ **Error handling** - HTTPException with logging
- ✅ **Performance limits** - max_hops (1-5 for multi-hop, 1-10 for shortest path)
- ✅ **Documentation** - Detailed docstrings with Sprint references

### 2. Test Coverage

**Integration Tests:**
- **File:** `tests/integration/components/test_multi_hop_query.py` (298 lines)
- **Sprint:** 27 Feature 27.2
- **Scope:** Multi-hop QUERY PROCESSING (decomposition, aggregation, entity linking)
- **Coverage:** Mock-based tests, not direct API endpoint tests

**Gap Identified:**
- ❌ **No API endpoint tests** - Integration tests exist for query logic, but NOT for the REST API endpoints implemented in Sprint 34

### 3. Frontend Integration

**Search Results:**
- ❌ **No frontend usage** - Zero references to `multihop`, `multi-hop`, or `multi_hop` in `frontend/src/`

**UI Integration:**
- Graph visualization in frontend uses **client-side filtering** and `/query-subgraph` endpoint
- Multi-hop traversal never integrated into UI components

---

## Feature Capabilities

### Multi-Hop Traversal (`/multi-hop`)

**Purpose:** Find all entities connected within N hops via `RELATES_TO` relationships

**Request Model:**
```python
class MultiHopRequest(BaseModel):
    entity_id: str              # Starting entity ID or name
    max_hops: int = 2           # Maximum hops (1-5)
    relationship_types: list[str] | None  # Filter by rel types
    include_paths: bool = False # Include full path information
```

**Response Model:**
```python
class MultiHopResponse(BaseModel):
    start_entity: str
    max_hops: int
    nodes: list[GraphNode]      # Connected entities with hop distance
    edges: list[GraphEdge]      # Relationships
    paths: list[list[str]] | None  # Full paths (optional)
```

**Cypher Query:**
```cypher
MATCH path = (start:base {entity_name: $entity_id})-[r:RELATES_TO*1..N]-(connected:base)
WITH DISTINCT connected, path, length(path) as hops
RETURN connected, hops, relationships(path), nodes(path)
ORDER BY hops, entity_name
LIMIT 100
```

**Performance:**
- Variable-length path matching: `[:RELATES_TO*1..N]`
- Max 100 nodes returned
- Separate query for edges between found nodes

### Shortest Path (`/shortest-path`)

**Purpose:** Find shortest path between two entities using Neo4j's `shortestPath` algorithm

**Request Model:**
```python
class ShortestPathRequest(BaseModel):
    source_entity: str  # Source entity ID or name
    target_entity: str  # Target entity ID or name
    max_hops: int = 5   # Maximum hops (1-10)
```

**Response Model:**
```python
class ShortestPathResponse(BaseModel):
    found: bool
    path: list[str] | None              # Node names in path
    relationships: list[PathRelationship] | None
    hops: int | None                    # Path length
```

**Cypher Query:**
```cypher
MATCH (start:base {entity_name: $source}), (end:base {entity_name: $target})
MATCH path = shortestPath((start)-[:RELATES_TO*1..N]-(end))
RETURN nodes(path), relationships(path), length(path)
```

---

## Usage Analysis

### Backend Endpoints Called

Analysis of frontend API calls in `frontend/src/`:

**Graph Visualization Endpoints Used:**
- ✅ `POST /api/v1/graph/viz/export` - Graph export (JSON, GraphML, Cytoscape)
- ✅ `POST /api/v1/graph/viz/query-subgraph` - Subgraph for query results (Sprint 29)
- ✅ `GET /api/v1/graph/viz/statistics` - Graph statistics (Sprint 29)
- ✅ `POST /api/v1/graph/viz/node-documents` - Entity documents (Sprint 29)
- ✅ `GET /api/v1/graph/viz/communities/{id}/documents` - Community docs (Sprint 29)

**Graph Visualization Endpoints NOT Used:**
- ❌ `POST /api/v1/graph/viz/multi-hop` - Multi-hop traversal (Sprint 34)
- ❌ `POST /api/v1/graph/viz/shortest-path` - Shortest path (Sprint 34)
- ❌ `GET /api/v1/graph/viz/export/formats` - DEPRECATED (marked 2025-12-07)
- ❌ `POST /api/v1/graph/viz/filter` - DEPRECATED (marked 2025-12-07)
- ❌ `POST /api/v1/graph/viz/communities/highlight` - DEPRECATED (marked 2025-12-07)

### Deprecation Timeline

**Sprint 34 (2024):**
- Implemented Multi-Hop and Shortest Path endpoints (Feature 34.5)
- Documentation created: `docs/api/MULTI_HOP_ENDPOINTS.md`

**2025-12-07:**
- Analysis identified 5 unused endpoints in `graph_viz.py`
- Added DEPRECATED comments with reason: "not called from frontend"
- Recommendation: "Consider removal in next major version"

**Sprint 60 (2025-12-21):**
- **This review confirms zero frontend usage**
- Endpoints remain fully functional but unused for 12+ months

---

## Architecture Analysis

### Why Multi-Hop Was Not Integrated

**Frontend Graph Interaction Pattern:**
1. **Query-Based Subgraph Extraction** (`/query-subgraph`)
   - Extract 1-hop neighborhood of entities from query results
   - Render subgraph in React vis-network component
   - Client-side filtering and interaction

2. **Client-Side Graph Traversal**
   - Vis-network provides interactive graph exploration
   - Users can click nodes to expand neighbors
   - No need for server-side multi-hop traversal

**Alternative Use Cases:**
- Multi-hop could be useful for **backend graph reasoning** (agents)
- Shortest path useful for **entity relationship discovery**
- Not needed for **frontend visualization** (handled client-side)

### Current Graph Reasoning Approach

**LangGraph Graph Agent** (`src/agents/graph_query.py`):
- Uses **LightRAG** for graph reasoning
- Local queries: Entity neighborhood (1-2 hops)
- Global queries: Community-based retrieval
- **Does NOT use Multi-Hop API endpoints**

---

## Recommendations

### 1. Remove Multi-Hop Endpoints ✅ RECOMMENDED

**Rationale:**
- Zero frontend usage for 12+ months
- Graph traversal handled client-side
- Backend agents use LightRAG, not REST API
- Reduces API surface area and maintenance burden

**Sprint 61 Actions:**
1. Remove endpoints from `src/api/routers/graph_viz.py`:
   - `POST /multi-hop` (lines 752-884)
   - `POST /shortest-path` (lines 889-960)
2. Remove models (lines 160-224):
   - `MultiHopRequest`, `MultiHopResponse`
   - `ShortestPathRequest`, `ShortestPathResponse`
   - `GraphNode`, `GraphEdge`, `PathRelationship`
3. Archive documentation:
   - Move `docs/api/MULTI_HOP_ENDPOINTS.md` → `docs/archive/`
   - Move `docs/sprints/SPRINT_34_FEATURE_34.5_MULTI_HOP_API.md` → `docs/archive/`
4. Keep integration tests:
   - `tests/integration/components/test_multi_hop_query.py` tests query decomposition logic
   - NOT testing the deprecated API endpoints
   - Still relevant for multi-hop reasoning capabilities

**Benefits:**
- Reduced codebase complexity
- Fewer endpoints to document and maintain
- Clear API surface (only actively used endpoints)

### 2. Alternative: Keep for Future Agent Use ⚠️ NOT RECOMMENDED

**Rationale:**
- Multi-hop traversal could be useful for future agentic reasoning
- Could expose via internal API for agents (not public REST)

**Concerns:**
- YAGNI (You Aren't Gonna Need It) - No current use case
- Can re-implement if needed (Cypher queries are simple)
- Better to remove now, add later if required

### 3. Alternative: Migrate to Internal Service ⚠️ OVERKILL

**Rationale:**
- Convert to internal graph service used by agents
- Remove from public REST API

**Concerns:**
- Over-engineering for unused functionality
- Agents use LightRAG directly, don't need abstraction layer

---

## Implementation Gaps

### 1. API Endpoint Tests

**Gap:** Integration tests exist for multi-hop query LOGIC, not REST API endpoints

**If Keeping Endpoints (NOT RECOMMENDED):**
- Add API tests to `tests/integration/api/test_graph_viz.py`:
  ```python
  async def test_multi_hop_endpoint():
      response = await client.post("/api/v1/graph/viz/multi-hop", json={
          "entity_id": "test_entity",
          "max_hops": 2
      })
      assert response.status_code == 200
      assert "nodes" in response.json()
  ```

### 2. OpenAPI Documentation

**Gap:** Endpoints exist in OpenAPI spec but marked deprecated

**If Removing (RECOMMENDED):**
- OpenAPI will auto-update when endpoints removed
- No action needed

---

## Migration Path

### Sprint 61: Removal Plan

**Step 1: Verify No Internal Usage**
```bash
# Search codebase for multi-hop API calls
grep -r "multi-hop\|multihop" src/ tests/ --exclude-dir=archive
```

**Expected:** Only find:
- `src/api/routers/graph_viz.py` (the implementation)
- `tests/integration/components/test_multi_hop_query.py` (query logic tests)
- Documentation files

**Step 2: Remove Code**
1. Delete endpoints and models from `graph_viz.py`
2. Run test suite: `pytest tests/`
3. Verify OpenAPI docs: `curl http://localhost:8000/docs`

**Step 3: Archive Documentation**
```bash
mv docs/api/MULTI_HOP_ENDPOINTS.md docs/archive/
mv docs/sprints/SPRINT_34_FEATURE_34.5_MULTI_HOP_API.md docs/archive/
```

**Step 4: Update TD-069**
- Mark TD-069 as RESOLVED
- Document decision: "Removed unused endpoints per Sprint 60 analysis"

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Frontend needs multi-hop later | Low | Medium | Re-implement from archived code (simple Cypher) |
| Agents need multi-hop traversal | Low | Low | Agents use LightRAG, not REST API |
| External API consumers | None | None | Endpoints never documented as public API |
| Breaking change | None | None | Endpoints unused, safe to remove |

**Overall Risk:** ✅ **LOW** - Safe to remove

---

## Related Technical Debt

### Other Deprecated Endpoints (graph_viz.py)

**Also Identified 2025-12-07:**
1. `GET /export/formats` (line 340) - Export formats hardcoded in frontend
2. `POST /filter` (line 367) - Client-side filtering preferred
3. `POST /communities/highlight` (line 424) - Client-side highlighting

**Sprint 61 Recommendation:** Remove all 5 deprecated endpoints together

---

## Documentation

### Existing Documentation

1. **API Docs:** `docs/api/MULTI_HOP_ENDPOINTS.md` (382 lines)
   - Comprehensive endpoint documentation
   - Request/response examples
   - Cypher query details
   - **Action:** Archive to `docs/archive/`

2. **Implementation Docs:** `docs/sprints/SPRINT_34_FEATURE_34.5_MULTI_HOP_API.md` (476 lines)
   - Sprint 34 implementation details
   - Design decisions and trade-offs
   - **Action:** Archive to `docs/archive/`

3. **Test Report:** Embedded in `test_multi_hop_query.py`
   - Tests query decomposition, not API endpoints
   - **Action:** Keep (tests query logic, not deprecated API)

---

## Conclusion

**Status:** 🔴 **DEPRECATED - RECOMMEND REMOVAL**

The Multi-Hop Query endpoints represent **well-implemented but unused functionality**. Despite being production-ready with comprehensive documentation, the endpoints have **zero frontend integration** and **zero backend usage** after 12+ months.

**Sprint 61 Action:**
- ✅ **Remove both endpoints** (`/multi-hop`, `/shortest-path`)
- ✅ **Archive documentation** to preserve implementation knowledge
- ✅ **Update TD-069 status** to RESOLVED

**Rationale:**
- Frontend uses client-side graph interaction
- Backend agents use LightRAG directly
- Simplifies API surface and reduces maintenance burden
- Can re-implement from archived code if future need arises

---

**Review Completed By:** Claude Code (Sprint 60 Documentation Agent)
**Review Date:** 2025-12-21
**TD-069 Status:** ✅ COMPLETE - Ready for Sprint 61 removal
