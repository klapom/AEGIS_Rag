"""Unit tests for SecureActionAgent.

Sprint 67 Feature 67.2: deepagents Integration with BubblewrapSandboxBackend
Tests for secure code execution with timeout, retry logic, and resource cleanup.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.action.bubblewrap_backend import ExecuteResult, WriteResult
from src.agents.action.secure_action_agent import ActionConfig, SecureActionAgent


@pytest.fixture
def mock_sandbox_backend():
    """Create mock sandbox backend for testing."""
    backend = Mock()
    backend.execute = AsyncMock()
    backend.write_file = AsyncMock()
    backend.read_file = AsyncMock()
    backend.cleanup = AsyncMock()
    backend.get_workspace_path = Mock(return_value="/tmp/aegis-workspace")
    backend.get_repo_path = Mock(return_value="/home/admin/projects/aegisrag/AEGIS_Rag")
    return backend


@pytest.fixture
def action_config():
    """Create test action configuration."""
    return ActionConfig(
        sandbox_timeout=10,
        max_retries=3,
        workspace_path="/tmp/test-workspace",
        retry_delay=0.1,  # Faster for tests
    )


class TestSecureActionAgent:
    """Test suite for SecureActionAgent."""

    def test_initialization(self, action_config, mock_sandbox_backend):
        """Test agent initialization with custom config and backend."""
        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        assert agent.config == action_config
        assert agent.sandbox == mock_sandbox_backend

    def test_initialization_default_config(self):
        """Test agent initialization with default config."""
        with patch("src.agents.action.secure_action_agent.BubblewrapSandboxBackend"):
            agent = SecureActionAgent()

            assert agent.config is not None
            assert agent.config.sandbox_timeout == 30
            assert agent.config.max_retries == 3

    @pytest.mark.asyncio
    async def test_execute_action_success(self, action_config, mock_sandbox_backend):
        """Test successful command execution."""
        # Mock successful execution
        mock_sandbox_backend.execute.return_value = ExecuteResult(
            stdout="Hello World\n", stderr="", exit_code=0, timed_out=False
        )

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.execute_action("echo 'Hello World'")

        assert result["success"] is True
        assert "Hello World" in result["output"]
        assert result["exit_code"] == 0
        assert result["retries"] == 0
        assert "execution_time_ms" in result

        # Verify sandbox was called
        mock_sandbox_backend.execute.assert_called_once_with(
            command="echo 'Hello World'", working_dir=None
        )

    @pytest.mark.asyncio
    async def test_execute_action_with_working_dir(self, action_config, mock_sandbox_backend):
        """Test command execution with custom working directory."""
        mock_sandbox_backend.execute.return_value = ExecuteResult(
            stdout="file1.txt\n", stderr="", exit_code=0, timed_out=False
        )

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.execute_action("ls", working_dir="/workspace/data")

        assert result["success"] is True

        # Verify working_dir was passed
        mock_sandbox_backend.execute.assert_called_once_with(
            command="ls", working_dir="/workspace/data"
        )

    @pytest.mark.asyncio
    async def test_execute_action_timeout(self, action_config, mock_sandbox_backend):
        """Test command timeout handling."""
        # Mock timeout
        mock_sandbox_backend.execute.return_value = ExecuteResult(
            stdout="",
            stderr="Command timed out",
            exit_code=124,
            timed_out=True,
        )

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.execute_action("sleep 100")

        assert result["success"] is False
        assert "timed out" in result["error"]
        assert result["retries"] == 0  # No retry on timeout

    @pytest.mark.asyncio
    async def test_execute_action_retry_logic(self, action_config, mock_sandbox_backend):
        """Test retry logic for transient failures."""
        # First two attempts fail, third succeeds
        mock_sandbox_backend.execute.side_effect = [
            ExecuteResult(stdout="", stderr="Connection refused", exit_code=1),
            ExecuteResult(stdout="", stderr="Connection refused", exit_code=1),
            ExecuteResult(stdout="Success\n", stderr="", exit_code=0),
        ]

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.execute_action("curl http://example.com")

        assert result["success"] is True
        assert result["retries"] == 2
        assert mock_sandbox_backend.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_action_all_retries_exhausted(self, action_config, mock_sandbox_backend):
        """Test behavior when all retries are exhausted."""
        # All attempts fail
        mock_sandbox_backend.execute.return_value = ExecuteResult(
            stdout="", stderr="Command failed", exit_code=1
        )

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.execute_action("failing_command")

        assert result["success"] is False
        assert "Command failed" in result["error"]
        assert result["retries"] == 3
        assert mock_sandbox_backend.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_action_exception_handling(self, action_config, mock_sandbox_backend):
        """Test exception handling during execution."""
        # Mock exception on first attempt, success on second
        mock_sandbox_backend.execute.side_effect = [
            Exception("Temporary error"),
            ExecuteResult(stdout="OK\n", stderr="", exit_code=0),
        ]

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.execute_action("test_command")

        assert result["success"] is True
        assert result["retries"] == 1
        assert mock_sandbox_backend.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_write_file_success(self, action_config, mock_sandbox_backend):
        """Test successful file write."""
        mock_sandbox_backend.write_file.return_value = WriteResult(
            path="/tmp/test-workspace/test.txt", size=11, success=True
        )

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.write_file("test.txt", "Hello World")

        assert result["success"] is True
        assert result["path"] == "/tmp/test-workspace/test.txt"
        assert result["size"] == 11

        mock_sandbox_backend.write_file.assert_called_once_with("test.txt", "Hello World")

    @pytest.mark.asyncio
    async def test_write_file_failure(self, action_config, mock_sandbox_backend):
        """Test file write failure."""
        mock_sandbox_backend.write_file.return_value = WriteResult(
            path="test.txt", size=0, success=False, error="Path traversal blocked"
        )

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.write_file("../etc/passwd", "malicious")

        assert result["success"] is False
        assert "Path traversal" in result["error"]

    @pytest.mark.asyncio
    async def test_write_file_exception(self, action_config, mock_sandbox_backend):
        """Test file write exception handling."""
        mock_sandbox_backend.write_file.side_effect = Exception("Disk full")

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.write_file("test.txt", "content")

        assert result["success"] is False
        assert "Disk full" in result["error"]

    @pytest.mark.asyncio
    async def test_read_file_success(self, action_config, mock_sandbox_backend):
        """Test successful file read."""
        mock_sandbox_backend.read_file.return_value = "File content\n"

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.read_file("test.txt")

        assert result["success"] is True
        assert result["content"] == "File content\n"

        mock_sandbox_backend.read_file.assert_called_once_with("test.txt")

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, action_config, mock_sandbox_backend):
        """Test file read when file doesn't exist."""
        mock_sandbox_backend.read_file.side_effect = FileNotFoundError("File not found")

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.read_file("nonexistent.txt")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_file_path_traversal(self, action_config, mock_sandbox_backend):
        """Test file read with path traversal attempt."""
        mock_sandbox_backend.read_file.side_effect = ValueError(
            "Path traversal attempt blocked"
        )

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.read_file("../../../etc/passwd")

        assert result["success"] is False
        assert "Path traversal" in result["error"]

    @pytest.mark.asyncio
    async def test_read_file_exception(self, action_config, mock_sandbox_backend):
        """Test file read exception handling."""
        mock_sandbox_backend.read_file.side_effect = Exception("Permission denied")

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        result = await agent.read_file("test.txt")

        assert result["success"] is False
        assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    async def test_cleanup(self, action_config, mock_sandbox_backend):
        """Test cleanup method."""
        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        await agent.cleanup()

        mock_sandbox_backend.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_exception(self, action_config, mock_sandbox_backend):
        """Test cleanup exception handling."""
        mock_sandbox_backend.cleanup.side_effect = Exception("Cleanup error")

        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        # Should not raise exception
        await agent.cleanup()

        mock_sandbox_backend.cleanup.assert_called_once()

    def test_get_workspace_path(self, action_config, mock_sandbox_backend):
        """Test get_workspace_path method."""
        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        path = agent.get_workspace_path()

        assert path == "/tmp/aegis-workspace"
        mock_sandbox_backend.get_workspace_path.assert_called_once()

    def test_get_repo_path(self, action_config, mock_sandbox_backend):
        """Test get_repo_path method."""
        agent = SecureActionAgent(config=action_config, sandbox_backend=mock_sandbox_backend)

        path = agent.get_repo_path()

        assert path == "/home/admin/projects/aegisrag/AEGIS_Rag"
        mock_sandbox_backend.get_repo_path.assert_called_once()


class TestActionConfig:
    """Test suite for ActionConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ActionConfig()

        assert config.sandbox_timeout == 30
        assert config.max_retries == 3
        assert config.workspace_path == "/tmp/aegis-workspace"
        assert config.retry_delay == 1.0
        assert config.repo_path == "/home/admin/projects/aegisrag/AEGIS_Rag"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ActionConfig(
            sandbox_timeout=60,
            max_retries=5,
            workspace_path="/custom/workspace",
            retry_delay=2.0,
            repo_path="/custom/repo",
        )

        assert config.sandbox_timeout == 60
        assert config.max_retries == 5
        assert config.workspace_path == "/custom/workspace"
        assert config.retry_delay == 2.0
        assert config.repo_path == "/custom/repo"


@pytest.mark.integration
class TestSecureActionAgentIntegration:
    """Integration tests for SecureActionAgent with real BubblewrapSandboxBackend.

    These tests require bubblewrap to be installed on the system.
    Skip if bubblewrap is not available.
    """

    @pytest.fixture
    def real_agent(self, tmp_path):
        """Create agent with real sandbox backend."""
        import shutil

        if not shutil.which("bwrap"):
            pytest.skip("bubblewrap not installed")

        config = ActionConfig(
            sandbox_timeout=5,
            workspace_path=str(tmp_path),
            repo_path="/tmp",  # Use /tmp as safe repo path
        )

        return SecureActionAgent(config=config)

    @pytest.mark.asyncio
    async def test_real_command_execution(self, real_agent):
        """Test real command execution with bubblewrap.

        Note: This test may fail with "Operation not permitted" if running
        without CAP_NET_ADMIN capability (required for network namespace).
        This is expected in unprivileged environments.
        """
        result = await real_agent.execute_action("echo 'Integration test'")

        # Check if we got permission error (expected without CAP_NET_ADMIN)
        if not result["success"] and "Operation not permitted" in result.get("error", ""):
            pytest.skip("Bubblewrap requires CAP_NET_ADMIN for network isolation")

        assert result["success"] is True
        assert "Integration test" in result["output"]
        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_real_file_operations(self, real_agent):
        """Test real file write and read operations."""
        # Write file
        write_result = await real_agent.write_file("integration_test.txt", "Test content\n")
        assert write_result["success"] is True

        # Read file
        read_result = await real_agent.read_file("integration_test.txt")
        assert read_result["success"] is True
        assert read_result["content"] == "Test content\n"

        # Cleanup
        await real_agent.cleanup()
