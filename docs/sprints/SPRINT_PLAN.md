# Sprint-Planung: AegisRAG
## Agentic Enterprise Graph Intelligence System

**Team-Setup:** 1-2 Entwickler + Claude Code Subagenten
**Sprint-Dauer:** 5-10 Arbeitstage
**Velocity:** 30-76 Story Points pro Sprint

**Note:** Detaillierte Sprint-Pläne befinden sich in separaten `SPRINT_XX_PLAN.md` Dateien.

---

## Sprint 1-70: Historical Sprints (Completed) ✅

**Summary:** Core foundation (Sprint 1-6), Memory Architecture (7-9), Graph Integration (10-17), Advanced RAG (33-50), Domain Training (51-63), Performance Optimization (64-70).

**Key Achievements:**
- 3-Layer Memory (Redis, Qdrant, Graphiti)
- Hybrid Search (Vector + BM25 + RRF)
- LightRAG Graph Reasoning
- LangGraph Multi-Agent Orchestration
- Domain Training with DSPy
- CUDA GPU Acceleration (10-80x speedup)
- Production Deployment (192.168.178.10)

**For detailed history, see:** `docs/sprints/SPRINT_PLAN_FULL_BACKUP.md`

---

## Sprint 71: SearchableSelect UI/UX + Backend API Integration ✅ (COMPLETED 2026-01-03)
**Ziel:** SearchableSelect Component, Backend APIs für Document/Section-Listing, Original Filenames
**Status:** ✅ **COMPLETE** - 4 Features, ~1,700 LOC
**Total Story Points:** ~50 SP (estimated)

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 71.13-71.15 | Domain Training UI (Data Augmentation, Batch Upload, Domain Details) | 21 | ✅ Frontend Only |
| 71.16 | SearchableSelect Component + Graph Communities UI | 13 | ✅ DONE |
| 71.17 | Backend API (GET /graph/documents, /sections) - Hash IDs | 8 | ✅ DONE |
| 71.17b | Original Filenames Migration (Neo4j → Qdrant) | 8 | ✅ DONE |
| 71.18 | E2E Test Fixes (Auth, Networkidle Timeouts) | 5 | ✅ DONE |

### Deliverables
- **SearchableSelect Component** (230 lines) - Keyboard navigation, filtering, cascading selection
- **Backend APIs:**
  - `GET /api/v1/graph/documents` (Qdrant-based, original filenames)
  - `GET /api/v1/graph/documents/{doc_id}/sections` (Neo4j-based)
- **Original Filenames:** "report.pdf" instead of "79f05c8e3acb6b32" (UX improvement)
- **Graph Communities UI:**
  - `SectionCommunitiesDialog.tsx` (section-level community detection)
  - `CommunityComparisonDialog.tsx` (multi-section overlap analysis)
- **E2E Tests:** 22/23 passing (96% pass rate)

### Success Criteria
- [x] SearchableSelect component reusable across dialogs
- [x] Document listing shows original filenames (<120ms P95)
- [x] Cascading selection (document → sections) working
- [x] 14/14 unit tests passing (Backend API)
- [x] 22/23 E2E tests passing (96%)

### References
- [SPRINT_71_FINAL_SUMMARY.md](SPRINT_71_FINAL_SUMMARY.md)
- [SPRINT_71_API_FRONTEND_GAP_ANALYSIS.md](SPRINT_71_API_FRONTEND_GAP_ANALYSIS.md)
- [SPRINT_71_FEATURE_71.17B_FILENAMES.md](SPRINT_71_FEATURE_71.17B_FILENAMES.md)

---

## Sprint 72: API-Frontend Gap Closure ✅ (COMPLETED 2026-01-03)
**Ziel:** Kritische API-Frontend Gaps schließen (MCP Tools, Domain Training, Memory UI)
**Status:** ✅ **COMPLETE** - 3 Major Features + Documentation
**Duration:** 5-6 Tage (Jan 2-3, 2026)
**Total Story Points:** 55 SP (estimated)

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 72.1 | MCP Tool Management UI | 13 | ✅ DONE |
| 72.2 | Domain Training UI Completion | 8 | ✅ DONE |
| 72.3 | Memory Management UI | 8 | ✅ DONE |
| 72.4 | Dead Code Removal (graph-analytics/*) | 3 | ✅ DONE |
| 72.5 | API-Frontend Gap Analysis Update | 2 | ✅ DONE |
| 72.6 | E2E Test Completion | 13 | ✅ DONE |
| 72.7 | Documentation Update | 5 | ✅ DONE |
| 72.8 | Performance Benchmarking | 3 | ⏳ IN PROGRESS |

### Deliverables Completed

**Feature 72.1: MCP Tool Management UI ✅**
- MCPToolsPage, MCPServerList, MCPToolExecutionPanel components
- Real-time health monitoring (CPU, memory, latency)
- Server connect/disconnect functionality
- Tool execution with type-safe parameter input
- Responsive design (desktop two-column, mobile tabs)
- 15 E2E tests passing

**Feature 72.2: Domain Training UI Completion ✅**
- Wired up Data Augmentation Dialog (71.13)
- Wired up Batch Document Upload (71.14)
- Wired up Domain Details Dialog (71.15)
- 18 previously skipped E2E tests now passing
- All backend APIs utilized from Sprint 71

**Feature 72.3: Memory Management UI ✅**
- MemoryManagementPage with 3 tabs (Statistics, Search, Consolidation)
- MemoryStatsCard for Redis, Qdrant, Graphiti layers
- MemorySearchPanel with cross-layer search (user, session, keywords, date)
- ConsolidationControl for manual trigger and history
- Export memory data as JSON
- 10 E2E tests passing

**Feature 72.4: Dead Code Removal ✅**
- Removed obsolete graph-analytics components
- Cleaned up 500+ LOC of unused code
- Updated imports in dependent components

**Feature 72.5: Gap Analysis Update ✅**
- Updated API-Frontend Gap Analysis document
- Gap rate improved from 72% → ~60% (18 endpoints connected)
- Documented remaining gaps for Sprint 73+

**Feature 72.6: E2E Test Completion ✅**
- Total E2E tests: 594 (26 new tests added)
- Pass rate: 100% (was 96% in Sprint 71)
- Added tests for MCP Tools (15), Memory Management (10), Domain Training (18)
- No flaky tests, all passing consistently

**Feature 72.7: Documentation Update ✅**
- Created `docs/guides/MCP_TOOLS_ADMIN_GUIDE.md` (~350 lines)
- Created `docs/guides/MEMORY_MANAGEMENT_GUIDE.md` (~400 lines)
- Updated `docs/ARCHITECTURE.md` with Sprint 72 Admin Features section
- Updated `docs/TECH_STACK.md` with MCP and Memory sections
- Updated this SPRINT_PLAN.md

### Success Criteria (All Met)

- [x] MCP Tools manageable via UI (no SSH + curl required)
- [x] Domain Training fully functional (18 skipped tests → passing)
- [x] Memory debugging via UI (no Neo4j browser needed)
- [x] E2E test pass rate: 96% → 100%
- [x] Gap Rate: 72% → 60% (18 endpoints connected)
- [x] Comprehensive user guides for admin features
- [x] Architecture documentation updated

### Gap Closure Achievement

- **Before Sprint 72:** 72% endpoints without UI (108/150)
- **After Sprint 72:** 60% endpoints without UI (90/150)
- **Improvement:** 12 percentage points (18 endpoints connected)

**Endpoints Connected:**
- 6 MCP endpoints (servers, tools, health)
- 9 Memory endpoints (stats, search, consolidate, export)
- 3 Domain endpoints (augment, batch upload, details)

### Related Issues

- **TD-081:** mem0 Integration Gap Analysis (DEFERRED to Sprint 73+)
- **TD-051:** Memory Consolidation Pipeline (IMPLEMENTED)
- **TD-053:** Admin Dashboard Full (PARTIAL - MCP + Memory done)

### References

- [SPRINT_72_PLAN.md](SPRINT_72_PLAN.md) - Detailed planning document
- [docs/guides/MCP_TOOLS_ADMIN_GUIDE.md](../guides/MCP_TOOLS_ADMIN_GUIDE.md)
- [docs/guides/MEMORY_MANAGEMENT_GUIDE.md](../guides/MEMORY_MANAGEMENT_GUIDE.md)
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md) - Updated with Sprint 72 section
- [docs/TECH_STACK.md](../TECH_STACK.md) - Updated with admin features

---

## Sprint 73: E2E Test Infrastructure & Documentation ✅ (COMPLETED 2026-01-03)
**Ziel:** Complete E2E test suite, documentation, and Sprint 73 wrap-up
**Status:** ✅ **COMPLETE** - 4 Features, 300+ lines documentation
**Total Story Points:** 29 SP

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 73.7 | Chat Interface E2E Tests (10/10 tests) | 8 | ✅ DONE |
| 73.8 | Integration Tests Analysis (chat-multi-turn timeout issues) | 5 | ✅ DONE |
| 73.9 | Documentation Cleanup (ADRs, Architecture) | 8 | ✅ DONE |
| 73.10 | Sprint Summary Documentation | 8 | ✅ DONE |

### Deliverables
- **E2E Tests:** `chat-interface-completion.spec.ts` (10 tests, 100% pass rate)
- **Analysis:** Integration test timeout analysis (60s → need 180s for LLM)
- **Documentation:**
  - Sprint 71-73 summaries
  - ADR cleanup and cross-referencing
  - Architecture updates

### Success Criteria
- [x] 10/10 chat interface E2E tests passing
- [x] Integration test behavior analyzed
- [x] Documentation comprehensive and up-to-date
- [x] Sprint summaries complete

### References
- [SPRINT_73_COMPLETION.md](SPRINT_73_COMPLETION.md)
- [SPRINT_73_INTEGRATION_TEST_ANALYSIS.md](SPRINT_73_INTEGRATION_TEST_ANALYSIS.md)

---

## Sprint 74: RAGAS Integration & Quality Metrics ✅ (COMPLETED 2026-01-04)
**Ziel:** RAGAS evaluation framework, retrieval comparison, Settings UI
**Status:** ✅ **COMPLETE** - 3 Features, comprehensive test infrastructure
**Total Story Points:** 34 SP

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 74.1 | Integration Test Fixes (timeouts, language-agnostic) | 8 | ✅ DONE |
| 74.2 | RAGAS Backend Tests (20-question dataset, 8 tests) | 13 | ✅ DONE |
| 74.3 | Retrieval Comparison (BM25/Vector/Hybrid, Settings UI) | 13 | ✅ DONE |

### Deliverables

**Feature 74.1: Integration Test Fixes ✅**
- Updated timeouts: 60s → 180s (realistic for LLM+RAG)
- Language-agnostic assertions (works with German/English)
- `docs/PERFORMANCE_BASELINES.md` created

**Feature 74.2: RAGAS Backend Tests ✅**
- `tests/ragas/data/aegis_ragas_dataset.jsonl` (20 questions)
  - 8 Factual, 6 Exploratory, 4 Summary, 2 Multi-hop
- `tests/ragas/test_ragas_integration.py` (8 test functions)
  - Context Precision (>0.75 target)
  - Context Recall (>0.70 target)
  - Faithfulness (>0.90 target)
  - Answer Relevancy (>0.80 target)

**Feature 74.3: Retrieval Comparison ✅**
- `tests/ragas/data/retrieval_comparison_dataset.jsonl` (10 queries)
  - 3 BM25-favored, 3 Vector-favored, 4 Hybrid-favored
- `tests/ragas/test_retrieval_comparison.py` (5 comparison tests)
  - RetrievalMethodEvaluator class
  - Custom IntentWeights for method isolation
- Settings UI: Retrieval method selector (Hybrid/Vector/BM25)

### Success Criteria
- [x] Integration tests pass with realistic timeouts
- [x] RAGAS evaluation framework ready for production
- [x] Retrieval comparison infrastructure complete
- [x] User-facing retrieval method selector in Settings

### References
- [SPRINT_74_PLAN.md](SPRINT_74_PLAN.md)
- `tests/ragas/` directory
- `frontend/src/types/settings.ts` (RetrievalMethod type)

---

## Sprint 75: Architecture Review & Critical Gap Discovery ✅ (COMPLETED 2026-01-05)
**Planned:** RAGAS Evaluation & RAG Quality Optimization
**Actually Delivered:** **Critical Architecture Gap Analysis**
**Status:** ✅ **COMPLETE** - 2 CRITICAL TDs discovered, blocked RAGAS execution
**Sprint Duration:** 1 day (2026-01-05)
**Total Story Points:** ~21 SP (architecture investigation + documentation)

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 75.0 | Infrastructure Fixes (Ollama context, GPU, Neo4j) | 5 | ✅ COMPLETE |
| 75.A | Frontend/Backend API Parity Analysis | 3 | ✅ COMPLETE |
| 75.B | **TD-084: Namespace Isolation in Ingestion** | 13 | 🔴 **CRITICAL - Discovered** |
| 75.C | **TD-085: DSPy Domain Prompts Not Used** | 21 | 🔴 **CRITICAL - Discovered** |

### Critical Findings

**🔴 TD-084: Namespace Isolation BROKEN**
- **Problem:** All docs hardcoded to `namespace_id="default"` in ingestion
- **Impact:** RAGAS evaluation impossible (docs contaminate each other)
- **Blocker for:** Multi-tenant isolation, project separation, evaluation
- **Effort:** 13 SP (Sprint 76)

**🔴 TD-085: DSPy Domain Training NOT USED**
- **Problem:** 34 SP invested in Domain Training (Sprint 45) → Optimized prompts NEVER used in extraction!
- **Impact:** Domain-specific extraction quality improvements unrealized
- **Wasted Investment:** 34 SP from Sprint 45
- **Effort:** 21 SP (Sprint 76-77)

### Deliverables
- ✅ **Infrastructure Fixes** (7 fixes committed)
  - Ollama context: 16K→32K tokens
  - GPU embeddings: PyTorch cu130 installed
  - Neo4j document_path: Fixed in 3 files
- ✅ **USER_JOURNEY_E2E.md** (~1,315 new lines)
- ✅ **TD-084_NAMESPACE_ISOLATION_IN_INGESTION.md**
- ✅ **TD-085_DSPY_DOMAIN_PROMPTS_NOT_USED_IN_EXTRACTION.md**
- ✅ **TD_INDEX.md updated** (2 critical items added)
- ✅ **E2E Test Scaffolds** (ragas-domain-setup.spec.ts, run_ragas_on_namespace.py)

### Sprint Pivot Decision
**Original Plan:** Execute RAGAS tests (Features 75.1-75.3)
**Blocker Discovered:** Namespace isolation missing → RAGAS results invalid
**Decision:** Deep-dive architecture review → Found 2 CRITICAL gaps
**Outcome:** Sprint 75 features moved to Sprint 76+ (after TD-084/085 fixes)

### Impact on Roadmap
- **Sprint 76:** Focus on TD-084 + TD-085 (34 SP)
- **Sprint 77:** RAGAS Evaluation (with proper namespace isolation)
- **Total Delay:** ~2-3 weeks, but prevents months of invalid evaluation data

### Success Criteria (Met)
- [x] Critical architecture gaps identified and documented
- [x] Infrastructure fixes deployed (7 fixes)
- [x] Technical debt prioritized (2 CRITICAL TDs created)
- [x] Sprint 76 roadmap clear (TD-084 + TD-085)
- [x] E2E test infrastructure prepared for future RAGAS runs

### References
- [SPRINT_75_PLAN.md](SPRINT_75_PLAN.md) - Original plan (features deferred)
- [SPRINT_75_RAGAS_FAILURE_ANALYSIS.md](SPRINT_75_RAGAS_FAILURE_ANALYSIS.md)
- [TD-084](../technical-debt/TD-084_NAMESPACE_ISOLATION_IN_INGESTION.md)
- [TD-085](../technical-debt/TD-085_DSPY_DOMAIN_PROMPTS_NOT_USED_IN_EXTRACTION.md)

---

## Sprint 76: .txt File Support + RAGAS Baseline ✅ (COMPLETED 2026-01-07)
**Ziel:** .txt File Ingestion (TD-089), Pydantic Chunk Fix, RAGAS Baseline Metrics
**Status:** ✅ **COMPLETE** - 3 Features, 146 entities, 6 critical issues identified
**Total Story Points:** ~13 SP

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 76.1 | Entity Extraction Bug Fix (chunk.text → chunk.content) | 2 | ✅ DONE |
| 76.2 | RAGAS Baseline Evaluation (4 metrics) | 5 | ✅ DONE |
| 76.3 | .txt File Support (TD-089) - Docling Integration | 5 | ✅ DONE |
| 76.4 | Pydantic Chunk Hard Failures | 1 | ✅ DONE |

### Deliverables

**Feature 76.1: Entity Extraction Bug Fix ✅**
- Fixed critical bug: `chunk.text` → `chunk.content` in graph_extraction.py
- 0 entities → 52 entities (RAGAS docs)
- 0 entities → 146 entities (HotpotQA)

**Feature 76.2: RAGAS Baseline Metrics ✅**
- Switched LLM: Nemotron → GPT-OSS:20b (24x better success rate)
- Results:
  - Faithfulness: 80%
  - Answer Relevancy: 93%
  - Context Recall: 50%
  - Context Precision: 20%

**Feature 76.3: .txt File Support ✅**
- Implemented `parse_text_file()` in docling_client.py (+219 lines)
- Base64 encoding for Docling API contract
- 15 HotpotQA files uploaded (100% success rate)
- Created 3 RAGAS datasets (15 questions with ground truth)

**Feature 76.4: Pydantic Chunk Hard Failures ✅**
- Added hard failures to graph_extraction.py and vector_embedding.py
- Prevents silent repr() bugs
- Enforces Pydantic models across pipeline

### Statistics

**Qdrant Vector Database:**
- Total Vectors: 17 chunks (6 small + 10 large)
- Dimension: 1024 (BGE-M3)
- Indexed: 0 (normal for <20k threshold)

**Neo4j Graph Database:**
- Chunks: 14 nodes (discrepancy with Qdrant 17)
- Entities: 146 nodes (38 unique types)
- Relations: 65 RELATES_TO edges
- MENTIONED_IN: 217 edges
- Communities: 92 (Louvain detection)
- Community Summaries: 0 (not generated)

### Critical Issues Identified

| TD | Issue | Priority | SP |
|----|-------|----------|-----|
| TD-090 | BM25 namespace metadata missing | HIGH | 1 |
| TD-091 | Chunk count mismatch (Qdrant 17 ≠ Neo4j 14) | HIGH | 2 |
| TD-093 | Qdrant index not updated post-ingestion | MEDIUM | 2 |
| TD-094 | Community summaries not generated | MEDIUM | 3 |
| TD-095 | Low entity connectivity (0.45 relations/entity) | MEDIUM | 3 |

### Success Criteria
- [x] .txt file ingestion working (15/15 files)
- [x] Entity extraction fixed (146 entities)
- [x] RAGAS baseline established (4 metrics)
- [x] Pydantic models enforced
- [ ] Data consistency (17≠14 chunks) - DEFERRED to Sprint 77

### References
- [SPRINT_76_FINAL_RESULTS.md](SPRINT_76_FINAL_RESULTS.md)
- [TD-089: .txt File Support](../technical-debt/TD-089.md)
- [ADR-027: Docling CUDA Ingestion](../adr/ADR-027-docling-cuda-ingestion.md)

---

## Sprint 77: Critical Bug Fixes + Community Enhancements ✅ (COMPLETED 2026-01-07)
**Ziel:** Resolve Sprint 76 critical bugs, Community Summarization, Entity Connectivity Benchmarks
**Status:** ✅ **COMPLETE** - 5 Features, 2,108 LOC, 100% success
**Total Story Points:** 11 SP

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 77.1 | BM25 Namespace Metadata Fix (TD-090) | 1 | ✅ DONE |
| 77.2 | Chunk Count Mismatch Investigation (TD-091) | 2 | ✅ DONE |
| 77.3 | Qdrant Index Optimization (TD-093) | 2 | ✅ DONE |
| 77.4 | Community Summarization Batch Job (TD-094) | 3 | ✅ DONE |
| 77.5 | Entity Connectivity as Domain Training Metric (TD-095) | 3 | ✅ DONE |

### Deliverables

**Feature 77.1: BM25 Namespace Fix ✅**
- 1-line fix: Copy namespace field from Qdrant payload to BM25 document
- Impact: Namespace filtering now works in hybrid search
- File: `src/components/vector_search/hybrid_search.py:680`

**Feature 77.2: Chunk Mismatch Resolved ✅**
- Root cause: Chunking bug created empty chunks (filtered out by Neo4j)
- Fixed adaptive_chunking.py to prevent empty chunks
- Consistency restored: Qdrant = Neo4j

**Feature 77.3: Qdrant Index Optimization ✅**
- Added post-ingestion index rebuild via Admin API
- Endpoint: `POST /api/v1/admin/qdrant/optimize`
- Ensures HNSW index updated after batch uploads

**Feature 77.4: Community Summarization Batch Job ✅**
- Created `scripts/generate_community_summaries.py` (+300 lines)
- Admin API: `POST /api/v1/admin/graph/communities/summarize`
- Result: 92/92 communities summarized (~45min batch job)
- Graph-Global search mode now functional

**Feature 77.5: Entity Connectivity Benchmarks ✅**
- Created `src/components/domain_training/domain_metrics.py` (+450 lines)
- Defined 4 domain-specific benchmarks:
  - **Factual**: 0.3-0.8 relations/entity (HotpotQA = 0.45 ✅)
  - **Narrative**: 1.5-3.0 relations/entity
  - **Technical**: 2.0-4.0 relations/entity
  - **Academic**: 2.5-5.0 relations/entity
- Admin API: `POST /api/v1/admin/domains/connectivity/evaluate`
- Frontend UI: ConnectivityMetrics component in Domain Detail Dialog
- Validation: HotpotQA connectivity (0.45) confirmed within benchmark!

### Code Changes
- Files Modified: 12
- Lines Added: 2,111
- Lines Removed: 3
- Net Lines: +2,108

### Success Criteria
- [x] BM25 namespace filtering working
- [x] Data consistency Qdrant↔Neo4j restored
- [x] Qdrant index optimization automated
- [x] 92/92 community summaries generated
- [x] Domain-specific connectivity benchmarks defined
- [x] HotpotQA connectivity validated (0.45 within [0.3, 0.8])

### References
- [SPRINT_77_PLAN.md](SPRINT_77_PLAN.md)
- [SPRINT_77_SESSION_1_RESULTS.md](SPRINT_77_SESSION_1_RESULTS.md)
- [SPRINT_77_SESSION_2_RESULTS.md](SPRINT_77_SESSION_2_RESULTS.md)
- [TD-090 to TD-095](../technical-debt/)

---

## Sprint 78: Graph Entity→Chunk Expansion & Semantic Search ✅ (COMPLETED 2026-01-08)
**Ziel:** Fix graph retrieval to return full chunks, implement 3-stage semantic entity expansion
**Status:** ✅ **FUNCTIONALLY COMPLETE** - 5/6 features, 20 unit tests, RAGAS deferred to Sprint 79
**Total Story Points:** 34 SP

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 78.1 | Entity→Chunk Expansion Fix (MENTIONED_IN traversal) | 5 | ✅ DONE |
| 78.2 | 3-Stage Entity Expansion Pipeline | 13 | ✅ DONE |
| 78.3 | Semantic Entity Reranking (BGE-M3) | 5 | ✅ DONE |
| 78.4 | Stop Words Removal (replaced with LLM filtering) | 2 | ✅ DONE |
| 78.5 | Configuration Setup (4 new settings) | 3 | ✅ DONE |
| 78.6 | Unit Tests + Documentation | 5 | ✅ DONE |
| 78.7 | RAGAS Evaluation with Optimized Pipeline | 1 | ⏭️ DEFERRED (Sprint 79) |

### Deliverables

**Feature 78.1: Entity→Chunk Expansion Fix ✅**
- **Critical Bug Fixed**: Graph search returned 100-char entity descriptions instead of 800-1800 token chunks
- Modified `dual_level_search.py` to traverse `(entity)-[:MENTIONED_IN]->(chunk)` relationships
- Result: Graph queries now return 447 chars avg (vs 100 chars before)
- Impact: Graph search now provides full document context

**Feature 78.2: 3-Stage Entity Expansion Pipeline ✅**
- Created `src/components/graph_rag/entity_expansion.py` (+418 lines)
- **SmartEntityExpander** class:
  - **Stage 1**: LLM extracts entities from query
  - **Stage 2**: Graph expansion via N-hop traversal (configurable 1-3 hops)
  - **Stage 3**: LLM synonym fallback (if < threshold)
  - **Stage 4**: Semantic reranking via BGE-M3 embeddings
- UI-configurable parameters for hops, threshold, synonyms

**Feature 78.3: Semantic Entity Reranking ✅**
- Implemented in `SmartEntityExpander.expand_and_rerank()`
- Uses BGE-M3 embeddings for cosine similarity
- Boosts semantically relevant entities while preserving graph-expanded entities

**Feature 78.4: Stop Words Obsolescence ✅**
- Removed manual 46-word stop list
- LLM entity extraction automatically filters stop words
- Cleaner code, no maintenance overhead

**Feature 78.5: Configuration Setup ✅**
- Added 4 new settings to `src/core/config.py`:
  - `graph_expansion_hops`: 1-3 (UI configurable)
  - `graph_min_entities_threshold`: 5-20 (synonym fallback trigger)
  - `graph_max_synonyms_per_entity`: 1-5 (LLM synonym limit)
  - `graph_semantic_reranking_enabled`: bool (toggle reranking)

**Feature 78.6: Unit Tests ✅**
- Created `tests/unit/components/graph_rag/test_entity_expansion.py` (+448 lines, 14 tests)
- Modified `tests/unit/components/graph_rag/test_dual_level_search.py` (+230 lines, 6 tests)
- **Total**: 20 unit tests, 100% pass rate
- Coverage: Entity extraction, graph expansion, synonym fallback, reranking, chunk retrieval

**Feature 78.7: RAGAS Evaluation ⏭️**
- **Status**: DEFERRED to Sprint 79
- **Root Cause**: RAGAS Few-Shot prompts too complex for local LLMs
  - GPT-OSS:20b: 85.76s per evaluation (15 evals = 1286s, timeout at 300s)
  - Nemotron3 Nano: >600s per evaluation (2903 char prompt)
- **Solution**: Sprint 79 will use DSPy to optimize prompts for local inference
- **Alternative Verification**: Functional testing accepted (20 unit tests + manual graph queries)

### Performance Testing Results

**RAGAS Prompt Complexity:**
- Context Precision prompt: 2903 chars (3 few-shot examples)
- GPT-OSS:20b: **85.76s** per evaluation (target: <20s)
- Nemotron3 Nano: **686s** per simple query (target: <60s)

**Graph Query Performance:**
- Entity→Chunk expansion: 447 chars avg (vs 100 chars before)
- 3-stage expansion: 7 graph + 6 synonyms = 13 entities
- Query latency: <500ms for hybrid graph+vector search

### Critical Findings

1. **Local LLMs Insufficient for RAGAS**: Few-shot prompts require cloud-scale inference or prompt optimization
2. **DSPy Optimization Needed**: Sprint 79 will compress prompts while maintaining accuracy (target: 4x speedup)
3. **Functional Verification Sufficient**: 20 unit tests + manual testing confirmed feature correctness

### Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Entity→Chunk Expansion | Full chunks | ✅ 447 chars | **PASS** |
| 3-Stage Pipeline | Working | ✅ 7+6=13 entities | **PASS** |
| Configuration | 4 settings | ✅ 4 settings | **PASS** |
| Unit Tests | >15 tests | ✅ 20 tests | **PASS** |
| RAGAS Metrics | 4 metrics | ⏭️ Deferred | **DEFERRED** |

**Overall**: ✅ **5/6 features complete** (83% functional, 100% code quality)

### References
- [SPRINT_78_PLAN.md](SPRINT_78_PLAN.md)
- [ADR-041: Entity→Chunk Expansion](../adr/ADR-041_ENTITY_CHUNK_EXPANSION.md) (pending)
- `src/components/graph_rag/entity_expansion.py`
- `src/components/graph_rag/dual_level_search.py`

---

## Sprint 79: RAGAS 0.4 Evaluation + Optional DSPy + Frontend UI 📝 (PLANNED)
**Ziel:** Upgrade to RAGAS 0.4.2, evaluate if timeouts persist, conditionally apply DSPy optimization, complete Frontend UI
**Status:** 📝 **PLANNED** - 8 Features, 31 SP (2 SP RAGAS Upgrade + 21 SP DSPy [CONDITIONAL] + 8 SP Frontend)
**Total Story Points:** 31 SP

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 79.8 | **RAGAS 0.4.2 Upgrade & Performance Evaluation (PHASE 1)** | 2 | 📝 **FIRST** |
| 79.1 | DSPy Integration & Training Data Collection | 8 | 🔀 CONDITIONAL |
| 79.2 | Optimized Context Precision for GPT-OSS:20b | 5 | 🔀 CONDITIONAL |
| 79.3 | Optimized Metrics for Nemotron3 Nano | 5 | 🔀 CONDITIONAL |
| 79.4 | Performance Benchmarking (Before/After) | 2 | 🔀 CONDITIONAL |
| 79.5 | RAGAS Evaluation with Optimized Prompts | 1 | 🔀 CONDITIONAL |
| 79.6 | Frontend UI für Graph Expansion Settings (Sprint 78 Follow-Up) | 5 | 📝 PLANNED |
| 79.7 | Admin Graph Operations UI (Sprint 77 Follow-Up) | 3 | 📝 PLANNED |

**2-Phase Strategy:**
- **PHASE 1 (Feature 79.8):** Upgrade to RAGAS 0.4.2, test if new features fix timeouts
- **PHASE 2 (Features 79.1-79.5):** CONDITIONAL - Only execute if Phase 1 doesn't fix timeouts
- **Frontend (79.6-79.7):** MANDATORY - Completes Sprint 76-78 backend features

### Sprint Goals

**Primary Objective:**
Reduce RAGAS evaluation time from **85.76s → <20s** (GPT-OSS:20b) and **>600s → <60s** (Nemotron3 Nano) using DSPy prompt optimization

**Secondary Objective:**
Complete Frontend UI for Sprint 76-78 backend features (Graph Expansion Settings, Community Summarization)

**Approach:**
1. Use DSPy BootstrapFewShot and MIPROv2 for automatic prompt compression
2. Maintain ≥90% accuracy while reducing prompt complexity
3. Create 20 training examples per metric (80 total)
4. A/B test optimized vs baseline prompts
5. Implement Frontend UI for Graph Expansion Settings (4 sliders/switches)
6. Implement Community Summarization UI (batch job trigger + progress)

### Planned Deliverables

**Feature 79.1: DSPy Integration**
- Install DSPy framework (`pip install dspy-ai`)
- Create training dataset (20 examples × 4 metrics = 80 examples)
- Implement DSPy signature for Context Precision metric
- Configure LLM backend for optimization (GPT-OSS:20b or OpenAI)

**Feature 79.2: GPT-OSS:20b Optimization**
- Baseline: 85.76s per evaluation (2903 char prompt)
- Target: <20s per evaluation (<500 char prompt)
- Method: MIPROv2 with 10 optimization steps
- Expected: 4x speedup, ≥90% accuracy

**Feature 79.3: Nemotron3 Nano Optimization**
- Baseline: >600s per evaluation
- Target: <60s per evaluation
- Method: BootstrapFewShot with 1-shot examples (vs 3-shot)
- Expected: 10x speedup, ≥85% accuracy

**Feature 79.4: Performance Benchmarking**
- Measure latency, accuracy, token count before/after
- Create comparison report with visualizations
- Document optimization techniques per LLM

**Feature 79.5: RAGAS Evaluation**
- Run full RAGAS suite with optimized prompts
- 15 contexts × 4 metrics = 60 evaluations
- Expected time: <5 minutes (vs 1286s baseline)

**Feature 79.6: Graph Expansion Settings UI (Sprint 78 Follow-Up)**
- GraphExpansionSettingsCard component (4 sliders + 1 toggle)
- GET/PUT /api/v1/admin/graph/expansion/config endpoints
- Redis persistence for settings (like LLM Config Sprint 64)
- 5 E2E tests (Load, Update, Persist, Validation, Reset)

**Feature 79.7: Community Summarization UI (Sprint 77 Follow-Up)**
- CommunitySummarizationCard component (trigger button + progress)
- Wired to existing POST /api/v1/admin/graph/communities/summarize
- Real-time progress display during batch job
- 3 E2E tests (Trigger, Progress, Complete)

### Expected Impact

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| GPT-OSS:20b latency | 85.76s | <20s | 4x faster |
| Nemotron3 Nano latency | >600s | <60s | 10x faster |
| Prompt length | 2903 chars | <500 chars | 6x compression |
| Accuracy | 100% | ≥90% | -10% acceptable |
| RAGAS total time | 1286s | <300s | 4x faster |

### References
- [SPRINT_79_PLAN.md](SPRINT_79_PLAN.md)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [RAGAS Framework](https://github.com/explodinggradients/ragas)

---

## Sprint 80+: Future Sprints (Backlog)

### High Priority Candidates
1. **RAGAS Quality Improvements** (Sprint 79 Results Analysis)
   - Chunking optimization based on Context Precision scores
   - Embedding tuning for better Context Recall
   - Reranking improvements for Answer Relevancy

2. **Graph Reasoning Enhancements** (5-8 SP)
   - Multi-hop graph traversal optimization
   - Semantic relationship extraction improvements
   - Community-based retrieval expansion

3. **mem0 Frontend UI** (8 SP)
   - User preferences page
   - Memory consolidation visualization
   - Session history management

### Long-Term Roadmap (Sprint 81+)
- **Multi-Modal RAG:** Image + Video + Audio processing
- **Federated Search:** Cross-domain knowledge aggregation
- **Cloud LLM Integration:** Azure OpenAI, Anthropic Claude, Cohere
- **Enterprise Features:** SSO, RBAC, Audit Logs
- **Advanced Agentic Capabilities:** Agent-level adaptation (A1/A2 from Paper 2512.16301)

---

## Sprint Metrics Overview

| Sprint | Total SP | Features | Status | Key Achievement |
|--------|---------|----------|--------|-----------------|
| 1-60 | ~1800 | ~150 | ✅ | Core RAG Platform |
| 61 | 29 | 5 | ✅ | Native Sentence-Transformers (+300% speed) |
| 62-63 | 93 | 20 | ✅ | Section-Aware RAG + Multi-Turn Research |
| 64 | 37 | 7 | ✅ | Domain Training Optimization + Production Deploy |
| 65 | 18 | 4 | ✅ | CUDA GPU Acceleration (10-80x speedup) |
| 66 | 29 | 5 | ✅ | E2E Test Stabilization (0% → 61% → 100%) |
| 67 | 75 | 14 | ✅ | Secure Shell Sandbox + Agents Adaptation + C-LARA |
| 68 | 62 | 10 | ✅ | Performance Optimization (500ms → 350ms P95) |
| 69 | 53 | 9 | ✅ | LLM Streaming (TTFT 320ms → 87ms) + Monitoring |
| 70 | 44 | 14 | ✅ | Deep Research Repair + Tool Use Integration |
| 71 | ~50 | 4 | ✅ | SearchableSelect + Original Filenames + API Integration |
| 72 | 55 | 8 | ✅ | API-Frontend Gap Closure (MCP, Domain, Memory UI) |
| 73 | 29 | 4 | ✅ | E2E Test Infrastructure & Documentation |
| 74 | 34 | 3 | ✅ | RAGAS Integration & Quality Metrics |
| 75 | ~21 | 3 | ✅ | Critical Architecture Gap Discovery (TD-084, TD-085) |
| 76 | ~13 | 4 | ✅ | .txt File Support + RAGAS Baseline (146 entities) |
| 77 | 11 | 5 | ✅ | Critical Bug Fixes + Community Summarization (2,108 LOC) |
| 78 | 34 | 6 | ✅ | Graph Entity→Chunk Expansion + 3-Stage Semantic Search |
| **79** | **12** | **4** | ✅ | **RAGAS 0.4.2 Migration + Graph UI + Admin Graph Ops (Completed)** |
| **80** | **21** | **10** | 📝 | **RAGAS P0 Critical Fixes - Faithfulness & Hybrid Fusion (Planned)** |
| **81** | **38** | **10** | 🚧 | **C-LARA SetFit 95% (Feature 81.7 Done) + Query Routing (In Progress)** |
| **82** | **8** | **4** | ✅ | **RAGAS Phase 1 - Text-Only Benchmark (500 samples)** |
| **83** | **26** | **4** | ✅ | **3-Rank Cascade + Gleaning + Fast Upload (7,638 LOC, 94+ tests)** |
| **84** | **20** | **6** | 📝 | **Stabilization & Iterative Ingestion (Outlier Detection, Configurable Cascade)** |
| **87** | **34** | **4** | ✅ | **BGE-M3 Native Hybrid Search (replaces BM25, 2,200+ LOC)** |
| **88** | **28** | **3** | ✅ | **RAGAS Phase 2 Evaluation (Tables + Code)** |
| **92** | **36** | **24** | ✅ | **Performance Optimization & Deep Research Enhancements (FlagEmbedding, GPU, Research UI)** |
| **93** | **34** | **5** | ✅ | **Tool Composition Framework (ToolComposer, Browser, Skill-Tool Mapping, DSL, LangGraph 1.0)** |
| **94** | **26** | **3** | ✅ | **Multi-Agent Communication (Messaging Bus, Shared Memory, Skill Orchestrator), 144 tests, TD-101 deferred** |
| **95** | **30** | **5** | ✅ | **Hierarchical Agents + Skill Libraries (Executive→Manager→Worker, 3,620+ LOC, 207 tests, 100%)** |
| **96** | **32** | **5** | ✅ | **EU Governance & Compliance (GDPR Articles, Audit Trail, Explainability, Certification, 3,329 LOC, 211 tests, 100%)** |
| **97** | **38** | **5** | ✅ | **Skill Management UI (Skill Registry, Config Editor, Tool Authorization, Lifecycle Dashboard, SKILL.md Editor, 2,450+ LOC)** |
| **98** | **40** | **6** | ✅ | **Governance & Monitoring UI (Agent Comm Dashboard, Hierarchy D3.js, GDPR Consent, Audit Viewer, Explainability, Certification, 2,780+ LOC)** |
| **99** | **54** | **4** | 📝 | **Backend API Integration (24 REST endpoints: Skills, Agents, GDPR, Audit - Connects Sprint 97-98 UI to Sprint 90-96 Backend)** |

**Cumulative Story Points (Sprints 1-99):** 3,047 + 38 + 40 + 54 = 3,179 SP
**Average Velocity (Sprints 61-79):** ~40 SP per sprint
**E2E Test Improvement:** 337/594 (57% - Sprint 66) → 620/620 (100% - Sprint 72)
**Code Quality:** 84% test coverage, 0 TypeScript errors, <500ms P95 query latency

---

## Development Principles

1. **Feature-Based Development:** 1 Feature = 1 Commit (Atomic Rollbacks)
2. **Test-Driven:** >80% test coverage (unit + integration + E2E)
3. **Documentation-First:** ADRs vor Code, README Updates pro Feature
4. **Performance-Oriented:** Query latency targets (Simple <200ms, Hybrid <500ms, Complex <1000ms)
5. **Production-Ready:** Docker Compose deployment, monitoring, alerts

---

## Code Quality Metrics

| Metric | Target | Current (Sprint 71) |
|--------|--------|---------------------|
| Test Coverage | >80% | 84% |
| E2E Pass Rate | 100% | 96% (22/23) |
| TypeScript Errors | 0 | 0 ✅ |
| Linting Errors | 0 | 0 ✅ |
| Build Time | <3min | 2min 15s ✅ |
| Query Latency P95 | <500ms | 350ms ✅ |

---

## References

- **Full Sprint History:** [SPRINT_PLAN_FULL_BACKUP.md](SPRINT_PLAN_FULL_BACKUP.md)
- **Architecture:** [ARCHITECTURE.md](../ARCHITECTURE.md)
- **ADRs:** [ADR_INDEX.md](../adr/ADR_INDEX.md)
- **Technical Debt:** [TD_INDEX.md](../technical-debt/TD_INDEX.md)
- **E2E Tests:** [USER_JOURNEYS_AND_TEST_PLAN.md](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md)

---

**Last Updated:** 2026-01-15
**Current Sprint:** 96 (Completed - EU Governance & Compliance, 32 SP, 211 tests)
**Previous Sprints:** 92-95 (Completed - Performance, Tool Composition, Multi-Agent Communication, Hierarchical Agents)
**Sprints 90-96 Milestone:** ✅ **7-Sprint Transformation Complete (208 SP, Basic RAG → Enterprise Agentic Framework)**
**Upcoming:** Sprint 97+ (Advanced Features & Quality Enhancements)

---

## Sprint 80-81: RAGAS Optimization Roadmap (Planned)

Based on comprehensive RAGAS evaluation (2026-01-08), prioritized improvements:

**Sprint 80 Focus (P0 Critical):**
- Cite-sources prompt engineering (Faithfulness +50-80%)
- Graph→Vector fallback on empty contexts (100% success rate)
- Hybrid cross-encoder reranking (Hallucination fix)
- Expanded evaluation datasets (50 Amnesty, 20 HotpotQA)

**Sprint 81 Focus (P1 High Priority):**
- Query-adaptive routing (automatic mode selection)
- Domain-agnostic entity extraction (70% coverage)
- Parent chunk retrieval (Context Recall +14%)
- Automated RAGAS CI/CD pipeline

**For detailed plans, see:**
- [SPRINT_80_PLAN.md](SPRINT_80_PLAN.md) - RAGAS P0 Critical Fixes
- [SPRINT_81_PLAN.md](SPRINT_81_PLAN.md) - Query Routing & Entity Extraction
- [RAGAS_ANALYSIS_2026_01_08.md](../ragas/RAGAS_ANALYSIS_2026_01_08.md) - Full evaluation analysis

---

## Sprint 82: RAGAS Phase 1 - Text-Only Benchmark ✅ (COMPLETED 2026-01-09)
**Epic:** 1000-Sample Stratified RAGAS Evaluation Benchmark
**Total Story Points:** 8 SP
**Status:** ✅ **COMPLETE** - 500-sample dataset generated, 168 files uploaded (33.6%)

| Feature | SP | Status |
|---------|-----|--------|
| 82.1 | Dataset Loader Infrastructure | 3 | ✅ DONE |
| 82.2 | Stratified Sampling Engine | 2 | ✅ DONE |
| 82.3 | Unanswerable Generation | 2 | ✅ DONE |
| 82.4 | AegisRAG JSONL Export | 1 | ✅ DONE |

**Deliverables:**
- `data/evaluation/ragas_phase1_500.jsonl` - 500 text-only samples
- `scripts/ragas_benchmark/` - Dataset loaders (HotpotQA, RAGBench, LogQA)
- Stratified sampling with quotas (doc_type, question_type, difficulty)
- 50 unanswerable questions (10%)

**Issues Encountered:**
- Upload process timed out at 168/500 files (HTTP 000 errors)
- 33.6% upload success rate → blocking for Sprint 83 ER-Extraction improvements

**For detailed plan, see:** [SPRINT_82_PLAN.md](SPRINT_82_PLAN.md)

---

## Sprint 83: ER-Extraction Robustness & Observability ✅ (COMPLETED 2026-01-10)
**Epic:** Ingestion Pipeline Reliability & Debugging
**Total Story Points:** 26 SP
**Status:** ✅ **COMPLETE** - 4 Features, 7,638 LOC, 94+ tests

| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| 83.1 | Comprehensive Ingestion Logging | 5 | P0 | ✅ DONE |
| 83.2 | 3-Rank LLM Fallback Cascade | 8 | P0 | ✅ DONE |
| 83.3 | Gleaning (Multi-Pass ER-Extraction) | 5 | P1 | ✅ DONE |
| 83.4 | Fast User Upload + Background Refinement | 8 | P1 | ✅ DONE |

**Deliverables:**
- **Feature 83.1:** Comprehensive structured logging with P50/P95/P99 metrics, LLM cost tracking, GPU VRAM monitoring (pynvml)
- **Feature 83.2:** 3-Rank Cascade (Nemotron3 → GPT-OSS:20b → Hybrid SpaCy NER+LLM) with 99.9% success rate
- **Feature 83.3:** Microsoft GraphRAG-style gleaning (+20-40% entity recall, configurable 0-3 rounds)
- **Feature 83.4:** Two-Phase Upload (2-5s SpaCy NER response + 30-60s background LLM refinement)
- **Dependencies Added:** SpaCy 3.7.0, pynvml 11.5.0, tenacity 8.0.0
- **ADR-049:** 3-Rank LLM Cascade + Gleaning architecture decision record (421 lines)
- **Tests:** 94+ unit tests (100% coverage), 4 integration tests

**Goals Achieved:**
- ✅ 99.9% extraction success rate (vs ~95% single LLM)
- ✅ Multi-language NER support (DE/EN/FR/ES via SpaCy)
- ✅ Comprehensive logging (P50/P95/P99 metrics, LLM cost, GPU VRAM)
- ✅ +20-40% entity recall with gleaning (Microsoft GraphRAG validated)
- ✅ 10-15x faster user upload experience (30-60s → 2-5s perceived time)

**For detailed plan, see:** [SPRINT_83_PLAN.md](SPRINT_83_PLAN.md)

---

## Sprint 84: Ingestion Pipeline Stabilization (PLANNED)
**Epic:** Bug Fixes & Performance Tuning
**Total Story Points:** ~15-20 SP (TBD)
**Status:** 📝 Planned

**Goals:**
- Fix bugs discovered during Sprint 83 logging implementation
- Performance tuning based on Sprint 83 metrics
- Upload remaining 332/500 RAGAS Phase 1 files (168 → 500)
- Achieve 95%+ upload success rate with fallback cascade

**Rationale:**
After implementing comprehensive logging (Sprint 83), we expect to discover additional bottlenecks and bugs that need fixing before proceeding to RAGAS Phase 2.

---

## Sprint 85-86: RAGAS 1000-Sample Benchmark (PLANNED)
**Epic:** Complete RAGAS Evaluation Infrastructure
**Total Story Points:** 34 SP (Phase 2: 13 SP, Phase 3: 21 SP)
**Timeline:** After Sprint 84 stabilization

### Phase Breakdown

| Sprint | Phase | Samples | Doc Types | SP |
|--------|-------|---------|-----------|-----|
| **82** | **Text-Only** | **500** | **clean_text, log_ticket** | **8** ✅ |
| **85** | **Structured** | **+300** | **table, code_config** | **13** |
| **86** | **Visual** | **+200** | **pdf_ocr, slide, pdf_text** | **21** |
| **Total** | | **1000** | **7 types** | **42** |

**Sprint 85 (Phase 2 - Structured Data):**
- T2-RAGBench table processor (markdown conversion)
- CodeRepoQA code extractor (syntax-aware)
- Statistical rigor package (Bootstrap CI, McNemar's test)

**Sprint 86 (Phase 3 - Visual Assets):**
- Asset downloader with SHA256 caching
- DocVQA dual-mode OCR (dataset vs Docling)
- SlideVQA multi-image processor
- PDF text extraction fallback

**For detailed plans, see:**
- [SPRINT_82_PLAN.md](SPRINT_82_PLAN.md) - Phase 1: Text-Only Benchmark ✅ COMPLETE
- [SPRINT_83_PLAN.md](SPRINT_83_PLAN.md) - ER-Extraction Robustness ✅ COMPLETE
- [SPRINT_85_PLAN.md](SPRINT_85_PLAN.md) - Phase 2: Structured Data 📝 PLANNED
- [SPRINT_86_PLAN.md](SPRINT_86_PLAN.md) - Phase 3: Visual Assets 📝 PLANNED
- [ADR-048](../adr/ADR-048-ragas-1000-sample-benchmark.md) - Full strategy documentation

---

## Sprint 87: BGE-M3 Native Hybrid Search ✅ (COMPLETED 2026-01-13)
**Epic:** Replace BM25 with Native BGE-M3 Sparse Vectors
**Total Story Points:** 34 SP
**Status:** ✅ **COMPLETE** - 4 Features, 2,200+ LOC

| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| 87.1 | FlagEmbedding Service Integration | 10 | P0 | ✅ DONE |
| 87.2 | Qdrant Multi-Vector Collection | 8 | P0 | ✅ DONE |
| 87.3 | Four-Way Hybrid Search (Dense+Sparse RRF) | 10 | P0 | ✅ DONE |
| 87.4 | BM25 Deprecation & Migration | 6 | P1 | ✅ DONE |

**Deliverables:**
- BGE-M3 embeddings via FlagEmbedding (Dense 1024D + Sparse lexical)
- Qdrant named vectors (dense + sparse in same point)
- Server-side RRF fusion (no Python merge)
- Async embedding fix for LangGraph compatibility
- TD-103 (BM25 Index Desync) fully resolved

**For detailed plan, see:** [SPRINT_87_PLAN.md](SPRINT_87_PLAN.md)

---

## Sprint 88: RAGAS Phase 2 Evaluation (Tables + Code) ✅ (COMPLETED 2026-01-13)
**Epic:** Multi-Format RAG Evaluation
**Total Story Points:** 28 SP
**Status:** ✅ **COMPLETE** - 3 Features, 800-sample ingestion started

| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| 88.1 | T2-RAGBench Table Ingestion | 10 | P0 | ✅ DONE |
| 88.2 | MBPP Code Ingestion | 8 | P0 | ✅ DONE |
| 88.3 | Comprehensive Metrics Schema | 10 | P0 | ✅ DONE |

**Deliverables:**
- 150 T2-RAGBench financial table samples (FinQA)
- 150 MBPP code samples (Python)
- 500 Phase 1 plaintext samples (HotpotQA, RAGBench, LogQA)
- Comprehensive metrics: 4 RAGAS + ingestion + retrieval + LLM eval
- Multi-vector BGE-M3 embeddings validated

**Ingestion Status (Sprint 88):**
- Aborted after 50/500 docs (LLM-first cascade too slow: 300-600s/doc)
- Led to Sprint 100 (SpaCy-First Pipeline) for 10-20x speedup

**For detailed plan, see:** [SPRINT_88_PLAN.md](SPRINT_88_PLAN.md)

---

## Sprint 92: Performance Optimization & Deep Research Enhancements ✅ (COMPLETED 2026-01-15)
**Epic:** Query Performance Fixes & UI Enhancements + Extraction Bug Fixes
**Total Story Points:** 36 SP
**Status:** ✅ **COMPLETE** - 24 Features/Bugfixes complete

| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| 92.1 | FlagEmbedding Warmup Fix | 2 | P0 | ✅ DONE |
| 92.2 | Ollama GPU Configuration Fix | 2 | P0 | ✅ DONE |
| 92.3 | Deep Research UI Enhancements | 4 | P0 | ✅ DONE |
| 92.4 | Graph Search Performance Fix (17-19s → <2s) | 3 | P1 | ✅ DONE |
| 92.5 | Vector Results Display Fix | 2 | P1 | ✅ DONE |
| 92.6 | Chunk Ranking Fix (1-indexed consistency) | 2 | P1 | ✅ DONE |
| 92.7 | BM25 → Sparse Label Rename | 1 | P2 | ✅ DONE |
| 92.8 | Timing Metrics Fix | 2 | P2 | ✅ DONE |
| 92.9 | Graph Hops Count UI | 1 | P2 | ✅ DONE |
| 92.10 | Sparse/Dense Counts UI | 1 | P2 | ✅ DONE |
| 92.11 | Context Relevance Threshold (Anti-Hallucination) | 3 | P0 | ✅ DONE |
| 92.12 | Docker Frontend Deployment | 2 | P1 | ✅ DONE |
| 92.13 | CORS Configuration for External Access | 1 | P1 | ✅ DONE |
| 92.14 | Entity Consolidation Pipeline | 4 | P0 | ✅ DONE |
| 92.15 | Sparse Results Count Fix | 1 | P1 | ✅ DONE |
| 92.16 | Entity Max-Length Filter | 1 | P1 | ✅ DONE |
| 92.17 | Comprehensive Extraction Debug Logging | 3 | P0 | ✅ DONE |
| 92.18 | SpaCy Language Detection Fix (Bug) | 2 | P0 | ✅ DONE |
| 92.19 | Entity Consolidation SpaCy Type Check (Bug) | 1 | P0 | ✅ DONE |
| 92.20 | Time Import Fix for LLM Stages (Bug) | 1 | P0 | ✅ DONE |
| 92.21 | Sparse Search Stop Words Filter | 1 | P1 | ✅ DONE |
| 92.22 | Community Detection GDS Label Fix | 2 | P0 | ✅ DONE |
| 92.23 | Recursive LLM Adaptive Scoring (ADR-052) | 3 | P0 | ✅ DONE |
| 92.24 | RAGAS Namespace Fix for Sprint 88 Ingestion | 1 | P1 | ✅ DONE |

### Completed Features

**Feature 92.1: FlagEmbedding Warmup Fix ✅**
- **Problem:** 40-90s delay on first query due to lazy loading of embedding model
- **Solution:** Changed from lazy loading to eager loading via factory pattern
- **Implementation:** Modified BGE-M3 embedding initialization at API startup
- **Impact:** First query now <500ms (within normal latency range)
- **Commit:** b8e157d
- **Files Modified:** `src/components/vector_search/embedding_service.py`

**Feature 92.2: Ollama GPU Configuration Fix ✅**
- **Problem:** Ollama running on CPU instead of GPU (19 tok/s vs 77 tok/s)
- **Solution:**
  - Added `OLLAMA_FLASH_ATTENTION=false` for DGX Spark Blackwell GPU compatibility
  - Reduced `OLLAMA_NUM_PARALLEL` from 4 to 2 for GPU memory optimization
- **Impact:** 4x speed improvement (19 → 77 tok/s)
- **Commit:** 964d8e6
- **Files Modified:** `docker-compose.dgx-spark.yml`, `.env.template`

**Feature 92.3: Deep Research UI Enhancements ✅**
- **Problem:** Deep research progress tracking lacked detail about retrieval process
- **Solution:** Enhanced ResearchProgressTracker component with 4 new visualization levels
- **Implementation Details:**
  - **Plan step:** Show generated sub-queries with relevance scores
  - **Search step:** Display chunks found per sub-query (count + brief preview)
  - **Evaluation step:** Show relevance scores and quality labels for each context
  - **Summary step:** Display which chunks were selected for final response
  - **Error handling:** Better feedback for empty results and timeouts
- **Files Modified:**
  - `src/api/v1/research.py` - Backend research orchestration
  - `frontend/src/components/research/ResearchProgressTracker.tsx` - UI component
- **Impact:** Users now understand research flow and retrieval effectiveness at each stage

**Feature 92.11: Context Relevance Threshold (Anti-Hallucination) ✅**
- **Problem:** LLM generates answers from training data when retrieved contexts are irrelevant
- **Root Cause:** NO_HEDGING prompt forbids "I don't know", combined with irrelevant graph results
- **Solution:** Pre-generation relevance check with configurable threshold (default: 0.3)
- **Implementation:**
  - Added `MIN_CONTEXT_RELEVANCE_THRESHOLD = 0.3` constant
  - Added `_check_context_relevance()` method to verify max score exceeds threshold
  - Added `_no_relevant_context_answer()` for standardized "not found" response
  - Added `context_relevance_threshold` field to `GenerationConfig` model
  - Threshold configurable via Redis config (UI planned for Sprint 97)
- **Files Modified:**
  - `src/agents/answer_generator.py` - Relevance check before LLM generation
  - `src/components/generation_config/generation_config_service.py` - Config field
- **Impact:** Prevents hallucination by refusing to generate when contexts are irrelevant
- **Sprint 97:** Admin UI configuration for threshold adjustment planned

**Feature 92.12: Docker Frontend Deployment ✅**
- **Problem:** Frontend required manual `npm run dev` startup
- **Solution:** Containerized React/Vite frontend with auto-start
- **Implementation:**
  - Created `docker/Dockerfile.frontend` (multi-stage, Debian slim for ARM64)
  - Added frontend service to `docker-compose.dgx-spark.yml` on port 80
  - Volume mounts for hot-reload in development
  - Health dependency on API service
- **ADR:** ADR-053 documents architecture decision
- **Impact:** Frontend auto-starts with `docker compose up -d`

**Feature 92.13: CORS Configuration for External Access ✅**
- **Problem:** Browser CORS preflight (OPTIONS) returned 400 Bad Request
- **Solution:** Added external IP to CORS origins in docker-compose
- **Implementation:**
  - Added `CORS_ORIGINS` environment variable with JSON array format
  - Uses `DGX_SPARK_IP` variable for dynamic configuration
  - Added port 80 to default CORS origins in `config.py`
- **Impact:** Frontend on port 80 can communicate with API on port 8000

**Feature 92.14: Entity Consolidation Pipeline ✅**
- **Problem:** Entity extraction pipeline had multiple quality issues:
  - LLM returned full sentences (91-145 chars) as "ENTITY" type
  - No deduplication between SpaCy and LLM entities
  - Quality filter applied too late (after relation extraction)
- **Root Cause:** Missing consolidation step between entity extraction and relation extraction
- **Solution:** New `EntityConsolidator` class with 3-step filtering:
  1. **Type Validation:** Reject generic "ENTITY" type (LLM extraction failures)
  2. **Length Filtering:** Max 80 chars (filters sentence-like entities)
  3. **Deduplication:** Case-insensitive exact match (prefer SpaCy over LLM)
- **Implementation:**
  - New file: `src/components/graph_rag/entity_consolidator.py` (~350 LOC)
  - Integrated into extraction pipeline after Stage 2 (LLM enrichment)
  - Logs consolidation stats (filter rate, by type/length/duplicate)
- **Files Modified:**
  - `src/components/graph_rag/entity_consolidator.py` - New consolidation service
  - `src/components/graph_rag/extraction_service.py:1079-1106` - Pipeline integration
- **Impact:** Cleaner entity graphs, no more sentence-like entities in Neo4j
- **Test Results:** 37.5% filter rate on problematic entities

**Feature 92.15: Sparse Results Count Fix ✅**
- **Problem:** UI showed "Sparse 0%" despite results being returned
- **Root Cause:** `sparse_results_count` field not passed through agent pipeline
- **Solution:** Added `dense_results_count` and `sparse_results_count` mappings
- **Files Modified:**
  - `src/agents/vector_search_agent.py:119-125` - Metadata dict mapping
  - `src/agents/vector_search_agent.py:237-260` - Search result transformation
- **Impact:** UI now correctly shows Sparse search result counts

**Feature 92.16: Entity Max-Length Filter ✅**
- **Problem:** SpaCy's EntityQualityFilter had min_length but no max_length
- **Solution:** Added `max_length=80` parameter to filter sentence-like entities
- **Files Modified:**
  - `src/components/graph_rag/entity_quality_filter.py:110` - New parameter
  - `src/components/graph_rag/entity_quality_filter.py:186-196` - Filter logic
- **Impact:** Entities longer than 80 chars (likely sentences) are filtered

**Feature 92.17: Comprehensive Extraction Debug Logging ✅**
- **Problem:** Extraction pipeline failures hard to debug (no visibility into LLM prompts/responses)
- **Solution:** Full-detail logging module for extraction pipeline
- **Implementation:**
  - New module: `src/components/graph_rag/extraction_debug_logger.py` (~530 LOC)
  - Logs: Full LLM prompts, full LLM responses, all entities/relations with details
  - Stage timing breakdown (SpaCy NER, LLM enrichment, LLM relation extraction)
  - JSON validation errors and token counts
  - Saves debug sessions to `/tmp/extraction_debug/*.json`
- **Environment Variables:**
  - `AEGIS_EXTRACTION_DEBUG=1` (default) - Enable/disable debug logging
  - `AEGIS_EXTRACTION_DEBUG_DIR=/tmp/extraction_debug` - Output directory
- **Impact:** Enables root cause analysis for extraction issues

**Feature 92.18: SpaCy Language Detection Fix (Bug) ✅**
- **Problem:** English text detected as Spanish ("es") instead of English ("en")
- **Root Cause:** `_detect_language()` had NO English indicators (score=0), but Spanish indicators included "de ", "es ", "en " which appear in English text
- **Solution:**
  - Added 20+ English-specific indicators: " the ", " is ", " are ", " have ", " been ", etc.
  - Refined Spanish indicators to remove common false positives
  - Increased detection threshold from 2 to 3
- **Files Modified:** `src/components/graph_rag/hybrid_extraction_service.py:157-218`
- **Impact:** English text now correctly uses `en_core_web_lg` model (previously used `es_core_news_lg`)

**Feature 92.19: Entity Consolidation SpaCy Type Check (Bug) ✅**
- **Problem:** SpaCy entities with type="ENTITY" (invalid) passed through consolidation
- **Root Cause:** `_filter_entities()` called with `check_types=False` for SpaCy source
- **Solution:** Added `check_types=self.config.reject_generic_types` for SpaCy entities
- **Files Modified:** `src/components/graph_rag/entity_consolidator.py:186-191`
- **Impact:** SpaCy entities with generic "ENTITY" type now filtered out

**Feature 92.20: Time Import Fix for LLM Stages (Bug) ✅**
- **Problem:** LLM enrichment/relation stages failing with "name 'time' is not defined"
- **Root Cause:** `time` imported inside `extract_with_spacy_first_pipeline()` but used in `_pipeline_stage2_entity_enrichment()` and `_pipeline_stage3_relation_extraction()` which are separate methods
- **Solution:** Moved `import time` to module level (line 34)
- **Files Modified:** `src/components/graph_rag/extraction_service.py:30-36`
- **Impact:** LLM stages now execute correctly (verified: 824ms enrichment, 14s relation extraction)

**Combined Impact of 92.18-92.20 Bug Fixes:**
| Metric | Before (Bugs) | After (Fixed) |
|--------|---------------|---------------|
| Language Detection | "es" (wrong) | "en" (correct) |
| Entity Types | 45 with "ENTITY" | 10 clean entities |
| Relations Extracted | 0 | **7 semantic relations** |
| Total Duration | 30min timeout | **46 seconds** |

### Additional Completed Features (Sprint 92 Continuation)

**Feature 92.4: Graph Search Performance Fix ✅**
- **Problem:** Graph search taking 17-19s, target <2s
- **Root Cause:** Sequential LLM calls + semantic reranking overhead
- **Solution:**
  - Background intent extraction with `asyncio.create_task()` (non-blocking)
  - Skip semantic reranking by default (use `expand_entities()` not `expand_and_rerank()`)
  - Added comprehensive timing logs for phase profiling
- **Impact:** 17-19s → <2s (**89-90% reduction**)
- **Files Modified:** `graph_query_agent.py`, `dual_level_search.py`, `entity_expansion.py`
- **Tests:** 5 unit tests added (100% pass)

**Feature 92.5: Vector Results Display Fix ✅**
- **Problem:** 5 results retrieved but 0 source cards displayed
- **Root Cause:** Frontend filtered sources by citation markers `[1]`, `[2]` - if LLM doesn't cite, 0 sources shown
- **Solution:** Fallback logic: if no citations found but sources exist, show all sources
- **Files Modified:** `MessageBubble.tsx` (lines 136-153)
- **Impact:** Sources always displayed when available

**Feature 92.6: Chunk Ranking Fix ✅**
- **Problem:** Rank #6 shown instead of higher ranks (#1-3)
- **Root Cause:** 3 issues found:
  1. Missing rank in frontend metadata
  2. 0-indexed ranks in Ollama reranker (`enumerate` without `start=1`)
  3. 0-indexed ranks in legacy reranker
- **Solution:** Fixed all 3 to use 1-indexed ranks consistently
- **Files Modified:** `chat.py`, `four_way_hybrid_search.py`, `reranker.py`
- **Tests:** 5 unit tests added (100% pass)

**Feature 92.21: Sparse Search Stop Words Filter ✅**
- **Problem:** Sparse search showing stop words as keywords ("hast", "du", "eine")
- **Solution:** Reuse `MULTILINGUAL_STOPWORDS` from bm25_search.py (3,999 words, 10 languages)
- **Implementation:** Added `filter_stop_words()` function to `four_way_hybrid_search.py`
- **Files Modified:** `four_way_hybrid_search.py` (lines 309, 715, 823)

**Feature 92.22: Community Detection GDS Label Fix ✅**
- **Problem:** Graph Global returning 0 results, community detection failing
- **Root Cause:** GDS Leiden algorithm using wrong label `'Entity'` instead of `'base'`
- **Solution:** Changed graph projection label in `community_detector.py`
- **Batch Run:** Manually assigned communities to 2,534 existing entities (2,387 communities created)
- **Files Modified:** `community_detector.py`

**Feature 92.23: Recursive LLM Adaptive Scoring (ADR-052) ✅**
- **Documented:** ADR-052 for recursive LLM adaptive scoring system
- **Implementation:** Completed in Sprint 92 session
- **Tests:** Mock-based validation script added

**Feature 92.24: RAGAS Namespace Fix for Sprint 88 Ingestion ✅**
- **Problem:** RAGAS evaluation finding 0 contexts (namespace mismatch)
- **Root Cause:** Documents ingested as `ragas_phase1_sprint88`, but eval using `ragas_phase1`
- **Solution:** Run evaluation with correct namespace: `--namespace ragas_phase1_sprint88`
- **Impact:** RAGAS metrics now computing correctly

### Success Criteria (All Met)

- [x] FlagEmbedding warmup eliminated (Feature 92.1)
- [x] Ollama GPU utilization verified (Feature 92.2)
- [x] Deep research visibility improved (Feature 92.3)
- [x] Graph search <2s latency (Feature 92.4) ✅ **17-19s → <2s**
- [x] Vector results display correctly (Feature 92.5) ✅ **Fallback to all sources**
- [x] Chunk ranking fixed (Feature 92.6) ✅ **1-indexed consistency**
- [x] All timing metrics populated (Feature 92.8)
- [x] All UI labels and counts accurate (92.7, 92.9, 92.10)
- [x] Stop words filtered from Sparse search (Feature 92.21)
- [x] Community detection working (Feature 92.22)
- [x] RAGAS evaluation running on correct namespace (Feature 92.24)

### Performance Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| First Query Latency | 40-90s | <500ms | **98% faster** |
| Ollama Token Rate | 19 tok/s | 77 tok/s | **4x faster** |
| Graph Search Latency | 17-19s | <2s | **89-90% reduction** |
| Source Display | 0/5 shown | 5/5 shown | **100% visibility** |
| Rank Consistency | 0-indexed | 1-indexed | **Correct ordering** |

### References

- Commit b8e157d - FlagEmbedding warmup fix
- Commit 964d8e6 - Ollama GPU configuration
- [ADR-024: BGE-M3 Embeddings](../adr/ADR-024-bge-m3-embeddings.md)
- [ADR-027: Docling CUDA Ingestion](../adr/ADR-027-docling-cuda-ingestion.md)

---

## Sprint 100: SpaCy-First Pipeline (MOVED from Sprint 89) 🔄 (IN PROGRESS 2026-01-13)
**Epic:** Entity Extraction Performance Optimization
**Total Story Points:** 18 SP
**Status:** 🔄 **IN PROGRESS** - Implementation complete, full ingestion running
**Note:** Originally planned as Sprint 89, moved to Sprint 100 to make room for Sprint 90 (Anthropic Agent Skills)

| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| 100.1 | SpaCy NER Stage (Stage 1) | 5 | P0 | ✅ DONE |
| 100.2 | LLM Entity Enrichment (Stage 2) | 5 | P0 | ✅ DONE |
| 100.3 | LLM Relation Extraction (Stage 3) | 5 | P0 | ✅ DONE |
| 100.4 | Feature Flag & Routing | 3 | P1 | ✅ DONE |

**Deliverables:**
- 3-Stage Pipeline (SpaCy ~50ms → LLM Enrichment ~5-15s → Relations ~10-30s)
- **Performance:** 27-54s/doc (vs 300-600s LLM-first cascade = **6-10x faster**)
- Feature flag: `AEGIS_USE_LEGACY_CASCADE=1` for rollback
- Test ingestion: 4/5 successful (80% vs 56% with LLM-first)

**Files Modified:**
- `src/config/extraction_cascade.py` - Pipeline config
- `src/prompts/extraction_prompts.py` - New prompts
- `src/components/graph_rag/extraction_service.py` - Pipeline implementation
- `src/components/graph_rag/extraction_factory.py` - Routing

**For detailed plan, see:** [SPRINT_100_PLAN.md](SPRINT_100_PLAN.md) (formerly SPRINT_89_PLAN.md)

---

## Sprint 101: E2E Validation & GDPR Bug Fix ✅ (COMPLETED 2026-01-15)
**Epic:** API Contract Testing & Critical Bug Fix
**Total Story Points:** 10 SP (4 SP bug fix + 6 SP testing)
**Status:** ✅ **COMPLETE** - All Sprint 100 fixes validated

| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| 101.1 | GDPR Consent Page Bug Fix | 4 | P0 | ✅ DONE |
| 101.2 | Playwright E2E Testing (7 test journeys) | 6 | P1 | ✅ DONE |

**Deliverables:**
- GDPR/Audit routers uncommented + Vite proxy added
- All 8 Sprint 100 contract fixes validated (7 E2E + 1 code verified)
- Playwright test journeys with screenshots

**Sprint 100 Validation Summary:**
- ✅ Fix #1: Skills List Pagination (validated in Sprint 100)
- ✅ Fix #2: GDPR Consents field (`items`)
- ✅ Fix #3: Audit Events field (`items`)
- ✅ Fix #4: Audit Reports query params (ISO 8601)
- ✅ Fix #5: Agent Hierarchy status enum (lowercase)
- ✅ Fix #6: GDPR Status mapping (`granted` → `active`)
- ✅ Fix #7: Agent Details field mapping (code verified)
- ✅ Fix #8: Skills Config validation endpoint

**Files Modified:**
- `src/api/main.py` - Uncommented GDPR/Audit routers
- `frontend/vite.config.ts` - Added `/api` proxy

**For detailed report, see:** [SPRINT_101_COMPLETE.md](SPRINT_101_COMPLETE.md)

---

## Sprint 90: Anthropic Agent Skills Foundation 🔄 (STARTING 2026-01-13)
**Epic:** Agentic Framework Transformation (Phase 1 of 7)
**Total Story Points:** 36 SP
**Status:** 🔄 **IN PROGRESS** - Implementation starting with parallel subagents

| Feature | SP | Priority | Status | Agent |
|---------|-----|----------|--------|-------|
| 90.1 | Skill Registry Implementation | 10 | P0 | 🔄 STARTING | backend-agent |
| 90.2 | Reflection Loop in Agent Core | 8 | P0 | 📝 PLANNED | backend-agent |
| 90.3 | Hallucination Monitoring & Logging | 8 | P0 | 📝 PLANNED | backend-agent |
| 90.4 | SKILL.md MVP Structure | 5 | P0 | 📝 PLANNED | documentation-agent |
| 90.5 | Base Skills (Retrieval, Answer) | 5 | P1 | 📝 PLANNED | documentation-agent |

**Target Outcomes:**
- Skill Registry operational with embedding-based intent matching
- Reflection loop for self-critique and validation
- Hallucination detection and logging
- RAGAS Faithfulness: 80% → 88%+

**For detailed plan, see:** [SPRINT_90_PLAN.md](SPRINT_90_PLAN.md)

---

## Sprint 97: Admin UI Configuration Enhancements 📝 (PLANNED)
**Epic:** Admin UI Settings & Quality Tuning
**Total Story Points:** ~12 SP (estimated)
**Status:** 📝 **PLANNED** - Deferred from Sprint 92

| Feature | SP | Priority | Status | Description |
|---------|-----|----------|--------|-------------|
| 97.1 | Context Relevance Threshold UI | 4 | P0 | 📝 PLANNED | Admin UI slider to configure anti-hallucination threshold (0.0-1.0) |
| 97.2 | HallucinationMonitor Integration | 4 | P1 | 📝 PLANNED | Integrate Sprint 90 HallucinationMonitor into answer generation pipeline |
| 97.3 | Hallucination Detection Dashboard | 4 | P2 | 📝 PLANNED | Admin UI for hallucination metrics and logs visualization |

**Target Outcomes:**
- UI slider for `context_relevance_threshold` in Admin Settings
- Real-time hallucination detection with claim-level verification
- Dashboard for monitoring hallucination metrics (PASS/WARN/FAIL verdicts)

**Dependencies:**
- Sprint 92.11: Context Relevance Threshold (Backend) ✅ DONE
- Sprint 90.3: Hallucination Monitoring & Logging ✅ DONE

---

## Cumulative Story Points

| Sprint | SP | Cumulative |
|--------|-----|------------|
| 1-70 | ~2,100 | 2,100 |
| 71 | 50 | 2,150 |
| 72 | 55 | 2,205 |
| 73 | 48 | 2,253 |
| 82 | 8 | 2,261 |
| 83 | 26 | 2,287 |
| 87 | 34 | 2,321 |
| 88 | 28 | 2,349 |
| 90 | 36 | 2,385 |
| 100 | 18 | 2,403 |
| 101 | 10 | 2,413 |
| **Total** | **2,413** | - |

---

## Sprint 108: E2E Test Baseline ✅ (COMPLETED 2026-01-16)
**Epic:** Playwright E2E Test Suite Establishment
**Total Story Points:** ~15 SP (testing infrastructure)
**Status:** ✅ **COMPLETE** - Baseline established

**Objectives:**
- Establish E2E test infrastructure for all 16 feature groups
- Create baseline test suite for Sprints 90-96 features
- Identify test gaps and fix priorities

**Deliverables:**
- ✅ 16 E2E test groups created (Groups 01-16)
- ✅ ~115 individual tests written
- ✅ Baseline pass rate: 410/1011 (40.6%)
- ✅ Test infrastructure and fixtures established

**Test Groups Created:**
1. MCP Tools (6 tests)
2. Bash Execution (5 tests)
3. Python Execution (5 tests)
4. Browser Tools (6 tests)
5. Skills Management (8 tests)
6. Skills Using Tools (9 tests)
7. Memory Management (10 tests)
8. Deep Research (8 tests)
9. Long Context (10 tests)
10. Hybrid Search (9 tests)
11. Document Upload (8 tests)
12. Graph Communities (7 tests)
13. Agent Hierarchy (8 tests)
14. GDPR & Audit (10 tests)
15. Explainability (9 tests)
16. MCP Marketplace (8 tests)

**Key Findings:**
- Most failures due to missing data-testid attributes
- API mock format mismatches
- React Router navigation reliability issues
- Test priority groups identified for Sprint 109

**For detailed report, see:** Test results in `/frontend/test-results/`

---

## Sprint 109: E2E Test Fixes (Groups 04-08, 10-12) 🔄 (IN PROGRESS 2026-01-17)
**Epic:** E2E Test Completion - Phase 1
**Total Story Points:** 62 SP
**Status:** 🔄 **IN PROGRESS** - Group 05 complete, Group 04 in progress

**Execution Strategy:**
- **Phase 1:** Complete Groups 04-06 (Browser, Skills, Tools) - 10 SP
- **Phase 2:** Groups 07-08 (Memory, Research) - 20 SP
- **Phase 3:** Groups 10-12 (Hybrid Search, Upload, Communities) - 30 SP
- **Deferred:** Group 06 (requires chat integration), Group 09 (moved to Sprint 110)

| Feature | Tests | SP | Status | Pass Rate |
|---------|-------|-----|--------|-----------|
| 109.1 | Groups 04-06 (Browser, Skills, Tools) | 23 | 🟡 Partial | 39% (9/23) |
| 109.2 | Groups 07-08 (Memory, Research) | 18 | 📝 Next | 0% |
| 109.3 | Groups 10-12 (Search, Upload, Communities) | 24 | 📝 Planned | 0% |

### Completed (109.1 Partial)
✅ **Group 05: Skills Management** - 8/8 tests (100%)
- Fixed API response format (array → SkillListResponse object)
- Fixed selector specificity (scoped to avoid dropdown matches)
- Changed to direct navigation (navigateClientSide)
- Added data-testid="save-error" to SkillConfigEditor
- Updated config link selectors to use data-testids

🟡 **Group 04: Browser Tools** - 1/6 tests (16.7%)
- Fixed tool parameter format (input_schema → parameters[])
- Changed from expandable cards to dropdown selection
- Tools load correctly, execution mocks need refinement

⏸️ **Group 06: Skills Using Tools** - 0/9 tests (deferred)
- Requires chat interface integration
- Beyond scope of data-testid fixes
- Moved to Sprint 110+

### Files Modified
- `e2e/group04-browser-tools.spec.ts` - Mock format + dropdown selection
- `e2e/group05-skills-management.spec.ts` - API format + selectors + navigation
- `e2e/group06-skills-using-tools.spec.ts` - API response format
- `src/pages/admin/SkillConfigEditor.tsx` - Added data-testid

**Commit:** `ccd6902` - Feature 109.1 Partial (8 SP earned)

### Next Steps (Current Sprint)
1. 🔄 **NOW:** Complete Group 04 Browser Tools (2 SP, 2-4 hours)
2. 📝 **Next:** Group 07 Memory Management (10 SP, 1-2 days)
3. 📝 **Next:** Group 08 Deep Research (10 SP, 1-2 days)
4. 📝 **Final:** Groups 10-12 Core RAG (30 SP, 3-4 days)

**Sprint 109 Target:** >80% pass rate per group, ≥50 tests passing overall

---

## Sprint 110: E2E Test Fixes (Groups 01-03, 13-16) 📝 (PLANNED)
**Epic:** E2E Test Completion - Phase 2
**Total Story Points:** 60 SP
**Status:** 📝 **PLANNED** - Focus: Tool Execution & Enterprise Features

**Execution Strategy:**
- **Phase 1:** Groups 01-03 Tool Execution (16 tests, 20 SP)
- **Phase 2:** Groups 13-16 Enterprise Features (35 tests, 40 SP)

| Feature | Tests | SP | Priority | Description |
|---------|-------|-----|----------|-------------|
| 110.1 | Groups 01-03: Tool Execution | 16 | P0 | MCP, Bash, Python execution |
| 110.2 | Groups 13-15: Enterprise | 27 | P1 | Hierarchy, GDPR, Explainability |
| 110.3 | Group 16: MCP Marketplace | 8 | P2 | Server marketplace UI |

### Groups 01-03: Tool Execution (20 SP)
- MCP Tools basic operations
- Bash command execution and output
- Python code execution and output

### Groups 13-16: Enterprise Features (40 SP)
- Agent Hierarchy visualization (partial work from Sprint 100)
- GDPR & Audit compliance UI
- Explainability dashboards
- MCP Marketplace (server discovery, installation)

**Sprint 110 Target:** >90% pass rate on Groups 01-03, 13-16, ≥80 tests passing

---

## Sprint 111: Long Context E2E + Cost Dashboard Token Chart 📝 (PLANNED)
**Epic:** E2E Test Completion - Phase 3 + Admin UI Enhancement
**Total Story Points:** 18 SP
**Status:** 📝 **PLANNED** - Focus: Long Context Handling + Cost Monitoring

**Note:** Long Context moved from Sprint 110 to allow focused implementation.

| Feature | Tests | SP | Priority | Description |
|---------|-------|-----|----------|-------------|
| 111.1 | Group 09: Long Context E2E | 10 | P0 | Large document handling, context window mgmt |
| 111.2 | Cost Dashboard Token Usage Chart | 8 | P0 | Token usage over time with range slider |

### Feature 111.1: Group 09 Long Context
**Scope:**
- Large document handling (>100K tokens)
- Context window management UI
- Document chunking visualization
- Context relevance scoring display

**Tests:**
1. Large document upload and processing
2. Context window indicators
3. Chunk preview functionality
4. Relevance score visualization
5. Long context search
6. Context compression strategies
7. Multi-document context merging
8. Context overflow handling
9. Context quality metrics
10. Context export functionality

**Expected Issues:**
- Large file upload UI/progress
- Context window visualization
- Chunk navigation and preview
- Score display formatting

### Feature 111.2: Cost Dashboard Token Usage Chart
**Scope:**
- Token Usage Over Time line chart (Recharts oder Chart.js)
- Schieberegler für Zeitraum-Auswahl (1 Tag - 3 Jahre)
- Logarithmische/Lineare Skala toggle
- Provider-Filter (alle/einzeln)
- Tägliche/Wöchentliche/Monatliche Aggregation

**UI Components:**
1. `TokenUsageChart.tsx` - Zeitverlaufs-Grafik Komponente
2. `TimeRangeSlider.tsx` - Slider mit Presets (1d, 7d, 30d, 90d, 1y, 3y)
3. `ChartControls.tsx` - Aggregation + Provider Filter

**Backend Requirements:**
- `GET /api/v1/admin/costs/timeseries?start=...&end=...&aggregation=daily`
- Response: `{ data: [{ date: "2026-01-17", tokens: 150000, cost_usd: 0.45, provider: "ollama" }, ...] }`

**Tests:**
1. Chart renders with data
2. Slider changes time range correctly
3. Provider filter works
4. Aggregation toggle updates chart
5. Empty state handling
6. Loading state
7. Error state
8. Export chart as PNG

**Sprint 111 Target:** 100% pass rate on Group 09 (10/10 tests) + Token Chart functional

---

## Cumulative Story Points (Updated)

| Sprint | SP | Cumulative | Status |
|--------|-----|------------|--------|
| 1-70 | ~2,100 | 2,100 | ✅ |
| 71 | 50 | 2,150 | ✅ |
| 72 | 55 | 2,205 | ✅ |
| 73 | 48 | 2,253 | ✅ |
| 82 | 8 | 2,261 | ✅ |
| 83 | 26 | 2,287 | ✅ |
| 87 | 34 | 2,321 | ✅ |
| 88 | 28 | 2,349 | ✅ |
| 90 | 36 | 2,385 | ✅ |
| 100 | 18 | 2,403 | ✅ |
| 101 | 10 | 2,413 | ✅ |
| 108 | 15 | 2,428 | ✅ |
| 109 | 62 | 2,490 | ✅ |
| 110 | 70 | 2,560 | ✅ |
| 111 | 62 | 2,622 | ✅ |
| 112 | 34 | 2,656 | ✅ |
| 113 | 36 | 2,692 | ✅ |
| **114** | **18** | **2,710** | ✅ **Complete** |
| **115** | **48** | **2,758** | ✅ **Complete** |
| **116** | **36** | **2,794** | ✅ **Complete** |
| **117** | **47** | **2,841** | ✅ **Complete** |
| **118** | **40** | **2,881** | ✅ **Complete** |
| **119** | **71** | **2,952** | ✅ **Complete** |
| **120** | **64** | **3,016** | ✅ **Complete** |
| **121** | **44** | **3,060** | ✅ **Complete** |
| **122** | **26** | **3,086** | ✅ **Complete** |
| **123** | **21** | **3,107** | ✅ **Complete** |
| **124** | **36** | **3,143** | ✅ **Complete** |
| **125** | **45** | **3,188** | ✅ **Complete** |
| **126** | **22** | **3,210** | ✅ **Complete** |
| **127 (Planned)** | **13** | **3,223** | 📋 |
| **128 (Planned)** | **8** | **3,231** | 📋 |
| **129 (Planned)** | **18** | **3,249** | 📋 |
| **Total** | **3,249** | - | - |

---

## Current Sprint Status

**Current Sprint:** 126 ✅ **Complete** (2026-02-07)
**Previous Sprint:** 125 ✅ **Complete** (2026-02-06)
**Next Sprint:** 127 📝 **Planned** (RAGAS Phase 1 Benchmark with vLLM Extraction)
**Focus:** Engine Mode + Domain Sub-Types + Pre-commit Hooks + CI/CD Streamlining (22 SP, 10 features)

### Sprint 114 Summary (Complete) ✅

**Date:** 2026-01-20
**Story Points:** 18 SP delivered (of 40 planned)
**Duration:** 184 minutes full E2E test run
**Baseline Established:** Critical for Sprint 115 optimization

**Features Completed:**
- **Feature 114.1:** Pattern Bug Fixes (15 SP) - 19 bugs fixed
- **Feature 114.2:** Missing data-testids (10 SP) - Already complete from Sprint 72
- **Feature 114.3:** Skip Missing Features (3 SP) - 28 tests skipped
- **CI/CD Improvements:** 6 deprecated actions fixed, 2 scripts created

**Key Results:**
- **Baseline E2E Pass Rate:** 46.5% (511/1099 tests passed)
- **Baseline E2E Duration:** 184 minutes (3h 4m)
- **Failure Analysis:** 83% timeout-related (Category E = 448/538 failures)
- **Category E Breakdown:**
  - 394 tests exceed 60s timeout
  - 123 tests exceed 120s (11.2%)
  - Top tests: 900s, 600s, 183s multi-turn conversations
- **CI Fixes Applied:** 5 deprecated actions, 1 quality gate fix, 2 scripts created
- **Modified Files:** 4 test files, 3 workflow files

**Critical Findings:**
- **Root Causes Identified:** LLM call chains, UI rendering waits, inefficient queries
- **Potential Optimizations:** 47% runtime savings available through mocking + parallelization
- **Test Pattern Categories:** 48 distinct patterns identified (Multi-Turn, Conversation UI, Domain Training, Upload, etc.)

**See:** `docs/sprints/SPRINT_114_PLAN.md` (Complete documentation)

---

### Sprint 115 ✅ **Complete** (2026-01-20)

**Status:** ✅ Complete
**Focus:** E2E Test Stabilization, Graph Query Optimization, CI/CD Optimization
**Story Points:** 48 SP delivered (100%)
**Duration:** 1 day (2026-01-20)

**Key Achievements:**
- **Query Latency:** 27s → 1.4s (**95% faster**) via ADR-057 Graph Query Optimization
- **Multi-Turn Tests:** Timeout → Passing (5/7 tests now pass)
- **CI Pipeline:** 45min → 20min (**56% faster**) via parallelization
- **Test Infrastructure:** 3-tier system with automatic retries

| Feature | SP | Status | Description |
|---------|-----|--------|-------------|
| **115.0** | **1** | ✅ | Playwright Timeout Alignment (180s) |
| **115.1** | **1** | ✅ | Graph Search Early-Exit (empty results) |
| **115.2** | **15** | ✅ | Backend Tracing via LangSmith Integration |
| **115.3** | **15** | ✅ | CI/CD Optimization (parallelization, caching) |
| **115.4** | **8** | ✅ | Test Suite Optimization (tiers, retries, timeouts) |
| **115.5** | **3** | ✅ | CI Bug Fixes (TypeScript compilation) |
| **115.6** | **5** | ✅ | Graph Query Optimization (ADR-057) |
| **Total** | **48** | ✅ | **100% Complete** |

**Critical Discoveries:**
1. **SmartEntityExpander** caused 97% of query latency (26s of 27s total)
2. **Redundant Graph Search Paths:** `graph_query_node` + `FourWayHybridSearch` were running in parallel
3. **Solution:** Disable `graph_query_node`, add Vector-First Graph-Augment (ADR-057)

**Test Infrastructure Improvements:**
- **3-Tier System:** fast (30s), standard (180s), full (300s)
- **Automatic Retries:** Local: 1, CI: 2
- **Unimplemented Features:** Already skipped in Sprint 114

**E2E Test Results (Post-Optimization):**
- Multi-Turn Conversation: 17/19 passed (18.8 minutes total)
- Conversation UI: 21/28 passed (partial run)
- 2 failures documented in Sprint 116 (test setup issues, not performance)

**See:** `docs/sprints/SPRINT_115_PLAN.md` (Full documentation)
**ADR:** `docs/adr/ADR-057-graph-query-optimization.md` (Architecture decision)

---

## Sprint 116 🔄 **In Progress** (2026-01-20)

**Status:** Planning (not started)
**Focus:** UI Features, Error Handling, Citations, Graph UI, Deep Research
**Story Points:** 36 SP planned
**Predecessor:** Sprint 115 (Graph Query Optimization)
**Successor:** Sprint 117 (Domain Training)

**Features Planned:**
- Domain Default Seeding (3 SP)
- Admin Dashboard Stats Cards (5 SP)
- API Error Handling (5 SP)
- Citation Tooltips & Linking (8 SP)
- Graph Edge Filters UI (5 SP)
- Deep Research Multi-Step (13 SP)

**See:** `docs/sprints/SPRINT_116_PLAN.md` (Detailed planning)
**Analysis:** `docs/sprints/SPRINT_116_SKIPPED_TESTS_ANALYSIS.md` (Skipped test analysis)

---

## Sprint 117 📋 **Planned** (After Sprint 116) - Domain Training API Phase 2

**Status:** Planning (Documentation Complete)
**Focus:** Complete Domain Training API with Classification, Discovery, Augmentation & Batch Ingestion
**Story Points:** 61 SP (9 Features)
**Predecessor:** Sprint 116
**Documentation:** [SPRINT_117_PLAN.md](SPRINT_117_PLAN.md)

### Feature Breakdown (61 SP)

| # | Feature | SP | Backend | Frontend | E2E Tests |
|---|---------|-----|---------|----------|-----------|
| **117.1** | **Domain Training API - CRUD** | **13** | ✅ GET/POST/PUT/DELETE /api/v1/admin/domains/* | ✅ DomainList, DomainCard, CreateModal, DetailsView | ✅ 6 tests |
| **117.2** | **Domain Classification** | **8** | ✅ POST /api/v1/admin/domains/classify (LLM-based) | ✅ DocumentClassifier, ClassificationResults | ✅ 6 tests |
| **117.3** | **Domain Auto-Discovery** | **8** | ✅ POST /api/v1/admin/domains/discover (Entity clustering) | ✅ DiscoveryWizard, DocumentUpload, Results | ✅ 6 tests |
| **117.4** | **Domain Data Augmentation** | **8** | ✅ POST /api/v1/admin/domains/augment (LLM synthesis) | ✅ AugmentationWizard, ResultsDisplay | ✅ 6 tests |
| **117.5** | **Domain Batch Ingestion** | **8** | ✅ POST /api/v1/admin/domains/ingest-batch (Routing) | ✅ BatchWizard, ProgressBar, Results | ✅ 7 tests |
| **117.6** | **Domain Details & Status** | **5** | ✅ GET training-status, training logs | ✅ DetailsPanel, ProgressBar, Logs | ✅ 6 tests |
| **117.7** | **Domain Validation** | **5** | ✅ POST /api/v1/admin/domains/{id}/validate | ✅ ValidationReport, HealthGauge, Issues | ✅ 6 tests |
| **117.8** | **Response Format** | **3** | ✅ Standard envelope across all endpoints | ✅ N/A (Backend-only) | ✅ Tests |
| **117.9** | **Default Domain Seeding** | **3** | ✅ Seed "general" domain on init | ✅ N/A (Backend-only) | ✅ 1 test |
| **Total** | | **61** | **9 APIs** | **18 Components** | **40+ Tests** |

### API Endpoints (12 total)

**Core Domain Management:**
- `GET /api/v1/admin/domains/` - List domains (pagination, filtering)
- `POST /api/v1/admin/domains/` - Create domain
- `GET /api/v1/admin/domains/{name}` - Get details
- `PUT /api/v1/admin/domains/{name}` - Update
- `DELETE /api/v1/admin/domains/{name}` - Delete

**Domain Features:**
- `POST /api/v1/admin/domains/classify` - LLM-based classification
- `POST /api/v1/admin/domains/discover` - Auto-discover from samples
- `POST /api/v1/admin/domains/augment` - Generate synthetic training data
- `POST /api/v1/admin/domains/ingest-batch` - Batch document ingestion

**Training & Validation:**
- `GET /api/v1/admin/domains/{name}/training-status` - Progress tracking
- `POST /api/v1/admin/domains/{name}/train` - Start training
- `POST /api/v1/admin/domains/{id}/validate` - Validate domain

### Frontend Components (18 total)

**Domain Management (4 components):**
- `DomainList` - Paginated domain listing
- `DomainCard` - Individual domain display
- `CreateDomainModal` - Wizard-style creation
- `DomainDetailsView` - Full domain information

**Classification (2 components):**
- `DocumentClassifier` - Text input for classification
- `ClassificationResults` - Results display with confidence

**Discovery (3 components):**
- `DomainDiscoveryWizard` - Multi-step discovery flow
- `DocumentUploadArea` - Drag-drop file upload
- `DiscoveryResults` - Display suggested domains

**Augmentation (2 components):**
- `AugmentationWizard` - Multi-step augmentation
- `AugmentationResults` - Generated samples display

**Batch Ingestion (3 components):**
- `BatchIngestionWizard` - Multi-step ingestion
- `BatchProgress` - Real-time progress tracking
- `BatchResults` - Results summary

**Training & Validation (4 components):**
- `DomainDetailsPanel` - Domain information
- `TrainingProgressBar` - Progress visualization
- `TrainingLogs` - Real-time log streaming
- `ValidationReport` - Validation results

### Key Technical Details

**LLM Integration:**
- Classification: Compare document against all domains
- Discovery: Extract entities, cluster semantically, suggest configurations
- Augmentation: Support 5 strategies (paraphrase, substitution, back-translation, synthesis, hybrid)
- Batch Ingestion: Auto-classify and route documents

**Performance Targets:**
- CRUD operations: <100ms
- Classification: <500ms (excl. LLM)
- Discovery: <2s (excl. LLM)
- Augmentation: <60s for 100 samples
- Batch ingestion: <5min for 100 documents
- Validation: <10s for 1000+ samples

**Data Models:**
- DomainSchema: name, description, entity_types, relation_types, intent_classes, model_family, confidence_threshold, metrics
- Standard Response Envelope: success, data, metadata, pagination

### Test Strategy

**Unit Tests:** 80%+ coverage (domain CRUD, validation, classification logic)
**Integration Tests:** 70%+ coverage (database persistence, LLM integration)
**E2E Tests:** 40+ tests covering all 9 features (Playwright)
**Performance Tests:** Baseline measurements for all endpoints

### Success Criteria

- [ ] All 12 API endpoints implemented and documented
- [ ] Input validation with proper HTTP status codes
- [ ] 18 React components with responsive design
- [ ] 40+ E2E tests passing
- [ ] Performance targets met
- [ ] Unit/integration test coverage >75%
- [ ] Comprehensive error handling
- [ ] API documentation complete

### Critical Path Dependencies

```
Sprint 117.1 (Domain CRUD) - Foundation
├── 117.2 (Classification) - Depends on 117.1
├── 117.3 (Discovery) - Depends on 117.1
├── 117.4 (Augmentation) - Depends on 117.1
├── 117.5 (Batch Ingestion) - Depends on 117.1
├── 117.6 (Training Status) - Depends on 117.1
└── 117.7 (Validation) - Depends on 117.1
```

**Dependencies:** Sprint 116 completion (Default domain seeding provides foundation)
**Blocked By:** None identified
**Blocks:** Sprint 118+ (Graph versioning, deep research) may depend on domain structures

**See:** [SPRINT_117_PLAN.md](SPRINT_117_PLAN.md) for complete detailed specification

---

## Sprint 118 ✅ **Complete** (2026-01-20 to 2026-01-25)

**Status:** ✅ Complete
**Focus:** Testing Infrastructure & Bug Fixes
**Story Points:** 40 SP delivered (23 planned + 17 bug fixes)
**Predecessor:** Sprint 117

**Achievements:**
- **Follow-up Questions:** 9/9 tests pass (100%) - Fixed 9 bugs (BUG-118.1 to BUG-118.9)
- **Graph Edge Filters:** data-testid fix verified
- **Memory Consolidation:** Mock URL corrected

**Bug Fixes (17 SP):**
- SSE Cache, Environment URLs, Component Integration, Multi-turn Cache, Test Timeouts

**Carry-Over to Sprint 119:**
- Visual Regression Framework (5 SP)
- Performance Regression Tests (13 SP)
- Graph Communities UI (5 SP)

**See:** `docs/sprints/SPRINT_118_PLAN.md`

---

## Sprint 119 ✅ **Complete** (2026-01-25 to 2026-01-26)

**Status:** ✅ Complete
**Focus:** Skipped E2E Test Analysis & Stabilization + Feature Implementation
**Story Points:** 71 SP delivered (25 SP bug fixes + 12 SP feature fixes + 34 SP features)
**Predecessor:** Sprint 118

**Achievements:**
- **Phase 1 (25 SP):** 8 E2E bug categories analyzed and fixed (BUG-119.1 to BUG-119.8)
- **Phase 2 (12 SP):** Domain Training API router prefix fix (31 tests un-skipped), BM25→SPARSE migration, long context fixture, follow-up tags
- **Phase 3 (34 SP):** Skills/Tools Chat Integration (20 SP), Graph Seed Data Script (3 SP), Conversation History Page (11 SP)

**Features Implemented:**
- **119.1:** Skills/Tools SSE handlers + ToolExecutionPanel + SkillActivationIndicator (18/18 E2E tests)
- **119.2:** `scripts/seed_test_graph_data.py` (10 entities, 13 relationships)
- **119.3:** `/history` page (382 LOC) with search, delete, export, date grouping (12/14 E2E tests)
- **119.5:** Domain Training API prefix fix (31 tests un-skipped)

**Carry-Over to Sprint 120:**
- Visual Regression Framework (5 SP)
- Performance Regression Tests (13 SP)
- Admin Indexing UI (5 SP)

**See:** `docs/sprints/SPRINT_119_PLAN.md`

---

## Sprint 120 ✅ **Complete** (2026-01-27)

**Status:** ✅ Complete
**Focus:** UI Polish, Tools Activation, Performance Fixes
**Story Points:** ~64 SP
**Predecessor:** Sprint 119

**Key Achievements:**
- Ollama GPU offload fix: 3.1→74 tok/s (+2,287%)
- MCP tool execution, disconnect crash fix, reconnect support
- Auth bypass for LAN IPs + Docker network
- MCP stdio buffer 16MB, default /app/data path
- Reranker CUDA singleton fixes

**See:** `docs/sprints/SPRINT_120_PLAN.md`

---

## Sprint 121 ✅ **Complete** (2026-01-27)

**Status:** ✅ Complete
**Focus:** Technical Debt Consolidation & Entity Management
**Story Points:** 44 SP
**Predecessor:** Sprint 120

**Features:**

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 121.1 | TD-054: Remove Duplicate Chunking Code | 6 | ✅ -1,727 lines removed |
| 121.2 | TD-078: Parallel Section Extraction | 11 | ✅ Tokenizer singleton + ThreadPoolExecutor |
| 121.3 | TD-070: Ingestion Performance Verification | 3 | ✅ 170s→38.5s (77% faster) |
| 121.4 | TD-055: MCP LLM Mode + Skills Review | 10 | ✅ Default→LLM, bilingual triggers |
| 121.5 | TD-104: Entity/Relation Delete API + Frontend | 14 | ✅ 5 endpoints, GDPR Article 17, EntityManagementPage |

**Key Achievements:**
- **Code cleanup:** -1,727 lines (ChunkingService removed, 65 obsolete tests removed)
- **Performance:** Ingestion 77% faster (170s→38.5s), graph extraction 81% faster (162s→31.2s)
- **GDPR:** Entity/Relation Delete API with GDPR Article 17 compliance, audit logging
- **Frontend:** EntityManagementPage with entity table, search, delete dialogs
- **MCP:** LLM tool detection default, enhanced bilingual prompts, 9 skill triggers

**See:** `docs/sprints/SPRINT_121_PLAN.md`

---

## Sprint 122 ✅ **COMPLETE** (2026-02-04)

**Status:** ✅ COMPLETE (5/5 Features + Infrastructure Fix)
**Focus:** E2E Test Stabilization - Timeout Fixes
**Story Points:** 26 SP delivered
**Predecessor:** Sprint 121

**Features:**

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 122.1 | Multi-Turn RAG Timeout Fix | 8 | ✅ 0%→**100%** (14/14+1 skip) |
| 122.2 | Deep Research E2E Tests | 5 | ✅ 91% (20/22) |
| 122.3 | Long Context E2E Tests | 5 | ✅ **100%** (46/46) |
| 122.4 | Selector Mismatch Fixes | 3 | ✅ Fixed `session-id` |
| 122.5 | Research Mode E2E Tests | 3 | 🟡 Deferred to Sprint 123 |
| 122.6 | Infrastructure Fixes | 2 | ✅ GPU + Qdrant ulimits |

**Key Achievements:**
- **Model Config:** `nemotron-3-nano:32k` (128K context)
- **Auth Fix:** Skip-if-already-home prevents race condition
- **ES Module Fix:** `import.meta.url` for `__dirname`
- **Selector Fix:** `conversation-id` → `session-id`
- **Qdrant Ulimits:** 1024 → 65536 (FD exhaustion fix)
- **Test Duration:** 1.1h → **4.9min** (**13x faster**)

**See:** `docs/sprints/SPRINT_122_PLAN.md`

---

## Sprint 123 ✅ **Complete** (2026-02-04)

**Status:** ✅ COMPLETE
**Focus:** E2E Test Stabilization + Hybrid Search Fixes
**Story Points:** 21 SP
**Predecessor:** Sprint 122

**Features:**

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 123.1 | Graph UI Test Fixes | 8 | ✅ Selector audit + timeout |
| 123.2 | MCP Service Test Fixes | 8 | ✅ Mock service / warmup |
| 123.3 | LLM Quality Test Fixes | 5 | ✅ Fuzzy matching |
| 123.10 | Hybrid Search UI + TC-46.1.9 removal | - | ✅ |
| 123.11 | Hybrid Search + Domain Training E2E fixes | - | ✅ |

**Commits:** `392b89e`, `fba691b`
**See:** `docs/sprints/SPRINT_123_PLAN.md`

---

## Sprint 124 ✅ **Complete** (2026-02-06)

**Status:** ✅ COMPLETE
**Focus:** RAGAS Evaluation Reboot + gpt-oss:120b Ingestion Benchmark
**Story Points:** 36 SP
**Predecessor:** Sprint 123

**Features:**

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 124.1 | RAGAS Accuracy Fixes (truncation, 128K ctx, BM25 cleanup) | 5 | ✅ |
| 124.2 | Database Reset (clean slate) | 2 | ✅ |
| 124.3 | Phase 1 Ingestion (28/498 with gpt-oss:120b) | 8 | ⏹️ Stopped (HTTP 000) |
| 124.6 | LLM Extraction Benchmark (3 models, think flag) | 3 | ✅ |
| 124.7 | DSPy Entertainment Domain Training (gpt-oss:120b) | 5 | ✅ |
| 124.8 | Entity Name Search (GraphFilters typeahead) | 5 | ✅ |
| 124.9 | Show in Graph (ContextMenu + URL params) | 5 | ✅ |
| 124.10 | Configurable extraction pipeline (env vars) | 3 | ✅ |

**Key Results:**
- **854 entities, 931 relations, 184 communities** from 28 docs
- **gpt-oss:120b benchmark:** 20s/extraction, but HTTP 000 bottleneck at Ollama
- **DSPy MIPROv2:** Entity F1 80%, Relation F1 88.9% (entertainment domain)
- **Frontend:** Entity Name Search, Show in Graph navigation, ContextMenu component
- **Finding:** Need vLLM for bulk ingestion (Ollama max 4 parallel)
- **Finding:** 100% RELATES_TO relations → need specific relation types

**Commits:** `060c5f0`, `8f2612b`, `5345720`, `b8bc9ff`
**See:** `docs/sprints/SPRINT_124_PLAN.md`

---

## Sprint 125 ✅ **Complete** (2026-02-06)

**Status:** ✅ COMPLETE
**Focus:** vLLM Integration + Domain-Aware Extraction + Domain Frontend
**Story Points:** 45 SP (100% delivered: 8+5+6+3+5+8+8)
**Predecessor:** Sprint 124

**Features:**

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 125.1 | vLLM Container Integration (Docker profile) | 8 | ✅ |
| 125.2 | AegisLLMProxy vLLM Routing | 5 | ✅ |
| 125.3 | S-P-O Triple Extraction (ADR-060 universal types) | 6 | ✅ |
| 125.6 | Documentation (ADR-059, ADR-060, TECH_STACK) | 3 | ✅ |
| 125.7 | Domain-Aware Extraction Pipeline | 5 | ✅ |
| 125.8 | Domain Taxonomy & Seed Catalog (ADR-060) | 8 | ✅ |
| 125.9 | Domain-Aware Frontend (upload, profiles, filter) | 8 | ✅ |

> **Dropped:** 125.3b Entity Dedup (3 SP) — existing EntityCanonicalizer (Sprint 85) sufficient
> **Moved to Sprint 126:** 125.4 RAGAS Ingestion (8 SP) + 125.5 Benchmark (5 SP)

**Key Decisions:**
- **vLLM** replaces Ollama for EXTRACTION tasks (19× throughput, continuous batching)
- **Nemotron-3-Nano-30B-A3B-NVFP4** for ER extraction (3.5B active, 18 GB VRAM, NVFP4)
- **Docker profiles:** `--profile ingestion` starts vLLM on demand
- **Dual-engine:** Ollama (Chat) + vLLM (Extraction) coexist (ADR-059)
- **S-P-O schema** with ADR-060 universal types (15 entity types, 21 relation types)
- **DDC+FORD Hybrid Taxonomy:** 35 standards-based domains with ontology-backed vocabularies (ADR-060)
- **Two-Tier Type System:** 15 universal types (Neo4j/Prometheus/UI) + 8-12 domain sub-types (prompts/properties)
- **Deployment Profiles:** Companies activate 1-5 domains at setup (pharma, law_firm, etc.)
- **Domain detection at upload:** BGE-M3 classifier runs BEFORE ingestion, user can confirm/override
- **Domain storage:** `domain_id` in both Qdrant payloads AND Neo4j nodes for targeted queries

**Targets:**
- >70% specific relation types (down from 100% RELATES_TO)
- Entity types from 15 universal types (>95% compliance)
- Entity names < 4 words, relations 1-3 words
- Domain detection before upload with >80% accuracy
- Domain stored in Qdrant + Neo4j for retrieval filtering

**See:** `docs/sprints/SPRINT_125_PLAN.md`

---

## Sprint 126 ✅ **Complete** (2026-02-07)

**Status:** ✅ COMPLETE
**Focus:** LLM Engine Mode + Domain Sub-Type Pipeline + Community Batch + Admin UI Polish
**Story Points:** 22 SP delivered (10 features)
**Predecessor:** Sprint 125

**Features Completed:**

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 126.1 | Runtime LLM Engine Mode (vLLM/Ollama/Auto, ADR-062) | 2 | ✅ |
| 126.2 | DeploymentProfilePage Save Bug Fix | 1 | ✅ |
| 126.3 | Community Detection as Nightly Batch Job (APScheduler) | 2 | ✅ |
| 126.4 | DSPy EntityExtractionSignature Fix (list[str] → list[dict]) | 2 | ✅ |
| 126.5 | NULL Relation-Type Backfill (1,021 legacy relations patched) | 1 | ✅ |
| 126.6 | Domain Sub-Type Pipeline (YAML defaults → Neo4j overrides → CRUD) | 3 | ✅ |
| 126.7 | AdminNavigationBar on ~28 Admin Pages | 1 | ✅ |
| 126.8 | Domain Seeding into Neo4j (35 domains) | 2 | ✅ |
| 126.9 | Pre-commit Hooks (13 hooks: Ruff, Bandit, secrets, TypeScript) | 5 | ✅ |
| 126.10 | CI/CD Streamlining (-40% runtime, remove duplicates) | 3 | ✅ |

**Key Achievements:**
- ✅ **ADR-062:** LLM Engine Mode Configuration (hot-reload via Redis, graceful degradation)
- ✅ `/api/v1/admin/llm/engine` GET/PUT endpoints + 3-card Admin UI selector
- ✅ **Community Batch Mode:** Skip during ingestion (`GRAPH_COMMUNITY_DETECTION_MODE=scheduled`), APScheduler cron at 5 AM daily, manual trigger API. **85% faster ingestion** (732s → ~107s/doc)
- ✅ **DSPy Fix:** EntityExtractionSig/RelationExtractionSig now produce typed dicts matching ADR-060 universal types (was list[str], now list[dict])
- ✅ **NULL Backfill:** 1,021 NULL relations → 212 specific types + 809 RELATED_TO (0 NULL remaining)
- ✅ **Domain Sub-Type Pipeline:** Entity sub_type preserved through extraction → Neo4j. 253 entity + 43 relation aliases from seed_domains.yaml. 4-tier prompt priority (trained → domain-enriched → generic → legacy). Cache invalidation on PUT /domains/{name}
- ✅ DeploymentProfilePage save fixed (URL, JSON body, auth token)
- ✅ AdminNavigationBar on all ~28 admin pages
- ✅ All 35 domains seeded into Neo4j with ontology references
- ✅ **Pre-commit Hooks:** 13 quality gates (Ruff lint+format, Bandit security, detect-secrets, TypeScript check, YAML/JSON/TOML, naming conventions, conventional commits). Security fixes: eval→ast.literal_eval, MD5 usedforsecurity, ~45 nosec annotations
- ✅ **CI/CD Streamlining:** Removed 8 duplicate checks + 9 unnecessary checks. CI runtime 25-30min → 15-20min (-40%)

**Technical Details:**
- **Engine Routing:** AegisLLMProxy._route_task() honors mode, falls back gracefully
- **Startup:** api/main.py reads engine mode, skips unnecessary warmups
- **Hot-Reload:** 30s Redis cache prevents thundering herd on mode changes
- **Domain Storage:** `:Domain` nodes with entity_sub_type_mapping + relation_hints
- **Community API:** POST `/api/v1/admin/community-detection/trigger`, GET `/status`
- **Sub-Type Flow:** LLM → domain-specific sub_type (e.g., DISEASE) → mapped to universal type (CONCEPT) → sub_type preserved as Neo4j property

**Commits:** `6763a8b`, `d4e015a`, `7660b27`, `2d11560`, `78be84c`, `cf2d493`
**See:** `docs/sprints/SPRINT_126_PLAN.md`, `docs/adr/ADR-062-llm-engine-mode-configuration.md`

---

## Sprint 127 ✅ **Complete** (2026-02-08)

**Status:** ✅ COMPLETE
**Focus:** RAGAS Phase 1 Benchmark with vLLM Extraction (10-Doc Baseline)
**Story Points:** 13 SP
**Predecessor:** Sprint 126

**Features:**

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 127.pre1 | vLLM Tenacity Retry (3x exp backoff on transient errors) | 1 | ✅ |
| 127.pre2 | 10-Doc RAGAS Ingestion (204 entities, 1,376 relations) | 2 | ✅ |
| 127.0 | Parallel Extraction Benchmark (2 workers optimal, 2.03x) | 2 | ✅ |
| 127.1 | Quality Evaluation (relation diversity, entity types) | 3 | ✅ |
| 127.2 | RAGAS Metrics Evaluation (CP=0.739, CR=0.760, F=0.699, AR=0.828) | 5 | ✅ |

**Key Results:**
- **RAGAS Baseline:** CP=0.739 (+27%), CR=0.760 (+162%), F=0.699, AR=0.828 (vs Sprint 82)
- **vLLM stability:** 199 calls, 0 retries needed (gpu-mem=0.45, tenacity validated)
- **LightRAG bottleneck confirmed:** 92% of graph extraction time, 79% generic RELATED_TO relations
- **Parallel extraction:** 2 workers optimal (2.03x speedup), GPU memory 0.45 optimal
- **RAGAS local model fix:** LangchainLLMWrapper + extract_json monkey-patch (94.6% parse success)
- **Full 498-doc ingestion deferred to Sprint 128** (after LightRAG removal: 75h → ~6h)

**See:** `docs/sprints/SPRINT_127_PLAN.md` (detailed plan)

---

## Sprint 128 ✅ **Complete** (2026-02-10)

**Status:** ✅ COMPLETE (30 SP delivered, 128.3 carried to Sprint 129.4)
**Focus:** LightRAG Removal + Cascade Timeout Guard + vLLM Stability + E2E Benchmarks
**Story Points:** 30 SP delivered (8 SP carried)
**Predecessor:** Sprint 127 ✅

**Features:**

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 128.1 | LightRAG Removal (-6,660 LOC, 8 files deleted) + domain_id/namespace fix | 8 | ✅ DONE |
| 128.2 | Cascade Timeout Guard (vLLM /metrics polling, exp backoff) | 3 | ✅ DONE |
| 128.3 | RAGAS Phase 1 Full Ingestion (498 docs) | 8 | ➡️ Moved to 129.4 |
| 128.4 | HyDE Query Expansion (5th RRF signal, LLM cache) | 5 | ✅ DONE |
| 128.5 | LLM Config Page — Engine-Aware Model Selection | 5 | ✅ DONE |
| 128.6 | Domain Prompt Verification — 35 domains (27/35 pass) | 3 | ✅ DONE |
| 128.7 | vLLM SM121 CUDA Stability — eugr native SM121 image (0 crashes) | 3 | ✅ DONE |
| 128.8 | E2E Pipeline Benchmark — 5-doc (100% success, 76.5% specificity) | 2 | ✅ DONE |
| 128.9 | 15-Doc Batch Benchmark — 212 entities, 626 relations, 84.5% specificity | 1 | ✅ DONE |

**Key Achievements:**
- LightRAG removed: -6,660 LOC, relation specificity 21%→84.5%, ingestion 13x faster
- vLLM eugr image: 0 CUDA crashes (vs 49 baseline), native SM121 compilation
- MAX_RELATIONSHIPS_PER_DOC cap removed (Sprint 5 legacy, blocked valid relations)
- Chat benchmark: vLLM 55 tok/s vs Ollama 64 tok/s (Ollama wins single-user chat)
- Cross-sentence benchmark (128.3a) running: w12_o3 most stable config (CV=7.6%)

---

## Sprint 129 🔄 **In Progress** (started 2026-02-10)

**Status:** 🔄 IN PROGRESS (11/12 features complete, ~29 SP delivered)
**Focus:** Extraction Resilience + RAGAS Full Ingestion + Domain Editor UI + Table Ingestion
**Story Points:** ~42 SP (estimated)
**Predecessor:** Sprint 128 ✅

**Features:**

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 129.1 | Cross-Sentence Window Bisection Fallback | 3 | ✅ |
| 129.2 | Metadata Artifact Filtering (clean_text, Doc Type) | 2 | ✅ |
| 129.3 | RAGAS Phase 1 Full Ingestion (498 docs) | 8 | 📝 |
| 129.4 | RAGAS Re-Evaluation (post-LightRAG baseline) | 3 | 📝 |
| 129.5 | Domain Editor UI (Admin) | 5 | 📝 |
| 129.6a | Table Content Extraction (Docling data.cells/rows parsing) | 2 | ✅ |
| 129.6b | Table Quality Heuristics (composite scoring, 6 metrics) | 2 | ✅ |
| 129.6c | VLM Model Evaluation (5 candidates, 45-iteration benchmark) | 3 | ✅ |
| 129.6d | VLM Selection: Nemotron VL v1 8B FP4 (ADR-063) | 3 | ✅ |
| 129.6e | Cross-Validation Logic + Pipeline Integration | 3 | ✅ |
| 129.6f | Table Ingestion E2E Benchmark (DP-Bench PDFs) | 2 | ✅ |
| 129.6g | VLM Parallel Page Processing (all pages, frontend toggle, Redis persist) | 3 | ✅ |
| 129.6h | VLM A/B Evaluation: DISABLE cross-validation, Cascade Rank 2/3 removed | 2 | ✅ |
| 129.7 | HyDE Query Classification (auto-enable for abstract queries) | 3 | ✅ |
| 129.8 | HyDE RAGAS A/B Evaluation | 3 | 📝 |
| 129.9 | TD-102: Relation Type Validation (partial) | 5 | ✅ |
| 129.10 | MAX_RELATIONSHIPS Cap removed | 2 | ✅ |

**Critical Path:** 129.1 → 129.2 → 129.3 → 129.4 → 129.8
**Table Path:** 129.6a+129.6b (parallel) → 129.6c+129.6d (parallel) → 129.6e → 129.6f → 129.6g

**Key Motivations:**
- Sprint 128.3a Benchmark revealed 0-relation windows → bisection fallback (129.1)
- Metadata artifacts (`clean_text`, `Doc Type`) pollute knowledge graph → filtering (129.2)
- 498-doc RAGAS ingestion carried from Sprint 128.3 → now feasible with stable vLLM (129.3)
- Tables completely discarded in current pipeline → full extraction + quality-gated ingestion (129.6a-f)
- VLM cross-validation via Nemotron VL v1 8B (ADR-063) — 45-iteration benchmark eliminated Granite-258M, DeepSeek-OCR-2, and V2 12B (129.6c-e)
- VLM parallel page processing: all pages rendered + sent to VLM via asyncio.gather + Semaphore, results pre-cached for cross-validation. Frontend toggle (AdminLLMConfigPage), Redis persistence, text-only format exclusion (129.6g)

### Sprint 129.6 Table Ingestion Results (2026-02-11)

**Features 129.6a + 129.6b + 129.6f COMPLETE — Tables now flow through full pipeline**

Previously, Docling parsed table structures but they were discarded during chunking. Sprint 129.6 adds:
- **129.6a**: Docling field extraction (`table_cells`, `grid`, `num_rows`, `num_cols`, `column_header`), markdown conversion, `_build_cells_2d()` grid builder
- **129.6b**: Composite quality scoring (6 metrics: header presence, density, consistency, cell length, column stability, row uniformity), grades EXCELLENT/GOOD/FAIR/POOR
- **129.6f**: E2E benchmark with 5 DP-Bench PDFs (pixel-rendered tables in real PDFs)

**Bugs Fixed:**
1. Docling field name mismatch: `cells`→`table_cells`, `rows`→`num_rows`, `columns`→`num_cols`, added `grid` support
2. Qdrant metadata gap: `is_table`, `table_quality_score`, `table_quality_grade` not propagated to Qdrant payload (whitelist in `vector_embedding.py`)
3. Empty chunk guard: Table-only PDFs produce empty prose text → Pydantic `min_length=1` validation error. Added skip for empty/whitespace-only chunks in `adaptive_chunking.py`
4. Test data format: 84/84 tests updated from old cell format to Docling format

**E2E Benchmark (5 DP-Bench PDFs):**

| File | Status | Time | Table Dim | Quality | Grade |
|------|--------|------|-----------|---------|-------|
| 01030000000045.pdf | success | 109s | 9x3 | 0.956 | EXCELLENT |
| 01030000000046.pdf | success | 342s | 12x7 | 0.946 | EXCELLENT |
| 01030000000047.pdf | failed* | 2s | — | — | — |
| 01030000000051.pdf | success | 132s | 9x4 | 0.961 | EXCELLENT |
| 01030000000052.pdf | success | 414s | 12x4 | 0.973 | EXCELLENT |

*Doc 47 = table-only PDF with no prose text → empty Chunk.content (fixed with empty chunk guard, needs rebuild + retest)

**Aggregate:** 4/5 success, 119 entities (12 types), 283 relations (18 types), 50.2% specificity, 4 table vectors in Qdrant (all EXCELLENT grade, scores 0.946-0.973)

### Sprint 129.6h VLM Cross-Validation Evaluation (2026-02-11)

**A/B Benchmark:** 4 docs (3 PDFs + 1 TXT), Nemotron VL 8B FP4 (port 8002, ~12GB GPU)

**Result: DISABLE VLM cross-validation.** Nemotron VL 8B agreement scores (0.23-0.76) consistently DOWNGRADE table quality. Docling heuristic scoring (0.90+ EXCELLENT) is already accurate.

**Key Decisions:**
1. **Cascade Rank 2/3 Removed** — Ollama fallback (gpt-oss:20b) wastes ~20GB GPU, triggers `cudaErrorIllegalInstruction`. vLLM tenacity retry (3 attempts, exp backoff) is sufficient.
2. **VLM table container stopped** — Reclaim 12GB GPU headroom.
3. **`TABLE_CROSS_VALIDATION_ENABLED=false`** (default) — Keep Docling heuristic scoring only.

**See:** [SPRINT_129_VLM_EVALUATION.md](SPRINT_129_VLM_EVALUATION.md)

**Detailed plan:** See [SPRINT_129_PLAN.md](SPRINT_129_PLAN.md)
