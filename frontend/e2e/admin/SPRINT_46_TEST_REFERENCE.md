# Sprint 46 E2E Tests - Test Reference Guide

**Quick lookup for all 25 test cases across Features 46.5 and 46.8**

## Table of Contents
1. [Feature 46.5 - Domain Auto Discovery (10 tests)](#feature-465-domain-auto-discovery-10-tests)
2. [Feature 46.8 - Admin Dashboard (15 tests)](#feature-468-admin-dashboard-15-tests)
3. [Test Categories](#test-categories)
4. [API Endpoints by Test](#api-endpoints-by-test)
5. [Element Selectors Reference](#element-selectors-reference)

---

## Feature 46.5 - Domain Auto Discovery (10 tests)

**File:** `frontend/e2e/admin/domain-auto-discovery.spec.ts`

### Test Case Reference

| # | Test ID | Test Name | Category | Assertions | API Endpoint |
|---|---------|-----------|----------|-----------|--------------|
| 1 | TC-46.5.1 | Render drag-drop upload area | UI | `[uploadArea]` visibility, `[fileInput]` type | - |
| 2 | TC-46.5.2 | Accept TXT, MD, DOCX, HTML | Input | Accept attribute contains formats | - |
| 3 | TC-46.5.3 | Reject unsupported files | Error | Error message or file rejection | `POST /domains/discover` |
| 4 | TC-46.5.4 | Error on >3 files | Validation | Error message or button disabled | - |
| 5 | TC-46.5.5 | Loading state on analyze | UX | Loading spinner, button disabled | `POST /domains/discover` |
| 6 | TC-46.5.6 | Show suggestion after analysis | Integration | Suggestion panel, title, confidence | `POST /domains/discover` |
| 7 | TC-46.5.7 | Edit and accept suggestion | Workflow | Edit field, accept button, success | `POST /domains/discover` → `POST /domains` |
| 8 | TC-46.5.8 | Multiple files for accuracy | Advanced | File list count = 2 | `POST /domains/discover` |
| 9 | TC-46.5.9 | Clear files and reset | UX | File input cleared, upload area visible | - |
| 10 | TC-46.5.10 | Handle API errors | Error | Error message visible, retry enabled | `POST /domains/discover` (500 error) |

### Test Details

#### TC-46.5.1: Render drag-drop upload area
```typescript
test('TC-46.5.1: should render drag-drop upload area on page load', async ({ page }) => {
  await page.goto('/admin/domain-discovery');
  await expect(page.locator('[data-testid="domain-discovery-upload-area"]')).toBeVisible();
  await expect(page.locator('[data-testid="domain-discovery-file-input"]')).toHaveAttribute('type', 'file');
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-upload-area"]`
- `[data-testid="domain-discovery-file-input"]`

**Expected:** Upload area is visible with file input

---

#### TC-46.5.2: Accept TXT, MD, DOCX, HTML
```typescript
test('TC-46.5.2: should accept TXT, MD, DOCX, HTML file types', async ({ page }) => {
  const acceptAttr = await page.locator('[data-testid="domain-discovery-file-input"]').getAttribute('accept');
  expect(acceptAttr).toContain('text/plain');
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-file-input"]`

**Expected:** Accept attribute includes supported formats

---

#### TC-46.5.3: Reject unsupported files
```typescript
test('TC-46.5.3: should reject unsupported file types', async ({ page }) => {
  await page.route('**/api/v1/admin/domains/discover', (route) => {
    route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Unsupported file type' }),
    });
  });
  // Upload PNG and verify error or rejection
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-upload-area"]`
- `[data-testid="domain-discovery-error"]`

**API Mock:**
- Route: `POST /api/v1/admin/domains/discover`
- Status: 400 Bad Request

---

#### TC-46.5.4: Error on >3 files
```typescript
test('TC-46.5.4: should show error when >3 files selected', async ({ page }) => {
  // Upload 4 files
  const errorMessage = page.locator('[data-testid="domain-discovery-max-files-error"]');
  const errorVisible = await errorMessage.isVisible().catch(() => false);
  expect(errorVisible || await analyzeButton.isDisabled()).toBeTruthy();
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-upload-area"]`
- `[data-testid="domain-discovery-max-files-error"]`
- `[data-testid="domain-discovery-analyze-button"]`

**Expected:** Error message or button disabled

---

#### TC-46.5.5: Loading state on analyze
```typescript
test('TC-46.5.5: should trigger loading state when analyze button clicked', async ({ page }) => {
  // Setup mock with 500ms delay
  await page.route('**/api/v1/admin/domains/discover', async (route) => {
    await new Promise(resolve => setTimeout(resolve, 500));
    route.fulfill({ status: 200, /* ... */ });
  });

  const loadingSpinner = page.locator('[data-testid="domain-discovery-loading"]');
  const spinnerVisible = await loadingSpinner.isVisible().catch(() => false);
  const isDisabled = await analyzeButton.isDisabled();
  expect(spinnerVisible && isDisabled).toBeTruthy();
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-analyze-button"]`
- `[data-testid="domain-discovery-loading"]`

**API Mock:** 500ms delay on POST /api/v1/admin/domains/discover

---

#### TC-46.5.6: Show suggestion after analysis
```typescript
test('TC-46.5.6: should show suggestion after analysis completes', async ({ page }) => {
  await page.route('**/api/v1/admin/domains/discover', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        title: 'Technical Documentation',
        description: 'Tech docs...',
        confidence: 0.85,
        detected_topics: ['Python', 'API', 'Documentation'],
      }),
    });
  });

  const suggestionPanel = page.locator('[data-testid="domain-discovery-suggestion"]');
  await expect(suggestionPanel).toBeVisible({ timeout: 10000 });
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-analyze-button"]`
- `[data-testid="domain-discovery-suggestion"]`
- `[data-testid="domain-discovery-suggestion-title"]`
- `[data-testid="domain-discovery-suggestion-description"]`
- `[data-testid="domain-discovery-suggestion-confidence"]`

**API Mock:**
- Endpoint: `POST /api/v1/admin/domains/discover`
- Response: `{ title, description, confidence, detected_topics }`

---

#### TC-46.5.7: Edit and accept suggestion
```typescript
test('TC-46.5.7: should allow editing and accepting suggestion', async ({ page }) => {
  // Upload, analyze, then edit and accept
  const descriptionEditField = page.locator('[data-testid="domain-discovery-suggestion-description-edit"]');
  await descriptionEditField.fill('Custom edited description');

  const acceptButton = page.locator('[data-testid="domain-discovery-accept-button"]');
  await acceptButton.click();

  const successMessage = page.locator('[data-testid="domain-discovery-success"]');
  await expect(successMessage).toBeVisible({ timeout: 5000 });
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-suggestion"]`
- `[data-testid="domain-discovery-suggestion-description-edit"]`
- `[data-testid="domain-discovery-accept-button"]`
- `[data-testid="domain-discovery-success"]`

**API Mocks:**
- POST /api/v1/admin/domains/discover (suggest)
- POST /api/v1/admin/domains (create)

---

#### TC-46.5.8: Multiple files for accuracy
```typescript
test('TC-46.5.8: should handle multiple files for more accurate discovery', async ({ page }) => {
  // Upload 2 files
  const fileList = page.locator('[data-testid="domain-discovery-file-list"]');
  const fileItems = page.locator('[data-testid="domain-discovery-file-item"]');
  expect(await fileItems.count()).toBe(2);

  // Analyze should work with multiple files
  const analyzeButton = page.locator('[data-testid="domain-discovery-analyze-button"]');
  expect(await analyzeButton.isDisabled()).toBeFalsy();
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-upload-area"]`
- `[data-testid="domain-discovery-file-list"]`
- `[data-testid="domain-discovery-file-item"]`
- `[data-testid="domain-discovery-analyze-button"]`

---

#### TC-46.5.9: Clear files and reset
```typescript
test('TC-46.5.9: should clear files and start over', async ({ page }) => {
  // Upload file, then click clear
  const clearButton = page.locator('[data-testid="domain-discovery-clear-button"]');
  await clearButton.click();

  const fileCount = await page.locator('[data-testid="domain-discovery-file-input"]')
    .evaluate((el: HTMLInputElement) => el.files?.length || 0);
  expect(fileCount).toBe(0);
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-clear-button"]`
- `[data-testid="domain-discovery-file-input"]`
- `[data-testid="domain-discovery-upload-area"]`

---

#### TC-46.5.10: Handle API errors
```typescript
test('TC-46.5.10: should handle API errors gracefully', async ({ page }) => {
  await page.route('**/api/v1/admin/domains/discover', (route) => {
    route.fulfill({
      status: 500,
      body: JSON.stringify({ error: 'Internal server error' }),
    });
  });

  const errorMessage = page.locator('[data-testid="domain-discovery-error"]');
  const errorVisible = await errorMessage.isVisible({ timeout: 5000 }).catch(() => false);
  expect(errorVisible).toBeTruthy();

  // Button should be re-enabled for retry
  const isDisabled = await analyzeButton.isDisabled();
  expect(isDisabled).toBeFalsy();
});
```

**Selectors Used:**
- `[data-testid="domain-discovery-analyze-button"]`
- `[data-testid="domain-discovery-error"]`

**API Mock:** 500 Internal Server Error

---

## Feature 46.8 - Admin Dashboard (15 tests)

**File:** `frontend/e2e/admin/admin-dashboard.spec.ts`

### Test Case Reference

| # | Test ID | Test Name | Category | Assertions | API Endpoints |
|---|---------|-----------|----------|-----------|---------------|
| 1 | TC-46.8.1 | Load at /admin | Nav | Heading visible, URL correct | - |
| 2 | TC-46.8.2 | Domain section | UI | Section visible, list items | `GET /dashboard/stats`, `GET /domains` |
| 3 | TC-46.8.3 | Indexing stats | UI | Section visible, stat values | `GET /indexing/stats` |
| 4 | TC-46.8.4 | Settings section | UI | Section visible, config items | `GET /settings` |
| 5 | TC-46.8.5 | Headers clickable | Interact | Has click handler or button role | - |
| 6 | TC-46.8.6 | Toggle collapse | Interact | Content visibility changes | - |
| 7 | TC-46.8.7 | Nav links work | Nav | Links have href, navigate | - |
| 8 | TC-46.8.8 | Loading state | UX | Spinner visible initially | `GET /dashboard/stats` |
| 9 | TC-46.8.9 | Stat cards | UI | Cards visible, values shown | `GET /dashboard/stats` |
| 10 | TC-46.8.10 | Refresh stats | Interact | Data updated on refresh | `GET /dashboard/stats` |
| 11 | TC-46.8.11 | Missing sections | Error | Graceful handling | `GET /api/v1/admin/**` (empty) |
| 12 | TC-46.8.12 | API errors | Error | Error message shown | `GET /dashboard/stats` (500) |
| 13 | TC-46.8.13 | User info | UI | Profile/badge visible | - |
| 14 | TC-46.8.14 | Mobile responsive | RWD | Renders at 375x812 | All endpoints |
| 15 | TC-46.8.15 | Last update | UI | Timestamp displayed | `GET /dashboard/stats` |

### Selector Reference

#### Section Headers
```typescript
'[data-testid="dashboard-section-domains"]'
'[data-testid="dashboard-section-indexing"]'
'[data-testid="dashboard-section-settings"]'
'[data-testid="dashboard-section-header-domains"]'
'[data-testid="dashboard-section-header-indexing"]'
```

#### Content Areas
```typescript
'[data-testid="dashboard-section-content-domains"]'
'[data-testid="dashboard-domain-list"]'
'[data-testid="dashboard-domain-item"]'
'[data-testid="dashboard-stat-card"]'
'[data-testid="dashboard-indexing-stat"]'
'[data-testid="dashboard-setting-item"]'
```

#### UI Elements
```typescript
'[data-testid="dashboard-loading"]'
'[data-testid="dashboard-error"]'
'[data-testid="dashboard-refresh-button"]'
'[data-testid="dashboard-nav-link"]'
'[data-testid="dashboard-last-updated"]'
'[data-testid="user-profile"]'
'[data-testid="user-badge"]'
```

---

## Test Categories

### By Type

#### UI Rendering Tests (10)
- TC-46.5.1, TC-46.5.2
- TC-46.8.2, TC-46.8.3, TC-46.8.4, TC-46.8.9, TC-46.8.13, TC-46.8.14, TC-46.8.15

#### Input/Validation Tests (2)
- TC-46.5.2, TC-46.5.4

#### Error Handling Tests (5)
- TC-46.5.3, TC-46.5.10
- TC-46.8.11, TC-46.8.12

#### Interactivity Tests (3)
- TC-46.8.5, TC-46.8.6, TC-46.8.10

#### API Integration Tests (3)
- TC-46.5.6, TC-46.5.7, TC-46.8.10

#### UX Tests (2)
- TC-46.5.5, TC-46.8.8

#### Navigation Tests (2)
- TC-46.8.1, TC-46.8.7

#### Workflow Tests (1)
- TC-46.5.7

### By Feature

#### Feature 46.5: Domain Auto Discovery
Tests 1-10: Upload, validation, analysis, suggestion, acceptance

#### Feature 46.8: Admin Dashboard
Tests 1-15: Dashboard loading, sections, stats, refresh, errors

---

## API Endpoints by Test

### Feature 46.5 API Routes

| Endpoint | Method | Tests | Mock Response |
|----------|--------|-------|---------------|
| `/api/v1/admin/domains/discover` | POST | TC-46.5.3, 5, 6, 7, 8, 10 | `{title, description, confidence, detected_topics}` |
| `/api/v1/admin/domains` | POST | TC-46.5.7 | `{id, title, description, created_at}` |

### Feature 46.8 API Routes

| Endpoint | Method | Tests | Mock Response |
|----------|--------|-------|---------------|
| `/api/v1/admin/dashboard/stats` | GET | TC-46.8.2, 8, 9, 10, 12, 15 | `{total_domains, active_domains, documents, embeddings, last_updated}` |
| `/api/v1/admin/domains` | GET | TC-46.8.2 | `{domains: [...]}`  |
| `/api/v1/admin/indexing/stats` | GET | TC-46.8.3 | `{documents_indexed, processing, chunks, speed}` |
| `/api/v1/admin/settings` | GET | TC-46.8.4 | `{embedding_model, chunk_size, enable_auto_discovery, ...}` |

---

## Element Selectors Reference

### Feature 46.5 Selectors

```typescript
// Upload area
'[data-testid="domain-discovery-upload-area"]'
'[data-testid="domain-discovery-file-input"]'
'[data-testid="domain-discovery-file-list"]'
'[data-testid="domain-discovery-file-item"]'
'[data-testid="domain-discovery-clear-button"]'

// Analysis
'[data-testid="domain-discovery-analyze-button"]'
'[data-testid="domain-discovery-loading"]'

// Errors
'[data-testid="domain-discovery-error"]'
'[data-testid="domain-discovery-max-files-error"]'

// Suggestion
'[data-testid="domain-discovery-suggestion"]'
'[data-testid="domain-discovery-suggestion-title"]'
'[data-testid="domain-discovery-suggestion-description"]'
'[data-testid="domain-discovery-suggestion-description-edit"]'
'[data-testid="domain-discovery-suggestion-confidence"]'
'[data-testid="domain-discovery-accept-button"]'
'[data-testid="domain-discovery-success"]'
```

### Feature 46.8 Selectors

```typescript
// Sections
'[data-testid="dashboard-section-domains"]'
'[data-testid="dashboard-section-indexing"]'
'[data-testid="dashboard-section-settings"]'
'[data-testid="dashboard-section-header-domains"]'
'[data-testid="dashboard-section-header-indexing"]'
'[data-testid="dashboard-section-content-domains"]'

// Content
'[data-testid="dashboard-domain-list"]'
'[data-testid="dashboard-domain-item"]'
'[data-testid="dashboard-stat-card"]'
'[data-testid="dashboard-indexing-stat"]'
'[data-testid="dashboard-setting-item"]'

// State
'[data-testid="dashboard-loading"]'
'[data-testid="dashboard-error"]'
'[data-testid="dashboard-refresh-button"]'
'[data-testid="dashboard-last-updated"]'

// Navigation
'[data-testid="dashboard-nav-link"]'

// User
'[data-testid="user-profile"]'
'[data-testid="user-badge"]'
```

---

## Quick Command Reference

```bash
# Run all tests
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts frontend/e2e/admin/admin-dashboard.spec.ts

# Run Feature 46.5
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts

# Run Feature 46.8
npx playwright test frontend/e2e/admin/admin-dashboard.spec.ts

# Run specific test
npx playwright test -g "TC-46.5.1"
npx playwright test -g "TC-46.8.5"

# Run with UI
npx playwright test frontend/e2e/admin/ --ui

# Debug
npx playwright test frontend/e2e/admin/ --debug
```

---

**Sprint 46 Test Reference**
Last Updated: 2025-12-15
Total Tests: 25
Total Endpoints Mocked: 7
File Size: ~1000 lines
