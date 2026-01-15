# E2E Testing Patterns & Best Practices

**Reference Guide for Sprint 97-98 Test Suites**

---

## 1. Page Object Model (POM)

All tests follow strict POM pattern for maintainability.

### Pattern Structure

```typescript
// 1. Define navigation function
async function navigateToFeaturePage(page: Page) {
  await page.goto(`${ADMIN_URL}/admin/feature`);
  await page.waitForLoadState('networkidle');
  await expect(page.getByTestId('feature-page')).toBeVisible();
}

// 2. Define action functions
async function performAction(page: Page, data: ActionData) {
  const input = page.getByTestId('input-field');
  await input.fill(data.value);

  const button = page.getByTestId('action-button');
  await button.click();

  await page.waitForLoadState('networkidle');
}

// 3. Define getter functions
async function getElementData(page: Page): Promise<ElementData> {
  const element = page.getByTestId('data-element');
  const text = await element.textContent();
  return { text };
}

// 4. Use in tests
test('should perform action', async ({ page }) => {
  await navigateToFeaturePage(page);
  await performAction(page, { value: 'test' });
  const data = await getElementData(page);
  expect(data.text).toBe('expected');
});
```

### Benefits
- **Maintainability:** UI changes → update POM, not all tests
- **Reusability:** Share utilities across tests
- **Readability:** Tests read like specifications
- **Scalability:** Easy to add new tests

---

## 2. Async/Await Pattern

All async operations must use proper `await`.

### Pattern

```typescript
// ✅ CORRECT: Always await async operations
test('should load data', async ({ page }) => {
  await page.goto(url);                          // await
  await page.waitForLoadState('networkidle');    // await
  await expect(element).toBeVisible();            // await
  const text = await element.textContent();      // await
  expect(text).toBe('expected');
});

// ❌ INCORRECT: Missing awaits
test('should load data', async ({ page }) => {
  page.goto(url);                                // Missing await
  page.waitForLoadState('networkidle');          // Missing await
  expect(element).toBeVisible();                 // Missing await
  const text = element.textContent();            // Missing await
});
```

### Rule
**Every async operation must be awaited or chained with `.then()`**

---

## 3. Element Interaction Pattern

Standard way to interact with page elements.

### Pattern

```typescript
// Get element
const button = page.getByTestId('action-button');

// Check visibility
await expect(button).toBeVisible();

// Interact
await button.click();

// Verify result
const text = await button.textContent();
expect(text).toBe('expected');

// Alternative: Use locator directly
await page.getByTestId('submit-button').click();
```

### Common Operations

```typescript
// Text input
const input = page.getByTestId('text-input');
await input.fill('value');
await input.clear();
await input.type('text');

// Select dropdown
const select = page.getByTestId('select-dropdown');
await select.selectOption('value');
await select.selectOption({ label: 'Display Label' });

// Checkbox
const checkbox = page.getByTestId('checkbox');
await checkbox.check();      // Check
await checkbox.uncheck();    // Uncheck
await checkbox.isChecked();  // Verify

// Click
const element = page.getByTestId('element');
await element.click();
await element.dblClick();    // Double click
await element.rightClick();  // Right click

// Hover
const element = page.getByTestId('element');
await element.hover();

// Drag and drop
const source = page.getByTestId('source');
const target = page.getByTestId('target');
await source.dragTo(target);
```

---

## 4. Wait Pattern

Proper waiting techniques for test stability.

### Pattern

```typescript
// ✅ BEST: Wait for condition
await expect(element).toBeVisible();
await expect(element).toContainText('text');
await page.waitForLoadState('networkidle');

// ✅ GOOD: Wait for element
await page.waitForSelector('[data-testid="element"]');

// ⚠️ ACCEPTABLE: Wait for timeout (last resort)
await page.waitForTimeout(500);

// ❌ BAD: Arbitrary delays (flaky)
await new Promise(resolve => setTimeout(resolve, 1000));
```

### Load States

```typescript
// Wait for load to complete
await page.waitForLoadState('domcontentloaded');  // Basic load
await page.waitForLoadState('load');               // Full load
await page.waitForLoadState('networkidle');        // All requests done

// Wait for navigation
await page.waitForNavigation();
```

---

## 5. Test Isolation Pattern

Each test must be independent.

### Pattern

```typescript
test.describe('Feature Tests', () => {
  // Setup that runs before EACH test
  test.beforeEach(async ({ page }) => {
    await navigateToPage(page);
    // Create test data if needed
  });

  // Individual test - ISOLATED
  test('should do action 1', async ({ page }) => {
    // This test doesn't depend on other tests
    await performAction1(page);
    await verifyResult1(page);
  });

  // Another isolated test
  test('should do action 2', async ({ page }) => {
    // This test doesn't depend on test 1
    // Both use same beforeEach setup
    await performAction2(page);
    await verifyResult2(page);
  });
});

// Tests can run in ANY ORDER (or parallel with proper setup)
```

### Key Rules
1. **No test dependencies:** Tests don't depend on other tests
2. **Shared setup:** Use `beforeEach` for common setup
3. **Fresh state:** Each test starts clean
4. **Deterministic:** Same test always passes/fails

---

## 6. Assertion Pattern

Clear, specific assertions for test clarity.

### Pattern

```typescript
// Element assertions
await expect(element).toBeVisible();
await expect(element).toBeEnabled();
await expect(element).toBeChecked();
await expect(element).toHaveAttribute('href', '/path');
await expect(element).toHaveClass('active');
await expect(element).toHaveCount(5);

// Text assertions
await expect(element).toContainText('Search');
await expect(element).toHaveText('Exact text');

// Value assertions
await expect(element).toHaveValue('123');

// Count assertions
const items = page.getByTestId('item');
const count = await items.count();
expect(count).toBeGreaterThan(0);
expect(count).toBeLessThan(100);

// Custom assertions
const text = await element.textContent();
expect(text).toMatch(/pattern/);
expect(text?.length).toBeGreaterThan(10);
```

### Best Practices
1. **Be specific:** `toContainText('exact')` not just `toBeTruthy()`
2. **Assert one thing:** Multiple assertions per test is OK, but clear
3. **Use semantic matchers:** `toBeVisible()` not `not.toHaveClass('hidden')`

---

## 7. Error Handling Pattern

Gracefully handle missing/optional elements.

### Pattern

```typescript
// Optional element
const optionalElement = page.getByTestId('optional');
if (await optionalElement.isVisible()) {
  const value = await optionalElement.textContent();
  expect(value).toBeTruthy();
}

// Conditional action
const button = page.getByTestId('button');
if (await button.isEnabled()) {
  await button.click();
} else {
  // Alternative action
  console.log('Button disabled, skipping');
}

// Try-catch for non-existent elements
try {
  await page.getByTestId('must-exist').waitFor({ timeout: 1000 });
  // Element exists, proceed
} catch (error) {
  // Element doesn't exist, handle gracefully
  expect.fail('Element should have existed');
}
```

---

## 8. Test Data Pattern

Using fixtures and factories for test data.

### Pattern

```typescript
import { TEST_SKILLS, createTestSkill } from './fixtures/test-data';

// Use predefined data
test('should display skill', async ({ page }) => {
  const skill = TEST_SKILLS[0];
  expect(skill.name).toBe('retrieval');
});

// Use factory with overrides
test('should create custom skill', async ({ page }) => {
  const skill = createTestSkill({
    name: 'custom-skill',
    isActive: false,
  });
  expect(skill.name).toBe('custom-skill');
});

// Generate random data
test('should handle unique data', async ({ page }) => {
  const uniqueId = generateSkillId();
  await createSkill(page, { id: uniqueId });
  await verifySkillExists(page, uniqueId);
});
```

### Key Rules
1. **Centralize data:** Use fixtures/factories, not hardcoded values
2. **Use overrides:** Extend base data with specific test needs
3. **Generate IDs:** Use factories for unique identifiers

---

## 9. Performance Pattern

Verify performance targets without being brittle.

### Pattern

```typescript
test('should load in acceptable time', async ({ page }) => {
  const startTime = Date.now();

  await page.goto(url);
  await page.waitForLoadState('networkidle');

  const loadTime = Date.now() - startTime;
  expect(loadTime).toBeLessThan(2000);  // 2 seconds
});

test('should handle large dataset', async ({ page }) => {
  // Test with 100+ items
  const items = await page.getByTestId('item').all();
  expect(items.length).toBeGreaterThan(100);

  // Verify responsive
  const firstItem = items[0];
  await expect(firstItem).toBeVisible();
});
```

### Guidelines
- Performance targets are guidelines, not hard failures
- Focus on responsiveness, not nanoseconds
- Test with realistic data volumes

---

## 10. Edge Case Pattern

Comprehensive edge case testing.

### Pattern

```typescript
test.describe('Edge Cases', () => {
  // Empty data
  test('should handle empty list', async ({ page }) => {
    // Verify "no items" message shown
    await expect(page.getByTestId('empty-message')).toBeVisible();
  });

  // Large data
  test('should handle 1000+ items', async ({ page }) => {
    const items = await page.getByTestId('item').count();
    expect(items).toBeGreaterThan(1000);

    // Verify pagination works
    const nextButton = page.getByTestId('next-page');
    await nextButton.click();
  });

  // Special characters
  test('should handle special chars', async ({ page }) => {
    await fillInput(page, 'value with @#$% chars');
    await submitForm(page);

    const result = page.getByTestId('result');
    const text = await result.textContent();
    expect(text).toContain('@#$%');
  });

  // Concurrent operations
  test('should handle concurrent updates', async ({ page }) => {
    // Perform two actions simultaneously
    await Promise.all([
      action1(page),
      action2(page),
    ]);

    // Verify both completed
    await expect(result1).toBeVisible();
    await expect(result2).toBeVisible();
  });

  // Network failures
  test('should handle API failures', async ({ page }) => {
    // Abort API requests
    await page.route('**/api/**', route => route.abort());

    // Try action
    await performAction(page);

    // Verify error handled gracefully
    await expect(page.getByTestId('error-message')).toBeVisible();
  });
});
```

---

## 11. Form Submission Pattern

Standard form interaction pattern.

### Pattern

```typescript
interface FormData {
  username: string;
  email: string;
  agree: boolean;
}

async function fillForm(page: Page, data: FormData) {
  // Text inputs
  await page.getByTestId('username-input').fill(data.username);
  await page.getByTestId('email-input').fill(data.email);

  // Checkboxes
  if (data.agree) {
    await page.getByTestId('agree-checkbox').check();
  }
}

async function submitForm(page: Page) {
  const submitButton = page.getByTestId('submit-button');
  await submitButton.click();

  // Wait for success/error
  await page.waitForLoadState('networkidle');
}

// Test
test('should submit form', async ({ page }) => {
  await navigateToForm(page);

  await fillForm(page, {
    username: 'testuser',
    email: 'test@example.com',
    agree: true,
  });

  await submitForm(page);

  // Verify success
  await expect(page.getByTestId('success-message')).toBeVisible();
});
```

---

## 12. Table/List Interaction Pattern

Common pattern for working with tables and lists.

### Pattern

```typescript
test('should filter list and verify results', async ({ page }) => {
  // Get initial count
  const initialRows = await page.getByTestId('table-row').count();
  expect(initialRows).toBeGreaterThan(0);

  // Apply filter
  await page.getByTestId('filter-input').fill('search-term');
  await page.getByTestId('filter-button').click();
  await page.waitForLoadState('networkidle');

  // Verify filtered results
  const filteredRows = await page.getByTestId('table-row').count();
  expect(filteredRows).toBeLessThanOrEqual(initialRows);

  // Verify all results match filter
  const rows = await page.getByTestId('table-row').all();
  for (const row of rows) {
    const text = await row.textContent();
    expect(text).toContain('search-term');
  }
});

test('should paginate through results', async ({ page }) => {
  // Get first page
  const page1Rows = await page.getByTestId('table-row').all();
  const page1Count = page1Rows.length;

  // Go to next page
  await page.getByTestId('next-page-button').click();
  await page.waitForLoadState('networkidle');

  // Get next page
  const page2Rows = await page.getByTestId('table-row').all();
  expect(page2Rows.length).toBeGreaterThan(0);

  // Verify different content
  const page1Text = page1Rows[0].textContent();
  const page2Text = page2Rows[0].textContent();
  expect(page1Text).not.toBe(page2Text);
});
```

---

## Common Pitfalls to Avoid

### 1. Missing Awaits
```typescript
// ❌ WRONG
const value = page.getByTestId('element').textContent();  // Not awaited

// ✅ CORRECT
const value = await page.getByTestId('element').textContent();
```

### 2. Hardcoded Delays
```typescript
// ❌ WRONG (flaky)
await new Promise(r => setTimeout(r, 1000));

// ✅ CORRECT (deterministic)
await page.waitForLoadState('networkidle');
```

### 3. No Isolation
```typescript
// ❌ WRONG (tests depend on each other)
test('login', async () => { /* login */ });
test('uses login from previous test', async () => { /* fails if run alone */ });

// ✅ CORRECT (each test independent)
test.beforeEach(async ({ page }) => { await login(page); });
test('action', async ({ page }) => { /* doesn't depend on login */ });
```

### 4. Too Broad Selectors
```typescript
// ❌ WRONG (might select wrong element)
const button = page.locator('button');  // Which button?

// ✅ CORRECT (specific selector)
const button = page.getByTestId('submit-button');
```

### 5. No Error Checking
```typescript
// ❌ WRONG (element might not exist)
const value = await page.getByTestId('optional').textContent();

// ✅ CORRECT (handle missing element)
const element = page.getByTestId('optional');
if (await element.isVisible()) {
  const value = await element.textContent();
}
```

---

## Debugging Tips

### View Current Page
```typescript
test('debug test', async ({ page }) => {
  // Take screenshot
  await page.screenshot({ path: 'debug.png' });

  // Print HTML
  const html = await page.content();
  console.log(html);

  // Print all text
  const text = await page.textContent();
  console.log(text);
});
```

### Interactive Debugging
```bash
# Run single test in debug mode
npm run test:e2e:debug -- 03-skill-management.spec.ts -g "search skills"
```

### Logging
```typescript
test('debug test', async ({ page }) => {
  console.log('Starting test');
  await page.goto(url);
  console.log('Navigated to page');

  await page.getByTestId('button').click();
  console.log('Button clicked');
});
```

---

## Summary

| Pattern | When to Use |
|---------|------------|
| **POM** | Always - organize utilities by feature |
| **Async/Await** | Always - every async operation |
| **Isolation** | Always - tests should be independent |
| **Assertions** | Always - verify expected behavior |
| **Error Handling** | For optional elements/actions |
| **Edge Cases** | Important features/workflows |
| **Performance** | For performance-critical features |

---

**Document:** TESTING_PATTERNS.md
**Status:** Complete
**Last Updated:** 2026-01-15

See also:
- README_SPRINT_97_98.md - Test suite documentation
- IMPLEMENTATION_SUMMARY.md - Overall summary
