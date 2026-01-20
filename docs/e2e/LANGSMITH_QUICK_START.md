# LangSmith + Playwright Quick Start (5 Minutes)

## 1-Minute Summary

LangSmith traces show you exactly what your LLM is doing - every call, every token, every delay. Enabled locally for debugging, **always disabled in CI/CD**.

## Quick Start (No Reading!)

```bash
# Terminal 1: Get API key from https://smith.langchain.com/settings
export LANGSMITH_API_KEY=sk-YOUR-KEY-HERE
export LANGSMITH_TRACING=true

# Terminal 1: Restart API
docker compose -f docker-compose.dgx-spark.yml up -d --force-recreate api
sleep 10

# Terminal 2: Start frontend
cd frontend && npm run dev

# Terminal 3: Run tests
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test

# Terminal 4: View traces
open https://smith.langchain.com/projects/aegis-rag-sprint115?tab=runs
```

Done! You'll see LLM traces appear in real-time.

## What You'll See in LangSmith

```
Run 1: test-group08-deep-research
├─ LLM Call: Query Understanding
│  ├─ Input: 274 tokens
│  ├─ Output: 89 tokens
│  └─ Duration: 1.2s
├─ LLM Call: Graph Expansion
│  ├─ Input: 512 tokens
│  ├─ Output: 156 tokens
│  └─ Duration: 2.8s
└─ LLM Call: Answer Generation
   ├─ Input: 1024 tokens
   ├─ Output: 234 tokens
   └─ Duration: 8.5s
```

## Common Commands

```bash
# Enable LangSmith for single test run
LANGSMITH_TRACING=true LANGSMITH_API_KEY=sk-... npm run test:e2e

# Run only fast tests (with tracing)
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --grep @fast

# Run specific test file
npx playwright test group08-deep-research.spec.ts

# Check if backend is configured correctly
curl http://localhost:8000/health | jq '.environment.langsmith'

# View API logs for tracing
docker logs aegis-api | grep -i langsmith

# Disable tracing (default)
LANGSMITH_TRACING=false npm run test:e2e
```

## CI/CD Status: ALWAYS DISABLED ✅

All GitHub Actions workflows explicitly disable LangSmith:

```bash
# Verify in CI/CD
grep -B2 -A2 "LANGSMITH_TRACING.*false" .github/workflows/ci.yml

# Result: ✅ LangSmith disabled in CI/CD
```

**Why?** Prevents cost overhead ($0.10+/day), trace project noise, and external dependencies.

## Troubleshooting (30 Seconds)

| Issue | Fix |
|-------|-----|
| Tests timeout | `docker logs aegis-api \| head -20` |
| No traces appear | Verify: `docker exec aegis-api printenv \| grep LANGSMITH` |
| API won't start | Restart: `docker compose up -d --force-recreate api` |
| Wrong project | Check: `.env` file has `LANGSMITH_PROJECT=aegis-rag-sprint115` |

## Files Modified

```
✅ frontend/e2e/setup/langsmith.ts
   └─ Pytest fixture for LangSmith helpers

✅ frontend/e2e/setup/langsmith.example.spec.ts
   └─ Example tests showing usage patterns

✅ .github/workflows/ci.yml
   └─ Unit/integration tests: LangSmith disabled

✅ .github/workflows/e2e.yml
   └─ E2E tests: LangSmith disabled

✅ docker-compose.dgx-spark.yml
   └─ Already has LangSmith vars (no change needed)

✅ docs/e2e/LANGSMITH_PLAYWRIGHT_SETUP.md
   └─ Full setup guide with troubleshooting

✅ docs/e2e/LANGSMITH_QUICK_START.md
   └─ This file!
```

## Next Steps

1. **Get LangSmith API Key:** https://smith.langchain.com/settings
2. **Run Setup Script:** See full guide in `LANGSMITH_PLAYWRIGHT_SETUP.md`
3. **View Traces:** https://smith.langchain.com/projects/aegis-rag-sprint115?tab=runs
4. **Explore Patterns:** Check example tests in `frontend/e2e/setup/langsmith.example.spec.ts`

## API Reference

From `frontend/e2e/setup/langsmith.ts`:

```typescript
// Get LangSmith project URL
langsmith.getProjectUrl()
// → "https://smith.langchain.com/projects/aegis-rag-sprint115?tab=runs"

// Check if tracing is enabled
langsmith.isEnabled()
// → true or false

// Log current status
langsmith.logStatus('my-test-name')
// → "[my-test-name] LangSmith tracing: enabled"
//    "View traces: https://smith.langchain.com/..."

// Get environment variables
langsmith.getEnvironmentVariables()
// → { LANGSMITH_TRACING: 'true', LANGSMITH_API_KEY: '...', ... }
```

## Key Principles

1. **Local Only** - Tracing enabled locally for debugging
2. **CI/CD Safe** - All workflows explicitly disable (no automatic traces)
3. **Zero CI/CD Cost** - No LangSmith API calls in pipelines
4. **Easy Toggle** - One env var: `LANGSMITH_TRACING=true/false`

---

**Need more?** Read `docs/e2e/LANGSMITH_PLAYWRIGHT_SETUP.md` for complete guide.
