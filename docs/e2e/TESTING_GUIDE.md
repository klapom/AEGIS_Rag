# E2E Testing Guide for AEGIS RAG

Quick reference for running, debugging, and maintaining E2E tests.

## Quick Start

```bash
# Run all E2E tests
poetry run pytest tests/e2e/ -v

# Run specific test
poetry run pytest tests/e2e/test_e2e_health_monitoring.py -v

# Run with visual debugging
HEADED=1 pytest tests/e2e/test_e2e_session_management.py -v
```

## Service Requirements

Before running E2E tests, ensure these services are running:

```bash
# Start all services
docker-compose -f docker-compose.dgx-spark.yml up -d

# Verify services
curl http://localhost:8000/health           # Backend
curl http://localhost:5179                  # Frontend
curl http://localhost:6333                  # Qdrant
neo4j://localhost:7687                      # Neo4j
redis-cli ping                              # Redis
```

## Test Files Organization

```
tests/e2e/
├── conftest.py                              # Shared fixtures
├── fixtures/                                # Test data fixtures
│   ├── sample_documents.py
│   ├── graph_data.py
│   └── training_datasets.py
├── utils/                                   # Utilities
│   └── cleanup.py
└── test_e2e_*.py                            # Test files (12 total)

Currently Active Tests:
├── test_e2e_health_monitoring.py            ✅ 5+ tests
├── test_e2e_chat_streaming_and_citations.py ✅ 10+ tests
├── test_e2e_session_management.py          ✅ 8 tests
├── test_e2e_document_ingestion_workflow.py  ✅ 1 test
├── test_e2e_graph_exploration_workflow.py   ✅ 1 test
├── test_e2e_sprint49_features.py           ✅ 2 tests
├── test_e2e_community_detection_workflow.py ✅ 5+ tests
├── test_e2e_cost_monitoring_workflow.py    ✅ 4+ tests
├── test_e2e_indexing_pipeline_monitoring.py ✅ 3+ tests
├── test_e2e_hybrid_search_quality.py       ✅ 5+ tests
├── test_e2e_upload_page_domain_classification.py ✅ 1 test
└── test_e2e_domain_creation_workflow.py    ✅ 3+ tests

Archive (Legacy):
└── archive/                                 # Deprecated tests
```

## Running Tests

### Run All Tests
```bash
poetry run pytest tests/e2e/ -v
```

### Run Specific File
```bash
poetry run pytest tests/e2e/test_e2e_health_monitoring.py -v
```

### Run Specific Test
```bash
poetry run pytest tests/e2e/test_e2e_health_monitoring.py::TestHealthMonitoring::test_health_dashboard_loads -v
```

### Run by Marker
```bash
# Run all E2E tests (same as without marker)
poetry run pytest tests/e2e/ -m e2e -v

# Run slow tests only
poetry run pytest tests/e2e/ -m slow -v

# Skip slow tests
poetry run pytest tests/e2e/ -m "not slow" -v

# Run Sprint 49 feature tests
poetry run pytest tests/e2e/ -m sprint49 -v
```

## Debugging

### Headed Mode (See Browser)
```bash
HEADED=1 pytest tests/e2e/test_e2e_session_management.py -v
```

### Slow Motion (0.5s delay between actions)
```bash
SLOWMO=500 pytest tests/e2e/test_e2e_session_management.py -v
```

### Combined
```bash
HEADED=1 SLOWMO=500 pytest tests/e2e/test_e2e_health_monitoring.py::TestHealthMonitoring::test_health_dashboard_loads -v
```

### View Screenshots
Failures automatically capture screenshots:
```bash
ls -la tests/e2e/screenshots/
# Shows: test_name_YYYYMMDD_HHMMSS.png
```

### Print Debug Info
```python
# In your test:
await asyncio.sleep(5)  # Pause to inspect
print(f"Page content: {await page.content()[:500]}")
print(f"Page URL: {page.url}")
```

### Dump Page HTML
```python
# Debug element not found
html = await page.content()
print(f"Looking for element in:\n{html}")

# Or save to file
with open("debug.html", "w") as f:
    f.write(html)
```

## Common Patterns

### Waiting for Elements
```python
# Wait with timeout
await expect(element).to_be_visible(timeout=5000)

# Wait for text
await expect(page.get_by_text("Success")).to_be_visible()

# Wait for file input (hidden but attachable)
await expect(page.locator('input[type="file"]')).to_be_attached()
```

### Finding Elements (Sprint 51 Compatible)
```python
# Primary: Use data-testid
element = page.locator('[data-testid="my-button"]')

# Fallback 1: By text
element = page.get_by_text(re.compile(r"click me", re.I))

# Fallback 2: By role
element = page.get_by_role("button", name="Click Me")

# Fallback 3: CSS selector
element = page.locator('.my-button-class')
```

### File Upload
```python
# Sprint 51 pattern:
file_input = page.locator('input[type="file"]')
if await file_input.count() == 0:
    file_input = page.locator('[data-testid="file-input"]')

await file_input.set_input_files(["/path/to/file1.pdf", "/path/to/file2.pdf"])
```

### Admin Navigation
```python
# Sprint 51: Direct URL navigation works
await page.goto(f"{base_url}/admin/upload")
await page.goto(f"{base_url}/admin/graph")
await page.goto(f"{base_url}/admin/health")
```

### Neo4j Connection
```python
# Always use get_secret_value() for SecretStr password
driver = AsyncGraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
)
async with driver.session() as session:
    result = await session.run("MATCH (n) RETURN count(n) as count")
    record = await result.single()
```

### Async/Await Pattern
```python
@pytest.mark.asyncio
async def test_something(self, page: Page):
    """All E2E tests are async."""
    await page.goto("http://localhost:5179")
    await asyncio.sleep(1)  # Wait for page load
    element = page.locator("h1")
    await expect(element).to_be_visible()
```

## Sprint 51 Changes

### What Changed
1. **Admin Navigation**: Centralized bar at top of `/admin` dashboard
2. **Direct URLs**: All admin pages accessible via clean URLs (`/admin/upload`, `/admin/graph`, etc.)
3. **Domain Section**: Moved to bottom, collapsed by default
4. **Phase Display**: Dynamic phase indicator with streaming
5. **File Inputs**: Standardized selector pattern

### How to Update Tests
When frontend changes:
1. Identify failing selector
2. Use browser DevTools to find new selector
3. Add fallback strategies
4. Test in isolation first, then full suite
5. Document change

## Creating New E2E Tests

### Minimal Test Template
```python
"""End-to-End Test: Feature Name.

This test validates:
1. Step 1
2. Step 2
3. Step 3
"""

import asyncio
import pytest
from playwright.async_api import Page, expect

@pytest.mark.e2e
class TestFeature:
    """Feature tests."""

    @pytest.mark.asyncio
    async def test_my_feature(self, page: Page, base_url: str):
        """Test description."""
        # Step 1: Navigate
        await page.goto(f"{base_url}/some-page")
        await page.wait_for_load_state("networkidle")

        # Step 2: Interact
        button = page.locator('[data-testid="my-button"]')
        await expect(button).to_be_visible()
        await button.click()

        # Step 3: Verify
        result = page.get_by_text("Success")
        await expect(result).to_be_visible()

        print("✅ Test passed")
```

### Best Practices
1. Use data-testid attributes
2. Add clear step comments
3. Use descriptive assertions
4. Handle flakiness with waits
5. Print progress for debugging
6. Keep tests independent
7. Clean up after tests
8. Use async/await consistently

## Troubleshooting

### Test Timeout
```python
# Increase timeout for slow operations
await page.wait_for_load_state("networkidle", timeout=30000)
await expect(element).to_be_visible(timeout=10000)
```

### Element Not Found
```python
# Debug: Print page content
print(await page.content())

# Or save for inspection
with open("debug.html", "w") as f:
    f.write(await page.content())
```

### Login Fails
```python
# Check credentials
username = page.locator('[data-testid="username-input"]')
password = page.locator('[data-testid="password-input"]')

# Verify fields exist
assert await username.count() > 0, "Username field not found"
```

### Async Issues
```python
# Ensure test is async
@pytest.mark.asyncio  # Required
async def test_name(self, ...):
    pass

# Use asyncio.sleep for waiting
await asyncio.sleep(1)  # Don't use time.sleep()
```

## CI/CD Integration

### Pre-Commit Checks
```bash
# Run before committing
pytest tests/e2e/ -v --tb=short
```

### GitHub Actions
E2E tests run on:
- Pull requests to main
- Merges to main
- Manual trigger

Results show in PR checks.

## Performance Notes

- **Typical Duration**: 5-10 minutes for full suite
- **Slowest Tests**: Graph exploration (~60s), document ingestion (~45s)
- **Fastest Tests**: Health monitoring (~5s per test)
- **Parallelization**: Not yet enabled (tests use shared state)

## Resources

- **Playwright Docs**: https://playwright.dev/python/docs/intro
- **Pytest Async**: https://pytest-asyncio.readthedocs.io/
- **AEGIS RAG Docs**: `/docs/`
- **Frontend Code**: `frontend/src/pages/` and `frontend/src/components/`

## Contact

For issues or questions:
1. Check this guide
2. Review test file docstrings
3. Check sprint documentation
4. Ask in team chat

---

**Last Updated**: December 18, 2025 (Sprint 51)
**Status**: All tests compatible with Sprint 51 UI changes
