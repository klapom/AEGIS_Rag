# Repository Structure
## AegisRAG Project

Verzeichnisstruktur und Ablagekonventionen.

**Last Updated:** 2025-12-09

---

## Root Directory

```
AEGIS_RAG/
├── CLAUDE.md                       # Projekt-Kontext für Claude Code
├── README.md                       # Projekt-Übersicht
├── pyproject.toml                  # Poetry Dependencies
├── Makefile                        # Build-Kommandos
├── docker-compose.yml              # Development Stack
├── docker-compose.dgx-spark.yml    # DGX Spark Stack
├── .env.template                   # Environment-Variablen Template
├── .env.dgx-spark.template         # DGX Spark Template
├── .pre-commit-config.yaml         # Pre-commit Hooks
├── .gitignore                      # Git Ignore
│
├── src/                            # Backend Source Code
├── frontend/                       # React Frontend
├── tests/                          # Tests
├── docs/                           # Dokumentation
├── scripts/                        # Utility Scripts
├── docker/                         # Dockerfiles
├── data/                           # Daten (gitignored)
├── config/                         # Konfigurationsdateien
├── monitoring/                     # Prometheus/Grafana Configs
└── .claude/                        # Claude Code Konfiguration
```

---

## Source Code (src/)

### Agents (src/agents/)

LangGraph Multi-Agent System.

```
src/agents/
├── __init__.py
├── coordinator.py              # Haupt-Orchestrator
├── vector_search.py            # Qdrant Hybrid Search
├── graph_query.py              # Neo4j + LightRAG
├── memory.py                   # Graphiti Memory
├── action.py                   # MCP Tool Execution
├── followup_generator.py       # Follow-up Fragen
└── title_generator.py          # Conversation Titles
```

### API (src/api/)

FastAPI REST Endpoints.

```
src/api/
├── main.py                     # App Entry Point
├── auth/                       # Authentication
│   └── jwt.py                  # JWT Handler
├── health/                     # Health Checks
│   └── endpoints.py
├── middleware/                 # Middleware
│   └── rate_limit.py
├── models/                     # API Models
│   └── requests.py
├── routers/                    # Zusätzliche Router
│   └── graph_viz.py            # Graph Visualization
└── v1/                         # API v1 Endpoints
    ├── admin.py                # Admin Endpoints
    ├── annotations.py          # VLM Annotations
    ├── chat.py                 # Chat/Query
    ├── memory.py               # Memory Access
    ├── query.py                # Search Queries
    └── title_generator.py      # Title Generation
```

### Components (src/components/)

Kern-Komponenten des Systems.

```
src/components/
├── graph_rag/                  # Knowledge Graph
│   ├── lightrag_client.py      # LightRAG Integration
│   ├── neo4j_client.py         # Neo4j Client
│   └── llm_extraction.py       # Entity/Relation Extraction
│
├── ingestion/                  # Document Ingestion
│   ├── docling_client.py       # Docling CUDA Client
│   ├── format_router.py        # Format Routing
│   ├── langgraph_pipeline.py   # 6-Node Pipeline
│   ├── langgraph_nodes.py      # Pipeline Nodes
│   ├── ingestion_state.py      # State Definitions
│   ├── streaming_pipeline.py   # Streaming Orchestrator
│   ├── image_processor.py      # VLM Image Processing
│   └── hybrid_chunker.py       # Section-Aware Chunking
│
├── llm_proxy/                  # LLM Routing
│   ├── aegis_llm_proxy.py      # Multi-Cloud Proxy
│   ├── cost_tracker.py         # SQLite Cost Tracking
│   └── dashscope_vlm.py        # Alibaba VLM Client
│
├── mcp/                        # Model Context Protocol
│   ├── client.py               # MCP Client
│   └── server.py               # MCP Server
│
├── memory/                     # Memory Layer
│   ├── graphiti_client.py      # Graphiti Integration
│   ├── redis_memory.py         # Redis Short-Term
│   └── consolidation.py        # Memory Consolidation
│
├── profiling/                  # User Profiling
│   ├── conversation_archiver.py
│   └── user_profile.py
│
├── retrieval/                  # Retrieval Components
│   ├── reranking.py            # Cross-Encoder
│   ├── query_decomposition.py  # Query Analysis
│   └── rrf_fusion.py           # Reciprocal Rank Fusion
│
├── sandbox/                    # Secure Execution
│   └── bubblewrap.py           # Shell Sandbox
│
├── shared/                     # Shared Services
│   ├── embedding_service.py    # BGE-M3 Embeddings
│   └── chunking_service.py     # Unified Chunking
│
├── temporal_memory/            # Temporal Memory
│   └── retention_policy.py
│
└── vector_search/              # Vector Search
    ├── qdrant_client.py        # Qdrant Client
    ├── bm25_search.py          # BM25 Index
    └── hybrid_search.py        # Hybrid Search + RRF
```

### Core (src/core/)

Infrastruktur und Konfiguration.

```
src/core/
├── config.py                   # Pydantic Settings
├── logging.py                  # Structured Logging
├── models.py                   # Shared Models
└── exceptions.py               # Custom Exceptions
```

### Weitere Verzeichnisse

```
src/
├── evaluation/                 # RAGAS Evaluation
├── models/                     # Pydantic Models
├── monitoring/                 # Prometheus Metrics
├── prompts/                    # Prompt Templates
├── ui/                         # Gradio UI (Legacy)
└── utils/                      # Utility Functions
```

---

## Frontend (frontend/)

React 19 + TypeScript Frontend.

```
frontend/
├── package.json                # NPM Dependencies
├── vite.config.ts              # Vite Configuration
├── tailwind.config.js          # Tailwind CSS
├── tsconfig.json               # TypeScript Config
├── playwright.config.ts        # E2E Test Config
│
├── public/                     # Static Assets
│
├── src/
│   ├── App.tsx                 # Root Component
│   ├── main.tsx                # Entry Point
│   │
│   ├── api/                    # API Client
│   │   └── client.ts
│   │
│   ├── components/             # UI Components
│   │   ├── admin/              # Admin UI
│   │   ├── auth/               # Authentication
│   │   ├── chat/               # Chat Interface
│   │   ├── dashboard/          # Dashboard
│   │   ├── graph/              # Graph Visualization
│   │   ├── history/            # Conversation History
│   │   ├── layout/             # Layout Components
│   │   ├── search/             # Search UI
│   │   └── settings/           # Settings
│   │
│   ├── contexts/               # React Contexts
│   │   ├── AuthContext.tsx
│   │   └── SettingsContext.tsx
│   │
│   ├── hooks/                  # Custom Hooks
│   │   ├── useStreamChat.ts
│   │   └── useSessions.ts
│   │
│   ├── pages/                  # Page Components
│   │   ├── HomePage.tsx
│   │   ├── LoginPage.tsx
│   │   └── admin/
│   │
│   ├── types/                  # TypeScript Types
│   │   ├── chat.ts
│   │   └── graph.ts
│   │
│   └── utils/                  # Utilities
│
└── e2e/                        # Playwright E2E Tests
    ├── fixtures/               # Test Fixtures
    ├── pom/                    # Page Object Models
    └── tests/                  # Test Specs
```

---

## Documentation (docs/)

### Root Level (docs/)

Essentielle Dokumentation.

```
docs/
├── CONTEXT_REFRESH.md          # Context Recovery Guide
├── TECH_STACK.md               # Technology Stack
├── ARCHITECTURE_EVOLUTION.md   # Architektur-Geschichte
├── NAMING_CONVENTIONS.md       # Code Standards
├── STRUCTURE.md                # Diese Datei
└── COMPONENT_INTERACTION_MAP.md
```

### Subdirectories

```
docs/
├── adr/                        # Architecture Decision Records
│   ├── ADR_INDEX.md            # ADR Index
│   └── ADR-001 bis ADR-043     # Einzelne ADRs
│
├── api/                        # API Dokumentation
│   ├── ENDPOINTS.md
│   ├── SSE_STREAMING.md
│   └── ERROR_CODES.md
│
├── analysis/                   # Analysen
│
├── examples/                   # Code-Beispiele
│
├── features/                   # Feature-Dokumentation
│
├── guides/                     # How-To Guides
│   ├── PRODUCTION_DEPLOYMENT_GUIDE.md
│   ├── CI_CD_GUIDE.md
│   └── GPU_REQUIREMENTS.md
│
├── operations/                 # Operations Docs
│   └── DGX_SPARK_DEPLOYMENT.md
│
├── reference/                  # Referenzen
│   └── GRAPHITI_REFERENCE.md
│
├── sprints/                    # Sprint Documentation
│   ├── SPRINT_PLAN.md          # Master Sprint Plan
│   ├── SPRINT_*_PLAN.md        # Sprint Plans
│   └── archive/                # Archivierte Sprints
│
├── technical-debt/             # Technical Debt Tracking
│   └── TD-*.md                 # Tech Debt Items
│
└── testing/                    # Testing Guides
```

---

## Tests (tests/)

```
tests/
├── conftest.py                 # Shared Fixtures
│
├── unit/                       # Unit Tests
│   ├── agents/
│   ├── api/
│   ├── components/
│   │   ├── graph_rag/
│   │   ├── ingestion/
│   │   ├── llm_proxy/
│   │   ├── mcp/
│   │   ├── memory/
│   │   ├── retrieval/
│   │   ├── sandbox/
│   │   ├── shared/
│   │   └── vector_search/
│   └── core/
│
├── integration/                # Integration Tests
│   ├── agents/
│   ├── api/
│   ├── components/
│   └── memory/
│
├── e2e/                        # E2E Tests
│
├── performance/                # Performance Tests
│
└── fixtures/                   # Test Fixtures
```

---

## Data (data/) - Gitignored

```
data/
├── documents/                  # Indexed Documents
├── uploads/                    # Upload Staging
├── cache/                      # Embedding Cache
├── lightrag/                   # LightRAG Storage
├── models/                     # Model Cache
├── sample_documents/           # Sample Data
└── evaluation/                 # Evaluation Data
```

---

## Infrastructure

### Docker (docker/)

```
docker/
├── Dockerfile.api              # API Container
└── Dockerfile.worker           # Worker Container
```

### Monitoring (monitoring/)

```
monitoring/
├── prometheus/
│   └── prometheus.yml          # Prometheus Config
└── grafana/
    └── dashboards/             # Grafana Dashboards
```

### Configuration (config/)

```
config/
└── grafana/                    # Grafana Configs
```

### GitHub (.github/)

```
.github/
├── workflows/
│   └── ci.yml                  # CI/CD Pipeline
├── pull_request_template.md
└── CODEOWNERS
```

---

## Scripts (scripts/)

```
scripts/
├── benchmark_embeddings.py     # Embedding Benchmarks
├── check_adr.py                # ADR Detection
├── check_naming.py             # Naming Convention Check
└── archive/                    # Archivierte Scripts
```

---

## Claude Code (.claude/)

```
.claude/
├── settings.json               # Claude Settings
└── agents/                     # Subagent Definitionen
    ├── api-agent.md
    ├── backend-agent.md
    ├── documentation-agent.md
    ├── infrastructure-agent.md
    └── testing-agent.md
```

---

## Ablagekonventionen

### Neuer Code

| Typ | Ablageort |
|-----|-----------|
| LangGraph Agent | `src/agents/` |
| API Endpoint | `src/api/v1/` |
| Neue Komponente | `src/components/{name}/` |
| Shared Service | `src/components/shared/` |
| Frontend Component | `frontend/src/components/{category}/` |
| Frontend Page | `frontend/src/pages/` |

### Neue Dokumentation

| Typ | Ablageort |
|-----|-----------|
| ADR | `docs/adr/ADR-{NNN}-{name}.md` |
| API Doku | `docs/api/` |
| Guide | `docs/guides/` |
| Sprint Plan | `docs/sprints/SPRINT_{N}_PLAN.md` |
| Tech Debt | `docs/technical-debt/TD-{NNN}_*.md` |
| Archiviert | `docs/sprints/archive/` |

### Konfiguration

| Typ | Ablageort |
|-----|-----------|
| Environment | `.env.template`, `.env.dgx-spark.template` |
| Docker | `docker/Dockerfile.*` |
| Docker Compose | Root (`docker-compose*.yml`) |
| CI/CD | `.github/workflows/` |
| Monitoring | `monitoring/` |
