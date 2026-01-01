"""Coordinator Agent - Main Orchestrator for Multi-Agent RAG System.

The Coordinator is the entry point for all queries and manages the entire
multi-agent workflow. It initializes state, invokes the LangGraph, and
manages conversation persistence.

Sprint 4 Feature 4.4: Coordinator Agent with State Persistence
Sprint 48 Feature 48.2: CoordinatorAgent Streaming Method (13 SP)
Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any

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


def _extract_channel_samples(
    retrieved_contexts: list[dict[str, Any]],
    query: str,
    max_per_channel: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """Extract sample results from each channel for display.

    Groups retrieved contexts by source_channel and returns top samples
    from each channel with truncated text for UI display.

    Sprint 52: Added query parameter to extract BM25 keywords.
    Sprint 52: Added matched_entities for graph channels.

    Args:
        retrieved_contexts: List of retrieved context dicts
        query: Original user query (for BM25 keyword extraction)
        max_per_channel: Maximum samples per channel (default: 3)

    Returns:
        Dict mapping channel names to lists of sample results
    """
    channel_samples: dict[str, list[dict[str, Any]]] = {
        "vector": [],
        "bm25": [],
        "graph_local": [],
        "graph_global": [],
    }

    # Extract BM25 keywords from query (same logic as four_way_hybrid_search.py)
    bm25_keywords = query.lower().split() if query else []

    for ctx in retrieved_contexts:
        if not isinstance(ctx, dict):
            continue

        # Get source channel (might be in different fields)
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
            continue  # Skip unknown channels

        # Only add if under limit
        if len(channel_samples[channel]) >= max_per_channel:
            continue

        # Extract text (truncate for display)
        text = ctx.get("text") or ctx.get("content") or ""
        if len(text) > 200:
            text = text[:200] + "..."

        # Create sample entry with base fields
        sample: dict[str, Any] = {
            "text": text,
            "score": ctx.get("score") or ctx.get("rrf_score") or 0,
            "document_id": ctx.get("document_id") or ctx.get("doc_id") or "",
            "title": ctx.get("title") or ctx.get("document_title") or "",
        }

        # Add channel-specific metadata
        if channel == "bm25":
            # BM25: Add search keywords used
            sample["keywords"] = bm25_keywords
        elif channel == "graph_local":
            # Graph Local: Add matched entities from result
            matched_entities = ctx.get("matched_entities", [])
            sample["matched_entities"] = matched_entities
        elif channel == "graph_global":
            # Graph Global: Add community ID and try to get entities
            sample["community_id"] = ctx.get("community_id")
            # Graph global doesn't return matched_entities directly,
            # but we can include any available entity info
            matched_entities = ctx.get("matched_entities", [])
            if matched_entities:
                sample["matched_entities"] = matched_entities

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

    Args:
        raw_weights: Original intent-based weights
        vector_count: Number of vector results
        bm25_count: Number of BM25 results
        graph_local_count: Number of graph local results
        graph_global_count: Number of graph global results

    Returns:
        Dict with effective weights for each channel
    """
    if not raw_weights:
        # Default equal weights if no raw weights
        return {"vector": 0.25, "bm25": 0.25, "local": 0.25, "global_": 0.25}

    # Map counts to channels
    counts = {
        "vector": vector_count,
        "bm25": bm25_count,
        "local": graph_local_count,
        "global_": graph_global_count,
    }

    # Calculate total weight of channels with results
    active_weight = 0.0
    for channel, count in counts.items():
        if count > 0:
            weight_key = channel if channel in raw_weights else channel.rstrip("_")
            active_weight += raw_weights.get(weight_key, 0) or raw_weights.get(channel, 0)

    # If no channels have results, return zeros
    if active_weight == 0:
        return {"vector": 0.0, "bm25": 0.0, "local": 0.0, "global_": 0.0}

    # Calculate effective weights (redistribute to active channels)
    effective = {}
    for channel, count in counts.items():
        weight_key = channel if channel in raw_weights else channel.rstrip("_")
        raw_weight = raw_weights.get(weight_key, 0) or raw_weights.get(channel, 0)

        if count > 0 and raw_weight > 0:
            # Normalize: channel's share of active weight
            effective[channel] = raw_weight / active_weight
        else:
            effective[channel] = 0.0

    return effective


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

        **Sprint 70 Feature 70.7: Lazy graph compilation with tools config**

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

        # Sprint 70 Feature 70.7: Lazy graph compilation
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

    async def _get_or_compile_graph(self) -> Any:
        """Get compiled graph, compiling if necessary.

        **Sprint 70 Feature 70.7: Lazy compilation with config hot-reload**

        Compiles graph on first call and caches for 60 seconds.
        After cache expires, re-compiles with fresh tools config from Redis.

        Returns:
            Compiled LangGraph instance

        Example:
            >>> coordinator = CoordinatorAgent()
            >>> graph = await coordinator._get_or_compile_graph()
            >>> # Graph compiled with current tools config
        """
        from datetime import datetime

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
        from datetime import timedelta

        from src.agents.graph import compile_graph_with_tools_config

        logger.info("compiling_graph_with_fresh_config", cache_ttl_seconds=self._graph_cache_ttl_seconds)

        self.compiled_graph = await compile_graph_with_tools_config(
            checkpointer=self.checkpointer
        )

        # Set cache expiration
        self._graph_cache_expires_at = now + timedelta(seconds=self._graph_cache_ttl_seconds)

        logger.info("graph_compiled_and_cached", expires_in_seconds=self._graph_cache_ttl_seconds)

        return self.compiled_graph

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
                "data": error_event.model_dump(mode="json"),
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

        # Create initial state with session_id for real-time phase events
        initial_state = create_initial_state(
            query=query,
            intent=intent or "hybrid",
            namespaces=namespaces,
            session_id=session_id,  # Sprint 52: Pass session_id for real-time phase events
        )

        # Create session config
        config = None
        if session_id and self.use_persistence:
            config = create_thread_config(session_id)
            config["recursion_limit"] = self.recursion_limit

        # Stream through LangGraph workflow
        # Sprint 52: Use stream_mode=["custom", "values"] to get:
        # - "custom": Real-time phase events via get_stream_writer() DURING node execution
        # - "values": Full accumulated state AFTER each node completes
        final_state = None
        try:
            # Sprint 70: Get graph with tools config
            graph = await self._get_or_compile_graph()
            async for chunk in graph.astream(
                initial_state, config=config, stream_mode=["custom", "values"]
            ):
                # With combined stream_mode, chunk is tuple: (stream_type, data)
                # Handle varying tuple lengths from different LangGraph versions
                if isinstance(chunk, tuple):
                    if len(chunk) >= 2:
                        stream_type, data = chunk[0], chunk[1]
                    elif len(chunk) == 1:
                        # Single value - skip or log warning
                        logger.warning("unexpected_single_value_chunk", chunk=str(chunk)[:100])
                        continue
                    else:
                        # Empty tuple - skip
                        continue
                else:
                    # Not a tuple - unexpected format
                    logger.warning("unexpected_chunk_format", chunk_type=type(chunk).__name__)
                    continue

                if stream_type == "custom":
                    # Sprint 52: Real-time events from get_stream_writer()
                    # These are emitted DURING node execution, not after!
                    if isinstance(data, dict):
                        event_type = data.get("type")

                        if event_type == "phase_event":
                            phase_data = data.get("data", {})
                            logger.info(
                                "custom_phase_event_received",
                                phase_type=phase_data.get("phase_type"),
                                status=phase_data.get("status"),
                            )
                            # Convert to PhaseEvent and yield immediately
                            if "phase_type" in phase_data:
                                yield PhaseEvent(**phase_data)

                        elif event_type == "token":
                            # Sprint 52: Real-time token streaming from LLM
                            # Yield directly as dict for SSE handler
                            yield {"type": "token", "data": data.get("data", {})}

                        elif event_type == "citation_map":
                            # Sprint 52: Citation map streamed before tokens
                            # Yield directly as dict for SSE handler
                            logger.info(
                                "custom_citation_map_received",
                                citations_count=len(data.get("data", {})),
                            )
                            yield {"type": "citation_map", "data": data.get("data", {})}

                elif stream_type == "values" and isinstance(data, dict):
                    # Full accumulated state after node completion
                    logger.debug(
                        "values_state_received",
                        has_answer="answer" in data,
                        keys=list(data.keys())[:5],
                    )
                    # Keep track of final state
                    final_state = data

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

            # Extract intent metadata from search results (Sprint 42)
            search_metadata = final_state.get("metadata", {}).get("search", {})
            detected_intent = final_state.get("metadata", {}).get("detected_intent")
            intent_confidence = final_state.get("metadata", {}).get("intent_confidence")

            logger.info(
                "coordinator_stream_complete",
                query=query[:100],
                latency_ms=latency_ms,
                answer_length=len(answer) if answer else 0,
                detected_intent=detected_intent,
                intent_confidence=intent_confidence,
            )

            # Sprint 52: Get channel samples from search metadata (extracted BEFORE RRF fusion)
            # This preserves source_channel info that would be lost after fusion
            channel_samples = search_metadata.get("channel_samples")

            if not channel_samples:
                # Fallback: Extract from post-fusion retrieved_contexts (less accurate)
                retrieved_contexts = final_state.get("retrieved_contexts", [])

                # Sprint 52 Debug: Log source_channel distribution
                channel_distribution = {}
                for ctx in retrieved_contexts:
                    if isinstance(ctx, dict):
                        ch = ctx.get("source_channel") or ctx.get("search_type") or "unknown"
                        channel_distribution[ch] = channel_distribution.get(ch, 0) + 1
                logger.info(
                    "channel_samples_fallback_debug",
                    total_contexts=len(retrieved_contexts),
                    channel_distribution=channel_distribution,
                    sample_keys=list(retrieved_contexts[0].keys()) if retrieved_contexts else [],
                )

                channel_samples = _extract_channel_samples(
                    retrieved_contexts, query, max_per_channel=3
                )
            else:
                logger.info(
                    "channel_samples_from_metadata",
                    channels=list(channel_samples.keys()),
                    counts={k: len(v) for k, v in channel_samples.items()},
                )

            # Get raw counts
            vector_count = search_metadata.get("vector_results_count", 0)
            bm25_count = search_metadata.get("bm25_results_count", 0)
            graph_local_count = search_metadata.get("graph_local_results_count", 0)
            graph_global_count = search_metadata.get("graph_global_results_count", 0)
            total_count = vector_count + bm25_count + graph_local_count + graph_global_count

            # Calculate effective weights based on actual results
            # If a channel has 0 results, its effective weight is 0
            raw_weights = search_metadata.get("weights", {})
            effective_weights = _calculate_effective_weights(
                raw_weights, vector_count, bm25_count, graph_local_count, graph_global_count
            )

            # Yield final answer with intent metadata
            # Sprint 52: Include full 4-way search metadata for frontend display
            # IMPORTANT: "answer" must be at top level for process_query_stream check
            yield {
                "answer": answer,
                "citation_map": citation_map,
                # Sprint 42: Include intent classification in answer metadata
                "intent": detected_intent,
                "intent_confidence": intent_confidence,
                "intent_weights": effective_weights,  # Use effective weights
                "metadata": {
                    "total_latency_ms": latency_ms,
                    "session_id": session_id,
                    "search_mode": search_metadata.get("search_mode", "hybrid"),
                    # Sprint 52: 4-way channel results for UI display
                    "four_way_results": {
                        "vector_count": vector_count,
                        "bm25_count": bm25_count,
                        "graph_local_count": graph_local_count,
                        "graph_global_count": graph_global_count,
                        "total_count": total_count,
                    },
                    # Sprint 52: Per-channel result samples for detailed display
                    "channel_samples": channel_samples,
                    "intent_method": search_metadata.get("intent_method"),
                    "intent_latency_ms": search_metadata.get("intent_latency_ms"),
                    # Include raw weights for comparison
                    "raw_weights": raw_weights,
                },
            }

            # Sprint 52 Feature 52.3: Generate follow-up questions asynchronously
            # CRITICAL: This runs AFTER the answer is complete and does NOT block
            if session_id and answer:
                # Extract sources from final state
                sources = []
                retrieved_contexts = final_state.get("retrieved_contexts", [])
                for ctx in retrieved_contexts:
                    if isinstance(ctx, dict):
                        sources.append(ctx)

                # Start async task to generate follow-up questions
                asyncio.create_task(
                    self._generate_followup_async(
                        session_id=session_id,
                        query=query,
                        answer=answer,
                        sources=sources,
                    )
                )

                logger.info(
                    "followup_generation_task_started",
                    session_id=session_id,
                    query_preview=query[:50],
                )

    async def _generate_followup_async(
        self,
        session_id: str,
        query: str,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> None:
        """Generate follow-up questions asynchronously in background.

        Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)

        This method runs as a background task and:
        1. Stores conversation context in Redis
        2. Generates follow-up questions (does NOT block answer display)
        3. Questions are retrieved via GET /chat/sessions/{session_id}/followup-questions

        CRITICAL: This does NOT emit SSE events. Follow-ups are pulled by frontend
        after answer is displayed.

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
                logger.info(
                    "followup_context_stored_for_async",
                    session_id=session_id,
                )

                # Sprint 65 Fix: Actually generate the follow-up questions!
                # Original Sprint 52 implementation only stored context but never generated questions
                try:
                    questions = await generate_followup_questions_async(session_id)
                    if questions:
                        logger.info(
                            "followup_questions_generated_async",
                            session_id=session_id,
                            count=len(questions),
                        )

                        # Sprint 65 Fix: STORE the generated questions in Redis
                        # So frontend can retrieve them without regenerating
                        from src.components.memory import get_redis_memory
                        redis_memory = get_redis_memory()
                        cache_key = f"{session_id}:followup"
                        await redis_memory.store(
                            key=cache_key,
                            value={"questions": questions},
                            namespace="cache",
                            ttl_seconds=300,  # 5 minutes (same as endpoint)
                        )
                        logger.info(
                            "followup_questions_cached",
                            session_id=session_id,
                            count=len(questions),
                        )
                    else:
                        logger.warning(
                            "followup_questions_empty_async",
                            session_id=session_id,
                        )
                except Exception as gen_error:
                    logger.error(
                        "followup_questions_generation_failed_async",
                        session_id=session_id,
                        error=str(gen_error),
                    )
            else:
                logger.warning(
                    "followup_context_storage_failed_async",
                    session_id=session_id,
                )

        except Exception as e:
            logger.error(
                "followup_async_task_failed",
                session_id=session_id,
                error=str(e),
            )

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
