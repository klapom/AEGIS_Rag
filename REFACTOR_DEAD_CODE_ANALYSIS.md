# Dead Code Analysis Report

**Generated:** 2025-12-07
**Tool:** Vulture (Python), Manual Analysis (TypeScript)
**Confidence Level:** 60%+ for functions/classes, 80%+ for variables

---

## Executive Summary

| Category | Count | Action Required |
|----------|-------|-----------------|
| Unused Functions/Methods/Classes | 269 | Review & Remove |
| Unused Variables | ~50 | Minor cleanup |
| Backend Endpoints not in Frontend | 18 | Already marked DEPRECATED |
| Potentially Removable Modules | 8 | Deep review needed |

---

## 1. Files with Most Unused Code (Top 20)

| File | Unused Items | Priority | Notes |
|------|--------------|----------|-------|
| `src/api/v1/admin.py` | 21 | P2 | Many ingestion job endpoints - verify frontend usage |
| `src/components/graph_rag/query_templates.py` | 19 | P1 | **Entire class unused** - template methods never called |
| `src/components/graph_rag/temporal_query_builder.py` | 12 | P1 | **Likely removable** - temporal features not used |
| `src/components/memory/monitoring.py` | 9 | P2 | Monitoring endpoints - check if Prometheus uses |
| `src/components/ingestion/progress_manager.py` | 9 | P3 | Internal methods - may be called dynamically |
| `src/api/routers/graph_viz.py` | 9 | P1 | Already marked DEPRECATED |
| `src/api/v1/chat.py` | 8 | P2 | Some planned for Sprint 38 |
| `src/components/graph_rag/evolution_tracker.py` | 7 | P1 | **Likely removable** - not integrated |
| `src/components/graph_rag/community_detector.py` | 7 | P2 | Community features - partial use |
| `src/api/v1/memory.py` | 6 | P1 | **Entire router unused** from frontend |
| `src/core/exceptions.py` | 5 | P3 | Custom exceptions - keep for error handling |
| `src/core/chunk.py` | 5 | P3 | Chunking utilities - verify usage |
| `src/components/mcp/connection_manager.py` | 5 | P1 | **MCP not integrated** - review MCP status |
| `src/components/graph_rag/version_manager.py` | 5 | P1 | **Likely removable** - versioning not used |
| `src/components/graph_rag/query_cache.py` | 5 | P2 | Caching - may be used internally |
| `src/api/v1/retrieval.py` | 5 | P1 | Already marked DEPRECATED |

---

## 2. Potentially Removable Modules (P1 Priority)

These modules have **most/all exports unused** and may be entirely removable:

### 2.1 `src/components/graph_rag/query_templates.py`

**Status:** Entire `GraphQueryTemplates` class unused
**Confidence:** 60%
**Lines of Code:** ~500

```
Unused methods (all 19):
- entity_lookup
- entity_neighbors
- shortest_path
- entity_relationships
- subgraph_extraction
- entity_by_type
- relationship_by_type
- entity_search
- entity_statistics
- relationship_statistics
- orphan_entities
- highly_connected
- recent_entities
- entity_evolution
- entity_similarity
- relationship_path
- entity_degree_distribution
- connected_components
```

**Recommendation:** REMOVE - query_builder.py is used instead

---

### 2.2 `src/components/graph_rag/temporal_query_builder.py`

**Status:** 12 unused methods, temporal features PLANNED for Sprint 39
**Confidence:** 60%
**Lines of Code:** ~350

```
Unused methods:
- as_of, between, valid_during, transaction_during
- current, with_history, at_valid_time, at_transaction_time
- return_clause, skip, set_param
- get_temporal_query_builder (singleton)
```

**Recommendation:** KEEP - Bi-Temporal Queries aktiviert in Sprint 39 (nach Auth)

---

### 2.3 `src/components/graph_rag/evolution_tracker.py`

**Status:** 7 unused methods, PLANNED for Sprint 39 (requires Auth for `changed_by`)
**Confidence:** 60%
**Lines of Code:** ~450

```
Unused methods:
- track_changes
- get_change_log
- get_change_statistics
- detect_drift
- get_stable_entities
- get_active_entities
- get_evolution_tracker (singleton)
```

**Recommendation:** KEEP - Entity Change Tracking aktiviert in Sprint 39 (requires Auth)

---

### 2.4 `src/components/graph_rag/version_manager.py`

**Status:** 5 unused methods, PLANNED for Sprint 39 (requires Auth for audit trail)
**Confidence:** 60%
**Lines of Code:** ~520

```
Unused methods:
- get_version_at
- compare_versions
- get_evolution
- revert_to_version
- get_version_manager (singleton)
```

**Recommendation:** KEEP - Entity Versioning aktiviert in Sprint 39 (requires Auth)

---

### 2.5 `src/api/v1/memory.py`

**Status:** 6 unused endpoints, no frontend calls
**Confidence:** 60%
**Lines of Code:** ~700

```
Unused endpoints:
- POST /memory/search (unified_memory_search)
- POST /memory/temporal/point-in-time (point_in_time_query)
- GET /memory/session/{session_id} (get_session_context)
- POST /memory/consolidate (trigger_consolidation)
- GET /memory/stats (get_memory_stats)
- DELETE /memory/session/{session_id} (delete_session)
```

**Recommendation:** Keep but add to TD-057 (Memory API Frontend Integration)

---

### 2.6 `src/components/mcp/` (Entire Directory)

**Status:** MCP client PLANNED for Sprint 40
**Files affected:**
- `client.py` - 5 unused
- `connection_manager.py` - 5 unused
- `client_stub.py` - 4 unused

**Recommendation:** KEEP - MCP Integration geplant für Sprint 40 (TD-055)

---

## 3. Backend Endpoints vs Frontend Usage

### 3.1 Endpoints Called from Frontend (21 endpoints)

```
/api/v1/chat/stream                    ✅ Used (main chat)
/api/v1/chat/sessions                  ✅ Used (session list)
/api/v1/chat/sessions/{id}             ✅ Used (session details)
/api/v1/chat/history/{session_id}      ✅ Used (conversation history)
/api/v1/admin/stats                    ✅ Used (system stats)
/api/v1/admin/costs/stats              ✅ Used (cost dashboard)
/api/v1/admin/pipeline/config          ✅ Used (worker config)
/api/v1/admin/indexing/scan-directory  ✅ Used (file browser)
/api/v1/admin/indexing/upload          ✅ Used (file upload)
/api/v1/admin/indexing/add             ✅ Used (start indexing)
/api/v1/admin/indexing/progress/{id}   ✅ Used (SSE progress)
/api/v1/admin/reindex                  ✅ Used (reindex button)
/api/v1/admin/llm/config               ✅ Used (LLM settings)
/api/v1/admin/llm/models               ✅ Used (model list)
/api/v1/graph/viz/statistics           ✅ Used (graph stats)
/api/v1/graph/viz/export               ✅ Used (graph export)
/api/v1/graph/viz/query-subgraph       ✅ Used (subgraph query)
/api/v1/graph/viz/node-documents       ✅ Used (entity documents)
/api/v1/graph/viz/communities          ✅ Used (community list)
/api/v1/graph/viz/communities/{id}     ✅ Used (community details)
/api/v1/graph/viz/communities/{id}/documents ✅ Used (community docs)
```

### 3.2 Endpoints NOT Called from Frontend (Already DEPRECATED)

```
DEPRECATED (Sprint 38 planned):
- POST /api/v1/chat/sessions/{id}/archive  ❌ Planned Sprint 38
- POST /api/v1/chat/search                 ❌ Planned Sprint 38
- POST /api/v1/auth/login                  ❌ Planned Sprint 38
- GET /api/v1/auth/me                      ❌ Planned Sprint 38

DEPRECATED (Remove recommended):
- GET /api/v1/graph/viz/export/formats     ❌ Hardcoded in frontend
- POST /api/v1/graph/viz/filter            ❌ Client-side filtering
- POST /api/v1/graph/viz/communities/highlight ❌ Client-side CSS
- POST /api/v1/graph/viz/multi-hop         ❌ Not integrated (Sprint 38?)
- POST /api/v1/graph/viz/shortest-path     ❌ Not integrated (Sprint 38?)

UNUSED (Memory API - keep for future):
- POST /api/v1/memory/search               ❌ Memory UI not built
- POST /api/v1/memory/temporal/point-in-time ❌ Temporal UI not built
- GET /api/v1/memory/session/{id}          ❌ Memory UI not built
- POST /api/v1/memory/consolidate          ❌ Memory UI not built
- GET /api/v1/memory/stats                 ❌ Memory UI not built
- DELETE /api/v1/memory/session/{id}       ❌ Memory UI not built

UNUSED (Retrieval API - already deprecated):
- POST /api/v1/retrieval/ingest            ❌ Use admin/indexing
- POST /api/v1/retrieval/upload            ❌ Use admin/indexing/upload
- GET /api/v1/retrieval/formats            ❌ Duplicate
- POST /api/v1/retrieval/prepare-bm25      ❌ Internal only
```

---

## 4. Unused Variables (Context Manager Exceptions)

These are false positives from context manager `__aexit__` signatures:

```python
# Pattern: async def __aexit__(self, exc_type, exc_val, exc_tb)
# These ARE required by Python spec, NOT dead code

src/components/graph_rag/neo4j_client.py:504
src/components/ingestion/docling_client.py:984
src/components/llm_proxy/dashscope_vlm.py:271
src/components/llm_proxy/ollama_vlm.py:205
```

**Recommendation:** Add to vulture whitelist, NOT dead code

---

## 5. Pydantic Model Fields (False Positives)

Vulture marks Pydantic model fields as unused because they're accessed dynamically:

```python
# Pattern: class FooModel(BaseModel):
#     field: str = Field(...)  # Marked "unused" but used via .model_dump()

src/api/models/cost_stats.py - limit_usd, spent_usd, etc.
src/api/models/pipeline_progress.py - entities_total, etc.
src/agents/state.py - result_count, vector_results_count, etc.
```

**Recommendation:** Add to vulture whitelist, NOT dead code

---

## 6. Recommended Actions

### Immediate (Sprint 38)

1. **Remove 3 deprecated graph_viz endpoints:**
   - `GET /export/formats`
   - `POST /filter`
   - `POST /communities/highlight`

2. **Integrate 2 graph_viz endpoints into GraphRAG:**
   - `POST /multi-hop` → Feature 38.4
   - `POST /shortest-path` → Feature 38.4

3. **Implement Authentication:**
   - `POST /auth/login` → Feature 38.1
   - `GET /auth/me` → Feature 38.1

### Sprint 39: Bi-Temporal Features aktivieren (nach Auth)

1. **Aktiviere Bi-Temporal Graph Features:**
   - `temporal_query_builder.py` - Temporal Queries
   - `evolution_tracker.py` - Entity Change Tracking
   - `version_manager.py` - Entity Versioning
   - **Requires:** Auth for `changed_by` audit trail

2. **Entferne 1 unused graph_rag Modul:**
   - `query_templates.py` (~500 LOC) - wird von query_builder.py ersetzt
   - **Total: ~500 LOC removal**

3. **Create TD-057: Memory API Frontend Integration**
   - Document 6 unused memory endpoints
   - Plan Memory Dashboard for future sprint

### Sprint 40: MCP Integration

1. **Aktiviere MCP Client (TD-055)**
   - `src/components/mcp/client.py`
   - `src/components/mcp/connection_manager.py`
   - External Tool Integration

### Long-term

1. **Review ingestion job API usage after Sprint 38**
2. **Set up automated dead code detection in CI (vulture)**

---

## 7. Vulture Whitelist (Create this file)

```python
# vulture_whitelist.py
# Add to pyproject.toml: [tool.vulture] paths = ["src/", "vulture_whitelist.py"]

# Context manager signatures (required by Python)
exc_type  # unused variable
exc_val   # unused variable
exc_tb    # unused variable

# Pydantic model fields (accessed dynamically)
model_config  # unused variable

# FastAPI router endpoints (called via HTTP, not Python)
login  # unused function
get_me  # unused function
# ... add all @router endpoints

# Enum members (used in conditionals)
VECTOR  # unused variable
GRAPH   # unused variable
MEMORY  # unused variable
```

---

## 8. Estimated Impact

| Action | Lines Removed | Sprint | Risk |
|--------|---------------|--------|------|
| Remove deprecated graph_viz endpoints | ~200 | 38 | Low |
| Remove query_templates.py | ~500 | 39 | Low |
| Remove retrieval.py (already deprecated) | ~700 | 38 | Low |
| Clean unused variables | ~50 | 38 | Very Low |
| **Total Safe Removal** | **~1,450 LOC** | | |

### Module Status Summary

| Module | LOC | Status | Sprint |
|--------|-----|--------|--------|
| `query_templates.py` | ~500 | REMOVE | 39 |
| `temporal_query_builder.py` | ~350 | KEEP - Bi-Temporal | 39 |
| `evolution_tracker.py` | ~450 | KEEP - Bi-Temporal | 39 |
| `version_manager.py` | ~520 | KEEP - Bi-Temporal | 39 |
| `src/components/mcp/*` | ~600 | KEEP - MCP | 40 |
| `src/api/v1/memory.py` | ~700 | KEEP - Memory UI | Future |
| `src/api/v1/retrieval.py` | ~700 | REMOVE - Deprecated | 38 |

---

## Appendix: Full Vulture Output

See: `vulture_full_output.txt` (run `poetry run vulture src/ --min-confidence 60 > vulture_full_output.txt`)
