"""
Sandbox Backend Protocol Definitions.

This module defines the protocol interfaces for sandbox backends,
compatible with the deepagents specification but implemented locally
since deepagents is not available.

Sprint: 40 - Feature 40.7: BubblewrapSandboxBackend
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ExecuteResult:
    """Result from executing a command in the sandbox."""

    stdout: str
    stderr: str
    exit_code: int


@dataclass
class WriteResult:
    """Result from writing a file in the sandbox."""

    success: bool
    error: str | None = None


@dataclass
class EditResult:
    """Result from editing a file in the sandbox."""

    success: bool
    error: str | None = None


@dataclass
class FileInfo:
    """Information about a file in the sandbox."""

    name: str
    size: int
    is_dir: bool


@dataclass
class GrepMatch:
    """A grep match result."""

    file: str
    line_number: int
    content: str


class SandboxBackendProtocol(Protocol):
    """
    Protocol for sandbox backend implementations.

    This protocol defines the interface that all sandbox backends must implement.
    It provides methods for executing commands, reading/writing files, and
    performing file operations in a secure, isolated environment.
    """

    def execute(self, command: str) -> ExecuteResult:
        """
        Execute a shell command in the sandbox.

        Args:
            command: Shell command to execute

        Returns:
            ExecuteResult with stdout, stderr, and exit_code
        """
        ...

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """
        Read a file from the sandbox filesystem.

        Args:
            file_path: Path to file (relative to sandbox root)
            offset: Line offset to start reading from
            limit: Maximum number of lines to read

        Returns:
            File contents as string
        """
        ...

    def write(self, file_path: str, content: str) -> WriteResult:
        """
        Write content to a file in the sandbox.

        Args:
            file_path: Path to file (must be in writable area)
            content: Content to write

        Returns:
            WriteResult indicating success or failure
        """
        ...

    def edit(self, file_path: str, old_string: str, new_string: str) -> EditResult:
        """
        Edit a file by replacing old_string with new_string.

        Args:
            file_path: Path to file to edit
            old_string: String to replace
            new_string: Replacement string

        Returns:
            EditResult indicating success or failure
        """
        ...

    def ls_info(self, path: str = "/repo") -> list[FileInfo]:
        """
        List directory contents.

        Args:
            path: Directory path to list

        Returns:
            List of FileInfo objects
        """
        ...

    def grep_raw(
        self, pattern: str, path: str = "/repo", glob: str | None = None
    ) -> list[GrepMatch] | str:
        """
        Search for pattern in files.

        Args:
            pattern: Regex pattern to search for
            path: Directory to search in
            glob: Optional glob pattern to filter files

        Returns:
            List of GrepMatch objects or error string
        """
        ...
