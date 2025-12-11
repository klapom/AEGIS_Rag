# AEGIS RAG - Agentic Enterprise Graph Intelligence System

**Status:** Sprint 43 Complete (2025-12-11)
**Version:** 1.3.0 (Production-Ready)

Enterprise-grade Retrieval-Augmented Generation System with multi-agent orchestration, temporal memory, and GPU-accelerated ingestion.

---

## Quick Start

**New to the project?**
1. Read [CLAUDE.md](CLAUDE.md) - Complete project context
2. Review [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md) - Context refresh strategies
3. Check [docs/sprints/SPRINT_PLAN.md](docs/sprints/SPRINT_PLAN.md) - Current sprint status

**Ready to develop?**
1. Follow [docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md](docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md)
2. Review [docs/NAMING_CONVENTIONS.md](docs/NAMING_CONVENTIONS.md)
3. Read [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) - 43 Architecture Decisions

---

## Current Sprint Status

### Sprint 43: Multi-Criteria Deduplication & Pipeline Monitoring (COMPLETE)
**Duration:** 2025-12-10 to 2025-12-11

**Key Achievements:**
- MultiCriteriaDeduplicator: 4 matching criteria (exact, edit-distance, substring, semantic)
- **10.1% entity deduplication** on large multi-chunk documents
- 12 new Prometheus metrics for chunking, deduplication, extraction
- Comprehensive benchmarking: chunk sizes, model comparison, parallel extraction
- HotPotQA evaluation: gemma3:4b + qwen2.5:7b parallel strategy
- RAGAS TXT pipeline evaluation with production ChunkingService

**Benchmarking Results:**
- Parallel extraction: +20-30% more entities, +45-107% more relations
- Model stability: qwen2.5:7b stable across all chunk sizes
- Optimal chunk size: 2500-3500 chars for speed, 500-1000 for coverage

**Architecture Decisions:**
- ADR-044: Multi-Criteria Entity Deduplication

### Sprint 44: Next (PLANNED)
**Candidates:**
- JWT Authentication Frontend (Login UI, Protected Routes)
- Community Summary Generation (TD-058)
- Learned RRF Weights (ML-based)
- NuExtract Model Evaluation
- Namespace Selector UI

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
- **CLAUDE.md** - Project context for Claude Code
- **CONTEXT_REFRESH.md** - Context refresh strategies
- **TECH_STACK.md** - Complete technology stack
- **ARCHITECTURE_EVOLUTION.md** - Sprint architecture history
- **NAMING_CONVENTIONS.md** - Code standards
- **COMPONENT_INTERACTION_MAP.md** - Component interactions

### Organized Subdirectories
- **docs/adr/** - Architecture Decision Records (ADR-001 to ADR-043)
- **docs/api/** - API endpoint documentation
- **docs/architecture/** - Architecture diagrams
- **docs/guides/** - Setup & how-to guides
- **docs/sprints/** - Sprint plans & reports
- **docs/operations/** - DGX Spark deployment guides
- **docs/technical-debt/** - Technical debt tracking

---

## Architecture Highlights

### Hybrid RAG System
- **Vector Search:** Qdrant + BGE-M3 embeddings
- **Graph Reasoning:** LightRAG + Neo4j (entity/relation extraction)
- **BM25 Keyword:** Reciprocal Rank Fusion (RRF)
- **Reranking:** Cross-encoder (ms-marco-MiniLM-L-6-v2)

### 3-Layer Memory Architecture
- **Layer 1:** Redis (short-term, <10ms)
- **Layer 2:** Qdrant (semantic, <50ms)
- **Layer 3:** Graphiti (episodic, bi-temporal, <200ms)

### LangGraph Multi-Agent System
- **Coordinator Agent:** Query routing & orchestration
- **Vector Search Agent:** Qdrant hybrid search
- **Graph Query Agent:** Neo4j + LightRAG
- **Memory Agent:** Graphiti retrieval
- **Action Agent:** Tool execution (MCP)

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
- **Sprints 1-43:** COMPLETE (Multi-Criteria Deduplication, Pipeline Monitoring)
- **Sprint 44:** PLANNED (TBD)

### Test Coverage
- **Unit Tests:** 467+ tests
- **Integration Tests:** 100+ tests
- **E2E Tests:** 111 Playwright tests
- **Total Coverage:** >80%

### Documentation
- **ADRs:** 44 Architecture Decision Records
- **Sprint Reports:** 37 sprint completion reports
- **Total Docs:** 150+ markdown files

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
1. Read [CLAUDE.md](CLAUDE.md) - Project context
2. Review [docs/NAMING_CONVENTIONS.md](docs/NAMING_CONVENTIONS.md)
3. Check [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)

### For Architects
1. Study [docs/ARCHITECTURE_EVOLUTION.md](docs/ARCHITECTURE_EVOLUTION.md)
2. Review ADR-039 to ADR-043 (Recent decisions)
3. Read [docs/TECH_STACK.md](docs/TECH_STACK.md)

### For DevOps
1. Follow [docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md](docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md)
2. Review [docs/operations/DGX_SPARK_DEPLOYMENT.md](docs/operations/DGX_SPARK_DEPLOYMENT.md)
3. Check [docs/guides/CI_CD_GUIDE.md](docs/guides/CI_CD_GUIDE.md)

---

## Resources

- **GitHub:** [github.com/klapom/AEGIS_Rag](https://github.com/klapom/AEGIS_Rag)
- **Documentation:** [docs/](docs/)
- **Issues:** GitHub Issues
- **ADRs:** [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)

---

**Last Updated:** 2025-12-09 (Sprint 42 Complete)
**Maintainer:** AEGIS RAG Team
