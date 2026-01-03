# Sprint 73: E2E Test Implementation - Quick Wins & Core Journeys

**Status:** PLANNED
**Start Date:** 2026-01-06 (nach Sprint 72)
**Duration:** 8-10 Arbeitstage
**Total Story Points:** 55 SP
**Focus:** Implement high-value E2E tests for core user journeys

---

## Sprint Overview

Sprint 73 fokussiert auf **Quick Wins** und **Core User Journeys** E2E Tests:
- **Quick Wins** (28 tests, 2-3 Tage): Responsive, Error Handling, Multi-turn
- **Core Journeys** (30 tests, 5-6 Tage): Chat, Search, Graph Visualization

**Ziel:** Pass Rate von 68% → 85% (+17 Prozentpunkte)

---

## Feature Overview

| # | Feature | Tests | SP | Priority | Parallelisierbar |
|---|---------|-------|-----|----------|------------------|
| 73.1 | Responsive Design Tests | 13 | 5 | P0 | Ja |
| 73.2 | Error Handling Tests | 8 | 3 | P0 | Ja |
| 73.3 | Chat Multi-Turn Tests | 7 | 5 | P0 | Ja |
| 73.4 | Chat Interface Completion | 10 | 8 | P1 | Ja |
| 73.5 | Search & Retrieval Tests | 8 | 5 | P1 | Ja |
| 73.6 | Graph Visualization Tests | 12 | 13 | P1 | Ja |
| 73.7 | 2 Failed Pipeline Tests Fix | 2 | 2 | P0 | Nein |
| 73.8 | E2E Test Infrastructure | 0 | 8 | P2 | Nein |
| 73.9 | Documentation Update | 0 | 3 | P2 | Ja |
| 73.10 | Sprint Summary | 0 | 3 | P2 | Nein |

**Total: 60 tests, 55 SP**

---

## Feature 73.1: Responsive Design Tests (13 tests, 5 SP)

**Ziel:** Test all major pages at mobile (375px), tablet (768px), desktop (1024px+) viewports.

### Tests to Implement (13)

#### Chat Page (4 tests)
1. **Mobile (375px):**
   - Hamburger menu visible
   - Chat input takes full width
   - Message bubbles stack correctly
   - Sidebar hidden by default

2. **Tablet (768px):**
   - Sidebar visible
   - Chat input 60% width
   - 2-column layout

3. **Desktop (1024px+):**
   - Full sidebar visible
   - Chat input 50% width
   - 3-column layout (sidebar, chat, details)

#### Admin Dashboard (3 tests)
4. **Mobile:** Navigation stacks vertically
5. **Tablet:** 2-column grid for cards
6. **Desktop:** 3-column grid for cards

#### Graph Analytics (3 tests)
7. **Mobile:** Graph controls collapse
8. **Tablet:** Graph + sidebar side-by-side
9. **Desktop:** Full screen graph with floating controls

#### Domain Training (3 tests)
10. **Mobile:** Form stacks vertically
11. **Tablet:** 2-column form
12. **Desktop:** 3-column form with preview

**Implementation:**
```typescript
test('should be responsive on mobile (375px)', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/');

  // Test mobile-specific elements
  const hamburger = page.getByTestId('mobile-menu-toggle');
  await expect(hamburger).toBeVisible();
});
```

**Files:**
- `e2e/tests/chat/responsive.spec.ts` (4 tests)
- `e2e/tests/admin/responsive.spec.ts` (3 tests)
- `e2e/tests/graph/responsive.spec.ts` (3 tests)
- `e2e/tests/admin/domain-training-responsive.spec.ts` (3 tests)

**Success Criteria:**
- [ ] 13/13 tests passing
- [ ] All tests complete in <2 minutes
- [ ] No flakiness
- [ ] Screenshots captured for each viewport

---

## Feature 73.2: Error Handling Tests (8 tests, 3 SP)

**Ziel:** Test error scenarios across all major features.

### Tests to Implement (8)

#### API Error Tests (4 tests)
1. **Chat message fails (500 error):**
   - Display error message
   - Retry button visible
   - Message marked as failed

2. **Document upload fails (413 Too Large):**
   - Error toast appears
   - File upload cancelled
   - Clear error message

3. **Search timeout (504 Gateway Timeout):**
   - Loading spinner stops
   - Timeout error displayed
   - Retry search button

4. **Authentication expires (401 Unauthorized):**
   - Redirect to login
   - Session state cleared
   - Return to original page after login

#### Network Error Tests (2 tests)
5. **Offline mode:**
   - Offline banner displayed
   - Queue messages for later
   - Restore when online

6. **Slow network (3G simulation):**
   - Loading states visible
   - Progressive rendering
   - No timeout errors

#### Validation Error Tests (2 tests)
7. **Invalid input (client-side):**
   - Field highlights red
   - Inline error message
   - Submit button disabled

8. **Server validation error (400 Bad Request):**
   - Field-specific errors displayed
   - Form stays populated
   - Fix and resubmit works

**Implementation:**
```typescript
test('should handle API 500 error gracefully', async ({ page }) => {
  // Mock API error
  await page.route('**/api/v1/chat', route => {
    route.fulfill({
      status: 500,
      body: JSON.stringify({ error: 'Internal Server Error' })
    });
  });

  await page.goto('/');
  await page.getByTestId('chat-input').fill('Test message');
  await page.getByTestId('send-button').click();

  // Verify error handling
  const errorMessage = page.getByTestId('message-error');
  await expect(errorMessage).toBeVisible();
  await expect(errorMessage).toContainText('Failed to send');

  const retryButton = page.getByTestId('retry-message');
  await expect(retryButton).toBeVisible();
});
```

**Files:**
- `e2e/tests/errors/api-errors.spec.ts` (4 tests)
- `e2e/tests/errors/network-errors.spec.ts` (2 tests)
- `e2e/tests/errors/validation-errors.spec.ts` (2 tests)

**Success Criteria:**
- [ ] 8/8 tests passing
- [ ] All error scenarios covered
- [ ] User-friendly error messages verified
- [ ] Retry mechanisms tested

---

## Feature 73.3: Chat Multi-Turn Tests (7 tests, 5 SP)

**Ziel:** Test conversation context preservation across multiple turns.

### Tests to Implement (7)

1. **3-turn conversation with context:**
   - Turn 1: "What is machine learning?"
   - Turn 2: "How does it differ from AI?" (context: "it" = machine learning)
   - Turn 3: "Give me examples" (context: previous topics)
   - Verify: Each response references previous context

2. **5-turn conversation with pronoun resolution:**
   - Test pronoun references ("it", "they", "this", "that")
   - Verify correct entity resolution

3. **Context window limit (10 turns):**
   - Send 12 messages
   - Verify: Only last 10 turns used as context
   - Verify: Older messages still visible but not in context

4. **Multi-document conversation:**
   - Turn 1: Ask about Document A
   - Turn 2: Ask about Document B
   - Turn 3: Compare A and B
   - Verify: Both documents retrieved in context

5. **Follow-up after error:**
   - Turn 1: Valid question
   - Turn 2: API error (simulate)
   - Turn 3: Follow-up to Turn 1
   - Verify: Context preserved despite error

6. **Branch conversation (edit previous message):**
   - Send 3 messages
   - Edit message 2
   - Send message 4
   - Verify: New branch created, old branch preserved

7. **Conversation resume (page reload):**
   - Send 3 messages
   - Reload page
   - Send message 4
   - Verify: Context restored from history

**Implementation:**
```typescript
test('should preserve context across 3 turns', async ({ page }) => {
  await page.goto('/');

  // Turn 1
  await page.getByTestId('chat-input').fill('What is machine learning?');
  await page.getByTestId('send-button').click();
  await page.waitForSelector('[data-testid="chat-response"]');

  // Turn 2 (with pronoun "it")
  await page.getByTestId('chat-input').fill('How does it work?');
  await page.getByTestId('send-button').click();
  await page.waitForSelector('[data-testid="chat-response"]:nth-child(4)');

  // Turn 3
  await page.getByTestId('chat-input').fill('Give me examples');
  await page.getByTestId('send-button').click();
  await page.waitForSelector('[data-testid="chat-response"]:nth-child(6)');

  // Verify: Response 3 contains context from previous turns
  const response3 = page.locator('[data-testid="chat-response"]').nth(2);
  const text = await response3.textContent();

  // Should reference machine learning (from turn 1)
  expect(text).toMatch(/machine learning|ML/i);
});
```

**Files:**
- `e2e/tests/chat/multi-turn.spec.ts` (7 tests)

**Success Criteria:**
- [ ] 7/7 tests passing
- [ ] Context preservation verified
- [ ] Pronoun resolution tested
- [ ] Conversation branching works

---

## Feature 73.4: Chat Interface Completion (10 tests, 8 SP)

**Ziel:** Complete E2E tests for all chat features.

### Tests to Implement (10)

1. **Conversation history search:**
   - Search conversations by keyword
   - Filter by date range
   - Sort by relevance/date

2. **Pin/unpin messages:**
   - Pin important message
   - Verify pinned section visible
   - Unpin message
   - Verify removed from pinned

3. **Export conversation:**
   - Export as JSON
   - Export as PDF (if implemented)
   - Verify file download

4. **Share conversation:**
   - Generate public link
   - Copy link to clipboard
   - Open link in incognito (verify public access)

5. **Message formatting:**
   - Send message with markdown (bold, italic, code)
   - Verify rendered correctly
   - Send code block
   - Verify syntax highlighting

6. **Delete message:**
   - Delete user message
   - Verify removed from UI
   - Verify conversation history updated

7. **Edit sent message:**
   - Edit previous message
   - Verify edited indicator
   - Verify conversation branching

8. **Conversation privacy settings:**
   - Set conversation to private
   - Verify share disabled
   - Set to public
   - Verify share enabled

9. **Auto-save draft:**
   - Start typing message
   - Navigate away
   - Return to chat
   - Verify draft restored

10. **Message reactions (if implemented):**
    - React to message with emoji
    - Verify reaction count
    - Remove reaction

**Files:**
- `e2e/tests/chat/history.spec.ts` (3 tests)
- `e2e/tests/chat/message-actions.spec.ts` (4 tests)
- `e2e/tests/chat/export-share.spec.ts` (3 tests)

**Success Criteria:**
- [ ] 10/10 tests passing
- [ ] All chat features tested
- [ ] User workflows complete

---

## Feature 73.5: Search & Retrieval Tests (8 tests, 5 SP)

**Ziel:** Test advanced search features.

### Tests to Implement (8)

1. **Advanced filters - Date range:**
   - Select date range filter
   - Verify results filtered

2. **Advanced filters - Document type:**
   - Filter by PDF/TXT/etc
   - Verify only matching types shown

3. **Search pagination:**
   - Search with >10 results
   - Navigate to page 2
   - Verify results load

4. **Search result sorting:**
   - Sort by relevance (default)
   - Sort by date (newest first)
   - Sort by title (A-Z)

5. **Search autocomplete:**
   - Start typing query
   - Verify suggestions appear
   - Select suggestion
   - Verify search executes

6. **Search history:**
   - Perform 3 searches
   - Open history
   - Verify 3 queries listed
   - Click previous query
   - Verify search re-executes

7. **Save search query:**
   - Save search with name
   - Verify saved in sidebar
   - Click saved search
   - Verify executes

8. **Search within domain:**
   - Select domain filter
   - Perform search
   - Verify only domain results

**Files:**
- `e2e/tests/search/filters.spec.ts` (4 tests)
- `e2e/tests/search/features.spec.ts` (4 tests)

**Success Criteria:**
- [ ] 8/8 tests passing
- [ ] All search features tested

---

## Feature 73.6: Graph Visualization Tests (12 tests, 13 SP)

**Ziel:** Test graph interaction features.

### Tests to Implement (12)

1. **Graph zoom controls:**
   - Click zoom in
   - Verify graph zooms
   - Click zoom out
   - Reset zoom

2. **Graph pan:**
   - Drag graph
   - Verify pans correctly

3. **Node selection:**
   - Click node
   - Verify node highlighted
   - Verify details panel opens

4. **Multi-select nodes:**
   - Ctrl+click 3 nodes
   - Verify all selected
   - Verify batch actions available

5. **Edge filtering:**
   - Filter by relationship type
   - Verify edges filtered
   - Reset filter

6. **Graph layout algorithms:**
   - Switch to force-directed
   - Switch to hierarchical
   - Verify layout changes

7. **Export graph as image:**
   - Click export PNG
   - Verify download
   - Click export SVG
   - Verify download

8. **Graph search/filter nodes:**
   - Search for entity name
   - Verify node highlighted
   - Verify graph centers on node

9. **Node details panel:**
   - Click node
   - Verify properties displayed
   - Verify relationships listed

10. **Edge details panel:**
    - Click edge
    - Verify relationship type shown
    - Verify source/target shown

11. **Graph statistics overlay:**
    - Toggle statistics
    - Verify node count
    - Verify edge count
    - Verify density

12. **Community detection visualization:**
    - Run community detection
    - Verify communities colored
    - Verify legend displayed

**Files:**
- `e2e/tests/graph/interactions.spec.ts` (5 tests)
- `e2e/tests/graph/export.spec.ts` (2 tests)
- `e2e/tests/graph/details.spec.ts` (3 tests)
- `e2e/tests/graph/community-viz.spec.ts` (2 tests)

**Success Criteria:**
- [ ] 12/12 tests passing
- [ ] All graph features tested

---

## Feature 73.7: Fix 2 Failed Pipeline Tests (2 tests, 2 SP)

**Ziel:** Fix timing issues in pipeline-progress.spec.ts.

### Tests to Fix (2)

1. **Line 601:** "should update elapsed time in real-time"
   - **Issue:** Timing assertion too strict
   - **Fix:** Use polling instead of exact timing

2. **Line 632:** "should show completion status when all stages finish"
   - **Issue:** Mock returns 11% instead of 100%
   - **Fix:** Update mock sequence to end at 100%

**Estimated Effort:** 30 minutes

---

## Feature 73.8: E2E Test Infrastructure (0 tests, 8 SP)

**Ziel:** Improve test execution speed and reliability.

### Improvements (8 SP)

1. **Parallel Execution (2 SP):**
   - Configure 2-4 workers
   - Expected: 2-4x faster execution

2. **Test Sharding for CI/CD (2 SP):**
   - Split tests across 4 shards
   - Expected: 4x faster CI/CD

3. **Visual Regression Testing (2 SP):**
   - Add screenshot assertions
   - Catch UI regressions

4. **Accessibility Testing (2 SP):**
   - Integrate axe-playwright
   - WCAG 2.1 compliance

**Files:**
- `playwright.config.ts` (update)
- `.github/workflows/e2e-tests.yml` (new/update)

---

## Sprint 73 Success Criteria

### Test Metrics
- [ ] **Total Tests:** 236 → 296 (+60 tests)
- [ ] **Passing Tests:** 161 → 250 (+89 tests)
- [ ] **Pass Rate:** 68% → 85% (+17 percentage points)
- [ ] **Skipped Tests:** 29 → 1 (-28 tests)
- [ ] **Execution Time:** <5 minutes (with parallel execution)

### Quality Metrics
- [ ] All Quick Win tests passing (28/28)
- [ ] All Core Journey tests passing (30/30)
- [ ] 2 failed tests fixed
- [ ] Visual regression enabled
- [ ] Accessibility testing enabled

### Documentation
- [ ] Test coverage report
- [ ] Sprint 73 summary
- [ ] Updated E2E test documentation

---

## Parallel Execution Strategy

### Wave 1 (Day 1-2, parallel)
- 73.1 Responsive Design Tests (testing-agent)
- 73.2 Error Handling Tests (testing-agent)
- 73.7 Fix Failed Pipeline Tests (quick fix - 30 min)

### Wave 2 (Day 3-4, parallel)
- 73.3 Chat Multi-Turn Tests (testing-agent)
- 73.4 Chat Interface Completion (testing-agent)

### Wave 3 (Day 5-6, parallel)
- 73.5 Search & Retrieval Tests (testing-agent)
- 73.6 Graph Visualization Tests (testing-agent)

### Wave 4 (Day 7-8)
- 73.8 Test Infrastructure
- 73.9 Documentation
- 73.10 Sprint Summary

---

## Dependencies

**Sprint 72 Prerequisites:**
- ✅ MCP Tools UI complete
- ✅ Memory Management UI complete
- ✅ Domain Training UI complete
- ✅ API-Frontend gap analysis complete

**Sprint 73 Prerequisites:**
- All Sprint 72 features merged to main
- E2E test baseline established (68% pass rate)
- Test infrastructure ready (Playwright configured)

---

## Rollback Plan

**If tests are flaky:**
1. Increase timeouts
2. Add explicit waits
3. Improve selectors (data-testid)

**If infrastructure changes break tests:**
1. Revert playwright.config.ts changes
2. Run tests sequentially (1 worker)

---

**END OF SPRINT 73 PLAN**
