# MCP (Model Context Protocol) Component

**Sprint 18:** External Tool Integration via MCP Protocol
**Architecture:** Multi-Server MCP Client with stdio/HTTP transports
**Performance:** <50ms tool discovery, <200ms tool execution overhead

---

## Overview

The MCP Component provides **Model Context Protocol (MCP) client** for connecting to external MCP servers and executing tool calls.

### Key Features

- **Multi-Server Support:** Connect to multiple MCP servers simultaneously
- **Dual Transport:** stdio (subprocess) and HTTP transports
- **Tool Discovery:** Automatic tool enumeration from servers
- **Error Handling:** Retry logic, timeout management, connection pooling
- **Statistics Tracking:** Tool call latency, success rates, server health

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   MCP Client Architecture                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │             MCPClient (Connection Manager)           │  │
│  │                                                       │  │
│  │  • Multi-server management                           │  │
│  │  • Transport abstraction (stdio/HTTP)                │  │
│  │  • Connection lifecycle (connect/disconnect)         │  │
│  └──────────────────────────────────────────────────────┘  │
│                      │                                       │
│        ┌─────────────┴─────────────┐                        │
│        ▼                           ▼                         │
│  ┌──────────────┐           ┌──────────────┐               │
│  │   stdio      │           │     HTTP     │               │
│  │  Transport   │           │   Transport  │               │
│  │              │           │              │               │
│  │  Subprocess  │           │  httpx.Client│               │
│  │  stdin/stdout│           │  REST API    │               │
│  └──────────────┘           └──────────────┘               │
│        │                           │                        │
│        └─────────────┬─────────────┘                        │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              External MCP Servers                    │  │
│  │                                                       │  │
│  │  • Filesystem Server (read/write files)             │  │
│  │  • Browser Server (web automation)                   │  │
│  │  • Database Server (SQL queries)                     │  │
│  │  • Custom Servers (domain-specific tools)           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Files

| File | Purpose | LOC |
|------|---------|-----|
| `client.py` | Main MCP client & connection manager | 650 |
| `connection_manager.py` | Server lifecycle management | 350 |
| `tool_executor.py` | Tool call execution & error handling | 450 |
| `error_handler.py` | Retry logic & exception handling | 280 |
| `result_parser.py` | Tool result parsing & validation | 220 |
| `models.py` | Pydantic models (MCPServer, MCPTool, etc.) | 380 |
| `types.py` | Type definitions & enums | 120 |

**Total:** ~2,450 lines of code

---

## MCP Client

### Overview

`MCPClient` manages connections to multiple MCP servers and tool execution.

### Usage

```python
from src.components.mcp.client import MCPClient
from src.components.mcp.models import MCPServer, TransportType

# Initialize client
client = MCPClient()

# Configure MCP servers
filesystem_server = MCPServer(
    name="filesystem",
    transport=TransportType.STDIO,
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"],
    retry_attempts=3,
    timeout=30
)

http_server = MCPServer(
    name="custom-api",
    transport=TransportType.HTTP,
    url="http://localhost:3000/mcp",
    headers={"Authorization": "Bearer token123"},
    timeout=10
)

# Connect to servers
await client.connect(filesystem_server)
await client.connect(http_server)

# Discover available tools
tools = await client.discover_tools("filesystem")
# Returns: List[MCPTool]
# [
#   MCPTool(name="read_file", description="Read file contents", ...),
#   MCPTool(name="write_file", description="Write file contents", ...),
#   ...
# ]

# Execute tool call
result = await client.execute_tool(
    server_name="filesystem",
    tool_name="read_file",
    arguments={"path": "/docs/README.md"}
)

# Result: MCPToolResult
print(result.success)  # True
print(result.content)  # File contents
print(result.execution_time_ms)  # 45.2

# Disconnect
await client.disconnect("filesystem")
```

### Server Configuration

**stdio Transport (Subprocess):**
```python
MCPServer(
    name="filesystem",
    transport=TransportType.STDIO,
    command="npx",  # Command to spawn subprocess
    args=["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
    env={"NODE_ENV": "production"},  # Environment variables
    retry_attempts=3,
    timeout=30  # seconds
)
```

**HTTP Transport (REST API):**
```python
MCPServer(
    name="custom-api",
    transport=TransportType.HTTP,
    url="http://localhost:3000/mcp",
    headers={"Authorization": "Bearer secret-token"},
    timeout=10,  # seconds
    retry_attempts=2
)
```

---

## Tool Discovery

### Overview

Automatic tool enumeration from connected MCP servers.

### Discovery Process

```python
# Discover all tools from all connected servers
all_tools = await client.discover_all_tools()

# Returns: Dict[str, List[MCPTool]]
# {
#   "filesystem": [
#     MCPTool(name="read_file", ...),
#     MCPTool(name="write_file", ...),
#     MCPTool(name="list_directory", ...)
#   ],
#   "database": [
#     MCPTool(name="execute_query", ...),
#     MCPTool(name="list_tables", ...)
#   ]
# }

# Filter tools by capability
file_tools = [
    tool for server_tools in all_tools.values()
    for tool in server_tools
    if "file" in tool.name.lower()
]
```

### Tool Schema

```python
from src.components.mcp.models import MCPTool

class MCPTool(BaseModel):
    name: str                      # Tool identifier (e.g., "read_file")
    description: str               # Human-readable description
    input_schema: dict             # JSON Schema for tool arguments
    output_schema: dict | None     # JSON Schema for tool results (optional)
    server_name: str               # Source MCP server

# Example input_schema:
{
  "type": "object",
  "properties": {
    "path": {"type": "string", "description": "File path"},
    "encoding": {"type": "string", "default": "utf-8"}
  },
  "required": ["path"]
}
```

---

## Tool Execution

### Overview

Execute tool calls with error handling, retries, and timeouts.

### Basic Execution

```python
# Execute tool
result = await client.execute_tool(
    server_name="filesystem",
    tool_name="read_file",
    arguments={"path": "/docs/README.md"}
)

# Check result
if result.success:
    print(f"Content: {result.content}")
else:
    print(f"Error: {result.error}")
    print(f"Error type: {result.error_type}")  # "timeout" | "connection" | "validation"
```

### Batch Execution

```python
# Execute multiple tools in parallel
tool_calls = [
    MCPToolCall(
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "/docs/README.md"}
    ),
    MCPToolCall(
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "/docs/INSTALL.md"}
    )
]

results = await client.execute_batch(tool_calls)

# Returns: List[MCPToolResult]
for result in results:
    print(f"Tool: {result.tool_name}, Success: {result.success}")
```

### Error Handling

```python
from src.components.mcp.error_handler import MCPErrorHandler

error_handler = MCPErrorHandler(
    max_retries=3,
    retry_delay=1.0,  # seconds
    exponential_backoff=True
)

# Execute with retry logic
result = await error_handler.execute_with_retry(
    tool_call=tool_call,
    executor=client.execute_tool
)
```

---

## Connection Management

### Server Lifecycle

```python
# Connect to server
await client.connect(server)

# Check connection status
status = client.get_server_status("filesystem")
# Returns: ServerStatus.CONNECTED | DISCONNECTED | ERROR

# Health check
is_healthy = await client.is_server_healthy("filesystem")

# Reconnect (auto-retry)
await client.reconnect("filesystem")

# Disconnect
await client.disconnect("filesystem")

# Disconnect all servers
await client.disconnect_all()
```

### Connection Pooling

```python
# HTTP transport uses connection pooling automatically
http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    ),
    timeout=httpx.Timeout(10.0)
)

# Reuse client across multiple tool calls
for i in range(100):
    result = await client.execute_tool(
        server_name="custom-api",
        tool_name="fetch_data",
        arguments={"id": i}
    )
    # Connection pooling ensures fast execution
```

---

## Statistics & Monitoring

### Client Statistics

```python
# Get client statistics
stats = client.get_stats()

# MCPClientStats
print(f"Total servers: {stats.total_servers}")
print(f"Connected servers: {stats.connected_servers}")
print(f"Total tool calls: {stats.total_tool_calls}")
print(f"Successful calls: {stats.successful_calls}")
print(f"Failed calls: {stats.failed_calls}")
print(f"Average latency: {stats.avg_tool_call_ms:.2f}ms")
```

### Per-Tool Statistics

```python
# Tool execution metrics
tool_stats = client.get_tool_stats("filesystem", "read_file")

print(f"Executions: {tool_stats.execution_count}")
print(f"Success rate: {tool_stats.success_rate:.2%}")
print(f"Avg latency: {tool_stats.avg_latency_ms:.2f}ms")
print(f"p95 latency: {tool_stats.p95_latency_ms:.2f}ms")
```

---

## Integration with LLM Agents

### Tool Call from LLM

```python
from ollama import AsyncClient
from src.components.mcp.client import MCPClient

# Initialize MCP client
mcp_client = MCPClient()
await mcp_client.connect(filesystem_server)

# Get available tools for LLM
tools = await mcp_client.discover_all_tools()
tool_schemas = [
    {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema
    }
    for server_tools in tools.values()
    for tool in server_tools
]

# LLM with tools
ollama_client = AsyncClient()
response = await ollama_client.chat(
    model="llama3.2:8b",
    messages=[
        {"role": "user", "content": "Read the README.md file"}
    ],
    tools=tool_schemas
)

# Execute tool call from LLM response
if response.tool_calls:
    for tool_call in response.tool_calls:
        result = await mcp_client.execute_tool(
            server_name="filesystem",  # Infer from tool name
            tool_name=tool_call.name,
            arguments=tool_call.arguments
        )

        # Feed result back to LLM
        follow_up = await ollama_client.chat(
            model="llama3.2:8b",
            messages=[
                {"role": "user", "content": "Read the README.md file"},
                {"role": "assistant", "tool_calls": [tool_call]},
                {"role": "tool", "content": result.content}
            ]
        )
```

---

## MCP Server Examples

### Official MCP Servers

**Filesystem Server:**
```bash
# Install
npm install -g @modelcontextprotocol/server-filesystem

# Run (stdio)
npx @modelcontextprotocol/server-filesystem /path/to/allowed/directory
```

**Browser Automation Server:**
```bash
# Install Puppeteer-based MCP server
npm install -g @modelcontextprotocol/server-puppeteer

# Run
npx @modelcontextprotocol/server-puppeteer
```

**Database Server:**
```bash
# Install PostgreSQL MCP server
npm install -g @modelcontextprotocol/server-postgres

# Run
npx @modelcontextprotocol/server-postgres postgresql://user:password@localhost/dbname
```

### Custom MCP Server

```typescript
// custom-mcp-server.ts
import { Server } from "@modelcontextprotocol/sdk";

const server = new Server({
  name: "custom-tools",
  version: "1.0.0"
});

// Define tool
server.tool({
  name: "process_data",
  description: "Process data with custom logic",
  input_schema: {
    type: "object",
    properties: {
      data: { type: "string" },
      format: { type: "string", enum: ["json", "csv"] }
    },
    required: ["data"]
  }
}, async (input) => {
  // Tool logic
  const result = await processData(input.data, input.format);
  return { success: true, result };
});

// Start server (stdio)
server.listen();
```

---

## Testing

### Unit Tests

```bash
# Test MCP client
pytest tests/unit/components/mcp/test_client.py

# Test connection manager
pytest tests/unit/components/mcp/test_connection_manager.py

# Test tool executor
pytest tests/unit/components/mcp/test_tool_executor.py

# Test error handling
pytest tests/unit/components/mcp/test_error_handler.py
```

### Integration Tests

```bash
# Test stdio transport with real MCP server
pytest tests/integration/components/mcp/test_stdio_transport.py

# Test HTTP transport
pytest tests/integration/components/mcp/test_http_transport.py
```

**Test Coverage:** 80% (62 unit tests, 18 integration tests)

---

## Configuration

### Environment Variables

```bash
# MCP Client
MCP_ENABLED=true
MCP_DEFAULT_TIMEOUT=30  # seconds
MCP_MAX_RETRIES=3
MCP_RETRY_DELAY=1.0

# Logging
MCP_LOG_LEVEL=INFO
MCP_LOG_TOOL_CALLS=true
```

---

## Security Considerations

### Filesystem Server Security

**Path Restriction:**
```python
# ONLY allow access to specific directory
filesystem_server = MCPServer(
    name="filesystem",
    transport=TransportType.STDIO,
    command="npx",
    args=[
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/safe/allowed/directory"  # RESTRICT to this path
    ]
)

# MCP server enforces path restriction
# Tool calls to /etc/passwd or ../../../ will FAIL
```

**Read-Only Mode:**
```python
# Disable write operations (if supported by server)
args=[
    "-y",
    "@modelcontextprotocol/server-filesystem",
    "/path",
    "--readonly"
]
```

### HTTP Server Security

**Authentication:**
```python
http_server = MCPServer(
    name="secure-api",
    transport=TransportType.HTTP,
    url="https://api.example.com/mcp",
    headers={
        "Authorization": "Bearer secret-token",
        "X-API-Key": "api-key-123"
    }
)
```

**TLS/HTTPS:**
```python
# Always use HTTPS for production
url="https://api.example.com/mcp"  # ✅ Secure
# url="http://api.example.com/mcp"  # ❌ Insecure
```

---

## Troubleshooting

### Issue: Server connection fails

**Check server process:**
```bash
# Test MCP server manually
npx @modelcontextprotocol/server-filesystem /path

# Look for JSON-RPC messages on stdout
```

**Check logs:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# MCP client will log connection details
await client.connect(server)
```

### Issue: Tool execution timeout

**Increase timeout:**
```python
server = MCPServer(
    name="slow-server",
    timeout=60,  # Increase from default 30s
    ...
)
```

**Check server health:**
```python
# Test with simple tool call
result = await client.execute_tool(
    server_name="slow-server",
    tool_name="ping",
    arguments={}
)
```

### Issue: JSON-RPC errors

**Enable verbose logging:**
```bash
MCP_LOG_LEVEL=DEBUG
MCP_LOG_TOOL_CALLS=true
```

**Check tool schema:**
```python
# Validate arguments against input_schema
tools = await client.discover_tools("filesystem")
read_file_tool = next(t for t in tools if t.name == "read_file")
print(read_file_tool.input_schema)

# Ensure arguments match schema
```

---

## Related Documentation

- **MCP Specification:** https://spec.modelcontextprotocol.io/
- **MCP SDK (TypeScript):** https://github.com/modelcontextprotocol/sdk
- **Official MCP Servers:** https://github.com/modelcontextprotocol/servers
- **Sprint 18 Summary:** [SPRINT_18_SUMMARY.md](../../docs/sprints/SPRINT_18_SUMMARY.md)

---

**Last Updated:** 2025-11-10
**Sprint:** 18 (MCP Integration)
**Maintainer:** Klaus Pommer + Claude Code (backend-agent, documentation-agent)
