"""Coordinator Agent - Main Orchestrator for Multi-Agent RAG System.

The Coordinator is the entry point for all queries and manages the entire
multi-agent workflow. It initializes state, invokes the LangGraph, and
manages conversation persistence.

Sprint 4 Feature 4.4: Coordinator Agent with State Persistence
Sprint 48 Feature 48.2: CoordinatorAgent Streaming Method (13 SP)
"""

import time
from typing import Any, AsyncGenerator

import structlog
from langgraph.checkpoint.memory import MemorySaver

from src.agents.checkpointer import create_checkpointer, create_thread_config
from src.agents.error_handler import handle_agent_error
from src.agents.graph import compile_graph
from src.agents.reasoning_data import ReasoningData
from src.agents.retry import retry_on_failure
from src.agents.state import create_initial_state
from src.core.config import settings
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

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
        namespaces: list[str] | None = None,
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
            namespaces: Optional list of namespaces to search in (default: ["default", "general"])

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
            ...     session_id="user123_session456",
            ...     namespaces=["default", "project_docs"]
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
                namespaces=namespaces,
            )

            # Create initial state
            initial_state = create_initial_state(
                query=query,
                intent=intent or "hybrid",
                namespaces=namespaces,
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

    async def process_query_stream(
        self,
        query: str,
        session_id: str | None = None,
        intent: str | None = None,
        namespaces: list[str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream phase events and final answer during query processing.

        Sprint 48 Feature 48.2: CoordinatorAgent Streaming Method (13 SP)

        This method provides real-time visibility into the query processing pipeline
        by emitting phase events as each agent executes. It enables the frontend to
        display a thinking process indicator.

        Args:
            query: User's query string
            session_id: Optional session ID for conversation persistence
            intent: Optional intent override (default: let router decide)
            namespaces: Optional list of namespaces to search in

        Yields:
            dict: Events with types:
                - phase_event: PhaseEvent updates (start, progress, completion)
                - answer_chunk: Streaming answer text (final answer)
                - reasoning_complete: Final reasoning summary with all phase events

        Example:
            >>> coordinator = CoordinatorAgent()
            >>> async for event in coordinator.process_query_stream(
            ...     query="What is RAG?",
            ...     session_id="user123"
            ... ):
            ...     if event["type"] == "phase_event":
            ...         print(f"Phase: {event['data']['phase_type']}")
            ...     elif event["type"] == "answer_chunk":
            ...         print(f"Answer: {event['data']['answer']}")
            ...     elif event["type"] == "reasoning_complete":
            ...         print(f"Completed {len(event['data']['phase_events'])} phases")
        """
        reasoning_data = ReasoningData()

        try:
            # Execute workflow and stream phase events
            async for event in self._execute_workflow_with_events(
                query=query,
                session_id=session_id,
                intent=intent,
                namespaces=namespaces,
                reasoning_data=reasoning_data,
            ):
                if isinstance(event, PhaseEvent):
                    # Add to reasoning data accumulator
                    reasoning_data.add_phase_event(event)

                    # Yield phase event to stream (mode='json' converts datetime to ISO strings)
                    yield {
                        "type": "phase_event",
                        "data": event.model_dump(mode='json'),
                    }

                elif isinstance(event, dict) and "answer" in event:
                    # Final answer received
                    yield {
                        "type": "answer_chunk",
                        "data": event,
                    }

            # Emit final reasoning summary
            yield {
                "type": "reasoning_complete",
                "data": reasoning_data.to_dict(),
            }

        except Exception as e:
            logger.error(
                "coordinator_stream_failed",
                query=query[:100],
                session_id=session_id,
                error=str(e),
            )

            # Emit error event
            from datetime import datetime

            error_event = PhaseEvent(
                phase_type=PhaseType.LLM_GENERATION,  # Generic phase for error
                status=PhaseStatus.FAILED,
                start_time=datetime.utcnow(),
                error=str(e),
            )
            yield {
                "type": "phase_event",
                "data": error_event.model_dump(mode='json'),
            }

            # Re-raise for proper error handling
            raise

    async def _execute_workflow_with_events(
        self,
        query: str,
        session_id: str | None,
        intent: str | None,
        namespaces: list[str] | None,
        reasoning_data: ReasoningData,
    ) -> AsyncGenerator[PhaseEvent | dict, None]:
        """Execute LangGraph workflow with phase event emissions.

        This is the core streaming implementation that orchestrates the LangGraph
        workflow and emits phase events as each node executes.

        Args:
            query: User query string
            session_id: Optional session ID for persistence
            intent: Optional intent override
            namespaces: Optional namespace filter
            reasoning_data: ReasoningData accumulator (for internal tracking)

        Yields:
            PhaseEvent or dict: Phase events or final answer

        Note:
            This uses the compiled_graph's astream() method to get real-time
            updates from each node execution.
        """
        start_time = time.perf_counter()

        logger.info(
            "coordinator_stream_started",
            query=query[:100],
            session_id=session_id,
            intent=intent,
        )

        # Create initial state
        initial_state = create_initial_state(
            query=query,
            intent=intent or "hybrid",
            namespaces=namespaces,
        )

        # Create session config
        config = None
        if session_id and self.use_persistence:
            config = create_thread_config(session_id)
            config["recursion_limit"] = self.recursion_limit

        # Stream through LangGraph workflow
        # Note: We use astream() to get updates as each node completes
        final_state = None
        try:
            async for event in self.compiled_graph.astream(initial_state, config=config):
                # DEBUG: Log what astream() is yielding
                logger.info(
                    "astream_event_received",
                    event_type=type(event).__name__,
                    is_dict=isinstance(event, dict),
                    keys=list(event.keys()) if isinstance(event, dict) else None,
                )

                # LangGraph astream yields (node_name, node_output) tuples
                if isinstance(event, dict):
                    # Extract node name and state from event
                    for node_name, node_state in event.items():
                        logger.info(
                            "node_completed",
                            node=node_name,
                            query=query[:50],
                            node_state_type=type(node_state).__name__,
                            has_phase_event="phase_event" in node_state
                            if isinstance(node_state, dict)
                            else False,
                        )

                        # Check if node added a phase_event to state
                        if isinstance(node_state, dict) and "phase_event" in node_state:
                            phase_event = node_state["phase_event"]
                            logger.info(
                                "phase_event_found",
                                node=node_name,
                                phase_type=phase_event.phase_type
                                if isinstance(phase_event, PhaseEvent)
                                else phase_event.get("phase_type"),
                            )
                            if isinstance(phase_event, PhaseEvent):
                                # Yield phase event (will be serialized by API layer)
                                yield phase_event
                            elif isinstance(phase_event, dict):
                                # Convert dict to PhaseEvent if needed
                                yield PhaseEvent(**phase_event)

                        # Keep track of final state
                        final_state = node_state

        except Exception as e:
            logger.error(
                "workflow_execution_failed",
                query=query[:100],
                error=str(e),
            )
            raise

        # Calculate total latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        # If we have a final state, extract the answer
        if final_state and isinstance(final_state, dict):
            answer = final_state.get("answer", "")
            citation_map = final_state.get("citation_map", {})

            logger.info(
                "coordinator_stream_complete",
                query=query[:100],
                latency_ms=latency_ms,
                answer_length=len(answer) if answer else 0,
            )

            # Yield final answer
            yield {
                "answer": answer,
                "citation_map": citation_map,
                "metadata": {
                    "total_latency_ms": latency_ms,
                    "session_id": session_id,
                },
            }

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
