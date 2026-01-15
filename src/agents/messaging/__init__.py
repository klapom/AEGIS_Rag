"""Agent Messaging System for Inter-Agent Communication.

Sprint 94 Feature 94.1: Agent Messaging Bus (8 SP)

This package provides the messaging infrastructure for direct agent-to-agent
communication with skill-aware routing and permission checking.

Modules:
    message_bus: Core message bus with Redis-backed queues
    handoff: LangGraph 1.0 tool-based handoff patterns

Example:
    >>> from src.agents.messaging import MessageBus, create_handoff_tool
    >>> from src.agents.tools.policy import PolicyEngine
    >>>
    >>> # Initialize message bus
    >>> policy = PolicyEngine()
    >>> bus = MessageBus(policy_engine=policy)
    >>>
    >>> # Register agents
    >>> bus.register_agent("coordinator", ["vector_search", "graph_query"])
    >>> bus.register_agent("vector_agent", ["retrieval"])
    >>>
    >>> # Send message
    >>> await bus.send_message(
    ...     sender="coordinator",
    ...     recipient="vector_agent",
    ...     message_type=MessageType.TASK_REQUEST,
    ...     payload={"query": "What is RAG?", "top_k": 5}
    ... )
    >>>
    >>> # Create handoff tool
    >>> handoff = create_handoff_tool("vector_agent", bus)
    >>> result = handoff("What is RAG?")
"""

from src.agents.messaging.handoff import (
    HandoffResult,
    create_handoff_tool,
    create_handoff_tools,
)
from src.agents.messaging.message_bus import (
    AgentMessage,
    MessageBus,
    MessagePriority,
    MessageType,
)

__all__ = [
    "MessageBus",
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "HandoffResult",
    "create_handoff_tool",
    "create_handoff_tools",
]
