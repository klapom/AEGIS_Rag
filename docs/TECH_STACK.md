# Technology Stack Matrix
## AegisRAG Project

Vollständiger Überblick über gewählte Technologien, Versionen, Alternativen und Begründungen.

---

## Core Stack Overview

| Category | Primary Choice | Version | Alternative 1 | Alternative 2 | Decision Basis |
|----------|---------------|---------|---------------|---------------|----------------|
| **Language** | Python | 3.11+ | TypeScript | Go | AI/ML Ecosystem (ADR-007) |
| **Web Framework** | FastAPI | 0.115+ | Django | Flask | Performance + Type Safety |
| **Orchestration** | LangGraph | 0.2+ | CrewAI | AutoGen | Workflow Control (ADR-001) |
| **Data Ingestion** | LlamaIndex | 0.11+ | LangChain | Custom | RAG-Optimized |
| **Vector DB** | Qdrant | 1.10+ | Pinecone | Weaviate | Performance (ADR-003) |
| **Graph DB** | Neo4j | 5.x | FalkorDB | Memgraph | Maturity + Community |
| **GraphRAG** | LightRAG | Latest | Microsoft GraphRAG | LlamaIndex PropertyGraph | Cost + Speed (ADR-004) |
| **Memory** | Graphiti | Latest | Custom | MemGPT | Temporal Awareness |
| **Cache** | Redis | 7.x | Memcached | DragonflyDB | Persistence + Features |
| **MCP** | Official Python SDK | Latest | TypeScript SDK | Custom | Native Support |
| **LLM** | Ollama (llama3.2:3b/8b) | Latest | Azure OpenAI GPT-4o | Anthropic Claude | Cost-Free Dev + Local (ADR-002) |
| **Embeddings** | nomic-embed-text (Ollama) | Latest | text-embedding-3-large | all-MiniLM-L6-v2 | Local + Cost-Free |
| **Monitoring** | Prometheus + Grafana | Latest | Datadog | New Relic | Open Source |
| **Logging** | Structlog | Latest | Python Logging | Loguru | Structured JSON |
| **Container** | Docker | 24+ | Podman | - | Industry Standard |
| **Orchestration** | Kubernetes | 1.28+ | Docker Swarm | Nomad | Production-Grade |
| **CI/CD** | GitHub Actions | - | GitLab CI | CircleCI | Native GitHub Integration |

---

## Sprint Progress (Sprints 12-15)

### Sprint 12: Advanced Features
**Status:** ✅ COMPLETE (2025-10-18 → 2025-10-21)

**Technologies Added:**
- **LightRAG**: Graph-based RAG with dual-level retrieval (entities + topics)
- **Advanced Chunking**: Adaptive chunking with LlamaIndex (512 tokens, 128 overlap)
- **Multi-Hop Graph Queries**: Neo4j Cypher for relationship traversal

**Achievements:**
- Graph-enhanced retrieval with entity linking
- Adaptive chunking for better context boundaries
- Multi-hop reasoning over knowledge graphs

### Sprint 13: Entity/Relation Extraction Pipeline
**Status:** ✅ COMPLETE (2025-10-21 → 2025-10-24)

**Technologies Added:**
- **spaCy (en_core_web_lg)**: Fast entity extraction (NER)
- **Sentence-Transformers (all-MiniLM-L6-v2)**: Semantic deduplication embeddings
- **Gemma 3 4B (Ollama)**: Lightweight relation extraction model
- **Advanced Deduplication**: Levenshtein + FAISS + token normalization

**Achievements:**
- Three-phase pipeline: SpaCy → Semantic Dedup → Gemma 3
- Performance: >300s → <30s (10x improvement)
- Entity deduplication: 95% accuracy
- ADR-017 (Semantic Deduplication), ADR-018 (Model Selection)

**Technical Stack:**
```python
# Entity Extraction
spacy.load("en_core_web_lg")  # NER
sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")  # Embeddings
faiss.IndexFlatL2(384)  # Vector similarity

# Relation Extraction
OllamaLLM(model="gemma2:4b")  # Lightweight, structured output
```

### Sprint 14: Production Benchmarking & Monitoring
**Status:** ✅ COMPLETE (2025-10-24 → 2025-10-27)

**Technologies Added:**
- **Prometheus Client**: Custom metrics (12 metrics total)
- **Memory Profiler**: Peak memory usage tracking
- **pytest-benchmark**: Performance regression testing
- **Tenacity**: Retry logic with exponential backoff

**Achievements:**
- Production-grade benchmarking suite
- 132 tests total (112 unit, 20 integration)
- Prometheus metrics for extraction pipeline
- Memory profiling and optimization
- ADR-019 (Integration Tests as E2E Tests)

**Monitoring Stack:**
```python
from prometheus_client import Counter, Histogram, Gauge

# Custom Metrics
entity_extraction_duration = Histogram("entity_extraction_duration_seconds", ...)
relation_extraction_duration = Histogram("relation_extraction_duration_seconds", ...)
entities_extracted_total = Counter("entities_extracted_total", ...)
relations_extracted_total = Counter("relations_extracted_total", ...)
```

### Sprint 15: React Frontend & SSE Streaming
**Status:** ✅ COMPLETE (2025-10-27 → 2025-10-28)

**Technologies Added:**
- **React 18.2**: Modern React with hooks
- **TypeScript 5.9**: Type-safe frontend development
- **Vite 7.1**: Fast build tool with HMR
- **Tailwind CSS v4.1**: Utility-first CSS framework (new `@import` syntax)
- **React Router v7.9**: Client-side routing
- **Zustand 5.0**: Lightweight state management
- **Server-Sent Events (SSE)**: Real-time streaming from backend
- **React Markdown**: Markdown rendering for answers
- **Vitest 4.0**: Unit testing framework
- **React Testing Library**: Component testing

**Achievements:**
- Production-ready React frontend (Perplexity.ai-inspired design)
- Real-time streaming with SSE (token-by-token display)
- German localization
- Multi-mode search (Hybrid, Vector, Graph, Memory)
- Health dashboard with system metrics
- 15 frontend tests, all passing
- ADR-020 (SSE Streaming), ADR-021 (Perplexity UI Design)

**Frontend Stack:**
```json
{
  "react": "^18.2.0",
  "typescript": "~5.9.0",
  "vite": "^7.1.0",
  "tailwindcss": "^4.1.0",
  "@tailwindcss/postcss": "^4.1.0",
  "react-router": "^7.9.2",
  "zustand": "^5.0.3",
  "react-markdown": "^9.0.2",
  "vitest": "^4.0.0",
  "@testing-library/react": "^16.1.0"
}
```

**Backend SSE Integration:**
```python
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
        yield f"event: source\ndata: {json.dumps(source)}\n\n"
        for token in tokens:
            yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"
        yield f"event: complete\ndata: {json.dumps(final_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Cumulative Technology Additions (Sprints 12-15)

| Sprint | Category | Technology | Version | Purpose |
|--------|----------|------------|---------|---------|
| 12 | GraphRAG | LightRAG | Latest | Dual-level graph retrieval |
| 13 | NLP | spaCy | 3.8+ | Fast entity extraction |
| 13 | Embeddings | all-MiniLM-L6-v2 | Latest | Deduplication embeddings |
| 13 | LLM | Gemma 3 4B (Ollama) | Latest | Relation extraction |
| 13 | Vector Search | FAISS | Latest | Semantic similarity |
| 14 | Monitoring | Prometheus Client | Latest | Custom metrics |
| 14 | Testing | pytest-benchmark | Latest | Performance tests |
| 14 | Reliability | Tenacity | ^9.0.0 | Retry logic |
| 15 | Frontend | React | 18.2.0 | UI framework |
| 15 | Frontend | TypeScript | 5.9.0 | Type safety |
| 15 | Frontend | Vite | 7.1.0 | Build tool |
| 15 | Frontend | Tailwind CSS | 4.1.0 | Styling |
| 15 | Frontend | React Router | 7.9.2 | Routing |
| 15 | Frontend | Zustand | 5.0.3 | State management |
| 15 | Streaming | SSE | Native | Real-time updates |
| 15 | Testing | Vitest | 4.0.0 | Frontend tests |

### Embedding Model Evolution

**Layer 2 (Qdrant):**
- Model: `nomic-embed-text` (Ollama)
- Dimensions: 768
- Purpose: Semantic document search
- Status: ✅ Production-ready

**Layer 3 (Graphiti):**
- Model: `BGE-M3` (1024-dim)
- Purpose: Episodic memory and temporal reasoning
- Status: ✅ Active (Sprint 10 implementation)
- Note: Incompatible embedding space with Layer 2

**Issue Identified (Sprint 16):**
- Two separate embedding models create incompatible vector spaces
- Cannot compute cross-layer similarity between Qdrant and Graphiti
- Sprint 16 Feature 16.4 will evaluate BGE-M3 standardization

---

## Detailed Component Analysis

### 1. Backend Framework: FastAPI

**Chosen Version:** 0.115+

**Key Dependencies:**
```toml
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.30.0"}
pydantic = "^2.9.0"
pydantic-settings = "^2.5.0"
```

**Why FastAPI?**
- Fastest Python web framework (Starlette + Pydantic)
- Auto-generated OpenAPI documentation
- Native async/await support
- Type safety via Pydantic v2
- Dependency injection system

**Alternatives Considered:**
| Framework | Pro | Contra | When to Use |
|-----------|-----|--------|-------------|
| Django | Batteries-included, ORM, Admin | Overkill, slower, not async-first | Full web apps with UI |
| Flask | Lightweight, simple | No async, manual validation | Microservices, simple APIs |
| Sanic | Fast, async | Smaller ecosystem | High-performance APIs |

---

### 2. Agent Orchestration: LangGraph

**Chosen Version:** 0.2+

**Key Dependencies:**
```toml
langgraph = "^0.2.0"
langchain-core = "^0.3.0"
langchain-ollama = "^0.2.0"  # Primary - Local & Cost-Free
langchain-openai = "^0.2.0"  # Optional for Azure OpenAI (Production only)
langchain-anthropic = "^0.2.0"  # Optional fallback (Production only)
langgraph-checkpoint-postgres = "^0.2.0"  # State persistence
```

**Why LangGraph?**
- Explicit graph-based workflow control
- State management with persistence
- Conditional routing and cycles
- LangSmith integration for debugging
- Production-ready (Uber, Klarna)

**Alternatives Considered:**
| Framework | Pro | Contra | When to Use |
|-----------|-----|--------|-------------|
| CrewAI | Easiest learning curve, fastest execution | Less control | Quick prototyping, role-based agents |
| AutoGen | Microsoft backing, event-driven | More complex setup | Research, code execution |
| LlamaIndex Workflows | Event-driven, RAG-native | Newer, less mature | Data-centric workflows |

**Migration Path:**
- Sprint 4: Evaluate LangGraph performance
- If bottlenecks: Consider CrewAI for speed-critical paths
- Abstraction layer allows framework swap

---

### 3. Data Ingestion: LlamaIndex

**Chosen Version:** 0.11+

**Key Dependencies:**
```toml
llama-index = "^0.11.0"
llama-index-llms-ollama = "^0.4.0"  # Primary - Local & Cost-Free
llama-index-embeddings-ollama = "^0.4.0"  # Primary - Local & Cost-Free
llama-index-vector-stores-qdrant = "^0.3.0"
llama-index-graph-stores-neo4j = "^0.3.0"
llama-index-llms-openai = "^0.2.0"  # Optional for Azure (Production only)
llama-index-embeddings-openai = "^0.2.0"  # Optional for Azure (Production only)
```

**Why LlamaIndex?**
- 300+ data connectors (APIs, DBs, Cloud)
- Purpose-built for RAG workflows
- Opinionated patterns accelerate development
- Native support for HyDE, Self-RAG, RAPTOR
- LlamaCloud for managed services

**Alternatives Considered:**
| Tool | Pro | Contra | When to Use |
|------|-----|--------|-------------|
| LangChain | Broader ecosystem, more flexible | Less RAG-focused | General AI apps |
| Haystack | Production-ready, pipelines | Less LLM-centric | Traditional NLP + RAG |
| Custom | Maximum control | High development cost | Specific requirements |

**Usage Pattern:**
- LlamaIndex for data ingestion and indexing
- LangGraph for workflow orchestration
- Combined approach: Best of both worlds

---

### 4. Vector Database: Qdrant

**Chosen Version:** 1.10+

**Key Dependencies:**
```toml
qdrant-client = "^1.11.0"
```

**Configuration:**
```yaml
qdrant:
  host: localhost
  port: 6333
  grpc_port: 6334
  collection: documents_v1
  vector_size: 768  # nomic-embed-text (Ollama, Primary) or 3072 for Azure (Optional)
  distance: Cosine
  quantization:
    type: scalar
    quantile: 0.99
    always_ram: true
```

**Why Qdrant?**
- Best performance (3ms @ 1M embeddings)
- 24x compression via quantization
- Advanced filtering during search
- Open source + managed option
- Native integrations

**Alternatives Considered:**
| Database | Pro | Contra | Cost (estimate) |
|----------|-----|--------|-----------------|
| Pinecone | Serverless, zero-ops | Vendor lock-in, no self-host | $70/month @ 1M vectors |
| Weaviate | Hybrid search native | Slower than Qdrant | Self-host or $25/month |
| ChromaDB | Easy setup | Not production-scale | Free (self-host) |
| Milvus | Highly scalable | Complex operations | Self-host only |

**Scaling Strategy:**
- Start: Qdrant Docker (1M vectors)
- Growth: Qdrant Cloud (10M+ vectors)
- Enterprise: Distributed Qdrant (billions)

---

### 5. Graph Database: Neo4j

**Chosen Version:** 5.x Community Edition

**Key Dependencies:**
```toml
neo4j = "^5.24.0"
```

**Configuration:**
```yaml
neo4j:
  uri: bolt://localhost:7687
  user: neo4j
  password: ${NEO4J_PASSWORD}
  database: neo4j
  max_connection_pool_size: 50
  connection_timeout: 30s
  memory:
    heap_max: 2G
    pagecache: 1G
```

**Why Neo4j?**
- Most mature graph database (since 2007)
- Cypher query language (intuitive)
- ACID compliance
- Excellent visualization (Neo4j Browser)
- Largest community

**Alternatives Considered:**
| Database | Pro | Contra | When to Use |
|----------|-----|--------|-------------|
| FalkorDB | Redis-compatible, fast | Less mature | Redis ecosystem |
| Memgraph | Fast in-memory | Less tooling | High-performance graphs |
| ArangoDB | Multi-model (Doc+Graph) | Less specialized | Flexible data models |
| JanusGraph | Distributed, scalable | Complex setup | Massive graphs |

**Edition Decision:**
- **Community Edition:** Free, sufficient for MVP
- **Enterprise Edition:** If needed (Multi-DC, Advanced Security)
- **AuraDB (Managed):** Consider for production

---

### 6. GraphRAG: LightRAG

**Chosen Version:** Latest from GitHub

**Key Dependencies:**
```toml
lightrag = {git = "https://github.com/HKUDS/LightRAG.git"}
```

**Why LightRAG?**
- Lower cost than Microsoft GraphRAG
- Incremental updates (no full re-index)
- Dual-level retrieval (entities + topics)
- Multiple backend support
- Active development (EMNLP 2025)

**Alternatives Considered:**
| Solution | Pro | Contra | Cost Factor |
|----------|-----|--------|-------------|
| Microsoft GraphRAG | Most mature, best docs | Expensive indexing, static | 10x LightRAG |
| LlamaIndex PropertyGraph | Native integration | Less optimized | Medium |
| Custom | Full control | High dev cost | Highest |

**Migration Strategy:**
- Sprint 5: Implement LightRAG
- Monitor: Cost, performance, quality
- Fallback: Microsoft GraphRAG if quality issues

---

### 7. Memory System: Graphiti

**Chosen Version:** Latest from GitHub

**Key Dependencies:**
```toml
graphiti = {git = "https://github.com/getzep/graphiti.git"}
```

**Why Graphiti?**
- Unique bi-temporal tracking
- Point-in-time queries
- Real-time incremental updates
- Sub-100ms retrieval latency
- Built for conversational AI

**Alternatives Considered:**
| Solution | Pro | Contra | When to Use |
|----------|-----|--------|-------------|
| MemGPT | Hierarchical memory | Complex setup | Research projects |
| Custom Redis+Vector | Simple | No temporal reasoning | Basic memory |
| Zep | Managed solution | Less flexible | Plug-and-play |

---

### 8. LLM Selection Matrix

**Development Strategy (Local-First):**

| Use Case | Development (Local) | Production (Optional) | Rationale |
|----------|-------------------|---------------------|-----------|
| **Query Understanding** | Ollama (llama3.2:3b) | Azure GPT-4o-mini (Optional) | Speed + Cost-free Dev |
| **Final Generation** | Ollama (llama3.2:8b) | Azure GPT-4o (Optional) | Quality + Local Testing |
| **Embedding** | nomic-embed-text (Ollama) | text-embedding-3-large (Azure, Optional) | Local-first + Cost-Free |
| **Reranking** | ms-marco-MiniLM-L12-v2 | cross-encoder/ms-marco-TinyBERT | Local processing |
| **Entity Extraction** | Ollama (llama3.2:8b) | Azure GPT-4o | Structured output |
| **Development/Testing** | Ollama (local) | N/A | Cost-free, offline capable |

**Ollama Models for Development:**
```bash
# Recommended Ollama models to pull
ollama pull llama3.2:3b        # Fast queries, 2GB RAM
ollama pull llama3.2:8b        # Quality responses, 4.7GB RAM
ollama pull nomic-embed-text   # Embeddings (768-dim), 274MB
ollama pull mistral:7b         # Alternative model
```

**Dual-Stack LLM Strategy:**
```python
# Environment-aware LLM routing
def select_llm(task_type: str, complexity: str, env: str = "dev") -> LLM:
    if env == "dev" or not os.getenv("AZURE_OPENAI_ENDPOINT"):
        # Local development with Ollama
        if task_type == "query_understanding":
            return OllamaLLM(model="llama3.2:3b")
        else:
            return OllamaLLM(model="llama3.2:8b")
    else:
        # Production with Azure OpenAI (optional)
        if task_type == "query_understanding":
            return AzureOpenAI(model="gpt-4o-mini")
        elif complexity == "high":
            return AzureOpenAI(model="gpt-4o")
        else:
            return AzureOpenAI(model="gpt-4o-mini")
```

**Migration Path:**
- **Sprint 1-6:** Develop entirely with Ollama (local)
- **Sprint 7:** Implement Azure OpenAI integration (optional)
- **Sprint 8-10:** A/B testing, benchmarking, production deployment

---

## Development Tools

### Code Quality

| Tool | Version | Purpose | Configuration |
|------|---------|---------|---------------|
| **Ruff** | Latest | Linter (replaces Flake8, isort) | `line-length=100` |
| **Black** | Latest | Formatter | `line-length=100` |
| **MyPy** | Latest | Type checker | `strict=true` |
| **Bandit** | Latest | Security scanner | Default |
| **Safety** | Latest | Dependency scanner | Daily checks |
| **Pre-commit** | Latest | Git hooks | Auto-run on commit |

**Pre-commit Configuration:**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
  
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.9
    hooks:
      - id: bandit
        args: [-c, pyproject.toml]
```

---

### Testing Stack

| Tool | Version | Purpose | Usage |
|------|---------|---------|-------|
| **pytest** | ^8.0.0 | Test framework | Unit, integration, E2E |
| **pytest-asyncio** | ^0.23.0 | Async tests | Async functions |
| **pytest-cov** | ^5.0.0 | Coverage reporting | `pytest --cov` |
| **pytest-mock** | ^3.14.0 | Mocking | Mock external services |
| **Faker** | ^30.0.0 | Test data generation | Factories |
| **Locust** | ^2.29.0 | Load testing | Performance tests |
| **responses** | ^0.25.0 | HTTP mocking | API tests |

**Coverage Targets:**
- Overall: >80%
- Critical paths: >90%
- New code: 100%

---

### Monitoring & Observability

| Component | Tool | Purpose | Retention |
|-----------|------|---------|-----------|
| **Metrics** | Prometheus | Time-series metrics | 30 days |
| **Visualization** | Grafana | Dashboards | N/A |
| **Logs** | Loki | Centralized logging | 7 days |
| **Traces** | Jaeger | Distributed tracing | 3 days |
| **APM** | LangSmith | LLM-specific tracing | 30 days |
| **Errors** | Sentry | Error tracking | 90 days |
| **Uptime** | Healthchecks.io | Cron monitoring | 30 days |

**Key Metrics:**
```yaml
Custom Metrics:
  - query_latency_seconds (histogram)
  - retrieval_precision_at_k (gauge)
  - agent_execution_time_seconds (histogram)
  - memory_hit_rate_ratio (gauge)
  - llm_token_usage_total (counter)
  - qdrant_search_latency_ms (histogram)
  - neo4j_query_latency_ms (histogram)
```

---

## Infrastructure Stack

### Containerization

**Docker Compose (Development):**
```yaml
services:
  api:
    image: aegis-rag-api:dev
    build: ./docker/Dockerfile.api
    ports: ["8000:8000"]
    
  qdrant:
    image: qdrant/qdrant:v1.11.0
    ports: ["6333:6333"]
    volumes: ["qdrant_data:/qdrant/storage"]
    
  neo4j:
    image: neo4j:5.24-community
    ports: ["7474:7474", "7687:7687"]
    volumes: ["neo4j_data:/data"]
    
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: ["redis_data:/data"]
    command: redis-server --appendonly yes
    
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
```

**Kubernetes (Production):**
- Helm Chart for deployment
- Horizontal Pod Autoscaling (HPA)
- Persistent Volume Claims (PVC) for databases
- Ingress with TLS (cert-manager)
- External Secrets Operator

---

### CI/CD Pipeline

**GitHub Actions Workflows:**

| Workflow | Trigger | Jobs | Duration |
|----------|---------|------|----------|
| **CI** | Push, PR | Lint → Test → Build → Security | ~8 min |
| **CD Staging** | Merge to develop | Build → Push → Deploy | ~5 min |
| **CD Production** | Tag v* | Build → Push → Deploy → Smoke Test | ~7 min |
| **Nightly** | Cron (2 AM) | Full test suite + E2E | ~30 min |

**Pipeline Stages:**
```
Lint (Black, Ruff, MyPy) → 
Unit Tests (pytest) → 
Integration Tests (Docker Compose) → 
Security Scan (Bandit, Trivy) → 
Build Docker Image → 
Push to Registry (GHCR) → 
Deploy (Helm) → 
Smoke Tests → 
Rollback on Failure
```

---

## Dependency Management

**Package Manager:** Poetry (preferred) or UV (faster)

**pyproject.toml Structure:**
```toml
[tool.poetry]
name = "aegis-rag"
version = "0.1.0"
python = "^3.11"

[tool.poetry.dependencies]
# Core
python = "^3.11"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.30.0"}
pydantic = "^2.9.0"

# LLM & RAG
langgraph = "^0.2.0"
langchain-core = "^0.3.0"
langchain-ollama = "^0.2.0"
llama-index = "^0.11.0"
llama-index-llms-ollama = "^0.4.0"  # Primary - Local & Cost-Free
llama-index-embeddings-ollama = "^0.4.0"  # Primary - Local & Cost-Free
ollama = "^0.3.0"  # Primary - Local & Cost-Free
openai = "^1.40.0"  # Optional for Azure OpenAI (Production only)
anthropic = "^0.34.0"  # Optional fallback (Production only)

# Databases
qdrant-client = "^1.11.0"
neo4j = "^5.24.0"
redis = "^5.0.0"

# Utilities
pydantic-settings = "^2.5.0"
python-dotenv = "^1.0.0"
tenacity = "^9.0.0"
structlog = "^24.4.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^5.0.0"
mypy = "^1.11.0"
ruff = "^0.6.0"
black = "^24.8.0"
pre-commit = "^3.8.0"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
```

**Update Strategy:**
- **Weekly:** Patch versions (automated PR via Dependabot)
- **Monthly:** Minor versions (manual review)
- **Quarterly:** Major versions (migration guide required)

---

## Cost Estimation (Monthly)

| Component | Tier | Cost | Notes |
|-----------|------|------|-------|
| **Ollama (Local)** | Self-hosted | $0 | Development & testing |
| **Azure OpenAI API** | Pay-as-go | $0-500 | Optional for production |
| **Qdrant** | Self-hosted | $0 | Docker container |
| **Neo4j** | Community | $0 | Docker container |
| **Redis** | Self-hosted | $0 | Docker container |
| **Compute** | Local/VPS | $0-50 | Local dev or small VPS |
| **LangSmith** | Free/Team | $0-39 | Optional tracing |
| **GitHub Actions** | Standard | $0 | Free for public repos |
| **Monitoring** | Self-hosted | $0 | Prometheus + Grafana |
| **Total (Development)** | - | **$0** | Fully local with Ollama |
| **Total (Production - Local)** | - | **$0-100** | Self-hosted, optional Azure |
| **Total (Production - Cloud)** | - | **$300-1000** | With Azure OpenAI + managed services |

**Cost Optimization Strategy:**
- **Development:** 100% free with Ollama (llama3.2:3b/8b + nomic-embed-text) and local Docker containers
- **Testing:** Use Ollama for all testing phases - no API costs
- **Embeddings:** Always use nomic-embed-text (Ollama) - local and free
- **Production:** Optional Azure OpenAI integration only if needed (LLM generation only)
- **Caching:** Redis for frequent queries to reduce any API calls
- **Scaling:** Start local, move to cloud only when necessary

---

## Version Compatibility Matrix

| Python | FastAPI | LangGraph | LlamaIndex | Qdrant Client | Neo4j Driver |
|--------|---------|-----------|------------|---------------|--------------|
| 3.11 | ✅ 0.115+ | ✅ 0.2+ | ✅ 0.11+ | ✅ 1.11+ | ✅ 5.24+ |
| 3.12 | ✅ 0.115+ | ✅ 0.2+ | ✅ 0.11+ | ✅ 1.11+ | ✅ 5.24+ |
| 3.13 | ⚠️ Testing | ⚠️ Testing | ⚠️ Testing | ✅ 1.11+ | ✅ 5.24+ |

**Recommendation:** Python 3.11 for maximum compatibility

---

## Technology Decision Checklist

When evaluating a new technology:

- [ ] **Maturity:** Production-ready? Active maintenance?
- [ ] **Community:** GitHub stars >1K? Active issues/PRs?
- [ ] **Documentation:** Comprehensive docs? Examples?
- [ ] **Integration:** Works with existing stack?
- [ ] **Performance:** Meets latency/throughput targets?
- [ ] **Cost:** Within budget? Hidden costs?
- [ ] **Licensing:** Compatible with project license?
- [ ] **Security:** CVE history? Security practices?
- [ ] **Support:** Community or commercial support available?
- [ ] **Migration:** Easy to migrate away if needed?

---

Diese Technology Stack Matrix sollte bei Major Version Updates oder Technology Evaluations aktualisiert werden.
