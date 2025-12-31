# DECISION LOG - AEGIS RAG

**Purpose:** Chronological list of major architecture and technology decisions
**Format:** Date | Decision | Rationale (2-3 sentences max)
**Last Updated:** 2025-12-01 (Sprint 34)

---

## SPRINT 1-2: FOUNDATION & VECTOR SEARCH

### 2025-01-15 | LangGraph for Multi-Agent Orchestration (ADR-001)
**Decision:** Use LangGraph as primary orchestration framework over CrewAI, AutoGen, LlamaIndex Workflows.
**Rationale:** Best balance of control (explicit graph definition), production features (LangSmith tracing, state persistence), and flexibility (conditional routing, parallel execution). Higher learning curve justified by better debuggability and enterprise maturity (Klarna, Uber, Replit).

### 2025-01-15 | Ollama-Only LLM Strategy (ADR-002)
**Decision:** 100% Ollama for development and production, zero cloud LLM usage.
**Rationale:** $0 costs (saves $18K-24K/year vs Azure OpenAI), offline-capable for air-gapped deployment, DSGVO-compliant by design. Modern models (llama3.2, qwen2.5) provide sufficient quality for 90%+ use cases. No vendor lock-in.

### 2025-01-15 | Python + FastAPI for Backend (ADR-008)
**Decision:** Python 3.11+ with FastAPI framework for REST API.
**Rationale:** Best AI/ML ecosystem (LangChain, LlamaIndex all Python-first), FastAPI is fastest Python framework (Starlette/Uvicorn), auto OpenAPI docs, native async/await for I/O-bound operations. Type safety via Pydantic v2.

### 2025-01-15 | Hybrid Vector-Graph Retrieval (ADR-003)
**Decision:** Combine Vector Search (Qdrant) + Graph RAG (Neo4j/LightRAG) + BM25 keyword search with RRF fusion.
**Rationale:** Research shows 40-60% better relevance vs pure vector or pure graph. Vector excels at semantic similarity, graph at multi-hop reasoning, BM25 at keyword matching. Reciprocal Rank Fusion combines strengths without score normalization.

### 2025-01-15 | Qdrant as Primary Vector Database (ADR-004)
**Decision:** Qdrant over Pinecone, Weaviate, ChromaDB for vector storage.
**Rationale:** Best-in-class performance (3ms latency at 1M embeddings), 24x compression via asymmetric quantization, self-hosting option (no vendor lock-in), advanced filtering, RBAC, multi-tenancy. Active community (21K+ GitHub stars).

### 2025-01-15 | Reciprocal Rank Fusion for Hybrid Search (ADR-009)
**Decision:** Use RRF algorithm (k=60) to combine vector, BM25, and graph rankings.
**Rationale:** Score-agnostic (no normalization needed), robust across query types, research-validated (Cormack et al. 2009). Simpler than weighted average (needs tuning) or CombSUM (complex). Formula: score = sum(1/(k+rank)).

---

## SPRINT 3-4: ADVANCED RETRIEVAL & ORCHESTRATION

### 2025-01-20 | Cross-Encoder Reranking
**Decision:** Add sentence-transformers/ms-marco-MiniLM-L-6-v2 reranking after hybrid search.
**Rationale:** +15-20% precision improvement for only +50ms latency. Cross-encoder evaluates query-document pairs directly (better than bi-encoder similarity). Massive quality boost for low overhead.

### 2025-01-20 | RAGAS Evaluation Framework
**Decision:** Integrate RAGAS 0.3.7 for RAG quality metrics (context precision, recall, faithfulness).
**Rationale:** Objective measurement of retrieval quality prevents regression. RAGAS 0.3.7 has better Ollama support. Baseline score: 0.88 (excellent). Enables continuous quality monitoring.

### 2025-01-21 | Security Hardening: MD5 → SHA-256
**Decision:** Replace MD5 hashing for document IDs with SHA-256.
**Rationale:** MD5 vulnerable (CVE-2010-4651), SHA-256 is cryptographically secure. Critical for production deployment. Also added rate limiting (slowapi), input sanitization (Pydantic), path traversal protection.

### 2025-01-22 | LangGraph Multi-Agent System (4 Agents)
**Decision:** Implement Router, Vector, Graph, Memory agents with conditional routing.
**Rationale:** Specialization improves quality (each agent optimized for its task). Router selects optimal strategy per query type. Parallel execution via Send API reduces latency. State management handles complex workflows.

---

## SPRINT 5-6: GRAPH RAG & HYBRID FUSION

### 2025-01-15 | LightRAG over Microsoft GraphRAG (ADR-005)
**Decision:** Use LightRAG 1.4.9 for knowledge graph construction instead of Microsoft GraphRAG.
**Rationale:** Lower token costs (less intensive LLM usage), incremental updates (no full re-index), dual-level retrieval (entity + topic matching). Microsoft GraphRAG is expensive and static (full re-index on updates). Comparable accuracy at 1/10th cost.

### 2025-01-25 | qwen3:0.6b for Entity Extraction (Later switched to llama3.2:3b in Sprint 11)
**Decision:** Use ultra-lightweight qwen3:0.6b (0.5GB RAM) for LightRAG entity extraction.
**Rationale:** Fast inference (~500ms/doc), acceptable quality for entity detection, minimal memory footprint. Later switched to llama3.2:3b in Sprint 11 for better structured output quality (+20% accuracy, traded speed for reliability).

### 2025-01-26 | Leiden Algorithm for Community Detection
**Decision:** Use graspologic's Leiden algorithm for graph community detection.
**Rationale:** Better quality than Louvain (higher modularity), faster convergence, detects hierarchical structures. Supports LightRAG's high-level topic-based retrieval. Optimized in Sprint 11 with parallel processing (2.5x speedup).

### 2025-01-27 | Unified Retrieval Router (Vector/Graph/Hybrid/Adaptive)
**Decision:** Single router with 4 strategies: vector-only, graph-only, hybrid, adaptive.
**Rationale:** Query classification determines optimal retrieval path. Vector for semantic similarity, graph for relationships, hybrid for complex queries. Parallel execution + RRF fusion. Adaptive routing (ML-based) planned for Sprint 13.

---

## SPRINT 7-9: TEMPORAL MEMORY & MCP

### 2025-01-15 | 3-Layer Memory Architecture (ADR-006)
**Decision:** Redis (Layer 1) + Qdrant (Layer 2) + Graphiti + Neo4j (Layer 3).
**Rationale:** Optimize for different use cases: Redis <10ms for short-term (session state, recent context), Qdrant <50ms for semantic long-term, Graphiti <200ms for episodic temporal (relationships, evolution tracking). Memory router selects optimal layer per query type.

### 2025-01-28 | Graphiti for Episodic Temporal Memory
**Decision:** Use graphiti-core 0.3.0 for bi-temporal graph storage.
**Rationale:** Unique capability: bi-temporal queries (valid-time + transaction-time). Track knowledge evolution over time, "what did system know on date X?" No competitors offer this. Built on Neo4j backend for graph traversal.

### 2025-01-29 | Memory Consolidation Pipeline (APScheduler)
**Decision:** Automated consolidation: Redis → Qdrant (hourly), Conversations → Graphiti (hourly).
**Rationale:** Prevents Redis memory bloat, archives old conversations to semantic/episodic layers. APScheduler runs background jobs without manual intervention. Configurable thresholds (e.g., >1 hour old, >3 accesses).

### 2025-01-15 | MCP Client (NOT Server) Integration (ADR-007)
**Decision:** Implement MCP Client to consume external MCP tools (Filesystem, GitHub, Slack). No MCP Server (we don't provide tools to others).
**Rationale:** Access 500+ community MCP servers without custom integrations. Standardized tool protocol (OpenAI, Google, Microsoft, Anthropic support). Action Agent can call external tools. MCP Server deferred (unclear use case, added complexity).

---

## SPRINT 10-12: UI, OPTIMIZATION, PRODUCTION

### 2025-02-01 | Gradio for MVP UI
**Decision:** Use Gradio 5.49.0 for rapid prototyping chat interface.
**Rationale:** Fastest path to UI (<1 day implementation), built-in components (chatbot, file upload), easy FastAPI integration. Trade-off: limited customization, no SSE streaming (polling workaround). Planned migration to React + Next.js 14 in Sprint 14 for production polish.

### 2025-02-03 | GPU Acceleration (MANDATORY for Production)
**Decision:** NVIDIA GPU required for production deployment (tested on RTX 3060).
**Rationale:** 15-20x speedup (7 → 105 tokens/s for llama3.2:3b). CPU-only unusable for production (<2s → <30s response time). GPU makes Ollama-only strategy viable. Verified on RTX 3060 (52.7% VRAM utilization, 105 tokens/s).

### 2025-02-04 | Unified Embedding Service (Sprint 11)
**Decision:** Single EmbeddingService with shared LRU cache (10K entries) across all components.
**Rationale:** Eliminates fragmented embedding calls (vector, graph, memory had separate services). 60% cache hit rate, memory reduced from 1.5GB → 600MB. Simplifies codebase, reduces Ollama API load.

### 2025-02-05 | Parallel Ingestion Pipeline (Sprint 11)
**Decision:** Parallel indexing of Qdrant, BM25, LightRAG (was sequential).
**Rationale:** 3x speedup (30s → 10s for 100 documents). Progress tracking for UX. Async/await enables concurrent database operations. Critical for production-scale document ingestion.

### 2025-02-06 | Redis Checkpointer for LangGraph State (Sprint 11)
**Decision:** langgraph-checkpoint-redis 0.1.2 for durable state persistence.
**Rationale:** In-memory state lost on restart. Redis persistence enables conversation resumption, crash recovery. Production-grade state management. Proper async cleanup prevents event loop warnings (Sprint 12 fix).

### 2025-01-15 | E2E Integration Testing with Real Services (ADR-014)
**Decision:** NO MOCKS for integration/E2E tests. Use real Docker services (Redis, Qdrant, Neo4j, Ollama).
**Rationale:** Sprint 6 showed mock behavior ≠ real behavior (timeout issues). Real services catch integration bugs, configuration problems, race conditions. Cost-free Ollama enables unlimited testing. Trade-off: slower execution (2-5 min), but higher confidence.

### 2025-01-15 | Critical Path Testing Strategy (ADR-015)
**Decision:** 4 critical paths: Vector Search, Graph RAG, Memory Query, Hybrid Fusion. 80% E2E baseline.
**Rationale:** Focus testing on user-facing workflows. NO MOCKS principle ensures production readiness. Sprint 8 baseline: 78.6% pass rate. Sprint 12: 88.5% (2.8x improvement from 17.9% in Sprint 11).

### 2025-02-07 | Production Deployment Guide (Sprint 12)
**Decision:** Comprehensive 800+ line guide covering GPU, Docker, K8s, monitoring, security, backup/DR.
**Rationale:** De-risks production deployment. Documents all prerequisites (NVIDIA drivers, container toolkit). Includes Prometheus/Grafana dashboards, security hardening (JWT, rate limiting, HTTPS/TLS), automated backup scripts. Critical for handoff to ops team.

---

## SPRINT 16: UNIFIED ARCHITECTURE & BGE-M3 MIGRATION

### 2025-10-28 | Unified Chunking Service (ADR-022)
**Decision:** Create single ChunkingService for all components (Qdrant, BM25, LightRAG).
**Rationale:** Eliminate fragmentation (3 separate chunking implementations), ensure consistency across indexes, reduce code duplication by 70%. SHA-256 deterministic chunk IDs enable reliable provenance tracking.

### 2025-10-28 | BGE-M3 System-Wide Standardization (ADR-024)
**Decision:** Migrate from nomic-embed-text (768-dim) to BGE-M3 (1024-dim) for all embeddings.
**Rationale:** Enable cross-layer similarity (Qdrant ↔ Graphiti), better multilingual support (German OMNITRACKER docs), unified architecture with single embedding model. Trade-off: +66% latency (+10ms with cache), but massive capability gain.

### 2025-10-28 | Unified Re-Indexing Pipeline (ADR-023)
**Decision:** Create POST /api/v1/admin/reindex endpoint with atomic transaction semantics.
**Rationale:** BGE-M3 migration requires re-embedding all documents. Atomic deletion (Qdrant + BM25) prevents inconsistent state. SSE streaming provides real-time progress visibility. Safety checks (confirm=true, dry-run) prevent accidental data loss.

### 2025-10-28 | PPTX Document Support
**Decision:** Add python-pptx dependency for PowerPoint extraction.
**Rationale:** OMNITRACKER corpus contains many PPTX training materials. python-pptx provides mature, battle-tested extraction. Minimal overhead (<1MB dependency).

### 2025-10-28 | Pydantic v2 ConfigDict Migration
**Decision:** Migrate all 21 Pydantic models from @root_validator to ConfigDict.
**Rationale:** Eliminate deprecation warnings, future-proof for Pydantic v3, cleaner model definitions. No performance impact (already on Pydantic v2 core).

---

## FUTURE DECISIONS (PLANNED)

### TBD | React + Next.js 14 Frontend (Sprint 14)
**Decision (Planned):** Replace Gradio with Next.js 14 + TypeScript + Tailwind CSS.
**Rationale:** Gradio insufficient for production UI (limited customization, no SSE, poor styling). Next.js provides professional polish, real-time streaming (SSE), dark mode, responsive design. NextAuth.js for authentication, Zustand for state management.

### TBD | Adaptive Routing with Machine Learning (Sprint 13)
**Decision (Planned):** ML-based query router to auto-select vector/graph/hybrid strategy.
**Rationale:** Current router uses heuristics (keyword matching). ML model can learn from query patterns, user feedback. Potential +10-15% relevance improvement. Train on historical query logs with RAGAS scores.

### TBD | Multi-User Authentication & Authorization
**Decision (Planned):** JWT-based auth, role-based access control (admin, user, viewer).
**Rationale:** Production requires user management. NextAuth.js integration in Sprint 14. User-specific rate limiting, audit logging, session management.

---

## SPRINT 20-31: PRODUCTION OPTIMIZATION & FRONTEND COMPLETION

### 2025-11-07 | Pure LLM Extraction as Default (ADR-026)
**Decision:** Replace Three-Phase Extraction (SpaCy + Dedup + Gemma) with Pure LLM extraction.
**Rationale:** Sprint 21's 1800-token chunks (vs 600 tokens) made LLM extraction feasible. Pure LLM provides better quality (domain-specific entities, German terms) with similar performance due to 65% chunk reduction. Three-Phase deprecated but available via config.

### 2025-11-19 | Alibaba Cloud Qwen3-32B for Extraction (ADR-037)
**Decision:** Use Alibaba Cloud Qwen3-32B (32B parameters) for entity/relation extraction instead of local Gemma 2 4B.
**Rationale:** 8x larger model (32B vs 4B) provides +10-15% extraction accuracy. Cost-effective ($0.001-0.003 per 1K tokens), automatic fallback to local if budget exceeded. Budget tracking via SQLite ensures cost control ($120/month covers 1K-3K documents).

### 2025-11-21 | Adaptive Section-Aware Chunking (ADR-039)
**Decision:** Implement adaptive chunking that respects document section boundaries while avoiding fragmentation.
**Rationale:** PowerPoint fragmentation problem (124 tiny chunks → 6-8 optimal chunks). Adaptive strategy: Large sections (>1200 tokens) stay standalone, small sections (<1200 tokens) merge to 800-1800 token range. Multi-section metadata enables precise citations and cleaner entity extraction (-15% false relations).

---

## SPRINT 34: KNOWLEDGE GRAPH ENHANCEMENT & RELATES_TO RELATIONSHIPS

### 2025-12-01 | RELATES_TO via Pure LLM Extraction
**Decision:** Use Alibaba Cloud qwen3-32b for semantic relation extraction via AegisLLMProxy.
**Rationale:** 32B model provides high-quality semantic relation extraction beyond entity mentions. Achieves +13% false relation reduction (baseline 23% → <10%) through section-aware context. Cost-effective at $0.001-0.003 per 1K tokens, automatic fallback to local Gemma 2 4B if budget exceeded. Pure LLM approach ensures consistency with entity extraction (both via AegisLLMProxy).

### 2025-12-01 | Edge Visualization Color-Coding by Relationship Type
**Decision:** Color-code edges by relationship type in graph visualization.
**Rationale:** Visual distinction improves user comprehension of graph structure. RELATES_TO edges (semantic) rendered in blue (#3B82F6), MENTIONED_IN edges (chunk references) in gray (#9CA3AF), HAS_SECTION edges (document structure) in green (#10B981). Pattern enables quick filtering by edge type.

### 2025-12-01 | Edge Filtering UI Pattern (Checkboxes + Weight Slider)
**Decision:** Implement checkboxes for edge type filtering + weight threshold slider in graph UI.
**Rationale:** Simple, intuitive pattern for exploring graph subsets. Users select which edge types to show (RELATES_TO, MENTIONED_IN, HAS_SECTION checkboxes), adjust minimum weight (0.0-1.0 slider). Real-time updates provide immediate feedback. Alternative (dropdown) less discoverable for multiple selections.

### 2025-12-01 | Comprehensive E2E Test Coverage for Graph Features (19 tests)
**Decision:** Implement 19 end-to-end tests covering graph visualization, filtering, and relation extraction.
**Rationale:** Visual components require browser-based testing (Playwright). Unit tests insufficient for graph interaction testing. 19 tests organized as: 6 relation extraction tests, 7 visualization tests, 6 filtering interaction tests. Ensures production-ready graph features.

---

## KEY PIVOT POINTS

### Sprint 11: LightRAG Model Switch (qwen3:0.6b → llama3.2:3b)
**Original:** qwen3:0.6b (ultra-lightweight, 0.5GB RAM)
**Problem:** Entity extraction format issues (JSON parsing errors)
**Pivot:** llama3.2:3b (better structured output)
**Trade-off:** Slower  but +20% accuracy
**Lesson:** Model quality > speed for entity extraction

### Sprint 14 (Planned): Gradio → React Migration
**Original:** Gradio MVP (Sprint 10)
**Problem:** Limited customization, no SSE streaming, poor styling
**Pivot:** React + Next.js 14 (Sprint 14)
**Reason:** Production UI requires professional polish
**Lesson:** Gradio excellent for prototyping, not production

### Sprint 9: MCP Client Only (Not MCP Server)
**Original:** Plan included MCP Server (provide tools to others)
**Problem:** Unclear use case, added complexity
**Pivot:** MCP Client only (consume external tools)
**Reason:** Focus on value delivery (action agent needs tools), not tool provision
**Lesson:** YAGNI principle - don't build what you don't need yet

---

## DECISION THEMES

### Cost Optimization
- Ollama-only strategy ($0 LLM costs, $18K-24K/year savings)
- Self-hosted infrastructure (Docker Compose, no cloud vendor lock-in)
- GPU acceleration on existing hardware (RTX 3060, $0 incremental cost)

### Quality over Speed
- Cross-encoder reranking (+50ms, +15-20% precision)
- llama3.2:3b over qwen3:0.6b (slower, but better quality)
- Real service testing (slower, but higher confidence)

### Developer Experience
- FastAPI auto OpenAPI docs
- LangGraph explicit control (vs CrewAI simplicity)
- Unified services (embedding, ingestion) reduce complexity

### Production Readiness
- GPU acceleration mandatory (15-20x speedup)
- Redis checkpointer (durable state)
- Comprehensive deployment guide (800+ lines)
- E2E testing with real services (NO MOCKS)

### Modularity & Flexibility
- 3-layer memory (optimize per use case)
- Hybrid retrieval (vector + graph + BM25)
- Multi-agent orchestration (specialized agents)
- Unified router (4 strategies)

---

## SPRINT 20: PERFORMANCE OPTIMIZATION & EXTRACTION QUALITY

### 2025-11-07 | Mirostat v2 for Ollama Sampling (Sprint 20.1)
**Decision:** Use mirostat_mode=2, tau=5.0, eta=0.1 for all Ollama LLM calls.
**Rationale:** 86% speed improvement (18.2 → 33.9 tokens/s) while maintaining quality. Adaptive sampling provides consistent perplexity without manual temperature tuning. Tested across 6 configurations, mirostat_v2 outperformed baseline, temperature sweep, and top_k/top_p.

### 2025-11-07 | LLM Extraction Pipeline with Config Switch (Sprint 20.4)
**Decision:** Implement dual extraction pipelines: three_phase (SpaCy, fast) vs llm_extraction (LLM, high quality).
**Rationale:** Trade-off between speed and quality. three_phase: ~15s/doc but high false positives (103 CONCEPT entities). llm_extraction: ~200s/doc but 98% noise removal (Few-Shot prompts). Config switch `EXTRACTION_PIPELINE` enables use-case selection (bulk ingestion vs quality-critical).

### 2025-11-07 | Chunk Size Bottleneck Identified (Sprint 20.5)
**Decision:** Defer full reindexing to Sprint 21, optimize chunk size first.
**Rationale:** Chunk analysis revealed 103 small chunks (~112 tokens avg) create massive LLM overhead (8-9s/call, ~36 min total). Increasing LIGHTRAG_CHUNK_TOKEN_SIZE from 600 → 1800 will reduce chunks by 65% (~12 min total). Better to reindex ONCE with optimal settings than twice.

### 2025-11-07 | Entity Extraction Bug Fix (Sprint 20.2 - Unplanned)
**Decision:** Fix type mismatch: dict → GraphEntity in ThreePhaseExtractor.
**Rationale:** Entities not created in Neo4j due to silent type mismatch. LightRAG expected GraphEntity objects, but ThreePhaseExtractor returned dicts. Fix enabled entity graph construction (0 → 107 entities). Critical for graph-based retrieval.

---

## SPRINT 21: UNIFIED INGESTION PIPELINE (PLANNED)

### TBD | Docling for Heavy Document Parsing
**Decision (Planned):** Replace LlamaIndex SimpleDirectoryReader with IBM Docling for PDF, DOCX, PPTX, XLSX, HTML.
**Rationale:** Better extraction quality (layout-aware parsing, table preservation, OCR). SimpleDirectoryReader loses structure (avg 470 chars/page from PowerPoint, suspected data loss). Docling provides Markdown output (RAG-friendly), image extraction, and table structure. Trade-off: Additional dependency but massive quality gain.

### TBD | Tree-sitter for Code Parsing
**Decision (Planned):** Add Tree-sitter AST parsing for Python, JavaScript, TypeScript, Java code files.
**Rationale:** Code files contain structured information (functions, classes) that should be extracted for better RAG. Treating code as plain text loses metadata. Tree-sitter provides language-agnostic parsing with function/class line numbers, docstring extraction.

### 2025-11-07 | Pure LLM Extraction as Default (ADR-026, Sprint 21)
**Decision:** Switch default extraction pipeline from `three_phase` (SpaCy + Dedup + Gemma) to `llm_extraction` (Pure LLM, NO SpaCy).
**Rationale:** Sprint 21 increases chunk size from 600 → 1800 tokens (3x), reducing total chunks by 65%. Pure LLM extraction (200-300s/doc) is slower per document but provides better quality (domain-specific terms, German support, no false positives). Chunk reduction compensates for LLM slowness, achieving similar total pipeline time as Sprint 20's fast SpaCy approach. Gemma 3 4B with Mirostat v2 (86% faster) makes this strategy viable. Config switch available: `EXTRACTION_PIPELINE=llm_extraction`.

---

## SPRINT 23: MULTI-CLOUD LLM EXECUTION & VLM INTEGRATION

### 2025-11-13 | ANY-LLM Core Library (NOT Gateway) (ADR-033)
**Decision:** Use ANY-LLM Core Library (`acompletion()` function) for unified LLM routing, but NOT deploy ANY-LLM Gateway.
**Rationale:** ANY-LLM Gateway requires separate server deployment (adds infrastructure complexity). Core Library provides sufficient functionality: multi-cloud routing (Ollama → Alibaba Cloud → OpenAI), budget tracking, provider fallbacks. Gateway features (BudgetManager, CostTracker, connection pooling) implemented manually with SQLite (389 LOC). VLM support missing in ANY-LLM, requires direct API integration anyway.

### 2025-11-13 | SQLite Cost Tracker (NOT ANY-LLM BudgetManager) (ADR-033)
**Decision:** Implement custom SQLite cost tracker (389 LOC) instead of using ANY-LLM Gateway BudgetManager.
**Rationale:** ANY-LLM Gateway requires separate server (adds complexity, ops overhead). SQLite provides full control: per-request tracking (timestamp, provider, model, tokens, cost, latency), monthly aggregations, CSV/JSON export, database at `data/cost_tracking.db`. Working perfectly (4/4 tests passing, $0.003 tracked). Re-evaluate if ANY-LLM adds VLM support or we need multi-tenant cost tracking.

### 2025-11-13 | DashScope VLM with Fallback Strategy (ADR-033)
**Decision:** Primary VLM: `qwen3-vl-30b-a3b-instruct` (cheaper output tokens), Fallback: `qwen3-vl-30b-a3b-thinking` (on 403 errors).
**Rationale:** Alibaba Cloud VLM best practices: instruct model has cheaper output token pricing, thinking model provides better reasoning but costs more. Automatic fallback on 403 errors (quota exceeded). VLM-specific parameters: `enable_thinking=True` for thinking model, `vl_high_resolution_images=True` (16,384 vs 2,560 tokens for better quality). Base64 image encoding, OpenAI-compatible API format.

### 2025-11-13 | Alibaba Cloud DashScope (NOT Ollama Cloud) (ADR-033 Deviation)
**Decision:** Use Alibaba Cloud DashScope API instead of planned "Ollama Cloud" (which doesn't exist yet).
**Rationale:** Sprint 23 planning assumed Ollama would launch cloud API. Investigation revealed Ollama Cloud not available yet (as of 2025-11-13). Alibaba Cloud DashScope provides: OpenAI-compatible API, Qwen models (qwen-turbo/plus/max), VLM support (qwen3-vl-30b), cost-effective pricing, ANY-LLM compatible. Pivot decision: Ollama Cloud → Alibaba Cloud. Ollama remains primary for local inference ($0 cost).

### 2025-11-13 | DashScope VLM Direct Integration (Bypass AegisLLMProxy) (TD-23.2)
**Decision:** DashScopeVLMClient bypasses AegisLLMProxy routing logic, makes direct API calls.
**Rationale:** ANY-LLM `acompletion()` function does NOT support image inputs (text-only). VLM requires base64 image encoding, special parameters (`enable_thinking`, `vl_high_resolution_images`), different API endpoint. Faster to implement direct integration (267 LOC) than extend AegisLLMProxy. Tech debt acknowledged (TD-23.2): Future work to extend AegisLLMProxy with VLM-specific `generate()` method for unified routing metrics.

---

## SPRINT 28: FRONTEND UX ENHANCEMENTS (PERPLEXITY-INSPIRED FEATURES)

### 2025-11-18 | Selective Perplexity UX Implementation (ADR-034)
**Decision:** Adopt proven UX patterns (citations, follow-ups, settings) from Perplexity.ai without full clone.
**Rationale:** High-value features (citations [1][2][3], follow-up questions, settings page) improve user experience while maintaining AEGIS RAG identity. Selective adoption faster than building from scratch. Proven patterns reduce UX risk.

### 2025-11-18 | Parallel Development Strategy - Wave-based (ADR-035)
**Decision:** Use wave-based parallel development with 3 waves of independent features.
**Rationale:** Enables 10x speedup vs. sequential development. Wave 1 (citations, follow-ups) independent of Wave 2 (settings, backend sync). Parallel frontend/backend work maximizes team velocity. Critical for rapid UX iteration.

### 2025-11-18 | Settings Management via localStorage (Phase 1) (ADR-036)
**Decision:** Use localStorage for settings in Phase 1, defer backend sync to Phase 3.
**Rationale:** Rapid implementation without backend complexity. localStorage provides instant read/write (no network latency). Phase 3 backend sync enables cross-device settings. Trade-off: localStorage 5-10MB limit acceptable for settings (conversations separate).

### 2025-11-18 | Custom ReactMarkdown Citation Renderers
**Decision:** Implement custom ReactMarkdown components for inline citation parsing.
**Rationale:** ReactMarkdown extensible component system perfect for [1][2][3] citations. Custom renderers handle citation parsing (115 LOC utilities), hover tooltips, click-to-scroll. Alternative: Regex replacement (fragile), HTML dangerouslySetInnerHTML (XSS risk).

### 2025-11-18 | React Context API for Settings State
**Decision:** Use React Context API for settings state management instead of Zustand.
**Rationale:** Settings isolated to Settings page + header. Context API simpler than Redux/Zustand for this scope. No external dependencies. Easy migration to backend sync (Phase 3). SettingsContext (105 LOC) manages theme, models, preferences.

### 2025-11-18 | forwardRef Pattern for Scroll-to-Source
**Decision:** Use React forwardRef + useImperativeHandle for SourceCardsScroll scroll-to-source.
**Rationale:** Imperative handle enables parent (StreamingAnswer) to trigger child (SourceCardsScroll) scroll. Alternative: State prop (causes re-render), Ref callback (complex). Pattern: Citation onClick → scrollToSource(index) → smooth scroll.

---

---

## SPRINT 35: SEAMLESS CHAT FLOW & UX ENHANCEMENT

### 2025-12-02 | Multi-turn Conversations Without Navigation
**Decision:** Implement seamless chat flow where conversations continue in-place without page navigation.
**Rationale:** Modern chat applications (ChatGPT, Claude) don't require navigation between messages. Inline message updates reduce cognitive load and provide faster UX. SSE streaming enables real-time response display.

### 2025-12-02 | Optimistic UI Updates for Chat Messages
**Decision:** Display user messages immediately with optimistic updates before server confirmation.
**Rationale:** Perceived latency reduction of 200-500ms. User sees immediate feedback. Server errors handled gracefully with retry/revert UI. Standard pattern in modern web applications.

### 2025-12-03 | Error Boundaries with Graceful Recovery
**Decision:** Implement React Error Boundaries with user-friendly error states and retry actions.
**Rationale:** Crash isolation prevents entire app failure. User-friendly messages replace technical stack traces. Retry buttons enable self-service recovery. Critical for production reliability.

---

## SPRINT 36: ADVANCED SEARCH & EXPORT FEATURES

### 2025-12-04 | Faceted Search with Qdrant Filters
**Decision:** Implement faceted search using Qdrant's native filtering capabilities (document type, date range, source).
**Rationale:** Qdrant supports efficient payload filtering at query time. No separate facet index needed. Filter combinations applied server-side for accurate results. Frontend receives filtered results without client-side post-processing.

### 2025-12-04 | Recent Searches in localStorage
**Decision:** Store recent searches in localStorage (not backend) with 20-item limit.
**Rationale:** Zero server load for search history. Instant retrieval (<1ms). Privacy-friendly (stays on device). 20-item limit prevents storage bloat. Simple implementation without database schema changes.

### 2025-12-05 | Multi-Format Export System (PDF, Markdown, JSON)
**Decision:** Implement export system with PDF (visual), Markdown (portable), and JSON (data) formats.
**Rationale:** Different use cases: PDF for sharing/printing, Markdown for documentation, JSON for data portability. Server-side generation ensures consistent formatting. Streaming for large exports prevents timeouts.

---

## SPRINT 37: STREAMING PIPELINE ARCHITECTURE

### 2025-12-05 | AsyncIO Queue-based Pipeline Architecture (Feature 37.1)
**Decision:** Implement StreamingPipelineOrchestrator with TypedQueue[T] for inter-stage communication instead of batch processing.
**Rationale:** 50% memory reduction vs batch (chunks processed incrementally, not held in memory). Backpressure support (maxsize) prevents OOM. Type-safe queues catch errors at type-check time. Natural fit for producer-consumer pattern.

### 2025-12-06 | SSE for Pipeline Progress Updates (Feature 37.5)
**Decision:** Use Server-Sent Events (SSE) for real-time pipeline progress instead of polling.
**Rationale:** SSE is simpler than WebSocket for unidirectional updates. Native browser support (EventSource API). Automatic reconnection on connection loss. Lower overhead than WebSocket for progress-only use case. Already proven in chat streaming.

### 2025-12-06 | Dynamic Worker Pool Configuration (Feature 37.7)
**Decision:** Allow runtime configuration of embedding/extraction/VLM workers via Admin UI.
**Rationale:** Hardware varies across deployments (GPU memory, CPU cores). Static config requires restart. Admin UI enables experimentation with worker counts. Sensible defaults (2 embedding, 4 extraction, 1 VLM) for common hardware.

### 2025-12-07 | Multi-Document Parallel Processing (Feature 37.8)
**Decision:** Process multiple documents concurrently with configurable parallelism limit.
**Rationale:** Batch ingestion (e.g., 100 PDFs) would be slow with sequential processing. Parallel processing achieves 4x throughput improvement. Memory-aware limits prevent OOM. Progress aggregation shows combined batch progress.

---

## SPRINT 38-47: GRAPH OPTIMIZATION & ADVANCED FEATURES

[Sprint 38-47 decisions documented separately - see individual sprint reports in docs/sprints/]

---

## SPRINT 48-49: ENTITY DEDUPLICATION & OLLAMA CONSOLIDATION

### 2025-12-10 | Nemotron as Default LLM (Sprint 48.9)
**Decision:** Use nemotron-mini:latest (4B parameters) as default generation model instead of llama3.2:8b.
**Rationale:** 2x faster inference (4B vs 8B parameters, ~200ms vs ~400ms per response). Better instruction following and structured output quality. Lower VRAM utilization (3.2GB vs 6.5GB) enables deployment on memory-constrained hardware. Ollama auto-download ensures availability. Config: OLLAMA_MODEL_GENERATION=nemotron-mini:latest in .env.

### 2025-12-10 | Ollama-based Reranking (Sprint 48, TD-059)
**Decision:** Replace sentence-transformers/ms-marco-MiniLM-L6-v2 reranking with Ollama-based model qllama/bge-reranker-v2-m3:q8_0.
**Rationale:** Eliminates sentence-transformers dependency entirely (-2GB Docker image size). Consistent with project's Ollama-first strategy (unified LLM routing via AegisLLMProxy). Supports multilingual reranking. Trade-off: Slightly higher latency (+50-100ms per document due to Ollama quantization) vs local inference, but acceptable for production (p95 still <500ms for typical 5-doc re-ranking).
**Alternatives Considered:**
- Keep sentence-transformers (rejected: unnecessary dependency, Docker bloat)
- Use smaller local model (rejected: insufficient quality for reranking)
- Keep local cross-encoder (rejected: locked us into specific model, hard to upgrade)

### 2025-12-11 | BGE-M3 for Entity Deduplication (Sprint 49.1-49.3, TD-059)
**Decision:** Migrate entity deduplication from sentence-transformers/all-MiniLM-L6-v2 (384-dim) to BGE-M3 (1024-dim).
**Rationale:**
- Eliminates sentence-transformers dependency entirely (saves ~2GB in Docker images and pyproject.toml dependency tree)
- BGE-M3 already in project for query embeddings (code reuse, consistent architecture)
- 1024-dim vs 384-dim provides better deduplication quality (28% false dedup reduction in testing)
- Multilingual support for OMNITRACKER German terms
- Ollama-based (no additional external service)
**Alternatives Considered:**
- Keep sentence-transformers (rejected: unnecessary dependency adds complexity)
- Use different model (rejected: BGE-M3 already available, proven in production)
- Rule-based deduplication (rejected: brittle, doesn't adapt to domain changes)
**Impact:** -2GB Docker image, improved dedup quality from 84% → 92% precision. Migration completed in Sprint 49.3.

### 2025-12-12 | Embedding-based Relation Type Deduplication (Sprint 49.4-49.6)
**Decision:** Replace hardcoded synonym lists (60+ entries) with embedding-based semantic clustering using BGE-M3 + hierarchical clustering.
**Rationale:**
- Hardcoded lists not scalable across domains (OMNITRACKER, medical, finance require different synonym sets)
- Embedding-based approach automatically discovers synonyms via semantic similarity
- No manual maintenance required (self-adapting to domain terminology)
- BGE-M3 multilingual support handles German, English, French relation types
- Redis caching (100-entry cache) provides performance (<5ms lookup)
**Clustering Threshold:** 0.88 cosine similarity determined empirically through testing (avoids false merges like "acquires" vs "purchases" at 0.85).
**Alternatives Considered:**
- Keep hardcoded lists (rejected: not scalable, requires code changes per domain)
- LLM-based validation (rejected: too slow/expensive, ~500ms per relation type cluster)
- Simpler similarity threshold (rejected: 0.88 tuning critical, 0.85 causes false positives)
**Impact:** Scalable to any domain, 40% reduction in manual synonym list maintenance, +8% relation dedup quality.

### 2025-12-12 | Hybrid Embedding + Manual Override Strategy (Sprint 49.8, Feature 49.8)
**Decision:** Implement HybridRelationDeduplicator with automatic embedding-based clustering + manual Redis-backed overrides.
**Rationale:**
- Pure embedding approach (0.88 threshold) occasionally clusters incorrectly edge cases
- Manual overrides stored in Redis enable domain experts to fix edge cases without code changes
- Redis overrides take precedence over automatic clustering (best of both worlds)
- Allows gradual refinement: capture edge cases in Redis, backport patterns to clustering threshold
- Domain-specific synonym pairs (e.g., "acquired_by" → "acquired", "is_part_of" → "part_of") controllable by admins
**Implementation:** RedisOverrideStore at data/relation_overrides.json, SettingsAPI endpoint for admin management.
**Alternatives Considered:**
- Pure embedding (rejected: occasional false merges on edge cases)
- Pure manual (rejected: requires code changes, not scalable)
- LLM-based validation (rejected: too slow for real-time requests)
**Impact:** Handles 100% of relation types correctly (vs 92% with pure embedding).

### 2025-12-13 | Provenance Tracking via source_chunk_id (Sprint 49.5, TD-048)
**Decision:** Add source_chunk_id property to all MENTIONED_IN relationships in Neo4j knowledge graph.
**Rationale:**
- Enables tracing entity mentions back to original document chunks
- Required for consistency validation (detect duplicates of same entity across chunks)
- Supports entity evidence display in UI (show which chunks mention entity)
- Enables chunk-level entity statistics (most-cited entities per chunk)
- Necessary for future chunk-level reranking (rerank by chunk not just document)
**Schema Change:** MENTIONED_IN relationships now carry (entity_id, chunk_id, source_chunk_id, sentence). Backfill completed for existing relationships via migration script.
**Alternatives Considered:**
- Store only document_id (rejected: loses chunk-level granularity)
- Track in separate Redis cache (rejected: requires consistency management, harder to query)
- Store in Qdrant metadata (rejected: knowledge graph relationship source, should live in Neo4j)
**Impact:** Full provenance tracking, enables citation at chunk level not just document. TD-048 resolved.

---

## KEY INSIGHTS FROM SPRINTS 48-49

### Dependency Minimization Theme
**Pattern:** Remove unnecessary dependencies (sentence-transformers × 2 in reranking + entity dedup).
**Rationale:** Each dependency adds:
- Docker image size (+2GB for sentence-transformers)
- Supply chain risk (new CVEs, maintenance burden)
- Version conflicts (Torch versions, CUDA compatibility)
- Cognitive load (developers must understand each library)
**Result:** Consolidated to Ollama-based services (single LLM provider) + BGE-M3 embeddings (single embedding model for vector + dedup + reranking semantics).

### Ollama-First Architecture
**Achievement:** All LLM + embedding operations now via Ollama or BGE-M3 (Ollama-served).
- Generation: nemotron-mini (4B)
- Reranking: qllama/bge-reranker-v2-m3
- Entity extraction: qwen3-32B (Alibaba Cloud via AegisLLMProxy, fallback to Ollama)
- Entity dedup: BGE-M3 embeddings
- Relation type dedup: BGE-M3 embeddings
**Benefit:** Single orchestration layer (AegisLLMProxy), unified caching strategy, simplified monitoring.

### Scalability via Semantic Similarity
**Insight:** Hardcoded lists (60+ relation synonyms) can't scale across domains.
**Solution:** Embedding-based clustering automatically adapts to domain terminology.
**Generalization:** Same pattern could apply to entity type deduplication (currently hardcoded), chunk quality scoring, etc.

---

## SPRINT 60: DOCUMENTATION CONSOLIDATION & TECHNICAL INVESTIGATIONS

### 2025-12-21 | Documentation Consolidation Post-Refactoring (Sprint 60.1-60.3)
**Decision:** Create 7 consolidated documentation files (ARCHITECTURE.md, TECH_STACK.md, CONVENTIONS.md, 4 analysis docs) from fragmented sources.
**Rationale:** Sprint 53-59 refactoring left documentation scattered across 40+ files. Consolidated docs provide single source of truth for architecture, tech stack, conventions. Archived 17 obsolete files. Critical for onboarding new developers and maintaining system knowledge.

### 2025-12-21 | vLLM vs Ollama Investigation - Keep Ollama (Sprint 60.4, TD-071)
**Decision:** Do NOT migrate from Ollama to vLLM for LLM inference.
**Rationale:** Investigation revealed vLLM not justified at current scale (<50 QPS). Ollama provides sufficient throughput with simpler architecture. vLLM benefits (batching, speculative decoding) only relevant at >100 QPS sustained load. Migration cost (deployment complexity, GPU memory tuning) outweighs benefits. Re-evaluate if load exceeds 100 QPS.

### 2025-12-21 | Sentence-Transformers Reranking Investigation (Sprint 60.4, TD-072)
**Decision:** Migrate from Ollama reranking to native sentence-transformers Cross-Encoder for 50x speedup.
**Rationale:** Investigation showed cross-encoder/ms-marco-MiniLM-L-6-v2 achieves 120ms vs 2000ms latency (50x faster) with comparable quality. Lower VRAM usage (90MB model vs 4GB Ollama). Recommended for Sprint 61 implementation. Trade-off: Additional dependency, but massive performance gain justifies it.

### 2025-12-21 | Sentence-Transformers Embeddings Investigation (Sprint 60.4, TD-073)
**Decision:** Migrate from Ollama embeddings to native sentence-transformers BGE-M3 for 3-5x speedup.
**Rationale:** Native BGE-M3 provides 3-5x faster embeddings (50-80ms vs 200-500ms), 60% less VRAM, identical quality. Batch processing enables 16x speedup for ingestion pipeline. Recommended for Sprint 61. Trade-off: Direct model loading vs Ollama API, but performance gain critical for production scale.

### 2025-12-21 | Multihop Endpoint Removal (Sprint 60.4, TD-069)
**Decision:** Remove deprecated multihop endpoints (POST /api/v1/graph/viz/multi-hop, /shortest-path) in Sprint 61.
**Rationale:** Zero frontend usage after 12+ months, zero backend usage (agents use LightRAG directly). Marked DEPRECATED 2025-12-07. Endpoints functional but unutilized. Reduces API surface area, simplifies maintenance. Can re-implement from archived code if needed.

---

## SPRINT 67-68: SECURE SANDBOX + ADAPTATION + PERFORMANCE

### 2025-12-31 | deepagents Integration with Bubblewrap Sandbox (Sprint 67.1-67.4, ADR-TBD)
**Decision:** Integrate deepagents framework with BubblewrapSandboxBackend for secure code execution.
**Rationale:** LangChain-native agent harness with standardized SandboxBackendProtocol. Bubblewrap provides Linux container isolation without Docker overhead. Multi-language support (Bash + Python) with shared workspace. Security features: syscall filtering, filesystem isolation, network restrictions. Alternative considered: Docker-based sandbox (rejected: too heavyweight, slower startup).

### 2025-12-31 | Tool-Level Adaptation Framework (Sprint 67.5-67.9, Paper 2512.16301)
**Decision:** Implement tool-level adaptation (T1/T2) instead of LLM fine-tuning for RAG optimization.
**Rationale:** Research paper (2512.16301) shows adapting retriever/reranker/query-rewriter achieves comparable gains to LLM fine-tuning at 1/10th cost. Unified Trace & Telemetry enables pipeline monitoring. Eval Harness provides automated quality gates (grounding, citation coverage, format compliance). Dataset Builder generates training data from production queries. Deferred agent-level adaptation (A1/A2) to Sprint 68.

### 2025-12-31 | C-LARA Intent Classifier (Sprint 67.10-67.13, TD-079)
**Decision:** Replace Semantic Router with C-LARA approach (LLM offline data generation + SetFit fine-tuning).
**Rationale:** Semantic Router achieves only 60% accuracy (A/B tested). C-LARA approach: Generate 1000 labeled examples with Qwen2.5:7b (87-95% benchmark accuracy), fine-tune SetFit classification model. Target: 85-92% accuracy improvement. SetFit provides efficient sentence-level classification without full LLM inference. Offline data generation avoids runtime LLM overhead.

### 2025-12-31 | Section Extraction Performance Optimization (Sprint 67.14 + 68.4, TD-078)
**Decision:** Two-phase optimization: Quick wins (Sprint 67, 2-3x speedup) + Parallelization (Sprint 68, 5-10x total speedup).
**Rationale:** Section extraction identified as critical bottleneck (9-15 minutes for medium PDFs). Phase 1 (Sprint 67): Batch tokenization, regex compilation, profiling instrumentation. Phase 2 (Sprint 68): ThreadPoolExecutor parallelization, LRU caching. Target: 15min → 2min for large PDFs. Enables real-time ingestion for production.

### 2025-12-31 | Technical Debt Archival - 7 Items (Sprint 67 Planning)
**Decision:** Archive 7 resolved TDs (043, 047, 058, 069, 071, 072, 073) after verification.
**Rationale:** Systematic review confirmed implementation status: TD-047 exceeded baseline (608 Playwright tests vs 40 planned), Sprint 60 investigations complete (TD-071, 072, 073), community summaries implemented (TD-058). Reduced active TD count 16 → 9 (-44%), story points 264 SP → 139 SP (-47%). Sprint 67-68 addresses 98% of remaining backlog (137 SP planned vs 139 SP total).

### 2025-12-31 | BM25 Cache Auto-Refresh (Sprint 68.5, TD-074)
**Decision:** Implement cache validation on startup with auto-refresh on discrepancy >10%.
**Rationale:** Cache discrepancy identified (10 cached vs 43 indexed documents). Auto-refresh ensures consistency without manual intervention. Namespace-aware caching prevents cross-contamination. Alternative considered: Manual refresh (rejected: requires ops intervention, error-prone).

### 2025-12-31 | Section Community Detection (Sprint 68.8)
**Decision:** Implement Louvain/Leiden algorithms for section-based community detection.
**Rationale:** Activate section-aware infrastructure (currently ~20% utilized). Section-level communities provide finer-grained context for hybrid search. Integration with Maximum Hybrid Search via 15 production Cypher queries. Alternative: Document-level communities (rejected: loses section granularity, less precise context).

---

**Last Updated:** 2025-12-31 (Sprint 67-68 Planning)
**Total Decisions Documented:** 84 (+8 from Sprint 60, 67-68)
**Current Sprint:** Sprint 67 (Planned)
**Next Sprint:** Sprint 68 (Planned - Production Hardening)
