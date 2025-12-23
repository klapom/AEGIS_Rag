"""Bash command security filters.

Sprint 59 Feature 59.3: Security validation for bash commands.

This module provides blacklist/whitelist filters to prevent execution
of dangerous bash commands.
"""

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SecurityCheckResult:
    """Result of security validation."""

    safe: bool
    reason: str | None = None


# Commands that should never be executed
COMMAND_BLACKLIST = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    ":(){:|:&};:",  # Fork bomb
    "chmod 777 /",
    "curl | bash",
    "wget | bash",
    "curl | sh",
    "wget | sh",
    "format",
    "fdisk",
    "parted",
]

# Regex patterns for dangerous command structures
DANGEROUS_PATTERNS = [
    r">\s*/dev/sd[a-z]",  # Writing to block devices
    r"rm\s+-rf\s+/[^/\s]",  # Dangerous rm on root subdirs
    r"\|\s*sh\s*$",  # Piping to shell
    r"\|\s*bash\s*$",  # Piping to bash
    r"eval\s+",  # Eval command
    r"exec\s+",  # Exec command
    r"sudo\s+",  # Sudo elevation
    r"su\s+",  # Su elevation
    r"chmod\s+777",  # Dangerous permissions
    r"chown\s+.*\s+/",  # Changing ownership of root
]

# Additional patterns for data exfiltration
EXFILTRATION_PATTERNS = [
    r"nc\s+",  # Netcat
    r"ncat\s+",  # Ncat
    r"telnet\s+",  # Telnet
    r"ftp\s+",  # FTP
    r"scp\s+",  # SCP
    r"rsync\s+",  # Rsync
    r"curl\s+.*-T",  # Curl upload
    r"wget\s+.*--post",  # Wget post
]


def is_command_safe(command: str) -> SecurityCheckResult:
    """Check if command is safe to execute.

    Args:
        command: The bash command to validate

    Returns:
        SecurityCheckResult with safe flag and reason if blocked

    Examples:
        >>> result = is_command_safe("ls -la")
        >>> result.safe
        True

        >>> result = is_command_safe("rm -rf /")
        >>> result.safe
        False
        >>> result.reason
        'Blocked command pattern: rm -rf /'
    """
    # Check exact blacklist matches
    for blocked in COMMAND_BLACKLIST:
        if blocked in command:
            logger.warning("blocked_command", command=command, pattern=blocked)
            return SecurityCheckResult(False, f"Blocked command pattern: {blocked}")

    # Check dangerous regex patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            logger.warning("dangerous_pattern", command=command, pattern=pattern)
            return SecurityCheckResult(False, f"Dangerous pattern detected: {pattern}")

    # Check exfiltration patterns
    for pattern in EXFILTRATION_PATTERNS:
        if re.search(pattern, command):
            logger.warning("exfiltration_pattern", command=command, pattern=pattern)
            return SecurityCheckResult(False, f"Potential data exfiltration pattern: {pattern}")

    return SecurityCheckResult(True, None)


def sanitize_environment() -> dict[str, str]:
    """Create sanitized environment variables for command execution.

    Returns:
        Dict of safe environment variables
    """
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "SHELL": "/bin/sh",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
    }


def get_allowed_commands() -> list[str]:
    """Get list of explicitly allowed safe commands.

    Returns:
        List of command names that are considered safe
    """
    return [
        # File operations (read-only)
        "ls",
        "cat",
        "head",
        "tail",
        "less",
        "more",
        "file",
        "stat",
        "wc",
        "grep",
        "find",
        "tree",
        # Text processing
        "sed",
        "awk",
        "cut",
        "sort",
        "uniq",
        "tr",
        "jq",
        # System info (read-only)
        "pwd",
        "whoami",
        "id",
        "date",
        "cal",
        "uptime",
        "df",
        "du",
        "free",
        "top",
        "ps",
        "env",
        "printenv",
        # Development tools
        "git",
        "python",
        "node",
        "npm",
        "pip",
        "poetry",
        "pytest",
        "black",
        "ruff",
        "mypy",
        # Archive operations
        "tar",
        "gzip",
        "gunzip",
        "zip",
        "unzip",
        # Other utilities
        "echo",
        "printf",
        "which",
        "type",
        "help",
    ]
