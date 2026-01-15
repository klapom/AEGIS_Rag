# Admin API Reference

**Last Updated:** 2026-01-15 (Sprint 97-98 Plan)
**Status:** Planned - Sprint 97-98 Implementation
**API Version:** v1
**Authentication:** Bearer token (OAuth 2.0) or API key

---

## Overview

This document describes the REST API endpoints for AegisRAG admin operations, including:

- **Skill Management** (Sprint 97)
- **GDPR & Compliance** (Sprint 98)
- **Agent Monitoring** (Sprint 98)
- **Audit Trail** (Sprint 98)

All endpoints use JSON for request/response bodies and follow RESTful conventions.

---

## Base URL

```
https://api.aegis-rag.com/api/v1/admin
```

**Local development:**
```
http://localhost:8000/api/v1/admin
```

---

## Authentication

### Bearer Token

Include JWT token in Authorization header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     https://api.aegis-rag.com/api/v1/admin/skills
```

### API Key

Include API key in header or query parameter:

```bash
# Header
curl -H "X-API-Key: sk_live_abc123..." \
     https://api.aegis-rag.com/api/v1/admin/skills

# Query parameter
curl "https://api.aegis-rag.com/api/v1/admin/skills?api_key=sk_live_abc123..."
```

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "error": "ValidationError",
  "detail": "Validation Error",
  "status_code": 400,
  "errors": [
    {
      "field": "config.embedding.dimension",
      "message": "Value must be 1024 or 512"
    }
  ],
  "timestamp": "2026-01-15T14:25:32Z",
  "request_id": "req_7a3f9b..."
}
```

### Common Status Codes

| Code | Meaning | Retry? |
|------|---------|--------|
| 200 | Success | N/A |
| 201 | Created | N/A |
| 400 | Bad request (validation error) | No |
| 401 | Unauthorized (auth failed) | No |
| 403 | Forbidden (insufficient permissions) | No |
| 404 | Not found | No |
| 429 | Rate limited | Yes (after delay) |
| 500 | Server error | Yes (with backoff) |
| 503 | Service unavailable | Yes (with backoff) |

---

# Skill Management Endpoints

## 1. List Skills

**Endpoint:**
```http
GET /skills
```

**Description:** Retrieve all available skills with filtering and pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| search | string | No | - | Search by skill name or description (partial match) |
| status | enum | No | "all" | Filter by status: "active", "inactive", or "all" |
| page | integer | No | 1 | Page number for pagination |
| limit | integer | No | 12 | Results per page (max 100) |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/skills?search=retrieval&status=active&page=1&limit=10" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "skills": [
    {
      "name": "retrieval",
      "version": "1.2.0",
      "description": "Vector & graph retrieval with hybrid search",
      "author": "AegisRAG Core",
      "is_active": true,
      "tools_count": 3,
      "triggers_count": 4,
      "icon": "🔍",
      "activation_count": 1247,
      "last_activated": "2026-01-15T14:23:45Z"
    },
    {
      "name": "web_search",
      "version": "1.1.0",
      "description": "Web browsing and search",
      "author": "AegisRAG Core",
      "is_active": true,
      "tools_count": 2,
      "triggers_count": 5,
      "icon": "🌐",
      "activation_count": 892,
      "last_activated": "2026-01-15T14:22:30Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 24,
    "pages": 3
  }
}
```

**Status Codes:**
- 200 OK - Skills retrieved successfully
- 400 Bad Request - Invalid parameters
- 401 Unauthorized - Auth required

---

## 2. Get Skill Details

**Endpoint:**
```http
GET /skills/{skill_name}
```

**Description:** Retrieve full details for a specific skill.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| skill_name | string | Name of skill (e.g., "retrieval") |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/skills/retrieval" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "name": "retrieval",
  "version": "1.2.0",
  "description": "Vector & graph retrieval with hybrid search",
  "author": "AegisRAG Core",
  "triggers": ["search", "find", "lookup", "retrieve"],
  "tools": [
    {
      "name": "vector_search",
      "status": "authorized"
    },
    {
      "name": "graph_query",
      "status": "authorized"
    },
    {
      "name": "reranking",
      "status": "authorized"
    }
  ],
  "dependencies": ["qdrant", "neo4j", "embedding_service"],
  "permissions": [
    "read_vectors",
    "query_graph",
    "access_embeddings"
  ],
  "config": {
    "embedding": {
      "model": "bge-m3",
      "dimension": 1024
    },
    "search": {
      "top_k": 10,
      "modes": ["vector", "hybrid"],
      "rrf_k": 60
    },
    "neo4j": {
      "max_hops": 2,
      "entity_limit": 50
    },
    "reranking": {
      "enabled": true,
      "model": "cross-encoder/ms-marco",
      "top_n": 5
    }
  },
  "instructions": "# Retrieval Skill\n\nVector and graph-based document retrieval...",
  "is_active": true,
  "activation_count": 1247,
  "last_activated": "2026-01-15T14:23:45Z",
  "metrics": {
    "success_rate": 0.987,
    "avg_duration_ms": 125,
    "p95_duration_ms": 340,
    "uptime_percent": 99.8
  }
}
```

**Status Codes:**
- 200 OK - Skill details retrieved
- 404 Not Found - Skill doesn't exist
- 401 Unauthorized - Auth required

---

## 3. Activate Skill

**Endpoint:**
```http
POST /skills/{skill_name}/activate
```

**Description:** Activate a skill (make it available for use).

**Request Body:** None

**Example Request:**

```bash
curl -X POST "https://api.aegis-rag.com/api/v1/admin/skills/retrieval/activate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Example Response:**

```json
{
  "status": "activated",
  "skill_name": "retrieval",
  "instructions_length": 1247,
  "timestamp": "2026-01-15T14:25:32Z"
}
```

**Status Codes:**
- 200 OK - Skill activated
- 400 Bad Request - Activation failed (check response for reason)
- 404 Not Found - Skill doesn't exist
- 409 Conflict - Skill already active

---

## 4. Deactivate Skill

**Endpoint:**
```http
POST /skills/{skill_name}/deactivate
```

**Description:** Deactivate a skill (no longer available).

**Request Body:** None

**Example Request:**

```bash
curl -X POST "https://api.aegis-rag.com/api/v1/admin/skills/retrieval/deactivate" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "status": "deactivated",
  "skill_name": "retrieval",
  "timestamp": "2026-01-15T14:25:32Z"
}
```

**Status Codes:**
- 200 OK - Skill deactivated
- 404 Not Found - Skill doesn't exist
- 409 Conflict - Skill already inactive

---

## 5. Get Skill Configuration

**Endpoint:**
```http
GET /skills/{skill_name}/config
```

**Description:** Get current YAML configuration for a skill.

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/skills/retrieval/config" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "embedding": {
    "model": "bge-m3",
    "dimension": 1024
  },
  "search": {
    "top_k": 10,
    "modes": ["vector", "hybrid"],
    "rrf_k": 60
  },
  "neo4j": {
    "max_hops": 2,
    "entity_limit": 50
  },
  "reranking": {
    "enabled": true,
    "model": "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "top_n": 5
  }
}
```

**Status Codes:**
- 200 OK - Config retrieved
- 404 Not Found - Skill doesn't exist

---

## 6. Update Skill Configuration

**Endpoint:**
```http
PUT /skills/{skill_name}/config
```

**Description:** Update skill YAML configuration.

**Request Body:**

```json
{
  "embedding": {
    "model": "bge-m3",
    "dimension": 1024
  },
  "search": {
    "top_k": 15,
    "modes": ["vector", "hybrid"],
    "rrf_k": 60
  }
}
```

**Example Request:**

```bash
curl -X PUT "https://api.aegis-rag.com/api/v1/admin/skills/retrieval/config" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "embedding": {"model": "bge-m3", "dimension": 1024},
    "search": {"top_k": 15, "modes": ["vector", "hybrid"]}
  }'
```

**Example Response:**

```json
{
  "status": "updated",
  "skill_name": "retrieval",
  "config": {
    "embedding": {"model": "bge-m3", "dimension": 1024},
    "search": {"top_k": 15, "modes": ["vector", "hybrid"]}
  },
  "timestamp": "2026-01-15T14:25:32Z"
}
```

**Status Codes:**
- 200 OK - Config updated and skill reloaded
- 400 Bad Request - Validation errors (see error details)
- 404 Not Found - Skill doesn't exist

---

## 7. Validate Skill Configuration

**Endpoint:**
```http
POST /skills/{skill_name}/config/validate
```

**Description:** Validate configuration without saving.

**Request Body:** Configuration object (same as PUT)

**Example Request:**

```bash
curl -X POST "https://api.aegis-rag.com/api/v1/admin/skills/retrieval/config/validate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "embedding": {"model": "bge-m3", "dimension": 1024},
    "search": {"top_k": 15}
  }'
```

**Example Response:**

```json
{
  "valid": false,
  "errors": [
    {
      "field": "search.top_k",
      "message": "Value must be between 1 and 50"
    }
  ],
  "warnings": [
    {
      "field": "search.top_k",
      "message": "Value > 10 may increase latency"
    }
  ]
}
```

**Status Codes:**
- 200 OK - Validation complete (check valid field)
- 404 Not Found - Skill doesn't exist

---

## 8. Get Tool Authorization

**Endpoint:**
```http
GET /skills/{skill_name}/tools
```

**Description:** Get authorized tools for a skill.

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/skills/retrieval/tools" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "skill_name": "retrieval",
  "tools": [
    {
      "name": "vector_search",
      "access_level": "standard",
      "rate_limit": "100/min",
      "domain_restrictions": {
        "allowed": ["*.wikipedia.org", "*.arxiv.org"],
        "blocked": []
      }
    },
    {
      "name": "graph_query",
      "access_level": "standard",
      "rate_limit": null
    },
    {
      "name": "reranking",
      "access_level": "standard",
      "rate_limit": null
    }
  ]
}
```

**Status Codes:**
- 200 OK - Tools retrieved
- 404 Not Found - Skill doesn't exist

---

## 9. Update Tool Authorization

**Endpoint:**
```http
PUT /skills/{skill_name}/tools/{tool_name}
```

**Description:** Update authorization for a specific tool in a skill.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| skill_name | string | Name of skill |
| tool_name | string | Name of tool (e.g., "web_search") |

**Request Body:**

```json
{
  "access_level": "elevated",
  "rate_limit": "60/min",
  "domain_restrictions": {
    "allowed": ["*.wikipedia.org", "*.github.com"],
    "blocked": ["*.malware.com"]
  }
}
```

**Example Request:**

```bash
curl -X PUT "https://api.aegis-rag.com/api/v1/admin/skills/research/tools/web_search" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "access_level": "standard",
    "rate_limit": "60/min",
    "domain_restrictions": {
      "allowed": ["*.wikipedia.org"],
      "blocked": []
    }
  }'
```

**Example Response:**

```json
{
  "status": "updated",
  "skill_name": "research",
  "tool_name": "web_search",
  "authorization": {
    "access_level": "standard",
    "rate_limit": "60/min",
    "domain_restrictions": {
      "allowed": ["*.wikipedia.org"],
      "blocked": []
    }
  },
  "timestamp": "2026-01-15T14:25:32Z"
}
```

**Status Codes:**
- 200 OK - Authorization updated
- 400 Bad Request - Invalid access level or rate limit
- 404 Not Found - Skill or tool doesn't exist

---

# GDPR & Compliance Endpoints

## 10. Create Consent Record

**Endpoint:**
```http
POST /gdpr/consents
```

**Description:** Create a new GDPR consent record.

**Request Body:**

```json
{
  "user_id": "user_123",
  "legal_basis": "consent",
  "data_categories": ["identifier", "contact"],
  "valid_from": "2026-01-15",
  "valid_until": "2027-01-15",
  "skill_restrictions": []
}
```

**Example Request:**

```bash
curl -X POST "https://api.aegis-rag.com/api/v1/admin/gdpr/consents" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "legal_basis": "consent",
    "data_categories": ["identifier", "contact"],
    "valid_from": "2026-01-15"
  }'
```

**Example Response:**

```json
{
  "consent_id": "consent_7a3f9b",
  "user_id": "user_123",
  "legal_basis": "consent",
  "data_categories": ["identifier", "contact"],
  "valid_from": "2026-01-15T00:00:00Z",
  "valid_until": null,
  "skill_restrictions": [],
  "created_at": "2026-01-15T14:25:32Z",
  "created_by": "admin_user"
}
```

**Status Codes:**
- 201 Created - Consent record created
- 400 Bad Request - Invalid legal basis or data categories
- 409 Conflict - User already has consent for this basis

---

## 11. List Consents

**Endpoint:**
```http
GET /gdpr/consents
```

**Description:** List consent records with filtering.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | No | Filter by user |
| status | enum | No | Filter: "active", "withdrawn", "expired" |
| page | integer | No | Page number |
| limit | integer | No | Results per page |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/gdpr/consents?status=active&limit=10" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "consents": [
    {
      "consent_id": "consent_7a3f9b",
      "user_id": "user_123",
      "legal_basis": "consent",
      "data_categories": ["identifier", "contact"],
      "status": "active",
      "valid_from": "2026-01-15T00:00:00Z",
      "valid_until": null,
      "created_at": "2026-01-15T14:25:32Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 47
  }
}
```

**Status Codes:**
- 200 OK - Consents retrieved
- 400 Bad Request - Invalid filter parameters

---

## 12. Withdraw Consent

**Endpoint:**
```http
DELETE /gdpr/consents/{consent_id}
```

**Description:** Withdraw a consent record.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| consent_id | string | ID of consent to withdraw |

**Example Request:**

```bash
curl -X DELETE "https://api.aegis-rag.com/api/v1/admin/gdpr/consents/consent_7a3f9b" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "status": "withdrawn",
  "consent_id": "consent_7a3f9b",
  "user_id": "user_123",
  "withdrawn_at": "2026-01-15T14:30:00Z"
}
```

**Status Codes:**
- 200 OK - Consent withdrawn
- 404 Not Found - Consent doesn't exist

---

## 13. Submit Erasure Request

**Endpoint:**
```http
POST /gdpr/erasure-request
```

**Description:** Submit a right-to-erasure (Art. 17) request.

**Request Body:**

```json
{
  "user_id": "user_123",
  "scope": "all",
  "justification": "User requested deletion"
}
```

**Example Request:**

```bash
curl -X POST "https://api.aegis-rag.com/api/v1/admin/gdpr/erasure-request" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "scope": "all"
  }'
```

**Example Response:**

```json
{
  "request_id": "req_9e1b4f",
  "user_id": "user_123",
  "request_type": "erasure",
  "status": "pending_review",
  "scope": "all",
  "submitted_at": "2026-01-15T14:25:32Z",
  "sla_deadline": "2026-02-14T14:25:32Z",
  "estimated_records": 42
}
```

**Status Codes:**
- 201 Created - Request submitted
- 400 Bad Request - Invalid scope

---

## 14. Get Data Export

**Endpoint:**
```http
GET /gdpr/data-export
```

**Description:** Export all data for a user (Art. 15 & 20).

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User to export |
| format | enum | No | "json" (default) or "csv" |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/gdpr/data-export?user_id=user_123&format=json" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "user_id": "user_123",
  "export_id": "exp_5d2c8a",
  "created_at": "2026-01-15T14:25:32Z",
  "expires_at": "2026-02-14T14:25:32Z",
  "download_url": "https://api.aegis-rag.com/exports/exp_5d2c8a/user_123_export.json",
  "data_categories": {
    "identifier": 1,
    "contact": 1,
    "behavioral": 5
  }
}
```

**Status Codes:**
- 200 OK - Export created
- 404 Not Found - User doesn't exist

---

# Audit Trail Endpoints

## 15. Query Audit Events

**Endpoint:**
```http
GET /audit/events
```

**Description:** Query audit logs with filtering.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| start_time | ISO8601 | No | Start timestamp (default: 24h ago) |
| end_time | ISO8601 | No | End timestamp (default: now) |
| event_type | string | No | Filter by type: SKILL_EXECUTED, DATA_READ, etc. |
| actor_id | string | No | Filter by actor |
| page | integer | No | Page number |
| limit | integer | No | Results per page (max 100) |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/audit/events?event_type=SKILL_EXECUTED&limit=20" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "events": [
    {
      "event_id": "evt_7a3f9b",
      "timestamp": "2026-01-15T14:25:32Z",
      "event_type": "SKILL_EXECUTED",
      "actor": "user_123",
      "resource": "retrieval_skill",
      "outcome": "success",
      "duration_ms": 320,
      "hash": "7a3f9b...",
      "chain_verified": true
    },
    {
      "event_id": "evt_5d2c8a",
      "timestamp": "2026-01-15T14:25:30Z",
      "event_type": "DATA_READ",
      "actor": "retrieval_skill",
      "resource": "document_7f3a",
      "outcome": "success",
      "data_categories": ["identifier", "contact"],
      "hash": "5d2c8a...",
      "chain_verified": true
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 14247
  }
}
```

**Status Codes:**
- 200 OK - Events retrieved
- 400 Bad Request - Invalid time range or parameters

---

## 16. Verify Audit Integrity

**Endpoint:**
```http
POST /audit/verify-integrity
```

**Description:** Verify audit chain integrity (detect tampering).

**Request Body:**

```json
{
  "start_time": "2026-01-01T00:00:00Z",
  "end_time": "2026-01-15T23:59:59Z"
}
```

**Example Request:**

```bash
curl -X POST "https://api.aegis-rag.com/api/v1/admin/audit/verify-integrity" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2026-01-01T00:00:00Z",
    "end_time": "2026-01-15T23:59:59Z"
  }'
```

**Example Response:**

```json
{
  "verified": true,
  "events_checked": 14247,
  "timestamp": "2026-01-15T14:30:00Z",
  "summary": "All hashes verified. No tampering detected."
}
```

**Status Codes:**
- 200 OK - Verification complete
- 400 Bad Request - Invalid time range

---

## 17. Export Audit Logs

**Endpoint:**
```http
GET /audit/export
```

**Description:** Export audit logs for external audit.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| start_time | ISO8601 | Yes | Start timestamp |
| end_time | ISO8601 | Yes | End timestamp |
| format | enum | No | "json" (default), "csv", or "pdf" |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/audit/export?start_time=2026-01-01T00:00:00Z&end_time=2026-01-31T23:59:59Z&format=csv" \
  -H "Authorization: Bearer <token>"
```

**Response:** Binary file (CSV, JSON, or PDF)

**Status Codes:**
- 200 OK - Export generated
- 400 Bad Request - Invalid parameters

---

# Agent Monitoring Endpoints

## 18. List Agents

**Endpoint:**
```http
GET /agents
```

**Description:** List all agents in the system.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| level | enum | No | Filter: "executive", "manager", "worker" |
| status | enum | No | Filter: "active", "idle", "error" |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/agents?level=worker" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "agents": [
    {
      "agent_id": "w1_vector",
      "name": "VectorSearch",
      "level": "worker",
      "parent": "mgr_001",
      "status": "active",
      "tasks_active": 0,
      "tasks_completed": 142,
      "success_rate": 0.987,
      "uptime_percent": 99.8,
      "memory_mb": 234
    }
  ],
  "total": 9
}
```

**Status Codes:**
- 200 OK - Agents retrieved

---

## 19. Get Agent Hierarchy

**Endpoint:**
```http
GET /agents/hierarchy
```

**Description:** Get agent hierarchy tree (Executive→Manager→Worker).

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/agents/hierarchy" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "executive": {
    "agent_id": "exec_001",
    "name": "Director",
    "children": [
      {
        "agent_id": "mgr_001",
        "name": "ResearchManager",
        "children": [
          {
            "agent_id": "w1_vector",
            "name": "VectorSearch",
            "status": "idle"
          },
          {
            "agent_id": "w2_web",
            "name": "WebSearch",
            "status": "active"
          }
        ]
      }
    ]
  }
}
```

**Status Codes:**
- 200 OK - Hierarchy retrieved

---

## 20. Get MessageBus Events

**Endpoint:**
```http
GET /agents/messages
```

**Description:** Get recent MessageBus events.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| time_range | string | No | "1h", "6h", "24h" (default: "1h") |
| agent_id | string | No | Filter by agent |
| message_type | string | No | Filter by type (SKILL_REQUEST, etc.) |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/agents/messages?time_range=1h&message_type=SKILL_REQUEST" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "messages": [
    {
      "message_id": "msg_7a3f9b",
      "timestamp": "2026-01-15T14:25:32Z",
      "from_agent": "mgr_001",
      "to_agent": "w1_vector",
      "message_type": "SKILL_REQUEST",
      "latency_ms": 8,
      "status": "delivered"
    }
  ],
  "stats": {
    "total": 1247,
    "by_type": {
      "SKILL_REQUEST": 412,
      "SKILL_RESPONSE": 412,
      "PHASE_UPDATE": 5
    }
  }
}
```

**Status Codes:**
- 200 OK - Messages retrieved

---

## 21. Get Agent Metrics

**Endpoint:**
```http
GET /agents/{agent_id}/metrics
```

**Description:** Get performance metrics for a specific agent.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| agent_id | string | Agent ID (e.g., "mgr_001") |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/agents/mgr_001/metrics" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "agent_id": "mgr_001",
  "name": "ResearchManager",
  "uptime_percent": 99.8,
  "tasks_completed": 142,
  "success_rate": 0.986,
  "failures": 2,
  "avg_task_duration_ms": 1120,
  "p50_task_duration_ms": 890,
  "p95_task_duration_ms": 2340,
  "memory_mb": 234,
  "cpu_percent": 3.5,
  "errors_last_24h": 2
}
```

**Status Codes:**
- 200 OK - Metrics retrieved
- 404 Not Found - Agent doesn't exist

---

## 22. Get Agent Logs

**Endpoint:**
```http
GET /agents/{agent_id}/logs
```

**Description:** Get recent logs for an agent.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| level | enum | No | "debug", "info", "warning", "error" |
| limit | integer | No | Max logs to return (default: 100) |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/agents/w1_vector/logs?level=error&limit=50" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "agent_id": "w1_vector",
  "logs": [
    {
      "timestamp": "2026-01-15T02:14:30Z",
      "level": "error",
      "message": "Qdrant connection timeout after 5000ms",
      "context": {
        "query": "What is X?",
        "duration_ms": 5040
      }
    }
  ],
  "total": 45
}
```

**Status Codes:**
- 200 OK - Logs retrieved
- 404 Not Found - Agent doesn't exist

---

## 23. Get Orchestration Status

**Endpoint:**
```http
GET /orchestration/active
```

**Description:** Get status of active orchestrations (multi-agent workflows).

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/orchestration/active" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "orchestrations": [
    {
      "orchestration_id": "orch_7a2b",
      "user_id": "user_123",
      "query": "What is quantum computing?",
      "phase": "2/3",
      "phase_name": "Aggregation",
      "progress_percent": 67,
      "started_at": "2026-01-15T14:23:45Z",
      "duration_ms": 4120,
      "active_agents": ["mgr_001", "w1_vector", "w2_web"],
      "status": "in_progress"
    }
  ],
  "total": 2
}
```

**Status Codes:**
- 200 OK - Orchestrations retrieved

---

## 24. Get Orchestration Trace

**Endpoint:**
```http
GET /orchestration/{orchestration_id}/trace
```

**Description:** Get detailed trace of an orchestration's execution.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| orchestration_id | string | Orchestration ID |

**Example Request:**

```bash
curl -X GET "https://api.aegis-rag.com/api/v1/admin/orchestration/orch_7a2b/trace" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "orchestration_id": "orch_7a2b",
  "trace": [
    {
      "timestamp": "2026-01-15T14:23:45.100Z",
      "event": "ORCHESTRATION_START",
      "query": "What is quantum computing?"
    },
    {
      "timestamp": "2026-01-15T14:23:45.150Z",
      "event": "INTENT_CLASSIFICATION",
      "result": "RESEARCH (confidence: 0.92)"
    },
    {
      "timestamp": "2026-01-15T14:23:45.203Z",
      "event": "SKILL_ROUTED",
      "skills": ["retrieval", "web_search", "synthesis"]
    },
    {
      "timestamp": "2026-01-15T14:23:45.524Z",
      "event": "RETRIEVAL_COMPLETE",
      "documents": 8
    },
    {
      "timestamp": "2026-01-15T14:23:47.400Z",
      "event": "ORCHESTRATION_COMPLETE",
      "total_duration_ms": 2300
    }
  ]
}
```

**Status Codes:**
- 200 OK - Trace retrieved
- 404 Not Found - Orchestration doesn't exist

---

## Rate Limiting

**Rate limits:**
- 1,000 requests/minute per API key (burst: 100)
- Admin endpoints have higher limits than user endpoints

**Rate limit headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1642258932
```

**When rate limited (429):**
```json
{
  "error": "TooManyRequests",
  "detail": "Rate limit exceeded",
  "status_code": 429,
  "retry_after": 45
}
```

---

## Pagination

**All list endpoints support pagination:**

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 47,
    "pages": 5
  }
}
```

**Query parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-15 | Initial API documentation (Sprint 97-98) |

---

## See Also

- **[Skill Management Guide](../guides/SKILL_MANAGEMENT_GUIDE.md)** - UI guide for skill management
- **[Governance & Compliance Guide](../guides/GOVERNANCE_COMPLIANCE_GUIDE.md)** - GDPR/Audit guide
- **[Agent Monitoring Guide](../guides/AGENT_MONITORING_GUIDE.md)** - Agent monitoring guide

---

**Document:** ADMIN_API_REFERENCE.md
**Last Updated:** 2026-01-15 (Sprint 97-98 Plan)
**Status:** Planned - Ready for Sprint 97-98 Implementation
**Audience:** Backend developers, Integration engineers, System administrators
**Maintainer:** Documentation Agent

---
