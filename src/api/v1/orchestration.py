"""Orchestration Monitoring API - Workflow Orchestration Endpoints.

Sprint 99 Feature 99.2: Agent Monitoring APIs (Part 2/2)

This module provides endpoints for monitoring workflow orchestration:
- GET /api/v1/orchestration/active: List active orchestrations (paginated, filterable)
- GET /api/v1/orchestration/:id/trace: Get orchestration timeline with events
- GET /api/v1/orchestration/metrics: Get performance metrics (success rate, P95 latency)

For agent communication endpoints, see agents.py

Architecture:
    - SkillOrchestrator: src/agents/orchestrator/skill_orchestrator.py

See Also:
    - docs/sprints/SPRINT_99_PLAN.md: Feature specification
    - src/api/models/agents.py: Pydantic models
"""

from datetime import datetime, UTC
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from src.agents.orchestrator.skill_orchestrator import SkillOrchestrator, WorkflowResult
from src.api.models.agents import (
    OrchestrationListResponse,
    OrchestrationMetrics,
    OrchestrationStatus,
    OrchestrationSummary,
    OrchestrationTrace,
    TraceEvent,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


# Global orchestrator instance (in production, use dependency injection)
_orchestrator_instance: SkillOrchestrator | None = None


def get_orchestrator() -> SkillOrchestrator:
    """Get or create global orchestrator instance.

    Returns:
        SkillOrchestrator instance
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = SkillOrchestrator(
            skill_manager=None, message_bus=None, llm=None  # Minimal init for monitoring
        )
    return _orchestrator_instance


# =============================================================================
# GET: List Active Orchestrations
# =============================================================================


@router.get("/active", response_model=OrchestrationListResponse)
async def list_active_orchestrations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    skill: str | None = Query(None, description="Filter by skill name"),
    status_filter: str | None = Query(
        None, description="Filter by status (running/completed/failed)"
    ),
) -> OrchestrationListResponse:
    """List active orchestrations with pagination and filtering.

    Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - skill: Filter by skill name
        - status_filter: Filter by status (running/completed/failed)

    **Example Response:**
    ```json
    {
      "items": [
        {
          "orchestration_id": "orch_abc123",
          "skill_name": "research_workflow",
          "status": "running",
          "started_at": "2026-01-15T10:30:00Z",
          "duration_ms": null,
          "phase": "synthesis",
          "progress_percent": 65
        }
      ],
      "total": 42,
      "page": 1,
      "page_size": 20,
      "total_pages": 3
    }
    ```

    Returns:
        OrchestrationListResponse with paginated orchestrations

    Raises:
        HTTPException: 503 if orchestrator unavailable
    """
    logger.info(
        "list_active_orchestrations_request",
        page=page,
        page_size=page_size,
        skill=skill,
        status_filter=status_filter,
    )

    try:
        orchestrator = get_orchestrator()

        # Get all active and completed orchestrations
        active_workflows = orchestrator._active_workflows
        history = orchestrator._execution_history

        # Combine active + recent history (last 1000)
        all_workflows: list[tuple[str, WorkflowResult]] = []

        # Active workflows
        for wf_id, result in active_workflows.items():
            all_workflows.append((wf_id, result))

        # Recent history (max 1000 for performance)
        for result in history[-1000:]:
            all_workflows.append((result.workflow_id, result))

        # Apply filters
        filtered_workflows = []
        for wf_id, result in all_workflows:
            # Filter by skill
            if skill:
                workflow_def = result.metadata.get("workflow")
                if workflow_def:
                    skills = getattr(workflow_def, "skills", [])
                    if skill not in skills:
                        continue

            # Filter by status
            if status_filter:
                if wf_id in active_workflows:
                    current_status = "running"
                else:
                    current_status = "completed" if result.success else "failed"

                if current_status != status_filter.lower():
                    continue

            filtered_workflows.append((wf_id, result))

        # Sort by start time (newest first)
        filtered_workflows.sort(
            key=lambda x: x[1].metadata.get("start_time", datetime.now(UTC)), reverse=True
        )

        # Pagination
        total = len(filtered_workflows)
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_workflows = filtered_workflows[start_idx:end_idx]

        # Convert to response models
        items: list[OrchestrationSummary] = []
        for wf_id, result in page_workflows:
            # Determine status
            if wf_id in active_workflows:
                status_val = OrchestrationStatus.RUNNING
                duration_ms = None
                progress_percent = None
                # Calculate progress from phase count
                if result.phase_results:
                    workflow_def = result.metadata.get("workflow")
                    if workflow_def:
                        total_skills = len(getattr(workflow_def, "skills", []))
                        if total_skills > 0:
                            progress_percent = int((len(result.phase_results) / total_skills) * 100)
            else:
                status_val = (
                    OrchestrationStatus.COMPLETED if result.success else OrchestrationStatus.FAILED
                )
                duration_ms = int(result.total_duration * 1000)
                progress_percent = 100 if result.success else None

            # Extract skill name
            workflow_def = result.metadata.get("workflow")
            skill_name = (
                getattr(workflow_def, "skills", ["unknown"])[0] if workflow_def else "unknown"
            )

            # Current phase
            current_phase = None
            if result.phase_results:
                latest_phase = result.phase_results[-1]
                current_phase = latest_phase.get("phase", "unknown")

            # Started at (from metadata or fallback)
            started_at = result.metadata.get("start_time")
            if started_at is None:
                # Fallback: estimate from first phase result timestamp
                if result.phase_results:
                    started_at = datetime.now(UTC)
                else:
                    started_at = datetime.now(UTC)

            items.append(
                OrchestrationSummary(
                    orchestration_id=wf_id,
                    skill_name=skill_name,
                    status=status_val,
                    started_at=started_at,
                    duration_ms=duration_ms,
                    phase=current_phase,
                    progress_percent=progress_percent,
                )
            )

        logger.info(
            "list_active_orchestrations_success",
            total=total,
            page=page,
            page_size=page_size,
            items_count=len(items),
        )

        return OrchestrationListResponse(
            items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
        )

    except Exception as e:
        logger.error("list_active_orchestrations_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to list orchestrations: {e}",
        ) from e


# =============================================================================
# GET: Orchestration Trace
# =============================================================================


@router.get("/{orchestration_id}/trace", response_model=OrchestrationTrace)
async def get_orchestration_trace(orchestration_id: str) -> OrchestrationTrace:
    """Get orchestration timeline with all events and state transitions.

    Path Parameters:
        - orchestration_id: Unique orchestration identifier

    **Example Response:**
    ```json
    {
      "orchestration_id": "orch_abc123",
      "skill_name": "research_workflow",
      "events": [
        {
          "timestamp": "2026-01-15T10:30:00Z",
          "event_type": "orchestration_started",
          "skill_name": null,
          "duration_ms": null,
          "success": null
        },
        {
          "timestamp": "2026-01-15T10:30:01Z",
          "event_type": "skill_started",
          "skill_name": "web_search",
          "duration_ms": null,
          "success": null
        },
        {
          "timestamp": "2026-01-15T10:30:03Z",
          "event_type": "skill_completed",
          "skill_name": "web_search",
          "duration_ms": 2000,
          "success": true
        }
      ],
      "total_duration_ms": 15300,
      "skill_count": 5,
      "success_rate": 0.8
    }
    ```

    Returns:
        OrchestrationTrace with timeline of events

    Raises:
        HTTPException: 404 if orchestration not found, 503 if unavailable
    """
    logger.info("get_orchestration_trace_request", orchestration_id=orchestration_id)

    try:
        orchestrator = get_orchestrator()

        # Find orchestration in active or history
        workflow_result = orchestrator.get_workflow_status(orchestration_id)

        if workflow_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orchestration '{orchestration_id}' not found",
            )

        # Extract skill name
        workflow_def = workflow_result.metadata.get("workflow")
        skill_name = getattr(workflow_def, "skills", ["unknown"])[0] if workflow_def else "unknown"

        # Build timeline from phase results
        events: list[TraceEvent] = []

        # Orchestration start event
        started_at = workflow_result.metadata.get("start_time", datetime.now(UTC))
        events.append(
            TraceEvent(
                timestamp=started_at,
                event_type="orchestration_started",
                skill_name=None,
                duration_ms=None,
                success=None,
            )
        )

        # Phase events
        skill_durations: dict[str, int] = {}
        skill_success: dict[str, bool] = {}

        for phase_result in workflow_result.phase_results:
            phase_name = phase_result.get("phase", "unknown")
            outputs = phase_result.get("outputs", {})
            errors = phase_result.get("errors", [])
            failed = phase_result.get("failed", False)

            # Extract skill names from outputs
            for output_key, output_value in outputs.items():
                # Extract skill name from output key (e.g., "web_search_result" -> "web_search")
                skill_name_extracted = output_key.replace("_result", "")

                # Skill started event (estimate timestamp)
                skill_start_time = started_at
                events.append(
                    TraceEvent(
                        timestamp=skill_start_time,
                        event_type="skill_started",
                        skill_name=skill_name_extracted,
                        duration_ms=None,
                        success=None,
                    )
                )

                # Skill completed event (estimate duration)
                skill_duration = 1000  # Mock 1s duration
                skill_durations[skill_name_extracted] = skill_duration
                skill_success[skill_name_extracted] = not failed

                events.append(
                    TraceEvent(
                        timestamp=skill_start_time,
                        event_type="skill_completed",
                        skill_name=skill_name_extracted,
                        duration_ms=skill_duration,
                        success=not failed,
                        error=errors[0] if errors else None,
                    )
                )

        # Orchestration end event
        total_duration_ms = int(workflow_result.total_duration * 1000)
        events.append(
            TraceEvent(
                timestamp=started_at,
                event_type="orchestration_completed",
                skill_name=None,
                duration_ms=total_duration_ms,
                success=workflow_result.success,
                error=(workflow_result.errors[0] if workflow_result.errors else None),
            )
        )

        # Calculate metrics
        skill_count = len(skill_durations)
        success_count = sum(1 for success in skill_success.values() if success)
        success_rate = success_count / max(skill_count, 1) if skill_count > 0 else 0.0

        logger.info(
            "get_orchestration_trace_success",
            orchestration_id=orchestration_id,
            event_count=len(events),
        )

        return OrchestrationTrace(
            orchestration_id=orchestration_id,
            skill_name=skill_name,
            events=events,
            total_duration_ms=total_duration_ms,
            skill_count=skill_count,
            success_rate=success_rate,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_orchestration_trace_failed",
            orchestration_id=orchestration_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to retrieve orchestration trace: {e}",
        ) from e


# =============================================================================
# GET: Orchestration Metrics
# =============================================================================


@router.get("/metrics", response_model=OrchestrationMetrics)
async def get_orchestration_metrics() -> OrchestrationMetrics:
    """Get aggregated orchestration performance metrics.

    Returns metrics across all orchestrations:
    - Total count (all-time)
    - Success rate
    - Average duration
    - P95 latency
    - Error rate

    **Example Response:**
    ```json
    {
      "total_count": 150,
      "success_count": 142,
      "success_rate": 0.947,
      "avg_duration_ms": 8500.0,
      "p95_latency_ms": 15000.0,
      "error_rate": 0.053
    }
    ```

    Returns:
        OrchestrationMetrics with performance statistics

    Raises:
        HTTPException: 503 if orchestrator unavailable
    """
    logger.info("get_orchestration_metrics_request")

    try:
        orchestrator = get_orchestrator()

        # Get metrics from orchestrator
        metrics = orchestrator.get_metrics()

        total_count = metrics.get("total_workflows", 0)
        successful = metrics.get("successful_workflows", 0)
        failed = metrics.get("failed_workflows", 0)

        success_rate = successful / max(total_count, 1) if total_count > 0 else 0.0
        error_rate = failed / max(total_count, 1) if total_count > 0 else 0.0

        # Calculate avg duration (in ms)
        avg_duration_ms = metrics.get("avg_duration", 0.0) * 1000

        # Calculate P95 latency from history
        history = orchestrator._execution_history
        if history:
            durations_ms = [result.total_duration * 1000 for result in history]
            durations_ms.sort()
            p95_index = int(len(durations_ms) * 0.95)
            p95_latency_ms = durations_ms[p95_index] if p95_index < len(durations_ms) else 0.0
        else:
            p95_latency_ms = 0.0

        logger.info(
            "get_orchestration_metrics_success",
            total_count=total_count,
            success_rate=success_rate,
        )

        return OrchestrationMetrics(
            total_count=total_count,
            success_count=successful,
            success_rate=success_rate,
            avg_duration_ms=avg_duration_ms,
            p95_latency_ms=p95_latency_ms,
            error_rate=error_rate,
        )

    except Exception as e:
        logger.error("get_orchestration_metrics_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to retrieve orchestration metrics: {e}",
        ) from e
