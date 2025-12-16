# Sprint 48: Real-Time Thinking Phase Events

**Sprint Duration:** 2 Weeks
**Total Story Points:** 55 SP
**Focus:** Backend SSE Phase Events für transparente Verarbeitungsschritte

---

## Sprint Goal

Implementierung eines vollständigen Phase-Event-Systems, das den Nutzer in Echtzeit über den aktuellen Verarbeitungsschritt informiert. Alle Phasen (Intent Classification, Vector Search, Graph Query, Reranking, LLM Generation) senden SSE-Events mit Timing und Metriken.

---

## Features

### Feature 48.1: Phase Event Models & Types (5 SP)

**Backend: Event-Modelle definieren**

```python
# src/models/reasoning_events.py
class PhaseType(str, Enum):
    INTENT_CLASSIFICATION = "intent_classification"
    VECTOR_SEARCH_START = "vector_search_start"
    VECTOR_SEARCH_COMPLETE = "vector_search_complete"
    BM25_SEARCH = "bm25_search"
    RRF_FUSION = "rrf_fusion"
    RERANKING = "reranking"
    GRAPH_QUERY_START = "graph_query_start"
    GRAPH_QUERY_COMPLETE = "graph_query_complete"
    MEMORY_RETRIEVAL = "memory_retrieval"
    LLM_GENERATION_START = "llm_generation_start"
    LLM_GENERATION_COMPLETE = "llm_generation_complete"

class PhaseStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"

class PhaseEvent(BaseModel):
    type: Literal["phase"] = "phase"
    phase: PhaseType
    message: str
    status: PhaseStatus
    duration_ms: float | None = None
    timestamp: str
    data: dict[str, Any] = Field(default_factory=dict)
```

**Frontend: TypeScript Types**

```typescript
// frontend/src/types/chat.ts
export type ChatChunkType = 'metadata' | 'token' | 'source' | 'error' | 'complete' | 'phase' | 'reasoning';

export interface PhaseEvent {
  type: 'phase';
  phase: string;
  message: string;
  status: 'in_progress' | 'completed' | 'error' | 'skipped';
  duration_ms?: number;
  timestamp: string;
  data?: Record<string, unknown>;
}
```

**Dateien:**
- `src/models/reasoning_events.py` (NEU)
- `frontend/src/types/chat.ts` (UPDATE)
- `frontend/src/types/reasoning.ts` (UPDATE)

**Akzeptanzkriterien:**
- [ ] PhaseType Enum mit allen Phasen definiert
- [ ] PhaseStatus Enum mit allen Stati definiert
- [ ] PhaseEvent Pydantic Model mit `to_sse()` Methode
- [ ] Frontend TypeScript Types synchronisiert
- [ ] Unit Tests für Models

---

### Feature 48.2: CoordinatorAgent Streaming Method (13 SP)

**Backend: Neue `process_query_stream()` Methode**

Der CoordinatorAgent benötigt eine neue Streaming-Methode, die:
1. Phase-Events während der Verarbeitung yieldet
2. Token-Events vom LLM streamt
3. Source-Events bei Abruf sendet
4. ReasoningData am Ende zusammenbaut

```python
# src/agents/coordinator.py
async def process_query_stream(
    self,
    query: str,
    session_id: str | None = None,
    intent: str | None = None,
    namespaces: list[str] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream query processing with phase events."""

    # Phase 1: Intent Classification
    yield PhaseEvent(
        phase=PhaseType.INTENT_CLASSIFICATION,
        message="Analysiere Anfrage-Typ...",
        status=PhaseStatus.IN_PROGRESS,
    ).model_dump()

    # ... Graph execution mit Phase-Events ...

    # Am Ende: ReasoningData zusammenbauen
    yield {
        "type": "reasoning",
        "reasoning_data": build_reasoning_data(state, phase_events)
    }
```

**Dateien:**
- `src/agents/coordinator.py` (UPDATE)
- `src/agents/state.py` (UPDATE - phase_events in State)

**Akzeptanzkriterien:**
- [ ] `process_query_stream()` Methode implementiert
- [ ] Yieldet Phase-Events für jede Phase
- [ ] Yieldet Token-Events während LLM Generation
- [ ] Yieldet Source-Events nach Retrieval
- [ ] Yieldet ReasoningData am Ende
- [ ] Integration Tests

---

### Feature 48.3: Agent Node Instrumentation (13 SP)

**Backend: LangGraph Nodes instrumentieren**

Jeder Agent-Node wird erweitert, um Phase-Events zu emittieren:

```python
# src/agents/graph.py
async def vector_search_node(state: AgentState) -> AgentState:
    """Instrumented vector search node."""
    # Emit start event
    state["phase_events"].append(PhaseEvent(
        phase=PhaseType.VECTOR_SEARCH_START,
        message="Starte Vektorsuche...",
        status=PhaseStatus.IN_PROGRESS,
        timestamp=_get_iso_timestamp(),
    ))

    start_time = time.perf_counter()

    # ... existing search logic ...

    # Emit completion event
    duration_ms = (time.perf_counter() - start_time) * 1000
    state["phase_events"].append(PhaseEvent(
        phase=PhaseType.VECTOR_SEARCH_COMPLETE,
        message=f"Vektorsuche: {len(results)} Ergebnisse",
        status=PhaseStatus.COMPLETED,
        duration_ms=duration_ms,
        timestamp=_get_iso_timestamp(),
        data={
            "result_count": len(results),
            "top_score": results[0]["score"] if results else 0,
        }
    ))

    return state
```

**Zu instrumentierende Nodes:**
1. `router_node` → Intent Classification
2. `vector_search_node` → Vector Search Start/Complete
3. `hybrid_search_node` → BM25, RRF Fusion, Reranking
4. `graph_query_node` → Graph Query Start/Complete
5. `memory_node` → Memory Retrieval
6. `answer_node` → LLM Generation Start/Complete

**Dateien:**
- `src/agents/graph.py` (UPDATE)
- `src/agents/vector_search_agent.py` (UPDATE)
- `src/agents/graph_query_agent.py` (UPDATE)
- `src/agents/memory_agent.py` (UPDATE)
- `src/agents/answer_generator.py` (UPDATE)
- `src/components/vector_search/hybrid_search.py` (UPDATE)

**Akzeptanzkriterien:**
- [ ] Alle Nodes emittieren Start-Events
- [ ] Alle Nodes emittieren Completion-Events mit Duration
- [ ] Error-Events bei Fehlern (recoverable vs fatal)
- [ ] Skipped-Events wenn Phase übersprungen wird
- [ ] Phase-Events enthalten relevante Metriken
- [ ] Integration Tests für jeden Node

---

### Feature 48.4: Chat Stream API Enhancement (8 SP)

**Backend: `/api/v1/chat/stream` erweitern**

Das Streaming-Endpoint muss die Phase-Events aus dem Coordinator weiterleiten:

```python
# src/api/v1/chat.py
async def generate_stream() -> AsyncGenerator[str, None]:
    """Enhanced SSE stream with phase events."""

    # Send initial metadata
    yield _format_sse_message({
        "type": "metadata",
        "session_id": session_id,
        "timestamp": _get_iso_timestamp(),
    })

    # Stream from coordinator with phase events
    async for chunk in coordinator.process_query_stream(
        query=request.query,
        session_id=session_id,
        intent=request.intent,
        namespaces=request.namespaces,
    ):
        # Forward all events (phase, token, source, reasoning)
        yield _format_sse_message(chunk)

        # Collect for persistence
        if chunk.get("type") == "phase":
            collected_phases.append(chunk)
        elif chunk.get("type") == "token":
            collected_answer.append(chunk["content"])

    # Signal completion
    yield _format_sse_message({"type": "complete"})
```

**Dateien:**
- `src/api/v1/chat.py` (UPDATE)

**Akzeptanzkriterien:**
- [ ] Phase-Events werden vor Tokens gesendet
- [ ] Token-Events während LLM Generation
- [ ] Source-Events nach Retrieval
- [ ] Reasoning-Event am Ende
- [ ] Complete-Event zum Abschluss
- [ ] Error-Handling mit Phase-Status
- [ ] API Tests

---

### Feature 48.5: Phase Events Redis Persistence (5 SP)

**Backend: Phase-Events in Redis speichern**

Phase-Events werden zusammen mit der Conversation in Redis gespeichert:

```python
# src/api/v1/chat.py
async def save_conversation_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
    intent: str | None = None,
    sources: list | None = None,
    follow_up_questions: list[str] | None = None,
    title: str | None = None,
    phase_events: list[dict] | None = None,  # NEU
    reasoning_data: dict | None = None,       # NEU
) -> bool:
    """Save conversation turn with phase events."""

    messages.append({
        "role": "assistant",
        "content": assistant_message,
        "timestamp": datetime.now(UTC).isoformat(),
        "intent": intent,
        "sources": serialized_sources,
        "phase_events": phase_events,        # NEU
        "reasoning_data": reasoning_data,    # NEU
        "total_duration_ms": sum(
            e.get("duration_ms", 0)
            for e in (phase_events or [])
            if e.get("status") == "completed"
        ),
    })
```

**Dateien:**
- `src/api/v1/chat.py` (UPDATE)

**Akzeptanzkriterien:**
- [ ] Phase-Events in Conversation gespeichert
- [ ] Reasoning-Data in Conversation gespeichert
- [ ] Abrufbar via `/api/v1/chat/sessions/{session_id}`
- [ ] Historische Phase-Events für Analytics verfügbar
- [ ] Integration Tests

---

### Feature 48.6: Frontend Phase Event Handler (8 SP)

**Frontend: `useStreamChat` erweitern**

Der Streaming-Hook muss Phase-Events verarbeiten:

```typescript
// frontend/src/hooks/useStreamChat.ts
export interface StreamingState {
  answer: string;
  sources: Source[];
  isStreaming: boolean;
  error: string | null;
  // NEU
  currentPhase: string | null;
  phaseEvents: PhaseEvent[];
  reasoningData: ReasoningData | null;
}

const handleChunk = (chunk: ChatChunk) => {
  switch (chunk.type) {
    case 'phase':
      setPhaseEvents(prev => [...prev, chunk as PhaseEvent]);
      setCurrentPhase(chunk.phase);
      break;
    case 'reasoning':
      setReasoningData(chunk.reasoning_data);
      break;
    // ... existing handlers
  }
};
```

**Frontend: TypingIndicator mit Phase-Info**

```typescript
// frontend/src/components/chat/ConversationView.tsx
<TypingIndicator
  text={typingText}
  showAvatar={true}
  startTime={thinkingStartTime ?? undefined}
  phase={streamingState.currentPhase}  // NEU
  progress={calculateProgress(streamingState.phaseEvents)}  // NEU
  details={getPhaseDetails(streamingState.currentPhase)}    // NEU
/>
```

**Dateien:**
- `frontend/src/hooks/useStreamChat.ts` (UPDATE)
- `frontend/src/api/chat.ts` (UPDATE)
- `frontend/src/components/chat/ConversationView.tsx` (UPDATE)
- `frontend/src/components/chat/TypingIndicator.tsx` (bereits erweitert)

**Akzeptanzkriterien:**
- [ ] Phase-Events werden empfangen und gespeichert
- [ ] Aktuelle Phase wird angezeigt
- [ ] Progress-Berechnung basierend auf Phasen
- [ ] Elapsed Time pro Phase sichtbar
- [ ] ReasoningData für ReasoningPanel verfügbar
- [ ] Component Tests

---

### Feature 48.7: ReasoningData Builder (3 SP)

**Backend: Automatische ReasoningData Generierung**

```python
# src/utils/phase_event_builder.py
def build_reasoning_data(
    state: AgentState,
    phase_events: list[PhaseEvent],
) -> ReasoningData:
    """Build ReasoningData from phase events."""

    retrieval_steps = []
    step_num = 1

    phase_to_source = {
        PhaseType.VECTOR_SEARCH_COMPLETE: "qdrant",
        PhaseType.BM25_SEARCH: "bm25",
        PhaseType.RRF_FUSION: "rrf_fusion",
        PhaseType.RERANKING: "reranker",
        PhaseType.GRAPH_QUERY_COMPLETE: "neo4j",
        PhaseType.MEMORY_RETRIEVAL: "redis",
    }

    for event in phase_events:
        if event.status == PhaseStatus.COMPLETED and event.phase in phase_to_source:
            retrieval_steps.append(RetrievalStep(
                step=step_num,
                source=phase_to_source[event.phase],
                duration_ms=event.duration_ms or 0,
                result_count=event.data.get("result_count", 0),
                details=event.data,
            ))
            step_num += 1

    total_duration = sum(
        e.duration_ms for e in phase_events
        if e.status == PhaseStatus.COMPLETED and e.duration_ms
    )

    return ReasoningData(
        intent=IntentInfo(
            intent=state.get("intent", "hybrid"),
            confidence=state.get("intent_confidence", 0.95),
        ),
        retrieval_steps=retrieval_steps,
        tools_used=[],
        total_duration_ms=total_duration,
    )
```

**Dateien:**
- `src/utils/phase_event_builder.py` (NEU)

**Akzeptanzkriterien:**
- [ ] Konvertiert Phase-Events zu RetrievalSteps
- [ ] Berechnet Gesamtdauer
- [ ] Intent-Info aus State extrahiert
- [ ] Unit Tests

---

## Error Handling Strategie

### Recoverable Errors (Phase continues)
- Einzelne Suchergebnisse nicht verfügbar
- Timeout bei optionalen Phasen (Reranking)
- Teilweise Graph-Ergebnisse

**Handling:**
```python
yield PhaseEvent(
    phase=PhaseType.RERANKING,
    message="Reranking übersprungen (Timeout)",
    status=PhaseStatus.SKIPPED,
    data={"reason": "timeout", "fallback": "using_rrf_results"}
)
# Continue with next phase
```

### Fatal Errors (Search aborted)
- Keine Retrieval-Ergebnisse
- LLM nicht erreichbar
- Kritische DB-Verbindungsfehler

**Handling:**
```python
yield PhaseEvent(
    phase=PhaseType.LLM_GENERATION_START,
    message="LLM nicht erreichbar",
    status=PhaseStatus.ERROR,
    data={"error": str(e), "recoverable": False}
)
# Stream ends, error event sent
yield {"type": "error", "error": "LLM service unavailable", "code": "LLM_ERROR"}
```

---

## Betroffene Dateien (Zusammenfassung)

### Backend - Neue Dateien
| Datei | Beschreibung |
|-------|--------------|
| `src/models/reasoning_events.py` | Phase Event Models |
| `src/utils/phase_event_builder.py` | ReasoningData Builder |

### Backend - Updates
| Datei | Änderungen |
|-------|------------|
| `src/agents/coordinator.py` | `process_query_stream()` Methode |
| `src/agents/state.py` | `phase_events` in State |
| `src/agents/graph.py` | Node Instrumentation |
| `src/agents/vector_search_agent.py` | Phase Events |
| `src/agents/graph_query_agent.py` | Phase Events |
| `src/agents/memory_agent.py` | Phase Events |
| `src/agents/answer_generator.py` | LLM Phase Events |
| `src/components/vector_search/hybrid_search.py` | Sub-Phase Events |
| `src/api/v1/chat.py` | Stream Enhancement + Redis Storage |

### Frontend - Updates
| Datei | Änderungen |
|-------|------------|
| `frontend/src/types/chat.ts` | Phase Event Types |
| `frontend/src/types/reasoning.ts` | RetrievalStep Updates |
| `frontend/src/hooks/useStreamChat.ts` | Phase Event Handler |
| `frontend/src/api/chat.ts` | ChatChunkType Extension |
| `frontend/src/components/chat/ConversationView.tsx` | Phase Props |

---

## SSE Event Flow (Vollständig)

```
Client POST /api/v1/chat/stream
    │
    ├── metadata (session_id, timestamp)
    │
    ├── phase (intent_classification, in_progress)
    ├── phase (intent_classification, completed, 5ms)
    │
    ├── phase (vector_search_start, in_progress)
    ├── phase (bm25_search, completed, 28ms, count=45)
    ├── phase (vector_search_complete, completed, 87ms, count=52)
    ├── phase (rrf_fusion, completed, 12ms, merged=67)
    ├── phase (reranking, completed, 112ms, top_score=0.95)
    │
    ├── phase (graph_query_start, in_progress)
    ├── phase (graph_query_complete, completed, 156ms, entities=12)
    │
    ├── source {...}
    ├── source {...}
    ├── source {...}
    │
    ├── phase (llm_generation_start, in_progress)
    ├── token "Die"
    ├── token " Antwort"
    ├── token " lautet"
    ├── token "..."
    ├── phase (llm_generation_complete, completed, 234ms)
    │
    ├── reasoning (ReasoningData mit retrieval_steps)
    │
    └── complete
```

---

## Akzeptanzkriterien (Sprint)

### Must Have
- [ ] Phase-Events für alle Hauptphasen (Intent, Vector, Graph, LLM)
- [ ] Elapsed Time Anzeige im Frontend
- [ ] Aktuelle Phase im TypingIndicator sichtbar
- [ ] Fehlerhafte Phasen werden angezeigt
- [ ] Phase-Events in Redis persistiert

### Should Have
- [ ] ReasoningData im ReasoningPanel anzeigen
- [ ] Progress-Berechnung basierend auf Phasen
- [ ] Sub-Phase Events (BM25, RRF, Reranking)

### Nice to Have
- [ ] Phase-Statistiken in Admin Dashboard
- [ ] Historische Phase-Performance Analyse

---

## Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Performance-Overhead durch Event-Emission | Mittel | Niedrig | Async Events, minimaler Payload |
| Breaking Change in SSE Format | Hoch | Mittel | Versionierung, Frontend graceful handling |
| Inkonsistente Event-Reihenfolge | Niedrig | Mittel | Sequentielle Emission, Timestamps |

---

## Bezug zu Technical Debt

### Relevant für Sprint 48
| TD# | Titel | Bezug |
|-----|-------|-------|
| TD-053 | Admin Dashboard | Phase-Events für System Monitoring nutzen |
| TD-059 | Reranking Container | Reranking-Phase zeigt Status (enabled/skipped) |
| TD-043 | Follow-up Questions Redis | Gleiches Redis-Pattern für Phase-Events |

### Nicht in Sprint 48
- TD-044, TD-045, TD-047 (andere Themen)

---

## Sprint Metriken

| Metrik | Target |
|--------|--------|
| Features | 7 |
| Story Points | 55 SP |
| Test Coverage | >80% |
| Phase Latency Overhead | <10ms |

---

## Definition of Done

- [ ] Alle Features implementiert
- [ ] Unit Tests für alle neuen Models
- [ ] Integration Tests für Streaming
- [ ] Frontend Component Tests
- [ ] E2E Tests für Phase Display
- [ ] Code Review abgeschlossen
- [ ] Dokumentation aktualisiert
- [ ] Performance validiert (<10ms Overhead)

---

**Erstellt:** 2025-12-16
**Sprint Start:** TBD
**Sprint End:** TBD
