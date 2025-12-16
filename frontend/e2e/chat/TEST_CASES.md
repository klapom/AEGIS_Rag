# Sprint 46 Test Cases Reference

## Quick Index

### Feature 46.1: ConversationView (13 tests)
- [TC-46.1.1 to TC-46.1.13](#feature-461-conversationview)

### Feature 46.2: ReasoningPanel (12 tests)
- [TC-46.2.1 to TC-46.2.12](#feature-462-reasoningpanel)

### Integration Tests (3 tests)
- [Integration-1 to Integration-3](#integration-tests)

---

## Feature 46.1: ConversationView

### TC-46.1.1: Render ConversationView on homepage
**Objective**: Verify ConversationView component renders properly on the main page
**Steps**:
1. Navigate to homepage (/)
2. Look for [data-testid="conversation-view"]
3. Verify proper CSS classes (flex, flex-col, h-full)

**Expected**: ConversationView container visible with proper flex layout

---

### TC-46.1.2: Message container visibility
**Objective**: Verify the scrollable messages container is visible and properly configured
**Steps**:
1. Load chat page
2. Locate [data-testid="messages-container"]
3. Check for overflow-y-auto and flex-1 classes

**Expected**: Messages container visible, scrollable, grows to fill space

---

### TC-46.1.3: User message styling
**Objective**: Verify user messages have blue background and correct label
**Steps**:
1. Send a message "What is the capital of France?"
2. Find [data-testid="message-bubble"][data-role="user"]
3. Check for blue-50 background class
4. Verify "Sie" label present

**Expected**: User message styled with blue background, labeled "Sie"

---

### TC-46.1.4: Assistant message styling
**Objective**: Verify assistant messages have white background and AegisRAG label
**Steps**:
1. Send a message and wait for response
2. Find [data-testid="message-bubble"][data-role="assistant"]
3. Check for white background
4. Verify "AegisRAG" label present

**Expected**: Assistant message styled with white background, labeled "AegisRAG"

---

### TC-46.1.5: Input area fixed at bottom
**Objective**: Verify input area stays fixed at bottom of viewport
**Steps**:
1. Load chat page
2. Find [data-testid="input-area"]
3. Verify flex-shrink-0 class
4. Send multiple messages to trigger scrolling
5. Verify input area still visible

**Expected**: Input area remains fixed and visible regardless of message scroll

---

### TC-46.1.6: Send button visible and clickable
**Objective**: Verify send button is properly rendered and functional
**Steps**:
1. Load chat page
2. Find [data-testid="send-button"]
3. Type a message in input
4. Verify button is enabled
5. Verify button is clickable

**Expected**: Send button visible and enabled when input has content

---

### TC-46.1.7: Message sending and display
**Objective**: Complete flow of sending message and displaying in conversation
**Steps**:
1. Send message "What is artificial intelligence?"
2. Wait for response
3. Verify message appears in conversation
4. Verify input is cleared
5. Verify response appears below user message

**Expected**: Message sent, displayed, input cleared, response visible

---

### TC-46.1.8: Streaming indicator during response
**Objective**: Verify streaming indicator appears during LLM response
**Steps**:
1. Send message "Explain quantum computing"
2. Check for streaming indicator
3. Wait for response complete
4. Verify response content present

**Expected**: Streaming visual feedback, then final response

---

### TC-46.1.9: Multiple messages maintain proper layout
**Objective**: Verify conversation layout works correctly with multiple messages
**Steps**:
1. Send message 1: "What is Python?"
2. Wait for response
3. Send message 2: "What is Java?"
4. Wait for response
5. Verify all 4+ messages visible
6. Verify proper alternation (user, assistant, user, assistant)

**Expected**: Multiple messages properly arranged vertically

---

### TC-46.1.10: Empty state display
**Objective**: Verify welcome message displays when conversation is empty
**Steps**:
1. Load chat page with no messages
2. Verify empty state content displayed
3. Verify input is ready for first message

**Expected**: Welcome message shown, input focused and ready

---

### TC-46.1.11: Keyboard navigation (Enter key)
**Objective**: Verify messages can be sent using Enter key
**Steps**:
1. Load chat page
2. Type in input: "What is blockchain?"
3. Press Enter key
4. Wait for response
5. Verify message appears

**Expected**: Enter key successfully sends message

---

### TC-46.1.12: Avatar display on messages
**Objective**: Verify avatars are shown for all messages
**Steps**:
1. Send a message
2. Wait for response
3. Count user and assistant messages
4. Verify both have avatars visible

**Expected**: All messages display appropriate avatars

---

### TC-46.1.13: Responsive message container
**Objective**: Verify message container is responsive and properly sized
**Steps**:
1. Load chat page
2. Get bounding box of [data-testid="messages-container"]
3. Verify width > 0 and height > 0
4. Verify container is visible

**Expected**: Messages container has proper dimensions and is responsive

---

## Feature 46.2: ReasoningPanel

### TC-46.2.1: Reasoning toggle button display
**Objective**: Verify "Reasoning anzeigen/ausblenden" button exists on assistant messages
**Steps**:
1. Send message "What is machine learning?"
2. Wait for response
3. Look for [data-testid="reasoning-toggle"]
4. Check button text contains "Reasoning"

**Expected**: Reasoning toggle button visible (if backend supports reasoning)

---

### TC-46.2.2: Panel expansion when clicked
**Objective**: Verify panel expands when toggle button is clicked
**Steps**:
1. Find [data-testid="reasoning-toggle"]
2. Click toggle button
3. Wait 300ms for animation
4. Check [data-testid="reasoning-content"] is visible
5. Verify aria-expanded="true"

**Expected**: Panel expands and content becomes visible

---

### TC-46.2.3: Panel collapse when clicked again
**Objective**: Verify panel collapses when toggle button clicked again
**Steps**:
1. Expand reasoning panel (see TC-46.2.2)
2. Click toggle button again
3. Wait 300ms for animation
4. Verify aria-expanded="false"
5. Verify content no longer visible

**Expected**: Panel collapses and content hidden

---

### TC-46.2.4: Intent classification display
**Objective**: Verify intent classification is displayed with confidence score
**Steps**:
1. Send message "Tell me about transformers in AI"
2. Expand reasoning panel
3. Find [data-testid="intent-section"]
4. Verify intent type displayed (Faktenbezogen, Stichwortsuche, etc.)
5. Verify confidence percentage (e.g., "85%")

**Expected**: Intent classification with confidence percentage shown

---

### TC-46.2.5: Retrieval chain steps display
**Objective**: Verify retrieval steps are shown in the panel
**Steps**:
1. Send message "What is vector search?"
2. Expand reasoning panel
3. Find [data-testid="retrieval-chain"]
4. Count [data-testid="retrieval-step-*"] elements
5. Verify step count > 0

**Expected**: Retrieval steps displayed with information

---

### TC-46.2.6: Timing information display
**Objective**: Verify timing is displayed for total and per-step
**Steps**:
1. Send message "What is embedding?"
2. Check [data-testid="reasoning-toggle"] for duration text (e.g., "145ms")
3. Expand reasoning panel
4. Check retrieval steps for individual timings
5. Verify timing format (ms or s)

**Expected**: Timing information displayed in human-readable format

---

### TC-46.2.7: Retrieval sources identification
**Objective**: Verify retrieval sources are correctly identified and displayed
**Steps**:
1. Send message "What is hybrid search?"
2. Expand reasoning panel
3. Collect all [data-testid="retrieval-step-*"] elements
4. Extract data-source attribute from each
5. Verify sources are valid (qdrant, bm25, neo4j, redis, rrf_fusion, reranker)

**Expected**: Valid retrieval sources identified and displayed

---

### TC-46.2.8: Intent styling with color badges
**Objective**: Verify intent classification has proper color styling
**Steps**:
1. Send message "Summarize machine learning concepts"
2. Expand reasoning panel
3. Find intent badge in [data-testid="intent-section"]
4. Check for background color classes (bg-blue-100, bg-amber-100, etc.)
5. Check for text color classes

**Expected**: Intent badge displays with appropriate Tailwind colors

---

### TC-46.2.9: Result counts per retrieval step
**Objective**: Verify result counts are shown for each retrieval step
**Steps**:
1. Send message "Tell me about embeddings"
2. Expand reasoning panel
3. Find first [data-testid="retrieval-step-*"]
4. Look for "Ergebnisse:" or "Zusammengefuehrt:" text
5. Verify numeric count present

**Expected**: Result counts displayed for retrieval steps

---

### TC-46.2.10: Responsive panel layout
**Objective**: Verify panel has responsive layout
**Steps**:
1. Send message "Explain neural networks"
2. Find [data-testid="reasoning-panel"]
3. Get bounding box dimensions
4. Verify width > 0 and height > 0
5. Check for proper CSS classes (border, rounded-lg)

**Expected**: Panel has proper dimensions and responsive layout

---

### TC-46.2.11: Chevron icon state change
**Objective**: Verify chevron icon changes direction on toggle
**Steps**:
1. Find [data-testid="reasoning-toggle"]
2. Check initial aria-expanded state
3. Click toggle to expand
4. Verify aria-expanded="true"
5. Click toggle to collapse
6. Verify aria-expanded="false"

**Expected**: Chevron icon state reflects expansion state

---

### TC-46.2.12: Tools section display
**Objective**: Verify tools section displays when tools are used
**Steps**:
1. Send message "What are large language models?"
2. Expand reasoning panel
3. Look for [data-testid="tools-section"]
4. If present, verify "Verwendete Tools" label
5. Verify tool badges displayed

**Expected**: Tools section shown if tools were used in retrieval

---

## Integration Tests

### Integration-1: Complete conversation flow with reasoning visibility
**Objective**: Test complete user journey with reasoning panel
**Steps**:
1. Verify ConversationView renders
2. Send message "Explain the concept of overfitting"
3. Wait for response
4. Verify message in conversation
5. Find reasoning toggle
6. Expand reasoning panel
7. Verify intent section visible
8. Collapse reasoning
9. Verify collapsed state

**Expected**: Full flow works seamlessly

---

### Integration-2: Viewing reasoning for multiple messages
**Objective**: Test reasoning panel works across multiple messages
**Steps**:
1. Send message 1: "What is neural networks?"
2. Wait for response
3. Send message 2: "How does backpropagation work?"
4. Wait for response
5. Expand reasoning for message 1
6. Collapse reasoning for message 1
7. Expand reasoning for message 2
8. Verify independent behavior

**Expected**: Reasoning toggles work independently per message

---

### Integration-3: Input functionality while reasoning panel expanded
**Objective**: Verify input works while reasoning panel is open
**Steps**:
1. Send message "Tell me about transformers"
2. Wait for response
3. Expand reasoning panel
4. Verify input is visible
5. Send new message with panel open
6. Wait for response
7. Verify new message appears

**Expected**: Input remains fully functional with panel open

---

## Test Execution Quick Reference

### Run all tests
```bash
npx playwright test conversation-ui.spec.ts
```

### Run specific test
```bash
npx playwright test conversation-ui.spec.ts -g "TC-46.1.1"
npx playwright test conversation-ui.spec.ts -g "TC-46.2.4"
```

### Run feature only
```bash
npx playwright test conversation-ui.spec.ts -g "Feature 46.1"
npx playwright test conversation-ui.spec.ts -g "Feature 46.2"
```

### Run with debug
```bash
npx playwright test conversation-ui.spec.ts -g "TC-46.1.1" --debug
```

### View results
```bash
npx playwright test conversation-ui.spec.ts --reporter=html
npx playwright show-report
```

---

## Selector Reference

| Test ID | Element |
|---------|---------|
| conversation-view | Main conversation container |
| messages-container | Scrollable messages area |
| message-bubble | Individual message |
| message-input | Input text field |
| send-button | Send button |
| input-area | Input area container |
| reasoning-panel | Reasoning panel container |
| reasoning-toggle | Expand/collapse button |
| reasoning-content | Expanded reasoning content |
| intent-section | Intent classification section |
| retrieval-chain | Retrieval steps container |
| retrieval-step-* | Individual retrieval step |
| tools-section | Tools used display |

---

## Notes

- All tests use German UI labels where appropriate
- ReasoningPanel tests gracefully handle missing reasoning data
- Tests use proper timeout handling for async operations
- All tests follow Page Object Model pattern
- Tests are isolated and can run in any order

