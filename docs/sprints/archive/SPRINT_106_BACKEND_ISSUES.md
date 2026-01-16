# Sprint 106: Backend API Issues Discovered During E2E Testing

**Created:** 2026-01-16
**Status:** Open Issues

---

## Issue 1: Graphiti Neo4j Client Missing Method ⚠️ High Priority

**Discovered:** Sprint 106 Memory Management E2E testing
**Location:** Likely `src/domains/knowledge_graph/neo4j_client.py`

**Error:**
```
'Neo4jClient' object has no attribute 'verify_connectivity'
```

**Impact:**
- Memory Management page shows Graphiti layer as "error" state
- Episodic memory statistics cannot be retrieved
- `/api/v1/memory/stats` returns partial data with error message

**API Response:**
```json
{
  "episodic": {
    "enabled": true,
    "available": true,
    "error": "'Neo4jClient' object has no attribute 'verify_connectivity'"
  }
}
```

**Expected Fix:**
Add `verify_connectivity()` method to Neo4jClient class:
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

**Priority:** High - Breaks Memory Management UI functionality

---

## Issue 2: MCP Server Configuration Missing 🔧 Sprint 107

**Discovered:** Sprint 106 Browser Tools E2E testing
**Location:** `config/` directory

**Problem:**
- No `config/mcp_servers.yaml` file exists
- ConnectionManager starts with empty server list
- All MCP-related E2E tests must use mocks

**API Responses:**
```bash
GET /api/v1/mcp/servers → []
GET /api/v1/mcp/tools → []
GET /api/v1/mcp/health → {"connected_servers": 0}
```

**Impact:**
- Browser Tools page shows no servers (correct behavior, but not useful)
- Skills-Tool Integration tests cannot verify real tool execution
- MCP functionality appears "broken" in production

**Expected Fix (Sprint 107):**
1. Create `config/mcp_servers.yaml` with default servers:
   - bash-tools (stdio: /usr/bin/bash)
   - python-tools (stdio: /usr/bin/python3 -m mcp_server)
   - browser-tools (http: localhost:9222)

2. Implement auto-connect on startup:
   - Load config on ConnectionManager init
   - Auto-connect servers with `auto_connect: true`
   - Implement config reload endpoint

3. Add registry integration:
   - Fetch server definitions from public registries
   - Install/uninstall workflow
   - Dependency management

**Priority:** Medium - Deferred to Sprint 107 (Feature 107.1-107.4)

---

## Issue 3: Qdrant Statistics Not Implemented ⚠️ Medium Priority

**Discovered:** Sprint 106 Memory Management E2E testing
**Location:** `src/api/v1/memory.py:571` (get_memory_stats function)

**Current Response:**
```json
{
  "long_term": {
    "available": true,
    "note": "Qdrant collection statistics require dedicated endpoint"
  }
}
```

**Problem:**
- Qdrant layer statistics are stubbed out
- Backend returns placeholder message instead of real stats
- Memory Management UI shows minimal information for Qdrant

**Expected Stats:**
```json
{
  "long_term": {
    "available": true,
    "collection_name": "aegis_rag",
    "points_count": 12543,
    "vectors_count": 12543,
    "indexed_vectors_count": 12543,
    "segments_count": 4,
    "disk_data_size_mb": 245.8,
    "ram_data_size_mb": 12.3,
    "avg_search_latency_ms": 45.2
  }
}
```

**Implementation Needed:**
```python
# In get_memory_stats() function
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
    # Add search latency tracking if available
}
```

**Impact:**
- Memory Management page shows incomplete statistics
- Cannot monitor Qdrant performance/usage
- UI design expects more detailed metrics (documents, size, latency)

**Priority:** Medium - UI works but shows minimal info

---

## Issue 4: Unverified API Endpoints ❓ Pending Investigation

**Discovered:** Sprint 106 E2E test analysis
**Status:** APIs may exist but not verified with production backend

### Agent Hierarchy (Group 13 - 6 failed tests)

**Expected Endpoints:**
- `GET /api/v1/agents/hierarchy` - Agent tree structure
- `GET /api/v1/agents/communication` - Message bus events

**Frontend Components:**
- `AgentHierarchyD3.tsx` - D3.js hierarchy visualization
- `MessageBusMonitor.tsx` - Real-time message monitoring

**Verification Needed:**
```bash
curl http://localhost:8000/api/v1/agents/hierarchy
curl http://localhost:8000/api/v1/agents/communication
```

### GDPR/Audit (Group 14 - 11 failed tests)

**Expected Endpoints:**
- `GET /api/v1/audit/events` - Audit log entries
- `GET /api/v1/gdpr/consents` - GDPR consent records
- `POST /api/v1/gdpr/consents` - Create consent
- `GET /api/v1/gdpr/data-subject-requests` - DSR requests

**Frontend Components:**
- `AuditLogBrowser.tsx` - Audit trail viewer
- `ConsentRegistry.tsx` - GDPR consent management
- `DataSubjectRights.tsx` - DSR request handling

**Verification Needed:**
```bash
curl http://localhost:8000/api/v1/audit/events
curl http://localhost:8000/api/v1/gdpr/consents
```

### Explainability (Group 15 - 9 failed tests)

**Expected Endpoints:**
- `GET /api/v1/explainability/decisions` - AI decision log
- `GET /api/v1/explainability/model-cards` - Model documentation
- `GET /api/v1/explainability/impact-assessments` - Impact assessments

**Frontend Components:**
- `ExplainabilityPage.tsx` - Explainability dashboard
- Components for decision transparency

**Verification Needed:**
```bash
curl http://localhost:8000/api/v1/explainability/decisions
```

**Priority:** Low - Investigate during Groups 13-15 E2E fix work

---

## Issue 5: Skills API Data Format ❓ Not Verified

**Discovered:** Sprint 106 Skills Registry testing (Group 05)
**Status:** Tests use mocks, real backend response format unknown

**Expected Response:**
```typescript
{
  items: SkillSummary[],
  total: number,
  page: number,
  limit: number
}
```

**Verification Needed:**
```bash
curl http://localhost:8000/api/v1/skills
curl http://localhost:8000/api/v1/skills/web_search/config
```

**Priority:** Low - Tests pass with mocks, verify during Skills feature work

---

## Summary

| Issue | Priority | Status | Sprint |
|-------|----------|--------|--------|
| Graphiti Neo4j verify_connectivity | High | Open | 106 |
| Qdrant Statistics Not Implemented | Medium | Open | TBD |
| MCP Server Configuration | Medium | Deferred | 107 |
| Agent Hierarchy APIs | Low | Unverified | TBD |
| GDPR/Audit APIs | Low | Unverified | TBD |
| Explainability APIs | Low | Unverified | TBD |
| Skills API Format | Low | Unverified | TBD |

**Recommendation:**
1. Fix Graphiti bug in Sprint 106 (quick fix)
2. Defer MCP configuration to Sprint 107 (planned)
3. Investigate Groups 13-15 APIs when fixing those test groups

---

**Last Updated:** 2026-01-16 (Sprint 106)
