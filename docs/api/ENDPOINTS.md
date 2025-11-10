# AEGIS RAG API Reference

**Version:** 1.0.0 (Sprint 21)
**Base URL:** `http://localhost:8000`
**Documentation:** `/docs` (Swagger UI), `/redoc` (ReDoc)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Health & Monitoring](#health--monitoring)
3. [Chat Endpoints](#chat-endpoints)
4. [Retrieval Endpoints](#retrieval-endpoints)
5. [Memory Endpoints](#memory-endpoints)
6. [Admin Endpoints](#admin-endpoints)
7. [Graph Visualization](#graph-visualization)
8. [Graph Analytics](#graph-analytics)
9. [Annotations API](#annotations-api-sprint-21)

---

## Authentication

**Current Status:** JWT authentication framework in place, not enforced in development.

### Get Access Token (Future)

```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=secretpass
```

**Response:**
```json
{
  "access_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Usage in Requests:**
```http
Authorization: Bearer eyJ0eXAi...
```

---

## Health & Monitoring

### Root Endpoint

```http
GET /
```

**Response:**
```json
{
  "name": "AEGIS RAG API",
  "version": "1.0.0",
  "status": "operational",
  "docs": "/docs"
}
```

### Basic Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T10:30:00Z"
}
```

### Detailed Health Check

```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T10:30:00Z",
  "services": {
    "qdrant": {"status": "healthy", "latency_ms": 5.2},
    "neo4j": {"status": "healthy", "latency_ms": 8.1},
    "redis": {"status": "healthy", "latency_ms": 1.3},
    "ollama": {"status": "healthy", "latency_ms": 120.5}
  },
  "memory": {
    "redis": {"hit_rate": 0.85, "keys": 1234},
    "qdrant": {"documents": 5000, "size_mb": 250},
    "neo4j": {"nodes": 15000, "relationships": 45000}
  }
}
```

### Prometheus Metrics

```http
GET /metrics
```

**Response:** Prometheus exposition format
```
# HELP aegis_rag_requests_total Total request count
# TYPE aegis_rag_requests_total counter
aegis_rag_requests_total{method="GET",endpoint="/health",status="200"} 1234

# HELP aegis_rag_request_latency_seconds Request latency
# TYPE aegis_rag_request_latency_seconds histogram
aegis_rag_request_latency_seconds_bucket{method="POST",endpoint="/api/v1/chat",le="0.1"} 450
```

---

## Chat Endpoints

### Send Chat Message (Streaming)

```http
POST /api/v1/chat
Content-Type: application/json

{
  "query": "How does vector search work?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "stream": true,
  "include_sources": true
}
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | User's question |
| `session_id` | string | No | Session ID for conversation history (auto-generated if omitted) |
| `stream` | boolean | No | Enable SSE streaming (default: true) |
| `include_sources` | boolean | No | Include source documents (default: true) |

**Response (Streaming):**

See [SSE_STREAMING.md](SSE_STREAMING.md) for detailed streaming format.

**Response (Non-Streaming):**
```json
{
  "answer": "Vector search uses embeddings to find semantically similar documents...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "intent": "hybrid",
  "sources": [
    {
      "content": "Vector search is a method...",
      "metadata": {
        "file_name": "vector_search.pdf",
        "page": 3
      },
      "score": 0.92
    }
  ],
  "latency_ms": 1250
}
```

**cURL Example:**
```bash
# Streaming (default)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AEGIS RAG?", "stream": true}'

# Non-streaming
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AEGIS RAG?", "stream": false}'
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "query": "How does LightRAG work?",
        "session_id": "my-session-123",
        "stream": False,
        "include_sources": True
    }
)

data = response.json()
print(f"Answer: {data['answer']}")
print(f"Intent: {data['intent']}")
print(f"Sources: {len(data['sources'])} documents")
```

**TypeScript Example:**
```typescript
const response = await fetch('http://localhost:8000/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'Explain hybrid search',
    stream: false,
    include_sources: true
  })
});

const data = await response.json();
console.log(`Answer: ${data.answer}`);
```

### Get Conversation History

```http
GET /api/v1/chat/conversations/{session_id}
```

**Parameters:**
| Name | Type | Location | Description |
|------|------|----------|-------------|
| `session_id` | string | path | Session identifier |

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-11-10T10:00:00Z",
  "updated_at": "2025-11-10T10:15:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What is vector search?",
      "timestamp": "2025-11-10T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Vector search uses embeddings...",
      "timestamp": "2025-11-10T10:00:05Z",
      "intent": "vector",
      "sources": [...]
    }
  ],
  "message_count": 4
}
```

### Search Conversations

```http
POST /api/v1/chat/conversations/search
Content-Type: application/json

{
  "query": "vector search",
  "limit": 10,
  "min_relevance": 0.7
}
```

**Response:**
```json
{
  "results": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "snippet": "...vector search uses embeddings...",
      "relevance_score": 0.92,
      "timestamp": "2025-11-10T10:00:00Z"
    }
  ],
  "total_results": 15
}
```

---

## Retrieval Endpoints

### Hybrid Search

```http
POST /api/v1/retrieval/search
Content-Type: application/json

{
  "query": "machine learning algorithms",
  "mode": "hybrid",
  "top_k": 5,
  "include_scores": true
}
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `mode` | string | No | Search mode: `vector`, `keyword`, `hybrid` (default: `hybrid`) |
| `top_k` | integer | No | Number of results (default: 5, max: 50) |
| `include_scores` | boolean | No | Include relevance scores (default: true) |

**Response:**
```json
{
  "results": [
    {
      "content": "Machine learning is a subset of AI...",
      "metadata": {
        "file_name": "ml_intro.pdf",
        "page": 1,
        "chunk_id": "abc123"
      },
      "score": 0.95,
      "rank": 1
    }
  ],
  "query_time_ms": 85,
  "mode": "hybrid",
  "total_results": 5
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "neural networks",
    "mode": "hybrid",
    "top_k": 10
  }'
```

### Prepare BM25 Index

```http
POST /api/v1/retrieval/prepare-bm25
```

**Description:** Initialize or rebuild BM25 keyword index from Qdrant corpus.

**Response:**
```json
{
  "status": "completed",
  "corpus_size": 5000,
  "index_time_ms": 2500,
  "message": "BM25 index prepared successfully"
}
```

---

## Memory Endpoints

### Store Memory

```http
POST /api/v1/memory
Content-Type: application/json

{
  "session_id": "user-123",
  "key": "user_preference",
  "value": {"theme": "dark", "language": "en"},
  "namespace": "preferences",
  "ttl_seconds": 86400
}
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | Session identifier |
| `key` | string | Yes | Memory key |
| `value` | any | Yes | JSON-serializable value |
| `namespace` | string | No | Memory namespace (default: `default`) |
| `ttl_seconds` | integer | No | Time-to-live in seconds |

**Response:**
```json
{
  "status": "success",
  "key": "user_preference",
  "namespace": "preferences",
  "expires_at": "2025-11-11T10:30:00Z"
}
```

### Retrieve Memory

```http
GET /api/v1/memory?session_id=user-123&key=user_preference&namespace=preferences
```

**Response:**
```json
{
  "key": "user_preference",
  "value": {"theme": "dark", "language": "en"},
  "namespace": "preferences",
  "created_at": "2025-11-10T10:30:00Z",
  "ttl_seconds": 86400
}
```

### Delete Memory

```http
DELETE /api/v1/memory?session_id=user-123&key=user_preference&namespace=preferences
```

**Response:**
```json
{
  "status": "deleted",
  "key": "user_preference",
  "namespace": "preferences"
}
```

---

## Admin Endpoints

**Note:** Admin endpoints require authentication in production.

### Re-Index All Documents (SSE Streaming)

```http
POST /api/v1/admin/reindex?confirm=true&dry_run=false
```

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `confirm` | boolean | Yes | Must be `true` to execute |
| `dry_run` | boolean | No | Simulate without changes (default: `false`) |

**Response (SSE Stream):**

See [SSE_STREAMING.md](SSE_STREAMING.md) for progress event format.

**Example Progress Events:**
```
data: {"status":"in_progress","phase":"initialization","progress_percent":0,"message":"Initializing re-indexing pipeline..."}

data: {"status":"in_progress","phase":"deletion","progress_percent":10,"message":"Deleting old indexes..."}

data: {"status":"in_progress","phase":"chunking","progress_percent":30,"documents_processed":150,"documents_total":500,"message":"Chunking documents..."}

data: {"status":"completed","progress_percent":100,"message":"Re-indexing completed successfully","documents_indexed":500}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/admin/reindex?confirm=true" \
  --no-buffer
```

**Python Example (SSE Client):**
```python
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/api/v1/admin/reindex?confirm=true"
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                print(f"Progress: {data['progress_percent']}% - {data['message']}")
```

### Get System Statistics

```http
GET /api/v1/admin/stats
```

**Response:**
```json
{
  "system": {
    "uptime_seconds": 86400,
    "version": "1.0.0",
    "environment": "production"
  },
  "corpus": {
    "total_documents": 5000,
    "total_chunks": 50000,
    "total_entities": 15000,
    "total_relationships": 45000
  },
  "performance": {
    "avg_query_latency_ms": 250,
    "requests_per_minute": 45,
    "error_rate": 0.01
  },
  "storage": {
    "qdrant_size_mb": 250,
    "neo4j_size_mb": 180,
    "redis_size_mb": 50
  }
}
```

---

## Graph Visualization

### Get Graph Data

```http
GET /api/v1/graph/visualization?query=machine+learning&limit=50&depth=2
```

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | No | Search query to filter graph |
| `limit` | integer | No | Max nodes to return (default: 50, max: 500) |
| `depth` | integer | No | Relationship depth (default: 2, max: 4) |

**Response:**
```json
{
  "nodes": [
    {
      "id": "node_123",
      "label": "Machine Learning",
      "type": "concept",
      "properties": {"importance": 0.95}
    }
  ],
  "edges": [
    {
      "source": "node_123",
      "target": "node_456",
      "relationship": "RELATED_TO",
      "weight": 0.8
    }
  ],
  "metadata": {
    "query_time_ms": 150,
    "total_nodes": 150,
    "total_edges": 300
  }
}
```

---

## Graph Analytics

### Get Community Detection

```http
POST /api/v1/graph/analytics/communities
Content-Type: application/json

{
  "algorithm": "louvain",
  "min_community_size": 5
}
```

**Response:**
```json
{
  "communities": [
    {
      "id": 1,
      "size": 45,
      "members": ["node_123", "node_456", ...],
      "cohesion_score": 0.85
    }
  ],
  "total_communities": 12,
  "modularity_score": 0.72
}
```

### Get Centrality Metrics

```http
GET /api/v1/graph/analytics/centrality?metric=pagerank&top_k=10
```

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `metric` | string | No | Metric: `pagerank`, `betweenness`, `degree` (default: `pagerank`) |
| `top_k` | integer | No | Number of top nodes (default: 10, max: 100) |

**Response:**
```json
{
  "metric": "pagerank",
  "top_nodes": [
    {
      "node_id": "node_123",
      "label": "Machine Learning",
      "score": 0.042
    }
  ],
  "computation_time_ms": 450
}
```

---

## Annotations API (Sprint 21)

### Get Image Annotations

```http
GET /api/v1/annotations/images/{image_id}
```

**Parameters:**
| Name | Type | Location | Description |
|------|------|----------|-------------|
| `image_id` | string | path | Image identifier from Docling |

**Response:**
```json
{
  "image_id": "img_abc123",
  "annotations": [
    {
      "type": "description",
      "text": "A diagram showing neural network architecture",
      "confidence": 0.92,
      "model": "llava:7b-v1.6-mistral-q2_K"
    }
  ],
  "metadata": {
    "source_document": "ml_book.pdf",
    "page": 5,
    "generated_at": "2025-11-10T10:30:00Z"
  }
}
```

### Generate Image Annotations

```http
POST /api/v1/annotations/generate
Content-Type: application/json

{
  "image_id": "img_abc123",
  "image_data": "base64-encoded-image",
  "prompt": "Describe this image in detail"
}
```

**Response:**
```json
{
  "image_id": "img_abc123",
  "annotation": {
    "type": "description",
    "text": "The image shows a convolutional neural network with 3 layers...",
    "confidence": 0.89
  },
  "processing_time_ms": 3500
}
```

---

## Rate Limiting

**Limits (Development):**
- Default: 100 requests/minute per IP
- Chat endpoint: 20 requests/minute per session
- Admin endpoints: 10 requests/minute per IP

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699876543
```

**Rate Limit Exceeded Response:**
```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded. Try again in 45 seconds.",
  "details": {
    "retry_after": 45
  }
}
```

---

## Response Headers

All responses include:
```http
X-Process-Time: 0.125        # Request processing time in seconds
X-Request-ID: uuid           # Unique request identifier (future)
Content-Type: application/json
```

---

## Error Handling

See [ERROR_CODES.md](ERROR_CODES.md) for complete error reference.

**Common HTTP Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable (e.g., Ollama down)

---

## Additional Resources

- **OpenAPI Specification:** http://localhost:8000/docs (Swagger UI)
- **ReDoc Documentation:** http://localhost:8000/redoc
- **SSE Streaming Guide:** [SSE_STREAMING.md](SSE_STREAMING.md)
- **Error Reference:** [ERROR_CODES.md](ERROR_CODES.md)
- **Authentication Guide:** [AUTHENTICATION.md](AUTHENTICATION.md) (future)

---

**Last Updated:** 2025-11-10
**Version:** Sprint 21
**Maintainer:** Klaus Pommer + Claude Code (documentation-agent)
