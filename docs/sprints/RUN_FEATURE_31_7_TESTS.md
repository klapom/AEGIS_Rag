# Run Feature 31.7 E2E Tests - Admin Indexing UI

## Quick Start

### Prerequisites
1. **Backend Running:** Ensure backend is running on `http://localhost:8000`
   ```bash
   cd backend
   poetry run uvicorn src.api.main:app --reload
   ```

2. **Test Documents Available:** Ensure test documents exist
   ```bash
   # Option 1: Use default sample documents
   ls data/sample_documents/

   # Option 2: Set custom path
   export TEST_DOCUMENTS_PATH=/path/to/test/documents
   ```

3. **Frontend Dependencies Installed:**
   ```bash
   cd frontend
   npm install
   ```

### Run E2E Tests

**Run All Admin Indexing Tests:**
```bash
cd frontend
npm run test:e2e -- e2e/admin/indexing.spec.ts
```

**Run Single Test:**
```bash
npm run test:e2e -- e2e/admin/indexing.spec.ts -g "should display indexing interface"
```

**Run with UI (Headed Mode):**
```bash
npm run test:e2e -- e2e/admin/indexing.spec.ts --headed
```

**Run with Debug:**
```bash
npm run test:e2e -- e2e/admin/indexing.spec.ts --debug
```

## Test Coverage

### 10 E2E Test Scenarios

1. **Display Indexing Interface** (`should display indexing interface with all controls`)
   - Verifies all UI elements are visible
   - Checks input field and button are enabled

2. **Invalid Directory Error** (`should handle invalid directory path with error message`)
   - Tests error handling for non-existent paths
   - Verifies error message display

3. **Cancel Indexing** (`should cancel indexing operation gracefully`)
   - Tests cancel button functionality
   - Verifies graceful abort

4. **Progress Bar Display** (`should display progress bar during indexing`)
   - Verifies progress bar appears
   - Checks progress percentage is valid (0-100%)

5. **Progress Tracking** (`should track indexing progress and display status updates`)
   - Monitors progress increments over time
   - Verifies status message updates

6. **Document Count** (`should display indexed document count`)
   - Checks document counter element
   - Verifies count is >= 0

7. **Success Completion** (`should complete indexing with success message`)
   - Tests full indexing workflow
   - Verifies success message display

8. **Advanced Options** (`should toggle advanced options if available`)
   - Tests advanced options toggle
   - Verifies toggle state

9. **Admin Access** (`should maintain admin access and page functionality`)
   - Verifies page is accessible
   - Checks all elements remain functional

10. **Statistics Snapshot** (`should get indexing statistics snapshot`)
    - Tests statistics retrieval
    - Verifies data structure

## Expected Results

### Success Indicators ✅
- All 10 tests pass
- No console errors
- Progress bar animates smoothly
- Status messages update in real-time
- Document count increments correctly
- Success message appears on completion

### Common Issues

#### Issue: Backend Not Running
**Error:** `Failed to fetch` or `Network error`
**Solution:**
```bash
cd backend
poetry run uvicorn src.api.main:app --reload
# Verify: http://localhost:8000/health
```

#### Issue: Test Documents Not Found
**Error:** `Directory not found` or `Access denied`
**Solution:**
```bash
# Create test documents directory
mkdir -p data/sample_documents

# Or set custom path
export TEST_DOCUMENTS_PATH=/path/to/documents
```

#### Issue: Port Already in Use
**Error:** `Port 8000 is already in use`
**Solution:**
```bash
# Kill existing process
pkill -f uvicorn
# Or use different port
uvicorn src.api.main:app --port 8001
```

#### Issue: Indexing Takes Too Long
**Error:** `Timeout after 120000ms`
**Solution:**
- Use smaller test document set
- Increase timeout in test:
  ```typescript
  timeout: 300000  // 5 minutes
  ```

## Manual Testing

### Test the UI Manually

1. **Start Frontend Dev Server:**
   ```bash
   cd frontend
   npm run dev
   ```

2. **Navigate to Admin Indexing Page:**
   ```
   http://localhost:5173/admin/indexing
   ```

3. **Test Workflow:**
   - Enter directory path: `data/sample_documents`
   - Click "Start Indexing"
   - Confirm deletion warning
   - Watch progress bar and status updates
   - Verify document count increments
   - Wait for success message

4. **Test Error Handling:**
   - Enter invalid path: `/invalid/path`
   - Click "Start Indexing"
   - Verify error message appears

5. **Test Cancel:**
   - Start indexing
   - Click "Cancel" button mid-process
   - Verify indexing stops

## Debugging E2E Tests

### View Test Artifacts
```bash
# Screenshots on failure
ls frontend/test-results/

# Playwright trace viewer
npx playwright show-trace frontend/test-results/trace.zip
```

### Enable Verbose Logging
```typescript
// In test file
test.use({ trace: 'on', screenshot: 'on', video: 'on' });
```

### Slow Down Tests
```typescript
// In playwright.config.ts
use: {
  slowMo: 1000,  // 1 second delay between actions
}
```

## CI/CD Integration

### GitHub Actions Workflow
```yaml
- name: Run Admin Indexing E2E Tests
  run: |
    cd frontend
    npm run test:e2e -- e2e/admin/indexing.spec.ts
```

### Environment Variables
```bash
# Required for CI/CD
export TEST_DOCUMENTS_PATH=/app/test-data
export BACKEND_URL=http://localhost:8000
```

## Performance Benchmarks

### Expected Timings
- **Test Suite Total:** 2-5 minutes (depends on document count)
- **Single Test:** 10-30 seconds
- **Indexing Operation:** 30-120 seconds (depends on documents)

### Optimization Tips
1. Use small document set for tests (5-10 files)
2. Mock backend responses for faster tests
3. Run tests in parallel (Playwright workers)

## Related Documentation

- **Feature Summary:** `FEATURE_31_7_UI_IMPLEMENTATION_SUMMARY.md`
- **POM:** `frontend/e2e/pom/AdminIndexingPage.ts`
- **Test Suite:** `frontend/e2e/admin/indexing.spec.ts`
- **Component:** `frontend/src/pages/admin/AdminIndexingPage.tsx`

---

**Last Updated:** 2025-11-20
**Feature:** Sprint 31 Feature 31.7
**Status:** Ready for Testing
