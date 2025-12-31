# AEGIS RAG Architecture

**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Last Updated:** 2025-12-31 (Sprint 67-68 Planning)

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

**Document Consolidated:** Sprint 60 Feature 60.1
**Sprint 67-68 Updates:** 2025-12-31
**Sources:** ARCHITECTURE_EVOLUTION.md, COMPONENT_INTERACTION_MAP.md, STRUCTURE.md, SPRINT_67_PLAN.md, SPRINT_68_PLAN.md
**Maintainer:** Claude Code with Human Review
