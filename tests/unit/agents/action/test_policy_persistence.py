"""Unit tests for PolicyPersistenceManager.

Sprint 68 Feature 68.7: Tool-Execution Reward Loop (FEAT-007)
Tests Redis persistence for tool selection policies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.action.policy_persistence import PolicyPersistenceManager
from src.agents.action.tool_policy import ToolSelectionPolicy


class TestPolicyPersistenceManager:
    """Test PolicyPersistenceManager class."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis = AsyncMock()
        redis.setex = AsyncMock()
        redis.get = AsyncMock()
        redis.delete = AsyncMock()
        redis.exists = AsyncMock()
        redis.ttl = AsyncMock()
        redis.scan_iter = AsyncMock()
        redis.set = AsyncMock()
        return redis

    @pytest.fixture
    def manager(self, mock_redis):
        """Create persistence manager with mock Redis."""
        return PolicyPersistenceManager(redis_client=mock_redis)

    def test_initialization(self):
        """Test manager initialization."""
        manager = PolicyPersistenceManager(
            key_prefix="test:policy", default_ttl_seconds=3600
        )

        assert manager.key_prefix == "test:policy"
        assert manager.default_ttl_seconds == 3600

    def test_make_key(self, manager):
        """Test Redis key generation."""
        key = manager._make_key("agent_123")

        assert key == "aegis:action:policy:agent_123"

    @pytest.mark.asyncio
    async def test_save_policy(self, manager, mock_redis):
        """Test saving policy to Redis."""
        policy = ToolSelectionPolicy(epsilon=0.1, alpha=0.1)
        policy.q_values[("tool", "context")] = 1.5

        result = await manager.save_policy("agent_1", policy)

        assert result is True
        mock_redis.setex.assert_called_once()
        # Check TTL was set
        args = mock_redis.setex.call_args[0]
        assert args[1] == manager.default_ttl_seconds  # TTL

    @pytest.mark.asyncio
    async def test_save_policy_with_custom_ttl(self, manager, mock_redis):
        """Test saving policy with custom TTL."""
        policy = ToolSelectionPolicy()

        result = await manager.save_policy("agent_1", policy, ttl_seconds=1800)

        assert result is True
        args = mock_redis.setex.call_args[0]
        assert args[1] == 1800  # Custom TTL

    @pytest.mark.asyncio
    async def test_load_policy_success(self, manager, mock_redis):
        """Test loading policy from Redis."""
        # Create policy JSON
        policy = ToolSelectionPolicy(epsilon=0.15, alpha=0.2)
        policy.q_values[("tool", "context")] = 1.5
        policy_json = policy.to_json()

        mock_redis.get.return_value = policy_json

        loaded = await manager.load_policy("agent_1")

        assert loaded is not None
        assert loaded.epsilon == 0.15
        assert loaded.get_q_value("tool", "context") == 1.5
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_policy_not_found(self, manager, mock_redis):
        """Test loading non-existent policy."""
        mock_redis.get.return_value = None

        loaded = await manager.load_policy("agent_1")

        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_policy(self, manager, mock_redis):
        """Test deleting policy from Redis."""
        mock_redis.delete.return_value = 1  # Deleted 1 key

        result = await manager.delete_policy("agent_1")

        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_policy_not_found(self, manager, mock_redis):
        """Test deleting non-existent policy."""
        mock_redis.delete.return_value = 0  # No keys deleted

        result = await manager.delete_policy("agent_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, manager, mock_redis):
        """Test checking if policy exists."""
        mock_redis.exists.return_value = 1  # Key exists

        result = await manager.exists("agent_1")

        assert result is True
        mock_redis.exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_not_found(self, manager, mock_redis):
        """Test checking non-existent policy."""
        mock_redis.exists.return_value = 0  # Key doesn't exist

        result = await manager.exists("agent_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_ttl(self, manager, mock_redis):
        """Test getting TTL for policy."""
        mock_redis.ttl.return_value = 3600

        ttl = await manager.get_ttl("agent_1")

        assert ttl == 3600
        mock_redis.ttl.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ttl_key_not_found(self, manager, mock_redis):
        """Test getting TTL for non-existent key."""
        mock_redis.ttl.return_value = -2  # Key doesn't exist

        ttl = await manager.get_ttl("agent_1")

        assert ttl is None

    @pytest.mark.asyncio
    async def test_get_ttl_no_expiry(self, manager, mock_redis):
        """Test getting TTL for key without expiry."""
        mock_redis.ttl.return_value = -1  # No TTL set

        ttl = await manager.get_ttl("agent_1")

        assert ttl is None

    def test_singleton_getter(self):
        """Test get_policy_persistence_manager singleton."""
        from src.agents.action.policy_persistence import get_policy_persistence_manager

        manager1 = get_policy_persistence_manager()
        manager2 = get_policy_persistence_manager()

        assert manager1 is manager2  # Same instance
