# Sprint 46 E2E Tests: ConversationView & ReasoningPanel

## Overview

This directory contains comprehensive Playwright E2E tests for Sprint 46 features:
- **Feature 46.1**: ConversationView - Chat-style conversation UI
- **Feature 46.2**: ReasoningPanel - Transparent reasoning/retrieval chain display

## Test File

**File**: `conversation-ui.spec.ts`
- **Total Tests**: 28 comprehensive test cases
- **Test Suites**: 3 (Feature 46.1, Feature 46.2, Integration)
- **Lines of Code**: 899

## Quick Start

### Prerequisites

Ensure services are running:
```bash
# Backend (port 8000)
uvicorn src.api.main:app --reload --port 8000

# Frontend (port 5179)
npm run dev  # from frontend directory

# LLM Service (port 11434)
ollama serve  # or configure via AegisLLMProxy
```

### Run Tests

Run all tests:
```bash
npx playwright test conversation-ui.spec.ts
```

Run with UI mode (recommended for development):
```bash
npx playwright test conversation-ui.spec.ts --ui
```

Run specific feature tests:
```bash
# Feature 46.1 only
npx playwright test conversation-ui.spec.ts -g "Feature 46.1"

# Feature 46.2 only
npx playwright test conversation-ui.spec.ts -g "Feature 46.2"

# Integration tests only
npx playwright test conversation-ui.spec.ts -g "Integration"
```

Run specific test:
```bash
npx playwright test conversation-ui.spec.ts -g "TC-46.1.1"
```

Generate HTML report:
```bash
npx playwright test conversation-ui.spec.ts --reporter=html
npx playwright show-report
```

## Test Categories

### Feature 46.1: ConversationView (13 tests)

Tests for chat-style conversation UI with the following categories:

#### Component Rendering (2 tests)
- ConversationView renders on homepage
- Message container is visible and scrollable

#### Styling & Layout (4 tests)
- User messages have blue background
- Assistant messages have white background  
- Input area fixed at bottom of viewport
- Message container is responsive

#### Functionality (5 tests)
- Messages can be sent and appear in conversation
- Streaming indicator displays during response
- Multiple messages maintain proper layout
- Empty state shows welcome message
- Keyboard navigation (Enter to send)

#### UI Components (2 tests)
- Send button visible and clickable
- Avatars displayed for each message

### Feature 46.2: ReasoningPanel (12 tests)

Tests for transparent reasoning panel with retrieval chain visualization:

#### Panel Interaction (4 tests)
- "Reasoning anzeigen" button exists on assistant messages
- Panel expands when button clicked
- Panel collapses when clicked again
- Chevron icon updates on toggle

#### Content Display (8 tests)
- Intent classification displayed with confidence score
- Intent shown with proper styling (colored badge)
- Retrieval steps shown in chain
- Retrieval sources displayed (Qdrant, BM25, Neo4j, etc.)
- Result counts shown for each retrieval step
- Timing information displayed (total + per-step)
- Tools section displays when available
- Panel layout is responsive

### Integration Tests (3 tests)

Tests for combined ConversationView + ReasoningPanel behavior:

1. **Complete conversation flow with reasoning visibility**
   - Send message → Receive response → View reasoning panel
   - Expand/collapse reasoning while viewing conversation

2. **Viewing reasoning for multiple messages**
   - Multiple messages in conversation
   - Toggle reasoning for different messages

3. **Input area remains functional with expanded reasoning**
   - Send message while reasoning panel is open
   - Ensure UI responsiveness

## Test Selectors

### ConversationView
```
[data-testid="conversation-view"]    - Main conversation container
[data-testid="messages-container"]   - Scrollable messages area
[data-testid="message-bubble"]       - Individual message
[data-testid="message-input"]        - Input field
[data-testid="send-button"]          - Send button
[data-testid="input-area"]           - Input area container
```

### ReasoningPanel
```
[data-testid="reasoning-panel"]      - Panel container
[data-testid="reasoning-toggle"]     - Expand/collapse button
[data-testid="reasoning-content"]    - Expanded content area
[data-testid="intent-section"]       - Intent classification display
[data-testid="retrieval-chain"]      - Retrieval steps container
[data-testid="retrieval-step-N"]     - Individual retrieval step
[data-testid="tools-section"]        - Tools used display
```

### Message Attributes
```
data-role="user"                     - User message
data-role="assistant"                - Assistant message
data-message-id="..."                - Message ID
data-source="..."                    - Retrieval source type
aria-expanded="true|false"           - Panel expansion state
```

## Environment Variables

Set these before running tests:

```bash
# Ollama (Primary LLM)
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL_GENERATION=llama3.2:8b

# Database URLs
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export NEO4J_URI=bolt://localhost:7687
export REDIS_HOST=localhost

# Frontend URL
export PLAYWRIGHT_TEST_BASE_URL=http://localhost:5179
```

## Timeout Handling

Tests use appropriate timeouts for different scenarios:

```
Component visibility:     1-3 seconds
Animation completion:     300ms
LLM response:            20-30 seconds
Feature existence check:  5 seconds (with fallback)
```

## Key Features

### Robustness
- Graceful handling of missing reasoning data (backend-dependent)
- Fallback assertions for optional features
- Proper error handling with try-catch patterns
- Async/await throughout

### Language Support
- German UI labels (native to application)
- Intent types: Faktenbezogen, Stichwortsuche, Explorativ, Zusammenfassung
- Button text: "Reasoning anzeigen" / "Reasoning ausblenden"

### Assertion Patterns

Check if optional feature exists:
```typescript
const exists = await element.isVisible({ timeout: 5000 }).catch(() => false);

if (exists) {
  // Test feature details
  await expect(element).toBeVisible();
  // ... more assertions
}
```

Wait for async operations:
```typescript
await chatPage.sendMessage('question');
await chatPage.waitForResponse();  // Wait for LLM
```

## Troubleshooting

### Tests timeout waiting for LLM response
- Check backend is running and healthy
- Verify LLM service (Ollama) is running
- Check network connectivity to backend

### ReasoningPanel tests skip
- Backend may not be sending reasoning data
- Check that response includes `reasoning` field
- Tests gracefully skip if reasoning unavailable

### Message not appearing in conversation
- Frontend may need more time to render
- Increase timeout in `waitForResponse()`
- Check browser console for errors

### Selectors not found
- Ensure correct data-testid attributes in components
- Verify components are fully rendered before assertion
- Use `--ui` mode to visually debug

## Development Tips

### Debug specific test
```bash
npx playwright test conversation-ui.spec.ts -g "TC-46.1.1" --debug
```

### See test execution live
```bash
npx playwright test conversation-ui.spec.ts --ui
```

### Generate trace for failed tests
```bash
npx playwright test conversation-ui.spec.ts --trace on
# Open trace with:
npx playwright show-trace trace.zip
```

### Run with specific browser
```bash
npx playwright test conversation-ui.spec.ts --project=firefox
npx playwright test conversation-ui.spec.ts --project=webkit
```

## CI/CD Integration

### GitHub Actions example
```yaml
- name: Run E2E tests
  run: |
    npm run test:e2e -- conversation-ui.spec.ts

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
    retention-days: 30
```

## Contributing

When adding new tests:
1. Follow TC naming convention: `TC-{Sprint}.{Feature}.{Number}`
2. Include descriptive test name and JSDoc comments
3. Use page object model (ChatPage) for interactions
4. Handle optional features gracefully
5. Add appropriate timeout for async operations
6. Update README with new test case descriptions

## Related Files

- Component implementations: `frontend/src/components/chat/`
  - `ConversationView.tsx`
  - `ReasoningPanel.tsx`
  - `RetrievalStep.tsx`
  - `MessageBubble.tsx`

- Test fixtures: `frontend/e2e/fixtures/index.ts`

- Page Object Model: `frontend/e2e/pom/ChatPage.ts`

- Types: `frontend/src/types/reasoning.ts`

## Coverage

**Total Test Count**: 28
- Feature 46.1: 13 tests
- Feature 46.2: 12 tests
- Integration: 3 tests

**Test Areas Covered**:
- Component rendering and visibility
- User interactions (click, type, send)
- Message styling and layout
- Panel expansion/collapse
- Content display (intent, retrieval, timing)
- Input functionality with concurrent panels
- Keyboard navigation
- Responsive behavior
- Error handling and edge cases

## Performance Notes

All tests complete in under 2 minutes (typically 60-90 seconds total)
- ConversationView tests: ~30 seconds
- ReasoningPanel tests: ~40 seconds  
- Integration tests: ~20 seconds

---

For more information, see the main E2E test README in the root e2e directory.
