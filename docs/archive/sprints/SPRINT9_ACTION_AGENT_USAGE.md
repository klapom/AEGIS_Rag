# Sprint 9: Action Agent Usage Guide

Quick reference for using the Tool Executor and Action Agent (Features 9.7 & 9.8).

## Quick Start

```python
import asyncio
from src.components.mcp.client import MCPClient
from src.components.mcp.models import MCPServer, TransportType
from src.components.mcp.tool_executor import ToolExecutor
from src.agents.action_agent import ActionAgent


async def main():
    # 1. Initialize MCP client
    mcp_client = MCPClient()

    # 2. Connect to an MCP server
    server = MCPServer(
        name="filesystem",
        transport=TransportType.STDIO,
        endpoint="mcp-server-filesystem",
        description="File operations",
        timeout=30,
    )
    await mcp_client.connect(server)

    # 3. Create tool executor
    tool_executor = ToolExecutor(mcp_client, timeout=30)

    # 4. Create action agent
    action_agent = ActionAgent(mcp_client, tool_executor)

    # 5. Execute an action
    result = await action_agent.execute(
        action="read the README file",
        parameters={"path": "README.md"}
    )

    print(f"Success: {result['success']}")
    print(f"Tool used: {result['tool']}")
    print(f"Result: {result['result']}")


asyncio.run(main())
```

## Component Reference

### 1. Tool Executor

Executes MCP tool calls with retry logic and error handling.

```python
from src.components.mcp.tool_executor import ToolExecutor

# Initialize
executor = ToolExecutor(mcp_client, timeout=30)

# Execute a tool
result = await executor.execute(
    tool_name="read_file",
    parameters={"path": "config.json"},
    expected_format="json"  # "json", "text", "binary", "auto"
)

# Check result
if result.success:
    print(result.result)
else:
    print(f"Error: {result.error}")
```

**Features:**
- Automatic retry (3 attempts with exponential backoff)
- Timeout handling (configurable, default 30s)
- Result parsing (JSON, text, binary)
- Error classification

### 2. Action Agent

LangGraph-based agent for executing actions via MCP tools.

```python
from src.agents.action_agent import ActionAgent

# Initialize
agent = ActionAgent(mcp_client, tool_executor)

# Execute an action
result = await agent.execute(
    action="read the configuration file",
    parameters={"path": "config.json"}
)

# Result structure
{
    "success": True,
    "result": {...},       # Parsed tool result
    "error": None,         # Error message if failed
    "trace": [...],        # Execution trace
    "tool": "read_file"    # Tool that was used
}
```

**Utility Methods:**
```python
# List available tools
tools = agent.get_available_tools()
# Returns: ["read_file", "write_file", ...]

# Get tool information
info = agent.get_tool_info("read_file")
# Returns: {
#     "name": "read_file",
#     "description": "...",
#     "server": "filesystem",
#     "parameters": {...}
# }
```

### 3. Tool Selector

Selects appropriate tools based on action descriptions.

```python
from src.agents.tool_selector import ToolSelector

selector = ToolSelector(mcp_client)

# Select a tool for an action
tool = selector.select_tool("read the README file")
print(tool.name)  # "read_file"

# Get multiple suggestions
suggestions = selector.get_tool_suggestions("create file", top_n=3)
for tool in suggestions:
    print(f"{tool.name}: {tool.description}")
```

## Error Handling

### Error Types

```python
from src.components.mcp.error_handler import ErrorType, MCPError

# TRANSIENT - Will retry
# Examples: timeout, connection error, network error

# PERMANENT - Won't retry
# Examples: invalid parameters, not found

# TOOL_ERROR - Tool-specific
# Examples: tool execution failed
```

### Custom Error Handling

```python
from src.components.mcp.error_handler import ErrorHandler, MCPError

handler = ErrorHandler()

try:
    # Your code
    pass
except Exception as e:
    # Classify error
    error_type = handler.classify_error(e)

    # Create user-friendly message
    message = handler.create_user_friendly_message(e)

    # Wrap error
    mcp_error = handler.wrap_error(e, "performing action")

    # Check if retryable
    if mcp_error.is_retryable():
        # Retry logic
        pass
```

## Result Parsing

```python
from src.components.mcp.result_parser import ResultParser

parser = ResultParser()

# Parse JSON
result = parser.parse({"key": "value"}, "json")

# Parse text
result = parser.parse("Hello world", "text")
# Returns: {"content": "Hello world", "format": "text"}

# Parse binary
result = parser.parse(b"binary data", "binary")
# Returns: {"data": "base64...", "encoding": "base64", "format": "binary"}

# Auto-detect format
result = parser.parse(data, "auto")

# Validate result
is_valid = parser.validate_result(result)

# Extract content
content = parser.extract_content(result)
```

## Retry Logic

The Tool Executor automatically retries transient failures:

```python
# Configuration
executor = ToolExecutor(mcp_client, timeout=30)

# Retry behavior:
# - Max attempts: 3
# - Backoff: exponential (1s, 2s, 4s, max 10s)
# - Retries on: timeout, connection errors, network errors
# - No retry on: invalid parameters, not found

# Example with retry
result = await executor.execute(
    tool_name="flaky_tool",
    parameters={}
)
# Will automatically retry up to 3 times if transient failures occur
```

## Tool Selection Patterns

The Tool Selector uses keyword matching:

```python
# File operations
"read the file" -> read_file
"write to file" -> write_file
"list files" -> list_file

# GitHub operations
"create issue" -> create_issue
"create pull request" -> create_pr

# Search operations
"search for" -> search_tool
"find files" -> search_tool

# Execution
"run command" -> execute_tool
```

**Custom patterns:**
```python
selector = ToolSelector(mcp_client)

# Add custom action patterns
selector.action_patterns["custom"] = ["keyword1", "keyword2"]
```

## LangGraph Workflow

The Action Agent uses a 3-node LangGraph workflow:

```
┌──────────────┐
│ select_tool  │ - Selects appropriate MCP tool
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ execute_tool │ - Executes tool with retry logic
└──────┬───────┘
       │
       ▼
┌──────────────┐
│handle_result │ - Processes result or error
└──────────────┘
```

**State Management:**
```python
from src.agents.action_agent import ActionAgentState

# State structure
state = {
    "action": "read file",
    "parameters": {"path": "file.txt"},
    "selected_tool": "read_file",
    "tool_result": {...},
    "error": "",
    "messages": [...]  # Execution trace
}
```

## Best Practices

### 1. Always Handle Results

```python
result = await agent.execute(action, parameters)

if result['success']:
    # Process result
    data = result['result']
else:
    # Handle error
    print(f"Action failed: {result['error']}")
    print(f"Trace: {result['trace']}")
```

### 2. Use Appropriate Timeouts

```python
# For fast operations
executor = ToolExecutor(mcp_client, timeout=10)

# For slow operations (e.g., GitHub API)
executor = ToolExecutor(mcp_client, timeout=60)
```

### 3. Check Tool Availability

```python
# Before executing
tools = agent.get_available_tools()
if "read_file" in tools:
    result = await agent.execute("read file", {...})
else:
    print("Tool not available")
```

### 4. Use Descriptive Actions

```python
# Good - specific and clear
result = await agent.execute(
    action="read the configuration file",
    parameters={"path": "config.json"}
)

# Less good - vague
result = await agent.execute(
    action="do something",
    parameters={}
)
```

### 5. Monitor Execution Traces

```python
result = await agent.execute(action, parameters)

# Review execution steps
for step in result['trace']:
    print(f"  - {step}")

# Useful for debugging and understanding agent behavior
```

## Testing

### Unit Testing with Mocks

```python
from unittest.mock import AsyncMock, MagicMock
from src.components.mcp.models import MCPTool, MCPToolResult

# Mock MCP client
mock_client = MagicMock()
mock_client.list_tools.return_value = [
    MCPTool(name="test_tool", description="Test", parameters={}, server="test")
]
mock_client.execute_tool = AsyncMock(return_value=MCPToolResult(
    tool_name="test_tool",
    success=True,
    result={"data": "ok"},
    execution_time=0.5
))

# Use in tests
executor = ToolExecutor(mock_client)
agent = ActionAgent(mock_client, executor)
```

### Using the Stub Client

```python
from src.components.mcp.client_stub import MCPClientStub
from src.components.mcp.models import MCPTool

# Create stub
stub = MCPClientStub()

# Add tools
stub.add_tool(MCPTool(
    name="test_tool",
    description="Test tool",
    parameters={},
    server="test"
))

# Use like real client
executor = ToolExecutor(stub)
result = await executor.execute("test_tool", {})
```

## Troubleshooting

### Issue: Tool Not Found

```python
# Check available tools
tools = mcp_client.list_tools()
print(f"Available: {[t.name for t in tools]}")

# Check tool exists
tool = mcp_client.get_tool("tool_name")
if not tool:
    print("Tool not found")
```

### Issue: Timeout Errors

```python
# Increase timeout
executor = ToolExecutor(mcp_client, timeout=60)

# Or handle timeout in error
result = await executor.execute(...)
if not result.success and "timeout" in result.error.lower():
    # Handle timeout specifically
    pass
```

### Issue: Retry Not Working

```python
# Check error type
from src.components.mcp.error_handler import ErrorHandler

handler = ErrorHandler()
error_type = handler.classify_error(exception)

# Only TRANSIENT errors trigger retry
# PERMANENT and TOOL_ERROR do not retry
```

## Examples

See `examples/sprint9_action_agent_example.py` for complete working examples:

1. File operations with retry
2. GitHub operations
3. Tool selection demonstration
4. Error handling scenarios

Run with:
```bash
poetry run python examples/sprint9_action_agent_example.py
```

## API Reference

See source code documentation for detailed API reference:

- `src/components/mcp/tool_executor.py`
- `src/agents/action_agent.py`
- `src/agents/tool_selector.py`
- `src/components/mcp/error_handler.py`
- `src/components/mcp/result_parser.py`
