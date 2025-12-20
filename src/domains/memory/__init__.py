"""Memory Domain - Public API.

Sprint 56: Domain boundary for 3-layer memory system.

Subdomains:
- redis: Redis memory storage
- graphiti: Graphiti integration
- conversation: Conversation history management

Usage:
    from src.domains.memory import (
        ConversationMemory,
        SessionStore,
        CacheService,
    )
"""

# Protocols (Sprint 57)
from src.domains.memory.protocols import (
    CacheService,
    ConversationMemory,
    MemoryConsolidation,
    SessionStore,
)

__all__ = [
    # Protocols (Sprint 57)
    "ConversationMemory",
    "SessionStore",
    "CacheService",
    "MemoryConsolidation",
]
