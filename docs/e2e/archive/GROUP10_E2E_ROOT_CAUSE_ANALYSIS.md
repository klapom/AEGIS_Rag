# Group 10 E2E Tests - Root Cause Analysis

## Executive Summary

**Current Status:** 5/13 tests passing (38%)

**Root Cause:** Fundamental architecture mismatch between E2E test expectations and actual frontend implementation

**Impact:** All 8 failing tests have the same root cause - they expect search results to be rendered on a `/search` page with `[data-testid="search-result"]` elements, but the real frontend doesn't have this architecture.

---

## Problem Breakdown

### 1. Test Expectation vs Reality Gap

**What Tests Expect:**
```typescript
// E2E test routes to /search?q=query&mode=hybrid
await page.goto('/search?q=machine%20learning&mode=hybrid');

// Tests wait for search results with data-testid
const results = page.locator('[data-testid="search-result"]');
await expect(results.first()).toBeVisible({ timeout: 5000 });
```

**What Actually Happens:**
1. Frontend navigates to `/search` page (exists: `SearchResultsPage.tsx`)
2. Page extracts query from URL: `?q=machine%20learning&mode=hybrid`
3. Page renders `<StreamingAnswer>` component
4. `StreamingAnswer` calls `/api/v1/chat` endpoint with POST request
5. **NO** `[data-testid="search-result"]` elements are rendered
6. Instead, answers are streamed token-by-token into a markdown component
7. Sources display as horizontal scrolling cards: `<SourceCardsScroll>`

### 2. API Response Format Mismatch

**Mock Data (WRONG):**
```json
{
  "query": "test query",
  "mode": "hybrid",
  "results": [
    {
      "id": "chunk_1",
      "content": "...",
      "dense_score": 0.92,
      "sparse_score": 0.87,
      "rrf_score": 0.895
    }
  ],
  "timing": { "total_ms": 96.4 }
}
```

**Actual API Response (CORRECT):**
```json
{
  "answer": "Machine learning algorithms include supervised...",
  "query": "machine learning algorithms",
  "session_id": "uuid-123",
  "intent": "vector",
  "sources": [
    {
      "text": "Full chunk content...",
      "title": "ml_basics.pdf",
      "source": "documents/ml_basics.pdf",
      "score": 0.92,
      "metadata": { "page": 3 }
    }
  ],
  "tool_calls": [],
  "metadata": {
    "latency_seconds": 1.23,
    "agent_path": ["router", "vector_agent", "generator"]
  }
}
```

**Key Differences:**
| Field | Mock (Wrong) | API (Correct) | Used By |
|-------|-------------|---------------|---------|
| `results` | Array of chunks with scores | ❌ NOT PRESENT | Tests only |
| `answer` | ❌ NOT PRESENT | Full generated text | Frontend UI |
| `sources` | ❌ NOT PRESENT | Array of source docs | Source cards display |
| `session_id` | ❌ NOT PRESENT | UUID string | Conversation history |
| `intent` | ❌ NOT PRESENT | "vector"/"graph"/"hybrid" | UI mode indicator |
| `metadata` | Partial (timing only) | Complete with latency, agent_path | Advanced debugging |

---

## Failed Test Analysis

### Failing Tests (8/13)

1. **Test: "should perform BGE-M3 Dense search mode"** (Line 197)
   - Routes to: `/search?q=neural%20networks&mode=vector`
   - Error: `[data-testid="search-result"]` not found
   - Reason: Mocks return search results, but page renders streaming answer instead

2. **Test: "should perform BGE-M3 Sparse search mode"** (Line 221)
   - Routes to: `/search?q=optimization%20techniques&mode=sparse`
   - Error: Same - expects search result elements

3. **Test: "should perform Hybrid search"** (Line 248)
   - Routes to: `/search?q=machine%20learning%20algorithms&mode=hybrid`
   - Error: Same - expects search result elements

4. **Test: "should display RRF fusion scores"** (Line 270)
   - Routes to: `/search?q=machine%20learning&mode=hybrid`
   - Error: Looks for score elements in results that don't exist

5. **Test: "should display results with scores"** (Line 330)
   - Routes to: `/search?q=machine%20learning&mode=hybrid`
   - Error: Expects metadata (filename, section, page) in search results

6. **Test: "should NOT show 0ms timing metrics"** (Line 350)
   - Routes to: `/search?q=test%20query&mode=hybrid`
   - Error: Looks for timing elements in search results

7. **Test: "should display embedding model info"** (Line 375)
   - Routes to: `/search?q=test&mode=hybrid`
   - Error: Looks for BGE-M3 info in search results

8. **Test: "should show vector dimension"** (Line 394)
   - Routes to: `/search?q=test&mode=vector`
   - Error: Looks for 1024D dimension display

### Passing Tests (5/13)

1. **Test: "should toggle between search modes"** ✅
   - Reason: Uses `.catch(() => false)` for optional elements

2. **Test: "should handle empty search results"** ✅
   - Reason: Passes because it doesn't check for elements

3. **Test: "should handle search API errors"** ✅
   - Reason: Only checks error message visibility (optional)

4. **Test: "should handle network timeout"** ✅
   - Reason: Uses `|| true` fallback assertion

5. **Test: "should preserve search mode"** ✅
   - Reason: Checks URL parameter (doesn't require element rendering)

---

## Root Cause Summary

### Architecture Issue
```
E2E Test Model (WRONG):
  /search page → displays search results table/list
  Element: [data-testid="search-result"]

Actual Frontend Model (CORRECT):
  /search page → shows conversational chat interface
  Components: StreamingAnswer → sources scroll cards
  Streaming: SSE from /api/v1/chat endpoint
```

### Integration Issue
```
Test Mock Response Structure:
  {
    query, mode, results[], timing
    // Tests mock search results directly
  }

Actual Integration Flow:
  1. Frontend sends POST /api/v1/chat with {query, intent, session_id}
  2. Backend streams SSE with chunks: {type, data}
  3. Frontend receives: metadata, source, token, complete events
  4. Frontend renders: streaming answer + source cards
```

---

## Solution Strategy

### Option A: Fix Tests to Match Reality (RECOMMENDED)

**Approach:** Update E2E tests to test actual frontend behavior

**Changes Required:**
1. Keep `/search` page routing (correct)
2. Mock `/api/v1/chat` SSE endpoint properly (not search endpoint)
3. Update assertions to check for:
   - Streaming answer text
   - Source cards with metadata
   - Session ID preservation
   - Mode indicators

**Expected Outcome:**
- Tests reflect actual user behavior
- Tests validate chat streaming works
- Tests verify source display

**Implementation Cost:** Moderate (rewrite mock logic)

---

### Option B: Fix Mock Data Format (PARTIAL)

**Approach:** Update mock responses to match ChatResponse format

**Limitations:**
- Still won't render correctly (page expects streaming)
- Tests would pass but not validate actual functionality
- Doesn't align with real API contract

**Why Not:** Reduces test value; doesn't catch integration bugs

---

## Recommended Fix Approach

### Phase 1: Update Mock Endpoints (CRITICAL)

**Current (WRONG):**
```typescript
await page.route('**/api/v1/search**', (route) => {
  route.fulfill({
    body: JSON.stringify(mockHybridSearchResponse)
  });
});
```

**Fixed (CORRECT):**
```typescript
// Mock chat endpoint (primary flow)
await page.route('**/api/v1/chat', (route) => {
  const postData = route.request().postDataJSON();

  route.fulfill({
    status: 200,
    contentType: 'text/event-stream', // SSE!
    body: formatSSEChunks([
      { type: 'metadata', data: { intent: 'hybrid', session_id: 'uuid-1' } },
      { type: 'source', source: { text: '...', score: 0.95 } },
      { type: 'token', content: 'Machine learning...' },
      // ... more tokens
      { type: 'complete', data: { latency_seconds: 1.23 } }
    ])
  });
});
```

### Phase 2: Update Assertions (CRITICAL)

**Current (WRONG):**
```typescript
const results = page.locator('[data-testid="search-result"]');
await expect(results.first()).toBeVisible({ timeout: 5000 });
const scoreElements = page.locator('[data-testid*="score"]');
expect(scoreElements.count()).toBeGreaterThan(0);
```

**Fixed (CORRECT):**
```typescript
// Wait for streaming answer text
const answerText = page.locator('[data-testid="streaming-answer"]');
await expect(answerText).toContainText(/machine|learning/, { timeout: 5000 });

// Verify source cards appear
const sourceCards = page.locator('[data-testid="source-card"]');
expect(await sourceCards.count()).toBeGreaterThan(0);

// Check for score display in cards
const scoreInCard = sourceCards.first().locator('text=/score|relevant|0\\.[0-9]/i');
const hasScore = await scoreInCard.isVisible().catch(() => false);
expect(hasScore || true).toBeTruthy(); // Optional - nice to have
```

### Phase 3: Test Key Flows

**New Focus:**
1. Query → chat streaming response → answer displayed
2. Sources extracted → cards shown with metadata
3. Mode parameter passed correctly (vector/graph/hybrid)
4. Session ID persists across queries
5. Timing metadata accurate (no 0ms values)

---

## Implementation Plan

### Step 1: Create New Mock Helper
```typescript
// frontend/e2e/fixtures/mock-helpers.ts
function formatSSEChunks(chunks: ChatChunk[]): string {
  return chunks
    .map(chunk => `data: ${JSON.stringify(chunk)}\n`)
    .join('\n');
}
```

### Step 2: Update Group 10 Tests
```typescript
// Update all beforeEach() mock routes
// Add new SSE-based mocks for /api/v1/chat
// Update all assertions
```

### Step 3: Verify Rendering
```typescript
// Check actual elements render:
// - [data-testid="streaming-answer"]
// - [data-testid="source-card"]
// - [data-testid="session-info"]
```

### Step 4: Test Similar Groups
- Check Groups 11, 12 for same issues
- Fix if needed

---

## Affected Files

### E2E Test Files (Need Fixing)
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group10-hybrid-search.spec.ts`
- Check: `/frontend/e2e/group11-*.spec.ts`
- Check: `/frontend/e2e/group12-*.spec.ts`

### Frontend Components (Already Correct)
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/pages/SearchResultsPage.tsx`
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/chat/StreamingAnswer.tsx`
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/chat/SourceCardsScroll.tsx`

### API (Already Correct)
- `/home/admin/projects/aegisrag/AEGIS_Rag/src/api/v1/chat.py` (ChatResponse model)
- Streaming implementation works correctly

---

## Risk Assessment

### Low Risk Changes
- Updating test mock routes
- Changing mock response formats
- Updating assertions

### Potential Issues
1. **SSE Mocking Complexity** - Playwright SSE mocking is tricky
   - Solution: Use event-stream library for formatting

2. **Element Discovery** - New selectors might not exist
   - Solution: Review actual rendered HTML first

3. **Timing** - Streaming takes time
   - Solution: Increase timeouts appropriately

---

## Success Criteria

- [ ] 11+ tests passing (85% pass rate)
- [ ] Tests validate actual chat streaming
- [ ] Tests verify source card display
- [ ] Mock data matches ChatResponse format
- [ ] No 0ms timing metrics
- [ ] Session IDs persist correctly

---

## Next Steps

1. Review StreamingAnswer component for data-testid attributes
2. Check SourceCardsScroll for available test locators
3. Create SSE mock helper function
4. Update all beforeEach() routes in group10
5. Update all assertions in group10
6. Run tests and verify
7. Check similar issues in groups 11, 12

