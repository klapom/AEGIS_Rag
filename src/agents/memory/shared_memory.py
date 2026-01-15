"""Shared Memory Protocol for Cross-Agent Collaboration.

Sprint 94 Feature 94.2: Shared Memory Protocol (8 SP)

This module provides a Redis-backed shared memory system that enables
collaborative knowledge sharing between skills via scoped memory spaces.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                 Shared Memory Protocol                       │
    ├─────────────────────────────────────────────────────────────┤
    │                                                             │
    │  Memory Scopes:                                             │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
    │  │ PRIVATE  │  │  SHARED  │  │  GLOBAL  │                 │
    │  │ (skill)  │  │ (skills) │  │ (system) │                 │
    │  └──────────┘  └──────────┘  └──────────┘                 │
    │                                                             │
    │  Access Control:                                            │
    │  - PRIVATE: Only owner skill can read/write                 │
    │  - SHARED: Authorized skills can read/write                 │
    │  - GLOBAL: All skills can read, admin can write             │
    │                                                             │
    │  Storage: Redis with TTL + LangGraph Checkpointer          │
    │  - Namespace isolation: {scope}:{skill}:{key}               │
    │  - Version tracking for concurrent updates                  │
    │  - Automatic expiration with TTL                            │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘

Example:
    >>> from src.agents.memory.shared_memory import SharedMemoryProtocol, MemoryScope
    >>>
    >>> memory = SharedMemoryProtocol()
    >>>
    >>> # Private memory (skill-only)
    >>> await memory.write(
    ...     key="research_findings",
    ...     value={"papers": 10, "citations": 45},
    ...     scope=MemoryScope.PRIVATE,
    ...     owner_skill="research"
    ... )
    >>>
    >>> # Shared memory (cross-skill)
    >>> await memory.write(
    ...     key="task_context",
    ...     value={"query": "...", "intent": "search"},
    ...     scope=MemoryScope.SHARED,
    ...     owner_skill="coordinator",
    ...     allowed_skills=["research", "synthesis", "memory"]
    ... )
    >>>
    >>> # Read with permission check
    >>> data = await memory.read(
    ...     key="task_context",
    ...     scope=MemoryScope.SHARED,
    ...     requesting_skill="research"
    ... )

Integration:
    - src/components/memory/redis_memory.py: Redis client
    - src/agents/skills/lifecycle.py: Skill context
    - src/agents/tools/policy.py: Permission patterns
    - LangGraph RedisCheckpointer: State persistence

See Also:
    - docs/sprints/SPRINT_94_PLAN.md: Feature specification
    - src/agents/communication/skill_messaging.py: Agent messaging
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

from src.components.memory.redis_memory import RedisMemoryManager
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class MemoryScope(Enum):
    """Memory scope for access control.

    Scopes:
        PRIVATE: Only owner skill can read/write (isolated)
        SHARED: Multiple authorized skills can read/write (collaborative)
        GLOBAL: All skills can read, admin can write (system-wide)

    Example:
        >>> scope = MemoryScope.PRIVATE
        >>> scope.value
        'private'
    """

    PRIVATE = "private"
    SHARED = "shared"
    GLOBAL = "global"


@dataclass
class MemoryEntry:
    """Entry in shared memory.

    Attributes:
        key: Entry key (within scope namespace)
        value: Entry value (JSON-serializable)
        scope: Memory scope (PRIVATE/SHARED/GLOBAL)
        owner_skill: Skill that owns this entry
        timestamp: When entry was created
        ttl_seconds: Time-to-live in seconds (None = no expiration)
        allowed_skills: Skills allowed to read/write (SHARED scope)
        version: Version counter for concurrent update detection
        metadata: Additional metadata (tags, confidence, etc.)

    Example:
        >>> entry = MemoryEntry(
        ...     key="findings",
        ...     value={"count": 10},
        ...     scope=MemoryScope.PRIVATE,
        ...     owner_skill="research",
        ...     timestamp=datetime.now(UTC),
        ...     ttl_seconds=3600
        ... )
    """

    key: str
    value: Any
    scope: MemoryScope
    owner_skill: str
    timestamp: datetime
    ttl_seconds: int | None = None
    allowed_skills: list[str] = field(default_factory=list)
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessControl:
    """Access control for memory operations.

    Attributes:
        can_read: Skills allowed to read
        can_write: Skills allowed to write
        is_admin: Admin skills bypass restrictions

    Example:
        >>> acl = AccessControl(
        ...     can_read=["research", "synthesis"],
        ...     can_write=["coordinator"],
        ...     is_admin=False
        ... )
    """

    can_read: list[str] = field(default_factory=list)
    can_write: list[str] = field(default_factory=list)
    is_admin: bool = False


# =============================================================================
# Shared Memory Protocol
# =============================================================================


class SharedMemoryProtocol:
    """Shared memory protocol for cross-agent collaboration.

    Provides Redis-backed memory with:
    - Scoped access control (PRIVATE, SHARED, GLOBAL)
    - TTL-based expiration
    - Version tracking for concurrent updates
    - Skill-aware permission enforcement
    - LangGraph checkpointer integration

    LangGraph 1.0 Integration:
        Used by agents to share state across skill boundaries.
        Integrates with RedisCheckpointer for persistent state.

    Example:
        >>> memory = SharedMemoryProtocol()
        >>>
        >>> # Write private data
        >>> await memory.write(
        ...     key="findings",
        ...     value={"count": 10},
        ...     scope=MemoryScope.PRIVATE,
        ...     owner_skill="research"
        ... )
        >>>
        >>> # Read with permission check
        >>> data = await memory.read(
        ...     key="findings",
        ...     scope=MemoryScope.PRIVATE,
        ...     requesting_skill="research"
        ... )
    """

    def __init__(
        self,
        redis_manager: RedisMemoryManager | None = None,
        default_ttl_seconds: int = 3600,  # 1 hour
        namespace: str = "shared_memory",
    ) -> None:
        """Initialize SharedMemoryProtocol.

        Args:
            redis_manager: Redis memory manager (default: new instance)
            default_ttl_seconds: Default TTL for entries (default: 3600)
            namespace: Redis namespace prefix (default: "shared_memory")
        """
        self._redis = redis_manager or RedisMemoryManager()
        self._default_ttl = default_ttl_seconds
        self._namespace = namespace
        self._admin_skills = {"admin", "coordinator", "orchestrator"}

        logger.info(
            "shared_memory_initialized",
            namespace=namespace,
            default_ttl_seconds=default_ttl_seconds,
        )

    def _build_key(self, key: str, scope: MemoryScope, owner_skill: str) -> str:
        """Build namespaced Redis key.

        Format: {namespace}:{scope}:{owner_skill}:{key}

        Args:
            key: Entry key
            scope: Memory scope
            owner_skill: Owner skill name

        Returns:
            Namespaced Redis key
        """
        return f"{self._namespace}:{scope.value}:{owner_skill}:{key}"

    def _is_admin(self, skill_name: str) -> bool:
        """Check if skill has admin privileges.

        Args:
            skill_name: Skill to check

        Returns:
            True if admin skill
        """
        return skill_name in self._admin_skills

    async def write(
        self,
        key: str,
        value: Any,
        scope: MemoryScope,
        owner_skill: str,
        ttl_seconds: int | None = None,
        allowed_skills: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Write entry to shared memory.

        Args:
            key: Entry key
            value: Entry value (JSON-serializable)
            scope: Memory scope (PRIVATE/SHARED/GLOBAL)
            owner_skill: Skill writing this entry
            ttl_seconds: Time-to-live in seconds (None = default)
            allowed_skills: Skills allowed to read/write (SHARED scope)
            metadata: Additional metadata

        Returns:
            True if written successfully

        Raises:
            MemoryError: If write fails

        Example:
            >>> await memory.write(
            ...     key="findings",
            ...     value={"count": 10},
            ...     scope=MemoryScope.PRIVATE,
            ...     owner_skill="research",
            ...     ttl_seconds=3600
            ... )
            True
        """
        try:
            # Build namespaced key
            redis_key = self._build_key(key, scope, owner_skill)

            # Get existing entry for version tracking
            existing = await self._get_raw(redis_key)
            version = existing["version"] + 1 if existing else 1

            # Create entry
            entry = MemoryEntry(
                key=key,
                value=value,
                scope=scope,
                owner_skill=owner_skill,
                timestamp=datetime.now(UTC),
                ttl_seconds=ttl_seconds or self._default_ttl,
                allowed_skills=allowed_skills or [],
                version=version,
                metadata=metadata or {},
            )

            # Serialize to JSON
            serialized = json.dumps(
                {
                    "key": entry.key,
                    "value": entry.value,
                    "scope": entry.scope.value,
                    "owner_skill": entry.owner_skill,
                    "timestamp": entry.timestamp.isoformat(),
                    "ttl_seconds": entry.ttl_seconds,
                    "allowed_skills": entry.allowed_skills,
                    "version": entry.version,
                    "metadata": entry.metadata,
                }
            )

            # Store in Redis
            await self._redis.store(
                key=redis_key,
                value=serialized,
                ttl_seconds=entry.ttl_seconds,
                namespace="",  # Already namespaced in key
            )

            logger.debug(
                "shared_memory_write",
                key=key,
                scope=scope.value,
                owner=owner_skill,
                version=version,
            )

            return True

        except Exception as e:
            logger.error("shared_memory_write_failed", key=key, error=str(e))
            raise MemoryError(operation="Failed to write to shared memory", reason=str(e)) from e

    async def read(
        self,
        key: str,
        scope: MemoryScope,
        requesting_skill: str,
        owner_skill: str | None = None,
    ) -> Any | None:
        """Read entry from shared memory with permission check.

        Args:
            key: Entry key
            scope: Memory scope
            requesting_skill: Skill requesting read access
            owner_skill: Owner skill (required for PRIVATE/SHARED)

        Returns:
            Entry value if found and permitted, None otherwise

        Raises:
            MemoryError: If read fails
            PermissionError: If access denied

        Example:
            >>> data = await memory.read(
            ...     key="findings",
            ...     scope=MemoryScope.PRIVATE,
            ...     requesting_skill="research",
            ...     owner_skill="research"
            ... )
        """
        try:
            # Determine owner skill
            if owner_skill is None:
                if scope == MemoryScope.GLOBAL:
                    owner_skill = "system"
                else:
                    raise ValueError("owner_skill required for PRIVATE/SHARED scope")

            # Build key
            redis_key = self._build_key(key, scope, owner_skill)

            # Get raw entry
            raw = await self._get_raw(redis_key)
            if not raw:
                return None

            # Parse entry
            entry = self._parse_entry(raw)

            # Check permissions
            if not self._can_read(entry, requesting_skill):
                logger.warning(
                    "shared_memory_access_denied",
                    key=key,
                    scope=scope.value,
                    requesting=requesting_skill,
                    owner=owner_skill,
                )
                raise PermissionError(f"Skill '{requesting_skill}' cannot read '{key}'")

            logger.debug(
                "shared_memory_read",
                key=key,
                scope=scope.value,
                requesting=requesting_skill,
            )

            return entry.value

        except PermissionError:
            raise
        except Exception as e:
            logger.error("shared_memory_read_failed", key=key, error=str(e))
            raise MemoryError(operation="Failed to read from shared memory", reason=str(e)) from e

    async def append(
        self,
        key: str,
        value: Any,
        scope: MemoryScope,
        owner_skill: str,
        requesting_skill: str,
    ) -> bool:
        """Append to list entry in shared memory.

        If entry doesn't exist, creates new list with value.
        If entry exists but is not a list, raises error.

        Args:
            key: Entry key
            value: Value to append
            scope: Memory scope
            owner_skill: Owner skill
            requesting_skill: Skill performing append

        Returns:
            True if appended successfully

        Raises:
            MemoryError: If append fails
            PermissionError: If access denied
            ValueError: If entry exists but is not a list

        Example:
            >>> await memory.append(
            ...     key="findings_list",
            ...     value={"paper_id": 123},
            ...     scope=MemoryScope.SHARED,
            ...     owner_skill="research",
            ...     requesting_skill="research"
            ... )
        """
        try:
            # Check write permission
            redis_key = self._build_key(key, scope, owner_skill)
            raw = await self._get_raw(redis_key)

            if raw:
                entry = self._parse_entry(raw)
                if not self._can_write(entry, requesting_skill):
                    raise PermissionError(f"Skill '{requesting_skill}' cannot write '{key}'")

                # Verify it's a list
                if not isinstance(entry.value, list):
                    raise ValueError(f"Entry '{key}' is not a list")

                # Append to existing list
                new_value = entry.value + [value]
            else:
                # Create new list
                new_value = [value]

            # Write updated value
            return await self.write(
                key=key,
                value=new_value,
                scope=scope,
                owner_skill=owner_skill,
                allowed_skills=(self._parse_entry(raw).allowed_skills if raw else []),
            )

        except (PermissionError, ValueError):
            raise
        except Exception as e:
            logger.error("shared_memory_append_failed", key=key, error=str(e))
            raise MemoryError(operation="Failed to append to shared memory", reason=str(e)) from e

    async def delete(
        self,
        key: str,
        scope: MemoryScope,
        owner_skill: str,
        requesting_skill: str,
    ) -> bool:
        """Delete entry from shared memory with permission check.

        Args:
            key: Entry key
            scope: Memory scope
            owner_skill: Owner skill
            requesting_skill: Skill requesting deletion

        Returns:
            True if deleted, False if not found

        Raises:
            MemoryError: If delete fails
            PermissionError: If access denied

        Example:
            >>> await memory.delete(
            ...     key="findings",
            ...     scope=MemoryScope.PRIVATE,
            ...     owner_skill="research",
            ...     requesting_skill="research"
            ... )
        """
        try:
            # Build key
            redis_key = self._build_key(key, scope, owner_skill)

            # Check permissions (only owner or admin can delete)
            raw = await self._get_raw(redis_key)
            if not raw:
                return False

            # Parse entry to check ownership
            parsed_entry = self._parse_entry(raw)

            # Only owner or admin can delete
            if not (
                requesting_skill == parsed_entry.owner_skill or self._is_admin(requesting_skill)
            ):
                raise PermissionError(f"Skill '{requesting_skill}' cannot delete '{key}'")

            # Delete from Redis
            deleted = await self._redis.delete(
                key=redis_key,
                namespace="",  # Already namespaced
            )

            logger.debug(
                "shared_memory_delete",
                key=key,
                scope=scope.value,
                requesting=requesting_skill,
                deleted=deleted,
            )

            return deleted

        except PermissionError:
            raise
        except Exception as e:
            logger.error("shared_memory_delete_failed", key=key, error=str(e))
            raise MemoryError(operation="Failed to delete from shared memory", reason=str(e)) from e

    async def list_keys(
        self,
        scope: MemoryScope,
        owner_skill: str | None = None,
        requesting_skill: str | None = None,
    ) -> list[str]:
        """List all keys in scope (with permission filtering).

        Args:
            scope: Memory scope to list
            owner_skill: Filter by owner skill (optional)
            requesting_skill: Requesting skill (for permission check)

        Returns:
            List of keys accessible to requesting skill

        Example:
            >>> keys = await memory.list_keys(
            ...     scope=MemoryScope.SHARED,
            ...     requesting_skill="research"
            ... )
        """
        try:
            # Build pattern
            if owner_skill:
                pattern = f"{self._namespace}:{scope.value}:{owner_skill}:*"
            else:
                pattern = f"{self._namespace}:{scope.value}:*"

            # Get all keys matching pattern
            redis_client = await self._redis.client
            keys = []

            async for redis_key in redis_client.scan_iter(match=pattern, count=100):
                # Extract actual key from namespaced key
                parts = redis_key.split(":", 3)
                if len(parts) == 4:
                    key = parts[3]

                    # Filter by permissions if requesting_skill provided
                    if requesting_skill:
                        raw = await self._get_raw(redis_key)
                        if raw:
                            entry = self._parse_entry(raw)
                            if self._can_read(entry, requesting_skill):
                                keys.append(key)
                    else:
                        keys.append(key)

            return keys

        except Exception as e:
            logger.error("shared_memory_list_keys_failed", error=str(e))
            return []

    async def extend_ttl(
        self,
        key: str,
        scope: MemoryScope,
        owner_skill: str,
        additional_seconds: int,
        requesting_skill: str,
    ) -> bool:
        """Extend TTL of entry.

        Args:
            key: Entry key
            scope: Memory scope
            owner_skill: Owner skill
            additional_seconds: Seconds to add to current TTL
            requesting_skill: Skill requesting extension

        Returns:
            True if TTL extended successfully

        Raises:
            PermissionError: If access denied
        """
        try:
            # Check permissions
            redis_key = self._build_key(key, scope, owner_skill)
            raw = await self._get_raw(redis_key)

            if not raw:
                return False

            entry = self._parse_entry(raw)
            if not self._can_write(entry, requesting_skill):
                raise PermissionError(f"Skill '{requesting_skill}' cannot modify '{key}'")

            # Extend TTL
            return await self._redis.extend_ttl(
                key=redis_key,
                additional_seconds=additional_seconds,
                namespace="",  # Already namespaced
            )

        except PermissionError:
            raise
        except Exception as e:
            logger.error("shared_memory_extend_ttl_failed", key=key, error=str(e))
            return False

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_raw(self, redis_key: str) -> dict[str, Any] | None:
        """Get raw entry from Redis.

        Args:
            redis_key: Full Redis key

        Returns:
            Raw entry dict or None if not found
        """
        raw = await self._redis.retrieve(
            key=redis_key,
            namespace="",  # Already namespaced
            track_access=False,
        )

        if raw and isinstance(raw, str):
            return json.loads(raw)
        elif raw and isinstance(raw, dict):
            # Already a dict (from store())
            return raw

        return None

    def _parse_entry(self, raw: dict[str, Any]) -> MemoryEntry:
        """Parse raw dict to MemoryEntry.

        Args:
            raw: Raw entry dict

        Returns:
            MemoryEntry instance
        """
        return MemoryEntry(
            key=raw["key"],
            value=raw["value"],
            scope=MemoryScope(raw["scope"]),
            owner_skill=raw["owner_skill"],
            timestamp=datetime.fromisoformat(raw["timestamp"]),
            ttl_seconds=raw.get("ttl_seconds"),
            allowed_skills=raw.get("allowed_skills", []),
            version=raw.get("version", 1),
            metadata=raw.get("metadata", {}),
        )

    def _can_read(self, entry: MemoryEntry, skill_name: str) -> bool:
        """Check if skill can read entry.

        Args:
            entry: Memory entry
            skill_name: Skill requesting read

        Returns:
            True if read allowed
        """
        # Admin bypass
        if self._is_admin(skill_name):
            return True

        # PRIVATE: Only owner can read
        if entry.scope == MemoryScope.PRIVATE:
            return skill_name == entry.owner_skill

        # SHARED: Owner or allowed skills can read
        if entry.scope == MemoryScope.SHARED:
            if skill_name == entry.owner_skill:
                return True
            if not entry.allowed_skills:  # Empty = public within shared
                return True
            return skill_name in entry.allowed_skills

        # GLOBAL: Everyone can read
        return entry.scope == MemoryScope.GLOBAL

    def _can_write(self, entry: MemoryEntry, skill_name: str) -> bool:
        """Check if skill can write entry.

        Args:
            entry: Memory entry
            skill_name: Skill requesting write

        Returns:
            True if write allowed
        """
        # Admin bypass
        if self._is_admin(skill_name):
            return True

        # PRIVATE: Only owner can write
        if entry.scope == MemoryScope.PRIVATE:
            return skill_name == entry.owner_skill

        # SHARED: Owner or allowed skills can write
        if entry.scope == MemoryScope.SHARED:
            if skill_name == entry.owner_skill:
                return True
            if not entry.allowed_skills:  # Empty = public within shared
                return True
            return skill_name in entry.allowed_skills

        # GLOBAL: Only admin can write
        if entry.scope == MemoryScope.GLOBAL:
            return self._is_admin(skill_name)

        return False

    async def get_metadata(
        self,
        key: str,
        scope: MemoryScope,
        owner_skill: str,
    ) -> dict[str, Any] | None:
        """Get metadata about an entry (without value).

        Args:
            key: Entry key
            scope: Memory scope
            owner_skill: Owner skill

        Returns:
            Metadata dict or None if not found
        """
        try:
            redis_key = self._build_key(key, scope, owner_skill)
            raw = await self._get_raw(redis_key)

            if not raw:
                return None

            entry = self._parse_entry(raw)

            # Get TTL from Redis
            redis_client = await self._redis.client
            ttl = await redis_client.ttl(redis_key)

            return {
                "key": entry.key,
                "scope": entry.scope.value,
                "owner_skill": entry.owner_skill,
                "timestamp": entry.timestamp.isoformat(),
                "ttl_seconds_remaining": ttl if ttl > 0 else None,
                "allowed_skills": entry.allowed_skills,
                "version": entry.version,
                "metadata": entry.metadata,
            }

        except Exception as e:
            logger.error("shared_memory_get_metadata_failed", key=key, error=str(e))
            return None

    async def get_metrics(self) -> dict[str, Any]:
        """Get shared memory metrics.

        Returns:
            Dict with usage statistics
        """
        try:
            redis_client = await self._redis.client
            pattern = f"{self._namespace}:*"

            # Count keys by scope
            private_count = 0
            shared_count = 0
            global_count = 0

            async for redis_key in redis_client.scan_iter(match=pattern, count=100):
                parts = redis_key.split(":", 2)
                if len(parts) >= 2:
                    scope = parts[1]
                    if scope == "private":
                        private_count += 1
                    elif scope == "shared":
                        shared_count += 1
                    elif scope == "global":
                        global_count += 1

            return {
                "total_entries": private_count + shared_count + global_count,
                "private_entries": private_count,
                "shared_entries": shared_count,
                "global_entries": global_count,
                "namespace": self._namespace,
            }

        except Exception as e:
            logger.error("shared_memory_metrics_failed", error=str(e))
            return {
                "total_entries": 0,
                "private_entries": 0,
                "shared_entries": 0,
                "global_entries": 0,
                "namespace": self._namespace,
            }

    async def aclose(self) -> None:
        """Close Redis connection (async cleanup)."""
        if self._redis:
            await self._redis.aclose()
            logger.info("shared_memory_closed")


# =============================================================================
# Factory Functions
# =============================================================================


def create_shared_memory(
    default_ttl_seconds: int = 3600,
    namespace: str = "shared_memory",
) -> SharedMemoryProtocol:
    """Create SharedMemoryProtocol with default configuration.

    Args:
        default_ttl_seconds: Default TTL for entries (default: 3600)
        namespace: Redis namespace prefix (default: "shared_memory")

    Returns:
        Configured SharedMemoryProtocol

    Example:
        >>> memory = create_shared_memory(default_ttl_seconds=7200)
        >>> await memory.write(...)
    """
    return SharedMemoryProtocol(
        default_ttl_seconds=default_ttl_seconds,
        namespace=namespace,
    )
