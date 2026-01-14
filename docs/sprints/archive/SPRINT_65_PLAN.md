# Sprint 65 Plan: E2E Test Fixes & Performance Optimization

## Sprint Overview

| Field | Value |
|-------|-------|
| Sprint Number | 65 |
| Start Date | 2025-12-26 |
| Duration | 7-10 days |
| Total Story Points | 40 SP |
| Focus | Critical E2E Test Failures, Performance Optimization, Test Infrastructure |
| Priority | HIGH - Production readiness depends on these fixes |

## Context: Production Deployment E2E Testing Results

**Baseline:** Sprint 64 production deployment tested with Playwright E2E suite (594 tests)
- ✅ **337 tests passed (56.7%)** - Core user journeys working
- ❌ **249 tests failed (41.9%)** - Critical features broken/slow
- ⏭️ **8 tests skipped (1.3%)**

**Root Causes Identified:**
1. **LLM Operation Timeouts:** Follow-up questions, research mode (>30s)
2. **UI Page Load Issues:** Domain training wizard timeout
3. **Database Query Performance:** History/conversation loading
4. **State Management:** Graph filter persistence failures
5. **API Validation Mismatches:** Domain training API
6. **Test Infrastructure:** Aggressive 30s timeouts for async operations

**Production Impact:**
- **Follow-up Questions:** Completely broken (11% success)
- **Domain Training:** Admin workflow blocked (40% success)
- **History Management:** User experience degraded (50% success)
- **Graph Visualization:** Partially broken (45% success)
- **Research Mode:** Performance issues (50% success)

See: [PRODUCTION_DEPLOYMENT_TEST_RESULTS.md](../../PRODUCTION_DEPLOYMENT_TEST_RESULTS.md)

---

## Features

### Feature 65.1: Follow-up Questions Fix (8 SP) 🔴 CRITICAL

**Priority:** P0 - Core feature completely broken
**Current Status:** 1/9 tests passing (11% success rate)
**Agent:** Backend Agent (Parallel Execution)

#### Problem Analysis

**E2E Test Failures:**
```
❌ should generate 3-5 follow-up questions (30s timeout)
❌ should display follow-up questions as clickable chips (30s timeout)
❌ should send follow-up question on click (30s timeout)
❌ should generate contextual follow-ups (30s timeout)
❌ should show loading state while generating (30s timeout)
❌ should persist follow-ups across page reloads (timeout)
❌ should handle multiple consecutive follow-ups (timeout)
❌ should prevent sending empty follow-up questions (timeout)
✅ should display follow-up questions after short responses (ONLY PASS)
```

**Root Causes:**
1. **Synchronous Generation:** Follow-up generation blocks response delivery (Sprint 52 async pattern not implemented)
2. **LLM Response Time:** >30s for follow-up generation (exceeds test timeout)
3. **No Caching:** Same questions regenerated repeatedly
4. **No Pre-warming:** Cold LLM model on first request

#### Implementation Tasks

##### Task 65.1.1: Async Follow-up Generation (3 SP)

**Implement Sprint 52.3 async pattern:**

```python
# src/agents/followup_generator.py (NEW/UPDATE)

from typing import List, AsyncGenerator
from src.core.redis_memory import get_redis_client

class FollowupGenerator:
    """Async follow-up question generator with caching."""

    async def generate_followups_async(
        self,
        conversation_id: str,
        last_query: str,
        last_answer: str,
        context: List[str]
    ) -> AsyncGenerator[dict, None]:
        """
        Generate follow-up questions asynchronously.

        Flow:
        1. Check Redis cache for similar context
        2. Generate questions via LLM (async)
        3. Cache results (TTL: 30min)
        4. Yield each question as SSE event
        """
        # Check cache first
        cache_key = f"followup:{conversation_id}:{hash(last_query)}"
        cached = await self.redis.get(cache_key)
        if cached:
            for question in json.loads(cached):
                yield {"type": "followup_question", "data": question}
            return

        # Generate via LLM (async)
        questions = await self.llm_proxy.generate_async(
            prompt=self._build_prompt(last_query, last_answer, context),
            max_tokens=150,
            temperature=0.7
        )

        # Parse and cache
        parsed = self._parse_questions(questions)
        await self.redis.setex(cache_key, 1800, json.dumps(parsed))

        for question in parsed:
            yield {"type": "followup_question", "data": question}
```

**Files:**
- `src/agents/followup_generator.py` (NEW - async generator)
- `src/agents/coordinator.py` (UPDATE - emit followup_questions event after answer complete)
- `tests/unit/agents/test_followup_generator.py` (NEW - async tests)

##### Task 65.1.2: SSE Event Integration (2 SP)

**Update coordinator to emit follow-ups separately:**

```python
# src/agents/coordinator.py

async def process_query(self, query: str) -> AsyncGenerator[dict, None]:
    """Process query with async follow-up generation."""

    # 1. Stream answer normally
    async for event in self.answer_generator.generate(query):
        yield event

    # 2. Answer complete - trigger async follow-up generation
    yield {"type": "answer_complete"}

    # 3. Generate follow-ups asynchronously (non-blocking)
    async for followup_event in self.followup_gen.generate_followups_async(
        conversation_id=self.conversation_id,
        last_query=query,
        last_answer=self.last_answer,
        context=self.get_recent_context()
    ):
        yield followup_event
```

**Files:**
- `src/agents/coordinator.py` (UPDATE - async followup emission)
- `src/api/v1/chat.py` (UPDATE - handle followup_questions SSE event)

##### Task 65.1.3: Frontend Loading State (2 SP)

**Add loading skeleton for follow-up questions:**

```tsx
// frontend/src/components/chat/FollowUpQuestions.tsx

export function FollowUpQuestions({ conversationId }: Props) {
  const [loading, setLoading] = useState(true);
  const [questions, setQuestions] = useState<string[]>([]);

  useEffect(() => {
    // Listen for SSE followup_questions events
    const eventSource = useStreamChat();

    eventSource.addEventListener('answer_complete', () => {
      setLoading(true); // Show skeleton
    });

    eventSource.addEventListener('followup_question', (event) => {
      setQuestions(prev => [...prev, event.data]);
      setLoading(false); // Hide skeleton
    });
  }, [conversationId]);

  if (loading) {
    return <FollowUpSkeleton />; // Shimmer effect
  }

  return (
    <div className="followup-chips">
      {questions.map(q => (
        <FollowUpChip key={q} question={q} onClick={() => handleClick(q)} />
      ))}
    </div>
  );
}
```

**Files:**
- `frontend/src/components/chat/FollowUpQuestions.tsx` (UPDATE - loading state)
- `frontend/src/hooks/useStreamChat.ts` (UPDATE - handle followup_questions event)
- `frontend/src/components/chat/FollowUpSkeleton.tsx` (NEW - loading skeleton)

##### Task 65.1.4: LLM Pre-warming (1 SP)

**Pre-warm LLM model on API startup:**

```python
# src/api/main.py

@app.on_event("startup")
async def startup_event():
    """Pre-warm LLM for faster first request."""
    logger.info("Pre-warming LLM for follow-up generation...")

    # Trigger dummy follow-up generation to warm model
    followup_gen = FollowupGenerator()
    await followup_gen.generate_followups_async(
        conversation_id="warmup",
        last_query="test",
        last_answer="test",
        context=[]
    )

    logger.info("LLM pre-warmed successfully")
```

**Files:**
- `src/api/main.py` (UPDATE - startup event)

#### Acceptance Criteria

- [ ] **Follow-up questions do NOT delay answer display**
- [ ] Follow-up questions appear within 5s after answer completes
- [ ] Loading skeleton shown while generating
- [ ] Redis cache reduces latency by >80% for similar contexts
- [ ] Pre-warming eliminates cold start delays
- [ ] **All 9 E2E tests pass (100% → 11%)**

#### Testing

**Unit Tests:**
- `test_followup_generator_async` - Async generation
- `test_followup_caching` - Redis cache hit/miss
- `test_followup_parsing` - LLM response parsing

**Integration Tests:**
- `test_followup_sse_flow` - Full SSE event flow
- `test_followup_cache_expiry` - TTL behavior

**E2E Tests:**
- Re-run all 9 follow-up E2E tests (should all pass)

---

### Feature 65.2: Domain Training UI Fixes (10 SP) 🔴 CRITICAL

**Priority:** P0 - Admin workflow completely blocked
**Current Status:** 16/40 tests passing (40% success rate)
**Agent:** Frontend Agent + Backend Agent (Parallel Execution)

#### Problem Analysis

**E2E Test Failures:**
```
❌ Domain Auto-Discovery UI (10/10 tests timeout)
   - should render drag-drop upload area (30s timeout)
   - should accept TXT, MD, DOCX, HTML file types (30s timeout)
   - should show suggestion after analysis completes (30s timeout)

❌ Domain Training API (validation failures)
   - should return 400 for empty file list (returns 422)
   - should reject files >10MB (validation mismatch)
   - should include error detail message (missing)

❌ Domain Wizard (navigation timeouts)
   - should validate domain name with regex (30s timeout)
   - should navigate to dataset upload step (30s timeout)
   - should complete full domain creation workflow (30s timeout)
```

**Root Causes:**
1. **UI Page Load:** Admin domain training page takes >30s to render (Vite chunk loading?)
2. **API Validation:** FastAPI returns 422 instead of expected 400 (Pydantic vs custom validation)
3. **Test Fixtures Missing:** No sample JSONL/TXT files for testing
4. **State Management:** Wizard step persistence broken across page reloads

#### Implementation Tasks

##### Task 65.2.1: Page Load Optimization (3 SP)

**Optimize domain training page bundle size:**

```tsx
// frontend/src/pages/admin/AdminDomainTrainingPage.tsx

// BEFORE: All components imported eagerly
import { DomainWizard } from '@/components/domain/DomainWizard';
import { DomainList } from '@/components/domain/DomainList';
import { DatasetUploader } from '@/components/domain/DatasetUploader';

// AFTER: Lazy load heavy components
const DomainWizard = lazy(() => import('@/components/domain/DomainWizard'));
const DatasetUploader = lazy(() => import('@/components/domain/DatasetUploader'));

export function AdminDomainTrainingPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <div className="domain-training-page">
        <DomainList /> {/* Keep eager loaded */}

        <Suspense fallback={<WizardSkeleton />}>
          <DomainWizard />
        </Suspense>

        <Suspense fallback={<UploaderSkeleton />}>
          <DatasetUploader />
        </Suspense>
      </div>
    </Suspense>
  );
}
```

**Vite Bundle Analysis:**
```bash
# Check current bundle size
npx vite-bundle-visualizer

# Expected improvement
# AdminDomainTrainingPage: 2.5MB → 800KB (lazy loading)
# Initial page load: 15s → 3s (on production)
```

**Files:**
- `frontend/src/pages/admin/AdminDomainTrainingPage.tsx` (UPDATE - lazy loading)
- `frontend/src/components/domain/*` (UPDATE - code splitting)
- `frontend/vite.config.ts` (UPDATE - chunk size warnings)

##### Task 65.2.2: API Validation Alignment (2 SP)

**Fix validation response codes:**

```python
# src/api/v1/domain_training.py

from fastapi import HTTPException, status

@router.post("/api/v1/domain/discover")
async def discover_domain(files: List[UploadFile]):
    """Discover domain from sample files."""

    # Validation: Empty file list
    if not files:
        # BEFORE: Pydantic returns 422 Unprocessable Entity
        # AFTER: Explicit 400 Bad Request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required"  # Add detail message
        )

    # Validation: File size limit
    for file in files:
        if file.size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} exceeds 10MB limit (size: {file.size})"
            )

    # Validation: File count limit
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum 10 files allowed, got {len(files)}"
        )

    # ... rest of logic
```

**Update Pydantic models to use custom validators:**

```python
# src/api/models/domain.py

from pydantic import BaseModel, field_validator

class DomainCreateRequest(BaseModel):
    name: str
    description: str

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate domain name format."""
        if not v:
            raise ValueError("Domain name is required")
        if not v.islower():
            raise ValueError("Domain name must be lowercase")
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Domain name must contain only letters, numbers, hyphens, underscores")
        return v
```

**Files:**
- `src/api/v1/domain_training.py` (UPDATE - explicit 400 responses)
- `src/api/models/domain.py` (UPDATE - custom validators)
- `tests/e2e/admin/domain-discovery-api.spec.ts` (UPDATE - expect 400 instead of 422)

##### Task 65.2.3: Test Fixtures (2 SP)

**Create sample test data:**

```typescript
// frontend/e2e/fixtures/domain-training/

// sample-machine-learning.txt (300 words about ML)
// sample-finance.txt (300 words about finance)
// sample-healthcare.txt (300 words about healthcare)
// sample-training.jsonl (5 training samples)

// fixtures/index.ts
export const DOMAIN_TEST_FILES = {
  machineLearning: 'fixtures/domain-training/sample-machine-learning.txt',
  finance: 'fixtures/domain-training/sample-finance.txt',
  healthcare: 'fixtures/domain-training/sample-healthcare.txt',
  trainingDataset: 'fixtures/domain-training/sample-training.jsonl'
};
```

```jsonl
# frontend/e2e/fixtures/domain-training/sample-training.jsonl

{"text": "Machine learning models require training data", "entities": ["Machine learning", "training data"], "domain": "machine_learning"}
{"text": "Neural networks learn patterns from examples", "entities": ["Neural networks", "patterns"], "domain": "machine_learning"}
{"text": "Supervised learning uses labeled datasets", "entities": ["Supervised learning", "labeled datasets"], "domain": "machine_learning"}
{"text": "Deep learning is a subset of machine learning", "entities": ["Deep learning", "machine learning"], "domain": "machine_learning"}
{"text": "Convolutional neural networks process images", "entities": ["Convolutional neural networks", "images"], "domain": "machine_learning"}
```

**Files:**
- `frontend/e2e/fixtures/domain-training/*` (NEW - test fixtures)
- `frontend/e2e/admin/test_domain_training_flow.spec.ts` (UPDATE - use fixtures)

##### Task 65.2.4: Wizard State Persistence (3 SP)

**Fix wizard step navigation:**

```tsx
// frontend/src/components/domain/DomainWizard.tsx

import { useLocalStorage } from '@/hooks/useLocalStorage';

export function DomainWizard() {
  // Persist wizard state across page reloads
  const [wizardState, setWizardState] = useLocalStorage('domain-wizard-state', {
    currentStep: 1,
    domainName: '',
    description: '',
    uploadedFiles: [],
    selectedModel: ''
  });

  const handleNextStep = () => {
    setWizardState(prev => ({
      ...prev,
      currentStep: prev.currentStep + 1
    }));
  };

  const handleBackStep = () => {
    setWizardState(prev => ({
      ...prev,
      currentStep: prev.currentStep - 1
    }));
  };

  const handleReset = () => {
    setWizardState({
      currentStep: 1,
      domainName: '',
      description: '',
      uploadedFiles: [],
      selectedModel: ''
    });
  };

  return (
    <WizardContainer currentStep={wizardState.currentStep}>
      {wizardState.currentStep === 1 && (
        <Step1DomainInfo
          values={wizardState}
          onNext={handleNextStep}
        />
      )}
      {wizardState.currentStep === 2 && (
        <Step2DatasetUpload
          values={wizardState}
          onNext={handleNextStep}
          onBack={handleBackStep}
        />
      )}
      {/* ... more steps */}
    </WizardContainer>
  );
}
```

**Files:**
- `frontend/src/components/domain/DomainWizard.tsx` (UPDATE - state persistence)
- `frontend/src/hooks/useLocalStorage.ts` (NEW - localStorage hook)

#### Acceptance Criteria

- [ ] Domain training page loads in <5s (currently >30s)
- [ ] API validation returns correct 400 status codes with detail messages
- [ ] Test fixtures available for all domain training E2E tests
- [ ] Wizard state persists across page reloads
- [ ] **All 40 domain training E2E tests pass (40% → 100%)**

#### Testing

**Unit Tests:**
- `test_domain_validation` - Custom validators return 400
- `test_file_size_validation` - File size limits enforced

**Integration Tests:**
- `test_domain_creation_flow` - Full wizard flow
- `test_wizard_state_persistence` - LocalStorage persistence

**E2E Tests:**
- Re-run all 40 domain training E2E tests

---

### Feature 65.3: History/Conversation Loading Optimization (8 SP) 🔴 CRITICAL

**Priority:** P0 - User experience severely degraded
**Current Status:** 4/8 tests passing (50% success rate)
**Agent:** Backend Agent (Parallel Execution)

#### Problem Analysis

**E2E Test Failures:**
```
❌ should list conversations in chronological order (30s timeout)
❌ should open conversation on click and restore messages (30s timeout)
❌ should search conversations by title and content (30s timeout)
❌ should auto-generate conversation title from first message (timeout)
✅ should delete conversation with confirmation dialog (7.5s)
✅ should display conversation metadata (5.9s)
```

**Root Causes:**
1. **No Pagination:** Loads ALL conversations at once (>100 conversations = timeout)
2. **N+1 Queries:** Each conversation triggers separate message count query
3. **No Caching:** Repeated requests fetch same data from database
4. **Full Message History:** Restoring conversation loads entire history (>100 messages)

#### Implementation Tasks

##### Task 65.3.1: Pagination Implementation (3 SP)

**Add cursor-based pagination:**

```python
# src/api/v1/history.py

from typing import Optional
from datetime import datetime

@router.get("/api/v1/history/conversations")
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = None,  # ISO timestamp of last conversation
    search: Optional[str] = None
) -> ConversationListResponse:
    """
    List conversations with pagination.

    Pagination:
    - limit: Max conversations per page (default: 20)
    - cursor: Timestamp of last conversation from previous page
    - Returns next_cursor for fetching next page
    """
    # Build query
    query = """
    MATCH (c:Conversation)
    WHERE c.created_at < $cursor
    ORDER BY c.created_at DESC
    LIMIT $limit
    """

    # Add search filter
    if search:
        query = query.replace(
            "WHERE c.created_at",
            "WHERE (c.title CONTAINS $search OR c.summary CONTAINS $search) AND c.created_at"
        )

    # Execute with single query (no N+1)
    result = await neo4j.run(f"""
    {query}
    OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
    RETURN c, count(m) as message_count
    """, {
        "cursor": cursor or datetime.now().isoformat(),
        "limit": limit,
        "search": search
    })

    conversations = []
    for record in result:
        conversations.append({
            "id": record["c"]["id"],
            "title": record["c"]["title"],
            "created_at": record["c"]["created_at"],
            "message_count": record["message_count"],  # Pre-counted!
            "summary": record["c"]["summary"]
        })

    # Determine next cursor
    next_cursor = conversations[-1]["created_at"] if conversations else None

    return ConversationListResponse(
        conversations=conversations,
        next_cursor=next_cursor,
        has_more=len(conversations) == limit
    )
```

**Frontend infinite scroll:**

```tsx
// frontend/src/pages/HistoryPage.tsx

import InfiniteScroll from 'react-infinite-scroll-component';

export function HistoryPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const loadMore = async () => {
    const response = await fetch(`/api/v1/history/conversations?limit=20&cursor=${cursor || ''}`);
    const data = await response.json();

    setConversations(prev => [...prev, ...data.conversations]);
    setCursor(data.next_cursor);
    setHasMore(data.has_more);
  };

  return (
    <InfiniteScroll
      dataLength={conversations.length}
      next={loadMore}
      hasMore={hasMore}
      loader={<ConversationSkeleton />}
    >
      {conversations.map(conv => (
        <ConversationCard key={conv.id} conversation={conv} />
      ))}
    </InfiniteScroll>
  );
}
```

**Files:**
- `src/api/v1/history.py` (UPDATE - pagination)
- `frontend/src/pages/HistoryPage.tsx` (UPDATE - infinite scroll)
- `frontend/package.json` (ADD - react-infinite-scroll-component)

##### Task 65.3.2: Redis Caching (2 SP)

**Cache conversation list:**

```python
# src/api/v1/history.py

from src.core.redis_memory import get_redis_client

@router.get("/api/v1/history/conversations")
async def list_conversations(...):
    """List conversations with Redis caching."""

    # Cache key includes pagination params
    cache_key = f"history:list:{cursor}:{limit}:{search or 'all'}"

    # Check cache first
    redis = get_redis_client()
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch from database (as above)
    result = await fetch_conversations_from_db(...)

    # Cache for 5 minutes
    await redis.setex(cache_key, 300, json.dumps(result))

    return result
```

**Cache invalidation:**

```python
# src/api/v1/chat.py

@router.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with cache invalidation."""

    # ... handle chat ...

    # Invalidate conversation list cache when new message added
    if request.conversation_id:
        redis = get_redis_client()
        # Delete all cached pages for this user
        await redis.delete_pattern("history:list:*")
```

**Files:**
- `src/api/v1/history.py` (UPDATE - Redis caching)
- `src/api/v1/chat.py` (UPDATE - cache invalidation)

##### Task 65.3.3: Lazy Message Loading (3 SP)

**Load messages on demand:**

```python
# src/api/v1/history.py

@router.get("/api/v1/history/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    message_limit: int = Query(50, ge=1, le=200),
    message_cursor: Optional[str] = None
) -> ConversationDetailResponse:
    """
    Get conversation details with paginated messages.

    Only loads recent messages (50) by default.
    Use message_cursor to load older messages.
    """
    # Fetch conversation metadata (fast)
    conversation = await neo4j.run("""
    MATCH (c:Conversation {id: $id})
    RETURN c
    """, {"id": conversation_id})

    # Fetch recent messages only (paginated)
    messages = await neo4j.run("""
    MATCH (c:Conversation {id: $id})-[:HAS_MESSAGE]->(m:Message)
    WHERE m.created_at < $cursor
    ORDER BY m.created_at DESC
    LIMIT $limit
    RETURN m
    """, {
        "id": conversation_id,
        "cursor": message_cursor or datetime.now().isoformat(),
        "limit": message_limit
    })

    return ConversationDetailResponse(
        conversation=conversation,
        messages=[parse_message(m) for m in messages],
        next_message_cursor=messages[-1]["created_at"] if messages else None,
        has_more_messages=len(messages) == message_limit
    )
```

**Frontend lazy loading:**

```tsx
// frontend/src/components/chat/ConversationMessages.tsx

export function ConversationMessages({ conversationId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageCursor, setMessageCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  // Load initial 50 messages
  useEffect(() => {
    loadMessages();
  }, [conversationId]);

  const loadMessages = async () => {
    const response = await fetch(
      `/api/v1/history/conversations/${conversationId}?message_limit=50&message_cursor=${messageCursor || ''}`
    );
    const data = await response.json();

    setMessages(prev => [...data.messages, ...prev]); // Prepend older messages
    setMessageCursor(data.next_message_cursor);
    setHasMore(data.has_more_messages);
  };

  return (
    <div className="messages">
      {hasMore && (
        <button onClick={loadMessages}>Load Older Messages</button>
      )}
      {messages.map(msg => (
        <MessageCard key={msg.id} message={msg} />
      ))}
    </div>
  );
}
```

**Files:**
- `src/api/v1/history.py` (UPDATE - lazy message loading)
- `frontend/src/components/chat/ConversationMessages.tsx` (UPDATE - paginated messages)

#### Acceptance Criteria

- [ ] Conversation list loads in <2s (currently >30s)
- [ ] Pagination: 20 conversations per page (infinite scroll)
- [ ] Search results return in <1s (indexed + cached)
- [ ] Opening conversation loads <5s (lazy message loading)
- [ ] Redis cache reduces DB queries by >80%
- [ ] **All 8 history E2E tests pass (50% → 100%)**

#### Testing

**Unit Tests:**
- `test_pagination` - Cursor-based pagination logic
- `test_cache_hit_miss` - Redis caching behavior
- `test_lazy_message_loading` - Message pagination

**Integration Tests:**
- `test_conversation_list_pagination` - Full pagination flow
- `test_cache_invalidation` - Cache cleared on new message

**E2E Tests:**
- Re-run all 8 history E2E tests

---

### Feature 65.4: Graph Filter State Management (5 SP) 🟡 MEDIUM

**Priority:** P1 - Feature partially broken
**Current Status:** ~16/35 tests passing (45% success rate)
**Agent:** Frontend Agent (Parallel Execution)

#### Problem Analysis

**E2E Test Failures:**
```
❌ should toggle RELATES_TO filter on and off (timeout)
❌ should toggle MENTIONED_IN filter on and off (timeout)
❌ should adjust weight threshold slider (timeout)
❌ should update graph when toggling both filters (timeout)
❌ should display graph legend with edge types (timeout)
❌ should display graph statistics (timeout)
❌ should reset all filters to default state (timeout)
❌ should maintain filter state when navigating within page (timeout)
```

**Root Causes:**
1. **Filter State Not Updating:** Checkbox/slider changes don't trigger graph re-render
2. **Debouncing Missing:** Slider triggers too many updates (performance)
3. **State Persistence Broken:** Filters reset on page navigation
4. **No Loading Indicators:** Graph appears frozen during filter updates

#### Implementation Tasks

##### Task 65.4.1: Filter State Refactoring (2 SP)

**Centralize filter state management:**

```tsx
// frontend/src/hooks/useGraphFilters.ts (NEW)

import { useState, useCallback } from 'react';
import { debounce } from 'lodash';

export interface GraphFilters {
  relatesTo: boolean;
  mentionedIn: boolean;
  weightThreshold: number;
}

export function useGraphFilters(initialFilters?: Partial<GraphFilters>) {
  const [filters, setFilters] = useState<GraphFilters>({
    relatesTo: true,
    mentionedIn: true,
    weightThreshold: 0.5,
    ...initialFilters
  });

  const [isUpdating, setIsUpdating] = useState(false);

  // Debounced filter update (500ms)
  const updateFilters = useCallback(
    debounce((newFilters: Partial<GraphFilters>) => {
      setFilters(prev => ({ ...prev, ...newFilters }));
      setIsUpdating(false);
    }, 500),
    []
  );

  const setFilter = (key: keyof GraphFilters, value: boolean | number) => {
    setIsUpdating(true);
    updateFilters({ [key]: value });
  };

  const resetFilters = () => {
    setFilters({
      relatesTo: true,
      mentionedIn: true,
      weightThreshold: 0.5
    });
  };

  return {
    filters,
    setFilter,
    resetFilters,
    isUpdating
  };
}
```

**Update graph component:**

```tsx
// frontend/src/components/graph/GraphVisualization.tsx

export function GraphVisualization() {
  const { filters, setFilter, resetFilters, isUpdating } = useGraphFilters();
  const { data: graphData, isLoading } = useGraphData(filters);

  return (
    <div className="graph-container">
      {/* Filter Controls */}
      <GraphFilterPanel
        filters={filters}
        onFilterChange={setFilter}
        onReset={resetFilters}
        disabled={isUpdating}
      />

      {/* Loading Overlay */}
      {(isLoading || isUpdating) && (
        <div className="graph-loading-overlay">
          <Spinner /> Updating graph...
        </div>
      )}

      {/* Graph Display */}
      <GraphCanvas data={graphData} />

      {/* Legend & Stats */}
      <GraphLegend data={graphData} />
      <GraphStatistics data={graphData} filters={filters} />
    </div>
  );
}
```

**Files:**
- `frontend/src/hooks/useGraphFilters.ts` (NEW - centralized state)
- `frontend/src/components/graph/GraphVisualization.tsx` (UPDATE - use hook)
- `frontend/package.json` (ADD - lodash for debouncing)

##### Task 65.4.2: Filter Persistence (2 SP)

**Persist filter state in URL query params:**

```tsx
// frontend/src/hooks/useGraphFilters.ts (UPDATE)

import { useSearchParams } from 'react-router-dom';

export function useGraphFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize from URL query params
  const initialFilters: GraphFilters = {
    relatesTo: searchParams.get('relatesTo') !== 'false',
    mentionedIn: searchParams.get('mentionedIn') !== 'false',
    weightThreshold: parseFloat(searchParams.get('weightThreshold') || '0.5')
  };

  const [filters, setFilters] = useState<GraphFilters>(initialFilters);

  // Sync filters to URL
  useEffect(() => {
    setSearchParams({
      relatesTo: filters.relatesTo.toString(),
      mentionedIn: filters.mentionedIn.toString(),
      weightThreshold: filters.weightThreshold.toString()
    });
  }, [filters]);

  // ... rest of hook
}
```

**URL Examples:**
```
/admin/graph?relatesTo=true&mentionedIn=false&weightThreshold=0.7
```

**Files:**
- `frontend/src/hooks/useGraphFilters.ts` (UPDATE - URL persistence)

##### Task 65.4.3: Add Explicit Wait Conditions (1 SP)

**Update E2E tests with proper waits:**

```typescript
// frontend/e2e/graph/edge-filters.spec.ts (UPDATE)

test('should toggle RELATES_TO filter on and off', async ({ page }) => {
  await page.goto('/admin/graph');

  // Wait for initial graph load
  await page.waitForSelector('[data-testid="graph-canvas"]');
  await page.waitForSelector('[data-testid="graph-loaded"]'); // NEW: Explicit load indicator

  // Toggle filter
  const relatesTo = page.locator('[data-testid="filter-relates-to"]');
  await relatesTo.click();

  // Wait for graph to update (not just timeout!)
  await page.waitForSelector('[data-testid="graph-updating"]'); // Loading overlay
  await page.waitForSelector('[data-testid="graph-loaded"]');   // Finished loading

  // Verify filter applied
  const edgeCount = await page.locator('[data-testid="edge-count"]').textContent();
  expect(parseInt(edgeCount)).toBeLessThan(initialEdgeCount);
});
```

**Add test attributes to components:**

```tsx
// frontend/src/components/graph/GraphVisualization.tsx

<div
  data-testid={isLoading || isUpdating ? "graph-updating" : "graph-loaded"}
  className="graph-container"
>
  {/* ... */}
</div>
```

**Files:**
- `frontend/e2e/graph/edge-filters.spec.ts` (UPDATE - explicit waits)
- `frontend/src/components/graph/GraphVisualization.tsx` (ADD - test attributes)

#### Acceptance Criteria

- [ ] Filter changes update graph within 500ms (debounced)
- [ ] Loading overlay shows during filter updates
- [ ] Filter state persists across page navigation (URL params)
- [ ] Reset button restores default filter state
- [ ] **All 35 graph filter E2E tests pass (45% → 100%)**

#### Testing

**Unit Tests:**
- `test_filter_debouncing` - 500ms debounce works
- `test_url_persistence` - Filters sync to/from URL

**E2E Tests:**
- Re-run all 35 graph visualization E2E tests

---

### Feature 65.5: Research Mode Performance (5 SP) 🟡 MEDIUM

**Priority:** P1 - Advanced feature slow
**Current Status:** ~5/10 tests passing (50% success rate)
**Agent:** Backend Agent (Parallel Execution)

#### Problem Analysis

**E2E Test Failures:**
```
❌ should show all research phases in order (timeout)
❌ should display synthesis results (timeout)
❌ should show research sources with quality metrics (timeout)
❌ should include web search results in research (timeout)
❌ should display research timeline/progression (timeout)
```

**Root Causes:**
1. **Long LLM Operations:** Multi-turn research takes >60s (exceeds 30s test timeout)
2. **Sequential Execution:** Research phases run sequentially (not parallelized)
3. **No Progress Streaming:** User sees nothing for 30-60s (appears frozen)
4. **Web Search Blocking:** External API calls add latency

#### Implementation Tasks

##### Task 65.5.1: Streaming Research Progress (2 SP)

**Emit progress events during research:**

```python
# src/agents/research_agent.py

async def research(self, query: str) -> AsyncGenerator[dict, None]:
    """
    Multi-phase research with progress streaming.

    Phases:
    1. Query decomposition (5s)
    2. Document search (10s)
    3. Web search (15s)
    4. Synthesis (20s)

    Total: ~50s
    """
    # Phase 1: Query decomposition
    yield {"type": "research_phase", "phase": "decomposition", "progress": 0.1}
    subqueries = await self.decompose_query(query)
    yield {"type": "research_phase", "phase": "decomposition", "progress": 0.2, "data": subqueries}

    # Phase 2: Document search (parallel)
    yield {"type": "research_phase", "phase": "document_search", "progress": 0.2}
    doc_results = await asyncio.gather(*[
        self.search_documents(sq) for sq in subqueries
    ])
    yield {"type": "research_phase", "phase": "document_search", "progress": 0.5, "data": doc_results}

    # Phase 3: Web search (parallel, optional)
    if self.config.enable_web_search:
        yield {"type": "research_phase", "phase": "web_search", "progress": 0.5}
        web_results = await asyncio.gather(*[
            self.search_web(sq) for sq in subqueries
        ])
        yield {"type": "research_phase", "phase": "web_search", "progress": 0.7, "data": web_results}

    # Phase 4: Synthesis
    yield {"type": "research_phase", "phase": "synthesis", "progress": 0.7}
    synthesis = await self.synthesize(query, doc_results, web_results)
    yield {"type": "research_phase", "phase": "synthesis", "progress": 1.0, "data": synthesis}

    # Final result
    yield {"type": "research_complete", "data": synthesis}
```

**Frontend progress display:**

```tsx
// frontend/src/components/chat/ResearchProgress.tsx

export function ResearchProgress() {
  const [phase, setPhase] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);

  useEffect(() => {
    const eventSource = useStreamChat();

    eventSource.addEventListener('research_phase', (event) => {
      const data = JSON.parse(event.data);
      setPhase(data.phase);
      setProgress(data.progress);
    });
  }, []);

  return (
    <div className="research-progress">
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      <div className="phase-indicator">
        <Check className={phase === 'decomposition' ? 'complete' : 'pending'} />
        Query Decomposition
      </div>
      <div className="phase-indicator">
        <Check className={phase === 'document_search' ? 'complete' : 'pending'} />
        Document Search
      </div>
      <div className="phase-indicator">
        <Check className={phase === 'web_search' ? 'complete' : 'pending'} />
        Web Search
      </div>
      <div className="phase-indicator">
        <Check className={phase === 'synthesis' ? 'complete' : 'pending'} />
        Synthesis
      </div>
    </div>
  );
}
```

**Files:**
- `src/agents/research_agent.py` (UPDATE - streaming progress)
- `frontend/src/components/chat/ResearchProgress.tsx` (NEW - progress UI)

##### Task 65.5.2: Optimize Research Orchestration (2 SP)

**Parallelize independent research operations:**

```python
# src/agents/research_agent.py

async def search_documents(self, subquery: str) -> List[Document]:
    """Search documents in parallel (vector + graph + web)."""

    # Parallel search across all sources
    vector_task = self.vector_search.search(subquery)
    graph_task = self.graph_search.search(subquery)
    web_task = self.web_search.search(subquery) if self.config.enable_web_search else None

    # Wait for all results
    vector_results, graph_results, web_results = await asyncio.gather(
        vector_task,
        graph_task,
        web_task or asyncio.sleep(0)  # Skip if disabled
    )

    # Merge and deduplicate
    all_results = vector_results + graph_results + (web_results or [])
    return self.deduplicate(all_results)
```

**Files:**
- `src/agents/research_agent.py` (UPDATE - parallel orchestration)

##### Task 65.5.3: Increase E2E Test Timeouts (1 SP)

**Update test timeouts for research mode:**

```typescript
// frontend/playwright.config.ts

export default defineConfig({
  // Default timeout
  timeout: 30 * 1000,

  // Shared expect timeout
  expect: {
    timeout: 10 * 1000,
  },

  // Per-test timeout overrides
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      // Research mode tests need longer timeout
      grep: /research-mode\.spec\.ts/,
      timeout: 90 * 1000,  // 90s for research tests
    },
  ],
});
```

**Alternative: Per-test timeout:**

```typescript
// frontend/e2e/research-mode.spec.ts

test('should show all research phases in order', async ({ chatPage }) => {
  test.setTimeout(90000); // 90s timeout for this specific test

  await chatPage.sendMessage('Research the history of machine learning');

  // Wait for all phases to complete
  await chatPage.page.waitForSelector('[data-testid="research-complete"]', {
    timeout: 60000
  });

  // Verify phases appeared in order
  const phases = await chatPage.page.locator('[data-testid="research-phase"]').allTextContents();
  expect(phases).toEqual([
    'Query Decomposition',
    'Document Search',
    'Web Search',
    'Synthesis'
  ]);
});
```

**Files:**
- `frontend/playwright.config.ts` (UPDATE - research mode timeout)
- `frontend/e2e/research-mode.spec.ts` (UPDATE - per-test timeouts)

#### Acceptance Criteria

- [ ] Research completes within 60s (down from >90s)
- [ ] Progress streaming shows phase transitions in real-time
- [ ] Parallel search reduces latency by >30%
- [ ] E2E tests have appropriate 90s timeouts
- [ ] **All 10 research mode E2E tests pass (50% → 100%)**

#### Testing

**Unit Tests:**
- `test_parallel_search` - Concurrent search operations
- `test_progress_streaming` - SSE phase events

**E2E Tests:**
- Re-run all 10 research mode E2E tests (with 90s timeout)

---

### Feature 65.6: Test Infrastructure Improvements (4 SP) 🟢 LOW

**Priority:** P2 - Quality of life
**Agent:** Testing Agent (Final Phase)

#### Problem Analysis

**General Test Issues:**
- **Aggressive Timeouts:** 30s too short for LLM operations
- **Missing Fixtures:** No sample data for domain training tests
- **No Smoke Tests:** Need quick validation subset (<5 min)
- **Slow CI/CD:** Full E2E suite takes 2+ hours

#### Implementation Tasks

##### Task 65.6.1: Configurable Test Timeouts (1 SP)

**Per-test-category timeouts:**

```typescript
// frontend/playwright.config.ts

export default defineConfig({
  // Default timeout for fast tests
  timeout: 30 * 1000,

  // Test-specific timeout configuration
  projects: [
    {
      name: 'fast',
      testMatch: /.*\/(chat|citations|error-handling|admin)\.spec\.ts/,
      timeout: 30 * 1000,
    },
    {
      name: 'slow-llm',
      testMatch: /.*\/(followup|research-mode|multi-turn)\.spec\.ts/,
      timeout: 90 * 1000,  // 90s for LLM-heavy tests
    },
    {
      name: 'slow-ui',
      testMatch: /.*\/domain-.*\.spec\.ts/,
      timeout: 60 * 1000,  // 60s for heavy UI tests
    },
  ],
});
```

**Files:**
- `frontend/playwright.config.ts` (UPDATE - categorized timeouts)

##### Task 65.6.2: Smoke Test Suite (2 SP)

**Create minimal test subset for quick validation:**

```typescript
// frontend/e2e/smoke.spec.ts (EXPAND)

import { test, expect } from './fixtures';

/**
 * Smoke Tests - Quick Validation Suite
 *
 * Runtime: <5 minutes
 * Coverage: Critical user journeys only
 *
 * Use for:
 * - Pre-deployment validation
 * - Quick regression checks
 * - CI/CD gating
 */

test.describe('Critical User Journeys (Smoke)', () => {
  test('should perform basic chat query', async ({ chatPage }) => {
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastResponse();
    expect(response.length).toBeGreaterThan(50);
  });

  test('should display citations', async ({ chatPage }) => {
    await chatPage.sendMessage('Explain neural networks');
    await chatPage.waitForResponse();

    const citations = await chatPage.page.locator('[data-testid="citation"]').count();
    expect(citations).toBeGreaterThan(0);
  });

  test('should load admin dashboard', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();

    const domains = await adminDashboardPage.page.locator('[data-testid="domain-card"]').count();
    expect(domains).toBeGreaterThan(0);
  });

  test('should perform vector search', async ({ chatPage }) => {
    await chatPage.sendMessage('machine learning algorithms');
    await chatPage.waitForResponse();

    const sources = await chatPage.page.locator('[data-testid="source-card"]').count();
    expect(sources).toBeGreaterThan(0);
  });

  test('should handle errors gracefully', async ({ chatPage }) => {
    // Simulate backend error
    await chatPage.page.route('**/api/v1/chat', route =>
      route.fulfill({ status: 500 })
    );

    await chatPage.sendMessage('test');

    const errorMsg = await chatPage.page.locator('[data-testid="error-message"]').textContent();
    expect(errorMsg).toContain('error');
  });
});
```

**Run smoke tests:**
```bash
# Quick validation (<5 min)
npx playwright test smoke.spec.ts

# Full suite (2+ hours)
npx playwright test
```

**Files:**
- `frontend/e2e/smoke.spec.ts` (EXPAND - 10-15 critical tests)
- `package.json` (ADD - script: `"test:smoke": "playwright test smoke.spec.ts"`)

##### Task 65.6.3: Test Fixtures Documentation (1 SP)

**Document test fixture usage:**

```markdown
# frontend/e2e/fixtures/README.md (NEW)

# E2E Test Fixtures

Test fixtures provide reusable test data and utilities.

## Domain Training Fixtures

Located in `e2e/fixtures/domain-training/`:

- `sample-machine-learning.txt` - 300 words about ML
- `sample-finance.txt` - 300 words about finance
- `sample-healthcare.txt` - 300 words about healthcare
- `sample-training.jsonl` - 5 training samples

**Usage:**
```typescript
import { DOMAIN_TEST_FILES } from './fixtures';

test('should upload training file', async ({ page }) => {
  await page.setInputFiles(
    '[data-testid="file-upload"]',
    DOMAIN_TEST_FILES.trainingDataset
  );
});
```

## Page Object Models (POM)

Located in `e2e/pom/`:

- `ChatPage.ts` - Chat interface interactions
- `AdminDashboardPage.ts` - Admin dashboard
- `AdminDomainTrainingPage.ts` - Domain training UI

**Usage:**
```typescript
test('chat test', async ({ chatPage }) => {
  await chatPage.sendMessage('Hello');
  await chatPage.waitForResponse();
});
```

## Authentication Fixtures

All tests use mocked authentication via `setupAuthMocking()`:

```typescript
const TEST_TOKEN = {
  access_token: 'test-jwt-token-for-e2e-tests',
  token_type: 'bearer',
  expires_in: 3600,
};
```

No real authentication required for E2E tests.
```

**Files:**
- `frontend/e2e/fixtures/README.md` (NEW - fixture documentation)

#### Acceptance Criteria

- [ ] Test timeouts configured by category (30s/60s/90s)
- [ ] Smoke test suite completes in <5 minutes
- [ ] Test fixture documentation complete
- [ ] CI/CD includes smoke test gate (pre-full-suite)

---

## Parallel Execution Strategy

### Wave 1: Critical Fixes (Days 1-4)
**High Priority - Blocking Production**

```
Parallel Group A (Backend Agent):
- Feature 65.1: Follow-up Questions Fix [8 SP]
- Feature 65.3: History/Conversation Loading [8 SP]
Total: 16 SP

Parallel Group B (Frontend Agent + Backend Agent):
- Feature 65.2: Domain Training UI Fixes [10 SP]
  - Frontend: Page load optimization (3 SP)
  - Backend: API validation (2 SP)
  - Frontend: Test fixtures (2 SP)
  - Frontend: Wizard state (3 SP)
Total: 10 SP

Duration: 3-4 days
```

### Wave 2: Medium Priority Fixes (Days 5-7)
**Medium Priority - Quality Improvements**

```
Parallel Group C (Frontend Agent):
- Feature 65.4: Graph Filter State Management [5 SP]

Parallel Group D (Backend Agent):
- Feature 65.5: Research Mode Performance [5 SP]

Total: 10 SP
Duration: 2-3 days
```

### Wave 3: Test Infrastructure (Days 8-10)
**Low Priority - Quality of Life**

```
Testing Agent:
- Feature 65.6: Test Infrastructure Improvements [4 SP]
  - Configurable timeouts (1 SP)
  - Smoke test suite (2 SP)
  - Fixture documentation (1 SP)

Duration: 1-2 days
```

---

## Acceptance Criteria (Sprint Level)

### Production Readiness
- [ ] **Follow-up questions:** 100% E2E test success (currently 11%)
- [ ] **Domain training:** 100% E2E test success (currently 40%)
- [ ] **History management:** 100% E2E test success (currently 50%)
- [ ] **Graph visualization:** 90%+ E2E test success (currently 45%)
- [ ] **Research mode:** 90%+ E2E test success (currently 50%)

### Performance Targets
- [ ] Follow-up generation: <5s (async, cached)
- [ ] Domain training page load: <5s (lazy loading)
- [ ] Conversation list: <2s (paginated, cached)
- [ ] Graph filter updates: <500ms (debounced)
- [ ] Research mode: <60s (streaming progress)

### Test Infrastructure
- [ ] LLM tests: 90s timeout
- [ ] UI tests: 60s timeout
- [ ] Fast tests: 30s timeout (default)
- [ ] Smoke tests: <5 min runtime
- [ ] Full E2E suite: <90 min runtime (down from 2+ hours)

### Overall E2E Success Rate
- [ ] **Target:** 90%+ tests passing (up from 57%)
- [ ] **Baseline:** 337/594 passing
- [ ] **Goal:** 535+/594 passing

---

## Dependencies

| Feature | Depends On | Blocks |
|---------|------------|--------|
| 65.1 | Redis Memory (Sprint 7), SSE Streaming (Sprint 50) | Production readiness |
| 65.2 | None | Admin workflow unblocked |
| 65.3 | Neo4j Schema, Redis (Sprint 7) | User experience |
| 65.4 | None | Graph feature completeness |
| 65.5 | Research Agent (Sprint 63) | Advanced feature usability |
| 65.6 | All above features | CI/CD efficiency |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM timeout fixes don't work | High | Pre-warming, caching, async patterns proven in other systems |
| Domain training wizard still slow | High | Lazy loading + code splitting tested locally first |
| Database pagination complex | Medium | Use proven cursor-based pattern (Slack, Twitter, etc.) |
| Graph state management refactor breaks existing | Medium | Incremental refactor with E2E tests at each step |
| Research mode still too slow | Low | Streaming progress improves perceived performance |
| Test timeout increases mask real performance issues | Medium | Monitor p95 latencies, set performance budgets |

---

## Definition of Done

- [ ] All critical E2E failures fixed (follow-up, domain training, history)
- [ ] Performance targets met (documented in acceptance criteria)
- [ ] E2E test success rate >90% (535+/594 tests)
- [ ] Unit test coverage >80% for new code
- [ ] Integration tests pass locally and in CI
- [ ] No regressions in working features (337 baseline tests still pass)
- [ ] Documentation updated (PRODUCTION_DEPLOYMENT_TEST_RESULTS.md)
- [ ] Sprint summary written
- [ ] Deployment validated on DGX Spark (http://192.168.178.10)

---

## Success Metrics

### Before Sprint 65 (Baseline)
- E2E Tests: 337/594 passing (56.7%)
- Follow-up Questions: 1/9 passing (11%)
- Domain Training: 16/40 passing (40%)
- History Management: 4/8 passing (50%)
- Graph Visualization: ~16/35 passing (45%)
- Research Mode: ~5/10 passing (50%)

### After Sprint 65 (Target)
- E2E Tests: 535+/594 passing (90%+)
- Follow-up Questions: 9/9 passing (100%)
- Domain Training: 40/40 passing (100%)
- History Management: 8/8 passing (100%)
- Graph Visualization: 32+/35 passing (90%+)
- Research Mode: 9+/10 passing (90%+)

---

## References

- [PRODUCTION_DEPLOYMENT_TEST_RESULTS.md](../../PRODUCTION_DEPLOYMENT_TEST_RESULTS.md) - E2E test failure analysis
- Sprint 52 Feature 52.3 - Async follow-up pattern (not implemented, now required)
- Sprint 63 Feature 63.8 - Research mode implementation
- docs/CONTEXT_REFRESH.md - Project context and goals

---

**Created:** 2025-12-26
**Status:** Ready for Execution
**Estimated Completion:** 2026-01-08 (10 working days)
