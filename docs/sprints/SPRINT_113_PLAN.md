# Sprint 113 Plan: E2E Test Stabilization

**Sprint Duration:** 2 weeks
**Total Tests:** 1099
**Pass Rate (Current):** 49% (538 passed, 544 failed, 17 skipped)
**Target Pass Rate:** 85%+ (95%+ for critical paths)

---

## Executive Summary

E2E test run on 2026-01-19 revealed **544 failing tests** out of 1099. Analysis shows:

| Failure Category | Count | % of Failures | Root Cause |
|------------------|-------|---------------|------------|
| LLM Response Timeout | 328 | 60% | Ollama 11-15min response vs 11-30s test timeout |
| UI Element Not Found | 112 | 21% | Missing data-testids, late rendering |
| API Errors | 62 | 11% | Unexpected error responses |
| Other | 42 | 8% | Various issues |

---

## Key Finding: LLM Response Time Crisis

**Critical Discovery:** Ollama `/api/chat` requests take **11-15 MINUTES** instead of expected <60s.

```
[GIN] 200 | 11m6s  | POST "/api/chat"
[GIN] 200 | 11m31s | POST "/api/chat"
[GIN] 200 | 12m17s | POST "/api/chat"
[GIN] 200 | 14m48s | POST "/api/chat"
```

**Root Cause Analysis:**
- Nemotron 3 Nano 30B model is slow on DGX Spark
- Prompt cache helps (cache hits: 6ms) but cold requests are extremely slow
- Tests timeout at 11-30s, LLM responds after 660-890s

---

## Sprint 113 Features

### Feature 113.0: Graph Search Early-Exit Optimization (COMPLETED - 5 SP)

**Status:** ✅ COMPLETED (2026-01-19)
**ADR:** [ADR-056](../adr/ADR-056-graph-search-early-exit.md)

**Problem:** Graph search took 13.4s even for empty namespaces due to 2x LLM calls.

**Solution:** Early-exit check before expensive LLM calls.

**Results:**
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Hybrid Search | 13.77s | 1.81s | **-87%** |
| Graph Search | 13,376ms | 99ms | **-99.3%** |

**Implementation:**
- Added `_namespace_has_entities()` method to `SmartEntityExpander`
- Skips Stage 1 (LLM Entity Extraction) and Stage 3 (LLM Synonym Generation) when namespace empty
- Created fulltext index on `entity_name` + `description` for future optimization

**Files Changed:**
- `src/components/graph_rag/entity_expansion.py`

---

### Feature 113.1: LLM Performance Optimization (Critical - 20 SP)

**Goal:** Reduce LLM response time from 11-15min to <60s

**Tasks:**
1. [ ] Enable streaming responses for faster TTFB
2. [ ] Implement aggressive prompt caching
3. [ ] Add LLM response time monitoring
4. [ ] Consider model switch: Nemotron 3 → qwen3:8b for tests
5. [ ] Add test-specific mock LLM mode for non-integration tests

**Affected Tests:** 328 (60% of all failures)

---

### Feature 113.2: Chat UI Test Fixes (15 SP)

**Files:** `conversation-ui.spec.ts` (26 failures)

**Issues:**
- Tests wait for LLM response that never arrives within timeout
- Message send/receive cycle broken due to timeout
- Reasoning panel tests fail waiting for response metadata

**Fixes:**
1. [ ] Add mock LLM responses for UI-only tests
2. [ ] Increase timeout for integration tests to 5min
3. [ ] Add `data-testid` for all chat components
4. [ ] Separate UI tests from integration tests

---

### Feature 113.3: Domain Training Test Fixes (12 SP)

**Files:**
- `test_domain_training_flow.spec.ts` (26 failures)
- `test_domain_training_api.spec.ts` (21 failures)
- `test_domain_upload_integration.spec.ts` (12 failures)

**Issues:**
- Wizard navigation timeouts (30s)
- API endpoint responses differ from expected schema
- File upload handling inconsistent

**Fixes:**
1. [ ] Fix new domain wizard button detection
2. [ ] Update API response schema expectations
3. [ ] Add proper file upload mock handling
4. [ ] Fix domain name validation regex display

---

### Feature 113.4: Graph Visualization Test Fixes (15 SP)

**Files:**
- `graph-visualization.spec.ts` (31 failures combined)
- `edge-filters.spec.ts` (10 failures)
- `version-compare.spec.ts` (10 failures)
- `time-travel.spec.ts` (9 failures)
- `entity-changelog.spec.ts` (9 failures)

**Issues:**
- Graph controls (zoom, pan, filter) not responding
- Version comparison modal issues
- Time travel slider interactions failing
- Entity changelog panel not loading data

**Fixes:**
1. [ ] Add proper wait conditions for graph rendering
2. [ ] Fix D3.js/vis.js event handling in tests
3. [ ] Add mock data for graph operations
4. [ ] Update element selectors for filters

---

### Feature 113.5: Pipeline & Admin UI Fixes (10 SP)

**Files:**
- `pipeline-progress.spec.ts` (22 failures)
- `memory-management.spec.ts` (14 failures)
- `vlm-integration.spec.ts` (14 failures)

**Issues:**
- Pipeline progress indicators not updating
- Memory stats not loading
- VLM image analysis timeouts

**Fixes:**
1. [ ] Add SSE mock for pipeline progress
2. [ ] Fix memory stats API call timing
3. [ ] Add VLM mock responses for image tests

---

### Feature 113.6: Search & Intent Test Fixes (8 SP)

**Files:**
- `search.spec.ts` (15 failures)
- `intent.spec.ts` (15 failures)
- `namespace-isolation.spec.ts` (11 failures)

**Issues:**
- Search results not appearing
- Intent classification timeout
- Namespace filtering not working

**Fixes:**
1. [ ] Add mock search results
2. [ ] Speed up intent classifier (use cached embeddings)
3. [ ] Fix namespace dropdown selection

---

### Feature 113.7: Error Handling & Structured Output (10 SP)

**Files:**
- `error-handling.spec.ts` (21 failures)
- `structured-output.spec.ts` (20 failures)
- `tool-output-viz.spec.ts` (16 failures)

**Issues:**
- Error messages not displayed correctly
- Structured output parsing failures
- Tool output visualization component missing

**Fixes:**
1. [ ] Add error boundary to all components
2. [ ] Fix JSON parsing in structured output
3. [ ] Add `data-testid` to tool output components

---

## Test Infrastructure Improvements

### 113.8: Mock Infrastructure (8 SP)

**Tasks:**
1. [ ] Create `MockLLMService` for test environment
2. [ ] Add `PLAYWRIGHT_MOCK_LLM=true` env variable
3. [ ] Implement mock responses for common queries
4. [ ] Add response latency simulation (<500ms)

### 113.9: Test Timeout Configuration (5 SP)

**Tasks:**
1. [ ] Create test timeout tiers:
   - UI-only: 10s
   - API integration: 30s
   - LLM integration: 5min
2. [ ] Add `@slow` tag for LLM-dependent tests
3. [ ] Configure parallel test execution for fast tests

### 113.10: CI/CD Pipeline Updates (5 SP)

**Tasks:**
1. [ ] Separate test suites: `fast`, `integration`, `e2e-full`
2. [ ] Add pre-commit hook for fast tests
3. [ ] Nightly run for full E2E suite
4. [ ] Add test failure alerts to Grafana

---

## Failure Breakdown by Test File

| File | Failures | Category | Priority |
|------|----------|----------|----------|
| conversation-ui.spec.ts | 26 | LLM Timeout | P0 |
| test_domain_training_flow.spec.ts | 26 | UI/Timeout | P1 |
| pipeline-progress.spec.ts | 22 | SSE/UI | P1 |
| error-handling.spec.ts | 21 | Error UI | P2 |
| test_domain_training_api.spec.ts | 21 | API | P1 |
| structured-output.spec.ts | 20 | UI | P2 |
| graph-visualization.spec.ts | 19+12 | Graph UI | P2 |
| tool-output-viz.spec.ts | 16 | UI | P2 |
| search.spec.ts | 15 | Search | P1 |
| intent.spec.ts | 15 | Intent | P1 |
| multi-turn-rag.spec.ts | 15 | LLM Timeout | P0 |
| memory-management.spec.ts | 14 | Admin UI | P2 |
| vlm-integration.spec.ts | 14 | VLM | P2 |
| research-mode.spec.ts | 12 | LLM Timeout | P0 |
| single-document-test.spec.ts | 12 | Ingestion | P1 |
| group19-llm-config.spec.ts | 12 | Config | P2 |

---

## Story Point Summary

| Feature | Story Points | Priority | Status |
|---------|--------------|----------|--------|
| 113.0 Graph Early-Exit | 5 | P0 | ✅ COMPLETED |
| 113.1 LLM Performance | 20 | P0 | In Progress |
| 113.2 Chat UI Tests | 15 | P0 |
| 113.3 Domain Training | 12 | P1 |
| 113.4 Graph Visualization | 15 | P2 |
| 113.5 Pipeline/Admin UI | 10 | P1 |
| 113.6 Search/Intent | 8 | P1 |
| 113.7 Error/Structured | 10 | P2 |
| 113.8 Mock Infrastructure | 8 | P0 |
| 113.9 Timeout Config | 5 | P1 |
| 113.10 CI/CD Updates | 5 | P2 |
| **Total** | **108 SP** | |

---

## Success Criteria

1. **Pass Rate:** ≥85% (current: 49%)
2. **Critical Path Pass Rate:** ≥95% (Chat, Search, Admin)
3. **Test Duration:** <30min for fast suite, <2h for full suite
4. **LLM Response Time:** <60s for test queries (with mock: <500ms)

---

## Dependencies

- Feature 113.1 (LLM Performance) blocks Features 113.2, 113.3, 113.4
- Feature 113.8 (Mock Infrastructure) enables faster iteration

---

## Risks

| Risk | Mitigation |
|------|------------|
| LLM cannot be optimized to <60s | Use mock LLM for all non-integration tests |
| Too many test changes destabilize suite | Incremental fixes with regression testing |
| GPU memory constraints | Implement LLM unloading between test runs |

---

## Test Run Results (2026-01-19 After Graph Early-Exit Fix)

### Summary

| Test Suite | Passed | Failed | Total | Pass Rate |
|------------|--------|--------|-------|-----------|
| Smoke Tests | 11 | 1 | 12 | **91.7%** |
| ReasoningPanel (TC-46.2.x) | 10 | 2 | 12 | **83.3%** |
| ConversationUI (TC-46.1.x) | 11 | 2 | 13 | **84.6%** |
| Chat Interface | 2 | 0 | 2 | **100%** |

### Performance After Fix

| Metric | Before Fix | After Fix | Improvement |
|--------|------------|-----------|-------------|
| Graph Search (empty NS) | 13,376ms | 6.8ms | **-99.9%** |
| Hybrid API (empty NS) | 13.77s | 16ms | **-99.9%** |
| TC-46.2.11 | ❌ Timeout | ✅ 25s | Fixed! |
| TC-46.2.12 | ❌ Timeout | ✅ 20.9s | Fixed! |

### Identified Bugs - ALL FIXED ✅

| Bug ID | Test | Issue | Root Cause | Status |
|--------|------|-------|------------|--------|
| ✅ BUG-113.1 | TC-46.2.2 | `aria-expanded` test fails | Test didn't handle `defaultExpanded=true` | **FIXED** |
| ✅ BUG-113.2 | TC-46.2.3 | Same as above | Same test issue | **FIXED** |
| ✅ BUG-113.3 | TC-46.1.5 | Input area class check fails | Test expected `flex-shrink-0`, component uses `absolute` | **FIXED** |
| ✅ BUG-113.4 | TC-46.1.9 | Message count too low | Race condition - test didn't wait for render | **FIXED** |
| ⏭️ BUG-113.5 | Smoke | URL check expects localhost:5179 | Test config issue (not a bug) | Deferred |

### Bug Details & Fixes

#### BUG-113.1 & BUG-113.2: ReasoningPanel aria-expanded Toggle - FIXED ✅

**Location:** `e2e/chat/conversation-ui.spec.ts` (lines 345-384, 386-429, 860-891)

**Root Cause:** Tests assumed `defaultExpanded=false` but component defaults to `defaultExpanded=true` (Sprint 51 change).

**Fix Applied:**
```typescript
// Sprint 113: If already expanded (defaultExpanded=true), collapse first
if (initialState === 'true') {
  await reasoningToggle.click();
  await chatPage.page.waitForTimeout(300);
}
```

#### BUG-113.3: Input Area Fixed Position - FIXED ✅

**Location:** `e2e/chat/conversation-ui.spec.ts` (lines 98-124)

**Root Cause:** CSS layout changed from `flex-shrink-0` to `absolute bottom-0` in Sprint 52.

**Fix Applied:**
```typescript
// Sprint 113: Updated for absolute positioning (Sprint 52 change)
expect(inputAreaClasses).toContain('absolute');
expect(inputAreaClasses).toContain('bottom-0');
```

#### BUG-113.4: Multiple Message Layout - FIXED ✅

**Location:** `e2e/chat/conversation-ui.spec.ts` (lines 201-242)

**Root Cause:** Test checked message count before all messages were rendered.

**Fix Applied:**
```typescript
// Sprint 113: Wait for all 4 messages to be rendered (with timeout)
await expect(messages).toHaveCount(4, { timeout: 30000 });
```

---

*Created: 2026-01-19*
*Sprint 112 → Sprint 113 Handoff*
*Updated: 2026-01-19 (Test Results after Feature 113.0)*
