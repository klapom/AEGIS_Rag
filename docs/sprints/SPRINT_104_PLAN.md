# Sprint 104 Plan: E2E Production Readiness (90%+ Pass Rate)

**Sprint Duration:** 2026-01-16 → 2026-01-17
**Total Story Points:** 25 SP
**Status:** 📝 Planned
**Priority:** P0 (Production Readiness)

---

## Sprint Goal

**Achieve 93%+ E2E Pass Rate** (180/194 tests) by fixing ALL blocked groups, ALL partial groups, AND all easy wins.

**Current State (Sprint 103):**
- ✅ 107/194 tests passing (56%)
- ❌ 81/194 tests failing (43%)
- ⏭️ 6/194 tests skipped (3%)

**Target State (Sprint 104):**
- ✅ 180+/194 tests passing (93%+)
- ❌ <15/194 tests failing (<8%)
- 🎯 Production-ready full-stack system

---

## Executive Summary

Sprint 104 fokussiert auf die **kritischen Blocker** aus Sprint 103:

### Critical Issues (0% Pass Rate Groups)
- **Group 4 (Browser Tools):** 0/6 tests - Frontend UI fehlt komplett
- **Group 5 (Skills Management):** 0/8 tests - Frontend UI fehlt komplett
- **Group 6 (Skills Using Tools):** 0/9 tests - Frontend-Backend Integration fehlt

### High Priority Issues (<30% Pass Rate)
- **Group 7 (Memory Management):** 3/15 tests (20%) - Component-Struktur mismatch
- **Group 13 (Agent Hierarchy):** 2/8 tests (25%) - Sprint 95 UI unvollständig
- **Group 14 (GDPR/Audit):** 3/14 tests (21%) - Sprint 100 API Contract fixes unvollständig
- **Group 15 (Explainability):** 4/13 tests (31%) - UI-Backend Integration fehlt

### Medium Priority Issues (30-70% Pass Rate)
- **Group 1 (MCP Tools):** 13/19 tests (68%) - Einzelne Test-IDs fehlen
- **Group 10 (Hybrid Search):** 5/13 tests (38%) - Mock-Daten Format mismatch

---

## Sprint Features

### Phase 1: Browser & Skills Frontend UI (8 SP)

#### Feature 104.1: Browser Tools Management UI (3 SP)
**Problem:** Group 4 hat 0% pass rate - keine UI vorhanden

**Deliverables:**
1. `frontend/src/pages/admin/BrowserToolsPage.tsx` (NEW)
   - Browser Tools Liste mit Status (active/idle/error)
   - "Navigate to URL" Tool UI
   - "Take Screenshot" Tool UI
   - "Execute JavaScript" Tool UI
   - Browser session management (start/stop/restart)

2. Test IDs:
   - `browser-tools-page`
   - `browser-tool-navigate`, `browser-tool-screenshot`, `browser-tool-evaluate`
   - `browser-session-status`, `browser-start-btn`, `browser-stop-btn`

3. Integration:
   - API: `POST /api/v1/mcp/tools/browser_{tool}/execute`
   - Real-time session status polling (5s interval)

**Acceptance Criteria:**
- ✅ 6/6 Group 4 tests passing
- ✅ Browser tools UI matches MCP backend interface
- ✅ Screenshot display in base64 PNG format

**Test Coverage:** 18 unit tests (component + API integration)

---

#### Feature 104.2: Skills Management UI (3 SP)
**Problem:** Group 5 hat 0% pass rate - UI existiert nicht

**Deliverables:**
1. `frontend/src/pages/admin/SkillsPage.tsx` (NEW)
   - Skills Registry Viewer
   - Skill Bundles (Research/Analysis/Synthesis/Development/Enterprise)
   - Individual Skill Cards (name, description, capabilities, status)
   - Skill activation/deactivation toggle

2. Test IDs:
   - `skills-page`, `skills-registry-list`
   - `skill-card-{skillName}` (e.g., `skill-card-research`, `skill-card-document-analysis`)
   - `skill-bundle-{bundleName}` (e.g., `skill-bundle-research`)
   - `skill-toggle-{skillName}`, `skill-status-{skillName}`

3. Integration:
   - API: `GET /api/v1/skills/registry` (list all skills)
   - API: `POST /api/v1/skills/{skill_name}/activate`
   - API: `POST /api/v1/skills/{skill_name}/deactivate`

**Acceptance Criteria:**
- ✅ 8/8 Group 5 tests passing
- ✅ Display 20+ skills from Sprint 95 Skill Libraries
- ✅ Bundle grouping working (5 bundles)

**Test Coverage:** 24 unit tests

---

#### Feature 104.3: Skills-Tools Integration UI (2 SP)
**Problem:** Group 6 hat 0% pass rate - Skill → Tool execution nicht sichtbar

**Deliverables:**
1. `frontend/src/components/skills/SkillExecutionPanel.tsx` (NEW)
   - Skill execution viewer
   - Tool invocation logs (which skill called which tool)
   - Execution trace: Skill → Tool → Result
   - Filter by skill type, tool type, timestamp

2. Test IDs:
   - `skill-execution-panel`
   - `execution-trace-{executionId}`
   - `skill-tool-mapping-{skillName}-{toolName}`
   - `filter-skill-type`, `filter-tool-type`

3. Integration:
   - API: `GET /api/v1/skills/executions` (execution history)
   - API: `GET /api/v1/skills/{skill_name}/tools` (which tools this skill uses)
   - WebSocket: Real-time execution updates

**Acceptance Criteria:**
- ✅ 9/9 Group 6 tests passing
- ✅ Real-time skill → tool execution visible
- ✅ Historical execution trace >100 entries

**Test Coverage:** 18 unit tests

---

### Phase 2: Admin UI Fixes (6 SP)

#### Feature 104.4: Memory Management Component Fix (2 SP)
**Problem:** Group 7 nur 20% pass rate - Component-Struktur stimmt nicht mit Tests überein

**Root Cause Analysis:**
- Test IDs vorhanden (`tab-stats`, `tab-search`, `tab-consolidation`)
- Aber: Tests können Elemente nicht finden → DOM-Struktur Problem

**Deliverables:**
1. Debug MemoryManagementPage DOM structure
   - Verify tab rendering (`<button data-testid="tab-stats">`)
   - Check conditional rendering (tabs nur bei bestimmten Zuständen?)
   - Validate component mount order

2. Fix identified issues:
   - Ensure tabs render on page load (nicht async delayed)
   - Fix CSS classes (display:none verhindert Test-Zugriff?)
   - Update tab navigation logic

3. Add missing test IDs:
   - `memory-stats-table`
   - `memory-search-input`, `memory-search-results`
   - `consolidation-trigger-btn`, `consolidation-status`

**Acceptance Criteria:**
- ✅ 14/15 Group 7 tests passing (20% → **93%**)
- ✅ All tabs clickable and render content
- ✅ Stats/Search/Consolidation features functional
- ✅ Only 1 failure remaining (edge case)

**Test Coverage:** 12 additional E2E assertions

---

#### Feature 104.5: Agent Hierarchy UI (2 SP)
**Problem:** Group 13 nur 25% pass rate - Sprint 95 UI unvollständig

**Deliverables:**
1. `frontend/src/pages/admin/AgentHierarchyPage.tsx` (UPDATE)
   - Executive → Manager → Worker hierarchy visualization
   - Agent communication trace viewer
   - Messaging bus activity monitor
   - Skill orchestration flow diagram

2. Test IDs:
   - `agent-hierarchy-tree`
   - `agent-node-executive`, `agent-node-manager-{id}`, `agent-node-worker-{id}`
   - `agent-communication-trace`
   - `messaging-bus-activity`

3. Integration:
   - API: `GET /api/v1/agents/hierarchy` (tree structure)
   - API: `GET /api/v1/agents/communications` (message history)
   - WebSocket: Real-time agent activity

**Acceptance Criteria:**
- ✅ 8/8 Group 13 tests passing (25% → **100%**)
- ✅ 3-tier hierarchy visualization working
- ✅ Real-time messaging bus activity visible
- ✅ ALL tests passing (0 failures)

**Test Coverage:** 16 unit tests

---

#### Feature 104.6: GDPR/Audit API Contract Fixes (2 SP)
**Problem:** Group 14 nur 21% pass rate - Sprint 100 Fixes unvollständig implementiert

**Sprint 100 Issues NOT Fixed:**
- Fix #2: GDPR Consents backend returns `items` ✅ (already fixed in Sprint 103)
- Fix #3: Audit Events backend returns `items` ❌ (NOT implemented)
- Fix #4: Audit Reports ISO 8601 timestamps ❌ (NOT implemented)
- Fix #6: GDPR Status mapping `granted` → `active` ✅ (already fixed in Sprint 103)

**Deliverables:**
1. **Backend Fix #3:** `src/api/v1/gdpr_audit.py`
   ```python
   # Current (WRONG):
   @router.get("/audit/events")
   async def get_audit_events():
       return {"events": [...]}  # ❌

   # Fixed (CORRECT):
   @router.get("/audit/events")
   async def get_audit_events():
       return {"items": [...]}  # ✅
   ```

2. **Backend Fix #4:** ISO 8601 timestamp format
   ```python
   # Current (WRONG):
   "timestamp": "2026-01-16 14:30:00"  # ❌

   # Fixed (CORRECT):
   "timestamp": "2026-01-16T14:30:00Z"  # ✅
   ```

3. **Frontend Update:** `AuditEventsPage.tsx`
   - Change `auditData.events` → `auditData.items`
   - Parse ISO 8601 timestamps correctly

**Acceptance Criteria:**
- ✅ 12/14 Group 14 tests passing (21% → **86%**)
- ✅ API contract matches Sprint 100 spec 100%
- ✅ No frontend-backend data format mismatches
- ✅ Only 2 failures remaining

**Test Coverage:** 8 integration tests

---

### Phase 3: Partial Group Improvements (4 SP)

#### Feature 104.7: MCP Tools Test ID Completion (2 SP)
**Problem:** Group 1 hat 68% pass rate - 6/19 tests failing wegen fehlender Test-IDs

**Deliverables:**
1. Analyze failing tests to identify missing test IDs
2. Add missing test IDs to:
   - `MCPServerList.tsx` (additional elements)
   - `MCPToolExecutionPanel.tsx` (if exists)
   - `MCPToolResultsViewer.tsx` (if exists)

3. Specific test IDs needed (from test failures):
   - `mcp-tool-result-{executionId}`
   - `mcp-tool-error-{executionId}`
   - `tool-execution-time`
   - `server-status-indicator`
   - `tool-latency-ms`

4. **AGGRESSIVE TARGET:** Fix 5/6 failures (not just 4/6)

**Acceptance Criteria:**
- ✅ 18/19 Group 1 tests passing (68% → **95%**)
- ✅ All MCP Tool UI elements testable
- ✅ Only 1 failure remaining (edge case)

**Test Coverage:** 6 additional E2E assertions

---

#### Feature 104.8: Hybrid Search Mock Data Fix (2 SP)
**Problem:** Group 10 hat 38% pass rate - Mock-Daten Format mismatch

**Root Cause:**
- Tests expect certain response format
- API returns different format
- Mocks don't match actual API

**Deliverables:**
1. Analyze actual API response format:
   - `GET /api/v1/retrieval/hybrid-search`
   - Document exact response schema

2. Update E2E test mocks to match:
   ```typescript
   // Current (WRONG):
   route.fulfill({
     body: JSON.stringify({ results: [...] })  // ❌
   });

   // Fixed (CORRECT):
   route.fulfill({
     body: JSON.stringify({ items: [...], mode: "hybrid", ... })  // ✅
   });
   ```

3. Update test assertions to match actual response:
   - Change `.results` → `.items`
   - Add `mode`, `execution_time_ms`, `metadata` checks

4. **AGGRESSIVE TARGET:** Fix 6/8 failures (not just 5/8)

**Acceptance Criteria:**
- ✅ 11/13 Group 10 tests passing (38% → **85%**)
- ✅ Mock data matches production API 100%
- ✅ All response fields validated
- ✅ Only 2 failures remaining

**Test Coverage:** 8 test updates

---

#### Feature 104.9: Explainability UI-Backend Integration (2 SP)
**Problem:** Group 15 hat 31% pass rate - UI existiert, aber Backend-Integration fehlt

**Deliverables:**
1. `frontend/src/pages/admin/ExplainabilityPage.tsx` (UPDATE)
   - Connect to backend API (currently static data?)
   - Real retrieval explanation fetching
   - Real decision trace fetching
   - Real compliance report fetching

2. API Integration:
   - `GET /api/v1/explainability/retrieval/{query_id}` (3-level explanation)
   - `GET /api/v1/explainability/decision/{decision_id}` (decision trace)
   - `GET /api/v1/explainability/compliance/{report_id}` (GDPR compliance)

3. Test IDs (additional):
   - `explanation-retrieval-{queryId}`
   - `explanation-decision-{decisionId}`
   - `explanation-compliance-{reportId}`
   - `explanation-level-technical`, `explanation-level-business`, `explanation-level-regulatory`

**Acceptance Criteria:**
- ✅ 11/13 Group 15 tests passing (31% → **85%**)
- ✅ Real-time explanation fetching working
- ✅ 3-level explanation rendering (Technical/Business/Regulatory)
- ✅ Only 2 failures remaining

**Test Coverage:** 12 integration tests

---

### Phase 3.5: Easy Wins (2 SP)

#### Feature 104.12: Perfect Groups Polish (2 SP)
**Problem:** Groups 2, 9, 11, 12 haben je 1-2 Failures obwohl fast perfekt

**Current State:**
- **Group 2 (Bash):** 15/16 = 94% (1 failure)
- **Group 9 (Long Context):** 11/13 = 85% (2 failures)
- **Group 11 (Upload):** 13/15 = 87% (2 failures)
- **Group 12 (Communities):** 14/15 = 93% (1 failure)

**Deliverables:**
1. **Group 2 Fix (Bash):**
   - Analyze 1 failing test
   - Likely: Timeout issue oder Command output format mismatch
   - Quick fix (<30 min)

2. **Group 9 Fix (Long Context):**
   - Analyze 2 failing tests
   - Likely: Response assertion format oder Streaming issues
   - Quick fixes (<1 hour total)

3. **Group 11 Fix (Upload):**
   - Analyze 2 failing tests
   - Likely: File size limits oder Upload progress tracking
   - Quick fixes (<1 hour total)

4. **Group 12 Fix (Communities):**
   - Analyze 1 failing test
   - Likely: Community ID format oder Pagination issue
   - Quick fix (<30 min)

**Acceptance Criteria:**
- ✅ Group 2: 16/16 = **100%** (94% → 100%) 🎯
- ✅ Group 9: 13/13 = **100%** (85% → 100%) 🎯
- ✅ Group 11: 15/15 = **100%** (87% → 100%) 🎯
- ✅ Group 12: 15/15 = **100%** (93% → 100%) 🎯
- ✅ **4 Perfect Groups** (zusätzlich zu Groups 3 & 8)

**Test Coverage:** 6 E2E test fixes

**Impact:** +6 passing tests

---

### Phase 4: E2E Testing & Documentation (2 SP)

#### Feature 104.10: Full E2E Test Execution (1 SP)
**Deliverables:**
1. Run all 194 E2E tests after Phase 1-3.5 fixes
2. Identify remaining failures (target: <10)
3. Quick fixes for low-hanging fruit (<30 min each)
4. Document final results

**Acceptance Criteria:**
- ✅ 180+/194 tests passing (93%+)
- ✅ All groups >80% pass rate (except edge cases)
- ✅ No P0 blockers remaining
- ✅ 8+ Perfect Groups (100% pass rate)

---

#### Feature 104.11: Sprint 104 Documentation (1 SP)
**Deliverables:**
1. `docs/sprints/SPRINT_104_COMPLETE.md` - Final results
2. `docs/sprints/SPRINT_104_SUMMARY.md` - Sprint overview
3. Update `docs/sprints/SPRINT_PLAN.md` - Sprint 104 ✅ Complete
4. Update `CLAUDE.md` - Sprint 104 summary line

**Acceptance Criteria:**
- ✅ Complete documentation of all changes
- ✅ Test results documented by group
- ✅ Sprint 105 recommendations provided

---

## Story Points Breakdown

| Feature | Component | SP | Priority | Impact |
|---------|-----------|----|----|--------|
| 104.1 Browser Tools UI | Frontend | 3 | P0 | +6 tests |
| 104.2 Skills Management UI | Frontend | 3 | P0 | +8 tests |
| 104.3 Skills-Tools Integration | Frontend | 2 | P0 | +9 tests |
| 104.4 Memory Management Fix | Frontend | 2 | P1 | +11 tests |
| 104.5 Agent Hierarchy UI | Frontend | 2 | P1 | +6 tests |
| 104.6 GDPR/Audit API Fixes | Backend + Frontend | 2 | P1 | +9 tests |
| 104.7 MCP Tools Test IDs | Frontend | 2 | P2 | +5 tests |
| 104.8 Hybrid Search Mocks | Tests | 2 | P2 | +6 tests |
| 104.9 Explainability Integration | Frontend | 2 | P2 | +7 tests |
| 104.12 Perfect Groups Polish | Tests | 2 | P2 | +6 tests |
| 104.10 E2E Testing | Tests | 1 | P0 | Validation |
| 104.11 Documentation | Docs | 1 | P0 | Docs |
| **TOTAL** | | **25 SP** | | **+73 tests** |

---

## Success Metrics

### Primary Metrics
- **E2E Pass Rate:** 56% → **93%+** (+37pp)
- **Tests Fixed:** 81 failures → **<15 failures** (73 tests fixed)
- **Blocked Groups:** 3 groups → **0 groups**
- **Perfect Groups:** 2 groups → **8 groups** (+6 groups)
- **Production Readiness:** 56% → **93%+**

### Group-Specific Targets (AGGRESSIVE)

| Group | Current | Target | Delta | Status After |
|-------|---------|--------|-------|--------------|
| Group 1 (MCP Tools) | 68% (13/19) | **95%** (18/19) | +27pp | ⚠️ 1 failure |
| Group 2 (Bash) | 94% (15/16) | **100%** (16/16) | +6pp | ✅ PERFECT |
| Group 4 (Browser) | 0% (0/6) | **100%** (6/6) | +100pp | ✅ PERFECT |
| Group 5 (Skills) | 0% (0/8) | **100%** (8/8) | +100pp | ✅ PERFECT |
| Group 6 (Skills+Tools) | 0% (0/9) | **100%** (9/9) | +100pp | ✅ PERFECT |
| Group 7 (Memory) | 20% (3/15) | **93%** (14/15) | +73pp | ⚠️ 1 failure |
| Group 9 (Long Context) | 85% (11/13) | **100%** (13/13) | +15pp | ✅ PERFECT |
| Group 10 (Hybrid Search) | 38% (5/13) | **85%** (11/13) | +47pp | ⚠️ 2 failures |
| Group 11 (Upload) | 87% (13/15) | **100%** (15/15) | +13pp | ✅ PERFECT |
| Group 12 (Communities) | 93% (14/15) | **100%** (15/15) | +7pp | ✅ PERFECT |
| Group 13 (Agent Hier) | 25% (2/8) | **100%** (8/8) | +75pp | ✅ PERFECT |
| Group 14 (GDPR/Audit) | 21% (3/14) | **86%** (12/14) | +65pp | ⚠️ 2 failures |
| Group 15 (Explainability) | 31% (4/13) | **85%** (11/13) | +54pp | ⚠️ 2 failures |

### Perfect Groups (100% Pass Rate)
**Current:** Groups 3, 8 (2 groups)
**Target:** Groups 2, 3, 4, 5, 6, 8, 9, 11, 12, 13 (**8 groups** + 2 existing = **10 groups total**)

### Remaining Failures After Sprint 104
- Group 1: 1 failure (edge case)
- Group 7: 1 failure (edge case)
- Group 10: 2 failures (complex scenarios)
- Group 14: 2 failures (complex scenarios)
- Group 15: 2 failures (complex scenarios)
- **Total: 8 failures remaining** (vs 81 currently)

---

## Technical Debt Addressed

| TD # | Title | Resolution |
|------|-------|------------|
| TD-105 | Browser Tools UI Missing | Feature 104.1 |
| TD-106 | Skills Management UI Missing | Feature 104.2 |
| TD-107 | Skills-Tools Integration Missing | Feature 104.3 |
| TD-108 | Memory Component DOM Mismatch | Feature 104.4 |
| TD-109 | Sprint 100 API Contracts Incomplete | Feature 104.6 |

**New TDs Created:** 5
**TDs Resolved:** 5
**Net TD:** 0

---

## Dependencies

### External Dependencies
- None

### Internal Dependencies
- Sprint 103 MCP Backend (✅ Complete)
- Sprint 98 UI Components (✅ Partial - completion in Sprint 104)
- Sprint 95 Hierarchical Agents (✅ Backend complete)
- Sprint 59 Tool Framework (✅ Complete)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Frontend complexity exceeds estimates | Medium | High | Use parallel frontend-agents (3 concurrent) |
| API contract changes require backend work | Low | Medium | Backend already complete, only format fixes needed |
| DOM structure debugging takes >2 SP | Medium | Medium | Use browser DevTools, add debug logging |
| E2E tests still fail after fixes | Low | High | Manual testing before E2E run, iterative fixes |

---

## Implementation Strategy

### Phase Sequence
1. **Phase 1 (8 SP):** Browser & Skills Frontend - Highest impact (fixes 0% groups)
2. **Phase 2 (6 SP):** Admin UI Fixes - Medium impact (20-31% → 70%+)
3. **Phase 3 (4 SP):** Partial Improvements - Low-hanging fruit (68% → 89%)
4. **Phase 4 (2 SP):** Testing & Docs - Validation

### Parallel Execution
- **3 Frontend-Agents:** Features 104.1, 104.2, 104.3 (Phase 1)
- **2 Frontend-Agents:** Features 104.4, 104.5 (Phase 2)
- **1 Backend-Agent + 1 Frontend-Agent:** Feature 104.6 (Phase 2)

**Estimated Completion Time:** 4-6 hours for all phases

---

## Definition of Done

- ✅ All 11 features implemented and tested
- ✅ 175+/194 E2E tests passing (90%+)
- ✅ All P0 groups >70% pass rate
- ✅ No syntax errors in any test file
- ✅ Unit test coverage >80% on new components
- ✅ Integration tests passing for all new APIs
- ✅ Complete documentation created
- ✅ Sprint 105 plan drafted

---

## Sprint 105 Preview (Future Work)

**Remaining Work After Sprint 104:**
- Final 5-10% E2E polish (reach 95%+)
- Performance optimization (response times <200ms)
- RAGAS Phase 2 Evaluation (deferred from Sprint 88)
- Domain Training Optimization (deferred from Sprint 103)

**Estimated Sprint 105:** 12-15 SP
