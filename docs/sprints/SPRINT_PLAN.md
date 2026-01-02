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

## Sprint 45: Domain-Specific Prompt Optimization mit DSPy ✅ (COMPLETE 2025-12-12)
**Ziel:** Admin UI für Domain-Training + Automatische Prompt-Optimierung + LLM-Gruppierung

**Start:** 2025-12-12
**End:** 2025-12-12
**Status:** COMPLETE

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

## Sprint 46: Conversation UI & Domain Auto-Discovery ✅ (COMPLETE 2025-12-16)
**Ziel:** Chat-Style Conversation UI + Transparentes Reasoning + Domain Auto-Discovery

**Start:** 2025-12-15
**End:** 2025-12-16
**Status:** COMPLETE

**Breakdown:**
| Feature | SP | Priority |
|---------|-----|----------|
| 46.1 Chat-Style Layout | 8 | P0 |
| 46.2 Transparent Reasoning Panel | 13 | P0 |
| 46.3 Bug Fix: Duplicate History | 2 | P0 |
| 46.4 Document-based Domain Discovery | 8 | P1 |
| 46.5 Integration with Domain Wizard | 3 | P1 |
| 46.6 Manual Domain Testing | 5 | P1 |
| 46.7 Admin UI Improvements | 5 | P2 |
| 46.8 Admin Area Consolidation | 8 | P2 |
| **Total** | **52** | |

### Deliverables
- Chat-style conversation UI (history scrolls up, input at bottom)
- Expandable "Reasoning" panel per message (like ChatGPT)
- Show retrieval steps: Intent → Qdrant → BM25 → Neo4j → Redis → RRF
- Domain auto-discovery from 1-3 uploaded documents
- Admin UI consolidated into single dashboard page
- Bug fix: Remove duplicate SessionSidebar components

### Key Changes
- **SearchResultsPage** → **ConversationView** (major refactor)
- **SSE Stream** → Add retrieval step events, intent events
- **Admin UI** → Consolidate multiple pages into sections

### Success Criteria
- [x] Conversation flows upward, input fixed at bottom
- [x] Reasoning panel shows all backend queries with timing
- [x] Domain discovery suggests sensible title/description from samples
- [x] At least one domain fully tested with documented results
- [x] No duplicate SessionSidebar components

### References
- [SPRINT_46_PLAN.md](SPRINT_46_PLAN.md)

---

## Sprint 48: Real-Time Thinking Phase Events ✅ (COMPLETE 2025-12-16)
**Ziel:** Echtzeit-Anzeige von LLM-Thinking-Events, Request Timeout & Cancel

**Start:** 2025-12-16
**End:** 2025-12-16
**Status:** COMPLETE

**Breakdown:**
| Feature | SP | Status |
|---------|-----|--------|
| 48.1 Thinking Event Streaming via SSE | 8 | ✅ DONE |
| 48.2 Real-Time Thinking Display UI | 13 | ✅ DONE |
| 48.3 Request Timeout & Cancellation | 8 | ✅ DONE |
| 48.4 Elapsed Time Display | 5 | ✅ DONE |
| **Total** | **34** | |

### Deliverables
- SSE thinking event stream from LLM responses
- Real-time thinking indicator in conversation UI
- Elapsed time display during generation
- Request timeout configuration
- Cancel request button with cleanup

### Technical Tasks
- Ollama thinking event parsing
- SSE stream for thinking chunks
- React UI for real-time thinking display
- Timeout handler with cleanup
- Cancel request implementation

### Success Criteria
- [x] Thinking events stream in real-time
- [x] Elapsed time updates every 100ms
- [x] Request cancellation works cleanly
- [x] Timeout cleanup prevents resource leaks

### References
- [SPRINT_48_PLAN.md](SPRINT_48_PLAN.md)

---

## Sprint 49: Dynamic UX & Knowledge Graph Deduplication ✅
**Ziel:** Dynamic model selection, semantic entity/relation deduplication, provenance tracking

**Breakdown:**
| Feature | SP |
|---------|-----|
| 49.1 Dynamic LLM Selection from Ollama | 8 |
| 49.2 Graph Relationship Type Multiselect | 8 |
| 49.3 Historical Phase Events Display | 13 |
| 49.4 Fix Indexing Progress Inconsistency | 3 |
| 49.5 Add source_chunk_id to Relationships | 13 |
| 49.6 Index Consistency Validation | 8 |
| 49.7 Semantic Relation Deduplication (Embeddings) | 13 |
| 49.8 Redis-based Synonym Overrides | 5 |
| 49.9 Migrate Entity Dedup to BGE-M3 | 8 |
| **Total** | **79** |

### Deliverables
- Dynamic model discovery API (Ollama)
- Dynamic relationship type discovery (Neo4j)
- Historical phase events in conversation view
- Fixed indexing progress messages
- source_chunk_id provenance tracking
- Index consistency validation service
- Semantic relation deduplication (BGE-M3 embeddings)
- Redis-based synonym management
- Entity deduplication with BGE-M3 (remove sentence-transformers)

### Technical Tasks
- Ollama model listing API
- Neo4j relationship type query
- Phase events lazy loading
- Provenance migration script
- Consistency validation endpoint
- SemanticRelationDeduplicator implementation
- HybridRelationDeduplicator with Redis
- Entity dedup migration to BGE-M3

### Success Criteria
- No hardcoded model/relationship type lists
- Phase events viewable in history
- All relationships have source_chunk_id
- <5% orphaned entities/chunks
- >90% relation duplicate reduction
- sentence-transformers dependency removed

### References
- [SPRINT_49_PLAN.md](SPRINT_49_PLAN.md)
- [TD-048: Graph Extraction Provenance](../technical_debt/TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md)
- [TD-063: Relation Deduplication](../technical_debt/TD-063_RELATION_DEDUPLICATION.md)
- [TD-059: Reranking Dependencies](../technical_debt/TD-059_RERANKING_DEPENDENCY_SIZE.md)

---

## Sprint 50: Comprehensive E2E Test Coverage 📋 (PLANNED 2025-12-17)
**Ziel:** Complete E2E test coverage for all critical user journeys with Playwright

**Breakdown:**
| Feature | SP |
|---------|-----|
| 50.1 Domain Creation Workflow | 8 |
| 50.2 Upload Page Domain Classification | 5 |
| 50.3 Graph Exploration Workflow | 13 |
| 50.4 Chat Streaming & Citations | 8 |
| 50.5 Session Management | 8 |
| 50.6 Community Detection Workflow | 8 |
| 50.7 Cost Monitoring Workflow | 5 |
| 50.8 Health Monitoring | 3 |
| 50.9 Indexing Pipeline Monitoring | 8 |
| 50.10 Test Infrastructure Improvements | 6 |
| **Total** | **72** |

### Deliverables
- 9 new E2E test files (total: 12 E2E tests)
- Test fixtures for training datasets, documents, graph data
- CI/CD pipeline configuration (.github/workflows/e2e.yml)
- Complete test documentation
- 100% critical user journey coverage

### Technical Tasks
- Domain creation workflow test
- Upload page with AI classification test
- Graph exploration and visualization test
- Chat streaming with citations test
- Session management (create, rename, share, delete) test
- Community detection and analysis test
- Cost dashboard and LLM config test
- Health monitoring test
- Indexing pipeline SSE monitoring test
- Test infrastructure improvements (parallel execution, CI/CD)

### Success Criteria
- All 9 new E2E tests implemented and passing
- Total: 12 E2E tests (3 existing + 9 new)
- 100% coverage of critical user journeys
- CI/CD pipeline configured and green
- Tests run reliably (>99% pass rate)
- Performance targets met (< 15 min suite)
- Zero flaky tests

### Parallel Execution Strategy
- **Team A (Backend Agent):** Domain, Upload, Graph (26 SP)
- **Team B (Frontend Agent):** Chat, Sessions, Communities (24 SP)
- **Team C (API Agent):** Monitoring, Infrastructure (22 SP)
- **Duration:** 8 days with 3 parallel teams

### References
- [SPRINT_50_PLAN.md](SPRINT_50_PLAN.md)
- [USER_JOURNEYS_AND_TEST_PLAN.md](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md)
- Existing E2E tests: document_ingestion, hybrid_search_quality, sprint49_features

---

## Sprint 51: Unutilized Features E2E Test Coverage 📋 (PLANNED TBD)
**Ziel:** E2E test coverage for implemented but unused features from Sprints 30-49 and ADRs

**Breakdown:**
| Feature | SP | Status |
|---------|-----|--------|
| 51.1 Bi-Temporal Queries / Graph Time Travel | 13 | ✅ Implemented (Sprint 39), Needs E2E |
| 51.2 Secure Shell Sandbox Execution | 8 | ✅ Implemented (Sprint 40), Needs E2E |
| 51.3 Dynamic LLM Model Configuration | 5 | ✅ Implemented (Sprint 49.1), Needs E2E |
| 51.4 Graph Relationship Type Filtering | 5 | ✅ Implemented (Sprint 49.2), Needs E2E |
| 51.5 Historical Phase Events Display | 3 | ✅ Implemented (Sprint 49.3), Needs E2E |
| 51.6 Index Consistency Validation UI | 5 | ⚠️ Backend Only (Sprint 49.6), Needs Frontend + E2E |
| 51.7 Mem0 User Preference Learning (OPTIONAL) | 13 | ⚠️ Designed (ADR-025), NOT Implemented |
| **Total (without Mem0)** | **39** | |
| **Total (with Mem0)** | **52** | |

### Deliverables
- 5-6 new E2E test files for unutilized features
- Frontend UI components:
  - TimeTravelControls.tsx + VersionHistoryPanel.tsx (Time Travel)
  - CodeAnalysisPage.tsx + SandboxExecutionLog.tsx (Sandbox)
  - ConsistencyReport.tsx (Index Validation)
- Test fixtures for temporal data, code repositories
- Updated USER_JOURNEYS_AND_TEST_PLAN.md with 7 new journeys (12-18)
- Optional: Complete Mem0 implementation if time permits

### Technical Tasks
- Graph time travel workflow test (temporal queries, version history, rollback)
- Secure shell sandbox test (Bubblewrap isolation, security boundaries)
- Dynamic LLM model discovery test (Ollama API, filtering logic)
- Graph relationship filtering test (multiselect, persistence)
- Historical phase events test (phase tracking, timing accuracy)
- Index consistency validation test (cross-system validation, re-indexing)
- OPTIONAL: Mem0 user preference learning implementation + test

### Success Criteria
- All 5 critical E2E tests passing (51.1-51.5)
- Feature 51.6 completed (consistency UI + test)
- Mem0 decision documented (implement or defer to Sprint 52)
- Temporal queries feature flag toggleable via UI
- Sandbox security boundaries validated
- Performance targets met:
  - Temporal queries: <500ms (per ADR-042)
  - Sandbox overhead: <200ms (per ADR-043)
- All tests run reliably (3x consecutive pass)
- Code coverage >80%

### ADR References
- **ADR-042:** Bi-Temporal Queries Opt-In Strategy (Sprint 39)
- **ADR-043:** Secure Shell Sandbox with Bubblewrap (Sprint 40)
- **ADR-025:** mem0 User Preference Learning (Sprint 21 planned, not implemented)

### Sprint References
- **Sprint 39:** Temporal queries implementation (440 lines, 6 API endpoints)
- **Sprint 40:** Bubblewrap sandbox implementation (deepagents integration)
- **Sprint 49.1:** Dynamic LLM model discovery
- **Sprint 49.2:** Graph relationship multiselect
- **Sprint 49.3:** Historical phase events display
- **Sprint 49.6:** Index consistency validation backend

### References
- [SPRINT_51_PLAN.md](SPRINT_51_PLAN.md)
- [USER_JOURNEYS_AND_TEST_PLAN.md](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md) - Journeys 12-18
- [ADR-042: Bi-Temporal Queries](../adr/ADR-042_BITEMPORAL_OPT_IN_STRATEGY.md)
- [ADR-043: Secure Shell Sandbox](../adr/ADR-043_SECURE_SHELL_SANDBOX.md)
- [ADR-025: mem0 User Preference Layer](../adr/ADR-025-mem0-user-preference-layer.md)

---

## Sprint 53: Quick Wins - Circular Dependencies & Admin Refactoring ✅ (COMPLETE 2025-12-19)
**Ziel:** Auflösung zirkulärer Dependencies + Admin.py Split

**Start:** 2025-12-18
**End:** 2025-12-19
**Status:** COMPLETE

**Breakdown:**
| Feature | SP | Status |
|---------|-----|--------|
| 53.1 Circular Dependency Fix: Admin → CommunitySummarizer | 5 | ✅ DONE |
| 53.2 Circular Dependency Fix: Extraction Factory Self-Import | 3 | ✅ DONE |
| 53.3 Admin.py Split: Indexing Module | 8 | ✅ DONE |
| 53.4 Admin.py Split: Cost Module | 5 | ✅ DONE |
| 53.5 Admin.py Split: LLM Config Module | 5 | ✅ DONE |
| 53.6 Admin.py Split: Graph Analytics Module | 5 | ✅ DONE |
| 53.7 Dead Code Removal | 3 | ✅ DONE |

### Deliverables
- Protocol-basierte Dependency Injection für LLM Config
- 4 neue Admin-Module (admin_indexing, admin_costs, admin_llm, admin_graph)
- admin.py reduziert von 4796 LOC auf ~500 LOC
- Singleton Registry für Graph Components
- Dead Code entfernt (Vulture-Findings)

### Success Criteria
- ✅ 0 zirkuläre Dependencies
- ✅ admin.py < 500 LOC
- ✅ 4 neue Admin-Module erstellt
- ✅ Alle Tests passieren

### References
- [SPRINT_53_PLAN.md](SPRINT_53_PLAN.md)
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)

---

## Sprint 54: langgraph_nodes.py Modularization ✅ (COMPLETE 2025-12-19)
**Ziel:** Split langgraph_nodes.py (2227 LOC) in modulares nodes/ Package

**Start:** 2025-12-19
**End:** 2025-12-19
**Status:** COMPLETE

**Breakdown:**
| Feature | SP | Status |
|---------|-----|--------|
| 54.1 Create nodes/ Package Structure | 3 | ✅ DONE |
| 54.2 Extract memory_management Node | 5 | ✅ DONE (150 LOC) |
| 54.3 Extract document_parsers Node | 8 | ✅ DONE (410 LOC) |
| 54.4 Extract image_enrichment Node | 6 | ✅ DONE (302 LOC) |
| 54.5 Extract adaptive_chunking Node | 6 | ✅ DONE (555 LOC) |
| 54.6 Extract vector_embedding Node | 5 | ✅ DONE (262 LOC) |
| 54.7 Extract graph_extraction Node | 8 | ✅ DONE (551 LOC) |
| 54.8 Legacy Wrapper & OPL Update | 3 | ✅ DONE (65 LOC facade) |

### Deliverables
- **nodes/__init__.py** - Package entry with all exports (72 LOC)
- **nodes/models.py** - Shared dataclasses SectionMetadata, AdaptiveChunk (65 LOC)
- **nodes/memory_management.py** - RAM/VRAM checks (150 LOC)
- **nodes/document_parsers.py** - Docling parsing (410 LOC)
- **nodes/image_enrichment.py** - VLM image processing (302 LOC)
- **nodes/adaptive_chunking.py** - Section-aware chunking (555 LOC)
- **nodes/vector_embedding.py** - BGE-M3 embeddings + Qdrant (262 LOC)
- **nodes/graph_extraction.py** - Neo4j entities/relations (551 LOC)
- **langgraph_nodes.py** - 65 LOC facade (down from 2227 LOC)

### Key Metrics
| Metric | Before | After |
|--------|--------|-------|
| langgraph_nodes.py | 2227 LOC | 65 LOC |
| Largest module | 2227 LOC | 555 LOC (adaptive_chunking) |
| Total node modules | 1 | 8 |
| Backward compatibility | N/A | 100% (facade pattern) |

### Success Criteria
- ✅ langgraph_nodes.py < 100 LOC (65 LOC achieved)
- ✅ 8 neue Node-Module in nodes/ Package
- ✅ Alle Imports funktionieren (direkt und via Facade)
- ✅ REFACTORING_OPL.md aktualisiert (OPL-003, OPL-004, DC-002)
- ✅ Keine neuen zirkulären Dependencies

### References
- [SPRINT_54_PLAN.md](SPRINT_54_PLAN.md)
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md)

---

## Sprint 55: lightrag_wrapper.py Modularization ✅ (COMPLETE 2025-12-19)
**Ziel:** Split lightrag_wrapper.py (1823 LOC) in modulares lightrag/ Package

**Start:** 2025-12-19
**End:** 2025-12-19
**Status:** COMPLETE

**Breakdown:**
| Feature | SP | Status |
|---------|-----|--------|
| 55.1 Create lightrag/ Package Structure | 3 | ✅ DONE |
| 55.2 Extract types.py (Data Models) | 3 | ✅ DONE (155 LOC) |
| 55.3 Extract initialization.py | 5 | ✅ DONE (210 LOC) |
| 55.4 Extract ingestion.py | 8 | ✅ DONE (450 LOC) |
| 55.5 Extract converters.py | 5 | ✅ DONE (245 LOC) |
| 55.6 Extract neo4j_storage.py | 8 | ✅ DONE (340 LOC) |
| 55.7 Extract client.py (Facade) | 5 | ✅ DONE (295 LOC) |
| 55.8 OPL Update & Cleanup | 3 | ✅ DONE (47 LOC facade) |

### Deliverables
- **lightrag/__init__.py** - Package entry with all exports (110 LOC)
- **lightrag/types.py** - QueryMode, LightRAGConfig, dataclasses (155 LOC)
- **lightrag/initialization.py** - Instance creation, embedding setup (210 LOC)
- **lightrag/converters.py** - Format conversion utilities (245 LOC)
- **lightrag/ingestion.py** - Document insertion operations (450 LOC)
- **lightrag/neo4j_storage.py** - Neo4j storage operations (340 LOC)
- **lightrag/client.py** - LightRAGClient facade class (295 LOC)
- **lightrag_wrapper.py** - 47 LOC facade (down from 1823 LOC)

### Key Metrics
| Metric | Before | After |
|--------|--------|-------|
| lightrag_wrapper.py | 1823 LOC | 47 LOC |
| Largest module | 1823 LOC | 450 LOC (ingestion) |
| Total lightrag modules | 1 | 7 |
| Backward compatibility | N/A | 100% (facade pattern) |

### Success Criteria
- ✅ lightrag_wrapper.py < 50 LOC (47 LOC achieved)
- ✅ 7 neue Module in lightrag/ Package
- ✅ Alle Imports funktionieren (direkt und via Facade)
- ✅ REFACTORING_OPL.md aktualisiert (OPL-005, DC-003)
- ✅ Keine neuen zirkulären Dependencies

### References
- [SPRINT_55_PLAN.md](SPRINT_55_PLAN.md)
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md)

---

## Sprint 56: domains/ Package Migration ✅ (COMPLETE 2025-12-19)
**Ziel:** Migration to DDD-inspired domains/ architecture per ADR-046

**Status:** COMPLETE

**Key Changes:**
- Introduced `src/domains/` with bounded contexts:
  - `knowledge_graph/` - Graph operations, communities, relations
  - `llm_integration/` - LLM proxy, cost tracking, routing
  - `vector_search/` - Qdrant, BM25, hybrid search
  - `memory/` - Redis, conversation, graphiti
- Established Protocol-based interfaces
- Implemented DI Container pattern

### References
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [SPRINT_56_PLAN.md](SPRINT_56_PLAN.md)

---

## Sprint 57: Protocol Definitions & Tool Framework ✅ (COMPLETE 2025-12-19)
**Ziel:** Protocol-basierte Interfaces und ToolExecutor Framework

**Status:** COMPLETE

**Key Deliverables:**
- Protocol definitions for all major components
- ToolExecutor Protocol for agent tools
- Updated DI Container with protocol support
- Removed tight coupling via interface segregation

### References
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [SPRINT_57_PLAN.md](SPRINT_57_PLAN.md)

---

## Sprint 58: Test Coverage & Final Cleanup ✅ (COMPLETE 2025-12-20)
**Ziel:** Achieve ≥80% test coverage, resolve all OPL entries

**Status:** COMPLETE

**Breakdown:**
| Feature | SP | Status |
|---------|-----|--------|
| 58.1 OPL Resolution | 8 | ✅ DONE |
| 58.2 Unit Test Suite Expansion | 13 | ✅ DONE |
| 58.3 API Test Fixtures | 8 | ✅ DONE |
| 58.4 Integration Tests | 8 | ✅ DONE |
| 58.5 Code Deprecation Markers | 5 | ✅ DONE |
| 58.6 Coverage Report & Benchmarks | 3 | ✅ DONE |

### Final Metrics
| Metric | Value |
|--------|-------|
| Total Tests | 2246 passed, 111 skipped |
| Test Runtime | ~3:07 min |
| Coverage (Targeted Modules) | 20-60% (admin APIs, ingestion) |
| OPL Entries | 0 remaining (all resolved) |

### Key Achievements
- Created `tests/unit/api/v1/conftest.py` with specialized test fixtures
- Fixed Python module caching issues in tests (patch-before-import pattern)
- Documented 111 skipped tests for Sprint 59 follow-up
- All deprecated code cleaned up per ADR-046

### References
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [SPRINT_58_PLAN.md](SPRINT_58_PLAN.md)
- [TESTING_REPORT_SPRINT58.md](TESTING_REPORT_SPRINT58.md)

---

## Sprint 59: Agentic Capabilities, Lifecycle & Hybrid Memory 🚧 (PLANNED)
**Ziel:** Evolve to Agentic Platform with Tool Use, Lifecycle, and Hybrid Memory Architecture

**Branch:** `sprint-59-agentic-capabilities`
**Estimated Duration:** 7-9 Tage
**Total Story Points:** 76 SP

### Overview
Sprint 59 transforms AEGIS RAG from a tool-augmented system into a **durable, auditable Agentic Platform** with:
- Deterministic Agent Lifecycle (AgentRun, Resume, Replay)
- Tool Use Framework (Bash/Python + Sandboxing)
- Task/Todo Tracking as First-Class-Entity
- Knowledge Graph Community Detection Fix
- **Hybrid Memory Architecture:**
  - Deterministic Agent Memory Core
  - **mem0 as optional, containerized Long-Term Memory Backend**

### Feature Breakdown
| # | Feature | SP | Priority |
|---|---------|-----|----------|
| 59.1 | Community Detection Fix | 8 | P0 |
| 59.2 | Tool Use Framework | 13 | P0 |
| 59.3 | Bash Execution Tool | 8 | P1 |
| 59.4 | Python Execution Tool | 8 | P1 |
| 59.5 | Sandboxing Layer | 10 | P0 |
| 59.6 | Agent Identity & Lifecycle | 10 | P0 |
| 59.7 | Agent Memory Core | 7 | P0 |
| 59.8 | **mem0 Backend Adapter** | 5 | P1 |
| 59.9 | Task/Todo Tracking | 4 | P1 |
| 59.10 | Agentic Search (Durable) | 13 | P1 |

### mem0 Integration Highlights

**Docker Deployment:**
```yaml
mem0:
  image: mem0ai/mem0:latest
  ports: ["8081:8080"]
  environment:
    - VECTOR_STORE_PROVIDER=qdrant
    - LLM_PROVIDER=ollama
    - OLLAMA_MODEL=nemotron3nano:30b
    - EMBEDDER_MODEL=bge-m3
```

**Architecture Principles:**
- ✅ Agent Core remains deterministic
- ✅ mem0 is **service**, not control mechanism
- ✅ No vendor lock-in (Protocol-based)
- ✅ Feature-flag enabled (`MEM0_ENABLED`)
- ✅ Reuses existing AEGIS stack (Qdrant, Ollama)

### Key Deliverables
- AgentRun entity with lifecycle management
- Tool Registry & Executor (OpenAI-compatible)
- Docker-based Sandbox with resource limits
- Agent Memory Core with policy-based writes
- **mem0 Backend Adapter** (optional, containerized)
- Task Tracking integrated in Agent State
- Durable Research Agent with LangGraph Checkpointing

### Success Criteria
- [ ] Community Detection funktioniert (entities have community_id)
- [ ] Tool Use Framework implementiert (Bash, Python sandboxed)
- [ ] Agent Lifecycle: create, resume, replay
- [ ] Hybrid Memory: Core + optional mem0 backend
- [ ] Task Tracking in AgentRun state
- [ ] Security Review bestanden (Sandbox isolation)
- [ ] E2E Tests für alle Features

### References
- [ADR-047: Hybrid Agent Memory](../adr/ADR-047-hybrid-agent-memory.md)
- [SPRINT_59_PLAN.md](SPRINT_59_PLAN.md)
- [mem0 GitHub](https://github.com/mem0ai/mem0)
- [mem0 Documentation](https://docs.mem0.ai)

---

## Sprint 60: Documentation Consolidation & Technical Investigations ✅
**Ziel:** Dokumentation konsolidieren, technische Voruntersuchungen

**Breakdown:**
| Feature | SP |
|---------|-----|
| 60.1 Core Documentation Consolidation | 13 |
| 60.2 GRAPHITI Temporal Queries Analysis | 8 |
| 60.3 Section Nodes Implementation Review | 3 |
| 60.4 TD-069: Multihop Endpoint Review | 3 |
| 60.5 TD-071: vLLM Investigation | 5 |
| 60.6 TD-072: Sentence-Transformers Reranking | 5 |
| 60.7 TD-073: Sentence-Transformers Embeddings | 5 |
| 60.8 Subdirectory Cleanup | 3 |

### Deliverables
- Konsolidierte Core-Dokumentation (7 Hauptdateien)
- GRAPHITI Temporal Queries Analyse
- vLLM Performance-Untersuchung
- Sentence-Transformers Evaluationen (Embeddings + Reranking)

### Success Criteria
- [ ] Dokumentation auf aktuellem Stand
- [ ] Technische Investigations abgeschlossen
- [ ] Entscheidungsgrundlage für Sprint 61 Performance-Optimierungen

### References
- [SPRINT_60_PLAN.md](SPRINT_60_PLAN.md)

---

## Sprint 61: Performance & Ollama Optimization ✅
**Ziel:** Native Sentence-Transformers, Cross-Encoder Reranking, Ollama Tuning

**Breakdown:**
| Feature | SP |
|---------|-----|
| 61.1 Native Sentence-Transformers Embeddings | 8 |
| 61.2 Cross-Encoder Reranking | 8 |
| 61.3 Ollama Configuration Tuning | 5 |
| 61.4 Deprecated Endpoint Cleanup | 3 |
| 61.5 Performance Testing & Documentation | 5 |

### Deliverables
- Native BGE-M3 Embeddings (3-5x faster, -60% VRAM)
- Cross-Encoder Reranking (50x faster: 120ms vs 2000ms)
- Optimierte Ollama-Konfiguration (+30% throughput)
- Entfernung von 5 deprecated multihop endpoints

### Success Criteria
- [ ] Query latency: -100ms (embeddings: -80ms, reranking: -20ms)
- [ ] Ingestion speed: +1500% (batch embeddings 16x faster)
- [ ] Ollama throughput: +30-50% (OLLAMA_NUM_PARALLEL=4)
- [ ] Code cleanup: Deprecated endpoints entfernt

### References
- [SPRINT_61_PLAN.md](SPRINT_61_PLAN.md)
- [ADR-024: BGE-M3 Embeddings](../adr/ADR_INDEX.md)

---

## Sprint 62 & 63: Section-Aware RAG & Multi-Turn Research ✅
**Ziel:** Section-Aware Citations, VLM Integration, Multi-Turn Research, Temporal Audit

**Duration:** 4-5 Wochen (2+3 Wochen)
**Total Story Points:** 93 SP (36 Sprint 62 + 57 Sprint 63)

**Sprint 62 Features (36 SP):**
| Feature | SP |
|---------|-----|
| 62.1 Section Graph Queries | 5 |
| 62.2 Multi-Section Vector Metadata | 3 |
| 62.3 VLM Image Integration | 5 |
| 62.4 Section-Aware Citations | 3 |
| 62.5 Hierarchical Section Queries | 2 |
| 62.6 Query Decomposition Engine | 3 |
| 62.7 Document Type Support Extension | 5 |
| 62.8 Community Detection Optimization | 3 |
| 62.9 Section Analytics API | 2 |
| 62.10 Research Backend | 6 |

**Sprint 63 Features (57 SP):**
| Feature | SP |
|---------|-----|
| 63.1 Multi-Turn Conversation Backend | 8 |
| 63.2 Temporal Audit Logging | 5 |
| 63.3 Redis Cache Layer | 3 |
| 63.4 Structured Output Support | 5 |
| 63.5 Community Detection UI | 3 |
| 63.6 E2E Test Coverage | 13 |
| 63.7 MCP Authentication & Security | 5 |
| 63.8 Research Mode UI | 8 |
| 63.9 Web Search Integration | 5 |
| 63.10 Tool Output Visualization | 2 |

### Deliverables
- Section-Aware Citation System (hierarchical references)
- VLM-based Image Processing (Docling CUDA + qwen3-vl:32b)
- Multi-Turn Conversation Memory (Redis-backed)
- Research Mode (multi-phase LLM orchestration)
- Web Search Integration (Tavily API)
- Comprehensive E2E Test Suite (111 Playwright tests)

### Success Criteria
- [ ] Section citations with hierarchy display (e.g., "Chapter 2 > Section 2.1")
- [ ] VLM image descriptions embedded in chunks
- [ ] Multi-turn context maintained across conversations
- [ ] Research mode with progress streaming
- [ ] Web search integrated into research workflow
- [ ] E2E test coverage >80% critical paths

### References
- [SPRINT_62_63_EXECUTION_PLAN.md](SPRINT_62_63_EXECUTION_PLAN.md)
- [SPRINT_62_PLAN.md](SPRINT_62_PLAN.md)
- [SPRINT_63_PLAN.md](SPRINT_63_PLAN.md)

---

## Sprint 64: Domain Training Optimization & Critical Bug Fixes ✅ (COMPLETE 2025-12-25)
**Ziel:** LLM Config Backend, Domain Training Fixes, Production Deployment

**Breakdown:**
| Feature | SP |
|---------|-----|
| 64.1 VLM-Chunking Integration | 3 |
| 64.2 Real DSPy MIPRO Implementation | 8 |
| 64.3 Domain Creation Validation | 3 |
| 64.4 Transactional Domain Operations | 3 |
| 64.5 Domain Training Validation Review | 2 |
| 64.6 Admin LLM Config Backend Integration | 13 |
| 64.7 E2E Testing Suite | 5 |

### Deliverables
- **Critical Bug Fixes:**
  - Admin UI LLM Config → Backend Integration (Redis persistence, 60s cache)
  - Domain Creation Validation (prevents invalid names, duplicates)
  - Transactional Domain Operations (all-or-nothing atomicity)
- **Domain Training Optimization:**
  - VLM-Chunking Integration (adaptive chunking uses VLM descriptions)
  - Real DSPy MIPRO (production-ready prompt optimization)
- **Production Deployment:**
  - Complete Docker Compose setup (Nginx + API + DBs)
  - Deployed to http://192.168.178.10 (DGX Spark)
  - E2E Testing (337/594 tests passed - 57% success)

### Success Criteria
- [x] Backend respects Admin UI model selection (was broken)
- [x] Invalid domain creation prevented (100% validation)
- [x] Domain creation atomic (no partial failures)
- [x] Image descriptions incorporated into chunks
- [x] DSPy MIPRO implemented (mock → real)
- [x] Production deployment functional
- [ ] **E2E test success rate >90%** (currently 57% - Sprint 65 target)

### References
- [SPRINT_64_PLAN.md](SPRINT_64_PLAN.md)
- [PRODUCTION_DEPLOYMENT_TEST_RESULTS.md](../../PRODUCTION_DEPLOYMENT_TEST_RESULTS.md)

---

## Sprint 65: CUDA GPU Acceleration + E2E Test Improvements ✅ (COMPLETED 2025-12-28)
**Ziel:** GPU-Beschleunigung, LLM Config Bug Fix, E2E Test Stabilisierung
**Status:** ✅ **ERFOLG** - Alle Hauptziele erreicht, 61% E2E Pass-Rate (0% → 61%)

**Breakdown:**
| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| 65.1 LLM Config Save Bug Fix | 3 | 🔴 CRITICAL | ✅ DONE |
| 65.2 CUDA Support für API Container | 8 | 🔴 CRITICAL | ✅ DONE |
| 65.3 E2E Tests OMNITRACKER Queries | 5 | 🟡 MEDIUM | ✅ DONE |
| 65.4 E2E Test Infrastructure Fix | 2 | 🔴 CRITICAL | ✅ DONE |

### Deliverables
- **CUDA GPU Acceleration:**
  - Created `docker/Dockerfile.api-cuda` mit NGC PyTorch 25.09 (CUDA 13.0, sm_121)
  - BGE-M3 embeddings on NVIDIA GB10 GPU: **10-80x speedup** (500-2000ms → 50-200ms)
  - VRAM usage: 2.12GB, device detection verified
- **LLM Config Bug Fixed:**
  - Admin UI can now save model configurations (was broken)
  - Frontend/backend schema mismatch resolved (`use_case` + `model_id`)
- **E2E Tests Improved:**
  - **Pass rate: 0% → 61%** (35/57 core tests passing)
  - Root cause: Stale Vite dev server (restarted → fixed)
  - Updated 42 test queries to OMNITRACKER domain
- **Technical Debt:**
  - TD-074: TypeScript strict mode temporarily disabled (re-enable in Sprint 66)

### Critical Findings
**22 E2E Tests Still Failing (39%):**
1. **Follow-up Questions (8 tests):** Backend not generating follow-ups → P0 Sprint 66
2. **Conversation History (5 tests):** Conversations not persisting → P0 Sprint 66
3. **OMNITRACKER Knowledge Base (9 tests):** Only 44 documents in Qdrant (19 PDFs not indexed) → P0 Sprint 66

### Success Criteria
- [x] CUDA GPU acceleration working (BGE-M3 on GPU, 2.12GB VRAM)
- [x] LLM config save functionality fixed
- [x] E2E test pass rate improved (0% → 61%)
- [x] OMNITRACKER test queries updated (42 queries)
- [ ] **E2E test pass rate >90%** → Sprint 66 objective

### References
- [SPRINT_65_REPORT.md](SPRINT_65_REPORT.md) - Comprehensive Sprint 65 documentation
- Commit: `4894b03` - docs(sprint65): Add comprehensive Sprint 65 report

---

## Sprint 66: E2E Test Stabilization & Critical Backend Fixes 🔄 (IN PROGRESS 2025-12-28)
**Ziel:** 100% E2E Test Pass Rate durch Backend Bug Fixes & Knowledge Base Completion
**Status:** 🔄 **IN PROGRESS** - Day 1: OMNITRACKER Document Indexing

**Breakdown:**
| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| 66.1 Fix Follow-up Questions Backend | 8 | 🔴 CRITICAL | 📋 PLANNED |
| 66.2 Fix Conversation History Persistence | 10 | 🔴 CRITICAL | 📋 PLANNED |
| 66.3 Index OMNITRACKER Documents | 3 | 🔴 CRITICAL | 🔄 IN PROGRESS |
| 66.4 Single Document Upload User Journey | 5 | 🟡 MEDIUM | 📋 PLANNED |
| 66.5 Re-enable TypeScript Strict Mode (TD-074) | 3 | 🟡 MEDIUM | 📋 PLANNED |

### Deliverables
- **Backend Fixes (Features 66.1 & 66.2):**
  - Follow-up question generation with LLM + Redis caching
  - Conversation history persistence (Redis/PostgreSQL)
  - API endpoints: `/api/v1/history`, `/api/v1/history/{session_id}`
  - Auto-generated conversation titles from first message
  - Search functionality (by title and content)
- **Knowledge Base (Feature 66.3):**
  - Index all 19 OMNITRACKER PDFs (66MB) into Qdrant
  - Target: 500-2000 chunks (currently only 44 documents)
  - Namespace: `omnitracker`
- **Admin UI (Feature 66.4):**
  - Single document upload with progress streaming
  - SSE progress events: Upload → Parse → Chunk → Embed → Index
  - E2E test for complete upload-to-search user journey
- **Code Quality (Feature 66.5):**
  - Re-enable TypeScript strict mode
  - Fix conditional JSX type errors
  - Upgrade @types/react to latest

### Success Criteria
- [ ] **E2E test pass rate = 100%** (57/57 core tests passing)
  - [ ] Fix 8 follow-up question tests (Feature 66.1)
  - [ ] Fix 5 conversation history tests (Feature 66.2)
  - [ ] Fix 9 OMNITRACKER retrieval tests (Feature 66.3)
- [ ] All 19 OMNITRACKER PDFs indexed (500+ chunks in Qdrant)
- [ ] Single document upload working (<3 minutes per PDF)
- [ ] TypeScript strict mode enabled (no type errors)
- [ ] All features have E2E tests

### Timeline
**Week 1 (Days 1-3):**
- Day 1: Feature 66.3 - Index OMNITRACKER documents
- Day 2-3: Feature 66.1 - Fix follow-up questions backend

**Week 2 (Days 4-7):**
- Day 4-6: Feature 66.2 - Fix conversation history persistence
- Day 7: Feature 66.4 - Single document upload user journey

**Week 3 (Day 8-9):**
- Day 8: Feature 66.5 - Re-enable TypeScript strict mode
- Day 9: Sprint review, full E2E test suite (594 tests), Sprint 66 report

### References
- [SPRINT_66_PLAN.md](SPRINT_66_PLAN.md) - Detailed Sprint 66 planning
- Previous Sprint: [SPRINT_65_REPORT.md](SPRINT_65_REPORT.md)

---

## Sprint 67: Secure Shell Sandbox + Agents Adaptation + LLM Intent Classifier 📋 (PLANNED 2025-12-31)
**Ziel:** Deepagents integration, Tool-level adaptation framework, C-LARA intent classification
**Duration:** 12 days | **Story Points:** 75 SP | **Status:** ⏳ PLANNED

**Breakdown:**
| Feature | SP | Priority | Description |
|---------|-----|----------|-------------|
| 67.1 BubblewrapSandboxBackend | 3 | 🔴 HIGH | Linux sandbox implementation |
| 67.2 Deepagents Integration | 5 | 🔴 HIGH | LangChain-native agent harness |
| 67.3 Multi-Language CodeAct | 5 | 🟡 MEDIUM | Bash + Python execution |
| 67.4 Sandbox Testing & Docs | 2 | 🟡 MEDIUM | E2E tests + documentation |
| 67.5 Unified Trace & Telemetry | 8 | 🔴 HIGH | RAG pipeline logging |
| 67.6 Eval Harness | 10 | 🔴 HIGH | Automated quality gates |
| 67.7 Dataset Builder | 8 | 🟡 MEDIUM | Training data generation |
| 67.8 Adaptive Reranker v1 | 13 | 🔴 HIGH | T1 adaptation |
| 67.9 Query Rewriter v1 | 6 | 🟡 MEDIUM | T2 adaptation |
| 67.10 C-LARA Data Generation | 3 | 🔴 HIGH | 1000 examples with Qwen2.5:7b |
| 67.11 SetFit Model Training | 3 | 🔴 HIGH | Fine-tune classification model |
| 67.12 Intent Classifier Integration | 5 | 🔴 HIGH | Replace Semantic Router |
| 67.13 A/B Testing | 2 | 🟡 MEDIUM | Compare vs baseline |
| 67.14 Section Extraction Quick Wins | 7 | 🔴 HIGH | TD-078 Phase 1 (profiling, batch tokenization, regex) |

### Epic 1: Secure Shell Sandbox (deepagents) - 15 SP
- BubblewrapSandboxBackend with security isolation
- Multi-language support (Bash + Python)
- SandboxBackendProtocol compliance
- Integration with LangGraph agents

### Epic 2: Agents Adaptation (Paper 2512.16301) - 45 SP
**Tool-Level Adaptation (T1/T2):**
- Unified Trace & Telemetry for RAG pipeline monitoring
- Eval Harness with automated quality gates
- Dataset Builder for training data generation
- Adaptive Reranker v1 (intent-aware reranking weights)
- Query Rewriter v1 (query expansion and refinement)

**Note:** Agent-Level Adaptation (A1/A2) deferred to Sprint 68

### Epic 3: LLM Intent Classifier (C-LARA) - 13 SP (TD-079)
**Problem:** Semantic Router achieves only 60% accuracy (A/B tested)
**Solution:** C-LARA approach (LLM offline data generation + SetFit fine-tuning)
- Phase 1: Generate 1000 examples with Qwen2.5:7b (87-95% accuracy on benchmarks)
- Phase 2: Train SetFit classification model
- Phase 3: Integration and A/B testing vs Semantic Router
- **Target:** 85-92% accuracy improvement

### Epic 4: Section Extraction Performance (TD-078 Phase 1) - 7 SP
**Problem:** 9-15 minutes for medium PDFs (critical bottleneck)
**Quick Wins (2-3x speedup):**
- Profiling instrumentation
- Batch tokenization (30-50% faster)
- Regex pattern compilation (10-20% faster)
- Early exit conditions (5-10% faster)

### Deliverables
- Secure code execution in Bubblewrap sandbox
- Tool-level adaptation framework (reranker, query-rewriter)
- Intent classification accuracy: 60% → 85-92%
- Section extraction: 2-3x faster (112s → 40-50s for 146 texts)

### Success Criteria
- [ ] Bubblewrap sandbox passes security tests (no escapes)
- [ ] Multi-language CodeAct executes Bash + Python
- [ ] Eval Harness validates grounding, citations, format
- [ ] Adaptive Reranker improves precision by +5-10%
- [ ] Intent classifier achieves >85% accuracy (A/B test)
- [ ] Section extraction <50s for 146 texts

### References
- [SPRINT_67_PLAN.md](SPRINT_67_PLAN.md) - Detailed Sprint 67 planning
- [SPRINT_SECURE_SHELL_SANDBOX_v3.md](SPRINT_SECURE_SHELL_SANDBOX_v3.md)
- [SPRINT_AGENTS_ADAPTATION.md](SPRINT_AGENTS_ADAPTATION.md)
- [TD-079_LLM_INTENT_CLASSIFIER_CLARA.md](../technical-debt/TD-079_LLM_INTENT_CLASSIFIER_CLARA.md)
- [TD-078_SECTION_EXTRACTION_PERFORMANCE.md](../technical-debt/TD-078_SECTION_EXTRACTION_PERFORMANCE.md)

---

## Sprint 68: Production Hardening + Performance Optimization + Section Features 📋 (PLANNED 2025-01-15)
**Ziel:** E2E test completion, performance optimization, section community detection
**Duration:** 10 days | **Story Points:** 62 SP | **Status:** ⏳ PLANNED

**Breakdown:**
| Feature | SP | Priority | Description |
|---------|-----|----------|-------------|
| 68.1 E2E Test Fixes | 8 | 🔴 CRITICAL | Fix 594 tests to 100% pass rate |
| 68.2 Performance Test Infrastructure | 3 | 🔴 HIGH | Automated regression testing |
| 68.3 E2E Documentation | 2 | 🟡 MEDIUM | Test coverage documentation |
| 68.4 Section Extraction Parallelization | 11 | 🔴 HIGH | TD-078 Phase 2 (ThreadPoolExecutor, caching) |
| 68.5 BM25 Cache Auto-Refresh | 5 | 🔴 HIGH | TD-074 (cache validation, auto-refresh) |
| 68.6 Ingestion Performance Tuning | 5 | 🟡 MEDIUM | TD-070 (batch optimization, GPU management) |
| 68.7 Performance Monitoring | 2 | 🟡 MEDIUM | Prometheus metrics, alerts |
| 68.8 Section Community Detection | 10 | 🟡 MEDIUM | Louvain/Leiden algorithms |
| 68.9 Memory-Write Policy | 10 | 🟡 MEDIUM | T3 adaptation (selective memory storage) |
| 68.10 Tool-Execution Reward Loop | 8 | 🟡 MEDIUM | A1 adaptation (execution feedback) |

### Epic 1: E2E Test Completion - 13 SP
**Problem:** 57% E2E pass rate (337/594 tests passing)
**Solution:**
- Fix follow-up question tests (currently broken)
- Fix conversation history persistence
- Fix domain training timeouts
- Add performance regression tests
- Comprehensive documentation

**Target:** 100% E2E pass rate (594/594 tests)

### Epic 2: Performance Optimization - 21 SP
**Section Extraction (TD-078 Phase 2):** 5-10x total speedup
- Parallel processing with ThreadPoolExecutor
- LRU caching for heading patterns
- Target: 146 texts in 12-15s (vs 112s current)

**BM25 Cache (TD-074):** Fix cache discrepancy
- Cache validation on startup
- Auto-refresh if discrepancy >10%
- Namespace-aware caching

**Ingestion (TD-070):** Batch optimization
- Optimal batch sizes for embeddings
- GPU memory management
- Neo4j bulk writes

**Performance Targets:**
- Query latency P95: 500ms → 350ms (-30%)
- Section extraction: 8x speedup
- Memory usage: -30%
- Throughput: 40 QPS → 50 QPS (+25%)

### Epic 3: Section Community Detection - 10 SP
- Louvain/Leiden algorithms for section-based communities
- Integration with Maximum Hybrid Search
- Section-level context for graph reasoning
- Cypher query templates (15 production queries)

### Epic 4: Advanced Adaptation Features - 18 SP
**Memory-Write Policy (T3):**
- Selective memory storage (relevance-based filtering)
- Reduce memory bloat by 50-70%

**Tool-Execution Reward Loop (A1):**
- Execution feedback signals
- Adaptive tool selection
- Performance-based routing

### Deliverables
- 100% E2E test pass rate (594/594)
- Query latency: 500ms → 350ms P95
- Section extraction: 8x speedup (15min → 2min for large PDFs)
- BM25 cache consistency (10 → 43 documents)
- Section-based community detection integrated

### Success Criteria
- [ ] All 594 E2E tests passing (100%)
- [ ] Performance regression tests automated
- [ ] Section extraction <15s for 146 texts
- [ ] BM25 cache matches Qdrant count
- [ ] Query latency P95 <350ms
- [ ] Section communities detected and searchable

### References
- [SPRINT_68_PLAN.md](SPRINT_68_PLAN.md) - Detailed Sprint 68 planning
- [section_community_detection_queries.md](../technical/section_community_detection_queries.md)
- [TD-078_SECTION_EXTRACTION_PERFORMANCE.md](../technical-debt/TD-078_SECTION_EXTRACTION_PERFORMANCE.md)
- [TD-074_BM25_CACHE_DISCREPANCY.md](../technical-debt/TD-074_BM25_CACHE_DISCREPANCY.md)
- [TD-070_INGESTION_PERFORMANCE_TUNING.md](../technical-debt/TD-070_INGESTION_PERFORMANCE_TUNING.md)

---

## Sprint 69: Performance Optimization & Quality Improvements ✅ (COMPLETED 2026-01-01)
**Ziel:** Sprint 68 Bug Fixes, LLM Streaming, Model Selection, Production Monitoring
**Status:** ✅ **COMPLETED** - 9 Features, 53 SP

**Breakdown:**
| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| 69.1 Sprint 68 E2E Test Fixes | 8 | 🔴 CRITICAL | ✅ DONE |
| 69.2 LLM Generation Streaming (TTFT <100ms) | 8 | 🟡 MEDIUM | ✅ DONE |
| 69.3 Query Complexity-Based Model Selection | 5 | 🟡 MEDIUM | ✅ DONE |
| 69.4 Learned Reranker Weights (TrainingDataExtractor) | 8 | 🟡 MEDIUM | ✅ DONE |
| 69.5 Query Rewriter v2 (Abstractive + Extractive) | 8 | 🟡 MEDIUM | ✅ DONE |
| 69.6 Dataset Builder for Adaptation | 5 | 🟡 MEDIUM | ✅ DONE |
| 69.7 Production Monitoring & Observability | 5 | 🟡 MEDIUM | ✅ DONE |
| 69.8 Documentation & Deployment Guides | 3 | 🟢 LOW | ✅ DONE |
| 69.9 Container Updates & Rebuild | 3 | 🔴 CRITICAL | ✅ DONE |

**Total: 53 SP**

### Deliverables
- **Bug Fixes (69.1):**
  - Memory integration test fixed (GraphitiEngine mocking)
  - Domain training test fixed (proper await for async operations)
  - All Sprint 68 E2E tests now passing
- **LLM Streaming (69.2):**
  - TTFT reduced from 320ms to <100ms
  - Server-Sent Events for real-time token streaming
  - StreamingClient abstraction over AegisLLMProxy
- **Model Selection (69.3):**
  - Three-tier complexity detection (SIMPLE/MODERATE/COMPLEX)
  - Automatic model routing (nemotron-3-nano:latest → qwen3:8b → qwen2.5:7b)
  - Admin UI configuration support
- **Learned Weights (69.4):**
  - TrainingDataExtractor from retrieval traces
  - WeightOptimizer for reranker weight tuning
  - Integration with adaptation framework
- **Query Rewriter v2 (69.5):**
  - Abstractive query expansion (synonyms, paraphrases)
  - Extractive query simplification (core entities)
  - Standalone question generation for follow-ups
- **Dataset Builder (69.6):**
  - Converts retrieval traces to training datasets
  - Supports multiple formats (JSON, CSV, Parquet)
  - Validation and quality metrics
- **Production Monitoring (69.7):**
  - Prometheus metrics (queries, latency, errors, cache, memory)
  - 21 alert rules across 8 categories
  - Grafana dashboard with 14 panels
- **Documentation (69.8):**
  - Sprint 69 feature summaries (7 documents)
  - Manual testing guide (1,350 lines)
  - Deployment runbooks

### Success Criteria
- [x] TTFT <100ms (achieved 87ms avg)
- [x] Model selection by complexity working
- [x] Prometheus metrics exported
- [x] Grafana dashboard loaded
- [x] All Sprint 68 tests passing
- [x] Documentation complete

### References
- [SPRINT_69_CHECKLIST.md](SPRINT_69_CHECKLIST.md)
- [SPRINT_69_FEATURE_69.2_SUMMARY.md](SPRINT_69_FEATURE_69.2_SUMMARY.md)
- [SPRINT_69_FEATURE_69.7_SUMMARY.md](SPRINT_69_FEATURE_69.7_SUMMARY.md)
- Commit: `d1b6930` - docs(sprint69): Implement Feature 69.8

---

## Sprint 70: Deep Research & Tool Use Integration ✅ (COMPLETED 2026-01-02)
**Ziel:** Fix Deep Research + Integrate MCP Tools via ReAct Pattern
**Status:** ✅ **COMPLETED** - All 11 features implemented (37 SP)

**Breakdown:**
| Feature | SP | Priority | Status |
|---------|-----|----------|--------|
| **Phase 1: Deep Research Repair** | | | |
| 70.1 Deep Research Planner Fix (LLMTask API) | 3 | 🔴 CRITICAL | ✅ DONE |
| 70.2 Deep Research Searcher Reuse (CoordinatorAgent) | 5 | 🔴 CRITICAL | ✅ DONE |
| 70.3 Deep Research Synthesizer Reuse (AnswerGenerator) | 3 | 🔴 CRITICAL | ✅ DONE |
| 70.4 Deep Research Supervisor Graph Creation | 5 | 🔴 CRITICAL | ✅ DONE |
| **Phase 2: Tool Use Integration** | | | |
| 70.5 Tool Use in Normal Chat (ReAct Pattern) | 3 | 🟡 MEDIUM | ✅ DONE |
| 70.6 Tool Use in Deep Research (ReAct Pattern) | 2 | 🟡 MEDIUM | ✅ DONE |
| **Phase 3: Tool Configuration & Monitoring** | | | |
| 70.7 Admin UI Toggle for Tool Use | 3 | 🟡 MEDIUM | ✅ DONE |
| 70.8 E2E Tests for Tool Use User Journeys | 2 | 🟡 MEDIUM | ✅ DONE |
| 70.9 Tool Result Streaming (Phase Events) | 3 | 🟡 MEDIUM | ✅ DONE |
| 70.10 Tool Analytics & Monitoring (Prometheus) | 3 | 🟡 MEDIUM | ✅ DONE |
| 70.11 LLM-based Tool Detection (Adaptive Strategies) | 5 | 🟢 LOW | ✅ DONE |

**Total: 37 SP**

### Problem Analysis
**Deep Research was completely broken:**
- TypeError: `AegisLLMProxy.generate() got an unexpected keyword argument 'prompt'`
- ModuleNotFoundError: `No module named 'src.components.vector_search.hybrid'`
- Code duplication: Re-implemented search instead of reusing CoordinatorAgent
- Returns "No information found" instead of actual results

**Action Agent (Tool Use) not integrated:**
- Exists but isolated from main chat graph
- No ReAct pattern for tool conversations
- Cannot be called from normal queries or deep research

### Solution Architecture
**Supervisor Pattern with Component Reuse:**
```
planner → searcher → supervisor → [continue | synthesize]
            ↑           ↓
            └───────────┘  (multi-turn loop)
```

**ReAct Pattern for Tool Use:**
```
answer → should_use_tools? → [tools | END]
           ↓                    ↓
         END                  answer  (cycle back!)
```

### Deliverables
- **Phase 1 (70.1-70.4): Deep Research Repair**
  - [x] Planner uses correct LLMTask API (no TypeError)
  - [x] Searcher reuses CoordinatorAgent (no broken imports)
  - [x] Synthesizer reuses AnswerGenerator (no code duplication)
  - [x] ResearchSupervisorState TypedDict created
  - [x] research_graph.py with Supervisor pattern
  - [x] Integration with `/api/v1/research/query` endpoint
- **Phase 2 (70.5-70.6): Tool Use Integration**
  - [x] tools_node and should_use_tools in normal chat
  - [x] ReAct cycle edges (tools → answer → tools)
  - [x] research_tools_node in deep research
  - [x] Admin-configurable tool enablement (no feature flag)
- **Phase 3 (70.7-70.11): Configuration & Advanced Features**
  - [x] Admin UI toggle with Redis persistence (70.7)
  - [x] 8 integration tests for tool use flows (70.8)
  - [x] Phase event streaming for tool execution (70.9)
  - [x] Prometheus metrics: tool_executions_total, duration, active (70.10)
  - [x] LLM-based tool detection with 3 strategies (70.11)
  - [x] Editable marker lists in Admin UI (70.11)

### Success Criteria
- [x] Deep Research executes multi-turn queries without errors
- [x] CoordinatorAgent reuse eliminates code duplication
- [x] Comprehensive reports with citations generated
- [x] Tools callable from both normal chat and deep research
- [x] ReAct loop enables multi-turn tool conversations
- [x] <30s latency for 3-iteration deep research
- [x] <5s additional latency per tool call
- [x] Admin can toggle tools without service restart (60s hot-reload)
- [x] Tool execution tracked in Prometheus + Grafana
- [x] LLM-based detection works multilingually (German/English)

### Technical Debt Resolved
- TD-070-01: Deep Research broken LLM API → Fixed with LLMTask
- TD-070-02: Deep Research broken imports → Fixed with component reuse
- TD-070-03: Deep Research code duplication → Removed
- TD-070-04: Action Agent not integrated → Will be integrated via ReAct

### Key Commits
- `38f2c94` - Tool Use Integration Phase 2 Complete (70.5-70.6)
- `00b6f70` - Feature 70.7: Admin UI Toggle (3 SP)
- `9a24ff1` - Features 70.8-70.10: Tests, Streaming, Analytics (8 SP)
- `bc530fb` - Feature 70.11: LLM-based Tool Detection (5 SP)

### References
- [SPRINT_70_PLAN.md](SPRINT_70_PLAN.md)
- [DEEP_RESEARCH_TOOL_USE_DESIGN.md](DEEP_RESEARCH_TOOL_USE_DESIGN.md)
- LangGraph ReAct: https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch
- LangGraph Supervisor: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams

### Implementation Highlights
**Adaptive Tool Detection (70.11):**
- 3 configurable strategies: Markers (fast), LLM (smart), Hybrid (balanced)
- Admin-editable marker lists + action hint phrases
- Multilingual support (German/English)
- Trade-offs: Markers (~0ms, 60-70%) vs LLM (+50-200ms, 90-95%) vs Hybrid (0-200ms, 85-90%)

**Tool Use Monitoring (70.9-70.10):**
- Real-time phase event streaming (IN_PROGRESS → COMPLETED/FAILED)
- Prometheus metrics: executions_total, duration_seconds, active_executions
- Grafana-ready for operational dashboards

**Configuration Architecture (70.7):**
- Redis persistence with 60s TTL cache
- Lazy graph compilation on first request
- Hot-reload: Admin changes → 60s → New conversations use new config

---

## Sprint 47+: Backlog Candidates 📋
**Candidates:**
| Feature | SP | Source |
|---------|-----|--------|
| JWT Authentication Frontend | 13 | Backlog |
| Learned RRF Weights | 8 | Backlog |
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
