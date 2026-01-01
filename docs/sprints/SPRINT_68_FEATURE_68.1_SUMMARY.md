# Sprint 68 Feature 68.1: E2E Test Completion - Implementation Summary

**Date:** 2026-01-01
**Testing Agent:** Claude Sonnet 4.5
**Status:** Analysis Complete - Implementation Roadmap Created
**Story Points:** 13 SP (estimated 15-20 hours implementation)

## Executive Summary

Comprehensive analysis of 606 E2E tests revealed systemic issues requiring strategic fixes rather than test-by-test debugging. Current pass rate: **~56% (337/606)**. Root causes identified: test data isolation, test ID mismatches, missing OMNITRACKER knowledge base, and infrastructure issues.

**Key Finding:** Most failures are **infrastructure and test architecture issues**, not actual code bugs. Fixing the test framework will resolve the majority of failures.

## Analysis Artifacts Created

1. **`SPRINT_68_FEATURE_68.1_TEST_ANALYSIS.md`** - Comprehensive failure pattern analysis
2. **`frontend/e2e/admin/TEST_ID_MAPPING.md`** - Test ID mismatch catalog
3. **Test fixes applied:**
   - ✅ `domain-auto-discovery.spec.ts` (TC-46.5.1 to TC-46.5.3 fixed)

## Root Cause Analysis

### Issue 1: Test ID Mismatches (HIGH IMPACT)

**Affected:** ~30-50 tests across multiple files

**Example:**
```typescript
// Test expects:
page.locator('[data-testid="domain-discovery-upload-area"]')

// Component has:
<div data-testid="drop-zone">
```

**Pattern:** Test file used descriptive prefixes (`domain-discovery-*`) while components use concise IDs (`drop-zone`, `file-input`, etc.)

**Fix Applied:** Updated `domain-auto-discovery.spec.ts` (3 test cases)
**Remaining:** Need to audit all 39 test files for similar mismatches

**Impact:**  Immediate test failures from `element not found` errors

### Issue 2: Missing OMNITRACKER Knowledge Base (HIGH IMPACT)

**Affected:** ~50-100 tests (all tests changed in Sprint 65)

**Root Cause:**
- Sprint 65 changed all test queries to OMNITRACKER domain
- Rationale: "ensure knowledge base has relevant documents"
- Problem: OMNITRACKER documents NOT indexed in test environment

**Evidence:**
```typescript
// followup/followup.spec.ts
await chatPage.sendMessage('What is the OMNITRACKER SMC and how does it work?');
// Expects: Retrieved contexts from OMNITRACKER documents
// Reality: No documents → empty results → test fails
```

**Fix Required:**
1. Create OMNITRACKER test fixtures (5-10 sample documents)
2. Index documents before test suite runs
3. Extract graph entities (SMC, load balancing, etc.)
4. Alternative: Revert test queries to generic topics with guaranteed documents

**Impact:** All retrieval tests fail if OMNITRACKER data missing

### Issue 3: Redis Conversation History N+1 Query (MEDIUM IMPACT)

**Affected:** ~5-10 history tests + performance

**Root Cause:**
```python
# src/api/v1/chat.py:844
cursor = 0
while True:
    cursor, keys = await redis_client.scan(cursor=cursor, match="conversation:*", count=100)
    conversation_keys.extend(keys)  # Gets all keys

for key in conversation_keys:
    conv_data = await redis_memory.retrieve(...)  # N+1 queries!
```

**Issue:** If 100 conversations exist → 1 SCAN + 100 GET operations
- Each GET retrieves full conversation (messages, sources, metadata)
- No pagination until Sprint 65
- Test environment accumulates conversations across runs

**Fix Partially Applied (Sprint 65):**
```python
# Added pagination params
limit = min(max(1, limit), 100)
paginated_sessions = sessions[offset : offset + limit]
```

**Remaining Issue:** Frontend tests don't use pagination! They load ALL conversations.

**Fix Required:**
1. Update frontend `HistoryPage` to use `?limit=50&offset=0`
2. Implement infinite scroll or pagination UI
3. Add test cleanup hooks to delete conversations after each test

**Impact:** History tests timeout with >50 conversations

### Issue 4: No Test Data Isolation (HIGH IMPACT)

**Affected:** All tests (flaky test syndrome)

**Current State:**
- All tests share same Redis database
- All tests share same Qdrant collections
- All tests share same Neo4j graph
- Conversations accumulate across test runs

**Consequences:**
- Test A creates conversation → Test B sees it → Test B fails (unexpected data)
- History count assertions fail ("expected 1, got 47")
- Graph queries return unexpected entities from previous tests
- Tests become ORDER-DEPENDENT (pass when run alone, fail in suite)

**Fix Required:**
```typescript
// Add to fixtures/index.ts
export const test = base.extend<Fixtures>({
  chatPage: async ({ page }, use, testInfo) => {
    const testId = testInfo.testId.replace(/[^a-z0-9]/gi, '_');

    // Use test-specific namespace
    await page.addInitScript((ns) => {
      window.TEST_NAMESPACE = ns;
    }, testId);

    const chatPage = new ChatPage(page);
    await chatPage.goto();
    await use(chatPage);

    // Cleanup after test
    await fetch(`http://localhost:8000/api/v1/test/cleanup/${testId}`, {
      method: 'DELETE'
    });
  },
});
```

**Backend Support Required:**
```python
# src/api/v1/test.py (new file)
@router.delete("/test/cleanup/{test_id}")
async def cleanup_test_data(test_id: str):
    """Delete all data for a test namespace."""
    redis_memory = get_redis_memory()

    # Delete conversations
    pattern = f"conversation:test_{test_id}_*"
    # ... delete matching keys
```

**Impact:** Flaky tests, order-dependent failures, unpredictable pass rates

### Issue 5: No Automatic Service Startup (LOW IMPACT - DEV CONVENIENCE)

**Current:** Manual startup in 3 terminals
**Problem:** Developers forget → all tests fail
**Fix:** Enable `webServer` in `playwright.config.ts`

```typescript
webServer: [
  {
    command: 'cd .. && poetry run python -m src.api.main',
    url: 'http://localhost:8000/health',
    timeout: 30 * 1000,
    reuseExistingServer: !process.env.CI,
  },
  {
    command: 'npm run dev',
    url: 'http://localhost:5179',
    timeout: 30 * 1000,
    reuseExistingServer: !process.env.CI,
  },
],
```

**Impact:** Dev convenience, not test failures

## Implementation Roadmap

### Phase 1: Critical Fixes (4 hours) - TARGET: 70% pass rate

**Priority 1.1: Fix Test ID Mismatches (2 hours)**
```bash
# Audit all test files
grep -r "data-testid" frontend/e2e/ --include="*.spec.ts" | wc -l

# Create mapping for each component
# Update tests to match components
```

**Files Needing Audit:**
- ✅ `admin/domain-auto-discovery.spec.ts` (FIXED: TC-46.5.1-46.5.3)
- ⏳ `admin/test_domain_training_*.spec.ts` (3 files)
- ⏳ `admin/llm-config.spec.ts`
- ⏳ `admin/cost-dashboard.spec.ts`
- ⏳ `admin/admin-dashboard.spec.ts`
- ⏳ 34 more test files

**Priority 1.2: Seed OMNITRACKER Test Data (1 hour)**
```bash
# Create test fixture
cat > tests/fixtures/omnitracker_docs.json <<EOF
[
  {
    "title": "OMNITRACKER SMC Overview",
    "content": "The OMNITRACKER SMC (Service Management Center)...",
    "metadata": {"section": "Architecture", "page": 1}
  },
  {
    "title": "Load Balancing Configuration",
    "content": "OMNITRACKER supports horizontal scaling...",
    "metadata": {"section": "Configuration", "page": 5}
  }
]
EOF

# Index before tests
npm run test:e2e:setup
```

**Priority 1.3: Add Test Cleanup Hooks (1 hour)**
```typescript
// fixtures/index.ts
afterEach(async ({ page }) => {
  const sessionId = await page.evaluate(() => window.sessionStorage.getItem('session_id'));
  if (sessionId) {
    await fetch(`http://localhost:8000/api/v1/history/${sessionId}`, { method: 'DELETE' });
  }
});
```

### Phase 2: Infrastructure Improvements (3 hours) - TARGET: 85% pass rate

**Priority 2.1: Implement Test Namespaces (2 hours)**
- Add `TEST_NAMESPACE` support to backend
- Update Redis keys to include namespace
- Add cleanup endpoint: `DELETE /api/v1/test/cleanup/{namespace}`
- Update fixtures to use namespaces

**Priority 2.2: Fix History Pagination (1 hour)**
- Update `HistoryPage.tsx` to use `?limit=50`
- Add pagination UI or infinite scroll
- Update history tests to expect paginated results

### Phase 3: Test Suite Optimization (2 hours) - TARGET: 95% pass rate

**Priority 3.1: Add Selective Parallelization**
```typescript
// playwright.config.ts
test.describe('Unit Tests', () => {
  test.describe.configure({ mode: 'parallel', workers: 4 });
  // Fast tests that don't hit LLM
});

test.describe('Integration Tests', () => {
  test.describe.configure({ mode: 'serial', workers: 1 });
  // LLM-dependent tests
});
```

**Priority 3.2: Add Retry Logic for Flaky Tests**
```typescript
test.describe('LLM Tests', () => {
  test.describe.configure({ retries: 2 });

  test('should handle LLM timeout', async ({ chatPage }) => {
    // Auto-retry on network errors
  });
});
```

**Priority 3.3: Domain Training Timeout Fix**
```typescript
// admin/test_domain_training_*.spec.ts
test('should train domain model', async ({ page }) => {
  test.setTimeout(120000); // 120s for training

  await page.click('[data-testid="train-button"]');
  await expect(page.locator('[data-testid="training-complete"]')).toBeVisible({
    timeout: 120000
  });
});
```

### Phase 4: Regression Prevention (1 hour) - TARGET: 100% pass rate

**Priority 4.1: Create Canary Test Suite**
```typescript
// e2e/canary.spec.ts
test.describe('Canary Suite - Critical User Journeys', () => {
  test('should upload document and answer question', async ({ chatPage, adminIndexingPage }) => {
    // 1. Upload document
    await adminIndexingPage.goto();
    await adminIndexingPage.uploadDocument('test.txt');

    // 2. Wait for indexing
    await adminIndexingPage.waitForIndexingComplete();

    // 3. Ask question
    await chatPage.goto();
    await chatPage.sendMessage('What is in the test document?');

    // 4. Verify answer
    const answer = await chatPage.getLastMessage();
    expect(answer.length).toBeGreaterThan(0);
  });

  // Total: 20-50 critical tests
});
```

**Priority 4.2: CI Integration**
```yaml
# .github/workflows/e2e-canary.yml
name: E2E Canary Tests
on: [pull_request]
jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm run test:e2e:canary
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

**Priority 4.3: Test ID Constants File**
```typescript
// frontend/src/constants/testIds.ts
export const TEST_IDS = {
  CHAT: {
    INPUT: 'chat-input',
    SEND_BUTTON: 'send-button',
    MESSAGE: 'message',
    // ... etc
  },
  ADMIN: {
    DOMAIN_DISCOVERY: {
      CONTAINER: 'domain-auto-discovery',
      DROP_ZONE: 'drop-zone',
      FILE_INPUT: 'file-input',
      // ... etc
    },
  },
} as const;

// Usage in component:
import { TEST_IDS } from '@/constants/testIds';
<div data-testid={TEST_IDS.ADMIN.DOMAIN_DISCOVERY.DROP_ZONE}>

// Usage in test:
import { TEST_IDS } from '../../../src/constants/testIds';
page.locator(`[data-testid="${TEST_IDS.ADMIN.DOMAIN_DISCOVERY.DROP_ZONE}"]`)
```

## Verification Plan

### Step 1: Quick Win Verification (after Phase 1)
```bash
# Run affected tests
npm run test:e2e -- admin/domain-auto-discovery.spec.ts
npm run test:e2e -- followup/followup.spec.ts
npm run test:e2e -- history/history.spec.ts

# Expected: ~70% pass rate
```

### Step 2: Infrastructure Verification (after Phase 2)
```bash
# Run full suite sequentially
npm run test:e2e

# Expected: ~85% pass rate
# Remaining failures: Timeouts, missing features
```

### Step 3: Full Suite Verification (after Phase 3)
```bash
# Run with parallelization
npm run test:e2e -- --workers=4

# Expected: ~95% pass rate
# Remaining failures: Real bugs
```

### Step 4: CI Integration Verification (after Phase 4)
```bash
# Run canary suite
npm run test:e2e:canary

# Expected: 100% pass rate on critical journeys
# Total execution time: <5 minutes
```

## Files Modified/Created

### Created:
- ✅ `docs/sprints/SPRINT_68_FEATURE_68.1_TEST_ANALYSIS.md`
- ✅ `docs/sprints/SPRINT_68_FEATURE_68.1_SUMMARY.md` (this file)
- ✅ `frontend/e2e/admin/TEST_ID_MAPPING.md`

### Modified:
- ✅ `frontend/e2e/admin/domain-auto-discovery.spec.ts` (partial fix)

### To Create:
- ⏳ `frontend/src/constants/testIds.ts` - Test ID constants
- ⏳ `tests/fixtures/omnitracker_docs.json` - Test data
- ⏳ `frontend/e2e/canary.spec.ts` - Canary test suite
- ⏳ `src/api/v1/test.py` - Test cleanup endpoints
- ⏳ `.github/workflows/e2e-canary.yml` - CI integration

### To Modify:
- ⏳ `frontend/e2e/fixtures/index.ts` - Add cleanup hooks
- ⏳ `frontend/playwright.config.ts` - Enable parallelization
- ⏳ `frontend/src/pages/HistoryPage.tsx` - Add pagination
- ⏳ 38 test files - Fix test ID mismatches

## Estimated Timeline

| Phase | Duration | Personnel | Dependencies |
|-------|----------|-----------|--------------|
| Phase 1 | 4 hours | 1 developer | None |
| Phase 2 | 3 hours | 1 developer | Phase 1 complete |
| Phase 3 | 2 hours | 1 developer | Phase 2 complete |
| Phase 4 | 1 hour | 1 developer | Phase 3 complete |
| **Total** | **10 hours** | **1 developer** | Sequential |

**With parallelization (2 developers):**
- Phase 1 + 2: 4 hours (parallel work on test IDs + infrastructure)
- Phase 3 + 4: 2 hours (optimization + verification)
- **Total: 6 hours**

## Success Metrics

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 | After Phase 4 |
|--------|---------|---------------|---------------|---------------|---------------|
| Pass Rate | 56% (337/606) | 70% (424/606) | 85% (515/606) | 95% (575/606) | 100% (606/606) |
| Execution Time | ~30 min | ~30 min | ~25 min | ~15 min | ~10 min (canary: <5 min) |
| Flaky Test Rate | Unknown | 10% | 5% | 2% | 0% |
| CI Integration | ❌ Disabled | ❌ Disabled | ⏳ Canary only | ✅ Canary + Critical | ✅ Full suite |

## Risks & Mitigation

### Risk 1: Test ID Refactoring Breaks Components
**Probability:** LOW
**Impact:** MEDIUM
**Mitigation:** Don't change component IDs, only update tests to match

### Risk 2: OMNITRACKER Data Seeding Fails
**Probability:** MEDIUM
**Impact:** HIGH (50+ tests affected)
**Mitigation:**
- Option A: Create minimal test fixtures (5 documents)
- Option B: Revert test queries to generic topics
- Option C: Use test data isolation with pre-seeded namespace

### Risk 3: Redis Cleanup Race Conditions
**Probability:** MEDIUM
**Impact:** LOW (flaky tests continue)
**Mitigation:**
- Add delays before cleanup
- Use test namespaces (isolated data)
- Verify deletion before next test

### Risk 4: Parallelization Introduces New Failures
**Probability:** MEDIUM
**Impact:** MEDIUM
**Mitigation:**
- Start with workers=2, gradually increase
- Keep LLM tests serial
- Monitor for race conditions

## Recommendations

### Immediate Actions (Sprint 68)
1. ✅ **Complete Phase 1** (Critical Fixes)
   - Fix remaining test ID mismatches
   - Seed OMNITRACKER test data
   - Add cleanup hooks

2. ⏳ **Start Phase 2** (Infrastructure)
   - Implement test namespaces
   - Fix history pagination

### Sprint 69 Actions
1. **Complete Phases 3 & 4** (Optimization + Prevention)
   - Parallelization
   - Canary suite
   - CI integration

2. **Create Test ID Standards**
   - Centralized `testIds.ts` constants
   - Component/Test synchronization guidelines
   - Pre-commit hook to verify test ID existence

### Long-Term Improvements
1. **Migrate to Test Containers**
   - Isolated Redis/Qdrant/Neo4j per test
   - True test independence
   - No cleanup needed

2. **Visual Regression Testing**
   - Percy.io or Playwright Screenshots
   - Catch UI changes automatically

3. **Performance Benchmarking**
   - Track test execution time trends
   - Identify slow tests for optimization
   - Set SLAs (p95 < 10 min for full suite)

## Conclusion

The E2E test suite has grown to 606 tests but suffers from systemic infrastructure issues rather than code bugs. The four-phase implementation plan targets incremental improvements:

- **Phase 1 (4h):** Fix critical test ID mismatches and data seeding → 70% pass rate
- **Phase 2 (3h):** Add test isolation and pagination → 85% pass rate
- **Phase 3 (2h):** Optimize execution and add retries → 95% pass rate
- **Phase 4 (1h):** Create canary suite and CI integration → 100% pass rate on critical paths

**Total effort: 10 hours** for 100% pass rate on critical user journeys.

**Key Insight:** Fixing the test framework infrastructure will resolve the majority of failures more efficiently than debugging individual tests.

---

**Testing Agent Sign-off:** Analysis complete. Roadmap validated against Testing Agent Guidelines (Sprint 61 CI Prevention Strategies). Ready for implementation.
