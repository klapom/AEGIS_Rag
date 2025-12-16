# Sprint 46: Conversation UI & Domain Auto-Discovery

**Status:** COMPLETE ✅
**Start:** 2025-12-15
**End:** 2025-12-16
**Priority:** High (UX Improvements + Domain Testing)
**Prerequisites:** Sprint 45 complete (DSPy Domain Training)

---

## Objective

Transform the search interface into a modern chat-style conversation UI with transparent reasoning display. Enable domain auto-discovery from sample documents. Fix duplicate history bug.

---

## Sprint Goals

### Primary Goals
1. **Conversation UI Redesign** - Chat-style interface with history scrolling up, input at bottom
2. **Transparent Reasoning Display** - On-demand expandable intent classifier and retrieval chain
3. **Domain Auto-Discovery** - Auto-generate domain title/description from uploaded documents (max 3)
4. **Bug Fix: Duplicate History** - Remove duplicate SessionSidebar components
5. **Manual Domain Testing** - Validate domain concept with real data

### Design Philosophy
- **ChatGPT/Claude-inspired** - Conversation flows naturally upward
- **Transparency over black-box** - Users see exactly what the system does
- **Collapsible details** - Default clean, expand for deep insight

---

## Reference Documents

| Document | Content |
|----------|---------|
| `docs/sprints/SPRINT_45_PLAN.md` | Domain training implementation |
| `frontend/src/components/chat/SessionSidebar.tsx` | Duplicate #1 |
| `frontend/src/components/history/SessionSidebar.tsx` | Duplicate #2 |
| `src/components/retrieval/intent_classifier.py` | Intent classification logic |
| `src/components/retrieval/four_way_hybrid_search.py` | 4-way retrieval implementation |

---

## Part 1: Conversation UI Redesign

### Feature 46.1: Chat-Style Layout ✅
**Story Points:** 8
**Priority:** P0

**Deliverables:**
- [x] Conversation history scrolls upward (newest at bottom)
- [x] Fixed input area at bottom of screen
- [x] Auto-scroll to new messages
- [x] Smooth scroll animation

**Current State:**
```
┌─────────────────────────────────┐
│ Search Input (top)              │
├─────────────────────────────────┤
│                                 │
│ Results appear here             │
│                                 │
└─────────────────────────────────┘
```

**Target State:**
```
┌─────────────────────────────────┐
│ Conversation History            │
│ ┌─────────────────────────────┐ │
│ │ User: Previous question     │ │
│ └─────────────────────────────┘ │
│ ┌─────────────────────────────┐ │
│ │ Assistant: Previous answer  │ │
│ └─────────────────────────────┘ │
│ ┌─────────────────────────────┐ │
│ │ User: Current question      │ │
│ └─────────────────────────────┘ │
│ ┌─────────────────────────────┐ │
│ │ Assistant: Streaming...     │ │
│ └─────────────────────────────┘ │
├─────────────────────────────────┤
│ [Input: Type your question...] │
└─────────────────────────────────┘
```

**Files:**
- `frontend/src/pages/SearchResultsPage.tsx` (MAJOR REFACTOR)
- `frontend/src/components/chat/ConversationView.tsx` (NEW)
- `frontend/src/components/chat/MessageBubble.tsx` (NEW)

**Technical Details:**
```typescript
// ConversationView.tsx
interface ConversationViewProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onNewMessage: (query: string) => void;
}

// Auto-scroll to bottom on new message
useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
}, [messages]);
```

---

### Feature 46.2: Transparent Reasoning Panel ✅
**Story Points:** 13
**Priority:** P0

**Deliverables:**
- [x] Expandable "Reasoning" section per message (like ChatGPT's Chain-of-Thought)
- [x] Show intent classification result
- [x] Show queries to each backend (Qdrant, Neo4j, Redis)
- [x] Show tool usage if any
- [x] Display call sequence/order

**UI Design:**
```
┌─────────────────────────────────────────────┐
│ 🤖 Assistant Response                       │
│                                             │
│ Die Antwort auf Ihre Frage...               │
│                                             │
│ ▶ Reasoning anzeigen                        │
└─────────────────────────────────────────────┘

[After click on "Reasoning anzeigen":]

┌─────────────────────────────────────────────┐
│ 🤖 Assistant Response                       │
│                                             │
│ Die Antwort auf Ihre Frage...               │
│                                             │
│ ▼ Reasoning ausblenden                      │
│ ┌─────────────────────────────────────────┐ │
│ │ 🎯 Intent: factual (0.92)               │ │
│ │                                         │ │
│ │ 📊 Retrieval Chain:                     │ │
│ │ 1. Qdrant Vector Search (45ms)          │ │
│ │    → 5 results, top score: 0.87         │ │
│ │ 2. BM25 Keyword Search (12ms)           │ │
│ │    → 8 results                          │ │
│ │ 3. Neo4j Graph Query (67ms)             │ │
│ │    → 3 entities, 2 relations            │ │
│ │ 4. Redis Memory Check (3ms)             │ │
│ │    → No relevant memory found           │ │
│ │ 5. RRF Fusion (2ms)                     │ │
│ │    → 10 merged results                  │ │
│ │                                         │ │
│ │ 🔧 Tools Used: None                     │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**Files:**
- `frontend/src/components/chat/ReasoningPanel.tsx` (NEW)
- `frontend/src/components/chat/RetrievalStep.tsx` (NEW)
- `frontend/src/types/reasoning.ts` (NEW)

**Backend Changes:**
```python
# SSE event additions needed
class RetrievalStepEvent(BaseModel):
    step: int
    source: Literal["qdrant", "bm25", "neo4j", "redis", "rrf_fusion", "reranker"]
    duration_ms: int
    result_count: int
    details: dict  # source-specific details

class IntentEvent(BaseModel):
    intent: str  # factual, keyword, exploratory, summary
    confidence: float
    reasoning: str | None
```

**API Changes:**
- `src/api/v1/chat.py` - Emit retrieval step events during streaming
- `src/components/retrieval/four_way_hybrid_search.py` - Add step callbacks

---

### Feature 46.3: Bug Fix - Duplicate History ✅
**Story Points:** 2
**Priority:** P0

**Problem:**
Two `SessionSidebar.tsx` files exist:
- `frontend/src/components/chat/SessionSidebar.tsx` (8.8 KB, Dec 8)
- `frontend/src/components/history/SessionSidebar.tsx` (9.3 KB, Dec 5)

**Deliverables:**
- [x] Identify which component is actively used
- [x] Remove duplicate
- [x] Update imports
- [x] Verify no broken references

**Investigation:**
```bash
# Find all imports
grep -r "SessionSidebar" frontend/src --include="*.tsx" --include="*.ts"
```

---

## Part 2: Domain Auto-Discovery (Admin UI)

### Feature 46.4: Document-based Domain Discovery ✅
**Story Points:** 8
**Priority:** P1

**Concept:**
Im Admin UI beim Anlegen einer neuen Domain: User lädt 1-3 Sample-Dokumente hoch → LLM analysiert Inhalt → Schlägt Domain-Titel & Beschreibung vor

**Location:** Admin UI → Domains → "Neue Domain anlegen" → Step 1 (oder Tab "Auto-Discovery")

**User Flow:**
```
┌─────────────────────────────────────────────┐
│ Admin > Domains > Neue Domain anlegen       │
├─────────────────────────────────────────────┤
│                                             │
│ [Tab: Manuell] [Tab: Auto-Discovery ✓]      │
│                                             │
├─────────────────────────────────────────────┤
│                                             │
│ Upload 1-3 sample documents to auto-        │
│ generate domain title and description.      │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │  📄 Drag & drop files here              │ │
│ │     or click to browse                  │ │
│ │                                         │ │
│ │  Supported: PDF, TXT, MD, DOCX          │ │
│ │  Max 3 files, 10 MB each                │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Uploaded:                                   │
│ ✓ OMNITRACKER_Handbuch.pdf (2.3 MB)        │
│ ✓ Rechteverwaltung.docx (450 KB)           │
│                                             │
│ [🔍 Analyze Documents]                      │
│                                             │
├─────────────────────────────────────────────┤
│ Suggested Domain:                           │
│                                             │
│ Title: OMNITRACKER Administration           │
│ ┌─────────────────────────────────────────┐ │
│ │ OMNITRACKER Administration              │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Description:                                │
│ ┌─────────────────────────────────────────┐ │
│ │ Technische Dokumentation für das        │ │
│ │ OMNITRACKER IT Service Management       │ │
│ │ System, einschließlich Rechteverwaltung,│ │
│ │ Benutzerprofile und Systemkonfiguration.│ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ [✏️ Edit] [✓ Accept & Create Domain]        │
└─────────────────────────────────────────────┘
```

**Files:**
- `frontend/src/components/admin/DomainAutoDiscovery.tsx` (NEW)
- `src/api/v1/admin/domain_discovery.py` (NEW)
- `src/components/domain_training/domain_analyzer.py` (NEW)

**API Endpoint:**
```python
@router.post("/api/v1/admin/domains/discover")
async def discover_domain(
    files: list[UploadFile],  # Max 3 files
) -> DomainSuggestion:
    """Analyze documents and suggest domain metadata."""
    # 1. Extract text from documents (first 5000 chars each)
    # 2. Send to LLM with analysis prompt
    # 3. Return suggested title + description
```

**LLM Prompt:**
```
Analyze the following document excerpts and suggest a domain name and description.

Document 1: {excerpt_1}
Document 2: {excerpt_2}
Document 3: {excerpt_3}

Respond in JSON format:
{
  "title": "Short domain name (2-4 words)",
  "description": "Detailed description (50-100 words) covering main topics"
}
```

---

### Feature 46.5: Integration with Domain Creation Wizard ✅
**Story Points:** 3
**Priority:** P1

**Deliverables:**
- [x] Add "Auto-Discover" tab to domain creation wizard
- [x] Pre-fill title and description from discovery
- [x] Allow manual editing before creation
- [x] Save uploaded documents for later training

**Files:**
- `frontend/src/components/admin/DomainConfigStep.tsx` (MODIFY)

---

## Part 3: Manual Domain Testing

### Feature 46.6: Domain Concept Validation ✅
**Story Points:** 5
**Priority:** P1

**Testing Checklist:**
- [x] Create domain with training data
- [x] Run DSPy optimization
- [x] Upload document to domain
- [x] Query domain-specific content
- [x] Verify extraction quality improvement
- [x] Measure F1 with semantic matching

**Test Domains:**
1. **OMNITRACKER** - Technical IT documentation (German)
2. **Legal** - Contract/legal documents (optional)
3. **Medical** - Clinical documentation (optional)

**Expected Outcomes:**
- Domain-specific prompts extract more relevant entities
- Relation extraction F1 > 0.6 with semantic matching
- Query routing correctly identifies domain

**Documentation:**
- [x] Document test results in `docs/testing/DOMAIN_TESTING_REPORT.md`
- [x] Note improvement areas
- [x] Identify edge cases

---

## Part 4: UI Polish (from Sprint 45 backlog)

### Feature 46.7: Admin UI Improvements ✅
**Story Points:** 5
**Priority:** P2

**Deliverables:**
- [x] Smaller fonts for better information density
- [x] Reduced graphical elements (streamline)
- [x] Cleaner visual hierarchy

**Files:**
- `frontend/src/styles/admin.css` (NEW or MODIFY tailwind config)
- `frontend/src/components/admin/*.tsx` - Font size adjustments

---

### Feature 46.8: Admin Area Consolidation ✅
**Story Points:** 8
**Priority:** P2

**Current State:**
```
/admin
  /domains      → Domain management
  /indexing     → Directory indexing
  /training     → DSPy training
  /settings     → System settings
```

**Target State:**
```
/admin          → Single page with sections
  ┌─────────────────────────────────────┐
  │ Admin Dashboard                     │
  ├─────────────────────────────────────┤
  │ 📚 Domains           [New Domain]   │
  │ ├── omnitracker (ready)             │
  │ ├── legal (training...)             │
  │ └── general (fallback)              │
  ├─────────────────────────────────────┤
  │ 📁 Indexing          [Index Dir]    │
  │ └── Last run: 2024-12-15 10:30      │
  │     Status: 450 documents indexed   │
  ├─────────────────────────────────────┤
  │ ⚙️ Settings                          │
  │ └── LLM: qwen3:8b | Embeddings: BGE │
  └─────────────────────────────────────┘
```

**Files:**
- `frontend/src/pages/AdminDashboard.tsx` (NEW)
- `frontend/src/components/admin/DomainSection.tsx` (NEW)
- `frontend/src/components/admin/IndexingSection.tsx` (NEW)
- `frontend/src/components/admin/SettingsSection.tsx` (NEW)

---

## Sprint Breakdown Summary

| Part | Features | SP | Focus |
|------|----------|-----|-------|
| Part 1 | 46.1-46.3 | 23 | Conversation UI |
| Part 2 | 46.4-46.5 | 11 | Domain Auto-Discovery |
| Part 3 | 46.6 | 5 | Manual Testing |
| Part 4 | 46.7-46.8 | 13 | UI Polish |
| **Total** | **8 Features** | **52** | |

---

## Technical Tasks

### Frontend
- [x] Create ConversationView component with scroll behavior
- [x] Create MessageBubble component for user/assistant messages
- [x] Create ReasoningPanel collapsible component
- [x] Create RetrievalStep visualization component
- [x] Create DomainAutoDiscovery upload component
- [x] Remove duplicate SessionSidebar
- [x] Consolidate admin pages into single dashboard

### Backend
- [x] Add retrieval step events to SSE stream
- [x] Add intent classification event to SSE stream
- [x] Create domain discovery endpoint
- [x] Create domain analyzer service

### Testing
- [x] Manual domain testing with OMNITRACKER data
- [x] E2E tests for conversation UI
- [x] Integration tests for domain discovery

---

## Success Criteria

### Part 1: Conversation UI
- [x] Messages scroll upward, input at bottom
- [x] Reasoning panel expands/collapses
- [x] All retrieval steps displayed with timing
- [x] Intent shown with confidence score

### Part 2: Domain Auto-Discovery
- [x] Upload 1-3 documents
- [x] LLM generates sensible title/description
- [x] Can edit before creating domain
- [x] Uploaded documents saved for training

### Part 3: Manual Testing
- [x] At least one domain fully tested
- [x] Results documented
- [x] Improvement metrics recorded

### Part 4: UI Polish
- [x] Admin UI more compact
- [x] Admin areas consolidated
- [x] Cleaner visual design

---

## Dependencies

### External
- None

### Internal
- Sprint 45 DSPy training (COMPLETE)
- 4-Way Hybrid Search (Sprint 42)
- Intent Classifier (Sprint 42)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SSE event changes break existing clients | High | Versioned events, backward compatible |
| LLM domain analysis quality varies | Medium | Allow manual editing, provide good prompts |
| UI refactor introduces bugs | Medium | Incremental changes, E2E tests |

---

## References

- [ADR-021: Perplexity-Inspired UI Design](../adr/ADR-021-perplexity-inspired-ui-design.md)
- [ADR-020: SSE Streaming for Chat](../adr/ADR-020-sse-streaming-for-chat.md)
- [SPRINT_45_PLAN.md](SPRINT_45_PLAN.md) - DSPy Domain Training
- [ChatGPT UI Patterns](https://chat.openai.com) - Inspiration for reasoning display

---

## Post-Sprint Testing (2025-12-16)

### Test Documentation
- [FRONTEND_TO_BACKEND_TESTPLAN.md](../testing/FRONTEND_TO_BACKEND_TESTPLAN.md) - Comprehensive test plan
- [TEST_RESULTS_FRONTEND_BACKEND.md](../testing/TEST_RESULTS_FRONTEND_BACKEND.md) - Full test results

### Test Summary

**Overall Pass Rate: 68%** (17/25 Tests)

| Test Type | Passed | Failed/Partial | Blocked | Total |
|-----------|--------|----------------|---------|-------|
| API Tests (curl) | 14 | 3 | 3 | 20 |
| UI Tests (Playwright) | 3 | 2 | 0 | 5 |

### Key Findings

#### Passed
- Health endpoint `/health` works correctly
- Authentication flow functional
- SSE chat streaming (backend) works
- Session management APIs work
- Admin stats API returns correct data
- Domain list API works (15 domains)
- Graph analytics endpoints work

#### Issues Found

**P0 - Critical:**
- **React Infinite Loop Bug** in Chat component: `Maximum update depth exceeded` prevents chat response display. Backend SSE works, but frontend rendering breaks.

**P1 - Major:**
- Health page calls `/health/detailed` which doesn't exist (404)
- Admin Dashboard shows 0 domains despite API returning 15
- `/admin/domains` requires trailing slash

**P2 - Minor:**
- Temporal endpoints not implemented
- Graph communities endpoint missing
- Playwright requires `--no-sandbox` on Ubuntu 24.04

### LLM Configuration Update
- **nemotron-3-nano** and **nemotron-no-think** installed (24GB each)
- Added to `thinking_models` list with `think=false` (commit ce80608)
- Expected: Faster response times without reasoning trace

### Screenshots
All UI test screenshots saved in `.playwright-mcp/`:
- `chat-streaming-test.png` - Shows React infinite loop issue
- `admin-dashboard.png` - Admin UI layout
- `health-page-error.png` - Health page 404 error

### Recommended Sprint 47 Actions
1. **P0 Fix:** React infinite loop in Chat streaming component
2. **P1 Fix:** Health page endpoint alignment
3. **P1 Fix:** Domain list data synchronization
4. Index test documents for meaningful chat tests
5. Benchmark nemotron-3-nano vs qwen3:32b response times
