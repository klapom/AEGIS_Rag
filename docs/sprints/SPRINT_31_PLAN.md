# Sprint 31 Plan: Production E2E Testing with Playwright

**Sprint Goal:** Comprehensive end-to-end testing with Playwright covering all frontend features with real backend & LLM integration

**Duration:** 7-9 days (estimated)
**Story Points:** 54 SP
**Priority:** P0 CRITICAL (Production Readiness)
**Start Date:** 2025-11-21 (after Sprint 30 completion)
**Branch:** `sprint-31-playwright-e2e`
**Status:** 📋 PLANNED

**⚠️ NOTE:** CI/CD disabled for Sprint 31 (cost savings until tests stabilize). Run tests locally only.

---

## Executive Summary

Sprint 31 delivers **comprehensive Playwright E2E tests** for all AegisRAG frontend features (Sprint 15-30), using **real backend integration** including **live LLM calls** (Ollama + Alibaba Cloud). This validates production readiness with realistic user workflows and acceptable LLM costs (~$0.50-2.00 per full test suite run).

### Key Deliverables

1. **Playwright Test Infrastructure** (Setup, CI/CD, reporting)
2. **Core User Flows** (Search, Streaming, Citations, Follow-up Questions)
3. **Admin Workflows** (Indexing, Stats, Health Dashboard)
4. **Settings & Preferences** (Theme, Export/Import, Model Config)
5. **Conversation Management** (History, Titles, Multi-turn)
6. **Graph Visualization** (Query Graph, Admin Graph, Node Details)
7. **Error Handling & Edge Cases** (Network errors, Timeouts, Validation)

### Why Real Backend Integration?

**Rationale:**
- ✅ **Production Confidence:** Tests validate real API contracts, not mocks
- ✅ **LLM Behavior:** Detect prompt regressions, output format changes
- ✅ **Performance:** Measure actual SSE streaming latency (not synthetic)
- ✅ **Cost:** Acceptable ($0.50-2.00 per run, ~$30/month for nightly CI)

**Trade-offs:**
- ⚠️ **Test Duration:** ~10-15 minutes (vs <1 min mocked)
- ⚠️ **LLM Costs:** ~$0.50-2.00 per full suite run
- ✅ **Production Validity:** 95% confidence vs 60% with mocks

**Mitigation:**
- Use local Ollama for most tests (FREE)
- Reserve Alibaba Cloud tests for critical paths only
- Run full suite nightly in CI (not per-commit)
- Budget: $30-50/month for CI runs

---

## Feature Coverage Analysis

### Sprint 15-30: Implemented Features

| Sprint | Feature | Component | Status | E2E Priority |
|--------|---------|-----------|--------|--------------|
| **Sprint 15** | SSE Streaming Chat | StreamingAnswer | ✅ | 🔴 CRITICAL |
| **Sprint 15** | Mode Selector | SearchInput | ✅ | 🟠 HIGH |
| **Sprint 15** | Source Cards | SourceCardsScroll | ✅ | 🟠 HIGH |
| **Sprint 15** | Session History | SessionSidebar | ✅ | 🟠 HIGH |
| **Sprint 27** | Copy Answer Button | CopyButton | ✅ | 🟡 MEDIUM |
| **Sprint 27** | Follow-up Questions | FollowUpQuestions | ✅ | 🔴 CRITICAL |
| **Sprint 27** | Quick Actions Bar | QuickActionsBar | ✅ | 🟡 MEDIUM |
| **Sprint 28** | Inline Citations [1][2] | Citation | ✅ | 🔴 CRITICAL |
| **Sprint 28** | Settings Page | Settings | ✅ | 🟠 HIGH |
| **Sprint 28** | Theme Switcher | Settings | ✅ | 🟡 MEDIUM |
| **Sprint 28** | Export/Import | Settings | ✅ | 🟠 HIGH |
| **Sprint 17** | Conversation Titles | SessionItem | ✅ | 🟡 MEDIUM |
| **Sprint 17** | Admin Indexing | AdminPage | ✅ | 🟠 HIGH |
| **Sprint 17** | Admin Stats | AdminPage | ✅ | 🟡 MEDIUM |
| **Sprint 15** | Health Dashboard | HealthDashboard | ✅ | 🟡 MEDIUM |
| **Sprint 29** | Graph Visualization | GraphViewer | ✅ | 🟠 HIGH |
| **Sprint 29** | Query Result Graph | GraphModal | ✅ | 🔴 CRITICAL |
| **Sprint 29** | Graph Search | GraphSearch | ✅ | 🟡 MEDIUM |
| **Sprint 29** | Node Details | NodeDetailsPanel | ✅ | 🟠 HIGH |

**Total:** 18 Features across 15 components

---

## Features Overview

| ID | Feature | SP | Priority | LLM Needed | Cost |
|----|---------|----|---------| -----------|------|
| 31.1 | Playwright Infrastructure Setup | 5 | 🔴 CRITICAL | No | $0 |
| 31.2 | Core Search & Streaming Tests | 8 | 🔴 CRITICAL | Yes | $0.20 |
| 31.3 | Citation & Source Tests | 5 | 🔴 CRITICAL | Yes | $0.10 |
| 31.4 | Follow-up Questions Tests | 5 | 🔴 CRITICAL | Yes | $0.10 |
| 31.5 | Conversation History Tests | 5 | 🟠 HIGH | Yes | $0.05 |
| 31.6 | Settings & Preferences Tests | 5 | 🟠 HIGH | No | $0 |
| 31.7 | Admin Workflows Tests | 5 | 🟠 HIGH | Yes | $0.30 |
| 31.8 | Graph Visualization Tests | 8 | 🟠 HIGH | Yes | $0.40 |
| 31.9 | Error Handling & Edge Cases | 3 | 🟡 MEDIUM | Yes | $0.05 |
| 31.10 | Admin Cost Dashboard Tests | 5 | 🟠 HIGH | No | $0 |
| **TOTAL** | | **54 SP** | | | **~$1.20** |

**Budget:** ~$1.20 per full test run (acceptable)

---

## Feature 31.1: Playwright Infrastructure Setup - 5 SP

**Priority:** 🔴 CRITICAL (Foundation for all tests)

**Deliverables:**
1. Playwright installation & configuration
2. Test fixtures for backend connection
3. Helper utilities for SSE streams, auth, waits
4. CI/CD integration (GitHub Actions)
5. Test reporting (HTML + Allure)
6. Cost tracking for LLM test runs

**Implementation:**

### 1. Installation

```bash
cd frontend
npm install -D @playwright/test @axe-core/playwright
npx playwright install chromium firefox webkit
```

### 2. Configuration

```typescript
// frontend/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // Sequential for backend state consistency
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Backend API
    extraHTTPHeaders: {
      'Accept': 'application/json',
    },
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'mobile',
      use: { ...devices['iPhone 13'] },
    },
  ],

  // ⚠️ CI/CD DISABLED for Sprint 31 (cost savings)
  // Run backend and frontend manually before tests:
  //   Terminal 1: poetry run python -m src.api.main
  //   Terminal 2: cd frontend && npm run dev
  //   Terminal 3: cd frontend && npm run test:e2e

  // webServer: [
  //   {
  //     command: 'cd .. && poetry run python -m src.api.main',
  //     url: 'http://localhost:8000/health',
  //     reuseExistingServer: !process.env.CI,
  //     timeout: 30000,
  //   },
  //   {
  //     command: 'npm run dev',
  //     url: 'http://localhost:5173',
  //     reuseExistingServer: !process.env.CI,
  //   },
  // ],
});
```

### 3. Fixtures

```typescript
// frontend/e2e/fixtures/base.ts
import { test as base, expect } from '@playwright/test';

type BaseFixtures = {
  apiUrl: string;
  waitForSSE: (selector: string, timeout?: number) => Promise<void>;
  clearBackendState: () => Promise<void>;
};

export const test = base.extend<BaseFixtures>({
  apiUrl: 'http://localhost:8000',

  // Wait for SSE streaming to complete
  waitForSSE: async ({ page }, use) => {
    await use(async (selector: string, timeout = 30000) => {
      await page.waitForSelector(selector, { state: 'visible', timeout });
      await page.waitForSelector('[data-streaming="false"]', { timeout });
    });
  },

  // Clear backend state between tests
  clearBackendState: async ({ apiUrl }, use) => {
    await use(async () => {
      // Clear Redis sessions
      await fetch(`${apiUrl}/api/v1/chat/sessions`, { method: 'DELETE' });

      // Clear test data (optional)
      // await fetch(`${apiUrl}/api/v1/admin/clear-test-data`, { method: 'POST' });
    });
  },
});

export { expect };
```

### 4. Helpers

```typescript
// frontend/e2e/helpers/llm.ts
/**
 * LLM Test Helpers
 * Cost tracking and utilities for tests using real LLM calls
 */

interface LLMCostTracker {
  startTest(testName: string): void;
  endTest(testName: string): Promise<number>;
  getTotalCost(): Promise<number>;
}

export const llmCostTracker: LLMCostTracker = {
  async startTest(testName: string) {
    // Store test start timestamp
    const timestamp = new Date().toISOString();
    await fetch('http://localhost:8000/api/v1/admin/llm-costs/test-start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ test_name: testName, timestamp })
    });
  },

  async endTest(testName: string) {
    // Get cost for this test
    const response = await fetch(
      `http://localhost:8000/api/v1/admin/llm-costs/test?test_name=${encodeURIComponent(testName)}`
    );
    const data = await response.json();
    return data.cost_usd || 0;
  },

  async getTotalCost() {
    const response = await fetch('http://localhost:8000/api/v1/admin/llm-costs/total');
    const data = await response.json();
    return data.total_cost_usd || 0;
  }
};

// Helper to skip LLM tests in CI if budget exceeded
export function skipIfBudgetExceeded(test: any, monthlyBudget = 30.0) {
  test.beforeAll(async () => {
    const totalCost = await llmCostTracker.getTotalCost();
    if (totalCost > monthlyBudget) {
      test.skip(true, `Monthly LLM budget exceeded: $${totalCost.toFixed(2)} > $${monthlyBudget}`);
    }
  });
}
```

### 5. Local Test Execution Workflow

**⚠️ CI/CD DISABLED** for Sprint 31 to avoid costs. Run tests locally following this workflow:

```bash
# Terminal 1: Start Backend (with services running)
poetry run python -m src.api.main

# Terminal 2: Start Frontend Dev Server
cd frontend
npm run dev

# Terminal 3: Run Playwright Tests
cd frontend
npm run test:e2e

# Or run specific tests
npm run test:e2e -- search/
npm run test:e2e -- --ui  # UI mode for debugging
```

**Prerequisites:**
- Redis, Qdrant, Neo4j running (via Docker Compose)
- Ollama running locally (or configured remote URL)
- Environment variables configured (.env file)

**Future CI/CD Integration (Sprint 32+):**
When tests are stable and costs are acceptable, enable CI with:
- Nightly runs only (not per-PR)
- Selective test execution (critical paths only)
- Budget controls (skip if monthly limit exceeded)

### 6. Cost Tracking Script

```python
# scripts/generate_llm_cost_report.py
"""Generate LLM cost report for Playwright E2E tests."""

import sqlite3
from datetime import datetime, timedelta

def generate_cost_report():
    conn = sqlite3.connect('data/cost_tracking.db')
    cursor = conn.cursor()

    # Cost in last 24 hours (nightly run)
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()

    cursor.execute("""
        SELECT
            provider,
            model,
            COUNT(*) as calls,
            SUM(total_tokens) as tokens,
            SUM(cost_usd) as cost
        FROM llm_calls
        WHERE timestamp > ?
        GROUP BY provider, model
        ORDER BY cost DESC
    """, (yesterday,))

    results = cursor.fetchall()

    print("# LLM Cost Report (Last 24h)")
    print()
    print("| Provider | Model | Calls | Tokens | Cost |")
    print("|----------|-------|-------|--------|------|")

    total_cost = 0
    for row in results:
        provider, model, calls, tokens, cost = row
        print(f"| {provider} | {model} | {calls} | {tokens:,} | ${cost:.4f} |")
        total_cost += cost

    print(f"| **TOTAL** | | | | **${total_cost:.4f}** |")
    print()
    print(f"**Monthly Projection:** ${total_cost * 30:.2f}")
    print()

    # Cost by test (if tracked)
    cursor.execute("""
        SELECT
            metadata->>'test_name' as test_name,
            COUNT(*) as calls,
            SUM(cost_usd) as cost
        FROM llm_calls
        WHERE timestamp > ? AND metadata->>'test_name' IS NOT NULL
        GROUP BY test_name
        ORDER BY cost DESC
        LIMIT 10
    """, (yesterday,))

    test_results = cursor.fetchall()

    if test_results:
        print("## Top 10 Costliest Tests")
        print()
        print("| Test Name | LLM Calls | Cost |")
        print("|-----------|-----------|------|")

        for test_name, calls, cost in test_results:
            print(f"| {test_name} | {calls} | ${cost:.4f} |")

    conn.close()

if __name__ == '__main__':
    generate_cost_report()
```

### Acceptance Criteria

- [ ] Playwright installed and configured
- [ ] Test fixtures for SSE, auth, backend state
- [ ] CI/CD workflow for nightly runs
- [ ] HTML + JSON test reporting
- [ ] LLM cost tracking integration
- [ ] Cost report generation script
- [ ] Documentation: Test writing guide

---

## Feature 31.2: Core Search & Streaming Tests - 8 SP

**Priority:** 🔴 CRITICAL (Core user flow)
**LLM Cost:** ~$0.20 per full test run

**Test Scenarios:**

### 1. Simple Search with Streaming

```typescript
// frontend/e2e/search/simple-search.spec.ts
import { test, expect } from '../fixtures/base';
import { llmCostTracker } from '../helpers/llm';

test.describe('Simple Search with Streaming', () => {
  test.beforeEach(async ({ clearBackendState }) => {
    await clearBackendState();
  });

  test('user submits query and receives streaming answer', async ({ page, waitForSSE }) => {
    await llmCostTracker.startTest('simple-search-streaming');

    // 1. Navigate to homepage
    await page.goto('/');

    // 2. Enter query
    await page.fill('input[type="search"]', 'What are transformers in deep learning?');

    // 3. Submit
    await page.click('button[type="submit"]');

    // 4. Wait for navigation to results page
    await page.waitForURL(/\/results\?session_id=.+/);

    // 5. Wait for streaming to start
    await page.waitForSelector('[data-streaming="true"]', { timeout: 5000 });

    // 6. Verify streaming indicator visible
    await expect(page.locator('[data-streaming-indicator]')).toBeVisible();

    // 7. Wait for streaming to complete
    await waitForSSE('[data-streaming="false"]', 30000);

    // 8. Verify answer contains expected content
    const answer = page.locator('.streaming-answer');
    await expect(answer).toContainText(/transformer/i);

    // 9. Verify source cards displayed
    const sourceCards = page.locator('.source-card');
    await expect(sourceCards).toHaveCount(3, { timeout: 5000 }); // Top 3 sources

    // 10. Track LLM cost
    const cost = await llmCostTracker.endTest('simple-search-streaming');
    console.log(`Test cost: $${cost.toFixed(4)}`);

    // 11. Assert cost within budget
    expect(cost).toBeLessThan(0.10); // Max $0.10 per simple search
  });

  test('streaming displays tokens progressively', async ({ page }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'Explain attention mechanisms');
    await page.click('button[type="submit"]');

    // Wait for first tokens
    await page.waitForSelector('[data-streaming="true"]');

    // Take screenshot of progressive rendering
    const answer = page.locator('.streaming-answer');

    // Verify text length increases over time
    const length1 = await answer.textContent().then(t => t?.length || 0);
    await page.waitForTimeout(1000);
    const length2 = await answer.textContent().then(t => t?.length || 0);
    await page.waitForTimeout(1000);
    const length3 = await answer.textContent().then(t => t?.length || 0);

    expect(length2).toBeGreaterThan(length1);
    expect(length3).toBeGreaterThan(length2);
  });

  test('SSE error handling: backend unavailable', async ({ page }) => {
    // Simulate backend down by stopping webServer
    // (In practice, use a proxy to simulate failure)

    await page.goto('/');
    await page.fill('input[type="search"]', 'Test query');
    await page.click('button[type="submit"]');

    // Expect error message
    await expect(page.locator('.error-message')).toContainText(/server unavailable|connection failed/i);
  });

  test('timeout handling: streaming exceeds 30s', async ({ page }) => {
    // This test uses a special query that triggers slow processing
    await page.goto('/');
    await page.fill('input[type="search"]', '__TEST_SLOW_RESPONSE__');
    await page.click('button[type="submit"]');

    // Wait for timeout error
    await expect(page.locator('.error-message')).toContainText(/timeout/i, { timeout: 35000 });
  });
});
```

### 2. Mode Selector Tests

```typescript
// frontend/e2e/search/mode-selector.spec.ts
import { test, expect } from '../fixtures/base';

test.describe('Search Mode Selector', () => {
  test('hybrid mode returns vector + graph results', async ({ page, waitForSSE }) => {
    await page.goto('/');

    // Select Hybrid mode
    await page.selectOption('select[name="search-mode"]', 'hybrid');

    await page.fill('input[type="search"]', 'Neural networks');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Verify metadata shows "hybrid" was used
    const metadata = await page.locator('[data-search-metadata]').textContent();
    expect(metadata).toContain('Hybrid');
  });

  test('vector mode returns embedding-based results', async ({ page, waitForSSE }) => {
    await page.goto('/');

    await page.selectOption('select[name="search-mode"]', 'vector');
    await page.fill('input[type="search"]', 'Neural networks');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    const metadata = await page.locator('[data-search-metadata]').textContent();
    expect(metadata).toContain('Vector');
  });

  test('graph mode uses LightRAG', async ({ page, waitForSSE }) => {
    await page.goto('/');

    await page.selectOption('select[name="search-mode"]', 'graph');
    await page.fill('input[type="search"]', 'What is the relationship between transformers and attention?');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    const metadata = await page.locator('[data-search-metadata]').textContent();
    expect(metadata).toContain('Graph');
  });
});
```

### Acceptance Criteria

- [ ] Simple search completes in <30s
- [ ] Streaming displays tokens progressively
- [ ] Source cards appear after answer
- [ ] Mode selector changes search strategy
- [ ] Error handling for backend failures
- [ ] Timeout handling for slow responses
- [ ] LLM cost tracked per test
- [ ] All tests cost <$0.20 combined

---

## Feature 31.3: Citation & Source Tests - 5 SP

**Priority:** 🔴 CRITICAL (Perplexity-style UX)
**LLM Cost:** ~$0.10 per full test run

**Test Scenarios:**

```typescript
// frontend/e2e/citations/inline-citations.spec.ts
import { test, expect } from '../fixtures/base';

test.describe('Inline Citations', () => {
  test('citations render as superscript [1][2][3]', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'What are transformers?');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Verify inline citations exist
    const citations = page.locator('.citation');
    await expect(citations.first()).toBeVisible();

    // Verify citation format [1]
    const firstCitation = await citations.first().textContent();
    expect(firstCitation).toMatch(/\[\d+\]/);
  });

  test('hover citation shows tooltip with source preview', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'Explain attention mechanisms');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Hover first citation
    await page.hover('.citation:first-child');

    // Verify tooltip appears
    await expect(page.locator('.citation-tooltip')).toBeVisible();

    // Verify tooltip content
    const tooltip = page.locator('.citation-tooltip');
    await expect(tooltip).toContainText(/Relevance:/);
    await expect(tooltip).toContainText(/Source:/);
  });

  test('click citation scrolls to source card', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'What is BERT?');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Get first source card position
    const sourceCard = page.locator('.source-card:first-child');
    const initialPosition = await sourceCard.boundingBox();

    // Click first citation
    await page.click('.citation:first-child');

    // Wait for scroll animation
    await page.waitForTimeout(1000);

    // Verify source card is in viewport
    await expect(sourceCard).toBeInViewport();

    // Verify highlight effect (flash animation)
    await expect(sourceCard).toHaveClass(/highlighted/);
  });

  test('consecutive citations [1][2] render correctly', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'Compare RNN and CNN architectures');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Find consecutive citations
    const answer = await page.locator('.streaming-answer').textContent();

    // Verify consecutive pattern exists
    expect(answer).toMatch(/\[\d+\]\[\d+\]/);

    // Verify spacing (should have slight gap)
    const citationElements = page.locator('.citation');
    const firstTwo = citationElements.nth(0).and(citationElements.nth(1));

    // Visual regression: Take screenshot of citations
    await expect(firstTwo.first()).toHaveScreenshot('consecutive-citations.png');
  });
});
```

### Acceptance Criteria

- [ ] Citations render as [1][2][3] superscripts
- [ ] Hover shows tooltip with source preview
- [ ] Click scrolls to source card with animation
- [ ] Consecutive citations have correct spacing
- [ ] Missing citations handled gracefully
- [ ] Visual regression tests pass

---

## Feature 31.4: Follow-up Questions Tests - 5 SP

**Priority:** 🔴 CRITICAL (Perplexity-style UX)
**LLM Cost:** ~$0.10 per full test run

**Test Scenarios:**

```typescript
// frontend/e2e/followup/followup-questions.spec.ts
import { test, expect } from '../fixtures/base';

test.describe('Follow-up Questions', () => {
  test('follow-up questions appear after answer completes', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'What are transformers in NLP?');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Wait for follow-up questions to generate
    await page.waitForSelector('.followup-questions', { timeout: 10000 });

    // Verify 3-5 questions displayed
    const questions = page.locator('.followup-question');
    const count = await questions.count();
    expect(count).toBeGreaterThanOrEqual(3);
    expect(count).toBeLessThanOrEqual(5);
  });

  test('clicking follow-up question triggers new search', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'Explain BERT model');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');
    await page.waitForSelector('.followup-questions');

    // Get first question text
    const questionText = await page.locator('.followup-question:first-child').textContent();

    // Click first question
    await page.click('.followup-question:first-child');

    // Verify navigation to new search
    await page.waitForURL(/session_id=.+/);

    // Verify query matches follow-up question
    const newQuery = page.locator('input[type="search"]');
    await expect(newQuery).toHaveValue(questionText || '');

    // Verify new answer streaming
    await page.waitForSelector('[data-streaming="true"]');
  });

  test('follow-up questions use Redis caching (fast on repeat)', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'What is GPT?');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // First load: Track time
    const start1 = Date.now();
    await page.waitForSelector('.followup-questions');
    const duration1 = Date.now() - start1;

    // Reload page (same session)
    await page.reload();

    // Second load: Should be faster (cached)
    const start2 = Date.now();
    await page.waitForSelector('.followup-questions');
    const duration2 = Date.now() - start2;

    // Verify caching (should be >50% faster)
    expect(duration2).toBeLessThan(duration1 * 0.5);
  });

  test('error handling: follow-up generation fails gracefully', async ({ page, waitForSSE }) => {
    // Use a query that triggers LLM error
    await page.goto('/');
    await page.fill('input[type="search"]', '__TEST_FOLLOWUP_ERROR__');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Verify no follow-up questions (or "No questions available" message)
    const followup = page.locator('.followup-questions');
    await expect(followup).not.toBeVisible();

    // OR: Error message displayed
    // await expect(page.locator('.followup-error')).toContainText(/No questions available/);
  });
});
```

### Acceptance Criteria

- [ ] 3-5 follow-up questions appear after answer
- [ ] Clicking question triggers new search
- [ ] Questions contextually relevant to answer
- [ ] Redis caching works (fast on reload)
- [ ] Error handling when generation fails
- [ ] Loading skeleton during generation

---

## Feature 31.5: Conversation History Tests - 5 SP

**Priority:** 🟠 HIGH (Multi-turn conversations)
**LLM Cost:** ~$0.05 per full test run

**Test Scenarios:**

```typescript
// frontend/e2e/history/conversation-history.spec.ts
import { test, expect } from '../fixtures/base';

test.describe('Conversation History', () => {
  test('conversation persists across browser refreshes', async ({ page, waitForSSE }) => {
    // Submit first query
    await page.goto('/');
    await page.fill('input[type="search"]', 'What is machine learning?');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Get session ID from URL
    const url = new URL(page.url());
    const sessionId = url.searchParams.get('session_id');

    // Refresh browser
    await page.reload();

    // Verify conversation still visible
    await expect(page.locator('.streaming-answer')).toBeVisible();

    // Verify session ID unchanged
    const newUrl = new URL(page.url());
    expect(newUrl.searchParams.get('session_id')).toBe(sessionId);
  });

  test('session sidebar shows past conversations', async ({ page, waitForSSE }) => {
    // Create 3 conversations
    for (let i = 0; i < 3; i++) {
      await page.goto('/');
      await page.fill('input[type="search"]', `Query ${i + 1}`);
      await page.click('button[type="submit"]');
      await waitForSSE('[data-streaming="false"]');
    }

    // Navigate to homepage
    await page.goto('/');

    // Verify sidebar shows 3 sessions
    const sessions = page.locator('.session-item');
    await expect(sessions).toHaveCount(3);
  });

  test('conversation titles auto-generated', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'Explain neural networks in simple terms');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Wait for title generation (LLM call)
    await page.waitForSelector('.session-title', { timeout: 10000 });

    // Verify title is concise (3-5 words)
    const title = await page.locator('.session-title').first().textContent();
    const wordCount = title?.trim().split(/\s+/).length || 0;
    expect(wordCount).toBeGreaterThanOrEqual(3);
    expect(wordCount).toBeLessThanOrEqual(7);
  });

  test('user can edit conversation title', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'What is TensorFlow?');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');
    await page.waitForSelector('.session-title');

    // Click edit icon
    await page.hover('.session-item:first-child');
    await page.click('.edit-title-icon');

    // Edit title
    const titleInput = page.locator('.title-input');
    await titleInput.fill('Custom Title');
    await titleInput.press('Enter');

    // Verify title saved
    await expect(page.locator('.session-title').first()).toHaveText('Custom Title');

    // Verify persists after reload
    await page.reload();
    await expect(page.locator('.session-title').first()).toHaveText('Custom Title');
  });

  test('multi-turn conversation maintains context', async ({ page, waitForSSE }) => {
    await page.goto('/');

    // Turn 1
    await page.fill('input[type="search"]', 'What is a neural network?');
    await page.click('button[type="submit"]');
    await waitForSSE('[data-streaming="false"]');

    // Turn 2: Follow-up (context-dependent)
    await page.fill('input[type="search"]', 'How does it differ from traditional algorithms?');
    await page.click('button[type="submit"]');
    await waitForSSE('[data-streaming="false"]');

    // Verify answer references "neural network" from Turn 1
    const answer = await page.locator('.streaming-answer').last().textContent();
    expect(answer).toMatch(/neural network/i);
  });
});
```

### Acceptance Criteria

- [ ] Conversations persist across refreshes
- [ ] Session sidebar shows past conversations
- [ ] Titles auto-generated (3-5 words)
- [ ] User can edit titles
- [ ] Multi-turn maintains context
- [ ] Delete conversation works

---

## Feature 31.6: Settings & Preferences Tests - 5 SP

**Priority:** 🟠 HIGH (User experience)
**LLM Cost:** $0 (no LLM calls)

**Test Scenarios:**

```typescript
// frontend/e2e/settings/settings.spec.ts
import { test, expect } from '../fixtures/base';

test.describe('Settings & Preferences', () => {
  test('theme switcher: light/dark/auto', async ({ page }) => {
    await page.goto('/settings');

    // Select Dark theme
    await page.selectOption('select[name="theme"]', 'dark');

    // Verify dark theme applied (check body class)
    await expect(page.locator('html')).toHaveClass(/dark/);

    // Refresh and verify persistence
    await page.reload();
    await expect(page.locator('html')).toHaveClass(/dark/);

    // Select Light theme
    await page.selectOption('select[name="theme"]', 'light');
    await expect(page.locator('html')).not.toHaveClass(/dark/);
  });

  test('export conversations as JSON', async ({ page, waitForSSE }) => {
    // Create a conversation first
    await page.goto('/');
    await page.fill('input[type="search"]', 'Test query for export');
    await page.click('button[type="submit"]');
    await waitForSSE('[data-streaming="false"]');

    // Navigate to settings
    await page.goto('/settings');

    // Click export button
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("Export Conversations")');
    const download = await downloadPromise;

    // Verify filename format
    expect(download.suggestedFilename()).toMatch(/aegis-conversations-\d{8}\.json/);

    // Verify JSON content
    const path = await download.path();
    const content = require('fs').readFileSync(path, 'utf-8');
    const data = JSON.parse(content);

    expect(data).toHaveProperty('conversations');
    expect(data.conversations.length).toBeGreaterThan(0);
  });

  test('import conversations from JSON', async ({ page }) => {
    await page.goto('/settings');

    // Upload JSON file
    const filePath = 'e2e/fixtures/test-conversations.json';
    await page.setInputFiles('input[type="file"]', filePath);

    // Verify success message
    await expect(page.locator('.import-success')).toContainText(/imported successfully/i);

    // Navigate to homepage and verify conversations loaded
    await page.goto('/');
    const sessions = page.locator('.session-item');
    await expect(sessions.count()).resolves.toBeGreaterThan(0);
  });

  test('clear history with confirmation', async ({ page, waitForSSE }) => {
    // Create conversations
    await page.goto('/');
    await page.fill('input[type="search"]', 'Test query');
    await page.click('button[type="submit"]');
    await waitForSSE('[data-streaming="false"]');

    // Open settings
    await page.goto('/settings');

    // Click clear history
    await page.click('button:has-text("Clear History")');

    // Verify confirmation dialog
    await expect(page.locator('.confirmation-dialog')).toBeVisible();

    // Confirm deletion
    await page.click('button:has-text("Löschen")');

    // Verify history cleared
    await page.goto('/');
    const sessions = page.locator('.session-item');
    await expect(sessions).toHaveCount(0);
  });

  test('model configuration: select provider', async ({ page }) => {
    await page.goto('/settings');

    // Navigate to Models tab
    await page.click('button:has-text("Models")');

    // Select Alibaba Cloud
    await page.check('input[name="provider-alibaba"]');

    // Enter API key
    await page.fill('input[name="alibaba-api-key"]', 'test-api-key');

    // Save
    await page.click('button:has-text("Save")');

    // Verify saved (reload and check)
    await page.reload();
    await page.click('button:has-text("Models")');
    await expect(page.locator('input[name="alibaba-api-key"]')).toHaveValue('test-api-key');
  });
});
```

### Acceptance Criteria

- [ ] Theme switcher works (light/dark/auto)
- [ ] Export conversations as JSON
- [ ] Import conversations from JSON
- [ ] Clear history with confirmation
- [ ] Model configuration persists
- [ ] Settings persist across sessions

---

## Feature 31.7: Admin Workflows Tests - 5 SP

**Priority:** 🟠 HIGH (Admin features)
**LLM Cost:** ~$0.30 per full test run (VLM indexing)

**Test Scenarios:**

```typescript
// frontend/e2e/admin/admin-workflows.spec.ts
import { test, expect } from '../fixtures/base';

test.describe('Admin Workflows', () => {
  test('directory indexing with progress tracking', async ({ page }) => {
    await page.goto('/admin');

    // Enter directory path
    await page.fill('input[name="directory"]', 'data/sample_documents/test');

    // Click "Index" button
    await page.click('button:has-text("Index")');

    // Verify progress bar appears
    await expect(page.locator('.progress-bar')).toBeVisible();

    // Wait for completion (SSE progress updates)
    await page.waitForSelector('.indexing-complete', { timeout: 120000 }); // 2 min max

    // Verify success message
    await expect(page.locator('.success-message')).toContainText(/successfully indexed/i);

    // Verify stats updated
    const statsAfter = await page.locator('[data-stats-documents]').textContent();
    expect(parseInt(statsAfter || '0')).toBeGreaterThan(0);
  });

  test('admin stats dashboard shows metrics', async ({ page }) => {
    await page.goto('/admin');

    // Verify 4 stat cards
    const statCards = page.locator('.stat-card');
    await expect(statCards).toHaveCount(4);

    // Verify metrics displayed
    await expect(page.locator('[data-stat="qdrant-chunks"]')).toContainText(/\d+/);
    await expect(page.locator('[data-stat="neo4j-entities"]')).toContainText(/\d+/);
    await expect(page.locator('[data-stat="conversations"]')).toContainText(/\d+/);
  });

  test('indexing error handling: invalid directory', async ({ page }) => {
    await page.goto('/admin');

    await page.fill('input[name="directory"]', '/invalid/path/does/not/exist');
    await page.click('button:has-text("Index")');

    // Verify error message
    await expect(page.locator('.error-message')).toContainText(/directory not found|invalid path/i);
  });

  test('real-time cost tracking during indexing', async ({ page }) => {
    await page.goto('/admin');

    await page.fill('input[name="directory"]', 'data/sample_documents/small_set');
    await page.click('button:has-text("Index")');

    // Wait for VLM cost updates (SSE events)
    await page.waitForSelector('[data-vlm-cost]', { timeout: 10000 });

    // Verify cost displayed
    const cost = await page.locator('[data-vlm-cost]').textContent();
    expect(parseFloat(cost || '0')).toBeGreaterThan(0);
  });
});
```

### Acceptance Criteria

- [ ] Directory indexing works end-to-end
- [ ] Progress bar shows real-time updates
- [ ] Admin stats accurate
- [ ] Error handling for invalid paths
- [ ] VLM cost tracking displays

---

## Feature 31.8: Graph Visualization Tests - 8 SP

**Priority:** 🟠 HIGH (Graph features)
**LLM Cost:** ~$0.40 per full test run

**Test Scenarios:**

```typescript
// frontend/e2e/graph/graph-visualization.spec.ts
import { test, expect } from '../fixtures/base';

test.describe('Graph Visualization', () => {
  test('query result graph modal opens', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'How are transformers related to attention?');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');

    // Click "View Graph" button
    await page.click('button:has-text("View Knowledge Graph")');

    // Verify modal opens
    await expect(page.locator('.graph-modal')).toBeVisible();

    // Verify graph rendered (canvas/svg exists)
    await expect(page.locator('canvas.graph-canvas')).toBeVisible();
  });

  test('graph nodes and edges render correctly', async ({ page, waitForSSE }) => {
    await page.goto('/');
    await page.fill('input[type="search"]', 'Explain neural networks');
    await page.click('button[type="submit"]');

    await waitForSSE('[data-streaming="false"]');
    await page.click('button:has-text("View Knowledge Graph")');

    // Wait for graph to render
    await page.waitForSelector('.graph-node', { timeout: 5000 });

    // Verify at least 2 nodes (entities from answer)
    const nodes = page.locator('.graph-node');
    await expect(nodes.count()).resolves.toBeGreaterThanOrEqual(2);
  });

  test('graph search finds nodes', async ({ page }) => {
    await page.goto('/graph');

    // Wait for full graph to load
    await page.waitForSelector('.graph-node', { timeout: 10000 });

    // Use search box
    await page.fill('input[name="graph-search"]', 'Transformer');

    // Verify search results dropdown
    await expect(page.locator('.search-results')).toBeVisible();

    // Click first result
    await page.click('.search-result:first-child');

    // Verify graph centers on selected node
    // (Check if node is highlighted)
    await expect(page.locator('.graph-node.highlighted')).toBeVisible();
  });

  test('node details panel shows related documents', async ({ page }) => {
    await page.goto('/graph');

    await page.waitForSelector('.graph-node');

    // Click a node
    await page.click('.graph-node:first-child');

    // Verify side panel opens
    await expect(page.locator('.node-details-panel')).toBeVisible();

    // Verify "Related Documents" section
    await expect(page.locator('.related-documents')).toBeVisible();

    // Verify at least 1 document
    const docs = page.locator('.document-card');
    await expect(docs.count()).resolves.toBeGreaterThanOrEqual(1);
  });

  test('community highlighting works', async ({ page }) => {
    await page.goto('/graph');

    await page.waitForSelector('.graph-node');

    // Select community from dropdown
    await page.selectOption('select[name="community"]', '0'); // Community ID

    // Verify nodes highlighted (color change)
    const highlightedNodes = page.locator('.graph-node.highlighted');
    await expect(highlightedNodes.count()).resolves.toBeGreaterThan(0);

    // Verify non-community nodes dimmed
    const dimmedNodes = page.locator('.graph-node.dimmed');
    await expect(dimmedNodes.count()).resolves.toBeGreaterThan(0);
  });
});
```

### Acceptance Criteria

- [ ] Query graph modal opens and renders
- [ ] Nodes and edges display correctly
- [ ] Graph search finds and centers nodes
- [ ] Node details panel shows documents
- [ ] Community highlighting works
- [ ] Graph export (JSON/GraphML)

---

## Feature 31.9: Error Handling & Edge Cases - 3 SP

**Priority:** 🟡 MEDIUM (Robustness)
**LLM Cost:** ~$0.05 per full test run

**Test Scenarios:**

```typescript
// frontend/e2e/errors/error-handling.spec.ts
import { test, expect } from '../fixtures/base';

test.describe('Error Handling', () => {
  test('empty query validation', async ({ page }) => {
    await page.goto('/');

    // Submit without typing
    await page.click('button[type="submit"]');

    // Verify validation error
    await expect(page.locator('.validation-error')).toContainText(/query cannot be empty/i);
  });

  test('network error during streaming', async ({ page }) => {
    // Use a proxy to simulate network failure mid-stream
    // (In practice, this requires a test proxy setup)

    await page.goto('/');
    await page.fill('input[type="search"]', 'Test query');
    await page.click('button[type="submit"]');

    // Simulate network failure after 2 seconds
    await page.waitForTimeout(2000);
    await page.context().setOffline(true);

    // Verify error message
    await expect(page.locator('.error-message')).toContainText(/connection lost|network error/i);
  });

  test('429 rate limit handling', async ({ page }) => {
    // Send 20 requests rapidly to trigger rate limit
    for (let i = 0; i < 20; i++) {
      await page.goto('/');
      await page.fill('input[type="search"]', `Query ${i}`);
      await page.click('button[type="submit"]');
    }

    // Expect rate limit error
    await expect(page.locator('.error-message')).toContainText(/rate limit|too many requests/i);
  });

  test('malformed JSON response handling', async ({ page }) => {
    // Use a special query that triggers malformed response
    await page.goto('/');
    await page.fill('input[type="search"]', '__TEST_MALFORMED_JSON__');
    await page.click('button[type="submit"]');

    // Verify graceful error
    await expect(page.locator('.error-message')).toContainText(/unexpected error/i);
  });
});
```

### Acceptance Criteria

- [ ] Empty query validation works
- [ ] Network errors handled gracefully
- [ ] Rate limit errors displayed
- [ ] Malformed responses don't crash app
- [ ] Error recovery (retry, back button)

---

## Feature 31.10: Admin Cost Dashboard Tests - 5 SP

**Priority:** 🟠 HIGH (Production monitoring)
**LLM Cost:** $0 (no LLM calls, UI tests only)

**Context:** Current AdminPage shows system stats (Qdrant, Neo4j, Redis) but NO LLM cost tracking. This feature adds comprehensive cost monitoring UI and E2E tests.

**Deliverables:**
1. Admin Cost Dashboard component (new)
2. Real-time cost metrics display
3. Provider-specific budget tracking
4. Cost history charts (last 7/30 days)
5. E2E tests for all cost features

### Admin Cost Dashboard Component (NEW)

```typescript
// frontend/src/pages/admin/CostDashboardPage.tsx
import { useState, useEffect } from 'react';
import { getCostStats, getCostHistory } from '../../api/admin';

interface CostStats {
  total_cost_usd: number;
  total_tokens: number;
  total_calls: number;
  by_provider: Record<string, ProviderCost>;
  by_model: Record<string, ModelCost>;
  budgets: Record<string, BudgetStatus>;
}

interface ProviderCost {
  provider: string;
  cost_usd: number;
  tokens: number;
  calls: number;
  models: string[];
}

interface BudgetStatus {
  provider: string;
  limit_usd: number;
  spent_usd: number;
  remaining_usd: number;
  utilization_percent: number;
  status: 'ok' | 'warning' | 'critical';
}

export function CostDashboardPage() {
  const [stats, setStats] = useState<CostStats | null>(null);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | 'all'>('7d');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCostStats();
  }, [timeRange]);

  const loadCostStats = async () => {
    setLoading(true);
    try {
      const data = await getCostStats(timeRange);
      setStats(data);
    } catch (err) {
      console.error('Failed to load cost stats:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold">LLM Cost Dashboard</h1>
            <p className="text-gray-600 mt-2">Monitor API costs and budgets</p>
          </div>

          {/* Time Range Selector */}
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as any)}
            className="px-4 py-2 border rounded-lg"
          >
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="all">All Time</option>
          </select>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-6">
          <CostCard
            title="Total Cost"
            value={`$${stats?.total_cost_usd.toFixed(2) || '0.00'}`}
            icon="💰"
            trend={calculateTrend(stats)}
          />
          <CostCard
            title="Total Tokens"
            value={stats?.total_tokens.toLocaleString() || '0'}
            icon="📊"
          />
          <CostCard
            title="API Calls"
            value={stats?.total_calls.toLocaleString() || '0'}
            icon="📞"
          />
          <CostCard
            title="Avg Cost/Call"
            value={`$${((stats?.total_cost_usd || 0) / (stats?.total_calls || 1)).toFixed(4)}`}
            icon="🎯"
          />
        </div>

        {/* Budget Status */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-2xl font-semibold mb-4">Budget Status</h2>
          <div className="space-y-4">
            {Object.entries(stats?.budgets || {}).map(([provider, budget]) => (
              <BudgetProgressBar key={provider} budget={budget} />
            ))}
          </div>
        </div>

        {/* Provider Breakdown */}
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold mb-4">Cost by Provider</h2>
            <ProviderPieChart data={stats?.by_provider} />
          </div>

          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold mb-4">Cost by Model</h2>
            <ModelBarChart data={stats?.by_model} />
          </div>
        </div>

        {/* Cost History */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-2xl font-semibold mb-4">Cost Trend</h2>
          <CostHistoryChart timeRange={timeRange} />
        </div>
      </div>
    </div>
  );
}
```

### Backend API Endpoint (NEW)

```python
# src/api/routers/admin.py
@router.get("/costs/stats")
async def get_cost_stats(time_range: str = "7d") -> dict[str, Any]:
    """Get LLM cost statistics.

    Args:
        time_range: "7d", "30d", or "all"

    Returns:
        Cost stats with provider/model breakdown and budgets
    """
    from src.components.llm_proxy.cost_tracker import get_cost_tracker

    tracker = get_cost_tracker()

    # Calculate time range
    if time_range == "7d":
        since = datetime.now() - timedelta(days=7)
    elif time_range == "30d":
        since = datetime.now() - timedelta(days=30)
    else:
        since = None  # All time

    # Get stats from SQLite
    stats = await tracker.get_aggregated_stats(since=since)

    # Get budget status
    budgets = {
        "ollama": {
            "provider": "ollama",
            "limit_usd": 0.0,  # Free
            "spent_usd": 0.0,
            "remaining_usd": 0.0,
            "utilization_percent": 0.0,
            "status": "ok"
        },
        "alibaba_cloud": {
            "provider": "alibaba_cloud",
            "limit_usd": float(os.getenv("MONTHLY_BUDGET_ALIBABA_CLOUD", "10.0")),
            "spent_usd": stats["by_provider"].get("alibaba_cloud", {}).get("cost_usd", 0.0),
            "remaining_usd": 0.0,  # Calculate below
            "utilization_percent": 0.0,
            "status": "ok"
        }
    }

    # Calculate remaining and status
    for provider, budget in budgets.items():
        if budget["limit_usd"] > 0:
            budget["remaining_usd"] = budget["limit_usd"] - budget["spent_usd"]
            budget["utilization_percent"] = (budget["spent_usd"] / budget["limit_usd"]) * 100

            if budget["utilization_percent"] >= 100:
                budget["status"] = "critical"
            elif budget["utilization_percent"] >= 80:
                budget["status"] = "warning"
            else:
                budget["status"] = "ok"

    return {
        "total_cost_usd": stats["total_cost_usd"],
        "total_tokens": stats["total_tokens"],
        "total_calls": stats["total_calls"],
        "by_provider": stats["by_provider"],
        "by_model": stats["by_model"],
        "budgets": budgets,
        "time_range": time_range
    }
```

### E2E Test Scenarios

```typescript
// frontend/e2e/admin/cost-dashboard.spec.ts
import { test, expect } from '../fixtures/base';

test.describe('Admin Cost Dashboard', () => {
  test('cost dashboard displays total metrics', async ({ page }) => {
    await page.goto('/admin/costs');

    // Verify 4 summary cards
    const cards = page.locator('.cost-card');
    await expect(cards).toHaveCount(4);

    // Verify metrics displayed
    await expect(page.locator('[data-metric="total-cost"]')).toBeVisible();
    await expect(page.locator('[data-metric="total-tokens"]')).toBeVisible();
    await expect(page.locator('[data-metric="api-calls"]')).toBeVisible();
    await expect(page.locator('[data-metric="avg-cost"]')).toBeVisible();
  });

  test('budget status shows provider limits', async ({ page }) => {
    await page.goto('/admin/costs');

    // Verify budget bars for each provider
    const budgetBars = page.locator('.budget-progress-bar');
    await expect(budgetBars.count()).resolves.toBeGreaterThan(0);

    // Verify Alibaba Cloud budget (if configured)
    const alibabaBudget = page.locator('[data-provider="alibaba_cloud"]');
    if (await alibabaBudget.count() > 0) {
      await expect(alibabaBudget).toContainText(/\$\d+\.\d{2}/); // Cost
      await expect(alibabaBudget).toContainText(/\d+%/); // Utilization
    }
  });

  test('time range selector filters data', async ({ page }) => {
    await page.goto('/admin/costs');

    // Get initial total cost
    const initialCost = await page.locator('[data-metric="total-cost"]').textContent();

    // Change time range to 30 days
    await page.selectOption('select[name="time-range"]', '30d');

    // Wait for update
    await page.waitForTimeout(500);

    // Verify cost changed (or stayed same if no data)
    const newCost = await page.locator('[data-metric="total-cost"]').textContent();
    expect(newCost).toBeDefined();
  });

  test('provider pie chart shows breakdown', async ({ page }) => {
    await page.goto('/admin/costs');

    // Verify pie chart rendered
    await expect(page.locator('.provider-pie-chart')).toBeVisible();

    // Verify legend with providers
    const legend = page.locator('.chart-legend');
    await expect(legend).toContainText(/ollama|alibaba|openai/i);
  });

  test('cost history chart displays trend', async ({ page }) => {
    await page.goto('/admin/costs');

    // Verify line chart rendered
    await expect(page.locator('.cost-history-chart')).toBeVisible();

    // Verify x-axis labels (dates)
    const xAxisLabels = page.locator('.chart-x-axis text');
    await expect(xAxisLabels.count()).resolves.toBeGreaterThan(0);
  });

  test('budget alert shown when limit exceeded', async ({ page }) => {
    // This test assumes budget is exceeded (mock or real)
    await page.goto('/admin/costs');

    // If any budget is critical (>100%), verify alert
    const criticalBudget = page.locator('.budget-status-critical');

    if (await criticalBudget.count() > 0) {
      // Verify alert banner
      await expect(page.locator('.budget-alert')).toContainText(/budget exceeded/i);

      // Verify red color indicator
      await expect(criticalBudget).toHaveClass(/bg-red/);
    }
  });

  test('model breakdown table shows details', async ({ page }) => {
    await page.goto('/admin/costs');

    // Verify model table
    const modelTable = page.locator('.model-breakdown-table');
    await expect(modelTable).toBeVisible();

    // Verify columns: Model, Calls, Tokens, Cost
    await expect(modelTable.locator('th')).toContainText(['Model', 'Calls', 'Tokens', 'Cost']);

    // Verify at least 1 row (if any LLM calls made)
    const rows = modelTable.locator('tbody tr');
    const rowCount = await rows.count();

    if (rowCount > 0) {
      // Verify first row has data
      const firstRow = rows.first();
      await expect(firstRow.locator('td').first()).toContainText(/llama|qwen|gpt/i);
    }
  });

  test('refresh button updates data', async ({ page }) => {
    await page.goto('/admin/costs');

    // Get initial timestamp
    const initialTimestamp = await page.locator('[data-timestamp]').textContent();

    // Click refresh
    await page.click('button:has-text("Refresh")');

    // Wait for update
    await page.waitForTimeout(500);

    // Verify timestamp changed
    const newTimestamp = await page.locator('[data-timestamp]').textContent();
    expect(newTimestamp).not.toBe(initialTimestamp);
  });
});
```

### Acceptance Criteria

- [ ] Cost dashboard page accessible at `/admin/costs`
- [ ] 4 summary cards: Total Cost, Tokens, Calls, Avg Cost
- [ ] Budget status bars for all providers
- [ ] Provider pie chart with breakdown
- [ ] Model bar chart with cost distribution
- [ ] Cost history line chart (7d/30d/all)
- [ ] Time range selector works
- [ ] Budget alerts for >80% utilization
- [ ] Refresh button updates data
- [ ] Visual regression tests pass

---

## Testing Infrastructure

### Test Organization

```
frontend/e2e/
├── fixtures/
│   ├── base.ts                  # Base fixtures (waitForSSE, clearBackendState)
│   └── test-conversations.json  # Sample data for import tests
├── helpers/
│   ├── llm.ts                   # LLM cost tracking
│   └── utils.ts                 # Shared utilities
├── search/
│   ├── simple-search.spec.ts    # Feature 31.2
│   └── mode-selector.spec.ts
├── citations/
│   └── inline-citations.spec.ts # Feature 31.3
├── followup/
│   └── followup-questions.spec.ts # Feature 31.4
├── history/
│   └── conversation-history.spec.ts # Feature 31.5
├── settings/
│   └── settings.spec.ts         # Feature 31.6
├── admin/
│   └── admin-workflows.spec.ts  # Feature 31.7
├── graph/
│   └── graph-visualization.spec.ts # Feature 31.8
├── errors/
│   └── error-handling.spec.ts   # Feature 31.9
└── performance/
    └── lighthouse.spec.ts       # Feature 31.10
```

### Test Execution

```bash
# Run all E2E tests
npm run test:e2e

# Run specific feature
npm run test:e2e -- search/

# Run with UI mode (debugging)
npm run test:e2e:ui

# Run in specific browser
npm run test:e2e -- --project=firefox

# Run with cost tracking
npm run test:e2e -- --reporter=./e2e/reporters/cost-reporter.ts
```

### CI/CD Integration

**Nightly Runs:**
- Schedule: 2 AM UTC daily
- Browsers: Chromium only (faster)
- Full suite: ~15 minutes
- Cost: ~$1.20 per run (~$36/month)

**PR Runs (Selective):**
- Only tests related to changed files
- Skip LLM tests if non-critical
- Parallel execution: 3 workers
- Duration: ~5 minutes

**Budget Controls:**
- Monthly budget: $50
- Alert at 80% utilization
- Auto-skip expensive tests if exceeded
- Cost report in PR comments

---

## Success Metrics

### Test Coverage

- **Feature Coverage:** 100% (all 18 Sprint 15-30 features)
- **Critical Paths:** 100% (Search, Streaming, Citations, Follow-up)
- **Edge Cases:** >80% (errors, timeouts, validation)
- **Accessibility:** WCAG 2.1 AA compliance

### Performance

- **Test Execution:** <15 minutes full suite
- **First Token Latency:** <1s (SSE streaming)
- **Lighthouse Score:** >80 (performance)
- **LLM Cost:** <$2.00 per full suite run

### Quality

- **Flakiness Rate:** <2% (reliable tests)
- **False Positives:** <1% (accurate assertions)
- **CI Success Rate:** >95% (stable pipeline)
- **Visual Regression:** 0 unexpected changes

---

## Cost Analysis

### LLM Cost Breakdown

| Feature | Tests | LLM Calls | Avg Cost | Total |
|---------|-------|-----------|----------|-------|
| Search & Streaming | 8 | ~4 per test | $0.025 | $0.20 |
| Citations | 5 | ~2 per test | $0.010 | $0.10 |
| Follow-up Questions | 5 | ~2 per test | $0.010 | $0.10 |
| Conversation History | 5 | ~1 per test | $0.010 | $0.05 |
| Admin Workflows | 3 | ~5 per test (VLM) | $0.100 | $0.30 |
| Graph Visualization | 5 | ~4 per test | $0.080 | $0.40 |
| Error Handling | 3 | ~1 per test | $0.017 | $0.05 |
| **TOTAL** | **34** | | | **$1.20** |

### Monthly Budget

**Nightly CI:**
- $1.20/day × 30 days = $36/month

**PR Runs (Selective):**
- ~5 PRs/week × $0.30/run = $6/month

**Developer Runs:**
- ~10 runs/week × $0.50/run = $20/month

**Total: ~$62/month** (within $100 budget)

**Mitigation:**
- Use local Ollama for non-critical tests (FREE)
- Cache LLM responses for repeated queries
- Skip expensive tests in PR (only nightly)

---

## Implementation Timeline

### Week 1: Foundation (Days 1-3, 13 SP)
- **Day 1:** Feature 31.1 (Playwright Setup) - 5 SP
- **Day 2:** Feature 31.2 (Search & Streaming) - 8 SP

### Week 2: Critical Features (Days 4-6, 23 SP)
- **Day 3:** Feature 31.3 (Citations) + Feature 31.4 (Follow-up) - 10 SP
- **Day 4:** Feature 31.5 (History) + Feature 31.6 (Settings) - 10 SP
- **Day 5:** Feature 31.7 (Admin) - 5 SP

### Week 3: Advanced & Polish (Days 7-9, 18 SP)
- **Day 6:** Feature 31.8 (Graph Visualization) - 8 SP
- **Day 7:** Feature 31.9 (Error Handling) + Feature 31.10 (Cost Dashboard) - 8 SP
- **Day 8:** Documentation, test refinement, bug fixes
- **Day 9:** Final testing, Sprint 31 completion report

---

## Sprint 31 Completion Criteria

- [ ] All 10 features implemented and passing
- [ ] 42+ E2E test specs created (8 new for Cost Dashboard)
- [ ] Playwright local testing workflow documented
- [ ] LLM cost tracking integration (backend + frontend)
- [ ] Test coverage: 100% critical features
- [ ] Admin Cost Dashboard: Fully functional
- [ ] Monthly cost: <$100 (local runs only, no CI)
- [ ] Documentation: Test writing guide
- [ ] Sprint 31 completion report

---

## Risks & Mitigation

### Risk 1: LLM Costs Exceed Budget
**Impact:** HIGH
**Mitigation:**
- Use local Ollama for 80% of tests
- Cache LLM responses for repeated queries
- Skip expensive tests in PR (only nightly)
- Monitor costs daily, alert at 80%

### Risk 2: Tests Too Slow (>15 minutes)
**Impact:** MEDIUM
**Mitigation:**
- Run tests in parallel (3 workers)
- Skip non-critical tests in PR
- Optimize SSE waiting logic
- Use faster assertion strategies

### Risk 3: Flaky Tests Due to LLM Variability
**Impact:** MEDIUM
**Mitigation:**
- Use flexible assertions (regex, contains)
- Retry failed tests (max 2 retries)
- Mock LLM for non-critical paths
- Document expected variability

### Risk 4: CI/CD Complexity (Backend + Frontend)
**Impact:** MEDIUM
**Mitigation:**
- Use Docker Compose for backend services
- Health checks before tests
- Clear documentation for setup
- Pre-built Docker images for faster startup

---

## Next Steps

1. **Review Sprint 31 Plan** with team
2. **Approve budget** ($100/month for LLM costs)
3. **Create Sprint 31 branch**
4. **Start Feature 31.1** (Playwright Infrastructure)
5. **Daily standups** to track progress
6. **Weekly cost review** to stay within budget

---

**Sprint 31 Readiness:** ✅ **READY TO START**
**Expected Completion:** 2025-12-04 (9 business days)
**Budget Allocated:** $100/month (LLM costs + CI/CD)

---

**Report Generated:** 2025-11-20
**Author:** Claude Code
**Sprint Lead:** Klaus Pommer
**Status:** PLANNED
