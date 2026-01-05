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

## Sprint 76+: Future Sprints (Planned)

### Sprint 76 Candidates (Based on Sprint 75 Results)
1. **RAG Quality Improvements** (Priority based on RAGAS analysis)
   - Chunking optimization
   - Embedding tuning
   - Retrieval parameter tuning
   - Reranking improvements
   - Context optimization
   - Prompt engineering

2. **Other Candidates:**
   - **mem0 Frontend UI** (8 SP) - User preferences page
   - **Agent Memory Architecture** (13 SP) - ADR-047 completion
   - **Retrieval Direct Access** (5 SP) - UI for `/retrieval/*` endpoints
   - **Graph Community Advanced Features** (8 SP) - Comparison visualizations

### Long-Term Roadmap (Sprint 77+)
- **Multi-Modal RAG:** Image + Video + Audio processing
- **Federated Search:** Cross-domain knowledge aggregation
- **Cloud LLM Integration:** Azure OpenAI, Anthropic, Cohere
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
| **75** | **34** | **3** | 🎯 | **RAGAS Evaluation & RAG Quality Optimization** |

**Cumulative Story Points (Sprints 1-75):** ~2,539 SP
**Average Velocity (Sprints 61-75):** ~44 SP per sprint
**E2E Test Improvement:** 337/594 (57% - Sprint 66) → 620/620 (100% - Sprint 72)

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

**Last Updated:** 2026-01-04
**Current Sprint:** 75 (In Progress - RAGAS Evaluation & RAG Quality Optimization)
**Next Sprint:** 76 (TBD - Based on Sprint 75 Results)
