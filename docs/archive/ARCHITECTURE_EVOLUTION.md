# ARCHITECTURE EVOLUTION - Sprint Journey
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Last Updated:** 2025-12-16 (Sprint 49)

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
| 40 | Graphiti Memory | 3-layer memory integration, episode creation, temporal retrieval |
| 41 | Parallel Extraction | Multi-model parallel LLM extraction, entity deduplication |
| 42 | Neo4j Migration | Community Edition migration, GDS integration |
| 43 | Entity Dedup | Multi-criteria deduplication (ADR-044), 10.1% reduction |
| 44 | Relation Dedup | Entity normalization in relations, type synonym resolution |
| 45 | LangGraph State | Unified AgentState, phase-based workflow |
| 46 | Cancellation | Request cancellation, graceful stream cleanup |
| 47 | Docling CUDA | GPU-accelerated ingestion, 3-5x speedup |
| 48 | Phase Events | Real-time thinking events, SSE streaming, Nemotron LLM |
| 49 | Dynamic UX | Embedding-based dedup, provenance tracking, consistency validation |
| 50 | Token Streaming | Token-by-token answer generation with TTFT tracking |
| 51 | Maximum Hybrid | 4-Signal Fusion, CommunityDetector fixes, Phase UI |

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

### Sprint 40: Graphiti Memory Integration
- **3-Layer Memory System:** Episodic (temporal events), Semantic (entity facts), Entity (isolated nodes)
- **Redis-Based Consolidation:** Automatic memory consolidation pipeline
- **Episode Creation API:** `POST /api/v1/memory/episodes` for explicit memory capture
- **Temporal Retrieval:** Query memory with time-aware filters and sorting
- **Integration Points:** Memory agent receives memory vectors alongside graph/vector results
- **Code Location:** `src/components/memory/graphiti_integration.py`

### Sprint 41: Multi-Model Parallel Extraction
- **Dual-Model Strategy:** gemma3:4b + qwen2.5:7b running in parallel
- **Entity Deduplication:** Post-extraction dedup merges results from both models
- **+20-30% Entity Recall:** Complementary extraction patterns improve coverage
- **Fault Tolerance:** If one model fails, use results from other model
- **Integration:** Pluggable in LangGraph ingestion agent
- **Code Location:** `src/components/ingestion/parallel_extraction.py`

### Sprint 42: Neo4j Community Edition Migration
- **From Memgraph to Neo4j:** Full migration of graph storage
- **GDS Library Support:** Graph Data Science for community detection, centrality analysis
- **APOC Integration:** Advanced stored procedures for complex graph operations
- **Query Language:** Cypher query syntax identical to Memgraph (seamless transition)
- **Performance:** Comparable to Memgraph on community-size graphs (<10M nodes)
- **Cost:** Zero-cost open-source alternative to Memgraph Pro

### Sprint 43: Multi-Criteria Entity Deduplication (ADR-044)
- **MultiCriteriaDeduplicator:** 4 matching criteria (exact, edit-distance, substring, semantic)
- **Typo & Abbreviation Handling:** Catches "AI" vs "artificial intelligence", case variations
- **False Positive Prevention:** Prevents "AI" (artificial intelligence) merging with "AI" in "NVIDIA"
- **10.1% Entity Reduction:** On large multi-chunk documents (68k chars, 18 chunks)
- **12 New Prometheus Metrics:** Chunking, deduplication, extraction by type
- **Comprehensive Benchmarking:** Chunk sizes (500-4000), model comparison (gemma3:4b vs qwen2.5:7b)
- **Model Stability Finding:** qwen2.5:7b stable across all chunk sizes, gemma3:4b unstable >2500 chars

### Sprint 44: Relation Deduplication (TD-063)
- **Entity Name Normalization:** Normalize entity names in relations before matching
- **Type Synonym Resolution:** Hardcoded maps for relation types (e.g., "produces" → "creates")
- **Bidirectional Handling:** Symmetric relation types (married_to, partners) detect reverse relationships
- **Reduces False Positives:** Same entities referred by different names no longer duplicate
- **Code Location:** `src/components/graph_rag/relation_deduplicator.py`
- **Neo4j Integration:** Constraint enforcement on relation deduplication

### Sprint 45: LangGraph State Management
- **Unified AgentState Model:** Central state object passed between all agents
- **Phase-Based Workflow:** Explicit phases (retrieval → reranking → generation → streaming)
- **Better Error Handling:** State accumulates errors/warnings, visible in response metadata
- **Context Injection:** State carries conversation history, user preferences, intent
- **Parallel Agent Execution:** LangGraph Send/Receive for true parallel agent calls
- **Code Location:** `src/core/agent_state.py`, `src/agents/coordinator.py`

### Sprint 46: Request Cancellation & Cleanup
- **AbortController Support:** Frontend AbortController propagates to backend via headers
- **Graceful Stream Cancellation:** SSE streams stop mid-generation, cleanup handlers run
- **Resource Cleanup:** Redis connections, Neo4j transactions properly closed
- **Cancellation Propagation:** LangGraph agent loops check cancellation flag
- **User Experience:** "Stop generating" button in UI actually works reliably
- **Code Location:** `src/api/v1/chat.py`, `src/agents/coordinator.py`

### Sprint 47: Docling CUDA Acceleration
- **GPU-Accelerated OCR:** Native CUDA 13.0 support for GB10 (Blackwell, sm_121)
- **Layout Analysis:** CUDA-optimized document structure detection
- **Performance:** 3-5x faster PDF ingestion (420s → 90s baseline)
- **Integration:** Docling container launched separately with `--gpus all`
- **Accuracy:** 95% OCR accuracy vs 70% with CPU-only LlamaIndex
- **Code Location:** `docker/docling.Dockerfile`, `src/components/ingestion/docling_pipeline.py`

### Sprint 48: Real-Time Thinking Phase Events
- **13 Phase Types:** RETRIEVE_VECTOR, RETRIEVE_GRAPH, RETRIEVE_MEMORY, RERANK, INTENT_CLASSIFY, FUSION, GENERATION, STREAMING, MEMORY_CONSOLIDATION, etc.
- **PhaseEvent Models:** Timestamp, phase type, metadata (retrieved count, latency), reasoning text
- **SSE Event Streaming:** Real-time phase updates to frontend
- **Frontend Indicators:** "Thinking..." phases displayed as numbered steps
- **Redis Persistence:** Phase event history stored for session replay
- **Nemotron Default LLM:** Replaced Qwen3:8b with Alibaba Nemotron (better multilingual)
- **Code Location:** `src/core/phase_events.py`, `src/api/v1/chat.py`
- **Related:** TD-059 Reranking with Ollama local models

### Sprint 49: Dynamic UX & Semantic Deduplication
- **Embedding-Based Relation Dedup:** BGE-M3 embeddings for semantic similarity (replaces hardcoded lists)
- **Entity Dedup Migration:** Move from sentence-transformers → BGE-M3 system-wide
- **Sentence-Transformers Removal:** Complete elimination of duplicate embedding model dependency
- **Dynamic Model/Relationship Discovery:** No hardcoded entity type or relation type lists
- **Provenance Tracking:** `source_chunk_id` on all entities/relations for audit trail
- **Index Consistency Validation:** Background job checks for inconsistencies, reports issues
- **Historical Phase Events:** Display previous thinking steps in conversation history
- **Embedding Synergy:** BGE-M3 used for queries + dedup + memory + reranking (single model)
- **Code Location:** `src/components/graph_rag/semantic_deduplicator.py`, `src/core/provenance.py`

### Sprint 50: Token Streaming & TTFT
- **Token-by-Token Streaming:** LLM answer generation with streaming via SSE
- **Time-to-First-Token (TTFT) Tracking:** Measure latency until first token arrives
- **Streaming Cursor:** Visual feedback during incremental answer generation
- **Frontend Integration:** React component updates incrementally as tokens arrive
- **Code Location:** `src/api/v1/chat.py`, `frontend/src/components/StreamingAnswer.tsx`

### Sprint 51: Maximum Hybrid Search & CommunityDetector Fixes
- **4-Signal Hybrid Retrieval:** Vector + BM25 + LightRAG local + LightRAG global
- **Cross-Modal Fusion:** Align chunk rankings with entity-based retrieval via MENTIONED_IN
- **CommunityDetector Bug Fixes:**
  - Fixed `e.id` vs `entity_id` property mismatch
  - Fixed `RELATED_TO` vs `RELATES_TO` relationship typo
  - P0 blocker preventing LightRAG global mode queries
- **Phase Event System:** Granular phase emission throughout pipeline
- **Phase Display UI:** Real-time "thinking..." indicators with step numbers
- **Answer Metadata:** Source normalization, relevance thresholding, citation filtering
- **Intent Classification:** Factual, keyword, exploratory, summary query types
- **Maximum Retrieval Architecture:**
  - Embedding search (Qdrant + BGE-M3): semantic similarity
  - Keyword search (BM25): exact matches
  - Local graph search (LightRAG): entity relationships in chunks
  - Global graph search (LightRAG + Community): topic-level relationships
- **Cross-Modal Fusion Algorithm:**
  - Query LightRAG local + global retrieval in parallel
  - Extract entity names from LightRAG results (ordered by rank)
  - Find chunks mentioning those entities via Neo4j MENTIONED_IN
  - Boost chunk scores: `final_score = rrf_score + alpha * sum(entity_boosts)`
- **Code Location:**
  - `src/components/vector_search/hybrid_search.py` (4-way fusion)
  - `src/components/retrieval/cross_modal_fusion.py` (entity-chunk alignment)
  - `src/components/graph_rag/community_detector.py` (bug fixes)
  - `src/agents/phase_emitter.py` (phase tracking)
  - `src/agents/coordinator.py` (orchestration with phases)

---

## Current Retrieval Architecture (Sprint 51)

### Maximum Hybrid Search: 4-Signal Fusion

```
User Query
    │
    ▼
┌──────────────────────────────────────────────────────────────────┐
│       Intent Classifier (LLM + Rule-based)                       │
│    factual | keyword | exploratory | summary                     │
└──────────────────────┬─────────────────────────────────────────┘
                       │
      ┌────────────────┼────────────────┬────────────────┐
      ▼                ▼                ▼                ▼
 ┌─────────┐      ┌─────────┐      ┌──────────┐    ┌──────────┐
 │ Vector  │      │  BM25   │      │LightRAG │    │LightRAG │
 │ (Qdrant)│      │ Search  │      │  Local   │    │ Global   │
 │ BGE-M3  │      │(rank-   │      │(Entity→  │    │(Community│
 │         │      │ bm25)   │      │ Chunk)   │    │→ Chunk)  │
 └────┬────┘      └────┬────┘      └────┬─────┘    └────┬─────┘
      │                │                │               │
      └────────────────┴────────────────┴───────────────┘
                       │
                       ▼
      ┌──────────────────────────────────────┐
      │  Intent-Weighted RRF Fusion (k=60)   │
      │  score = Σ w_i(intent) * 1/(k+rank) │
      └──────────────────────────────────────┘
                       │
                       ▼
      ┌──────────────────────────────────────────┐
      │  Cross-Modal Fusion (MENTIONED_IN)       │
      │  final_score = rrf + alpha * entity_boost│
      └──────────────────────────────────────────┘
                       │
                       ▼
              Ranked Results (4-Signal)
```

**Intent Weight Profiles (Sprint 51):**

| Intent | Vector | BM25 | Local | Global |
|--------|--------|------|-------|--------|
| factual | 0.3 | 0.3 | 0.4 | 0.0 |
| keyword | 0.1 | 0.6 | 0.3 | 0.0 |
| exploratory | 0.2 | 0.1 | 0.2 | 0.5 |
| summary | 0.1 | 0.0 | 0.1 | 0.8 |

**Cross-Modal Fusion Mechanism (Sprint 51):**

1. **Parallel Retrieval:** Vector + BM25 + LightRAG local + global execute simultaneously
2. **RRF Combination:** Intent-weighted fusion of 4 signals
3. **Entity Extraction:** Extract entity names from LightRAG results (ranked by relevance)
4. **Chunk Mention Lookup:** Query Neo4j for MENTIONED_IN relationships
5. **Score Boosting:** Chunks mentioning highly-ranked entities receive bonus scores
6. **Final Ranking:** Re-rank chunks with combined RRF + entity boost scores

---

## Performance Evolution

| Metric | Sprint 2 | Sprint 21 | Sprint 37 | Sprint 42 | Sprint 51 |
|--------|----------|-----------|-----------|-----------|-----------|
| Vector Search | <200ms | <150ms | <100ms | <100ms | <100ms |
| Hybrid Query | <500ms | <400ms | <300ms | <350ms (4-way) | <400ms (with cross-modal) |
| TTFT (1st token) | N/A | N/A | N/A | N/A | <50ms |
| Full Answer | N/A | N/A | N/A | <1000ms | <1200ms (streamed) |
| Document Ingestion | 420s | 120s | 90s | 90s | 90s |
| Test Coverage | 212 | 400+ | 500+ | 600+ | 700+ |
| Retrieval Channels | 2 | 2 | 2 | 4 | 4 (with fusion) |

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
10. **Graphiti Memory Integration** - Episodic/semantic/entity layers, temporal queries
11. **Neo4j Community Edition** - Free, performant, same Cypher syntax
12. **Real-Time Phase Events** - Transparency into reasoning pipeline
13. **BGE-M3 Universal Embedding** - Single model for queries, dedup, memory, reranking
14. **Provenance Tracking** - `source_chunk_id` enables audit trails and debugging
15. **Cross-Modal Fusion** - Combining chunk + entity rankings improves precision
16. **Token Streaming** - TTFT <50ms, better UX for long answers
17. **Phase Granularity** - Showing intermediate thinking steps builds user trust

### Challenges Overcome
1. **Embedding Mismatch** - Solved with BGE-M3 system-wide
2. **Chunk Fragmentation** - Solved with section-aware chunking
3. **Entity Extraction Quality** - Solved with Pure LLM
4. **Cost Visibility** - Solved with SQLite cost tracking
5. **Multi-Hop Reasoning** - Solved with GraphRAG + context injection
6. **Shell Security** - Solved with Bubblewrap (not Docker)
7. **Entity Duplicates** - Solved with MultiCriteriaDeduplicator (ADR-044)
8. **Model Instability** - Solved with parallel extraction fallback
9. **Relation Type Synonyms** - Solved with type synonym resolution + normalization
10. **Request Cancellation** - Solved with AbortController + LangGraph loop checks
11. **Hardcoded Configuration** - Solved with dynamic discovery in Sprint 49
12. **LightRAG Community Queries** - Solved with CommunityDetector bug fixes (Sprint 51)
13. **Entity-Chunk Alignment** - Solved with cross-modal fusion via MENTIONED_IN (Sprint 51)
14. **Poor TTFT Experience** - Solved with token streaming + early response flush (Sprint 50)

---

## Current System Architecture (Sprint 51)

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

### Enterprise Features (Sprint 38-49)
- JWT authentication with protected routes
- Conversation search and share links
- GraphRAG multi-hop reasoning
- Bi-temporal entity versioning
- MCP integration and shell sandbox
- 4-Way Hybrid RRF with intent classification
- Multi-criteria entity deduplication (10.1% reduction)
- Comprehensive pipeline monitoring (12 new Prometheus metrics)
- Graphiti 3-layer memory system with temporal queries
- Multi-model parallel extraction (gemma3:4b + qwen2.5:7b)
- Neo4j Community Edition with GDS library
- Relation deduplication with type synonym resolution
- Real-time thinking phase events (13 phase types)
- Request cancellation with graceful cleanup
- Docling GPU acceleration (3-5x faster ingestion)
- Embedding-based semantic deduplication (BGE-M3)
- Provenance tracking with source_chunk_id
- Index consistency validation
- Dynamic model/relationship discovery

### Advanced Optimization (Sprint 50-51)
- Token-by-token LLM streaming with TTFT <50ms
- Time-to-First-Token tracking for answer generation
- Maximum Hybrid Search: 4-signal fusion (Vector + BM25 + Graph Local + Graph Global)
- Cross-Modal Fusion: Entity-chunk alignment via MENTIONED_IN relationships
- CommunityDetector bug fixes for LightRAG global mode support
- Phase event granularity: Separate phases for each retrieval channel
- Phase Display UI: Real-time thinking indicators with step numbers
- Answer metadata: Source normalization, relevance thresholding, citation filtering
- Streaming cursor: Visual feedback during incremental generation
