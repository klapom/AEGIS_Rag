# AEGIS RAG Architecture

**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Last Updated:** 2026-02-06 (Sprint 125: vLLM Dual-Engine, Domain-Aware Extraction)

---

## Executive Summary

**AEGIS RAG** = Enterprise-grade Hybrid RAG System

**Core Capabilities:**
- **Local-First:** Ollama-based, zero cloud dependencies for development
- **4-Way Hybrid Retrieval:** Dense + Sparse (BGE-M3) + Graph Local + Graph Global with Intent-Weighted RRF
- **BGE-M3 Native Hybrid:** Single model generates Dense (1024D) + Sparse (lexical weights) vectors - replaces BM25
- **3-Layer Memory:** Redis → Qdrant → Graphiti
- **Multi-Agent:** LangGraph with 5+ specialized agents
- **Bi-Temporal:** Entity versioning with time travel queries
- **Agentic Tools:** Bash/Python execution with sandboxing (Sprint 59)

---

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AEGIS RAG System (Sprint 125+)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │   React Frontend (Port 80)                              │              │
│  │   - Domain Detection at Upload (BGE-M3)                 │              │
│  │   - Domain Filter + Deployment Profile Selection        │              │
│  │   - Sub-Type Display in Graph Visualization             │              │
│  └──────────────┬───────────────────────────────────────────┘              │
│                 │ HTTP POST /api/v1/chat + /api/v1/retrieval/upload       │
│                 ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend (Port 8000)                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │  │
│  │  │ Chat API     │  │ Retrieval API│  │ Domain-Aware Ingestion   │  │  │
│  │  │ (Ollama)     │  │ (Vector+Graph)  │ (vLLM Extraction)        │  │  │
│  │  └──────────┬───┘  └──────┬───────┘  └───────────┬──────────────┘  │  │
│  └─────────────┼─────────────┼──────────────────────┼─────────────────────┘  │
│                │             │                      │                       │
│                ▼             ▼                      ▼                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │          LangGraph Multi-Agent Orchestration (Sprint 125)             │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────────────┐   │  │
│  │  │ Router  │→ │ Vector  │  │  Graph  │  │ Domain Classifier    │   │  │
│  │  │  Agent  │  │  Agent  │  │  Agent  │  │ (Extraction Prompt)  │   │  │
│  │  └─────────┘  └────┬────┘  └────┬────┘  └──────────┬───────────┘   │  │
│  │                    │            │                   │               │  │
│  │               ┌────┴────────────┴───────────────────┘               │  │
│  │               │     Aggregator Node (Intent-Weighted RRF)          │  │
│  │               └──────────────┬──────────────────────────┘           │  │
│  └──────────────────────────────┼──────────────────────────────────────┘  │
│                                 │                                        │
│                                 ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                   Dual-Engine LLM Routing                             │  │
│  │                                                                      │  │
│  │  ┌─────────────────────┐           ┌──────────────────────────┐     │  │
│  │  │ Ollama (Chat)       │           │ vLLM (Extraction)        │     │  │
│  │  │ Port 11434          │           │ Port 8001                │     │  │
│  │  │ Nemotron-3-Nano:128k│           │ Nemotron NVFP4 30B-A3B  │     │  │
│  │  │ 4 concurrent max    │           │ 256+ concurrent          │     │  │
│  │  │ 74 tok/s            │           │ 60-80 tok/s (DGX Spark) │     │  │
│  │  │ User-facing queries │           │ S-P-O extraction jobs    │     │  │
│  │  └─────────────────────┘           └──────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                        │
│                                 ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                   Storage Layer (Sprint 125)                          │  │
│  │  ┌─────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────────────┐  │  │
│  │  │  Redis  │  │ Qdrant       │  │ Neo4j    │  │ Domain Taxonomy │  │  │
│  │  │(Memory) │  │ (Vector)     │  │ (Graph)  │  │ (35 DDC+FORD)   │  │  │
│  │  │Port 6379│  │Port 6333     │  │Port 7687 │  │ + Sub-Types     │  │  │
│  │  │         │  │ Dense 1024D  │  │          │  │ Entity Prompts  │  │  │
│  │  │         │  │ Sparse Lex.  │  │ with_id: │  │                 │  │  │
│  │  │         │  │ Server RRF   │  │ domain_id│  │ domain_id →     │  │  │
│  │  │         │  │              │  │          │  │ prompt selection│  │  │
│  │  └─────────┘  └──────────────┘  └──────────┘  └─────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
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
│       ├── tools/              # Tool framework
│       │   ├── registry.py     # Tool registration (Sprint 59)
│       │   ├── executor.py     # Tool execution (Sprint 59)
│       │   ├── mapping.py      # Skill→Tool mapping (Sprint 93)
│       │   ├── composition.py  # Tool composition (Sprint 93)
│       │   ├── policy.py       # PolicyEngine (Sprint 93)
│       │   ├── browser.py      # Browser tool (Sprint 93)
│       │   └── builtin/        # Bash/Python/Web tools
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
   ├→ Vector Agent: Qdrant Dense + Sparse (BGE-M3) → Server-Side RRF
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

**Two-Phase Upload Strategy (Sprint 83.4):**

```
Phase 1: Fast Upload (2-5s response)
1. Document Upload (Frontend)
   ↓
2. POST /api/v1/admin/upload-fast (FastAPI)
   ↓
3. Fast Pipeline (SpaCy NER + Basic Chunking)
   ├→ Node 1: Docling CUDA (OCR, layout)
   ├→ Node 2: Section-Aware Chunking (800-1800 tokens)
   ├→ Node 3: BGE-M3 Embeddings (1024-dim)
   ├→ Node 4: Qdrant Upload (vector only)
   └→ Node 5: SpaCy NER (entities only, multi-language: DE/EN/FR/ES)
   ↓
4. Immediate Response to User
   └→ Status: "processing_background" + document_id

Phase 2: Background Refinement (30-60s async)
5. Background Job Queue (Redis-tracked)
   ↓
6. Full LLM Extraction Pipeline
   ├→ 3-Rank Cascade Fallback (Sprint 83.2):
   │  ├→ Rank 1: Nemotron3 (300s timeout)
   │  ├→ Rank 2: GPT-OSS:20b (300s timeout)
   │  └→ Rank 3: Hybrid SpaCy NER + LLM (600s relations)
   │
   ├→ Gleaning Multi-Pass (Sprint 83.3):
   │  ├→ Round 1: Initial extraction
   │  ├→ Completeness Check (logit bias YES/NO)
   │  ├→ Round 2-N: Extract missing entities (continuation prompt)
   │  └→ Deduplication (semantic + substring)
   │
   └→ Retry Logic (exponential backoff: 1s → 2s → 4s → 8s)
   ↓
7. Storage Layer
   ├→ Qdrant: Vector storage + metadata update (LLM entities replace SpaCy)
   ├→ Neo4j: Entity/Relation graph (LLM quality)
   └→ Redis: Job status ("ready" when complete)
   ↓
8. Post-Processing
   ├→ Community Detection (Leiden/Louvain)
   ├→ Entity Deduplication (embedding-based)
   └→ Relation Normalization
   ↓
9. Status Update
   └→ GET /api/v1/admin/upload-status/{document_id} → "ready"
```

**Key Improvements (Sprint 83):**
- **10-15x faster user upload** (2-5s vs 30-60s perceived time)
- **3-rank fallback cascade** (99.9% extraction success rate)
- **Gleaning +20-40%** entity recall (Microsoft GraphRAG approach)
- **Multi-language NER** (DE/EN/FR/ES SpaCy support)
- **Comprehensive logging** (P50/P95/P99 metrics, LLM cost tracking, GPU VRAM monitoring)
- **Ollama health monitoring** (periodic checks + auto-restart capability)

### Domain-Aware Ingestion Pipeline (Sprint 125 / ADR-060, ADR-061)

**Architecture:** Three-stage domain classification → prompts → S-P-O extraction

```
Phase 1: Fast Upload (2-5s)
Document Upload (Frontend) →
├→ Step 1: Parse & OCR (Docling CUDA)
├→ Step 2: Section Chunking (800-1800 tokens)
├→ Step 3: BGE-M3 Embedding (Dense 1024D + Sparse lexical)
├→ Step 4: Domain Classification (BGE-M3 cosine sim ≥0.85)
│           └→ Match against 35 DDC+FORD domain embeddings
│           └→ Select domain_id (default: "generic")
├→ Step 5: Qdrant Upload (vector + domain_id metadata)
├→ Step 6: Fast NER (SpaCy, multi-language)
└→ Response: "processing_background" + document_id

Phase 2: Background Refinement (30-120s async)
Domain-Driven S-P-O Extraction →
├→ Step 7: Select Extraction Prompt (by domain_id)
│           └→ If "medical": use medical entity/relation types
│           └→ If "legal": use legal domain vocabulary
│           └→ Else: use 15+22 universal types
├→ Step 8: vLLM Extraction (Nemotron NVFP4, 256+ parallel)
│           └→ S-P-O output (subject, predicate, object with types)
│           └→ Fallback: Ollama (Nemotron Nano) if vLLM unavailable
├→ Step 9: Type Validation (15 entity + 22 relation universal types)
├→ Step 10: Neo4j Storage (with domain_id + sub_type property)
├→ Step 11: Community Detection (Leiden/Louvain)
└→ Status: "ready" when complete

Phase 3: Domain Seeding (Optional)
Seed Domains from YAML (Spring 125.8) →
├→ 35 domains (DDC + FORD categories)
├→ Entity/relation vocabularies per domain
├→ Deployment profiles (1-5 active domains per customer)
└→ Auto-configuration from seed_domains.yaml
```

**Domain Taxonomy (35 DDC+FORD Domains):**

| Category | Domains | Examples |
|----------|---------|----------|
| **DDC (30)** | Knowledge, Computing, Language, Medicine, etc. | 000-999 hierarchy |
| **FORD (5)** | Engineering, Business, Environmental, etc. | Domain-specific |
| **Special** | Custom, Generic | Fallback types |

**Two-Tier Entity/Relation System (ADR-060):**

| Tier | Purpose | Storage |
|------|---------|---------|
| **Tier 1: Universal** | 15 entity types (Person, Org, Location, etc.), 22 relation types | Neo4j Label + Property |
| **Tier 2: Domain** | Domain-specific sub-types (e.g., "Physician" for medical domain) | Neo4j `sub_type` property |

**Deployment Profiles (Sprint 125.8):**

```yaml
# seed_domains.yaml
profiles:
  healthcare:
    domains: [medical, pharmaceutical]
    entity_types: [Person, Organization, Procedure, Medication]
    relation_types: [TREATS, CAUSED_BY, PRESCRIBED_BY]

  legal:
    domains: [law, regulation]
    entity_types: [Person, Organization, Law, Case]
    relation_types: [CITES, CONTRADICTS, ENFORCES]

  academic:
    domains: [research, education]
    entity_types: [Person, Organization, Topic, Publication]
    relation_types: [AUTHORED_BY, CITES, COLLABORATES_WITH]
```

**Domain-Aware Frontend (Sprint 125.9):**

1. **Domain Detection at Upload:**
   - Show detected domain (e.g., "Medical" for healthcare docs)
   - Allow manual override to specific domain

2. **Deployment Profile Page:**
   - Select active domains (1-5 per environment)
   - Configure entity/relation type vocabularies
   - Manage domain-specific extraction rules

3. **Domain Filter in Graph Retrieval:**
   - Filter entities by domain (e.g., "Show only medical entities")
   - Sub-type display in graph visualization

4. **Retrieval Targeting:**
   - Query inherits document's domain context
   - Graph queries respect domain boundaries

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
| **82** | RAGAS Phase 1 Benchmark | 500-sample text-only benchmark (HotpotQA + RAGBench + LogQA), stratified sampling, 8 question types, 3 difficulty levels |
| **83** | ER-Extraction Improvements | 3-Rank LLM Cascade (Nemotron3→GPT-OSS→Hybrid NER), Gleaning (+20-40% recall), Fast Upload (2-5s), Multi-language SpaCy (DE/EN/FR/ES), Comprehensive Logging (P95 metrics, GPU VRAM, LLM cost) |
| **87** | BGE-M3 Native Hybrid Search | FlagEmbedding Service (Dense 1024D + Sparse lexical), Qdrant multi-vector collection, Server-side RRF fusion, **Replaces BM25** |
| **88** | RAGAS Phase 2 Evaluation | Tables (T2-RAGBench) + Code (MBPP) evaluation, 10/10 GT retrieval (100%), Async embedding fix, Comprehensive metrics schema |
| **92** | Recursive LLM Adaptive Scoring | BGE-M3 hybrid relevance scoring (20-40x faster), Parallel worker configuration (1-10 workers per backend), Configurable scoring methods |
| **93** | Tool Composition Framework | ToolComposer + PolicyEngine integration, Skill-Tool Mapping Layer (41 tests, 1711 LOC), Browser Tool for web automation, LangGraph 1.0 InjectedState patterns |

### Sprint 87-88: BGE-M3 Native Hybrid Search

**Sprint 87: Architecture Evolution (BM25 → BGE-M3 Sparse)**

The hybrid search architecture evolved from separate Vector + BM25 to unified BGE-M3 Dense + Sparse:

```
OLD (Sprints 1-86):
┌─────────────────────────────────────────────────────────────┐
│  Query → ┌─────────────────┐ ┌─────────────────┐            │
│          │ SentenceTransf. │ │     BM25        │            │
│          │ (Dense 1024D)   │ │ (Separate Index)│            │
│          └────────┬────────┘ └────────┬────────┘            │
│                   │                   │                      │
│                   └───────┬───────────┘                      │
│                           ↓                                  │
│                    Client-Side RRF                           │
│                           ↓                                  │
│                      Results                                 │
└─────────────────────────────────────────────────────────────┘

NEW (Sprint 87+):
┌─────────────────────────────────────────────────────────────┐
│  Query → ┌─────────────────────────────────────────┐        │
│          │          FlagEmbedding (BGE-M3)         │        │
│          │  ┌──────────────┐ ┌──────────────────┐  │        │
│          │  │ Dense (1024D)│ │ Sparse (Lexical) │  │        │
│          │  └──────┬───────┘ └────────┬─────────┘  │        │
│          └─────────┼──────────────────┼────────────┘        │
│                    │                  │                      │
│                    ↓                  ↓                      │
│          ┌─────────────────────────────────────────┐        │
│          │        Qdrant Multi-Vector Collection   │        │
│          │  Named Vectors: "dense" + "sparse"      │        │
│          │         Server-Side RRF Fusion          │        │
│          └─────────────────────────────────────────┘        │
│                           ↓                                  │
│                      Results                                 │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
1. **Always in Sync:** Dense + Sparse generated in single forward pass
2. **Learned Lexical Weights:** BGE-M3 learns better token importance than BM25
3. **Server-Side RRF:** Qdrant Query API fuses vectors natively (lower latency)
4. **Single Model:** Simpler deployment, lower memory footprint (~2GB VRAM)

**Sprint 88: RAGAS Evaluation Framework**

Comprehensive evaluation with 4 RAGAS metrics + operational metrics:

| Metric Type | Metrics |
|-------------|---------|
| **RAGAS Quality** | Context Precision, Context Recall, Faithfulness, Answer Relevancy |
| **Ingestion** | Time/doc, Chunks/doc, Characters/doc, Entities/doc, Relations/doc |
| **Retrieval** | Latency (P50/P95/P99), Contexts retrieved, GT match rate |
| **LLM Evaluation** | Eval time/sample, Token usage, Model used |

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

## Sprint 92-93: Advanced Tool Composition & Recursive LLM Optimization

### Sprint 92: Recursive LLM Adaptive Scoring (ADR-052)

**Problem:** Recursive LLM context processor was using expensive LLM scoring (2-4 seconds for 20 segments) instead of efficient embedding-based scoring.

**Solution: BGE-M3 Hybrid Relevance Scoring**

```python
# OLD (Sprints 1-91): Per-segment LLM scoring
for segment in segments:
    score = await llm_score_segment(segment, query)  # 100-200ms × 20 = 2-4s

# NEW (Sprint 92+): BGE-M3 batch embedding scoring
embedding_service = get_embedding_service()  # FlagEmbedding with BGE-M3

# Embed all segments in one pass
query_embedding = embedding_service.embed_single(query)
segment_embeddings = embedding_service.embed_batch(segments)

# Compute hybrid similarity for all at once
for i, segment in enumerate(segments):
    sparse_score = compute_sparse_similarity(...)
    dense_score = cosine_similarity(...)
    segment.relevance_score = 0.4 * sparse_score + 0.6 * dense_score
```

**Performance Impact:**
- **Scoring Latency:** 2-4 seconds → **50-100ms** (20-40x speedup)
- **Cost:** 20 LLM API calls → **0 LLM calls** (pure embedding compute)
- **Accuracy:** BGE-M3 achieves **87.6% NDCG@10** on BEIR (proven accuracy)

**Parallel Worker Configuration:**
```python
class RecursiveLLMSettings(BaseSettings):
    max_parallel_workers: int = Field(
        default=1,  # DGX Spark: single-threaded
        description="Max parallel segment processing (1 for Ollama, 5-10 for cloud)"
    )

    worker_limits: dict[str, int] = {
        "ollama": 1,        # DGX Spark
        "openai": 10,       # Cloud
        "alibaba": 5,       # Moderate parallelism
    }
```

**Performance Projections:**
- **DGX Spark (1 worker):** 52-54s → 50-51s (~5% improvement)
- **Cloud (10 workers):** 52-54s → 10-11s (**5x speedup**)

**References:** [Sprint 92 RECURSIVE_LLM_IMPROVEMENTS.md](sprints/SPRINT_92_RECURSIVE_LLM_IMPROVEMENTS.md), ADR-052

---

### Sprint 93: Tool Composition Framework (Sprint 93 Feature 93.1-93.4)

**Architecture:** Complete tool composition ecosystem with intelligent routing, policy enforcement, and skill-aware tool mapping.

#### Feature 93.1: ToolComposer Framework

**Purpose:** Plan and compose tool chains for complex multi-step tasks.

```python
from src.agents.tools.composition import ToolComposer

composer = ToolComposer(tool_registry={...})

# Plan a tool chain
request = UserRequest(
    task="Research AGI safety papers and summarize findings",
    skills=["research", "analysis"]
)

chain = await composer.plan_chain(request)
# → [BrowserTool, WebSearchTool, DocumentParserTool, SummarizationTool]

result = await composer.execute_chain(chain, input_data="AGI safety papers 2025")
```

**Key Capabilities:**
- Intelligent tool selection based on task requirements
- Dependency resolution and validation
- Execution planning and optimization
- Skill-based filtering (only tools the skill can use)
- Fallback chains for fault tolerance
- Cost optimization (prefer local tools over API calls)

#### Feature 93.2: PolicyEngine (Access Control & Guardrails)

**Purpose:** Enforce execution policies and security guardrails on tool usage.

```python
from src.agents.tools.policy import PolicyEngine

policy = PolicyEngine()

# Register skill permissions
policy.register_skill("research", ["browser", "web_search", "file_read"])
policy.register_skill("analysis", ["python_execute", "data_analysis"])

# Set rate limits
policy.set_rate_limit("openai_api", 10, per_minute=True)
policy.set_rate_limit("browser", 50, per_day=True)

# Enforce policy
can_execute = await policy.check_permission(
    skill="research",
    tool="browser",
    inputs={"url": "https://example.com"}
)

if can_execute:
    result = await tool.execute(**inputs)
else:
    raise PermissionError("Skill 'research' cannot use 'browser' tool")
```

**Enforcement Layers:**
1. **Skill Authorization:** Which skills can use which tools
2. **Input Validation:** Validate tool inputs against schema
3. **Rate Limiting:** Per-tool rate limits with time windows
4. **Audit Logging:** Track all tool usage for compliance
5. **Admin Bypass:** Allow privileged operations with audit trail

#### Feature 93.3: Skill-Tool Mapping Layer (41 tests, 1711 LOC)

**Purpose:** Dynamic discovery and access control for tool-skill relationships.

```python
from src.agents.tools.mapping import SkillToolMapper, ToolCapability

mapper = SkillToolMapper()

# Register tool with capabilities
mapper.register_tool(
    "browser",
    ToolCapability(
        name="browser",
        description="Web browsing with Playwright",
        async_support=True,
        requires_network=True,
        rate_limit=30,
        tags=["web", "automation"],
    ),
    required_skills=["research", "web_automation"],
)

# Dynamic discovery
async_tools = mapper.discover_tools("research", {"async_support": True})
# → [ToolCapability(name='browser', ...), ToolCapability(name='web_search', ...)]

# Permission checks
can_use = mapper.can_skill_use_tool("research", "browser")  # → True
skills_for_tool = mapper.get_skills_for_tool("browser")  # → ["research", "web_automation"]
```

**Components:**
- `ToolCapability` dataclass: Rich metadata (parameters, async support, streaming, network, filesystem)
- `SkillToolMapper` class: Registration, discovery, permission checks
- `check_tool_permission()` helper: Integrated mapper + PolicyEngine checks
- `InjectedState` pattern: LangGraph 1.0 skill context in tools

**Test Coverage:** 41 unit tests, 100% pass rate, strict type checking

#### Feature 93.4: Browser Tool for Web Automation

**Purpose:** Safe web browsing and scraping via Playwright with Skill-aware access control.

```python
from src.agents.tools.browser import BrowserTool

browser = BrowserTool()

# Navigate and extract
result = await browser.navigate(
    url="https://arxiv.org",
    action="click",
    selector="input[name='query']"
)

# Scrape with CSS selectors
papers = await browser.query_selector_all(
    selector=".arxiv-result",
    extract={"title": "h2", "abstract": "p.abstract"}
)

# Wait for dynamic content
await browser.wait_for(text="Loaded", timeout=10000)

# Close gracefully
await browser.close()
```

**Security Features:**
- Network isolation (only allowed domains)
- Timeout enforcement (max 300s per operation)
- Memory limits (prevent infinite loops)
- User-agent rotation (avoid detection)
- Screenshot capabilities (visual verification)
- SSL certificate validation

**Integration with PolicyEngine:**
```python
# Policy checks before navigation
policy.set_allowed_domains("research", ["arxiv.org", "scholar.google.com"])
policy.set_rate_limit("browser", requests_per_minute=5)

# Enforced at execution time
if not await policy.check_permission("research", "browser", inputs={"url": url}):
    raise PermissionError("Domain not allowed")
```

---

## LangGraph 1.0 Architecture Patterns (Sprint 93+)

### InjectedState for Skill Context

**Pattern:** Pass skill/user context through LangGraph state to tools.

```python
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def skill_aware_tool(
    query: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Tool with access to skill context."""
    active_skill = state.get("active_skill")
    user_id = state.get("user_id")

    # Check permission via mapper
    if not mapper.can_skill_use_tool(active_skill, "browser"):
        raise PermissionError("Skill not authorized")

    # Execute with skill context
    return await browser.execute(query, skill=active_skill)
```

### Tool Composition in LangGraph

**Pattern:** Integrate ToolComposer with LangGraph agent graph.

```python
from langgraph.graph import StateGraph, START, END

class ToolCompositionState(TypedDict):
    task: str
    skill: str
    tool_chain: list[str]
    execution_results: list[dict]

workflow = StateGraph(ToolCompositionState)

async def plan_tools(state: ToolCompositionState):
    """Plan tool chain based on task."""
    composer = ToolComposer(tool_registry=get_tool_registry())
    chain = await composer.plan_chain(
        UserRequest(task=state["task"], skills=[state["skill"]])
    )
    return {"tool_chain": chain}

async def execute_tools(state: ToolCompositionState):
    """Execute planned tool chain."""
    results = []
    for tool in state["tool_chain"]:
        result = await execute_tool(tool, state["task"])
        results.append(result)
    return {"execution_results": results}

workflow.add_node("planner", plan_tools)
workflow.add_node("executor", execute_tools)
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", END)
```

---

## Performance Characteristics (Updated Sprint 93)

| Operation | Target Latency (p95) | Achieved | Notes |
|-----------|---------------------|----------|-------|
| Simple Query (Vector) | <200ms | 180ms | ✅ |
| Hybrid Query (Vector+Graph) | <500ms | 450ms | ✅ |
| Complex Multi-Hop | <1000ms | 980ms | ✅ |
| Recursive LLM Scoring | <500ms | 50-100ms | ✅ Sprint 92 improvement (20-40x) |
| Tool Composition Planning | <100ms | <50ms | ✅ Sprint 93 (in-memory lookup) |
| Skill-Tool Permission Check | <10ms | <5ms | ✅ Sprint 93 (O(1) operation) |
| Browser Navigation | <5s | 2-4s | ✅ With timeout enforcement |
| Ingestion (per page) | <2s | 1.8s | ✅ GPU accelerated |
| Embedding (batch 32) | <500ms | 420ms | ✅ BGE-M3 |

---

**Document Consolidated:** Sprint 60 Feature 60.1
**Sprint 67-68 Updates:** 2025-12-31
**Sprint 72 Updates:** 2026-01-03 (Admin Features)
**Sprint 76-79 Updates:** 2026-01-08 (Graph Search Enhancement, RAGAS Optimization)
**Sprint 81 Updates:** 2026-01-09 (C-LARA SetFit Multi-Teacher Intent Classification 95.22%)
**Sprint 92-93 Updates:** 2026-01-15 (Recursive LLM Adaptive Scoring, Tool Composition Framework)
**Sources:** ARCHITECTURE_EVOLUTION.md, COMPONENT_INTERACTION_MAP.md, STRUCTURE.md, SPRINT_92_RECURSIVE_LLM_IMPROVEMENTS.md, SPRINT_93_FEATURE_93.3_SUMMARY.md, SPRINT_100_PLAN.md
**Maintainer:** Claude Code with Human Review
