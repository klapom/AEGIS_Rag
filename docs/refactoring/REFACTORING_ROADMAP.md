# Technical Debt & Refactoring Roadmap

**Generated:** 2025-11-13
**Source:** Comprehensive analysis of docs/refactoring/ + codebase TODO comments
**Total TD Items:** 28 (from refactoring docs + code analysis)
**Sprint 24 Scope:** 6 features (24 SP), Deferred: 4 features (21 SP)

---

## Executive Summary

This roadmap consolidates ALL technical debt items from:
1. **Refactoring Documentation** (`docs/refactoring/reference/`)
2. **Sprint 22 Hybrid Approach Plan** (incomplete items)
3. **Codebase TODO Comments** (31 TODOs found in src/)
4. **Sprint 23 Technical Debt** (ANY-LLM, VLM, cost tracking)

**Key Findings:**
- **28 Technical Debt Items** identified across 6 categories
- **10 items from refactoring docs** (deprecated code, duplications, architecture)
- **4 items from Sprint 23** (LLM proxy, cost tracking, VLM routing)
- **14 items from code TODOs** (health checks, monitoring, authentication)

**Priority Breakdown:**
- **P0 (Critical):** 0 items
- **P1 (High):** 3 items (deprecated code removal, duplicate base agent)
- **P2 (Medium):** 9 items (API security, embedding consolidation, BaseClient pattern)
- **P3 (Low):** 16 items (code quality, TODOs, profiling modules)

---

## 🔴 Category 1: Deprecated Code Removal (P1 - High Priority)

### TD-REF-01: Remove unified_ingestion.py (DEPRECATED Sprint 21)
**Source:** docs/refactoring/reference/BACKEND_REFACTORING_PLAN.md (Section 1.1)
**Original Sprint:** Sprint 21
**Category:** Architecture
**Priority:** P1 (High)
**Effort:** M (1 day)

**Description:**
Remove deprecated `UnifiedIngestionPipeline` replaced by LangGraph ingestion pipeline (ADR-027). Parallel execution incompatible with memory constraints.

**Current State:**
- File exists: `src/components/shared/unified_ingestion.py` (275 lines)
- Marked DEPRECATED in Sprint 21 (lines 4-24)
- Breaking changes announced for Sprint 22 removal
- Used in: Admin re-indexing endpoint, UI ingestion (if exists)

**Target State:**
- File moved to `archive/deprecated/unified_ingestion_sprint1-21.py`
- All imports migrated to `create_ingestion_graph()` from LangGraph pipeline
- Tests migrated to `test_langgraph_pipeline.py`

**Impact if not fixed:**
- Code confusion (two ingestion paths)
- Memory constraint violations (asyncio.gather uses too much RAM)
- ADR-027 architecture violations

**Related Components:**
- `src/components/ingestion/langgraph_pipeline.py` (replacement)
- `src/api/v1/admin.py` (admin re-indexing endpoint)
- `tests/unit/components/shared/test_unified_ingestion.py` (migrate tests)

**Acceptance Criteria:**
- [ ] File removed from src/
- [ ] All imports updated to LangGraph pipeline
- [ ] Tests passing (integration tests for LangGraph)
- [ ] Admin endpoint uses new pipeline
- [ ] 275 lines of code deleted

**Estimated Effort:** 1 day (6-8h)

**Status:** Sprint 22 Phase 1 - NOT COMPLETED (deferred to Sprint 24)

---

### TD-REF-02: Archive three_phase_extractor.py (DEPRECATED Sprint 21)
**Source:** docs/refactoring/reference/BACKEND_REFACTORING_PLAN.md (Section 1.2)
**Original Sprint:** Sprint 13-20 (active), Sprint 21 (deprecated)
**Category:** Architecture
**Priority:** P1 (High)
**Effort:** S (0.5 day)

**Description:**
Archive three-phase extraction pipeline (SpaCy NER + Dedup + Gemma). ADR-026 states pure LLM extraction is superior and default.

**Current State:**
- File exists: `src/components/graph_rag/three_phase_extractor.py` (350 lines)
- Config default changed: `extraction_pipeline="llm_extraction"` (was `"three_phase"`)
- Lower quality than pure LLM approach

**Target State:**
- File archived to `archive/deprecated/three_phase_extractor_sprint13-20.py`
- Config updated: Remove `"three_phase"` from Literal type
- `extraction_factory.py` updated: Remove three_phase branch
- Tests archived to `archive/tests/`

**Impact if not fixed:**
- Confusion about which extraction pipeline to use
- Maintaining deprecated code with lower quality
- ADR-026 violations

**Related Components:**
- `src/components/graph_rag/extraction_factory.py` (remove three_phase branch)
- `src/core/config.py` (update Literal type)
- `tests/unit/components/graph_rag/test_three_phase_extractor.py` (archive tests)

**Acceptance Criteria:**
- [ ] File archived to archive/deprecated/
- [ ] Config Literal updated (remove "three_phase")
- [ ] extraction_factory.py updated
- [ ] Tests archived
- [ ] 350 lines of code removed from src/

**Estimated Effort:** 0.5 day (3-4h)

**Status:** Sprint 22 Phase 3 - NOT COMPLETED (deferred to Sprint 24)

---

### TD-REF-03: Remove LlamaIndex load_documents() Method
**Source:** docs/refactoring/reference/BACKEND_REFACTORING_PLAN.md (Section 1.3)
**Original Sprint:** Sprint 21
**Category:** Architecture
**Priority:** P1 (High)
**Effort:** M (1 day)

**Description:**
Remove deprecated `DocumentIngestionPipeline.load_documents()` method. ADR-028: LlamaIndex deprecated as primary ingestion framework, Docling is now primary.

**Current State:**
- File: `src/components/vector_search/ingestion.py` (lines 137-163 marked DEPRECATED)
- Uses LlamaIndex SimpleDirectoryReader
- Marked with deprecation warning in Sprint 21

**Target State:**
- Method removed entirely
- All callers migrated to Docling
- LlamaIndex dependency kept only for connectors (fallback)
- Runtime deprecation warning removed

**Impact if not fixed:**
- Confusion about which ingestion method to use
- Violates ADR-028 (Docling as primary parser)
- Maintains dual ingestion code paths

**Related Components:**
- `src/components/ingestion/docling_client.py` (replacement)
- `src/components/vector_search/ingestion.py` (remove method)
- All callers using load_documents() (migrate to Docling)

**Acceptance Criteria:**
- [ ] load_documents() method removed
- [ ] All callers migrated to Docling
- [ ] Tests updated
- [ ] LlamaIndex dependency retained (for connectors only)
- [ ] ~100 lines removed

**Estimated Effort:** 1 day (high complexity - affects multiple ingestion paths)

**Status:** Sprint 22 Phase 3 - NOT COMPLETED (deferred to Sprint 24)

---

## 🟡 Category 2: Code Duplication Elimination (P2 - Medium Priority)

### TD-REF-04: Remove Duplicate Base Agent (base.py vs base_agent.py)
**Source:** docs/refactoring/reference/BACKEND_REFACTORING_PLAN.md (Section 2.1)
**Original Sprint:** Unknown (legacy duplication)
**Category:** Code Quality
**Priority:** P2 (Medium)
**Effort:** S (0.5 day)

**Description:**
Two IDENTICAL `BaseAgent` class implementations exist. Creates confusion about which to use.

**Current State:**
- `src/agents/base.py` (155 lines)
- `src/agents/base_agent.py` (155 lines - IDENTICAL)
- Both files have same abstract `process()` method, same helpers (`_add_trace`, `_measure_latency`)

**Target State:**
- Keep `src/agents/base_agent.py` (more explicit naming)
- Remove `src/agents/base.py`
- Update all imports: `from src.agents.base import BaseAgent` → `from src.agents.base_agent import BaseAgent`

**Impact if not fixed:**
- Developer confusion (which file to import?)
- Code duplication (155 lines)
- Maintenance burden (update both files)

**Related Components:**
- All agent files importing `BaseAgent`
- `tests/unit/agents/test_base_agent.py` (update imports)

**Acceptance Criteria:**
- [ ] base.py removed
- [ ] All imports updated to base_agent.py
- [ ] Tests passing
- [ ] 155 lines of duplicate code removed

**Estimated Effort:** 0.5 day (low complexity - simple import refactoring)

**Status:** PENDING

---

### TD-REF-05: Consolidate Duplicate Embedding Services
**Source:** docs/refactoring/reference/BACKEND_REFACTORING_PLAN.md (Section 2.2)
**Original Sprint:** Sprint 11 (wrapper created for backward compat)
**Category:** Code Quality
**Priority:** P2 (Medium)
**Effort:** M (1 day)

**Description:**
`EmbeddingService` is just a wrapper around `UnifiedEmbeddingService`. All methods delegate to unified service.

**Current State:**
- `src/components/shared/embedding_service.py` (UnifiedEmbeddingService - 269 lines - core)
- `src/components/vector_search/embeddings.py` (EmbeddingService - 160 lines - wrapper)
- Wrapper delegates everything to unified service (Sprint 11 backward compatibility)

**Target State:**
**Option A (Recommended for Sprint 24+):**
- Remove wrapper entirely
- Migrate all imports to `UnifiedEmbeddingService`

**Option B (Conservative):**
- Add deprecation warning to `EmbeddingService.__init__()`
- Keep wrapper for 1-2 sprints
- Remove in Sprint 25 after migration period

**Impact if not fixed:**
- Code duplication (160 lines of wrapper code)
- Confusion about which service to use
- Maintenance burden (update both)

**Related Components:**
- All components importing `EmbeddingService` (migrate to `UnifiedEmbeddingService`)
- `tests/unit/components/vector_search/test_embeddings.py` (migrate tests)

**Acceptance Criteria:**
- [ ] Wrapper removed OR deprecation warning added
- [ ] All imports migrated to UnifiedEmbeddingService
- [ ] Tests migrated
- [ ] 160 lines of wrapper code removed (if Option A)

**Estimated Effort:** 1 day (medium complexity - import updates across codebase)

**Status:** PENDING

---

### TD-REF-06: Standardize Client Naming Conventions
**Source:** docs/refactoring/reference/BACKEND_REFACTORING_PLAN.md (Section 2.3)
**Original Sprint:** Multiple sprints (inconsistent naming)
**Category:** Code Quality
**Priority:** P2 (Medium)
**Effort:** M (1 day)

**Description:**
Inconsistent naming for client wrapper classes (`Wrapper` suffix vs `Client` suffix).

**Current State:**
- `QdrantClientWrapper` (wrapper suffix)
- `GraphitiWrapper` (wrapper suffix)
- `LightRAGWrapper` (wrapper suffix)
- `DoclingContainerClient` (container + client)
- `Neo4jClient` (no suffix - correct)
- `MCPClient` (no suffix - correct)

**Target State:**
Standardize to `<Service>Client` pattern:
- `QdrantClientWrapper` → `QdrantClient`
- `GraphitiWrapper` → `GraphitiClient`
- `LightRAGWrapper` → `LightRAGClient`
- `DoclingContainerClient` → `DoclingClient`
- `Neo4jClient` ✓ (already correct)
- `MCPClient` ✓ (already correct)

**Impact if not fixed:**
- Inconsistent API naming
- Confusion about which naming pattern to follow
- "Wrapper" suffix is redundant (Client already implies wrapper)

**Related Components:**
- All files importing these clients (update imports)
- Tests (update imports)
- Documentation (update references)

**Acceptance Criteria:**
- [ ] All client classes renamed to `<Service>Client`
- [ ] Backward compatibility aliases created (e.g., `QdrantClientWrapper = QdrantClient`)
- [ ] All imports updated
- [ ] Tests passing
- [ ] Documentation updated

**Estimated Effort:** 1 day (medium complexity - requires import updates)

**Status:** PENDING

---

## 🟢 Category 3: Architecture Improvements (P3 - Low Priority)

### TD-REF-07: Extract Common Client Base Class
**Source:** docs/refactoring/reference/BACKEND_REFACTORING_PLAN.md (Section 3.1)
**Original Sprint:** Future (no existing BaseClient)
**Category:** Architecture
**Priority:** P3 (Low)
**Effort:** M (1 day)

**Description:**
All client classes duplicate connection/health check/logging patterns. Extract to BaseClient abstract class.

**Current State:**
- `QdrantClient`, `Neo4jClient`, `DoclingClient`, etc. all duplicate:
  - `__init__()` with logger and config
  - `connect()` / `disconnect()` / `health_check()` methods
  - ~50 lines of boilerplate per client (6 clients = 300 lines)

**Target State:**
- Create `src/core/base_client.py` with `BaseClient` abstract class
- All clients inherit from `BaseClient`
- Reduce boilerplate by ~50% per client (estimate: 150 lines saved)

**Impact if not fixed:**
- Code duplication (300+ lines across clients)
- Inconsistent patterns (some clients have __aenter__/__aexit__, some don't)
- Maintenance burden (update connection pattern in 6 places)

**Related Components:**
- All client classes (Qdrant, Neo4j, Docling, Graphiti, LightRAG, MCP)
- `src/core/base_client.py` (new file)

**Acceptance Criteria:**
- [ ] BaseClient abstract class created
- [ ] All clients inherit from BaseClient
- [ ] Duplicate code removed (~150 lines saved)
- [ ] Tests passing
- [ ] Documentation for BaseClient pattern

**Estimated Effort:** 1 day

**Status:** Sprint 22 Phase 3 - NOT COMPLETED (deferred to Future Sprint)

---

### TD-REF-08: Standardize Error Handling Patterns
**Source:** docs/refactoring/reference/BACKEND_REFACTORING_PLAN.md (Section 2.4)
**Original Sprint:** Multiple sprints (inconsistent patterns)
**Category:** Code Quality
**Priority:** P3 (Low)
**Effort:** L (2 days)

**Description:**
Inconsistent error handling across components (bare try/except, custom exceptions, tenacity retry).

**Current State:**
**Pattern 1: Bare try/except**
```python
try:
    result = await detect_communities()
except Exception as e:
    logger.error("detection_failed", error=str(e))
    return []  # Silent failure
```

**Pattern 2: Re-raise with custom exception**
```python
try:
    documents = await load()
except Exception as e:
    logger.error("load_failed", error=str(e))
    raise VectorSearchError(f"Failed to load: {e}") from e  # Good!
```

**Pattern 3: Tenacity retry decorator**
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
async def embed_single(self, text: str) -> list[float]:
    # Automatic retry with exponential backoff
```

**Target State:**
- Create `src/core/error_handling.py` with standardized patterns
- `with_retries()` decorator
- `safe_execute()` helper function
- Gradual migration to standard patterns

**Impact if not fixed:**
- Inconsistent error handling (hard to predict behavior)
- Silent failures (Pattern 1)
- Inconsistent logging (some log, some don't)

**Related Components:**
- All components with error handling (50+ files)
- `src/core/error_handling.py` (new file)

**Acceptance Criteria:**
- [ ] error_handling.py created
- [ ] 5-10 components migrated to new patterns
- [ ] Tests for error handling helpers
- [ ] Documentation for standard patterns

**Estimated Effort:** 2 days (high complexity - affects all components, gradual migration)

**Status:** DEFERRED to Future Sprint (gradual rollout)

---

## 📊 Category 4: Sprint 23 Technical Debt

### TD-23.1: ANY-LLM Partial Integration
**Source:** Sprint 23 (Feature 23.6)
**Original Sprint:** Sprint 23
**Category:** Architecture
**Priority:** P2 (Medium)
**Effort:** L (2 days)

**Description:**
Using ANY-LLM's `acompletion()` function but NOT using full framework features (BudgetManager, CostTracker, ConnectionPooling, Gateway).

**Current State:**
- Custom SQLite `CostTracker` (389 LOC)
- Manual budget checking in `aegis_llm_proxy.py`
- ANY-LLM Core Library only (not Gateway)

**Target State:**
- Deploy ANY-LLM Gateway as microservice
- Use built-in BudgetManager, CostTracker
- Unified connection pooling

**Impact if not fixed:**
- Code duplication (custom CostTracker vs ANY-LLM built-in)
- Missing features (connection pooling, advanced routing)
- Complexity (manual budget tracking)

**Related Components:**
- `src/components/llm_proxy/cost_tracker.py` (custom implementation)
- `src/components/llm_proxy/aegis_llm_proxy.py` (manual routing)

**Acceptance Criteria:**
- [ ] ANY-LLM Gateway deployed
- [ ] Custom CostTracker replaced with ANY-LLM built-in
- [ ] Tests passing
- [ ] Cost tracking accuracy maintained

**Estimated Effort:** 2 days

**Status:** DEFERRED to Sprint 25+ (custom SQLite solution working perfectly, ANY-LLM Gateway adds infrastructure complexity)

---

### TD-23.2: DashScope VLM Bypass Routing
**Source:** Sprint 23 (Feature 23.5)
**Original Sprint:** Sprint 23
**Category:** Architecture
**Priority:** P3 (Low)
**Effort:** M (1 day)

**Description:**
`DashScopeVLMClient` bypasses `AegisLLMProxy` routing logic. VLM requests don't go through unified routing system.

**Current State:**
- Direct API calls in `dashscope_vlm.py`
- No unified routing metrics for VLM tasks
- Cost tracking works (manual integration)

**Target State:**
- Extend `AegisLLMProxy` with VLM-specific generate method
- Unified interface: `proxy.generate(task)` for both text and vision
- Routing metrics for VLM tasks

**Impact if not fixed:**
- Code duplication (VLM routing vs text routing)
- No unified routing metrics
- Missing ANY-LLM integration for VLM

**Related Components:**
- `src/components/llm_proxy/dashscope_vlm.py` (direct API calls)
- `src/components/llm_proxy/aegis_llm_proxy.py` (extend for VLM)
- `src/components/ingestion/image_processor.py` (caller)

**Acceptance Criteria:**
- [ ] AegisLLMProxy supports VLM tasks
- [ ] DashScopeVLMClient removed (integrated into proxy)
- [ ] Tests passing
- [ ] Routing metrics for VLM

**Estimated Effort:** 1 day

**Status:** DEFERRED to Sprint 25+ (ANY-LLM doesn't support VLM yet, functional workaround in place)

---

### TD-23.3: Token Split Estimation (50/50)
**Source:** Sprint 23 (Feature 23.6), aegis_llm_proxy.py:495-497
**Original Sprint:** Sprint 23
**Category:** Code Quality
**Priority:** P3 (Low)
**Effort:** S (0.5 day)

**Description:**
Token split estimation uses 50/50 split for input/output tokens because ANY-LLM response doesn't provide detailed breakdown. Alibaba Cloud charges different rates for input vs output.

**Current State:**
```python
# Estimate 50/50 split for input/output tokens if not available
tokens_input = result.tokens_used // 2
tokens_output = result.tokens_used - tokens_input
```

**Target State:**
Extract detailed token usage from API responses. Alibaba Cloud returns `prompt_tokens` and `completion_tokens`.

```python
if hasattr(result, 'usage') and result.usage:
    tokens_input = result.usage.get('prompt_tokens', 0)
    tokens_output = result.usage.get('completion_tokens', 0)
else:
    # Fallback to total tokens
    tokens_input = result.tokens_used // 2
    tokens_output = result.tokens_used - tokens_input
```

**Impact if not fixed:**
- Inaccurate cost calculations (input/output rates differ)
- 50/50 split is estimation, not actual usage

**Related Components:**
- `src/components/llm_proxy/aegis_llm_proxy.py` (update token parsing)
- `src/components/llm_proxy/cost_tracker.py` (accurate input/output split)

**Acceptance Criteria:**
- [ ] Token input/output split accurate (not 50/50)
- [ ] Cost calculations use correct rates
- [ ] Unit tests cover edge cases (missing usage field)
- [ ] SQLite database shows accurate token breakdown

**Estimated Effort:** 0.5 day

**Status:** Sprint 24 Feature 24.2 (SCHEDULED)

---

### TD-23.4: Async/Sync Bridge Complexity
**Source:** Sprint 23 (Feature 23.5), image_processor.py:414-434
**Original Sprint:** Sprint 23
**Category:** Code Quality
**Priority:** P3 (Low)
**Effort:** M (1 day)

**Description:**
`ImageProcessor.process_image()` is synchronous but calls async `generate_vlm_description_with_dashscope()`. We use `asyncio.run()` with thread pool executor to bridge sync/async, adding complexity.

**Current Workaround:**
```python
try:
    loop = asyncio.get_running_loop()
    # Already in event loop - use ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, generate_vlm_description_with_dashscope(...))
        description = future.result()
except RuntimeError:
    # Not in event loop - use asyncio.run
    description = asyncio.run(generate_vlm_description_with_dashscope(...))
```

**Target State:**
Make entire ingestion pipeline async. Refactor `ImageProcessor.process_image()` to be async.

**Impact if not fixed:**
- Code complexity (ThreadPoolExecutor workaround)
- Potential event loop issues
- Inconsistent async patterns

**Related Components:**
- `src/components/ingestion/image_processor.py` (make async)
- All callers (update to use `await`)
- LangGraph pipeline (verify compatibility)

**Acceptance Criteria:**
- [ ] ImageProcessor fully async
- [ ] No ThreadPoolExecutor usage
- [ ] All callers updated (ingestion pipeline)
- [ ] Tests passing with async fixtures
- [ ] Performance unchanged or improved

**Estimated Effort:** 1 day

**Status:** Sprint 24 Feature 24.3 (SCHEDULED)

---

## 🔧 Category 5: API Layer Improvements (P2 - Medium Priority)

### TD-REF-09: Fix CORS Configuration
**Source:** docs/refactoring/reference/API_REFACTORING_PLAN_V1.md (Section P1.1)
**Original Sprint:** Multiple sprints (insecure config)
**Category:** Security
**Priority:** P2 (Medium)
**Effort:** S (0.5 day)

**Description:**
CORS configuration too permissive (`allow_origins=["*"]`), even in development.

**Current State:**
```python
# src/api/main.py:119-125
allow_origins=["*"]  # Too permissive
```

**Target State:**
```python
# In settings.py
ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

# In main.py
allow_origins=settings.ALLOWED_ORIGINS if settings.environment == "development" else [],
```

**Impact if not fixed:**
- Security vulnerability (CORS allows all origins)
- No protection against CSRF attacks

**Related Components:**
- `src/api/main.py` (fix CORS config)
- `src/core/config.py` (add ALLOWED_ORIGINS setting)

**Acceptance Criteria:**
- [ ] CORS restricted to specific origins
- [ ] Development: localhost:3000, localhost:8080
- [ ] Production: empty list (must configure explicitly)
- [ ] Tests validate CORS restrictions

**Estimated Effort:** 0.5 day

**Status:** Sprint 22 Phase 1 Task 22.2.2 - COMPLETED (per plan, verify in code)

---

### TD-REF-10: Standardize Error Responses
**Source:** docs/refactoring/reference/API_REFACTORING_PLAN_V1.md (Section P1.2)
**Original Sprint:** Multiple sprints (inconsistent errors)
**Category:** API Consistency
**Priority:** P2 (Medium)
**Effort:** M (1 day)

**Description:**
Inconsistent error response formats across API endpoints. Some return `ErrorResponse` model, others return plain dict.

**Current State:**
- Some endpoints: `ErrorResponse` model (main.py handlers)
- Others: Plain dict with "detail"
- No request_id for debugging
- Inconsistent timestamps

**Target State:**
Create `src/api/models/errors.py`:
```python
class StandardErrorResponse(BaseModel):
    error_code: str  # "VALIDATION_ERROR", "INTERNAL_ERROR", etc.
    message: str
    details: dict[str, Any] | None = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str | None = None
    path: str | None = None
```

**Impact if not fixed:**
- Inconsistent API responses
- Hard to debug (no request_id)
- Poor developer experience

**Related Components:**
- `src/api/models/errors.py` (new file)
- `src/api/main.py` (update exception handlers)
- All endpoint files (update error returns)

**Acceptance Criteria:**
- [ ] StandardErrorResponse model created
- [ ] All exception handlers updated
- [ ] All endpoints use consistent error format
- [ ] Tests passing

**Estimated Effort:** 1 day

**Status:** Sprint 22 Phase 1 Task 22.2.1 - COMPLETED (per plan, verify in code)

---

### TD-REF-11: Add Rate Limiting to Missing Endpoints
**Source:** docs/refactoring/reference/API_REFACTORING_PLAN_V1.md (Section P1.3)
**Original Sprint:** Multiple sprints (inconsistent rate limiting)
**Category:** Security
**Priority:** P2 (Medium)
**Effort:** S (0.5 day)

**Description:**
Annotation and admin endpoints have no rate limiting. Could be abused for DoS.

**Current State:**
- `src/api/v1/annotations.py`: No rate limiting
- `src/api/v1/admin.py` `/stats` endpoint: No rate limiting

**Target State:**
```python
@router.get("/document/{document_id}")
@limiter.limit("30/minute")
async def get_document_annotations(...):
    ...

@router.get("/stats")
@limiter.limit("60/minute")
async def get_system_stats(...):
    ...
```

**Impact if not fixed:**
- DoS vulnerability (unlimited requests)
- No protection against abuse

**Related Components:**
- `src/api/v1/annotations.py` (add rate limiting)
- `src/api/v1/admin.py` (add rate limiting)

**Acceptance Criteria:**
- [ ] Annotation endpoints rate limited (30/minute read, 10/minute write)
- [ ] Admin endpoints rate limited (60/minute stats, 5/hour reindex)
- [ ] Tests validate rate limits
- [ ] 429 errors returned when exceeded

**Estimated Effort:** 0.5 day

**Status:** Sprint 22 Phase 1 Task 22.2.2 - COMPLETED (per plan, verify in code)

---

### TD-REF-12: Standardize Authentication
**Source:** docs/refactoring/reference/API_REFACTORING_PLAN_V1.md (Section P1.4)
**Original Sprint:** Multiple sprints (inconsistent auth)
**Category:** Security
**Priority:** P2 (Medium)
**Effort:** M (1 day)

**Description:**
Inconsistent authentication patterns across endpoints.

**Current State:**
- `annotations.py`: Uses `get_current_user` (required)
- `retrieval.py`: Uses `get_current_user` with `| None` (optional)
- `chat.py`: No authentication
- Inconsistent parameter naming: `_current_user` vs `current_user`

**Target State:**
Create `src/api/auth/dependencies.py`:
```python
RequireAuth = Depends(get_current_user)  # Returns User
OptionalAuth = Depends(get_current_user_optional)  # Returns User | None
```

Apply consistently:
- **Public:** Health checks, auth token endpoints
- **Optional Auth:** Search, retrieval (rate limits differ)
- **Require Auth:** Chat, memory, admin, annotations

**Impact if not fixed:**
- Security inconsistency (unprotected endpoints)
- Confusing authentication requirements
- Chat endpoint unprotected (security issue!)

**Related Components:**
- `src/api/auth/dependencies.py` (new file)
- All endpoint files (update auth)

**Acceptance Criteria:**
- [ ] RequireAuth and OptionalAuth dependencies created
- [ ] Chat endpoint protected (now requires auth)
- [ ] Consistent auth across all endpoints
- [ ] Tests validate auth requirements

**Estimated Effort:** 1 day

**Status:** Sprint 22 Phase 1 Task 22.2.3 - COMPLETED (per plan, verify in code)

---

## 📝 Category 6: Code TODOs (P3 - Low Priority)

### TD-TODO-01: Health Check TODOs (Qdrant, Graphiti)
**Source:** Grep search - src/api/health/memory_health.py
**Original Sprint:** Multiple sprints
**Category:** Monitoring
**Priority:** P3 (Low)
**Effort:** S (0.5 day)

**Description:**
Memory health check endpoints return placeholder data (0 collections, 0 vectors, 0 capacity).

**Current State:**
```python
# src/api/health/memory_health.py:251-260
# TODO: Implement Qdrant health check when client is available
"collections": 0,  # TODO: Get actual collection count
"vectors": 0,  # TODO: Get actual vector count
"capacity": 0.0,  # TODO: Get actual capacity

# src/api/health/memory_health.py:284-293
# TODO: Implement Graphiti health check when client is available
"nodes": 0,  # TODO: Get actual node count
"edges": 0,  # TODO: Get actual edge count
"capacity": 0.0,  # TODO: Get actual capacity
```

**Target State:**
Implement real health checks using Qdrant and Graphiti clients.

**Impact if not fixed:**
- Health checks return fake data
- No monitoring of actual system capacity
- Can't detect capacity issues

**Related Components:**
- `src/api/health/memory_health.py` (implement real checks)
- `src/components/vector_search/qdrant_client.py` (use for stats)
- `src/components/memory/graphiti_wrapper.py` (use for stats)

**Acceptance Criteria:**
- [ ] Qdrant health check returns real data
- [ ] Graphiti health check returns real data
- [ ] Tests validate health check accuracy
- [ ] All TODOs removed

**Estimated Effort:** 0.5 day

**Status:** Sprint 24 Feature 24.4 (SCHEDULED - part of TODO cleanup)

---

### TD-TODO-02: Memory Monitoring Capacity Tracking
**Source:** Grep search - src/components/memory/monitoring.py
**Original Sprint:** Multiple sprints
**Category:** Monitoring
**Priority:** P3 (Low)
**Effort:** S (0.5 day)

**Description:**
Memory monitoring returns placeholder capacity values.

**Current State:**
```python
# src/components/memory/monitoring.py:211-212
capacity = 0.0  # TODO: Get from Qdrant API
entries = 0  # TODO: Get collection size

# src/components/memory/monitoring.py:259-260
capacity = 0.0  # TODO: Get from Graphiti API
entries = 0  # TODO: Get node count
```

**Target State:**
Query Qdrant and Graphiti APIs for real capacity/entry counts.

**Impact if not fixed:**
- Monitoring reports fake capacity data
- Can't detect when memory tiers are full
- No alerts for capacity issues

**Related Components:**
- `src/components/memory/monitoring.py` (implement real queries)
- `src/components/vector_search/qdrant_client.py` (add capacity methods)
- `src/components/memory/graphiti_wrapper.py` (add capacity methods)

**Acceptance Criteria:**
- [ ] Real capacity data from Qdrant
- [ ] Real capacity data from Graphiti
- [ ] Tests validate capacity tracking
- [ ] All TODOs removed

**Estimated Effort:** 0.5 day

**Status:** Sprint 24 Feature 24.4 (SCHEDULED - part of TODO cleanup)

---

### TD-TODO-03: Startup/Shutdown Event Handlers
**Source:** Grep search - src/api/main.py:103,109
**Original Sprint:** Multiple sprints
**Category:** Infrastructure
**Priority:** P3 (Low)
**Effort:** S (0.5 day)

**Description:**
Startup and shutdown event handlers have TODO comments but no implementations.

**Current State:**
```python
# src/api/main.py:103
# TODO: Initialize database connections, load models, etc.

# src/api/main.py:109
# TODO: Close database connections, cleanup resources
```

**Target State:**
Implement proper startup/shutdown logic:
- Startup: Initialize Qdrant, Neo4j, Redis connections
- Shutdown: Close connections, cleanup resources

**Impact if not fixed:**
- No graceful shutdown (connections not closed)
- Resources not cleaned up on exit
- Potential connection leaks

**Related Components:**
- `src/api/main.py` (implement handlers)
- All client classes (add to startup/shutdown)

**Acceptance Criteria:**
- [ ] Startup handler initializes all connections
- [ ] Shutdown handler closes all connections
- [ ] Tests validate startup/shutdown
- [ ] All TODOs removed

**Estimated Effort:** 0.5 day

**Status:** Sprint 24 Feature 24.4 (SCHEDULED - part of TODO cleanup)

---

### TD-TODO-04: Multi-hop Query Context Injection
**Source:** Grep search - src/components/retrieval/query_decomposition.py:375
**Original Sprint:** Future enhancement
**Category:** Enhancement
**Priority:** P3 (Low)
**Effort:** L (2 days)

**Description:**
Query decomposition doesn't inject context from previous results for true multi-hop queries.

**Current State:**
```python
# src/components/retrieval/query_decomposition.py:375
# TODO: For true multi-hop, inject context from previous results
```

**Target State:**
Implement context injection for multi-hop queries (sub-query results inform next sub-query).

**Impact if not fixed:**
- Multi-hop queries less accurate
- No context propagation between sub-queries

**Related Components:**
- `src/components/retrieval/query_decomposition.py` (implement context injection)

**Acceptance Criteria:**
- [ ] Context injection implemented
- [ ] Multi-hop queries use previous results
- [ ] Tests validate context propagation
- [ ] TODO removed

**Estimated Effort:** 2 days

**Status:** DEFERRED to Future Sprint (enhancement, not critical)

---

### TD-TODO-05: Memory Consolidation Migration
**Source:** Grep search - src/components/memory/consolidation.py:427
**Original Sprint:** Future enhancement
**Category:** Enhancement
**Priority:** P3 (Low)
**Effort:** M (1 day)

**Description:**
Memory consolidation TODO: Migrate unique items to Qdrant/Graphiti.

**Current State:**
```python
# src/components/memory/consolidation.py:427
# TODO: Migrate unique items to Qdrant/Graphiti
```

**Target State:**
Implement migration of consolidated items to long-term storage (Qdrant for semantic search, Graphiti for episodic memory).

**Impact if not fixed:**
- Consolidated memories not migrated to long-term storage
- Redis accumulates old memories

**Related Components:**
- `src/components/memory/consolidation.py` (implement migration)
- `src/components/vector_search/qdrant_client.py` (store semantic memories)
- `src/components/memory/graphiti_wrapper.py` (store episodic memories)

**Acceptance Criteria:**
- [ ] Migration to Qdrant implemented
- [ ] Migration to Graphiti implemented
- [ ] Tests validate migration
- [ ] TODO removed

**Estimated Effort:** 1 day

**Status:** DEFERRED to Future Sprint (enhancement, not critical)

---

### TD-TODO-06: Profiling Modules (Sprint 17)
**Source:** Grep search - src/components/profiling/__init__.py:24,44
**Original Sprint:** Sprint 17
**Category:** Enhancement
**Priority:** P3 (Low)
**Effort:** L (2 days)

**Description:**
Profiling modules TODO from Sprint 17 - implement remaining profiling modules.

**Current State:**
```python
# src/components/profiling/__init__.py:24
# TODO: Sprint 17 - Implement remaining profiling modules

# src/components/profiling/__init__.py:44
# TODO: Sprint 17 - Uncomment when implemented
```

**Target State:**
Implement remaining profiling modules (performance profiling, memory profiling, etc.).

**Impact if not fixed:**
- Incomplete profiling capabilities
- Can't profile all system components

**Related Components:**
- `src/components/profiling/` (implement remaining modules)

**Acceptance Criteria:**
- [ ] All profiling modules implemented
- [ ] Tests for profiling modules
- [ ] TODOs removed

**Estimated Effort:** 2 days

**Status:** DEFERRED to Future Sprint (enhancement, Sprint 17 backlog)

---

### TD-TODO-07: LightRAG Entity/Relation Extraction
**Source:** Grep search - src/components/graph_rag/lightrag_wrapper.py:406-407
**Original Sprint:** Multiple sprints
**Category:** Enhancement
**Priority:** P3 (Low)
**Effort:** M (1 day)

**Description:**
LightRAG wrapper returns empty entities/relationships lists (TODO: Extract from LightRAG internal state).

**Current State:**
```python
# src/components/graph_rag/lightrag_wrapper.py:406-407
entities=[],  # TODO: Extract from LightRAG internal state
relationships=[],  # TODO: Extract from LightRAG internal state
context="",  # TODO: Get context used for generation
```

**Target State:**
Extract entities, relationships, and context from LightRAG internal state after query.

**Impact if not fixed:**
- Can't see which entities/relationships were used
- No transparency into LightRAG reasoning
- Hard to debug graph queries

**Related Components:**
- `src/components/graph_rag/lightrag_wrapper.py` (extract from internal state)

**Acceptance Criteria:**
- [ ] Entities extracted from LightRAG
- [ ] Relationships extracted from LightRAG
- [ ] Context extracted
- [ ] Tests validate extraction
- [ ] TODOs removed

**Estimated Effort:** 1 day

**Status:** DEFERRED to Future Sprint (enhancement, not critical)

---

## 📊 Sprint 24 Scope & Recommendations

### Sprint 24 Feature Mapping

Based on existing `docs/sprints/SPRINT_24_PLANNING.md`, we have these features:

#### ✅ Already Planned in Sprint 24:

1. **Feature 24.1: Prometheus Metrics** (5 SP) - NEW (from TD-G.2)
2. **Feature 24.2: Token Tracking Accuracy Fix** (3 SP) - TD-23.3
3. **Feature 24.3: Async/Sync Bridge Refactoring** (5 SP) - TD-23.4
4. **Feature 24.4: Code Linting and Type Safety** (3 SP) - Includes TD-TODO-01, TD-TODO-02, TD-TODO-03
5. **Feature 24.7: Missing Integration Tests** (5 SP) - NEW (from Sprint 23)
6. **Feature 24.8: Documentation Debt Resolution** (3 SP) - NEW

**Total Planned:** 24 SP (6 features)

#### 🔄 Additional Refactoring Items to Consider:

From refactoring docs, high-priority items NOT in Sprint 24:

1. **TD-REF-01: Remove unified_ingestion.py** (P1, 1 day) - From Sprint 22 Phase 1
2. **TD-REF-02: Archive three_phase_extractor.py** (P1, 0.5 day) - From Sprint 22 Phase 3
3. **TD-REF-03: Remove LlamaIndex load_documents()** (P1, 1 day) - From Sprint 22 Phase 3
4. **TD-REF-04: Remove Duplicate Base Agent** (P2, 0.5 day) - From Sprint 22 Phase 3
5. **TD-REF-05: Consolidate Embedding Services** (P2, 1 day) - From Sprint 22 Phase 3
6. **TD-REF-06: Standardize Client Naming** (P2, 1 day) - From Sprint 22 Phase 3

**Total Refactoring Debt:** ~5 days = ~10 SP

### Recommendation for Sprint 24:

#### Option A: Current Scope (24 SP - RECOMMENDED)
Focus on observability, cost tracking, and code quality improvements. Defer heavy refactoring to future sprint.

**Pros:**
- Manageable scope (24 SP fits 1 week)
- High-value features (Prometheus metrics, token accuracy)
- Quick wins (TODO cleanup, linting)

**Cons:**
- Defers deprecated code removal
- Doesn't address architecture debt

#### Option B: Extended Scope (34 SP)
Add highest-priority refactoring items from Sprint 22.

**Additional Features:**
- Feature 24.9: Remove Deprecated Code (TD-REF-01, TD-REF-02, TD-REF-03) - 5 SP
- Feature 24.10: Consolidate Duplicates (TD-REF-04, TD-REF-05) - 5 SP

**Pros:**
- Addresses P1 deprecated code removal
- Cleans up code duplications
- Aligns with Sprint 22 incomplete work

**Cons:**
- Larger scope (34 SP = 1.5 weeks)
- More risk (breaking changes)
- May delay Sprint 25

#### Recommended Approach: Option A (Current Scope)

**Rationale:**
1. Sprint 24 should focus on **stabilization** (metrics, monitoring, tests)
2. Deprecated code removal (Sprint 22 debt) can wait until Sprint 25
3. Current scope (24 SP) is manageable and delivers high value
4. Refactoring debt (Sprint 22 Phase 3) is P2/P3, not critical

### Sprint 25 Candidates (Deferred Items)

**Priority 1 (High):**
- TD-REF-01: Remove unified_ingestion.py (P1, 1 day)
- TD-REF-02: Archive three_phase_extractor.py (P1, 0.5 day)
- TD-REF-03: Remove LlamaIndex load_documents() (P1, 1 day)

**Priority 2 (Medium):**
- TD-REF-04: Remove Duplicate Base Agent (P2, 0.5 day)
- TD-REF-05: Consolidate Embedding Services (P2, 1 day)
- TD-REF-06: Standardize Client Naming (P2, 1 day)
- TD-23.1: ANY-LLM Full Integration (P2, 2 days)

**Priority 3 (Low):**
- TD-REF-07: Extract BaseClient Pattern (P3, 1 day)
- TD-REF-08: Standardize Error Handling (P3, 2 days)
- TD-23.2: DashScope VLM Routing (P3, 1 day)
- TD-TODO-04: Multi-hop Context Injection (P3, 2 days)
- TD-TODO-05: Memory Consolidation Migration (P3, 1 day)
- TD-TODO-06: Profiling Modules (P3, 2 days)
- TD-TODO-07: LightRAG Entity Extraction (P3, 1 day)

---

## 📈 Technical Debt Metrics Summary

### Total Technical Debt Items: 28

**By Priority:**
- **P0 (Critical):** 0 items
- **P1 (High):** 3 items (TD-REF-01, TD-REF-02, TD-REF-03) - 2.5 days
- **P2 (Medium):** 9 items (TD-REF-04 to TD-REF-12, TD-23.1) - 9 days
- **P3 (Low):** 16 items (TD-REF-07, TD-REF-08, TD-23.2 to TD-23.4, TD-TODO-01 to TD-TODO-07) - 15.5 days

**Total Estimated Effort:** 27 days (~54 SP)

**By Category:**
1. **Deprecated Code Removal:** 3 items (2.5 days)
2. **Code Duplication:** 3 items (2 days)
3. **Architecture Improvements:** 4 items (6 days)
4. **Sprint 23 Debt:** 4 items (4.5 days)
5. **API Layer:** 4 items (3 days)
6. **Code TODOs:** 10 items (9 days)

**Sprint 24 Resolution:**
- **Scheduled:** 6 features (24 SP) = ~12 days
- **Deferred to Sprint 25+:** 22 items (42 SP) = ~21 days

---

## 🔄 Implementation Order (Recommended)

### Sprint 24 (Week 1: Days 1-5)

**Day 1: Observability** (5 SP)
- Feature 24.1: Prometheus Metrics Implementation

**Day 2: LLM Proxy Improvements** (8 SP)
- Feature 24.3: Async/Sync Bridge Refactoring (5 SP)
- Feature 24.2: Token Tracking Accuracy Fix (3 SP)

**Day 3: Testing & Quality** (5 SP)
- Feature 24.7: Missing Integration Tests

**Day 4: Code Quality** (3 SP)
- Feature 24.4: Code Linting and Type Safety (includes TD-TODO-01, TD-TODO-02, TD-TODO-03)

**Day 5: Documentation** (3 SP)
- Feature 24.8: Documentation Debt Resolution

**Total:** 24 SP (5 days)

### Sprint 25 (Week 1: Days 1-3) - Refactoring Debt

**Day 1: Deprecated Code Removal** (P1)
- TD-REF-01: Remove unified_ingestion.py (1 day)

**Day 2: More Deprecated Code** (P1)
- TD-REF-02: Archive three_phase_extractor.py (0.5 day)
- TD-REF-03: Remove LlamaIndex load_documents() (1 day)

**Day 3: Code Duplication** (P2)
- TD-REF-04: Remove Duplicate Base Agent (0.5 day)
- TD-REF-05: Consolidate Embedding Services (1 day)

**Total:** 4 days (P1 deprecated code + P2 duplications)

### Sprint 25 (Week 2: Days 4-5) - Architecture

**Day 4-5: Architecture Improvements** (P2/P3)
- TD-REF-06: Standardize Client Naming (1 day)
- TD-REF-07: Extract BaseClient Pattern (1 day)

**Total:** 2 days

### Future Sprints (Sprint 26+)

**Sprint 26: ANY-LLM & VLM Integration**
- TD-23.1: ANY-LLM Full Integration (2 days)
- TD-23.2: DashScope VLM Routing (1 day)

**Sprint 27: Error Handling & Enhancements**
- TD-REF-08: Standardize Error Handling (2 days)
- TD-TODO-04: Multi-hop Context Injection (2 days)

**Sprint 28: Memory & Profiling**
- TD-TODO-05: Memory Consolidation Migration (1 day)
- TD-TODO-06: Profiling Modules (2 days)
- TD-TODO-07: LightRAG Entity Extraction (1 day)

---

## 📋 Dependencies & Risks

### Critical Dependencies

1. **Sprint 22 Incomplete:**
   - Phase 1 (API Security) COMPLETED
   - Phase 2 (Hybrid Ingestion) COMPLETED
   - **Phase 3 (Rest Refactoring) NOT COMPLETED** → Deferred to Sprint 24/25

2. **Sprint 23 Incomplete:**
   - Feature 23.6 (LangGraph Migration) PARTIALLY COMPLETE → Missing integration tests (Sprint 24 Feature 24.7)

3. **ADR Compliance:**
   - ADR-026: Pure LLM Extraction (requires TD-REF-02)
   - ADR-028: LlamaIndex Deprecation (requires TD-REF-03)
   - ADR-027: Docling Container (requires TD-REF-01)

### Risk Assessment

**Low Risk:**
- Code TODOs (TD-TODO-01 to TD-TODO-03) - No breaking changes
- Token tracking fix (TD-23.3) - Improves accuracy
- Async/sync bridge (TD-23.4) - Internal refactoring

**Medium Risk:**
- Deprecated code removal (TD-REF-01 to TD-REF-03) - Breaking changes, but well-documented
- Client naming (TD-REF-06) - Public API changes (mitigate with aliases)

**High Risk:**
- BaseClient pattern (TD-REF-07) - Affects all clients (phased rollout recommended)
- Error handling standardization (TD-REF-08) - Affects all components (gradual migration)

---

## ✅ Success Criteria

### Sprint 24 Success:
- ✅ Prometheus metrics endpoint operational (`/metrics`)
- ✅ Token tracking 100% accurate (no 50/50 split)
- ✅ Async/sync bridge removed (cleaner code)
- ✅ Integration tests for LangGraph pipeline passing
- ✅ All P0/P1 TODOs resolved or documented
- ✅ Code quality >90% (Ruff, MyPy strict mode)
- ✅ Test coverage >80% maintained
- ✅ Documentation updated (architecture, API, guides)

### Sprint 25 Success:
- ✅ All deprecated files removed (unified_ingestion.py, three_phase_extractor.py, load_documents())
- ✅ Code duplications eliminated (base agent, embedding services)
- ✅ Client naming standardized
- ✅ ADR compliance (ADR-026, ADR-027, ADR-028)
- ✅ Zero P1 technical debt remaining

### Long-Term Success (Sprint 26+):
- ✅ ANY-LLM fully integrated (Gateway deployed)
- ✅ VLM routing unified
- ✅ BaseClient pattern adopted across all clients
- ✅ Error handling standardized
- ✅ All enhancements completed (multi-hop, profiling)
- ✅ Zero P2 technical debt remaining

---

## 📚 Related Documents

**Refactoring Plans:**
- `docs/refactoring/reference/BACKEND_REFACTORING_PLAN.md` (47 items)
- `docs/refactoring/reference/API_REFACTORING_PLAN_V1.md` (21 items)
- `docs/refactoring/reference/TESTING_STRATEGY.md` (17 test gaps)
- `docs/refactoring/SPRINT_22_HYBRID_APPROACH_PLAN.md` (incomplete Phase 3)

**Sprint Plans:**
- `docs/sprints/SPRINT_24_PLANNING.md` (current sprint)
- `docs/sprint-23/SPRINT_23_PLANNING_v2_ANY_LLM.md` (Sprint 23 debt)

**ADRs:**
- ADR-026: Pure LLM Extraction Default
- ADR-027: Docling Container Architecture
- ADR-028: LlamaIndex Deprecation Strategy
- ADR-033: ANY-LLM Integration

**Code Analysis:**
- TODO comments: 31 items in src/ directory
- Grep pattern: `TODO:` in Python files

---

**Last Updated:** 2025-11-13
**Author:** Backend Agent (Claude Code)
**Status:** Ready for Sprint 24 Planning Review
**Next Steps:** Review with Klaus, finalize Sprint 24 scope
