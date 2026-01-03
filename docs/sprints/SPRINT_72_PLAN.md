# Sprint 72: API-Frontend Gap Closure

**Status:** PLANNED
**Branch:** `sprint-72-gap-closure`
**Start Date:** 2026-01-06 (nach Sprint 71)
**Estimated Duration:** 6–8 Tage
**Total Story Points:** 55 SP

---

## Sprint Overview

Sprint 72 schließt **kritische API-Frontend Gaps** durch UI-Implementierung für existierende Backend-Endpoints:

- **MCP Tool Management UI** (Prio 1) - Admins können MCP Server verwalten
- **Domain Training UI Completion** (Prio 1) - Wire up missing endpoints
- **Memory Management UI** (Prio 1) - Admin-facing memory debugging tools
- **Dead Code Removal** (Prio 1) - graph-analytics/* deprecation
- **E2E Test Completion** (Prio 1) - 100% pass rate target

**Note:** mem0 Layer 0 Integration deferred to Sprint 73+ (siehe TD-081)

**Voraussetzung:**
Sprint 71 abgeschlossen (SearchableSelect, API endpoints, E2E tests stable)

**Gap Closure Target:**
- Before Sprint 72: **72% endpoints without UI** (108/150)
- After Sprint 72: **~60% endpoints without UI** (goal: 90/150)
- **Improvement:** ~12 percentage points (18 endpoints connected)

---

## Feature Overview

| # | Feature | SP | Priority | Parallelisierbar |
|---|--------|----|----------|------------------|
| 72.1 | MCP Tool Management UI | 13 | P0 | Ja (Frontend) |
| 72.2 | Domain Training UI Completion | 8 | P0 | Ja |
| 72.3 | Memory Management UI | 8 | P0 | Ja |
| 72.4 | Dead Code Removal (graph-analytics/*) | 3 | P1 | Ja |
| 72.5 | API-Frontend Gap Analysis Update | 2 | P1 | Ja |
| 72.6 | E2E Test Completion | 13 | P1 | Nach 72.1-72.3 |
| 72.7 | Documentation Update | 5 | P2 | Ja |
| 72.8 | Performance Benchmarking | 3 | P2 | Ja |

**Total: 55 SP**

---

## Feature Details

### Feature 72.1: MCP Tool Management UI (13 SP)

**Priority:** P0
**Ziel:** Admin UI für MCP Server Management (connect/disconnect, tool execution testing).

**Related:** Feature 71.9 (MCP Tool Framework Backend)

**Scope:**
- `/admin/tools` page expansion
- MCP server list with status (connected/disconnected)
- Connect/disconnect buttons
- Tool execution test panel
- Real-time server health monitoring

**Neue Dateien:**
```
frontend/src/pages/admin/MCPToolsPage.tsx     # 280 lines
frontend/src/components/admin/
├── MCPServerList.tsx                          # 180 lines
├── MCPServerCard.tsx                          # 120 lines
├── MCPToolExecutionPanel.tsx                  # 220 lines
└── MCPHealthMonitor.tsx                       # 100 lines
frontend/e2e/tests/admin/
└── mcp-tools.spec.ts                          # 15 E2E tests
```

**Backend Endpoints (bereits vorhanden):**
```
✅ GET  /mcp/health
✅ GET  /mcp/servers
✅ POST /mcp/servers/{server_name}/connect
✅ POST /mcp/servers/{server_name}/disconnect
✅ GET  /mcp/tools
✅ GET  /mcp/tools/{tool_name}
✅ POST /mcp/tools/{tool_name}/execute
```

**Acceptance Criteria:**
- [ ] `/admin/tools` page displays all MCP servers
- [ ] Connect/disconnect buttons functional
- [ ] Tool execution panel allows testing individual tools
- [ ] Health monitor shows real-time status (green/red/yellow)
- [ ] Error handling for failed connections
- [ ] E2E tests: 15/15 passing

---

### Feature 72.2: Domain Training UI Completion (8 SP)

**Priority:** P1
**Ziel:** Wire up missing endpoints für Features 71.13-71.15 (Data Augmentation, Batch Upload, Domain Details).

**Related:** Sprint 71 Features 71.13-71.15

**Scope:**
- Connect `DataAugmentationDialog` to `/domain-training/augment`
- Connect `BatchDocumentUploadDialog` to `/domain-training/ingest-batch`
- Connect `DomainDetailDialog` to `/domain-training/{domain_name}` (GET)
- Wire up validation, reindex, training-status endpoints
- E2E test fixes (18 skipped → passing)

**Modified Files:**
```
frontend/src/components/admin/
├── DataAugmentationDialog.tsx           # +API integration (50 lines changed)
├── BatchDocumentUploadDialog.tsx        # +API integration (60 lines changed)
├── DomainDetailDialog.tsx               # +GET endpoint (40 lines changed)
└── DomainList.tsx                       # +action buttons (30 lines changed)
frontend/src/api/admin.ts                # +5 new API functions (100 lines)
frontend/e2e/tests/admin/
└── domain-training-new-features.spec.ts # Un-skip 18 tests
```

**Acceptance Criteria:**
- [ ] Data augmentation generates samples via API
- [ ] Batch document upload starts ingestion job
- [ ] Domain details dialog shows full info (LLM model, metrics, prompts)
- [ ] E2E tests: 19/19 passing (0 skipped)

---

### Feature 72.3: Memory Management UI (8 SP)

**Priority:** P1
**Ziel:** Admin-facing UI für Memory debugging and management.

**Related:** TD-051-MEMORY-CONSOLIDATION-PIPELINE.md, Feature 71.10

**Scope:**
- `/admin/memory` page creation
- Memory stats dashboard (Redis, Qdrant, Graphiti)
- Search memory by user/session
- Manual consolidation trigger
- Memory export (JSON download)

**Neue Dateien:**
```
frontend/src/pages/admin/MemoryManagementPage.tsx  # 240 lines
frontend/src/components/admin/
├── MemoryStatsCard.tsx                             # 120 lines
├── MemorySearchPanel.tsx                           # 180 lines
└── ConsolidationControl.tsx                        # 100 lines
frontend/e2e/tests/admin/
└── memory-management.spec.ts                       # 10 E2E tests
```

**Backend Endpoints (bereits vorhanden):**
```
✅ POST /memory/consolidate
✅ POST /memory/search
✅ GET  /memory/session/{session_id}
✅ GET  /memory/stats
✅ POST /memory/temporal/point-in-time
```

**Acceptance Criteria:**
- [ ] Memory stats displayed (keys, size, hit rate)
- [ ] Search finds memories by user/session
- [ ] Manual consolidation button triggers background job
- [ ] Memory export downloads JSON
- [ ] E2E tests: 10/10 passing

---

### Feature 72.4: Dead Code Removal (3 SP)

**Priority:** P1
**Ziel:** Deprecate and remove `graph-analytics/*` endpoints (replaced by `graph/viz/*`).

**Related:** API-Frontend Gap Analysis (Sprint 71.8-71.10)

**Scope:**
- Mark 6 endpoints as DEPRECATED
- Add migration guide in docs
- Remove routes from FastAPI (if no usage detected)
- Update frontend to use new endpoints

**Deprecated Endpoints:**
```
❌ GET /graph-analytics/communities
❌ GET /graph-analytics/clusters
❌ GET /graph-analytics/centrality
❌ GET /graph-analytics/similarity
❌ GET /graph-analytics/temporal-analysis
❌ POST /graph-analytics/query
```

**Replaced by:**
```
✅ GET /api/v1/graph/viz/communities
✅ GET /api/v1/graph/viz/clusters
✅ ... (modern endpoints)
```

**Acceptance Criteria:**
- [ ] Deprecation warnings logged when old endpoints called
- [ ] Migration guide published
- [ ] No frontend code uses old endpoints
- [ ] All tests updated to new endpoints

---

### Feature 72.5: API-Frontend Gap Analysis Update (2 SP)

**Priority:** P1
**Ziel:** Update gap analysis document with Sprint 72 progress.

**Scope:**
- Recalculate gap percentage
- Document newly connected endpoints
- Identify remaining gaps for Sprint 73

**Expected Result:**
- Gap Rate: **72%** (Sprint 71) → **<50%** (Sprint 72)
- Document: `docs/sprints/SPRINT_72_API_FRONTEND_GAP_CLOSURE.md`

---

### Feature 72.6: E2E Test Completion (13 SP)

**Priority:** P1
**Ziel:** Complete E2E test coverage for Sprint 72 features.

**Scope:**
- MCP Tools UI tests (15 tests)
- Domain Training UI tests (18 tests → un-skip)
- Memory Management tests (10 tests)
- mem0 integration tests (8 tests - if Frontend UI implemented)

**Target:**
- E2E Pass Rate: **96%** (Sprint 71) → **100%** (Sprint 72)

---

### Feature 72.7: Documentation Update (5 SP)

**Priority:** P2
**Ziel:** Update docs for Sprint 72 changes.

**New Docs:**
```
docs/components/
└── MEMORY_MEM0_INTEGRATION.md       # 400 lines
docs/user-guides/
└── MCP_TOOLS_ADMIN_GUIDE.md         # 300 lines
docs/sprints/
└── SPRINT_72_API_FRONTEND_GAP_CLOSURE.md  # Gap analysis update
```

**Updated Docs:**
```
src/components/memory/README.md      # +mem0 Layer 0 section
docs/ARCHITECTURE.md                 # +4-layer memory diagram
docs/TECH_STACK.md                   # +mem0 dependency
```

---

### Feature 72.8: Performance Benchmarking (3 SP)

**Priority:** P2
**Ziel:** Benchmark MCP Tools + Memory Management UI performance impact.

**Metrics:**
- MCP tool execution latency (target: <5s p95)
- Memory stats page load time (target: <500ms)
- Memory search query latency (target: <200ms)
- Manual consolidation execution time

**Deliverable:** `docs/performance/SPRINT_72_BENCHMARKS.md`

---

## Parallel Execution Strategy

### Wave 1 (Tag 1-2, parallel)
- 72.1 MCP Tool Management UI (Frontend)
- 72.2 Domain Training UI Completion
- 72.4 Dead Code Removal

### Wave 2 (Tag 3-4, parallel)
- 72.3 Memory Management UI
- 72.5 API-Frontend Gap Analysis Update

### Wave 3 (Tag 5-6, parallel)
- 72.6 E2E Test Completion
- 72.7 Documentation Update
- 72.8 Performance Benchmarking

### Wave 4 (Tag 7-8)
- Integration Testing
- Docker Container Rebuild
- Production Deployment Prep

---

## Security & Privacy Notes

- MCP tool execution requires admin authentication
- Memory export limited to admin users + session owners
- Dead code removal requires migration path documentation

---

## Definition of Done (Sprint 72)

- [ ] **MCP Tools UI:** `/admin/tools` functional, 15 E2E tests passing
- [ ] **Domain Training:** All missing endpoints connected, 19 E2E tests passing
- [ ] **Memory Management UI:** `/admin/memory` functional, 10 E2E tests passing
- [ ] **Dead Code Removal:** 6 deprecated endpoints documented + warnings added
- [ ] **Gap Analysis:** Updated document shows ~60% gap rate
- [ ] **E2E Tests:** 100% pass rate (all skipped tests now passing)
- [ ] **Documentation:** User guides published
- [ ] **Performance:** MCP tools <5s p95, Memory UI <500ms load time

---

## Rollback Plan

**If MCP UI breaks:**
1. Backend endpoints remain functional (no impact on agents)
2. Rollback frontend deployment only

**If Memory Management UI breaks:**
1. Core memory functionality unaffected
2. Rollback frontend deployment only

---

## Success Metrics

**Gap Closure:**
- Gap Rate: **72% → ~60%** (~12 percentage points improvement)
- Endpoints Connected: 18 endpoints (MCP, Domain Training, Memory)

**E2E Test Coverage:**
- Pass Rate: **96% → 100%** (all skipped tests resolved)

**Admin Experience:**
- MCP Tools manageable via UI (no more SSH + curl)
- Memory debugging via UI (no more Neo4j browser)
- Domain Training fully functional (no skipped tests)

---

**END OF SPRINT 72 PLAN**
