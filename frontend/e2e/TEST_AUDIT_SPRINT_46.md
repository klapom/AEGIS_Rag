# E2E Test Audit Report - Sprint 46
**Date:** December 16, 2025
**Status:** IN PROGRESS
**Total Test Files:** 31
**Previous Sprint:** Sprint 45

---

## Executive Summary

Sprint 46 introduced new E2E tests for Features 46.1-46.8 (ConversationView, ReasoningPanel, AdminDashboard, DomainAutoDiscovery). This audit identifies outdated tests that conflict with new features and proposes fixes.

### Key Issues Identified

| Issue | Count | Severity | Impact |
|-------|-------|----------|--------|
| Auth-gated routes (settings page) | 1 | High | Tests fail on login redirect |
| Missing test data attributes | 3 | High | Tests cannot find elements |
| Outdated component selectors | 2 | Medium | Tests fail to locate components |
| Admin route consolidation | 5 | Medium | Tests reference old admin routes |
| SessionSidebar migration | 1 | Low | Component moved to chat/ |

---

## Test Files Overview (31 Total)

### NEW Sprint 46 Tests (3 Files)
**Status:** Ready for use ✓

1. **`e2e/chat/conversation-ui.spec.ts`** ✓
   - TC-46.1.x: ConversationView tests (15 tests)
   - TC-46.2.x: ReasoningPanel tests (13 tests)
   - Integration tests (3 tests)
   - **Status:** Working correctly, uses proper fixtures
   - **Note:** Tests may fail if backend is not running

2. **`e2e/admin/admin-dashboard.spec.ts`** ✓
   - TC-46.8.x: AdminDashboard unified interface (15 tests)
   - **Status:** Properly mocked, working
   - **Note:** Good example of flexible selector strategy (fallback selectors)

3. **`e2e/admin/domain-auto-discovery.spec.ts`** ✓
   - TC-46.5.x: Domain discovery UI (7 tests)
   - **Status:** Partially tested, some assertions may fail

4. **`e2e/admin/domain-discovery-api.spec.ts`** ✓
   - Domain discovery API tests (8+ tests)
   - **Status:** API-focused, working

### SMOKE Tests (1 File)
**Status:** 9 passed, 3 failed ⚠️

**`e2e/smoke.spec.ts`**
- ✓ Load homepage
- ✓ Backend health endpoint
- ✓ Backend connectivity
- ✓ Page navigation
- ✓ Frontend port verification
- ✗ Chat interface elements (missing data attributes)
- ✗ Message input/send button (missing data attributes)
- ✗ Settings page (auth required, redirects to login)

**Fixes needed:**
1. Settings page needs auth fixture or skip in smoke tests
2. Chat page locators need to match actual component rendering

### History Tests (1 File)
**Status:** Requires investigation 🔍

**`e2e/history/history.spec.ts`**
- Uses `historyPage` fixture correctly
- References moved SessionSidebar component
- **Issue:** May fail if component was moved from history/ to chat/
- **Status:** Needs verification with running app

### Search Tests (3 Files)
**Status:** Verify test data attributes

1. **`e2e/search/search.spec.ts`**
   - Vector search tests
   - **Status:** Verify `[data-testid]` attributes exist

2. **`e2e/search/intent.spec.ts`**
   - Intent classification tests
   - **Status:** Check API response mocking

3. **`e2e/search/namespace-isolation.spec.ts`**
   - Namespace isolation tests
   - **Status:** Verify data setup

### Admin Tests (10+ Files) - ⚠️ CRITICAL REVIEW NEEDED

**Status:** Mixed - Some outdated, some new

#### New Sprint 46 Tests (Already listed above)
- admin-dashboard.spec.ts ✓
- domain-auto-discovery.spec.ts ✓
- domain-discovery-api.spec.ts ✓

#### Potentially Outdated Tests
**These reference old admin routes/structure:**

1. **`e2e/admin/cost-dashboard.spec.ts`**
   - **Issue:** Routes to /dashboard/costs (old structure?)
   - **Status:** ❓ Verify route exists in current app

2. **`e2e/admin/indexing.spec.ts`** (37KB)
   - **Issue:** May reference /admin/indexing (consolidated into AdminDashboard?)
   - **Status:** ❓ Verify if this should merge with admin-dashboard

3. **`e2e/admin/llm-config.spec.ts`**
   - **Issue:** May reference old LLM config route
   - **Status:** ❓ Check if consolidated into AdminDashboard

4. **`e2e/admin/vlm-integration.spec.ts`**
   - **Issue:** VLM integration may be outdated
   - **Status:** ❓ Review if still relevant

#### Domain Training Tests (New, Sprint 45)
1. **`test_domain_training_api.spec.ts`**
2. **`test_domain_training_flow.spec.ts`**
3. **`test_domain_upload_integration.spec.ts`**
- **Status:** Recent additions, should be functional
- **Note:** Follow naming convention (test_ prefix should be removed)

### Citations Tests (1 File)
**`e2e/citations/citations.spec.ts`**
- **Status:** Verify citations UI still exists in new ConversationView

### Error Handling Tests (1 File)
**`e2e/errors/error-handling.spec.ts`**
- **Status:** Should work, uses generic error handling

### Follow-up Tests (1 File)
**`e2e/followup/followup.spec.ts`**
- **Status:** Verify followup questions UI in new ConversationView

### Graph Tests (4 Files)
1. **`e2e/graph/admin-graph.spec.ts`**
2. **`e2e/graph/edge-filters.spec.ts`**
3. **`e2e/graph/graph-visualization.spec.ts`**
4. **`e2e/graph/query-graph.spec.ts`**
- **Status:** Should be functional (graph features unchanged)
- **Note:** Verify graph visualization still accessible from new UI

### Settings Tests (1 File)
**`e2e/settings/settings.spec.ts`**
- **Status:** ⚠️ May require auth mocking (settings page may be protected)

### Additional Tests (6 Files)
**`e2e/tests/` subdirectory:**
1. `admin/pipeline-progress.spec.ts`
2. `auth/login.spec.ts`
3. `chat/conversation-search.spec.ts`
4. `chat/share-conversation.spec.ts`
5. `graph/entity-changelog.spec.ts`
6. `graph/time-travel.spec.ts`
- **Status:** Verify these follow new fixture pattern

---

## Key Changes from Sprint 45 to Sprint 46

### Component Migrations
- **SessionSidebar:** Moved from `/src/components/history/` to `/src/components/chat/`
- **AdminDashboard:** New unified admin interface at `/admin`
- **ConversationView:** New main chat component
- **ReasoningPanel:** New transparent reasoning display

### Routing Changes
- **Old:** `/admin/indexing`, `/admin/llm-config`, `/admin/graph`, etc.
- **New:** `/admin` (unified AdminDashboard with sections)
- **Preserved:** `/history`, `/settings`, `/search`, `/graph` (query visualization)

### Authentication
- Settings page now auth-gated (redirects to `/login` without auth)
- Admin pages require authentication
- Fixtures now include `setupAuthMocking()` for protected routes

---

## Test Fixture Analysis

### Current Fixtures Pattern (`e2e/fixtures/index.ts`)

**Good practices:**
- Page Object Models for each page
- Pre-configured fixtures reduce boilerplate
- Auth mocking centralized
- Proper use of `use()` pattern

**Fixtures available:**
```typescript
- chatPage: Pre-navigated to /
- historyPage: Pre-navigated to /history
- settingsPage: Pre-navigated to /settings (⚠️ requires auth?)
- adminIndexingPage: With auth mocking
- adminGraphPage: With auth mocking
- costDashboardPage: With auth mocking
- adminLLMConfigPage: With auth mocking
- adminDomainTrainingPage: With auth mocking
- authenticatedPage: Generic page with auth
- authChatPage: Chat with auth
```

### Fixture Issues

1. **settingsPage fixture:**
   - Doesn't include auth mocking
   - Smoke test fails with "redirects to /login"
   - **Fix:** Add auth mocking OR update test expectations

2. **Missing fixtures for Sprint 46:**
   - No fixture for AdminDashboard at `/admin`
   - Domain discovery page needs fixture
   - **Fix:** Add AdminDashboardPage fixture

---

## Recommendations

### Priority 1: Critical Fixes (Required for tests to run)

1. **Fix settingsPage fixture** (affects smoke tests)
   - Add `setupAuthMocking()` to settingsPage fixture
   - OR skip settings test in smoke.spec.ts with note
   - **Impact:** 1 failing test

2. **Verify chat page selectors** (affects smoke tests)
   - Check if `[data-testid="message-input"]` exists on new ConversationView
   - Check if `[data-testid="send-button"]` exists
   - **Impact:** 2 failing tests

3. **Create AdminDashboardPage fixture**
   - Follows pattern of existing page objects
   - Needed for admin tests
   - **Impact:** Improves test maintainability

### Priority 2: Important Updates

1. **Review admin route consolidation**
   - Verify old routes (/admin/indexing, /admin/llm-config) still exist
   - If consolidated, update tests to point to /admin sections
   - **Files affected:** cost-dashboard.spec.ts, indexing.spec.ts, llm-config.spec.ts

2. **Verify SessionSidebar location**
   - Check if history.spec.ts still works with new location
   - **File affected:** history.spec.ts

3. **Update domain training test naming**
   - Rename test_domain_training_*.spec.ts to domain-training-*.spec.ts
   - Follows convention: no test_ prefix
   - **Files affected:** 3 files

### Priority 3: Nice to Have

1. **Improve test selectors**
   - Use both primary and fallback selectors (like admin-dashboard.spec.ts does)
   - Reduces brittleness when UI changes slightly

2. **Add skip/xtest comments**
   - Mark tests that require manual verification
   - Document why they're skipped

3. **Document E2E test strategy**
   - List which tests require backend
   - Which tests are fully mocked
   - Performance expectations (p95 latencies)

---

## Test Execution Strategy

### Prerequisites
- Backend running on http://localhost:8000
- Frontend running on http://localhost:5179
- Ollama or configured LLM service running
- Qdrant, Neo4j, Redis (optional for mocked tests)

### Test Categories

| Category | Count | Run Time | Backend Required | Mocked |
|----------|-------|----------|------------------|--------|
| Smoke Tests | 12 | ~40s | Yes | Partial |
| Chat/Conversation | 31 | ~60s | Yes | No |
| History | 8 | ~40s | Yes | No |
| Search | ~20 | ~60s | Yes | No |
| Admin | ~50 | ~120s | Yes | Partial |
| Graph | ~20 | ~60s | Yes | No |
| Settings | ~10 | ~30s | Yes* | Partial |
| **TOTAL** | **~150** | **~5min** | **Yes** | **Mixed** |

*Settings requires auth (now detected)

### Recommended Test Runs

```bash
# Quick smoke test (3 min, infrastructure only)
npx playwright test e2e/smoke.spec.ts --reporter=list

# Chat features (includes new Sprint 46 features)
npx playwright test e2e/chat --reporter=list

# All tests with coverage
npx playwright test --reporter=html

# Run specific test with tracing
npx playwright test e2e/chat/conversation-ui.spec.ts --trace=on
```

---

## Fixed Issues Summary

### Smoke Tests
- [x] Backend health endpoint test works
- [ ] Chat interface elements (need to verify selectors)
- [ ] Settings page (need auth fixture)

### Admin Tests
- [x] New admin-dashboard.spec.ts works
- [ ] Old admin routes need consolidation review
- [ ] Missing AdminDashboardPage fixture

### Chat Tests
- [x] New conversation-ui.spec.ts works
- [ ] Chat page selectors need verification

---

## Sprint 46 Feature Coverage

| Feature | Test File | Status | Coverage |
|---------|-----------|--------|----------|
| 46.1 ConversationView | conversation-ui.spec.ts | ✓ | 15 tests |
| 46.2 ReasoningPanel | conversation-ui.spec.ts | ✓ | 13 tests |
| 46.5 DomainAutoDiscovery | domain-auto-discovery.spec.ts | ✓ | 7+ tests |
| 46.8 AdminDashboard | admin-dashboard.spec.ts | ✓ | 15 tests |
| Domain Discovery API | domain-discovery-api.spec.ts | ✓ | 8+ tests |

---

## Next Steps

1. Run full test suite with current findings
2. Fix Priority 1 issues (3 failures)
3. Document results in PR
4. Archive old admin tests if routes consolidated
5. Add AdminDashboardPage fixture
6. Update naming convention for domain training tests
7. Create consolidated test summary

---

## Test Audit Checklist

- [ ] Fix settingsPage fixture (add auth)
- [ ] Verify chat page selectors
- [ ] Create AdminDashboardPage fixture
- [ ] Review admin route consolidation
- [ ] Verify SessionSidebar location
- [ ] Test domain training tests
- [ ] Run full test suite
- [ ] Document all changes
- [ ] Create PR with fixes

---

## Contact & Questions

For questions about this audit or specific tests, refer to:
- Test fixtures: `/e2e/fixtures/index.ts`
- Page objects: `/e2e/pom/`
- Sprint 46 docs: `/e2e/admin/SPRINT_46_*.md`

---

**Last Updated:** 2025-12-16
**Auditor:** Testing Agent
**Status:** Draft - Awaiting validation runs
