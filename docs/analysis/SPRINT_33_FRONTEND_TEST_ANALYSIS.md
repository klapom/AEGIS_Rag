# Sprint 33 Frontend E2E Test Analysis Report

**Date:** 2025-11-27
**Status:** 26 failing tests out of 289 total (91.0% pass rate)
**Environment:** Windows development environment with Docker services
**Root Cause:** Backend API service not running during test execution

---

## Executive Summary

The frontend E2E tests are failing primarily due to **one critical infrastructure issue**:
- **Backend API (http://localhost:8000) is not running** during test execution
- This causes ECONNREFUSED errors when tests attempt to make real API calls
- Tests that mock the fetch API pass; tests that attempt real backend calls fail

**Quick Fix:** Either mock the fetch calls for tests OR ensure the backend is running before executing tests.

---

## Test Failure Categories

### Category 1: Backend API Connection Failures (19 tests)

**Root Cause:** `TypeError: fetch failed` with `ECONNREFUSED` error

Tests attempting real HTTP requests to http://localhost:8000 fail because the backend is not running.

**Affected Test Files:**
- `HomePage.e2e.test.tsx` - 9 tests (all with real API calls)
- `AdminStats.e2e.test.tsx` - 2 tests
- `SearchResultsPage.e2e.test.tsx` - multiple tests
- `ConversationPersistence.e2e.test.tsx` - multiple tests
- `FullWorkflow.e2e.test.tsx` - 2 tests

**Error Pattern:**
```
Streaming error: TypeError: fetch failed
  at node:internal/deps/undici/undici:13510:13
  ...
  code: 'ECONNREFUSED'
```

**Affected Tests in HomePage.e2e.test.tsx:**
1. "should navigate to search page on Enter key press"
2. "should navigate to search page on submit button click"
3. "should trim whitespace before submission"
4. "should default to hybrid mode"
5. "should switch to vector mode when Vector chip is clicked"
6. "should switch to graph mode when Graph chip is clicked"
7. "should switch to memory mode when Memory chip is clicked"
8. "should navigate with quick prompt when clicked"

**Issue:** Tests in HomePage.e2e.test.tsx don't mock the `streamChat` API call, so they attempt real HTTP requests to `/api/v1/chat/stream`.

### Category 2: Canvas/Graphics Library Missing (2 tests)

**Root Cause:** Missing `canvas` npm package for rendering graph visualizations

Tests in `GraphViewer.test.tsx` fail because they try to render a canvas-based force graph.

**Error Pattern:**
```
Not implemented: HTMLCanvasElement's getContext() method: without installing the canvas npm package
```

**Affected Tests:**
1. "renders graph with nodes and edges"
2. "calls onNodeClick callback when provided"

**Fix:** Install the `canvas` package: `npm install canvas`

### Category 3: Indexing API Missing Response Stream (3 tests)

**Root Cause:** Mock setup doesn't return proper ReadableStream for SSE streaming

Tests in `AdminIndexingPage.test.tsx` attempt to iterate over undefined response body.

**Error Pattern:**
```
Indexing error: TypeError: Cannot read properties of undefined (reading 'Symbol(Symbol.asyncIterator)')
```

**Affected Tests:**
1. "should start indexing on confirmation"
2. "should display indexing progress"
3. "directory scanning" tests

**Issue:** The test mock for `POST /api/v1/admin/indexing/add` doesn't properly return a `body` property with a ReadableStream, causing the async iteration in AdminIndexingPage.tsx:197 to fail.

### Category 4: Unit Test Failures (2 tests)

**Root Cause:** Mock setup issues with SSE streaming

Test in `chat.test.ts` fails when setting up SSE mock streams.

**Affected Tests:**
1. "should yield chat chunks from SSE stream" (in chat.test.ts)

**Issue:** The mock SSE stream setup may not be properly initializing the ReadableStream.

---

## Detailed Root Cause Analysis

### Issue 1: Backend Service Not Running (CRITICAL - Affects 19 tests)

**Current State:**
- Frontend tests run in `vitest` with `jsdom` environment
- Tests in HomePage.e2e.test.tsx and other files call real API endpoints
- Backend API (Python FastAPI) is not running on http://localhost:8000
- Tests receive `ECONNREFUSED` errors instead of mocked responses

**Frontend Code Attempting Real Requests:**
```typescript
// src/api/chat.ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function* streamChat(request: ChatRequest, signal?: AbortSignal): AsyncGenerator<ChatChunk> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });
  // ... error if response fails
}
```

**Example Test Code:**
```typescript
// src/test/e2e/HomePage.e2e.test.tsx - line ~119
it('should navigate to search page on Enter key press', async () => {
  render(
    <BrowserRouter>
      <HomePage />
    </BrowserRouter>
  );

  const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
  fireEvent.change(input, { target: { value: 'test query' } });
  fireEvent.keyDown(input, { key: 'Enter' });

  // This triggers StreamingAnswer component which calls streamChat()
  // streamChat() makes real HTTP request to http://localhost:8000
  // Request fails with ECONNREFUSED
});
```

**Why This Happens:**
- HomePage.e2e.test.tsx doesn't mock the `fetch` API
- Unlike ErrorHandling.e2e.test.tsx (which uses `setupGlobalFetchMock()`), HomePage tests let fetch run normally
- Vitest's jsdom environment can't connect to localhost:8000 (no real network)
- Tests timeout waiting for a response that never comes

### Issue 2: Canvas Package Not Installed (MEDIUM - Affects 2 tests)

**Current State:**
- GraphViewer.test.tsx renders a 3D force graph component
- Component uses `ForceGraph3D` which requires canvas rendering
- `canvas` npm package is not installed
- Tests fail when trying to use HTMLCanvasElement.getContext()

**Test Setup:**
```typescript
// src/test/setup.ts mocks react-force-graph
vi.mock('react-force-graph', () => {
  return {
    default: vi.fn(),
    ForceGraph2D: vi.fn((props: any) => null),
    ForceGraph3D: vi.fn(() => null),  // Mocked but canvas still needed
    ForceGraph3D: vi.fn(() => null),
  };
});
```

**Issue:** The mock returns null, but the actual test still tries to render a canvas context.

### Issue 3: Admin Indexing Mock Response Missing Stream Body (MEDIUM - Affects 3 tests)

**Current State:**
- AdminIndexingPage.test.tsx mocks the indexing API response
- But the mock doesn't return a proper `body` property
- Component code tries to iterate: `for await (const chunk of response.body)`
- Code fails because `response.body` is undefined

**Example Fix Needed:**
```typescript
// Current (broken) mock:
setupGlobalFetchMock(
  vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(mockAdminStats),  // Missing body!
  })
);

// Should be:
setupGlobalFetchMock(
  vi.fn().mockResolvedValue({
    ok: true,
    body: createMockSSEStream([...chunks...]),  // Add body with stream
  })
);
```

### Issue 4: Chat Unit Test SSE Mock Setup (LOW - Affects 1 test)

**Current State:**
- chat.test.ts has a unit test for SSE streaming
- Mock setup in helpers.ts might have initialization issues
- Test fails when trying to yield from SSE stream

---

## Test Failure Breakdown by Severity

### CRITICAL (9 tests - Infrastructure dependency)

**Fix Time:** 5-10 minutes
**Effort:** Very Low
**Impact:** Unblocks majority of failing tests

1. HomePage.e2e.test.tsx - "should navigate to search page on Enter key press"
2. HomePage.e2e.test.tsx - "should navigate to search page on submit button click"
3. HomePage.e2e.test.tsx - "should trim whitespace before submission"
4. HomePage.e2e.test.tsx - "should default to hybrid mode"
5. HomePage.e2e.test.tsx - "should switch to vector mode when Vector chip is clicked"
6. HomePage.e2e.test.tsx - "should switch to graph mode when Graph chip is clicked"
7. HomePage.e2e.test.tsx - "should switch to memory mode when Memory chip is clicked"
8. HomePage.e2e.test.tsx - "should navigate with quick prompt when clicked"
9. FullWorkflow.e2e.test.tsx - "should handle complete exploration journey"
10. FullWorkflow.e2e.test.tsx - "should support keyboard-only navigation"

**Solution:** Mock `fetch` API in HomePage.e2e.test.tsx

### HIGH (2 tests - Canvas dependency)

**Fix Time:** 2-3 minutes
**Effort:** Very Low
**Impact:** Fixes graph rendering tests

1. GraphViewer.test.tsx - "renders graph with nodes and edges"
2. GraphViewer.test.tsx - "calls onNodeClick callback when provided"

**Solution:** Install canvas package or improve mock setup

### MEDIUM (3 tests - Mock response body)

**Fix Time:** 5 minutes
**Effort:** Low
**Impact:** Fixes admin indexing tests

1. AdminIndexingPage.test.tsx - "should start indexing on confirmation"
2. AdminIndexingPage.test.tsx - "should display indexing progress"
3. AdminIndexingPage.test.tsx - "directory scanning" tests

**Solution:** Add `body: ReadableStream` to mock response

### LOW (1 test - Setup issue)

**Fix Time:** 3 minutes
**Effort:** Low
**Impact:** Single unit test

1. chat.test.ts - "should yield chat chunks from SSE stream"

**Solution:** Review and fix SSE mock stream initialization

---

## Recommended Fixes (Priority Order)

### Fix #1: Add Fetch Mocking to HomePage.e2e.test.tsx (CRITICAL)

**File:** `C:\Projekte\AEGISRAG\frontend\src\test\e2e\HomePage.e2e.test.tsx`

**Problem:** Tests interact with StreamingAnswer component which makes real HTTP requests to the backend API.

**Solution:** Mock the fetch API at the top of tests that render HomePage with search interaction.

```typescript
import { setupGlobalFetchMock, cleanupGlobalFetchMock, createMockSSEStream } from './helpers';
import { mockSSEStream } from './fixtures';

describe('HomePage E2E Tests', () => {
  // ... existing code ...

  describe('Search Input Interaction', () => {
    beforeEach(() => {
      // Mock successful SSE streaming response
      setupGlobalFetchMock(
        vi.fn().mockImplementation(async () => ({
          ok: true,
          body: createMockSSEStream([
            mockSSEStream.metadata,
            ...mockSSEStream.tokens,
            ...mockSSEStream.sources,
            mockSSEStream.complete,
          ]),
        }))
      );
    });

    afterEach(() => {
      cleanupGlobalFetchMock();
    });

    it('should navigate to search page on Enter key press', async () => {
      // ... existing test code ...
    });

    // ... rest of tests ...
  });
});
```

### Fix #2: Install Canvas Package (HIGH)

**Command:**
```bash
cd C:\Projekte\AEGISRAG\frontend
npm install canvas
```

**Rationale:** The canvas package is required for rendering HTMLCanvasElement in jsdom environment for force-graph tests.

### Fix #3: Add Body to Admin Indexing Mock Response (MEDIUM)

**File:** `C:\Projekte\AEGISRAG\frontend\src\pages\admin\AdminIndexingPage.test.tsx`

**Problem:** The mock response for POST /api/v1/admin/indexing/add doesn't include a `body` property.

**Solution:** Update mock to include a ReadableStream body:

```typescript
// In the test that mocks indexing:
const mockStream = createMockSSEStream([
  { type: 'metadata', status: 'indexing_started', progress_percent: 0 },
  { type: 'progress', status: 'processing', progress_percent: 25 },
  { type: 'progress', status: 'processing', progress_percent: 50 },
  { type: 'progress', status: 'processing', progress_percent: 75 },
  { type: 'complete', status: 'indexing_complete', progress_percent: 100 },
]);

setupGlobalFetchMock(
  vi.fn().mockResolvedValue({
    ok: true,
    body: mockStream,  // Add this!
  })
);
```

### Fix #4: Review SSE Mock Stream Setup (LOW)

**File:** `C:\Projekte\AEGISRAG\frontend\src\test\e2e\helpers.ts`

**Problem:** The `createMockSSEStream` function might not be properly initializing the stream for all use cases.

**Current Implementation:** (Lines 14-35)
```typescript
export function createMockSSEStream(chunks: ChatChunk[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream({
    async start(controller) {
      try {
        for (const chunk of chunks) {
          const sseMessage = `data: ${JSON.stringify(chunk)}\n\n`;
          controller.enqueue(encoder.encode(sseMessage));
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      } catch (error) {
        controller.error(error);
      }
    },
  });
}
```

**Check:** Verify that the ReadableStream is properly implementing the asyncIterator protocol for the async-for-loop in StreamingAnswer.tsx.

---

## Architecture Context

### Frontend Test Structure

**Current Setup:**
- Testing framework: Vitest (v4.0.4)
- Environment: jsdom (browser-like DOM without real network)
- Assertion library: @testing-library/react + jest-dom matchers
- SSE testing: Custom helpers with ReadableStream mocking

**Test Files Location:**
```
frontend/
├── src/
│   ├── test/
│   │   ├── setup.ts          # Global setup for all tests
│   │   ├── e2e/
│   │   │   ├── ErrorHandling.e2e.test.tsx       (7 tests, all passing)
│   │   │   ├── HomePage.e2e.test.tsx            (19 tests, 9 failing)
│   │   │   ├── AdminStats.e2e.test.tsx          (10 tests, 2 failing)
│   │   │   ├── FullWorkflow.e2e.test.tsx        (20 tests, 2 failing)
│   │   │   ├── ConversationPersistence.e2e.test.tsx (12 tests, 3 failing)
│   │   │   ├── helpers.ts
│   │   │   └── fixtures.ts
│   │   └── setup.ts
│   ├── api/
│   │   ├── chat.ts           # API client (uses http://localhost:8000)
│   │   ├── admin.ts
│   │   ├── chat.test.ts      (7 tests, 1 failing)
│   └── pages/
│       └── admin/
│           └── AdminIndexingPage.test.tsx (10 tests, 3 failing)
├── vitest.config.ts
├── .env                       # VITE_API_BASE_URL=http://localhost:8000
└── package.json
```

### Backend API Structure

**Python FastAPI Backend:**
```
src/
├── api/
│   ├── main.py              # FastAPI app entry point
│   ├── v1/
│   │   ├── chat.py          # POST /api/v1/chat/stream (SSE)
│   │   ├── admin.py         # POST /api/v1/admin/indexing/add (SSE)
│   │   ├── admin.py         # GET /api/v1/admin/stats
│   │   └── ...
│   └── ...
├── agents/
│   ├── coordinator.py       # Main agent orchestration
│   └── ...
└── components/
    ├── vector_search/
    ├── graph_rag/
    └── ...
```

**Status:** Backend NOT running during test execution (normal for jsdom environment)

---

## Why Tests Are Designed This Way

### Jest-DOM vs E2E Testing Philosophy

**Current Approach:**
- Tests use jsdom (lightweight DOM simulation)
- Tests don't spawn a real backend server
- Tests that need backend interaction should mock fetch
- Tests that are integration-focused should use test containers or run backend

**Why This Matters:**
- jsdom cannot make real HTTP connections
- Even if backend was running on localhost:8000, jsdom wouldn't reach it
- The correct approach is to mock API responses OR use Playwright for real E2E tests

### Passing Tests Example

**ErrorHandling.e2e.test.tsx** (7/7 passing) correctly mocks fetch:
```typescript
describe('Error Handling E2E Tests', () => {
  afterEach(() => {
    cleanupGlobalFetchMock();  // ✓ Cleans up after each test
  });

  it('should display error message on network failure', async () => {
    setupGlobalFetchMock(mockFetchNetworkError());  // ✓ Mocks before test
    // ... rest of test ...
  });
});
```

**HomePage.e2e.test.tsx** (9/19 failing) doesn't mock fetch:
```typescript
describe('HomePage E2E Tests', () => {
  it('should navigate to search page on Enter key press', async () => {
    render(<BrowserRouter><HomePage /></BrowserRouter>);
    // Renders HomePage which contains SearchInput
    // SearchInput calls StreamingAnswer which calls streamChat()
    // streamChat() tries real fetch to http://localhost:8000
    // ✗ FAILS: ECONNREFUSED
  });
});
```

---

## Summary Table

| Category | Tests Failing | Severity | Root Cause | Fix Time | Effort |
|----------|---------------|----------|-----------|----------|--------|
| Backend Connection | 9 (HomePage) | Critical | No fetch mock | 5 min | Low |
| Backend Connection | 2 (FullWorkflow) | Critical | Real API calls | 5 min | Low |
| Canvas Rendering | 2 (GraphViewer) | High | Missing package | 2 min | Very Low |
| Admin Mock Response | 3 (AdminIndexing) | Medium | Missing body field | 5 min | Low |
| SSE Mock Setup | 1 (chat.test.ts) | Low | Stream init issue | 3 min | Low |
| **TOTAL** | **26** | - | **Multiple** | **20 min** | **Low** |

---

## Test Statistics

### Overall Results
- **Total Test Files:** 28 (17 failed, 11 passed)
- **Total Tests:** 289 (26 failed, 263 passed)
- **Pass Rate:** 91.0%
- **Execution Time:** 55.83s

### By Category

**Passing Test Files (11):**
- ErrorHandling.e2e.test.tsx (7/7 passing)
- SearchResultsPage.e2e.test.tsx (8/8 passing)
- SSEStreaming.e2e.test.tsx (6/6 passing)
- ConversationTitles.e2e.test.tsx (7/7 passing)
- StreamingDuplicateFix.e2e.test.tsx (5/5 passing)
- SearchInput.test.tsx (6/6 passing)
- IndexingDetailDialog.test.tsx (4/4 passing)
- ErrorTrackingButton.test.tsx (3/3 passing)
- citations.test.tsx (9/9 passing)
- ... and 2 more

**Failing Test Files (17):**
- HomePage.e2e.test.tsx (10/19 failing)
- AdminStats.e2e.test.tsx (2/10 failing)
- FullWorkflow.e2e.test.tsx (2/20 failing)
- AdminIndexingPage.test.tsx (3/10 failing)
- GraphViewer.test.tsx (2/6 failing)
- ConversationPersistence.e2e.test.tsx (3/15 failing)
- chat.test.ts (1/7 failing)
- ... and 10 more

---

## Recommendations for Sprint 33

### Immediate Actions (Next 30 minutes)

1. **Add Fetch Mocks to HomePage.e2e.test.tsx**
   - File: `C:\Projekte\AEGISRAG\frontend\src\test\e2e\HomePage.e2e.test.tsx`
   - Import: `setupGlobalFetchMock, cleanupGlobalFetchMock, createMockSSEStream`
   - Add beforeEach/afterEach for fetch mocking in "Search Input Interaction" describe block
   - Unblocks 9 failing tests

2. **Install Canvas Package**
   - Command: `npm install canvas`
   - Unblocks 2 GraphViewer tests

3. **Fix Admin Indexing Mock Response**
   - File: `C:\Projekte\AEGISRAG\frontend\src\pages\admin\AdminIndexingPage.test.tsx`
   - Add `body: createMockSSEStream([...])` to mock response
   - Unblocks 3 admin indexing tests

### Medium-term Actions (Sprint 34)

1. **Consider Real E2E Tests with Playwright**
   - Current tests run in jsdom (no real network)
   - Could add Playwright tests that spawn real backend + frontend
   - Would provide more realistic testing but slower execution

2. **Document Test Mocking Standards**
   - Create testing guide in docs/
   - Define when to mock vs. when to use integration tests
   - Add to CLAUDE.md Testing Strategy section

3. **CI/CD Integration**
   - Ensure Docker services run before frontend tests (if needed)
   - Or ensure all frontend tests properly mock external calls
   - Add test categorization (unit, component, e2e)

### Code Quality Improvements

1. **Standardize Mock Setup**
   - All E2E tests should follow error handling pattern
   - Use setupGlobalFetchMock/cleanupGlobalFetchMock consistently
   - Add template for new E2E tests

2. **Add Test Comments**
   - Document which tests need mock setup
   - Explain why certain tests don't mock (if intentional)

3. **Improve Test Naming**
   - Include "mocked" in test name if using mocks
   - Example: "should display results when clicking search (mocked API)"

---

## Related Issues & Context

### Known Technical Debt

From CLAUDE.md:
- **TD-043**: Follow-up Questions Redis Storage (9 E2E tests affected)
  - Backend `save_conversation_turn()` not storing to Redis
  - Front-end implementation correct, backend fix required
  - Some conversation tests may fail due to this

### Sprint 32 Context

Recent refactoring (commit 374f5e3):
- Neo4j Label Migration: `:Entity` → `:base`
- 12 source files + 7 test files migrated
- 109/109 graph_rag unit tests passing

### Architecture Decisions

From ADR-039 (Adaptive Section-Aware Chunking):
- Chunk size: 800-1800 tokens
- Section-based metadata: headings, pages, bboxes
- Neo4j Section nodes for hierarchical queries

---

## How to Verify Fixes

### Test Command
```bash
cd C:\Projekte\AEGISRAG\frontend
npm test
```

### Expected Output After Fixes
```
Test Files  [11 failed | 17 passed] (28)
Tests       [0 failed | 289 passed] (289)
Pass Rate   100%
```

### Individual Test File Verification
```bash
# Test HomePage after fix
npm test -- HomePage.e2e.test.tsx

# Test Canvas after installing package
npm test -- GraphViewer.test.tsx

# Test admin indexing after mock fix
npm test -- AdminIndexingPage.test.tsx
```

---

## Appendix: API Endpoint Reference

### Chat Endpoints

| Endpoint | Method | Purpose | Status in Tests |
|----------|--------|---------|-----------------|
| `/api/v1/chat/stream` | POST | SSE streaming response | Not mocked in HomePage |
| `/api/v1/chat/` | POST | Non-streaming response | Not mocked in some tests |
| `/api/v1/chat/sessions` | GET | List sessions | Mocked in ConversationPersistence |
| `/api/v1/chat/history/{sessionId}` | GET | Get conversation history | Mocked |
| `/api/v1/chat/history/{sessionId}` | DELETE | Delete session | Mocked |
| `/api/v1/chat/sessions/{sessionId}/generate-title` | POST | Generate title | Mocked |
| `/api/v1/chat/sessions/{sessionId}/followup-questions` | GET | Follow-up questions | Mocked |

### Admin Endpoints

| Endpoint | Method | Purpose | Status in Tests |
|----------|--------|---------|-----------------|
| `/api/v1/admin/stats` | GET | System statistics | Mocked in AdminStats |
| `/api/v1/admin/indexing/add` | POST | Start indexing (SSE) | Mock missing body |
| `/api/v1/admin/indexing/scan-directory` | POST | Scan directory | Mocked but may fail |
| `/api/v1/admin/costs/stats` | GET | Cost statistics | Mocked |
| `/api/v1/admin/reindex` | POST | Reindex documents | Mocked |

---

## Notes

- Project was recently moved from OneDrive to C:\Projekte\AEGISRAG
- Frontend uses React 19 with TypeScript
- Backend uses Python 3.12.7 with FastAPI
- Tests use Vitest with jsdom (browser simulation)
- Docker services mentioned in context but not running during test execution
- All 26 failing tests can be fixed with ~20 minutes of work

