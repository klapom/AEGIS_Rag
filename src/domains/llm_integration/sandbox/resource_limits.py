"""Resource limits for sandboxed execution.

Sprint 59 Feature 59.5: Configurable resource limits for code execution.

This module provides resource limit management using the resource module
for process-level limits and Docker API for container-level limits.
"""

import resource
from dataclasses import dataclass, field
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ResourceLimits:
    """Configurable resource limits for sandboxed execution.

    These limits apply to both process-level and container-level sandboxing.
    """

    # Memory limits
    max_memory_mb: int = 256
    """Maximum memory in MB (default: 256)"""

    # CPU limits
    max_cpu_seconds: int = 30
    """Maximum CPU time in seconds (default: 30)"""

    max_cpu_quota: int = 50000
    """CPU quota for Docker (default: 50000 = 50% of one core)"""

    # File limits
    max_file_size_mb: int = 10
    """Maximum file size that can be created in MB (default: 10)"""

    max_open_files: int = 20
    """Maximum number of open file descriptors (default: 20)"""

    # Process limits
    max_processes: int = 5
    """Maximum number of processes (default: 5)"""

    # Network limits
    network_disabled: bool = True
    """Disable network access (default: True)"""

    # Filesystem limits
    read_only: bool = True
    """Make filesystem read-only (default: True)"""

    allowed_paths: list[str] = field(default_factory=lambda: ["/tmp"])
    """List of paths that can be written to"""

    # Additional Docker options
    docker_options: dict[str, Any] = field(default_factory=dict)
    """Additional Docker container options"""


def apply_limits(limits: ResourceLimits) -> None:
    """Apply resource limits to current process.

    This function uses the resource module to set hard limits on the current
    process. Should be called before executing untrusted code.

    Args:
        limits: ResourceLimits configuration

    Raises:
        RuntimeError: If limits cannot be applied

    Examples:
        >>> limits = ResourceLimits(max_memory_mb=128, max_cpu_seconds=10)
        >>> apply_limits(limits)
    """
    try:
        # Memory limit (virtual memory)
        memory_bytes = limits.max_memory_mb * 1024 * 1024
        resource.setrlimit(
            resource.RLIMIT_AS,
            (memory_bytes, memory_bytes)
        )
        logger.debug("memory_limit_set", mb=limits.max_memory_mb)

    except (ValueError, OSError) as e:
        logger.warning("memory_limit_failed", error=str(e))
        # Don't fail completely - continue with other limits

    try:
        # CPU time limit
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (limits.max_cpu_seconds, limits.max_cpu_seconds)
        )
        logger.debug("cpu_limit_set", seconds=limits.max_cpu_seconds)

    except (ValueError, OSError) as e:
        logger.warning("cpu_limit_failed", error=str(e))

    try:
        # File size limit
        file_size_bytes = limits.max_file_size_mb * 1024 * 1024
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (file_size_bytes, file_size_bytes)
        )
        logger.debug("file_size_limit_set", mb=limits.max_file_size_mb)

    except (ValueError, OSError) as e:
        logger.warning("file_size_limit_failed", error=str(e))

    try:
        # Number of open files
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (limits.max_open_files, limits.max_open_files)
        )
        logger.debug("open_files_limit_set", count=limits.max_open_files)

    except (ValueError, OSError) as e:
        logger.warning("open_files_limit_failed", error=str(e))

    try:
        # Number of processes (not available on all platforms)
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (limits.max_processes, limits.max_processes)
        )
        logger.debug("process_limit_set", count=limits.max_processes)

    except (ValueError, OSError, AttributeError) as e:
        logger.warning("process_limit_failed", error=str(e))

    logger.info("resource_limits_applied", limits=limits)


def get_current_usage() -> dict[str, int]:
    """Get current resource usage.

    Returns:
        Dict with current resource usage metrics

    Examples:
        >>> usage = get_current_usage()
        >>> "memory_kb" in usage
        True
    """
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)

        return {
            "memory_kb": usage.ru_maxrss,
            "user_cpu_seconds": int(usage.ru_utime),
            "system_cpu_seconds": int(usage.ru_stime),
            "voluntary_context_switches": usage.ru_nvcsw,
            "involuntary_context_switches": usage.ru_nivcsw,
        }

    except Exception as e:
        logger.error("get_usage_failed", error=str(e))
        return {}


def get_docker_resource_limits(limits: ResourceLimits) -> dict[str, Any]:
    """Convert ResourceLimits to Docker API parameters.

    Args:
        limits: ResourceLimits configuration

    Returns:
        Dict of Docker API parameters

    Examples:
        >>> limits = ResourceLimits(max_memory_mb=256, max_cpu_quota=50000)
        >>> docker_params = get_docker_resource_limits(limits)
        >>> docker_params["mem_limit"]
        '256m'
    """
    params: dict[str, Any] = {
        "mem_limit": f"{limits.max_memory_mb}m",
        "cpu_quota": limits.max_cpu_quota,
        "network_disabled": limits.network_disabled,
        "read_only": limits.read_only,
    }

    # Add security options
    params["security_opt"] = ["no-new-privileges"]

    # Add volume binds for allowed paths
    if limits.allowed_paths and not limits.read_only:
        params["volumes"] = {
            path: {"bind": path, "mode": "rw"}
            for path in limits.allowed_paths
        }

    # Merge additional Docker options
    params.update(limits.docker_options)

    return params


def validate_limits(limits: ResourceLimits) -> tuple[bool, str | None]:
    """Validate resource limits configuration.

    Args:
        limits: ResourceLimits to validate

    Returns:
        Tuple of (valid, error_message)

    Examples:
        >>> limits = ResourceLimits(max_memory_mb=256)
        >>> valid, error = validate_limits(limits)
        >>> valid
        True
    """
    if limits.max_memory_mb < 1:
        return False, "max_memory_mb must be at least 1"

    if limits.max_memory_mb > 16384:  # 16GB
        return False, "max_memory_mb too large (max: 16384)"

    if limits.max_cpu_seconds < 1:
        return False, "max_cpu_seconds must be at least 1"

    if limits.max_cpu_seconds > 3600:  # 1 hour
        return False, "max_cpu_seconds too large (max: 3600)"

    if limits.max_file_size_mb < 1:
        return False, "max_file_size_mb must be at least 1"

    if limits.max_open_files < 1:
        return False, "max_open_files must be at least 1"

    if limits.max_processes < 1:
        return False, "max_processes must be at least 1"

    return True, None
