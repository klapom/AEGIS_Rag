# Sprint 101 Plan: E2E Validation & GDPR Bug Fix

**Sprint Duration:** TBD (after Sprint 100)
**Sprint Goal:** Complete Playwright E2E testing for all Sprint 100 contract fixes + fix GDPR page bug
**Total Story Points:** 10 SP
**Priority:** P1 (Testing & Bug Fix)

---

## Sprint Context

**Background:**
Sprint 100 implemented 8 API contract fixes (22 SP). Only Fix #1 (Skills List Pagination) was validated with Playwright MCP. Remaining 7 fixes need E2E testing.

**Discovered Issue:**
GDPR Consent Page loads empty screen (no errors, no API calls) - blocks testing of Fixes #2 and #6.

---

## Feature 101.1: GDPR Consent Page Bug Fix (4 SP)

**Priority:** P0 (Blocker)
**Issue:** Page renders empty screen after login, no API calls triggered

**Investigation Steps:**
1. Check React component mounting
2. Verify API endpoint availability
3. Check route configuration
4. Inspect data fetching logic

**Acceptance Criteria:**
- ✅ Page loads with data or proper error message
- ✅ API calls to `/api/v1/gdpr/consents` visible in Network
- ✅ Can test Fixes #2 and #6

---

## Feature 101.2: Playwright E2E Testing (6 SP)

**Priority:** P1 (Testing Coverage)

### Test Journey #1: Audit Trail - Events List (1 SP)
**Fix Validated:** Fix #3 (Audit Events field name)

**Steps:**
1. Navigate to `/admin/audit-trail`
2. Verify events list loads
3. Check API: `GET /api/v1/audit/events` returns `items` field
4. Verify events display correctly

**Expected:** Events table shows data, no TypeErrors

---

### Test Journey #2: Audit Reports Generation (1 SP)
**Fix Validated:** Fix #4 (Audit Reports query params)

**Steps:**
1. Navigate to `/admin/audit-trail` → Reports tab
2. Select timeRange "Last 7 Days"
3. Click "Generate Report"
4. Check API: `GET /api/v1/audit/reports/...?start_time=...&end_time=...`
5. Verify ISO 8601 timestamps sent (not "7d")

**Expected:** Report generated with proper timestamp format

---

### Test Journey #3: Agent Hierarchy - Status Display (1 SP)
**Fix Validated:** Fix #5 (Agent Hierarchy status enum)

**Steps:**
1. Navigate to `/admin/agent-hierarchy`
2. Verify hierarchy tree loads
3. Check node status badges display correctly
4. Check API: `GET /api/v1/agents/hierarchy` returns lowercase status values

**Expected:** Status badges show "active", "idle", "busy" (lowercase)

---

### Test Journey #4: Agent Details - Field Mapping (1 SP)
**Fix Validated:** Fix #7 (Agent Details field names)

**Steps:**
1. Navigate to `/admin/agent-hierarchy`
2. Click on any agent node
3. Verify Agent Details panel opens
4. Check all fields populated: agent_name, agent_level (UPPERCASE), success_rate_pct (%), latency, etc.

**Expected:** All agent details display correctly without TypeErrors

---

### Test Journey #5: Skills Config - YAML Validation (2 SP)
**Fix Validated:** Fix #8 (Skills Config validation endpoint)

**Steps:**
1. Navigate to `/admin/skills/registry`
2. Click on any skill → "Config" link
3. Edit YAML configuration
4. Test invalid YAML (e.g., missing colon)
5. Verify validation API called: `POST /api/v1/skills/{name}/config/validate`
6. Check error messages displayed
7. Test valid YAML → verify success

**Expected:** Validation endpoint works, errors/warnings displayed

---

### Test Journey #6 & #7: GDPR Pages (After Bug Fix)
**Fix Validated:** Fix #2 (GDPR Consents field), Fix #6 (GDPR Status mapping)

**Steps:**
1. Navigate to `/admin/gdpr-consent`
2. Verify consents list loads
3. Check API: `GET /api/v1/gdpr/consents` returns `items` field
4. Verify status displayed as "active" (not "granted")
5. Check status badge colors correct

**Expected:** Consents display with proper field names and status mapping

---

## Success Criteria

1. ✅ GDPR Consent Page bug fixed and loading correctly
2. ✅ All 7 Playwright test journeys completed
3. ✅ No TypeErrors or API errors in any tested page
4. ✅ All 8 Sprint 100 fixes validated with E2E tests
5. ✅ Screenshots captured for all test journeys

---

## Implementation Priority

**Phase 1:** GDPR Bug Fix (Day 1) - 4 SP
- Debug GDPR Consent Page empty screen
- Fix component mounting/data fetching issue
- Validate fix with Playwright

**Phase 2:** E2E Testing (Day 2-3) - 6 SP
- Test Journey #1: Audit Events
- Test Journey #2: Audit Reports
- Test Journey #3: Agent Hierarchy Status
- Test Journey #4: Agent Details Fields
- Test Journey #5: Skills Config Validation
- Test Journey #6-7: GDPR Consents & Status (after fix)

---

**Created:** 2026-01-15
**Dependencies:** Sprint 100 contract fixes must be deployed
**Risk:** GDPR bug may require significant debugging time

---

## Sprint 100 Validation Summary

| Fix | Feature | SP | E2E Status |
|-----|---------|-----|-----------|
| #1 | Skills List Pagination | 3 | ✅ PASS (Sprint 100) |
| #2 | GDPR Consents field | 2 | ⏳ Blocked by bug |
| #3 | Audit Events field | 2 | ⏳ Sprint 101.2 |
| #4 | Audit Reports params | 3 | ⏳ Sprint 101.2 |
| #5 | Agent Hierarchy status | 0 | ⏳ Sprint 101.2 |
| #6 | GDPR Status mapping | 2 | ⏳ Blocked by bug |
| #7 | Agent Details fields | 3 | ⏳ Sprint 101.2 |
| #8 | Skills Config validation | 3 | ⏳ Sprint 101.2 |

**Total:** 18 SP to validate in Sprint 101 (8 SP fixed in Sprint 100)
