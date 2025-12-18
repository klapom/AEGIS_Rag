# Technology Stack
## AegisRAG Project

Aktueller Technologie-Stack des AEGIS RAG Systems.

**Last Updated:** 2025-12-18 (Sprint 51: Maximum Hybrid Search)

---

## Hardware: DGX Spark (sm_121)

| Component | Specification |
|-----------|---------------|
| GPU | NVIDIA GB10 (Blackwell, sm_121) |
| CUDA | 13.0, Driver 580.95.05 |
| Memory | 128GB Unified |
| CPU | 20 ARM Cortex (aarch64) |
| OS | Ubuntu 24.04 |

### Framework Compatibility

| Framework | Status | Notes |
|-----------|--------|-------|
| PyTorch cu130 | ✅ Works | `pip install torch --index-url https://download.pytorch.org/whl/cu130` |
| NGC Container | ✅ Works | `nvcr.io/nvidia/pytorch:25.09-py3` or newer |
| llama.cpp | ✅ Works | Native CUDA compilation |
| Triton | ⚠️ Build | Must build from source for sm_121a |
| PyTorch cu128 | ❌ Fails | `nvrtc: error: invalid value for --gpu-architecture` |
| TensorFlow | ❌ Unsupported | Not supported on DGX Spark |
| TensorRT | ❌ Fails | No sm_121 support |

### Required Environment Variables

```bash
export TORCH_CUDA_ARCH_LIST="12.1a"
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas
export CUDACXX=/usr/local/cuda-13.0/bin/nvcc
```

### Flash Attention Workaround

Flash SDP muss deaktiviert werden, stattdessen Memory-Efficient SDP nutzen.

---

## Core Stack

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Python | 3.12.7 | Runtime |
| **Web Framework** | FastAPI | 0.115+ | REST API |
| **Orchestration** | LangGraph | 0.6.10 | Multi-Agent System |
| **Data Ingestion** | Docling CUDA Container | Latest | GPU-accelerated OCR |
| **Fallback Ingestion** | LlamaIndex | 0.14.3 | Connectors only |
| **Vector DB** | Qdrant | 1.11.0 | Semantic Search |
| **Graph DB** | Neo4j | 5.24 Community | Knowledge Graph |
| **GraphRAG** | LightRAG | Latest | Entity/Topic Retrieval |
| **Memory** | Graphiti | Latest | Bi-Temporal Memory |
| **Cache** | Redis | 7.x | Short-Term Memory |
| **LLM Routing** | AegisLLMProxy | Custom | Multi-Cloud Routing |
| **Embeddings** | BGE-M3 | 1024-dim | Multilingual Embeddings |
| **Monitoring** | Prometheus + Grafana | Latest | Observability |
| **Logging** | Structlog | Latest | Structured JSON |
| **Container** | Docker | 24+ | Containerization |
| **Orchestration** | Kubernetes | 1.28+ | Production Deployment |
| **CI/CD** | GitHub Actions | - | Pipeline |

---

## Backend Stack

### Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | ^0.115.0 | Web Framework |
| uvicorn | ^0.30.0 | ASGI Server |
| pydantic | ^2.9.0 | Data Validation |
| pydantic-settings | ^2.5.0 | Configuration |
| langgraph | ^0.6.10 | Agent Orchestration |
| langchain-core | ^0.3.0 | LLM Abstractions |
| langchain-ollama | ^0.2.0 | Ollama Integration |
| qdrant-client | ^1.11.0 | Vector Database |
| neo4j | ^5.24.0 | Graph Database |
| redis | ^5.0.0 | Cache |
| httpx | ^0.27.0 | Async HTTP Client |
| tenacity | ^9.0.0 | Retry Logic |
| structlog | ^24.4.0 | Logging |

### Package Manager

Poetry (pyproject.toml)

---

## Frontend Stack

| Package | Version | Purpose |
|---------|---------|---------|
| React | 19 | UI Framework |
| TypeScript | ~5.9.0 | Type Safety |
| Vite | 7.1.12 | Build Tool |
| Tailwind CSS | 4.1.0 | Styling |
| React Router | 7.9.2 | Routing |
| Zustand | 5.0.3 | State Management |
| React Markdown | 9.0.2 | Markdown Rendering |
| Lucide Icons | Latest | Icons |
| Playwright | Latest | E2E Testing |

---

## LLM Configuration

### Routing Hierarchy (AegisLLMProxy)

| Priority | Provider | Models | Use Case |
|----------|----------|--------|----------|
| 1 | DGX Spark (vLLM/Ollama) | llama3.2, gemma-3 | Primary Runtime |
| 2 | Alibaba Cloud DashScope | qwen-turbo/plus/max | Fallback |
| 3 | OpenAI | gpt-4o, gpt-4o-mini | Optional Fallback |

### Model Selection

| Task | Model | Provider |
|------|-------|----------|
| Query Understanding | llama3.2:3b | Ollama |
| Generation | llama3.2:8b | Ollama |
| Entity Extraction | gemma-3-4b-it-Q8_0 | Ollama |
| Embeddings | BGE-M3 (1024-dim) | Ollama |
| VLM (Images) | qwen3-vl-30b-a3b-instruct | DashScope |

### Cost Tracking

- SQLite database: `data/cost_tracking.db`
- Monthly budget: $120 (Alibaba Cloud)

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

## Ingestion Pipeline

### Document Processing

| Component | Technology | Purpose |
|-----------|------------|---------|
| OCR | Docling CUDA | GPU-accelerated (95% accuracy) |
| VLM Enrichment | Qwen3-VL | Image descriptions |
| Chunking | Section-Aware Adaptive | 800-1800 tokens |
| Tokenizer | BGE-M3 | 8192 context window |

### Supported Formats

| Format | Handler | Status |
|--------|---------|--------|
| PDF | Docling | ✅ Primary |
| DOCX | Docling | ✅ Primary |
| PPTX | python-pptx | ✅ Supported |
| TXT/MD | Native | ✅ Supported |
| Images | VLM Pipeline | ✅ Supported |

### Pipeline Architecture (LangGraph)

6-Node State Machine:
1. Docling Parse (OCR)
2. VLM Enrichment (Image descriptions)
3. Section-Aware Chunking
4. BGE-M3 Embedding
5. Graph Extraction (Pure LLM)
6. Validation

---

## 4-Signal Hybrid Search Architecture (Sprint 51)

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

**Intent-Weighted RRF:**
- Factual queries: 0.3 vector, 0.3 BM25, 0.4 local, 0.0 global
- Keyword queries: 0.1 vector, 0.6 BM25, 0.3 local, 0.0 global
- Exploratory: 0.2 vector, 0.1 BM25, 0.2 local, 0.5 global
- Summary: 0.1 vector, 0.0 BM25, 0.1 local, 0.8 global

**Cross-Modal Fusion:**
- Extract entity names from LightRAG results (ranked by relevance)
- Query Neo4j for MENTIONED_IN relationships (entities → chunks)
- Boost chunk scores: `final_score = rrf_score + alpha * sum(entity_boosts)`
- Re-rank final results

### CommunityDetector Bug Fixes (Sprint 51)

Fixed critical issues blocking LightRAG global queries:
1. Entity property: `e.id` → `entity_id` (Neo4j property names)
2. Relationship type: `RELATED_TO` → `RELATES_TO` (typo fix)

---

## Phase Event System (Sprint 51)

Real-time thinking pipeline transparency via Server-Sent Events (SSE).

### Phase Types

| Phase | Purpose | Metadata |
|-------|---------|----------|
| INTENT_CLASSIFY | Query understanding | intent, confidence |
| RETRIEVE_VECTOR | Vector search | results_count, latency_ms |
| RETRIEVE_BM25 | Keyword search | results_count, latency_ms |
| RETRIEVE_GRAPH_LOCAL | Entity relationships | entities_found, latency_ms |
| RETRIEVE_GRAPH_GLOBAL | Community retrieval | topics_found, latency_ms |
| FUSION | RRF + cross-modal | fusion_method, output_count |
| RERANK | Cross-encoder re-ranking | rerank_model, output_count |
| GENERATION | LLM answer generation | model, tokens |
| STREAMING | Token-by-token output | ttft_ms, tokens_per_sec |

### Event Emission Strategy

- **Start Event:** Emitted when phase begins
- **End Event:** Emitted when phase completes (with latency + metadata)
- **Frontend Display:** "Thinking... Step 1/8" format
- **Persistence:** Phase events stored in conversation history
- **Metadata:** Retrieved count, latency, model name, error details

### Token Streaming (Sprint 50-51)

```
Phase: GENERATION → (Start)
  "Generating answer with llama3.2:8b..."
                    ↓
Phase: STREAMING → (Tokens 1-10)
  TTFT: 45ms
  Tokens/sec: 15.3
  Current: "RAG is Retrieval-Augmented Generation..."
                    ↓
Phase: STREAMING → (Complete)
  Total tokens: 125
  Duration: 8.2s
```

---

## 3-Layer Memory Architecture

| Layer | Storage | Latency | Purpose |
|-------|---------|---------|---------|
| 1 | Redis | <10ms | Session state, working memory |
| 2 | Qdrant | <50ms | Semantic long-term memory |
| 3 | Graphiti + Neo4j | <200ms | Episodic, bi-temporal relationships |

---

## Multi-Agent System (LangGraph)

| Agent | Responsibility |
|-------|----------------|
| Coordinator | Query routing, orchestration |
| Vector Search | Qdrant hybrid search (Vector + BM25) |
| Graph Query | Neo4j + LightRAG (entities, topics) |
| Memory | Graphiti retrieval, consolidation |
| Action | Tool execution (MCP) |

### Retrieval Strategy

- **Hybrid Search:** Vector + BM25 + Graph
- **Fusion:** Reciprocal Rank Fusion (RRF, k=60)
- **Reranking:** Cross-encoder (ms-marco-MiniLM-L-6-v2)

---

## Development Tools

### Code Quality

| Tool | Purpose |
|------|---------|
| Ruff | Linter (line-length=100) |
| Black | Formatter (line-length=100) |
| MyPy | Type checker (strict) |
| Bandit | Security scanner |
| Pre-commit | Git hooks |

### Monitoring Stack

| Component | Tool |
|-----------|------|
| Metrics | Prometheus |
| Visualization | Grafana |
| Logs | Loki |
| Traces | Jaeger |
| LLM Tracing | LangSmith |

---

## Infrastructure

### Docker Services

| Service | Image |
|---------|-------|
| API | aegis-rag-api:dev |
| Qdrant | qdrant/qdrant:v1.11.0 |
| Neo4j | neo4j:5.24-community |
| Redis | redis:7-alpine |
| Prometheus | prom/prometheus:latest |
| Grafana | grafana/grafana:latest |

### Kubernetes

- Helm Charts for deployment
- Horizontal Pod Autoscaling (HPA)
- Persistent Volume Claims (PVC)
- Ingress with TLS (cert-manager)

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Simple Query (Vector) | <200ms p95 |
| Hybrid Query (Vector+Graph) | <500ms p95 |
| Complex Multi-Hop | <1000ms p95 |
| Sustained Load | 50 QPS |
| Document Ingestion | <90s (streaming) |

---

## Security

| Feature | Implementation |
|---------|----------------|
| Hashing | SHA-256 (chunk IDs) |
| Input Validation | Pydantic v2 |
| Rate Limiting | slowapi |
| Content Filtering | Custom middleware |
| Secrets | Environment variables |

---

## Cost Estimation (Monthly)

| Component | Cost | Notes |
|-----------|------|-------|
| Ollama (Local) | $0 | Development |
| DGX Spark | Hardware | Primary runtime |
| Alibaba Cloud | $0-120 | Budget-controlled |
| Self-hosted DBs | $0 | Docker containers |
| **Total (Dev)** | **$0** | Fully local |
| **Total (Prod)** | **$0-150** | With cloud fallback |
