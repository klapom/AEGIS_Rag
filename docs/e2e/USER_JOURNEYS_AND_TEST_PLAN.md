# AEGIS RAG - Complete User Journeys & E2E Test Plan

**Status:** Comprehensive Mapping
**Created:** 2025-12-17
**Last Updated:** 2026-01-15 (Sprint 92 - Complete Feature Coverage)
**Purpose:** Map all user journeys and design complete E2E test coverage

---

## Recent Updates (Sprints 72-92)

### Sprint 92 Features (2026-01-15)
- **FlagEmbedding Warmup:** Model pre-loading at API startup (40s→<1s first query)
- **Ollama GPU Fix:** 4x speed improvement (19→77 tok/s)
- **Deep Research UI Enhancements:** 4 visualization levels (plan/search/evaluate/summary)
- **Graph Search Performance:** 17-19s→<2s (89% faster)
- **Context Relevance Guard:** Anti-hallucination threshold (0.3 default)
- **Docker Frontend:** Containerized React deployment on port 80
- **Sparse/Dense UI Counts:** Search result breakdown display
- **Community Detection Fix:** GDS label compatibility (2,387 communities)
- **Recursive LLM Scoring:** ADR-052 adaptive entity scoring

### Sprint 87-88 Features (2026-01-13)
- **BGE-M3 Native Hybrid:** Replaces BM25 with learned sparse vectors
- **Qdrant Multi-Vector:** Dense + Sparse in same collection
- **Server-Side RRF:** Fusion computed in Qdrant (no Python merge)
- **RAGAS Phase 2:** Tables + Code evaluation (T2-RAGBench, MBPP)

### Sprint 72-73 Features (2026-01-03)
- **MCP Tool Management UI:** Server connect/disconnect, tool execution, health monitoring
- **Memory Management UI:** 3-layer stats (Redis/Qdrant/Graphiti), search, consolidation
- **Domain Training UI:** Data augmentation, batch upload, domain details
- **E2E Test Infrastructure:** 620+ tests, 100% pass rate

---

## Frontend Routes Overview

### Public Routes
```
/login                     → LoginPage (JWT Authentication)
/share/:shareToken         → SharedConversationPage (Public Conversation Sharing)
```

### Protected Routes (Require Authentication)

#### Main Application
```
/                          → HomePage (Chat Interface)
/search                    → SearchResultsPage (Search Results Display)
/settings                  → Settings (User Settings, Theme, Retrieval Mode)
```

#### Admin Routes (Sprint 72+ Updated)
```
/admin                     → AdminDashboard (Consolidated Admin Overview)
/admin/tools               → MCPToolsPage (MCP Server & Tool Management) [NEW Sprint 72]
/admin/memory              → MemoryManagementPage (3-Layer Memory Debug) [NEW Sprint 72]
/admin/indexing            → AdminIndexingPage (Document Indexing Management)
/admin/graph               → GraphAnalyticsPage (Knowledge Graph Visualization)
/admin/graph-ops           → AdminGraphOpsPage (Graph Operations) [NEW Sprint 79]
/admin/communities         → GraphCommunitiesPage (Community Detection) [NEW Sprint 79]
/admin/costs               → CostDashboardPage (LLM Cost Tracking)
/admin/llm-config          → AdminLLMConfigPage (LLM Configuration)
/admin/domain-training     → DomainTrainingPage (DSPy Domain Training)
/admin/upload              → UploadPage (Document Upload with Domain Classification)
```

#### Health & Monitoring
```
/health                    → HealthDashboard (System Health Monitoring)
```

---

## Complete User Journeys

### Journey 1: MCP Tool Management (Sprint 72.1)

**User Goal:** Manage MCP servers and execute tools from the admin UI

#### Steps:
1. **Navigate to MCP Tools** (`/admin/tools`)
   - Click "Admin" in navigation
   - Click "MCP Tools" link
   - See server list with status badges

2. **Connect MCP Server**
   - View server list (filesystem, web-search, database)
   - See status badges (connected/disconnected/error)
   - Click "Connect" button on disconnected server
   - Watch status update to "connected"

3. **Execute Tool**
   - Select server → tools panel shows available tools
   - Select tool (e.g., `read_file`)
   - Enter parameters (file path, timeout)
   - Click "Execute"
   - View result (success: content, error: message)

4. **Monitor Health**
   - View health statistics (connected/disconnected/error counts)
   - Auto-refresh every 30 seconds
   - Export execution logs

#### Test Coverage:
- **Test File:** `frontend/e2e/tests/admin/mcp-tools.spec.ts`
- **Tests:** 15 tests covering all MCP Tool Management features
- **Data Attributes:** `mcp-tools-page`, `mcp-server-card-*`, `tool-selector`, `execute-button`

#### API Endpoints:
```
GET  /api/v1/mcp/servers                    → List all servers
POST /api/v1/mcp/servers/{name}/connect     → Connect server
POST /api/v1/mcp/servers/{name}/disconnect  → Disconnect server
GET  /api/v1/mcp/tools                      → List all tools
POST /api/v1/mcp/tools/{name}/execute       → Execute tool
GET  /api/v1/mcp/health                     → Health statistics
```

---

### Journey 2: Memory Management (Sprint 72.3)

**User Goal:** Debug and manage 3-layer memory system (Redis, Qdrant, Graphiti)

#### Steps:
1. **Navigate to Memory Management** (`/admin/memory`)
   - Click "Admin" in navigation
   - Click "Memory Management" link
   - See 3 tabs: Statistics, Search, Consolidation

2. **View Memory Statistics** (Tab: Stats)
   - **Redis Stats:** Keys count, memory MB, hit rate %
   - **Qdrant Stats:** Documents count, size MB, avg latency
   - **Graphiti Stats:** Episodes, entities, avg latency
   - Click "Refresh" to update stats

3. **Search Memory** (Tab: Search)
   - Enter search query
   - Filter by: user ID, session ID, date range, layer
   - View results with relevance scores
   - See layer indicator (Redis/Qdrant/Graphiti)
   - Export results as JSON

4. **Trigger Consolidation** (Tab: Consolidation)
   - View consolidation history (past runs)
   - Click "Trigger Consolidation"
   - Watch progress (items processed/consolidated)
   - See completion status

#### Test Coverage:
- **Test File:** `frontend/e2e/tests/admin/memory-management.spec.ts`
- **Tests:** 10 tests covering all Memory Management features
- **Data Attributes:** `memory-management-page`, `tab-stats`, `redis-stats`, `search-results`

#### API Endpoints:
```
GET  /api/v1/memory/stats                   → Memory statistics
POST /api/v1/memory/search                  → Search memory
GET  /api/v1/memory/consolidate/status      → Consolidation status
POST /api/v1/memory/consolidate             → Trigger consolidation
GET  /api/v1/memory/session/{id}/export     → Export session memory
```

---

### Journey 3: Deep Research Mode (Sprint 63, Enhanced Sprint 92)

**User Goal:** Conduct multi-step research with progress tracking

#### Steps:
1. **Enable Research Mode** (Chat Interface)
   - Toggle research mode switch
   - Switch persists in localStorage

2. **Submit Research Query**
   - Enter complex question
   - Press Enter or click Send

3. **Watch Progress Tracker** (Sprint 92.3 Enhanced)
   - **Plan Phase:** See generated sub-queries with relevance scores
   - **Search Phase:** View chunks found per sub-query (count + preview)
   - **Evaluate Phase:** See relevance scores and quality labels
   - **Summary Phase:** Display selected chunks for final response

4. **Review Research Results**
   - Read synthesized answer
   - View research sources with quality metrics
   - See research statistics (queries run, sources found, duration)
   - Optional: View web search results (if enabled)

5. **Interrupt if Needed**
   - Click "Stop Research" button
   - Research halts and shows partial results

#### Test Coverage:
- **Test File:** `frontend/e2e/research-mode.spec.ts`
- **Tests:** 12 tests covering Deep Research features
- **Sprint 92 Additions:** 4 new visualization level tests needed

#### API Endpoints:
```
POST /api/v1/chat/research      → Start research (SSE streaming)
GET  /api/v1/research/status    → Research progress
POST /api/v1/research/stop      → Stop research
```

---

### Journey 4: Hybrid Search with BGE-M3 (Sprint 87)

**User Goal:** Search documents using 4-signal hybrid retrieval

#### Steps:
1. **Navigate to Chat** (`/`)
   - See welcome screen with quick prompts

2. **Enter Search Query**
   - Type query in chat input
   - Select search mode: Hybrid (default), Vector, Sparse, Graph
   - Optional: Select namespaces/domains
   - Press Enter

3. **Watch Phase Progress** (Real-time)
   - Intent Classification (query analysis)
   - **Dense Search** (BGE-M3 1024-dim vectors) [Sprint 87]
   - **Sparse Search** (BGE-M3 learned lexical) [Sprint 87 - replaces BM25]
   - Graph Local (entity relationships)
   - Graph Global (community summaries)
   - RRF Fusion (server-side in Qdrant) [Sprint 87]
   - Reranking (cross-encoder)
   - LLM Generation

4. **Review Results**
   - Streaming answer with citations
   - **Sparse/Dense Counts** displayed [Sprint 92.10]
   - **Graph Hops Count** displayed [Sprint 92.9]
   - Click citations to view source chunks
   - Timing metrics for each phase [Sprint 92.8 fix]

#### Test Coverage:
- **Existing Tests:** `frontend/e2e/search/search.spec.ts`, `search-features.spec.ts`
- **Sprint 87 Additions:** BGE-M3 hybrid mode tests needed
- **Sprint 92 Additions:** Sparse/Dense counts, timing metrics tests

---

### Journey 5: Document Upload & Ingestion (Sprint 83 Enhanced)

**User Goal:** Upload documents with fast feedback and background processing

#### Steps:
1. **Navigate to Upload** (`/admin/upload`)
   - See upload dropzone

2. **Upload Documents**
   - Drag & drop files OR click to select
   - **Fast Upload Response** (2-5s) [Sprint 83.4]
   - See domain classification with confidence scores

3. **Background Processing**
   - **SpaCy NER** runs first (fast, <5s)
   - **3-Rank LLM Cascade** refines in background [Sprint 83.2]
     - Rank 1: Nemotron3 (local, fast)
     - Rank 2: GPT-OSS:20b (fallback)
     - Rank 3: Hybrid SpaCy+LLM (final fallback)
   - **Gleaning** for +20-40% entity recall [Sprint 83.3]

4. **Check Status**
   - `GET /api/v1/admin/upload-status/{doc_id}`
   - View processing progress
   - See extraction metrics

#### Test Coverage:
- **Existing Tests:** `frontend/e2e/admin/indexing.spec.ts`, `ingestion-jobs.spec.ts`
- **Sprint 83 Additions:** Fast upload response, background status tests

---

### Journey 6: Graph Communities & Analytics (Sprint 79)

**User Goal:** Analyze graph communities and entity relationships

#### Steps:
1. **Navigate to Graph Communities** (`/admin/communities`)
   - See community list with statistics

2. **View Community Details**
   - Select community from list
   - See member entities
   - View community summary (LLM-generated)
   - See entity connectivity scores

3. **Run Community Detection**
   - Click "Run Detection"
   - Select algorithm (GDS Louvain) [Sprint 92.22 fix]
   - Watch progress
   - See results (community count, modularity)

4. **Compare Sections** (SectionCommunitiesDialog)
   - Select document → sections
   - Compare entity overlap between sections

#### Test Coverage:
- **Test File:** `frontend/e2e/tests/admin/graph-communities.spec.ts`
- **Tests:** Graph community detection, comparison, GDS label fix

---

### Journey 7: Anti-Hallucination Context Guard (Sprint 92.11)

**User Goal:** Ensure LLM only answers from relevant contexts

#### Steps:
1. **Ask Question About Unknown Topic**
   - Enter query not covered in indexed documents

2. **System Behavior**
   - Retrieval runs (vector, graph, hybrid)
   - **Context Relevance Check** [Sprint 92.11]
   - If max relevance score < threshold (default 0.3):
     - LLM generation SKIPPED
     - Standardized "not found" response returned
   - If relevant contexts found:
     - Normal LLM generation proceeds

3. **Expected Response (Irrelevant)**
   ```
   I don't have relevant information in my knowledge base to answer
   this question accurately. The retrieved contexts don't contain
   information about [topic].
   ```

4. **Configure Threshold** (Admin)
   - Set via Redis config (UI in Sprint 97)
   - `MIN_CONTEXT_RELEVANCE_THRESHOLD = 0.3`

#### Test Coverage:
- **Sprint 92 Additions:** Anti-hallucination threshold tests needed
- **Test Scenarios:**
  - Query with relevant contexts → normal answer
  - Query with irrelevant contexts → "not found" response
  - Threshold configuration test

---

## E2E Test File Index

### Existing Tests (Sprint 72-92)

| File | Feature | Tests | Sprint |
|------|---------|-------|--------|
| `tests/admin/mcp-tools.spec.ts` | MCP Tool Management | 15 | 72 |
| `tests/admin/memory-management.spec.ts` | Memory Management | 10 | 72 |
| `tests/admin/graph-communities.spec.ts` | Graph Communities | 8 | 79 |
| `tests/admin/domain-training-new-features.spec.ts` | Domain Training | 18 | 72 |
| `research-mode.spec.ts` | Deep Research | 12 | 63+ |
| `search/search-features.spec.ts` | Search Features | 15 | 74 |
| `chat/chat-features.spec.ts` | Chat Features | 20 | 73 |
| `memory/consolidation.spec.ts` | Memory Consolidation | 5 | 72 |

### Tests Needed (Sprint 92)

| Feature | Priority | Suggested File | Tests Needed |
|---------|----------|----------------|--------------|
| Deep Research UI (4 levels) | P0 | `research-mode-enhanced.spec.ts` | 8 |
| Sparse/Dense Counts UI | P1 | `search-metrics.spec.ts` | 4 |
| Graph Hops Count UI | P1 | `search-metrics.spec.ts` | 2 |
| Timing Metrics Display | P1 | `search-metrics.spec.ts` | 4 |
| Context Relevance Guard | P0 | `anti-hallucination.spec.ts` | 6 |
| BM25 → Sparse Label | P2 | `ui-labels.spec.ts` | 2 |

---

## Data Attributes Reference (Sprint 72-92)

### MCP Tools Page
```typescript
data-testid="mcp-tools-page"
data-testid="mcp-servers-list"
data-testid="mcp-server-card-{name}"
data-testid="server-status-{name}"
data-testid="connect-button-{name}"
data-testid="disconnect-button-{name}"
data-testid="mcp-tool-execution-panel"
data-testid="tool-selector"
data-testid="execute-button"
data-testid="execution-result"
data-testid="execution-error"
data-testid="health-monitor"
data-testid="refresh-button"
```

### Memory Management Page
```typescript
data-testid="memory-management-page"
data-testid="tab-stats"
data-testid="tab-search"
data-testid="tab-consolidation"
data-testid="memory-stats-card"
data-testid="redis-stats"
data-testid="qdrant-stats"
data-testid="graphiti-stats"
data-testid="memory-search-panel"
data-testid="search-query-input"
data-testid="user-id-input"
data-testid="session-id-input"
data-testid="search-button"
data-testid="search-results"
data-testid="search-result-row"
data-testid="export-button"
data-testid="consolidation-control"
data-testid="trigger-consolidation-button"
data-testid="consolidation-history"
data-testid="refresh-stats-button"
data-testid="toggle-filters-button"
```

### Research Mode
```typescript
data-testid="research-mode-toggle"
data-testid="research-mode-switch"
data-testid="research-progress"
data-testid="phase-plan"
data-testid="phase-search"
data-testid="phase-evaluate"
data-testid="phase-synthesize"
data-testid="phase-status"
data-testid="research-synthesis"
data-testid="research-sources"
data-testid="research-source-item"
data-testid="quality-score"
data-testid="relevance-score"
data-testid="stop-research"
data-testid="research-stats"
data-testid="research-confidence"
```

### Search Results (Sprint 92 Additions)
```typescript
data-testid="sparse-results-count"
data-testid="dense-results-count"
data-testid="graph-hops-count"
data-testid="timing-metrics"
data-testid="phase-timing-{phase}"
data-testid="search-mode-selector"
data-testid="hybrid-mode-active"
```

---

## Performance Expectations

| Journey | Target Latency (P95) | Sprint 92 Actual |
|---------|----------------------|------------------|
| MCP Tool Execution | <500ms | ~125ms |
| Memory Search | <300ms | ~50ms |
| Graph Search | <2s | 1.2s (was 17-19s) |
| Research (3 iterations) | <30s | ~20s |
| Hybrid Search | <500ms | 350ms |
| First Query (cold start) | <1s | <500ms (was 40-90s) |

---

## Running E2E Tests

### Full Test Suite
```bash
cd frontend
npm run e2e
```

### Specific Feature Tests
```bash
# MCP Tools
npx playwright test tests/admin/mcp-tools.spec.ts

# Memory Management
npx playwright test tests/admin/memory-management.spec.ts

# Research Mode
npx playwright test research-mode.spec.ts

# All Admin Tests
npx playwright test tests/admin/
```

### Visual Regression
```bash
npx playwright test --update-snapshots
```

### Debug Mode
```bash
npx playwright test --debug tests/admin/mcp-tools.spec.ts
```

---

## References

- [MCP_TOOLS_ADMIN_GUIDE.md](../guides/MCP_TOOLS_ADMIN_GUIDE.md) - MCP Tools documentation
- [MEMORY_MANAGEMENT_GUIDE.md](../guides/MEMORY_MANAGEMENT_GUIDE.md) - Memory Management documentation
- [TOOL_FRAMEWORK_USER_JOURNEY.md](TOOL_FRAMEWORK_USER_JOURNEY.md) - Tool Framework journeys
- [SPRINT_PLAN.md](../sprints/SPRINT_PLAN.md) - Sprint planning and features
- [ADR-052](../adr/ADR-052-recursive-llm-adaptive-scoring.md) - Recursive LLM Scoring
- [ADR-053](../adr/ADR-053-docker-frontend-deployment.md) - Docker Frontend

---

**Document Version:** 3.0
**Last Updated:** 2026-01-15 (Sprint 92 Complete)
**Next Review:** Sprint 100
