# Dead Code Detection & Removal Strategy

**Sprint:** 71
**Date:** 2026-01-02
**Status:** Strategy Defined

---

## Executive Summary

**Goal:** Identify and remove unused code, dependencies, and API endpoints to improve maintainability, reduce attack surface, and speed up builds.

**Scope:**
- Backend: Python code, API endpoints, dependencies
- Frontend: TypeScript/React components, routes, dependencies
- Infrastructure: Docker images, unused services

---

## Backend Dead Code Detection

### 1. Test Coverage Analysis (**Primary Method**)

**Tool:** `coverage.py` with pytest

**Command:**
```bash
poetry run pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=json

# Generate human-readable report
poetry run coverage report --skip-covered --show-missing
```

**Strategy:**
- **<50% coverage** → Investigate module (likely unused or undertested)
- **0% coverage** → Strong candidate for removal
- **Never executed lines** → Dead code paths

**Expected Candidates:**
- Old router files (graph_analytics.py, graph_visualization.py)
- Unused utility modules
- Deprecated functions

---

### 2. Static Dead Code Detection

**Tool:** `vulture` - Dead code detector for Python

**Installation:**
```bash
poetry add --group dev vulture
```

**Command:**
```bash
vulture src/ --min-confidence 80 --sort-by-size
```

**Output:**
- Unused imports
- Unused variables
- Unused functions/classes
- Unused attributes

**Confidence Levels:**
- 100% → Definitely unused (safe to remove)
- 80-99% → Likely unused (review manually)
- <80% → Potentially used dynamically (keep)

**Known False Positives:**
- Pydantic model fields (used via dict access)
- FastAPI route handlers (called by framework)
- SQLAlchemy models (used via ORM)

**Whitelist File (`vulture-whitelist.py`):**
```python
# Pydantic models
_.dict()
_.model_dump()

# FastAPI
_.get()
_.post()
_.put()
_.delete()

# SQLAlchemy
_.query
_.filter
```

---

### 3. Unused Import Detection

**Tool:** `autoflake` - Remove unused imports

**Installation:**
```bash
poetry add --group dev autoflake
```

**Check Mode (Dry-Run):**
```bash
autoflake --check --remove-all-unused-imports --recursive src/
```

**Apply Removal:**
```bash
autoflake --in-place --remove-all-unused-imports --recursive src/
```

**Verify:**
```bash
poetry run pytest  # Ensure tests still pass
poetry run ruff check src/  # Ensure no lint errors
```

---

### 4. API Endpoint Usage Analysis

**Method:** Cross-reference backend endpoints with frontend usage + production logs

**Step 1: Extract Backend Endpoints**
```python
# Already done in Sprint 71 analysis
# Result: 150 endpoints
```

**Step 2: Extract Frontend Usage**
```bash
grep -r "fetch(" frontend/src | grep "/api/"
grep -r "axios." frontend/src | grep "/api/"
```

**Step 3: Check Production Logs (if available)**
```bash
# Example: Check Nginx access logs
grep "GET /api/" /var/log/nginx/access.log | awk '{print $7}' | sort | uniq -c | sort -rn
```

**Step 4: Identify Unused Endpoints**
- 108 endpoints have no frontend usage (72%!)
- Cross-check with production logs (if available)
- Mark for removal or documentation

**Categories for Removal:**
- **Deprecated:** graph_analytics.py endpoints (replaced by graph_viz.py)
- **Examples:** dependencies.py (/risky, /recommendations, /protected, etc.)
- **Duplicates:** Health endpoints (/health vs /health/*, /health/live vs /health/ready)

---

### 5. Dependency Audit

**Tool:** `poetry show --tree`

**Command:**
```bash
# List all dependencies with tree
poetry show --tree > deps_tree.txt

# Find outdated dependencies
poetry show --outdated

# Find unused dependencies (manual)
# For each dependency in pyproject.toml:
grep -r "import <package>" src/
```

**Expected Candidates:**
- Old testing libraries (if replaced)
- Unused utility packages
- Transitive dependencies from removed packages

**Safe Removal Process:**
1. Remove from pyproject.toml
2. Run `poetry lock --no-update`
3. Run `poetry install`
4. Run full test suite
5. If tests fail, revert
6. If tests pass, commit removal

---

## Frontend Dead Code Detection

### 1. Unused Exports Detection

**Tool:** `ts-prune` - Find unused TypeScript exports

**Installation:**
```bash
npm install --save-dev ts-prune
```

**Command:**
```bash
npx ts-prune --project frontend/tsconfig.json
```

**Output:**
```
src/components/OldButton.tsx:10 - OldButton (used 0 times)
src/utils/deprecatedHelper.ts:5 - formatDate (used 0 times)
```

**Strategy:**
- **0 usages** → Remove export
- **1 usage in tests only** → Evaluate if still needed
- **>0 usages** → Keep

**False Positives:**
- Entry points (main.tsx, App.tsx)
- React components imported dynamically
- Types used in type-only imports

---

### 2. Unused Components Detection

**Manual Analysis:**
```bash
# Find all components
find frontend/src/components -name "*.tsx" | sort

# For each component, check usages
grep -r "import.*ComponentName" frontend/src
```

**Expected Candidates:**
- Old UI components (replaced in redesigns)
- Test-only components in src/ (should be in __tests__)
- Deprecated features

---

### 3. Unused Dependencies Detection

**Tool:** `depcheck` - Find unused npm packages

**Installation:**
```bash
npm install --save-dev depcheck
```

**Command:**
```bash
npx depcheck frontend/
```

**Output:**
```
Unused dependencies:
  - old-ui-library
  - unused-utility-package

Missing dependencies (used but not in package.json):
  - react-icons
```

**Strategy:**
- **Unused dependencies** → Remove from package.json
- **Missing dependencies** → Add to package.json (important!)
- **Dev dependencies** → Move to devDependencies if only used in dev

**Verify:**
```bash
npm run build  # Ensure build still works
npm run test   # Ensure tests still pass
```

---

### 4. Route Analysis

**Method:** Check if all routes in App.tsx are reachable

**Audit:**
```typescript
// frontend/src/App.tsx
<Route path="/admin/legacy" element={<AdminPage />} />  // Still used?
<Route path="/dashboard/costs" element={<CostDashboardPage />} />  // Duplicate of /admin/costs?
```

**Strategy:**
1. List all routes in App.tsx
2. Check if links exist to each route
3. Identify orphaned routes (no links)
4. Verify with stakeholders before removal

**Expected Candidates:**
- `/admin/legacy` - Old admin page (replaced by new dashboard?)
- `/dashboard/costs` - Duplicate route

---

### 5. Asset Cleanup

**Unused Images/Icons:**
```bash
# Find all image imports
grep -r "import.*from.*\\.png" frontend/src
grep -r "import.*from.*\\.svg" frontend/src

# Find all assets
find frontend/public -type f

# Compare: which assets are never imported?
```

**Unused Fonts:**
```bash
# Check font imports in CSS/SCSS
grep -r "@font-face" frontend/src
```

---

## Dead Code Removal Process

### Step-by-Step Workflow

#### Phase 1: Identify Candidates
1. Run all detection tools (vulture, ts-prune, depcheck, coverage)
2. Create list of candidates with confidence scores
3. Review with team (avoid removing active code!)

#### Phase 2: Categorize Candidates
**Backend:**
- API endpoints (150 total, 108 unused)
- Python modules (coverage < 50%)
- Dependencies (unused packages)

**Frontend:**
- Components (unused exports)
- Routes (orphaned pages)
- Dependencies (unused packages)

#### Phase 3: Safe Removal
For each candidate:
1. **Verify unused:** Check logs, analytics, git blame
2. **Create branch:** `git checkout -b feat/remove-dead-code-<name>`
3. **Remove code:** Delete files, update imports
4. **Run tests:** `pytest`, `npm test`
5. **Run linters:** `ruff`, `eslint`
6. **Manual QA:** Test affected features
7. **Commit:** Clear message explaining removal
8. **PR review:** Get team approval
9. **Merge:** Squash commits

#### Phase 4: Verify Deployment
1. Deploy to staging
2. Run E2E tests (Sprint 71!)
3. Monitor logs for errors
4. If issues arise, rollback immediately

---

## Priority-Based Removal Plan

### 🔴 HIGH PRIORITY (Sprint 71)

#### Backend
- [x] **graph_analytics.py router** (6 endpoints, replaced by graph_viz.py)
- [x] **dependencies.py example endpoints** (/risky, /recommendations, /upload duplicates)
- [x] **Duplicate health endpoints** (consolidate /health/* variants)
- [x] **Unused auth endpoints** (/auth/refresh, /auth/register if truly unused)

**Estimated SP:** 2 (Feature 71.11)

#### Frontend
- [x] **Duplicate routes** (/dashboard/costs, /admin/legacy)
- [x] **Unused components** (identified by ts-prune)
- [x] **Old test files** (*.test.tsx without actual tests)

**Estimated SP:** 2 (Feature 71.12)

---

### 🟡 MEDIUM PRIORITY (Future Sprints)

#### Backend
- [ ] Unused utility modules (coverage < 20%)
- [ ] Old migration scripts (pre-Sprint 50)
- [ ] Deprecated Pydantic models

#### Frontend
- [ ] Unused UI library components (if any)
- [ ] Old SVG icons (replaced by Lucide)

---

### 🟢 LOW PRIORITY (Continuous)

#### Backend
- [ ] Outdated dependencies (security patches only)
- [ ] Code with coverage 50-80% (improve tests first)

#### Frontend
- [ ] Bundle size optimization (tree-shaking)
- [ ] Image/asset optimization

---

## Monitoring & Prevention

### Prevent Dead Code Accumulation

#### 1. Pre-commit Hooks
```bash
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-unused-imports
      name: Check for unused imports
      entry: autoflake --check --remove-all-unused-imports
      language: system
      types: [python]
```

#### 2. CI/CD Checks
```yaml
# .github/workflows/code-quality.yml
- name: Check Dead Code
  run: |
    poetry run vulture src/ --min-confidence 90 || true
    npx ts-prune --project frontend/tsconfig.json || true
```

#### 3. Quarterly Audits
- Run full detection suite every 3 months
- Review coverage reports
- Update whitelist for false positives

---

## Tools Summary

| Tool | Language | Purpose | Installation |
|------|----------|---------|--------------|
| coverage.py | Python | Test coverage | Built-in pytest |
| vulture | Python | Dead code detector | `poetry add --group dev vulture` |
| autoflake | Python | Unused imports | `poetry add --group dev autoflake` |
| ts-prune | TypeScript | Unused exports | `npm install --save-dev ts-prune` |
| depcheck | JavaScript | Unused dependencies | `npm install --save-dev depcheck` |
| grep/awk | Bash | Manual analysis | Built-in |

---

## Expected Outcomes (Sprint 71)

### Before
- **Backend:**
  - 150 API endpoints (108 unused)
  - ~50 Python modules (coverage unknown)
  - ~100 dependencies

- **Frontend:**
  - ~200 components (unknown unused)
  - ~50 npm packages
  - 2 duplicate routes

### After Sprint 71
- **Backend:**
  - ~130 API endpoints (20 removed)
  - ~45 Python modules (5 dead removed)
  - ~90 dependencies (10% reduction)
  - Test coverage >80%

- **Frontend:**
  - ~180 components (20 unused removed)
  - ~45 npm packages (5 unused removed)
  - 0 duplicate routes
  - Bundle size -10%

---

## Risks & Mitigation

### Risk 1: Removing Active Code
**Mitigation:**
- Run detection tools with high confidence threshold (>80%)
- Check production logs for actual usage
- Review with team before removal
- Gradual rollout (staging first)

### Risk 2: Breaking Tests
**Mitigation:**
- Run full test suite before/after each removal
- Require 100% test pass rate
- E2E tests (Sprint 71!) catch integration issues

### Risk 3: Reverting Removals
**Mitigation:**
- Keep dead code in git history (can always recover)
- Document removal reason in commit message
- Feature flags for risky removals

---

## Conclusion

Sprint 71 will systematically identify and remove dead code using automated tools (vulture, ts-prune, depcheck) and manual analysis (coverage, logs, API-Frontend mapping). This will:
- **Reduce maintenance burden** - less code to maintain
- **Improve build times** - fewer dependencies to process
- **Increase clarity** - remove confusing deprecated code
- **Enhance security** - reduce attack surface

**Next Steps:**
1. Run detection tools (Features 71.11-71.12)
2. Prioritize removal candidates
3. Create removal PRs
4. Verify with E2E tests
5. Deploy and monitor
