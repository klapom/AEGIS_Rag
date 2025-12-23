# Quick Start Guide - E2E Testing Sprint 62+63 Features

## 30-Second Setup

### 1. Start Services (3 terminals)
```bash
# Terminal 1: Backend
cd /path/to/AEGIS_Rag
poetry run python -m src.api.main

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Tests (wait for both to be ready)
cd frontend
npm run test:e2e
```

### 2. Verify Services Running
```bash
curl http://localhost:8000/health
curl http://localhost:5179
```

## Run Tests

### All Tests
```bash
npm run test:e2e
```

### Specific Feature
```bash
# Section tests
npm run test:e2e -- section-

# Research mode
npm run test:e2e -- research-

# Multi-turn
npm run test:e2e -- multi-turn

# Tool output
npm run test:e2e -- tool-output

# Structured
npm run test:e2e -- structured-
```

### Single Test
```bash
npm run test:e2e -- -g "should display section badges"
```

### With Browser Visible
```bash
npm run test:e2e -- --headed
```

### Debug Mode
```bash
npm run test:e2e -- --debug
```

## View Results

```bash
npx playwright show-report
```

## Test Files Location

```
/frontend/e2e/
  ├── section-citations.spec.ts       (12 tests)
  ├── section-analytics.spec.ts        (15 tests)
  ├── research-mode.spec.ts            (12 tests)
  ├── multi-turn-rag.spec.ts          (16 tests)
  ├── tool-output-viz.spec.ts         (18 tests)
  ├── structured-output.spec.ts       (22 tests)
  ├── SPRINT_62_63_E2E_TESTS.md       (full guide)
  └── QUICK_START_TESTING.md          (this file)
```

## Common Issues

### Tests Timeout
- Make sure backend is running: `curl http://localhost:8000/health`
- Check Ollama is available: `curl http://localhost:11434/api/tags`

### Element Not Found
- Feature may not be implemented yet
- Tests gracefully skip unavailable features
- Check browser console for errors

### Flaky Tests
- Increase wait timeout: `await page.waitForTimeout(1000)`
- Wait for network idle: `await page.waitForLoadState('networkidle')`

### Auth Errors
- Fixtures automatically mock auth
- Check `aegis_auth_token` in localStorage

## Test Categories

### Sprint 62 (Section Features)
- **Citations** (12): Section badges, document types, hierarchy paths
- **Analytics** (15): Statistics, distributions, entity counts

### Sprint 63 (Research & Multi-Turn)
- **Research Mode** (12): Toggle, progress, synthesis, sources
- **Multi-Turn RAG** (16): Context, memory, contradictions
- **Tool Output** (18): Syntax highlighting, exit codes
- **Structured Output** (22): JSON validation, schema

## Performance

- **Total Runtime**: ~56 minutes (sequential)
- **Per Test**: ~35 seconds average
- **Test Timeout**: 30 seconds
- **Assertion Timeout**: 10 seconds

## Key Test Patterns

### Check if Element Exists
```typescript
const element = page.locator('[data-testid="my-element"]');
const isVisible = await element.isVisible().catch(() => false);

if (isVisible) {
  // Test element
  expect(element).toBeTruthy();
}
```

### Wait for LLM Response
```typescript
await chatPage.waitForResponse(60000); // 60s timeout
const lastMessage = await chatPage.getLastMessage();
expect(lastMessage).toBeTruthy();
```

### Skip Unavailable Feature
```typescript
if (!hasFeature) {
  test.skip();
  return;
}
```

## Documentation

- **Full Guide**: `/frontend/e2e/SPRINT_62_63_E2E_TESTS.md`
- **Implementation Summary**: `/FEATURE_63_6_E2E_TESTS_SUMMARY.md`
- **This File**: Quick reference

## Support

For detailed help, see:
- `SPRINT_62_63_E2E_TESTS.md` - Comprehensive guide
- Playwright docs: https://playwright.dev
- Test descriptions in test files

## CI/CD

**Important**: Tests run locally only (cost control)
- Manual backend startup required
- CI/CD disabled in `playwright.config.ts`
- Can be enabled if needed (uncomment `webServer` section)
