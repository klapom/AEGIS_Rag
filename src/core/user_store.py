"""User storage with Redis backend and bcrypt password hashing.

Sprint Context: Sprint 38 (2025-12-08) - Feature 38.1a: JWT Authentication Backend

This module provides user management with Redis as the storage backend.
Users are stored with bcrypt-hashed passwords for security.

Architecture:
    - User data stored in Redis with key prefix "user:"
    - Passwords hashed with bcrypt (cost factor 12)
    - User lookup by username or user_id
    - Automatic timestamp tracking (created_at, updated_at)

Security Features:
    - Bcrypt password hashing (cost factor 12)
    - No plaintext password storage
    - Secure password verification
    - User data isolation by key prefix

Example:
    >>> from src.core.user_store import UserStore, UserCreate, UserInDB
    >>> store = UserStore()
    >>> await store.create_user(UserCreate(
    ...     username="john",
    ...     password="secret123",
    ...     email="john@example.com"
    ... ))
    >>> user = await store.get_user_by_username("john")
    >>> await store.verify_password("secret123", user.hashed_password)
    True

See Also:
    - src/api/v1/auth.py: Authentication endpoints
    - src/core/auth.py: JWT token management
"""

import json
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
import structlog
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator

from src.core.config import settings

logger = structlog.get_logger(__name__)

# Bcrypt password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    """User creation request.

    Attributes:
        username: Unique username (3-50 chars)
        password: Password (min 8 chars)
        email: Email address (optional)
        role: User role (default: user)

    Example:
        >>> user_create = UserCreate(
        ...     username="john_doe",
        ...     password="secure123",
        ...     email="john@example.com"
        ... )
    """

    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=100)
    email: str | None = None
    role: str = Field(default="user", pattern="^(user|admin|superadmin)$")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Basic email validation."""
        if v is not None and v != "":
            if "@" not in v or "." not in v.split("@")[-1]:
                raise ValueError("Invalid email format")
        return v


class UserInDB(BaseModel):
    """User model as stored in database.

    Attributes:
        user_id: Unique user identifier (UUID)
        username: Username
        hashed_password: Bcrypt password hash
        email: Email address (optional)
        role: User role
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        is_active: Account active status

    Example:
        >>> user = UserInDB(
        ...     user_id="user_123",
        ...     username="john",
        ...     hashed_password="$2b$12$...",
        ...     email="john@example.com",
        ...     role="user",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     is_active=True
        ... )
    """

    user_id: str
    username: str
    hashed_password: str
    email: str | None = None
    role: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


class UserPublic(BaseModel):
    """User model for public responses (no password).

    Attributes:
        user_id: Unique user identifier
        username: Username
        email: Email address (optional)
        role: User role
        created_at: Account creation timestamp
        is_active: Account active status

    Example:
        >>> user = UserPublic(
        ...     user_id="user_123",
        ...     username="john",
        ...     email="john@example.com",
        ...     role="user",
        ...     created_at=datetime.now(UTC),
        ...     is_active=True
        ... )
    """

    user_id: str
    username: str
    email: str | None = None
    role: str
    created_at: datetime
    is_active: bool = True


class UserStore:
    """User storage with Redis backend.

    This class manages user data in Redis with bcrypt password hashing.
    All operations are async for non-blocking I/O.

    Attributes:
        redis_client: Redis async client
        key_prefix: Redis key prefix for user data

    Example:
        >>> store = UserStore()
        >>> user = await store.create_user(UserCreate(...))
        >>> retrieved = await store.get_user_by_username(user.username)
        >>> verified = await store.verify_password("password", retrieved.hashed_password)
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        """Initialize user store.

        Args:
            redis_client: Optional Redis client (creates default if None)
        """
        self.redis_client = redis_client or redis.from_url(
            settings.redis_url, decode_responses=True
        )
        self.key_prefix = "user:"
        logger.info("user_store_initialized", redis_url=settings.redis_url)

    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis_client.close()

    def _hash_password(self, password: str) -> str:
        """Hash password with bcrypt.

        Args:
            password: Plaintext password

        Returns:
            Bcrypt password hash

        Example:
            >>> hash = self._hash_password("secret123")
            >>> hash.startswith("$2b$")
            True
        """
        return pwd_context.hash(password)  # type: ignore[no-any-return]

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash.

        Args:
            plain_password: Plaintext password
            hashed_password: Bcrypt password hash

        Returns:
            True if password matches, False otherwise

        Example:
            >>> hash = self._hash_password("secret123")
            >>> await self.verify_password("secret123", hash)
            True
            >>> await self.verify_password("wrong", hash)
            False
        """
        return pwd_context.verify(plain_password, hashed_password)  # type: ignore[no-any-return]

    def _user_key(self, user_id: str) -> str:
        """Generate Redis key for user data.

        Args:
            user_id: User identifier

        Returns:
            Redis key string

        Example:
            >>> self._user_key("user_123")
            'user:user_123'
        """
        return f"{self.key_prefix}{user_id}"

    def _username_key(self, username: str) -> str:
        """Generate Redis key for username-to-userid mapping.

        Args:
            username: Username

        Returns:
            Redis key string

        Example:
            >>> self._username_key("john")
            'user:username:john'
        """
        return f"{self.key_prefix}username:{username}"

    async def create_user(self, user_create: UserCreate) -> UserInDB:
        """Create new user.

        Args:
            user_create: User creation data

        Returns:
            Created user object

        Raises:
            ValueError: If username already exists

        Example:
            >>> user = await store.create_user(UserCreate(
            ...     username="john",
            ...     password="secret123",
            ...     email="john@example.com"
            ... ))
            >>> user.username
            'john'
        """
        # Check if username already exists
        if await self.get_user_by_username(user_create.username):
            logger.warning("user_creation_failed", username=user_create.username, reason="exists")
            raise ValueError(f"Username '{user_create.username}' already exists")

        # Generate user ID
        import uuid

        user_id = f"user_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)

        # Create user object
        user = UserInDB(
            user_id=user_id,
            username=user_create.username,
            hashed_password=self._hash_password(user_create.password),
            email=user_create.email,
            role=user_create.role,
            created_at=now,
            updated_at=now,
            is_active=True,
        )

        # Store in Redis
        user_data = user.model_dump()
        # Convert datetime to ISO format for JSON serialization
        user_data["created_at"] = user.created_at.isoformat()
        user_data["updated_at"] = user.updated_at.isoformat()

        await self.redis_client.set(self._user_key(user_id), json.dumps(user_data))
        await self.redis_client.set(self._username_key(user_create.username), user_id)

        logger.info(
            "user_created",
            user_id=user_id,
            username=user_create.username,
            role=user_create.role,
        )

        return user

    async def get_user_by_username(self, username: str) -> UserInDB | None:
        """Get user by username.

        Args:
            username: Username to lookup

        Returns:
            User object if found, None otherwise

        Example:
            >>> user = await store.get_user_by_username("john")
            >>> user.username if user else None
            'john'
        """
        # Get user_id from username mapping
        user_id = await self.redis_client.get(self._username_key(username))
        if not user_id:
            return None

        return await self.get_user_by_id(user_id)

    async def get_user_by_id(self, user_id: str) -> UserInDB | None:
        """Get user by user_id.

        Args:
            user_id: User identifier

        Returns:
            User object if found, None otherwise

        Example:
            >>> user = await store.get_user_by_id("user_123")
            >>> user.user_id if user else None
            'user_123'
        """
        user_data_str = await self.redis_client.get(self._user_key(user_id))
        if not user_data_str:
            return None

        user_data = json.loads(user_data_str)
        # Convert ISO format back to datetime
        user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
        user_data["updated_at"] = datetime.fromisoformat(user_data["updated_at"])

        return UserInDB(**user_data)

    async def update_user(self, user_id: str, **updates: Any) -> UserInDB | None:
        """Update user data.

        Args:
            user_id: User identifier
            **updates: Fields to update

        Returns:
            Updated user object if found, None otherwise

        Example:
            >>> user = await store.update_user("user_123", email="new@example.com")
            >>> user.email if user else None
            'new@example.com'
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(user, key) and key not in ["user_id", "created_at"]:
                setattr(user, key, value)

        user.updated_at = datetime.now(UTC)

        # Store in Redis
        user_data = user.model_dump()
        user_data["created_at"] = user.created_at.isoformat()
        user_data["updated_at"] = user.updated_at.isoformat()

        await self.redis_client.set(self._user_key(user_id), json.dumps(user_data))

        logger.info("user_updated", user_id=user_id, updated_fields=list(updates.keys()))

        return user

    async def delete_user(self, user_id: str) -> bool:
        """Delete user.

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if not found

        Example:
            >>> deleted = await store.delete_user("user_123")
            >>> deleted
            True
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        # Delete user data and username mapping
        await self.redis_client.delete(self._user_key(user_id))
        await self.redis_client.delete(self._username_key(user.username))

        logger.info("user_deleted", user_id=user_id, username=user.username)

        return True

    def to_public(self, user: UserInDB) -> UserPublic:
        """Convert UserInDB to UserPublic (remove password).

        Args:
            user: User from database

        Returns:
            User without password hash

        Example:
            >>> user_db = UserInDB(...)
            >>> user_public = store.to_public(user_db)
            >>> hasattr(user_public, 'hashed_password')
            False
        """
        return UserPublic(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            is_active=user.is_active,
        )
