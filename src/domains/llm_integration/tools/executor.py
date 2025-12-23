"""Tool Executor with Sandboxing Support.

Sprint 59 Feature 59.2: Executes tools with optional sandboxing.

This module provides the execution engine for registered tools with:
- Parameter validation before execution
- Sandboxed execution for security-critical tools
- Direct execution for safe tools
- Comprehensive error handling and logging
- Execution time tracking

Architecture:
    ToolExecutor handles tool invocation with:
    1. Tool lookup from registry
    2. Parameter validation
    3. Sandboxed or direct execution
    4. Result handling and error formatting

Usage:
    >>> from src.domains.llm_integration.tools.executor import ToolExecutor
    >>> executor = ToolExecutor(sandbox_enabled=True)
    >>>
    >>> result = await executor.execute(
    ...     tool_name="search",
    ...     parameters={"query": "machine learning"}
    ... )
    >>> print(result)  # {"result": [...]}
"""

import time
from typing import Any

import structlog

from src.domains.llm_integration.tools.registry import ToolDefinition, ToolRegistry
from src.domains.llm_integration.tools.validators import validate_parameters

logger = structlog.get_logger(__name__)


class ToolExecutor:
    """Executes registered tools with validation and sandboxing.

    Handles tool execution with comprehensive error handling, validation,
    and optional sandboxing for security-critical operations.

    Attributes:
        sandbox_enabled: Whether to use sandboxing for tools that require it
        _execution_count: Counter for total executions
        _error_count: Counter for failed executions
    """

    def __init__(self, sandbox_enabled: bool = True) -> None:
        """Initialize tool executor.

        Args:
            sandbox_enabled: Enable sandbox for tools that require it
                           (default: True)
        """
        self.sandbox_enabled = sandbox_enabled
        self._execution_count = 0
        self._error_count = 0

        logger.info("tool_executor_initialized", sandbox_enabled=sandbox_enabled)

    async def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool by name with parameter validation.

        Args:
            tool_name: Name of the registered tool
            parameters: Tool input parameters

        Returns:
            Dict with either:
                - {"result": <tool_output>} on success
                - {"error": "<error_message>"} on failure

        Example:
            >>> executor = ToolExecutor()
            >>> result = await executor.execute(
            ...     "calculator",
            ...     {"operation": "add", "a": 5, "b": 3}
            ... )
            >>> assert result == {"result": 8}
        """
        execution_start = time.perf_counter()
        self._execution_count += 1

        try:
            # Look up tool in registry
            tool = ToolRegistry.get_tool(tool_name)
            if not tool:
                self._error_count += 1
                logger.warning("tool_not_found", tool_name=tool_name)
                return {"error": f"Unknown tool: {tool_name}"}

            # Validate parameters against schema
            validation_result = validate_parameters(parameters, tool.parameters)
            if not validation_result.valid:
                self._error_count += 1
                logger.warning(
                    "parameter_validation_failed",
                    tool_name=tool_name,
                    error=validation_result.error,
                )
                return {"error": f"Invalid parameters: {validation_result.error}"}

            # Use coerced parameters if available
            validated_params = validation_result.coerced_params or parameters

            # Execute with or without sandbox
            if tool.requires_sandbox and self.sandbox_enabled:
                result = await self._execute_sandboxed(tool, validated_params)
            else:
                result = await self._execute_direct(tool, validated_params)

            # Track execution time
            execution_time_ms = (time.perf_counter() - execution_start) * 1000

            logger.info(
                "tool_executed",
                tool_name=tool_name,
                execution_time_ms=round(execution_time_ms, 2),
                sandboxed=tool.requires_sandbox and self.sandbox_enabled,
                success="error" not in result,
            )

            return result

        except Exception as e:
            self._error_count += 1
            logger.error("tool_execution_exception", tool_name=tool_name, error=str(e))
            return {"error": f"Execution failed: {str(e)}"}

    async def _execute_sandboxed(
        self,
        tool: ToolDefinition,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute tool in sandbox environment.

        Args:
            tool: Tool definition
            parameters: Validated parameters

        Returns:
            Execution result or error dict
        """
        try:
            # Import sandbox (lazy to avoid circular dependency)
            from src.domains.llm_integration.sandbox import get_sandbox

            sandbox = await get_sandbox()
            logger.debug(
                "executing_in_sandbox",
                tool_name=tool.name,
                sandbox_type="docker",
            )
            return await sandbox.run(tool.handler, parameters)

        except ImportError as e:
            # Docker not available - fall back to direct execution
            logger.warning(
                "sandbox_unavailable",
                tool_name=tool.name,
                error=str(e),
                fallback="direct_execution",
            )
            return await self._execute_direct(tool, parameters)

        except Exception as e:
            logger.error("sandboxed_execution_failed", tool_name=tool.name, error=str(e))
            return {"error": f"Sandboxed execution failed: {str(e)}"}

    async def _execute_direct(
        self,
        tool: ToolDefinition,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute tool directly without sandbox.

        Args:
            tool: Tool definition
            parameters: Validated parameters

        Returns:
            Execution result or error dict
        """
        try:
            # Call the tool handler
            result = await tool.handler(**parameters)

            # Wrap result in standard format
            return {"result": result}

        except TypeError as e:
            # Parameter mismatch
            logger.error(
                "tool_parameter_mismatch",
                tool_name=tool.name,
                error=str(e),
                parameters=list(parameters.keys()),
            )
            return {"error": f"Parameter mismatch: {str(e)}"}

        except Exception as e:
            logger.error("tool_execution_failed", tool_name=tool.name, error=str(e))
            return {"error": str(e)}

    async def batch_execute(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Execute multiple tool calls in sequence.

        Args:
            tool_calls: List of tool call dicts with:
                - name: Tool name
                - parameters: Tool parameters

        Returns:
            List of execution results in same order

        Example:
            >>> calls = [
            ...     {"name": "search", "parameters": {"query": "AI"}},
            ...     {"name": "calculator", "parameters": {"operation": "add", "a": 1, "b": 2}}
            ... ]
            >>> results = await executor.batch_execute(calls)
        """
        results = []

        for call in tool_calls:
            tool_name = call.get("name")
            parameters = call.get("parameters", {})

            if not tool_name:
                results.append({"error": "Missing tool name in call"})
                continue

            result = await self.execute(tool_name, parameters)
            results.append(result)

        logger.info("batch_execution_completed", tool_count=len(tool_calls))

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get execution statistics.

        Returns:
            Dict with execution counts and error rate

        Example:
            >>> stats = executor.get_stats()
            >>> print(stats)
            {
                "total_executions": 42,
                "errors": 3,
                "error_rate": 0.071,
                "sandbox_enabled": True
            }
        """
        error_rate = self._error_count / self._execution_count if self._execution_count > 0 else 0.0

        return {
            "total_executions": self._execution_count,
            "errors": self._error_count,
            "error_rate": round(error_rate, 3),
            "sandbox_enabled": self.sandbox_enabled,
        }

    def reset_stats(self) -> None:
        """Reset execution statistics.

        Useful for testing or per-session tracking.
        """
        self._execution_count = 0
        self._error_count = 0
        logger.info("executor_stats_reset")


# Singleton instance for global executor
_global_executor: ToolExecutor | None = None


def get_tool_executor(sandbox_enabled: bool = True) -> ToolExecutor:
    """Get global tool executor instance (singleton).

    Args:
        sandbox_enabled: Enable sandboxing (default: True)

    Returns:
        ToolExecutor singleton

    Example:
        >>> executor = get_tool_executor()
        >>> result = await executor.execute("search", {"query": "AI"})
    """
    global _global_executor
    if _global_executor is None:
        _global_executor = ToolExecutor(sandbox_enabled=sandbox_enabled)
    return _global_executor
