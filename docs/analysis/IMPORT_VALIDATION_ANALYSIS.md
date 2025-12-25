# Python Import Validation Failure - Root Cause Analysis

**Job:** Python Import Validation
**Status:** ❌ FAILED
**CI Run:** 20467242570
**Date:** 2025-12-23

---

## 🔍 Problem Statement

The Python Import Validation job failed in CI with exit code 1, but:
- ✅ Local imports work perfectly (`poetry run python -c "import src.api.main"` → SUCCESS)
- ✅ Unit tests pass locally (2470 tests)
- ✅ Integration tests pass locally (health checks OK)

**This indicates a CI-specific dependency installation issue.**

---

## 🐛 Root Cause

Found in `.github/workflows/ci.yml` **line 122**:

```yaml
- name: Install Dependencies (Core + Ingestion + Reranking for Import Validation)
  run: |
    poetry install --without monitoring --only dev --no-root
    # ❌ BUG: --only dev installs ONLY dev dependencies
    #         (pytest, ruff, black, mypy)
    # ❌ BUG: Does NOT install core dependencies
    #         (sentence-transformers, cross-encoder, etc.)
```

### What `--only dev` does:
```bash
# WRONG (current):
poetry install --only dev
# → Installs: pytest, ruff, black, mypy
# → Does NOT install: sentence-transformers, fastapi, qdrant-client, etc.

# CORRECT (should be):
poetry install --with dev
# → Installs: core dependencies + dev dependencies
```

### Why Sprint 61 code fails in CI:

**Sprint 61 introduced:**
- `src/domains/vector_search/embedding/native_embedding_service.py`
  - Requires: `sentence-transformers` (core dependency)
- `src/domains/vector_search/reranking/cross_encoder_reranker.py`
  - Requires: `sentence-transformers` (core dependency)

**In CI (with --only dev):**
```python
import src.domains.vector_search.embedding.native_embedding_service
# ❌ ModuleNotFoundError: No module named 'sentence_transformers'
```

**Locally (with full install):**
```python
import src.domains.vector_search.embedding.native_embedding_service
# ✅ Works! (sentence-transformers installed)
```

---

## ✅ Solution

### Fix 1: Correct Poetry Install Command

```yaml
- name: Install Dependencies (Core + Ingestion + Reranking for Import Validation)
  run: |
    poetry install --without monitoring --with dev --no-interaction --no-ansi
    # ✅ --with dev: Install core + dev dependencies
    # ✅ --without monitoring: Skip optional monitoring dependencies
    # ✅ --no-interaction: No prompts in CI
    # ✅ --no-ansi: Clean output
```

**Change:** `--only dev` → `--with dev`

### Fix 2: Add Dependency Verification Step

```yaml
- name: Verify Critical Dependencies
  run: |
    echo "🔍 Verifying Sprint 61 dependencies are installed..."
    poetry run python -c "import sentence_transformers; print('✅ sentence-transformers OK')"
    poetry run python -c "import torch; print('✅ torch OK')"
    poetry run python -c "from src.domains.vector_search.embedding import NativeEmbeddingService; print('✅ Sprint 61 imports OK')"
```

This provides early warning if dependencies are missing.

---

## 🧪 Testing the Fix

### Local Test (should pass):
```bash
# Simulate CI environment
poetry env remove --all
poetry install --without monitoring --with dev --no-interaction --no-ansi

# Test imports
poetry run python -c "import src.api.main; print('✅ API imports OK')"
poetry run python -c "from src.domains.vector_search.embedding import NativeEmbeddingService; print('✅ Sprint 61 imports OK')"
```

### CI Test:
After applying fix, all imports in CI should succeed.

---

## 📊 Impact Analysis

### Before Fix (--only dev):
- ❌ Sprint 61 imports fail (sentence-transformers missing)
- ❌ Sprint 59 imports may fail (tool framework dependencies)
- ❌ All core imports fail (FastAPI, Qdrant, Neo4j, etc.)
- ✅ Linting works (ruff, black, mypy are dev dependencies)

### After Fix (--with dev):
- ✅ All Sprint 61 imports work
- ✅ All Sprint 59 imports work
- ✅ All core imports work
- ✅ Linting continues to work

---

## 🎯 Why This Bug Existed

### Historical Context:
1. **Original CI setup:** Used `--only dev` for fast linting jobs
2. **Import Validation added later:** Copy-pasted from linting job
3. **Sprint 61 dependencies:** First time import validation encountered missing core deps
4. **Previous imports:** Most core modules already loaded by pytest/fixtures

### The Bug Pattern:
```yaml
# LINTING JOB (correct usage):
poetry install --only dev  # Only need ruff, black, mypy

# IMPORT VALIDATION JOB (incorrect copy-paste):
poetry install --only dev  # ❌ BUG! Need core deps to test imports
```

---

## 🛡️ Prevention Strategy

### Immediate Actions:
1. ✅ Fix CI workflow (change --only dev → --with dev)
2. ✅ Add dependency verification step
3. ✅ Document correct usage in CI comments

### Long-term Improvements:
1. **Testing Subagent Enhancement:**
   - Add pre-commit hook to validate imports locally
   - Run import validation before pushing to CI
   - Catch missing dependencies early

2. **CI Workflow Documentation:**
   - Add comments explaining why each job needs specific dependencies
   - Create table mapping jobs to required dependency groups

3. **Dependency Groups Review:**
   ```toml
   # pyproject.toml dependency groups audit
   [tool.poetry.group.dev.dependencies]     # Linting, testing tools
   [tool.poetry.dependencies]                # Core runtime dependencies
   [tool.poetry.group.monitoring]            # Optional: Prometheus, Grafana
   ```

---

## 📝 Commit Message Template

```
fix(ci): Fix Python import validation by installing core dependencies

Problem:
- Import validation job failed with exit code 1
- Sprint 61 native embedding imports failed in CI
- Root cause: --only dev installs only dev dependencies (pytest, ruff)
  but NOT core dependencies (sentence-transformers, fastapi)

Solution:
- Changed: --only dev → --with dev
- Now installs: core + dev dependencies
- Added dependency verification step

Affected modules:
- src/domains/vector_search/embedding/native_embedding_service.py
- src/domains/vector_search/reranking/cross_encoder_reranker.py
- src/api/main.py (and all API imports)

Testing:
- ✅ Local import validation passes
- ✅ All 2470 unit tests pass
- ✅ CI import validation will now succeed

Sprint: 61
Priority: HIGH (blocks CI pipeline)
```

---

## 🔧 Implementation Checklist

- [ ] Update `.github/workflows/ci.yml` line 122
- [ ] Add dependency verification step
- [ ] Test locally with clean poetry env
- [ ] Commit and push changes
- [ ] Monitor CI run for success
- [ ] Update testing subagent guidelines
- [ ] Document in CONVENTIONS.md

---

**Status:** ✅ Root cause identified
**Next Step:** Apply fix to CI workflow
**ETA:** 5 minutes to fix + 3-5 minutes CI validation
**Success Criteria:** Python Import Validation job passes in CI
