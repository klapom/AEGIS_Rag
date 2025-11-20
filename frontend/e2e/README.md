# E2E Testing with Playwright

AEGIS RAG E2E test suite for comprehensive testing of frontend features with real backend/LLM integration.

## Prerequisites

Before running E2E tests, ensure:

1. **Backend Requirements**
   - FastAPI server running on `http://localhost:8000`
   - Health endpoint accessible: `http://localhost:8000/health`
   - Ollama container running with Gemma-3 4B model
   - (Optional) Alibaba Cloud DashScope API key configured for VLM tests

2. **Frontend Requirements**
   - Node.js 18+ installed
   - Playwright installed: `npm install -D @playwright/test`
   - Chromium browser: `npx playwright install chromium`

3. **LLM Setup**
   - Local: Ollama with `gemma-3-4b-it-Q8_0` model
   - Cloud: Alibaba Cloud DashScope (for VLM-dependent admin tests)
   - Cost: Local tests are FREE, admin tests cost ~$0.30/run

## Local Execution (3 Terminals)

### Terminal 1: Start Backend API

```bash
cd C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag
poetry install --with dev
poetry run python -m src.api.main
```

**Expected Output:**
```
INFO:     Application startup complete
Uvicorn running on http://0.0.0.0:8000
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

### Terminal 2: Start Frontend Dev Server

```bash
cd frontend
npm install  # First time only
npm run dev
```

**Expected Output:**
```
Local:   http://localhost:5173
```

Browser should open automatically at http://localhost:5173

### Terminal 3: Run Tests

```bash
cd frontend
npm run test:e2e
```

**Test Output:**
```
Running 25 tests...
smoke.spec.ts: 7 passed
search.spec.ts: 4 passed (in progress)
citations.spec.ts: 3 passed (in progress)
...
```

## Test Suite Structure

### Wave 1: Infrastructure (Feature 31.1) - COMPLETE

**Playwright Configuration**
- `playwright.config.ts` - E2E test configuration
- CI/CD disabled (local-only execution)
- Sequential workers (avoid LLM rate limits)
- 30s timeout (for LLM responses)

**Page Object Models (POMs)**
```
e2e/pom/
├── BasePage.ts              # Common methods
├── ChatPage.ts              # Chat interface
├── HistoryPage.ts           # Conversation history
├── SettingsPage.ts          # Settings & theme
├── AdminIndexingPage.ts     # Document indexing
├── AdminGraphPage.ts        # Knowledge graph
└── CostDashboardPage.ts     # Cost tracking (Feature 31.10)
```

**Test Fixtures**
```
e2e/fixtures/
└── index.ts                 # Custom Playwright fixtures
```

### Wave 2: Cost API Backend (Feature 31.2) - PENDING

Cost tracking API endpoints:
- `GET /api/v1/costs/summary` - Monthly cost summary
- `GET /api/v1/costs/breakdown` - Cost by provider
- `GET /api/v1/costs/details` - Detailed cost records

### Wave 3: Feature E2E Tests (Features 31.3-31.9)

#### Feature 31.3: Search & Streaming Tests (5 SP)
```
e2e/search/
├── basic-search.spec.ts         # Simple keyword search
├── semantic-search.spec.ts      # Vector similarity
├── streaming.spec.ts            # SSE streaming responses
├── timeout-handling.spec.ts     # Timeout recovery
└── network-errors.spec.ts       # Network resilience
```

**Test Cases:**
- Single-turn search with streaming
- Multi-turn conversations
- Timeout recovery
- Network error handling
- Response validation

#### Feature 31.4: Citation Tests (3 SP)
```
e2e/citations/
├── inline-citations.spec.ts     # [1], [2] in responses
├── citation-accuracy.spec.ts    # Source validation
└── citation-interaction.spec.ts # Click to view source
```

**Test Cases:**
- Citation generation in responses
- Citation accuracy verification
- Citation source preview
- Citation metadata extraction

#### Feature 31.5: Follow-up Questions Tests (3 SP)
```
e2e/followup/
├── followup-generation.spec.ts  # Question suggestion
├── followup-click.spec.ts       # Click to search
└── followup-accuracy.spec.ts    # Relevance validation
```

**Test Cases:**
- Follow-up question suggestion
- Clicking follow-up executes search
- Answer relevance validation

#### Feature 31.6: Conversation History Tests (3 SP)
```
e2e/history/
├── session-management.spec.ts   # Create/delete sessions
├── history-search.spec.ts       # Search conversations
└── session-export.spec.ts       # Export conversations
```

**Test Cases:**
- Create new session
- Load existing session
- Delete session
- Search history
- Export to JSON/CSV

#### Feature 31.7: Settings & Theme Tests (2 SP)
```
e2e/settings/
├── theme-toggle.spec.ts         # Light/dark mode
├── settings-persistence.spec.ts # LocalStorage
└── export-import.spec.ts        # Settings backup
```

**Test Cases:**
- Toggle dark mode
- Verify theme persistence
- Export settings
- Import settings

#### Feature 31.8: Graph Visualization Tests (4 SP)
```
e2e/graph/
├── graph-loading.spec.ts        # Graph render
├── graph-interaction.spec.ts    # Zoom/pan/filter
├── graph-query.spec.ts          # Query integration
└── admin-graph.spec.ts          # Admin controls
```

**Test Cases:**
- Knowledge graph visualization
- Node/edge interaction
- Query filtering
- Zoom/pan controls

#### Feature 31.9: Error Handling Tests (3 SP)
```
e2e/errors/
├── input-validation.spec.ts     # Invalid input
├── backend-errors.spec.ts       # 5xx handling
├── timeout-recovery.spec.ts     # Timeout recovery
└── network-errors.spec.ts       # Network failures
```

**Test Cases:**
- Invalid input validation
- Backend error messages
- Timeout recovery
- Network error recovery

### Wave 4: Advanced Features (Features 31.10-31.13)

#### Feature 31.10: Cost Dashboard Tests (4 SP)
```
e2e/admin/
├── cost-dashboard.spec.ts       # Cost display
├── budget-tracking.spec.ts      # Budget alerts
├── cost-export.spec.ts          # Export costs
└── provider-analytics.spec.ts  # Provider breakdown
```

**Requires:**
- Backend cost tracking API (Feature 31.2)
- Cost database schema
- Provider-specific analytics

## Test Data

### Seeded Test Documents
```
data/test-documents/
├── sample-page.pdf          # 5 pages, 5000 words
├── sample-table.pdf         # Table-heavy document
├── sample-images.pdf        # Image-rich document
└── multi-language.pdf       # English + Chinese
```

### Test Queries
- "What is the main topic?" - Semantic search
- "Find tables with data" - Structured search
- "Compare versions" - Complex reasoning
- "Extract metadata" - Entity extraction

## Running Tests

### Run All Tests
```bash
npm run test:e2e
```

### Run Specific Test Suite
```bash
npm run test:e2e -- search
npm run test:e2e -- citations
npm run test:e2e -- followup
```

### Run Single Test
```bash
npm run test:e2e -- search/basic-search.spec.ts
```

### Run with UI
```bash
npm run test:e2e:ui
```

Open browser to inspect tests live

### Debug Mode
```bash
npm run test:e2e:debug
```

Step through tests line-by-line

### View Report
```bash
npm run test:e2e:report
```

Open HTML test report

## Environment Variables

Create `.env.test` in frontend directory:

```bash
# Backend
VITE_API_URL=http://localhost:8000

# Test Timeouts
TEST_TIMEOUT_LLM=20000       # 20s for LLM calls
TEST_TIMEOUT_NETWORK=10000   # 10s for network
TEST_TIMEOUT_UI=5000         # 5s for UI

# Test Features
TEST_ADMIN_FEATURES=false    # Disable if no admin access
TEST_VLM_FEATURES=false      # Disable if no Alibaba Cloud key

# Debugging
DEBUG_SCREENSHOTS=true       # Save screenshots on failure
DEBUG_TRACES=true            # Save traces on failure
HEADLESS=true                # Run headless
```

## Common Issues

### Backend Connection Timeout
```
Error: Backend health check failed after timeout
```

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check firewall settings
3. Ensure no port conflicts

### LLM Response Timeout
```
Error: LLM response timeout after 20000ms
```

**Solution:**
1. Check Ollama is running: `docker ps | grep ollama`
2. Check LLM model loaded: `curl http://localhost:11434/api/tags`
3. Increase timeout in playwright.config.ts

### Frontend Not Loading
```
Error: baseURL http://localhost:5173 is not reachable
```

**Solution:**
1. Verify frontend is running: `npm run dev`
2. Check console for build errors
3. Ensure no Vite conflicts

### Test Isolation Issues
```
Flaky tests due to shared state
```

**Solution:**
1. Clear localStorage between tests: `page.context().clearCookies()`
2. Use test fixtures for setup/teardown
3. Enable test retry: `test.describe.configure({ retries: 2 })`

## Cost Tracking

### Local Tests (FREE)
- Uses local Ollama (Gemma-3 4B)
- No API calls
- ~100ms per test

### Admin Tests (PAID)
- Uses Alibaba Cloud VLM
- ~$0.001-0.01 per VLM call
- Admin suite: ~$0.30 total

### Monthly Cost Estimate
```
Development: ~$5-10/month (10-20 runs)
CI/CD Pipeline: DISABLED (zero cost)
Production Monitoring: Separate budget
```

## CI/CD Integration

**IMPORTANT: E2E tests are disabled for CI/CD to avoid costs**

To enable CI/CD:
1. Create `.github/workflows/e2e.yml`
2. Configure test data seeding
3. Set `PLAYWRIGHT_WEBSERVER_DISABLED=false`
4. Configure Alibaba Cloud credentials
5. Add cost monitoring

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm install
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

## Performance Benchmarks

### Expected Response Times
```
Homepage Load:           500ms
Chat Input Send:         100ms
LLM Response Start:      2000ms (Ollama warm)
Full LLM Response:       10-20s
Citation Render:         500ms
Page Navigation:         300ms
```

### Test Execution Times
```
Smoke Tests:             5s (7 tests)
Search Tests:            45s (5 tests, with LLM calls)
Citations Tests:         30s (3 tests)
Full Suite:              ~10 minutes
```

## Best Practices

### Test Design
1. Use Page Object Models for all page interactions
2. Wait for network idle before assertions
3. Use data-testid attributes for reliable selectors
4. Mock external APIs when testing error paths
5. Use fixtures for common setup

### Test Isolation
1. Each test should be independent
2. Clear data between tests
3. Use unique test data per run
4. Clean up after tests

### Debugging
1. Enable trace: `trace: 'retain-on-failure'`
2. Take screenshots: `--screenshot only-on-failure`
3. Use debug mode: `npm run test:e2e:debug`
4. Check logs: `DEBUG=pw:api`

## References

- [Playwright Documentation](https://playwright.dev/)
- [AEGIS RAG Frontend](../src/)
- [AEGIS RAG Backend](../src/api/)
- [Sprint 31 Plan](../../docs/sprints/SPRINT_31_PLAN.md)
