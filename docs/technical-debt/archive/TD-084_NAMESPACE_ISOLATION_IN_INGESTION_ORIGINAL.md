# TD-084: Namespace Isolation in Document Ingestion Pipeline

**Status:** Open
**Priority:** 🔴 **CRITICAL** - Multi-Tenant Data Leak
**Effort:** 13 SP
**Sprint:** 76 (Required for RAGAS isolation)
**Created:** 2025-01-05
**Root Cause:** Sprint 51 added namespace concept but never integrated into ingestion

---

## Problem

**CRITICAL BUG:** All ingested documents are stored in `namespace_id="default"` regardless of intended isolation.

This breaks multi-tenant separation completely!

### Current Behavior (BROKEN)

```python
# src/components/ingestion/nodes/graph_extraction.py:291
relations_created = await lightrag._store_relations_to_neo4j(
    relations=relations,
    chunk_id=chunk_id,
    namespace_id="default",  # ❌ HARDCODED! All docs go to "default"!
)
```

**Impact:**
- ❌ RAGAS evaluation domain gets mixed with production docs
- ❌ Project-specific docs contaminate other projects
- ❌ Test data pollutes production namespace
- ❌ No true multi-tenant isolation

### Evidence

1. **IngestionState has NO namespace field:**
   ```python
   # src/components/ingestion/ingestion_state.py
   class IngestionState(TypedDict, total=False):
       document_path: str
       document_id: str
       # ... NO namespace_id field!
   ```

2. **Upload endpoints don't accept namespace:**
   ```python
   # src/api/v1/admin_indexing.py
   @router.post("/indexing/upload")
   async def upload_files(files: list[UploadFile]):
       # ❌ No namespace_id parameter!
   ```

3. **Frontend has no namespace selector:**
   - AdminIndexingPage.tsx has NO namespace UI
   - NamespaceSelector exists but is ONLY used in Chat/Search

---

## Impact Analysis

### Affected Components

| Component | Impact | Severity |
|-----------|--------|----------|
| **Graph Extraction** | All entities/relations → "default" | 🔴 Critical |
| **Qdrant Indexing** | All chunks → "default" collection | 🔴 Critical |
| **RAGAS Evaluation** | Cannot isolate test docs from prod | 🔴 Critical |
| **Multi-Project Support** | Projects share same namespace | 🔴 Critical |
| **Neo4j Storage** | No namespace filtering possible | 🔴 Critical |

### Real-World Failures

**Sprint 75 RAGAS E2E User Journey:**
```
Step 1: Create domain "ragas_eval_domain" ✓
Step 2: Configure RAG settings ✓
Step 3: Ingest AEGIS docs → ❌ Goes to "default" namespace!
Step 4: RAGAS evaluation → ❌ Gets polluted by other docs!
```

**Result:** Context Precision/Recall = 0.0 (wrong documents retrieved)

---

## Root Cause

**Sprint 42** introduced namespace concept for **retrieval filtering only**.
**Sprint 51** hardcoded `namespace_id="default"` in graph extraction.
**Sprint 45-75** built features on top without namespace awareness.

**Nobody connected ingestion to namespaces!**

---

## Solution Design

### Required Changes

#### 1. **IngestionState - Add Namespace Field (2 SP)**

```python
# src/components/ingestion/ingestion_state.py
class IngestionState(TypedDict, total=False):
    # ============================================================
    # INPUT FIELDS (set by caller before pipeline starts)
    # ============================================================
    document_path: str
    document_id: str
    namespace_id: str  # ✅ NEW: Multi-tenant isolation (default: "default")
    domain_id: str | None  # Optional DSPy domain for extraction prompts
    # ...
```

#### 2. **Embedding Node - Use Namespace (2 SP)**

```python
# src/components/ingestion/nodes/embedding_node.py
async def embedding_node(state: IngestionState) -> IngestionState:
    namespace_id = state.get("namespace_id", "default")

    # Add namespace to Qdrant point metadata
    points = []
    for idx, chunk in enumerate(chunks):
        point = PointStruct(
            id=chunk_id,
            vector=embedding,
            payload={
                "namespace_id": namespace_id,  # ✅ Include namespace!
                "document_id": state["document_id"],
                # ...
            }
        )
        points.append(point)
```

#### 3. **Graph Extraction - Use Namespace (2 SP)**

```python
# src/components/ingestion/nodes/graph_extraction.py
async def graph_extraction_node(state: IngestionState) -> IngestionState:
    namespace_id = state.get("namespace_id", "default")

    # Line 135: Pass namespace to LightRAG
    graph_stats = await lightrag.insert_prechunked_documents(
        chunks=prechunked_docs,
        document_id=state["document_id"],
        document_path=state["document_path"],
        namespace_id=namespace_id,  # ✅ Use state namespace!
    )

    # Line 291: Use namespace for relations
    relations_created = await lightrag._store_relations_to_neo4j(
        relations=relations,
        chunk_id=chunk_id,
        namespace_id=namespace_id,  # ✅ FIXED!
    )
```

#### 4. **Backend API - Accept Namespace (3 SP)**

```python
# src/api/v1/admin_indexing.py

class AddDocumentsRequest(BaseModel):
    file_paths: list[str]
    namespace_id: str = Field(default="default", description="Multi-tenant namespace")
    domain_id: str | None = Field(default=None, description="Optional DSPy domain")
    # ...

@router.post("/indexing/add")
async def add_documents_endpoint(request: AddDocumentsRequest):
    # Pass namespace to ingestion pipeline
    state = IngestionState(
        document_path=file_path,
        document_id=doc_id,
        namespace_id=request.namespace_id,  # ✅ From request!
        domain_id=request.domain_id,
        # ...
    )
```

#### 5. **Frontend UI - Namespace Selector (4 SP)**

```tsx
// frontend/src/pages/admin/AdminIndexingPage.tsx
import { NamespaceSelector } from '../../components/search/NamespaceSelector';

export function AdminIndexingPage() {
  const [selectedNamespace, setSelectedNamespace] = useState<string>('default');
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);

  return (
    <>
      {/* Add Namespace Selector before file selection */}
      <div className="mb-4">
        <label className="text-sm font-medium text-gray-700 mb-2 block">
          Target Namespace
        </label>
        <NamespaceSelector
          selectedNamespaces={[selectedNamespace]}
          onSelectionChange={(ns) => setSelectedNamespace(ns[0])}
          compact={false}
        />
      </div>

      {/* Existing file upload UI */}
      {/* ... */}
    </>
  );
}
```

---

## Testing Strategy

### Unit Tests (2 SP)
- IngestionState with namespace_id
- Embedding node adds namespace to Qdrant payload
- Graph extraction uses correct namespace

### Integration Tests (3 SP)
- Upload to custom namespace → verify Qdrant has namespace metadata
- Query with namespace filter → only returns docs from that namespace
- Multi-namespace ingestion → verify isolation

### E2E Tests (2 SP)
- RAGAS workflow with `ragas_eval_domain` namespace
- Context Precision/Recall > 0.8 (proves isolation works)

---

## Acceptance Criteria

1. ✅ IngestionState has `namespace_id` field
2. ✅ All ingestion nodes use `state["namespace_id"]`
3. ✅ Backend APIs accept `namespace_id` parameter
4. ✅ Frontend has namespace selector in upload UI
5. ✅ Qdrant points have `namespace_id` in payload
6. ✅ Neo4j entities/relations tagged with namespace
7. ✅ Tests verify complete namespace isolation
8. ✅ RAGAS evaluation works with custom namespace

---

## Migration Plan

### Backward Compatibility

**Existing documents in "default" namespace:**
- ✅ No migration needed (already in "default")
- ✅ New API defaults to `namespace_id="default"`
- ✅ Existing behavior preserved

### Deployment

1. **Phase 1:** Backend changes (API + ingestion)
2. **Phase 2:** Frontend UI updates
3. **Phase 3:** Documentation + E2E tests

---

## Related Issues

- **Sprint 75:** RAGAS evaluation requires namespace isolation
- **TD-085:** DSPy domain prompts not used in extraction
- **Sprint 42:** Namespace filtering in retrieval (partial solution)
- **Sprint 51:** Hardcoded "default" namespace introduced

---

## References

- `src/components/ingestion/ingestion_state.py` - State definition
- `src/components/ingestion/nodes/graph_extraction.py:291` - Hardcoded namespace
- `src/components/ingestion/nodes/embedding_node.py` - Qdrant indexing
- `frontend/src/components/search/NamespaceSelector.tsx` - Existing UI component
- `docs/USER_JOURNEY_E2E.md` - RAGAS workflow (Sprint 75)
