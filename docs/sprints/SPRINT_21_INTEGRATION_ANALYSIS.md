# Sprint 21 Integration Analysis - Docling Architecture

**Date:** 2025-11-07
**Sprint:** 21 (Container-based Docling + LangGraph Pipeline)
**Status:** Pre-Implementation Analysis

---

## Executive Summary

This document analyzes the current AEGIS RAG ingestion architecture and identifies:
1. **Components to deprecate** (LlamaIndex SimpleDirectoryReader)
2. **Components to preserve** (ChunkingService, EmbeddingService, Graph Extraction)
3. **Integration points** for Sprint 21 Docling container
4. **Test compatibility** strategy

**Key Decision:** Docling will **replace** LlamaIndex's SimpleDirectoryReader for document parsing, but will **integrate with** existing chunking, embedding, and graph extraction pipelines.

---

## Current Ingestion Architecture (Pre-Sprint 21)

### 1. Document Loading Layer
**File:** `src/components/vector_search/ingestion.py`
**Component:** `DocumentIngestionPipeline.load_documents()`

```python
# CURRENT: Uses LlamaIndex SimpleDirectoryReader
from llama_index.core import SimpleDirectoryReader

loader = SimpleDirectoryReader(
    input_dir=str(validated_path),
    required_exts=[".pdf", ".txt", ".md", ".docx", ".csv", ".pptx"],  # Sprint 16
    recursive=True,
    filename_as_id=True,
)
documents = loader.load_data()  # Returns List[Document]
```

**Capabilities:**
- ✅ PDF, DOCX, PPTX, TXT, MD, CSV parsing
- ✅ Recursive directory traversal
- ✅ Basic metadata extraction (file_name, file_path)
- ❌ **NO OCR** for scanned PDFs
- ❌ **NO table extraction** (tables lost in text)
- ❌ **NO layout analysis** (formatting lost)
- ❌ **NO GPU acceleration**

**Deprecation Plan:**
- **Status:** ⚠️ DEPRECATED in Sprint 21
- **Replacement:** Docling CUDA Container (`DoclingContainerClient`)
- **Migration Path:** Lines 156-183 in `ingestion.py`

---

### 2. Chunking Layer
**File:** `src/core/chunking_service.py`
**Component:** `ChunkingService` (ADR-022)

```python
# CURRENT: Unified chunking across all pipelines
service = ChunkingService(
    strategy=ChunkStrategy(
        method="adaptive",  # Sentence-aware
        chunk_size=600,     # Sprint 16 alignment
        overlap=150,        # 25% overlap
    )
)
chunks = service.chunk_document(document_id, content, metadata)
```

**Capabilities:**
- ✅ 4 chunking strategies (fixed, adaptive, paragraph, sentence)
- ✅ SHA-256 chunk_id for graph-vector alignment
- ✅ Token-accurate counting (tiktoken)
- ✅ Prometheus metrics
- ✅ Consistent boundaries across Qdrant + Neo4j

**Sprint 21 Status:**
- **Status:** ✅ **PRESERVED** - No changes needed
- **Integration:** Docling output → ChunkingService → Chunks
- **Update:** Feature 21.4 will change `chunk_size` from 600 → 1800 tokens

---

### 3. Embedding Layer
**File:** `src/components/shared/embedding_service.py`
**Component:** `UnifiedEmbeddingService`

```python
# CURRENT: Shared embedding service (Sprint 11)
service = get_embedding_service()
embeddings = await service.embed_batch(texts)  # BGE-M3, 1024D
```

**Capabilities:**
- ✅ BGE-M3 via Ollama (1024 dimensions)
- ✅ Batch embedding with connection pooling
- ✅ Pickle-compatible (lazy AsyncClient)
- ✅ Shared cache across components

**Sprint 21 Status:**
- **Status:** ✅ **PRESERVED** - No changes needed
- **Integration:** Chunks → EmbeddingService → Vectors → Qdrant

---

### 4. Graph Extraction Layer
**File:** `src/components/graph_rag/lightrag_wrapper.py`
**Component:** `LightRAGWrapper.insert_documents_optimized()`

```python
# CURRENT: Three-Phase Extraction Pipeline (Sprint 13)
# Phase 1: SpaCy NER (fast, broad entities)
# Phase 2: Semantic deduplication (entity normalization)
# Phase 3: Gemma 3 4B LLM (relation extraction)

graph_stats = await lightrag.insert_documents_optimized(lightrag_docs)
```

**Capabilities:**
- ✅ Three-phase entity/relation extraction (ADR-017)
- ✅ >10x performance improvement (>300s → <30s)
- ✅ Semantic deduplication (95% entity quality)
- ✅ Neo4j storage with provenance tracking
- ✅ Document-level chunking via ChunkingService

**Sprint 21 Status:**
- **Status:** ✅ **PRESERVED** - No changes needed
- **Integration:** Chunks → ThreePhaseExtractor → Neo4j

---

### 5. Unified Ingestion Pipeline
**File:** `src/components/shared/unified_ingestion.py`
**Component:** `UnifiedIngestionPipeline`

```python
# CURRENT: Orchestrates parallel indexing
result = await pipeline.ingest_directory(input_dir)
# Parallel tasks:
# 1. Qdrant + BM25 indexing
# 2. Neo4j graph construction
```

**Capabilities:**
- ✅ Parallel indexing to Qdrant + Neo4j
- ✅ Shared embedding service (no duplicates)
- ✅ Error handling with partial success
- ✅ Progress tracking

**Sprint 21 Status:**
- **Status:** ⚠️ **DEPRECATED** - Replaced by LangGraph state machine
- **Replacement:** Feature 21.2 LangGraph Ingestion Pipeline
- **Reason:** LangGraph provides:
  - Sequential memory-optimized execution (4.4GB RAM constraint)
  - Container lifecycle management (start/stop Docling)
  - SSE streaming for React UI progress
  - Redis checkpointing (future TD-38)

---

## Sprint 21 Integration Points

### Integration Point 1: Document Parsing (DOCLING REPLACES)

**Current Code:** `src/components/vector_search/ingestion.py:128-183`

```python
# ❌ DEPRECATED: LlamaIndex SimpleDirectoryReader
async def load_documents(self, input_dir: str | Path) -> list[Document]:
    loader = SimpleDirectoryReader(
        input_dir=str(validated_path),
        required_exts=[".pdf", ".txt", ".md", ".docx", ".csv", ".pptx"],
    )
    documents = loader.load_data()
    return documents
```

**Sprint 21 Replacement:** Feature 21.1 - DoclingContainerClient

```python
# ✅ NEW: Docling CUDA Container
from src.components.ingestion.docling_client import DoclingContainerClient

docling = DoclingContainerClient(base_url="http://localhost:8080")
await docling.start_container()  # Memory-optimized start

# Parse single document
parsed = await docling.parse_document(file_path)
# Returns: {
#   "text": "...",
#   "metadata": {...},
#   "tables": [...],
#   "images": [...],
#   "layout": {...}
# }

await docling.stop_container()  # Free VRAM
```

**Key Changes:**
- **OCR:** Scanned PDFs now fully parsed
- **Tables:** Preserved in structured format
- **Layout:** Headings, lists, columns detected
- **GPU:** RTX 3060 6GB VRAM (80% utilization)
- **Lifecycle:** Container start/stop per batch

---

### Integration Point 2: Chunking Strategy (PARAMETER UPDATE)

**Current Code:** `src/core/chunking_service.py:64-68`

```python
# ❌ DEPRECATED: 600 token chunks (Sprint 16)
chunk_strategy = ChunkStrategy(
    method="adaptive",
    chunk_size=600,      # ← TOO SMALL (Sprint 20 analysis)
    overlap=150,         # 25% overlap
)
```

**Sprint 21 Update:** Feature 21.4 - 1800 Token Chunks

```python
# ✅ NEW: 1800 token chunks (3x increase)
chunk_strategy = ChunkStrategy(
    method="adaptive",   # Sentence-aware (preserved)
    chunk_size=1800,     # ← 3x increase (65% fewer chunks)
    overlap=300,         # Maintain 1/6 ratio (16.7%)
)
```

**Rationale:** Sprint 20 chunk analysis revealed:
- Current avg: 112 tokens/chunk (massive overhead)
- Target: 1800 tokens/chunk (optimal for LLM context)
- Reduction: 65% fewer chunks (faster retrieval)

---

### Integration Point 3: LangGraph State Machine (NEW ORCHESTRATOR)

**Current Code:** `src/components/shared/unified_ingestion.py:115-122`

```python
# ❌ DEPRECATED: Parallel execution with asyncio.gather
tasks = []
if self.enable_qdrant:
    tasks.append(safe_index_qdrant())
if self.enable_neo4j:
    tasks.append(safe_index_neo4j())
results = await asyncio.gather(*tasks)
```

**Sprint 21 Replacement:** Feature 21.2 - LangGraph Sequential Pipeline

```python
# ✅ NEW: LangGraph 5-node pipeline
from langgraph.graph import StateGraph

graph = StateGraph(IngestionState)
graph.add_node("memory_check", memory_check_node)
graph.add_node("docling", docling_parse_node)
graph.add_node("chunking", chunking_node)
graph.add_node("embedding", embedding_node)
graph.add_node("graph_extraction", graph_extraction_node)

# Sequential edges (memory-optimized)
graph.add_edge("memory_check", "docling")
graph.add_edge("docling", "chunking")
graph.add_edge("chunking", "embedding")
graph.add_edge("embedding", "graph_extraction")

# Compile graph
pipeline = graph.compile()

# Stream execution with SSE progress
async for event in pipeline.astream(initial_state):
    node_name = list(event.keys())[0]
    state = event[node_name]
    # Send SSE to React UI: {"node": node_name, "progress": state["overall_progress"]}
```

**Key Changes:**
- **Sequential:** One stage at a time (4.4GB RAM constraint)
- **Container Lifecycle:** Start/stop Docling between batches
- **Progress:** Real-time SSE streaming to React UI
- **State:** TypedDict with 15+ fields for tracking

---

### Integration Point 4: Batch Processing (NEW FEATURE)

**Current Code:** Scripts use single document or directory

```python
# ❌ DEPRECATED: No batch support, no progress tracking
stats = await pipeline.index_documents(input_dir=input_dir)
```

**Sprint 21 Addition:** Feature 21.3 - BatchOrchestrator

```python
# ✅ NEW: Batch processing with progress monitoring
from src.components.ingestion.batch_orchestrator import BatchOrchestrator

orchestrator = BatchOrchestrator(
    batch_size=10,  # 10 docs per Docling batch
    max_concurrent_batches=1,  # Sequential (RAM constraint)
)

# AsyncGenerator for SSE streaming
async for progress in orchestrator.process_batch(document_paths):
    # Yields: {
    #   "batch_id": "...",
    #   "document_id": "...",
    #   "current_node": "chunking",
    #   "progress": 0.65,
    #   "errors": []
    # }
    await send_sse(progress)
```

**Key Changes:**
- **Batch Size:** 10 docs per Docling container lifecycle
- **Progress:** Real-time SSE to React UI
- **Error Handling:** Continue on failure, track errors
- **Memory:** Monitor RAM, pause if >4GB

---

## Components Requiring Deprecation Markers

### 1. DocumentIngestionPipeline.load_documents()
**File:** `src/components/vector_search/ingestion.py:128-183`

**Deprecation Comment:**
```python
# ============================================================================
# DEPRECATED: Sprint 21 - This method will be replaced by DoclingContainerClient
# ============================================================================
# REASON: LlamaIndex SimpleDirectoryReader lacks:
#   - OCR for scanned PDFs
#   - Table extraction (tables lost in text)
#   - Layout analysis (formatting lost)
#   - GPU acceleration
#
# REPLACEMENT: Feature 21.1 - DoclingContainerClient
#   from src.components.ingestion.docling_client import DoclingContainerClient
#   docling = DoclingContainerClient(base_url="http://localhost:8080")
#   await docling.start_container()
#   parsed = await docling.parse_document(file_path)
#   await docling.stop_container()
#
# MIGRATION STATUS: DO NOT USE for new code
# REMOVAL: Sprint 22 (after full Docling migration)
# ============================================================================

async def load_documents(
    self,
    input_dir: str | Path,
    required_exts: list[str] | None = None,
    recursive: bool = True,
) -> list[Document]:
    """Load documents from directory using LlamaIndex.

    ⚠️ DEPRECATED: Use DoclingContainerClient instead (Sprint 21)
    """
```

---

### 2. UnifiedIngestionPipeline
**File:** `src/components/shared/unified_ingestion.py:34-252`

**Deprecation Comment:**
```python
# ============================================================================
# DEPRECATED: Sprint 21 - This class will be replaced by LangGraph pipeline
# ============================================================================
# REASON: Parallel execution (asyncio.gather) incompatible with:
#   - Memory constraints (4.4GB RAM limit)
#   - Container lifecycle management (Docling start/stop)
#   - SSE progress streaming (React UI)
#   - Sequential stage execution
#
# REPLACEMENT: Feature 21.2 - LangGraph Ingestion State Machine
#   from src.components.ingestion.langgraph_pipeline import create_ingestion_graph
#   pipeline = create_ingestion_graph()
#   async for event in pipeline.astream(initial_state):
#       # Stream progress to React UI
#
# MIGRATION STATUS: DO NOT USE for new code
# REMOVAL: Sprint 22 (after LangGraph migration complete)
# ============================================================================

class UnifiedIngestionPipeline:
    """Single pipeline that indexes documents to all AEGIS RAG systems.

    ⚠️ DEPRECATED: Use LangGraph pipeline instead (Sprint 21)
    """
```

---

### 3. Scripts Using LlamaIndex SimpleDirectoryReader
**Files:**
- `scripts/index_documents.py`
- `scripts/index_one_doc_test.py`
- `scripts/clear_and_reindex.py`

**Deprecation Comment (add to all 3 scripts):**
```python
"""
============================================================================
DEPRECATED SCRIPT: Sprint 21
============================================================================
This script uses LlamaIndex SimpleDirectoryReader which is being replaced
by Docling CUDA Container in Sprint 21.

REPLACEMENT: Sprint 21 scripts will use:
  1. DoclingContainerClient for document parsing
  2. LangGraph pipeline for orchestration
  3. BatchOrchestrator for batch processing
  4. SSE streaming for React UI progress

MIGRATION STATUS: DO NOT USE for production ingestion
USE INSTEAD: scripts/batch_ingest_langgraph.py (Sprint 21)
REMOVAL: Sprint 22
============================================================================

Sprint 19 Update: Uses current production settings:
- BGE-M3 embeddings (1024D, upgraded from nomic-embed-text 768D)
- Adaptive chunking (600 tokens, 150 overlap - Sprint 16 alignment)
- Hybrid RAG (Qdrant + Neo4j/LightRAG)

⚠️ WARNING: This script will be replaced in Sprint 21
"""
```

---

## Components to Preserve (No Changes)

### 1. ChunkingService
**File:** `src/core/chunking_service.py`
**Status:** ✅ PRESERVED
**Changes:** Only parameter update (600 → 1800 tokens) via Feature 21.4

### 2. UnifiedEmbeddingService
**File:** `src/components/shared/embedding_service.py`
**Status:** ✅ PRESERVED
**Changes:** None

### 3. ThreePhaseExtractor
**File:** `src/components/graph_rag/three_phase_extractor.py`
**Status:** ✅ PRESERVED
**Changes:** None

### 4. LightRAGWrapper.insert_documents_optimized()
**File:** `src/components/graph_rag/lightrag_wrapper.py`
**Status:** ✅ PRESERVED
**Changes:** None

### 5. QdrantClientWrapper
**File:** `src/components/vector_search/qdrant_client.py`
**Status:** ✅ PRESERVED
**Changes:** None

---

## Test Compatibility Strategy

### Integration Tests (NO MOCKS - ADR-014)

**Current Tests Using Deprecated Code:**
1. `tests/components/vector_search/test_ingestion.py`
2. `tests/components/shared/test_unified_ingestion.py`
3. `tests/e2e/test_unified_ingestion_e2e.py`

**Strategy:**
1. **Keep existing tests** for backward compatibility (Sprint 21)
2. **Add new tests** for Docling + LangGraph (Sprint 21 Test Plan)
3. **Remove old tests** in Sprint 22 after full migration

**New Test Structure (Sprint 21):**
```
tests/
├── components/
│   ├── ingestion/
│   │   ├── test_docling_client.py           # Feature 21.1 (12 tests)
│   │   ├── test_docling_container_integration.py  # Real Docker (6 tests)
│   │   ├── test_langgraph_nodes.py          # Feature 21.2 (30 tests)
│   │   ├── test_ingestion_pipeline_integration.py  # Real services (12 tests)
│   │   ├── test_batch_orchestrator.py       # Feature 21.3 (10 tests)
│   │   └── test_chunking_1800_tokens.py     # Feature 21.4 (8 tests)
│   └── vector_search/
│       └── test_ingestion.py  # ⚠️ DEPRECATED (keep for Sprint 21)
├── e2e/
│   ├── test_ingestion_pipeline_e2e.py       # Docling → Neo4j (18 tests)
│   └── test_unified_ingestion_e2e.py        # ⚠️ DEPRECATED (keep for Sprint 21)
```

**CI/CD Impact:**
- **Sprint 21:** Run both old and new tests (ensure no regressions)
- **Sprint 22:** Remove old tests, keep only LangGraph tests

---

## Migration Checklist

### Pre-Implementation (Sprint 21 Start)
- [x] Read and understand current ingestion architecture
- [x] Identify deprecation targets
- [x] Create integration analysis document
- [ ] Add deprecation comments to code
- [ ] Update DECISION_LOG.md with Sprint 21 decisions

### Feature 21.1: Docling CUDA Docker Container
- [ ] Create `src/components/ingestion/docling_client.py`
- [ ] Add Docker Compose service for Docling
- [ ] Implement DoclingContainerClient (start/stop/parse)
- [ ] Add 12 unit tests + 6 integration tests

### Feature 21.2: LangGraph Ingestion State Machine
- [ ] Create `src/components/ingestion/langgraph_pipeline.py`
- [ ] Define IngestionState TypedDict (15 fields)
- [ ] Implement 5 nodes (memory_check, docling, chunking, embedding, graph)
- [ ] Add 30 unit tests + 12 integration tests

### Feature 21.3: Batch Processing + Progress Monitoring
- [ ] Create `src/components/ingestion/batch_orchestrator.py`
- [ ] Implement AsyncGenerator for SSE streaming
- [ ] Create FastAPI SSE endpoint
- [ ] Create React IngestionMonitor component
- [ ] Add 10 unit tests + 8 integration tests

### Feature 21.4: Chunking Strategy Definition
- [ ] Update ChunkingService default (600 → 1800 tokens)
- [ ] Add configuration parameter in settings
- [ ] Update all tests to use new chunk size
- [ ] Add 8 unit tests + 4 integration tests

### Post-Implementation (Sprint 21 End)
- [ ] Update all scripts to use new pipeline
- [ ] Run full test suite (old + new tests)
- [ ] Performance benchmarking (compare to Sprint 20)
- [ ] Update documentation (README, CONTEXT_REFRESH)
- [ ] Git commit: "feat(sprint21): Container-based Docling + LangGraph pipeline"

### Sprint 22 (Cleanup)
- [ ] Remove deprecated UnifiedIngestionPipeline
- [ ] Remove deprecated load_documents()
- [ ] Remove old integration tests
- [ ] Remove deprecated scripts
- [ ] Update DECISION_LOG.md

---

## Risk Assessment

### High Risk
1. **Memory Constraints (4.4GB RAM):**
   - **Mitigation:** Sequential pipeline, container stop between batches
   - **Testing:** Load tests with 100 documents (Feature 21.3)

2. **Docker GPU Access (Windows):**
   - **Mitigation:** WSL2 + NVIDIA Container Toolkit setup
   - **Testing:** Real GPU integration tests (Feature 21.1)

### Medium Risk
1. **Chunk Size Change (600 → 1800):**
   - **Impact:** All existing vectors incompatible
   - **Mitigation:** Full reindex required
   - **Testing:** Compare retrieval quality (Sprint 21 vs Sprint 20)

2. **LangGraph State Serialization:**
   - **Impact:** Redis checkpointing (TD-38)
   - **Mitigation:** Defer to Sprint 22, use in-memory state for Sprint 21

### Low Risk
1. **Test Duplication (old + new):**
   - **Impact:** 2x CI/CD time
   - **Mitigation:** Remove old tests in Sprint 22

---

## Appendix: File Inventory

### Files to Deprecate (Sprint 21)
1. `src/components/vector_search/ingestion.py` (lines 128-183)
2. `src/components/shared/unified_ingestion.py` (entire class)
3. `scripts/index_documents.py`
4. `scripts/index_one_doc_test.py`
5. `scripts/clear_and_reindex.py`
6. `tests/components/vector_search/test_ingestion.py`
7. `tests/components/shared/test_unified_ingestion.py`
8. `tests/e2e/test_unified_ingestion_e2e.py`

### Files to Preserve (No Changes)
1. `src/core/chunking_service.py` ✅
2. `src/components/shared/embedding_service.py` ✅
3. `src/components/graph_rag/three_phase_extractor.py` ✅
4. `src/components/graph_rag/lightrag_wrapper.py` ✅
5. `src/components/vector_search/qdrant_client.py` ✅
6. `src/core/chunk.py` ✅

### Files to Create (Sprint 21)
1. `src/components/ingestion/docling_client.py` (Feature 21.1)
2. `src/components/ingestion/langgraph_pipeline.py` (Feature 21.2)
3. `src/components/ingestion/batch_orchestrator.py` (Feature 21.3)
4. `tests/components/ingestion/test_docling_client.py`
5. `tests/components/ingestion/test_langgraph_nodes.py`
6. `tests/components/ingestion/test_batch_orchestrator.py`
7. `tests/e2e/test_ingestion_pipeline_e2e.py`
8. `scripts/batch_ingest_langgraph.py`

---

**End of Integration Analysis**
