"""Admin API Module.

This module contains administrative endpoints for domain management,
including domain auto-discovery from uploaded files.

Sprint 46 - Feature 46.4: Domain Auto-Discovery Backend

Available routers:
- domain_discovery: Domain auto-discovery from file uploads
"""

from src.api.v1.admin_discovery.domain_discovery import router as domain_discovery_router

__all__ = ["domain_discovery_router"]
