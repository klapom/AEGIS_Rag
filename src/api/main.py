"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

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
# Sprint 53: Admin module split
from src.api.v1.admin_costs import router as admin_costs_router
from src.api.v1.admin_graph import router as admin_graph_router
from src.api.v1.admin_llm import router as admin_llm_router
from src.api.v1.admin_indexing import router as admin_indexing_router
from src.api.v1.admin_discovery import domain_discovery_router  # Sprint 46 Feature 46.4
from src.api.v1.annotations import router as annotations_router  # Feature 21.6
from src.api.v1.auth import router as auth_router  # Sprint 22 Feature 22.2.4
from src.api.v1.chat import router as chat_router
from src.api.v1.domain_training import router as domain_training_router  # Sprint 45 Feature 45.3
from src.api.v1.health import router as v1_health_router
from src.api.v1.mcp import router as mcp_router  # Sprint 40 Feature 40.2: MCP Tool Discovery
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

    # Sprint 31: Initialize FormatRouter with Docling health check
    docling_available = False
    try:
        from src.api.v1 import retrieval
        from src.components.ingestion import langgraph_pipeline
        from src.components.ingestion.format_router import initialize_format_router

        logger.info("Initializing FormatRouter with Docling health check...")
        retrieval._format_router = await initialize_format_router()
        docling_available = retrieval._format_router.docling_available
        logger.info(
            "format_router_initialized_retrieval",
            docling_available=docling_available,
        )

        # Sprint 32: Also initialize ingestion pipeline router
        try:
            await langgraph_pipeline.initialize_ingestion_pipeline()
            logger.info(
                "format_router_initialized_ingestion",
                docling_available=langgraph_pipeline._format_router.docling_available,
            )
        except Exception as pipeline_err:
            logger.warning(
                "ingestion_pipeline_init_failed",
                error=str(pipeline_err),
                note="Ingestion pipeline will initialize on first use",
            )
    except Exception as e:
        logger.warning(
            "format_router_initialization_failed",
            error=str(e),
            note="FormatRouter will use default (Docling assumed available)",
        )

    # Sprint 51: Pre-warm Docling container if available
    # This prevents the container from being stopped after each document
    if docling_available:
        try:
            from src.components.ingestion.docling_client import prewarm_docling_container

            await prewarm_docling_container()
            logger.info("docling_container_prewarmed", status="success")
        except Exception as prewarm_err:
            logger.warning(
                "docling_prewarm_failed",
                error=str(prewarm_err),
                note="Container will be started on-demand per document",
            )

    # Sprint 27 Feature 27.1: Initialize database connections
    try:
        from src.components.graph_rag.neo4j_client import get_neo4j_client
        from src.components.vector_search.qdrant_client import get_qdrant_client

        logger.info("Initializing database connections...")

        # Initialize Neo4j connection
        neo4j_client = get_neo4j_client()
        await neo4j_client.health_check()
        logger.info("Neo4j connection initialized", status="healthy")

        # Initialize Qdrant connection (lazy initialization on first use)
        qdrant_client = get_qdrant_client()
        logger.info("Qdrant client initialized", status="ready")

        logger.info("All database connections initialized successfully")

    except Exception as e:
        logger.warning(
            "Failed to initialize some database connections",
            error=str(e),
            note="Services will initialize on first use",
        )

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Sprint 51: Clear pre-warmed Docling client reference (keep container running)
    # Note: We intentionally do NOT stop the container on backend shutdown
    # because it was started externally (docker compose up -d docling)
    try:
        from src.components.ingestion.docling_client import (
            get_prewarmed_docling_client,
            is_docling_container_prewarmed,
        )

        if is_docling_container_prewarmed():
            client = get_prewarmed_docling_client()
            if client and client.client:
                await client.client.aclose()
            logger.info("docling_client_closed", container_status="running")
    except Exception as e:
        logger.warning("docling_client_close_warning", error=str(e))

    # Sprint 27 Feature 27.1: Close database connections gracefully
    try:
        from src.components.graph_rag.neo4j_client import get_neo4j_client
        from src.components.vector_search.qdrant_client import get_qdrant_client

        logger.info("Closing database connections...")

        # Close Neo4j connection
        neo4j_client = get_neo4j_client()
        await neo4j_client.close()
        logger.info("Neo4j connection closed")

        # Close Qdrant connection
        qdrant_client = get_qdrant_client()
        await qdrant_client.close()
        logger.info("Qdrant connection closed")

        logger.info("All database connections closed successfully")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


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
logger.info(
    "middleware_registered",
    middleware="RequestIDMiddleware",
    note="First in chain for proper logging",
)

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
async def track_requests(request: Request, call_next) -> None:
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

# Sprint 53: Admin module split - Cost, LLM, Graph, Indexing endpoints
app.include_router(admin_costs_router, prefix="/api/v1")
app.include_router(admin_llm_router, prefix="/api/v1")
app.include_router(admin_graph_router, prefix="/api/v1")
app.include_router(admin_indexing_router, prefix="/api/v1")
logger.info(
    "admin_split_routers_registered",
    routers=["admin_costs", "admin_llm", "admin_graph", "admin_indexing"],
    note="Sprint 53: Admin module split for maintainability",
)

# Authentication API router (Sprint 22 Feature 22.2.4: JWT Authentication)
app.include_router(auth_router)
logger.info(
    "router_registered",
    router="auth_router",
    prefix="/api/v1/auth",
    note="Sprint 22: JWT authentication endpoints",
)

# Chat API router (Sprint 10: Feature 10.1)
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
logger.info("router_registered", router="chat_router", prefix="/api/v1")

# Memory API router (Sprint 7: Feature 7.6)
app.include_router(memory_router, prefix="/api/v1", tags=["memory"])

# MCP API router (Sprint 40: Feature 40.2 - Tool Discovery & Management)
app.include_router(mcp_router)
logger.info(
    "router_registered",
    router="mcp_router",
    prefix="/api/v1/mcp",
    note="Sprint 40: MCP tool discovery and execution",
)

# Domain Training API router (Sprint 45: Feature 45.3 - Domain Training API)
app.include_router(domain_training_router)
logger.info(
    "router_registered",
    router="domain_training_router",
    prefix="/admin/domains",
    note="Sprint 45: DSPy-based domain training and classification",
)

# Domain Discovery API router (Sprint 46: Feature 46.4 - Domain Auto-Discovery)
app.include_router(domain_discovery_router)
logger.info(
    "router_registered",
    router="domain_discovery_router",
    prefix="/api/v1/admin/domains",
    note="Sprint 46: File-based domain auto-discovery with LLM analysis",
)

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
