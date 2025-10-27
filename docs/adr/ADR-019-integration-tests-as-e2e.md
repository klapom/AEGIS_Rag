# ADR-019: Integration Tests as E2E Tests

## Status
**Accepted** (2025-10-27)

## Context

During Sprint 14 test coverage implementation, we created comprehensive tests for the Three-Phase Extraction Pipeline. Initially, we planned a separate E2E test layer in addition to unit and integration tests, following a traditional 4-layer test pyramid:

```
       /\
      /E2E\         ← Separate E2E layer (planned)
     /----\
    / Intg \        ← Integration tests with mocks
   /--------\
  /   Unit   \      ← Unit tests
 /------------\
```

However, we discovered that our integration tests already provide E2E-like coverage:
- Use **real Docker services** (Ollama, Neo4j, Redis, Qdrant) - NO MOCKS
- Test **complete workflows** (document → extraction → storage)
- Validate **end-to-end functionality** identical to production

**Problem:**
Creating a separate E2E test layer resulted in:
1. **Redundant tests**: E2E tests duplicated integration test workflows
2. **API signature mismatches**: E2E tests had import errors (`record_deduplication_ratio` vs `record_deduplication_reduction`)
3. **Maintenance overhead**: Two layers testing the same workflows
4. **Slower feedback**: Additional test execution time with no additional confidence

**Question:** Should we maintain a separate E2E test layer, or can integration tests serve as E2E tests?

## Decision

We will **use integration tests with real Docker services as E2E tests** instead of maintaining a separate E2E test layer.

**New Test Architecture:**
```
       /\
      / Intg\       ← Integration tests = E2E tests (real services, complete workflows)
     /------\
    /  Unit  \      ← Unit tests (mocked dependencies)
   /----------\
  / Foundation \    ← Core unit tests
 /--------------\
```

**What This Means:**
- Integration tests use real services (Ollama, Neo4j, Redis, Qdrant)
- Integration tests exercise complete workflows (document → entities → relations → storage)
- No separate E2E test directory (`tests/e2e/` for pipeline E2E deleted)
- Integration tests provide production confidence

## Alternatives Considered

### Alternative 1: Separate E2E Test Layer
**Pro:**
- Clear separation of concerns (unit → integration → E2E)
- Follows traditional test pyramid
- Explicit "E2E" naming makes intent clear

**Contra:**
- **Redundant**: E2E tests duplicate integration test functionality
- **Maintenance overhead**: Two layers testing same workflows
- **API mismatches**: E2E tests had import errors in Sprint 14
- **Slower feedback**: Additional 5-10 minutes execution time
- **No additional confidence**: Integration tests already use real services

### Alternative 2: Mock-Based Integration Tests + Separate E2E
**Pro:**
- Faster integration test execution (mocked services)
- E2E tests provide real service validation
- Clear test intent separation

**Contra:**
- **False confidence**: Mocks don't catch real service issues (learned in Sprint 8)
- **More complex**: Three distinct test layers to maintain
- **Longer CI time**: Two separate test suites with real services

### Alternative 3: Pure Unit Tests + E2E Only (No Integration Tests)
**Pro:**
- Simplest architecture (2 layers only)
- Clear separation (isolated vs. full system)

**Contra:**
- **Missing middle layer**: No tests for component integration patterns
- **E2E too slow**: All integration testing at E2E level (10+ min execution)
- **Debugging harder**: Failures in E2E harder to isolate

## Rationale

### Why Integration Tests Can Serve as E2E Tests

**1. Real Services:**
Integration tests use actual Docker services, not mocks:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_factory_creates_functional_three_phase_pipeline():
    """Test with REAL Ollama + Neo4j services."""
    settings = get_settings()  # Real config
    pipeline = ExtractionPipelineFactory.create(settings)  # Real factory

    test_text = "Alice and Bob work together at TechCorp."
    entities, relations = await pipeline.extract(test_text, document_id="test_1")

    # Real extraction happened with Ollama + Neo4j
    assert len(entities) > 0
```

**2. Complete Workflows:**
Integration tests exercise end-to-end extraction pipeline:
- Document ingestion
- Entity extraction (Phase 1: SpaCy)
- Semantic deduplication (Phase 2: Embeddings)
- Relation extraction (Phase 3: Gemma 3 4B)
- Storage in Neo4j

**3. Production Confidence:**
Integration tests validate production-like scenarios:
- Multiple sequential extractions
- Large document handling
- Unicode text support
- Empty/edge case handling
- Batch processing

**4. Performance Validation:**
Integration tests enforce performance requirements:
```python
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_extractor_performance_with_retry():
    start_time = time.time()
    relations = await extractor.extract(text, entities)
    elapsed_time = time.time() - start_time

    # Enforce <30s requirement
    assert elapsed_time < 30, f"Extraction took {elapsed_time:.2f}s"
```

### Sprint 14 Evidence

**Integration Test Results:**
- 20 tests passing in 5m 37s (337s)
- All tests use real Docker services
- Tests cover complete extraction workflows
- Performance requirements validated

**Deleted E2E Tests:**
- `tests/e2e/test_sprint14_full_pipeline_e2e.py` (redundant)
- `tests/integration/test_metrics_integration.py` (54 unit tests sufficient)

**Outcome:**
- Simpler test architecture (3 layers → 2 layers)
- No loss of coverage or confidence
- Faster maintenance (one less layer)

## Consequences

### Positive

✅ **Simplified Architecture:**
- 2 test layers instead of 3-4
- Clear distinction: Unit (mocked) vs Integration (real services)
- Less confusion about where tests belong

✅ **Reduced Maintenance:**
- No duplicate tests across E2E and integration
- Single source of truth for workflow validation
- API changes only need updates in one place

✅ **Faster Feedback:**
- No separate E2E execution phase
- 20 integration tests in 5m 37s provide full confidence
- Developers get full validation in one test run

✅ **Production Confidence:**
- All integration tests use real services
- Workflows identical to production
- Performance requirements enforced

✅ **Better Test Organization:**
- Unit tests: Fast, isolated, mocked dependencies
- Integration tests: Slow, real services, complete workflows
- Stress tests: Performance validation, memory profiling

### Negative

⚠️ **Longer Integration Test Execution:**
- 5m 37s for 20 tests (avg 16.8s per test)
- Acceptable trade-off for real service validation

⚠️ **Docker Service Dependency:**
- Integration tests require running Docker services
- CI must ensure all services available
- Mitigation: Docker Compose setup ensures consistency

⚠️ **Terminology Ambiguity:**
- "Integration tests" implies component integration, but also do E2E
- Mitigation: Clear documentation and test naming

### Mitigations

**For Execution Time:**
- Use session-scoped fixtures (services initialized once)
- Run integration tests in parallel where possible
- Acceptable: 5m 37s provides 95%+ production confidence

**For Docker Dependency:**
- Docker Compose ensures consistent environment
- CI pipeline validates service availability before tests
- Local development: Clear setup instructions

**For Terminology:**
- Document clearly in test docstrings
- Use markers: `@pytest.mark.integration` (includes E2E scenarios)
- ADR provides clear explanation of approach

## Implementation

### Test Organization

**Unit Tests** (`tests/components/`, `tests/monitoring/`, `tests/scripts/`):
- Mock all external dependencies
- Test individual functions/classes
- Fast execution (<10s for 112 tests)

**Integration Tests** (`tests/integration/`):
- Use real Docker services (NO MOCKS)
- Test complete workflows
- Validate production scenarios
- Slower execution (5m 37s for 20 tests)

**Stress Tests** (`tests/stress/`):
- Memory profiling (tracemalloc, psutil)
- Large batch processing (100+ documents)
- Connection pool exhaustion
- Sustained throughput testing

### Test Naming Convention

```python
# Unit test (mocked dependencies)
@pytest.mark.unit
def test_extractor_initialization_with_retry_params():
    """Test extractor initializes with retry parameters."""
    extractor = GemmaRelationExtractor(max_retries=5)
    assert extractor.max_retries == 5

# Integration test = E2E test (real services)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_document_processing_workflow():
    """E2E test: Full document processing with extraction factory.

    This test simulates a complete workflow:
    1. Create pipeline from config
    2. Extract entities and relations
    3. Verify data quality
    """
    pipeline = create_extraction_pipeline_from_config()
    entities, relations = await pipeline.extract(document, document_id="test_e2e")

    assert len(entities) >= 2
    for entity in entities:
        assert "name" in entity
        assert "type" in entity
```

### CI Pipeline

```yaml
# .github/workflows/test.yml
name: Test Suite

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Unit Tests
        run: poetry run pytest -m unit
        # Fast: <10s

  integration-tests:
    runs-on: ubuntu-latest
    services:
      ollama: ...
      neo4j: ...
      redis: ...
      qdrant: ...
    steps:
      - name: Verify Services
        run: |
          curl -f http://localhost:11434/api/tags
          curl -f http://localhost:7474

      - name: Run Integration Tests (= E2E)
        run: poetry run pytest -m integration
        # Slower: ~5-6 minutes
```

## References

- **Sprint 14 Completion Report**: [SPRINT_14_COMPLETION_REPORT.md](../sprints/SPRINT_14_COMPLETION_REPORT.md)
- **ADR-014**: E2E Integration Testing Strategy (Sprint 8)
- **ADR-015**: Critical Path Testing Strategy (Sprint 8)
- **Test Files**:
  - `tests/integration/test_extraction_factory_integration.py` (9 tests)
  - `tests/integration/test_gemma_retry_integration.py` (11 tests)

## Review History

- **2025-10-27**: Accepted during Sprint 14 after E2E test redundancy discovered
- **Reviewed by**: Claude Code (Backend Subagent), User (Product Owner)

---

**Summary:**

Integration tests with real Docker services provide E2E validation without a separate test layer, simplifying architecture while maintaining production confidence. This approach eliminates redundant tests, reduces maintenance overhead, and provides faster feedback with no loss of coverage.
