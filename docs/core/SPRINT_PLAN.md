# Sprint-Planung: Agentisches RAG-System
## Projektname: AegisRAG (Agentic Enterprise Graph Intelligence System)

**Gesamtdauer:** 11 Sprints à 1 Woche (11 Wochen)
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

## Sprint 7: Component 3 - Graphiti Memory + Azure OpenAI Integration (Optional)
**Ziel:** Temporal Memory, Episodic vs. Semantic, Long-Term Context, Optional Azure OpenAI Support

### Deliverables
- [x] Graphiti Installation mit Neo4j Backend
- [x] Bi-Temporal Datenstruktur (Valid Time + Transaction Time)
- [x] Episodic Subgraph (Raw Conversations)
- [x] Semantic Subgraph (Extracted Facts)
- [x] Memory Agent (LangGraph Integration)
- [x] Point-in-Time Query API
- [ ] **NEW: Azure OpenAI Integration Layer (Optional)**
- [ ] **NEW: LLM Abstraction Interface**
- [ ] **NEW: Environment-based LLM Selection**

### Technical Tasks
- Graphiti Config und Schema Design
- Memory Ingestion Pipeline (Conversation → Graph)
- Temporal Query Interface
- Memory Retrieval Agent Implementation
- Memory Decay Strategy (Time-based + Relevance)
- Redis für Short-Term Working Memory
- **NEW: Azure OpenAI Client Wrapper (langchain-openai)**
- **NEW: LLM Factory Pattern (Ollama vs. Azure)**
- **NEW: Environment Variables für Azure Config**
- **NEW: Fallback Logic (Azure unavailable → Ollama)**

### Success Criteria
- Conversations werden automatisch in Episodic Memory persistiert
- Facts werden extrahiert und in Semantic Memory gespeichert
- Point-in-Time Queries rekonstruieren historischen Kontext
- Memory Retrieval <100ms
- **NEW: System läuft mit Ollama (default) UND Azure OpenAI (optional)**
- **NEW: LLM-Switch ohne Code-Änderung (nur .env)**

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

## Sprint 9: 3-Layer Memory Architecture + LLM A/B Testing
**Ziel:** Redis Short-Term, Qdrant Long-Term, Graphiti Episodic, Ollama vs. Azure Benchmarking

### Deliverables
- [x] Redis Working Memory Manager
- [x] Memory Router (welche Layer für Query?)
- [x] Memory Consolidation Pipeline (Short → Long)
- [x] Memory Decay & Eviction Policies
- [x] Unified Memory API
- [x] Memory Health Monitoring
- [ ] **NEW: LLM A/B Testing Framework**
- [ ] **NEW: Performance Benchmarks (Ollama vs. Azure)**
- [ ] **NEW: Quality Metrics (RAGAS for both LLMs)**

### Technical Tasks
- Redis Cluster Setup mit Eviction Policies
- Memory Tier Selection Logic
- Automatic Memory Consolidation (Cron Jobs)
- Relevance Scoring für Memory Ranking
- Memory Search across all Layers
- Prometheus Metrics für Memory Stats
- **NEW: A/B Test Harness (gleiche Queries, beide LLMs)**
- **NEW: Latency Comparison (p50, p95, p99)**
- **NEW: Quality Comparison (RAGAS, Human Eval)**
- **NEW: Cost Tracking Dashboard**

### Success Criteria
- Memory Router entscheidet korrekt zwischen Layers (90%+)
- Consolidation läuft automatisch ohne Data Loss
- Memory Retrieval latency: Redis <10ms, Qdrant <50ms, Graphiti <100ms
- Memory Capacity Planning Dashboard
- **NEW: Benchmark Report (Ollama vs. Azure) erstellt**
- **NEW: Decision Matrix für LLM-Wahl dokumentiert**

---

## Sprint 10: Component 4 - MCP Server Integration
**Ziel:** Model Context Protocol, Tool Integration, OAuth 2.1

### Deliverables
- [x] MCP Server Implementation (Python SDK)
- [x] stdio Transport für lokale Tools
- [x] Streamable HTTP für Remote Services
- [x] OAuth 2.1 Authentication Flow
- [x] Action Agent (LangGraph Integration)
- [x] MCP Tool Registry & Discovery

### Technical Tasks
- MCP Python SDK Setup
- Tool Definitions (Resources, Prompts, Sampling)
- stdio Server für File System, Shell
- HTTP Server für REST APIs
- OAuth Provider Integration (Auth0/Clerk)
- Action Agent mit MCP Tool Calls

### Success Criteria
- MCP Server startet und registriert Tools
- stdio Tools (ls, cat, grep) funktional
- HTTP Tools können Remote APIs aufrufen
- OAuth Flow funktioniert End-to-End
- Action Agent nutzt MCP Tools korrekt

---

## Sprint 11: Integration, Testing & Production Readiness
**Ziel:** Full System Integration, Load Testing, Deployment

### Deliverables
- [x] End-to-End Integration aller 4 Komponenten
- [x] Full Evaluation Suite (RAGAS, Custom Metrics)
- [x] Load Testing (Locust/K6)
- [x] Production Docker Images (Multi-Stage Builds)
- [x] Kubernetes Manifests (Helm Charts)
- [x] Monitoring Stack (Prometheus, Grafana, Loki)
- [x] Documentation (Architecture, API, Deployment)

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

## Post-Sprint 11: Continuous Improvement Backlog

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
