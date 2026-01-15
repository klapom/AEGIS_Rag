"""Graph Query Agent for Knowledge Graph Retrieval.

This module implements the Graph Query Agent that handles GRAPH intent routing
and executes graph-based knowledge retrieval using dual-level search.

Sprint 5: Feature 5.5 - Graph Query Agent
Sprint 48 Feature 48.3: Agent Node Instrumentation (13 SP) - Graph Query
Sprint 69 Feature 69.5: Query Rewriter v2 - Graph-Intent Extraction (8 SP)
Integrates with Sprint 4 Router and Sprint 5 DualLevelSearch.
"""

from datetime import datetime
from typing import Any

import structlog

from src.agents.base_agent import BaseAgent
from src.agents.retry import retry_on_failure
from src.components.graph_rag.section_communities import (
    SectionCommunityService,
    get_section_community_service,
)
from src.components.retrieval.query_rewriter_v2 import (
    QueryRewriterV2,
    get_query_rewriter_v2,
)
from src.core.config import settings
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

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

logger = structlog.get_logger(__name__)


def classify_search_mode(query: str) -> SearchMode:
    """Classify query to determine optimal search mode.

    Uses heuristics to determine whether to use local (entity-level),
    global (topic-level), or hybrid search based on query characteristics.

    Heuristics:
    - Local: Specific entity questions ("who", "what is", "which")
    - Global: Broad overview questions ("summarize", "overview", "themes")
    - Hybrid: Default for complex or ambiguous queries

    Sprint 68 Feature 68.5: Added community-based search detection.

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


def should_use_community_search(query: str) -> bool:
    """Determine if query should use community-based section retrieval.

    Sprint 68 Feature 68.5: Section Community Detection

    Community-based search is useful for:
    - Cross-document section queries ("show all sections about X")
    - Thematic clustering ("related sections on topic Y")
    - Navigation queries ("find similar sections")

    Args:
        query: User query string

    Returns:
        bool: True if community search is appropriate

    Examples:
        >>> should_use_community_search("Show all sections about authentication")
        True
        >>> should_use_community_search("What is RAG?")
        False
    """
    query_lower = query.lower().strip()

    # Community search keywords
    community_keywords = [
        "show all sections",
        "find sections",
        "related sections",
        "similar sections",
        "sections about",
        "all documentation on",
        "across documents",
        "cross-document",
    ]

    for keyword in community_keywords:
        if keyword in query_lower:
            logger.debug(
                "community_search_selected",
                keyword=keyword,
                query=query[:50],
            )
            return True

    return False


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
        community_service: SectionCommunityService | None = None,
        query_rewriter_v2: QueryRewriterV2 | None = None,
    ) -> None:
        """Initialize Graph Query Agent.

        Sprint 68 Feature 68.5: Added section community service.
        Sprint 69 Feature 69.5: Added query rewriter v2 for graph intent extraction.

        Args:
            name: Agent name (default: "graph_query_agent")
            dual_level_search: DualLevelSearch instance (optional, uses singleton if None)
            community_service: SectionCommunityService instance (optional, uses singleton if None)
            query_rewriter_v2: QueryRewriterV2 instance (optional, uses singleton if None)
        """
        super().__init__(name=name)
        self.dual_level_search = dual_level_search or get_dual_level_search()
        self.community_service = community_service or get_section_community_service()
        self.query_rewriter_v2 = query_rewriter_v2 or get_query_rewriter_v2()

        self.logger.info(
            "graph_query_agent_initialized",
            agent=name,
            has_query_rewriter_v2=query_rewriter_v2 is not None,
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
        import time
        phase_timings = {}  # Track timing for each phase

        # Extract query
        query = state.get("query", "")
        if not query:
            self.logger.warning("graph_query_no_query", state=state)
            return state

        # Sprint 76: Extract namespaces for multi-tenant isolation
        namespaces = state.get("namespaces")
        if not namespaces:
            namespaces = ["default", "general"]  # Default namespaces

        self.logger.info(
            "graph_query_started",
            query=query[:100],
            intent=state.get("intent", "unknown"),
            namespaces=namespaces,
        )

        # Add agent to trace
        self._add_trace(state, "processing graph query")

        try:
            # Sprint 92 Performance Optimization: Execute intent extraction in background
            # Intent extraction is informational only and doesn't block search execution
            # This saves ~500-1000ms by not waiting for LLM response
            import asyncio

            # Start intent extraction in background (non-blocking)
            graph_intent_task = asyncio.create_task(
                self.query_rewriter_v2.extract_graph_intents(query)
            )

            # Sprint 68 Feature 68.5: Check if community search should be used
            use_community_search = should_use_community_search(query)

            if use_community_search:
                # Community-based section retrieval
                phase_start = time.perf_counter()
                top_k = getattr(settings, "graph_search_top_k", 10)
                community_result = await self.community_service.retrieve_by_community(
                    query=query,
                    top_k=top_k,
                )
                phase_timings["community_search_ms"] = (time.perf_counter() - phase_start) * 1000

                # Calculate latency
                latency_ms = self._calculate_latency_ms(timing)

                # Build graph result from community retrieval
                graph_result = GraphSearchResult(
                    query=query,
                    answer=f"Found {community_result.total_sections} sections in {len(community_result.communities)} communities.",
                    entities=[],
                    relationships=[],
                    topics=[],
                    context="\n\n".join(
                        [
                            f"**{s.get('heading', 'Unknown')}** (Page {s.get('page_no', 0)})\n{s.get('content', '')[:200]}..."
                            for s in community_result.sections[:5]
                        ]
                    ),
                    mode="community",
                    metadata={
                        "communities_found": len(community_result.communities),
                        "sections_found": community_result.total_sections,
                        "retrieval_time_ms": community_result.retrieval_time_ms,
                        "search_type": "community",
                    },
                )

                self._log_success(
                    "community_search",
                    query=query[:50],
                    communities_found=len(community_result.communities),
                    sections_found=community_result.total_sections,
                    latency_ms=latency_ms,
                )
            else:
                # Standard graph search (existing logic)
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
                    phase_start = time.perf_counter()
                    entities, local_metadata = await self.dual_level_search.local_search(
                        query=query, top_k=top_k, namespaces=namespaces
                    )
                    phase_timings["local_search_ms"] = (time.perf_counter() - phase_start) * 1000
                    # Sprint 92: Include graph_hops_used in metadata
                    graph_result = GraphSearchResult(
                        query=query,
                        answer=f"Found {len(entities)} entities related to the query.",
                        entities=entities,
                        relationships=[],
                        topics=[],
                        context="",
                        mode="local",
                        metadata={
                            "entities_found": len(entities),
                            "graph_hops_used": local_metadata.get("graph_hops_used", 0),
                        },
                    )
                elif search_mode == SearchMode.GLOBAL:
                    # Topic-level search
                    phase_start = time.perf_counter()
                    topics = await self.dual_level_search.global_search(
                        query=query, top_k=min(top_k, 5), namespaces=namespaces
                    )
                    phase_timings["global_search_ms"] = (time.perf_counter() - phase_start) * 1000
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
                    phase_start = time.perf_counter()
                    graph_result = await self.dual_level_search.hybrid_search(
                        query=query, top_k=top_k, namespaces=namespaces
                    )
                    phase_timings["hybrid_search_ms"] = (time.perf_counter() - phase_start) * 1000

                # Calculate latency
                latency_ms = self._calculate_latency_ms(timing)

            # Sprint 92: Collect intent extraction result (non-blocking)
            # Try to get result if it finished, otherwise skip
            graph_intent_result = None
            try:
                graph_intent_result = await asyncio.wait_for(graph_intent_task, timeout=0.1)
                self.logger.info(
                    "graph_intents_extracted",
                    query=query[:50],
                    intents=graph_intent_result.graph_intents,
                    entities=graph_intent_result.entities_mentioned,
                    cypher_hints_count=len(graph_intent_result.cypher_hints),
                    confidence=graph_intent_result.confidence,
                    latency_ms=round(graph_intent_result.latency_ms, 2),
                )
            except asyncio.TimeoutError:
                self.logger.debug(
                    "graph_intent_extraction_still_running",
                    query=query[:50],
                    fallback="skip_intent_metadata",
                )
            except Exception as e:
                self.logger.warning(
                    "graph_intent_extraction_failed",
                    query=query[:50],
                    error=str(e),
                    fallback="skip_intent_metadata",
                )

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
                    # Sprint 69 Feature 69.5: Add graph intent metadata
                    "graph_intents": (
                        graph_intent_result.graph_intents if graph_intent_result else []
                    ),
                    "entities_mentioned": (
                        graph_intent_result.entities_mentioned if graph_intent_result else []
                    ),
                    "cypher_hints": (
                        graph_intent_result.cypher_hints if graph_intent_result else []
                    ),
                    "intent_confidence": (
                        graph_intent_result.confidence if graph_intent_result else 0.0
                    ),
                    "intent_extraction_latency_ms": (
                        round(graph_intent_result.latency_ms, 2) if graph_intent_result else 0.0
                    ),
                },
            }

            # Add entities as retrieved contexts (for compatibility with vector search)
            if entities_list:
                retrieved_contexts = []
                # Sprint 92: Extract graph_hops_used from graph_result metadata
                graph_hops_used = graph_result.metadata.get("graph_hops_used", 0)

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
                        "metadata": {
                            **entity,
                            "graph_hops_used": graph_hops_used,  # Sprint 92: Add hops count
                        },
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

            # Log success with phase timings
            self._log_success(
                "graph_query",
                query=query[:50],
                mode=search_mode.value,
                entities_found=len(entities_list),
                relationships_found=len(relationships_list),
                topics_found=len(topics_list),
                latency_ms=latency_ms,
                phase_timings=phase_timings,  # Sprint 92: Detailed phase timings
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


async def graph_query_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node function for graph query processing.

    This is the node function that gets added to the LangGraph StateGraph.
    It instantiates the GraphQueryAgent and calls process().

    Sprint 48 Feature 48.3: Emits phase events for graph query.
    Sprint 80 Feature 80.2: Graph→Vector fallback when graph returns empty results.

    Args:
        state: Current agent state

    Returns:
        Updated agent state after graph query processing with phase_event

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

    # Create phase event for graph query
    event = PhaseEvent(
        phase_type=PhaseType.GRAPH_QUERY,
        status=PhaseStatus.IN_PROGRESS,
        start_time=datetime.utcnow(),
    )

    try:
        # Instantiate agent
        agent = GraphQueryAgent()

        # Process state
        updated_state = await agent.process(state)

        # Update phase event with success
        event.status = PhaseStatus.COMPLETED
        event.end_time = datetime.utcnow()
        event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000

        # Extract metadata from graph search results
        graph_metadata = updated_state.get("metadata", {}).get("graph_search", {})
        event.metadata = {
            "entities_found": graph_metadata.get("entities_found", 0),
            "relationships_found": graph_metadata.get("relationships_found", 0),
            "topics_found": graph_metadata.get("topics_found", 0),
            "mode": graph_metadata.get("mode", "unknown"),
        }

        # Add phase event to state
        updated_state["phase_event"] = event

        # Sprint 80 Feature 80.2: Graph→Vector Fallback
        # If graph search returns empty contexts, fall back to vector search
        graph_contexts = updated_state.get("retrieved_contexts", [])
        if len(graph_contexts) == 0 and settings.graph_vector_fallback_enabled:
            logger.warning(
                "graph_empty_fallback_to_vector",
                query=state.get("query", "")[:50],
                reason="graph_returned_empty_contexts",
            )

            # Import vector search node (lazy import to avoid circular dependency)
            from src.agents.vector_search_agent import vector_search_node

            # Run vector search as fallback
            fallback_state = await vector_search_node(state.copy())

            # Merge fallback results
            fallback_contexts = fallback_state.get("retrieved_contexts", [])
            for ctx in fallback_contexts:
                ctx["search_type"] = "vector_fallback"  # Mark as fallback
            updated_state["retrieved_contexts"] = fallback_contexts

            # Update metadata to indicate fallback was used
            if "metadata" not in updated_state:
                updated_state["metadata"] = {}
            updated_state["metadata"]["graph_vector_fallback"] = {
                "triggered": True,
                "fallback_contexts_count": len(fallback_contexts),
                "reason": "graph_returned_empty_contexts",
            }

            logger.info(
                "graph_vector_fallback_complete",
                query=state.get("query", "")[:50],
                fallback_contexts_count=len(fallback_contexts),
            )

        logger.info(
            "graph_query_node_complete",
            query=state.get("query", "")[:50],
            entities_found=event.metadata["entities_found"],
            duration_ms=event.duration_ms,
            contexts_count=len(updated_state.get("retrieved_contexts", [])),
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
            "graph_query_node_failed",
            error=str(e),
            duration_ms=event.duration_ms,
        )

        # Re-raise to let error handling take over
        raise


# Export public API
__all__ = [
    "GraphQueryAgent",
    "graph_query_node",
    "classify_search_mode",
    "should_use_community_search",
    "SearchMode",
]
