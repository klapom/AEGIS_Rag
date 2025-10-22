# DECISION LOG - AEGIS RAG

**Purpose:** Chronological list of major architecture and technology decisions
**Format:** Date | Decision | Rationale (2-3 sentences max)
**Last Updated:** 2025-10-22 (Post-Sprint 12)

---

## SPRINT 1-2: FOUNDATION & VECTOR SEARCH

### 2025-01-15 | LangGraph for Multi-Agent Orchestration (ADR-001)
**Decision:** Use LangGraph as primary orchestration framework over CrewAI, AutoGen, LlamaIndex Workflows.
**Rationale:** Best balance of control (explicit graph definition), production features (LangSmith tracing, state persistence), and flexibility (conditional routing, parallel execution). Higher learning curve justified by better debuggability and enterprise maturity (Klarna, Uber, Replit).

### 2025-01-15 | Ollama-Only LLM Strategy (ADR-002)
**Decision:** 100% Ollama for development and production, zero cloud LLM usage.
**Rationale:** $0 costs (saves $18K-24K/year vs Azure OpenAI), offline-capable for air-gapped deployment, DSGVO-compliant by design. Modern models (llama3.2, qwen2.5) provide sufficient quality for 90%+ use cases. No vendor lock-in.

### 2025-01-15 | Python + FastAPI for Backend (ADR-008)
**Decision:** Python 3.11+ with FastAPI framework for REST API.
**Rationale:** Best AI/ML ecosystem (LangChain, LlamaIndex all Python-first), FastAPI is fastest Python framework (Starlette/Uvicorn), auto OpenAPI docs, native async/await for I/O-bound operations. Type safety via Pydantic v2.

### 2025-01-15 | Hybrid Vector-Graph Retrieval (ADR-003)
**Decision:** Combine Vector Search (Qdrant) + Graph RAG (Neo4j/LightRAG) + BM25 keyword search with RRF fusion.
**Rationale:** Research shows 40-60% better relevance vs pure vector or pure graph. Vector excels at semantic similarity, graph at multi-hop reasoning, BM25 at keyword matching. Reciprocal Rank Fusion combines strengths without score normalization.

### 2025-01-15 | Qdrant as Primary Vector Database (ADR-004)
**Decision:** Qdrant over Pinecone, Weaviate, ChromaDB for vector storage.
**Rationale:** Best-in-class performance (3ms latency at 1M embeddings), 24x compression via asymmetric quantization, self-hosting option (no vendor lock-in), advanced filtering, RBAC, multi-tenancy. Active community (21K+ GitHub stars).

### 2025-01-15 | Reciprocal Rank Fusion for Hybrid Search (ADR-009)
**Decision:** Use RRF algorithm (k=60) to combine vector, BM25, and graph rankings.
**Rationale:** Score-agnostic (no normalization needed), robust across query types, research-validated (Cormack et al. 2009). Simpler than weighted average (needs tuning) or CombSUM (complex). Formula: score = sum(1/(k+rank)).

---

## SPRINT 3-4: ADVANCED RETRIEVAL & ORCHESTRATION

### 2025-01-20 | Cross-Encoder Reranking
**Decision:** Add sentence-transformers/ms-marco-MiniLM-L-6-v2 reranking after hybrid search.
**Rationale:** +15-20% precision improvement for only +50ms latency. Cross-encoder evaluates query-document pairs directly (better than bi-encoder similarity). Massive quality boost for low overhead.

### 2025-01-20 | RAGAS Evaluation Framework
**Decision:** Integrate RAGAS 0.3.7 for RAG quality metrics (context precision, recall, faithfulness).
**Rationale:** Objective measurement of retrieval quality prevents regression. RAGAS 0.3.7 has better Ollama support. Baseline score: 0.88 (excellent). Enables continuous quality monitoring.

### 2025-01-21 | Security Hardening: MD5 → SHA-256
**Decision:** Replace MD5 hashing for document IDs with SHA-256.
**Rationale:** MD5 vulnerable (CVE-2010-4651), SHA-256 is cryptographically secure. Critical for production deployment. Also added rate limiting (slowapi), input sanitization (Pydantic), path traversal protection.

### 2025-01-22 | LangGraph Multi-Agent System (4 Agents)
**Decision:** Implement Router, Vector, Graph, Memory agents with conditional routing.
**Rationale:** Specialization improves quality (each agent optimized for its task). Router selects optimal strategy per query type. Parallel execution via Send API reduces latency. State management handles complex workflows.

---

## SPRINT 5-6: GRAPH RAG & HYBRID FUSION

### 2025-01-15 | LightRAG over Microsoft GraphRAG (ADR-005)
**Decision:** Use LightRAG 1.4.9 for knowledge graph construction instead of Microsoft GraphRAG.
**Rationale:** Lower token costs (less intensive LLM usage), incremental updates (no full re-index), dual-level retrieval (entity + topic matching). Microsoft GraphRAG is expensive and static (full re-index on updates). Comparable accuracy at 1/10th cost.

### 2025-01-25 | qwen3:0.6b for Entity Extraction (Later switched to llama3.2:3b in Sprint 11)
**Decision:** Use ultra-lightweight qwen3:0.6b (0.5GB RAM) for LightRAG entity extraction.
**Rationale:** Fast inference (~500ms/doc), acceptable quality for entity detection, minimal memory footprint. Later switched to llama3.2:3b in Sprint 11 for better structured output quality (+20% accuracy, traded speed for reliability).

### 2025-01-26 | Leiden Algorithm for Community Detection
**Decision:** Use graspologic's Leiden algorithm for graph community detection.
**Rationale:** Better quality than Louvain (higher modularity), faster convergence, detects hierarchical structures. Supports LightRAG's high-level topic-based retrieval. Optimized in Sprint 11 with parallel processing (2.5x speedup).

### 2025-01-27 | Unified Retrieval Router (Vector/Graph/Hybrid/Adaptive)
**Decision:** Single router with 4 strategies: vector-only, graph-only, hybrid, adaptive.
**Rationale:** Query classification determines optimal retrieval path. Vector for semantic similarity, graph for relationships, hybrid for complex queries. Parallel execution + RRF fusion. Adaptive routing (ML-based) planned for Sprint 13.

---

## SPRINT 7-9: TEMPORAL MEMORY & MCP

### 2025-01-15 | 3-Layer Memory Architecture (ADR-006)
**Decision:** Redis (Layer 1) + Qdrant (Layer 2) + Graphiti + Neo4j (Layer 3).
**Rationale:** Optimize for different use cases: Redis <10ms for short-term (session state, recent context), Qdrant <50ms for semantic long-term, Graphiti <200ms for episodic temporal (relationships, evolution tracking). Memory router selects optimal layer per query type.

### 2025-01-28 | Graphiti for Episodic Temporal Memory
**Decision:** Use graphiti-core 0.3.0 for bi-temporal graph storage.
**Rationale:** Unique capability: bi-temporal queries (valid-time + transaction-time). Track knowledge evolution over time, "what did system know on date X?" No competitors offer this. Built on Neo4j backend for graph traversal.

### 2025-01-29 | Memory Consolidation Pipeline (APScheduler)
**Decision:** Automated consolidation: Redis → Qdrant (hourly), Conversations → Graphiti (hourly).
**Rationale:** Prevents Redis memory bloat, archives old conversations to semantic/episodic layers. APScheduler runs background jobs without manual intervention. Configurable thresholds (e.g., >1 hour old, >3 accesses).

### 2025-01-15 | MCP Client (NOT Server) Integration (ADR-007)
**Decision:** Implement MCP Client to consume external MCP tools (Filesystem, GitHub, Slack). No MCP Server (we don't provide tools to others).
**Rationale:** Access 500+ community MCP servers without custom integrations. Standardized tool protocol (OpenAI, Google, Microsoft, Anthropic support). Action Agent can call external tools. MCP Server deferred (unclear use case, added complexity).

---

## SPRINT 10-12: UI, OPTIMIZATION, PRODUCTION

### 2025-02-01 | Gradio for MVP UI
**Decision:** Use Gradio 5.49.0 for rapid prototyping chat interface.
**Rationale:** Fastest path to UI (<1 day implementation), built-in components (chatbot, file upload), easy FastAPI integration. Trade-off: limited customization, no SSE streaming (polling workaround). Planned migration to React + Next.js 14 in Sprint 14 for production polish.

### 2025-02-03 | GPU Acceleration (MANDATORY for Production)
**Decision:** NVIDIA GPU required for production deployment (tested on RTX 3060).
**Rationale:** 15-20x speedup (7 → 105 tokens/s for llama3.2:3b). CPU-only unusable for production (<2s → <30s response time). GPU makes Ollama-only strategy viable. Verified on RTX 3060 (52.7% VRAM utilization, 105 tokens/s).

### 2025-02-04 | Unified Embedding Service (Sprint 11)
**Decision:** Single EmbeddingService with shared LRU cache (10K entries) across all components.
**Rationale:** Eliminates fragmented embedding calls (vector, graph, memory had separate services). 60% cache hit rate, memory reduced from 1.5GB → 600MB. Simplifies codebase, reduces Ollama API load.

### 2025-02-05 | Parallel Ingestion Pipeline (Sprint 11)
**Decision:** Parallel indexing of Qdrant, BM25, LightRAG (was sequential).
**Rationale:** 3x speedup (30s → 10s for 100 documents). Progress tracking for UX. Async/await enables concurrent database operations. Critical for production-scale document ingestion.

### 2025-02-06 | Redis Checkpointer for LangGraph State (Sprint 11)
**Decision:** langgraph-checkpoint-redis 0.1.2 for durable state persistence.
**Rationale:** In-memory state lost on restart. Redis persistence enables conversation resumption, crash recovery. Production-grade state management. Proper async cleanup prevents event loop warnings (Sprint 12 fix).

### 2025-01-15 | E2E Integration Testing with Real Services (ADR-014)
**Decision:** NO MOCKS for integration/E2E tests. Use real Docker services (Redis, Qdrant, Neo4j, Ollama).
**Rationale:** Sprint 6 showed mock behavior ≠ real behavior (timeout issues). Real services catch integration bugs, configuration problems, race conditions. Cost-free Ollama enables unlimited testing. Trade-off: slower execution (2-5 min), but higher confidence.

### 2025-01-15 | Critical Path Testing Strategy (ADR-015)
**Decision:** 4 critical paths: Vector Search, Graph RAG, Memory Query, Hybrid Fusion. 80% E2E baseline.
**Rationale:** Focus testing on user-facing workflows. NO MOCKS principle ensures production readiness. Sprint 8 baseline: 78.6% pass rate. Sprint 12: 88.5% (2.8x improvement from 17.9% in Sprint 11).

### 2025-02-07 | Production Deployment Guide (Sprint 12)
**Decision:** Comprehensive 800+ line guide covering GPU, Docker, K8s, monitoring, security, backup/DR.
**Rationale:** De-risks production deployment. Documents all prerequisites (NVIDIA drivers, container toolkit). Includes Prometheus/Grafana dashboards, security hardening (JWT, rate limiting, HTTPS/TLS), automated backup scripts. Critical for handoff to ops team.

---

## SPRINT 13+ FUTURE DECISIONS (PLANNED)

### TBD | React + Next.js 14 Frontend (Sprint 14)
**Decision (Planned):** Replace Gradio with Next.js 14 + TypeScript + Tailwind CSS.
**Rationale:** Gradio insufficient for production UI (limited customization, no SSE, poor styling). Next.js provides professional polish, real-time streaming (SSE), dark mode, responsive design. NextAuth.js for authentication, Zustand for state management.

### TBD | Adaptive Routing with Machine Learning (Sprint 13)
**Decision (Planned):** ML-based query router to auto-select vector/graph/hybrid strategy.
**Rationale:** Current router uses heuristics (keyword matching). ML model can learn from query patterns, user feedback. Potential +10-15% relevance improvement. Train on historical query logs with RAGAS scores.

### TBD | Multi-User Authentication & Authorization
**Decision (Planned):** JWT-based auth, role-based access control (admin, user, viewer).
**Rationale:** Production requires user management. NextAuth.js integration in Sprint 14. User-specific rate limiting, audit logging, session management.

---

## KEY PIVOT POINTS

### Sprint 11: LightRAG Model Switch (qwen3:0.6b → llama3.2:3b)
**Original:** qwen3:0.6b (ultra-lightweight, 0.5GB RAM)
**Problem:** Entity extraction format issues (JSON parsing errors)
**Pivot:** llama3.2:3b (better structured output)
**Trade-off:** Slower (150 → 105 tokens/s), but +20% accuracy
**Lesson:** Model quality > speed for entity extraction

### Sprint 14 (Planned): Gradio → React Migration
**Original:** Gradio MVP (Sprint 10)
**Problem:** Limited customization, no SSE streaming, poor styling
**Pivot:** React + Next.js 14 (Sprint 14)
**Reason:** Production UI requires professional polish
**Lesson:** Gradio excellent for prototyping, not production

### Sprint 9: MCP Client Only (Not MCP Server)
**Original:** Plan included MCP Server (provide tools to others)
**Problem:** Unclear use case, added complexity
**Pivot:** MCP Client only (consume external tools)
**Reason:** Focus on value delivery (action agent needs tools), not tool provision
**Lesson:** YAGNI principle - don't build what you don't need yet

---

## DECISION THEMES

### Cost Optimization
- Ollama-only strategy ($0 LLM costs, $18K-24K/year savings)
- Self-hosted infrastructure (Docker Compose, no cloud vendor lock-in)
- GPU acceleration on existing hardware (RTX 3060, $0 incremental cost)

### Quality over Speed
- Cross-encoder reranking (+50ms, +15-20% precision)
- llama3.2:3b over qwen3:0.6b (slower, but better quality)
- Real service testing (slower, but higher confidence)

### Developer Experience
- FastAPI auto OpenAPI docs
- LangGraph explicit control (vs CrewAI simplicity)
- Unified services (embedding, ingestion) reduce complexity

### Production Readiness
- GPU acceleration mandatory (15-20x speedup)
- Redis checkpointer (durable state)
- Comprehensive deployment guide (800+ lines)
- E2E testing with real services (NO MOCKS)

### Modularity & Flexibility
- 3-layer memory (optimize per use case)
- Hybrid retrieval (vector + graph + BM25)
- Multi-agent orchestration (specialized agents)
- Unified router (4 strategies)

---

**Last Updated:** 2025-10-22 (Post-Sprint 12)
**Total Decisions Documented:** 35+
**Next Sprint:** Sprint 13 (Test Infrastructure & Performance)
