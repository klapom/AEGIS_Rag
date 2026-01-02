# Sprint 71: Comprehensive E2E Testing & Code Quality

**Sprint:** 71
**Duration:** 5 days
**Total Story Points:** 40 SP
**Focus:** Complete E2E test coverage + API-Frontend gap closure + Dead code removal

---

## 🎯 Sprint Goals

1. **100% User Journey Coverage:** E2E tests for EVERY feature with Playwright
2. **API-Frontend Gap Analysis:** Identify and close critical gaps (76 endpoints without UI!)
3. **Dead Code Detection:** Remove unused components, endpoints, and code
4. **Test Infrastructure:** Improve test reliability and execution speed

---

## 📊 Current State Analysis

### E2E Test Coverage (Before Sprint 71)
- **Existing Tests:** ~7 E2E spec files
- **Coverage:** Partial (mainly chat, search, admin basics)
- **Missing:** Tool use, MCP, memory, temporal, graph analytics, domain training

### API-Frontend Gaps (Discovered)
- **Total Backend Endpoints:** 150
- **Frontend-Connected Endpoints:** 42 (28%)
- **Gaps (No UI):** 108 (72%!)

**Critical Gaps by Category:**
- Domain Training: 13 endpoints (100% without UI)
- MCP (Tool Framework): 7 endpoints (100% without UI)
- Admin - Ingestion Jobs: 6 endpoints (100% without UI)
- Graph Analytics: 6 endpoints (100% without UI)
- Retrieval: 6 endpoints (100% without UI)
- Memory: 5 endpoints (80% without UI)

### Code Quality Issues
- Potential dead code in old router files (graph_analytics.py, graph_visualization.py)
- Unused dependencies in pyproject.toml
- Frontend components without API connections
- Test files without actual tests

---

## 🗂️ Feature Breakdown

### Phase 1: Complete E2E User Journey Testing (25 SP)

#### 71.1 Core Chat & Search E2E Tests (5 SP)
**Priority:** 🔴 CRITICAL

**User Journeys to Test:**
- [x] Basic chat message (already exists)
- [ ] Maximum Hybrid Search (4 signals: Vector + BM25 + Graph Local + Graph Global)
- [ ] Follow-up questions generation
- [ ] Conversation history loading
- [ ] Session archiving
- [ ] Conversation sharing (public link)
- [ ] Real-time phase events display
- [ ] Streaming answer display with citations

**Deliverables:**
- `frontend/e2e/tests/chat/maximum-hybrid-search.spec.ts`
- `frontend/e2e/tests/chat/follow-up-questions.spec.ts`
- `frontend/e2e/tests/chat/conversation-history.spec.ts`
- `frontend/e2e/tests/chat/session-archive.spec.ts`
- `frontend/e2e/tests/chat/phase-events-realtime.spec.ts`

---

#### 71.2 Deep Research E2E Tests (3 SP)
**Priority:** 🔴 CRITICAL

**User Journeys to Test:**
- [ ] Deep Research multi-turn query (planner → searcher → supervisor → synthesizer)
- [ ] Research report generation with citations
- [ ] Deep Research with tool use (ReAct pattern)
- [ ] Deep Research health check

**Deliverables:**
- `frontend/e2e/tests/research/deep-research-multi-turn.spec.ts`
- `frontend/e2e/tests/research/research-with-tools.spec.ts`

---

#### 71.3 Tool Use & MCP E2E Tests (5 SP)
**Priority:** 🔴 CRITICAL (Sprint 70 feature)

**User Journeys to Test:**
- [ ] Tool detection (markers, LLM-based, hybrid)
- [ ] Tool execution in normal chat (ReAct cycle)
- [ ] Tool execution in deep research
- [ ] Admin toggle for tool enablement
- [ ] Tool result phase events streaming
- [ ] Playwright MCP tool execution (browser automation)
- [ ] MCP server health check

**Deliverables:**
- `frontend/e2e/tests/tools/tool-detection.spec.ts`
- `frontend/e2e/tests/tools/tool-execution-chat.spec.ts`
- `frontend/e2e/tests/tools/tool-execution-research.spec.ts`
- `frontend/e2e/tests/tools/admin-tool-toggle.spec.ts`
- `frontend/e2e/tests/tools/mcp-playwright.spec.ts`

---

#### 71.4 Admin - Indexing & Ingestion E2E Tests (4 SP)
**Priority:** 🟡 MEDIUM

**User Journeys to Test:**
- [ ] Document upload with domain classification
- [ ] Batch indexing
- [ ] Re-indexing with VLM metadata
- [ ] Ingestion job monitoring (NEW - no UI yet!)
- [ ] Job cancellation
- [ ] Job error logs viewing
- [ ] Pipeline config management
- [ ] Pipeline preset selection
- [ ] Index consistency validation

**Deliverables:**
- `frontend/e2e/tests/admin/document-upload-domain-classification.spec.ts`
- `frontend/e2e/tests/admin/batch-indexing.spec.ts`
- `frontend/e2e/tests/admin/re-indexing-vlm.spec.ts`
- `frontend/e2e/tests/admin/ingestion-job-monitoring.spec.ts` (NEW UI NEEDED)
- `frontend/e2e/tests/admin/pipeline-config.spec.ts`

---

#### 71.5 Domain Training E2E Tests (3 SP)
**Priority:** 🟡 MEDIUM

**User Journeys to Test:**
- [ ] Domain creation wizard (config → dataset → training)
- [ ] Training progress streaming (SSE)
- [ ] Domain stats viewing
- [ ] Domain validation
- [ ] Domain reindexing
- [ ] Query classification with trained domain
- [ ] Dataset augmentation
- [ ] Training model selection

**Deliverables:**
- `frontend/e2e/tests/domain-training/domain-creation-wizard.spec.ts`
- `frontend/e2e/tests/domain-training/training-progress-sse.spec.ts`
- `frontend/e2e/tests/domain-training/domain-validation.spec.ts`
- `frontend/e2e/tests/domain-training/query-classification.spec.ts`

---

#### 71.6 Graph Visualization & Temporal E2E Tests (3 SP)
**Priority:** 🟡 MEDIUM

**User Journeys to Test:**
- [ ] Entity graph visualization
- [ ] Community graph visualization
- [ ] Subgraph querying
- [ ] Graph export (JSON, GraphML)
- [ ] Entity version history (temporal)
- [ ] Version comparison
- [ ] Version revert
- [ ] Point-in-time query
- [ ] Entity changelog viewing

**Deliverables:**
- `frontend/e2e/tests/graph/entity-visualization.spec.ts`
- `frontend/e2e/tests/graph/community-visualization.spec.ts`
- `frontend/e2e/tests/graph/graph-export.spec.ts`
- `frontend/e2e/tests/graph/entity-version-history.spec.ts`
- `frontend/e2e/tests/graph/point-in-time-query.spec.ts`

---

#### 71.7 Memory & Consolidation E2E Tests (2 SP)
**Priority:** 🟢 LOW

**User Journeys to Test:**
- [ ] Memory search (semantic search in Graphiti)
- [ ] Memory consolidation (merge related entities)
- [ ] Session memory retrieval
- [ ] Temporal point-in-time memory query
- [ ] Memory stats viewing

**Deliverables:**
- `frontend/e2e/tests/memory/memory-search.spec.ts`
- `frontend/e2e/tests/memory/memory-consolidation.spec.ts`
- `frontend/e2e/tests/memory/session-memory.spec.ts`

---

### Phase 2: API-Frontend Gap Closure (10 SP)

#### 71.8 Ingestion Job Monitoring UI (5 SP)
**Priority:** 🔴 CRITICAL

**Problem:** 6 ingestion job endpoints have NO UI!

**Solution:**
Create new Admin page `/admin/jobs` with:
- Job list table (status, progress, duration)
- Job detail view (logs, errors, events)
- Cancel job button
- Real-time progress updates (SSE or polling)
- Filter by status (pending, running, completed, failed)

**Deliverables:**
- `frontend/src/pages/admin/IngestionJobsPage.tsx`
- `frontend/src/components/admin/JobListTable.tsx`
- `frontend/src/components/admin/JobDetailModal.tsx`
- `frontend/src/api/jobs.ts` (API client)
- `frontend/e2e/tests/admin/ingestion-jobs-ui.spec.ts`

---

#### 71.9 MCP Tool Management UI (3 SP)
**Priority:** 🟡 MEDIUM

**Problem:** 7 MCP endpoints have NO UI!

**Solution:**
Extend Admin page `/admin/tools` with:
- MCP server list (status, tools count)
- Connect/disconnect server buttons
- Tool list per server
- Tool execution test panel
- Health status monitoring

**Deliverables:**
- `frontend/src/components/admin/MCPServerList.tsx`
- `frontend/src/components/admin/MCPToolList.tsx`
- `frontend/src/components/admin/MCPToolTestPanel.tsx`
- `frontend/src/api/mcp.ts` (API client)
- `frontend/e2e/tests/admin/mcp-tool-management.spec.ts`

---

#### 71.10 Memory Management UI (2 SP)
**Priority:** 🟢 LOW

**Problem:** 5 memory endpoints have NO UI!

**Solution:**
Create new page `/admin/memory` with:
- Memory stats dashboard
- Search interface
- Consolidation trigger button
- Session memory viewer

**Deliverables:**
- `frontend/src/pages/admin/MemoryManagementPage.tsx`
- `frontend/src/components/admin/MemoryStatsPanel.tsx`
- `frontend/src/components/admin/MemorySearchPanel.tsx`
- `frontend/src/api/memory.ts` (API client)
- `frontend/e2e/tests/admin/memory-management-ui.spec.ts`

---

### Phase 3: Dead Code Detection & Removal (5 SP)

#### 71.11 Backend Dead Code Analysis (2 SP)
**Priority:** 🟡 MEDIUM

**Strategy:**
1. **Coverage Analysis:**
   ```bash
   poetry run pytest --cov=src --cov-report=html --cov-report=term-missing
   ```
   - Identify untested modules (likely dead)
   - Highlight never-executed code paths

2. **Static Analysis:**
   ```bash
   poetry add vulture  # Dead code detector
   vulture src/ --min-confidence 80
   ```

3. **Import Analysis:**
   ```python
   # Find unused imports
   poetry add autoflake
   autoflake --check --remove-all-unused-imports --recursive src/
   ```

4. **API Endpoint Usage:**
   - Cross-reference 150 backend endpoints with frontend usage
   - Identify endpoints never called (108 candidates!)
   - Check logs for actual production usage

**Candidates for Removal:**
- Old graph_analytics.py router (6 endpoints, replaced by graph_viz.py)
- Duplicate health endpoints (7 health/* endpoints)
- Unused auth endpoints (/auth/refresh, /auth/register if not used)
- Dependencies.py example endpoints (/risky, /recommendations, etc.)

**Deliverables:**
- `docs/technical-debt/TD_DEAD_CODE_ANALYSIS.md`
- PR with dead code removal

---

#### 71.12 Frontend Dead Code Analysis (2 SP)
**Priority:** 🟡 MEDIUM

**Strategy:**
1. **Unused Exports:**
   ```bash
   npx ts-prune  # Find unused exports
   ```

2. **Unused Dependencies:**
   ```bash
   npx depcheck  # Find unused npm packages
   ```

3. **Component Usage:**
   - Analyze component imports with ts-morph
   - Identify components never imported

4. **Route Analysis:**
   - Check if all routes in App.tsx are reachable
   - Identify orphaned pages

**Candidates for Removal:**
- Duplicate routes (/dashboard/costs = /admin/costs)
- Legacy admin page (/admin/legacy)
- Test-only components in production build
- Unused icons/assets

**Deliverables:**
- `docs/technical-debt/TD_FRONTEND_DEAD_CODE.md`
- PR with dead code removal

---

#### 71.13 Dependency Audit & Cleanup (1 SP)
**Priority:** 🟢 LOW

**Strategy:**
1. **Python Dependencies:**
   ```bash
   poetry show --tree  # Analyze dependency tree
   poetry show --outdated  # Check for updates
   ```
   - Remove unused packages from pyproject.toml
   - Update to latest compatible versions
   - Run tests after each removal

2. **TypeScript Dependencies:**
   ```bash
   npm outdated
   npm audit
   ```
   - Remove unused packages from package.json
   - Update to latest compatible versions
   - Check bundle size impact

**Deliverables:**
- Updated pyproject.toml (cleaned)
- Updated package.json (cleaned)
- Dependency audit report

---

## 🧪 Test Infrastructure Improvements

### Test Execution Speed
- Parallelize Playwright tests (sharding)
- Mock external services (Ollama, Docling) in E2E when possible
- Use test fixtures for common setup

### Test Reliability
- Add retry logic for flaky tests
- Improve wait strategies (wait for network idle)
- Add better error messages for debugging

### CI/CD Integration
- Run E2E tests in GitHub Actions
- Generate Playwright HTML report
- Fail PR if critical E2E tests fail

---

## 📈 Success Criteria

### E2E Test Coverage
- [x] 100% of user journeys have E2E tests
- [x] All Sprint 70 features tested (Deep Research, Tool Use)
- [x] All admin pages tested
- [x] Critical paths have >95% pass rate

### API-Frontend Gaps
- [x] <20% of API endpoints without UI (down from 72%)
- [x] All critical gaps closed (Ingestion Jobs, MCP, Memory)
- [x] Gap analysis document published

### Dead Code Removal
- [x] Backend test coverage >80%
- [x] Frontend unused exports removed
- [x] Dependency count reduced by >10%
- [x] No endpoints/routes unreachable

---

## 📋 Sprint Backlog

| Feature | SP | Priority | Assignee |
|---------|-----|----------|----------|
| **Phase 1: E2E Tests** | | | |
| 71.1 Core Chat & Search E2E | 5 | 🔴 CRITICAL | Team |
| 71.2 Deep Research E2E | 3 | 🔴 CRITICAL | Team |
| 71.3 Tool Use & MCP E2E | 5 | 🔴 CRITICAL | Team |
| 71.4 Admin Indexing E2E | 4 | 🟡 MEDIUM | Team |
| 71.5 Domain Training E2E | 3 | 🟡 MEDIUM | Team |
| 71.6 Graph & Temporal E2E | 3 | 🟡 MEDIUM | Team |
| 71.7 Memory E2E | 2 | 🟢 LOW | Team |
| **Phase 2: Gap Closure** | | | |
| 71.8 Ingestion Job Monitoring UI | 5 | 🔴 CRITICAL | Frontend |
| 71.9 MCP Tool Management UI | 3 | 🟡 MEDIUM | Frontend |
| 71.10 Memory Management UI | 2 | 🟢 LOW | Frontend |
| **Phase 3: Dead Code** | | | |
| 71.11 Backend Dead Code Analysis | 2 | 🟡 MEDIUM | Backend |
| 71.12 Frontend Dead Code Analysis | 2 | 🟡 MEDIUM | Frontend |
| 71.13 Dependency Audit | 1 | 🟢 LOW | Infrastructure |
| **Total** | **40 SP** | | |

---

## 🛠️ Technical Approach

### E2E Test Organization
```
frontend/e2e/
├── tests/
│   ├── chat/
│   │   ├── maximum-hybrid-search.spec.ts
│   │   ├── follow-up-questions.spec.ts
│   │   └── phase-events-realtime.spec.ts
│   ├── research/
│   │   ├── deep-research-multi-turn.spec.ts
│   │   └── research-with-tools.spec.ts
│   ├── tools/
│   │   ├── tool-detection.spec.ts
│   │   ├── tool-execution-chat.spec.ts
│   │   └── mcp-playwright.spec.ts
│   ├── admin/
│   │   ├── ingestion-job-monitoring.spec.ts
│   │   ├── pipeline-config.spec.ts
│   │   └── mcp-tool-management.spec.ts
│   ├── domain-training/
│   │   ├── domain-creation-wizard.spec.ts
│   │   └── training-progress-sse.spec.ts
│   ├── graph/
│   │   ├── entity-visualization.spec.ts
│   │   └── entity-version-history.spec.ts
│   └── memory/
│       ├── memory-search.spec.ts
│       └── memory-consolidation.spec.ts
├── fixtures/
│   ├── test-documents/
│   ├── test-datasets/
│   └── mock-responses/
└── utils/
    ├── api-helpers.ts
    ├── auth-helpers.ts
    └── wait-helpers.ts
```

### Dead Code Detection Tools
**Backend:**
- `vulture` - Dead code detector
- `autoflake` - Unused import remover
- `coverage.py` - Test coverage analysis

**Frontend:**
- `ts-prune` - Unused exports detector
- `depcheck` - Unused dependency checker
- `webpack-bundle-analyzer` - Bundle size analysis

### API-Frontend Gap Closure Strategy
1. **Prioritize by Impact:**
   - Critical: Ingestion Jobs (6 endpoints) - User needs job monitoring
   - Medium: MCP Tools (7 endpoints) - Admin needs tool management
   - Low: Memory (5 endpoints) - Power-user feature

2. **Incremental Approach:**
   - Build UI components incrementally
   - E2E test each new page
   - Deploy behind feature flag if risky

---

## 🎯 Definition of Done

### For Each E2E Test
- [x] Test file created with clear test case name
- [x] Test covers complete user journey (login → action → verification)
- [x] Test passes consistently (3 consecutive runs)
- [x] Test uses proper Playwright best practices (no hard-coded waits)
- [x] Test has clear assertion messages
- [x] Test is documented in TEST_CASES.md

### For API-Frontend Gap Closure
- [x] Frontend UI component created
- [x] API client method implemented
- [x] E2E test passing
- [x] Documentation updated
- [x] No console errors

### For Dead Code Removal
- [x] Code identified as unused (tools + manual verification)
- [x] Tests still pass after removal
- [x] No production logs showing usage
- [x] PR reviewed and approved

---

## 🚀 Sprint Execution Plan

### Day 1 (Phase 1 Start)
- Morning: Sprint planning, setup E2E test infrastructure
- Afternoon: Start 71.1 (Core Chat & Search E2E) + 71.2 (Deep Research E2E)

### Day 2 (Phase 1 Continue)
- Morning: Complete 71.1 + 71.2
- Afternoon: Start 71.3 (Tool Use & MCP E2E) - critical Sprint 70 feature

### Day 3 (Phase 1 Finish + Phase 2 Start)
- Morning: Complete 71.3, start 71.4 (Admin Indexing E2E)
- Afternoon: Start 71.8 (Ingestion Job Monitoring UI) - parallel Frontend work

### Day 4 (Phase 2 + Phase 3)
- Morning: Complete 71.8, start 71.9 (MCP Tool Management UI)
- Afternoon: Start 71.11 (Backend Dead Code Analysis)

### Day 5 (Finish + Documentation)
- Morning: Complete remaining features, run full test suite
- Afternoon: Sprint retrospective, documentation, Sprint 72 planning

---

## 📚 References

- [USER_JOURNEYS_AND_TEST_PLAN.md](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md)
- [API-FRONTEND-GAP-ANALYSIS.md](./SPRINT_71_API_FRONTEND_GAP_ANALYSIS.md) (TO CREATE)
- [DEAD_CODE_ANALYSIS.md](../technical-debt/TD_DEAD_CODE_ANALYSIS.md) (TO CREATE)
- Playwright Documentation: https://playwright.dev/
- Vulture (Dead Code Detector): https://github.com/jendrikseipp/vulture
- ts-prune: https://github.com/nadeesha/ts-prune

---

## 🎉 Sprint 71 Success Vision

**After Sprint 71:**
- ✅ **Every user journey** has automated E2E tests
- ✅ **Critical API-Frontend gaps** closed (Ingestion Jobs, MCP Tools)
- ✅ **Dead code removed** - cleaner, faster codebase
- ✅ **Test coverage** >80% backend, >90% E2E critical paths
- ✅ **Confidence** to ship features knowing they work end-to-end
- ✅ **Maintenance burden** reduced - no unused code/dependencies

**Ready for Sprint 72:** Feature development with solid testing foundation!
