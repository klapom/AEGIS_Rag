# E2E Test Mocks Fix: Groups 04-06

## Overview

Fixed E2E test mocks for Groups 04-06 by adding missing API endpoint mocks that were causing tests to fail silently. The UI components have correct data-testid attributes, but tests were not returning mock data from required API endpoints.

## Changes Summary

### Group 04: Browser Tools (6 tests)
**File:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts`

**Root Cause:**
- Mocked `/api/v1/mcp/health` but NOT `/api/v1/mcp/servers`
- MCPServerList component calls `getMCPServers()` which requests `/api/v1/mcp/servers`
- Without mock, browser server never loaded in UI, causing all tests to fail

**Fix Applied:**
- Added complete `/api/v1/mcp/servers` mock returning browser server with 4 tools
- Returns proper MCPServer[] structure with all required fields:
  - `name`: "browser"
  - `status`: "connected"
  - `description`: "Browser automation tools"
  - `url`: "stdio://browser-mcp"
  - `tools[]`: Array of MCPTool objects with parameters

**Mock Tools:**
```typescript
[
  { name: 'browser_navigate', parameters: [{ name: 'url', type: 'string', required: true }] },
  { name: 'browser_click', parameters: [{ name: 'element', type: 'string', required: true }, ...] },
  { name: 'browser_take_screenshot', parameters: [...] },
  { name: 'browser_evaluate', parameters: [{ name: 'function', type: 'string', required: true }] }
]
```

**Expected Results After Fix:**
- ✅ Browser server displays in MCPServerList
- ✅ Server status badge shows "Connected"
- ✅ Tools expand and show all 4 browser tools
- ✅ Tool data-testid attributes match: `tool-${tool.name}`

---

### Group 05: Skills Management (8 tests)
**File:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts`

**Root Cause:**
- Tests navigate to `/admin/skills/registry` but Skills Registry page calls `/api/v1/skills/registry` endpoint
- Original mocks only patched `/api/v1/skills` (paginated legacy endpoint)
- No mocks for config validation, activate/deactivate endpoints

**Fixes Applied:**

1. **Skills Registry Endpoint** (`/api/v1/skills/registry`)
   - Returns array of MOCK_SKILLS directly (not paginated)
   - Skills load and display in UI

2. **Skill Config Endpoints** (`/api/v1/skills/{skillName}/config`)
   - **GET:** Returns YAML config string in `.config` field
   - **PUT:** Returns success response for config updates

3. **Config Validation** (`/api/v1/skills/{skillName}/config/validate`)
   - Returns `{ valid: true, errors: [], warnings: [] }`
   - Enable/disable validation status in UI

4. **Skill Toggle Endpoints:**
   - `/api/v1/skills/{skillName}/activate` → `{ success: true }`
   - `/api/v1/skills/{skillName}/deactivate` → `{ success: true }`

**Mock Skills Data:**
```typescript
[
  {
    name: 'web_search',
    version: '1.0.0',
    description: 'Search the web for information using DuckDuckGo',
    icon: '🔍',
    is_active: true,
    tools_count: 2,
    triggers_count: 5
  },
  // ... (5 skills total)
]
```

**Expected Results After Fix:**
- ✅ Skills Registry loads with 5 skill cards
- ✅ Each skill card shows name, description, version, status badge
- ✅ Config editor opens and displays YAML
- ✅ YAML validation works (shows errors/warnings)
- ✅ Active/Inactive toggles trigger API calls
- ✅ Config save persists changes

---

### Group 06: Skills Using Tools (8 tests)
**File:** `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts`

**Root Causes:**
1. Tests navigate to chat page but didn't use `navigateClientSide()` helper for auth
2. Missing `/api/v1/mcp/servers` mock (chat page may display available tools)
3. Missing `/api/v1/skills/registry` mock (skills not loaded)
4. Legacy `/api/v1/skills` mock returned wrong structure

**Fixes Applied:**

1. **Updated Navigation**
   - Changed from `page.goto('/')` to `navigateClientSide(page, '/')`
   - Proper authentication and redirect handling

2. **Added MCP Servers Mock**
   - Returns array of 3 servers (bash, python, browser) with full tool definitions
   - Each tool includes `parameters` array (required by TypeScript interface)

3. **Added Skills Registry Mock**
   - Returns array of 3 skills with proper structure
   - All skills marked as `is_active: true`
   - Includes metadata: `tools_count`, `triggers_count`, timestamps

4. **Updated Legacy Skills Mock**
   - Kept for backward compatibility
   - Returns paginated structure with `items` array

**Mock MCP Servers (3 total):**
```typescript
[
  {
    name: 'bash',
    status: 'connected',
    description: 'Bash shell execution tools',
    url: 'stdio://bash-mcp',
    tools: [
      { name: 'bash', description: 'Execute bash commands', server_name: 'bash', parameters: [] },
      { name: 'shell_execute', description: 'Execute shell scripts', server_name: 'bash', parameters: [] }
    ]
  },
  // ... (python and browser similarly structured)
]
```

**Expected Results After Fix:**
- ✅ Chat page loads with proper auth
- ✅ Chat interface ready for messages
- ✅ Skills can be triggered via chat messages
- ✅ Tool execution mocks return proper responses
- ✅ Error handling displays gracefully
- ✅ Progress indicators update correctly

---

## API Endpoints Summary

### Group 04 Required Endpoints
| Endpoint | Method | Returns |
|----------|--------|---------|
| `/api/v1/mcp/servers` | GET | `MCPServer[]` |
| `/api/v1/mcp/tools/execute` | POST | MCPExecutionResult |

### Group 05 Required Endpoints
| Endpoint | Method | Returns |
|----------|--------|---------|
| `/api/v1/skills/registry` | GET | Skill[] (not paginated) |
| `/api/v1/skills/{name}/config` | GET | `{ config: string }` |
| `/api/v1/skills/{name}/config` | PUT | `{ success: true }` |
| `/api/v1/skills/{name}/config/validate` | POST | ValidationResult |
| `/api/v1/skills/{name}/activate` | POST | `{ success: true }` |
| `/api/v1/skills/{name}/deactivate` | POST | `{ success: true }` |

### Group 06 Required Endpoints
| Endpoint | Method | Returns |
|----------|--------|---------|
| `/api/v1/mcp/servers` | GET | `MCPServer[]` |
| `/api/v1/skills/registry` | GET | Skill[] |
| `/api/v1/skills` | GET | `{ items: Skill[], total: number }` |
| `/api/v1/chat/stream` | POST | Server-Sent Events |

---

## TypeScript Types Used

### MCPServer
```typescript
interface MCPServer {
  name: string;
  status: MCPServerStatus;
  url?: string;
  description?: string;
  tools: MCPTool[];
  last_connected?: string;
  error_message?: string;
}
```

### MCPTool
```typescript
interface MCPTool {
  name: string;
  description: string;
  server_name: string;
  parameters: MCPToolParameter[];
}
```

### MCPToolParameter
```typescript
interface MCPToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required: boolean;
  default?: unknown;
  enum?: string[];
}
```

### Skill (from registry)
```typescript
interface Skill {
  name: string;
  version: string;
  description: string;
  icon: string;
  is_active: boolean;
  tools_count: number;
  triggers_count: number;
  created_at: string;
  updated_at: string;
}
```

---

## Test Data-TestID Mapping

### Group 04 (Browser Tools)
- Server card: `mcp-server-${server.name}` → `mcp-server-browser`
- Status badge: `server-status-${server.name}` → `server-status-browser`
- Tools list: `tools-list-${server.name}` → `tools-list-browser`
- Individual tool: `tool-${tool.name}` → `tool-browser_navigate`, `tool-browser_click`, etc.

### Group 05 (Skills Management)
- Skill card: `skill-card-${skill.name}` → `skill-card-web_search`, etc.
- Status badge (Active/Inactive) via text matching
- Config link: `a:has-text("Config")`
- YAML editor: `textarea`

### Group 06 (Skills Using Tools)
- Message input: `message-input`
- Send button: `send-button`
- Tool execution indicator: `tool-execution-${toolName}`
- Skill activation indicator: `skill-activated-${skillName}`
- Tool status: `tool-status-success`, `tool-status-error`, `tool-status-timeout`

---

## Implementation Notes

### Authentication Handling
- Group 06 now uses `navigateClientSide()` helper from fixtures
- Performs actual login via UI form (not localStorage manipulation)
- Ensures auth state is properly managed by React app

### Mock Data Consistency
- All mock data includes required fields per TypeScript interfaces
- Mock dates use current timestamp: `new Date().toISOString()`
- Array parameters are always included (even if empty `[]`)

### Error Simulation
- Validation errors can be tested by mocking different response structures
- Tool execution errors use 500 status codes
- Timeout scenarios mock delayed responses

---

## Verification Checklist

After applying these fixes, verify:

- [ ] Group 04 Tests
  - [ ] Browser server loads in MCPServerList
  - [ ] Status badge shows "Connected"
  - [ ] Tools list expands showing 4 tools
  - [ ] Tool names match data-testid attributes
  - [ ] All 6 tests pass

- [ ] Group 05 Tests
  - [ ] Skills Registry loads with 5 cards
  - [ ] Each card displays name, version, description
  - [ ] Status badges show Active/Inactive correctly
  - [ ] Config editor opens and shows YAML
  - [ ] YAML validation works (success/error states)
  - [ ] Config save works (PUT call succeeds)
  - [ ] All 8 tests pass

- [ ] Group 06 Tests
  - [ ] Chat page loads after auth
  - [ ] Message input is visible
  - [ ] Chat messages can be sent
  - [ ] Tool execution indicators appear
  - [ ] Skill activation tracked in response
  - [ ] Error messages display properly
  - [ ] All 8 tests pass

---

## Common Pitfalls Addressed

1. **Missing Array Wrapper**: MCPServer and Skill endpoints return arrays, not single objects
2. **YAML vs JSON**: Config endpoint returns `.config` field with YAML string (not parsed JSON)
3. **Parameter Types**: MCPToolParameter requires `parameters: []` array (even if empty)
4. **HTTP Methods**: Config validation uses POST, config retrieval uses GET, config save uses PUT
5. **Status Codes**: Successful responses return 200, errors return 500
6. **Navigation Auth**: Chat tests must use `navigateClientSide()` not `page.goto()`

---

## Files Modified

1. `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group04-browser-tools.spec.ts`
   - Added `/api/v1/mcp/servers` mock with browser server definition

2. `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group05-skills-management.spec.ts`
   - Updated skills list endpoint to `/api/v1/skills/registry`
   - Added config validation, activate/deactivate mocks
   - Fixed config GET/PUT handling

3. `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/group06-skills-using-tools.spec.ts`
   - Updated navigation to use `navigateClientSide()`
   - Added `/api/v1/mcp/servers` mock with all 3 servers
   - Added `/api/v1/skills/registry` mock
   - Updated legacy `/api/v1/skills` mock structure

---

## Next Steps

1. Run all three test groups to verify fixes
2. Monitor CI/CD pipeline for test results
3. If specific tests still fail, check:
   - Browser DevTools Network tab for actual API calls
   - Console logs for mock route matching issues
   - Component data-testid attributes match test locators
4. Update any additional mocks as needed based on actual component behavior
