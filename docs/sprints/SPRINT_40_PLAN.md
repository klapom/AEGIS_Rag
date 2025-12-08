# Sprint 40: MCP Integration + Secure Shell Sandbox (v3)

**Status:** PLANNED
**Duration:** Nach Sprint 39
**Story Points:** 46 SP (29 MCP + 17 Shell Sandbox)
**Dependencies:** Sprint 38 (Auth), Sprint 39 (Bi-Temporal)
**ADRs:**
- [ADR-007: Model Context Protocol Client Integration](../adr/ADR_INDEX.md#adr-007)
- [ADR-043: Secure Shell Sandbox mit Bubblewrap + deepagents](../adr/ADR-043_SECURE_SHELL_SANDBOX.md)

---

## Sprint Objectives

### Kombinierter Ansatz: MCP + Shell Sandbox (v3)

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Sprint 40: Tool Execution Layer                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  MCP CLIENT (External Tools)                                 │   │
│  │  - Filesystem Server                                         │   │
│  │  - Web Fetch Server                                          │   │
│  │  - GitHub Server                                             │   │
│  │  - SQLite Server                                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  SECURE SHELL SANDBOX (Internal Tool) - v3                   │   │
│  │  - Bubblewrap process isolation (NOT Docker)                 │   │
│  │  - deepagents integration (Planning, Filesystem)             │   │
│  │  - Multi-Language: Bash + Python (Pyodide)                   │   │
│  │  - Exposed as MCP Tool: secure_shell:execute                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  MCP SERVER (AegisRAG als Tool-Provider)                     │   │
│  │  - search_knowledge                                          │   │
│  │  - query_graph                                               │   │
│  │  - secure_shell (NEU!)                                       │   │
│  │  - ingest_document                                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Primary Goals
1. **MCP Client Activation** - Connect to external MCP servers
2. **Secure Shell Sandbox (v3)** - Bubblewrap + deepagents integration
3. **Multi-Language CodeAct** - Bash + Python execution
4. **Tool Discovery UI** - Browse and manage available tools
5. **Progress Tracking** - Session-persistent analysis state

### v3 Improvements (vs v2)

| Bereich | v2 (Custom) | v3 (LangChain-Integration) |
|---------|-------------|---------------------------|
| Agent Harness | Eigene Implementierung | `deepagents` Package |
| Code Execution | Custom LangGraph Node | Multi-Language CodeAct |
| Bash Sandbox | Custom Docker | `BubblewrapSandboxBackend` |
| Python Sandbox | - | `langchain-sandbox` (Pyodide) |
| Progress Tracking | - | `aegis-progress.json` |
| **Story Points** | 19 SP | **17 SP** (-10%) |

### Why Combined Sprint?

| Synergie | Beschreibung |
|----------|--------------|
| **Shell als MCP Tool** | `secure_shell:execute` wird als MCP Tool exponiert |
| **Einheitliche Tool-Architektur** | Alle Tools (intern + extern) via MCP API |
| **Shared Audit Logging** | MCP und Shell teilen Audit-Trail |
| **Frontend Integration** | Ein Tool-Browser fur alles |

---

## Feature Overview

| Feature | Story Points | Priority | Status |
|---------|--------------|----------|--------|
| **MCP Features** | | | |
| 40.1: MCP Client Activation | 3 SP | P0 | Backend Ready |
| 40.2: Tool Discovery & Management | 5 SP | P1 | Partial |
| 40.3: Chat Tool Integration | 8 SP | P1 | New |
| 40.4: Tool Execution Panel | 5 SP | P1 | New |
| 40.5: AegisRAG as MCP Server | 5 SP | P2 | New |
| 40.6: MCP Server Configuration UI | 3 SP | P2 | New |
| **Shell Sandbox Features (v3)** | | | |
| 40.7: BubblewrapSandboxBackend | 5 SP | P0 | New |
| 40.8: deepagents Integration | 4 SP | P0 | New |
| 40.9: Multi-Language CodeAct | 3 SP | P1 | New |
| 40.10: Progress Tracking | 2 SP | P1 | New |
| 40.11: Observability & Audit | 3 SP | P1 | New |
| **Total** | **46 SP** | | |

---

## Epic 1: MCP Client Features (29 SP)

### Feature 40.1: MCP Client Activation (3 SP) - P0

```python
# src/components/mcp/client.py - ACTIVATE

from src.components.mcp.connection_manager import MCPConnectionManager

# Initialize connection manager
manager = MCPConnectionManager()

# Connect to filesystem server
await manager.connect_server(
    name="filesystem",
    command="npx @modelcontextprotocol/server-filesystem /data"
)

# Connect to web fetch server
await manager.connect_server(
    name="web",
    command="npx @anthropic/mcp-server-fetch"
)

# List available tools across all servers
tools = await manager.list_all_tools()
```

### Feature 40.2: Tool Discovery & Management (5 SP) - P1

**API Endpoints:**
```python
# src/api/v1/mcp.py

@router.get("/mcp/servers")
async def list_mcp_servers() -> list[MCPServerInfo]:
    """List configured MCP servers and their status."""

@router.post("/mcp/servers/{server_name}/connect")
async def connect_server(server_name: str) -> MCPConnectionResponse:
    """Connect to an MCP server."""

@router.get("/mcp/tools")
async def list_all_tools() -> list[MCPToolInfo]:
    """List all available tools across connected servers."""

@router.post("/mcp/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, request: ToolExecuteRequest) -> ToolExecuteResponse:
    """Execute an MCP tool."""
```

### Feature 40.3: Chat Tool Integration (8 SP) - P1

```
User: "Lies die Datei /data/reports/q4.pdf und fasse sie zusammen"
       |
       v
+-----------------------------------------+
| LLM selektiert Tool:                    |
| - Tool: filesystem:read_file            |
| - Arguments: {path: "/data/reports/..."}|
+-----------------------------------------+
       |
       v
+-----------------------------------------+
| Tool Execution Card im Chat:            |
| [Tool] Using tool: filesystem:read_file |
|    Path: /data/reports/q4.pdf           |
|    Status: Complete (2.3s)              |
+-----------------------------------------+
       |
       v
Response: "Basierend auf dem Q4-Bericht..."
```

### Feature 40.4: Tool Execution Panel (5 SP) - P1

**GUI: Tool Browser Modal**
```
+-----------------------------------------------------------------+
|  Browse Tools                                          [Close]   |
|-----------------------------------------------------------------|
|  Search: [________________________] [Search]                     |
|  Filter: [All Servers v]                                         |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  | [Folder] Filesystem Server (3 tools)                      |  |
|  | - read_file - Read file contents                          |  |
|  | - write_file - Write to file                              |  |
|  | - list_directory - List directory contents                |  |
|  +-----------------------------------------------------------+  |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  | [Terminal] Secure Shell (2 tools) - SANDBOX               |  |
|  | - execute_bash - Run bash in Bubblewrap sandbox           |  |
|  | - execute_python - Run Python in Pyodide sandbox          |  |
|  |   [!] Network disabled, read-only filesystem               |  |
|  +-----------------------------------------------------------+  |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  | [Globe] Web Fetch Server (1 tool)                         |  |
|  | - fetch_url - Fetch content from URL                      |  |
|  +-----------------------------------------------------------+  |
|                                                                  |
+-----------------------------------------------------------------+
```

### Feature 40.5: AegisRAG as MCP Server (5 SP) - P2

```python
# src/mcp_server/tools.py

MCP_TOOLS = [
    {
        "name": "search_knowledge",
        "description": "Search the knowledge base using hybrid retrieval",
        "inputSchema": {...}
    },
    {
        "name": "query_graph",
        "description": "Query the knowledge graph for entities",
        "inputSchema": {...}
    },
    {
        "name": "secure_shell",  # NEU!
        "description": "Execute shell commands in secure Bubblewrap sandbox",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "workspace": {"type": "string", "default": "/data"},
                "timeout": {"type": "integer", "default": 30},
                "language": {
                    "type": "string",
                    "enum": ["bash", "python"],
                    "default": "bash"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "ingest_document",
        "description": "Ingest document into knowledge base",
        "inputSchema": {...}
    }
]
```

**Usage from Claude Desktop:**
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "aegisrag": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "env": {"AEGISRAG_API_URL": "http://localhost:8000"}
    }
  }
}
```

### Feature 40.6: MCP Server Configuration UI (3 SP) - P2

**Admin Panel fur Server-Konfiguration**

---

## Epic 2: Secure Shell Sandbox v3 (17 SP)

### Feature 40.7: BubblewrapSandboxBackend (5 SP) - P0

**User Stories:**
| ID | Story | Akzeptanzkriterien |
|----|-------|-------------------|
| SM-01 | Als System implementiere ich `SandboxBackendProtocol` | Alle Interface-Methoden erfullt |
| SM-02 | Als System fuhre ich Commands in Bubblewrap-Sandbox aus | Prozess-Isolation verifiziert |
| SM-03 | Als System beschranke ich Filesystem auf definierte Pfade | Read-only Repo, tmpfs Workspace |
| SM-04 | Als System wende ich Seccomp-Profile an | Syscall-Whitelist aktiv |

**Implementation:**
```python
# src/components/sandbox/bubblewrap_backend.py

from deepagents.backends.protocol import (
    SandboxBackendProtocol,
    ExecuteResult,
    WriteResult,
    EditResult
)
import subprocess
from pathlib import Path

class BubblewrapSandboxBackend(SandboxBackendProtocol):
    """
    Sandbox Backend using Linux Bubblewrap for process isolation.
    Implements deepagents SandboxBackendProtocol.
    """

    def __init__(
        self,
        repo_path: str,
        workspace_path: str = "/tmp/aegis-workspace",
        timeout: int = 30,
        seccomp_profile: str | None = None,
        output_limit: int = 32768  # 32KB
    ):
        self.repo_path = Path(repo_path).resolve()
        self.workspace = Path(workspace_path)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.seccomp_profile = seccomp_profile
        self.output_limit = output_limit

    def _build_bwrap_command(self, command: str) -> list[str]:
        """Build bubblewrap command with security restrictions."""
        return [
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
            # Seccomp
            *(["--seccomp", self.seccomp_profile] if self.seccomp_profile else []),
            # Run command
            "--", "sh", "-c", command
        ]

    def execute(self, command: str) -> ExecuteResult:
        """Execute shell command in Bubblewrap sandbox."""
        try:
            result = subprocess.run(
                self._build_bwrap_command(command),
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return ExecuteResult(
                stdout=result.stdout[:self.output_limit],
                stderr=result.stderr[:self.output_limit],
                exit_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            return ExecuteResult(
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                exit_code=-1
            )

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file from sandbox filesystem."""
        result = self.execute(f"sed -n '{offset+1},{offset+limit}p' '{file_path}'")
        return result.stdout if result.exit_code == 0 else f"Error: {result.stderr}"

    def write(self, file_path: str, content: str) -> WriteResult:
        """Write file to workspace (only workspace is writable)."""
        if not file_path.startswith("/workspace"):
            return WriteResult(success=False, error="Writes only allowed in /workspace")
        # Implementation via heredoc
        ...

    def ls_info(self, path: str = "/repo") -> list[FileInfo]:
        """List directory contents."""
        result = self.execute(f"ls -la '{path}'")
        # Parse output to FileInfo
        ...

    def grep_raw(self, pattern: str, path: str = "/repo") -> list[GrepMatch]:
        """Search for pattern in files."""
        result = self.execute(f"grep -rn '{pattern}' '{path}'")
        # Parse to GrepMatch
        ...
```

### Feature 40.8: deepagents Integration (4 SP) - P0

**User Stories:**
| ID | Story | Akzeptanzkriterien |
|----|-------|-------------------|
| SM-05 | Als System erstelle ich Agent mit `create_deep_agent()` | Agent lauft mit Custom Backend |
| SM-06 | Als Agent nutze ich Planning via TodoListMiddleware | Todos werden erstellt/aktualisiert |
| SM-07 | Als Agent nutze ich Filesystem-Tools (read/write/grep) | Tools funktionieren uber Backend |
| SM-08 | Als System konfiguriere ich Human-in-the-Loop | Gefahrliche Commands erfordern Approval |

**Agent Configuration:**
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

    # Python Backend (Pyodide)
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
```

### Feature 40.9: Multi-Language CodeAct (3 SP) - P1

**User Stories:**
| ID | Story | Akzeptanzkriterien |
|----|-------|-------------------|
| SM-09 | Als Agent kann ich mehrzeilige Bash-Skripte ausfuhren | Bubblewrap-Sandbox, Skript-Execution |
| SM-10 | Als Agent kann ich Python-Code ausfuhren | Pyodide-Sandbox, State Persistence |
| SM-11 | Als Agent kann ich Dateien zwischen Sandboxes teilen | Shared Workspace funktional |
| SM-12 | Als Agent wahle ich die passende Sprache fur den Task | Automatische Sprachauswahl |

**Architecture:**
```
+-------------------------------------------+
|            deepagents Agent                |
|  +-------------------------------------+   |
|  |     CompositeBackend                |   |
|  |  +-----------+---------------+      |   |
|  |  | /bash/*   | /python/*     |      |   |
|  |  | Bubblewrap| Pyodide       |      |   |
|  |  | Sandbox   | Sandbox       |      |   |
|  |  +-----------+---------------+      |   |
|  |         ^           ^               |   |
|  |         +-----+-----+               |   |
|  |        Shared Workspace             |   |
|  +-------------------------------------+   |
+-------------------------------------------+
```

**Use Cases nach Sprache:**

| Bash | Python |
|------|--------|
| `find . -name "*.py"` | DataFrame-Analyse |
| `grep -r "TODO"` | JSON/YAML Parsing |
| `git log --oneline` | Embedding-Generierung |
| `wc -l src/**/*.py` | Entity Extraction |
| `tree -L 2` | Knowledge Graph Ops |

### Feature 40.10: Progress Tracking (2 SP) - P1

**User Stories:**
| ID | Story | Akzeptanzkriterien |
|----|-------|-------------------|
| SM-13 | Als Agent tracke ich Analyse-Fortschritt uber Sessions | Progress JSON aktualisiert |
| SM-14 | Als Agent lese ich beim Start den Progress-Status | Startup liest Status |

**Progress File Schema:**
```json
{
    "repo": "/path/to/analyzed/repo",
    "status": "in_progress",
    "started_at": "2025-12-08T10:00:00Z",
    "analyzed_paths": [
        "src/components/",
        "src/agents/"
    ],
    "pending_paths": [
        "src/api/",
        "tests/"
    ],
    "entities_extracted": 42,
    "sessions": [
        {
            "session_id": "abc123",
            "timestamp": "2025-12-08T10:00:00Z",
            "action": "started",
            "files_processed": 15
        },
        {
            "session_id": "abc123",
            "timestamp": "2025-12-08T10:30:00Z",
            "action": "paused",
            "files_processed": 28
        }
    ],
    "next_steps": [
        "Continue with src/api/ directory",
        "Extract API endpoint entities"
    ]
}
```

**System Prompt Extension:**
```
## Session Management
At the START of each session:
1. Read /workspace/aegis-progress.json if it exists
2. Report current analysis status to user
3. Continue from where the last session stopped

At the END of each session (or when interrupted):
1. Update /workspace/aegis-progress.json with your progress
2. Document analyzed paths, extracted entities, and next steps
3. Set status to "completed" only when ALL paths are analyzed
```

### Feature 40.11: Observability & Audit (3 SP) - P1

**User Stories:**
| ID | Story | Akzeptanzkriterien |
|----|-------|-------------------|
| SM-15 | Als Operator logge ich alle Ausfuhrungen | Timestamp, Command/Code, Language, Output-Hash |
| SM-16 | Als System beende ich Commands nach Timeout | Konfigurierbarer Timeout, SIGKILL |
| SM-17 | Als System truncatiere ich grosse Outputs | Max 32KB, Truncation-Marker |

**Audit Logging:**
```python
# Alle Shell-Aufrufe werden geloggt
logger.info(
    "sandbox_execution",
    event_type="shell_command",
    timestamp=datetime.utcnow().isoformat(),
    user_id=user_context.get("user_id"),
    session_id=user_context.get("session_id"),
    language="bash",  # oder "python"
    command=command[:200],  # Truncate for log
    command_hash=hashlib.sha256(command.encode()).hexdigest(),
    workspace=workspace_path,
    exit_code=result.exit_code,
    duration_ms=result.duration_ms,
    output_bytes=len(result.stdout),
    truncated=result.truncated
)
```

**Suspicious Pattern Detection:**
```python
SUSPICIOUS_PATTERNS = [
    r"curl.*\|.*sh",      # Pipe to shell
    r"wget.*-O.*\|",       # Download and execute
    r"base64.*-d",         # Decode obfuscated
    r"eval\s*\(",          # Dynamic eval
    r"/dev/(tcp|udp)/",    # Network via /dev
]

def check_suspicious(command: str) -> list[str]:
    """Check command against suspicious patterns."""
    matches = []
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            matches.append(pattern)
    return matches
```

---

## GUI Components

### Tool Execution Card (Chat)

```typescript
// frontend/src/components/chat/ToolExecutionCard.tsx

export function ToolExecutionCard({ execution }: { execution: ToolExecution }) {
  const isShellTool = execution.server === 'secure_shell';
  const language = execution.arguments?.language || 'bash';

  return (
    <div
      className={`rounded-lg p-3 mb-3 border ${
        execution.status === 'error' ? 'bg-red-50 border-red-200' :
        execution.status === 'complete' ? 'bg-green-50 border-green-200' :
        'bg-blue-50 border-blue-200'
      }`}
      data-testid="tool-execution-card"
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">
          {execution.status === 'running' ? '...' :
           execution.status === 'complete' ? '[OK]' :
           execution.status === 'error' ? '[X]' :
           isShellTool ? '[>_]' : '[Tool]'}
        </span>
        <span className="font-medium">
          {isShellTool
            ? `Secure Shell (${language})`
            : `Tool: ${execution.server}:${execution.toolName}`}
        </span>
        {isShellTool && (
          <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded text-xs">
            Bubblewrap Sandbox
          </span>
        )}
      </div>

      {/* Command/Arguments */}
      <div className="text-sm text-gray-600 mt-2 ml-7 font-mono bg-gray-100 p-2 rounded">
        {isShellTool ? (
          <code>$ {execution.arguments.command}</code>
        ) : (
          Object.entries(execution.arguments).map(([k, v]) => (
            <div key={k}>{k}: {String(v).substring(0, 50)}</div>
          ))
        )}
      </div>

      {/* Status */}
      <div className="text-sm text-gray-500 mt-1 ml-7">
        Status: {execution.status}
        {execution.duration && ` (${(execution.duration / 1000).toFixed(1)}s)`}
        {execution.truncated && (
          <span className="text-amber-600 ml-2">[!] Output truncated</span>
        )}
      </div>
    </div>
  );
}
```

### MCP Server Management (Admin)

```
+-----------------------------------------------------------------+
|  Admin > Tool Servers                                            |
|-----------------------------------------------------------------|
|                                                                  |
|  Internal Tools                                                  |
|  +-----------------------------------------------------------+  |
|  | [>_] Secure Shell (v3)                       [Active]     |  |
|  |   Bubblewrap sandbox with deepagents integration          |  |
|  |   Languages: Bash, Python (Pyodide)                       |  |
|  |   Security: Network disabled, read-only FS, seccomp       |  |
|  |   Limits: 30s timeout, 32KB output                        |  |
|  |                                                           |  |
|  |   [Configure Limits] [View Audit Log] [View Progress]     |  |
|  +-----------------------------------------------------------+  |
|                                                                  |
|  External MCP Servers                         [+ Add Server]     |
|  +-----------------------------------------------------------+  |
|  | [*] Filesystem                              [Connected]   |  |
|  |   Tools: read_file, write_file, list_directory            |  |
|  |   [Disconnect] [View Tools]                               |  |
|  +-----------------------------------------------------------+  |
|  +-----------------------------------------------------------+  |
|  | [*] Web Fetch                               [Connected]   |  |
|  |   Tools: fetch_url                                        |  |
|  |   [Disconnect] [View Tools]                               |  |
|  +-----------------------------------------------------------+  |
|  +-----------------------------------------------------------+  |
|  | [ ] GitHub                                 [Disconnected] |  |
|  |   Requires: GITHUB_TOKEN                                  |  |
|  |   [Connect] [Configure]                                   |  |
|  +-----------------------------------------------------------+  |
|                                                                  |
+-----------------------------------------------------------------+
```

---

## Acceptance Criteria

### MCP Features (40.1-40.6)
- [ ] MCP servers connectable via Admin UI
- [ ] Tool discovery lists all tools (internal + external)
- [ ] LLM can select and execute MCP tools
- [ ] Tool execution shown in chat UI
- [ ] AegisRAG exposes tools via MCP protocol
- [ ] Works with Claude Desktop

### Shell Sandbox Features v3 (40.7-40.11)
- [ ] BubblewrapSandboxBackend erfullt SandboxBackendProtocol
- [ ] Agent lauft mit deepagents auf DGX Spark
- [ ] Bubblewrap Overhead <100ms (vs Docker 200-400ms)
- [ ] Keine Netzwerkverbindung moglich (--unshare-net)
- [ ] Filesystem ist read-only (except /workspace)
- [ ] Timeout funktioniert (SIGKILL after grace)
- [ ] Output wird bei 32KB truncated
- [ ] Multi-Language: Bash + Python funktional
- [ ] Shared Workspace zwischen Sandboxes
- [ ] Progress Tracking uber Sessions
- [ ] Alle Ausfuhrungen im Audit-Log
- [ ] Seccomp blockiert gefahrliche Syscalls
- [ ] LLM-Wechsel funktioniert (Claude <-> OpenAI <-> Ollama)
- [ ] Security-Tests bestanden (kein Sandbox-Escape)

---

## Test Plan

### Unit Tests (25 tests)
- [ ] BubblewrapSandboxBackend Protocol-Compliance
- [ ] MCP Client connection/disconnection
- [ ] Tool discovery and listing
- [ ] Tool execution with mock responses
- [ ] Output truncation
- [ ] Command validation (blocklist)
- [ ] Progress file read/write

### Integration Tests (15 tests)
- [ ] MCP server communication
- [ ] Shell sandbox with real Bubblewrap
- [ ] Python sandbox with Pyodide
- [ ] Shared workspace file exchange
- [ ] Timeout enforcement
- [ ] deepagents integration
- [ ] Read-only filesystem verification

### Security Tests (10 tests)
- [ ] Network isolation (no egress)
- [ ] Path traversal prevention
- [ ] Privilege escalation prevention
- [ ] Sandbox escape attempts
- [ ] Seccomp syscall blocking
- [ ] Fork bomb handling

### E2E Tests (10 tests)
- [ ] Tool Browser UI
- [ ] Tool execution in chat
- [ ] Admin server management
- [ ] Progress status display
- [ ] Audit log viewing
- [ ] Error handling UI

---

## Dependencies

```toml
# pyproject.toml additions for Sprint 40
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
- Node.js for MCP servers (npx)

---

## Risiken & Mitigations

| Risiko | Impact | Mitigation |
|--------|--------|------------|
| ARM64-Kompatibilitat (Bubblewrap) | Medium | Fruhzeitig auf DGX Spark testen |
| deepagents API-Anderungen | Low | Version pinnen, Changelog monitoren |
| Seccomp blockiert benotigte Syscalls | Medium | Iteratives Profiling mit strace |
| Pyodide Package-Limitierung | Low | Core-Packages verfugbar, Rest via Bash |
| MCP Server Instabilitat | Low | Reconnection Logic, Fallback |

---

## Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Bubblewrap Process Start | <100ms | subprocess timing |
| Pyodide Sandbox Start | <500ms | Cold start |
| Command Execution | Native | ~0ms overhead |
| MCP Tool Execution | <100ms overhead | Network latency |
| Tool Discovery | <500ms | API response time |
| **Total Sandbox Overhead** | **<200ms** | End-to-end |

---

## Related Documents

- [ADR-007: Model Context Protocol Client Integration](../adr/ADR_INDEX.md#adr-007)
- [ADR-043: Secure Shell Sandbox mit Bubblewrap + deepagents](../adr/ADR-043_SECURE_SHELL_SANDBOX.md)
- `src/components/mcp/client.py` - MCP Client (ready)
- `src/components/mcp/connection_manager.py` - Connection Manager (ready)
- [deepagents GitHub](https://github.com/langchain-ai/deepagents)
- [langgraph-codeact GitHub](https://github.com/langchain-ai/langgraph-codeact)
- [Bubblewrap GitHub](https://github.com/containers/bubblewrap)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Anthropic: Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
