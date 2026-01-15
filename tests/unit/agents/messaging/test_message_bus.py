"""Unit tests for MessageBus.

Sprint 94 Feature 94.1: Agent Messaging Bus (8 SP)

Tests cover:
- Agent registration and unregistration
- Message sending and receiving
- Skill-aware routing and permission checks
- Priority-based message handling
- Request-response pattern
- Broadcast messaging
- Queue management
- Error handling
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio import Redis

from src.agents.messaging.message_bus import (
    AgentMessage,
    MessageBus,
    MessagePriority,
    MessageType,
    create_message_bus,
)
from src.core.exceptions import MemoryError


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock(spec=Redis)
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.zpopmin = AsyncMock(return_value=[])
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.delete = AsyncMock(return_value=0)
    redis_mock.expireat = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_policy():
    """Mock PolicyEngine."""
    policy = MagicMock()
    policy.can_use_tool = AsyncMock(return_value=True)
    return policy


@pytest.fixture
async def message_bus(mock_redis, mock_policy):
    """MessageBus instance with mocked Redis."""
    bus = MessageBus(policy_engine=mock_policy, redis_url="redis://localhost:6379/0")

    # Inject mock client directly (bypass lazy init)
    bus._client = mock_redis

    yield bus

    # Cleanup
    await bus.close()


# =============================================================================
# Test AgentMessage Serialization
# =============================================================================


def test_agent_message_to_dict():
    """Test AgentMessage.to_dict() serialization."""
    timestamp = datetime.now(UTC)
    message = AgentMessage(
        id="msg-123",
        sender="agent-a",
        recipient="agent-b",
        message_type=MessageType.TASK_REQUEST,
        payload={"query": "test"},
        priority=MessagePriority.HIGH,
        timestamp=timestamp,
        correlation_id="corr-123",
        ttl_seconds=60,
        metadata={"key": "value"},
    )

    data = message.to_dict()

    assert data["id"] == "msg-123"
    assert data["sender"] == "agent-a"
    assert data["recipient"] == "agent-b"
    assert data["message_type"] == "task_request"
    assert data["payload"] == {"query": "test"}
    assert data["priority"] == 2  # HIGH = 2
    assert data["timestamp"] == timestamp.isoformat()
    assert data["correlation_id"] == "corr-123"
    assert data["ttl_seconds"] == 60
    assert data["metadata"] == {"key": "value"}


def test_agent_message_from_dict():
    """Test AgentMessage.from_dict() deserialization."""
    timestamp = datetime.now(UTC)
    data = {
        "id": "msg-123",
        "sender": "agent-a",
        "recipient": "agent-b",
        "message_type": "task_request",
        "payload": {"query": "test"},
        "priority": 2,  # HIGH
        "timestamp": timestamp.isoformat(),
        "correlation_id": "corr-123",
        "ttl_seconds": 60,
        "metadata": {"key": "value"},
    }

    message = AgentMessage.from_dict(data)

    assert message.id == "msg-123"
    assert message.sender == "agent-a"
    assert message.recipient == "agent-b"
    assert message.message_type == MessageType.TASK_REQUEST
    assert message.payload == {"query": "test"}
    assert message.priority == MessagePriority.HIGH
    assert message.timestamp == timestamp
    assert message.correlation_id == "corr-123"
    assert message.ttl_seconds == 60
    assert message.metadata == {"key": "value"}


def test_agent_message_roundtrip():
    """Test serialization roundtrip."""
    original = AgentMessage(
        id="msg-123",
        sender="agent-a",
        recipient="agent-b",
        message_type=MessageType.RESULT_SHARE,
        payload={"results": [1, 2, 3]},
        priority=MessagePriority.URGENT,
        correlation_id="corr-456",
    )

    data = original.to_dict()
    restored = AgentMessage.from_dict(data)

    assert restored.id == original.id
    assert restored.sender == original.sender
    assert restored.recipient == original.recipient
    assert restored.message_type == original.message_type
    assert restored.payload == original.payload
    assert restored.priority == original.priority
    assert restored.correlation_id == original.correlation_id


# =============================================================================
# Test Agent Registration
# =============================================================================


def test_register_agent(message_bus):
    """Test agent registration."""
    message_bus.register_agent("agent-a", ["agent-b", "agent-c"])

    assert "agent-a" in message_bus.get_registered_agents()
    assert message_bus.get_agent_targets("agent-a") == ["agent-b", "agent-c"]


def test_register_agent_no_targets(message_bus):
    """Test agent registration without specific targets (can message all)."""
    message_bus.register_agent("agent-a")

    assert "agent-a" in message_bus.get_registered_agents()
    assert message_bus.get_agent_targets("agent-a") == []


def test_unregister_agent(message_bus):
    """Test agent unregistration."""
    message_bus.register_agent("agent-a", ["agent-b"])

    result = message_bus.unregister_agent("agent-a")

    assert result is True
    assert "agent-a" not in message_bus.get_registered_agents()


def test_unregister_nonexistent_agent(message_bus):
    """Test unregistering agent that doesn't exist."""
    result = message_bus.unregister_agent("nonexistent")

    assert result is False


# =============================================================================
# Test Message Sending
# =============================================================================


@pytest.mark.asyncio
async def test_send_message_success(message_bus, mock_redis):
    """Test successful message sending."""
    message_bus.register_agent("agent-a", ["agent-b"])
    message_bus.register_agent("agent-b")

    message_id = await message_bus.send_message(
        sender="agent-a",
        recipient="agent-b",
        message_type=MessageType.TASK_REQUEST,
        payload={"query": "test"},
        priority=MessagePriority.HIGH,
    )

    assert message_id is not None
    assert isinstance(message_id, str)

    # Verify Redis zadd was called
    mock_redis.zadd.assert_called_once()
    call_args = mock_redis.zadd.call_args
    assert "agent:queue:agent-b" in call_args[0]


@pytest.mark.asyncio
async def test_send_message_unregistered_sender(message_bus):
    """Test sending message from unregistered sender."""
    message_bus.register_agent("agent-b")

    with pytest.raises(ValueError, match="not registered"):
        await message_bus.send_message(
            sender="agent-a",  # Not registered
            recipient="agent-b",
            message_type=MessageType.TASK_REQUEST,
            payload={"query": "test"},
        )


@pytest.mark.asyncio
async def test_send_message_permission_denied(message_bus):
    """Test sending message to unauthorized recipient."""
    message_bus.register_agent("agent-a", ["agent-b"])  # Only allowed to message agent-b
    message_bus.register_agent("agent-c")

    with pytest.raises(ValueError, match="not authorized"):
        await message_bus.send_message(
            sender="agent-a",
            recipient="agent-c",  # Not in allowed list
            message_type=MessageType.TASK_REQUEST,
            payload={"query": "test"},
        )


@pytest.mark.asyncio
async def test_send_message_to_nonexistent_recipient(message_bus):
    """Test sending message to non-existent recipient."""
    message_bus.register_agent("agent-a", ["agent-b"])

    with pytest.raises(ValueError, match="not registered"):
        await message_bus.send_message(
            sender="agent-a",
            recipient="agent-b",  # Not registered
            message_type=MessageType.TASK_REQUEST,
            payload={"query": "test"},
        )


@pytest.mark.asyncio
async def test_send_message_broadcast(message_bus, mock_redis):
    """Test broadcast message to all agents."""
    message_bus.register_agent("agent-a")
    message_bus.register_agent("agent-b")
    message_bus.register_agent("agent-c")

    message_id = await message_bus.send_message(
        sender="agent-a",
        recipient="*",  # Broadcast
        message_type=MessageType.STATUS_UPDATE,
        payload={"status": "ready"},
    )

    assert message_id is not None

    # Should have enqueued to agent-b and agent-c (not sender)
    assert mock_redis.zadd.call_count == 2


@pytest.mark.asyncio
async def test_send_message_with_correlation_id(message_bus, mock_redis):
    """Test sending message with correlation ID."""
    message_bus.register_agent("agent-a", ["agent-b"])
    message_bus.register_agent("agent-b")

    correlation_id = "corr-123"
    message_id = await message_bus.send_message(
        sender="agent-a",
        recipient="agent-b",
        message_type=MessageType.TASK_REQUEST,
        payload={"query": "test"},
        correlation_id=correlation_id,
    )

    assert message_id is not None

    # Verify correlation_id in message
    call_args = mock_redis.zadd.call_args
    message_json = list(call_args[0][1].keys())[0]
    message_dict = json.loads(message_json)
    assert message_dict["correlation_id"] == correlation_id


# =============================================================================
# Test Message Receiving
# =============================================================================


@pytest.mark.asyncio
async def test_receive_message_success(message_bus, mock_redis):
    """Test receiving a message from queue."""
    message_bus.register_agent("agent-b")

    # Mock Redis returning a message
    test_message = AgentMessage(
        id="msg-123",
        sender="agent-a",
        recipient="agent-b",
        message_type=MessageType.TASK_REQUEST,
        payload={"query": "test"},
    )
    message_json = json.dumps(test_message.to_dict())
    mock_redis.zpopmin.return_value = [(message_json, 100)]

    message = await message_bus.receive_message("agent-b", block=False)

    assert message is not None
    assert message.id == "msg-123"
    assert message.sender == "agent-a"
    assert message.payload == {"query": "test"}


@pytest.mark.asyncio
async def test_receive_message_empty_queue(message_bus, mock_redis):
    """Test receiving from empty queue (non-blocking)."""
    message_bus.register_agent("agent-b")

    mock_redis.zpopmin.return_value = []

    message = await message_bus.receive_message("agent-b", block=False)

    assert message is None


@pytest.mark.asyncio
async def test_receive_message_unregistered_agent(message_bus):
    """Test receiving message for unregistered agent."""
    with pytest.raises(ValueError, match="not registered"):
        await message_bus.receive_message("nonexistent", block=False)


@pytest.mark.asyncio
async def test_receive_message_blocking_timeout(message_bus, mock_redis):
    """Test blocking receive with timeout."""
    message_bus.register_agent("agent-b")

    mock_redis.zpopmin.return_value = []

    message = await message_bus.receive_message("agent-b", timeout_seconds=0.1, block=True)

    assert message is None


# =============================================================================
# Test Request-Response Pattern
# =============================================================================


@pytest.mark.asyncio
async def test_send_response(message_bus, mock_redis):
    """Test sending response to original message."""
    message_bus.register_agent("agent-a", ["agent-b"])
    message_bus.register_agent("agent-b", ["agent-a"])

    original_message = AgentMessage(
        id="msg-123",
        sender="agent-a",
        recipient="agent-b",
        message_type=MessageType.TASK_REQUEST,
        payload={"query": "test"},
        correlation_id="corr-123",
    )

    response_id = await message_bus.send_response(
        original_message=original_message,
        sender="agent-b",
        payload={"results": [1, 2, 3]},
    )

    assert response_id is not None

    # Verify response was sent to original sender
    call_args = mock_redis.zadd.call_args
    assert "agent:queue:agent-a" in call_args[0]

    # Verify correlation_id preserved
    message_json = list(call_args[0][1].keys())[0]
    message_dict = json.loads(message_json)
    assert message_dict["correlation_id"] == "corr-123"


@pytest.mark.asyncio
async def test_request_and_wait_success(message_bus, mock_redis):
    """Test request-and-wait pattern with successful response."""
    message_bus.register_agent("agent-a", ["agent-b"])
    message_bus.register_agent("agent-b", ["agent-a"])

    # Simulate response being received
    async def simulate_response():
        await asyncio.sleep(0.1)
        # Get correlation_id from pending_responses
        correlation_ids = list(message_bus._pending_responses.keys())
        if correlation_ids:
            correlation_id = correlation_ids[0]
            future = message_bus._pending_responses[correlation_id]
            if not future.done():
                future.set_result({"results": [1, 2, 3]})

    # Start background task to simulate response
    asyncio.create_task(simulate_response())

    response = await message_bus.request_and_wait(
        sender="agent-a",
        recipient="agent-b",
        payload={"query": "test"},
        timeout_seconds=1.0,
    )

    assert response is not None
    assert response == {"results": [1, 2, 3]}


@pytest.mark.asyncio
async def test_request_and_wait_timeout(message_bus):
    """Test request-and-wait with timeout."""
    message_bus.register_agent("agent-a", ["agent-b"])
    message_bus.register_agent("agent-b")

    response = await message_bus.request_and_wait(
        sender="agent-a",
        recipient="agent-b",
        payload={"query": "test"},
        timeout_seconds=0.1,  # Short timeout
    )

    assert response is None


# =============================================================================
# Test Queue Management
# =============================================================================


@pytest.mark.asyncio
async def test_get_queue_size(message_bus, mock_redis):
    """Test getting queue size."""
    message_bus.register_agent("agent-b")

    mock_redis.zcard.return_value = 5

    size = await message_bus.get_queue_size("agent-b")

    assert size == 5
    mock_redis.zcard.assert_called_once_with("agent:queue:agent-b")


@pytest.mark.asyncio
async def test_get_queue_size_unregistered(message_bus):
    """Test getting queue size for unregistered agent."""
    with pytest.raises(ValueError, match="not registered"):
        await message_bus.get_queue_size("nonexistent")


@pytest.mark.asyncio
async def test_clear_queue(message_bus, mock_redis):
    """Test clearing agent's queue."""
    message_bus.register_agent("agent-b")

    mock_redis.delete.return_value = 3

    cleared = await message_bus.clear_queue("agent-b")

    assert cleared == 3
    mock_redis.delete.assert_called_once_with("agent:queue:agent-b")


@pytest.mark.asyncio
async def test_clear_queue_unregistered(message_bus):
    """Test clearing queue for unregistered agent."""
    with pytest.raises(ValueError, match="not registered"):
        await message_bus.clear_queue("nonexistent")


# =============================================================================
# Test Message Priority
# =============================================================================


@pytest.mark.asyncio
async def test_message_priority_ordering(message_bus, mock_redis):
    """Test that messages are enqueued with priority scores."""
    message_bus.register_agent("agent-a", ["agent-b"])
    message_bus.register_agent("agent-b")

    # Send high priority message
    await message_bus.send_message(
        sender="agent-a",
        recipient="agent-b",
        message_type=MessageType.TASK_REQUEST,
        payload={"urgent": True},
        priority=MessagePriority.URGENT,
    )

    # Verify score calculation (lower score = higher priority)
    call_args = mock_redis.zadd.call_args
    score = list(call_args[0][1].values())[0]

    # URGENT priority (3) should result in lower score
    # Score = (10 - priority) * 1e10 + timestamp
    # For URGENT: (10 - 3) * 1e10 = 7e10
    assert score < 8e10  # Should be in 7e10 range


# =============================================================================
# Test Error Handling
# =============================================================================


@pytest.mark.asyncio
async def test_redis_connection_failure():
    """Test handling Redis connection failure."""
    bus = MessageBus(redis_url="redis://invalid:9999/0")

    with patch.object(Redis, "from_url") as mock_from_url:
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock(side_effect=Exception("Connection failed"))
        mock_from_url.return_value = mock_client

        with pytest.raises(MemoryError, match="Failed to connect"):
            await bus.client


@pytest.mark.asyncio
async def test_enqueue_message_failure(message_bus, mock_redis):
    """Test handling Redis enqueue failure."""
    message_bus.register_agent("agent-a", ["agent-b"])
    message_bus.register_agent("agent-b")

    mock_redis.zadd.side_effect = Exception("Redis error")

    with pytest.raises(MemoryError, match="Failed to enqueue"):
        await message_bus.send_message(
            sender="agent-a",
            recipient="agent-b",
            message_type=MessageType.TASK_REQUEST,
            payload={"query": "test"},
        )


# =============================================================================
# Test Factory Function
# =============================================================================


def test_create_message_bus():
    """Test factory function."""
    bus = create_message_bus(redis_url="redis://localhost:6379/0")

    assert bus is not None
    assert isinstance(bus, MessageBus)


def test_create_message_bus_with_policy(mock_policy):
    """Test factory function with policy engine."""
    bus = create_message_bus(policy_engine=mock_policy)

    assert bus is not None
    assert bus.policy is mock_policy


# =============================================================================
# Test Policy Engine Integration
# =============================================================================


@pytest.mark.asyncio
async def test_policy_engine_check_on_send(message_bus, mock_policy):
    """Test that policy engine is consulted on message send."""
    message_bus.register_agent("agent-a", ["agent-b"])
    message_bus.register_agent("agent-b")

    mock_policy.can_use_tool.return_value = True

    await message_bus.send_message(
        sender="agent-a",
        recipient="agent-b",
        message_type=MessageType.TASK_REQUEST,
        payload={"query": "test"},
    )

    # Verify policy was checked
    mock_policy.can_use_tool.assert_called()


@pytest.mark.asyncio
async def test_policy_engine_denies_message(message_bus, mock_policy, mock_redis):
    """Test policy engine denying message."""
    message_bus.register_agent("agent-a", ["agent-b"])
    message_bus.register_agent("agent-b")

    # Set policy to deny
    async def deny_all(*args, **kwargs):
        return False

    mock_policy.can_use_tool = AsyncMock(side_effect=deny_all)

    with pytest.raises(ValueError, match="Policy denied"):
        await message_bus.send_message(
            sender="agent-a",
            recipient="agent-b",
            message_type=MessageType.TASK_REQUEST,
            payload={"query": "test"},
        )


# =============================================================================
# Test Cleanup
# =============================================================================


@pytest.mark.asyncio
async def test_close(message_bus, mock_redis):
    """Test closing message bus connection."""
    await message_bus.close()

    mock_redis.close.assert_called_once()
    assert message_bus._client is None
