"""Bash Execution Tool.

Sprint 59 Feature 59.3: Execute bash commands with sandboxing.

This tool allows LLM agents to execute bash commands in a controlled,
sandboxed environment with security validation and resource limits.
"""

import asyncio
from typing import Any

import structlog

from src.domains.llm_integration.tools.builtin.bash_security import (
    is_command_safe,
    sanitize_environment,
)
from src.domains.llm_integration.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


BASH_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "The bash command to execute",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30, max: 300)",
            "default": 30,
            "minimum": 1,
            "maximum": 300,
        },
        "working_dir": {
            "type": "string",
            "description": "Working directory for command execution (optional)",
        },
    },
    "required": ["command"],
}


@ToolRegistry.register(
    name="bash",
    description="Execute a bash command in a sandboxed environment. "
    "Supports common Unix commands like ls, cat, grep, etc. "
    "Dangerous commands are blocked for security.",
    parameters=BASH_TOOL_SCHEMA,
    requires_sandbox=True,
    metadata={
        "category": "execution",
        "danger_level": "high",
        "version": "1.0.0",
    },
)
async def bash_execute(
    command: str,
    timeout: int = 30,
    working_dir: str | None = None,
) -> dict[str, Any]:
    """Execute bash command with timeout and security validation.

    Args:
        command: Bash command to execute
        timeout: Execution timeout in seconds (max 300)
        working_dir: Working directory for execution (optional)

    Returns:
        Dict with stdout, stderr, and exit_code

    Examples:
        >>> result = await bash_execute("ls -la")
        >>> result["exit_code"]
        0
        >>> "total" in result["stdout"]
        True

        >>> result = await bash_execute("rm -rf /")
        >>> "error" in result
        True
    """
    logger.info("bash_execute_called", command=command, timeout=timeout)

    # Enforce maximum timeout
    if timeout > 300:
        logger.warning("timeout_clamped", requested=timeout, clamped=300)
        timeout = 300

    # Security check
    security_check = is_command_safe(command)
    if not security_check.safe:
        logger.error("command_blocked", command=command, reason=security_check.reason)
        return {
            "error": f"Command blocked: {security_check.reason}",
            "exit_code": -1,
        }

    try:
        # Create subprocess with sanitized environment
        env = sanitize_environment()

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=env,
        )

        try:
            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            exit_code = process.returncode or 0

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            logger.info(
                "bash_execute_completed",
                command=command,
                exit_code=exit_code,
                stdout_length=len(stdout_str),
                stderr_length=len(stderr_str),
            )

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": exit_code,
                "success": exit_code == 0,
            }

        except TimeoutError:
            # Kill process on timeout
            logger.warning("bash_execute_timeout", command=command, timeout=timeout)
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass

            return {
                "error": f"Command timed out after {timeout} seconds",
                "exit_code": -1,
                "success": False,
            }

    except FileNotFoundError as e:
        logger.error("working_dir_not_found", working_dir=working_dir, error=str(e))
        return {
            "error": f"Working directory not found: {working_dir}",
            "exit_code": -1,
            "success": False,
        }

    except PermissionError as e:
        logger.error("permission_denied", command=command, error=str(e))
        return {
            "error": f"Permission denied: {e}",
            "exit_code": -1,
            "success": False,
        }

    except Exception as e:
        logger.error("bash_execute_failed", command=command, error=str(e), exc_info=True)
        return {
            "error": f"Execution failed: {e}",
            "exit_code": -1,
            "success": False,
        }


async def bash_execute_batch(
    commands: list[str],
    timeout_per_command: int = 30,
    stop_on_error: bool = True,
) -> list[dict[str, Any]]:
    """Execute multiple bash commands in sequence.

    Args:
        commands: List of bash commands to execute
        timeout_per_command: Timeout per command in seconds
        stop_on_error: Stop execution if a command fails

    Returns:
        List of results for each command

    Examples:
        >>> results = await bash_execute_batch(["pwd", "ls -la"])
        >>> len(results)
        2
        >>> all(r.get("success") for r in results)
        True
    """
    results = []

    for command in commands:
        result = await bash_execute(command, timeout=timeout_per_command)
        results.append(result)

        if stop_on_error and not result.get("success", False):
            logger.info("batch_stopped_on_error", command=command)
            break

    return results
