"""
Unit tests for ProgressTracker.

Sprint: 40 - Feature 40.10: Progress Tracking
ADR: ADR-043 Secure Shell Sandbox

Test Coverage:
    - Session initialization
    - Session resumption
    - Progress tracking
    - Path marking
    - Status retrieval
    - File persistence
    - Error handling
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.components.sandbox.progress import ProgressState, ProgressTracker, SessionInfo


@pytest.fixture
def temp_progress_file():
    """Create a temporary progress file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "aegis-progress.json"


@pytest.fixture
def tracker(temp_progress_file):
    """Create a ProgressTracker instance."""
    return ProgressTracker(str(temp_progress_file))


class TestProgressTrackerInit:
    """Test ProgressTracker initialization."""

    def test_init_creates_tracker(self, temp_progress_file):
        """Test that tracker is initialized correctly."""
        tracker = ProgressTracker(str(temp_progress_file))

        assert tracker.progress_file == temp_progress_file
        assert tracker.state is None

    def test_load_nonexistent_file(self, tracker):
        """Test loading from non-existent file."""
        state = tracker.load()

        assert state is None
        assert tracker.state is None


class TestSessionInitialization:
    """Test session initialization."""

    def test_init_session_creates_state(self, tracker):
        """Test that init_session creates initial state."""
        tracker.init_session(
            repo_path="/path/to/repo",
            initial_paths=["src/", "tests/", "docs/"],
            session_id="test_session_1",
        )

        assert tracker.state is not None
        assert tracker.state.repo == "/path/to/repo"
        assert tracker.state.status == "in_progress"
        assert tracker.state.pending_paths == ["src/", "tests/", "docs/"]
        assert tracker.state.analyzed_paths == []
        assert tracker.state.entities_extracted == 0

    def test_init_session_creates_session_info(self, tracker):
        """Test that init_session creates session info."""
        tracker.init_session(
            repo_path="/path/to/repo",
            initial_paths=["src/"],
            session_id="test_session_1",
        )

        assert len(tracker.state.sessions) == 1
        session = tracker.state.sessions[0]
        assert session.session_id == "test_session_1"
        assert session.action == "started"

    def test_init_session_saves_to_file(self, tracker, temp_progress_file):
        """Test that init_session saves to file."""
        tracker.init_session(
            repo_path="/path/to/repo", initial_paths=["src/"], session_id="test_session_1"
        )

        assert temp_progress_file.exists()

        # Load and verify
        with open(temp_progress_file) as f:
            data = json.load(f)

        assert data["repo"] == "/path/to/repo"
        assert data["status"] == "in_progress"
        assert data["pending_paths"] == ["src/"]


class TestSessionResumption:
    """Test session resumption."""

    def test_resume_session_loads_state(self, tracker, temp_progress_file):
        """Test that resume_session loads existing state."""
        # Initialize first
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/", "tests/"])

        # Create new tracker and resume
        tracker2 = ProgressTracker(str(temp_progress_file))
        success = tracker2.resume_session(session_id="resumed_session")

        assert success
        assert tracker2.state is not None
        assert tracker2.state.repo == "/path/to/repo"
        assert len(tracker2.state.sessions) == 2  # Started + resumed

    def test_resume_session_no_state(self, tracker):
        """Test resume_session with no existing state."""
        success = tracker.resume_session()

        assert not success
        assert tracker.state is None

    def test_resume_session_adds_session_info(self, tracker):
        """Test that resume adds session info."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/"])

        tracker.resume_session(session_id="resumed_1")

        assert len(tracker.state.sessions) == 2
        assert tracker.state.sessions[1].action == "resumed"


class TestProgressTracking:
    """Test progress tracking functionality."""

    def test_mark_analyzed_moves_path(self, tracker):
        """Test that mark_analyzed moves path from pending to analyzed."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/", "tests/"])

        tracker.mark_analyzed("src/", entities_count=20)

        assert "src/" in tracker.state.analyzed_paths
        assert "src/" not in tracker.state.pending_paths
        assert "tests/" in tracker.state.pending_paths

    def test_mark_analyzed_increments_entities(self, tracker):
        """Test that mark_analyzed increments entity count."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/"])

        tracker.mark_analyzed("src/", entities_count=20)
        assert tracker.state.entities_extracted == 20

        tracker.mark_analyzed("tests/", entities_count=15)
        assert tracker.state.entities_extracted == 35

    def test_mark_analyzed_updates_files_processed(self, tracker):
        """Test that mark_analyzed updates files_processed."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/"])

        initial_count = tracker.state.sessions[-1].files_processed

        tracker.mark_analyzed("src/", entities_count=10)
        assert tracker.state.sessions[-1].files_processed == initial_count + 1

    def test_mark_analyzed_no_state(self, tracker):
        """Test mark_analyzed with no state (should not crash)."""
        # Should not raise
        tracker.mark_analyzed("src/", entities_count=10)

    def test_add_next_steps(self, tracker):
        """Test adding next steps."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/"])

        tracker.add_next_steps(["Analyze tests/", "Extract API patterns"])

        assert tracker.state.next_steps == ["Analyze tests/", "Extract API patterns"]

    def test_mark_completed(self, tracker):
        """Test marking analysis as completed."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/"])

        tracker.mark_completed()

        assert tracker.state.status == "completed"
        assert any(s.action == "completed" for s in tracker.state.sessions)

    def test_mark_failed(self, tracker):
        """Test marking analysis as failed."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/"])

        tracker.mark_failed("Network timeout")

        assert tracker.state.status == "failed"
        assert tracker.state.next_steps == ["Failed: Network timeout"]


class TestStatusRetrieval:
    """Test status retrieval methods."""

    def test_get_status_returns_dict(self, tracker):
        """Test that get_status returns dictionary."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/", "tests/"])
        tracker.mark_analyzed("src/", entities_count=20)

        status = tracker.get_status()

        assert isinstance(status, dict)
        assert status["repo"] == "/path/to/repo"
        assert status["status"] == "in_progress"
        assert "src/" in status["analyzed_paths"]
        assert status["entities_extracted"] == 20

    def test_get_status_no_state(self, tracker):
        """Test get_status with no state."""
        status = tracker.get_status()

        assert status is None

    def test_get_pending_paths(self, tracker):
        """Test getting pending paths."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/", "tests/"])
        tracker.mark_analyzed("src/", entities_count=10)

        pending = tracker.get_pending_paths()

        assert pending == ["tests/"]

    def test_get_analyzed_paths(self, tracker):
        """Test getting analyzed paths."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/", "tests/"])
        tracker.mark_analyzed("src/", entities_count=10)

        analyzed = tracker.get_analyzed_paths()

        assert analyzed == ["src/"]


class TestFilePersistence:
    """Test file persistence and loading."""

    def test_save_and_load(self, tracker, temp_progress_file):
        """Test saving and loading state."""
        tracker.init_session(
            repo_path="/path/to/repo",
            initial_paths=["src/", "tests/"],
            session_id="test_session",
        )
        tracker.mark_analyzed("src/", entities_count=20)
        tracker.add_next_steps(["Analyze tests/"])

        # Create new tracker and load
        tracker2 = ProgressTracker(str(temp_progress_file))
        state = tracker2.load()

        assert state is not None
        assert state.repo == "/path/to/repo"
        assert "src/" in state.analyzed_paths
        assert state.entities_extracted == 20
        assert state.next_steps == ["Analyze tests/"]

    def test_save_updates_timestamp(self, tracker):
        """Test that save updates timestamp."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/"])

        first_timestamp = tracker.state.updated_at

        # Modify and save
        tracker.mark_analyzed("src/", entities_count=10)

        second_timestamp = tracker.state.updated_at

        assert second_timestamp >= first_timestamp

    def test_save_atomic_write(self, tracker, temp_progress_file):
        """Test that save uses atomic write."""
        tracker.init_session(repo_path="/path/to/repo", initial_paths=["src/"])

        # Verify no .tmp file left behind
        tmp_file = temp_progress_file.with_suffix(".tmp")
        assert not tmp_file.exists()

    def test_save_no_state(self, tracker):
        """Test save with no state."""
        result = tracker.save()

        assert not result


class TestProgressState:
    """Test ProgressState dataclass."""

    def test_to_dict(self):
        """Test converting ProgressState to dictionary."""
        state = ProgressState(
            repo="/path/to/repo",
            status="in_progress",
            started_at="2025-12-08T10:00:00Z",
            analyzed_paths=["src/"],
            pending_paths=["tests/"],
            entities_extracted=20,
            sessions=[
                SessionInfo(
                    session_id="session_1",
                    timestamp="2025-12-08T10:00:00Z",
                    action="started",
                    files_processed=5,
                )
            ],
            next_steps=["Analyze tests/"],
        )

        data = state.to_dict()

        assert data["repo"] == "/path/to/repo"
        assert data["status"] == "in_progress"
        assert data["analyzed_paths"] == ["src/"]
        assert data["entities_extracted"] == 20
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_id"] == "session_1"


class TestErrorHandling:
    """Test error handling."""

    def test_load_corrupted_file(self, tracker, temp_progress_file):
        """Test loading corrupted JSON file."""
        # Write invalid JSON
        temp_progress_file.parent.mkdir(parents=True, exist_ok=True)
        temp_progress_file.write_text("{invalid json")

        state = tracker.load()

        assert state is None

    def test_load_missing_fields(self, tracker, temp_progress_file):
        """Test loading file with missing required fields."""
        # Write partial JSON
        temp_progress_file.parent.mkdir(parents=True, exist_ok=True)
        temp_progress_file.write_text('{"status": "in_progress"}')

        tracker.load()

        # Should handle gracefully (may be None or partial state)
        # Implementation dependent


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
