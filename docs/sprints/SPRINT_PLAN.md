# Sprint-Planung: AegisRAG
## Agentic Enterprise Graph Intelligence System

**Team-Setup:** 1-2 Entwickler + Claude Code Subagenten
**Sprint-Dauer:** 5 Arbeitstage
**Velocity:** 30-40 Story Points pro Sprint

---

## Sprint 1: Foundation & Infrastructure Setup ✅
**Ziel:** Entwicklungsumgebung, Core-Infrastruktur, CI/CD Pipeline

**Breakdown:**
| Feature | SP |
|---------|-----|
| Repository-Struktur (Monorepo) | 3 |
| Docker Compose (Qdrant, Redis, Neo4j) | 5 |
| Python Environment + Poetry | 3 |
| Pre-commit Hooks (Black, Ruff, MyPy) | 2 |
| GitHub Actions CI/CD | 5 |
| Logging-Framework (Structlog) | 2 |

### Deliverables
- Repository mit Monorepo-Layout
- Docker Compose für lokale Entwicklung
- pyproject.toml mit Dependencies
- Pre-commit Hooks konfiguriert
- CI/CD Pipeline (Lint, Test, Build)
- .env Template und Secrets Management

### Technical Tasks
- Git Repository initialisieren
- Docker Compose Services definieren
- Python 3.11+ Environment Setup
- Basic Health-Check Endpoints

### Success Criteria
- `docker compose up` startet alle Services
- `pytest` läuft erfolgreich durch
- CI Pipeline ist grün

### References
- Branch: `sprint-01-foundation`

---

## Sprint 2: Vector Search Foundation ✅
**Ziel:** Qdrant-Integration, Hybrid Search, Basic Retrieval

**Breakdown:**
| Feature | SP |
|---------|-----|
| 2.1 Qdrant Client Foundation | 5 |
| 2.2 Document Ingestion Pipeline | 8 |
| 2.3 Embedding Service | 5 |
| 2.4 Text Chunking Strategy | 3 |
| 2.5 BM25 Search Engine | 5 |
| 2.6 Hybrid Search (Vector + BM25) | 8 |
| 2.7 Retrieval API Endpoints | 5 |
| 2.8 Security Hardening | 5 |

### Deliverables
- QdrantClientWrapper mit async/sync Support
- DocumentIngestionPipeline (PDF, TXT, MD, DOCX)
- EmbeddingService mit LRU Cache
- BM25Search mit Persistence
- HybridSearch mit RRF Fusion
- FastAPI Endpoints für Search/Ingest

### Technical Tasks
- Qdrant Python Client Integration
- LlamaIndex SimpleDirectoryReader
- Ollama nomic-embed-text Integration
- rank_bm25 Implementation
- Rate Limiting (slowapi)

### Success Criteria
- 933 Test-Dokumente indexiert
- Hybrid Search <200ms
- 212 Tests passing (98.6% coverage)
- P0/P1/P2 Security implementiert

### References
- [ADR-004: Qdrant als Vector Database](../adr/ADR_INDEX.md)
- [ADR-009: RRF für Hybrid Search](../adr/ADR_INDEX.md)

---

## Sprint 3: Advanced Retrieval ✅
**Ziel:** Reranking, Query-Transformation, Metadata-Filtering

**Breakdown:**
| Feature | SP |
|---------|-----|
| Cross-Encoder Reranker | 8 |
| Query Decomposition | 5 |
| Metadata-Filter Engine | 8 |
| RAGAS Evaluation Framework | 5 |
| Adaptive Chunking | 8 |
| Security Fix (MD5 → SHA-256) | 2 |

### Deliverables
- Cross-Encoder Reranker (ms-marco-MiniLM)
- Query Classifier (SIMPLE/COMPOUND/MULTI_HOP)
- Metadata-Filter Engine (Date, Source, Tags)
- RAGAS Metrics Integration
- Adaptive Chunking basierend auf Document-Typ

### Technical Tasks
- HuggingFace sentence-transformers Integration
- Query Classifier mit Ollama llama3.2
- Qdrant Metadata Filter Integration
- RAGAS Context Precision/Recall/Faithfulness

### Success Criteria
- Reranking +23% Precision @3
- Query Decomposition 90%+ Accuracy
- RAGAS Score 0.88

### References
- [SPRINT_3_SUMMARY.md](../archive/sprints/SPRINT_3_SUMMARY.md)

---

## Sprint 4: LangGraph Orchestration Layer ✅
**Ziel:** Multi-Agent Framework, State Management, Routing

**Breakdown:**
| Feature | SP |
|---------|-----|
| LangGraph Coordinator Agent | 13 |
| Query Router | 8 |
| Vector Search Agent | 5 |
| State Management | 8 |
| LangSmith Integration | 3 |
| Error Handling & Retry | 3 |

### Deliverables
- LangGraph Coordinator Agent
- Query Router mit Intent-Classification
- Vector Search Agent
- State Persistence (Redis)
- LangSmith Tracing

### Technical Tasks
- LangGraph Graph Definition (Nodes, Edges)
- Agent Base Classes mit Tool Interface
- Redis State Backend
- Durable Execution Setup

### Success Criteria
- Coordinator routet 95%+ Queries korrekt
- State über Multi-Turn erhalten
- LangSmith zeigt Execution Steps

### References
- [ADR-001: LangGraph als Orchestrierung](../adr/ADR_INDEX.md)

---

## Sprint 5: LightRAG Integration ✅
**Ziel:** Graph-basiertes Reasoning, Knowledge Graph Construction

**Breakdown:**
| Feature | SP |
|---------|-----|
| LightRAG Setup | 5 |
| Neo4j Backend | 5 |
| Entity Extraction Pipeline | 13 |
| Dual-Level Retrieval | 8 |
| Graph Query Agent | 8 |
| Incremental Updates | 5 |

### Deliverables
- LightRAG mit Neo4j Backend
- Entity & Relationship Extraction
- Dual-Level Retrieval (Entities + Topics)
- Graph Query Agent (LangGraph)
- Incremental Graph Updates

### Technical Tasks
- Neo4j Docker-Service mit Persistenz
- LightRAG Config (Ollama LLM + Embeddings)
- Cypher Query Templates
- Graph Visualization UI

### Success Criteria
- Knowledge Graph mit 500+ Entities
- Graph Queries <500ms
- Incremental Updates ohne Full-Reindex

### References
- [ADR-005: LightRAG statt Microsoft GraphRAG](../adr/ADR_INDEX.md)

---

## Sprint 6: Hybrid Vector-Graph Retrieval ✅
**Ziel:** Parallel Retrieval, Context Fusion, Multi-Hop Reasoning

**Breakdown:**
| Feature | SP |
|---------|-----|
| Parallel Execution (Send API) | 8 |
| RRF für Vector+Graph | 5 |
| Multi-Hop Query Expansion | 8 |
| Community Detection (Leiden) | 8 |
| Global vs. Local Search | 5 |
| Hybrid Evaluation | 5 |

### Deliverables
- Parallel Vector+Graph Execution
- Reciprocal Rank Fusion
- Multi-Hop Query Expansion
- Community Detection Integration
- Benchmark Suite

### Technical Tasks
- Async Retrieval Orchestration
- Context Fusion Algorithmus
- Graph Traversal Optimierung
- Query Mode Selection Logic

### Success Criteria
- Parallel Retrieval spart 40%+ Latency
- Hybrid +30% bessere Relevance
- Multi-Hop über 3+ Hops

### References
- [ADR-003: Hybrid Vector-Graph Architecture](../adr/ADR_INDEX.md)

---

## Sprint 7: Graphiti Memory Integration ✅
**Ziel:** Temporal Memory, Episodic vs. Semantic, Long-Term Context

**Breakdown:**
| Feature | SP |
|---------|-----|
| Graphiti Setup | 5 |
| Bi-Temporal Datenstruktur | 8 |
| Episodic Subgraph | 8 |
| Semantic Subgraph | 8 |
| Memory Agent | 8 |
| Point-in-Time API | 5 |

### Deliverables
- Graphiti mit Neo4j Backend
- Bi-Temporal Model (Valid Time + Transaction Time)
- Episodic Subgraph (Conversations)
- Semantic Subgraph (Facts)
- Memory Retrieval Agent

### Technical Tasks
- Graphiti Config und Schema Design
- Memory Ingestion Pipeline
- Temporal Query Interface
- Redis für Short-Term Memory

### Success Criteria
- Conversations in Episodic Memory
- Facts in Semantic Memory
- Point-in-Time Queries funktional
- Memory Retrieval <100ms

### References
- [ADR-006: 3-Layer Memory Architecture](../adr/ADR_INDEX.md)

---

## Sprint 8: Critical Path E2E Testing 📋
**Ziel:** Production-Confidence durch E2E Tests für kritische Paths

**Breakdown:**
| Feature | SP |
|---------|-----|
| High Risk Tests (12 paths) | 24 |
| Medium Risk Tests (8 paths) | 10 |
| Lower Risk Tests (6 paths) | 2 |
| CI Pipeline Updates | 2 |
| Documentation | 2 |

### Deliverables
- 40 E2E Integration Tests
- Real Service Integration (Redis, Qdrant, Neo4j, Ollama)
- CI Pipeline Validation
- Coverage Report

### Technical Tasks
- E2E Tests für High Risk Paths (Community Detection, Reranking, RAGAS)
- Medium Risk (Hybrid Search, Ingestion, Metadata Filter)
- CI Pipeline Service Availability Checks

### Success Criteria
- 40 E2E Tests passing
- Test Execution <10 Minuten
- 95%+ Critical Path Coverage
- NO MOCKS Policy

### References
- [ADR-014: E2E Integration Testing](../adr/ADR-014-e2e-integration-testing.md)
- [ADR-015: Critical Path Testing](../adr/ADR-015-critical-path-testing.md)

---

## Sprint 14: Backend Performance & Testing ✅
**Ziel:** Testing Infrastructure & Monitoring für Extraction Pipeline

**Breakdown:**
| Feature | SP |
|---------|-----|
| 14.2 Extraction Pipeline Factory | 8 |
| 14.3 Production Benchmarking | 8 |
| 14.5 Retry Logic & Error Handling | 8 |
| 14.6 Prometheus Metrics | 8 |

### Deliverables
- ExtractionPipelineFactory
- BenchmarkRunner mit Memory Profiling
- Retry Logic (tenacity)
- 12 Prometheus Metrics

### Technical Tasks
- Factory Pattern für Pipeline Selection
- tracemalloc Memory Profiling
- Exponential Backoff Retry
- Metrics für Extraction Pipeline

### Success Criteria
- 132/132 Tests passing
- Factory creates Three-Phase Pipeline
- Prometheus Observability

### References
- [SPRINT_14_COMPLETION_REPORT.md](SPRINT_14_COMPLETION_REPORT.md)
- [ADR-019: Integration Tests as E2E](../adr/ADR-019-integration-tests-as-e2e.md)

---

## Sprint 15: Frontend Interface ✅
**Ziel:** Perplexity-Inspired UI mit SSE Streaming

**Breakdown:**
| Feature | SP |
|---------|-----|
| 15.1 React + Vite + SSE Backend | 13 |
| 15.2 Perplexity Layout | 8 |
| 15.3 Search Input + Mode Selector | 10 |
| 15.4 Streaming Answer + Sources | 21 |
| 15.5 Conversation History | 13 |
| 15.6 Health Dashboard | 8 |

### Deliverables
- React 18 + Vite + TypeScript + Tailwind
- SSE Streaming Endpoint
- Multi-Mode Search (Hybrid, Vector, Graph, Memory)
- Source Cards mit Provenance
- Session History Sidebar
- Health Dashboard

### Technical Tasks
- SSE Endpoint: POST /api/v1/chat/stream
- Zustand State Management
- React Router 6
- German Localization

### Success Criteria
- Streaming <100ms to first token
- Session History persistent
- Responsive Design (Mobile + Desktop)

### References
- [SPRINT_15_PLAN.md](SPRINT_15_PLAN.md)
- [ADR-020: SSE Streaming](../adr/ADR-020-sse-streaming-for-chat.md)
- [ADR-021: Perplexity UI Design](../adr/ADR-021-perplexity-inspired-ui-design.md)

---

## Sprint 16: Unified Ingestion Architecture 📋
**Ziel:** Architektur-Vereinheitlichung, PPTX Support, BGE-M3

**Breakdown:**
| Feature | SP |
|---------|-----|
| 16.1 Unified Chunking Service | 6 |
| 16.2 Unified Re-Indexing Pipeline | 13 |
| 16.3 PPTX Document Support | 8 |
| 16.4 BGE-M3 Evaluation | 8 |
| 16.5 Graph Extraction mit Chunks | 13 |
| 16.6 Frontend E2E Tests | 13 |
| 16.7 Graphiti Performance Eval | 8 |

### Deliverables
- ChunkingService (Single Source of Truth)
- POST /api/v1/admin/reindex mit SSE Progress
- PPTX Support via python-pptx
- BGE-M3 Standardization Decision
- Unified Chunk IDs in Neo4j

### Technical Tasks
- Centralized Chunking Logic
- Atomic Re-Indexing (Qdrant + BM25 + Neo4j)
- BGE-M3 vs nomic-embed-text Benchmark
- Playwright E2E Tests

### Success Criteria
- All 3 Indexes use same Chunks
- Re-Indexing 100 Docs <2 Minuten
- Index Consistency (BM25 == Qdrant == Neo4j)

### References
- [ADR-022: Unified Chunking](../adr/ADR-022-unified-chunking-service.md)
- [ADR-023: Unified Re-Indexing](../adr/ADR-023-unified-reindexing-pipeline.md)
- [ADR-024: BGE-M3 Standardization](../adr/ADR-024-bge-m3-system-wide-standardization.md)

---

## Sprint 17: Admin UI & User Profiling 📋
**Ziel:** Admin UI, Conversation Fixes, Implicit User Profiling

**Breakdown:**
| Feature | SP |
|---------|-----|
| 17.1 Admin UI Directory Indexing | 13 |
| 17.2 Conversation History Fixes | 8 |
| 17.3 Auto-Generated Titles | 5 |
| 17.4 Implicit User Profiling | 21 |
| 17.5 Fix Duplicate Streaming | 3 |
| 17.6 Admin Statistics API | 5 |

### Deliverables
- Admin Page mit Directory Selection
- Conversation Persistence (Redis)
- LLM-Generated Conversation Titles
- User Profile Graph (Neo4j)
- Semantic Conversation Search

### Technical Tasks
- AdminPage Component
- Redis Session Persistence
- Profile Signal Extraction
- Answer Complexity Adaptation

### Success Criteria
- Conversations persist across refreshes
- Follow-up Questions mit Context
- User Profile builds implicitly

### References
- [SPRINT_17_PLAN.md](SPRINT_17_PLAN.md)

---

## Sprint 33: Directory Indexing & Live Progress 📋
**Ziel:** Enhanced Directory Indexing mit Live Progress

**Breakdown:**
| Feature | SP |
|---------|-----|
| 33.1 Verzeichnisauswahl-Dialog | 5 |
| 33.2 Dateilisten mit Farbkodierung | 5 |
| 33.3 Live-Fortschrittsanzeige | 5 |
| 33.4 Detail-Dialog | 13 |
| 33.5 Error-Tracking | 5 |
| 33.6 Live-Log Stream | 8 |
| 33.7 Persistente Logging-DB | 13 |
| 33.8 Parallele Verarbeitung | 8 |

### Deliverables
- Verzeichnisauswahl mit rekursiver Suche
- Farbkodierte Dateiliste (Docling/LlamaIndex/Unsupported)
- Echtzeit-Fortschrittsanzeige
- SQLite Job-Persistierung

### Technical Tasks
- Directory Selection UI
- SSE Progress Events
- SQLite Logging Backend
- Parallel File Processing

### Success Criteria
- Live Progress für alle Files
- Error-Tracking mit Details
- Persistente Job History

### References
- [SPRINT_33_PLAN.md](SPRINT_33_PLAN.md)

---

## Sprint 34: Knowledge Graph Enhancement 📋
**Ziel:** LightRAG Schema Alignment, RELATES_TO Relationships

**Breakdown:**
| Feature | SP |
|---------|-----|
| 34.1 entity_id Property Migration | 5 |
| 34.2 RELATES_TO Extraction | 13 |
| 34.3 Graph Visualization | 13 |
| 34.4 Graph Filter & Styling | 8 |
| 34.5 Multi-Hop Query Support | 8 |
| 34.6 Graph Export | 5 |
| 34.7 Analytics Dashboard | 8 |
| 34.8 Re-Indexing | 3 |

### Deliverables
- Neo4j Schema mit entity_id Property
- Entity-Entity RELATES_TO Relationships
- Frontend Graph Visualization
- Multi-Hop Traversal (1-5 Hops)
- Export (Cytoscape, D3, vis.js)

### Technical Tasks
- Neo4j Schema Migration
- LLM-based Relationship Extraction
- Edge Styling (Farben, Gewichtung)
- PageRank Analytics

### Success Criteria
- Schema aligned mit LightRAG Standard
- RELATES_TO mit weight, description, keywords
- Multi-Hop Queries funktional

### References
- [SPRINT_34_PLAN.md](SPRINT_34_PLAN.md)
- [ADR-040: LightRAG Schema Alignment](../adr/ADR-040-lightrag-neo4j-schema-alignment.md)

---

## Sprint 40: MCP + Secure Shell Sandbox 📋
**Ziel:** MCP Client/Server Integration + Bubblewrap Shell Sandbox

**Breakdown:**
| Feature | SP |
|---------|-----|
| 40.1 MCP Client Activation | 3 |
| 40.2 Tool Discovery | 5 |
| 40.3 Chat Tool Integration | 8 |
| 40.4 Tool Execution Panel | 5 |
| 40.5 AegisRAG als MCP Server | 5 |
| 40.6 MCP Server Config UI | 3 |
| 40.7 BubblewrapSandboxBackend | 5 |
| 40.8 deepagents Integration | 4 |
| 40.9 Multi-Language CodeAct | 3 |
| 40.10 Progress Tracking | 2 |
| 40.11 Observability & Audit | 3 |

### Deliverables
- MCP Client (Filesystem, Web Fetch, GitHub)
- Secure Shell Sandbox (Bubblewrap, NOT Docker)
- Multi-Language Execution (Bash + Python/Pyodide)
- AegisRAG MCP Server (search_knowledge, query_graph, secure_shell)

### Technical Tasks
- MCP Connection Manager
- BubblewrapSandboxBackend (SandboxBackendProtocol)
- deepagents Integration
- Audit Logging

### Success Criteria
- MCP Tools in Chat verwendbar
- Shell Sandbox <100ms Overhead
- Network Isolation (--unshare-net)
- Timeout + Output Truncation

### References
- [SPRINT_40_PLAN.md](SPRINT_40_PLAN.md)
- [ADR-007: MCP Client Integration](../adr/ADR_INDEX.md)
- [ADR-043: Secure Shell Sandbox](../adr/ADR-043_SECURE_SHELL_SANDBOX.md)

---

## Sprint 41: Namespace Isolation + RAGAS 🔄
**Ziel:** Multi-Tenant Namespace Isolation + RAG Evaluation

**Breakdown:**
| Feature | SP |
|---------|-----|
| 41.1 Namespace Isolation Layer | 5 |
| 41.2 Namespace in FourWayHybridSearch | 3 |
| 41.3 Namespace Filter in Graph | 3 |
| 41.4 Chat API Namespace Parameter | 2 |
| 41.5 Namespace Integration Tests | 2 |
| 41.6 Benchmark Corpus Ingestion | 5 |
| 41.7 RAGAS Evaluation Pipeline | 5 |
| 41.8 Evaluation Reports | 3 |
| 41.9 JSON Apostrophe Fix + Parallel Embeddings | 2 |

### Deliverables
- NamespaceManager (Qdrant, Neo4j, BM25, Redis)
- Neo4j Query Validator (Security Layer)
- RAGAS Integration mit Namespace-Scoped Search
- Benchmark Datasets (HotpotQA, MS MARCO, Natural Questions)
- JSON Apostrophe Repair (French text support)
- Parallel Embedding Generation (GPU utilization fix)

### Technical Tasks
- SecureNeo4jClient mit Query Validation
- Payload-based Filtering (Qdrant)
- BenchmarkDatasetLoader
- RAGAS Metrics (Context Precision/Recall/Faithfulness)

### Success Criteria
- Queries ohne namespace_id Filter werden REJECTED
- No Cross-Namespace Data Leakage
- 77 Unit Tests + 11 Playwright E2E Tests

### References
- [SPRINT_41_PLAN.md](SPRINT_41_PLAN.md)
- [SPRINT_41_SUMMARY.md](SPRINT_41_SUMMARY.md)

---

## Sprint 42: 4-Way Hybrid RRF ✅ (COMPLETE 2025-12-09)
**Ziel:** Intent-Weighted 4-Way Hybrid Retrieval

**Breakdown:**
| Feature | SP |
|---------|-----|
| 42.1 Intent Classifier | 8 |
| 42.2 4-Way Hybrid Search Engine | 13 |
| 42.3 Automatic Community Detection | 5 |
| 42.4 DGX Spark Compatibility Fix | 2 |

### Deliverables
- IntentClassifier (factual, keyword, exploratory, summary)
- FourWayHybridSearch (Vector + BM25 + Graph Local + Graph Global)
- Intent-Weighted RRF Fusion
- Community Detection in Ingestion Pipeline

### Technical Tasks
- LLM + Rule-based Intent Classification
- 4-Way RRF Formula
- Neo4j Community ID auf Entities
- VRAM Parsing für Unified Memory

### Success Criteria
- 95 Unit Tests (0.95s)
- 100% Intent Classification Accuracy
- Graceful Degradation verified

### References
- [SPRINT_42_PLAN.md](SPRINT_42_PLAN.md)
- [TD-057: 4-Way Hybrid RRF](../technical-debt/TD-057_4WAY_HYBRID_RRF_RETRIEVAL.md)

---

## Sprint 43: Multi-Criteria Deduplication & Pipeline Monitoring ✅ (COMPLETE 2025-12-11)
**Ziel:** Multi-Criteria Entity Deduplication + Production Pipeline Monitoring & Evaluation

**Start:** 2025-12-10
**End:** 2025-12-11
**Status:** COMPLETE

**Breakdown:**
| Feature | SP | Status |
|---------|-----|--------|
| 43.1 MultiCriteriaDeduplicator Implementation | 5 | ✅ DONE |
| 43.2 Config Options for Deduplication | 2 | ✅ DONE |
| 43.3 Unit Tests for Multi-Criteria Matching | 3 | ✅ DONE |
| 43.4 Integration with Extraction Pipeline | 3 | ✅ DONE |
| 43.5 Benchmark: Before vs After Dedup | 2 | ✅ DONE |
| 43.6 Documentation Update | 1 | ✅ DONE |
| 43.7 Chunking Metrics (chars in/out, overlap) | 3 | ✅ DONE |
| 43.8 Deduplication Metrics in Pipeline | 3 | ✅ DONE |
| 43.9 Extraction Metrics (Entities/Relations by type) | 2 | ✅ DONE |
| 43.10 Logging for Report Generation | 2 | ✅ DONE |
| 43.11 RAGAS TXT Pipeline Evaluation | 5 | ✅ DONE |
| 43.12 HotPotQA Smart Chunk-Size Benchmark | 3 | ✅ DONE (Bonus) |
| 43.13 Parallel Extraction Benchmark | 3 | ✅ DONE (Bonus) |

### Deliverables
**Part 1: Deduplication (COMPLETE)**
- MultiCriteriaDeduplicator class (extends SemanticDeduplicator)
- 4 matching criteria: exact, edit distance, substring, semantic
- Config options for thresholds and min-lengths
- Unit tests with Nicolas Cage test cases (335 lines)
- Benchmark comparison: raw vs deduplicated entity counts

**Part 2: Pipeline Monitoring (COMPLETE)**
- Prometheus metrics for chunking (input chars, output chunks, overlap)
- Prometheus metrics for deduplication (before/after counts, match criteria)
- Prometheus metrics for extraction (entity types, relation types, model)
- Structured logging for JSON report export
- RAGAS TXT evaluation pipeline script

**Part 3: Comprehensive Benchmarking (COMPLETE)**
- Chunk size benchmark (500-4000 chars) with qwen3:32b
- HotPotQA smart benchmark with gemma3:4b and qwen2.5:7b
- Parallel extraction benchmark (gemma3:4b + qwen2.5:7b combined)
- Full pipeline evaluation with large HotPotQA samples (10 samples, 68k chars)

### Technical Tasks
**Part 1: Deduplication**
- ✅ python-Levenshtein dependency (Added to pyproject.toml)
- ✅ _is_duplicate_by_criteria() method
- ✅ Two-phase deduplication (fast criteria + semantic)
- ✅ Factory function update (create_deduplicator_from_config)

**Part 2: Pipeline Monitoring**
- ✅ New metrics in src/monitoring/metrics.py (12 new metrics)
- ✅ Chunking service metric integration
- ✅ Deduplicator metric integration (lightrag_wrapper.py)
- ✅ RAGAS samples → TXT files conversion
- ✅ Pipeline execution with TXT input

**Part 3: Benchmarking**
- ✅ scripts/benchmark_chunk_sizes.py
- ✅ scripts/benchmark_chunking_smart.py
- ✅ scripts/benchmark_parallel_hotpotqa.py
- ✅ scripts/ragas_txt_pipeline_evaluation.py

### Success Criteria
**Part 1: Deduplication**
- ✅ 5-6% additional reduction vs simple lowercase dedup
- ✅ Substring matching catches "Goertz" in "Allison Beth 'Allie' Goertz"
- ✅ Graceful fallback without python-Levenshtein
- ✅ Feature flag support (enable_multi_criteria_dedup)

**Part 2: Pipeline Monitoring**
- ✅ Prometheus endpoint exposes all new metrics
- ✅ Reports can be generated from structured logs
- ✅ RAGAS TXT evaluation runs through production pipeline

**Part 3: Benchmarking Results**
- ✅ **10.1% deduplication reduction** on large multi-chunk documents
- ✅ **Optimal chunk size:** 2500-3500 chars for speed, 500-1000 for coverage
- ✅ **Parallel extraction:** +20-30% more entities, +45-107% more relations
- ✅ **Model comparison:** qwen2.5:7b stable across all chunk sizes

### Key Findings (RAGAS Evaluation)

| Metric | Value |
|--------|-------|
| Large samples processed | 10/10 (68,126 chars) |
| Chunks created | 18 |
| Entities (raw → deduped) | 346 → 311 |
| **Dedup reduction** | **10.1%** |
| Multi-chunk dedup rate | 8.6-18.3% |
| Entity types | ORG (32%), PERSON (29%), LOCATION (17%) |

**Model Comparison (HotPotQA):**
| Model | Stability | Max Entities | Best For |
|-------|-----------|--------------|----------|
| gemma3:4b | ⚠️ Unstable >2500 chars | 104 | Small chunks |
| qwen2.5:7b | ✅ Stable all sizes | 92 | Large chunks |
| Parallel | ✅ Fault-tolerant | 129 (+24%) | Production |

### References
- [ADR-044: Multi-Criteria Entity Deduplication](../adr/ADR-044_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md)
- [TD-062: Multi-Criteria Entity Deduplication](../technical-debt/TD-062_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md)
- [RAGAS_EVALUATION_ANALYSIS.md](../RAGAS_EVALUATION_ANALYSIS.md)
- [NEO4J_LLM_GRAPH_BUILDER_COMPARISON.md](../NEO4J_LLM_GRAPH_BUILDER_COMPARISON.md)

### Reports Generated
- `reports/chunk_size_benchmark_20251210_211022.json`
- `reports/benchmark_smart_gemma3_4b_20251211_090246.json`
- `reports/benchmark_smart_qwen2.5_7b_20251211_093131.json`
- `reports/benchmark_parallel_hotpotqa_20251211_100720.json`
- `reports/ragas_txt_pipeline_eval_20251211_135825.json`
- `reports/ragas_txt_pipeline_eval_20251211_160655.json`
- `reports/llm_extraction_benchmark_round2_20251211_071122_dedup.json`

---

## Sprint 44: Relation Deduplication & Full Pipeline Evaluation ✅
**Ziel:** Relation Deduplication + Multi-Model Pipeline Evaluation mit Production-Grade Monitoring

**Start:** 2025-12-12
**End:** 2025-12-12
**Status:** COMPLETE

---

### Part 1: Relation Deduplication (TD-063)

| Feature | SP | Status |
|---------|-----|--------|
| 44.1 RelationDeduplicator Implementation | 5 | 📋 |
| 44.2 Entity Name Normalization for Relations | 2 | 📋 |
| 44.3 Type Synonym Resolution | 3 | 📋 |
| 44.4 Bidirectional Relation Handling | 2 | 📋 |
| 44.5 Integration with lightrag_wrapper.py | 2 | 📋 |
| 44.6 Unit Tests for Relation Deduplication | 2 | 📋 |

**Deliverables:**
- `src/components/graph_rag/relation_deduplicator.py` (NEW)
- Stage 1: Entity name normalization (remap to canonical names after entity dedup)
- Stage 2: Type synonym resolution (STARRED_IN, ACTED_IN, PLAYED_IN → ACTED_IN)
- Stage 3: Bidirectional/symmetric relation handling (A↔B only once)
- Config: `enable_relation_dedup`, `relation_type_synonyms`

---

### Part 2: Pipeline Monitoring & Logging Enhancement

| Feature | SP | Status |
|---------|-----|--------|
| 44.7 PipelineMonitor Class | 3 | 📋 |
| 44.8 Structured Event Logging | 2 | 📋 |
| 44.9 Report Generator | 3 | 📋 |
| 44.10 Model-Configurable Extraction | 2 | 📋 |

**Deliverables:**
- `src/monitoring/pipeline_monitor.py` (NEW) - Collects all pipeline metrics
- Structured JSON event logging for each pipeline stage
- Report generator: JSON + Markdown summary
- `--model` parameter für Extraction-Modell-Auswahl

**Pipeline Stages mit Monitoring:**
```
TXT Input → Chunking → Extraction → Entity Dedup → Relation Dedup → Neo4j Insert
    │           │           │            │              │              │
    └───────────┴───────────┴────────────┴──────────────┴──────────────┘
                            Pipeline Monitor (collects all metrics)
```

**Metriken pro Stage:**
| Stage | Metriken |
|-------|----------|
| Input | file_count, total_chars, avg_chars_per_file |
| Chunking | chunks_created, avg_chunk_size, overlap_chars |
| Extraction | entities_raw, relations_raw, entity_types, relation_types, duration |
| Entity Dedup | before, after, reduction_%, criteria_distribution |
| Relation Dedup | before, after, reduction_%, type_merges, bidirectional_merges |
| Neo4j | nodes_created, edges_created, duration |

---

### Part 3: Multi-Model Pipeline Evaluation

| Feature | SP | Status |
|---------|-----|--------|
| 44.11 Evaluation Script mit Model-Parameter | 3 | 📋 |
| 44.12 HotPotQA TXT Dataset (10 Samples) | 1 | 📋 |
| 44.13 Model Runs: qwen3:8b, qwen2.5:7b, nuextract | 3 | 📋 |
| 44.14 Model Runs: gemma3:4b, qwen2.5:3b | 2 | 📋 |
| 44.15 Comparison Report Generator | 3 | 📋 |

**Test-Matrix:**
| Model | Size | Priority | Expected Time |
|-------|------|----------|---------------|
| qwen3:32b | 20 GB | BASELINE (neu mit Relation Dedup!) | ~47 min |
| qwen3:8b | 5 GB | HIGH | ~15-20 min |
| qwen2.5:7b | 4 GB | HIGH | ~12-18 min |
| nuextract:3.8b | 2 GB | HIGH (NER-specialized) | ~10-15 min |
| gemma3:4b | 3 GB | MEDIUM | ~10-15 min |
| qwen2.5:3b | 1 GB | MEDIUM | ~8-12 min |

**WICHTIG:** Die Sprint 43 Baseline (qwen3:32b) enthält KEINE Relation Deduplication!
Alle Modelle müssen mit der vollständigen Pipeline (inkl. Relation Dedup) neu getestet werden.

**Evaluation Metriken pro Model:**
1. **Quality:** Entities, Relations, Entity Types Distribution
2. **Deduplication:** Entity Reduction %, Relation Reduction %
3. **Performance:** Time/Sample, Time/1000 chars
4. **Stability:** Success Rate, JSON Parse Errors

**Deliverables:**
- `scripts/pipeline_model_evaluation.py` - Main evaluation script
- `reports/model_comparison_<model>_<timestamp>.json` - Per-model reports
- `reports/model_comparison_summary_<timestamp>.md` - Aggregated comparison

---

### Sprint 44 Breakdown Summary

| Part | Features | SP | Focus |
|------|----------|-----|-------|
| Part 1 | 44.1-44.6 | 16 | Relation Deduplication |
| Part 2 | 44.7-44.10 | 10 | Pipeline Monitoring |
| Part 3 | 44.11-44.15 | 12 | Model Evaluation |
| **Total** | **15 Features** | **38** | |

---

### Technical Tasks

**Relation Deduplication:**
- Create `src/components/graph_rag/relation_deduplicator.py`
- Define `RELATION_TYPE_SYNONYMS` mapping
- Define `SYMMETRIC_RELATIONS` set
- Modify entity deduplicator to return `entity_mapping: dict[str, str]`
- Update `lightrag_wrapper.py` integration

**Pipeline Monitoring:**
- Create `src/monitoring/pipeline_monitor.py`
- Add `@monitor_stage` decorator for automatic metric collection
- JSON event log format with timestamps
- Report generator with Markdown output

**Model Evaluation:**
- Extend `ragas_txt_pipeline_evaluation.py` with `--model` parameter
- Parallel-safe execution (one model at a time)
- Aggregation script for cross-model comparison

---

### Success Criteria

**Part 1: Relation Deduplication**
- [ ] 25-40% relation reduction on parallel extraction
- [ ] Type synonyms merged correctly
- [ ] Entity references remapped to canonical names
- [ ] Symmetric relations deduplicated

**Part 2: Pipeline Monitoring**
- [ ] All pipeline stages emit structured metrics
- [ ] JSON report with complete pipeline trace
- [ ] Markdown summary for human review

**Part 3: Model Evaluation**
- [ ] 5+ models evaluated on same dataset
- [ ] Comparison matrix: Quality vs Speed vs Size
- [ ] Clear recommendation for production model

---

### References
- [TD-063: Relation Deduplication](../technical-debt/TD-063_RELATION_DEDUPLICATION.md)
- [SPRINT_43_PLAN.md](SPRINT_43_PLAN.md) - Entity Deduplication baseline
- [ADR-044: Multi-Criteria Entity Deduplication](../adr/ADR-044_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md)

### Sprint 43 Reference (OHNE Relation Dedup)
| Metric | Value |
|--------|-------|
| Samples | 10 |
| Input Chars | 68,126 |
| Chunks | 18 |
| Entities (raw → dedup) | 346 → 311 (10.1%) |
| Relations (NICHT dedupliziert!) | 287 |
| Total Time | 2802.6s (~47 min) |

**Erwartung nach Sprint 44:**
- Relations nach Dedup: ~180-200 (25-40% Reduktion)
- Neue Baseline mit qwen3:32b erforderlich

---

## Sprint 45: Domain-Specific Prompt Optimization mit DSPy 🔄
**Ziel:** Admin UI für Domain-Training + Automatische Prompt-Optimierung + LLM-Gruppierung

**Start:** 2025-12-12
**Status:** IN PROGRESS

**Breakdown:**
| Feature | SP | Priority |
|---------|-----|----------|
| 45.1 Domain Registry in Neo4j | 3 | P0 |
| 45.2 DSPy Integration Service | 8 | P0 |
| 45.3 Domain Training API | 5 | P0 |
| 45.4 Domain Training Admin UI | 8 | P1 |
| 45.5 Training Progress & Logging | 3 | P1 |
| 45.6 Domain Classifier | 5 | P1 |
| 45.7 Upload Page Domain Suggestion | 5 | P1 |
| 45.8 Fallback Generic Prompt | 2 | P2 |
| 45.9 Domain Auto-Discovery | 5 | P1 |
| 45.10 LLM-Grouped Ingestion | 3 | P1 |
| 45.11 Training Data Augmentation | 5 | P1 |
| 45.12 Metric Configuration UI | 3 | P1 |
| 45.13 E2E Tests | 3 | P2 |
| **Total** | **58** | |

### Deliverables
- Admin UI für Domain-Training (Name, Description, LLM Model, Dataset)
- DSPy Integration für automatische Prompt-Optimierung
- Domain Registry in Neo4j (nutzt bestehende Infrastruktur)
- Automatische Domain-Klassifikation bei Document Upload
- Generischer Fallback-Prompt für unbekannte Domains
- **Domain Auto-Discovery**: 3-10 Sample-Dokumente hochladen → LLM generiert Titel/Description
- **LLM-Grouped Ingestion**: Batch-Uploads nach LLM gruppieren für optimales Model Loading
- **Training Data Augmentation**: LLM generiert zusätzliche Samples aus 5-10 Seed-Samples
- **Metric Configuration**: Preset-Auswahl (F1/Recall/Precision) + Entity/Relation Gewichtung

### Key Decisions
- **Neo4j statt SQLite** - Nutzt bestehende Infrastruktur, keine neue DB
- **DSPy nur für Training** - Optimierte Prompts werden extrahiert und statisch gespeichert
- **Kein DSPy in Production** - Keine zusätzliche Runtime-Dependency
- **Domain = Prompt + Few-Shots** - Jede Domain hat eigene optimierte Prompts
- **Embedding-basierte Klassifikation** - Domain-Description → Embedding → Cosine Similarity
- **Single-Domain per Document** - Ein Dokument gehört zu genau einer Domain

### Technical Tasks
- Neo4j Schema für Domain + TrainingLog Nodes
- DSPyOptimizer mit Ollama Backend
- Background Task für Training mit Progress Logging
- DomainClassifier mit BGE-M3 Embeddings
- 3-Step Wizard UI (Config → Dataset → Training)
- GroupedIngestionProcessor für Batch-Uploads
- Auto-Discovery LLM-Prompt

### Success Criteria
- [ ] Domains können per UI erstellt und trainiert werden
- [ ] DSPy optimiert Prompts automatisch (Entity + Relation)
- [ ] Training-Progress in Echtzeit sichtbar
- [ ] Documents werden automatisch zur passenden Domain klassifiziert
- [ ] Fallback zu generischem Prompt bei niedriger Confidence (<50%)
- [ ] Auto-Discovery generiert sinnvolle Domain-Vorschläge aus Samples
- [ ] Batch-Uploads werden nach LLM gruppiert verarbeitet
- [ ] Data Augmentation generiert valide Samples aus 5-10 Seeds
- [ ] Metric Configuration erlaubt Preset-Auswahl + Gewichtung

### References
- [SPRINT_45_PLAN.md](SPRINT_45_PLAN.md)
- [DSPy Documentation](https://dspy.ai/)
- ADR-045: Domain-Specific Extraction Strategy (TBD)

---

## Sprint 46+: Backlog Candidates 📋
**Candidates:**
| Feature | SP | Source |
|---------|-----|--------|
| JWT Authentication Frontend | 13 | Backlog |
| Learned RRF Weights | 8 | Backlog |
| Conversation Search UI | 8 | Backlog |
| NuExtract Model Evaluation | 5 | Backlog |
| Qwen3:8b-Q4_K_M Benchmark | 3 | Backlog |
| Reranking in Container (TD-059) | 3 | Tech Debt |
| Unified Chunk IDs (TD-060) | 5 | Tech Debt |
| Ollama GPU Docker Config (TD-061) | 3 | Tech Debt |

---

## Backlog: Future Enhancements

### High Priority
- Advanced Query Decomposition (Tree-of-Thought)
- Multi-Modal RAG (Images, Tables)
- Fine-Tuning von Retrieval Models
- Security Audit & Penetration Testing

### Medium Priority
- Query Analytics Dashboard
- A/B Testing Framework
- Multi-Tenancy Support
- Backup & Disaster Recovery

### Low Priority
- Additional MCP Servers (Slack, Jira)
- Voice Interface Integration
- Mobile API Optimization
- Internationalization (i18n)

---

## Definition of Done (DoD)

- [ ] Code Review abgeschlossen
- [ ] Unit Tests Coverage >80%
- [ ] Integration Tests erfolgreich
- [ ] Documentation aktualisiert
- [ ] Performance-Anforderungen erfüllt
- [ ] Security-Review bestanden
