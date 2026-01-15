"""LangGraph 1.0 Tool-Based Handoff Patterns for Agent Communication.

Sprint 94 Feature 94.1: Agent Messaging Bus (8 SP)

This module implements LangGraph 1.0's recommended tool-based handoff pattern
for agent-to-agent communication, as an alternative to the langgraph-supervisor
library. This approach provides more control and flexibility.

Key Features:
    - @tool decorated handoff functions for LangGraph integration
    - HandoffResult dataclass for structured responses
    - Factory functions for creating handoff tools
    - Integration with MessageBus for actual message passing
    - Support for both synchronous and asynchronous handoffs

LangGraph 1.0 Pattern:
    Instead of using langgraph-supervisor library, we create @tool decorated
    functions that agents can call to hand off work to other agents.

    >>> from langchain_core.tools import tool
    >>> from langgraph.prebuilt import create_react_agent
    >>>
    >>> @tool
    >>> def handoff_to_retrieval(query: str) -> str:
    ...     '''Hand off to retrieval agent for document search.'''
    ...     return retrieval_agent.invoke({"query": query})
    >>>
    >>> supervisor = create_react_agent(
    ...     model=llm,
    ...     tools=[handoff_to_retrieval, handoff_to_synthesis],
    ...     state_modifier="Coordinate tasks between agents."
    ... )

Example:
    >>> from src.agents.messaging import MessageBus, create_handoff_tool
    >>>
    >>> # Create message bus
    >>> bus = MessageBus()
    >>> bus.register_agent("coordinator", ["vector_agent"])
    >>> bus.register_agent("vector_agent", ["coordinator"])
    >>>
    >>> # Create handoff tool
    >>> handoff_to_vector = create_handoff_tool(
    ...     target_agent="vector_agent",
    ...     message_bus=bus,
    ...     sender_agent="coordinator",
    ... )
    >>>
    >>> # Use in LangGraph agent
    >>> from langgraph.prebuilt import create_react_agent
    >>> agent = create_react_agent(
    ...     model=llm,
    ...     tools=[handoff_to_vector],
    ...     state_modifier="You are a coordinator agent."
    ... )
    >>>
    >>> # Agent can now call handoff_to_vector as a tool
    >>> result = agent.invoke({"messages": [("user", "Search for RAG papers")]})

See Also:
    - src/agents/messaging/message_bus.py: MessageBus implementation
    - docs/sprints/SPRINT_94_PLAN.md: LangGraph 1.0 patterns (lines 26-48)
    - LangGraph docs: https://langchain-ai.github.io/langgraph/
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

import structlog
from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.agents.messaging.message_bus import MessageBus, MessagePriority, MessageType

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class HandoffResult:
    """Result of an agent handoff.

    Attributes:
        success: Whether handoff succeeded
        agent: Target agent that was handed off to
        result: Result from target agent (if success=True)
        error: Error message (if success=False)
        message_id: Message ID from message bus
        duration_seconds: Time taken for handoff

    Example:
        >>> result = HandoffResult(
        ...     success=True,
        ...     agent="vector_agent",
        ...     result={"documents": [...]},
        ...     message_id="abc123",
        ...     duration_seconds=2.5,
        ... )
        >>> if result.success:
        ...     documents = result.result["documents"]
    """

    success: bool
    agent: str
    result: Any = None
    error: str | None = None
    message_id: str | None = None
    duration_seconds: float = 0.0

    def __str__(self) -> str:
        """Human-readable string representation.

        Returns:
            String describing handoff result
        """
        if self.success:
            return f"Handoff to {self.agent} succeeded (took {self.duration_seconds:.2f}s)"
        else:
            return f"Handoff to {self.agent} failed: {self.error}"


# =============================================================================
# Handoff Tool Factory
# =============================================================================


def create_handoff_tool(
    target_agent: str,
    message_bus: MessageBus,
    sender_agent: str,
    timeout_seconds: float = 30.0,
    tool_name: str | None = None,
    tool_description: str | None = None,
) -> Callable[..., HandoffResult]:
    """Create a LangGraph tool for handing off to another agent.

    This follows the LangGraph 1.0 recommended pattern of using @tool decorated
    functions for agent handoff, rather than the langgraph-supervisor library.

    Args:
        target_agent: Agent ID to hand off to
        message_bus: MessageBus instance for communication
        sender_agent: Agent ID that will use this handoff tool
        timeout_seconds: Timeout for waiting for response (default: 30s)
        tool_name: Optional custom tool name (default: "handoff_to_{target}")
        tool_description: Optional custom description

    Returns:
        Tool-decorated function for LangGraph

    Example:
        >>> bus = MessageBus()
        >>> bus.register_agent("coordinator", ["vector_agent"])
        >>> bus.register_agent("vector_agent", ["coordinator"])
        >>>
        >>> handoff = create_handoff_tool(
        ...     target_agent="vector_agent",
        ...     message_bus=bus,
        ...     sender_agent="coordinator",
        ... )
        >>>
        >>> # Can be used directly
        >>> result = handoff(query="What is RAG?", top_k=5)
        >>>
        >>> # Or passed to LangGraph agent
        >>> from langgraph.prebuilt import create_react_agent
        >>> agent = create_react_agent(model=llm, tools=[handoff])
    """
    name = tool_name or f"handoff_to_{target_agent}"
    description = tool_description or f"Hand off task to {target_agent} agent for execution."

    def handoff_tool(input: dict[str, Any]) -> HandoffResult:
        """Hand off task to target agent.

        This tool sends a message to the target agent via the message bus
        and waits for a response.

        Args:
            input: Dict of parameters to pass to target agent

        Returns:
            HandoffResult with execution outcome
        """
        import time

        start_time = time.perf_counter()

        try:
            # Use asyncio.run to execute async request_and_wait
            # (LangChain tools are synchronous, but MessageBus is async)
            response = asyncio.run(
                message_bus.request_and_wait(
                    sender=sender_agent,
                    recipient=target_agent,
                    payload=input,  # Changed from kwargs to input
                    timeout_seconds=timeout_seconds,
                )
            )

            duration = time.perf_counter() - start_time

            if response is not None:
                logger.info(
                    "handoff_succeeded",
                    sender=sender_agent,
                    target=target_agent,
                    duration_seconds=duration,
                )

                return HandoffResult(
                    success=True,
                    agent=target_agent,
                    result=response,
                    duration_seconds=duration,
                )
            else:
                logger.warning(
                    "handoff_timeout",
                    sender=sender_agent,
                    target=target_agent,
                    timeout_seconds=timeout_seconds,
                )

                return HandoffResult(
                    success=False,
                    agent=target_agent,
                    error=f"Timeout after {timeout_seconds}s waiting for {target_agent}",
                    duration_seconds=duration,
                )

        except Exception as e:
            duration = time.perf_counter() - start_time

            logger.error(
                "handoff_failed",
                sender=sender_agent,
                target=target_agent,
                error=str(e),
            )

            return HandoffResult(
                success=False,
                agent=target_agent,
                error=str(e),
                duration_seconds=duration,
            )

    # Decorate with @tool and set attributes
    decorated_tool = tool(handoff_tool)
    decorated_tool.name = name  # Override default name
    decorated_tool.description = description  # Override default description

    return decorated_tool


def create_handoff_tools(
    agent_targets: dict[str, list[str]],
    message_bus: MessageBus,
    timeout_seconds: float = 30.0,
) -> dict[str, list[Callable[..., HandoffResult]]]:
    """Create handoff tools for multiple agents.

    Given a mapping of agents to their allowed targets, creates handoff tools
    for each agent to communicate with its targets.

    Args:
        agent_targets: Dict mapping agent_id -> list of allowed target agent_ids
        message_bus: MessageBus instance
        timeout_seconds: Default timeout for all handoffs

    Returns:
        Dict mapping agent_id -> list of handoff tools for that agent

    Example:
        >>> bus = MessageBus()
        >>> bus.register_agent("coordinator", ["vector_agent", "graph_agent"])
        >>> bus.register_agent("vector_agent", ["coordinator"])
        >>> bus.register_agent("graph_agent", ["coordinator"])
        >>>
        >>> agent_targets = {
        ...     "coordinator": ["vector_agent", "graph_agent"],
        ...     "vector_agent": ["coordinator"],
        ...     "graph_agent": ["coordinator"],
        ... }
        >>>
        >>> all_tools = create_handoff_tools(agent_targets, bus)
        >>> coordinator_tools = all_tools["coordinator"]  # 2 tools
        >>> vector_tools = all_tools["vector_agent"]      # 1 tool
    """
    tools_by_agent: dict[str, list[Callable[..., HandoffResult]]] = {}

    for sender, targets in agent_targets.items():
        tools = []
        for target in targets:
            handoff_tool = create_handoff_tool(
                target_agent=target,
                message_bus=message_bus,
                sender_agent=sender,
                timeout_seconds=timeout_seconds,
            )
            tools.append(handoff_tool)

        tools_by_agent[sender] = tools

        logger.info(
            "handoff_tools_created",
            sender_agent=sender,
            target_count=len(targets),
        )

    return tools_by_agent


# =============================================================================
# Async Handoff Helpers
# =============================================================================


async def async_handoff(
    target_agent: str,
    message_bus: MessageBus,
    sender_agent: str,
    payload: dict[str, Any],
    timeout_seconds: float = 30.0,
) -> HandoffResult:
    """Async handoff to another agent (for use in async contexts).

    This is the async version of handoff, for use when you're already in an
    async context and don't want the overhead of asyncio.run().

    Args:
        target_agent: Agent to hand off to
        message_bus: MessageBus instance
        sender_agent: Agent initiating handoff
        payload: Data to pass to target agent
        timeout_seconds: Timeout for response

    Returns:
        HandoffResult with outcome

    Example:
        >>> async def my_agent_logic():
        ...     result = await async_handoff(
        ...         target_agent="vector_agent",
        ...         message_bus=bus,
        ...         sender_agent="coordinator",
        ...         payload={"query": "test"},
        ...     )
        ...     if result.success:
        ...         return result.result
    """
    import time

    start_time = time.perf_counter()

    try:
        response = await message_bus.request_and_wait(
            sender=sender_agent,
            recipient=target_agent,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

        duration = time.perf_counter() - start_time

        if response is not None:
            logger.info(
                "async_handoff_succeeded",
                sender=sender_agent,
                target=target_agent,
                duration_seconds=duration,
            )

            return HandoffResult(
                success=True,
                agent=target_agent,
                result=response,
                duration_seconds=duration,
            )
        else:
            logger.warning(
                "async_handoff_timeout",
                sender=sender_agent,
                target=target_agent,
                timeout_seconds=timeout_seconds,
            )

            return HandoffResult(
                success=False,
                agent=target_agent,
                error=f"Timeout after {timeout_seconds}s waiting for {target_agent}",
                duration_seconds=duration,
            )

    except Exception as e:
        duration = time.perf_counter() - start_time

        logger.error(
            "async_handoff_failed",
            sender=sender_agent,
            target=target_agent,
            error=str(e),
        )

        return HandoffResult(
            success=False,
            agent=target_agent,
            error=str(e),
            duration_seconds=duration,
        )


# =============================================================================
# Integration Examples
# =============================================================================


def create_coordinator_with_handoffs(
    llm: Any,
    message_bus: MessageBus,
    available_agents: list[str],
) -> Any:
    """Example: Create a coordinator agent with handoff tools.

    This demonstrates the LangGraph 1.0 pattern for creating a supervisor/
    coordinator agent that can delegate to other agents via handoff tools.

    Args:
        llm: Language model for the coordinator
        message_bus: MessageBus instance
        available_agents: List of agent IDs coordinator can delegate to

    Returns:
        LangGraph create_react_agent instance

    Example:
        >>> from langchain_openai import ChatOpenAI
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> bus = MessageBus()
        >>> bus.register_agent("coordinator", ["vector_agent", "graph_agent"])
        >>>
        >>> coordinator = create_coordinator_with_handoffs(
        ...     llm=llm,
        ...     message_bus=bus,
        ...     available_agents=["vector_agent", "graph_agent"],
        ... )
        >>>
        >>> result = coordinator.invoke({
        ...     "messages": [("user", "Find papers about RAG and summarize")]
        ... })
    """
    from langgraph.prebuilt import create_react_agent

    # Create handoff tools for each available agent
    tools = []
    for agent_id in available_agents:
        handoff_tool = create_handoff_tool(
            target_agent=agent_id,
            message_bus=message_bus,
            sender_agent="coordinator",
        )
        tools.append(handoff_tool)

    # Create coordinator with handoff tools
    coordinator = create_react_agent(
        model=llm,
        tools=tools,
        state_modifier=(
            "You are a coordinator agent that delegates tasks to specialized agents. "
            f"Available agents: {', '.join(available_agents)}. "
            "Use the handoff tools to delegate tasks appropriately."
        ),
    )

    logger.info(
        "coordinator_created_with_handoffs",
        available_agents=available_agents,
        tool_count=len(tools),
    )

    return coordinator
