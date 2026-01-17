# Sprint 102 E2E Tests - Action Items

**Created:** 2026-01-15
**Priority:** HIGH
**Status:** PENDING REVIEW

## Critical Actions Required Before Test Execution

### 1. Add Missing data-testid Attributes (CRITICAL)

#### SkillRegistry.tsx
**File:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/pages/admin/SkillRegistry.tsx`

**Required Changes:**
```tsx
// Line ~245: SkillCard component
function SkillCard({ skill, onToggle }: SkillCardProps) {
  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg border-2..."
      data-testid={`skill-card-${skill.name}`}  // ADD THIS
    >
      {/* ... rest of component */}
    </div>
  );
}
```

**Impact:** Without this, 5 tests in Group 5 will fail.

---

#### SkillConfigEditor.tsx
**File:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/pages/admin/SkillConfigEditor.tsx`

**Required Changes:**
```tsx
// Line ~234: Validation Status section
<div
  className="bg-white dark:bg-gray-800 rounded-lg..."
  data-testid="validation-status"  // ADD THIS
>
  <h3 className="font-semibold text-lg...">
    Validation
  </h3>
  {/* ... validation content */}
</div>

// Line ~254: Errors section
{validation.errors.length > 0 && (
  <div
    className="space-y-2"
    data-testid="validation-errors"  // ADD THIS
  >
    {/* ... error messages */}
  </div>
)}

// Line ~202: Error Display
{error && (
  <div
    className="bg-red-50 dark:bg-red-900/20..."
    data-testid="save-error"  // ADD THIS
  >
    <p className="text-red-800 dark:text-red-200">{error}</p>
  </div>
)}
```

**Impact:** Without these, 3 tests in Group 5 will fail.

---

#### MCPToolsPage.tsx Components
**Files:**
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/pages/admin/MCPToolsPage.tsx`
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/admin/MCPServerList.tsx`
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/admin/MCPToolExecutionPanel.tsx`

**Required Changes:**
```tsx
// MCPServerList.tsx - Server item
<div
  className="server-item..."
  data-testid={`mcp-server-${server.name}`}  // ADD THIS
>
  <span data-testid="server-status">{server.status}</span>  // ADD THIS
</div>

// MCPServerList.tsx - Tool item
<button
  className="tool-button..."
  data-testid={`tool-${tool.name}`}  // ADD THIS
>
  {tool.name}
</button>

// MCPToolExecutionPanel.tsx - Execution states
<div data-testid="tool-execution-loading">Loading...</div>  // ADD THIS
<div data-testid="tool-execution-result">{result}</div>      // ADD THIS
<div data-testid="tool-execution-error">{error}</div>        // ADD THIS

// MCPToolExecutionPanel.tsx - Parameter inputs
<input
  data-testid={`param-${param.name}`}  // ADD THIS
  {...}
/>
```

**Impact:** Without these, 6 tests in Group 4 will fail.

---

### 2. Verify API Endpoints Exist (CRITICAL)

#### Skills API Endpoints
**Required Endpoints:**
```
GET  /api/v1/skills                      # List skills
GET  /api/v1/skills/{skillName}/config   # Get skill config
PUT  /api/v1/skills/{skillName}/config   # Update skill config
POST /api/v1/skills/{skillName}/activate # Activate skill
POST /api/v1/skills/{skillName}/deactivate # Deactivate skill
POST /api/v1/skills/{skillName}/config/validate # Validate config
```

**Verification Command:**
```bash
curl http://localhost:8000/api/v1/skills
curl http://localhost:8000/api/v1/skills/web_search/config
```

**Impact:** If endpoints missing, ALL Group 5 tests will fail.

---

#### MCP API Endpoints
**Required Endpoints:**
```
GET  /api/v1/mcp/health                  # MCP health status
POST /api/v1/mcp/tools/execute           # Execute tool
GET  /api/v1/mcp/servers                 # List MCP servers
GET  /api/v1/mcp/tools                   # List available tools
```

**Verification Command:**
```bash
curl http://localhost:8000/api/v1/mcp/health
curl http://localhost:8000/api/v1/mcp/servers
```

**Impact:** If endpoints missing, ALL Group 4 tests will fail.

---

#### Chat SSE Endpoint
**Required Endpoint:**
```
POST /api/v1/chat/stream                 # SSE streaming for chat
```

**Event Format Expected:**
```typescript
// Tool use event
{ type: 'tool_use', tool: string, parameters: object, execution_id?: string }

// Tool result event
{ type: 'tool_result', tool: string, result: any, success: boolean, error?: string, execution_id?: string }

// Skill activation event
{ type: 'skill_activated', skill: string, reason: string }

// Error event
{ type: 'error', message: string }
```

**Verification Command:**
```bash
curl -N -H "Accept: text/event-stream" -H "Content-Type: application/json" \
  -d '{"message": "test"}' \
  http://localhost:8000/api/v1/chat/stream
```

**Impact:** If SSE format differs, ALL Group 6 tests will fail.

---

### 3. Component Existence Verification (HIGH)

Check if these components exist:
```bash
# Skills components
ls frontend/src/pages/admin/SkillRegistry.tsx
ls frontend/src/pages/admin/SkillConfigEditor.tsx

# MCP components
ls frontend/src/pages/admin/MCPToolsPage.tsx
ls frontend/src/components/admin/MCPServerList.tsx
ls frontend/src/components/admin/MCPToolExecutionPanel.tsx
ls frontend/src/components/admin/MCPHealthMonitor.tsx

# Chat components with tool execution display
ls frontend/src/components/chat/ConversationView.tsx
```

**If components are missing, tests marked with `.skip()`:**
```typescript
test.skip('component not yet implemented', async ({ page }) => {
  // Test code here
});
```

---

### 4. Frontend Port Configuration (MEDIUM)

**Tests expect frontend on:** `http://localhost:80`
**Playwright config has:** `http://localhost:5179`

**Decision Required:**
1. Update tests to use `http://localhost:5179`?
2. Update playwright.config.ts baseURL to `http://localhost:80`?
3. Keep both and make configurable?

**Current Workaround:**
Tests navigate to absolute paths (e.g., `/admin/skills/registry`), which uses the baseURL from playwright.config.ts.

---

### 5. Mock vs Real Backend Testing (MEDIUM)

**Current Approach:** Tests mock ALL API endpoints

**Alternative Approach:** Test against real backend for integration testing

**Decision Required:**
- Keep mocks for fast, isolated tests?
- Add separate integration test suite with real backend?
- Use environment variable to toggle mock/real?

**Recommendation:** Keep mocks, add separate `*.integration.spec.ts` files for real backend tests.

---

## Execution Plan

### Phase 1: Component Updates (2-4 hours)
1. Add data-testid attributes to SkillRegistry.tsx
2. Add data-testid attributes to SkillConfigEditor.tsx
3. Add data-testid attributes to MCP components
4. Commit: `feat(e2e): Add data-testid attributes for Sprint 102 tests`

### Phase 2: API Verification (1 hour)
1. Verify all skills endpoints exist
2. Verify all MCP endpoints exist
3. Verify SSE event format matches expectations
4. Document any discrepancies

### Phase 3: Test Execution (1 hour)
1. Run Group 4 tests (browser tools)
2. Run Group 5 tests (skills management)
3. Run Group 6 tests (skills using tools)
4. Document results in SPRINT_102_TEST_RESULTS.md

### Phase 4: Bug Fixes (2-4 hours)
1. Fix any failing tests due to selector issues
2. Update mocks to match actual API responses
3. Add `.skip()` for tests requiring unimplemented features
4. Re-run all tests

### Phase 5: Documentation (30 minutes)
1. Create test coverage report
2. Update Sprint 102 status
3. Create GitHub issue for any blocking bugs

---

## Test Execution Commands

### Dry Run (Verify tests are parseable)
```bash
cd frontend
npx playwright test --list group04-browser-tools.spec.ts
npx playwright test --list group05-skills-management.spec.ts
npx playwright test --list group06-skills-using-tools.spec.ts
```

### Run Individual Groups
```bash
# Group 4: Browser Tools (6 tests)
npx playwright test group04-browser-tools.spec.ts --headed

# Group 5: Skills Management (8 tests)
npx playwright test group05-skills-management.spec.ts --headed

# Group 6: Skills Using Tools (9 tests)
npx playwright test group06-skills-using-tools.spec.ts --headed
```

### Run All Sprint 102 Tests
```bash
npx playwright test group04-browser-tools.spec.ts group05-skills-management.spec.ts group06-skills-using-tools.spec.ts --reporter=html
```

### Debug Mode (Step through tests)
```bash
npx playwright test group05-skills-management.spec.ts --debug
```

---

## Expected Test Results (After Fixes)

| Test Group | Total Tests | Expected Pass | Expected Fail/Skip | Notes |
|------------|-------------|---------------|-------------------|-------|
| Group 4: Browser Tools | 6 | 4-6 | 0-2 | Skip if MCP browser not connected |
| Group 5: Skills Management | 8 | 8 | 0 | Should all pass with mocks |
| Group 6: Skills Using Tools | 9 | 7-9 | 0-2 | Skip if skills not implemented |
| **TOTAL** | **23** | **19-23** | **0-4** | |

---

## Contact & Escalation

**Questions about tests:** Frontend Agent
**Component implementation issues:** Backend Agent (Skills/MCP)
**API endpoint issues:** API Agent
**Test execution issues:** Testing Agent

**Blocking Issues:**
- Missing API endpoints → Escalate to API Agent
- Missing components → Escalate to Frontend Agent
- Test infrastructure issues → Escalate to Testing Agent

---

**END OF ACTION ITEMS**
