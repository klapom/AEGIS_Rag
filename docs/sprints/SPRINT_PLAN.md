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
| **81** | **24** | **10** | 📝 | **Query-Adaptive Routing & Entity Extraction Improvements (Planned)** |

**Cumulative Story Points (Sprints 1-81):** ~2,694 SP
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

**Last Updated:** 2026-01-08
**Current Sprint:** 80 (Planned - RAGAS P0 Critical Fixes: Faithfulness & Hybrid Fusion)
**Previous Sprints:** 77-79 (Completed - Bug Fixes, Graph Entity Expansion, RAGAS 0.4.2 Migration)
**Next Sprint:** 81 (Planned - Query-Adaptive Routing & Entity Extraction Improvements)

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
