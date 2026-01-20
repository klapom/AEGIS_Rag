"""Domain Auto-Discovery Components.

Sprint 117 - Feature 117.3: Domain Auto-Discovery (8 SP)

This module provides components for automatic domain discovery from sample documents
using document clustering, entity extraction, and LLM-based analysis.
"""

from src.components.domain_discovery.discovery_service import (
    DomainDiscoveryService,
    get_domain_discovery_service,
)

__all__ = ["DomainDiscoveryService", "get_domain_discovery_service"]
