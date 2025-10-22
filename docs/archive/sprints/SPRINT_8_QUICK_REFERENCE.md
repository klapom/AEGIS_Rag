# Sprint 8 Quick Reference: Critical Path E2E Tests

**Version:** 1.0
**Date:** 2025-10-18
**Sprint Duration:** 4 weeks, 40 SP

---

## Sprint 8 at a Glance

**Goal:** Add 40 critical path E2E tests to increase production confidence from 75% → 95%

**Problem:** 96% of tests are mocked → Sprint 6 Neo4j failures proved mocks inadequate

**Solution:** Test 20 critical integration paths with real services (Ollama, Neo4j, Qdrant, Redis)

---

## Test Categories (40 tests, 40 SP)

### Category 1: Sprint 6 Neo4j Integration (P0 - CRITICAL)
**Tests:** 13, **SP:** 13
**Risk:** Proven CI failures
**Week:** 1

| Test ID | Test Name | SP | Services |
|---------|-----------|----|---------  |
| 6.1 | Query Cache Hit/Miss | 1 | Neo4j |
| 6.2 | Batch Query Executor | 1 | Neo4j |
| 6.3 | Query Builder Cypher | 1 | Neo4j |
| 6.4 | Optimization Performance | 1 | Neo4j |
| 6.5 | Community Detection (GDS) | 2 | Neo4j + GDS |
| 6.6 | Community Detection (NetworkX) | 1 | Neo4j + NetworkX |
| 6.7 | Community Labeling (LLM) | 1 | Neo4j + Ollama |
| 6.8 | Community Storage | 1 | Neo4j |
| 6.9 | Community Performance | 0.5 | Neo4j + GDS |
| 6.10 | Temporal Point-in-Time | 1 | Neo4j |
| 6.11 | Version History Pruning | 1 | Neo4j |
| 6.12 | Version Comparison | 0.5 | Neo4j |
| 6.13 | Temporal Query Performance | 0.5 | Neo4j |

---

### Category 2: Sprint 5 LightRAG Integration (P0 - CRITICAL)
**Tests:** 15, **SP:** 16
**Risk:** Zero E2E coverage
**Week:** 2

| Test ID | Test Name | SP | Services |
|---------|-----------|----|---------  |
| 5.1 | Entity Extraction E2E | 2 | Ollama + Neo4j |
| 5.2 | Entity Deduplication | 1 | Neo4j |
| 5.3 | Relationship Extraction | 1 | Ollama + Neo4j |
| 5.4 | Extraction Performance | 0.5 | Ollama + Neo4j |
| 5.5 | Multi-Document Graph | 2 | Ollama + Neo4j |
| 5.6 | Graph Merge Dedup | 1 | Neo4j |
| 5.7 | Transaction Timeout | 1 | Neo4j |
| 5.8 | Concurrent Graph Updates | 1 | Neo4j |
| 5.9 | Local Search E2E | 1 | Neo4j |
| 5.10 | Global Search E2E | 1 | Neo4j |
| 5.11 | Hybrid Local+Global | 1 | Neo4j |
| 5.12 | Complex Multi-Hop Query | 1 | Neo4j |
| 5.13 | Query Performance | 0.5 | Neo4j |
| 5.14 | Incremental Doc Addition | 1 | Ollama + Neo4j |
| 5.15 | Entity Update Propagation | 1 | Neo4j |

---

### Category 3: Sprint 3 Advanced Retrieval (P0 - CRITICAL)
**Tests:** 13, **SP:** 11
**Risk:** Never tested with real models
**Week:** 3

| Test ID | Test Name | SP | Services |
|---------|-----------|----|---------  |
| 3.1 | Cross-Encoder Loading | 1 | sentence-transformers |
| 3.2 | Reranking Accuracy | 1 | sentence-transformers |
| 3.3 | Batch Reranking Perf | 1 | sentence-transformers |
| 3.4 | CPU vs GPU Inference | 0.5 | sentence-transformers |
| 3.5 | Query Decomposition E2E | 1 | Ollama |
| 3.6 | Decomposition JSON Parse | 0.5 | Ollama |
| 3.7 | Decomposition Latency | 0.5 | Ollama |
| 3.8 | Filters + Hybrid Search | 1 | Qdrant + Ollama |
| 3.9 | Complex Filter Conditions | 0.5 | Qdrant |
| 3.10 | Filter Performance (10K) | 0.5 | Qdrant |
| 3.11 | RAGAS Faithfulness | 1 | Ollama |
| 3.12 | RAGAS Relevance | 1 | Ollama |
| 3.13 | RAGAS Performance | 1 | Ollama |

---

### Category 4: Sprint 2 & 4 Enhancements (P1 - HIGH)
**Tests:** 4, **SP:** 4
**Risk:** Medium - stress testing
**Week:** 4

| Test ID | Test Name | SP | Services |
|---------|-----------|----|---------  |
| 2.1 | Large-Scale Indexing (1K docs) | 1 | Qdrant + Ollama |
| 2.2 | Concurrent Index Updates | 1 | Qdrant |
| 2.5 | Corrupted Document Handling | 1 | Document Loaders |
| 4.4 | Long Conversation (20 turns) | 1 | Redis + LangGraph |

---

## Delivery Schedule

### Week 1: Category 1 (13 SP)
- **Focus:** Sprint 6 Neo4j Integration (highest risk)
- **Deliverable:** 13 E2E tests passing in CI
- **Key Validation:** Community detection, temporal queries, query optimization

### Week 2: Category 2 (16 SP)
- **Focus:** Sprint 5 LightRAG Integration
- **Deliverable:** 15 E2E tests passing in CI
- **Key Validation:** Entity extraction, graph construction, dual-level search

### Week 3: Category 3 (11 SP)
- **Focus:** Sprint 3 Advanced Retrieval
- **Deliverable:** 13 E2E tests passing in CI
- **Key Validation:** Cross-encoder, RAGAS, query decomposition

### Week 4: Category 4 (4 SP) + Buffer
- **Focus:** Sprint 2 & 4 stress testing
- **Deliverable:** 4 E2E tests + refinements
- **Key Validation:** Scale, edge cases, long conversations

---

## Test Template

```python
# tests/integration/sprint8/test_<feature>_e2e.py

import pytest

@pytest.mark.integration
@pytest.mark.neo4j  # or @pytest.mark.ollama, @pytest.mark.qdrant
@pytest.mark.sprint8
async def test_<feature>_e2e(<fixtures>):
    """Test X.Y: <Feature Name>

    Services: <Service1> (real), <Service2> (real)
    Flow: <Step1> → <Step2> → <Step3>
    Validates: <What it validates>
    Time: ~<Xseconds>
    Story Points: <Y> SP
    """
    # Setup
    <initialize components>

    # Execute
    <perform action>

    # Verify
    assert <condition>, "<failure message>"

    # Cleanup
    <cleanup resources>
```

---

## Running Tests

### Local Development

```bash
# Start services
docker compose up -d

# Run all Sprint 8 tests
pytest tests/integration/sprint8/ -v -m sprint8

# Run specific category
pytest tests/integration/sprint8/ -v -m "sprint8 and neo4j"

# Run single test
pytest tests/integration/sprint8/test_neo4j_query_optimization_e2e.py::test_query_cache_hit_miss_validation -v
```

### CI/CD

```bash
# CI automatically runs all Sprint 8 tests
# Configured in: .github/workflows/sprint8-e2e-tests.yml

# Services configured:
# - Redis (6379)
# - Qdrant (6333)
# - Neo4j (7687)
# - Ollama (11434)

# Test execution: <30 minutes
# Timeout: 45 minutes (buffer)
```

---

## Success Criteria

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Tests Added** | 40 tests | `pytest --collect-only -m sprint8 | grep "test_"` |
| **All Passing** | 100% (40/40) | `pytest tests/integration/sprint8/ -v` |
| **Execution Time** | <30 min | `pytest --durations=0` |
| **Code Coverage** | 85%+ | `pytest --cov=src --cov-report=term-missing` |
| **CI Success** | 100% (no flaky tests) | GitHub Actions dashboard |

---

## Common Issues & Solutions

### Issue 1: Neo4j Timeout in CI
**Symptom:** `Neo4j not available: Connection refused`

**Solution:**
```yaml
# Increase health check start period in .github/workflows/sprint8-e2e-tests.yml
options: >-
  --health-start-period 60s  # Was 30s
  --health-retries 20        # Was 10
```

---

### Issue 2: Ollama Model Not Found
**Symptom:** `Model 'llama3.2:8b' not available`

**Solution:**
```bash
# In CI workflow, ensure models pulled before tests
- name: Install Ollama
  run: |
    ollama pull llama3.2:8b
    ollama pull nomic-embed-text
    # Wait for models to be ready
    sleep 10
```

---

### Issue 3: Test Timeout
**Symptom:** `Test timeout after 60s`

**Solution:**
```python
# Increase timeout for slow tests
@pytest.mark.timeout(300)  # 5 minutes for large graph tests
async def test_large_graph_construction():
    ...
```

---

### Issue 4: Flaky Test (Intermittent Failures)
**Symptom:** Test passes locally, fails in CI

**Solution:**
```python
# Add retry logic with tenacity
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
async def test_with_retry():
    # Test code that may have transient failures
    ...
```

---

## Service Health Checks

### Before Running Tests

```bash
# Check all services
docker compose ps

# Expected output:
# NAME              STATE    HEALTH
# aegis-redis       Up       healthy
# aegis-qdrant      Up       healthy
# aegis-neo4j       Up       healthy
# aegis-ollama      Up       healthy

# Manual health checks
curl http://localhost:6333/health        # Qdrant
redis-cli ping                           # Redis
curl http://localhost:7474               # Neo4j
curl http://localhost:11434/api/tags     # Ollama
```

---

## Debugging Failed Tests

### Step 1: Check Service Logs

```bash
# View logs for specific service
docker compose logs neo4j -f
docker compose logs qdrant -f
docker compose logs ollama -f
```

### Step 2: Run Test in Isolation

```bash
# Run single failing test with verbose output
pytest tests/integration/sprint8/test_failing.py::test_specific -vvs

# Options:
# -vv: Very verbose (shows all assertions)
# -s: Show print statements
# --log-cli-level=DEBUG: Show debug logs
```

### Step 3: Inspect Service State

```python
# Add to test for debugging
import pdb; pdb.set_trace()  # Python debugger

# Or use pytest fixtures to inspect state
async def test_debug(neo4j_driver):
    # Run query to check Neo4j state
    result = neo4j_driver.execute_query("MATCH (n) RETURN count(n)")
    print(f"Node count: {result}")
```

---

## Contacts & Resources

**Sprint 8 Lead:** <test-engineer@example.com>
**DevOps Support:** <devops@example.com>
**QA Validation:** <qa@example.com>

**Documents:**
- Full Analysis: `docs/SPRINT_8_CRITICAL_PATH_ANALYSIS.md`
- Executive Summary: `docs/SPRINT_8_EXECUTIVE_SUMMARY.md`
- ADR-014: `docs/adr/ADR-014-e2e-integration-testing.md`

**GitHub:**
- Project Board: `https://github.com/org/aegis-rag/projects/sprint-8`
- Issues: `https://github.com/org/aegis-rag/issues?label=sprint-8`

**Slack:**
- Channel: `#sprint-8-e2e-tests`
- Daily Standup: 9:00 AM CET

---

## Daily Checklist

### Developer Daily Tasks
- [ ] Pull latest `sprint-8` branch
- [ ] Start Docker Compose services
- [ ] Verify service health
- [ ] Implement 2-3 tests (5 SP/week)
- [ ] Run tests locally (verify passing)
- [ ] Commit + push (trigger CI)
- [ ] Verify CI passing
- [ ] Update Sprint 8 project board

### Team Daily Standup (9:00 AM CET)
- What did I complete yesterday?
- What am I working on today?
- Any blockers?
- Service health issues?

---

## Sprint 8 Burndown Target

| Week | Completed Tests | Completed SP | Remaining Tests | Remaining SP |
|------|----------------|--------------|-----------------|--------------|
| 0 (Start) | 0 | 0 | 40 | 40 |
| 1 (End) | 13 | 13 | 27 | 27 |
| 2 (End) | 28 | 29 | 12 | 11 |
| 3 (End) | 41 | 40 | -1 | 0 |
| 4 (End) | 40 | 40 | 0 | 0 |

**Note:** Week 3 shows 41 tests because Category 3 has 13 tests (not 12)

---

## Definition of Done (Per Test)

- [ ] Test specification documented (docstring with services, flow, validation, time, SP)
- [ ] Test implemented with real services (no mocks)
- [ ] Test passes locally on developer machine
- [ ] Test passes in CI (GitHub Actions)
- [ ] Test execution time reasonable (<60s, or justified if longer)
- [ ] Test cleanup verified (no data leaks, no side effects)
- [ ] Code reviewed by team member
- [ ] PR merged to `sprint-8` branch

---

## Sprint 8 Completion Checklist

- [ ] All 40 E2E tests passing in CI (100% pass rate)
- [ ] Code coverage 85%+ on critical paths
- [ ] CI execution time <30 minutes
- [ ] No flaky tests (100% reliability over 10 runs)
- [ ] Documentation updated (Sprint 8 summary, test guide)
- [ ] Risk matrix updated (all P0 risks mitigated)
- [ ] Sprint 8 demo prepared (show E2E tests in action)
- [ ] Sprint 8 retrospective scheduled
- [ ] Merge `sprint-8` → `main`

---

**End of Quick Reference**

This document is a living reference - update as needed during Sprint 8.
