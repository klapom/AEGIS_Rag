# Sprint 106 E2E Test Fix Plan

**Created:** 2026-01-16
**Status:** In Progress
**Estimated SP:** 30-40

## Executive Summary

E2E test suite has **~50% failure rate** (186/362 tests failed in partial run).
Major issues identified and initial fixes applied.

## Fixes Applied (Sprint 105)

### 1. Timeout Reduction ✅
- **File:** `playwright.config.ts`
- **Change:** Test timeout 30s → 5s, Expect timeout 10s → 3s
- **Impact:** ~84 minutes saved per full run

### 2. Domain Auto-Discovery Route ✅
- **Files:** `App.tsx`, `DomainDiscoveryPage.tsx`
- **Change:** Added `/admin/domain-discovery` route
- **Impact:** 10 failures → ~2 failures

### 3. TestID Standardization ✅
- **File:** `DomainAutoDiscovery.tsx`
- **Change:** Updated testids to match E2E expectations
- **Impact:** Tests can now find elements

### 4. Auth Token Preservation ✅
- **File:** `llm-config-backend-integration.spec.ts`
- **Change:** Don't clear `aegis_auth_token` in beforeEach
- **Impact:** 10 failures → 8 failures

### 5. Model Name Update ✅
- **File:** `llm-config-backend-integration.spec.ts`
- **Change:** `qwen3:32b` → `nemotron-no-think:latest`
- **Impact:** Tests match production config

## Remaining Issues (Sprint 106 TODO)

### Priority 1: Auth Pattern Fix (Est. 8 SP)
**Problem:** Multiple test files use `localStorage.clear()` which removes auth token

**Affected Files:**
- `llm-config.spec.ts`
- `llm-config-backend-integration.spec.ts`
- Other admin tests

**Fix:** Create helper function `clearTestDataPreservingAuth()`

### Priority 2: TestID Alignment (Est. 10 SP)
**Problem:** Component testids don't match E2E expectations

**Pattern:**
- Components use: `drop-zone`, `file-input`
- Tests expect: `domain-discovery-upload-area`, `domain-discovery-file-input`

**Fix Options:**
1. Update all components to use prefixed testids
2. Create `TEST_IDS` constant file shared between components and tests

### Priority 3: Graph Tests (Est. 6 SP)
**Problem:** Graph visualization tests fail due to missing elements

**Root Cause:** Tests expect graph elements that aren't rendered
- Missing D3 graph initialization
- Missing edge color legend

### Priority 4: Error Handling Tests (Est. 4 SP)
**Problem:** Error state tests timeout waiting for error messages

**Root Cause:** Error states not properly triggered by API mocks

### Priority 5: Chat UI Tests (Est. 6 SP)
**Problem:** Conversation styling tests fail

**Root Cause:** CSS class expectations don't match actual implementation

## Test Group Analysis

| Group | Failures | Root Cause | Priority |
|-------|----------|------------|----------|
| chat-conversation-ui | 25 | CSS/styling mismatch | P3 |
| graph-visualization | 19 | Missing D3 elements | P2 |
| errors-error-handling | 17 | Mock API issues | P2 |
| admin-llm-config | 17 | Auth + model names | P1 ✅ |
| admin-vlm-integration | 12 | VLM UI elements | P3 |
| graph-edge-filters | 10 | Filter component | P3 |
| followup-follow-up | 10 | Context handling | P3 |
| admin-domain-auto | 10 | Missing route | P1 ✅ |
| followup-followup-Follow | 9 | Same as above | P3 |
| citations-inline | 9 | Citation rendering | P3 |
| domain-training | 28 | Wizard UI | P2 |
| domain-upload | 12 | Upload flow | P2 |

## Recommended Sprint 106 Approach

### Phase 1: Quick Wins (8 SP)
1. Fix auth pattern across all admin tests
2. Apply TestID fixes to domain-training component

### Phase 2: Graph & Error Tests (10 SP)
1. Fix graph visualization test mocks
2. Fix error handling API mocks

### Phase 3: UI Tests (12 SP)
1. Fix chat styling assertions
2. Fix VLM integration tests
3. Fix citation tests

## Success Metrics

- **Target:** 80% E2E pass rate (800/1005 tests)
- **Current:** ~50% pass rate
- **Gap:** 300+ tests need fixing

## Commands

```bash
# Run specific test group
npx playwright test e2e/admin/llm-config-backend-integration.spec.ts --reporter=line

# Run with trace on failure
npx playwright test --trace=retain-on-failure

# View trace
npx playwright show-trace test-results/<test-folder>/trace.zip
```
