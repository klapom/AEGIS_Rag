# Sprint 17: Admin UI & Advanced Features
**Status:** 🚧 IN PROGRESS (started 2025-10-29)
**Goal:** Admin UI for re-indexing management and advanced frontend features
**Duration:** 5-7 days (estimated)
**Completed:** 4/6 features (24 SP / 55 SP total - 44% complete)

---

## 🎯 Sprint Objectives

Based on Sprint 16 learnings and user requests:

### **Key Features Requested:**
1. ✅ **Admin UI for Directory Indexing** (User Request: 2025-10-28)
   - Interface to specify directory to index
   - Real-time indexing progress display
   - Integration with unified re-indexing pipeline (Feature 16.2)

2. 📋 **Technical Debt from Sprint 15/16**
   - TD-36: Accessibility improvements (WCAG 2.1 AA compliance)
   - TD-37: Error boundary implementation (graceful error handling)
   - Frontend E2E test improvements (if needed)

---

## 📦 Sprint Features

### Feature 17.1: Admin UI for Directory Indexing (13 SP)
**Status:** 📋 PLANNED
**Duration:** 2 days

**Problem:**
Currently no user interface to specify directories for indexing or monitor indexing progress in real-time.

**Solution:**
Create admin UI that integrates with the unified re-indexing pipeline (Feature 16.2) and provides real-time progress monitoring.

**Tasks:**
- [ ] Create Admin page component (`AdminPage.tsx`)
- [ ] Directory selection UI (input field + file browser button)
- [ ] Re-indexing control panel (confirm button, dry-run toggle)
- [ ] Real-time progress display (SSE integration)
  - Progress bar with percentage
  - Current phase display (initialization, deletion, chunking, embedding, indexing, validation)
  - Current document being processed
  - ETA calculation display
- [ ] Indexing history table (past re-indexing operations)
- [ ] System statistics dashboard
  - Total documents indexed
  - Total chunks in Qdrant
  - BM25 corpus size
  - Neo4j entity count
- [ ] Admin authentication/authorization
- [ ] Error handling and user feedback
- [ ] Responsive design

**Deliverables:**
```typescript
// frontend/src/pages/AdminPage.tsx
export function AdminPage() {
  const [inputDir, setInputDir] = useState<string>('');
  const [dryRun, setDryRun] = useState<boolean>(false);
  const [progress, setProgress] = useState<ReindexProgress | null>(null);

  // SSE connection to /api/v1/admin/reindex endpoint
  // Real-time progress updates
  // ETA calculation and display
}
```

**API Integration:**
- `POST /api/v1/admin/reindex` (SSE streaming) - from Feature 16.2
- `GET /api/v1/admin/stats` - system statistics endpoint (NEW)
- `GET /api/v1/admin/history` - indexing history (NEW)

**Benefits:**
- ✅ User can specify custom directory for indexing
- ✅ Real-time visibility into indexing progress
- ✅ Dry-run mode to preview changes
- ✅ Historical tracking of indexing operations

---

### Feature 17.2: Conversation History Fixes (8 SP)
**Status:** ✅ COMPLETED (2025-10-29)
**Commit:** `7346801` - fix(sprint-17): Fix duplicate streaming & implement conversation persistence
**Duration:** 1 day
**Priority:** HIGH (User-reported bugs)

**Problem:**
Three critical issues prevented proper conversation management:
1. **Conversations not saving**: Messages were never persisted to Redis after processing
2. **Follow-up questions don't work**: Each search created a new session instead of reusing existing session_id
3. **Empty session list**: `list_sessions()` returned hardcoded empty list

**Root Causes Identified:**
- `src/api/v1/chat.py` (Lines 273-398): `chat_stream()` never called `memory_api.store()` to save messages
- `src/api/v1/chat.py` (Lines 419-430): `list_sessions()` returned hardcoded empty list (TODO not implemented)
- `frontend/src/pages/SearchResultsPage.tsx` (Lines 20-22): `handleNewSearch()` never included `session_id` in URL
- Frontend created NEW session for every search, losing conversation context

**Solution Implemented:**
Fixed backend persistence and frontend session management.

**Tasks:**
- [x] **Backend: Add conversation persistence**
  - Added `save_conversation_turn()` helper function
  - Added persistence call after streaming completes in `chat_stream()`
  - Added persistence call in `chat()` endpoint
  - Stores both user question and assistant answer
  - Saves to Redis with key pattern: `conversation:{session_id}`, 7-day TTL
- [x] **Backend: Implement session listing**
  - Replaced TODO in `list_sessions()` with actual Redis SCAN
  - Queries Redis keys matching `conversation:*` pattern
  - Extracts session metadata (last_activity, created_at, message_count)
  - Returns populated SessionListResponse, sorted by last_activity
- [x] **Frontend: Preserve session_id across searches**
  - Modified `handleNewSearch()` to include current `session_id` in URL
  - Added state management to track activeSessionId
  - Passes session_id to StreamingAnswer component
  - Follow-up questions now reuse same session
- [x] **Frontend: Session ID callback**
  - Added `onSessionIdReceived` callback to StreamingAnswer
  - Captures session_id from metadata for new conversations
- [x] **Backend: Implement get_conversation_history**
  - Retrieves conversation from Redis by session_id
  - Returns 404 if session not found
  - Extracts messages and metadata
- [ ] Add integration tests for conversation persistence (TODO)
- [ ] Add E2E test for follow-up questions (TODO)

**Deliverables:**
```python
# Backend: src/api/v1/chat.py (add after streaming completes)
async def save_conversation(session_id: str, user_message: str, assistant_message: str):
    memory_api = get_unified_memory_api()
    await memory_api.store(
        key=f"conversation:{session_id}",
        value={
            "messages": [...],
            "updated_at": datetime.now(),
            "message_count": len(messages)
        },
        namespace="conversations"
    )

# Backend: Implement list_sessions()
async def list_sessions() -> SessionListResponse:
    redis_client = await get_redis_manager()
    keys = await redis_client.scan_match("conversation:*")
    sessions = []
    for key in keys:
        session_data = await redis_client.get(key)
        sessions.append(SessionInfo(...))
    return SessionListResponse(sessions=sessions, total_count=len(sessions))
```

```typescript
// Frontend: src/pages/SearchResultsPage.tsx
const handleNewSearch = (newQuery: string, newMode: SearchMode) => {
    const params = new URLSearchParams({
        q: newQuery,
        mode: newMode,
        session_id: sessionId || ""  // FIX: Preserve session_id!
    });
    navigate(`/search?${params.toString()}`);
};
```

**Benefits:**
- ✅ Conversations persist across browser refreshes
- ✅ Session sidebar shows actual conversation history
- ✅ Follow-up questions maintain conversation context
- ✅ Users can continue conversations from history
- ✅ Multi-turn conversations work as expected

---

### Feature 17.3: Auto-Generated Conversation Titles (5 SP)
**Status:** ✅ COMPLETED (2025-10-29)
**Commit:** `e30a5e2` - feat(sprint-17): Feature 17.3 - Auto-generated conversation titles with inline editing
**Duration:** 0.5 day
**Priority:** MEDIUM (User-requested feature)

**Problem:**
Conversations in sidebar show generic IDs or timestamps instead of meaningful titles. Users cannot quickly identify conversations.

**User Request:**
> "eine Konversation sollte auch nach der ersten Antwort eine kurze präzise Zusammenfassung als Titel erhalten, mit der Möglichkeit durch den Benutzer den Namen zu ändern"

**Solution:**
Auto-generate concise conversation title after first answer using LLM, with user edit capability.

**Tasks:**
- [x] **Backend: Title generation endpoint**
  - Added `POST /api/v1/chat/sessions/{session_id}/generate-title` endpoint
  - Uses Ollama LLM to generate 3-5 word title from first Q&A exchange
  - Prompt: "Generate a very concise 3-5 word title for this conversation..."
  - Stores title in Redis conversation metadata with timestamp
- [x] **Backend: Title update endpoint**
  - Added `PATCH /api/v1/chat/sessions/{session_id}` endpoint
  - Allows user to update conversation title
  - Validates title length (1-100 chars)
  - Updates Redis with new title and timestamp
- [x] **Frontend: Auto-trigger title generation**
  - Auto-triggers after first answer completes (answer length > 50 chars)
  - Calls generate-title endpoint when streaming ends
  - Updates session in sidebar via onTitleGenerated callback
  - Silently fails if generation fails (non-critical)
- [x] **Frontend: Editable titles**
  - Added inline edit functionality to SessionItem component
  - Click to edit → Input field with auto-focus/select
  - Save on blur or Enter key, cancel on Escape
  - Calls PATCH endpoint on save with loading spinner
  - Hover effect indicates editability
  - Optimistic UI update
- [x] Extended SessionInfo model with optional title field
- [x] Updated list_sessions() to include title in response
- [ ] Add tests for title generation and editing (deferred to E2E test phase)

**Deliverables:**
```python
# Backend: src/api/v1/chat.py
@router.post("/sessions/{session_id}/generate-title")
async def generate_conversation_title(session_id: str) -> TitleResponse:
    """Auto-generate concise conversation title from first Q&A."""
    # Get first message pair
    conversation = await memory_api.get(f"conversation:{session_id}")
    first_qa = conversation["messages"][:2]

    # Generate title with LLM
    prompt = f"Generate a concise 3-5 word title: Q: {first_qa[0]} A: {first_qa[1]}"
    title = await ollama_client.generate(prompt, max_tokens=20)

    # Save title
    conversation["title"] = title
    await memory_api.store(f"conversation:{session_id}", conversation)

    return TitleResponse(title=title)

@router.patch("/sessions/{session_id}")
async def update_conversation_title(session_id: str, request: UpdateTitleRequest):
    """Allow user to manually edit conversation title."""
    conversation = await memory_api.get(f"conversation:{session_id}")
    conversation["title"] = request.title
    await memory_api.store(f"conversation:{session_id}", conversation)
    return {"status": "updated"}
```

```typescript
// Frontend: src/components/sidebar/SessionItem.tsx
export function SessionItem({ session }: { session: SessionInfo }) {
    const [isEditing, setIsEditing] = useState(false);
    const [title, setTitle] = useState(session.title);

    const handleSave = async () => {
        await updateSessionTitle(session.id, title);
        setIsEditing(false);
    };

    return isEditing ? (
        <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={handleSave}
        />
    ) : (
        <div onClick={() => setIsEditing(true)}>{title}</div>
    );
}
```

**Benefits:**
- ✅ Users can quickly identify conversations in sidebar
- ✅ Automatic title generation saves user time
- ✅ User can customize titles for better organization
- ✅ Improved conversation management UX

---

### Feature 17.4: Implicit User Profiling & Conversation Search (21 SP)
**Status:** 📋 PLANNED
**Duration:** 3 days
**Priority:** HIGH (Strategic feature)

**Problem:**
System has no "memory" of user behavior across sessions. Cannot:
1. Search through past conversations semantically
2. Understand user's role, interests, and expertise level
3. Personalize answers based on user's history
4. Provide context-aware recommendations

**User Request:**
> "Es soll möglich sein, in vergangenen Session zu suchen. Ebenso soll das System ein 'Gefühl' oder 'Wissen' um die Person aufbauen die gerade sucht. [...] Das Wissen um die Person soll dabei aber implizit im System vorhanden sein und nicht an die Oberfläche kommen."

**Solution:**
Hybrid storage architecture with implicit user profiling:
- **Qdrant**: Semantic search over archived conversations
- **Neo4j**: User behavior knowledge graph (implicit profile)
- **Redis**: Active session state (hot cache)

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                   Conversation Lifecycle                     │
├─────────────────────────────────────────────────────────────┤
│ Phase 1: ACTIVE (Redis)                                     │
│  └─ Real-time chat (TTL: 7 days)                           │
│  └─ Ultra-fast reads/writes (<1ms)                         │
├─────────────────────────────────────────────────────────────┤
│ Phase 2: ARCHIVED (Qdrant + Background Processing)         │
│  └─ After 7 days OR user-triggered archive                 │
│  └─ Semantic search enabled                                 │
│  └─ Extract implicit profile signals                        │
├─────────────────────────────────────────────────────────────┤
│ Phase 3: PROFILING (Neo4j Knowledge Graph)                 │
│  └─ User → INTERESTED_IN → Topic                           │
│  └─ User → ROLE → JobFunction                              │
│  └─ User → EXPERTISE_LEVEL → Domain                        │
│  └─ User → FREQUENTLY_ASKS_ABOUT → Category               │
└─────────────────────────────────────────────────────────────┘
```

**Implicit Profiling Strategy:**

The system builds a user profile WITHOUT storing personal data:

```cypher
// Example Neo4j Knowledge Graph (Implicit Profile)

// User asks many questions about scripting
(user:User {id: "user-123"})
  -[:INTERESTED_IN {strength: 0.85, signal_count: 12}]->
  (topic:Topic {name: "OMNITRACKER Scripting"})

// User's questions indicate admin-level knowledge
(user)
  -[:HAS_ROLE {confidence: 0.78, inferred_from: "query_complexity"}]->
  (role:Role {name: "System Administrator"})

// User frequently asks about advanced topics
(user)
  -[:EXPERTISE_LEVEL {level: "advanced", evidence_count: 8}]->
  (domain:Domain {name: "OMNITRACKER Administration"})

// User's conversation patterns
(user)
  -[:PREFERS_MODE {usage_ratio: 0.65}]->
  (mode:SearchMode {name: "hybrid"})

// Cross-session knowledge connections
(user)
  -[:DISCUSSED {session_count: 3, last_date: "2025-10-29"}]->
  (doc:Document {title: "Advanced Scripting Guide"})
```

**Privacy-First Design:**
- ❌ NO personal identifiable information stored
- ❌ NO conversation content in profile graph
- ✅ ONLY behavioral signals (topics, patterns, preferences)
- ✅ User can clear profile anytime
- ✅ GDPR-compliant (pseudo-anonymized user IDs)

**Tasks:**

**A. Conversation Archiving Pipeline:**
- [ ] **Background job: Archive conversations after 7 days**
  - Celery task scheduled daily
  - Move Redis → Qdrant + Neo4j
  - Preserve only metadata in Redis (title, date, archive_id)
- [ ] **Conversation embedding for semantic search**
  - Generate embedding from full conversation text
  - Store in Qdrant collection: `archived_conversations`
  - Payload: title, summary, topics, date, user_id
- [ ] **Manual archive trigger**
  - `POST /api/v1/chat/sessions/{session_id}/archive` endpoint
  - User can archive important conversations immediately

**B. Semantic Conversation Search:**
- [ ] **Search endpoint: `POST /api/v1/chat/search`**
  ```python
  {
    "query": "Was habe ich über Scripting gelernt?",
    "user_id": "user-123",  # Filter to current user only
    "limit": 10,
    "time_range": "last_30_days"  # Optional
  }
  ```
  - Semantic search in Qdrant over user's archived conversations
  - Return: Conversation snippets with relevance scores
- [ ] **Frontend: Conversation search UI**
  - Search bar in SessionSidebar
  - Display results with highlighted snippets
  - Click to load full conversation

**C. Implicit Profile Extraction:**
- [ ] **Signal extraction from conversations**
  ```python
  async def extract_profile_signals(conversation: Conversation, user_id: str):
      # 1. Topic Extraction
      topics = await llm.extract_topics(conversation)
      # → INTERESTED_IN relations

      # 2. Role Inference
      role_signals = analyze_question_complexity(conversation)
      # → HAS_ROLE relation (Admin, Developer, User)

      # 3. Expertise Level
      expertise = infer_expertise_from_questions(conversation)
      # → EXPERTISE_LEVEL (Beginner, Intermediate, Advanced)

      # 4. Search Mode Preference
      mode_usage = count_search_modes(conversation)
      # → PREFERS_MODE (hybrid, vector, graph)

      # 5. Frequently Discussed Documents
      mentioned_docs = extract_document_references(conversation)
      # → DISCUSSED relations
  ```
- [ ] **Neo4j schema for user profile graph**
  ```cypher
  // Nodes
  CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE
  CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE
  CREATE CONSTRAINT role_name IF NOT EXISTS FOR (r:Role) REQUIRE r.name IS UNIQUE

  // Indices for fast queries
  CREATE INDEX user_profile_lookup IF NOT EXISTS FOR (u:User) ON (u.id)
  ```
- [ ] **Incremental profile updates**
  - After each conversation: Update strength/confidence scores
  - Decay old signals over time (time-weighted)
  - Merge conflicting signals with confidence scoring

**D. Profile-Aware RAG (Personalization):**
- [ ] **Inject user profile into retrieval context**
  ```python
  async def retrieve_with_profile(query: str, user_id: str):
      # 1. Get user profile from Neo4j
      profile = await neo4j.get_user_profile(user_id)
      # {
      #   "interests": ["Scripting", "Administration"],
      #   "expertise": {"OMNITRACKER": "advanced"},
      #   "role": "System Administrator"
      # }

      # 2. Boost retrieval for relevant topics
      boosted_query = f"{query} (User context: {profile['role']}, interested in {profile['interests']})"

      # 3. Filter/rank results based on expertise
      results = await hybrid_search(boosted_query)
      results = adjust_for_expertise(results, profile['expertise'])

      return results
  ```
- [ ] **Answer adaptation based on profile**
  ```python
  system_prompt = f"""
  You are answering for a user with the following implicit profile:
  - Role: {profile['role']}
  - Expertise: {profile['expertise']}
  - Interests: {profile['interests']}

  Adapt your answer complexity and terminology accordingly.
  - For "Beginner": Use simple explanations, more examples
  - For "Advanced": Be concise, assume knowledge, go deeper

  DO NOT mention the user's profile explicitly in your answer.
  """
  ```

**E. Profile Management (Privacy Controls):**
- [ ] **View profile signals (optional transparency)**
  - `GET /api/v1/users/me/profile` endpoint
  - Show inferred topics, expertise, preferences
  - "Here's what the system has learned about you"
- [ ] **Clear profile**
  - `DELETE /api/v1/users/me/profile` endpoint
  - Delete all profile nodes and relations from Neo4j
  - Keep archived conversations (they're useful!)
- [ ] **Opt-out of profiling**
  - User setting: `enable_personalization: false`
  - System uses default behavior (no profile boost)

**F. Analytics & Monitoring:**
- [ ] **Profile accuracy metrics**
  - Track: Are personalized answers more helpful?
  - User feedback: Thumbs up/down on answers
  - A/B test: Profile-aware vs. default retrieval
- [ ] **Profile drift detection**
  - Alert if user profile changes significantly
  - Example: "Beginner" user suddenly asks advanced questions
  - Suggest: Re-calibrate expertise level

**Deliverables:**

```python
# Backend: src/components/profiling/profile_extractor.py

class ImplicitProfileExtractor:
    """Extract behavioral signals from conversations."""

    async def extract_topics(self, conversation: Conversation) -> List[Topic]:
        """Extract topics using LLM."""
        prompt = f"Extract 3-5 main topics from this conversation: {conversation.summary}"
        topics = await self.llm.generate(prompt)
        return [Topic(name=t, confidence=0.8) for t in topics]

    async def infer_role(self, conversation: Conversation) -> Role:
        """Infer user role from question complexity."""
        complexity_score = self._analyze_complexity(conversation)
        if complexity_score > 0.7:
            return Role(name="System Administrator", confidence=complexity_score)
        elif complexity_score > 0.4:
            return Role(name="Power User", confidence=complexity_score)
        else:
            return Role(name="End User", confidence=complexity_score)

    async def infer_expertise(self, user_id: str, domain: str) -> ExpertiseLevel:
        """Infer expertise from historical conversations."""
        conversations = await self.get_user_conversations(user_id, domain=domain)

        # Analyze question progression
        early_questions = conversations[:5]
        recent_questions = conversations[-5:]

        progression_score = self._compare_complexity(early_questions, recent_questions)

        if progression_score > 0.5:
            return ExpertiseLevel.ADVANCED
        elif progression_score > 0.2:
            return ExpertiseLevel.INTERMEDIATE
        else:
            return ExpertiseLevel.BEGINNER

# Backend: src/components/profiling/profile_aware_retrieval.py

class ProfileAwareRetrieval:
    """Personalize retrieval based on user profile."""

    async def retrieve(self, query: str, user_id: str) -> List[Document]:
        # 1. Get profile
        profile = await self.neo4j.get_profile(user_id)

        # 2. Boost query for user interests
        boosted_query = self._boost_for_interests(query, profile.interests)

        # 3. Standard hybrid retrieval
        results = await self.hybrid_search.search(boosted_query)

        # 4. Re-rank for expertise level
        results = self._rerank_for_expertise(results, profile.expertise)

        return results

    def _boost_for_interests(self, query: str, interests: List[str]) -> str:
        """Add implicit boost for user's known interests."""
        # Semantic boost (not visible to user)
        interest_context = " ".join(interests)
        return f"{query} [Context: {interest_context}]"

    def _rerank_for_expertise(self, results: List[Document], expertise: Dict[str, ExpertiseLevel]) -> List[Document]:
        """Adjust document complexity to match user expertise."""
        for doc in results:
            domain = doc.metadata.get("domain")
            user_level = expertise.get(domain, ExpertiseLevel.INTERMEDIATE)
            doc_level = doc.metadata.get("complexity", "intermediate")

            # Boost if levels match
            if doc_level == user_level.value:
                doc.score *= 1.2
            # Penalize if too complex or too simple
            elif abs(self._level_diff(doc_level, user_level)) > 1:
                doc.score *= 0.8

        return sorted(results, key=lambda x: x.score, reverse=True)
```

```typescript
// Frontend: src/components/search/ConversationSearch.tsx

export function ConversationSearch() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<ConversationSearchResult[]>([]);

    const handleSearch = async () => {
        const response = await fetch('/api/v1/chat/search', {
            method: 'POST',
            body: JSON.stringify({
                query,
                limit: 10,
                time_range: 'all'
            })
        });
        setResults(await response.json());
    };

    return (
        <div className="conversation-search">
            <input
                placeholder="Durchsuche deine früheren Konversationen..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <SearchResults results={results} />
        </div>
    );
}

// Frontend: src/components/profile/ProfileInsights.tsx (Optional)

export function ProfileInsights() {
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [showProfile, setShowProfile] = useState(false);

    useEffect(() => {
        fetch('/api/v1/users/me/profile')
            .then(r => r.json())
            .then(setProfile);
    }, []);

    if (!showProfile) return null;

    return (
        <div className="profile-insights">
            <h3>Was das System über dich gelernt hat:</h3>
            <div>
                <strong>Hauptinteressen:</strong>
                <ul>
                    {profile.interests.map(i => (
                        <li key={i.topic}>{i.topic} (Stärke: {i.strength.toFixed(2)})</li>
                    ))}
                </ul>
            </div>
            <div>
                <strong>Erkannte Rolle:</strong> {profile.role}
            </div>
            <div>
                <strong>Expertise-Level:</strong>
                {Object.entries(profile.expertise).map(([domain, level]) => (
                    <span key={domain}>{domain}: {level}</span>
                ))}
            </div>
            <button onClick={clearProfile}>Profil löschen</button>
        </div>
    );
}
```

**Benefits:**
- ✅ Semantic search through past conversations
- ✅ System "remembers" user preferences implicitly
- ✅ Personalized answer complexity (beginner vs. expert)
- ✅ Relevance boost for user's known interests
- ✅ Privacy-first: No PII stored, only behavioral signals
- ✅ User control: View and delete profile anytime
- ✅ GDPR-compliant: Pseudo-anonymized, purpose-limited

**Privacy Guarantees:**
```python
# What IS stored:
{
  "user_id": "hash(email)",  # Pseudo-anonymized
  "interests": ["Scripting", "Administration"],
  "expertise": {"OMNITRACKER": "advanced"},
  "role": "System Administrator"
}

# What is NOT stored:
❌ Conversation content (only in Qdrant embeddings)
❌ Personal information (name, email, etc.)
❌ Explicit tracking ("User clicked X")
❌ Profile exposed to user (unless they request it)
```

**Example User Experience:**

```
Session 1:
User: "Wie erstelle ich einen Benutzer?"
System: [Detaillierte Anfänger-Anleitung]
→ Profile: Beginner, interested in "User Management"

Session 5:
User: "Batch-Import von 1000 Benutzern per Script"
System: [Knappe Code-Beispiele, fortgeschrittene Optionen]
→ Profile: Intermediate→Advanced, interested in "Scripting"

Session 10:
User: "Performance-Optimierung für LDAP-Sync"
System: [Technische Details, Annahme von Vorwissen]
→ Profile: Advanced, role=Administrator
→ Retrieval boost: Zeigt zuerst Admin-Docs
```

**Implementation Phases:**

**Phase 1 (MVP - 1 day):**
- Conversation archiving (Redis → Qdrant)
- Semantic search over conversations
- Basic topic extraction

**Phase 2 (Profiling - 1.5 days):**
- Neo4j profile graph
- Implicit signal extraction
- Profile-aware retrieval boost

**Phase 3 (Privacy & UX - 0.5 days):**
- Profile management endpoints
- Privacy controls (view/delete)
- Optional transparency UI

---

### Feature 17.5: Fix Duplicate Answer Streaming (3 SP)
**Status:** ✅ COMPLETED (2025-10-29)
**Commit:** `7346801` - fix(sprint-17): Fix duplicate streaming & implement conversation persistence
**Duration:** 0.5 day
**Priority:** HIGH (User-reported bug)

**Problem:**
Streaming answers were duplicated - the same answer appeared twice in the frontend.

**User Report:**
> "Die Ausgabe nach der Frage enthält die gleiche Antwort doppelt: Basierend auf dem bereitgestellten Kontext [...] [repeated twice]"

**Root Cause Identified:**
React StrictMode intentionally double-mounts components in development, causing `useEffect` to fire twice and create TWO SSE connections for the same query.

**Evidence:**
Backend logs confirmed duplicate requests arriving within milliseconds:
```
06:18:56 session_id=34991fde-7d81-421a-a4d7-9dec4f19343a query="welche dokumente hast du geladen"
06:18:56 session_id=727d9444-8c6e-4c1f-b796-b96674e5a7c3 query="welche dokumente hast du geladen"
```
→ Same query, different session_ids, same timestamp

**Investigation Tasks:**
- [x] Checked browser network tab - Found 2 SSE connections per request
- [x] Identified React StrictMode as root cause
- [x] Confirmed useEffect lacked cleanup function to abort connections
- [x] Verified streaming logic was correct, problem was double mounting

**Solution Implemented:**
Added AbortController to cancel SSE connections on component unmount.

**Implementation:**

**Fix Applied:**

```typescript
// frontend/src/components/chat/StreamingAnswer.tsx
useEffect(() => {
    // Sprint 17 Feature 17.5: Fix duplicate streaming caused by React StrictMode
    const abortController = new AbortController();
    let isAborted = false;

    const fetchStream = async () => {
        try {
            for await (const chunk of streamChat({
                query,
                intent: mode,
                session_id: sessionId,
                include_sources: true
            }, abortController.signal)) {  // ← Pass AbortSignal
                if (isAborted) break;  // Stop if unmounted
                handleChunk(chunk);
            }
        } catch (err) {
            if (isAborted || (err instanceof Error && err.name === 'AbortError')) {
                return;  // Ignore expected abort
            }
            // Handle other errors...
        }
    };

    fetchStream();

    // Cleanup: Cancel SSE connection when component unmounts
    return () => {
        isAborted = true;
        abortController.abort();
    };
}, [query, mode, sessionId]);
```

```typescript
// frontend/src/api/chat.ts
export async function* streamChat(request: ChatRequest, signal?: AbortSignal): AsyncGenerator<ChatChunk> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,  // ← Pass signal to fetch
  });
  // ... rest of implementation
}
```

**Tasks:**
- [x] Added AbortController to StreamingAnswer component
- [x] Added cleanup function to cancel connection on unmount
- [x] Modified streamChat() to accept AbortSignal parameter
- [x] Properly handle AbortError in error handling
- [x] Tested with React StrictMode enabled
- [ ] Add integration test for streaming (TODO)

**Files Modified:**
- `frontend/src/components/chat/StreamingAnswer.tsx`
- `frontend/src/api/chat.ts`

**Benefits:**
- ✅ Clean answer display (no duplicates)
- ✅ Better user experience
- ✅ Reduced bandwidth (50% less data)
- ✅ Works correctly with React StrictMode in development

---

### Feature 17.6: Admin Statistics API (5 SP)
**Status:** ✅ COMPLETED (2025-10-29)
**Commit:** `7111c78` - feat(sprint-17): Feature 17.6 - Admin Statistics API
**Duration:** 0.5 day

**Problem:**
No API endpoint to retrieve system statistics for admin UI display.

**Solution:**
Create admin endpoints for system statistics and indexing history.

**Tasks:**
- [x] `GET /api/v1/admin/stats` endpoint implemented
  - Qdrant: Total chunks, collection name, vector dimension
  - BM25: Corpus size (graceful degradation if unavailable)
  - Neo4j: Entity count, relationship count, chunk count (Cypher queries)
  - Redis: Active conversation count (scan conversation:*)
  - System: Embedding model name, last reindex timestamp (placeholder)
  - Individual stat collection wrapped in try-except for resilience
  - Returns partial results if some stats fail
- [x] Pydantic SystemStats model with optional fields
- [x] Comprehensive error handling and logging
- [x] OpenAPI documentation (auto-generated by FastAPI)
- [ ] `GET /api/v1/admin/history` endpoint (deferred - requires persistent storage implementation)
- [ ] Authentication middleware (deferred - Sprint 18 security hardening)
- [ ] Add tests for statistics endpoint (deferred to E2E test phase)

**Deliverables:**
```python
@router.get("/api/v1/admin/stats")
async def get_system_stats() -> SystemStats:
    """Get comprehensive system statistics."""
    return {
        "documents_total": ...,
        "qdrant_chunks": ...,
        "bm25_corpus_size": ...,
        "neo4j_entities": ...,
        "last_reindex": ...
    }
```

**Benefits:**
- ✅ Admin can monitor system health
- ✅ Track indexing history
- ✅ Data for dashboards and reporting

---

### Feature 17.3: Accessibility Improvements (TD-36) (8 SP)
**Status:** 📋 PLANNED
**Duration:** 1 day

**Problem:**
Frontend lacks proper accessibility features (WCAG 2.1 AA compliance).

**Solution:**
Add accessibility improvements across all components.

**Tasks:**
- [ ] Add ARIA labels to all interactive elements
- [ ] Keyboard navigation support (Tab, Enter, Escape)
- [ ] Focus management (modal dialogs, dropdowns)
- [ ] Color contrast compliance (WCAG AA: 4.5:1)
- [ ] Screen reader testing with NVDA/JAWS
- [ ] Alt text for images
- [ ] Semantic HTML (proper heading hierarchy)
- [ ] Skip navigation links
- [ ] Accessible error messages (role="alert")
- [ ] Form validation with clear error descriptions

**Deliverables:**
- All components pass axe-core automated testing
- Manual testing with screen readers
- Accessibility documentation

**Benefits:**
- ✅ Compliance with WCAG 2.1 AA standards
- ✅ Better user experience for all users
- ✅ Legal compliance (accessibility laws)

---

### Feature 17.4: Error Boundary Implementation (TD-37) (5 SP)
**Status:** 📋 PLANNED
**Duration:** 0.5 day

**Problem:**
Frontend lacks error boundaries for graceful error handling.

**Solution:**
Implement React error boundaries at component level.

**Tasks:**
- [ ] Create `ErrorBoundary` component
- [ ] Add error boundaries at key component levels
  - App level (global fallback)
  - Page level (per page)
  - Component level (critical components)
- [ ] Error logging integration (send to backend)
- [ ] User-friendly error UI
- [ ] Automatic error recovery (retry button)
- [ ] Development vs. production error display

**Deliverables:**
```typescript
// frontend/src/components/ErrorBoundary.tsx
export class ErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to backend
    // Display user-friendly message
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}
```

**Benefits:**
- ✅ Graceful error handling without app crash
- ✅ Better debugging with error logs
- ✅ Improved user experience

---

### Feature 17.5: Frontend E2E Test Improvements (8 SP)
**Status:** 📋 CONDITIONAL (only if Sprint 16 E2E tests need improvements)
**Duration:** 1 day

**Tasks:**
- [ ] Review Sprint 16 E2E test results
- [ ] Fix any flaky tests
- [ ] Add missing test coverage
- [ ] Improve test reliability
- [ ] Add visual regression testing
- [ ] CI integration improvements

---

## 📊 Sprint Metrics

### **Story Points Breakdown:**
```yaml
Feature 17.1: Admin UI for Directory Indexing   13 SP
Feature 17.2: Admin Statistics API               5 SP
Feature 17.3: Accessibility Improvements         8 SP
Feature 17.4: Error Boundary Implementation      5 SP
Feature 17.5: E2E Test Improvements              8 SP (optional)
-----------------------------------------------------------
Total:                                          39 SP (31 SP required, 8 SP optional)
```

### **Estimated Duration:**
- **Optimistic:** 4 days (7.75 SP/day velocity)
- **Realistic:** 5-6 days (6.5 SP/day velocity)
- **Pessimistic:** 7 days (5.6 SP/day velocity)

### **Feature Dependencies:**
```
Sprint 16 (Feature 16.2: Unified Re-Indexing) ✅ PREREQUISITE
  └── 17.1 (Admin UI) 📋 NEXT
  └── 17.2 (Admin API) 📋 NEXT

17.3 (Accessibility) 📋 (Independent)
17.4 (Error Boundaries) 📋 (Independent)
17.5 (E2E Tests) 📋 (Conditional)
```

**Critical Path:** Sprint 16.2 → 17.1 → 17.2 (18 SP)

---

## 🎯 Success Criteria

### **Functional Requirements:**
- [ ] Admin can specify directory to index via UI
- [ ] Real-time progress display shows current phase and ETA
- [ ] System statistics dashboard displays accurate data
- [ ] Indexing history shows past operations
- [ ] All components meet WCAG 2.1 AA standards
- [ ] Error boundaries prevent app crashes
- [ ] Admin UI works on mobile + desktop

### **Non-Functional Requirements:**
- [ ] Admin UI response time <100ms
- [ ] SSE progress updates every 500ms
- [ ] Accessibility score >95 (axe-core)
- [ ] Error boundary catches all React errors
- [ ] Test coverage >80% for new components

### **Documentation:**
- [ ] Admin UI user guide
- [ ] API documentation for admin endpoints
- [ ] Accessibility testing guide
- [ ] Error handling best practices

---

## 📚 References

- **Sprint 16 Plan:** Unified Re-Indexing Pipeline (Feature 16.2)
- **Sprint 15 Plan:** Frontend completion
- **Technical Debt:** TD-36 (Accessibility), TD-37 (Error Boundaries)

---

## 🚀 Next Steps

**Immediate Actions (after Sprint 16 completion):**
1. Review Sprint 16 Feature 16.2 re-indexing API
2. Design Admin UI mockups
3. Create statistics API endpoints
4. Implement Admin UI components
5. Add accessibility features
6. Add error boundaries

**Estimated Start:** After Sprint 16 completion
**Estimated Completion:** Sprint 17: TBD (depends on Sprint 16 end date)

---

**Last Updated:** 2025-10-28
**Status:** 📋 PLANNED (Feature 17.1 requested by user on 2025-10-28)
