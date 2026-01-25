# Sprint 119 Plan: Skipped E2E Test Analysis & Stabilization

**Date:** 2026-01-25
**Status:** 📝 In Progress
**Total Story Points:** 35 SP (estimated)
**Predecessor:** Sprint 118 (Testing Infrastructure & Bug Fixes)
**Successor:** Sprint 120 (Visual Regression / Performance Tests)

---

## Executive Summary

Sprint 119 focuses on **analyzing and fixing skipped E2E tests**. Sprint 118 successfully fixed 9 critical bugs (17 SP) but deferred infrastructure features. This sprint will:

1. **Analyze all skipped tests** - Categorize by reason (feature missing, API missing, data dependency)
2. **Enable or fix viable tests** - Tests that should work but don't
3. **Document technical debt** - Create TDs for tests requiring new features
4. **Carry-over features** - Visual regression, performance tests from Sprint 118

---

## Skipped Test Analysis (Sprint 119.1)

### Summary of Skipped Tests

| Category | Test Files | Tests | Reason | Action |
|----------|------------|-------|--------|--------|
| **Graph Versioning** | time-travel.spec.ts, entity-changelog.spec.ts, version-compare.spec.ts | 28 | Features 39.5-39.7 not implemented | Keep skipped (TD) |
| **Domain Training API** | test_domain_training_api.spec.ts | 31 | API endpoints not implemented | Keep skipped (TD) |
| **Performance Regression** | performance-regression.spec.ts | ~15 | Metrics endpoints missing | Analyze & fix |
| **Citations** | citations.spec.ts | 7 | Citation rendering issues | Analyze & fix |
| **Bash Execution** | group02-bash-execution.spec.ts | 5 | Security sandbox feature | Keep skipped |
| **Deep Research** | group08-deep-research.spec.ts | 3 | Slow/timeout issues | Increase timeout |
| **MCP Tools** | group01-mcp-tools.spec.ts | 4 | Tool integration | Analyze & fix |

**Total Skipped:** ~93 tests

---

## Feature Breakdown

### Primary Objectives (Sprint 119)

| Feature | Category | SP | Priority |
|---------|----------|----|---------:|
| Skipped Test Analysis | Testing | 5 | CRITICAL |
| Performance Regression Test Enablement | Testing | 8 | HIGH |
| Citations Test Fix | Testing | 5 | HIGH |
| MCP Tools Test Fix | Testing | 3 | MEDIUM |

### Carry-Over from Sprint 118

| Feature | Category | SP | Priority |
|---------|----------|----|---------:|
| Visual Regression Framework | Infrastructure | 5 | HIGH |
| Performance Regression Tests (full) | Infrastructure | 13 | HIGH |
| Graph Communities UI | Frontend | 5 | MEDIUM |
| admin/memory-management.spec.ts Fix | Bug | 3 | MEDIUM |

---

## Skipped Test Categories

### 1. Graph Versioning (28 tests) - KEEP SKIPPED

**Files:**
- `tests/graph/time-travel.spec.ts` - Feature 39.5
- `tests/graph/entity-changelog.spec.ts` - Feature 39.6
- `tests/graph/version-compare.spec.ts` - Feature 39.7

**Reason:** These features are planned but not implemented. Tests are correctly marked `test.describe.skip()`.

**Action:** Create TD-119.1 for Graph Versioning feature implementation.

---

### 2. Domain Training API (31 tests) - KEEP SKIPPED

**File:** `admin/test_domain_training_api.spec.ts`

**Reason:** 8 test.describe.skip blocks covering:
- Basic Operations
- Classification
- Domain Auto-Discovery
- Training Data Augmentation
- Batch Ingestion
- Domain Detail Operations
- Input Validation
- Response Format Validation

**Action:** Tests require full Domain Training API (Sprint 117 feature). Keep skipped.

---

### 3. Performance Regression (~15 tests) - ANALYZE

**File:** `tests/integration/performance-regression.spec.ts`

**Tests skipped due to:**
- Missing metrics endpoints (`/admin/metrics`)
- Missing upload functionality
- Missing admin pages

**Sprint 119 Action:** Enable tests where endpoints exist, skip only truly missing features.

---

### 4. Citations (7 tests) - FIX

**File:** `citations/citations.spec.ts`

**Tests skip when:**
- Citation elements not found in response
- Missing `data-testid` attributes

**Sprint 119 Action:** Verify citation rendering, add missing test IDs.

---

### 5. Bash Execution (5 tests) - KEEP SKIPPED

**File:** `group02-bash-execution.spec.ts`

**Reason:** Security sandbox feature not exposed in UI. These tests are for future agentic capabilities.

**Action:** Keep skipped until Bash execution UI implemented.

---

### 6. Deep Research (3 tests) - FIX TIMEOUTS

**File:** `group08-deep-research.spec.ts`

**Issue:** Tests timeout after 60s but Deep Research takes 30-120s.

**Sprint 119 Action:** Increase timeout to 180s, add @full tag.

---

### 7. MCP Tools (4 tests) - ANALYZE

**File:** `group01-mcp-tools.spec.ts`

**Tests skip when:**
- MCP tool panels not found
- Server connection fails

**Sprint 119 Action:** Verify MCP server running, fix selectors.

---

## Execution Plan

### Phase 1: Analysis (Day 1)
- [ ] Run all skipped tests, capture exact failure reasons
- [ ] Categorize by: Feature Missing, API Missing, Data Dependency, Bug
- [ ] Document in this plan

### Phase 2: Quick Fixes (Day 2-3)
- [ ] Fix timeout-related skips (Deep Research, Long Context)
- [ ] Add missing data-testids (Citations, MCP)
- [ ] Enable tests where APIs exist (Performance subset)

### Phase 3: Documentation (Day 4)
- [ ] Create TDs for feature-missing tests
- [ ] Update PLAYWRIGHT_E2E.md with skip reasons
- [ ] Final test run and metrics

---

## Sprint 119 Execution Notes

### Test Analysis Results (2026-01-25)

**Analysis Status:** ✅ Complete

| Test File | Total | Pass | Fail | Skip | Notes |
|-----------|-------|------|------|------|-------|
| **time-travel.spec.ts** | 9 | 0 | 0 | 9 | Feature 39.5 not implemented |
| **entity-changelog.spec.ts** | 9 | 0 | 0 | 9 | Feature 39.6 not implemented |
| **version-compare.spec.ts** | 10 | 0 | 0 | 10 | Feature 39.7 not implemented |
| **test_domain_training_api.spec.ts** | 31 | 0 | 0 | 31 | API not implemented |
| **citations.spec.ts** | 9 | 4 | 0 | 5 | **4 pass!** Skips are conditional (no citations in response) |
| **group02-bash-execution.spec.ts** | ~6 | 0 | 0 | 6 | Security sandbox not exposed in UI |
| **group08-deep-research.spec.ts** | 3 | 0 | 0 | 3 | Timeout issues (30-120s research) |
| **performance-regression.spec.ts** | ~15 | 0 | 0 | 15 | Metrics endpoints missing |

### Key Findings

#### ✅ Tests that PASS (can be unskipped)
1. **citations.spec.ts** - 4 tests pass, 5 skip only when no citations in response
   - These are self-skipping based on response content (correct behavior)

#### ⏸️ Tests Correctly Skipped (feature not implemented)
1. **Graph Versioning** (28 tests) - Features 39.5-39.7 not implemented
2. **Domain Training API** (31 tests) - Full API not exposed
3. **Bash Execution** (6 tests) - Security sandbox not in UI

#### 🔧 Tests that Need Fixes
1. **group08-deep-research.spec.ts** - Increase timeout to 180s
2. **performance-regression.spec.ts** - Some tests can be enabled with existing APIs

---

## References

- [Sprint 118 Plan](SPRINT_118_PLAN.md)
- [E2E Testing Guide](../e2e/PLAYWRIGHT_E2E.md)
- [Technical Debt Index](../technical-debt/TD_INDEX.md)
