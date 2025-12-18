# Sprint 51: Phase Display & Admin UX Fixes

**Status:** PLANNED
**Branch:** `sprint-51-phase-admin-fixes`
**Start Date:** 2025-12-18
**Estimated Duration:** 3-4 Tage
**Total Story Points:** 26 SP

---

## Sprint Overview

Sprint 51 adressiert **kritische UX-Probleme** im Reasoning Panel und Admin-Bereich, die während der Tests identifiziert wurden. Der ursprüngliche Plan (E2E Tests für unutilized Features) wird auf Sprint 52/53 verschoben.

**Identifizierte Issues:**
1. **Phase Display:** Zeiten falsch, immer "Faktenbezogen", 1/9 → 3/3 Phase Mismatch
2. **LLM Streaming:** Antwort wird nicht gestreamt, nur am Ende angezeigt
3. **Admin Navigation:** Subpages nicht oben verlinkt, Domains nicht eingeklappt
4. **Domain Training:** Veralteter Status, keine Lösch-Funktion

**Verschoben auf zukünftige Sprints:**
- Sprint 52: Graph Time Travel (Inkompatibilitäts-Analyse erforderlich)
- Sprint 53: Secure Shell Sandbox (generische Bash vs Repo-spezifisch)
- Sprint 54: LightRAG/RELATES_TO Relationen-Analyse

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 51.1 | Phase Display Fixes | 8 | P0 | NEW |
| 51.2 | LLM Answer Streaming | 5 | P0 | NEW |
| 51.3 | Admin Navigation & Layout | 5 | P1 | NEW |
| 51.4 | Domain Training Status & Delete | 5 | P1 | NEW |
| 51.5 | Intent Classification Fix | 3 | P1 | NEW |

**Total: 26 SP**

---

## Feature Details

### Feature 51.1: Phase Display Fixes (8 SP)
**Priority:** P0
**Team:** Frontend + Backend

**Probleme:**
1. Phase count zeigt "1/9 Phasen" am Anfang, aber "3/3" am Ende
2. Execution times werden nicht korrekt angezeigt (z.B. "0ms" für Phasen)
3. Phasen werden nur am Ende angezeigt, nicht während der Verarbeitung
4. Keine Zwischenergebnisse während der Verarbeitung

**Root Cause Analyse:**

```typescript
// frontend/src/types/reasoning.ts
export const TOTAL_PHASES = Object.keys(PHASE_NAMES).length; // = 9

// Aber Backend sendet nur 3 Phasen:
// - intent_classification
// - rrf_fusion
// - llm_generation
// Die anderen 6 Phasen werden nie gesendet!
```

**Lösung:**

1. **Backend:** Alle relevanten Phasen senden (vector_search, bm25_search, etc.)
2. **Backend:** Start-Events am Anfang jeder Phase senden (nicht nur end)
3. **Frontend:** TOTAL_PHASES dynamisch basierend auf Config, nicht hardcoded
4. **Frontend:** Echtzeit-Updates während Phasen anzeigen

**Files zu ändern:**

```
src/agents/coordinator_agent.py   # Phase events für alle Schritte
src/agents/vector_search_agent.py # Phase start/end events
src/agents/answer_generator.py    # LLM generation phase tracking
frontend/src/types/reasoning.ts   # Dynamic phase count
frontend/src/hooks/useStreamChat.ts # Real-time phase handling
frontend/src/components/chat/PhaseIndicator.tsx # Better UI updates
```

**Acceptance Criteria:**
- [ ] Alle 9 Phasen werden im Backend gesendet (wenn ausgeführt)
- [ ] Start und End Events für jede Phase
- [ ] Korrekte Zeiten für jede Phase
- [ ] Echtzeit-Updates während Verarbeitung
- [ ] Phase count zeigt tatsächliche Phasen (nicht hardcoded 9)

---

### Feature 51.2: LLM Answer Streaming (5 SP)
**Priority:** P0
**Team:** Backend + Frontend

**Problem:**
- Antwort wird erst am Ende komplett angezeigt
- Keine Token-für-Token Streaming während LLM generiert
- Benutzer wartet lange ohne Feedback

**Aktuelle Implementierung:**

```python
# src/agents/answer_generator.py
# Generiert komplette Antwort, dann sendet sie als ein Block
answer = await self.llm.ainvoke(prompt)
return {"answer": answer.content}
```

**Lösung:**

```python
# Streaming mit async generator
async def generate_streaming(self, ...):
    async for chunk in self.llm.astream(prompt):
        yield {"token": chunk.content}
    yield {"complete": True}
```

**Frontend Integration:**

```typescript
// useStreamChat.ts - Token handling
case 'token':
  setAnswer(prev => prev + chunk.data.token);
  break;
```

**Files zu ändern:**

```
src/agents/answer_generator.py    # Streaming generator
src/api/v1/chat.py               # Stream tokens via SSE
frontend/src/hooks/useStreamChat.ts # Handle token events
```

**Acceptance Criteria:**
- [ ] Tokens werden einzeln gestreamt
- [ ] Antwort erscheint progressiv
- [ ] Streaming-Cursor während Generierung
- [ ] Latency < 500ms bis erstes Token (TTFT)

---

### Feature 51.3: Admin Navigation & Layout (5 SP)
**Priority:** P1
**Team:** Frontend

**Probleme:**
1. Admin Subpages sind nur im Footer verlinkt, nicht oben
2. Domains Section ist oben, sollte eingeklappt unten sein

**Aktuelle Struktur:**
```
Admin Dashboard
├── Domains         <-- sollte unten, eingeklappt
├── Indexing
├── Settings
└── Footer: Links   <-- sollten oben sein
```

**Gewünschte Struktur:**
```
Admin Dashboard
├── [Navigation Bar: Graph | Costs | LLM | Health | Training]
├── Indexing
├── Settings
└── Domains (collapsed by default)
```

**Lösung:**

```tsx
// AdminDashboard.tsx
export function AdminDashboard() {
  return (
    <div>
      {/* TOP: Navigation Bar */}
      <AdminNavigationBar />

      <header>...</header>

      {/* Sections */}
      <IndexingSection />
      <SettingsSection />

      {/* BOTTOM: Domains (collapsed) */}
      <DomainSection defaultExpanded={false} />
    </div>
  );
}
```

**Files zu ändern:**

```
frontend/src/pages/AdminDashboard.tsx
frontend/src/components/admin/AdminNavigationBar.tsx (NEW)
frontend/src/components/admin/DomainSection.tsx # defaultExpanded prop
```

**Acceptance Criteria:**
- [ ] Navigation Bar oben mit allen Subpage-Links
- [ ] Domains Section ganz unten
- [ ] Domains standardmäßig eingeklappt
- [ ] Responsive Design erhalten

---

### Feature 51.4: Domain Training Status & Delete (5 SP)
**Priority:** P1
**Team:** Frontend + Backend

**Probleme:**
1. Domain-Liste zeigt veralteten Status (pending/training statt failed)
2. Keine Möglichkeit, eine Domain zu löschen
3. View-Dialog zeigt korrekten Status, aber Liste nicht

**Root Cause:**
- `useDomains()` Hook fetcht nur einmal, kein Auto-Refetch
- Kein Polling oder WebSocket für Status-Updates
- Delete-API existiert nicht

**Lösung:**

```typescript
// useDomainTraining.ts
export function useDomains() {
  return useQuery({
    queryKey: ['domains'],
    queryFn: fetchDomains,
    refetchInterval: 5000, // Poll every 5 seconds
    staleTime: 2000,       // Consider stale after 2s
  });
}
```

```python
# Backend: DELETE endpoint
@router.delete("/domains/{domain_id}")
async def delete_domain(domain_id: str):
    """Delete a domain and its associated data."""
    # 1. Delete from database
    # 2. Delete training artifacts
    # 3. Clean up BM25 index entries
    return {"status": "deleted"}
```

**Files zu ändern:**

```
frontend/src/hooks/useDomainTraining.ts  # Auto-refetch
frontend/src/components/admin/DomainList.tsx # Delete button
frontend/src/components/admin/DomainDetailDialog.tsx # Delete action
src/api/v1/admin.py  # DELETE endpoint
```

**Acceptance Criteria:**
- [ ] Domain-Status wird automatisch aktualisiert (polling)
- [ ] Delete-Button in Domain-Liste und Detail-Dialog
- [ ] Bestätigungsdialog vor Löschen
- [ ] Backend DELETE Endpoint implementiert
- [ ] Status in Liste und Dialog konsistent

---

### Feature 51.5: Intent Classification Fix (3 SP)
**Priority:** P1
**Team:** Backend

**Problem:**
- Intent-Klassifikation zeigt immer "Faktenbezogen" (factual)
- Confidence ist immer 80%
- Andere Intent-Typen (keyword, exploratory, summary) werden nie angezeigt

**Root Cause Analyse:**

```python
# src/components/retrieval/intent_classifier.py
# Prüfen: Wird der Intent korrekt klassifiziert?
# Wird er korrekt an Frontend gesendet?
```

**Mögliche Issues:**
1. Intent Classifier gibt immer "factual" zurück
2. Intent wird nicht vom Backend zum Frontend gesendet
3. Frontend ignoriert andere Intent-Typen

**Files zu prüfen:**

```
src/components/retrieval/intent_classifier.py
src/agents/coordinator_agent.py  # Intent passing
src/api/v1/chat.py              # SSE metadata
frontend/src/hooks/useStreamChat.ts # Intent handling
```

**Acceptance Criteria:**
- [ ] Intent Classifier unterscheidet alle 4 Typen korrekt
- [ ] Intent wird im SSE metadata Event gesendet
- [ ] Frontend zeigt korrekten Intent an
- [ ] Confidence Score ist realistisch (nicht immer 80%)

---

## Verschobene Features

### Sprint 52: Graph Time Travel (13 SP)
**Reason:** Inkompatibilitäts-Analyse mit bestehendem Code erforderlich

**Analyse-Tasks:**
1. Prüfen: Temporal Query Builder mit aktuellem Neo4j Schema
2. Prüfen: Version Manager Integration mit Entity Extraction
3. Prüfen: Evolution Tracker mit Community Detection
4. UI Components für Time Travel entwickeln

**Files to Analyze:**
```
src/components/graph_rag/temporal_query_builder.py
src/components/graph_rag/evolution_tracker.py
src/components/graph_rag/version_manager.py
src/components/graph_rag/entity_extractor.py
src/components/graph_rag/community_detector.py
```

### Sprint 53: Secure Shell Sandbox (8 SP)
**Reason:** Test soll generische Bash-Execution testen, nicht Repo-spezifisch

**Änderungen:**
- Sandbox für beliebige Shell-Commands, nicht nur Repository-Analyse
- User-Eingabe von Commands unterstützen
- Security: Command Whitelist/Blacklist

### Sprint 54: LightRAG Relations Analysis
**Reason:** Komplexes Thema erfordert dedizierte Analyse

**Themen:**
1. RELATES_TO vs MENTIONED_IN Semantik
2. Relation Merging bei hoher Entity-Dichte
3. LightRAG Description-Feld für semantische Attribution
4. Performance bei vielen Relations (>10k)

---

## Timeline

### Tag 1
- Feature 51.1 (Phase Display) - Backend phase events
- Feature 51.3 (Admin Navigation) - Start

### Tag 2
- Feature 51.1 (Phase Display) - Frontend integration
- Feature 51.3 (Admin Navigation) - Complete

### Tag 3
- Feature 51.2 (LLM Streaming)
- Feature 51.5 (Intent Classification)

### Tag 4
- Feature 51.4 (Domain Status & Delete)
- Testing & Bug Fixes

---

## Acceptance Criteria (Sprint Complete)

- [ ] Phase Display zeigt korrekte Zeiten und alle ausgeführten Phasen
- [ ] LLM-Antwort wird Token-für-Token gestreamt
- [ ] Admin Navigation Bar oben, Domains unten eingeklappt
- [ ] Domain-Status wird automatisch aktualisiert
- [ ] Domains können gelöscht werden
- [ ] Intent-Klassifikation funktioniert für alle 4 Typen
- [ ] Alle Tests passieren
- [ ] Code Review abgeschlossen

---

## Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| LLM Streaming kompliziert | Medium | High | Schrittweise Implementation, Token buffering |
| Phase Events Performance | Low | Medium | Batch events, debounce UI updates |
| Backward Compatibility | Low | Medium | Feature Flags für neue Features |

---

## Definition of Done

### Per Feature
- [ ] Implementation abgeschlossen
- [ ] Tests geschrieben (unit + integration)
- [ ] Code Review bestanden
- [ ] Dokumentation aktualisiert
- [ ] E2E Test passiert

### Sprint Complete
- [ ] Alle Features merged
- [ ] CI/CD Pipeline grün
- [ ] Sprint Summary erstellt
- [ ] Retrospective durchgeführt

---

**END OF SPRINT 51 PLAN**
