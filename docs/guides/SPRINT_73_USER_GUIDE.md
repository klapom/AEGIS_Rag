# Sprint 73 User Guide: E2E Testing & Test Infrastructure

**Sprint:** 73
**Date:** 2026-01-03
**Audience:** Developers, QA Engineers, DevOps
**Level:** Beginner to Intermediate

---

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Running Tests](#running-tests)
4. [Writing New Tests](#writing-new-tests)
5. [Test Infrastructure](#test-infrastructure)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Introduction

Sprint 73 delivered comprehensive E2E test coverage for the AEGIS RAG frontend, plus enhanced test infrastructure for parallel execution, visual regression, and accessibility testing.

### What You'll Learn

- How to run E2E tests locally
- How to write new E2E tests
- How to use parallel execution for faster testing
- How to perform visual regression testing
- How to check accessibility (WCAG 2.1 AA)
- How to debug failing tests

---

## Quick Start

### Prerequisites

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Install Playwright browsers
npx playwright install --with-deps

# 3. Install accessibility testing (optional)
npm install --save-dev @axe-core/playwright
```

### Run Your First Test

```bash
# Run all E2E tests (sequential, slow)
npm run test:e2e

# Run tests in parallel (recommended, fast)
npm run test:parallel

# Run with UI (visual test runner)
npm run test:e2e:ui
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
npm run test:e2e

# Run specific test file
npx playwright test e2e/tests/chat/chat-features.spec.ts

# Run tests matching pattern
npx playwright test --grep "should search"

# Run in headed mode (see browser)
npm run test:e2e:headed

# Run in debug mode (step through)
npm run test:e2e:debug
```

### Parallel Execution (Recommended)

```bash
# Run all tests in parallel (4 workers)
npm run test:parallel

# Run only Chromium (fastest)
npm run test:parallel:chromium

# Test all browsers (Chromium, Firefox, WebKit)
npm run test:parallel:all-browsers
```

**Performance:**
- Sequential: ~10 minutes
- Parallel: ~2-3 minutes (70% faster!)

### Test Suites

```bash
# Run chat tests only
npm run test:chat

# Run search tests only
npm run test:search

# Run graph visualization tests
npm run test:graph

# Run admin tests only
npm run test:admin

# Run error handling tests
npm run test:errors
```

### Integration Tests (Requires Live Backend)

```bash
# Start services first
docker compose up -d  # Backend, Qdrant, Neo4j, Redis, Ollama

# Then run integration tests
npm run test:integration

# Or specific integration test
npm run test:integration:multi-turn
npm run test:integration:performance
```

---

## Writing New Tests

### Test File Structure

```typescript
import { test, expect } from '../../fixtures';

/**
 * Test Suite Description
 * Feature XX.Y: Feature Name
 */
test.describe('Feature Name', () => {
  /**
   * Test description
   * Verifies specific behavior
   */
  test('should do something', async ({ page }) => {
    // 1. Arrange: Set up test data
    await page.goto('/');

    // 2. Act: Perform action
    const button = page.getByTestId('my-button');
    await button.click();

    // 3. Assert: Verify result
    const result = page.getByTestId('result');
    await expect(result).toBeVisible();
    await expect(result).toHaveText('Expected Text');
  });
});
```

### Using Authentication Mocking

```typescript
import { test } from '../../fixtures';
import { setupAuthMocking } from '../../helpers/auth';

test('authenticated page', async ({ page }) => {
  // Mock authentication
  await setupAuthMocking(page);

  // Navigate to protected page
  await page.goto('/admin');

  // Test authenticated content
  // ...
});
```

### Mocking API Endpoints

```typescript
test('should handle API response', async ({ page }) => {
  // Mock API endpoint
  await page.route('**/api/v1/chat', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        response: 'Mocked response',
        session_id: 'test-123',
      }),
    });
  });

  await page.goto('/');

  // Trigger API call
  await page.getByTestId('send-button').click();

  // Verify mocked response
  const message = page.getByTestId('message').last();
  await expect(message).toContainText('Mocked response');
});
```

### Using data-testid Attributes

**In React Component:**
```tsx
<button data-testid="send-button" onClick={handleSend}>
  Send
</button>
```

**In Test:**
```typescript
const button = page.getByTestId('send-button');
await button.click();
```

---

## Test Infrastructure

### Visual Regression Testing

**Setup:**
```typescript
import { visual } from '../../visual-regression.config';

test('page renders consistently @visual', async ({ page }) => {
  await page.goto('/');

  // Compare full page screenshot
  await visual.comparePage(page, 'chat-page-default', {
    fullPage: true,
    mask: [visual.masks.timestamps], // Hide dynamic content
  });
});
```

**Update Snapshots:**
```bash
npm run test:visual:update
```

### Accessibility Testing

**Setup:**
```typescript
import { a11y } from '../../accessibility.config';

test('page is accessible @a11y', async ({ page }) => {
  await page.goto('/');

  // Check WCAG 2.1 Level AA compliance
  await a11y.checkPage(page, 'Chat Page', {
    wcagLevel: a11y.wcagLevels.AA,
  });
});
```

**Run Accessibility Tests:**
```bash
npm run test:a11y
```

### Responsive Testing

```typescript
test('responsive on mobile', async ({ page }) => {
  // Set mobile viewport
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/');

  // Check mobile-specific UI
  const hamburger = page.getByTestId('mobile-menu-toggle');
  await expect(hamburger).toBeVisible();
});
```

---

## Troubleshooting

### Test Fails Locally

**Problem:** Test fails on your machine

**Solutions:**

1. **Check browser version:**
   ```bash
   npx playwright install
   ```

2. **Clear test results:**
   ```bash
   rm -rf test-results playwright-report
   ```

3. **Run in headed mode:**
   ```bash
   npm run test:e2e:headed
   ```

4. **Check screenshots:**
   - Located in `test-results/<test-name>/test-failed-1.png`

### Element Not Found

**Problem:** `Error: element(s) not found`

**Solutions:**

1. **Wait for element:**
   ```typescript
   await page.waitForSelector('[data-testid="my-element"]', {
     timeout: 10000,
   });
   ```

2. **Wait for network:**
   ```typescript
   await page.waitForLoadState('networkidle');
   ```

3. **Add explicit wait:**
   ```typescript
   await page.waitForTimeout(1000);
   ```

### Visual Regression Fails

**Problem:** Screenshot comparison fails

**Solutions:**

1. **View diff image:**
   - Check `test-results/<test-name>/<screenshot>-diff.png`

2. **Update snapshot (if intentional change):**
   ```bash
   npm run test:visual:update
   ```

3. **Increase threshold:**
   ```typescript
   await visual.comparePage(page, 'page', {
     threshold: 0.3, // 30% tolerance (increase if needed)
   });
   ```

### Accessibility Violations

**Problem:** Test fails with a11y violations

**Solutions:**

1. **Read violation details:**
   - Check console output for specific issues

2. **Fix the violation:**
   - Add `aria-label` to buttons
   - Improve color contrast
   - Fix heading hierarchy

3. **Disable rule temporarily (false positive):**
   ```typescript
   await a11y.checkPage(page, 'Page', {
     disabledRules: ['color-contrast'],
   });
   ```

### Tests Slow Locally

**Problem:** Tests take too long

**Solutions:**

1. **Use parallel execution:**
   ```bash
   npm run test:parallel
   ```

2. **Run specific test:**
   ```bash
   npx playwright test e2e/tests/chat/chat-features.spec.ts:28
   ```

3. **Reduce workers:**
   - Edit `playwright.config.parallel.ts`
   - Change `workers: 4` to `workers: 2`

---

## FAQ

### Q: Do I need the backend running for E2E tests?

**A:** No, for most E2E tests. They use mocked APIs (`page.route()`). Only integration tests require live backend.

**E2E (mocked APIs):** No backend needed
**Integration tests:** Backend required

### Q: How do I add a new test?

**A:**
1. Create test file in appropriate directory (e.g., `e2e/tests/chat/my-test.spec.ts`)
2. Import fixtures: `import { test, expect } from '../../fixtures';`
3. Write test using `test.describe()` and `test()`
4. Run: `npx playwright test e2e/tests/chat/my-test.spec.ts`

### Q: How do I debug a failing test?

**A:**
```bash
# Option 1: Debug mode (step through)
npx playwright test --debug e2e/tests/chat/my-test.spec.ts

# Option 2: Headed mode (see browser)
npm run test:e2e:headed

# Option 3: View trace
npx playwright show-trace test-results/<test-name>/trace.zip
```

### Q: What's the difference between E2E and Integration tests?

**A:**

**E2E Tests:**
- Mock all API calls with `page.route()`
- No backend required
- Fast execution (~2-3 min)
- Test frontend logic in isolation

**Integration Tests:**
- Use real backend services
- Require Docker Compose running
- Slower execution (~5-10 min)
- Test full stack end-to-end

### Q: How do I run tests in CI/CD?

**A:**
```bash
# GitHub Actions mode
npm run test:ci

# Sharded execution (parallel CI workers)
SHARD_INDEX=1 SHARD_TOTAL=4 npm run test:ci:sharded
```

### Q: How do I update visual regression snapshots?

**A:**
```bash
# Update all snapshots
npm run test:visual:update

# Update specific test
npx playwright test --update-snapshots e2e/tests/chat/my-test.spec.ts
```

### Q: How do I check test coverage?

**A:** See `docs/TEST_COVERAGE_REPORT.md` for comprehensive coverage report.

### Q: Can I run tests on mobile browsers?

**A:** Yes! Use parallel config:
```bash
npx playwright test --config=playwright.config.parallel.ts --project=mobile-chrome
npx playwright test --config=playwright.config.parallel.ts --project=mobile-safari
```

---

## Best Practices

### ✅ Do's

1. **Use `data-testid` attributes** for reliable selectors
2. **Mock APIs with `page.route()`** for E2E tests
3. **Use parallel execution** for faster test runs
4. **Add visual regression tests** for critical UI
5. **Check accessibility** for all pages
6. **Write descriptive test names** (e.g., "should display error message when API fails")
7. **Use fixtures** for authentication and common setups
8. **Wait for network idle** before assertions

### ❌ Don'ts

1. **Don't use CSS selectors** (fragile, use `data-testid` instead)
2. **Don't hardcode timeouts** (use `waitForSelector` instead)
3. **Don't test implementation details** (test user-visible behavior)
4. **Don't share state between tests** (keep tests isolated)
5. **Don't skip failing tests** (fix them or document why)
6. **Don't commit `.only()` or `.skip()`** (use conditionally)

---

## Additional Resources

**Documentation:**
- [Test Infrastructure README](../frontend/e2e/TEST_INFRASTRUCTURE_README.md)
- [Test Coverage Report](../docs/TEST_COVERAGE_REPORT.md)
- [Sprint 73 Progress Summary](../docs/sprints/SPRINT_73_PROGRESS_SUMMARY.md)

**Example Tests:**
- [Visual Regression Examples](../frontend/e2e/tests/examples/visual-regression.example.spec.ts)
- [Accessibility Examples](../frontend/e2e/tests/examples/accessibility.example.spec.ts)
- [Chat Features](../frontend/e2e/tests/chat/chat-features.spec.ts)

**External Resources:**
- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Testing Best Practices](https://playwright.dev/docs/best-practices)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

**Last Updated:** 2026-01-03
**Sprint:** 73
**Feedback:** Please report issues or suggestions to the development team
