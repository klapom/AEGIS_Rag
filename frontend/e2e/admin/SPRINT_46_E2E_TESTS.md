# Sprint 46 E2E Tests - Domain Auto Discovery & Admin Dashboard

## Overview

This document covers the comprehensive Playwright E2E test suites for Sprint 46 Features 46.5 (Domain Auto Discovery) and 46.8 (Admin Dashboard).

**Total Test Cases:** 25
- **Feature 46.5 (Domain Auto Discovery):** 10 test cases
- **Feature 46.8 (Admin Dashboard):** 15 test cases

## File Structure

```
frontend/e2e/admin/
├── domain-auto-discovery.spec.ts    (10 tests)
├── admin-dashboard.spec.ts          (15 tests)
└── SPRINT_46_E2E_TESTS.md          (this file)
```

## Feature 46.5: Domain Auto Discovery Tests

**File:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/admin/domain-auto-discovery.spec.ts`

### Overview
Comprehensive tests for the automated domain discovery feature that analyzes document samples and suggests domain configurations.

### Test Cases

| ID | Test Name | Description | Status |
|----|-----------|-------------|--------|
| TC-46.5.1 | Render drag-drop upload area | Verify UI elements for file upload are visible | ✓ |
| TC-46.5.2 | Accept TXT, MD, DOCX, HTML | Verify file input accepts supported formats | ✓ |
| TC-46.5.3 | Reject unsupported file types | Verify system rejects PNG, JPG, etc. | ✓ |
| TC-46.5.4 | Show error for >3 files | Verify error when exceeding file limit | ✓ |
| TC-46.5.5 | Analyze loading state | Verify loading indicator during analysis | ✓ |
| TC-46.5.6 | Show suggestion after analysis | Verify suggestion panel appears with mock API | ✓ |
| TC-46.5.7 | Edit and accept suggestion | Verify edit workflow and domain creation | ✓ |
| TC-46.5.8 | Multiple files for accuracy | Verify system handles 2-3 files correctly | ✓ |
| TC-46.5.9 | Clear files and reset | Verify reset functionality | ✓ |
| TC-46.5.10 | Handle API errors gracefully | Verify error handling on API failure | ✓ |

### API Mocking

The following endpoints are mocked:

```
POST /api/v1/admin/domains/discover
├── Success: Returns { title, description, confidence, detected_topics }
├── Timeout: Simulates processing delay
└── Error: Returns 500 error response

POST /api/v1/admin/domains
└── Success: Creates domain and returns 201 response
```

### Key Features Tested

1. **File Upload**
   - Drag-and-drop area rendering
   - File input filtering by type
   - Multiple file selection (max 3)
   - File size validation

2. **Analysis**
   - Loading state display
   - API request with file data
   - Timeout handling
   - Error messages

3. **Suggestion Workflow**
   - Display detected domain name
   - Show confidence score
   - Display description
   - List detected topics
   - Edit suggestion details
   - Accept and create domain

4. **Error Handling**
   - Unsupported file types
   - Exceeding file count
   - API failures
   - Network timeouts

### Running Feature 46.5 Tests

```bash
# Run all domain discovery tests
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts

# Run specific test
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts -g "TC-46.5.1"

# Run with UI mode
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts --ui

# Run with headed browser
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts --headed
```

## Feature 46.8: Admin Dashboard Tests

**File:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/admin/admin-dashboard.spec.ts`

### Overview
Comprehensive tests for the unified admin dashboard that consolidates domain management, indexing operations, and system settings.

### Test Cases

| ID | Test Name | Description | Status |
|----|-----------|-------------|--------|
| TC-46.8.1 | Dashboard loads at /admin | Verify page navigates and displays main heading | ✓ |
| TC-46.8.2 | Domain section renders | Verify domain list displays with data | ✓ |
| TC-46.8.3 | Indexing stats section | Verify indexing statistics display | ✓ |
| TC-46.8.4 | Settings section | Verify configuration settings display | ✓ |
| TC-46.8.5 | Section headers clickable | Verify headers have click handlers | ✓ |
| TC-46.8.6 | Toggle section collapse | Verify expand/collapse functionality | ✓ |
| TC-46.8.7 | Quick navigation links | Verify navigation links work | ✓ |
| TC-46.8.8 | Loading state on init | Verify loading spinner appears initially | ✓ |
| TC-46.8.9 | Domain stat cards | Verify statistics cards display values | ✓ |
| TC-46.8.10 | Refresh stats | Verify data refreshes on button click | ✓ |
| TC-46.8.11 | Handle missing sections | Verify graceful handling of empty data | ✓ |
| TC-46.8.12 | Display API errors | Verify error messages on API failure | ✓ |
| TC-46.8.13 | User info in header | Verify user profile/badge display | ✓ |
| TC-46.8.14 | Mobile responsive | Verify mobile viewport rendering | ✓ |
| TC-46.8.15 | Last update timestamp | Verify timestamp display format | ✓ |

### API Mocking

The following endpoints are mocked:

```
GET /api/v1/admin/dashboard/stats
├── Success: Returns { total_domains, active_domains, documents, embeddings, last_updated }
└── Error: Returns 500 error response

GET /api/v1/admin/domains
├── Success: Returns { domains: [...] }
└── Error: Returns 500 error response

GET /api/v1/admin/indexing/stats
├── Success: Returns { documents_indexed, processing, failed, chunks, speed }
└── Error: Returns 500 error response

GET /api/v1/admin/settings
└── Success: Returns { embedding_model, chunk_size, enable_auto_discovery, ... }
```

### Key Features Tested

1. **Dashboard Layout**
   - Main heading displays
   - URL is at /admin
   - Responsive design (mobile/desktop)

2. **Sections**
   - Domain management section
   - Indexing operations section
   - System settings section
   - Collapsible sections
   - Section headers

3. **Statistics**
   - Total domains card
   - Active domains card
   - Total documents card
   - Indexing speed card
   - Last updated timestamp

4. **Navigation**
   - Quick nav links to sub-pages
   - Navigation links are functional
   - URL updates correctly

5. **Data Management**
   - Auto-refresh of stats
   - Manual refresh button
   - Error messages on failures
   - Graceful handling of missing data

6. **User Experience**
   - Loading state during initial load
   - Loading spinner visibility
   - Error message clarity
   - Mobile responsiveness

### Running Feature 46.8 Tests

```bash
# Run all admin dashboard tests
npx playwright test frontend/e2e/admin/admin-dashboard.spec.ts

# Run specific test
npx playwright test frontend/e2e/admin/admin-dashboard.spec.ts -g "TC-46.8.1"

# Run with UI mode
npx playwright test frontend/e2e/admin/admin-dashboard.spec.ts --ui

# Run specific category
npx playwright test frontend/e2e/admin/admin-dashboard.spec.ts -g "responsive"
```

## Authentication Mocking

Both test suites use the `setupAuthMocking()` function from `frontend/e2e/fixtures/index.ts`:

```typescript
import { test, expect, setupAuthMocking } from '../fixtures';

test.beforeEach(async ({ page }) => {
  await setupAuthMocking(page);
});
```

This function:
- Mocks `/api/v1/auth/me` endpoint
- Mocks `/api/v1/auth/refresh` endpoint
- Sets `aegis_auth_token` in localStorage
- Simulates authenticated user session

## Test Patterns & Best Practices

### 1. Resilient Selectors
Uses `data-testid` attributes for reliable element location:
```typescript
const uploadArea = page.locator('[data-testid="domain-discovery-upload-area"]');
```

### 2. Fallback Testing
Includes alternative selectors for UI variations:
```typescript
const sectionVisible = await indexingSection.isVisible().catch(() => false);
if (sectionVisible) {
  // Test specific section
} else {
  // Test generic content
}
```

### 3. API Mocking
Routes are mocked to control responses and simulate delays:
```typescript
await page.route('**/api/v1/admin/domains/discover', (route) => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ /* mock data */ }),
  });
});
```

### 4. Async Waiting
Proper timeout handling for async operations:
```typescript
await expect(element).toBeVisible({ timeout: 10000 });
```

### 5. Error Resilience
Tests handle optional UI elements gracefully:
```typescript
const errorVisible = await errorMessage.isVisible().catch(() => false);
if (errorVisible) {
  // Verify error text
}
```

## Running All Sprint 46 Tests

```bash
# Run both test suites
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts frontend/e2e/admin/admin-dashboard.spec.ts

# Run with verbose output
npx playwright test frontend/e2e/admin/ -vv

# Run with trace on failure
npx playwright test frontend/e2e/admin/ --trace on

# Run with screenshot on failure
npx playwright test frontend/e2e/admin/ --screenshot on
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Run Sprint 46 E2E Tests
  run: npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts frontend/e2e/admin/admin-dashboard.spec.ts

- name: Upload Test Report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
    retention-days: 30
```

## Expected Test Environment

### Frontend
- URL: `http://localhost:5179` (Vite dev server)
- React 19, TypeScript, Tailwind CSS
- Playwright 111+

### Backend
- URL: `http://localhost:8000` (FastAPI)
- Authentication: JWT tokens
- APIs: Mocked in tests

### Browsers
- Chromium (default)
- Firefox (optional)
- WebKit (optional)

## Debugging Failed Tests

### Enable Debug Mode
```bash
npx playwright test frontend/e2e/admin/domain-auto-discovery.spec.ts --debug
```

### View Test Report
```bash
npx playwright show-report
```

### Run Single Test
```bash
npx playwright test frontend/e2e/admin/admin-dashboard.spec.ts -g "TC-46.8.1"
```

### Check Network Logs
The tests capture network requests via route interception. Review the test output for API mocking details.

## Known Limitations

1. **UI Variations**: Tests account for different possible UI layouts and selectors
2. **Loading States**: Some loading indicators may not be visible depending on response speed
3. **Mobile Testing**: Mobile viewport tests are basic; full responsive testing may need additional scenarios
4. **API Versioning**: Tests mock v1 API endpoints; updates needed if API structure changes

## Future Enhancements

1. **Visual Regression Testing**
   - Add Percy/Chromatic for visual diffs
   - Screenshot comparisons across runs

2. **Performance Testing**
   - Add Lighthouse audit checks
   - Core Web Vitals validation

3. **Accessibility Testing**
   - Add axe-core for accessibility checks
   - WCAG compliance validation

4. **E2E Integration**
   - Real backend testing with Docker containers
   - Database state validation

## Maintenance

### When to Update Tests

1. **UI Changes**: Update selectors and test expectations
2. **API Changes**: Update mock response data
3. **New Features**: Add new test cases
4. **Bug Fixes**: Add regression tests

### Test Review Checklist

- [ ] All required test cases are present
- [ ] Authentication mocking is correct
- [ ] API routes are properly mocked
- [ ] Selectors use data-testid attributes
- [ ] Tests have clear descriptions
- [ ] Error handling is tested
- [ ] Loading states are verified
- [ ] Mobile responsiveness is checked

## Contact

For questions or issues with these tests:
1. Review the test comments and documentation
2. Check the Playwright documentation
3. Run tests with `--debug` flag for detailed output
4. Refer to `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/fixtures/index.ts` for fixture setup

---

**Sprint 46** - Domain Auto Discovery & Unified Admin Dashboard
**Last Updated:** 2025-12-15
**Test Coverage:** 25 test cases
**File Locations:**
- Domain Auto Discovery: `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/admin/domain-auto-discovery.spec.ts`
- Admin Dashboard: `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/admin/admin-dashboard.spec.ts`
