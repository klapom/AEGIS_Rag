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

## SPRINT 76-79: RAGAS EVALUATION & GRAPH SEARCH ENHANCEMENT

### 2026-01-06 | .txt File Support for RAGAS Dataset (Sprint 76.1)
**Decision:** Add plain text (.txt) file support to ingestion pipeline for HotpotQA evaluation dataset.
**Rationale:** RAGAS evaluation requires ground truth datasets (HotpotQA, Amnesty QA) which are primarily .txt files. Docling CUDA handles PDFs/DOCX, but .txt files need direct parsing. Minimal overhead (SimpleDirectoryReader fallback), enables 15 HotpotQA files for evaluation. Critical for establishing RAGAS baseline metrics.

### 2026-01-06 | RAGAS Baseline Evaluation (Sprint 76.2-76.3)
**Decision:** Establish RAGAS baseline using GPT-OSS:20b local LLM (Faithfulness 80%, Answer Relevancy 93%, Context Recall 50%, Context Precision 20%).
**Rationale:** Baseline metrics critical before optimization. GPT-OSS:20b selected for local inference (no cloud costs). Results show strong answer quality (80% faithfulness, 93% relevancy) but weak retrieval (50% recall, 20% precision). Identifies retrieval as primary optimization target for Sprint 77-78.

### 2026-01-07 | BM25 Namespace Filtering Bug Fix (Sprint 77.1, TD-092)
**Decision:** Fix critical bug where BM25 keyword search ignored namespace filtering, returning results from all namespaces.
**Rationale:** Security/privacy issue - users could see chunks from other namespaces. BM25 cache invalidation not respecting namespace boundaries. Fix: Add namespace_id to BM25 cache key, filter results by namespace before RRF fusion. Verified with 6 integration tests (100% pass rate).

### 2026-01-07 | Chunk ID Mismatch Resolution (Sprint 77.2, TD-093)
**Decision:** Align chunk ID generation between Qdrant (SHA-256 hash) and Neo4j (UUID) to enable cross-database provenance tracking.
**Rationale:** Chunk ID mismatch caused citation failures (Qdrant chunk_id ≠ Neo4j chunk_id). Unified approach: SHA-256(namespace_id + document_id + chunk_index) for both databases. Enables reliable chunk→document→entity provenance. Migration script backfilled 15,000+ existing chunks.

### 2026-01-07 | Community Summarization (92/92 Communities, Sprint 77.3-77.4)
**Decision:** Generate LLM-powered summaries for all 92 detected communities in HotpotQA knowledge graph.
**Rationale:** Community summaries enable "Graph-Global" search mode (high-level topic matching). Batch job endpoint (POST /api/v1/admin/graph/communities/summarize) processes communities in parallel. 92/92 summaries generated successfully (0 failures). Average 150 tokens/summary, ~15s per community. Critical for hybrid retrieval quality.

### 2026-01-07 | Entity Connectivity as Domain Training Metric (Sprint 77.5, TD-095)
**Decision:** Implement connectivity evaluation (avg relations per entity) as domain type classifier (Factual: 0.3-0.8, Narrative: 1.5-3.0, Technical: 2.0-4.0, Academic: 2.5-5.0).
**Rationale:** Different domain types exhibit different connectivity patterns. Connectivity metric enables automatic domain type detection, informs chunking strategy (narrative requires more context), and provides quality signal for entity extraction. Endpoint: POST /api/v1/admin/domains/connectivity/evaluate. Benchmarked across 4 domains.

### 2026-01-08 | Entity→Chunk Expansion via MENTIONED_IN Traversal (Sprint 78.1, ADR-041)
**Decision:** Change graph search from returning entity descriptions (100 chars) to full document chunks (800-1800 tokens) via `(entity)-[:MENTIONED_IN]->(chunk)` Neo4j relationship traversal.
**Rationale:** LLM answer generation requires full context, not entity descriptions. 100-char descriptions insufficient for accurate answers. MENTIONED_IN relationships already exist from ingestion pipeline. Cypher query change simple (15 lines), massive impact: 4.5x more context per entity. Trade-off: +70ms latency (0.05s → 0.12s), but acceptable for 4.5x quality gain.

### 2026-01-08 | 3-Stage Semantic Entity Expansion (Sprint 78.2-78.3, ADR-041)
**Decision:** Implement SmartEntityExpander with 3-stage pipeline: (1) LLM entity extraction, (2) Graph N-hop expansion, (3) LLM synonym fallback, (4) BGE-M3 semantic reranking.
**Rationale:**
- Stage 1 (LLM): Better than keyword extraction (context-aware, auto-filters stop words)
- Stage 2 (Graph): Leverages domain knowledge (1-3 hops configurable)
- Stage 3 (Synonym): Fallback when graph sparse (only if < threshold)
- Stage 4 (Reranker): GPU-accelerated semantic ranking (optional)
**Impact:** 0-2 initial entities → 10-15 expanded entities (avg 7x expansion). Entity expansion: 0.4-0.9s depending on synonym fallback.

### 2026-01-08 | UI-Configurable Graph Expansion Settings (Sprint 78.4, Feature 78.4)
**Decision:** Expose 4 graph expansion settings via Admin UI: graph_expansion_hops (1-3), graph_min_entities_threshold (5-20), graph_max_synonyms_per_entity (1-5), graph_semantic_reranking_enabled (bool).
**Rationale:** Enable power users to tune graph search without code changes. Settings stored in Redis (similar to LLM config pattern from Sprint 64). Pydantic validation ensures valid ranges (ge/le constraints). Defaults optimized for general use (1 hop, 10 threshold, 3 synonyms, reranking enabled). UI deferred to Sprint 79 Feature 79.6 (8 SP).

### 2026-01-08 | RAGAS Deferral to Sprint 79 (Sprint 78.6, TD-096)
**Decision:** Defer RAGAS evaluation from Sprint 78 to Sprint 79 due to slow local LLM performance (GPT-OSS:20b 85.76s/eval, Nemotron3 Nano >600s/eval).
**Rationale:** RAGAS Few-Shot prompts (2903 chars) too complex for local LLMs. 15 evaluations × 85.76s = 1286s → timeout at 300s. Alternative verification: 20 unit tests (100% pass rate) + manual graph queries validate functionality. Sprint 79 will optimize RAGAS prompts using DSPy (target: 4x-10x speedup, ≥90% accuracy).

### 2026-01-08 | DSPy Framework for RAGAS Prompt Optimization (Sprint 79.1-79.5, Planned)
**Decision (Planned):** Use DSPy BootstrapFewShot + MIPROv2 to optimize RAGAS prompts for local LLMs.
**Rationale:** DSPy automates prompt compression via learned few-shot examples. BootstrapFewShot (for GPT-OSS:20b, Nemotron3 Nano): Generate 2 few-shot demos, use 1 labeled demo → 4x-10x speedup. MIPROv2 (if Qwen2.5:7b available): Generate 10 prompt candidates with instruction optimization → best prompt selected via metric. Training data: 80 labeled examples (4 metrics × 20). Target: GPT-OSS:20b <20s, Nemotron3 <60s, ≥90% accuracy.

---

## SPRINT 83: ER-EXTRACTION IMPROVEMENTS

### 2026-01-10 | Comprehensive Ingestion Logging (Sprint 83.1, Feature 83.1, 5 SP)
**Decision:** Implement centralized logging utilities with P50/P95/P99 percentile tracking, LLM cost aggregation, GPU VRAM monitoring, and extraction quality metrics.
**Rationale:** Production ingestion pipeline lacks observability (no latency tracking, no cost visibility, no GPU monitoring). Feature 83.1 adds `logging_utils.py` (337 LOC) with 7 utility functions: percentile calculation, phase summaries, LLM cost tracking, extraction quality metrics, chunk-entity provenance, memory snapshots (RAM + VRAM via pynvml). Structured logging enables bottleneck identification, cost optimization, and SLA monitoring. 22 unit tests (100% coverage).

### 2026-01-10 | 3-Rank LLM Fallback Cascade (Sprint 83.2, Feature 83.2, 8 SP)
**Decision:** Implement 3-rank cascade fallback strategy: Rank 1 (Nemotron3, 300s timeout) → Rank 2 (GPT-OSS:20b, 300s timeout) → Rank 3 (Hybrid SpaCy NER + LLM, 600s relations).
**Rationale:** Single-LLM extraction fragile (timeouts, parse errors, Ollama crashes). 3-rank cascade achieves 99.9% extraction success rate (vs ~95% single LLM). Rank 1 handles 95%+ cases (fast GPU inference on DGX Spark). Rank 2 fallback on Rank 1 failure (larger model, higher quality). Rank 3 hybrid uses instant SpaCy NER (multi-language: DE/EN/FR/ES) for entities, reserves expensive LLM (600s timeout) only for relations. Retry logic: Exponential backoff (1s → 2s → 4s → 8s) with tenacity. Ollama health monitoring: Periodic /api/health checks + auto-restart recommendation. 50+ tests (100% coverage).

### 2026-01-10 | Multi-Language SpaCy NER (Sprint 83.2, Feature 83.2)
**Decision:** Use SpaCy transformer-based NER models for multi-language entity extraction (de_core_news_lg, en_core_web_lg, fr_core_news_lg, es_core_news_lg).
**Rationale:** LLM-only extraction slow (30-60s per chunk, expensive tokens) and single-language (EN-optimized). SpaCy NER provides instant entity extraction (~50-100ms) with ~85% precision across German, English, French, Spanish (EU production requirements). Language auto-detection via heuristic-based detection. Entity type mapping: SpaCy labels (PER, ORG, LOC) → GraphEntity types. Hybrid approach: SpaCy entities (fast, cheap) + LLM relations (high quality). Trade-off: ~5-10% lower entity quality vs pure LLM, but 20-60x faster and enables Rank 3 fallback.

### 2026-01-10 | Gleaning Multi-Pass Entity Extraction (Sprint 83.3, TD-100, 5 SP)
**Decision:** Implement Microsoft GraphRAG-style gleaning with 0-3 configurable rounds: Round 1 (baseline extraction) → Completeness Check (logit bias YES/NO) → Round 2-N (extract missing entities) → Deduplication.
**Rationale:** Human annotators miss 20-40% of entities on first pass - same for LLMs (Microsoft GraphRAG research). Gleaning improves entity recall by asking LLM "Did I miss anything?" after initial extraction. Completeness Check uses logit bias (favor "NO" token) to reduce false positives. Continuation Prompt: "Extract ONLY the entities that were MISSED" with context-aware instruction. Semantic deduplication (exact match, substring match, confidence preservation) prevents duplicates across rounds. Cost-benefit: gleaning_steps=1 provides +20% recall for 2x cost (best ROI), gleaning_steps=2-3 yields +35-40% recall with diminishing returns. Configuration: gleaning_steps=0 (default, fast ingestion), gleaning_steps=1-2 (research/legal docs), gleaning_steps=3 (critical documents). 16 unit tests (100% coverage).

### 2026-01-10 | Two-Phase Upload Strategy (Sprint 83.4, Feature 83.4, 8 SP)
**Decision:** Implement two-phase upload: Phase 1 (Fast Upload, 2-5s response) → Phase 2 (Background Refinement, 30-60s async).
**Rationale:** Traditional upload blocks user 30-60s (full LLM extraction + graph indexing). Two-phase strategy provides immediate feedback: Phase 1 uses SpaCy NER (instant, multi-language) + Qdrant vector upload only → returns document_id + status="processing_background". Phase 2 runs full LLM extraction with gleaning + Neo4j graph indexing in background (Redis-tracked job queue with retry logic). User experience: 10-15x faster perceived upload time (2-5s vs 30-60s), no blocking, can upload multiple documents concurrently. Status API: GET /upload-status/{document_id} provides real-time progress (parsing → chunking → extraction → indexing). Retry logic: Exponential backoff, max 3 retries on failure. 14 tests (12 unit + 2 integration, 100% coverage).

### 2026-01-10 | Domain-Specific ER-Extraction Settings (Sprint 83.2, Feature 83.2)
**Decision:** Add `extraction_settings` field to DomainConfig for domain-specific extraction cascade configuration.
**Rationale:** Different domains require different extraction strategies (e.g., legal docs need gleaning_steps=2 for exhaustive entity extraction, technical docs use Rank 1 LLM only for speed). DomainConfig `extraction_settings` field (JSON in Neo4j) allows per-domain override of default cascade (Rank 1-3 models, timeouts, gleaning_steps). Future Sprint 84+ will implement UI for domain administrators to configure extraction strategy without code changes.

---

---

## SPRINT 75-93: EVALUATION, OPTIMIZATION & AGENTIC FRAMEWORK

### 2026-01-06 | Namespace Isolation Architecture (Sprint 75, ADR-045)
**Context:** Multi-tenant RAG system required isolation of documents across different users/domains. BM25 cache and Neo4j graphs risked cross-contamination without explicit namespace enforcement.

**Decision:** Implement namespace_id as primary key in all retrieval operations (Qdrant, BM25, Neo4j, Graphiti). Every ingestion operation tags with namespace, every retrieval filters by namespace. Cascade filtering through all 4 retrieval layers (Vector, BM25, Graph, Memory).

**Consequences:**
- Positive: Complete isolation, no cross-tenant data leakage, multi-tenant ready
- Negative: +3 SP for QA, +15% query latency for namespace filtering
- Mitigation: Index optimization on namespace_id (Qdrant payload filters, BM25 partition strategy)

### 2026-01-06 | DSPy Integration Planning (Sprint 75)
**Context:** RAGAS Few-Shot prompts (2903 chars) caused 85.76s timeouts per evaluation with local LLMs. RAGAS 0.3.9 not optimized for local inference.

**Decision:** Plan DSPy integration for Sprint 79 (CONDITIONAL). First attempt RAGAS 0.4.2 upgrade (feature 79.8) to test if framework improvements fix timeouts. Only proceed with DSPy if 0.4.2 doesn't reduce latency.

**Consequences:**
- Positive: RAGAS 0.4.2 may solve timeout problem natively, DSPy only as fallback
- Negative: 2-phase approach adds complexity, decision point mid-sprint
- Rationale: Reduce risk by testing simpler solution first before DSPy

### 2026-01-06 | .txt File Support for RAGAS (Sprint 76, Feature 76.1)
**Context:** RAGAS evaluation datasets (HotpotQA, RAGBench) primarily in .txt format. Ingestion pipeline only supported PDF/DOCX via Docling.

**Decision:** Add SimpleDirectoryReader fallback for plain text files. Parse .txt directly without extraction tools. Enable 15 HotpotQA files for RAGAS baseline.

**Consequences:** Enables RAGAS evaluation baseline, minor change (<50 LOC), no new dependencies

### 2026-01-07 | Critical BM25 Namespace Bug Fix (Sprint 77, TD-092)
**Context:** BM25 keyword search returned results from all namespaces regardless of namespace filter. Security/privacy issue - users could see chunks from other namespaces.

**Decision:** Fix BM25 cache key generation to include namespace_id. Add namespace filtering before RRF fusion. Verified with integration tests.

**Consequences:** Security fix (critical priority), broke 0 functionality, enables multi-tenant isolation

### 2026-01-07 | Chunk ID Alignment (Sprint 77, TD-093)
**Context:** Qdrant chunk IDs (SHA-256 hash) didn't match Neo4j chunk IDs (UUID). Citation/provenance tracking impossible - Qdrant chunk_id ≠ Neo4j chunk_id.

**Decision:** Unify to SHA-256(namespace_id + document_id + chunk_index) for both Qdrant and Neo4j. Run migration for 15,000+ existing chunks. Backward compatible chunk lookup.

**Consequences:** Enables reliable cross-database provenance, migration required, citation tracking now works

### 2026-01-07 | Community Summarization Batch Job (Sprint 77, Feature 77.4)
**Context:** LightRAG community detection identified 92 communities in HotpotQA graph, but no summaries. Graph-Global search mode requires community-level summaries for high-level context retrieval.

**Decision:** Generate LLM-powered summaries for all 92 communities via batch API endpoint (POST /api/v1/admin/graph/communities/summarize). Parallel processing with configurable batch size.

**Consequences:** Enables Graph-Global search mode, 15s total processing time, summaries enable topic-level retrieval

### 2026-01-08 | Entity→Chunk Expansion via MENTIONED_IN (Sprint 78, Feature 78.1, ADR-041)
**Context:** Graph search returned Entity descriptions (100 chars) instead of full document chunks. LLM answer generation lacked sufficient context.

**Decision:** Change Cypher query to traverse MENTIONED_IN relationships from entities to chunks. Return full chunk text (800-1800 tokens) instead of entity metadata. Backward compatible via GraphEntity.description field.

**Consequences:**
- Positive: 4.5x more context per entity (100 → 447 chars avg), RAGAS-ready
- Negative: +70ms latency (0.05s → 0.12s per entity), acceptable tradeoff
- Rationale: Quality improvement (4.5x context) far outweighs minor latency cost

### 2026-01-08 | 3-Stage Semantic Entity Expansion (Sprint 78, Feature 78.2, ADR-041)
**Context:** Manual stop words list (46 words) not scalable across domains. Entity extraction needed semantic awareness, not just text matching.

**Decision:** Implement 3-stage pipeline: (1) LLM entity extraction, (2) Graph N-hop expansion (1-3 hops), (3) LLM synonym fallback (if <threshold). Each stage configurable.

**Consequences:**
- Positive: Replaces fragile stop words, domain-agnostic, semantically aware
- Negative: 0.4-0.9s entity expansion time (3 LLM calls in worst case)
- Optimization: Stage 3 only triggered if graph expansion <10 entities (default threshold)

### 2026-01-08 | BGE-M3 Semantic Reranking for Graph Entities (Sprint 78, Feature 78.3)
**Context:** Expanded entities (13-15 total) still needed semantic ranking relative to query to improve relevance ordering.

**Decision:** Add Stage 4: Semantic reranking via BGE-M3 embeddings (1024-dim) and cosine similarity. Optional feature (configurable bool).

**Consequences:** GPU-accelerated, <1% latency impact, improves ranking quality

### 2026-01-08 | Graph Search Configuration UI Preparation (Sprint 78, Feature 78.5)
**Context:** 4 new Backend settings for graph search (hops, threshold, synonyms, reranking), but no frontend UI for admins. Only .env configurable.

**Decision:** Add 4 settings to config.py with Pydantic validation ranges. Store in Redis (similar to Sprint 64 LLM config). UI implementation deferred to Sprint 79 (feature 79.6).

**Consequences:** Enables admin configuration without restarts, UI to follow in Sprint 79

### 2026-01-09 | RAGAS 0.4.2 Upgrade Decision (Sprint 79, Feature 79.8)
**Context:** RAGAS 0.3.9 timeouts (85.76s per eval) made evaluation impossible. RAGAS 0.4.2 released with GPT-5 support and Universal Provider.

**Decision:** Upgrade to RAGAS 0.4.2 with conditional follow-up: if timeouts persist, implement DSPy (features 79.1-79.5). If 0.4.2 solves timeout, skip DSPy (save 21 SP).

**Consequences:**
- Positive: Potential 2-3x speedup from new framework optimizations
- Negative: Breaking API changes (ground_truths → reference, etc.)
- Rationale: 2-phase approach minimizes risk - test simple solution first

### 2026-01-10 | RAGAS Comprehensve Logging Infrastructure (Sprint 83, Feature 83.1)
**Context:** Ingestion pipeline lacked observability - no latency tracking, no cost visibility, no GPU monitoring, no extraction quality metrics.

**Decision:** Implement centralized logging utilities (logging_utils.py, 337 LOC) with P50/P95/P99 percentiles, LLM cost aggregation, GPU VRAM monitoring (pynvml), extraction quality scoring, chunk-entity provenance tracking.

**Consequences:** Production observability enabled, cost tracking (critical for Alibaba Cloud budget), SLA monitoring enabled

### 2026-01-10 | 3-Rank LLM Fallback Cascade (Sprint 83, Feature 83.2, ADR-049)
**Context:** Single-LLM extraction fragile (timeouts, parse errors, Ollama crashes). 95% success rate insufficient for production.

**Decision:** Implement fallback cascade: Rank 1 (Nemotron3, 300s) → Rank 2 (GPT-OSS:20b, 300s) → Rank 3 (Hybrid SpaCy NER + LLM relations, 600s). Retry logic with exponential backoff (1s → 2s → 4s → 8s).

**Consequences:**
- Positive: 99.9% extraction success rate (vs 95%), Ollama health monitoring added
- Negative: Rank 3 fallback slower (30-60s), but acceptable for production
- Impact: Mission-critical resilience improvement

### 2026-01-10 | Multi-Language SpaCy NER (Sprint 83, Feature 83.2)
**Context:** LLM-only entity extraction single-language (EN-optimized), slow (30-60s per chunk), expensive (token costs).

**Decision:** Use SpaCy transformer-based NER for instant multi-language entity extraction (de_core_news_lg, en_core_web_lg, fr_core_news_lg, es_core_news_lg). 20-60x faster, ~85% precision across languages. Hybrid: SpaCy entities (fast) + LLM relations (high quality).

**Consequences:**
- Positive: 20-60x faster entity extraction, multi-language support, ~5-10% lower quality acceptable
- Rationale: Quality/speed tradeoff justified for production-scale ingestion

### 2026-01-10 | Gleaning Multi-Pass Entity Extraction (Sprint 83, Feature 83.3, TD-100)
**Context:** Entity extraction (LLM or SpaCy) misses 20-40% of entities on first pass, similar to human annotators (Microsoft GraphRAG research).

**Decision:** Implement gleaning with 0-3 configurable rounds: Round 1 (baseline) → Completeness check (logit bias) → Rounds 2-N (extract missing) → Dedup. Semantic deduplication prevents duplicates across rounds.

**Consequences:**
- Positive: +20% recall (gleaning_steps=1, best ROI), +35-40% with steps=2-3
- Negative: 2x-3x cost increase, gleaning_steps=0 for fast ingestion, 1-2 for research/legal
- Rationale: Configuration enables use-case selection (bulk vs. quality-critical)

### 2026-01-10 | Two-Phase Upload Strategy (Sprint 83, Feature 83.4)
**Context:** Traditional upload blocks user 30-60s (full LLM extraction + graph indexing). Bad UX for document upload.

**Decision:** Phase 1 (Fast, 2-5s): SpaCy NER + Qdrant upload only → returns document_id immediately. Phase 2 (Background, 30-60s): Full LLM extraction + Neo4j indexing in Redis job queue. Status API provides real-time progress (parsing → chunking → extraction → indexing).

**Consequences:**
- Positive: 10-15x faster perceived upload (2-5s vs 30-60s), concurrent uploads enabled
- Negative: Eventual consistency (2-60s delay for full indexing)
- UX Impact: Critical for production usability

### 2026-01-10 | BGE-M3 Replaces BM25 for Hybrid Search (Sprint 87, Feature 87.1)
**Context:** BM25 keyword search deprecated in favor of BGE-M3 native dense+sparse hybrid. FlagEmbedding service provides both vector types from single model.

**Decision:** Migrate Vector + BM25 channel to MultiVectorHybridSearch using BGE-M3. Qdrant multi-vector collection with server-side RRF fusion (replaces Python-side RRF). Single embedding service call returns both dense (1024-dim) and sparse (lexical weights) vectors.

**Consequences:**
- Positive: Simpler architecture (1 embedding model, 1 Qdrant collection), server-side RRF eliminates desync
- Negative: BM25 pickle index removed (1 less file), learning curve for multi-vector Qdrant
- Migration: Async embedding fix for LangGraph compatibility (added awaits for embedding calls)

### 2026-01-11 | Recursive LLM Adaptive Scoring with Granularity Mapping (Sprint 92, ADR-052)
**Context:** Large documents (320K tokens, 10x context window) require hierarchical processing. Flat 3-level recursion insufficient - need adaptive scoring based on query granularity.

**Decision:** Implement C-LARA granularity mapping (Coarse-grained → Medium → Fine-grained) to determine recursion depth automatically. Query intent drives processing strategy: high-level summaries vs. detailed analysis vs. specific fact-finding.

**Consequences:**
- Positive: Adaptive processing reduces token waste, 40-60% efficiency gain
- Latency: 9-15s per document (tractable)
- Enables: Full research paper analysis, systematic document analysis

### 2026-01-14 | Intent-Based Skill Router Architecture (Sprint 91, ADR-050)
**Context:** Skill system loaded all 4 skills (~4,000 tokens wasted) for every query. No task decomposition capability. LangGraph agents lacked multi-skill orchestration.

**Decision:** Implement intent-based skill router using C-LARA classifier (95.22% accuracy, ~40ms). Router activates only relevant skills per query intent. Planner skill decomposes complex queries into 3-10 subtasks.

**Consequences:**
- Positive: 30-35% token savings (4,000 → 2,500), 8-12% Context Recall improvement, 15-20% latency reduction
- New Capability: Research agents, planning agents, analysis agents enabled
- Rationale: Selective skill loading matches human expert specialization

### 2026-01-15 | LangGraph 1.0 Migration (Sprint 93, ADR-055)
**Context:** LangGraph 0.6 API changed significantly in 1.0. ToolNode, InjectedState, error recovery patterns redesigned. Team must migrate for continued support.

**Decision:** Migrate to LangGraph 1.0 adopting new patterns: ToolNode with handle_tool_errors=True (built-in retry), InjectedState for skill context in tools, durable execution for long-running chains.

**Consequences:**
- Positive: Built-in error recovery, state injection simplifies skill-aware tools, better durable execution
- Negative: Breaking changes require code migration (40+ files affected)
- Timeline: Sprint 93 (14-18 days estimated)

### 2026-01-15 | Tool Composition Framework (Sprint 93, Feature 93.1)
**Context:** Tools (browser, filesystem, API) need composition for complex workflows. LangGraph 1.0 ToolNode enables this pattern.

**Decision:** Implement ToolNode-based composition with LangGraph 1.0 patterns. Chain multiple tools (web search → content fetch → analysis). Policy guardrails enforce per-skill tool permissions (skill X can use browser, file tools, but not API tool).

**Consequences:** +40% automation capability, secure skill-tool access via permission system

---

## Sprint 124 Decisions (2026-02-06)

### 2026-02-06 | gpt-oss:120b Benchmark for RAGAS Phase 1 (Sprint 124, Feature 124.5)
**Context:** Nemotron-3-Nano Q4_K_M (31.6B) produces poor ER extraction quality (100% RELATES_TO). Need larger model for RAGAS Phase 1 benchmark baseline.

**Decision:** Deploy gpt-oss:120b (MXFP4, 75GB VRAM) via Ollama for bulk ingestion benchmark. Increase Ollama memory limit from 64GB to 100GB.

**Consequences:**
- Positive: Higher quality entity extraction (854 entities, 931 relations from 28 documents)
- Negative: Ollama max 4 concurrent requests → HTTP 000 timeouts, stuck at 28/498 documents
- Negative: 100% RELATES_TO relations (generic extraction prompt)
- Timeline: Sprint 124 (benchmark only, ingestion incomplete)

### 2026-02-06 | Environment-Variable LLM Model Selection (Sprint 124, Feature 124.6)
**Context:** Model name was hardcoded in relation_extractor.py and extraction_cascade.py. Switching models for benchmarking required code changes.

**Decision:** Introduce `LIGHTRAG_LLM_MODEL` environment variable for model selection. Both relation_extractor.py and extraction_cascade.py read from env var with fallback to nemotron-3-nano:128k.

**Consequences:** Zero-code model switching via .env or docker-compose, enables rapid A/B testing

### 2026-02-06 | Configurable LLM Thinking Mode (Sprint 124, Feature 124.7)
**Context:** Nemotron3 Nano's "thinking" mode (CoT reasoning) was hardcoded off (`think=False`). Some tasks benefit from reasoning.

**Decision:** Introduce `AEGIS_LLM_THINKING` environment variable (true/false). Applied to both regular and streaming LLM execution paths in AegisLLMProxy.

**Consequences:** Configurable per deployment, enables reasoning benchmarks without code changes

---

## Sprint 125 Decisions (2026-02-06)

### 2026-02-06 | vLLM as Extraction Inference Engine (Sprint 125, Feature 125.1) — ADR-059
**Context:** Ollama bottleneck: max 4 concurrent requests, HTTP 000 timeouts at scale. NVIDIA txt2kg cookbook uses vLLM for 19× throughput over Ollama. Red Hat benchmarks: vLLM 793 tok/s vs Ollama 41 tok/s (A100 40GB).

**Decision:** Add vLLM as separate Docker container with `--profile ingestion` for on-demand start. Dual-engine architecture: Ollama for chat + vLLM for extraction. VRAM budget: Ollama 25GB + vLLM ~18GB = 43GB of 128GB available.

**Consequences:**
- Positive: 19× throughput, 256+ concurrent batching, continuous batch scheduling
- Positive: NVFP4 optimized for Blackwell sm_121 (4× FLOPS over BF16)
- Negative: Additional container complexity, ~60s cold start
- Trade-off: Different model format (HuggingFace NVFP4 vs Ollama GGUF)

### 2026-02-06 | Nemotron-3-Nano-30B-A3B-NVFP4 for Extraction (Sprint 125, Feature 125.1)
**Context:** Need high-quality extraction model optimized for vLLM on DGX Spark. Compare: gpt-oss:120b (75GB, 20 tok/s), Nemotron Q4_K_M (25GB, 74 tok/s).

**Decision:** Use nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4 — 30B total / 3.5B active (MoE), ~18GB VRAM, 60-80 tok/s expected on vLLM. Mamba2 + MoE + Attention hybrid architecture. Up to 256K context, 86.7% AIME 2025.

**Consequences:** 3.3× throughput vs dense models (only 10% parameter activation), fits alongside Ollama in 128GB VRAM

### 2026-02-06 | Specific Relation Type Extraction (Sprint 125, Feature 125.3)
**Context:** Sprint 124 benchmark: 100% RELATES_TO relations (931/931). Root cause: DSPy extraction prompt generates generic types. NVIDIA txt2kg uses Subject-Predicate-Object triples.

**Decision:** Update DSPY_OPTIMIZED_RELATION_PROMPT to enforce specific S-P-O relation types (WORKS_AT, CREATED, LOCATED_IN, USES, etc.). Add relation type validation in relation_extractor.py. Target: <30% RELATES_TO, >70% specific types.

**Consequences:** Dramatically improved graph query quality, enables graph-based reasoning for RAGAS evaluation

### 2026-02-06 | DDC+FORD Hybrid Domain Taxonomy (Sprint 125, Feature 125.8) — ADR-060
**Context:** Domain-aware extraction requires a principled taxonomy. Industry standards (NAICS, GICS) classify businesses, not knowledge. Need ~35 domains that cover all document types with ontology-backed entity/relation vocabularies. Empirical BGE-M3 testing on DGX Spark validated 35 domains with 0 danger pairs, 0 warning pairs.

**Decision:** Use DDC (Dewey Decimal, 138+ countries) + FORD (OECD Fields of R&D) as basis for 35 seed domains across 5 sectors. Store in `data/seed_domains.yaml` with DDC/FORD codes, keywords, ontology references, and entity/relation type mappings.

**Consequences:** Standards-based, traceable taxonomy. No ad-hoc domain naming. Every domain linked to established ontologies (SNOMED-CT, FIBO, ACM CCS, etc.).

### 2026-02-06 | Two-Tier Entity/Relation Type System (Sprint 125, Feature 125.8) — ADR-060
**Context:** Need domain-specific entity types (e.g., DISEASE, MEDICATION for medicine) without exploding Prometheus cardinality (260+ types × 3 models), Neo4j labels (260+ indexes), or UI colors (260+ types).

**Decision:** Tier 1: 15 universal entity types + 21 universal relation types (in Neo4j labels, Prometheus, UI). Tier 2: 8-12 domain-specific sub-types per domain (only in extraction prompts and Neo4j property `sub_type`, mapped to Tier 1). Total per extraction prompt: ~25 entity types + ~28 relation types = ~150-200 tokens overhead.

**Consequences:** Prometheus sees only 15 labels (not 260+). Neo4j has 15 labels (not 260+). UI shows 15 colors. LLM gets focused domain context per chunk.

### 2026-02-06 | Deployment Profiles for Domain Activation (Sprint 125, Feature 125.8) — ADR-060
**Context:** Research shows most companies use 1-5 domains (65% use 1-2). Even Samsung/Berkshire Hathaway max ~7-8 domains. Universities are the only case needing all 35. Loading 35 domains for a law firm (2 domains) wastes resources and adds noise.

**Decision:** Pre-defined deployment profiles (pharma, law_firm, engineering, software, etc.) that activate only relevant domains. Profile selected at setup. University profile activates all 35. Custom profile for manual selection.

**Consequences:** Typical deployment: 15 universal + (3 domains × 10 sub-types) = ~45 total types. Minimal overhead.

### 2026-02-06 | Ontology-Backed Entity/Relation Vocabularies (Sprint 125, Feature 125.8) — ADR-060
**Context:** 32/35 proposed domains have free, formal ontologies (SNOMED-CT for medicine, FIBO for finance, ACM CCS for CS, GEMET for environment, NATOTerm for defense, etc.). Entity/relation sub-types should derive from these standards, not be invented ad-hoc.

**Decision:** Each domain in seed_domains.yaml references its ontology sources with URLs and licenses. Domain sub-types are extracted from these ontologies. Relation hints are domain-specific (e.g., "TREATS → Medication → Disease" for medicine).

**Consequences:** Entity/relation vocabularies are traceable to international standards. Enables future deep integration with ontology APIs (e.g., SNOMED-CT FHIR, FIBO SPARQL).

### 2026-02-06 | LightRAG Removal — Direct Neo4j (Sprint 127, planned) — ADR-061
**Context:** Comprehensive audit revealed AegisRAG uses only 3 functions from `lightrag-hku` (Neo4j driver init, `ainsert_custom_kg`, `aquery`). 45+ files / ~12,000 LOC of extraction, dedup, community detection, graph query, and monitoring are 100% custom. Data is written to Neo4j twice (LightRAG internal + AegisRAG custom schema).

**Decision:** Remove `lightrag-hku` dependency in Sprint 127. Replace Neo4j driver with existing `neo4j_client.py`, eliminate `ainsert_custom_kg()` (double storage), replace `rag.aquery()` with `DualLevelSearch` in `maximum_hybrid_search.py`. Verify with RAGAS benchmark comparison (Sprint 126 baseline vs 127 post-removal).

**Consequences:** ~50% fewer Neo4j writes during ingestion. One Neo4j client instead of two. Eliminates format conversion overhead. ADR-005 (LightRAG statt GraphRAG) superseded. Risk: RRF quality in hybrid search — mitigated by RAGAS comparison.

### 2026-02-06 | Entity Deduplication via Existing EntityCanonicalizer (Sprint 125)
**Context:** Sprint 125 originally planned a new EntityRelationNormalizer (125.3b, 3 SP) inspired by txt2kg. Audit of existing `entity_canonicalization.py` (Sprint 85) revealed it already implements 3-strategy matching: exact normalization (lowercase + underscore), Levenshtein distance (≤2 edits for short names), and BGE-M3 embedding similarity (≥0.85 threshold).

**Decision:** Drop Feature 125.3b. Existing EntityCanonicalizer is sufficient. Unknown entity types from LLM output handled by a new output-parser validation step in 125.3 that maps to nearest universal type.

**Consequences:** 3 SP saved in Sprint 125. No new dedup code needed. Sprint 125 reduced from 53 to 45 SP.

---

### 2026-02-06 | Structured Table Ingestion Investigation (Sprint 127.5)
**Context:** LightRAG audit revealed unused Excel/CSV ingestion capability (via textract). LightRAG's approach is basic text extraction that loses tabular structure. Docling CUDA already extracts tables from PDFs as structured `TableData` objects with cell coordinates, rows, and columns. Tabular data (financial reports, specs, benchmarks) loses meaning when chunked as flat text.

**Decision:** Add Investigation Spike (127.5, 3 SP) to evaluate three strategies: (A) Direct DB storage with SQL/Cypher queries, (B) Table-aware chunking preserving row/column structure, (C) Hybrid approach with NL-to-SQL agent for large tables. Deliverable: ADR with recommendation + prototype.

**Consequences:** Sprint 127 grows from 5 to 8 SP. Opens path for structured data retrieval that text-based RAG cannot handle well (e.g., "What was NVIDIA's revenue in Q3 2025?" requires cell lookup, not semantic similarity).

---

---

## SPRINT 126: LLM ENGINE MODE + ADMIN UI POLISH + DOMAIN SEEDING

### 2026-02-07 | Runtime LLM Engine Mode Configuration (Sprint 126.1) — ADR-062
**Context:** vLLM (40.7GB) + Ollama (24GB) cannot run simultaneously on DGX Spark (128GB unified memory). Deployments need flexibility: instant API startup for chat, or on-demand vLLM for bulk ingestion.

**Decision:** Configurable engine mode (`vllm` / `ollama` / `auto`) stored in Redis. PUT `/api/v1/admin/llm/engine` endpoint enables hot-reload without container restart. AegisLLMProxy routes extraction tasks to vLLM (793 tok/s, 256+ concurrent) when mode permits, falls back to Ollama (41 tok/s, 4 concurrent).

**Consequences:**
- ✅ Zero-startup `ollama` mode (60s cold start eliminated)
- ✅ Hot-reload via Redis (30s local cache)
- ✅ Graceful degradation (fallback routing)
- ⚠️ Operator must understand tradeoffs

### 2026-02-07 | DeploymentProfilePage Save Bug Fix (Sprint 126.2)
**Context:** Admin UI deployment profile save returned "Failed to save" error despite backend accepting request.

**Root Cause:**
- Wrong API endpoint URL (`/api/v1/admin/` → correct: `/api/v1/retrieval/admin/`)
- Form data sent instead of JSON body
- Missing auth token (raw fetch() → apiClient.put())
- Backend expected `request.json()` but received `Form(...)`

**Decision:** Fix all layers:
1. Frontend: Update URL, use JSON body, switch to apiClient
2. Backend: Change parameter from Form(...) to request.json()

**Consequences:** Deployment profile changes now persist correctly, unblocking profile-based domain activation testing.

### 2026-02-07 | AdminNavigationBar Deployment on All ~28 Admin Pages (Sprint 126.3)
**Context:** Admin users navigated via "Back to Admin Dashboard" links, requiring clicks to return home between pages. Poor UX for rapid domain/LLM config changes.

**Decision:** Replace "Back to Admin" links with persistent AdminNavigationBar at top of all ~28 admin pages. Navbar includes quick-nav links to: Dashboard, Domains, LLM Config, Deployment, Namespaces, Entity Management.

**Consequences:**
- ✅ Direct navigation between admin sections
- ✅ Consistent visual hierarchy
- ✅ Reduced clicks per workflow (30% fewer for typical admin session)

### 2026-02-07 | Domain Seeding into Neo4j (Sprint 126.4)
**Context:** Deployment profiles reference domains from `seed_domains.yaml` (35 domains: pharma, law, finance, etc.). But domains were never seeded into Neo4j — DeploymentProfilePage showed "Domain not found" errors when activating profiles.

**Decision:** Run `seed_all_domains()` to load `seed_domains.yaml` into Neo4j:
- Creates `:Domain` nodes with properties (name, description, ontology_url, entity_types, relation_types)
- Establishes `:PART_OF` relationships (e.g., `DISEASE → medicine_domain`)
- Validates against entity/relation type constraints

**Consequences:** All 35 domains now available in deployment profiles, unblocking domain-specific extraction and UI testing.

### 2026-02-07 | Community Detection as Nightly Batch Job (Sprint 126.3)
**Context:** Community detection (GDS Leiden/Louvain) during ingestion adds ~625s per document (732s total → 107s without). For bulk ingestion, this is unacceptable.

**Decision:** Make community detection a scheduled batch job instead of running during ingestion. APScheduler cron triggers at 5:00 AM daily. Manual trigger via POST `/api/v1/admin/community-detection/trigger`. New env var `GRAPH_COMMUNITY_DETECTION_MODE=scheduled` (default: `inline` for backward compat).

**Consequences:**
- ✅ 85% faster ingestion (732s → ~107s per document)
- ✅ Community quality unchanged (same algorithms, just deferred)
- ⚠️ Communities may be stale for up to 24h until next batch run
- Manual trigger available for immediate refresh

### 2026-02-07 | DSPy EntityExtractionSignature Fix (Sprint 126.4)
**Context:** DSPy EntityExtractionSig used `list[str]` output, producing unstructured entity names without types. This caused all entities to be stored as generic "ENTITY" type, defeating ADR-060's 15 universal entity types.

**Decision:** Change DSPy signatures to produce typed dicts: EntityExtractionSig → `list[dict[str, str]]` with `{name, type, description}`, RelationExtractionSig → `list[dict[str, str]]` with `{source, target, type, description}`. Added backward-compatible fallback for old string format. Normalize existing Neo4j domain training data.

**Consequences:**
- ✅ DSPy-trained prompts now produce typed entities matching ADR-060
- ✅ Backward compatible with old training data
- ✅ Training data normalization handles legacy formats

### 2026-02-07 | NULL Relation-Type Backfill (Sprint 126.5)
**Context:** Sprint 124 legacy data contained 1,021 relations with NULL types in Neo4j (from gpt-oss:120b generic extraction before S-P-O pipeline fix in Sprint 125).

**Decision:** Run idempotent backfill script (`scripts/backfill_relation_types.py`) that pattern-matches relation descriptions to assign specific types: CONTAINS (89), PART_OF (45), USES (38), LOCATED_IN (21), CREATED_BY (19), etc. Remaining 809 unmatched relations get RELATED_TO (acceptable fallback).

**Consequences:**
- ✅ 0 NULL relations remaining (was 1,021)
- ✅ 212 relations got specific types (20.8%)
- ✅ 809 relations set to RELATED_TO (79.2%) — acceptable for legacy data
- ✅ Idempotent — safe to re-run

### 2026-02-07 | Domain Sub-Type Pipeline — YAML Factory Defaults with Neo4j Runtime Overrides (Sprint 126.6)
**Context:** ADR-060 defines 15 universal entity types + domain-specific sub-types. But LLM extraction outputs domain-specific types (e.g., DISEASE, MEDICATION) that need mapping to universal types while preserving the sub-type for fine-grained queries.

**Decision:** Implement 4-tier prompt priority system: (1) DSPy-trained domain prompts, (2) domain-enriched prompts (universal types + domain sub-types from Neo4j), (3) generic ADR-060 prompts, (4) legacy prompts. YAML `seed_domains.yaml` provides 253 entity aliases + 43 relation aliases as factory defaults. Neo4j `:Domain` nodes store `entity_sub_type_mapping` and `relation_hints` as runtime overrides. Async `_refresh_domain_type_mappings_from_db()` loads at extraction time. Cache invalidation on PUT `/domains/{name}`.

**Consequences:**
- ✅ Sub-types preserved through entire pipeline (LLM → extraction_service → Neo4j property `sub_type`)
- ✅ Factory defaults from YAML, runtime overrides from Neo4j
- ✅ API CRUD for domain type mappings (DomainCreateRequest/UpdateRequest include mapping fields)
- ✅ No LLM prompt token budget increase (sub-types only in domain-enriched tier)

---

**Last Updated:** 2026-02-07 (Sprint 126)
**Total Decisions Documented:** 173 (+7 from Sprint 126)
**Current Sprint:** Sprint 126 ✅ Complete
**Next Sprint:** Sprint 127 (LightRAG Removal — Direct Neo4j), Sprint 128 (Domain Editor UI + Table Ingestion)
