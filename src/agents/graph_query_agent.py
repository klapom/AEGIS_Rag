"""Graph Query Agent for Knowledge Graph Retrieval.

This module implements the Graph Query Agent that handles GRAPH intent routing
and executes graph-based knowledge retrieval using dual-level search.

Sprint 5: Feature 5.5 - Graph Query Agent
Integrates with Sprint 4 Router and Sprint 5 DualLevelSearch.
"""

from typing import Any

import structlog

from src.agents.base_agent import BaseAgent
from src.agents.retry import retry_on_failure

try:
    # Try user's implementation first (Feature 5.4)
    from src.components.graph_rag.dual_level_search import (
        DualLevelSearch,
        SearchMode,
        get_dual_level_search,
    )
    from src.core.models import GraphQueryResult as GraphSearchResult
except ImportError:
    # Fallback to placeholder if not available yet
    from src.components.graph_rag.dual_level_search_placeholder import (
        DualLevelSearch,
        GraphSearchResult,
        SearchMode,
        get_dual_level_search,
    )
from src.core.config import settings

logger = structlog.get_logger(__name__)


def classify_search_mode(query: str) -> SearchMode:
    """Classify query to determine optimal search mode.

    Uses heuristics to determine whether to use local (entity-level),
    global (topic-level), or hybrid search based on query characteristics.

    Heuristics:
    - Local: Specific entity questions ("who", "what is", "which")
    - Global: Broad overview questions ("summarize", "overview", "themes")
    - Hybrid: Default for complex or ambiguous queries

    Args:
        query: User query string

    Returns:
        SearchMode enum (LOCAL, GLOBAL, or HYBRID)

    Examples:
        >>> classify_search_mode("Who is John Smith?")
        SearchMode.LOCAL
        >>> classify_search_mode("Summarize the main themes in the documents")
        SearchMode.GLOBAL
        >>> classify_search_mode("How are RAG and LLMs related?")
        SearchMode.HYBRID
    """
    query_lower = query.lower().strip()

    # Local search keywords (specific entity queries)
    local_keywords = [
        "who is",
        "who are",
        "what is",
        "what are",
        "which",
        "where is",
        "when did",
        "define",
        "explain the entity",
        "tell me about",
    ]

    # Global search keywords (broad/overview queries)
    global_keywords = [
        "summarize",
        "summary",
        "overview",
        "main themes",
        "key topics",
        "high-level",
        "overall",
        "general",
        "big picture",
        "what are the major",
        "what are the main",
    ]

    # Check for local keywords
    for keyword in local_keywords:
        if keyword in query_lower:
            logger.debug(
                "search_mode_classified",
                mode="local",
                keyword=keyword,
                query=query[:50],
            )
            return SearchMode.LOCAL

    # Check for global keywords
    for keyword in global_keywords:
        if keyword in query_lower:
            logger.debug(
                "search_mode_classified",
                mode="global",
                keyword=keyword,
                query=query[:50],
            )
            return SearchMode.GLOBAL

    # Default to hybrid for complex/ambiguous queries
    logger.debug(
        "search_mode_classified",
        mode="hybrid",
        reason="default",
        query=query[:50],
    )
    return SearchMode.HYBRID


class GraphQueryAgent(BaseAgent):
    """Agent for graph-based knowledge retrieval.

    Processes GRAPH intent queries by:
    1. Classifying query complexity to determine search mode
    2. Executing dual-level graph search (local/global/hybrid)
    3. Updating AgentState with graph query results
    4. Tracking execution metadata

    Inherits from BaseAgent and implements async process() method.
    Uses retry logic for fault tolerance.

    Attributes:
        name: Agent name for logging and tracing
        dual_level_search: DualLevelSearch instance for graph queries
    """

    def __init__(
        self,
        name: str = "graph_query_agent",
        dual_level_search: DualLevelSearch | None = None,
    ) -> None:
        """Initialize Graph Query Agent.

        Args:
            name: Agent name (default: "graph_query_agent")
            dual_level_search: DualLevelSearch instance (optional, uses singleton if None)
        """
        super().__init__(name=name)
        self.dual_level_search = dual_level_search or get_dual_level_search()

        self.logger.info(
            "graph_query_agent_initialized",
            agent=name,
        )

    @retry_on_failure(max_attempts=3, min_wait=1.0, max_wait=10.0)
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process graph query and update state.

        Main processing method that:
        1. Extracts query from state
        2. Classifies search mode (local/global/hybrid)
        3. Executes graph search via DualLevelSearch
        4. Updates state with results and metadata

        Args:
            state: Current agent state (AgentState dict)

        Returns:
            Updated agent state with graph query results

        Raises:
            Exception: If graph query fails after retries
        """
        # Start timing
        timing = self._measure_latency()

        # Extract query
        query = state.get("query", "")
        if not query:
            self.logger.warning("graph_query_no_query", state=state)
            return state

        self.logger.info(
            "graph_query_started",
            query=query[:100],
            intent=state.get("intent", "unknown"),
        )

        # Add agent to trace
        self._add_trace(state, "processing graph query")

        try:
            # Classify search mode based on query
            search_mode = classify_search_mode(query)

            self.logger.info(
                "graph_query_mode_selected",
                query=query[:50],
                mode=search_mode.value,
            )

            # Execute graph search based on mode
            top_k = getattr(settings, "graph_search_top_k", 10)

            if search_mode == SearchMode.LOCAL:
                # Entity-level search
                entities = await self.dual_level_search.local_search(query=query, top_k=top_k)
                graph_result = GraphSearchResult(
                    query=query,
                    answer=f"Found {len(entities)} entities related to the query.",
                    entities=entities,
                    relationships=[],
                    topics=[],
                    context="",
                    mode="local",
                    metadata={"entities_found": len(entities)},
                )
            elif search_mode == SearchMode.GLOBAL:
                # Topic-level search
                topics = await self.dual_level_search.global_search(
                    query=query, top_k=min(top_k, 5)
                )
                graph_result = GraphSearchResult(
                    query=query,
                    answer=f"Found {len(topics)} topics related to the query.",
                    entities=[],
                    relationships=[],
                    topics=topics,
                    context="",
                    mode="global",
                    metadata={"topics_found": len(topics)},
                )
            else:  # HYBRID
                # Combined search with LLM answer
                graph_result = await self.dual_level_search.hybrid_search(query=query, top_k=top_k)

            # Calculate latency
            latency_ms = self._calculate_latency_ms(timing)

            # Convert Pydantic models to dicts if needed
            entities_list = []
            if graph_result.entities:
                for entity in graph_result.entities:
                    if hasattr(entity, "model_dump"):
                        entities_list.append(entity.model_dump())
                    elif isinstance(entity, dict):
                        entities_list.append(entity)
                    else:
                        entities_list.append({"data": str(entity)})

            relationships_list = []
            if graph_result.relationships:
                for rel in graph_result.relationships:
                    if hasattr(rel, "model_dump"):
                        relationships_list.append(rel.model_dump())
                    elif isinstance(rel, dict):
                        relationships_list.append(rel)
                    else:
                        relationships_list.append({"data": str(rel)})

            topics_list = []
            if graph_result.topics:
                for topic in graph_result.topics:
                    if hasattr(topic, "model_dump"):
                        topics_list.append(topic.model_dump())
                    elif isinstance(topic, dict):
                        topics_list.append(topic)
                    else:
                        topics_list.append({"data": str(topic)})

            # Update state with graph results
            state["graph_query_result"] = {
                "query": graph_result.query,
                "mode": (
                    graph_result.mode
                    if isinstance(graph_result.mode, str)
                    else graph_result.mode.value
                ),
                "answer": graph_result.answer,
                "entities": entities_list,
                "relationships": relationships_list,
                "context": graph_result.context,
                "topics": topics_list,
                "metadata": {
                    **graph_result.metadata,
                    "latency_ms": latency_ms,
                },
            }

            # Add entities as retrieved contexts (for compatibility with vector search)
            if entities_list:
                retrieved_contexts = []
                for i, entity in enumerate(entities_list):
                    context = {
                        "id": entity.get("id", f"entity_{i}"),
                        "text": (
                            f"{entity.get('name', 'Unknown')}: "
                            f"{entity.get('description', 'No description')}"
                        ),
                        "score": entity.get("confidence", 1.0),  # Use confidence as score
                        "source": "graph",
                        "document_id": entity.get("source_document", ""),
                        "rank": i,
                        "search_type": "graph",
                        "metadata": entity,
                    }
                    retrieved_contexts.append(context)

                # Append to existing contexts (if any)
                if "retrieved_contexts" not in state:
                    state["retrieved_contexts"] = []
                state["retrieved_contexts"].extend(retrieved_contexts)

            # Update metadata
            if "metadata" not in state:
                state["metadata"] = {}

            state["metadata"]["graph_search"] = {
                "mode": search_mode.value,
                "entities_found": len(entities_list),
                "relationships_found": len(relationships_list),
                "topics_found": len(topics_list),
                "latency_ms": latency_ms,
            }

            # Log success
            self._log_success(
                "graph_query",
                query=query[:50],
                mode=search_mode.value,
                entities_found=len(entities_list),
                relationships_found=len(relationships_list),
                topics_found=len(topics_list),
                latency_ms=latency_ms,
            )

            self._add_trace(state, f"graph query complete ({search_mode.value} mode)")

            return state

        except Exception as e:
            self._log_error(
                "graph_query",
                error=e,
                query=query[:50],
            )

            # Update state with error
            return await self.handle_error(state, e, "graph_query_processing")


# ============================================================================
# LangGraph Node Function
# ============================================================================


async def graph_query_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node function for graph query processing.

    This is the node function that gets added to the LangGraph StateGraph.
    It instantiates the GraphQueryAgent and calls process().

    Args:
        state: Current agent state

    Returns:
        Updated agent state after graph query processing

    Example:
        >>> from langgraph.graph import StateGraph
        >>> graph = StateGraph(AgentState)
        >>> graph.add_node("graph_query", graph_query_node)
    """
    logger.info(
        "graph_query_node_invoked",
        query=state.get("query", "")[:50],
        intent=state.get("intent", "unknown"),
    )

    # Instantiate agent
    agent = GraphQueryAgent()

    # Process state
    updated_state = await agent.process(state)

    logger.info(
        "graph_query_node_complete",
        query=state.get("query", "")[:50],
        entities_found=updated_state.get("metadata", {})
        .get("graph_search", {})
        .get("entities_found", 0),
    )

    return updated_state


# Export public API
__all__ = [
    "GraphQueryAgent",
    "graph_query_node",
    "classify_search_mode",
    "SearchMode",
]
