"""Unit tests for Sandboxing Layer.

Sprint 59 Feature 59.5: Docker-based sandbox tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domains.llm_integration.sandbox.resource_limits import (
    ResourceLimits,
    validate_limits,
    get_docker_resource_limits,
)
from src.domains.llm_integration.sandbox.container import DockerSandbox


# =============================================================================
# Resource Limits Tests
# =============================================================================


class TestResourceLimits:
    """Tests for resource limit configuration."""

    def test_default_limits(self):
        """Test default resource limits."""
        limits = ResourceLimits()

        assert limits.max_memory_mb == 256
        assert limits.max_cpu_seconds == 30
        assert limits.network_disabled is True
        assert limits.read_only is True

    def test_custom_limits(self):
        """Test custom resource limits."""
        limits = ResourceLimits(
            max_memory_mb=512,
            max_cpu_seconds=60,
            network_disabled=False,
        )

        assert limits.max_memory_mb == 512
        assert limits.max_cpu_seconds == 60
        assert limits.network_disabled is False

    def test_validate_limits_success(self):
        """Test validation of valid limits."""
        limits = ResourceLimits(max_memory_mb=256, max_cpu_seconds=30)
        valid, error = validate_limits(limits)

        assert valid is True
        assert error is None

    def test_validate_limits_memory_too_small(self):
        """Test validation fails for too small memory."""
        limits = ResourceLimits(max_memory_mb=0)
        valid, error = validate_limits(limits)

        assert valid is False
        assert "memory" in error.lower()

    def test_validate_limits_memory_too_large(self):
        """Test validation fails for too large memory."""
        limits = ResourceLimits(max_memory_mb=20000)
        valid, error = validate_limits(limits)

        assert valid is False
        assert "too large" in error.lower()

    def test_get_docker_resource_limits(self):
        """Test conversion to Docker API parameters."""
        limits = ResourceLimits(
            max_memory_mb=512,
            max_cpu_quota=100000,
            network_disabled=True,
        )

        docker_params = get_docker_resource_limits(limits)

        assert docker_params["mem_limit"] == "512m"
        assert docker_params["cpu_quota"] == 100000
        assert docker_params["network_disabled"] is True
        assert docker_params["read_only"] is True
        assert "no-new-privileges" in docker_params["security_opt"]


# =============================================================================
# Docker Sandbox Tests
# =============================================================================


class TestDockerSandbox:
    """Tests for Docker container sandbox."""

    def test_sandbox_initialization(self):
        """Test sandbox initialization."""
        sandbox = DockerSandbox(
            image="python:3.12-slim",
            memory_limit="256m",
            network_disabled=True,
        )

        assert sandbox.image == "python:3.12-slim"
        assert sandbox.memory_limit == "256m"
        assert sandbox.network_disabled is True

    def test_invalid_limits_raise_error(self):
        """Test that invalid limits raise error."""
        with pytest.raises(ValueError):
            DockerSandbox(
                resource_limits=ResourceLimits(max_memory_mb=0)
            )

    @pytest.mark.asyncio
    async def test_run_bash_command(self):
        """Test running bash command in sandbox."""
        # Mock Docker client
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"hello world\n"

        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container

        sandbox = DockerSandbox()
        sandbox._client = mock_client

        result = await sandbox.run_bash("echo 'hello world'", timeout=30)

        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "hello world" in result["output"]

        # Verify container was removed
        mock_container.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_python_code(self):
        """Test running Python code in sandbox."""
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"42\n"

        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container

        sandbox = DockerSandbox()
        sandbox._client = mock_client

        result = await sandbox.run_python("print(42)", timeout=30)

        assert result["success"] is True
        assert "42" in result["output"]

    @pytest.mark.asyncio
    async def test_sandbox_timeout(self):
        """Test that sandbox enforces timeout."""
        mock_container = MagicMock()
        # Simulate timeout by never completing
        import asyncio
        mock_container.wait.side_effect = asyncio.TimeoutError()

        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container

        sandbox = DockerSandbox()
        sandbox._client = mock_client

        result = await sandbox.run_bash("sleep 100", timeout=1)

        assert result["success"] is False
        assert "timed out" in result["error"].lower()

        # Verify container was killed
        mock_container.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_sandbox_cleanup(self):
        """Test sandbox cleanup."""
        mock_client = MagicMock()

        sandbox = DockerSandbox()
        sandbox._client = mock_client

        await sandbox.cleanup()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test sandbox as context manager."""
        mock_client = MagicMock()

        async with DockerSandbox() as sandbox:
            sandbox._client = mock_client

        # Cleanup should have been called
        mock_client.close.assert_called_once()


# =============================================================================
# Integration with Tool Executor
# =============================================================================


class TestSandboxToolIntegration:
    """Tests for sandbox integration with tools."""

    @pytest.mark.asyncio
    async def test_executor_uses_sandbox_for_required_tools(self):
        """Test that executor uses sandbox for tools that require it."""
        from src.domains.llm_integration.tools.executor import ToolExecutor
        from src.domains.llm_integration.tools.registry import ToolRegistry

        # Register test tool that requires sandbox
        @ToolRegistry.register(
            name="test_sandboxed",
            description="Test tool requiring sandbox",
            parameters={"type": "object", "properties": {}},
            requires_sandbox=True,
        )
        async def test_tool():
            return "executed"

        executor = ToolExecutor(sandbox_enabled=True)

        # Mock sandbox
        with patch("src.domains.llm_integration.sandbox.get_sandbox") as mock_get_sandbox:
            mock_sandbox = AsyncMock()
            mock_sandbox.run.return_value = {"result": "executed"}
            mock_get_sandbox.return_value = mock_sandbox

            result = await executor.execute("test_sandboxed", {})

            # Should have used sandbox
            mock_get_sandbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_executor_fallback_when_docker_unavailable(self):
        """Test that executor falls back when Docker unavailable."""
        from src.domains.llm_integration.tools.executor import ToolExecutor
        from src.domains.llm_integration.tools.registry import ToolRegistry

        @ToolRegistry.register(
            name="test_fallback",
            description="Test fallback",
            parameters={"type": "object", "properties": {}},
            requires_sandbox=True,
        )
        async def test_tool():
            return "fallback_executed"

        executor = ToolExecutor(sandbox_enabled=True)

        # Mock sandbox to raise ImportError
        with patch("src.domains.llm_integration.sandbox.get_sandbox") as mock_get_sandbox:
            mock_get_sandbox.side_effect = ImportError("Docker not installed")

            result = await executor.execute("test_fallback", {})

            # Should fall back to direct execution
            assert "result" in result
            assert result["result"] == "fallback_executed"
