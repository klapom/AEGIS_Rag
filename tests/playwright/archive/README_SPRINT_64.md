# Sprint 64: E2E Test Suite

This directory contains comprehensive E2E tests for Sprint 64 critical features.

---

## Test Files

### 1. VLM Image Search Tests
**File:** `test_vlm_image_search.py`
**Tests:** 3 E2E tests
**Duration:** ~10 minutes
**SP:** 1.5

Tests VLM image description integration and hybrid search functionality.

**What it tests:**
- PDF indexing with embedded images
- VLM image description generation
- BBox matching to sections
- Qdrant metadata storage
- Hybrid search with VLM content

**Run:** `poetry run pytest test_vlm_image_search.py -v`

### 2. Domain Training Tests
**File:** `test_domain_training.py`
**Tests:** 6 E2E/Integration tests
**Duration:** ~3 minutes
**SP:** 1.5

Tests domain training UI validation and data persistence.

**What it tests:**
- Frontend 5-sample minimum validation
- Error message clarity
- DSPy training with real metrics
- Neo4j domain persistence
- Transactional creation (no orphans)
- Training failure rollback

**Run:** `poetry run pytest test_domain_training.py -v`

### 3. Domain Persistence Tests
**File:** `test_domain_persistence.py` (in `../integration/`)
**Tests:** 6 integration tests
**Duration:** ~6 minutes
**SP:** Included in 1.5

Tests domain creation, persistence, and transaction handling.

**What it tests:**
- Validation failure prevents creation
- Successful training persists domain
- Exception handling and rollback
- Unique constraint enforcement
- All metrics stored correctly
- Domain updates and versioning

**Run:** `poetry run pytest ../integration/test_domain_persistence.py -v`

---

## Quick Commands

### Run All Sprint 64 Tests
```bash
poetry run pytest test_vlm_image_search.py test_domain_training.py ../integration/test_domain_persistence.py -v
```

### Run Only Quick Tests (No VLM)
```bash
poetry run pytest test_domain_training.py ../integration/test_domain_persistence.py -v
```

### Run With Marker
```bash
poetry run pytest . -m sprint64 -v
```

### Debug Mode (See Browser)
```bash
HEADED=1 poetry run pytest test_domain_training.py::TestDomainTraining::test_domain_validation_min_samples -v
```

### Slow Motion (500ms per action)
```bash
SLOWMO=500 poetry run pytest test_vlm_image_search.py -v
```

---

## Documentation

### Comprehensive Guides
- **[SPRINT_64_E2E_TESTS.md](SPRINT_64_E2E_TESTS.md)** - Complete testing guide with all details
- **[SPRINT_64_E2E_SUMMARY.md](SPRINT_64_E2E_SUMMARY.md)** - Implementation summary and status
- **[../../TESTING_SPRINT_64.md](../../TESTING_SPRINT_64.md)** - Quick start guide

### Feature Plans
- **[../../docs/sprints/SPRINT_64_PLAN.md](../../docs/sprints/SPRINT_64_PLAN.md)** - Sprint 64 requirements and implementation

---

## Test Coverage

| Feature | Tests | Coverage |
|---------|-------|----------|
| VLM Integration | 3 E2E | Complete flow from indexing to search |
| Frontend Validation | 3 E2E | Min samples, errors, cancel |
| Data Persistence | 6 Integration | Creation, rollback, updates |
| **Total** | **15** | **All critical paths** |

---

## Prerequisites

### Services
- Frontend: http://localhost:5179
- API Backend: http://localhost:8000
- Qdrant: localhost:6333
- Neo4j: bolt://localhost:7687
- Redis: localhost:6379

### Installation
```bash
# Install test dependencies
poetry install --with dev

# Install Playwright browsers (if needed)
poetry run playwright install chromium

# Verify setup
poetry run pytest --collect-only test_vlm_image_search.py
# Should show: 3 tests collected
```

---

## Test Patterns

### VLM Test Pattern
```python
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_vlm_feature():
    # 1. Setup test data
    # 2. Index document
    # 3. Wait for VLM processing
    # 4. Query for VLM content
    # 5. Verify results
```

### Domain Training Pattern
```python
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_domain_feature():
    # 1. Navigate to page
    # 2. Fill form
    # 3. Upload data
    # 4. Verify UI feedback
    # 5. Validate database state
```

### Integration Pattern
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_domain_persistence():
    # 1. Perform action
    # 2. Verify in Neo4j
    # 3. Cleanup
```

---

## Troubleshooting

### Tests Timeout
- Increase timeout: `await expect(...).to_be_visible(timeout=600000)`
- Check service logs: `docker logs qdrant`
- Use smaller test data: `self.create_test_dataset(5)`

### Browser Not Launching
```bash
poetry run playwright install chromium
poetry run playwright install-deps
```

### Import Errors
- Check service is running
- Tests will skip if service unavailable
- Check error message for specifics

### Flaky Tests
- Run with `pytest -v` to see full output
- Add retry: `@pytest.mark.flaky(reruns=3)`
- Increase timeout for slow systems

---

## Fixtures

### Page (E2E)
```python
async def test_example(page: Page):
    await page.goto("http://localhost:5179/admin")
    # Use page for browser automation
```

### Neo4j Driver (Integration)
```python
async def test_persistence(neo4j_driver):
    async with neo4j_driver.session() as session:
        result = await session.run(query)
```

### Qdrant Client (Verification)
```python
async def test_qdrant(qdrant_client):
    points = await qdrant_client.scroll(collection)
```

### Base URL
```python
async def test_navigation(page: Page, base_url: str):
    await page.goto(f"{base_url}/admin/indexing")
```

---

## Test Markers

### Available Markers
```bash
# E2E tests
pytest -m e2e

# Integration tests
pytest -m integration

# Sprint 64 specific
pytest -m sprint64

# Exclude slow tests
pytest -m "not slow"

# Combined
pytest -m "sprint64 and not slow"
```

---

## Performance Metrics

| Test | Type | Duration | Notes |
|------|------|----------|-------|
| VLM Integration | E2E | ~10 min | Includes VLM processing |
| Domain Validation | E2E | ~30 sec | Quick UI check |
| Domain Training | E2E | ~2 min | Real DSPy with 10 samples |
| Domain Persistence | Integration | ~1 min | Database operations |

---

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run Sprint 64 Tests
  run: poetry run pytest tests/e2e/test_*.py tests/integration/test_domain_*.py -v
  timeout-minutes: 30
```

### Coverage Report
```bash
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Acceptance Criteria

### Feature 64.1: VLM Integration
- [x] VLM descriptions in chunks with `[Image Description]:` prefix
- [x] Chunks have image_annotations array
- [x] Qdrant stores metadata
- [x] Hybrid search finds VLM content

### Feature 64.2: Domain Training
- [x] Frontend validates 5 samples minimum
- [x] Error messages clear
- [x] No orphaned domains
- [x] Realistic F1 scores (0.4-0.95)

---

## Next Steps

1. Run tests against your local services
2. Monitor test execution time
3. Add performance benchmarks
4. Integrate with CI/CD pipeline
5. Generate coverage reports

---

## Support

For issues:
1. Check logs: `poetry run pytest test_*.py -v -s`
2. Debug mode: `HEADED=1 poetry run pytest test_*.py -v`
3. See [SPRINT_64_E2E_TESTS.md](SPRINT_64_E2E_TESTS.md) for detailed troubleshooting

---

**Last Updated:** 2025-12-24
**Status:** Ready for testing
**Tests:** 15 collected, all passing syntax validation
