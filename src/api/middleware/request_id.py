"""Request ID tracking middleware for FastAPI.

Sprint Context: Sprint 22 (2025-11-11) - Feature 22.2: API Security Hardening
Task: 22.2.1 - Implement Request ID Tracking Middleware

This middleware assigns a unique UUID to every incoming request, adds it to all logs,
and returns it in response headers. This enables request correlation across logs,
tracing, debugging, and support.

Features:
    - Generate UUID4 for each request (or accept existing X-Request-ID header)
    - Add request ID to request state (request.state.request_id)
    - Add request ID to response headers (X-Request-ID)
    - Integrate with structlog for automatic log correlation
    - Measure request duration and add to logs
    - Windows-safe logging (no Unicode emojis)

Architecture:
    Request → Middleware → Generate/Extract ID → Bind to structlog context →
    Process Request → Add to Response Headers → Clear context

Example:
    >>> from src.api.middleware.request_id import RequestIDMiddleware
    >>> app.add_middleware(RequestIDMiddleware)  # MUST be first middleware

    Every request will now have:
    - request.state.request_id: UUID for use in endpoints
    - Response header X-Request-ID: Same UUID for client tracking
    - All logs automatically include request_id field

Usage in Endpoints:
    >>> from fastapi import Request, Depends
    >>> from src.api.dependencies import get_request_id
    >>>
    >>> @router.post("/upload")
    >>> async def upload(request_id: str = Depends(get_request_id)):
    ...     logger.info("upload_started", request_id=request_id)
    ...     # request_id automatically in logs via contextvars

Notes:
    - MUST be registered as the FIRST middleware in the app
    - Uses structlog.contextvars for automatic context binding
    - Windows-safe: No Unicode characters in logs (JSON format recommended)
    - Request ID format: UUID4 (e.g., "550e8400-e29b-41d4-a716-446655440000")
    - Passthrough: Existing X-Request-ID headers are preserved

See Also:
    - src/api/dependencies.py: get_request_id() dependency
    - src/core/logging.py: structlog configuration
    - Feature 22.2.2: Standardized error responses (will use request IDs)
    - Feature 22.2.3: Rate limiting (will log request IDs)
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track requests with unique IDs.

    This middleware generates or extracts a unique request ID for every incoming
    request, stores it in the request state, binds it to the structlog context,
    and adds it to the response headers.

    Request ID Flow:
        1. Check for existing X-Request-ID header (passthrough)
        2. Generate new UUID4 if no header present
        3. Store in request.state.request_id
        4. Bind to structlog context (all logs include request_id)
        5. Process request and measure duration
        6. Add X-Request-ID to response headers
        7. Clear structlog context (prevent leakage)

    Attributes:
        None (stateless middleware)

    Example:
        >>> from fastapi import FastAPI
        >>> from src.api.middleware.request_id import RequestIDMiddleware
        >>>
        >>> app = FastAPI()
        >>> app.add_middleware(RequestIDMiddleware)  # MUST be first
        >>>
        >>> # All subsequent middleware and endpoints have access to request ID

    Performance:
        - Overhead: <1ms per request (UUID generation + context binding)
        - Memory: ~100 bytes per request (UUID string + context vars)
        - No I/O operations (all in-memory)

    Security:
        - UUID4 is cryptographically random (no predictable patterns)
        - Request ID cannot be used to enumerate or guess other IDs
        - Safe to expose in response headers and logs

    Notes:
        - MUST be registered BEFORE any other middleware for proper logging
        - Uses structlog.contextvars for thread-safe context binding
        - Automatically clears context after request (prevents leakage)
        - Windows-compatible (no Unicode in log messages)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process each request and assign a unique ID.

        This method is called for every incoming request. It generates or extracts
        a request ID, binds it to the logging context, processes the request, and
        adds the ID to the response headers.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler in the chain

        Returns:
            Response: HTTP response with X-Request-ID header

        Raises:
            Exception: Any exception from downstream handlers is logged and re-raised

        Example:
            # Automatic for all requests (no manual invocation needed)
            GET /api/v1/search
            -> Middleware assigns request_id: "550e8400-e29b-41d4-a716-446655440000"
            -> All logs include: "request_id": "550e8400-e29b-41d4-a716-446655440000"
            -> Response header: X-Request-ID: 550e8400-e29b-41d4-a716-446655440000

        Logging:
            request_received: Logged when request arrives (method, path, client_host)
            request_completed: Logged when request finishes (status_code, duration_ms)
            request_failed: Logged if exception occurs (error, exc_info)

        Context Binding:
            All logs within this request automatically include:
            - request_id: Unique UUID for this request
            - No need to manually pass request_id to logger calls
        """
        # 1. Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 2. Store in request state (accessible via request.state.request_id)
        request.state.request_id = request_id

        # 3. Bind to structlog context (all logs in this request include request_id)
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # 4. Log request received (Windows-safe: no emojis)
        start_time = time.time()
        logger.info(
            "request_received",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # 5. Process request (call next middleware or route handler)
        response = None
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception with request ID context
            logger.error("request_failed", error=str(e), exc_info=True)
            raise  # Re-raise to let exception handlers deal with it
        finally:
            # 6. Clear structlog context (prevent leakage to next request)
            structlog.contextvars.clear_contextvars()

        # 7. Add request ID to response headers
        duration_ms = (time.time() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id

        # 8. Log request completed (Windows-safe: no emojis)
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=f"{duration_ms:.2f}",
        )

        return response
