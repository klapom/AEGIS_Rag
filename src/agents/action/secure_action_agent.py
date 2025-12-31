"""Secure Action Agent with deepagents Integration.

Sprint 67 Feature 67.2: deepagents Integration with BubblewrapSandboxBackend
LangChain-native integration for secure code execution in sandboxed environment.

Architecture:
- Uses BubblewrapSandboxBackend for filesystem and network isolation
- Integrates with deepagents framework for agent orchestration
- Provides timeout enforcement and resource cleanup
- Supports retry logic for transient failures

Security features:
- Sandbox isolation via Bubblewrap
- Timeout enforcement (30s default)
- Output truncation (32KB max)
- Resource cleanup on shutdown
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import structlog

from src.agents.action.bubblewrap_backend import BubblewrapSandboxBackend
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ActionConfig:
    """Configuration for SecureActionAgent.

    Attributes:
        sandbox_timeout: Timeout for sandbox commands in seconds
        max_retries: Maximum number of retries for failed commands
        workspace_path: Path to workspace directory for temporary files
        retry_delay: Delay between retries in seconds
        repo_path: Path to repository (mounted read-only in sandbox)

    """

    sandbox_timeout: int = 30
    max_retries: int = 3
    workspace_path: str = "/tmp/aegis-workspace"
    retry_delay: float = 1.0
    repo_path: str = "/home/admin/projects/aegisrag/AEGIS_Rag"


class SecureActionAgent:
    """Action agent with secure sandboxed code execution via deepagents.

    Provides secure command execution using BubblewrapSandboxBackend with
    timeout enforcement, retry logic, and resource cleanup.

    Features:
    - Sandbox isolation (filesystem + network)
    - Timeout enforcement (configurable)
    - Retry logic for transient failures
    - Resource cleanup on shutdown
    - LangChain-compatible interface

    Example:
        >>> config = ActionConfig(sandbox_timeout=30)
        >>> agent = SecureActionAgent(config=config)
        >>> result = await agent.execute_action("ls -la /repo")
        >>> print(result["output"])
        >>> await agent.cleanup()
    """

    def __init__(
        self,
        config: ActionConfig | None = None,
        sandbox_backend: BubblewrapSandboxBackend | None = None,
    ) -> None:
        """Initialize secure action agent.

        Args:
            config: Agent configuration (defaults to ActionConfig())
            sandbox_backend: Custom sandbox backend (optional)

        Raises:
            ValueError: If repo_path doesn't exist
            FileNotFoundError: If bubblewrap binary not found
        """
        self.logger = structlog.get_logger(__name__)
        self.config = config or ActionConfig()

        # Initialize sandbox backend
        if sandbox_backend is None:
            sandbox_backend = BubblewrapSandboxBackend(
                repo_path=self.config.repo_path,
                timeout=self.config.sandbox_timeout,
                workspace_path=self.config.workspace_path,
            )

        self.sandbox = sandbox_backend

        self.logger.info(
            "secure_action_agent_initialized",
            workspace=self.config.workspace_path,
            timeout=self.config.sandbox_timeout,
            max_retries=self.config.max_retries,
        )

    async def execute_action(
        self, command: str, working_dir: str | None = None
    ) -> dict[str, Any]:
        """Execute action in secure sandbox with retry logic.

        Args:
            command: Shell command to execute
            working_dir: Working directory inside sandbox (default: /workspace)

        Returns:
            Dictionary with execution results:
            - success: Whether execution succeeded
            - output: Combined stdout/stderr output
            - exit_code: Command exit code
            - execution_time_ms: Execution time in milliseconds
            - retries: Number of retries performed
            - error: Error message if failed

        Example:
            >>> result = await agent.execute_action("echo 'Hello World'")
            >>> assert result["success"] is True
            >>> assert "Hello World" in result["output"]
        """
        self.logger.info(
            "executing_action",
            command=command[:100],  # Log first 100 chars
            working_dir=working_dir,
        )

        start_time = time.time()
        last_error = None
        retries = 0

        for attempt in range(self.config.max_retries):
            try:
                # Execute via sandbox
                result = await self.sandbox.execute(
                    command=command, working_dir=working_dir
                )

                execution_time_ms = (time.time() - start_time) * 1000

                if result.success:
                    self.logger.info(
                        "action_execution_success",
                        exit_code=result.exit_code,
                        execution_time_ms=execution_time_ms,
                        retries=retries,
                    )

                    return {
                        "success": True,
                        "output": result.stdout,
                        "exit_code": result.exit_code,
                        "execution_time_ms": execution_time_ms,
                        "retries": retries,
                    }

                # Command failed, prepare for retry
                last_error = f"Command failed with exit code {result.exit_code}: {result.stderr}"

                if result.timed_out:
                    last_error = f"Command timed out after {self.config.sandbox_timeout}s"
                    self.logger.warning(
                        "action_timeout",
                        command=command[:100],
                        timeout=self.config.sandbox_timeout,
                    )
                    # Don't retry timeouts
                    break

                self.logger.warning(
                    "action_execution_failed",
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries,
                    exit_code=result.exit_code,
                    error=result.stderr,
                )

                retries += 1

                # Wait before retry (exponential backoff)
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)

            except Exception as e:
                last_error = str(e)
                self.logger.error(
                    "action_execution_exception",
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__,
                )

                retries += 1

                # Wait before retry
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)

        # All retries exhausted
        execution_time_ms = (time.time() - start_time) * 1000

        self.logger.error(
            "action_execution_failed_all_retries",
            error=last_error,
            retries=retries,
            execution_time_ms=execution_time_ms,
        )

        return {
            "success": False,
            "error": last_error or "Unknown error",
            "exit_code": -1,
            "execution_time_ms": execution_time_ms,
            "retries": retries,
        }

    async def write_file(self, path: str, content: str) -> dict[str, Any]:
        """Write file to workspace.

        Args:
            path: Relative path in workspace
            content: File content

        Returns:
            Dictionary with write results:
            - success: Whether write succeeded
            - path: Absolute path to written file
            - size: File size in bytes
            - error: Error message if failed
        """
        self.logger.info("writing_file", path=path, size=len(content))

        try:
            result = await self.sandbox.write_file(path, content)

            if result.success:
                self.logger.info("file_write_success", path=result.path, size=result.size)
                return {
                    "success": True,
                    "path": result.path,
                    "size": result.size,
                }
            else:
                self.logger.error("file_write_failed", path=path, error=result.error)
                return {"success": False, "error": result.error}

        except Exception as e:
            self.logger.error(
                "file_write_exception", path=path, error=str(e), error_type=type(e).__name__
            )
            return {"success": False, "error": str(e)}

    async def read_file(self, path: str) -> dict[str, Any]:
        """Read file from workspace or repo.

        Args:
            path: Relative path (workspace or repo)

        Returns:
            Dictionary with read results:
            - success: Whether read succeeded
            - content: File content
            - error: Error message if failed
        """
        self.logger.info("reading_file", path=path)

        try:
            content = await self.sandbox.read_file(path)

            self.logger.info("file_read_success", path=path, size=len(content))

            return {"success": True, "content": content}

        except FileNotFoundError as e:
            self.logger.error("file_not_found", path=path)
            return {"success": False, "error": f"File not found: {path}"}

        except ValueError as e:
            # Path traversal attempt
            self.logger.error("file_read_blocked", path=path, error=str(e))
            return {"success": False, "error": str(e)}

        except Exception as e:
            self.logger.error(
                "file_read_exception", path=path, error=str(e), error_type=type(e).__name__
            )
            return {"success": False, "error": str(e)}

    async def cleanup(self) -> None:
        """Cleanup sandbox resources.

        Removes all files in workspace and performs any necessary cleanup.
        Should be called when agent is no longer needed.
        """
        self.logger.info("cleanup_started", workspace=self.config.workspace_path)

        try:
            await self.sandbox.cleanup()
            self.logger.info("cleanup_completed", workspace=self.config.workspace_path)

        except Exception as e:
            self.logger.error(
                "cleanup_failed", error=str(e), error_type=type(e).__name__
            )

    def get_workspace_path(self) -> str:
        """Get absolute path to workspace directory.

        Returns:
            Workspace path
        """
        return self.sandbox.get_workspace_path()

    def get_repo_path(self) -> str:
        """Get absolute path to repository directory.

        Returns:
            Repository path
        """
        return self.sandbox.get_repo_path()
