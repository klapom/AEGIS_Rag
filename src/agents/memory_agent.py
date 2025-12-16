"""Memory Agent for Episodic and Semantic Memory Retrieval.

This module implements the Memory Agent that handles MEMORY intent routing
and executes memory retrieval across the 3-layer memory architecture.

Sprint 7: Feature 7.4 - Memory Agent (LangGraph Integration)
Sprint 48 Feature 48.3: Agent Node Instrumentation (13 SP) - Memory Retrieval
Integrates with Sprint 4 Router and Sprint 7.3 Memory Router.
"""

from datetime import datetime
from typing import Any

import structlog

from src.agents.base_agent import BaseAgent
from src.agents.retry import retry_on_failure
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

# Import will be available after Feature 7.3
try:
    from src.components.memory.memory_router import MemoryRouter, get_memory_router
except ImportError:
    # Placeholder for development - will be replaced by actual implementation
    class MemoryRouter:
        """Placeholder MemoryRouter for development."""

        async def search_memory(
            self,
            query: str,
            layers: list | None = None,
            top_k: int = 5,
        ) -> dict[str, list[dict[str, Any]]]:
            """Placeholder search_memory method."""
            return {}

    def get_memory_router() -> MemoryRouter:
        """Placeholder getter."""
        return MemoryRouter()


logger = structlog.get_logger(__name__)


class MemoryAgent(BaseAgent):
    """Agent for episodic and semantic memory retrieval.

    Processes MEMORY intent queries by:
    1. Routing query to appropriate memory layer(s) (Redis/Qdrant/Graphiti)
    2. Executing memory search via MemoryRouter
    3. Updating AgentState with memory results
    4. Tracking execution metadata

    Inherits from BaseAgent and implements async process() method.
    Uses retry logic for fault tolerance.

    Attributes:
        name: Agent name for logging and tracing
        memory_router: MemoryRouter instance for 3-layer memory access
    """

    def __init__(
        self,
        name: str = "memory_agent",
        memory_router: MemoryRouter | None = None,
    ) -> None:
        """Initialize Memory Agent.

        Args:
            name: Agent name (default: "memory_agent")
            memory_router: MemoryRouter instance (optional, uses singleton if None)
        """
        super().__init__(name=name)
        self.memory_router = memory_router or get_memory_router()

        self.logger.info(
            "memory_agent_initialized",
            agent=name,
        )

    @retry_on_failure(max_attempts=3, min_wait=1.0, max_wait=10.0)
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process memory query and update state.

        Main processing method that:
        1. Extracts query from state
        2. Routes to appropriate memory layer(s) via MemoryRouter
        3. Executes memory search across selected layers
        4. Updates state with results and metadata

        Args:
            state: Current agent state (AgentState dict)

        Returns:
            Updated agent state with memory results

        Raises:
            Exception: If memory search fails after retries
        """
        # Start timing
        timing = self._measure_latency()

        # Extract query
        query = state.get("query", "")
        if not query:
            self.logger.warning("memory_query_no_query", state=state)
            return state

        self.logger.info(
            "memory_query_started",
            query=query[:100],
            intent=state.get("intent", "unknown"),
        )

        # Add agent to trace
        self._add_trace(state, "processing memory query")

        try:
            # Get limit from state config or use default
            limit = state.get("metadata", {}).get("config", {}).get("top_k", 5)

            # Get session_id from state metadata
            session_id = state.get("metadata", {}).get("session_id")

            # Route query to appropriate memory layer(s)
            # MemoryRouter automatically selects layers based on query analysis
            results = await self.memory_router.search_memory(
                query=query,
                session_id=session_id,
                limit=limit,
            )

            # Calculate latency
            latency_ms = self._calculate_latency_ms(timing)

            # Convert results to retrieved_contexts format for state
            retrieved_contexts = []
            layers_used = []

            for layer, layer_results in results.items():
                layers_used.append(layer)

                for i, result in enumerate(layer_results):
                    # Handle different result formats from different layers
                    if isinstance(result, dict):
                        context = {
                            "id": result.get("id", f"{layer}_{i}"),
                            "text": result.get("text", str(result)),
                            "score": result.get("score", 0.0),
                            "source": f"memory_{layer}",
                            "document_id": result.get("document_id", ""),
                            "rank": i,
                            "search_type": "memory",
                            "metadata": {
                                "memory_layer": layer,
                                "timestamp": result.get("timestamp"),
                                **result.get("metadata", {}),
                            },
                        }
                    else:
                        # Fallback for non-dict results
                        context = {
                            "id": f"{layer}_{i}",
                            "text": str(result),
                            "score": 0.0,
                            "source": f"memory_{layer}",
                            "document_id": "",
                            "rank": i,
                            "search_type": "memory",
                            "metadata": {"memory_layer": layer},
                        }

                    retrieved_contexts.append(context)

            # Update state with memory results
            state["memory_results"] = results

            # Append to existing retrieved_contexts (if any)
            if "retrieved_contexts" not in state:
                state["retrieved_contexts"] = []
            state["retrieved_contexts"].extend(retrieved_contexts)

            # Update metadata
            if "metadata" not in state:
                state["metadata"] = {}

            state["metadata"]["memory_search"] = {
                "layers_used": layers_used,
                "total_results": len(retrieved_contexts),
                "results_per_layer": {
                    layer: len(layer_results) for layer, layer_results in results.items()
                },
                "latency_ms": latency_ms,
            }

            # Add memory layers to metadata for tracking
            state["metadata"]["memory_layers_used"] = layers_used

            # Log success
            self._log_success(
                "memory_query",
                query=query[:50],
                layers_used=layers_used,
                total_results=len(retrieved_contexts),
                latency_ms=latency_ms,
            )

            self._add_trace(state, f"memory query complete ({len(layers_used)} layers)")

            return state

        except Exception as e:
            # Calculate latency even on error
            latency_ms = self._calculate_latency_ms(timing)

            self._log_error(
                "memory_query",
                error=e,
                query=query[:50],
                latency_ms=latency_ms,
            )

            # Update state with error information
            if "metadata" not in state:
                state["metadata"] = {}

            state["metadata"]["memory_search"] = {
                "layers_used": [],
                "total_results": 0,
                "results_per_layer": {},
                "latency_ms": latency_ms,
                "error": str(e),
            }

            # Use BaseAgent's error handling
            return await self.handle_error(state, e, "memory_query_processing")


# ============================================================================
# LangGraph Node Function
# ============================================================================


async def memory_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node function for memory query processing.

    This is the node function that gets added to the LangGraph StateGraph.
    It instantiates the MemoryAgent and calls process().

    Sprint 48 Feature 48.3: Emits phase events for memory retrieval.

    Args:
        state: Current agent state

    Returns:
        Updated agent state after memory query processing with phase_event

    Example:
        >>> from langgraph.graph import StateGraph
        >>> graph = StateGraph(AgentState)
        >>> graph.add_node("memory", memory_node)
    """
    logger.info(
        "memory_node_invoked",
        query=state.get("query", "")[:50],
        intent=state.get("intent", "unknown"),
    )

    # Create phase event for memory retrieval
    event = PhaseEvent(
        phase_type=PhaseType.MEMORY_RETRIEVAL,
        status=PhaseStatus.IN_PROGRESS,
        start_time=datetime.utcnow(),
    )

    try:
        # Instantiate agent
        agent = MemoryAgent()

        # Process state
        updated_state = await agent.process(state)

        # Update phase event with success
        event.status = PhaseStatus.COMPLETED
        event.end_time = datetime.utcnow()
        event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000

        # Extract metadata from memory search results
        memory_metadata = updated_state.get("metadata", {}).get("memory_search", {})
        event.metadata = {
            "total_results": memory_metadata.get("total_results", 0),
            "layers_used": memory_metadata.get("layers_used", []),
            "results_per_layer": memory_metadata.get("results_per_layer", {}),
        }

        # Add phase event to state
        updated_state["phase_event"] = event

        logger.info(
            "memory_node_complete",
            query=state.get("query", "")[:50],
            layers_used=event.metadata["layers_used"],
            total_results=event.metadata["total_results"],
            duration_ms=event.duration_ms,
        )

        return updated_state

    except Exception as e:
        # Mark phase event as failed
        event.status = PhaseStatus.FAILED
        event.error = str(e)
        event.end_time = datetime.utcnow()
        event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000

        # Add failed phase event to state
        state["phase_event"] = event

        logger.error(
            "memory_node_failed",
            error=str(e),
            duration_ms=event.duration_ms,
        )

        # Re-raise to let error handling take over
        raise


# Export public API
__all__ = [
    "MemoryAgent",
    "memory_node",
]
