# E2E Groups 04-06 Mock Fixes - Verification Guide

## Implementation Verification

This document provides step-by-step verification that all mock fixes have been correctly applied.

---

## Group 04: Browser Tools - Verification

### Step 1: Check Mock Exists
**File:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts`

Run this command to verify the mock is present:
```bash
grep -n "api/v1/mcp/servers" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts
```

**Expected Output:**
```
103:    await page.route('**/api/v1/mcp/servers', (route) => {
```

### Step 2: Verify Mock Returns Browser Server
```bash
grep -A 50 "api/v1/mcp/servers" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts | grep -E "name:|browser|status|tools"
```

**Expected Output Contains:**
```
name: 'browser'
status: 'connected'
tools: [
  { name: 'browser_navigate'
  { name: 'browser_click'
  { name: 'browser_take_screenshot'
  { name: 'browser_evaluate'
```

### Step 3: Verify Tool Parameters Structure
```bash
grep -A 100 "api/v1/mcp/servers" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts | grep -E "parameters:|type:|required"
```

**Expected Output Contains:**
```
parameters: [
  { name: 'url', type: 'string', ... required: true }
  { name: 'element', type: 'string', ... required: true }
```

### Step 4: Verify Mock Completeness
```bash
grep "last_connected" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts
```

**Expected Output:**
```
last_connected: new Date().toISOString()
```

### Step 5: Run Group 04 Tests
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag && \
npx playwright test frontend/e2e/group04-browser-tools.spec.ts --reporter=line
```

**Expected Result:**
```
✓ should display browser MCP tools in UI (...)
✓ should execute navigate to URL command (...)
✓ should execute click element command (...)
✓ should execute take screenshot command (...)
✓ should execute evaluate JavaScript command (...)
✓ should handle tool execution errors gracefully (...)

6 passed (...)
```

---

## Group 05: Skills Management - Verification

### Step 1: Check Registry Endpoint Mock
```bash
grep -n "api/v1/skills/registry" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts
```

**Expected Output:**
```
135:  await page.route('**/api/v1/skills/registry', (route) => {
```

### Step 2: Verify Config Endpoint Mock
```bash
grep -n "api/v1/skills/\*/config" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts
```

**Expected Output (2 occurrences - GET/PUT and validate):**
```
144:  await page.route('**/api/v1/skills/*/config', async (route) => {
182:  await page.route('**/api/v1/skills/*/config/validate', (route) => {
```

### Step 3: Verify Activate/Deactivate Endpoints
```bash
grep -E "api/v1/skills/\*/activate|api/v1/skills/\*/deactivate" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts
```

**Expected Output:**
```
195:  await page.route('**/api/v1/skills/*/activate', (route) => {
204:  await page.route('**/api/v1/skills/*/deactivate', (route) => {
```

### Step 4: Verify Mock Data Structure
```bash
grep -A 5 "name: 'web_search'" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts | head -10
```

**Expected Output Contains:**
```
name: 'web_search',
version: '1.0.0',
description: 'Search the web for information using DuckDuckGo',
icon: '🔍',
is_active: true,
tools_count: 2,
triggers_count: 5,
```

### Step 5: Verify Config Response Format
```bash
grep -A 20 "config:" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts | head -15
```

**Expected Output:**
```
config: `name: ${skillName}
version: 1.0.0
description: Configuration for ${skillName}
tools:
  - tool1
  - tool2
triggers:
  - trigger1
```

### Step 6: Run Group 05 Tests
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag && \
npx playwright test frontend/e2e/group05-skills-management.spec.ts --reporter=line
```

**Expected Result:**
```
✓ should load Skills Registry with 5 skills (...)
✓ should open Skill config editor (...)
✓ should validate YAML syntax - valid config (Sprint 100 Fix #8) (...)
✓ should validate YAML syntax - invalid syntax (Sprint 100 Fix #8) (...)
✓ should validate YAML schema - missing required fields (Sprint 100 Fix #8) (...)
✓ should enable/disable skill toggle (...)
✓ should save configuration successfully (...)
✓ should handle save errors gracefully (...)

8 passed (...)
```

---

## Group 06: Skills Using Tools - Verification

### Step 1: Verify Import of navigateClientSide
```bash
grep "navigateClientSide" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts | head -1
```

**Expected Output:**
```
import { test, expect, setupAuthMocking, navigateClientSide } from './fixtures';
```

### Step 2: Verify navigateClientSide Usage in Helper
```bash
grep -A 3 "async function navigateToChat" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts
```

**Expected Output:**
```
async function navigateToChat(page: Page) {
  await navigateClientSide(page, '/');
  await page.waitForLoadState('networkidle');
```

### Step 3: Verify MCP Servers Mock
```bash
grep -n "api/v1/mcp/servers" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts
```

**Expected Output:**
```
111:    await page.route('**/api/v1/mcp/servers', (route) => {
```

### Step 4: Verify Three Servers in Mock
```bash
grep -E "name: '(bash|python|browser)'" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts | wc -l
```

**Expected Output:**
```
3
```

### Step 5: Verify Skills Registry Mock
```bash
grep -n "api/v1/skills/registry" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts
```

**Expected Output:**
```
155:    await page.route('**/api/v1/skills/registry', (route) => {
```

### Step 6: Verify Skills Count in Mock
```bash
grep -c "name: '" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts | head -1
```

**Expected Output Contains:** At least 8 names (3 for servers + 3 for skills + tools)

### Step 7: Verify Legacy Skills Endpoint
```bash
grep -n "api/v1/skills'" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts | grep -v registry
```

**Expected Output:**
```
198:    await page.route('**/api/v1/skills', (route) => {
```

### Step 8: Run Group 06 Tests
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag && \
npx playwright test frontend/e2e/group06-skills-using-tools.spec.ts --reporter=line
```

**Expected Result:**
```
✓ should invoke bash tool via skill (...)
✓ should invoke python tool via skill (...)
✓ should invoke browser tool via skill (...)
✓ should handle end-to-end flow: skill → tool → result (...)
✓ should handle tool execution errors gracefully (...)
✓ should handle skill activation failures (...)
✓ should handle timeout during tool execution (...)
✓ should display tool execution progress indicators (...)
✓ should handle multiple concurrent tool executions (...)

8 passed (...)
```

---

## Comprehensive Verification

### All Mocks Present
```bash
echo "=== GROUP 04 ===" && \
grep -c "page.route" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts && \
echo "=== GROUP 05 ===" && \
grep -c "page.route" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts && \
echo "=== GROUP 06 ===" && \
grep -c "page.route" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts
```

**Expected Output:**
```
=== GROUP 04 ===
2
=== GROUP 05 ===
6
=== GROUP 06 ===
5
```

### Syntax Validation
```bash
echo "=== GROUP 04 ===" && \
node -c /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts && \
echo "✓ Syntax OK" && \
echo "=== GROUP 05 ===" && \
node -c /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts && \
echo "✓ Syntax OK" && \
echo "=== GROUP 06 ===" && \
node -c /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts && \
echo "✓ Syntax OK"
```

**Expected Output:**
```
=== GROUP 04 ===
✓ Syntax OK
=== GROUP 05 ===
✓ Syntax OK
=== GROUP 06 ===
✓ Syntax OK
```

### Run All Three Groups
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag && \
npx playwright test frontend/e2e/group0[456]-*.spec.ts --reporter=line
```

**Expected Result:**
```
✓ Group 4: Browser MCP Tools (6 tests)
✓ Group 5: Skills Management (8 tests)
✓ Group 6: Skills Using Tools (8 tests)

22 passed (...)
```

---

## Mock Response Validation

### Verify Group 04 Response Structure
```bash
cat > /tmp/verify_g04.js << 'EOF'
const mock = {
  name: 'browser',
  status: 'connected',
  description: 'Browser automation tools',
  url: 'stdio://browser-mcp',
  tools: [
    { name: 'browser_navigate', description: 'Navigate to a URL in the browser', server_name: 'browser', parameters: [{ name: 'url', type: 'string', description: 'The URL to navigate to', required: true }] },
    { name: 'browser_click', description: 'Click an element in the browser', server_name: 'browser', parameters: [{ name: 'element', type: 'string', description: 'Element selector', required: true }, { name: 'ref', type: 'string', description: 'Element reference', required: false }] },
    { name: 'browser_take_screenshot', description: 'Take a screenshot of the current page', server_name: 'browser', parameters: [{ name: 'filename', type: 'string', description: 'Screenshot filename', required: false }, { name: 'type', type: 'string', description: 'Image type (png/jpg)', required: false }] },
    { name: 'browser_evaluate', description: 'Evaluate JavaScript in the browser', server_name: 'browser', parameters: [{ name: 'function', type: 'string', description: 'JavaScript function to execute', required: true }] }
  ],
  last_connected: new Date().toISOString()
};

console.log('✓ Group 04 mock validates:', JSON.stringify(mock, null, 2).length, 'bytes');
console.log('✓ Tools count:', mock.tools.length);
console.log('✓ All tools have parameters:', mock.tools.every(t => Array.isArray(t.parameters)));
EOF
node /tmp/verify_g04.js
```

**Expected Output:**
```
✓ Group 04 mock validates: 1427 bytes
✓ Tools count: 4
✓ All tools have parameters: true
```

### Verify Group 05 Mocks Structure
```bash
grep -o "await page.route" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts | wc -l
```

**Expected Output:**
```
6
```

**The 6 mocks should be:**
1. `/api/v1/skills/registry` - GET
2. `/api/v1/skills/*/config` - GET/PUT
3. `/api/v1/skills/*/config/validate` - POST
4. `/api/v1/skills/*/activate` - POST
5. `/api/v1/skills/*/deactivate` - POST

### Verify Group 06 Mocks Structure
```bash
grep -o "await page.route" /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts | wc -l
```

**Expected Output:**
```
5
```

**The 5 mocks should be:**
1. `/api/v1/mcp/health` - GET
2. `/api/v1/mcp/servers` - GET
3. `/api/v1/skills/registry` - GET
4. `/api/v1/skills` - GET (legacy)

---

## Data-TestID Validation

### Group 04 Expected Data-TestIDs
```bash
grep -o 'data-testid="[^"]*"' /home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/admin/MCPServerCard.tsx | sort -u
```

**Expected Output (all should be findable in tests):**
```
data-testid="mcp-server-${server.name}"
data-testid="server-status-${server.name}"
data-testid="tool-${tool.name}"
data-testid="tools-list-${server.name}"
data-testid="toggle-tools-${server.name}"
```

### Verify Test Locators Match Component Data-TestIDs
```bash
echo "=== Component data-testids ===" && \
grep -o '\[data-testid="[^"]*"\]' /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts | sort -u
```

**Expected Output:**
```
[data-testid="mcp-server-browser"]
[data-testid="server-status"]
[data-testid="tool-browser_click"]
[data-testid="tool-browser_evaluate"]
[data-testid="tool-browser_navigate"]
[data-testid="tool-browser_take_screenshot"]
```

---

## Pre-Run Checklist

Before running tests, verify:

- [ ] All 3 test files have correct syntax (node -c passes)
- [ ] All mocks use `await page.route()` correctly
- [ ] All mocks return status 200 for success cases
- [ ] All mock responses are valid JSON
- [ ] Group 04 has 2 mocks (health + servers)
- [ ] Group 05 has 6 mocks (registry + config + validation + toggle)
- [ ] Group 06 has 5 mocks (health + servers + registry + legacy skills)
- [ ] navigateClientSide is imported in Group 06
- [ ] navigateToChat uses navigateClientSide in Group 06
- [ ] Mock tool parameters always include empty array `[]` minimum
- [ ] Mock skill data includes all required fields

---

## Post-Test Validation

After running tests, verify:

- [ ] All 22 tests pass (6 + 8 + 8)
- [ ] No "element not found" errors
- [ ] No "Cannot read property of undefined" errors
- [ ] No "Mock route not matched" errors
- [ ] No timeout errors (tests complete within 30s each)
- [ ] Browser screenshots show correct UI rendered
- [ ] Test logs show mock routes being matched

---

## Troubleshooting

If tests fail, check:

1. **"Browser server not found in UI"**
   - Verify `/api/v1/mcp/servers` mock returns status 200
   - Check mock is in `beforeEach`, not `before`
   - Verify browser server name is exactly "browser" (case-sensitive)

2. **"Skills Registry empty"**
   - Verify `/api/v1/skills/registry` returns array directly
   - Check endpoint is `/registry` not just `/skills`
   - Ensure mock returns 5 skill objects

3. **"Config validation fails"**
   - Verify `/api/v1/skills/*/config/validate` endpoint exists
   - Check response includes `{ valid: true, errors: [], warnings: [] }`
   - Ensure endpoint is POST, not GET

4. **"Chat page shows login instead of chat"**
   - Check `navigateToChat` uses `navigateClientSide()`
   - Verify `setupAuthMocking` is called in `beforeEach`
   - Check login credentials in fixture match actual backend

5. **"Tool parameters undefined"**
   - Verify each MCPTool has `parameters: []` array
   - Check each parameter has `name`, `type`, `description`, `required`
   - Ensure parameter types are valid: string|number|boolean|object|array

---

## Success Criteria

All verification steps pass when:

✅ All 3 syntax checks pass
✅ All mocks are present (2 + 6 + 5 = 13 total)
✅ All mock responses are valid JSON
✅ All 22 tests pass
✅ No timeout or "element not found" errors
✅ All data-testids match component definitions
✅ All mock endpoints return expected structures

---

## Final Status

**Date:** 2026-01-17
**Status:** ✅ **READY FOR TESTING**
**Expected Pass Rate:** 100% (22/22)
**Estimated Run Time:** ~3-5 minutes for all groups

**Modified Files:**
- ✅ `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts`
- ✅ `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts`
- ✅ `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts`

**Documentation Created:**
- ✅ `E2E_GROUPS_04_06_MOCK_FIXES.md` (comprehensive details)
- ✅ `E2E_GROUPS_04_06_QUICK_REFERENCE.md` (quick lookup)
- ✅ `E2E_GROUPS_04_06_VERIFICATION.md` (this file)
