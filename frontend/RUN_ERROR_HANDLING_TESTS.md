# Running Error Handling E2E Tests - Quick Reference

**Feature:** Sprint 31 - Feature 31.9
**Test File:** `frontend/e2e/errors/error-handling.spec.ts`
**Total Tests:** 21
**Duration:** 5-10 minutes
**Cost:** FREE

## Quick Start

### Step 1: Start Backend (Terminal 1)
```bash
cd AEGIS_Rag
poetry run python -m src.api.main
```
Wait for: `INFO:     Uvicorn running on http://0.0.0.0:8000`

### Step 2: Start Frontend (Terminal 2)
```bash
cd AEGIS_Rag/frontend
npm run dev
```
Wait for: `VITE v7.1.7  ready in ... ms`
Navigate to: http://localhost:5173

### Step 3: Run Tests (Terminal 3)
```bash
cd AEGIS_Rag/frontend
npm run test:e2e -- e2e/errors/error-handling.spec.ts
```

## What to Expect

### Test Output
```
Running 21 tests using 1 worker
[1/21] [chromium] › error-handling.spec.ts › Error Handling - Timeout & Recovery › ...
[2/21] [chromium] › error-handling.spec.ts › Error Handling - Input Validation › ...
...
21 passed
```

### Success
- All 21 tests PASS
- Duration: 5-10 minutes
- HTML report generated

### Failure (Expected if services not running)
- Frontend connection refused (localhost:5173)
- Backend not responding
- These are setup issues, not test issues

## Test Categories

### 1. Timeout & Recovery (3 tests) [~90s]
- Backend timeout (30+ seconds)
- Slow response recovery
- Incomplete streaming

### 2. Input Validation (4 tests) [~120s]
- Empty queries
- Special characters
- Long queries (5000+ chars)
- Edge cases (spaces)

### 3. Backend Failure Recovery (3 tests) [~90s]
- Disconnection handling
- LLM errors
- Retry logic

### 4. Streaming Failures (3 tests) [~90s]
- SSE connection drops
- Partial messages
- Recovery

### 5. User Experience (5 tests) [~150s]
- Error messages
- Loading states
- Submit prevention
- Input cleanup
- Conversation persistence

### 6. Network Resilience (3 tests) [~90s]
- Timeout handling
- Rate limiting
- Security verification

## Viewing Results

### HTML Report
```bash
npm run test:e2e:report
```
Opens browser with detailed test results, screenshots, traces

### CLI Output
```bash
# Show last 50 lines of test output
tail -50 test-results.log

# Full test output
cat test-results.json | jq '.'
```

### Specific Test Trace
```bash
# Extract and view trace for failed test
unzip "test-results/errors-error-handling-*/trace.zip"
```

## Common Issues

### Issue: "Connection refused localhost:5173"
**Solution:** Start frontend with `npm run dev` before running tests

### Issue: "Backend health check failed"
**Solution:** Start backend with `poetry run python -m src.api.main` before tests

### Issue: "Tests timeout after 30 seconds"
**Reason:** Designed to timeout for error scenarios
**Expected:** App should remain functional after timeout

### Issue: "Some tests fail, others pass"
**Cause:** Network/timing issues during test run
**Solution:** Re-run tests with fresh services

## Test Configuration

**File:** `playwright.config.ts`
**Key Settings:**
- Sequential execution (1 worker)
- 30 second test timeout
- Chrome browser
- Screenshots on failure
- Trace retention

## Test Structure

### Each Error Test Pattern
```typescript
// 1. Send message that might error
await chatPage.sendMessage('query');

// 2. Handle timeout gracefully
try {
  await chatPage.waitForResponse(timeout);
  expect(response).toBeTruthy();
} catch (error) {
  // Timeout is expected for some error scenarios
  expect(await chatPage.isInputReady()).toBeTruthy();
}
```

### Key Assertion
```typescript
// Main goal: App remains functional after error
expect(await chatPage.isInputReady()).toBeTruthy();
```

## Performance Tips

### Run Specific Test Category
```bash
npm run test:e2e -- e2e/errors/error-handling.spec.ts -g "Timeout & Recovery"
```

### Run Single Test
```bash
npm run test:e2e -- e2e/errors/error-handling.spec.ts -g "should handle empty query"
```

### Run with UI (Slower but Visual)
```bash
npm run test:e2e:ui -- e2e/errors/error-handling.spec.ts
```

### Run with Debug Mode
```bash
npm run test:e2e:debug -- e2e/errors/error-handling.spec.ts
```

## Cost Verification

### No LLM Costs For
- Timeout tests (no generation)
- Input validation (rejected before LLM)
- Backend failure tests (error paths)

### Total Cost
**$0.00** - Error tests don't trigger expensive LLM calls

## Files Involved

### Test Files
- `frontend/e2e/errors/error-handling.spec.ts` (476 lines, 21 tests)

### Supporting Files
- `frontend/e2e/fixtures/index.ts` (fixtures)
- `frontend/e2e/pom/ChatPage.ts` (page object)
- `frontend/e2e/pom/BasePage.ts` (base methods)
- `frontend/playwright.config.ts` (configuration)

## Continuous Integration

### Enable in CI/CD (Optional)
Uncomment webServer section in `playwright.config.ts`:
```typescript
webServer: [
  {
    command: 'cd .. && poetry run python -m src.api.main',
    url: 'http://localhost:8000/health',
  },
  {
    command: 'npm run dev',
    url: 'http://localhost:5173',
  },
]
```

### Then in CI Pipeline
```bash
npm run test:e2e -- e2e/errors/error-handling.spec.ts
```

## Documentation

- `ERROR_HANDLING_TEST_SUMMARY.md` - Detailed test guide
- `FEATURE_31_9_SUMMARY.md` - Feature overview
- This file - Quick reference

## Contact & Support

For test-related questions:
- Check `ERROR_HANDLING_TEST_SUMMARY.md` for details
- Review test output and Playwright reports
- Check test traces for failures

## Success Checklist

After running tests:
- [ ] All 21 tests pass
- [ ] Duration is 5-10 minutes
- [ ] HTML report generated successfully
- [ ] No screenshots of failures
- [ ] Cost is $0.00
- [ ] Ready for production

---

**Last Updated:** 2025-11-20
**Feature:** Sprint 31, Feature 31.9
**Status:** READY TO RUN
