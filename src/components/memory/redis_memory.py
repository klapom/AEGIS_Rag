"""Redis Working Memory Manager for Layer 1 Short-Term Memory.

This module provides Redis-based working memory for:
- Recent conversation context
- Temporary query results
- Session-based state
- Fast access to frequently used data
"""

import json
from datetime import datetime
from typing import Any

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.core.config import settings
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


class RedisMemoryManager:
    """Redis-based working memory manager for short-term storage.

    Provides:
    - Session-scoped memory (conversation context)
    - Automatic expiration (TTL-based)
    - Access tracking for consolidation decisions
    - Fast key-value storage for recent interactions
    """

    def __init__(
        self,
        redis_url: str | None = None,
        default_ttl_seconds: int | None = None,
    ):
        """Initialize Redis memory manager.

        Args:
            redis_url: Redis connection URL (default: from settings)
            default_ttl_seconds: Default TTL in seconds (default: from settings)
        """
        self.redis_url = redis_url or settings.redis_memory_url
        self.default_ttl = default_ttl_seconds or settings.redis_memory_ttl_seconds

        self._client: Redis | None = None

        logger.info(
            "Initialized RedisMemoryManager",
            redis_url=self.redis_url,
            default_ttl_seconds=self.default_ttl,
        )

    @property
    async def client(self) -> Redis:
        """Get Redis client (lazy initialization).

        Returns:
            Redis async client

        Raises:
            MemoryError: If connection fails
        """
        if self._client is None:
            try:
                self._client = await Redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._client.ping()
                logger.info("Redis client initialized and connected")
            except Exception as e:
                logger.error("Failed to connect to Redis", error=str(e))
                raise MemoryError(f"Failed to connect to Redis: {e}") from e

        return self._client

    async def store(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
        namespace: str = "memory",
    ) -> bool:
        """Store value in working memory with automatic expiration.

        Args:
            key: Storage key
            value: Value to store (will be JSON serialized)
            ttl_seconds: Time-to-live in seconds (default: from settings)
            namespace: Key namespace prefix (default: "memory")

        Returns:
            True if stored successfully

        Raises:
            MemoryError: If storage fails
        """
        try:
            ttl = ttl_seconds or self.default_ttl
            namespaced_key = f"{namespace}:{key}"

            # Serialize value to JSON
            serialized = json.dumps(
                {
                    "value": value,
                    "stored_at": datetime.utcnow().isoformat(),
                    "access_count": 0,
                }
            )

            redis_client = await self.client
            await redis_client.setex(namespaced_key, ttl, serialized)

            logger.debug(
                "Stored value in working memory",
                key=namespaced_key,
                ttl_seconds=ttl,
            )

            return True

        except Exception as e:
            logger.error("Failed to store in working memory", key=key, error=str(e))
            raise MemoryError(f"Failed to store in working memory: {e}") from e

    async def retrieve(
        self,
        key: str,
        namespace: str = "memory",
        track_access: bool = True,
    ) -> Any | None:
        """Retrieve value from working memory.

        Args:
            key: Storage key
            namespace: Key namespace prefix (default: "memory")
            track_access: Increment access counter (default: True)

        Returns:
            Stored value or None if not found

        Raises:
            MemoryError: If retrieval fails
        """
        try:
            namespaced_key = f"{namespace}:{key}"
            redis_client = await self.client

            serialized = await redis_client.get(namespaced_key)
            if not serialized:
                logger.debug("Key not found in working memory", key=namespaced_key)
                return None

            # Deserialize and update access count
            data = json.loads(serialized)
            value = data.get("value")

            if track_access:
                data["access_count"] = data.get("access_count", 0) + 1
                data["last_accessed_at"] = datetime.utcnow().isoformat()

                # Update with same TTL
                ttl = await redis_client.ttl(namespaced_key)
                if ttl > 0:
                    await redis_client.setex(
                        namespaced_key,
                        ttl,
                        json.dumps(data),
                    )

            logger.debug(
                "Retrieved value from working memory",
                key=namespaced_key,
                access_count=data.get("access_count"),
            )

            return value

        except RedisError as e:
            logger.error("Failed to retrieve from working memory", key=key, error=str(e))
            raise MemoryError(f"Failed to retrieve from working memory: {e}") from e

    async def get_metadata(
        self,
        key: str,
        namespace: str = "memory",
    ) -> dict[str, Any] | None:
        """Get metadata about a stored value (without incrementing access count).

        Args:
            key: Storage key
            namespace: Key namespace prefix (default: "memory")

        Returns:
            Metadata dictionary or None if not found
        """
        try:
            namespaced_key = f"{namespace}:{key}"
            redis_client = await self.client

            serialized = await redis_client.get(namespaced_key)
            if not serialized:
                return None

            data = json.loads(serialized)
            ttl = await redis_client.ttl(namespaced_key)

            return {
                "key": key,
                "namespace": namespace,
                "stored_at": data.get("stored_at"),
                "access_count": data.get("access_count", 0),
                "last_accessed_at": data.get("last_accessed_at"),
                "ttl_seconds": ttl if ttl > 0 else None,
            }

        except Exception as e:
            logger.error("Failed to get metadata", key=key, error=str(e))
            return None

    async def delete(
        self,
        key: str,
        namespace: str = "memory",
    ) -> bool:
        """Delete value from working memory.

        Args:
            key: Storage key
            namespace: Key namespace prefix (default: "memory")

        Returns:
            True if deleted, False if not found
        """
        try:
            namespaced_key = f"{namespace}:{key}"
            redis_client = await self.client

            deleted = await redis_client.delete(namespaced_key)

            logger.debug(
                "Deleted from working memory",
                key=namespaced_key,
                existed=bool(deleted),
            )

            return bool(deleted)

        except Exception as e:
            logger.error("Failed to delete from working memory", key=key, error=str(e))
            return False

    async def get_frequently_accessed(
        self,
        min_access_count: int = 3,
        namespace: str = "memory",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get frequently accessed items for consolidation.

        Args:
            min_access_count: Minimum access count threshold (default: 3)
            namespace: Key namespace prefix (default: "memory")
            limit: Maximum number of items to return (default: 100)

        Returns:
            List of frequently accessed items with metadata
        """
        try:
            redis_client = await self.client
            pattern = f"{namespace}:*"

            items = []
            async for key in redis_client.scan_iter(match=pattern, count=100):
                serialized = await redis_client.get(key)
                if not serialized:
                    continue

                data = json.loads(serialized)
                access_count = data.get("access_count", 0)

                if access_count >= min_access_count:
                    ttl = await redis_client.ttl(key)
                    items.append(
                        {
                            "key": key.replace(f"{namespace}:", ""),
                            "value": data.get("value"),
                            "access_count": access_count,
                            "stored_at": data.get("stored_at"),
                            "last_accessed_at": data.get("last_accessed_at"),
                            "ttl_seconds": ttl if ttl > 0 else None,
                        }
                    )

                # Respect limit
                if len(items) >= limit:
                    break

            # Sort by access count descending
            items.sort(key=lambda x: x["access_count"], reverse=True)

            logger.info(
                "Retrieved frequently accessed items",
                count=len(items),
                min_access_count=min_access_count,
            )

            return items[:limit]

        except Exception as e:
            logger.error("Failed to get frequently accessed items", error=str(e))
            return []

    async def store_conversation_context(
        self,
        session_id: str,
        messages: list[dict[str, str]],
        ttl_seconds: int | None = None,
    ) -> bool:
        """Store conversation context for a session.

        Args:
            session_id: Session identifier
            messages: List of conversation messages
            ttl_seconds: Time-to-live in seconds (default: from settings)

        Returns:
            True if stored successfully
        """
        return await self.store(
            key=f"conversation:{session_id}",
            value=messages,
            ttl_seconds=ttl_seconds,
            namespace="context",
        )

    async def get_conversation_context(
        self,
        session_id: str,
    ) -> list[dict[str, str]] | None:
        """Retrieve conversation context for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of conversation messages or None if not found
        """
        return await self.retrieve(
            key=f"conversation:{session_id}",
            namespace="context",
        )

    async def extend_ttl(
        self,
        key: str,
        additional_seconds: int,
        namespace: str = "memory",
    ) -> bool:
        """Extend the TTL of a stored value.

        Args:
            key: Storage key
            additional_seconds: Seconds to add to current TTL
            namespace: Key namespace prefix (default: "memory")

        Returns:
            True if TTL extended successfully
        """
        try:
            namespaced_key = f"{namespace}:{key}"
            redis_client = await self.client

            current_ttl = await redis_client.ttl(namespaced_key)
            if current_ttl <= 0:
                return False

            new_ttl = current_ttl + additional_seconds
            await redis_client.expire(namespaced_key, new_ttl)

            logger.debug(
                "Extended TTL",
                key=namespaced_key,
                new_ttl_seconds=new_ttl,
            )

            return True

        except Exception as e:
            logger.error("Failed to extend TTL", key=key, error=str(e))
            return False

    async def close(self) -> None:
        """Close Redis connection.

        Deprecated: Use aclose() instead for proper async cleanup.
        """
        await self.aclose()

    async def aclose(self) -> None:
        """Close Redis connection (async cleanup).

        Sprint 13: Proper async cleanup to prevent event loop errors.
        This method should be called in pytest fixture teardown.
        """
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis client closed")


# Global instance (singleton pattern)
_redis_memory: RedisMemoryManager | None = None


def get_redis_memory() -> RedisMemoryManager:
    """Get global Redis memory manager instance (singleton).

    Returns:
        RedisMemoryManager instance
    """
    global _redis_memory
    if _redis_memory is None:
        _redis_memory = RedisMemoryManager()
    return _redis_memory
