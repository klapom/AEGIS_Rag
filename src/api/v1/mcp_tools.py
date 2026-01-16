"""MCP Tool Execution API endpoints.

Sprint 103 Feature 103.1: Execute bash, python, and browser tools via API.

This module provides MCP-compatible API endpoints for executing tools
that are part of the internal tool execution framework.

Endpoints:
    POST /api/v1/mcp/tools/{tool_name}/execute - Execute a tool with parameters

Security:
    - All endpoints require JWT authentication
    - Tool execution is logged for audit
    - Bash/Python tools use security validation
    - Timeout limits enforced (max 60s)

Example Usage:
    # Execute bash command
    >>> response = requests.post(
    ...     "/api/v1/mcp/tools/bash/execute",
    ...     json={"parameters": {"command": "ls -la"}, "timeout": 30},
    ...     headers=auth_headers
    ... )

    # Execute Python code
    >>> response = requests.post(
    ...     "/api/v1/mcp/tools/python/execute",
    ...     json={"parameters": {"code": "print('hello')"}, "timeout": 30},
    ...     headers=auth_headers
    ... )

    # Browser navigation
    >>> response = requests.post(
    ...     "/api/v1/mcp/tools/browser_navigate/execute",
    ...     json={"parameters": {"url": "https://example.com"}, "timeout": 30},
    ...     headers=auth_headers
    ... )

See Also:
    - src/domains/llm_integration/tools/builtin/bash_tool.py
    - src/domains/llm_integration/tools/builtin/python_tool.py
    - src/domains/llm_integration/tools/builtin/browser_executor.py
"""

import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.core.auth import User
from src.domains.llm_integration.tools.builtin.bash_tool import bash_execute
from src.domains.llm_integration.tools.builtin.browser_executor import (
    browser_click,
    browser_evaluate,
    browser_fill,
    browser_get_text,
    browser_navigate,
    browser_screenshot,
    browser_type,
)
from src.domains.llm_integration.tools.builtin.python_tool import python_execute

router = APIRouter(prefix="/api/v1/mcp/tools", tags=["MCP Tools"])
logger = structlog.get_logger(__name__)


# Pydantic Models


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool.

    Attributes:
        parameters: Tool-specific parameters
        timeout: Execution timeout in seconds (max 60)
    """

    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific parameters",
    )
    timeout: int = Field(
        default=30,
        description="Execution timeout in seconds",
        ge=1,
        le=60,
    )


class ToolExecutionResult(BaseModel):
    """Result from tool execution.

    Attributes:
        result: Tool execution result (stdout, screenshot data, etc.)
        execution_time_ms: Execution duration in milliseconds
        status: 'success' | 'error' | 'timeout'
        error_message: Error message if status is 'error' or 'timeout'
    """

    result: Any | None = Field(
        default=None,
        description="Tool execution result",
    )
    execution_time_ms: int = Field(
        description="Execution time in milliseconds",
    )
    status: str = Field(
        description="Execution status: success, error, or timeout",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if failed",
    )


# Tool Name to Function Mapping

TOOL_EXECUTORS = {
    # Bash tool
    "bash": bash_execute,
    # Python tool
    "python": python_execute,
    # Browser tools
    "browser_navigate": browser_navigate,
    "browser_click": browser_click,
    "browser_screenshot": browser_screenshot,
    "browser_evaluate": browser_evaluate,
    "browser_get_text": browser_get_text,
    "browser_fill": browser_fill,
    "browser_type": browser_type,
}


# API Endpoints


@router.post("/{tool_name}/execute", response_model=ToolExecutionResult)
async def execute_tool(
    tool_name: str,
    request: ToolExecutionRequest,
    current_user: User = Depends(get_current_user),
) -> ToolExecutionResult:
    """Execute an MCP tool with parameters.

    Args:
        tool_name: Name of the tool to execute (bash, python, browser_navigate, etc.)
        request: Tool execution parameters and timeout
        current_user: Authenticated user

    Returns:
        ToolExecutionResult with execution result and metadata

    Raises:
        HTTPException: 404 if tool not found, 500 if execution fails

    Examples:
        # Bash command
        ```bash
        curl -X POST -H "Authorization: Bearer $TOKEN" \\
             -H "Content-Type: application/json" \\
             -d '{"parameters": {"command": "ls -la"}, "timeout": 30}' \\
             "http://localhost:8000/api/v1/mcp/tools/bash/execute"
        ```

        # Python code
        ```bash
        curl -X POST -H "Authorization: Bearer $TOKEN" \\
             -H "Content-Type: application/json" \\
             -d '{"parameters": {"code": "print(2+2)"}, "timeout": 30}' \\
             "http://localhost:8000/api/v1/mcp/tools/python/execute"
        ```

        # Browser navigation
        ```bash
        curl -X POST -H "Authorization: Bearer $TOKEN" \\
             -H "Content-Type: application/json" \\
             -d '{"parameters": {"url": "https://example.com"}, "timeout": 30}' \\
             "http://localhost:8000/api/v1/mcp/tools/browser_navigate/execute"
        ```
    """
    logger.info(
        "mcp_tool_execution_started",
        user_id=current_user.user_id,
        tool_name=tool_name,
        parameters=request.parameters,
        timeout=request.timeout,
    )

    # Check if tool exists
    if tool_name not in TOOL_EXECUTORS:
        logger.warning("tool_not_found", tool_name=tool_name, available_tools=list(TOOL_EXECUTORS.keys()))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}. Available tools: {', '.join(TOOL_EXECUTORS.keys())}",
        )

    # Get tool executor
    executor = TOOL_EXECUTORS[tool_name]

    # Start timer
    start_time = time.perf_counter()

    try:
        # Execute tool with parameters
        result = await executor(**request.parameters, timeout=request.timeout)

        # Calculate execution time
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        # Determine status from result
        if isinstance(result, dict):
            success = result.get("success", True)
            error_message = result.get("error")
        else:
            success = True
            error_message = None

        # Map to status string
        if success:
            execution_status = "success"
        elif error_message and "timed out" in error_message.lower():
            execution_status = "timeout"
        else:
            execution_status = "error"

        logger.info(
            "mcp_tool_execution_completed",
            user_id=current_user.user_id,
            tool_name=tool_name,
            status=execution_status,
            execution_time_ms=execution_time_ms,
        )

        return ToolExecutionResult(
            result=result,
            execution_time_ms=execution_time_ms,
            status=execution_status,
            error_message=error_message,
        )

    except TypeError as e:
        # Parameter mismatch error
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(
            "mcp_tool_parameter_error",
            user_id=current_user.user_id,
            tool_name=tool_name,
            error=str(e),
            parameters=request.parameters,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters for tool {tool_name}: {str(e)}",
        ) from e

    except Exception as e:
        # General execution error
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(
            "mcp_tool_execution_error",
            user_id=current_user.user_id,
            tool_name=tool_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}",
        ) from e


@router.get("/list")
async def list_available_tools(
    current_user: User = Depends(get_current_user),
) -> dict[str, list[str]]:
    """List all available MCP tools.

    Returns:
        Dict with list of available tool names grouped by category

    Example:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" \\
             "http://localhost:8000/api/v1/mcp/tools/list"
        ```
    """
    logger.info("mcp_tools_listed", user_id=current_user.user_id)

    # Group tools by category
    execution_tools = ["bash", "python"]
    browser_tools = [
        "browser_navigate",
        "browser_click",
        "browser_screenshot",
        "browser_evaluate",
        "browser_get_text",
        "browser_fill",
        "browser_type",
    ]

    return {
        "execution": execution_tools,
        "browser": browser_tools,
        "all": list(TOOL_EXECUTORS.keys()),
    }


@router.get("/{tool_name}/schema")
async def get_tool_schema(
    tool_name: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get parameter schema for a specific tool.

    Args:
        tool_name: Name of the tool
        current_user: Authenticated user

    Returns:
        Tool parameter schema

    Raises:
        HTTPException: 404 if tool not found

    Example:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" \\
             "http://localhost:8000/api/v1/mcp/tools/bash/schema"
        ```
    """
    if tool_name not in TOOL_EXECUTORS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        )

    # Import schemas based on tool name
    from src.domains.llm_integration.tools.builtin.bash_tool import BASH_TOOL_SCHEMA
    from src.domains.llm_integration.tools.builtin.browser_executor import (
        CLICK_SCHEMA,
        EVALUATE_SCHEMA,
        FILL_SCHEMA,
        GET_TEXT_SCHEMA,
        NAVIGATE_SCHEMA,
        SCREENSHOT_SCHEMA,
        TYPE_SCHEMA,
    )
    from src.domains.llm_integration.tools.builtin.python_tool import PYTHON_TOOL_SCHEMA

    schema_map = {
        "bash": BASH_TOOL_SCHEMA,
        "python": PYTHON_TOOL_SCHEMA,
        "browser_navigate": NAVIGATE_SCHEMA,
        "browser_click": CLICK_SCHEMA,
        "browser_screenshot": SCREENSHOT_SCHEMA,
        "browser_evaluate": EVALUATE_SCHEMA,
        "browser_get_text": GET_TEXT_SCHEMA,
        "browser_fill": FILL_SCHEMA,
        "browser_type": TYPE_SCHEMA,
    }

    logger.info("tool_schema_retrieved", user_id=current_user.user_id, tool_name=tool_name)

    return {
        "tool_name": tool_name,
        "schema": schema_map.get(tool_name, {}),
    }
