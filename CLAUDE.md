# CLAUDE.md - AegisRAG Project Context

## 🔄 Session Continuity Check

**Falls diese Session kompaktiert wurde:**
1. **DEEP CONTEXT REFRESH:** Lies [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md) für vollständigen Projekt-Context
2. Lies dieses gesamte CLAUDE.md Dokument (inkl. Subagent Responsibilities weiter unten)
3. Checke docs/sprints/SPRINT_PLAN.md für aktuellen Sprint-Status
4. Verifiziere ADR-Awareness aus docs/adr/ADR_INDEX.md
5. Bestätige Naming Conventions aus docs/NAMING_CONVENTIONS.md

**Zeichen für Context Loss:**
- Du kennst Projekt-Struktur nicht mehr
- Du fragst nach bereits beantworteten Architektur-Fragen
- Du nutzt Subagenten nicht mehr systematisch (siehe "Subagent Responsibilities" weiter unten)
- Du hältst dich nicht an Naming Conventions

→ Dann: **docs/CONTEXT_REFRESH.md lesen** (umfassender Context Refresh mit 3 Strategien)

---

## 📍 Current Project State (Sprint 32)

**Sprint 20 Status**: ✅ COMPLETE (2025-10-31 - 2025-11-06)
- ✅ Performance Optimization & Extraction Quality
- ✅ Chunk overhead analysis (65% overhead identified with 600-token chunks)
- ✅ LLM extraction quality improvements
- ✅ Pure LLM pipeline introduced (ADR-026)
- ✅ Preparation for 1800-token chunking strategy

**Sprint 21 Status**: ✅ COMPLETE (2025-11-07 - 2025-11-10, branch: `sprint-21-container-ingestion`)
- **Objective**: Container-based document ingestion with GPU-accelerated OCR
- **Key Achievements**:
  - ✅ **Docling CUDA Container Integration** (ADR-027)
    - GPU-accelerated OCR (EasyOCR): 95% accuracy (vs 70% LlamaIndex)
    - Table structure preservation: 92% detection rate
    - Performance: 420s → 120s per document (3.5x faster)
    - Container isolation: Manage 6GB VRAM allocation
  - ✅ **LlamaIndex Deprecation** (ADR-028)
    - Deprecated as primary ingestion framework
    - Retained as fallback + connector library (300+ connectors)
  - ✅ **LangGraph Pipeline Redesign**
    - 6-node state machine: Docling → VLM → Chunking → Embedding → Graph → Validation
    - 31 integration tests for DoclingContainerClient
  - ✅ **Documentation Cleanup**
    - 4 critical ADRs created (ADR-027 to ADR-030, 1,900+ lines)
    - Sprint 1-9, 13, 18 documentation backfilled (17,132 words)
    - Drift analysis completed (18 drifts identified)

- **Architecture Decisions**:
  - ADR-027: Docling Container vs. LlamaIndex
  - ADR-028: LlamaIndex Deprecation Strategy
  - ADR-029: React Migration Deferral
  - ADR-030: Sprint Extension from 12 to 21+ Sprints

**Sprint 22 Status**: ✅ COMPLETE (2025-11-11, 1 day)
- **Objective**: Post-Sprint 21 cleanup and documentation
- **Key Achievements**:
  - ✅ Repository organization and cleanup
  - ✅ Test execution report (Sprint 22)
  - ✅ Comprehensive documentation review

**Sprint 23 Status**: ✅ COMPLETE (2025-11-11 - 2025-11-13, branch: `main`)
- **Objective**: Multi-Cloud LLM Execution & VLM Integration
- **Key Achievements**:
  - ✅ AegisLLMProxy Implementation (ADR-033) - 509 LOC unified routing
  - ✅ Alibaba Cloud DashScope Integration (Qwen models)
  - ✅ SQLite Cost Tracker - 389 LOC persistent tracking
  - ✅ DashScope VLM Client - 267 LOC with qwen3-vl models
  - ✅ LangGraph Pipeline Migration (4 components migrated)
- **Architecture Decisions**:
  - ADR-032: Multi-Cloud Execution Strategy
  - ADR-033: ANY-LLM Integration (ACCEPTED)

**Sprint 24 Status**: ✅ COMPLETE (2025-11-14, 1 day)
- **Objective**: Dependency Optimization & CI Performance
- **Key Achievements**:
  - ✅ 85% CI speedup (Poetry cache optimization)
  - ✅ 60% dependency reduction (Poetry dependency groups)
  - ✅ Lazy imports for optional dependencies (5 core files)
  - ✅ 725+ lines of deprecated code removed

**Sprint 25 Status**: ✅ COMPLETE (2025-11-15, 1 day - accelerated with 4 parallel agents!)
- **Objective**: Production Readiness & LLM Architecture Consolidation
- **Key Achievements**:
  - ✅ **10 Features Delivered** (45 SP, 100% complete)
  - ✅ **Feature 25.1:** Prometheus Metrics + Grafana Dashboard (5 SP)
  - ✅ **Feature 25.2:** LangGraph Integration Tests (5 SP)
  - ✅ **Feature 25.3:** Token Tracking Accuracy Fix (3 SP) - 20% more accurate costs
  - ✅ **Feature 25.4:** Async/Sync Bridge Refactoring (5 SP) - 40 lines removed
  - ✅ **Feature 25.5:** MyPy Strict Mode (2 SP) - CI enforced
  - ✅ **Feature 25.6:** Architecture Documentation Update (2 SP) - 3,574 lines
  - ✅ **Feature 25.7:** Remove Deprecated Code (5 SP) - 549 lines removed
  - ✅ **Feature 25.8:** Consolidate Duplicate Code (3 SP) - 300 lines removed
  - ✅ **Feature 25.9:** Standardize Client Naming (2 SP) - 4 clients renamed
  - ✅ **Feature 25.10:** ALL LLM Calls Migrated to AegisLLMProxy (5 SP) ⭐⭐⭐
    - 7 files migrated: router.py, extraction_service.py, graphiti_wrapper.py, community_labeler.py, dual_level_search.py, custom_metrics.py, image_processor.py
    - $11,750/year cost visibility achieved
    - 34/35 unit tests passing
    - Complete cost tracking via SQLite
    - Multi-cloud routing: Local → Alibaba → OpenAI
    - Architecture consistency (ADR-033 compliance)
- **Performance**: 45 SP in 1 day (vs estimated 8 days) = 8x acceleration!
- **Code Metrics**: +3,117 lines added, -1,626 lines removed (net -796 refactoring)
- **ADR Compliance**: 100% (ADR-026, ADR-027, ADR-028, ADR-033)

**Sprint 30 Status**: ✅ COMPLETE (2025-11-20, 1 day - branch: `main`)
- **Objective**: Frontend Production Testing & Missing Feature Implementation
- **Key Achievements**:
  - ✅ **Feature 27.10: Inline Source Citations** - NACHGEHOLT & PRODUCTION READY ⭐⭐⭐
    - **Context**: Feature wurde in Sprint 27 vergessen und während Sprint 30 Testing nachimplementiert
    - Citation generation with [1], [2] markers in LLM responses
    - citation_map in LangGraph state for source metadata
    - SSE streaming support for real-time citation display
    - 19/19 Citation tests passing (12 Unit + 7 Frontend E2E)
  - ✅ **Test Infrastructure Improvements** (während Citation-Implementierung)
    - Lazy Import Pattern documented in CLAUDE.md (comprehensive guide)
    - Testing Best Practices in SUBAGENTS.md (quick reference)
    - 9 commits: poetry.lock sync → Black formatting → Sprint documentation
    - Fixed 10+ pre-existing test issues (mock paths, API URLs, IntentClassifier assertions)
  - ✅ **CI/CD Quality Gates**
    - Code Quality: Black, Ruff, MyPy all passing ✅
    - Unit Tests: 467 passed (Citation tests: 12/12) ✅
    - Frontend Tests: E2E + Unit all passing ✅
- **Lessons Learned**:
  - Lazy imports require patching at source module, not caller
  - Integration tests should have realistic assertions (e.g., accept HYBRID intent)
  - API router prefixes must be included in test URLs
  - Black formatting: prefer single-line for short .format() calls
  - Feature tracking: Vergessene Features können während Testing nachgeholt werden
- **Code Metrics**: 9 commits, +138 lines documentation, -5 lines refactoring
- **Test Coverage**: 19/19 Citation tests passing, Feature PRODUCTION READY

**Sprint 31 Status**: ✅ COMPLETE (2025-11-21, branch: `main`)
- **Objective**: Comprehensive E2E Test Coverage & Frontend Architecture Improvements
- **Key Achievements**:
  - ✅ **E2E Test Infrastructure Setup** (Feature 31.1)
    - Playwright E2E framework mit 111 tests (100 User + 11 Admin)
    - Page Object Model (POM) pattern für alle Features
    - Real LLM backend integration (Alibaba Cloud Qwen / Local Ollama)
    - Fixtures für Backend/Frontend lifecycle management
  - ✅ **Frontend Dependency Optimization** (Feature 31.2)
    - react-force-graph → react-force-graph-2d + react-force-graph-3d migration
    - 103 AFRAME packages removed (dependency bloat eliminated)
    - Standalone packages for 2D/3D graph visualization
    - Build errors fixed, TypeScript types corrected
  - ✅ **HomePage → ChatPage Transformation** (Feature 31.11 - CRITICAL FIX)
    - **Problem**: E2E tests expected chat interface on `/` but found only landing page
    - **Solution**: Transformed HomePage into full-featured chat interface
    - Inline message input with `data-testid="message-input"`
    - Streaming responses rendered in-place (no navigation)
    - Conversation history with session management
    - Citations, Follow-up Questions, Message data-testids
  - ✅ **AdminIndexingPage Implementation** (Feature 31.7)
    - Complete Admin UI for document indexing (399 LOC)
    - SSE streaming progress, cancellation support
    - All 10 required data-testid attributes
    - Route registered at `/admin/indexing`
- **Test Coverage**:
  - 100 User Frontend E2E Tests (Citations, Error Handling, Search, History, Graph, Settings)
  - 11 Admin E2E Tests (Indexing, Graph Analytics, Cost Dashboard)
  - Backend: 467 unit tests passing
- **Code Metrics**: 25+ documentation files organized to `docs/sprints/`
- **Architecture**: ChatPage architecture aligned with E2E test expectations

**Sprint 32 Status**: ✅ SUBSTANTIALLY COMPLETE (2025-11-21 - 2025-11-24, branch: `main`)
- **Objective**: Adaptive Section-Aware Chunking (ADR-039) & Admin E2E Testing Documentation
- **Key Achievements**:
  - ✅ **Feature 32.1: Section Extraction from Docling JSON** (8 SP)
    - Extract section hierarchy from Docling JSON (title, subtitle-level-1, subtitle-level-2)
    - 16/16 tests passing, full metadata tracking (headings, pages, bboxes)
    - File: `src/components/ingestion/section_extraction.py` (212 lines)
  - ✅ **Feature 32.2: Adaptive Section Merging Logic** (13 SP)
    - Adaptive merging: large sections >1200 tokens standalone, small sections <1200 tokens merged
    - PowerPoint optimization: 15 slides → 2-3 chunks (was 124 tiny chunks!)
    - 14/14 tests passing, 98% fragmentation reduction
    - File: `src/components/ingestion/langgraph_nodes.py` (Lines 123-271)
  - ✅ **Feature 32.3: Multi-Section Metadata in Qdrant** (8 SP)
    - Store multi-section metadata in Qdrant payloads (section_headings, pages, bboxes)
    - Section-based re-ranking: +10% retrieval precision
    - Citation enhancement: "[1] doc.pdf - Section: 'Load Balancing' (Page 2)"
    - 28+ tests passing, 100% backward compatible
  - ✅ **Features 32.5-32.7: Admin E2E Tests** (21 SP - implemented Sprint 31, documented Sprint 32)
    - Admin Indexing: 10 tests (progress, cancellation, error handling)
    - Admin Analytics: 11 tests (visualization, exports, PageRank)
    - Admin Cost Dashboard: 8 tests (budget tracking, warnings)
- **Features Deferred**:
  - ⏸️ Feature 32.4: Neo4j Section Nodes (13 SP - deferred to Sprint 33, optional P2)
- **Performance Metrics**:
  - PowerPoint chunking: 124 chunks → 2-3 chunks (-98% fragmentation)
  - False relations reduced: +23% baseline → <10% (improvement +13%)
  - Retrieval precision: +10% with section-based re-ranking
  - Citation accuracy: 100% (section names match)
- **Test Coverage**: 87+ tests passing (16 extraction + 14 chunking + 28 qdrant + 29 E2E), 100% pass rate
- **Code Metrics**: +2,213 lines added (implementation + tests), -34 lines removed
- **Story Points**: 50/63 SP delivered (79% completion), 12.5 SP/day velocity
- **ADR Compliance**: ADR-039 (Adaptive Section-Aware Chunking) - ACCEPTED & IMPLEMENTED

**Current Work**: Sprint 32 complete, Sprint 33 planning (Neo4j Section Nodes, BGE-M3 similarity merging)

---

## Project Overview
**AegisRAG** (Agentic Enterprise Graph Intelligence System) ist ein produktionsreifes agentisches RAG-System mit vier Core-Komponenten:

1. **Vector Search** (Qdrant + Hybrid Search)
2. **Graph Reasoning** (LightRAG + Neo4j)
3. **Temporal Memory** (Graphiti + Bi-Temporal Structure)
4. **Tool Integration** (Model Context Protocol Server)

**Orchestration:** LangGraph Multi-Agent System
**Data Ingestion:** Docling CUDA Container + LlamaIndex fallback (ADR-027, ADR-028)
**Entity/Relation Extraction:** Pure LLM (Alibaba Cloud Qwen3-32B, fallback to local Gemma 2 4B) - ADR-026, ADR-037
**Chunking:** Adaptive Section-Aware Chunking (800-1800 tokens, respects document structure) - ADR-039
**Monitoring:** LangSmith + Prometheus + RAGAS

---

## Architecture Principles

### Core Design Patterns
- **Hybrid Retrieval:** Vector Similarity + Graph Traversal + BM25 Keyword
- **Parallel Execution:** Async Retrieval via LangGraph Send API
- **3-Layer Memory:** Redis (Short-Term) → Qdrant (Semantic) → Graphiti (Episodic)
- **Intent-Based Routing:** Query Classifier → Specialized Agents
- **Fail-Safe Design:** Graceful Degradation, Retry with Exponential Backoff

### Technology Stack
```yaml
Backend: Python 3.12.7, FastAPI, Pydantic v2
Dependency Management: Poetry (pyproject.toml)
Orchestration: LangGraph 0.6.10, LangChain Core
Data Ingestion:
  - Primary: Docling CUDA Container (GPU-accelerated OCR, ADR-027)
  - Fallback: LlamaIndex 0.14.3 (connectors only, ADR-028)
Entity/Relation Extraction:
  - Method: Pure LLM Extraction (NO SpaCy, NO Three-Phase) - ADR-026, ADR-037
  - Primary: Alibaba Cloud Qwen3-32B (32B parameters, high quality)
  - Fallback: Local Ollama Gemma 2 4B (automatic fallback on budget exceeded)
  - Routing: AegisLLMProxy with Complexity=HIGH + Quality=HIGH
  - Cost Tracking: SQLite database ($120/month budget)
Chunking Strategy:
  - Method: Adaptive Section-Aware Chunking - ADR-039
  - Size: 800-1800 tokens (adaptive based on section boundaries)
  - Metadata: Multi-section tracking (headings, pages, bounding boxes)
  - Graph Schema: Explicit Section nodes in Neo4j for hierarchical queries
Vector DB: Qdrant 1.11.0
Graph DB: Neo4j 5.24 Community Edition
Memory Cache: Redis 7.x with Persistence
LLM Proxy: AegisLLMProxy (ANY-LLM Core Library, ADR-033)
  - Multi-cloud routing: Local Ollama → Alibaba Cloud → OpenAI
  - Budget tracking with provider-specific limits
  - Cost tracking: SQLite database (persistent tracking)
LLM Models:
  - Local (Ollama):
    - Generation: llama3.2:3b (query) / llama3.2:8b (generation)
    - Extraction: gemma-3-4b-it-Q8_0 (ADR-018)
    - Vision: llava:7b-v1.6-mistral-q2_K (Feature 21.6)
  - Cloud (Alibaba DashScope):
    - Text: qwen-turbo / qwen-plus / qwen-max
    - Vision (VLM):
      - Primary: qwen3-vl-30b-a3b-instruct (cheaper output tokens)
      - Fallback: qwen3-vl-30b-a3b-thinking (on 403 errors, enable_thinking)
    - Best Practices: vl_high_resolution_images=True (16,384 vs 2,560 tokens)
Embeddings: BGE-M3 (1024-dim, multilingual, ADR-024) - Local & Cost-Free
Optional Production: Azure OpenAI GPT-4o (if budget allows)
MCP: Official Python SDK (anthropic/mcp)
Container Runtime: Docker Compose + NVIDIA Container Toolkit (CUDA 12.4)
Frontend:
  - React 19, TypeScript, Vite 7.1.12
  - UI: Tailwind CSS, Lucide Icons
  - Graph Visualization: react-force-graph-2d ^1.29.0, react-force-graph-3d ^1.24.4
  - E2E Testing: Playwright (111 tests with POM pattern)
  - State Management: React Context API
  - Routing: React Router v6
```

### Development Environment

**Operating System:** Windows (Primary Development)
- **Python:** 3.12.7
- **Package Manager:** Poetry (not pip)
- **Shell:** PowerShell / CMD
- **Git:** Git for Windows

**Important Windows-Specific Considerations:**

1. **Dependency Installation:**
   ```bash
   # Use Poetry, NOT pip
   poetry install
   poetry install --with dev  # Include dev dependencies

   # Add new dependencies
   poetry add package-name
   poetry add --group dev package-name  # Dev dependency
   ```

2. **Logging Requirements (Windows Console):**
   ```python
   # ❌ AVOID: Unicode characters in logs (Windows console issues)
   logger.info("✅ Success")  # May display as garbage characters
   logger.info("🚀 Starting")  # May not render correctly

   # ✅ USE: ASCII-safe logging
   logger.info("SUCCESS: Operation completed")
   logger.info("STARTING: Service initialization")

   # ✅ ACCEPTABLE: Unicode in structured fields (not printed to console)
   logger.info("operation_completed", status="success", emoji="✅")  # OK if structlog JSON
   ```

3. **Path Handling:**
   ```python
   # Use pathlib.Path for cross-platform compatibility
   from pathlib import Path

   file_path = Path("data") / "documents" / "file.pdf"  # ✅ Works on Windows & Linux
   file_path = "data\\documents\\file.pdf"  # ❌ Windows-only
   ```

4. **Docker on Windows:**
   - Docker Desktop with WSL2 backend
   - NVIDIA Container Toolkit for CUDA support (GPU acceleration)
   - Windows paths must be converted for Docker volumes: `C:\Users\...` → `/c/Users/...`

5. **Environment Variables:**
   - Use `.env` file (loaded by python-dotenv)
   - Windows: `set VAR=value` (CMD) or `$env:VAR="value"` (PowerShell)
   - Poetry automatically loads `.env` when running commands

**Rationale for Windows:**
- Primary development environment
- NVIDIA GPU support (RTX 3060 6GB)
- Docker Desktop with WSL2 for containerization
- Production deployment will be Linux (Kubernetes)

### Repository Structure
```
aegis-rag/
├── src/
│   ├── agents/              # LangGraph Agents
│   │   ├── coordinator.py
│   │   ├── vector_search.py
│   │   ├── graph_query.py
│   │   ├── action.py
│   │   └── memory.py
│   ├── components/          # Core Components
│   │   ├── ingestion/       # Docling Container + LangGraph Pipeline (Sprint 21)
│   │   ├── vector_search/   # Qdrant + Hybrid Search + BGE-M3
│   │   ├── graph_rag/       # LightRAG + Neo4j + Three-Phase Extraction
│   │   ├── memory/          # Graphiti + Redis
│   │   ├── llm_proxy/       # Multi-Cloud LLM Routing (Sprint 23)
│   │   │   ├── aegis_llm_proxy.py    # ANY-LLM wrapper with routing logic
│   │   │   ├── cost_tracker.py       # SQLite cost tracking (389 LOC)
│   │   │   └── dashscope_vlm.py      # Alibaba Cloud VLM client (267 LOC)
│   │   └── mcp/             # MCP Client (tool integration)
│   ├── core/                # Shared Core
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── models.py        # Pydantic Models
│   │   └── exceptions.py
│   ├── api/                 # FastAPI Endpoints
│   │   ├── v1/
│   │   └── health.py
│   └── utils/               # Helper Functions
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/                 # Deployment & Maintenance
├── config/                  # Configuration Files
├── docker/                  # Dockerfiles
├── k8s/                     # Kubernetes Manifests
├── docs/                    # Documentation
├── .github/                 # CI/CD Workflows
├── pyproject.toml
├── docker-compose.yml
├── CLAUDE.md               # This file
├── SPRINT_PLAN.md
├── ADR/                    # Architecture Decision Records
└── README.md
```

---

## Development Workflow

### 🎯 Feature-basierte Sprint-Entwicklung (WICHTIG!)

**Neue Regel ab Sprint 2:**
Jeder Sprint wird in **einzelne Features** heruntergebrochen, um granulare Git-Commits zu ermöglichen.

**Vorteile:**
✅ 1 Feature = 1 Git Commit (Atomic Rollbacks)
✅ Bessere Nachvollziehbarkeit und Code-Review
✅ Parallele Entwicklung mehrerer Features
✅ Klare Ownership und Zuständigkeiten

**Feature-Definition:**
Jedes Feature hat:
1. **Feature-ID:** {Sprint}.{Nr} (z.B. 2.1, 2.2, 2.3)
2. **Feature-Name:** Kurz und prägnant
3. **Deliverables:** Konkrete Outputs
4. **Technical Tasks:** Implementation Steps
5. **Git Commit:** feat(scope): description
6. **Tests:** Unit + Integration (>80% coverage)
7. **Dependencies:** Benötigt andere Features?

**Beispiel Sprint 2:**
- Feature 2.1: Qdrant Client Foundation
- Feature 2.2: Document Ingestion Pipeline
- Feature 2.3: Embedding Service
- Feature 2.4: Text Chunking Strategy
- Feature 2.5: BM25 Search Engine
- Feature 2.6: Hybrid Search (Vector + BM25)
- Feature 2.7: Retrieval API Endpoints
- Feature 2.8: Security Hardening

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: Feature development (1 Feature = 1 Branch)
- `fix/*`: Bug fixes
- `sprint-N`: Sprint-specific branches

### Commit Convention
```
<type>(<scope>): <subject>

[optional body]
[optional footer]
```

**Types:** feat, fix, docs, style, refactor, test, chore
**Scopes:** vector, graph, memory, mcp, agent, api, infra, security

**Examples:**
```
feat(vector): implement hybrid search with BM25
feat(qdrant): implement client wrapper with connection pooling
feat(security): add P0 input validation and injection prevention
fix(graph): resolve neo4j connection pooling issue
docs(api): add OpenAPI schema for retrieval endpoints
```

**REGEL:** 1 Feature = 1 Commit (außer bei sehr großen Features: dann Feature-Teilschritte)

### Code Quality Gates
- **Linting:** Ruff (replaces Flake8, isort, pyupgrade)
- **Formatting:** Black (line-length=100)
- **Type Checking:** MyPy (strict mode)
- **Security:** Bandit, Safety
- **Testing:** pytest with coverage >80%
- **Pre-commit Hooks:** Auto-run on `git commit`

---

## Subagent Responsibilities

### Backend Subagent (primary)
**Focus:** Core business logic, agent implementation, orchestration
- LangGraph agent definitions
- Retrieval algorithms (Hybrid Search, RRF)
- Memory management logic
- MCP server implementation
- Unit & integration tests

### Infrastructure Subagent
**Focus:** DevOps, deployment, observability
- Docker Compose & Dockerfiles
- Kubernetes manifests (Helm charts)
- CI/CD pipelines (GitHub Actions)
- Monitoring setup (Prometheus, Grafana)
- Database migrations & backups

### API Subagent
**Focus:** REST API, input validation, error handling
- FastAPI routers & endpoints
- Pydantic request/response models
- OpenAPI documentation
- Rate limiting & authentication
- API integration tests

### Testing Subagent
**Focus:** Test coverage, quality assurance
- pytest fixtures & utilities
- Unit tests for all modules
- Integration tests for agents
- E2E tests for user flows
- Performance & load tests

---

## Critical Implementation Details

### LangGraph Agent Pattern
```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

# State Management
class AgentState(MessagesState):
    query: str
    intent: str
    retrieved_contexts: List[Document]
    final_answer: str

# Graph Construction
graph = StateGraph(AgentState)
graph.add_node("router", route_query)
graph.add_node("vector_search", vector_search_agent)
graph.add_node("graph_query", graph_query_agent)
graph.add_node("fusion", context_fusion)
graph.add_node("generate", generation_agent)

# Conditional Routing
graph.add_conditional_edges(
    "router",
    determine_path,
    {
        "vector": "vector_search",
        "graph": "graph_query",
        "hybrid": "vector_search",  # Then parallel to graph
    }
)
```

### Hybrid Search Implementation
```python
# Reciprocal Rank Fusion
def reciprocal_rank_fusion(
    vector_results: List[Document],
    bm25_results: List[Document],
    k: int = 60
) -> List[Document]:
    """Combine vector and keyword search with RRF."""
    scores = defaultdict(float)
    for rank, doc in enumerate(vector_results):
        scores[doc.id] += 1 / (k + rank + 1)
    for rank, doc in enumerate(bm25_results):
        scores[doc.id] += 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### Error Handling Pattern
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def retrieval_with_retry(query: str) -> List[Document]:
    """Retrieve with automatic retry on transient failures."""
    try:
        return await qdrant_client.search(query)
    except QdrantException as e:
        logger.error(f"Retrieval failed: {e}")
        raise
```

---

## Environment Variables

### Required Configuration
```bash
# Ollama (Primary - No API Keys needed!)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=llama3.2:8b
OLLAMA_MODEL_QUERY=llama3.2:3b
OLLAMA_MODEL_EMBEDDING=nomic-embed-text

# Alibaba Cloud DashScope (Sprint 23)
ALIBABA_CLOUD_API_KEY=sk-...  # Required for cloud VLM and text models
ALIBABA_CLOUD_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
# Budget limits (optional, defaults to unlimited)
MONTHLY_BUDGET_ALIBABA_CLOUD=10.0  # USD per month
MONTHLY_BUDGET_OPENAI=20.0         # USD per month

# Optional: Azure OpenAI (Production only)
# USE_AZURE_LLM=false
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_API_KEY=your-api-key
# ANTHROPIC_API_KEY=sk-ant-...  # Optional fallback

# Databases
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=<optional>

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure-password>

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<optional>

# Observability
LANGSMITH_API_KEY=<optional>
LANGSMITH_PROJECT=aegis-rag

# MCP
MCP_SERVER_PORT=3000
MCP_AUTH_ENABLED=true
```

---

## Performance Requirements

### Latency Targets
- **Simple Query (Vector Only):** <200ms p95
- **Hybrid Query (Vector + Graph):** <500ms p95
- **Complex Multi-Hop:** <1000ms p95
- **Memory Retrieval:** <100ms p95

### Throughput
- **Sustained Load:** 50 QPS
- **Peak Load:** 100 QPS (with auto-scaling)

### Resource Limits
- **Memory per Request:** <512MB
- **Total System Memory:** <16GB (excluding DBs)
- **CPU:** <4 cores sustained

---

## Testing Strategy

### Unit Tests (>80% coverage)
- Test each agent in isolation with mocked dependencies
- Test retrieval algorithms with synthetic data
- Test memory consolidation logic

### Integration Tests
- Test agent → component interactions
- Test database operations (Qdrant, Neo4j, Redis)
- Test MCP server communication

### E2E Tests
- Test full query flows (User Query → Final Answer)
- Test multi-turn conversations with memory
- Test error handling and recovery

### Performance Tests
- Load testing with Locust (100 concurrent users)
- Stress testing to find breaking point
- Soak testing (24h sustained load)

### Test Mocking Best Practices

**Critical Pattern: Lazy Import Patching**

When testing code that uses lazy imports (imports inside functions rather than at module level), you **MUST patch at the original source module**, not at the importing module.

**Why Lazy Imports?**
- Avoid circular dependencies
- Reduce startup time
- Make optional dependencies truly optional
- Prevent import-time side effects

**Common Mistake:**
```python
# ❌ WRONG: Trying to patch at the caller module
with patch("src.api.v1.chat.get_redis_memory") as mock:
    # This will fail with AttributeError!
    # get_redis_memory is not defined at module level in chat.py
```

**Correct Approach:**
```python
# ✅ CORRECT: Patch at the original source module
with patch("src.components.memory.get_redis_memory") as mock:
    # This works because get_redis_memory is defined in memory module
```

**Real Examples from AEGIS RAG:**

1. **LightRAG Dependencies** (`test_lightrag_client.py`):
   ```python
   # ❌ Wrong:
   patch("src.components.graph_rag.lightrag_wrapper.AsyncGraphDatabase.driver")

   # ✅ Correct:
   patch("neo4j.AsyncGraphDatabase.driver")

   # ❌ Wrong:
   patch("src.components.graph_rag.lightrag_wrapper.initialize_pipeline_status")

   # ✅ Correct:
   patch("lightrag.kg.shared_storage.initialize_pipeline_status")
   ```

2. **Redis Memory** (`test_followup_questions_api.py`):
   ```python
   # ❌ Wrong:
   patch("src.api.v1.chat.get_redis_memory")

   # ✅ Correct:
   patch("src.components.memory.get_redis_memory")
   ```

3. **Answer Generator** (`test_graph.py`):
   ```python
   # ❌ Wrong:
   patch("src.agents.graph.get_answer_generator")

   # ✅ Correct:
   patch("src.agents.answer_generator.get_answer_generator")
   ```

**How to Identify Lazy Imports:**

1. Check if function is imported at module level:
   ```python
   # Module-level import (normal)
   from src.components.memory import get_redis_memory

   # Can be patched at caller module
   ```

2. Look for imports inside functions:
   ```python
   # Lazy import (inside function)
   async def save_conversation_turn(session_id: str):
       from src.components.memory import get_redis_memory  # ← Lazy!
       redis_memory = get_redis_memory()

   # MUST be patched at source: "src.components.memory.get_redis_memory"
   ```

**Detection Strategy:**
- If you get `AttributeError: <module 'X'> does not have attribute 'Y'`
- Check if Y is lazy-imported in X
- Patch Y at its **original definition location**

**Related Issues:**
- Sprint 27 Feature 27.10 (Citation tests)
- Commit 5ddfcb1 (Lazy import fixes)

---

## Monitoring & Observability

### Metrics to Track
```yaml
Retrieval Metrics:
  - query_latency_ms (p50, p95, p99)
  - retrieval_precision_at_k
  - context_relevance_score
  - document_coverage

Agent Metrics:
  - agent_execution_time_ms
  - tool_call_count
  - tool_call_success_rate
  - routing_accuracy

Memory Metrics:
  - memory_hit_rate (per layer)
  - memory_eviction_rate
  - memory_consolidation_latency

System Metrics:
  - requests_per_second
  - error_rate (4xx, 5xx)
  - active_connections
  - database_connection_pool_usage
```

### Alerting Rules
- **Critical:** p95 latency >1000ms for 5min
- **Warning:** Error rate >5% for 3min
- **Info:** Memory hit rate <60%

---

## Common Issues & Solutions

### Issue: Qdrant Connection Timeout
**Solution:** Increase connection pool size in `config.py`, check network latency

### Issue: Neo4j Out of Memory during Indexing
**Solution:** Batch processing, reduce concurrent writes, increase `dbms.memory.heap.max_size`

### Issue: LangGraph State Not Persisting
**Solution:** Verify Redis connection, check state serialization (Pydantic compatibility)

### Issue: MCP OAuth Flow Fails
**Solution:** Check redirect URI configuration, verify Auth0/Clerk credentials

---

## Security Considerations

### Input Validation
- Sanitize all user inputs (query, parameters)
- Validate file uploads (type, size, malware scan)
- Rate limiting per user/IP

### Secrets Management
- Never commit secrets to Git
- Use environment variables or secret managers (Vault, AWS Secrets Manager)
- Rotate API keys regularly

### Data Access
- Implement RBAC for multi-tenancy
- Audit logs for sensitive operations
- Encrypt data at rest (Neo4j, Redis)

### API Security
- HTTPS only in production
- JWT authentication with short expiry
- CORS configuration for allowed origins

---

## Deployment

### Local Development
```bash
# Start all services
docker compose up -d

# Run migrations
python scripts/migrate.py

# Start API server
uvicorn src.api.main:app --reload --port 8000
```

### Production (Kubernetes)
```bash
# Deploy with Helm
helm install aegis-rag ./k8s/helm-chart \
  --namespace production \
  --values k8s/values-prod.yaml

# Check deployment
kubectl get pods -n production
kubectl logs -f deployment/aegis-rag-api -n production
```

---

## Troubleshooting Commands

```bash
# Check service health
curl http://localhost:8000/health

# View logs
docker compose logs -f api
docker compose logs -f qdrant
docker compose logs -f neo4j

# Database access
# Qdrant UI: http://localhost:6333/dashboard
# Neo4j Browser: http://localhost:7474
# Redis CLI: redis-cli -h localhost -p 6379

# Run specific test suite
pytest tests/integration/test_agents.py -v

# Performance profiling
python -m cProfile -o profile.stats scripts/benchmark.py
```

---

## Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LlamaIndex Docs](https://docs.llamaindex.ai/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [RAGAS Evaluation](https://docs.ragas.io/)

---

## Contact & Support

- **Project Lead:** [Your Name]
- **Repository:** github.com/your-org/aegis-rag
- **Documentation:** docs.aegis-rag.com
- **Issue Tracker:** GitHub Issues
- **Community:** Discord/Slack Channel
