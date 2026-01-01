"""Bubblewrap Sandbox Backend for secure code execution.

Sprint 67 Feature 67.1: BubblewrapSandboxBackend
Implements deepagents SandboxBackendProtocol with Linux Bubblewrap isolation.

Security features:
- Filesystem isolation (read-only repo + tmpfs workspace)
- Network isolation (unshare-net)
- Syscall filtering (seccomp)
- Timeout enforcement (30s default)
- Output truncation (32KB max)
"""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)


class ExecuteResult:
    """Result from sandbox command execution.

    Attributes:
        stdout: Standard output from command
        stderr: Standard error from command
        exit_code: Command exit code
        timed_out: Whether command timed out
        truncated: Whether output was truncated
    """

    def __init__(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        timed_out: bool = False,
        truncated: bool = False,
    ) -> None:
        """Initialize execution result.

        Args:
            stdout: Standard output
            stderr: Standard error
            exit_code: Exit code
            timed_out: Whether timeout occurred
            truncated: Whether output was truncated
        """
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.truncated = truncated

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0 and not self.timed_out

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ExecuteResult(exit_code={self.exit_code}, "
            f"timed_out={self.timed_out}, truncated={self.truncated})"
        )


class WriteResult:
    """Result from sandbox file write operation.

    Attributes:
        path: Path to written file
        size: File size in bytes
        success: Whether write was successful
        error: Error message if failed
    """

    def __init__(
        self, path: str, size: int, success: bool = True, error: str | None = None
    ) -> None:
        """Initialize write result.

        Args:
            path: File path
            size: File size
            success: Whether write succeeded
            error: Error message if failed
        """
        self.path = path
        self.size = size
        self.success = success
        self.error = error

    def __repr__(self) -> str:
        """String representation."""
        return f"WriteResult(path={self.path}, size={self.size}, success={self.success})"


class BubblewrapSandboxBackend:
    """Bubblewrap-based sandbox for secure command execution.

    Implements deepagents SandboxBackendProtocol with Linux Bubblewrap isolation.

    Security layers:
    1. Filesystem: Read-only repo + isolated tmpfs workspace
    2. Network: Unshare network namespace (no network access)
    3. Syscalls: Seccomp profile filtering (optional)
    4. Resources: Timeout enforcement, output limits

    Example:
        >>> backend = BubblewrapSandboxBackend(
        ...     repo_path="/path/to/repo",
        ...     timeout=30
        ... )
        >>> result = await backend.execute("ls -la")
        >>> print(result.stdout)
    """

    MAX_OUTPUT_SIZE = 32 * 1024  # 32KB output limit
    DEFAULT_TIMEOUT = 30  # 30 seconds default timeout

    def __init__(
        self,
        repo_path: str,
        allowed_domains: list[str] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        seccomp_profile: str | None = None,
        workspace_path: str | None = None,
        enable_network_isolation: bool = True,
    ) -> None:
        """Initialize Bubblewrap sandbox backend.

        Args:
            repo_path: Path to repository (mounted read-only)
            allowed_domains: List of allowed network domains (currently unused)
            timeout: Command timeout in seconds
            seccomp_profile: Path to seccomp profile JSON (optional)
            workspace_path: Custom workspace path (default: /tmp/aegis-workspace)
            enable_network_isolation: Whether to use --unshare-net (requires CAP_NET_ADMIN)
                If False, network isolation is disabled for unprivileged environments.

        Raises:
            ValueError: If repo_path doesn't exist
            FileNotFoundError: If bubblewrap binary not found
        """
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        # Workspace: tmpfs for temporary files
        self.workspace = Path(workspace_path or "/tmp/aegis-workspace")
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.allowed_domains = allowed_domains or []
        self.timeout = timeout
        self.seccomp_profile = seccomp_profile
        self.enable_network_isolation = enable_network_isolation
        self.logger = logger.bind(backend="bubblewrap")

        # Verify bubblewrap is installed
        if not shutil.which("bwrap"):
            raise FileNotFoundError(
                "bubblewrap not found. Install with: sudo apt-get install bubblewrap"
            )

        # Log network isolation status
        isolation_status = "enabled" if enable_network_isolation else "disabled (unprivileged mode)"
        self.logger.info(
            "sandbox_backend_initialized",
            repo_path=str(self.repo_path),
            workspace=str(self.workspace),
            timeout=self.timeout,
            network_isolation=isolation_status,
        )

    def _build_bubblewrap_command(self, command: str, working_dir: str | None = None) -> list[str]:
        """Build bubblewrap command with security restrictions.

        Args:
            command: Shell command to execute
            working_dir: Working directory inside sandbox

        Returns:
            List of command arguments for subprocess
        """
        bwrap_args = [
            "bwrap",
            # Filesystem isolation
            "--ro-bind",
            "/usr",
            "/usr",  # Read-only system binaries
            "--ro-bind",
            "/lib",
            "/lib",  # Read-only libraries
            "--ro-bind",
            "/lib64",
            "/lib64",  # Read-only 64-bit libraries
            "--ro-bind",
            "/bin",
            "/bin",  # Read-only binaries
            "--ro-bind",
            "/sbin",
            "/sbin",  # Read-only system binaries
            "--proc",
            "/proc",  # Proc filesystem
            "--dev",
            "/dev",  # Device filesystem (minimal)
            "--tmpfs",
            "/tmp",  # Temporary filesystem (isolated)
            # Repository: Read-only
            "--ro-bind",
            str(self.repo_path),
            "/repo",
            # Workspace: Read-write tmpfs
            "--bind",
            str(self.workspace),
            "/workspace",
            # Working directory
            "--chdir",
            working_dir or "/workspace",
            # Process/IPC isolation (always enabled)
            "--unshare-pid",  # Separate PID namespace
            "--unshare-ipc",  # Separate IPC namespace
            "--die-with-parent",  # Kill sandbox if parent dies
        ]

        # Network isolation (optional, requires CAP_NET_ADMIN)
        if self.enable_network_isolation:
            bwrap_args.insert(len(bwrap_args) - 1, "--unshare-net")

        # Add seccomp profile if provided
        if self.seccomp_profile and Path(self.seccomp_profile).exists():
            bwrap_args.extend(["--seccomp", "9"])
            bwrap_args.append(f"9<{self.seccomp_profile}")

        # Command to execute
        bwrap_args.extend(["--", "/bin/bash", "-c", command])

        return bwrap_args

    async def execute(self, command: str, working_dir: str | None = None) -> ExecuteResult:
        """Execute command in Bubblewrap sandbox.

        Executes a shell command with process/IPC isolation. Network isolation
        is optional (disabled by default for unprivileged environments).

        Args:
            command: Shell command to execute
            working_dir: Working directory (default: /workspace)

        Returns:
            ExecuteResult with stdout, stderr, exit code, and timeout status

        Raises:
            asyncio.TimeoutError: If command exceeds timeout
        """
        self.logger.info(
            "sandbox_execute_start",
            command=command[:100],  # Log first 100 chars
            working_dir=working_dir,
            timeout=self.timeout,
        )

        # Build bubblewrap command
        bwrap_cmd = self._build_bubblewrap_command(command, working_dir)

        try:
            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                *bwrap_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
                timed_out = False
            except asyncio.TimeoutError:
                # Kill process on timeout
                process.kill()
                await process.wait()
                stdout_bytes = b""
                stderr_bytes = b"Command timed out"
                timed_out = True

            # Decode output
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # Truncate if needed
            truncated = False
            if len(stdout) > self.MAX_OUTPUT_SIZE:
                stdout = stdout[: self.MAX_OUTPUT_SIZE]
                stdout += "\n... (output truncated)"
                truncated = True

            if len(stderr) > self.MAX_OUTPUT_SIZE:
                stderr = stderr[: self.MAX_OUTPUT_SIZE]
                stderr += "\n... (output truncated)"
                truncated = True

            exit_code = process.returncode or (124 if timed_out else 0)

            result = ExecuteResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                timed_out=timed_out,
                truncated=truncated,
            )

            self.logger.info(
                "sandbox_execute_complete",
                exit_code=exit_code,
                timed_out=timed_out,
                truncated=truncated,
                stdout_length=len(stdout),
                stderr_length=len(stderr),
            )

            return result

        except Exception as e:
            self.logger.error("sandbox_execute_error", error=str(e), error_type=type(e).__name__)
            return ExecuteResult(
                stdout="",
                stderr=f"Sandbox execution error: {str(e)}",
                exit_code=1,
            )

    async def write_file(self, path: str, content: str) -> WriteResult:
        """Write file to workspace.

        Args:
            path: Relative path in workspace
            content: File content

        Returns:
            WriteResult with path, size, success status

        Raises:
            ValueError: If path attempts to escape workspace
        """
        # Resolve path relative to workspace
        file_path = (self.workspace / path).resolve()

        # Security: Prevent path traversal
        if not str(file_path).startswith(str(self.workspace)):
            error_msg = f"Path traversal attempt blocked: {path}"
            self.logger.error("sandbox_write_blocked", path=path, reason="path_traversal")
            return WriteResult(path=path, size=0, success=False, error=error_msg)

        try:
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            file_path.write_text(content)
            size = file_path.stat().st_size

            self.logger.info("sandbox_file_written", path=str(file_path), size=size)

            return WriteResult(path=str(file_path), size=size, success=True)

        except Exception as e:
            error_msg = f"File write error: {str(e)}"
            self.logger.error(
                "sandbox_write_error",
                path=path,
                error=str(e),
                error_type=type(e).__name__,
            )
            return WriteResult(path=path, size=0, success=False, error=error_msg)

    async def read_file(self, path: str) -> str:
        """Read file from workspace or repo.

        Args:
            path: Relative path (workspace or repo)

        Returns:
            File content

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path attempts to escape allowed directories
        """
        # Try workspace first
        workspace_path = (self.workspace / path).resolve()
        repo_path = (self.repo_path / path).resolve()

        # Security: Check path is within allowed directories
        in_workspace = str(workspace_path).startswith(str(self.workspace))
        in_repo = str(repo_path).startswith(str(self.repo_path))

        if not (in_workspace or in_repo):
            raise ValueError(f"Path traversal attempt blocked: {path}")

        # Read from workspace if exists, otherwise try repo
        if workspace_path.exists():
            content = workspace_path.read_text()
            self.logger.info("sandbox_file_read", path=str(workspace_path), source="workspace")
            return content
        elif repo_path.exists():
            content = repo_path.read_text()
            self.logger.info("sandbox_file_read", path=str(repo_path), source="repo")
            return content
        else:
            raise FileNotFoundError(f"File not found: {path}")

    async def cleanup(self) -> None:
        """Clean up workspace directory.

        Removes all files in workspace (not the workspace directory itself).
        """
        try:
            for item in self.workspace.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

            self.logger.info("sandbox_workspace_cleaned", workspace=str(self.workspace))

        except Exception as e:
            self.logger.error(
                "sandbox_cleanup_error",
                error=str(e),
                error_type=type(e).__name__,
            )

    def get_workspace_path(self) -> str:
        """Get absolute path to workspace directory.

        Returns:
            Workspace path
        """
        return str(self.workspace)

    def get_repo_path(self) -> str:
        """Get absolute path to repository directory.

        Returns:
            Repository path
        """
        return str(self.repo_path)
