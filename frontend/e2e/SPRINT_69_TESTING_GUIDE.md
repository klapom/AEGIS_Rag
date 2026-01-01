# Sprint 69 E2E Testing Quick Start Guide

**Date:** 2026-01-01
**Feature:** Sprint 69.1 - E2E Test Fixes & Stabilization

---

## Overview

Sprint 69 introduces comprehensive E2E test improvements including:
- **Test Data Fixtures** for consistent testing
- **Retry Utilities** for robust async operations
- **Follow-up Context Tests** (10 new tests)
- **Memory Consolidation Tests** (10 new tests)

---

## Prerequisites

### 1. Backend Services Running
Ensure all required services are running:

```bash
# Check services status
docker compose -f docker-compose.dgx-spark.yml ps

# Required services:
# - Backend API (port 8000)
# - Frontend (port 5179)
# - Qdrant (port 6333)
# - Neo4j (port 7687)
# - Redis (port 6379)
# - Ollama (port 11434)
```

### 2. Test Environment Setup

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend

# Install dependencies
npm install

# Install Playwright browsers (if not done)
npx playwright install
```

---

## Running Tests

### Quick Test Commands

#### Run All New Tests
```bash
# Follow-up context tests (10 tests)
npm run test:e2e -- followup/follow-up-context.spec.ts

# Memory consolidation tests (10 tests)
npm run test:e2e -- memory/consolidation.spec.ts

# Run both
npm run test:e2e -- followup/follow-up-context.spec.ts memory/consolidation.spec.ts
```

#### Run Specific Test Case
```bash
# Run single test by ID
npm run test:e2e -- followup/follow-up-context.spec.ts --grep "TC-69.1.1"

# Run by description
npm run test:e2e -- --grep "maintain context from initial query"
```

#### Run with Debug Output
```bash
# Enable verbose logging
npm run test:e2e -- followup/follow-up-context.spec.ts --debug

# Run headed (see browser)
npm run test:e2e -- followup/follow-up-context.spec.ts --headed

# Both
npm run test:e2e -- followup/follow-up-context.spec.ts --headed --debug
```

#### Run Full E2E Suite
```bash
# All E2E tests (including new tests)
npm run test:e2e

# Parallel execution (faster)
npm run test:e2e -- --workers=4
```

---

## Test Suites

### 1. Follow-up Context Tests
**File:** `followup/follow-up-context.spec.ts`
**Tests:** 10
**Duration:** ~150s total (~15s per test)

**Test Cases:**
- TC-69.1.1: Follow-up maintains context from initial query
- TC-69.1.2: Multi-turn follow-ups maintain full context chain
- TC-69.1.3: Context preserved across different query types
- TC-69.1.4: Generic follow-up inherits specific context
- TC-69.1.5: Key entities from initial query appear in follow-up
- TC-69.1.6: Session context persists across follow-ups
- TC-69.1.7: Citations maintained in follow-up responses
- TC-69.1.8: Long conversations maintain recent context
- TC-69.1.9: Brief responses maintain context
- TC-69.1.10: Follow-ups work after error recovery

**Run:**
```bash
npm run test:e2e -- followup/follow-up-context.spec.ts
```

### 2. Memory Consolidation Tests
**File:** `memory/consolidation.spec.ts`
**Tests:** 10
**Duration:** ~200s total (~20s per test)

**Test Cases:**
- TC-69.1.11: Consolidation status transitions correctly
- TC-69.1.12: Short-term memory persists after reload
- TC-69.1.13: Long conversation triggers consolidation
- TC-69.1.14: New messages work during consolidation
- TC-69.1.15: Recent messages accessible after consolidation
- TC-69.1.16: Conversation coherence after consolidation
- TC-69.1.17: Independent sessions don't conflict
- TC-69.1.18: Chat works if memory service unavailable
- TC-69.1.19: Consolidation timeout handled gracefully
- TC-69.1.20: Consolidation completes within timeout

**Run:**
```bash
npm run test:e2e -- memory/consolidation.spec.ts
```

---

## Using New Test Utilities

### Test Data Fixtures

Import reusable test data:

```typescript
import {
  TEST_QUERIES,
  EXPECTED_PATTERNS,
  TEST_TIMEOUTS,
  TEST_DOCUMENTS,
  ASSERTIONS,
  TEST_UTILS
} from '../fixtures/test-data';

// Use predefined queries
await chatPage.sendMessage(TEST_QUERIES.OMNITRACKER.SMC_OVERVIEW);

// Use consistent timeouts
await chatPage.waitForResponse(TEST_TIMEOUTS.LLM_RESPONSE);

// Verify patterns
const response = await chatPage.getLastMessage();
expect(EXPECTED_PATTERNS.OMNITRACKER.SMC.test(response)).toBeTruthy();
```

### Retry Utilities

Import robust retry functions:

```typescript
import {
  retryAssertion,
  waitForCount,
  waitForText,
  RetryPresets
} from '../utils/retry';

// Retry assertions
await retryAssertion(
  async () => {
    const count = await chatPage.getFollowupQuestionCount();
    expect(count).toBeGreaterThanOrEqual(3);
  },
  RetryPresets.PATIENT  // 5 retries, 2s delay
);

// Wait for element count
await waitForCount(
  () => page.locator('.item').count(),
  5,
  RetryPresets.STANDARD
);

// Wait for text
await waitForText(
  page.locator('.status'),
  /complete/i,
  RetryPresets.QUICK
);
```

### Enhanced ChatPage Methods

Use new context tracking methods:

```typescript
// Get conversation context
const recentMessages = await chatPage.getConversationContext(3);

// Verify context maintained
const hasContext = await chatPage.verifyContextMaintained([
  'OMNITRACKER', 'SMC', 'management'
]);

// Wait for message count
await chatPage.waitForMessageCount(6);  // 3 Q + 3 A

// Click follow-up with context verification
await chatPage.clickFollowupAndVerifyContext(
  0,  // First follow-up
  ['OMNITRACKER', 'database', 'connection']
);
```

---

## Debugging Failed Tests

### Common Failures

#### 1. Follow-up Questions Not Generated
```
Error: Follow-up questions not generated
```

**Diagnosis:**
```bash
# Check backend logs
docker compose logs api | grep "follow-up"

# Check LLM service
curl http://localhost:11434/api/tags
```

**Fix:**
- Verify Ollama is running
- Check LLM model loaded
- Increase retry timeout in test

#### 2. Context Not Maintained
```
Error: Context not maintained. Expected: OMNITRACKER. Got: ...
```

**Diagnosis:**
- Print actual response in test
- Check if LLM model supports conversation context
- Verify context keywords are reasonable

**Fix:**
```typescript
// Add debug logging
const response = await chatPage.getLastMessage();
console.log('Response:', response);
console.log('Expected keywords:', ['OMNITRACKER', 'SMC']);
```

#### 3. Memory Consolidation Timeout
```
Error: Consolidation not triggered
```

**Diagnosis:**
```bash
# Check memory services
docker compose ps redis graphiti

# Check backend logs
docker compose logs api | grep "memory"
```

**Fix:**
- Verify Redis is running
- Check Graphiti service
- Increase consolidation timeout

### Enable Verbose Logging

```bash
# Run with debug output
DEBUG=pw:api npm run test:e2e -- followup/follow-up-context.spec.ts

# Playwright trace
npm run test:e2e -- followup/follow-up-context.spec.ts --trace on

# View trace
npx playwright show-trace trace.zip
```

### Test in Isolation

```bash
# Run single test
npm run test:e2e -- --grep "TC-69.1.1"

# Run headed (see browser)
npm run test:e2e -- --grep "TC-69.1.1" --headed --slowMo=500

# Run with specific browser
npm run test:e2e -- --grep "TC-69.1.1" --project=chromium
```

---

## Performance Tips

### Parallel Execution

```bash
# Run tests in parallel (4 workers)
npm run test:e2e -- --workers=4

# Disable parallelism (debugging)
npm run test:e2e -- --workers=1
```

### Timeout Configuration

Adjust timeouts in `playwright.config.ts`:

```typescript
use: {
  timeout: 90000,  // 90s per test
  navigationTimeout: 30000,  // 30s for page loads
  actionTimeout: 10000,  // 10s for actions
}
```

Or in individual tests:

```typescript
test('long running test', async ({ chatPage }) => {
  test.setTimeout(180000);  // 3 minutes
  // Test code
});
```

---

## Test Reports

### View HTML Report

```bash
# Generate report
npm run test:e2e

# Open report
npx playwright show-report
```

### Generate Coverage Report

```bash
# Run tests with coverage
npm run test:e2e -- --coverage

# View coverage
open coverage/index.html
```

### CI/CD Integration

Tests run automatically in CI:

```yaml
# .github/workflows/e2e.yml
- name: Run E2E Tests
  run: |
    npm run test:e2e -- followup/follow-up-context.spec.ts
    npm run test:e2e -- memory/consolidation.spec.ts
```

---

## Best Practices

### 1. Use Retry Logic for Async Operations

✅ **Good:**
```typescript
await retryAssertion(
  async () => {
    const count = await chatPage.getFollowupQuestionCount();
    expect(count).toBeGreaterThanOrEqual(3);
  },
  RetryPresets.PATIENT
);
```

❌ **Bad:**
```typescript
await page.waitForTimeout(5000);  // Fixed timeout - flaky!
const count = await chatPage.getFollowupQuestionCount();
expect(count).toBeGreaterThanOrEqual(3);
```

### 2. Use Test Data Fixtures

✅ **Good:**
```typescript
await chatPage.sendMessage(TEST_QUERIES.OMNITRACKER.SMC_OVERVIEW);
await chatPage.waitForResponse(TEST_TIMEOUTS.LLM_RESPONSE);
```

❌ **Bad:**
```typescript
await chatPage.sendMessage('What is OMNITRACKER SMC?');
await chatPage.waitForResponse(90000);
```

### 3. Verify Context, Not Exact Text

✅ **Good:**
```typescript
const hasContext = await chatPage.verifyContextMaintained([
  'OMNITRACKER', 'SMC', 'management'
]);
expect(hasContext).toBeTruthy();
```

❌ **Bad:**
```typescript
const response = await chatPage.getLastMessage();
expect(response).toBe('The OMNITRACKER SMC is...');  // Too brittle!
```

### 4. Use Descriptive Test Names

✅ **Good:**
```typescript
test('TC-69.1.1: follow-up maintains context from initial query', ...)
```

❌ **Bad:**
```typescript
test('test 1', ...)
```

---

## Next Steps

### Phase 1: Verify Implementation (Current)
1. Run all new tests: `npm run test:e2e -- followup/follow-up-context.spec.ts memory/consolidation.spec.ts`
2. Verify 100% pass rate
3. Check retry statistics

### Phase 2: Expand Coverage (Future)
1. Apply retry logic to existing tests
2. Convert tests to use test data fixtures
3. Add context verification to all follow-up tests

### Phase 3: Performance Optimization (Future)
1. Parallel test execution
2. Test result caching
3. Mock LLM responses for faster tests

---

## Troubleshooting Checklist

Before running tests, verify:

- [ ] Backend API running (http://localhost:8000/health)
- [ ] Frontend running (http://localhost:5179)
- [ ] Qdrant running (http://localhost:6333)
- [ ] Neo4j running (bolt://localhost:7687)
- [ ] Redis running (localhost:6379)
- [ ] Ollama running (http://localhost:11434)
- [ ] Playwright browsers installed (`npx playwright install`)
- [ ] Node dependencies installed (`npm install`)

---

## Support & Resources

- **Documentation:** `/docs/sprints/SPRINT_69_FEATURE_69.1_SUMMARY.md`
- **Retry Utilities:** `/frontend/e2e/utils/retry.ts`
- **Test Data Fixtures:** `/frontend/e2e/fixtures/test-data.ts`
- **ChatPage POM:** `/frontend/e2e/pom/ChatPage.ts`

---

**Last Updated:** 2026-01-01
**Sprint:** 69
**Feature:** 69.1
