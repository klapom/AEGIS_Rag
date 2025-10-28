# DEPENDENCY RATIONALE - AEGIS RAG

**Purpose:** Justification for major library choices with version constraints
**Format:** Library: Version | Rationale | Alternatives Rejected
**Last Updated:** 2025-10-22 (Post-Sprint 12)

---

## ORCHESTRATION & AGENTS

### LangGraph: 0.6.10 | Multi-Agent Orchestration Framework (ADR-001)

**Version:** `^0.6.10` (latest stable)

**Rationale:**
- **Explicit Control:** Graph-based workflow definition with conditional routing, cycles, parallel execution (Send API)
- **Production Features:** LangSmith tracing, durable execution via checkpointers, state persistence, retry logic
- **Flexibility:** Supports complex multi-agent workflows with precise state management (Pydantic typing)
- **Ecosystem:** Native integration with LangChain, Vector DBs, Tools
- **Maturity:** Enterprise-proven (Klarna, Uber, Replit use in production)

**Alternatives Rejected:**
- **CrewAI:** Too simple (limited control over workflow), no graph visualization, younger ecosystem. 5.76x faster but lacks production features.
- **AutoGen (Microsoft):** Event-driven architecture requires more infrastructure setup, conversational paradigm less suited for deterministic RAG workflows. More boilerplate.
- **LlamaIndex Workflows:** Newer API (less mature), less ecosystem integration, less community support. Good for RAG-specific tasks but weaker for general orchestration.

**Trade-offs:**
- ⚠️ Steep learning curve (requires understanding of graph concepts)
- ⚠️ More boilerplate code than CrewAI
- ⚠️ Higher initial development time
- ✅ Better debuggability via LangGraph Studio (visual graph inspection)
- ✅ Production-ready state management out-of-box

---

## LLM PROVIDERS

### Ollama: >=0.6.0,<1.0.0 | Local LLM Inference (ADR-002)

**Version:** `>=0.6.0,<1.0.0` (required by langchain-ollama 1.0.0)

**Rationale:**
- **Zero Cost:** 100% local inference, $0 API fees (saves $18K-24K/year vs Azure OpenAI)
- **Offline-Capable:** Air-gapped deployment for sensitive/classified data, no internet dependency
- **DSGVO Compliance:** 100% data residency (no data leaves local network)
- **No Vendor Lock-in:** Switch models freely (llama3.2, qwen2.5, smollm2)
- **Modern Performance:** llama3.2:8b quality sufficient for 90%+ use cases, GPU acceleration mandatory (105 tokens/s on RTX 3060)

**Alternatives Rejected:**
- **Azure OpenAI:** $200-500/month dev, $1000+/month production. Requires internet, vendor lock-in, DSGVO challenges (US data residency). Better quality (GPT-4o) but not worth cost.
- **Anthropic Claude:** Similar costs, no EU hosting, smaller ecosystem. Better reasoning but vendor lock-in.
- **OpenAI API (Direct):** Not DSGVO-compliant (US data), no SLA, higher hallucination rate vs local models.

**Trade-offs:**
- ⚠️ Lower quality than GPT-4o for very complex tasks (acceptable trade-off)
- ⚠️ Requires GPU (12GB VRAM recommended, RTX 3060 minimum)
- ⚠️ Manual model updates (no auto-updates like cloud APIs)
- ✅ No API rate limits, unlimited usage
- ✅ Privacy by design (data never leaves local infrastructure)

**Models Used:**
- `llama3.2:3b` - Query understanding, entity extraction (105 tokens/s on GPU)
- `llama3.2:8b` - Answer generation, complex reasoning (85 tokens/s on GPU)
- `qwen2.5:7b` - Alternative for complex reasoning (70 tokens/s on GPU)
- `qwen3:0.6b` - Ultra-lightweight fallback (150 tokens/s, 0.5GB RAM)
- `nomic-embed-text` - Embeddings (768-dim, 274MB model)

---

### LangChain-Ollama: 1.0.0 | Ollama Integration for LangChain

**Version:** `^1.0.0` (latest stable, requires ollama>=0.6.0)

**Rationale:**
- Native integration between LangChain/LangGraph and Ollama
- Async client support for non-blocking LLM calls
- Streaming response support (SSE in Sprint 14)
- Type-safe interfaces (Pydantic models)

**Upgrade Path:**
- Sprint 1-10: `langchain-ollama 0.x` with `ollama 0.5.x`
- Sprint 11+: `langchain-ollama 1.0.0` with `ollama >=0.6.0`
- Breaking change: Stricter version requirements (improved stability)

---

### LangChain-Core: 1.0.0 | LangChain Base Library

**Version:** `^1.0.0` (required by langchain-ollama 1.0.0)

**Rationale:**
- Core abstractions for LLMs, prompts, chains, tools
- Type-safe interfaces (Pydantic v2 compatibility)
- Foundation for LangGraph state management
- Active development, weekly releases

**Note:** We use LangChain minimally (mainly for Ollama integration). Primary orchestration is LangGraph (which builds on LangChain-Core).

---

## VECTOR DATABASES

### Qdrant: ~1.11.0 | High-Performance Vector Search (ADR-004)

**Version:** `~1.11.0` (pin to 1.11.x, compatible with Qdrant server v1.11.0)

**Rationale:**
- **Best-in-Class Performance:** 3ms latency at 1M embeddings, sub-10ms at production scale
- **Compression:** 24x via asymmetric quantization (Scalar + Product Quantization)
- **Self-Hosting:** No vendor lock-in, full control over infrastructure, Qdrant Cloud option available
- **Advanced Features:** Metadata filtering, RBAC, multi-tenancy, distributed replication
- **Ecosystem:** Native support in LangGraph, CrewAI, LlamaIndex

**Alternatives Rejected:**
- **Pinecone:** Vendor lock-in (no self-hosting), higher costs at scale, less control. Excellent performance but not worth trade-offs.
- **Weaviate:** Native hybrid search (vector + BM25) but slower performance, higher memory footprint, less mature quantization. Jack-of-all-trades approach.
- **ChromaDB:** Best for prototyping (pip install), MCP server available, but not production-scale (no distributed replication, limited to millions not billions of vectors).

**Trade-offs:**
- ⚠️ No managed service (if self-hosting, need ops expertise)
- ⚠️ Requires tuning for optimal performance (quantization, indexing)
- ✅ Open source (Apache 2.0 license)
- ✅ Active community (21K+ GitHub stars)

**Configuration:**
- Collection: `aegis_documents` (768-dim nomic-embed-text)
- Quantization: Asymmetric (24x compression)
- HNSW Index: M=16, ef_construct=100 (balanced speed/accuracy)

---

### LlamaIndex-Vector-Stores-Qdrant: 0.8.6 | Qdrant Integration for LlamaIndex

**Version:** `^0.8.6` (requires llama-index-core >=0.13.0)

**Rationale:**
- Used by `scripts/index_documents.py` for batch ingestion
- Simplifies vector upsert operations
- Compatible with LlamaIndex document loaders

**Note:** LlamaIndex used ONLY for ingestion scripts, not core RAG pipeline (which uses native Qdrant client).

---

## GRAPH DATABASES

### Neo4j: 5.14.0 | Graph Database for LightRAG & Graphiti (ADR-005)

**Version:** `^5.14.0` (Python driver, compatible with Neo4j server 5.24)

**Rationale:**
- **Industry Standard:** Most mature graph database, Cypher query language
- **LightRAG Backend:** Knowledge graph storage (entities, relationships, communities)
- **Graphiti Backend:** Bi-temporal episodic memory (valid-time + transaction-time)
- **Performance:** Optimized for traversal queries, APOC procedures for graph algorithms

**Alternatives Rejected:**
- **ArangoDB:** Multi-model (document + graph) but weaker ecosystem for RAG use cases
- **Neo4j Aura (Cloud):** Vendor lock-in, costs vs self-hosting
- **TigerGraph:** Better for massive graphs (billions of edges) but overkill for RAG

**Configuration:**
- Server: Neo4j 5.24-community (Docker)
- Memory: 512MB heap initial, 1GB max (sufficient for 1000s of documents)
- APOC Plugins: Core procedures for graph analytics

---

## KNOWLEDGE GRAPH & GRAPH RAG

### LightRAG-HKU: 1.4.9 | Knowledge Graph Construction (ADR-005)

**Version:** `^1.4.9` (latest stable)

**Rationale:**
- **Cost-Efficient:** Lower LLM token usage than Microsoft GraphRAG (faster entity extraction)
- **Incremental Updates:** No full re-index needed (unlike Microsoft GraphRAG static approach)
- **Dual-Level Retrieval:** Low-level (entity matching) + High-level (topic/community matching)
- **Developer Experience:** Built-in web UI, API server, Docker-ready
- **Benchmarks:** Comparable accuracy to Microsoft GraphRAG at ~1/10th cost

**Alternatives Rejected:**
- **Microsoft GraphRAG:** Mature (23.8K stars), excellent docs, Azure integration, but extremely high indexing costs (intensive LLM usage), static graph structure (full re-index on updates), no temporal awareness.
- **LlamaIndex PropertyGraph:** Native integration with LlamaIndex, flexible schema, but less optimized than dedicated GraphRAG systems, younger development.
- **No GraphRAG (Vector + Graphiti only):** Simpler architecture, lower costs, but no community detection, no global search capability.

**Trade-offs:**
- ⚠️ Younger project (less mature than Microsoft GraphRAG)
- ⚠️ Smaller community (fewer resources)
- ⚠️ Less enterprise features
- ✅ Abstraction layer allows swap to Microsoft GraphRAG if needed
- ✅ Active development, responsive maintainers

**Model Switch (Sprint 11):**
- **Sprint 5-10:** qwen3:0.6b (ultra-lightweight, 0.5GB RAM, 150 tokens/s)
- **Sprint 11+:** llama3.2:3b (better structured output, 105 tokens/s, +20% accuracy)
- Reason: JSON parsing errors with qwen3 entity extraction

---

### NetworkX: 3.2 | Graph Algorithms for LightRAG

**Version:** `^3.2` (latest stable)

**Rationale:**
- Pure Python graph library for analysis (no Neo4j dependency)
- Used by LightRAG for community detection preprocessing
- Leiden algorithm implementation (via graspologic)

---

### Graspologic: 3.4.1 | Graph Statistics & Community Detection

**Version:** `^3.4.1` (latest stable)

**Rationale:**
- **Leiden Algorithm:** Better quality than Louvain (higher modularity), faster convergence
- **Hierarchical Structures:** Detects multi-level communities for LightRAG high-level retrieval
- **Microsoft Research:** Maintained by Microsoft, well-tested

**Note:** Sprint 11 optimized community detection with parallel processing (2.5x speedup: 20s → 8s for 933 docs)

---

## TEMPORAL MEMORY

### Graphiti-Core: 0.3.0 | Episodic Temporal Memory (ADR-006)

**Version:** `^0.3.0` (latest stable)

**Rationale:**
- **Unique Capability:** Bi-temporal graph storage (valid-time + transaction-time)
- **Temporal Queries:** "What did system know on date X?" (point-in-time queries)
- **Knowledge Evolution:** Track how facts change over time
- **Relationship Tracking:** Entity connections evolve with temporal context
- **No Competitors:** Only library offering bi-temporal memory for LLM systems

**Alternatives Rejected:**
- **LangChain Memory:** Simpler but no temporal awareness, no relationship tracking
- **Custom Neo4j Solution:** Would require significant development, Graphiti provides turnkey solution
- **SQL-based Memory:** Poor for graph traversal, no semantic search

**Trade-offs:**
- ⚠️ Steep learning curve (bi-temporal concepts complex)
- ⚠️ Newer library (less battle-tested than LangChain memory)
- ⚠️ API breaking changes (Sprint 12: constructor signature changed in 0.3.0)
- ✅ Unique temporal capabilities justify complexity
- ✅ Built on Neo4j (proven graph backend)

**Sprint 12 Issue (TD-27):**
- graphiti-core 0.3.0 changed constructor (no longer accepts neo4j params directly)
- 18 tests skipped pending fix in Sprint 13.2

---

## MEMORY & CACHING

### Redis: 5.0.0 | Short-Term Memory & State Persistence (ADR-006)

**Version:** `^5.0.0` with asyncio extras

**Rationale:**
- **Layer 1 Memory:** <10ms latency for session state, recent context
- **LangGraph Checkpointer:** Durable state persistence (langgraph-checkpoint-redis 0.1.2)
- **Caching:** BM25 index persistence, community detection results
- **Async Support:** Native async/await for non-blocking operations

**Configuration:**
- Server: Redis 7.4-alpine (Docker)
- Database: 0 (default)
- TTL: 1-24 hours (configurable per use case)
- Memory: 100MB typical usage

---

### LangGraph-Checkpoint-Redis: 0.1.2 | Redis Checkpointer for LangGraph

**Version:** `^0.1.2` (latest stable)

**Rationale:**
- Durable state persistence for LangGraph workflows
- Conversation resumption after restart/crash
- Redis backend for high-speed checkpoint save/load
- Sprint 12: Added proper async cleanup (`aclose()` method) to prevent event loop warnings

**Sprint 12 Enhancement:**
- Created `src/agents/checkpointer.py` with `RedisCheckpointSaver` class
- Proper async resource management (`aclose()` in fixtures)
- Eliminated 9+ pytest event loop warnings

---

## WEB FRAMEWORK

### FastAPI: 0.115.0 | Modern Python Web Framework (ADR-008)

**Version:** `^0.115.0` (latest stable)

**Rationale:**
- **Performance:** Fastest Python framework (Starlette/Uvicorn async foundation)
- **Auto Documentation:** OpenAPI/Swagger UI generated automatically
- **Type Safety:** Pydantic v2 integration for request/response validation
- **Async Native:** Native async/await for I/O-bound operations (LLM calls, DB queries)
- **Ecosystem:** Best integration with AI/ML libraries (LangChain, LlamaIndex)

**Alternatives Rejected:**
- **Django:** Overkill for API-only backend, slower than FastAPI, heavier (ORM, admin panel not needed). Better for monolithic apps.
- **Flask:** Simpler but no native async support, manual validation, no auto docs. Good for simple APIs but not production RAG systems.
- **Node.js/Express:** Single language (JS frontend + backend) but weaker AI/ML ecosystem, less LLM library support, poor NumPy/Pandas integration.

**Trade-offs:**
- ⚠️ Younger than Django/Flask (less mature)
- ⚠️ Less "batteries included" (need to add middleware)
- ✅ Best performance/features for AI/ML APIs
- ✅ Auto-generated interactive docs (huge DX win)

**Middleware:**
- CORS: `fastapi.middleware.cors`
- Rate Limiting: `slowapi` (10/min search, 5/hour ingest)
- Metrics: `prometheus-client` (Prometheus integration)

---

### Uvicorn: 0.30.0 | ASGI Server for FastAPI

**Version:** `^0.30.0` with `[standard]` extras

**Rationale:**
- Lightning-fast ASGI server (async I/O)
- HTTP/1.1 and WebSocket support
- Graceful shutdown handling
- Production-ready (used by major companies)

**Standard Extras:**
- `uvloop` (faster event loop on Linux)
- `httptools` (faster HTTP parsing)
- `websockets` (WebSocket support for SSE in Sprint 14)

---

### Pydantic: 2.9.0 | Data Validation & Settings

**Version:** `^2.9.0` (Pydantic v2)

**Rationale:**
- Type-safe data validation (FastAPI, LangChain integration)
- Settings management via environment variables
- JSON schema generation (OpenAPI docs)
- Performance: Pydantic v2 is 5-50x faster than v1 (Rust core)

**Upgrade:** Sprint 2 migrated from Pydantic v1 → v2 (breaking changes, worth it for performance)

---

### Pydantic-Settings: 2.5.0 | Environment Configuration

**Version:** `^2.5.0` (Pydantic v2 compatible)

**Rationale:**
- 12-factor app configuration (environment variables)
- Type-safe settings validation
- `.env` file support (`python-dotenv` integration)
- Secrets management (`SecretStr` type)

**Configuration:**
- `src/core/config.py` - Centralized settings class
- `.env` file for local development
- Environment variables for production

---

## SEARCH & RETRIEVAL

### Rank-BM25: 0.2.2 | Keyword Search Algorithm (ADR-009)

**Version:** `^0.2.2` (latest stable)

**Rationale:**
- BM25 is gold standard for keyword-based retrieval
- Complements vector search (catches exact matches)
- Simple API, no external dependencies
- Pickle persistence for index storage

**Alternatives Rejected:**
- **Elasticsearch:** Overkill (requires separate service), better for full-text search at massive scale. BM25 sufficient for RAG use case.
- **Whoosh:** Pure Python but slower, less active development
- **Tantivy (Rust):** Faster but requires Rust compilation, higher complexity

**Configuration:**
- Tokenization: Custom (lowercase, split, stemming)
- Index: Pickle file (`data/bm25_index.pkl`)
- Update: Re-fit on document ingestion

---

### Sentence-Transformers: 3.3.1 | Cross-Encoder Reranking

**Version:** `^3.3.1` (latest stable, HuggingFace compatibility)

**Rationale:**
- **Cross-Encoder Reranking:** Evaluates query-document pairs directly (better than bi-encoder cosine similarity)
- **Quality Boost:** +15-20% precision improvement for only +50ms latency
- **Model:** `ms-marco-MiniLM-L-6-v2` (Microsoft, optimized for search reranking)
- **HuggingFace Integration:** Easy model downloads, community support

**Alternatives Rejected:**
- **OpenAI Embeddings Similarity:** Weaker than cross-encoder for reranking, cloud dependency
- **Custom Reranking Model:** Too much effort, ms-marco pretrained model excellent
- **No Reranking:** Simpler but -15-20% precision (not acceptable for production)

**Model Details:**
- Architecture: MiniLM (6 layers, lightweight)
- Training: MS MARCO dataset (850K query-document pairs)
- Latency: ~5ms per pair, batch processing for top-10 results

---

## EVALUATION

### RAGAS: 0.3.7 | RAG Evaluation Framework

**Version:** `^0.3.7` (better Ollama support)

**Rationale:**
- **Objective Metrics:** Context Precision, Context Recall, Faithfulness, Answer Relevancy
- **Ollama Support:** RAGAS 0.3.7 improved compatibility with local LLMs
- **Regression Detection:** Baseline score 0.88 (excellent), track quality over time
- **Research-Backed:** Based on recent RAG evaluation research

**Alternatives Rejected:**
- **TruLens:** More comprehensive but heavier, requires MLflow setup. Overkill for current needs.
- **LangSmith Evaluation:** Good but vendor lock-in, requires LangSmith cloud account
- **Manual Evaluation:** Not scalable, subjective

**Metrics Baseline (Sprint 3):**
- Context Precision: 0.91
- Context Recall: 0.87
- Faithfulness: 0.88
- **Average:** 0.88 (excellent)

---

### Datasets: 4.0.0 | HuggingFace Datasets for Evaluation

**Version:** `^4.0.0` (required by ragas 0.3.7)

**Rationale:**
- Load evaluation datasets (MS MARCO, Natural Questions)
- Compatible with RAGAS evaluation pipeline
- Efficient data loading (memory-mapped, fast iteration)

---

## DOCUMENT INGESTION

### LlamaIndex-Core: 0.14.3 | Document Loading & Chunking

**Version:** `^0.14.3` (upgraded for newer ollama packages)

**Rationale:**
- Best-in-class document loaders (PDF, TXT, MD, DOCX, etc.)
- Adaptive chunking strategies (paragraph, heading, function, sentence)
- Node/Document abstractions for RAG pipelines
- Used ONLY for ingestion scripts, not core RAG (which uses native clients)

**Upgrade Path:**
- Sprint 1-10: `llama-index-core 0.11.x`
- Sprint 11+: `llama-index-core 0.14.3` (compatibility with ollama >=0.5.1)

---

### LlamaIndex-LLMs-Ollama: 0.8.0 | Ollama Integration for LlamaIndex

**Version:** `^0.8.0` (requires core >=0.14.3, ollama >=0.5.1)

**Rationale:**
- Ollama LLM integration for LlamaIndex ingestion
- Async client support
- Streaming response support

---

### LlamaIndex-Embeddings-Ollama: 0.8.3 | Embeddings via Ollama

**Version:** `^0.8.3` (requires core >=0.13.0, ollama >=0.3.1)

**Rationale:**
- nomic-embed-text embeddings via Ollama
- Batch embedding support
- No upper version limit (flexible compatibility)

---

### LlamaIndex-Readers-File: 0.5.4 | File Format Loaders

**Version:** `^0.5.4` (latest stable)

**Rationale:**
- PDF, DOCX, MD, TXT loaders
- Used by `scripts/index_documents.py`
- Metadata extraction (filename, path, creation date)

**Supported Formats:**
- PDF: PyPDF2 backend
- DOCX: python-docx backend (via docx2txt 0.9)
- Markdown: Native parser
- Text: UTF-8 encoding

---

## UI FRAMEWORK

### Gradio: 5.49.0 | Rapid Prototyping UI (Sprint 10)

**Version:** `^5.49.0` (latest stable)

**Rationale:**
- **Fastest Prototyping:** Chat UI in <1 day
- **Built-in Components:** Chatbot, file upload, progress bars, markdown rendering
- **FastAPI Integration:** Easy backend connection
- **Zero Frontend Code:** Pure Python (no React/Vue knowledge needed)

**Alternatives Rejected:**
- **Streamlit:** Similar to Gradio but weaker for chat interfaces, less interactive
- **React + Next.js:** Best for production but 10x longer development time
- **Vue.js:** Good framework but no RAG-specific templates

**Trade-offs:**
- ⚠️ Limited customization (CSS constraints)
- ⚠️ No native SSE streaming (polling workaround)
- ⚠️ Poor styling options (moved to Tailwind in Sprint 14)
- ✅ Perfect for MVP (fast iteration)
- ✅ Easy handoff to non-frontend developers

**Migration Plan (Sprint 14):**
- Replace Gradio with React + Next.js 14 + TypeScript
- Add SSE streaming, dark mode, responsive design
- Production-grade UI polish

---

## UTILITIES

### Python-Dotenv: 1.0.0 | Environment Variable Management

**Version:** `^1.0.0` (latest stable)

**Rationale:**
- 12-factor app configuration
- `.env` file support for local development
- Pydantic-settings integration
- Prevents hardcoded secrets in code

---

### Tenacity: >=8.1.0,<9.0.0 | Retry Logic with Exponential Backoff

**Version:** `>=8.1.0,<9.0.0` (downgraded for graphiti-core compatibility in Sprint 8)

**Rationale:**
- Retry transient failures (network errors, API timeouts)
- Exponential backoff (prevents thundering herd)
- Configurable stop conditions (max attempts, max delay)
- Used for Ollama calls, database operations, API requests

**Configuration:**
- Max attempts: 3
- Backoff: Exponential (2^n seconds)
- Retry on: Network errors, timeouts, 5xx HTTP codes

---

### Structlog: 24.4.0 | Structured Logging

**Version:** `^24.4.0` (latest stable)

**Rationale:**
- JSON-formatted logs (parseable by log aggregators)
- Context binding (request IDs, user IDs)
- Performance: Faster than standard Python logging
- Production-ready (used by major companies)

**Log Levels:**
- DEBUG: Development details
- INFO: Request/response logs
- WARNING: Deprecated features, slow queries
- ERROR: Exceptions, failures
- CRITICAL: System failures

---

### HTTPx: 0.27.0 | Async HTTP Client

**Version:** `^0.27.0` (latest stable)

**Rationale:**
- Async HTTP requests (non-blocking)
- HTTP/2 support (faster than requests library)
- Timeout handling, retry logic
- Used for external API calls (MCP servers)

---

### AIOFiles: 24.1.0 | Async File I/O

**Version:** `^24.1.0` (latest stable)

**Rationale:**
- Non-blocking file operations
- Critical for document upload (large files)
- Prevents event loop blocking

---

### PyYAML: 6.0.0 | YAML Configuration

**Version:** `^6.0.0` (latest stable, CVE-2020-14343 patched)

**Rationale:**
- Configuration files (docker-compose.yml, CI/CD)
- Human-readable format
- Safer than JSON for nested configs

---

### Python-Multipart: 0.0.20 | File Upload Support

**Version:** `^0.0.20` (updated for Gradio 5.x compatibility)

**Rationale:**
- FastAPI file upload dependency
- Multipart form data parsing
- Required by Gradio file upload component

---

### NumPy: 1.26.0 | Numerical Operations

**Version:** `^1.26.0` (latest stable)

**Rationale:**
- Vector operations in memory consolidation
- Embedding manipulation (normalization, similarity)
- Efficient array processing

---

### APScheduler: 3.10.0 | Cron-Based Scheduling

**Version:** `^3.10.0` (latest stable)

**Rationale:**
- Memory consolidation pipeline (hourly jobs)
- Background task scheduling
- Persistent job store (Redis-backed)

**Jobs:**
- `consolidate_redis_to_qdrant`: Every 1 hour
- `consolidate_conversations_to_graphiti`: Every 1 hour
- `cleanup_old_sessions`: Every 24 hours

---

## MONITORING & OBSERVABILITY

### Prometheus-Client: 0.21.0 | Metrics Collection

**Version:** `^0.21.0` (latest stable)

**Rationale:**
- Production-grade metrics (request rate, latency, errors)
- Prometheus scraping endpoint (`/metrics`)
- Grafana dashboard integration (Sprint 12)

**Metrics Tracked:**
- `http_requests_total` (counter)
- `http_request_duration_seconds` (histogram)
- `llm_tokens_generated_total` (counter)
- `vector_search_latency_seconds` (histogram)

---

### SlowAPI: 0.1.9 | Rate Limiting

**Version:** `^0.1.9` (latest stable)

**Rationale:**
- Prevent API abuse (DDoS protection)
- Per-endpoint rate limits
- Redis storage backend (distributed rate limiting)

**Limits:**
- `/api/v1/search`: 10/min
- `/api/v1/ingest`: 5/hour
- `/api/v1/chat`: 20/min

---

## SECURITY

### Python-Jose: 3.3.0 | JWT Token Handling

**Version:** `^3.3.0` with `[cryptography]` extras

**Rationale:**
- JWT authentication for API endpoints
- Cryptographic signing (RS256, HS256)
- Token expiry validation

**Configuration:**
- Secret: Environment variable (`JWT_SECRET`)
- Algorithm: HS256 (symmetric)
- Expiry: 24 hours

---

### Passlib: 1.7.4 | Password Hashing

**Version:** `^1.7.4` with `[bcrypt]` extras

**Rationale:**
- Bcrypt hashing (industry standard)
- Secure password storage (no plaintext)
- Slow hashing (brute-force resistant)

**Configuration:**
- Algorithm: bcrypt
- Rounds: 12 (balance security/performance)

---

## DEVELOPMENT TOOLS (dev dependencies)

### Pytest: 8.0.0 | Testing Framework

**Version:** `^8.0.0` (latest stable)

**Rationale:**
- Industry-standard Python testing
- Fixture system (session/function scopes)
- Plugin ecosystem (pytest-asyncio, pytest-cov, pytest-mock)
- Marker system (unit, integration, e2e)

---

### Pytest-Asyncio: 0.23.0 | Async Test Support

**Version:** `^0.23.0` (latest stable)

**Rationale:**
- Async test execution (`@pytest.mark.asyncio`)
- Event loop management (critical for Sprint 13 TD-26 fix)
- Async fixture support

**Configuration:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

### Pytest-Cov: 5.0.0 | Code Coverage

**Version:** `^5.0.0` (latest stable)

**Rationale:**
- Coverage reports (term, HTML, XML)
- CI integration (Codecov, Coveralls)
- Current: >70% overall, >80% critical paths

---

### Pytest-Mock: 3.14.0 | Mocking Support

**Version:** `^3.14.0` (latest stable)

**Rationale:**
- Simplified mocking API (cleaner than unittest.mock)
- Fixture-based mocking
- Used ONLY for unit tests (not E2E per ADR-014)

---

### Ruff: 0.14.0 | Fast Python Linter

**Version:** `^0.14.0` (upgraded for Gradio 5.x compatibility)

**Rationale:**
- 10-100x faster than Flake8/Pylint (Rust implementation)
- Combines multiple tools (isort, pyupgrade, flake8-bugbear)
- Auto-fix support (--fix flag)

**Checks Enabled:**
- pycodestyle (E, W)
- pyflakes (F)
- isort (I)
- pep8-naming (N)
- pyupgrade (UP)
- flake8-bugbear (B)
- flake8-comprehensions (C4)
- flake8-simplify (SIM)

---

### Black: 24.8.0 | Code Formatter

**Version:** `^24.8.0` (latest stable)

**Rationale:**
- Opinionated formatting (no config needed)
- Consistent code style across team
- Fast (Rust core in recent versions)

**Configuration:**
- Line length: 100 (matches Ruff)
- Target: Python 3.11

---

### MyPy: 1.11.0 | Static Type Checker

**Version:** `^1.11.0` (latest stable)

**Rationale:**
- Catch type errors before runtime
- Gradual typing (optional type hints)
- IDE integration (VS Code, PyCharm)

**Configuration:**
- `check_untyped_defs = true`
- `no_implicit_optional = true`
- Ignore imports for untyped libraries (qdrant, ollama, etc.)

---

### Bandit: 1.7.9 | Security Linter

**Version:** `^1.7.9` (latest stable)

**Rationale:**
- Security vulnerability scanning
- Detects common issues (hardcoded secrets, SQL injection, weak crypto)
- CI integration (fail on high-severity issues)

**Checks:**
- Hardcoded passwords/secrets
- Unsafe YAML loading (CVE-2020-14343)
- SQL injection patterns
- Weak cryptography (MD5, DES)

---

## VERSION CONSTRAINTS SUMMARY

### Strict Pins (~)
- `qdrant-client ~1.11.0` - Server compatibility critical

### Range Constraints (>=X,<Y)
- `ollama >=0.6.0,<1.0.0` - langchain-ollama 1.0.0 requirement
- `tenacity >=8.1.0,<9.0.0` - graphiti-core compatibility

### Flexible (^)
- Most libraries use caret (^) for SemVer compatibility
- Allows minor/patch updates (e.g., `^2.9.0` → `2.9.x`, `2.10.x`)

---

## SPRINT 16 NEW DEPENDENCIES

### python-pptx: 1.0.2 | PowerPoint Document Extraction (Feature 16.5)

**Version:** `^1.0.2` (latest stable)

**Rationale:**
- **OMNITRACKER Use Case:** OMNITRACKER corpus contains many PPTX training materials
- **Mature Library:** 10+ years development, battle-tested, widely used
- **Simple API:** Easy integration with existing LlamaIndex loaders
- **Comprehensive:** Extracts text, tables, speaker notes, slide titles
- **Small Footprint:** <1MB dependency, no heavy dependencies

**Alternatives Rejected:**
- **python-pptx-fork:** Less maintained, no additional features
- **Apache POI (Java):** Requires JVM, heavyweight, cross-language complexity
- **Manual XML parsing:** Too low-level, error-prone, not worth effort

**Trade-offs:**
- ⚠️ No embedded image OCR (would need pytesseract)
- ⚠️ No chart data extraction (only text)
- ✅ Sufficient for text-based RAG use case
- ✅ Fast extraction (<100ms per slide)

**Usage:**
```python
from pptx import Presentation

prs = Presentation('training.pptx')
for slide in prs.slides:
    for shape in slide.shapes:
        if hasattr(shape, "text"):
            yield shape.text
```

---

### Pydantic v2 ConfigDict Migration (Feature 16.8)

**Version:** `^2.9.0` (no version change, API migration only)

**Rationale:**
- **Eliminate Deprecation Warnings:** `@root_validator` deprecated in Pydantic v2
- **Future-Proof:** ConfigDict is canonical approach in Pydantic v2+
- **Cleaner Syntax:** Model configuration in single dict vs scattered decorators
- **No Performance Impact:** Already using Pydantic v2 core (5-50x faster than v1)

**Migration:** 21 models updated from `@root_validator` to `ConfigDict`

**Before (Sprint 1-15):**
```python
from pydantic import BaseModel, root_validator

class QueryRequest(BaseModel):
    query: str
    max_results: int = 10

    @root_validator  # Deprecated in Pydantic v2
    def validate_query(cls, values):
        if not values.get("query"):
            raise ValueError("Query cannot be empty")
        return values
```

**After (Sprint 16):**
```python
from pydantic import BaseModel, model_validator

class QueryRequest(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=False
    )

    query: str
    max_results: int = 10

    @model_validator(mode='after')  # Pydantic v2 canonical
    def validate_query(self):
        if not self.query:
            raise ValueError("Query cannot be empty")
        return self
```

**Benefits:**
- ✅ No deprecation warnings in logs
- ✅ Future-proof for Pydantic v3
- ✅ Better IDE auto-completion
- ✅ Cleaner model definitions

---

**Last Updated:** 2025-10-28 (Post-Sprint 16)
**Total Dependencies:** 61+ (production + dev)
**Dependency Health:** All actively maintained, no critical CVEs
**Sprint 16 Additions:** python-pptx (1.0.2), Pydantic v2 ConfigDict migration
