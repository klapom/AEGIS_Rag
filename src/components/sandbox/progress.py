"""
Progress Tracking for Sandbox Sessions.

This module provides functionality to track analysis progress across
sessions using a persistent JSON file. This enables long-running
analysis tasks to be paused and resumed without losing state.

Sprint: 40 - Feature 40.10: Progress Tracking
ADR: ADR-043 Secure Shell Sandbox

Progress File Location: /workspace/aegis-progress.json

Use Cases:
    - Long-running code analysis that spans multiple sessions
    - Resuming after interruption or timeout
    - Tracking which paths have been analyzed
    - Recording entities extracted during analysis

Example:
    >>> from src.components.sandbox.progress import ProgressTracker
    >>> tracker = ProgressTracker("/tmp/workspace/aegis-progress.json")
    >>>
    >>> # Initialize new session
    >>> tracker.init_session("/path/to/repo", ["src/", "tests/"])
    >>>
    >>> # Mark path as analyzed
    >>> tracker.mark_analyzed("src/components/", entities_count=15)
    >>>
    >>> # Get current status
    >>> status = tracker.get_status()
    >>> print(f"Progress: {status['analyzed_paths']}")
    >>>
    >>> # Complete analysis
    >>> tracker.mark_completed()
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SessionInfo:
    """Information about an analysis session."""

    session_id: str
    timestamp: str
    action: str  # started, paused, resumed, completed
    files_processed: int = 0


@dataclass
class ProgressState:
    """
    State of analysis progress.

    This dataclass represents the complete state of an analysis session,
    including what has been analyzed, what remains, and historical information.
    """

    repo: str
    status: str  # in_progress, completed, failed
    started_at: str
    analyzed_paths: list[str] = field(default_factory=list)
    pending_paths: list[str] = field(default_factory=list)
    entities_extracted: int = 0
    sessions: list[SessionInfo] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "repo": self.repo,
            "status": self.status,
            "started_at": self.started_at,
            "analyzed_paths": self.analyzed_paths,
            "pending_paths": self.pending_paths,
            "entities_extracted": self.entities_extracted,
            "sessions": [asdict(s) for s in self.sessions],
            "next_steps": self.next_steps,
            "updated_at": self.updated_at,
        }


class ProgressTracker:
    """
    Tracker for analysis progress across sessions.

    This class manages reading and writing progress state to a JSON file,
    enabling long-running analyses to be paused and resumed.

    The progress file is stored at /workspace/aegis-progress.json within
    the sandbox environment, making it accessible across sandbox executions.

    Args:
        progress_file: Path to progress JSON file

    Example:
        >>> tracker = ProgressTracker("/workspace/aegis-progress.json")
        >>>
        >>> # Start new analysis
        >>> tracker.init_session(
        ...     repo_path="/path/to/repo",
        ...     initial_paths=["src/", "tests/", "docs/"]
        ... )
        >>>
        >>> # Mark path as analyzed
        >>> tracker.mark_analyzed("src/components/", entities_count=20)
        >>>
        >>> # Get pending paths
        >>> pending = tracker.get_pending_paths()
        >>>
        >>> # Add next steps
        >>> tracker.add_next_steps([
        ...     "Analyze tests/ directory",
        ...     "Extract test patterns"
        ... ])
        >>>
        >>> # Complete analysis
        >>> tracker.mark_completed()
    """

    def __init__(self, progress_file: str):
        """Initialize progress tracker."""
        self.progress_file = Path(progress_file)
        self.state: ProgressState | None = None

    def load(self) -> ProgressState | None:
        """
        Load progress state from file.

        Returns:
            ProgressState if file exists, None otherwise
        """
        if not self.progress_file.exists():
            logger.info("progress_file_not_found", file=str(self.progress_file))
            return None

        try:
            with open(self.progress_file) as f:
                data = json.load(f)

            # Convert sessions back to SessionInfo objects
            sessions = [SessionInfo(**s) for s in data.get("sessions", [])]

            self.state = ProgressState(
                repo=data["repo"],
                status=data["status"],
                started_at=data["started_at"],
                analyzed_paths=data.get("analyzed_paths", []),
                pending_paths=data.get("pending_paths", []),
                entities_extracted=data.get("entities_extracted", 0),
                sessions=sessions,
                next_steps=data.get("next_steps", []),
                updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            )

            logger.info(
                "progress_loaded",
                file=str(self.progress_file),
                status=self.state.status,
                analyzed_count=len(self.state.analyzed_paths),
                pending_count=len(self.state.pending_paths),
            )

            return self.state

        except Exception as e:
            logger.exception(
                "progress_load_error", file=str(self.progress_file), error=str(e)
            )
            return None

    def save(self) -> bool:
        """
        Save progress state to file.

        Returns:
            True if successful, False otherwise
        """
        if not self.state:
            logger.warning("progress_save_no_state", message="No state to save")
            return False

        try:
            # Update timestamp
            self.state.updated_at = datetime.utcnow().isoformat()

            # Ensure directory exists
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)

            # Write atomically
            temp_file = self.progress_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(self.state.to_dict(), f, indent=2)

            temp_file.rename(self.progress_file)

            logger.info(
                "progress_saved",
                file=str(self.progress_file),
                status=self.state.status,
                analyzed_count=len(self.state.analyzed_paths),
            )

            return True

        except Exception as e:
            logger.exception(
                "progress_save_error", file=str(self.progress_file), error=str(e)
            )
            return False

    def init_session(
        self, repo_path: str, initial_paths: list[str], session_id: str | None = None
    ) -> None:
        """
        Initialize a new analysis session.

        Args:
            repo_path: Path to repository being analyzed
            initial_paths: List of paths to analyze
            session_id: Optional session ID (auto-generated if not provided)
        """
        now = datetime.utcnow().isoformat()
        session_id = session_id or f"session_{datetime.utcnow().timestamp()}"

        self.state = ProgressState(
            repo=repo_path,
            status="in_progress",
            started_at=now,
            analyzed_paths=[],
            pending_paths=initial_paths.copy(),
            entities_extracted=0,
            sessions=[
                SessionInfo(
                    session_id=session_id,
                    timestamp=now,
                    action="started",
                    files_processed=0,
                )
            ],
            next_steps=[f"Analyze {initial_paths[0]}" if initial_paths else ""],
            updated_at=now,
        )

        self.save()

        logger.info(
            "session_initialized",
            repo=repo_path,
            session_id=session_id,
            pending_count=len(initial_paths),
        )

    def resume_session(self, session_id: str | None = None) -> bool:
        """
        Resume an existing session.

        Args:
            session_id: Session ID (auto-generated if not provided)

        Returns:
            True if resumed successfully, False if no state found
        """
        state = self.load()
        if not state:
            logger.warning("resume_session_no_state", message="No session to resume")
            return False

        session_id = session_id or f"session_{datetime.utcnow().timestamp()}"
        state.sessions.append(
            SessionInfo(
                session_id=session_id,
                timestamp=datetime.utcnow().isoformat(),
                action="resumed",
                files_processed=0,
            )
        )

        self.state = state
        self.save()

        logger.info(
            "session_resumed",
            session_id=session_id,
            analyzed_count=len(state.analyzed_paths),
            pending_count=len(state.pending_paths),
        )

        return True

    def mark_analyzed(self, path: str, entities_count: int = 0) -> None:
        """
        Mark a path as analyzed.

        Args:
            path: Path that was analyzed
            entities_count: Number of entities extracted from this path
        """
        if not self.state:
            logger.warning("mark_analyzed_no_state", path=path)
            return

        if path in self.state.pending_paths:
            self.state.pending_paths.remove(path)

        if path not in self.state.analyzed_paths:
            self.state.analyzed_paths.append(path)

        self.state.entities_extracted += entities_count

        # Update files processed in last session
        if self.state.sessions:
            self.state.sessions[-1].files_processed += 1

        self.save()

        logger.info(
            "path_analyzed",
            path=path,
            entities_count=entities_count,
            total_analyzed=len(self.state.analyzed_paths),
            remaining=len(self.state.pending_paths),
        )

    def add_next_steps(self, steps: list[str]) -> None:
        """
        Add recommended next steps.

        Args:
            steps: List of next steps to add
        """
        if not self.state:
            logger.warning("add_next_steps_no_state")
            return

        self.state.next_steps = steps
        self.save()

    def mark_completed(self) -> None:
        """Mark analysis as completed."""
        if not self.state:
            logger.warning("mark_completed_no_state")
            return

        self.state.status = "completed"
        self.state.sessions.append(
            SessionInfo(
                session_id=self.state.sessions[-1].session_id
                if self.state.sessions
                else "unknown",
                timestamp=datetime.utcnow().isoformat(),
                action="completed",
                files_processed=0,
            )
        )

        self.save()

        logger.info(
            "analysis_completed",
            repo=self.state.repo,
            total_analyzed=len(self.state.analyzed_paths),
            entities_extracted=self.state.entities_extracted,
        )

    def mark_failed(self, reason: str) -> None:
        """
        Mark analysis as failed.

        Args:
            reason: Failure reason
        """
        if not self.state:
            logger.warning("mark_failed_no_state")
            return

        self.state.status = "failed"
        self.state.next_steps = [f"Failed: {reason}"]

        self.save()

        logger.error("analysis_failed", repo=self.state.repo, reason=reason)

    def get_status(self) -> dict[str, Any] | None:
        """
        Get current status.

        Returns:
            Status dictionary or None if no state
        """
        if not self.state:
            state = self.load()
            if not state:
                return None

        return self.state.to_dict() if self.state else None

    def get_pending_paths(self) -> list[str]:
        """
        Get list of pending paths.

        Returns:
            List of paths still to be analyzed
        """
        if not self.state:
            state = self.load()
            if not state:
                return []

        return self.state.pending_paths.copy() if self.state else []

    def get_analyzed_paths(self) -> list[str]:
        """
        Get list of analyzed paths.

        Returns:
            List of paths already analyzed
        """
        if not self.state:
            state = self.load()
            if not state:
                return []

        return self.state.analyzed_paths.copy() if self.state else []
