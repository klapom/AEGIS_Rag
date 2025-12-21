# AEGIS RAG - Agentic Enterprise Graph Intelligence System

**Status:** Sprint 60 Complete (2025-12-21)
**Version:** 2.0.0 (Production-Ready, Post-Refactoring)

Enterprise-grade Retrieval-Augmented Generation System with multi-agent orchestration, temporal memory, GPU-accelerated ingestion, and comprehensive technical investigations completed.

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

### Sprint 60: Documentation Consolidation & Technical Investigations (COMPLETE)
**Duration:** 2025-12-15 to 2025-12-21

**Key Achievements:**
- Documentation consolidated: 7 files → 4 consolidated docs
  - ARCHITECTURE.md (merged: Evolution + Component Map + Structure)
  - TECH_STACK.md (merged: Dependencies + DGX Spark config)
  - CONVENTIONS.md (renamed from Naming Conventions)
  - DECISION_LOG.md (preserved for history)
- 4 Technical Investigations completed:
  - TD-069: Multihop Endpoint Review
  - TD-071: vLLM vs Ollama Investigation
  - TD-072: Sentence-Transformers Reranking Analysis
  - TD-073: Sentence-Transformers Embeddings Analysis
- Subdirectory cleanup: 17 documents archived
- Tool Framework implementation verified (Sprint 59)
- Research Agent implementation verified (Sprint 59)

**Documentation Improvements:**
- All Sprint 53-59 refactoring reflected
- Domain-driven structure documented
- DGX Spark configuration centralized
- Technical debt tracking organized

### Sprint 61: Performance Optimizations (PLANNED)
**Candidates:**
- Embedding optimization (investigate BGE-M3 vs Sentence-Transformers)
- Reranking performance improvements
- Query latency optimization
- Memory efficiency enhancements

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
- **Sprints 1-59:** COMPLETE (Comprehensive feature development, refactoring, tool framework)
- **Sprint 60:** COMPLETE (Documentation consolidation, technical investigations)
- **Sprint 61:** PLANNED (Performance optimizations)

### Test Coverage
- **Unit Tests:** 500+ tests
- **Integration Tests:** 120+ tests
- **E2E Tests:** 111 Playwright tests
- **Total Coverage:** >80%

### Documentation
- **ADRs:** 46+ Architecture Decision Records
- **Sprint Reports:** 60 sprint completion reports
- **Technical Debt:** 73+ items tracked (TD-001 to TD-073)
- **Total Docs:** 180+ markdown files

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

**Last Updated:** 2025-12-21 (Sprint 60 Complete)
**Current Sprint:** Sprint 61 (Performance Optimizations - Planning)
**Maintainer:** AEGIS RAG Team
