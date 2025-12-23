"""Research API Endpoints.

Sprint 62 Feature 62.10: Research Endpoint Backend (6 SP)

This module provides research endpoints for multi-step research queries
with LangGraph workflow orchestration and SSE streaming support.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.agents.research.graph import ResearchState, create_research_graph
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

    Args:
        query: Research question
        namespace: Namespace to search in
        max_iterations: Maximum iterations

    Yields:
        SSE-formatted progress events
    """
    try:
        # Create initial state
        initial_state: ResearchState = {
            "query": query,
            "namespace": namespace,
            "research_plan": [],
            "search_results": [],
            "synthesis": "",
            "iteration": 0,
            "max_iterations": max_iterations,
            "quality_metrics": {},
            "should_continue": True,
        }

        # Create graph
        graph = create_research_graph()

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
                    # Emit progress for each phase
                    if node_name == "plan":
                        progress = ResearchProgress(
                            phase="plan",
                            message="Creating research plan",
                            iteration=iteration_count,
                            metadata={"num_queries": len(state_update.get("research_plan", []))},
                        )
                        yield f"data: {progress.model_dump_json()}\n\n"

                    elif node_name == "search":
                        iteration_count = state_update.get("iteration", iteration_count)
                        progress = ResearchProgress(
                            phase="search",
                            message=f"Executing searches (iteration {iteration_count})",
                            iteration=iteration_count,
                            metadata={"num_queries": len(state_update.get("research_plan", []))},
                        )
                        yield f"data: {progress.model_dump_json()}\n\n"

                    elif node_name == "evaluate":
                        metrics = state_update.get("quality_metrics", {})
                        progress = ResearchProgress(
                            phase="evaluate",
                            message="Evaluating search results",
                            iteration=iteration_count,
                            metadata=metrics,
                        )
                        yield f"data: {progress.model_dump_json()}\n\n"

                    elif node_name == "synthesize":
                        progress = ResearchProgress(
                            phase="synthesize",
                            message="Synthesizing final answer",
                            iteration=iteration_count,
                            metadata={"num_results": len(state_update.get("search_results", []))},
                        )
                        yield f"data: {progress.model_dump_json()}\n\n"

                    # Update tracking
                    last_state.update(state_update)

            # Allow other tasks to run
            await asyncio.sleep(0)

        # Final state is the last_state
        final_state = last_state

        # Extract sources from search results
        sources = _extract_sources(final_state.get("search_results", []))

        # Create final response
        response = ResearchQueryResponse(
            query=query,
            synthesis=final_state.get("synthesis", ""),
            sources=sources,
            iterations=final_state.get("iteration", 0),
            quality_metrics=final_state.get("quality_metrics", {}),
            research_plan=final_state.get("research_plan", []),
        )

        # Send final result
        yield f"data: {response.model_dump_json()}\n\n"

        # Send completion event
        yield "data: [DONE]\n\n"

    except asyncio.TimeoutError:
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

            # Execute research workflow
            from src.agents.research.graph import run_research

            final_state = await asyncio.wait_for(
                run_research(
                    query=request.query,
                    max_iterations=request.max_iterations,
                    namespace=request.namespace,
                ),
                timeout=RESEARCH_TIMEOUT_SECONDS,
            )

            # Extract sources
            sources = _extract_sources(final_state.get("search_results", []))

            logger.info(
                "research_query_complete",
                query=request.query,
                iterations=final_state.get("iteration", 0),
                num_sources=len(sources),
                response_format=request.response_format,
            )

            # Sprint 63 Feature 63.4: Return structured format if requested
            if request.response_format == "structured":
                from src.api.services.response_formatter import (
                    format_research_response_structured,
                )

                structured_response = format_research_response_structured(
                    query=request.query,
                    synthesis=final_state.get("synthesis", ""),
                    sources=sources,
                    research_plan=final_state.get("research_plan", []),
                    iterations=final_state.get("iteration", 0),
                    quality_metrics=final_state.get("quality_metrics", {}),
                    start_time=start_time,
                )
                return structured_response.model_dump()

            # Create natural format response (default)
            response = ResearchQueryResponse(
                query=request.query,
                synthesis=final_state.get("synthesis", ""),
                sources=sources,
                iterations=final_state.get("iteration", 0),
                quality_metrics=final_state.get("quality_metrics", {}),
                research_plan=final_state.get("research_plan", []),
            )

            return response

        except asyncio.TimeoutError:
            logger.error("research_timeout", query=request.query)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Research timeout after {RESEARCH_TIMEOUT_SECONDS}s",
            )

    except AegisRAGException as e:
        logger.error("research_aegis_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        logger.error("research_query_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research failed: {str(e)}",
        )


@router.get("/health")
async def research_health() -> dict[str, str]:
    """Health check for research endpoint.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "research"}
