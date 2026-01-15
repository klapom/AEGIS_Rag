"""Research API Endpoints.

Sprint 62 Feature 62.10: Research Endpoint Backend (6 SP)
Sprint 70 Feature 70.4: Deep Research Supervisor Graph (5 SP)

This module provides research endpoints for multi-step research queries
with LangGraph workflow orchestration and SSE streaming support.

Updated in Sprint 70 to use new Supervisor Pattern with component reuse.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.agents.research.research_graph import (
    ResearchSupervisorState,
    create_initial_research_state,
    get_research_graph,
    get_research_graph_with_config,  # Sprint 70 Feature 70.7
)
from src.api.models.research import (
    ResearchProgress,
    ResearchQueryRequest,
    ResearchQueryResponse,
    Source,
)
from src.core.exceptions import AegisRAGException

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/research", tags=["research"])

# Timeout constants
RESEARCH_TIMEOUT_SECONDS = 180  # 3 minutes for multi-step research
PHASE_TIMEOUT_SECONDS = 60  # Individual phase timeout


async def _stream_research_progress(
    query: str,
    namespace: str,
    max_iterations: int,
) -> AsyncGenerator[str, None]:
    """Stream research progress as SSE events.

    Sprint 70: Updated to use new Supervisor Pattern graph.

    Args:
        query: Research question
        namespace: Namespace to search in
        max_iterations: Maximum iterations

    Yields:
        SSE-formatted progress events
    """
    try:
        # Create initial state (Sprint 70: New state structure)
        initial_state = create_initial_research_state(
            query=query,
            max_iterations=max_iterations,
            namespace=namespace,
        )

        # Create graph (Sprint 70 Feature 70.7: Load tools config from Redis)
        graph = await get_research_graph_with_config()

        # Send initial progress
        progress = ResearchProgress(
            phase="start",
            message="Starting research workflow",
            iteration=0,
            metadata={"query": query, "namespace": namespace},
        )
        yield f"data: {progress.model_dump_json()}\n\n"

        # Track state changes to emit progress
        last_state = initial_state.copy()
        iteration_count = 0  # Initialize iteration counter

        async for event in graph.astream(initial_state):
            # Parse event to detect phase changes
            if isinstance(event, dict):
                # Extract node name from event
                node_name = None
                state_update = None

                for key, value in event.items():
                    if isinstance(value, dict):
                        node_name = key
                        state_update = value
                        break

                if node_name and state_update:
                    # Emit progress for each phase (Sprint 70: Updated node names)
                    # Sprint 92: Enhanced metadata for detailed UI feedback
                    if node_name == "planner":
                        sub_queries = state_update.get("sub_queries", [])
                        progress = ResearchProgress(
                            phase="plan",
                            message="Creating research plan",
                            iteration=iteration_count,
                            metadata={
                                "num_queries": len(sub_queries),
                                # Sprint 92: Send actual sub-queries for display
                                "plan_steps": sub_queries,
                            },
                        )
                        yield f"data: {progress.model_dump_json()}\n\n"

                    elif node_name == "searcher":
                        iteration_count = state_update.get("iteration", iteration_count)
                        all_contexts = state_update.get("all_contexts", [])

                        # Sprint 92: Group contexts by query_index for per-query counts
                        contexts_by_query: dict[int, int] = {}
                        for ctx in all_contexts:
                            query_idx = ctx.get("query_index", 0)
                            contexts_by_query[query_idx] = contexts_by_query.get(query_idx, 0) + 1

                        progress = ResearchProgress(
                            phase="search",
                            message=f"Executing searches (iteration {iteration_count})",
                            iteration=iteration_count,
                            metadata={
                                "num_queries": len(state_update.get("sub_queries", [])),
                                "num_contexts": len(all_contexts),
                                # Sprint 92: Per-query chunk counts
                                "contexts_per_query": contexts_by_query,
                                "sources_found": len(all_contexts),
                            },
                        )
                        yield f"data: {progress.model_dump_json()}\n\n"

                    elif node_name == "supervisor":
                        all_contexts = state_update.get("all_contexts", [])

                        # Sprint 92: Calculate quality metrics for display
                        num_contexts = len(all_contexts)
                        avg_score = 0.0
                        if num_contexts > 0:
                            avg_score = sum(ctx.get("score", 0.0) for ctx in all_contexts) / num_contexts

                        # Determine quality level
                        if num_contexts >= 10 and avg_score > 0.7:
                            quality_label = "excellent"
                        elif num_contexts >= 5 and avg_score > 0.5:
                            quality_label = "good"
                        elif num_contexts >= 3:
                            quality_label = "fair"
                        else:
                            quality_label = "poor"

                        progress = ResearchProgress(
                            phase="evaluate",
                            message="Evaluating search quality",
                            iteration=iteration_count,
                            metadata={
                                "should_continue": state_update.get("should_continue", False),
                                "num_contexts": num_contexts,
                                # Sprint 92: Enhanced quality metrics
                                "num_results": num_contexts,
                                "avg_score": round(avg_score, 3),
                                "quality_score": avg_score,
                                "quality_label": quality_label,
                            },
                        )
                        yield f"data: {progress.model_dump_json()}\n\n"

                    elif node_name == "synthesizer":
                        all_contexts = state_update.get("all_contexts", [])
                        metadata_update = state_update.get("metadata", {})

                        # Sprint 92: Show which contexts are being used
                        # Top contexts by score for synthesis
                        top_contexts = sorted(
                            all_contexts,
                            key=lambda c: c.get("score", 0.0),
                            reverse=True
                        )[:10]

                        context_summaries = []
                        for i, ctx in enumerate(top_contexts[:5], 1):
                            text = ctx.get("text", "")[:80] + "..." if len(ctx.get("text", "")) > 80 else ctx.get("text", "")
                            source = ctx.get("source", ctx.get("source_channel", "unknown"))
                            context_summaries.append(f"[{i}] {source}: {text}")

                        progress = ResearchProgress(
                            phase="synthesize",
                            message="Synthesizing final answer",
                            iteration=iteration_count,
                            metadata={
                                "num_contexts": len(all_contexts),
                                # Sprint 92: Show contexts being synthesized
                                "num_sources_cited": metadata_update.get("num_sources_cited", len(top_contexts)),
                                "top_sources": context_summaries,
                            },
                        )
                        yield f"data: {progress.model_dump_json()}\n\n"

                    # Update tracking
                    last_state.update(state_update)

            # Allow other tasks to run
            await asyncio.sleep(0)

        # Final state is the last_state
        final_state = last_state

        # Extract sources from contexts (Sprint 70: Changed from search_results to all_contexts)
        sources = _extract_sources(final_state.get("all_contexts", []))

        # Create final response (Sprint 70: Updated field names)
        response = ResearchQueryResponse(
            query=query,
            synthesis=final_state.get("synthesis", ""),
            sources=sources,
            iterations=final_state.get("iteration", 0),
            quality_metrics=final_state.get("metadata", {}).get("quality_metrics", {}),
            research_plan=final_state.get("sub_queries", []),
        )

        # Send final result
        yield f"data: {response.model_dump_json()}\n\n"

        # Send completion event
        yield "data: [DONE]\n\n"

    except TimeoutError:
        logger.error("research_timeout", query=query)
        error_msg = {"error": "Research timeout", "query": query}
        yield f"data: {json.dumps(error_msg)}\n\n"

    except Exception as e:
        logger.error("research_stream_error", error=str(e), exc_info=True)
        error_msg = {"error": str(e), "query": query}
        yield f"data: {json.dumps(error_msg)}\n\n"


def _extract_sources(search_results: list[dict[str, Any]]) -> list[Source]:
    """Extract and format sources from search results.

    Args:
        search_results: Raw search results

    Returns:
        List of formatted Source objects
    """
    sources = []

    for result in search_results:
        source = Source(
            text=result.get("text", ""),
            score=result.get("score", 0.0),
            source_type=result.get("source", "unknown"),
            metadata=result.get("metadata", {}),
            entities=result.get("entities", []),
            relationships=result.get("relationships", []),
        )
        sources.append(source)

    # Sort by score and deduplicate
    sources = sorted(sources, key=lambda s: s.score, reverse=True)

    # Take top 20 sources
    return sources[:20]


@router.post("/query", response_model=ResearchQueryResponse)
async def research_query(
    request: ResearchQueryRequest,
) -> ResearchQueryResponse | StreamingResponse:
    """Execute a research query with multi-step workflow.

    Sprint 62 Feature 62.10: Research Endpoint Backend

    This endpoint executes a multi-step research workflow:
    1. Plan: Decompose query into search strategies
    2. Search: Execute searches across vector/graph stores
    3. Evaluate: Assess result quality and decide to continue
    4. Synthesize: Generate comprehensive research answer

    Args:
        request: Research query request

    Returns:
        Research response with synthesis and sources (or SSE stream)

    Raises:
        HTTPException: If research fails

    Examples:
        >>> # Non-streaming request
        >>> request = ResearchQueryRequest(
        ...     query="What is machine learning?",
        ...     namespace="ml_docs",
        ...     stream=False
        ... )
        >>> response = await research_query(request)
        >>> response.synthesis
        "Machine learning is..."

        >>> # Streaming request
        >>> request = ResearchQueryRequest(
        ...     query="What is deep learning?",
        ...     stream=True
        ... )
        >>> # Returns StreamingResponse with SSE events
    """
    logger.info(
        "research_query_start",
        query=request.query,
        namespace=request.namespace,
        max_iterations=request.max_iterations,
        stream=request.stream,
    )

    try:
        # Streaming response
        if request.stream:
            return StreamingResponse(
                _stream_research_progress(
                    query=request.query,
                    namespace=request.namespace,
                    max_iterations=request.max_iterations,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # Non-streaming response
        try:
            # Track start time for latency
            import time

            start_time = time.time()

            # Execute research workflow (Sprint 70 Feature 70.7: Load tools config)
            graph = await get_research_graph_with_config()
            initial_state = create_initial_research_state(
                query=request.query,
                max_iterations=request.max_iterations,
                namespace=request.namespace,
            )

            final_state = await asyncio.wait_for(
                graph.ainvoke(initial_state),
                timeout=RESEARCH_TIMEOUT_SECONDS,
            )

            # Extract sources (Sprint 70: Changed from search_results to all_contexts)
            sources = _extract_sources(final_state.get("all_contexts", []))

            logger.info(
                "research_query_complete",
                query=request.query,
                iterations=final_state.get("iteration", 0),
                num_sources=len(sources),
                response_format=request.response_format,
            )

            # Sprint 63 Feature 63.4: Return structured format if requested
            # Sprint 70: Updated field names
            if request.response_format == "structured":
                from src.api.services.response_formatter import (
                    format_research_response_structured,
                )

                structured_response = format_research_response_structured(
                    query=request.query,
                    synthesis=final_state.get("synthesis", ""),
                    sources=sources,
                    research_plan=final_state.get("sub_queries", []),
                    iterations=final_state.get("iteration", 0),
                    quality_metrics=final_state.get("metadata", {}).get(
                        "quality_metrics", {}
                    ),
                    start_time=start_time,
                )
                return structured_response.model_dump()

            # Create natural format response (default) (Sprint 70: Updated field names)
            response = ResearchQueryResponse(
                query=request.query,
                synthesis=final_state.get("synthesis", ""),
                sources=sources,
                iterations=final_state.get("iteration", 0),
                quality_metrics=final_state.get("metadata", {}).get("quality_metrics", {}),
                research_plan=final_state.get("sub_queries", []),
            )

            return response

        except TimeoutError as err:
            logger.error("research_timeout", query=request.query)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Research timeout after {RESEARCH_TIMEOUT_SECONDS}s",
            ) from err

    except AegisRAGException as e:
        logger.error("research_aegis_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.error("research_query_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research failed: {str(e)}",
        ) from e


@router.get("/health")
async def research_health() -> dict[str, str]:
    """Health check for research endpoint.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "research"}
