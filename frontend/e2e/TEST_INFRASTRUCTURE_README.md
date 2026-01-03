# Test Infrastructure Guide

**Feature 73.8: Test Infrastructure Improvements**
**Created:** 2026-01-03
**Sprint:** 73

---

## Overview

This document describes the enhanced test infrastructure for the AEGIS RAG frontend, including parallel execution, visual regression testing, accessibility testing, and advanced reporting.

---

## Table of Contents

1. [Parallel Test Execution](#parallel-test-execution)
2. [Visual Regression Testing](#visual-regression-testing)
3. [Accessibility Testing](#accessibility-testing)
4. [Test Reporting](#test-reporting)
5. [npm Scripts Reference](#npm-scripts-reference)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Parallel Test Execution

### Overview

Parallel execution runs multiple tests simultaneously, reducing total execution time from ~10 minutes to ~2-3 minutes.

### Configuration

**File:** `playwright.config.parallel.ts`

**Key Settings:**
- **Workers:** 4 (local), 2 (CI)
- **Fully Parallel:** `true`
- **Retries:** 2 (CI only)
- **Browsers:** Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari

### Usage

```bash
# Run tests in parallel (recommended for E2E with mocks)
npm run test:parallel

# Run specific browser
npm run test:parallel:chromium

# Run all browsers
npm run test:parallel:all-browsers

# Run with UI (headed mode)
npm run test:parallel:headed
```

### When to Use

**✅ Use Parallel Config For:**
- E2E tests with mocked APIs
- Visual regression tests
- Accessibility tests
- Tests that don't require live backend

**❌ Use Standard Config For:**
- Integration tests (live backend)
- Tests with SSE streaming
- Tests with database writes
- Multi-turn conversation tests

---

## Visual Regression Testing

### Overview

Visual regression testing catches unintended UI changes by comparing screenshots pixel-by-pixel.

### Configuration

**File:** `e2e/visual-regression.config.ts`

**Features:**
- Automatic screenshot capture and comparison
- Custom thresholds per component/page
- Masking for dynamic content (timestamps, timers)
- Multi-viewport responsive testing

### Usage

```typescript
import { visual } from '../../visual-regression.config';

test('page renders consistently', async ({ page }) => {
  await page.goto('/');

  // Compare full page
  await visual.comparePage(page, 'chat-page-default', {
    fullPage: true,
    mask: [visual.masks.timestamps], // Hide dynamic content
  });
});

test('component renders correctly', async ({ page }) => {
  const button = page.getByTestId('send-button');

  // Compare component
  await visual.compareComponent(button, 'send-button-default', {
    threshold: 0.1, // 10% tolerance
  });
});

test('responsive layout', async ({ page }) => {
  // Test multiple viewports
  await visual.compareResponsive(page, 'chat-page', [
    visual.viewports.mobile,
    visual.viewports.tablet,
    visual.viewports.desktop,
  ]);
});
```

### npm Scripts

```bash
# Run visual regression tests
npm run test:visual

# Update snapshots (after intentional changes)
npm run test:visual:update
```

### Snapshot Location

Snapshots are stored in: `e2e/__screenshots__/`

**Example:**
```
e2e/
└── __screenshots__/
    └── tests/
        └── chat/
            ├── chat-page-default.png
            ├── chat-page-mobile.png
            ├── chat-page-tablet.png
            └── chat-page-desktop.png
```

### Masking Dynamic Content

Use masks to hide content that changes between runs:

```typescript
await visual.comparePage(page, 'my-page', {
  mask: [
    visual.masks.timestamps,    // [data-testid*="timestamp"]
    visual.masks.timers,        // [data-testid*="timing"]
    visual.masks.spinners,      // .animate-spin
    visual.masks.randomIds,     // [id^="radix-"]
    page.locator('.my-dynamic-element'), // Custom selector
  ],
});
```

---

## Accessibility Testing

### Overview

Automated accessibility (a11y) testing ensures WCAG 2.1 Level AA compliance using axe-core.

### Prerequisites

```bash
npm install --save-dev @axe-core/playwright
```

### Configuration

**File:** `e2e/accessibility.config.ts`

**Standards:**
- WCAG 2.1 Level AA (default)
- WCAG 2.1 Level A
- WCAG 2.2 Level AA (future)

### Usage

```typescript
import { a11y } from '../../accessibility.config';

test('page is accessible', async ({ page }) => {
  await page.goto('/');

  // Check full page
  await a11y.checkPage(page, 'Chat Page', {
    wcagLevel: a11y.wcagLevels.AA,
  });
});

test('component is accessible', async ({ page }) => {
  // Check specific component
  await a11y.checkComponent(
    page,
    '[data-testid="message-input"]',
    'Message Input'
  );
});

test('form with exceptions', async ({ page }) => {
  // Disable specific rules (false positives)
  await a11y.checkPage(page, 'Admin Page', {
    disabledRules: ['color-contrast'], // Known issue
    exclude: ['.third-party-widget'],  // Can't control
  });
});
```

### npm Scripts

```bash
# Run accessibility tests
npm run test:a11y
```

### Common Violations

| Rule | Description | Fix |
|------|-------------|-----|
| `label` | Form inputs missing labels | Add `<label>` or `aria-label` |
| `button-name` | Button missing accessible name | Add `aria-label` or text content |
| `color-contrast` | Insufficient contrast (4.5:1) | Adjust colors to meet WCAG AA |
| `heading-order` | Heading levels skipped | Use proper `<h1>`-`<h6>` hierarchy |
| `alt-text` | Image missing alt attribute | Add descriptive `alt` text |

### Keyboard Navigation Testing

```typescript
test('keyboard navigable', async ({ page }) => {
  await page.goto('/');

  // Tab through interactive elements
  await page.keyboard.press('Tab'); // First element
  await page.keyboard.press('Tab'); // Second element

  // Verify focus visible
  const focused = await page.evaluate(() => {
    return document.activeElement?.getAttribute('data-testid');
  });

  console.log(`Focused element: ${focused}`);
});
```

---

## Test Reporting

### HTML Report

**Default reporter** with interactive UI:

```bash
# Run tests (generates report)
npm run test:parallel

# Open report
npm run test:report

# Or manually
open playwright-report/index.html
```

**Features:**
- Test results with pass/fail status
- Screenshots on failure
- Trace viewer (timeline, network, console)
- Filterable by status, browser, file

### JSON Report

**File:** `test-results/results.json`

**Usage:**
- CI/CD integration
- Custom dashboards
- Historical tracking

### JUnit Report

**File:** `test-results/junit.xml`

**Usage:**
- Jenkins integration
- GitLab CI
- Azure DevOps

### GitHub Actions Report

Enabled automatically in CI:

```bash
npm run test:ci
```

**Features:**
- Annotations on PRs
- Failed test summaries
- Direct links to logs

---

## npm Scripts Reference

### Test Execution

| Script | Description |
|--------|-------------|
| `npm run test:e2e` | Run all E2E tests (sequential) |
| `npm run test:e2e:ui` | Open Playwright UI mode |
| `npm run test:e2e:headed` | Run tests with browser visible |
| `npm run test:e2e:debug` | Run tests in debug mode |

### Parallel Execution

| Script | Description |
|--------|-------------|
| `npm run test:parallel` | Run tests in parallel (4 workers) |
| `npm run test:parallel:headed` | Parallel execution with visible browser |
| `npm run test:parallel:chromium` | Parallel, Chromium only |
| `npm run test:parallel:all-browsers` | Test Chromium + Firefox + WebKit |

### Integration Tests

| Script | Description |
|--------|-------------|
| `npm run test:integration` | Run integration tests (live backend) |
| `npm run test:integration:multi-turn` | Run multi-turn chat tests |
| `npm run test:integration:performance` | Run performance regression tests |

### Test Suites

| Script | Description |
|--------|-------------|
| `npm run test:chat` | Run chat tests only |
| `npm run test:search` | Run search tests only |
| `npm run test:graph` | Run graph visualization tests |
| `npm run test:admin` | Run admin tests only |
| `npm run test:errors` | Run error handling tests |

### Visual & Accessibility

| Script | Description |
|--------|-------------|
| `npm run test:visual` | Run visual regression tests |
| `npm run test:visual:update` | Update visual snapshots |
| `npm run test:a11y` | Run accessibility tests |

### Reporting

| Script | Description |
|--------|-------------|
| `npm run test:report` | Open HTML report |
| `npm run test:trace` | Open trace viewer |

### CI/CD

| Script | Description |
|--------|-------------|
| `npm run test:ci` | Run tests for CI (GitHub Actions) |
| `npm run test:ci:sharded` | Run sharded tests (parallel CI) |

---

## Best Practices

### 1. Use Parallel Config for E2E Tests

```bash
# ✅ Good: Fast execution for mocked tests
npm run test:parallel

# ❌ Bad: Slow sequential execution
npm run test:e2e
```

### 2. Tag Visual and Accessibility Tests

```typescript
test.describe('My Tests @visual @a11y', () => {
  // ...
});
```

Run selectively:
```bash
npm run test:visual  # Runs @visual tests only
npm run test:a11y    # Runs @a11y tests only
```

### 3. Mask Dynamic Content

```typescript
// ❌ Bad: Flaky due to timestamps
await visual.comparePage(page, 'my-page');

// ✅ Good: Mask dynamic content
await visual.comparePage(page, 'my-page', {
  mask: [visual.masks.timestamps],
});
```

### 4. Use Appropriate Thresholds

```typescript
// Full page: Allow more variance
await visual.comparePage(page, 'page', {
  threshold: 0.2, // 20%
  maxDiffPixels: 100,
});

// Component: Strict comparison
await visual.compareComponent(button, 'button', {
  threshold: 0.1, // 10%
  maxDiffPixels: 50,
});
```

### 5. Check Accessibility Early

```typescript
test('new feature is accessible', async ({ page }) => {
  await page.goto('/new-feature');

  // Check immediately during development
  await a11y.checkPage(page, 'New Feature');
});
```

---

## Troubleshooting

### Visual Regression Failures

**Problem:** Screenshot comparison fails unexpectedly

**Solutions:**
1. **Check diff image:** `test-results/<test-name>/<screenshot>-diff.png`
2. **Update snapshots if intentional:** `npm run test:visual:update`
3. **Increase threshold:** Adjust `threshold` in test
4. **Mask dynamic content:** Add more selectors to `mask` array

### Accessibility Violations

**Problem:** Test fails with a11y violations

**Solutions:**
1. **Read violation details:** Check console output for affected elements
2. **Fix the issue:** Add labels, improve contrast, fix heading order
3. **Disable rule temporarily:** Use `disabledRules` if false positive
4. **Exclude third-party:** Use `exclude` for uncontrollable widgets

### Parallel Execution Failures

**Problem:** Tests fail in parallel but pass sequentially

**Solutions:**
1. **Check test isolation:** Ensure no shared state between tests
2. **Add waits:** `await page.waitForLoadState('networkidle')`
3. **Use test fixtures:** Isolate auth, mocks per test
4. **Run sequentially:** Use standard config for problematic tests

### CI/CD Failures

**Problem:** Tests pass locally but fail in CI

**Solutions:**
1. **Check browser versions:** Update Playwright: `npx playwright install`
2. **Increase timeouts:** CI is slower, increase `timeout` values
3. **Check screenshots:** CI environment may render differently
4. **Use retries:** Enable `retries: 2` in CI config

---

## Examples

See working examples in:
- `e2e/tests/examples/visual-regression.example.spec.ts`
- `e2e/tests/examples/accessibility.example.spec.ts`

---

## References

**Playwright Documentation:**
- [Visual Comparisons](https://playwright.dev/docs/test-snapshots)
- [Accessibility Testing](https://playwright.dev/docs/accessibility-testing)
- [Test Configuration](https://playwright.dev/docs/test-configuration)

**WCAG Guidelines:**
- [WCAG 2.1 Level AA](https://www.w3.org/WAI/WCAG21/quickref/?currentsidebar=%23col_overview&levels=aaa)
- [axe-core Rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)

---

**Last Updated:** 2026-01-03
**Feature:** 73.8 - Test Infrastructure Improvements
**Sprint:** 73
