# Sprint 47: Bug Fixes & UI Stabilization

**Status:** PLANNED
**Start:** 2025-12-17
**End:** 2025-12-20
**Priority:** Critical (P0 Bug Fixes)
**Prerequisites:** Sprint 46 complete (Testing revealed critical issues)

---

## Objective

Fix critical bugs discovered during Sprint 46 post-implementation testing. Stabilize the frontend-to-backend integration and resolve UI data synchronization issues.

---

## Sprint Goals

### Primary Goals
1. **P0 Fix: React Infinite Loop** - Fix `Maximum update depth exceeded` error in Chat streaming
2. **P1 Fix: Health Page** - Align frontend with backend `/health` endpoint
3. **P1 Fix: Domain List Sync** - Fix Admin Dashboard showing 0 domains
4. **P1 Fix: Trailing Slash** - Make `/admin/domains` work without trailing slash

### Secondary Goals
5. **TD-050: Verify Answer Streaming** - Investigate if duplicate streaming issue is related to React loop
6. **TD-053: Admin Dashboard Polish** - Address remaining Admin UI technical debt

---

## Reference Documents

| Document | Content |
|----------|---------|
| `docs/testing/TEST_RESULTS_FRONTEND_BACKEND.md` | Full test results from Sprint 46 |
| `docs/testing/FRONTEND_TO_BACKEND_TESTPLAN.md` | Test plan reference |
| `docs/sprints/SPRINT_46_PLAN.md` | Previous sprint with identified issues |
| `docs/technical-debt/TD_INDEX.md` | Technical debt index |

---

## Part 1: Critical Bug Fixes (P0)

### Feature 47.1: Fix React Infinite Loop in Chat
**Story Points:** 13
**Priority:** P0 - CRITICAL
**Source:** Sprint 46 UI Testing

**Problem:**
When SSE tokens stream in from the backend, the Chat component enters an infinite re-render loop:
```
[ERROR] Maximum update depth exceeded. This can happen when a component
calls setState inside useEffect...
```

**Symptoms:**
- Backend SSE streaming works correctly (verified via curl)
- "AegisRAG denkt nach..." loading indicator appears
- Tokens never display - infinite re-render blocks UI
- Browser console floods with error messages

**Investigation Areas:**
- [ ] `useEffect` hooks with incorrect/missing dependencies
- [ ] State updates triggered by streaming tokens
- [ ] Potential connection to TD-050 (Duplicate Answer Streaming)
- [ ] Message state mutation during streaming

**Files to Investigate:**
- `frontend/src/components/chat/ChatMessage.tsx`
- `frontend/src/hooks/useSSE.ts` or similar streaming hook
- `frontend/src/pages/SearchResultsPage.tsx`
- `frontend/src/components/chat/ConversationView.tsx`

**Acceptance Criteria:**
- [ ] Chat streaming displays tokens incrementally
- [ ] No console errors during streaming
- [ ] Response completes without freezing
- [ ] Works with all LLM models (qwen3, nemotron)

**Screenshot Reference:** `.playwright-mcp/chat-streaming-test.png`

---

### Feature 47.2: Fix Health Page Endpoint
**Story Points:** 3
**Priority:** P1
**Source:** Sprint 46 UI Testing

**Problem:**
Frontend Health page calls `/health/detailed` which returns 404. Only `/health` is implemented.

**Error Message:**
```
Fehler beim Laden des System-Status
HTTP 404: {"error":{"code":"NOT_FOUND","message":"Not Found",
"details":null,"path":"/health/detailed"}}
```

**Solution Options:**
1. **Option A (Recommended):** Update frontend to use `/health` endpoint
2. **Option B:** Implement `/health/detailed` endpoint on backend

**Files:**
- `frontend/src/pages/HealthDashboard.tsx` (or similar)
- `frontend/src/services/api.ts` - health check function

**Acceptance Criteria:**
- [ ] Health page loads without errors
- [ ] All service statuses displayed (Qdrant, Neo4j, Redis, Ollama)
- [ ] Version info shown

**Screenshot Reference:** `.playwright-mcp/health-page-error.png`

---

## Part 2: Data Synchronization Fixes (P1)

### Feature 47.3: Fix Domain List Sync in Admin Dashboard
**Story Points:** 5
**Priority:** P1
**Source:** Sprint 46 UI Testing + TD-053

**Problem:**
Admin Dashboard shows "No domains configured" but API returns 15 domains.

**Evidence:**
```bash
# API returns 15 domains
curl http://localhost:8000/admin/domains/
# Returns: [{"name": "omnitracker_expertise...", "status": "ready"}, ...]

# UI shows: "No domains configured"
```

**Investigation Areas:**
- [ ] Frontend API call URL (missing trailing slash?)
- [ ] State management for domain list
- [ ] Data transformation/mapping issues
- [ ] Race condition during load

**Files:**
- `frontend/src/pages/AdminDashboard.tsx`
- `frontend/src/components/admin/DomainSection.tsx`
- `frontend/src/services/api.ts` - domain API calls

**Acceptance Criteria:**
- [ ] Admin Dashboard displays all 15 domains
- [ ] Domain status badges show correctly
- [ ] Domain list updates after creating new domain

**Screenshot Reference:** `.playwright-mcp/admin-dashboard.png`

---

### Feature 47.4: Fix Trailing Slash Requirement
**Story Points:** 2
**Priority:** P1
**Source:** Sprint 46 API Testing

**Problem:**
`/admin/domains` returns 404, but `/admin/domains/` works. This inconsistency breaks frontend calls.

**Solution:**
Add redirect or accept both variants in backend router.

**Files:**
- `src/api/v1/admin/domains.py` - Router configuration

**Implementation:**
```python
# Option A: Add redirect
@router.get("/domains", include_in_schema=False)
async def domains_redirect():
    return RedirectResponse(url="/admin/domains/")

# Option B: Configure router to accept both
router = APIRouter(redirect_slashes=True)
```

**Acceptance Criteria:**
- [ ] `/admin/domains` works without trailing slash
- [ ] `/admin/domains/` continues to work
- [ ] No redirect loops

---

## Part 3: Technical Debt Resolution

### Feature 47.5: TD-050 - Verify Answer Streaming
**Story Points:** 3
**Priority:** P2
**Source:** Technical Debt Index

**Context from TD-050:**
> Duplicate Answer Streaming - Frontend may render answer twice
> Status: NEEDS VERIFICATION (3 SP)

**Investigation:**
- [ ] Check if related to P0 infinite loop bug
- [ ] Test after 47.1 is fixed
- [ ] Verify single answer rendering
- [ ] Update TD status based on findings

**Acceptance Criteria:**
- [ ] Confirm whether TD-050 is same root cause as 47.1
- [ ] Update TD_INDEX.md with findings
- [ ] Close if resolved by 47.1

---

### Feature 47.6: TD-053 - Admin Dashboard Polish
**Story Points:** 8 (reduced from 34 SP - partial scope)
**Priority:** P2
**Source:** Technical Debt Index

**Context from TD-053:**
> Admin Dashboard - Multiple UI improvements needed
> Status: OPEN (34 SP total)

**Sprint 47 Scope (subset):**
- [ ] Verify domain data loads correctly (covered by 47.3)
- [ ] Ensure collapsible sections work
- [ ] Fix any broken links/navigation
- [ ] Test indexing section functionality

**Deferred to Sprint 48+:**
- Full Admin UI redesign
- Indexing progress visualization
- Advanced settings management

**Acceptance Criteria:**
- [ ] Admin Dashboard functional after 47.3 fix
- [ ] No console errors on Admin page
- [ ] All sections expand/collapse correctly

---

## Part 4: Testing & Validation

### Feature 47.7: Regression Testing
**Story Points:** 5
**Priority:** P1

**Test Plan:**
1. Re-run all UI tests from `FRONTEND_TO_BACKEND_TESTPLAN.md`
2. Verify all P0/P1 bugs are fixed
3. Capture new screenshots for comparison
4. Update `TEST_RESULTS_FRONTEND_BACKEND.md`

**Test Cases to Re-run:**
- [ ] UI.1: Login Flow (was PASS - verify still works)
- [ ] UI.2: Session Sidebar (was PASS - verify still works)
- [ ] UI.3: Chat Streaming (was PARTIAL - should be PASS)
- [ ] UI.4: Admin Dashboard (was PASS - verify domains show)
- [ ] UI.5: Health Page (was FAIL - should be PASS)

**Acceptance Criteria:**
- [ ] All 5 UI tests PASS
- [ ] Overall pass rate > 90%
- [ ] No new regressions

---

## Sprint Breakdown Summary

| Part | Features | SP | Focus |
|------|----------|-----|-------|
| Part 1 | 47.1-47.2 | 16 | Critical Bugs (P0/P1) |
| Part 2 | 47.3-47.4 | 7 | Data Sync (P1) |
| Part 3 | 47.5-47.6 | 11 | Tech Debt |
| Part 4 | 47.7 | 5 | Testing |
| **Total** | **7 Features** | **39** | |

---

## Technical Tasks

### Frontend
- [ ] Debug useEffect dependencies in Chat component
- [ ] Fix streaming token state management
- [ ] Update Health page API call
- [ ] Fix Admin domain list API call
- [ ] Add error boundaries for better error display

### Backend
- [ ] Add trailing slash redirect for `/admin/domains`
- [ ] (Optional) Implement `/health/detailed` if needed

### Testing
- [ ] Run Playwright tests after each fix
- [ ] Update test documentation
- [ ] Capture comparison screenshots

---

## Success Criteria

### Part 1: Critical Bugs
- [ ] Chat streaming works without infinite loop
- [ ] Health page displays all services

### Part 2: Data Sync
- [ ] Admin Dashboard shows 15 domains
- [ ] API works with/without trailing slash

### Part 3: Tech Debt
- [ ] TD-050 status updated
- [ ] TD-053 partially resolved

### Part 4: Testing
- [ ] All 5 UI tests pass
- [ ] Documentation updated

---

## Dependencies

### External
- None

### Internal
- Sprint 46 complete (testing completed)
- Access to test screenshots in `.playwright-mcp/`

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| React loop hard to debug | High | Use React DevTools, add logging |
| Fix breaks other features | Medium | Run full regression suite |
| TD-050 unrelated to 47.1 | Low | Investigate separately if needed |

---

## Known Issues to NOT Address (Sprint 48+)

These issues were identified but are out of scope for Sprint 47:

| Issue | Category | Sprint |
|-------|----------|--------|
| Temporal endpoints | P2 | 48+ |
| Graph communities endpoint | P2 | 48+ |
| Full Admin redesign | P2 | 48+ |
| Indexing progress UI | P2 | 48+ |

---

## References

- [TEST_RESULTS_FRONTEND_BACKEND.md](../testing/TEST_RESULTS_FRONTEND_BACKEND.md)
- [FRONTEND_TO_BACKEND_TESTPLAN.md](../testing/FRONTEND_TO_BACKEND_TESTPLAN.md)
- [SPRINT_46_PLAN.md](SPRINT_46_PLAN.md)
- [TD_INDEX.md](../technical-debt/TD_INDEX.md)
