# Sprint 69 E2E Test Infrastructure

**Sprint:** 69
**Feature:** 69.1 - E2E Test Fixes & Stabilization
**Date:** 2026-01-01
**Story Points:** 13

---

## Overview

Sprint 69 introduces a comprehensive E2E test infrastructure to achieve 100% test pass rate and eliminate flaky tests caused by race conditions and timing issues.

### Key Additions

1. **Test Data Fixtures** (`fixtures/test-data.ts`) - 11KB
   - Reusable test documents, queries, and expected patterns
   - Consistent test data across all E2E suites

2. **Retry Utilities** (`utils/retry.ts`) - 12KB
   - Robust retry logic for async operations
   - Configurable presets for common scenarios

3. **Follow-up Context Tests** (`followup/follow-up-context.spec.ts`) - 15KB
   - 10 comprehensive test cases
   - Context preservation verification

4. **Memory Consolidation Tests** (`memory/consolidation.spec.ts`) - 13KB
   - 10 test cases for race condition prevention
   - Async operation validation

5. **Enhanced ChatPage POM** (`pom/ChatPage.ts`)
   - Context tracking methods
   - Message verification helpers

---

## File Structure

```
frontend/e2e/
├── fixtures/
│   ├── index.ts              # POM fixtures (existing)
│   └── test-data.ts          # ✨ NEW: Test data fixtures (11KB)
│
├── utils/
│   ├── index.ts              # ✨ NEW: Utilities index
│   └── retry.ts              # ✨ NEW: Retry utilities (12KB)
│
├── pom/
│   └── ChatPage.ts           # ✨ UPDATED: Context tracking
│
├── followup/
│   ├── followup.spec.ts      # Existing follow-up tests
│   └── follow-up-context.spec.ts  # ✨ NEW: Context tests (15KB)
│
├── memory/
│   └── consolidation.spec.ts # ✨ NEW: Memory tests (13KB)
│
├── docs/
│   ├── SPRINT_69_TESTING_GUIDE.md   # Quick start guide
│   └── README_SPRINT_69.md          # This file
│
└── docs/sprints/
    └── SPRINT_69_FEATURE_69.1_SUMMARY.md  # Complete documentation
```

---

## Quick Start

### 1. Run New Tests

```bash
# Follow-up context tests (10 tests, ~150s)
npm run test:e2e -- followup/follow-up-context.spec.ts

# Memory consolidation tests (10 tests, ~200s)
npm run test:e2e -- memory/consolidation.spec.ts

# All new tests
npm run test:e2e -- followup/follow-up-context.spec.ts memory/consolidation.spec.ts
```

### 2. Use Test Utilities

```typescript
import { TEST_QUERIES, TEST_TIMEOUTS, EXPECTED_PATTERNS } from '../fixtures/test-data';
import { retryAssertion, RetryPresets } from '../utils/retry';

test('example test', async ({ chatPage }) => {
  // Use test data fixtures
  await chatPage.sendMessage(TEST_QUERIES.OMNITRACKER.SMC_OVERVIEW);
  await chatPage.waitForResponse(TEST_TIMEOUTS.LLM_RESPONSE);

  // Use retry logic
  await retryAssertion(
    async () => {
      const count = await chatPage.getFollowupQuestionCount();
      expect(count).toBeGreaterThanOrEqual(3);
    },
    RetryPresets.PATIENT
  );

  // Verify patterns
  const response = await chatPage.getLastMessage();
  expect(EXPECTED_PATTERNS.OMNITRACKER.SMC.test(response)).toBeTruthy();
});
```

### 3. Use Enhanced ChatPage Methods

```typescript
// Get conversation context
const recentMessages = await chatPage.getConversationContext(3);

// Verify context maintained
const hasContext = await chatPage.verifyContextMaintained([
  'OMNITRACKER', 'SMC'
]);

// Click follow-up with verification
await chatPage.clickFollowupAndVerifyContext(0, ['OMNITRACKER', 'database']);
```

---

## Test Coverage

### New Tests Added

| Test Suite | Tests | Duration | File |
|------------|-------|----------|------|
| Follow-up Context | 10 | ~150s | `followup/follow-up-context.spec.ts` |
| Memory Consolidation | 10 | ~200s | `memory/consolidation.spec.ts` |
| **Total** | **20** | **~350s** | - |

### Test Cases

#### Follow-up Context Tests (TC-69.1.1 to TC-69.1.10)
1. Follow-up maintains context from initial query
2. Multi-turn follow-ups maintain full context chain
3. Context preserved across different query types
4. Generic follow-up inherits specific context
5. Key entities from initial query appear in follow-up
6. Session context persists across follow-ups
7. Citations maintained in follow-up responses
8. Long conversations maintain recent context
9. Brief responses maintain context
10. Follow-ups work after error recovery

#### Memory Consolidation Tests (TC-69.1.11 to TC-69.1.20)
11. Consolidation status transitions correctly
12. Short-term memory persists after reload
13. Long conversation triggers consolidation
14. New messages work during consolidation
15. Recent messages accessible after consolidation
16. Conversation coherence after consolidation
17. Independent sessions don't conflict
18. Chat works if memory service unavailable
19. Consolidation timeout handled gracefully
20. Consolidation completes within timeout

---

## Key Features

### 1. Test Data Fixtures

**Location:** `fixtures/test-data.ts`

**Exports:**
- `TEST_DOCUMENTS`: Sample documents for testing
- `TEST_QUERIES`: Domain-specific test queries
- `EXPECTED_PATTERNS`: Regex patterns for verification
- `MOCK_MEMORY`: Mock memory data
- `MOCK_GRAPH`: Mock graph data
- `TEST_TIMEOUTS`: Consistent timeout values
- `ASSERTIONS`: Common assertion helpers
- `TEST_UTILS`: Utility functions

**Usage:**
```typescript
import {
  TEST_QUERIES,
  EXPECTED_PATTERNS,
  TEST_TIMEOUTS
} from '../fixtures/test-data';
```

### 2. Retry Utilities

**Location:** `utils/retry.ts`

**Functions:**
- `retryAsync<T>()`: Retry any async function
- `retryAssertion()`: Retry assertions
- `waitForLocator()`: Wait for element state
- `waitForCount()`: Wait for count match
- `waitForText()`: Wait for text pattern
- `waitForNetworkIdle()`: Wait for network
- `retryExpect()`: Retry expect assertions
- `waitForCondition()`: Wait for custom condition
- `retryAction()`: Retry page actions
- `waitForResponse()`: Wait for API response

**Presets:**
```typescript
RetryPresets.QUICK       // 3 retries, 500ms
RetryPresets.STANDARD    // 3 retries, 1s
RetryPresets.PATIENT     // 5 retries, 2s
RetryPresets.AGGRESSIVE  // 10 retries, exponential backoff
RetryPresets.LLM_RESPONSE // 3 retries, 5s
RetryPresets.NETWORK     // 5 retries, 2s, backoff
```

### 3. Enhanced ChatPage POM

**Location:** `pom/ChatPage.ts`

**New Methods:**
- `getConversationContext(count)`: Get last N messages
- `verifyContextMaintained(keywords)`: Check context preservation
- `getMessageByIndex(index)`: Get specific message
- `waitForMessageCount(count)`: Wait for message count
- `clickFollowupAndVerifyContext(index, keywords)`: Click with verification

---

## Best Practices

### ✅ Use Retry Logic

```typescript
// Good: Robust retry
await retryAssertion(
  async () => expect(await page.locator('.item').count()).toBe(5),
  RetryPresets.STANDARD
);

// Bad: Fixed timeout
await page.waitForTimeout(5000);
expect(await page.locator('.item').count()).toBe(5);
```

### ✅ Use Test Data Fixtures

```typescript
// Good: Reusable fixtures
await chatPage.sendMessage(TEST_QUERIES.OMNITRACKER.SMC_OVERVIEW);

// Bad: Hardcoded strings
await chatPage.sendMessage('What is OMNITRACKER SMC?');
```

### ✅ Verify Context, Not Exact Text

```typescript
// Good: Pattern matching
expect(EXPECTED_PATTERNS.OMNITRACKER.SMC.test(response)).toBeTruthy();

// Bad: Exact match
expect(response).toBe('The OMNITRACKER SMC is...');
```

### ✅ Use Descriptive Test Names

```typescript
// Good: Clear identifier
test('TC-69.1.1: follow-up maintains context from initial query', ...)

// Bad: Vague name
test('test 1', ...)
```

---

## Performance Tips

### Parallel Execution
```bash
# Run tests in parallel (faster)
npm run test:e2e -- --workers=4

# Sequential (debugging)
npm run test:e2e -- --workers=1
```

### Selective Testing
```bash
# Run single test case
npm run test:e2e -- --grep "TC-69.1.1"

# Run specific suite
npm run test:e2e -- followup/follow-up-context.spec.ts
```

### Timeout Configuration
```typescript
// Adjust per test
test('long test', async ({ chatPage }) => {
  test.setTimeout(180000);  // 3 minutes
});

// Or use global config in playwright.config.ts
```

---

## Troubleshooting

### Common Issues

**Issue:** Follow-up questions not generated
```
Error: Follow-up questions not generated
```
**Solution:**
- Check backend LLM service running
- Increase retry timeout: `RetryPresets.AGGRESSIVE`
- Verify Ollama model loaded

**Issue:** Context not maintained
```
Error: Context not maintained. Expected: OMNITRACKER
```
**Solution:**
- Verify LLM supports conversation context
- Check context keywords are in response
- Add debug logging to inspect response

**Issue:** Memory consolidation timeout
```
Error: Consolidation not triggered
```
**Solution:**
- Check Redis and Graphiti services running
- Verify backend consolidation threshold
- Increase timeout: `TEST_TIMEOUTS.MEMORY_CONSOLIDATION`

### Debug Mode

```bash
# Run with trace
npm run test:e2e -- --trace on followup/follow-up-context.spec.ts

# View trace
npx playwright show-trace trace.zip

# Headed mode (see browser)
npm run test:e2e -- --headed followup/follow-up-context.spec.ts
```

---

## Documentation

- **Quick Start Guide:** `frontend/e2e/SPRINT_69_TESTING_GUIDE.md`
- **Feature Summary:** `docs/sprints/SPRINT_69_FEATURE_69.1_SUMMARY.md`
- **Retry Utilities Docs:** `frontend/e2e/utils/retry.ts` (JSDoc comments)
- **Test Data Docs:** `frontend/e2e/fixtures/test-data.ts` (JSDoc comments)

---

## Metrics

### Implementation Metrics

| Metric | Value |
|--------|-------|
| New Test Files | 2 |
| New Utility Files | 2 |
| Updated POM Files | 1 |
| Total New Tests | 20 |
| Lines of Code Added | ~1,200 |
| Documentation Pages | 3 |

### Test Metrics (Target)

| Metric | Before | After (Target) |
|--------|--------|----------------|
| Total E2E Tests | 606 | 626 |
| Pass Rate | 56% | 100% |
| Failing Tests | 266 | 0 |
| Avg Retry Rate | N/A | <5% |

---

## Future Enhancements

### Phase 2 (Upcoming Sprints)

1. **Apply to Existing Tests**
   - Convert existing tests to use retry logic
   - Migrate to test data fixtures
   - Add context verification

2. **Performance Tests**
   - Load testing for consolidation
   - Stress testing with 100+ messages
   - Concurrent session testing

3. **Advanced Features**
   - Semantic similarity for context
   - Entity extraction verification
   - Citation relevance scoring

4. **Test Data Generation**
   - Auto-generate from real docs
   - Mock LLM responses
   - Synthetic conversation generation

---

## Contributing

When adding new E2E tests:

1. **Use Test Data Fixtures**
   - Add new queries to `TEST_QUERIES`
   - Add patterns to `EXPECTED_PATTERNS`
   - Use `TEST_TIMEOUTS` for consistency

2. **Use Retry Logic**
   - Wrap async assertions in `retryAssertion()`
   - Use appropriate preset: `RetryPresets.STANDARD`
   - Log retry attempts for debugging

3. **Follow Naming Convention**
   - Test ID: `TC-{Sprint}.{Feature}.{Number}`
   - Description: Clear, actionable
   - Example: `TC-69.1.1: follow-up maintains context`

4. **Document Tests**
   - Add JSDoc comments
   - Update test count in README
   - Update Sprint summary

---

## Support

For questions or issues:

1. Check documentation:
   - This README
   - `SPRINT_69_TESTING_GUIDE.md`
   - Feature summary

2. Review test code:
   - Follow-up tests for context examples
   - Memory tests for async patterns
   - Retry utilities for error handling

3. Run in debug mode:
   - Use `--headed --debug`
   - Enable trace: `--trace on`
   - Check console logs

---

**Last Updated:** 2026-01-01
**Sprint:** 69
**Feature:** 69.1
**Author:** Testing Agent (Claude Sonnet 4.5)
