# Sprint 24: Dependency Optimization & CI Performance (ORIGINAL PLAN - SEE SUMMARY)

**Status:** ✅ COMPLETED (but scope changed - see SPRINT_24_SUMMARY.md)
**Original Goal:** Technical Debt Cleanup & System Hardening
**Actual Goal:** Dependency optimization, CI performance improvements, and lazy imports
**Duration:** 2 days (2025-11-13 to 2025-11-14)
**Prerequisites:** Sprint 23 complete (Multi-Cloud LLM Integration)
**Story Points (Planned):** 34 SP
**Story Points (Actual):** 28 SP

---

⚠️ **IMPORTANT: THIS IS THE ORIGINAL PLAN - IT WAS NOT FULLY EXECUTED**

**What Actually Happened:**
Sprint 24 pivoted from the planned technical debt cleanup to **critical dependency optimization and CI performance improvements** after discovering:
- CI taking 15-20 minutes (5-8 min just for dependency installation)
- 1.5GB dependency footprint blocking minimal installations
- 89 Ruff linter errors causing CI failures
- llama_index as required core dependency

**For the ACTUAL Sprint 24 execution and results, see:**
👉 **[SPRINT_24_SUMMARY.md](SPRINT_24_SUMMARY.md)** 👈

**Quick Summary of Actual Sprint 24:**
- ✅ Features 24.9-24.15 implemented (28 SP)
- ✅ CI performance: **85% faster** (15-20 min → 2-3 min)
- ✅ Dependency install: **97% faster** (5-8 min → 3-14 sec)
- ✅ Minimal install: **60% smaller** (1.5GB → ~600MB)
- ✅ Ruff linter: **100% fixed** (89 → 0 errors)
- ✅ Lazy imports: **5 core files**
- ❌ Features 24.1-24.8 below: **DEFERRED to Sprint 25**

---

# ORIGINAL PLAN BELOW (Not Fully Executed)

---

## 🎯 Sprint Objectives

### **Primary Goals:**
1. Resolve Sprint 23 technical debt (ANY-LLM, VLM, cost tracking)
2. Implement missing observability features (Prometheus metrics)
3. Improve code quality and maintainability
4. Fix Windows-specific development issues
5. Enhance testing infrastructure

### **Success Criteria:**
- ✅ All P0 and P1 technical debt items resolved
- ✅ Prometheus metrics exporting to /metrics endpoint
- ✅ Token tracking accuracy improved (no 50/50 estimation)
- ✅ Async/sync bridge refactored (cleaner architecture)
- ✅ Code quality improvements (linting, type safety)
- ✅ Test coverage maintained >80%

---

## 📊 Technical Debt Overview

### Total Technical Debt Items Found: 15

**Priority Breakdown:**
- **P0 (Critical):** 0 items
- **P1 (High):** 0 items
- **P2 (Medium):** 3 items (TD-23.1, TD-G.1, TD-G.2)
- **P3 (Low):** 4 items (TD-23.2, TD-23.3, TD-23.4, remaining TODO items)

**Effort Estimation:**
- **Total Effort:** 16 days (34 SP)
- **Sprint 24 Scope:** 11 days (focus on P2 and high-value P3)
- **Future Sprints:** 5 days (deferred low-priority items)

---

## 📦 Sprint Features

### Category 1: Observability & Monitoring

#### Feature 24.1: Prometheus Metrics Implementation (5 SP)
**Priority:** P2 (Medium)
**Duration:** 1 day
**Source:** TD-G.2 (Sprint 23), aegis_llm_proxy.py:514-518

**Problem:**
Cost tracking logs structured metrics but doesn't export to Prometheus. No /metrics endpoint for monitoring dashboards.

**Solution:**
Implement `src/core/metrics.py` with prometheus_client and export metrics endpoint.

**Deliverables:**
- [ ] `src/core/metrics.py` with LLM-specific metrics
- [ ] FastAPI /metrics endpoint
- [ ] Grafana dashboard JSON (LLM cost, latency, requests)
- [ ] Documentation in `docs/guides/MONITORING.md`

**Metrics to Implement:**
```python
# LLM Metrics
llm_requests_total = Counter("llm_requests_total", "Total LLM requests", ["provider", "model", "task_type"])
llm_latency_seconds = Histogram("llm_latency_seconds", "LLM request latency", ["provider", "model"])
llm_cost_usd = Counter("llm_cost_usd", "Total LLM cost in USD", ["provider", "model"])
llm_tokens_used = Counter("llm_tokens_used", "Total tokens used", ["provider", "model", "token_type"])
llm_errors_total = Counter("llm_errors_total", "Total LLM errors", ["provider", "error_type"])

# Budget Metrics
monthly_budget_remaining = Gauge("monthly_budget_remaining_usd", "Monthly budget remaining", ["provider"])
monthly_spend = Gauge("monthly_spend_usd", "Monthly spend so far", ["provider"])
```

**Acceptance Criteria:**
- ✅ /metrics endpoint returns Prometheus-formatted metrics
- ✅ Metrics update in real-time during LLM requests
- ✅ Grafana dashboard displays cost and latency trends
- ✅ Budget alerts trigger when >80% spent
- ✅ Integration tests validate metric collection

---

### Category 2: LLM Proxy & Cost Tracking

#### Feature 24.2: Token Tracking Accuracy Fix (3 SP)
**Priority:** P3 (Low)
**Duration:** 0.5 day
**Source:** TD-23.3, aegis_llm_proxy.py:495-497

**Problem:**
Token split estimation uses 50/50 split for input/output tokens because ANY-LLM response doesn't provide detailed breakdown. Alibaba Cloud charges different rates for input vs output.

**Current Code:**
```python
# Estimate 50/50 split for input/output tokens if not available
tokens_input = result.tokens_used // 2
tokens_output = result.tokens_used - tokens_input
```

**Solution:**
Extract detailed token usage from API responses. Alibaba Cloud returns `prompt_tokens` and `completion_tokens`.

**Implementation:**
```python
# Parse response.usage properly
if hasattr(result, 'usage') and result.usage:
    tokens_input = result.usage.get('prompt_tokens', 0)
    tokens_output = result.usage.get('completion_tokens', 0)
else:
    # Fallback to total tokens
    tokens_input = result.tokens_used // 2
    tokens_output = result.tokens_used - tokens_input
```

**Deliverables:**
- [ ] Update `aegis_llm_proxy.py` to parse usage properly
- [ ] Add unit tests for token parsing
- [ ] Update cost tracker with accurate input/output split
- [ ] Verify with DashScope API response

**Acceptance Criteria:**
- ✅ Token input/output split accurate (not 50/50)
- ✅ Cost calculations use correct rates
- ✅ Unit tests cover edge cases (missing usage field)
- ✅ SQLite database shows accurate token breakdown

---

#### Feature 24.3: Async/Sync Bridge Refactoring (5 SP)
**Priority:** P3 (Low)
**Duration:** 1 day
**Source:** TD-23.4, image_processor.py:414-434

**Problem:**
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

**Solution:**
Make entire ingestion pipeline async. Refactor `ImageProcessor.process_image()` to be async.

**Deliverables:**
- [ ] Refactor `ImageProcessor.process_image()` to async
- [ ] Update all callers to use `await`
- [ ] Remove ThreadPoolExecutor complexity
- [ ] Verify LangGraph pipeline compatibility
- [ ] Update tests to use async fixtures

**Acceptance Criteria:**
- ✅ `ImageProcessor` fully async
- ✅ No ThreadPoolExecutor usage
- ✅ All callers updated (ingestion pipeline)
- ✅ Tests passing with async fixtures
- ✅ Performance unchanged or improved

---

### Category 3: Architecture & Code Quality

#### Feature 24.4: Code Linting and Type Safety Improvements (5 SP) ⭐ EXPANDED
**Priority:** P1 (High) - **UPGRADED from P3 due to CI failures**
**Duration:** 1 day
**Source:** CI Ruff Linter failures (89 errors) + TODO comments in codebase

**Problem:**
CI failing with 89 Ruff linter errors (primarily type annotations) + multiple TODO comments indicating incomplete implementations.

**Ruff Linter Errors (89 total):**
- **65 errors:** Type annotations (UP045: `Optional[X]` → `X | None`, UP035: `Dict/List/Tuple` → `dict/list/tuple`, UP006: Generic type hints)
- **15 errors:** Unused imports (F401)
- **5 errors:** Import sorting (I001)
- **4 errors:** Style issues (SIM102, SIM105, UP017, UP015, etc.)

**Affected Modules:**
- `src/components/llm_proxy/*` (30 errors) - Sprint 23 code
- `src/components/ingestion/*` (25 errors)
- `src/api/*` (20 errors)
- `src/core/*` (10 errors)
- Others (4 errors)

**TODO Items Found:**
1. `scripts/benchmark_embeddings.py:293` - Implement NDCG@10, MRR, Precision@5
2. `src/components/retrieval/query_decomposition.py:375` - Multi-hop query context injection
3. `src/components/profiling/__init__.py:24,44` - Sprint 17 profiling modules
4. `src/components/memory/monitoring.py:211,212,259,260` - Qdrant/Graphiti capacity tracking
5. `src/api/main.py:103,109` - Startup/shutdown event handlers
6. `src/api/health/memory_health.py:180,181,251-260,284-293` - Health check implementations

**Solution:**
1. **Fix all 89 Ruff linter errors** (modern type hints, remove unused imports, sort imports)
2. Systematic cleanup of TODO items, implement high-priority or document deferral

**Deliverables:**
- [ ] Fix 89 Ruff linter errors (modern type annotations)
- [ ] Remove unused imports (15 instances)
- [ ] Sort imports (5 instances)
- [ ] Fix style issues (4 instances)
- [ ] Audit all TODO comments in src/
- [ ] Implement high-priority TODOs (health checks, monitoring)
- [ ] Document deferred TODOs with rationale
- [ ] Run MyPy strict mode and fix type errors

**Acceptance Criteria:**
- ✅ Ruff linter passing (0 errors) - **CI blocker resolved**
- ✅ All P0/P1 TODOs implemented
- ✅ P2/P3 TODOs documented with tickets
- ✅ MyPy strict mode passing
- ✅ Code quality score >90%
- ✅ CI Code Quality job passing

---

#### Feature 24.5: DashScope VLM Routing Unification (5 SP)
**Priority:** P3 (Low) - DEFERRED to Future Sprint
**Duration:** 1 day
**Source:** TD-23.2, dashscope_vlm.py

**Problem:**
`DashScopeVLMClient` bypasses `AegisLLMProxy` routing logic. VLM requests don't go through unified routing system.

**Impact:**
- VLM cost tracking works (manual integration)
- No unified routing metrics for VLM vs text tasks
- Code duplication between `aegis_llm_proxy.py` and `dashscope_vlm.py`

**Solution (Future):**
Extend `AegisLLMProxy` with VLM-specific generate method. Unified interface: `proxy.generate(task)` for both text and vision.

**Decision for Sprint 24:**
**DEFERRED** - Current workaround is functional. ANY-LLM doesn't support VLM yet, so unified routing would require custom implementation. Re-evaluate in Sprint 25+ when ANY-LLM adds VLM support.

**Related Files:**
- `src/components/llm_proxy/dashscope_vlm.py`
- `src/components/ingestion/image_processor.py`

---

#### Feature 24.6: ANY-LLM Full Integration (8 SP)
**Priority:** P2 (Medium) - DEFERRED to Future Sprint
**Duration:** 2 days
**Source:** TD-23.1, aegis_llm_proxy.py

**Problem:**
Using ANY-LLM's `acompletion()` function for text generation but NOT using full framework features:
- ❌ ANY-LLM BudgetManager (built-in)
- ❌ ANY-LLM CostTracker (built-in)
- ❌ ANY-LLM ConnectionPooling
- ❌ ANY-LLM Gateway (centralized proxy)

**Current Workaround:**
- Custom SQLite `CostTracker` (389 LOC)
- Manual budget checking in `aegis_llm_proxy.py`

**Decision for Sprint 24:**
**DEFERRED** - Custom SQLite solution working perfectly (4/4 tests passing, $0.003 tracked). ANY-LLM Gateway requires separate server deployment (infrastructure complexity). Re-evaluate if:
- ANY-LLM adds VLM support
- We need multi-tenant cost tracking
- Database grows beyond 100MB

**Future Resolution Options:**
1. Deploy ANY-LLM Gateway as microservice (adds infrastructure complexity)
2. Keep custom SQLite solution (simpler, working well)
3. Contribute VLM support to ANY-LLM upstream

**Related Files:**
- `src/components/llm_proxy/cost_tracker.py`
- `src/components/llm_proxy/aegis_llm_proxy.py`

---

### Category 4: Testing & Quality Assurance

#### Feature 24.7: Missing Integration Tests (5 SP)
**Priority:** P2 (Medium)
**Duration:** 1 day
**Source:** Sprint 23 Feature 23.6 (LangGraph migration)

**Problem:**
Feature 23.6 (LangGraph migration) marked as incomplete - missing integration tests.

**Solution:**
Create comprehensive integration tests for LangGraph ingestion pipeline.

**Deliverables:**
- [ ] Integration tests for LangGraph nodes (5 nodes)
- [ ] E2E test for full ingestion pipeline
- [ ] Test coverage report (target: >80%)
- [ ] CI pipeline validation

**Test Coverage:**
```python
# tests/integration/components/ingestion/test_langgraph_pipeline.py

async def test_memory_check_node_success():
    """Test memory check node with sufficient memory."""
    ...

async def test_docling_processing_node():
    """Test Docling container integration."""
    ...

async def test_chunking_node():
    """Test chunking with HybridChunker."""
    ...

async def test_embedding_node():
    """Test Qdrant embedding and upsert."""
    ...

async def test_graph_extraction_node():
    """Test LightRAG entity/relation extraction."""
    ...

async def test_end_to_end_pipeline():
    """Test complete pipeline: PDF → Qdrant + Neo4j."""
    ...
```

**Acceptance Criteria:**
- ✅ 6+ integration tests created
- ✅ All tests passing
- ✅ Coverage >80% for ingestion module
- ✅ CI pipeline includes new tests
- ✅ Documentation updated

---

### Category 5: Documentation & Cleanup

#### Feature 24.8: Documentation Debt Resolution (3 SP)
**Priority:** P3 (Low)
**Duration:** 0.5 day
**Source:** Various docs/ TODOs

**Problem:**
Multiple documentation gaps and TODO placeholders.

**Documentation Gaps:**
1. Architecture Overview: `docs/architecture/CURRENT_ARCHITECTURE.md` (TODO: Task 1.4)
2. Production Deployment: Update with Sprint 21-23 changes
3. API Documentation: Complete missing endpoints

**Solution:**
Systematic documentation review and completion.

**Deliverables:**
- [ ] `docs/architecture/CURRENT_ARCHITECTURE.md` - Sprint 23 architecture
- [ ] Update `docs/guides/PRODUCTION_DEPLOYMENT.md`
- [ ] API documentation for /metrics endpoint
- [ ] Update TECH_DEBT.md with Sprint 24 resolutions

**Acceptance Criteria:**
- ✅ All high-priority documentation TODOs resolved
- ✅ Architecture docs reflect Sprint 23 state
- ✅ API docs complete and tested
- ✅ TECH_DEBT.md updated

---

#### Feature 24.13: Remaining Unit Test Failures Documentation (0 SP)
**Priority:** P1 (High) - DOCUMENTATION ONLY
**Duration:** 0 hours (documentation task)
**Source:** CI Run 19341717338 - Post Feature 24.11

**Problem:**
After successful Feature 24.11 (IngestionError signature fixes), CI run 19341717338 revealed 5 additional unit test failures unrelated to IngestionError:

**Failure 1: test_chunk_id_provenance_tracking (LightRAG Cypher Query)**
- **File:** `tests/unit/components/graph_rag/test_lightrag_wrapper.py::TestLightRAGWrapperSprint16::test_chunk_id_provenance_tracking`
- **Error:** `AssertionError: assert 'MATCH (e:base {entity_id: entity_id})' in '...'`
- **Root Cause:** Cypher query format mismatch
  - **Expected format:** `MATCH (e:base {entity_id: entity_id})`
  - **Actual format:** `MERGE (e:base:PERSON {entity_id: $entity_id})`
- **Analysis:**
  - Test expects `MATCH` statement but code generates `MERGE`
  - Test expects non-parameterized syntax (`entity_id: entity_id`) but code uses parameterized (`$entity_id`)
  - Code uses multi-label format (`:base:PERSON`) which is modern Neo4j best practice
- **Impact:** Low - Cypher query works correctly, test assertion outdated
- **Recommendation:** Update test assertion to match modern Cypher format (MERGE + parameterized + multi-label)

**Failure 2: test_start_container_success (Docling Mock Call Count)**
- **File:** `tests/unit/components/ingestion/test_docling_client_unit.py::test_start_container_success`
- **Error:** `AssertionError: Expected 'run' to have been called once. Called 2 times.`
- **Actual Calls:**
  1. `docker ps --filter name=aegis-docling --format '{{.Names}}'` (check if container running)
  2. `docker compose --profile ingestion up -d docling` (start container)
- **Root Cause:** Test expects only the `docker compose` call, but implementation now includes pre-check
- **Analysis:**
  - Code behavior: Check if container already running before starting (defensive programming)
  - Test expectation: Only expects docker compose call
  - Added defensive check is good practice (avoid duplicate container starts)
- **Impact:** Low - Implementation improvement, test needs update
- **Recommendation:** Update test to expect 2 calls instead of 1, or use `assert_called_with()` for specific call

**Failure 3: test_parse_document_success (Docling Task ID)**
- **File:** `tests/unit/components/ingestion/test_docling_client_unit.py::test_parse_document_success`
- **Error:** `IngestionError: Unexpected error parsing document: Document ingestion failed: No task_id in response: {...}`
- **Root Cause:** Mock response structure missing 'task_id' field
- **Analysis:**
  - Docling container API uses async task pattern (POST → task_id → poll status)
  - Mock response returns full document structure directly (synchronous pattern)
  - Code expects: `{'task_id': 'task_123'}`
  - Mock returns: `{'text': '...', 'metadata': {...}, 'tables': [...], 'images': [...]}`
- **Impact:** Medium - Test mock doesn't match actual API contract
- **Recommendation:** Fix mock to include task_id field and async task flow

**Failure 4: test_parse_batch_success (Docling Batch Parsing)**
- **File:** `tests/unit/components/ingestion/test_docling_client_unit.py::test_parse_batch_success`
- **Error:** `AssertionError: assert 0 == 3` (Expected 3 parsed documents, got 0)
- **Root Cause:** Same as Failure 3 - missing task_id in mock responses
- **Analysis:**
  - Test expects 3 documents to be parsed successfully
  - All 3 fail due to missing task_id in mock response
  - Batch processing logic works, but mock data structure incorrect
- **Impact:** Medium - Test infrastructure issue
- **Recommendation:** Same fix as Failure 3 - update mock data structure

**Failure 5: test_parse_batch_partial_failure (Docling Partial Failure)**
- **File:** `tests/unit/components/ingestion/test_docling_client_unit.py::test_parse_batch_partial_failure`
- **Error:** `AssertionError: assert 0 == 2` (Expected 2 successful parses, got 0)
- **Root Cause:** Same as Failure 3 - missing task_id in mock responses
- **Analysis:**
  - Test scenario: 3 documents, 1 should fail, 2 should succeed
  - Actual result: All 3 fail due to mock data issue
  - Partial failure handling logic not tested
- **Impact:** Medium - Critical test scenario not validated
- **Recommendation:** Same fix as Failure 3 + verify partial failure logic

**Summary:**
- **Total Failures:** 5 tests
- **Categories:**
  1. Outdated test assertions (1 test) - Low priority
  2. Mock call count mismatches (1 test) - Low priority
  3. Mock data structure issues (3 tests) - Medium priority
- **Root Causes:**
  - LightRAG: Test assertions don't match modern Cypher syntax
  - Docling: Mock data doesn't match async task API contract
- **Next Steps (Feature 24.14):**
  1. Fix LightRAG test assertion (1 line change)
  2. Update Docling mock call expectations (1 test)
  3. Fix Docling mock data structure for async task pattern (3 tests)

**Deliverables:**
- ✅ Documentation of all 5 failures (this section)
- ✅ Root cause analysis completed
- ✅ Impact assessment completed
- ✅ Recommendations for Feature 24.14 provided

**Acceptance Criteria:**
- ✅ All 5 failures documented with full error details
- ✅ Root causes identified
- ✅ Impact and priority assessed
- ✅ Recommendations for fixes provided

---

## 🔧 Technical Debt Resolution Summary

### Sprint 23 Technical Debt

| ID | Description | Priority | Effort | Sprint 24 Action |
|----|-------------|----------|--------|------------------|
| TD-23.1 | ANY-LLM partial integration | P2 | 3 days | **DEFERRED** - Working solution |
| TD-23.2 | DashScope VLM bypass routing | P3 | 2 days | **DEFERRED** - Functional workaround |
| TD-23.3 | Token split estimation | P3 | 1 day | **Feature 24.2** ✅ |
| TD-23.4 | Async/sync bridge | P3 | 2 days | **Feature 24.3** ✅ |

### General Technical Debt

| ID | Description | Priority | Effort | Sprint 24 Action |
|----|-------------|----------|--------|------------------|
| TD-G.1 | Windows-only dev env | P2 | 1 week | **DEFERRED** - Use pathlib, LF endings |
| TD-G.2 | No Prometheus metrics | P2 | 3 days | **Feature 24.1** ✅ |

### Sprint 24 Resolution Plan

**Week 1 (Days 1-3): P2 and High-Value P3**
- Day 1: Feature 24.1 (Prometheus Metrics) - 5 SP
- Day 2: Feature 24.3 (Async/Sync Bridge) - 5 SP
- Day 2.5: Feature 24.2 (Token Tracking) - 3 SP
- Day 3: Feature 24.7 (Integration Tests) - 5 SP

**Week 1 (Days 4-5): Code Quality & Documentation**
- Day 4: Feature 24.4 (Linting & Type Safety) - 3 SP
- Day 5: Feature 24.8 (Documentation) - 3 SP

**Deferred to Future Sprints:**
- TD-23.1: ANY-LLM Full Integration (8 SP) - Sprint 25+
- TD-23.2: DashScope VLM Routing (5 SP) - Sprint 25+
- TD-G.1: Windows-only dev env (1 week) - Sprint 26+

---

## 🎯 Sprint 24 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| TD Items Resolved | 4/4 scheduled | Feature completion |
| Prometheus Metrics | /metrics endpoint live | curl test |
| Token Tracking Accuracy | 100% (no estimation) | Database validation |
| Code Quality Score | >90% | Ruff + MyPy |
| Test Coverage | >80% | pytest --cov |
| Documentation Completeness | 100% P0/P1 TODOs | Manual review |

---

## 📋 Related Technical Debt Items Not in Sprint 24

### Historical Technical Debt (Resolved)

**Sprint 12:**
- ✅ TD-23: LightRAG E2E tests (5 tests fixed)
- ✅ TD-24: Graphiti method renamed (14 tests)
- ✅ TD-25: Redis async cleanup (0 warnings)

**Sprint 13:**
- ✅ TD-26: Memory Agent Event Loop Errors (4 tests)
- ✅ TD-27: Graphiti API Compatibility (18 tests)
- ✅ TD-28: LightRAG Fixture Connection (5 tests)
- ✅ TD-29: pytest-timeout not installed
- ✅ TD-31, TD-32, TD-33: LightRAG timeout issues (resolved with Gemma-3-4b)

**Sprint 18:**
- ✅ TD-38: Test Selector Modernization
- ✅ TD-39: Mock Data Synchronization
- ✅ TD-40: Test Helper Library
- ✅ TD-41: Admin Stats Endpoint 404
- ✅ TD-42: Import Error Prevention

**Sprint 22:**
- ✅ TD-22.1: LlamaIndex Partial Deprecation (ADR-028)

### Low-Priority TODOs (Not Scheduled)

**Profiling Module:**
- `src/components/profiling/__init__.py:24,44` - Sprint 17 profiling modules (DEFERRED - not critical)

**Benchmark Metrics:**
- `scripts/benchmark_embeddings.py:293` - NDCG@10, MRR, Precision@5 (NICE TO HAVE)

**Query Decomposition:**
- `src/components/retrieval/query_decomposition.py:375` - Multi-hop context injection (FUTURE ENHANCEMENT)

---

## 🚀 Sprint 24 Completion Criteria

- ✅ Prometheus metrics endpoint operational
- ✅ Token tracking accuracy improved (no 50/50 split)
- ✅ Async/sync bridge refactored (cleaner code)
- ✅ Integration tests for LangGraph pipeline
- ✅ Code quality improvements (linting, type safety)
- ✅ Documentation updated (architecture, API, guides)
- ✅ Test coverage >80% maintained
- ✅ All P2 technical debt resolved or deferred with rationale

---

## 📊 Priority Matrix

```
┌───────────────┬────────────────────────┬────────────────────────┐
│               │  Low Effort (<2 days)  │ High Effort (>2 days)  │
├───────────────┼────────────────────────┼────────────────────────┤
│ High Impact   │ Feature 24.2 (Token)   │ Feature 24.1 (Metrics) │
│               │ Feature 24.8 (Docs)    │ Feature 24.7 (Tests)   │
├───────────────┼────────────────────────┼────────────────────────┤
│ Medium Impact │ Feature 24.4 (Quality) │ Feature 24.3 (Async)   │
│               │                        │ TD-23.1 (DEFERRED)     │
├───────────────┼────────────────────────┼────────────────────────┤
│ Low Impact    │ TODO cleanup           │ TD-23.2 (DEFERRED)     │
│               │                        │ TD-G.1 (DEFERRED)      │
└───────────────┴────────────────────────┴────────────────────────┘
```

---

## 🔄 Next Steps After Sprint 24

**Sprint 25 Candidates:**
1. ANY-LLM Full Integration (TD-23.1) - If ANY-LLM adds VLM support
2. DashScope VLM Routing Unification (TD-23.2) - If routing metrics needed
3. Cross-platform Development (TD-G.1) - Linux CI/CD pipeline
4. Advanced Features (multi-hop queries, profiling modules)

**Long-Term Roadmap:**
- Kubernetes production deployment
- Multi-tenant cost tracking
- Advanced query decomposition
- Enhanced profiling and analytics

---

**Sprint 24 Objectives:** Technical debt cleanup and system hardening ✅
**Next Sprint:** Sprint 25 - Advanced Features & Production Readiness

**Last Updated:** 2025-11-13
**Author:** Documentation Agent (Claude Code)
**Architecture:** Post-Sprint 23 Multi-Cloud LLM System
