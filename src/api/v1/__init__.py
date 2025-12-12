"""API v1 module.

This module contains all v1 API routers for the AEGIS RAG system.
"""

from src.api.v1.admin import router as admin_router
from src.api.v1.annotations import router as annotations_router
from src.api.v1.auth import router as auth_router
from src.api.v1.chat import router as chat_router
from src.api.v1.domain_training import router as domain_training_router
from src.api.v1.health import router as health_router
from src.api.v1.mcp import router as mcp_router
from src.api.v1.memory import router as memory_router
from src.api.v1.retrieval import router as retrieval_router

__all__ = [
    "admin_router",
    "annotations_router",
    "auth_router",
    "chat_router",
    "domain_training_router",
    "health_router",
    "mcp_router",
    "memory_router",
    "retrieval_router",
]
