# Sprint 36: Pipeline Parallelisierungs-Konzept

**Date:** 2025-12-06
**Author:** Claude Code
**Status:** KONZEPT (zur Diskussion)

## 1. Aktuelle Architektur-Analyse

### 1.1 Sequentieller Pipeline-Flow
```
START
  |
memory_check_node (5%)
  |
parse_node [docling/llamaindex] (20%)
  |
image_enrichment_node [VLM] (35%)
  |
chunking_node (50%)
  |
embedding_node (75%)
  |
graph_extraction_node (100%)
  |
END
```

### 1.2 Zeitmessungen (406-Seiten PDF)
| Phase | Dauer | Bottleneck |
|-------|-------|------------|
| Docling Parsing | ~5 min | GPU (OCR) |
| VLM Enrichment | ~0.5 min | GPU (qwen3-vl) |
| Chunking | ~0.1 min | CPU |
| Embedding | ~1 min | GPU (BGE-M3) |
| Graph Extraction | ~10 min | LLM (Qwen3:32b) |

**Hauptbottleneck:** Graph Extraction (Entity/Relation Extraction via LLM)

### 1.3 Aktuelle Memory-Constraints
- **RAM Limit:** 4.4GB (IngestionState)
- **VRAM Limit:** 6GB (RTX 3060 / GB10)
- **Container Isolation:** Docling Container separate VRAM

## 2. Parallelisierungs-Optionen

### Option A: Chunk-Level Parallelisierung (Empfohlen)
**Konzept:** Parallelisiere LLM-Calls innerhalb des Graph Extraction Nodes

```
                        ┌─────────────────────────────────────┐
                        │         graph_extraction_node       │
                        │                                     │
                        │   ┌────────┐ ┌────────┐ ┌────────┐ │
Chunks ──────────────►  │   │ Chunk1 │ │ Chunk2 │ │ Chunk3 │ │
(z.B. 32 Chunks)        │   │  LLM   │ │  LLM   │ │  LLM   │ │
                        │   └────────┘ └────────┘ └────────┘ │
                        │        │          │          │     │
                        │        ▼          ▼          ▼     │
                        │   ┌────────────────────────────┐   │
                        │   │   Merge Entities/Relations │   │
                        │   └────────────────────────────┘   │
                        └─────────────────────────────────────┘
```

**Vorteile:**
- Größter Performance-Gewinn (Graph Extraction ist 60% der Gesamtzeit)
- Keine Änderung der Pipeline-Architektur nötig
- Einfache Implementierung mit `asyncio.gather()`

**Implementierung:**
```python
async def graph_extraction_node_parallel(state: IngestionState) -> IngestionState:
    chunks = state["chunks"]
    batch_size = 4  # 4 parallele LLM Calls

    all_entities = []
    all_relations = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]

        # Parallel extraction
        results = await asyncio.gather(*[
            extract_entities_and_relations(chunk)
            for chunk in batch
        ])

        for entities, relations in results:
            all_entities.extend(entities)
            all_relations.extend(relations)

    return {**state, "entities": all_entities, "relations": all_relations}
```

**Erwarteter Speedup:** 3-4x für Graph Extraction
- 32 Chunks / 4 parallel = 8 Batches
- Statt 32 sequentiellen LLM Calls nur 8

---

### Option A.2: Streaming Pipeline (Chunk-Level Pipelining) - SEHR EMPFOHLEN
**Konzept:** Sobald ein Chunk erstellt ist, sofort in die nächste Stage schicken

```
Zeit ──────────────────────────────────────────────────────────────────►

         Chunking    Embedding    Graph Extraction
         ────────    ─────────    ────────────────
Chunk 1: [████]─────►[████]──────►[████████████]
Chunk 2:    [████]───►[████]──────►[████████████]
Chunk 3:       [████]─►[████]──────►[████████████]
Chunk 4:          [████]►[████]────►[████████████]
...

Statt:
         Chunking         Embedding              Graph Extraction
         ────────         ─────────              ────────────────
All:     [████████████]──►[████████████████]────►[████████████████████████████]
```

**Vorteile:**
- **Maximale Parallelität:** Alle Stages arbeiten gleichzeitig
- **Reduzierte Latenz:** Erste Ergebnisse früher verfügbar
- **Bessere GPU-Auslastung:** Embedding und LLM können parallel laufen

**Implementierung mit AsyncIO Queues:**
```python
import asyncio
from asyncio import Queue

async def streaming_pipeline(document_path: str):
    # Queues für Inter-Stage Kommunikation
    chunk_queue: Queue[Chunk] = Queue(maxsize=10)
    embedding_queue: Queue[EmbeddedChunk] = Queue(maxsize=10)

    # Sentinel für "fertig"
    DONE = object()

    async def chunking_stage():
        """Erzeugt Chunks und schiebt sie in die Queue."""
        async for chunk in create_chunks_streaming(document_path):
            await chunk_queue.put(chunk)
            logger.info(f"Chunk {chunk.id} -> Queue")
        await chunk_queue.put(DONE)

    async def embedding_stage():
        """Holt Chunks, erstellt Embeddings, schiebt weiter."""
        while True:
            chunk = await chunk_queue.get()
            if chunk is DONE:
                await embedding_queue.put(DONE)
                break

            embedding = await embed_chunk(chunk)
            await embedding_queue.put(embedding)
            logger.info(f"Chunk {chunk.id} embedded")

    async def graph_extraction_stage():
        """Holt embedded Chunks, extrahiert Entities."""
        while True:
            embedded = await embedding_queue.get()
            if embedded is DONE:
                break

            entities = await extract_entities(embedded)
            await store_in_neo4j(entities)
            logger.info(f"Chunk {embedded.id} -> Neo4j")

    # Alle Stages parallel starten
    await asyncio.gather(
        chunking_stage(),
        embedding_stage(),
        graph_extraction_stage(),
    )
```

**Erweiterung mit Worker Pool für Graph Extraction:**
```python
async def graph_extraction_stage_parallel(num_workers: int = 4):
    """Parallel Graph Extraction mit Worker Pool."""
    semaphore = asyncio.Semaphore(num_workers)
    tasks = []

    async def process_one(embedded):
        async with semaphore:
            entities = await extract_entities(embedded)
            await store_in_neo4j(entities)

    while True:
        embedded = await embedding_queue.get()
        if embedded is DONE:
            # Warten bis alle Tasks fertig
            await asyncio.gather(*tasks)
            break

        task = asyncio.create_task(process_one(embedded))
        tasks.append(task)
```

**Erwarteter Speedup:** 4-6x (kombiniert Streaming + Parallelisierung)

**LangGraph Implementation mit Send API:**
```python
from langgraph.graph import StateGraph, Send

def create_streaming_graph():
    graph = StateGraph(IngestionState)

    # Fan-out: Jeder Chunk wird parallel verarbeitet
    def route_to_embedding(state: IngestionState) -> list[Send]:
        return [
            Send("embed_chunk", {"chunk": c, "index": i})
            for i, c in enumerate(state["chunks"])
        ]

    def route_to_extraction(state: IngestionState) -> list[Send]:
        return [
            Send("extract_entities", {"embedded_chunk": e, "index": i})
            for i, e in enumerate(state["embedded_chunks"])
        ]

    graph.add_node("parse", docling_parse_node)
    graph.add_node("chunk", chunking_node)
    graph.add_node("embed_chunk", embed_single_chunk)  # Pro Chunk!
    graph.add_node("extract_entities", extract_single_chunk)  # Pro Chunk!
    graph.add_node("merge_results", merge_all_results)

    graph.add_conditional_edges("chunk", route_to_embedding)
    graph.add_conditional_edges("embed_chunk", route_to_extraction)
    graph.add_edge("extract_entities", "merge_results")

    return graph.compile()
```

---

### Option B: Stage-Level Parallelisierung
**Konzept:** Parallele Ausführung unabhängiger Stages für verschiedene Chunks

```
         ┌──────────────────────────────────────────────────────────────┐
         │                   Streaming Pipeline                         │
         │                                                              │
Chunk 1: │ [Embed]──────►[Graph Extract]                               │
Chunk 2: │       [Embed]──────►[Graph Extract]                         │
Chunk 3: │             [Embed]──────►[Graph Extract]                   │
Chunk 4: │                   [Embed]──────►[Graph Extract]             │
         └──────────────────────────────────────────────────────────────┘
```

**Vorteile:**
- GPU-Auslastung wird maximiert (Embedding & LLM parallel)
- Kein Warten zwischen Stages

**Nachteile:**
- Komplexere State-Verwaltung
- Potentielle VRAM-Konflikte (Embedding + LLM gleichzeitig)
- Erfordert Pipeline-Umbau

**Implementation mit LangGraph Send API:**
```python
from langgraph.graph import Send

def route_chunks(state: IngestionState) -> list[Send]:
    """Fan-out: Send each chunk to parallel processing."""
    return [
        Send("process_chunk", {"chunk": chunk, "index": i})
        for i, chunk in enumerate(state["chunks"])
    ]
```

---

### Option C: Document-Level Parallelisierung
**Konzept:** Mehrere Dokumente gleichzeitig verarbeiten

```
Doc 1: ─────►[Parse]───►[Chunk]───►[Embed]───►[Graph]───►
Doc 2:       ─────►[Parse]───►[Chunk]───►[Embed]───►[Graph]───►
Doc 3:             ─────►[Parse]───►[Chunk]───►[Embed]───►[Graph]───►
```

**Vorteile:**
- Einfach zu implementieren (run_batch_ingestion existiert bereits)
- Natürliche Ressourcen-Isolation

**Nachteile:**
- Benötigt mehr RAM (mehrere IngestionStates)
- VRAM-Konflikte bei GPU-intensiven Stages
- Nicht hilfreich für einzelne große Dokumente

**Aktueller Status:** Bereits als `run_batch_ingestion()` vorhanden, aber sequentiell.

---

### Option D: Hybrid-Ansatz (Empfehlung für DGX Spark)
**Konzept:** Kombiniere Chunk-Level + Document-Level für maximale Auslastung

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DGX Spark (128GB RAM, GB10 GPU)              │
│                                                                     │
│  Document Pipeline 1:                                               │
│    ┌─────────┐    ┌─────────┐    ┌─────────────────────────┐       │
│    │ Docling │───►│ Chunking│───►│ Graph (4 LLM parallel) │        │
│    └─────────┘    └─────────┘    └─────────────────────────┘       │
│                                                                     │
│  Document Pipeline 2:                                               │
│    ┌─────────┐    ┌─────────┐    ┌─────────────────────────┐       │
│    │ Docling │───►│ Chunking│───►│ Graph (4 LLM parallel) │        │
│    └─────────┘    └─────────┘    └─────────────────────────┘       │
│                                                                     │
│  Shared Resources:                                                  │
│    - Qdrant (Embedding Storage)                                     │
│    - Neo4j (Graph Storage)                                          │
│    - Ollama (Qwen3:32b - GPU VRAM shared)                          │
└─────────────────────────────────────────────────────────────────────┘
```

**Konfiguration:**
```yaml
# config/parallelization.yml
parallel_documents: 2          # Max 2 Docs gleichzeitig (RAM-Limit)
parallel_chunks_per_doc: 4     # 4 LLM Calls parallel pro Doc
ollama_max_concurrent: 8       # Total max concurrent LLM calls
embedding_batch_size: 16       # BGE-M3 Batch-Embedding
```

---

## 3. Empfohlene Implementierungsreihenfolge

### Phase 1: Quick Win - Chunk-Level Parallelisierung (Option A)
**Aufwand:** 1-2 Tage
**Speedup:** 3-4x für Graph Extraction

```python
# Änderung in langgraph_nodes.py

async def graph_extraction_node(state: IngestionState) -> IngestionState:
    chunks = state["chunks"]
    parallel_workers = settings.GRAPH_EXTRACTION_WORKERS  # Default: 4

    # Batch processing with semaphore
    semaphore = asyncio.Semaphore(parallel_workers)

    async def process_chunk(chunk):
        async with semaphore:
            return await extract_entities_and_relations(chunk)

    # Parallel extraction
    results = await asyncio.gather(*[process_chunk(c) for c in chunks])

    # Merge results
    all_entities = [e for r in results for e in r.entities]
    all_relations = [r for r in results for r in r.relations]

    return {**state, "entities": all_entities, "relations": all_relations}
```

**Neue Config-Optionen:**
```yaml
# .env
GRAPH_EXTRACTION_WORKERS=4
EMBEDDING_BATCH_SIZE=16
```

### Phase 2: Embedding Batching (Bonus)
**Aufwand:** 0.5 Tage
**Speedup:** 2x für Embedding

```python
async def embedding_node(state: IngestionState) -> IngestionState:
    chunks = state["chunks"]
    batch_size = settings.EMBEDDING_BATCH_SIZE  # Default: 16

    all_embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [c["text"] for c in batch]

        # Batch embedding (BGE-M3 unterstützt Batching)
        embeddings = await embedding_service.embed_batch(texts)
        all_embeddings.extend(embeddings)

    return {**state, "embeddings": all_embeddings}
```

### Phase 3: Document-Level Parallelisierung (Optional)
**Aufwand:** 2-3 Tage
**Speedup:** 2x für Multi-Document Batches

Erfordert:
- Semaphore für VRAM-Management
- Shared Qdrant/Neo4j Client Pool
- Progress Aggregation für SSE

---

## 4. Resource-Management

### 4.1 VRAM-Semaphore
```python
class VRAMSemaphore:
    """Manage VRAM allocation across parallel operations."""

    def __init__(self, total_vram_mb: int = 5500):
        self.total = total_vram_mb
        self.allocated = 0
        self.lock = asyncio.Lock()

    async def acquire(self, vram_mb: int):
        async with self.lock:
            while self.allocated + vram_mb > self.total:
                await asyncio.sleep(0.1)
            self.allocated += vram_mb

    async def release(self, vram_mb: int):
        async with self.lock:
            self.allocated -= vram_mb

# Usage
vram_semaphore = VRAMSemaphore(5500)  # 5.5GB safe limit

async def llm_call_with_vram(prompt: str):
    await vram_semaphore.acquire(1000)  # Qwen3:32b ~ 1GB per call
    try:
        return await llm_proxy.complete(prompt)
    finally:
        await vram_semaphore.release(1000)
```

### 4.2 Rate Limiting für Ollama
```python
from asyncio import Semaphore

# Ollama can handle ~8 concurrent requests safely
ollama_semaphore = Semaphore(8)

async def extract_entities_throttled(chunk):
    async with ollama_semaphore:
        return await extract_entities_and_relations(chunk)
```

---

## 5. Progress Tracking Update

### 5.1 Chunk-Level Progress für Frontend
```typescript
// frontend/src/types/admin.ts
interface DetailedProgress {
  // Existing...
  chunks_total: number;
  chunks_processed: number;

  // NEW: Parallel processing info
  parallel_workers: number;
  active_workers: number;
  chunks_in_flight: number;  // Currently being processed
}
```

### 5.2 Backend SSE Update
```python
async def graph_extraction_node_parallel(state: IngestionState) -> IngestionState:
    chunks = state["chunks"]

    async def process_with_progress(chunk, index):
        result = await extract_entities_and_relations(chunk)

        # Emit progress event
        await emit_sse_progress({
            "chunks_processed": index + 1,
            "chunks_total": len(chunks),
            "active_workers": current_active_count,
        })

        return result

    # ...
```

---

## 6. Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| VRAM Overflow | Mittel | Hoch | VRAMSemaphore, conservative limits |
| Rate Limiting Ollama | Niedrig | Mittel | Semaphore, exponential backoff |
| Entity Duplicates | Mittel | Niedrig | Deduplication in Neo4j merge |
| Neo4j Write Conflicts | Niedrig | Mittel | Batch writes, transaction retry |
| OOM bei großen Docs | Mittel | Hoch | Chunk streaming, nicht alle in RAM |

---

## 7. Erfolgsmetriken

### 7.1 Performance-Ziele
- **Graph Extraction:** 10 min → 3 min (3.3x Speedup)
- **Embedding:** 1 min → 0.5 min (2x Speedup)
- **Gesamt-Pipeline:** 17 min → 9 min (406-Seiten PDF)

### 7.2 Monitoring
```yaml
# Prometheus Metrics
aegis_pipeline_parallel_workers_active{stage="graph_extraction"}
aegis_pipeline_chunk_processing_rate{chunks_per_second}
aegis_pipeline_vram_utilization_percent
aegis_ollama_concurrent_requests
```

---

## 8. Nächste Schritte

1. **Entscheidung:** Option A (Chunk-Level) als Quick Win?
2. **Config:** GRAPH_EXTRACTION_WORKERS default value?
3. **Testing:** Benchmark mit 406-Seiten PDF vor/nach Parallelisierung
4. **Monitoring:** Grafana Dashboard für parallel worker metrics

---

## Anhang: Architektur-Diagramm (Ziel-Zustand)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AegisRAG Ingestion Pipeline                     │
│                           (Parallelized Architecture)                   │
│                                                                         │
│   ┌─────────┐   ┌────────────┐   ┌─────────────────────────────────┐   │
│   │ Docling │──►│  Chunking  │──►│      Graph Extraction           │   │
│   │ (GPU)   │   │  (CPU)     │   │  ┌─────────────────────────────┐│   │
│   └─────────┘   └────────────┘   │  │    Worker Pool (4)          ││   │
│        │                         │  │  ┌────┐┌────┐┌────┐┌────┐   ││   │
│        ▼                         │  │  │W1  ││W2  ││W3  ││W4  │   ││   │
│   ┌─────────┐                    │  │  │LLM ││LLM ││LLM ││LLM │   ││   │
│   │  Image  │                    │  │  └────┘└────┘└────┘└────┘   ││   │
│   │   VLM   │                    │  └─────────────────────────────┘│   │
│   │  (GPU)  │                    │              │                   │   │
│   └─────────┘                    │              ▼                   │   │
│        │                         │  ┌─────────────────────────────┐│   │
│        ▼                         │  │   Entity/Relation Merge     ││   │
│   ┌─────────┐                    │  └─────────────────────────────┘│   │
│   │Embedding│                    └─────────────────────────────────┘   │
│   │ BGE-M3  │                                    │                     │
│   │  (GPU)  │                                    ▼                     │
│   │ Batch16 │                             ┌──────────┐                 │
│   └─────────┘                             │  Neo4j   │                 │
│        │                                  │  Graph   │                 │
│        ▼                                  └──────────┘                 │
│   ┌─────────┐                                                          │
│   │ Qdrant  │                                                          │
│   │ Vectors │                                                          │
│   └─────────┘                                                          │
│                                                                         │
│   Legend: ──► Sequential    ═══► Parallel Workers                      │
└─────────────────────────────────────────────────────────────────────────┘
```
