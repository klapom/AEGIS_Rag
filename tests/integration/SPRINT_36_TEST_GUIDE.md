# Sprint 36 Integration Tests - Quick Reference

## Files Created

```
tests/integration/
├── llm_proxy/
│   ├── __init__.py
│   └── test_vlm_integration.py           (435 lines, 22 tests)
├── test_local_vs_cloud.py                (460 lines, 23 tests)
└── SPRINT_36_TEST_GUIDE.md               (this file)
```

## Quick Run Commands

### All Sprint 36 VLM Tests
```bash
pytest tests/integration/llm_proxy/test_vlm_integration.py \
       tests/integration/test_local_vs_cloud.py \
       -v
```

### Factory Pattern Tests Only
```bash
pytest tests/integration/llm_proxy/test_vlm_integration.py::TestVLMFactoryPattern -v
```

### Ollama VLM Tests
```bash
pytest tests/integration/llm_proxy/test_vlm_integration.py::TestOllamaVLMIntegration -v
```

### Local vs Cloud Comparison Tests
```bash
pytest tests/integration/test_local_vs_cloud.py::TestLocalVsCloudVLMMetadata -v
```

### Configuration Tests
```bash
pytest tests/integration/llm_proxy/test_vlm_integration.py::TestVLMConfiguration -v
pytest tests/integration/test_local_vs_cloud.py::TestConfigurationDrivenBehavior -v
```

### With Coverage Report
```bash
pytest tests/integration/llm_proxy/test_vlm_integration.py \
       tests/integration/test_local_vs_cloud.py \
       --cov=src/components/llm_proxy \
       --cov=src/components/ingestion/image_processor \
       --cov-report=html
```

### Cloud Tests (requires ALIBABA_CLOUD_API_KEY)
```bash
pytest -m cloud tests/integration/test_local_vs_cloud.py -v
```

### Skip Cloud Tests (for CI)
```bash
pytest -m "not cloud" tests/integration/test_local_vs_cloud.py -v
```

## Test Classes Overview

### test_vlm_integration.py (22 tests)

| Class | Tests | Focus |
|-------|-------|-------|
| TestVLMFactoryPattern | 6 | Factory pattern, backend selection, defaults |
| TestOllamaVLMIntegration | 5 | Ollama client, image processing, mocking |
| TestImageProcessorVLMIntegration | 3 | ImageProcessor integration with factory |
| TestVLMConfiguration | 3 | Environment variables, config files, priority |
| TestVLMErrorHandling | 5 | Error scenarios, metadata consistency |

### test_local_vs_cloud.py (23 tests)

| Class | Tests | Focus |
|-------|-------|-------|
| TestLocalVsCloudVLMMetadata | 3 | Metadata structure comparison |
| TestLocalVsCloudCostTracking | 3 | Cost tracking (local vs cloud) |
| TestConfigurationDrivenBehavior | 4 | Config file validation, precedence |
| TestVLMBackendDescriptions | 3 | Enum validation, backend properties |
| TestVLMProtocolInterface | 2 | Protocol compliance |
| TestVLMFallbackBehavior | 2 | Fallback patterns |
| TestVLMIntegrationChains | 1 | Complete integration pipeline |
| (Other classes) | 5 | Additional tests |

## Key Features Tested

### VLM Factory Pattern
- ✅ Ollama client creation
- ✅ DashScope client creation
- ✅ Environment variable selection
- ✅ Config file selection
- ✅ Default fallback (Ollama)
- ✅ Priority: env > config > default

### OllamaVLMClient
- ✅ Initialization with custom params
- ✅ Image description generation
- ✅ File existence validation
- ✅ Custom model override
- ✅ HTTP error handling
- ✅ Metadata structure

### ImageProcessor Integration
- ✅ VLM Factory detection
- ✅ Factory usage for image processing
- ✅ Complete integration chain

### Local vs Cloud
- ✅ Metadata structure parity
- ✅ Cost tracking (local $0, cloud $$)
- ✅ Backend isolation
- ✅ Configuration precedence
- ✅ Fallback mechanisms

## Test Markers

### Pytest Markers Used

```python
@pytest.mark.asyncio        # Async test
@pytest.mark.cloud          # Requires ALIBABA_CLOUD_API_KEY
@pytest.mark.integration    # Integration test
```

## Environment Setup

### For Local Testing

```bash
# Required
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL_VLM=qwen3-vl:32b

# Optional (for cloud tests)
export ALIBABA_CLOUD_API_KEY=sk-...
export ALIBABA_CLOUD_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

### For CI/CD

Tests auto-mock Ollama when running in CI (no setup needed).

## Test Fixtures

All tests use lightweight fixtures:

- **test_image**: Minimal valid PNG (1x1 pixel, 94 bytes)
- **tmp_path**: Pytest's temporary directory
- No external service dependencies (all mocked)

## Common Test Patterns

### Mocking Ollama HTTP

```python
with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "response": "Description",
        "eval_count": 50,
        "total_duration": 1000000000,
    }
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_http.return_value = mock_client
```

### Testing Config Loading

```python
with patch("src.components.llm_proxy.vlm_factory.get_llm_proxy_config") as mock_config:
    mock_config.return_value = MagicMock(routing={"vlm_backend": "ollama"})
    backend = get_vlm_backend_from_config()
```

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_ollama_client_with_mock_http(self, test_image):
    """Test with async mock."""
    with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
        # Setup and assertions
```

## Debugging Failed Tests

### Run with Verbose Output
```bash
pytest tests/integration/llm_proxy/test_vlm_integration.py -vvv --tb=long
```

### Run Single Test
```bash
pytest tests/integration/llm_proxy/test_vlm_integration.py::TestVLMFactoryPattern::test_vlm_factory_get_ollama_client -vvs
```

### Print Debug Info
```bash
pytest tests/integration/llm_proxy/test_vlm_integration.py -v -s
```

### Show Test Execution Time
```bash
pytest tests/integration/llm_proxy/test_vlm_integration.py -v --durations=10
```

## Continuous Integration

### GitHub Actions Integration

Tests are CI-ready:
- Ollama not required (HTTP mocked)
- Cloud tests skip without ALIBABA_CLOUD_API_KEY
- All async tests properly handled
- No filesystem dependencies

### Running in CI

```yaml
# .github/workflows/test.yml
- name: Sprint 36 Integration Tests
  run: |
    pytest tests/integration/llm_proxy/test_vlm_integration.py \
           tests/integration/test_local_vs_cloud.py \
           -m "not cloud" \
           -v --tb=short
```

## Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| vlm_factory.py | 100% | 100% |
| ollama_vlm.py | 95% | 95% |
| dashscope_vlm.py | 85% | 70% |
| image_processor.py | 90% | 85% |

## Related Files

- **Source**: `src/components/llm_proxy/vlm_factory.py`
- **Source**: `src/components/llm_proxy/ollama_vlm.py`
- **Source**: `src/components/llm_proxy/dashscope_vlm.py`
- **Source**: `src/components/ingestion/image_processor.py`
- **Config**: `config/llm_config.yml`
- **Template**: `.env.dgx-spark.template`

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | Check module exists in src/components/llm_proxy/ |
| Async failures | Ensure @pytest.mark.asyncio decorator |
| Mock not working | Use correct patch path (lazy imports) |
| Cloud tests skip | Set ALIBABA_CLOUD_API_KEY or skip with -m "not cloud" |
| File not found | Check tmp_path fixture is passed to test |

## Performance

- **Total test time**: ~5-10 seconds (mocked tests only)
- **Cloud tests**: Add 2-5s per test if ALIBABA_CLOUD_API_KEY set
- **Coverage generation**: Add 20-30 seconds

## For More Details

See: `SPRINT_36_INTEGRATION_TESTS.md`
