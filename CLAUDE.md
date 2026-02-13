# CLAUDE.md - AegisRAG Essentials

## Context Loss Recovery
1. [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md)
2. [docs/sprints/SPRINT_PLAN.md](docs/sprints/SPRINT_PLAN.md)
3. [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)
4. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
5. [docs/TECH_STACK.md](docs/TECH_STACK.md)
6. **Erweiterte Infos:** [docs/CLAUDE_extended.md](docs/CLAUDE_extended.md)

---

## Projekt-Übersicht

**AegisRAG** = Agentic Enterprise Graph Intelligence System

| Komponente | Technologie | Zweck |
|-----------|------------|-------|
| Vector Search | Qdrant + BGE-M3 | Dense+Sparse Hybrid Retrieval |
| Graph Reasoning | Neo4j | Entity/Relation Queries |
| Temporal Memory | Graphiti + Redis | 3-Layer Memory |
| Orchestration | LangGraph | Multi-Agent System |
| LLM Routing | AegisLLMProxy | Multi-Cloud (ADR-033) |
| Ingestion | Docling CUDA | GPU-accelerated OCR |
| Evaluation | RAGAS 0.4.2 | 4 Metriken |

---

## Tech Stack (Kurzfassung)

```yaml
Backend: Python 3.12.7, FastAPI, Poetry
Orchestration: LangGraph 0.6.10

DBs:
  Vector: Qdrant 1.11.0 (Dense+Sparse, RRF)
  Graph: Neo4j 5.24 Community
  Memory: Redis 7.x + Graphiti

LLM:
  Chat: Ollama (Nemotron3 Nano 30/3a)
  Extraction: vLLM (port 8001, ADR-059)
  Fallback: Alibaba DashScope
  Embeddings: BGE-M3 (FlagEmbedding)

Ingestion:
  Parser: Docling CUDA (ADR-027)
  Chunking: Section-aware 800-1800 tokens (ADR-039)
  Extraction: LLM Cascade (ADR-026)

Frontend: React 19, TypeScript, Vite 7.1.12, Tailwind
Testing: pytest, Playwright
```

---

## DGX Spark Deployment

**Hardware:** NVIDIA GB10 (Blackwell), CUDA 13.0, 128GB Unified Memory, ARM64

### Services (alle Docker)
```yaml
Frontend:  http://192.168.178.10      # Port 80
Backend:   http://192.168.178.10:8000 # FastAPI
Qdrant:    localhost:6333/6334        # Vector DB
Neo4j:     bolt://localhost:7687      # Graph DB (Browser: 7474)
Redis:     localhost:6379             # Memory/Cache
Ollama:    http://localhost:11434     # Chat (Nemotron3)
vLLM:      http://localhost:8001      # Extraction Engine
Grafana:   http://192.168.178.10:3000 # Monitoring
```

### Quick Start
```bash
# Alle Services starten
docker compose -f docker-compose.dgx-spark.yml up -d

# Logs prüfen
docker logs -f aegis-frontend
docker logs -f aegis-api

# Container neu bauen (nach Code-Änderungen)
docker compose -f docker-compose.dgx-spark.yml build --no-cache api frontend
docker compose -f docker-compose.dgx-spark.yml up -d --force-recreate api frontend
```

### Ingestion API (KRITISCH)

**IMMER Frontend API verwenden:**
```bash
# ✅ RICHTIG
POST http://localhost:8000/api/v1/retrieval/upload
Content-Type: multipart/form-data
file: <binary>
namespace: "test_namespace"
domain: "research_papers"

# Status prüfen
GET http://localhost:8000/api/v1/admin/upload-status/{document_id}
```

---

## Development Workflow

### Feature Development
- **1 Feature = 1 Commit** (Atomic Rollbacks)
- Feature-ID: `{Sprint}.{Nr}` (z.B. 128.1, 128.2)

### Code Quality
```bash
# Linting & Formatting
ruff check src/
black src/ --line-length=100
mypy src/

# Tests
pytest tests/unit -v
pytest tests/integration -v

# E2E Tests (Playwright)
cd frontend
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test
```

---

## Claude Code Subagents

| Agent | Trigger Keywords | Focus |
|-------|------------------|-------|
| **backend-agent** | "implement", "LangGraph", "agent", "retrieval" | Core business logic |
| **api-agent** | "API", "endpoint", "FastAPI", "Pydantic" | REST endpoints |
| **frontend-agent** | "UI", "React", "component", "TypeScript" | React UI |
| **testing-agent** | "test", "pytest", "E2E", "Playwright" | Tests |
| **infrastructure-agent** | "Docker", "deploy", "CI/CD" | Deployment |
| **documentation-agent** | "document", "ADR", "README" | Docs |
| **performance-agent** | "optimize", "benchmark", "profiling" | Performance |
| **rag-tuning-agent** | "RAGAS", "metrics", "evaluate" | RAG optimization |

---

## Environment Variables

```bash
# LLM Engines
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=Nemotron3
VLLM_ENABLED=true
VLLM_BASE_URL=http://localhost:8001
VLLM_MODEL=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4

# Databases
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
REDIS_HOST=localhost

# Cloud Fallback
ALIBABA_CLOUD_API_KEY=sk-...
MONTHLY_BUDGET_ALIBABA_CLOUD=10.0

# LangSmith Tracing (Sprint 115+)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=aegis-rag-sprint115
```

**WICHTIG:** Container nach `.env` Änderungen neu starten:
```bash
docker compose -f docker-compose.dgx-spark.yml up -d --force-recreate api
```

---

## Wichtige ADRs

| ADR | Beschreibung |
|-----|--------------|
| ADR-026 | Pure LLM Extraction Pipeline |
| ADR-027 | Docling CUDA Ingestion |
| ADR-033 | AegisLLMProxy Multi-Cloud Routing |
| ADR-039 | Adaptive Section-Aware Chunking |
| ADR-059 | vLLM Dual-Engine (Ollama/vLLM) |
| ADR-060 | S-P-O Entity Extraction (15+22 Types) |
| ADR-062 | LLM Engine Mode (vLLM/Ollama/Auto) |

---

## Sprint-Abschluss

**Verwende `/commit` — deckt alle Docs-Updates ab (A-J):** SPRINT_PLAN, DECISION_LOG, CLAUDE.md, TECH_STACK, ADR_INDEX, Root Cleanup, ARCHITECTURE, README, TD-Archivierung, scripts/README.

**Docker Rebuild nach Sprint:**
```bash
docker compose -f docker-compose.dgx-spark.yml build --no-cache api frontend
docker compose -f docker-compose.dgx-spark.yml up -d
```

---

## Quick Commands

```bash
# Services starten
docker compose -f docker-compose.dgx-spark.yml up -d

# Logs
docker logs -f aegis-api
docker logs -f aegis-frontend

# Health Check
curl http://localhost:8000/health

# API neu laden
docker compose -f docker-compose.dgx-spark.yml restart api

# Tests
pytest tests/unit -v
cd frontend && npx playwright test
```

---

## Aktuelle Sprint-Highlights

**Sprint 128 Complete:** LightRAG Removal (-6,660 LOC), Cascade Guard, HyDE, vLLM eugr SM121 (0 CUDA crashes), Domain Prompt Verification (27/35), E2E Benchmarks (15-doc: 212 entities, 626 relations, 84.5% relation specificity), MAX_RELATIONSHIPS cap removed, Chat Benchmark (Ollama 64 vs vLLM 55 tok/s). 30 SP (128.3 carried to 129).

**Previous Sprints:** 127 (RAGAS CP=0.739, CR=0.760), 126 (LLM Engine Mode, community batch jobs), 125 (vLLM dual-engine, S-P-O extraction), 121 (ChunkingService removal, -1,727 LOC), 120 (Ollama 3→74 tok/s), 115 (Graph 27s→1.4s), 92 (Graph <2s, Frontend Docker).

---

## Links

- [Extended Info](docs/CLAUDE_extended.md) - DGX Spark Details, vLLM, Ollama, Playwright, Repo-Struktur
- [Architecture](docs/ARCHITECTURE.md)
- [Tech Stack](docs/TECH_STACK.md)
- [Sprint Plans](docs/sprints/)
- [ADR Index](docs/adr/ADR_INDEX.md)
- [TD Index](docs/technical-debt/TD_INDEX.md)
