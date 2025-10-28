# AEGIS RAG Frontend E2E Test Suite

**Sprint 15 - React Application Testing**

This directory contains comprehensive End-to-End (E2E) tests for the AEGIS RAG Frontend application.

## Overview

The E2E test suite covers real user workflows and integration scenarios, ensuring that the frontend application works correctly from a user's perspective. Tests are written using Vitest and React Testing Library.

### Test Coverage

- **HomePage Tests**: Landing page interactions, search input, mode selection, quick prompts
- **SearchResultsPage Tests**: Results page rendering, navigation, URL handling
- **SSE Streaming Tests**: Server-Sent Events streaming, token display, source cards
- **Error Handling Tests**: Network errors, HTTP errors, streaming errors, recovery
- **Full Workflow Tests**: Complete user journeys from landing to results

## Test Files

### Core Test Files

1. **`HomePage.e2e.test.tsx`** (17 test scenarios)
   - Initial page render
   - Search input interaction
   - Mode selection (Hybrid, Vector, Graph, Memory)
   - Quick prompt navigation
   - Form submission
   - Keyboard shortcuts

2. **`SearchResultsPage.e2e.test.tsx`** (16 test scenarios)
   - Page rendering with URL params
   - Empty query handling
   - New search submission
   - URL encoding
   - Layout and accessibility

3. **`SSEStreaming.e2e.test.tsx`** (30+ test scenarios)
   - Token-by-token streaming
   - Source card display
   - Metadata handling
   - Stream completion
   - Error handling during streaming
   - Chunk parsing

4. **`ErrorHandling.e2e.test.tsx`** (25+ test scenarios)
   - Network errors
   - HTTP errors (400, 401, 403, 404, 429, 500, 502, 503)
   - Streaming errors
   - Invalid data handling
   - Error recovery
   - Error UI display

5. **`FullWorkflow.e2e.test.tsx`** (20+ test scenarios)
   - Complete user workflows
   - Multi-step interactions
   - Mode switching workflows
   - Follow-up queries
   - Complex user journeys
   - Edge cases

### Utilities

- **`fixtures.ts`**: Test data and mock responses
  - Mock SSE stream data
  - Mock sources and sessions
  - Mock API responses
  - Sample queries (valid, empty, long, special)

- **`helpers.ts`**: Test utility functions
  - Mock stream creation
  - Fetch mocking utilities
  - Navigation mocks
  - Event simulation helpers

## Running the Tests

### Run All E2E Tests

```bash
npm test
```

### Run Specific Test File

```bash
npm test HomePage.e2e.test
npm test SearchResultsPage.e2e.test
npm test SSEStreaming.e2e.test
npm test ErrorHandling.e2e.test
npm test FullWorkflow.e2e.test
```

### Run Tests in Watch Mode

```bash
npm run test:watch
```

### Run Tests with UI

```bash
npm run test:ui
```

### Generate Coverage Report

```bash
npm run test:coverage
```

## Test Structure

### Typical Test Pattern

```typescript
describe('Component/Feature E2E Tests', () => {
  beforeEach(() => {
    // Setup mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Cleanup
    cleanupGlobalFetchMock();
  });

  describe('Specific Feature', () => {
    it('should perform expected behavior', async () => {
      // Arrange: Setup mocks and render component
      setupGlobalFetchMock(mockFetchSSESuccess());

      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Act: Perform user actions
      const input = screen.getByPlaceholderText(/search/i);
      fireEvent.change(input, { target: { value: 'test query' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      // Assert: Verify expected outcome
      await waitFor(() => {
        expect(screen.getByText(/test query/i)).toBeInTheDocument();
      });
    });
  });
});
```

## Key Testing Concepts

### 1. Component Rendering

Tests verify that components render correctly with various props and states:

```typescript
render(
  <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
    <SearchResultsPage />
  </MemoryRouter>
);
```

### 2. User Interactions

Tests simulate real user interactions:

```typescript
fireEvent.change(input, { target: { value: 'test' } });
fireEvent.click(button);
fireEvent.keyDown(input, { key: 'Enter' });
```

### 3. Asynchronous Testing

Tests handle async operations with `waitFor`:

```typescript
await waitFor(
  () => {
    expect(screen.getByText(/result/i)).toBeInTheDocument();
  },
  { timeout: 3000 }
);
```

### 4. Mock SSE Streaming

Tests mock Server-Sent Events streaming:

```typescript
setupGlobalFetchMock(
  vi.fn().mockResolvedValue({
    ok: true,
    body: createMockSSEStream(chunks),
  })
);
```

## Test Categories

### Functional Tests
- User can submit queries
- Results display correctly
- Mode selection works
- Navigation flows properly

### Integration Tests
- Components work together
- API integration functions
- Routing works correctly
- State management works

### Error Handling Tests
- Network failures handled
- HTTP errors displayed
- Streaming errors recovered
- User can retry

### Edge Case Tests
- Empty queries
- Long queries
- Special characters
- Rapid changes
- Invalid data

## Best Practices

### 1. Use Realistic Mocks

Mock data should closely resemble real API responses:

```typescript
const mockChunks: ChatChunk[] = [
  { type: 'metadata', session_id: '123', data: { intent: 'hybrid' } },
  { type: 'token', content: 'Hello' },
  { type: 'source', source: { text: 'Source text', title: 'Title' } },
  { type: 'complete', data: { latency_seconds: 1.5 } },
];
```

### 2. Test User Flows, Not Implementation

Focus on what users see and do:

```typescript
// Good: Test user behavior
it('should display results when user submits query', async () => {
  const input = screen.getByPlaceholderText(/search/i);
  fireEvent.change(input, { target: { value: 'test' } });
  fireEvent.keyDown(input, { key: 'Enter' });

  await waitFor(() => {
    expect(screen.getByText(/result/i)).toBeInTheDocument();
  });
});

// Bad: Test implementation details
it('should call setState with correct value', () => {
  // Don't test internal state directly
});
```

### 3. Clean Up After Tests

Always clean up mocks and state:

```typescript
afterEach(() => {
  vi.clearAllMocks();
  cleanupGlobalFetchMock();
});
```

### 4. Use Descriptive Test Names

Test names should clearly describe what is being tested:

```typescript
// Good
it('should display error message when network request fails', async () => {});

// Bad
it('should work', async () => {});
```

### 5. Group Related Tests

Use `describe` blocks to organize tests:

```typescript
describe('Error Handling', () => {
  describe('Network Errors', () => {
    it('should handle connection failure', () => {});
    it('should handle timeout', () => {});
  });

  describe('HTTP Errors', () => {
    it('should handle 404', () => {});
    it('should handle 500', () => {});
  });
});
```

## Common Patterns

### Testing Navigation

```typescript
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => ({
  ...await vi.importActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// In test
await waitFor(() => {
  expect(mockNavigate).toHaveBeenCalledWith('/search?q=test');
});
```

### Testing SSE Streaming

```typescript
const chunks: ChatChunk[] = [
  { type: 'metadata', session_id: '123' },
  { type: 'token', content: 'Hello' },
  { type: 'complete', data: {} },
];

setupGlobalFetchMock(
  vi.fn().mockResolvedValue({
    ok: true,
    body: createMockSSEStream(chunks),
  })
);
```

### Testing Error States

```typescript
setupGlobalFetchMock(
  mockFetchHTTPError(500, 'Internal Server Error')
);

await waitFor(() => {
  expect(screen.getByText(/Fehler/i)).toBeInTheDocument();
});
```

## Troubleshooting

### Tests Timing Out

If tests timeout, increase the timeout or check for missing mocks:

```typescript
await waitFor(
  () => {
    expect(screen.getByText(/result/i)).toBeInTheDocument();
  },
  { timeout: 5000 } // Increase timeout
);
```

### Mocks Not Working

Ensure mocks are set up before rendering:

```typescript
beforeEach(() => {
  setupGlobalFetchMock(mockFetchSSESuccess());
});

// Then render component
render(<Component />);
```

### Elements Not Found

Use `screen.debug()` to see what's rendered:

```typescript
screen.debug(); // Prints current DOM
```

Or check if element appears asynchronously:

```typescript
await waitFor(() => {
  expect(screen.getByText(/text/i)).toBeInTheDocument();
});
```

## Coverage Goals

- **Statements**: > 80%
- **Branches**: > 75%
- **Functions**: > 80%
- **Lines**: > 80%

Current coverage focuses on:
- User-facing workflows
- Error handling
- API integration
- Navigation flows

## Contributing

When adding new tests:

1. Follow existing patterns and structure
2. Add tests to appropriate file or create new file
3. Update this README if adding new test categories
4. Ensure tests are independent and can run in any order
5. Use descriptive test names and comments
6. Mock external dependencies appropriately

## References

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- Sprint 15 ADR-020: SSE Streaming Implementation
- Sprint 15 ADR-021: Search Input Component Design
