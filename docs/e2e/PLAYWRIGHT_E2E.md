# AegisRAG Playwright E2E Testing Guide

**Last Updated:** 2026-01-18 (Sprint 111)
**Framework:** Playwright + TypeScript
**Test Environment:** http://192.168.178.10 (Docker Container)
**Auth Credentials:** admin / admin123
**Documentation:** This file is the authoritative source for all E2E testing information

---

## Quick Start

```bash
# Navigate to frontend directory
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend

# Run all tests against production Docker container
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --reporter=list

# Run specific group
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test e2e/group09-long-context.spec.ts --reporter=list

# Run with parallel workers
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --workers=3 --reporter=list
```

---

## Executive Summary

| Metric | Value | Status |
|--------|-------|--------|
| **Total Test Groups** | 17 groups | - |
| **Total Tests** | ~210 tests | - |
| **Sprint 109 Complete** | 7/16 (43.75%) | ✅ |
| **Sprint 111 E2E Fixes** | Groups 13-16 | ✅ 41/41 (100%) |
| **Sprint 111 Features** | Long Context + Token Chart | ✅ COMPLETE |
| **Groups 01-03** | Auth Pattern Fixed | ✅ 46/46 (100%) |
| **Group 09** | Long Context UI | ✅ 23/23 (100%) |
| **Group 17** | Token Usage Chart (NEW) | ✅ 8/8 (100%) |

---

## Test Groups Status Overview

### Sprint 109 - COMPLETE ✅ (Groups 04-08, 10-12)

| Group | Feature | Tests | Pass Rate | Notes |
|-------|---------|-------|-----------|-------|
| **04** | Browser Tools | 6 | **100%** (6/6) | Auth + API mocks fixed |
| **05** | Skills Management | 8 | **100%** (8/8) | API format + selectors fixed |
| **06** | Skills Using Tools | 9 | **DEFERRED** | Requires chat integration |
| **07** | Memory Management | 15 | **100%** (15/15) | Auth + strict mode fixed |
| **08** | Deep Research | 11 | **90.9%** (10/11) | 1 intentional skip |
| **10** | Hybrid Search | 13 | **100%** (13/13) | Already passing |
| **11** | Document Upload | 15 | **100%** (15/15) | Already passing |
| **12** | Graph Communities | 16 | **93.75%** (15/16) | 1 intentional skip |

### Sprint 111 - E2E Fixes COMPLETE ✅ (Groups 13-16)

| Group | Feature | Tests | Pass Rate | Notes |
|-------|---------|-------|-----------|-------|
| **13** | Agent Hierarchy | 8 | **100%** (8/8) | Zoom controls aria-labels, skills badges D3 format |
| **14** | GDPR & Audit | 14 | **100%** (14/14) | Pagination controls, rights description, audit events |
| **15** | Explainability | 13 | **100%** (13/13) | Model info section, audit trail link, decision paths |
| **16** | MCP Marketplace | 6 | **100%** (6/6) | data-testid fix |

### Sprint 111 - COMPLETE ✅ (Groups 01-03, 09, 17)

| Group | Feature | Tests | Pass Rate | Notes |
|-------|---------|-------|-----------|-------|
| **01** | MCP Tools | 16 | **100%** (16/16) | Auth pattern fixed |
| **02** | Bash Execution | 15 | **100%** (15/15) | Command sandbox |
| **03** | Python Execution | 15 | **100%** (15/15) | Code execution |
| **09** | Long Context | 23 | **100%** (23/23) | Large document handling (Feature 111.1) |
| **17** | Token Usage Chart | 8 | **100%** (8/8) | Cost dashboard chart (Feature 111.2) |

---

## Sprint 109 Execution Summary ✅

### Phase 1: Browser Tools ✅
- Fixed tool execution endpoint mocks (`/api/v1/mcp/tools/{toolName}/execute`)
- Added auth setup (setupAuthMocking + navigateClientSide)
- All 6 tests passing (100%)

### Phase 2: Memory & Research ✅
- Group 07: Memory Management - 15/15 tests (100%)
- Group 08: Deep Research - 10/11 tests (90.9%)
- Fixed auth setup, resolved Playwright strict mode violations

### Phase 3: Core RAG Features ✅
- Group 10: Hybrid Search - 13/13 tests (100%)
- Group 11: Document Upload - 15/15 tests (100%)
- Group 12: Graph Communities - 15/16 tests (93.75%)

**Sprint 109 Total:** 82/83 tests passing (98.8%)

---

## Sprint 111 Execution Summary (Groups 13-16) ✅

### Feature 111.0: E2E Test Fixes

**Date:** 2026-01-18
**Result:** 41/41 tests passing (100%)

#### Group 13: Agent Hierarchy (8/8)
- Fixed zoom controls aria-labels (lowercase)
- Fixed skills badges D3 format in mock data

**Files Modified:**
- `AgentHierarchyD3.tsx`: Lowercase aria-labels for zoom controls
- `group13-agent-hierarchy.spec.ts`: Fixed skills test mock format

#### Group 14: GDPR & Audit (14/14)
- Added pagination controls (10 items/page) in ConsentRegistry
- Added rights description text in DataSubjectRights
- Fixed audit events mock with complete fields

**Files Modified:**
- `ConsentRegistry.tsx`: Client-side pagination (ITEMS_PER_PAGE = 10)
- `DataSubjectRights.tsx`: Added rights description section
- `group14-gdpr-audit.spec.ts`: Fixed mocks (25 consents for pagination, complete audit event fields)

#### Group 15: Explainability (13/13)
- Added model info section with data-testid
- Added audit trail link to /admin/audit
- Fixed API endpoint mocks (use /recent instead of /decision-paths)

**Files Modified:**
- `ExplainabilityPage.tsx`: Model info section, audit trail link, decision-path testid
- `group15-explainability.spec.ts`: Fixed endpoint mocks, CSS selector parsing

#### Group 16: MCP Marketplace (6/6)
- Changed data-testid to `mcp-server-browser`

**Files Modified:**
- `MCPServerBrowser.tsx`: Fixed data-testid attribute

---

## Sprint 111 Feature Implementation Summary ✅

### Feature 111.1: Long Context UI (10 SP)

**Date:** 2026-01-18
**Result:** 23/23 tests passing (100%)

#### New Components Created
- `ContextWindowIndicator.tsx` - Visual gauge for context usage (0-100%)
- `ChunkExplorer.tsx` - Interactive chunk navigation with search
- `RelevanceScoreDisplay.tsx` - Score visualization with distribution
- `ContextCompressionPanel.tsx` - Compression strategy selector
- `LongContextPage.tsx` - Admin page at `/admin/long-context`

#### Test Coverage (Group 09)
- Large document upload and processing
- Context window indicators (current/max tokens)
- Chunk preview with navigation
- Relevance score visualization
- Long context search functionality
- Context compression strategies
- Multi-document context merging
- Context overflow handling
- Quality metrics display
- Context export (JSON/Markdown)

### Feature 111.2: Token Usage Chart (8 SP)

**Date:** 2026-01-18
**Result:** 8/8 tests passing (100%)

#### New Components Created
- `TimeRangeSlider.tsx` - Time range with presets (1d-3y)
- `ChartControls.tsx` - Aggregation/provider/scale controls
- `TokenUsageChart.tsx` - Main chart with Recharts

#### Integration
- Added to `CostDashboardPage.tsx`
- Uses Recharts library (AreaChart, ResponsiveContainer)
- Fetches from `/api/v1/admin/costs/timeseries`

#### Test Coverage (Group 17)
- Chart renders with data
- Slider changes time range
- Provider filter works
- Aggregation toggle (daily/weekly/monthly)
- Empty state handling
- Loading state display
- Error state handling
- Export chart as PNG

### Groups 01-03: Auth Pattern Fix

**Date:** 2026-01-18
**Result:** 46/46 tests passing (100%)

Tests already had proper auth setup but needed Docker container rebuild for latest frontend code.

---

## Working Test Pattern (Reference) ⭐

**Group 03 Python Execution** and **Group 05 Skills Management** achieve **100% pass rates** and should be used as reference patterns.

### Key Pattern Elements

```typescript
import { test, expect, setupAuthMocking, navigateClientSide } from './fixtures';

const MCP_TOOLS_URL = '/admin/tools';

test.describe('Feature Tests', () => {
  // 1. Setup auth and ALL mocks in beforeEach
  test.beforeEach(async ({ page }) => {
    // Setup auth first
    await setupAuthMocking(page);

    // Setup ALL API mocks with proper data
    await page.route('**/api/v1/mcp/servers', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([mockServer]),
      });
    });

    await page.route('**/api/v1/mcp/tools', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockTools),
      });
    });
  });

  // 2. Tests use navigateClientSide for reliable navigation
  test('should execute action', async ({ page }) => {
    // Test-specific execution mock
    await page.route('**/api/v1/mcp/tools/tool_name/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, result: { ... } }),
      });
    });

    // Navigate using client-side routing
    await navigateClientSide(page, MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // 3. Use scoped selectors for clarity
    const tool = page.locator('[data-testid="tool-name"]');
    await tool.click();

    // 4. Wait for result with explicit timeout
    await expect(page.locator('text=/expected/i')).toBeVisible({ timeout: 5000 });
  });
});
```

### Why This Pattern Works

1. **Comprehensive beforeEach mocking:** All common API routes mocked upfront
2. **navigateClientSide():** More reliable than page.goto() for React Router
3. **Explicit waits:** `waitForLoadState('networkidle')` ensures page is ready
4. **Scoped selectors:** Clear, unambiguous element selection
5. **Proper timeout handling:** Explicit timeouts for async operations
6. **Realistic mock data:** Mock responses match actual backend structure

---

## API Contract-First Development (Sprint 112+)

### Best Practice: OpenAPI Specification First

**Before implementing frontend features with new API calls:**

1. **Define OpenAPI spec** in `docs/api/openapi/`
2. **Implement backend** endpoints matching spec
3. **Generate TypeScript types** from spec (optional)
4. **Implement frontend** using real APIs
5. **E2E tests** validate against real responses

**OpenAPI Specs:**
- `docs/api/openapi/context-api.yaml` - Long Context API (Sprint 112)

### Anti-Pattern: Demo Data Fallbacks

**❌ Don't:** Use catch blocks to generate fake data
```typescript
// BAD - Masks missing APIs, E2E tests pass but API doesn't exist!
} catch (err) {
  console.error('API Error:', err);
  setData(generateDemoData()); // Tests pass with fake data
}
```

**✅ Do:** Fail explicitly, fix the API
```typescript
// GOOD - Surfaces missing APIs, forces implementation
} catch (err) {
  setError(`API Error: ${err.message}`);
  // E2E test will fail, prompting API implementation
}
```

### Contract Validation Strategy

Use Playwright API mocking **only** for:
- ❌ Network error simulation (500, 503, timeout)
- ❌ Edge case testing (empty responses, malformed data)
- ❌ Rate limiting scenarios

For happy-path tests, **prefer real API calls**:
```typescript
// ✅ Happy path - use real API (no mocking)
test('should load real documents', async ({ page }) => {
  await navigateClientSide(page, '/admin/long-context');
  // Data comes from actual Qdrant + ingested Sprint docs
  await expect(page.locator('text=SPRINT_111_PLAN.md')).toBeVisible();
});

// ✅ Error path - use mocking
test('should handle API error', async ({ page }) => {
  await page.route('**/api/v1/context/documents', (route) => {
    route.fulfill({ status: 500, body: JSON.stringify({ detail: 'Server error' }) });
  });
  await navigateClientSide(page, '/admin/long-context');
  await expect(page.locator('[data-testid="error-banner"]')).toBeVisible();
});
```

### Real Test Data Strategy

**Problem:** E2E tests with mocked data don't validate real integration.

**Solution:** Use actual project documents as test data:

```bash
# Index Sprint Plan documents into Qdrant
python scripts/ingest_sprint_docs.py --namespace sprint_docs
```

**Benefits:**
- Tests validate real API responses
- Known content allows specific assertions
- Documents grow with project (22 files, ~275K tokens)

**Example assertion on real data:**
```typescript
test('should show indexed Sprint 111', async ({ page }) => {
  // No mocking - real API call
  await navigateClientSide(page, '/admin/long-context');

  // Assert on actual indexed document
  const doc = page.locator('[data-testid^="document-item-"]', {
    hasText: 'SPRINT_111_PLAN.md'
  });
  await expect(doc).toBeVisible();
  await expect(doc.locator('text=/tokens/')).toBeVisible();
});
```

---

## Common Issues & Fixes

### Issue 1: API Response Format Mismatch

**Example:** Skills returned array instead of `SkillListResponse` object

**Fix:** Update mock to match TypeScript interface:
```typescript
// ❌ Wrong
body: JSON.stringify([skill1, skill2])

// ✅ Correct
body: JSON.stringify({
  items: [skill1, skill2],
  total: 2,
  page: 1,
  page_size: 12,
  total_pages: 1
})
```

### Issue 2: Selector Specificity

**Example:** `text=/Active/i` matched dropdown AND badges

**Fix:** Scope selector to specific container:
```typescript
// ❌ Too broad
page.locator('text=/Active/i')

// ✅ Scoped
page.locator('[data-testid^="skill-card-"]').locator('text=/Active/i')
```

### Issue 3: React Router Navigation Unreliable

**Example:** Config editor navigation via link click failed

**Fix:** Use direct navigation:
```typescript
// ❌ Indirect
await page.locator('[data-testid="skill-edit-link"]').click();

// ✅ Direct
await navigateClientSide(page, '/admin/skills/web_search/config');
```

### Issue 4: Missing data-testid Attributes

**Example:** Error message had no testid

**Fix:** Add data-testid to component:
```typescript
<div data-testid="save-error" className="bg-red-50...">
  <p>{error}</p>
</div>
```

### Issue 5: TypeScript Import Errors at Runtime

**Symptom:** `The requested module does not provide an export named 'InterfaceName'`

**Solution:**
1. Create `types/*.ts` file for shared interfaces
2. Move interface to types file
3. Update imports to `import type { InterfaceName }`

---

## E2E Testing Best Practices

### Critical Rules

1. **Always verify backend APIs first** before assuming missing endpoints
   - Sprint 108: ALL backend APIs were correct, failures were frontend issues

2. **Rebuild Docker containers after code changes**
   ```bash
   cd /home/admin/projects/aegisrag/AEGIS_Rag
   docker compose -f docker-compose.dgx-spark.yml build --no-cache frontend
   docker compose -f docker-compose.dgx-spark.yml build --no-cache api
   docker compose -f docker-compose.dgx-spark.yml up -d
   ```

3. **TypeScript type safety**
   - Never export interfaces from component files (runtime code)
   - Use dedicated `types/*.ts` files for shared type definitions
   - Use `import type { }` syntax for type-only imports

4. **E2E timing tolerances**
   - Add 50-100% overhead for E2E tests vs API-only tests
   - Network latency, UI rendering, DOM mutations all add time
   - Example: API responds in 5s → E2E test needs 8-15s timeout

5. **Selector strategies**
   - Use scoped selectors: `parent.getByTestId('child')`
   - Avoid global selectors when multiple elements exist

6. **Mock API graceful fallbacks**
   - Components may cache data and skip redundant API calls
   - Don't require API mock to be called - make it optional

7. **Hidden file inputs**
   - Custom upload UIs hide native file inputs
   - Use `.count()` to check DOM existence, not `.toBeVisible()`

8. **Playwright buffer limits**
   - File operations have 50MB buffer limit
   - Test with smaller file sizes (10-20MB instead of 60MB)

---

## Test Execution Workflow

### Standard Test Run

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend

# Full test suite (~15-20 minutes)
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --reporter=list

# Specific group
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test e2e/group07-memory-management.spec.ts --reporter=list

# Parallel execution (3 workers, faster)
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --workers=3 --reporter=list

# Save results to file
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --reporter=list 2>&1 | tee test-results/results-$(date +%Y%m%d-%H%M%S).log
```

### After Test Run - Documentation Update

1. **Update this file (PLAYWRIGHT_E2E.md):**
   - Update "Test Groups Status Overview" table
   - Add new bugs/fixes to sprint section
   - Update remaining issues

2. **Update Sprint Plan:**
   - Document test-related tasks in `docs/sprints/SPRINT_XXX_PLAN.md`

---

## File Organization

### Test Files Location

```
frontend/e2e/
├── group01-mcp-tools.spec.ts           # MCP Tools Management
├── group02-bash-execution.spec.ts      # Bash Tool Execution
├── group03-python-execution.spec.ts    # Python Tool (⭐ Reference)
├── group04-browser-tools.spec.ts       # Browser MCP Tools
├── group05-skills-management.spec.ts   # Skills Management (⭐ Reference)
├── group06-skills-using-tools.spec.ts  # Skills Using Tools (deferred)
├── group07-memory-management.spec.ts   # Memory Management
├── group08-deep-research.spec.ts       # Deep Research Mode
├── group09-long-context.spec.ts        # Long Context (Sprint 111)
├── group10-hybrid-search.spec.ts       # BGE-M3 Hybrid Search
├── group11-document-upload.spec.ts     # Document Upload
├── group12-graph-communities.spec.ts   # Graph Communities
├── group13-agent-hierarchy.spec.ts     # Agent Hierarchy
├── group14-gdpr-audit.spec.ts          # GDPR/Audit
├── group15-explainability.spec.ts      # Explainability
├── group16-mcp-marketplace.spec.ts     # MCP Marketplace
├── group17-token-usage-chart.spec.ts   # Token Usage Chart (Sprint 111)
└── fixtures/index.ts                   # Shared test utilities
```

### Documentation Location

```
docs/e2e/
├── PLAYWRIGHT_E2E.md                   # THIS FILE (authoritative guide)
├── TESTING_PATTERNS.md                 # Test patterns & best practices
├── USER_JOURNEYS_AND_TEST_PLAN.md      # User journey definitions
├── TOOL_FRAMEWORK_USER_JOURNEY.md      # Tool framework journeys
└── archive/                            # Archived/outdated documents
```

---

## Test Group Descriptions

### Group 01-03: Tool Execution
- **MCP Tools:** Server connection, tool discovery, execution
- **Bash Execution:** Command sandbox, security validation
- **Python Execution:** Code execution, AST validation

### Group 04-06: Skills & Tools
- **Browser Tools:** Browser automation via MCP
- **Skills Management:** Registry, config editor, lifecycle
- **Skills Using Tools:** Chat + skill invocation (requires integration)

### Group 07-08: Memory & Research
- **Memory Management:** 3-layer stats, search, consolidation
- **Deep Research:** Multi-step research, progress tracking

### Group 09: Long Context (Sprint 111)
- Large document handling (>100K tokens)
- Context window management UI
- Document chunking visualization
- Context relevance scoring

### Group 10-12: Core RAG
- **Hybrid Search:** Vector + Graph + Sparse search
- **Document Upload:** Upload, processing, management
- **Graph Communities:** Community detection, visualization

### Group 13-16: Enterprise
- **Agent Hierarchy:** Executive→Manager→Worker visualization
- **GDPR & Audit:** Consent management, audit trails
- **Explainability:** Decision traces, source attribution
- **MCP Marketplace:** Server discovery, installation

### Group 17: Cost Analytics (Sprint 111)
- **Token Usage Chart:** Time series visualization with Recharts
- Time range slider (1d-3y) with logarithmic scale
- Provider filtering, aggregation controls (daily/weekly/monthly)
- Export chart as PNG functionality

---

## Success Metrics

### Sprint 111 COMPLETE ✅

| Group | Tests | Status |
|-------|-------|--------|
| Groups 01-03 | 46/46 | ✅ 100% |
| Group 09 Long Context | 23/23 | ✅ 100% |
| Groups 13-16 | 41/41 | ✅ 100% |
| Group 17 Token Chart | 8/8 | ✅ 100% |
| **Sprint 111 Total** | **118/118** | **✅ 100%** |

### Cumulative Pass Rates

| Sprint | Tests | Status |
|--------|-------|--------|
| Sprint 109 | 82/83 | ✅ 98.8% |
| Sprint 111 | 118/118 | ✅ 100% |
| **Total** | **200/201** | **✅ 99.5%** |

### End Goal (Sprint 112+)
- All 17 groups: >95% pass rate
- Overall: >200 tests passing (99%+ of ~210)
- Production-ready E2E test suite

---

## Related Documentation

- **Sprint Plans:** `docs/sprints/SPRINT_XXX_PLAN.md`
- **CLAUDE.md:** E2E Testing Strategy section
- **Testing Patterns:** `docs/e2e/TESTING_PATTERNS.md`
- **User Journeys:** `docs/e2e/USER_JOURNEYS_AND_TEST_PLAN.md`
- **Archive:** `docs/e2e/archive/` - Outdated E2E documentation

---

**Last Test Run:** 2026-01-18 (Sprint 111 COMPLETE: 118/118 = 100%)
**Sprint 111 Tests:** Groups 01-03 (46), Group 09 (23), Groups 13-16 (41), Group 17 (8)
**Next Sprint:** Sprint 112
**Maintained By:** Claude Code + Sprint Team
