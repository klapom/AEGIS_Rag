# AegisRAG Agentic Capabilities - Low-Level Technical Reference

## Overview

This document provides comprehensive low-level technical documentation of the agentic capabilities in AegisRAG. It covers the LangGraph state machine architecture, individual agent implementations, retrieval pipelines, tool frameworks, and API contracts with code references and technical specifications.

**Status:** Production (Sprint 83+)
**Last Updated:** Sprint 88
**Key Components:** LangGraph orchestration, 3-way hybrid search (Sprint 88), intent classification, graph RAG, tool execution, memory management

---

## 1. LangGraph State Machine Architecture

### 1.1 State Schema

The core state object that flows through the entire agent graph is defined in `/home/admin/projects/aegisrag/AEGIS_Rag/src/agents/state.py`:

```python
class AgentState(MessagesState):
    """State passed between LangGraph nodes.

    Inherits from MessagesState to maintain message history and integrates
    with LangChain's message-based conversation flow.
    """

    # Query and Intent
    query: str = Field(default="", description="Original user query")
    intent: str = Field(
        default="hybrid",
        description="Detected query intent (vector, graph, hybrid, direct)"
    )

    # Retrieval Results
    retrieved_contexts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved document contexts from search"
    )
    search_mode: Literal["vector", "graph", "hybrid"] = Field(
        default="hybrid",
        description="Search mode to use for retrieval"
    )

    # Graph and Memory Results
    graph_query_result: dict[str, Any] | None = Field(
        default=None,
        description="Results from graph RAG query (Sprint 5)"
    )
    memory_results: dict[str, Any] | None = Field(
        default=None,
        description="Results from memory retrieval (Sprint 7)"
    )

    # Metadata and Tracking
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for execution tracking"
    )
    citation_map: dict[int, dict[str, Any]] = Field(
        default_factory=dict,
        description="Map of citation numbers to source metadata"
    )
    answer: str = Field(
        default="",
        description="Generated answer from LLM"
    )

    # Namespace Filtering (Sprint 41)
    namespaces: list[str] | None = Field(
        default=None,
        description="Namespaces to search in (default: ['default', 'general'])"
    )

    # Phase Events and Streaming (Sprint 48+)
    phase_event: PhaseEvent | None = Field(
        default=None,
        description="Latest phase event emitted by the current node"
    )
    phase_events: list[PhaseEvent] = Field(
        default_factory=list,
        description="List of all phase events for streaming"
    )

    # Tool Execution Tracking (Sprint 70)
    tool_execution_count: int = Field(
        default=0,
        description="Number of tool executions in this conversation"
    )
```

**Key Types:**

```python
class RetrievedContext(BaseModel):
    """A single retrieved context/document."""

    id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text content")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0 to 1.0)")
    source: str = Field(default="unknown", description="Document source")
    document_id: str = Field(default="", description="Parent document ID")
    rank: int = Field(default=0, ge=0, description="Ranking position")
    search_type: Literal["vector", "bm25", "hybrid", "graph", "graph_local", "graph_global"]
    metadata: dict[str, Any] = Field(default_factory=dict)

class SearchMetadata(BaseModel):
    """Metadata about search execution."""

    latency_ms: float = Field(..., ge=0.0)
    result_count: int = Field(..., ge=0)
    search_mode: Literal["vector", "bm25", "hybrid", "graph", "graph_local", "graph_global"]
    vector_results_count: int = Field(default=0, ge=0)
    bm25_results_count: int = Field(default=0, ge=0)
    reranking_applied: bool = Field(default=False)
    error: str | None = Field(default=None)
```

**State Creation:**

```python
def create_initial_state(
    query: str,
    intent: str = "hybrid",
    namespaces: list[str] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Create initial agent state from user query."""
    return {
        "messages": [],
        "query": query,
        "intent": intent,
        "retrieved_contexts": [],
        "search_mode": intent if intent in ["vector", "graph", "hybrid"] else "hybrid",
        "namespaces": namespaces,
        "session_id": session_id,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "agent_path": [],
        },
    }

def update_state_metadata(
    state: dict[str, Any],
    agent_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update state metadata with agent execution info."""
    if "metadata" not in state:
        state["metadata"] = {}

    if "agent_path" not in state["metadata"]:
        state["metadata"]["agent_path"] = []

    # Add agent to path if not already the last entry
    if not state["metadata"]["agent_path"] or \
       state["metadata"]["agent_path"][-1] != agent_name:
        state["metadata"]["agent_path"].append(agent_name)

    # Update additional metadata
    state["metadata"].update(kwargs)

    return state
```

---

### 1.2 Node Definitions and Execution Flow

The LangGraph is defined in `/home/admin/projects/aegisrag/AEGIS_Rag/src/agents/graph.py`:

```
START
  ↓
[ROUTER NODE] - Intent classification
  ├→ User-selected intent (direct) → Skip LLM classification
  └→ Auto mode → LLM classification (RetryLogic: 3 attempts)
  ↓
[CONDITIONAL ROUTING]
  ├→ "vector" → VECTOR_SEARCH_NODE → (RRF fusion)
  ├→ "graph" → GRAPH_QUERY_NODE → (Dual-level search)
  ├→ "hybrid" → [VECTOR_SEARCH_NODE + GRAPH_QUERY_NODE] → (Parallel execution)
  └→ "memory" → MEMORY_NODE
  ↓
[LLM_ANSWER_NODE] - Answer generation with citations
  │ - Streams tokens in real-time (Sprint 52)
  │ - Inline citation markers [1], [2], etc.
  │ - Faithfulness enforcement (Sprint 80)
  │ - No-hedging mode (Sprint 81)
  ↓
[END]
```

**Key Node Functions:**

1. **Router Node** (`src/agents/router.py`):
   - Classifies query intent using LLM or respects user selection
   - Phase events: INTENT_CLASSIFICATION (IN_PROGRESS → COMPLETED/FAILED)
   - Emits: `route_decision`, `intent`, `metadata.intent_source`

2. **Vector Search Node** (`src/agents/vector_search_agent.py`):
   - Executes 4-way hybrid search (Sprint 88: BGE-M3 multi-vector)
   - Phase events: VECTOR_SEARCH, BM25_SEARCH, GRAPH_QUERY, RRF_FUSION
   - Returns: `retrieved_contexts`, `metadata.search` with detailed metrics

3. **Graph Query Node** (`src/agents/graph_query_agent.py`):
   - Executes dual-level graph search (local + global)
   - Phase events: GRAPH_QUERY (IN_PROGRESS → COMPLETED/FAILED)
   - Returns: `graph_query_result`, `metadata.graph_search`

4. **Memory Node** (`src/agents/memory_agent.py`):
   - Retrieves from 3-layer memory (Redis/Qdrant/Graphiti)
   - Phase events: MEMORY_RETRIEVAL (IN_PROGRESS → COMPLETED/FAILED)
   - Returns: `memory_results`, `metadata.memory_search`

5. **LLM Answer Node** (`src/agents/graph.py::llm_answer_node`):
   - Generates answer with inline citations
   - Streams tokens real-time to UI (Sprint 52)
   - Phase events: LLM_GENERATION (IN_PROGRESS → COMPLETED/FAILED)
   - Returns: `answer`, `citation_map`, `messages`

---

### 1.3 Edge Conditions and Routing Logic

```python
# Conditional routing based on intent
def route_to_search_mode(state: dict[str, Any]) -> str:
    """Route to appropriate search based on intent."""
    intent = state.get("intent", "hybrid")

    if intent == "vector":
        return "vector_search"
    elif intent == "graph":
        return "graph_query"
    elif intent == "hybrid":
        return "hybrid_search"  # Parallel execution
    elif intent == "memory":
        return "memory_search"
    else:
        return "llm_answer"  # Fallback to direct LLM
```

**Parallel Execution (Hybrid Mode):**

Sprint 42 introduced true hybrid mode where Vector and Graph searches execute in parallel, then results are fused:

```python
# In StateGraph construction:
graph.add_edge("router", "vector_search")
graph.add_edge("router", "graph_query")
graph.add_edge("vector_search", "answer_generator")
graph.add_edge("graph_query", "answer_generator")
graph.add_edge("answer_generator", END)
```

---

## 2. Agent Implementations

### 2.1 Base Agent Class

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/agents/base_agent.py`

All agents inherit from `BaseAgent`:

```python
class BaseAgent(ABC):
    """Abstract base class for all agents.

    All agents should inherit from this class and implement the process() method.
    Provides common functionality for logging, error handling, and state updates.
    All agents are async by design to support concurrent operations.
    """

    def __init__(self, name: str) -> None:
        """Initialize base agent.

        Args:
            name: Name of the agent (used in logging and tracing)
        """
        self.name = name
        self.logger = logger.bind(agent=name)

    @abstractmethod
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process the state and return updated state.

        This is the main method that each agent must implement.
        The method must be async to support concurrent operations.

        Args:
            state: Current agent state dictionary

        Returns:
            Updated agent state dictionary

        Raises:
            Exception: If processing fails
        """
        pass

    def _measure_latency(self) -> dict[str, Any]:
        """Start measuring execution latency."""
        import time
        return {"start_time": time.perf_counter()}

    def _calculate_latency_ms(self, timing: dict[str, Any]) -> float:
        """Calculate elapsed time in milliseconds."""
        import time
        return (time.perf_counter() - timing["start_time"]) * 1000

    def _log_success(self, context: str, **kwargs: Any) -> None:
        """Log successful operation."""
        self.logger.info(f"{context}_success", **kwargs)

    def _log_error(self, context: str, error: Exception, **kwargs: Any) -> None:
        """Log error with context."""
        self.logger.error(f"{context}_error", error=str(error), **kwargs)

    def _add_trace(self, state: dict[str, Any], action: str) -> None:
        """Add trace entry to state agent_path."""
        if "metadata" not in state:
            state["metadata"] = {}
        if "agent_path" not in state["metadata"]:
            state["metadata"]["agent_path"] = []
        state["metadata"]["agent_path"].append(f"{self.name}: {action}")
```

---

### 2.2 Coordinator Agent

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/agents/coordinator.py`

The main orchestrator that initializes state and manages the entire query flow:

```python
class CoordinatorAgent:
    """Main orchestrator for multi-agent RAG system.

    Sprint 4 Feature 4.4: Coordinator Agent with State Persistence
    Sprint 48 Feature 48.2: Streaming Method (13 SP)
    Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)
    """

    def __init__(self, use_persistence: bool = True) -> None:
        """Initialize Coordinator Agent.

        Args:
            use_persistence: Enable conversation history persistence via Redis
        """
        self.use_persistence = use_persistence
        self.graph = compile_graph()  # Compile LangGraph
        self.checkpointer = create_checkpointer() if use_persistence else None

    async def invoke(
        self,
        query: str,
        session_id: str | None = None,
        intent: str = "hybrid",
        namespaces: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Invoke the agent graph synchronously.

        Args:
            query: User query
            session_id: Session ID for conversation persistence
            intent: Query intent ("vector", "graph", "hybrid", "memory")
            namespaces: Namespaces to search in
            **kwargs: Additional configuration

        Returns:
            Final agent state with answer and metadata
        """
        # Create initial state
        state = create_initial_state(
            query=query,
            intent=intent,
            namespaces=namespaces,
            session_id=session_id,
        )

        # Invoke graph with checkpointing if enabled
        config = create_thread_config(session_id) if self.use_persistence else None

        result = await self.graph.ainvoke(
            state,
            config=config,
            timeout=90,  # REQUEST_TIMEOUT_SECONDS
        )

        return result

    async def stream(
        self,
        query: str,
        session_id: str | None = None,
        intent: str = "hybrid",
        namespaces: list[str] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream agent execution with real-time phase events and tokens.

        Sprint 48 Feature 48.2: Streaming support with phase events
        Sprint 52: Token-by-token streaming to chat window

        Yields:
            Event dictionaries with types: phase_event, token, citation_map, answer
        """
        # Create initial state
        state = create_initial_state(
            query=query,
            intent=intent,
            namespaces=namespaces,
            session_id=session_id,
        )

        config = create_thread_config(session_id) if self.use_persistence else None

        # Stream graph execution
        async for output in self.graph.astream(
            state,
            config=config,
            timeout=90,
        ):
            # Output format: {node_name: {state_updates}}
            for node_name, state_update in output.items():
                # Extract phase events if present
                if "phase_events" in state_update:
                    for event in state_update["phase_events"]:
                        yield {"type": "phase_event", "data": event}

                # Extract phase event if present
                if "phase_event" in state_update and state_update["phase_event"]:
                    yield {
                        "type": "phase_event",
                        "data": state_update["phase_event"]
                    }

            yield output
```

**Helper Functions:**

```python
def _extract_channel_samples(
    retrieved_contexts: list[dict[str, Any]],
    query: str,
    max_per_channel: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """Extract sample results from each channel for UI display.

    Groups results by source_channel and returns top samples from each.
    Sprint 52: Added query parameter for BM25 keyword extraction.

    Returns:
        Dict mapping channel names to sample lists:
        {
            "vector": [{text, score, document_id, title}, ...],
            "bm25": [{text, score, document_id, title, keywords}, ...],
            "graph_local": [{text, score, document_id, title, matched_entities}, ...],
            "graph_global": [{text, score, document_id, title, community_id}, ...],
        }
    """
    channel_samples: dict[str, list[dict[str, Any]]] = {
        "vector": [],
        "bm25": [],
        "graph_local": [],
        "graph_global": [],
    }

    # Extract BM25 keywords from query
    bm25_keywords = query.lower().split() if query else []

    for ctx in retrieved_contexts:
        source = ctx.get("source_channel") or ctx.get("search_type") or "unknown"

        # Normalize channel names
        if source in ("vector", "embedding"):
            channel = "vector"
        elif source in ("bm25", "keyword"):
            channel = "bm25"
        elif source in ("graph_local", "local"):
            channel = "graph_local"
        elif source in ("graph_global", "global"):
            channel = "graph_global"
        else:
            continue

        # Only add if under limit
        if len(channel_samples[channel]) >= max_per_channel:
            continue

        # Create sample entry
        text = ctx.get("text", "")[:200] + "..."
        sample = {
            "text": text,
            "score": ctx.get("score", 0),
            "document_id": ctx.get("document_id", ""),
            "title": ctx.get("title", ""),
        }

        # Add channel-specific metadata
        if channel == "bm25":
            sample["keywords"] = bm25_keywords
        elif channel == "graph_local":
            sample["matched_entities"] = ctx.get("matched_entities", [])
        elif channel == "graph_global":
            sample["community_id"] = ctx.get("community_id")

        channel_samples[channel].append(sample)

    return channel_samples

def _calculate_effective_weights(
    raw_weights: dict[str, float],
    vector_count: int,
    bm25_count: int,
    graph_local_count: int,
    graph_global_count: int,
) -> dict[str, float]:
    """Calculate effective weights based on actual results.

    If a channel has 0 results, its effective weight is 0.
    Remaining weight is redistributed proportionally.

    Example:
        >>> raw_weights = {"vector": 0.3, "bm25": 0.3, "local": 0.4, "global": 0.0}
        >>> _calculate_effective_weights(
        ...     raw_weights,
        ...     vector_count=10, bm25_count=0,  # No BM25 results
        ...     graph_local_count=5, graph_global_count=0
        ... )
        {'vector': 0.375, 'bm25': 0.0, 'local': 0.5, 'global': 0.0}
        # BM25's 0.3 weight is redistributed to vector and local proportionally
    """
    # Fallback for missing weights
    if not raw_weights:
        return {"vector": 0.25, "bm25": 0.25, "local": 0.25, "global_": 0.25}

    counts = {
        "vector": vector_count,
        "bm25": bm25_count,
        "local": graph_local_count,
        "global_": graph_global_count,
    }

    # Find channels with results
    channels_with_results = [ch for ch, cnt in counts.items() if cnt > 0]

    if not channels_with_results:
        # No results - return equal weights
        return {"vector": 0.25, "bm25": 0.25, "local": 0.25, "global_": 0.25}

    # Calculate total weight for channels with results
    active_weight = sum(raw_weights.get(ch, 0.0) for ch in channels_with_results)

    # Redistribute
    effective_weights = {}
    for channel, weight in raw_weights.items():
        if counts[channel] > 0:
            effective_weights[channel] = weight / active_weight
        else:
            effective_weights[channel] = 0.0

    return effective_weights
```

---

### 2.3 Vector Search Agent

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/agents/vector_search_agent.py`

Executes the 4-way hybrid search with intent-weighted RRF:

```python
class VectorSearchAgent(BaseAgent):
    """Agent for 4-way hybrid search with intent classification.

    Integrates 4-Way Hybrid Search with automatic intent classification.
    Performs retrieval and updates state with results, intent metadata, and weights.

    Sprint 88: Uses BGE-M3 multi-vector search (dense + sparse with server-side RRF).
    """

    def __init__(
        self,
        four_way_search: FourWayHybridSearch | None = None,
        top_k: int | None = None,
        use_reranking: bool | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize Vector Search Agent.

        Args:
            four_way_search: FourWayHybridSearch instance (created if None)
            top_k: Number of results to retrieve (default: settings.retrieval_top_k)
            use_reranking: Whether to apply reranking (default: settings.reranker_enabled)
            max_retries: Maximum retry attempts on failure (default: 3)
        """
        super().__init__(name="VectorSearchAgent")
        self.four_way_search = four_way_search or FourWayHybridSearch()
        self.top_k = top_k or settings.retrieval_top_k
        self.use_reranking = (
            use_reranking
            if use_reranking is not None
            else settings.reranker_enabled
        )
        self.max_retries = max_retries

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process state and perform hybrid search.

        Args:
            state: Current agent state with query

        Returns:
            Updated state with retrieved_contexts and metadata

        Raises:
            VectorSearchError: If search fails after all retries
        """
        query = state.get("query", "")
        if not query:
            self.logger.warning("Empty query received, skipping search")
            return state

        # Track agent execution
        if "metadata" not in state:
            state["metadata"] = {}
        if "agent_path" not in state["metadata"]:
            state["metadata"]["agent_path"] = []
        state["metadata"]["agent_path"].append(f"{self.name}: started")

        timing = self._measure_latency()

        try:
            # Get namespaces from state (Sprint 41)
            namespaces = state.get("namespaces")

            # Perform hybrid search with retry logic
            search_result = await self._search_with_retry(
                query,
                namespaces=namespaces
            )

            # Convert results to dict format for state
            retrieved_contexts = [
                ctx.model_dump()
                for ctx in self._convert_results(search_result["results"])
            ]

            # Calculate latency
            latency_ms = self._calculate_latency_ms(timing)

            # Create metadata dict (Sprint 42: Intent classification metadata)
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
                # Intent classification metadata (Sprint 42)
                "intent": search_result["search_metadata"]["intent"],
                "intent_confidence": search_result["search_metadata"]["intent_confidence"],
                "intent_method": search_result["search_metadata"]["intent_method"],
                "intent_latency_ms": search_result["search_metadata"]["intent_latency_ms"],
                "weights": search_result["search_metadata"]["weights"],
                # Channel samples extracted BEFORE fusion for UI display (Sprint 52)
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
        self,
        query: str,
        namespaces: list[str] | None = None
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
            # Build filters for namespace filtering (Sprint 41)
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
            return {
                "results": result["results"],
                "search_metadata": {
                    "vector_results_count": result["metadata"].vector_results_count,
                    "bm25_results_count": result["metadata"].bm25_results_count,
                    "graph_local_results_count": result["metadata"].graph_local_results_count,
                    "graph_global_results_count": result["metadata"].graph_global_results_count,
                    "reranking_applied": self.use_reranking,
                    # Intent classification metadata (Sprint 42)
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
                    # Channel samples extracted BEFORE fusion (Sprint 52)
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
            raise VectorSearchError(
                query=query,
                reason=f"4-way hybrid search failed: {e}"
            ) from e

    def _convert_results(
        self,
        results: list[dict[str, Any]]
    ) -> list[RetrievedContext]:
        """Convert HybridSearch results to RetrievedContext format.

        Handles score extraction from various fields (rerank_score, rrf_score, etc.)
        with defensive clipping to [0.0, 1.0] for Pydantic validation.

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

            # Start with metadata from result
            result_metadata = result.get("metadata", {})
            metadata = {
                "search_type": result.get("search_type", "hybrid"),
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

            # Create RetrievedContext
            try:
                context = RetrievedContext(
                    id=result.get("id", ""),
                    text=result.get("text", result.get("content", "")),
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
                )
                continue

        return contexts


async def vector_search_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node function for vector search.

    This function is called by LangGraph when the graph executes.

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
        # Execute vector search
        agent = VectorSearchAgent(
            top_k=settings.retrieval_top_k,
            use_reranking=settings.reranker_enabled,
        )
        result_state = await agent.process(state)

        # Extract metadata from search results
        search_metadata = result_state.get("metadata", {}).get("search", {})

        # Emit individual phase events for each sub-phase

        # 1. Vector Search Phase (30% of total latency)
        if search_metadata.get("vector_results_count", 0) > 0:
            vector_event = PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=search_metadata.get("latency_ms", 0) * 0.3,
                metadata={
                    "results_count": search_metadata.get("vector_results_count", 0),
                },
            )
            result_state["phase_events"].append(vector_event)

        # 2. BM25 Search Phase (30% of total latency)
        if search_metadata.get("bm25_results_count", 0) > 0:
            bm25_event = PhaseEvent(
                phase_type=PhaseType.BM25_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=search_metadata.get("latency_ms", 0) * 0.3,
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
                duration_ms=search_metadata.get("latency_ms", 0) * 0.2,
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
            duration_ms=search_metadata.get("latency_ms", 0) * 0.2,
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
```

---

### 2.4 Graph Query Agent

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/agents/graph_query_agent.py`

Executes dual-level graph search (local + global):

```python
class GraphQueryAgent(BaseAgent):
    """Agent for Knowledge Graph Retrieval.

    Handles GRAPH intent routing and executes graph-based knowledge retrieval
    using dual-level search (local entity expansion + global community context).

    Sprint 5: Feature 5.5 - Graph Query Agent
    Sprint 48 Feature 48.3: Agent Node Instrumentation
    Sprint 69 Feature 69.5: Query Rewriter v2 - Graph-Intent Extraction
    """

    def __init__(
        self,
        dual_level_search: DualLevelSearch | None = None,
        query_rewriter: QueryRewriterV2 | None = None,
        top_k: int | None = None,
        search_mode: SearchMode = SearchMode.HYBRID,
    ) -> None:
        """Initialize Graph Query Agent.

        Args:
            dual_level_search: DualLevelSearch instance
            query_rewriter: QueryRewriterV2 instance (Sprint 69)
            top_k: Number of results to retrieve
            search_mode: Search mode (LOCAL, GLOBAL, HYBRID)
        """
        super().__init__(name="GraphQueryAgent")
        self.dual_level_search = dual_level_search or get_dual_level_search()
        self.query_rewriter = query_rewriter or get_query_rewriter_v2()
        self.top_k = top_k or settings.retrieval_top_k
        self.search_mode = search_mode

    @retry_on_failure(max_attempts=3, min_wait=1.0, max_wait=10.0)
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute graph query and update state.

        Args:
            state: Current agent state

        Returns:
            Updated state with graph_query_result
        """
        query = state.get("query", "")
        if not query:
            self.logger.warning("graph_query_no_query")
            return state

        timing = self._measure_latency()

        try:
            # Sprint 69: Rewrite query for graph intent extraction
            rewritten_query = await self.query_rewriter.rewrite_for_graph(query)

            # Classify search mode based on query
            search_mode = classify_search_mode(rewritten_query)

            # Execute dual-level search
            results = await self.dual_level_search.search(
                query=rewritten_query,
                search_mode=search_mode,
                top_k=self.top_k,
            )

            latency_ms = self._calculate_latency_ms(timing)

            # Convert results to retrieved_contexts format
            retrieved_contexts = []
            for i, result in enumerate(results):
                context = {
                    "id": result.get("id", f"graph_{i}"),
                    "text": result.get("text", ""),
                    "score": result.get("score", 0.0),
                    "source": f"graph_{search_mode.value}",
                    "document_id": result.get("document_id", ""),
                    "rank": i,
                    "search_type": search_mode.value,
                    "metadata": {
                        "search_mode": search_mode.value,
                        **result.get("metadata", {}),
                    },
                }
                retrieved_contexts.append(context)

            # Update state
            state["graph_query_result"] = {
                "results": results,
                "search_mode": search_mode.value,
                "total_results": len(results),
            }

            if "retrieved_contexts" not in state:
                state["retrieved_contexts"] = []
            state["retrieved_contexts"].extend(retrieved_contexts)

            # Update metadata
            if "metadata" not in state:
                state["metadata"] = {}

            state["metadata"]["graph_search"] = {
                "latency_ms": latency_ms,
                "result_count": len(results),
                "search_mode": search_mode.value,
            }

            self._log_success(
                "graph_query",
                query=query[:50],
                search_mode=search_mode.value,
                result_count=len(results),
                latency_ms=latency_ms,
            )

            return state

        except Exception as e:
            latency_ms = self._calculate_latency_ms(timing)
            self._log_error("graph_query", error=e, query=query[:50], latency_ms=latency_ms)

            # Update state with error
            if "metadata" not in state:
                state["metadata"] = {}

            state["metadata"]["graph_search"] = {
                "latency_ms": latency_ms,
                "result_count": 0,
                "error": str(e),
            }

            return await self.handle_error(state, e, "graph_query_processing")


def classify_search_mode(query: str) -> SearchMode:
    """Classify query to determine optimal graph search mode.

    Args:
        query: User query string

    Returns:
        SearchMode enum (LOCAL, GLOBAL, or HYBRID)

    Examples:
        >>> classify_search_mode("Who is John Smith?")
        SearchMode.LOCAL
        >>> classify_search_mode("Summarize the main themes")
        SearchMode.GLOBAL
    """
    query_lower = query.lower().strip()

    # Local search keywords (specific entity queries)
    local_keywords = [
        "who is", "who are", "what is", "what are", "which",
        "where is", "when did", "define", "explain the entity", "tell me about",
    ]

    # Global search keywords (broad/overview queries)
    global_keywords = [
        "summarize", "summary", "overview", "main themes", "key topics",
        "high-level", "big picture", "trends", "patterns",
    ]

    # Check for local keywords
    for keyword in local_keywords:
        if keyword in query_lower:
            return SearchMode.LOCAL

    # Check for global keywords
    for keyword in global_keywords:
        if keyword in query_lower:
            return SearchMode.GLOBAL

    # Default to HYBRID
    return SearchMode.HYBRID


async def graph_query_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node function for graph query.

    Sprint 48 Feature 48.3: Emits phase events for graph query.

    Args:
        state: Current agent state

    Returns:
        Updated state with graph_query_result and phase_event
    """
    event = PhaseEvent(
        phase_type=PhaseType.GRAPH_QUERY,
        status=PhaseStatus.IN_PROGRESS,
        start_time=datetime.utcnow(),
    )

    try:
        agent = GraphQueryAgent()
        updated_state = await agent.process(state)

        # Update phase event
        event.status = PhaseStatus.COMPLETED
        event.end_time = datetime.utcnow()
        event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000

        # Extract metadata
        graph_metadata = updated_state.get("metadata", {}).get("graph_search", {})
        event.metadata = {
            "result_count": graph_metadata.get("result_count", 0),
            "search_mode": graph_metadata.get("search_mode", "hybrid"),
        }

        updated_state["phase_event"] = event

        logger.info(
            "graph_query_node_complete",
            result_count=event.metadata["result_count"],
            duration_ms=event.duration_ms,
        )

        return updated_state

    except Exception as e:
        # Mark phase event as failed
        event.status = PhaseStatus.FAILED
        event.error = str(e)
        event.end_time = datetime.utcnow()
        event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000

        state["phase_event"] = event

        logger.error("graph_query_node_failed", error=str(e))

        raise
```

---

### 2.5 Memory Agent

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/agents/memory_agent.py`

Retrieves from 3-layer temporal memory (Redis, Qdrant, Graphiti):

```python
class MemoryAgent(BaseAgent):
    """Agent for episodic and semantic memory retrieval.

    Processes MEMORY intent queries by:
    1. Routing query to appropriate memory layer(s)
    2. Executing memory search via MemoryRouter
    3. Updating AgentState with memory results
    4. Tracking execution metadata

    Sprint 7: Feature 7.4 - Memory Agent (LangGraph Integration)
    Sprint 48 Feature 48.3: Agent Node Instrumentation
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

    @retry_on_failure(max_attempts=3, min_wait=1.0, max_wait=10.0)
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process memory query and update state.

        Args:
            state: Current agent state (AgentState dict)

        Returns:
            Updated agent state with memory results
        """
        timing = self._measure_latency()

        query = state.get("query", "")
        if not query:
            self.logger.warning("memory_query_no_query")
            return state

        self.logger.info(
            "memory_query_started",
            query=query[:100],
            intent=state.get("intent", "unknown"),
        )

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

            latency_ms = self._calculate_latency_ms(timing)

            # Convert results to retrieved_contexts format
            retrieved_contexts = []
            layers_used = []

            for layer, layer_results in results.items():
                layers_used.append(layer)

                for i, result in enumerate(layer_results):
                    # Handle different result formats
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
                    layer: len(layer_results)
                    for layer, layer_results in results.items()
                },
                "latency_ms": latency_ms,
            }

            state["metadata"]["memory_layers_used"] = layers_used

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
            latency_ms = self._calculate_latency_ms(timing)

            self._log_error(
                "memory_query",
                error=e,
                query=query[:50],
                latency_ms=latency_ms,
            )

            # Update state with error
            if "metadata" not in state:
                state["metadata"] = {}

            state["metadata"]["memory_search"] = {
                "layers_used": [],
                "total_results": 0,
                "results_per_layer": {},
                "latency_ms": latency_ms,
                "error": str(e),
            }

            return await self.handle_error(state, e, "memory_query_processing")


async def memory_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node function for memory query processing.

    Sprint 48 Feature 48.3: Emits phase events for memory retrieval.

    Args:
        state: Current agent state

    Returns:
        Updated agent state after memory query processing with phase_event
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

        logger.error("memory_node_failed", error=str(e), duration_ms=event.duration_ms)

        raise
```

---

### 2.6 Action Agent (Tool Execution)

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/agents/action/secure_action_agent.py`

Executes tools in sandboxed environment with security and RL-based tool selection:

```python
@dataclass
class ActionConfig:
    """Configuration for SecureActionAgent.

    Attributes:
        sandbox_timeout: Timeout for sandbox commands in seconds
        max_retries: Maximum number of retries for failed commands
        workspace_path: Path to workspace directory for temporary files
        retry_delay: Delay between retries in seconds
        repo_path: Path to repository (mounted read-only in sandbox)
        enable_reward_loop: Enable RL-based tool selection (Sprint 68)
        epsilon: Exploration rate for ε-greedy policy (Sprint 68)
        alpha: Learning rate for Q-learning updates (Sprint 68)
        expected_duration_ms: Expected command duration for efficiency reward (Sprint 68)
    """

    sandbox_timeout: int = 30
    max_retries: int = 3
    workspace_path: str = "/tmp/aegis-workspace"
    retry_delay: float = 1.0
    repo_path: str = "/home/admin/projects/aegisrag/AEGIS_Rag"
    enable_reward_loop: bool = True
    epsilon: float = 0.1
    alpha: float = 0.1
    expected_duration_ms: float = 5000.0


class SecureActionAgent:
    """Action agent with secure sandboxed code execution via deepagents.

    Features:
    - Sandbox isolation (filesystem + network)
    - Timeout enforcement (configurable, default: 30s)
    - Retry logic for transient failures
    - Resource cleanup on shutdown
    - LangChain-compatible interface
    - RL-based tool selection with reward feedback (Sprint 68)

    Security features:
    - Bubblewrap sandbox isolation
    - Timeout enforcement
    - Output truncation (32KB max)
    - Resource cleanup on shutdown

    Reward Loop (Sprint 68):
    - Multi-component reward calculation
    - ε-greedy tool selection policy
    - Q-learning value updates
    - Redis persistence for learned policies

    Example:
        >>> config = ActionConfig(sandbox_timeout=30)
        >>> agent = SecureActionAgent(config=config)
        >>> result = await agent.execute_action("ls -la /repo")
        >>> print(result["output"])
        >>> await agent.cleanup()
    """

    def __init__(
        self,
        config: ActionConfig | None = None,
        sandbox_backend: BubblewrapSandboxBackend | None = None,
        policy: ToolSelectionPolicy | None = None,
        reward_calculator: ToolRewardCalculator | None = None,
    ) -> None:
        """Initialize secure action agent.

        Args:
            config: ActionConfig with sandbox settings
            sandbox_backend: Bubblewrap sandbox backend (created if None)
            policy: ToolSelectionPolicy for RL-based selection (created if None)
            reward_calculator: ToolRewardCalculator for reward computation (created if None)
        """
        self.config = config or ActionConfig()
        self.sandbox = sandbox_backend or BubblewrapSandboxBackend(config=self.config)
        self.policy = policy or ToolSelectionPolicy(epsilon=self.config.epsilon)
        self.reward_calculator = (
            reward_calculator
            or ToolRewardCalculator(expected_duration_ms=self.config.expected_duration_ms)
        )

        logger.info(
            "SecureActionAgent initialized",
            timeout=self.config.sandbox_timeout,
            enable_reward_loop=self.config.enable_reward_loop,
        )

    async def execute_action(
        self,
        command: str,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute command in secure sandbox with RL-based selection.

        Args:
            command: Command to execute
            timeout: Override default timeout (seconds)
            env: Environment variables to set

        Returns:
            Dict with keys: output, return_code, duration_ms, selected_tool, reward

        Raises:
            TimeoutError: If execution exceeds timeout
            ExecutionError: If sandbox execution fails
        """
        timeout_sec = timeout or self.config.sandbox_timeout

        # Sprint 68: Use RL-based policy for tool selection
        selected_tool = self.policy.select_tool(command)

        logger.info(
            "action_executing",
            command=command[:100],
            timeout=timeout_sec,
            selected_tool=selected_tool,
        )

        try:
            import time
            start_time = time.perf_counter()

            # Execute command in sandbox
            result = await self.sandbox.execute(
                command=command,
                timeout=timeout_sec,
                env=env,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            # Sprint 68: Calculate reward for this action
            if self.config.enable_reward_loop:
                reward = self.reward_calculator.calculate_reward(
                    command=command,
                    return_code=result["return_code"],
                    duration_ms=duration_ms,
                    output_length=len(result.get("output", "")),
                )

                # Update policy with reward (Q-learning)
                await self.policy.update_with_reward(
                    tool=selected_tool,
                    reward=reward,
                    alpha=self.config.alpha,
                )
            else:
                reward = 0.0

            logger.info(
                "action_completed",
                command=command[:100],
                return_code=result["return_code"],
                duration_ms=duration_ms,
                reward=reward,
            )

            return {
                "output": result.get("output", ""),
                "return_code": result["return_code"],
                "duration_ms": duration_ms,
                "selected_tool": selected_tool,
                "reward": reward,
            }

        except Exception as e:
            logger.error(
                "action_failed",
                command=command[:100],
                error=str(e),
            )

            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.sandbox.cleanup()
```

---

## 3. Retrieval Pipeline

### 3.1 Intent Classification (C-LARA SetFit)

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/components/retrieval/intent_classifier.py`

```python
class Intent(str, Enum):
    """Query intent types for 4-Way Hybrid RRF."""

    FACTUAL = "factual"        # Specific fact lookup
    KEYWORD = "keyword"        # Keyword search
    EXPLORATORY = "exploratory"  # Broad exploration
    SUMMARY = "summary"        # High-level overview


class CLARAIntent(str, Enum):
    """C-LARA intent types from SetFit training (Sprint 81).

    Amazon Science C-LARA Framework for context-aware LLM-assisted RAG.
    5 classes for fine-grained query routing:
    - factual → high local graph (entity facts)
    - procedural → high vector + global (how-to guides)
    - comparison → balanced (compare options)
    - recommendation → balanced (suggestions)
    - navigation → high BM25 + local (find documents)
    """

    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    COMPARISON = "comparison"
    RECOMMENDATION = "recommendation"
    NAVIGATION = "navigation"


@dataclass(frozen=True)
class IntentWeights:
    """RRF weights for each retrieval channel based on intent.

    The weights determine how much each retrieval channel contributes
    to the final RRF score:
        score(chunk) = w_vec * 1/(k+r_vec) + w_bm25 * 1/(k+r_bm25)
                     + w_local * 1/(k+r_local) + w_global * 1/(k+r_global)

    where k=60 (RRF constant) and r_X is the rank from channel X.

    Attributes:
        vector: Weight for Qdrant vector search (semantic similarity)
        bm25: Weight for BM25 keyword search
        local: Weight for Graph Local (Entity → Chunk expansion)
        global_: Weight for Graph Global (Community → Entity → Chunk expansion)
    """

    vector: float
    bm25: float
    local: float
    global_: float

    def __post_init__(self) -> None:
        """Validate that weights sum to 1.0."""
        total = self.vector + self.bm25 + self.local + self.global_
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


# Intent → Weight Mappings (Legacy 4-class)
INTENT_WEIGHT_PROFILES: dict[Intent, IntentWeights] = {
    Intent.FACTUAL: IntentWeights(vector=0.3, bm25=0.3, local=0.4, global_=0.0),
    Intent.KEYWORD: IntentWeights(vector=0.1, bm25=0.6, local=0.3, global_=0.0),
    Intent.EXPLORATORY: IntentWeights(vector=0.2, bm25=0.1, local=0.2, global_=0.5),
    Intent.SUMMARY: IntentWeights(vector=0.1, bm25=0.0, local=0.1, global_=0.8),
}

# Sprint 81: C-LARA 5-class intent → Weight Mappings (from SetFit training)
CLARA_INTENT_WEIGHT_PROFILES: dict[CLARAIntent, IntentWeights] = {
    # Factual: Specific facts → high local graph (entity lookup)
    CLARAIntent.FACTUAL: IntentWeights(vector=0.3, bm25=0.3, local=0.4, global_=0.0),
    # Procedural: How-to queries → high vector (semantic) + global (context)
    CLARAIntent.PROCEDURAL: IntentWeights(vector=0.4, bm25=0.1, local=0.2, global_=0.3),
    # Comparison: Compare options → balanced vector + BM25
    CLARAIntent.COMPARISON: IntentWeights(vector=0.35, bm25=0.25, local=0.2, global_=0.2),
    # Recommendation: Suggestions → balanced with slight global preference
    CLARAIntent.RECOMMENDATION: IntentWeights(vector=0.3, bm25=0.2, local=0.2, global_=0.3),
    # Navigation: Find specific docs → high BM25 + local
    CLARAIntent.NAVIGATION: IntentWeights(vector=0.2, bm25=0.5, local=0.3, global_=0.0),
}


class IntentClassifier:
    """Intent classifier supporting 4 methods (fastest to most accurate).

    Sprint 42: Intent-Weighted RRF (original 4-class)
    Sprint 67: C-LARA SetFit Integration (5-class, 85-92% accuracy, 20-50ms)
    Sprint 52: Zero-Shot Embedding Classification (60% accuracy, 20-50ms)
    """

    @staticmethod
    async def classify_intent(
        query: str,
        method: str = "setfit",  # Sprint 67: SetFit is now default
    ) -> IntentClassificationResult:
        """Classify query intent using specified method.

        Args:
            query: User query string
            method: Classification method
                - "setfit": C-LARA SetFit model (20-50ms, 85-92%)
                - "embedding": Zero-shot BGE-M3 (20-50ms, 60%)
                - "rule_based": Fast regex (0ms, medium)
                - "llm": LLM-based (2-10s, highest)

        Returns:
            IntentClassificationResult with intent and confidence

        Raises:
            ValueError: If method not supported
        """
        if method == "setfit":
            return await _classify_setfit(query)
        elif method == "embedding":
            return await _classify_embedding(query)
        elif method == "rule_based":
            return _classify_rule_based(query)
        elif method == "llm":
            return await _classify_llm(query)
        else:
            raise ValueError(f"Unknown classification method: {method}")


@dataclass
class IntentClassificationResult:
    """Result of intent classification.

    Attributes:
        intent: Classified intent (FACTUAL, KEYWORD, EXPLORATORY, SUMMARY, or C-LARA variant)
        confidence: Confidence score (0.0-1.0)
        method: Classification method used (setfit, embedding, rule_based, llm)
        latency_ms: Classification latency in milliseconds
        weights: RRF weights for this intent
    """

    intent: str
    confidence: float
    method: str
    latency_ms: float
    weights: dict[str, float]


async def _classify_setfit(query: str) -> IntentClassificationResult:
    """Classify using C-LARA SetFit model (Sprint 81).

    SetFit (Sentence Transformers Fine-tuning) provides:
    - 85-92% accuracy on 5-class C-LARA intents
    - Fast inference (~20-50ms)
    - Better performance than zero-shot methods

    Model: models/c_lara_setfit_20250101
    Training: 42 edge case queries + 4 LLM teachers (Nemotron3, GPT-OSS, Qwen3, Alibaba)
    """
    import time
    start = time.perf_counter()

    try:
        # Load SetFit model (cached)
        from setfit import SetFitModel
        model = SetFitModel.from_pretrained("models/c_lara_setfit_20250101")

        # Classify (returns probabilities for all 5 classes)
        predictions = model.predict(query, as_numpy=True)

        # Get top prediction
        class_names = ["factual", "procedural", "comparison", "recommendation", "navigation"]
        intent_idx = predictions.argmax()
        intent = class_names[intent_idx]
        confidence = float(predictions[intent_idx])

        latency_ms = (time.perf_counter() - start) * 1000

        # Get RRF weights for this intent
        clara_intent = CLARAIntent(intent)
        weights_obj = CLARA_INTENT_WEIGHT_PROFILES[clara_intent]
        weights = {
            "vector": weights_obj.vector,
            "bm25": weights_obj.bm25,
            "local": weights_obj.local,
            "global": weights_obj.global_,
        }

        return IntentClassificationResult(
            intent=intent,
            confidence=confidence,
            method="setfit",
            latency_ms=latency_ms,
            weights=weights,
        )

    except Exception as e:
        logger.error(f"SetFit classification failed: {e}, falling back to embedding")
        return await _classify_embedding(query)


async def _classify_embedding(query: str) -> IntentClassificationResult:
    """Classify using Zero-Shot Embedding Classification.

    Sprint 52: Uses BGE-M3 embeddings to compare query with intent descriptions.
    Approach:
    1. Embed query using BGE-M3
    2. Embed intent descriptions
    3. Compute cosine similarity
    4. Return highest match

    Accuracy: ~60% (lower than LLM but fast)
    Latency: 20-50ms
    """
    import time
    start = time.perf_counter()

    try:
        from src.components.vector_search.embeddings import get_embeddings

        embeddings = get_embeddings()

        # Embed query
        query_embedding = await embeddings.embed_text(query)

        # Embed intent descriptions
        descriptions = {
            Intent.FACTUAL: INTENT_DESCRIPTIONS[Intent.FACTUAL],
            Intent.KEYWORD: INTENT_DESCRIPTIONS[Intent.KEYWORD],
            Intent.EXPLORATORY: INTENT_DESCRIPTIONS[Intent.EXPLORATORY],
            Intent.SUMMARY: INTENT_DESCRIPTIONS[Intent.SUMMARY],
        }

        best_intent = None
        best_score = -1.0

        for intent, description in descriptions.items():
            desc_embedding = await embeddings.embed_text(description)

            # Compute cosine similarity
            similarity = cosine_similarity(query_embedding, desc_embedding)

            if similarity > best_score:
                best_score = similarity
                best_intent = intent

        latency_ms = (time.perf_counter() - start) * 1000

        # Get RRF weights
        weights_obj = INTENT_WEIGHT_PROFILES[best_intent]
        weights = {
            "vector": weights_obj.vector,
            "bm25": weights_obj.bm25,
            "local": weights_obj.local,
            "global": weights_obj.global_,
        }

        return IntentClassificationResult(
            intent=best_intent.value,
            confidence=best_score,
            method="embedding",
            latency_ms=latency_ms,
            weights=weights,
        )

    except Exception as e:
        logger.error(f"Embedding classification failed: {e}")
        return _classify_rule_based(query)


def _classify_rule_based(query: str) -> IntentClassificationResult:
    """Fast rule-based classification using regex patterns.

    Latency: ~0ms
    Accuracy: ~50-60%
    """
    import time
    start = time.perf_counter()

    query_lower = query.lower()

    # Summary patterns
    summary_patterns = [
        r"\bsummarize\b", r"\bsummary\b", r"\boverview\b",
        r"\bmain themes\b", r"\bkey (topics|points|ideas)\b",
    ]

    # Keyword patterns
    keyword_patterns = [
        r"\berror\s+\d+\b", r"\bversion\s+[\d.]+\b",
        r"\b[A-Z]{2,}\b", r"\bAPI\b", r"\b\w+\.py\b",
    ]

    # Exploratory patterns
    exploratory_patterns = [
        r"\bhow (does|can|do)\b", r"\bwhy\b", r"\bexplain\b",
        r"\brelationship\b", r"\bconnect\b", r"\bcompare\b",
    ]

    # Check patterns
    for pattern in summary_patterns:
        if re.search(pattern, query_lower):
            weights_obj = INTENT_WEIGHT_PROFILES[Intent.SUMMARY]
            return IntentClassificationResult(
                intent="summary",
                confidence=0.7,
                method="rule_based",
                latency_ms=(time.perf_counter() - start) * 1000,
                weights={
                    "vector": weights_obj.vector,
                    "bm25": weights_obj.bm25,
                    "local": weights_obj.local,
                    "global": weights_obj.global_,
                },
            )

    for pattern in keyword_patterns:
        if re.search(pattern, query_lower):
            weights_obj = INTENT_WEIGHT_PROFILES[Intent.KEYWORD]
            return IntentClassificationResult(
                intent="keyword",
                confidence=0.6,
                method="rule_based",
                latency_ms=(time.perf_counter() - start) * 1000,
                weights={
                    "vector": weights_obj.vector,
                    "bm25": weights_obj.bm25,
                    "local": weights_obj.local,
                    "global": weights_obj.global_,
                },
            )

    for pattern in exploratory_patterns:
        if re.search(pattern, query_lower):
            weights_obj = INTENT_WEIGHT_PROFILES[Intent.EXPLORATORY]
            return IntentClassificationResult(
                intent="exploratory",
                confidence=0.6,
                method="rule_based",
                latency_ms=(time.perf_counter() - start) * 1000,
                weights={
                    "vector": weights_obj.vector,
                    "bm25": weights_obj.bm25,
                    "local": weights_obj.local,
                    "global": weights_obj.global_,
                },
            )

    # Default to FACTUAL
    weights_obj = INTENT_WEIGHT_PROFILES[Intent.FACTUAL]
    return IntentClassificationResult(
        intent="factual",
        confidence=0.5,
        method="rule_based",
        latency_ms=(time.perf_counter() - start) * 1000,
        weights={
            "vector": weights_obj.vector,
            "bm25": weights_obj.bm25,
            "local": weights_obj.local,
            "global": weights_obj.global_,
        },
    )
```

---

### 3.2 Four-Way Hybrid Search with Intent-Weighted RRF

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/components/retrieval/four_way_hybrid_search.py`

```python
@dataclass
class FourWaySearchMetadata:
    """Metadata from 4-Way Hybrid Search execution.

    Attributes:
        vector_results_count: Results from Qdrant dense search
        bm25_results_count: Results from Qdrant sparse vectors (Sprint 88)
        graph_local_results_count: Entity fact results
        graph_global_results_count: Community context results
        intent: Detected query intent
        intent_confidence: Confidence of intent classification
        intent_method: Classification method used
        intent_latency_ms: Time spent on intent classification
        weights: RRF weights for each channel
        total_latency_ms: Total search execution time
        channels_executed: List of channels that were executed
        namespaces_searched: Namespaces included in search
        channel_samples: Sample results from each channel (Sprint 52)
    """

    vector_results_count: int
    bm25_results_count: int
    graph_local_results_count: int
    graph_global_results_count: int
    intent: str
    intent_confidence: float
    intent_method: str
    intent_latency_ms: float
    weights: dict[str, float]
    total_latency_ms: float
    channels_executed: list[str]
    namespaces_searched: list[str]
    channel_samples: dict[str, list[dict[str, Any]]] | None = None


class FourWayHybridSearch:
    """4-Way Hybrid Retrieval with Intent-Weighted RRF.

    Sprint 88: Updated to use BGE-M3 multi-vector search (dense + sparse).

    This engine combines 4 retrieval channels:
    1. Multi-Vector Search (Qdrant) - Dense (semantic) + Sparse (lexical) with server-side RRF
       - Replaces separate Vector + BM25 channels (Sprint 88)
       - Uses BGE-M3 sparse vectors instead of pickle-based BM25
       - Server-side fusion eliminates desync issues
    2. Graph Local - Entity → Chunk expansion (MENTIONED_IN relationships)
    3. Graph Global - Community → Entity → Chunk expansion

    The weights for each channel are dynamically determined by
    classifying the query intent (factual, keyword, exploratory, summary,
    or C-LARA 5-class variants).

    Academic References:
    - GraphRAG (Edge et al., 2024) - arXiv:2404.16130
    - LightRAG (Guo et al., EMNLP 2025) - arXiv:2410.05779
    - BGE-M3 (Chen et al., 2024) - arXiv:2402.03216
    """

    def __init__(
        self,
        hybrid_search: HybridSearch | None = None,
        multi_vector_search: MultiVectorHybridSearch | None = None,
        neo4j_client: Neo4jClient | None = None,
        rrf_k: int = 60,
    ):
        """Initialize 4-Way Hybrid Search.

        Args:
            hybrid_search: Existing HybridSearch instance (legacy fallback)
            multi_vector_search: MultiVectorHybridSearch instance (Sprint 88)
            neo4j_client: Neo4j client for graph queries
            rrf_k: RRF constant (default: 60)
        """
        self.hybrid_search = hybrid_search or HybridSearch()
        self.multi_vector_search = multi_vector_search or MultiVectorHybridSearch()
        self.neo4j_client = neo4j_client or Neo4jClient()
        self.rrf_k = rrf_k

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: MetadataFilters | None = None,
        use_reranking: bool = False,
        intent_override: Intent | None = None,
        allowed_namespaces: list[str] | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Execute 4-Way Hybrid Search with Intent-Weighted RRF.

        Sprint 68 Feature 68.4: Added query caching for latency optimization.

        Args:
            query: User query string
            top_k: Number of final results to return
            filters: Metadata filters (applied to vector search only)
            use_reranking: Whether to apply cross-encoder reranking
            intent_override: Override intent classification (for testing)
            allowed_namespaces: Namespaces to include in search
            use_cache: Use query result caching (Sprint 68)

        Returns:
            Dict with structure:
            {
                "query": "...",
                "results": [...],  # Final RRF-fused results
                "intent": "factual",  # Detected intent
                "weights": {
                    "vector": 0.3,
                    "bm25": 0.3,
                    "local": 0.4,
                    "global": 0.0,
                },
                "metadata": FourWaySearchMetadata(...)
            }
        """
        import time
        total_start = time.perf_counter()

        logger.info(
            "four_way_hybrid_search_started",
            query=query[:100],
            top_k=top_k,
            intent_override=intent_override,
        )

        # Step 1: Classify intent (if not overridden)
        intent_start = time.perf_counter()
        if intent_override:
            intent = intent_override
            intent_method = "override"
            intent_confidence = 1.0
        else:
            result = await classify_intent(query)
            intent = result.intent
            intent_method = result.method
            intent_confidence = result.confidence

        intent_latency_ms = (time.perf_counter() - intent_start) * 1000

        # Get RRF weights for this intent
        try:
            # Try C-LARA weights first (if intent matches)
            clara_intent = CLARAIntent(intent)
            weights_obj = CLARA_INTENT_WEIGHT_PROFILES[clara_intent]
        except ValueError:
            # Fall back to legacy weights
            legacy_intent = Intent(intent)
            weights_obj = INTENT_WEIGHT_PROFILES[legacy_intent]

        weights = {
            "vector": weights_obj.vector,
            "bm25": weights_obj.bm25,
            "local": weights_obj.local,
            "global": weights_obj.global_,
        }

        logger.info(
            "intent_classified",
            intent=intent,
            confidence=intent_confidence,
            method=intent_method,
            latency_ms=intent_latency_ms,
            weights=weights,
        )

        # Step 2: Execute parallel searches
        vector_results = []
        bm25_results = []
        graph_local_results = []
        graph_global_results = []

        try:
            # 2a. Multi-Vector Search (Qdrant) - Dense + Sparse (Sprint 88)
            multi_vector_start = time.perf_counter()

            multi_vector_result = await self.multi_vector_search.search(
                query=query,
                top_k=top_k,
                filters=filters,
                namespace_filter=allowed_namespaces,
            )

            # Extract results from multi-vector search
            # Sprint 88: Result includes both dense and sparse hits with server-side RRF
            vector_results = multi_vector_result.get("dense_results", [])
            bm25_results = multi_vector_result.get("sparse_results", [])

            multi_vector_latency_ms = (time.perf_counter() - multi_vector_start) * 1000

            logger.info(
                "multi_vector_search_completed",
                vector_results=len(vector_results),
                sparse_results=len(bm25_results),
                latency_ms=multi_vector_latency_ms,
            )

            # 2b. Graph Local Search (parallel to vector search)
            if weights["local"] > 0:
                graph_local_start = time.perf_counter()

                graph_local_results = await self.neo4j_client.local_entity_search(
                    query=query,
                    top_k=top_k,
                    namespace_filter=allowed_namespaces,
                )

                graph_local_latency_ms = (time.perf_counter() - graph_local_start) * 1000

                logger.info(
                    "graph_local_search_completed",
                    results=len(graph_local_results),
                    latency_ms=graph_local_latency_ms,
                )

            # 2c. Graph Global Search (parallel to vector search)
            if weights["global"] > 0:
                graph_global_start = time.perf_counter()

                graph_global_results = await self.neo4j_client.global_community_search(
                    query=query,
                    top_k=top_k,
                    namespace_filter=allowed_namespaces,
                )

                graph_global_latency_ms = (time.perf_counter() - graph_global_start) * 1000

                logger.info(
                    "graph_global_search_completed",
                    results=len(graph_global_results),
                    latency_ms=graph_global_latency_ms,
                )

        except Exception as e:
            logger.error("Search execution failed", error=str(e), exc_info=True)
            raise

        # Step 3: Extract channel samples BEFORE fusion (Sprint 52)
        channel_samples = {}
        if vector_results:
            channel_samples["vector"] = [
                {
                    "text": r.get("text", "")[:200],
                    "score": r.get("score", 0),
                    "document_id": r.get("document_id", ""),
                }
                for r in vector_results[:3]
            ]
        if bm25_results:
            channel_samples["bm25"] = [
                {
                    "text": r.get("text", "")[:200],
                    "score": r.get("score", 0),
                    "document_id": r.get("document_id", ""),
                }
                for r in bm25_results[:3]
            ]
        if graph_local_results:
            channel_samples["graph_local"] = [
                {
                    "text": r.get("text", "")[:200],
                    "score": r.get("score", 0),
                    "document_id": r.get("document_id", ""),
                }
                for r in graph_local_results[:3]
            ]
        if graph_global_results:
            channel_samples["graph_global"] = [
                {
                    "text": r.get("text", "")[:200],
                    "score": r.get("score", 0),
                    "document_id": r.get("document_id", ""),
                }
                for r in graph_global_results[:3]
            ]

        # Step 4: Apply Weighted RRF Fusion
        rrf_start = time.perf_counter()

        # Normalize scores to [0, 1] for fair comparison
        vector_results = self._normalize_scores(vector_results)
        bm25_results = self._normalize_scores(bm25_results)
        graph_local_results = self._normalize_scores(graph_local_results)
        graph_global_results = self._normalize_scores(graph_global_results)

        # Apply intent-weighted RRF
        fused_results = weighted_reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            graph_local_results=graph_local_results,
            graph_global_results=graph_global_results,
            weights={
                "vector": weights["vector"],
                "bm25": weights["bm25"],
                "local": weights["local"],
                "global": weights["global"],
            },
            rrf_k=self.rrf_k,
            top_k=top_k,
        )

        rrf_latency_ms = (time.perf_counter() - rrf_start) * 1000

        logger.info(
            "rrf_fusion_completed",
            fused_results=len(fused_results),
            latency_ms=rrf_latency_ms,
        )

        # Step 5: Apply reranking if enabled
        if use_reranking:
            rerank_start = time.perf_counter()

            from src.components.retrieval.reranker import get_reranker
            reranker = get_reranker()

            reranked_results = await reranker.rerank(
                query=query,
                contexts=fused_results,
                top_k=top_k,
            )

            rerank_latency_ms = (time.perf_counter() - rerank_start) * 1000

            logger.info(
                "reranking_completed",
                latency_ms=rerank_latency_ms,
            )
        else:
            reranked_results = fused_results

        # Step 6: Compile final response
        total_latency_ms = (time.perf_counter() - total_start) * 1000

        channels_executed = []
        if vector_results:
            channels_executed.append("vector")
        if bm25_results:
            channels_executed.append("bm25")
        if graph_local_results:
            channels_executed.append("graph_local")
        if graph_global_results:
            channels_executed.append("graph_global")

        metadata = FourWaySearchMetadata(
            vector_results_count=len(vector_results),
            bm25_results_count=len(bm25_results),
            graph_local_results_count=len(graph_local_results),
            graph_global_results_count=len(graph_global_results),
            intent=intent,
            intent_confidence=intent_confidence,
            intent_method=intent_method,
            intent_latency_ms=intent_latency_ms,
            weights=weights,
            total_latency_ms=total_latency_ms,
            channels_executed=channels_executed,
            namespaces_searched=allowed_namespaces or ["default"],
            channel_samples=channel_samples,
        )

        logger.info(
            "four_way_hybrid_search_completed",
            query=query[:100],
            results=len(reranked_results),
            intent=intent,
            channels=channels_executed,
            total_latency_ms=total_latency_ms,
        )

        return {
            "query": query,
            "results": reranked_results,
            "intent": intent,
            "weights": weights,
            "metadata": metadata,
        }

    def _normalize_scores(
        self,
        results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Normalize scores to [0, 1] range.

        Args:
            results: List of result dicts

        Returns:
            Results with normalized scores
        """
        if not results:
            return []

        scores = [r.get("score", 0) for r in results]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            # All scores are the same
            return [{**r, "score": 0.5} for r in results]

        normalized = []
        for r in results:
            score = r.get("score", 0)
            normalized_score = (score - min_score) / (max_score - min_score)
            normalized.append({**r, "score": normalized_score})

        return normalized
```

---

## 4. Tool Framework

### 4.1 Tool Registry and Management

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/domains/llm_integration/tools/registry.py`

```python
@dataclass
class ToolDefinition:
    """Definition of an available tool.

    Attributes:
        name: Tool name (used in function calls)
        description: Human-readable description
        parameters: JSON Schema for parameters
        handler: Async function to execute
        requires_sandbox: Whether tool needs sandboxing
        metadata: Additional tool metadata (tags, version, etc.)
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable
    requires_sandbox: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """Registry for LLM-callable tools.

    Class-level registry that manages tool registration and retrieval.
    Provides decorator-based registration and OpenAI-compatible schemas.

    Example:
        >>> @ToolRegistry.register(
        ...     name="search",
        ...     description="Search the knowledge base",
        ...     parameters={
        ...         "type": "object",
        ...         "properties": {
        ...             "query": {"type": "string", "description": "Search query"}
        ...         },
        ...         "required": ["query"]
        ...     }
        ... )
        >>> async def search_tool(query: str) -> dict:
        ...     return {"results": [...]}
    """

    _tools: dict[str, ToolDefinition] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        parameters: dict[str, Any],
        requires_sandbox: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Callable:
        """Decorator to register a tool in the registry.

        Args:
            name: Tool name (must be unique)
            description: Human-readable description
            parameters: JSON Schema for parameters
            requires_sandbox: Whether tool execution needs sandboxing
            metadata: Additional metadata (tags, version, etc.)

        Returns:
            Decorator function

        Example:
            >>> @ToolRegistry.register(
            ...     name="python_repl",
            ...     description="Execute Python code",
            ...     parameters={
            ...         "type": "object",
            ...         "properties": {
            ...             "code": {"type": "string", "description": "Python code"}
            ...         },
            ...         "required": ["code"]
            ...     },
            ...     requires_sandbox=True
            ... )
            >>> async def python_repl_tool(code: str) -> dict:
            ...     # Execute code in sandbox
            ...     pass
        """
        def decorator(handler: Callable) -> Callable:
            tool_def = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                handler=handler,
                requires_sandbox=requires_sandbox,
                metadata=metadata or {},
            )
            cls._tools[name] = tool_def

            logger.info(
                "tool_registered",
                name=name,
                requires_sandbox=requires_sandbox,
            )

            return handler

        return decorator

    @classmethod
    def get_tool(cls, name: str) -> ToolDefinition | None:
        """Get a tool definition by name.

        Args:
            name: Tool name

        Returns:
            ToolDefinition if found, None otherwise
        """
        return cls._tools.get(name)

    @classmethod
    def get_tools(cls) -> list[ToolDefinition]:
        """Get all registered tools.

        Returns:
            List of all tool definitions
        """
        return list(cls._tools.values())

    @classmethod
    def get_openai_tools_schema(cls) -> list[dict[str, Any]]:
        """Get OpenAI-compatible function calling schema.

        Returns:
            List of tool definitions in OpenAI format:
            [
                {
                    "type": "function",
                    "function": {
                        "name": "search",
                        "description": "...",
                        "parameters": {...}
                    }
                }
            ]
        """
        tools = []
        for tool in cls._tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            })

        return tools

    @classmethod
    async def execute_tool(
        cls,
        name: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a tool by name.

        Args:
            name: Tool name
            **kwargs: Tool parameters

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
            Exception: If tool execution fails
        """
        tool_def = cls._tools.get(name)
        if not tool_def:
            raise ValueError(f"Tool not found: {name}")

        logger.info("tool_executing", name=name, params=kwargs)

        try:
            result = await tool_def.handler(**kwargs)

            logger.info("tool_executed", name=name, success=True)

            return {
                "name": name,
                "result": result,
                "success": True,
            }

        except Exception as e:
            logger.error("tool_execution_failed", name=name, error=str(e))

            raise
```

---

### 4.2 Built-in Tools

Available tools for LLM agent tool use:

**Bash Tool** (`src/domains/llm_integration/tools/builtin/bash_tool.py`):
```python
@ToolRegistry.register(
    name="bash",
    description="Execute bash commands in secure sandbox",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Bash command to execute"}
        },
        "required": ["command"]
    },
    requires_sandbox=True,
)
async def bash_tool(command: str) -> dict[str, Any]:
    """Execute bash command securely.

    Args:
        command: Bash command string

    Returns:
        {
            "output": "Command output",
            "return_code": 0,
            "duration_ms": 123.45
        }
    """
    pass
```

**Python Tool** (`src/domains/llm_integration/tools/builtin/python_tool.py`):
```python
@ToolRegistry.register(
    name="python",
    description="Execute Python code in secure sandbox",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"}
        },
        "required": ["code"]
    },
    requires_sandbox=True,
)
async def python_tool(code: str) -> dict[str, Any]:
    """Execute Python code securely.

    Args:
        code: Python code string

    Returns:
        {
            "output": "Execution result",
            "return_code": 0,
            "duration_ms": 123.45
        }
    """
    pass
```

---

## 5. API Contracts

### 5.1 Chat Endpoint

Location: `/home/admin/projects/aegisrag/AEGIS_Rag/src/api/v1/chat.py`

```
POST /chat/message
Content-Type: application/json

Request:
{
    "query": "What is AegisRAG?",
    "session_id": "sess_123abc",  # Optional, for conversation history
    "intent": "hybrid",            # Optional: "vector", "graph", "hybrid", "memory", or "auto"
    "namespaces": ["default"],    # Optional: filter by namespace
    "metadata": {
        "user_id": "user_456",
        "source": "chat_ui"
    }
}

Response (with streaming via SSE):

event: phase_event
data: {
    "type": "phase_event",
    "phase_type": "INTENT_CLASSIFICATION",
    "status": "COMPLETED",
    "duration_ms": 45.2,
    "metadata": {"intent": "factual"}
}

event: phase_event
data: {
    "type": "phase_event",
    "phase_type": "VECTOR_SEARCH",
    "status": "COMPLETED",
    "duration_ms": 123.4,
    "metadata": {"results_count": 10}
}

event: token
data: {
    "type": "token",
    "content": " AegisRAG"
}

event: token
data: {
    "type": "token",
    "content": " is"
}

...

event: answer
data: {
    "type": "answer",
    "content": "AegisRAG is an agentic enterprise graph intelligence system...",
    "citation_map": {
        "1": {"source": "docs/architecture.md", "page": 5},
        "2": {"source": "docs/overview.md", "page": 1}
    },
    "metadata": {
        "intent": "factual",
        "search_mode": "hybrid",
        "contexts_count": 10,
        "latency_ms": 234.5
    }
}
```

**Chat Endpoint Function** (`src/api/v1/chat.py`):

```python
@router.post("/message")
async def chat_message(request: ChatRequest) -> StreamingResponse:
    """Chat endpoint with SSE streaming.

    Sprint 48 Feature 48.4: Chat Stream API Enhancement (8 SP)
    Sprint 48 Feature 48.5: Phase Events Redis Persistence (5 SP)
    Sprint 52: Token-by-token streaming and phase events

    Args:
        request: ChatRequest with query, session_id, intent, namespaces

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException: If request validation fails
    """
    query = request.query
    session_id = request.session_id or str(uuid.uuid4())
    intent = request.intent or "hybrid"
    namespaces = request.namespaces

    logger.info(
        "chat_message_received",
        query=query[:100],
        session_id=session_id,
        intent=intent,
    )

    async def event_stream():
        """Generate SSE events for streaming response."""
        try:
            # Get coordinator
            coordinator = get_coordinator()

            # Stream graph execution
            async for output in coordinator.stream(
                query=query,
                session_id=session_id,
                intent=intent,
                namespaces=namespaces,
            ):
                # output is yielded from graph.astream()
                for node_name, state_updates in output.items():
                    # Extract phase events if present
                    if "phase_events" in state_updates:
                        for event in state_updates["phase_events"]:
                            yield f"event: phase_event\n"
                            yield f"data: {json.dumps(event.model_dump_json())}\n\n"

                    # Extract answer if present
                    if node_name == "llm_answer" and "answer" in state_updates:
                        answer = state_updates["answer"]
                        citation_map = state_updates.get("citation_map", {})

                        yield f"event: answer\n"
                        yield f"data: {json.dumps({
                            'type': 'answer',
                            'content': answer,
                            'citation_map': citation_map,
                            'metadata': state_updates.get('metadata', {})
                        })}\n\n"

            # Save conversation turn
            await save_conversation_turn(
                session_id=session_id,
                user_message=query,
                assistant_message="",  # Will be filled from streamed response
                intent=intent,
            )

        except Exception as e:
            logger.error(
                "chat_message_error",
                error=str(e),
                session_id=session_id,
            )

            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )
```

---

## 6. Performance Characteristics

### 6.1 Latency Budgets

| Operation | Target P95 | Actual (Sprint 88) | Notes |
|-----------|------------|-------------------|-------|
| Intent Classification (SetFit) | 50ms | 20-50ms | C-LARA 5-class model |
| Vector Search (Qdrant) | 100ms | 80-150ms | Dense + sparse multi-vector |
| Graph Local Search | 100ms | 90-180ms | Entity → chunk expansion |
| Graph Global Search | 150ms | 120-250ms | Community → entity → chunk |
| RRF Fusion | 50ms | 30-60ms | Server-side for multi-vector |
| Cross-Encoder Reranking | 200ms | 150-300ms | BGE-Reranker-v2-M3 |
| LLM Answer Generation | 60s | 45-120s | Depends on response length |
| **Full Hybrid Query** | **500ms** | **400-700ms** | Without LLM generation |
| **Full Chat Response** | **90s** | **60-120s** | Including LLM streaming |

### 6.2 Resource Usage

- **Vector Database (Qdrant)**: ~500MB baseline, +1MB per 1000 indexed chunks
- **Graph Database (Neo4j)**: ~1GB baseline, +10MB per 1000 entity-relationship pairs
- **Memory Cache (Redis)**: ~100MB baseline, +1MB per conversation history (100 turns)
- **GPU Memory (Ollama/Embeddings)**: ~4GB for inference models
- **CPU/Memory (Backend)**: ~500MB per agent instance

### 6.3 Scaling Considerations

**Concurrent Users:**
- Single instance: 50-100 concurrent requests (depends on LLM latency)
- Horizontal scaling: Via Kubernetes deployment with load balancer
- Graph database bottleneck: Neo4j recommend sharding at 10M+ entities

**Document Ingestion:**
- Vector indexing: ~1000 chunks/min (8 cores, GPU)
- Graph extraction: ~500 chunks/min (entity extraction bottleneck)
- Recommendation: Batch ingestion with async workers

**Query Performance:**
- Vector search optimization: Use namespace filtering to reduce search space
- Graph traversal: Limit hops to 2-3 for <500ms latency
- Hybrid search: Graph queries are typically longer than vector (~2-3x slowdown)

---

## 7. Code Examples

### 7.1 Implementing a Custom Agent

```python
from src.agents.base_agent import BaseAgent
from src.agents.state import AgentState
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class CustomSearchAgent(BaseAgent):
    """Example custom agent for domain-specific search."""

    def __init__(self, name: str = "custom_search") -> None:
        """Initialize custom agent."""
        super().__init__(name=name)

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process state and return updated state.

        Args:
            state: Current agent state

        Returns:
            Updated state with custom results
        """
        query = state.get("query", "")

        if not query:
            self.logger.warning("empty_query")
            return state

        # Track execution
        timing = self._measure_latency()
        self._add_trace(state, "custom search started")

        try:
            # Custom search logic
            results = await self._custom_search(query)

            latency_ms = self._calculate_latency_ms(timing)

            # Update state
            if "retrieved_contexts" not in state:
                state["retrieved_contexts"] = []

            state["retrieved_contexts"].extend(results)

            # Add metadata
            if "metadata" not in state:
                state["metadata"] = {}

            state["metadata"]["custom_search"] = {
                "latency_ms": latency_ms,
                "result_count": len(results),
            }

            self._log_success(
                "custom_search",
                result_count=len(results),
                latency_ms=latency_ms,
            )

            self._add_trace(state, f"custom search completed ({len(results)} results)")

            return state

        except Exception as e:
            latency_ms = self._calculate_latency_ms(timing)
            self._log_error("custom_search", error=e, latency_ms=latency_ms)

            return await self.handle_error(state, e, "custom_search_processing")

    async def _custom_search(self, query: str) -> list[dict[str, Any]]:
        """Perform custom search.

        Args:
            query: Search query

        Returns:
            List of result dicts
        """
        # Implement custom search logic
        return [
            {
                "id": "result_1",
                "text": "Custom search result",
                "score": 0.95,
                "source": "custom",
                "document_id": "doc_123",
                "rank": 1,
                "search_type": "custom",
                "metadata": {},
            }
        ]


# Register node in LangGraph
async def custom_search_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node function for custom search."""
    agent = CustomSearchAgent()
    return await agent.process(state)


# Add to graph:
# graph.add_node("custom_search", custom_search_node)
# graph.add_edge("router", "custom_search")
# graph.add_edge("custom_search", "llm_answer")
```

---

### 7.2 Registering and Using Custom Tools

```python
from src.domains.llm_integration.tools.registry import ToolRegistry
from typing import Any

# Register tool
@ToolRegistry.register(
    name="calculate_distance",
    description="Calculate distance between two coordinates",
    parameters={
        "type": "object",
        "properties": {
            "lat1": {"type": "number", "description": "First latitude"},
            "lon1": {"type": "number", "description": "First longitude"},
            "lat2": {"type": "number", "description": "Second latitude"},
            "lon2": {"type": "number", "description": "Second longitude"},
        },
        "required": ["lat1", "lon1", "lat2", "lon2"]
    }
)
async def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> dict[str, Any]:
    """Calculate great-circle distance between two points.

    Args:
        lat1: First latitude
        lon1: First longitude
        lat2: Second latitude
        lon2: Second longitude

    Returns:
        Distance in kilometers
    """
    import math

    # Haversine formula
    R = 6371  # Earth radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat/2)**2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    )

    c = 2 * math.asin(math.sqrt(a))
    distance = R * c

    return {
        "distance_km": distance,
        "distance_miles": distance * 0.621371,
    }


# Use tool
async def example_usage():
    """Example of using the tool."""
    result = await ToolRegistry.execute_tool(
        "calculate_distance",
        lat1=40.7128,
        lon1=-74.0060,  # New York
        lat2=51.5074,
        lon2=-0.1278,   # London
    )

    print(f"Distance: {result['result']['distance_km']:.2f} km")
```

---

## 8. Debugging and Observability

### 8.1 Structured Logging

All agents emit structured logs with context:

```python
logger.info(
    "vector_search_completed",
    query=query[:100],
    result_count=10,
    latency_ms=234.5,
    intent="factual",
    weights={
        "vector": 0.3,
        "bm25": 0.3,
        "local": 0.4,
        "global": 0.0,
    }
)
```

### 8.2 Phase Event Tracking

Each agent phase emits structured phase events:

```python
PhaseEvent(
    phase_type=PhaseType.VECTOR_SEARCH,
    status=PhaseStatus.COMPLETED,
    start_time=datetime.utcnow(),
    end_time=datetime.utcnow(),
    duration_ms=234.5,
    metadata={
        "result_count": 10,
        "search_mode": "hybrid",
    },
)
```

### 8.3 Agent Path Tracing

State metadata includes agent_path for debugging:

```python
state["metadata"]["agent_path"] = [
    "router (llm): started",
    "router (llm): completed (100ms)",
    "VectorSearchAgent: started",
    "VectorSearchAgent: completed (10 results, 234ms)",
    "llm_answer: started",
    "llm_answer: completed (1250ms)",
]
```

---

## References

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **ADR-033**: AegisLLMProxy Multi-Cloud Routing
- **ADR-039**: Adaptive Section-Aware Chunking
- **ADR-040**: RELATES_TO Semantic Relationships
- **Sprint 88**: BGE-M3 Multi-Vector Integration
- **Sprint 81**: C-LARA SetFit Intent Classification
- **Sprint 68**: Tool Execution Reward Loop

---

**Document Version:** 1.0
**Last Updated:** Sprint 88 (2025-01-13)
**Status:** Production Ready
