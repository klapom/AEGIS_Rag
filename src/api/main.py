"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from prometheus_client import Counter, Histogram, make_asgi_app
from slowapi.errors import RateLimitExceeded

from src.api import graph_analytics, graph_visualization
from src.api.health import router as health_router
from src.api.middleware import limiter, rate_limit_handler
from src.api.middleware.exception_handler import (
    aegis_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.api.middleware.request_id import RequestIDMiddleware
from src.api.routers import graph_viz
from src.api.v1.admin import router as admin_router
from src.api.v1.annotations import router as annotations_router  # Feature 21.6
from src.api.v1.auth import router as auth_router  # Sprint 22 Feature 22.2.4
from src.api.v1.chat import router as chat_router
from src.api.v1.health import router as v1_health_router
from src.api.v1.memory import router as memory_router
from src.api.v1.retrieval import router as retrieval_router
from src.core.config import get_settings
from src.core.exceptions import AegisRAGException
from src.core.logging import get_logger, setup_logging

# Initialize settings and logging
settings = get_settings()
setup_logging(log_level=settings.log_level, json_logs=settings.json_logs)
logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "aegis_rag_requests_total", "Total request count", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "aegis_rag_request_latency_seconds", "Request latency", ["method", "endpoint"]
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Initialize LangSmith tracing (Sprint 4 Feature 4.5)
    from src.core.tracing import setup_langsmith_tracing

    tracing_enabled = setup_langsmith_tracing()
    logger.info(
        "langsmith_tracing_status",
        enabled=tracing_enabled,
        project=settings.langsmith_project if tracing_enabled else None,
    )

    # Sprint 10: Initialize BM25 model on startup
    # The HybridSearch will automatically load BM25 from disk cache if available.
    # If not, it will need to be trained via /api/v1/retrieval/prepare-bm25
    try:
        from src.api.v1.retrieval import get_hybrid_search

        hybrid_search = get_hybrid_search()

        # Check if BM25 is already loaded from cache
        if not hybrid_search.bm25_search.is_fitted():
            # No cache found, try to initialize from Qdrant
            logger.info("No BM25 cache found, initializing from Qdrant...")
            await hybrid_search.prepare_bm25_index()
            logger.info("bm25_initialized_on_startup", status="success")
        else:
            logger.info(
                "bm25_loaded_from_cache",
                status="success",
                corpus_size=hybrid_search.bm25_search.get_corpus_size(),
            )
    except Exception as e:
        # Non-fatal: BM25 can be initialized later via API
        logger.warning(
            "bm25_initialization_failed",
            error=str(e),
            note="Can be initialized via /api/v1/retrieval/prepare-bm25",
        )

    # TODO: Initialize database connections, load models, etc.

    yield

    # Shutdown
    logger.info("application_shutting_down")
    # TODO: Close database connections, cleanup resources


# Create FastAPI app
app = FastAPI(
    title="AEGIS RAG API",
    description="Agentic Enterprise Graph Intelligence System - Production-ready RAG API",
    version=settings.app_version,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# Sprint 22 Feature 22.2.1: Request ID Tracking Middleware
# IMPORTANT: Must be registered FIRST to ensure all logs have request IDs
app.add_middleware(RequestIDMiddleware)
logger.info("middleware_registered", middleware="RequestIDMiddleware", note="First in chain for proper logging")

# Register rate limiter (Sprint 22 Feature 22.2.3)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore[arg-type]
logger.info(
    "rate_limiter_configured",
    enabled=settings.rate_limit_enabled,
    global_limit=f"{settings.rate_limit_per_minute}/minute",
    storage=settings.rate_limit_storage_uri,
)

# CORS middleware (Sprint 22 Feature 22.2.3: Secure CORS Configuration)
# SECURITY: No wildcard (*) origins - only specific allowed origins from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # From config (no wildcard!)
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
logger.info(
    "cors_configured",
    allowed_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    note="No wildcard origins (security hardening)",
)


# Sprint 22 Feature 22.2.2: Standardized Exception Handlers
# Register exception handlers (order matters - specific to general)
app.add_exception_handler(AegisRAGException, aegis_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

logger.info(
    "exception_handlers_registered",
    handlers=["AegisRAGException", "RequestValidationError", "HTTPException", "Generic"],
    note="Sprint 22 Feature 22.2.2: Standardized error responses with request IDs",
)


# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track request metrics."""
    import time

    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    latency = time.time() - start_time
    REQUEST_COUNT.labels(
        method=request.method, endpoint=request.url.path, status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(latency)

    # Add response headers
    response.headers["X-Process-Time"] = str(latency)

    return response


# Include routers
# TD-41: Enhanced router registration logging
logger.info("registering_routers", phase="startup")

app.include_router(health_router)
logger.info("router_registered", router="health_router", prefix="(default)")

app.include_router(v1_health_router)
logger.info("router_registered", router="v1_health_router", prefix="/api/v1")

app.include_router(retrieval_router)
logger.info("router_registered", router="retrieval_router", prefix="/api/v1/retrieval")

# Feature 21.6: Image Annotations API
app.include_router(annotations_router)
logger.info("router_registered", router="annotations_router", prefix="/api/v1/annotations")

app.include_router(admin_router, prefix="/api/v1")  # Sprint 16 Feature 16.3: Admin re-indexing
logger.info(
    "router_registered",
    router="admin_router",
    prefix="/api/v1/admin",
    note="Sprint 18 TD-41: Admin router with /stats endpoint - prefix fixed!",
)

# Authentication API router (Sprint 22 Feature 22.2.4: JWT Authentication)
app.include_router(auth_router)
logger.info("router_registered", router="auth_router", prefix="/api/v1/auth", note="Sprint 22: JWT authentication endpoints")

# Chat API router (Sprint 10: Feature 10.1)
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
logger.info("router_registered", router="chat_router", prefix="/api/v1")

# Memory API router (Sprint 7: Feature 7.6)
app.include_router(memory_router, prefix="/api/v1", tags=["memory"])

# Graph visualization and analytics routers (Sprint 6: Features 6.5 & 6.6)
app.include_router(graph_visualization.router, prefix="/api/v1", tags=["visualization"])
app.include_router(graph_analytics.router, prefix="/api/v1", tags=["analytics"])

# Enhanced graph visualization router (Sprint 12: Feature 12.8)
app.include_router(graph_viz.router)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "docs": "/docs",
    }
