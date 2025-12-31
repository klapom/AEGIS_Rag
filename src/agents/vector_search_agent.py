"""Vector Search Agent with 4-Way Hybrid Retrieval.

Integrates 4-Way Hybrid Search (Vector + BM25 + Graph Local + Graph Global)
with intent-weighted RRF from Sprint 42.

Sprint 48 Feature 48.3: Agent Node Instrumentation (13 SP) - Vector Search
Sprint 42: Intent-Weighted RRF (TD-057)
"""

from datetime import datetime
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.agents.base_agent import BaseAgent
from src.agents.state import RetrievedContext
from src.components.retrieval.four_way_hybrid_search import FourWayHybridSearch
from src.core.config import settings
from src.core.exceptions import VectorSearchError
from src.core.logging import get_logger
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

logger = get_logger(__name__)


class VectorSearchAgent(BaseAgent):
    """Agent for 4-way hybrid search with intent classification.

    Integrates 4-Way Hybrid Search with automatic intent classification.
    Performs retrieval and updates state with results, intent metadata, and weights.
    """

    def __init__(
        self,
        four_way_search: FourWayHybridSearch | None = None,
        top_k: int | None = None,
        use_reranking: bool = False,  # TD-059: Disabled by default
        max_retries: int = 3,
    ) -> None:
        """Initialize Vector Search Agent.

        Args:
            four_way_search: FourWayHybridSearch instance (created if None)
            top_k: Number of results to retrieve (default from settings)
            use_reranking: Whether to apply reranking (default from settings)
            max_retries: Maximum retry attempts on failure (default: 3)
        """
        super().__init__(name="VectorSearchAgent")
        self.four_way_search = four_way_search or FourWayHybridSearch()
        self.top_k = top_k or settings.retrieval_top_k
        # TD-059: Reranking disabled by default (sentence-transformers not in container)
        self.use_reranking = use_reranking
        self.max_retries = max_retries

        self.logger.info(
            "VectorSearchAgent initialized (4-Way Hybrid + Intent)",
            top_k=self.top_k,
            use_reranking=self.use_reranking,
            max_retries=self.max_retries,
        )

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process state and perform hybrid search.

        Args:
            state: Current agent state with query

        Returns:
            Updated state with retrieved contexts and metadata

        Raises:
            VectorSearchError: If search fails after all retries
        """
        query = state.get("query", "")
        if not query:
            self.logger.warning("Empty query received, skipping search")
            if "metadata" not in state:
                state["metadata"] = {}
            if "agent_path" not in state["metadata"]:
                state["metadata"]["agent_path"] = []
            state["metadata"]["agent_path"].append(f"{self.name}: skipped (empty query)")
            return state

        # Track agent execution
        if "metadata" not in state:
            state["metadata"] = {}
        if "agent_path" not in state["metadata"]:
            state["metadata"]["agent_path"] = []
        state["metadata"]["agent_path"].append(f"{self.name}: started")

        timing = self._measure_latency()

        try:
            # Get namespaces from state (Sprint 41 Feature 41.4)
            namespaces = state.get("namespaces")

            # Perform hybrid search with retry logic
            search_result = await self._search_with_retry(query, namespaces=namespaces)

            # Convert results to dict format for state
            retrieved_contexts = [
                ctx.model_dump() for ctx in self._convert_results(search_result["results"])
            ]

            # Calculate latency
            latency_ms = self._calculate_latency_ms(timing)

            # Create metadata dict (Sprint 42: Include intent classification)
            metadata = {
                "latency_ms": latency_ms,
                "result_count": len(retrieved_contexts),
                "search_mode": "4way_hybrid",
                "vector_results_count": search_result["search_metadata"]["vector_results_count"],
                "bm25_results_count": search_result["search_metadata"]["bm25_results_count"],
                "graph_local_results_count": search_result["search_metadata"][
                    "graph_local_results_count"
                ],
                "graph_global_results_count": search_result["search_metadata"][
                    "graph_global_results_count"
                ],
                "reranking_applied": search_result["search_metadata"]["reranking_applied"],
                # Intent classification metadata
                "intent": search_result["search_metadata"]["intent"],
                "intent_confidence": search_result["search_metadata"]["intent_confidence"],
                "intent_method": search_result["search_metadata"]["intent_method"],
                "intent_latency_ms": search_result["search_metadata"]["intent_latency_ms"],
                "weights": search_result["search_metadata"]["weights"],
                # Sprint 52: Channel samples extracted BEFORE fusion for UI display
                "channel_samples": search_result["search_metadata"].get("channel_samples"),
                "error": None,
            }

            # Update state
            state["retrieved_contexts"] = retrieved_contexts
            state["metadata"]["search"] = metadata

            # Store intent at top level for easy access (used by frontend)
            state["metadata"]["detected_intent"] = search_result["search_metadata"]["intent"]
            state["metadata"]["intent_confidence"] = search_result["search_metadata"][
                "intent_confidence"
            ]

            state["metadata"]["agent_path"].append(
                f"{self.name}: completed ({len(retrieved_contexts)} results, {latency_ms:.0f}ms)"
            )
            self._log_success(
                "vector_search",
                query_length=len(query),
                result_count=len(retrieved_contexts),
                latency_ms=latency_ms,
                reranking_applied=metadata["reranking_applied"],
            )

            return state

        except Exception as e:
            latency_ms = self._calculate_latency_ms(timing)
            self._log_error("vector_search", e, query_length=len(query), latency_ms=latency_ms)

            # Set error metadata
            state["metadata"]["search"] = {
                "latency_ms": latency_ms,
                "result_count": 0,
                "search_mode": "hybrid",
                "vector_results_count": 0,
                "bm25_results_count": 0,
                "reranking_applied": False,
                "error": str(e),
            }

            state["metadata"]["agent_path"].append(f"{self.name}: failed: {str(e)}")
            state["metadata"]["error"] = {
                "agent": self.name,
                "error_type": type(e).__name__,
                "message": str(e),
                "context": "Hybrid search execution",
            }
            return state

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(VectorSearchError),
        reraise=True,
    )
    async def _search_with_retry(
        self, query: str, namespaces: list[str] | None = None
    ) -> dict[str, Any]:
        """Perform 4-way hybrid search with intent classification and retry logic.

        Args:
            query: Search query
            namespaces: Optional list of namespaces to search in

        Returns:
            Search results from FourWayHybridSearch with intent metadata

        Raises:
            VectorSearchError: If search fails after retries
        """
        try:
            # Build filters for namespace filtering (Sprint 41 Feature 41.4)
            filters = None
            if namespaces:
                from src.components.retrieval.filters import MetadataFilters

                filters = MetadataFilters(namespace=namespaces)

            # Execute 4-way hybrid search with intent classification
            result = await self.four_way_search.search(
                query=query,
                top_k=self.top_k,
                filters=filters,
                use_reranking=self.use_reranking,
                allowed_namespaces=namespaces,
            )

            # Transform result format to match expected structure
            # FourWayHybridSearch returns: {"query", "results", "intent", "weights", "metadata"}
            # We need to match the old format for compatibility
            return {
                "results": result["results"],
                "search_metadata": {
                    "vector_results_count": result["metadata"].vector_results_count,
                    "bm25_results_count": result["metadata"].bm25_results_count,
                    "graph_local_results_count": result["metadata"].graph_local_results_count,
                    "graph_global_results_count": result["metadata"].graph_global_results_count,
                    "reranking_applied": self.use_reranking,
                    # Sprint 42: Intent classification metadata
                    "intent": result["intent"],
                    "intent_confidence": result["metadata"].intent_confidence,
                    "intent_method": result["metadata"].intent_method,
                    "intent_latency_ms": result["metadata"].intent_latency_ms,
                    "weights": {
                        "vector": result["weights"]["vector"],
                        "bm25": result["weights"]["bm25"],
                        "local": result["weights"]["local"],
                        "global": result["weights"]["global"],
                    },
                    # Sprint 52: Channel samples extracted BEFORE fusion for UI display
                    "channel_samples": result["metadata"].channel_samples,
                },
            }
        except Exception as e:
            self.logger.warning(
                "Search attempt failed, will retry",
                error=str(e),
                query_length=len(query),
                namespaces=namespaces,
            )
            raise VectorSearchError(query=query, reason=f"4-way hybrid search failed: {e}") from e

    def _convert_results(self, results: list[dict[str, Any]]) -> list[RetrievedContext]:
        """Convert HybridSearch results to RetrievedContext format.

        Args:
            results: Results from HybridSearch

        Returns:
            List of RetrievedContext objects
        """
        contexts = []
        for result in results:
            # Extract reranking score if available, otherwise use RRF or original score
            score = result.get(
                "normalized_rerank_score",
                result.get(
                    "rerank_score",
                    result.get(
                        "weighted_rrf_score",
                        result.get("rrf_score", result.get("score", 0.0)),
                    ),
                ),
            )

            # Defensive clipping to [0.0, 1.0] for Pydantic validation
            if score > 1.0 or score < 0.0:
                self.logger.warning(
                    "Score out of bounds, clipping to [0.0, 1.0]",
                    original_score=score,
                    result_id=result.get("id", "unknown"),
                )
                score = max(0.0, min(1.0, score))

            # Extract rank (final rank from reranking or original rank)
            rank = result.get("final_rank", result.get("rrf_rank", result.get("rank", 0)))

            # Sprint 51 Fix: Start with metadata from result (includes document metadata from Qdrant)
            result_metadata = result.get("metadata", {})
            metadata = {
                "search_type": result.get("search_type", "hybrid"),
                # Include document metadata for frontend display
                "source": result_metadata.get("source", result.get("source", "")),
                "format": result_metadata.get("format", ""),
                "file_type": result_metadata.get("file_type", ""),
                "file_size": result_metadata.get("file_size"),
                "page_count": result_metadata.get("page_count"),
                "page": result_metadata.get("page"),
                "created_at": result_metadata.get("created_at"),
                "parser": result_metadata.get("parser", ""),
                "section_headings": result_metadata.get("section_headings", []),
                "namespace": result_metadata.get("namespace", "default"),
            }

            # Add reranking metadata if present
            if "rerank_score" in result:
                metadata["rerank_score"] = result["rerank_score"]
                metadata["original_rrf_rank"] = result.get("original_rrf_rank", 0)

            # Add RRF metadata if present
            if "rrf_score" in result:
                metadata["rrf_score"] = result["rrf_score"]
                metadata["rrf_rank"] = result.get("rrf_rank", 0)

            # Try to create RetrievedContext with detailed error logging
            try:
                context = RetrievedContext(
                    id=result.get("id", ""),
                    text=result.get("text", ""),
                    score=float(score),
                    source=result.get("source", "unknown"),
                    document_id=result.get("document_id", ""),
                    rank=int(rank),
                    search_type=result.get("search_type", "hybrid"),
                    metadata=metadata,
                )
                contexts.append(context)
            except Exception as e:
                self.logger.error(
                    "Failed to create RetrievedContext, skipping result",
                    error=str(e),
                    result_id=result.get("id", "unknown"),
                    search_type=result.get("search_type", "unknown"),
                    score=score,
                    rank=rank,
                    text_preview=result.get("text", "")[:100],
                )
                # Continue with next result instead of failing completely
                continue

        return contexts


# ============================================================================
# LangGraph Node Function
# ============================================================================


async def vector_search_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node function for vector search.

    This function is called by LangGraph when the graph executes.
    It instantiates the VectorSearchAgent and processes the state.

    Sprint 48 Feature 48.3: Emits phase events for vector search.
    Sprint 51 Feature 51.1: Emits granular phase events for all sub-phases.

    Args:
        state: Current agent state dictionary

    Returns:
        Updated state with search results and phase_event

    Example:
        >>> from langgraph.graph import StateGraph
        >>> from src.agents.state import AgentState
        >>>
        >>> graph = StateGraph(AgentState)
        >>> graph.add_node("vector_search", vector_search_node)
    """
    import time

    start_time = time.perf_counter()

    # Initialize phase_events list if not present
    if "phase_events" not in state:
        state["phase_events"] = []

    try:
        # Execute vector search (this internally runs vector, BM25, graph, and RRF)
        agent = VectorSearchAgent(
            top_k=settings.retrieval_top_k,
            use_reranking=False,  # TD-059: Disabled - sentence-transformers not in container
        )
        result_state = await agent.process(state)

        # Extract metadata from search results
        search_metadata = result_state.get("metadata", {}).get("search", {})

        # Sprint 51 Fix: Emit individual phase events for each sub-phase
        # that was executed in the four-way hybrid search

        # 1. Vector Search Phase
        if search_metadata.get("vector_results_count", 0) > 0:
            vector_event = PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=search_metadata.get("latency_ms", 0) * 0.3,  # Approximate 30% of total
                metadata={
                    "results_count": search_metadata.get("vector_results_count", 0),
                },
            )
            result_state["phase_events"].append(vector_event)

        # 2. BM25 Search Phase
        if search_metadata.get("bm25_results_count", 0) > 0:
            bm25_event = PhaseEvent(
                phase_type=PhaseType.BM25_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=search_metadata.get("latency_ms", 0) * 0.3,  # Approximate 30% of total
                metadata={
                    "results_count": search_metadata.get("bm25_results_count", 0),
                },
            )
            result_state["phase_events"].append(bm25_event)

        # 3. Graph Local Search Phase (if executed)
        if search_metadata.get("graph_local_results_count", 0) > 0:
            graph_local_event = PhaseEvent(
                phase_type=PhaseType.GRAPH_QUERY,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=search_metadata.get("latency_ms", 0) * 0.2,  # Approximate 20% of total
                metadata={
                    "results_count": search_metadata.get("graph_local_results_count", 0),
                    "search_type": "local",
                },
            )
            result_state["phase_events"].append(graph_local_event)

        # 4. RRF Fusion Phase
        rrf_event = PhaseEvent(
            phase_type=PhaseType.RRF_FUSION,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=search_metadata.get("latency_ms", 0) * 0.2,  # Approximate 20% of total
            metadata={
                "final_results_count": search_metadata.get("result_count", 0),
                "intent": search_metadata.get("intent", "hybrid"),
                "weights": search_metadata.get("weights", {}),
            },
        )
        result_state["phase_events"].append(rrf_event)

        # For compatibility, also add the last phase event as phase_event
        result_state["phase_event"] = rrf_event

        total_duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            "vector_search_phases_complete",
            duration_ms=total_duration,
            phase_count=len(result_state["phase_events"]),
            results_count=search_metadata.get("result_count", 0),
        )

        return result_state

    except Exception as e:
        # Mark as failed
        error_event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.FAILED,
            error=str(e),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=(time.perf_counter() - start_time) * 1000,
        )

        state["phase_event"] = error_event
        if "phase_events" in state:
            state["phase_events"].append(error_event)

        logger.error(
            "vector_search_phase_failed",
            error=str(e),
            duration_ms=error_event.duration_ms,
        )

        # Re-raise to let error handling take over
        raise
