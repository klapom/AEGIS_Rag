# Sprint 46 E2E Tests - Quick Start Guide

## One-Line Summary
**25 comprehensive Playwright E2E tests for Domain Auto Discovery (46.5) and Admin Dashboard (46.8) with full API mocking and authentication support.**

## Quick Reference

### Test Files Location
```
/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/admin/
├── domain-auto-discovery.spec.ts    (10 tests)
├── admin-dashboard.spec.ts          (15 tests)
└── SPRINT_46_E2E_TESTS.md
```

### Run Tests Immediately

```bash
# Run all Sprint 46 tests
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts frontend/e2e/admin/admin-dashboard.spec.ts

# Run Feature 46.5 only
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts

# Run Feature 46.8 only
npx playwright test frontend/e2e/admin/admin-dashboard.spec.ts

# Run with UI (visual debugging)
npx playwright test frontend/e2e/admin/ --ui

# Run with headed browser
npx playwright test frontend/e2e/admin/ --headed

# Run single test
npx playwright test frontend/e2e/admin/admin-dashboard.spec.ts -g "TC-46.8.1"
```

## Feature 46.5: Domain Auto Discovery (10 tests)

### What It Tests
Automated domain discovery that:
- Accepts file uploads (TXT, MD, DOCX, HTML)
- Analyzes documents for domain configuration
- Suggests domain name, description, topics
- Handles errors and edge cases

### Test Cases
```
TC-46.5.1   Drag-drop upload area
TC-46.5.2   Accept TXT, MD, DOCX, HTML
TC-46.5.3   Reject unsupported files
TC-46.5.4   Error on >3 files
TC-46.5.5   Show loading during analysis
TC-46.5.6   Display suggestion with mock API
TC-46.5.7   Edit and accept suggestion
TC-46.5.8   Multiple files for accuracy
TC-46.5.9   Clear and reset
TC-46.5.10  Handle API errors
```

### Key Test Code Pattern
```typescript
test('TC-46.5.X: description', async ({ page }) => {
  await setupAuthMocking(page);  // Enable auth
  await page.goto('/admin/domain-discovery');

  // Mock API
  await page.route('**/api/v1/admin/domains/discover', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ /* mock data */ }),
    });
  });

  // Test interaction
  await page.locator('[data-testid="element"]').click();
  await expect(page.locator('[data-testid="result"]')).toBeVisible();
});
```

## Feature 46.8: Admin Dashboard (15 tests)

### What It Tests
Unified admin dashboard featuring:
- Domain management overview
- Indexing statistics
- System settings display
- Collapsible sections
- Real-time stats updates
- Error handling

### Test Cases
```
TC-46.8.1   Dashboard loads at /admin
TC-46.8.2   Domain section renders
TC-46.8.3   Indexing stats section
TC-46.8.4   Settings section
TC-46.8.5   Section headers clickable
TC-46.8.6   Toggle section collapse
TC-46.8.7   Quick navigation links
TC-46.8.8   Loading state on init
TC-46.8.9   Domain stat cards
TC-46.8.10  Refresh stats button
TC-46.8.11  Handle missing sections
TC-46.8.12  Display API errors
TC-46.8.13  User info in header
TC-46.8.14  Mobile responsive
TC-46.8.15  Last update timestamp
```

### Key Test Code Pattern
```typescript
test('TC-46.8.X: description', async ({ page }) => {
  // Mock API endpoints
  await page.route('**/api/v1/admin/dashboard/stats', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_domains: 5,
        active_domains: 3,
        // ... more stats
      }),
    });
  });

  await page.goto('/admin');

  // Verify sections render
  const section = page.locator('[data-testid="dashboard-section-domains"]');
  await expect(section).toBeVisible();
});
```

## Authentication

All tests use built-in auth mocking:

```typescript
import { test, expect, setupAuthMocking } from '../fixtures';

test.beforeEach(async ({ page }) => {
  await setupAuthMocking(page);
});
```

This automatically:
- Mocks `/api/v1/auth/me`
- Mocks `/api/v1/auth/refresh`
- Sets JWT token in localStorage
- Enables access to protected routes

## Mocked Endpoints

### Feature 46.5
```
POST /api/v1/admin/domains/discover
POST /api/v1/admin/domains
```

### Feature 46.8
```
GET /api/v1/admin/dashboard/stats
GET /api/v1/admin/domains
GET /api/v1/admin/indexing/stats
GET /api/v1/admin/settings
```

## Test Structure

All tests follow this pattern:
1. **Setup**: Mock APIs and authentication
2. **Navigate**: Go to feature route
3. **Interact**: Perform user actions
4. **Verify**: Assert expected outcomes
5. **Cleanup**: Auto-handled by Playwright

## Common Selectors

```typescript
// Data test IDs used throughout
[data-testid="domain-discovery-upload-area"]
[data-testid="domain-discovery-file-input"]
[data-testid="domain-discovery-analyze-button"]
[data-testid="domain-discovery-suggestion"]

[data-testid="dashboard-section-domains"]
[data-testid="dashboard-section-indexing"]
[data-testid="dashboard-stat-card"]
[data-testid="dashboard-loading"]
```

## Debugging

### View Test Output
```bash
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts -vv
```

### Debug Mode (Interactive)
```bash
npx playwright test frontend/e2e/admin/admin-dashboard.spec.ts --debug
```

### Generate Report
```bash
npx playwright show-report
```

### Capture Screenshots
```bash
npx playwright test frontend/e2e/admin/ --screenshot on
```

### Trace on Failure
```bash
npx playwright test frontend/e2e/admin/ --trace on
```

## Expected Prerequisites

### Frontend
- Vite dev server running on `http://localhost:5179`
- React 19 with TypeScript
- Tailwind CSS

### Backend
- FastAPI running on `http://localhost:8000`
- `/api/v1/auth/*` endpoints available
- Admin routes protected (tests mock auth)

### Dependencies
```bash
npm install --save-dev @playwright/test
npm install --save-dev @types/node
```

## File Coverage

| Feature | File | Tests | Lines of Code |
|---------|------|-------|----------------|
| 46.5 | domain-auto-discovery.spec.ts | 10 | ~350 |
| 46.8 | admin-dashboard.spec.ts | 15 | ~450 |
| **Total** | | **25** | **~800** |

## Test Execution Time

- **Single test**: ~5-10 seconds
- **Feature 46.5 (10 tests)**: ~60-80 seconds
- **Feature 46.8 (15 tests)**: ~90-120 seconds
- **Both features (25 tests)**: ~150-200 seconds

## Key Features

✓ **Full API Mocking** - No real backend calls needed
✓ **Authentication Handling** - Built-in admin auth support
✓ **Error Scenarios** - Tests error paths and edge cases
✓ **Mobile Testing** - Includes responsive design checks
✓ **Resilient Selectors** - Uses data-testid for stability
✓ **Comprehensive Coverage** - 25 test cases covering all major flows
✓ **Well Documented** - Each test has clear description
✓ **Fallback Testing** - Handles UI variations gracefully

## Common Issues & Solutions

### Tests Timeout
```bash
# Increase timeout in playwright.config.ts
timeout: 30000  // 30 seconds
```

### Element Not Found
```bash
# Use appropriate waits
await expect(element).toBeVisible({ timeout: 10000 });
```

### Auth Mocking Issues
```bash
# Ensure setupAuthMocking is in beforeEach
test.beforeEach(async ({ page }) => {
  await setupAuthMocking(page);
});
```

### API Route Not Mocked
```bash
# Check route patterns match exactly
await page.route('**/api/v1/admin/**', (route) => {
  // Ensure pattern matches your API calls
});
```

## Next Steps

1. **Run the tests** - Execute immediately to verify setup
2. **Review output** - Check console and test report
3. **Debug failures** - Use `--debug` flag for issues
4. **Add more tests** - Extend coverage as needed
5. **Integrate CI/CD** - Add to your pipeline

## Documentation

For detailed information, see:
- Full docs: `SPRINT_46_E2E_TESTS.md`
- Fixtures: `frontend/e2e/fixtures/index.ts`
- Base page: `frontend/e2e/pom/BasePage.ts`
- Playwright docs: https://playwright.dev

## Test Markers/Tags

Tests use naming convention for easy filtering:

```bash
# Run tests by feature
npx playwright test -g "46.5"      # Domain Auto Discovery
npx playwright test -g "46.8"      # Admin Dashboard

# Run by test type
npx playwright test -g "loading"   # Loading state tests
npx playwright test -g "error"     # Error handling tests
```

---

**Sprint 46 E2E Tests Quick Start**
Created: 2025-12-15
Tests: 25 comprehensive test cases
Coverage: Domain Auto Discovery + Admin Dashboard
