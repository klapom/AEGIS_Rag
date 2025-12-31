# TD-047: Critical Path E2E Tests (Sprint 8)

**Status:** OPEN
**Priority:** HIGH
**Severity:** Production Confidence Gap
**Original Sprint:** Sprint 8
**Story Points:** 40 SP
**Created:** 2025-12-04

---

## Problem Statement

Sprint 8 was planned to deliver 40 E2E integration tests covering 26 critical paths, but was never fully executed. The project currently relies heavily on mocked unit tests, which provide false confidence - as evidenced by Sprint 6 CI failures where 432 mocked tests passed locally but 2/9 CI jobs failed.

**Current State:**
- Production Confidence: ~75% (target: 95%)
- Integration bugs: ~10/quarter (target: 2/quarter)
- CI debugging time: ~5 hours/week (target: 1 hour/week)

---

## Impact

### Risk Assessment
- **High Risk Paths (12):** ZERO current E2E coverage
- **Medium Risk Paths (8):** Partial coverage only
- **Lower Risk Paths (6):** Good coverage exists

### Business Impact
- Production incidents from untested integration paths
- Extended debugging time for CI failures
- False confidence from mocked tests

---

## Critical Paths Requiring Coverage

### High Risk (12 paths, Priority 1)
1. Community Detection (Neo4j + Ollama)
2. Cross-Encoder Reranking
3. RAGAS Evaluation with Ollama
4. LightRAG Entity Extraction
5. Temporal Queries (Graphiti)
6. Memory Consolidation (Redis -> Qdrant)
7. Graph Query Cache Invalidation
8. Batch Query Executor
9. Version Manager (10 versions)
10. PageRank Analytics
11. Query Templates (19 patterns)
12. Community Search Filter

### Medium Risk (8 paths, Priority 2)
13. Hybrid Search (Vector + BM25)
14. Document Ingestion Pipeline
15. Metadata Filtering
16. Query Decomposition
17. Graph Visualization Export
18. Dual-Level Search (Entities + Topics)
19. Reciprocal Rank Fusion
20. Adaptive Chunking

### Lower Risk (6 paths, Priority 3)
21. BM25 Search
22. Embedding Service
23. Qdrant Client Operations
24. Neo4j Client Wrapper
25. Redis Memory Manager
26. API Endpoints

---

## Solution

### Test Strategy (per ADR-015)

**NO MOCKS Policy:**
- All tests use real services (Redis, Qdrant, Neo4j, Ollama)
- Session-scoped fixtures for service reuse
- Cleanup between tests for isolation
- Acceptable trade-off: ~10 min execution time for 95% production confidence

**Test Distribution:**
- High Risk: 24 tests (2 tests per critical path)
- Medium Risk: 12 tests (1.5 tests per path)
- Lower Risk: 4 tests (validation only)
- **Total: 40 E2E tests**

### Implementation Tasks

```
tests/e2e/
├── test_community_detection_e2e.py      # High Risk #1
├── test_cross_encoder_e2e.py            # High Risk #2
├── test_ragas_evaluation_e2e.py         # High Risk #3
├── test_lightrag_extraction_e2e.py      # High Risk #4
├── test_temporal_queries_e2e.py         # High Risk #5
├── test_memory_consolidation_e2e.py     # High Risk #6
├── test_cache_invalidation_e2e.py       # High Risk #7
├── test_batch_executor_e2e.py           # High Risk #8
├── test_version_manager_e2e.py          # High Risk #9
├── test_pagerank_analytics_e2e.py       # High Risk #10
├── test_query_templates_e2e.py          # High Risk #11
├── test_community_search_e2e.py         # High Risk #12
├── test_hybrid_search_e2e.py            # Medium Risk #13
├── test_ingestion_pipeline_e2e.py       # Medium Risk #14
└── ...
```

### CI Pipeline Updates
- Ensure all services running before tests
- Add test execution time monitoring
- Create coverage report for critical paths

---

## Acceptance Criteria

- [ ] 40 E2E tests implemented and passing
- [ ] All 12 High Risk paths have E2E coverage
- [ ] Test execution time <10 minutes
- [ ] CI pipeline validates service availability before tests
- [ ] Coverage report shows 95%+ critical path coverage
- [ ] No mocked tests for critical integration paths
- [ ] Sprint completion report created

---

## Estimated Effort

**Story Points:** 40 SP

**Breakdown:**
- High Risk tests (24 tests): 24 SP
- Medium Risk tests (12 tests): 10 SP
- Lower Risk tests (4 tests): 2 SP
- CI pipeline updates: 2 SP
- Documentation: 2 SP

**Timeline:**
- Sequential: 4 weeks (1 developer)
- Parallel: 1 week (4 subagents)

---

## References

- [SPRINT_PLAN.md - Sprint 8](../sprints/SPRINT_PLAN.md#sprint-8-critical-path-e2e-testing)
- [ADR-015: Critical Path Testing Strategy](../adr/ADR-015-critical-path-testing.md)
- [ADR-014: E2E Integration Testing Strategy](../adr/ADR-014-e2e-integration-testing.md)

---

## Target Sprint

**Recommended:** Sprint 37 (dedicated E2E sprint)

---

**Last Updated:** 2025-12-04
