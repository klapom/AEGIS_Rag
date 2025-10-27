# CI/CD Guide - Sprint 14 Feature 14.7

## Overview

This guide covers the CI/CD pipeline for AEGIS RAG, including troubleshooting common issues, performance optimization tips, and best practices for maintaining reliable builds.

---

## Pipeline Architecture

### Current Workflow (GitHub Actions)

```yaml
name: CI Pipeline
on: [push, pull_request]

jobs:
  test:
    - lint (ruff, black, mypy)
    - unit-tests (pytest, coverage)
    - integration-tests (pytest with services)
    - e2e-tests (full system test)
```

### Build Time Optimization

**Without Caching:** ~15-20 minutes
**With Caching:** ~5-8 minutes (60-70% reduction)

---

## Caching Strategies

### 1. Poetry Dependencies

```yaml
- name: Cache Poetry dependencies
  uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pypoetry
      .venv
    key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
    restore-keys: |
      ${{ runner.os }}-poetry-
```

**Benefit:** Avoids re-downloading/installing Python packages every run.

### 2. Docker Layer Caching

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v2

- name: Cache Docker layers
  uses: actions/cache@v3
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-buildx-
```

**Benefit:** Reuses Docker layers for faster image builds.

### 3. Ollama Models

```yaml
- name: Cache Ollama models
  uses: actions/cache@v3
  with:
    path: ~/.ollama/models
    key: ollama-models-${{ hashFiles('scripts/setup_ollama.sh') }}
    restore-keys: |
      ollama-models-
```

**Benefit:** Avoids re-downloading large LLM models (~4-8GB).

### 4. Test Data & Fixtures

```yaml
- name: Cache test fixtures
  uses: actions/cache@v3
  with:
    path: tests/fixtures
    key: test-fixtures-${{ hashFiles('tests/fixtures/**') }}
```

**Benefit:** Speeds up test data setup.

---

## Parallel Test Execution

### Using `pytest-xdist`

```bash
# Run tests in parallel (auto-detect CPU cores)
pytest tests/ -n auto --dist loadfile

# Run with specific worker count
pytest tests/ -n 4
```

**Performance:** 2-4x faster on multi-core runners.

### Test Splitting by Type

```yaml
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/unit/ -n auto

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - run: pytest tests/integration/ -n auto

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - run: pytest tests/e2e/
```

**Benefit:** Independent test jobs run in parallel, faster feedback.

---

## Dependency Management

### Poetry Lock File Hygiene

```bash
# Update dependencies (check for conflicts)
poetry update

# Export requirements.txt for CI
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Verify lock file is current
poetry check
```

### Pinning Critical Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.11"
spacy = "^3.7.0"  # Pin major.minor for stability
lightrag = "^0.1.0"  # Pin specific version
```

**Best Practice:** Pin major versions for production stability, allow minor/patch updates.

---

## Flaky Test Management

### Identifying Flaky Tests

```bash
# Run test multiple times to detect flakiness
pytest tests/integration/test_foo.py --count=10

# Run with pytest-flakefinder
pytest --flake-finder --flake-runs=5
```

### Common Causes & Fixes

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Timing Dependencies** | Tests fail intermittently | Add `await asyncio.sleep(0.1)` or use `pytest-asyncio` fixtures |
| **Resource Cleanup** | Tests fail after specific order | Use proper teardown fixtures, ensure cleanup |
| **External Service Timeouts** | Tests timeout randomly | Increase timeout, add retry logic, mock external calls |
| **Race Conditions** | Tests fail in parallel | Use locks, ensure proper async coordination |

### Quarantine Flaky Tests

```python
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_sometimes_fails():
    # Automatically retry up to 3 times
    pass

@pytest.mark.skip(reason="Flaky - TD-42")
def test_very_flaky():
    # Skip entirely until fixed
    pass
```

---

## Debugging CI Failures

### Local Reproduction

```bash
# 1. Pull exact CI environment
docker pull ghcr.io/aegis-rag/ci-runner:latest

# 2. Run locally
docker run -it --rm \
  -v $(pwd):/workspace \
  ghcr.io/aegis-rag/ci-runner:latest \
  bash

# 3. Reproduce CI commands
poetry install
pytest tests/ -v
```

### Access CI Artifacts

```yaml
- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: |
      test-results.xml
      coverage.xml
      .pytest_cache/
```

**Access:** Download from GitHub Actions UI → Artifacts section.

### Enable Debug Logging

```yaml
- name: Run tests with debug
  env:
    LOG_LEVEL: DEBUG
    PYTEST_VERBOSE: "true"
  run: pytest tests/ -vv -s --tb=long
```

---

## Performance Optimization Tips

### 1. Reduce Test Scope for PRs

```yaml
# Only run affected tests on PR
- name: Detect changed files
  id: changes
  uses: dorny/paths-filter@v2
  with:
    filters: |
      backend:
        - 'src/**'
      tests:
        - 'tests/**'

- name: Run backend tests
  if: steps.changes.outputs.backend == 'true'
  run: pytest tests/unit/ tests/integration/
```

### 2. Fail Fast

```yaml
- name: Run tests with fail-fast
  run: pytest tests/ --maxfail=5 -x
```

**Benefit:** Stop after 5 failures to save time.

### 3. Skip Slow Tests on PR

```python
@pytest.mark.slow
def test_very_slow_integration():
    pass
```

```yaml
# PR workflow: skip slow tests
- run: pytest tests/ -m "not slow"

# Main branch: run all tests
- run: pytest tests/
```

---

## Coverage Requirements

### Target: >80% Code Coverage

```bash
# Generate coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=xml

# Fail if coverage drops below threshold
pytest tests/ --cov=src --cov-fail-under=80
```

### Upload to Codecov

```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
    fail_ci_if_error: true
```

---

## Security Scanning

### 1. Bandit (Python Security Linter)

```bash
bandit -r src/ -f json -o bandit-report.json
```

### 2. Safety (Dependency Vulnerability Scanning)

```bash
safety check --json
```

### 3. Trivy (Docker Image Scanning)

```yaml
- name: Scan Docker image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: aegis-rag:${{ github.sha }}
    severity: CRITICAL,HIGH
```

---

## Troubleshooting Common Issues

### Issue: Poetry Install Fails

**Error:** `SolverProblemError: Because package X depends on Y...`

**Solution:**
```bash
# Clear Poetry cache
poetry cache clear pypi --all

# Update lock file
poetry lock --no-update

# Force reinstall
poetry install --remove-untracked
```

### Issue: Pytest Hangs on Async Tests

**Error:** Tests hang indefinitely

**Solution:**
```python
# Add timeout decorator
@pytest.mark.timeout(60)
async def test_long_running():
    pass

# Or configure globally in pytest.ini
[pytest]
timeout = 300
```

### Issue: Docker Build OOM

**Error:** `Container killed (OOM)`

**Solution:**
```yaml
# Increase Docker memory limit
- name: Set up Docker
  run: |
    echo '{"default-address-pools":[{"base":"172.17.0.0/12","size":24}]}' | \
    sudo tee /etc/docker/daemon.json
    sudo systemctl restart docker
```

### Issue: Rate Limited by External APIs

**Error:** `HTTP 429: Too Many Requests`

**Solution:**
```yaml
# Use GitHub Actions secrets for API keys
- name: Set API keys
  env:
    OLLAMA_API_KEY: ${{ secrets.OLLAMA_API_KEY }}
  run: pytest tests/

# Or mock external calls in tests
@pytest.fixture
def mock_ollama(monkeypatch):
    monkeypatch.setattr("ollama.Client.chat", lambda *args: {"response": "mocked"})
```

---

## CI/CD Best Practices

### 1. Keep CI Fast (<10 minutes)
- Use caching aggressively
- Run only necessary tests on PRs
- Parallelize independent jobs

### 2. Make CI Deterministic
- Pin all dependencies
- Use fixed seeds for random tests
- Avoid time-dependent tests

### 3. Fail Early, Fail Clearly
- Run linting first (fast feedback)
- Use descriptive error messages
- Upload logs and artifacts on failure

### 4. Maintain CI Infrastructure
- Update actions to latest versions
- Monitor runner performance
- Clean up old caches/artifacts

### 5. Document CI Requirements
- List required secrets/env vars
- Document service dependencies
- Provide local reproduction steps

---

## Monitoring & Alerts

### GitHub Actions Status Badge

```markdown
![CI Status](https://github.com/your-org/aegis-rag/actions/workflows/ci.yml/badge.svg)
```

### Slack Notifications on Failure

```yaml
- name: Notify Slack on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "CI Failed: ${{ github.workflow }} on ${{ github.ref }}"
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Future Improvements

1. **Self-Hosted Runners**: Faster builds with cached dependencies
2. **Matrix Testing**: Test against multiple Python versions (3.11, 3.12)
3. **Performance Regression Tests**: Automated benchmarking in CI
4. **Canary Deployments**: Gradual rollout with automatic rollback
5. **Dependency Scanning**: Automated PRs for security updates (Dependabot)

---

## References

- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions/security-hardening-for-github-actions)
- [Poetry CI/CD Guide](https://python-poetry.org/docs/ci/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Docker Build Optimization](https://docs.docker.com/build/cache/)
