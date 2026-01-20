# LangSmith Tracing for Playwright E2E Tests

## Overview

LangSmith integration with Playwright E2E tests enables full visibility into LLM call chains, token counts, and latency bottlenecks during local testing. This guide shows how to enable LangSmith tracing **only** for Playwright tests while keeping CI/CD clean.

## Key Design Decisions

- **Default: Disabled** - LangSmith is disabled by default to avoid cost overhead and trace project noise
- **Opt-in for local development** - Enable LangSmith when debugging specific issues
- **CI/CD always disabled** - GitHub Actions workflows explicitly disable LangSmith to prevent automatic trace generation
- **Playwright-specific configuration** - Setup in `frontend/e2e/setup/langsmith.ts` provides helpers for tests

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Playwright E2E Tests                         │
│  (frontend/e2e/setup/langsmith.ts fixture)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼──────┐          ┌─────▼──────┐
    │  Local:   │          │ CI/CD:     │
    │ ENABLED   │          │ DISABLED   │
    │ (optional)│          │ (always)   │
    └────┬──────┘          └─────┬──────┘
         │                       │
    ┌────▼──────────────────────▼──────┐
    │  Backend (Docker API service)    │
    │  LANGSMITH_TRACING env var       │
    │  LANGSMITH_API_KEY env var       │
    └────┬───────────────────────────┬─┘
         │                           │
    ┌────▼─────────────────┐   ┌────▼──────────────┐
    │  Local with LangSmith │   │  CI/CD (disabled) │
    │  -Traces created      │   │  -No traces       │
    │  -Visible in Smith    │   │  -No API calls    │
    └──────────────────────┘   └───────────────────┘
```

## Setup Instructions

### Step 1: Get LangSmith API Key

1. Sign up at https://smith.langchain.com (free tier available)
2. Go to https://smith.langchain.com/settings
3. Copy your API key (starts with `sk-...`)

### Step 2: Enable LangSmith in Docker Compose

Edit `/home/admin/projects/aegisrag/AEGIS_Rag/docker-compose.dgx-spark.yml`:

```yaml
api:
  environment:
    # Existing vars...
    # Sprint 115: Enable LangSmith for local Playwright testing
    - LANGSMITH_TRACING=${LANGSMITH_TRACING:-false}
    - LANGSMITH_API_KEY=${LANGSMITH_API_KEY:-}
    - LANGSMITH_PROJECT=${LANGSMITH_PROJECT:-aegis-rag-sprint115}
    - LANGCHAIN_TRACING_V2=${LANGSMITH_TRACING:-false}
    - LANGCHAIN_API_KEY=${LANGSMITH_API_KEY:-}
    - LANGCHAIN_PROJECT=${LANGSMITH_PROJECT:-aegis-rag-sprint115}
```

**Already configured in current docker-compose.dgx-spark.yml** ✅

### Step 3: Update .env File

Edit `/home/admin/projects/aegisrag/AEGIS_Rag/.env`:

```bash
# ============================================================================
# LangSmith Observability (Optional) - Sprint 115 Feature 115.6
# ============================================================================
# Set LANGSMITH_TRACING=true and LANGSMITH_API_KEY=<your-key> to enable traces
# Default: false (disabled) - no traces created in CI/CD

LANGSMITH_TRACING=false  # Set to 'true' to enable
LANGSMITH_API_KEY=sk-YOUR-KEY-HERE  # Copy from https://smith.langchain.com/settings
LANGSMITH_PROJECT=aegis-rag-sprint115  # Project name in LangSmith
# LANGSMITH_ENDPOINT=https://api.smith.langchain.com  # Default endpoint
```

### Step 4: Restart Docker Containers

```bash
# Set environment variables and restart API
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=sk-YOUR-KEY-HERE

# Restart API with new environment
docker compose -f docker-compose.dgx-spark.yml up -d --force-recreate api

# Verify backend is ready
docker logs -f aegis-api | grep "health"
```

### Step 5: Run Frontend Services

In separate terminal:

```bash
# Terminal 2: Start frontend dev server
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend
npm run dev

# Expected output:
#   ➜  Local:   http://localhost:5179/
#   ➜  press h to show help
```

### Step 6: Run Playwright Tests

In another terminal:

```bash
# Terminal 3: Run Playwright tests
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend

# Run all tests with LangSmith tracing enabled
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test

# Or run specific test file
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test group01-mcp-tools.spec.ts

# Run with specific project (fast/chromium/full)
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --project chromium

# Run with verbose output
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --reporter=list
```

### Step 7: View Traces in LangSmith

1. Open https://smith.langchain.com
2. Navigate to **Projects** tab
3. Find your project (default: `aegis-rag-sprint115`)
4. View **Runs** tab to see all test traces
5. Click any trace to see:
   - LLM call chain (inputs, outputs, tokens)
   - Latency breakdown (where time is spent)
   - Token counts (input/output per call)
   - Error details if applicable

## Using LangSmith Fixture in Tests

### Basic Usage

```typescript
import { test } from '../setup/langsmith';

test('example: using langsmith fixture', async ({ page, langsmith }) => {
  // Log whether LangSmith is enabled
  langsmith.logStatus('my-test-name');

  // Navigate to page (this creates traces if enabled)
  await page.goto('/');

  // Get LangSmith project URL
  if (langsmith.isEnabled()) {
    console.log(`View traces: ${langsmith.getProjectUrl()}`);
  }
});
```

### Advanced Patterns

**Check if LangSmith is enabled:**
```typescript
if (langsmith.isEnabled()) {
  // Run expensive tracing setup only if enabled
  console.log(`Tracing enabled. Project: ${langsmith.getProjectUrl()}`);
}
```

**Get environment variables for API verification:**
```typescript
const envVars = langsmith.getEnvironmentVariables();
// Returns: {
//   LANGSMITH_TRACING: 'true',
//   LANGSMITH_API_KEY: 'sk-...',
//   LANGSMITH_PROJECT: 'aegis-rag-sprint115',
//   LANGCHAIN_TRACING_V2: 'true',
//   ...
// }
```

**Conditional test execution:**
```typescript
test('only run with tracing enabled', async ({ langsmith }) => {
  if (!langsmith.isEnabled()) {
    test.skip();
    return;
  }

  // This test only runs when LangSmith is enabled
});
```

## CI/CD Configuration

### Guaranteed Disabled in CI/CD

All CI/CD workflows explicitly disable LangSmith:

```yaml
# .github/workflows/ci.yml
- name: Run Unit Tests (LangSmith Disabled)
  env:
    LANGSMITH_TRACING: 'false'
    LANGCHAIN_TRACING_V2: 'false'
    LANGSMITH_API_KEY: ''  # Empty to prevent accidental use
  run: poetry run pytest ...
```

Benefits of explicit disabling:
- **Zero cost overhead** - No LangSmith API calls in CI/CD
- **Clean trace project** - Only intentional traces from local debugging
- **Faster CI/CD** - No external API dependency
- **Clear audit trail** - Easy to see traces are development-only

### Verify CI/CD Disabled

```bash
# Check that CI/CD workflow has LangSmith disabled
grep -A 5 "LANGSMITH_TRACING" .github/workflows/ci.yml
grep -A 5 "LANGSMITH_TRACING" .github/workflows/e2e.yml

# Expected output: LANGSMITH_TRACING: 'false'
```

## Troubleshooting

### Tests Won't Start / API Not Ready

**Symptom:** Tests timeout waiting for API

**Solution:**
```bash
# Check API container health
docker logs aegis-api | head -50

# Verify services are running
docker compose -f docker-compose.dgx-spark.yml ps

# Manually verify API is responding
curl http://localhost:8000/health

# Restart if needed
docker compose -f docker-compose.dgx-spark.yml restart api
```

### LangSmith API Key Error

**Symptom:** Error about missing LANGSMITH_API_KEY

**Solution:**
```bash
# Verify API key is set
echo $LANGSMITH_API_KEY

# If empty, set it:
export LANGSMITH_API_KEY=sk-YOUR-KEY-HERE

# Restart API:
docker compose -f docker-compose.dgx-spark.yml up -d --force-recreate api

# Verify in container:
docker exec aegis-api printenv | grep LANGSMITH
```

### Traces Not Appearing in LangSmith

**Possible causes:**
1. API container restarted before tracing enabled (env vars read at startup)
2. LANGSMITH_API_KEY is incorrect
3. Network connectivity issue
4. Project name mismatch

**Solution:**
```bash
# 1. Verify environment in container
docker exec aegis-api printenv | grep -E "LANGSMITH|LANGCHAIN"

# 2. Verify API sees the config
curl -s http://localhost:8000/api/v1/health | jq '.environment.langsmith'

# 3. Check API logs for tracing startup
docker logs aegis-api 2>&1 | grep -i "langsmith\|tracing"

# 4. Force full restart
docker compose -f docker-compose.dgx-spark.yml down
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=sk-YOUR-KEY-HERE
docker compose -f docker-compose.dgx-spark.yml up -d
sleep 30  # Wait for services to stabilize
```

### Performance Issues

**Symptom:** Tests run slowly with LangSmith enabled

**Root cause:** LangSmith traces add minimal overhead (<5%) but network latency to smith.langchain.com can add 100-500ms per LLM call

**Mitigation:**
1. Run tests with fewer concurrent workers:
   ```bash
   npx playwright test --workers=1
   ```

2. Disable tracing for fast tests:
   ```bash
   LANGSMITH_TRACING=false npm run test:e2e
   ```

3. Only trace specific test suites:
   ```bash
   LANGSMITH_TRACING=true npx playwright test group08-deep-research.spec.ts
   ```

## Example: Complete Local Setup

```bash
#!/bin/bash
# Full setup script for LangSmith Playwright testing

set -e

echo "🔧 Setting up LangSmith for Playwright E2E tests..."

# Get API key from user
read -p "Enter LangSmith API key (from https://smith.langchain.com/settings): " LANGSMITH_API_KEY
if [ -z "$LANGSMITH_API_KEY" ]; then
  echo "❌ API key required"
  exit 1
fi

# Export environment
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=$LANGSMITH_API_KEY
export LANGSMITH_PROJECT=aegis-rag-sprint115

echo "✅ Environment variables set"
echo "   LANGSMITH_TRACING=$LANGSMITH_TRACING"
echo "   LANGSMITH_PROJECT=$LANGSMITH_PROJECT"

# Restart Docker API
echo "🔄 Restarting API with LangSmith enabled..."
docker compose -f docker-compose.dgx-spark.yml up -d --force-recreate api

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API ready"
    break
  fi
  echo "  Attempt $i/30..."
  sleep 2
done

# Start frontend in background
echo "🚀 Starting frontend dev server..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Quick start:"
echo "   Terminal 3: cd frontend && npm run test:e2e"
echo ""
echo "📊 View traces:"
echo "   https://smith.langchain.com/projects/$LANGSMITH_PROJECT?tab=runs"
echo ""
echo "📚 Documentation:"
echo "   docs/e2e/LANGSMITH_PLAYWRIGHT_SETUP.md"
echo ""
```

## Architecture Decision: Why Only Local?

### Why Not CI/CD?

1. **Cost** - Each test generates trace API call ($0.0001-0.001 per call)
   - 200 tests × 10 LLM calls = 2,000 traces/run
   - Multiple runs per day = $0.10-1.00/day cost

2. **Noise** - Trace project becomes unreadable
   - Development traces mixed with test traces
   - Hard to find relevant production issues

3. **Reliability** - External dependency adds failure points
   - Network issues block CI/CD
   - LangSmith API downtime breaks pipelines

4. **Security** - API key exposure in logs
   - GitHub Actions logs are visible in PRs
   - Secrets can leak in error messages

### Why Local?

1. **Debugging** - Manual investigation requires full trace visibility
2. **Performance** - Single local run vs 200 CI runs
3. **Flexible** - Enable only when needed
4. **Isolated** - No impact on other team members

## See Also

- [Playwright E2E Documentation](/home/admin/projects/aegisrag/AEGIS_Rag/docs/e2e/PLAYWRIGHT_E2E.md)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangChain Tracing](https://docs.langchain.com/docs/guides/tracing/)
- [Infrastructure Agent Notes](docs/CLAUDE.md#infrastructure-agent-notes)

## Sprint 115 Changes

- Sprint 115 Feature 115.6: LangSmith integration for Playwright tests
- Created `frontend/e2e/setup/langsmith.ts` fixture for test helpers
- Explicitly disabled LangSmith in all CI/CD workflows
- Added comprehensive documentation for local setup
- Verified no traces generated during CI/CD runs

## Questions?

- Check existing traces: https://smith.langchain.com
- Review setup file: `frontend/e2e/setup/langsmith.ts`
- See example test: `frontend/e2e/setup/langsmith.example.spec.ts`
- Check documentation: `docs/e2e/LANGSMITH_PLAYWRIGHT_SETUP.md`
