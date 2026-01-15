# AEGIS RAG Technology Stack

**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Last Updated:** 2026-01-15 (Sprint 93: Tool Composition, LangGraph 1.0, Playwright Integration)

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
| **Orchestration** | LangGraph | 1.0.6 | Multi-Agent System (Sprint 93: 1.0 GA with ToolNode, InjectedState, Durable Execution) |
| **LLM Framework** | LangChain Core | 1.1.2 | LLM Abstractions |
| **Vector DB** | Qdrant | 1.11.0 | Semantic Search |
| **Graph DB** | Neo4j | 5.24 Community | Knowledge Graph |
| **GraphRAG** | LightRAG-HKU | 1.4.9 | Entity/Topic Retrieval |
| **Temporal Memory** | Graphiti-Core | 0.3.0 | Bi-Temporal Memory |
| **Cache** | Redis | 7.x | Short-Term Memory |
| **Data Ingestion** | Docling CUDA | Latest | GPU OCR (95% accuracy) |
| **Fallback Ingestion** | LlamaIndex Core | 0.14.3 | 300+ Connectors |
| **Multi-language NER** | SpaCy | 3.7.0 | DE/EN/FR/ES Entity Extraction (Sprint 83) |
| **NER Models** | SpaCy Transformers | 1.3.0 | Transformer-based NER (Sprint 83) |
| **GPU Monitoring** | pynvml | 11.5.0 | VRAM Tracking (Sprint 83) |
| **Retry Logic** | Tenacity | 8.0.0 | Exponential Backoff (Sprint 83) |

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
| **Testing** | Playwright | 1.57.0 | E2E Tests (111 tests, Sprint 93: Browser Tool Integration) |

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
| **1** | **Ollama (DGX Spark)** | nemotron-nano  gpt-oss:20 | $0 | Primary (Dev + Prod) |
| **2** | **Alibaba Cloud DashScope** | qwen-turbo/plus/max, qwen3-vl | $0-120/mo | Cloud Fallback |
| **3** | **OpenAI** | gpt-4o, gpt-4o-mini | Optional | Optional Fallback |

### Model Selection by Task

| Task | Model | Provider | Size | Purpose |
|------|-------|----------|------|---------|
| **Query Understanding** | nemotron-nano | Ollama | 2,5GB | Fast intent classification |
| **Answer Generation** | nemotron-nano | Ollama | 2,5GB | Quality responses |
| **Entity Extraction (Rank 1)** | Nemotron3 Nano 30/3a | Ollama | 2.5GB | Primary ER-Extraction (Sprint 83) |
| **Entity Extraction (Rank 2)** | gpt-oss:20b | Ollama | 12GB | Fallback ER-Extraction (Sprint 83) |
| **Entity Extraction (Rank 3)** | SpaCy NER + gpt-oss:20b | SpaCy + Ollama | - | Hybrid NER (DE/EN/FR/ES) + LLM relations (Sprint 83) |
| **Complex Reasoning** | 2,5 | Ollama | 4.7GB | Multi-hop queries |
| **Embeddings** | BGE-M3 (1024-dim) | flag-embedding | 2.3GB | Universal semantic embeddings |
| **Reranking** | bge-reranker-v2-m3 | flag-embedding | - | Cross-encoder reranking |
| **VLM (Images)** | qwen3-vl-30b-a3b | DashScope | - | Image descriptions (cloud) |

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

### Embeddings: BGE-M3 (BAAI/bge-m3) - 1024-dim Dense + Sparse (ADR-024, ADR-041)

**Status:** ✅ **NATIVE HYBRID SEARCH** (Sprint 87 - FlagEmbedding Integration)

**Why BGE-M3:**
- **Unified Embedding Model:** Single model for semantic + keyword search
- **High Dimensionality:** 1024-dim dense vectors (superior semantic separation)
- **Sparse Lexical Vectors:** Learned token weights (replaces BM25 - ADR-041 Sprint 87)
- **Multilingual Support:** 100+ languages with consistent embedding space
- **Native Python Integration:** FlagEmbedding library (1.2.0+) for local dense + sparse embeddings

**Sprint 87 Hybrid Search Evolution:**
- **Dense Vectors:** 1024-dim semantic embeddings (Qdrant collection: `documents_v1`)
- **Sparse Vectors:** Learned lexical weights (BM25 replacement - better quality)
- **Qdrant Multi-Vector:** Server-side RRF fusion (Reciprocal Rank Fusion, k=60)
- **Performance:** Async embedding service with FlagEmbedding.SparseEmbedding
- **BM25 Deprecation:** Replaced by BGE-M3 sparse vectors (ADR-041, Sprint 87)

**FlagEmbedding 1.2.0+ Features:**
- `SparseEmbedding`: Learned token weights for keyword search
- `DenseEmbedding`: Dense vectors for semantic similarity
- `Reranker`: Cross-encoder reranking (bge-reranker-v2-m3)
- Unified API: Single library for all embedding tasks

**Implementation (Sprint 87):**
```python
from flagembedding import FlagEmbedding

# Dense + Sparse embeddings in one call
model = FlagEmbedding(
    model_name="BAAI/bge-m3",
    use_fp16=True,  # DGX Spark optimization
    batch_size=32
)

# Returns both dense (1024D) and sparse (lexical weights)
results = model.encode_queries(
    queries,
    return_dense=True,
    return_sparse=True  # Learned weights
)
```

**Qdrant Collection Schema (Sprint 87):**
```yaml
collection: documents_v1
vector_size: 1024
distance: Cosine
payloads:
  - name: text
    type: text
  - name: metadata
    type: object
vectors:
  - name: dense
    size: 1024
    distance: Cosine
  - name: sparse
    sparse_vector_type: bm25  # Learned weights
```

**Server-Side RRF (Sprint 87):**
Qdrant performs Reciprocal Rank Fusion on search results:
- Dense search: Top-K by cosine similarity
- Sparse search: Top-K by learned token weights
- Fusion: RRF(k=60) combines both rankings
- Result: Superior recall vs single-modal search

**Trade-offs:**
- ⚠️ Sparse indexing overhead (~2x more memory than dense alone)
- ⚠️ RRF computation adds ~10-20ms latency
- ✅ Replaces BM25 with superior semantic quality
- ✅ No external indexing service (all in Qdrant)
- ✅ Unified embedding pipeline (dense + sparse in one pass)
- ✅ 99s per sample (1024-dim dense) vs 85s for legacy BM25

**Performance (Sprint 87):**
- **Embedding Generation:** ~15-20ms per chunk (batch 32)
- **Dense Search:** <100ms (1M vectors)
- **Sparse Search:** <100ms (learned weights)
- **RRF Fusion:** +10-20ms (server-side)
- **Total Hybrid:** <200ms p95

**Sprint 87 Metrics:**
- ✅ Sparse vectors integrated and tested
- ✅ Qdrant multi-vector collection operational
- ✅ RRF fusion working server-side
- ✅ BM25 removed (replaced by sparse)
- ✅ Async embedding service fixed for LangGraph compatibility

---

### Keyword Search: ~~Rank-BM25~~ → BGE-M3 Sparse (Sprint 87 Replacement)

**Status:** ✅ **DEPRECATED** (Sprint 87: Replaced by BGE-M3 sparse vectors)

**Why BGE-M3 Sparse Replaces BM25:**
- **Superior Quality:** Learned token weights > fixed BM25 formula
- **Unified Model:** Single embedding model (dense + sparse)
- **Server-Side Fusion:** Qdrant RRF combines dense + sparse seamlessly
- **Semantic Awareness:** Sparse weights learned from semantic tasks

**Legacy Configuration (Pre-Sprint 87):**
- Tokenization: Custom (lowercase, split, stemming)
- Index: Pickle file (`data/bm25_index.pkl`)
- Update: Re-fit on document ingestion

**Migration Notes (Sprint 87):**
- ❌ BM25 index removed from codebase
- ✅ Replaced with FlagEmbedding sparse vectors
- ✅ Performance improved: ~85s → 99s (acceptable for superior quality)
- ✅ No external indexing service needed

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

### New Dependencies (Sprint 67) - IMPLEMENTED

**Secure Shell Sandbox:**
- `deepagents >=0.2.0` - LangChain-native agent harness with SandboxBackendProtocol ✅ COMPLETE
- `bubblewrap` (system package) - Linux container isolation for code execution ✅ COMPLETE

**Adaptation Framework:**
- `setfit >=1.0.0` - Sentence Transformers fine-tuning for intent classification ✅ COMPLETE
- (Reuses existing: LangGraph, Qwen2.5:7b via Ollama) ✅

**Performance Monitoring:**
- (Enhanced Prometheus metrics - no new dependencies) ✅

### Performance Targets (Sprint 68)

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Query Latency P95** | 500ms | 350ms | -30% |
| **Section Extraction** | 9-15min | 2min | 8x faster |
| **E2E Test Pass Rate** | 57% (337/594) | 100% (594/594) | +43% |
| **Memory Usage** | 8.6GB | 6.0GB | -30% |
| **Throughput** | 40 QPS | 50 QPS | +25% |

### Architecture Enhancements (Sprint 67 COMPLETE, Sprint 68 In Progress)

**Secure Code Execution (Sprint 67 ✅):**
- BubblewrapSandboxBackend with syscall filtering ✅ COMPLETE
- Multi-language support (Bash + Python) ✅ COMPLETE
- Workspace isolation and network restrictions ✅ COMPLETE
- Security tests: path traversal, network escape, sandbox escape all passing

**Tool-Level Adaptation (Sprint 67 ✅):**
- Unified Trace & Telemetry (RAG pipeline monitoring) ✅ COMPLETE (1,850 LOC)
- Eval Harness (automated quality gates with 6 metrics) ✅ COMPLETE
- Adaptive Reranker v1 (cross-encoder fine-tuned) ✅ COMPLETE (+8% hit@5)
- Query Rewriter v1 (query expansion with graph intent) ✅ COMPLETE (+6% recall)
- Dataset Builder (500+ pairs generated from traces) ✅ COMPLETE

**Intent Classification (Sprint 67 → Sprint 81 ✅):**
- C-LARA approach: LLM data generation (Qwen2.5:7b) + SetFit fine-tuning ✅ COMPLETE
- **Sprint 67 accuracy: 60% → 89.5%** (+29.5 percentage points) ✅
- **Sprint 81 Multi-Teacher: 89.5% → 95.22%** (+5.7 percentage points) ✅
- Multi-Teacher data generation: 4 LLMs (qwen2.5:7b, mistral:7b, phi4-mini, gemma3:4b)
- 1,043 training examples (1,001 LLM-generated + 42 edge cases)
- 5-Class C-LARA intents: factual, procedural, comparison, recommendation, navigation
- ~40ms inference latency, 99.7%+ confidence scores

**Section Features (Sprint 68 In Progress):**
- Section Community Detection (Louvain/Leiden algorithms) - IN PROGRESS
- 15 production Cypher queries for section-based retrieval - PLANNED
- Parallelized section extraction (ThreadPoolExecutor) - PLANNED

---

## Sprint 72 Admin UI Features

### MCP Tool Management Integration

**New Frontend Components:**
- `MCPToolsPage.tsx` - Main MCP tools admin page
- `MCPServerList.tsx` - Server listing and connect/disconnect
- `MCPServerCard.tsx` - Individual server status card
- `MCPHealthMonitor.tsx` - Real-time health metrics display
- `MCPToolExecutionPanel.tsx` - Tool parameter input and execution

**New Backend Endpoints:**
- `GET /api/v1/mcp/servers` - List all MCP servers
- `POST /api/v1/mcp/servers/{name}/connect` - Connect to server
- `POST /api/v1/mcp/servers/{name}/disconnect` - Disconnect from server
- `GET /api/v1/mcp/servers/{name}/health` - Get server health metrics
- `GET /api/v1/mcp/servers/{name}/tools` - List available tools
- `POST /api/v1/mcp/tools/execute` - Execute a tool with parameters

**Features:**
- Real-time server health monitoring (CPU, memory, latency)
- Connect/disconnect MCP servers via UI
- Type-safe tool execution with parameter validation
- Pretty-printed JSON result display
- Auto-refresh every 30 seconds
- Responsive design (desktop two-column, mobile tabs)

**Documentation:** [docs/guides/MCP_TOOLS_ADMIN_GUIDE.md](guides/MCP_TOOLS_ADMIN_GUIDE.md)

### Memory Management UI

**New Frontend Components:**
- `MemoryManagementPage.tsx` - Main memory admin page (3 tabs)
- `MemoryStatsCard.tsx` - Statistics display for each memory layer
- `MemorySearchPanel.tsx` - Cross-layer search interface
- `ConsolidationControl.tsx` - Manual consolidation trigger and history

**New Backend Endpoints:**
- `GET /api/v1/memory/stats` - Get all layer statistics
- `GET /api/v1/memory/redis/stats` - Redis layer statistics
- `GET /api/v1/memory/qdrant/stats` - Qdrant layer statistics
- `GET /api/v1/memory/graphiti/stats` - Graphiti layer statistics
- `GET /api/v1/memory/search` - Search across memory layers
- `POST /api/v1/memory/consolidate` - Trigger manual consolidation
- `GET /api/v1/memory/consolidate/history` - Get consolidation history
- `GET /api/v1/memory/consolidate/status` - Get current consolidation status
- `POST /api/v1/memory/export` - Export memory data as JSON

**Tab 1: Statistics**
- Real-time metrics for Redis, Qdrant, and Graphiti
- Per-layer health indicators and capacity usage
- Refresh and optimization controls

**Tab 2: Search**
- Search across all memory layers simultaneously
- Filter by user ID, session ID, date range, keywords
- Results grouped by layer with relevance scores
- Export/delete individual memories

**Tab 3: Consolidation**
- Manual consolidation trigger with progress monitoring
- Consolidation history (last 30 operations)
- Auto-consolidation settings (interval, threshold)
- Retry failed items

**Features:**
- 3-layer visibility (Redis, Qdrant, Graphiti)
- Cross-layer search without Neo4j browser
- Manual consolidation without kubectl/docker commands
- Memory usage trending and capacity planning
- Automatic vs manual consolidation triggers

**Documentation:** [docs/guides/MEMORY_MANAGEMENT_GUIDE.md](guides/MEMORY_MANAGEMENT_GUIDE.md)

### Domain Training UI Completion (Feature 72.2)

**Features Connected:**
- Data Augmentation Dialog (71.13) - Generate synthetic training data
- Batch Document Upload (71.14) - Upload multiple documents with progress
- Domain Details Dialog (71.15) - View and edit domain configuration

**Integration Notes:**
- All backend APIs existed from Sprint 71
- Feature 72.2 purely frontend wiring work
- 18 previously skipped E2E tests now passing

---

## Evaluation & Quality Assurance

### RAGAS Framework (v0.4.2) - RAG Evaluation (Sprint 74-88)

**Status:** ✅ **MIGRATED** (Sprint 79: 0.3.9 → 0.4.2, Sprint 88: Phase 2 evaluation)

**Purpose:** Reference-free evaluation of RAG system quality with 4 metrics + code/table QA.

**RAGAS Core Metrics (0.4.2):**

| Metric | Description | Target Score | Implementation |
|--------|-------------|--------------|-----------------|
| **Context Precision** | Relevant chunks in top-K retrieval | >0.75 | LLM-evaluated usefulness |
| **Context Recall** | Coverage of ground truth in retrieved contexts | >0.70 | Reference-based scoring |
| **Faithfulness** | Answer grounded in retrieved contexts | >0.90 | LLM consistency check |
| **Answer Relevancy** | Answer addresses the query | >0.80 | Question-answer similarity |

**Sprint 88 Evaluation Expansion (Phase 2):**
- **T2-RAGBench** (Tables & Code): 5/5 domains complete (100%)
  - Table QA: 5 benchmark datasets
  - Code QA: 5 benchmark datasets
  - Implemented via RAGAS with custom evaluators
- **MBPP** (Mostly Basic Python Problems): 5/5 categories (100%)
  - Code generation evaluation
  - Functional correctness scoring
  - LLM-assisted execution validation

**Sprint 79 RAGAS Upgrade (0.3.9 → 0.4.2):**
- **Universal LLM Factory:** Auto-detect LLM and prompt routing
- **Experiment API:** Track experiment runs and compare metrics
- **DSPy Optimizer:** Prompt optimization for local models
- **Performance Improvement:** 4x speedup on Nemotron3 with optimized prompts

**Performance Results (Sprint 76-78, GPT-OSS:20b, 10 Amnesty QA questions):**
- **Faithfulness:** 80% ✅
- **Answer Relevancy:** 93% ✅
- **Context Recall:** 50% ⚠️ (below target)
- **Context Precision:** 20% ⚠️ (below target)

**Sprint 88 Metrics Schema:**
```python
# 4 RAGAS metrics + 3 operational metrics
ragas_metrics = {
    "context_precision": 0.72,      # LLM-evaluated relevance
    "context_recall": 0.65,         # Coverage of ground truth
    "faithfulness": 0.88,           # Answer grounding
    "answer_relevancy": 0.91,       # Query-answer match
}

# Operational metrics (Sprint 88 NEW)
operational_metrics = {
    "ingestion_latency_ms": 1234.5,     # Upload to searchable
    "retrieval_latency_ms": 145.3,      # Query to results
    "generation_latency_ms": 2345.6,    # Answer generation
}
```

**Files:**
- `scripts/run_ragas_evaluation.py` - Evaluation runner (Phase 1 + 2)
- `tests/ragas/data/` - Benchmarks (HotpotQA, RAGBench, T2-RAGBench, MBPP)
- `tests/ragas/test_ragas_integration.py` - Backend tests (20+ tests)
- `src/evaluation/ragas_metrics.py` - Metrics schema (Sprint 88)
- `src/evaluation/t2ragbench_evaluator.py` - Table/Code QA evaluation
- `src/evaluation/mbpp_evaluator.py` - Code generation evaluation

**References:**
- [RAGAS GitHub](https://github.com/explodinggradients/ragas)
- [RAGAS 0.4.2 Docs](https://docs.ragas.io/en/latest/)
- [ADR-048: 1000-Sample RAGAS Benchmark](adr/ADR-048-ragas-1000-sample-benchmark.md)
- [docs/ragas/RAGAS_JOURNEY.md](ragas/RAGAS_JOURNEY.md) - Experiment log

---

### DSPy Framework (v2.5+) - Prompt Optimization (Sprint 79)

**Purpose:** Automatic prompt optimization for local LLMs using Stanford DSPy framework.

**Problem:**
RAGAS Few-Shot prompts (2903 chars, 3 examples) too complex for local Ollama inference:
- GPT-OSS:20b: 85.76s per evaluation (target: <20s)
- Nemotron3 Nano: >600s per evaluation (target: <60s)

**DSPy Solution:**
Optimize RAGAS metric prompts using BootstrapFewShot + MIPROv2:
1. **Prompt Compression:** 2903 chars → <1200 chars (2.4x reduction)
2. **Few-Shot Reduction:** 3 examples → 1-2 examples
3. **Instruction Optimization:** LLM-friendly wording for local models
4. **Accuracy Preservation:** Maintain ≥90% accuracy vs original prompts

**Expected Performance (Sprint 79 Targets):**
- GPT-OSS:20b: 85.76s → <20s (4x speedup) ✅
- Nemotron3 Nano: >600s → <60s (10x speedup) ✅
- Total RAGAS time: 1286s → <300s (4.3x speedup) ✅

**DSPy Optimization Techniques:**
```python
import dspy

# Define RAGAS Context Precision as DSPy Signature
class ContextPrecisionSignature(dspy.Signature):
    """Verify if context was useful in arriving at the answer."""
    question: str = dspy.InputField()
    answer: str = dspy.InputField()
    context: str = dspy.InputField()
    verdict: int = dspy.OutputField(desc="1 if useful, 0 if not")

# Optimize with BootstrapFewShot (for GPT-OSS:20b)
optimizer = dspy.BootstrapFewShot(max_bootstrapped_demos=2, max_labeled_demos=1)
compiled_program = optimizer.compile(
    student=ContextPrecisionModule(),
    trainset=training_examples  # 20 examples per metric
)

# Optimize with MIPROv2 (for Nemotron3 Nano - more aggressive)
optimizer = dspy.MIPROv2(num_candidates=10, max_bootstrapped_demos=1)
compiled_program = optimizer.compile(
    student=ContextPrecisionModule(),
    trainset=training_examples
)
```

**Training Data Requirements:**
- 80 labeled examples total (4 metrics × 20 examples each)
- Examples from RAGAS docs + custom Amnesty QA contexts
- Stored in `data/dspy_training/{metric}_examples.json`

**Cache Management:**
- Compiled programs stored in `data/dspy_cache/{llm}_{metric}.json`
- Reusable across RAGAS runs (no re-optimization needed)
- Cache size: ~50-100KB per compiled program

**Integration with RAGAS:**
```bash
# Run RAGAS with DSPy-optimized prompts
poetry run python scripts/run_ragas_evaluation.py \
  --namespace amnesty_qa \
  --mode graph \
  --use-dspy-optimized \
  --llm gpt-oss:20b \
  --dspy-cache-dir data/dspy_cache/
```

**Files:**
- `src/evaluation/dspy_ragas/` - DSPy RAGAS optimization module (Sprint 79)
- `scripts/train_dspy_ragas_optimizers.py` - Optimizer training script
- `scripts/benchmark_dspy_ragas.py` - Performance benchmarking
- `data/dspy_training/` - Training examples (80 examples)
- `data/dspy_cache/` - Compiled programs (8 files: 4 metrics × 2 LLMs)

**References:**
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [SPRINT_79_PLAN.md](sprints/SPRINT_79_PLAN.md) - DSPy RAGAS optimization
- [ADR-042: DSPy for RAGAS Prompt Optimization](adr/ADR-042-dspy-ragas-optimization.md) (Sprint 79)

---

## Graph Expansion Configuration (Sprint 78)

### 3-Stage Semantic Entity Expansion

**Purpose:** Intelligente Entity-Erweiterung für Graph-Retrieval mit LLM + Graph-Traversierung + Synonymen.

**Configuration Settings:**

| Setting | Type | Range | Default | Description |
|---------|------|-------|---------|-------------|
| `graph_expansion_hops` | int | 1-3 | 1 | Graph traversal depth (N-hop neighbors) |
| `graph_min_entities_threshold` | int | 5-20 | 10 | Min entities before LLM synonym fallback |
| `graph_max_synonyms_per_entity` | int | 1-5 | 3 | Max LLM-generated synonyms per entity |
| `graph_semantic_reranking_enabled` | bool | - | true | BGE-M3 semantic reranking of entities |

**Environment Variables:**
```bash
# .env
GRAPH_EXPANSION_HOPS=2              # 1-3 (default: 1)
GRAPH_MIN_ENTITIES_THRESHOLD=15     # 5-20 (default: 10)
GRAPH_MAX_SYNONYMS_PER_ENTITY=5     # 1-5 (default: 3)
GRAPH_SEMANTIC_RERANKING_ENABLED=true
```

**Usage:**
```python
from src.core.config import settings

expander = SmartEntityExpander(
    graph_expansion_hops=settings.graph_expansion_hops,        # ENV var
    min_entities_threshold=settings.graph_min_entities_threshold,
    max_synonyms_per_entity=settings.graph_max_synonyms_per_entity,
)
```

**Frontend UI (Sprint 79 Feature 79.6):**
- `GraphExpansionSettingsCard` component in AdvancedSettings page
- 4 Sliders/Switches (hops, threshold, synonyms, reranking)
- GET/PUT `/api/v1/admin/graph/expansion/config` endpoints
- Redis persistence (similar to LLM Config Sprint 64)

**Impact:**
- Query: "What are global implications of abortion?"
- Before (Sprint 77): 0-2 entities (only exact matches)
- After (Sprint 78): 13 entities (7 graph + 6 synonyms) ✅
- Retrieval improved from 0 chunks → 5 relevant chunks

**References:**
- [ADR-041: Entity→Chunk Expansion & 3-Stage Semantic Search](adr/ADR-041-entity-chunk-expansion-semantic-search.md)
- [SPRINT_78_PLAN.md](sprints/SPRINT_78_PLAN.md)
- `src/components/graph_rag/entity_expansion.py` - SmartEntityExpander class

---

---

## Intent Classification: SetFit + C-LARA (Sprint 67-81)

### SetFit Framework (sentence-transformers 3.3.1)

**Status:** ✅ **PRODUCTION** (Sprint 81: 95.22% accuracy, multi-teacher data)

**Purpose:** Few-shot intent classification with contrastive learning.

**Why SetFit:**
- **Few-Shot Learning:** Train with 1-5 examples per class
- **Contrastive Learning:** Learn discriminative embeddings
- **Sentence-Transformers Integration:** Reuses BGE-M3 backbone
- **Production Performance:** ~40ms inference latency, 99.7%+ confidence

**Sprint 81: C-LARA SetFit Multi-Teacher Intent Classification

### C-LARA 5-Class Intent Framework

**Architecture:** Amazon Science C-LARA (Context-aware LLM-Assisted RAG) + SetFit Contrastive Learning

| Intent | Description | RRF Weights (V/BM25/L/G) |
|--------|-------------|--------------------------|
| **factual** | Specific fact lookup (who, what, when) | 0.30 / 0.30 / 0.40 / 0.00 |
| **procedural** | How-to queries (step-by-step) | 0.40 / 0.10 / 0.20 / 0.30 |
| **comparison** | Compare options (X vs Y) | 0.35 / 0.25 / 0.20 / 0.20 |
| **recommendation** | Suggestions (best X for Y) | 0.30 / 0.20 / 0.20 / 0.30 |
| **navigation** | Find specific docs/sections | 0.20 / 0.50 / 0.30 / 0.00 |

### Multi-Teacher Data Generation

**Why Multi-Teacher:**
- Reduces single-model bias (4 LLMs with different architectures/training)
- Diverse linguistic patterns (creative vs technical vs precise)
- Better generalization on edge cases

| Teacher | Examples | Style | Purpose |
|---------|----------|-------|---------|
| **qwen2.5:7b** | 300 | Precise | Structured, technical queries |
| **mistral:7b** | 300 | Creative | Varied phrasing, natural language |
| **phi4-mini** | 200 | Technical | Domain-specific terminology |
| **gemma3:4b** | 200 | Diverse | Multilingual, short queries |
| **Edge Cases** | 42 | Manual | Typos, code, mixed lang, short |

**Total:** 1,043 training examples

### Edge Cases (Sprint 81 Robustness)

| Category | Examples | Purpose |
|----------|----------|---------|
| **Typos** | "Waht is the defualt port?" | Handle spelling errors |
| **Code** | "Was macht os.path.join()?" | Code snippet queries |
| **Mixed Language** | "Wie mache ich X in Python?" | DE/EN mixed queries |
| **Short Queries** | "RAG?" | Single-word queries |

### Training Results

| Metric | Sprint 67 | Sprint 81 | Improvement |
|--------|-----------|-----------|-------------|
| **Validation Accuracy** | 89.5% | **95.22%** | +5.7pp |
| **Training Time** | 8 min (CPU) | **37 min** (NGC GPU) | - |
| **Model Size** | 420 MB | 418 MB | ~same |
| **Inference Latency** | ~50ms | **~40ms** | -20% |
| **Confidence** | ~85% | **99.7%+** | +17% |

### Per-Class F1 Scores (Sprint 81)

| Intent | F1 Score | Status |
|--------|----------|--------|
| factual | 92.68% | ✅ |
| procedural | 94.12% | ✅ |
| comparison | 97.56% | ✅ |
| recommendation | 97.67% | ✅ |
| navigation | 93.98% | ✅ |

### Files

| File | Purpose |
|------|---------|
| `src/adaptation/intent_data_generator.py` | Multi-teacher data generation |
| `src/adaptation/intent_trainer.py` | SetFit training pipeline |
| `scripts/train_intent_standalone.py` | NGC container training script |
| `src/components/retrieval/intent_classifier.py` | Production classifier (5-class) |
| `models/intent_classifier/` | Trained SetFit model (418 MB) |
| `data/intent_training_multi_teacher_v1.jsonl` | Training data (1,043 examples) |

### Integration

```python
from src.components.retrieval.intent_classifier import classify_intent, CLARAIntent

# Classify query
result = await classify_intent("How do I configure Redis?")
print(result.clara_intent)  # CLARAIntent.PROCEDURAL
print(result.confidence)    # 0.9975
print(result.weights)       # IntentWeights(vector=0.4, bm25=0.1, local=0.2, global_=0.3)
```

**Environment Variable:** `USE_SETFIT_CLASSIFIER=true` (default: true)

---

---

## Sprint 75-93 Technology Evolution Summary

### Sprint 75: CUDA 13.0 & DGX Spark sm_121 Support
- **Infrastructure:** NVIDIA Blackwell GPU (GB10), CUDA 13.0, sm_121 architecture
- **PyTorch:** cu130 wheels (official support, ~10-12 sec/iter)
- **Framework Compatibility:** PyTorch cu128 ❌, TensorFlow ❌, TensorRT ❌ (no sm_121 support yet)
- **Impact:** Foundation for all GPU-accelerated features (embeddings, inference, DSPy training)

### Sprint 79: RAGAS & DSPy Integration
- **RAGAS:** 0.3.9 → 0.4.2 (Universal LLM Factory, Experiment API, DSPy Optimizer)
- **DSPy:** 2.5+ for prompt optimization (BootstrapFewShot, MIPROv2)
- **Performance:** 4x speedup on local models (85.76s → ~20s per evaluation)
- **Files:** `src/evaluation/dspy_ragas/`, training examples in `data/dspy_training/`

### Sprint 81: SetFit Intent Classification
- **SetFit:** >=1.0.0 (few-shot text classification)
- **Datasets:** 4.0.0 (HuggingFace datasets for training)
- **Accuracy:** 89.5% (Sprint 67) → **95.22%** (Sprint 81, multi-teacher)
- **Performance:** ~40ms inference, 99.7%+ confidence
- **Multi-Teacher:** 4 LLMs (qwen2.5:7b, mistral:7b, phi4-mini, gemma3:4b) + 42 edge cases
- **Training Data:** 1,043 examples, 5-class C-LARA intents

### Sprint 82: HuggingFace Datasets & Evaluation Infrastructure
- **Datasets:** 4.0.0 (added to CORE dependencies for SetFit training)
- **RAGBench Adapters:** Stratified sampling, benchmark adapters
- **Evaluation:** 500-sample benchmark (450 answerable + 50 unanswerable)
- **Files:** `tests/ragas/data/`, evaluation adapters

### Sprint 83: Multi-language SpaCy & Ollama Health Monitor
- **SpaCy:** 3.7.0 (DE/EN/FR/ES multi-language NER)
- **spacy-transformers:** 1.3.0 (transformer-based NER models)
- **pynvml:** 11.5.0 (GPU VRAM monitoring)
- **3-Rank Cascade:** Nemotron3 → GPT-OSS → Hybrid SpaCy NER (99.9% success)
- **Gleaning:** +20-40% entity extraction recall (Microsoft GraphRAG technique)
- **Ollama Health Monitor:** Automatic server health checks, error recovery

### Sprint 87: BGE-M3 Native Hybrid Search
- **FlagEmbedding:** 1.2.0+ (dense 1024-dim + sparse lexical weights)
- **Qdrant Multi-Vector:** Server-side RRF fusion (Reciprocal Rank Fusion, k=60)
- **BM25 Deprecation:** Removed, replaced by BGE-M3 sparse vectors
- **Performance:** <200ms p95 (dense + sparse + RRF)
- **Async Fix:** LangGraph compatibility for embedding service calls
- **Migration:** `docs/sprints/SPRINT_87_FINAL_RESULTS.md` documents transition

### Sprint 88: RAGAS Phase 2 Evaluation
- **T2-RAGBench:** Tables & Code QA (5/5 domains, 100%)
- **MBPP:** Code generation (5/5 categories, 100%)
- **Metrics Schema:** 4 RAGAS + 3 operational metrics
- **Evaluators:** `t2ragbench_evaluator.py`, `mbpp_evaluator.py`
- **Comprehensive Logging:** P95 metrics, GPU VRAM, LLM cost tracking

### Sprint 93: LangGraph 1.0 & Tool Composition
- **LangGraph:** 1.0.6 (upgrade from 0.6.10, Oct 2025 GA)
- **Prebuilt Features:** ToolNode, InjectedState, Error Recovery
- **Durable Execution:** State persistence across long-running chains
- **Playwright Integration:** 1.57.0 (browser tool for web automation)
- **Tool DSL:** YAML/JSON parsers for tool composition
- **Features:**
  - 93.1: Tool Composition Framework (ToolNode with error handling)
  - 93.2: Browser Tool (Playwright-based web automation)
  - 93.3: Skill-Tool Mapping (InjectedState for skill context)
  - 93.4: Policy Guardrails (per-skill tool permissions)
  - 93.5: Tool Chain DSL (YAML/JSON tool definition)

---

**Document Consolidated:** Sprint 60 Feature 60.1
**Sprint 67 Complete:** 2026-01-11 (Sandbox + Adaptation + C-LARA, 75 SP, 195 tests, 3,511 LOC)
**Sprint 72 Complete:** 2026-01-03 (Admin UI Features: MCP Tools + Memory Mgmt + Domain Training)
**Sprint 78 Complete:** 2026-01-08 (Graph Entity→Chunk Expansion + 3-Stage Semantic Search, 34 SP, ADR-041)
**Sprint 79 Complete:** 2026-01-08 (RAGAS 0.4.2 Migration, Graph Expansion UI, Admin Graph Ops UI)
**Sprint 81 Complete:** 2026-01-09 (C-LARA SetFit Multi-Teacher 95.22% Accuracy, 40ms inference)
**Sprint 82 Complete:** 2026-01-10 (RAGAS Phase 1 Text-Only Benchmark, 500 samples, 8 SP)
**Sprint 83 Complete:** 2026-01-11 (ER-Extraction Improvements, 3-Rank Cascade, Gleaning, Multi-language SpaCy)
**Sprint 87 Complete:** 2026-01-13 (BGE-M3 Native Hybrid Search, FlagEmbedding, Qdrant RRF, BM25 deprecated)
**Sprint 88 Complete:** 2026-01-14 (RAGAS Phase 2 Evaluation, T2-RAGBench, MBPP code QA)
**Sprint 92 Complete:** 2026-01-14 (Recursive LLM Context Processing, Adaptive Scoring, ADR-052)
**Sprint 93 In Progress:** 2026-01-15 (LangGraph 1.0 Migration, Tool Composition, Playwright Integration)

**Sources:** TECH_STACK.md, DEPENDENCY_RATIONALE.md, pyproject.toml, SPRINT_75-93 plans and final results
**Maintainer:** Documentation Agent (Claude Code)
