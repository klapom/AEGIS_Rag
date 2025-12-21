# Sprint 61: Performance Optimizations & Section-Aware Features

**Sprint Duration:** 2-3 weeks
**Total Story Points:** 74 SP
**Priority:** HIGH (Performance + Production-Readiness)
**Dependencies:** Sprint 60 Complete ✅

---

## Executive Summary

Sprint 61 focuses on **high-ROI performance optimizations** and **activating dormant section-aware features**. Based on Sprint 60 technical investigations, we identified:
- **2 critical migrations** (Embeddings + Reranking: 3-50x speedups)
- **1 cleanup task** (deprecated endpoints)
- **4 Ollama optimizations** (+30-50% throughput)
- **9 section-aware features** (currently unused despite implementation)
- **1 temporal tracking** (minimum viable GRAPHITI integration)

**Expected Impact:**
- Query latency: **-100ms** (embeddings: -80ms, reranking: -20ms)
- Ingestion speed: **+1500%** (batch embeddings 16x faster)
- Ollama throughput: **+30-50%** (configuration tuning + batching)
- Section utilization: **0% → 80%** (activate existing infrastructure)
- Temporal tracking: **Basic audit trail** (who/when/what changed)

---

## Wave 1: Critical Performance Migrations (19 SP)

### Feature 61.1: Native Sentence-Transformers Embeddings (8 SP)

**Priority:** P0 (Highest ROI)
**Status:** READY (investigation complete in Sprint 60)
**Dependencies:** None

**Rationale (from TD-073):**
- **Performance:** 3-5x faster (20ms vs 100ms single, 16x batch)
- **Memory:** -60% VRAM (2GB vs 5GB)
- **Quality:** IDENTICAL (same BGE-M3 weights)
- **Risk:** VERY LOW (same model, verified cu130 compatibility)

#### Tasks

1. **Install Dependencies (1 SP)**
   ```bash
   # Update docker/Dockerfile.api
   pip install sentence-transformers>=2.5.0 --index-url https://download.pytorch.org/whl/cu130

   # DGX Spark specific
   export TORCH_CUDA_ARCH_LIST="12.1a"
   export CUDACXX=/usr/local/cuda-13.0/bin/nvcc
   ```

2. **Implement NativeEmbeddingService (2 SP)**
   - **File:** `src/domains/vector_search/embedding/native_embedding_service.py`
   - **Class:** `NativeEmbeddingService`
   - **Methods:**
     - `__init__()` - Load BGE-M3, apply Flash Attention workaround
     - `embed()` - Batch embedding with normalization
     - `dimension` property - Return 1024
   - **Code:**
     ```python
     from sentence_transformers import SentenceTransformer
     import torch

     class NativeEmbeddingService:
         def __init__(self):
             # Flash Attention workaround for DGX Spark sm_121
             torch.backends.cuda.enable_flash_sdp(False)
             torch.backends.cuda.enable_mem_efficient_sdp(True)

             self.model = SentenceTransformer("BAAI/bge-m3", device="cuda")

         def embed(self, texts, batch_size=32, normalize=True):
             if isinstance(texts, str):
                 texts = [texts]
             return self.model.encode(
                 texts,
                 batch_size=batch_size,
                 normalize_embeddings=normalize,
                 show_progress_bar=False
             ).tolist()
     ```

3. **Update Embedding Service Factory (1 SP)**
   - **File:** `src/domains/vector_search/embedding/factory.py` (new)
   - **Feature flag:** `EMBEDDING_BACKEND` (env var)
   - **Options:** `"native"` (new) or `"ollama"` (legacy)

4. **Quality Verification Tests (1 SP)**
   - **File:** `tests/unit/domains/vector_search/test_embedding_parity.py`
   - **Test:** Cosine similarity(Ollama, Native) == 1.0
   - **Coverage:** 1000 test texts

5. **Performance Benchmarking (1 SP)**
   - **Metrics:** Single embedding latency, batch latency, throughput
   - **Target:** 3-5x speedup confirmed
   - **File:** `tests/benchmarks/test_embedding_performance.py`

6. **Integration & Migration (1 SP)**
   - Update `src/components/shared/embedding_service.py` to use factory
   - Gradual rollout with feature flag
   - Monitor VRAM usage (should drop from 5GB to 2GB)

7. **Documentation (1 SP)**
   - **ADR:** `docs/adr/ADR-049-NATIVE_SENTENCE_TRANSFORMERS.md`
   - Update `docs/TECH_STACK.md`

**Acceptance Criteria:**
- [x] Native embeddings 3-5x faster than Ollama
- [x] Quality parity: Cosine sim == 1.0
- [x] VRAM usage <2.5GB (vs 5GB before)
- [x] Backward compatible (feature flag rollback)
- [x] 80%+ test coverage

**CUDA Version Note (DGX Spark sm_121):**
```markdown
## CUDA 13.0 Requirement for DGX Spark

**Hardware:** NVIDIA GB10 (Blackwell Architecture)
- **CUDA Capability:** sm_121 / sm_121a (August 2025)
- **Installed CUDA:** 13.0
- **Why cu130 Required:**
  - CUDA 13.0 is first version supporting sm_121 (Blackwell GPUs)
  - Older CUDA (12.8, 12.1, 11.8) only support up to sm_120
  - Performance penalty: cu128 is **3x slower** (30+ sec/iter vs 10-12 sec/iter)

**PyTorch Compatibility:**
- PyTorch 2.4: Supports CUDA 11.8, 12.1, 12.4 (NOT 13.0)
- PyTorch 2.9+: Supports CUDA 13.0 (cu130 wheels)
- Sentence-Transformers: No direct CUDA dependency (uses PyTorch)

**Correct Installation:**
```bash
# PyTorch cu130 (for DGX Spark sm_121)
pip install torch>=2.9.0 --index-url https://download.pytorch.org/whl/cu130

# Sentence-Transformers (works with any PyTorch CUDA version)
pip install sentence-transformers>=2.5.0

# Flash Attention Workaround (sm_121 not yet supported by FA2)
python -c "import torch; torch.backends.cuda.enable_flash_sdp(False)"
```

**Alternative CUDA Versions (NOT RECOMMENDED):**
- CUDA 12.8/12.1: Works but 3x slower (sm_120 fallback)
- CUDA 11.8: Works but 3x slower + no modern features
```

---

### Feature 61.2: Cross-Encoder Reranking (9 SP)

**Priority:** P0 (Highest ROI)
**Status:** READY (investigation complete in Sprint 60)
**Dependencies:** Feature 61.1 (same sentence-transformers library)

**Rationale (from TD-072):**
- **Performance:** 50x faster (120ms vs 2000ms for 20 docs)
- **Quality:** Better (NDCG@10: 0.87 vs 0.85 LLM est.)
- **Ollama Load:** -20% (frees LLM for generation)
- **Risk:** LOW (well-tested models, standard PyTorch ops)

#### Tasks

1. **Implement CrossEncoderReranker (2 SP)**
   - **File:** `src/domains/vector_search/reranking/cross_encoder_reranker.py`
   - **Class:** `CrossEncoderReranker`
   - **Model:** `BAAI/bge-reranker-base` (quality-speed balance)
   - **Methods:**
     - `__init__()` - Load model, apply Flash Attention workaround
     - `rerank()` - Score query-doc pairs, return sorted indices

2. **Integrate with Hybrid Search (2 SP)**
   - **File:** `src/agents/vector_search.py`
   - **Update:** Hybrid search agent to use Cross-Encoder
   - **Flow:**
     ```python
     # Before (LLM reranking)
     results = hybrid_search(query, top_k=20)

     # After (Cross-Encoder)
     raw_results = hybrid_search(query, top_k=100)  # Get more candidates
     reranker = CrossEncoderReranker()
     reranked = reranker.rerank(query, [r["text"] for r in raw_results], top_k=20)
     final_results = [raw_results[idx] for idx, score in reranked]
     ```

3. **Verify Current Ollama Reranker Status (1 SP)**
   - **Search:** `src/components/retrieval/reranker.py` (referenced in TD-072)
   - **Check:** Is Ollama reranking actually implemented?
   - **Action:** If YES → migration, if NO → direct implementation

4. **Unit Tests (1 SP)**
   - **File:** `tests/unit/domains/vector_search/test_cross_encoder.py`
   - **Tests:**
     - Reranking correctness (higher score for relevant docs)
     - Batch processing (100 docs)
     - Performance (latency <150ms for 20 docs)

5. **Integration Tests (1 SP)**
   - **File:** `tests/integration/agents/test_reranking_agent.py`
   - **Test:** Full query flow with Cross-Encoder

6. **Benchmarking (1 SP)**
   - **Compare:** Cross-Encoder vs Ollama (if exists)
   - **Metrics:** Latency, quality (NDCG), Ollama load reduction
   - **Target:** 50x speedup confirmed

7. **Documentation (1 SP)**
   - **ADR:** `docs/adr/ADR-050-CROSS_ENCODER_RERANKING.md`
   - Update `docs/components/RERANKING.md` (new)

**Acceptance Criteria:**
- [x] Reranking <150ms for 20 docs (vs ~2000ms LLM)
- [x] Quality: NDCG@10 ≥0.85
- [x] Ollama load reduction measurable
- [x] 80%+ test coverage

---

### Feature 61.3: Remove Deprecated Multihop Endpoints (2 SP)

**Priority:** P2 (Cleanup)
**Status:** READY (reviewed in Sprint 60 TD-069)
**Dependencies:** None

**Rationale:**
- **5 deprecated endpoints** in `graph_viz.py` (unused for 12+ months)
- **Zero frontend integration**
- **Zero backend usage** (agents use LightRAG, not REST API)

#### Tasks

1. **Remove Endpoints (1 SP)**
   - **File:** `src/api/routers/graph_viz.py`
   - **Delete:**
     - `POST /multi-hop` (lines 752-884)
     - `POST /shortest-path` (lines 889-960)
     - `GET /export/formats` (line 340)
     - `POST /filter` (line 367)
     - `POST /communities/highlight` (line 424)
   - **Delete Models:**
     - `MultiHopRequest`, `MultiHopResponse`
     - `ShortestPathRequest`, `ShortestPathResponse`
     - `GraphNode`, `GraphEdge`, `PathRelationship`

2. **Archive Documentation (0.5 SP)**
   - **Already archived:** `docs/archive/api/MULTI_HOP_ENDPOINTS.md`
   - **Already archived:** `docs/archive/sprints/SPRINT_34_FEATURE_34.5_MULTI_HOP_API.md`

3. **Keep Integration Tests (0.5 SP)**
   - **File:** `tests/integration/components/test_multi_hop_query.py`
   - **Keep:** Tests query decomposition logic (not deprecated API)
   - **Rename:** `test_multi_hop_query_logic.py` (clarify scope)

**Acceptance Criteria:**
- [x] 5 deprecated endpoints removed
- [x] All tests pass
- [x] OpenAPI docs updated (auto-generated)
- [x] No breaking changes (endpoints unused)

---

## Wave 2: Ollama Performance Tuning (10 SP)

### Feature 61.4: Ollama Configuration Optimization (3 SP)

**Priority:** P1 (Low-hanging fruit)
**Status:** READY (researched by Haiku subagent)
**Dependencies:** None

**Rationale (from Ollama research):**
- **Throughput:** +30% via `OLLAMA_NUM_PARALLEL=4`
- **Latency:** +10-14% via `OLLAMA_NUM_THREADS=16`
- **Warm time:** -3-5s via `OLLAMA_KEEP_ALIVE=30m`
- **Effort:** 2-3 SP (pure configuration)

#### Tasks

1. **Update docker-compose.dgx-spark.yml (1 SP)**
   ```yaml
   services:
     api:
       environment:
         # Ollama Performance Tuning (Sprint 61)
         OLLAMA_NUM_PARALLEL: "4"       # Process 4 concurrent requests
         OLLAMA_NUM_THREADS: "16"       # CPU threads for attention
         OLLAMA_KEEP_ALIVE: "30m"       # Keep model loaded
         OLLAMA_FLASH_ATTENTION: "0"    # Disable (sm_121 workaround)

         # Existing vars...
         OLLAMA_BASE_URL: "http://localhost:11434"
         OLLAMA_MODEL_GENERATION: "llama3.2:8b"
   ```

2. **Verify Quantization Settings (0.5 SP)**
   - **Current:** Q4_K_M (proven optimal per research)
   - **Action:** Document as optimal in `docs/TECH_STACK.md`
   - **No change needed**

3. **Benchmarking (1 SP)**
   - **Before:** Baseline throughput, latency
   - **After:** Measure +30% throughput gain
   - **File:** `tests/benchmarks/test_ollama_performance.py`

4. **Documentation (0.5 SP)**
   - **File:** `docs/analysis/OLLAMA_OPTIMIZATION_OPPORTUNITIES_SPRINT61.md` (already exists from subagent)
   - **Update:** `docs/TECH_STACK.md` with optimal settings

**Acceptance Criteria:**
- [x] Throughput +25-35%
- [x] Latency impact <10ms
- [x] VRAM <10GB (current ~8.6GB)
- [x] Model stays loaded (no reload delays)

**Expected Metrics:**
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Throughput | 30-40 tok/s | 40-52 tok/s | +30% |
| Single Query Latency | 50ms | 45ms | -10% |
| Memory | 8.6GB | 9-10GB | +5% (acceptable) |

---

### Feature 61.5: Request Batching (3 SP) - CONDITIONAL

**Priority:** P2 (Only if concurrent users >5)
**Status:** READY (design complete from research)
**Dependencies:** Feature 61.4
**Trigger:** Implement ONLY if monitoring shows concurrent users >5

#### Tasks

1. **Implement BatchProcessor (2 SP)**
   - **File:** `src/domains/llm_integration/proxy/batch_processor.py`
   - **Class:** `BatchProcessor`
   - **Logic:**
     - Accumulate requests in 50ms window
     - Batch size matches `OLLAMA_NUM_PARALLEL=4`
     - Send batch to Ollama
     - Distribute responses

2. **Integration (0.5 SP)**
   - **File:** `src/domains/llm_integration/proxy/aegis_proxy.py`
   - **Update:** `AegisLLMProxy.generate()` to use BatchProcessor

3. **Tests & Benchmarks (0.5 SP)**
   - **Test:** Burst scenarios (10 concurrent requests)
   - **Verify:** +30-50% throughput for bursts

**Acceptance Criteria:**
- [x] Throughput +30-50% for concurrent requests
- [x] Latency penalty: +50ms (batching window)
- [x] Graceful degradation (no batching if load low)

**Decision Point:** Check load metrics in Week 2 of Sprint 61. Skip if <5 concurrent users.

---

### Feature 61.6: Redis Semantic Caching (5 SP) - DEFERRED to Sprint 62

**Priority:** P3 (High impact but deferred)
**Status:** DESIGN READY (research complete)
**Dependencies:** Redis already deployed
**Trigger:** Deferred to Sprint 62-63 (load-dependent)

**Rationale:**
- **Cache hit rate:** 85-90% expected
- **Speedup:** 10x (500ms → 50ms for cached)
- **Complexity:** Medium (2-phase implementation)

**Sprint 62 Scope (if triggered):**
- Phase 1: Exact-match caching (3 SP)
- Phase 2: Semantic similarity caching (2 SP)

---

## Wave 3: Section-Aware Features Activation (33 SP)

**Context:** Sprint 60 analysis revealed **Section Nodes & Metadata exist but are 80% unused**. Wave 3 activates this dormant infrastructure.

### Feature 61.7: Section-Aware Graph Queries (5 SP)

**Priority:** P1 (Unlock Neo4j Section Nodes)
**Status:** Infrastructure exists, needs query implementation
**Dependencies:** None

**Current Status (from analysis):**
- ✅ Section nodes created in Neo4j (Sprint 32-33)
- ✅ Relationships: `HAS_SECTION`, `CONTAINS_CHUNK`, `DEFINES`
- ❌ **NEVER QUERIED** by agents

#### Tasks

1. **Implement Section Query Templates (2 SP)**
   - **File:** `src/components/graph_rag/query_templates.py`
   - **New Queries:**
     ```cypher
     # Find entities in specific section
     MATCH (s:Section {heading: $section_heading})-[:DEFINES]->(e:Entity)
     RETURN e

     # Find relationships within section
     MATCH (s:Section)-[:CONTAINS_CHUNK]->(c:Chunk)
     MATCH (e1:Entity)-[:MENTIONED_IN]->(c)
     MATCH (e2:Entity)-[:MENTIONED_IN]->(c)
     MATCH (e1)-[r:RELATES_TO]-(e2)
     RETURN e1, r, e2

     # Section-scoped multi-hop
     MATCH (s:Section {heading: $section})-[:DEFINES]->(start:Entity)
     MATCH path = (start)-[:RELATES_TO*1..2]-(connected:Entity)
     RETURN path
     ```

2. **Update Graph Agent (2 SP)**
   - **File:** `src/agents/graph_query.py`
   - **New Method:** `query_section_entities(section_heading)`
   - **Integration:** Router agent detects "in section X" queries

3. **Integration Tests (1 SP)**
   - **File:** `tests/integration/agents/test_section_graph_queries.py`
   - **Tests:**
     - Query entities in section
     - Section-scoped relationships
     - Multi-hop from section

**Acceptance Criteria:**
- [x] Agent can answer "What entities are in section X?"
- [x] Section-scoped graph traversal works
- [x] 80%+ test coverage

**Use Cases:**
- "Explain the Load Balancing section and related technologies"
- "What are the key concepts in Chapter 3?"
- "Find all entities mentioned in the Architecture section"

---

### Feature 61.8: Multi-Section Metadata in Vector Search (3 SP)

**Priority:** P1 (Activate existing Qdrant metadata)
**Status:** Metadata exists, needs query integration
**Dependencies:** None

**Current Status:**
- ✅ Metadata stored in Qdrant (`section_headings`, `primary_section`, etc.)
- ❌ **NOT USED** in search filters or ranking

#### Tasks

1. **Section-Based Filtering (1 SP)**
   - **File:** `src/components/vector_search/qdrant_client.py`
   - **Add Filter Parameter:**
     ```python
     def search(
         self,
         query_vector,
         limit,
         section_filter: str | None = None  # NEW
     ):
         if section_filter:
             # Filter by primary_section or section_headings contains
             filters = {"primary_section": section_filter}
     ```

2. **Activate Section Reranking (1 SP)**
   - **File:** `src/components/vector_search/hybrid_search.py`
   - **Current:** `section_based_reranking()` exists but NOT called
   - **Fix:** Integrate into `FourWayHybridSearch` (Feature 42)

3. **Integration Tests (1 SP)**
   - **Test:** "Find answers in section X" queries
   - **Verify:** Section boost applied correctly

**Acceptance Criteria:**
- [x] Can filter search by section name
- [x] Section name boost active in reranking
- [x] Performance impact <10ms

---

### Feature 61.9: VLM Image Integration with Sections (5 SP)

**Priority:** P1 (Close critical gap)
**Status:** VLM exists, Section exists, NOT linked
**Dependencies:** None

**Current Status (from analysis):**
- ✅ VLM generates image descriptions (Sprint 21)
- ✅ Sections extracted and chunked (Sprint 32)
- ❌ **NO CONNECTION:** VLM descriptions stored separately

#### Tasks

1. **Map Images to Sections (2 SP)**
   - **File:** `src/components/ingestion/nodes/image_enrichment.py`
   - **Logic:**
     - Match image page_no + bbox to section bbox
     - Insert VLM description into section text
     - Track image metadata in section

2. **Update Chunking (1 SP)**
   - **File:** `src/components/ingestion/nodes/adaptive_chunking.py`
   - **Integration:** Include VLM descriptions when merging sections

3. **Neo4j Section Nodes (1 SP)**
   - **File:** `src/components/graph_rag/neo4j_client.py`
   - **Add Property:** `Section.has_images: bool`, `Section.image_count: int`

4. **Tests (1 SP)**
   - **Test:** VLM descriptions appear in chunk text
   - **Test:** Section nodes track image presence

**Acceptance Criteria:**
- [x] VLM descriptions embedded in section chunks
- [x] Image metadata in section nodes
- [x] No duplicate text (VLM only added once)

**Impact:** Queries like "Explain the architecture diagram" can now retrieve VLM descriptions within section context.

---

### Feature 61.10: Section-Aware Citation Enhancement (3 SP)

**Priority:** P2 (Improve UX)
**Status:** Partially implemented, needs API exposure
**Dependencies:** Features 61.7, 61.8

**Current Status:**
- ✅ `_build_citation_map()` includes section metadata
- ❌ Chat API may not fully expose sections to frontend

#### Tasks

1. **Update Citation Format (1 SP)**
   - **File:** `src/agents/answer_generator.py`
   - **Enhance:** Include `section_headings` + `primary_section` + `page_no`
   - **Format:** `"Section: 'Multi-Server Architecture' (Page 1, Chunk 3)"`

2. **API Exposure (1 SP)**
   - **File:** `src/api/v1/chat.py`
   - **Verify:** Citation map includes section data in SSE stream
   - **Test:** Frontend receives section info

3. **Integration Test (1 SP)**
   - **File:** `tests/integration/api/test_section_citations.py`
   - **Test:** End-to-end citation with sections

**Acceptance Criteria:**
- [x] Citations include section name + page
- [x] Frontend displays section info
- [x] Backward compatible (works without sections)

---

### Feature 61.11: Section-Aware Reranking Full Integration (2 SP)

**Priority:** P1 (Activate existing code)
**Status:** Code exists, NOT called in production
**Dependencies:** Feature 61.2 (Cross-Encoder)

**Current Status:**
- ✅ `section_based_reranking()` implemented
- ❌ NOT called by `FourWayHybridSearch`

#### Tasks

1. **Integrate into Hybrid Search (1 SP)**
   - **File:** `src/components/vector_search/hybrid_search.py`
   - **Update:** Call `section_based_reranking()` after RRF fusion
   - **Order:** RRF → Section Boost → Cross-Encoder

2. **Tests (1 SP)**
   - **Test:** Section name in query boosts relevant chunks
   - **Verify:** Works with Cross-Encoder

**Acceptance Criteria:**
- [x] Section boost active in production
- [x] Combines with Cross-Encoder correctly
- [x] Performance impact <15ms

---

### Feature 61.12: HAS_SUBSECTION Hierarchical Links (3 SP)

**Priority:** P2 (Enhance Section Hierarchy)
**Status:** Gap identified in Sprint 60
**Dependencies:** Feature 61.7

**Current Status:**
- ✅ `HAS_SECTION` (Document → Section)
- ❌ **MISSING:** `HAS_SUBSECTION` (Section → Section)

#### Tasks

1. **Implement Hierarchy Detection (1 SP)**
   - **File:** `src/components/ingestion/nodes/section_extraction.py`
   - **Logic:** Detect parent-child from heading levels
     ```python
     # Example: Level 1 heading "Architecture"
     #          Level 2 heading "Load Balancing" (child of Architecture)
     if section.level > parent.level:
         create HAS_SUBSECTION relationship
     ```

2. **Update Neo4j Client (1 SP)**
   - **File:** `src/components/graph_rag/neo4j_client.py`
   - **Add Relationship:** `(parent:Section)-[:HAS_SUBSECTION {level_diff}]->(child:Section)`

3. **Query Templates (0.5 SP)**
   - **New Query:** "Get all subsections of X"
     ```cypher
     MATCH (parent:Section {heading: $parent})-[:HAS_SUBSECTION*]->(child:Section)
     RETURN child
     ORDER BY child.order
     ```

4. **Tests (0.5 SP)**
   - **Test:** Hierarchical section queries
   - **Test:** Multi-level traversal

**Acceptance Criteria:**
- [x] Section hierarchy queryable
- [x] Agent can expand "Show all subsections of X"
- [x] Backward compatible (works without subsections)

---

### Feature 61.13: Document Type Support for Sections (5 SP)

**Priority:** P2 (Expand coverage)
**Status:** Currently PDF/PPTX only (via Docling)
**Dependencies:** None

**Current Status:**
- ✅ **PDF:** Sections extracted via Docling
- ✅ **PPTX:** Slide titles as sections
- ❌ **Markdown:** Not section-aware
- ❌ **DOCX:** May not preserve headings
- ❌ **TXT:** No structure

#### Tasks

1. **Markdown Section Extraction (2 SP)**
   - **File:** `src/components/ingestion/parsers/markdown_parser.py` (new)
   - **Logic:** Parse `#` headers as sections
     ```python
     # Heading Level 1 → Section Level 1
     # Heading Level 2 → Section Level 2
     # etc.
     ```

2. **DOCX Heading Preservation (1 SP)**
   - **File:** Enhance Docling DOCX parser config
   - **Ensure:** Headings marked with style metadata

3. **TXT Heuristic Section Detection (1 SP)**
   - **File:** `src/components/ingestion/parsers/txt_parser.py`
   - **Heuristics:**
     - ALL CAPS lines (e.g., "CHAPTER 1: INTRODUCTION")
     - Numbered sections (e.g., "1. Architecture")
     - Empty line + capitalized line

4. **Tests (1 SP)**
   - **Test:** Markdown sections extracted correctly
   - **Test:** DOCX headings preserved
   - **Test:** TXT heuristics work

**Acceptance Criteria:**
- [x] Markdown: Sections from headers
- [x] DOCX: Headings extracted
- [x] TXT: Basic section detection
- [x] Backward compatible (no sections = whole doc)

**Supported Document Types After Feature:**
| Type | Section Support | Method |
|------|----------------|--------|
| PDF | ✅ Full | Docling layout analysis |
| PPTX | ✅ Full | Slide titles |
| Markdown | ✅ Full | Header parsing |
| DOCX | ✅ Partial | Heading styles |
| TXT | ⚠️ Heuristic | Capitalization + numbering |
| HTML | ❌ Future | Header tags (`<h1>`, `<h2>`) |

---

### Feature 61.14: Section-Based Community Detection (3 SP)

**Priority:** P3 (Advanced graph analysis)
**Status:** Gap identified
**Dependencies:** Feature 61.7

**Current Status:**
- ✅ Communities detected globally (Leiden algorithm)
- ❌ Communities NOT scoped to sections

#### Tasks

1. **Section-Scoped Community Detection (2 SP)**
   - **File:** `src/components/graph_rag/neo4j_client.py`
   - **New Method:** `detect_communities_in_section(section_heading)`
   - **Logic:** Run Leiden only on entities in section

2. **Query Templates (0.5 SP)**
   - **Query:** "Find entity clusters in section X"

3. **Tests (0.5 SP)**
   - **Test:** Section communities separate from global
   - **Test:** Community stats per section

**Acceptance Criteria:**
- [x] Can detect communities per section
- [x] Section community stats available
- [x] Doesn't break global community detection

---

### Feature 61.15: Section Analytics Endpoint (2 SP)

**Priority:** P3 (Observability)
**Status:** NEW
**Dependencies:** Features 61.7, 61.14

#### Tasks

1. **Implement Endpoint (1 SP)**
   - **File:** `src/api/v1/analytics.py` (new)
   - **Endpoint:** `GET /api/v1/analytics/sections`
   - **Stats:**
     - Section count per document
     - Entity count per section
     - Relation count per section
     - Community count per section

2. **Tests (1 SP)**
   - **Test:** Stats accurate
   - **Test:** Performance <500ms

**Acceptance Criteria:**
- [x] Analytics endpoint returns section stats
- [x] Integrated with admin dashboard (future)

---

## Wave 4: Temporal Tracking - Minimum Viable (8 SP)

### Feature 61.16: Basic Temporal Audit Trail (8 SP)

**Priority:** P2 (Minimum viable temporal tracking)
**Status:** NEW (based on GRAPHITI analysis)
**Dependencies:** None

**Rationale:**
- **User Need:** "Who changed what and when?" (basic audit trail)
- **GRAPHITI Status:** Episode-based provenance (NOT bi-temporal queries)
- **Neo4j Status:** Bi-temporal implemented (Sprint 39) but complex
- **Decision:** **Minimum viable = Entity/Relation change tracking**

#### Minimum Viable Temporal (NOT Full Bi-Temporal)

**Scope:**
1. Track when entities/relations are created/updated
2. Log WHO made the change (user_id or "system")
3. Simple queries: "Show changes in last 7 days"
4. **NOT implementing:** Point-in-time queries, time-travel, full bi-temporal

**Rationale:**
- Full bi-temporal queries (GRAPHITI analysis) require 21+ SP
- User primarily needs audit trail, not time-travel
- Can upgrade to full bi-temporal later (Sprint 65+)

#### Tasks

1. **Add Temporal Properties to Neo4j (2 SP)**
   - **File:** `src/components/graph_rag/neo4j_client.py`
   - **Add Properties:**
     ```cypher
     Entity: created_at, updated_at, created_by, updated_by
     Relation: created_at, updated_at, created_by, updated_by
     ```
   - **Update:** Creation and update methods

2. **Change Log Table (2 SP)**
   - **File:** `src/core/database/change_log.py` (new)
   - **Schema:**
     ```sql
     CREATE TABLE change_log (
         id SERIAL PRIMARY KEY,
         entity_id VARCHAR,
         entity_type VARCHAR,
         change_type VARCHAR, -- 'create', 'update', 'delete'
         changed_by VARCHAR,
         changed_at TIMESTAMP,
         changes JSONB  -- {field: {old, new}}
     )
     ```

3. **Change Tracking Service (2 SP)**
   - **File:** `src/domains/knowledge_graph/tracking/change_tracker.py`
   - **Methods:**
     - `log_entity_change(entity, change_type, user)`
     - `log_relation_change(relation, change_type, user)`
     - `get_recent_changes(days=7)`

4. **API Endpoint (1 SP)**
   - **File:** `src/api/v1/audit.py` (new)
   - **Endpoint:** `GET /api/v1/audit/changes?days=7`
   - **Response:** List of recent changes

5. **Tests (1 SP)**
   - **Test:** Changes logged correctly
   - **Test:** Recent changes query works
   - **Test:** Audit trail accurate

**Acceptance Criteria:**
- [x] Every entity/relation change logged
- [x] Can query "Show changes in last N days"
- [x] Audit trail includes WHO, WHEN, WHAT
- [x] Performance impact <20ms per write

**What About GRAPHITI?**
- **Keep GRAPHITI:** Still useful for episodic memory (conversations)
- **Use Case Split:**
  - **Neo4j Audit Trail:** Who/when/what changed (entities/relations)
  - **GRAPHITI Episodes:** Conversational provenance (which conversation mentioned X)
- **3-Layer Memory Intact:**
  - Redis: Short-term
  - Qdrant: Semantic
  - Graphiti: Episodic + Temporal provenance

---

## Wave 5: Agent Use Cases for Multihop (Deferred to Sprint 62)

### Research Question: Multihop Endpoint Use Cases for Agents?

**Analysis:**
The multihop endpoints (`/multi-hop`, `/shortest-path`) were deprecated because:
1. Frontend doesn't use them (client-side graph interaction)
2. Backend agents use LightRAG directly (not REST API)

**Potential Agent Use Cases:**
1. **Agent-to-Agent Communication:**
   - External agents (MCP clients) query graph via REST API
   - Multi-hop useful for "find related entities" without LightRAG access

2. **Agentic Research Agent (Sprint 59):**
   - Research agent could use multihop to explore knowledge graph
   - "Find all technologies related to X within 2 hops"

3. **Dynamic Graph Exploration:**
   - Agent doesn't know graph structure in advance
   - Multi-hop API provides exploratory queries

**Decision:**
- **Sprint 61:** Remove deprecated endpoints (Feature 61.3)
- **Sprint 62:** **IF** MCP client or research agent needs graph exploration:
  - Redesign as **internal API** (not public REST)
  - Or integrate into LightRAG query templates

**Deferred to Sprint 62** (pending agent usage analysis)

---

## Sprint 61 Feature Summary

| Wave | Feature | SP | Priority | Dependencies |
|------|---------|-------|----------|--------------|
| **Wave 1** | | **19 SP** | | |
| 1 | Native Sentence-Transformers Embeddings | 8 | P0 | None |
| 1 | Cross-Encoder Reranking | 9 | P0 | 61.1 |
| 1 | Remove Deprecated Multihop Endpoints | 2 | P2 | None |
| **Wave 2** | | **10 SP** | | |
| 2 | Ollama Configuration Optimization | 3 | P1 | None |
| 2 | Request Batching (Conditional) | 3 | P2 | 61.4 |
| 2 | Redis Semantic Caching (Deferred) | 5 | P3 | Deferred |
| **Wave 3** | | **33 SP** | | |
| 3 | Section-Aware Graph Queries | 5 | P1 | None |
| 3 | Multi-Section Metadata in Vector Search | 3 | P1 | None |
| 3 | VLM Image Integration with Sections | 5 | P1 | None |
| 3 | Section-Aware Citation Enhancement | 3 | P2 | 61.7, 61.8 |
| 3 | Section-Aware Reranking Integration | 2 | P1 | 61.2 |
| 3 | HAS_SUBSECTION Hierarchical Links | 3 | P2 | 61.7 |
| 3 | Document Type Support for Sections | 5 | P2 | None |
| 3 | Section-Based Community Detection | 3 | P3 | 61.7 |
| 3 | Section Analytics Endpoint | 2 | P3 | 61.7, 61.14 |
| **Wave 4** | | **8 SP** | | |
| 4 | Basic Temporal Audit Trail | 8 | P2 | None |
| **TOTAL** | | **74 SP** | | |

**Deferred to Sprint 62:**
- Redis Semantic Caching (5 SP)
- Multihop Agent Use Cases (Research + potential reimplementation)

---

## Execution Strategy

### Parallel Execution (3 Weeks)

**Week 1: Critical Performance (19 SP)**
- 3 Agents in parallel:
  - Agent 1: Feature 61.1 (Embeddings)
  - Agent 2: Feature 61.2 (Reranking)
  - Agent 3: Feature 61.3 + 61.4 (Cleanup + Ollama)

**Week 2: Section Features Wave A (20 SP)**
- 3 Agents in parallel:
  - Agent 1: Features 61.7, 61.11 (Graph queries + Reranking)
  - Agent 2: Features 61.8, 61.9 (Metadata + VLM)
  - Agent 3: Features 61.10, 61.12 (Citations + Hierarchy)

**Week 3: Section Features Wave B + Temporal (16 SP)**
- 2 Agents:
  - Agent 1: Features 61.13, 61.14, 61.15 (Doc types + Analytics)
  - Agent 2: Feature 61.16 (Temporal tracking)

**Conditional Features:**
- Feature 61.5 (Batching): Check load in Week 2
  - IF concurrent users >5 → implement
  - ELSE → defer to Sprint 62

---

## Success Metrics

### Performance Targets

| Metric | Sprint 60 Baseline | Sprint 61 Target | Improvement |
|--------|-------------------|------------------|-------------|
| **Query Latency (p95)** | 200ms | 100ms | **-50%** |
| **Embedding (single)** | 100ms | 20-30ms | **-70-80%** |
| **Embedding (batch 32)** | 500ms | 200ms | **-60%** |
| **Reranking (20 docs)** | ~2000ms (LLM est.) | 120ms | **-94%** |
| **Ollama Throughput** | 30-40 tok/s | 40-52 tok/s | **+30%** |
| **VRAM (Embeddings)** | ~5GB | ~2GB | **-60%** |
| **VRAM (Reranking)** | ~5GB (LLM) | ~0.6GB | **-88%** |
| **Section Utilization** | 0% | 80% | **+80%** |

### Feature Adoption

| Feature | Before | After | Target |
|---------|--------|-------|--------|
| **Section-Aware Queries** | 0% | 80% | Agents use sections |
| **VLM Integration** | 0% | 100% | Images in sections |
| **Citation Sections** | 0% | 100% | All citations have sections |
| **Temporal Audit** | 0% | 100% | All changes logged |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **DGX Spark cu130 Issues** | Low | High | PyTorch 2.9+ verified, Flash Attention workaround documented |
| **Performance Regression** | Low | Medium | Extensive benchmarking, feature flags for rollback |
| **Section Integration Bugs** | Medium | Medium | Comprehensive integration tests, gradual rollout |
| **VLM Section Mapping** | Medium | Medium | Bbox matching algorithm, fallback to whole-doc |
| **Temporal Overhead** | Low | Low | Async logging, <20ms overhead target |
| **Ollama Config Impact** | Low | Low | Incremental tuning, rollback via env vars |

**Overall Risk:** **MEDIUM-LOW** - Well-researched migrations, existing infrastructure activation

---

## Dependencies

**External:**
- PyTorch 2.9+ with CUDA 13.0 (cu130 wheels)
- Sentence-Transformers 2.5.0+
- Ollama 0.3.x+ (current version sufficient)

**Internal:**
- Sprint 60 complete ✅
- Neo4j Section Nodes (Sprint 32-33) ✅
- Qdrant Section Metadata (Sprint 32) ✅
- VLM Pipeline (Sprint 21) ✅

---

## Rollback Plan

**Feature Flags:**
```bash
# Embedding Backend
EMBEDDING_BACKEND=native  # or "ollama" for rollback

# Reranking Backend
RERANKER_BACKEND=crossencoder  # or "none" to disable

# Ollama Config (easy rollback)
OLLAMA_NUM_PARALLEL=1  # revert to default
OLLAMA_KEEP_ALIVE=5m   # revert to default

# Section Features (backward compatible)
SECTION_QUERIES_ENABLED=true  # or false to disable
```

**Rollback Procedure:**
1. Revert environment variables
2. Restart API container
3. Monitor metrics
4. No database migration needed (all backward compatible)

---

## Documentation Updates

**New ADRs:**
- ADR-049: Native Sentence-Transformers Embeddings
- ADR-050: Cross-Encoder Reranking
- ADR-051: Ollama Production Tuning
- ADR-052: Section-Aware Knowledge Graph Queries
- ADR-053: Minimum Viable Temporal Tracking

**Updated Docs:**
- `docs/TECH_STACK.md` - CUDA 13.0 requirements, Ollama config
- `docs/ARCHITECTURE.md` - Section-aware architecture
- `docs/CONVENTIONS.md` - Temporal tracking conventions
- `docs/analysis/` - 3 new Ollama optimization docs (from subagent)

**New Docs:**
- `docs/components/RERANKING.md` - Cross-Encoder reranking
- `docs/components/TEMPORAL_TRACKING.md` - Audit trail usage
- `docs/guides/SECTION_QUERIES.md` - Section-aware query patterns

---

## Sprint 61 Acceptance Criteria (ALL)

- [x] **Performance:** Query latency -50%, embedding 3-5x faster, reranking 50x faster
- [x] **Ollama:** +30% throughput, optimal configuration documented
- [x] **Sections:** 80% feature utilization (graph queries, metadata, VLM, citations)
- [x] **Temporal:** Basic audit trail (who/when/what changed)
- [x] **Cleanup:** 5 deprecated endpoints removed
- [x] **Tests:** 80%+ coverage for all new features
- [x] **Docs:** All ADRs written, TECH_STACK.md updated
- [x] **Rollback:** Feature flags tested, rollback procedures verified

---

**Sprint 61 Total:** 74 SP (2-3 weeks with 3 parallel agents)
**Expected Outcome:** Production-ready performance optimizations + full section-aware capabilities

---

**Document Created:** 2025-12-21
**Sprint 60 Status:** ✅ COMPLETE
**Sprint 61 Status:** 📋 PLANNED (Ready for execution)
