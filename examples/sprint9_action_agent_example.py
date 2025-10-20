"""Example usage of Action Agent with MCP Tools.

This example demonstrates how to use the Action Agent (Feature 9.8)
with Tool Executor (Feature 9.7) to execute actions via MCP tools.

Sprint 9 Features 9.7 & 9.8
"""

import asyncio
from src.components.mcp.client import MCPClient
from src.components.mcp.models import MCPServer, TransportType
from src.components.mcp.tool_executor import ToolExecutor
from src.agents.action_agent import ActionAgent


async def example_file_operations():
    """Example: File operations using Action Agent."""
    print("\n=== Example 1: File Operations ===\n")

    # Initialize MCP client
    mcp_client = MCPClient()

    # Configure a filesystem MCP server (stdio transport)
    filesystem_server = MCPServer(
        name="filesystem",
        transport=TransportType.STDIO,
        endpoint="mcp-server-filesystem",  # Command to start MCP server
        description="Filesystem operations server",
        timeout=30,
    )

    try:
        # Connect to MCP server
        print("Connecting to filesystem MCP server...")
        await mcp_client.connect(filesystem_server)
        print(f"Connected! Discovered {len(mcp_client.list_tools())} tools\n")

        # Create tool executor
        tool_executor = ToolExecutor(mcp_client, timeout=30)

        # Create action agent
        action_agent = ActionAgent(mcp_client, tool_executor)

        # Example 1: Read a file
        print("Action 1: Read README file")
        result = await action_agent.execute(
            action="read the README file",
            parameters={"path": "README.md"},
        )

        print(f"Success: {result['success']}")
        print(f"Tool used: {result['tool']}")
        print(f"Trace: {' -> '.join(result['trace'])}")
        if result['success']:
            print(f"Content preview: {str(result['result'])[:100]}...")
        print()

        # Example 2: Write a file
        print("Action 2: Write to output file")
        result = await action_agent.execute(
            action="write content to output file",
            parameters={
                "path": "output.txt",
                "content": "Hello from Action Agent!",
            },
        )

        print(f"Success: {result['success']}")
        print(f"Tool used: {result['tool']}")
        if result['error']:
            print(f"Error: {result['error']}")
        print()

    finally:
        # Cleanup
        await mcp_client.disconnect_all()


async def example_github_operations():
    """Example: GitHub operations using Action Agent."""
    print("\n=== Example 2: GitHub Operations ===\n")

    # Initialize MCP client
    mcp_client = MCPClient()

    # Configure a GitHub MCP server (HTTP transport)
    github_server = MCPServer(
        name="github",
        transport=TransportType.HTTP,
        endpoint="http://localhost:8080",  # HTTP MCP server
        description="GitHub operations server",
        timeout=60,
    )

    try:
        # Connect to MCP server
        print("Connecting to GitHub MCP server...")
        await mcp_client.connect(github_server)
        print(f"Connected! Discovered {len(mcp_client.list_tools())} tools\n")

        # Create tool executor and action agent
        tool_executor = ToolExecutor(mcp_client, timeout=60)
        action_agent = ActionAgent(mcp_client, tool_executor)

        # Example: Create a GitHub issue
        print("Action: Create GitHub issue")
        result = await action_agent.execute(
            action="create a GitHub issue for the bug",
            parameters={
                "title": "Bug: Action agent not working",
                "body": "The action agent fails to execute...",
            },
        )

        print(f"Success: {result['success']}")
        print(f"Tool used: {result['tool']}")
        if result['success']:
            print(f"Issue created: #{result['result'].get('issue_number')}")
        print()

    finally:
        await mcp_client.disconnect_all()


async def example_tool_selection():
    """Example: Understanding tool selection logic."""
    print("\n=== Example 3: Tool Selection ===\n")

    # Initialize components (using stub for demo)
    from src.components.mcp.client_stub import MCPClientStub
    from src.components.mcp.models import MCPTool

    mcp_client = MCPClientStub()

    # Add some sample tools
    tools = [
        MCPTool(
            name="read_file",
            description="Read a file from disk",
            parameters={"type": "object"},
            server="filesystem",
        ),
        MCPTool(
            name="write_file",
            description="Write a file to disk",
            parameters={"type": "object"},
            server="filesystem",
        ),
        MCPTool(
            name="create_issue",
            description="Create a GitHub issue",
            parameters={"type": "object"},
            server="github",
        ),
    ]

    for tool in tools:
        mcp_client.add_tool(tool)

    # Create action agent
    tool_executor = ToolExecutor(mcp_client)
    action_agent = ActionAgent(mcp_client, tool_executor)

    # Show available tools
    print("Available tools:")
    for tool_name in action_agent.get_available_tools():
        info = action_agent.get_tool_info(tool_name)
        print(f"  - {tool_name}: {info['description']}")
    print()

    # Test tool selection
    from src.agents.tool_selector import ToolSelector

    selector = ToolSelector(mcp_client)

    test_actions = [
        "read the configuration file",
        "write data to output",
        "create a GitHub issue",
        "search for files",
    ]

    print("Tool selection for different actions:")
    for action in test_actions:
        tool = selector.select_tool(action)
        print(f"  '{action}' -> {tool.name if tool else 'None'}")
    print()

    # Get tool suggestions
    print("Tool suggestions for 'read file':")
    suggestions = selector.get_tool_suggestions("read file", top_n=3)
    for i, tool in enumerate(suggestions, 1):
        print(f"  {i}. {tool.name} - {tool.description}")


async def example_error_handling():
    """Example: Error handling and retry logic."""
    print("\n=== Example 4: Error Handling ===\n")

    from src.components.mcp.client_stub import MCPClientStub
    from src.components.mcp.models import MCPTool, MCPToolResult

    # Setup stub client
    mcp_client = MCPClientStub()
    mcp_client.add_tool(
        MCPTool(
            name="flaky_tool",
            description="A tool that sometimes fails",
            parameters={"type": "object"},
            server="test",
        )
    )

    # Mock the connection to simulate failures
    connection = mcp_client.connections.get("test") or mcp_client.connections.setdefault(
        "test", type("Connection", (), {"transport": "stdio"})()
    )

    # Create tool executor (with retry)
    tool_executor = ToolExecutor(mcp_client, timeout=5)
    action_agent = ActionAgent(mcp_client, tool_executor)

    # Test 1: Tool not found
    print("Test 1: Tool not found")
    result = await action_agent.execute(
        action="use nonexistent tool",
        parameters={},
    )
    print(f"  Success: {result['success']}")
    print(f"  Error: {result['error']}")
    print()

    # Test 2: Successful execution
    print("Test 2: Successful execution")
    # Override execute_tool to return success
    async def mock_success(*args, **kwargs):
        return MCPToolResult(
            tool_name="flaky_tool",
            success=True,
            result={"data": "ok"},
            execution_time=0.5,
        )

    mcp_client.execute_tool = mock_success

    result = await action_agent.execute(
        action="use the flaky tool",
        parameters={},
    )
    print(f"  Success: {result['success']}")
    print(f"  Result: {result['result']}")
    print()

    # Test 3: Transient failure with retry
    print("Test 3: Transient failure (will retry)")
    attempt = {"count": 0}

    async def mock_retry(*args, **kwargs):
        attempt["count"] += 1
        if attempt["count"] < 3:
            # Fail first 2 times
            return MCPToolResult(
                tool_name="flaky_tool",
                success=False,
                error="Timeout - connection failed",
                execution_time=1.0,
            )
        # Succeed on 3rd attempt
        return MCPToolResult(
            tool_name="flaky_tool",
            success=True,
            result={"data": "ok"},
            execution_time=0.5,
        )

    mcp_client.execute_tool = mock_retry

    result = await action_agent.execute(
        action="use the flaky tool",
        parameters={},
    )
    print(f"  Success: {result['success']}")
    print(f"  Attempts made: {attempt['count']}")
    print(f"  Trace: {result['trace']}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Sprint 9 Action Agent Examples")
    print("Features 9.7 (Tool Executor) & 9.8 (Action Agent)")
    print("=" * 60)

    # Note: Examples 1 & 2 require actual MCP servers running
    # They are commented out by default
    # Uncomment to run with real MCP servers:

    # await example_file_operations()
    # await example_github_operations()

    # These examples work with stubs (no external dependencies):
    await example_tool_selection()
    await example_error_handling()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
