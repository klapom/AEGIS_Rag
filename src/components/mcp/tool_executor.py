"""MCP Tool Executor.

Executes MCP tool calls with error handling and retry logic.
Supports timeout, exponential backoff, and result parsing.

Sprint 9 Feature 9.7: Tool Execution Handler
"""

import asyncio
import time
from typing import Any

from src.components.mcp.client import MCPClient
from src.components.mcp.error_handler import ErrorHandler
from src.components.mcp.models import MCPToolCall, MCPToolResult
from src.components.mcp.result_parser import ResultParser
from src.core.logging import get_logger

logger = get_logger(__name__)

class ToolExecutor:
    """Execute MCP tool calls with error handling and retry logic.

    Features:
    - Automatic retry with exponential backoff (3 attempts)
    - Configurable timeout (default 30s)
    - Error classification (transient vs permanent)
    - Result parsing for multiple formats
    - Execution metrics and logging
    """

    def __init__(self, mcp_client: MCPClient, timeout: int = 30) -> None:
        """Initialize tool executor.

        Args:
            mcp_client: MCP client instance
            timeout: Timeout in seconds for tool execution
        """
        self.client = mcp_client
        self.timeout = timeout
        self.parser = ResultParser()
        self.error_handler = ErrorHandler()
        self.logger = logger.bind(component="tool_executor")

    async def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        server_name: str | None = None,
        expected_format: str = "json",
    ) -> MCPToolResult:
        """Execute a tool call with retry logic.

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            server_name: Optional server name to use
            expected_format: Expected result format ("json", "text", "binary", "auto")

        Returns:
            MCPToolResult with execution details and parsed result
        """
        start_time = time.time()

        try:
            # Find tool to validate it exists
            tool = self.client.get_tool(tool_name, server_name)
            if not tool:
                execution_time = time.time() - start_time
                return MCPToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Tool '{tool_name}' not found",
                    execution_time=execution_time,
                )

            self.logger.info(
                "executing_tool",
                tool=tool_name,
                server=tool.server,
                params=parameters,
            )

            # Create tool call
            tool_call = MCPToolCall(
                tool_name=tool_name,
                arguments=parameters,
                timeout=self.timeout,
            )

            # Execute with retry logic
            result = await self._execute_with_retry(tool_call)

            # Parse result if successful
            if result.success and result.result is not None:
                parsed_result = self.parser.parse(result.result, expected_format)
                result.result = parsed_result

            self.logger.info(
                "tool_execution_success" if result.success else "tool_execution_failed",
                tool=tool_name,
                success=result.success,
                execution_time_ms=result.execution_time * 1000,
            )

            return result

        except Exception as e:
            # Catch any unexpected errors
            execution_time = time.time() - start_time
            mcp_error = self.error_handler.wrap_error(e, f"executing tool '{tool_name}'")

            self.logger.error(
                "tool_execution_exception",
                tool=tool_name,
                error=str(mcp_error),
                error_type=mcp_error.error_type.value,
                execution_time_ms=execution_time * 1000,
            )

            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=str(mcp_error),
                execution_time=execution_time,
            )

    def _should_retry_result(self, result: MCPToolResult) -> bool:
        """Determine if a failed result should trigger a retry.

        Args:
            result: Tool result to check

        Returns:
            True if result indicates a transient failure
        """
        if result.success:
            return False

        # Check if error indicates transient failure
        if result.error:
            error_lower = result.error.lower()
            transient_keywords = ["timeout", "connection", "network", "temporary"]
            return any(keyword in error_lower for keyword in transient_keywords)

        return False

    async def _execute_with_retry(self, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute tool with retry logic (up to 3 attempts).

        Args:
            tool_call: Tool call to execute

        Returns:
            Tool execution result
        """
        max_attempts = 3
        last_result = None

        for attempt in range(max_attempts):
            try:
                # Execute via MCP client
                result = await self.client.execute_tool(tool_call)

                # If successful or permanent failure, return immediately
                if result.success or not self._should_retry_result(result):
                    return result

                # Transient failure - log and retry
                last_result = result
                self.logger.warning(
                    "tool_execution_retry",
                    tool=tool_call.tool_name,
                    attempt=attempt + 1,
                    error=result.error,
                )

                # Wait before retry with exponential backoff
                if attempt < max_attempts - 1:
                    wait_time = min(2**attempt, 10)  # Max 10 seconds
                    await asyncio.sleep(wait_time)

            except Exception as e:
                # Unexpected exception during execution
                self.logger.error(
                    "tool_execution_exception",
                    tool=tool_call.tool_name,
                    attempt=attempt + 1,
                    error=str(e),
                )

                if attempt == max_attempts - 1:
                    # Last attempt - return error result
                    return MCPToolResult(
                        tool_name=tool_call.tool_name,
                        success=False,
                        error=f"Execution failed after {max_attempts} attempts: {str(e)}",
                    )

                # Wait before retry
                await asyncio.sleep(min(2**attempt, 10))

        # All retries exhausted - return last result
        return last_result or MCPToolResult(
            tool_name=tool_call.tool_name,
            success=False,
            error=f"Execution failed after {max_attempts} attempts",
        )
