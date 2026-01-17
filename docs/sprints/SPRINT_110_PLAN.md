# Sprint 110 Plan - E2E Test Completion (Groups 01-03, 13-16)

**Status:** 🔄 In Progress
**Target:** Complete remaining E2E test groups (Tool Execution + Enterprise)
**Sprint Points:** 65 SP (60 + 3 bug fix + 2 bug fix)
**Completed:** 5 SP (Feature 110.0 + 110.4)
**Estimated Duration:** 1-1.5 weeks

**Note:** Group 09 Long Context moved to Sprint 111 for dedicated focus

---

## Sprint Goals

0. **Bug Fix:** Complete Feature 110.0 - Admin Memory Search Endpoint (3 SP) ✅
1. **Bug Fix:** Feature 110.4 - Domain Training Model Selector (2 SP) 📝
2. Complete Groups 01-03: Tool Execution (20 SP)
3. Complete Groups 13-16: Enterprise Features (40 SP)
4. Achieve >80% pass rate per group
5. Total: 65 SP, ~60 tests

**Moved to Sprint 111:**
- ⏸️ Group 09: Long Context (10 SP) - see `SPRINT_111_PLAN.md`

---

## Feature Breakdown

### ✅ Feature 110.0: Admin Memory Search Endpoint (3 SP) - BUG FIX

**Status:** ✅ **COMPLETE**
**Priority:** 🔴 **CRITICAL** (Blocking Memory Management UI)
**Story Points:** 3 SP
**Effort:** 30 minutes
**Date Completed:** 2026-01-17

#### Problem

Sprint 72.3 "Memory Management UI" was marked as complete, but the backend endpoint was never implemented:

- ✅ Frontend UI created: `MemorySearchPanel.tsx`, `MemoryManagementPage.tsx`
- ✅ Documentation written: `docs/guides/MEMORY_MANAGEMENT_GUIDE.md`
- ❌ Backend endpoint **missing**: `/api/v1/admin/memory/search`

**User Impact:**
- Memory Management page search throws **HTTP 422 Error**
- Error: `{"error": "Field required", "loc": ["body", "query"]}`
- Frontend expects filter-only search (session_id, user_id, namespace)
- Existing `/api/v1/memory/search` requires semantic `query` field

#### Solution Implemented

**New Endpoint:** `POST /api/v1/admin/memory/search`

**File:** `src/api/v1/admin.py` (+172 lines)

**Features:**
- ✅ Filter-based search (no query required)
- ✅ Supports: `user_id`, `session_id`, `query` (optional), `namespace`
- ✅ Pagination: `offset`, `limit`
- ✅ Flattened results (not grouped by layer)
- ✅ Matches frontend TypeScript contract exactly

**API Contract:**
```typescript
// Request
{
  user_id?: string;
  session_id?: string;
  query?: string;       // ← Optional!
  namespace?: string;
  limit: number;        // Default: 20
  offset: number;       // Default: 0
}

// Response
{
  results: MemorySearchResult[];  // Flattened from all layers
  total_count: number;
  query: AdminMemorySearchRequest;
}
```

**Differences from `/api/v1/memory/search`:**
- Query is **optional** (filter-only search supported)
- Results are **flattened** (not grouped by layer)
- Designed for **admin debugging UI**

#### Files Changed

- `src/api/v1/admin.py` (+172 lines)
  - Added `AdminMemorySearchRequest` model
  - Added `AdminMemorySearchResult` model
  - Added `AdminMemorySearchResponse` model
  - Added `admin_memory_search()` endpoint handler

#### Success Criteria Met

- ✅ Endpoint matches frontend TypeScript contract
- ✅ Filter-only search works (no query required)
- ✅ Results are properly flattened from all layers
- ✅ Pagination works (offset/limit)
- ✅ Comprehensive error handling and logging

---

### ⏸️ Feature 110.1: Group 09 - Long Context (10 SP) - MOVED TO SPRINT 111

**Status:** ⏸️ **MOVED TO SPRINT 111**
**Reason:** User requested dedicated focus with Token Usage Chart feature
**See:** `SPRINT_111_PLAN.md` for full details

---

### ✅ Feature 110.4: Domain Training Model Selector (2 SP) - BUG FIX

**Status:** ✅ **COMPLETE**
**Priority:** 🟡 **MEDIUM** (UI Bug from Sprint 109)
**Story Points:** 2 SP
**Date Completed:** 2026-01-17

#### Problem

**Original Bug Report (Sprint 109.3B):**
> "Domain Training ==> 'New Domain' ==> Use default model ==> Kann kein Modell ausgewählt werden"

**Root Cause Analysis (2026-01-17):**
- Frontend `useAvailableModels()` hook called `/admin/domains/available-models`
- This endpoint **did NOT exist** (returned 404)
- Working endpoint exists at `/admin/llm/models` (returns 12 Ollama models)

#### Solution Implemented

**Option A (Frontend fix):** Updated hook to use existing endpoint

**File:** `frontend/src/hooks/useDomainTraining.ts`

```typescript
// Fixed: Uses existing LLM models endpoint
const response = await apiClient.get<OllamaModelsResponse>(
  '/admin/llm/models'  // ✅ Returns 12 Ollama models
);
if (response.ollama_available && response.models) {
  setData(response.models.map(m => m.name));
}
```

#### Files Changed

- `frontend/src/hooks/useDomainTraining.ts` (+20 LOC, -5 LOC)
  - Added `OllamaModelsResponse` interface
  - Updated `useAvailableModels()` to call `/admin/llm/models`
  - Added Ollama availability check

#### Success Criteria Met

- ✅ Model dropdown shows all 12 Ollama models
- ✅ Can select custom model when creating new domain
- ✅ No 404 errors in browser console
- ✅ Graceful handling if Ollama unavailable

---

### 📝 Feature 110.2: Groups 01-03 - Tool Execution (20 SP)

**Status:** 📝 Planned
**Story Points:** 20 SP (6-7 SP per group)
**Effort:** 2-3 days

#### Group 01: MCP Tools (6 tests) - 6 SP

**Scope:**
- MCP server connection status
- MCP tool discovery and listing
- MCP tool parameter validation
- MCP tool execution tracking

**Expected Issues:**
- MCP server health endpoint mocks
- Tool schema validation
- Server connection state management
- Tool execution response format

---

#### Group 02: Bash Execution (5 tests) - 7 SP

**Scope:**
- Bash command execution UI
- Command history display
- Output streaming
- Error handling and sanitization

**Expected Issues:**
- Security sandboxing indicators
- Streaming output display
- Command history persistence
- Error vs warning differentiation

---

#### Group 03: Python Execution (5 tests) - 7 SP

**Scope:**
- Python code execution UI
- Jupyter kernel integration
- Notebook cell management
- Output visualization

**Expected Issues:**
- Kernel startup indicators
- Cell execution state
- Output format handling (text, images, plots)
- Kernel restart functionality

---

### 📝 Feature 110.3: Groups 13-16 - Enterprise Features (40 SP)

**Status:** 📝 Planned
**Story Points:** 40 SP (10 SP per group)
**Effort:** 4-5 days

#### Group 13: Agent Hierarchy (8 tests) - 10 SP

**Scope:**
- Agent hierarchy visualization (Executive→Manager→Worker)
- Agent detail panels
- Agent performance metrics
- Agent communication flow

**Expected Issues:**
- Hierarchy tree visualization
- Agent status indicators
- Success rate formatting
- Agent interaction history

**Note:** Some fixes already done in Sprint 100 (GROUP_13_FIXES_SUMMARY.md)

---

#### Group 14: GDPR & Audit (10 tests) - 10 SP

**Scope:**
- GDPR consent registry UI
- Audit trail browser
- PII redaction settings
- Data subject rights UI

**Expected Issues:**
- Consent status display
- Audit log filtering/search
- PII detection indicators
- Data export functionality

---

#### Group 15: Explainability (9 tests) - 10 SP

**Scope:**
- RAG decision explanations
- Retrieval trace visualization
- Prompt engineering display
- Model reasoning breakdown

**Expected Issues:**
- Explanation formatting
- Trace timeline display
- Decision tree visualization
- Prompt diff viewer

---

#### Group 16: MCP Marketplace (8 tests) - 10 SP

**Scope:**
- MCP server marketplace UI
- Server installation/removal
- Server ratings and reviews
- Server configuration wizard

**Expected Issues:**
- Marketplace API integration
- Server installation progress
- Review submission UI
- Configuration form generation

---

## Sprint 110 Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Total Story Points** | 70 SP | 0 SP | 📝 Not Started |
| **Features Complete** | 4 | 0 | 📝 Not Started |
| **Test Groups Complete** | 9 | 0 | 📝 Not Started |
| **Individual Tests Passing** | ~70 tests | 0 tests | 📝 Not Started |

---

## Sprint 110 Execution Order

### Phase 1: Long Context (PRIORITY ⭐)
**Duration:** 1-2 days
**SP:** 10 SP

1. **Day 1-2: Group 09 Long Context** (10 tests, 10 SP)
   - Implement UI components (5 components)
   - Connect to backend APIs (4 endpoints)
   - Write E2E tests (10 tests)
   - **Deliverable:** Long Context UI fully functional

### Phase 2: Tool Execution
**Duration:** 2-3 days
**SP:** 20 SP

2. **Day 3-4: Groups 01-03** (16 tests, 20 SP)
   - Group 01: MCP Tools (6 tests)
   - Group 02: Bash Execution (5 tests)
   - Group 03: Python Execution (5 tests)
   - **Deliverable:** Tool execution E2E tests passing

### Phase 3: Enterprise Features
**Duration:** 4-5 days
**SP:** 40 SP

3. **Day 5-9: Groups 13-16** (35 tests, 40 SP)
   - Group 13: Agent Hierarchy (8 tests)
   - Group 14: GDPR & Audit (10 tests)
   - Group 15: Explainability (9 tests)
   - Group 16: MCP Marketplace (8 tests)
   - **Deliverable:** Enterprise E2E tests passing

**Sprint 110 Total Duration:** 9-10 days (~2 weeks)

---

## Dependencies & Blockers

### Group 09 Long Context Dependencies
- ✅ Backend context window calculation (should exist)
- ✅ Qdrant chunk metadata storage (exists)
- ❓ Context compression service (verify if implemented)
- ❓ Relevance scoring algorithm (verify if implemented)

### Group 06 (Deferred from Sprint 109)
- ❌ Chat interface integration (not yet implemented)
- **Decision:** Keep deferred until chat UI refactoring complete

---

## Success Criteria

### Minimum Viable (Must Have)
- ✅ Group 09: Long Context - 10/10 tests (100%)
- ✅ Groups 01-03: Tool Execution - >80% pass rate
- ✅ Groups 13-16: Enterprise - >80% pass rate

### Stretch Goals (Nice to Have)
- ✅ All 9 groups at 100% pass rate
- ✅ Group 06: Skills Using Tools (if time permits)
- ✅ Performance optimization for large document handling

---

## Known Risks

1. **Long Context UI Complexity**
   - **Risk:** 100+ chunks may cause UI performance issues
   - **Mitigation:** Virtual scrolling, lazy loading, pagination

2. **Backend API Availability**
   - **Risk:** Context compression/scoring APIs may not exist yet
   - **Mitigation:** Create mock endpoints if needed, document for backend team

3. **Large File Upload**
   - **Risk:** >10MB files may timeout
   - **Mitigation:** Chunked upload, progress tracking

4. **Scope Creep**
   - **Risk:** 70 SP in 2 weeks is aggressive
   - **Mitigation:** Prioritize Group 09, defer others if needed

---

## Deferred from Previous Sprints

### Group 06: Skills Using Tools (9 tests, 2 SP)
**Reason:** Requires chat interface integration
**Status:** ⏸️ Deferred to Sprint 111 or later
**Dependencies:** Chat UI refactoring

---

## Next Immediate Actions (Sprint 110 Kickoff)

**Pre-Sprint:**
1. ✅ Verify backend APIs exist for Long Context features
2. ✅ Review Group 09 test file to understand requirements
3. ✅ Identify reusable components from other groups

**Sprint Start:**
1. 📝 Create `LongContextViewer.tsx` component
2. 📝 Implement `ContextWindowIndicator.tsx` (progress gauge)
3. 📝 Build `ChunkExplorer.tsx` (virtual scroll list)
4. 📝 Add `RelevanceScoreDisplay.tsx` (score badges)
5. 📝 Develop `ContextCompressionPanel.tsx` (compression controls)
6. 📝 Connect to backend APIs
7. 📝 Write E2E tests for Group 09

---

**Last Updated:** 2026-01-17 (Sprint 110 PLANNED)
**Previous Sprint:** Sprint 109 (60/62 SP, 98.8% pass rate ✅)
**Next Review:** After Group 09 completion
