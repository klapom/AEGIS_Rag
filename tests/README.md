# AEGIS RAG Sprint 2 - Test Suite

Comprehensive test suite for Sprint 2: Vector Search Foundation with >80% code coverage.

## Test Structure

```
tests/
├── conftest.py                           # Shared fixtures and configuration
├── components/
│   └── vector_search/
│       ├── test_qdrant_client.py         # Qdrant wrapper tests
│       ├── test_embeddings.py            # Embedding service tests
│       ├── test_bm25_search.py           # BM25 keyword search tests
│       ├── test_hybrid_search.py         # Hybrid search tests
│       └── test_ingestion.py             # Document ingestion tests
├── utils/
│   └── test_fusion.py                    # RRF algorithm tests
├── api/
│   └── v1/
│       └── test_retrieval.py             # FastAPI endpoint tests
└── integration/
    ├── test_e2e_indexing.py              # E2E indexing workflow tests
    └── test_e2e_hybrid_search.py         # E2E hybrid search tests
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
Fast tests with mocked dependencies. Run these during development:
```bash
pytest -m unit
```

### Integration Tests (`@pytest.mark.integration`)
Tests requiring real services (Qdrant, Ollama). Ensure services are running:
```bash
# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Start Ollama and pull model
ollama pull nomic-embed-text

# Run integration tests
pytest -m integration
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/utils/test_fusion.py
```

### Run Specific Test Function
```bash
pytest tests/utils/test_fusion.py::test_rrf_basic_fusion
```

### Run by Marker
```bash
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not integration" # Skip integration tests
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html to view detailed coverage
```

### Parallel Execution (Faster)
```bash
pip install pytest-xdist
pytest -n auto  # Use all CPU cores
```

### Verbose Output
```bash
pytest -v           # Verbose test names
pytest -vv          # Extra verbose with full diffs
pytest -s           # Show print statements
```

## Test Coverage Goals

| Module | Target Coverage | Status |
|--------|----------------|--------|
| `qdrant_client.py` | >85% | ✅ |
| `embeddings.py` | >85% | ✅ |
| `bm25_search.py` | >85% | ✅ |
| `fusion.py` | >90% | ✅ |
| `ingestion.py` | >80% | ✅ |
| `hybrid_search.py` | >80% | ✅ |
| `retrieval.py` | >80% | ✅ |
| **Overall** | **>80%** | **Target** |

## Key Test Fixtures

### Mock Fixtures (Unit Tests)
- `mock_qdrant_client` - Mock Qdrant client wrapper
- `mock_embedding_service` - Mock embedding service
- `mock_bm25_search` - Mock BM25 search
- `sample_documents` - Sample test documents
- `sample_embeddings` - Mock embedding vectors

### Integration Fixtures
- `integration_qdrant_client` - Real Qdrant client
- `integration_embedding_service` - Real Ollama embeddings
- `integration_test_docs` - Temporary test documents
- `temp_test_dir` - Temporary directory for tests

## Test Patterns

### Async Tests
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Parametrized Tests
```python
@pytest.mark.unit
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiplication(input, expected):
    assert input * 2 == expected
```

### Error Testing
```python
@pytest.mark.unit
def test_error_handling():
    with pytest.raises(VectorSearchError) as exc_info:
        function_that_raises()
    assert "error message" in str(exc_info.value)
```

## Continuous Integration

Tests are configured for CI/CD pipelines:
- Fast unit tests run on every commit
- Integration tests run on PR and main branch
- Coverage reports uploaded to Codecov

### GitHub Actions Example
```yaml
- name: Run Unit Tests
  run: pytest -m unit --cov=src --cov-report=xml

- name: Run Integration Tests
  run: |
    docker run -d -p 6333:6333 qdrant/qdrant
    pytest -m integration
```

## Debugging Tests

### Run Failed Tests Only
```bash
pytest --lf  # Last failed
pytest --ff  # Failed first, then others
```

### Drop into Debugger on Failure
```bash
pytest --pdb
```

### Show Print Statements
```bash
pytest -s
```

### Increase Verbosity
```bash
pytest -vv --tb=long
```

## Test Development Guidelines

1. **Write Tests First (TDD)**: Write failing test, implement feature, make test pass
2. **Test Coverage**: Aim for >80% coverage, focus on critical paths
3. **Mock External Dependencies**: Unit tests should be fast and isolated
4. **Use Fixtures**: Reuse common test setup via conftest.py
5. **Clear Test Names**: Use descriptive names that explain what is being tested
6. **Test Edge Cases**: Empty inputs, null values, error conditions
7. **Happy Path + Error Cases**: Test both success and failure scenarios
8. **Document Complex Tests**: Add docstrings explaining test purpose

## Common Issues

### Integration Tests Fail with Connection Error
**Solution**: Ensure Qdrant and Ollama services are running:
```bash
docker run -d -p 6333:6333 qdrant/qdrant
ollama serve
ollama pull nomic-embed-text
```

### Tests Timeout
**Solution**: Increase timeout in pytest.ini or skip slow tests:
```bash
pytest -m "not slow"
```

### Import Errors
**Solution**: Install package in development mode:
```bash
pip install -e .
```

### Coverage Too Low
**Solution**: Identify uncovered lines:
```bash
pytest --cov=src --cov-report=term-missing
```

## Performance Benchmarks

Expected test execution times:
- Unit tests: ~10-30 seconds
- Integration tests: ~60-120 seconds (depends on services)
- Full test suite: ~2-3 minutes

Parallel execution (with pytest-xdist):
- Unit tests: ~5-15 seconds
- Full suite: ~60-90 seconds

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)
