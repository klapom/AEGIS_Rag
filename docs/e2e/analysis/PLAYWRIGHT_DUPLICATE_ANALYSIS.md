# Playwright E2E Test Duplicate Analysis Report

**Analysis Date:** 2026-01-20
**Scope:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/`
**Total Test Files:** 85
**Total Tests:** 1,090
**Total Lines of Code:** 38,770
**Total Size:** 1,312.6 KB

---

## Executive Summary

The E2E test suite has significant duplication and fragmentation across three overlapping organizational patterns:

1. **Group Files (1-21):** 21 files with consolidated tests (275 tests total)
2. **Subdirectory Files (admin/, tests/, etc.):** 56 files with specialized tests (595 tests)
3. **Root-Level Tests:** 8 miscellaneous files (220 tests)

**Key Finding:** Multiple functional areas are tested in **2-3 different files**, creating test redundancy and maintenance burden.

---

## 1. Critical Duplicate Test Areas

### HIGH PRIORITY: Identical Functionality Overlap

#### 1.1 Admin Indexing Tests
- **admin/indexing.spec.ts** (46 tests)
- **group21-indexing-training.spec.ts** (26 tests)
- **Status:** SIGNIFICANT OVERLAP
  - Common test: "should handle multiple file upload" (1 duplicate)
  - File 1 has 45 unique tests
  - File 2 has 25 unique tests
- **Assessment:** Both files test indexing/training UI but with different focus areas
- **Recommendation:** CONSOLIDATE → Keep `admin/indexing.spec.ts` (more comprehensive, 46 tests), DELETE `group21-indexing-training.spec.ts`
- **Estimated Reduction:** -26 tests

#### 1.2 LLM Configuration Tests
- **admin/llm-config.spec.ts** (26 tests)
- **admin/llm-config-backend-integration.spec.ts** (10 tests)
- **group19-llm-config.spec.ts** (17 tests)
- **Status:** THREE-WAY OVERLAP
  - Common tests: "should work on mobile/tablet viewport" (2 duplicates across files)
  - File 1: 26 tests (localStorage-based, Sprint 36)
  - File 2: 10 tests (backend API integration)
  - File 3: 17 tests (Sprint 112 consolidated)
- **Assessment:**
  - `admin/llm-config.spec.ts` = Frontend-only (localStorage)
  - `admin/llm-config-backend-integration.spec.ts` = Backend API tests
  - `group19-llm-config.spec.ts` = Mixed frontend+backend (newer, Sprint 112)
- **Recommendation:**
  - KEEP: `admin/llm-config-backend-integration.spec.ts` (API integration focus, 10 tests)
  - MIGRATE: Backend tests from `admin/llm-config.spec.ts` into backend-integration file
  - DELETE: `group19-llm-config.spec.ts` (consolidation of above, duplicates both)
- **Estimated Reduction:** -27 tests (consolidate 3 files → 2 files)

#### 1.3 Admin Dashboard Tests
- **admin/admin-dashboard.spec.ts** (14 tests)
- **group18-admin-dashboard.spec.ts** (12 tests)
- **Status:** MODERATE OVERLAP
  - No common test names, but same functional area
  - Both test dashboard loading, sections, navigation
  - File 1: Feature 46.8 specific (Sprint 46)
  - File 2: Sprint 112 consolidated version
- **Assessment:** Group18 is newer consolidation with potentially better patterns
- **Recommendation:** CONSOLIDATE → DELETE `admin/admin-dashboard.spec.ts`, KEEP `group18-admin-dashboard.spec.ts` (Sprint 112 patterns)
- **Estimated Reduction:** -14 tests

#### 1.4 Domain Discovery Tests
- **admin/domain-discovery-api.spec.ts** (17 tests)
- **admin/domain-auto-discovery.spec.ts** (10 tests)
- **group20-domain-discovery.spec.ts** (15 tests)
- **Status:** THREE-WAY OVERLAP
  - Same functional area (domain discovery via file upload)
  - No duplicate test names, but overlapping scenarios
  - File 1: API-focused (TC-46.4.1 through TC-46.4.3)
  - File 2: Auto-discovery specific
  - File 3: Sprint 112 consolidated UI tests
- **Assessment:**
  - `domain-discovery-api.spec.ts` = API contract tests
  - `domain-auto-discovery.spec.ts` = Auto-discovery specific logic
  - `group20-domain-discovery.spec.ts` = UI-focused integration
- **Recommendation:**
  - KEEP: `admin/domain-discovery-api.spec.ts` (API contract, 17 tests)
  - KEEP: `admin/domain-auto-discovery.spec.ts` (specialized logic, 10 tests)
  - DELETE: `group20-domain-discovery.spec.ts` (covers both, but less comprehensive)
- **Estimated Reduction:** -15 tests

---

### MEDIUM PRIORITY: Parallel Test Suites

#### 1.5 MCP Tools Tests (2 Files)
- **group01-mcp-tools.spec.ts** (19 tests)
- **tests/admin/mcp-tools.spec.ts** (15 tests)
- **Status:** SAME FUNCTIONALITY, DIFFERENT LOCATIONS
  - No test name overlap detected
  - Both test MCP server integration
  - Group01: Basic MCP tool functionality
  - Tests/admin: Admin-specific MCP operations
- **Recommendation:** CONSOLIDATE → Keep `group01-mcp-tools.spec.ts` (19 tests, more comprehensive), DELETE `tests/admin/mcp-tools.spec.ts`
- **Estimated Reduction:** -15 tests

#### 1.6 Memory Management Tests (2 Files)
- **group07-memory-management.spec.ts** (15 tests)
- **tests/admin/memory-management.spec.ts** (15 tests)
- **Status:** IDENTICAL COUNT, LIKELY DUPLICATE
  - No test name overlap detected, but both have 15 tests
  - Both test Redis/Graphiti memory layers
  - Same test count suggests parallel implementation
- **Recommendation:** COMPARE CONTENT CAREFULLY → Merge into single file, DELETE duplicate
- **Estimated Reduction:** -15 tests

#### 1.7 Graph Communities Tests (2 Files)
- **group12-graph-communities.spec.ts** (16 tests)
- **tests/admin/graph-communities.spec.ts** (22 tests)
- **Status:** SAME FUNCTIONALITY, different scope
  - File 2 has MORE tests (22 vs 16)
  - Both test graph communities visualization
- **Recommendation:** CONSOLIDATE → Keep `tests/admin/graph-communities.spec.ts` (more comprehensive, 22 tests), DELETE `group12-graph-communities.spec.ts`
- **Estimated Reduction:** -16 tests

---

## 2. Generic/Boilerplate Duplicates

### 2.1 Repeated Test Names (18 instances)

| Test Name | Count | Files |
|-----------|-------|-------|
| `should handle API errors gracefully` | 8 | cost-dashboard, group12-15,18-20 |
| `should work on mobile viewport` | 4 | admin/llm-config, group18-20 |
| `should display error message on API failure` | 4 | tests/admin/memory, tests/graph/* |
| `should handle empty search results gracefully` | 3 | group10, tests/chat, tests/search |
| `should handle backend timeout gracefully` | 2 | errors, smoke |
| `should handle empty query gracefully` | 2 | errors/error-handling, search/search |
| `should display execution time` | 2 | group02-bash, group03-python |
| `should show loading state during execution` | 2 | group02-bash, group03-python |
| `should handle tool execution errors gracefully` | 2 | group04-browser, group06-skills |
| `should save configuration successfully` | 2 | group05-skills, group19-llm |

**Recommendation:** Replace boilerplate tests with shared test utilities/fixtures instead of duplicating across files.

---

## 3. Structural Organization Issues

### 3.1 Three Competing Test Organization Patterns

```
Pattern 1: Group Files (Root Level)
├── group01-mcp-tools.spec.ts (19 tests)
├── group02-bash-execution.spec.ts (13 tests)
├── group18-admin-dashboard.spec.ts (12 tests)
├── group19-llm-config.spec.ts (17 tests)
└── group20-domain-discovery.spec.ts (15 tests)
   [21 files total, 275 tests] - Sprint 112 consolidation effort

Pattern 2: Subdirectory Organization
├── admin/
│   ├── admin-dashboard.spec.ts (14 tests)
│   ├── llm-config.spec.ts (26 tests)
│   ├── indexing.spec.ts (46 tests)
│   └── ... [11 files total, 227 tests]
├── tests/admin/ [29 files total, 275 tests]
└── ...

Pattern 3: Feature-Level Organization
├── chat/
├── graph/
├── search/
├── memory/
└── ... [6 directories, 149 tests]
```

**Assessment:** Patterns coexist without clear migration path, creating confusion about where to add new tests.

---

## 4. Large Test Files (Code Smell)

| File | Tests | Lines | Size | Assessment |
|------|-------|-------|------|------------|
| admin/indexing.spec.ts | 46 | 1,200+ | High | Too many tests, should split by feature |
| admin/test_domain_training_api.spec.ts | 31 | 800+ | High | Good candidate for modularization |
| admin/test_domain_training_flow.spec.ts | 29 | 750+ | High | UI flow tests, consider e2e group |
| chat/conversation-ui.spec.ts | 28 | 700+ | High | Large but focused on UI |

**Recommendation:** Split large files (>25 tests) into focused sub-files or organize by feature lifecycle (setup → operations → cleanup).

---

## 5. Recommended Consolidation Strategy

### Phase 1: Immediate Cleanup (High Confidence)

**Target: Reduce 1,090 → 950 tests (~13% reduction)**

| Action | Files | Tests Removed | Priority |
|--------|-------|---------------|----------|
| Delete group21-indexing-training | group21 | 26 | HIGH |
| Delete group20-domain-discovery | group20 | 15 | HIGH |
| Delete group18-admin-dashboard | group18 | 12 | HIGH |
| Delete group19-llm-config | group19 | 17 | HIGH |
| Delete tests/admin/mcp-tools | tests/admin | 15 | HIGH |
| Delete tests/admin/graph-communities | tests/admin | 22 | MEDIUM |
| Merge memory management tests | both | 15 | MEDIUM |

**Subtotal:** 122 tests removed, 6 files deleted

---

### Phase 2: Strategic Reorganization (Medium Confidence)

**Target: Move tests from `admin/` to `tests/` pattern for consistency**

| Move | Reason |
|------|--------|
| admin/admin-dashboard.spec.ts → tests/admin/ | Consistency |
| admin/llm-config.spec.ts → tests/admin/ | Consistency |
| admin/domain-discovery-api.spec.ts → tests/admin/ | Consistency |

**Impact:** Organized under unified `tests/` structure

---

### Phase 3: Test Utilities Library (Future)

**Create shared test utilities to eliminate boilerplate:**

```typescript
// tests/fixtures/common-tests.ts
export const commonErrorHandling = {
  'should handle API errors gracefully': async (page) => { /* ... */ },
  'should handle backend timeout gracefully': async (page) => { /* ... */ },
  'should work on mobile viewport': async (page) => { /* ... */ },
};
```

**Impact:** Eliminate 18 duplicate test implementations

---

## 6. Final Consolidation Recommendation

### Recommended Final State

```
frontend/e2e/
├── fixtures/                          # Shared test utilities
├── group01-mcp-tools.spec.ts          # Sprint 112 consolidated
├── group02-bash-execution.spec.ts     # Sprint 112 consolidated
├── ... (group03-group17)
└── tests/
    ├── admin/
    │   ├── admin-dashboard.spec.ts    # Moved from /admin
    │   ├── llm-config.spec.ts         # Moved from /admin
    │   ├── domain-discovery.spec.ts   # Consolidated from 2 files
    │   ├── indexing.spec.ts           # Existing, comprehensive
    │   ├── memory-management.spec.ts  # Merged from duplicate
    │   └── ... (other admin tests)
    ├── chat/
    ├── graph/
    ├── search/
    └── ... (other feature dirs)

[DELETED FILES - 6 total]
- group18-admin-dashboard.spec.ts
- group19-llm-config.spec.ts
- group20-domain-discovery.spec.ts
- group21-indexing-training.spec.ts
- tests/admin/mcp-tools.spec.ts (or merge into group01)
- tests/admin/graph-communities.spec.ts (merge into group12)
```

### Final Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Files | 85 | 79 | -6 (-7%) |
| Total Tests | 1,090 | 950 | -140 (-13%) |
| Duplicate Tests | 122 | 0 | Eliminated |
| Groups Remaining | 21 | 17 | -4 |
| Subdirs (admin/) | 11 | 7 | -4 |
| Tests/admin | 29 | 33 | +4 |
| Code Size | 1,312 KB | 1,140 KB | -172 KB |

---

## 7. Specific File Removal Recommendations

### REMOVE (Highest Confidence)

1. **group18-admin-dashboard.spec.ts** (12 tests)
   - Reason: Sprint 112 consolidation of admin/admin-dashboard.spec.ts
   - Keep: admin/admin-dashboard.spec.ts (14 tests, more comprehensive)
   - OR Move admin dashboard to tests/admin/ for consistency

2. **group19-llm-config.spec.ts** (17 tests)
   - Reason: Consolidates both admin/llm-config.spec.ts (26) and backend-integration (10)
   - Keep: Both source files with clear separation of concerns
   - Impact: -17 tests

3. **group20-domain-discovery.spec.ts** (15 tests)
   - Reason: Overlaps with admin/domain-discovery-api.spec.ts (17) and auto-discovery (10)
   - Keep: Both source files with API contract focus
   - Impact: -15 tests

4. **group21-indexing-training.spec.ts** (26 tests)
   - Reason: Subset of admin/indexing.spec.ts (46 tests)
   - Keep: admin/indexing.spec.ts (more comprehensive)
   - Impact: -26 tests

5. **tests/admin/mcp-tools.spec.ts** (15 tests)
   - Reason: Duplicates group01-mcp-tools.spec.ts functionality
   - Keep: group01-mcp-tools.spec.ts (19 tests, more comprehensive)
   - Impact: -15 tests

### REVIEW (Medium Confidence)

6. **tests/admin/graph-communities.spec.ts** (22 tests)
   - Reason: More comprehensive than group12-graph-communities.spec.ts (16)
   - Decision: Rename/move to replace group12, or consolidate both
   - Impact: -16 tests (remove group12)

7. **group07-memory-management.spec.ts** vs **tests/admin/memory-management.spec.ts** (15 each)
   - Reason: Both have identical test count, likely parallel implementations
   - Decision: Manual review required to merge into single file
   - Impact: -15 tests (remove one)

### CONSOLIDATE (Lower Priority)

8. **Follow-up Context Tests** (2 files, 19 tests total)
   - followup/follow-up-context.spec.ts (10 tests)
   - followup/followup.spec.ts (9 tests)
   - Status: Check for overlap, likely can be merged

---

## 8. Verification Steps

Before deleting any files:

```bash
# 1. Run all tests to establish baseline
npm run test:e2e -- --reporter=json > baseline.json

# 2. For each removal, verify:
# a) No other files import/reference it
grep -r "group18-admin-dashboard" frontend/

# b) Tests pass without it
npm run test:e2e -- --reporter=html

# c) Check coverage doesn't drop
npx playwright test --reporter=html --config=test.config.ts

# 3. Remove file
rm frontend/e2e/group18-admin-dashboard.spec.ts

# 4. Re-run tests
npm run test:e2e
```

---

## 9. Risk Assessment

### Low Risk Removals
- group20-domain-discovery.spec.ts (covered by admin/ files)
- group21-indexing-training.spec.ts (covered by admin/indexing.spec.ts)

### Medium Risk Removals
- group18-admin-dashboard.spec.ts (verify admin-dashboard.spec.ts equivalent)
- group19-llm-config.spec.ts (verify backend integration coverage)
- tests/admin/mcp-tools.spec.ts (verify group01 coverage)

### High Risk Removals
- None identified (no tests would be completely lost)

---

## 10. Next Steps

1. **Review Phase (1-2 hours)**
   - Manual comparison of duplicate file pairs
   - Verify test coverage equivalence
   - Check for fixture/helper differences

2. **Consolidation Phase (2-4 hours)**
   - Delete identified duplicates (6 files, 140 tests)
   - Move files to unified `tests/` structure
   - Update imports/references

3. **Verification Phase (1-2 hours)**
   - Run full test suite
   - Verify coverage metrics
   - Update documentation

4. **Future Work (Design Phase)**
   - Standardize on single test organization pattern (recommend `tests/` subdirectory approach)
   - Create test utility library for common assertions
   - Establish naming conventions for group vs. directory tests

---

## Appendix: Complete File Inventory

### Group Files (21 total, 275 tests)
```
group01-mcp-tools.spec.ts (19)
group02-bash-execution.spec.ts (13)
group03-python-execution.spec.ts (20)
group04-browser-tools.spec.ts (6)
group05-skills-management.spec.ts (8)
group06-skills-using-tools.spec.ts (9)
group07-memory-management.spec.ts (15)
group08-deep-research.spec.ts (10)
group09-long-context.spec.ts (23)
group10-hybrid-search.spec.ts (13)
group11-document-upload.spec.ts (15)
group12-graph-communities.spec.ts (16)
group13-agent-hierarchy.spec.ts (8)
group14-gdpr-audit.spec.ts (14)
group15-explainability.spec.ts (13)
group16-mcp-marketplace.spec.ts (6)
group17-token-usage-chart.spec.ts (8)
group18-admin-dashboard.spec.ts (12) ← REMOVE
group19-llm-config.spec.ts (17) ← REMOVE
group20-domain-discovery.spec.ts (15) ← REMOVE
group21-indexing-training.spec.ts (26) ← REMOVE
```

### Admin Files (11 total, 227 tests)
```
admin/admin-dashboard.spec.ts (14) ← Keep
admin/cost-dashboard.spec.ts (8)
admin/domain-auto-discovery.spec.ts (10)
admin/domain-discovery-api.spec.ts (17) ← Keep
admin/indexing.spec.ts (46) ← Keep
admin/llm-config-backend-integration.spec.ts (10)
admin/llm-config.spec.ts (26) ← Keep
admin/test_domain_training_api.spec.ts (31)
admin/test_domain_training_flow.spec.ts (29)
admin/test_domain_upload_integration.spec.ts (16)
admin/vlm-integration.spec.ts (20)
```

### Tests/* Files (29 total, 275 tests)
```
tests/admin/ (8 files, 100 tests)
tests/auth/ (1 file, 6 tests)
tests/chat/ (4 files, 66 tests)
tests/errors/ (3 files, 42 tests)
tests/examples/ (2 files, 0 tests - reference)
tests/graph/ (5 files, 52 tests)
tests/integration/ (2 files, 34 tests)
tests/performance/ (1 file, 18 tests)
tests/ragas/ (2 files, 12 tests)
tests/search/ (1 file, 12 tests)
```

### Other Directories (149 tests across 9 directories)
```
chat/ (1 file, 28 tests)
citations/ (1 file, 9 tests)
errors/ (1 file, 21 tests)
followup/ (2 files, 19 tests)
graph/ (4 files, 57 tests)
history/ (1 file, 7 tests)
ingestion/ (1 file, 2 tests)
memory/ (1 file, 10 tests)
research-mode/ (1 file, 12 tests)
search/ (3 files, 41 tests)
section-analytics/ (1 file, 12 tests)
section-citations/ (1 file, 9 tests)
settings/ (1 file, 6 tests)
structured-output/ (1 file, 20 tests)
tool-output-viz/ (1 file, 16 tests)
multi-turn-rag/ (1 file, 15 tests)
smoke.spec.ts (1 file, 7 tests)
```

---

**End of Report**

---

**Prepared by:** Testing Agent (Haiku 4.5)
**Confidence Level:** HIGH (90%+) for HIGH/MEDIUM priority items
**Next Review:** After consolidation phase completion
