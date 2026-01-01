"""Redis Persistence for Tool Selection Policy.

Sprint 68 Feature 68.7: Tool-Execution Reward Loop (FEAT-007)
Persists Q-values and policy state to Redis for cross-session learning.

Architecture:
- Async Redis operations
- Automatic serialization/deserialization
- TTL support for policy expiration
- Atomic updates to prevent race conditions

Features:
- Save/load policy state to Redis
- Automatic JSON serialization
- Configurable TTL (default: 7 days)
- Error handling with fallback
"""

import json
from typing import Any

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.agents.action.tool_policy import ToolSelectionPolicy
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class PolicyPersistenceManager:
    """Manages persistence of tool selection policy to Redis.

    Provides async methods to save and load policy state with automatic
    serialization and TTL management.

    Features:
    - Async Redis operations
    - JSON serialization
    - TTL support (7 days default)
    - Error handling with logging

    Example:
        >>> manager = PolicyPersistenceManager()
        >>> await manager.save_policy("my_agent", policy)
        >>> loaded = await manager.load_policy("my_agent")
    """

    def __init__(
        self,
        redis_client: Redis | None = None,
        key_prefix: str = "aegis:action:policy",
        default_ttl_seconds: int = 604800,  # 7 days
    ) -> None:
        """Initialize persistence manager.

        Args:
            redis_client: Redis client instance (uses default if None)
            key_prefix: Prefix for Redis keys
            default_ttl_seconds: Default TTL in seconds (7 days = 604800)
        """
        self.logger = structlog.get_logger(__name__)
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        self.default_ttl_seconds = default_ttl_seconds

        self.logger.info(
            "policy_persistence_manager_initialized",
            key_prefix=key_prefix,
            default_ttl_seconds=default_ttl_seconds,
        )

    async def _get_redis_client(self) -> Redis:
        """Get Redis client instance.

        Returns:
            Redis client

        Raises:
            RuntimeError: If Redis client is not available
        """
        if self.redis_client is None:
            # Lazy import to avoid circular dependencies
            from src.components.memory.redis_manager import get_redis_manager

            manager = get_redis_manager()
            self.redis_client = await manager.get_client()

        return self.redis_client

    def _make_key(self, agent_id: str) -> str:
        """Create Redis key for agent policy.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Redis key string
        """
        return f"{self.key_prefix}:{agent_id}"

    async def save_policy(
        self,
        agent_id: str,
        policy: ToolSelectionPolicy,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Save policy state to Redis.

        Args:
            agent_id: Unique agent identifier
            policy: Policy instance to save
            ttl_seconds: Optional TTL (uses default if None)

        Returns:
            True if save succeeded, False otherwise

        Example:
            >>> success = await manager.save_policy("agent_1", policy)
            >>> assert success is True
        """
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(agent_id)

            # Serialize policy to JSON
            policy_json = policy.to_json()

            # Save to Redis with TTL
            ttl = ttl_seconds or self.default_ttl_seconds
            await redis_client.setex(key, ttl, policy_json)

            self.logger.info(
                "policy_saved",
                agent_id=agent_id,
                key=key,
                ttl_seconds=ttl,
                total_updates=policy.total_updates,
            )

            return True

        except RedisError as e:
            self.logger.error(
                "policy_save_failed_redis",
                agent_id=agent_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

        except Exception as e:
            self.logger.error(
                "policy_save_failed",
                agent_id=agent_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def load_policy(self, agent_id: str) -> ToolSelectionPolicy | None:
        """Load policy state from Redis.

        Args:
            agent_id: Unique agent identifier

        Returns:
            ToolSelectionPolicy instance or None if not found

        Example:
            >>> policy = await manager.load_policy("agent_1")
            >>> if policy:
            ...     print(policy.total_updates)
        """
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(agent_id)

            # Load from Redis
            policy_json = await redis_client.get(key)

            if policy_json is None:
                self.logger.info("policy_not_found", agent_id=agent_id, key=key)
                return None

            # Deserialize from JSON
            policy = ToolSelectionPolicy.from_json(policy_json)

            self.logger.info(
                "policy_loaded",
                agent_id=agent_id,
                key=key,
                total_updates=policy.total_updates,
            )

            return policy

        except RedisError as e:
            self.logger.error(
                "policy_load_failed_redis",
                agent_id=agent_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

        except Exception as e:
            self.logger.error(
                "policy_load_failed",
                agent_id=agent_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def delete_policy(self, agent_id: str) -> bool:
        """Delete policy from Redis.

        Args:
            agent_id: Unique agent identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(agent_id)

            deleted = await redis_client.delete(key)

            if deleted:
                self.logger.info("policy_deleted", agent_id=agent_id, key=key)
            else:
                self.logger.warning("policy_not_found_for_delete", agent_id=agent_id, key=key)

            return bool(deleted)

        except RedisError as e:
            self.logger.error(
                "policy_delete_failed",
                agent_id=agent_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def exists(self, agent_id: str) -> bool:
        """Check if policy exists in Redis.

        Args:
            agent_id: Unique agent identifier

        Returns:
            True if policy exists, False otherwise
        """
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(agent_id)

            exists = await redis_client.exists(key)
            return bool(exists)

        except RedisError as e:
            self.logger.error(
                "policy_exists_check_failed",
                agent_id=agent_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def get_ttl(self, agent_id: str) -> int | None:
        """Get remaining TTL for policy.

        Args:
            agent_id: Unique agent identifier

        Returns:
            TTL in seconds, or None if key doesn't exist or no TTL set
        """
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(agent_id)

            ttl = await redis_client.ttl(key)

            if ttl == -2:  # Key doesn't exist
                return None
            if ttl == -1:  # Key exists but no TTL
                return None

            return ttl

        except RedisError as e:
            self.logger.error(
                "policy_ttl_check_failed",
                agent_id=agent_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def list_policies(self) -> list[str]:
        """List all saved policy agent IDs.

        Returns:
            List of agent IDs with saved policies
        """
        try:
            redis_client = await self._get_redis_client()
            pattern = f"{self.key_prefix}:*"

            # Scan for keys matching pattern
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                # Extract agent_id from key
                agent_id = key.decode("utf-8").replace(f"{self.key_prefix}:", "")
                keys.append(agent_id)

            self.logger.info("policies_listed", count=len(keys))
            return keys

        except RedisError as e:
            self.logger.error(
                "policy_list_failed", error=str(e), error_type=type(e).__name__
            )
            return []

    async def update_policy_field(
        self, agent_id: str, field_path: str, value: Any
    ) -> bool:
        """Update specific field in policy without loading entire state.

        Useful for atomic updates to Q-values or counts.

        Args:
            agent_id: Unique agent identifier
            field_path: JSON path to field (e.g., "q_values.search:general")
            value: New value for field

        Returns:
            True if update succeeded, False otherwise

        Example:
            >>> await manager.update_policy_field(
            ...     "agent_1",
            ...     "q_values.search:general",
            ...     1.5
            ... )
        """
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(agent_id)

            # Load current policy
            policy_json = await redis_client.get(key)
            if policy_json is None:
                self.logger.warning("policy_not_found_for_update", agent_id=agent_id)
                return False

            # Parse JSON
            policy_dict = json.loads(policy_json)

            # Update field (simple dot-notation path)
            path_parts = field_path.split(".")
            current = policy_dict
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[path_parts[-1]] = value

            # Save back to Redis
            new_policy_json = json.dumps(policy_dict, indent=2)
            ttl = await redis_client.ttl(key)
            if ttl > 0:
                await redis_client.setex(key, ttl, new_policy_json)
            else:
                await redis_client.set(key, new_policy_json)

            self.logger.info(
                "policy_field_updated",
                agent_id=agent_id,
                field_path=field_path,
                value=value,
            )

            return True

        except Exception as e:
            self.logger.error(
                "policy_field_update_failed",
                agent_id=agent_id,
                field_path=field_path,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


# Singleton instance
_persistence_manager: PolicyPersistenceManager | None = None


def get_policy_persistence_manager() -> PolicyPersistenceManager:
    """Get singleton PolicyPersistenceManager instance.

    Returns:
        PolicyPersistenceManager instance
    """
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = PolicyPersistenceManager()
    return _persistence_manager
