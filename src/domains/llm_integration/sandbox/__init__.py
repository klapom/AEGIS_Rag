"""Sandboxing Layer for LLM Tool Execution.

Sprint 59 Feature 59.5: Isolated execution environment for tools.

This package provides multiple levels of sandboxing:
- Docker container-based isolation (strongest)
- Process-level isolation with resource limits
- Network restrictions

Usage:
    from src.domains.llm_integration.sandbox import get_sandbox

    sandbox = await get_sandbox()
    result = await sandbox.run(command, timeout=30)
"""

from src.domains.llm_integration.sandbox.container import DockerSandbox
from src.domains.llm_integration.sandbox.resource_limits import (
    ResourceLimits,
    apply_limits,
)

__all__ = [
    "DockerSandbox",
    "ResourceLimits",
    "apply_limits",
    "get_sandbox",
]


_sandbox_instance: DockerSandbox | None = None


async def get_sandbox(
    use_docker: bool = True,
    **kwargs,
) -> DockerSandbox:
    """Get singleton sandbox instance.

    Args:
        use_docker: Use Docker-based sandbox (default: True)
        **kwargs: Additional sandbox configuration

    Returns:
        Configured sandbox instance

    Examples:
        >>> sandbox = await get_sandbox()
        >>> result = await sandbox.run_bash("ls -la")
        >>> result["exit_code"]
        0
    """
    global _sandbox_instance

    if _sandbox_instance is None:
        if use_docker:
            _sandbox_instance = DockerSandbox(**kwargs)
        else:
            # For now, always use Docker
            # Process-level sandbox can be added later
            _sandbox_instance = DockerSandbox(**kwargs)

    return _sandbox_instance
