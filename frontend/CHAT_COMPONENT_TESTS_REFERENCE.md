# Chat Component Unit Tests - Quick Reference

**Sprint 35 Feature 35.1** | **Status: COMPLETE - All 77 Tests Passing**

## Test Files Location

```
frontend/src/components/chat/
├── UserAvatar.test.tsx      (13 tests)
├── BotAvatar.test.tsx       (16 tests)
└── ChatMessage.test.tsx     (48 tests)
```

## Quick Test Commands

```bash
# Run all three chat component tests
npm test -- --run UserAvatar.test.tsx BotAvatar.test.tsx ChatMessage.test.tsx

# Run individual test file
npm test -- --run UserAvatar.test.tsx
npm test -- --run BotAvatar.test.tsx
npm test -- --run ChatMessage.test.tsx

# Watch mode for development
npm test UserAvatar.test.tsx BotAvatar.test.tsx ChatMessage.test.tsx

# With coverage report
npm test -- --coverage UserAvatar.test.tsx BotAvatar.test.tsx ChatMessage.test.tsx
```

## Test Coverage Overview

| Component | Tests | Status | Lines | Branches |
|-----------|-------|--------|-------|----------|
| UserAvatar.tsx | 13 | ✓ PASS | 100% | 100% |
| BotAvatar.tsx | 16 | ✓ PASS | 100% | 100% |
| ChatMessage.tsx | 48 | ✓ PASS | 100% | 100% |
| **TOTAL** | **77** | **✓ PASS** | **100%** | **100%** |

## UserAvatar Tests (13)

Simple blue avatar component for user messages.

### Core Tests
- Renders with correct data-testid
- Has accessibility label (aria-label)
- Applies blue background (bg-blue-500)
- Has correct size (w-8 h-8)
- Applies rounded-full
- Centers content (flex, items-center, justify-center)

### Advanced Tests
- Prevents flex shrinking (flex-shrink-0)
- Renders User icon from lucide-react
- Icon has white color
- Maintains fixed size
- Renders without props
- Stable across rerenders
- Integrates with ChatMessage layout

## BotAvatar Tests (16)

Gradient avatar component for assistant messages.

### Core Tests
- Renders with correct data-testid
- Has accessibility label (aria-label: "AegisRAG assistant avatar")
- Applies gradient styling (bg-gradient-to-br from-teal-400 to-blue-500)
- Has correct size (w-8 h-8)
- Applies rounded-full
- Centers content (flex, items-center, justify-center)

### Advanced Tests
- Prevents flex shrinking (flex-shrink-0)
- Renders Bot icon from lucide-react
- Icon has white color
- Distinguishes from UserAvatar with gradient
- Maintains fixed size
- Renders without props
- Stable across rerenders
- Integrates with ChatMessage layout
- Consistent icon styling with UserAvatar

## ChatMessage Tests (48)

Complete message container component. Organized into 11 test groups.

### Basic Rendering (3 tests)
```tsx
- Renders chat message container
- Sets data-role="user" for user messages
- Sets data-role="assistant" for assistant messages
```

### User Messages (7 tests)
```tsx
- Correct styling (flex gap-4 py-6 border-b)
- Displays message content
- Shows "Sie" label
- Renders UserAvatar
- No BotAvatar
- Plain text (no markdown)
- Preserves whitespace (whitespace-pre-wrap)
```

### Assistant Messages (6 tests)
```tsx
- Correct styling
- Displays message content
- Shows "AegisRAG" label
- Renders BotAvatar
- No UserAvatar
- Markdown support (renders <strong>, <em>)
```

### Citations (5 tests)
```tsx
- Uses MarkdownWithCitations when citations present
- No error without onCitationClick handler
- Passes citations to MarkdownWithCitations
- Falls back to plain markdown if no citations
- Falls back if citations array empty
```

### Animation Classes (2 tests)
```tsx
- Applies animate-fade-in class
- Animation on both user and assistant
```

### Timestamps (4 tests)
```tsx
- Displays timestamp when provided
- No timestamp when not provided
- German locale formatting (de-DE)
- Correct styling (text-xs text-gray-400 mt-2)
```

### Layout Structure (5 tests)
```tsx
- Proper flex layout (gap-4, flex-shrink-0)
- Border styling (border-b border-gray-100)
- Padding (py-6)
- Prose styling (prose prose-sm)
- Overflow prevention (min-w-0)
```

### Long Messages (4 tests)
```tsx
- Handles 200+ character user messages
- Handles 200+ character assistant messages
- Handles multiline messages
- Handles code blocks in markdown
```

### Message Role Variations (3 tests)
```tsx
- Identifies user role correctly
- Identifies assistant role correctly
- Applies correct label based on role
```

### Integration (4 tests)
```tsx
- Complete user message with all elements
- Complete assistant message with all elements
- Handles multiple messages in sequence
- Consistent styling across types
```

### Edge Cases (5 tests)
```tsx
- Empty message content
- Undefined citations
- Special characters (<>&"')
- HTML-like content (safely escaped)
- Very long URLs
```

## Key Test Patterns

### Data-TestID Pattern
```tsx
const avatar = screen.getByTestId('user-avatar');
expect(avatar).toBeInTheDocument();
```

### Accessibility Testing
```tsx
expect(element).toHaveAttribute('aria-label', 'expected label');
```

### Styling Assertions
```tsx
expect(element).toHaveClass('bg-blue-500');
expect(element).toHaveClass('w-8', 'h-8');
```

### DOM Structure
```tsx
const { container } = render(<Component />);
const strong = container.querySelector('strong');
expect(strong?.textContent).toBe('text');
```

### Conditional Rendering
```tsx
expect(screen.getByTestId('user-avatar')).toBeInTheDocument();
expect(screen.queryByTestId('bot-avatar')).not.toBeInTheDocument();
```

## Mock Data

### UserAvatar & BotAvatar
No props required - stateless components with defaults.

### ChatMessage
```tsx
// User message
const userMessage = {
  role: 'user',
  content: 'What is AegisRAG?',
  timestamp?: '2025-12-04T14:30:00Z',
};

// Assistant message with citations
const assistantMessage = {
  role: 'assistant',
  content: 'AegisRAG is powerful[1].',
  citations: [
    {
      text: 'AegisRAG documentation',
      title: 'Overview',
      source: 'docs.pdf',
      score: 0.95,
    },
  ],
  onCitationClick?: (sourceId: string) => void,
};
```

## Common Assertions

### Presence Assertions
```tsx
expect(element).toBeInTheDocument();
expect(screen.getByTestId('id')).toBeInTheDocument();
expect(screen.queryByTestId('id')).not.toBeInTheDocument();
```

### Content Assertions
```tsx
expect(screen.getByText('text')).toBeInTheDocument();
expect(element.textContent).toBe('exact text');
expect(element.className).toContain('class');
```

### Attribute Assertions
```tsx
expect(element).toHaveAttribute('aria-label', 'text');
expect(element).toHaveClass('class-name');
expect(element).toHaveClass('class1', 'class2');
```

### Style Assertions
```tsx
expect(element).toHaveStyle({ color: 'white' });
```

## Test Execution

### All Tests
```
Test Files: 3 passed
Tests: 77 passed
Duration: ~1.7s
```

### By Component
```
UserAvatar.test.tsx:  13 tests, 54ms
BotAvatar.test.tsx:   16 tests, 61ms
ChatMessage.test.tsx: 48 tests, 89ms
```

## CI/CD Integration

Tests are ready for CI/CD pipeline:
- Run with: `npm test -- --run [files]`
- No external services required
- No special configuration needed
- All dependencies installed with `npm install`

## Notes

- Tests use Vitest (not Jest)
- Tests use React Testing Library (best practices)
- 100% code coverage for tested components
- All tests isolated and independent
- No shared state between tests
- Tests can run in any order
- No external mocks needed (pure components)

## Related Files

**Source Components:**
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/chat/UserAvatar.tsx`
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/chat/BotAvatar.tsx`
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/chat/ChatMessage.tsx`

**Type Definitions:**
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/types/chat.ts`

**Documentation:**
- `/home/admin/projects/aegisrag/AEGIS_Rag/SPRINT_35_CHAT_TESTS_SUMMARY.md`

**Related Components:**
- `MarkdownWithCitations.tsx` - Renders citations in assistant messages
- `Citation.tsx` - Individual citation component
- `SkeletonMessage.tsx` - Loading state (has tests)
- `TypingIndicator.tsx` - Typing animation (has tests)
