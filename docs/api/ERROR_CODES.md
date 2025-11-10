# AEGIS RAG API Error Reference

**Last Updated:** 2025-11-10 (Sprint 21)

---

## Error Response Format

All API errors follow a consistent JSON structure:

```json
{
  "error": "ErrorCodeName",
  "message": "Human-readable error description",
  "details": {
    "field": "additional context",
    "retry_after": 30
  }
}
```

**Fields:**
- `error` (string): Machine-readable error code
- `message` (string): User-friendly error description
- `details` (object, optional): Additional context for debugging

---

## HTTP Status Codes

### 2xx Success

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |

### 4xx Client Errors

| Code | Status | Description |
|------|--------|-------------|
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |

### 5xx Server Errors

| Code | Status | Description |
|------|--------|-------------|
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Service temporarily unavailable |

---

## Error Codes

### Validation Errors (422)

#### `ValidationError`

**Description:** Request validation failed (Pydantic validation).

**Example Response:**
```json
{
  "error": "ValidationError",
  "message": "Request validation failed",
  "details": {
    "errors": [
      {
        "loc": ["body", "query"],
        "msg": "field required",
        "type": "value_error.missing"
      },
      {
        "loc": ["body", "top_k"],
        "msg": "ensure this value is less than or equal to 50",
        "type": "value_error.number.not_le"
      }
    ]
  }
}
```

**Common Causes:**
- Missing required fields
- Invalid field types
- Value out of range
- String too long/short

**Solution:**
- Check request schema in [ENDPOINTS.md](ENDPOINTS.md)
- Validate input before sending request
- Review `details.errors` for specific field issues

---

### Authentication Errors (401)

#### `InvalidToken`

**Description:** JWT token is invalid or expired.

**Example Response:**
```json
{
  "error": "InvalidToken",
  "message": "Authentication token is invalid or expired",
  "details": {
    "token_expired": true,
    "expired_at": "2025-11-10T10:00:00Z"
  }
}
```

**Solution:**
- Refresh JWT token via `/api/v1/auth/token`
- Check token expiration before request

#### `MissingToken`

**Description:** No authentication token provided.

**Example Response:**
```json
{
  "error": "MissingToken",
  "message": "Authentication required. Please provide a valid JWT token.",
  "details": {
    "header_required": "Authorization: Bearer <token>"
  }
}
```

**Solution:**
- Add `Authorization: Bearer <token>` header to request

---

### Rate Limiting Errors (429)

#### `RateLimitExceeded`

**Description:** Too many requests from the same IP/session.

**Example Response:**
```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded. Try again in 45 seconds.",
  "details": {
    "retry_after": 45,
    "limit": 100,
    "window_seconds": 60
  }
}
```

**Solution:**
- Wait `retry_after` seconds before retrying
- Implement exponential backoff
- Use caching to reduce requests

**Rate Limits:**
- Default: 100 requests/minute per IP
- Chat: 20 requests/minute per session
- Admin: 10 requests/minute per IP

---

### Resource Errors (404)

#### `ResourceNotFound`

**Description:** Requested resource does not exist.

**Example Response:**
```json
{
  "error": "ResourceNotFound",
  "message": "Conversation with session_id 'abc123' not found",
  "details": {
    "resource_type": "conversation",
    "session_id": "abc123"
  }
}
```

**Common Cases:**
- Invalid `session_id` in `/api/v1/chat/conversations/{session_id}`
- Non-existent `image_id` in `/api/v1/annotations/images/{image_id}`

**Solution:**
- Verify resource ID exists
- Check for typos in path parameters

#### `EndpointNotFound`

**Description:** API endpoint does not exist.

**Example Response:**
```json
{
  "error": "EndpointNotFound",
  "message": "The requested endpoint does not exist",
  "details": {
    "path": "/api/v1/invalid",
    "available_endpoints": "/docs"
  }
}
```

**Solution:**
- Check API documentation at `/docs`
- Verify HTTP method (GET vs POST)
- Check endpoint spelling

---

### Service Errors (503)

#### `OllamaUnavailable`

**Description:** Ollama LLM service is not responding.

**Example Response:**
```json
{
  "error": "OllamaUnavailable",
  "message": "Failed to connect to Ollama service. Please ensure Ollama is running.",
  "details": {
    "service_url": "http://localhost:11434",
    "retry_after": 10,
    "troubleshooting": "Run 'ollama serve' or check docker-compose"
  }
}
```

**Common Causes:**
- Ollama service not started
- Docker container stopped
- Network connectivity issues

**Solution:**
```bash
# Check Ollama status
curl http://localhost:11434/api/version

# Start Ollama (Docker)
docker-compose up -d ollama

# Start Ollama (native)
ollama serve
```

#### `QdrantUnavailable`

**Description:** Qdrant vector database is not responding.

**Example Response:**
```json
{
  "error": "QdrantUnavailable",
  "message": "Failed to connect to Qdrant database",
  "details": {
    "service_url": "http://localhost:6333",
    "retry_after": 10
  }
}
```

**Solution:**
```bash
# Check Qdrant status
curl http://localhost:6333/health

# Start Qdrant
docker-compose up -d qdrant
```

#### `Neo4jUnavailable`

**Description:** Neo4j graph database is not responding.

**Example Response:**
```json
{
  "error": "Neo4jUnavailable",
  "message": "Failed to connect to Neo4j database",
  "details": {
    "service_uri": "bolt://localhost:7687",
    "retry_after": 10
  }
}
```

**Solution:**
```bash
# Check Neo4j status
curl http://localhost:7474

# Start Neo4j
docker-compose up -d neo4j
```

#### `DoclingUnavailable`

**Description:** Docling container is not running (Sprint 21+).

**Example Response:**
```json
{
  "error": "DoclingUnavailable",
  "message": "Docling container is not running. Start it via docker-compose.",
  "details": {
    "service_url": "http://localhost:8080",
    "start_command": "docker-compose --profile ingestion up -d docling",
    "note": "Docling requires GPU (6GB VRAM)"
  }
}
```

**Solution:**
```bash
# Start Docling container
docker-compose --profile ingestion up -d docling

# Wait for health check
curl http://localhost:8080/health
```

---

### Processing Errors (500)

#### `VectorSearchError`

**Description:** Error during vector search operation.

**Example Response:**
```json
{
  "error": "VectorSearchError",
  "message": "Failed to search vector database",
  "details": {
    "query": "machine learning",
    "collection": "aegis-rag-chunks",
    "inner_error": "Collection not found"
  }
}
```

**Common Causes:**
- Qdrant collection not initialized
- Invalid query embedding
- Collection deleted

**Solution:**
- Run `/api/v1/admin/reindex?confirm=true` to rebuild indexes
- Check Qdrant collection exists: `curl http://localhost:6333/collections`

#### `GraphQueryError`

**Description:** Error during Neo4j graph query.

**Example Response:**
```json
{
  "error": "GraphQueryError",
  "message": "Failed to execute graph query",
  "details": {
    "query": "MATCH (n) RETURN n LIMIT 10",
    "neo4j_error": "NodeNotFound: Node with id 123 not found"
  }
}
```

**Solution:**
- Check Neo4j is running
- Verify graph is populated (run re-indexing if empty)

#### `EmbeddingGenerationError`

**Description:** Failed to generate embeddings.

**Example Response:**
```json
{
  "error": "EmbeddingGenerationError",
  "message": "Failed to generate embeddings with BGE-M3",
  "details": {
    "model": "bge-m3",
    "text_length": 5000,
    "max_length": 8192,
    "suggestion": "Reduce input text length"
  }
}
```

**Common Causes:**
- Input text too long (>8192 tokens)
- Ollama not running
- Model not downloaded

**Solution:**
```bash
# Download BGE-M3 model
ollama pull bge-m3

# Verify model
ollama list | grep bge-m3
```

#### `LLMGenerationError`

**Description:** LLM failed to generate response.

**Example Response:**
```json
{
  "error": "LLMGenerationError",
  "message": "Failed to generate response with llama3.2:8b",
  "details": {
    "model": "llama3.2:8b",
    "error_type": "ModelNotFound",
    "suggestion": "Run 'ollama pull llama3.2:8b'"
  }
}
```

**Solution:**
```bash
# Pull required models
ollama pull llama3.2:3b
ollama pull llama3.2:8b
ollama pull gemma-3-4b-it-GGUF:Q8_0
```

#### `MemoryStorageError`

**Description:** Failed to store/retrieve memory.

**Example Response:**
```json
{
  "error": "MemoryStorageError",
  "message": "Failed to store memory in Redis",
  "details": {
    "operation": "store",
    "key": "user_preference",
    "redis_error": "Connection refused"
  }
}
```

**Solution:**
```bash
# Check Redis status
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

---

### Re-Indexing Errors

#### `ReindexConfirmationRequired`

**Description:** Re-indexing requires explicit confirmation.

**Example Response:**
```json
{
  "error": "ReindexConfirmationRequired",
  "message": "Re-indexing is a destructive operation. Add '?confirm=true' to proceed.",
  "details": {
    "warning": "This will delete all existing indexes",
    "confirm_url": "/api/v1/admin/reindex?confirm=true"
  }
}
```

**Solution:**
- Add `?confirm=true` query parameter to request

#### `ReindexInProgress`

**Description:** Re-indexing is already running.

**Example Response:**
```json
{
  "error": "ReindexInProgress",
  "message": "Re-indexing is already in progress. Please wait for completion.",
  "details": {
    "progress_percent": 45,
    "eta_seconds": 120,
    "current_phase": "embedding"
  }
}
```

**Solution:**
- Wait for current re-indexing to complete
- Monitor progress via SSE stream

#### `NoDocumentsFound`

**Description:** No documents found to index.

**Example Response:**
```json
{
  "error": "NoDocumentsFound",
  "message": "No documents found in input directory",
  "details": {
    "input_dir": "/app/documents",
    "supported_formats": [".pdf", ".txt", ".docx"]
  }
}
```

**Solution:**
- Add documents to input directory
- Check file extensions are supported

---

## Error Handling Best Practices

### Client-Side Retry Logic

```javascript
async function callAPIWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);

      if (response.status === 429) {
        // Rate limit - use Retry-After header
        const retryAfter = parseInt(response.headers.get('X-RateLimit-Reset') || '60');
        await sleep(retryAfter * 1000);
        continue;
      }

      if (response.status >= 500) {
        // Server error - exponential backoff
        await sleep(Math.pow(2, i) * 1000);
        continue;
      }

      if (!response.ok) {
        const error = await response.json();
        throw new APIError(error.error, error.message, error.details);
      }

      return await response.json();

    } catch (error) {
      if (i === maxRetries - 1) throw error;
    }
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

class APIError extends Error {
  constructor(code, message, details) {
    super(message);
    this.code = code;
    this.details = details;
  }
}
```

### Python Error Handling

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class AegisAPIError(Exception):
    """AEGIS RAG API error."""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def call_api(url: str, **kwargs):
    """Call API with retry logic."""
    async with httpx.AsyncClient() as client:
        response = await client.post(url, **kwargs)

        if response.status_code == 429:
            # Rate limit - respect Retry-After
            retry_after = int(response.headers.get('X-RateLimit-Reset', 60))
            raise httpx.HTTPError(f"Rate limited, retry after {retry_after}s")

        if response.status_code >= 500:
            # Server error - retry
            raise httpx.HTTPError(f"Server error: {response.status_code}")

        if response.status_code >= 400:
            # Client error - don't retry
            error_data = response.json()
            raise AegisAPIError(
                code=error_data["error"],
                message=error_data["message"],
                details=error_data.get("details")
            )

        return response.json()

# Usage
try:
    result = await call_api(
        "http://localhost:8000/api/v1/chat",
        json={"query": "What is AEGIS RAG?"}
    )
except AegisAPIError as e:
    if e.code == "OllamaUnavailable":
        print(f"Ollama service is down: {e.message}")
        # Fallback logic
    else:
        print(f"API Error [{e.code}]: {e.message}")
```

---

## Monitoring & Debugging

### Check Service Health

```bash
# All services
curl http://localhost:8000/api/v1/health | jq

# Ollama
curl http://localhost:11434/api/version

# Qdrant
curl http://localhost:6333/health

# Neo4j
curl http://localhost:7474

# Docling
curl http://localhost:8080/health
```

### View Logs

```bash
# API logs
docker-compose logs -f api

# Ollama logs
docker-compose logs -f ollama

# Qdrant logs
docker-compose logs -f qdrant

# Neo4j logs
docker-compose logs -f neo4j

# Docling logs
docker-compose logs -f docling
```

### Prometheus Metrics

```bash
# Error rate
curl http://localhost:9090/api/v1/query?query=aegis_rag_requests_total{status="500"}

# Request latency
curl http://localhost:9090/api/v1/query?query=aegis_rag_request_latency_seconds
```

---

## Support & Troubleshooting

**Common Issues:**
1. **All endpoints return 503:**
   - Check all services are running: `docker-compose ps`
   - Restart services: `docker-compose restart`

2. **Slow response times:**
   - Check Ollama model is loaded: `ollama ps`
   - Monitor GPU usage: `nvidia-smi`
   - Check Prometheus metrics at http://localhost:9090

3. **Intermittent errors:**
   - Check Redis memory: `docker exec aegis-redis redis-cli INFO memory`
   - Check disk space: `df -h`

**For further assistance:**
- Open issue: https://github.com/aegis-rag/aegis-rag/issues
- Check logs: `docker-compose logs`
- Review documentation: http://localhost:8000/docs

---

**Last Updated:** 2025-11-10
**Sprint:** 21
**Maintainer:** Klaus Pommer + Claude Code (documentation-agent)
