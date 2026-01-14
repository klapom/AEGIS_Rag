# API-Frontend Gap Analysis - Sprint 71

**Date:** 2026-01-02
**Sprint:** 71
**Status:** Analysis Complete

---

## Executive Summary

**Total Backend API Endpoints:** 150
**Frontend-Connected Endpoints:** 42 (28%)
**Gaps (No Frontend UI):** 108 (72%!)

This represents a **significant architectural issue** - the majority of backend functionality has no user-facing interface.

---

## Gap Distribution by Category

| Category | Total Endpoints | Frontend Connected | Gaps | Gap % |
|----------|----------------|-------------------|------|-------|
| Domain Training | 13 | 0 | 13 | 100% |
| MCP (Tool Framework) | 7 | 0 | 7 | 100% |
| Admin - Ingestion Jobs | 6 | 0 | 6 | 100% |
| Graph Analytics | 6 | 0 | 6 | 100% |
| Retrieval | 6 | 0 | 6 | 100% |
| Memory | 5 | 0 | 5 | 100% |
| Health | 7 | 3 | 4 | 57% |
| Auth | 5 | 2 | 3 | 60% |
| Admin - Indexing | 18 | 11 | 7 | 39% |
| Chat & Sessions | 15 | 12 | 3 | 20% |

---

## Detailed Gap Analysis

### 🔴 CRITICAL GAPS (Must Fix in Sprint 71)

#### 1. Admin - Ingestion Jobs (6 endpoints, 100% gap)
**Problem:** Users have NO visibility into document ingestion job status.

**Missing Endpoints:**
```
GET    /admin/ingestion/jobs
GET    /admin/ingestion/jobs/{job_id}
POST   /admin/ingestion/jobs/{job_id}/cancel
GET    /admin/ingestion/jobs/{job_id}/errors
GET    /admin/ingestion/jobs/{job_id}/events
GET    /admin/ingestion/jobs/{job_id}/progress
```

**Impact:** Users cannot:
- Monitor long-running ingestion jobs
- Cancel stuck jobs
- Debug ingestion errors
- Track batch upload progress

**Solution (Feature 71.8 - 5 SP):**
Create `/admin/jobs` page with:
- Job list table (status, progress, duration)
- Job detail modal (logs, errors, events)
- Cancel button
- Real-time progress updates (SSE or polling)

---

#### 2. MCP Tool Framework (7 endpoints, 100% gap)
**Problem:** Admins have NO way to manage MCP servers and tools via UI.

**Missing Endpoints:**
```
GET    /mcp/health
GET    /mcp/servers
POST   /mcp/servers/{server_name}/connect
POST   /mcp/servers/{server_name}/disconnect
GET    /mcp/tools
GET    /mcp/tools/{tool_name}
POST   /mcp/tools/{tool_name}/execute
```

**Impact:** Admins cannot:
- See which MCP servers are available
- Connect/disconnect servers
- View available tools per server
- Test tool execution

**Solution (Feature 71.9 - 3 SP):**
Extend `/admin/tools` page with:
- MCP server list (status, tools count)
- Connect/disconnect buttons
- Tool list per server
- Tool execution test panel

---

#### 3. Domain Training (13 endpoints, 100% gap)
**Problem:** Domain training workflow is COMPLETELY inaccessible via UI!

**Missing Endpoints:**
```
GET    /domain-training/
POST   /domain-training/
POST   /domain-training/augment
GET    /domain-training/available-models
POST   /domain-training/classify
POST   /domain-training/discover
POST   /domain-training/ingest-batch
DELETE /domain-training/{domain_name}
GET    /domain-training/{domain_name}
POST   /domain-training/{domain_name}/reindex
GET    /domain-training/{domain_name}/stats
POST   /domain-training/{domain_name}/train
GET    /domain-training/{domain_name}/training-status
GET    /domain-training/{domain_name}/training-stream
GET    /domain-training/{domain_name}/training-stream/stats
POST   /domain-training/{domain_name}/validate
```

**Impact:** Users cannot:
- Create/manage domains
- Upload training datasets
- Monitor training progress
- Validate trained models

**Note:** There IS a `/admin/domain-training` page in frontend, but it may be outdated!

**Action:** Audit existing DomainTrainingPage and connect all endpoints.

---

### 🟡 MEDIUM GAPS (Consider for Sprint 71)

#### 4. Memory Management (5 endpoints, 100% gap)
**Missing Endpoints:**
```
POST   /memory/consolidate
POST   /memory/search
GET    /memory/session/{session_id}
GET    /memory/stats
POST   /memory/temporal/point-in-time
```

**Impact:** Power users cannot:
- Search semantic memory
- Trigger memory consolidation
- View session-specific memories
- Query point-in-time memory state

**Solution (Feature 71.10 - 2 SP):**
Create `/admin/memory` page with:
- Memory stats dashboard
- Search interface
- Consolidation trigger
- Session memory viewer

---

#### 5. Retrieval (Direct Access) (6 endpoints, 100% gap)
**Missing Endpoints:**
```
POST   /retrieval/search
POST   /retrieval/ingest
POST   /retrieval/upload
GET    /retrieval/stats
GET    /retrieval/formats
POST   /retrieval/prepare-bm25
POST   /retrieval/auth/token
```

**Impact:** Power users cannot:
- Bypass chat interface for direct retrieval
- Test retrieval algorithms in isolation
- Manually prepare BM25 index

**Note:** These may be intentionally backend-only (API-first design).

**Action:** Evaluate if UI is needed - possibly for debugging/testing only.

---

### 🟢 LOW PRIORITY GAPS

#### 6. Graph Analytics (6 endpoints, likely DEPRECATED)
**Missing Endpoints:**
```
GET    /graph-analytics/centrality/{entity_id}
GET    /graph-analytics/gaps
GET    /graph-analytics/influential
GET    /graph-analytics/pagerank
GET    /graph-analytics/recommendations/{entity_id}
GET    /graph-analytics/statistics
```

**Status:** Likely replaced by `/graph/viz/*` endpoints.

**Action (Feature 71.11):** Mark as dead code and remove in Sprint 71.

---

#### 7. Graph Communities (2 endpoints, partial gap)
**Missing Endpoints:**
```
POST   /graph/communities/compare
GET    /graph/communities/{document_id}/sections/{section_id}
```

**Impact:** Users cannot:
- Compare community structures between documents
- View section-specific community data

**Action:** Low priority - niche power-user feature.

---

#### 8. Health Endpoints (4 endpoints, partial gap)
**Missing Endpoints:**
```
GET    /health/
GET    /health/detailed
GET    /health/graphiti
GET    /health/live
GET    /health/qdrant
GET    /health/ready
GET    /health/redis
```

**Status:** Partially connected (/health, /health/containers, /health/metrics).

**Action:** Health endpoints are primarily for ops/monitoring - UI not critical.

---

#### 9. Auth Endpoints (3 endpoints, partial gap)
**Missing Endpoints:**
```
GET    /auth/me
POST   /auth/refresh
POST   /auth/register
```

**Status:** /auth/login and /auth/logout are connected.

**Note:** /auth/me and /auth/refresh may be called programmatically (lib/api.ts).

**Action:** Verify usage - may not need UI buttons.

---

## Frontend Pages WITHOUT Corresponding Endpoints

### Orphaned Pages (Need Investigation)
- `/dashboard/costs` - Duplicate of `/admin/costs`?
- `/admin/legacy` - Old admin page still linked?

### Pages with Partial API Coverage
- `/admin/domain-training` - Page exists but 13 endpoints unused!
  - DomainTrainingPage.tsx may be outdated or incomplete

---

## Root Cause Analysis

### Why So Many Gaps?

1. **Backend-First Development:**
   - Many features built API-first without immediate UI
   - Intended for future UI or programmatic access

2. **Admin Features:**
   - Power-user/ops features built but not prioritized for UI
   - Example: Ingestion job monitoring, MCP server management

3. **API Evolution:**
   - New endpoints added (Sprint 70: MCP, Tool Use) without UI
   - Old endpoints deprecated but not removed (graph-analytics)

4. **Domain Training Gap:**
   - Frontend page exists but endpoints not wired up
   - Possible disconnect between backend and frontend teams

---

## Recommendations for Sprint 71

### Priority 1 (MUST FIX - 13 SP)
- [x] **71.8** Ingestion Job Monitoring UI (5 SP)
- [x] **71.9** MCP Tool Management UI (3 SP)
- [x] **71.10** Memory Management UI (2 SP)
- [x] Audit DomainTrainingPage and wire up 13 endpoints (3 SP)

### Priority 2 (SHOULD FIX - Future Sprints)
- [ ] Graph Community Comparison UI
- [ ] Direct Retrieval Testing UI (for developers)

### Priority 3 (EVALUATE & REMOVE - Dead Code)
- [x] **71.11** Remove graph-analytics/* endpoints (deprecated)
- [ ] Remove duplicate health endpoints
- [ ] Remove unused example endpoints from dependencies.py

---

## Success Metrics

**Before Sprint 71:**
- Gap Rate: 72% (108/150 endpoints without UI)

**After Sprint 71 (Target):**
- Gap Rate: <25% (40/150 endpoints without UI)
- Critical gaps closed: 100% (Ingestion Jobs, MCP, Memory)
- Deprecated endpoints removed: 100% (graph-analytics)

---

## API-Frontend Mapping Table

### Fully Connected Categories
| Category | Total | Connected | Gap % |
|----------|-------|-----------|-------|
| Chat & Sessions | 15 | 12 | 20% ✅ |
| Admin - LLM | 5 | 5 | 0% ✅ |
| Admin - Tools | 2 | 1 | 50% |
| Research | 2 | 2 | 0% ✅ |
| Graph Viz | 5 | 5 | 0% ✅ |
| Temporal | 6 | 5 | 17% ✅ |

### Partially Connected Categories
| Category | Total | Connected | Gap % |
|----------|-------|-----------|-------|
| Admin - Indexing | 18 | 11 | 39% |
| Admin - Pipeline | 2 | 1 | 50% |
| Health | 10 | 3 | 70% |
| Auth | 5 | 2 | 60% |

### Completely Disconnected Categories ⚠️
| Category | Total | Connected | Gap % |
|----------|-------|-----------|-------|
| Domain Training | 13 | 0 | 100% 🔴 |
| MCP | 7 | 0 | 100% 🔴 |
| Admin - Ingestion Jobs | 6 | 0 | 100% 🔴 |
| Graph Analytics | 6 | 0 | 100% 🔴 |
| Retrieval | 6 | 0 | 100% 🔴 |
| Memory | 5 | 0 | 100% 🔴 |
| Analytics | 1 | 0 | 100% 🔴 |
| Annotations | 2 | 0 | 100% 🔴 |

---

## Conclusion

Sprint 71 will focus on closing the **most critical gaps** (Ingestion Jobs, MCP, Memory) and **removing dead code** (graph-analytics). This will reduce the gap rate from **72% to ~25%** and provide users with essential admin features.

**Next Steps:**
1. Implement Features 71.8-71.10 (UI for critical gaps)
2. Audit and wire up DomainTrainingPage
3. Remove deprecated graph-analytics endpoints
4. Document remaining gaps for future sprints
