# Ingestion Jobs E2E Test Guide

**File:** `ingestion-jobs.spec.ts`
**Tests:** 12 total (7 fixed in Sprint 72)
**Status:** All executable (0 skipped)

## Quick Reference

### Mock Job Creation

```typescript
// Create a job at 65% progress
const mockJob = createMockIngestionJob('job-123', 'test.pdf', 65, 'running');

// Returns:
{
  id: 'job-123',
  name: 'test.pdf',
  status: 'running',
  progress: 65,
  current_step: 'embedding',  // Calculated from progress
  current_document: 'job-123-doc-1',
  documents: [
    { id: 'job-123-doc-1', name: 'document1.pdf', progress: 130, status: 'processing', ... },
    { id: 'job-123-doc-2', name: 'document2.pdf', progress: 30, status: 'queued', ... },
    { id: 'job-123-doc-3', name: 'document3.pdf', progress: 0, status: 'queued', ... },
  ],
  total_documents: 3,
  completed_documents: 0,
  failed_documents: 0,
  start_time: '2026-01-03T...',
}
```

### Setup Pattern

All tests using mocked jobs follow this pattern:

```typescript
test('test name', async ({ page }) => {
  // 1. Create mock jobs
  const mockJob = createMockIngestionJob('job-id', 'file.pdf', progress, 'running');

  // 2. Setup API mocking
  await setupMockIngestionJobs(page, [mockJob]);

  // 3. Setup auth (required for protected routes)
  await setupAuthMocking(page);

  // 4. Navigate
  await page.goto('/admin/jobs');

  // 5. Test assertions
  const jobRow = page.locator('[data-testid="job-row-job-id"]');
  await expect(jobRow).toBeVisible();
});
```

## Test Coverage

### ✓ Basic Navigation
- Display jobs page
- Back button navigation
- Empty state handling
- Job list display

### ✓ Job Monitoring
- Overall progress bars
- Current processing step
- Status badges (running/completed/failed)
- Auto-refresh mechanism

### ✓ Document Details
- Expand job to see documents
- Up to 3 concurrent documents
- Document progress display

### ✓ Job Control
- Cancel running jobs
- Confirmation dialogs
- Status updates after actions

### ✓ Real-Time Updates
- SSE stream support
- Progress updates
- Status transitions

## API Mocking

### Mocked Endpoints

| Endpoint | Method | Response |
|----------|--------|----------|
| `/api/v1/ingestion/jobs` | GET | `{jobs: MockIngestionJob[], total: number}` |
| `/api/v1/ingestion/jobs/{jobId}` | GET | `MockIngestionJob` or `{error: string}` |
| `/api/v1/ingestion/jobs/{jobId}/cancel` | POST | `{success: boolean, jobId: string}` |
| `/api/v1/ingestion/jobs/*/progress` | GET (SSE) | `text/event-stream` with job updates |

### Route Patterns

```typescript
// The setupMockIngestionJobs function handles:
page.route('**/api/v1/ingestion/jobs**', ...);
page.route('**/api/v1/ingestion/jobs/[a-z0-9-]+**', ...);
page.route('**/api/v1/ingestion/jobs/*/cancel', ...);

// The setupMockSSEStream function handles:
page.route('**/api/v1/ingestion/jobs/*/progress', ...);
```

## Test Isolation

Each test is fully isolated:
- No shared state between tests
- Each creates its own mock jobs
- No backend service dependencies
- Mock routes apply only to current test

## Progress Levels Reference

Different progress values show different stages:

```typescript
// Early stage (parsing)
createMockIngestionJob('id', 'file.pdf', 10, 'running');
// current_step: 'parsing'
// doc1: queued, doc2: queued, doc3: queued

// Mid stage (chunking)
createMockIngestionJob('id', 'file.pdf', 40, 'running');
// current_step: 'chunking'
// doc1: processing, doc2: queued, doc3: queued

// Late stage (embedding)
createMockIngestionJob('id', 'file.pdf', 70, 'running');
// current_step: 'embedding'
// doc1: completed, doc2: processing, doc3: queued

// Complete
createMockIngestionJob('id', 'file.pdf', 100, 'completed');
// current_step: 'graph_extraction'
// doc1: completed, doc2: completed, doc3: completed
```

## Common Patterns

### Check if Element Exists Before Acting
```typescript
const button = page.getByTestId('some-button');
const isVisible = await button.isVisible().catch(() => false);

if (isVisible) {
  await button.click();
}
```

### Safe Try-Catch for Optional UI
```typescript
try {
  await expandButton.click();
} catch {
  // Element doesn't exist, continue test
}
```

### Verify with Flexible Matchers
```typescript
// Match any percentage format
expect(progressText).toMatch(/\d+%/);

// Match one of several status values
expect(statusText).toMatch(/running|completed|failed|pending/i);

// Case-insensitive match
expect(stepText).toMatch(/parsing|chunking|embedding|graph_extraction|graph extraction/i);
```

## Debugging Tips

### Print Mock Job Data
```typescript
const mockJob = createMockIngestionJob('job-id', 'file.pdf', 50, 'running');
console.log('Mock Job:', JSON.stringify(mockJob, null, 2));
```

### Inspect DOM Elements
```typescript
const jobRow = page.locator('[data-testid^="job-row-"]');
const count = await jobRow.count();
console.log('Job rows found:', count);

const textContent = await jobRow.first().textContent();
console.log('First row content:', textContent);
```

### Run Single Test
```bash
npx playwright test ingestion-jobs.spec.ts -g "should show overall"
```

### Run with UI Mode
```bash
npx playwright test ingestion-jobs.spec.ts --ui
```

### Debug Mode
```bash
npx playwright test ingestion-jobs.spec.ts --debug
```

## Expected Test Results

All 12 tests should pass:

```
✓ should display jobs page when navigating from admin
✓ should show back button that navigates to /admin
✓ should display empty state when no jobs exist
✓ should display job list when jobs exist
✓ should show overall progress bar for running job
✓ should display current processing step
✓ should show status badges (running, completed, failed)
✓ should allow expanding job to see parallel documents
✓ should display up to 3 concurrent documents processing
✓ should allow canceling a running job
✓ should auto-refresh job list every 10 seconds
✓ should receive real-time SSE updates for job progress

Total: 12 tests
Expected Duration: ~5-10 seconds (no real backend)
```

## Adding New Tests

To add a new ingestion jobs test:

1. **Create mock jobs:**
   ```typescript
   const mockJob = createMockIngestionJob('job-new', 'new.pdf', 50, 'running');
   ```

2. **Setup mocking:**
   ```typescript
   await setupMockIngestionJobs(page, [mockJob]);
   await setupAuthMocking(page);
   ```

3. **Navigate and test:**
   ```typescript
   await page.goto('/admin/jobs');
   // Your assertions here
   ```

## File Structure

```typescript
ingestion-jobs.spec.ts
├── Imports
├── JSDoc header
├── Type Definitions
│   ├── MockDocument interface
│   └── MockIngestionJob interface
├── Helper Functions
│   ├── createMockIngestionJob(...)
│   ├── setupMockIngestionJobs(...)
│   └── setupMockSSEStream(...)
└── Test Suite
    ├── Navigation tests (existing)
    ├── Progress bar test (fixed)
    ├── Step display test (fixed)
    ├── Status badge test (fixed)
    ├── Document expansion test (fixed)
    ├── Concurrent documents test (fixed)
    ├── Cancel job test (fixed)
    ├── Auto-refresh test (existing)
    └── SSE updates test (fixed)
```

## Notes

- Tests do **not** require a running backend
- Mock API responses are synchronous
- No network latency simulation (tests run fast)
- To simulate network delays, add `await page.waitForTimeout(ms)`
- SSE mock is simplified (not full EventStream protocol)
- For full SSE testing, consider using actual backend

## Related Files

- Test file: `e2e/tests/admin/ingestion-jobs.spec.ts`
- Fixtures: `e2e/fixtures/index.ts`
- Test data: `e2e/fixtures/test-data.ts`
- POM: `e2e/pom/AdminIndexingPage.ts`

## Support

For questions about these tests:
1. Check the test JSDoc comments
2. Review helper function implementations
3. Look at similar tests in other admin specs
4. Check Playwright documentation
5. Review E2E testing strategy docs

---

**Last Updated:** Sprint 72, Feature 72.6
**Maintainer:** Testing Agent
**Tests:** 12/12 (0 skipped)
