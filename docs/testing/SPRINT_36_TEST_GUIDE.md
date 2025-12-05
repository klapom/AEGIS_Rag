# Sprint 36 Test Guide - Quick Reference

**Last Updated:** 2025-12-05
**Test Suite:** 109 unit/integration tests
**Status:** COMPLETE

---

## Quick Start

### Run All Tests
```bash
# Unit tests only (fast, no external dependencies)
pytest tests/unit/ -v

# Skip cloud tests (CI/CD default)
pytest tests/ -m "not cloud" --tb=short

# Run specific test file
pytest tests/unit/components/llm_proxy/test_vlm_factory.py -v
```

### Run Cloud Tests
```bash
# Requires: ALIBABA_CLOUD_API_KEY env var
pytest tests/integration/test_cloud_llm_vlm.py -m cloud -v

# Show skipped tests
pytest tests/integration/test_cloud_llm_vlm.py -m cloud -v -rs
```

### Generate Coverage Report
```bash
# Create HTML report
pytest tests/ --cov=src --cov-report=html --co cloud

# Check if >80% coverage
pytest tests/ --cov=src --cov-fail-under=80
```

---

## Test Files Overview

| File | Tests | Purpose |
|------|-------|---------|
| `test_vlm_factory.py` | 31 | VLM Factory pattern & backend switching |
| `test_ollama_vlm.py` | 33 | OllamaVLMClient local inference |
| `test_chunking_service.py` | 25 | Unified chunking service (all strategies) |
| `test_cloud_llm_vlm.py` | 20 | Cloud LLM/VLM integration (with graceful skipping) |

---

## Test Categories

### Unit Tests (89 tests)
Fast, isolated tests with mocked dependencies.

```bash
pytest tests/unit/ -v --tb=short
```

**VLM Factory (31 tests)**
- Backend enum validation
- Configuration priority (env > config > default)
- Factory function (explicit/config-driven)
- Singleton pattern (create, cache, close, reset)
- Error handling and recovery

**OllamaVLMClient (33 tests)**
- Initialization (base_url, model, timeout)
- Image description generation
- Base64 encoding verification
- Model availability checking
- Async context manager support
- HTTP error handling
- Edge cases (empty response, very long text)

**ChunkingService (25 tests)**
- All chunking strategies (adaptive, fixed, sentence, paragraph)
- Section metadata preservation
- Token counting and chunk ID generation
- Merge logic with multi-section tracking
- Singleton pattern and configuration

### Integration Tests (20 tests)
Tests with real or mocked external services.

```bash
# Skip cloud tests (default for CI/CD)
pytest tests/integration/ -m "not cloud" -v

# Run cloud tests (requires API key)
pytest tests/integration/test_cloud_llm_vlm.py -m cloud -v
```

**Cloud Integration Tests**
- DashScope VLM (initialization, API calls)
- Ollama VLM (local zero-cost inference)
- VLM Factory (backend switching)
- Cloud LLM Routing (Alibaba integration)
- Shared client (singleton, reconnection)
- Configuration (API keys, URLs, budgets)
- Error handling (invalid creds, timeouts, rate limits)

---

## Common Tasks

### Add New Test
```python
# tests/unit/components/llm_proxy/test_new_feature.py
import pytest
from unittest.mock import patch, AsyncMock

class TestNewFeature:
    """Tests for NewFeature."""

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operation."""
        # Arrange
        mock_client = AsyncMock()

        # Act
        result = await mock_client.some_method()

        # Assert
        assert result is not None
        mock_client.some_method.assert_called_once()
```

### Test with Environment Variables
```python
def test_with_env_var(self):
    """Test that respects environment variable."""
    with patch.dict(os.environ, {"MY_VAR": "value"}):
        result = get_config()
        assert result == "value"
```

### Test Async Code
```python
@pytest.mark.asyncio
async def test_async_function(self):
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Mock HTTP Requests
```python
import httpx

def test_http_request(self):
    """Test HTTP request."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}

    client = MyClient()
    client.http_client = AsyncMock()
    client.http_client.post = AsyncMock(return_value=mock_response)

    result = await client.do_something()
    assert result is not None
```

---

## Cloud Test Setup

### Prerequisites
```bash
# Set API key
export ALIBABA_CLOUD_API_KEY="sk-..."
# OR
export DASHSCOPE_API_KEY="sk-..."

# Optional: Set base URL
export ALIBABA_CLOUD_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# Optional: Set budget
export MONTHLY_BUDGET_ALIBABA_CLOUD="10.0"  # USD
```

### Running Cloud Tests
```bash
# Run with API key
pytest tests/integration/test_cloud_llm_vlm.py::TestCloudVLMDashScope -v -m cloud

# Skip if key missing (graceful)
pytest tests/integration/test_cloud_llm_vlm.py -v  # Tests are skipped automatically

# View skipped tests
pytest tests/integration/test_cloud_llm_vlm.py -v -rs
```

### Cost Awareness
- Cloud tests make **real API calls** (may incur costs)
- Set `MONTHLY_BUDGET_ALIBABA_CLOUD` to limit spending
- Use test data (1x1 PNG image) to minimize costs
- Run in isolated environment with cost alerts enabled

---

## Debugging Failed Tests

### View Full Error Output
```bash
pytest tests/unit/test_file.py::TestClass::test_method -vv --tb=long
```

### Drop into Debugger
```python
def test_something():
    """Test with debugger."""
    import pdb; pdb.set_trace()  # Pause here
    result = my_function()
    assert result
```

### Use Logging
```python
import structlog

def test_with_logging():
    """Test with logging output."""
    logger = structlog.get_logger()
    logger.info("test_message", value="data")

    result = my_function()
    assert result
```

### Run Single Test
```bash
# Single test
pytest tests/unit/test_vlm_factory.py::TestVLMBackendEnum::test_ollama_backend_value -v

# All tests matching pattern
pytest tests/unit/ -k "test_ollama" -v
```

---

## Test Markers

### Available Markers
```bash
# Run only async tests
pytest tests/ -m asyncio -v

# Run only cloud tests
pytest tests/ -m cloud -v

# Skip slow tests
pytest tests/ -m "not slow" -v

# Skip cloud tests (CI/CD default)
pytest tests/ -m "not cloud" -v
```

### Mark Custom Tests
```python
@pytest.mark.cloud
def test_cloud_feature():
    """Test that requires cloud setup."""
    pass

@pytest.mark.slow
def test_slow_operation():
    """Test that takes >1 second."""
    pass
```

---

## Fixtures

### Global Fixtures (`tests/conftest.py`)
- `event_loop` - Async event loop management
- `tmp_path` - Temporary directory (pytest builtin)

### Cloud Test Fixtures (`tests/integration/conftest.py`)
- `skip_without_alibaba_key` - Skip if no API key
- `create_minimal_test_image` - Minimal PNG for VLM tests

### Usage
```python
@pytest.mark.asyncio
async def test_with_fixture(self, skip_without_alibaba_key, create_minimal_test_image):
    """Test using fixtures."""
    # skip_without_alibaba_key is used as skip decorator
    # create_minimal_test_image returns Path to test image
    image_path = create_minimal_test_image
    assert image_path.exists()
```

---

## Best Practices

### 1. Clear Naming
```python
# Good
def test_vlm_factory_creates_ollama_client():
    pass

def test_ollama_client_encodes_image_as_base64():
    pass

# Avoid
def test_factory():
    pass

def test_encode():
    pass
```

### 2. One Assert Per Test (Ideally)
```python
# Good
def test_config_defaults_to_ollama():
    """Test default backend is OLLAMA."""
    backend = get_vlm_backend_from_config()
    assert backend == VLMBackend.OLLAMA

# Less Good
def test_config_multiple_checks():
    """Test config has multiple properties."""
    backend = get_vlm_backend_from_config()
    assert backend == VLMBackend.OLLAMA
    assert backend.value == "ollama"
    assert str(backend) == "ollama"
```

### 3. Use Descriptive Docstrings
```python
def test_config_priority_env_var_first():
    """Test environment variable has highest priority.

    Priority order:
    1. VLM_BACKEND env var
    2. llm_config.yml routing.vlm_backend
    3. Default: OLLAMA
    """
    with patch.dict(os.environ, {"VLM_BACKEND": "dashscope"}):
        backend = get_vlm_backend_from_config()
        assert backend == VLMBackend.DASHSCOPE
```

### 4. Arrange-Act-Assert Pattern
```python
def test_factory_creates_client():
    """Test factory creates client."""
    # Arrange
    mock_client_class = MagicMock()

    # Act
    with patch("module.ClientClass", mock_client_class):
        client = get_vlm_client(VLMBackend.OLLAMA)

    # Assert
    assert client is not None
    mock_client_class.assert_called_once()
```

### 5. Isolate External Dependencies
```python
def test_with_mocked_http():
    """Test isolates HTTP calls."""
    # Create mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "value"}

    # Patch httpx
    with patch("httpx.AsyncClient") as mock_http:
        client = OllamaVLMClient()
        client.client.post = AsyncMock(return_value=mock_response)
        # Now test works without real HTTP calls
```

---

## Troubleshooting

### Tests Hang
```bash
# Check timeout (default 300s)
pytest tests/ --timeout=10 -v  # 10 second timeout

# Run with verbose to see where it hangs
pytest tests/ -vv --tb=short
```

### Import Errors
```bash
# Verify dependencies installed
pip list | grep pytest

# Reinstall dependencies
pip install -e ".[dev]"  # From project root
```

### Async Errors
```python
# Use @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_code():
    result = await async_function()
```

### Mock Not Working
```python
# Patch at source module, not caller
# Wrong: patch("module_that_imports.function")
# Right: patch("module_where_function_defined.function")

from src.components.llm_proxy.vlm_factory import OllamaVLMClient
# This import works, but need to patch at vlm_factory
with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient"):
    pass
```

---

## Performance Tips

### Run Tests in Parallel
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run with -n auto
pytest tests/ -n auto -v
```

### Run Only Failed Tests
```bash
# Save results
pytest tests/ --lf -v  # Last Failed

# Run failed tests
pytest tests/ --ff -v  # Failed First
```

### Skip Slow Tests in Development
```bash
# Skip tests marked as slow
pytest tests/ -m "not slow" -v
```

---

## CI/CD Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -m "not cloud" --cov=src --cov-fail-under=80
```

### Pre-commit Hook
```bash
# Install pre-commit
pip install pre-commit

# Run tests before commit
pre-commit run pytest --all-files
```

---

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [AegisRAG Testing Strategy](/docs/testing/TESTING_STRATEGY.md)

---

## Support

For issues or questions:
1. Check test docstrings for examples
2. Review existing tests in same file
3. Consult SPRINT_36_TESTS_SUMMARY.md for detailed docs
4. Contact: @testing-team on project Slack

---

**Happy Testing! 🧪**
