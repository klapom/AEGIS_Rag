"""Agents Memory Module.

Sprint 94 Feature 94.2: Shared Memory Protocol (8 SP)

This module provides memory management for multi-agent systems,
enabling cross-agent collaboration via shared memory spaces.

Exports:
    - SharedMemoryProtocol: Main shared memory interface
    - MemoryScope: Enum for memory scopes (PRIVATE/SHARED/GLOBAL)
    - MemoryEntry: Data model for memory entries
    - AccessControl: Access control model
    - create_shared_memory: Factory function
"""

from src.agents.memory.shared_memory import (
    AccessControl,
    MemoryEntry,
    MemoryScope,
    SharedMemoryProtocol,
    create_shared_memory,
)

__all__ = [
    "SharedMemoryProtocol",
    "MemoryScope",
    "MemoryEntry",
    "AccessControl",
    "create_shared_memory",
]
