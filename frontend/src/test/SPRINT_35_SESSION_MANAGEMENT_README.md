# Sprint 35 Feature 35.5 - Session Management Test Suite

Complete unit test coverage for the Session History Sidebar component and hooks.

## Quick Start

### Run All Tests
```bash
cd frontend
npm test -- src/components/chat/SessionSidebar.test.tsx src/hooks/__tests__/useSessions.test.ts --run
```

### Run Individual Test Suites
```bash
# SessionSidebar Component Tests
npm test -- src/components/chat/SessionSidebar.test.tsx --run

# useSessions Hook Tests
npm test -- src/hooks/__tests__/useSessions.test.ts --run
```

### Watch Mode (Development)
```bash
npm test -- src/components/chat/SessionSidebar.test.tsx
npm test -- src/hooks/__tests__/useSessions.test.ts
```

---

## Test Suite Overview

### SessionSidebar Component
**Location:** `/frontend/src/components/chat/SessionSidebar.test.tsx`
**Tests:** 43
**Status:** ✅ All Passing

Tests the visual display and user interaction logic of the session history sidebar.

#### Key Test Categories:
- **Rendering**: Component structure, buttons, groups
- **Session Grouping**: Today, Yesterday, Last 7 Days, Older
- **Active State**: Highlighting and selection
- **User Interactions**: Clicks, hover effects, mobile toggle
- **Delete Functionality**: Confirmation, API calls, state updates
- **Mobile Responsive**: Sidebar toggle, overlay
- **Loading States**: Loading messages, group visibility
- **Edge Cases**: Long titles, empty states

#### Example Tests:
```typescript
it('should call onSelectSession when session item clicked', () => {
  render(<SessionSidebar ... />);
  const sessionItems = screen.getAllByTestId('session-item');
  fireEvent.click(sessionItems[0]);
  expect(mockOnSelectSession).toHaveBeenCalledWith('session-1');
});

it('should show delete button on hover', async () => {
  render(<SessionSidebar ... />);
  const sessionItem = screen.getAllByTestId('session-item')[0];
  fireEvent.mouseEnter(sessionItem);
  await waitFor(() => {
    expect(screen.getByTestId('delete-session')).toBeInTheDocument();
  });
});
```

---

### useSessions Hook
**Location:** `/frontend/src/hooks/__tests__/useSessions.test.ts`
**Tests:** 48
**Status:** ✅ All Passing

Tests the session management logic including fetching, grouping, deletion, and refetching.

#### Key Test Categories:
- **Initialization**: Mount behavior, initial state
- **Data Fetching**: API calls, state updates
- **Error Handling**: API errors, error states, recovery
- **Date Grouping**: Accurate grouping by date (today, yesterday, lastWeek, older)
- **Session Removal**: Deletion, list updates, group updates
- **Refetching**: Manual refresh, state updates
- **Data Persistence**: State across re-renders
- **Edge Cases**: Same timestamps, very old dates, special characters

#### Example Tests:
```typescript
it('should fetch sessions on mount', async () => {
  renderHook(() => useSessions());
  await waitFor(() => {
    expect(chatApi.listSessions).toHaveBeenCalledTimes(1);
  });
});

it('should group sessions correctly by date', async () => {
  const { result } = renderHook(() => useSessions());
  await waitFor(() => {
    expect(result.current.groupedSessions.today.length).toBe(1);
    expect(result.current.groupedSessions.yesterday.length).toBe(1);
    expect(result.current.groupedSessions.lastWeek.length).toBe(1);
  });
});

it('should remove session from list after deletion', async () => {
  const { result } = renderHook(() => useSessions());
  await waitFor(() => {
    expect(result.current.sessions.length).toBe(4);
  });

  await act(async () => {
    await result.current.removeSession('session-1');
  });

  expect(result.current.sessions.length).toBe(3);
});
```

---

## File Structure

```
frontend/src/
├── components/chat/
│   ├── SessionSidebar.tsx                 # Component under test
│   └── SessionSidebar.test.tsx           # 43 tests
│
├── hooks/
│   ├── useSessions.ts                    # Hook under test
│   └── __tests__/
│       └── useSessions.test.ts           # 48 tests
│
├── api/
│   └── chat.ts                           # API client (mocked in tests)
│
└── test/
    ├── SPRINT_35_TESTS_SUMMARY.md       # Detailed summary
    └── SPRINT_35_SESSION_MANAGEMENT_README.md  # This file
```

---

## Mocking Strategy

### Component Tests (SessionSidebar)
```typescript
// Mock the useSessions hook
vi.mock('../../hooks/useSessions', () => ({
  useSessions: vi.fn(),
}));

// Set return value for hook
vi.mocked(useSessionsModule.useSessions).mockReturnValue({
  sessions: [],
  groupedSessions: mockSessionsData,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
  removeSession: vi.fn(),
});

// Mock window.confirm
global.confirm = vi.fn(() => true);
```

### Hook Tests (useSessions)
```typescript
// Mock API functions
vi.mock('../../api/chat', () => ({
  listSessions: vi.fn(),
  deleteSession: vi.fn(),
}));

// Set API responses
vi.mocked(chatApi.listSessions).mockResolvedValue({
  sessions: mockSessionInfoData,
  total_count: mockSessionInfoData.length,
});

// Test error scenarios
vi.mocked(chatApi.deleteSession).mockRejectedValue(
  new Error('Delete failed')
);
```

---

## Testing Best Practices Followed

### 1. Proper Hook Testing
```typescript
// Using renderHook for testing React hooks
const { result } = renderHook(() => useSessions());

// Using act() for state updates
await act(async () => {
  await result.current.removeSession('session-1');
});

// Using waitFor for async operations
await waitFor(() => {
  expect(result.current.isLoading).toBe(false);
});
```

### 2. Component User Interactions
```typescript
// Firing real user events
fireEvent.click(button);
fireEvent.mouseEnter(element);
fireEvent.mouseLeave(element);

// Waiting for rendered elements
await waitFor(() => {
  expect(screen.getByTestId('delete-session')).toBeInTheDocument();
});
```

### 3. Data-testid Attributes
All interactive elements have proper data-testid attributes:
- `session-sidebar` - Main container
- `sidebar-toggle` - Mobile menu button
- `new-chat-button` - New chat button
- `session-item` - Session in list
- `session-title` - Session title
- `delete-session` - Delete button

### 4. Comprehensive Assertions
```typescript
// Check multiple properties
expect(sidebar).toBeInTheDocument();
expect(sidebar.className).toContain('bg-gray-900');
expect(sidebar.className).toContain('text-white');

// Check call arguments
expect(mockRemoveSession).toHaveBeenCalledWith('session-1');
expect(global.confirm).toHaveBeenCalledWith('Delete this conversation?');
```

---

## Test Data

### SessionSidebar Test Data
```typescript
const mockSessionsData = {
  today: [
    {
      session_id: 'session-1',
      title: 'Today Conversation 1',
      preview: 'First message today',
      updated_at: new Date().toISOString(),
      message_count: 5,
    },
    // ... more sessions
  ],
  yesterday: [...],
  lastWeek: [...],
  older: [...],
};
```

### useSessions Test Data
```typescript
const mockSessionInfoData: SessionInfo[] = [
  {
    session_id: 'session-1',
    title: 'Today Conversation',
    last_message: 'Last message today',
    updated_at: new Date().toISOString(),
    message_count: 5,
  },
  // ... more sessions with different dates
];
```

---

## Coverage Metrics

| Test File | Tests | Pass Rate | Status |
|-----------|-------|-----------|--------|
| SessionSidebar.test.tsx | 43 | 100% | ✅ |
| useSessions.test.ts | 48 | 100% | ✅ |
| **Total** | **91** | **100%** | **✅** |

### Performance
- SessionSidebar tests: ~150ms
- useSessions tests: ~1955ms
- Combined runtime: ~2.1s

---

## Common Testing Patterns

### Testing User Interactions
```typescript
// Click and verify callback
fireEvent.click(screen.getByTestId('new-chat-button'));
expect(mockOnNewChat).toHaveBeenCalledTimes(1);
expect(mockOnToggle).toHaveBeenCalledTimes(1);

// Hover to show element
fireEvent.mouseEnter(sessionItem);
await waitFor(() => {
  expect(screen.getByTestId('delete-session')).toBeInTheDocument();
});
```

### Testing Date Grouping
```typescript
// Sessions are grouped correctly
expect(result.current.groupedSessions.today.length).toBe(1);
expect(result.current.groupedSessions.yesterday.length).toBe(1);
expect(result.current.groupedSessions.lastWeek.length).toBe(1);
expect(result.current.groupedSessions.older.length).toBe(1);

// Sessions in correct groups
expect(result.current.groupedSessions.today[0].session_id).toBe('session-1');
expect(result.current.groupedSessions.yesterday[0].session_id).toBe('session-2');
```

### Testing API Calls
```typescript
// Verify API called with correct arguments
expect(chatApi.deleteSession).toHaveBeenCalledWith('session-1');

// Test error handling
vi.mocked(chatApi.deleteSession).mockRejectedValue(new Error('API Error'));
const success = await result.current.removeSession('session-1');
expect(success).toBe(false);
```

### Testing State Updates
```typescript
// Test loading state
expect(result.current.isLoading).toBe(true);

// Wait for state update
await waitFor(() => {
  expect(result.current.isLoading).toBe(false);
});

// Verify state is updated
expect(result.current.sessions).toEqual(expectedSessions);
```

---

## Debugging Tips

### Run Single Test
```bash
npm test -- src/components/chat/SessionSidebar.test.tsx -t "should render sidebar with correct structure" --run
```

### View Test Output
```bash
npm test -- src/components/chat/SessionSidebar.test.tsx --reporter=verbose --run
```

### Debug in VS Code
Add breakpoint in test, then run:
```bash
node --inspect-brk ./node_modules/.bin/vitest run src/components/chat/SessionSidebar.test.tsx
```

### Check Rendered Output
```typescript
const { debug } = render(<SessionSidebar ... />);
debug(); // Prints HTML to console
```

---

## Related Files

### Source Files Tested
- `/frontend/src/components/chat/SessionSidebar.tsx` - Component implementation
- `/frontend/src/hooks/useSessions.ts` - Hook implementation
- `/frontend/src/api/chat.ts` - API client (mocked in tests)

### Type Definitions
- `/frontend/src/api/chat.ts` - SessionSummary type
- `/frontend/src/types/chat.ts` - SessionInfo, SessionListResponse types

### Related Components
- `ChatPage.tsx` - Parent component using SessionSidebar
- `useSessions.ts` - Hook providing session data

---

## Continuous Integration

### GitHub Actions Integration
The test suite is optimized for CI/CD:
- Fast execution (~2 seconds)
- No external dependencies
- Deterministic results
- Clear error messages

### Running in CI
```bash
npm test -- src/components/chat/SessionSidebar.test.tsx src/hooks/__tests__/useSessions.test.ts --run
```

---

## Troubleshooting

### Test Timeout
If tests timeout, check for:
- Unresolved promises in async code
- Missing `await waitFor()` calls
- Missing `act()` wrappers for state updates

### Mock Not Working
Check that:
- Mock is defined before test
- Using `vi.mocked()` wrapper for type safety
- Clearing mocks in `beforeEach()`

### Element Not Found
Ensure:
- data-testid attribute exists in component
- Element rendered with correct conditions
- Using correct query method (getBy, queryBy, findBy)

---

## Future Enhancements

### Potential Additions
1. **Visual Regression Tests** - Screenshot comparison
2. **Performance Tests** - Test with 1000+ sessions
3. **Accessibility Tests** - ARIA attributes, keyboard navigation
4. **Integration Tests** - SessionSidebar + Parent component
5. **Snapshot Tests** - Component output verification

---

## References

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

**Created:** 2025-12-04
**Last Modified:** 2025-12-04
**Test Framework:** Vitest 4.0.4
**React Testing Library:** Latest
