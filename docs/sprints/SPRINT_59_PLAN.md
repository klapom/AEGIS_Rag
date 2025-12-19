# Sprint 59: Agentic Features & Tool Use

**Status:** PLANNED
**Branch:** `sprint-59-agentic-features`
**Start Date:** TBD (nach Sprint 58)
**Estimated Duration:** 5-7 Tage
**Total Story Points:** 55 SP

---

## Sprint Overview

Sprint 59 implementiert **Agentic Capabilities** für AegisRAG:
- Bash/Python Execution mit Sandboxing
- Agentic Search / Deep Research
- Tool Use Framework
- Community Detection Fix

**Voraussetzung:** Sprint 58 abgeschlossen (Refactoring complete, 80% Coverage)

**Hinweis:** Die refactored Codebase (Sprint 53-58) bietet die ideale Grundlage:
- Protocol-basierte Interfaces für Tool Use
- Domain Boundaries für saubere Integration
- DI Container für flexible Konfiguration

---

## Features

| # | Feature | SP | Priority | Parallelisierbar |
|---|---------|-----|----------|------------------|
| 59.1 | Community Detection Fix | 8 | P0 | Nein (Blocker) |
| 59.2 | Tool Use Framework | 13 | P0 | Nach 59.1 |
| 59.3 | Bash Execution Tool | 8 | P1 | Ja (Agent 1) |
| 59.4 | Python Execution Tool | 8 | P1 | Ja (Agent 2) |
| 59.5 | Sandboxing Layer | 10 | P0 | Ja (Agent 3) |
| 59.6 | Agentic Search / Deep Research | 13 | P1 | Nach 59.2 |

**Total: 55 SP**

---

## Feature Details

### Feature 59.1: Community Detection Fix (8 SP)

**Priority:** P0 (Blocker - keine Communities gefunden!)
**Parallelisierung:** Nein - muss zuerst gefixt werden

**Problem:**
Community Detection läuft, aber keine Communities werden erstellt:
```
=== COMMUNITY DATA ===
Entities with community_id: 0   ← KEINE COMMUNITIES!
```

**Root Cause Analysis (Sprint 51):**
1. Property-Name Bug: `e.id` statt `e.entity_id`
2. Relationship-Type Bug: `RELATED_TO` statt `RELATES_TO`

**Betroffene Datei:** `src/domains/knowledge_graph/communities/detector.py`
(ehemals `src/components/graph_rag/community_detector.py`)

**Fixes:**

```python
# FIX 1: Property Names
# FALSCH:
entities_query = "MATCH (e:base) RETURN e.id AS id"
# RICHTIG:
entities_query = "MATCH (e:base) RETURN e.entity_id AS id"

# FIX 2: Relationship Type
# FALSCH:
MATCH (e1:base)-[r:RELATED_TO]-(e2:base)
# RICHTIG:
MATCH (e1:base)-[r:RELATES_TO]-(e2:base)
```

**Zeilen zu ändern:**
- Zeile 376: `e.id` → `e.entity_id`
- Zeile 382: `e1.id, e2.id` → `e1.entity_id, e2.entity_id`
- Zeile 383: `RELATED_TO` → `RELATES_TO`
- Zeile 506: `{id: entity_id}` → `{entity_id: $entity_id}`
- Zeile 544: `e.id` → `e.entity_id`
- Zeile 582: `e.id` → `e.entity_id`
- Zeile 611: `e.id` → `e.entity_id`

**Validation:**

```python
# Nach Fix: Re-run Community Detection
async def test_community_detection():
    detector = CommunityDetector()
    await detector.detect_communities()

    # Verify
    query = "MATCH (e:base) WHERE e.community_id IS NOT NULL RETURN count(e)"
    result = await neo4j.query(query)
    assert result[0]["count(e)"] > 0, "Communities should be detected"
```

**Acceptance Criteria:**
- [ ] Property Names korrekt (entity_id)
- [ ] Relationship Types korrekt (RELATES_TO)
- [ ] Nach Re-Ingestion: Entities haben community_id
- [ ] LightRAG `global` mode funktioniert

---

### Feature 59.2: Tool Use Framework (13 SP)

**Priority:** P0 (Foundation für alle Tool-Features)
**Parallelisierung:** Nach 59.1

**Ziel:** Erweiterbares Framework für LLM Tool Use.

**Neue Dateien:**

```
src/domains/llm_integration/tools/
├── __init__.py
├── registry.py              # Tool Registration
├── executor.py              # Tool Execution
├── schemas.py               # OpenAI-compatible Tool Schemas
├── validators.py            # Input Validation
└── result_handlers.py       # Result Processing
```

**Tool Registry:**

```python
# src/domains/llm_integration/tools/registry.py
"""Tool Registry for LLM Tool Use.

Sprint 59 Feature 59.2: Central registry for available tools.
"""

from typing import Callable, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ToolDefinition:
    """Definition of an available tool."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    handler: Callable
    requires_sandbox: bool = False


class ToolRegistry:
    """Registry for LLM-callable tools."""

    _tools: dict[str, ToolDefinition] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        parameters: dict[str, Any],
        requires_sandbox: bool = False,
    ) -> Callable:
        """Decorator to register a tool."""
        def decorator(func: Callable) -> Callable:
            cls._tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                handler=func,
                requires_sandbox=requires_sandbox,
            )
            logger.info("tool_registered", name=name)
            return func
        return decorator

    @classmethod
    def get_tool(cls, name: str) -> ToolDefinition | None:
        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls) -> list[ToolDefinition]:
        return list(cls._tools.values())

    @classmethod
    def get_openai_tools_schema(cls) -> list[dict]:
        """Get tools in OpenAI function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            }
            for tool in cls._tools.values()
        ]
```

**Tool Executor:**

```python
# src/domains/llm_integration/tools/executor.py
"""Tool Executor with Sandboxing Support.

Sprint 59 Feature 59.2: Executes tools with optional sandboxing.
"""

from typing import Any
import structlog

from src.domains.llm_integration.tools.registry import ToolRegistry, ToolDefinition
from src.domains.llm_integration.tools.validators import validate_parameters

logger = structlog.get_logger(__name__)


class ToolExecutor:
    """Executes registered tools."""

    def __init__(self, sandbox_enabled: bool = True):
        self.sandbox_enabled = sandbox_enabled
        self._sandbox: "Sandbox | None" = None

    async def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool by name."""
        tool = ToolRegistry.get_tool(tool_name)
        if not tool:
            return {"error": f"Unknown tool: {tool_name}"}

        # Validate parameters
        validation_result = validate_parameters(parameters, tool.parameters)
        if not validation_result.valid:
            return {"error": validation_result.error}

        # Execute with or without sandbox
        if tool.requires_sandbox and self.sandbox_enabled:
            return await self._execute_sandboxed(tool, parameters)
        else:
            return await self._execute_direct(tool, parameters)

    async def _execute_sandboxed(
        self,
        tool: ToolDefinition,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute tool in sandbox."""
        from src.domains.llm_integration.sandbox import get_sandbox
        sandbox = await get_sandbox()
        return await sandbox.run(tool.handler, parameters)

    async def _execute_direct(
        self,
        tool: ToolDefinition,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute tool directly."""
        try:
            result = await tool.handler(**parameters)
            return {"result": result}
        except Exception as e:
            logger.error("tool_execution_failed", tool=tool.name, error=str(e))
            return {"error": str(e)}
```

**Integration mit AegisLLMProxy:**

```python
# src/domains/llm_integration/proxy/aegis_proxy.py (UPDATE)
class AegisLLMProxy:
    """Updated with tool use support."""

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> dict:
        """Chat with tool use capability."""
        if tools is None:
            tools = ToolRegistry.get_openai_tools_schema()

        response = await self._call_llm(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )

        # Handle tool calls
        if response.get("tool_calls"):
            return await self._handle_tool_calls(response, messages)

        return response
```

**Acceptance Criteria:**
- [ ] Tool Registry funktional
- [ ] Tool Executor mit Sandbox Support
- [ ] OpenAI-kompatible Schemas
- [ ] Integration in AegisLLMProxy

---

### Feature 59.3: Bash Execution Tool (8 SP)

**Priority:** P1
**Parallelisierung:** Agent 1 (nach 59.2)

**Neue Datei:** `src/domains/llm_integration/tools/builtin/bash_tool.py`

```python
"""Bash Execution Tool.

Sprint 59 Feature 59.3: Execute bash commands with sandboxing.
"""

import asyncio
from typing import Any

from src.domains.llm_integration.tools.registry import ToolRegistry


BASH_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "The bash command to execute",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30)",
            "default": 30,
        },
        "working_dir": {
            "type": "string",
            "description": "Working directory for command execution",
        },
    },
    "required": ["command"],
}


@ToolRegistry.register(
    name="bash",
    description="Execute a bash command in a sandboxed environment",
    parameters=BASH_TOOL_SCHEMA,
    requires_sandbox=True,
)
async def bash_execute(
    command: str,
    timeout: int = 30,
    working_dir: str | None = None,
) -> dict[str, Any]:
    """Execute bash command with timeout.

    Args:
        command: Bash command to execute
        timeout: Execution timeout in seconds
        working_dir: Working directory

    Returns:
        Dict with stdout, stderr, and exit_code
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )

        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": process.returncode,
        }
    except asyncio.TimeoutError:
        process.kill()
        return {
            "error": f"Command timed out after {timeout} seconds",
            "exit_code": -1,
        }
    except Exception as e:
        return {
            "error": str(e),
            "exit_code": -1,
        }
```

**Blacklist/Whitelist:**

```python
# src/domains/llm_integration/tools/builtin/bash_security.py
"""Bash command security filters."""

COMMAND_BLACKLIST = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    ":(){:|:&};:",  # Fork bomb
    "chmod 777 /",
    "curl | bash",
    "wget | bash",
]

DANGEROUS_PATTERNS = [
    r">\s*/dev/sd[a-z]",  # Writing to block devices
    r"rm\s+-rf\s+/[^/]",  # Dangerous rm
    r"\|\s*sh\s*$",       # Piping to shell
]

def is_command_safe(command: str) -> tuple[bool, str | None]:
    """Check if command is safe to execute."""
    for blocked in COMMAND_BLACKLIST:
        if blocked in command:
            return False, f"Blocked command pattern: {blocked}"

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return False, f"Dangerous pattern detected"

    return True, None
```

**Acceptance Criteria:**
- [ ] Bash Tool registriert
- [ ] Timeout funktioniert
- [ ] Blacklist/Whitelist aktiv
- [ ] Sandbox-Integration

---

### Feature 59.4: Python Execution Tool (8 SP)

**Priority:** P1
**Parallelisierung:** Agent 2 (nach 59.2)

**Neue Datei:** `src/domains/llm_integration/tools/builtin/python_tool.py`

```python
"""Python Execution Tool.

Sprint 59 Feature 59.4: Execute Python code with sandboxing.
"""

import ast
import sys
from io import StringIO
from typing import Any

from src.domains.llm_integration.tools.registry import ToolRegistry


PYTHON_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": "Python code to execute",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30)",
            "default": 30,
        },
    },
    "required": ["code"],
}


@ToolRegistry.register(
    name="python",
    description="Execute Python code in a sandboxed environment",
    parameters=PYTHON_TOOL_SCHEMA,
    requires_sandbox=True,
)
async def python_execute(
    code: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute Python code with restrictions.

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds

    Returns:
        Dict with output, result, and any errors
    """
    # Validate code first
    validation = validate_python_code(code)
    if not validation.valid:
        return {"error": validation.error}

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        # Create restricted globals
        restricted_globals = create_restricted_globals()

        # Execute
        exec(code, restricted_globals)

        output = sys.stdout.getvalue()
        return {
            "output": output,
            "success": True,
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False,
        }
    finally:
        sys.stdout = old_stdout


def validate_python_code(code: str) -> "ValidationResult":
    """Validate Python code for safety."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ValidationResult(False, f"Syntax error: {e}")

    # Check for dangerous imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in BLOCKED_MODULES:
                    return ValidationResult(False, f"Blocked module: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module in BLOCKED_MODULES:
                return ValidationResult(False, f"Blocked module: {node.module}")

    return ValidationResult(True, None)


BLOCKED_MODULES = [
    "os",
    "subprocess",
    "sys",
    "shutil",
    "socket",
    "ctypes",
    "multiprocessing",
    "__builtins__",
]


def create_restricted_globals() -> dict:
    """Create restricted globals for code execution."""
    import math
    import json
    import datetime
    import re

    return {
        "__builtins__": {
            "print": print,
            "len": len,
            "range": range,
            "str": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "bool": bool,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
        },
        "math": math,
        "json": json,
        "datetime": datetime,
        "re": re,
    }
```

**Acceptance Criteria:**
- [ ] Python Tool registriert
- [ ] AST Validation funktioniert
- [ ] Blocked Modules
- [ ] Restricted Globals

---

### Feature 59.5: Sandboxing Layer (10 SP)

**Priority:** P0 (Security-kritisch)
**Parallelisierung:** Agent 3 (parallel zu 59.3, 59.4)

**Neue Dateien:**

```
src/domains/llm_integration/sandbox/
├── __init__.py
├── container.py         # Docker-based sandbox
├── process.py           # Process-level isolation
├── resource_limits.py   # CPU/Memory limits
└── network.py           # Network restrictions
```

**Container-based Sandbox:**

```python
# src/domains/llm_integration/sandbox/container.py
"""Docker-based sandbox for code execution.

Sprint 59 Feature 59.5: Isolated execution environment.
"""

import asyncio
import docker
from typing import Any, Callable
import structlog

logger = structlog.get_logger(__name__)


class DockerSandbox:
    """Docker container-based sandbox."""

    def __init__(
        self,
        image: str = "python:3.12-slim",
        memory_limit: str = "256m",
        cpu_quota: int = 50000,  # 50% CPU
        network_disabled: bool = True,
    ):
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.network_disabled = network_disabled
        self._client = docker.from_env()

    async def run(
        self,
        command: str,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Run command in sandbox container."""
        try:
            container = self._client.containers.run(
                self.image,
                command=command,
                detach=True,
                mem_limit=self.memory_limit,
                cpu_quota=self.cpu_quota,
                network_disabled=self.network_disabled,
                read_only=True,
                security_opt=["no-new-privileges"],
            )

            # Wait with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(container.wait),
                timeout=timeout,
            )

            logs = container.logs().decode("utf-8")
            container.remove()

            return {
                "output": logs,
                "exit_code": result["StatusCode"],
            }
        except asyncio.TimeoutError:
            container.kill()
            container.remove()
            return {"error": "Execution timed out", "exit_code": -1}
        except Exception as e:
            logger.error("sandbox_execution_failed", error=str(e))
            return {"error": str(e), "exit_code": -1}
```

**Resource Limits:**

```python
# src/domains/llm_integration/sandbox/resource_limits.py
"""Resource limits for sandboxed execution."""

import resource
from dataclasses import dataclass


@dataclass
class ResourceLimits:
    """Configurable resource limits."""
    max_memory_mb: int = 256
    max_cpu_seconds: int = 30
    max_file_size_mb: int = 10
    max_processes: int = 5
    max_open_files: int = 20


def apply_limits(limits: ResourceLimits) -> None:
    """Apply resource limits to current process."""
    # Memory limit
    resource.setrlimit(
        resource.RLIMIT_AS,
        (limits.max_memory_mb * 1024 * 1024, limits.max_memory_mb * 1024 * 1024)
    )

    # CPU time limit
    resource.setrlimit(
        resource.RLIMIT_CPU,
        (limits.max_cpu_seconds, limits.max_cpu_seconds)
    )

    # File size limit
    resource.setrlimit(
        resource.RLIMIT_FSIZE,
        (limits.max_file_size_mb * 1024 * 1024, limits.max_file_size_mb * 1024 * 1024)
    )

    # Process limit
    resource.setrlimit(
        resource.RLIMIT_NPROC,
        (limits.max_processes, limits.max_processes)
    )
```

**Acceptance Criteria:**
- [ ] Docker Sandbox funktional
- [ ] Resource Limits anwendbar
- [ ] Network Isolation
- [ ] Read-only Filesystem Option

---

### Feature 59.6: Agentic Search / Deep Research (13 SP)

**Priority:** P1
**Parallelisierung:** Nach 59.2 (braucht Tool Framework)

**Konzept:** Multi-Step Research Agent der:
1. Query analysiert
2. Suchstrategie plant
3. Multiple Suchen ausführt
4. Ergebnisse synthetisiert

**Neue Dateien:**

```
src/agents/research/
├── __init__.py
├── planner.py           # Research Planning
├── searcher.py          # Multi-Source Search
├── synthesizer.py       # Result Synthesis
└── graph.py             # LangGraph Workflow
```

**Research Agent Graph:**

```python
# src/agents/research/graph.py
"""Deep Research Agent with LangGraph.

Sprint 59 Feature 59.6: Multi-step research workflow.
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator


class ResearchState(TypedDict):
    """State for research workflow."""
    query: str
    research_plan: list[str]
    search_results: Annotated[list[dict], operator.add]
    synthesis: str
    iteration: int
    max_iterations: int


def create_research_graph() -> StateGraph:
    """Create the research agent graph."""
    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("plan", plan_research)
    workflow.add_node("search", execute_searches)
    workflow.add_node("evaluate", evaluate_results)
    workflow.add_node("synthesize", synthesize_findings)

    # Add edges
    workflow.add_edge("plan", "search")
    workflow.add_edge("search", "evaluate")
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "continue": "search",
            "synthesize": "synthesize",
        }
    )
    workflow.add_edge("synthesize", END)

    workflow.set_entry_point("plan")
    return workflow.compile()


async def plan_research(state: ResearchState) -> ResearchState:
    """Plan the research strategy."""
    from src.domains.llm_integration import get_llm_proxy

    llm = await get_llm_proxy()
    plan = await llm.generate(
        f"Create a research plan for: {state['query']}\n"
        "List 3-5 specific search queries to answer this question."
    )

    state["research_plan"] = parse_plan(plan)
    return state


async def execute_searches(state: ResearchState) -> ResearchState:
    """Execute planned searches."""
    from src.domains.vector_search import search_hybrid
    from src.domains.knowledge_graph import query_graph

    results = []
    for search_query in state["research_plan"]:
        # Hybrid search
        vector_results = await search_hybrid(search_query, top_k=5)
        results.extend(vector_results)

        # Graph search
        graph_results = await query_graph(search_query)
        results.extend(graph_results)

    state["search_results"].extend(results)
    state["iteration"] += 1
    return state


async def synthesize_findings(state: ResearchState) -> ResearchState:
    """Synthesize all findings into coherent answer."""
    from src.domains.llm_integration import get_llm_proxy

    llm = await get_llm_proxy()
    synthesis = await llm.generate(
        f"Query: {state['query']}\n\n"
        f"Research Findings:\n{format_results(state['search_results'])}\n\n"
        "Synthesize these findings into a comprehensive answer."
    )

    state["synthesis"] = synthesis
    return state
```

**Integration mit Chat:**

```python
# src/api/v1/chat.py (UPDATE)
@router.post("/chat/research")
async def deep_research(request: ResearchRequest) -> StreamingResponse:
    """Execute deep research query with multi-step reasoning."""
    from src.agents.research import create_research_graph

    graph = create_research_graph()
    initial_state = {
        "query": request.query,
        "research_plan": [],
        "search_results": [],
        "synthesis": "",
        "iteration": 0,
        "max_iterations": request.max_iterations or 3,
    }

    async def generate():
        async for event in graph.astream(initial_state):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Acceptance Criteria:**
- [ ] Research Planner funktional
- [ ] Multi-Source Search
- [ ] Iterative Refinement
- [ ] Result Synthesis
- [ ] SSE Streaming für Progress

---

## Parallel Execution Strategy

### Wave 1 (Tag 1): Community Fix (BLOCKER)
```
Agent 1: Feature 59.1 - Community Detection Fix
         Alle anderen warten oder arbeiten an Design-Docs!
```

### Wave 2 (Tag 2): Tool Framework
```
Agent 1: Feature 59.2 - Tool Use Framework (FOUNDATION)
```

### Wave 3 (Tag 3-5): Tools & Sandbox (3 Agents parallel)
```
┌─────────────────────────────────────────────────────┐
│                PARALLEL EXECUTION                    │
├──────────────┬──────────────┬──────────────────────┤
│   Agent 1    │   Agent 2    │   Agent 3            │
│   59.3       │   59.4       │   59.5               │
│   Bash Tool  │   Python     │   Sandboxing         │
│   8 SP       │   8 SP       │   10 SP              │
└──────────────┴──────────────┴──────────────────────┘
```

### Wave 4 (Tag 6-7): Deep Research
```
Agent 1: Feature 59.6 - Agentic Search
Agent 2: Integration Tests
Agent 3: Documentation
Agent 4: Security Review
```

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Command Injection | Blacklist + Whitelist patterns |
| Resource Exhaustion | CPU/Memory limits |
| Network Access | Docker network isolation |
| File System Access | Read-only containers |
| Privilege Escalation | no-new-privileges flag |
| Timeout Attacks | Strict timeouts + kill |

---

## Acceptance Criteria (Sprint Complete)

- [ ] Community Detection funktioniert
- [ ] Tool Use Framework implementiert
- [ ] Bash Tool mit Sandboxing
- [ ] Python Tool mit Sandboxing
- [ ] Docker-based Sandbox
- [ ] Agentic Search / Deep Research
- [ ] Security Review bestanden
- [ ] E2E Tests für alle Features

---

## Definition of Done

### Per Feature
- [ ] Implementation abgeschlossen
- [ ] Unit Tests (≥80% Coverage)
- [ ] Integration Tests
- [ ] Security Review
- [ ] Documentation

### Sprint Complete
- [ ] Alle Features merged
- [ ] CI/CD grün
- [ ] Security Audit bestanden
- [ ] Performance Benchmarks

---

## References

- [ADR-046: Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md) - Completed
- [Sprint 51: Community Detection Bug](SPRINT_51_PLAN.md)
- [Sprint 57: ToolExecutor Protocol](SPRINT_57_PLAN.md)

---

**END OF SPRINT 59 PLAN**
