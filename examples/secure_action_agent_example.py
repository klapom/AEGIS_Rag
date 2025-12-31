"""Example: SecureActionAgent with BubblewrapSandboxBackend.

Sprint 67 Feature 67.2: deepagents Integration
Demonstrates secure code execution with sandbox isolation.

This example shows:
- Basic command execution
- File operations (write/read)
- Error handling and retry logic
- Resource cleanup
"""

import asyncio
from pathlib import Path

from src.agents.action import ActionConfig, SecureActionAgent


async def main():
    """Run SecureActionAgent examples."""
    print("=" * 60)
    print("SecureActionAgent Example - Sprint 67 Feature 67.2")
    print("=" * 60)
    print()

    # Create agent with custom configuration
    config = ActionConfig(
        sandbox_timeout=30,
        max_retries=3,
        workspace_path="/tmp/aegis-action-example",
        repo_path=str(Path(__file__).parent.parent),
    )

    agent = SecureActionAgent(config=config)

    try:
        # Example 1: Simple command execution
        print("Example 1: Simple Command Execution")
        print("-" * 60)
        result = await agent.execute_action("echo 'Hello from Sandbox!'")

        if result["success"]:
            print(f"✓ Command succeeded")
            print(f"  Output: {result['output'].strip()}")
            print(f"  Exit code: {result['exit_code']}")
            print(f"  Execution time: {result['execution_time_ms']:.2f}ms")
        else:
            print(f"✗ Command failed: {result['error']}")
        print()

        # Example 2: File operations
        print("Example 2: File Operations")
        print("-" * 60)

        # Write file
        write_result = await agent.write_file("example.txt", "This is a test file.\n")
        if write_result["success"]:
            print(f"✓ File written: {write_result['path']}")
            print(f"  Size: {write_result['size']} bytes")
        else:
            print(f"✗ Write failed: {write_result['error']}")

        # Read file
        read_result = await agent.read_file("example.txt")
        if read_result["success"]:
            print(f"✓ File read successfully")
            print(f"  Content: {read_result['content'].strip()}")
        else:
            print(f"✗ Read failed: {read_result['error']}")
        print()

        # Example 3: Working with files in sandbox
        print("Example 3: Working with Files in Sandbox")
        print("-" * 60)

        # Create a file and count lines
        await agent.write_file(
            "data.txt",
            "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n",
        )

        result = await agent.execute_action("wc -l /workspace/data.txt")
        if result["success"]:
            print(f"✓ Line count: {result['output'].strip()}")
        else:
            print(f"✗ Command failed: {result['error']}")
        print()

        # Example 4: Path traversal prevention
        print("Example 4: Security - Path Traversal Prevention")
        print("-" * 60)

        malicious_result = await agent.write_file("../../../etc/passwd", "malicious")
        if not malicious_result["success"]:
            print(f"✓ Path traversal blocked: {malicious_result['error']}")
        else:
            print(f"✗ Security vulnerability: path traversal allowed!")
        print()

        # Example 5: Timeout handling
        print("Example 5: Timeout Handling")
        print("-" * 60)

        # Configure short timeout for demonstration
        agent.config.sandbox_timeout = 2

        result = await agent.execute_action("sleep 10")
        if not result["success"]:
            print(f"✓ Timeout handled: {result['error']}")
            print(f"  Execution time: {result['execution_time_ms']:.2f}ms")
        else:
            print(f"✗ Timeout not enforced!")
        print()

        # Example 6: Get paths
        print("Example 6: Workspace and Repository Paths")
        print("-" * 60)
        print(f"Workspace: {agent.get_workspace_path()}")
        print(f"Repository: {agent.get_repo_path()}")
        print()

    finally:
        # Always cleanup
        print("Cleanup")
        print("-" * 60)
        await agent.cleanup()
        print("✓ Workspace cleaned up")
        print()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
