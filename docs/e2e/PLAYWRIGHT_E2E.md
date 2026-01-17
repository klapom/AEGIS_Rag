# AegisRAG Playwright E2E Testing Guide

**Last Updated:** 2026-01-17 (Sprint 110)
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
| **Total Test Groups** | 16 groups | - |
| **Total Tests** | ~200 tests | - |
| **Sprint 109 Complete** | 7/16 (43.75%) | ✅ |
| **Sprint 109 Pass Rate** | 98.8% (82/83 tests) | - |
| **Sprint 110 Focus** | Groups 01-03, 13-16 | - |
| **Sprint 111 Focus** | Long Context (Group 09) | - |

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

### Sprint 110 - PLANNED (Groups 01-03, 13-16)

| Group | Feature | Tests | Priority | Notes |
|-------|---------|-------|----------|-------|
| **01** | MCP Tools | 6 | Medium | Tool execution |
| **02** | Bash Execution | 5 | Medium | Command sandbox |
| **03** | Python Execution | 5 | Medium | Code execution |
| **13** | Agent Hierarchy | 8 | Medium | D3 visualization |
| **14** | GDPR & Audit | 10 | Medium | Compliance UI |
| **15** | Explainability | 9 | Medium | Decision traces |
| **16** | MCP Marketplace | 8 | Low | Server discovery |

### Sprint 111 - PLANNED (Long Context)

| Group | Feature | Tests | Priority | Notes |
|-------|---------|-------|----------|-------|
| **09** | Long Context | 10 | **HIGH** | Large document handling |

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

---

## Success Metrics

### Sprint 110 Targets
- Groups 01-03: >80% pass rate
- Groups 13-16: >80% pass rate
- **Overall:** ≥90 tests passing

### Sprint 111 Targets
- Group 09: 10/10 (100%) - Long Context Priority

### End Goal (Sprint 112+)
- All 16 groups: >95% pass rate
- Overall: >190 tests passing (95% of ~200)
- Production-ready E2E test suite

---

## Related Documentation

- **Sprint Plans:** `docs/sprints/SPRINT_XXX_PLAN.md`
- **CLAUDE.md:** E2E Testing Strategy section
- **Testing Patterns:** `docs/e2e/TESTING_PATTERNS.md`
- **User Journeys:** `docs/e2e/USER_JOURNEYS_AND_TEST_PLAN.md`
- **Archive:** `docs/e2e/archive/` - Outdated E2E documentation

---

**Last Test Run:** 2026-01-17
**Next Test Run:** After Sprint 110 fixes
**Maintained By:** Claude Code + Sprint Team
