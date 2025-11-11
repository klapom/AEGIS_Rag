# API Error Responses Documentation

**Sprint 22 Feature 22.2.2: Standardized API Error Responses**

All API endpoints return errors in a consistent, standardized format with request IDs for log correlation and error codes for programmatic handling.

---

## Error Response Format

All error responses follow this structure:

```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "value",
      "additional": "context"
    },
    "request_id": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
    "timestamp": "2025-11-11T14:30:00.123456Z",
    "path": "/api/v1/endpoint"
  }
}
```

### Fields

- **`code`** (string, required): Machine-readable error code from `ErrorCode` enum
- **`message`** (string, required): Human-readable error description
- **`details`** (object, optional): Additional context about the error
- **`request_id`** (string, required): Unique request ID for log correlation
- **`timestamp`** (string, required): ISO 8601 timestamp when error occurred
- **`path`** (string, required): API endpoint path that generated the error

---

## Error Codes

### 4xx Client Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `BAD_REQUEST` | 400 | Invalid request format or parameters |
| `UNAUTHORIZED` | 401 | Authentication required or failed |
| `FORBIDDEN` | 403 | Not authorized to access resource |
| `NOT_FOUND` | 404 | Requested resource not found |
| `METHOD_NOT_ALLOWED` | 405 | HTTP method not allowed for endpoint |
| `CONFLICT` | 409 | Request conflicts with current state |
| `UNPROCESSABLE_ENTITY` | 422 | Request validation failed (Pydantic) |
| `TOO_MANY_REQUESTS` | 429 | Rate limit exceeded |

### 5xx Server Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `GATEWAY_TIMEOUT` | 504 | Gateway timeout |

### Business Logic Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_FILE_FORMAT` | 400 | Unsupported file format |
| `FILE_TOO_LARGE` | 413 | File size exceeds maximum |
| `FILE_NOT_FOUND` | 404 | Requested file does not exist |
| `INGESTION_FAILED` | 500 | Document ingestion failed |
| `VECTOR_SEARCH_FAILED` | 500 | Vector search operation failed |
| `GRAPH_QUERY_FAILED` | 500 | Graph query operation failed |
| `DATABASE_CONNECTION_FAILED` | 503 | Database connection failed |
| `VALIDATION_FAILED` | 400 | Input validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |

---

## Example Error Responses

### 1. Validation Error (Missing Required Field)

**Request:**
```bash
POST /api/v1/retrieval/search
Content-Type: application/json

{}
```

**Response:** `422 Unprocessable Entity`
```json
{
  "error": {
    "code": "UNPROCESSABLE_ENTITY",
    "message": "Request validation failed",
    "details": {
      "validation_errors": [
        {
          "loc": ["body", "query"],
          "msg": "Field required",
          "type": "missing"
        }
      ]
    },
    "request_id": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
    "timestamp": "2025-11-11T14:30:00.123456Z",
    "path": "/api/v1/retrieval/search"
  }
}
```

### 2. Invalid File Format

**Request:**
```bash
POST /api/v1/retrieval/upload
Content-Type: multipart/form-data

file=document.xyz
```

**Response:** `400 Bad Request`
```json
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "Invalid file format: document.xyz",
    "details": {
      "filename": "document.xyz",
      "expected_formats": [".pdf", ".docx", ".txt", ".md"]
    },
    "request_id": "b2c3d4e5-f6g7-8h9i-0j1k-l2m3n4o5p6q7",
    "timestamp": "2025-11-11T14:31:15.456789Z",
    "path": "/api/v1/retrieval/upload"
  }
}
```

### 3. File Too Large

**Request:**
```bash
POST /api/v1/retrieval/upload
Content-Type: multipart/form-data

file=huge_document.pdf (150MB)
```

**Response:** `413 Payload Too Large`
```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File too large: huge_document.pdf (150.00MB > 100MB)",
    "details": {
      "filename": "huge_document.pdf",
      "size_mb": 150.0,
      "max_size_mb": 100.0
    },
    "request_id": "c3d4e5f6-g7h8-9i0j-1k2l-m3n4o5p6q7r8",
    "timestamp": "2025-11-11T14:32:30.789012Z",
    "path": "/api/v1/retrieval/upload"
  }
}
```

### 4. Vector Search Failed

**Request:**
```bash
POST /api/v1/retrieval/search
Content-Type: application/json

{
  "query": "test query",
  "search_type": "vector"
}
```

**Response:** `500 Internal Server Error`
```json
{
  "error": {
    "code": "VECTOR_SEARCH_FAILED",
    "message": "Vector search failed: Qdrant connection timeout",
    "details": {
      "query": "test query",
      "reason": "Qdrant connection timeout"
    },
    "request_id": "d4e5f6g7-h8i9-0j1k-2l3m-n4o5p6q7r8s9",
    "timestamp": "2025-11-11T14:33:45.012345Z",
    "path": "/api/v1/retrieval/search"
  }
}
```

### 5. Rate Limit Exceeded

**Request:**
```bash
POST /api/v1/retrieval/search
Content-Type: application/json

{
  "query": "test query"
}
# (11th request in 1 minute)
```

**Response:** `429 Too Many Requests`
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded: 10 requests per minute",
    "details": {
      "limit": 10,
      "window": "minute"
    },
    "request_id": "e5f6g7h8-i9j0-1k2l-3m4n-o5p6q7r8s9t0",
    "timestamp": "2025-11-11T14:34:00.345678Z",
    "path": "/api/v1/retrieval/search"
  }
}
```

### 6. Resource Not Found

**Request:**
```bash
GET /api/v1/nonexistent-endpoint
```

**Response:** `404 Not Found`
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Not Found",
    "details": null,
    "request_id": "f6g7h8i9-j0k1-2l3m-4n5o-p6q7r8s9t0u1",
    "timestamp": "2025-11-11T14:35:15.678901Z",
    "path": "/api/v1/nonexistent-endpoint"
  }
}
```

### 7. Unauthorized Access

**Request:**
```bash
POST /api/v1/retrieval/ingest
Content-Type: application/json

{
  "input_dir": "./data"
}
# (No Authorization header)
```

**Response:** `401 Unauthorized`
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication failed: Invalid credentials",
    "details": {
      "reason": "Invalid credentials"
    },
    "request_id": "g7h8i9j0-k1l2-3m4n-5o6p-q7r8s9t0u1v2",
    "timestamp": "2025-11-11T14:36:30.901234Z",
    "path": "/api/v1/retrieval/ingest"
  }
}
```

### 8. Database Connection Failed

**Request:**
```bash
POST /api/v1/retrieval/search
Content-Type: application/json

{
  "query": "test query"
}
# (Qdrant is down)
```

**Response:** `503 Service Unavailable`
```json
{
  "error": {
    "code": "DATABASE_CONNECTION_FAILED",
    "message": "Failed to connect to qdrant: Connection refused",
    "details": {
      "database": "qdrant",
      "reason": "Connection refused"
    },
    "request_id": "h8i9j0k1-l2m3-4n5o-6p7q-r8s9t0u1v2w3",
    "timestamp": "2025-11-11T14:37:45.234567Z",
    "path": "/api/v1/retrieval/search"
  }
}
```

---

## Using Request IDs for Debugging

Every error response includes a unique `request_id` that appears in both:
1. **API response** (in the `error.request_id` field)
2. **Server logs** (in all log entries for that request)

### Example Workflow:

1. **User receives error:**
   ```json
   {
     "error": {
       "code": "VECTOR_SEARCH_FAILED",
       "request_id": "d4e5f6g7-h8i9-0j1k-2l3m-n4o5p6q7r8s9",
       ...
     }
   }
   ```

2. **User reports issue with request ID**

3. **Developer searches logs:**
   ```bash
   grep "d4e5f6g7-h8i9-0j1k-2l3m-n4o5p6q7r8s9" /var/log/aegis-rag.log
   ```

4. **Full request trace revealed:**
   ```json
   {"timestamp": "...", "request_id": "d4e5...", "event": "request_started", ...}
   {"timestamp": "...", "request_id": "d4e5...", "event": "vector_search_started", ...}
   {"timestamp": "...", "request_id": "d4e5...", "event": "qdrant_timeout", ...}
   {"timestamp": "...", "request_id": "d4e5...", "event": "vector_search_failed", ...}
   ```

---

## Error Handling Best Practices

### For API Clients:

1. **Check `error.code`** for programmatic handling:
   ```python
   if response.status_code != 200:
       error_code = response.json()["error"]["code"]

       if error_code == "RATE_LIMIT_EXCEEDED":
           # Retry with exponential backoff
           time.sleep(60)
           retry_request()
       elif error_code == "INVALID_FILE_FORMAT":
           # Show user-friendly message
           show_error("Please upload a PDF, DOCX, or TXT file")
       else:
           # Generic error handling
           show_error(response.json()["error"]["message"])
   ```

2. **Log `request_id`** for support requests:
   ```python
   logger.error(
       f"API error: {error['message']} (request_id: {error['request_id']})"
   )
   ```

3. **Parse `details`** for field-level errors:
   ```python
   if error_code == "UNPROCESSABLE_ENTITY":
       for validation_error in error["details"]["validation_errors"]:
           field = ".".join(validation_error["loc"])
           message = validation_error["msg"]
           show_field_error(field, message)
   ```

### For API Developers:

1. **Use custom exceptions** instead of `HTTPException`:
   ```python
   # BAD
   raise HTTPException(status_code=400, detail="Invalid file format")

   # GOOD
   raise InvalidFileFormatError(filename="test.xyz", expected_formats=[".pdf"])
   ```

2. **Include helpful details**:
   ```python
   raise VectorSearchError(
       query=user_query,
       reason="Qdrant connection timeout after 5s"
   )
   ```

3. **Let the global handler format errors** - don't build error responses manually

---

## Testing Error Responses

### Unit Tests (Exception Handlers):
```python
from src.core.exceptions import InvalidFileFormatError

async def test_error_handler():
    exc = InvalidFileFormatError(filename="test.xyz", expected_formats=[".pdf"])
    response = await aegis_exception_handler(mock_request, exc)

    assert response.status_code == 400
    assert "INVALID_FILE_FORMAT" in response.body.decode()
```

### Integration Tests (End-to-End):
```python
def test_api_error_response(client):
    response = client.post("/api/v1/retrieval/search", json={})

    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "UNPROCESSABLE_ENTITY"
    assert "request_id" in data["error"]
```

---

## Migration Guide

### Updating Existing Endpoints:

**Before (Sprint <22):**
```python
@router.post("/endpoint")
async def my_endpoint(request: Request):
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid input")
```

**After (Sprint 22+):**
```python
@router.post("/endpoint")
async def my_endpoint(request: Request):
    if not valid:
        raise ValidationError(field="input", issue="Invalid format")
```

The global exception handler will automatically convert this to:
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Validation failed for field 'input': Invalid format",
    "details": {"field": "input", "issue": "Invalid format"},
    "request_id": "...",
    "timestamp": "...",
    "path": "..."
  }
}
```

---

## See Also

- **Implementation:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\src\api\middleware\exception_handler.py`
- **Error Models:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\src\core\models.py`
- **Custom Exceptions:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\src\core\exceptions.py`
- **Unit Tests:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\tests\unit\api\test_error_responses.py`
- **Integration Tests:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\tests\integration\api\test_error_responses_integration.py`
