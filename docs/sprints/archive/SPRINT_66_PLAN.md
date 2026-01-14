# Sprint 66 Plan - E2E Test Stabilization & Critical Backend Fixes

**Sprint Start:** 28. Dezember 2025
**Sprint Goal:** Achieve 100% E2E test pass rate by fixing critical backend bugs and knowledge base gaps
**Previous Sprint:** Sprint 65 (61% E2E pass rate, 35/57 tests passing)

---

## Sprint Objectives

### Primary Goals
1. **Fix Follow-up Questions Backend** - 8 E2E tests failing (P0)
2. **Fix Conversation History Persistence** - 5 E2E tests failing (P0)
3. **Index OMNITRACKER Documents** - 9 E2E tests failing due to missing data (P0)
4. **Achieve 100% E2E Test Pass Rate** - All 57 tests passing

### Secondary Goals
5. **Single Document Upload User Journey** - New admin workflow for testing individual documents
6. **Re-enable TypeScript Strict Mode** - TD-074 from Sprint 65

---

## Problem Analysis - Why Are E2E Tests Not at 100%?

### Current Status: 35/57 passing (61%)

Sprint 65 improved E2E tests from **0% → 61%** by fixing the stale Vite dev server. However, **22 tests (39%) still fail** due to **3 critical backend bugs**:

---

## Critical Issues (22 Failing Tests)

### Issue 1: Follow-up Questions Not Generating (8 tests, P0)

**Status:** ❌ **CRITICAL** - Core feature completely broken
**Impact:** 8/57 tests failing (14% of test suite)
**Affected Tests:**
1. `followup/followup.spec.ts:24` - should generate 3-5 follow-up questions
2. `followup/followup.spec.ts:44` - should display follow-up questions as clickable chips
3. `followup/followup.spec.ts:66` - should send follow-up question on click
4. `followup/followup.spec.ts:97` - should generate contextual follow-ups
5. `followup/followup.spec.ts:123` - should show loading state while generating follow-ups
6. `followup/followup.spec.ts:142` - should persist follow-ups across page reloads
7. `followup/followup.spec.ts:180` - should handle multiple consecutive follow-ups
8. `followup/followup.spec.ts:236` - should prevent sending empty follow-up questions

**Error Pattern:**
```
TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
- waiting for locator('[data-testid="followup-question"]') to be visible
```

**Root Cause Analysis:**

The frontend expects follow-up questions in the `/api/v1/chat` SSE response:
```typescript
// Expected SSE event from backend
data: {"type": "followup_questions", "questions": ["Question 1", "Question 2", "Question 3"]}
```

But the backend is **not sending** this event, causing the UI element `[data-testid="followup-question"]` to never render.

**Investigation Steps:**
1. Check `/api/v1/chat` endpoint in `src/api/v1/chat.py`
2. Verify `generate_followup_questions()` function is being called
3. Check Redis caching for follow-up questions (Sprint 64 feature 64.4)
4. Verify LLM prompt for follow-up generation
5. Check if follow-up generation is disabled in config

**Hypothesis:**
- Follow-up generation might be disabled in LLM config
- Redis cache key mismatch preventing retrieval
- LLM not receiving correct prompt for follow-up generation
- SSE stream not sending `followup_questions` event type

**Expected Behavior:**
```python
# src/api/v1/chat.py
async def generate_followup_questions(query: str, context: str) -> List[str]:
    """Generate 3-5 contextual follow-up questions"""
    # Should use LLM to generate questions based on query + context
    # Should cache in Redis with key: f"followup:{session_id}:{message_id}"
    # Should return 3-5 questions
    pass

# Should send SSE event:
yield f"data: {json.dumps({
    'type': 'followup_questions',
    'questions': questions
})}\n\n"
```

---

### Issue 2: Conversation History Not Persisting (5 tests, P0)

**Status:** ❌ **CRITICAL** - Core feature completely broken
**Impact:** 5/57 tests failing (9% of test suite)
**Affected Tests:**
1. `history/history.spec.ts:22` - should auto-generate conversation title from first message
2. `history/history.spec.ts:51` - should list conversations in chronological order (newest first)
3. `history/history.spec.ts:79` - should open conversation on click and restore messages
4. `history/history.spec.ts:113` - should search conversations by title and content
5. `history/history.spec.ts:170` - should handle empty history gracefully

**Error Pattern:**
```
Error: expect(received).toBeGreaterThanOrEqual(expected)
Expected: >= 1
Received:    0
```

**Root Cause Analysis:**

The frontend calls `/api/v1/history` to retrieve conversations, but the backend returns **0 conversations**. This means conversations are **not being saved** to the database.

**Investigation Steps:**
1. Check `/api/v1/history` endpoints in `src/api/v1/history.py`
2. Verify conversation saving in chat endpoint (`/api/v1/chat`)
3. Check database schema for conversation storage (Redis or PostgreSQL?)
4. Verify session ID tracking across requests
5. Check if conversation auto-save is disabled in config

**Hypothesis:**
- Conversations are not being saved after each message
- Session ID is not being persisted across requests
- Database connection issue preventing saves
- Conversation title generation failing (blocks save)
- Auto-save feature disabled in config

**Expected Behavior:**
```python
# src/api/v1/chat.py
async def save_conversation(session_id: str, message: dict):
    """Save conversation after each user message + LLM response"""
    # Should save to Redis or database
    # Should auto-generate title from first user message
    # Should include: session_id, messages[], created_at, updated_at
    pass

# src/api/v1/history.py
async def get_conversations(user_id: str) -> List[Conversation]:
    """Retrieve all conversations for user"""
    # Should return conversations in chronological order (newest first)
    # Should include: id, title, message_count, created_at, updated_at
    pass
```

---

### Issue 3: OMNITRACKER Knowledge Base Empty (9 tests, P0)

**Status:** ❌ **CRITICAL** - Test data not loaded
**Impact:** 9/57 tests failing (16% of test suite)
**Affected Tests:**
1. `search/intent.spec.ts:17` - should classify factual queries as VECTOR search
2. `search/intent.spec.ts:110` - should maintain intent context in follow-ups
3. `search/intent.spec.ts:153` - should handle single-word queries
4. `search/namespace-isolation.spec.ts:67` - should support follow-up questions within namespace context
5. `search/namespace-isolation.spec.ts:148` - should maintain session across namespace-filtered queries
6. `search/namespace-isolation.spec.ts:190` - should handle rapid sequential queries
7. `search/search.spec.ts:15` - should perform basic search with streaming
8. `search/search.spec.ts:97` - should handle multiple queries in sequence
9. `search/search.spec.ts:179` - should gracefully timeout if backend is slow

**Error Pattern:**
```
Response: "I don't have enough information in the knowledge base to answer this question."
Expected: Response containing "omnitracker", "smc", "application server", etc.
```

**Root Cause Analysis:**

**Discovery:** Qdrant collection "documents_v1" contains **only 44 documents**!

```bash
$ curl -s http://localhost:6333/collections/documents_v1 | jq '.result.points_count'
44
```

**But:** The `data/omnitracker/` directory contains **19 OMNITRACKER PDFs (66MB total)**!

```bash
$ ls -lh data/omnitracker/ | wc -l
19

$ du -sh data/omnitracker/
66M     data/omnitracker/
```

**Conclusion:** The OMNITRACKER documents **have NOT been indexed** into Qdrant!

**Investigation Steps:**
1. Verify OMNITRACKER PDFs exist in `data/omnitracker/`
2. Check ingestion pipeline configuration
3. Run document ingestion manually for OMNITRACKER directory
4. Verify chunking and embedding quality
5. Check namespace isolation (are documents in correct namespace?)

**Expected State:**
- **19 OMNITRACKER PDFs** should produce **~500-2000 chunks** (depending on chunking strategy)
- Current: 44 documents (probably old test data)
- Target: 500+ documents with OMNITRACKER content

**Ingestion Required:**
```bash
# Manual ingestion command (to be verified)
python -m src.cli.ingest --directory data/omnitracker --namespace omnitracker
```

---

## Sprint 66 Features (Derived from Issues)

### Feature 66.1: Fix Follow-up Questions Backend

**Priority:** P0 - CRITICAL
**Complexity:** Medium (2-3 days)
**Dependencies:** None

**Acceptance Criteria:**
- [ ] `/api/v1/chat` sends SSE event `{"type": "followup_questions", "questions": [...]}`
- [ ] LLM generates 3-5 contextual follow-up questions based on query + response
- [ ] Follow-up questions cached in Redis (key: `followup:{session_id}:{message_id}`)
- [ ] Frontend displays follow-up questions as clickable chips
- [ ] All 8 follow-up E2E tests passing

**Technical Implementation:**

1. **Backend Implementation (`src/api/v1/chat.py`):**
```python
async def generate_followup_questions(
    query: str,
    response: str,
    context: List[dict],
    session_id: str
) -> List[str]:
    """Generate 3-5 contextual follow-up questions using LLM

    Args:
        query: User's original query
        response: LLM's response to the query
        context: Retrieved documents/context
        session_id: Current session ID for caching

    Returns:
        List of 3-5 follow-up question strings
    """
    # 1. Build prompt for follow-up generation
    prompt = f"""Based on this conversation, generate 3-5 relevant follow-up questions:

User Query: {query}
Assistant Response: {response}

Generate questions that:
- Explore related topics
- Dig deeper into the response
- Are specific and actionable
- Relate to the available context

Return ONLY the questions, one per line, without numbering."""

    # 2. Call LLM (use intent classification model or dedicated follow-up model)
    llm_config = get_llm_config("followup_generation")
    llm = get_llm(llm_config)

    result = await llm.ainvoke(prompt)
    questions = [q.strip() for q in result.content.split('\n') if q.strip()][:5]

    # 3. Cache in Redis (60s TTL)
    cache_key = f"followup:{session_id}:{hash(query)}"
    await redis_client.setex(cache_key, 60, json.dumps(questions))

    return questions

# 4. Send SSE event in chat endpoint
async def chat_stream(...):
    # ... after generating response ...

    # Generate follow-up questions
    followup_questions = await generate_followup_questions(
        query=message.content,
        response=full_response,
        context=retrieved_docs,
        session_id=session_id
    )

    # Send SSE event
    yield f"data: {json.dumps({
        'type': 'followup_questions',
        'questions': followup_questions
    })}\n\n"
```

2. **LLM Config Setup:**
- Add new use case `followup_generation` to LLM config
- Default model: `qwen3:32b` (same as intent classification)
- Fallback: OpenAI GPT-4o-mini

3. **Testing:**
```python
# tests/integration/test_followup_questions.py
async def test_followup_questions_generated():
    """Test that follow-up questions are generated and sent via SSE"""
    response = client.post("/api/v1/chat", json={
        "message": "What is the OMNITRACKER SMC?",
        "session_id": "test-session-123"
    })

    # Parse SSE stream
    events = parse_sse_stream(response.content)

    # Verify followup_questions event exists
    followup_event = next(e for e in events if e["type"] == "followup_questions")
    assert followup_event is not None
    assert len(followup_event["questions"]) >= 3
    assert len(followup_event["questions"]) <= 5
    assert all(q.endswith("?") for q in followup_event["questions"])
```

**Files to Modify:**
- `src/api/v1/chat.py` - Add `generate_followup_questions()`, send SSE event
- `src/core/config.py` - Add `followup_generation` LLM config
- `src/domains/llm_integration/llm_factory.py` - Support new use case
- `tests/integration/test_followup_questions.py` - Integration tests

---

### Feature 66.2: Fix Conversation History Persistence

**Priority:** P0 - CRITICAL
**Complexity:** Medium-High (3-4 days)
**Dependencies:** None

**Acceptance Criteria:**
- [ ] Conversations saved to database after each message exchange
- [ ] Conversation title auto-generated from first user message
- [ ] `/api/v1/history` returns conversations in chronological order (newest first)
- [ ] Conversations include metadata: message_count, created_at, updated_at
- [ ] Search functionality works (by title and content)
- [ ] All 5 conversation history E2E tests passing

**Technical Implementation:**

1. **Database Schema (Redis or PostgreSQL):**

**Option A: Redis (Recommended for MVP):**
```python
# Key structure:
# conversation:{user_id}:{session_id} → Conversation JSON
# conversation_index:{user_id} → Sorted Set (score = created_at timestamp)

# Conversation JSON structure:
{
    "id": "session-uuid-123",
    "user_id": "user-123",
    "title": "OMNITRACKER SMC Overview",
    "messages": [
        {"role": "user", "content": "What is the SMC?", "timestamp": "2025-12-28T10:00:00Z"},
        {"role": "assistant", "content": "The SMC is...", "timestamp": "2025-12-28T10:00:05Z"}
    ],
    "message_count": 2,
    "created_at": "2025-12-28T10:00:00Z",
    "updated_at": "2025-12-28T10:00:05Z",
    "namespace": "omnitracker"
}
```

**Option B: PostgreSQL (Better for production):**
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    namespace VARCHAR(100),
    message_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_created (user_id, created_at DESC)
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

2. **Backend Implementation (`src/api/v1/history.py`):**

```python
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime

class Conversation(BaseModel):
    id: str
    user_id: str
    title: str
    messages: List[Message]
    message_count: int
    created_at: datetime
    updated_at: datetime
    namespace: Optional[str] = None

class ConversationService:
    """Service for managing conversation persistence"""

    async def save_conversation(
        self,
        session_id: str,
        user_id: str,
        messages: List[Message],
        namespace: Optional[str] = None
    ) -> Conversation:
        """Save or update conversation

        - Auto-generate title from first user message
        - Update message_count and updated_at
        """
        # Generate title from first user message (if new conversation)
        existing = await self.get_conversation(session_id)
        if not existing:
            first_user_msg = next((m for m in messages if m.role == "user"), None)
            title = await self._generate_title(first_user_msg.content if first_user_msg else "New Conversation")
        else:
            title = existing.title

        conversation = Conversation(
            id=session_id,
            user_id=user_id,
            title=title,
            messages=messages,
            message_count=len(messages),
            created_at=existing.created_at if existing else datetime.now(),
            updated_at=datetime.now(),
            namespace=namespace
        )

        # Save to Redis
        key = f"conversation:{user_id}:{session_id}"
        await redis_client.set(key, conversation.json())

        # Update index (sorted set by created_at)
        index_key = f"conversation_index:{user_id}"
        await redis_client.zadd(index_key, {session_id: conversation.created_at.timestamp()})

        return conversation

    async def get_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """Get all conversations for user, sorted by created_at DESC"""
        index_key = f"conversation_index:{user_id}"

        # Get session IDs from sorted set (newest first)
        session_ids = await redis_client.zrevrange(index_key, offset, offset + limit - 1)

        # Fetch conversations
        conversations = []
        for session_id in session_ids:
            conv = await self.get_conversation(session_id.decode())
            if conv:
                conversations.append(conv)

        return conversations

    async def search_conversations(
        self,
        user_id: str,
        query: str
    ) -> List[Conversation]:
        """Search conversations by title or content"""
        all_convs = await self.get_conversations(user_id, limit=1000)

        # Simple text search (can be improved with FTS)
        query_lower = query.lower()
        results = []
        for conv in all_convs:
            # Search in title
            if query_lower in conv.title.lower():
                results.append(conv)
                continue

            # Search in message content
            for msg in conv.messages:
                if query_lower in msg.content.lower():
                    results.append(conv)
                    break

        return results

    async def _generate_title(self, first_message: str) -> str:
        """Generate conversation title from first user message using LLM"""
        prompt = f"""Generate a short, descriptive title (max 60 characters) for this conversation:

User's first message: {first_message}

Title (concise, no quotes):"""

        llm_config = get_llm_config("title_generation")
        llm = get_llm(llm_config)

        result = await llm.ainvoke(prompt)
        title = result.content.strip().strip('"').strip("'")[:60]

        return title

# API Endpoints
@router.get("/api/v1/history")
async def get_conversation_history(
    user_id: str = "default",  # TODO: Get from auth
    limit: int = 50,
    offset: int = 0
) -> List[Conversation]:
    """Get conversation history for user"""
    service = ConversationService()
    return await service.get_conversations(user_id, limit, offset)

@router.get("/api/v1/history/{session_id}")
async def get_conversation(session_id: str) -> Conversation:
    """Get specific conversation by ID"""
    service = ConversationService()
    conv = await service.get_conversation(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@router.delete("/api/v1/history/{session_id}")
async def delete_conversation(session_id: str, user_id: str = "default"):
    """Delete conversation"""
    service = ConversationService()
    await service.delete_conversation(session_id, user_id)
    return {"status": "deleted"}

@router.get("/api/v1/history/search")
async def search_conversations(query: str, user_id: str = "default") -> List[Conversation]:
    """Search conversations by title or content"""
    service = ConversationService()
    return await service.search_conversations(user_id, query)
```

3. **Integration with Chat Endpoint:**

```python
# src/api/v1/chat.py
async def chat_stream(...):
    # ... existing code ...

    # After generating response, save conversation
    conversation_service = ConversationService()

    # Build messages list
    messages = session_messages + [
        Message(role="user", content=message.content, timestamp=datetime.now()),
        Message(role="assistant", content=full_response, timestamp=datetime.now())
    ]

    # Save conversation
    await conversation_service.save_conversation(
        session_id=session_id,
        user_id="default",  # TODO: Get from auth
        messages=messages,
        namespace=message.namespace
    )
```

4. **Testing:**
```python
# tests/integration/test_conversation_history.py
async def test_conversation_saved_after_chat():
    """Test that conversations are saved after each message"""
    session_id = str(uuid.uuid4())

    # Send first message
    response1 = client.post("/api/v1/chat", json={
        "message": "What is the OMNITRACKER SMC?",
        "session_id": session_id
    })

    # Verify conversation exists
    history = client.get("/api/v1/history").json()
    assert len(history) >= 1

    # Find our conversation
    conv = next(c for c in history if c["id"] == session_id)
    assert conv["message_count"] == 2  # user + assistant
    assert conv["title"] != ""
    assert "OMNITRACKER" in conv["title"] or "SMC" in conv["title"]

async def test_conversation_title_generated():
    """Test that title is auto-generated from first message"""
    session_id = str(uuid.uuid4())

    response = client.post("/api/v1/chat", json={
        "message": "Explain the OMNITRACKER Application Server architecture",
        "session_id": session_id
    })

    conv = client.get(f"/api/v1/history/{session_id}").json()
    assert "Application Server" in conv["title"] or "architecture" in conv["title"]

async def test_search_conversations():
    """Test conversation search functionality"""
    # Create conversation with known content
    session_id = str(uuid.uuid4())
    client.post("/api/v1/chat", json={
        "message": "Tell me about load balancing in OMNITRACKER",
        "session_id": session_id
    })

    # Search for it
    results = client.get("/api/v1/history/search?query=load balancing").json()
    assert len(results) >= 1
    assert any(session_id == r["id"] for r in results)
```

**Files to Modify:**
- `src/api/v1/history.py` - Implement ConversationService, API endpoints
- `src/api/v1/chat.py` - Integrate conversation saving
- `src/core/models.py` - Add Conversation and Message Pydantic models
- `tests/integration/test_conversation_history.py` - Integration tests

---

### Feature 66.3: Index OMNITRACKER Documents

**Priority:** P0 - CRITICAL
**Complexity:** Low-Medium (1-2 days)
**Dependencies:** Docling container running

**Acceptance Criteria:**
- [ ] All 19 OMNITRACKER PDFs (66MB) indexed into Qdrant
- [ ] Qdrant `documents_v1` collection contains 500+ chunks
- [ ] Retrieval returns relevant results for OMNITRACKER queries
- [ ] All 9 OMNITRACKER-related E2E tests passing

**Technical Implementation:**

1. **Verify OMNITRACKER Documents:**
```bash
$ ls -lh data/omnitracker/
# Should show 19 PDFs totaling ~66MB
```

2. **Run Ingestion Pipeline:**

**Option A: Via Admin UI (Recommended for testing):**
- Navigate to http://192.168.178.10/admin/ingestion
- Select directory: `data/omnitracker/`
- Namespace: `omnitracker`
- Click "Ingest Documents"
- Wait for processing (may take 10-30 minutes for 66MB)

**Option B: Via CLI:**
```bash
# Start Docling container if not running
docker compose -f docker-compose.dgx-spark.yml up -d docling

# Run ingestion
python -m src.cli.ingest \
    --directory data/omnitracker \
    --namespace omnitracker \
    --batch-size 10 \
    --verbose
```

**Option C: Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/ingest \
    -H "Content-Type: application/json" \
    -d '{
        "directory": "data/omnitracker",
        "namespace": "omnitracker",
        "batch_size": 10
    }'
```

3. **Verify Ingestion:**

```bash
# Check document count
curl -s http://localhost:6333/collections/documents_v1 | jq '.result.points_count'
# Expected: 500-2000 (was 44 before)

# Search for OMNITRACKER content
curl -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{
        "message": "What is the OMNITRACKER SMC?",
        "namespace": "omnitracker"
    }'
# Expected: Response with relevant OMNITRACKER content (not "not enough information")
```

4. **Monitor Ingestion Progress:**

The ingestion pipeline should log progress:
```
[INFO] Processing document 1/19: 02_CDays2025-Roadmap_OMNITRACKER-Plattform.pdf
[INFO] Extracted 45 pages, 1200 chunks
[INFO] Embedding batch 1/12 (100 chunks)
[INFO] Uploaded batch 1/12 to Qdrant
...
[INFO] Ingestion complete: 19 documents, 1543 chunks, 15.2 minutes
```

5. **Troubleshooting:**

**If ingestion fails:**
- Check Docling container logs: `docker logs docling`
- Verify PDF files are readable: `file data/omnitracker/*.pdf`
- Check disk space: `df -h`
- Verify Qdrant connection: `curl http://localhost:6333/collections`

**If retrieval still fails:**
- Check embedding model: Verify BGE-M3 loaded on GPU
- Check chunking strategy: Verify chunks are 800-1800 tokens (ADR-039)
- Check BM25 indexing: Verify BM25 index created alongside vector index

6. **Testing:**
```python
# tests/integration/test_omnitracker_retrieval.py
async def test_omnitracker_documents_indexed():
    """Verify OMNITRACKER documents are in Qdrant"""
    # Check collection size
    response = requests.get("http://localhost:6333/collections/documents_v1")
    data = response.json()
    assert data["result"]["points_count"] >= 500, "OMNITRACKER documents not indexed"

async def test_omnitracker_retrieval():
    """Test retrieval of OMNITRACKER content"""
    response = client.post("/api/v1/chat", json={
        "message": "What is the OMNITRACKER SMC and how does it work?",
        "namespace": "omnitracker"
    })

    # Parse SSE stream
    events = parse_sse_stream(response.content)
    response_text = "".join(e["content"] for e in events if e["type"] == "chunk")

    # Verify response contains OMNITRACKER content
    assert "omnitracker" in response_text.lower()
    assert "smc" in response_text.lower() or "system management console" in response_text.lower()
    assert "not enough information" not in response_text.lower()
```

**Files to Modify:**
- `src/cli/ingest.py` - CLI ingestion script (if not exists)
- `src/api/v1/admin/ingestion.py` - Admin UI ingestion endpoint
- `tests/integration/test_omnitracker_retrieval.py` - Integration tests

---

### Feature 66.4: Single Document Upload User Journey (New)

**Priority:** P1 - High
**Complexity:** Low (1-2 days)
**Dependencies:** Feature 66.3 (Ingestion pipeline working)

**User Story:**
> As an **admin**, I want to **upload a single OMNITRACKER document via the admin UI and immediately search its content**, so that I can **quickly test document ingestion and retrieval without processing the entire directory**.

**Motivation:**
- Current ingestion processes entire directories (19 PDFs, 10-30 minutes)
- Admins need to test single documents quickly (1 PDF, 1-3 minutes)
- Useful for:
  - Testing new document types
  - Debugging ingestion issues
  - Quick content verification
  - Demo purposes

**Acceptance Criteria:**
- [ ] Admin UI has "Upload Single Document" button on `/admin/ingestion` page
- [ ] User can select a PDF file from local filesystem
- [ ] File is uploaded to backend and ingested immediately
- [ ] Progress indicator shows: Upload → Parse → Chunk → Embed → Index
- [ ] After ingestion, user is redirected to chat page with pre-filled search query
- [ ] Search results contain content from uploaded document
- [ ] E2E test covers full user journey

**Technical Implementation:**

1. **Frontend: Upload UI (`frontend/src/pages/admin/AdminIngestionPage.tsx`):**

```typescript
const AdminIngestionPage = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
    } else {
      alert('Please select a PDF file');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('namespace', 'omnitracker');

    try {
      // Upload file and get SSE stream for progress
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/ingest/upload`, {
        method: 'POST',
        body: formData,
      });

      // Parse SSE stream for progress updates
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            setUploadProgress(data);
          }
        }
      }

      // Redirect to chat with pre-filled query
      const query = `Tell me about the content in ${selectedFile.name}`;
      window.location.href = `/?query=${encodeURIComponent(query)}`;
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Document Ingestion</h1>

      {/* Single Document Upload */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h2 className="text-xl font-semibold mb-4">Upload Single Document</h2>

        <input
          type="file"
          accept="application/pdf"
          onChange={handleFileSelect}
          className="mb-4"
        />

        {selectedFile && (
          <div className="mb-4">
            <p className="text-sm text-gray-600">
              Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!selectedFile || isUploading}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:bg-gray-400"
        >
          {isUploading ? 'Uploading...' : 'Upload & Ingest'}
        </button>

        {/* Progress Indicator */}
        {uploadProgress && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">{uploadProgress.stage}</span>
              <span className="text-sm text-gray-600">{uploadProgress.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress.progress}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">{uploadProgress.message}</p>
          </div>
        )}
      </div>

      {/* Existing directory ingestion UI */}
      {/* ... */}
    </div>
  );
};
```

2. **Backend: Upload Endpoint (`src/api/v1/admin/ingestion.py`):**

```python
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import tempfile
import os

@router.post("/api/v1/admin/ingest/upload")
async def upload_and_ingest_document(
    file: UploadFile = File(...),
    namespace: str = "default"
):
    """Upload and ingest a single document with progress streaming"""

    async def progress_stream():
        """SSE stream for upload progress"""
        try:
            # 1. Save uploaded file to temp directory
            yield f"data: {json.dumps({'stage': 'Uploading', 'progress': 10, 'message': 'Saving file...'})}\n\n"

            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_path = temp_file.name

            yield f"data: {json.dumps({'stage': 'Parsing', 'progress': 30, 'message': 'Extracting text with Docling...'})}\n\n"

            # 2. Parse document with Docling
            from src.domains.document_processing.docling_parser import DoclingParser
            parser = DoclingParser()
            parsed_doc = await parser.parse_document(temp_path)

            yield f"data: {json.dumps({'stage': 'Chunking', 'progress': 50, 'message': f'Creating chunks ({len(parsed_doc.pages)} pages)...'})}\n\n"

            # 3. Chunk document
            from src.domains.document_processing.chunking import SectionAwareChunker
            chunker = SectionAwareChunker()
            chunks = chunker.chunk_document(parsed_doc)

            yield f"data: {json.dumps({'stage': 'Embedding', 'progress': 70, 'message': f'Generating embeddings ({len(chunks)} chunks)...'})}\n\n"

            # 4. Generate embeddings
            from src.domains.vector_search.embedding import BGEEmbedding
            embedding_model = BGEEmbedding()
            embeddings = await embedding_model.embed_documents([c.content for c in chunks])

            yield f"data: {json.dumps({'stage': 'Indexing', 'progress': 90, 'message': 'Uploading to Qdrant...'})}\n\n"

            # 5. Upload to Qdrant
            from src.domains.vector_search.qdrant_client import QdrantClient
            qdrant = QdrantClient()
            await qdrant.upload_points(
                collection_name="documents_v1",
                points=[
                    {
                        "id": str(uuid.uuid4()),
                        "vector": emb,
                        "payload": {
                            "content": chunk.content,
                            "metadata": {
                                "source": file.filename,
                                "namespace": namespace,
                                "chunk_index": i,
                                "page_number": chunk.page_number
                            }
                        }
                    }
                    for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
                ]
            )

            # 6. Complete
            yield f"data: {json.dumps({'stage': 'Complete', 'progress': 100, 'message': f'Indexed {len(chunks)} chunks successfully!'})}\n\n"

            # Clean up temp file
            os.unlink(temp_path)

        except Exception as e:
            yield f"data: {json.dumps({'stage': 'Error', 'progress': 0, 'message': str(e)})}\n\n"

    return StreamingResponse(progress_stream(), media_type="text/event-stream")
```

3. **E2E Test (`frontend/e2e/admin/single-document-upload.spec.ts`):**

```typescript
import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Single Document Upload User Journey', () => {
  test('should upload document, ingest, and search content', async ({ page }) => {
    // 1. Navigate to admin ingestion page
    await page.goto('/admin/ingestion');

    // 2. Select PDF file from data/omnitracker/
    const filePath = path.join(__dirname, '../../../data/omnitracker/02_CDays2025-Roadmap_OMNITRACKER-Plattform.pdf');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    // 3. Verify file selected
    await expect(page.locator('text=/02_CDays2025-Roadmap_OMNITRACKER-Plattform.pdf/')).toBeVisible();

    // 4. Click upload button
    await page.locator('button:has-text("Upload & Ingest")').click();

    // 5. Wait for progress completion (max 3 minutes for single doc)
    await expect(page.locator('text=/Complete/')).toBeVisible({ timeout: 180000 });

    // 6. Should redirect to chat page
    await expect(page).toHaveURL(/\/\?query=/);

    // 7. Should have pre-filled query
    const messageInput = page.locator('[data-testid="message-input"]');
    const inputValue = await messageInput.inputValue();
    expect(inputValue).toContain('02_CDays2025-Roadmap_OMNITRACKER-Plattform.pdf');

    // 8. Send query
    await page.locator('[data-testid="send-button"]').click();

    // 9. Wait for response
    await page.waitForSelector('[data-testid="message-assistant"]', { timeout: 30000 });

    // 10. Verify response contains content from uploaded document
    const response = await page.locator('[data-testid="message-assistant"]').last().textContent();
    expect(response?.toLowerCase()).toContain('omnitracker');
    expect(response?.toLowerCase()).not.toContain('not enough information');
  });
});
```

**Files to Create:**
- `frontend/src/pages/admin/AdminIngestionPage.tsx` - Upload UI
- `src/api/v1/admin/ingestion.py` - Upload endpoint
- `frontend/e2e/admin/single-document-upload.spec.ts` - E2E test

---

### Feature 66.5: Re-enable TypeScript Strict Mode (TD-074)

**Priority:** P1 - High
**Complexity:** Low (1 day)
**Dependencies:** None

**Acceptance Criteria:**
- [ ] `strict: true` in `tsconfig.app.json`
- [ ] `noUnusedLocals: true` in `tsconfig.app.json`
- [ ] `noUnusedParameters: true` in `tsconfig.app.json`
- [ ] Frontend builds without type errors
- [ ] All E2E tests still passing

**Technical Implementation:**

1. **Upgrade React Type Definitions:**
```bash
cd frontend
npm install --save-dev @types/react@latest @types/react-dom@latest
```

2. **Fix Conditional JSX Type Errors:**

**Before (causes type error):**
```typescript
{condition && <Component />}
```

**After (type-safe):**
```typescript
{condition ? <Component /> : null}
```

3. **Run Type Check:**
```bash
cd frontend
npm run type-check
# Should show no errors
```

4. **Re-enable Strict Mode:**
```json
// frontend/tsconfig.app.json
{
  "compilerOptions": {
    "strict": true,  // ✅ Re-enabled
    "noUnusedLocals": true,  // ✅ Re-enabled
    "noUnusedParameters": true  // ✅ Re-enabled
  }
}
```

5. **Verify Build:**
```bash
npm run build
# Should complete without errors
```

**Files to Modify:**
- `frontend/tsconfig.app.json` - Re-enable strict mode
- `frontend/src/**/*.tsx` - Fix conditional JSX patterns (estimated 10-20 files)

---

## Sprint 66 Success Criteria

### Primary Goal: 100% E2E Test Pass Rate

**Target:** 57/57 tests passing (100%)
**Current:** 35/57 tests passing (61%)
**Gap:** 22 tests to fix

**Breakdown:**
- [ ] Fix 8 follow-up question tests (Feature 66.1)
- [ ] Fix 5 conversation history tests (Feature 66.2)
- [ ] Fix 9 OMNITRACKER retrieval tests (Feature 66.3)

### Secondary Goals

- [ ] Single document upload user journey working (Feature 66.4)
- [ ] TypeScript strict mode re-enabled (Feature 66.5)
- [ ] All features documented
- [ ] All features have E2E tests

---

## Sprint 66 Timeline

### Week 1 (Days 1-3)

**Day 1:**
- Feature 66.3: Index OMNITRACKER documents (1 day)
  - Run ingestion pipeline
  - Verify 500+ documents in Qdrant
  - Test retrieval with OMNITRACKER queries
  - Fix 9 E2E tests

**Day 2-3:**
- Feature 66.1: Fix follow-up questions backend (2 days)
  - Implement `generate_followup_questions()`
  - Send SSE event in chat endpoint
  - Add LLM config for follow-up generation
  - Fix 8 E2E tests

### Week 2 (Days 4-7)

**Day 4-6:**
- Feature 66.2: Fix conversation history persistence (3 days)
  - Design database schema (Redis or PostgreSQL)
  - Implement ConversationService
  - Create API endpoints (/api/v1/history)
  - Integrate with chat endpoint
  - Fix 5 E2E tests

**Day 7:**
- Feature 66.4: Single document upload user journey (1 day)
  - Build upload UI
  - Implement upload endpoint with progress streaming
  - Create E2E test

### Week 3 (Day 8)

**Day 8:**
- Feature 66.5: Re-enable TypeScript strict mode (1 day)
  - Upgrade @types/react
  - Fix conditional JSX patterns
  - Re-enable strict mode
  - Verify build + E2E tests

### Sprint Review

**Day 9:**
- Run full E2E test suite (594 tests)
- Verify 100% pass rate (57/57 core tests)
- Create Sprint 66 report
- Update SPRINT_PLAN.md

---

## Risk Assessment

### High Risk

**Risk:** OMNITRACKER ingestion takes longer than expected (>2 hours)
**Mitigation:** Run ingestion overnight, monitor progress, use single document upload for testing

**Risk:** Conversation history database schema requires major refactoring
**Mitigation:** Start with simple Redis implementation, migrate to PostgreSQL later if needed

### Medium Risk

**Risk:** Follow-up question generation produces low-quality questions
**Mitigation:** Iterate on LLM prompt, test with multiple models (qwen3:32b, llama3.2:8b, GPT-4o-mini)

**Risk:** TypeScript strict mode reveals many type errors
**Mitigation:** Fix errors incrementally, prioritize critical files first

### Low Risk

**Risk:** Single document upload UI has UX issues
**Mitigation:** Use existing upload patterns from other admin pages

---

## Dependencies

### External Dependencies
- **Docling Container:** Must be running for document ingestion (Feature 66.3, 66.4)
- **Qdrant:** Must be healthy for document indexing and retrieval
- **Redis:** Required for conversation history (Feature 66.2) and follow-up caching (Feature 66.1)
- **LLM (Ollama/qwen3:32b):** Required for follow-up generation and title generation

### Internal Dependencies
- **BGE-M3 GPU Acceleration:** Must be working (verified in Sprint 65)
- **Vite Dev Server:** Must be restarted before E2E tests
- **Frontend Build:** Must pass before deploying to production

---

## Definition of Done

### Feature-Level DoD
- [ ] Implementation complete and tested
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] E2E tests passing (all affected tests)
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] No new technical debt introduced

### Sprint-Level DoD
- [ ] All 5 features complete
- [ ] 100% E2E test pass rate (57/57 tests)
- [ ] Sprint 66 report created
- [ ] SPRINT_PLAN.md updated
- [ ] Docker containers rebuilt (if needed)
- [ ] Production deployment successful
- [ ] No critical bugs in backlog

---

## Testing Strategy

### Unit Tests
- `tests/unit/test_followup_generation.py` - Follow-up question generation logic
- `tests/unit/test_conversation_service.py` - Conversation CRUD operations
- `tests/unit/test_title_generation.py` - Title generation from first message

### Integration Tests
- `tests/integration/test_followup_questions.py` - Follow-up questions E2E (backend + LLM)
- `tests/integration/test_conversation_history.py` - Conversation history persistence
- `tests/integration/test_omnitracker_retrieval.py` - OMNITRACKER document retrieval

### E2E Tests
- `frontend/e2e/followup/followup.spec.ts` - 9 follow-up question tests
- `frontend/e2e/history/history.spec.ts` - 7 conversation history tests
- `frontend/e2e/search/search.spec.ts` - 17 search tests (including OMNITRACKER)
- `frontend/e2e/admin/single-document-upload.spec.ts` - Single document upload journey (new)

### Manual Testing
- Upload single OMNITRACKER document via admin UI
- Verify follow-up questions appear after responses
- Verify conversation history loads on page reload
- Search for OMNITRACKER-specific content (SMC, Application Server, etc.)

---

## Rollback Plan

If Sprint 66 features cause regressions:

1. **Revert Git Commits:**
```bash
git revert <sprint-66-commit-hash>
git push
```

2. **Rebuild Containers:**
```bash
docker compose -f docker-compose.dgx-spark.yml build --no-cache api
docker compose -f docker-compose.dgx-spark.yml up -d
```

3. **Restore Database State:**
```bash
# If using Redis for conversation history
redis-cli FLUSHDB  # Clear conversations (if corrupted)

# If using Qdrant for documents
# Re-run ingestion from backup directory
```

4. **Rollback Frontend:**
```bash
cd frontend
git checkout <previous-working-commit>
npm run build
```

---

## Success Metrics

### E2E Test Pass Rate
- **Sprint 64:** 337/594 (57%)
- **Sprint 65:** 35/57 core tests (61%)
- **Sprint 66 Target:** 57/57 core tests (100%) ✅

### Performance Metrics
- BGE-M3 Embedding Speed: 50-200ms per batch (GPU) ✅ (from Sprint 65)
- Follow-up Generation Time: <3s per query (Target)
- Conversation History Load Time: <500ms (Target)
- Single Document Ingestion Time: 1-3 minutes (Target)

### Code Quality
- Unit Test Coverage: >80%
- Integration Test Coverage: >70%
- E2E Test Coverage: 100% of core user journeys
- TypeScript Strict Mode: Enabled ✅

---

## Next Sprint Preview (Sprint 67)

After achieving 100% E2E test pass rate in Sprint 66, Sprint 67 will focus on:

1. **Full Test Suite Execution:** Run all 594 E2E tests (not just 57 core tests)
2. **Performance Optimization:** Reduce follow-up generation time, optimize conversation history loading
3. **Batch Document Ingestion:** Support for bulk OMNITRACKER document ingestion (all 19 PDFs at once)
4. **Advanced Search Features:** Filters, sorting, faceting
5. **User Authentication:** Multi-user support, conversation isolation

---

**Sprint 66 Plan Created:** 2025-12-28
**Estimated Completion:** 2026-01-10 (2 weeks)
**Sprint Lead:** Claude Sonnet 4.5
**Environment:** DGX Spark (NVIDIA GB10, CUDA 13.0, ARM64)
