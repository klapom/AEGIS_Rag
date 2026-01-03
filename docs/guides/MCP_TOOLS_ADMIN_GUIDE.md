# MCP Tools Administration Guide

**Document:** Feature 72.1 - MCP Tool Management UI
**Status:** Complete
**Last Updated:** 2026-01-03

---

## Overview

The MCP Tools Admin page (`/admin/tools`) provides a unified interface for managing Model Context Protocol (MCP) servers and executing tools without requiring SSH access or command-line interaction. This guide covers server management, tool execution, and troubleshooting.

### Key Features

- **Real-time Server Health Monitoring:** View connection status of all MCP servers
- **Connect/Disconnect Management:** Add or remove MCP servers from the UI
- **Tool Execution Testing:** Execute tools with parameters and view results
- **Server Status Dashboard:** Monitor CPU, memory, and response latency
- **Responsive Design:** Works on desktop (two-column layout) and mobile (tab navigation)

---

## Navigation

### Accessing the MCP Tools Page

1. **From Admin Dashboard:**
   - Navigate to `https://your-domain/admin`
   - Click the **"Tools"** tab in the navigation bar
   - Or click **"Manage MCP Tools"** button (if available)

2. **Direct URL:**
   - `https://your-domain/admin/tools`

3. **Mobile Access:**
   - Same URL works on mobile with responsive tab interface
   - Tabs: "Servers" | "Execute"

### Layout Overview

#### Desktop (≥768px width)
```
┌─────────────────────────────────────────────────────────┐
│  Back Button  |  Health Monitor (Real-time)            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────┐  ┌──────────────────────────┐ │
│  │   MCP Server List    │  │  Tool Execution Panel    │ │
│  │ - Connect/Disconnect │  │ - Parameter Input        │ │
│  │ - Status Indicators  │  │ - Execute Button         │ │
│  │ - Health Metrics     │  │ - Result Display         │ │
│  └──────────────────────┘  └──────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Mobile (<768px width)
```
┌──────────────────────────────┐
│  Back | Servers | Execute     │
├──────────────────────────────┤
│                              │
│  [Tab Content - Switches]     │
│                              │
└──────────────────────────────┘
```

---

## Managing MCP Servers

### Server List Overview

The MCP Server List displays all available and connected servers:

| Column | Description | Example |
|--------|-------------|---------|
| **Server Name** | MCP server identifier | `filesystem`, `postgres_db`, `claude` |
| **Status** | Connection state (Connected/Disconnected) | Green badge = Connected |
| **Protocol** | Server protocol version | `mcp://2.0` |
| **Last Sync** | Time of last health check | `2 minutes ago` |
| **Actions** | Connect/Disconnect buttons | [Connect] or [Disconnect] |

### Connecting a Server

**Prerequisites:**
- MCP server must be configured in backend settings
- Server must be accessible (network reachable)
- Appropriate permissions required

**Steps:**

1. **Locate the server** in the server list
2. **Check current status:**
   - Green badge = Already connected
   - Gray badge = Disconnected
3. **Click [Connect] button** (only appears if disconnected)
4. **Wait for confirmation:**
   - Page updates with success message
   - Status changes to green "Connected"
   - ~2-5 seconds for connection establishment
5. **Verify health metrics appear**

**Example: Connecting Filesystem Server**

```
Server Name: filesystem
Status: [Disconnected] ← Click this
Protocol: mcp://2.0
Last Sync: -

↓ After clicking [Connect] ↓

Server Name: filesystem
Status: [Connected] ✓
Protocol: mcp://2.0
Last Sync: Just now
```

### Disconnecting a Server

1. **Locate the connected server** (green status badge)
2. **Click [Disconnect] button**
3. **Confirm disconnection** (if prompted)
4. **Verify status updates:**
   - Badge changes to gray
   - "Last Sync" resets to "-"

### Health Monitoring

The Health Monitor bar at the top displays real-time server metrics:

| Metric | Meaning | Range |
|--------|---------|-------|
| **CPU Usage** | Percentage of server CPU utilization | 0-100% (red if >80%) |
| **Memory** | Server process memory usage | Varies (red if >2GB) |
| **Response Time** | Average latency for tool execution | <100ms (green), <500ms (yellow), >500ms (red) |
| **Connected Servers** | Count of active connections | e.g., "3/5 connected" |

**Example Health Monitor:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ 3/5 Connected  │  CPU: 25%  │  Memory: 320MB  │  Avg Response: 45ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Executing Tools

The Tool Execution Panel allows you to test tools directly from the UI without command-line access.

### Tool Selection

1. **Click on a tool** in the server list (blue text)
2. Tool details load in the right panel:
   - Tool name
   - Description
   - Required/optional parameters
   - Example inputs

### Parameter Input

Each tool parameter has:
- **Label:** Parameter name
- **Type:** `string`, `integer`, `boolean`, `array`, `object`
- **Required:** (Red asterisk * if required)
- **Description:** Inline help text
- **Input Field:** Text box, dropdown, or JSON editor

**Examples:**

**String Parameter:**
```
Path ✱
Type: string
Description: File path to read (e.g., /home/user/data.txt)

[________________________________________]
```

**Integer Parameter:**
```
Timeout (seconds)
Type: integer
Description: Maximum execution time (default: 30)

[____]  (defaults to 30 if empty)
```

**Boolean Parameter:**
```
☐ Recursive
Type: boolean
Description: Apply operation recursively to subdirectories
```

**Object Parameter:**
```
Query Parameters
Type: object
Description: JSON object of search filters

{
  "field": "string_value",
  "count": 10
}
```

### Executing a Tool

1. **Fill all required parameters** (marked with *)
2. **Review parameter values** for correctness
3. **Click [Execute Tool] button**
4. **Wait for execution:**
   - Status shows "Executing..."
   - Progress bar displays
   - ~5-30 seconds typical
5. **View results:**
   - Success message (green)
   - Tool output displayed
   - Copy button for output

### Result Display

**Success Result:**
```
┌─────────────────────────────────────────────────────┐
│ ✓ Tool execution successful                         │
├─────────────────────────────────────────────────────┤
│ Output:                                             │
│ {                                                   │
│   "files": [                                        │
│     "/home/user/document.txt",                      │
│     "/home/user/data.json"                          │
│   ],                                                │
│   "count": 2,                                       │
│   "total_size": "1.2 MB"                           │
│ }                                                   │
│                                                     │
│ [Copy Output]  [New Execution]                     │
└─────────────────────────────────────────────────────┘
```

**Error Result:**
```
┌─────────────────────────────────────────────────────┐
│ ✗ Tool execution failed                             │
├─────────────────────────────────────────────────────┤
│ Error:                                              │
│ FileNotFoundError: Path does not exist:             │
│ /home/user/nonexistent.txt                         │
│                                                     │
│ [Retry with Different Path]                        │
└─────────────────────────────────────────────────────┘
```

---

## Common Use Cases

### Use Case 1: Listing Files in a Directory

**Scenario:** Check what files are available in the documents folder

**Steps:**
1. Select **"filesystem"** server
2. Select **"list_directory"** tool
3. Enter Path: `/data/documents`
4. Leave "Recursive" unchecked
5. Click **[Execute Tool]**

**Expected Output:**
```json
{
  "files": [
    "report.pdf",
    "analysis.xlsx",
    "notes.txt"
  ],
  "directories": ["archive"],
  "total": 4
}
```

### Use Case 2: Reading File Contents

**Scenario:** View the contents of a configuration file

**Steps:**
1. Select **"filesystem"** server
2. Select **"read_file"** tool
3. Enter Path: `/etc/app/config.json`
4. Click **[Execute Tool]**

**Expected Output:**
```json
{
  "content": "{\"debug\": true, \"port\": 8000}",
  "encoding": "utf-8",
  "size": 52
}
```

### Use Case 3: Querying a Database

**Scenario:** Test a SQL query against the production database

**Steps:**
1. Select **"postgres_db"** server
2. Select **"execute_query"** tool
3. Enter Query:
   ```sql
   SELECT COUNT(*) as total_documents FROM documents
   WHERE created_at > NOW() - INTERVAL '7 days'
   ```
4. Set Timeout: `10` (seconds)
5. Click **[Execute Tool]**

**Expected Output:**
```json
{
  "rows": [
    {"total_documents": 145}
  ],
  "execution_time_ms": 234,
  "affected_rows": 1
}
```

---

## Health Monitoring in Depth

### Health Check Mechanism

- **Automatic:** Every 30 seconds
- **On-Demand:** Click **[Refresh Health]** button
- **Triggers:** Connect/disconnect actions

### Interpreting Health Status

| Status | Icon | Color | Meaning | Action |
|--------|------|-------|---------|--------|
| Connected | ✓ | Green | Server operational | None |
| Disconnected | ✗ | Gray | Not connected | Click [Connect] |
| Degraded | ⚠ | Yellow | Slow/partial response | Monitor or reconnect |
| Failed | ✗ | Red | Connection failed | Check network/server |

### Performance Indicators

**Green Zone (Healthy):**
- Response time: <100ms
- CPU: <60%
- Memory: <500MB

**Yellow Zone (Acceptable):**
- Response time: 100-500ms
- CPU: 60-80%
- Memory: 500MB-1.5GB

**Red Zone (Attention Needed):**
- Response time: >500ms
- CPU: >80%
- Memory: >1.5GB

---

## Troubleshooting

### Issue: Server Shows "Disconnected" but Should Be Running

**Problem:** MCP server appears disconnected when you know it's running

**Diagnosis Steps:**

1. **Check backend logs:**
   ```bash
   docker logs aegis-rag-api | grep "mcp"
   ```

2. **Verify server process:**
   ```bash
   ps aux | grep "[m]cp"
   ```

3. **Test network connectivity:**
   ```bash
   curl -s http://localhost:YOUR_MCP_PORT/health
   ```

**Solutions:**

- **If logs show connection refused:** Start the MCP server
- **If process running but connection fails:** Check firewall rules
- **If health endpoint fails:** Restart MCP server container
  ```bash
  docker restart aegis-rag-mcp
  ```

### Issue: Tool Execution Times Out

**Problem:** Tool execution shows "Timeout exceeded" error

**Causes:**
- Timeout value too low
- Network latency to tool server
- Server overloaded
- Tool performing heavy operation

**Solutions:**

1. **Increase timeout value:**
   - Default: 30 seconds
   - Increase to 60 seconds for heavy operations
   - Maximum: 300 seconds (5 minutes)

2. **Check server load:**
   - View Health Monitor CPU/Memory
   - If >80% CPU, wait or restart server

3. **Simplify query:**
   - Reduce scope of operation
   - Add filtering parameters
   - Break into multiple smaller calls

### Issue: "Permission Denied" Error

**Problem:** Tool returns "Permission denied" when accessing files

**Causes:**
- User running MCP server lacks file permissions
- File owned by different user
- Directory lacks read permissions

**Solutions:**

```bash
# Check file ownership
ls -la /path/to/file

# Change permissions (if you own the file)
chmod 644 /path/to/file

# Run MCP server as different user
sudo -u username docker run ... aegis-rag-mcp
```

### Issue: Tool Parameters Not Accepted

**Problem:** Valid-looking parameters return "Invalid parameter" error

**Causes:**
- Wrong parameter type (e.g., string instead of integer)
- Special characters need escaping
- Object parameters malformed JSON
- Missing required fields

**Solutions:**

1. **Verify parameter types:**
   - Integer: No quotes, digits only
   - String: Use plain text (no extra quotes)
   - Object: Valid JSON, properly escaped

2. **Check for special characters:**
   - Paths with spaces: OK (handled automatically)
   - JSON: Escape internal quotes with backslash

3. **Review error message:**
   - Usually indicates which parameter failed
   - Follow format example shown in help text

### Issue: Health Metrics Not Updating

**Problem:** "Last Sync" time stays the same, metrics don't change

**Causes:**
- Health check disabled
- Server connection issue
- Client-side caching

**Solutions:**

1. **Manual refresh:**
   - Click **[Refresh Health]** button
   - Wait 5-10 seconds

2. **Check auto-refresh setting:**
   - Should be enabled by default
   - Contact admin if disabled

3. **Restart connection:**
   - Click [Disconnect]
   - Wait 2 seconds
   - Click [Connect]

### Issue: Cannot See All Available Tools

**Problem:** Tool list incomplete or missing expected tools

**Causes:**
- Server not fully connected
- Tool definitions not loaded
- Custom tool registration failed

**Solutions:**

1. **Check server status:** Must show "Connected"

2. **Refresh the page:** `Ctrl+R` or `Cmd+R`

3. **Check backend logs:**
   ```bash
   docker logs aegis-rag-api | grep "tool.*register"
   ```

4. **Reconnect server:**
   - Click [Disconnect] then [Connect]
   - This reloads all tool definitions

---

## Best Practices

### Server Management

1. **Minimize Active Connections:** Only keep needed servers connected
   - Reduces memory footprint
   - Improves health check speed
   - Simplifies troubleshooting

2. **Monitor Health Regularly:** Check metrics every 30 minutes
   - Catch degradation early
   - Identify problematic servers
   - Plan capacity upgrades

3. **Document Custom Tools:** Maintain a list of custom tools with:
   - Description
   - Required parameters
   - Common error codes
   - Example inputs/outputs

### Tool Execution

1. **Test Before Production Use:** Always test tool execution first
   - Verify output format
   - Check edge cases
   - Document results

2. **Use Conservative Timeouts:** Start high, reduce gradually
   - Prevents spurious failures
   - Better for user experience
   - Adjust based on actual performance

3. **Log All Executions:** Enable logging for auditing
   - Track who executed what
   - Debug issues after-the-fact
   - Comply with security policies

4. **Validate Parameters:** Double-check before execution
   - Verify file paths exist
   - Confirm query syntax
   - Escape special characters properly

---

## API Reference

### Backend Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/mcp/servers` | List all MCP servers |
| POST | `/api/v1/mcp/servers/{name}/connect` | Connect to a server |
| POST | `/api/v1/mcp/servers/{name}/disconnect` | Disconnect from a server |
| GET | `/api/v1/mcp/servers/{name}/health` | Get server health metrics |
| GET | `/api/v1/mcp/servers/{name}/tools` | List tools in a server |
| POST | `/api/v1/mcp/tools/execute` | Execute a tool |

### Example API Call

```bash
# List all servers
curl -X GET http://localhost:8000/api/v1/mcp/servers \
  -H "Authorization: Bearer YOUR_TOKEN"

# Execute a tool
curl -X POST http://localhost:8000/api/v1/mcp/tools/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "server": "filesystem",
    "tool": "read_file",
    "parameters": {
      "path": "/data/documents/report.txt"
    },
    "timeout": 30
  }'
```

---

## FAQ

**Q: Can I execute tools from the main search interface?**
A: No, tool execution is only available from the `/admin/tools` page for security reasons.

**Q: What happens if a tool execution fails mid-way?**
A: The operation is stopped and rolled back (if applicable). You can retry from the UI.

**Q: Can I create new MCP servers from the UI?**
A: No, server configuration requires backend setup. Use the config file and restart the backend.

**Q: How long are tool execution logs kept?**
A: 30 days by default. Adjust in settings under "Admin > Logging".

**Q: Can I execute multiple tools in parallel?**
A: You can start one tool and open another browser tab to execute a different tool, but they run independently.

**Q: Is there a rate limit on tool executions?**
A: Yes, default is 10 executions per minute per user. Contact admin to adjust.

---

## Related Documentation

- [Admin Dashboard Guide](./ADMIN_DASHBOARD_GUIDE.md)
- [Memory Management Guide](./MEMORY_MANAGEMENT_GUIDE.md)
- [API Documentation](../api/admin.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

---

**Document Version:** 1.0
**Feature:** Sprint 72.1
**Compatibility:** Frontend React 19, Backend FastAPI 0.115+
