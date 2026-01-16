# Sprint 107: MCP Auto-Discovery & Backend Fixes

**Sprint Goal:**
1. Fix critical backend issues from Sprint 106 E2E testing
2. Implement automatic MCP server discovery and integration with public MCP registries

**Story Points:** 26 SP (5 SP backend fixes + 21 SP MCP features)

**Priority:** High (Backend fixes) + Medium (MCP features)

---

## Background

**Current State (Sprint 106):**
- ✅ MCP Backend APIs functional (`/api/v1/mcp/servers`, `/tools`, `/health`)
- ✅ Frontend UI components (MCPServerCard, MCPToolExecutionPanel)
- ❌ No server configuration - ConnectionManager starts empty
- ❌ No auto-discovery - servers must be manually added via API

**Problem:**
Production deployment has 0 MCP servers configured. E2E tests use mocks but highlight missing production setup.

**API Status Verification (Sprint 106):**
```bash
# MCP APIs exist but return empty data
curl http://localhost:8000/api/v1/mcp/servers
# Response: []

curl http://localhost:8000/api/v1/mcp/tools
# Response: []

curl http://localhost:8000/api/v1/mcp/health
# Response: {"status": "healthy", "connected_servers": 0, ...}
```

**Missing Backend Infrastructure:**
1. **No MCP Server Configuration File** - No `config/mcp_servers.yaml` exists
2. **No Connection Manager Initialization** - ConnectionManager starts with empty server list
3. **No Auto-Connect Logic** - Servers must be manually connected via API POST requests
4. **No Registry Integration** - No connection to public MCP registries

---

## Features

### Feature 107.1: MCP Server Configuration File (5 SP)

**Description:** Add YAML-based MCP server configuration with auto-connect on startup

**Implementation:**
```yaml
# config/mcp_servers.yaml
servers:
  - name: bash-tools
    transport: stdio
    command: /usr/bin/bash
    args: []
    description: "Bash command execution tools"
    auto_connect: true
    enabled: true

  - name: python-tools
    transport: stdio
    command: /usr/bin/python3
    args: ["-m", "mcp_server"]
    description: "Python code execution tools"
    auto_connect: true
    enabled: true

  - name: browser-tools
    transport: http
    url: "http://localhost:9222"
    description: "Browser automation via Chrome DevTools Protocol"
    auto_connect: false
    enabled: true
```

**Tasks:**
- [ ] Create `config/mcp_servers.yaml` template
- [ ] Add Pydantic model for server config validation
- [ ] Load config on ConnectionManager init
- [ ] Auto-connect enabled servers on startup
- [ ] Add config reload endpoint `/api/v1/mcp/reload-config`

**Files:**
- `config/mcp_servers.yaml` (new)
- `src/components/mcp/config.py` (new)
- `src/components/mcp/connection_manager.py` (modify)

---

### Feature 107.2: MCP Registry Auto-Discovery (8 SP)

**Description:** Integrate with public MCP server registries for automatic discovery

**MCP Registries:**
- https://github.com/modelcontextprotocol/servers - Official MCP servers
- https://mcpregistry.org - Community registry
- https://awesome-mcp.dev - Curated awesome list

**Implementation:**
```python
class MCPRegistryClient:
    """Client for fetching MCP server definitions from registries."""

    async def discover_servers(self, registry_url: str) -> list[MCPServerDefinition]:
        """Fetch available servers from registry."""

    async def install_server(self, server_id: str, registry: str) -> MCPServer:
        """Download and configure server from registry."""

    async def search_servers(self, query: str) -> list[MCPServerDefinition]:
        """Search registries for servers matching query."""
```

**API Endpoints:**
- `GET /api/v1/mcp/registry/servers` - List available servers from registries
- `POST /api/v1/mcp/registry/install` - Install server from registry
- `GET /api/v1/mcp/registry/search?q=filesystem` - Search registries

**Tasks:**
- [ ] Implement MCPRegistryClient
- [ ] Add caching for registry metadata (Redis, 1h TTL)
- [ ] Create install/uninstall workflow
- [ ] Add server dependency resolution
- [ ] Handle authentication for private registries

**Files:**
- `src/components/mcp/registry_client.py` (new)
- `src/api/v1/mcp_registry.py` (new)

---

### Feature 107.3: Frontend Server Discovery UI (5 SP)

**Description:** UI for browsing, searching, and installing MCP servers from registries

**Components:**
- `MCPServerBrowser` - Browse available servers from registries
- `MCPServerInstaller` - Install wizard with dependency checks
- `MCPServerSearch` - Search across multiple registries
- `MCPServerMarketplace` - Card-based marketplace view

**Mockup:**
```
┌─────────────────────────────────────────┐
│ MCP Server Marketplace                  │
│ ┌─────────────────────────────────────┐ │
│ │ Search: [filesystem tools      ] 🔍 │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ 📁 Filesystem Tools      ⭐ 1.2k    │ │
│ │ Read/write files, list directories   │ │
│ │ Registry: modelcontextprotocol/...   │ │
│ │                        [Install] 📥  │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ 🌐 Web Scraper          ⭐ 856      │ │
│ │ Extract data from websites           │ │
│ │ Registry: awesome-mcp.dev            │ │
│ │                        [Install] 📥  │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Tasks:**
- [ ] Create MCPServerBrowser component
- [ ] Add search/filter functionality
- [ ] Implement install workflow with progress
- [ ] Add server rating/popularity display
- [ ] Show installation requirements (dependencies, permissions)

**Files:**
- `frontend/src/pages/admin/MCPMarketplace.tsx` (new)
- `frontend/src/components/admin/MCPServerBrowser.tsx` (new)
- `frontend/src/components/admin/MCPServerInstaller.tsx` (new)

---

### Feature 107.4: Server Dependency Management (3 SP)

**Description:** Manage server dependencies (npm packages, Python packages, system tools)

**Example:**
```yaml
# Server with dependencies
servers:
  - name: github-tools
    transport: stdio
    command: npx
    args: ["@modelcontextprotocol/server-github"]
    dependencies:
      npm:
        - "@modelcontextprotocol/server-github@^1.0.0"
      env:
        - GITHUB_TOKEN  # Required
    auto_install: true
```

**Tasks:**
- [ ] Add dependency resolution
- [ ] Auto-install npm/pip packages
- [ ] Validate required environment variables
- [ ] Display missing dependencies in UI
- [ ] Add dependency update check

---

## Backend Issues from Sprint 106 E2E Testing

**Priority Issues to Address:**

### Issue 107.0A: Graphiti Neo4j Client Bug ⚠️ High Priority

**Error:** `'Neo4jClient' object has no attribute 'verify_connectivity'`

**Location:** `src/domains/knowledge_graph/neo4j_client.py` (likely)

**Fix Required:**
```python
class Neo4jClient:
    async def verify_connectivity(self) -> bool:
        """Verify Neo4j connection is active."""
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j connectivity check failed: {e}")
            return False
```

**Impact:** Memory Management UI shows Graphiti layer as "error" state

**Story Points:** 2 SP (Quick fix)

---

### Issue 107.0B: Qdrant Statistics Not Implemented ⚠️ Medium Priority

**Current Response:** `"note": "Qdrant collection statistics require dedicated endpoint"`

**Location:** `src/api/v1/memory.py:571` (get_memory_stats function)

**Fix Required:**
```python
from src.components.vector_search.qdrant_client import get_qdrant_client

qdrant_client = get_qdrant_client()
collection_info = await qdrant_client.get_collection(settings.qdrant_collection_name)

qdrant_stats = {
    "available": True,
    "collection_name": collection_info.collection_name,
    "points_count": collection_info.points_count,
    "vectors_count": collection_info.vectors_count,
    "indexed_vectors_count": collection_info.indexed_vectors_count,
    "segments_count": collection_info.segments_count,
    "disk_data_size_mb": collection_info.disk_data_size / 1024 / 1024,
    "ram_data_size_mb": collection_info.ram_data_size / 1024 / 1024,
}
```

**Impact:** Memory Management UI shows minimal Qdrant information

**Story Points:** 3 SP

---

### Issue 107.0C: Unverified APIs for Groups 13-15 ❓ Low Priority

**APIs to Verify:**
- Agent Hierarchy: `/api/v1/agents/hierarchy`, `/agents/communication`
- GDPR/Audit: `/api/v1/audit/events`, `/gdpr/consents`
- Explainability: `/api/v1/explainability/decisions`

**Action:** Investigate during respective E2E test fixes (Groups 13-15)

**Story Points:** TBD

---

## Testing

- [ ] Unit tests for MCPRegistryClient
- [ ] Integration tests for server installation
- [ ] E2E tests for marketplace UI
- [ ] Test offline registry fallback
- [ ] Test dependency installation
- [ ] Fix Issue 107.0A (Graphiti verify_connectivity)
- [ ] Fix Issue 107.0B (Qdrant statistics)

---

## Documentation

- [ ] ADR-XXX: MCP Auto-Discovery Architecture
- [ ] User Guide: Installing MCP Servers
- [ ] API Documentation: Registry endpoints
- [ ] config/mcp_servers.yaml.example
- [ ] Document backend fixes (107.0A, 107.0B)

---

## Success Criteria

- [ ] Production deployment has 3+ pre-configured MCP servers
- [ ] Users can discover servers from public registries
- [ ] One-click install from marketplace
- [ ] Dependency auto-installation works
- [ ] Server config reload without restart
- [ ] Memory Management UI shows complete statistics (Graphiti + Qdrant)

---

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- [MCP Registry](https://mcpregistry.org)
- Sprint 40: Original MCP Implementation
- Sprint 106: E2E Test Fixes (highlighted missing config + backend issues)

---

## Story Points Breakdown

| Feature/Fix | SP |
|-------------|-----|
| Issue 107.0A: Graphiti Neo4j bug | 2 |
| Issue 107.0B: Qdrant statistics | 3 |
| Feature 107.1: MCP Config File | 5 |
| Feature 107.2: Registry Auto-Discovery | 8 |
| Feature 107.3: Frontend Marketplace UI | 5 |
| Feature 107.4: Dependency Management | 3 |
| **Total** | **26 SP** |

---

**Status:** 📝 Planned (includes Sprint 106 backend fixes)
**Estimated Completion:** Sprint 107
**Prerequisite:** Fix Issues 107.0A, 107.0B before Feature 107.1
