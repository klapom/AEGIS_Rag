# Sprint 37: Streaming Pipeline & Visual Progress Dashboard

**Sprint Duration:** 2025-12-07 - 2025-12-10 (4 Tage)
**Sprint Goal:** 6-8x Pipeline Speedup durch Streaming-Architektur + Echtzeit-Visualisierung
**Total Story Points:** 55 SP

---

## Sprint Backlog

### Feature 37.1: Streaming Pipeline Architecture (13 SP)
**Priority:** P0 (Kritisch)
**Beschreibung:** Umstellung der sequentiellen Pipeline auf AsyncIO Queue-basierte Streaming-Architektur

**Technical Tasks:**
1. `StreamingPipelineOrchestrator` Klasse erstellen
2. AsyncIO Queues für Inter-Stage Kommunikation
3. Chunk-Producer (aus Docling JSON)
4. Embedding-Consumer/Producer
5. Graph-Extraction-Consumer mit Worker Pool
6. Graceful Shutdown und Error Handling
7. Pipeline State Aggregation für SSE

**Deliverables:**
- `src/components/ingestion/streaming_pipeline.py` (neu)
- `src/components/ingestion/pipeline_queues.py` (neu)

**Acceptance Criteria:**
- [ ] Chunks werden sofort nach Erstellung weitergeleitet
- [ ] Embedding startet während Chunking noch läuft
- [ ] Graph Extraction startet während Embedding noch läuft
- [ ] Fehler in einem Chunk stoppen nicht die Pipeline
- [ ] Memory-Nutzung bleibt unter 4GB

---

### Feature 37.2: Worker Pool für Graph Extraction (8 SP)
**Priority:** P0 (Kritisch)
**Beschreibung:** Parallele LLM-Calls für Entity/Relation Extraction

**Technical Tasks:**
1. `GraphExtractionWorkerPool` Klasse
2. Configurable Worker Count (default: 4)
3. Semaphore für VRAM-Management
4. Per-Chunk Timeout und Retry
5. Result Aggregation und Deduplication
6. Ollama Connection Pooling

**Deliverables:**
- `src/components/ingestion/extraction_worker_pool.py` (neu)
- Config: `GRAPH_EXTRACTION_WORKERS=4`

**Acceptance Criteria:**
- [ ] 4 parallele LLM-Calls gleichzeitig
- [ ] Kein VRAM Overflow (Semaphore-geschützt)
- [ ] Entity-Deduplication funktioniert
- [ ] 3-4x Speedup für Graph Extraction Phase

---

### Feature 37.3: Pipeline Progress State Manager (8 SP)
**Priority:** P0 (Kritisch)
**Beschreibung:** Zentraler State Manager für Echtzeit-Progress Tracking aller Stages

**Technical Tasks:**
1. `PipelineProgressManager` Singleton
2. Stage-Level Progress (chunks_processed/total per stage)
3. Worker-Level Progress (active workers, queue depth)
4. Timing Metrics (duration per stage, per chunk)
5. Thread-safe Updates via asyncio.Lock
6. SSE Event Emission bei State Changes

**Datenstruktur:**
```python
@dataclass
class PipelineProgress:
    # Document Info
    document_id: str
    document_name: str
    total_chunks: int

    # Stage Progress
    chunking: StageProgress      # chunks_created, is_complete
    embedding: StageProgress     # chunks_embedded, in_flight, is_complete
    extraction: StageProgress    # chunks_extracted, in_flight, is_complete

    # Worker Pool Info
    active_workers: int
    max_workers: int
    queue_depth: int

    # Timing
    started_at: float
    stage_timings: dict[str, float]  # stage -> duration_ms

    # Entities (live count)
    entities_extracted: int
    relations_extracted: int
```

**Deliverables:**
- `src/components/ingestion/progress_manager.py` (neu)
- Updated SSE Events in `admin.py`

**Acceptance Criteria:**
- [ ] Progress Updates alle 500ms
- [ ] Korrekte Zählung pro Stage
- [ ] Worker Pool Status sichtbar
- [ ] Entity/Relation Count live

---

### Feature 37.4: Visual Pipeline Progress Component (13 SP)
**Priority:** P1 (Hoch)
**Beschreibung:** React-Komponente für grafische Pipeline-Visualisierung

**Design Mockup (mit VLM Stage):**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Document: DE-D-BasicAdministration.pdf (8.2 MB)                            │
│  Total Chunks: 32 | Images: 48 | Elapsed: 2:34 | Est. Remaining: 1:45       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Pipeline Stages ──────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │ │
│  │  │ Parsing  │──►│   VLM    │──►│ Chunking │──►│Embedding │            │ │
│  │  │ ████████ │   │ ██████░░ │   │ ████████ │   │ ██████░░ │            │ │
│  │  │  1/1 ✓   │   │ 38/48 🖼  │   │ 32/32 ✓  │   │  28/32   │            │ │
│  │  │  4:52    │   │  1:23    │   │  0.8s    │   │  12.4s   │            │ │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘            │ │
│  │        │                                            │                  │ │
│  │        └────────────────────────────────────────────┼──────────────┐   │ │
│  │                                                     ▼              │   │ │
│  │                                              ┌──────────┐          │   │ │
│  │                                              │Extraction│◄─────────┘   │ │
│  │                                              │ ████░░░░ │              │ │
│  │                                              │  18/32   │              │ │
│  │                                              │  45.2s   │              │ │
│  │                                              └──────────┘              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Worker Pools ─────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  VLM Workers (1):     [V1: ████████░░]  Queue: 10 images              │ │
│  │  Embed Workers (2):   [E1: ████] [E2: ██░░]  Queue: 4 chunks          │ │
│  │  Extract Workers (4): [X1: ██] [X2: ██] [X3: ░░] [X4: ░░]  Queue: 6   │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Live Metrics ─────────────────────────────────────────────────────────┐ │
│  │  Entities: 127 (+12) | Relations: 89 (+8) | Images Described: 38      │ │
│  │  Qdrant: 28 vectors | Neo4j: 216 writes | LLM Calls: 52               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Configuration ───────────────────────────────────────────── [⚙️ Edit] ┐ │
│  │  VLM: 1 worker | Embed: 2 workers | Extract: 4 workers                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Kompakte Ansicht (Mobile/Collapsed):**
```
┌────────────────────────────────────────────────┐
│ DE-D-BasicAdministration.pdf                   │
│ ████████████████████░░░░░░░░ 68%  ETA: 1:45   │
├────────────────────────────────────────────────┤
│ Parse ✓ → VLM 79% → Chunk ✓ → Embed → Extract │
│ Workers: V1 E2 X4 | Entities: 127 | Rel: 89   │
└────────────────────────────────────────────────┘
```

**Technical Tasks:**
1. `PipelineProgressVisualization.tsx` Komponente
2. Stage-Progress-Bars mit Animation
3. Worker Pool Visualisierung
4. Live Entity/Relation Counter
5. Time Elapsed / Estimated Remaining
6. Responsive Design (Mobile-friendly)
7. Dark Mode Support

**Deliverables:**
- `frontend/src/components/admin/PipelineProgressVisualization.tsx`
- `frontend/src/components/admin/StageProgressBar.tsx`
- `frontend/src/components/admin/WorkerPoolDisplay.tsx`
- `frontend/src/hooks/usePipelineProgress.ts`

**Acceptance Criteria:**
- [ ] Alle 3 Stages visuell dargestellt
- [ ] Progress-Bars animiert (smooth transitions)
- [ ] Worker Pool Status live aktualisiert
- [ ] Entity/Relation Count mit Delta-Anzeige
- [ ] Responsive für Desktop und Mobile
- [ ] 21 data-testid Attribute für E2E Tests

---

### Feature 37.5: Backend SSE Streaming Updates (5 SP)
**Priority:** P1 (Hoch)
**Beschreibung:** Erweiterte SSE Events für Visual Progress

**Neue SSE Event Struktur:**
```typescript
interface PipelineProgressEvent {
  type: "pipeline_progress";
  data: {
    document_id: string;
    document_name: string;
    total_chunks: number;

    stages: {
      chunking: {
        processed: number;
        total: number;
        status: "pending" | "in_progress" | "completed";
        duration_ms: number;
      };
      embedding: {
        processed: number;
        total: number;
        in_flight: number;
        status: "pending" | "in_progress" | "completed";
        duration_ms: number;
      };
      extraction: {
        processed: number;
        total: number;
        in_flight: number;
        status: "pending" | "in_progress" | "completed";
        duration_ms: number;
      };
    };

    worker_pool: {
      active: number;
      max: number;
      queue_depth: number;
      workers: Array<{
        id: number;
        status: "idle" | "processing" | "error";
        current_chunk?: string;
        progress_percent?: number;
      }>;
    };

    metrics: {
      entities_total: number;
      entities_delta: number;
      relations_total: number;
      relations_delta: number;
      neo4j_writes: number;
    };

    timing: {
      started_at: number;
      elapsed_ms: number;
      estimated_remaining_ms: number;
    };
  };
}
```

**Technical Tasks:**
1. SSE Event Schema definieren
2. Progress Manager → SSE Bridge
3. Throttling (max 2 events/sec)
4. Delta-Berechnung für Metrics
5. ETA-Berechnung basierend auf Durchsatz

**Deliverables:**
- Updated `src/api/v1/admin.py`
- `src/api/v1/schemas/pipeline_progress.py` (neu)

**Acceptance Criteria:**
- [ ] SSE Events alle 500ms
- [ ] Korrekte Delta-Berechnung
- [ ] ETA-Berechnung mit <10% Fehler
- [ ] Keine SSE-Überlastung (Throttling)

---

### Feature 37.6: Integration Tests für Streaming Pipeline (5 SP)
**Priority:** P1 (Hoch)
**Beschreibung:** Comprehensive Tests für die neue Pipeline-Architektur

**Test Cases:**
1. Single Chunk Pipeline Flow
2. Multi-Chunk Parallel Processing
3. Worker Pool Scaling (1, 2, 4 workers)
4. Error Recovery (einzelner Chunk fehlschlägt)
5. Memory Leak Detection (100 Chunks)
6. SSE Event Ordering
7. Progress Accuracy Validation

**Deliverables:**
- `tests/integration/test_streaming_pipeline.py`
- `tests/integration/test_worker_pool.py`

**Acceptance Criteria:**
- [ ] 15+ Integration Tests
- [ ] >90% Code Coverage für neue Module
- [ ] CI/CD Pipeline grün

---

### Feature 37.7: Admin UI für Worker Pool Konfiguration (8 SP)
**Priority:** P1 (Hoch)
**Beschreibung:** Vollständige Konfigurierbarkeit aller Worker-Parameter direkt in der Admin-Oberfläche

**Design Mockup:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Pipeline Configuration                                        [Save] [Reset]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Document Processing ───────────────────────────────────────────────────┐│
│  │  Parallel Documents:    [▼ 2 ]  (1-4)   "Process multiple docs at once" ││
│  │  Max Queue Size:        [▼ 10]  (5-50)  "Backpressure limit"            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ VLM Image Processing ──────────────────────────────────────────────────┐│
│  │  VLM Workers:           [▼ 1 ]  (1-2)   "GPU-bound, keep low"           ││
│  │  Batch Size:            [▼ 4 ]  (1-8)   "Images per VLM call"           ││
│  │  Timeout (sec):         [▼ 180] (60-300)"Per batch timeout"             ││
│  │  Max Images per Doc:    [▼ 50]  (10-200)"Limit for large PDFs"          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Embedding Generation ──────────────────────────────────────────────────┐│
│  │  Embedding Workers:     [▼ 2 ]  (1-4)   "Parallel embedding tasks"      ││
│  │  Batch Size:            [▼ 8 ]  (4-32)  "Chunks per embedding call"     ││
│  │  Timeout (sec):         [▼ 60]  (30-120)"Per batch timeout"             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Entity/Relation Extraction ────────────────────────────────────────────┐│
│  │  Extraction Workers:    [▼ 4 ]  (1-8)   "Parallel LLM calls"            ││
│  │  Timeout (sec):         [▼ 120] (60-300)"Per chunk timeout"             ││
│  │  Max Retries:           [▼ 2 ]  (0-3)   "Retry failed chunks"           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Resource Limits ───────────────────────────────────────────────────────┐│
│  │  Max Concurrent LLM:    [▼ 8 ]  (4-16)  "Total across all workers"      ││
│  │  Max VRAM (MB):         [▼ 5500](4000-6000)"GPU memory limit"           ││
│  │  Max RAM (MB):          [▼ 4000](2000-8000)"System memory limit"        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Presets ───────────────────────────────────────────────────────────────┐│
│  │  [Conservative]  [Balanced]  [Aggressive]  [Custom]                     ││
│  │   (1 doc, safe)  (2 docs)    (3 docs, fast) (current)                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  Current Hardware: NVIDIA GB10 (8GB VRAM) | 128GB RAM | 10 Cores           │
│  Recommended Preset: [Balanced] based on detected hardware                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Technical Tasks:**
1. `PipelineConfigPanel.tsx` Komponente
2. Slider/Dropdown für jeden Parameter
3. Preset-Buttons (Conservative, Balanced, Aggressive)
4. Hardware-Erkennung API (`GET /api/v1/admin/hardware`)
5. Live-Validation (zeige Warnings bei zu aggressiven Settings)
6. Persist to Backend (`POST /api/v1/admin/pipeline/config`)
7. Config Reset to Defaults

**API Endpoints (neu):**
```python
# GET /api/v1/admin/pipeline/config
# Returns current config + hardware info + recommendations

# POST /api/v1/admin/pipeline/config
# Update config (validates against hardware limits)

# GET /api/v1/admin/hardware
# Returns detected GPU, RAM, CPU info

# POST /api/v1/admin/pipeline/config/preset/{preset_name}
# Apply preset (conservative, balanced, aggressive)
```

**Deliverables:**
- `frontend/src/components/admin/PipelineConfigPanel.tsx`
- `frontend/src/components/admin/WorkerConfigSlider.tsx`
- `frontend/src/components/admin/PresetSelector.tsx`
- `src/api/v1/admin.py` (neue Endpoints)
- `src/core/pipeline_config.py` (Config Management)

**Acceptance Criteria:**
- [ ] Alle Worker-Parameter konfigurierbar
- [ ] Presets funktionieren
- [ ] Hardware-Erkennung zeigt GPU/RAM
- [ ] Validation verhindert ungültige Kombinationen
- [ ] Settings persistieren (Redis oder SQLite)
- [ ] 15 data-testid Attribute für E2E Tests

---

### Feature 37.8: Multi-Dokument Parallelisierung (8 SP)
**Priority:** P1 (Hoch)
**Beschreibung:** Aktivierung und Integration des existierenden `ParallelIngestionOrchestrator`

**Aktueller Stand:**
- `ParallelIngestionOrchestrator` existiert (Sprint 33)
- `PARALLEL_FILES=3` ist bereits konfiguriert
- **ABER:** Admin API nutzt sequentielles `run_batch_ingestion`

**Technical Tasks:**
1. Admin API auf `ParallelIngestionOrchestrator` umstellen
2. SSE Progress Aggregation für mehrere Dokumente
3. Document-Level Progress Tracking
4. Resource Semaphore für VRAM-Sharing
5. Error Isolation (ein Dokument-Fehler stoppt nicht andere)
6. Visual Progress für Multi-Dokument

**Visual Progress (Multi-Document):**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Batch: 3 Documents | Parallel: 2 | Elapsed: 3:45                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Document 1: report.pdf (2.1 MB) ───────────────────────────── [100%] ✓ │
│  │  Parse ✓ → VLM ✓ → Chunk ✓ → Embed ✓ → Extract ✓                       │
│  │  32 chunks | 127 entities | 89 relations | 2:12                         │
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Document 2: manual.pdf (5.4 MB) ────────────────────────────── [68%] ◐ │
│  │  Parse ✓ → VLM ✓ → Chunk ✓ → Embed 78% → Extract 45%                   │
│  │  48 chunks | 89 entities | 52 relations | 1:33 remaining                │
│  │  Workers: [X1: ██] [X2: ██] [X3: ░░] [X4: ░░]                           │
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Document 3: specs.docx (1.2 MB) ────────────────────────────── [23%] ◔ │
│  │  Parse ✓ → VLM 50% → Chunk pending → Embed pending → Extract pending    │
│  │  0 chunks | 0 entities | 0 relations | waiting...                       │
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Queue ──────────────────────────────────────────────────────────────── │
│  │  Waiting: 0 documents | Active: 2 | Completed: 1 | Failed: 0            │
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Deliverables:**
- Updated `src/api/v1/admin.py` (ParallelIngestionOrchestrator integration)
- `src/components/ingestion/multi_doc_progress.py` (Progress Aggregation)
- `frontend/src/components/admin/MultiDocumentProgress.tsx`
- `frontend/src/components/admin/DocumentProgressCard.tsx`

**Acceptance Criteria:**
- [ ] 2-3 Dokumente parallel verarbeitbar
- [ ] Jedes Dokument hat eigenen Progress-Status
- [ ] VRAM wird fair geteilt (Semaphore)
- [ ] Ein Fehler stoppt nicht andere Dokumente
- [ ] Gesamtfortschritt korrekt aggregiert

---

### Feature 37.9: E2E Tests für Visual Progress (5 SP)
**Priority:** P2 (Mittel)
**Beschreibung:** Playwright E2E Tests für die neue Visualisierung

**Test Cases:**
1. Progress Bars update correctly
2. Worker Pool display updates
3. Entity/Relation counters increment
4. Time elapsed updates
5. Completion state displays correctly

**Deliverables:**
- `frontend/e2e/tests/admin/pipeline-progress.spec.ts`

**Acceptance Criteria:**
- [ ] 10 E2E Tests
- [ ] All data-testid attributes verified
- [ ] Mobile responsive test

---

## Sprint Timeline

```
Day 1 (2025-12-07):
├── Feature 37.1: Streaming Pipeline Architecture (Start)
├── Feature 37.2: Worker Pool (Start)
└── Feature 37.3: Progress Manager (Start)

Day 2 (2025-12-08):
├── Feature 37.1: Streaming Pipeline (Complete)
├── Feature 37.2: Worker Pool (Complete)
├── Feature 37.3: Progress Manager (Complete)
└── Feature 37.5: SSE Updates (Start)

Day 3 (2025-12-09):
├── Feature 37.4: Visual Progress Component (Start)
├── Feature 37.5: SSE Updates (Complete)
└── Feature 37.6: Integration Tests (Start)

Day 4 (2025-12-10):
├── Feature 37.4: Visual Progress Component (Complete)
├── Feature 37.6: Integration Tests (Complete)
├── Feature 37.7: E2E Tests (Complete)
└── Sprint Review & Demo
```

---

## Technical Architecture

### Architektur-Entscheidung: LangGraph vs Pure AsyncIO

**Frage:** Bleibt die Streaming-Pipeline in LangGraph oder wird sie ein separater Mechanismus?

**Empfehlung:** **Hybrid-Ansatz** - LangGraph für Orchestrierung, AsyncIO für Parallelisierung

#### Option 1: Pure LangGraph (Send API)
```python
# LangGraph Send API für Fan-Out
def route_chunks_to_workers(state: IngestionState) -> list[Send]:
    return [Send("extract_chunk", {"chunk": c}) for c in state["chunks"]]
```
**Vorteile:**
- Konsistent mit bestehender Architektur
- LangGraph Tracing/Debugging
- State Management eingebaut

**Nachteile:**
- Send API wartet bis ALLE Fan-Out Tasks fertig → kein echtes Streaming
- Kein Backpressure-Handling
- Schwieriger: Worker Pool mit dynamischer Größe

#### Option 2: Pure AsyncIO (Queues)
```python
# AsyncIO Queues für Streaming
chunk_queue = asyncio.Queue(maxsize=10)
await asyncio.gather(producer(), consumer())
```
**Vorteile:**
- Echtes Streaming (kein Warten auf alle Chunks)
- Backpressure eingebaut (Queue maxsize)
- Flexible Worker Pool Konfiguration

**Nachteile:**
- Separate von LangGraph → zwei Systeme
- Kein LangSmith Tracing
- State Management manuell

#### Option 3: Hybrid (EMPFOHLEN) ✅
```python
# LangGraph für High-Level Flow
graph.add_node("parse", docling_parse_node)
graph.add_node("process_parallel", streaming_processor_node)  # ← Wrapper
graph.add_node("finalize", finalize_node)

# AsyncIO INNERHALB des LangGraph Nodes
async def streaming_processor_node(state: IngestionState) -> IngestionState:
    """LangGraph Node der intern AsyncIO Streaming nutzt."""
    orchestrator = StreamingPipelineOrchestrator(
        vlm_workers=settings.VLM_WORKERS,
        embedding_workers=settings.EMBEDDING_WORKERS,
        extraction_workers=settings.GRAPH_EXTRACTION_WORKERS,
    )

    # Streaming mit Queues INNERHALB des Nodes
    result = await orchestrator.process(
        chunks=state["chunks"],
        images=state["images"],
        progress_callback=emit_sse_progress,
    )

    return {**state, **result}
```

**Vorteile des Hybrid-Ansatzes:**
- ✅ LangGraph bleibt der Entry Point (Konsistenz)
- ✅ LangSmith Tracing für High-Level Flow
- ✅ AsyncIO Queues für echtes Streaming
- ✅ Backpressure und Worker Pool Kontrolle
- ✅ Bestehende Pipeline kann schrittweise migriert werden
- ✅ Ein Node im Graph = gesamte Parallel-Verarbeitung

**Architektur-Diagramm (Hybrid):**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LangGraph StateGraph                            │
│                                                                         │
│  ┌──────────┐   ┌──────────┐   ┌───────────────────────┐   ┌────────┐ │
│  │  parse   │──►│   vlm    │──►│  streaming_processor  │──►│finalize│ │
│  │ (Docling)│   │ (images) │   │    (AsyncIO intern)   │   │        │ │
│  └──────────┘   └──────────┘   └───────────────────────┘   └────────┘ │
│                                          │                             │
│                                          ▼                             │
│                        ┌─────────────────────────────────────┐         │
│                        │  StreamingPipelineOrchestrator      │         │
│                        │  (Pure AsyncIO, NICHT LangGraph)    │         │
│                        │                                     │         │
│                        │  ┌─────────┐ Queue ┌─────────┐     │         │
│                        │  │Chunking │──────►│Embedding│     │         │
│                        │  └─────────┘       └────┬────┘     │         │
│                        │                         │ Queue    │         │
│                        │                         ▼          │         │
│                        │               ┌─────────────────┐  │         │
│                        │               │ Extraction Pool │  │         │
│                        │               │ [W1][W2][W3][W4]│  │         │
│                        │               └─────────────────┘  │         │
│                        └─────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Flow Diagram
```
                                    ┌─────────────────────────────────────┐
                                    │      PipelineProgressManager        │
                                    │   (Singleton, Thread-safe State)    │
                                    └──────────────┬──────────────────────┘
                                                   │ SSE Events
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        StreamingPipelineOrchestrator                      │
│                                                                          │
│  ┌─────────────┐   Queue    ┌─────────────┐   Queue    ┌──────────────┐ │
│  │  Chunking   │──────────►│  Embedding  │──────────►│  Extraction   │ │
│  │   Stage     │ (max=10)  │    Stage    │ (max=10)  │  Worker Pool  │ │
│  │             │           │             │           │   (4 workers) │ │
│  └─────────────┘           └─────────────┘           └──────────────┘ │
│        │                         │                         │          │
│        └─────────────────────────┴─────────────────────────┘          │
│                                  │                                     │
│                                  ▼                                     │
│                        Progress Updates → Manager                      │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              PipelineProgressVisualization Component               │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐                     │ │
│  │  │ Chunking │───►│Embedding │───►│Extraction│                     │ │
│  │  │ ████████ │    │ ██████░░ │    │ ████░░░░ │                     │ │
│  │  └──────────┘    └──────────┘    └──────────┘                     │ │
│  │                                                                    │ │
│  │  Worker Pool: [W1: ██] [W2: ██] [W3: ░░] [W4: ░░]                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### File Structure (New Files)
```
src/components/ingestion/
├── streaming_pipeline.py          # Feature 37.1
├── pipeline_queues.py             # Feature 37.1
├── extraction_worker_pool.py      # Feature 37.2
└── progress_manager.py            # Feature 37.3

src/api/v1/schemas/
└── pipeline_progress.py           # Feature 37.5

frontend/src/components/admin/
├── PipelineProgressVisualization.tsx   # Feature 37.4
├── StageProgressBar.tsx                # Feature 37.4
└── WorkerPoolDisplay.tsx               # Feature 37.4

frontend/src/hooks/
└── usePipelineProgress.ts         # Feature 37.4

tests/integration/
├── test_streaming_pipeline.py     # Feature 37.6
└── test_worker_pool.py            # Feature 37.6

frontend/e2e/tests/admin/
└── pipeline-progress.spec.ts      # Feature 37.7
```

---

## Configuration

### New Environment Variables
```bash
# ============================================
# WORKER POOL CONFIGURATION (Fully Adjustable)
# ============================================

# Graph Extraction Workers
GRAPH_EXTRACTION_WORKERS=4          # Parallel LLM workers (1-8 empfohlen)
EXTRACTION_WORKER_TIMEOUT=120       # Seconds per chunk timeout
EXTRACTION_MAX_RETRIES=2            # Retries per failed chunk
EXTRACTION_BATCH_SIZE=1             # Chunks per LLM call (1 = streaming)

# Embedding Workers
EMBEDDING_WORKERS=2                 # Parallel embedding workers
EMBEDDING_BATCH_SIZE=8              # Chunks per embedding batch (BGE-M3)
EMBEDDING_WORKER_TIMEOUT=60         # Seconds per batch

# VLM Workers (Image Enrichment)
VLM_WORKERS=1                       # Parallel VLM workers (GPU-bound)
VLM_BATCH_SIZE=4                    # Images per VLM batch
VLM_WORKER_TIMEOUT=180              # Seconds per batch (images are slow)
VLM_MAX_IMAGES_PER_DOC=50           # Limit images to process

# ============================================
# QUEUE CONFIGURATION
# ============================================
CHUNK_QUEUE_MAX_SIZE=10             # Max chunks waiting for embedding
EMBEDDING_QUEUE_MAX_SIZE=10         # Max chunks waiting for extraction
VLM_QUEUE_MAX_SIZE=20               # Max images waiting for VLM

# Queue Backpressure
QUEUE_BACKPRESSURE_THRESHOLD=0.8    # Start slowing down at 80% full
QUEUE_BACKPRESSURE_DELAY_MS=100     # Delay when backpressure triggered

# ============================================
# SSE CONFIGURATION
# ============================================
SSE_PROGRESS_THROTTLE_MS=500        # Min interval between SSE events
SSE_METRICS_DELTA_WINDOW=5          # Seconds for delta calculation

# ============================================
# RESOURCE LIMITS
# ============================================
MAX_CONCURRENT_LLM_CALLS=8          # Total across all workers
MAX_VRAM_USAGE_MB=5500              # VRAM limit for semaphore
MAX_RAM_USAGE_MB=4000               # RAM limit for queue sizing
```

### Runtime Configuration API (Feature 37.2.1)
```python
# POST /api/v1/admin/pipeline/config
{
    "graph_extraction_workers": 4,
    "embedding_workers": 2,
    "vlm_workers": 1,
    "queue_sizes": {
        "chunk": 10,
        "embedding": 10,
        "vlm": 20
    }
}

# GET /api/v1/admin/pipeline/config
# Returns current configuration + recommendations based on hardware
```

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Pipeline Duration (32 chunks) | 17 min | 3 min | End-to-end timing |
| Graph Extraction Speedup | 1x | 4x | Phase timing |
| Memory Usage | 4GB | <4GB | Peak RAM |
| SSE Latency | N/A | <100ms | Event timing |
| Test Coverage | N/A | >90% | pytest-cov |

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| VRAM Overflow mit 4 Workers | Medium | High | Semaphore, reduce to 2 workers |
| Queue Backpressure | Low | Medium | Queue size limits, backoff |
| Entity Deduplication Errors | Medium | Low | Neo4j MERGE semantics |
| SSE Connection Drops | Low | Low | Auto-reconnect in frontend |
| Ollama Rate Limiting | Low | Medium | Exponential backoff |

---

## Definition of Done

- [ ] All features implemented and tested
- [ ] Integration tests passing (>90% coverage)
- [ ] E2E tests passing
- [ ] Visual Progress Component responsive
- [ ] SSE Events <100ms latency
- [ ] Pipeline 4-6x faster than baseline
- [ ] Documentation updated (CLAUDE.md, ADR)
- [ ] Demo video recorded

---

## Dependencies

- Sprint 36: Qwen3 `think=False` Fix (completed)
- LangGraph Send API understanding
- AsyncIO Queue expertise
- React animation libraries (framer-motion optional)
