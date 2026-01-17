# E2E Test Fixes: Groups 13-15 Summary

**Sprint:** 107 (Backend Fixes)
**Date:** 2026-01-16
**Scope:** Agent Hierarchy, GDPR/Audit, Explainability Pages

---

## Overview

Fixed missing testids and verified API contracts for E2E test groups 13-15. Most issues were minor testid mismatches or missing accessibility attributes. Major finding: Sprint 100 API contract fixes already implemented correctly.

---

## Group 13: Agent Hierarchy Page ✅ FIXED

**Status:** 4 fixes applied, all tests should pass

### Fixes Applied

1. **AgentHierarchyPage.tsx:189** - Added `data-testid="empty-state"` to error div
   - Test expected: `[data-testid="empty-state"]` OR `[class*="empty"]`
   - Fixed: Added testid to error state component

2. **AgentHierarchyPage.tsx:264** - Changed `data-testid="agent-details-panel"` to `"agent-details"`
   - Test expected: `[data-testid="agent-details"]` OR `[class*="details-panel"]`
   - Fixed: Simplified testid to match test expectations

3. **AgentDetailsPanel.tsx:215** - Added `data-testid="performance-metrics"` to performance section
   - Test expected: `[data-testid="performance-metrics"]` OR `[class*="metrics"]`
   - Fixed: Added testid wrapper to metrics container

4. **AgentHierarchyD3.tsx:293,302,311** - Added `aria-label` attributes to zoom controls
   - Test expected: `button[aria-label*="zoom in"]` for accessibility
   - Fixed: Added aria-labels ("Zoom in", "Zoom out", "Reset zoom") for screen readers

### Backend API Status

✅ `/api/v1/agents/hierarchy` - Returns real data (nodes/edges format)
⚠️ `/api/v1/agents/{id}/details` - Returns runtime error: "Agent not registered with message bus"

**Note:** Agent details API works structurally but requires agents to be registered with the message bus at runtime. This is a known limitation documented in SPRINT_107_PLAN.md (Issue 107.0C).

---

## Group 14: GDPR/Audit Pages ✅ VERIFIED

**Status:** Sprint 100 fixes already implemented, 1 known limitation

### Sprint 100 API Contract Fixes (Already Implemented)

#### Fix #2: GDPR Consents List Field ✅
- **Backend:** Returns `items` array (not `consents`)
- **Frontend:** GDPRConsent.tsx:64 correctly uses `items` field
```typescript
const items = consentsData.items || [];
```

#### Fix #3: Audit Events List Field ✅
- **Backend:** Returns `items` array (not `events`)
- **Frontend:** AuditTrail.tsx:64 correctly uses `items` field
```typescript
setEvents(data.items || []);
```

#### Fix #4: Compliance Reports Timestamps ✅
- **Backend:** Expects ISO 8601 `start_time` & `end_time` (not `timeRange` enum)
- **Frontend:** AuditTrail.tsx:79-104 correctly converts timeRange to ISO 8601
```typescript
const start_time_iso = start_time.toISOString();
const end_time_iso = end_time.toISOString();
```

#### Fix #6: GDPR Consent Status Mapping ✅
- **Backend:** Uses `granted` status
- **Frontend:** GDPRConsent.tsx:67-70 correctly maps `granted` → `active`
```typescript
status: consent.status === 'granted' ? 'active' : consent.status
```

### Testids Already Present

✅ ConsentRegistry.tsx:159 - `data-testid="consent-row-${consent.id}"`
✅ AuditLogBrowser.tsx:260 - `data-testid="audit-event-${event.id}"`
✅ AuditLogBrowser.tsx:217,227 - "Previous" / "Next" pagination buttons
✅ ComplianceReports.tsx:85 - "Generate Report" button with time range selector

### Known Limitation

❌ **GDPR Consents Pagination Not Implemented**
- **Issue:** ConsentRegistry component doesn't support pagination
- **Test Expectation:** Pagination controls when total > page_size (50 items, 10 per page)
- **Current Behavior:** Shows all consents at once (fine for small datasets)
- **Impact:** Test `should display pagination controls for consents` may fail
- **Recommendation:** Add pagination to ConsentRegistry in future sprint (not critical for MVP)

### Backend API Status

✅ `/api/v1/gdpr/consents` - Returns `{items: [], total: 0, page: 1, page_size: 20}`
✅ `/api/v1/audit/events` - Returns `{items: [], total: 0, page: 1, page_size: 20}`

---

## Group 15: Explainability Page ⚠️ API MISMATCH

**Status:** Frontend correct, tests mock wrong endpoints

### Root Cause: E2E Test Design Issue

The E2E tests were written for a **different API design** than what was actually implemented. The frontend correctly uses the implemented APIs, but the tests mock non-existent endpoints.

### Actual vs Expected APIs

| Test Expects | Actual Backend | Status |
|--------------|----------------|--------|
| `/api/v1/explainability/decision-paths` | `/api/v1/explainability/recent` | ❌ Mismatch |
| `/api/v1/explainability/metrics` | *Not implemented* | ❌ Missing |
| `/api/v1/certification/status` | *Not implemented* | ❌ Missing |

### Implemented Backend APIs (Sprint 104)

✅ `/api/v1/explainability/recent` - List recent decision traces
✅ `/api/v1/explainability/trace/{trace_id}` - Get full trace details
✅ `/api/v1/explainability/explain/{trace_id}` - Get explanation for trace (3 levels: user/expert/audit)
✅ `/api/v1/explainability/attribution/{trace_id}` - Get source documents for trace

### Frontend Implementation (Correct)

✅ ExplainabilityPage.tsx uses correct APIs:
```typescript
const traces = await getRecentTraces(undefined, 20);        // /recent
const trace = await getDecisionTrace(traceId);              // /trace/{id}
const explanationData = await getExplanation(traceId, level); // /explain/{id}
const sourceData = await getSourceAttribution(traceId);     // /attribution/{id}
```

✅ Page heading: "Explainability Dashboard" (matches test `/explainability|transparency/i`)
✅ Testid: `data-testid="explainability-page"`
✅ Error handling present

### Missing Features

The tests expect features that weren't implemented:

1. **Aggregate Decision Paths View** (`/decision-paths`)
   - Test expects list of decision paths with steps/agents
   - Frontend shows **trace-based view** (select from recent traces)
   - Both valid UX patterns, just different designs

2. **Aggregate Transparency Metrics** (`/metrics`)
   - Test expects dashboard with explainability/interpretability scores
   - Frontend shows **per-trace metrics** (confidence, hallucination risk)
   - Aggregate metrics would require separate endpoint

3. **Certification Status** (`/certification/status`)
   - Test expects EU AI Act / GDPR / ISO 27001 certificates
   - Not implemented in backend or frontend
   - Would require new certification tracking system

4. **Audit Trail Link**
   - Test expects link/button to audit trail page (`a[href*="/audit"]`)
   - Frontend mentions "Audit View" but doesn't link to AuditTrail page
   - **Quick Fix:** Add link in header or info section

### Recommendation

**Option A: Update E2E Tests (Preferred)**
- Rewrite Group 15 tests to mock `/recent`, `/trace/{id}`, `/explain/{id}`, `/attribution/{id}`
- Test actual UI: trace list, trace detail view, 3-level explanations, source attribution
- Verify decision flow display, confidence metrics, explanation levels

**Option B: Implement Missing Features (Sprint 108+)**
- Add `/decision-paths` endpoint (aggregate view of all traces)
- Add `/metrics` endpoint (system-wide transparency metrics)
- Add `/certification/status` endpoint (certification tracking)
- Add audit trail navigation link
- **Story Points:** ~13 SP (3 endpoints + UI + tests)

**Quick Win: Add Audit Trail Link (1 SP)**
```tsx
// ExplainabilityPage.tsx header
<Link
  to="/admin/audit"
  className="..."
  data-testid="audit-trail-link"
>
  View Full Audit Trail →
</Link>
```

---

## Summary of Changes

### Files Modified (Group 13)

1. `frontend/src/pages/admin/AgentHierarchyPage.tsx`
   - Line 189: Added `data-testid="empty-state"` to error div
   - Line 264: Changed `"agent-details-panel"` → `"agent-details"`

2. `frontend/src/components/agent/AgentDetailsPanel.tsx`
   - Line 215: Added `data-testid="performance-metrics"` wrapper

3. `frontend/src/components/agent/AgentHierarchyD3.tsx`
   - Lines 293, 302, 311: Added `aria-label` attributes to zoom buttons

### Files Verified (Group 14)

All Sprint 100 fixes already present, no changes needed:
- ✅ `frontend/src/pages/admin/GDPRConsent.tsx` (items field, status mapping)
- ✅ `frontend/src/pages/admin/AuditTrail.tsx` (items field, ISO timestamps)
- ✅ `frontend/src/components/gdpr/ConsentRegistry.tsx` (testids, empty state)
- ✅ `frontend/src/components/audit/AuditLogBrowser.tsx` (testids, pagination)

### Files Verified (Group 15)

No changes needed - frontend correctly implements Sprint 104 design:
- ✅ `frontend/src/pages/admin/ExplainabilityPage.tsx` (uses correct APIs)
- ✅ `src/api/v1/explainability.py` (implements 4 trace-based endpoints)

**Action Item:** Update E2E tests OR implement missing aggregate features in Sprint 108.

---

## Test Execution Recommendations

### Group 13 (Agent Hierarchy)
- **Expected:** All 6 tests should pass after testid fixes
- **Risk:** Agent details API requires message bus registration (runtime dependency)
- **Workaround:** Tests mock the API, so no runtime dependency in E2E

### Group 14 (GDPR/Audit)
- **Expected:** 10/11 tests should pass
- **Known Failure:** `should display pagination controls for consents` (pagination not implemented)
- **Impact:** Low (pagination works for audit events, just not consents)

### Group 15 (Explainability)
- **Expected:** 0/9 tests will pass (API mocks wrong endpoints)
- **Root Cause:** Test design mismatch with actual implementation
- **Options:**
  1. Rewrite tests to match actual APIs ✅ Recommended
  2. Implement missing aggregate features (13 SP)
  3. Skip Group 15 tests until Sprint 108

---

## Related Documentation

- **Sprint 107 Plan:** `docs/sprints/SPRINT_107_PLAN.md`
  - Issue 107.0A: Graphiti Neo4j bug
  - Issue 107.0B: Qdrant statistics
  - Issue 107.0C: Unverified APIs for Groups 13-15 (this report)

- **Sprint 100 Fixes:** `docs/sprints/SPRINT_100_FIXES_SUMMARY.md`
  - Fix #2: Consents list field (`items`)
  - Fix #3: Audit Events list field (`items`)
  - Fix #4: Compliance Reports timestamps (ISO 8601)
  - Fix #6: GDPR Status mapping (`granted` → `active`)

- **Sprint 104 Explainability:** `docs/sprints/SPRINT_104_SUMMARY.md`
  - Feature 104.10: Trace-based explainability UI
  - Backend APIs: `/recent`, `/trace/{id}`, `/explain/{id}`, `/attribution/{id}`

- **E2E Test Guide:** `tests/playwright/PLAYWRIGHT_E2E.md`
  - Group 13-15 test execution instructions
  - Backend API status verification

---

**Status:** Groups 13-14 ready for E2E testing, Group 15 requires test redesign or feature implementation.
