"""Deep Research API Endpoints.

Sprint 116.10: Deep Research Multi-Step (13 SP)

This module provides dedicated deep research endpoints with enhanced
tracking, intermediate results, and export functionality.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.agents.research.research_graph import (
    create_initial_research_state,
    get_research_graph_with_config,
)
from src.agents.research.state import ExecutionStep
from src.api.models.deep_research import (
    CancelResearchRequest,
    DeepResearchRequest,
    DeepResearchResponse,
    DeepResearchStatusResponse,
    ExecutionStepModel,
    ExportResearchRequest,
    IntermediateAnswer,
)
from src.api.models.research import Source
from src.core.exceptions import AegisRAGException

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/research/deep", tags=["deep_research"])

# In-memory storage for active research sessions
# TODO: Move to Redis for production (Sprint 117+)
_active_research: dict[str, dict[str, Any]] = {}
_research_tasks: dict[str, asyncio.Task] = {}


def _create_execution_step_model(step: ExecutionStep) -> ExecutionStepModel:
    """Convert internal ExecutionStep to API model.

    Args:
        step: Internal execution step

    Returns:
        API execution step model
    """
    return ExecutionStepModel(
        step_name=step.get("step_name", ""),
        started_at=datetime.fromisoformat(step.get("started_at", datetime.utcnow().isoformat())),
        completed_at=(
            datetime.fromisoformat(step["completed_at"]) if step.get("completed_at") else None
        ),
        duration_ms=step.get("duration_ms"),
        status=step.get("status", "running"),
        result=step.get("result", {}),
        error=step.get("error"),
    )


def _extract_intermediate_answers(
    sub_questions: list[str],
    all_contexts: list[dict[str, Any]],
    intermediate_answers: dict[str, str] | None,
) -> list[IntermediateAnswer]:
    """Extract intermediate answers for sub-questions.

    Args:
        sub_questions: List of sub-questions
        all_contexts: All retrieved contexts
        intermediate_answers: Map of sub-question to answer

    Returns:
        List of intermediate answers
    """
    results = []

    if not intermediate_answers:
        intermediate_answers = {}

    for sub_q in sub_questions:
        # Get contexts for this sub-question
        contexts = [ctx for ctx in all_contexts if ctx.get("research_query") == sub_q]

        # Get answer if available
        answer = intermediate_answers.get(sub_q, "")

        # Extract sources
        sources = []
        for ctx in contexts[:5]:  # Top 5 sources
            source = Source(
                text=ctx.get("text", ""),
                score=ctx.get("score", 0.0),
                source_type=ctx.get("source", "unknown"),
                metadata=ctx.get("metadata", {}),
                entities=ctx.get("entities", []),
                relationships=ctx.get("relationships", []),
            )
            sources.append(source)

        # Calculate confidence based on number of contexts and scores
        confidence = 0.0
        if contexts:
            avg_score = sum(ctx.get("score", 0.0) for ctx in contexts) / len(contexts)
            coverage = min(len(contexts) / 5.0, 1.0)
            confidence = avg_score * 0.7 + coverage * 0.3

        results.append(
            IntermediateAnswer(
                sub_question=sub_q,
                answer=answer if answer else f"Searching... ({len(contexts)} contexts found)",
                contexts_count=len(contexts),
                sources=sources,
                confidence=confidence,
            )
        )

    return results


async def _execute_deep_research(
    research_id: str,
    request: DeepResearchRequest,
) -> None:
    """Execute deep research workflow in background.

    Args:
        research_id: Unique research ID
        request: Deep research request
    """
    logger.info("deep_research_started", research_id=research_id, query=request.query)

    start_time = datetime.utcnow()

    try:
        # Create initial state
        initial_state = create_initial_research_state(
            query=request.query,
            max_iterations=request.max_iterations,
            namespace=request.namespace,
        )

        # Add Sprint 116.10 fields
        initial_state["current_step"] = "pending"
        initial_state["execution_steps"] = []
        initial_state["intermediate_answers"] = {}

        # Store initial state
        _active_research[research_id] = {
            "request": request,
            "state": initial_state,
            "status": "pending",
            "created_at": start_time,
        }

        # Get research graph
        graph = await get_research_graph_with_config()

        # Execute with timeout
        final_state = await asyncio.wait_for(
            graph.ainvoke(initial_state),
            timeout=request.timeout_seconds,
        )

        # Calculate total time
        end_time = datetime.utcnow()
        total_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Extract sources
        sources = []
        for ctx in final_state.get("all_contexts", []):
            source = Source(
                text=ctx.get("text", ""),
                score=ctx.get("score", 0.0),
                source_type=ctx.get("source", "unknown"),
                metadata=ctx.get("metadata", {}),
                entities=ctx.get("entities", []),
                relationships=ctx.get("relationships", []),
            )
            sources.append(source)

        # Sort by score and take top 20
        sources = sorted(sources, key=lambda s: s.score, reverse=True)[:20]

        # Extract intermediate answers
        intermediate_answers_list = _extract_intermediate_answers(
            sub_questions=final_state.get("sub_queries", []),
            all_contexts=final_state.get("all_contexts", []),
            intermediate_answers=final_state.get("intermediate_answers"),
        )

        # Update state with final results
        _active_research[research_id].update(
            {
                "state": final_state,
                "status": "complete",
                "completed_at": end_time,
                "total_time_ms": total_time_ms,
                "sources": sources,
                "intermediate_answers": intermediate_answers_list,
            }
        )

        logger.info(
            "deep_research_completed",
            research_id=research_id,
            total_time_ms=total_time_ms,
            num_sources=len(sources),
        )

    except asyncio.TimeoutError:
        logger.error("deep_research_timeout", research_id=research_id)
        _active_research[research_id].update(
            {
                "status": "error",
                "error": f"Research timeout after {request.timeout_seconds}s",
            }
        )

    except Exception as e:
        logger.error("deep_research_error", research_id=research_id, error=str(e), exc_info=True)
        _active_research[research_id].update(
            {
                "status": "error",
                "error": str(e),
            }
        )


@router.post("", response_model=DeepResearchResponse)
async def start_deep_research(
    request: DeepResearchRequest,
) -> DeepResearchResponse:
    """Start a deep research query with multi-step workflow.

    Sprint 116.10 Feature: Enhanced deep research with intermediate results.

    Args:
        request: Deep research request

    Returns:
        Deep research response with research ID

    Raises:
        HTTPException: If research fails to start

    Examples:
        >>> request = DeepResearchRequest(
        ...     query="What is machine learning?",
        ...     namespace="ml_docs"
        ... )
        >>> response = await start_deep_research(request)
        >>> response.status
        "pending"
    """
    logger.info("start_deep_research", query=request.query, namespace=request.namespace)

    try:
        # Generate unique research ID
        research_id = f"research_{uuid.uuid4().hex[:12]}"

        # Start background task
        task = asyncio.create_task(_execute_deep_research(research_id, request))
        _research_tasks[research_id] = task

        # Return initial response
        return DeepResearchResponse(
            id=research_id,
            query=request.query,
            status="pending",
            sub_questions=[],
            intermediate_answers=[],
            final_answer="",
            sources=[],
            execution_steps=[],
            total_time_ms=0,
            created_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error("start_deep_research_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start deep research: {str(e)}",
        ) from e


@router.get("/{research_id}/status", response_model=DeepResearchStatusResponse)
async def get_research_status(research_id: str) -> DeepResearchStatusResponse:
    """Get status of ongoing deep research.

    Args:
        research_id: Unique research ID

    Returns:
        Current research status

    Raises:
        HTTPException: If research not found
    """
    logger.debug("get_research_status", research_id=research_id)

    if research_id not in _active_research:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research {research_id} not found",
        )

    research_data = _active_research[research_id]
    state = research_data.get("state", {})
    status_val = research_data.get("status", "pending")

    # Calculate progress percentage
    current_step = state.get("current_step", "pending")
    step_map = {
        "pending": 0,
        "decomposing": 20,
        "retrieving": 40,
        "analyzing": 60,
        "synthesizing": 80,
        "complete": 100,
        "error": 0,
    }
    progress_percent = step_map.get(current_step, 0)

    # Estimate time remaining (simple heuristic)
    estimated_time_remaining_ms = None
    if status_val not in ["complete", "error", "cancelled"]:
        created_at = research_data.get("created_at", datetime.utcnow())
        elapsed_ms = int((datetime.utcnow() - created_at).total_seconds() * 1000)

        if progress_percent > 0:
            total_estimated = elapsed_ms / (progress_percent / 100.0)
            estimated_time_remaining_ms = int(total_estimated - elapsed_ms)

    # Convert execution steps to models
    execution_steps = []
    for step in state.get("execution_steps", []):
        execution_steps.append(_create_execution_step_model(step))

    return DeepResearchStatusResponse(
        id=research_id,
        status=status_val,
        current_step=current_step,
        progress_percent=progress_percent,
        estimated_time_remaining_ms=estimated_time_remaining_ms,
        execution_steps=execution_steps,
    )


@router.get("/{research_id}", response_model=DeepResearchResponse)
async def get_research_result(research_id: str) -> DeepResearchResponse:
    """Get full deep research result.

    Args:
        research_id: Unique research ID

    Returns:
        Complete research response

    Raises:
        HTTPException: If research not found
    """
    logger.debug("get_research_result", research_id=research_id)

    if research_id not in _active_research:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research {research_id} not found",
        )

    research_data = _active_research[research_id]
    state = research_data.get("state", {})
    request = research_data["request"]

    # Convert execution steps
    execution_steps = []
    for step in state.get("execution_steps", []):
        execution_steps.append(_create_execution_step_model(step))

    return DeepResearchResponse(
        id=research_id,
        query=request.query,
        status=research_data.get("status", "pending"),
        sub_questions=state.get("sub_queries", []),
        intermediate_answers=research_data.get("intermediate_answers", []),
        final_answer=state.get("synthesis", ""),
        sources=research_data.get("sources", []),
        execution_steps=execution_steps,
        total_time_ms=research_data.get("total_time_ms", 0),
        created_at=research_data.get("created_at", datetime.utcnow()),
        completed_at=research_data.get("completed_at"),
        error=research_data.get("error"),
    )


@router.post("/{research_id}/cancel")
async def cancel_research(
    research_id: str,
    request: CancelResearchRequest | None = None,
) -> dict[str, str]:
    """Cancel ongoing deep research.

    Args:
        research_id: Unique research ID
        request: Optional cancellation request with reason

    Returns:
        Cancellation status

    Raises:
        HTTPException: If research not found
    """
    logger.info(
        "cancel_research", research_id=research_id, reason=request.reason if request else None
    )

    if research_id not in _active_research:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research {research_id} not found",
        )

    # Cancel background task
    if research_id in _research_tasks:
        task = _research_tasks[research_id]
        task.cancel()
        del _research_tasks[research_id]

    # Update status
    _active_research[research_id].update(
        {
            "status": "cancelled",
            "error": (
                f"Cancelled by user: {request.reason}"
                if request and request.reason
                else "Cancelled by user"
            ),
        }
    )

    return {"status": "cancelled", "message": "Research cancelled successfully"}


@router.get("/{research_id}/export")
async def export_research(
    research_id: str,
    format: str = "markdown",
    include_sources: bool = True,
    include_intermediate: bool = False,
) -> StreamingResponse:
    """Export research results as PDF or markdown.

    Args:
        research_id: Unique research ID
        format: Export format (pdf or markdown)
        include_sources: Include source citations
        include_intermediate: Include intermediate answers

    Returns:
        StreamingResponse with exported file

    Raises:
        HTTPException: If research not found or export fails
    """
    logger.info(
        "export_research",
        research_id=research_id,
        format=format,
        include_sources=include_sources,
    )

    if research_id not in _active_research:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research {research_id} not found",
        )

    research_data = _active_research[research_id]
    state = research_data.get("state", {})
    request = research_data["request"]

    if format == "markdown":
        # Generate markdown
        markdown_lines = [
            f"# Deep Research: {request.query}",
            "",
            f"**Research ID:** `{research_id}`",
            f"**Status:** {research_data.get('status', 'unknown')}",
            f"**Created:** {research_data.get('created_at', 'N/A')}",
            "",
            "## Final Answer",
            "",
            state.get("synthesis", "No answer available yet."),
            "",
        ]

        # Add intermediate answers if requested
        if include_intermediate and research_data.get("intermediate_answers"):
            markdown_lines.extend(
                [
                    "## Intermediate Findings",
                    "",
                ]
            )

            for ia in research_data["intermediate_answers"]:
                markdown_lines.extend(
                    [
                        f"### {ia.sub_question}",
                        "",
                        f"**Confidence:** {ia.confidence:.2%}",
                        f"**Contexts:** {ia.contexts_count}",
                        "",
                        ia.answer,
                        "",
                    ]
                )

        # Add sources if requested
        if include_sources and research_data.get("sources"):
            markdown_lines.extend(
                [
                    "## Sources",
                    "",
                ]
            )

            for idx, source in enumerate(research_data["sources"], 1):
                markdown_lines.extend(
                    [
                        f"**[{idx}]** _{source.source_type}_ (Score: {source.score:.3f})",
                        "",
                        source.text[:500] + ("..." if len(source.text) > 500 else ""),
                        "",
                    ]
                )

        markdown_content = "\n".join(markdown_lines)

        return StreamingResponse(
            iter([markdown_content.encode()]),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=research_{research_id}.md"},
        )

    elif format == "pdf":
        # TODO: Implement PDF export (Sprint 117+)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF export not yet implemented",
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {format}. Use 'markdown' or 'pdf'",
        )


@router.get("/health")
async def deep_research_health() -> dict[str, str]:
    """Health check for deep research endpoint.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "deep_research"}
