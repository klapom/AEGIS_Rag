# Test Patterns & Best Practices

**Sprint:** 73
**Date:** 2026-01-03
**Purpose:** Standardized test patterns for consistent, maintainable E2E tests

---

## Table of Contents

1. [Test Structure Patterns](#test-structure-patterns)
2. [Authentication Patterns](#authentication-patterns)
3. [API Mocking Patterns](#api-mocking-patterns)
4. [Assertion Patterns](#assertion-patterns)
5. [Waiting Patterns](#waiting-patterns)
6. [Error Handling Patterns](#error-handling-patterns)
7. [Data Management Patterns](#data-management-patterns)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

---

## Test Structure Patterns

### Pattern 1: AAA (Arrange-Act-Assert)

```typescript
test('should send message', async ({ page }) => {
  // 📦 ARRANGE: Set up test conditions
  await page.goto('/');
  const input = page.getByTestId('message-input');
  const button = page.getByTestId('send-button');

  // 🎬 ACT: Perform the action
  await input.fill('Hello, world!');
  await button.click();

  // ✅ ASSERT: Verify the outcome
  const message = page.getByTestId('message').last();
  await expect(message).toContainText('Hello, world!');
});
```

**Why:** Clear separation of setup, action, and verification makes tests easier to read and maintain.

---

### Pattern 2: Test Describe Grouping

```typescript
test.describe('Feature Name - Sprint XX', () => {
  // Shared setup
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.describe('Sub-feature A', () => {
    test('should do X', async ({ page }) => {
      // Test X
    });

    test('should do Y', async ({ page }) => {
      // Test Y
    });
  });

  test.describe('Sub-feature B', () => {
    test('should do Z', async ({ page }) => {
      // Test Z
    });
  });
});
```

**Why:** Logical grouping improves test organization and allows shared setup/teardown.

---

### Pattern 3: Test Documentation

```typescript
/**
 * Feature 73.4: Chat Interface Completion
 *
 * Tests conversation history search functionality:
 * 1. Search within current conversation
 * 2. Filter by date range
 * 3. Highlight search results
 * 4. Clear search
 *
 * Scope: 4 tests, 2 SP
 * Dependencies: Chat API, Message storage
 */
test.describe('Conversation History Search', () => {
  test('should search messages within current conversation', async ({ page }) => {
    // Test implementation
  });
});
```

**Why:** Clear documentation helps developers understand test purpose and scope.

---

## Authentication Patterns

### Pattern 1: Mock Authentication (E2E Tests)

```typescript
import { setupAuthMocking } from '../../helpers/auth';

test('authenticated page', async ({ page }) => {
  // Mock auth endpoints and set token
  await setupAuthMocking(page);

  // Navigate to protected page
  await page.goto('/admin');

  // Verify authenticated content
  const welcomeMessage = page.getByText('Welcome, testuser');
  await expect(welcomeMessage).toBeVisible();
});
```

**When to use:** All E2E tests that access protected routes.

---

### Pattern 2: Real Authentication (Integration Tests)

```typescript
test('login flow', async ({ page }) => {
  await page.goto('/login');

  // Use real credentials
  await page.getByTestId('username-input').fill(process.env.TEST_USERNAME!);
  await page.getByTestId('password-input').fill(process.env.TEST_PASSWORD!);
  await page.getByTestId('login-button').click();

  // Wait for redirect
  await page.waitForURL('/');

  // Verify logged in
  const logoutButton = page.getByTestId('logout-button');
  await expect(logoutButton).toBeVisible();
});
```

**When to use:** Integration tests that test auth flow end-to-end.

---

## API Mocking Patterns

### Pattern 1: Simple Response Mock

```typescript
test('should display API data', async ({ page }) => {
  // Mock successful response
  await page.route('**/api/v1/data', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [{ id: 1, name: 'Item 1' }],
      }),
    });
  });

  await page.goto('/');

  const item = page.getByText('Item 1');
  await expect(item).toBeVisible();
});
```

---

### Pattern 2: Dynamic Mock with Request Inspection

```typescript
test('should filter by query param', async ({ page }) => {
  await page.route('**/api/v1/search**', route => {
    const url = new URL(route.request().url());
    const query = url.searchParams.get('q');

    const results = mockData.filter(item =>
      item.title.includes(query || '')
    );

    route.fulfill({
      status: 200,
      body: JSON.stringify({ results }),
    });
  });

  await page.goto('/search?q=machine');

  // Verify filtered results
  const results = page.getByTestId('search-result');
  await expect(results).toHaveCount(3);
});
```

---

### Pattern 3: Sequential Mock Responses

```typescript
test('should poll for updates', async ({ page }) => {
  let callCount = 0;
  const responses = [
    { status: 'pending', progress: 0 },
    { status: 'in-progress', progress: 50 },
    { status: 'completed', progress: 100 },
  ];

  await page.route('**/api/v1/status', route => {
    route.fulfill({
      status: 200,
      body: JSON.stringify(responses[callCount++] || responses[responses.length - 1]),
    });
  });

  await page.goto('/');

  // Wait for completion
  await page.waitForFunction(
    () => document.querySelector('[data-testid="status"]')?.textContent === 'completed',
    { timeout: 10000 }
  );
});
```

---

### Pattern 4: Error Response Mock

```typescript
test('should handle 500 error', async ({ page }) => {
  await page.route('**/api/v1/chat', route => {
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({
        error: 'Internal Server Error',
      }),
    });
  });

  await page.goto('/');
  await page.getByTestId('send-button').click();

  const errorMessage = page.getByTestId('error-message');
  await expect(errorMessage).toBeVisible();
  await expect(errorMessage).toContainText('Internal Server Error');
});
```

---

## Assertion Patterns

### Pattern 1: Visibility Assertions

```typescript
// ✅ Good: Wait for visibility
await expect(page.getByTestId('element')).toBeVisible();

// ✅ Good: Check NOT visible
await expect(page.getByTestId('element')).not.toBeVisible();

// ❌ Bad: Don't check existence alone
const exists = await page.locator('[data-testid="element"]').count() > 0;
```

**Why:** `toBeVisible()` waits for element and checks it's actually visible to users.

---

### Pattern 2: Text Content Assertions

```typescript
// ✅ Good: Exact match
await expect(page.getByTestId('title')).toHaveText('Welcome');

// ✅ Good: Partial match
await expect(page.getByTestId('message')).toContainText('Success');

// ✅ Good: Regex match
await expect(page.getByTestId('count')).toHaveText(/\d+ items/);

// ❌ Bad: Manual text extraction
const text = await page.getByTestId('title').textContent();
expect(text).toBe('Welcome'); // Not recommended
```

---

### Pattern 3: Count Assertions

```typescript
// ✅ Good: Check count
await expect(page.getByTestId('message')).toHaveCount(5);

// ✅ Good: Check at least N
const count = await page.getByTestId('message').count();
expect(count).toBeGreaterThanOrEqual(3);

// ✅ Good: Check none
await expect(page.getByTestId('error')).toHaveCount(0);
```

---

### Pattern 4: Attribute Assertions

```typescript
// ✅ Good: Check attribute
await expect(page.getByTestId('input')).toHaveAttribute('type', 'text');

// ✅ Good: Check disabled
await expect(page.getByTestId('button')).toBeDisabled();

// ✅ Good: Check enabled
await expect(page.getByTestId('button')).toBeEnabled();

// ✅ Good: Check CSS
await expect(page.getByTestId('element')).toHaveCSS('color', 'rgb(255, 0, 0)');
```

---

## Waiting Patterns

### Pattern 1: Wait for Element

```typescript
// ✅ Good: Built-in wait with expect
await expect(page.getByTestId('element')).toBeVisible({ timeout: 10000 });

// ✅ Good: Explicit wait
await page.waitForSelector('[data-testid="element"]', { timeout: 10000 });

// ❌ Bad: Fixed timeout
await page.waitForTimeout(5000); // Avoid unless necessary
```

---

### Pattern 2: Wait for Network

```typescript
// ✅ Good: Wait for network idle
await page.waitForLoadState('networkidle');

// ✅ Good: Wait for specific request
const responsePromise = page.waitForResponse('**/api/v1/data');
await page.getByTestId('load-button').click();
await responsePromise;

// ✅ Good: Wait for navigation
await Promise.all([
  page.waitForNavigation(),
  page.getByTestId('submit-button').click(),
]);
```

---

### Pattern 3: Wait for Condition

```typescript
// ✅ Good: Poll for condition
await page.waitForFunction(
  () => document.querySelector('[data-testid="progress"]')?.textContent === '100%',
  { timeout: 15000 }
);

// ✅ Good: Wait for multiple conditions
await Promise.all([
  expect(page.getByTestId('status')).toHaveText('Ready'),
  expect(page.getByTestId('button')).toBeEnabled(),
]);
```

---

## Error Handling Patterns

### Pattern 1: Graceful Feature Detection

```typescript
test('optional feature', async ({ page }) => {
  await page.goto('/');

  // Check if feature exists
  const feature = page.getByTestId('optional-feature');
  const isVisible = await feature.isVisible().catch(() => false);

  if (isVisible) {
    // Test feature
    await feature.click();
    // ...
  } else {
    console.log('[INFO] Optional feature not implemented yet');
    // Test passes gracefully
  }
});
```

**When to use:** Testing features that may not be implemented yet (TDD approach).

---

### Pattern 2: Expected Error Handling

```typescript
test('should handle error gracefully', async ({ page }) => {
  // Mock error
  await page.route('**/api/v1/action', route => {
    route.fulfill({ status: 500 });
  });

  await page.goto('/');
  await page.getByTestId('action-button').click();

  // Verify error handling
  const errorToast = page.getByTestId('error-toast');
  await expect(errorToast).toBeVisible();
  await expect(errorToast).toContainText('Something went wrong');

  // Verify recovery
  const retryButton = page.getByTestId('retry-button');
  await expect(retryButton).toBeVisible();
});
```

---

### Pattern 3: Timeout Handling

```typescript
test('should timeout gracefully', async ({ page }) => {
  await page.goto('/');

  try {
    await page.waitForSelector('[data-testid="never-appears"]', {
      timeout: 5000,
    });
    throw new Error('Should have timed out');
  } catch (error) {
    // Expected timeout
    expect(error.message).toContain('Timeout');
  }
});
```

---

## Data Management Patterns

### Pattern 1: Mock Data Factory

```typescript
// helpers/mockDataFactory.ts
export function createMockMessage(overrides = {}) {
  return {
    id: `msg-${Date.now()}`,
    role: 'assistant',
    content: 'Default message',
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

// In test
test('should display message', async ({ page }) => {
  const mockMessage = createMockMessage({
    content: 'Custom message',
  });

  await page.route('**/api/v1/chat', route => {
    route.fulfill({
      status: 200,
      body: JSON.stringify(mockMessage),
    });
  });

  // ...
});
```

---

### Pattern 2: Test Fixtures

```typescript
// fixtures/index.ts
import { test as base } from '@playwright/test';

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    await page.goto('/');
    await use(page);
  },
});

// In test
test('uses fixture', async ({ authenticatedPage }) => {
  // Page is already authenticated and loaded
  await expect(authenticatedPage.getByTestId('welcome')).toBeVisible();
});
```

---

### Pattern 3: Test Data Cleanup

```typescript
test.afterEach(async ({ page }) => {
  // Clear localStorage
  await page.evaluate(() => localStorage.clear());

  // Clear cookies
  await page.context().clearCookies();
});
```

---

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: CSS Selectors

```typescript
// ❌ BAD: Fragile CSS selector
const button = page.locator('.btn.btn-primary.send-button');

// ✅ GOOD: data-testid
const button = page.getByTestId('send-button');
```

**Why:** CSS classes change, data-testid is stable.

---

### ❌ Anti-Pattern 2: Fixed Timeouts

```typescript
// ❌ BAD: Arbitrary wait
await page.waitForTimeout(3000);
await expect(page.getByTestId('element')).toBeVisible();

// ✅ GOOD: Wait for condition
await expect(page.getByTestId('element')).toBeVisible({ timeout: 10000 });
```

**Why:** Fixed timeouts are flaky and slow.

---

### ❌ Anti-Pattern 3: Testing Implementation Details

```typescript
// ❌ BAD: Testing React state
const state = await page.evaluate(() => window.__REACT_STATE__);
expect(state.count).toBe(5);

// ✅ GOOD: Testing user-visible behavior
await expect(page.getByTestId('count-display')).toHaveText('5');
```

**Why:** Tests should verify what users see, not implementation.

---

### ❌ Anti-Pattern 4: Shared State Between Tests

```typescript
// ❌ BAD: Shared global state
let sharedData = [];

test('test 1', async ({ page }) => {
  sharedData.push('data');
  // ...
});

test('test 2', async ({ page }) => {
  expect(sharedData.length).toBe(1); // ❌ Depends on test order!
});

// ✅ GOOD: Isolated tests
test('test 1', async ({ page }) => {
  const localData = [];
  localData.push('data');
  // ...
});

test('test 2', async ({ page }) => {
  const localData = [];
  expect(localData.length).toBe(0); // ✅ Independent!
});
```

---

### ❌ Anti-Pattern 5: Multiple Assertions in One Test

```typescript
// ❌ BAD: Testing multiple features
test('should do everything', async ({ page }) => {
  // Test login
  // Test navigation
  // Test form submission
  // Test logout
  // ... (100 lines)
});

// ✅ GOOD: One test per feature
test('should login', async ({ page }) => {
  // Test login only
});

test('should navigate', async ({ page }) => {
  // Test navigation only
});
```

**Why:** Small, focused tests are easier to debug and maintain.

---

## Summary

### Key Takeaways

1. **Use AAA pattern** (Arrange-Act-Assert) for clear test structure
2. **Use `data-testid`** for reliable element selection
3. **Mock APIs** with `page.route()` for E2E tests
4. **Wait for conditions** instead of fixed timeouts
5. **Test user behavior**, not implementation details
6. **Keep tests isolated** - no shared state
7. **Document tests** with clear descriptions

### Pattern Checklist

- [ ] Test follows AAA pattern
- [ ] Uses `data-testid` selectors
- [ ] Has clear test description
- [ ] Mocks APIs appropriately
- [ ] Uses proper waits (no `waitForTimeout`)
- [ ] Asserts user-visible behavior
- [ ] Is independent of other tests
- [ ] Handles errors gracefully

---

**Last Updated:** 2026-01-03
**Sprint:** 73
**Feedback:** Submit improvements to these patterns via PR
