# Sprint 68 Feature 68.1: E2E Test Analysis

**Date:** 2026-01-01
**Status:** In Progress
**Story Points:** 13 SP

## Executive Summary

Current E2E test suite status:
- **Total Tests:** 606 (verified from test execution)
- **Estimated Passed:** ~337 (from Sprint 67 report)
- **Estimated Failed:** ~269 (from Sprint 67 report)
- **Pass Rate:** ~56%

**Critical Observation:** The test count has grown from 594 (Sprint 67) to 606 (current), indicating new tests were added without verifying pass rate.

## Test Architecture Analysis

### Fixtures & Page Object Models

**Location:** `frontend/e2e/fixtures/index.ts`

**Architecture:**
- ✅ Uses Playwright fixtures for dependency injection
- ✅ Page Object Model pattern for maintainability
- ✅ Authentication mocking for protected routes
- ✅ Reusable test utilities

**Fixtures Available:**
1. `chatPage` - Chat interface (with auth)
2. `historyPage` - Conversation history
3. `settingsPage` - User settings
4. `adminIndexingPage` - Document ingestion
5. `adminGraphPage` - Graph visualization
6. `adminDashboardPage` - Admin dashboard
7. `costDashboardPage` - Cost tracking
8. `adminLLMConfigPage` - LLM configuration
9. `adminDomainTrainingPage` - Domain training
10. `authenticatedPage` - Generic auth page
11. `authChatPage` - Authenticated chat

### Test Configuration

**Location:** `frontend/playwright.config.ts`

**Settings:**
- Timeout: 30s (for LLM responses)
- Expect Timeout: 10s
- Workers: 1 (sequential execution to avoid LLM rate limits)
- Retries: 0 (local), 2 (CI)
- Reporters: HTML, JSON, JUnit

**Critical Issue:** No automatic backend/frontend startup configured. Tests require manual service startup in separate terminals.

## Test Failure Pattern Analysis

### Pattern 1: Follow-up Questions (Priority 1)

**File:** `frontend/e2e/followup/followup.spec.ts`

**Issue:** Follow-up questions not persisting or loading correctly

**Root Cause Analysis:**

1. **Backend Endpoint:** `GET /chat/sessions/{session_id}/followup-questions`
   - Location: `src/api/v1/chat.py:1749-1959`
   - Logic:
     ```python
     # Priority 1: Check async generation (background task)
     async_questions = await generate_followup_questions_async(session_id)

     # Priority 2: Check cache (5min TTL)
     cached_questions = await redis_memory.retrieve(key=cache_key, namespace="cache")

     # Priority 3: Check stored questions in conversation
     stored_questions = conversation.get("follow_up_questions", [])

     # Priority 4: Generate synchronously from last Q&A
     questions = await generate_followup_questions(query, answer, sources)
     ```

2. **Conversation Storage:** `save_conversation_turn()` function
   - Location: `src/api/v1/chat.py:61-192`
   - Stores: `follow_up_questions`, `title`, `messages`, `sources`
   - TTL: 7 days (604800 seconds)
   - Namespace: `"conversation"`

**Test Cases Affected:**
- ✅ `should generate 3-5 follow-up questions` (9 tests)
- ❌ `should persist follow-ups across page reloads` (flaky - depends on conversation persistence)
- ❌ `should handle multiple consecutive follow-ups` (depends on Redis state)

**Hypothesis:** Tests are passing locally but failing in CI due to:
- Redis connection issues
- Async background task not completing before test polls
- Cache eviction before verification

### Pattern 2: Conversation History (Priority 2)

**File:** `frontend/e2e/history/history.spec.ts`

**Issue:** History loading timeout (>5s) and session list retrieval

**Root Cause Analysis:**

1. **Backend Endpoint:** `GET /chat/sessions`
   - Location: `src/api/v1/chat.py:806-901`
   - Logic:
     ```python
     # Scan ALL conversation keys in Redis
     cursor = 0
     while True:
         cursor, keys = await redis_client.scan(cursor=cursor, match="conversation:*", count=100)
         conversation_keys.extend(keys)
         if cursor == 0:
             break

     # Retrieve each conversation (N+1 query problem!)
     for key in conversation_keys:
         conv_data = await redis_memory.retrieve(key=session_id, namespace="conversation")
     ```

2. **Performance Issue:** N+1 query problem
   - If 100 conversations exist → 1 SCAN + 100 GET operations
   - Each GET retrieves full conversation data (messages, sources, metadata)
   - No pagination implemented until Sprint 65 (limit/offset params added)

**Test Cases Affected:**
- ❌ `should list conversations in chronological order` (timeout with >50 conversations)
- ❌ `should open conversation on click and restore messages` (depends on history load)
- ❌ `should search conversations by title and content` (requires full list first)

**Hypothesis:** Tests are timing out because:
- Test environment accumulates conversations across runs
- No cleanup between test runs
- Redis SCAN is slow with 100+ keys

**Sprint 65 Fix Applied:**
```python
# Added pagination
limit = min(max(1, limit), 100)  # Clamp between 1 and 100
offset = max(0, offset)
paginated_sessions = sessions[offset : offset + limit]
```

**Issue:** Frontend tests may not be using pagination parameters!

### Pattern 3: OMNITRACKER Retrieval (Priority 3)

**File:** Multiple test files referencing OMNITRACKER queries

**Issue:** Graph filters not applied correctly, retrieval returns no results

**Root Cause Analysis:**

1. **Sprint 65 Update:** All test queries changed to OMNITRACKER domain
   - Rationale: "ensure knowledge base has relevant documents for retrieval"
   - Files updated:
     - `followup/followup.spec.ts`
     - `history/history.spec.ts`
     - Other test files

2. **Knowledge Base Requirement:**
   - Tests assume OMNITRACKER documents are indexed in Qdrant
   - Tests assume OMNITRACKER entities exist in Neo4j graph
   - No test setup/teardown to ensure data exists

3. **Graph Filter Logic:**
   - Agent: `src/agents/graph_query_agent.py`
   - Applies filters from state: `state.get("graph_filters")`
   - If filters too restrictive → empty results

**Test Cases Affected:**
- ❌ All tests using OMNITRACKER queries (if documents not indexed)
- ❌ Graph-specific tests expecting entity/relation results

**Hypothesis:** Tests are failing because:
- OMNITRACKER documents not in test database
- Graph entities not extracted
- No test data seeding before test execution

### Pattern 4: Domain Training Timeouts (Priority 4)

**File:** `frontend/e2e/admin/test_domain_training_*.spec.ts`

**Issue:** Training exceeds 30s timeout

**Root Cause Analysis:**

1. **Test Timeout:** 30s (from `playwright.config.ts`)
2. **Actual Training Time:** Likely 60-120s for real LLM fine-tuning
3. **Backend Process:** Domain training is synchronous (blocks request)

**Solution Options:**
1. Increase test timeout to 120s for domain training tests
2. Make domain training async (background job)
3. Mock LLM training endpoint in tests

**Recommended:** Option 1 (quick fix) + Option 2 (proper solution in Sprint 69)

### Pattern 5: Missing UI Elements (Observed in Test Run)

**File:** `frontend/e2e/admin/domain-auto-discovery.spec.ts`

**Error:**
```
Error: expect(locator).toBeVisible() failed
Locator: locator('[data-testid="domain-discovery-upload-area"]')
Expected: visible
Timeout: 10000ms
Error: element(s) not found
```

**Root Cause:** Frontend component removed or test-id changed without updating test

**Test Cases Affected:**
- ❌ `TC-46.5.1: should render drag-drop upload area on page load`

## Test Infrastructure Issues

### Issue 1: No Automatic Service Startup

**Current Setup:** Manual startup required
```bash
# Terminal 1: Backend
cd .. && poetry run python -m src.api.main

# Terminal 2: Frontend
npm run dev

# Terminal 3: Tests
npm run test:e2e
```

**Problem:**
- Developers forget to start services → all tests fail
- Service crashes during test run → flaky tests
- No health check verification before tests start

**Solution:** Enable `webServer` config in `playwright.config.ts`

### Issue 2: No Test Data Isolation

**Current Setup:**
- Tests share Redis database
- Tests share Qdrant collections
- Tests share Neo4j graph
- Conversations accumulate across test runs

**Problem:**
- Flaky tests (depend on leftover data)
- History tests timeout with accumulated conversations
- Graph tests return unexpected entities

**Solution:**
- Use separate test namespaces
- Implement test cleanup hooks
- Consider test containers

### Issue 3: No Parallel Execution

**Current Setup:** `workers: 1` (sequential)

**Rationale:** Avoid LLM rate limits

**Problem:**
- 606 tests × ~3s avg = ~30 minutes total runtime
- Slow feedback loop

**Solution:**
- Group tests by category (unit, integration, e2e)
- Run non-LLM tests in parallel
- Use `test.describe.configure({ mode: 'parallel' })` selectively

### Issue 4: No Retry Logic for Flaky Tests

**Current Setup:** `retries: 0` (local)

**Problem:**
- Network-dependent tests fail sporadically
- LLM timeout variations cause failures
- Redis connection blips fail tests

**Solution:** Add selective retry logic
```typescript
test.describe('Flaky Tests', () => {
  test.describe.configure({ retries: 2 });

  test('should handle LLM timeout', async ({ chatPage }) => {
    // Test with retry on timeout
  });
});
```

## Recommended Fix Roadmap

### Phase 1: Quick Wins (2 hours)

1. **Fix missing UI elements** (1 hour)
   - Audit all `data-testid` attributes in components
   - Update tests to match current UI

2. **Increase domain training timeout** (15 min)
   - Update timeout for domain training tests to 120s
   - Add comment explaining why

3. **Add test cleanup hooks** (45 min)
   - Clear Redis test namespaces after each test
   - Add `afterEach` hook to clean up

### Phase 2: Backend Fixes (4 hours)

1. **Fix conversation history pagination** (1 hour)
   - Ensure frontend uses `limit=50` parameter
   - Add loading indicator for pagination

2. **Fix follow-up questions persistence** (2 hours)
   - Debug async background task completion
   - Add logging to track generation status
   - Verify Redis storage/retrieval

3. **Seed OMNITRACKER test data** (1 hour)
   - Create test fixture with OMNITRACKER documents
   - Index documents before test run
   - Extract graph entities

### Phase 3: Infrastructure (3 hours)

1. **Enable automatic service startup** (1 hour)
   - Configure `webServer` in playwright.config.ts
   - Add health check verification

2. **Add test data isolation** (1 hour)
   - Use namespace: `test:{test_id}`
   - Auto-cleanup on test completion

3. **Implement selective parallelization** (1 hour)
   - Group tests by type
   - Parallelize unit tests
   - Keep LLM tests sequential

### Phase 4: Validation (2 hours)

1. **Run full test suite** (1 hour)
   - Verify 100% pass rate
   - Document any remaining failures

2. **Create canary suite** (1 hour)
   - Select 20-50 critical tests
   - Run on every PR

## Success Metrics

- **Pass Rate:** 100% (606/606 tests)
- **Execution Time:** <15 minutes (with parallelization)
- **Flaky Test Rate:** <2% (max 12 flaky tests)
- **CI Integration:** Canary suite in GitHub Actions

## Next Steps

1. ✅ Complete this analysis document
2. ⏳ Fix Phase 1: Quick Wins
3. ⏳ Fix Phase 2: Backend Fixes
4. ⏳ Fix Phase 3: Infrastructure
5. ⏳ Fix Phase 4: Validation
6. ⏳ Document in SPRINT_68_FEATURE_68.1_SUMMARY.md

---

**Testing Agent:** This analysis provides a comprehensive roadmap to achieve 100% E2E test pass rate. The key insight is that the majority of failures are due to infrastructure issues (test data isolation, service startup) rather than actual code bugs.
