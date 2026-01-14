# Sprint: Secure Shell Sandbox für AegisRAG v3

## Sprint-Ziel

Sichere, token-effiziente Ausführungsumgebung für Shell-Befehle im Agentic RAG System, basierend auf LangChain/LangGraph-Ökosystem mit Custom Bubblewrap-Sandbox.

---

## Änderungen gegenüber v2

| Bereich | v2 (Custom) | v3 (LangChain-Integration) |
|---------|-------------|---------------------------|
| Agent Harness | Eigene Implementierung | `deepagents` Package |
| Code Execution | Custom LangGraph Node | Multi-Language CodeAct |
| Bash Sandbox | Custom Docker | `BubblewrapSandboxBackend` |
| Python Sandbox | – | `langchain-sandbox` (Pyodide) |
| Backend-Abstraktion | Eigene Interfaces | `deepagents` BackendProtocol |
| Planning | Custom | `deepagents` TodoListMiddleware |
| Human-in-the-Loop | Custom | `deepagents` interrupt_on |
| Progress Tracking | – | `aegis-progress.json` |
| **Story Points** | 29 SP | **17 SP** |

---

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    AegisRAG Agent                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              deepagents.create_deep_agent()           │  │
│  │  - TodoListMiddleware (Planning)                      │  │
│  │  - FilesystemMiddleware                               │  │
│  │  - Custom AegisMiddleware                             │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           BubblewrapSandboxBackend                    │  │
│  │  implements: SandboxBackendProtocol                   │  │
│  │  - execute(command) → stdout/stderr                   │  │
│  │  - read/write/edit/ls/grep                            │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                 Bubblewrap Sandbox                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Filesystem: read-only repo mount + tmpfs workspace │    │
│  │  Network: Unix Socket → Egress Proxy                │    │
│  │  Seccomp: ~40 Syscalls whitelisted                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Technologie-Stack

| Komponente | Package | Version | Zweck |
|------------|---------|---------|-------|
| Agent Harness | `deepagents` | ≥0.2 | Planning, Filesystem, Subagents |
| Code Execution | `langgraph-codeact` | ≥0.1.3 | Script statt einzelne Commands |
| Runtime | `langgraph` | ≥0.4.5 | Graph-basierte Orchestrierung |
| LLM Abstraction | `langchain` | ≥0.3.20 | Multi-Provider Support |
| Sandbox | Bubblewrap | OS-Level | Prozess-Isolation |

---

## Architektur-Entscheidungen

### ADR-01: deepagents als Agent Harness

**Kontext:** deepagents implementiert bereits Planning, Filesystem, Subagents.

**Entscheidung:** deepagents als Basis verwenden, Custom Backend implementieren.

**Begründung:**
- Reduziert Implementierungsaufwand um ~50%
- Battle-tested (Claude Code inspiriert)
- LLM-agnostisch (OpenAI, Anthropic, Ollama)
- Aktiv maintained (v0.2 Nov 2025)

### ADR-02: Custom BubblewrapSandboxBackend

**Kontext:** deepagents unterstützt Remote Sandboxes (Runloop, Daytona, Modal), aber keine lokale Bubblewrap-Integration.

**Entscheidung:** Eigenes Backend implementieren, das `SandboxBackendProtocol` erfüllt.

**Begründung:**
- Lokale Ausführung auf DGX Spark (kein Cloud-Dependency)
- Volle Kontrolle über Security-Konfiguration
- Kein Vendor Lock-in

### ADR-03: Multi-Language CodeAct (Bash + Python)

**Kontext:** langgraph-codeact ist für Python optimiert. AegisRAG benötigt sowohl Shell-Commands (Repo-Navigation) als auch Python (Datenverarbeitung).

**Entscheidung:** Bash-Execution als zusätzliches Tool neben Python-Execution implementieren.

**Begründung:**
- Bash optimal für Filesystem-Operationen (grep, find, tree, git)
- Python optimal für Datenverarbeitung (pandas, Embeddings, JSON/YAML)
- Agent wählt situativ die passende Sprache
- Beide Sandboxes teilen Workspace (Dateien übergeben)
- State Persistence in beiden Umgebungen

**Architektur:**
```
┌─────────────────────────────────────────┐
│            deepagents Agent             │
│  ┌─────────────────────────────────┐    │
│  │     CompositeBackend            │    │
│  │  ┌───────────┬───────────────┐  │    │
│  │  │ /bash/*   │ /python/*     │  │    │
│  │  │ Bubblewrap│ Pyodide       │  │    │
│  │  │ Sandbox   │ Sandbox       │  │    │
│  │  └───────────┴───────────────┘  │    │
│  │         ▲           ▲           │    │
│  │         └─────┬─────┘           │    │
│  │        Shared Workspace         │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**Use Cases nach Sprache:**

| Bash | Python |
|------|--------|
| `find . -name "*.py"` | DataFrame-Analyse |
| `grep -r "TODO"` | JSON/YAML Parsing |
| `git log --oneline` | Embedding-Generierung |
| `wc -l src/**/*.py` | Entity Extraction |
| `tree -L 2` | Knowledge Graph Ops |

---

## Epics & User Stories

### Epic 1: BubblewrapSandboxBackend (Kern)

| ID | User Story | Akzeptanzkriterien |
|----|------------|-------------------|
| SM-01 | Als System implementiere ich `SandboxBackendProtocol` | Alle Interface-Methoden erfüllt |
| SM-02 | Als System führe ich Commands in Bubblewrap-Sandbox aus | Prozess-Isolation verifiziert |
| SM-03 | Als System beschränke ich Filesystem auf definierte Pfade | Read-only Repo, tmpfs Workspace |
| SM-04 | Als System route ich Netzwerk durch Egress-Proxy | Domain-Allowlist funktional |
| SM-05 | Als System wende ich Seccomp-Profile an | Syscall-Whitelist aktiv |

### Epic 2: deepagents Integration

| ID | User Story | Akzeptanzkriterien |
|----|------------|-------------------|
| SM-06 | Als System erstelle ich Agent mit `create_deep_agent()` | Agent läuft mit Custom Backend |
| SM-07 | Als Agent nutze ich Planning via TodoListMiddleware | Todos werden erstellt/aktualisiert |
| SM-08 | Als Agent nutze ich Filesystem-Tools (read/write/grep) | Tools funktionieren über Backend |
| SM-09 | Als System konfiguriere ich Human-in-the-Loop | Gefährliche Commands erfordern Approval |
| SM-09b | Als Agent tracke ich Analyse-Fortschritt über Sessions | Progress JSON aktualisiert, Startup liest Status |

### Epic 3: Multi-Language CodeAct

| ID | User Story | Akzeptanzkriterien |
|----|------------|-------------------|
| SM-10 | Als Agent kann ich mehrzeilige Bash-Skripte ausführen | Bubblewrap-Sandbox, Skript-Execution |
| SM-11 | Als Agent kann ich Python-Code ausführen | Pyodide-Sandbox, State Persistence |
| SM-12 | Als Agent kann ich Dateien zwischen Sandboxes teilen | Shared Workspace funktional |
| SM-13 | Als Agent wähle ich die passende Sprache für den Task | Automatische Sprachauswahl basierend auf Task |

### Epic 4: Observability & Safety

| ID | User Story | Akzeptanzkriterien |
|----|------------|-------------------|
| SM-14 | Als Operator logge ich alle Ausführungen | Timestamp, Command/Code, Language, Output-Hash |
| SM-15 | Als System beende ich Commands nach Timeout | Konfigurierbarer Timeout, SIGKILL |
| SM-16 | Als System truncatiere ich große Outputs | Max 32KB, Truncation-Marker |

---

## Technische Tasks

### Phase 1: Backend-Implementierung (5 SP)

- [ ] Bubblewrap auf DGX Spark (ARM64) testen
- [ ] `BubblewrapSandboxBackend` Klasse implementieren
  - [ ] `execute(command: str) -> ExecuteResult`
  - [ ] `read(path: str) -> str`
  - [ ] `write(path: str, content: str) -> WriteResult`
  - [ ] `edit(path: str, old: str, new: str) -> EditResult`
  - [ ] `ls_info(path: str) -> list[FileInfo]`
  - [ ] `grep_raw(pattern: str, path: str) -> list[GrepMatch]`
- [ ] Seccomp-Profil erstellen (strace-basiert)
- [ ] Egress-Proxy mit Domain-Allowlist

### Phase 2: deepagents Integration (4 SP)

- [ ] `create_deep_agent()` mit Custom Backend
- [ ] System-Prompt für AegisRAG Code-Analyse
- [ ] interrupt_on Konfiguration für gefährliche Commands
- [ ] Token-Limit Konfiguration (Context Window Management)
- [ ] Progress Tracking implementieren
  - [ ] `aegis-progress.json` Schema definieren
  - [ ] Startup: Progress lesen und Status ausgeben
  - [ ] Shutdown: Progress aktualisieren

### Phase 3: Multi-Language CodeAct (3 SP)

- [ ] `execute_bash` Tool mit Bubblewrap-Backend
- [ ] `execute_python` Tool mit Pyodide-Backend (langchain-sandbox)
- [ ] CompositeBackend für Shared Workspace
- [ ] Workspace Mount-Konfiguration (beide Sandboxes sehen /workspace)
- [ ] State Persistence Tests (Bash schreibt Datei, Python liest)

### Phase 4: Testing & Dokumentation (3 SP)

- [ ] Unit Tests für Backend-Protocol
- [ ] Integration Tests mit deepagents
- [ ] Security Tests (Path Traversal, Network Escape, Sandbox Escape)
- [ ] Performance Benchmarks
- [ ] Dokumentation

---

## Implementierung: BubblewrapSandboxBackend

```python
from deepagents.backends.protocol import (
    SandboxBackendProtocol, 
    ExecuteResult, 
    WriteResult, 
    EditResult
)
from deepagents.backends.utils import FileInfo, GrepMatch
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
        allowed_domains: list[str] = None,
        timeout: int = 30,
        seccomp_profile: str = None
    ):
        self.repo_path = Path(repo_path).resolve()
        self.workspace = Path("/tmp/aegis-workspace")
        self.allowed_domains = allowed_domains or []
        self.timeout = timeout
        self.seccomp_profile = seccomp_profile
    
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
            # Network isolation (via proxy socket)
            "--unshare-net",
            # Drop capabilities
            "--cap-drop", "ALL",
            # Seccomp
            *(["--seccomp", self.seccomp_profile] if self.seccomp_profile else []),
            # Run command
            "--", "sh", "-c", command
        ]
    
    def execute(self, command: str) -> ExecuteResult:
        """Execute shell command in sandbox."""
        try:
            result = subprocess.run(
                self._build_bwrap_command(command),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd="/workspace"
            )
            return ExecuteResult(
                stdout=result.stdout[:32000],  # Truncate
                stderr=result.stderr[:32000],
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
        # Implementation using execute()
        result = self.execute(f"sed -n '{offset+1},{offset+limit}p' {file_path}")
        return result.stdout if result.exit_code == 0 else f"Error: {result.stderr}"
    
    def write(self, file_path: str, content: str) -> WriteResult:
        """Write file to workspace."""
        if not file_path.startswith("/workspace"):
            return WriteResult(error="Writes only allowed in /workspace")
        # Implementation
        ...
    
    def ls_info(self, path: str) -> list[FileInfo]:
        """List directory contents."""
        result = self.execute(f"ls -la {path}")
        # Parse output to FileInfo
        ...
    
    def grep_raw(
        self, 
        pattern: str, 
        path: str = None, 
        glob: str = None
    ) -> list[GrepMatch] | str:
        """Search for pattern in files."""
        cmd = f"grep -rn '{pattern}' {path or '/repo'}"
        result = self.execute(cmd)
        # Parse to GrepMatch
        ...
```

---

## Agent-Konfiguration

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend
from deepagents.middleware import TodoListMiddleware, FilesystemMiddleware
from langchain.chat_models import init_chat_model
from langchain_sandbox import PyodideSandbox

# LLM (austauschbar)
model = init_chat_model(
    "anthropic:claude-sonnet-4-5",  # oder "openai:gpt-4o", "ollama:qwen2.5"
)

# Bash Backend (Bubblewrap)
bash_backend = BubblewrapSandboxBackend(
    repo_path="/path/to/analyzed/repo",
    allowed_domains=["github.com"],
    timeout=30
)

# Python Backend (Pyodide)
python_backend = PyodideSandboxBackend(
    stateful=True,
    allow_net=True  # Für pip installs
)

# Composite Backend mit Shared Workspace
backend = CompositeBackend(
    default=bash_backend,
    routes={
        "/python/": python_backend
    },
    shared_workspace="/workspace"  # Beide sehen gleichen Workspace
)

# Agent erstellen
agent = create_deep_agent(
    model=model,
    backend=backend,
    system_prompt="""
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
    """,
    interrupt_on={
        "execute_bash": {
            "patterns": ["rm -rf", "curl", "wget", "> /"],
            "allowed_decisions": ["approve", "reject"]
        }
    }
)

# Beispiel: Multi-Language Workflow mit Progress Tracking
result = await agent.ainvoke({
    "messages": [{
        "role": "user", 
        "content": """
        1. Find all Python files with TODO comments
        2. Extract the TODOs into a structured JSON
        3. Categorize them by priority
        """
    }]
})
# Agent wird:
# 1. Progress lesen (falls vorhanden)
# 2. Bash: grep -rn "TODO" --include="*.py" > /workspace/todos.txt
# 3. Python: Parse todos.txt, create JSON structure
# 4. Python: Categorize with simple heuristics or LLM
# 5. Progress aktualisieren
```

## Progress Tracking Schema

```json
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "repo": {
            "type": "string",
            "description": "Path or URL of analyzed repository"
        },
        "status": {
            "type": "string",
            "enum": ["in_progress", "completed", "failed"]
        },
        "started_at": {
            "type": "string",
            "format": "date-time"
        },
        "analyzed_paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Paths already analyzed"
        },
        "pending_paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Paths still to analyze"
        },
        "entities_extracted": {
            "type": "integer",
            "description": "Total count of extracted entities"
        },
        "sessions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "action": {"type": "string"},
                    "files_processed": {"type": "integer"}
                }
            }
        },
        "next_steps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Recommended actions for next session"
        },
        "error": {
            "type": "string",
            "description": "Error message if status is failed"
        }
    },
    "required": ["repo", "status"]
}
```

---

## Definition of Done

- [ ] BubblewrapSandboxBackend erfüllt SandboxBackendProtocol
- [ ] Agent läuft mit deepagents auf DGX Spark
- [ ] Security-Tests bestanden (kein Sandbox-Escape)
- [ ] Performance: <200ms Overhead pro Command
- [ ] LLM-Wechsel funktioniert (Claude ↔ OpenAI ↔ Ollama)
- [ ] Dokumentation aktualisiert

---

## Risiken & Mitigationen

| Risiko | Mitigation |
|--------|------------|
| Bubblewrap ARM64-Kompatibilität | Frühzeitig auf DGX Spark testen |
| deepagents API-Änderungen | Version pinnen, Changelog monitoren |
| Bash CodeAct Komplexität | Minimal Viable erst, dann erweitern |

---

## Schätzung

| Epic | Story Points |
|------|--------------|
| BubblewrapSandboxBackend | 5 |
| deepagents Integration | 4 |
| Multi-Language CodeAct | 3 |
| Testing & Dokumentation | 3 |
| Puffer | 2 |
| **Gesamt** | **17 SP** |

**Ersparnis gegenüber v2:** 12 SP (~41%)

---

## Abhängigkeiten

```toml
# pyproject.toml
[project]
dependencies = [
    "deepagents>=0.2.0",
    "langgraph>=0.4.5",
    "langgraph-codeact>=0.1.3",
    "langchain>=0.3.20",
    "langchain-sandbox>=0.0.5",     # PyodideSandbox für Python
    "langchain-anthropic>=0.3.9",   # Optional
    "langchain-openai>=0.3.0",      # Optional
]
```

---

## Referenzen

### LangChain/LangGraph
- [deepagents GitHub](https://github.com/langchain-ai/deepagents)
- [deepagents Backends Docs](https://docs.langchain.com/oss/python/deepagents/backends)
- [langgraph-codeact GitHub](https://github.com/langchain-ai/langgraph-codeact)
- [langchain-sandbox GitHub](https://github.com/langchain-ai/langchain-sandbox)
- [Sandboxes for DeepAgents Blog](https://blog.langchain.com/execute-code-with-sandboxes-for-deepagents/)

### Anthropic Engineering
- [Writing Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Sandbox Runtime (Open Source)](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)

### Weitere
- [CodeAnt AI: Code Sandboxes for LLMs](https://www.codeant.ai/blogs/agentic-rag-shell-sandboxing)
- [Bubblewrap](https://github.com/containers/bubblewrap)

---

## Changelog

| Version | Datum | Änderungen |
|---------|-------|------------|
| v1 | 2025-12-08 | Initial Sprint Definition |
| v2 | 2025-12-08 | Anthropic Patterns: Bubblewrap, Code Execution, Tool Discovery |
| v3 | 2025-12-08 | LangChain-Integration: deepagents, langgraph-codeact |
| v3.1 | 2025-12-08 | ADR-03 präzisiert: Multi-Language CodeAct (Bash + Python) |
| v3.2 | 2025-12-08 | Progress Tracking für Session-übergreifende Analysen (SM-09b) |
