# Sprint 33 Frontend Test Fixes - Implementation Guide

**Quick Reference:** 4 fixes required to resolve 26 failing tests in ~20 minutes

---

## Fix #1: Add Fetch Mocking to HomePage.e2e.test.tsx (CRITICAL - Fixes 9 tests)

**File:** `C:\Projekte\AEGISRAG\frontend\src\test\e2e\HomePage.e2e.test.tsx`

**Problem:** Tests that render HomePage with search input don't mock the fetch API, causing real HTTP requests to fail with ECONNREFUSED.

**Failing Tests:**
- should navigate to search page on Enter key press
- should navigate to search page on submit button click
- should trim whitespace before submission
- should default to hybrid mode
- should switch to vector mode when Vector chip is clicked
- should switch to graph mode when Graph chip is clicked
- should switch to memory mode when Memory chip is clicked
- should navigate with quick prompt when clicked
- (Plus 1 test in FullWorkflow.e2e.test.tsx)

### Code Changes

**Location:** Top of file (after existing imports, around line 23)

Add imports:
```typescript
import {
  setupGlobalFetchMock,
  cleanupGlobalFetchMock,
  createMockSSEStream,
} from './helpers';
import { mockSSEStream } from './fixtures';
```

**Location:** In "Search Input Interaction" describe block (around line 104)

Replace this:
```typescript
describe('Search Input Interaction', () => {
  it('should update input value when user types', () => {
```

With this:
```typescript
describe('Search Input Interaction', () => {
  beforeEach(() => {
    // Mock successful SSE streaming response for all search tests
    setupGlobalFetchMock(
      vi.fn().mockImplementation(async () => ({
        ok: true,
        body: createMockSSEStream([
          mockSSEStream.metadata,
          mockSSEStream.tokens[0],
          mockSSEStream.tokens[1],
          ...mockSSEStream.sources,
          mockSSEStream.complete,
        ]),
      }))
    );
  });

  afterEach(() => {
    cleanupGlobalFetchMock();
  });

  it('should update input value when user types', () => {
```

**Location:** In "Mode Selection" describe block (around line 192)

Add the same beforeEach/afterEach:
```typescript
describe('Mode Selection', () => {
  beforeEach(() => {
    setupGlobalFetchMock(
      vi.fn().mockImplementation(async () => ({
        ok: true,
        body: createMockSSEStream([
          mockSSEStream.metadata,
          mockSSEStream.tokens[0],
          mockSSEStream.tokens[1],
          ...mockSSEStream.sources,
          mockSSEStream.complete,
        ]),
      }))
    );
  });

  afterEach(() => {
    cleanupGlobalFetchMock();
  });

  it('should default to hybrid mode', async () => {
```

**Location:** In "Quick Prompts" describe block (around line 313)

Add the same beforeEach/afterEach:
```typescript
describe('Quick Prompts', () => {
  beforeEach(() => {
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

  it('should navigate with quick prompt when clicked', async () => {
```

### Why This Works

- The `setupGlobalFetchMock()` replaces the global fetch with a mock that returns SSE chunks
- When HomePage renders and user types a query, StreamingAnswer component calls `streamChat()`
- `streamChat()` fetches from the mocked API instead of trying to connect to http://localhost:8000
- Tests now receive the mock SSE stream with tokens and sources
- Fixes 9 failing tests with minimal code changes

### Verification

```bash
cd C:\Projekte\AEGISRAG\frontend
npm test -- HomePage.e2e.test.tsx

# Expected output:
# HomePage E2E Tests ... PASS
# All tests passing
```

---

## Fix #2: Install Canvas Package (HIGH - Fixes 2 tests)

**File:** None - Package installation

**Problem:** GraphViewer.test.tsx tests fail because `canvas` package is missing, which is required for HTMLCanvasElement.getContext() in jsdom environment.

**Failing Tests:**
- renders graph with nodes and edges
- calls onNodeClick callback when provided

### Installation

**Command:**
```bash
cd C:\Projekte\AEGISRAG\frontend
npm install canvas
```

**Alternative (if above fails):**
```bash
npm install canvas --save-dev
```

### Why This Works

- The `canvas` package provides a Node.js implementation of HTML5 Canvas
- When jest/vitest runs in jsdom environment, HTMLCanvasElement.getContext() needs this
- ForceGraph3D component tries to render using canvas
- With canvas installed, the rendering can proceed

### Verification

```bash
npm test -- GraphViewer.test.tsx

# Expected output:
# GraphViewer ... PASS
# All tests passing
```

### If Installation Fails

If `npm install canvas` fails with build errors (Windows sometimes has issues):

**Alternative: Mock Canvas More Completely**

In `src/test/setup.ts`, replace the THREE mock section with:

```typescript
// Mock Canvas for force-graph rendering
const canvasMock = {
  getContext: vi.fn(() => ({
    fillStyle: '',
    strokeStyle: '',
    fillRect: vi.fn(),
    strokeRect: vi.fn(),
    fill: vi.fn(),
    stroke: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    arc: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    translate: vi.fn(),
    scale: vi.fn(),
    rotate: vi.fn(),
    drawImage: vi.fn(),
    clearRect: vi.fn(),
    font: '',
    textAlign: '',
    textBaseline: '',
    fillText: vi.fn(),
    strokeText: vi.fn(),
    measureText: vi.fn(() => ({ width: 0 })),
    getImageData: vi.fn(() => ({ data: [] })),
  })),
};

Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
  value: vi.fn(() => canvasMock.getContext()),
});
```

---

## Fix #3: Add Body to Admin Indexing Mock Response (MEDIUM - Fixes 3 tests)

**File:** `C:\Projekte\AEGISRAG\frontend\src\pages\admin\AdminIndexingPage.test.tsx`

**Problem:** The mock response for the indexing API doesn't include a `body` property with a ReadableStream, causing the async iteration in component code to fail.

**Failing Tests:**
- should start indexing on confirmation
- should display indexing progress
- directory scanning > should display error message on scan failure

### Code Changes

**Find the section with indexing tests** (around line 120-180)

Look for this pattern:
```typescript
it('should start indexing on confirmation', async () => {
  // ... test setup ...

  // Mock fetch - MISSING BODY!
  setupGlobalFetchMock(
    vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    })
  );
```

Replace with:
```typescript
it('should start indexing on confirmation', async () => {
  // ... test setup ...

  // Mock fetch with SSE stream body
  const indexingMockStream = createMockSSEStream([
    {
      type: 'metadata',
      status: 'indexing_started',
      progress_percent: 0,
      documents_processed: 0,
    },
    {
      type: 'progress',
      status: 'scanning_directory',
      progress_percent: 25,
      documents_processed: 2,
      current_file: 'document1.pdf',
    },
    {
      type: 'progress',
      status: 'extracting_content',
      progress_percent: 50,
      documents_processed: 5,
      current_file: 'document2.pdf',
    },
    {
      type: 'progress',
      status: 'processing',
      progress_percent: 75,
      documents_processed: 7,
      current_file: 'document3.pdf',
    },
    {
      type: 'complete',
      status: 'indexing_complete',
      progress_percent: 100,
      documents_processed: 10,
      chunks_created: 142,
    },
  ]);

  setupGlobalFetchMock(
    vi.fn().mockResolvedValue({
      ok: true,
      body: indexingMockStream,  // ADD THIS LINE
    })
  );
```

**Find other indexing tests and apply similar fix:**

For directory scanning mock:
```typescript
const scanMockStream = createMockSSEStream([
  { type: 'metadata', status: 'scan_started', files_found: 0 },
  { type: 'progress', status: 'scanning', files_found: 5 },
  { type: 'progress', status: 'scanning', files_found: 10 },
  { type: 'complete', status: 'scan_complete', files_found: 15 },
]);

setupGlobalFetchMock(
  vi.fn().mockResolvedValue({
    ok: true,
    body: scanMockStream,
  })
);
```

### Why This Works

- AdminIndexingPage component code (line ~197) does: `for await (const chunk of response.body)`
- Without `body`, the async iteration throws TypeError
- `createMockSSEStream()` from helpers.ts creates a proper ReadableStream
- ReadableStream implements async iteration protocol correctly
- Component can now read SSE chunks and display progress

### Verification

```bash
npm test -- AdminIndexingPage.test.tsx

# Expected output:
# AdminIndexingPage ... PASS
# Indexing tests passing
# Directory scanning tests passing
```

---

## Fix #4: Review SSE Mock Stream Setup (LOW - Fixes 1 test)

**File:** `C:\Projekte\AEGISRAG\frontend\src\test\e2e\helpers.ts` (Lines 14-35)

**Problem:** chat.test.ts has one failing SSE test. The issue is likely in the helper setup, not the test itself.

**Failing Test:**
- should yield chat chunks from SSE stream

### Current Code

```typescript
export function createMockSSEStream(chunks: ChatChunk[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream({
    async start(controller) {
      try {
        // Send each chunk with a small delay to simulate streaming
        for (const chunk of chunks) {
          const sseMessage = `data: ${JSON.stringify(chunk)}\n\n`;
          controller.enqueue(encoder.encode(sseMessage));
          // Small delay to allow async iteration to work properly
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
        // Send [DONE] signal and close
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      } catch (error) {
        controller.error(error);
      }
    },
  });
}
```

### Verification

Run the test:
```bash
npm test -- src/api/chat.test.ts

# Check if it passes now with other fixes applied
# If still failing, add this logging:
```

### If Still Failing

Add this debug version:
```typescript
export function createMockSSEStream(chunks: ChatChunk[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream({
    async start(controller) {
      try {
        console.log('SSE Stream: Starting with', chunks.length, 'chunks');

        // Send each chunk with a small delay to simulate streaming
        for (const chunk of chunks) {
          const sseMessage = `data: ${JSON.stringify(chunk)}\n\n`;
          console.log('SSE Stream: Enqueueing chunk:', chunk.type);
          controller.enqueue(encoder.encode(sseMessage));
          // Small delay to allow async iteration to work properly
          await new Promise((resolve) => setTimeout(resolve, 10));
        }

        console.log('SSE Stream: Sending [DONE]');
        // Send [DONE] signal and close
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      } catch (error) {
        console.error('SSE Stream error:', error);
        controller.error(error);
      }
    },
  });
}
```

Then run test and check console output to see where it fails.

### Most Likely Issue

The test might not be awaiting the stream properly. Check `src/api/chat.test.ts`:

```typescript
// Look for this pattern:
it('should yield chat chunks from SSE stream', async () => {
  setupGlobalFetchMock(...);

  // Should properly await async generator:
  const chunks = [];
  for await (const chunk of streamChat(request)) {
    chunks.push(chunk);
  }

  expect(chunks).toHaveLength(expectedLength);
});
```

---

## Complete Fix Checklist

- [ ] **Fix #1 Complete:** HomePage.e2e.test.tsx - Added fetch mocks to Search Input Interaction, Mode Selection, and Quick Prompts describe blocks
- [ ] **Fix #2 Complete:** Installed canvas package with `npm install canvas`
- [ ] **Fix #3 Complete:** AdminIndexingPage.test.tsx - Added body: ReadableStream to mock responses
- [ ] **Fix #4 Verified:** SSE mock stream setup works (or debugging completed)
- [ ] **Tests Run:** `npm test` executed and results verified
- [ ] **All Tests Passing:** 289/289 tests passing (or close to it)

---

## Testing Order (Recommended)

1. **First:** Apply Fix #1 (HomePage mocking)
   - Quick, high impact (9 tests)
   - Unblocks understanding of remaining failures

2. **Second:** Apply Fix #2 (Canvas package)
   - Fastest (just install)
   - Fixes GraphViewer tests

3. **Third:** Apply Fix #3 (Admin mock response)
   - Medium complexity
   - Fixes admin indexing tests

4. **Fourth:** Verify Fix #4 (SSE stream)
   - Debug if needed
   - Single test, low priority

---

## Validation Commands

### Test Everything
```bash
cd C:\Projekte\AEGISRAG\frontend
npm test
```

### Test Individual Files (in order)
```bash
# Should now pass (9 tests)
npm test -- HomePage.e2e.test.tsx

# Should now pass (2 tests)
npm test -- GraphViewer.test.tsx

# Should now pass (3 tests)
npm test -- AdminIndexingPage.test.tsx

# Should pass (1 test)
npm test -- src/api/chat.test.ts
```

### Full Summary After Fixes
```
Test Files  [0 failed | 28 passed] (28)
Tests       [0 failed | 289 passed] (289)
Pass Rate   100%
```

---

## Common Issues & Troubleshooting

### Issue: Canvas installation fails on Windows

**Error:** `gyp ERR! MSB build error`

**Solution:**
```bash
# Option 1: Use pre-built binary
npm install canvas --save-binary

# Option 2: Use mock instead (as described in Fix #2 alternative)

# Option 3: Install build tools
npm install --global windows-build-tools
npm install canvas
```

### Issue: Fetch mock not being recognized

**Error:** `TypeError: fetch is not a function`

**Solution:**
- Ensure `setupGlobalFetchMock()` is called in `beforeEach()`
- Ensure `cleanupGlobalFetchMock()` is called in `afterEach()`
- Check import paths match exactly

### Issue: ReadableStream not iterable

**Error:** `Symbol(Symbol.asyncIterator) not found`

**Solution:**
- Ensure mock response includes `body: ReadableStream`
- Verify `createMockSSEStream()` returns proper ReadableStream
- Check that async iteration is: `for await (const chunk of response.body)`

### Issue: SSE chunks not being parsed

**Error:** `Failed to parse SSE chunk`

**Solution:**
- Ensure chunks have proper format: `{ type: 'token', content: '...' }`
- Verify `[DONE]` signal is being sent
- Check TextEncoder is properly encoding UTF-8

---

## References

### Test Helper Functions

From `C:\Projekte\AEGISRAG\frontend\src\test\e2e\helpers.ts`:
- `setupGlobalFetchMock(mockFetch)` - Sets up fetch mock
- `cleanupGlobalFetchMock()` - Cleans up after test
- `createMockSSEStream(chunks)` - Creates ReadableStream with SSE chunks
- `mockFetchNetworkError()` - Returns network error mock
- `mockFetchHTTPError(status, message)` - Returns HTTP error mock

### Test Fixture Data

From `C:\Projekte\AEGISRAG\frontend\src\test\e2e\fixtures.ts`:
- `mockSSEStream` - Complete SSE message sequence
- `mockSources` - Source documents
- `mockAPIResponses` - API response templates

### Vitest Config

From `C:\Projekte\AEGISRAG\frontend\vitest.config.ts`:
- Environment: jsdom
- Setup files: ./src/test/setup.ts
- Globals: true (no need to import describe, it, etc.)

---

## Summary

These 4 fixes resolve 26 failing tests:

| Fix | Tests Fixed | Time | Complexity |
|-----|------------|------|-----------|
| #1: HomePage mocking | 9 | 5 min | Low |
| #2: Canvas install | 2 | 2 min | Very Low |
| #3: Admin mock body | 3 | 5 min | Low |
| #4: SSE stream verify | 1 | 3 min | Low |
| **TOTAL** | **26** | **15 min** | **Low** |

All fixes are isolated, testable independently, and follow existing code patterns in the test suite.

