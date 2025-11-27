# Follow-up Questions Feature Fix - Sprint 33

## Problem Statement
All 9 Follow-up Questions E2E tests fail because `[data-testid="followup-question"]` never appears in the frontend.

## Root Cause Analysis

### Frontend Implementation ✅ CORRECT
The frontend is correctly implemented:

1. **FollowUpQuestions Component** (`frontend/src/components/chat/FollowUpQuestions.tsx`):
   - Line 108: Correctly renders buttons with `data-testid="followup-question"`
   - Properly fetches questions from `/api/v1/chat/sessions/{sessionId}/followup-questions`
   - Handles loading/error states correctly

2. **StreamingAnswer Component** (`frontend/src/components/chat/StreamingAnswer.tsx`):
   - Lines 284-297: Conditionally renders FollowUpQuestions when `!isStreaming && currentSessionId`
   - Passes sessionId and click handler correctly

3. **API Client** (`frontend/src/api/chat.ts`):
   - Lines 249-264: `getFollowUpQuestions()` correctly calls backend endpoint

### Backend Issue ❌ BROKEN
The backend conversation storage is failing:

1. **Symptoms**:
   - Non-streaming endpoint: Session created but conversation not saved to Redis
   - Streaming endpoint: Session created but conversation not saved to Redis
   - Follow-up endpoint returns 404: "Session not found"

2. **Code Modified** (`src/api/v1/chat.py`):
   - Lines 100-126: Added `sources` serialization to `save_conversation_turn()`
   - Lines 373-386: Added logging to track save success/failure
   - Lines 70-79: Added debug logging for save start

3. **Expected Behavior**:
   - After chat response, `save_conversation_turn()` should store conversation to Redis
   - Redis key: `{session_id}` in namespace `"conversation"`
   - TTL: 7 days (604800 seconds)
   - Stored data should include messages with `sources` field

4. **Current Behavior**:
   - Conversation save is returning False or throwing exception
   - Redis retrieve returns None for session_id
   - Follow-up API can't find session → 404 error

## Changes Made

### 1. Frontend Logging Enhancement
**Files**: `frontend/src/components/chat/FollowUpQuestions.tsx`, `StreamingAnswer.tsx`

Added console logging to track:
- When FollowUpQuestions component is rendered/blocked
- When follow-up API is called
- Response from follow-up API

### 2. Backend Bug Fix Attempt
**File**: `src/api/v1/chat.py`

**Lines 100-126**: Fixed `save_conversation_turn()` to serialize sources:
```python
# Serialize sources for storage (ensure they're dicts)
serialized_sources = []
if sources:
    for source in sources:
        if isinstance(source, dict):
            serialized_sources.append(source)
        elif hasattr(source, 'model_dump'):
            serialized_sources.append(source.model_dump())
        elif hasattr(source, 'dict'):
            serialized_sources.append(source.dict())

messages.append({
    "role": "assistant",
    "content": assistant_message,
    "timestamp": datetime.now(UTC).isoformat(),
    "intent": intent,
    "source_count": len(sources) if sources else 0,
    "sources": serialized_sources,  # Store full sources for follow-up generation
})
```

**Lines 70-79, 142-167, 373-386**: Added comprehensive logging:
- `save_conversation_turn_start`: When save begins
- `redis_memory_obtained`: After getting Redis client
- `storing_conversation_to_redis`: Before Redis store call
- `conversation_saved_success`: On successful save
- `conversation_save_failed_redis_returned_false`: If Redis returns False
- `conversation_save_failed_nonstreaming`: Warning if save fails in non-streaming endpoint

## Next Steps (TODO)

### Immediate (Backend Developer)
1. **Check Backend Logs**: Look for log entries:
   - `save_conversation_turn_start`
   - `storing_conversation_to_redis`
   - `conversation_saved_success` vs `conversation_save_failed_*`

2. **Verify Redis Connection**:
   - Check if Redis is accessible from backend
   - Test Redis store/retrieve manually
   - Check if namespace "conversation" is writable

3. **Test Conversation Storage**:
   ```python
   # In Python REPL or test script
   from src.components.memory import get_redis_memory
   import asyncio

   async def test():
       redis = get_redis_memory()
       success = await redis.store(
           key="test_session",
           value={"test": "data"},
           namespace="conversation",
           ttl_seconds=300
       )
       print(f"Store success: {success}")

       result = await redis.retrieve(
           key="test_session",
           namespace="conversation"
       )
       print(f"Retrieved: {result}")

   asyncio.run(test())
   ```

4. **Fix Root Cause**:
   - Determine why `redis_memory.store()` is failing
   - Check for serialization errors (large sources?)
   - Check Redis memory limits
   - Check namespace configuration

### Testing (After Backend Fix)
1. **Manual Test**:
   ```bash
   # Terminal 1: Start backend with logs visible
   uvicorn src.api.main:app --reload --log-level=debug

   # Terminal 2: Test API
   python test_stream_followup.py
   ```

2. **E2E Tests**:
   ```bash
   cd frontend
   npm run test:e2e -- followup.spec.ts
   ```

3. **Expected Result**:
   - All 9 E2E tests should pass
   - Follow-up questions (3-5) appear after each response
   - Questions are clickable and send new messages

## Test Scripts Created
1. `test_followup_api.py`: Tests non-streaming endpoint + follow-up
2. `test_stream_followup.py`: Tests SSE streaming + follow-up (matches frontend behavior)
3. `test_redis_direct.py`: Direct Redis test (has import issues, needs fix)

## Files Modified
### Frontend
- `frontend/src/components/chat/FollowUpQuestions.tsx` (logging)
- `frontend/src/components/chat/StreamingAnswer.tsx` (logging)

### Backend
- `src/api/v1/chat.py` (sources serialization + logging)

### Test Scripts
- `test_followup_api.py` (new)
- `test_stream_followup.py` (new)
- `test_redis_direct.py` (new, needs import fix)

## Summary
**Frontend is correct.** The issue is entirely in the backend conversation storage. Once Redis storage is fixed, the follow-up questions will appear automatically in the frontend with the correct `data-testid="followup-question"`.

**Backend Issue**: `save_conversation_turn()` is not successfully storing conversations to Redis, causing the follow-up endpoint to return 404.

---
**Date**: 2025-11-25
**Sprint**: 33
**Feature**: Follow-up Questions (Sprint 31 Feature 31.4)
**Status**: Backend fix required, frontend implementation complete
