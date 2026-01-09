# AEGIS RAG Architecture

**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Last Updated:** 2026-01-09 (Sprint 81: C-LARA SetFit 95% Accuracy)

---

## Executive Summary

**AEGIS RAG** = Enterprise-grade Hybrid RAG System

**Core Capabilities:**
- **Local-First:** Ollama-based, zero cloud dependencies for development
- **4-Way Hybrid Retrieval:** Vector + BM25 + Graph Local + Graph Global with Intent-Weighted RRF
- **3-Layer Memory:** Redis → Qdrant → Graphiti
- **Multi-Agent:** LangGraph with 5+ specialized agents
- **Bi-Temporal:** Entity versioning with time travel queries
- **Agentic Tools:** Bash/Python execution with sandboxing (Sprint 59)

---

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AEGIS RAG System                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────┐          │
│  │   React Frontend (Port 5179)                        │          │
│  │   - SearchResultsPage (SSE streaming)               │          │
│  │   - StreamingAnswer (ReactMarkdown)                 │          │
│  │   - Citation (inline [1][2][3])                     │          │
│  │   - FollowUpQuestions                               │          │
│  │   - Settings (localStorage)                         │          │
│  └──────────────┬───────────────────────────────────────┘          │
│                 │ HTTP POST /api/v1/chat (SSE)                     │
│                 ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend (Port 8000)                      │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌──────────────┐         │  │
│  │  │ Health API │  │ Retrieval API│  │ Graph Viz API│         │  │
│  │  │ (Sprint 2) │  │  (Sprint 2)  │  │ (Sprint 12)  │         │  │
│  │  └────────────┘  └──────┬───────┘  └──────────────┘         │  │
│  └─────────────────────────┼──────────────────────────────────────┘  │
│                            │                                         │
│                            ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │          LangGraph Multi-Agent Orchestration                  │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │  │
│  │  │ Router  │→ │ Vector  │  │  Graph  │  │ Memory  │         │  │
│  │  │  Agent  │  │  Agent  │  │  Agent  │  │  Agent  │         │  │
│  │  └─────────┘  └────┬────┘  └────┬────┘  └────┬────┘         │  │
│  │                    │            │            │               │  │
│  │               ┌────┴────────────┴────────────┴────┐          │  │
│  │               │     Aggregator Node              │          │  │
│  │               └──────────────┬───────────────────┘          │  │
│  └──────────────────────────────┼──────────────────────────────┘  │
│                                 │                                  │
│                                 ▼                                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Storage Layer                               │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐     │  │
│  │  │  Redis  │  │ Qdrant  │  │ Neo4j   │  │AegisLLMProxy│     │  │
│  │  │(Memory) │  │(Vector) │  │ (Graph) │  │ Multi-Cloud │     │  │
│  │  │Port 6379│  │Port 6333│  │Port 7687│  │ LLM Routing │     │  │
│  │  │         │  │ BGE-M3  │  │         │  │ (ADR-033)   │     │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────┘     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Domain Structure (Sprint 56 Refactoring)

Post-refactoring (Sprint 53-59), the codebase follows **Domain-Driven Design (DDD)** principles:

```
src/
├── agents/                     # LangGraph Multi-Agent System
│   ├── coordinator.py          # Main orchestrator
│   ├── vector_search.py        # Qdrant hybrid search
│   ├── graph_query.py          # Neo4j + LightRAG
│   ├── memory.py               # Graphiti memory
│   ├── action.py               # MCP tool execution
│   └── research/               # Agentic research agent (Sprint 59)
│
├── domains/                    # Domain-Driven Design Structure
│   ├── document_processing/    # Ingestion domain
│   │   ├── chunking/           # Section-aware chunking
│   │   ├── embedding/          # BGE-M3 embeddings
│   │   └── storage/            # Qdrant/Neo4j storage
│   │
│   ├── knowledge_graph/        # Graph domain
│   │   ├── entities/           # Entity management
│   │   ├── relationships/      # Relationship extraction
│   │   └── community/          # Community detection
│   │
│   ├── vector_search/          # Vector search domain
│   │   ├── hybrid/             # Hybrid search (Vector + BM25)
│   │   └── reranking/          # Result reranking
│   │
│   ├── memory/                 # Memory domain
│   │   ├── redis/              # Short-term memory
│   │   ├── qdrant/             # Semantic memory
│   │   └── graphiti/           # Episodic memory
│   │
│   └── llm_integration/        # LLM domain
│       ├── proxy/              # AegisLLMProxy
│       ├── tools/              # Tool framework (Sprint 59)
│       │   ├── registry.py     # Tool registration
│       │   ├── executor.py     # Tool execution
│       │   └── builtin/        # Bash/Python tools
│       └── sandbox/            # Docker sandboxing (Sprint 59)
│
├── api/                        # FastAPI endpoints
│   └── v1/                     # API v1
│       ├── chat.py             # Chat/Query endpoint
│       ├── admin.py            # Admin endpoints
│       └── memory.py           # Memory access
│
└── core/                       # Core infrastructure
    ├── config/                 # Configuration
    ├── logging/                # Structured logging
    └── exceptions/             # Custom exceptions
```

**Key Changes (Sprint 53-59):**
- ✅ **components/** → **domains/** (DDD structure)
- ✅ Protocol-based interfaces for domain boundaries
- ✅ Dependency injection container
- ✅ 80%+ test coverage maintained
- ✅ Tool framework added (Sprint 59)
- ✅ Research agent added (Sprint 59)

---

## Component Interactions

### Request Flow: User Query → Answer

```
1. User Query (Frontend)
   ↓
2. POST /api/v1/chat (FastAPI)
   ↓
3. LangGraph Router Agent
   ├→ Determines query type (vector/graph/hybrid/memory)
   └→ Routes to specialized agents
   ↓
4. Parallel Agent Execution (LangGraph Send API)
   ├→ Vector Agent: Qdrant + BM25 → RRF Fusion
   ├→ Graph Agent: Neo4j (local + global queries)
   └→ Memory Agent: Redis → Qdrant → Graphiti
   ↓
5. Aggregator Node
   ├→ Combines results from all agents
   ├→ Re-ranks with intent weights
   └→ Generates citations
   ↓
6. Answer Generation (AegisLLMProxy)
   ├→ Primary: Ollama (local, DGX Spark)
   ├→ Fallback: Alibaba Cloud DashScope
   └→ Optional: OpenAI
   ↓
7. SSE Stream → Frontend
   └→ Token-by-token rendering
```

### Ingestion Flow: Document → Knowledge Graph

```
1. Document Upload (Frontend)
   ↓
2. POST /api/v1/admin/ingest (FastAPI)
   ↓
3. LangGraph Ingestion Pipeline (6 Nodes)
   ├→ Node 1: Format Detection
   ├→ Node 2: Docling CUDA (OCR, layout)
   ├→ Node 3: Section-Aware Chunking (800-1800 tokens)
   ├→ Node 4: BGE-M3 Embeddings (1024-dim)
   ├→ Node 5: Entity Extraction (LLM-based)
   └→ Node 6: Graph Storage (Neo4j + Qdrant)
   ↓
4. Storage Layer
   ├→ Qdrant: Vector storage + metadata
   ├→ Neo4j: Entity/Relation graph
   └→ Redis: Session state
   ↓
5. Post-Processing
   ├→ Community Detection (Leiden/Louvain)
   ├→ Entity Deduplication (embedding-based)
   └→ Relation Normalization
```

---

## Evolution History

### Major Milestones

| Sprint | Theme | Key Changes |
|--------|-------|-------------|
| **1-4** | Foundation | Docker stack, LangGraph orchestration, 4 agents |
| **5-6** | Hybrid Retrieval | LightRAG integration, RRF fusion, parallel execution |
| **7** | 3-Layer Memory | Redis + Qdrant + Graphiti integration |
| **13-20** | Extraction Evolution | SpaCy → Pure LLM pipeline |
| **21** | Container Ingestion | Docling CUDA (95% accuracy, 3-5x speedup) |
| **25** | LLM Routing | AegisLLMProxy multi-cloud routing |
| **32-34** | Chunking & Relations | Section-aware chunking, RELATES_TO relationships |
| **39-40** | Bi-Temporal | Entity versioning, time travel, Graphiti memory |
| **41-44** | Deduplication | Parallel extraction, entity dedup (10.1% reduction) |
| **45-48** | LangGraph State | Unified AgentState, cancellation, phase events |
| **51** | Maximum Hybrid | 4-signal fusion, community detection fixes |
| **53-59** | Refactoring | DDD structure, protocols, 80% coverage, tool framework |
| **76-77** | RAGAS & Bug Fixes | .txt support (15 HotpotQA), RAGAS baseline (80% faithfulness), BM25 namespace fix, community summarization (92/92) |
| **78** | Graph Search Enhancement | Entity→Chunk expansion (100-char→447-char), 3-stage semantic search (LLM→Graph→Synonym→BGE-M3), 4 UI settings |
| **79** | RAGAS 0.4.2 Migration | RAGAS 0.4.2 upgrade, Graph Expansion UI (56 tests), Admin Graph Ops UI (74 tests), BGE-M3 Embeddings (99s/sample) |
| **81** | C-LARA Intent Classification | Multi-Teacher SetFit (4 LLMs + 42 edge cases), 5-class C-LARA intents, 95.22% accuracy, ~40ms inference |

### Sprint 53-59: Major Refactoring

**Sprint 53-57: Refactoring Foundation**
- Protocol-based interfaces
- Domain boundaries (components → domains)
- Dependency injection
- Test coverage >80%

**Sprint 58: Bug Fixes**
- 10 test failures fixed
- Integration tests stabilized

**Sprint 59: Agentic Features**
- Tool Use Framework (decorator-based)
- Bash Tool (blacklist validation, timeout enforcement)
- Python Tool (AST validation, restricted globals)
- Docker Sandbox (resource limits, network isolation)
- Research Agent (LangGraph multi-step reasoning)

---

## Architecture Patterns

### 1. Multi-Agent Orchestration (LangGraph)

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("router", router_agent)
workflow.add_node("vector", vector_agent)
workflow.add_node("graph", graph_agent)
workflow.add_node("memory", memory_agent)
workflow.add_node("aggregator", aggregator)

# Conditional routing
workflow.add_conditional_edges(
    "router",
    determine_agents,
    {
        "vector_only": "vector",
        "graph_only": "graph",
        "hybrid": "vector",  # Then Send() to graph
    }
)

# Parallel execution via Send()
workflow.add_edge("vector", "aggregator")
workflow.add_edge("graph", "aggregator")
workflow.add_edge("aggregator", END)
```

### 2. Hybrid Search (RRF Fusion)

```
Results_hybrid = RRF(
    α × Results_vector +
    β × Results_BM25 +
    γ × Results_graph_local +
    δ × Results_graph_global
)

Where: α + β + γ + δ = 1.0
```

### 3. 3-Layer Memory

```
Layer 1: Redis (Short-term)
- TTL: 3600s
- Latency: <10ms
- Use: Session state, recent context

Layer 2: Qdrant (Semantic)
- Retention: Permanent
- Latency: <50ms
- Use: Long-term facts, embeddings

Layer 3: Graphiti (Episodic)
- Retention: Temporal
- Latency: <200ms
- Use: Temporal relationships, entity history
```

### 4. Tool Framework (Sprint 59)

```python
@ToolRegistry.register(
    name="bash",
    description="Execute bash command",
    parameters=BASH_TOOL_SCHEMA,
    requires_sandbox=True
)
async def bash_execute(command: str, timeout: int = 30):
    # Security validation
    check = is_command_safe(command)

    # Sandboxed execution
    sandbox = await get_sandbox()
    return await sandbox.run_bash(command, timeout)
```

---

## Key Design Decisions

### ADRs Implemented

- **ADR-001:** LangGraph for orchestration (vs CrewAI/AutoGen)
- **ADR-024:** BGE-M3 embeddings (1024-dim, multilingual)
- **ADR-026:** Pure LLM extraction pipeline
- **ADR-027:** Docling CUDA for ingestion
- **ADR-033:** AegisLLMProxy multi-cloud routing
- **ADR-039:** Section-aware adaptive chunking
- **ADR-040:** RELATES_TO semantic relationships
- **ADR-046:** Comprehensive refactoring strategy (Sprint 53-59)

### Technology Choices

| Component | Technology | Alternative Rejected | Reason |
|-----------|------------|---------------------|--------|
| Orchestration | LangGraph | CrewAI, AutoGen | Explicit control, production features |
| Vector DB | Qdrant | Weaviate, Pinecone | Performance, local-first |
| Graph DB | Neo4j | GraphDB, Neptune | Ecosystem, GDS library |
| LLM | Ollama (local) | OpenAI, Anthropic | Cost ($0 vs $24K/year), privacy |
| Frontend | React 19 | Vue, Svelte | Ecosystem, TypeScript support |

---

## Performance Characteristics

| Operation | Target Latency (p95) | Achieved |
|-----------|---------------------|----------|
| Simple Query (Vector) | <200ms | ✅ 180ms |
| Hybrid Query (Vector+Graph) | <500ms | ✅ 450ms |
| Complex Multi-Hop | <1000ms | ✅ 980ms |
| Ingestion (per page) | <2s | ✅ 1.8s (GPU) |
| Embedding (batch 32) | <500ms | ✅ 420ms |

---

## Security Architecture

### Defense in Depth (5 Layers) - Sprint 59

1. **Input Validation**
   - Bash: Blacklist + pattern matching
   - Python: AST analysis

2. **Restricted Environment**
   - Bash: Sanitized env vars
   - Python: Restricted globals, blocked modules

3. **Docker Sandbox**
   - Network isolation
   - Read-only filesystem
   - Resource limits (memory, CPU)

4. **Timeout Enforcement**
   - Max 300s per execution
   - Process/container killing

5. **Result Truncation**
   - Prevent memory exhaustion

---

## Future Directions

### Short-term (Sprint 61-65)
- [ ] LLM integration for research agent
- [ ] Process-level sandboxing (alternative to Docker)
- [ ] Additional built-in tools (file operations, network)
- [ ] Tool usage analytics

### Medium-term (Sprint 66-75)
- [x] Temporal queries (GRAPHITI analysis - Sprint 60)
- [ ] Advanced community detection **← IN PROGRESS (Sprint 68)**
- [ ] Multi-modal document understanding
- [ ] Enhanced caching strategies

### Long-term (Sprint 76+)
- [ ] Distributed deployment (K8s)
- [ ] Multi-tenant support
- [ ] Real-time graph updates
- [ ] Advanced anomaly detection

---

## Sprint 67-68 Architecture Enhancements

### Secure Shell Sandbox Architecture (Sprint 67)

```python
┌───────────────────────────────────────────────────────────┐
│             Action Agent (LangGraph)                      │
├───────────────────────────────────────────────────────────┤
│                                                           │
│   ┌─────────────────────────────────────────┐            │
│   │   deepagents Framework                  │            │
│   │   ┌──────────────────────────────┐     │            │
│   │   │ SandboxBackendProtocol       │     │            │
│   │   │ - execute(command)           │     │            │
│   │   │ - write_file(path, content)  │     │            │
│   │   │ - read_file(path)            │     │            │
│   │   └──────────┬───────────────────┘     │            │
│   └──────────────┼──────────────────────────┘            │
│                  ▼                                         │
│   ┌──────────────────────────────────────────┐           │
│   │  BubblewrapSandboxBackend                │           │
│   │  - Syscall filtering (seccomp)           │           │
│   │  - Filesystem isolation (/tmp only)      │           │
│   │  - Network restrictions                  │           │
│   │  - Multi-language (Bash + Python)        │           │
│   └──────────────────────────────────────────┘           │
└───────────────────────────────────────────────────────────┘
```

### Tool-Level Adaptation Framework (Sprint 67)

```
┌──────────────────────────────────────────────────────────┐
│         Adaptation Framework (Paper 2512.16301)          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────┐         │
│  │  Unified Trace & Telemetry                │         │
│  │  - Pipeline event logging                  │         │
│  │  - Performance metrics collection          │         │
│  │  - Quality signal tracking                 │         │
│  └────────────┬───────────────────────────────┘         │
│               │                                          │
│               ▼                                          │
│  ┌────────────────────────────────────────────┐         │
│  │  Eval Harness                              │         │
│  │  - Grounding validation                    │         │
│  │  - Citation coverage check                 │         │
│  │  - Format compliance                       │         │
│  └────────────┬───────────────────────────────┘         │
│               │                                          │
│               ▼                                          │
│  ┌────────────────────────────────────────────┐         │
│  │  Tool-Level Adaptation (T1/T2)             │         │
│  │  ┌───────────────┐  ┌───────────────┐     │         │
│  │  │ Adaptive      │  │ Query         │     │         │
│  │  │ Reranker v1   │  │ Rewriter v1   │     │         │
│  │  │ (Intent-aware)│  │ (Expansion)   │     │         │
│  │  └───────────────┘  └───────────────┘     │         │
│  └────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────┘
```

### Performance Enhancements (Sprint 68)

**Section Extraction Optimization:**
- **Phase 1 (Sprint 67):** Batch tokenization, regex compilation → 2-3x speedup
- **Phase 2 (Sprint 68):** ThreadPoolExecutor parallelization → 5-10x total speedup
- **Target:** 15min → 2min for large PDFs

**BM25 Cache Consistency:**
- Auto-refresh on startup if discrepancy >10%
- Namespace-aware caching
- Cache validation logging

**Section Community Detection:**
- Louvain/Leiden algorithms for section-based communities
- 15 production Cypher queries
- Integration with Maximum Hybrid Search

---

## Sprint 72 Admin Features (UI-Frontend Gap Closure)

### MCP Tool Management UI (Feature 72.1)

**Purpose:** Unified interface for managing Model Context Protocol (MCP) servers and executing tools without SSH/CLI

**Architecture:**

```
┌────────────────────────────────────────────────────────┐
│   React Frontend (MCPToolsPage + Components)           │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ MCPServerList    │  │ MCPToolExecutionPanel    │  │
│  │ - Connect/Disco  │  │ - Parameter Input        │  │
│  │ - Status Badge   │  │ - Tool Execution        │  │
│  │ - Health Metrics │  │ - Result Display        │  │
│  └─────────┬────────┘  └─────────┬────────────────┘  │
│            │                     │                   │
│            └─────────┬───────────┘                   │
│                      │                               │
│           [MCPHealthMonitor]                         │
│           - Real-time metrics (CPU, Mem, Latency)    │
│           - Auto-refresh every 30s                   │
│                                                      │
└────────────────────────────────┬──────────────────────┘
                                 │ HTTP REST API
                    ┌────────────▼──────────────┐
                    │  FastAPI Backend          │
                    │  /api/v1/mcp/*            │
                    │  - servers (list)         │
                    │  - connect/disconnect     │
                    │  - health checks          │
                    │  - tools (execute)        │
                    └───────────────────────────┘
```

**Components:**

| Component | Lines | Purpose |
|-----------|-------|---------|
| `MCPToolsPage` | 200+ | Main page, tab switching |
| `MCPServerList` | 250+ | Server list, connect/disconnect |
| `MCPToolExecutionPanel` | 300+ | Parameter input, execution |
| `MCPServerCard` | 150+ | Individual server status |
| `MCPHealthMonitor` | 180+ | Real-time health metrics |

**Features:**

- **Server Management:** Connect/disconnect MCP servers in real-time
- **Health Monitoring:** CPU, memory, response latency tracking
- **Tool Execution:** Type-safe parameter input with validation
- **Result Display:** Pretty-printed JSON with copy-to-clipboard
- **Error Handling:** User-friendly error messages with retry logic
- **Responsive Design:** Desktop two-column, mobile tab-based

**User Guide:** [docs/guides/MCP_TOOLS_ADMIN_GUIDE.md](guides/MCP_TOOLS_ADMIN_GUIDE.md)

### Domain Training UI Completion (Feature 72.2)

**Purpose:** Complete wiring of Features 71.13-71.15 with backend APIs

**Features Connected:**

1. **Data Augmentation Dialog** (71.13)
   - Generate synthetic training examples
   - Configure augmentation parameters
   - Preview augmented data

2. **Batch Document Upload** (71.14)
   - Upload multiple documents in bulk
   - Progress tracking
   - Error handling per document

3. **Domain Details Dialog** (71.15)
   - View domain configuration
   - Edit domain metadata
   - Trigger domain training pipeline

**Backend Integration:**

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/admin/domains/{id}/augment` | Generate synthetic data |
| `POST /api/v1/admin/domains/{id}/documents/batch` | Bulk upload |
| `GET /api/v1/admin/domains/{id}` | Get domain details |
| `PUT /api/v1/admin/domains/{id}` | Update domain config |

**Success Criteria:**
- All 18 skipped E2E tests now passing
- Domain training fully functional from UI
- No API endpoints needed (all exist from Sprint 71)

### Memory Management UI (Feature 72.3)

**Purpose:** Comprehensive debugging interface for 3-layer memory system

**Architecture:**

```
┌────────────────────────────────────────────────┐
│  MemoryManagementPage (Tabs: Stats | Search)   │
├────────────────────────────────────────────────┤
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │Statistics│  │ Search   │  │Consolidate │  │
│  │- Redis   │  │- By user │  │- Trigger   │  │
│  │- Qdrant  │  │- By date │  │- History   │  │
│  │- Graphiti│  │- Keywords│  │- Settings  │  │
│  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │               │        │
│  ┌────▼──────────────▼───────────────▼──────┐ │
│  │  MemoryStatsCard (each layer)            │ │
│  │  MemorySearchPanel (global search)       │ │
│  │  ConsolidationControl (manual trigger)   │ │
│  └────────────────────────────────────────┘  │
│                                                │
└───────────────┬────────────────────────────────┘
                │ REST API
    ┌───────────▼──────────────┐
    │  FastAPI Backend         │
    │  /api/v1/memory/*        │
    │  - stats (all layers)    │
    │  - search (cross-layer)  │
    │  - consolidate (trigger) │
    │  - export (backup)       │
    └──────────────────────────┘
```

**Components:**

| Component | Purpose |
|-----------|---------|
| `MemoryStatsCard` | Display layer statistics (Redis, Qdrant, Graphiti) |
| `MemorySearchPanel` | Cross-layer search by user, session, keywords |
| `ConsolidationControl` | Manual consolidation trigger & history |

**Statistics Display:**

- **Redis (Layer 1):** Keys, memory, hit rate, latency, TTL
- **Qdrant (Layer 2):** Collections, vectors, search latency
- **Graphiti (Layer 3):** Nodes, relationships, temporal scope

**Search Capabilities:**

- By user ID (across all layers)
- By session ID
- By keywords (semantic search in Qdrant)
- By date range
- Export results as JSON

**Consolidation Control:**

- Manual trigger with progress monitoring
- Consolidation history (last 30 consolidations)
- Auto-consolidation settings (interval, threshold)
- Retry failed items

**User Guide:** [docs/guides/MEMORY_MANAGEMENT_GUIDE.md](guides/MEMORY_MANAGEMENT_GUIDE.md)

---

## Sprint 76-79: Graph Search Enhancement & RAGAS Evaluation

### Sprint 76-77: RAGAS Foundation & Critical Bug Fixes

**Sprint 76 Achievements:**
- **.txt File Support:** Added 15 HotpotQA files for evaluation dataset
- **RAGAS Baseline:** Faithfulness 80%, Answer Relevancy 93% (using GPT-OSS:20b)
- **Entity Extraction:** 146 entities extracted from HotpotQA dataset

**Sprint 77 Critical Fixes:**
- **BM25 Namespace Fix:** Corrected namespace filtering in keyword search
- **Chunk Mismatch Resolution:** Fixed chunk ID alignment between Qdrant and Neo4j
- **Community Summarization:** Generated summaries for 92/92 communities
- **Entity Connectivity Benchmarks:** Evaluated connectivity metrics across 4 domain types (Factual, Narrative, Technical, Academic)

### Sprint 78: Entity→Chunk Expansion & 3-Stage Semantic Search (ADR-041)

**Problem Statement:**
Graph search was returning only 100-character entity descriptions instead of full document chunks, providing insufficient context for LLM answer generation.

**Solution Architecture:**

```python
# BEFORE (Sprint 77) - Entity descriptions only
MATCH (e:base)
WHERE e.entity_name IN $entities
RETURN e.entity_id, e.entity_name, e.description  -- Only 100 chars!

# AFTER (Sprint 78) - Full document chunks via MENTIONED_IN traversal
MATCH (e:base)-[:MENTIONED_IN]->(c:chunk)
WHERE e.entity_name IN $expanded_entities
  AND c.namespace_id IN $namespaces
WITH c, collect(DISTINCT e.entity_name) AS matched_entities,
     count(DISTINCT e) AS entity_count
RETURN c.chunk_id, c.text, c.document_id, c.chunk_index,
       matched_entities, entity_count
ORDER BY entity_count DESC
LIMIT $top_k
```

**3-Stage Semantic Entity Expansion Pipeline:**

```
┌─────────────────────────────────────────────────────────────┐
│          SmartEntityExpander (3-Stage Pipeline)             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Stage 1: LLM Entity Extraction                            │
│  ┌────────────────────────────────────────┐                │
│  │ Input: "Who developed Ollama?"         │                │
│  │ LLM: Extract entities from query       │                │
│  │ Output: ["Ollama", "developer"]        │                │
│  │ Features: Context-aware, auto-filters  │                │
│  └────────────────┬───────────────────────┘                │
│                   │                                         │
│  Stage 2: Graph N-Hop Expansion                            │
│  ┌────────────────▼───────────────────────┐                │
│  │ Input: ["Ollama", "developer"]         │                │
│  │ Neo4j: Traverse N-hops (configurable)  │                │
│  │ Cypher: MATCH (e)-[*1..N]-(related)    │                │
│  │ Output: ["Ollama", "Meta", "LLaMA",    │                │
│  │          "vLLM", "inference"]          │                │
│  │ Config: graph_expansion_hops (1-3)     │                │
│  └────────────────┬───────────────────────┘                │
│                   │                                         │
│  Stage 3: LLM Synonym Fallback (if < threshold)            │
│  ┌────────────────▼───────────────────────┐                │
│  │ Condition: len(entities) < threshold   │                │
│  │ LLM: Generate synonyms for top 2       │                │
│  │ Input: ["Ollama", "developer"]         │                │
│  │ Output: ["LLM runtime", "creator",     │                │
│  │          "maintainer"]                 │                │
│  │ Config: graph_max_synonyms_per_entity  │                │
│  └────────────────┬───────────────────────┘                │
│                   │                                         │
│  Stage 4: BGE-M3 Semantic Reranking (optional)             │
│  ┌────────────────▼───────────────────────┐                │
│  │ Input: All expanded entities           │                │
│  │ BGE-M3: Rank by semantic similarity    │                │
│  │ Output: Top-K most relevant entities   │                │
│  │ Config: graph_semantic_reranking_enabled│               │
│  └────────────────────────────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Configuration Settings (UI-Exposed, Sprint 78):**

| Setting | Type | Range | Default | Purpose |
|---------|------|-------|---------|---------|
| `graph_expansion_hops` | int | 1-3 | 1 | Graph traversal depth |
| `graph_min_entities_threshold` | int | 5-20 | 10 | Synonym fallback trigger |
| `graph_max_synonyms_per_entity` | int | 1-5 | 3 | LLM synonym generation limit |
| `graph_semantic_reranking_enabled` | bool | - | true | Enable BGE-M3 reranking |

**Impact:**
- **Context Quality:** 4.5x more context (100 chars → 447 chars avg chunk size)
- **Graph Query Latency:** +70ms (0.05s → 0.12s) for 4.5x more context
- **Entity Expansion:** 0.4-0.9s (depending on synonym fallback)
- **End-to-End Query:** ~500ms (within target <500ms for hybrid queries)

**Test Coverage:** 20 comprehensive unit tests (100% pass rate)
- 14 tests for SmartEntityExpander (all 4 stages + edge cases)
- 6 tests for dual_level_search (Entity→Chunk traversal, namespace filtering, ranking)

### Sprint 79: DSPy RAGAS Prompt Optimization (Planned)

**Problem Statement:**
RAGAS Few-Shot prompts (2903 chars) too complex for local LLMs:
- GPT-OSS:20b: 85.76s per evaluation (timeout at 300s for 15 contexts)
- Nemotron3 Nano: >600s per simple query

**Solution Approach: DSPy Framework v2.5+**

**DSPy BootstrapFewShot (for GPT-OSS:20b, Nemotron3 Nano):**
```python
# Define RAGAS Context Precision as DSPy Signature
class ContextPrecisionSignature(dspy.Signature):
    """Verify if context was useful in arriving at the answer."""
    question: str = dspy.InputField()
    answer: str = dspy.InputField()
    context: str = dspy.InputField()
    verdict: int = dspy.OutputField(desc="1 if useful, 0 if not")

# Optimize with BootstrapFewShot (for small models)
optimizer = dspy.BootstrapFewShot(
    max_bootstrapped_demos=2,  # Generate 2 few-shot examples
    max_labeled_demos=1,       # Use 1 labeled example
)
compiled_program = optimizer.compile(
    student=ContextPrecisionModule(),
    trainset=training_examples  # 20 examples per metric
)
```

**DSPy MIPROv2 (for Qwen2.5:7b - if available):**
```python
# Multi-Prompt Instruction Proposal Optimizer v2
optimizer = dspy.MIPROv2(
    prompt_model=qwen25_7b,  # Use Qwen2.5:7b for prompt generation
    task_model=gpt_oss_20b,  # Use GPT-OSS:20b for evaluation
    metric=ragas_f1_score,   # Composite RAGAS metric
    num_candidates=10,       # Generate 10 prompt candidates
    init_temperature=1.4,    # High temp for diversity
)
```

**Performance Targets (Sprint 79):**
- GPT-OSS:20b: 85.76s → <20s (4x speedup)
- Nemotron3 Nano: >600s → <60s (10x speedup)
- Accuracy: ≥90% (vs 100% baseline)

**Training Data Requirements:**
- 20 labeled examples per metric (4 metrics × 20 = 80 examples total)
- Amnesty QA dataset (10 questions) + HotpotQA (15 questions)
- Human validation for ground truth

---

**Document Consolidated:** Sprint 60 Feature 60.1
**Sprint 67-68 Updates:** 2025-12-31
**Sprint 72 Updates:** 2026-01-03 (Admin Features)
**Sprint 76-79 Updates:** 2026-01-08 (Graph Search Enhancement, RAGAS Optimization)
**Sprint 81 Updates:** 2026-01-09 (C-LARA SetFit Multi-Teacher Intent Classification 95.22%)
**Sources:** ARCHITECTURE_EVOLUTION.md, COMPONENT_INTERACTION_MAP.md, STRUCTURE.md, SPRINT_67_PLAN.md, SPRINT_72_PLAN.md, SPRINT_78_PLAN.md, SPRINT_81_PLAN.md
**Maintainer:** Claude Code with Human Review
