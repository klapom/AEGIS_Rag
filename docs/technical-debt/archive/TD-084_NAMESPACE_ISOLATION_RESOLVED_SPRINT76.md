# TD-084: Namespace Isolation in Document Ingestion Pipeline

**Status:** ✅ **RESOLVED** in Sprint 76
**Priority:** 🔴 CRITICAL
**Resolution Date:** 2026-01-05
**Story Points Invested:** 13 SP
**Resolution Commits:**
- `188951f` - Backend implementation
- `0271e70` - Frontend implementation
- `790ca07` - Parameter propagation fix

---

## Original Problem

**CRITICAL BUG:** All ingested documents were stored in `namespace_id="default"` regardless of intended isolation, breaking multi-tenant separation completely.

### Impact
- ❌ RAGAS evaluation domain mixed with production docs
- ❌ Project-specific docs contaminated other projects
- ❌ Test data polluted production namespace
- ❌ No true multi-tenant isolation

---

## Resolution Summary

### Sprint 76 Implementation

**Feature 76.1 (TD-084): Namespace Isolation - Backend**

#### 1. IngestionState Extended
```python
# src/components/ingestion/ingestion_state.py
class IngestionState(TypedDict, total=False):
    namespace_id: str  # ✅ NEW: Multi-tenant isolation (default: "default")
    domain_id: str | None  # ✅ NEW: Optional DSPy domain
```

#### 2. Vector Embedding Node Updated
```python
# src/components/ingestion/nodes/vector_embedding.py:260-262
# Sprint 76 Feature 76.1 (TD-084): Multi-tenant namespace isolation
# Use namespace_id from state instead of hardcoded "default"
"namespace": state.get("namespace_id", "default"),
```

#### 3. Graph Extraction Node Updated
```python
# src/components/ingestion/nodes/graph_extraction.py:169-173
# Sprint 76 Features 76.1 & 76.2 (TD-084 & TD-085): Use namespace and domain from state
namespace_id = state.get("namespace_id", "default")
domain_id = state.get("domain_id")  # Optional

graph_stats = await lightrag.insert_prechunked_documents(
    chunks=prechunked_docs,
    document_id=state["document_id"],
    document_path=state["document_path"],
    namespace_id=namespace_id,  # ✅ Propagated from state
    domain_id=domain_id,
)
```

#### 4. Relations Storage Fixed
```python
# src/components/ingestion/nodes/graph_extraction.py:331
relations_created = await lightrag._store_relations_to_neo4j(
    relations=relations,
    chunk_id=chunk_id,
    namespace_id=namespace_id,  # ✅ Multi-tenant isolation from state
)
```

**Feature 76.1 (TD-084): Namespace Isolation - Frontend**

#### 5. Upload API Extended
```python
# src/api/v1/admin_indexing.py
class AddDocumentsRequest(BaseModel):
    file_paths: list[str]
    namespace_id: str = Field(default="default")  # ✅ NEW
    domain_id: str | None = Field(default=None)  # ✅ NEW
```

#### 6. Frontend UI Added
```tsx
// frontend/src/pages/admin/AdminIndexingPage.tsx
// ✅ Namespace selector integrated
// ✅ Domain selector integrated (TD-085)
```

---

## Verification

### Code Evidence (Sprint 76)

1. **Namespace propagation in graph_extraction.py:**
   ```bash
   $ grep "namespace_id.*state" src/components/ingestion/nodes/graph_extraction.py
   namespace_id = state.get("namespace_id", "default")  # Line 170
   namespace_id=namespace_id,  # Line 331
   ```

2. **Namespace in Qdrant payload:**
   ```bash
   $ grep "namespace.*state" src/components/ingestion/nodes/vector_embedding.py
   "namespace": state.get("namespace_id", "default"),  # Line 262
   ```

3. **LightRAG client signature:**
   ```bash
   $ grep "domain_id" src/components/graph_rag/lightrag/client.py
   Sprint 76 TD-085: Added domain_id for DSPy-optimized extraction prompts.  # Line 179
   ```

### Test Results
- ✅ Namespace isolation working in ingestion pipeline
- ✅ Qdrant points have correct namespace metadata
- ✅ Neo4j entities tagged with namespace
- ✅ Multi-tenant separation verified

---

## Lessons Learned

1. **Architecture Gaps Accumulate:** Sprint 42 introduced namespaces for retrieval, Sprint 51 hardcoded "default", Sprints 45-75 built features without namespace awareness.

2. **End-to-End Testing Critical:** Issue only discovered when trying RAGAS E2E workflow in Sprint 75.

3. **State Management:** IngestionState is central - all pipeline nodes must respect its fields.

4. **Quick Resolution When Planned:** 13 SP estimate, completed in 1 sprint with proper design.

---

## Related

- **TD-085:** DSPy Domain Prompts (resolved in same sprint)
- **Sprint 75:** RAGAS evaluation gap analysis
- **Sprint 42:** Original namespace concept (retrieval only)
- **Sprint 51:** Hardcoded "default" introduced

---

## Impact

**Before (Broken):**
- All docs → "default" namespace
- No multi-tenant isolation
- RAGAS evaluation impossible

**After (Fixed):**
- Docs go to specified namespace
- True multi-tenant separation
- RAGAS evaluation works with isolated namespace
- Project-specific ingestion supported

---

## References

- **Resolution Commits:** `188951f`, `0271e70`, `790ca07`
- **Sprint:** 76
- **Original TD:** [TD-084_NAMESPACE_ISOLATION_IN_INGESTION.md](../TD-084_NAMESPACE_ISOLATION_IN_INGESTION.md)
- **Code Changes:**
  - `src/components/ingestion/ingestion_state.py`
  - `src/components/ingestion/nodes/vector_embedding.py`
  - `src/components/ingestion/nodes/graph_extraction.py`
  - `src/api/v1/admin_indexing.py`
  - `frontend/src/pages/admin/AdminIndexingPage.tsx`
