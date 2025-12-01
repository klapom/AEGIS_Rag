# Sprint 35: Frontend UX Enhancement & Chat Experience

**Status:** PLANNED
**Branch:** `sprint-35-frontend-ux`
**Start Date:** 2025-12-01
**Estimated Duration:** 5-7 Tage
**Total Story Points:** 52 SP

---

## Sprint Overview

Sprint 35 fokussiert auf **Frontend User Experience Verbesserungen**. Nach erfolgreicher Implementierung des Knowledge Graphen (Sprint 34) und der RELATES_TO-Extraktion optimieren wir jetzt die Benutzeroberfläche:

1. **Seamless Q&A Chat Flow** - Chat-Erlebnis wie Claude/ChatGPT
2. **Admin Indexing Side-by-Side Layout** - Log und Details nebeneinander (50%/50%)
3. **Follow-up Questions Fix** - Bug aus TD-043 beheben
4. **Session Management Improvements** - Conversation History und Titles
5. **UI Polish** - Loading States, Animations, Dark Mode Vorbereitung

---

## Current State Analysis

### HomePage.tsx (Chat Interface)

**Aktueller Zustand:**
- Frage und Antwort in separaten Boxen mit Labels "Frage" / "Antwort"
- Conversation History als Liste von Boxen
- StreamingAnswer als separater Bereich

**Probleme:**
- Kein nahtloser Chat-Flow (jede Message ist eine separate Box)
- Labels "Frage" / "Antwort" unterbrechen den Lesefluss
- Kein visuelles Avatar/Icon System

### AdminIndexingPage.tsx (Indexing Interface)

**Aktueller Zustand:**
- Progress Log in collapsible `<details>` Element
- Details Button oeffnet Dialog (Modal)
- Vertikales Layout

**Probleme:**
- Details nicht sofort sichtbar (erst nach Klick)
- Log und Details nicht gleichzeitig sichtbar
- Modal unterbricht Workflow

---

## Features

| # | Feature | SP | Priority | Dependencies |
|---|---------|-----|----------|--------------|
| 35.1 | Seamless Chat Flow (Claude/ChatGPT Style) | 13 | P0 | - |
| 35.2 | Admin Indexing Side-by-Side Layout | 8 | P0 | - |
| 35.3 | Follow-up Questions Redis Fix (TD-043) | 5 | P0 | - |
| 35.4 | Auto-Generated Conversation Titles | 8 | P1 | 35.3 |
| 35.5 | Session History Sidebar | 8 | P1 | 35.4 |
| 35.6 | Loading States & Animations | 5 | P2 | - |
| 35.7 | Dark Mode Preparation | 5 | P2 | - |

**Total: 52 SP**

---

## Feature Details

### Feature 35.1: Seamless Chat Flow (13 SP)
**Priority:** P0

**Ziel:** Chat-Erlebnis wie Claude/ChatGPT - nahtloser Fluss von Frage und Antwort.

**Aktuelle Implementierung:**
```tsx
// HomePage.tsx - Aktuell
{conversationHistory.map((message, index) => (
  <div className={`p-6 rounded-lg ${
    message.role === 'user' ? 'bg-blue-50' : 'bg-white'
  }`}>
    <div className="text-xs font-semibold">
      {message.role === 'user' ? 'Frage' : 'Antwort'}
    </div>
    <div>{message.content}</div>
  </div>
))}
```

**Neue Implementierung (Claude-Style):**
```tsx
// HomePage.tsx - Neu
{conversationHistory.map((message, index) => (
  <div className="flex gap-4 py-6 border-b border-gray-100">
    {/* Avatar */}
    <div className={`w-8 h-8 rounded-full flex-shrink-0 ${
      message.role === 'user'
        ? 'bg-blue-600'
        : 'bg-gradient-to-br from-teal-500 to-blue-600'
    }`}>
      {message.role === 'user' ? <UserIcon /> : <BotIcon />}
    </div>

    {/* Content */}
    <div className="flex-1 min-w-0">
      {/* Name (optional) */}
      <div className="text-sm font-semibold text-gray-900 mb-1">
        {message.role === 'user' ? 'Sie' : 'AegisRAG'}
      </div>

      {/* Message */}
      <div className="text-gray-800 prose prose-sm max-w-none">
        {message.content}
      </div>

      {/* Citations (nur bei assistant) */}
      {message.role === 'assistant' && message.citations && (
        <CitationList citations={message.citations} />
      )}
    </div>
  </div>
))}
```

**Design-Aenderungen:**
- [ ] Avatar-System (User = Blue Circle, Bot = Gradient Circle mit Icon)
- [ ] Keine separaten Boxen - durchgehender Fluss mit Border-Bottom
- [ ] Compact Layout ohne ueberfluessige Labels
- [ ] Name-Labels ("Sie" / "AegisRAG") optional via Settings
- [ ] Prose Styling fuer Markdown-Rendering
- [ ] Smooth Scroll to Bottom bei neuer Message
- [ ] Input-Feld fixiert am unteren Rand (wie ChatGPT)

**Tasks:**
- [ ] ChatMessage Component erstellen (Avatar + Content)
- [ ] UserAvatar und BotAvatar Components
- [ ] Prose/Markdown Styling integrieren
- [ ] Bottom-fixed Input Layout
- [ ] Auto-scroll Hook implementieren
- [ ] Tests fuer neue Components

**Acceptance Criteria:**
- [ ] Chat-Flow ohne visuelle Unterbrechungen
- [ ] Avatar-Icons fuer User und Bot
- [ ] Input-Feld immer sichtbar (fixed bottom)
- [ ] Smooth scrolling bei neuen Messages
- [ ] E2E Tests bestehen weiterhin

---

### Feature 35.2: Admin Indexing Side-by-Side Layout (8 SP)
**Priority:** P0

**Ziel:** Log und Details waehrend Indexierung nebeneinander anzeigen (50%/50%).

**Aktuelle Implementierung:**
- Progress Log in `<details>` (collapsed by default)
- Details nur im Dialog sichtbar (Modal)

**Neue Implementierung (Split View):**
```tsx
// AdminIndexingPage.tsx - Neu
{isIndexing && progress && (
  <div className="grid grid-cols-2 gap-6">
    {/* LEFT: Progress Log (50%) */}
    <div className="bg-gray-50 rounded-lg p-4">
      <h3 className="font-semibold mb-3">Progress Log</h3>
      <div className="h-96 overflow-y-auto font-mono text-xs space-y-1">
        {progressHistory.map((chunk, i) => (
          <LogEntry key={i} chunk={chunk} />
        ))}
      </div>
    </div>

    {/* RIGHT: Details Panel (50%) */}
    <div className="bg-white rounded-lg border p-4">
      <h3 className="font-semibold mb-3">Aktuelle Datei</h3>
      <DetailPanel progress={detailedProgress} />
    </div>
  </div>
)}
```

**Detail Panel Inhalte:**
```tsx
interface DetailPanelProps {
  progress: DetailedProgress | null;
}

function DetailPanel({ progress }: DetailPanelProps) {
  if (!progress) return <EmptyState />;

  return (
    <div className="space-y-4">
      {/* Current File */}
      <div>
        <label>Datei:</label>
        <span>{progress.current_file || '-'}</span>
      </div>

      {/* Page Progress */}
      <div>
        <label>Seite:</label>
        <span>{progress.current_page} / {progress.total_pages}</span>
        <ProgressBar value={progress.page_progress} />
      </div>

      {/* VLM Analysis */}
      {progress.vlm_analysis && (
        <div>
          <label>VLM Analyse:</label>
          <div className="text-sm">{progress.vlm_analysis}</div>
        </div>
      )}

      {/* Chunks */}
      <div>
        <label>Chunks:</label>
        <span>{progress.chunks_created}</span>
      </div>

      {/* Entities */}
      <div>
        <label>Entities:</label>
        <span>{progress.entities_extracted}</span>
      </div>

      {/* Pipeline Stage */}
      <div>
        <label>Pipeline:</label>
        <PipelineStages current={progress.pipeline_stage} />
      </div>
    </div>
  );
}
```

**Layout-Aenderungen:**
- [ ] Grid Layout mit `grid-cols-2` (responsive auf Mobile: `grid-cols-1`)
- [ ] Log Panel links (50%) mit scroll und auto-follow
- [ ] Detail Panel rechts (50%) mit Live-Updates
- [ ] Remove Dialog - Details direkt sichtbar
- [ ] Collapsible Option fuer kompakte Ansicht

**Tasks:**
- [ ] Grid Layout in AdminIndexingPage implementieren
- [ ] LogEntry Component fuer einzelne Log-Zeilen
- [ ] DetailPanel Component fuer rechte Seite
- [ ] PipelineStages Visualization
- [ ] Auto-scroll fuer Log Panel
- [ ] Responsive Layout (mobile = stacked)

**Acceptance Criteria:**
- [ ] Log und Details gleichzeitig sichtbar (side-by-side)
- [ ] 50%/50% Split auf Desktop
- [ ] Stacked Layout auf Mobile (<768px)
- [ ] Live Updates in beiden Panels
- [ ] E2E Tests bestehen weiterhin

---

### Feature 35.3: Follow-up Questions Redis Fix (5 SP)
**Priority:** P0
**Technical Debt:** TD-043

**Problem:**
Backend `save_conversation_turn()` speichert nicht korrekt in Redis. Follow-up Questions funktionieren im Frontend, aber Backend-Persistenz fehlt.

**Root Cause (aus TD-043):**
```python
# src/api/v1/chat.py - BUGGY
async def chat_stream():
    # ... streaming logic ...
    # MISSING: await memory_api.store(session_id, messages)
```

**Fix:**
```python
# src/api/v1/chat.py - FIXED
async def chat_stream():
    # ... streaming logic ...

    # After streaming complete, persist to Redis
    await save_conversation_turn(
        session_id=session_id,
        user_message=query,
        assistant_message=full_response,
        sources=sources,
        follow_up_questions=follow_up_questions
    )
```

**Tasks:**
- [ ] Analysiere `src/api/v1/chat.py` fuer missing storage calls
- [ ] Implementiere `save_conversation_turn()` mit Redis
- [ ] Speichere: session_id, messages, sources, follow_up_questions
- [ ] Integration Tests fuer Redis persistence
- [ ] Verifiziere E2E Tests fuer Follow-up Questions

**Acceptance Criteria:**
- [ ] Follow-up Questions werden in Redis gespeichert
- [ ] Session kann nach Browser-Refresh fortgesetzt werden
- [ ] 9 Follow-up Question E2E Tests bestehen

---

### Feature 35.4: Auto-Generated Conversation Titles (8 SP)
**Priority:** P1
**Dependencies:** Feature 35.3

**Ziel:** LLM-basierte Titel-Generierung nach erster Antwort (3-5 Woerter).

**Implementation:**

**Backend:**
```python
# src/api/v1/chat.py
async def generate_conversation_title(query: str, answer: str) -> str:
    """Generate 3-5 word title using LLM."""
    prompt = f"""Generate a concise 3-5 word title for this conversation:

User Question: {query[:200]}
Assistant Answer: {answer[:500]}

Title (3-5 words, no quotes):"""

    response = await aegis_llm_proxy.complete(prompt, max_tokens=20)
    return response.strip()

@router.post("/api/v1/chat/sessions/{session_id}/title")
async def update_session_title(session_id: str, title: str):
    """Update session title in Redis."""
    await redis_memory.update_title(session_id, title)
```

**Frontend:**
```tsx
// Nach erster Antwort
const handleFirstResponse = async (response: string) => {
  const title = await api.generateTitle(currentQuery, response);
  setSessionTitle(title);
  // Auto-update in sidebar
};
```

**Tasks:**
- [ ] Backend Endpoint fuer Title Generation
- [ ] Backend Endpoint fuer Title Update
- [ ] Frontend Hook: useConversationTitle
- [ ] Inline Edit fuer manuelle Titel-Aenderung
- [ ] Redis Schema fuer Session Metadata
- [ ] Unit Tests fuer Title Generation

**Acceptance Criteria:**
- [ ] Titel wird nach erster Antwort generiert
- [ ] Titel ist 3-5 Woerter
- [ ] Titel kann manuell editiert werden
- [ ] Titel erscheint in Sidebar

---

### Feature 35.5: Session History Sidebar (8 SP)
**Priority:** P1
**Dependencies:** Feature 35.4

**Ziel:** Sidebar mit vergangenen Konversationen (wie ChatGPT).

**Design:**
```tsx
function SessionSidebar() {
  const { sessions, isLoading } = useSessions();

  return (
    <aside className="w-64 bg-gray-900 text-white h-screen overflow-y-auto">
      {/* New Chat Button */}
      <button className="w-full p-4 border-b border-gray-700">
        + Neue Konversation
      </button>

      {/* Session Groups (Today, Yesterday, Last Week) */}
      <SessionGroup title="Heute" sessions={todaySessions} />
      <SessionGroup title="Gestern" sessions={yesterdaySessions} />
      <SessionGroup title="Letzte Woche" sessions={lastWeekSessions} />

      {/* Settings */}
      <div className="absolute bottom-0 w-full p-4 border-t border-gray-700">
        <SettingsMenu />
      </div>
    </aside>
  );
}
```

**Tasks:**
- [ ] SessionSidebar Component
- [ ] SessionItem Component (Title + Preview + Date)
- [ ] useSessions Hook (fetch from Redis)
- [ ] Session Grouping (Today/Yesterday/Week/Month)
- [ ] "New Chat" Button
- [ ] Delete Session Funktion
- [ ] Responsive Toggle (hamburger menu auf Mobile)

**Acceptance Criteria:**
- [ ] Sidebar zeigt vergangene Sessions
- [ ] Sessions sind nach Datum gruppiert
- [ ] Click auf Session laedt Conversation
- [ ] "New Chat" startet neue Session
- [ ] Delete Funktion vorhanden

---

### Feature 35.6: Loading States & Animations (5 SP)
**Priority:** P2

**Ziel:** Professionelle Loading-States und subtile Animationen.

**Komponenten:**
- [ ] Skeleton Loader fuer Chat Messages
- [ ] Typing Indicator (drei Punkte Animation)
- [ ] Smooth Message Appearance (fade-in)
- [ ] Progress Shimmer Effect
- [ ] Button Loading States

**Tasks:**
- [ ] SkeletonMessage Component
- [ ] TypingIndicator Component
- [ ] CSS Animations (tailwind-animate)
- [ ] Framer Motion Integration (optional)
- [ ] Consistent Loading Patterns

**Acceptance Criteria:**
- [ ] Keine "leeren" Zustaende
- [ ] Smooth Transitions
- [ ] Konsistente Loading-Patterns

---

### Feature 35.7: Dark Mode Preparation (5 SP)
**Priority:** P2

**Ziel:** CSS-Vorbereitung fuer Dark Mode (Implementation in Sprint 36).

**Tasks:**
- [ ] Tailwind Dark Mode Konfiguration
- [ ] CSS Variables fuer Farben
- [ ] Color Palette Definition (Light/Dark)
- [ ] Dark Mode Toggle in Settings
- [ ] localStorage Persistence
- [ ] System Preference Detection

**Acceptance Criteria:**
- [ ] Dark Mode Toggle funktioniert
- [ ] Farben wechseln korrekt
- [ ] Preference wird gespeichert

---

## Architecture References

- **TD-043**: [Follow-up Questions Redis Storage](../technical-debt/TD-043_FOLLOWUP_QUESTIONS_REDIS.md)
- **Sprint 31**: [HomePage → ChatPage Transformation](SPRINT_31_PLAN.md)
- **Sprint 33**: [Admin Indexing Progress](SPRINT_33_PLAN.md)

---

## Timeline (Parallel Execution)

```
Day 1-2: Feature 35.1 (Seamless Chat Flow) + Feature 35.3 (Redis Fix)
Day 2-3: Feature 35.2 (Admin Side-by-Side Layout)
Day 3-4: Feature 35.4 (Auto Titles) + Feature 35.5 (Sidebar)
Day 4-5: Feature 35.6 (Loading States) + Feature 35.7 (Dark Mode Prep)
Day 5-6: Testing & Bug Fixes
Day 6-7: Documentation & Code Review
```

**Estimated Total:** 5-7 Tage mit paralleler Entwicklung

---

## Success Criteria

- [ ] Chat-Flow nahtlos wie Claude/ChatGPT
- [ ] Admin Indexing: Log + Details side-by-side
- [ ] Follow-up Questions funktionieren persistent
- [ ] Auto-generated Conversation Titles
- [ ] Session History in Sidebar
- [ ] Loading States und Animations
- [ ] Dark Mode Toggle funktioniert
- [ ] Alle bestehenden E2E Tests bestehen
- [ ] Code Coverage >80% fuer neue Components

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking E2E Tests | Medium | High | Test-first development, incremental changes |
| Redis Schema Migration | Low | Medium | Backward compatible updates |
| Mobile Layout Issues | Medium | Medium | Mobile-first design, responsive testing |
| Dark Mode Color Conflicts | Low | Low | CSS Variables, systematic color review |

---

## Post-Sprint Review Items

- User Feedback zu Chat-Flow sammeln
- Performance-Messung (Time to First Token)
- Accessibility Audit (WCAG 2.1)
- Mobile Usability Testing
- Identify weitere UX Improvements fuer Sprint 36
