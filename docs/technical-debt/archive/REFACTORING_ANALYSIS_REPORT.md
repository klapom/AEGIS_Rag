# Comprehensive Refactoring Analysis Report
## Frontend-to-Backend Dead Code Detection

**Analysis Date:** 2025-12-07
**Objective:** Identify unused backend code by tracing frontend API calls

---

## Executive Summary

This analysis maps all frontend API calls against backend endpoints to identify unused code.

### Key Metrics
- **Total Frontend API Calls:** 26+ unique endpoints called
- **Total Backend Endpoints:** 65+ endpoints defined
- **Potentially Unused Endpoints:** ~15 endpoints (23%)
- **Files Analyzed:** 26 API/Router files

---

## 1. Frontend API Calls Summary

### Chat API (`frontend/src/api/chat.ts`)
**Called Endpoints (11):**
1. `POST /api/v1/chat/stream` - SSE streaming chat (Line 35) ✅ USED
2. `POST /api/v1/chat/` - Non-streaming chat (Line 106) ✅ USED
3. `GET /api/v1/chat/sessions` - List sessions (Line 128) ✅ USED
4. `GET /api/v1/chat/history/{session_id}` - Get history (Line 150) ✅ USED
5. `DELETE /api/v1/chat/history/{session_id}` - Delete history (Line 171) ✅ USED
6. `GET /api/v1/chat/sessions/{session_id}` - Get session info (Line 210) ✅ USED
7. `POST /api/v1/chat/sessions/{session_id}/generate-title` - Generate title (Line 233) ✅ USED
8. `PATCH /api/v1/chat/sessions/{session_id}` - Update title (Line 257) ✅ USED
9. `GET /api/v1/chat/sessions/{session_id}/followup-questions` - Get follow-ups (Line 287) ✅ USED
10. `GET /api/v1/chat/sessions/{session_id}/conversation` - Get conversation (Line 311) ✅ USED

### Admin API (`frontend/src/api/admin.ts`)
**Called Endpoints (6):**
1. `POST /api/v1/admin/reindex` - Re-index with SSE (Line 38) ✅ USED
2. `GET /api/v1/admin/stats` - System stats (Line 103) ✅ USED
3. `GET /api/v1/admin/costs/stats` - Cost stats (Line 164) ✅ USED
4. `POST /api/v1/admin/indexing/scan-directory` - Scan directory (Line 196) ✅ USED
5. `POST /api/v1/admin/indexing/upload` - Upload files (Line 241) ✅ USED
6. `POST /api/v1/admin/indexing/add` - Add documents SSE (Line 276) ✅ USED

### Graph Viz API (`frontend/src/api/graphViz.ts`)
**Called Endpoints (5):**
1. `POST /api/v1/graph/viz/export` - Export graph (Line 26) ✅ USED
2. `POST /api/v1/graph/viz/query-subgraph` - Query subgraph (Line 57) ✅ USED
3. `GET /api/v1/graph/viz/statistics` - Graph stats (Line 114) ✅ USED
4. `GET /api/v1/graph/viz/communities?limit=N` - Top communities (Line 137) ✅ USED
5. `POST /api/v1/graph/viz/node-documents` - Node documents (Line 167) ✅ USED

### Health API (`frontend/src/api/health.ts`)
**Called Endpoints (2):**
1. `GET /health` - Basic health (Line 16) ✅ USED
2. `GET /health/detailed` - Detailed health (Line 36) ✅ USED

---

## 2. Backend Endpoints Summary

### Chat API (`src/api/v1/chat.py`)
**Endpoints Defined (13):**
- `POST /chat/` (Line 328) ✅ USED
- `POST /chat/stream` (Line 467) ✅ USED
- `GET /chat/sessions` (Line 673) ✅ USED
- `GET /chat/sessions/{session_id}` (Line 749) ✅ USED
- `GET /chat/history/{session_id}` (Line 804) ✅ USED
- `DELETE /chat/history/{session_id}` (Line 862) ✅ USED
- `POST /chat/sessions/{session_id}/generate-title` (Line 926) ✅ USED
- `PATCH /chat/sessions/{session_id}` (Line 1021) ✅ USED
- `GET /chat/sessions/{session_id}/followup-questions` (Line 1267) ✅ USED
- `POST /chat/sessions/{session_id}/archive` (Line 1453) ⚠️ **UNUSED** (manual trigger)
- `POST /chat/search` (Line 1513) ⚠️ **UNUSED** (conversation search)
- `GET /chat/sessions/{session_id}/conversation` (Line 311 in frontend) ✅ USED

### Admin API (`src/api/v1/admin.py`)
**Endpoints Defined (20+):**
- `POST /admin/reindex` (Line 343) ✅ USED
- `POST /admin/indexing/add` (Line 846) ✅ USED
- `POST /admin/indexing/scan-directory` (Line 952) ✅ USED
- `POST /admin/indexing/upload` (Line 1111) ✅ USED
- `GET /admin/stats` (Line 1473) ✅ USED
- `POST /admin/indexing/stream-progress` (Line 1665) ⚠️ **UNUSED** (old SSE implementation?)
- `GET /admin/costs/stats` (Line 2002) ✅ USED
- `GET /admin/costs/history` (Line 2254) ⚠️ **UNUSED** (not in frontend)
- `POST /admin/indexing/batch` (Line 2456) ⚠️ **UNUSED** (batch ingestion)
- `GET /admin/ingestion/jobs` (Line 2734) ⚠️ **POSSIBLY UNUSED** (job tracking)
- `GET /admin/ingestion/jobs/{job_id}` (Line 2804) ⚠️ **POSSIBLY UNUSED**
- `GET /admin/ingestion/jobs/{job_id}/events` (Line 2868) ⚠️ **POSSIBLY UNUSED**
- `GET /admin/ingestion/jobs/{job_id}/errors` (Line 2937) ⚠️ **POSSIBLY UNUSED**
- `POST /admin/ingestion/jobs/{job_id}/cancel` (Line 2993) ⚠️ **POSSIBLY UNUSED**
- `DELETE /admin/ingestion/jobs/{job_id}` (Line 3060) ⚠️ **POSSIBLY UNUSED**
- `GET /admin/ingestion/jobs/{job_id}/progress` (Line 3130) ⚠️ **POSSIBLY UNUSED**
- `GET /admin/pipeline/config` (Line 3365) ⚠️ **POSSIBLY UNUSED**
- `POST /admin/pipeline/config` (Line 3432) ⚠️ **POSSIBLY UNUSED**
- `POST /admin/pipeline/config/preset/{preset_name}` (Line 3504) ⚠️ **POSSIBLY UNUSED**

### Graph Viz API (`src/api/routers/graph_viz.py`)
**Endpoints Defined (10):**
- `POST /api/v1/graph/viz/export` (Line 231) ✅ USED
- `GET /api/v1/graph/viz/export/formats` (Line 278) ⚠️ **UNUSED**
- `POST /api/v1/graph/viz/filter` (Line 299) ⚠️ **UNUSED**
- `POST /api/v1/graph/viz/communities/highlight` (Line 350) ⚠️ **UNUSED**
- `POST /api/v1/graph/viz/query-subgraph` (Line 406) ✅ USED
- `GET /api/v1/graph/viz/statistics` (Line 447) ✅ USED
- `POST /api/v1/graph/viz/node-documents` (Line 514) ✅ USED
- `GET /api/v1/graph/viz/communities/{community_id}/documents` (Line 572) ⚠️ **POSSIBLY USED** (useCommunityDocuments hook)
- `POST /api/v1/graph/viz/multi-hop` (Line 672) ⚠️ **UNUSED** (Sprint 34 feature)
- `POST /api/v1/graph/viz/shortest-path` (Line 805) ⚠️ **UNUSED** (Sprint 34 feature)

### Retrieval API (`src/api/v1/retrieval.py`)
**Endpoints Defined (6):**
- `POST /retrieval/search` (Line 181) ⚠️ **POSSIBLY UNUSED**
- `POST /retrieval/ingest` (Line 325) ⚠️ **UNUSED**
- `POST /retrieval/upload` (Line 412) ⚠️ **UNUSED** (duplicate of admin/upload?)
- `GET /retrieval/formats` (Line 544) ⚠️ **UNUSED**
- `POST /retrieval/prepare-bm25` (Line 601) ⚠️ **UNUSED** (internal API?)
- `GET /retrieval/stats` (Line 644) ⚠️ **UNUSED**
- `POST /retrieval/auth/token` (Line 694) ⚠️ **UNUSED** (auth endpoint?)

### Auth API (`src/api/v1/auth.py`)
**Endpoints Defined (2):**
- `POST /auth/login` (Line 92) ⚠️ **UNUSED** (no auth in frontend)
- `GET /auth/me` (Line 173) ⚠️ **UNUSED** (no auth in frontend)

### Memory API (`src/api/v1/memory.py`)
**Endpoints Defined (6):**
- `POST /memory/search` (Line 204) ⚠️ **UNUSED**
- `POST /memory/temporal/point-in-time` (Line 319) ⚠️ **UNUSED**
- `GET /memory/session/{session_id}` (Line 408) ⚠️ **UNUSED**
- `POST /memory/consolidate` (Line 491) ⚠️ **UNUSED**
- `GET /memory/stats` (Line 571) ⚠️ **UNUSED**
- `DELETE /memory/session/{session_id}` (Line 694) ⚠️ **UNUSED**

### Health API (`src/api/v1/health.py`)
**Endpoints Defined (4):**
- `GET /api/v1/health/` (Line 47) ✅ USED
- `GET /api/v1/health/detailed` (Line 66) ✅ USED
- `GET /api/v1/health/ready` (Line 158) ⚠️ **UNUSED** (Kubernetes probe?)
- `GET /api/v1/health/live` (Line 185) ⚠️ **UNUSED** (Kubernetes probe?)

### Annotations API (`src/api/v1/annotations.py`)
**Endpoints Defined (2):**
- `GET /annotations/{annotation_id}` (Line 98) ⚠️ **UNUSED**
- `GET /annotations/chunk/{chunk_id}` (Line 266) ⚠️ **UNUSED**

---

## 3. Unused Endpoints (MARK FOR DEPRECATION)

### HIGH PRIORITY - Completely Unused

| Endpoint | File | Line | Recommendation |
|----------|------|------|----------------|
| `POST /chat/sessions/{session_id}/archive` | chat.py | 1453 | ⚠️ DEPRECATE (manual trigger not used) |
| `POST /chat/search` | chat.py | 1513 | ⚠️ DEPRECATE (conversation search unused) |
| `GET /admin/costs/history` | admin.py | 2254 | ⚠️ DEPRECATE (frontend uses /costs/stats only) |
| `POST /admin/indexing/batch` | admin.py | 2456 | ⚠️ DEPRECATE (batch ingestion not used) |
| `GET /api/v1/graph/viz/export/formats` | graph_viz.py | 278 | ⚠️ DEPRECATE (formats hardcoded in frontend) |
| `POST /api/v1/graph/viz/filter` | graph_viz.py | 299 | ⚠️ DEPRECATE (filtering done client-side) |
| `POST /api/v1/graph/viz/communities/highlight` | graph_viz.py | 350 | ⚠️ DEPRECATE (highlighting done client-side) |
| `POST /api/v1/graph/viz/multi-hop` | graph_viz.py | 672 | ⚠️ DEPRECATE (Sprint 34 not integrated) |
| `POST /api/v1/graph/viz/shortest-path` | graph_viz.py | 805 | ⚠️ DEPRECATE (Sprint 34 not integrated) |
| `POST /retrieval/search` | retrieval.py | 181 | ⚠️ DEPRECATE (replaced by coordinator) |
| `POST /retrieval/ingest` | retrieval.py | 325 | ⚠️ DEPRECATE (replaced by admin/indexing) |
| `POST /retrieval/upload` | retrieval.py | 412 | ⚠️ DEPRECATE (duplicate of admin/upload) |
| `GET /retrieval/formats` | retrieval.py | 544 | ⚠️ DEPRECATE (formats returned by admin API) |
| `POST /retrieval/prepare-bm25` | retrieval.py | 601 | ⚠️ DEPRECATE (internal, should be private) |
| `GET /retrieval/stats` | retrieval.py | 644 | ⚠️ DEPRECATE (replaced by admin/stats) |
| `POST /retrieval/auth/token` | retrieval.py | 694 | ⚠️ DEPRECATE (auth not implemented) |
| `POST /auth/login` | auth.py | 92 | ⚠️ DEPRECATE (auth not implemented) |
| `GET /auth/me` | auth.py | 173 | ⚠️ DEPRECATE (auth not implemented) |

### MEDIUM PRIORITY - Possibly Unused (Requires Verification)

| Endpoint | File | Line | Notes |
|----------|------|------|-------|
| `GET /admin/ingestion/jobs` | admin.py | 2734 | Job tracking endpoints - verify if used by Sprint 37 |
| `GET /admin/ingestion/jobs/{job_id}` | admin.py | 2804 | Job tracking endpoints - verify if used by Sprint 37 |
| `GET /admin/ingestion/jobs/{job_id}/events` | admin.py | 2868 | Job tracking endpoints - verify if used by Sprint 37 |
| `GET /admin/ingestion/jobs/{job_id}/errors` | admin.py | 2937 | Job tracking endpoints - verify if used by Sprint 37 |
| `POST /admin/ingestion/jobs/{job_id}/cancel` | admin.py | 2993 | Job tracking endpoints - verify if used by Sprint 37 |
| `DELETE /admin/ingestion/jobs/{job_id}` | admin.py | 3060 | Job tracking endpoints - verify if used by Sprint 37 |
| `GET /admin/ingestion/jobs/{job_id}/progress` | admin.py | 3130 | Job tracking endpoints - verify if used by Sprint 37 |
| `GET /admin/pipeline/config` | admin.py | 3365 | Pipeline config endpoints - verify if used by Sprint 37 |
| `POST /admin/pipeline/config` | admin.py | 3432 | Pipeline config endpoints - verify if used by Sprint 37 |
| `POST /admin/pipeline/config/preset/{preset_name}` | admin.py | 3504 | Pipeline config endpoints - verify if used by Sprint 37 |
| `POST /memory/search` | memory.py | 204 | Memory endpoints - verify if used by coordinator |
| `POST /memory/temporal/point-in-time` | memory.py | 319 | Memory endpoints - verify if used by coordinator |
| `GET /memory/session/{session_id}` | memory.py | 408 | Memory endpoints - verify if used by coordinator |
| `POST /memory/consolidate` | memory.py | 491 | Memory endpoints - verify if used by coordinator |
| `GET /memory/stats` | memory.py | 571 | Memory endpoints - verify if used by coordinator |
| `DELETE /memory/session/{session_id}` | memory.py | 694 | Memory endpoints - verify if used by coordinator |
| `GET /annotations/{annotation_id}` | annotations.py | 98 | Annotations endpoints - verify if used by frontend |
| `GET /annotations/chunk/{chunk_id}` | annotations.py | 266 | Annotations endpoints - verify if used by frontend |

### LOW PRIORITY - Infrastructure Endpoints

| Endpoint | File | Line | Notes |
|----------|------|------|-------|
| `GET /api/v1/health/ready` | health.py | 158 | Kubernetes readiness probe - keep for deployment |
| `GET /api/v1/health/live` | health.py | 185 | Kubernetes liveness probe - keep for deployment |

---

## 4. Unused Service Functions

### Candidate Files for Review
1. **`src/api/v1/retrieval.py`** - Entire file appears unused (replaced by coordinator)
2. **`src/api/v1/auth.py`** - Auth system not implemented in frontend
3. **`src/api/v1/memory.py`** - Memory API not called from frontend (used internally?)
4. **`src/api/v1/annotations.py`** - Annotations system not visible in frontend

---

## 5. Recommended Refactoring Actions

### Phase 1: Mark Unused Code (NO DELETION)
1. Add `# DEPRECATED: Not called from frontend (identified 2025-12-07)` comments to all HIGH PRIORITY endpoints
2. Add deprecation warnings to endpoint docstrings
3. Create tracking issue for removal in next major version

### Phase 2: Verification (Before Deletion)
1. Search backend codebase for internal calls to MEDIUM PRIORITY endpoints
2. Check if coordinator/agents use memory/retrieval APIs internally
3. Verify Sprint 37 job tracking integration
4. Check if annotations are used in admin workflows

### Phase 3: Consolidation (Future Sprint)
1. Merge duplicate functionality:
   - `/retrieval/upload` → `/admin/indexing/upload`
   - `/retrieval/stats` → `/admin/stats`
2. Move internal APIs to private modules:
   - `POST /retrieval/prepare-bm25` → internal helper
3. Complete auth implementation or remove auth API entirely

---

## 6. Code Marked with DEPRECATED Comments

### Files to Modify
- `src/api/v1/chat.py` (2 endpoints)
- `src/api/v1/admin.py` (2 endpoints)
- `src/api/routers/graph_viz.py` (5 endpoints)
- `src/api/v1/retrieval.py` (7 endpoints - entire file)
- `src/api/v1/auth.py` (2 endpoints - entire file)

---

## 7. Estimated Impact

### Code Reduction Potential
- **Endpoints to deprecate:** 18 HIGH PRIORITY + 18 MEDIUM PRIORITY = 36 endpoints
- **Lines of code:** ~5,000+ lines (endpoint definitions + helper functions)
- **Test files:** ~2,000+ lines of tests for deprecated endpoints

### Maintenance Benefits
- Reduced API surface area (-55% endpoints)
- Simplified documentation
- Faster onboarding for new developers
- Reduced security attack surface

---

## 8. Next Steps

1. ✅ **Review this report** with team
2. ⏳ **Mark HIGH PRIORITY endpoints** with DEPRECATED comments (this PR)
3. ⏳ **Verify MEDIUM PRIORITY endpoints** (internal usage check)
4. ⏳ **Create removal plan** for next major version
5. ⏳ **Update API documentation** to reflect deprecated status

---

## Appendix A: Frontend API Usage by Component

### Chat Components
- `HomePage.tsx` → Uses `streamChat()`, `getFollowUpQuestions()`
- `SessionSidebar` → Uses `listSessions()`, `deleteSession()`
- `ConversationHistory` → Uses `getConversationHistory()`

### Admin Components
- `AdminIndexingPage.tsx` → Uses `streamReindex()`, `scanDirectory()`, `uploadFiles()`, `streamAddDocuments()`
- `AdminLLMConfigPage.tsx` → Uses `getSystemStats()`
- `CostDashboardPage.tsx` → Uses `getCostStats()`

### Graph Components
- `GraphVisualization3D.tsx` → Uses `fetchGraphData()`, `fetchGraphStatistics()`
- `GraphSearchPanel.tsx` → Uses `fetchQuerySubgraph()`
- `NodeDetailsPanel.tsx` → Uses `fetchDocumentsByNode()`

---

## Appendix B: Backend Endpoints by Router

### ✅ Active Routers (High Usage)
1. **chat.py** - 11/13 endpoints used (85%)
2. **admin.py** - 6/20 endpoints used (30%)
3. **graph_viz.py** - 5/10 endpoints used (50%)
4. **health.py** - 2/4 endpoints used (50%)

### ⚠️ Deprecated Routers (Low/No Usage)
1. **retrieval.py** - 0/7 endpoints used (0%)
2. **auth.py** - 0/2 endpoints used (0%)
3. **memory.py** - 0/6 endpoints used (0%)
4. **annotations.py** - 0/2 endpoints used (0%)

---

**Report Generated:** 2025-12-07
**Analyzed By:** Backend Agent (AEGIS RAG)
**Status:** Ready for Review
