"""Coordinator Agent - Main Orchestrator for Multi-Agent RAG System.

The Coordinator is the entry point for all queries and manages the entire
multi-agent workflow. It initializes state, invokes the LangGraph, and
manages conversation persistence.

Sprint 4 Feature 4.4: Coordinator Agent with State Persistence
"""

import time
from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver

from src.agents.checkpointer import create_checkpointer, create_thread_config
from src.agents.error_handler import handle_agent_error
from src.agents.graph import compile_graph
from src.agents.retry import retry_on_failure
from src.agents.state import create_initial_state
from src.core.config import settings

logger = structlog.get_logger(__name__)


class CoordinatorAgent:
    """Main orchestrator agent for the multi-agent RAG system.

    The Coordinator manages:
    - Query initialization and state creation
    - LangGraph compilation and invocation
    - Session-based conversation history
    - Error handling and recovery
    - Performance tracking and observability

    This is the primary interface for external systems (API, CLI, etc.)
    to interact with the RAG system.
    """

    def __init__(
        self,
        use_persistence: bool = True,
        recursion_limit: int | None = None,
    ) -> None:
        """Initialize Coordinator Agent.

        Args:
            use_persistence: Enable conversation persistence (default: True)
            recursion_limit: Max recursion depth for LangGraph (default from settings)
        """
        self.name = "CoordinatorAgent"
        self.use_persistence = use_persistence
        self.recursion_limit = recursion_limit or settings.langgraph_recursion_limit

        # Create checkpointer if persistence is enabled
        self.checkpointer: MemorySaver | None = None
        if self.use_persistence:
            self.checkpointer = create_checkpointer()

        # Compile graph once (reused for all queries)
        self.compiled_graph = compile_graph(checkpointer=self.checkpointer)

        logger.info(
            "coordinator_initialized",
            use_persistence=self.use_persistence,
            recursion_limit=self.recursion_limit,
        )

    @retry_on_failure(max_attempts=2, backoff_factor=1.5)
    async def process_query(
        self,
        query: str,
        session_id: str | None = None,
        intent: str | None = None,
    ) -> dict[str, Any]:
        """Process a user query through the multi-agent system.

        This is the main entry point for query processing. It:
        1. Creates initial state
        2. Sets up session configuration
        3. Invokes the LangGraph
        4. Returns final state with results

        Args:
            query: User's query string
            session_id: Optional session ID for conversation persistence.
                       If None, a new session is created.
            intent: Optional intent override (default: let router decide)

        Returns:
            Final state dictionary containing:
                - query: Original query
                - intent: Detected/assigned intent
                - retrieved_contexts: List of retrieved documents
                - messages: Conversation history
                - metadata: Execution metadata (latency, agent_path, etc.)

        Raises:
            Exception: If query processing fails after retries

        Example:
            >>> coordinator = CoordinatorAgent()
            >>> result = await coordinator.process_query(
            ...     query="What is RAG?",
            ...     session_id="user123_session456"
            ... )
            >>> print(f"Retrieved {len(result['retrieved_contexts'])} docs")
        """
        start_time = time.perf_counter()

        try:
            logger.info(
                "coordinator_processing_query",
                query=query[:100],
                session_id=session_id,
                intent=intent,
            )

            # Create initial state
            initial_state = create_initial_state(
                query=query,
                intent=intent or "hybrid",
            )

            # Create session config
            config = None
            if session_id and self.use_persistence:
                config = create_thread_config(session_id)
                config["recursion_limit"] = self.recursion_limit

            # Invoke graph
            final_state = await self.compiled_graph.ainvoke(
                initial_state,
                config=config,
            )

            # Calculate total latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Add coordinator metadata
            if "metadata" not in final_state:
                final_state["metadata"] = {}

            final_state["metadata"]["coordinator"] = {
                "total_latency_ms": latency_ms,
                "session_id": session_id,
                "use_persistence": self.use_persistence,
            }

            # Ensure agent_path includes coordinator
            if "agent_path" not in final_state["metadata"]:
                final_state["metadata"]["agent_path"] = []
            final_state["metadata"]["agent_path"].insert(0, "coordinator: started")
            final_state["metadata"]["agent_path"].append(
                f"coordinator: completed ({latency_ms:.0f}ms)"
            )

            logger.info(
                "coordinator_query_complete",
                query=query[:100],
                session_id=session_id,
                latency_ms=latency_ms,
                agent_path=final_state["metadata"]["agent_path"],
                result_count=len(final_state.get("retrieved_contexts", [])),
            )

            return final_state

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                "coordinator_query_failed",
                query=query[:100],
                session_id=session_id,
                error=str(e),
                latency_ms=latency_ms,
            )

            # Create error state
            error_state = initial_state if "initial_state" in locals() else {}
            error_state = handle_agent_error(
                error=e,
                state=error_state,
                agent_name=self.name,
                context="Query processing",
            )

            # Add coordinator metadata
            if "metadata" not in error_state:
                error_state["metadata"] = {}
            error_state["metadata"]["coordinator"] = {
                "total_latency_ms": latency_ms,
                "session_id": session_id,
                "failed": True,
            }

            # Re-raise for retry logic
            raise

    async def process_multi_turn(
        self,
        queries: list[str],
        session_id: str,
    ) -> list[dict[str, Any]]:
        """Process multiple queries in the same conversation session.

        All queries share the same session_id, allowing the system to
        maintain context across turns.

        Args:
            queries: List of query strings
            session_id: Session ID for conversation persistence

        Returns:
            List of final states, one per query

        Example:
            >>> coordinator = CoordinatorAgent()
            >>> results = await coordinator.process_multi_turn(
            ...     queries=["What is RAG?", "How does it work?"],
            ...     session_id="conversation123"
            ... )
        """
        results = []

        for i, query in enumerate(queries, 1):
            logger.info(
                "multi_turn_processing",
                turn=i,
                total_turns=len(queries),
                session_id=session_id,
                query=query[:100],
            )

            try:
                result = await self.process_query(
                    query=query,
                    session_id=session_id,
                )
                results.append(result)

            except Exception as e:
                logger.error(
                    "multi_turn_query_failed",
                    turn=i,
                    session_id=session_id,
                    error=str(e),
                )
                # Create error result
                error_result = {
                    "query": query,
                    "error": str(e),
                    "metadata": {
                        "turn": i,
                        "session_id": session_id,
                        "failed": True,
                    },
                }
                results.append(error_result)

        logger.info(
            "multi_turn_complete",
            total_queries=len(queries),
            successful=sum(1 for r in results if "error" not in r),
            failed=sum(1 for r in results if "error" in r),
            session_id=session_id,
        )

        return results

    def get_session_history(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve conversation history for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of checkpoints for the session

        Example:
            >>> history = coordinator.get_session_history("session123")
            >>> print(f"Found {len(history)} checkpoints")
        """
        if not self.use_persistence or not self.checkpointer:
            logger.warning(
                "session_history_unavailable",
                reason="Persistence disabled",
                session_id=session_id,
            )
            return []

        try:
            from src.agents.checkpointer import get_conversation_history

            history = get_conversation_history(self.checkpointer, session_id)
            logger.info(
                "session_history_retrieved",
                session_id=session_id,
                checkpoint_count=len(history),
            )
            return history

        except Exception as e:
            logger.error(
                "session_history_failed",
                session_id=session_id,
                error=str(e),
            )
            return []


# ============================================================================
# Singleton Instance
# ============================================================================

# Global coordinator instance (singleton pattern)
_coordinator: CoordinatorAgent | None = None


def get_coordinator(
    use_persistence: bool = True,
    force_new: bool = False,
) -> CoordinatorAgent:
    """Get global coordinator instance (singleton).

    Args:
        use_persistence: Enable conversation persistence
        force_new: Force creation of new instance (default: False)

    Returns:
        CoordinatorAgent instance

    Example:
        >>> coordinator = get_coordinator()
        >>> result = await coordinator.process_query("What is RAG?")
    """
    global _coordinator

    if _coordinator is None or force_new:
        _coordinator = CoordinatorAgent(use_persistence=use_persistence)

    return _coordinator


# Export public API
__all__ = [
    "CoordinatorAgent",
    "get_coordinator",
]
