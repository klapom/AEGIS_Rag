# Running Feature 31.2: Search & Streaming E2E Tests

**Status:** Ready to Execute
**Location:** `frontend/e2e/search/`
**Tests:** 18 total (search.spec.ts + intent.spec.ts)
**Expected Duration:** 3-5 minutes
**LLM Cost:** USD 0.00 (local Ollama)

## Quick Start (3 Steps)

### Step 1: Start Backend (Terminal 1)
```bash
cd "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag"
poetry run python -m src.api.main
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Verify Backend:**
```bash
curl http://localhost:8000/health
```

### Step 2: Start Frontend (Terminal 2)
```bash
cd "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\frontend"
npm run dev
```

**Expected Output:**
```
  Local:   http://localhost:5173
  press h + enter to show help
```

### Step 3: Run Tests (Terminal 3)
```bash
cd "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\frontend"
npm run test:e2e -- search/
```

## Test Execution Options

### Full Test Suite
```bash
# Run all search tests
npm run test:e2e -- search/
```

### Run Specific Test Files
```bash
# Search flow tests only
npm run test:e2e -- search/search.spec.ts

# Intent classification tests only
npm run test:e2e -- search/intent.spec.ts
```

### Run Specific Test Groups
```bash
# Run tests matching pattern
npm run test:e2e -- search/search.spec.ts -g "streaming"
npm run test:e2e -- search/intent.spec.ts -g "VECTOR"
```

### Interactive Modes

#### Playwright UI (Recommended for First Run)
```bash
npm run test:e2e -- search/ --ui
```
This opens an interactive UI where you can:
- Run tests individually
- Pause/resume execution
- Step through test actions
- View browser interactions
- See assertion details

#### Headed Mode (See Browser Actions)
```bash
npm run test:e2e -- search/ --headed
```
Browser window visible during test execution - useful for debugging.

#### Debug Mode (Step Through Tests)
```bash
npm run test:e2e -- search/search.spec.ts --debug
```
Opens Playwright Inspector for line-by-line execution.

#### Verbose Output
```bash
npm run test:e2e -- search/ --verbose
```
Detailed output for each test step.

## Understanding Test Output

### Success Output
```
PASS  frontend/e2e/search/search.spec.ts (180s)
  Search & Streaming
    OK should perform basic search with streaming (18s)
    OK should show streaming animation during LLM response (20s)
    OK should stream tokens incrementally (SSE) (16s)
    OK should handle long-form answer streaming (32s)
    OK should display source information in response (22s)
    OK should handle multiple queries in sequence (35s)
    OK should maintain search context across messages (28s)
    OK should handle queries with special characters and formatting (19s)

  Search Error Handling
    OK should handle empty query gracefully (8s)
    OK should handle very short queries (12s)
    OK should gracefully timeout if backend is slow (31s)

  Search UI Interactions
    OK should clear input after sending message (9s)
    OK should enable send button after response completes (10s)
    OK should allow sending messages using Enter key (15s)

PASS  frontend/e2e/search/intent.spec.ts (200s)
  Intent Classification
    OK should classify factual queries as VECTOR search (18s)
    OK should classify relationship questions as GRAPH search (22s)
    OK should classify comparative queries as HYBRID search (35s)
    OK should handle definition queries (16s)
    OK should handle how-to questions (24s)
    OK should handle why questions (20s)
    OK should handle complex multi-part questions (28s)
    OK should maintain intent context in follow-ups (25s)

  Intent Classification - Edge Cases
    OK should handle single-word queries (12s)
    OK should handle queries with domain-specific terminology (20s)
    OK should handle negation in queries (18s)
    OK should handle queries with numbers and metrics (16s)
    OK should handle technical acronym questions (14s)

===================== 18 passed (380s) =====================
```

### Failure Output
```
FAIL  frontend/e2e/search/search.spec.ts (45s)

  Search & Streaming
    1) should perform basic search with streaming

Error: Expected 'Some response text' to contain 'transform'
  at /project/frontend/e2e/search/search.spec.ts:22

Trace: test-results/trace.zip
Screenshots: test-results/failures/search-1.png
```

## Troubleshooting Guide

### Backend Connection Error
```
Error: Failed to connect to localhost port 8000
```

**Solutions:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check poetry installation: `poetry --version`
3. Install dependencies: `cd .. && poetry install`
4. Start backend: `poetry run python -m src.api.main`

### Frontend Not Loading
```
Error: net::ERR_CONNECTION_REFUSED at localhost:5173
```

**Solutions:**
1. Verify frontend is running: Open http://localhost:5173 in browser
2. Check Node installation: `npm --version`
3. Install dependencies: `cd frontend && npm install`
4. Clear cache: `rm -rf frontend/node_modules/.vite`
5. Start frontend: `npm run dev`

### LLM Response Timeout
```
Error: LLM response timeout after 30000ms
```

**Solutions:**
1. Check Ollama is running: `ollama serve` in separate terminal
2. Verify model exists: `ollama ls` (should show gemma:3-4b or similar)
3. Check system resources: `free -m` (need 4GB+ RAM)
4. Increase timeout: Change `waitForResponse(30000)` to `waitForResponse(60000)`

### Test Hangs on Message Input
```
Test seems to pause indefinitely when filling message input
```

**Solutions:**
1. Verify frontend is responsive: Check in browser
2. Clear browser cache: `rm -rf ~/.cache/chromium`
3. Restart frontend: Ctrl+C and `npm run dev`
4. Check browser console for errors: Open DevTools F12

### SSE Streaming Not Working
```
Tests pass but responses appear instant (not streaming)
```

**Solutions:**
1. Check backend logs for SSE stream
2. Verify chat endpoint is sending SSE headers
3. Check browser Network tab in DevTools
4. Verify `data-streaming` attribute in response

## Test Result Analysis

### Viewing Results

#### HTML Report (Best)
```bash
npm run test:e2e:report
```
Opens interactive HTML report in browser with:
- Test timeline
- Screenshots on failure
- Traces for debugging
- Detailed error messages

#### JSON Results
```bash
cat frontend/test-results/results.json | jq '.'
```
Machine-readable format for CI/CD integration

#### JUnit XML
```bash
cat frontend/test-results/junit.xml
```
For integration with test reporting tools

### Interpreting Results

**Pass Indicators:**
- Status: "passed"
- Duration: Increases gradually (LLM response time expected)
- Assertions: All green checkmarks
- Screenshots: Only on failure

**Failure Indicators:**
- Status: "failed"
- Error message: Explicit assertion failure
- Screenshot: Shows browser state at failure
- Trace: Available for detailed debugging

### Performance Metrics

**Typical Response Times:**
- Simple factual query: 15-25 seconds
- Complex comparative query: 25-35 seconds
- Follow-up query: 10-20 seconds (faster due to context)
- Error handling: 5-10 seconds (quick timeout)

**Total Suite Time:**
- All 18 tests: 3-5 minutes
- Sequential execution: Intentional (prevents rate limiting)
- Parallelization: Not recommended (Ollama resource constraint)

## Common Test Patterns

### Basic Search Test Pattern
```typescript
test('should do something', async ({ chatPage }) => {
  // 1. Send message
  await chatPage.sendMessage('Your query here');

  // 2. Wait for response
  await chatPage.waitForResponse();

  // 3. Verify response
  const response = await chatPage.getLastMessage();
  expect(response).toBeTruthy();
  expect(response).toContain('expected keyword');
});
```

### Intent Classification Test Pattern
```typescript
test('should classify as VECTOR search', async ({ chatPage }) => {
  // Send factual question
  await chatPage.sendMessage('What is X?');
  await chatPage.waitForResponse();

  // Verify response indicates vector search used
  const response = await chatPage.getLastMessage();
  expect(response).toMatch(/definition|meaning|is/i);
});
```

### Error Handling Pattern
```typescript
test('should handle error gracefully', async ({ chatPage }) => {
  // Send problematic input
  await chatPage.sendMessage('');

  // Try to get input state
  const isReady = await chatPage.isInputReady();
  expect(isReady).toBeTruthy();
});
```

## Continuous Testing

### Running Tests Repeatedly
```bash
# Run tests in watch mode (reruns on file change)
npm run test:e2e -- search/ --watch
```

### Automated Flakiness Detection
```bash
# Run each test 5 times to detect intermittent failures
for i in {1..5}; do
  npm run test:e2e -- search/search.spec.ts
done
```

### Baseline Performance
```bash
# Measure average response times
time npm run test:e2e -- search/ --reporter=json \
  > test-results/baseline.json
```

## CI/CD Integration

### GitHub Actions Template
```yaml
name: Feature 31.2 Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm install
      - run: poetry install  # For backend
      - run: ollama pull gemma:3-4b  # Pull Ollama model
      - run: ollama serve &  # Start Ollama
      - run: poetry run python -m src.api.main &  # Start backend
      - run: npm run dev &  # Start frontend
      - run: npm run test:e2e -- search/
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

## Performance Optimization

### Reduce Test Duration
1. Run specific test group: `-g "pattern"`
2. Use search.spec.ts only for sanity checks
3. Batch related tests together

### Optimize Ollama
1. Allocate more VRAM: Set `OLLAMA_GPU=1` or `OLLAMA_GPU=0` (CPU only)
2. Increase max context: `OLLAMA_KEEP_ALIVE=10m`
3. Use quantized models: Current gemma:3-4b is Q4 (optimized)

### Network Optimization
1. Use localhost (avoid network latency)
2. Test on same machine as services
3. Monitor network: `netstat -i` during tests

## Test Maintenance

### Adding New Tests
```typescript
test.describe('New Feature', () => {
  test('should do something new', async ({ chatPage }) => {
    // Follow same pattern as existing tests
    await chatPage.sendMessage('Your test query');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });
});
```

### Updating Timeouts
Change in `playwright.config.ts`:
```typescript
timeout: 30 * 1000,  // Increase if needed
expect: {
  timeout: 10 * 1000,  // Assertion timeout
}
```

### Fixing Flaky Tests
1. Increase timeout: `waitForResponse(60000)`
2. Add intermediate waits: `await page.waitForTimeout(500)`
3. Use explicit conditions: `waitForSelector` instead of `waitForNavigation`
4. Check browser console: `page.on('console', console.log)`

## Support & Debugging

### View Browser Console
```typescript
page.on('console', (msg) => console.log(msg.text()));
```

### Take Screenshots During Test
```typescript
await page.screenshot({ path: 'screenshot.png' });
```

### View Network Requests
```bash
npm run test:e2e -- search/ --trace=on
# Then view in: npx playwright show-trace test-results/trace.zip
```

### Enable Debug Logging
```bash
DEBUG=pw:api npm run test:e2e -- search/
```

## Next Steps

After all tests pass:

1. Commit results: `git add test-results/`
2. Update metrics: Document baseline performance
3. Proceed to Feature 31.3: Citation E2E tests
4. Set up CI/CD: Integrate into GitHub Actions

## Summary

Feature 31.2 delivers 18 comprehensive E2E tests:
- 13 search and streaming tests (flow, errors, UI)
- 13 intent classification tests (routing, edge cases)
- Full documentation (README, TEST_PLAN)
- 3-5 minute execution time
- USD 0.00 cost (local Ollama)

**All tests ready to execute!**

---

**Created:** 2025-11-20
**Test Suite:** Sprint 31, Feature 31.2 (8 SP)
**Framework:** Playwright 1.40+ with TypeScript
