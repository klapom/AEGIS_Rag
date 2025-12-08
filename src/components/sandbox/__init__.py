"""
Secure Sandbox Components.

This package provides secure sandbox backends for executing commands
in isolated environments with strong security guarantees.

Sprint: 40 - Features 40.7-40.11: Secure Shell Sandbox
ADR: ADR-043 Secure Shell Sandbox

Components:
    - BubblewrapSandboxBackend: Linux Bubblewrap-based sandbox
    - ProgressTracker: Session-persistent progress tracking
    - SandboxBackendProtocol: Protocol interface for backends

Example:
    >>> from src.components.sandbox import BubblewrapSandboxBackend, ProgressTracker
    >>>
    >>> # Create sandbox backend
    >>> backend = BubblewrapSandboxBackend(
    ...     repo_path="/path/to/repo",
    ...     workspace_path="/tmp/workspace"
    ... )
    >>>
    >>> # Execute command
    >>> result = backend.execute("ls -la /repo")
    >>>
    >>> # Track progress
    >>> tracker = ProgressTracker("/tmp/workspace/aegis-progress.json")
    >>> tracker.init_session("/path/to/repo", ["src/", "tests/"])
"""

from src.components.sandbox.bubblewrap_backend import BubblewrapSandboxBackend
from src.components.sandbox.progress import ProgressTracker, ProgressState, SessionInfo
from src.components.sandbox.protocol import (
    EditResult,
    ExecuteResult,
    FileInfo,
    GrepMatch,
    SandboxBackendProtocol,
    WriteResult,
)

__all__ = [
    "BubblewrapSandboxBackend",
    "ProgressTracker",
    "ProgressState",
    "SessionInfo",
    "SandboxBackendProtocol",
    "ExecuteResult",
    "WriteResult",
    "EditResult",
    "FileInfo",
    "GrepMatch",
]
