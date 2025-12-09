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

## Sprint 42: 4-Way Hybrid RRF ✅
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
