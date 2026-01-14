# Sprint 72: E2E Test Gap Analysis

**Created:** 2026-01-03
**Related:** SPRINT_72_PLAN.md (Feature 72.7 - E2E Test Completion)

---

## Executive Summary

**Current E2E Test Status:**
- **Total Tests:** 157
- **Passing:** 97
- **Skipped:** 60
- **Pass Rate:** 62% (97/157)

**Sprint 72 Target:**
- **Total Tests:** ~232 (+ 75 new tests)
- **Passing:** 232
- **Skipped:** 0
- **Pass Rate:** 100%

**Gap:** 75 missing/skipped E2E tests for Sprint 72 features

---

## Current E2E Test Coverage (Sprint 71)

### ✅ Well-Covered Pages (100% coverage)

| Page/Feature | Tests | Status | Coverage |
|--------------|-------|--------|----------|
| **Auth/Login** | 9 | 9 passing | 100% ✅ |
| **Chat (Share + Search)** | 26 | 26 passing | 100% ✅ |
| **Graph Analytics (Core)** | 33 | 33 passing | 55% ✅ (skipped tests for long-running ops) |
| **Indexing/Pipeline** | 23 | 23 passing | 74% ✅ (skipped tests for slow operations) |

---

### ⚠️ Partially Covered Pages (Need Work)

| Page/Feature | Total Tests | Passing | Skipped | Coverage | Issue |
|--------------|-------------|---------|---------|----------|-------|
| **Ingestion Jobs** | 12 | 5 | 7 | 42% | Require active ingestion jobs |
| **Graph Communities** | 60 | 33 | 27 | 55% | Long-running community detection |

---

### ❌ Missing E2E Tests (Sprint 72 Features)

#### 1. **MCP Tool Management** (Feature 72.2) - **15 tests missing**

**Missing File:** `frontend/e2e/tests/admin/mcp-tools.spec.ts`

**Required Tests:**
1. ✗ Display `/admin/tools` page when navigating from admin
2. ✗ Show MCP server list with status badges (connected/disconnected/error)
3. ✗ Connect to MCP server via button
4. ✗ Disconnect from MCP server via button
5. ✗ Display error message on connection failure
6. ✗ Show available tools per server
7. ✗ Open tool execution test panel
8. ✗ Execute tool with parameters
9. ✗ Display tool execution result (success)
10. ✗ Display tool execution error (failure)
11. ✗ Real-time health monitor updates status
12. ✗ Filter tools by server
13. ✗ Search tools by name
14. ✗ Export tool execution logs
15. ✗ Auto-refresh server list every 30 seconds

---

#### 2. **Domain Training UI** (Feature 72.3) - **18 tests need un-skipping**

**Existing File:** `frontend/e2e/tests/admin/domain-training-new-features.spec.ts`

**Currently Skipped (need Backend integration):**
- Data Augmentation Dialog (6 tests skipped)
- Batch Document Upload Dialog (6 tests skipped)
- Domain Details Dialog (6 tests skipped)

**Action Required:** Wire up endpoints → un-skip tests

---

#### 3. **Memory Management** (Feature 72.4) - **10 tests missing**

**Missing File:** `frontend/e2e/tests/admin/memory-management.spec.ts`

**Required Tests:**
1. ✗ Display `/admin/memory` page when navigating from admin
2. ✗ Show memory stats for all layers (Redis, Qdrant, Graphiti)
3. ✗ Display Redis stats (keys, memory_mb, hit_rate)
4. ✗ Display Qdrant stats (documents, size_mb, avg_search_latency_ms)
5. ✗ Display Graphiti stats (episodes, entities, avg_search_latency_ms)
6. ✗ Search memory by user ID
7. ✗ Search memory by session ID
8. ✗ Display search results with relevance scores
9. ✗ Trigger manual memory consolidation
10. ✗ Export memory as JSON download

---

#### 4. **E2E Test Infrastructure** (Feature 72.6) - **10 tests missing**

**Missing File:** `frontend/e2e/tests/infrastructure/performance-regression.spec.ts`

**Required Performance Tests:**
1. ✗ Query latency < 500ms (simple query)
2. ✗ Query latency < 1000ms (complex multi-hop query)
3. ✗ Document upload < 3 minutes (medium PDF)
4. ✗ Section extraction < 50s (146 texts)
5. ✗ BM25 cache hit rate > 80%
6. ✗ Redis memory usage < 2GB
7. ✗ Qdrant search latency < 100ms
8. ✗ Neo4j graph query < 500ms
9. ✗ Embedding generation < 200ms (batch of 10)
10. ✗ Reranking < 50ms (top 10 results)

---

## Missing Tests Summary

| Feature | File | Tests Missing | Priority |
|---------|------|---------------|----------|
| MCP Tool Management (72.1) | `mcp-tools.spec.ts` | 15 | 🔴 CRITICAL |
| Domain Training (72.2) | `domain-training-new-features.spec.ts` | 18 (skipped) | 🔴 CRITICAL |
| Memory Management (72.3) | `memory-management.spec.ts` | 10 | 🔴 CRITICAL |
| Performance Regression (72.6) | `performance-regression.spec.ts` | 10 | 🟡 MEDIUM |
| **TOTAL** | | **53 tests** | |

---

## Additional Gaps (Pre-Existing)

### Skipped Tests from Sprint 71 (Need Active Jobs)

#### **Ingestion Jobs** (7 skipped)
- Overall progress bar for running job
- Current processing step display
- Status badges (running, completed, failed)
- Expand job for parallel documents
- Up to 3 concurrent documents display
- Cancel job functionality
- Real-time SSE updates

**Action:** Create test fixtures with mock ingestion jobs OR run tests against live ingestion

---

#### **Graph Communities** (27 skipped)
- Section communities dialog - fetch and display communities (requires Neo4j data)
- Community details when expanded
- Community comparison results
- Overlap matrix display

**Action:** Seed Neo4j with test data OR mock community detection API

---

## Implementation Plan (Feature 72.6)

### Phase 1: Critical Tests (Days 1-3) - 43 tests
1. **MCP Tool Management** (15 tests) - 1 day
2. **Domain Training** (18 tests - un-skip) - 1 day
3. **Memory Management** (10 tests) - 1 day

### Phase 2: Performance Tests (Days 4-5) - 10 tests
4. **Performance Regression** (10 tests) - 2 days

### Phase 3: Skipped Test Resolution (Days 6-7) - 34 tests
5. **Ingestion Jobs** (7 tests with mock jobs) - 1 day
6. **Graph Communities** (27 tests with seeded data) - 1 day

---

## Success Criteria (Sprint 72 End)

- [ ] **Total E2E Tests:** 157 → 232 (+75 tests)
- [ ] **Pass Rate:** 62% → 100% (+38 percentage points)
- [ ] **Skipped Tests:** 60 → 0 (all resolved)
- [ ] **Performance Tests:** 10 automated regression tests
- [ ] **Frontend Coverage:** All Sprint 72 features have E2E tests (MCP, Domain, Memory)

---

## Test Automation Strategy

### Fixtures & Mock Data
```typescript
// frontend/e2e/fixtures/mcp-servers.ts
export const mockMCPServers = [
  {
    name: "filesystem",
    status: "connected",
    tools: ["read_file", "write_file", "list_directory"],
    health: "healthy"
  },
  {
    name: "web-search",
    status: "disconnected",
    tools: ["tavily_search", "google_search"],
    health: "unknown"
  }
];

// frontend/e2e/fixtures/memory-stats.ts
export const mockMemoryStats = {
  redis: { keys: 1234, memory_mb: 50, hit_rate: 0.85 },
  qdrant: { documents: 5000, size_mb: 250, avg_search_latency_ms: 45 },
  graphiti: { episodes: 500, entities: 2000, avg_search_latency_ms: 95 }
};
```

### Performance Test Infrastructure
```typescript
// frontend/e2e/tests/infrastructure/performance-regression.spec.ts
test('Query latency < 500ms (simple query)', async ({ page }) => {
  const startTime = Date.now();
  await page.goto('/');
  await page.getByTestId('chat-input').fill('What is machine learning?');
  await page.getByTestId('send-button').click();

  // Wait for response
  await page.getByTestId('chat-response').waitFor();
  const latency = Date.now() - startTime;

  expect(latency).toBeLessThan(500);
});
```

---

## References

- **Sprint 72 Plan:** [SPRINT_72_PLAN.md](SPRINT_72_PLAN.md)
- **Current E2E Tests:** [USER_JOURNEYS_AND_TEST_PLAN.md](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md)
- **Test Fixtures:** `frontend/e2e/fixtures/`
- **Playwright Config:** `frontend/playwright.config.ts`

---

**Last Updated:** 2026-01-03
**Status:** 📋 **PLANNED** - Sprint 72 Feature 72.7
**Owner:** Klaus Pommer + Claude Code (testing-agent, frontend-agent)
