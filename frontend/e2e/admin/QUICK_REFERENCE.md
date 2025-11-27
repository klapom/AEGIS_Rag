# Sprint 33 E2E Tests - Quick Reference

## Test File Location
```
C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\frontend\e2e\admin\indexing.spec.ts
```

## Test Statistics

| Metric | Value |
|--------|-------|
| Total Tests | 37 |
| Test Groups | 6 |
| Features Covered | 6 (31.7, 33.1-33.5) |
| Estimated Duration | 15-25 minutes |
| Page Object Methods | 30+ |
| Data-TestID Selectors | 25+ |

## Run Commands

```bash
# Full suite
npm run test:e2e -- e2e/admin/indexing.spec.ts

# By feature
npm run test:e2e -- e2e/admin/indexing.spec.ts -g "Feature 33.1"
npm run test:e2e -- e2e/admin/indexing.spec.ts -g "Feature 33.2"
npm run test:e2e -- e2e/admin/indexing.spec.ts -g "Feature 33.3"
npm run test:e2e -- e2e/admin/indexing.spec.ts -g "Feature 33.4"
npm run test:e2e -- e2e/admin/indexing.spec.ts -g "Feature 33.5"

# Debug mode
npm run test:e2e -- e2e/admin/indexing.spec.ts --debug

# HTML report
npm run test:e2e -- e2e/admin/indexing.spec.ts --reporter=html
open playwright-report/index.html
```

## Test Summary

### Feature 33.1 - Directory Selection (5 tests, 1-2 min)
- Display input field
- Show default path
- Enable button on input
- Display recursive checkbox
- Handle files

### Feature 33.2 - File Colors (3 tests, 1-2 min)
- Display statistics
- Display file list
- Support selection controls

### Feature 33.3 - Progress (5 tests, 2-3 min)
- Display current file
- Display page numbers
- Calculate ETA
- Show progress bar

### Feature 33.4 - Details (7 tests, 3-5 min)
- Show Details button
- Open dialog
- Show page preview
- Show VLM images
- Show pipeline status
- Show entities

### Feature 33.5 - Errors (7 tests, 2-3 min)
- Show error button
- Show error badge
- Open error dialog
- Display error list
- CSV export
- Error categorization

### Feature 31.7 - Legacy (10 tests, 5-10 min)
- Display interface
- Handle invalid paths
- Cancel indexing
- Progress tracking
- Count display
- Success messages
- Advanced options
- Admin access
- Statistics

## Key Data-TestID Attributes

### Must Implement (Critical)
```
[data-testid="directory-input"]
[data-testid="start-indexing"]
[data-testid="progress-bar"]
[data-testid="progress-percentage"]
[data-testid="error-button"]
[data-testid="error-count-badge"]
```

### Important
```
[data-testid="file-list"]
[data-testid="scan-statistics"]
[data-testid="indexed-count"]
[data-testid="current-file"]
[data-testid="error-dialog"]
[data-testid="error-list"]
```

### Optional
```
[data-testid="recursive-checkbox"]
[data-testid="select-all"]
[data-testid="detail-dialog"]
[data-testid="detail-page-preview"]
[data-testid="error-export-csv"]
```

## Main POM Methods

```typescript
// Setup
await adminIndexingPage.goto()
await adminIndexingPage.setDirectoryPath(path)

// Actions
await adminIndexingPage.startIndexing()
await adminIndexingPage.cancelIndexing()
await adminIndexingPage.openDetailDialog()
await adminIndexingPage.openErrorDialog()
await adminIndexingPage.selectFile(name, selected)

// Queries
await adminIndexingPage.getProgressPercentage()
await adminIndexingPage.getProgressDetails()
await adminIndexingPage.getFileList()
await adminIndexingPage.getErrorCount()
await adminIndexingPage.getErrorList()
await adminIndexingPage.getSelectedFiles()

// Checks
await adminIndexingPage.isProgressVisible()
await adminIndexingPage.isIndexingInProgress()
await adminIndexingPage.isAdminAccessible()
```

## Prerequisites

1. Backend running: `poetry run python -m src.api.main`
2. Frontend running: `npm run dev`
3. Optional: Set `TEST_DOCUMENTS_PATH` env var

## Expected Results

### Success
- All 37 tests pass
- HTML report generated
- No console errors
- All features validated

### Partial Success
- Tests gracefully skip if features not implemented
- Core functionality (31.7) must pass
- New features (33.1-33.5) can gracefully degrade

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Timeout | Increase timeouts in AdminIndexingPage, check backend health |
| Element not found | Verify data-testid attributes match, check CSS |
| Backend error | Ensure `http://localhost:8000/health` responds |
| Directory not found | Use `TEST_DOCUMENTS_PATH` env var or create test docs |

## Files

| File | Purpose | Status |
|------|---------|--------|
| `indexing.spec.ts` | Test specs | CREATED |
| `AdminIndexingPage.ts` | POM | ENHANCED |
| `SPRINT_33_TESTS.md` | Full guide | CREATED |
| `IMPLEMENTATION_SUMMARY.md` | Details | CREATED |
| `QUICK_REFERENCE.md` | This file | CREATED |

## Next Steps

1. Implement data-testid attributes in frontend
2. Run: `npm run test:e2e -- e2e/admin/indexing.spec.ts`
3. Fix failing tests
4. Generate HTML report
5. Verify all features work as expected

---

**Status:** READY FOR EXECUTION
**Created:** 2025-11-27
**Sprint:** 33
