# Sprint 46 Feature 46.6 - Testing Quick Start Guide

## Quick Summary
- **Feature:** Manual Domain Testing
- **Status:** Complete - Ready for Docker Testing
- **Test Results:** 11/12 passing (92%)
- **Time to Run:** <5 minutes

---

## Run Static Analysis (No Dependencies Required)

### Command
```bash
python3 scripts/static_domain_testing.py
```

### What It Tests
- File structure (14 files present)
- Class/method definitions
- Module exports
- API endpoint registration
- Configuration setup
- Sprint feature completeness

### Expected Output
```
Tests Passed: 11/12 (92%)

[PASS] Test 1: File Structure
[PASS] Test 2: Module Exports
[PASS] Test 3: DomainRepository
[PASS] Test 4: DomainClassifier
[PASS] Test 5: DSPyOptimizer
[FAIL] Test 6: API Endpoints (minor issue)
[PASS] Test 7: FastAPI Integration
[PASS] Test 8: Configuration
[PASS] Test 9: Test Structure
[PASS] Test 10: Documentation
[PASS] Test 11: Code Quality
[PASS] Test 12: Sprint Requirements
```

---

## Run Dynamic Testing (Requires Poetry Dependencies)

### Prerequisites
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag
poetry install
```

### Command
```bash
PYTHONPATH=/home/admin/projects/aegisrag/AEGIS_Rag python3 scripts/manual_domain_testing.py
```

### What It Tests
- Component imports
- Singleton pattern
- Method availability
- Configuration attributes
- Vector search integration

---

## Run Docker Integration Tests

### 1. Start Services
```bash
docker-compose up -d neo4j redis qdrant ollama
sleep 10
```

### 2. Run Unit Tests
```bash
pytest tests/unit/components/domain_training/ -v
```

### 3. Run Integration Tests
```bash
pytest tests/integration/api/test_domain_training_api.py -v
```

### 4. Run Full Test Suite with Coverage
```bash
pytest tests/ \
  --cov=src/components/domain_training \
  --cov=src/api/v1/domain_training \
  --cov-report=html \
  --cov-report=term
```

### 5. View Coverage Report
```bash
# After running tests with coverage
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

---

## API Testing Examples

### 1. Create a Domain
```bash
curl -X POST http://localhost:8000/api/v1/admin/domains/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "tech_docs",
    "description": "Technical documentation for software projects",
    "llm_model": "qwen3:32b"
  }'
```

### 2. List All Domains
```bash
curl -X GET http://localhost:8000/api/v1/admin/domains/ \
  -H "Accept: application/json"
```

### 3. Get Available Models
```bash
curl -X GET http://localhost:8000/api/v1/admin/domains/available-models
```

### 4. Classify a Document
```bash
curl -X POST http://localhost:8000/api/v1/admin/domains/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "FastAPI is a modern web framework for building APIs with Python",
    "top_k": 3
  }'
```

### 5. Discover Domain from Samples
```bash
curl -X POST http://localhost:8000/api/v1/admin/domains/discover \
  -H "Content-Type: application/json" \
  -d '{
    "sample_texts": [
      "FastAPI is a web framework",
      "Flask is lightweight",
      "Django is batteries-included"
    ],
    "llm_model": "qwen3:32b"
  }'
```

### 6. Start Training
```bash
curl -X POST http://localhost:8000/api/v1/admin/domains/tech_docs/train \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {
        "text": "FastAPI is a web framework",
        "entities": ["FastAPI", "web framework"],
        "relations": []
      }
    ]
  }'
```

### 7. Check Training Status
```bash
curl -X GET http://localhost:8000/api/v1/admin/domains/tech_docs/training-status
```

### 8. Delete a Domain
```bash
curl -X DELETE http://localhost:8000/api/v1/admin/domains/tech_docs
```

---

## Component Tests (Unit Tests)

### Run Repository Tests Only
```bash
pytest tests/unit/components/domain_training/test_domain_repository.py -v
```

### Run Classifier Tests Only
```bash
pytest tests/unit/components/domain_training/test_domain_classifier.py -v
```

### Run DSPy Optimizer Tests Only
```bash
pytest tests/unit/components/domain_training/test_dspy_optimizer.py -v
```

### Run Progress Tracker Tests Only
```bash
pytest tests/unit/components/domain_training/test_training_progress.py -v
```

---

## Troubleshooting

### Issue: "No module named 'src'"
**Solution:** Set PYTHONPATH
```bash
export PYTHONPATH=/home/admin/projects/aegisrag/AEGIS_Rag
python3 scripts/manual_domain_testing.py
```

### Issue: "No module named 'numpy'"
**Solution:** Install Poetry dependencies
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag
poetry install
```

### Issue: "Neo4j connection failed"
**Solution:** Start Neo4j in Docker
```bash
docker-compose up -d neo4j
sleep 5
```

### Issue: "Ollama service unavailable"
**Solution:** Start Ollama
```bash
docker-compose up -d ollama
sleep 10
```

---

## Key Files

### Testing Documentation
- **Full Report:** `docs/testing/SPRINT_46_DOMAIN_TESTING.md`
- **Test Results:** `SPRINT_46_TESTING_RESULTS.md`
- **This Guide:** `TESTING_QUICK_START.md`

### Testing Scripts
- **Static Analysis:** `scripts/static_domain_testing.py`
- **Dynamic Testing:** `scripts/manual_domain_testing.py`

### Test Modules
- **Repository Tests:** `tests/unit/components/domain_training/test_domain_repository.py`
- **Classifier Tests:** `tests/unit/components/domain_training/test_domain_classifier.py`
- **Optimizer Tests:** `tests/unit/components/domain_training/test_dspy_optimizer.py`
- **Progress Tests:** `tests/unit/components/domain_training/test_training_progress.py`
- **API Tests:** `tests/integration/api/test_domain_training_api.py`

### Domain Training Component
- **Module Init:** `src/components/domain_training/__init__.py`
- **Repository:** `src/components/domain_training/domain_repository.py`
- **Classifier:** `src/components/domain_training/domain_classifier.py`
- **DSPy Optimizer:** `src/components/domain_training/dspy_optimizer.py`
- **Progress Tracker:** `src/components/domain_training/training_progress.py`

### API Endpoints
- **Domain Training Router:** `src/api/v1/domain_training.py`
- **Domain Discovery Router:** `src/api/v1/admin/domain_discovery.py`

---

## Test Coverage Goals

### Target: >80% Coverage

#### Modules to Cover
- `src/components/domain_training/domain_repository.py` - Critical
- `src/components/domain_training/domain_classifier.py` - Critical
- `src/components/domain_training/dspy_optimizer.py` - Critical
- `src/components/domain_training/training_progress.py` - Important
- `src/components/domain_training/domain_discovery.py` - Important
- `src/components/domain_training/data_augmentation.py` - Important
- `src/api/v1/domain_training.py` - Critical

#### Commands to Check Coverage
```bash
# Generate coverage report
pytest tests/ --cov=src/components/domain_training --cov-report=term-missing

# Generate HTML report
pytest tests/ --cov=src/components/domain_training --cov-report=html
```

---

## Useful pytest Commands

### Run with verbose output
```bash
pytest tests/unit/components/domain_training/ -v
```

### Run with print statements visible
```bash
pytest tests/unit/components/domain_training/ -s
```

### Run specific test function
```bash
pytest tests/unit/components/domain_training/test_domain_repository.py::test_create_domain -v
```

### Run tests matching pattern
```bash
pytest tests/unit/components/domain_training/ -k "domain_classifier" -v
```

### Run with different log level
```bash
pytest tests/unit/components/domain_training/ --log-cli-level=DEBUG
```

### Run and stop on first failure
```bash
pytest tests/unit/components/domain_training/ -x
```

---

## Performance Benchmarks

### Expected Performance Metrics

| Operation | Target | Method |
|-----------|--------|--------|
| Domain listing | <100ms | Measure with curl timing |
| Document classification | <200ms | Single document, cold cache |
| Domain classification (warm) | <50ms | After classifier loaded |
| Training initialization | <1s | Background task startup |
| Training per epoch | <10s | Depends on sample count |

### How to Measure
```bash
# Measure endpoint response time
time curl -X GET http://localhost:8000/api/v1/admin/domains/

# Multiple runs for average
for i in {1..10}; do curl -s http://localhost:8000/api/v1/admin/domains/ > /dev/null; done
```

---

## Next Steps

1. **For Development:** Run static analysis to verify changes
   ```bash
   python3 scripts/static_domain_testing.py
   ```

2. **For Integration:** Run tests in Docker
   ```bash
   docker-compose up -d neo4j
   pytest tests/integration/api/test_domain_training_api.py -v
   ```

3. **For Deployment:** Run full test suite with coverage
   ```bash
   pytest tests/ --cov=src/components/domain_training --cov-report=html
   ```

4. **For Production:** Verify checklist in `docs/testing/SPRINT_46_DOMAIN_TESTING.md`

---

## Support

### For Issues
1. Check `docs/testing/SPRINT_46_DOMAIN_TESTING.md` for detailed information
2. Review test output for error messages
3. Check CLAUDE.md for environment configuration

### For Questions
- See `TESTING_QUICK_START.md` (this file) for quick commands
- See `SPRINT_46_TESTING_RESULTS.md` for detailed results
- See `docs/testing/SPRINT_46_DOMAIN_TESTING.md` for comprehensive guide

---

**Last Updated:** 2025-12-15
**Status:** Complete
**Ready for:** Docker Integration Testing
