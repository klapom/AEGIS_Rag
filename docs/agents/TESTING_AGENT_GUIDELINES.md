# Testing Agent Guidelines - Enhanced CI/CD Quality Gates

**Purpose:** Prevent common CI failures through proactive local testing
**Target:** testing-agent subagent (used via Task tool)
**Sprint:** 61 (Post-mortem improvements)

---

## 🎯 Mission Statement

The testing-agent should **prevent CI failures** by catching issues locally BEFORE they reach GitHub Actions. Think of it as a "CI Pre-flight Check" that runs on the developer's machine.

---

## 🚨 Common CI Failure Patterns (Sprint 61 Learnings)

### ❌ Failure Pattern 1: Import Errors
**Symptom:** Code works locally but fails in CI
**Root Cause:**
- Missing dependencies in CI environment
- Import validation job has different dependencies than dev environment
- Lazy imports hide missing dependencies

**Prevention Checklist:**
```bash
# 1. Validate imports in clean environment
poetry env remove --all
poetry install --with dev --no-interaction
poetry run python -c "import src.api.main; print('✅ API imports')"

# 2. Test Sprint-specific imports
poetry run python -c "from src.domains.vector_search.embedding import NativeEmbeddingService; print('✅ Sprint imports')"

# 3. Validate all modified files
for file in $(git diff --name-only HEAD~1 | grep '\.py$'); do
    module=$(echo $file | sed 's/\//./g' | sed 's/\.py$//')
    poetry run python -c "import $module" || echo "❌ $file"
done
```

**Testing Agent Action:**
```python
# When creating/modifying imports:
1. Run import validation on modified files
2. Test in clean poetry environment
3. Verify dependencies in pyproject.toml
4. Check CI workflow has correct dependency groups
```

---

### ❌ Failure Pattern 2: Obsolete Tests
**Symptom:** Test references removed/refactored code
**Root Cause:**
- Feature removed but tests not updated
- UI refactored but integration tests not cleaned up

**Example (Sprint 61):**
```python
# tests/integration/test_gradio_ui.py
with patch("src.ui.gradio_app.httpx.AsyncClient"):  # ❌ src.ui doesn't exist!
```

**Prevention Checklist:**
```bash
# 1. Find tests for removed features
rg "src\.ui\." tests/  # Check for removed UI references
rg "gradio" tests/     # Check for deprecated dependencies

# 2. Run affected tests
pytest tests/integration/test_gradio_ui.py -v

# 3. Remove or update obsolete tests
git rm tests/integration/test_gradio_ui.py
```

**Testing Agent Action:**
```python
# When removing features:
1. Search for test files referencing the feature
2. Run tests to verify they don't import removed code
3. Either update or remove obsolete tests
4. Update test documentation
```

---

### ❌ Failure Pattern 3: Linting Errors
**Symptom:** Code passes local checks but fails CI linting
**Root Cause:**
- Local ruff/black versions differ from CI
- Pre-commit hooks not installed
- Auto-formatters not run before commit

**Prevention Checklist:**
```bash
# 1. Run full linting suite (same as CI)
poetry run ruff check src/ tests/
poetry run black --check src/ tests/ --line-length=100
poetry run mypy src/ --config-file=pyproject.toml

# 2. Auto-fix linting issues
poetry run ruff check --fix src/ tests/
poetry run black src/ tests/ --line-length=100

# 3. Verify no new issues
poetry run ruff check src/ tests/ --diff
```

**Testing Agent Action:**
```python
# Before creating PR/commit:
1. Run ruff check --fix on modified files
2. Run black formatter on modified files
3. Run mypy on modified modules
4. Verify all checks pass
5. Add pre-commit hook if missing
```

---

### ❌ Failure Pattern 4: Disk Space Issues (CI Infrastructure)
**Symptom:** `No space left on device` in GitHub Actions
**Root Cause:**
- Large coverage reports (HTML)
- Poetry cache accumulation
- Docker images not cleaned up

**Prevention Checklist:**
```bash
# 1. Check artifact sizes locally
du -sh htmlcov/     # Should be reasonable (<100MB)
du -sh .venv/       # Should be reasonable (<2GB)

# 2. Review CI workflow for cleanup steps
grep "Free Disk Space" .github/workflows/ci.yml
grep "Clear.*Cache" .github/workflows/ci.yml

# 3. Verify coverage config
grep "cov-report" .github/workflows/ci.yml  # Should NOT include html in CI
```

**Testing Agent Action:**
```python
# When modifying CI workflows:
1. Check for disk space cleanup steps
2. Verify artifact uploads are minimal (XML, not HTML)
3. Add Poetry cache cleanup after install
4. Test workflow changes in fork first
```

---

## 📋 Testing Agent Pre-Commit Checklist

### Phase 1: Code Quality (2-5 min)
```bash
# 1. Linting
poetry run ruff check --fix src/ tests/
poetry run black src/ tests/ --line-length=100
poetry run mypy src/

# 2. Import Validation
poetry run python -c "import src.api.main"
# Test all modified files

# 3. Quick Test Run
pytest tests/unit/{modified_test_files} -v
```

### Phase 2: Test Coverage (5-10 min)
```bash
# 1. Run affected tests
pytest tests/unit/ -k "test_pattern" -v

# 2. Check coverage delta
pytest tests/unit/ --cov=src --cov-report=term-missing

# 3. Verify no test regressions
pytest tests/integration/ -k "health" -v  # Quick smoke test
```

### Phase 3: CI Simulation (Optional, 10-15 min)
```bash
# 1. Clean environment
poetry env remove --all

# 2. Install like CI
poetry install --with dev --no-interaction

# 3. Run full test suite
pytest tests/unit/ tests/components/ tests/api/ -v -m "not integration"

# 4. Integration smoke test
pytest tests/integration/ -k "health" -v
```

---

## 🤖 Testing Agent Prompts

### When User Says: "Create tests for X"
**Agent Response:**
```
I'll create comprehensive tests for X with the following approach:

1. ✅ Unit tests with >80% coverage
2. ✅ Integration tests for critical paths
3. ✅ Import validation (test imports work)
4. ✅ Run local linting (ruff + black)
5. ✅ Verify tests pass locally
6. ✅ Update test documentation

Pre-flight checks:
- [ ] All imports validated
- [ ] Linting passes (ruff + black + mypy)
- [ ] Tests pass locally (pytest -v)
- [ ] Coverage >80% for new code
- [ ] No obsolete test references
```

### When User Says: "Fix failing tests"
**Agent Response:**
```
I'll debug the failing tests systematically:

1. 🔍 Identify failure pattern (import, logic, assertion, timeout)
2. 🔍 Check if test is obsolete (references removed code)
3. 🔧 Fix root cause (not just symptoms)
4. ✅ Verify fix locally
5. ✅ Run full test suite to prevent regressions

Analysis:
- Error type: [ImportError|AssertionError|Timeout|etc]
- Affected modules: [list]
- Root cause: [explanation]
- Fix strategy: [approach]
```

### When User Says: "Run tests before commit"
**Agent Response:**
```
I'll run the pre-commit test suite:

Phase 1: Quick Checks (2-3 min)
- ✅ Ruff linting
- ✅ Black formatting
- ✅ MyPy type checking
- ✅ Import validation

Phase 2: Test Execution (5-10 min)
- ✅ Modified test files
- ✅ Affected unit tests
- ✅ Integration smoke tests

Phase 3: CI Preview (optional)
- ✅ Clean env simulation
- ✅ Full unit test suite
- ✅ Coverage report

Summary:
- Tests passed: X/Y
- Coverage: Z%
- Linting: [PASS|FAIL]
- Ready for commit: [YES|NO]
```

---

## 🛡️ Defensive Testing Practices

### 1. Import Safety
```python
# ❌ BAD: Lazy import without verification
def my_function():
    from expensive_library import feature  # Fails in CI if not installed
    return feature()

# ✅ GOOD: Explicit import with error handling
try:
    from expensive_library import feature
except ImportError as e:
    logger.error("expensive_library not installed")
    raise ImportError("Install: pip install expensive-library") from e

def my_function():
    return feature()
```

### 2. Test Isolation
```python
# ❌ BAD: Test depends on external state
def test_user_exists():
    assert get_user(123)  # Fails if user 123 doesn't exist

# ✅ GOOD: Test creates its own data
def test_user_exists():
    user = create_test_user(id=123)
    assert get_user(123) == user
```

### 3. Dependency Verification
```python
# ✅ GOOD: Verify dependencies before running
@pytest.fixture(scope="session", autouse=True)
def verify_dependencies():
    """Verify critical dependencies are installed."""
    try:
        import sentence_transformers
        import torch
    except ImportError as e:
        pytest.skip(f"Missing dependency: {e}")
```

---

## 📊 Success Metrics

### Testing Agent Should Achieve:
- **90%+ CI success rate** (vs 69% before Sprint 61 fixes)
- **<5% false positives** (CI fails that weren't caught locally)
- **<10 min pre-commit time** (fast feedback loop)
- **100% import coverage** (all new imports validated)

### Monthly Audit:
```bash
# 1. Check CI failure rate
gh run list --limit 50 --json conclusion --jq '.[] | select(.conclusion != "success") | length'

# 2. Analyze failure patterns
gh run list --limit 20 --json conclusion,url | grep failure

# 3. Update testing agent guidelines based on patterns
```

---

## 🎯 Testing Agent Configuration

### Recommended Tool Settings
```yaml
# .testing-agent.yml (proposed)
pre_commit:
  enabled: true
  checks:
    - linting (ruff + black + mypy)
    - import_validation
    - quick_tests (modified files only)

  thresholds:
    max_time: 600s  # 10 minutes
    min_coverage: 80%
    max_failures: 0

ci_simulation:
  enabled: false  # Optional, enable for critical PRs
  clean_env: true
  full_test_suite: true

auto_fix:
  linting: true   # Auto-run ruff --fix and black
  imports: false  # Manual review required
  tests: false    # Manual review required
```

---

## 📝 Documentation Updates

**Files to Update:**
1. `docs/CONVENTIONS.md` - Add testing guidelines
2. `.pre-commit-config.yaml` - Add testing hooks
3. `CONTRIBUTING.md` - Add pre-commit checklist
4. `README.md` - Add CI status badges

---

## ✅ Sprint 61 Lessons Learned Summary

1. **Import Validation:** Always test imports in clean environment
2. **Obsolete Tests:** Grep for feature references before committing
3. **Linting:** Run full linting suite (ruff + black + mypy) locally
4. **CI Workflows:** Verify dependency installation commands
5. **Disk Space:** Optimize artifact sizes and add cleanup steps

---

**Status:** ✅ Guidelines Complete
**Next Step:** Implement in testing-agent subagent
**Impact:** Prevent 90% of CI failures before they reach CI
**Maintenance:** Monthly audit and update based on new failure patterns
