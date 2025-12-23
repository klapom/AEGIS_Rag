"""Python Execution Tool.

Sprint 59 Feature 59.4: Execute Python code with sandboxing.

This tool allows LLM agents to execute Python code in a controlled environment
with AST validation and restricted globals.
"""

import asyncio
import sys
from io import StringIO
from typing import Any

import structlog

from src.domains.llm_integration.tools.builtin.python_security import (
    create_restricted_globals,
    get_code_complexity,
    validate_python_code,
)
from src.domains.llm_integration.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


PYTHON_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": "Python code to execute. Must be valid Python 3 syntax.",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30, max: 300)",
            "default": 30,
            "minimum": 1,
            "maximum": 300,
        },
    },
    "required": ["code"],
}


@ToolRegistry.register(
    name="python",
    description="Execute Python code in a sandboxed environment. "
    "Supports standard library modules like math, json, datetime, re, etc. "
    "Dangerous modules (os, subprocess, sys) are blocked for security.",
    parameters=PYTHON_TOOL_SCHEMA,
    requires_sandbox=True,
    metadata={
        "category": "execution",
        "danger_level": "high",
        "version": "1.0.0",
    },
)
async def python_execute(
    code: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute Python code with restrictions.

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds (max 300)

    Returns:
        Dict with output, result, and any errors

    Examples:
        >>> result = await python_execute("print('hello')")
        >>> result["success"]
        True
        >>> "hello" in result["output"]
        True

        >>> result = await python_execute("import os")
        >>> result["success"]
        False
        >>> "Blocked module" in result["error"]
        True
    """
    logger.info("python_execute_called", code_length=len(code), timeout=timeout)

    # Enforce maximum timeout
    if timeout > 300:
        logger.warning("timeout_clamped", requested=timeout, clamped=300)
        timeout = 300

    # Validate code first
    validation = validate_python_code(code)
    if not validation.valid:
        logger.error("code_validation_failed", error=validation.error)
        return {
            "error": validation.error,
            "success": False,
        }

    # Get code complexity metrics
    complexity = get_code_complexity(code)
    if complexity["lines"] > 1000:
        logger.warning("code_too_long", lines=complexity["lines"])
        return {
            "error": f"Code too long: {complexity['lines']} lines (max 1000)",
            "success": False,
        }

    # Execute in separate task with timeout
    try:
        result = await asyncio.wait_for(
            _execute_python_code(code),
            timeout=timeout,
        )
        return result

    except TimeoutError:
        logger.warning("python_execute_timeout", timeout=timeout)
        return {
            "error": f"Execution timed out after {timeout} seconds",
            "success": False,
        }

    except Exception as e:
        logger.error("python_execute_failed", error=str(e), exc_info=True)
        return {
            "error": f"Execution failed: {e}",
            "success": False,
        }


async def _execute_python_code(code: str) -> dict[str, Any]:
    """Internal function to execute Python code.

    Args:
        code: Python code to execute

    Returns:
        Dict with execution results
    """
    # Capture stdout
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()

    try:
        # Create restricted globals
        restricted_globals = create_restricted_globals()
        restricted_locals: dict[str, Any] = {}

        # Execute code
        exec(code, restricted_globals, restricted_locals)

        # Get captured output
        stdout_output = sys.stdout.getvalue()
        stderr_output = sys.stderr.getvalue()

        # Get any variables created
        user_vars = {k: v for k, v in restricted_locals.items() if not k.startswith("_")}

        logger.info(
            "python_execute_success",
            stdout_length=len(stdout_output),
            stderr_length=len(stderr_output),
            num_vars=len(user_vars),
        )

        return {
            "output": stdout_output,
            "stderr": stderr_output if stderr_output else None,
            "variables": user_vars,
            "success": True,
        }

    except Exception as e:
        # Get captured output before exception
        stdout_output = sys.stdout.getvalue()
        stderr_output = sys.stderr.getvalue()

        logger.error(
            "python_execution_error",
            error=str(e),
            error_type=type(e).__name__,
        )

        return {
            "error": f"{type(e).__name__}: {str(e)}",
            "output": stdout_output if stdout_output else None,
            "stderr": stderr_output if stderr_output else None,
            "success": False,
        }

    finally:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr


async def python_execute_batch(
    code_snippets: list[str],
    timeout_per_snippet: int = 30,
    stop_on_error: bool = True,
    shared_globals: bool = False,
) -> list[dict[str, Any]]:
    """Execute multiple Python code snippets.

    Args:
        code_snippets: List of Python code snippets to execute
        timeout_per_snippet: Timeout per snippet in seconds
        stop_on_error: Stop execution if a snippet fails
        shared_globals: Share globals between snippets

    Returns:
        List of results for each snippet

    Examples:
        >>> results = await python_execute_batch([
        ...     "x = 10",
        ...     "print(x + 5)"
        ... ], shared_globals=True)
        >>> len(results)
        2
        >>> results[1]["success"]
        True
    """
    results = []
    shared_context = create_restricted_globals() if shared_globals else None

    for idx, code in enumerate(code_snippets):
        logger.info("batch_execute", snippet=idx + 1, total=len(code_snippets))

        if shared_context:
            # Execute with shared globals
            result = await _execute_with_context(code, shared_context, timeout_per_snippet)
        else:
            # Execute independently
            result = await python_execute(code, timeout=timeout_per_snippet)

        results.append(result)

        if stop_on_error and not result.get("success", False):
            logger.info("batch_stopped_on_error", snippet=idx + 1)
            break

    return results


async def _execute_with_context(
    code: str,
    globals_dict: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    """Execute code with shared globals context.

    Args:
        code: Python code to execute
        globals_dict: Shared globals dictionary
        timeout: Execution timeout

    Returns:
        Dict with execution results
    """
    # Validate code
    validation = validate_python_code(code)
    if not validation.valid:
        return {"error": validation.error, "success": False}

    # Execute with timeout
    try:
        result = await asyncio.wait_for(
            _execute_with_globals(code, globals_dict),
            timeout=timeout,
        )
        return result
    except TimeoutError:
        return {
            "error": f"Execution timed out after {timeout} seconds",
            "success": False,
        }


async def _execute_with_globals(
    code: str,
    globals_dict: dict[str, Any],
) -> dict[str, Any]:
    """Execute code with specific globals.

    Args:
        code: Python code to execute
        globals_dict: Globals dictionary

    Returns:
        Dict with execution results
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()

    try:
        exec(code, globals_dict)

        stdout_output = sys.stdout.getvalue()
        stderr_output = sys.stderr.getvalue()

        return {
            "output": stdout_output,
            "stderr": stderr_output if stderr_output else None,
            "success": True,
        }

    except Exception as e:
        stdout_output = sys.stdout.getvalue()
        stderr_output = sys.stderr.getvalue()

        return {
            "error": f"{type(e).__name__}: {str(e)}",
            "output": stdout_output if stdout_output else None,
            "stderr": stderr_output if stderr_output else None,
            "success": False,
        }

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
