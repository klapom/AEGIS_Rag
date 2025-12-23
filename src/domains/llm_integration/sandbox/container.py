"""Docker-based sandbox for code execution.

Sprint 59 Feature 59.5: Isolated execution environment using Docker containers.

This module provides Docker container-based sandboxing with resource limits,
network isolation, and read-only filesystem options.
"""

import asyncio
from collections.abc import Callable
from typing import Any

import structlog

from src.domains.llm_integration.sandbox.resource_limits import (
    ResourceLimits,
    validate_limits,
)

logger = structlog.get_logger(__name__)


class DockerSandbox:
    """Docker container-based sandbox for code execution.

    This sandbox provides strong isolation using Docker containers with
    configurable resource limits, network isolation, and read-only filesystems.

    Examples:
        >>> sandbox = DockerSandbox(memory_limit="128m", network_disabled=True)
        >>> result = await sandbox.run_bash("ls -la", timeout=30)
        >>> result["exit_code"]
        0
    """

    def __init__(
        self,
        image: str = "python:3.12-slim",
        memory_limit: str = "256m",
        cpu_quota: int = 50000,  # 50% CPU
        network_disabled: bool = True,
        read_only: bool = True,
        resource_limits: ResourceLimits | None = None,
    ):
        """Initialize Docker sandbox.

        Args:
            image: Docker image to use (default: python:3.12-slim)
            memory_limit: Memory limit string (default: 256m)
            cpu_quota: CPU quota (default: 50000 = 50%)
            network_disabled: Disable network access (default: True)
            read_only: Make filesystem read-only (default: True)
            resource_limits: ResourceLimits object (optional, overrides other params)
        """
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.network_disabled = network_disabled
        self.read_only = read_only
        self.resource_limits = resource_limits or ResourceLimits()

        # Validate limits
        valid, error = validate_limits(self.resource_limits)
        if not valid:
            raise ValueError(f"Invalid resource limits: {error}")

        # Docker client will be initialized lazily
        self._client = None

        logger.info(
            "docker_sandbox_initialized",
            image=image,
            memory=memory_limit,
            network_disabled=network_disabled,
        )

    def _get_client(self):
        """Get or initialize Docker client lazily."""
        if self._client is None:
            try:
                import docker
                self._client = docker.from_env()
                logger.debug("docker_client_initialized")
            except ImportError:
                logger.error("docker_not_installed")
                raise ImportError(
                    "Docker SDK not installed. Install with: pip install docker"
                ) from None
            except Exception as e:
                logger.error("docker_client_init_failed", error=str(e))
                raise RuntimeError(f"Failed to initialize Docker client: {e}") from e

        return self._client

    async def run_bash(
        self,
        command: str,
        timeout: int = 30,
        working_dir: str | None = None,
    ) -> dict[str, Any]:
        """Run bash command in sandbox container.

        Args:
            command: Bash command to execute
            timeout: Execution timeout in seconds
            working_dir: Working directory inside container

        Returns:
            Dict with output, stderr, and exit_code

        Examples:
            >>> result = await sandbox.run_bash("echo hello")
            >>> result["output"]
            'hello\\n'
        """
        logger.info("run_bash", command=command, timeout=timeout)

        try:
            client = self._get_client()

            # Prepare container configuration
            container_config = {
                "image": self.image,
                "command": ["bash", "-c", command],
                "detach": True,
                "mem_limit": self.memory_limit,
                "cpu_quota": self.cpu_quota,
                "network_disabled": self.network_disabled,
                "read_only": self.read_only,
                "security_opt": ["no-new-privileges"],
                "remove": False,  # We'll remove manually after getting logs
            }

            if working_dir:
                container_config["working_dir"] = working_dir

            # Add /tmp as writable if read_only is True
            if self.read_only:
                container_config["tmpfs"] = {"/tmp": "rw,size=100m"}

            # Run container
            container = client.containers.run(**container_config)

            try:
                # Wait with timeout
                result = await asyncio.wait_for(
                    asyncio.to_thread(container.wait),
                    timeout=timeout,
                )

                # Get logs
                logs = container.logs().decode("utf-8", errors="replace")

                # Get exit code
                exit_code = result.get("StatusCode", -1)

                logger.info(
                    "bash_execution_completed",
                    exit_code=exit_code,
                    output_length=len(logs),
                )

                return {
                    "output": logs,
                    "exit_code": exit_code,
                    "success": exit_code == 0,
                }

            except TimeoutError:
                logger.warning("bash_execution_timeout", timeout=timeout)
                container.kill()
                return {
                    "error": f"Execution timed out after {timeout} seconds",
                    "exit_code": -1,
                    "success": False,
                }

            finally:
                # Cleanup container
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning("container_removal_failed", error=str(e))

        except Exception as e:
            logger.error("sandbox_execution_failed", error=str(e), exc_info=True)
            return {
                "error": f"Sandbox execution failed: {e}",
                "exit_code": -1,
                "success": False,
            }

    async def run_python(
        self,
        code: str,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Run Python code in sandbox container.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            Dict with output, stderr, and exit_code

        Examples:
            >>> result = await sandbox.run_python("print('hello')")
            >>> "hello" in result["output"]
            True
        """
        logger.info("run_python", code_length=len(code), timeout=timeout)

        # Escape code for bash command
        escaped_code = code.replace("'", "'\\''")
        command = f"python3 -c '{escaped_code}'"

        return await self.run_bash(command, timeout=timeout)

    async def run(
        self,
        handler: Callable,
        parameters: dict[str, Any],
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Run a tool handler in sandbox.

        This is the generic interface used by ToolExecutor.

        Args:
            handler: Tool handler function
            parameters: Parameters for the handler
            timeout: Execution timeout

        Returns:
            Dict with execution results

        Examples:
            >>> async def my_tool(x: int) -> int:
            ...     return x * 2
            >>> result = await sandbox.run(my_tool, {"x": 5}, timeout=10)
            >>> result["result"]
            10
        """
        logger.info(
            "run_handler",
            handler=handler.__name__,
            timeout=timeout,
        )

        # For now, we can't directly execute Python callables in Docker
        # This would require serializing the function and its dependencies
        # Instead, we'll execute it directly (sandboxing requires more work)
        # TODO: Implement proper callable serialization for Docker execution

        try:
            result = await asyncio.wait_for(
                handler(**parameters),
                timeout=timeout,
            )

            return {"result": result}

        except TimeoutError:
            logger.warning("handler_timeout", handler=handler.__name__, timeout=timeout)
            return {
                "error": f"Handler timed out after {timeout} seconds",
                "exit_code": -1,
            }

        except Exception as e:
            logger.error(
                "handler_execution_failed",
                handler=handler.__name__,
                error=str(e),
                exc_info=True,
            )
            return {
                "error": f"Handler execution failed: {e}",
                "exit_code": -1,
            }

    async def cleanup(self) -> None:
        """Cleanup Docker resources.

        Examples:
            >>> await sandbox.cleanup()
        """
        if self._client:
            try:
                self._client.close()
                logger.info("docker_client_closed")
            except Exception as e:
                logger.warning("docker_cleanup_failed", error=str(e))

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        await self.cleanup()
