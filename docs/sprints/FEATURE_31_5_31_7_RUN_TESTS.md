# Feature 31.5 & 31.7 E2E Tests - Quick Start Guide

## Overview

- **Features:** 31.5 (Conversation History) + 31.7 (Admin Indexing)
- **Tests:** 17 E2E tests (7 history + 10 admin)
- **Cost:** FREE (history) + ~$0.30 (admin with VLM)
- **Time:** ~3-5 minutes per run

## Prerequisites

### 1. Backend API (Terminal 1)

```bash
# Navigate to project root
cd /c/Users/Klaus\ Pommer/OneDrive\ -\ Pommer\ IT-Consulting\ GmbH/99_Studium_Klaus/AEGIS_Rag

# Install dependencies (if not done)
poetry install --with dev

# Start backend
poetry run python -m src.api.main
```

**Expected Output:**
```
INFO:     Application startup complete
Uvicorn running on http://0.0.0.0:8000
```

**Verify:**
```bash
curl http://localhost:8000/health
```

### 2. Frontend Dev Server (Terminal 2)

```bash
# Navigate to frontend
cd frontend

# Install dependencies (if not done)
npm install

# Start dev server
npm run dev
```

**Expected Output:**
```
Local:   http://localhost:5173/
```

### 3. Run Tests (Terminal 3)

```bash
cd frontend

# Run all E2E tests
npm run test:e2e

# OR run specific test suites
npm run test:e2e -- history/history.spec.ts
npm run test:e2e -- admin/indexing.spec.ts
```

---

## Test Execution

### Option A: Run All Tests

```bash
npm run test:e2e
```

**Expected Results:**
```
✓ history/history.spec.ts (7 tests) ........... PASSED
✓ admin/indexing.spec.ts (10 tests) .......... PASSED

Tests: 17 passed
Time: ~3-5 minutes
```

### Option B: Run History Tests Only

```bash
npm run test:e2e -- history
```

**Expected Results:**
```
✓ history/history.spec.ts (7 tests) ........... PASSED

Tests: 7 passed
Time: ~1 minute
```

**Tests:**
1. should auto-generate conversation title from first message ✓
2. should list conversations in chronological order ✓
3. should open conversation on click and restore messages ✓
4. should search conversations by title and content ✓
5. should delete conversation with confirmation dialog ✓
6. should handle empty history gracefully ✓
7. should display conversation metadata ✓

### Option C: Run Admin Tests Only

```bash
npm run test:e2e -- admin
```

**Expected Results:**
```
✓ admin/indexing.spec.ts (10 tests) .......... PASSED

Tests: 10 passed
Time: ~2-4 minutes
```

**Tests:**
1. should display indexing interface with all controls ✓
2. should handle invalid directory path with error message ✓
3. should cancel indexing operation gracefully ✓
4. should display progress bar during indexing ✓
5. should track indexing progress and display status updates ✓
6. should display indexed document count ✓
7. should complete indexing with success message ✓
8. should toggle advanced options if available ✓
9. should maintain admin access and page functionality ✓
10. should get indexing statistics snapshot ✓

### Option D: Run Single Test

```bash
# Run specific test by name
npm run test:e2e -- history -g "should auto-generate"

# Run with verbosity
npm run test:e2e -- history -g "should auto-generate" --reporter=verbose
```

---

## Interactive Debugging

### UI Mode (Inspect Tests Live)

```bash
npm run test:e2e:ui
```

Opens browser where you can:
- Watch tests execute in real-time
- Step through tests line-by-line
- Inspect page state
- Modify selectors and re-run

### Debug Mode (Step-by-Step)

```bash
npm run test:e2e:debug
```

Opens Playwright Inspector:
- Step through code
- Evaluate expressions
- Inspect DOM
- Modify test execution

### View HTML Report

```bash
npm run test:e2e:report
```

Opens detailed HTML report with:
- Test status for each case
- Screenshots on failure
- Video recordings (if configured)
- Trace files for debugging

---

## Troubleshooting

### Test Fails: "Backend health check failed"

**Problem:** Backend not running or port 8000 not available

**Solution:**
```bash
# Verify backend is running
curl http://localhost:8000/health

# If not running, start it
poetry run python -m src.api.main

# Check if port is in use
netstat -ano | grep 8000
# If in use, kill process or use different port
```

### Test Fails: "Frontend not loading"

**Problem:** Frontend dev server not running or port 5173 not available

**Solution:**
```bash
# Start frontend dev server
cd frontend
npm run dev

# Verify it's accessible
curl http://localhost:5173/
```

### Test Fails: "LLM response timeout"

**Problem:** Ollama not running or model not loaded

**Solution:**
```bash
# Verify Ollama is running
docker ps | grep ollama

# If not running, start it
docker run -d -p 11434:11434 ollama/ollama

# Load model
docker exec ollama ollama pull gemma-3-4b-it-Q8_0

# Test Ollama
curl http://localhost:11434/api/tags
```

### Test Fails: "Admin indexing timeout (120s)"

**Problem:** VLM extraction taking too long or failing

**Solution:**
```bash
# Check if VLM API key configured
echo $ALIBABA_CLOUD_API_KEY

# If empty, set it
export ALIBABA_CLOUD_API_KEY=sk-...

# Verify API key is valid
curl -H "Authorization: Bearer $ALIBABA_CLOUD_API_KEY" \
  https://dashscope-intl.aliyuncs.com/api/v1/services/aigc_text/text-generation

# For large test documents, increase timeout
npm run test:e2e -- admin -t 180000  # 3 minutes
```

### Test Fails: "Conversation not found in history"

**Problem:** Conversation wasn't created or history not updated

**Solution:**
```bash
# Verify message was sent successfully
# Check browser console in UI mode: npm run test:e2e:ui

# Check backend logs for errors
# Look for POST /api/v1/chat/send errors

# Verify database is accessible
# Check SQLite history database exists
ls -la data/conversations.db
```

---

## Environment Configuration

### .env File Setup

Create `frontend/.env.local`:
```bash
VITE_API_URL=http://localhost:8000
VITE_OLLAMA_BASE_URL=http://localhost:11434
```

Optional for admin tests:
```bash
ALIBABA_CLOUD_API_KEY=sk-...
ALIBABA_CLOUD_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
TEST_DOCUMENTS_PATH=/path/to/test/documents
```

### Playwright Config

Config location: `frontend/playwright.config.ts`

Key settings:
- Timeout: 30 seconds (for LLM responses)
- Workers: 1 (sequential, avoid rate limits)
- Report: HTML + JSON + JUnit
- Screenshots: On failure
- Traces: On failure

---

## Expected Test Results

### All Tests Pass ✓

```
Frontend\e2e\history\history.spec.ts
  Conversation History - Feature 31.5
    ✓ should auto-generate conversation title from first message (8s)
    ✓ should list conversations in chronological order (8s)
    ✓ should open conversation on click and restore messages (6s)
    ✓ should search conversations by title and content (5s)
    ✓ should delete conversation with confirmation dialog (6s)
    ✓ should handle empty history gracefully (2s)
    ✓ should display conversation metadata (7s)

Frontend\e2e\admin\indexing.spec.ts
  Admin Indexing Workflows - Feature 31.7
    ✓ should display indexing interface with all controls (3s)
    ✓ should handle invalid directory path with error message (3s)
    ✓ should cancel indexing operation gracefully (5s)
    ✓ should display progress bar during indexing (8s)
    ✓ should track indexing progress and display status updates (12s)
    ✓ should display indexed document count (5s)
    ✓ should complete indexing with success message (45s)
    ✓ should toggle advanced options if available (3s)
    ✓ should maintain admin access and page functionality (3s)
    ✓ should get indexing statistics snapshot (4s)

17 tests passed (195 seconds)
```

### Some Tests Skip or Fail

This is acceptable for certain scenarios:

```
✓ Test passes - feature working correctly
◇ Test skipped - optional feature not available
✗ Test fails - check error message and logs
```

**Acceptable Failures:**
- VLM extraction tests (if no Alibaba Cloud API key)
- Advanced options toggle (if not implemented)
- Export conversation (if export feature not enabled)

---

## Performance Benchmarks

### Expected Timing

| Test | Time | Notes |
|------|------|-------|
| Auto-generate title | 8-10s | Includes LLM response |
| Search conversation | 5-6s | Local search, no LLM |
| Delete conversation | 4-6s | Quick DB operation |
| Display interface | 2-3s | Pure UI, no delay |
| Invalid path error | 2-3s | Error handling, no VLM |
| Progress bar display | 5-8s | Depends on file size |
| Complete indexing | 45-60s | Includes VLM extraction |
| Toggle options | 2-3s | Pure UI |

### Total Execution Time

- History tests (7): ~1 minute
- Admin tests without VLM (3): ~10 seconds
- Admin tests with VLM (7): ~2-3 minutes
- **Total: 3-4 minutes**

---

## Test Files

### Created Files

```
frontend/e2e/history/history.spec.ts
  - 490 lines
  - 7 conversation history tests
  - Uses: HistoryPage, ChatPage POMs

frontend/e2e/admin/indexing.spec.ts
  - 263 lines
  - 10 admin indexing tests
  - Uses: AdminIndexingPage POM
```

### Test Fixtures Used

```
frontend/e2e/fixtures/index.ts
  - chatPage: ChatPage fixture
  - historyPage: HistoryPage fixture
  - adminIndexingPage: AdminIndexingPage fixture
```

### Page Object Models

```
frontend/e2e/pom/HistoryPage.ts
  - getConversationCount()
  - clickConversation(index)
  - searchConversations(query)
  - deleteConversation(index)
  - etc. (13 methods)

frontend/e2e/pom/AdminIndexingPage.ts
  - setDirectoryPath(path)
  - startIndexing()
  - waitForIndexingComplete(timeout)
  - getProgressPercentage()
  - etc. (12 methods)
```

---

## Common Commands

```bash
# Quick test run
npm run test:e2e

# History tests only
npm run test:e2e -- history

# Admin tests only
npm run test:e2e -- admin

# Interactive UI mode
npm run test:e2e:ui

# Debug mode
npm run test:e2e:debug

# View test report
npm run test:e2e:report

# Run single test with verbose output
npm run test:e2e -- history -g "auto-generate" --reporter=verbose

# Run with 3-minute timeout
npm run test:e2e -- -t 180000

# Run with specific browser
npm run test:e2e -- --project=chromium
```

---

## Continuous Integration (Optional)

### Enable CI/CD Tests

To run tests in GitHub Actions:

1. Set up backend in workflow:
   ```yaml
   - run: poetry install --with dev
   - run: poetry run python -m src.api.main &
   - run: sleep 10  # Wait for backend
   ```

2. Set up frontend:
   ```yaml
   - run: npm install
   - run: npm run dev &
   - run: sleep 5  # Wait for frontend
   ```

3. Run tests:
   ```yaml
   - run: npm run test:e2e
   ```

4. Upload artifacts on failure:
   ```yaml
   - uses: actions/upload-artifact@v4
     if: failure()
     with:
       name: playwright-report
       path: playwright-report/
   ```

**Cost Consideration:** ~$0.30 per CI run (admin VLM tests)

---

## Next Steps

1. **Run tests locally** to verify all 17 tests pass
2. **Check performance** - each test should complete in <30s
3. **Monitor logs** for any warnings or errors
4. **Enable CI/CD** if monthly budget allocated ($10-20)
5. **Add more E2E tests** for Features 31.8, 31.9, 31.10

---

## Support

For issues or questions:

1. Check error message in test output
2. Review troubleshooting section above
3. Check browser console (UI mode: `npm run test:e2e:ui`)
4. View HTML report: `npm run test:e2e:report`
5. Enable debug mode: `npm run test:e2e:debug`

---

**Test Suite Version:** 1.0
**Last Updated:** 2025-11-20
**Status:** READY FOR EXECUTION
