# Feature 52.4: CI/CD Pipeline Optimization - Test Plan

## Overview
Verification plan for Feature 52.4: Re-enable integration tests in GitHub Actions with proper LLM/embedding mocking.

## Pre-Requisites

### Local Environment
- Python 3.12.7 with Poetry
- Docker services running: Qdrant, Neo4j, Redis, Ollama
- DGX Spark or development machine with access to all services

### CI Environment
- GitHub repository with Actions enabled
- Test branch for validation (do not merge to main until verified)

## Test Categories

### 1. Local Development Testing (CI=false)

These tests verify that local development is unaffected by the changes.

#### Test 1.1: Unit Tests with Real Ollama
**Objective**: Verify local development uses real LLM, not mocks

```bash
# Clear any CI environment variable
unset CI

# Run integration tests pointing to real Ollama
poetry run pytest tests/integration/test_chat_sse.py -v --tb=short

# Expected Result:
# ✅ Tests run without "[CI MODE]" messages
# ✅ Real Ollama is called (may see actual LLM responses in logs)
# ✅ Tests pass with real service responses
```

#### Test 1.2: Verify Mocking is Disabled Locally
**Objective**: Confirm mocking fixtures don't activate locally

```bash
# Run with capture to see fixture output
poetry run pytest tests/integration/test_answer_generator_citations.py -v -s

# Expected Result:
# ✅ No "[CI MODE]" messages in output
# ✅ Real embedding service called
# ✅ Real LLM responses used in tests
```

#### Test 1.3: Local Test Requiring Real LLM
**Objective**: Verify requires_llm tests run locally

```bash
# Find a test marked with @pytest.mark.requires_llm
poetry run pytest tests/integration/ -v -k "requires_llm" --co | head -5

# Run it
poetry run pytest tests/integration/test_cloud_llm_vlm.py::test_example -v -s

# Expected Result:
# ✅ Test runs (not skipped)
# ✅ Uses real Ollama/cloud LLM
```

---

### 2. CI Environment Testing (CI=true)

These tests verify the auto-mocking works in CI-like conditions.

#### Test 2.1: Local Simulation of CI Conditions
**Objective**: Verify auto-mocking activates with CI=true

```bash
# Simulate GitHub Actions environment
CI=true poetry run pytest tests/integration/test_answer_generator_citations.py -v -s

# Expected Output:
# ✅ "[CI MODE] AegisLLMProxy fully mocked for CI testing"
# ✅ "[CI MODE] EmbeddingService mocked with 1024-dim vectors"
# ✅ Tests pass with mocked responses
# ✅ No real Ollama calls
```

#### Test 2.2: Verify LLM Mocking
**Objective**: Confirm LLMResponse is properly mocked

```bash
# Enable CI mode and capture detailed output
CI=true poetry run pytest tests/integration/ -v -s -k "citation" --tb=short

# Expected Result in Test Output:
# ✅ Mocked LLM response: "Mocked LLM response for CI testing"
# ✅ Provider: "mock"
# ✅ Cost: 0.0 USD (not charged in CI)
# ✅ latency_ms: 10.0 (mock latency)
```

#### Test 2.3: Verify Embedding Mocking
**Objective**: Confirm embeddings are mocked with correct dimension

```bash
# Enable CI mode
CI=true poetry run pytest tests/integration/test_e2e_hybrid_search.py -v -s

# Expected Result:
# ✅ Embeddings generated successfully
# ✅ Dimension: 1024 (BGE-M3 spec)
# ✅ Deterministic: same text → same embedding
# ✅ Search works with mocked embeddings
```

#### Test 2.4: Verify requires_llm Tests are Skipped
**Objective**: Confirm tests marked requires_llm are auto-skipped in CI

```bash
# Enable CI mode
CI=true poetry run pytest tests/integration/ -v --tb=short 2>&1 | grep -i "requires real ollama"

# Expected Result:
# ✅ Multiple test skips with message:
#    "Test requires real Ollama (not available in CI)"
# ✅ Skipped count increases with CI=true
```

**Verify with explicit marker**:
```bash
CI=true poetry run pytest tests/integration/ -v -m "requires_llm"

# Expected Result:
# ✅ All tests marked requires_llm are skipped
# ✅ Output: "5 deselected" or similar
```

#### Test 2.5: Verify cloud Tests are Skipped
**Objective**: Confirm tests marked cloud are auto-skipped in CI

```bash
# Enable CI mode
CI=true poetry run pytest tests/integration/ -v --tb=short 2>&1 | grep -i "requires cloud"

# Expected Result:
# ✅ Test skips with message:
#    "Test requires cloud API keys (not available in CI)"
```

#### Test 2.6: Deterministic Mock Embeddings
**Objective**: Verify embeddings are reproducible with same text

```bash
# Create test script
cat > /tmp/test_embedding_determinism.py << 'EOF'
import os
os.environ['CI'] = 'true'

import asyncio
from tests.integration.conftest import _is_ci_environment

async def test():
    from src.components.shared.embedding_service import EmbeddingService

    service = EmbeddingService()

    # Same text should produce same embedding
    emb1 = await service.embed_text("test query")
    emb2 = await service.embed_text("test query")

    assert emb1 == emb2, "Embeddings should be deterministic"
    assert len(emb1) == 1024, "Dimension should be 1024"
    print("✅ Embeddings are deterministic and correct dimension")

asyncio.run(test())
EOF

poetry run python /tmp/test_embedding_determinism.py

# Expected Result:
# ✅ Deterministic embeddings verified
# ✅ Dimension correct: 1024
```

---

### 3. GitHub Actions Integration Testing

These tests verify the workflow executes correctly in GitHub Actions.

#### Test 3.1: Trigger CI on Test Branch
**Objective**: Verify integration tests run in GitHub Actions

```bash
# Create test branch
git checkout -b test/52.4-ci-optimization

# Commit changes
git add .
git commit -m "feat(sprint52): Re-enable integration tests with auto-mocking

- Auto-mock LLM and embeddings in CI
- Skip requires_llm and cloud tests in CI
- Update GitHub Actions workflow"

# Push to trigger CI
git push -u origin test/52.4-ci-optimization

# Go to GitHub Actions and monitor:
# https://github.com/YOUR_ORG/aegis-rag/actions

# Expected Result:
# ✅ integration-tests job starts (no longer skipped)
# ✅ Services start: Qdrant, Neo4j, Redis
# ✅ Run Integration Tests step executes
# ✅ Tests pass with auto-mocking enabled
# ✅ Coverage reported
# ✅ Quality gate passes
```

#### Test 3.2: Verify CI Output Messages
**Objective**: Confirm CI mode messages appear in Actions logs

```bash
# In GitHub Actions, check "Run Integration Tests (with Auto-Mocking)" step
# Expected log output:
# ✅ "Running integration tests with auto-mocking..."
# ✅ "CI=true enables LLM/embedding mocks for all tests"
# ✅ "[CI MODE] AegisLLMProxy fully mocked for CI testing"
# ✅ "[CI MODE] EmbeddingService mocked with 1024-dim vectors"
```

#### Test 3.3: Verify Test Skipping in CI
**Objective**: Confirm proper test skipping in Actions

```bash
# In GitHub Actions logs, search for:
grep "skipped" "Run Integration Tests (with Auto-Mocking)"

# Expected: Multiple tests skipped with reasons
# ✅ Tests marked requires_llm skipped
# ✅ Tests marked cloud skipped
# ✅ Skip count: depends on test suite (estimate 5-10 skipped)
```

#### Test 3.4: Coverage Report Generation
**Objective**: Verify coverage is collected in CI

```bash
# In GitHub Actions artifacts:
# Expected: coverage.xml and htmlcov/ uploaded

# Codecov link should be available:
# https://codecov.io/github/YOUR_ORG/aegis-rag

# Expected Result:
# ✅ Coverage report generated
# ✅ Uploaded to codecov
# ✅ Coverage >50% (existing requirement)
```

#### Test 3.5: Quality Gate Passes
**Objective**: Verify quality gate includes integration tests

```bash
# In GitHub Actions, check "Unified Quality Gate" step
# Expected output:
# ✅ "Checking all quality gates..."
# ✅ "✅ Integration Tests passed"
# ✅ "✅ All critical quality gates passed!"

# If PR: Verify automated comment posted
# Expected PR comment:
# ✅ "✅ Unified Quality Gate Passed"
# ✅ "✅ Integration Tests (with LLM/embedding auto-mocking)"
```

---

### 4. Edge Case Testing

#### Test 4.1: LLM Module Not Available
**Objective**: Verify graceful handling if AegisLLMProxy doesn't exist

```bash
# This is handled by try/except in conftest.py
# Create scenario: temporarily rename module
# Should skip silently

# Expected Result:
# ✅ Tests still run (fallback behavior)
# ✅ No ImportError exceptions
```

#### Test 4.2: EmbeddingService Module Not Available
**Objective**: Verify graceful handling if EmbeddingService doesn't exist

```bash
# This is handled by try/except in conftest.py
# Should skip silently without errors

# Expected Result:
# ✅ Tests still run
# ✅ No ImportError exceptions
```

#### Test 4.3: Database Services Unavailable
**Objective**: Verify tests properly fail if databases aren't available

```bash
# Stop one or more services
docker-compose down

# Run integration tests
CI=true poetry run pytest tests/integration/test_e2e_hybrid_search.py -v

# Expected Result:
# ✅ Tests fail with clear database connection errors
# ✅ Not masked by mocking (mocking only affects LLM/embeddings)
# ✅ Error messages indicate which service is missing
```

---

## Performance Benchmarks

### Baseline Metrics (Before Changes)
- Integration tests: DISABLED (not measured)
- CI pipeline: ~12 minutes (without integration tests)

### Target Metrics (After Changes)
- Integration tests job: ~5-6 minutes
- Total CI pipeline: ~15 minutes
- Service startup: <1 minute
- Test execution: 3-4 minutes

### Verification
```bash
# Check GitHub Actions timing for integration-tests job
# Should complete in <6 minutes for ~20-25 tests

# If takes >10 minutes: investigate test performance
# If takes <3 minutes: verify tests are actually running
```

---

## Rollback Plan

If issues occur:

### Option 1: Disable integration tests again
```yaml
# In .github/workflows/ci.yml
integration-tests:
  if: false  # Revert to disabled state
```

### Option 2: Temporary disable auto-mocking
```python
# In tests/integration/conftest.py
def _is_ci_environment() -> bool:
    return False  # Force disable mocking temporarily
```

### Option 3: Skip specific failing tests
```bash
# In CI job run command
poetry run pytest tests/integration/ \
  --ignore=tests/integration/test_failing.py \
  -v
```

---

## Sign-Off Checklist

- [ ] Test 1.1: Local development uses real Ollama
- [ ] Test 1.2: Mocking disabled locally
- [ ] Test 1.3: requires_llm tests run locally
- [ ] Test 2.1: Auto-mocking activates with CI=true
- [ ] Test 2.2: LLM responses properly mocked
- [ ] Test 2.3: Embeddings properly mocked (1024-dim)
- [ ] Test 2.4: requires_llm tests skipped in CI
- [ ] Test 2.5: cloud tests skipped in CI
- [ ] Test 2.6: Embeddings are deterministic
- [ ] Test 3.1: Integration tests run in GitHub Actions
- [ ] Test 3.2: CI mode messages in Actions logs
- [ ] Test 3.3: Proper test skipping in Actions
- [ ] Test 3.4: Coverage report generated
- [ ] Test 3.5: Quality gate passes
- [ ] Test 4.1: Graceful handling if LLM module missing
- [ ] Test 4.2: Graceful handling if Embedding module missing
- [ ] Test 4.3: Database errors properly reported
- [ ] Performance: CI completes <15 minutes
- [ ] Documentation: Sprint plan complete
- [ ] Ready for merge: All checks pass

---

## Additional Notes

### Expected Test Counts
- Total integration tests: ~24-26
- Skipped in CI (requires_llm): ~2-3
- Skipped in CI (cloud): ~1-2
- Running in CI (mocked): ~20-23

### LLM Response Format
Mocked responses follow LLMResponse Pydantic model:
```python
content: str
provider: str  # "mock" in CI
model: str
tokens_used: int
cost_usd: float  # 0.0 in CI
latency_ms: float  # 10.0 in CI
```

### Debugging Commands
```bash
# Verbose test output
CI=true poetry run pytest tests/integration/ -vv -s

# Show all marked tests
poetry run pytest tests/integration/ --co -m "requires_llm"

# Single test execution
CI=true poetry run pytest tests/integration/test_answer_generator_citations.py::test_citation_flow -vv -s

# With coverage details
CI=true poetry run pytest tests/integration/ --cov=src --cov-report=term-missing -v
```
