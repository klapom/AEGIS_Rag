"""Vector Search Agent with Hybrid Retrieval.

Integrates existing HybridSearch from Sprint 2-3 into LangGraph orchestration.
Performs vector + BM25 search with optional reranking.
"""

from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.agents.base_agent import BaseAgent
from src.agents.state import RetrievedContext
from src.components.vector_search.hybrid_search import HybridSearch
from src.core.config import settings
from src.core.exceptions import VectorSearchError
from src.core.logging import get_logger

logger = get_logger(__name__)


class VectorSearchAgent(BaseAgent):
    """Agent for hybrid vector + keyword search.

    Integrates the existing HybridSearch component from Sprint 2-3.
    Performs retrieval and updates state with results and metadata.
    """

    def __init__(
        self,
        hybrid_search: HybridSearch | None = None,
        top_k: int | None = None,
        use_reranking: bool = True,
        max_retries: int = 3,
    ) -> None:
        """Initialize Vector Search Agent.

        Args:
            hybrid_search: HybridSearch instance (created if None)
            top_k: Number of results to retrieve (default from settings)
            use_reranking: Whether to apply reranking (default: True)
            max_retries: Maximum retry attempts on failure (default: 3)
        """
        super().__init__(name="VectorSearchAgent")
        self.hybrid_search = hybrid_search or HybridSearch()
        self.top_k = top_k or settings.retrieval_top_k
        self.use_reranking = use_reranking
        self.max_retries = max_retries

        self.logger.info(
            "VectorSearchAgent initialized",
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
            # Perform hybrid search with retry logic
            search_result = await self._search_with_retry(query)

            # Convert results to dict format for state
            retrieved_contexts = [
                ctx.model_dump() for ctx in self._convert_results(search_result["results"])
            ]

            # Calculate latency
            latency_ms = self._calculate_latency_ms(timing)

            # Create metadata dict
            metadata = {
                "latency_ms": latency_ms,
                "result_count": len(retrieved_contexts),
                "search_mode": "hybrid",
                "vector_results_count": search_result["search_metadata"]["vector_results_count"],
                "bm25_results_count": search_result["search_metadata"]["bm25_results_count"],
                "reranking_applied": search_result["search_metadata"]["reranking_applied"],
                "error": None,
            }

            # Update state
            state["retrieved_contexts"] = retrieved_contexts
            state["metadata"]["search"] = metadata

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
    async def _search_with_retry(self, query: str) -> dict[str, Any]:
        """Perform hybrid search with retry logic.

        Args:
            query: Search query

        Returns:
            Search results from HybridSearch

        Raises:
            VectorSearchError: If search fails after retries
        """
        try:
            return await self.hybrid_search.hybrid_search(
                query=query,
                top_k=self.top_k,
                use_reranking=self.use_reranking,
            )
        except Exception as e:
            self.logger.warning(
                "Search attempt failed, will retry",
                error=str(e),
                query_length=len(query),
            )
            raise VectorSearchError(query=query, reason=f"Hybrid search failed: {e}") from e

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
                result.get("rerank_score", result.get("rrf_score", result.get("score", 0.0))),
            )

            # Extract rank (final rank from reranking or original rank)
            rank = result.get("final_rank", result.get("rrf_rank", result.get("rank", 0)))

            # Build metadata
            metadata = {
                "search_type": result.get("search_type", "hybrid"),
            }

            # Add reranking metadata if present
            if "rerank_score" in result:
                metadata["rerank_score"] = result["rerank_score"]
                metadata["original_rrf_rank"] = result.get("original_rrf_rank", 0)

            # Add RRF metadata if present
            if "rrf_score" in result:
                metadata["rrf_score"] = result["rrf_score"]
                metadata["rrf_rank"] = result.get("rrf_rank", 0)

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

        return contexts


# ============================================================================
# LangGraph Node Function
# ============================================================================


async def vector_search_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node function for vector search.

    This function is called by LangGraph when the graph executes.
    It instantiates the VectorSearchAgent and processes the state.

    Args:
        state: Current agent state dictionary

    Returns:
        Updated state with search results

    Example:
        >>> from langgraph.graph import StateGraph
        >>> from src.agents.state import AgentState
        >>>
        >>> graph = StateGraph(AgentState)
        >>> graph.add_node("vector_search", vector_search_node)
    """
    agent = VectorSearchAgent(
        top_k=settings.retrieval_top_k,
        use_reranking=True,
    )
    return await agent.process(state)
