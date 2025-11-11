# Sprint 22: Hybrid Approach - Critical Refactoring + Format Coverage

**Status:** 📋 PLANNED
**Approach:** Hybrid (Strategic Mix)
**Timeline:** 4 Wochen (2 Wochen Critical Path + 2 Wochen Rest)
**Total Effort:** 82-120h (20-30h/week)
**Created:** 2025-11-11
**Related:**
- [Format Evaluation](../evaluations/INGESTION_FORMAT_EVALUATION.md)
- [Reference Docs](./reference/) - Detailed subagent analysis

---

## 🎯 Executive Summary

**Strategie:** Weder "Erst Refactoring" noch "Erst Features", sondern **strategisch gemischt** für maximalen Impact bei minimalem Risiko.

**Warum Hybrid?**
1. ✅ **Verhindert Konflikte** - `unified_ingestion.py` weg → kein Konflikt mit Format Router
2. ✅ **Schneller User Value** - Nach 2 Wochen: 30+ Formate unterstützt!
3. ✅ **Saubere Basis** - API Security + Error Handling vor neuen Features
4. ✅ **Gründliches Refactoring** - P2-P4 Items mit realer Feature-Basis (Woche 3-4)

**Deliverables:**
- **Woche 1:** API production-ready (Security, Errors, Auth), alte Ingestion gelöscht
- **Woche 2:** 30+ Formate, Graceful Degradation (Docling → LlamaIndex Fallback)
- **Woche 3-4:** BaseClient Pattern, alle restlichen Refactorings

---

## 📋 Context & Rationale

### Problem Statement

Nach Sprint 21 haben wir zwei große Baustellen:

**1. Refactoring Needs (84-114h gesamt):**
- 780+ Zeilen deprecated/duplicate Code
- 5 kritische API Security Issues
- 17 Test-Gaps
- Inkonsistente Patterns (Error Handling, Auth, Logging)

**2. Format Coverage Gaps (22-30h):**
- Nur 8 Formate unterstützt (Docling)
- 13 kritische Formate fehlen (CSV, XML, IPYNB, etc.)
- Keine externen Quellen (Web, Google Drive, Notion)
- Kein Fallback bei Docling-Ausfall

### Dependency Analysis

**Kritische Konflikte:**
1. `unified_ingestion.py` (275 Zeilen) ❌ würde mit Format Router kollidieren
2. ADR-028 "LlamaIndex Deprecation" ❌ widerspricht Hybrid Strategy (brauchen LlamaIndex!)

**Hilfreiche Refactorings für Hybrid Ingestion:**
3. API Security (Error Responses, Rate Limiting, Auth) ✅ saubere Basis für neue Endpoints
4. Request ID Tracking ✅ Debugging für Format Router
5. BaseClient Pattern ✅ könnte BaseParser für Router werden

**Unabhängige Items (später):**
- three_phase_extractor.py, base.py duplicate, embedding wrapper, client naming

### Decision: Hybrid Approach

```yaml
Phase 1 (Woche 1): Critical Refactoring
  Zweck: Konflikte verhindern, saubere Basis schaffen
  Items: Nur blockierende/hilfreiche Refactorings
  Effort: 20-30h
  Result: API production-ready, alte Ingestion weg

Phase 2 (Woche 2): Hybrid Ingestion
  Zweck: User Value, neue Features auf sauberer Basis
  Items: Format Router + LlamaIndex Fallback
  Effort: 22-30h
  Result: 30+ Formate, Graceful Degradation

Phase 3 (Woche 3-4): Rest Refactoring
  Zweck: Gründliches Refactoring ohne Zeitdruck
  Items: P2-P4 Backend/API Items
  Effort: 40-60h
  Result: Production-ready V1, BaseClient Pattern
```

---

## 📅 Phase Overview

| Phase | Duration | Effort | Focus | User Value | Code Quality |
|-------|----------|--------|-------|------------|--------------|
| **Phase 1** | Woche 1 | 20-30h | Critical Refactoring | ❌ None | ✅ API Basis |
| **Phase 2** | Woche 2 | 22-30h | Hybrid Ingestion | ✅ 30+ Formate | ✅ Gut |
| **Phase 3** | Woche 3-4 | 40-60h | Rest Refactoring | ➖ Indirect | ✅✅ Sehr gut |
| **Total** | 4 Wochen | 82-120h | Hybrid | ✅ Nach 2 Wochen | ✅✅ Production |

---

## 🔧 Phase 1: Critical Refactoring (Woche 1, 20-30h)

**Ziel:** Konflikte verhindern, saubere API-Basis schaffen
**Strategie:** Nur Items die Hybrid Ingestion blockieren oder helfen

### Feature 22.1: Remove Deprecated Ingestion Code (10-12h)

**Rationale:** `unified_ingestion.py` würde mit Format Router kollidieren → MUSS weg

#### Task 22.1.1: Delete unified_ingestion.py (3-4h)

**File:** `src/components/shared/unified_ingestion.py` (275 lines)

**Steps:**
1. Find all imports:
```bash
grep -r "from src.components.shared.unified_ingestion import" src/
grep -r "from src.components.shared import.*unified_ingestion" src/
```

**Expected imports (from Sprint 20 analysis):**
- `src/api/v1/admin.py` - Admin re-indexing endpoint (deprecated)
- `src/ui/gradio_app.py` - UI ingestion (if still exists)
- `src/components/vector_search/ingestion.py` - Old ingestion wrapper

2. Replace with LangGraph Pipeline:
```python
# ❌ OLD (src/api/v1/admin.py)
from src.components.shared.unified_ingestion import UnifiedIngestionPipeline

pipeline = UnifiedIngestionPipeline()
result = await pipeline.ingest_document(file_path)

# ✅ NEW
from src.components.ingestion.langgraph_pipeline import IngestionPipeline
from src.components.ingestion.docling_client import DoclingContainerClient

pipeline = IngestionPipeline()
result = await pipeline.run({
    "document_path": str(file_path),
    "session_id": "admin_reindex",
    "metadata": {"source": "admin"}
})
```

3. Delete file:
```bash
git rm src/components/shared/unified_ingestion.py
```

4. Update tests:
```bash
# Find test files
grep -r "unified_ingestion" tests/

# Update or delete tests
# tests/unit/shared/test_unified_ingestion.py → DELETE (functionality moved)
# tests/integration/test_ingestion.py → UPDATE to use LangGraph pipeline
```

**Testing:**
```bash
pytest tests/integration/test_ingestion_langgraph.py -v
pytest tests/api/test_admin.py::test_reindex -v  # If admin endpoint uses it
```

**Git Commit:**
```bash
git add -A
git commit -m "refactor(ingestion): remove unified_ingestion.py (replaced by LangGraph)

- Delete src/components/shared/unified_ingestion.py (275 lines)
- Migrate src/api/v1/admin.py to LangGraph pipeline
- Update/delete related tests
- No breaking changes (internal refactoring only)

Related: Sprint 22 Phase 1, Feature 22.1
Prevents conflict with upcoming Format Router (Phase 2)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ 275 lines deleted
- ✅ All imports migrated to LangGraph
- ✅ Tests passing

---

#### Task 22.1.2: Update ADR-028 (LlamaIndex NOT Deprecated!) (1-2h)

**Rationale:** ADR-028 sagt "Deprecate LlamaIndex" aber Hybrid Strategy braucht es als Fallback!

**File:** `docs/adr/ADR-028-llamaindex-deprecation-strategy.md`

**Changes:**
1. Update Title: "LlamaIndex Deprecation Strategy" → "LlamaIndex Fallback Strategy"
2. Update Status: "Deprecated" → "Optional Fallback"
3. Add Section: "Sprint 22 Update: Hybrid Ingestion Strategy"

**New Section to Add:**
```markdown
## Sprint 22 Update: Hybrid Ingestion Strategy (2025-11-11)

### Context Change

Sprint 22 introduced **Format Router** with Hybrid Ingestion Strategy:
- Docling remains PRIMARY for PDF/DOCX/PPTX (GPU OCR, layout, high quality)
- LlamaIndex role EXPANDED to cover 13 additional formats (CSV, XML, IPYNB, etc.)

**Decision:** LlamaIndex is NOT deprecated, it's a **strategic fallback** and **format coverage** tool.

### New Architecture

```yaml
Format Router:
  PDF/DOCX/PPTX/XLSX → Docling (Primary - GPU, high quality)
  CSV/XML/IPYNB/RTF/EPUB → LlamaIndex (Fallback - format coverage)
  Web URLs → LlamaIndex (Connectors)
  Google Drive/Notion → LlamaIndex (Connectors)
  Docling Unavailable → LlamaIndex (Graceful degradation)
```

### Configuration Update

```python
# src/core/config.py
llamaindex_enabled: bool = Field(
    default=True,  # CHANGED from False
    description="Enable LlamaIndex fallback parser (NOT deprecated!)"
)
docling_enabled: bool = Field(
    default=True,
    description="Enable Docling as primary parser"
)
```

### Dependencies Update

**Keep ALL LlamaIndex dependencies** (no longer deprecated):
```toml
# Core library (for format coverage + connectors)
llama-index-core = "^0.14.3"
llama-index-readers-file = "^0.5.4"  # CSV, XML, IPYNB, etc.

# Optional connectors (Sprint 23+)
# llama-index-readers-web = "^0.3.1"
# llama-index-readers-google = "^0.2.1"
```

See: [Format Evaluation](../evaluations/INGESTION_FORMAT_EVALUATION.md) for full analysis.
```

**Git Commit:**
```bash
git add docs/adr/ADR-028-llamaindex-deprecation-strategy.md
git commit -m "docs(adr): update ADR-028 - LlamaIndex as strategic fallback

- Change status: Deprecated → Optional Fallback
- Add Sprint 22 Hybrid Ingestion Strategy context
- Update config: llamaindex_enabled = True (not False!)
- Clarify: LlamaIndex fills 13 format gaps, provides graceful degradation

Related: Sprint 22 Phase 1, Feature 22.1
Rationale: Hybrid Strategy needs LlamaIndex for CSV/XML/IPYNB + fallback

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ ADR-028 updated (LlamaIndex NOT deprecated)
- ✅ Config documentation corrected

---

#### Task 22.1.3: Minimal Test Baseline (3-4 critical tests) (6-8h)

**Rationale:** Safety net vor Refactoring

**Tests to Add:**

**1. Client Lifecycle Test (2-3h):**
```python
# tests/integration/test_client_lifecycle.py

import pytest
from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.vector_search.qdrant_client_wrapper import QdrantClientWrapper
from src.components.graph_rag.neo4j_client import Neo4jClient

@pytest.mark.integration
async def test_docling_container_lifecycle():
    """Test Docling container start/stop lifecycle."""
    client = DoclingContainerClient()

    # Start container
    await client.start_container()
    assert await client.health_check() == True

    # Parse document
    parsed = await client.parse_document(Path("tests/fixtures/sample.pdf"))
    assert parsed["text"] != ""

    # Stop container
    await client.stop_container()
    assert await client.health_check() == False


@pytest.mark.integration
async def test_qdrant_connection_pooling():
    """Test Qdrant connection pooling and reconnection."""
    client = QdrantClientWrapper()

    # First query
    results1 = await client.search(collection="test", query_vector=[...])

    # Simulate disconnect
    await client.close()

    # Should reconnect automatically
    results2 = await client.search(collection="test", query_vector=[...])
    assert len(results2) > 0
```

**2. Error Propagation Test (2-3h):**
```python
# tests/integration/test_error_propagation.py

@pytest.mark.integration
async def test_ingestion_error_propagation():
    """Test errors propagate correctly through LangGraph pipeline."""
    pipeline = IngestionPipeline()

    # Invalid file should raise IngestionError
    with pytest.raises(IngestionError) as exc:
        await pipeline.run({
            "document_path": "nonexistent.pdf",
            "session_id": "test"
        })

    assert "File not found" in str(exc.value)

    # Should NOT crash entire system
    # Next document should process fine
    result = await pipeline.run({
        "document_path": "tests/fixtures/valid.pdf",
        "session_id": "test"
    })
    assert result["status"] == "success"


@pytest.mark.integration
async def test_cascade_failure_prevention():
    """Test system doesn't cascade fail when one component down."""
    # Simulate Neo4j down
    with mock.patch("src.components.graph_rag.neo4j_client.Neo4jClient.health_check", return_value=False):
        pipeline = IngestionPipeline()
        result = await pipeline.run({"document_path": "test.pdf", "session_id": "test"})

        # Should skip graph extraction but complete other steps
        assert result["status"] == "partial_success"
        assert result["qdrant_indexed"] == True
        assert result["graph_indexed"] == False
        assert "neo4j_unavailable" in result["warnings"]
```

**3. Configuration Injection Test (2-3h):**
```python
# tests/unit/core/test_config_injection.py

@pytest.mark.unit
def test_custom_settings_injection():
    """Test components accept custom settings (for DI refactoring later)."""
    custom_settings = Settings(
        qdrant_host="custom-host",
        qdrant_port=9999,
        docling_base_url="http://custom:8080"
    )

    # Should accept custom settings
    client = QdrantClientWrapper(settings=custom_settings)
    assert client.host == "custom-host"
    assert client.port == 9999

    # Default settings should still work
    default_client = QdrantClientWrapper()
    assert default_client.host == settings.qdrant_host
```

**Git Commit:**
```bash
git add tests/integration/test_client_lifecycle.py tests/integration/test_error_propagation.py tests/unit/core/test_config_injection.py
git commit -m "test(refactoring): add critical baseline tests before refactoring

Add 3 critical test categories:
- Client lifecycle (Docling, Qdrant, Neo4j connection/reconnection)
- Error propagation (IngestionError, cascade failure prevention)
- Configuration injection (custom settings for DI pattern)

Coverage: +50 lines, protects against refactoring regressions
Related: Sprint 22 Phase 1, Feature 22.1

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ 3 critical test categories covered
- ✅ Baseline protection against regressions

---

### Feature 22.2: API Security & Consistency (8-12h)

**Rationale:** Neue `/ingest/*` Endpoints brauchen saubere Basis (Error Handling, Rate Limiting, Auth)

#### Task 22.2.1: Standardize Error Responses (3-4h)

**Files:**
- `src/api/models/errors.py` (NEW)
- `src/api/main.py` (UPDATE exception handlers)
- All endpoint files (UPDATE error returns)

**Implementation:**

**1. Create Error Models:**
```python
# src/api/models/errors.py

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from fastapi import Request
from fastapi.responses import JSONResponse

class StandardErrorResponse(BaseModel):
    """Standardized error response for all endpoints."""

    error_code: str = Field(
        description="Machine-readable error code (e.g., VALIDATION_ERROR, INTERNAL_ERROR)"
    )
    message: str = Field(
        description="Human-readable error message"
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error details (optional)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO 8601 timestamp"
    )
    request_id: str | None = Field(
        default=None,
        description="Request ID for tracing (from X-Request-ID header)"
    )
    path: str | None = Field(
        default=None,
        description="Request path that caused error"
    )


def build_error_response(
    error_code: str,
    message: str,
    status_code: int,
    details: dict | None = None,
    request: Request | None = None,
) -> JSONResponse:
    """Build standardized error response.

    Args:
        error_code: Machine-readable code (VALIDATION_ERROR, INTERNAL_ERROR, etc.)
        message: Human-readable message
        status_code: HTTP status code (400, 401, 500, etc.)
        details: Optional additional details
        request: FastAPI Request object (for request_id, path)

    Returns:
        JSONResponse with StandardErrorResponse
    """
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

**2. Update Exception Handlers:**
```python
# src/api/main.py

from src.api.models.errors import build_error_response
from fastapi.exceptions import RequestValidationError
from src.core.exceptions import IngestionError, RetrievalError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    # Sanitize validation errors (don't expose internal field names)
    errors = []
    for error in exc.errors():
        loc = ".".join(str(x) for x in error.get("loc", []))
        errors.append({
            "field": loc,
            "message": error.get("msg", "Validation failed"),
            "type": error.get("type", "validation_error").split(".")[-1],
        })

    return build_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        details={"errors": errors},
        request=request
    )


@app.exception_handler(IngestionError)
async def ingestion_exception_handler(request: Request, exc: IngestionError) -> JSONResponse:
    """Handle ingestion-specific errors."""
    return build_error_response(
        error_code="INGESTION_ERROR",
        message=str(exc),
        status_code=400,
        details={"component": exc.component} if hasattr(exc, "component") else None,
        request=request
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    logger.error("unhandled_exception", exc_info=exc, request_id=getattr(request.state, "request_id", None))

    return build_error_response(
        error_code="INTERNAL_ERROR",
        message="An internal error occurred",
        status_code=500,
        details={"error_type": type(exc).__name__} if settings.environment == "development" else None,
        request=request
    )
```

**3. Update Endpoints to Use New Pattern:**
```python
# Example: src/api/v1/retrieval.py

from src.api.models.errors import build_error_response

@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    try:
        result = await process_upload(file)
        return result
    except ValueError as e:
        # Use standardized error response
        return build_error_response(
            error_code="INVALID_FILE",
            message=f"File validation failed: {str(e)}",
            status_code=400,
            request=request
        )
```

**Testing:**
```python
# tests/api/test_error_responses.py

def test_validation_error_format():
    """Test validation errors follow standard format."""
    response = client.post("/api/v1/upload", json={"invalid": "data"})
    assert response.status_code == 422

    error = response.json()
    assert error["error_code"] == "VALIDATION_ERROR"
    assert error["message"] == "Request validation failed"
    assert "timestamp" in error
    assert "request_id" in error
    assert "details" in error
    assert "errors" in error["details"]


def test_internal_error_format():
    """Test internal errors follow standard format."""
    with mock.patch("some_function", side_effect=Exception("Test error")):
        response = client.post("/api/v1/some-endpoint")
        assert response.status_code == 500

        error = response.json()
        assert error["error_code"] == "INTERNAL_ERROR"
        assert error["message"] == "An internal error occurred"
        assert "timestamp" in error
```

**Git Commit:**
```bash
git add src/api/models/errors.py src/api/main.py src/api/v1/*.py tests/api/test_error_responses.py
git commit -m "feat(api): standardize error responses across all endpoints

- Create StandardErrorResponse model (error_code, message, details, timestamp, request_id, path)
- Add build_error_response() helper function
- Update all exception handlers in main.py
- Update endpoint error returns to use standard format
- Add error response tests

Breaking: Error response format changed
Pre-production: OK (not live yet)
Related: Sprint 22 Phase 1, Feature 22.2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ StandardErrorResponse model created
- ✅ All endpoints use consistent error format
- ✅ Tests passing

---

#### Task 22.2.2: Add Missing Rate Limiting + Fix CORS (2-3h)

**Files:**
- `src/api/v1/annotations.py` (ADD rate limiting)
- `src/api/v1/admin.py` (ADD rate limiting)
- `src/api/main.py` (FIX CORS config)

**Implementation:**

**1. Fix CORS:**
```python
# src/api/main.py

# ❌ OLD (too permissive)
allow_origins=["*"] if settings.environment == "development" else []

# ✅ NEW (specific origins)
allow_origins=settings.ALLOWED_ORIGINS if settings.environment == "development" else settings.CORS_ALLOWED_ORIGINS
```

```python
# src/core/config.py

ALLOWED_ORIGINS: list[str] = Field(
    default=["http://localhost:3000", "http://localhost:8080"],
    description="Allowed CORS origins in development"
)
CORS_ALLOWED_ORIGINS: list[str] = Field(
    default=[],  # Production: specify explicitly
    description="Allowed CORS origins in production"
)
```

**2. Add Rate Limiting:**
```python
# src/api/v1/annotations.py

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/document/{document_id}")
@limiter.limit("30/minute")  # 30 requests per minute
async def get_document_annotations(
    request: Request,  # Required for limiter
    document_id: str,
    user: User = Depends(get_current_user)
):
    """Get annotations for document (rate limited)."""
    ...


@router.post("/document/{document_id}/annotate")
@limiter.limit("10/minute")  # Lower limit for write operations
async def create_annotation(
    request: Request,
    document_id: str,
    annotation: AnnotationCreate,
    user: User = Depends(get_current_user)
):
    """Create new annotation (rate limited)."""
    ...
```

```python
# src/api/v1/admin.py

@router.get("/stats")
@limiter.limit("60/minute")
async def get_system_stats(request: Request, user: User = Depends(get_current_user)):
    """Get system statistics (rate limited)."""
    ...


@router.post("/reindex")
@limiter.limit("5/hour")  # Very restrictive for expensive operations
async def trigger_reindex(request: Request, user: User = Depends(get_current_user)):
    """Trigger full re-indexing (heavily rate limited)."""
    ...
```

**Testing:**
```python
# tests/api/test_rate_limiting.py

def test_annotation_rate_limit():
    """Test annotation endpoints are rate limited."""
    # Make 31 requests (exceeds 30/minute limit)
    for i in range(31):
        response = client.get(f"/api/v1/annotations/document/test-doc")
        if i < 30:
            assert response.status_code in [200, 401]  # OK or needs auth
        else:
            assert response.status_code == 429  # Rate limit exceeded


def test_reindex_rate_limit():
    """Test reindex endpoint is heavily rate limited."""
    # Make 6 requests (exceeds 5/hour limit)
    for i in range(6):
        response = client.post("/api/v1/admin/reindex")
        if i < 5:
            assert response.status_code in [200, 401, 403]
        else:
            assert response.status_code == 429
```

**Git Commit:**
```bash
git add src/api/main.py src/api/v1/annotations.py src/api/v1/admin.py src/core/config.py tests/api/test_rate_limiting.py
git commit -m "feat(api): add rate limiting and fix CORS configuration

CORS:
- Fix: Change allow_origins=['*'] to specific list (security)
- Add ALLOWED_ORIGINS config (dev: localhost:3000, localhost:8080)

Rate Limiting:
- Add to annotations endpoints (30/minute read, 10/minute write)
- Add to admin endpoints (60/minute stats, 5/hour reindex)
- Add rate limiting tests

Related: Sprint 22 Phase 1, Feature 22.2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ CORS fixed (specific origins, not *)
- ✅ Rate limiting added to critical endpoints
- ✅ Tests passing

---

#### Task 22.2.3: Standardize Authentication (2-3h)

**Files:**
- `src/api/auth/dependencies.py` (NEW)
- All endpoint files (UPDATE to use consistent auth)

**Implementation:**

**1. Create Auth Dependencies:**
```python
# src/api/auth/dependencies.py

from fastapi import Depends, HTTPException
from src.api.auth.jwt import get_current_user_from_token
from src.core.models import User

async def require_auth(token: str = Depends(get_current_user_from_token)) -> User:
    """Require authentication (returns User, raises 401 if invalid)."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    return User(id=token, email=f"{token}@example.com")  # Simplified


async def optional_auth(token: str | None = Depends(get_current_user_from_token)) -> User | None:
    """Optional authentication (returns User | None, never raises)."""
    if not token:
        return None
    return User(id=token, email=f"{token}@example.com")


# Type aliases for cleaner endpoint signatures
RequireAuth = Depends(require_auth)
OptionalAuth = Depends(optional_auth)
```

**2. Update Endpoints:**
```python
# src/api/v1/annotations.py

from src.api.auth.dependencies import RequireAuth

@router.get("/document/{document_id}")
async def get_document_annotations(
    document_id: str,
    user: User = RequireAuth,  # ✅ Consistent, clear
):
    """Get annotations (authentication required)."""
    ...


# src/api/v1/retrieval.py

from src.api.auth.dependencies import OptionalAuth

@router.post("/search")
async def search_documents(
    query: SearchQuery,
    user: User | None = OptionalAuth,  # ✅ Optional (rate limits differ)
):
    """Search documents (authentication optional, affects rate limits)."""
    if user:
        # Authenticated: higher rate limit
        ...
    else:
        # Anonymous: lower rate limit
        ...


# src/api/v1/chat.py

from src.api.auth.dependencies import RequireAuth

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    user: User = RequireAuth,  # ✅ Now requires auth (was unprotected!)
):
    """Chat endpoint (authentication now required)."""
    ...
```

**Define Auth Policy Document:**
```python
# src/api/auth/policy.py

"""Authentication Policy for AEGIS RAG API.

Public Endpoints (No Auth Required):
  - GET /health, /health/detailed
  - POST /auth/token (login endpoint)

Optional Auth (Better rate limits if authenticated):
  - POST /api/v1/search
  - POST /api/v1/retrieve
  - GET /api/v1/memory/search

Require Auth (Must be authenticated):
  - POST /api/v1/chat (conversations)
  - POST /api/v1/upload (file ingestion)
  - GET/POST /api/v1/annotations/* (all annotation endpoints)
  - GET/POST /api/v1/admin/* (all admin endpoints)
  - POST /api/v1/memory/consolidate
"""
```

**Testing:**
```python
# tests/api/test_authentication.py

def test_protected_endpoint_requires_auth():
    """Test protected endpoints return 401 without auth."""
    response = client.post("/api/v1/chat", json={"message": "test"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTHENTICATION_REQUIRED"


def test_optional_auth_endpoint_works_without_auth():
    """Test optional auth endpoints work without auth (lower rate limit)."""
    response = client.post("/api/v1/search", json={"query": "test"})
    assert response.status_code == 200  # Works without auth


def test_optional_auth_endpoint_better_with_auth():
    """Test optional auth endpoints have better rate limits with auth."""
    # Without auth: lower rate limit
    # With auth: higher rate limit
    ...
```

**Git Commit:**
```bash
git add src/api/auth/dependencies.py src/api/auth/policy.py src/api/v1/*.py tests/api/test_authentication.py
git commit -m "feat(api): standardize authentication across all endpoints

- Create RequireAuth and OptionalAuth dependency aliases
- Define authentication policy (public/optional/required)
- Apply consistent auth to all endpoints:
  - Chat: Now requires auth (was unprotected!)
  - Annotations: Requires auth (already had)
  - Admin: Requires auth (already had)
  - Search/Retrieve: Optional auth (better rate limits if authenticated)
- Add authentication tests

Related: Sprint 22 Phase 1, Feature 22.2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ Authentication consistent across all endpoints
- ✅ Auth policy documented
- ✅ Tests passing

---

#### Task 22.2.4: Add Request ID Middleware (1-2h)

**Files:**
- `src/api/middleware.py` (UPDATE)
- `src/api/main.py` (REGISTER middleware)

**Implementation:**

```python
# src/api/middleware.py

import uuid
import structlog
from fastapi import Request

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add request ID to all requests for tracing."""
    # Get or generate request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    # Add to logging context (all logs will include request_id)
    with structlog.contextvars.bind_contextvars(request_id=request_id):
        response = await call_next(request)

    # Add to response headers
    response.headers["X-Request-ID"] = request_id

    return response
```

```python
# src/api/main.py

# Register middleware
app.middleware("http")(request_id_middleware)

# Now all error responses will include request_id (already handled by build_error_response())
```

**Testing:**
```python
# tests/api/test_middleware.py

def test_request_id_generated():
    """Test request ID is generated if not provided."""
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 36  # UUID length


def test_request_id_preserved():
    """Test provided request ID is preserved."""
    custom_id = "custom-request-123"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers["X-Request-ID"] == custom_id


def test_request_id_in_error_response():
    """Test request ID included in error responses."""
    response = client.post("/api/v1/invalid-endpoint")
    error = response.json()
    assert "request_id" in error
    assert error["request_id"] == response.headers["X-Request-ID"]
```

**Git Commit:**
```bash
git add src/api/middleware.py src/api/main.py tests/api/test_middleware.py
git commit -m "feat(api): add request ID tracking middleware

- Generate or extract X-Request-ID from headers
- Propagate to all logs via structlog context
- Add to response headers
- Include in error responses (via build_error_response)
- Add middleware tests

Related: Sprint 22 Phase 1, Feature 22.2
Benefit: Distributed tracing, easier debugging

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ Request ID tracking enabled
- ✅ All logs include request_id
- ✅ Tests passing

---

### Phase 1 Summary (Woche 1)

**Features Completed:**
- ✅ Feature 22.1: Remove Deprecated Ingestion Code (10-12h)
  - unified_ingestion.py deleted (275 lines)
  - ADR-028 updated (LlamaIndex NOT deprecated)
  - 3 critical test baselines added
- ✅ Feature 22.2: API Security & Consistency (8-12h)
  - Error responses standardized
  - CORS fixed, Rate limiting added
  - Authentication consistent
  - Request ID tracking enabled

**Git Commits:** 7 commits total (1 per task)

**Deliverables:**
- ✅ API layer production-ready (Security, Errors, Auth, Tracing)
- ✅ Old ingestion code removed (no conflicts with Format Router)
- ✅ Test baseline established (3 critical categories)
- ✅ ~300 lines deleted, ~400 lines added (net +100 high-quality code)

**Result:** Saubere Basis für Phase 2 (Hybrid Ingestion)

---

## 🚀 Phase 2: Hybrid Ingestion (Woche 2, 22-30h)

**Ziel:** User Value! 30+ Formate unterstützen, Graceful Degradation
**Basis:** Clean API from Phase 1 (Error Handling, Rate Limiting, Auth all ready)

### Feature 22.3: Format Router (8-12h)

**Rationale:** Route documents to optimal parser (Docling vs LlamaIndex) based on format

#### Task 22.3.1: Implement Format Router Core (4-6h)

**File:** `src/components/ingestion/format_router.py` (NEW)

**Implementation:**

```python
# src/components/ingestion/format_router.py

"""Format Router - Route documents to optimal parser.

Routes documents to Docling (high-quality OCR/layout) or LlamaIndex
(format coverage/connectors) based on file type and availability.

Example:
    >>> router = FormatRouter()
    >>> parser = router.route_document(Path("data.pdf"))
    >>> # Returns: ParserType.DOCLING (GPU-accelerated, high quality)

    >>> parser = router.route_document(Path("data.csv"))
    >>> # Returns: ParserType.LLAMAINDEX (format coverage)
"""

from enum import Enum
from pathlib import Path
from typing import Literal
import structlog

logger = structlog.get_logger(__name__)


class ParserType(Enum):
    """Available document parsers."""
    DOCLING = "docling"
    LLAMAINDEX = "llamaindex"


class FormatRouter:
    """Route documents to optimal parser based on format.

    Routing Rules:
      - PDF/DOCX/PPTX/XLSX → Docling (GPU OCR, layout, high quality)
      - CSV/XML/IPYNB/RTF/EPUB → LlamaIndex (format coverage)
      - Web URLs → LlamaIndex (web scraping connectors)
      - If Docling disabled → LlamaIndex fallback (graceful degradation)

    Attributes:
        docling_enabled: Use Docling for primary formats (default: True)
        llamaindex_fallback: Use LlamaIndex as fallback (default: True)
    """

    # Docling-optimized formats (GPU OCR, layout analysis)
    DOCLING_FORMATS = {".pdf", ".docx", ".pptx", ".xlsx", ".html"}

    # LlamaIndex-only formats (Docling doesn't support)
    LLAMAINDEX_FORMATS = {
        ".csv", ".xml", ".ipynb", ".epub", ".rtf",
        ".hwp", ".mbox", ".json", ".txt", ".md"
    }

    def __init__(
        self,
        docling_enabled: bool = True,
        llamaindex_fallback: bool = True,
    ):
        self.docling_enabled = docling_enabled
        self.llamaindex_fallback = llamaindex_fallback

        logger.info(
            "format_router_initialized",
            docling_enabled=docling_enabled,
            llamaindex_fallback=llamaindex_fallback
        )

    def route_document(self, file_path: Path) -> ParserType:
        """Determine which parser to use for given file.

        Args:
            file_path: Path to document file

        Returns:
            ParserType enum (DOCLING or LLAMAINDEX)

        Raises:
            ValueError: If file format unsupported by any parser

        Example:
            >>> router = FormatRouter()
            >>> router.route_document(Path("report.pdf"))
            ParserType.DOCLING
            >>> router.route_document(Path("data.csv"))
            ParserType.LLAMAINDEX
        """
        suffix = file_path.suffix.lower()

        # Route to Docling if enabled and format optimized
        if self.docling_enabled and suffix in self.DOCLING_FORMATS:
            logger.info(
                "route_to_docling",
                file=file_path.name,
                suffix=suffix,
                reason="high_quality_ocr_layout"
            )
            return ParserType.DOCLING

        # Route to LlamaIndex if format requires it
        if suffix in self.LLAMAINDEX_FORMATS:
            if not self.llamaindex_fallback:
                raise ValueError(
                    f"Format {suffix} requires LlamaIndex fallback, but fallback is disabled. "
                    f"Enable with: llamaindex_fallback=True"
                )

            logger.info(
                "route_to_llamaindex",
                file=file_path.name,
                suffix=suffix,
                reason="format_coverage"
            )
            return ParserType.LLAMAINDEX

        # Fallback to LlamaIndex if Docling disabled
        if not self.docling_enabled and self.llamaindex_fallback:
            logger.warning(
                "docling_disabled_fallback",
                file=file_path.name,
                suffix=suffix,
                message="Using LlamaIndex fallback (lower OCR quality for PDF/DOCX)"
            )
            return ParserType.LLAMAINDEX

        # Unknown format
        supported = self.DOCLING_FORMATS | self.LLAMAINDEX_FORMATS
        raise ValueError(
            f"Unsupported file format: {suffix}. "
            f"Supported: {sorted(supported)}"
        )

    def route_url(self, url: str) -> ParserType:
        """Route web URLs to appropriate parser.

        Web scraping always uses LlamaIndex connectors (AsyncWebPageReader).

        Args:
            url: URL to web resource

        Returns:
            ParserType.LLAMAINDEX

        Example:
            >>> router = FormatRouter()
            >>> router.route_url("https://example.com/article")
            ParserType.LLAMAINDEX
        """
        logger.info("route_to_llamaindex", url=url, reason="web_scraping")
        return ParserType.LLAMAINDEX

    def route_connector(self, source_type: str) -> ParserType:
        """Route connector-based sources (Google Drive, Notion, etc.).

        All cloud/API connectors use LlamaIndex.

        Args:
            source_type: Connector type ("google_drive", "notion", "confluence", etc.)

        Returns:
            ParserType.LLAMAINDEX

        Example:
            >>> router = FormatRouter()
            >>> router.route_connector("google_drive")
            ParserType.LLAMAINDEX
        """
        logger.info("route_to_llamaindex", source_type=source_type, reason="connector")
        return ParserType.LLAMAINDEX

    def get_supported_formats(self) -> dict[str, list[str]]:
        """Get list of supported formats by parser.

        Returns:
            Dict mapping parser name to list of supported formats

        Example:
            >>> router = FormatRouter()
            >>> formats = router.get_supported_formats()
            >>> print(formats["docling"])
            ['.pdf', '.docx', '.pptx', '.xlsx', '.html']
        """
        return {
            "docling": sorted(self.DOCLING_FORMATS),
            "llamaindex": sorted(self.LLAMAINDEX_FORMATS),
            "total": sorted(self.DOCLING_FORMATS | self.LLAMAINDEX_FORMATS),
        }
```

**Configuration:**
```python
# src/core/config.py

class Settings(BaseSettings):
    # ... existing settings ...

    # Format Router settings (NEW)
    ingestion_router_enabled: bool = Field(
        default=True,
        description="Enable format-based routing (Docling vs LlamaIndex)"
    )
```

**Testing:**
```python
# tests/unit/ingestion/test_format_router.py

import pytest
from pathlib import Path
from src.components.ingestion.format_router import FormatRouter, ParserType


@pytest.mark.parametrize("file_format,expected_parser", [
    (".pdf", ParserType.DOCLING),
    (".docx", ParserType.DOCLING),
    (".pptx", ParserType.DOCLING),
    (".xlsx", ParserType.DOCLING),
    (".csv", ParserType.LLAMAINDEX),
    (".xml", ParserType.LLAMAINDEX),
    (".ipynb", ParserType.LLAMAINDEX),
    (".rtf", ParserType.LLAMAINDEX),
    (".epub", ParserType.LLAMAINDEX),
])
def test_router_format_routing(file_format, expected_parser):
    """Test router correctly routes all supported formats."""
    router = FormatRouter()
    file_path = Path(f"test{file_format}")
    assert router.route_document(file_path) == expected_parser


def test_router_docling_fallback_when_disabled():
    """Test LlamaIndex fallback when Docling disabled."""
    router = FormatRouter(docling_enabled=False, llamaindex_fallback=True)

    # PDF should fallback to LlamaIndex (lower quality, but functional)
    assert router.route_document(Path("test.pdf")) == ParserType.LLAMAINDEX


def test_router_raises_on_unsupported_format():
    """Test router raises ValueError for unsupported formats."""
    router = FormatRouter()

    with pytest.raises(ValueError) as exc:
        router.route_document(Path("test.unknown"))

    assert "Unsupported file format" in str(exc.value)


def test_router_url_routing():
    """Test web URLs always route to LlamaIndex."""
    router = FormatRouter()
    assert router.route_url("https://example.com") == ParserType.LLAMAINDEX


def test_router_connector_routing():
    """Test connectors always route to LlamaIndex."""
    router = FormatRouter()
    assert router.route_connector("google_drive") == ParserType.LLAMAINDEX
    assert router.route_connector("notion") == ParserType.LLAMAINDEX


def test_router_get_supported_formats():
    """Test get_supported_formats returns all formats."""
    router = FormatRouter()
    formats = router.get_supported_formats()

    assert len(formats["docling"]) == 5  # PDF, DOCX, PPTX, XLSX, HTML
    assert len(formats["llamaindex"]) == 9  # CSV, XML, IPYNB, etc.
    assert len(formats["total"]) == 14  # Combined
```

**Git Commit:**
```bash
git add src/components/ingestion/format_router.py src/core/config.py tests/unit/ingestion/test_format_router.py
git commit -m "feat(ingestion): implement format router for hybrid parsing

Add FormatRouter class:
- Route PDF/DOCX/PPTX/XLSX → Docling (GPU, high quality)
- Route CSV/XML/IPYNB/RTF/EPUB → LlamaIndex (format coverage)
- Route web URLs → LlamaIndex (web scraping)
- Graceful degradation: Docling disabled → LlamaIndex fallback
- Support 14 total formats (5 Docling + 9 LlamaIndex)

Add comprehensive tests (9 test cases)
Related: Sprint 22 Phase 2, Feature 22.3

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ Format Router implemented
- ✅ 14 formats supported
- ✅ 9 test cases passing

---

#### Task 22.3.2: Integrate Router into LangGraph Pipeline (4-6h)

**File:** `src/components/ingestion/langgraph_pipeline.py` (UPDATE)

**Implementation:**

```python
# src/components/ingestion/langgraph_pipeline.py

from src.components.ingestion.format_router import FormatRouter, ParserType
from src.components.ingestion.docling_client import DoclingContainerClient
# LlamaIndexFallbackParser will be implemented in next task

async def docling_node(state: IngestionState) -> dict:
    """Node 1: Parse document with Docling or LlamaIndex fallback.

    Now uses Format Router to determine parser:
    - PDF/DOCX/PPTX/XLSX → Docling (GPU, high quality)
    - CSV/XML/IPYNB/etc. → LlamaIndex (format coverage)
    """
    file_path = Path(state["document_path"])

    # Initialize router
    router = FormatRouter(
        docling_enabled=settings.docling_enabled,
        llamaindex_fallback=settings.llamaindex_fallback,
    )

    # Determine parser
    parser_type = router.route_document(file_path)

    if parser_type == ParserType.DOCLING:
        # Use Docling (existing code)
        logger.info("using_docling_parser", file=file_path.name)

        client = DoclingContainerClient(
            base_url=settings.docling_base_url,
            timeout_seconds=settings.docling_timeout,
        )

        await client.start_container()
        try:
            parsed = await client.parse_document(file_path)
        finally:
            await client.stop_container()  # Free VRAM

    else:
        # Use LlamaIndex fallback (NEW - next task)
        logger.info("using_llamaindex_parser", file=file_path.name)

        from src.components.ingestion.llamaindex_fallback import LlamaIndexFallbackParser

        fallback = LlamaIndexFallbackParser()
        parsed = await fallback.parse_document(file_path)

    # Log parser used (for metrics)
    logger.info(
        "document_parsed",
        file=file_path.name,
        parser=parser_type.value,
        text_length=len(parsed["text"]),
        tables_found=len(parsed["tables"]),
        images_found=len(parsed["images"]),
    )

    return {"docling_result": parsed}
```

**Testing:**
```python
# tests/integration/test_ingestion_routing.py

@pytest.mark.integration
async def test_pdf_routed_to_docling():
    """Test PDF documents routed to Docling."""
    pipeline = IngestionPipeline()

    result = await pipeline.run({
        "document_path": "tests/fixtures/sample.pdf",
        "session_id": "test"
    })

    # Should use Docling (check logs)
    assert result["metadata"]["parser"] == "docling"


@pytest.mark.integration
async def test_csv_routed_to_llamaindex():
    """Test CSV documents routed to LlamaIndex."""
    pipeline = IngestionPipeline()

    result = await pipeline.run({
        "document_path": "tests/fixtures/data.csv",
        "session_id": "test"
    })

    # Should use LlamaIndex
    assert result["metadata"]["parser"] == "llamaindex"


@pytest.mark.integration
async def test_fallback_when_docling_disabled():
    """Test graceful degradation when Docling disabled."""
    with mock.patch("settings.docling_enabled", False):
        pipeline = IngestionPipeline()

        result = await pipeline.run({
            "document_path": "tests/fixtures/sample.pdf",
            "session_id": "test"
        })

        # Should fallback to LlamaIndex (lower quality, but functional)
        assert result["metadata"]["parser"] == "llamaindex"
        assert "docling_disabled_fallback" in result["warnings"]
```

**Git Commit:**
```bash
git add src/components/ingestion/langgraph_pipeline.py tests/integration/test_ingestion_routing.py
git commit -m "feat(ingestion): integrate format router into LangGraph pipeline

Update docling_node in LangGraph pipeline:
- Use FormatRouter to determine parser (Docling vs LlamaIndex)
- Route PDF/DOCX → Docling (GPU, high quality)
- Route CSV/XML/IPYNB → LlamaIndex (format coverage, next task)
- Graceful degradation: Docling disabled → LlamaIndex fallback
- Log parser used for metrics

Add integration tests for routing logic
Related: Sprint 22 Phase 2, Feature 22.3

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ Router integrated into LangGraph
- ✅ Tests passing

---

### Feature 22.4: LlamaIndex Fallback Parser (6-8h)

**Rationale:** Parse formats Docling doesn't support (CSV, XML, IPYNB, etc.)

#### Task 22.4.1: Implement LlamaIndex Fallback Parser (4-5h)

**File:** `src/components/ingestion/llamaindex_fallback.py` (NEW)

**Implementation:**

```python
# src/components/ingestion/llamaindex_fallback.py

"""LlamaIndex Fallback Parser - Format coverage for non-Docling formats.

Provides parsing for formats not supported by Docling:
- CSV, XML, IPYNB, EPUB, RTF, HWP, Mbox
- Web scraping, cloud storage connectors, databases

Example:
    >>> parser = LlamaIndexFallbackParser()
    >>> parsed = await parser.parse_document(Path("data.csv"))
    >>> print(parsed["text"])
    "Name,Age,City..."
"""

import time
from pathlib import Path
from typing import Any
import structlog

from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file import (
    CSVReader,
    XMLReader,
    IPYNBReader,
    EpubReader,
    RTFReader,
    HWPReader,
    MboxReader,
)

logger = structlog.get_logger(__name__)


class LlamaIndexFallbackParser:
    """Fallback parser using LlamaIndex for non-Docling formats.

    Supports:
      - CSV, XML, IPYNB, EPUB, RTF, HWP, Mbox
      - Plain text, Markdown, JSON
      - Future: Web scraping, cloud connectors

    Attributes:
        file_extractor: Dict mapping extensions to LlamaIndex readers
    """

    def __init__(self):
        # Register custom readers for specific formats
        self.file_extractor = {
            ".csv": CSVReader(),
            ".xml": XMLReader(),
            ".ipynb": IPYNBReader(),
            ".epub": EpubReader(),
            ".rtf": RTFReader(),
            ".hwp": HWPReader(),
            ".mbox": MboxReader(),
        }

        logger.info(
            "llamaindex_fallback_initialized",
            supported_formats=list(self.file_extractor.keys())
        )

    async def parse_document(self, file_path: Path) -> dict[str, Any]:
        """Parse document using LlamaIndex readers.

        Args:
            file_path: Path to document file

        Returns:
            dict with keys: text, metadata, tables, images, layout
            (Same structure as Docling for compatibility with LangGraph pipeline)

        Example:
            >>> parser = LlamaIndexFallbackParser()
            >>> parsed = await parser.parse_document(Path("data.csv"))
            >>> print(parsed["text"][:100])
            "Name,Age,City\nAlice,30,Berlin..."
        """
        start_time = time.time()
        suffix = file_path.suffix.lower()

        logger.info("llamaindex_parsing_start", file=file_path.name, suffix=suffix)

        # Use custom reader if available
        if suffix in self.file_extractor:
            reader = self.file_extractor[suffix]
            documents = reader.load_data(file_path)
        else:
            # Use SimpleDirectoryReader for other formats (TXT, MD, JSON)
            reader = SimpleDirectoryReader(
                input_files=[str(file_path)],
                file_extractor=self.file_extractor,
            )
            documents = reader.load_data()

        # Convert to Docling-compatible format
        parsed = self._convert_to_docling_format(documents, file_path)

        parse_time_ms = (time.time() - start_time) * 1000
        parsed["parse_time_ms"] = parse_time_ms

        logger.info(
            "llamaindex_parsing_complete",
            file=file_path.name,
            parse_time_ms=parse_time_ms,
            text_length=len(parsed["text"]),
            num_documents=len(documents),
        )

        return parsed

    def _convert_to_docling_format(
        self, documents: list, file_path: Path
    ) -> dict[str, Any]:
        """Convert LlamaIndex documents to Docling-compatible format.

        Ensures compatibility with existing LangGraph pipeline nodes.

        Args:
            documents: List of LlamaIndex Document objects
            file_path: Original file path (for metadata)

        Returns:
            dict with Docling-compatible structure
        """
        # Combine all document text
        full_text = "\n\n".join(doc.text for doc in documents)

        # Extract metadata from first document
        metadata = documents[0].metadata if documents else {}

        return {
            "text": full_text,
            "metadata": {
                "source": file_path.name,
                "file_path": str(file_path),
                "parser": "llamaindex",
                "format": file_path.suffix,
                "num_documents": len(documents),
                **metadata,
            },
            "tables": [],  # LlamaIndex doesn't extract tables (yet)
            "images": [],  # LlamaIndex doesn't extract images (yet)
            "layout": {},  # LlamaIndex doesn't do layout analysis
            "parse_time_ms": 0,  # Set by caller
            "md_content": full_text,  # Use plain text as markdown
            "json_content": {},  # No structured JSON from LlamaIndex
        }

    async def parse_url(self, url: str) -> dict[str, Any]:
        """Parse web page using AsyncWebPageReader.

        Args:
            url: URL to web page

        Returns:
            Parsed content in Docling-compatible format

        Example:
            >>> parser = LlamaIndexFallbackParser()
            >>> parsed = await parser.parse_url("https://example.com/article")
        """
        # TODO: Implement in Sprint 23 (Feature 23.1: Web Scraping)
        from llama_index.readers.web import AsyncWebPageReader

        reader = AsyncWebPageReader()
        documents = await reader.aload_data([url])

        return self._convert_to_docling_format(documents, Path(url))
```

**Testing:**
```python
# tests/unit/ingestion/test_llamaindex_fallback.py

import pytest
from pathlib import Path
from src.components.ingestion.llamaindex_fallback import LlamaIndexFallbackParser


@pytest.mark.unit
async def test_csv_parsing():
    """Test CSV file parsing."""
    parser = LlamaIndexFallbackParser()

    # Create temp CSV file
    csv_path = Path("tests/fixtures/test_data.csv")
    csv_path.write_text("Name,Age,City\nAlice,30,Berlin\nBob,25,Munich")

    parsed = await parser.parse_document(csv_path)

    assert parsed["text"] != ""
    assert "Alice" in parsed["text"]
    assert "Berlin" in parsed["text"]
    assert parsed["metadata"]["parser"] == "llamaindex"
    assert parsed["metadata"]["format"] == ".csv"


@pytest.mark.unit
async def test_xml_parsing():
    """Test XML file parsing."""
    parser = LlamaIndexFallbackParser()

    xml_path = Path("tests/fixtures/test_config.xml")
    xml_path.write_text("<config><setting>value</setting></config>")

    parsed = await parser.parse_document(xml_path)

    assert "config" in parsed["text"].lower()
    assert "setting" in parsed["text"].lower()
    assert parsed["metadata"]["format"] == ".xml"


@pytest.mark.unit
async def test_jupyter_notebook_parsing():
    """Test Jupyter notebook parsing."""
    parser = LlamaIndexFallbackParser()

    # Create minimal .ipynb file
    ipynb_path = Path("tests/fixtures/test_notebook.ipynb")
    ipynb_content = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Test Notebook"]},
            {"cell_type": "code", "source": ["print('Hello World')"]},
        ]
    }
    ipynb_path.write_text(json.dumps(ipynb_content))

    parsed = await parser.parse_document(ipynb_path)

    assert "Test Notebook" in parsed["text"]
    assert "Hello World" in parsed["text"]
    assert parsed["metadata"]["format"] == ".ipynb"


@pytest.mark.unit
async def test_docling_compatible_format():
    """Test output is compatible with Docling format (for LangGraph)."""
    parser = LlamaIndexFallbackParser()

    parsed = await parser.parse_document(Path("tests/fixtures/test.txt"))

    # Must have all Docling keys
    assert "text" in parsed
    assert "metadata" in parsed
    assert "tables" in parsed
    assert "images" in parsed
    assert "layout" in parsed
    assert "parse_time_ms" in parsed
    assert "md_content" in parsed

    # Parser metadata
    assert parsed["metadata"]["parser"] == "llamaindex"
```

**Git Commit:**
```bash
git add src/components/ingestion/llamaindex_fallback.py tests/unit/ingestion/test_llamaindex_fallback.py tests/fixtures/*
git commit -m "feat(ingestion): implement LlamaIndex fallback parser

Add LlamaIndexFallbackParser class:
- Parse CSV, XML, IPYNB, EPUB, RTF, HWP, Mbox formats
- Output Docling-compatible format (for LangGraph pipeline)
- Graceful handling of unknown formats via SimpleDirectoryReader

Support 9 new formats:
- CSV (data exports, logs)
- XML (config files, API responses)
- IPYNB (Jupyter notebooks)
- EPUB (eBooks)
- RTF (rich text)
- HWP (Hangul Word Processor)
- Mbox (email archives)
- TXT, MD, JSON (via SimpleDirectoryReader)

Add comprehensive tests (5 test cases)
Related: Sprint 22 Phase 2, Feature 22.4

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ LlamaIndex Fallback Parser implemented
- ✅ 9 new formats supported
- ✅ Docling-compatible format
- ✅ Tests passing

---

#### Task 22.4.2: Integration Tests (Docling vs LlamaIndex Parity) (2-3h)

**File:** `tests/integration/test_parser_parity.py` (NEW)

**Implementation:**

```python
# tests/integration/test_parser_parity.py

"""Test parity between Docling and LlamaIndex parsers.

Ensures both parsers produce similar output for formats they both support (DOCX).
"""

import pytest
from pathlib import Path
from difflib import SequenceMatcher
from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.ingestion.llamaindex_fallback import LlamaIndexFallbackParser


def text_similarity(text1: str, text2: str) -> float:
    """Calculate text similarity (0.0 to 1.0)."""
    return SequenceMatcher(None, text1, text2).ratio()


@pytest.mark.integration
@pytest.mark.slow
async def test_docx_parity_simple_document():
    """Test both parsers produce similar output for simple DOCX."""
    # Simple DOCX: plain text, no tables/images
    docx_path = Path("tests/fixtures/simple_document.docx")

    # Parse with Docling
    docling_parser = DoclingContainerClient()
    await docling_parser.start_container()
    try:
        docling_result = await docling_parser.parse_document(docx_path)
    finally:
        await docling_parser.stop_container()

    # Parse with LlamaIndex
    llamaindex_parser = LlamaIndexFallbackParser()
    llamaindex_result = await llamaindex_parser.parse_document(docx_path)

    # Compare text content (should be very similar for simple docs)
    similarity = text_similarity(
        docling_result["text"],
        llamaindex_result["text"]
    )

    assert similarity > 0.95, (
        f"Parsers should produce similar text for simple DOCX (similarity: {similarity:.2f})"
    )

    # Both should extract content
    assert len(docling_result["text"]) > 100
    assert len(llamaindex_result["text"]) > 100


@pytest.mark.integration
@pytest.mark.slow
async def test_docx_parity_complex_document():
    """Test Docling superior for complex DOCX (tables, layout)."""
    # Complex DOCX: tables, multiple columns, images
    docx_path = Path("tests/fixtures/complex_document.docx")

    # Parse with both
    docling_parser = DoclingContainerClient()
    await docling_parser.start_container()
    try:
        docling_result = await docling_parser.parse_document(docx_path)
    finally:
        await docling_parser.stop_container()

    llamaindex_parser = LlamaIndexFallbackParser()
    llamaindex_result = await llamaindex_parser.parse_document(docx_path)

    # Docling should find tables
    assert len(docling_result["tables"]) > 0, "Docling should extract tables"
    assert len(llamaindex_result["tables"]) == 0, "LlamaIndex doesn't extract tables"

    # Docling should find images
    assert len(docling_result["images"]) > 0, "Docling should find images"
    assert len(llamaindex_result["images"]) == 0, "LlamaIndex doesn't extract images"

    # Docling should have layout info
    assert docling_result["layout"] != {}, "Docling should have layout info"
    assert llamaindex_result["layout"] == {}, "LlamaIndex doesn't do layout analysis"


@pytest.mark.integration
async def test_format_coverage_gap():
    """Test LlamaIndex covers formats Docling doesn't support."""
    # CSV file (Docling doesn't support)
    csv_path = Path("tests/fixtures/data.csv")

    # Docling should reject
    docling_parser = DoclingContainerClient()
    with pytest.raises(Exception):  # Unsupported format error
        await docling_parser.parse_document(csv_path)

    # LlamaIndex should handle
    llamaindex_parser = LlamaIndexFallbackParser()
    result = await llamaindex_parser.parse_document(csv_path)

    assert result["text"] != ""
    assert result["metadata"]["parser"] == "llamaindex"


@pytest.mark.integration
async def test_graceful_degradation():
    """Test system remains functional when Docling unavailable."""
    with mock.patch("src.components.ingestion.docling_client.DoclingContainerClient.start_container", side_effect=Exception("Container failed")):
        # Router should fallback to LlamaIndex
        pipeline = IngestionPipeline()

        # Should still process PDF (lower quality, but functional)
        result = await pipeline.run({
            "document_path": "tests/fixtures/sample.pdf",
            "session_id": "test"
        })

        assert result["status"] == "success"
        assert result["metadata"]["parser"] == "llamaindex"
        assert "docling_unavailable_fallback" in result["warnings"]
```

**Git Commit:**
```bash
git add tests/integration/test_parser_parity.py tests/fixtures/*
git commit -m "test(ingestion): add parser parity tests (Docling vs LlamaIndex)

Add comprehensive parity tests:
- Simple DOCX: Both parsers similar (>95% similarity)
- Complex DOCX: Docling superior (tables, images, layout)
- Format coverage: LlamaIndex covers CSV/XML (Docling gap)
- Graceful degradation: LlamaIndex fallback when Docling unavailable

Validates hybrid strategy:
- Use Docling for quality (PDF/DOCX with tables/images)
- Use LlamaIndex for coverage (CSV/XML/IPYNB)
- Fallback works (no single point of failure)

Related: Sprint 22 Phase 2, Feature 22.4

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Deliverable:**
- ✅ Parity tests passing
- ✅ Validates hybrid strategy

---

### Feature 22.5: API Updates & Documentation (6-8h)

**Rationale:** Update API endpoints to support new formats, document changes

#### Task 22.5.1: Update Upload Endpoint (2-3h)

**File:** `src/api/v1/retrieval.py` (UPDATE)

**Implementation:**

```python
# src/api/v1/retrieval.py

from src.components.ingestion.format_router import FormatRouter

@router.post("/upload")
@limiter.limit("10/hour")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = RequireAuth,
) -> IngestionResponse:
    """Upload and ingest document (now supports 14+ formats).

    Supported Formats:
      - Docling (high quality): PDF, DOCX, PPTX, XLSX, HTML
      - LlamaIndex (coverage): CSV, XML, IPYNB, EPUB, RTF, TXT, MD, JSON

    Rate Limit: 10 uploads per hour
    Authentication: Required
    """
    # Validate file size (already in Phase 1 if P2.1 done, otherwise add here)
    # Validate content type (same)

    # Save uploaded file temporarily
    temp_path = Path(f"/tmp/{file.filename}")
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Check if format supported
    router = FormatRouter()
    try:
        parser_type = router.route_document(temp_path)
    except ValueError as e:
        # Unsupported format
        return build_error_response(
            error_code="UNSUPPORTED_FORMAT",
            message=str(e),
            status_code=400,
            details={"supported_formats": router.get_supported_formats()},
            request=request
        )

    # Ingest via LangGraph pipeline (router handles Docling vs LlamaIndex)
    pipeline = IngestionPipeline()
    result = await pipeline.run({
        "document_path": str(temp_path),
        "session_id": f"user_{current_user.id}",
        "metadata": {
            "source": "upload",
            "user_id": current_user.id,
            "filename": file.filename,
            "parser": parser_type.value,
        }
    })

    # Cleanup temp file
    temp_path.unlink()

    return IngestionResponse(
        status="success",
        document_id=result["document_id"],
        parser_used=parser_type.value,
        formats_supported=router.get_supported_formats()["total"],
    )
```

**Update Response Model:**
```python
# src/api/models/retrieval.py

class IngestionResponse(BaseModel):
    """Response from document ingestion."""
    status: str = Field(description="Ingestion status (success, partial_success, failed)")
    document_id: str = Field(description="Unique document ID")
    parser_used: str = Field(description="Parser used (docling or llamaindex)")
    formats_supported: list[str] = Field(description="All supported formats")
    warnings: list[str] = Field(default_factory=list, description="Warnings (if any)")
```

**Git Commit:**
```bash
git add src/api/v1/retrieval.py src/api/models/retrieval.py
git commit -m "feat(api): update upload endpoint to support 14+ formats

Update /upload endpoint:
- Check format support via FormatRouter
- Return parser used (docling vs llamaindex)
- Return list of all supported formats
- Improved error messages for unsupported formats

Supports 14 formats now:
- Docling: PDF, DOCX, PPTX, XLSX, HTML (high quality)
- LlamaIndex: CSV, XML, IPYNB, EPUB, RTF, TXT, MD, JSON, Mbox

Related: Sprint 22 Phase 2, Feature 22.5

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 22.5.2: Add Supported Formats Endpoint (1-2h)

**File:** `src/api/v1/retrieval.py` (ADD)

**Implementation:**

```python
# src/api/v1/retrieval.py

@router.get("/supported-formats")
async def get_supported_formats() -> dict[str, Any]:
    """Get list of supported document formats.

    Returns format lists for:
    - Docling parser (GPU-accelerated, high quality)
    - LlamaIndex parser (format coverage, fallback)
    - Total supported formats

    Example Response:
    {
      "docling": [".pdf", ".docx", ".pptx", ".xlsx", ".html"],
      "llamaindex": [".csv", ".xml", ".ipynb", ".epub", ".rtf", ...],
      "total": [".pdf", ".docx", ..., ".csv", ".xml", ...],
      "count": {
        "docling": 5,
        "llamaindex": 9,
        "total": 14
      }
    }
    """
    router = FormatRouter()
    formats = router.get_supported_formats()

    return {
        **formats,
        "count": {
            "docling": len(formats["docling"]),
            "llamaindex": len(formats["llamaindex"]),
            "total": len(formats["total"]),
        },
        "parser_info": {
            "docling": {
                "quality": "high",
                "speed": "fast (GPU)",
                "features": ["OCR", "layout analysis", "table extraction", "image detection"]
            },
            "llamaindex": {
                "quality": "medium",
                "speed": "fast (CPU)",
                "features": ["format coverage", "web scraping (Sprint 23)", "cloud connectors (Sprint 23)"]
            }
        }
    }
```

**Testing:**
```python
# tests/api/test_supported_formats.py

def test_get_supported_formats():
    """Test supported formats endpoint."""
    response = client.get("/api/v1/supported-formats")
    assert response.status_code == 200

    data = response.json()
    assert "docling" in data
    assert "llamaindex" in data
    assert "total" in data
    assert "count" in data

    # Should support 14+ formats
    assert data["count"]["total"] >= 14

    # Docling should include PDF
    assert ".pdf" in data["docling"]

    # LlamaIndex should include CSV
    assert ".csv" in data["llamaindex"]
```

**Git Commit:**
```bash
git add src/api/v1/retrieval.py tests/api/test_supported_formats.py
git commit -m "feat(api): add supported formats endpoint

Add GET /supported-formats endpoint:
- List all supported formats by parser
- Show parser capabilities (quality, speed, features)
- Return counts (docling: 5, llamaindex: 9, total: 14)

Useful for:
- Frontend file upload UI (show supported formats)
- API documentation (dynamic format list)
- Monitoring (track format coverage)

Related: Sprint 22 Phase 2, Feature 22.5

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 22.5.3: Update Documentation (3h)

**Files:**
- `docs/components/ingestion/README.md` (UPDATE)
- `docs/api/ENDPOINTS.md` (UPDATE)
- `CLAUDE.md` (UPDATE)

**Git Commit:**
```bash
git add docs/components/ingestion/README.md docs/api/ENDPOINTS.md CLAUDE.md
git commit -m "docs: update ingestion documentation for hybrid strategy

Update ingestion README:
- Add Format Router section
- Add LlamaIndex Fallback Parser section
- Update supported formats list (8 → 14)
- Add format comparison table (Docling vs LlamaIndex)

Update API docs:
- Document /supported-formats endpoint
- Update /upload endpoint (now 14 formats)
- Add format-specific examples

Update CLAUDE.md:
- Update Data Ingestion section (Hybrid Strategy)
- Update Tech Stack (LlamaIndex = Fallback, not deprecated)

Related: Sprint 22 Phase 2, Feature 22.5

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Phase 2 Summary (Woche 2)

**Features Completed:**
- ✅ Feature 22.3: Format Router (8-12h)
  - Router core implemented (14 formats supported)
  - Integrated into LangGraph pipeline
- ✅ Feature 22.4: LlamaIndex Fallback Parser (6-8h)
  - Parser implemented (9 new formats)
  - Parity tests (Docling vs LlamaIndex)
- ✅ Feature 22.5: API Updates & Documentation (6-8h)
  - Upload endpoint updated
  - Supported formats endpoint added
  - Documentation updated

**Git Commits:** 7 commits total

**Deliverables:**
- ✅ **30+ Formate unterstützt** (8 → 14 file formats, unlimited external sources)
- ✅ **Graceful Degradation** (Docling → LlamaIndex Fallback)
- ✅ **Production-ready Feature** (Tests, Docs, API)
- ✅ ~800 lines added (Router + Fallback + Tests)

**Result:** USER VALUE! 30+ Formate nach nur 2 Wochen!

---

## 🔧 Phase 3: Rest Refactoring (Woche 3-4, 40-60h)

**Ziel:** Gründliches Refactoring ohne Zeitdruck
**Basis:** Features funktionieren, kein User-Druck

**Items:**
- BaseClient Pattern (P2 Backend)
- three_phase_extractor.py archivieren (P1 Backend, noch nicht gemacht)
- base.py duplicate entfernen (P1 Backend, noch nicht gemacht)
- Embedding wrapper elimination (P2 Backend)
- Client naming (P2 Backend)
- BaseRetriever interface (P2 Backend)
- Error handling pattern (P2 Backend)
- Dependency injection (P3 Backend)
- File upload validation (P2 API)
- Pagination standardisierung (P2 API)
- Model consolidation (P2 API)
- Helper function extraction (P3 API)
- Remaining Test Gaps (7-10 tests)

**Reference:** Siehe `docs/refactoring/reference/` für alle Details

**Empfehlung:** Nach Phase 2 Pause einlegen, User Feedback sammeln, dann Phase 3 starten

---

## 🎯 Git Commit Strategy

**Wichtig:** 1 Feature = 1 Commit (atomic rollbacks)

### Phase 1 Commits (7 total)
1. `refactor(ingestion): remove unified_ingestion.py (replaced by LangGraph)`
2. `docs(adr): update ADR-028 - LlamaIndex as strategic fallback`
3. `test(refactoring): add critical baseline tests before refactoring`
4. `feat(api): standardize error responses across all endpoints`
5. `feat(api): add rate limiting and fix CORS configuration`
6. `feat(api): standardize authentication across all endpoints`
7. `feat(api): add request ID tracking middleware`

### Phase 2 Commits (7 total)
8. `feat(ingestion): implement format router for hybrid parsing`
9. `feat(ingestion): integrate format router into LangGraph pipeline`
10. `feat(ingestion): implement LlamaIndex fallback parser`
11. `test(ingestion): add parser parity tests (Docling vs LlamaIndex)`
12. `feat(api): update upload endpoint to support 14+ formats`
13. `feat(api): add supported formats endpoint`
14. `docs: update ingestion documentation for hybrid strategy`

**Total:** 14 commits über 2 Wochen

---

## ✅ Testing Strategy

### Pre-Refactoring Tests (Phase 1, 3 tests)
1. **Client Lifecycle** - Docling, Qdrant, Neo4j connection/reconnection
2. **Error Propagation** - IngestionError, cascade failure prevention
3. **Configuration Injection** - Custom settings for DI pattern

### Hybrid Ingestion Tests (Phase 2, 4 test suites)
1. **Format Router Tests** (9 cases)
   - All 14 formats routed correctly
   - Fallback when Docling disabled
   - Unsupported format errors
2. **LlamaIndex Fallback Tests** (5 cases)
   - CSV, XML, IPYNB parsing
   - Docling-compatible format
3. **Parser Parity Tests** (4 cases)
   - Simple DOCX similarity >95%
   - Complex DOCX: Docling superior
   - Format coverage gap (CSV works)
   - Graceful degradation
4. **API Tests** (3 cases)
   - Upload endpoint supports 14 formats
   - Supported formats endpoint
   - Error handling for unsupported formats

**Total:** 21 new test cases, >80% coverage maintained

---

## 📊 Success Criteria

### Phase 1 (Woche 1)
- ✅ unified_ingestion.py deleted (275 lines)
- ✅ ADR-028 updated (LlamaIndex NOT deprecated)
- ✅ API Security: CORS fixed, Rate Limiting added, Auth standardized
- ✅ Error responses standardized
- ✅ Request ID tracking enabled
- ✅ 3 critical test baselines added

### Phase 2 (Woche 2)
- ✅ Format Router implemented (14 formats supported)
- ✅ LlamaIndex Fallback Parser implemented (9 new formats)
- ✅ Graceful Degradation (Docling → LlamaIndex fallback)
- ✅ API updated (/upload supports 14 formats)
- ✅ Documentation updated
- ✅ 21 test cases passing

### Phase 3 (Woche 3-4)
- ✅ BaseClient Pattern (50% boilerplate reduction)
- ✅ All P1 Backend Items completed
- ✅ All P2 API Items completed
- ✅ Test coverage ≥85%
- ✅ Production-ready V1

---

## 📋 Context Refresh Instructions

**Wenn diese Session kompaktiert wurde:**

1. **Lies dieses Dokument komplett** (`SPRINT_22_HYBRID_APPROACH_PLAN.md`)
2. **Check aktuellen Status:**
   - Welche Phase? (Woche 1, 2, 3-4)
   - Welches Feature? (22.1, 22.2, 22.3, etc.)
   - Welcher Task? (z.B. 22.1.1, 22.3.2)
3. **Check Git Status:**
   ```bash
   git status
   git log --oneline -10
   ```
4. **Reference Docs bei Bedarf:**
   - Phase 1: Nur dieses Dokument (alles hier)
   - Phase 2: Nur dieses Dokument (alles hier)
   - Phase 3: `docs/refactoring/reference/` für P2-P4 Details

**Dieses Dokument ist selbst-erklärend und context-refresh-safe!**

---

## 🔗 Related Documents

- [Format Evaluation](../evaluations/INGESTION_FORMAT_EVALUATION.md) - Format Gap Analysis
- [Reference Docs](./reference/) - Detailed subagent analysis (Backend, API, Testing)
- ADR-027: Docling Container Architecture
- ADR-028: LlamaIndex Fallback Strategy (updated in Phase 1)

---

## 📝 Notes

**Pre-Production Advantage:**
- Keine Breaking Changes Concerns
- Keine Migration Guides nötig
- Keine API Versioning (v1 → v2)
- Direkte Änderungen möglich

**Why Hybrid Works:**
- Phase 1 bereitet saubere Basis vor (verhindert Konflikte)
- Phase 2 liefert User Value schnell (30+ Formate nach 2 Wochen)
- Phase 3 kann gründlich sein (keine Feature-Pressure)

**Iterativ & Risiko-arm:**
- Jede Woche Deliverables
- Rollback pro Phase möglich
- Tests als Safety Net

---

**Ende Sprint 22 Hybrid Approach Plan**
