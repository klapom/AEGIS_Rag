# AEGIS RAG Technology Stack

**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Last Updated:** 2025-12-31 (Sprint 67-68 Planning)

---

## Executive Summary

**AEGIS RAG** is an enterprise-grade hybrid RAG system with a fully local-first architecture:

- **Zero Cloud Dependencies (Dev):** Ollama + self-hosted databases = $0/month
- **4-Way Hybrid Retrieval:** Vector + BM25 + Graph Local + Graph Global
- **Multi-Agent Orchestration:** LangGraph with 5+ specialized agents
- **3-Layer Memory:** Redis → Qdrant → Graphiti
- **GPU-Accelerated:** DGX Spark (NVIDIA Blackwell sm_121) + CUDA 13.0
- **Bi-Temporal Knowledge:** Entity versioning with time travel queries

---

## DGX Spark Hardware & Deployment

### Hardware Specifications

| Component | Specification |
|-----------|---------------|
| **GPU** | NVIDIA GB10 (Blackwell Architecture) |
| **CUDA Capability** | 12.1 → sm_121 / sm_121a |
| **Memory** | 128GB Unified (CPU + GPU shared) |
| **CPU** | 20 ARM Cortex Cores (aarch64) |
| **CUDA Version** | 13.0 |
| **Driver** | 580.95.05+ |
| **OS** | Ubuntu 24.04 LTS |

### Framework Compatibility (sm_121 Support)

| Framework | Status | Notes |
|-----------|--------|-------|
| **PyTorch cu130** | ✅ Works | Official wheels, ~10-12 sec/iter |
| **NGC Container** | ✅ Works | `nvcr.io/nvidia/pytorch:25.09-py3` |
| **llama.cpp** | ✅ Works | Native CUDA compilation |
| **Triton** | ⚠️ Build Required | Must build from source for sm_121a |
| **PyTorch cu128** | ❌ Fails | `nvrtc: invalid value for --gpu-architecture` |
| **TensorFlow** | ❌ Unsupported | Not supported on DGX Spark |
| **TensorRT** | ❌ Fails | No sm_121 support |
| **ONNX Runtime** | ⚠️ Manual Compile | Requires `CMAKE_CUDA_ARCHITECTURES=121` |

### Required Environment Variables

```bash
export TORCH_CUDA_ARCH_LIST="12.1a"
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas
export CUDACXX=/usr/local/cuda-13.0/bin/nvcc
export CUDA_HOME=/usr/local/cuda-13.0
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
```

### Flash Attention Workaround

```python
import torch
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(True)
```

**Reason:** Flash Attention kernels not yet compiled for sm_121. Memory-Efficient SDP provides acceptable performance.

### Performance Characteristics

- **cu130 Training:** ~10-12 sec/iteration
- **cu128 Training:** ~30+ sec/iteration (3x slower!)
- **llama.cpp (Qwen3-235B IQ3_M):** ~15 tok/s @ 107GB
- **Unified Memory:** 128GB total (~119GB usable after OS overhead)

### Common Issues & Solutions

#### 1. Wrong `nvcc` Version

**Problem:** `/usr/bin/nvcc` (CUDA 12.0) instead of `/usr/local/cuda-13.0/bin/nvcc`

**Solution:**
```bash
sudo apt remove nvidia-cuda-toolkit
# OR specify in cmake:
cmake -DCMAKE_CUDA_COMPILER=/usr/local/cuda-13.0/bin/nvcc ...
```

#### 2. Flash Attention Compilation Error

**Problem:** `kernel fmha_cutlassF_f16_aligned_64x128_rf_sm80 is for sm80-sm100, but was built for sm121`

**Solution:** Use Memory-Efficient SDP backend (see above).

#### 3. PEP 668 "externally-managed-environment"

**Solution:**
```bash
pip install --break-system-packages <package>
```

---

## Core Technology Stack

### Backend Stack

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Python | 3.12.7 | Runtime |
| **Package Manager** | Poetry | Latest | Dependency Management |
| **Web Framework** | FastAPI | 0.115+ | REST API |
| **ASGI Server** | Uvicorn | 0.30+ | Async HTTP Server |
| **Orchestration** | LangGraph | 0.6.10 | Multi-Agent System |
| **LLM Framework** | LangChain Core | 1.0.0 | LLM Abstractions |
| **Vector DB** | Qdrant | 1.11.0 | Semantic Search |
| **Graph DB** | Neo4j | 5.24 Community | Knowledge Graph |
| **GraphRAG** | LightRAG-HKU | 1.4.9 | Entity/Topic Retrieval |
| **Temporal Memory** | Graphiti-Core | 0.3.0 | Bi-Temporal Memory |
| **Cache** | Redis | 7.x | Short-Term Memory |
| **Data Ingestion** | Docling CUDA | Latest | GPU OCR (95% accuracy) |
| **Fallback Ingestion** | LlamaIndex Core | 0.14.3 | 300+ Connectors |

### Frontend Stack

| Package | Version | Purpose |
|---------|---------|---------|
| **Framework** | React | 19 | UI Framework |
| **Language** | TypeScript | ~5.9.0 | Type Safety |
| **Build Tool** | Vite | 7.1.12 | Fast Dev Server |
| **Styling** | Tailwind CSS | 4.1.0 | Utility-First CSS |
| **Routing** | React Router | 7.9.2 | Client-Side Routing |
| **State** | Zustand + Context API | 5.0.3 | Global + Local State |
| **Markdown** | React Markdown | 9.0.2 | Markdown Rendering |
| **Icons** | Lucide Icons | Latest | Icon Library |
| **Testing** | Playwright | Latest | E2E Tests (111 tests) |

### Development Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **Linter** | Ruff | 0.14+ | Fast Python Linter (10-100x faster than Flake8) |
| **Formatter** | Black | 24.8+ | Opinionated Code Formatter |
| **Type Checker** | MyPy | 1.11+ | Static Type Analysis |
| **Security** | Bandit | 1.7.9 | Security Vulnerability Scanner |
| **Testing** | Pytest | 8.0+ | Unit/Integration Testing |
| **Coverage** | Pytest-Cov | 5.0+ | Code Coverage (>80% target) |

---

## LLM Configuration & Routing

### AegisLLMProxy Multi-Cloud Routing (ADR-033)

**Architecture:** Local-First with Cloud Fallback

| Priority | Provider | Models | Cost | Use Case |
|----------|----------|--------|------|----------|
| **1** | **Ollama (DGX Spark)** | llama3.2, gemma-3, BGE-M3 | $0 | Primary (Dev + Prod) |
| **2** | **Alibaba Cloud DashScope** | qwen-turbo/plus/max, qwen3-vl | $0-120/mo | Cloud Fallback |
| **3** | **OpenAI** | gpt-4o, gpt-4o-mini | Optional | Optional Fallback |

### Model Selection by Task

| Task | Model | Provider | Size | Purpose |
|------|-------|----------|------|---------|
| **Query Understanding** | llama3.2:3b | Ollama | 2GB | Fast intent classification |
| **Answer Generation** | llama3.2:8b | Ollama | 4.7GB | Quality responses |
| **Entity Extraction** | gemma-3-4b-it-Q8_0 | Ollama | 2.7GB | Pure LLM extraction (ADR-026) |
| **Complex Reasoning** | qwen2.5:7b | Ollama | 4.7GB | Multi-hop queries |
| **Embeddings** | BGE-M3 (1024-dim) | Ollama | 2.3GB | Universal semantic embeddings |
| **Reranking** | bge-reranker-v2-m3 | Ollama | - | Cross-encoder reranking |
| **VLM (Images)** | qwen3-vl-30b-a3b | DashScope | - | Image descriptions (cloud) |
| **VLM (Local Alt)** | llava:7b-v1.6-mistral-q2_K | Ollama | 4.7GB | Local image descriptions |

**Total Model Storage:** ~23GB (all Ollama models)
**Typical VRAM Usage:** 8-12GB (2-3 models loaded simultaneously)

### Ollama Rationale (ADR-002)

**Why Ollama:**
- **Zero Cost:** $0 API fees (saves $18K-24K/year vs Azure OpenAI)
- **Offline Capable:** Air-gapped deployment for sensitive data
- **DSGVO Compliance:** 100% data residency (no data leaves local network)
- **No Vendor Lock-in:** Switch models freely

**Alternatives Rejected:**
- **Azure OpenAI:** $200-500/month dev, $1000+/month production. Requires internet, vendor lock-in, DSGVO challenges.
- **Anthropic Claude:** Similar costs, no EU hosting, smaller ecosystem.
- **OpenAI API (Direct):** Not DSGVO-compliant (US data), no SLA.

**Trade-offs:**
- ⚠️ Lower quality than GPT-4o for very complex tasks (acceptable trade-off)
- ⚠️ Requires GPU (12GB VRAM recommended)
- ⚠️ Manual model updates
- ✅ No API rate limits, unlimited usage
- ✅ Privacy by design

### Cost Tracking

**Component:** `src/components/llm_proxy/cost_tracker.py` (389 LOC)

**Implementation:**
- SQLite database: `data/cost_tracking.db`
- Per-request tracking: timestamp, provider, model, tokens, cost, latency
- Monthly aggregations by provider
- CSV/JSON export for analysis

**Monthly Budgets:**
- Alibaba Cloud: $10-120/month (configurable)
- OpenAI: Optional (pay-per-use)
- Ollama: $0 (local)

---

## Dependency Rationale

### Orchestration: LangGraph 0.6.10 (ADR-001)

**Why LangGraph:**
- **Explicit Control:** Graph-based workflow with conditional routing, cycles, parallel execution (Send API)
- **Production Features:** LangSmith tracing, durable checkpoints, state persistence, retry logic
- **Flexibility:** Complex multi-agent workflows with Pydantic-typed state
- **Ecosystem:** Native integration with LangChain, Vector DBs, Tools
- **Maturity:** Enterprise-proven (Klarna, Uber, Replit)

**Alternatives Rejected:**
- **CrewAI:** Too simple (limited workflow control), no graph visualization. 5.76x faster but lacks production features.
- **AutoGen (Microsoft):** Event-driven requires more infrastructure, conversational paradigm less suited for deterministic RAG.
- **LlamaIndex Workflows:** Newer API (less mature), less ecosystem integration.

**Trade-offs:**
- ⚠️ Steep learning curve
- ⚠️ More boilerplate code
- ✅ Better debuggability (LangGraph Studio)
- ✅ Production-ready state management

---

### Vector DB: Qdrant 1.11.0 (ADR-004)

**Why Qdrant:**
- **Best-in-Class Performance:** 3ms latency @ 1M embeddings, sub-10ms at production scale
- **Compression:** 24x via asymmetric quantization (Scalar + Product Quantization)
- **Self-Hosting:** No vendor lock-in, full infrastructure control
- **Advanced Features:** Metadata filtering, RBAC, multi-tenancy, distributed replication

**Alternatives Rejected:**
- **Pinecone:** Vendor lock-in (no self-hosting), higher costs at scale.
- **Weaviate:** Slower performance, higher memory footprint, less mature quantization.
- **ChromaDB:** Best for prototyping, but not production-scale (no distributed replication).

**Trade-offs:**
- ⚠️ No managed service (if self-hosting)
- ⚠️ Requires tuning for optimal performance
- ✅ Open source (Apache 2.0)
- ✅ Active community (21K+ GitHub stars)

**Configuration:**
- Collection: `documents_v1` (1024-dim BGE-M3)
- Quantization: Scalar (0.99 quantile)
- HNSW Index: M=16, ef_construct=100

---

### Graph DB: Neo4j 5.24 Community (ADR-005)

**Why Neo4j:**
- **Industry Standard:** Most mature graph database, Cypher query language
- **LightRAG Backend:** Knowledge graph storage (entities, relationships, communities)
- **Graphiti Backend:** Bi-temporal episodic memory (valid-time + transaction-time)
- **Performance:** Optimized for traversal queries, APOC procedures for graph algorithms

**Alternatives Rejected:**
- **ArangoDB:** Multi-model but weaker ecosystem for RAG use cases
- **Neo4j Aura (Cloud):** Vendor lock-in, costs vs self-hosting
- **TigerGraph:** Better for massive graphs (billions of edges) but overkill for RAG

**Configuration:**
- Server: Neo4j 5.24-community (Docker)
- Memory: 512MB heap initial, 2GB max
- APOC Plugins: Core procedures for graph analytics

---

### GraphRAG: LightRAG-HKU 1.4.9 (ADR-005)

**Why LightRAG:**
- **Cost-Efficient:** Lower LLM token usage than Microsoft GraphRAG
- **Incremental Updates:** No full re-index needed (vs Microsoft GraphRAG static approach)
- **Dual-Level Retrieval:** Low-level (entity matching) + High-level (topic/community matching)
- **Developer Experience:** Built-in web UI, API server, Docker-ready
- **Benchmarks:** Comparable accuracy to Microsoft GraphRAG at ~1/10th cost

**Alternatives Rejected:**
- **Microsoft GraphRAG:** Mature (23.8K stars), excellent docs, but extremely high indexing costs, static graph structure, no temporal awareness.
- **LlamaIndex PropertyGraph:** Flexible schema but less optimized than dedicated GraphRAG systems.
- **No GraphRAG (Vector + Graphiti only):** Simpler but no community detection, no global search capability.

**Trade-offs:**
- ⚠️ Younger project (less mature)
- ⚠️ Smaller community
- ✅ Abstraction layer allows swap to Microsoft GraphRAG if needed
- ✅ Active development

**Model Switch (Sprint 11):**
- **Sprint 5-10:** qwen3:0.6b (ultra-lightweight)
- **Sprint 11+:** llama3.2:3b (better structured output, +20% accuracy)

---

### Temporal Memory: Graphiti-Core 0.3.0 (ADR-006)

**Why Graphiti:**
- **Unique Capability:** Bi-temporal graph storage (valid-time + transaction-time)
- **Temporal Queries:** "What did system know on date X?" (point-in-time queries)
- **Knowledge Evolution:** Track how facts change over time
- **Relationship Tracking:** Entity connections evolve with temporal context
- **No Competitors:** Only library offering bi-temporal memory for LLM systems

**Alternatives Rejected:**
- **LangChain Memory:** Simpler but no temporal awareness, no relationship tracking
- **Custom Neo4j Solution:** Would require significant development effort
- **SQL-based Memory:** Poor for graph traversal, no semantic search

**Trade-offs:**
- ⚠️ Steep learning curve (bi-temporal concepts complex)
- ⚠️ Newer library (less battle-tested)
- ⚠️ API breaking changes (Sprint 12: constructor signature changed in 0.3.0)
- ✅ Unique temporal capabilities justify complexity
- ✅ Built on Neo4j (proven graph backend)

---

### Embeddings: BGE-M3 (BAAI/bge-m3) - 1024-dim (ADR-024, ADR-041)

**Status:** ✅ **EXPANDED** (Sprint 49 - Unified Embedding Strategy)

**Why BGE-M3:**
- **Universal Model:** Single embedding model for all semantic tasks
- **High Dimensionality:** 1024-dim vs 384-dim (superior semantic separation)
- **Multilingual Support:** 100+ languages with consistent embedding space
- **Ollama Integration:** Model served via Ollama (no Python transformers library dependency)
- **Consistency:** Same embedding space for queries, documents, entity dedup, relation clustering

**Sprint 49 Expanded Usage:**
- **Query Embeddings:** Dense vector representations for similarity search
- **Document Chunk Embeddings:** Index chunk content for hybrid search
- **Entity Deduplication:** Semantic similarity comparison (NEW - Sprint 49, 0.85 threshold)
- **Relation Type Clustering:** Group relation types by semantic similarity (NEW - Sprint 49, 0.88 threshold)

**Alternatives Rejected (Sprint 49):**
- **sentence-transformers:** Duplicate functionality for 2GB Docker bloat (REMOVED)
- **OpenAI Embeddings:** Cloud dependency, DSGVO concerns, cost
- **Local transformers:** Duplicate model management (Ollama already serves BGE-M3)

**Trade-offs:**
- ⚠️ CPU embeddings slightly slower for dedup (~100ms) vs GPU reranking (10ms)
- ⚠️ Dependency on Ollama model availability
- ✅ Unified embedding model (consistency across all tasks)
- ✅ -2GB Docker image savings (removed sentence-transformers)
- ✅ 1024-dim higher quality than 384-dim alternatives
- ✅ Multilingual support built-in

**Performance:**
- **Query Embeddings:** ~30-50ms per query (GPU-accelerated)
- **Batch Document Embeddings:** ~10-20ms per chunk (vectorized)
- **Dedup Comparisons:** ~50-100ms for entity/relation clustering (CPU-acceptable latency)

---

### Keyword Search: Rank-BM25 0.2.2 (ADR-009)

**Why BM25:**
- **Gold Standard:** Best keyword-based retrieval algorithm
- **Complements Vector Search:** Catches exact matches vector search misses
- **Simple API:** No external dependencies
- **Pickle Persistence:** Index storage in filesystem

**Alternatives Rejected:**
- **Elasticsearch:** Overkill (requires separate service), better for full-text search at massive scale.
- **Whoosh:** Pure Python but slower, less active development
- **Tantivy (Rust):** Faster but requires Rust compilation, higher complexity

**Configuration:**
- Tokenization: Custom (lowercase, split, stemming)
- Index: Pickle file (`data/bm25_index.pkl`)
- Update: Re-fit on document ingestion

---

### Clustering: Scikit-learn 1.6.0 (ADR-041 - Expanded in Sprint 49)

**Status:** ✅ **EXPANDED** (Sprint 49)

**Why Scikit-learn:**
- **Hierarchical Clustering:** Agglomerative clustering for entity and relation deduplication
- **Cosine Similarity:** Efficient similarity computations for dedup threshold matching
- **Distance Metrics:** pdist/squareform for pairwise distance computation
- **Industry Standard:** Well-maintained, excellent documentation, optimized C backends

**Sprint 49 New Usages:**
- **Entity Deduplication:** `AgglomerativeClustering` with BGE-M3 embeddings (linkage='average', distance_threshold=0.15)
- **Relation Type Clustering:** Group relation types by semantic similarity (linkage='ward', distance_threshold=0.12)
- **Cosine Similarity Computation:** Compare embedding vectors for threshold-based matching

**Alternatives Rejected (Sprint 49):**
- **SciPy Linkage:** Lower-level API, requires manual dendrogram construction
- **DBSCAN:** Harder to tune (eps/min_samples), doesn't guarantee full coverage
- **K-Means:** Requires pre-specifying cluster count (dynamic thresholding better for dedup)

**Trade-offs:**
- ⚠️ O(n²) complexity (acceptable for <1000 entities per document)
- ⚠️ Requires dense embedding matrix in memory
- ✅ Industry-standard, well-maintained library
- ✅ Excellent documentation
- ✅ Optimized C backends for performance
- ✅ Integrates seamlessly with NumPy/SciPy ecosystem

**Performance:**
- **Hierarchical Clustering:** O(n²) complexity
- **Cosine Similarity:** ~0.1-0.5ms for 1K embeddings (vectorized NumPy)
- **Typical Runtime:** 10-50ms for 100-500 entities (acceptable for ingestion)
- **Memory:** ~10MB for 10K embeddings (1024-dim × float32)

---

### Document Ingestion: Docling CUDA Container (ADR-027)

**Why Docling:**
- **Superior OCR Quality:** 95% accuracy vs 70% with LlamaIndex
- **Table Structure Preservation:** 92% detection rate vs 60%
- **GPU Acceleration:** 3.5x faster (420s → 120s per document)
- **Container Isolation:** Prevents GPU memory leaks, manages VRAM
- **Professional Tool:** IBM Research project, enterprise-grade

**Alternatives Rejected:**
- **LlamaIndex OCR:** Lower quality (70%), slower, CPU-only
- **Tesseract:** Open-source but lower accuracy, no table understanding
- **Azure Document Intelligence:** Cloud dependency, costs ($1.50/1000 pages)

**Container Management:**
- Started on-demand (first document upload)
- Auto-stopped after parsing (frees 6GB VRAM)
- Health checks ensure container readiness
- Managed via DoclingContainerClient

**LlamaIndex Deprecation (ADR-028):**
- **Sprint 21 Decision:** LlamaIndex moved from **primary ingestion** to **fallback + connector library**
- **Retained for:** 300+ connector ecosystem (APIs, Cloud, Databases)
- **PDF/DOCX:** Use Docling CUDA Container (primary)
- **APIs/Cloud:** Use LlamaIndex connectors (Notion, Google Drive, Slack)

---

### Web Framework: FastAPI 0.115+ (ADR-008)

**Why FastAPI:**
- **Performance:** Fastest Python framework (Starlette/Uvicorn async foundation)
- **Auto Documentation:** OpenAPI/Swagger UI generated automatically
- **Type Safety:** Pydantic v2 integration for request/response validation
- **Async Native:** Native async/await for I/O-bound operations (LLM calls, DB queries)
- **Ecosystem:** Best integration with AI/ML libraries (LangChain, LlamaIndex)

**Alternatives Rejected:**
- **Django:** Overkill for API-only backend, slower than FastAPI, heavier (ORM, admin panel not needed).
- **Flask:** Simpler but no native async support, manual validation, no auto docs.
- **Node.js/Express:** Single language (JS frontend + backend) but weaker AI/ML ecosystem.

**Trade-offs:**
- ⚠️ Younger than Django/Flask (less mature)
- ⚠️ Less "batteries included" (need to add middleware)
- ✅ Best performance/features for AI/ML APIs
- ✅ Auto-generated interactive docs (huge DX win)

---

### Section-Aware Chunking (ADR-039 - Sprint 32)

**Architecture:** Pure Python + BGE-M3 Tokenizer

**Why Section-Aware:**
- **Context Preservation:** Chunks respect document structure (headings, paragraphs)
- **Adaptive Sizing:** 800-1800 tokens (optimized for BGE-M3's 8192 context window)
- **Neo4j Section Nodes:** Hierarchical structure in graph
- **Multi-Section Metadata:** Qdrant chunks track parent sections

**No New Dependencies:**
- Section extraction: Native Python string parsing
- Adaptive merging: Existing BGE-M3 tokenizer
- Neo4j Section nodes: Existing Neo4j driver (5.14.0)
- Multi-section metadata: Existing Qdrant client (1.11.0)

---

### RELATES_TO Semantic Relationships (ADR-040 - Sprint 34)

**Why RELATES_TO:**
- **Semantic Relationships:** LLM-extracted semantic connections between entities
- **Pure LLM Extraction:** Uses existing gemma-3-4b-it-Q8_0 (no new dependencies)
- **Graph Visualization:** Enhanced edge rendering with react-force-graph-2d
- **Admin UI:** Graph analytics with E2E tests (Playwright)

**No New Dependencies:**
- RELATES_TO extraction: Existing LLM proxy (gemma-3-4b-it-Q8_0)
- Graph visualization: Existing react-force-graph-2d ^1.29.0
- Edge rendering: Native D3-style force simulation

---

## 4-Way Hybrid Search Architecture (Sprint 51 - Maximum Hybrid)

### Retrieval Signals

| Signal | Component | Purpose | Speed |
|--------|-----------|---------|-------|
| **Vector** | Qdrant + BGE-M3 | Semantic similarity search | <100ms |
| **Keyword** | BM25 (rank-bm25) | Exact phrase matching | <30ms |
| **Local Graph** | LightRAG local mode | Entity relationships in chunks | <150ms |
| **Global Graph** | LightRAG global + Communities | Topic-level relationships | <150ms |

### Fusion Pipeline

```
4 Parallel Searches → Intent-Weighted RRF → Cross-Modal Fusion → Final Ranking
```

**Intent-Weighted RRF (Reciprocal Rank Fusion, k=60):**
- **Factual queries:** 0.3 vector, 0.3 BM25, 0.4 local, 0.0 global
- **Keyword queries:** 0.1 vector, 0.6 BM25, 0.3 local, 0.0 global
- **Exploratory:** 0.2 vector, 0.1 BM25, 0.2 local, 0.5 global
- **Summary:** 0.1 vector, 0.0 BM25, 0.1 local, 0.8 global

**Cross-Modal Fusion:**
1. Extract entity names from LightRAG results (ranked by relevance)
2. Query Neo4j for MENTIONED_IN relationships (entities → chunks)
3. Boost chunk scores: `final_score = rrf_score + alpha * sum(entity_boosts)`
4. Re-rank final results

### CommunityDetector Bug Fixes (Sprint 51)

Fixed critical issues blocking LightRAG global queries:
1. Entity property: `e.id` → `entity_id` (Neo4j property names)
2. Relationship type: `RELATED_TO` → `RELATES_TO` (typo fix)

---

## 3-Layer Memory Architecture

| Layer | Storage | Latency | Purpose | Retention |
|-------|---------|---------|---------|-----------|
| **1** | Redis | <10ms | Session state, working memory | 1-24 hours (TTL) |
| **2** | Qdrant | <50ms | Semantic long-term memory | Permanent |
| **3** | Graphiti + Neo4j | <200ms | Episodic, bi-temporal relationships | Temporal (versioned) |

**Memory Consolidation (APScheduler 3.10.0):**
- `consolidate_redis_to_qdrant`: Every 1 hour
- `consolidate_conversations_to_graphiti`: Every 1 hour
- `cleanup_old_sessions`: Every 24 hours

---

## Multi-Agent System (LangGraph)

### Agents

| Agent | Responsibility | Tools |
|-------|----------------|-------|
| **Coordinator** | Query routing, orchestration | Intent classification |
| **Vector Search** | Qdrant hybrid search (Vector + BM25) | Qdrant, BM25 |
| **Graph Query** | Neo4j + LightRAG (entities, topics) | Neo4j, LightRAG |
| **Memory** | Graphiti retrieval, consolidation | Graphiti, Redis |
| **Action** | Tool execution (Bash, Python) | MCP Tools (Sprint 59) |
| **Research** | Multi-step agentic search | Planner, Searcher, Synthesizer |

### Tool Framework (Sprint 59)

**Decorator-Based Registration:**
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

**Built-in Tools:**
- **Bash Tool:** Command execution with blacklist validation, timeout enforcement
- **Python Tool:** AST validation, restricted globals, blocked modules
- **Docker Sandbox:** Network isolation, read-only filesystem, resource limits (memory, CPU)

**Security Layers (5-Layer Defense):**
1. Input Validation (Bash blacklist, Python AST)
2. Restricted Environment (sanitized env vars, restricted globals)
3. Docker Sandbox (network isolation, read-only filesystem)
4. Timeout Enforcement (max 300s, process killing)
5. Result Truncation (prevent memory exhaustion)

---

## Database Configuration

### Qdrant

| Setting | Value |
|---------|-------|
| Host | localhost |
| Port | 6333 (HTTP), 6334 (gRPC) |
| Collection | documents_v1 |
| Vector Size | 1024 (BGE-M3) |
| Distance | Cosine |
| Quantization | Scalar (0.99 quantile) |

### Neo4j

| Setting | Value |
|---------|-------|
| URI | bolt://localhost:7687 |
| Database | neo4j |
| Edition | Community 5.24 |
| Max Pool Size | 50 |
| Heap Max | 2G |
| Page Cache | 1G |

### Redis

| Setting | Value |
|---------|-------|
| Host | localhost |
| Port | 6379 |
| Persistence | AOF (appendonly) |

---

## Infrastructure

### Docker Services

| Service | Image |
|---------|-------|
| API | aegis-rag-api:dev |
| Qdrant | qdrant/qdrant:v1.11.0 |
| Neo4j | neo4j:5.24-community |
| Redis | redis:7-alpine |
| Docling | ds4sd/docling:latest |
| Prometheus | prom/prometheus:latest |
| Grafana | grafana/grafana:latest |

### Monitoring Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| **Metrics** | Prometheus | Request rate, latency, errors |
| **Visualization** | Grafana | Dashboards, alerting |
| **Logs** | Loki | Log aggregation |
| **Traces** | Jaeger | Distributed tracing |
| **LLM Tracing** | LangSmith | LangGraph workflow debugging |

### Metrics Tracked (Prometheus-Client 0.21.0)

- `http_requests_total` (counter)
- `http_request_duration_seconds` (histogram)
- `llm_tokens_generated_total` (counter)
- `vector_search_latency_seconds` (histogram)

---

## Security

| Feature | Implementation | Technology |
|---------|----------------|------------|
| **Hashing** | SHA-256 | Chunk IDs |
| **Input Validation** | Pydantic v2 | Request/Response validation |
| **Rate Limiting** | slowapi | 10/min search, 5/hour ingest |
| **JWT Auth** | python-jose | JWT token handling (HS256) |
| **Password Hashing** | passlib | Bcrypt (12 rounds) |
| **Content Filtering** | Custom middleware | - |
| **Secrets** | pydantic-settings | Environment variables |

---

## Performance Targets

| Metric | Target (p95) | Achieved |
|--------|--------------|----------|
| Simple Query (Vector) | <200ms | ✅ 180ms |
| Hybrid Query (Vector+Graph) | <500ms | ✅ 450ms |
| Complex Multi-Hop | <1000ms | ✅ 980ms |
| Sustained Load | 50 QPS | ✅ Tested |
| Document Ingestion (per page) | <2s | ✅ 1.8s (GPU) |
| Embedding (batch 32) | <500ms | ✅ 420ms |

---

## Cost Estimation (Monthly)

| Component | Dev Cost | Production Cost | Notes |
|-----------|----------|-----------------|-------|
| **Ollama (Local)** | $0 | $0 | DGX Spark |
| **DGX Spark** | Hardware | Hardware | Primary runtime |
| **Alibaba Cloud** | $0 | $0-120 | Budget-controlled |
| **OpenAI** | $0 | Optional | Pay-per-use |
| **Self-hosted DBs** | $0 | $0 | Docker containers |
| **Total** | **$0** | **$0-150** | Fully local dev, cloud fallback prod |

**Cost Savings vs Cloud-Only:**
- Azure OpenAI: $200-500/month dev, $1000+/month production
- **Savings:** $18K-24K/year

---

## Version Constraints Summary

### Strict Pins (~)
- `qdrant-client ~1.11.0` - Server compatibility critical

### Range Constraints (>=X,<Y)
- `ollama >=0.6.0,<1.0.0` - langchain-ollama 1.0.0 requirement
- `tenacity >=8.1.0,<9.0.0` - graphiti-core compatibility

### Flexible (^)
- Most libraries use caret (^) for SemVer compatibility
- Allows minor/patch updates (e.g., `^2.9.0` → `2.9.x`, `2.10.x`)

---

## Dependency Health

**Total Dependencies:** 61 (production + dev) - **1 REMOVED** (sentence-transformers in Sprint 49)

**Dependency Health:**
- All actively maintained
- No critical CVEs
- Regular security scans via Bandit

**Sprint 49 Cleanup:**
- ✅ Sentence-transformers removed (-2GB Docker)
- ✅ BGE-M3 expanded to universal embedding model
- ✅ Ollama-first strategy enforced (all transformers managed by Ollama)
- ✅ Docker image size reduced by ~2GB

---

## Sprint 67-68 Additions

### New Dependencies (Sprint 67)

**Secure Shell Sandbox:**
- `deepagents >=0.2.0` - LangChain-native agent harness with SandboxBackendProtocol
- `bubblewrap` (system package) - Linux container isolation for code execution

**Adaptation Framework:**
- `setfit >=1.0.0` - Sentence Transformers fine-tuning for intent classification
- (Reuses existing: LangGraph, Qwen2.5:7b via Ollama)

**Performance Monitoring:**
- (Enhanced Prometheus metrics - no new dependencies)

### Performance Targets (Sprint 68)

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Query Latency P95** | 500ms | 350ms | -30% |
| **Section Extraction** | 9-15min | 2min | 8x faster |
| **E2E Test Pass Rate** | 57% (337/594) | 100% (594/594) | +43% |
| **Memory Usage** | 8.6GB | 6.0GB | -30% |
| **Throughput** | 40 QPS | 50 QPS | +25% |

### Architecture Enhancements (Sprint 67-68)

**Secure Code Execution:**
- BubblewrapSandboxBackend with syscall filtering
- Multi-language support (Bash + Python)
- Workspace isolation and network restrictions

**Tool-Level Adaptation:**
- Unified Trace & Telemetry (RAG pipeline monitoring)
- Eval Harness (automated quality gates)
- Adaptive Reranker v1 (intent-aware reranking)
- Query Rewriter v1 (query expansion)

**Intent Classification:**
- C-LARA approach: LLM data generation (Qwen2.5:7b) + SetFit fine-tuning
- Target accuracy: 60% → 85-92%

**Section Features:**
- Section Community Detection (Louvain/Leiden algorithms)
- 15 production Cypher queries for section-based retrieval
- Parallelized section extraction (ThreadPoolExecutor)

---

**Document Consolidated:** Sprint 60 Feature 60.1
**Sprint 67-68 Updates:** 2025-12-31
**Sources:** TECH_STACK.md, DEPENDENCY_RATIONALE.md, DGX_SPARK_SM121_REFERENCE.md, SPRINT_67_PLAN.md, SPRINT_68_PLAN.md
**Maintainer:** Claude Code with Human Review
