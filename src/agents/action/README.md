# BubblewrapSandboxBackend - Secure Code Execution

**Sprint 67 Feature 67.1: BubblewrapSandboxBackend**

Secure command execution sandbox using Linux Bubblewrap for process isolation.

## Overview

`BubblewrapSandboxBackend` provides a secure environment for executing untrusted code with multiple layers of security:

1. **Filesystem Isolation**: Read-only repository + isolated tmpfs workspace
2. **Network Isolation**: Unshare network namespace (no network access)
3. **Syscall Filtering**: Optional seccomp profile for syscall whitelisting
4. **Resource Limits**: Timeout enforcement, output truncation

## Installation

### Prerequisites

Install bubblewrap on your system:

```bash
# Ubuntu/Debian
sudo apt-get install bubblewrap

# Fedora/RHEL
sudo dnf install bubblewrap

# Arch Linux
sudo pacman -S bubblewrap
```

### Python Dependencies

```bash
poetry add deepagents>=0.2.0
```

## Usage

### Basic Example

```python
from src.agents.action.bubblewrap_backend import BubblewrapSandboxBackend

# Initialize sandbox
backend = BubblewrapSandboxBackend(
    repo_path="/path/to/repository",
    workspace_path="/tmp/aegis-workspace",
    timeout=30,
)

# Execute command
result = await backend.execute("ls -la /repo")

if result.success:
    print(result.stdout)
else:
    print(f"Error: {result.stderr}")
    print(f"Exit code: {result.exit_code}")
```

### File Operations

```python
# Write file to workspace
write_result = await backend.write_file("output.txt", "Hello, World!")

if write_result.success:
    print(f"File written: {write_result.path} ({write_result.size} bytes)")

# Read file from workspace or repo
content = await backend.read_file("output.txt")
print(content)

# Cleanup workspace
await backend.cleanup()
```

### With Seccomp Profile

```python
backend = BubblewrapSandboxBackend(
    repo_path="/path/to/repository",
    seccomp_profile="/path/to/seccomp_profile.json",
)
```

## Security Features

### Filesystem Isolation

The sandbox provides two filesystem areas:

- **Repository (Read-Only)**: Mounted at `/repo`, contains analyzed code
- **Workspace (Read-Write)**: Mounted at `/workspace`, tmpfs for temporary files

System directories (`/usr`, `/lib`, `/bin`) are mounted read-only.

### Network Isolation

Network access is completely disabled via `--unshare-net`. This prevents:
- Outbound HTTP/HTTPS requests
- DNS lookups
- Socket connections
- Data exfiltration

### Timeout Enforcement

Commands are terminated after the configured timeout (default: 30 seconds):

```python
backend = BubblewrapSandboxBackend(
    repo_path="/path/to/repo",
    timeout=60,  # 60 seconds
)
```

### Output Truncation

Output is limited to 32KB to prevent memory exhaustion:

```python
# Large outputs are automatically truncated
result = await backend.execute("cat /dev/urandom | head -c 100000")
assert result.truncated
```

### Path Traversal Protection

Attempts to access files outside allowed directories are blocked:

```python
# Blocked: Path traversal
result = await backend.write_file("../../../etc/passwd", "malicious")
assert not result.success
assert "path traversal" in result.error.lower()
```

## API Reference

### BubblewrapSandboxBackend

#### `__init__(repo_path, allowed_domains=None, timeout=30, seccomp_profile=None, workspace_path=None)`

Initialize sandbox backend.

**Parameters:**
- `repo_path` (str): Path to repository (mounted read-only)
- `allowed_domains` (list[str], optional): List of allowed network domains (currently unused)
- `timeout` (int, optional): Command timeout in seconds (default: 30)
- `seccomp_profile` (str, optional): Path to seccomp profile JSON
- `workspace_path` (str, optional): Custom workspace path (default: `/tmp/aegis-workspace`)

**Raises:**
- `ValueError`: If repo_path doesn't exist
- `FileNotFoundError`: If bubblewrap binary not found

#### `async execute(command, working_dir=None) -> ExecuteResult`

Execute command in sandbox.

**Parameters:**
- `command` (str): Shell command to execute
- `working_dir` (str, optional): Working directory (default: `/workspace`)

**Returns:**
- `ExecuteResult`: Result with stdout, stderr, exit code

#### `async write_file(path, content) -> WriteResult`

Write file to workspace.

**Parameters:**
- `path` (str): Relative path in workspace
- `content` (str): File content

**Returns:**
- `WriteResult`: Result with path, size, success status

#### `async read_file(path) -> str`

Read file from workspace or repo.

**Parameters:**
- `path` (str): Relative path

**Returns:**
- `str`: File content

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `ValueError`: If path attempts to escape allowed directories

#### `async cleanup() -> None`

Clean up workspace directory (removes all files).

### ExecuteResult

Result from command execution.

**Attributes:**
- `stdout` (str): Standard output
- `stderr` (str): Standard error
- `exit_code` (int): Command exit code
- `timed_out` (bool): Whether command timed out
- `truncated` (bool): Whether output was truncated

**Properties:**
- `success` (bool): True if exit_code == 0 and not timed_out

### WriteResult

Result from file write operation.

**Attributes:**
- `path` (str): File path
- `size` (int): File size in bytes
- `success` (bool): Whether write succeeded
- `error` (str | None): Error message if failed

## Seccomp Profile

The seccomp profile (`seccomp_profile.json`) defines which syscalls are allowed:

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": [
    "SCMP_ARCH_X86_64",
    "SCMP_ARCH_AARCH64"
  ],
  "syscalls": [
    {
      "names": ["read", "write", "open", ...],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

**Default Action**: Block all syscalls not in whitelist
**Allowed Syscalls**: Essential syscalls for process execution, filesystem I/O, memory management

## Testing

Run unit tests:

```bash
# Run all tests
poetry run pytest tests/unit/agents/action/ -v

# Run with coverage
poetry run pytest tests/unit/agents/action/ --cov=src/agents/action --cov-report=term-missing

# Run integration tests (requires bubblewrap)
poetry run pytest tests/unit/agents/action/ -v -m "not skipif"
```

**Test Coverage**: 89% (exceeds requirement of 80%)

## Performance

- **Overhead**: ~5-10ms per command (bubblewrap startup)
- **Timeout**: Default 30s, configurable
- **Output Limit**: 32KB (prevents memory exhaustion)

## Limitations

- **No Network Access**: Completely isolated (cannot make HTTP requests)
- **Linux Only**: Requires Linux kernel namespaces
- **ARM64/x86_64 Only**: Seccomp profile supports these architectures
- **No GPU Access**: Cannot access CUDA/GPU devices

## Future Enhancements

1. **Network Proxy**: Egress proxy for allowed domains
2. **Resource Quotas**: CPU, memory limits via cgroups
3. **Multi-Language**: Python sandbox integration (Pyodide)
4. **Audit Logging**: Detailed syscall tracing
5. **Container Support**: Docker/Podman backend alternative

## References

- [Bubblewrap Documentation](https://github.com/containers/bubblewrap)
- [Seccomp Documentation](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html)
- [deepagents GitHub](https://github.com/langchain-ai/deepagents)
- [Sprint 67 Plan](../../../docs/sprints/SPRINT_67_PLAN.md)

## License

MIT License - See project LICENSE file for details.
