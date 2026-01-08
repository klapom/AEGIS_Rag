# CLAUDE.md - AegisRAG Project Context

## Session Continuity Check

**Bei Context Loss:**
1. Lies [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md)
2. Checke docs/sprints/SPRINT_PLAN.md
3. Verifiziere ADR-Awareness: docs/adr/ADR_INDEX.md
4. Consolidated Architecture: docs/ARCHITECTURE.md
5. Technology Stack: docs/TECH_STACK.md
6. Code Conventions: docs/CONVENTIONS.md

---

## Project Overview

**AegisRAG** = Agentic Enterprise Graph Intelligence System

| Component | Technology | Purpose |
|-----------|------------|---------|
| Vector Search | Qdrant + BM25 + RRF | Hybrid Retrieval |
| Graph Reasoning | LightRAG + Neo4j | Entity/Relation Queries |
| Temporal Memory | Graphiti + Redis | 3-Layer Memory |
| Orchestration | LangGraph | Multi-Agent System |
| LLM Routing | AegisLLMProxy | Multi-Cloud (ADR-033) |
| Ingestion | Docling CUDA | GPU-accelerated OCR |
| Chunking | Section-Aware | 800-1800 tokens (ADR-039) |

---

## Technology Stack

**See [docs/TECH_STACK.md](docs/TECH_STACK.md) for complete details**

```yaml
Backend: Python 3.12.7, FastAPI, Pydantic v2
Package Manager: Poetry (pyproject.toml)
Orchestration: LangGraph 0.6.10 + LangChain Core

Databases:
  Vector: Qdrant 1.11.0 (hybrid: vector + BM25 + RRF)
  Graph: Neo4j 5.24 Community (entity/relation extraction)
  Memory: Redis 7.x + Graphiti (3-layer temporal memory)

LLM & Embeddings:
  Current Model: Nemotron3 Nano 30/3a (DGX Spark)
  LLM Routing: AegisLLMProxy (ADR-033) - Multi-cloud support
  Fallback: Alibaba Cloud DashScope, OpenAI
  Embeddings: BGE-M3 (1024-dim, multilingual) - ADR-024
  Reranking: 

Ingestion:
  Parser: Docling CUDA (GPU-accelerated OCR) - ADR-027
  Chunking: Section-aware (800-1800 tokens) - ADR-039
  Extraction: Pure LLM pipeline - ADR-026

Frontend:
  Framework: React 19, TypeScript, Vite 7.1.12
  Styling: Tailwind CSS, Lucide Icons
  Testing: Playwright

---

## DGX Spark Deployment (sm_121)

**Hardware:** NVIDIA GB10 (Blackwell), CUDA 13.0, 128GB Unified Memory, ARM64

### Running Services (alle auf DGX Spark!)
```yaml
Backend:   http://localhost:8000  # FastAPI (uvicorn)
Frontend:  http://localhost:5179  # Vite dev server
Qdrant:    localhost:6333/6334    # Vector DB (gRPC on 6334)
Neo4j:     bolt://localhost:7687  # Graph DB (Browser: 7474)
Redis:     localhost:6379         # Memory/Cache
Ollama:    http://localhost:11434 # LLM (llama3.2:8b)
```

**WICHTIG:** Alle Services laufen auf der DGX Spark in Docker!
- Backend/Frontend: Direkt mit poetry/npm gestartet
- Datenbanken: Native Installation auf DGX Spark
- Docling Container: Muss separat gestartet werden für PDF-Ingestion

### Framework Compatibility
| Framework | Status | Notes |
|-----------|--------|-------|
| PyTorch cu130 | Works | `--index-url https://download.pytorch.org/whl/cu130` |
| NGC Container | Works | `nvcr.io/nvidia/pytorch:25.09-py3` |
| llama.cpp | Works | Native CUDA compilation |
| PyTorch cu128 | Fails | `nvrtc: invalid value for --gpu-architecture` |
| TensorFlow | Unsupported | Not yet supported on DGX Spark |
| TensorRT | Fails | Not yet  sm_121 support |

### Required Environment
```bash
export TORCH_CUDA_ARCH_LIST="12.1a"
export CUDACXX=/usr/local/cuda-13.0/bin/nvcc
```

### Flash Attention Workaround
```python
import torch
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(True)
```

---

## Repository Structure

```
aegis-rag/
├── src/
│   ├── agents/                  # LangGraph Agents
│   │   ├── coordinator/         # Query routing & orchestration
│   │   ├── vector_agent/        # Vector search execution
│   │   ├── graph_agent/         # Graph reasoning
│   │   ├── memory_agent/        # Memory retrieval
│   │   └── action_agent/        # Tool execution (MCP)
│   ├── domains/                 # Domain-driven structure (Sprint 56+)
│   │   ├── document_processing/ # Ingestion & chunking
│   │   ├── knowledge_graph/     # Graph extraction & reasoning
│   │   ├── vector_search/       # Vector retrieval
│   │   │   ├── embedding/       # BGE-M3 embeddings (planned Sprint 61)
│   │   │   └── reranking/       # Cross-encoder reranking (planned Sprint 61)
│   │   ├── memory/              # Graphiti + Redis
│   │   └── llm_integration/     # AegisLLMProxy
│   │       └── tools/           # Tool framework (Sprint 59)
│   ├── core/                    # Config, Logging, Models
│   └── api/                     # FastAPI Endpoints
├── tests/                       # Unit, Integration, E2E tests
├── frontend/                    # React 19 Frontend + Playwright E2E
├── docs/                        # Documentation
│   ├── adr/                     # Architecture Decision Records
│   ├── sprints/                 # Sprint Plans & Reports
│   ├── technical-debt/          # Technical debt items
│   ├── archive/                 # Archived documentation
│   └── analysis/                # Technical investigations
└── docker/                      # Dockerfiles & compose files
```

---

## Development Workflow

### Feature-Based Development
- **1 Feature = 1 Commit** (Atomic Rollbacks)
- Feature-ID: `{Sprint}.{Nr}` (e.g., 38.1, 38.2)

### Branch Strategy
- `main`: Production-ready
- `feature/*`: Feature branches
- `fix/*`: Bug fixes

### Commit Convention
```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
Scopes: vector, graph, memory, agent, api, infra
```

### Code Quality Gates
- **Linting:** Ruff
- **Formatting:** Black (line-length=100)
- **Types:** MyPy (strict)
- **Testing:** pytest (>80% coverage)

---

## Subagent Responsibilities

| Subagent | Focus |
|----------|-------|
| **Backend** | LangGraph agents, retrieval algorithms, memory logic |
| **Infrastructure** | Docker, K8s, CI/CD, monitoring |
| **API** | FastAPI routers, Pydantic models, OpenAPI |
| **Testing** | Unit, integration, E2E tests |

---

## Environment Variables

```bash
# Ollama (Primary)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=Nemotron3

# Alibaba Cloud DashScope
ALIBABA_CLOUD_API_KEY=sk-...
MONTHLY_BUDGET_ALIBABA_CLOUD=10.0

# Databases
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
REDIS_HOST=localhost
```

---

## Performance Requirements

| Metric | Target |
|--------|--------|
| Simple Query (Vector) | <200ms p95 |
| Hybrid Query (Vector+Graph) | <500ms p95 |
| Complex Multi-Hop | <1000ms p95 |
| Sustained Load | 50 QPS |

---

## Testing Strategy

### Test Categories
- **Unit Tests:** Mocked dependencies, fast (<1s)
- **Integration Tests:** Real services (Qdrant, Neo4j, Redis)
- **E2E Tests:** Full flows with Playwright

### Lazy Import Patching (Critical!)

When patching lazy imports, **patch at source module**, not caller:

```python
# WRONG
patch("src.api.v1.chat.get_redis_memory")

# CORRECT
patch("src.components.memory.get_redis_memory")
```

---

## Key ADRs

| ADR | Decision |
|-----|----------|
| ADR-024 | BGE-M3 embeddings (1024-dim) |
| ADR-026 | Pure LLM extraction pipeline |
| ADR-027 | Docling CUDA for ingestion |
| ADR-033 | AegisLLMProxy multi-cloud routing |
| ADR-039 | Adaptive section-aware chunking |
| ADR-040 | RELATES_TO semantic relationships |

---


## Quick Commands

```bash
# Start services
docker compose up -d

# Run tests
pytest tests/unit -v
pytest tests/integration -v

# Start API
uvicorn src.api.main:app --reload --port 8000

# Check health
curl http://localhost:8000/health
```

---

## Sprint-Abschluss: Dokumentations- & Container-Update Checkliste

**Nach jedem Sprint MÜSSEN folgende Schritte durchgeführt werden:**

### 1. Dokumentation aktualisieren (MANDATORY)

**A. ADR erstellen/aktualisieren (wenn architektonische Entscheidungen):**
- Neue ADR in `docs/adr/ADR-XXX-title.md` erstellen
- `docs/adr/ADR_INDEX.md` aktualisieren

**B. DECISION_LOG.md aktualisieren (ALWAYS):**
- Neue Sektion für Sprint XX mit allen Entscheidungen
- Format: `### 2026-XX-XX | Decision Title (Sprint XX.Y)`
- **Total Decisions** + **Current/Next Sprint** am Ende aktualisieren

**C. TECH_STACK.md aktualisieren (bei neuen Dependencies/Frameworks):**
- Neue Dependencies mit Versions-Nummern dokumentieren
- Beispiele: RAGAS 0.3.9→0.4.2, DSPy 2.5+, neue npm packages

**D. ARCHITECTURE.md aktualisieren (bei System-Architektur-Änderungen):**
- Neue Komponenten/Module dokumentieren
- Interaktions-Diagramme + Performance-Metriken aktualisieren

**E. SPRINT_PLAN.md aktualisieren (ALWAYS):**
- Sprint XX Status: 📝 Planned → ✅ Complete
- **Cumulative Story Points** aktualisieren
- Nächsten Sprint-Eintrag anlegen

**F. README.md aktualisieren (Major Features):**
- **Current Sprint Status** aktualisieren
- Key Achievements + Performance Metrics hinzufügen

**G. CLAUDE.md aktualisieren (ALWAYS - Sprint Summary):**
- Sprint XX Complete Zeile hinzufügen (max 1 Zeile, kompakt)
- Format: `**Sprint XX Complete:** Hauptfeatures + Metriken`

**H. Root-Verzeichnis bereinigen (wenn temporäre Dokumentations-Artefakte vorhanden):**
- Temporäre Markdown-Dateien aus Root löschen (z.B. `TEMP_ANALYSIS.md`, `NOTES.md`)
- Sprint-spezifische Notizen nach `docs/sprints/archive/` verschieben
- Nur permanente Docs im Root behalten: `README.md`, `CLAUDE.md`, `CHANGELOG.md`

**I. Behobene Technical Debt archivieren (wenn TDs gelöst wurden):**
- Gelöste TD-Dateien von `docs/technical-debt/` nach `docs/technical-debt/archive/` verschieben
- TD_INDEX.md aktualisieren: Eintrag als "✅ RESOLVED (Sprint XX)" markieren
- **Active TD Count** und **Total SP** im TD_INDEX.md Footer aktualisieren
- Beispiel: `TD-096` (RAGAS Timeouts) wird in Sprint 79 gelöst → nach `archive/TD-096-ragas-timeout.md`

---

### 2. Docker Container neu bauen (MANDATORY)

**Nach jedem Sprint müssen die Docker Container neu gebaut werden:**

```bash
# 1. API Container neu bauen (enthält Backend Code)
docker compose -f docker-compose.dgx-spark.yml build --no-cache api

# 2. Test Container neu bauen (enthält Tests)
docker compose -f docker-compose.dgx-spark.yml build --no-cache test

# 3. Docling Container (nur bei Änderungen am Ingestion Code)
docker compose -f docker-compose.dgx-spark.yml build --no-cache docling

# 4. Alle Container neu starten
docker compose -f docker-compose.dgx-spark.yml up -d
```

**Container-Images prüfen:**
```bash
# Image-Datum prüfen (sollte nach Sprint-Commit sein)
docker images aegis-rag-api --format "{{.CreatedAt}}"
docker images aegis-rag-test --format "{{.CreatedAt}}"
```

**Wichtig:** Die Datenbank-Container (Qdrant, Neo4j, Redis, Ollama) müssen NICHT neu gebaut werden - diese verwenden offizielle Images.

---

### 3. Sprint-Abschluss-Commit (OPTIONAL)

```bash
# Nach allen Dokumentations-Updates:
git add docs/ README.md CLAUDE.md
git commit -m "docs(sprintXX): Complete Sprint XX documentation

- ADR-XXX: [Decision Title]
- DECISION_LOG.md: X new decisions
- ARCHITECTURE.md: [Changes]
- SPRINT_PLAN.md: Sprint XX Complete
- [weitere Änderungen]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Automatisierung:** Aktuell NICHT automatisiert - manuelle Checkliste erforderlich. Zukünftig (Sprint 80+) könnte `scripts/sprint_close.py` + Git Hooks teilweise automatisieren.

**Sprint 64 Complete:** Domain training optimization, LLM config backend integration (Redis persistence, 60s cache), multi-turn research agents, section-aware citations, production deployment (Docker Compose + Nginx @ 192.168.178.10), E2E testing (337/594 passed).
**Sprint 65 Complete:** CUDA optimization for embeddings (10-80x speedup), critical E2E test fixes, performance improvements.
**Sprint 66 Complete:** Document upload pipeline stabilization, VLM metadata, Admin UI fixes.
**Sprint 67 Complete:** Secure Shell Sandbox, Agents Adaptation Framework, C-LARA Intent Classifier (60%→89.5% accuracy), 195 tests passing, 3,511 LOC.
**Sprint 68 Complete:** E2E test completion (594→606 tests, 57%→100%), performance optimization (500ms→320ms P95), section community detection, cache optimization.
**Sprint 69 Complete:** LLM streaming (TTFT 320ms→87ms), model selection (3-tier routing), learned reranker weights, query rewriter v2, production monitoring (Prometheus + Grafana).
**Sprint 70 Complete:** Deep Research Repair + Tool Use Integration.
**Sprint 71 Complete:** SearchableSelect Component, Backend APIs (/graph/documents, /sections), Original Filenames, 22/23 E2E tests (96%).
**Sprint 72 Complete:** API-Frontend Gap Closure (MCP, Domain, Memory UI), Gap 72%→60% (18 endpoints), 100% E2E (594 tests).
**Sprint 73 Complete:** E2E Test Infrastructure & Documentation, Chat Interface tests (10/10), Integration test analysis.
**Sprint 74 Complete:** RAGAS Integration & Quality Metrics, Timeouts 60s→180s, RAGAS tests (20 questions, 8 tests), Retrieval comparison.
**Sprint 75 Complete:** Critical Architecture Gap Discovery (TD-084: Namespace Isolation, TD-085: DSPy), Infrastructure fixes (Ollama 32K, PyTorch cu130).
**Sprint 76 Complete:** .txt File Support + RAGAS Baseline (15 HotpotQA files, 146 entities, 38 types), Entity extraction fix, RAGAS (Faithfulness 80%, Relevancy 93%).
**Sprint 77 Complete:** Critical Bug Fixes (BM25 namespace, chunk mismatch, Qdrant index), Community Summarization (92/92, batch job + API), Entity Connectivity Benchmarks (4 domains), 2,108 LOC.
**Sprint 78 Complete:** Graph Entity→Chunk Expansion (100-char→447-char full chunks), 3-Stage Semantic Search (LLM→Graph N-hop→Synonym→BGE-M3), 4 UI settings (hops 1-3, threshold 5-20), 20 unit tests (100%), ADR-041, RAGAS deferred (GPT-OSS:20b 85.76s, Nemotron3 >600s).
**Sprint 79 Planned:** DSPy RAGAS Optimization (21 SP), Target: GPT-OSS:20b <20s (4x), Nemotron3 <60s (10x), ≥90% accuracy, 5 features (DSPy integration, optimized prompts, benchmarking, evaluation).

---

## Links

**Core Documentation:**
- [Architecture](docs/ARCHITECTURE.md)
- [Technology Stack](docs/TECH_STACK.md)
- [Code Conventions](docs/CONVENTIONS.md)
- [Context Refresh](docs/CONTEXT_REFRESH.md)

**Project Planning:**
- [Sprint Plans](docs/sprints/)
- [ADR Index](docs/adr/ADR_INDEX.md)
- [Technical Debt Index](docs/technical-debt/TD_INDEX.md)

**External Resources:**
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Documentation](https://neo4j.com/docs/)
