# Frontend-to-Backend Integration Test Plan

**Version:** 1.1
**Date:** 2025-12-16
**Sprint:** 46 (Post-Implementation Testing)
**LLM Model:** nemotron-3-nano (INSTALLED), nemotron-no-think (think=false)
**Test Results:** [TEST_RESULTS_FRONTEND_BACKEND.md](TEST_RESULTS_FRONTEND_BACKEND.md)

---

## Overview

Dieser Testplan dokumentiert systematische Tests aller Frontend-Funktionen mit ihren Backend-Endpunkten. Tests werden manuell vom Frontend aus durchgeführt, um die End-to-End-Funktionalität zu validieren.

### Test-Umgebung
- **Frontend:** http://localhost:5179 (Vite Dev Server)
- **Backend:** http://localhost:8000 (FastAPI)
- **Databases:** Qdrant (6333), Neo4j (7687), Redis (6379)
- **LLM:** Ollama (11434) - nemotron-3-nano

---

## Test Categories

| Category | Priority | Endpoints | Estimated Time |
|----------|----------|-----------|----------------|
| 1. Health & Connectivity | P0 | 2 | 5 min |
| 2. Authentication | P0 | 3 | 5 min |
| 3. Chat Streaming | P0 | 5 | 15 min |
| 4. Session Management | P1 | 6 | 10 min |
| 5. Admin Dashboard | P1 | 4 | 10 min |
| 6. Indexing Pipeline | P1 | 4 | 15 min |
| 7. Domain Training | P1 | 5 | 15 min |
| 8. Graph Visualization | P2 | 5 | 10 min |
| 9. Temporal Features | P2 | 4 | 10 min |
| **Total** | | **38** | **~95 min** |

---

## Category 1: Health & Connectivity (P0)

### Test 1.1: Basic Health Check
**Page:** HealthDashboard
**Endpoint:** `GET /health`
**Steps:**
1. Navigate to `/health` page
2. Verify page loads without errors
3. Check all service indicators (green/red)

**Expected:**
- [ ] Page loads within 3 seconds
- [ ] Shows status for: API, Qdrant, Neo4j, Redis, Ollama

### Test 1.2: Detailed Health Check
**Endpoint:** `GET /health/detailed`
**Steps:**
1. On HealthDashboard, check detailed view
2. Verify all dependency statuses

**Expected:**
- [ ] Response includes version info
- [ ] Shows memory/CPU metrics
- [ ] All services marked "healthy"

---

## Category 2: Authentication (P0)

### Test 2.1: Login Flow
**Page:** Login Page (if exists)
**Endpoint:** `POST /api/v1/auth/login`
**Steps:**
1. Open app in incognito/private window
2. Attempt to access protected route
3. Login with credentials

**Expected:**
- [ ] Redirects to login if unauthenticated
- [ ] JWT token stored in localStorage
- [ ] Redirects to dashboard after login

### Test 2.2: Session Persistence
**Endpoint:** `GET /api/v1/auth/me`
**Steps:**
1. After login, refresh page
2. Check if session persists

**Expected:**
- [ ] User remains logged in
- [ ] User info displays correctly

### Test 2.3: Logout
**Endpoint:** `POST /api/v1/auth/logout`
**Steps:**
1. Click logout button
2. Verify token cleared

**Expected:**
- [ ] Token removed from localStorage
- [ ] Redirects to login/home

---

## Category 3: Chat Streaming (P0) - CRITICAL

### Test 3.1: Basic Chat Query
**Page:** HomePage (/)
**Endpoint:** `POST /api/v1/chat/stream` (SSE)
**Steps:**
1. Navigate to home page
2. Enter query: "Was ist OMNITRACKER?"
3. Submit query

**Expected:**
- [ ] SSE connection established
- [ ] Tokens stream incrementally
- [ ] Answer completes within 30s
- [ ] No timeout errors

### Test 3.2: Search Mode Selection
**Component:** SearchInput
**Steps:**
1. Test each search mode:
   - [ ] Hybrid (default)
   - [ ] Vector only
   - [ ] Graph only
   - [ ] Memory only

**Expected:**
- [ ] Mode indicator shows correctly
- [ ] Query uses selected mode
- [ ] Results differ between modes

### Test 3.3: Source Citations
**Endpoint:** SSE metadata
**Steps:**
1. Query something with known sources
2. Check source cards below answer

**Expected:**
- [ ] Sources display with titles
- [ ] Clicking source shows details
- [ ] Citation numbers match

### Test 3.4: Reasoning Panel (Sprint 46)
**Component:** ReasoningPanel
**Steps:**
1. Submit query
2. Expand "Reasoning anzeigen" panel

**Expected:**
- [ ] Panel expands/collapses
- [ ] Shows Intent classification
- [ ] Shows Retrieval steps with timing:
  - Qdrant Vector Search
  - BM25 Keyword Search
  - Neo4j Graph Query
  - Redis Memory Check
  - RRF Fusion

### Test 3.5: Follow-Up Questions
**Endpoint:** `GET /api/v1/chat/sessions/{id}/followup-questions`
**Steps:**
1. After receiving answer
2. Check for follow-up suggestions

**Expected:**
- [ ] 2-4 follow-up questions displayed
- [ ] Clicking question sends new query
- [ ] Context maintained

---

## Category 4: Session Management (P1)

### Test 4.1: Session Creation
**Endpoint:** Automatic via chat
**Steps:**
1. Start new conversation
2. Check session sidebar

**Expected:**
- [ ] New session appears in sidebar
- [ ] Grouped by date (today, yesterday, etc.)

### Test 4.2: Session History
**Endpoint:** `GET /api/v1/chat/sessions`
**Component:** SessionSidebar
**Steps:**
1. View session list
2. Click on previous session

**Expected:**
- [ ] All sessions listed
- [ ] Clicking loads conversation history
- [ ] Messages display correctly

### Test 4.3: Auto-Generated Titles
**Endpoint:** `POST /api/v1/chat/sessions/{id}/generate-title`
**Steps:**
1. Start new conversation
2. Wait for title generation (~5s)

**Expected:**
- [ ] Title auto-generates based on query
- [ ] Title visible in sidebar
- [ ] German titles if German query

### Test 4.4: Manual Title Edit
**Endpoint:** `PATCH /api/v1/chat/sessions/{id}`
**Steps:**
1. Click edit icon on session title
2. Enter new title
3. Save

**Expected:**
- [ ] Edit mode activates
- [ ] New title saves
- [ ] Title persists after refresh

### Test 4.5: Session Deletion
**Endpoint:** `DELETE /api/v1/chat/history/{id}`
**Steps:**
1. Click delete on a session
2. Confirm deletion

**Expected:**
- [ ] Confirmation dialog appears
- [ ] Session removed from list
- [ ] No data leakage

### Test 4.6: Conversation Search
**Endpoint:** `POST /api/v1/chat/search`
**Steps:**
1. Use search field in sidebar
2. Search for keyword

**Expected:**
- [ ] Matching conversations shown
- [ ] Highlights match context

---

## Category 5: Admin Dashboard (P1)

### Test 5.1: Dashboard Load
**Page:** AdminDashboard (/admin)
**Steps:**
1. Navigate to /admin
2. Check all sections load

**Expected:**
- [ ] Domain Section visible
- [ ] Indexing Section visible
- [ ] Settings Section visible
- [ ] No loading spinners stuck

### Test 5.2: System Statistics
**Endpoint:** `GET /api/v1/admin/stats`
**Steps:**
1. On Admin page, check stats display

**Expected:**
- [ ] Qdrant: Vector count, collection size
- [ ] Neo4j: Node count, relationship count
- [ ] BM25: Document count
- [ ] Redis: Key count

### Test 5.3: Namespace List
**Endpoint:** `GET /api/v1/admin/namespaces`
**Component:** NamespaceSelector
**Steps:**
1. Check namespace dropdown
2. Select different namespace

**Expected:**
- [ ] Namespaces load correctly
- [ ] Selection persists
- [ ] Affects search scope

### Test 5.4: Collapsible Sections
**Component:** AdminSection
**Steps:**
1. Click section headers to collapse/expand

**Expected:**
- [ ] Sections collapse smoothly
- [ ] State persists during session

---

## Category 6: Indexing Pipeline (P1)

### Test 6.1: Directory Scan
**Endpoint:** `POST /api/v1/admin/indexing/scan-directory`
**Steps:**
1. Navigate to Admin > Indexing
2. Enter directory path: `/home/admin/test-docs/`
3. Click "Scan"

**Expected:**
- [ ] File list appears
- [ ] Files categorized (Docling/LlamaIndex/Unsupported)
- [ ] File count shown

### Test 6.2: Dry-Run Indexing
**Endpoint:** `POST /api/v1/admin/reindex` (SSE)
**Steps:**
1. Enable "Dry Run" toggle
2. Click "Index"

**Expected:**
- [ ] SSE progress stream
- [ ] Shows what WOULD be indexed
- [ ] No actual database changes

### Test 6.3: Live Indexing
**Endpoint:** `POST /api/v1/admin/reindex` (SSE)
**Steps:**
1. Disable "Dry Run"
2. Click "Index"
3. Monitor progress

**Expected:**
- [ ] Progress bar updates
- [ ] File-by-file status
- [ ] Completion notification
- [ ] Stats update after completion

### Test 6.4: Pipeline Progress Details
**Component:** PipelineProgressVisualization
**Endpoint:** EventSource `/api/v1/admin/indexing/progress/{jobId}`
**Steps:**
1. During indexing, click "Details"
2. View step-by-step progress

**Expected:**
- [ ] Shows: Chunking → Embedding → Vector Store → Graph
- [ ] Per-step timing
- [ ] Error details if any

---

## Category 7: Domain Training (P1)

### Test 7.1: Domain List
**Endpoint:** `GET /admin/domains`
**Page:** DomainTrainingPage
**Steps:**
1. Navigate to Admin > Domains
2. View domain list

**Expected:**
- [ ] Domains listed with status
- [ ] "general" (fallback) always present
- [ ] Training status indicators

### Test 7.2: Domain Auto-Discovery (Sprint 46)
**Component:** DomainAutoDiscovery
**Endpoint:** `POST /api/v1/admin/domains/discover`
**Steps:**
1. Click "New Domain" > "Auto-Discovery" tab
2. Upload 1-3 sample documents
3. Click "Analyze"

**Expected:**
- [ ] Files accepted (TXT, MD, DOCX, PDF)
- [ ] Loading indicator during analysis
- [ ] Suggested title & description appear
- [ ] Can edit before accepting

### Test 7.3: Domain Creation
**Endpoint:** `POST /admin/domains`
**Steps:**
1. Fill in domain details (manual or from discovery)
2. Click "Create"

**Expected:**
- [ ] Domain created successfully
- [ ] Appears in domain list
- [ ] Status: "untrained"

### Test 7.4: Domain Training
**Endpoint:** `POST /admin/domains/{name}/train`
**Steps:**
1. Select domain
2. Configure training (model, samples)
3. Click "Start Training"

**Expected:**
- [ ] SSE training progress
- [ ] Shows optimization steps
- [ ] Status changes: training → ready

### Test 7.5: Document Classification
**Endpoint:** `POST /admin/domains/classify`
**Steps:**
1. Upload new document
2. Check domain suggestion

**Expected:**
- [ ] Domain suggested based on content
- [ ] Confidence score shown
- [ ] Can override suggestion

---

## Category 8: Graph Visualization (P2)

### Test 8.1: Graph Load
**Endpoint:** `POST /api/v1/graph/viz/export`
**Page:** GraphAnalyticsPage
**Steps:**
1. Navigate to Graph page
2. Wait for graph to load

**Expected:**
- [ ] D3 visualization renders
- [ ] Nodes and edges visible
- [ ] Can zoom/pan

### Test 8.2: Graph Search
**Component:** GraphSearch
**Steps:**
1. Enter entity name in search
2. Select from results

**Expected:**
- [ ] Autocomplete suggestions
- [ ] Clicking centers on node
- [ ] Node details panel shows

### Test 8.3: Node Details
**Component:** NodeDetailsPanel
**Steps:**
1. Click on a node
2. View details panel

**Expected:**
- [ ] Entity name, type, properties
- [ ] Connected relationships
- [ ] Related documents link

### Test 8.4: Community Detection
**Endpoint:** `GET /api/v1/graph/viz/communities`
**Component:** TopCommunities
**Steps:**
1. View top communities list

**Expected:**
- [ ] Communities ranked by size
- [ ] Can click to view community
- [ ] Community members listed

### Test 8.5: Graph Statistics
**Endpoint:** `GET /api/v1/graph/viz/statistics`
**Steps:**
1. View graph stats panel

**Expected:**
- [ ] Total nodes/edges
- [ ] Entity type distribution
- [ ] Relationship type distribution

---

## Category 9: Temporal Features (P2)

### Test 9.1: Point-in-Time Query
**Endpoint:** `POST /api/v1/temporal/point-in-time`
**Component:** TimeTravelTab
**Steps:**
1. Navigate to Graph > Time Travel
2. Select date in past
3. Execute query

**Expected:**
- [ ] Graph shows state at selected time
- [ ] Entities that didn't exist are hidden
- [ ] Changes highlighted

### Test 9.2: Entity Changelog
**Endpoint:** `GET /api/v1/entities/{id}/changelog`
**Component:** EntityChangelog
**Steps:**
1. Select entity
2. View "History" tab

**Expected:**
- [ ] Chronological change list
- [ ] Shows: Created, Updated, Deleted events
- [ ] Timestamps for each change

### Test 9.3: Version Comparison
**Endpoint:** `GET /api/v1/entities/{id}/versions/{a}/compare/{b}`
**Component:** VersionCompare
**Steps:**
1. Select two versions from changelog
2. Click "Compare"

**Expected:**
- [ ] Side-by-side diff view
- [ ] Highlights added/removed properties
- [ ] Shows relationship changes

### Test 9.4: Version Revert
**Endpoint:** `POST /api/v1/entities/{id}/versions/{v}/revert`
**Steps:**
1. Select previous version
2. Click "Revert to this version"
3. Confirm

**Expected:**
- [ ] Confirmation dialog
- [ ] Entity reverted
- [ ] New changelog entry for revert

---

## Test Execution Protocol

### Before Testing
1. [ ] Ensure all services running: `docker ps`
2. [ ] Verify Ollama model: `curl http://localhost:11434/api/tags`
3. [ ] Clear browser cache
4. [ ] Open browser DevTools > Network tab

### During Testing
- Record response times
- Note any errors in console
- Screenshot failures
- Log API responses for debugging

### After Each Test
- Mark test as: PASS / FAIL / BLOCKED
- Note any issues found
- Create bug ticket if needed

---

## Test Results Template

```markdown
## Test Results - [DATE]

### Summary
| Category | Passed | Failed | Blocked | Notes |
|----------|--------|--------|---------|-------|
| Health   | X/2    |        |         |       |
| Auth     | X/3    |        |         |       |
| Chat     | X/5    |        |         |       |
| Sessions | X/6    |        |         |       |
| Admin    | X/4    |        |         |       |
| Indexing | X/4    |        |         |       |
| Domain   | X/5    |        |         |       |
| Graph    | X/5    |        |         |       |
| Temporal | X/4    |        |         |       |
| **Total**| X/38   |        |         |       |

### Issues Found
1. [Issue Title] - Category X.X
   - Description:
   - Severity: P0/P1/P2
   - Screenshot: [link]

### Notes
- LLM Model used:
- Response times:
- Special observations:
```

---

## Quick Reference: API Endpoints

> **Note:** Updated 2025-12-16 based on actual API testing. See `TEST_RESULTS_FRONTEND_BACKEND.md` for details.

### Health API
```
GET  /health                      # Basic health check (VERIFIED)
GET  /health/detailed             # NOT IMPLEMENTED
```

### Chat API
```
POST /api/v1/chat/stream          # SSE Chat Streaming (VERIFIED)
GET  /api/v1/chat/sessions        # List sessions (VERIFIED)
GET  /api/v1/chat/sessions/{id}   # Session info (VERIFIED)
POST /api/v1/chat/sessions/{id}/generate-title
GET  /api/v1/chat/sessions/{id}/followup-questions
DELETE /api/v1/chat/history/{id}  # Delete session
POST /api/v1/chat/search          # Conversation search
```

### Admin API
```
GET  /api/v1/admin/stats          # System stats (VERIFIED)
GET  /api/v1/admin/namespaces     # Namespace list (VERIFIED)
POST /api/v1/admin/reindex        # SSE Reindex
POST /api/v1/admin/indexing/scan-directory  # param: "path" (not "directory")
GET  /api/v1/admin/ingestion/jobs            # Job list (VERIFIED)
GET  /api/v1/admin/ingestion/jobs/{job_id}/progress  # EventSource
```

### Domain API
```
GET  /admin/domains/              # List domains (TRAILING SLASH REQUIRED!) (VERIFIED)
POST /admin/domains/              # Create domain
POST /admin/domains/{name}/train  # Start training
GET  /admin/domains/{name}/training-status
GET  /admin/domains/available-models  # List Ollama models (VERIFIED)
POST /api/v1/admin/domains/discover   # Auto-discovery
POST /admin/domains/classify          # Classify document
```

### Graph API
```
GET  /api/v1/graph/analytics/statistics  # Analytics stats (VERIFIED)
GET  /api/v1/graph/viz/statistics        # Viz stats (VERIFIED)
GET  /api/v1/graph/visualize/subgraph    # Subgraph export
GET  /api/v1/graph/viz/communities       # NOT IMPLEMENTED
```

### Temporal API (NOT IMPLEMENTED)
```
POST /api/v1/temporal/point-in-time      # NOT IMPLEMENTED
GET  /api/v1/entities/{id}/changelog     # NOT IMPLEMENTED
```

---

## Next Steps After Testing

1. **Document Results** in `docs/testing/TEST_RESULTS_SPRINT46.md`
2. **Create Bug Tickets** for any failures
3. **Update ADRs** if architectural issues found
4. **Plan Sprint 47** based on findings
