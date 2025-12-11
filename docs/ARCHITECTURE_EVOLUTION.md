# ARCHITECTURE EVOLUTION - Sprint Journey
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Last Updated:** 2025-12-11 (Sprint 43)

---

## Executive Summary

**AEGIS RAG** = Enterprise-grade Hybrid RAG System
- **Local-First:** Ollama-based, zero cloud dependencies for dev
- **4-Way Hybrid Retrieval:** Vector + BM25 + Graph Local + Graph Global with Intent-Weighted RRF
- **3-Layer Memory:** Redis → Qdrant → Graphiti
- **Multi-Agent:** LangGraph with 5 specialized agents
- **Bi-Temporal:** Entity versioning with time travel queries

---

## Sprint Overview (1-42)

| Sprint | Theme | Key Change |
|--------|-------|------------|
| 1 | Foundation | Project setup, Docker stack |
| 2 | Vector Search | Qdrant + BM25 + Hybrid (RRF) |
| 3 | Advanced Retrieval | Reranking, RAGAS evaluation |
| 4 | Orchestration | LangGraph Multi-Agent (4 agents) |
| 5 | Graph RAG | LightRAG + Neo4j |
| 6 | Hybrid Fusion | Vector-Graph fusion, routing |
| 7 | Memory | Graphiti 3-layer architecture |
| 8 | Testing | E2E critical path (80% baseline) |
| 9 | MCP + Memory | MCP client, consolidation pipeline |
| 10 | UI | Gradio interface |
| 11 | Optimization | GPU support, unified pipeline |
| 12 | Production | CI/CD, monitoring, deployment |
| 13 | Entity Pipeline | Pure LLM extraction |
| 14 | Performance | Benchmarking, Prometheus |
| 15 | React Frontend | SSE streaming, Perplexity UI |
| 16 | Unified Arch | BGE-M3 system-wide, chunking |
| 17 | Admin UI | User profiling, archiving |
| 18-19 | CI/CD & Debt | Technical debt resolution |
| 20 | Extraction | Pure LLM pipeline default |
| 21 | Container | Docling CUDA, VLM |
| 22-24 | Production | Cleanup, dependency optimization |
| 25 | LLM Arch | AegisLLMProxy migration |
| 26-27 | Frontend | Modal refactoring, query enhancement |
| 28 | Frontend UX | Perplexity features, settings |
| 29-30 | VLM + Testing | VLM PDF ingestion, Frontend E2E |
| 31 | E2E Testing | 111 Playwright tests, Admin UI |
| 32 | Chunking | Section-aware, Neo4j sections |
| 33 | Indexing | Directory indexing, multi-format |
| 34 | Graph | RELATES_TO relationships, visualization |
| 35-36 | UX | Seamless chat, faceted search, export |
| 37 | Pipeline | Streaming pipeline, worker pools |
| 38 | Auth + GraphRAG | JWT Auth, Share Links, Multi-Hop GraphRAG |
| 39 | Bi-Temporal | Entity versioning, time travel queries |
| 40 | MCP + Sandbox | MCP integration, Bubblewrap shell sandbox |
| 42 | 4-Way Hybrid | Intent-Weighted RRF, Graph Global channel |
| 43 | Dedup & Monitoring | MultiCriteria Dedup (10.1%), Prometheus Metrics, Benchmarking |

---

## Architecture Milestones

### Sprint 1-4: Foundation & Orchestration
```
User Query → FastAPI → LangGraph Router → Agents → Response
                              │
                   ┌──────────┼──────────┐
                   ▼          ▼          ▼
               Vector     Graph      Memory
               Agent      Agent      Agent
```

### Sprint 5-6: Hybrid Retrieval
- **LightRAG** dual-level retrieval (entities + topics)
- **RRF Fusion** for vector + graph results
- Parallel execution via LangGraph Send API

### Sprint 7: 3-Layer Memory
```
Layer 1: Redis     (Short-term, <10ms, session state)
Layer 2: Qdrant    (Semantic, <50ms, long-term facts)
Layer 3: Graphiti  (Episodic, <200ms, temporal relationships)
```

### Sprint 13-20: Extraction Evolution
- **Sprint 13:** Three-Phase Pipeline (SpaCy → Semantic Dedup → Gemma)
- **Sprint 20:** Pure LLM Pipeline (single-pass extraction)
- **Result:** Simpler architecture, better quality

### Sprint 21: Container-Based Ingestion
- **Docling CUDA:** GPU-accelerated OCR (95% accuracy vs 70% LlamaIndex)
- **Performance:** 420s → 120s per document (3.5x faster)
- **LlamaIndex:** Deprecated for ingestion, kept for connectors

### Sprint 23-25: Multi-Cloud LLM
- **AegisLLMProxy:** Unified routing (Local → Alibaba → OpenAI)
- **Cost Tracking:** SQLite database, $120/month budget
- **Complete Migration:** 7 files migrated in Sprint 25

### Sprint 32: Section-Aware Chunking
- **Adaptive merging:** 800-1800 tokens respecting document structure
- **PowerPoint:** 124 chunks → 2-3 chunks (-98% fragmentation)
- **Neo4j:** Section nodes for hierarchical queries

### Sprint 34: Knowledge Graph Enhancement
- **RELATES_TO:** Semantic relationships between entities
- **Visualization:** Color-coded edges, weight-based filtering
- **19 E2E tests** for graph features

### Sprint 37: Streaming Pipeline
- **AsyncIO queues** with backpressure
- **SSE progress** updates
- **Worker pool** configuration

### Sprint 38: Authentication & GraphRAG Multi-Hop
- **JWT Authentication:** Frontend login, protected routes, API tokens
- **Conversation Search:** Semantic search through archived conversations
- **Share Links:** Time-limited public conversation links
- **GraphRAG Multi-Hop:** Sequential sub-query execution with context injection

### Sprint 39: Bi-Temporal Knowledge Graph
- **Entity Versioning:** Version history with rollback capability
- **Time Travel Queries:** "What did we know on date X?"
- **Change Tracking:** Audit trail with `changed_by` user attribution
- **Temporal UI:** Isolated Time Travel tab with date slider

### Sprint 40: MCP Integration & Shell Sandbox
- **MCP Client:** Connect to external tool servers (Filesystem, GitHub, Web)
- **Secure Shell Sandbox:** Bubblewrap process isolation (not Docker)
- **deepagents Integration:** Multi-language CodeAct (Bash + Python)
- **AegisRAG as MCP Server:** Expose search/query/shell tools

### Sprint 42: 4-Way Hybrid RRF
- **Intent Classification:** LLM + rule-based (factual, keyword, exploratory, summary)
- **4 Retrieval Channels:** Vector + BM25 + Graph Local + Graph Global
- **Intent-Weighted Fusion:** Dynamic RRF weights per query intent
- **Automatic Community Detection:** community_id on entity nodes

### Sprint 43: Multi-Criteria Deduplication & Pipeline Monitoring
- **MultiCriteriaDeduplicator:** 4 matching criteria (exact, edit-distance, substring, semantic)
- **10.1% Entity Reduction:** On large multi-chunk documents (68k chars, 18 chunks)
- **12 New Prometheus Metrics:** Chunking, deduplication, extraction by type
- **Comprehensive Benchmarking:** Chunk sizes (500-4000), model comparison (gemma3:4b vs qwen2.5:7b)
- **Parallel Extraction:** +20-30% more entities by combining gemma3:4b + qwen2.5:7b
- **Model Stability Finding:** qwen2.5:7b stable across all chunk sizes, gemma3:4b unstable >2500 chars

---

## Current Retrieval Architecture (Sprint 42)

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│              Intent Classifier (qwen3:8b)                    │
│         factual | keyword | exploratory | summary            │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Vector  │   │   BM25   │   │  Graph   │   │  Graph   │
    │  Search  │   │  Search  │   │  Local   │   │  Global  │
    │ (Qdrant) │   │ (rank-   │   │(Entity→  │   │(Community│
    │          │   │  bm25)   │   │  Chunk)  │   │→ Chunk)  │
    └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                                │
                                ▼
              ┌─────────────────────────────────────────┐
              │     Intent-Weighted RRF Fusion          │
              │                                         │
              │  score = Σ w_i(intent) * 1/(k + rank_i) │
              └─────────────────────────────────────────┘
                                │
                                ▼
                         Ranked Results
```

**Intent Weight Profiles:**

| Intent | Vector | BM25 | Local | Global |
|--------|--------|------|-------|--------|
| factual | 0.3 | 0.3 | 0.4 | 0.0 |
| keyword | 0.1 | 0.6 | 0.3 | 0.0 |
| exploratory | 0.2 | 0.1 | 0.2 | 0.5 |
| summary | 0.1 | 0.0 | 0.1 | 0.8 |

---

## Performance Evolution

| Metric | Sprint 2 | Sprint 21 | Sprint 37 | Sprint 42 |
|--------|----------|-----------|-----------|-----------|
| Vector Search | <200ms | <150ms | <100ms | <100ms |
| Hybrid Query | <500ms | <400ms | <300ms | <350ms (4-way) |
| Document Ingestion | 420s | 120s | 90s | 90s |
| Test Coverage | 212 | 400+ | 500+ | 600+ |
| Retrieval Channels | 2 | 2 | 2 | 4 |

---

## Key Learnings

### What Worked
1. **RRF Fusion** - Score-agnostic, works for heterogeneous results
2. **3-Layer Memory** - Flexibility for different query types
3. **Pure LLM Extraction** - Simpler than Three-Phase, better quality
4. **Docling CUDA** - Massive OCR improvement over LlamaIndex
5. **AegisLLMProxy** - Clean abstraction for multi-cloud routing
6. **Intent-Weighted RRF** - Dynamic fusion adapts to query type
7. **Bi-Temporal Opt-In** - Performance preserved for standard queries
8. **Multi-Criteria Deduplication** - 10.1% reduction on multi-chunk docs
9. **Parallel Model Extraction** - Fault-tolerance + 20-30% more entities

### Challenges Overcome
1. **Embedding Mismatch** - Solved with BGE-M3 system-wide
2. **Chunk Fragmentation** - Solved with section-aware chunking
3. **Entity Extraction Quality** - Solved with Pure LLM
4. **Cost Visibility** - Solved with SQLite cost tracking
5. **Multi-Hop Reasoning** - Solved with GraphRAG + context injection
6. **Shell Security** - Solved with Bubblewrap (not Docker)
7. **Entity Duplicates** - Solved with MultiCriteriaDeduplicator (ADR-044)
8. **Model Instability** - Solved with parallel extraction fallback

---

## Current System Architecture (Sprint 42)

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                            │
│      (SSE Streaming, Perplexity-style UI, Time Travel)      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                           │
│              (REST API, JWT Auth, SSE, MCP)                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              LangGraph Multi-Agent System                    │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌───────┐ │
│  │Coordin-│  │ Vector │  │ Graph  │  │ Memory │  │Action │ │
│  │  ator  │  │ Agent  │  │ Agent  │  │ Agent  │  │ Agent │ │
│  └────────┘  └────────┘  └────────┘  └────────┘  └───────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                 4-Way Hybrid Retrieval                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ Vector  │  │  BM25   │  │  Graph  │  │  Graph Global   │ │
│  │ (Qdrant)│  │         │  │  Local  │  │  (Community)    │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Storage & Services                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐      │
│  │  Redis  │  │ Qdrant  │  │  Neo4j  │  │ AegisLLM  │      │
│  │ Memory  │  │ Vector  │  │  Graph  │  │   Proxy   │      │
│  └─────────┘  └─────────┘  └─────────┘  └───────────┘      │
│                                                              │
│  ┌─────────┐  ┌─────────────────────────────────────────┐   │
│  │   MCP   │  │      Bubblewrap Shell Sandbox           │   │
│  │ Servers │  │    (Bash + Python via Pyodide)          │   │
│  └─────────┘  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Feature Summary by Sprint Range

### Foundation (Sprint 1-12)
- Project setup, Docker infrastructure
- Qdrant + BM25 hybrid search with RRF
- LangGraph orchestration, 4 agents
- LightRAG + Neo4j graph RAG
- 3-Layer memory (Redis, Qdrant, Graphiti)
- Gradio UI, CI/CD, monitoring

### Advanced Features (Sprint 13-25)
- Pure LLM entity extraction
- React frontend with SSE streaming
- BGE-M3 system-wide embeddings
- Docling CUDA container ingestion
- AegisLLMProxy multi-cloud routing
- Section-aware adaptive chunking

### Production Polish (Sprint 26-37)
- Perplexity-style UX features
- Graph visualization with RELATES_TO
- 111 Playwright E2E tests
- Streaming pipeline with worker pools
- Faceted search and export

### Enterprise Features (Sprint 38-43)
- JWT authentication with protected routes
- Conversation search and share links
- GraphRAG multi-hop reasoning
- Bi-temporal entity versioning
- MCP integration and shell sandbox
- 4-Way Hybrid RRF with intent classification
- Multi-criteria entity deduplication (10.1% reduction)
- Comprehensive pipeline monitoring (12 new Prometheus metrics)
