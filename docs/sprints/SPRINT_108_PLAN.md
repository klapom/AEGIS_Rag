# Sprint 108: E2E Test Fixes & Quality Assurance

**Sprint Goal:** Fix all remaining E2E test failures and resolve SKIP-marked tests

**Story Points:** TBD (will be determined after test analysis)
**Status:** 📝 Planned
**Duration:** TBD

---

## Sprint Context

Following Sprint 107's successful MCP Auto-Discovery implementation (26 SP, 100% complete), Sprint 108 focuses on comprehensive E2E test quality assurance. This sprint addresses all remaining Playwright test failures and resolves tests currently marked as SKIP.

**Previous Sprint:** Sprint 107 Complete (MCP Auto-Discovery + Backend Fixes)
**Test Environment:** http://192.168.178.10 (Docker Production)
**Test Framework:** Playwright
**Total Test Groups:** 16 groups (Group 01-16)

---

## Test Status Summary (Sprint 108 Initial Run - 2026-01-16)

| Group | Status | Passed | Failed | Skipped | Priority | Bug ID |
|-------|--------|--------|--------|---------|----------|--------|
| Group 01 | ✅ Pass | 15 | 0 | 4 | Medium | - |
| Group 02 | ⚠️ Partial | 12 | 1 | 2 | Medium | 108.5 |
| Group 03 | ✅ Perfect | 20 | 0 | 0 | ✅ Reference | - |
| Group 04 | ⏭️ Skipped | 0 | 0 | 6 | High | - |
| Group 05 | ⏭️ Skipped | 0 | 0 | 8 | High | - |
| Group 06 | ⏭️ Skipped | 0 | 0 | 9 | High | - |
| Group 07 | ❌ Critical | 3 | 12 | 0 | **Critical** | 108.1 |
| Group 08 | ✅ Pass | 10 | 0 | 1 | Medium | - |
| Group 09 | ⚠️ Partial | 12 | 1 | 0 | Medium | 108.6 |
| Group 10 | ✅ Perfect | 13 | 0 | 0 | ✅ Working | - |
| Group 11 | ⚠️ Partial | 12 | 2 | 0 | Medium | 108.7 |
| Group 12 | ✅ Good | 14 | 1 | 1 | Low | 108.8 |
| Group 13 | ❌ Critical | 2 | 6 | 0 | **Critical** | 108.2 |
| Group 14 | ❌ Critical | 4 | 10 | 0 | **Critical** | 108.3 |
| Group 15 | ❌ Critical | 4 | 10 | 0 | **Critical** | 108.4 |
| Group 16 | ❌ Critical | 0 | 6 | 0 | **Critical** | 108.0A, 108.0B |

**Total:** 120 passed, 49 failed, 31 skipped (200 tests total)
**Test Duration:** 18.9 minutes
**Pass Rate:** 60% (excluding skipped: 71%)

**Critical Issues:** 44 failures across 5 groups (Groups 7, 13, 14, 15, 16)
**Medium Issues:** 5 failures across 4 groups (Groups 2, 9, 11, 12)

---

## Issues to Address

### Critical Issues (Must Fix)

#### Issue 108.1: Group 07 - Memory Management Page Failures (12 failed tests)
**Priority:** Critical
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Failures:**
- Test count: 3 passed, 12 failed
- Root Cause: API contract mismatch (partially fixed in Sprint 106)
- Known Issue: Graphiti Neo4j `verify_connectivity` method (fixed in Sprint 107)

**Investigation Notes:**
- Sprint 107.0A fixed `verify_connectivity` method
- Sprint 107.0B implemented Qdrant statistics
- Need to verify if these fixes resolve Group 07 failures

**Acceptance Criteria:**
- [ ] All 15 Memory Management tests pass
- [ ] Redis stats display correctly
- [ ] Qdrant stats display correctly
- [ ] Graphiti stats display correctly
- [ ] No API contract mismatches

---

#### Issue 108.2: Group 13 - Agent Hierarchy Page Failures (6 failed tests)
**Priority:** Critical
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Failures:**
- Test count: 2 passed, 6 failed
- Likely Cause: Missing backend APIs or data-testid mismatches

**Investigation Notes:**
- Need to verify `/api/v1/agents/hierarchy` endpoint exists
- Need to verify `/api/v1/agents/communication` endpoint exists
- Check for data-testid alignment

**Acceptance Criteria:**
- [ ] All 8 Agent Hierarchy tests pass
- [ ] Agent hierarchy tree renders
- [ ] Communication flow displays correctly
- [ ] Backend APIs return valid data

---

#### Issue 108.3: Group 14 - GDPR/Audit Page Failures (11 failed tests)
**Priority:** Critical
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Failures:**
- Test count: 3 passed, 11 failed
- Likely Cause: Missing backend APIs or incomplete implementations

**Investigation Notes:**
- Sprint 95-96 implemented GDPR/Audit features
- Need to verify `/api/v1/audit/events` endpoint
- Need to verify `/api/v1/gdpr/consents` endpoint
- Check event filtering and consent management

**Acceptance Criteria:**
- [ ] All 14 GDPR/Audit tests pass
- [ ] Audit log displays and filters work
- [ ] GDPR consent registry works
- [ ] Data subject rights functionality works
- [ ] Backend APIs return valid data

---

#### Issue 108.4: Group 15 - Explainability Page Failures (9 failed tests)
**Priority:** Critical
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Failures:**
- Test count: 4 passed, 9 failed
- Likely Cause: Missing backend APIs or incomplete implementations

**Investigation Notes:**
- Sprint 95-96 implemented Explainability features
- Need to verify `/api/v1/explainability/*` endpoints
- Check for 3-level explanation system (Simple/Detailed/Technical)

**Acceptance Criteria:**
- [ ] All 13 Explainability tests pass
- [ ] Explanation levels display correctly
- [ ] Decision tree visualization works
- [ ] Trace viewer functions properly
- [ ] Backend APIs return valid data

---

### High Priority Issues (Should Fix)

#### Issue 108.5: Group 04 - Browser Tools (6 skipped tests)
**Priority:** High
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Status:**
- All tests skipped (missing data-testids)
- Sprint 106 Fix 5 added data-testids to components

**Investigation Notes:**
- MCPServerCard.tsx updated with `mcp-server-${name}` testid
- MCPToolExecutionPanel.tsx updated with execution testids
- Need to un-skip tests and verify

**Acceptance Criteria:**
- [ ] All 6 Browser Tools tests pass
- [ ] Tests use correct data-testids
- [ ] No test.skip() markers

---

#### Issue 108.6: Group 05 - Skills Registry (8 skipped tests)
**Priority:** High
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Status:**
- All tests skipped (missing data-testids)
- Sprint 106 Fix 6 added validation testids

**Investigation Notes:**
- SkillRegistry.tsx already has `skill-card-${name}` testids
- SkillConfigEditor.tsx updated with validation testids
- Need to un-skip tests and verify

**Acceptance Criteria:**
- [ ] All 8 Skills Registry tests pass
- [ ] Skill cards render correctly
- [ ] Config editor validation works
- [ ] No test.skip() markers

---

#### Issue 108.7: Group 06 - Skills-Tool Integration (9 skipped tests)
**Priority:** High
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Status:**
- All tests skipped (Skill-Tool integration UI)
- Sprint 106 Fix 7 added tool execution testids

**Investigation Notes:**
- ToolExecutionDisplay.tsx updated with `tool-execution-${tool_name}` testids
- SearchInput.tsx has `message-input` and `send-button` testids
- Need to un-skip tests and verify

**Acceptance Criteria:**
- [ ] All 9 Skills-Tool tests pass
- [ ] Chat interface works
- [ ] Tool execution displays correctly
- [ ] No test.skip() markers

---

#### Issue 108.8: Group 09 - Long Context (3 failed tests)
**Priority:** High
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Failures:**
- Test count: 10 passed, 3 failed
- Likely Cause: Timing issues (per PLAYWRIGHT_E2E.md)

**Investigation Notes:**
- E2E tests add ~50% overhead to response times
- May need to adjust timeout values

**Acceptance Criteria:**
- [ ] All 13 Long Context tests pass
- [ ] Timing assertions account for E2E overhead
- [ ] No flaky tests

---

#### Issue 108.9: Group 10 - Hybrid Search (2 failed tests)
**Priority:** High
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Failures:**
- Test count: 11 passed, 2 failed
- Likely Cause: Timing issues or selector mismatches

**Acceptance Criteria:**
- [ ] All 13 Hybrid Search tests pass
- [ ] Search results display correctly
- [ ] Mode switching works

---

#### Issue 108.10: Group 11 - Document Upload (6 failed tests)
**Priority:** High
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Failures:**
- Test count: 9 passed, 6 failed
- Likely Cause: Mock race conditions (per Fix 4 in PLAYWRIGHT_E2E.md)

**Investigation Notes:**
- Mock delay inconsistencies
- Need consistent delays in beforeEach and test mocks

**Acceptance Criteria:**
- [ ] All 15 Document Upload tests pass
- [ ] Upload progress displays correctly
- [ ] File validation works
- [ ] No mock race conditions

---

### Medium Priority Issues (Nice to Fix)

#### Issue 108.11: Group 01 - MCP Tools (4 skipped tests)
**Priority:** Medium
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Status:**
- 15 passed, 4 skipped
- Known Issue: Auth timeout (per PLAYWRIGHT_E2E.md)

**Acceptance Criteria:**
- [ ] All 19 MCP Tools tests pass
- [ ] No test.skip() markers
- [ ] Auth timeout resolved

---

#### Issue 108.12: Group 02 - Bash Execution (2 skipped tests)
**Priority:** Medium
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Status:**
- 14 passed, 2 skipped
- Feature deferred tests (per Fix 3 in PLAYWRIGHT_E2E.md)

**Acceptance Criteria:**
- [ ] All 16 Bash Execution tests pass (or documented as deferred)
- [ ] Skip markers have clear reasons

---

#### Issue 108.13: Group 08 - Deep Research (1 skipped test)
**Priority:** Medium
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Status:**
- 10 passed, 1 skipped

**Acceptance Criteria:**
- [ ] All 11 Deep Research tests pass
- [ ] No test.skip() markers

---

#### Issue 108.14: Group 12 - Graph Communities (1 failed, 1 skipped)
**Priority:** Medium
**Story Points:** TBD
**Status:** 🔍 Investigating

**Current Status:**
- 14 passed, 1 failed, 1 skipped
- Likely Cause: Selector specificity (per Fix 2 in PLAYWRIGHT_E2E.md)

**Acceptance Criteria:**
- [ ] All 16 Graph Communities tests pass
- [ ] Specific selectors with .first()
- [ ] No test.skip() markers

---

## Bug Tracking

### Critical Bugs Found (Immediate Fix Required)

#### BUG 108.0A: MCP Marketplace Route Not Registered (**FIXED**)
**Priority:** Critical
**Sprint:** 107 (Post-release bug)
**Story Points:** 1 SP
**Status:** ✅ Fixed
**Test Group:** Group 16 (All 6 tests failed)

**Problem:**
All Group 16 tests failed because `/admin/mcp-marketplace` route was not registered in App.tsx. The component was created in Sprint 107 but the route registration was missed.

**Error:**
```
Error: element(s) not found
Locator: getByTestId('page-title')
Expected: "MCP Server Marketplace"
```

**Failed Tests:**
- Test 195: 16.1 should display marketplace page with server browser
- Test 196: 16.2 should display server cards with correct information
- Test 197: 16.3 should search servers by name and tags
- Test 198: 16.4 should open installer dialog when clicking server card
- Test 199: 16.5 should show dependencies in installer dialog
- Test 200: 16.6 should install server and show success message

**Root Cause:**
Sprint 107 created `frontend/src/pages/admin/MCPMarketplace.tsx` and related components, but forgot to:
1. Import MCPMarketplace in App.tsx
2. Register route `/admin/mcp-marketplace`

**Fix Applied (2026-01-16):**
```typescript
// frontend/src/App.tsx

// Added import (line 52)
import { MCPMarketplace } from './pages/admin/MCPMarketplace';

// Added route (line 100)
<Route path="/admin/mcp-marketplace" element={<MCPMarketplace />} />
```

**Verification:**
- [x] Route import added
- [x] Route registration added
- [x] Frontend container rebuilt
- [ ] Group 16 E2E tests re-run (pending)

**Impact:** All MCP Marketplace features were inaccessible via UI (6/6 tests failed)

---

### Bugs Found During Testing (Not Yet Fixed)

#### BUG 108.0B: Group 16 Auth Pattern Timeout
**Priority:** High
**Story Points:** 2 SP
**Status:** 🔄 In Progress
**Test Group:** Group 16 (6 tests failing)

**Problem:**
Group 16 tests fail with auth timeout when using `setupAuthMocking()` pattern.

**Error:**
```
TimeoutError: locator.waitFor: Timeout 5000ms exceeded.
Call log: waiting for getByPlaceholder('Enter your username') to be visible
```

**Investigation:**
- Route is correctly registered (/admin/mcp-marketplace)
- API mocks are set up correctly
- Auth pattern from Group 03 causes timeout
- Suspected: Session state conflicts or rate limiting

**Next Steps:**
- [ ] Investigate if page redirects correctly to login
- [ ] Check if localStorage token approach works better for this page
- [ ] Compare with working groups (Group 10, 12)
- [ ] Consider using mock auth instead of real login for this test

---

#### BUG 108.1: Group 07 Memory Management - 12 Test Failures
**Priority:** Critical
**Story Points:** 8 SP
**Status:** 📝 Documented (from pre-Sprint 108 status)
**Test Group:** Group 07 (12 failures, 3 passed)

**Failed Tests:**
- Load Memory Management page
- Display tabs
- Redis statistics (Layer 1)
- Qdrant statistics (Layer 2)
- Graphiti statistics (Layer 3)
- Search tab
- Consolidation tab
- Export/clear functions
- Stats with numeric values
- Error-free page handling

**Known Fixes Applied:**
- Sprint 106 Fix 8: API contract alignment (redis/qdrant/graphiti field names)
- Sprint 107.0A: Neo4j verify_connectivity method
- Sprint 107.0B: Qdrant statistics implementation

**Remaining Issues:**
Despite Sprint 107 backend fixes, 12/15 tests still fail. Needs investigation whether:
- Frontend components not updated after API changes
- Test expectations don't match actual UI
- Backend API still returns incorrect data structure

**Next Steps:**
- [ ] Verify Sprint 107 backend fixes are deployed
- [ ] Check actual API responses vs test expectations
- [ ] Update frontend components if needed
- [ ] Align data-testids with test expectations

---

#### BUG 108.2: Group 13 Agent Hierarchy - 6 Test Failures
**Priority:** Critical
**Story Points:** 5 SP
**Status:** 📝 Documented
**Test Group:** Group 13 (6 failures, 2 passed)

**Failed Tests:**
- Load Agent Hierarchy page
- Open agent details panel
- Display performance metrics
- Handle API errors
- Tree zoom/pan controls
- Agent skills badges

**Suspected Cause:**
- Missing or incomplete backend APIs (`/api/v1/agents/hierarchy`, `/api/v1/agents/communication`)
- Frontend components may exist but backend integration missing
- Sprint 95-98 features may not be fully implemented

**Next Steps:**
- [ ] Verify backend API endpoints exist
- [ ] Check API response structure matches frontend expectations
- [ ] Verify D3 tree visualization dependencies
- [ ] Test with real backend data

---

#### BUG 108.3: Group 14 GDPR/Audit - 10 Test Failures
**Priority:** Critical
**Story Points:** 8 SP
**Status:** 📝 Documented
**Test Group:** Group 14 (10 failures, 4 passed)

**Failed Tests:**
- Load GDPR Consent page
- Display consents list
- Consent status mapping (granted→active)
- Load Audit Events page
- Display audit events
- Handle empty lists
- Handle API errors
- Pagination controls (consents and events)

**Suspected Cause:**
- Backend APIs missing or incomplete (`/api/v1/audit/events`, `/api/v1/gdpr/consents`)
- API contract mismatch (Sprint 100 fixes may not be complete)
- Sprint 95-96 features partially implemented

**Next Steps:**
- [ ] Verify backend API endpoints exist
- [ ] Check API response structure (items field, status mapping)
- [ ] Verify ISO 8601 timestamp format
- [ ] Test pagination implementation

---

#### BUG 108.4: Group 15 Explainability - 10 Test Failures
**Priority:** Critical
**Story Points:** 8 SP
**Status:** 📝 Documented
**Test Group:** Group 15 (10 failures, 4 passed)

**Failed Tests:**
- Load Explainability Dashboard
- Display decision paths
- Display certification status
- Display transparency metrics
- Display audit trail links
- Display model information
- Handle empty decision paths
- Handle API errors
- Display confidence levels

**Suspected Cause:**
- Backend APIs missing or incomplete (`/api/v1/explainability/*`)
- Sprint 95-96 features partially implemented
- Decision tree visualization not working

**Next Steps:**
- [ ] Verify backend API endpoints exist
- [ ] Check 3-level explanation system (Simple/Detailed/Technical)
- [ ] Verify decision tree data structure
- [ ] Test trace viewer functionality

---

#### BUG 108.5: Group 02 Bash - 1 Test Failure
**Priority:** Medium
**Story Points:** 2 SP
**Status:** 📝 Documented
**Test Group:** Group 02 (1 failure, 12 passed, 2 skipped)

**Failed Test:**
- should block dangerous rm -rf command

**Error:**
Test expects API to reject `rm -rf` command with 403 SECURITY_VIOLATION, but likely the backend doesn't implement this security check.

**Next Steps:**
- [ ] Verify backend implements rm -rf blocking
- [ ] Check security validation in bash tool execution
- [ ] Update backend or test expectations

---

#### BUG 108.6: Group 09 Long Context - 1 Test Failure
**Priority:** Medium
**Story Points:** 1 SP
**Status:** 📝 Documented
**Test Group:** Group 09 (1 failure, 12 passed)

**Failed Test:**
- should handle BGE-M3 dense+sparse scoring at Level 0-1

**Error:**
Performance timing assertion likely too strict (899ms actual vs <400ms expected)

**Next Steps:**
- [ ] Adjust timing expectation to account for E2E overhead
- [ ] Follow Fix 1 from PLAYWRIGHT_E2E.md (+50% buffer)

---

#### BUG 108.7: Group 11 Document Upload - 2 Test Failures
**Priority:** Medium
**Story Points:** 2 SP
**Status:** 📝 Documented
**Test Group:** Group 11 (2 failures, 12 passed)

**Failed Tests:**
- should upload document with fast endpoint (<5s response)
- should reject files larger than limit

**Suspected Cause:**
- Timing assertion too strict (8.1s actual vs <5s expected)
- File size validation not implemented or different behavior

**Next Steps:**
- [ ] Adjust timing expectation (+50% buffer)
- [ ] Verify file size limit validation in backend
- [ ] Check frontend file validation logic

---

#### BUG 108.8: Group 12 Graph Communities - 1 Test Failure
**Priority:** Low
**Story Points:** 1 SP
**Status:** 📝 Documented
**Test Group:** Group 12 (1 failure, 14 passed, 1 skipped)

**Failed Test:**
- should fetch communities from API on load

**Suspected Cause:**
- API mock not matching actual API response structure
- Timing issue during page load

**Next Steps:**
- [ ] Verify API mock data structure
- [ ] Add networkidle wait before assertions

---

## Sprint Workflow

### Phase 1: Test Execution & Analysis (Current)
1. ✅ Run all Playwright E2E tests
2. 🔄 Analyze test failures
3. 🔄 Categorize issues by priority
4. 🔄 Document bugs in this plan

### Phase 2: Critical Fixes
1. Fix Group 07 (Memory Management)
2. Fix Group 13 (Agent Hierarchy)
3. Fix Group 14 (GDPR/Audit)
4. Fix Group 15 (Explainability)

### Phase 3: High Priority Fixes
1. Un-skip and fix Groups 04, 05, 06
2. Fix timing issues in Groups 09, 10, 11

### Phase 4: Medium Priority Fixes
1. Fix remaining skipped tests
2. Address flaky tests

### Phase 5: Verification & Documentation
1. Run full test suite again
2. Verify all tests pass
3. Update PLAYWRIGHT_E2E.md
4. Complete sprint documentation

---

## Success Criteria

- [ ] All 202 E2E tests pass (100% pass rate)
- [ ] Zero test.skip() markers (except documented deferrals)
- [ ] Zero flaky tests
- [ ] All data-testids properly aligned
- [ ] All backend APIs verified
- [ ] Documentation updated

---

## Test Execution Log

### 2026-01-16: Initial Test Run - COMPLETED

**Command:**
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test e2e/group*.spec.ts --reporter=list
```

**Status:** ✅ Complete
**Duration:** 18.9 minutes
**Results:** 120 passed, 49 failed, 31 skipped (200 total tests)

**Detailed Results:**
- Group 01 (MCP Tools): 15 passed, 0 failed, 4 skipped
- Group 02 (Bash): 12 passed, 1 failed, 2 skipped
- Group 03 (Python): 20 passed, 0 failed, 0 skipped ✅ (Reference Pattern)
- Group 04 (Browser Tools): 0 passed, 0 failed, 6 skipped
- Group 05 (Skills Management): 0 passed, 0 failed, 8 skipped
- Group 06 (Skills-Tool Integration): 0 passed, 0 failed, 9 skipped
- Group 07 (Memory Management): 3 passed, 12 failed, 0 skipped ❌ Critical
- Group 08 (Deep Research): 10 passed, 0 failed, 1 skipped
- Group 09 (Long Context): 12 passed, 1 failed, 0 skipped
- Group 10 (Hybrid Search): 13 passed, 0 failed, 0 skipped ✅
- Group 11 (Document Upload): 12 passed, 2 failed, 0 skipped
- Group 12 (Graph Communities): 14 passed, 1 failed, 1 skipped
- Group 13 (Agent Hierarchy): 2 passed, 6 failed, 0 skipped ❌ Critical
- Group 14 (GDPR/Audit): 4 passed, 10 failed, 0 skipped ❌ Critical
- Group 15 (Explainability): 4 passed, 10 failed, 0 skipped ❌ Critical
- Group 16 (MCP Marketplace): 0 passed, 6 failed, 0 skipped ❌ Critical (Sprint 107)

**Bugs Identified:** 9 issues (BUG 108.0A - 108.0B, 108.1 - 108.8)
**Bugs Fixed:** 1 issue (BUG 108.0A - Route registration)
**Estimated Total SP:** 37 SP for all bug fixes

---

## Notes

- Reference Pattern: Group 03 (Python Execution) - 100% passing, use as template
- Auth Pattern: `setupAuthMocking(page)` in beforeEach
- Navigation: Always use `page.goto()` not `navigateClientSide()`
- API Mocks: Set up in beforeEach BEFORE navigation
- Sprint 107 Fixes: verify_connectivity and Qdrant stats should resolve some Group 07 issues

---

**Next Sprint:** TBD (depends on Sprint 108 completion)
