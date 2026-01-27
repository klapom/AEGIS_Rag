# TD-055: MCP Client Implementation (Sprint 9)

**Status:** OPEN
**Priority:** LOW
**Severity:** Feature Gap
**Original Sprint:** Sprint 9
**Story Points:** 21 SP
**Created:** 2025-12-04

---

## Problem Statement

The Model Context Protocol (MCP) client implementation is missing. AegisRAG cannot connect to external MCP servers to use their tools, limiting the system's ability to integrate with external services and knowledge sources.

**Current State:**
- No MCP client implementation
- No tool discovery mechanism
- No Action Agent for external tool calls
- System is self-contained (cannot call external tools)

---

## What is MCP?

Model Context Protocol (MCP) is Anthropic's open standard for connecting AI systems to external tools, data sources, and services. It enables:

- **Tool Discovery:** Find available tools on MCP servers
- **Tool Execution:** Call external tools with structured input/output
- **Context Sharing:** Share context between AI and external systems

**Official SDK:** `anthropic/mcp` (Python SDK)

---

## Target Architecture

### MCP Integration Flow

```
User Query
    ↓
Coordinator Agent
    ↓
Intent Classification
    ↓ (tool_use intent)
Action Agent ← NEW
    ↓
MCP Client ← NEW
    ↓
External MCP Server
    ↓
Tool Execution Result
    ↓
Response to User
```

### Supported MCP Servers (Examples)

- **Database MCP:** Query external databases
- **Web Search MCP:** Search the web (Brave, Google)
- **File System MCP:** Access file systems
- **API Gateway MCP:** Call external APIs
- **Custom MCP:** Organization-specific tools

---

## Solution Components

### 1. MCP Client Implementation

```python
# src/components/mcp/client.py

from mcp import Client, Tool, ToolResult
from mcp.client import StdioServerParameters

class MCPClient:
    """MCP Client for connecting to external servers."""

    def __init__(self, config: MCPConfig):
        self.config = config
        self.clients: dict[str, Client] = {}

    async def connect(self, server_name: str) -> None:
        """Connect to an MCP server."""
        server_config = self.config.servers[server_name]

        # Stdio transport (local process)
        if server_config.transport == "stdio":
            params = StdioServerParameters(
                command=server_config.command,
                args=server_config.args,
                env=server_config.env
            )
            client = Client(server_name, params)
            await client.connect()
            self.clients[server_name] = client

        # SSE transport (remote server)
        elif server_config.transport == "sse":
            # Connect via HTTP SSE
            pass

    async def discover_tools(self, server_name: str) -> List[Tool]:
        """Discover available tools on a server."""
        client = self.clients[server_name]
        tools = await client.list_tools()
        return tools

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict
    ) -> ToolResult:
        """Call a tool on an MCP server."""
        client = self.clients[server_name]
        result = await client.call_tool(tool_name, arguments)
        return result

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for client in self.clients.values():
            await client.disconnect()
```

### 2. Tool Discovery Service

```python
# src/components/mcp/discovery.py

class ToolDiscoveryService:
    """Manage tool discovery across MCP servers."""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.tool_registry: dict[str, Tool] = {}

    async def discover_all(self) -> dict[str, List[Tool]]:
        """Discover tools from all configured servers."""
        all_tools = {}
        for server_name in self.mcp_client.config.servers:
            await self.mcp_client.connect(server_name)
            tools = await self.mcp_client.discover_tools(server_name)
            all_tools[server_name] = tools

            # Register tools for quick lookup
            for tool in tools:
                self.tool_registry[f"{server_name}:{tool.name}"] = tool

        return all_tools

    def find_tool(self, query: str) -> Optional[Tool]:
        """Find a tool by name or description."""
        # Exact match
        if query in self.tool_registry:
            return self.tool_registry[query]

        # Fuzzy search by description
        for tool_id, tool in self.tool_registry.items():
            if query.lower() in tool.description.lower():
                return tool

        return None
```

### 3. Action Agent (LangGraph)

```python
# src/agents/action_agent.py

from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

class ActionAgentState(TypedDict):
    query: str
    tool_calls: List[ToolCall]
    tool_results: List[ToolResult]
    final_response: str

async def plan_tool_use(state: ActionAgentState) -> ActionAgentState:
    """Plan which tools to call."""
    # Use LLM to determine tool calls
    tool_calls = await llm.plan_tools(
        query=state["query"],
        available_tools=tool_registry.list_tools()
    )
    state["tool_calls"] = tool_calls
    return state

async def execute_tools(state: ActionAgentState) -> ActionAgentState:
    """Execute tool calls via MCP."""
    results = []
    for call in state["tool_calls"]:
        server, tool = call.tool_id.split(":")
        result = await mcp_client.call_tool(server, tool, call.arguments)
        results.append(result)
    state["tool_results"] = results
    return state

async def synthesize_response(state: ActionAgentState) -> ActionAgentState:
    """Synthesize final response from tool results."""
    response = await llm.synthesize(
        query=state["query"],
        tool_results=state["tool_results"]
    )
    state["final_response"] = response
    return state

# Build Action Agent Graph
action_graph = StateGraph(ActionAgentState)
action_graph.add_node("plan", plan_tool_use)
action_graph.add_node("execute", execute_tools)
action_graph.add_node("synthesize", synthesize_response)
action_graph.add_edge("plan", "execute")
action_graph.add_edge("execute", "synthesize")
action_agent = action_graph.compile()
```

### 4. MCP Configuration

```yaml
# config/mcp_servers.yaml

servers:
  filesystem:
    transport: stdio
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/data"]
    enabled: true

  brave-search:
    transport: stdio
    command: npx
    args: ["-y", "@anthropic/mcp-server-brave-search"]
    env:
      BRAVE_API_KEY: ${BRAVE_API_KEY}
    enabled: true

  custom-api:
    transport: sse
    url: https://api.example.com/mcp
    headers:
      Authorization: Bearer ${API_TOKEN}
    enabled: false
```

### 5. Integration with Coordinator

```python
# src/agents/coordinator.py

async def route_query(state: CoordinatorState) -> str:
    """Route query to appropriate agent."""
    intent = state["intent"]

    if intent == "tool_use":
        # Route to Action Agent
        return "action"
    elif intent == "factual":
        return "vector_search"
    # ... other intents
```

---

## Implementation Tasks

### Phase 1: MCP Client (8 SP)
- [ ] Install MCP SDK dependency
- [ ] Implement MCPClient class
- [ ] Stdio transport support
- [ ] SSE transport support
- [ ] Connection management
- [ ] Unit tests

### Phase 2: Tool Discovery (5 SP)
- [ ] ToolDiscoveryService class
- [ ] Tool registry
- [ ] Tool search/lookup
- [ ] Configuration loading
- [ ] Integration tests

### Phase 3: Action Agent (5 SP)
- [ ] ActionAgent LangGraph definition
- [ ] Tool planning with LLM
- [ ] Tool execution handler
- [ ] Response synthesis
- [ ] Integration with Coordinator

### Phase 4: Configuration & Testing (3 SP)
- [ ] YAML configuration schema
- [ ] Environment variable support
- [ ] E2E tests with mock MCP server
- [ ] Documentation

---

## Acceptance Criteria

- [ ] MCP Client connects to external servers
- [ ] Tool discovery lists available tools
- [ ] Action Agent plans and executes tool calls
- [ ] Tool results synthesized into response
- [ ] Configuration via YAML file
- [ ] Error handling for tool failures
- [ ] 80%+ test coverage
- [ ] Documentation with examples

---

## Affected Files

```
src/components/mcp/                     # NEW directory
├── client.py                           # MCP Client
├── discovery.py                        # Tool Discovery
├── config.py                           # Configuration
└── models.py                           # Pydantic models

src/agents/
├── action_agent.py                     # NEW: Action Agent
└── coordinator.py                      # UPDATE: Add action routing

config/mcp_servers.yaml                 # NEW: MCP configuration
tests/unit/mcp/                         # NEW: MCP tests
```

---

## Dependencies

- `mcp` - Anthropic's MCP Python SDK
- Node.js (for stdio MCP servers)
- External MCP servers (optional)

---

## Security Considerations

- **API Keys:** Secure storage for server credentials
- **Sandboxing:** Limit tool capabilities
- **Validation:** Validate tool inputs/outputs
- **Rate Limiting:** Prevent abuse of external tools
- **Audit Logging:** Log all tool calls

---

## Estimated Effort

**Story Points:** 21 SP

**Breakdown:**
- Phase 1 (Client): 8 SP
- Phase 2 (Discovery): 5 SP
- Phase 3 (Action Agent): 5 SP
- Phase 4 (Config/Testing): 3 SP

---

## References

- [SPRINT_PLAN.md - Sprint 9](../sprints/SPRINT_PLAN.md#sprint-9)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/anthropics/mcp)
- [MCP Server Examples](https://github.com/modelcontextprotocol/servers)

---

## Target Sprint

**Recommended:** Sprint 41+ (strategic feature, lower priority)

---

**Last Updated:** 2025-12-04
