# AEGIS RAG - Agentic Enterprise Graph Intelligence System

**Status:** Sprint 21 Complete (2025-11-10)
**Version:** 1.0.0 (Production-Ready)

Enterprise-grade Retrieval-Augmented Generation System with multi-agent orchestration, temporal memory, and GPU-accelerated ingestion.

---

## 🚀 Quick Start

**New to the project?**
1. Read [docs/CLAUDE.md](docs/CLAUDE.md) - Complete project context
2. Review [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md) - Context refresh strategies
3. Check [docs/sprints/SPRINT_PLAN.md](docs/sprints/SPRINT_PLAN.md) - Current sprint status

**Ready to develop?**
1. Follow [docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md](docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md)
2. Review [docs/NAMING_CONVENTIONS.md](docs/NAMING_CONVENTIONS.md)
3. Read [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) - 30 Architecture Decisions

---

## 📋 Current Sprint Status

### Sprint 21: Container-Based Ingestion ✅ COMPLETE
**Duration:** 2025-11-07 → 2025-11-10

**Key Achievements:**
- ✅ Docling CUDA Container (95% OCR accuracy, 3.5x faster)
- ✅ VLM Integration (llava:7b-v1.6-mistral-q2_K, Qwen3-VL 4B)
- ✅ LangGraph 6-Node Pipeline (Docling → VLM → Chunking → Embedding → Graph → Validation)
- ✅ LlamaIndex Deprecation (now fallback only, ADR-028)
- ✅ 31 Integration Tests (100% pass rate)
- ✅ Documentation complete (Sprint 1-21)

**Architecture Decisions:**
- ADR-026: Pure LLM Extraction as Default Pipeline
- ADR-027: Docling CUDA Container vs. LlamaIndex
- ADR-028: LlamaIndex Deprecation Strategy
- ADR-029: React Migration Deferral
- ADR-030: Sprint Extension (12 → 21+ Sprints)

### Sprint 22: Production Deployment 📋 PLANNED
**Planned:**
- React Frontend Migration
- Kubernetes Deployment
- External User Onboarding
- Performance Validation (100+ docs)

---

## 🛠️ Technology Stack (Sprint 21)

### Core Components
- **Backend:** Python 3.12.7, FastAPI, Pydantic v2
- **Orchestration:** LangGraph 0.6.10, LangChain Core
- **Ingestion:** Docling CUDA Container (GPU-accelerated OCR, ADR-027)
- **Fallback:** LlamaIndex 0.14.3 (connectors only, ADR-028)

### Databases
- **Vector DB:** Qdrant 1.11.0 (semantic search)
- **Graph DB:** Neo4j 5.24 Community (knowledge graph)
- **Memory Cache:** Redis 7.x (short-term memory)

### AI Models (Local & Cost-Free)
- **Query Understanding:** llama3.2:3b (Ollama)
- **Answer Generation:** llama3.2:8b (Ollama)
- **Entity Extraction:** gemma-3-4b-it-Q8_0 (Ollama, ADR-026)
- **Vision (VLM):** llava:7b-v1.6-mistral-q2_K (Sprint 21)
- **Vision (Alt):** qwen3-vl:4b (Sprint 21)
- **Embeddings:** BGE-M3 (1024-dim, multilingual, ADR-024)

### Infrastructure
- **Container Runtime:** Docker + NVIDIA Container Toolkit (CUDA 12.4)
- **CI/CD:** GitHub Actions
- **GPU:** NVIDIA RTX 3060 (12GB VRAM, Sprint 21 Feature 21.6)

---

## 📚 Documentation Structure

### Core Docs (docs/ root) - 9 files
Essential reference documentation:
- **CLAUDE.md** - Project context for Claude Code
- **CONTEXT_REFRESH.md** - Context refresh strategies (Quick/Standard/Deep)
- **TECH_STACK.md** - Complete technology stack (Sprint 1-21)
- **ARCHITECTURE_EVOLUTION.md** - Sprint-by-sprint architecture history
- **DEPENDENCY_RATIONALE.md** - Dependency justifications
- **SUBAGENTS.md** - 6 specialized subagents
- **NAMING_CONVENTIONS.md** - Code standards
- **DECISION_LOG.md** - Decision log
- **COMPONENT_INTERACTION_MAP.md** - Component interactions

### Organized Subdirectories - 12 categories
- **docs/adr/** - Architecture Decision Records (ADR-001 to ADR-030)
- **docs/api/** - API endpoint documentation
- **docs/architecture/** - Architecture diagrams
- **docs/core/** - Core project documentation
- **docs/guides/** - Setup & how-to guides
- **docs/reference/** - Technical references
- **docs/evaluations/** - Comparisons & evaluations
- **docs/planning/** - Planning documents
- **docs/examples/** - Code examples
- **docs/sprints/** - Sprint plans & reports
- **docs/troubleshooting/** - Debugging guides
- **docs/archive/** - Obsolete/historical docs

---

## 🏗️ Architecture Highlights

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

### Ingestion Pipeline (Sprint 21)
**6-Node LangGraph State Machine:**
1. **Docling Parse:** GPU-accelerated OCR (95% accuracy)
2. **VLM Enrichment:** Image descriptions with BBox provenance
3. **Chunking:** HybridChunker (1024 tokens, BGE-M3 optimized)
4. **Embedding:** BGE-M3 batch embeddings
5. **Graph Extraction:** Pure LLM (gemma-3-4b-it-Q8_0, ADR-026)
6. **Validation:** Schema validation, provenance checks

---

## 🤖 Claude Code Integration

**6 Specialized Subagents:**
1. **backend-agent** - Core business logic, LangGraph agents
2. **infrastructure-agent** - Docker, CI/CD, Kubernetes
3. **api-agent** - FastAPI endpoints, OpenAPI docs
4. **testing-agent** - Unit, integration, E2E tests
5. **documentation-agent** - ADRs, API docs, guides
6. **subagent-architect** - Agent configuration design

**Usage:**
- See [docs/SUBAGENTS.md](docs/SUBAGENTS.md) for delegation strategies
- Use [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md) for context recovery

---

## 📊 Project Status

### Sprint Completion
- **Sprints 1-21:** ✅ COMPLETE (Container-based ingestion, VLM enrichment)
- **Sprint 22:** 📋 PLANNED (Production deployment, React migration)

### Test Coverage
- **Unit Tests:** 112+ tests
- **Integration Tests:** 51+ tests (including 31 for Docling)
- **E2E Tests:** 28+ tests
- **Total Coverage:** >80%

### Documentation
- **ADRs:** 30 Architecture Decision Records (ADR-001 to ADR-030)
- **Sprint Reports:** 21 sprint completion reports
- **Component READMEs:** 10+ component documentation files
- **Total Docs:** 100+ markdown files

---

## 🔒 Security & Compliance

### Local-First Strategy (ADR-002)
- **100% Ollama:** No cloud dependencies
- **Offline Capable:** Air-gapped deployment
- **DSGVO Compliant:** No data leaves local network
- **Cost-Free:** Zero API costs in development

### Security Features
- SHA-256 hashing for chunk IDs
- Input validation and sanitization
- Rate limiting
- Content filtering

---

## 📦 Dependencies

**Runtime:**
- Python 3.11+
- Docker + NVIDIA Container Toolkit
- Ollama (7 models: llama3.2, gemma-3, llava, qwen3-vl, BGE-M3)
- Poetry (dependency management)

**GPU Requirements:**
- NVIDIA GPU with CUDA 12.4 support
- 12GB+ VRAM recommended (for VLM + Docling)
- RTX 3060 / RTX 3070 / RTX 4060 or better

---

## 🚀 Next Steps

### For Developers
1. Read [docs/CLAUDE.md](docs/CLAUDE.md) - Project context
2. Review [docs/NAMING_CONVENTIONS.md](docs/NAMING_CONVENTIONS.md)
3. Check [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) for architecture decisions

### For Architects
1. Study [docs/ARCHITECTURE_EVOLUTION.md](docs/ARCHITECTURE_EVOLUTION.md)
2. Review ADR-026 through ADR-030 (Sprint 21 decisions)
3. Read [docs/TECH_STACK.md](docs/TECH_STACK.md) for complete stack

### For DevOps
1. Follow [docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md](docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md)
2. Review [docs/guides/GPU_REQUIREMENTS.md](docs/guides/GPU_REQUIREMENTS.md)
3. Check [docs/guides/CI_CD_GUIDE.md](docs/guides/CI_CD_GUIDE.md)

---

## 📞 Resources

- **GitHub:** [github.com/klapom/AEGIS_Rag](https://github.com/klapom/AEGIS_Rag)
- **Documentation:** [docs/](docs/)
- **Issues:** GitHub Issues
- **ADRs:** [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)

---

**Last Updated:** 2025-11-10 (Sprint 21 Complete)
**Maintainer:** AEGIS RAG Team
