# Sprint 21: Container-Based Ingestion Pipeline with LangGraph Orchestration

**Status:** 📋 PLANNED (v2 - Container Architecture)
**Goal:** Memory-optimized document ingestion with Docling CUDA container + LangGraph state machine
**Duration:** 10 days (estimated)
**Prerequisites:** Sprint 20 complete, Docker + NVIDIA Container Toolkit installed
**Story Points:** 55 SP (increased from 42 SP due to container orchestration complexity)

---

## 🎯 Sprint Objectives

### **Primary Goals:**
1. **Docling as CUDA Docker Container** (not Python library) for memory isolation
2. **LangGraph State Machine** for sequential pipeline orchestration
3. **Memory-Optimized Service Rotation** (start/stop containers dynamically)
4. **Batch Processing** with progress tracking for React UI
5. **4-Stage Pipeline:** Docling → Chunking → Embeddings → Graph Extraction

### **Success Criteria:**
- ✅ Docling container processes documents with GPU acceleration
- ✅ LangGraph orchestrates 4 pipeline stages sequentially
- ✅ Memory stays <4.4GB RAM (service rotation working)
- ✅ Batch processing of 100+ documents without OOM
- ✅ React UI shows real-time ingestion progress
- ✅ Neo4j + Qdrant populated correctly
- ✅ Pipeline recoverable via Redis checkpointing (TD for later)

---

## 🏗️ New Architecture Overview

### **Container-Based Service Rotation**

```
MEMORY CONSTRAINTS:
- Available RAM: ~4.4GB
- GPU: RTX 3060, 6GB VRAM
- CPU: 8 cores (mostly idle)

STRATEGY: Sequential Stage Processing with Container Start/Stop

Stage 1: Docling Container (CUDA)
  docker-compose up docling
  → Process documents (PDF, PPTX, DOCX)
  → Output: JSON/Markdown
  docker-compose stop docling  # Free ~2GB RAM

Stage 2: Chunking (Ollama)
  → Text splitting with adaptive strategy
  → Output: Document chunks (1200-1800 tokens)

Stage 3: Embeddings (Ollama + BGE-M3)
  → Embed chunks
  → Upsert to Qdrant
  → Output: Vector IDs

Stage 4: Graph Extraction (Ollama + Gemma-3-4b)
  → Entity/Relation extraction
  → Insert to Neo4j via LightRAG
  → Output: Entity/Relation IDs
```

### **LangGraph State Machine**

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List

class IngestionState(TypedDict):
    # Document Info
    document_path: str
    document_id: str
    batch_id: str
    batch_index: int
    total_documents: int

    # Stage Results
    parsed_content: str               # Docling Output (Markdown)
    parsed_metadata: dict             # Pages, tables, images
    chunks: List[DocumentChunk]        # Chunking Output
    embedded_chunks: List[str]         # Qdrant IDs
    entities: List[Entity]             # Neo4j Entity IDs
    relations: List[Relation]          # Neo4j Relation IDs

    # Status Tracking (for React UI)
    docling_status: str                # "pending|running|completed|failed"
    chunking_status: str
    embedding_status: str
    graph_status: str
    overall_progress: float            # 0.0 - 1.0

    # Memory Management
    current_memory_mb: float
    requires_container_restart: bool

    # Error Handling
    errors: List[dict]
    retry_count: int
    max_retries: int

# Graph Construction
graph = StateGraph(IngestionState)
graph.add_node("memory_check", memory_check_node)
graph.add_node("docling", docling_processing_node)
graph.add_node("chunking", chunking_node)
graph.add_node("embedding", embedding_node)
graph.add_node("graph_extraction", graph_extraction_node)

# Flow
graph.add_edge(START, "memory_check")
graph.add_conditional_edges(
    "memory_check",
    should_proceed,
    {
        "proceed": "docling",
        "insufficient_memory": END
    }
)
graph.add_edge("docling", "chunking")
graph.add_edge("chunking", "embedding")
graph.add_edge("embedding", "graph_extraction")
graph.add_edge("graph_extraction", END)
```

---

## 📦 Sprint Features

### Feature 21.1: Docling CUDA Docker Container (13 SP)
**Priority:** HIGH - Foundation for ingestion
**Duration:** 3 days

#### **Problem:**
Docling as Python library would compete for RAM with Ollama, Neo4j, Qdrant. Container isolation enables memory-optimized service rotation.

#### **Solution:**
Standalone Docling container with NVIDIA CUDA support, managed by docker-compose profiles.

#### **Docker Compose Configuration**

```yaml
# docker-compose.yml
services:
  docling:
    image: docling/docling:latest-cuda  # CUDA-enabled image
    profiles:
      - ingestion
    runtime: nvidia
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - DOCLING_GPU_MEMORY_FRACTION=0.8  # 80% of 6GB VRAM
      - DOCLING_LAZY_LOADING=true         # Load models on-demand
      - DOCLING_ENABLE_OCR=true
      - DOCLING_ENABLE_LAYOUT=true
      - DOCLING_ENABLE_TABLES=true
    volumes:
      - ./data/documents:/input:ro        # Read-only input
      - ./data/parsed:/output             # Parsed output
      - docling-cache:/root/.cache        # Model cache (persistent)
    ports:
      - "8080:8080"                       # HTTP API
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: "no"                         # Manual start/stop

volumes:
  docling-cache:
    driver: local
```

#### **Docling API Integration**

```python
# src/components/ingestion/docling_client.py
import subprocess
import httpx
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

class DoclingContainerClient:
    """Client for Docling CUDA container with lifecycle management."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout

    async def start_container(self):
        """Start Docling container with docker-compose."""
        logger.info("Starting Docling container...")

        result = subprocess.run(
            ["docker-compose", "up", "-d", "docling"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to start Docling: {result.stderr}")

        # Wait for container ready
        await self._wait_for_ready()
        logger.info("Docling container ready")

    async def stop_container(self):
        """Stop Docling container to free memory."""
        logger.info("Stopping Docling container...")

        subprocess.run(
            ["docker-compose", "stop", "docling"],
            capture_output=True
        )

        logger.info("Docling container stopped, memory freed")

    async def _wait_for_ready(self, max_retries: int = 30):
        """Wait for Docling API to be ready."""
        for i in range(max_retries):
            try:
                response = await self.client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return
            except httpx.RequestError:
                pass

            await asyncio.sleep(2)

        raise TimeoutError("Docling container did not become ready")

    async def parse_document(self, file_path: Path) -> dict:
        """Parse document via Docling API.

        Returns:
            {
                "content": "Markdown text",
                "metadata": {
                    "pages": 10,
                    "tables": 5,
                    "images": 3
                }
            }
        """
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}

            response = await self.client.post(
                f"{self.base_url}/parse",
                files=files,
                data={"output_format": "markdown"}
            )

        if response.status_code != 200:
            raise ValueError(f"Docling parsing failed: {response.text}")

        return response.json()
```

#### **Tasks:**
- [ ] Create Docling CUDA Dockerfile (if not using official image)
- [ ] Add Docling service to `docker-compose.yml` with CUDA runtime
- [ ] Implement `DoclingContainerClient` with start/stop/parse methods
- [ ] Test GPU memory allocation (6GB VRAM, 80% limit)
- [ ] Test model caching (lazy loading, persistent volume)
- [ ] Benchmark: Parse 10-page PDF (target: <30s)
- [ ] Error handling: Container crash, OOM, timeout

#### **Deliverables:**
```bash
docker-compose.yml                     # Docling service definition
src/components/ingestion/docling_client.py  # Container client
tests/ingestion/test_docling_container.py   # Integration tests
docs/sprints/SPRINT_21_DOCLING_DOCKER.md    # Docker setup guide
```

#### **Acceptance Criteria:**
- ✅ Docling container starts with `docker-compose up docling`
- ✅ GPU acceleration verified (6GB VRAM utilized)
- ✅ Parse PDF (10 pages) in <30s with GPU
- ✅ Container stop frees ~2GB RAM (verified with `docker stats`)
- ✅ Model cache persistent across restarts
- ✅ Error handling graceful (container crash, parse failure)

---

### Feature 21.2: LangGraph Ingestion State Machine (21 SP)
**Priority:** HIGH - Core orchestration
**Duration:** 4 days

#### **Problem:**
Need sequential processing with memory-aware service rotation, error handling, and progress tracking for React UI.

#### **Solution:**
LangGraph state machine with 5 nodes (memory_check, docling, chunking, embedding, graph_extraction).

#### **State Schema**

```python
# src/components/ingestion/state.py
from typing import TypedDict, List, Literal
from dataclasses import dataclass

@dataclass
class DocumentChunk:
    chunk_id: str
    content: str
    char_count: int
    token_count: int
    metadata: dict

@dataclass
class Entity:
    entity_id: str
    name: str
    type: str
    description: str

@dataclass
class Relation:
    relation_id: str
    source: str
    target: str
    type: str
    description: str

class IngestionState(TypedDict):
    """State for document ingestion pipeline."""

    # Document Info
    document_path: str
    document_id: str
    batch_id: str
    batch_index: int          # Current document in batch (1-based)
    total_documents: int      # Total documents in batch

    # Stage Results
    parsed_content: str       # Docling Output (Markdown)
    parsed_metadata: dict     # {pages: int, tables: int, images: int}
    chunks: List[DocumentChunk]
    embedded_chunks: List[str]  # Qdrant IDs
    entities: List[Entity]
    relations: List[Relation]

    # Status Tracking (for React UI SSE)
    docling_status: Literal["pending", "running", "completed", "failed"]
    chunking_status: Literal["pending", "running", "completed", "failed"]
    embedding_status: Literal["pending", "running", "completed", "failed"]
    graph_status: Literal["pending", "running", "completed", "failed"]
    overall_progress: float   # 0.0 - 1.0

    # Memory Management
    current_memory_mb: float
    requires_container_restart: bool

    # Error Handling
    errors: List[dict]        # [{stage: str, error: str, timestamp: str}]
    retry_count: int
    max_retries: int          # Default: 3
```

#### **Node Implementations**

**1. Memory Check Node**

```python
# src/components/ingestion/nodes/memory_check.py
import psutil
import structlog

logger = structlog.get_logger(__name__)

async def memory_check_node(state: IngestionState) -> IngestionState:
    """Check available memory before processing."""

    memory = psutil.virtual_memory()
    available_mb = memory.available / (1024 ** 2)

    logger.info(
        "Memory check",
        available_mb=available_mb,
        threshold_mb=1000,  # Require 1GB free minimum
    )

    state["current_memory_mb"] = available_mb

    if available_mb < 1000:
        state["errors"].append({
            "stage": "memory_check",
            "error": f"Insufficient memory: {available_mb:.0f}MB available, need 1000MB",
            "timestamp": datetime.now().isoformat(),
        })
        return state  # Will route to END

    return state

def should_proceed(state: IngestionState) -> str:
    """Conditional edge: proceed or abort."""
    if state["errors"]:
        return "insufficient_memory"
    return "proceed"
```

**2. Docling Processing Node**

```python
# src/components/ingestion/nodes/docling.py
from src.components.ingestion.docling_client import DoclingContainerClient

async def docling_processing_node(state: IngestionState) -> IngestionState:
    """Parse document with Docling container."""

    state["docling_status"] = "running"

    try:
        client = DoclingContainerClient()

        # Start container (if not already running)
        await client.start_container()

        # Parse document
        result = await client.parse_document(Path(state["document_path"]))

        state["parsed_content"] = result["content"]
        state["parsed_metadata"] = result["metadata"]
        state["docling_status"] = "completed"
        state["overall_progress"] = 0.25  # 25% done

        # Stop container to free memory
        await client.stop_container()

        logger.info(
            "Docling parsing complete",
            document_id=state["document_id"],
            pages=result["metadata"]["pages"],
            content_length=len(result["content"]),
        )

    except Exception as e:
        state["docling_status"] = "failed"
        state["errors"].append({
            "stage": "docling",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })
        logger.error("Docling parsing failed", error=str(e))

    return state
```

**3. Chunking Node**

```python
# src/components/ingestion/nodes/chunking.py
from src.components.ingestion.chunking_service import ChunkingService

async def chunking_node(state: IngestionState) -> IngestionState:
    """Chunk parsed content."""

    state["chunking_status"] = "running"

    try:
        chunker = ChunkingService(
            chunk_size=1800,  # From Sprint 20 analysis
            overlap=300,
            strategy="adaptive",
        )

        chunks = chunker.chunk_text(
            text=state["parsed_content"],
            document_id=state["document_id"],
        )

        state["chunks"] = chunks
        state["chunking_status"] = "completed"
        state["overall_progress"] = 0.50  # 50% done

        logger.info(
            "Chunking complete",
            document_id=state["document_id"],
            num_chunks=len(chunks),
            avg_chunk_size=sum(c.token_count for c in chunks) / len(chunks),
        )

    except Exception as e:
        state["chunking_status"] = "failed"
        state["errors"].append({
            "stage": "chunking",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })
        logger.error("Chunking failed", error=str(e))

    return state
```

**4. Embedding Node**

```python
# src/components/ingestion/nodes/embedding.py
from src.components.vector_search.qdrant_client import QdrantClient

async def embedding_node(state: IngestionState) -> IngestionState:
    """Embed chunks and upsert to Qdrant."""

    state["embedding_status"] = "running"

    try:
        qdrant = QdrantClient()

        # Embed and upsert chunks
        chunk_ids = await qdrant.upsert_chunks(
            chunks=[c.content for c in state["chunks"]],
            metadatas=[{"chunk_id": c.chunk_id, "document_id": state["document_id"]} for c in state["chunks"]],
        )

        state["embedded_chunks"] = chunk_ids
        state["embedding_status"] = "completed"
        state["overall_progress"] = 0.75  # 75% done

        logger.info(
            "Embedding complete",
            document_id=state["document_id"],
            num_embeddings=len(chunk_ids),
        )

    except Exception as e:
        state["embedding_status"] = "failed"
        state["errors"].append({
            "stage": "embedding",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })
        logger.error("Embedding failed", error=str(e))

    return state
```

**5. Graph Extraction Node**

```python
# src/components/ingestion/nodes/graph_extraction.py
from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async

async def graph_extraction_node(state: IngestionState) -> IngestionState:
    """Extract entities and relations with LightRAG."""

    state["graph_status"] = "running"

    try:
        lightrag = await get_lightrag_wrapper_async()

        # Insert document (triggers entity/relation extraction)
        result = await lightrag.insert_documents_optimized([{
            "text": state["parsed_content"],
            "id": state["document_id"],
        }])

        # Extract entity/relation IDs from result
        state["entities"] = result.get("entities", [])
        state["relations"] = result.get("relations", [])
        state["graph_status"] = "completed"
        state["overall_progress"] = 1.0  # 100% done

        logger.info(
            "Graph extraction complete",
            document_id=state["document_id"],
            num_entities=len(state["entities"]),
            num_relations=len(state["relations"]),
        )

    except Exception as e:
        state["graph_status"] = "failed"
        state["errors"].append({
            "stage": "graph_extraction",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })
        logger.error("Graph extraction failed", error=str(e))

    return state
```

#### **Graph Construction**

```python
# src/components/ingestion/graph.py
from langgraph.graph import StateGraph, START, END

def create_ingestion_graph() -> StateGraph:
    """Create LangGraph ingestion pipeline."""

    graph = StateGraph(IngestionState)

    # Add nodes
    graph.add_node("memory_check", memory_check_node)
    graph.add_node("docling", docling_processing_node)
    graph.add_node("chunking", chunking_node)
    graph.add_node("embedding", embedding_node)
    graph.add_node("graph_extraction", graph_extraction_node)

    # Add edges
    graph.add_edge(START, "memory_check")
    graph.add_conditional_edges(
        "memory_check",
        should_proceed,
        {
            "proceed": "docling",
            "insufficient_memory": END
        }
    )
    graph.add_edge("docling", "chunking")
    graph.add_edge("chunking", "embedding")
    graph.add_edge("embedding", "graph_extraction")
    graph.add_edge("graph_extraction", END)

    return graph.compile()
```

#### **Tasks:**
- [ ] Define `IngestionState` TypedDict with all fields
- [ ] Implement 5 nodes (memory_check, docling, chunking, embedding, graph)
- [ ] Graph construction with conditional routing
- [ ] Error handling in each node
- [ ] Progress tracking (overall_progress field)
- [ ] Integration tests with mock services

#### **Deliverables:**
```bash
src/components/ingestion/state.py
src/components/ingestion/nodes/memory_check.py
src/components/ingestion/nodes/docling.py
src/components/ingestion/nodes/chunking.py
src/components/ingestion/nodes/embedding.py
src/components/ingestion/nodes/graph_extraction.py
src/components/ingestion/graph.py
tests/ingestion/test_graph.py
```

#### **Acceptance Criteria:**
- ✅ All 5 nodes implemented and tested
- ✅ State transitions correctly through pipeline
- ✅ Error handling in each node (failed status + errors list)
- ✅ Progress tracking (0.0 → 1.0)
- ✅ Conditional routing works (memory check)
- ✅ Integration test: End-to-end document processing

---

### Feature 21.3: Batch Processing + Progress Monitoring (13 SP)
**Priority:** HIGH - User experience
**Duration:** 3 days

#### **Problem:**
Need to process 100+ documents in batches with real-time progress visible in React UI.

#### **Solution:**
Batch orchestrator with SSE streaming to React frontend via FastAPI.

#### **Batch Orchestrator**

```python
# src/components/ingestion/batch_orchestrator.py
from typing import List, AsyncGenerator
import asyncio
from pathlib import Path

class BatchOrchestrator:
    """Orchestrate batch document ingestion with progress tracking."""

    def __init__(self, graph):
        self.graph = graph

    async def process_batch(
        self,
        file_paths: List[Path],
        batch_id: str,
    ) -> AsyncGenerator[dict, None]:
        """Process batch of documents, yielding progress updates.

        Yields progress events for SSE streaming to React UI:
            {
                "type": "batch_start",
                "batch_id": str,
                "total_documents": int
            }
            {
                "type": "document_progress",
                "document_id": str,
                "batch_index": int,
                "docling_status": str,
                "overall_progress": float
            }
            {
                "type": "batch_complete",
                "batch_id": str,
                "successful": int,
                "failed": int
            }
        """

        total = len(file_paths)
        successful = 0
        failed = 0

        # Batch start event
        yield {
            "type": "batch_start",
            "batch_id": batch_id,
            "total_documents": total,
            "timestamp": datetime.now().isoformat(),
        }

        for i, file_path in enumerate(file_paths, 1):
            document_id = f"{batch_id}_{file_path.stem}"

            # Initialize state
            initial_state = {
                "document_path": str(file_path),
                "document_id": document_id,
                "batch_id": batch_id,
                "batch_index": i,
                "total_documents": total,
                "parsed_content": "",
                "parsed_metadata": {},
                "chunks": [],
                "embedded_chunks": [],
                "entities": [],
                "relations": [],
                "docling_status": "pending",
                "chunking_status": "pending",
                "embedding_status": "pending",
                "graph_status": "pending",
                "overall_progress": 0.0,
                "current_memory_mb": 0.0,
                "requires_container_restart": False,
                "errors": [],
                "retry_count": 0,
                "max_retries": 3,
            }

            # Run graph
            async for event in self.graph.astream(initial_state):
                # Extract current state
                node_name = list(event.keys())[0]
                state = event[node_name]

                # Yield progress update
                yield {
                    "type": "document_progress",
                    "document_id": document_id,
                    "batch_index": i,
                    "current_node": node_name,
                    "docling_status": state.get("docling_status", "pending"),
                    "chunking_status": state.get("chunking_status", "pending"),
                    "embedding_status": state.get("embedding_status", "pending"),
                    "graph_status": state.get("graph_status", "pending"),
                    "overall_progress": state.get("overall_progress", 0.0),
                    "errors": state.get("errors", []),
                    "timestamp": datetime.now().isoformat(),
                }

            # Final state
            if state.get("errors"):
                failed += 1
            else:
                successful += 1

        # Batch complete event
        yield {
            "type": "batch_complete",
            "batch_id": batch_id,
            "successful": successful,
            "failed": failed,
            "total_documents": total,
            "timestamp": datetime.now().isoformat(),
        }
```

#### **FastAPI SSE Endpoint**

```python
# src/api/v1/ingestion.py
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from src.components.ingestion.batch_orchestrator import BatchOrchestrator
from src.components.ingestion.graph import create_ingestion_graph

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])

@router.post("/batch")
async def ingest_batch(
    files: List[UploadFile] = File(...),
    batch_id: str = None,
):
    """Ingest batch of documents with SSE progress streaming.

    Returns SSE stream with progress updates for React UI.
    """

    if not batch_id:
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Save uploaded files to temp directory
    temp_dir = Path(f"/tmp/ingestion/{batch_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    file_paths = []
    for file in files:
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(await file.read())
        file_paths.append(file_path)

    # Create orchestrator
    graph = create_ingestion_graph()
    orchestrator = BatchOrchestrator(graph)

    # Stream progress events
    async def event_generator():
        async for event in orchestrator.process_batch(file_paths, batch_id):
            # SSE format
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

#### **React UI Integration**

```typescript
// frontend/src/components/IngestionMonitor.tsx
import { useEffect, useState } from 'react';

interface ProgressEvent {
  type: 'batch_start' | 'document_progress' | 'batch_complete';
  batch_id: string;
  document_id?: string;
  batch_index?: number;
  docling_status?: string;
  overall_progress?: number;
  successful?: number;
  failed?: number;
}

export function IngestionMonitor({ batchId }: { batchId: string }) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [currentProgress, setCurrentProgress] = useState(0);

  useEffect(() => {
    const eventSource = new EventSource(`/api/v1/ingestion/batch/${batchId}/stream`);

    eventSource.onmessage = (event) => {
      const data: ProgressEvent = JSON.parse(event.data);

      setEvents((prev) => [...prev, data]);

      if (data.type === 'document_progress') {
        setCurrentProgress(data.overall_progress || 0);
      }
    };

    return () => eventSource.close();
  }, [batchId]);

  return (
    <div className="ingestion-monitor">
      <h2>Batch Ingestion: {batchId}</h2>

      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${currentProgress * 100}%` }}
        />
      </div>

      <div className="event-log">
        {events.map((event, i) => (
          <div key={i} className={`event event-${event.type}`}>
            {event.type === 'document_progress' && (
              <span>
                Document {event.batch_index}: {event.docling_status}
                ({(event.overall_progress! * 100).toFixed(0)}%)
              </span>
            )}
            {event.type === 'batch_complete' && (
              <span>
                ✅ Batch complete: {event.successful} successful, {event.failed} failed
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

#### **Tasks:**
- [ ] Implement `BatchOrchestrator` with async generator
- [ ] FastAPI SSE endpoint for batch ingestion
- [ ] React component for progress monitoring
- [ ] File upload handling (multipart form)
- [ ] Temporary file cleanup after processing
- [ ] Batch resume logic (if interrupted - TD for later)

#### **Deliverables:**
```bash
src/components/ingestion/batch_orchestrator.py
src/api/v1/ingestion.py
frontend/src/components/IngestionMonitor.tsx
tests/api/test_ingestion_api.py
```

#### **Acceptance Criteria:**
- ✅ Batch processing of 100 documents completes successfully
- ✅ SSE stream delivers real-time progress to React UI
- ✅ Progress bar updates in real-time (0-100%)
- ✅ Event log shows all processing stages
- ✅ Failed documents logged with errors
- ✅ Batch summary (successful/failed counts)

---

### Feature 21.4: TBD - To Be Defined (0 SP)
**Priority:** TBD
**Duration:** TBD

**Status:** Feature content to be provided by user.

---

### Feature 21.5: Tables, Images & Layout Extraction from JSON (8 SP)
**Priority:** HIGH - Data richness
**Duration:** 2 days

**Status:** ✅ COMPLETED (2025-11-08)

#### **Problem:**
Docling extracts rich metadata (tables, images, layout) in JSON format, but we weren't using it. Need to parse and store this structural information.

#### **Solution:**
Parse Docling's `json_content` to extract tables, images, and layout metadata, then store in `DoclingParsedDocument`.

#### **Implementation:**
Modified `DoclingContainerClient.parse_document()` to:
- Parse `json_content` from Docling response
- Extract tables with captions, page numbers, and bounding boxes
- Extract images/pictures with captions and provenance
- Extract layout information (schema, pages, text count)

#### **Deliverables:**
```bash
src/components/ingestion/docling_client.py    # Enhanced with JSON parsing
tests/integration/components/ingestion/test_docling_container_integration.py
generate_docling_report.py                     # HTML report generator
docling_structure_report.html                  # Analysis output
```

#### **Acceptance Criteria:**
- ✅ Tables extracted with captions, page_no, bbox, ref, label
- ✅ Images extracted with captions, page_no, bbox, ref, label
- ✅ Layout info extracted (schema_name, version, pages, texts_count)
- ✅ Integration test validates all metadata fields
- ✅ HTML report displays structure analysis

---

### Feature 21.6: Image-Enhanced Document Ingestion with VLM (55 SP)
**Priority:** HIGH - Advanced capability
**Duration:** 9-10 days

**Status:** 📋 READY FOR IMPLEMENTATION

#### **Overview:**
Integration von Qwen3-VL-4B für intelligente Bildbeschreibungen in der Dokumenten-Ingestion-Pipeline mit vollständiger Provenance-Tracking und Frontend-Visualisierung.

**Ziel:** Docling extrahiert Dokument-Struktur und Bilder → Qwen3-VL beschreibt Bilder → Beschreibungen werden IN DoclingDocument eingefügt → HybridChunker erstellt kontextualisierte Chunks → Embeddings mit Hierarchie-Kontext → BBox-Provenance für PDF-Overlay-Rendering im Frontend.

#### **Critical Architecture Decisions:**

1. **VLM-Text Placement:**
   - ✅ Insert VLM text INTO `picture_item.text` in DoclingDocument (NOT separate chunks)
   - ✅ HybridChunker automatically adds hierarchical context (headings, captions, page numbers)

2. **BBox Storage:**
   - ✅ Store complete BBox ONLY in Qdrant (absolute + normalized + page context)
   - ✅ Neo4j stores minimal provenance (chunk_id, has_image_annotation flag)

3. **Coordinate Format:**
   - ✅ Absolute coordinates (PDF points)
   - ✅ Normalized coordinates (0-1 scale for frontend)
   - ✅ Page context (width, height, unit, dpi, coord_origin)

4. **Annotation Loading:**
   - ✅ On-demand via API when PDF is displayed (not during every search)
   - ✅ 10-30ms latency acceptable

5. **Prompting Strategy:**
   - ✅ Simple, natural language prompts (Qwen3-VL best practice)
   - ❌ NOT complex JSON instructions

#### **Pipeline Architecture:**

```
Stage 1: Docling Extraction
├─ PDF/DOCX → DoclingDocument
├─ Text, Tabellen, Bilder extrahieren
└─ BBox + Page-Dimensionen erfassen

Stage 2: Image Enrichment (VLM)
├─ Bildfilterung (Größe, Relevanz)
├─ Qwen3-VL Beschreibung generieren
├─ VLM-Text IN picture_item.text einfügen ← KRITISCH
└─ VLM-Metadata mit BBox speichern

Stage 3: Chunking (HybridChunker)
├─ Angereichertes DoclingDocument → Chunks
├─ Chunks enthalten automatisch:
│   ├─ Section-Headers
│   ├─ Captions
│   ├─ Page-Numbers
│   └─ VLM-Beschreibungen mit Kontext
└─ BBox-Info zu Chunks zuordnen

Stage 4: Embeddings (Qdrant)
├─ Contextualized Text embedden (BGE-M3)
└─ Payload mit vollständiger Provenance:
    ├─ image_annotations (mit BBox)
    ├─ page_dimensions
    └─ document_path

Stage 5: Graph Extraction (Neo4j)
├─ Entity/Relation Extraktion
└─ Minimal-Provenance:
    ├─ chunk_id (Link zu Qdrant)
    ├─ has_image_annotation (Flag)
    └─ image_page_nos (Quick-Info)
```

#### **Technology Stack:**

- **Docling:** quay.io/docling-project/docling-serve (CPU-only container)
- **VLM:** qwen3-vl:4b-instruct via Ollama (~5-6GB VRAM)
- **Chunking:** HybridChunker from Docling with BGE-M3 tokenizer
- **Embeddings:** bge-m3 (8192 token context, replaces nomic-embed-text)
- **Orchestration:** LangGraph State Machine (5 nodes)

#### **Key Data Structures:**

**Enhanced BBox:**
```python
{
    'bbox_absolute': {'left': float, 'top': float, 'right': float, 'bottom': float},
    'page_context': {
        'page_no': int,
        'page_width': float,
        'page_height': float,
        'unit': 'pt',
        'dpi': 72,
        'coord_origin': str
    },
    'bbox_normalized': {'left': float, 'top': float, 'right': float, 'bottom': float}
}
```

**Qdrant Payload:**
```python
{
    "content": str,
    "contextualized_content": str,
    "document_id": str,
    "document_path": str,
    "page_no": int,
    "headings": List[str],
    "page_dimensions": {...},
    "contains_images": bool,
    "image_annotations": [
        {
            "description": str,
            "vlm_model": "qwen3-vl:4b-instruct",
            "bbox_absolute": {...},
            "page_context": {...},
            "bbox_normalized": {...}
        }
    ]
}
```

**Neo4j Entity:**
```python
{
    'name': str,
    'type': str,
    'document_id': str,
    'chunk_id': str,
    'qdrant_point_id': str,  # Link to Qdrant
    'page_no': int,
    'section_path': str,
    'has_image_annotation': bool,
    'image_page_nos': List[int]
}
```

#### **API Endpoints:**

1. **Unified Search:**
```python
POST /api/search
{
    "query": str,
    "search_type": "vector" | "graph" | "hybrid",
    "include_annotations": bool  # Default: false
}
```

2. **On-Demand Annotations:**
```python
GET /api/document/{document_id}/annotations
?chunk_ids=[...]&page_no=15

Response:
{
    "annotations_by_page": {
        "15": {
            "page_dimensions": {...},
            "annotations": [...]
        }
    }
}
```

#### **Configuration (ingestion_config.yaml):**

```yaml
docling:
  container_name: "aegis-docling"
  port: 5001
  memory_limit: "2g"
  options:
    do_ocr: true
    generate_picture_images: true
    images_scale: 2.0

qwen3vl:
  model: "qwen3-vl:4b-instruct"
  temperature: 0.7
  top_p: 0.8
  top_k: 20
  num_ctx: 4096

image_filtering:
  min_size: 100
  min_aspect_ratio: 0.1
  max_aspect_ratio: 10

chunking:
  tokenizer_model: "BAAI/bge-m3"
  max_tokens: 8192
  merge_peers: true

embedding:
  model: "bge-m3"
  batch_size: 32

graph:
  llm_model: "qwen2.5:3b"
  temperature: 0.1
```

#### **Tasks:**

**Node 1-2 (Docling + VLM):** 2-3 days
- [ ] LangGraph State Schema definieren
- [ ] Docling Integration Class implementieren
- [ ] Qwen3-VL Image Processor implementieren (einfache Prompts!)
- [ ] Image filtering logic (size, aspect ratio)
- [ ] BBox extraction with page context
- [ ] VLM text insertion into picture_item.text
- [ ] Enhanced BBox structure with normalization

**Node 3 (Chunking):** 1 day
- [ ] HybridChunker setup with BGE-M3 tokenizer
- [ ] BBox-to-chunk mapping
- [ ] Chunk enrichment with image metadata

**Node 4 (Embeddings):** 1 day
- [ ] Qdrant payload structure with image annotations
- [ ] BGE-M3 embedding generation
- [ ] Full provenance storage

**Node 5 (Graph):** 1 day
- [ ] Neo4j minimal provenance
- [ ] Entity extraction with image indicators
- [ ] Qdrant reference links

**API-Endpoints:** 1 day
- [ ] Unified search endpoint
- [ ] On-demand annotation endpoint
- [ ] Batch annotation retrieval

**Testing:** 2 days
- [ ] Unit tests (image filtering, bbox enrichment, coordinate normalization)
- [ ] Integration tests (E2E pipeline with test PDFs)
- [ ] API tests (search, annotations, performance <50ms)

**Dokumentation:** 1 day
- [ ] Feature documentation
- [ ] API documentation
- [ ] Frontend integration guide

#### **Deliverables:**
```bash
src/components/ingestion/ingestion_state.py           # LangGraph State
src/components/ingestion/langgraph_nodes.py           # 5 Pipeline Nodes
src/components/ingestion/langgraph_pipeline.py        # Graph Construction
src/components/ingestion/image_processor.py           # Qwen3-VL Integration
ingestion_config.yaml                                  # Configuration
src/api/v1/annotations.py                              # Annotation API
tests/unit/components/ingestion/test_langgraph_nodes_unit.py
tests/integration/components/ingestion/test_image_pipeline.py
docs/features/FEATURE_21_6_IMAGE_VLM.md
```

#### **Acceptance Criteria:**
- ✅ Docling extrahiert Bilder mit BBox + Page-Context
- ✅ Qwen3-VL beschreibt Bilder (>90% Success-Rate)
- ✅ VLM-Text wird IN DoclingDocument eingefügt
- ✅ HybridChunker erstellt Chunks mit Hierarchie-Kontext
- ✅ Qdrant speichert vollständige BBox-Provenance (absolute + normalized + page_context)
- ✅ Neo4j Entities haben Referenz zu Qdrant (minimal provenance)
- ✅ API-Endpoint für On-Demand Annotations (Latenz <50ms)
- ✅ Normalisierte Koordinaten funktionieren mit PDF.js
- ✅ Integration Tests bestanden
- ✅ Dokumentation vollständig

#### **Performance Targets:**

| Component | Target | Measurement |
|-----------|--------|-------------|
| Docling Extraction | <10s/doc | Benchmark |
| VLM per Image | <3s | Ollama metrics |
| Chunking | <2s | Timer |
| Embedding | <5s | BGE-M3 batch |
| Graph Extraction | <10s | Neo4j insert |
| Annotation Lookup | <30ms | API latency |
| **Total Pipeline** | **~5-10 min/doc** | **(5-10 images)** |

---

## 🔧 Technical Debt Created

| ID | Description | Priority | Sprint |
|----|-------------|----------|--------|
| TD-38 | Implement Redis checkpointing for pipeline recovery | P2 | Sprint 22 |
| TD-39 | Add semantic chunking strategy (vs adaptive) | P3 | Sprint 22 |
| TD-40 | Grafana dashboard for ingestion metrics | P2 | Sprint 22 |
| TD-41 | Batch resume logic (if interrupted) | P2 | Sprint 22 |
| TD-42 | Docling model warmup script (first-run optimization) | P3 | Sprint 22 |

---

## 📊 Sprint 21 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Docling GPU utilization | >80% of 6GB VRAM | nvidia-smi |
| Document parsing speed | <30s for 10-page PDF | Benchmark |
| Memory isolation | <4.4GB RAM peak | docker stats |
| Batch processing | 100 docs without OOM | Integration test |
| Chunk size | 1200-1800 tokens avg | ChunkingService stats |
| Pipeline latency | <5min per document | End-to-end test |
| React UI responsiveness | <100ms SSE latency | Frontend metrics |

---

## 🚀 Sprint 21 Completion Criteria

- ✅ Docling CUDA container operational with GPU acceleration
- ✅ LangGraph state machine orchestrates 4 pipeline stages
- ✅ Batch processing of 100+ documents completes successfully
- ✅ React UI displays real-time ingestion progress (SSE)
- ✅ Memory stays <4.4GB RAM (container rotation working)
- ✅ Chunking produces optimal 1200-1800 token chunks
- ✅ Neo4j + Qdrant populated correctly
- ✅ Integration tests passing (>80% coverage)
- ✅ Documentation complete (Docker setup, API, React UI)

---

**Sprint 21 Objectives:** Container-based ingestion with memory-optimized orchestration ✅
**Next Sprint:** Sprint 22 - Pipeline Recovery (Redis checkpointing), Grafana Monitoring

**Last Updated:** 2025-11-07
**Author:** Claude Code
**Architecture:** Container-Based + LangGraph Orchestration (v2)
