# AegisRAG Agent Code Snippets - Reference Export

> This document contains key code snippets from AegisRAG's agentic architecture for understanding and extending the multi-agent system. Use this as a reference when designing new features or integrating with Claude AI.

## Table of Contents

1. [State Management](#1-state-management)
2. [Coordinator Agent](#2-coordinator-agent)
3. [Query Router & Intent Classification](#3-query-router--intent-classification)
4. [Retrieval Pipeline](#4-retrieval-pipeline)
5. [Memory Agent](#5-memory-agent)
6. [Action Agent & Tools](#6-action-agent--tools)
7. [Streaming & Real-Time Events](#7-streaming--real-time-events)
8. [Design Patterns](#8-design-patterns)

---

## 1. State Management

### 1.1 Agent State Schema

**File:** `src/agents/state.py` (Lines 48-118)

**Purpose:** Central state object passed between all LangGraph nodes

```python
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from typing import Any, Literal

class AgentState(MessagesState):
    """State passed between LangGraph nodes.

    This is the central state object that flows through the entire agent graph.
    Each agent reads from and writes to this state.

    Inherits from MessagesState to maintain message history and integrates
    with LangChain's message-based conversation flow.
    """

    query: str = Field(default="", description="Original user query")
    intent: str = Field(
        default="hybrid",
        description="Detected query intent (vector, graph, hybrid, direct)",
    )
    retrieved_contexts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved document contexts from search",
    )
    search_mode: Literal["vector", "graph", "hybrid"] = Field(
        default="hybrid",
        description="Search mode to use for retrieval",
    )
    graph_query_result: dict[str, Any] | None = Field(
        default=None,
        description="Results from graph RAG query",
    )
    memory_results: dict[str, Any] | None = Field(
        default=None,
        description="Results from memory retrieval",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for execution tracking",
    )
    citation_map: dict[int, dict[str, Any]] = Field(
        default_factory=dict,
        description="Map of citation numbers to source metadata",
    )
    answer: str = Field(
        default="",
        description="Generated answer from LLM",
    )
    namespaces: list[str] | None = Field(
        default=None,
        description='Namespaces to search in. Defaults to ["default", "general"]',
    )
    phase_event: Any | None = Field(
        default=None,
        description="Latest phase event emitted by the current node",
    )
    phase_events: list[Any] = Field(
        default_factory=list,
        description="List of all phase events for streaming",
    )
    tool_execution_count: int = Field(
        default=0,
        ge=0,
        description="Number of tool executions in this conversation",
    )
```

**Key Design Pattern:** TypedDict with Pydantic v2 validation

**Dependencies:** LangChain MessagesState, Pydantic BaseModel

### 1.2 State Creation & Initialization

**File:** `src/agents/state.py` (Lines 155-184)

**Purpose:** Factory function for creating initial agent state

```python
def create_initial_state(
    query: str,
    intent: str = "hybrid",
    namespaces: list[str] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Create initial agent state from user query.

    Args:
        query: User's query string
        intent: Detected intent (default: "hybrid")
        namespaces: Namespaces to search in (default: None)
        session_id: Session identifier for real-time phase event streaming

    Returns:
        Dictionary representing the initial AgentState
    """
    return {
        "messages": [],
        "query": query,
        "intent": intent,
        "retrieved_contexts": [],
        "search_mode": intent if intent in ["vector", "graph", "hybrid"] else "hybrid",
        "namespaces": namespaces,
        "session_id": session_id,  # Sprint 52: For real-time phase events
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "agent_path": [],
        },
    }
```

### 1.3 State Metadata Tracking

**File:** `src/agents/state.py` (Lines 187-215)

**Purpose:** Update state metadata as agents execute

```python
def update_state_metadata(
    state: dict[str, Any],
    agent_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update state metadata with agent execution info.

    Args:
        state: Current agent state
        agent_name: Name of the agent updating the state
        **kwargs: Additional metadata fields to update

    Returns:
        Updated state dictionary
    """
    if "metadata" not in state:
        state["metadata"] = {}

    if "agent_path" not in state["metadata"]:
        state["metadata"]["agent_path"] = []

    # Add agent to path if not already the last entry
    if not state["metadata"]["agent_path"] or state["metadata"]["agent_path"][-1] != agent_name:
        state["metadata"]["agent_path"].append(agent_name)

    # Update additional metadata
    state["metadata"].update(kwargs)

    return state
```

---

## 2. Coordinator Agent

### 2.1 Coordinator Initialization

**File:** `src/agents/coordinator.py` (Lines 195-228)

**Purpose:** Main orchestrator for the multi-agent system

```python
class CoordinatorAgent:
    """Main orchestrator agent for the multi-agent RAG system.

    The Coordinator manages:
    - Query initialization and state creation
    - LangGraph compilation and invocation
    - Session-based conversation history
    - Error handling and recovery
    - Performance tracking and observability
    """

    def __init__(
        self,
        use_persistence: bool = True,
        recursion_limit: int | None = None,
    ) -> None:
        """Initialize Coordinator Agent.

        Sprint 70 Feature 70.7: Lazy graph compilation with tools config

        Args:
            use_persistence: Enable conversation persistence (default: True)
            recursion_limit: Max recursion depth for LangGraph
        """
        self.name = "CoordinatorAgent"
        self.use_persistence = use_persistence
        self.recursion_limit = recursion_limit or settings.langgraph_recursion_limit

        # Create checkpointer if persistence is enabled
        self.checkpointer: MemorySaver | None = None
        if self.use_persistence:
            self.checkpointer = create_checkpointer()

        # Sprint 70: Lazy graph compilation
        # Graph is compiled on first request with tools config from Redis
        self.compiled_graph: Any | None = None
        self._graph_cache_expires_at: datetime | None = None
        self._graph_cache_ttl_seconds = 60  # Re-check config every 60s

        logger.info(
            "coordinator_initialized",
            use_persistence=self.use_persistence,
            recursion_limit=self.recursion_limit,
            lazy_compilation=True,
        )
```

### 2.2 Lazy Graph Compilation with Hot-Reload

**File:** `src/agents/coordinator.py` (Lines 230-274)

**Purpose:** Get or compile graph with tools config caching

```python
async def _get_or_compile_graph(self) -> Any:
    """Get compiled graph, compiling if necessary.

    Sprint 70 Feature 70.7: Lazy compilation with config hot-reload

    Compiles graph on first call and caches for 60 seconds.
    After cache expires, re-compiles with fresh tools config from Redis.

    Returns:
        Compiled LangGraph instance
    """
    from datetime import datetime, timedelta
    from src.agents.graph import compile_graph_with_tools_config

    # Check if cache is still valid
    now = datetime.now()
    if (
        self.compiled_graph is not None
        and self._graph_cache_expires_at is not None
        and now < self._graph_cache_expires_at
    ):
        logger.debug("using_cached_compiled_graph")
        return self.compiled_graph

    # Cache expired or first compilation - load config and compile
    logger.info("compiling_graph_with_fresh_config", cache_ttl_seconds=self._graph_cache_ttl_seconds)

    self.compiled_graph = await compile_graph_with_tools_config(
        checkpointer=self.checkpointer
    )

    # Set cache expiration
    self._graph_cache_expires_at = now + timedelta(seconds=self._graph_cache_ttl_seconds)

    logger.info("graph_compiled_and_cached", expires_in_seconds=self._graph_cache_ttl_seconds)

    return self.compiled_graph
```

### 2.3 Process Query (Synchronous)

**File:** `src/agents/coordinator.py` (Lines 276-412)

**Purpose:** Main entry point for single query processing

```python
@retry_on_failure(max_attempts=2, backoff_factor=1.5)
async def process_query(
    self,
    query: str,
    session_id: str | None = None,
    intent: str | None = None,
    namespaces: list[str] | None = None,
) -> dict[str, Any]:
    """Process a user query through the multi-agent system.

    Args:
        query: User's query string
        session_id: Optional session ID for conversation persistence
        intent: Optional intent override (default: let router decide)
        namespaces: Optional list of namespaces to search in

    Returns:
        Final state dictionary containing:
            - query: Original query
            - intent: Detected/assigned intent
            - retrieved_contexts: List of retrieved documents
            - messages: Conversation history
            - metadata: Execution metadata (latency, agent_path, etc.)

    Raises:
        Exception: If query processing fails after retries
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

        # Invoke graph (Sprint 70: lazy compilation with tools config)
        graph = await self._get_or_compile_graph()
        final_state = await graph.ainvoke(
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

        logger.info(
            "coordinator_query_complete",
            query=query[:100],
            session_id=session_id,
            latency_ms=latency_ms,
            result_count=len(final_state.get("retrieved_contexts", [])),
        )

        return final_state

    except Exception as e:
        logger.error(
            "coordinator_query_failed",
            query=query[:100],
            session_id=session_id,
            error=str(e),
        )
        raise
```

### 2.4 Streaming Query with Phase Events

**File:** `src/agents/coordinator.py` (Lines 485-593)

**Purpose:** Stream phase events and final answer during processing

```python
async def process_query_stream(
    self,
    query: str,
    session_id: str | None = None,
    intent: str | None = None,
    namespaces: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """Stream phase events and final answer during query processing.

    Sprint 48 Feature 48.2: CoordinatorAgent Streaming Method

    This method provides real-time visibility into the query processing pipeline
    by emitting phase events as each agent executes.

    Args:
        query: User's query string
        session_id: Optional session ID for conversation persistence
        intent: Optional intent override
        namespaces: Optional list of namespaces to search in

    Yields:
        dict: Events with types:
            - phase_event: PhaseEvent updates (start, progress, completion)
            - answer_chunk: Streaming answer text (final answer)
            - reasoning_complete: Final reasoning summary
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
                    "data": event.model_dump(mode="json"),
                }

            elif isinstance(event, dict):
                event_type = event.get("type")

                if event_type == "token":
                    # Sprint 52: Stream token directly to SSE handler
                    yield event

                elif event_type == "citation_map":
                    # Sprint 52: Stream citation map directly to SSE handler
                    yield event

                elif "answer" in event:
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
        raise
```

### 2.5 Async Follow-up Generation

**File:** `src/agents/coordinator.py` (Lines 846-940)

**Purpose:** Generate follow-up questions asynchronously without blocking

```python
async def _generate_followup_async(
    self,
    session_id: str,
    query: str,
    answer: str,
    sources: list[dict[str, Any]],
) -> None:
    """Generate follow-up questions asynchronously in background.

    Sprint 52 Feature 52.3: Async Follow-up Questions

    This method runs as a background task and:
    1. Stores conversation context in Redis
    2. Generates follow-up questions (does NOT block answer display)
    3. Questions are retrieved via GET /chat/sessions/{session_id}/followup-questions

    Args:
        session_id: Session ID
        query: User query
        answer: Generated answer
        sources: Retrieved source documents
    """
    try:
        from src.agents.followup_generator import (
            generate_followup_questions_async,
            store_conversation_context,
        )

        # Store context in Redis for follow-up generation
        success = await store_conversation_context(
            session_id=session_id,
            query=query,
            answer=answer,
            sources=sources,
        )

        if success:
            logger.info("followup_context_stored_for_async", session_id=session_id)

            # Sprint 65 Fix: Actually generate the follow-up questions!
            try:
                questions = await generate_followup_questions_async(session_id)
                if questions:
                    logger.info(
                        "followup_questions_generated_async",
                        session_id=session_id,
                        count=len(questions),
                    )

                    # Sprint 65 Fix: STORE the generated questions in Redis
                    from src.components.memory import get_redis_memory
                    redis_memory = get_redis_memory()
                    cache_key = f"{session_id}:followup"
                    await redis_memory.store(
                        key=cache_key,
                        value={"questions": questions},
                        namespace="cache",
                        ttl_seconds=300,  # 5 minutes
                    )
                    logger.info(
                        "followup_questions_cached",
                        session_id=session_id,
                        count=len(questions),
                    )
            except Exception as gen_error:
                logger.error(
                    "followup_questions_generation_failed_async",
                    session_id=session_id,
                    error=str(gen_error),
                )

    except Exception as e:
        logger.error(
            "followup_async_task_failed",
            session_id=session_id,
            error=str(e),
        )
```

### 2.6 Singleton Pattern

**File:** `src/agents/coordinator.py` (Lines 991-1013)

**Purpose:** Global coordinator instance management

```python
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
```

---

## 3. Query Router & Intent Classification

### 3.1 Intent Enum & Classification

**File:** `src/components/retrieval/intent_classifier.py` (Lines 49-78)

**Purpose:** Define query intent types

```python
class Intent(str, Enum):
    """Query intent types for 4-Way Hybrid RRF."""

    FACTUAL = "factual"
    KEYWORD = "keyword"
    EXPLORATORY = "exploratory"
    SUMMARY = "summary"


class CLARAIntent(str, Enum):
    """C-LARA intent types from SetFit training (Sprint 81).

    Amazon Science C-LARA Framework:
    - Context-aware LLM-Assisted RAG intent detection
    - 5 classes for fine-grained query routing

    Mapping to IntentWeights (for 4-Way Hybrid RRF):
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
```

### 3.2 Intent Weights for RRF Fusion

**File:** `src/components/retrieval/intent_classifier.py` (Lines 80-130)

**Purpose:** Define RRF weights per intent type

```python
@dataclass(frozen=True)
class IntentWeights:
    """RRF weights for each retrieval channel based on intent.

    The weights determine how much each retrieval channel contributes
    to the final RRF score:
        score(chunk) = w_vec * 1/(k+r_vec) + w_bm25 * 1/(k+r_bm25)
                     + w_local * 1/(k+r_local) + w_global * 1/(k+r_global)

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


# Legacy 4-class weight profiles
INTENT_WEIGHT_PROFILES: dict[Intent, IntentWeights] = {
    Intent.FACTUAL: IntentWeights(vector=0.3, bm25=0.3, local=0.4, global_=0.0),
    Intent.KEYWORD: IntentWeights(vector=0.1, bm25=0.6, local=0.3, global_=0.0),
    Intent.EXPLORATORY: IntentWeights(vector=0.2, bm25=0.1, local=0.2, global_=0.5),
    Intent.SUMMARY: IntentWeights(vector=0.1, bm25=0.0, local=0.1, global_=0.8),
}

# Sprint 81: C-LARA 5-class weight profiles
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
```

### 3.3 Intent Classifier with SetFit & Embeddings

**File:** `src/components/retrieval/intent_classifier.py` (Lines 197-270)

**Purpose:** Multi-method intent classification with SetFit as primary

```python
class IntentClassifier:
    """Intent Classifier with C-LARA SetFit and Zero-Shot Embedding Classification.

    Classification Methods:
    1. setfit (Sprint 67): C-LARA trained SetFit model (~20-50ms, 85-92% accuracy)
    2. embedding: Zero-Shot using BGE-M3 embeddings (~20-50ms, 60% accuracy)
    3. rule_based: Fast regex patterns (~0ms, fallback)
    4. llm: LLM-based classification (~2-10s, optional)

    Example:
        classifier = IntentClassifier(method="setfit")
        result = await classifier.classify("What is OMNITRACKER?")
        # result.intent == Intent.FACTUAL
        # result.method == "setfit"
        # result.latency_ms ~= 30.0
        # result.confidence ~= 0.92
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
        method: str = "setfit",
        setfit_model_path: str | None = None,
    ):
        """Initialize Intent Classifier.

        Args:
            base_url: Ollama API URL (for LLM fallback)
            model: LLM model to use (for LLM fallback)
            timeout: Request timeout in seconds
            method: Classification method: "setfit", "embedding", "rule_based", or "llm"
            setfit_model_path: Path to SetFit model directory
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL_INTENT", "nemotron-3-nano")
        self.timeout = timeout
        self.method = method
        self.client = httpx.AsyncClient(timeout=timeout)

        # Sprint 67: SetFit model configuration
        self.setfit_model_path = setfit_model_path or os.getenv(
            "INTENT_CLASSIFIER_MODEL_PATH", "models/intent_classifier"
        )
        self.use_setfit = os.getenv("USE_SETFIT_CLASSIFIER", "true").lower() == "true"
        self.setfit_model: SetFitModel | None = None
        self.setfit_initialized = False

        # Cache for query classifications (LRU)
        self._cache: dict[str, tuple[Intent, float]] = {}
        self._cache_max_size = 1000

        # Sprint 52: Cache for intent description embeddings
        self._intent_embeddings: dict[Intent, list[float]] = {}
        self._embeddings_initialized = False

        logger.info(
            "IntentClassifier initialized",
            method=method,
            use_setfit=self.use_setfit,
            setfit_model_path=self.setfit_model_path,
        )
```

### 3.4 SetFit Classification with Confidence

**File:** `src/components/retrieval/intent_classifier.py` (Lines 354-447)

**Purpose:** Classify using C-LARA trained SetFit model

```python
def _classify_with_setfit(self, query: str) -> tuple[CLARAIntent, float]:
    """Classify using C-LARA trained SetFit model.

    Sprint 67: Uses fine-tuned SetFit model for 85-92% accuracy.
    Sprint 81: Updated for 5-class C-LARA intents (95% accuracy).

    Args:
        query: User query

    Returns:
        Tuple of (CLARAIntent, confidence)

    Raises:
        ValueError: If SetFit model is not loaded
    """
    if self.setfit_model is None:
        raise ValueError("SetFit model not loaded")

    # Run prediction
    predict_start = time.perf_counter()
    predictions = self.setfit_model.predict([query])
    predict_time_ms = (time.perf_counter() - predict_start) * 1000

    # Get predicted label - handle both string, int, and tensor predictions
    prediction = predictions[0]

    # Convert tensor to native Python type if needed
    if hasattr(prediction, 'item'):
        prediction = prediction.item()
    elif hasattr(prediction, 'numpy'):
        prediction = prediction.numpy().item()

    # Sprint 81: C-LARA 5-class model returns string labels
    if isinstance(prediction, str):
        label_str = prediction.lower()
        string_to_intent = {
            "factual": CLARAIntent.FACTUAL,
            "procedural": CLARAIntent.PROCEDURAL,
            "comparison": CLARAIntent.COMPARISON,
            "recommendation": CLARAIntent.RECOMMENDATION,
            "navigation": CLARAIntent.NAVIGATION,
        }
        intent = string_to_intent.get(label_str, CLARAIntent.FACTUAL)
    else:
        # Legacy: Integer label (0-4 for C-LARA 5-class)
        predicted_label = int(prediction)
        label_to_intent = {
            0: CLARAIntent.FACTUAL,
            1: CLARAIntent.PROCEDURAL,
            2: CLARAIntent.COMPARISON,
            3: CLARAIntent.RECOMMENDATION,
            4: CLARAIntent.NAVIGATION,
        }
        intent = label_to_intent.get(predicted_label, CLARAIntent.FACTUAL)

    # Get prediction probabilities for confidence
    try:
        probs = self.setfit_model.predict_proba([query])[0]
        # Convert tensor to list/array if needed
        if hasattr(probs, 'tolist'):
            probs = probs.tolist()
        elif hasattr(probs, 'numpy'):
            probs = probs.numpy().tolist()
        confidence = float(max(probs))

        # Calculate margin (difference between top 2 predictions)
        sorted_probs = sorted(probs, reverse=True)
        margin = sorted_probs[0] - sorted_probs[1] if len(sorted_probs) > 1 else 0.0

        logger.debug(
            "setfit_classification_complete",
            query=query[:50],
            intent=intent.value,
            confidence=round(confidence, 4),
            margin=round(margin, 4),
        )

    except AttributeError:
        # Model doesn't support predict_proba, use default confidence
        confidence = 0.85  # Default for SetFit models
        logger.debug(
            "setfit_classification_complete",
            query=query[:50],
            intent=intent.value,
            confidence=confidence,
            note="predict_proba not available",
        )

    return intent, confidence
```

### 3.5 Main Classification Method

**File:** `src/components/retrieval/intent_classifier.py` (Lines 449-586)

**Purpose:** Main entry point with fallback chain

```python
async def classify(self, query: str) -> "IntentClassificationResult":
    """Classify query intent and return weights.

    Args:
        query: User query string

    Returns:
        IntentClassificationResult with intent, weights, and metadata
    """
    start_time = time.perf_counter()

    # Normalize query for cache lookup
    cache_key = query.lower().strip()

    # Check cache first
    if cache_key in self._cache:
        cached_data = self._cache[cache_key]
        # ... cache handling code ...
        logger.debug("intent_cache_hit", query=query[:50])
        return IntentClassificationResult(...)

    # Classify based on configured method
    intent: Intent | None = None
    clara_intent: CLARAIntent | None = None
    weights: IntentWeights | None = None
    confidence = 0.0
    method = self.method

    # Sprint 67/81: Try SetFit first if enabled (returns CLARAIntent)
    if self.method == "setfit":
        try:
            self._ensure_setfit_model()
            if self.setfit_model is not None:
                clara_intent, confidence = self._classify_with_setfit(query)
                weights = CLARA_INTENT_WEIGHT_PROFILES[clara_intent]
                # Map CLARAIntent to legacy Intent for backward compatibility
                intent = self._clara_to_legacy_intent(clara_intent)
                method = "setfit"
            else:
                clara_intent = None
        except Exception as e:
            logger.warning(
                "setfit_classification_failed",
                query=query[:50],
                error=str(e),
                fallback="embedding or rule_based",
            )
            clara_intent = None

    # Fallback to embedding if setfit failed
    if intent is None and self.method in ["setfit", "embedding"]:
        try:
            intent, confidence = await self._classify_with_embeddings(query)
            weights = INTENT_WEIGHT_PROFILES[intent]
            method = "embedding"
        except Exception as e:
            logger.warning(
                "embedding_classification_failed",
                query=query[:50],
                error=str(e),
                fallback="rule_based",
            )
            intent = None

    # LLM fallback
    elif intent is None and self.method == "llm":
        try:
            intent, confidence = await self._classify_with_llm(query)
            weights = INTENT_WEIGHT_PROFILES[intent]
            method = "llm"
        except Exception as e:
            logger.warning(
                "llm_classification_failed",
                query=query[:50],
                error=str(e),
                fallback="rule_based",
            )
            intent = None

    # Final fallback: rule-based
    if intent is None:
        intent = self._classify_rule_based(query)
        weights = INTENT_WEIGHT_PROFILES[intent]
        confidence = 0.7
        method = "rule_based"

    # Update cache with LRU eviction
    if len(self._cache) >= self._cache_max_size:
        oldest_key = next(iter(self._cache))
        del self._cache[oldest_key]
    self._cache[cache_key] = (
        intent.value,
        weights,
        clara_intent.value if clara_intent else None,
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "intent_classified",
        query=query[:50],
        intent=intent.value,
        clara_intent=clara_intent.value if clara_intent else None,
        confidence=round(confidence, 2),
        method=method,
        latency_ms=round(latency_ms, 2),
    )

    return IntentClassificationResult(
        intent=intent,
        weights=weights,
        confidence=confidence,
        latency_ms=latency_ms,
        method=method,
        clara_intent=clara_intent,
    )
```

---

## 4. Retrieval Pipeline

### 4.1 Vector Search Agent with 4-Way Hybrid

**File:** `src/agents/vector_search_agent.py` (Lines 30-100)

**Purpose:** Execute 4-way hybrid search with intent classification

```python
class VectorSearchAgent(BaseAgent):
    """Agent for 4-way hybrid search with intent classification.

    Integrates 4-Way Hybrid Search with automatic intent classification.
    Performs retrieval and updates state with results, intent metadata, and weights.
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
            top_k: Number of results to retrieve (default from settings)
            use_reranking: Whether to apply reranking (default: use settings)
            max_retries: Maximum retry attempts on failure (default: 3)
        """
        super().__init__(name="VectorSearchAgent")
        self.four_way_search = four_way_search or FourWayHybridSearch()
        self.top_k = top_k or settings.retrieval_top_k
        self.use_reranking = use_reranking if use_reranking is not None else settings.reranker_enabled
        self.max_retries = max_retries

        self.logger.info(
            "VectorSearchAgent initialized (4-Way Hybrid + Intent)",
            top_k=self.top_k,
            use_reranking=self.use_reranking,
            max_retries=self.max_retries,
        )
```

---

## 5. Memory Agent

### 5.1 Memory Agent Implementation

**File:** `src/agents/memory_agent.py` (Lines 45-100)

**Purpose:** Execute memory queries across 3-layer architecture

```python
class MemoryAgent(BaseAgent):
    """Agent for episodic and semantic memory retrieval.

    Processes MEMORY intent queries by:
    1. Routing query to appropriate memory layer(s) (Redis/Qdrant/Graphiti)
    2. Executing memory search via MemoryRouter
    3. Updating AgentState with memory results
    4. Tracking execution metadata

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
        # Start timing implementation...
        pass
```

---

## 6. Action Agent & Tools

### 6.1 Secure Action Agent Configuration

**File:** `src/agents/action/secure_action_agent.py` (Lines 44-70)

**Purpose:** Configuration for sandboxed code execution

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
```

### 6.2 Secure Action Agent Class

**File:** `src/agents/action/secure_action_agent.py` (Lines 72-120)

**Purpose:** Main secure action agent for tool execution

```python
class SecureActionAgent:
    """Action agent with secure sandboxed code execution via deepagents.

    Provides secure command execution using BubblewrapSandboxBackend with
    timeout enforcement, retry logic, and resource cleanup.

    Features:
    - Sandbox isolation (filesystem + network)
    - Timeout enforcement (configurable)
    - Retry logic for transient failures
    - Resource cleanup on shutdown
    - LangChain-compatible interface

    Example:
        >>> config = ActionConfig(sandbox_timeout=30)
        >>> agent = SecureActionAgent(config=config)
        >>> result = await agent.execute_action("ls -la /repo")
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
            config: Agent configuration (defaults to ActionConfig())
            sandbox_backend: Custom sandbox backend (optional)
            policy: Tool selection policy (optional, created if None)
            reward_calculator: Reward calculator (optional, created if None)

        Raises:
            ValueError: If repo_path doesn't exist
            FileNotFoundError: If bubblewrap binary not found
        """
        self.logger = structlog.get_logger(__name__)
        self.config = config or ActionConfig()

        # Initialize sandbox backend
        if sandbox_backend is None:
            sandbox_backend = BubblewrapSandboxBackend(
                repo_path=self.config.repo_path,
                timeout=self.config.sandbox_timeout,
                workspace_path=self.config.workspace_path,
            )

        self.sandbox_backend = sandbox_backend
        # ... additional initialization ...
```

### 6.3 Tool Executor with Validation

**File:** `src/domains/llm_integration/tools/executor.py` (Lines 41-100)

**Purpose:** Execute tools with parameter validation

```python
class ToolExecutor:
    """Executes registered tools with validation and sandboxing.

    Handles tool execution with comprehensive error handling, validation,
    and optional sandboxing for security-critical operations.

    Attributes:
        sandbox_enabled: Whether to use sandboxing for tools that require it
        _execution_count: Counter for total executions
        _error_count: Counter for failed executions
    """

    def __init__(self, sandbox_enabled: bool = True) -> None:
        """Initialize tool executor.

        Args:
            sandbox_enabled: Enable sandbox for tools that require it
                           (default: True)
        """
        self.sandbox_enabled = sandbox_enabled
        self._execution_count = 0
        self._error_count = 0

        logger.info("tool_executor_initialized", sandbox_enabled=sandbox_enabled)

    async def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool by name with parameter validation.

        Args:
            tool_name: Name of the registered tool
            parameters: Tool input parameters

        Returns:
            Dict with either:
                - {"result": <tool_output>} on success
                - {"error": "<error_message>"} on failure

        Example:
            >>> executor = ToolExecutor()
            >>> result = await executor.execute(
            ...     "calculator",
            ...     {"operation": "add", "a": 5, "b": 3}
            ... )
            >>> assert result == {"result": 8}
        """
        execution_start = time.perf_counter()
        self._execution_count += 1

        try:
            # Look up tool in registry
            tool = ToolRegistry.get_tool(tool_name)
            if not tool:
                self._error_count += 1
                logger.warning("tool_not_found", tool_name=tool_name)
                return {"error": f"Unknown tool: {tool_name}"}

            # Validate parameters
            # ... validation code ...

        except Exception as e:
            self._error_count += 1
            logger.error("tool_execution_failed", tool_name=tool_name, error=str(e))
            return {"error": str(e)}
```

### 6.4 Tool Parameter Schemas

**File:** `src/domains/llm_integration/tools/schemas.py` (Lines 40-100)

**Purpose:** Define JSON schemas for tool parameters

```python
def create_parameter_schema(
    properties: dict[str, dict[str, Any]],
    required: list[str] | None = None,
    additional_properties: bool = False,
) -> dict[str, Any]:
    """Create JSON Schema for tool parameters.

    Args:
        properties: Property definitions (name -> schema)
        required: List of required property names
        additional_properties: Allow extra properties (default: False)

    Returns:
        JSON Schema dict

    Example:
        >>> schema = create_parameter_schema(
        ...     properties={
        ...         "name": {
        ...             "type": "string",
        ...             "description": "User name"
        ...         },
        ...         "age": {
        ...             "type": "integer",
        ...             "minimum": 0
        ...         }
        ...     },
        ...     required=["name"]
        ... )
    """
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": additional_properties,
    }


def create_function_schema(
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Create OpenAI function calling schema.

    Args:
        name: Function name
        description: Human-readable description
        parameters: JSON Schema for parameters

    Returns:
        OpenAI function schema
    """
    # ... implementation ...
```

---

## 7. Streaming & Real-Time Events

### 7.1 Phase Event System

**File:** `src/agents/phase_events_queue.py` (Lines 1-66)

**Purpose:** Real-time phase event updates during query processing

```python
"""Phase Event System for Real-Time Chat Progress - Sprint 52.

This module provides real-time phase event updates during query processing.

Two methods are available:
1. stream_phase_event() - Uses LangGraph's get_stream_writer() for REAL-TIME
   events that are emitted DURING node execution (preferred method).
2. emit_phase_event() (legacy) - Uses async queues, but these are only
   drained when the event loop yields.

Usage:
    # PREFERRED: In LangGraph nodes using stream_mode=["custom", "values"]:
    from src.agents.phase_events_queue import stream_phase_event

    stream_phase_event(
        phase_type=PhaseType.INTENT_CLASSIFICATION,
        status=PhaseStatus.IN_PROGRESS,
    )
"""

import asyncio
from datetime import datetime
from langgraph.config import get_stream_writer
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

# Global registry of phase event queues per session
_phase_queues: dict[str, asyncio.Queue] = {}
_phase_lock = asyncio.Lock()


async def get_or_create_phase_queue(session_id: str) -> asyncio.Queue:
    """Get or create a phase event queue for a session.

    Args:
        session_id: Session identifier

    Returns:
        AsyncIO queue for phase events
    """
    async with _phase_lock:
        if session_id not in _phase_queues:
            _phase_queues[session_id] = asyncio.Queue(maxsize=50)
            logger.debug("phase_queue_created", session_id=session_id)
        return _phase_queues[session_id]
```

### 7.2 SSE Streaming in Chat API

**File:** `src/api/v1/chat.py` (Lines 1-60)

**Purpose:** Server-sent events for real-time responses

```python
"""Chat API Endpoints for AEGIS RAG.

Sprint 10 Feature 10.1: FastAPI Chat Endpoints
Sprint 15 Feature 15.1: SSE Streaming Endpoint
Sprint 17 Feature 17.2: Conversation History Persistence
Sprint 48 Feature 48.4: Chat Stream API Enhancement (8 SP)
Sprint 48 Feature 48.5: Phase Events Redis Persistence (5 SP)

This module provides RESTful chat endpoints for the Gradio UI and React frontend.
It integrates the CoordinatorAgent for query processing and UnifiedMemoryAPI for session management.
Includes Server-Sent Events (SSE) streaming for real-time token-by-token responses with phase events.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.agents.coordinator import CoordinatorAgent
from src.agents.followup_generator import generate_followup_questions

# Timeout constants
REQUEST_TIMEOUT_SECONDS = 90  # Total request timeout
PHASE_TIMEOUT_SECONDS = 30  # Individual phase timeout
LLM_TIMEOUT_SECONDS = 60  # LLM generation timeout

router = APIRouter(prefix="/chat", tags=["chat"])


def get_coordinator() -> CoordinatorAgent:
    """Get or create singleton CoordinatorAgent instance."""
    global _coordinator
    if _coordinator is None:
        _coordinator = CoordinatorAgent(use_persistence=True)
        logger.info("coordinator_initialized_for_chat_api")
    return _coordinator
```

---

## 8. Design Patterns

### 8.1 Singleton Pattern (Coordinator)

**Pattern Name:** Singleton

**Used In:** CoordinatorAgent, IntentClassifier

**Purpose:** Ensure single instance of expensive resources

```python
# Global instance
_coordinator: CoordinatorAgent | None = None

def get_coordinator(use_persistence: bool = True, force_new: bool = False) -> CoordinatorAgent:
    """Get global coordinator instance (singleton)."""
    global _coordinator
    if _coordinator is None or force_new:
        _coordinator = CoordinatorAgent(use_persistence=use_persistence)
    return _coordinator
```

**Benefit:** Reuses compiled LangGraph and checkpointer across requests

---

### 8.2 State Machine Pattern (LangGraph)

**Pattern Name:** State Machine

**Used In:** LangGraph agent workflow

**Purpose:** Orchestrate multi-agent pipeline with conditional routing

```python
# State flows through nodes:
# query → router → [vector_agent | graph_agent | memory_agent] → llm_generator → answer

# Each node is a state transition:
# initial_state → process() → updated_state
```

**Benefit:** Clear separation of concerns, testability, observability

---

### 8.3 Strategy Pattern (Intent Classification)

**Pattern Name:** Strategy

**Used In:** IntentClassifier with multiple classification methods

**Purpose:** Switch between classification algorithms at runtime

```python
# Methods: setfit → embedding → rule_based → llm
# Each method is a strategy that can be swapped

if self.method == "setfit":
    intent, confidence = self._classify_with_setfit(query)
elif self.method == "embedding":
    intent, confidence = await self._classify_with_embeddings(query)
elif self.method == "rule_based":
    intent = self._classify_rule_based(query)
else:
    intent, confidence = await self._classify_with_llm(query)
```

**Benefit:** Easy to swap strategies, test different approaches, A/B testing

---

### 8.4 Factory Pattern (State Creation)

**Pattern Name:** Factory

**Used In:** create_initial_state()

**Purpose:** Encapsulate state creation logic

```python
def create_initial_state(
    query: str,
    intent: str = "hybrid",
    namespaces: list[str] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Factory function for creating initial agent state."""
    return {
        "messages": [],
        "query": query,
        "intent": intent,
        # ... other fields ...
    }
```

**Benefit:** Centralized state initialization, easier to maintain defaults

---

### 8.5 Decorator Pattern (Retry Logic)

**Pattern Name:** Decorator

**Used In:** @retry_on_failure, @retry (Tenacity)

**Purpose:** Add retry logic to methods transparently

```python
@retry_on_failure(max_attempts=3, backoff_factor=1.5)
async def process_query(self, query: str, ...) -> dict[str, Any]:
    """Process query with automatic retries on failure."""
    # Method will automatically retry 3 times with exponential backoff
    pass
```

**Benefit:** Clean separation of business logic and error handling

---

### 8.6 Observer Pattern (Phase Events)

**Pattern Name:** Observer

**Used In:** stream_phase_event(), SSE streaming

**Purpose:** Emit real-time events to frontend as agents execute

```python
# During node execution:
stream_phase_event(
    phase_type=PhaseType.INTENT_CLASSIFICATION,
    status=PhaseStatus.COMPLETED,
    details={"confidence": 0.92}
)

# Frontend subscribes via SSE:
# GET /chat/stream?session_id=xxx
# Receives: {"type": "phase_event", "data": {...}}
```

**Benefit:** Real-time visibility, streaming UI updates, no polling

---

### 8.7 Builder Pattern (Tool Schema)

**Pattern Name:** Builder

**Used In:** create_parameter_schema(), create_function_schema()

**Purpose:** Construct complex JSON schemas declaratively

```python
schema = create_parameter_schema(
    properties={
        "query": {"type": "string", "description": "Search query"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
    },
    required=["query"]
)
```

**Benefit:** Readable schema definition, type safety

---

### 8.8 Chain of Responsibility (Classification Fallback)

**Pattern Name:** Chain of Responsibility

**Used In:** IntentClassifier.classify()

**Purpose:** Try multiple classification methods in sequence

```python
# Try SetFit first
if self.method == "setfit":
    try:
        return self._classify_with_setfit(query)
    except:
        pass  # Fall through

# Try embedding
try:
    return self._classify_with_embeddings(query)
except:
    pass  # Fall through

# Try rule-based
return self._classify_rule_based(query)
```

**Benefit:** Graceful degradation, fault tolerance

---

## Summary

| Design Pattern | Location | Purpose |
|----------------|----------|---------|
| **Singleton** | CoordinatorAgent, IntentClassifier | Single instance of expensive resources |
| **State Machine** | LangGraph graph definition | Multi-agent orchestration |
| **Strategy** | Intent classification methods | Runtime algorithm switching |
| **Factory** | create_initial_state() | Encapsulate object creation |
| **Decorator** | @retry_on_failure | Add cross-cutting concerns |
| **Observer** | Stream phase events | Real-time event emission |
| **Builder** | Tool schema builders | Complex object construction |
| **Chain of Responsibility** | Classification fallback | Sequential handler chain |

---

## Key Architectural Principles

1. **Type Safety:** Heavy use of Pydantic v2 for runtime validation
2. **Composability:** Each agent is independent and composable
3. **Observability:** Comprehensive logging and phase events
4. **Resilience:** Retry logic, graceful degradation, error handling
5. **Performance:** Caching (LRU, embeddings, graph), async I/O
6. **Security:** Sandboxed tool execution, parameter validation
7. **Extensibility:** Strategy pattern for classification, pluggable components

---

## Integration with Claude AI

When extending these patterns in Claude AI:

1. **State Management:** Always preserve AgentState schema for type consistency
2. **Coordinator API:** Use get_coordinator() singleton for query processing
3. **Intent Classification:** Use classify_intent() for adaptive retrieval weights
4. **Tool Execution:** Use ToolExecutor.execute() for secure command execution
5. **Streaming:** Implement SSE handlers for real-time phase events
6. **Error Handling:** Follow retry and fallback patterns
7. **Logging:** Use structlog for structured observability

---

**Generated:** 2026-01-13

**Related Documentation:**
- [Architecture Overview](../ARCHITECTURE.md)
- [ADR-040: RELATES_TO Semantic Relationships](../adr/ADR-040-semantic-relationships.md)
- [ADR-042: Intent Classification & 4-Way Hybrid RRF](../adr/ADR-042-intent-rrf.md)
- [Sprint Planning](../sprints/)
