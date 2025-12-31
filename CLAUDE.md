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

## Sprint-Abschluss: Docker Container Update

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

**Sprint 64 Complete:** Domain training optimization, LLM config backend integration (Redis persistence, 60s cache), multi-turn research agents, section-aware citations, production deployment (Docker Compose + Nginx @ 192.168.178.10), E2E testing (337/594 passed - core journeys working).
**Sprint 65 Upcoming:** Fix critical E2E failures (follow-up questions, domain training timeouts), performance optimizations (history loading, graph filters), test infrastructure improvements.

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
