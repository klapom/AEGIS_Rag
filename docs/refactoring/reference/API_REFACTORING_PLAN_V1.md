# AEGIS RAG - API Refactoring Plan (Pre-Production V1)

**Status:** V1 Pre-Production (Not Live)
**Timeline:** 2-3 Weeks (36-57h total)
**Approach:** Direct fixes, no backward compatibility concerns

---

## Executive Summary

The API layer has grown organically over 21 sprints, leading to inconsistencies in:
- Error response formats (dict vs ErrorResponse model)
- Authentication patterns (required/optional/none)
- Rate limiting (applied inconsistently)
- Validation (gaps in file uploads, pagination)
- Documentation (OpenAPI completeness varies)

**Pre-production advantage:** We can make breaking changes freely since there are no external users yet.

---

## Priority 1: Critical Security Fixes (8-12h)

### P1.1: Fix CORS Configuration (30 min)
**File:** `src/api/main.py:119-125`

**Current Issue:**
```python
allow_origins=["*"]  # Too permissive, even in dev
```

**Fix:**
```python
# In settings.py
ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

# In main.py
allow_origins=settings.ALLOWED_ORIGINS if settings.environment == "development" else [],
```

**Breaking:** No

---

### P1.2: Standardize Error Responses (3-4h)
**Files:** All endpoints

**Current Issue:**
- Some return `ErrorResponse` model (main.py handlers)
- Others return plain dict with "detail"
- No request_id for debugging
- Inconsistent timestamps

**Fix:**
Create `src/api/models/errors.py`:
```python
class StandardErrorResponse(BaseModel):
    error_code: str  # "VALIDATION_ERROR", "INTERNAL_ERROR", etc.
    message: str
    details: dict[str, Any] | None = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str | None = None
    path: str | None = None

def build_error_response(
    error_code: str,
    message: str,
    status_code: int,
    details: dict | None = None,
    request: Request | None = None,
) -> JSONResponse:
    """Build standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content=StandardErrorResponse(
            error_code=error_code,
            message=message,
            details=details,
            request_id=getattr(request.state, "request_id", None) if request else None,
            path=str(request.url) if request else None,
        ).model_dump(mode="json")
    )
```

Update all exception handlers in `main.py` and all endpoints.

**Breaking:** Yes (error format changes, but OK since not live)

---

### P1.3: Add Rate Limiting (2-3h)
**Files:** `src/api/v1/annotations.py`, `src/api/v1/admin.py`

**Current Issue:**
- Annotation endpoints have no rate limiting
- Admin `/stats` endpoint has no rate limiting
- Could be abused for DoS

**Fix:**
```python
@router.get("/document/{document_id}")
@limiter.limit("30/minute")
async def get_document_annotations(...):
    ...

@router.get("/stats")
@limiter.limit("60/minute")
async def get_system_stats(...):
    ...
```

**Breaking:** No

---

### P1.4: Standardize Authentication (2-3h)
**Files:** All endpoints

**Current Issue:**
- `annotations.py`: Uses `get_current_user` (required)
- `retrieval.py`: Uses `get_current_user` with `| None` (optional)
- `chat.py`: No authentication
- Inconsistent parameter naming: `_current_user` vs `current_user`

**Fix:**
Create `src/api/auth/dependencies.py`:
```python
RequireAuth = Depends(get_current_user)  # Returns User, not str | None
OptionalAuth = Depends(get_current_user_optional)  # Returns User | None

# Usage
async def protected_endpoint(user: User = RequireAuth):
    ...

async def optional_auth_endpoint(user: User | None = OptionalAuth):
    ...
```

Apply consistently:
- **Public:** Health checks, auth token endpoints
- **Optional Auth:** Search, retrieval (rate limits differ)
- **Require Auth:** Chat, memory, admin, annotations

**Breaking:** No (if existing None checks preserved)

---

### P1.5: Fix SSE Race Condition (1-2h)
**File:** `src/api/v1/chat.py:419-503`

**Current Issue:**
Conversation saved **after** SSE stream completes. If client disconnects, conversation is lost.

**Fix:**
```python
async def generate_stream() -> AsyncGenerator[str, None]:
    collected_answer = []
    collected_sources = []

    try:
        # ... streaming logic ...
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield _format_sse_message({"type": "error", ...})
    finally:
        # Always save, even on disconnect
        full_answer = "".join(collected_answer)
        if full_answer and len(full_answer) > 10:
            await save_conversation_turn(...)
```

**Breaking:** No

---

## Priority 2: Validation & Consistency (10-16h)

### P2.1: File Upload Validation (3-4h)
**File:** `src/api/v1/retrieval.py:373-461`

**Current Issue:**
- No file size limit
- No content-type validation
- No malware scanning
- Could allow DoS via large files

**Fix:**
```python
MAX_FILE_SIZE_MB = 50

@router.post("/upload")
@limiter.limit("10/hour")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: str | None = Depends(get_current_user),
) -> IngestionResponse:
    # Validate file size
    file_size = 0
    chunk_size = 1024 * 1024
    for chunk in iter(lambda: file.file.read(chunk_size), b""):
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(413, f"File too large. Max: {MAX_FILE_SIZE_MB}MB")
    file.file.seek(0)

    # Validate content type
    allowed_types = ["application/pdf", "text/plain", "text/markdown"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Invalid content type: {file.content_type}")

    # TODO: Add ClamAV virus scanning
    ...
```

**Breaking:** No

---

### P2.2: Standardize Pagination (3-4h)
**Files:** Multiple endpoints

**Current Issue:**
- No pagination for large result sets
- `top_k` parameter inconsistently named (`limit`, `top_k`, `max_results`)
- No cursor-based pagination

**Fix:**
Create `src/api/models/pagination.py`:
```python
class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100, description="Results per page")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool

# Usage
@router.get("/memory/search")
async def search_memory(
    params: PaginationParams = Depends(),
    ...
) -> PaginatedResponse[MemorySearchResult]:
    ...
```

**Breaking:** Yes (if replacing `top_k`, but OK since not live)

---

### P2.3: Request ID Tracking (2-3h)
**Files:** All endpoints

**Fix:**
Add middleware in `src/api/middleware.py`:
```python
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    with structlog.contextvars.bind_contextvars(request_id=request_id):
        response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    return response
```

**Breaking:** No

---

### P2.4: Consolidate Duplicate Models (2-3h)
**Files:** `src/core/models.py`, `src/api/v1/*.py`

**Current Issue:**
- Multiple files define their own models
- `HealthStatus` enum in both `models.py` and `v1/health.py`
- Annotation models only in `annotations.py`

**Fix:**
Create `src/api/models/` directory:
```
src/api/models/
├── __init__.py
├── common.py        # ErrorResponse, HealthStatus, etc.
├── chat.py          # Chat-specific models
├── retrieval.py     # Retrieval models
├── memory.py        # Memory models
├── admin.py         # Admin models
├── annotations.py   # Annotation models
└── pagination.py    # Pagination models
```

Update imports across all endpoints.

**Breaking:** No (internal refactoring)

---

### P2.5: OpenAPI Documentation (0-2h)
**Files:** All endpoint files

**Fix:**
Add standardized documentation to all endpoints:
```python
@router.post(
    "/endpoint",
    response_model=ResponseModel,
    status_code=200,
    summary="One-line summary (<80 chars)",
    description="""
    Detailed description:
    - What it does
    - When to use it
    - Performance characteristics
    - Rate limits
    """,
    responses={
        200: {"description": "Success", "model": ResponseModel},
        400: {"description": "Invalid input", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal error", "model": ErrorResponse},
    },
    openapi_extra={
        "examples": {
            "example1": {
                "summary": "Basic usage",
                "value": {...}
            }
        }
    }
)
```

**Breaking:** No

---

## Priority 3: Code Quality (8-14h)

### P3.1: Extract Helper Functions (2-3h)
**File:** `src/api/v1/chat.py:935-1053`

**Fix:**
Move to `src/api/utils/responses.py`:
```python
def extract_answer(result: dict) -> str:
    """Extract answer from coordinator result."""
    ...

def extract_sources(result: dict, max_sources: int = 5) -> list[SourceDocument]:
    """Extract and format source documents."""
    ...

def format_sse_message(data: dict) -> str:
    """Format data as Server-Sent Events message."""
    ...

def get_iso_timestamp() -> str:
    """Get current UTC timestamp in ISO 8601 format."""
    return datetime.now(datetime.UTC).isoformat()
```

**Breaking:** No

---

### P3.2: Standardize Logging (2-3h)
**Files:** All endpoint files

**Fix:**
```python
# Always use this import
from src.core.logging import get_logger
logger = get_logger(__name__)

# Snake_case event names
logger.info(
    "endpoint_called",
    endpoint="/api/v1/...",
    method="POST",
    user_id=user.id if user else None,
    request_id=request.state.request_id,
)
```

**Breaking:** No

---

### P3.3: Simplify Router Registration (1-2h)
**File:** `src/api/main.py:223-260`

**Fix:**
Create `src/api/utils/routing.py`:
```python
def register_routers(app: FastAPI, routers: list[tuple[APIRouter, str | None]]):
    """Register multiple routers with automatic logging."""
    for router, prefix_override in routers:
        prefix = prefix_override or router.prefix or "(default)"
        app.include_router(router, prefix=prefix_override)
        logger.info("router_registered", router=router.tags[0] if router.tags else "unknown", prefix=prefix)

# Usage in main.py
register_routers(app, [
    (health_router, None),
    (retrieval_router, None),
    (annotations_router, None),
    (admin_router, "/api/v1"),
    (chat_router, "/api/v1"),
    ...
])
```

**Breaking:** No

---

### P3.4: Centralize Session ID Generation (1-2h)
**Files:** `src/api/v1/chat.py`

**Fix:**
Create `src/api/utils/session.py`:
```python
def generate_session_id(prefix: str = "session") -> str:
    """Generate unique session ID with optional prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def validate_session_id(session_id: str) -> bool:
    """Validate session ID format."""
    return bool(re.match(r"^[a-z]+_[a-f0-9]{12}$", session_id))
```

**Breaking:** No

---

### P3.5: Add Response Compression (1h)
**File:** `src/api/main.py`

**Fix:**
```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Breaking:** No

---

### P3.6: Add API Metrics (2-3h)
**File:** `src/api/main.py`

**Fix:**
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

**Breaking:** No

---

## Priority 4: Future Enhancements (10-15h)

### P4.1: Background Task Health Checks (2-3h)
Add endpoint to check background task status.

### P4.2: Request/Response Logging Middleware (2-3h)
Log full request/response in dev mode for debugging.

### P4.3: Swagger UI Customization (1-2h)
Improve dev experience with better Swagger defaults.

### P4.4: Rate Limit Headers (2-3h)
Add X-RateLimit-* headers to all responses.

### P4.5: Webhook Support (3-4h)
Allow clients to register webhooks for long-running operations.

---

## Implementation Timeline

### Week 1: Security & Validation (P1 + P2.1-P2.3)
**Effort:** 18-25h

- Day 1: Fix CORS, add rate limiting, fix authentication (5-7h)
- Day 2: Standardize error responses (3-4h)
- Day 3: Fix SSE race condition, add request ID tracking (3-5h)
- Day 4-5: File upload validation, consolidate models (5-7h)
- Weekend: OpenAPI documentation review (0-2h)

**Result:** All security issues fixed, validation improved

---

### Week 2: Code Quality (P2.4-P2.5 + P3)
**Effort:** 10-18h

- Day 1: Standardize pagination (3-4h)
- Day 2: Extract helper functions, standardize logging (4-6h)
- Day 3: Simplify router registration, centralize session IDs (2-4h)
- Day 4: Add response compression, API metrics (3-4h)

**Result:** Consistent patterns, better code quality

---

### Week 3 (Optional): Enhancements (P4)
**Effort:** 10-15h

- Background task health checks
- Request/response logging
- Swagger UI customization
- Rate limit headers
- Webhook support (if needed)

**Result:** Enhanced developer experience, production-ready

---

## Total Effort Summary

| Priority | Effort | Items | Status |
|----------|--------|-------|--------|
| **P1** | 8-12h | 5 | Critical (Sprint 22) |
| **P2** | 10-16h | 5 | High (Sprint 22) |
| **P3** | 8-14h | 6 | Medium (Sprint 22/23) |
| **P4** | 10-15h | 5 | Low (Sprint 23+) |
| **Total** | 36-57h | 21 | 2-3 weeks |

---

## Success Criteria

### Security
- ✅ CORS configured properly
- ✅ Rate limiting on all public endpoints
- ✅ Authentication consistent across API
- ✅ File upload validation complete
- ✅ SSE race condition fixed

### Consistency
- ✅ Error responses standardized
- ✅ Pagination standardized
- ✅ Authentication patterns consistent
- ✅ Logging patterns consistent
- ✅ All models in `src/api/models/`

### Documentation
- ✅ OpenAPI docs complete for all endpoints
- ✅ All endpoints have examples
- ✅ All error responses documented

### Quality
- ✅ No duplicate code in endpoints
- ✅ Helper functions extracted to utils
- ✅ Router registration simplified
- ✅ Request ID tracking enabled

---

## Testing Requirements

For each refactoring item:

1. **Unit Tests:** Test new utilities (errors.py, session.py, responses.py)
2. **Integration Tests:** Test full request/response cycle
3. **Security Tests:** Validate CORS, rate limiting, authentication
4. **Regression Tests:** Ensure existing functionality preserved

**Estimated test effort:** 10-15h additional (included in testing-agent plan)

---

## What's Different (Pre-Production)

**No need for:**
- ❌ API versioning (v1 → v2)
- ❌ Migration guides for external users
- ❌ Deprecation warnings (just fix)
- ❌ Backward compatibility layer
- ❌ Gradual rollout strategies

**Can do:**
- ✅ Make breaking changes freely
- ✅ Change error formats
- ✅ Rename parameters (`top_k` → `limit/offset`)
- ✅ Standardize authentication immediately
- ✅ Faster implementation (no dual support)

**Result:** ~40% less effort, cleaner API, production-ready for V1 launch

---

## Summary

**Pre-production advantage:** We can refactor the API aggressively without worrying about breaking external users.

**Recommended:** Execute P1 + P2 in Sprint 22 (2 weeks, 18-28h)

**Key Improvements:**
- All security issues resolved
- Consistent error handling
- Proper validation everywhere
- Better documentation
- Cleaner code patterns

**Result:** Production-ready API layer for V1 launch.
