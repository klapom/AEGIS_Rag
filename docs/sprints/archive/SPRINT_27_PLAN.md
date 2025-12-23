# Sprint 27: Backend Stability + Frontend Enhancements

**Sprint:** 27
**Start Date:** 2025-11-18
**Duration:** 6 days
**Total Story Points:** 29 SP
**Branch:** `main` (direct commits for small features) / `feature/*` for larger features

---

## Sprint Goals

### Primary Objectives
1. **Backend Stability:** Complete monitoring, test coverage, and E2E test fixes
2. **Frontend UX:** Implement 4 critical Perplexity-inspired features
3. **Production Readiness:** Achieve 80% test coverage and 100% E2E pass rate

### Success Metrics
- ✅ All P2 monitoring TODOs resolved (TD-TODO-01, 02, 03)
- ✅ Test coverage ≥ 80% (Graph RAG, Agents, Memory)
- ✅ E2E tests: 100% pass rate (184/184)
- ✅ 4 new frontend features deployed
- ✅ Zero critical bugs (P0/P1)

---

## Feature Breakdown

### Backend Features (16 SP)

#### Feature 27.1: Monitoring Completion (5 SP)

**Priority:** P1 (Critical - Production Readiness)
**Effort:** 5 SP (1 day)
**Dependencies:** Qdrant, Neo4j, Redis running

**Description:**
Implement real health checks and graceful connection management for production deployment.

**Technical Tasks:**
1. Implement real Qdrant health checks (collection count, vector count, capacity)
2. Implement real Graphiti health checks (episode count, memory usage)
3. Add graceful startup handlers (initialize connections, load models)
4. Add graceful shutdown handlers (close connections, cleanup resources)
5. Update monitoring.py with real capacity tracking
6. Write integration tests for health endpoints

**Affected Files:**
- `src/api/health/memory_health.py` (TD-TODO-01)
- `src/components/memory/monitoring.py` (TD-TODO-02)
- `src/api/main.py` (TD-TODO-03)
- `tests/integration/test_health_endpoints.py` (new)

**Acceptance Criteria:**
- [ ] Qdrant health check returns real collection/vector counts
- [ ] Graphiti health check returns real episode/memory counts
- [ ] Memory capacity tracking shows actual usage (not 0.0)
- [ ] Startup handler initializes all connections gracefully
- [ ] Shutdown handler closes all connections without errors
- [ ] Health endpoints respond within 500ms
- [ ] Integration tests cover all health check scenarios
- [ ] No placeholder TODOs remaining in monitoring code

**API Changes:**
```python
# GET /health/memory - Now returns real data
{
  "qdrant": {
    "status": "healthy",
    "collections": 3,  # Real count
    "vectors": 15234,  # Real count
    "capacity": 0.45   # Real % (0.0-1.0)
  },
  "graphiti": {
    "status": "healthy",
    "episodes": 127,    # Real count
    "entities": 456,    # Real count
    "memory_usage_mb": 234.5  # Real usage
  }
}
```

**Tests:**
```python
# tests/integration/test_health_endpoints.py
async def test_memory_health_returns_real_data():
    # Setup: Add test data to Qdrant + Graphiti
    # Execute: GET /health/memory
    # Assert: All counts > 0, capacity between 0.0-1.0
    pass

async def test_graceful_startup():
    # Execute: Start app
    # Assert: All connections initialized, no errors in logs
    pass

async def test_graceful_shutdown():
    # Execute: Shutdown app
    # Assert: All connections closed cleanly, no warnings
    pass
```

---

#### Feature 27.2: Test Coverage to 80% (8 SP)

**Priority:** P1 (Critical - Quality Assurance)
**Effort:** 8 SP (2 days)
**Dependencies:** None

**Description:**
Increase test coverage to 80% by adding comprehensive tests for Graph RAG, Agents, and Memory components.

**Technical Tasks:**
1. Add unit tests for LightRAG wrapper (extraction, insertion, query)
2. Add unit tests for Graphiti wrapper (memory operations, consolidation)
3. Add integration tests for LangGraph agents (coordinator, vector, graph, memory)
4. Add integration tests for hybrid search (RRF, multi-mode)
5. Add tests for multi-hop query decomposition
6. Add tests for memory consolidation pipeline
7. Run coverage report and identify remaining gaps
8. Add tests for identified gaps until 80% coverage

**Target Components:**
- `src/components/graph_rag/` (currently ~60% coverage)
- `src/agents/` (currently ~50% coverage)
- `src/components/memory/` (currently ~65% coverage)
- `src/components/retrieval/` (currently ~70% coverage)

**Acceptance Criteria:**
- [ ] Overall test coverage ≥ 80%
- [ ] Graph RAG components ≥ 85% coverage
- [ ] Agent modules ≥ 80% coverage
- [ ] Memory components ≥ 80% coverage
- [ ] All critical paths covered (happy path + error cases)
- [ ] No flaky tests (3 consecutive runs pass)
- [ ] Coverage report generated (HTML + JSON)

**Test Files to Create/Expand:**
```
tests/unit/components/graph_rag/
  - test_lightrag_wrapper.py (NEW - 15 tests)
  - test_extraction_factory.py (EXPAND - +10 tests)

tests/unit/components/memory/
  - test_graphiti_wrapper.py (NEW - 12 tests)
  - test_consolidation.py (EXPAND - +8 tests)

tests/integration/agents/
  - test_coordinator_agent.py (NEW - 8 tests)
  - test_vector_search_agent.py (EXPAND - +5 tests)
  - test_graph_query_agent.py (NEW - 6 tests)
  - test_memory_agent.py (NEW - 5 tests)

tests/integration/components/
  - test_hybrid_search.py (EXPAND - +7 tests)
  - test_multi_hop_query.py (NEW - 6 tests)
```

**Example Test Cases:**

```python
# tests/unit/components/graph_rag/test_lightrag_wrapper.py

@pytest.mark.asyncio
async def test_lightrag_insert_document():
    """Test document insertion into LightRAG."""
    wrapper = LightRAGWrapper()
    doc = Document(content="Test content", metadata={"source": "test.pdf"})

    result = await wrapper.insert(doc)

    assert result.success is True
    assert result.entities_extracted > 0
    assert result.relationships_extracted > 0

@pytest.mark.asyncio
async def test_lightrag_query_with_mode():
    """Test LightRAG query with different modes."""
    wrapper = LightRAGWrapper()

    # Test local mode
    result_local = await wrapper.query("test query", mode="local")
    assert result_local is not None

    # Test global mode
    result_global = await wrapper.query("test query", mode="global")
    assert result_global is not None

    # Test hybrid mode
    result_hybrid = await wrapper.query("test query", mode="hybrid")
    assert result_hybrid is not None

@pytest.mark.asyncio
async def test_lightrag_extraction_failure_handling():
    """Test LightRAG handles extraction failures gracefully."""
    wrapper = LightRAGWrapper()

    # Mock LLM failure
    with patch('src.components.graph_rag.lightrag_wrapper.aegis_llm_proxy') as mock_llm:
        mock_llm.generate.side_effect = Exception("LLM failed")

        result = await wrapper.insert(Document(content="Test"))

        # Should handle error gracefully
        assert result.success is False
        assert "error" in result.message.lower()
```

---

#### Feature 27.3: Fix SSE E2E Tests (3 SP)

**Priority:** P2 (Medium - Quality Assurance)
**Effort:** 3 SP (0.5 day)
**Dependencies:** None

**Description:**
Fix remaining 10 E2E test failures (9 SSEStreaming + 1 StreamingDuplicateFix) by refactoring SSE mocks.

**Root Cause Analysis:**
- SSEStreaming tests fail due to ReadableStream mock issues
- StreamingDuplicateFix test fails due to AbortController error handling
- Current mocks don't properly simulate SSE chunked responses

**Technical Tasks:**
1. Refactor SSE mock to use proper ReadableStream implementation
2. Fix AbortController cleanup in StreamingAnswer component
3. Update test expectations for SSE event format
4. Add retry logic for flaky SSE tests
5. Verify no regressions in existing 174 passing tests

**Affected Files:**
- `frontend/tests/e2e/SSEStreaming.test.tsx` (9 failing tests)
- `frontend/tests/e2e/StreamingDuplicateFix.test.tsx` (1 failing test)
- `frontend/tests/mocks/sse.ts` (refactor mock implementation)
- `frontend/src/components/chat/StreamingAnswer.tsx` (AbortController fix)

**Acceptance Criteria:**
- [ ] All SSEStreaming tests passing (18/18)
- [ ] StreamingDuplicateFix test passing (2/2)
- [ ] Overall E2E tests: 184/184 (100%)
- [ ] No flaky tests (3 consecutive runs pass)
- [ ] SSE mock properly simulates chunked responses
- [ ] AbortController cleanup prevents duplicates

**Test Fix Strategy:**

```typescript
// frontend/tests/mocks/sse.ts - BEFORE (BROKEN)
export const mockSSE = {
  addEventListener: vi.fn(),
  close: vi.fn()
};

// frontend/tests/mocks/sse.ts - AFTER (FIXED)
export class MockEventSource {
  private listeners: Map<string, Function[]> = new Map();

  addEventListener(event: string, handler: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(handler);
  }

  simulateMessage(data: string) {
    const handlers = this.listeners.get('message') || [];
    handlers.forEach(handler => handler({ data }));
  }

  simulateError(error: Error) {
    const handlers = this.listeners.get('error') || [];
    handlers.forEach(handler => handler({ error }));
  }

  close() {
    this.listeners.clear();
  }
}

// Usage in tests
test('should handle SSE streaming', async () => {
  const mockSource = new MockEventSource();

  render(<StreamingAnswer sessionId="test" />);

  // Simulate SSE chunks
  await act(async () => {
    mockSource.simulateMessage('data: {"token": "Hello"}');
    mockSource.simulateMessage('data: {"token": " World"}');
    mockSource.simulateMessage('data: [DONE]');
  });

  expect(screen.getByText('Hello World')).toBeInTheDocument();
});
```

---

### Frontend Features (13 SP)

#### Feature 27.10: Source Citations [1][2][3] (4 SP)

**Priority:** P1 (High - Trust & Transparency)
**Effort:** 4 SP (1 day)
**Dependencies:** Backend generation agent

**Description:**
Add inline source citations in answer text like Perplexity ([1], [2], [3]) for trust and transparency.

**Technical Tasks:**

**Backend:**
1. Modify generation prompt to include source IDs
2. Update generation agent to return citation map
3. Add citation_map field to ChatResponse model
4. Update SSE streaming to include citation data

**Frontend:**
5. Create AnswerWithCitations component
6. Parse [1], [2], [3] markers and render as clickable buttons
7. Handle citation click (scroll to source OR open modal)
8. Add hover tooltip showing source preview
9. Update StreamingAnswer to use AnswerWithCitations

**Affected Files:**
- `src/agents/generation_agent.py` (citation logic)
- `src/core/models.py` (add citation_map field)
- `frontend/src/components/chat/AnswerWithCitations.tsx` (NEW)
- `frontend/src/components/chat/StreamingAnswer.tsx` (integration)
- `frontend/src/types/chat.ts` (update types)

**Acceptance Criteria:**
- [ ] LLM generates answers with inline [1], [2], [3] citations
- [ ] Citations rendered as clickable blue buttons
- [ ] Click citation scrolls to source card (or opens modal)
- [ ] Hover citation shows source preview tooltip
- [ ] Citation numbers match source order
- [ ] Works with SSE streaming (citations appear progressively)
- [ ] Markdown rendering preserved (code blocks, lists, etc.)
- [ ] Mobile-friendly (touch targets ≥ 44px)

**Implementation:**

```python
# src/agents/generation_agent.py

async def generate_with_citations(
    query: str,
    retrieved_contexts: List[SourceDocument]
) -> tuple[str, dict[int, SourceDocument]]:
    """Generate answer with inline source citations."""
    # Build context with source IDs
    context_with_ids = ""
    citation_map = {}
    for idx, doc in enumerate(retrieved_contexts, start=1):
        context_with_ids += f"[Source {idx}]:\n{doc.content}\n\n"
        citation_map[idx] = doc

    prompt = f"""Answer the question using the provided sources.

When referencing information from a source, add an inline citation like [1], [2], [3].
Use multiple citations [1][2] when information comes from multiple sources.

Question: {query}

Sources:
{context_with_ids}

Answer (with inline citations):"""

    answer = await aegis_llm_proxy.generate(prompt)
    return answer, citation_map
```

```typescript
// frontend/src/components/chat/AnswerWithCitations.tsx

interface AnswerWithCitationsProps {
  answer: string;
  citationMap: Record<number, Source>;
  onCitationClick: (sourceIndex: number) => void;
}

export function AnswerWithCitations({
  answer,
  citationMap,
  onCitationClick
}: AnswerWithCitationsProps) {
  const renderWithCitations = (text: string) => {
    // Split by citation pattern [1], [2], etc.
    const parts = text.split(/(\[\d+\])/g);

    return parts.map((part, i) => {
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const sourceIdx = Number(match[1]);
        const source = citationMap[sourceIdx];

        return (
          <button
            key={i}
            onClick={() => onCitationClick(sourceIdx)}
            className="inline-flex items-center justify-center w-6 h-6 text-xs
                       bg-blue-500/10 hover:bg-blue-500/20 text-blue-600
                       rounded border border-blue-500/30 transition mx-0.5
                       cursor-pointer"
            title={source?.title || `Quelle ${sourceIdx}`}
          >
            {sourceIdx}
          </button>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="prose prose-lg max-w-none">
      <ReactMarkdown
        components={{
          // Inject citations into text nodes
          p: ({ node, children, ...props }) => (
            <p {...props}>{renderWithCitations(String(children))}</p>
          )
        }}
      >
        {answer}
      </ReactMarkdown>
    </div>
  );
}
```

**Tests:**
```typescript
// frontend/tests/components/AnswerWithCitations.test.tsx

test('renders inline citations as clickable buttons', () => {
  const citationMap = {
    1: { title: 'Source 1', url: 'http://example.com/1' },
    2: { title: 'Source 2', url: 'http://example.com/2' }
  };

  render(
    <AnswerWithCitations
      answer="This is a fact [1] and another fact [2]."
      citationMap={citationMap}
      onCitationClick={vi.fn()}
    />
  );

  expect(screen.getByText('1')).toBeInTheDocument();
  expect(screen.getByText('2')).toBeInTheDocument();
});

test('handles citation click', async () => {
  const handleClick = vi.fn();
  const citationMap = { 1: { title: 'Source 1' } };

  render(
    <AnswerWithCitations
      answer="Fact [1]."
      citationMap={citationMap}
      onCitationClick={handleClick}
    />
  );

  await userEvent.click(screen.getByText('1'));
  expect(handleClick).toHaveBeenCalledWith(1);
});
```

---

#### Feature 27.5: Follow-up Questions (5 SP)

**Priority:** P1 (High - User Engagement)
**Effort:** 5 SP (1 day)
**Dependencies:** Backend LLM proxy

**Description:**
Display 3-5 follow-up question suggestions after each answer to guide users to deeper insights.

**Technical Tasks:**

**Backend:**
1. Create follow-up question generation function (uses LLM)
2. Add GET endpoint `/sessions/{session_id}/followup-questions`
3. Generate questions based on last Q&A + sources
4. Cache questions in Redis (5min TTL)

**Frontend:**
5. Create FollowUpQuestions component
6. Fetch questions after answer completes
7. Display as clickable cards below answer
8. Handle question click (populate input + auto-submit)
9. Add loading skeleton for question generation

**Affected Files:**
- `src/agents/coordinator.py` (generation logic)
- `src/api/v1/chat.py` (new endpoint)
- `frontend/src/components/chat/FollowUpQuestions.tsx` (NEW)
- `frontend/src/pages/SearchPage.tsx` (integration)

**Acceptance Criteria:**
- [ ] 3-5 follow-up questions generated for each answer
- [ ] Questions appear within 2s after answer completes
- [ ] Questions are relevant and insightful
- [ ] Click question auto-submits new query
- [ ] Loading skeleton shown during generation
- [ ] Questions cached (avoid regenerating on refresh)
- [ ] Handles LLM errors gracefully (no crash)

**Implementation:**

```python
# src/agents/coordinator.py

async def generate_followup_questions(
    query: str,
    answer: str,
    sources: List[SourceDocument]
) -> List[str]:
    """Generate 3-5 follow-up questions based on Q&A."""
    prompt = f"""Based on this Q&A, suggest 3-5 insightful follow-up questions:

Q: {query}
A: {answer[:500]}...

Generate questions that:
1. Explore related topics mentioned in the answer
2. Request clarification on complex points
3. Go deeper into specific details
4. Connect to broader context

Output as JSON array: ["question1", "question2", "question3"]
"""

    response = await aegis_llm_proxy.generate(
        prompt=prompt,
        model="llama3.2:3b",  # Fast model for question generation
        temperature=0.7  # Some creativity
    )

    try:
        questions = json.loads(response)
        return questions[:5]  # Max 5
    except json.JSONDecodeError:
        logger.warning("Failed to parse follow-up questions, using fallback")
        return []
```

```typescript
// frontend/src/components/chat/FollowUpQuestions.tsx

interface FollowUpQuestionsProps {
  sessionId: string;
  onQuestionClick: (question: string) => void;
}

export function FollowUpQuestions({ sessionId, onQuestionClick }: FollowUpQuestionsProps) {
  const [questions, setQuestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        const response = await fetch(`/api/v1/chat/sessions/${sessionId}/followup-questions`);
        const data = await response.json();
        setQuestions(data.followup_questions);
      } catch (err) {
        console.error('Failed to fetch follow-up questions:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchQuestions();
  }, [sessionId]);

  if (loading) return <FollowUpSkeleton />;
  if (questions.length === 0) return null;

  return (
    <div className="mt-6 border-t border-gray-200 pt-6">
      <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
        <svg className="w-5 h-5 mr-2 text-blue-500">
          {/* Lightbulb icon */}
        </svg>
        Verwandte Fragen
      </h3>
      <div className="space-y-2">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onQuestionClick(q)}
            className="w-full text-left px-4 py-3 bg-gray-50 hover:bg-blue-50
                       border border-gray-200 hover:border-blue-300
                       rounded-lg transition-all text-sm text-gray-800
                       group"
          >
            <span className="text-blue-500 mr-2 group-hover:mr-3 transition-all">→</span>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
```

**Tests:**
```typescript
// frontend/tests/components/FollowUpQuestions.test.tsx

test('fetches and displays follow-up questions', async () => {
  const questions = ['Question 1?', 'Question 2?', 'Question 3?'];

  global.fetch = vi.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({ followup_questions: questions })
    })
  ) as any;

  render(<FollowUpQuestions sessionId="test" onQuestionClick={vi.fn()} />);

  await waitFor(() => {
    expect(screen.getByText('Question 1?')).toBeInTheDocument();
    expect(screen.getByText('Question 2?')).toBeInTheDocument();
  });
});

test('handles question click', async () => {
  const handleClick = vi.fn();

  global.fetch = vi.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({ followup_questions: ['Q1?'] })
    })
  ) as any;

  render(<FollowUpQuestions sessionId="test" onQuestionClick={handleClick} />);

  await waitFor(() => screen.getByText('Q1?'));

  await userEvent.click(screen.getByText('Q1?'));
  expect(handleClick).toHaveBeenCalledWith('Q1?');
});
```

---

#### Feature 27.6: Copy Answer to Clipboard (2 SP)

**Priority:** P2 (Medium - Convenience)
**Effort:** 2 SP (0.5 day)
**Dependencies:** None

**Description:**
Add a "Copy" button to each answer for easy clipboard export.

**Technical Tasks:**
1. Create CopyButton component with clipboard API
2. Add visual feedback (checkmark icon, 2s)
3. Handle clipboard permissions
4. Add to StreamingAnswer toolbar
5. Support both markdown and plain text copy

**Affected Files:**
- `frontend/src/components/chat/CopyButton.tsx` (NEW)
- `frontend/src/components/chat/StreamingAnswer.tsx` (integrate button)

**Acceptance Criteria:**
- [ ] Copy button visible next to each answer
- [ ] Click copies answer to clipboard
- [ ] Visual feedback: icon changes to checkmark for 2s
- [ ] Handles clipboard permission errors gracefully
- [ ] Works on all browsers (fallback for old browsers)
- [ ] Copies markdown format (preserves formatting)

**Implementation:**

```typescript
// frontend/src/components/chat/CopyButton.tsx

interface CopyButtonProps {
  text: string;
  format?: 'markdown' | 'plain';
}

export function CopyButton({ text, format = 'markdown' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      const textToCopy = format === 'plain'
        ? text.replace(/[#*_`[\]]/g, '')  // Strip markdown
        : text;

      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      // Fallback for browsers without Clipboard API
      fallbackCopy(textToCopy);
    }
  };

  const fallbackCopy = (text: string) => {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100
                 transition-colors flex items-center space-x-1"
      title={copied ? 'Kopiert!' : 'Antwort kopieren'}
    >
      {copied ? (
        <>
          <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-sm text-green-600">Kopiert!</span>
        </>
      ) : (
        <>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <span className="text-sm">Kopieren</span>
        </>
      )}
    </button>
  );
}
```

**Integration in StreamingAnswer:**

```typescript
// frontend/src/components/chat/StreamingAnswer.tsx

// Add toolbar below answer
<div className="flex items-center justify-between border-t border-gray-200 pt-4 mt-4">
  <div className="flex items-center space-x-2">
    <CopyButton text={answer} format="markdown" />
    {/* Future buttons: Regenerate, Share */}
  </div>
  <div className="text-xs text-gray-500">
    {wordCount} Wörter · {estimatedReadTime} Min Lesezeit
  </div>
</div>
```

**Tests:**
```typescript
// frontend/tests/components/CopyButton.test.tsx

test('copies text to clipboard', async () => {
  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn(() => Promise.resolve())
    }
  });

  render(<CopyButton text="Test content" />);

  await userEvent.click(screen.getByTitle('Antwort kopieren'));

  expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Test content');
  expect(screen.getByText('Kopiert!')).toBeInTheDocument();
});

test('shows visual feedback for 2 seconds', async () => {
  vi.useFakeTimers();

  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn(() => Promise.resolve())
    }
  });

  render(<CopyButton text="Test" />);

  await userEvent.click(screen.getByTitle('Antwort kopieren'));
  expect(screen.getByText('Kopiert!')).toBeInTheDocument();

  vi.advanceTimersByTime(2000);
  expect(screen.queryByText('Kopiert!')).not.toBeInTheDocument();

  vi.useRealTimers();
});
```

---

#### Feature 27.9: Quick Actions Bar (2 SP)

**Priority:** P2 (Medium - UX)
**Effort:** 2 SP (0.5 day)
**Dependencies:** None

**Description:**
Add a quick actions bar above conversation history for common tasks (New Chat, Clear, Settings).

**Technical Tasks:**
1. Create QuickActionsBar component
2. Add "New Chat" button (Ctrl+N / Cmd+N)
3. Add "Clear History" button with confirmation
4. Add "Settings" button (placeholder for future)
5. Implement keyboard shortcuts
6. Add to ConversationHistory sidebar

**Affected Files:**
- `frontend/src/components/layout/QuickActionsBar.tsx` (NEW)
- `frontend/src/components/history/ConversationHistory.tsx` (integrate bar)
- `frontend/src/hooks/useKeyboardShortcuts.ts` (NEW)

**Acceptance Criteria:**
- [ ] Quick actions bar visible above conversation list
- [ ] "New Chat" button creates new session
- [ ] "Clear History" shows confirmation dialog
- [ ] Keyboard shortcuts work (Ctrl+N, Ctrl+K)
- [ ] Responsive on mobile (icons only)
- [ ] Icons clearly labeled with tooltips

**Implementation:**

```typescript
// frontend/src/components/layout/QuickActionsBar.tsx

export function QuickActionsBar({
  onNewChat,
  onClearHistory
}: {
  onNewChat: () => void;
  onClearHistory: () => void;
}) {
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const handleClearClick = () => {
    setShowClearConfirm(true);
  };

  const handleConfirmClear = async () => {
    await onClearHistory();
    setShowClearConfirm(false);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        onNewChat();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onNewChat]);

  return (
    <>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <button
          onClick={onNewChat}
          className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-white border
                     border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          title="Neue Konversation (Ctrl+N)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 4v16m8-8H4" />
          </svg>
          <span className="hidden sm:inline">Neu</span>
        </button>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleClearClick}
            className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50
                       rounded-lg transition-colors"
            title="Verlauf löschen"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>

          <button
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100
                       rounded-lg transition-colors"
            title="Einstellungen"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Clear Confirmation Modal */}
      {showClearConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm mx-4">
            <h3 className="text-lg font-semibold mb-2">Verlauf löschen?</h3>
            <p className="text-gray-600 mb-4">
              Alle Konversationen werden permanent gelöscht. Diese Aktion kann nicht rückgängig gemacht werden.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={handleConfirmClear}
                className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                Löschen
              </button>
              <button
                onClick={() => setShowClearConfirm(false)}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
              >
                Abbrechen
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
```

**Tests:**
```typescript
// frontend/tests/components/QuickActionsBar.test.tsx

test('triggers new chat on button click', async () => {
  const handleNewChat = vi.fn();
  render(<QuickActionsBar onNewChat={handleNewChat} onClearHistory={vi.fn()} />);

  await userEvent.click(screen.getByTitle(/Neue Konversation/i));
  expect(handleNewChat).toHaveBeenCalled();
});

test('shows confirmation before clearing history', async () => {
  const handleClear = vi.fn();
  render(<QuickActionsBar onNewChat={vi.fn()} onClearHistory={handleClear} />);

  await userEvent.click(screen.getByTitle(/Verlauf löschen/i));
  expect(screen.getByText('Verlauf löschen?')).toBeInTheDocument();

  await userEvent.click(screen.getByText('Löschen'));
  expect(handleClear).toHaveBeenCalled();
});

test('handles keyboard shortcut Ctrl+N', async () => {
  const handleNewChat = vi.fn();
  render(<QuickActionsBar onNewChat={handleNewChat} onClearHistory={vi.fn()} />);

  fireEvent.keyDown(window, { key: 'n', ctrlKey: true });
  expect(handleNewChat).toHaveBeenCalled();
});
```

---

## Testing Strategy

### Unit Tests
- LightRAG wrapper: 15 tests (extraction, insertion, query)
- Graphiti wrapper: 12 tests (memory ops, consolidation)
- Follow-up generation: 8 tests (prompt, parsing, caching)
- Citation parsing: 6 tests (regex, rendering)

### Integration Tests
- LangGraph agents: 24 tests (coordinator, vector, graph, memory)
- Hybrid search: 12 tests (RRF, multi-mode)
- Health endpoints: 8 tests (Qdrant, Graphiti, startup/shutdown)

### E2E Tests
- SSEStreaming: 18 tests (refactored mocks)
- StreamingDuplicateFix: 2 tests (AbortController)
- Source citations: 6 tests (click, hover, scroll)
- Follow-up questions: 4 tests (fetch, click, error)
- Copy button: 3 tests (copy, feedback, fallback)
- Quick actions: 5 tests (new chat, clear, shortcuts)

**Total New Tests:** ~123 tests

---

## Sprint Timeline

### Day 1 (2025-11-18)
- Feature 27.1: Monitoring Completion (5 SP)
  - Morning: Implement Qdrant + Graphiti health checks
  - Afternoon: Startup/shutdown handlers + tests

### Day 2 (2025-11-19)
- Feature 27.2: Test Coverage (Part 1) (4 SP)
  - Morning: LightRAG wrapper tests (15 tests)
  - Afternoon: Graphiti wrapper tests (12 tests)

### Day 3 (2025-11-20)
- Feature 27.2: Test Coverage (Part 2) (4 SP)
  - Morning: LangGraph agent tests (24 tests)
  - Afternoon: Hybrid search tests + coverage report

### Day 4 (2025-11-21)
- Feature 27.10: Source Citations (4 SP)
  - Morning: Backend citation logic + API changes
  - Afternoon: Frontend AnswerWithCitations component + tests

### Day 5 (2025-11-22)
- Feature 27.5: Follow-up Questions (5 SP)
  - Morning: Backend generation + caching
  - Afternoon: Frontend FollowUpQuestions component + integration

### Day 6 (2025-11-23)
- Feature 27.3: Fix SSE E2E Tests (3 SP)
  - Morning: Refactor SSE mocks + AbortController fix
- Feature 27.6: Copy Button (2 SP)
  - Afternoon: CopyButton component + integration
- Feature 27.9: Quick Actions (2 SP)
  - Evening: QuickActionsBar component + keyboard shortcuts

---

## Definition of Done

### Code Quality
- [ ] All TypeScript strict mode checks pass
- [ ] All MyPy strict mode checks pass
- [ ] No linting errors (Ruff, Black)
- [ ] No security vulnerabilities (Bandit)

### Testing
- [ ] All unit tests passing (>80% coverage)
- [ ] All integration tests passing
- [ ] All E2E tests passing (184/184)
- [ ] No flaky tests (3 consecutive runs pass)

### Documentation
- [ ] All new functions have docstrings
- [ ] API endpoint documentation updated
- [ ] Component prop types documented
- [ ] Sprint completion report created

### Production Readiness
- [ ] No P0/P1 bugs
- [ ] Health checks return real data
- [ ] Graceful startup/shutdown works
- [ ] All frontend features deployed to dev

---

## Risk Mitigation

### Risk 1: Test Coverage Takes Longer Than Expected
**Mitigation:** Prioritize critical paths (agents, graph RAG). Defer less critical tests to Sprint 28.

### Risk 2: SSE Mock Refactoring Breaks Existing Tests
**Mitigation:** Run full E2E suite after each mock change. Keep old mock as fallback.

### Risk 3: Follow-up Question Quality is Poor
**Mitigation:** Iterate on prompt engineering. Add user feedback mechanism for question quality.

### Risk 4: Citation Parsing Regex is Fragile
**Mitigation:** Use robust regex pattern. Add extensive unit tests for edge cases.

---

## Sprint Metrics

### Velocity Target
- **Planned:** 29 SP (6 days)
- **Expected:** ~25-30 SP (realistic with testing focus)
- **Stretch Goal:** 32 SP (add bonus features)

### Quality Metrics
- **Test Coverage:** 80%+ (up from ~65%)
- **E2E Pass Rate:** 100% (up from 94.6%)
- **Code Quality:** Zero linting/type errors

### User Impact Metrics
- **Source Citations:** Measure citation click rate
- **Follow-up Questions:** Measure CTR on follow-up questions
- **Copy Button:** Measure copy action frequency
- **Quick Actions:** Measure new chat creation rate

---

## Related Documentation

- **Sprint 26 Report:** `docs/sprints/SPRINT_26_COMPLETION_REPORT.md`
- **Frontend Proposal:** `docs/sprints/SPRINT_27_FRONTEND_FEATURES_PROPOSAL.md`
- **Tech Debt Status:** `docs/TECH_DEBT.md`
- **Refactoring Roadmap:** `docs/refactoring/REFACTORING_ROADMAP.md`

---

**Created:** 2025-11-18
**Author:** Claude Code
**Sprint Lead:** Klaus Pommer
**Status:** ✅ READY TO START
