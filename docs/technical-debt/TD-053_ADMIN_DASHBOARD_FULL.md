# TD-053: Admin Dashboard Full Implementation (Sprint 11)

**Status:** OPEN
**Priority:** MEDIUM
**Severity:** Feature Gap
**Original Sprint:** Sprint 11
**Story Points:** 34 SP
**Created:** 2025-12-04

---

## Problem Statement

The Admin interface is incomplete. While basic document indexing and cost dashboard exist, critical admin features are missing: LLM model configuration, user management, permission/RBAC system, and comprehensive system monitoring.

**Current State:**
- AdminIndexingPage: Document indexing (SSE progress) - DONE
- AdminCostDashboard: LLM cost tracking - DONE
- AdminGraphAnalytics: Graph statistics - DONE
- **Missing:** LLM model configuration UI
- **Missing:** User & permission management
- **Missing:** System configuration UI
- **Missing:** Full monitoring dashboard

---

## Target Features

### 1. LLM Model Configuration UI

```tsx
// Admin can switch LLM models without code changes
interface LLMConfig {
    provider: "ollama" | "alibaba" | "openai";
    model_generation: string;
    model_extraction: string;
    model_embedding: string;
    temperature: number;
    max_tokens: number;
    budget_limit_monthly: number;
}
```

**Features:**
- Model selection dropdown (per task type)
- Provider configuration (API keys, endpoints)
- Budget limits per provider
- A/B testing configuration
- Model performance comparison

### 2. User & Permission Management

```tsx
// RBAC System
interface User {
    user_id: string;
    email: string;
    role: "admin" | "user" | "viewer";
    created_at: datetime;
    last_login: datetime;
    document_quota: number;
    query_quota_daily: number;
}

interface Role {
    role_name: string;
    permissions: Permission[];
}

type Permission =
    | "documents:read"
    | "documents:write"
    | "admin:access"
    | "config:edit"
    | "users:manage";
```

**Features:**
- User CRUD operations
- Role assignment
- Permission matrix
- Activity logs per user
- Quota management

### 3. Vector Database Management

```tsx
interface VectorDBConfig {
    qdrant_host: string;
    qdrant_port: number;
    collection_name: string;
    vector_size: number;
    distance_metric: "cosine" | "euclidean" | "dot";
}
```

**Features:**
- Collection management (create/delete)
- Index statistics
- Reindexing trigger
- Backup/restore
- Performance metrics

### 4. Memory Layer Configuration

```tsx
interface MemoryConfig {
    redis_ttl_hours: number;
    consolidation_interval_hours: number;
    decay_rate: number;
    eviction_threshold: number;
    graphiti_enabled: boolean;
}
```

**Features:**
- Layer enable/disable
- TTL configuration
- Consolidation scheduling
- Decay rate adjustment

### 5. System Monitoring Dashboard

```tsx
interface SystemMetrics {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    active_connections: number;
    queries_per_minute: number;
    average_latency_ms: number;
    error_rate: number;
}
```

**Features:**
- Real-time metrics (WebSocket)
- Service health status
- Alert configuration
- Log viewer
- Performance trends

---

## Solution Architecture

### Backend APIs

```python
# src/api/v1/admin/config.py

@router.get("/api/v1/admin/config/llm")
async def get_llm_config() -> LLMConfig:
    """Get current LLM configuration."""

@router.put("/api/v1/admin/config/llm")
async def update_llm_config(config: LLMConfig) -> LLMConfig:
    """Update LLM configuration."""

@router.get("/api/v1/admin/config/memory")
async def get_memory_config() -> MemoryConfig:
    """Get memory layer configuration."""

# src/api/v1/admin/users.py

@router.get("/api/v1/admin/users")
async def list_users() -> List[User]:
    """List all users."""

@router.post("/api/v1/admin/users")
async def create_user(user: UserCreate) -> User:
    """Create new user."""

@router.put("/api/v1/admin/users/{user_id}/role")
async def update_user_role(user_id: str, role: str) -> User:
    """Update user role."""

# src/api/v1/admin/monitoring.py

@router.get("/api/v1/admin/metrics")
async def get_system_metrics() -> SystemMetrics:
    """Get current system metrics."""

@router.websocket("/api/v1/admin/metrics/stream")
async def stream_metrics(websocket: WebSocket):
    """Stream real-time metrics."""
```

### Frontend Pages

```
frontend/src/pages/admin/
├── AdminDashboard.tsx          # Overview with key metrics
├── AdminLLMConfig.tsx          # LLM model configuration
├── AdminUsersPage.tsx          # User management
├── AdminPermissionsPage.tsx    # Role/permission management
├── AdminVectorDBPage.tsx       # Qdrant management
├── AdminMemoryPage.tsx         # Memory layer config
├── AdminMonitoringPage.tsx     # Real-time monitoring
├── AdminLogsPage.tsx           # Log viewer
└── AdminSettingsPage.tsx       # General settings
```

---

## Implementation Tasks

### Phase 1: LLM Configuration UI (8 SP)
- [ ] Backend config API (get/update)
- [ ] Config storage (Redis or file-based)
- [ ] AdminLLMConfig page
- [ ] Model selection components
- [ ] Budget limit UI
- [ ] Tests

### Phase 2: User Management (13 SP)
- [ ] User model and storage
- [ ] User CRUD API
- [ ] Role/permission system
- [ ] AdminUsersPage
- [ ] AdminPermissionsPage
- [ ] Activity logging
- [ ] Authentication integration
- [ ] Tests

### Phase 3: System Configuration (5 SP)
- [ ] VectorDB config API
- [ ] Memory config API
- [ ] AdminVectorDBPage
- [ ] AdminMemoryPage
- [ ] Configuration export/import
- [ ] Tests

### Phase 4: Monitoring Dashboard (8 SP)
- [ ] Metrics collection service
- [ ] WebSocket streaming
- [ ] AdminMonitoringPage
- [ ] AdminLogsPage
- [ ] Alert configuration
- [ ] Grafana integration
- [ ] Tests

---

## Acceptance Criteria

- [ ] Admin can change LLM models without code changes
- [ ] Admin can manage users and roles
- [ ] Permission system restricts access correctly
- [ ] Vector database stats visible
- [ ] Memory configuration adjustable
- [ ] Real-time metrics displayed
- [ ] Logs searchable and filterable
- [ ] Configuration exportable as YAML/JSON
- [ ] 80%+ test coverage

---

## Security Considerations

- **Authentication:** Admin endpoints require admin role
- **API Keys:** Encrypted storage, masked display
- **Audit Trail:** All config changes logged
- **Rate Limiting:** Prevent brute force
- **Input Validation:** Strict config validation

---

## Affected Files

```
src/api/v1/admin/
├── config.py                   # NEW: Config endpoints
├── users.py                    # NEW: User management
├── monitoring.py               # NEW: Metrics endpoints
└── __init__.py

src/core/
├── rbac.py                     # NEW: RBAC system
├── config_store.py             # NEW: Config persistence
└── auth.py                     # UPDATE: Add admin checks

frontend/src/pages/admin/       # NEW: Admin pages
frontend/src/components/admin/  # NEW: Admin components
```

---

## Dependencies

- Authentication system (JWT or session-based)
- Prometheus/Grafana (metrics)
- Config storage backend (Redis or file)

---

## Estimated Effort

**Story Points:** 34 SP

**Breakdown:**
- Phase 1 (LLM Config): 8 SP
- Phase 2 (Users): 13 SP
- Phase 3 (System Config): 5 SP
- Phase 4 (Monitoring): 8 SP

---

## References

- [SPRINT_PLAN.md - Sprint 11](../sprints/SPRINT_PLAN.md#sprint-11)

---

## Target Sprint

**Recommended:** Sprint 40+ (lower priority, foundational features first)

---

**Last Updated:** 2025-12-04
