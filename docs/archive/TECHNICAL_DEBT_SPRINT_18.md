# Technical Debt Tracking - Sprint 18

**Created:** 2025-10-29
**Sprint:** 18
**Status:** 📋 PLANNED

---

## Overview

This document tracks all technical debt items from Sprint 17 and earlier that need to be addressed in Sprint 18, plus any new debt discovered during development.

---

## Sprint 17 Carryover Debt

### TD-38: Test Selector Modernization ⚠️ HIGH PRIORITY
**Status:** 📋 Planned for Sprint 18
**Effort:** 5 SP
**Affected Files:** 5 E2E test files
**Root Cause:** Tests use `getByText()` which finds multiple elements

**Problem:**
- 44 E2E tests failing from Sprint 15/16
- Brittle selectors break when UI structure changes
- Multiple element issues cause non-deterministic failures

**Solution:**
```typescript
// BEFORE (brittle)
getByText('Hybrid')  // ❌ Finds multiple "Hybrid" texts

// AFTER (resilient)
getByRole('button', { name: 'Hybrid Mode' })  // ✅ Specific and accessible
within(modeSelector).getByText('Hybrid')       // ✅ Scoped query
getByTestId('mode-hybrid-button')              // ✅ Unique identifier
```

**Action Items:**
- [ ] Add `data-testid` to ambiguous UI elements (mode selectors, tabs, loading indicators)
- [ ] Replace `getByText` with `getByRole` for better accessibility
- [ ] Use `within()` for scoped queries to avoid multiple element issues
- [ ] Update 5 failing test files:
  - `HomePage.e2e.test.tsx` (6 tests)
  - `SearchResultsPage.e2e.test.tsx` (17 tests)
  - `FullWorkflow.e2e.test.tsx` (11 tests)
  - `SSEStreaming.e2e.test.tsx` (9 tests)
  - `ErrorHandling.e2e.test.tsx` (1 test)

**Benefits:**
- More resilient tests that survive UI refactoring
- Better accessibility validation
- Clearer test intent

**Timeline:** Days 1-2 of Sprint 18

---

### TD-39: Mock Data Synchronization ⚠️ MEDIUM PRIORITY
**Status:** 📋 Planned for Sprint 18
**Effort:** 3 SP
**Affected Files:** `frontend/src/test/fixtures.ts`, multiple test files

**Problem:**
- Mock responses don't match current API structure
- Tests expect old field names/structures
- Difficult to maintain as API evolves

**Solution:**
```typescript
// Create type-safe mock generator
import { SystemStats } from '../types/admin';

function generateMockFromType<T>(partial: Partial<T>): T {
  // Type-safe mock creation with compiler validation
}

const mockStats = generateMockFromType<SystemStats>({
  qdrant_total_chunks: 1523,
  // Compiler ensures all required fields present
});

// Validation test
it('mocks match current API structure', () => {
  expectType<SystemStats>(mockAdminStats);  // ✅ Compile-time check
});
```

**Action Items:**
- [ ] Audit all mock data in `fixtures.ts`
- [ ] Compare with current API responses
- [ ] Update mocks to match OpenAPI spec
- [ ] Create mock generator utility
- [ ] Add validation tests for mocks
- [ ] Document mock update process

**Benefits:**
- Reduced test brittleness
- Easier API evolution
- Compile-time validation of test data

**Timeline:** Day 3 of Sprint 18

---

### TD-40: Test Helper Library 🔵 LOW PRIORITY
**Status:** 📋 Planned for Sprint 18
**Effort:** 3 SP
**Affected Files:** All test files

**Problem:**
- Duplicate test code across files
- Inconsistent wait/retry logic
- Poor error messages in tests

**Solution:**
```typescript
// test/utils/helpers.ts
export async function waitForStreamingComplete(timeout = 5000) {
  await waitFor(() => {
    expect(screen.queryByText(/Suche läuft/i)).not.toBeInTheDocument();
  }, { timeout });
}

export function selectMode(mode: 'hybrid' | 'vector' | 'graph' | 'memory') {
  const button = screen.getByRole('button', { name: new RegExp(mode, 'i') });
  fireEvent.click(button);
}

// Custom matcher
expect.extend({
  toHaveSourceCards(received, expectedCount) {
    const sources = within(received).queryAllByTestId('source-card');
    return {
      pass: sources.length === expectedCount,
      message: () => `Expected ${expectedCount} sources, found ${sources.length}`
    };
  }
});

// Usage
await waitForStreamingComplete();
selectMode('hybrid');
expect(resultsContainer).toHaveSourceCards(3);
```

**Action Items:**
- [ ] Create `test/utils/` directory
- [ ] Build common test helpers (5+ utilities)
- [ ] Create custom matchers (3+ matchers)
- [ ] Improve error messages
- [ ] Write testing guide with examples
- [ ] Document best practices

**Benefits:**
- DRY test code (50% reduction in duplication)
- Improved developer experience
- Better test failure messages

**Timeline:** Day 5 of Sprint 18

---

## New Technical Debt (Sprint 17)

### TD-41: Admin Stats Endpoint 404 Issue 🔴 CRITICAL
**Status:** 🐛 BUG - Discovered 2025-10-29
**Effort:** 2 SP
**Severity:** HIGH

**Problem:**
- `/api/v1/admin/stats` endpoint returns 404 at runtime
- Endpoint exists in router when tested programmatically
- Frontend shows error when accessing Admin Dashboard

**Evidence:**
```bash
# Programmatic test shows endpoint exists:
$ python -c "from src.api.v1 import admin; print([r.path for r in admin.router.routes])"
['/api/v1/admin/reindex', '/api/v1/admin/stats']  # ✅ Endpoint registered

# But HTTP request fails:
$ curl http://localhost:8000/api/v1/admin/stats
{"detail":"Not Found"}  # ❌ 404 error
```

**Root Cause:** Unknown - requires investigation
- Possible router registration timing issue
- FastAPI route matching problem
- Middleware interference

**Action Items:**
- [ ] Investigate FastAPI router registration order
- [ ] Check if admin router prefix causes conflict
- [ ] Test with explicit path `/api/v1/admin/stats` vs relative `/stats`
- [ ] Verify main.py router inclusion order
- [ ] Check for middleware that might block the route
- [ ] Add integration test for admin stats endpoint

**Workaround:** None currently

**Impact:**
- Admin Dashboard statistics section unusable
- Cannot view system health metrics
- User experience degraded

**Timeline:** Day 1 of Sprint 18 (urgent fix)

---

### TD-42: Import Error Prevention System 🟡 MEDIUM
**Status:** ✅ PARTIALLY RESOLVED
**Effort:** 2 SP
**Created:** 2025-10-29 (from Sprint 17 bugs)

**Problem:**
- Two import errors discovered at deployment time:
  1. `chat.py`: Forward reference `SourceDocument` not quoted
  2. `admin.py`: Missing `BaseModel, Field` imports

**Fix Applied:**
```python
# chat.py - Forward reference fix
async def save_conversation_turn(
    sources: list["SourceDocument"] | None = None,  # ✅ Quoted forward ref
)

# admin.py - Import fix
from pydantic import BaseModel, Field  # ✅ Top-level import
```

**Remaining Work:**
- [ ] Add pre-commit hook for import validation
- [ ] CI check for Python import errors (✅ Added in ci-sprint-18.yml)
- [ ] Lint rule for forward references
- [ ] Documentation on forward reference best practices

**Benefits:**
- Catch import errors before deployment
- Prevent backend startup failures
- Faster development feedback

**Timeline:** Day 2 of Sprint 18

---

## Historical Technical Debt (Pre-Sprint 17)

### TD-26 to TD-37: RESOLVED ✅
All technical debt items TD-26 through TD-37 from Sprint 13 and earlier have been resolved in Sprint 14-16.

See:
- Sprint 13 completion report
- Sprint 14 ADR-019 (Integration Tests)
- Sprint 16 unified chunking strategy

---

## Sprint 18 Quality Metrics

### Target Metrics
| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| E2E Test Pass Rate | 76% (140/184) | 95%+ | 🔴 BELOW TARGET |
| Test Execution Time | 33s | <40s | ✅ PASS |
| Code Coverage (Backend) | 85% | >80% | ✅ PASS |
| Code Coverage (Frontend) | TBD | >70% | ⚠️ TO MEASURE |
| Import Errors | 0 | 0 | ✅ PASS |

### Quality Gates
- ✅ All Python imports validate without errors
- ✅ Frontend builds without TypeScript errors
- ⚠️ E2E tests achieve 95%+ pass rate
- ✅ No critical security vulnerabilities
- ✅ API contracts validated

---

## Lessons Learned

### From Sprint 17 Issues

**1. Import Validation is Critical**
- **Lesson:** Import errors only manifest at runtime, not in IDEs
- **Action:** CI pipeline now validates all Python imports (TD-42)
- **Prevention:** Pre-commit hooks for import checking

**2. Forward References Need Quotes**
- **Lesson:** `list[SourceDocument]` fails if class defined later
- **Action:** Always use `list["SourceDocument"]` for forward refs
- **Prevention:** Lint rule in Ruff config

**3. Test Brittleness Compounds Over Time**
- **Lesson:** 44 failing tests from text-based selectors
- **Action:** Modernize to role-based selectors (TD-38)
- **Prevention:** Test selector guidelines in docs

**4. Mock Drift Causes False Confidence**
- **Lesson:** Tests passed with outdated mock data
- **Action:** Type-safe mock generator (TD-39)
- **Prevention:** OpenAPI contract validation

---

## Priority Matrix

```
 High Impact │ TD-41 (Stats 404)     │ TD-38 (Test Selectors) │
             │ 🔴 CRITICAL           │ ⚠️ HIGH                │
             │ Blocks deployment     │ Test quality           │
─────────────┼───────────────────────┼────────────────────────┤
Medium Impact│ TD-42 (Import Check)  │ TD-39 (Mock Sync)      │
             │ 🟡 MEDIUM             │ 🟡 MEDIUM              │
             │ CI improvement        │ Maintenance            │
─────────────┼───────────────────────┼────────────────────────┤
 Low Impact  │                       │ TD-40 (Test Helpers)   │
             │                       │ 🔵 LOW                 │
             │                       │ DX improvement         │
─────────────┴───────────────────────┴────────────────────────
             Low Effort              High Effort
```

**Sprint 18 Focus Order:**
1. 🔴 TD-41 (Admin Stats 404) - Day 1
2. 🟡 TD-42 (Import Checks) - Day 2
3. ⚠️ TD-38 (Test Selectors) - Days 1-2
4. 🟡 TD-39 (Mock Sync) - Day 3
5. 🔵 TD-40 (Test Helpers) - Day 5

---

## Sprint 18 Success Criteria

**Must Have (Blocking):**
- ✅ TD-41 resolved (Admin stats working)
- ✅ TD-38 completed (95%+ test pass rate)
- ✅ No import errors in CI

**Should Have (Important):**
- ✅ TD-42 completed (import validation CI)
- ✅ TD-39 completed (mock synchronization)

**Nice to Have (Optional):**
- ⭕ TD-40 completed (test helpers)

---

**Document Maintained By:** Development Team
**Last Updated:** 2025-10-29
**Next Review:** Sprint 18 Completion
