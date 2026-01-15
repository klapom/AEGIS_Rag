# AEGIS RAG - Agentic Enterprise Graph Intelligence System

**Status:** Sprint 81 In Progress (2026-01-09) | Feature 81.7 C-LARA Complete ✅
**Version:** 2.5.0 (Production-Ready, C-LARA Intent Classification 95%)

Enterprise-grade Retrieval-Augmented Generation System with multi-agent orchestration, temporal memory, GPU-accelerated ingestion, 3-stage semantic graph search, and comprehensive RAGAS evaluation framework.

---

## Quick Start

**New to the project?**
1. Read [CLAUDE.md](CLAUDE.md) - Complete project context
2. Review [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
3. Check [docs/TECH_STACK.md](docs/TECH_STACK.md) - Technology details
4. Review [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md) - Context refresh strategies

**Ready to develop?**
1. Follow [docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md](docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md)
2. Review [docs/CONVENTIONS.md](docs/CONVENTIONS.md) - Code standards
3. Read [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) - Architecture Decisions

---

## Current Sprint Status

### Sprint 96: EU Governance & Compliance (COMPLETE) ✅
**Duration:** 2026-01-13 to 2026-01-15
**Total Story Points:** 32 SP
**Status:** ✅ **COMPLETE** - All 5 Features Delivered (100% pass rate)

**Completed Deliverables:**
- **Feature 96.1: GDPR/DSGVO Compliance Layer (10 SP)** - Articles 6,7,13-17,20,30 implementation
- **Feature 96.2: Audit Trail System (8 SP)** - SHA-256 cryptographic chain, 7-year retention
- **Feature 96.3: Explainability Engine (8 SP)** - 3-level explanations (User/Expert/Audit), source attribution
- **Feature 96.4: Skill Certification Framework (4 SP)** - 3-tier validation (Basic/Standard/Enterprise)
- **Feature 96.5: Integration Testing (2 SP)** - 211 tests (100% pass rate)

**Key Metrics:**
- **Test Coverage:** 211 tests passing in 0.19s (100% pass rate)
- **Code Quality:** 3,329 LOC implementation, 4,290 LOC tests, 97%+ coverage
- **EU Compliance:** Full GDPR + EU AI Act readiness, NIST AI RMF integration ready
- **Modules Delivered:** 4 governance modules (gdpr, audit, explainability, certification)

### Major Milestone: Sprints 90-96 Transformation ✅
**Total Investment:** 208 Story Points across 7 sprints
**Transformation:** Basic RAG → Enterprise Agentic Framework with EU Compliance
**Implementation:** 15,000+ LOC, 800+ tests, 5 skill frameworks, hierarchical agents, governance layer
**Outcome:** Production-ready enterprise system with full EU compliance certifications

---

### Sprint 78: Graph Entity→Chunk Expansion & Semantic Search (COMPLETE)
**Duration:** 2026-01-08
**Total Story Points:** 34 SP
**Status:** ✅ **FUNCTIONALLY COMPLETE** (5/6 features, RAGAS deferred to Sprint 79)

**Key Achievements:**
- **Entity→Chunk Expansion Fix (5 SP):** Graph search now returns full 447-char chunks instead of 100-char entity descriptions
  - Modified `dual_level_search.py` to traverse `(entity)-[:MENTIONED_IN]->(chunk)` relationships
  - Impact: 4.5x more context for LLM (100 chars → 447 chars avg)
- **3-Stage Entity Expansion Pipeline (13 SP):** SmartEntityExpander with LLM→Graph→Synonym→Reranking
  - Stage 1: LLM extracts entities from query (context-aware, auto-filters stop words)
  - Stage 2: Graph N-hop traversal (configurable 1-3 hops, preserves domain knowledge)
  - Stage 3: LLM synonym fallback (only when < threshold, prevents semantic drift)
  - Stage 4: BGE-M3 semantic reranking (GPU-accelerated, optional)
- **UI Configuration (3 SP):** 4 new settings in Admin UI
  - `graph_expansion_hops`: 1-3 (default: 1)
  - `graph_min_entities_threshold`: 5-20 (default: 10)
  - `graph_max_synonyms_per_entity`: 1-5 (default: 3)
  - `graph_semantic_reranking_enabled`: bool (default: true)
- **Unit Tests (5 SP):** 20 comprehensive tests (100% pass rate)
  - 14 tests for SmartEntityExpander (all 4 stages + edge cases)
  - 6 tests for dual_level_search (Entity→Chunk traversal, namespace filtering, ranking)
- **Documentation (5 SP):** ADR-041 created, comprehensive Sprint 78 documentation

**RAGAS Evaluation (1 SP - Deferred to Sprint 79):**
- Root Cause: RAGAS Few-Shot prompts (2903 chars) too complex for local LLMs
  - GPT-OSS:20b: 85.76s per evaluation (timeout at 300s for 15 contexts)
  - Nemotron3 Nano: >600s per simple query
- Alternative Verification: Functional testing (20 unit tests + manual graph queries)
- Sprint 79 Solution: DSPy prompt optimization (target: 4x speedup, ≥90% accuracy)

**Performance:**
- Graph query latency: +70ms (0.05s→0.12s) for 4.5x more context
- Entity expansion: 0.4-0.9s (depending on synonym fallback)
- End-to-end query: ~500ms (within target <500ms for hybrid queries)

### Sprint 76-77: RAGAS Foundation & Critical Bug Fixes (COMPLETE)
**Sprint 76:** .txt File Support (15 HotpotQA files), RAGAS Baseline (Faithfulness 80%, Answer Relevancy 93%), 146 entities extracted
**Sprint 77:** BM25 namespace fix, chunk mismatch resolved, Community Summarization (92/92), Entity Connectivity Benchmarks (4 domains), 2,108 LOC added

### Sprint 79: DSPy RAGAS Prompt Optimization (PLANNED)
**Goal:** Optimize RAGAS prompts for local LLMs using DSPy
**Total Story Points:** 21 SP
**Target Performance:**
- GPT-OSS:20b: 85.76s → <20s (4x speedup)
- Nemotron3 Nano: >600s → <60s (10x speedup)
- Accuracy: ≥90% (vs 100% baseline)
**Approach:** DSPy BootstrapFewShot + MIPROv2 for automatic prompt compression

---

## Technology Stack

### Core Components
- **Backend:** Python 3.12.7, FastAPI, Pydantic v2
- **Orchestration:** LangGraph 0.6.10, LangChain Core
- **Ingestion:** Docling CUDA Container (GPU-accelerated OCR, ADR-027)
- **Fallback:** LlamaIndex 0.14.3 (connectors only, ADR-028)

### Databases
- **Vector DB:** Qdrant 1.11.0 (semantic search)
- **Graph DB:** Neo4j 5.24 Community (knowledge graph)
- **Memory Cache:** Redis 7.x (short-term memory)

### AI Models
- **LLM Routing:** AegisLLMProxy - fully configurable (ADR-033)
- **Current Runtime:** DGX Spark (vLLM/Ollama with cu130)
- **Fallback:** Alibaba Cloud DashScope, OpenAI
- **Embeddings:** BGE-M3 (1024-dim, multilingual, ADR-024)

### Infrastructure
- **Container Runtime:** Docker + NVIDIA Container Toolkit
- **CI/CD:** GitHub Actions
- **DGX Spark:** NVIDIA GB10 (sm_121), CUDA 13.0, 128GB Unified Memory

---

## Documentation Structure

### Core Docs (Root & docs/)
**Sprint 60 Consolidated Documentation:**
- **ARCHITECTURE.md** - System architecture, domain structure, component interactions
- **TECH_STACK.md** - Complete technology stack, DGX Spark config, dependencies
- **CONVENTIONS.md** - Code standards, naming conventions, protocols
- **DECISION_LOG.md** - Historical decisions and rationale
- **CLAUDE.md** - Project context for Claude Code sessions
- **CONTEXT_REFRESH.md** - Context recovery strategies

### Organized Subdirectories
- **docs/adr/** - Architecture Decision Records (ADR-001 to ADR-046+)
- **docs/api/** - API endpoint documentation
- **docs/guides/** - Setup & how-to guides (CI/CD, GPU, Production, Testing, WSL2)
- **docs/sprints/** - Sprint plans & completion reports (Sprint 1-60)
- **docs/technical-debt/** - Technical debt tracking (TD-001 to TD-073)
- **docs/analysis/** - Technical investigations & analysis reports
- **docs/archive/** - Archived documentation from prior sprints

---

## Architecture Highlights

### 4-Way Hybrid Retrieval System
- **Vector Search:** Qdrant + BGE-M3 embeddings (1024-dim, multilingual)
- **Graph Reasoning:** LightRAG + Neo4j (entity/relation extraction, ADR-026)
- **Keyword Search:** BM25 + Reciprocal Rank Fusion (RRF, ADR-009)
- **Reranking:** Cross-encoder (ms-marco-MiniLM-L-6-v2)

### 3-Layer Memory Architecture
- **Layer 1:** Redis (short-term, <10ms)
- **Layer 2:** Qdrant (semantic, <50ms)
- **Layer 3:** Graphiti (episodic, bi-temporal, <200ms)

### LangGraph Multi-Agent System (Sprint 59+)
- **Coordinator Agent:** Query routing & orchestration
- **Vector Search Agent:** Qdrant hybrid search
- **Graph Query Agent:** Neo4j + LightRAG
- **Memory Agent:** Graphiti temporal memory retrieval
- **Action Agent:** Tool execution (MCP) - Tool Framework (Sprint 59)
- **Research Agent:** Complex multi-step research (Sprint 59)

### Ingestion Pipeline (Streaming)
**6-Node LangGraph State Machine:**
1. **Docling Parse:** GPU-accelerated OCR (95% accuracy)
2. **VLM Enrichment:** Image descriptions with BBox provenance
3. **Chunking:** Section-aware (800-1800 tokens, ADR-039)
4. **Embedding:** BGE-M3 batch embeddings
5. **Graph Extraction:** Pure LLM (ADR-026)
6. **Validation:** Schema validation, provenance checks

---

## Claude Code Integration

**4 Specialized Subagents:**
1. **backend-agent** - Core business logic, LangGraph agents
2. **infrastructure-agent** - Docker, CI/CD, Kubernetes
3. **api-agent** - FastAPI endpoints, OpenAPI docs
4. **testing-agent** - Unit, integration, E2E tests

**Usage:**
- See [docs/SUBAGENTS.md](docs/SUBAGENTS.md) for delegation strategies
- Use [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md) for context recovery

---

## Project Status

### Sprint Completion
- **Sprints 1-60:** COMPLETE (Core features, refactoring, documentation consolidation)
- **Sprints 61-63:** COMPLETE (Multi-turn research, section-aware citations)
- **Sprint 64:** COMPLETE (Domain training, LLM config backend, production deployment)

### Test Coverage
- **Unit Tests:** 500+ tests
- **Integration Tests:** 130+ tests (domain training, LLM config)
- **E2E Tests:** 111 Playwright tests (Sprint 63+64)
- **Total Coverage:** >80%

### Documentation
- **ADRs:** 46+ Architecture Decision Records
- **Sprint Reports:** 64 sprint completion reports
- **Technical Debt:** 76+ items tracked (TD-001 to TD-076)
- **Features:** 24+ documented features (Sprint 62-64)
- **Total Docs:** 200+ markdown files

---

## Security & Compliance

### Local-First Strategy (ADR-002)
- **Ollama Primary:** Zero cloud dependencies for dev
- **Multi-Cloud Option:** AegisLLMProxy (Alibaba, OpenAI)
- **DSGVO Compliant:** Data stays local by default
- **Cost Tracking:** SQLite database, $120/month budget

### Security Features
- SHA-256 hashing for chunk IDs
- Input validation and sanitization
- Rate limiting
- Content filtering

---

## Dependencies

**Runtime:**
- Python 3.12+
- Docker + NVIDIA Container Toolkit
- Ollama 
- Poetry (dependency management)

**GPU Requirements:**
- NVIDIA GPU with CUDA 13.0+ support
- 12GB+ VRAM recommended (for VLM + Docling)
- DGX Spark: CUDA 13.0, PyTorch cu130

---

## Next Steps

### For Developers
1. Read [CLAUDE.md](CLAUDE.md) - Project context & environment
2. Review [docs/CONVENTIONS.md](docs/CONVENTIONS.md) - Code standards
3. Check [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) - Architecture decisions

### For Architects
1. Study [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
2. Review ADR-044 to ADR-046+ (Recent decisions)
3. Read [docs/TECH_STACK.md](docs/TECH_STACK.md) - Technology details

### For DevOps
1. Follow [docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md](docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md)
2. Review [docs/guides/DGX_SPARK_DEPLOYMENT.md](docs/guides/DGX_SPARK_DEPLOYMENT.md)
3. Check [docs/guides/CI_CD_GUIDE.md](docs/guides/CI_CD_GUIDE.md)

---

## Resources

- **GitHub:** [github.com/klapom/AEGIS_Rag](https://github.com/klapom/AEGIS_Rag)
- **Documentation:** [docs/](docs/)
- **Issues:** GitHub Issues
- **ADRs:** [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)

---

**Last Updated:** 2025-12-25 (Sprint 64 Complete)
**Next Sprint:** Sprint 65 (Advanced Features - Planning)
**Maintainer:** AEGIS RAG Team
