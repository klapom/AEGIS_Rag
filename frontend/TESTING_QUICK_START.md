# AEGIS RAG Frontend Testing - Quick Start Guide

## Running Tests

### Run All Tests
```bash
npm test
```

### Run Specific Test Suite
```bash
# HomePage tests
npm test HomePage.e2e.test

# SearchResultsPage tests
npm test SearchResultsPage.e2e.test

# SSE Streaming tests
npm test SSEStreaming.e2e.test

# Error handling tests
npm test ErrorHandling.e2e.test

# Full workflow tests
npm test FullWorkflow.e2e.test
```

### Watch Mode (Auto-rerun on changes)
```bash
npm run test:watch
```

### Interactive UI
```bash
npm run test:ui
```

### Coverage Report
```bash
npm run test:coverage
```

## Test Results Summary

**Total Tests**: 144
**Passing**: 105 (72.9%)
**Failing**: 39 (27.1%)

### Passing Test Suites
- ✅ **HomePage.e2e.test.tsx**: 17/17 tests passing (100%)
- ✅ **SearchResultsPage.e2e.test.tsx**: 16/16 tests passing (100%)
- ✅ **ErrorHandling.e2e.test.tsx**: 24/25 tests passing (96%)

### Partially Passing Test Suites
- ⚠️ **SSEStreaming.e2e.test.tsx**: 19/28 tests passing (68%)
- ⚠️ **FullWorkflow.e2e.test.tsx**: 9/20 tests passing (45%)

## What's Tested

### User Workflows ✅
- Search query submission
- Mode selection (Hybrid, Vector, Graph, Memory)
- Quick prompts
- Navigation flows
- Error handling

### SSE Streaming ✅
- Token-by-token display
- Source cards
- Metadata display
- Stream completion
- Error recovery

### Error Scenarios ✅
- Network failures
- HTTP errors (4xx, 5xx)
- Malformed data
- Timeout handling

### Edge Cases ✅
- Empty queries
- Long queries
- Special characters
- URL encoding
- Invalid parameters

## Test File Structure

```
frontend/src/test/e2e/
├── fixtures.ts                    # Mock data and test fixtures
├── helpers.ts                     # Test utility functions
├── HomePage.e2e.test.tsx          # Landing page tests
├── SearchResultsPage.e2e.test.tsx # Results page tests
├── SSEStreaming.e2e.test.tsx      # Streaming tests
├── ErrorHandling.e2e.test.tsx     # Error scenario tests
├── FullWorkflow.e2e.test.tsx      # Complete workflow tests
├── README.md                      # Detailed documentation
└── index.ts                       # Centralized exports
```

## Quick Test Examples

### Testing Search Submission
```typescript
it('should submit query on Enter key press', async () => {
  render(<HomePage />);

  const input = screen.getByPlaceholderText(/Fragen Sie/i);
  fireEvent.change(input, { target: { value: 'test query' } });
  fireEvent.keyDown(input, { key: 'Enter' });

  await waitFor(() => {
    expect(mockNavigate).toHaveBeenCalledWith('/search?q=test%20query');
  });
});
```

### Testing SSE Streaming
```typescript
it('should display streaming tokens', async () => {
  setupGlobalFetchMock(mockFetchSSESuccess());

  render(<StreamingAnswer query="test" mode="hybrid" />);

  await waitFor(() => {
    expect(screen.getByText(/This is a test answer/i)).toBeInTheDocument();
  });
});
```

### Testing Error Handling
```typescript
it('should show error on network failure', async () => {
  setupGlobalFetchMock(mockFetchNetworkError());

  render(<StreamingAnswer query="test" mode="hybrid" />);

  await waitFor(() => {
    expect(screen.getByText(/Fehler beim Laden/i)).toBeInTheDocument();
  });
});
```

## Common Issues

### Tests Timing Out
**Solution**: Increase timeout in waitFor
```typescript
await waitFor(
  () => expect(screen.getByText(/text/i)).toBeInTheDocument(),
  { timeout: 5000 }
);
```

### Mocks Not Working
**Solution**: Ensure mocks are set up before rendering
```typescript
beforeEach(() => {
  setupGlobalFetchMock(mockFetchSSESuccess());
});
```

### Elements Not Found
**Solution**: Use screen.debug() to see rendered output
```typescript
screen.debug(); // Prints current DOM
```

## Next Steps

1. **Fix Failing Tests**: See `E2E_TEST_SUMMARY.md` for details
2. **Add More Tests**: Extend coverage for new features
3. **CI/CD Integration**: Add tests to build pipeline
4. **Visual Regression**: Consider adding screenshot tests

## Documentation

- **Detailed Guide**: See `src/test/e2e/README.md`
- **Test Summary**: See `E2E_TEST_SUMMARY.md`
- **Vitest Docs**: https://vitest.dev/
- **Testing Library**: https://testing-library.com/react

## Support

For questions or issues:
1. Check `src/test/e2e/README.md` for detailed documentation
2. Review test examples in existing test files
3. Check Vitest documentation for framework questions
