# TESTING QUICK START GUIDE

**AegisRAG Testing Infrastructure - Sprint 31+**

This guide contains essential testing knowledge, common pitfalls, and solutions for the AegisRAG testing infrastructure.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [React StrictMode + E2E Tests Issue](#react-strictmode--e2e-tests-issue)
3. [Running Tests](#running-tests)
4. [Common Issues & Solutions](#common-issues--solutions)
5. [Test Architecture](#test-architecture)

---

## Quick Start

### Backend Tests
```bash
# Run all backend tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_lightrag_client.py
```

### Frontend Tests

**Prerequisites:**
- Backend must be running on port 8000
- Frontend must be running on port 5179

```bash
# Terminal 1: Start Backend
poetry run python -m src.api.main

# Terminal 2: Start Frontend
cd frontend
npm run dev

# Terminal 3: Run E2E Tests
cd frontend
npm run test:e2e
```

---

## React StrictMode + E2E Tests Issue

### Problem Description

**Discovered:** 2025-11-21 (Sprint 31 E2E Testing)

React StrictMode causes **double-mounting** in development mode, which triggers AbortController cleanup during the unmount phase, aborting SSE (Server-Sent Events) fetch requests before they complete.

#### Symptoms:
- E2E tests timeout after 20-30 seconds
- Network trace shows first `stream` request with **"x-unknown"** status (aborted)
- Backend logs show **NO incoming requests** during test execution
- Manual testing works fine (user waits through double-mount)

#### Technical Root Cause:
```
1. React StrictMode → Component mounts
2. useEffect → fetch starts
3. StrictMode → Component unmounts (development only)
4. Cleanup → AbortController.abort() → First fetch aborted
5. StrictMode → Component re-mounts
6. useEffect → Second fetch starts
7. Tests timeout waiting for aborted response
```

### Solution: Conditional StrictMode

**File:** `frontend/src/main.tsx`

```typescript
/**
 * React StrictMode Configuration - Sprint 31 Fix
 *
 * Issue: StrictMode causes double-mounting in development, which triggers
 * AbortController cleanup between mounts, aborting SSE fetch requests.
 *
 * Evidence:
 * - Network trace shows first "stream" request with "x-unknown" status (aborted)
 * - Second request succeeds but tests timeout waiting for response
 * - Backend logs show no incoming requests when StrictMode is enabled
 *
 * Solution: Conditionally disable StrictMode during E2E tests while keeping
 * it enabled for development to catch side effects.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Disable StrictMode during Playwright E2E tests to prevent fetch abortion
// Playwright sets window.playwright when running tests
const isE2ETest = typeof window !== 'undefined' && (window as any).playwright;
const enableStrictMode = !isE2ETest && import.meta.env.DEV;

const app = enableStrictMode ? (
  <StrictMode>
    <App />
  </StrictMode>
) : (
  <App />
);

createRoot(document.getElementById('root')!).render(app);
```

#### Why This Works:
- **E2E Tests:** StrictMode disabled → No double-mounting → Fetch completes successfully
- **Development:** StrictMode enabled → Side effects detected → Better code quality
- **Production:** StrictMode disabled (via `import.meta.env.DEV`) → Optimal performance

### Test Results

| Metric | Before Fix | After Fix |
|--------|-----------|----------|
| **Smoke Tests Passing** | 0/12 (0%) | **12/12 (100%)** |
| **Test Duration** | 20-30s timeout | **42s complete suite** |
| **Backend Requests** | 0 (none reaching server) | **60+ successful (200 OK)** |
| **Network Errors** | "x-unknown" aborted | Clean 200 OK responses |

### Debugging Techniques Used

1. **Network Trace Analysis (Playwright)**
   ```bash
   npx playwright test --trace on
   npx playwright show-trace trace.zip
   ```
   - Navigate to Network tab
   - Look for aborted requests ("x-unknown" status)
   - Check request/response timeline

2. **Backend Logging**
   ```bash
   # Filter for chat stream requests
   tail -f logs/api.log | grep "POST /api/v1/chat"
   ```

3. **Manual Testing Comparison**
   - If manual testing works but E2E fails → Environment issue (like StrictMode)
   - If both fail → Application/backend issue

### Related Files
- `frontend/src/main.tsx` - Conditional StrictMode logic
- `frontend/src/api/chat.ts` - SSE streaming implementation
- `frontend/src/components/chat/StreamingAnswer.tsx` - AbortController usage
- `frontend/playwright.config.ts` - E2E test configuration

---

## Running Tests

### Unit Tests (Backend)

```bash
# All unit tests
poetry run pytest tests/unit/

# Specific module
poetry run pytest tests/unit/test_lightrag_client.py

# With verbose output
poetry run pytest tests/unit/ -v

# With coverage
poetry run pytest tests/unit/ --cov=src --cov-report=term-missing
```

### Integration Tests (Backend)

```bash
# All integration tests
poetry run pytest tests/integration/

# Specific test
poetry run pytest tests/integration/test_citation_generation.py
```

### E2E Tests (Frontend)

```bash
cd frontend

# Run all E2E tests
npm run test:e2e

# Run specific test file
npx playwright test smoke.spec.ts

# Run specific test (by name)
npx playwright test --grep "should load homepage"

# Run with headed browser (see what's happening)
npx playwright test --headed

# Generate trace for debugging
npx playwright test --trace on
npx playwright show-trace test-results/.../trace.zip
```

### Smoke Tests

Quick validation that infrastructure is working:

```bash
cd frontend
npx playwright test smoke.spec.ts --project=chromium
```

**Expected:** 12/12 tests passing in ~40-50 seconds

---

## Common Issues & Solutions

### Issue 1: E2E Tests Timeout

**Symptoms:**
- Tests timeout after 20-30 seconds
- Error: "Failed to receive LLM response within 20000ms"

**Solutions:**
1. **Check StrictMode:** Ensure conditional StrictMode is implemented (see above)
2. **Check Backend:** Verify backend is running on port 8000
   ```bash
   curl http://localhost:8000/health
   ```
3. **Check Frontend:** Verify frontend is running on port 5179
   ```bash
   curl http://localhost:5179
   ```
4. **Check Network:** Look at Playwright trace for aborted requests

### Issue 2: Lazy Import Mock Failures

**Symptoms:**
- `AttributeError: <module 'X'> does not have attribute 'Y'`
- Tests fail with "cannot find attribute to patch"

**Cause:** Lazy imports (imports inside functions) must be patched at their **original source module**, not at the importing module.

**Example:**
```python
# ❌ WRONG: Trying to patch at caller module
with patch("src.api.v1.chat.get_redis_memory") as mock:
    # Fails! get_redis_memory is lazy-imported in chat.py

# ✅ CORRECT: Patch at original source module
with patch("src.components.memory.get_redis_memory") as mock:
    # Works! get_redis_memory is defined in memory module
```

**Detection:**
1. Check if function is imported at module level in the caller
2. If not found, search for lazy imports inside functions
3. Patch at the module where function is **defined**, not where it's **used**

**Related Documentation:** See `CLAUDE.md` → "Test Mocking Best Practices"

### Issue 3: Port Conflicts

**Symptoms:**
- "Address already in use" errors
- Tests fail to connect to backend/frontend

**Solutions:**
```bash
# Windows: Find process using port
netstat -ano | findstr :8000
netstat -ano | findstr :5179

# Kill process by PID
taskkill /PID <PID> /F

# Or use different ports in .env and playwright.config.ts
```

### Issue 4: CORS Errors

**Symptoms:**
- Frontend shows CORS errors in console
- E2E tests fail with network errors

**Solution:** Update `src/core/config.py` to allow test port range:
```python
allowed_origins=["http://localhost:5170", "http://localhost:5171", ..., "http://localhost:5180"]
```

---

## Test Architecture

### Backend Test Structure
```
tests/
├── unit/               # Isolated component tests
│   ├── test_lightrag_client.py
│   ├── test_citation_generation.py
│   └── conftest.py    # pytest fixtures
├── integration/       # Component interaction tests
│   ├── test_langgraph_pipeline.py
│   └── test_api_endpoints.py
└── e2e/              # Full system tests
    └── test_e2e_retrieval.py
```

### Frontend Test Structure
```
frontend/
├── e2e/                    # Playwright E2E tests
│   ├── smoke.spec.ts       # Infrastructure validation
│   ├── citations/
│   │   └── citations.spec.ts
│   └── fixtures.ts         # Page Object Models
├── src/
│   └── components/
│       └── __tests__/      # Component unit tests (Vitest)
└── playwright.config.ts
```

### Test Naming Conventions

**Backend:**
- Unit: `test_<component>_<function>.py`
- Integration: `test_<feature>_integration.py`
- E2E: `test_e2e_<flow>.py`

**Frontend:**
- E2E: `<feature>.spec.ts`
- Component: `<Component>.test.tsx`

### Fixtures and Page Objects

**Backend (pytest):**
```python
# tests/conftest.py
@pytest.fixture
def mock_llm():
    return MockLLM()
```

**Frontend (Playwright):**
```typescript
// e2e/fixtures.ts
export const test = base.extend<{
  chatPage: ChatPage;
}>({
  chatPage: async ({ page }, use) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    await use(chatPage);
  },
});
```

---

## Test Coverage Goals

- **Backend:** >80% coverage for all core components
- **Frontend:** >70% coverage for critical user flows
- **E2E:** 100% of happy paths, 50% of error paths

### Checking Coverage

**Backend:**
```bash
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

**Frontend:**
```bash
npm run test:coverage
open coverage/index.html
```

---

## Continuous Integration

### GitHub Actions

**Workflow:** `.github/workflows/test.yml`

```yaml
- Backend tests run on every push
- Frontend E2E tests run on PR to main
- Coverage reports uploaded to Codecov
```

### Local Pre-commit Checks

```bash
# Run before committing
poetry run black src tests
poetry run ruff check src tests
poetry run mypy src
poetry run pytest
```

---

## Performance Benchmarks

### Expected Test Durations

| Test Suite | Expected Duration |
|-----------|------------------|
| Backend Unit | 5-10s |
| Backend Integration | 15-30s |
| Frontend E2E (Smoke) | 40-50s |
| Frontend E2E (Full) | 2-3 minutes |

If tests take significantly longer, investigate:
- Database connection pooling
- LLM mock responses (avoid real API calls in tests)
- Parallel test execution

---

## Troubleshooting Checklist

When tests fail, check in this order:

1. **Services Running?**
   - [ ] Backend on port 8000
   - [ ] Frontend on port 5179
   - [ ] Docker containers (if needed)

2. **Environment Variables?**
   - [ ] `.env` file exists and loaded
   - [ ] `VITE_API_BASE_URL` set correctly

3. **Dependencies Updated?**
   - [ ] `poetry install` (backend)
   - [ ] `npm install` (frontend)

4. **Port Conflicts?**
   - [ ] Check with `netstat -ano | findstr :8000`
   - [ ] Kill conflicting processes

5. **StrictMode Issue?**
   - [ ] Check `frontend/src/main.tsx` has conditional logic
   - [ ] Verify `window.playwright` detection works

6. **Network Traces?**
   - [ ] Run with `--trace on`
   - [ ] Look for aborted/failed requests

---

## References

- **CLAUDE.md** - Full project context and testing best practices
- **SUBAGENTS.md** - Testing agent responsibilities
- **ADR-031** (future) - E2E Testing Strategy and StrictMode Fix
- **Playwright Docs** - https://playwright.dev/
- **pytest Docs** - https://docs.pytest.org/

---

**Last Updated:** 2025-11-21 (Sprint 31 - React StrictMode Fix)
**Maintainer:** AegisRAG Team
