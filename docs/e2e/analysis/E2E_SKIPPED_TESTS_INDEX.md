# E2E Skipped Tests - Complete Documentation Index

**Analysis Date:** 2026-01-20  
**Scope:** All Playwright E2E test files in `/frontend/e2e/` (70 test files scanned)  
**Tests Found:** 23 skipped test suites across 16 files  
**Total Story Points:** 176 SP

## Document Navigation

### Quick Start
- **[SKIPPED_TESTS_TABLE.md](SKIPPED_TESTS_TABLE.md)** - Just the markdown table, easy to copy/paste (6.1 KB)
- **[SKIPPED_TESTS_SUMMARY.md](SKIPPED_TESTS_SUMMARY.md)** - Quick reference with categories and SP breakdown (5.8 KB)

### Detailed Documentation
- **[docs/sprints/SPRINT_116_SKIPPED_TESTS_ANALYSIS.md](docs/sprints/SPRINT_116_SKIPPED_TESTS_ANALYSIS.md)** - Complete analysis with implementation priorities (12 KB)
- **[docs/sprints/SPRINT_116_PLAN.md](docs/sprints/SPRINT_116_PLAN.md)** - Sprint planning and feature categories (6.5 KB)

## Quick Summary

| Category | Count | SP | Priority |
|----------|-------|----|---------| 
| Domain Management | 8 | 53 | HIGH |
| Graph & Versioning | 5 | 39 | MEDIUM |
| Research & Performance | 2 | 26 | MEDIUM |
| MCP & Tools | 3 | 21 | MEDIUM |
| Quality & Infrastructure | 4 | 18 | MEDIUM |
| Admin Dashboard | 1 | 5 | LOW |
| **TOTAL** | **23** | **176** | - |

## Key Findings

### Highest Impact Features
1. **Domain Training API CRUD** (13 SP) - Foundation for 8 domain features
2. **Entity Versioning APIs** (13 SP) - Foundation for 3 graph features
3. **Deep Research Multi-Step** (13 SP) - Complex LLM orchestration
4. **Performance Regression Tests** (13 SP) - Infrastructure baseline
5. **Version Comparison UI** (13 SP) - Complex diff visualization

### Quick Wins (Under 5 SP)
- Default domain seeding (3 SP)
- Domain response format (3 SP)
- Admin dashboard stats cards (5 SP)
- Graph communities UI (5 SP)
- Edge filters UI (5 SP)
- Visual regression framework (5 SP)
- API error handling (5 SP)
- Citation features (5 SP)
- Graph visualization (3 SP)

### Critical Dependencies
```
Domain CRUD (13 SP)
├── Classification (8 SP)
├── Auto-Discovery (8 SP)
├── Augmentation (8 SP)
├── Batch Ingestion (8 SP)
├── Details/Status (5 SP)
├── Validation (5 SP)
└── Response Format (3 SP)

Entity Versioning (13 SP)
├── Version Compare (13 SP)
├── Changelog (10 SP)
└── Time Travel (8 SP)
```

## Skipped Tests by Category

### Domain Management Tests (58 SP)
**File:** `test_domain_training_api.spec.ts`  
**Status:** 7 test suites all skipped (Endpoint returns 404)

- CRUD Operations (13 SP)
- Classification (8 SP)
- Auto-Discovery (8 SP)
- Data Augmentation (8 SP)
- Batch Ingestion (8 SP)
- Domain Details (5 SP)
- Input Validation (5 SP)
- Response Format (3 SP)

### Graph Versioning Tests (44 SP)
- Time Travel Tab (8 SP) - `time-travel.spec.ts`
- Version Comparison (13 SP) - `version-compare.spec.ts`
- Entity Changelog (10 SP) - `entity-changelog.spec.ts`
- Edge Filters (5 SP) - `edge-filters.spec.ts`
- Graph Visualization (8 SP) - `graph-visualization.spec.ts`

### MCP & Tool Tests (21 SP)
- Tool Management (8 SP) - `group01-mcp-tools.spec.ts`
- Bash Execution (8 SP) - `group02-bash-execution.spec.ts`
- Graph Communities (5 SP) - `group12-graph-communities.spec.ts`

### Research & Performance (26 SP)
- Deep Research Multi-Step (13 SP) - `group08-deep-research.spec.ts`
- Performance Regression (13 SP) - `performance-regression.spec.ts`

### Quality & Infrastructure (18 SP)
- Visual Regression Framework (5 SP) - `visual-regression.example.spec.ts`
- API Error Handling (5 SP) - `api-errors.spec.ts`
- Citation Features (5 SP) - `citations.spec.ts`

### Admin Dashboard (8 SP)
- Statistics Cards (5 SP) - `admin-dashboard.spec.ts`
- Default Domain Seeding (3 SP) - `test_domain_training_flow.spec.ts`

## Backend API Endpoints Required

### Domain Management (12 endpoints)
```
GET    /api/v1/admin/domains/
GET    /api/v1/admin/domains/{name}
GET    /api/v1/admin/domains/available-models
POST   /api/v1/admin/domains/
POST   /api/v1/admin/domains/classify
POST   /api/v1/admin/domains/discover
POST   /api/v1/admin/domains/augment
POST   /api/v1/admin/domains/ingest-batch
GET    /api/v1/admin/domains/{name}/training-status
POST   /api/v1/admin/domains/{id}/train
```

### Entity Versioning (5 endpoints)
```
GET    /api/v1/entities/{id}/versions
GET    /api/v1/entities/{id}/versions/{v1}/compare/{v2}
GET    /api/v1/entities/{id}/changelog
POST   /api/v1/entities/{id}/versions/{version}/revert
POST   /api/v1/temporal/point-in-time
```

### Admin Dashboard (3 endpoints)
```
GET    /api/v1/admin/dashboard/stats
GET    /api/v1/admin/indexing/stats
GET    /api/v1/admin/settings
```

## Frontend Components Required

### Domain Training
- Domain list view
- Domain wizard (multi-step)
- Dataset upload & preview
- Metric configuration
- Training monitor

### Graph Features
- TimeTravelTab (temporal navigation)
- VersionCompareView (diff visualization)
- EntityChangelogPanel (history display)
- GraphEdgeFilter (filtering controls)
- Graph visualization (canvas/WebGL)

### MCP Tools
- MCPToolsPage (registry UI)
- Tool selector (combobox)
- Tool executor (command runner)
- Tool toggles (enable/disable)

### Quality Components
- Citation tooltip
- Error boundary
- Retry UI
- StatCard
- Performance instrumentation

## Test Pattern & Methodology

### Playwright Configuration
- **Test Framework:** Playwright with TypeScript
- **Fixtures:** Custom `setupAuthMocking` fixture
- **Pattern:** `setupAuthMocking(page) + page.goto() + assertions`
- **Timeout Strategy:** Graceful fallbacks with `.catch(() => false)`

### Data-TestID Requirements
- All interactive elements require `data-testid` selectors
- Common pattern: `[data-testid="component-name"]`
- Graph tests need: graph canvas, edges, nodes, legend

### Mock API Pattern
```typescript
await page.route('**/api/v1/endpoint/**', async (route) => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(mockData)
  });
});
```

## Recommendations

### Sprint 116 (33 SP - Foundation & Quick Wins)
1. Domain CRUD API (13 SP) - Unblocks 40+ SP
2. Default domain seeding (3 SP) - Quick win
3. Admin dashboard stats (5 SP) - Quick win
4. API error handling (5 SP) - QoL improvement
5. Citation features (7 SP) - UX improvement

### Sprint 117-118 (143 SP - Major Features)
**Priority 1:** Entity versioning APIs (13 SP)
**Priority 2:** Domain classification & discovery (16 SP)
**Priority 3:** Graph & versioning UIs (34 SP)
**Priority 4:** Research & infrastructure (39 SP)
**Priority 5:** Remaining features (41 SP)

## File Locations

| Document | Size | Location |
|----------|------|----------|
| This Index | - | `/E2E_SKIPPED_TESTS_INDEX.md` |
| Table Only | 6.1 KB | `/SKIPPED_TESTS_TABLE.md` |
| Quick Summary | 5.8 KB | `/SKIPPED_TESTS_SUMMARY.md` |
| Full Analysis | 12 KB | `/docs/sprints/SPRINT_116_SKIPPED_TESTS_ANALYSIS.md` |
| Sprint Plan | 6.5 KB | `/docs/sprints/SPRINT_116_PLAN.md` |

## How to Use This Documentation

### For Sprint Planning
1. Open `SPRINT_116_PLAN.md` - See feature categories and priorities
2. Check `SPRINT_116_SKIPPED_TESTS_ANALYSIS.md` - Review dependencies and detailed specs
3. Use `SKIPPED_TESTS_SUMMARY.md` - Quick reference during planning

### For Implementation
1. Start with highest priority (Domain CRUD API - 13 SP)
2. Reference backend endpoints in this document
3. Use test file names to find implementation specs
4. Check test fixtures for expected data structures

### For Team Communication
1. Share `SKIPPED_TESTS_TABLE.md` - Easy to copy/paste
2. Reference `SKIPPED_TESTS_SUMMARY.md` - Good overview
3. Link to specific sections in `SPRINT_116_SKIPPED_TESTS_ANALYSIS.md`

## Test Files Scanned

**Total Files:** 70 Playwright test files
**Files with Skipped Tests:** 16
**Files with Active Tests:** 54

### With Skipped Tests (16 files)
- admin/admin-dashboard.spec.ts
- admin/test_domain_training_api.spec.ts
- admin/test_domain_training_flow.spec.ts
- citations/citations.spec.ts
- edge-filters.spec.ts
- entity-changelog.spec.ts
- graph-visualization.spec.ts
- group01-mcp-tools.spec.ts
- group02-bash-execution.spec.ts
- group08-deep-research.spec.ts
- group12-graph-communities.spec.ts
- tests/errors/api-errors.spec.ts
- tests/examples/visual-regression.example.spec.ts
- tests/graph/entity-changelog.spec.ts
- tests/graph/version-compare.spec.ts
- tests/integration/performance-regression.spec.ts

## Next Steps

1. **Share this documentation** with sprint planning team
2. **Review priorities** in SPRINT_116_SKIPPED_TESTS_ANALYSIS.md
3. **Plan Sprints 116-118** based on dependencies
4. **Implementation starts** with Domain CRUD API (13 SP)
5. **Monitor coverage** as features are implemented

---

**Generated:** 2026-01-20  
**Analyst:** Testing Agent  
**Status:** Complete - Ready for Sprint Planning  
**Total Time to Generate:** ~45 minutes of comprehensive analysis  
