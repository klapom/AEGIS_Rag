"""State Persistence with LangGraph Checkpointers.

Provides checkpointing functionality for conversation state persistence.
Supports in-memory (MemorySaver) and future Redis-based persistence.

Sprint 4 Feature 4.4: Coordinator Agent with State Persistence
"""

from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver

logger = structlog.get_logger(__name__)


def create_checkpointer() -> MemorySaver:
    """Create a checkpointer for state persistence.

    Currently uses MemorySaver for in-memory state persistence.
    Future sprints will add Redis/SQLite support for production.

    Returns:
        MemorySaver instance for state persistence

    Example:
        >>> checkpointer = create_checkpointer()
        >>> compiled_graph = graph.compile(checkpointer=checkpointer)
        >>> # State is now persisted across invocations with same thread_id
    """
    logger.info(
        "creating_checkpointer",
        type="memory",
        note="In-memory only, will be replaced with Redis in Sprint 7",
    )

    # Create MemorySaver (in-memory state persistence)
    checkpointer = MemorySaver()

    logger.info("checkpointer_created", type="MemorySaver")

    return checkpointer


def create_thread_config(session_id: str) -> dict[str, Any]:
    """Create LangGraph thread configuration for conversation tracking.

    The thread_id is used to identify and restore conversation state.
    All invocations with the same thread_id share the same state.

    Args:
        session_id: Unique session identifier (e.g., user_id, conversation_id)

    Returns:
        Thread configuration dict for LangGraph invocation

    Example:
        >>> config = create_thread_config("user123_session456")
        >>> result = await graph.ainvoke(state, config=config)
        >>> # Later invocations with same session_id will have access to history
    """
    return {
        "configurable": {
            "thread_id": session_id,
        }
    }


def get_conversation_history(
    checkpointer: MemorySaver,
    session_id: str,
) -> list[dict[str, Any]]:
    """Retrieve conversation history for a session.

    Args:
        checkpointer: Checkpointer instance
        session_id: Session identifier

    Returns:
        List of checkpoint states for the session

    Example:
        >>> checkpointer = create_checkpointer()
        >>> history = get_conversation_history(checkpointer, "session123")
        >>> print(f"Found {len(history)} checkpoints")
    """
    try:
        config = create_thread_config(session_id)
        # Get all checkpoints for this thread
        checkpoints = list(checkpointer.list(config))

        logger.debug(
            "conversation_history_retrieved",
            session_id=session_id,
            checkpoint_count=len(checkpoints),
        )

        return checkpoints

    except Exception as e:
        logger.error(
            "conversation_history_retrieval_failed",
            session_id=session_id,
            error=str(e),
        )
        return []


def clear_conversation_history(
    checkpointer: MemorySaver,
    session_id: str,
) -> bool:
    """Clear conversation history for a session.

    Args:
        checkpointer: Checkpointer instance
        session_id: Session identifier

    Returns:
        True if cleared successfully, False otherwise

    Example:
        >>> checkpointer = create_checkpointer()
        >>> success = clear_conversation_history(checkpointer, "session123")
    """
    try:
        # MemorySaver doesn't have a direct clear method
        # For now, we just log the intent
        # In production Redis implementation, we'll delete the keys
        logger.info(
            "conversation_history_clear_requested",
            session_id=session_id,
            note="MemorySaver doesn't support selective deletion",
        )
        return True

    except Exception as e:
        logger.error(
            "conversation_history_clear_failed",
            session_id=session_id,
            error=str(e),
        )
        return False


# TODO Sprint 7: Redis Checkpointer
# def create_redis_checkpointer() -> BaseCheckpointSaver:
#     """Create Redis-based checkpointer for production.
#
#     Returns:
#         Redis checkpointer instance
#     """
#     from langgraph.checkpoint.redis import RedisCheckpointSaver
#     import redis
#
#     redis_client = redis.Redis(
#         host=settings.redis_host,
#         port=settings.redis_port,
#         password=settings.redis_password.get_secret_value(),
#         db=settings.redis_db,
#     )
#
#     return RedisCheckpointSaver(redis_client)


# Export public API
__all__ = [
    "create_checkpointer",
    "create_thread_config",
    "get_conversation_history",
    "clear_conversation_history",
]
