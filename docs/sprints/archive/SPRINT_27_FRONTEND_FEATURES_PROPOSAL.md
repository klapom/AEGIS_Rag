# Sprint 27: Perplexity-Inspired Frontend Features

**Erstellt:** 2025-11-15
**Basis:** Perplexity.ai UI Analysis + Current Frontend Gap Analysis
**Sprint 26 Status:** TypeScript build passing, 94.6% E2E pass rate

---

## Executive Summary

Sprint 26 hat die **Frontend Production Readiness** erreicht. Sprint 27 sollte **User Experience Enhancements** fokussieren, inspiriert von Perplexity.ai's bester UX.

### Current Features ✅ (Sprint 15-26)

**Already Implemented:**
- ✅ Perplexity-inspired layout (large centered search)
- ✅ Mode selector chips (Hybrid, Vector, Graph, Memory)
- ✅ Token-by-token SSE streaming
- ✅ Source cards (horizontal scroll, modal detail view)
- ✅ Markdown rendering (react-markdown)
- ✅ Conversation history sidebar
- ✅ Auto-generated conversation titles
- ✅ Inline title editing (Sprint 26)
- ✅ Session management (create, delete)
- ✅ Keyboard shortcuts (Enter, Shift+Enter)

### Missing Features ❌ (Perplexity Gap Analysis)

**High Impact, Low Effort (Sprint 27 Candidates):**
1. ❌ Follow-up Question Suggestions (Related Questions)
2. ❌ Copy Answer to Clipboard
3. ❌ Regenerate Answer
4. ❌ Share Conversation (Link generation)
5. ❌ Quick Actions (Clear, New Chat)
6. ❌ Source Citation in Text (inline [1], [2], [3])

**Medium Impact, Medium Effort:**
7. ❌ Dark Mode / Theme Toggle
8. ❌ Export Conversation (Markdown, PDF)
9. ❌ Keyboard Shortcuts Panel (help overlay)
10. ❌ Search History / Recent Queries

**High Impact, High Effort (Sprint 28+):**
11. ❌ Collections / Library (organize conversations)
12. ❌ Focus Mode / Deep Dive (multi-step research)
13. ❌ Voice Input (Speech-to-Text)
14. ❌ Image Upload (VLM integration)
15. ❌ Collaborative Sharing (real-time)

---

## Sprint 27 Recommended Features (20 SP)

### Feature 27.5: Follow-up Question Suggestions ⭐ (5 SP)

**Priority:** P1 (High - User Engagement)
**Effort:** 5 SP (1 day)
**Perplexity Inspiration:** Related Questions section

**Description:**
Display 3-5 follow-up question suggestions after each answer to guide users to deeper insights.

**Backend Implementation:**

```python
# src/agents/coordinator.py

async def generate_followup_questions(
    query: str,
    answer: str,
    sources: List[SourceDocument]
) -> List[str]:
    """Generate 3-5 follow-up questions based on answer and sources.

    Uses LLM to suggest natural follow-up questions.
    """
    prompt = f"""Based on this Q&A, suggest 3-5 insightful follow-up questions:

Q: {query}
A: {answer[:500]}...

Generate questions that:
1. Explore related topics
2. Request clarification
3. Go deeper into specifics
4. Connect to broader context

Output as JSON array: ["question1", "question2", ...]
"""

    response = await aegis_llm_proxy.generate(prompt)
    questions = json.loads(response)
    return questions[:5]  # Max 5
```

**API Endpoint:**

```python
# src/api/v1/chat.py

@router.get("/sessions/{session_id}/followup-questions")
async def get_followup_questions(session_id: str) -> dict[str, list[str]]:
    """Get follow-up question suggestions for last answer."""
    # Get last Q&A from session
    conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")
    last_qa = conversation["messages"][-2:]  # Last user + assistant

    questions = await generate_followup_questions(
        query=last_qa[0]["content"],
        answer=last_qa[1]["content"],
        sources=last_qa[1].get("sources", [])
    )

    return {"followup_questions": questions}
```

**Frontend Component:**

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
      <h3 className="text-sm font-medium text-gray-700 mb-3">
        Verwandte Fragen
      </h3>
      <div className="space-y-2">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onQuestionClick(q)}
            className="w-full text-left px-4 py-3 bg-gray-50 hover:bg-gray-100
                       border border-gray-200 rounded-lg transition-colors
                       text-sm text-gray-800"
          >
            <span className="text-primary mr-2">→</span>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
```

**UX Flow:**
1. User asks question → Answer streams
2. After streaming complete, fetch follow-up questions (async)
3. Display 3-5 related questions below answer
4. Click question → Populate search input → Auto-submit

**Tests:**
- Unit tests for follow-up generation logic
- E2E tests for question click flow
- Mock LLM responses for consistent testing

**Success Metrics:**
- CTR (Click-Through Rate) on follow-up questions
- Session depth increase (avg questions per session)

---

### Feature 27.6: Copy Answer to Clipboard ⭐ (2 SP)

**Priority:** P2 (Medium - Convenience)
**Effort:** 2 SP (0.5 day)
**Perplexity Inspiration:** Copy button on answers

**Description:**
Add a "Copy" button to each answer for easy clipboard export.

**Implementation:**

```typescript
// frontend/src/components/chat/StreamingAnswer.tsx

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
      title={copied ? 'Kopiert!' : 'Antwort kopieren'}
    >
      {copied ? (
        <svg className="w-5 h-5 text-green-600">
          {/* Checkmark icon */}
        </svg>
      ) : (
        <svg className="w-5 h-5">
          {/* Copy icon */}
        </svg>
      )}
    </button>
  );
}

// Add to StreamingAnswer toolbar
<div className="flex items-center justify-between border-t border-gray-200 pt-4 mt-4">
  <CopyButton text={answer} />
  <RegenerateButton onClick={handleRegenerate} />
  <ShareButton sessionId={currentSessionId} />
</div>
```

**Features:**
- Copy answer to clipboard
- Visual feedback (checkmark icon, 2s)
- Fallback for browsers without Clipboard API
- Copy markdown or plain text (user preference)

---

### Feature 27.7: Regenerate Answer ⭐ (3 SP)

**Priority:** P2 (Medium - Quality Control)
**Effort:** 3 SP (0.5 day)
**Perplexity Inspiration:** Regenerate button

**Description:**
Allow users to regenerate the last answer with different parameters or context.

**Backend:**
```python
# src/api/v1/chat.py

@router.post("/sessions/{session_id}/regenerate")
async def regenerate_last_answer(
    session_id: str,
    request: RegenerateRequest
) -> StreamingResponse:
    """Regenerate last answer with optional parameter changes."""
    # Get last user query from session
    conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")
    last_query = conversation["messages"][-2]["content"]  # Last user message

    # Remove last assistant response
    conversation["messages"] = conversation["messages"][:-1]
    await redis_memory.store(key=session_id, value=conversation, namespace="conversation")

    # Re-run query with new parameters
    return await chat_stream(ChatRequest(
        query=last_query,
        session_id=session_id,
        intent=request.mode or conversation.get("mode", "hybrid")
    ))
```

**Frontend:**
```typescript
function RegenerateButton({ onClick }: { onClick: () => void }) {
  const [loading, setLoading] = useState(false);

  const handleRegenerate = async () => {
    setLoading(true);
    try {
      await onClick();
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleRegenerate}
      disabled={loading}
      className="flex items-center space-x-2 px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200
                 rounded-lg transition disabled:opacity-50"
    >
      {loading ? (
        <LoadingSpinner />
      ) : (
        <svg className="w-4 h-4">
          {/* Refresh icon */}
        </svg>
      )}
      <span>Neu generieren</span>
    </button>
  );
}
```

**Use Cases:**
- Answer quality not satisfactory → Regenerate
- Want different retrieval mode → Change mode + Regenerate
- System error during streaming → Retry

---

### Feature 27.8: Share Conversation (Link Generation) ⭐ (4 SP)

**Priority:** P2 (Medium - Collaboration)
**Effort:** 4 SP (1 day)
**Perplexity Inspiration:** Share button with public link

**Description:**
Generate shareable links for conversations (read-only access).

**Backend:**

```python
# src/api/v1/chat.py

class ShareSettings(BaseModel):
    expiry_hours: int = Field(default=24, ge=1, le=168)  # 1h to 7d
    allow_fork: bool = Field(default=True)  # Allow viewers to fork conversation

@router.post("/sessions/{session_id}/share")
async def create_share_link(
    session_id: str,
    settings: ShareSettings
) -> dict[str, str]:
    """Generate public share link for conversation."""
    # Create share token
    share_token = secrets.token_urlsafe(16)
    expiry = datetime.utcnow() + timedelta(hours=settings.expiry_hours)

    # Store share metadata in Redis
    await redis_memory.store(
        key=f"share:{share_token}",
        value={
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expiry.isoformat(),
            "allow_fork": settings.allow_fork
        },
        ttl_seconds=settings.expiry_hours * 3600,
        namespace="shares"
    )

    share_url = f"{settings.BASE_URL}/share/{share_token}"
    return {"share_url": share_url, "expires_at": expiry.isoformat()}

@router.get("/share/{share_token}")
async def get_shared_conversation(share_token: str) -> ConversationHistoryResponse:
    """Get shared conversation (read-only)."""
    share_data = await redis_memory.retrieve(key=f"share:{share_token}", namespace="shares")

    if not share_data:
        raise HTTPException(status_code=404, detail="Share link expired or not found")

    return await get_conversation_history(share_data["session_id"])
```

**Frontend:**

```typescript
// Share Modal Component
function ShareModal({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [expiryHours, setExpiryHours] = useState(24);

  const handleGenerateLink = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expiry_hours: expiryHours })
      });
      const data = await response.json();
      setShareUrl(data.share_url);
    } catch (err) {
      console.error('Failed to generate share link:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (shareUrl) {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Modal onClose={onClose}>
      <h2 className="text-xl font-semibold mb-4">Konversation teilen</h2>

      {!shareUrl ? (
        <>
          <p className="text-gray-600 mb-4">
            Erstellen Sie einen öffentlichen Link für diese Konversation.
          </p>

          <label className="block mb-4">
            <span className="text-sm text-gray-700">Link-Gültigkeit:</span>
            <select
              value={expiryHours}
              onChange={(e) => setExpiryHours(Number(e.target.value))}
              className="mt-1 block w-full rounded-lg border-gray-300"
            >
              <option value={1}>1 Stunde</option>
              <option value={24}>24 Stunden</option>
              <option value={72}>3 Tage</option>
              <option value={168}>7 Tage</option>
            </select>
          </label>

          <button
            onClick={handleGenerateLink}
            disabled={loading}
            className="w-full py-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
          >
            {loading ? 'Generiere Link...' : 'Link erstellen'}
          </button>
        </>
      ) : (
        <>
          <p className="text-sm text-gray-600 mb-2">Ihr Share-Link:</p>
          <div className="flex items-center space-x-2 mb-4">
            <input
              type="text"
              value={shareUrl}
              readOnly
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
            />
            <button
              onClick={handleCopy}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
            >
              {copied ? 'Kopiert!' : 'Kopieren'}
            </button>
          </div>
          <p className="text-xs text-gray-500">
            Link verfällt in {expiryHours} Stunden
          </p>
        </>
      )}
    </Modal>
  );
}
```

**Features:**
- Expiry settings (1h, 24h, 3d, 7d)
- Read-only access (no editing)
- Optional: Allow forking (viewers can create own copy)
- QR code for mobile sharing

---

### Feature 27.9: Quick Actions Bar ⭐ (2 SP)

**Priority:** P2 (Medium - UX)
**Effort:** 2 SP (0.5 day)
**Perplexity Inspiration:** Quick action buttons

**Description:**
Add a quick actions bar above conversation history for common tasks.

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
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
      <button
        onClick={onNewChat}
        className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-white border border-gray-300
                   rounded-lg hover:bg-gray-50 transition"
        title="Neue Konversation (Ctrl+N)"
      >
        <svg className="w-4 h-4">
          {/* Plus icon */}
        </svg>
        <span>Neu</span>
      </button>

      <div className="flex items-center space-x-2">
        <button
          onClick={onClearHistory}
          className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg"
          title="Verlauf löschen"
        >
          <svg className="w-4 h-4">
            {/* Trash icon */}
          </svg>
        </button>

        <button
          className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          title="Einstellungen"
        >
          <svg className="w-4 h-4">
            {/* Settings icon */}
          </svg>
        </button>
      </div>
    </div>
  );
}
```

**Keyboard Shortcuts:**
- `Ctrl+N` / `Cmd+N`: New chat
- `Ctrl+K` / `Cmd+K`: Clear input
- `Ctrl+/` / `Cmd+/`: Show keyboard shortcuts help

---

### Feature 27.10: Source Citation in Text ⭐⭐ (4 SP)

**Priority:** P1 (High - Trust & Transparency)
**Effort:** 4 SP (1 day)
**Perplexity Inspiration:** Inline [1], [2], [3] citations

**Description:**
Add inline source citations in the answer text like Perplexity ([1], [2], [3]).

**Backend Enhancement:**

```python
# src/agents/generation_agent.py

async def generate_with_citations(
    query: str,
    retrieved_contexts: List[SourceDocument]
) -> tuple[str, dict[int, SourceDocument]]:
    """Generate answer with inline source citations.

    Returns:
        answer: Text with inline [1], [2], [3] citations
        citation_map: {1: SourceDocument, 2: SourceDocument, ...}
    """
    # Build context with source IDs
    context_with_ids = ""
    citation_map = {}
    for idx, doc in enumerate(retrieved_contexts, start=1):
        context_with_ids += f"[Source {idx}]:\n{doc.content}\n\n"
        citation_map[idx] = doc

    prompt = f"""Answer the question using the provided sources.

When referencing information from a source, add an inline citation like [1], [2], [3].

Question: {query}

Sources:
{context_with_ids}

Answer (with inline citations):"""

    answer = await llm_proxy.generate(prompt)
    return answer, citation_map
```

**Frontend Component:**

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
  // Replace [1], [2], [3] with clickable citations
  const renderWithCitations = (text: string) => {
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
            className="inline-flex items-center justify-center w-5 h-5 text-xs
                       bg-primary/10 hover:bg-primary/20 text-primary rounded
                       border border-primary/30 transition mx-0.5"
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
          // Custom renderer for text nodes to inject citations
          text: ({ node, ...props }) => renderWithCitations(props.children as string)
        }}
      >
        {answer}
      </ReactMarkdown>
    </div>
  );
}
```

**UX Flow:**
1. Answer streams with inline [1], [2], [3] citations
2. Citations are clickable buttons
3. Click [1] → Open source #1 in modal OR scroll to source card
4. Hover citation → Show source preview tooltip

**Benefits:**
- Increased trust and transparency
- Easy fact-checking
- Better source attribution
- Perplexity-parity UX

---

## Sprint 27 Feature Summary (20 SP Frontend Enhancements)

| Feature | Priority | Effort | Impact | Perplexity Parity |
|---------|----------|--------|--------|-------------------|
| 27.5: Follow-up Questions | P1 | 5 SP | High (Engagement) | ⭐⭐⭐ |
| 27.6: Copy Answer | P2 | 2 SP | Medium (Convenience) | ⭐⭐ |
| 27.7: Regenerate Answer | P2 | 3 SP | Medium (Quality) | ⭐⭐ |
| 27.8: Share Conversation | P2 | 4 SP | Medium (Collaboration) | ⭐⭐⭐ |
| 27.9: Quick Actions Bar | P2 | 2 SP | Low (UX) | ⭐ |
| 27.10: Source Citations | P1 | 4 SP | High (Trust) | ⭐⭐⭐ |
| **TOTAL** | - | **20 SP** | - | - |

**Combined with Sprint 27 Backend Features:**
- Feature 27.1: Monitoring Completion (5 SP)
- Feature 27.2: Test Coverage to 80% (8 SP)
- Feature 27.3: Fix SSE E2E Tests (3 SP)
- Feature 27.4: Documentation Backfill (4 SP)

**Total Sprint 27:** 40 SP (8 days) - **TOO LARGE**

**Recommendation:** Split into Sprint 27 (Backend + Critical Frontend) and Sprint 28 (Remaining Frontend)

---

## Sprint 27 REVISED: Backend + Frontend Enhancements (29 SP, 6 days) ⭐

**Backend (16 SP):**
- Feature 27.1: Monitoring Completion (5 SP) - P1
- Feature 27.2: Test Coverage to 80% (8 SP) - P1
- Feature 27.3: Fix SSE E2E Tests (3 SP) - P2

**Frontend (13 SP):**
- Feature 27.10: Source Citations [1][2][3] (4 SP) - P1 (High Trust Impact)
- Feature 27.5: Follow-up Questions (5 SP) - P1 (High Engagement)
- Feature 27.6: Copy Answer to Clipboard (2 SP) - P2 (High Convenience)
- Feature 27.9: Quick Actions Bar (2 SP) - P2 (UX Polish)

**Total Sprint 27:** 29 SP (6 days)

**Rationale:**
- Source Citations: Critical for trust & transparency (Perplexity parity)
- Follow-up Questions: Drives user engagement and deeper exploration
- Copy Answer: Low effort, high convenience (2 SP only)
- Quick Actions: Low effort UX improvement (2 SP only)

**Deferred to Sprint 28:**
- Feature 27.7: Regenerate Answer (3 SP)
- Feature 27.8: Share Conversation (4 SP)
- Feature 27.4: Documentation Backfill (4 SP)

---

## Sprint 28: Collaboration Features + Documentation (11 SP, 2-3 days)

**Frontend Collaboration (7 SP):**
- Feature 27.7: Regenerate Answer (3 SP) - P2
- Feature 27.8: Share Conversation (4 SP) - P2

**Documentation (4 SP):**
- Feature 27.4: Documentation Backfill (4 SP) - P3
  - Sprint 22, 23, 24, 25, 26 ADRs
  - Architecture diagram updates
  - API documentation refresh

**Total Sprint 28:** 11 SP (2-3 days)

---

## Long-Term Roadmap (Sprint 29+)

### Sprint 29: Advanced Features (25 SP)
- Dark Mode / Theme Toggle (3 SP)
- Export Conversation (Markdown, PDF) (4 SP)
- Keyboard Shortcuts Panel (2 SP)
- Search History / Recent Queries (3 SP)
- Collections / Library (8 SP)
- Focus Mode / Deep Dive (5 SP)

### Sprint 30+: Cutting Edge
- Voice Input (Speech-to-Text) (8 SP)
- Image Upload (VLM integration) (5 SP) - **Backend already supports VLM!**
- Collaborative Sharing (real-time) (13 SP)
- Advanced Analytics Dashboard (8 SP)

---

## Conclusion

Sprint 27 kombiniert **Backend Stabilität** (Monitoring, Tests) mit **kritischen Frontend-Features** (Source Citations, Follow-up Questions, Copy, Quick Actions) für Perplexity-Parity.

Sprint 28 fokussiert dann auf **Collaboration Features** (Regenerate, Share) und **Documentation Backfill**.

**Final Sprint 27 Scope (REVISED):**
- ✅ Monitoring Completion (5 SP)
- ✅ Test Coverage to 80% (8 SP)
- ✅ Fix SSE E2E Tests (3 SP)
- ✅ Source Citations [1][2][3] (4 SP)
- ✅ Follow-up Questions (5 SP)
- ✅ Copy Answer to Clipboard (2 SP)
- ✅ Quick Actions Bar (2 SP)
- **Total: 29 SP (6 Tage)**

**Sprint 28 Scope:**
- ✅ Regenerate Answer (3 SP)
- ✅ Share Conversation (4 SP)
- ✅ Documentation Backfill (4 SP)
- **Total: 11 SP (2-3 Tage)**

---

**Erstellt:** 2025-11-15 (Original)
**Aktualisiert:** 2025-11-18 (Sprint 27 Scope Revision)
**Autor:** Claude Code
**Basis:** Perplexity.ai UI Analysis (Jan 2025 Knowledge) + Current Frontend Gap Analysis
**Status:** ✅ FINAL - READY FOR SPRINT 27 PLANNING
