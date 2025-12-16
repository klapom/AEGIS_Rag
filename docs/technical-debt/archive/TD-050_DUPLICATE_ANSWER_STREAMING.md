# TD-050: Duplicate Answer Streaming Fix (Sprint 17)

**Status:** NEEDS VERIFICATION
**Priority:** HIGH
**Severity:** UX Bug
**Original Sprint:** Sprint 17 (Feature 17.5)
**Story Points:** 3 SP
**Created:** 2025-12-04

---

## Problem Statement

Users reported seeing duplicate answers in the streaming response - the same answer appearing twice in the UI. This creates confusion and degrades the user experience.

**Reported Symptoms:**
- Same answer content displayed twice
- May occur during SSE streaming
- Possibly related to state management or re-renders

---

## Current Status

**NEEDS VERIFICATION:** This issue was marked as HIGH PRIORITY in Sprint 17 planning, but it's unclear if it was subsequently fixed. Before implementing a fix, we need to:

1. Verify if the bug still exists
2. Reproduce the issue consistently
3. Identify root cause

---

## Potential Root Causes

### 1. React State Double-Update
```tsx
// Potential issue: Multiple state updates from same event
const handleStreamEvent = (event: MessageEvent) => {
    setMessages(prev => [...prev, event.data]);  // Called twice?
};
```

### 2. SSE Event Duplication
```python
# Backend might yield same content twice
async def stream_response():
    yield f"data: {chunk}\n\n"
    # Accidental duplicate yield?
```

### 3. React StrictMode Double-Render
```tsx
// StrictMode intentionally double-invokes certain functions
// Could cause duplicate state updates in development
```

### 4. Zustand Store Race Condition
```tsx
// Multiple components subscribing to same store
// Updates might trigger multiple re-renders
```

---

## Investigation Steps

### Step 1: Reproduce the Bug
```bash
# Run frontend in development mode
cd frontend && npm run dev

# Open browser DevTools -> Network tab
# Filter by EventStream
# Submit a query and observe SSE events
```

### Step 2: Check SSE Events
- Are duplicate events being sent from backend?
- Are events being processed multiple times in frontend?

### Step 3: Check React State
- Add console.log to message state updates
- Check if same message ID appears twice
- Verify useEffect dependencies

---

## Potential Fixes

### Fix A: Deduplicate Messages by ID
```tsx
// frontend/src/hooks/useStreamChat.ts

const handleStreamEvent = (event: MessageEvent) => {
    const message = JSON.parse(event.data);
    setMessages(prev => {
        // Prevent duplicate messages
        if (prev.some(m => m.id === message.id)) {
            return prev;
        }
        return [...prev, message];
    });
};
```

### Fix B: Use useRef to Track Processed Events
```tsx
const processedEvents = useRef<Set<string>>(new Set());

const handleStreamEvent = (event: MessageEvent) => {
    const eventId = event.lastEventId || generateId();
    if (processedEvents.current.has(eventId)) {
        return; // Skip duplicate
    }
    processedEvents.current.add(eventId);
    // Process event...
};
```

### Fix C: Backend Event ID Tracking
```python
# src/api/v1/chat.py

async def stream_response():
    event_id = 0
    for chunk in response_stream:
        event_id += 1
        yield f"id: {event_id}\ndata: {chunk}\n\n"
```

---

## Acceptance Criteria

- [ ] Bug reproduction confirmed (or confirmed fixed)
- [ ] Root cause identified
- [ ] Fix implemented if needed
- [ ] No duplicate messages in streaming responses
- [ ] E2E test added to prevent regression
- [ ] Works in both development and production modes

---

## Affected Files (Potential)

```
frontend/src/hooks/useStreamChat.ts       # SSE handling
frontend/src/components/chat/StreamingAnswer.tsx
frontend/src/stores/chatStore.ts          # Zustand state
src/api/v1/chat.py                        # Backend SSE endpoint
```

---

## Verification Test

```typescript
// frontend/tests/e2e/no-duplicate-streaming.spec.ts

test('streaming response should not show duplicates', async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="message-input"]', 'Test query');
    await page.click('[data-testid="send-button"]');

    // Wait for streaming to complete
    await page.waitForSelector('[data-testid="streaming-complete"]');

    // Get all message elements
    const messages = await page.$$('[data-testid="assistant-message"]');

    // Check for duplicates
    const contents = await Promise.all(
        messages.map(m => m.textContent())
    );

    const uniqueContents = new Set(contents);
    expect(uniqueContents.size).toBe(contents.length);
});
```

---

## Estimated Effort

**Story Points:** 3 SP (if bug exists)
- Investigation: 1 SP
- Fix implementation: 1 SP
- Testing: 1 SP

---

## References

- [SPRINT_PLAN.md - Sprint 17 Feature 17.5](../sprints/SPRINT_PLAN.md#sprint-17)

---

## Target Sprint

**Recommended:** Sprint 35 or 36 (verify first, then fix if needed)

---

## Action Items

1. **Immediate:** Verify if bug still exists
2. **If confirmed:** Implement fix in Sprint 35/36
3. **If resolved:** Close this TD and document when/how it was fixed

---

**Last Updated:** 2025-12-04
