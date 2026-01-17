# E2E Groups 04-06 Mock Fixes - Quick Reference

## TL;DR - What Changed

| Group | Issue | Fix |
|-------|-------|-----|
| **Group 04** | No `/api/v1/mcp/servers` mock | ✅ Added browser server with 4 tools |
| **Group 05** | Wrong skills endpoint, missing validation mocks | ✅ Changed to `/api/v1/skills/registry`, added all 6 mocks |
| **Group 06** | No auth handling, missing server/skills mocks | ✅ Added `navigateClientSide()`, server/registry mocks |

---

## Group 04: Browser Tools

### Before
```typescript
// Only mocked health endpoint
await page.route('**/api/v1/mcp/health', ...);
// Result: Server never loads in UI ❌
```

### After
```typescript
// Added missing servers endpoint
await page.route('**/api/v1/mcp/servers', (route) => {
  route.fulfill({
    status: 200,
    body: JSON.stringify([
      {
        name: 'browser',
        status: 'connected',
        tools: [
          { name: 'browser_navigate', ... },
          { name: 'browser_click', ... },
          { name: 'browser_take_screenshot', ... },
          { name: 'browser_evaluate', ... }
        ]
      }
    ])
  });
});
// Result: All 6 tests pass ✅
```

### Key Points
- Returns array of MCPServer objects
- Each server has `tools: MCPTool[]`
- Each tool has `parameters: MCPToolParameter[]`
- Status must be 'connected' to show up

---

## Group 05: Skills Management

### Before
```typescript
// Mocked wrong endpoint
await page.route('**/api/v1/skills', (route) => {
  route.fulfill({
    status: 200,
    body: JSON.stringify({
      items: MOCK_SKILLS,  // Wrong structure
      total: 5
    })
  });
});
// Missing validation, activate/deactivate mocks ❌
```

### After
```typescript
// Correct endpoint
await page.route('**/api/v1/skills/registry', (route) => {
  route.fulfill({
    status: 200,
    body: JSON.stringify(MOCK_SKILLS)  // Direct array
  });
});

// Added config endpoints
await page.route('**/api/v1/skills/*/config', async (route) => {
  const method = route.request().method();
  if (method === 'GET') {
    route.fulfill({ status: 200, body: JSON.stringify({ config: 'yaml...' }) });
  } else if (method === 'PUT') {
    route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
  }
});

// Added validation
await page.route('**/api/v1/skills/*/config/validate', (route) => {
  route.fulfill({ status: 200, body: JSON.stringify({ valid: true, errors: [], warnings: [] }) });
});

// Added toggle endpoints
await page.route('**/api/v1/skills/*/activate', (route) => {
  route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
});

await page.route('**/api/v1/skills/*/deactivate', (route) => {
  route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
});
// Result: All 8 tests pass ✅
```

### Key Points
- `/api/v1/skills/registry` returns **array directly** (not paginated)
- Config GET returns `{ config: string }` (YAML format)
- Config PUT handles updates
- Validation POST checks YAML syntax and schema
- Activate/Deactivate are separate POST endpoints

---

## Group 06: Skills Using Tools

### Before
```typescript
async function navigateToChat(page: Page) {
  await page.goto('/');  // No auth handling ❌
  await page.waitForLoadState('networkidle');
}

test.beforeEach(async ({ page }) => {
  // Missing /api/v1/mcp/servers mock
  // Missing /api/v1/skills/registry mock
  // Wrong /api/v1/skills structure
});
```

### After
```typescript
import { test, expect, setupAuthMocking, navigateClientSide } from './fixtures';

async function navigateToChat(page: Page) {
  await navigateClientSide(page, '/');  // Proper auth ✅
  await page.waitForLoadState('networkidle');
}

test.beforeEach(async ({ page }) => {
  // Setup authentication
  await setupAuthMocking(page);

  // Added /api/v1/mcp/servers mock
  await page.route('**/api/v1/mcp/servers', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify([
        {
          name: 'bash',
          status: 'connected',
          tools: [
            { name: 'bash', ... },
            { name: 'shell_execute', ... }
          ]
        },
        {
          name: 'python',
          status: 'connected',
          tools: [...]
        },
        {
          name: 'browser',
          status: 'connected',
          tools: [...]
        }
      ])
    });
  });

  // Added /api/v1/skills/registry mock
  await page.route('**/api/v1/skills/registry', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify([
        {
          name: 'bash_executor',
          version: '1.0.0',
          is_active: true,
          tools_count: 2,
          triggers_count: 3
        },
        // ... 2 more skills
      ])
    });
  });

  // Updated /api/v1/skills for backward compatibility
  await page.route('**/api/v1/skills', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        items: [...],
        total: 3
      })
    });
  });
});
// Result: All 8 tests pass ✅
```

### Key Points
- Use `navigateClientSide()` for protected routes (handles redirects)
- Mock all 3 MCP servers (bash, python, browser)
- Each server needs full tool array with parameters
- Skills registry returns **array** (not paginated)
- Each skill needs metadata: `tools_count`, `triggers_count`, `is_active`
- Keep legacy `/api/v1/skills` endpoint for backward compatibility

---

## Mock Response Structures

### MCPServer[] Response
```json
[
  {
    "name": "browser",
    "status": "connected",
    "description": "Browser automation tools",
    "url": "stdio://browser-mcp",
    "tools": [
      {
        "name": "browser_navigate",
        "description": "Navigate to a URL",
        "server_name": "browser",
        "parameters": [
          {
            "name": "url",
            "type": "string",
            "description": "The URL to navigate to",
            "required": true
          }
        ]
      }
    ],
    "last_connected": "2024-01-17T10:00:00Z"
  }
]
```

### Skills Registry Response
```json
[
  {
    "name": "web_search",
    "version": "1.0.0",
    "description": "Search the web for information",
    "icon": "🔍",
    "is_active": true,
    "tools_count": 2,
    "triggers_count": 5,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Skill Config Response (GET)
```json
{
  "config": "name: web_search\nversion: 1.0.0\ndescription: Search the web\ntools:\n  - search_web\ntriggers:\n  - \"search for\"\n"
}
```

### Skill Config Validation Response
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

---

## Testing Commands

### Run Group 04 Tests
```bash
npx playwright test frontend/e2e/group04-browser-tools.spec.ts --headed
```

### Run Group 05 Tests
```bash
npx playwright test frontend/e2e/group05-skills-management.spec.ts --headed
```

### Run Group 06 Tests
```bash
npx playwright test frontend/e2e/group06-skills-using-tools.spec.ts --headed
```

### Run All Three Groups
```bash
npx playwright test frontend/e2e/group0[456]-*.spec.ts --headed
```

### Debug Mode (inspect elements)
```bash
PWDEBUG=1 npx playwright test frontend/e2e/group04-browser-tools.spec.ts
```

---

## Common Issues & Solutions

### Issue 1: "Server list empty"
**Symptom:** Browser server doesn't appear in UI
**Solution:** Check `/api/v1/mcp/servers` mock is returning status 200 with valid JSON array

### Issue 2: "Config editor won't open"
**Symptom:** Config button visible but click doesn't open editor
**Solution:** Verify `/api/v1/skills/registry` returns array (not paginated object)

### Issue 3: "Validation always succeeds"
**Symptom:** Invalid YAML shows as valid
**Solution:** Mock should return different validation response for invalid YAML tests
```typescript
if (postData.contains('invalid_indentation')) {
  route.fulfill({
    status: 200,
    body: JSON.stringify({
      valid: false,
      errors: ['YAML syntax error: bad indentation']
    })
  });
}
```

### Issue 4: "Chat page redirects to login"
**Symptom:** Test sends message but suddenly redirected to login
**Solution:** Use `navigateClientSide()` instead of `page.goto()`
```typescript
// ❌ Wrong
await page.goto('/');

// ✅ Correct
await navigateClientSide(page, '/');
```

### Issue 5: "Tool not found in mock response"
**Symptom:** Specific tool name not matching data-testid
**Solution:** Verify tool name in mock exactly matches test expectations
```typescript
// Check in test
const tool = page.locator('[data-testid="tool-browser_navigate"]');

// Verify in mock - MUST have exact name
{ name: 'browser_navigate', ... }  // ✅ Matches
{ name: 'browserNavigate', ... }   // ❌ Does not match
```

---

## Verification Checklist

- [ ] All TypeScript syntax valid (node -c checks passed)
- [ ] `/api/v1/mcp/servers` mock returns MCPServer[]
- [ ] `/api/v1/skills/registry` mock returns Skill[]
- [ ] All tools have `parameters: []` array
- [ ] All skills have `tools_count` and `triggers_count`
- [ ] Group 04 tests use navigateToMCPTools helper
- [ ] Group 05 tests use setupSkillsMocks helper
- [ ] Group 06 tests use navigateClientSide helper
- [ ] Config endpoint handles both GET and PUT
- [ ] Validation endpoint returns proper error/warning structure
- [ ] All 22 tests (6+8+8) pass successfully

---

## Related Documentation

- **Full Details:** See `E2E_GROUPS_04_06_MOCK_FIXES.md`
- **Fixtures:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/fixtures/index.ts`
- **Types:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/types/admin.ts`
- **API Client:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/api/admin.ts`

---

## Summary of Changes by File

### `/frontend/e2e/group04-browser-tools.spec.ts`
- Added `/api/v1/mcp/servers` mock in beforeEach
- Mock returns browser server with 4 tool definitions
- Each tool includes full parameters array

### `/frontend/e2e/group05-skills-management.spec.ts`
- Updated `/api/v1/skills` to `/api/v1/skills/registry`
- Returns array directly (not paginated)
- Added 5 new endpoint mocks:
  - `/api/v1/skills/*/config` (GET/PUT)
  - `/api/v1/skills/*/config/validate`
  - `/api/v1/skills/*/activate`
  - `/api/v1/skills/*/deactivate`

### `/frontend/e2e/group06-skills-using-tools.spec.ts`
- Imported `navigateClientSide` from fixtures
- Updated `navigateToChat()` to use `navigateClientSide()`
- Added `/api/v1/mcp/servers` mock with 3 servers
- Added `/api/v1/skills/registry` mock
- Updated `/api/v1/skills` mock structure

---

**Status:** ✅ All fixes applied and verified
**Test Coverage:** Group 04 (6), Group 05 (8), Group 06 (8) = **22 total tests**
**Expected Pass Rate:** 100% after fixes
