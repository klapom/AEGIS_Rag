# ARCHITECTURE EVOLUTION - Sprint Journey
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Last Updated:** 2025-12-08 (Sprint 37)

---

## Executive Summary

**AEGIS RAG** = Enterprise-grade Hybrid RAG System
- **Local-First:** Ollama-based, zero cloud dependencies for dev
- **Hybrid Retrieval:** Vector + Graph + BM25 with RRF Fusion
- **3-Layer Memory:** Redis → Qdrant → Graphiti
- **Multi-Agent:** LangGraph with 5 specialized agents

---

## Sprint Overview (1-37)

| Sprint | Theme | Key Change | ADRs |
|--------|-------|------------|------|
| 1 | Foundation | Project setup, Docker stack | ADR-001, ADR-002 |
| 2 | Vector Search | Qdrant + BM25 + Hybrid (RRF) | ADR-003, ADR-004, ADR-009 |
| 3 | Advanced Retrieval | Reranking, RAGAS evaluation | - |
| 4 | Orchestration | LangGraph Multi-Agent (4 agents) | - |
| 5 | Graph RAG | LightRAG + Neo4j | ADR-005 |
| 6 | Hybrid Fusion | Vector-Graph fusion, routing | - |
| 7 | Memory | Graphiti 3-layer architecture | ADR-006 |
| 8 | Testing | E2E critical path (80% baseline) | ADR-014, ADR-015 |
| 9 | MCP + Memory | MCP client, consolidation pipeline | ADR-007 |
| 10 | UI | Gradio interface | - |
| 11 | Optimization | GPU support, unified pipeline | - |
| 12 | Production | CI/CD, monitoring, deployment | - |
| 13 | Entity Pipeline | Pure LLM extraction | ADR-017, ADR-018 |
| 14 | Performance | Benchmarking, Prometheus | ADR-019 |
| 15 | React Frontend | SSE streaming, Perplexity UI | ADR-020, ADR-021 |
| 16 | Unified Arch | BGE-M3 system-wide, chunking | ADR-022, ADR-023, ADR-024 |
| 17 | Admin UI | User profiling, archiving | - |
| 18-19 | CI/CD & Debt | Technical debt resolution | - |
| 20 | Extraction | Pure LLM pipeline default | ADR-026 |
| 21 | Container | Docling CUDA, VLM | ADR-027, ADR-028, ADR-029, ADR-030 |
| 22-24 | Production | Cleanup, dependency optimization | - |
| 25 | LLM Arch | AegisLLMProxy migration | ADR-033 |
| 26-27 | Frontend | Modal refactoring, query enhancement | - |
| 28 | Frontend UX | Perplexity features, settings | ADR-034, ADR-035, ADR-036 |
| 29-30 | VLM + Testing | VLM PDF ingestion, Frontend E2E | - |
| 31 | E2E Testing | 111 Playwright tests, Admin UI | - |
| 32 | Chunking | Section-aware, Neo4j sections | ADR-039 |
| 33 | Indexing | Directory indexing, multi-format | - |
| 34 | Graph | RELATES_TO relationships, visualization | ADR-040, ADR-041 |
| 35-36 | UX | Seamless chat, faceted search, export | - |
| 37 | Pipeline | Streaming pipeline, worker pools | ADR-042, ADR-043 |

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
- **Sprint 20:** Pure LLM Pipeline (single-pass extraction, ADR-026)
- **Result:** Simpler architecture, better quality

### Sprint 21: Container-Based Ingestion
- **Docling CUDA:** GPU-accelerated OCR (95% accuracy vs 70% LlamaIndex)
- **Performance:** 420s → 120s per document (3.5x faster)
- **LlamaIndex:** Deprecated for ingestion, kept for connectors (ADR-028)

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

---

## Performance Evolution

| Metric | Sprint 2 | Sprint 21 | Sprint 37 |
|--------|----------|-----------|-----------|
| Vector Search | <200ms | <150ms | <100ms |
| Hybrid Query | <500ms | <400ms | <300ms |
| Document Ingestion | 420s | 120s | 90s (streaming) |
| Test Coverage | 212 tests | 400+ tests | 500+ tests |

---

## Key Learnings

### What Worked
1. **RRF Fusion** - Score-agnostic, works for heterogeneous results
2. **3-Layer Memory** - Flexibility for different query types
3. **Pure LLM Extraction** - Simpler than Three-Phase, better quality
4. **Docling CUDA** - Massive OCR improvement over LlamaIndex
5. **AegisLLMProxy** - Clean abstraction for multi-cloud routing

### Challenges Overcome
1. **Embedding Mismatch** - Solved with BGE-M3 system-wide (ADR-024)
2. **Chunk Fragmentation** - Solved with section-aware chunking (ADR-039)
3. **Entity Extraction Quality** - Solved with Pure LLM (ADR-026)
4. **Cost Visibility** - Solved with SQLite cost tracking

---

## Current Architecture (Sprint 37)

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│         (SSE Streaming, Perplexity-style UI)            │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                    FastAPI Backend                       │
│              (REST API, WebSocket, SSE)                 │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│              LangGraph Multi-Agent System               │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐       │
│  │ Router │  │ Vector │  │ Graph  │  │ Memory │       │
│  │ Agent  │  │ Agent  │  │ Agent  │  │ Agent  │       │
│  └────────┘  └────────┘  └────────┘  └────────┘       │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   Storage Layer                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐  │
│  │  Redis  │  │ Qdrant  │  │  Neo4j  │  │AegisLLM   │  │
│  │ Memory  │  │ Vector  │  │  Graph  │  │  Proxy    │  │
│  └─────────┘  └─────────┘  └─────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## ADR Summary

| Category | ADRs |
|----------|------|
| **Orchestration** | ADR-001 (LangGraph) |
| **LLM** | ADR-002 (Ollama), ADR-033 (AegisLLMProxy) |
| **Vector** | ADR-003 (Hybrid), ADR-004 (Qdrant), ADR-024 (BGE-M3) |
| **Graph** | ADR-005 (LightRAG), ADR-040 (RELATES_TO) |
| **Memory** | ADR-006 (3-Layer), ADR-007 (MCP) |
| **Ingestion** | ADR-027 (Docling), ADR-028 (LlamaIndex deprecation) |
| **Chunking** | ADR-039 (Section-Aware) |
| **Frontend** | ADR-020 (SSE), ADR-021 (Perplexity UI) |
