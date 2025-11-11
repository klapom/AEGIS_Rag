# Test Coverage Improvement Plan
## Sprint 14 - Path to 80% Coverage

**Current Status:** 32% total coverage (9307 statements, 6329 missed)
**Target:** 80% coverage
**Gap:** 48 percentage points (~4480 additional statements to cover)

**Generated:** 2025-10-27
**Context:** This plan addresses the coverage gap identified during Sprint 14 CI improvements.

---

## Executive Summary

### Coverage by Component

| Component | Current | Target | Priority | Estimated Effort |
|-----------|---------|--------|----------|------------------|
| **UI** | 0% | 60% | P2 | 3d |
| **Graph RAG** | 15% | 75% | P0 | 8d |
| **Agents** | 24% | 80% | P0 | 10d |
| **Memory System** | 18% | 75% | P1 | 6d |
| **MCP Components** | 19% | 70% | P2 | 4d |
| **API Endpoints** | 45% | 80% | P1 | 4d |
| **Evaluation** | 13% | 70% | P2 | 3d |
| **Core/Utils** | 75% | 85% | P3 | 2d |

**Total Estimated Effort:** 40 developer-days

---

## Phase 1: Critical Path Components (P0) - Weeks 1-3

### 1.1 Graph RAG Components (Current: 9-45%)
**Goal:** 75% coverage | **Effort:** 8 days | **Priority:** P0

#### High Priority Files (<20% coverage):

**1. `lightrag_wrapper.py` (9% → 75%)**
- **Missing:** Insert operations, query operations, graph updates
- **Tests Needed:**
  ```
  - test_lightrag_initialization
  - test_insert_document_success
  - test_insert_document_with_entities
  - test_query_local_search
  - test_query_global_search
  - test_query_hybrid_search
  - test_graph_update_operations
  - test_error_handling (Neo4j failures, LLM failures)
  - test_concurrent_operations
  ```
- **Coverage Target:** 75% (251 of 335 statements)
- **Estimated Effort:** 3 days

**2. `extraction_service.py` (15% → 75%)**
- **Missing:** Entity extraction, relation extraction, retry logic
- **Tests Needed:**
  ```
  - test_extract_entities_from_text
  - test_extract_relations_from_text
  - test_extraction_with_confidence_scores
  - test_extraction_retry_on_failure
  - test_extraction_timeout_handling
  - test_batch_extraction
  - test_invalid_input_handling
  ```
- **Coverage Target:** 75% (120 of 160 statements)
- **Estimated Effort:** 2 days

**3. `three_phase_extractor.py` (19% → 75%)**
- **Missing:** Phase 1 (SpaCy), Phase 2 (Dedup), Phase 3 (LLM enrichment)
- **Tests Needed:**
  ```
  - test_phase1_spacy_extraction
  - test_phase2_semantic_deduplication
  - test_phase3_llm_enrichment
  - test_end_to_end_three_phase_pipeline
  - test_performance_benchmarks
  - test_deduplication_rate_metrics
  ```
- **Coverage Target:** 75% (68 of 90 statements)
- **Estimated Effort:** 2 days

**4. `query_builder.py` (12% → 70%)**
- **Missing:** Cypher query construction, parameter binding
- **Tests Needed:**
  ```
  - test_build_local_search_query
  - test_build_global_search_query
  - test_build_hybrid_search_query
  - test_build_temporal_query
  - test_query_parameterization
  - test_cypher_injection_prevention
  ```
- **Coverage Target:** 70% (119 of 170 statements)
- **Estimated Effort:** 1 day

### 1.2 Agent System (Current: 16-29%)
**Goal:** 80% coverage | **Effort:** 10 days | **Priority:** P0

#### Critical Agent Files:

**1. `coordinator.py` (24% → 80%)**
- **Missing:** Agent orchestration, state management, routing decisions
- **Tests Needed:**
  ```
  - test_coordinator_initialization
  - test_route_to_vector_search_agent
  - test_route_to_graph_query_agent
  - test_route_to_memory_agent
  - test_parallel_agent_execution
  - test_agent_failure_handling
  - test_state_checkpointing
  - test_conversation_flow_management
  - test_timeout_handling
  ```
- **Coverage Target:** 80% (66 of 82 statements)
- **Estimated Effort:** 3 days

**2. `graph_query_agent.py` (16% → 80%)**
- **Missing:** Graph query construction, result processing
- **Tests Needed:**
  ```
  - test_local_search_execution
  - test_global_search_execution
  - test_hybrid_search_execution
  - test_query_result_parsing
  - test_context_fusion
  - test_neo4j_connection_failure
  - test_empty_result_handling
  - test_query_timeout
  ```
- **Coverage Target:** 80% (80 of 100 statements)
- **Estimated Effort:** 3 days

**3. `memory_agent.py` (20% → 80%)**
- **Missing:** Memory retrieval, consolidation triggering
- **Tests Needed:**
  ```
  - test_retrieve_from_redis_cache
  - test_retrieve_from_graphiti
  - test_memory_consolidation_trigger
  - test_episodic_memory_search
  - test_temporal_memory_query
  - test_memory_relevance_scoring
  - test_memory_not_found_handling
  ```
- **Coverage Target:** 80% (53 of 66 statements)
- **Estimated Effort:** 2 days

**4. `vector_search_agent.py` (21% → 80%)**
- **Missing:** Vector search, hybrid retrieval, reranking
- **Tests Needed:**
  ```
  - test_vector_search_execution
  - test_hybrid_search_with_bm25
  - test_reranking_pipeline
  - test_metadata_filtering
  - test_empty_results_handling
  - test_qdrant_connection_failure
  ```
- **Coverage Target:** 80% (60 of 75 statements)
- **Estimated Effort:** 2 days

---

## Phase 2: Production Readiness (P1) - Weeks 4-5

### 2.1 Memory System (Current: 12-23%)
**Goal:** 75% coverage | **Effort:** 6 days | **Priority:** P1

**1. `redis_manager.py` (12% → 75%)**
- **Missing:** Redis operations, connection pooling, failover
- **Tests Needed:**
  ```
  - test_redis_connection_pool
  - test_set_get_operations
  - test_batch_operations
  - test_ttl_management
  - test_connection_failure_handling
  - test_redis_cluster_support (if applicable)
  - test_memory_cleanup
  ```
- **Coverage Target:** 75% (196 of 261 statements)
- **Estimated Effort:** 2 days

**2. `graphiti_wrapper.py` (23% → 75%)**
- **Missing:** Graphiti API calls, entity/episode management
- **Tests Needed:**
  ```
  - test_add_episode
  - test_search_episodes
  - test_entity_extraction
  - test_temporal_queries
  - test_api_error_handling
  - test_concurrent_writes
  ```
- **Coverage Target:** 75% (95 of 127 statements)
- **Estimated Effort:** 2 days

**3. `consolidation.py` (16% → 70%)**
- **Missing:** Memory consolidation logic, background tasks
- **Tests Needed:**
  ```
  - test_trigger_consolidation
  - test_consolidation_strategy
  - test_memory_merging
  - test_consolidation_scheduling
  - test_consolidation_failure_recovery
  ```
- **Coverage Target:** 70% (157 of 224 statements)
- **Estimated Effort:** 2 days

### 2.2 API Endpoints (Current: 27-80%)
**Goal:** 80% coverage | **Effort:** 4 days | **Priority:** P1

**1. `chat.py` (43% → 80%)**
- **Missing:** Streaming responses, error handling, auth
- **Tests Needed:**
  ```
  - test_chat_endpoint_success
  - test_streaming_response
  - test_conversation_context
  - test_authentication_required
  - test_rate_limiting
  - test_invalid_input
  - test_timeout_handling
  ```
- **Coverage Target:** 80% (113 of 141 statements)
- **Estimated Effort:** 2 days

**2. `memory.py` (42% → 80%)**
- **Missing:** Memory CRUD operations, search endpoints
- **Tests Needed:**
  ```
  - test_store_memory_endpoint
  - test_retrieve_memory_endpoint
  - test_search_memories_endpoint
  - test_delete_memory_endpoint
  - test_pagination
  - test_filtering
  - test_error_responses
  ```
- **Coverage Target:** 80% (162 of 203 statements)
- **Estimated Effort:** 2 days

---

## Phase 3: Feature Completeness (P2) - Weeks 6-7

### 3.1 MCP Components (Current: 0-42%)
**Goal:** 70% coverage | **Effort:** 4 days | **Priority:** P2

**1. `client.py` (17% → 70%)**
- **Missing:** MCP tool calls, OAuth flow, connection management
- **Tests Needed:**
  ```
  - test_mcp_client_initialization
  - test_call_tool_success
  - test_list_tools
  - test_oauth_authentication
  - test_connection_retry
  - test_tool_call_timeout
  - test_result_parsing
  ```
- **Coverage Target:** 70% (144 of 205 statements)
- **Estimated Effort:** 2 days

**2. `connection_manager.py` (19% → 70%)**
- **Missing:** Connection pooling, health checks, failover
- **Tests Needed:**
  ```
  - test_connection_pool_management
  - test_health_check_endpoint
  - test_connection_failover
  - test_concurrent_connections
  - test_connection_timeout
  ```
- **Coverage Target:** 70% (69 of 98 statements)
- **Estimated Effort:** 1 day

**3. `tool_executor.py` (22% → 70%)**
- **Missing:** Tool execution, validation, error handling
- **Tests Needed:**
  ```
  - test_execute_tool_success
  - test_validate_tool_input
  - test_tool_execution_timeout
  - test_tool_not_found
  - test_invalid_parameters
  ```
- **Coverage Target:** 70% (44 of 63 statements)
- **Estimated Effort:** 1 day

### 3.2 UI & Monitoring (Current: 0%)
**Goal:** 60% coverage | **Effort:** 5 days | **Priority:** P2

**1. `gradio_app.py` (0% → 60%)**
- **Missing:** All UI interactions (integration tests required)
- **Tests Needed:**
  ```
  - test_app_initialization
  - test_chat_interface
  - test_file_upload
  - test_graph_visualization
  - test_memory_inspection
  - test_error_display
  - test_multi_user_sessions
  ```
- **Coverage Target:** 60% (172 of 287 statements)
- **Estimated Effort:** 3 days
- **Note:** Requires Gradio test harness setup

**2. `metrics.py` (0% → 70%)**
- **Missing:** All metrics collection
- **Tests Needed:**
  ```
  - test_prometheus_metrics_registration
  - test_counter_increment
  - test_histogram_observation
  - test_gauge_setting
  - test_metrics_export
  ```
- **Coverage Target:** 70% (29 of 42 statements)
- **Estimated Effort:** 1 day

**3. `ragas_eval.py` (26% → 70%)**
- **Missing:** RAGAS metric computation
- **Tests Needed:**
  ```
  - test_context_precision_calculation
  - test_context_recall_calculation
  - test_faithfulness_calculation
  - test_answer_relevance_calculation
  - test_eval_with_mock_data
  ```
- **Coverage Target:** 70% (109 of 156 statements)
- **Estimated Effort:** 1 day

---

## Phase 4: Polish & Maintenance (P3) - Week 8

### 4.1 Core & Utilities (Current: 75%)
**Goal:** 85% coverage | **Effort:** 2 days | **Priority:** P3

**1. `tracing.py` (26% → 85%)**
- **Tests Needed:**
  ```
  - test_span_creation
  - test_trace_context_propagation
  - test_trace_export
  ```
- **Estimated Effort:** 1 day

**2. `fusion.py` (10% → 80%)**
- **Tests Needed:**
  ```
  - test_reciprocal_rank_fusion
  - test_context_deduplication
  - test_score_normalization
  ```
- **Estimated Effort:** 1 day

---

## Implementation Strategy

### Testing Approach

**1. Unit Tests (Weeks 1-6)**
- Mock external dependencies (Qdrant, Neo4j, Redis, Ollama)
- Focus on business logic, error handling, edge cases
- Target: 70-80% coverage per module

**2. Integration Tests (Weeks 7-8)**
- Test with real services in Docker Compose
- Focus on end-to-end flows, performance, reliability
- Mark with `@pytest.mark.integration`

**3. E2E Tests (Ongoing)**
- Test critical user journeys
- Include UI interactions where applicable
- Acceptance criteria validation

### Test Fixtures & Mocking Strategy

**Centralized Fixtures (`tests/conftest.py`):**
```python
# Already implemented:
- mock_ollama_embedding_model
- mock_embedding_service
- sample_documents

# To add:
- mock_neo4j_client
- mock_lightrag_wrapper
- mock_graphiti_client
- mock_redis_client
- mock_qdrant_client
- sample_graph_data
- sample_memory_episodes
```

**Mocking Libraries:**
- `pytest-mock` for function/method mocks
- `unittest.mock.AsyncMock` for async operations
- `responses` for HTTP mocking (MCP, Ollama)
- `fakeredis` for Redis tests (faster than Docker)
- `neo4j-driver` embedded mode for graph tests

### Known Issues to Address

**Before Starting Coverage Work:**

1. **Fix Embedding Service Tests (5 failures)**
   - `conftest.py`: Update `LRUCache` import path
   - `test_embeddings.py`: Rewrite mock-based tests to use statistics
   - Files: `tests/conftest.py:342`, `tests/components/vector_search/test_embeddings.py`
   - Estimated Effort: 2 hours

2. **Fix Community Performance Test (flaky)**
   - Increase cache threshold to 300ms or make test conditional on system load
   - File: `tests/components/graph_rag/test_community_performance.py:259`
   - Estimated Effort: 30 minutes

3. **Fix CI Integration Tests (Docker/GitHub Actions)**
   - Documented as infrastructure limitation (disk space)
   - Will pass locally and in PR-triggered CI
   - No action required

---

## Milestones & Success Criteria

### Week 2 Milestone (End of Phase 1.1)
- **Target:** Graph RAG components at 75% coverage
- **Success Criteria:**
  - `lightrag_wrapper.py`: 75%
  - `extraction_service.py`: 75%
  - `three_phase_extractor.py`: 75%
  - All tests passing locally
  - Zero flaky tests

### Week 4 Milestone (End of Phase 1)
- **Target:** Critical Path (P0) complete
- **Success Criteria:**
  - Graph RAG: 75% coverage
  - Agents: 80% coverage
  - Total coverage: >50%
  - CI pipeline green (excluding Docker failures)

### Week 6 Milestone (End of Phase 2)
- **Target:** Production Readiness (P1) complete
- **Success Criteria:**
  - Memory System: 75% coverage
  - API Endpoints: 80% coverage
  - Total coverage: >65%

### Week 8 Milestone (End of Plan)
- **Target:** 80% total coverage achieved
- **Success Criteria:**
  - All P0, P1, P2 components at target coverage
  - CI `--cov-fail-under=80` passing
  - Documentation updated
  - Test suite runtime <10 minutes (unit tests only)

---

## Resource Requirements

### Tooling
- **Already Available:**
  - pytest, pytest-cov, pytest-asyncio, pytest-mock, pytest-timeout
  - Docker Compose (Qdrant, Neo4j, Redis, Ollama)
  - Coverage reporting (terminal, HTML, JSON, XML)

- **To Add:**
  - `fakeredis` - Fast in-memory Redis for tests
  - `responses` - HTTP mocking library
  - `pytest-benchmark` - Performance regression detection
  - Gradio test harness (if available)

### CI/CD Updates
- Keep `--cov-fail-under=50` during development
- Raise to 60% after Week 4, 70% after Week 6, 80% after Week 8
- Add coverage diff reporting in PRs
- Add coverage badge to README

---

## Risks & Mitigation

### Risk 1: Underestimated Complexity
**Likelihood:** Medium | **Impact:** High
- **Mitigation:** Start with Phase 1 (P0), adjust estimates after Week 2
- **Contingency:** Reduce P2/P3 scope if behind schedule

### Risk 2: Flaky Integration Tests
**Likelihood:** High | **Impact:** Medium
- **Mitigation:** Use `fakeredis`, Neo4j embedded mode where possible
- **Contingency:** Accept lower coverage for integration-heavy modules

### Risk 3: Test Maintenance Burden
**Likelihood:** Medium | **Impact:** Medium
- **Mitigation:** Invest in reusable fixtures, clear test naming
- **Contingency:** Document test patterns, create test templates

### Risk 4: UI Testing Complexity
**Likelihood:** High | **Impact:** Low
- **Mitigation:** Focus on backend logic, treat Gradio as thin layer
- **Contingency:** Accept 40-50% coverage for `gradio_app.py` if UI testing proves prohibitive

---

## Tracking & Reporting

### Daily Tracking
```bash
# Run coverage report
poetry run pytest --cov=src --cov-report=term-missing -m "not integration" -q

# Generate HTML report
poetry run coverage html
# Open: htmlcov/index.html
```

### Weekly Progress Report
- Coverage delta (current week vs last week)
- Tests added/fixed count
- Flaky test count
- CI stability (pass rate)

### Automation
- Pre-commit hook: Fail if coverage decreases by >2%
- CI: Fail if coverage below threshold (50% → 60% → 70% → 80%)
- Coverage report artifact uploaded on each CI run

---

## Appendix A: File-by-File Coverage Targets

### P0 Files (Critical Path)
| File | Current | Target | Priority | Effort |
|------|---------|--------|----------|--------|
| `lightrag_wrapper.py` | 9% | 75% | P0 | 3d |
| `extraction_service.py` | 15% | 75% | P0 | 2d |
| `three_phase_extractor.py` | 19% | 75% | P0 | 2d |
| `coordinator.py` | 24% | 80% | P0 | 3d |
| `graph_query_agent.py` | 16% | 80% | P0 | 3d |
| `memory_agent.py` | 20% | 80% | P0 | 2d |
| `vector_search_agent.py` | 21% | 80% | P0 | 2d |
| `query_builder.py` | 12% | 70% | P0 | 1d |

### P1 Files (Production Readiness)
| File | Current | Target | Priority | Effort |
|------|---------|--------|----------|--------|
| `redis_manager.py` | 12% | 75% | P1 | 2d |
| `graphiti_wrapper.py` | 23% | 75% | P1 | 2d |
| `consolidation.py` | 16% | 70% | P1 | 2d |
| `chat.py` | 43% | 80% | P1 | 2d |
| `memory.py` | 42% | 80% | P1 | 2d |

### P2 Files (Feature Completeness)
| File | Current | Target | Priority | Effort |
|------|---------|--------|----------|--------|
| `client.py` (MCP) | 17% | 70% | P2 | 2d |
| `connection_manager.py` | 19% | 70% | P2 | 1d |
| `gradio_app.py` | 0% | 60% | P2 | 3d |
| `ragas_eval.py` | 26% | 70% | P2 | 1d |
| `metrics.py` | 0% | 70% | P2 | 1d |

---

## Appendix B: Test Templates

### Template: Agent Test Suite
```python
"""Test suite for {AgentName}Agent.

Covers:
- Agent initialization
- Tool calls and execution
- State management
- Error handling
- Performance benchmarks
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.unit
@pytest.mark.asyncio
async def test_{agent_name}_initialization():
    """Test agent initializes with correct configuration."""
    agent = {AgentName}Agent(config=test_config)
    assert agent.name == "{agent_name}"
    assert agent.tools == expected_tools

@pytest.mark.unit
@pytest.mark.asyncio
async def test_{agent_name}_successful_execution(mock_dependencies):
    """Test agent executes successfully with valid input."""
    agent = {AgentName}Agent()
    result = await agent.run(state)
    assert result.status == "success"
    assert result.output is not None

@pytest.mark.unit
@pytest.mark.asyncio
async def test_{agent_name}_error_handling(mock_dependencies):
    """Test agent handles errors gracefully."""
    mock_dependencies.side_effect = Exception("Test error")
    agent = {AgentName}Agent()
    result = await agent.run(state)
    assert result.status == "error"
    assert "Test error" in result.error_message

@pytest.mark.integration
@pytest.mark.asyncio
async def test_{agent_name}_with_real_services():
    """Integration test with real dependencies."""
    # Requires: Docker Compose with services running
    agent = {AgentName}Agent()
    result = await agent.run(real_state)
    assert result.status == "success"
```

### Template: Component Test Suite
```python
"""Test suite for {ComponentName}.

Covers:
- Core functionality
- Edge cases
- Error conditions
- Performance
"""
import pytest

@pytest.mark.unit
def test_{component}_basic_operation():
    """Test basic operation with valid input."""
    component = {ComponentName}()
    result = component.process(valid_input)
    assert result == expected_output

@pytest.mark.unit
def test_{component}_empty_input():
    """Test handling of empty input."""
    component = {ComponentName}()
    with pytest.raises(ValueError, match="Input cannot be empty"):
        component.process("")

@pytest.mark.unit
def test_{component}_concurrent_access():
    """Test thread-safety for concurrent access."""
    component = {ComponentName}()
    # Test concurrent calls...

@pytest.mark.unit
@pytest.mark.benchmark
def test_{component}_performance(benchmark):
    """Benchmark performance of core operation."""
    component = {ComponentName}()
    result = benchmark(component.process, test_input)
    assert result.duration < 100  # ms
```

---

## Appendix C: Coverage Calculation Details

**Current State (from coverage.json):**
- Total Statements: 9307
- Missed Statements: 6329
- Current Coverage: 32%

**To Reach 80%:**
- Target Missed: 1861 (20% of 9307)
- Additional Coverage Needed: 4468 statements (6329 - 1861)
- Percentage Points to Gain: 48%

**Phased Targets:**
- Phase 1 End (Week 4): 50% coverage (1396 additional statements)
- Phase 2 End (Week 6): 65% coverage (2472 additional statements)
- Phase 3 End (Week 8): 80% coverage (4468 additional statements)

**Confidence Level:** Medium
- Assumes 70-80% of "missed" statements are testable
- Excludes defensive code paths, configuration logic
- UI testing may require more effort than estimated

---

## Sprint 16 Test Statistics (2025-10-28)

### New Test Coverage

**Feature 16.1: Unified Chunking Service**
- Unit Tests: 52 tests (100% pass rate)
- Integration Tests: 7 tests (100% pass rate)
- Coverage: 100% for ChunkingService
- Files: `tests/components/retrieval/test_chunking.py`

**Feature 16.2: BGE-M3 Migration**
- Unit Tests: 26 tests (100% pass rate)
- Modified Tests: 89 dimension updates across 11 files (768→1024)
- Rewritten Tests: 7 tests for new EmbeddingService API
- Coverage: 100% for UnifiedEmbeddingService
- Files: `tests/components/vector_search/test_embeddings*.py`

**Feature 16.3: Unified Re-Indexing**
- Integration Tests: Pending (admin endpoint created, tests TODO)
- Manual Testing: SSE streaming validated
- Coverage: 0% (implementation complete, tests deferred to Feature 16.4)

### Total Sprint 16 Tests Added
- **Unit Tests:** 78 tests (52 chunking + 26 embedding)
- **Integration Tests:** 7 tests
- **E2E Tests:** 10 tests (Sprint 15 frontend tests revalidated)
- **Total:** 95 new tests

### System-Wide Test Results
- **Backend Tests:** 49/52 embedding tests pass (94%)
- **Frontend Tests:** 105/144 Vitest tests pass (73%)
- **Total Tests:** 240 tests (178 passing, 74% overall)

### Known Test Failures (Pre-Existing)
1. `test_generate_embeddings_success` - TextNode API issue
2. `test_graphiti_search_with_embeddings_e2e` - Graphiti API mismatch
3. `test_e2e_embedding_cache` - Timing issue (passes in isolation)

### E2E Testing Strategy (Feature 16.7)
**Decision:** Vitest for component tests + Playwright for E2E flows

**Rationale:**
- Vitest: Fast unit/integration tests for React components
- Playwright: Cross-browser E2E user flows
- Together: Comprehensive frontend coverage

**Planned E2E Flows:**
1. Search with different modes (Hybrid, Vector, Graph, Memory)
2. Streaming answer display
3. Source card interaction
4. Session history navigation
5. Health dashboard monitoring

**Target Coverage:** 85%+ for critical user paths

---

**Document Version:** 1.1
**Last Updated:** 2025-10-28 (Sprint 16 Update)
**Owner:** Sprint 16 Team
**Status:** Active Development
