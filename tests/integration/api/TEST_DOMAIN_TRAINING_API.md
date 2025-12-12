# Domain Training API Integration Tests

Sprint 45 - Feature 45.12: Comprehensive Integration Test Suite

## Overview

This test suite provides comprehensive integration test coverage for the Domain Training API endpoints. All 41 tests verify correct API behavior with mocked external dependencies (Neo4j, Redis, Ollama).

## Test Coverage

### 1. Domain Creation (6 tests)

- **test_create_domain_success**: Successful domain creation with all fields
- **test_create_domain_missing_name**: Validation error when name is missing
- **test_create_domain_missing_description**: Validation error when description is missing
- **test_create_domain_short_description**: Validation error when description < 10 chars
- **test_create_domain_invalid_name_format**: Validation error for invalid name (spaces, uppercase)
- **test_create_domain_default_llm_model**: Uses default LLM when not specified

**Endpoint**: `POST /api/v1/admin/domains/`

**Expected Status Codes**:
- 201 Created (success)
- 422 Unprocessable Entity (validation errors)

### 2. List Domains (3 tests)

- **test_list_domains_empty**: Returns empty list when no domains exist
- **test_list_domains_returns_all**: Returns all domains with complete metadata
- **test_list_domains_includes_metadata**: Verifies all required fields in response

**Endpoint**: `GET /api/v1/admin/domains/`

**Expected Status Codes**:
- 200 OK

### 3. Get Domain (3 tests)

- **test_get_domain_exists**: Returns existing domain with complete data
- **test_get_domain_not_found**: Returns 404 for non-existent domain
- **test_get_domain_includes_prompts**: Includes extraction prompts in response

**Endpoint**: `GET /api/v1/admin/domains/{name}`

**Expected Status Codes**:
- 200 OK (success)
- 404 Not Found (domain doesn't exist)

### 4. Training Operations (6 tests)

- **test_start_training_success**: Successfully starts training with 5+ samples
- **test_start_training_domain_not_found**: Returns 404 when domain doesn't exist
- **test_start_training_already_running**: Returns 409 when training in progress
- **test_start_training_insufficient_samples**: Validation error with <5 samples
- **test_start_training_exactly_five_samples**: Succeeds with exactly 5 samples (minimum)
- **test_start_training_many_samples**: Succeeds with >5 samples

**Endpoint**: `POST /api/v1/admin/domains/{name}/train`

**Expected Status Codes**:
- 200 OK (training started)
- 404 Not Found (domain doesn't exist)
- 409 Conflict (training already running)
- 422 Unprocessable Entity (insufficient samples)

### 5. Training Status (4 tests)

- **test_get_training_status_running**: Returns progress for in-progress training
- **test_get_training_status_completed**: Returns metrics for completed training
- **test_get_training_status_no_training**: Returns not_started when no training has occurred
- **test_get_training_status_failed**: Returns error details for failed training

**Endpoint**: `GET /api/v1/admin/domains/{name}/training-status`

**Expected Status Codes**:
- 200 OK

### 6. Delete Domain (3 tests)

- **test_delete_domain_success**: Successfully deletes existing domain
- **test_delete_domain_not_found**: Returns 404 for non-existent domain
- **test_delete_general_domain_fails**: Prevents deletion of protected 'general' domain

**Endpoint**: `DELETE /api/v1/admin/domains/{name}`

**Expected Status Codes**:
- 204 No Content (success)
- 404 Not Found (domain doesn't exist)
- 400 Bad Request (protected domain)

### 7. Available Models (3 tests)

- **test_get_available_models_success**: Returns list of available Ollama models
- **test_get_available_models_empty**: Handles empty model list gracefully
- **test_get_available_models_ollama_unavailable**: Handles connection failures

**Endpoint**: `GET /api/v1/admin/domains/available-models`

**Expected Status Codes**:
- 200 OK (success, even with empty list)
- 503 Service Unavailable (Ollama offline)

### 8. Document Classification (6 tests)

- **test_classify_document_success**: Classifies document and returns top matches
- **test_classify_document_empty_text**: Validation error for empty text
- **test_classify_document_very_short_text**: Handles minimal text gracefully
- **test_classify_document_custom_top_k**: Respects top_k parameter
- **test_classify_document_invalid_top_k**: Validation error for top_k=0
- **test_classify_document_negative_top_k**: Validation error for negative top_k

**Endpoint**: `POST /api/v1/admin/domains/classify`

**Expected Status Codes**:
- 200 OK (success)
- 422 Unprocessable Entity (validation errors)

### 9. Error Handling (3 tests)

- **test_api_returns_400_on_validation_error**: Proper 400/422 validation responses
- **test_api_returns_404_on_not_found**: Consistent 404 responses
- **test_api_returns_409_on_conflict**: Proper 409 conflict responses

### 10. Response Format (4 tests)

- **test_api_returns_json_content_type**: All responses have application/json content-type
- **test_create_domain_returns_201_created**: POST returns 201 status
- **test_delete_domain_returns_204_no_content**: DELETE returns empty 204 response
- **test_training_status_returns_200_ok**: GET status returns 200 OK

## Test Statistics

| Category | Count |
|----------|-------|
| Create Domain | 6 |
| List Domains | 3 |
| Get Domain | 3 |
| Training | 6 |
| Training Status | 4 |
| Delete Domain | 3 |
| Available Models | 3 |
| Document Classification | 6 |
| Error Handling | 3 |
| Response Format | 4 |
| **Total** | **41** |

## Fixtures

All tests use shared fixtures from `conftest.py`:

### Domain Fixtures
- `sample_domain_data`: Complete domain with all fields
- `sample_general_domain`: Default 'general' domain
- `domain_creation_request`: POST request payload
- `domain_creation_request_minimal`: Minimal POST payload

### Training Fixtures
- `sample_training_log`: Completed training log
- `sample_training_log_failed`: Failed training log
- `sample_training_samples`: 5 sample training documents
- `training_request`: Complete training request

### API Fixtures
- `client`: FastAPI TestClient
- `api_base_url`: API base URL
- `mock_domain_repository`: Mocked DomainRepository
- `mock_http_client`: Mocked HTTP client
- `ollama_models`: Sample Ollama models list

## Mock Strategy

All external dependencies are mocked to ensure tests run fast and independently:

```python
# Neo4j
- DomainRepository.create_domain() -> AsyncMock
- DomainRepository.get_domain() -> AsyncMock
- DomainRepository.list_domains() -> AsyncMock
- DomainRepository.delete_domain() -> AsyncMock
- DomainRepository.create_training_log() -> AsyncMock
- DomainRepository.update_training_log() -> AsyncMock
- DomainRepository.get_latest_training_log() -> AsyncMock

# Ollama
- httpx.AsyncClient -> Mocked with proper response structure
- Returns {"models": [{"name": "...", "size": ...}]}

# Domain Classifier
- DomainClassifier.load_domains() -> AsyncMock
- DomainClassifier.classify_document() -> Returns similarity scores
```

## Running Tests

### Run all domain training API tests
```bash
poetry run pytest tests/integration/api/test_domain_training_api.py -v
```

### Run specific test
```bash
poetry run pytest tests/integration/api/test_domain_training_api.py::test_create_domain_success -v
```

### Run with coverage
```bash
poetry run pytest tests/integration/api/test_domain_training_api.py --cov=src/api --cov-report=html
```

### Run tests matching pattern
```bash
poetry run pytest tests/integration/api/test_domain_training_api.py -k "create_domain" -v
```

## Test Data Examples

### Sample Domain
```python
{
    "id": "uuid-123",
    "name": "tech_docs",
    "description": "Technical documentation for APIs and software libraries",
    "status": "ready",
    "llm_model": "qwen3:32b",
    "entity_prompt": "Extract technical entities...",
    "relation_prompt": "Extract relationships...",
    "entity_examples": "[{...}]",
    "relation_examples": "[{...}]",
    "training_samples": 50,
    "training_metrics": {"entity_f1": 0.89, "relation_f1": 0.82},
    "created_at": "2025-12-12T10:00:00",
    "trained_at": "2025-12-12T11:00:00"
}
```

### Sample Training Request
```python
{
    "samples": [
        {
            "text": "Python is a programming language",
            "entities": ["Python"],
            "relations": []
        },
        # ... 4 more samples (minimum 5)
    ]
}
```

### Sample Classification Response
```python
{
    "recommended": "tech_docs",
    "confidence": 0.89,
    "candidates": [
        {"domain": "tech_docs", "score": 0.89},
        {"domain": "general", "score": 0.45}
    ]
}
```

## Key Test Patterns

### Mocking External Dependencies
```python
@pytest.fixture
def mock_domain_repository():
    """Mock DomainRepository - patch at source module."""
    with patch('src.components.domain_training.get_domain_repository') as mock:
        instance = AsyncMock()
        mock.return_value = instance
        instance.create_domain = AsyncMock()
        # ... configure other methods
        yield instance
```

### Testing HTTP Status Codes
```python
response = client.post("/api/v1/admin/domains/", json=payload)
assert response.status_code == 201
```

### Testing Validation Errors
```python
response = client.post("/api/v1/admin/domains/", json={"name": "invalid"})
assert response.status_code == 422
```

### Testing Protected Resources
```python
response = client.delete("/api/v1/admin/domains/general")
assert response.status_code == 400  # Cannot delete protected domain
```

## Coverage Goals

Target coverage for API layer: **>80%**

Test components:
- HTTP status codes (all paths covered)
- Request validation (all error cases)
- Response formats (JSON, content-type)
- Error handling (400, 404, 409, 422, 503)
- Business logic integration (with mocks)
- Edge cases (empty lists, null values, boundary conditions)

## Next Steps

1. Implement Domain Training API endpoints in `src/api/v1/admin.py`
2. Ensure all route handlers match test expectations
3. Run full test suite: `poetry run pytest tests/integration/api/test_domain_training_api.py -v`
4. Address any failing tests
5. Generate coverage report: `pytest --cov=src/api --cov-report=html`
6. Verify >80% coverage achieved

## Related Tests

- **Unit Tests**: `tests/unit/components/domain_training/`
  - `test_domain_repository.py`
  - `test_domain_classifier.py`
  - `test_dspy_optimizer.py`

- **E2E Tests**: `tests/e2e/test_domain_training_workflow.py`
  - Complete training workflow
  - Document ingestion and classification

## Notes

- All tests use `TestClient` from FastAPI (no real HTTP calls)
- Async operations are handled by pytest-asyncio
- Fixtures provide reusable test data to minimize duplication
- Tests are isolated and can run in any order
- Coverage report HTML: `htmlcov/index.html`
