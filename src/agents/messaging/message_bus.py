"""Message Bus for Agent-to-Agent Communication with Redis Backing.

Sprint 94 Feature 94.1: Agent Messaging Bus (8 SP)

This module implements a Redis-backed message bus that enables direct
agent-to-agent communication with skill-aware routing and permission checks.

Key Features:
    - Asynchronous message passing with Redis queues
    - Skill-aware routing (agents can only message authorized targets)
    - Multiple message types (task_request, result_share, status_update, error_report)
    - Priority-based message handling
    - Message TTL and automatic expiration
    - Request-response pattern support
    - Broadcast messaging

Architecture:
    ┌─────────────────────────────────────────────────┐
    │              MessageBus                         │
    ├─────────────────────────────────────────────────┤
    │                                                 │
    │  Agent A ──▶ [Queue A] ──▶ Agent A Handler     │
    │  Agent B ──▶ [Queue B] ──▶ Agent B Handler     │
    │                                                 │
    │  Permission Check: PolicyEngine                 │
    │  Storage: Redis (per-agent queues)             │
    │  Correlation: Track request-response pairs      │
    └─────────────────────────────────────────────────┘

Example:
    >>> from src.agents.messaging import MessageBus, MessageType
    >>> from src.agents.tools.policy import PolicyEngine
    >>>
    >>> # Initialize
    >>> policy = PolicyEngine()
    >>> bus = MessageBus(policy_engine=policy)
    >>>
    >>> # Register agents
    >>> bus.register_agent("coordinator", ["vector_search", "graph_query"])
    >>> bus.register_agent("vector_agent", ["retrieval"])
    >>>
    >>> # Send task request
    >>> message_id = await bus.send_message(
    ...     sender="coordinator",
    ...     recipient="vector_agent",
    ...     message_type=MessageType.TASK_REQUEST,
    ...     payload={"query": "What is RAG?", "top_k": 5}
    ... )
    >>>
    >>> # Receive and process
    >>> message = await bus.receive_message("vector_agent")
    >>> result = await process_retrieval(message.payload)
    >>>
    >>> # Send response
    >>> await bus.send_response(
    ...     original_message=message,
    ...     sender="vector_agent",
    ...     payload={"results": result}
    ... )

See Also:
    - src/agents/messaging/handoff.py: LangGraph 1.0 handoff patterns
    - src/agents/tools/policy.py: PolicyEngine for permission checks
    - docs/sprints/SPRINT_94_PLAN.md: Feature specification
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

import structlog
from redis.asyncio import Redis

from src.core.config import settings
from src.core.exceptions import MemoryError

if TYPE_CHECKING:
    from src.agents.tools.policy import PolicyEngine

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class MessageType(Enum):
    """Type of inter-agent message.

    Attributes:
        TASK_REQUEST: Request another agent to perform a task
        RESULT_SHARE: Share results/findings with another agent
        STATUS_UPDATE: Update status of ongoing work
        ERROR_REPORT: Report error/failure to coordinator
        HANDOFF: Hand off task to another agent (LangGraph pattern)
        BROADCAST: Broadcast message to all agents
    """

    TASK_REQUEST = "task_request"
    RESULT_SHARE = "result_share"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    HANDOFF = "handoff"
    BROADCAST = "broadcast"


class MessagePriority(Enum):
    """Priority level for message processing.

    Attributes:
        LOW: Low priority (processed last)
        NORMAL: Normal priority (default)
        HIGH: High priority (processed first)
        URGENT: Urgent priority (immediate processing)
    """

    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class AgentMessage:
    """Message between agents.

    Attributes:
        id: Unique message identifier (UUID)
        sender: Agent ID that sent the message
        recipient: Agent ID to receive message ("*" for broadcast)
        message_type: Type of message
        payload: Message content (dict)
        priority: Message priority level
        timestamp: When message was created
        correlation_id: ID linking request-response pairs
        ttl_seconds: Time-to-live in seconds
        metadata: Additional metadata

    Example:
        >>> message = AgentMessage(
        ...     id=str(uuid.uuid4()),
        ...     sender="coordinator",
        ...     recipient="vector_agent",
        ...     message_type=MessageType.TASK_REQUEST,
        ...     payload={"query": "What is RAG?", "top_k": 5},
        ...     priority=MessagePriority.HIGH,
        ... )
    """

    id: str
    sender: str
    recipient: str
    message_type: MessageType
    payload: dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None
    ttl_seconds: int = 60
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize message to dict for Redis storage.

        Returns:
            Dict representation of message
        """
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentMessage:
        """Deserialize message from dict.

        Args:
            data: Dict representation from Redis

        Returns:
            AgentMessage instance
        """
        return cls(
            id=data["id"],
            sender=data["sender"],
            recipient=data["recipient"],
            message_type=MessageType(data["message_type"]),
            payload=data["payload"],
            priority=MessagePriority(data["priority"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            ttl_seconds=data.get("ttl_seconds", 60),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# Message Bus
# =============================================================================


class MessageBus:
    """Message bus for agent-to-agent communication with Redis backing.

    Provides asynchronous message passing between agents with:
    - Skill-aware routing and permission checks
    - Redis-backed persistent queues
    - Request-response correlation
    - Priority-based message handling
    - Broadcast support
    - Automatic message expiration

    Attributes:
        policy_engine: Optional PolicyEngine for permission checks
        redis_url: Redis connection URL

    Example:
        >>> bus = MessageBus(policy_engine=policy)
        >>> bus.register_agent("coordinator", ["vector_search"])
        >>> await bus.send_message(
        ...     sender="coordinator",
        ...     recipient="vector_agent",
        ...     message_type=MessageType.TASK_REQUEST,
        ...     payload={"query": "test"}
        ... )
    """

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        redis_url: str | None = None,
    ) -> None:
        """Initialize MessageBus.

        Args:
            policy_engine: Optional PolicyEngine for permission checks
            redis_url: Redis connection URL (default: from settings)
        """
        self.policy = policy_engine
        self.redis_url = redis_url or settings.redis_memory_url

        self._client: Redis | None = None
        self._registered_agents: dict[str, list[str]] = {}  # agent_id -> allowed_targets
        self._pending_responses: dict[str, asyncio.Future] = {}  # correlation_id -> Future
        self._lock = asyncio.Lock()

        logger.info(
            "message_bus_initialized",
            has_policy_engine=policy_engine is not None,
            redis_url=self.redis_url,
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
                await self._client.ping()
                logger.info("message_bus_redis_connected")
            except Exception as e:
                logger.error("message_bus_redis_connection_failed", error=str(e))
                raise MemoryError(
                    operation="Failed to connect to Redis for message bus", reason=str(e)
                ) from e

        return self._client

    def register_agent(
        self,
        agent_id: str,
        allowed_targets: list[str] | None = None,
    ) -> None:
        """Register an agent with the message bus.

        Args:
            agent_id: Unique agent identifier
            allowed_targets: List of agent IDs this agent can message (None = all)

        Example:
            >>> bus.register_agent("coordinator", ["vector_agent", "graph_agent"])
            >>> bus.register_agent("vector_agent", ["coordinator"])
        """
        self._registered_agents[agent_id] = allowed_targets or []

        logger.info(
            "agent_registered",
            agent_id=agent_id,
            allowed_target_count=len(allowed_targets) if allowed_targets else "all",
        )

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the message bus.

        Args:
            agent_id: Agent to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        if agent_id not in self._registered_agents:
            return False

        del self._registered_agents[agent_id]

        logger.info("agent_unregistered", agent_id=agent_id)
        return True

    async def send_message(
        self,
        sender: str,
        recipient: str,
        message_type: MessageType,
        payload: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: str | None = None,
        ttl_seconds: int = 60,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Send message to another agent.

        Args:
            sender: Sending agent ID
            recipient: Receiving agent ID ("*" for broadcast)
            message_type: Type of message
            payload: Message content
            priority: Message priority (default: NORMAL)
            correlation_id: Optional correlation ID for request-response
            ttl_seconds: Time-to-live in seconds (default: 60)
            metadata: Optional additional metadata

        Returns:
            Message ID

        Raises:
            ValueError: If sender not registered or permission denied
            MemoryError: If Redis operation fails

        Example:
            >>> message_id = await bus.send_message(
            ...     sender="coordinator",
            ...     recipient="vector_agent",
            ...     message_type=MessageType.TASK_REQUEST,
            ...     payload={"query": "test"},
            ...     priority=MessagePriority.HIGH,
            ... )
        """
        # Validate sender is registered
        if sender not in self._registered_agents:
            raise ValueError(f"Agent '{sender}' not registered with message bus")

        # Check permission (skill-aware routing)
        if recipient != "*":
            await self._check_messaging_permission(sender, recipient)

        # Create message
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id or str(uuid.uuid4()),
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )

        # Send to queue(s)
        if recipient == "*":
            # Broadcast to all registered agents except sender
            for agent_id in self._registered_agents:
                if agent_id != sender:
                    await self._enqueue_message(agent_id, message)
        else:
            await self._enqueue_message(recipient, message)

        logger.info(
            "message_sent",
            message_id=message.id,
            sender=sender,
            recipient=recipient,
            message_type=message_type.value,
            priority=priority.value,
        )

        return message.id

    async def _check_messaging_permission(self, sender: str, recipient: str) -> None:
        """Check if sender can message recipient.

        Args:
            sender: Sending agent ID
            recipient: Receiving agent ID

        Raises:
            ValueError: If permission denied
        """
        # Check if recipient exists
        if recipient not in self._registered_agents:
            raise ValueError(f"Agent '{recipient}' not registered with message bus")

        # Get sender's allowed targets
        allowed_targets = self._registered_agents.get(sender)

        # If allowed_targets is empty list, sender can message anyone
        # If allowed_targets has items, check if recipient is in list
        if allowed_targets and recipient not in allowed_targets:
            logger.warning(
                "messaging_permission_denied",
                sender=sender,
                recipient=recipient,
                allowed_targets=allowed_targets,
            )
            raise ValueError(
                f"Agent '{sender}' not authorized to message '{recipient}'. "
                f"Allowed targets: {allowed_targets}"
            )

        # Optionally check PolicyEngine
        if self.policy:
            # Use can_use_tool as a proxy for messaging permission
            # (treating agent messaging as a "tool" for permission purposes)
            try:
                can_message = await self.policy.can_use_tool(
                    skill_name=sender,
                    tool_name=f"message:{recipient}",
                )
                if not can_message:
                    raise ValueError(
                        f"Policy denied messaging from '{sender}' to '{recipient}'"
                    )
            except ValueError:
                # Re-raise ValueError (permission denied)
                raise
            except Exception as e:
                logger.error(
                    "policy_check_failed",
                    sender=sender,
                    recipient=recipient,
                    error=str(e),
                )
                # Fail open on policy check errors (allow message)

    async def _enqueue_message(self, agent_id: str, message: AgentMessage) -> None:
        """Enqueue message in agent's Redis queue with priority.

        Args:
            agent_id: Agent to receive message
            message: Message to enqueue

        Raises:
            MemoryError: If Redis operation fails
        """
        try:
            redis_client = await self.client
            queue_key = f"agent:queue:{agent_id}"

            # Serialize message
            message_json = json.dumps(message.to_dict())

            # Use sorted set for priority queue
            # Score = priority + timestamp (lower = higher priority)
            score = (10 - message.priority.value) * 1e10 + message.timestamp.timestamp()

            await redis_client.zadd(queue_key, {message_json: score})

            # Set expiration on message
            expiry_time = int((message.timestamp + timedelta(seconds=message.ttl_seconds)).timestamp())
            await redis_client.expireat(queue_key, expiry_time)

            logger.debug(
                "message_enqueued",
                agent_id=agent_id,
                message_id=message.id,
                priority=message.priority.value,
            )

        except Exception as e:
            logger.error(
                "message_enqueue_failed",
                agent_id=agent_id,
                message_id=message.id,
                error=str(e),
            )
            raise MemoryError(
                operation=f"Failed to enqueue message for agent '{agent_id}'", reason=str(e)
            ) from e

    async def receive_message(
        self,
        agent_id: str,
        timeout_seconds: float | None = None,
        block: bool = True,
    ) -> AgentMessage | None:
        """Receive message from agent's queue.

        Args:
            agent_id: Agent ID to receive message for
            timeout_seconds: Timeout for blocking receive (default: None = no timeout)
            block: Whether to block waiting for message (default: True)

        Returns:
            AgentMessage or None if no message available (non-blocking) or timeout

        Raises:
            ValueError: If agent not registered
            MemoryError: If Redis operation fails

        Example:
            >>> # Blocking receive with timeout
            >>> message = await bus.receive_message("vector_agent", timeout_seconds=5.0)
            >>>
            >>> # Non-blocking receive
            >>> message = await bus.receive_message("vector_agent", block=False)
            >>> if message:
            ...     process(message)
        """
        if agent_id not in self._registered_agents:
            raise ValueError(f"Agent '{agent_id}' not registered with message bus")

        try:
            redis_client = await self.client
            queue_key = f"agent:queue:{agent_id}"

            if block:
                # Blocking receive with timeout
                start_time = asyncio.get_event_loop().time()
                while True:
                    # Pop highest priority message (lowest score)
                    result = await redis_client.zpopmin(queue_key, count=1)

                    if result:
                        message_json, _score = result[0]
                        message_dict = json.loads(message_json)
                        message = AgentMessage.from_dict(message_dict)

                        logger.debug(
                            "message_received",
                            agent_id=agent_id,
                            message_id=message.id,
                            sender=message.sender,
                        )

                        return message

                    # Check timeout
                    if timeout_seconds is not None:
                        elapsed = asyncio.get_event_loop().time() - start_time
                        if elapsed >= timeout_seconds:
                            logger.debug(
                                "receive_timeout",
                                agent_id=agent_id,
                                timeout_seconds=timeout_seconds,
                            )
                            return None

                    # Wait a bit before retrying
                    await asyncio.sleep(0.1)
            else:
                # Non-blocking receive
                result = await redis_client.zpopmin(queue_key, count=1)

                if not result:
                    return None

                message_json, _score = result[0]
                message_dict = json.loads(message_json)
                message = AgentMessage.from_dict(message_dict)

                logger.debug(
                    "message_received",
                    agent_id=agent_id,
                    message_id=message.id,
                    sender=message.sender,
                )

                return message

        except Exception as e:
            logger.error(
                "message_receive_failed",
                agent_id=agent_id,
                error=str(e),
            )
            raise MemoryError(
                operation=f"Failed to receive message for agent '{agent_id}'", reason=str(e)
            ) from e

    async def send_response(
        self,
        original_message: AgentMessage,
        sender: str,
        payload: dict[str, Any],
        priority: MessagePriority | None = None,
    ) -> str:
        """Send response to a received message (preserves correlation_id).

        Args:
            original_message: Message being responded to
            sender: Responding agent ID
            payload: Response payload
            priority: Optional priority (defaults to original message priority)

        Returns:
            Response message ID

        Example:
            >>> message = await bus.receive_message("vector_agent")
            >>> results = await perform_search(message.payload["query"])
            >>> await bus.send_response(
            ...     original_message=message,
            ...     sender="vector_agent",
            ...     payload={"results": results}
            ... )
        """
        response_id = await self.send_message(
            sender=sender,
            recipient=original_message.sender,
            message_type=MessageType.RESULT_SHARE,
            payload=payload,
            priority=priority or original_message.priority,
            correlation_id=original_message.correlation_id,
        )

        # If there's a pending future for this correlation, resolve it
        if original_message.correlation_id in self._pending_responses:
            future = self._pending_responses.pop(original_message.correlation_id)
            if not future.done():
                future.set_result(payload)

        return response_id

    async def request_and_wait(
        self,
        sender: str,
        recipient: str,
        payload: dict[str, Any],
        timeout_seconds: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> dict[str, Any] | None:
        """Send request and wait for response (request-response pattern).

        Args:
            sender: Requesting agent ID
            recipient: Agent to handle request
            payload: Request payload
            timeout_seconds: Timeout for waiting response (default: 30s)
            priority: Message priority (default: NORMAL)

        Returns:
            Response payload or None if timeout

        Example:
            >>> response = await bus.request_and_wait(
            ...     sender="coordinator",
            ...     recipient="vector_agent",
            ...     payload={"query": "What is RAG?", "top_k": 5},
            ...     timeout_seconds=10.0,
            ... )
            >>> if response:
            ...     results = response["results"]
        """
        correlation_id = str(uuid.uuid4())

        # Create future for response
        response_future: asyncio.Future = asyncio.Future()
        self._pending_responses[correlation_id] = response_future

        try:
            # Send request
            await self.send_message(
                sender=sender,
                recipient=recipient,
                message_type=MessageType.TASK_REQUEST,
                payload=payload,
                priority=priority,
                correlation_id=correlation_id,
            )

            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout_seconds)

            logger.info(
                "request_response_completed",
                sender=sender,
                recipient=recipient,
                correlation_id=correlation_id,
            )

            return response

        except asyncio.TimeoutError:
            logger.warning(
                "request_response_timeout",
                sender=sender,
                recipient=recipient,
                correlation_id=correlation_id,
                timeout_seconds=timeout_seconds,
            )
            return None

        finally:
            # Clean up pending response
            self._pending_responses.pop(correlation_id, None)

    async def get_queue_size(self, agent_id: str) -> int:
        """Get number of pending messages in agent's queue.

        Args:
            agent_id: Agent ID

        Returns:
            Number of pending messages

        Raises:
            ValueError: If agent not registered
        """
        if agent_id not in self._registered_agents:
            raise ValueError(f"Agent '{agent_id}' not registered with message bus")

        try:
            redis_client = await self.client
            queue_key = f"agent:queue:{agent_id}"

            size = await redis_client.zcard(queue_key)
            return int(size)

        except Exception as e:
            logger.error(
                "get_queue_size_failed",
                agent_id=agent_id,
                error=str(e),
            )
            return 0

    async def clear_queue(self, agent_id: str) -> int:
        """Clear all messages from agent's queue.

        Args:
            agent_id: Agent ID

        Returns:
            Number of messages cleared

        Raises:
            ValueError: If agent not registered
        """
        if agent_id not in self._registered_agents:
            raise ValueError(f"Agent '{agent_id}' not registered with message bus")

        try:
            redis_client = await self.client
            queue_key = f"agent:queue:{agent_id}"

            cleared = await redis_client.delete(queue_key)

            logger.info(
                "queue_cleared",
                agent_id=agent_id,
                messages_cleared=cleared,
            )

            return int(cleared)

        except Exception as e:
            logger.error(
                "clear_queue_failed",
                agent_id=agent_id,
                error=str(e),
            )
            return 0

    def get_registered_agents(self) -> list[str]:
        """Get list of registered agent IDs.

        Returns:
            List of agent IDs
        """
        return list(self._registered_agents.keys())

    def get_agent_targets(self, agent_id: str) -> list[str] | None:
        """Get allowed messaging targets for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of allowed target agent IDs, or None if agent not registered
        """
        return self._registered_agents.get(agent_id)

    async def close(self) -> None:
        """Close Redis connection.

        Should be called on shutdown to properly clean up resources.
        """
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("message_bus_redis_closed")


# =============================================================================
# Factory Functions
# =============================================================================


def create_message_bus(
    policy_engine: PolicyEngine | None = None,
    redis_url: str | None = None,
) -> MessageBus:
    """Factory function to create a MessageBus instance.

    Args:
        policy_engine: Optional PolicyEngine for permission checks
        redis_url: Optional Redis connection URL

    Returns:
        Configured MessageBus instance

    Example:
        >>> from src.agents.tools.policy import create_default_policy_engine
        >>> policy = create_default_policy_engine()
        >>> bus = create_message_bus(policy_engine=policy)
    """
    return MessageBus(policy_engine=policy_engine, redis_url=redis_url)
