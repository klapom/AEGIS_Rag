# Sprint-Planung: Agentisches RAG-System
## Projektname: AegisRAG (Agentic Enterprise Graph Intelligence System)

**Gesamtdauer:** 12 Sprints à 1 Woche (12 Wochen)
**Team-Setup:** 1-2 Entwickler + Claude Code Subagenten

**Note:** Sprint 8 "Critical Path E2E Testing" was strategically inserted after Sprint 7 to validate critical integration paths from Sprint 1-6 before proceeding with new features. This decision (ADR-015) increases production confidence from 75% to 95%.

---

## Sprint 1: Foundation & Infrastructure Setup
**Ziel:** Entwicklungsumgebung, Core-Infrastruktur, CI/CD Pipeline

### Deliverables
- [x] Repository-Struktur mit Monorepo-Layout
- [x] Docker Compose für lokale Entwicklung (Qdrant, Redis, Neo4j)
- [x] pyproject.toml mit Dependencies (LangGraph, LlamaIndex)
- [x] Pre-commit Hooks (Black, Ruff, MyPy)
- [x] GitHub Actions CI/CD Pipeline (Lint, Test, Build)
- [x] .env Template und Secrets Management
- [x] Logging-Framework (Structlog)

### Technical Tasks
- Repository initialisieren mit Git
- Docker Compose Services definieren
- Python 3.11+ Environment Setup
- Dependency Management (Poetry/UV)
- Basic Health-Check Endpoints

### Success Criteria
- `docker compose up` startet alle Services
- `pytest` läuft erfolgreich durch
- CI Pipeline ist grün
- Alle Entwickler können lokal arbeiten

---

## Sprint 2: Component 1 - Vector Search Foundation
**Ziel:** Qdrant-Integration, Hybrid Search, Basic Retrieval

> **🎯 WICHTIG: Feature-basierte Entwicklung**
> Ab Sprint 2 wird jeder Sprint in **einzelne Features** heruntergebrochen, um:
> - Granulare Git-Commits zu ermöglichen (1 Commit = 1 Feature)
> - Bessere Nachvollziehbarkeit und Code-Review zu gewährleisten
> - Atomic Rollbacks bei Problemen zu ermöglichen
> - Parallele Entwicklung mehrerer Features zu unterstützen

### Sprint 2 Feature-Breakdown

#### Feature 2.1: Qdrant Client Foundation ✅
**Deliverables:**
- [x] QdrantClientWrapper mit async/sync Support
- [x] Connection Pooling und Health Checks
- [x] Retry Logic mit Exponential Backoff
- [x] Collection Management (create, delete, list)

**Technical Tasks:**
- Qdrant Python Client Integration
- Connection Pool Configuration
- Health Check Endpoints
- Unit Tests für Client Operations

**Git Commits:** `feat(qdrant): implement client wrapper with connection pooling`

---

#### Feature 2.2: Document Ingestion Pipeline ✅
**Deliverables:**
- [x] DocumentIngestionPipeline mit LlamaIndex
- [x] Support für PDF, TXT, MD, DOCX
- [x] Recursive Directory Loading
- [x] Path Traversal Security (P1)

**Technical Tasks:**
- SimpleDirectoryReader Integration
- File Type Handlers
- Security Validation
- Ingestion Unit Tests

**Git Commits:** `feat(ingestion): add document loading pipeline with security`

---

#### Feature 2.3: Embedding Service ✅
**Deliverables:**
- [x] EmbeddingService mit Ollama nomic-embed-text
- [x] LRU Cache für Embeddings (OOM Protection)
- [x] Batch Processing Support
- [x] Retry Logic mit tenacity

**Technical Tasks:**
- Ollama Embedding Model Integration
- LRU Cache Implementation
- Batch Embedding Generation
- Embedding Unit Tests

**Git Commits:** `feat(embeddings): implement embedding service with LRU cache`

---

#### Feature 2.4: Text Chunking Strategy ✅
**Deliverables:**
- [x] SentenceSplitter Integration
- [x] Configurable chunk_size/chunk_overlap
- [x] Chunk Metadata Preservation
- [x] Semantic Boundary Respect

**Technical Tasks:**
- LlamaIndex SentenceSplitter Setup
- Chunking Configuration
- Metadata Tracking
- Chunking Unit Tests

**Git Commits:** `feat(chunking): add sentence-based chunking with metadata`

---

#### Feature 2.5: BM25 Search Engine ✅
**Deliverables:**
- [x] BM25Search mit rank_bm25
- [x] Tokenization Pipeline
- [x] Index Persistence (pickle)
- [x] Search with Configurable top_k

**Technical Tasks:**
- rank_bm25 Integration
- Custom Tokenizer
- Index Save/Load
- BM25 Unit Tests (62 tests)

**Git Commits:** `feat(bm25): implement BM25 search with persistence`

---

#### Feature 2.6: Hybrid Search (Vector + BM25) ✅
**Deliverables:**
- [x] HybridSearch Orchestrator
- [x] Reciprocal Rank Fusion (RRF)
- [x] Parallel Vector+BM25 Execution
- [x] Configurable Search Modes (hybrid/vector/bm25)

**Technical Tasks:**
- HybridSearch Implementation
- RRF Algorithm
- Async Parallel Execution
- Hybrid Search Unit Tests

**Git Commits:** `feat(hybrid): add hybrid search with RRF fusion`

---

#### Feature 2.7: Retrieval API Endpoints ✅
**Deliverables:**
- [x] POST /api/v1/search (hybrid search)
- [x] POST /api/v1/ingest (document ingestion)
- [x] POST /api/v1/bm25/prepare (BM25 indexing)
- [x] GET /api/v1/stats (system statistics)

**Technical Tasks:**
- FastAPI Router Setup
- Request/Response Models (Pydantic)
- OpenAPI Documentation
- API Unit Tests (27 tests)

**Git Commits:** `feat(api): add retrieval endpoints with OpenAPI docs`

---

#### Feature 2.8: Security Hardening (P0/P1/P2) ✅
**Deliverables:**
- [x] P0: Input Sanitization & Validation
- [x] P0: SQL/NoSQL Injection Prevention
- [x] P1: Error Message Sanitization
- [x] P1: Rate Limiting (slowapi)
- [x] P1: Path Traversal Protection
- [x] P2: Health Check Endpoints (/health, /ready, /live)

**Technical Tasks:**
- Pydantic Validation Schemas
- Rate Limiting Middleware
- Path Security Validation
- Error Handlers
- Security Unit Tests

**Git Commits:**
- `feat(security): add P0 input validation and injection prevention`
- `feat(security): add P1 rate limiting and error sanitization`
- `feat(security): add P2 health check endpoints`

---

### Consolidated Sprint 2 Success Criteria
- ✅ 933 Test-Dokumente erfolgreich indexiert
- ✅ Hybrid Search liefert Top-5 Results <200ms
- ✅ BM25 Index mit 933 Dokumenten erstellt
- ✅ 212 Tests passing, 3 skipped, 0 failed (98.6% coverage)
- ✅ API Documentation (OpenAPI/Swagger) verfügbar
- ✅ P0/P1/P2 Security Fixes implementiert
- ✅ Rate Limiting: 10/min (search), 5/hour (ingest)

---

## Sprint 3: Component 1 - Advanced Retrieval
**Ziel:** Reranking, Query-Transformation, Metadata-Filtering
**Status:** ✅ COMPLETE (335/338 tests passing, 99.1%)

### Deliverables
- ✅ Cross-Encoder Reranker Integration (ms-marco-MiniLM)
- ✅ Query Decomposition für komplexe Fragen (Ollama llama3.2)
- ✅ Metadata-Filter Engine (Date, Source, Tags) - 42 tests
- ✅ Retrieval Evaluation Framework (RAGAS) - 20 tests
- ✅ Adaptive Chunking basierend auf Document-Typ - 45 tests
- ✅ Security Fix: MD5 → SHA-256 migration

### Technical Tasks
- ✅ Reranker Model Loading (HuggingFace sentence-transformers)
- ✅ Query Classifier für Retrieval-Strategie (SIMPLE/COMPOUND/MULTI_HOP)
- ✅ Metadata Filter Engine with Qdrant integration
- ✅ RAGAS Metrics Integration (Context Precision/Recall/Faithfulness)
- ✅ Performance-Optimierung (Batch Processing, Lazy Loading)
- ✅ Document-type detection and adaptive chunking strategies

### Success Criteria
- ✅ Reranking verbessert Precision @3 um 15%+ (Achieved: 23% improvement)
- ✅ Query Decomposition für 90% komplexer Queries (Achieved: 90%+ classification accuracy)
- ✅ Metadata-Filter reduziert False Positives um 30% (Achieved: 33% reduction)
- ✅ RAGAS Score > 0.85 (Achieved: 0.88 for hybrid-full scenario)

### Sprint 3 Summary
**Test Coverage**: 335/338 passing (99.1%)
**Features Delivered**: 6 (including security fix)
**Documentation**: [SPRINT_3_SUMMARY.md](../../SPRINT_3_SUMMARY.md)
**Examples**: [sprint3_examples.md](../examples/sprint3_examples.md)

**Key Components**:
- `src/components/retrieval/reranker.py` - Cross-encoder reranking (18 tests)
- `src/components/retrieval/query_decomposition.py` - LLM-based query classification
- `src/components/retrieval/filters.py` - Metadata filtering engine (42 tests)
- `src/components/retrieval/chunking.py` - Adaptive chunking (45 tests)
- `src/evaluation/ragas_eval.py` - RAGAS evaluation framework (20 tests)

**Dependencies Added**:
- sentence-transformers ^3.3.1 (cross-encoder models)
- ragas ^0.2.5 (RAG evaluation)
- datasets ^3.2.0 (HuggingFace datasets)

---

## Sprint 4: LangGraph Orchestration Layer
**Ziel:** Multi-Agent Framework, State Management, Routing

### Deliverables
- [x] LangGraph Coordinator Agent
- [x] Query Router mit Intent-Classification
- [x] Vector Search Agent (Integration Component 1)
- [x] State Management (Conversation Context)
- [x] LangSmith Integration für Tracing
- [x] Error Handling & Retry Logic

### Technical Tasks
- LangGraph Graph Definition (Nodes, Edges, Conditional Routes)
- Agent Base Classes mit Tool Interface
- Query Router Model Training/Prompting
- State Persistence (Redis Backend)
- LangSmith API Integration
- Durable Execution Setup

### Success Criteria
- Coordinator routet 95%+ Queries korrekt
- State bleibt über Multi-Turn Conversations erhalten
- LangSmith zeigt alle Execution Steps
- Retry Logic handled transiente Failures

---

## Sprint 5: Component 2 - LightRAG Integration
**Ziel:** Graph-basiertes Reasoning, Knowledge Graph Construction

### Deliverables
- [x] LightRAG Installation und Setup
- [x] Neo4j Backend-Konfiguration
- [x] Entity & Relationship Extraction Pipeline
- [x] Dual-Level Retrieval (Entities + Topics)
- [x] Graph Query Agent (LangGraph Integration)
- [x] Incremental Graph Updates

### Technical Tasks
- Neo4j Docker-Service mit Persistenz
- LightRAG Config (Ollama LLM + Embedding Model, Extraction Prompts)
- Graph Construction für Test-Corpus
- Cypher Query Templates
- Graph Query Agent Implementation
- Web UI für Graph-Visualisierung

### Success Criteria
- Knowledge Graph mit 500+ Entities konstruiert
- Graph Queries liefern Results <500ms
- Dual-Level Retrieval funktional
- Incremental Updates ohne Full-Reindex

---

## Sprint 6: Component 2 - Hybrid Vector-Graph Retrieval
**Ziel:** Parallel Retrieval, Context Fusion, Multi-Hop Reasoning

### Deliverables
- [x] Parallel Execution (LangGraph Send API)
- [x] Reciprocal Rank Fusion für Vector+Graph
- [x] Multi-Hop Query Expansion
- [x] Community Detection Integration (Leiden)
- [x] Global vs. Local Search Modes
- [x] Hybrid Retrieval Evaluation

### Technical Tasks
- Async Retrieval Orchestration
- Context Fusion Algorithmus (RRF)
- Graph Traversal Optimierung
- Community Detection für Topic Clustering
- Query Mode Selection Logic
- Benchmark Suite (Vector vs. Graph vs. Hybrid)

### Success Criteria
- Parallel Retrieval spart 40%+ Latency
- Hybrid Approach zeigt 30%+ bessere Relevance
- Multi-Hop Queries funktionieren über 3+ Hops
- Community Detection identifiziert Themen-Cluster

---

## Sprint 7: Component 3 - Graphiti Memory Integration
**Ziel:** Temporal Memory, Episodic vs. Semantic, Long-Term Context

### Deliverables
- [x] Graphiti Installation mit Neo4j Backend
- [x] Bi-Temporal Datenstruktur (Valid Time + Transaction Time)
- [x] Episodic Subgraph (Raw Conversations)
- [x] Semantic Subgraph (Extracted Facts)
- [x] Memory Agent (LangGraph Integration)
- [x] Point-in-Time Query API

### Technical Tasks
- Graphiti Config und Schema Design
- Memory Ingestion Pipeline (Conversation → Graph)
- Temporal Query Interface
- Memory Retrieval Agent Implementation
- Memory Decay Strategy (Time-based + Relevance)
- Redis für Short-Term Working Memory

### Success Criteria
- Conversations werden automatisch in Episodic Memory persistiert
- Facts werden extrahiert und in Semantic Memory gespeichert
- Point-in-Time Queries rekonstruieren historischen Kontext
- Memory Retrieval <100ms

---

## Sprint 8: Critical Path E2E Testing
**Ziel:** Production-Confidence durch E2E Tests für kritische Integration Paths aus Sprint 1-6
**Status:** 📋 PLANNED (Inserted after Sprint 7)

### Context & Rationale
Sprint 6 CI failures revealed a critical gap: **432 mocked unit tests passed locally, but 2/9 CI jobs failed** (Docker Build timeout, Neo4j integration timeout). This proves mocked tests provide false confidence.

**Strategic Decision (ADR-015):** Insert Sprint 8 to validate 26 critical integration paths from Sprint 1-6 with E2E tests (NO MOCKS), focusing on highest-risk paths that could cause production failures.

**Expected Impact:**
- Production Confidence: 75% → 95% (20% increase)
- Integration bugs: 10/quarter → 2/quarter (80% reduction)
- CI debugging time: 5 hours/week → 1 hour/week (80% reduction)
- ROI: 162% annual return (260 hours saved vs. 160 hours invested)

### Deliverables
- [ ] 40 E2E integration tests covering 26 critical paths
- [ ] Real service integration (Redis, Qdrant, Neo4j, Ollama)
- [ ] CI pipeline validation (all services running)
- [ ] Test execution time <10 minutes total
- [ ] Coverage report for critical paths
- [ ] Sprint 8 completion report

### Critical Paths to Test (26 total)

#### High Risk (12 paths, ZERO current coverage)
1. **Community Detection (Neo4j + Ollama)** - Most complex integration
2. **Cross-Encoder Reranking** - External model dependency
3. **RAGAS Evaluation with Ollama** - LLM-based metrics
4. **LightRAG Entity Extraction** - Graph + LLM integration
5. **Temporal Queries (Graphiti)** - Bi-temporal model
6. **Memory Consolidation (Redis → Qdrant)** - Multi-database sync
7. **Graph Query Cache Invalidation** - Cache consistency
8. **Batch Query Executor** - Parallel execution
9. **Version Manager (10 versions)** - Temporal history
10. **PageRank Analytics** - Graph algorithm
11. **Query Templates (19 patterns)** - Query generation
12. **Community Search Filter** - Graph + vector hybrid

#### Medium Risk (8 paths, partial coverage)
13. **Hybrid Search (Vector + BM25)** - Dual retrieval
14. **Document Ingestion Pipeline** - Multi-format support
15. **Metadata Filtering** - Complex filter logic
16. **Query Decomposition** - LLM classification
17. **Graph Visualization Export** - 3 formats (D3, Cytoscape, vis.js)
18. **Dual-Level Search (Entities + Topics)** - LightRAG integration
19. **Reciprocal Rank Fusion** - Context fusion
20. **Adaptive Chunking** - Document-type detection

#### Lower Risk (6 paths, good coverage)
21. **BM25 Search** - Already 62 tests
22. **Embedding Service** - Cache + batch processing
23. **Qdrant Client Operations** - Connection pooling
24. **Neo4j Client Wrapper** - Basic CRUD
25. **Redis Memory Manager** - TTL + eviction
26. **API Endpoints** - FastAPI routes

### Test Strategy (ADR-015)

**Risk-Based Approach:**
- Focus on High Risk paths first (60% of effort)
- Add targeted tests for Medium Risk paths (30% of effort)
- Validate existing coverage for Lower Risk (10% of effort)

**NO MOCKS Policy (ADR-014):**
- All tests use real services (Redis, Qdrant, Neo4j, Ollama)
- Session-scoped fixtures for service reuse
- Cleanup between tests to ensure isolation
- Acceptable trade-off: ~10 min execution time for 95% production confidence

**Test Distribution:**
- High Risk: 24 tests (2 tests per critical path)
- Medium Risk: 12 tests (1.5 tests per path)
- Lower Risk: 4 tests (validation only)
- **Total: 40 E2E tests**

### Technical Tasks
- [ ] Implement 24 E2E tests for High Risk paths
- [ ] Implement 12 E2E tests for Medium Risk paths
- [ ] Implement 4 validation tests for Lower Risk paths
- [ ] Update CI pipeline to ensure all services running
- [ ] Add test execution time monitoring
- [ ] Create coverage report for critical paths
- [ ] Document remaining gaps (if any)

### Success Criteria
- ✅ 40 E2E tests implemented and passing
- ✅ All 12 High Risk paths have E2E coverage
- ✅ Test execution time <10 minutes
- ✅ CI pipeline validates service availability before tests
- ✅ Coverage report shows 95%+ critical path coverage
- ✅ No mocked tests for critical integration paths
- ✅ Sprint 8 completion report created

### Story Points: 40 SP
**Breakdown:**
- High Risk tests (24 tests): 24 SP (1 SP per test avg)
- Medium Risk tests (12 tests): 10 SP (0.8 SP per test)
- Lower Risk tests (4 tests): 2 SP (0.5 SP per test)
- CI pipeline updates: 2 SP
- Documentation: 2 SP

**Timeline:**
- Sequential: 4 weeks (1 developer, 10 SP/week)
- Parallel: 1 week (4 subagents, 10 SP each)

**References:**
- [SPRINT_8_PLAN.md](../../SPRINT_8_PLAN.md) - Detailed plan with critical path analysis
- [ADR-015](../adr/ADR-015-critical-path-testing.md) - Critical Path Testing Strategy
- [ADR-014](../adr/ADR-014-e2e-integration-testing.md) - E2E Integration Testing Strategy

---

## Sprint 14: Backend Performance & Testing
**Ziel:** Comprehensive Testing Infrastructure & Monitoring for Sprint 13 Pipeline
**Status:** ✅ COMPLETE (2025-10-24 → 2025-10-27)

### Context
Sprint 13 delivered the Three-Phase Extraction Pipeline (SpaCy + Semantic Dedup + Gemma 3 4B) with 10x performance improvement (>300s → <30s). Sprint 14 focuses on testing infrastructure, monitoring, and production readiness.

### Deliverables
- ✅ **Feature 14.2**: Extraction Pipeline Factory (configuration-driven selection)
- ✅ **Feature 14.3**: Production Benchmarking Suite (memory profiling, performance tracking)
- ✅ **Feature 14.5**: Retry Logic & Error Handling (tenacity-based resilience)
- ✅ **Feature 14.6**: Prometheus Metrics & Monitoring (comprehensive observability)

### Test Coverage
- ✅ **Unit Tests**: 112/112 passing (9.12s execution)
  - test_extraction_factory.py: 25 tests
  - test_gemma_retry_logic.py: 18 tests (fixed 5 flaky tests)
  - test_benchmark_production_pipeline.py: 15 tests
  - test_metrics.py: 54 tests

- ✅ **Integration Tests**: 20/20 passing (5m 37s with real Docker services)
  - test_extraction_factory_integration.py: 9 tests
  - test_gemma_retry_integration.py: 11 tests

- ✅ **Stress Tests**: 5 tests created (not yet executed)
  - test_sprint14_stress_performance.py: 100-doc batch, memory leak detection, connection pool

### Key Decisions
- ✅ **ADR-019**: Use integration tests with real services as E2E tests (eliminates redundant test layer)

### Technical Tasks
- ✅ ExtractionPipelineFactory with create() method
- ✅ BenchmarkRunner with tracemalloc memory profiling
- ✅ Retry logic using tenacity (exponential backoff)
- ✅ 12 Prometheus metrics for extraction pipeline
- ✅ Fixed 5 flaky retry logic tests
- ✅ Comprehensive test suite (132 tests total)

### Success Criteria
- ✅ Factory creates working Three-Phase pipeline from config
- ✅ Benchmarking tracks memory usage and performance
- ✅ Retry logic handles transient failures gracefully
- ✅ Prometheus metrics provide comprehensive observability
- ✅ 100% test success rate (132/132 passing)
- ✅ Integration tests use real Docker services (Ollama, Neo4j, Redis, Qdrant)

### Story Points: 45 SP (Delivered) / 40 SP (Planned)
**Velocity:** 11.25 SP/day (12.5% overdelivery)

### References
- [SPRINT_14_COMPLETION_REPORT.md](../sprints/SPRINT_14_COMPLETION_REPORT.md) - Detailed completion report
- [ADR-019](../adr/ADR-019-integration-tests-as-e2e.md) - Integration Tests as E2E Tests
- Branch: `sprint-14-backend-performance`

---

## Sprint 15: Frontend Interface with Perplexity-Inspired UI
**Ziel:** Production-ready web interface with SSE streaming and RAG-optimized UX
**Status:** ✅ COMPLETE (2025-10-27 → 2025-10-28)

### Context
After Sprint 14's backend completion, AegisRAG needs a user-facing frontend. User decision: "Warum das Rad neu erfinden. Lass uns an der Oberfläche von Perplexity orientieren" → Adopt proven Perplexity.ai design patterns for RAG-first UX.

**Key Design Decisions:**
- ✅ Perplexity-inspired minimalist UI (sidebar + main content)
- ✅ Server-Sent Events (SSE) for streaming (not WebSocket)
- ✅ React 18 + Vite + TypeScript + Tailwind CSS
- ✅ Multi-mode search selector (Hybrid, Vector, Graph, Memory)
- ✅ Source cards with LightRAG provenance
- ✅ German localization

### Deliverables
- [x] **Feature 15.1**: React + Vite setup + SSE backend endpoint (13 SP, 2 days)
- [x] **Feature 15.2**: Perplexity-style layout (sidebar + header + main) (8 SP, 1 day)
- [x] **Feature 15.3**: Search input with mode selector (10 SP, 1.5 days)
- [x] **Feature 15.4**: Streaming answer display with source cards (21 SP, 3 days)
- [x] **Feature 15.5**: Conversation history sidebar (13 SP, 2 days)
- [x] **Feature 15.6**: System health dashboard (8 SP, 1 day)

### Technical Tasks

**Backend Changes:**
- [ ] New SSE endpoint: `POST /api/v1/chat/stream` (StreamingResponse)
- [ ] CoordinatorAgent streaming method: `process_query_stream()`
- [ ] Sessions API: `GET /api/v1/chat/sessions` (list all sessions)
- [ ] Update CORS for frontend (http://localhost:5173)

**Frontend Stack:**
- [ ] React 18.2 + Vite 5 + TypeScript 5
- [ ] Tailwind CSS 3 (Perplexity design system)
- [ ] Zustand (state management)
- [ ] React Router 6 (routing)
- [ ] Vitest + React Testing Library

**Key Components:**
```
frontend/src/
├── components/
│   ├── layout/         # AppLayout, Sidebar, Header
│   ├── search/         # SearchInput, ModeSelector
│   ├── results/        # StreamingAnswer, SourceCard
│   ├── history/        # SessionList, SessionItem
│   └── health/         # HealthDashboard, ServiceStatus
├── hooks/
│   ├── useStreamChat.ts    # SSE client hook
│   ├── useSessions.ts      # Session management
│   └── useHealthCheck.ts   # Health monitoring
├── stores/
│   ├── chatStore.ts        # Zustand chat state
│   └── sessionStore.ts     # Zustand session state
├── api/
│   ├── chat.ts             # Chat API client
│   ├── sessions.ts         # Session API client
│   └── health.ts           # Health API client
└── pages/
    ├── HomePage.tsx        # Landing page with search
    ├── ResultsPage.tsx     # Search results with streaming
    └── HealthPage.tsx      # System health dashboard
```

**Design System (Perplexity-inspired):**
- **Primary Color**: #20808D (Teal)
- **Font**: Inter sans-serif
- **Border Radius**: 12-24px (rounded)
- **Spacing**: 24-32px (generous padding)
- **Responsive**: Mobile-first approach

### Success Criteria
- [x] User can search with 4 modes (Hybrid, Vector, Graph, Memory)
- [x] Streaming answer displays token-by-token (<100ms to first token)
- [x] Source cards show LightRAG provenance (chunk ID, confidence)
- [x] Session history persists across browser refreshes
- [x] Health dashboard shows Qdrant, Neo4j, Redis, Ollama status
- [x] Responsive design works on mobile + desktop
- [x] German localization for all UI strings
- [ ] E2E tests with Playwright (5+ user flows) → TD-35 (Sprint 16)

### Story Points: 73 SP
**Breakdown:**
- Feature 15.1: React + SSE Backend (13 SP)
- Feature 15.2: Layout (8 SP)
- Feature 15.3: Search Input (10 SP)
- Feature 15.4: Streaming Answer (21 SP)
- Feature 15.5: History Sidebar (13 SP)
- Feature 15.6: Health Dashboard (8 SP)

**Timeline:**
- Sequential: 7-10 days (1 developer, ~8-10 SP/day)
- Parallel: 3-4 days (3 subagents: Backend, Frontend, Testing)

### Architecture Decisions
- [ADR-020](../adr/ADR-020-sse-streaming-for-chat.md) - SSE Streaming for Chat
- [ADR-021](../adr/ADR-021-perplexity-inspired-ui-design.md) - Perplexity-Inspired UI Design

### References
- [SPRINT_15_PLAN.md](../sprints/SPRINT_15_PLAN.md) - Detailed implementation plan (1240 lines)
- [SPRINT_15_COMPLETION_REPORT.md](../sprints/SPRINT_15_COMPLETION_REPORT.md) - Full completion report
- [ADR-020](../decisions/ADR-020-sse-streaming.md) - SSE vs WebSocket decision
- [ADR-021](../decisions/ADR-021-perplexity-ui-design.md) - Perplexity UI adoption rationale
- Branch: `sprint-15-frontend` (merged to main: 2025-10-28)
- Release: v0.15.0

---

## Sprint 16: Unified Ingestion Architecture & Advanced Features
**Ziel:** Architectural unification, PPTX support, unified re-indexing, and BGE-M3 evaluation
**Status:** 📋 PLANNED (2025-10-28)

### Context
After Sprint 15's frontend completion and comprehensive architecture review, critical duplications and synchronization issues were identified:

**Architectural Issues Found:**
- ❌ **Chunking duplication**: Logic scattered across 3 components (Qdrant, BM25, LightRAG)
- ❌ **No unified re-indexing**: Qdrant, BM25, Neo4j can become out-of-sync
- ❌ **Two embedding models**: nomic-embed-text (768-dim) + BGE-M3 (1024-dim) incompatible
- ❌ **No cross-layer similarity**: Can't compare Qdrant (Layer 2) with Graphiti (Layer 3)

**New Requirements:**
- ✅ Unified chunking service (single source of truth)
- ✅ Atomic re-indexing across all 3 indexes
- ✅ BGE-M3 evaluation and standardization strategy
- ✅ PPTX format support (python-pptx backend)
- ✅ Graph extraction using unified chunks

### Deliverables
- [ ] **Feature 16.1**: Unified Chunking Service (6 SP) 🆕 **(revised from 8 SP)**
- [ ] **Feature 16.2**: Unified Re-Indexing Pipeline (13 SP) 🆕
- [ ] **Feature 16.3**: PPTX Document Support (8 SP)
- [ ] **Feature 16.4**: BGE-M3 Evaluation & Standardization (8 SP) 🆕
- [ ] **Feature 16.5**: Graph Extraction with Unified Chunks (13 SP)
- [ ] **Feature 16.6**: Frontend E2E Tests with Playwright (13 SP)
- [ ] **Feature 16.7**: Graphiti Performance Evaluation & Optimization (8 SP) 🆕

### Technical Tasks

**Feature 16.1: Unified Chunking Service** 🆕
**Problem:** Chunking logic scattered across Qdrant, BM25, and LightRAG components
**Solution:** Create centralized `ChunkingService` as single source of truth

Tasks:
- [ ] Create `src/core/chunking_service.py` with unified chunking logic
- [ ] Support multiple strategies: adaptive, sentence-based, fixed-size
- [ ] Configuration via `ChunkingConfig` Pydantic model
- [ ] Migrate Qdrant ingestion to use `ChunkingService`
- [ ] Migrate BM25 indexing to use same chunks
- [ ] Migrate LightRAG extraction to use same chunks
- [ ] Add comprehensive tests (10+ test cases)
- [ ] Document chunk format and metadata

**Deliverables:**
```python
class ChunkingService:
    async def chunk_document(
        text: str,
        strategy: ChunkStrategy = "adaptive",
        chunk_size: int = 512,
        overlap: int = 128
    ) -> List[Chunk]:
        """Unified chunking for all consumers"""
```

**Benefits:**
- Guaranteed consistency across all 3 indexes
- Single place to change chunking strategy
- Easier testing and validation

---

**Feature 16.2: Unified Re-Indexing Pipeline** 🆕
**Problem:** No atomic re-indexing; Qdrant, BM25, Neo4j can become out-of-sync
**Solution:** Create unified re-indexing endpoint with transactional semantics

Tasks:
- [ ] Create `POST /api/v1/admin/reindex` endpoint
- [ ] Atomic deletion: Qdrant + BM25 + Neo4j (all-or-nothing)
- [ ] Progress tracking via SSE (same as chat streaming)
- [ ] Safety checks: confirmation parameter, dry-run mode
- [ ] Re-index all documents using unified chunking service
- [ ] Validate index consistency after completion
- [ ] Add admin authentication/authorization
- [ ] Comprehensive error handling and rollback

**Deliverables:**
```python
@router.post("/api/v1/admin/reindex")
async def reindex_all_documents(
    dry_run: bool = False,
    confirm: bool = False
) -> StreamingResponse:
    """Atomically rebuild all indexes"""
```

**Benefits:**
- Guaranteed synchronization across indexes
- Single operation for re-indexing
- Progress visibility via UI

---

**Feature 16.3: PPTX Document Support**
**Problem:** PowerPoint presentations not supported
**Solution:** Add python-pptx backend via LlamaIndex

Tasks:
- [ ] Add `python-pptx` dependency (pyproject.toml)
- [ ] Update `required_exts` list to include `.pptx`
- [ ] Test PPTX text extraction with LlamaIndex
- [ ] Handle embedded images/tables in slides
- [ ] Add PPTX test fixtures (OMNITRACKER presentations)
- [ ] Update documentation with supported formats

**Benefits:**
- Support for OMNITRACKER ITSM training materials (many PPTX files)

---

**Feature 16.4: BGE-M3 Evaluation & Standardization** 🆕
**Problem:** Two embedding models (nomic + BGE-M3) create incompatible vector spaces
**Solution:** Benchmark and decide on standardization strategy

Tasks:
- [ ] Benchmark: nomic-embed-text vs. BGE-M3 on Qdrant
- [ ] Metrics: Retrieval quality (NDCG@10), latency, GPU memory
- [ ] Test cross-layer similarity (768-dim vs. 1024-dim)
- [ ] Decision: Standardize on BGE-M3 OR keep separate with factory pattern
- [ ] If standardize: Re-embed all Qdrant documents (933+ docs)
- [ ] If factory: Create `EmbeddingServiceFactory` with layer selection
- [ ] Document decision in ADR-024

**Options:**
- **Option A:** Keep separate (low effort, no cross-layer similarity)
- **Option B:** Standardize on BGE-M3 (high effort, full compatibility)
- **Option C:** Factory pattern with dimension projection (medium effort)

**Benefits:**
- Clear strategy for embedding model usage
- Potential cross-layer semantic search
- Performance optimization

---

**Feature 16.5: Graph Extraction with Unified Chunks**
**Problem:** LightRAG may re-chunk documents differently than Qdrant
**Solution:** Use unified chunks from `ChunkingService` for entity extraction

Tasks:
- [ ] Refactor `LightRAGWrapper.insert_documents()` to accept chunks
- [ ] Entity extraction per chunk (using unified chunks)
- [ ] Provenance tracking: Link entities to Qdrant chunk IDs
- [ ] Neo4j schema: Add `chunk_id` property to `:MENTIONED_IN` relationship
- [ ] Batch processing for entity extraction (improve performance)
- [ ] Neo4j transaction batching (reduce memory pressure)
- [ ] Validate chunk alignment between Qdrant and Neo4j

**Deliverables:**
```python
async def insert_documents_with_chunks(
    chunks: List[Chunk],  # From ChunkingService
    batch_size: int = 10
) -> Dict[str, Any]:
    """Extract entities from unified chunks"""
```

**Benefits:**
- Perfect chunk alignment between Qdrant and Neo4j
- Can link vector results to graph entities
- Easier debugging and provenance

---

**Feature 16.6: Frontend E2E Tests** (TD-35)
**Solution:** Add Playwright tests for critical user flows

Tasks:
- [ ] Playwright setup with TypeScript
- [ ] Test: Homepage load and search
- [ ] Test: Streaming results display
- [ ] Test: Session history persistence
- [ ] Test: Health dashboard refresh
- [ ] Test: Mode selector (Hybrid, Vector, Graph, Memory)
- [ ] CI integration (GitHub Actions)
- [ ] Screenshot comparison for visual regression

**Benefits:**
- Catch UI regressions early
- Validate SSE streaming in browser
- Production confidence

---

**Feature 16.7: Graphiti Performance Evaluation & Optimization** 🆕
**Problem:** Graphiti uses internal LLM calls for entity extraction (blackbox, unknown performance)
**Context:** LightRAG optimized with SpaCy + quantized Gemma 2 4B (10x speedup). Graphiti performance unknown.

Tasks:
- [ ] **Benchmark Graphiti Ingestion**
  - Measure `add_episode()` duration for 100 OMNITRACKER documents
  - Profile LLM call count and token usage
  - Compare with LightRAG performance baseline (~2.5s per document)
  - Memory profiling (peak usage during ingestion)

- [ ] **Entity Extraction Quality Comparison**
  - Compare Graphiti entities vs LightRAG entities (precision/recall)
  - Evaluate deduplication accuracy
  - Test on same OMNITRACKER corpus

- [ ] **Graphiti Internal Analysis**
  - Research what LLM Graphiti uses internally (BGE-M3 for embeddings, what for extraction?)
  - Count LLM calls per episode (how many?)
  - Identify optimization opportunities

- [ ] **Custom Entity Extractor Evaluation**
  - Research Graphiti 0.3.21+ custom entity type API
  - Can we inject SpaCy pre-filtering?
  - Can we use our optimized Gemma 2 4B pipeline?
  - Feasibility assessment

- [ ] **Document Decision**
  - If Graphiti <5s per episode (acceptable): Keep as-is
  - If Graphiti 5-30s per episode (slow): Evaluate optimization (custom extractors)
  - If Graphiti >30s per episode (too slow): Consider alternatives
  - Create ADR-024 with decision and rationale

**Deliverables:**
```markdown
docs/benchmarks/GRAPHITI_PERFORMANCE_BENCHMARK.md
- Ingestion duration comparison (Graphiti vs LightRAG)
- Entity extraction quality metrics
- Memory profiling results
- LLM call analysis
- Optimization recommendations

docs/adr/ADR-024-graphiti-optimization-strategy.md (if needed)
- Decision: Keep / Optimize / Replace
- Rationale and trade-offs
- Implementation plan (if optimize)
```

**Benefits:**
- Understand Graphiti performance characteristics
- Identify optimization opportunities
- Apply LightRAG learnings to Graphiti if possible
- Make informed decision on Graphiti future

**Reference:**
- [LIGHTRAG_VS_GRAPHITI.md](../architecture/LIGHTRAG_VS_GRAPHITI.md) - LightRAG vs Graphiti comparison

---

### Success Criteria
- [ ] **Unified Chunking**: All 3 indexes (Qdrant, BM25, LightRAG) use same chunks from ChunkingService
- [ ] **Atomic Re-Indexing**: `POST /admin/reindex` endpoint works end-to-end with SSE progress
- [ ] **PPTX Support**: PowerPoint files index successfully with text extraction
- [ ] **BGE-M3 Decision**: Benchmarking complete, strategy documented in ADR-024
- [ ] **Graph Alignment**: Neo4j LightRAG entities linked to Qdrant chunk IDs via source_chunk_id
- [ ] **Index Consistency**: BM25 corpus size == Qdrant points count == LightRAG chunk count
- [ ] **E2E Tests**: 5+ critical user flows pass in CI with Playwright
- [ ] **Performance**: Re-indexing 100 documents completes in <2 minutes
- [ ] **Graphiti Performance**: Benchmarking complete, decision documented (Keep/Optimize/Replace)
- [ ] **Layer Clarity**: LightRAG (Layer 2 chunk-based) vs Graphiti (Layer 3 episode-based) documented

### Story Points: 69 SP (+17 SP for architecture improvements)
**Breakdown:**
- Feature 16.1: Unified Chunking Service (6 SP) 🆕 **(revised: -2 SP, no A/B testing needed)**
- Feature 16.2: Unified Re-Indexing Pipeline (13 SP) 🆕
- Feature 16.3: PPTX Document Support (8 SP)
- Feature 16.4: BGE-M3 Evaluation & Standardization (8 SP) 🆕
- Feature 16.5: Graph Extraction with Unified Chunks (13 SP)
- Feature 16.6: Frontend E2E Tests (13 SP)
- Feature 16.7: Graphiti Performance Evaluation (8 SP) 🆕

**Timeline:**
- Sequential: 6-8 days (1 developer, ~8-10 SP/day)
- Parallel: 3-4 days (3 subagents: Backend, Architecture, Testing)

**Justification for +11 SP:**
- Unified Chunking is architectural refactoring (medium complexity)
- Unified Re-Indexing requires transactional logic (high complexity)
- BGE-M3 evaluation needs benchmarking infrastructure

### Architecture Decisions
- [ADR-022](../decisions/ADR-022-unified-chunking-service.md) - Unified Chunking Service 🆕
- [ADR-023](../decisions/ADR-023-unified-reindexing-pipeline.md) - Unified Re-Indexing Pipeline 🆕
- [ADR-024](../decisions/ADR-024-bge-m3-standardization.md) - BGE-M3 Standardization Strategy 🆕

### Technical Debt Addressed
- **TD-35**: Frontend E2E Tests (from Sprint 15) ✅
- **TD-38**: Chunking duplication (NEW - critical architectural issue) ✅
- **TD-39**: Index synchronization issues (NEW - medium severity) ✅
- **TD-40**: Embedding model fragmentation (NEW - medium severity) ✅

### Technical Debt Deferred
- **TD-36**: Accessibility improvements (defer to Sprint 17)
- **TD-37**: Error boundary implementation (defer to Sprint 17)

### References
- Branch: TBD (will be `sprint-16-ingestion-improvements`)
- Dependencies: Sprint 15 complete
- Blocked by: None

---

## Sprint 9: 3-Layer Memory Architecture + MCP Client Integration
**Ziel:** Vollständige Memory-Architektur mit MCP Client für externe Tool-Nutzung

### Deliverables
- [ ] Redis Working Memory Manager
- [ ] Memory Router (welche Layer für Query?)
- [ ] Memory Consolidation Pipeline (Short → Long)
- [ ] Memory Decay & Eviction Policies
- [ ] Unified Memory API
- [ ] Memory Health Monitoring
- [ ] **MCP Client Implementation** (Python SDK)
- [ ] **MCP Tool Discovery** (Connect to external MCP Servers)
- [ ] **Action Agent** (LangGraph Integration mit MCP Tools)
- [ ] **Tool Execution Handler** (Call external MCP Tools)

### Technical Tasks
- Redis Cluster Setup mit Eviction Policies
- Memory Tier Selection Logic
- Automatic Memory Consolidation (Cron Jobs)
- Relevance Scoring für Memory Ranking
- Memory Search across all Layers
- Prometheus Metrics für Memory Stats
- MCP Client SDK Setup (connect to external servers)
- Tool Discovery (list available tools from MCP servers)
- Action Agent mit MCP Tool Calls
- Error Handling für Tool Execution

### Success Criteria
- Memory Router entscheidet korrekt zwischen Layers (90%+)
- Consolidation läuft automatisch ohne Data Loss
- Memory Retrieval latency: Redis <10ms, Qdrant <50ms, Graphiti <100ms
- Memory Capacity Planning Dashboard
- MCP Client verbindet zu externen Servern
- Tool Discovery listet verfügbare Tools
- Action Agent kann externe MCP Tools aufrufen
- Tool Execution mit Error Handling funktioniert

---

## Sprint 10: End-User Interface
**Ziel:** Benutzerfreundliche Web-Oberfläche für End-User Interaktion

### Deliverables
- [ ] Web-basierte Chat-Oberfläche
- [ ] Document Upload Interface
- [ ] Search Results Visualization
- [ ] Conversation History View
- [ ] Real-time Response Streaming
- [ ] Multi-turn Conversation Support
- [ ] Source Citation Display
- [ ] Responsive Design (Desktop/Mobile)

### Technical Tasks
- Frontend Framework Setup (React/Vue/Svelte - TBD)
- WebSocket Integration für Streaming
- File Upload Component
- Chat UI Components
- Result Visualization (Citations, Relevance Scores)
- Session Management
- API Client Integration
- Responsive Layout Implementation

### Success Criteria
- User kann Documents hochladen via Drag & Drop
- Chat-Interface zeigt Responses in Real-time
- Source Citations sind klickbar und nachvollziehbar
- Multi-turn Conversations bleiben konsistent
- Interface ist responsive (Mobile + Desktop)
- Latency <500ms für User Input → Response Start
- User Testing: 90%+ Satisfaction Score

---

## Sprint 11: Configuration & Admin Interface
**Ziel:** Admin-Oberfläche für System-Konfiguration und Management

### Deliverables
- [ ] Admin Dashboard
- [ ] LLM Model Configuration UI
- [ ] Vector Database Management
- [ ] Memory Layer Configuration
- [ ] User & Permission Management
- [ ] System Monitoring Dashboard
- [ ] Configuration Import/Export
- [ ] API Key Management

### Technical Tasks
- Admin Frontend Setup
- Configuration Forms (LLM Models, Databases)
- System Status Monitoring UI
- User Management CRUD
- Permission/Role Management
- Configuration Validation
- Live System Metrics Display
- Export/Import Configuration (JSON/YAML)

### Success Criteria
- Admin kann LLM Models ohne Code-Änderung wechseln
- Vector Database Konfiguration über UI möglich
- Memory Layer Settings sind anpassbar
- User Management funktioniert vollständig
- System Metrics sind in Real-time sichtbar
- Configuration Export/Import funktioniert
- Admin Testing: 95%+ Task Success Rate

---

## Sprint 12: Integration, Testing & Production Readiness
**Ziel:** Full System Integration, Load Testing, Deployment

### Deliverables
- [ ] End-to-End Integration aller Komponenten
- [ ] Full Evaluation Suite (RAGAS, Custom Metrics)
- [ ] Load Testing (Locust/K6)
- [ ] Production Docker Images (Multi-Stage Builds)
- [ ] Kubernetes Manifests (Helm Charts)
- [ ] Monitoring Stack (Prometheus, Grafana, Loki)
- [ ] Documentation (Architecture, API, Deployment)

### Technical Tasks
- Integration Tests für alle Agent Paths
- RAGAS Evaluation auf Test-Corpus
- Load Tests mit 100+ concurrent users
- Docker Images optimieren (<500MB)
- Kubernetes Deployment (Staging)
- Observability Stack Setup
- Runbook für Incident Response

### Success Criteria
- Alle Integration Tests grün
- RAGAS Score > 0.85 für alle Query-Typen
- System handled 50 QPS ohne Degradation
- Deployment funktioniert mit Helm-Chart
- Monitoring zeigt alle kritischen Metrics
- Documentation ist vollständig

---

---

## Post-Sprint 12: Continuous Improvement Backlog

### High Priority
- Advanced Query Decomposition (Tree-of-Thought)
- Multi-Modal RAG (Images, Tables via RAG-Anything)
- Fine-Tuning von Retrieval Models
- Cost Optimization (Model Caching, Batch Processing)
- Security Audit & Penetration Testing

### Medium Priority
- Web UI für System Management
- Query Analytics Dashboard
- A/B Testing Framework
- Multi-Tenancy Support
- Backup & Disaster Recovery

### Low Priority
- Additional MCP Servers (Slack, Jira, Google Drive)
- Voice Interface Integration
- Mobile API Optimization
- Internationalization (i18n)

---

## Sprint Velocity Assumptions
- **Sprint-Dauer:** 5 Arbeitstage
- **Team-Kapazität:** 30-40 Story Points pro Sprint
- **Risiko-Buffer:** 20% für unvorhergesehene Komplexität
- **Claude Code Support:** Subagenten übernehmen 40-60% Implementierung

## Definition of Done (DoD)
- [ ] Code Review abgeschlossen
- [ ] Unit Tests Coverage >80%
- [ ] Integration Tests erfolgreich
- [ ] Documentation aktualisiert
- [ ] Performance-Anforderungen erfüllt
- [ ] Security-Review bestanden
- [ ] Deployed in Staging Environment
- [ ] Product Owner Sign-Off

## Risk Management
| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|---------|-----------|
| LLM API Rate Limits (Azure) | Niedrig | Mittel | Primary: Ollama (no limits), Fallback: Azure |
| Neo4j Performance bei Scale | Mittel | Hoch | Indexing, Query Optimization |
| Komplexität Multi-Agent Debugging | Hoch | Hoch | LangSmith, extensive Logging |
| Graphiti Maturity Issues | Mittel | Mittel | Community Support, Fallback zu GraphRAG |
| Budget Überschreitung (LLM Costs) | Niedrig | Niedrig | Development: $0 (Ollama), Production: Optional Azure |
