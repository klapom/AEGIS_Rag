"""Audit Trail API Endpoints.

Sprint 99 Feature 99.4: Audit Trail APIs (8 SP, 3 endpoints)
Implements EU AI Act Article 12 compliance with SHA-256 cryptographic chain.

Endpoints:
    - GET /api/v1/audit/events - List audit events (filterable, paginated)
    - GET /api/v1/audit/reports/:type - Generate compliance report
    - GET /api/v1/audit/integrity - Verify SHA-256 cryptographic chain

Performance Targets:
    - GET /events: P50 <100ms, P95 <250ms, P99 <500ms
    - GET /reports: P50 <1000ms, P95 <3000ms, P99 <5000ms
    - GET /integrity: P50 <500ms, P95 <2000ms, P99 <4000ms

Compliance:
    - EU AI Act Article 12: Record-Keeping Requirements
    - 7-year retention period
    - SHA-256 chain ensures tamper-evident logs
"""

import math
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.models.audit_models import (
    AuditEvent,
    AuditEventListResponse,
    AuditEventTypeEnum,
    AuditReportResponse,
    AuditReportSummary,
    IntegrityCheckResponse,
    OutcomeEnum,
    ReportTypeEnum,
)
from src.core.logging import get_logger
from src.governance.audit.storage import InMemoryAuditStorage
from src.governance.audit.trail import (
    AuditEventType,
    AuditTrailManager,
)

logger = get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize audit trail manager (singleton pattern)
_audit_manager: Optional[AuditTrailManager] = None


def get_audit_manager() -> AuditTrailManager:
    """Get or create audit trail manager singleton."""
    global _audit_manager
    if _audit_manager is None:
        storage = InMemoryAuditStorage(retention_days=365 * 7)  # 7 years
        _audit_manager = AuditTrailManager(storage=storage, retention_days=365 * 7)
    return _audit_manager


def _map_event_type_to_enum(event_type: AuditEventType) -> AuditEventTypeEnum:
    """Map internal AuditEventType to API enum."""
    mapping = {
        AuditEventType.SKILL_LOADED: AuditEventTypeEnum.SKILL_EXECUTE,
        AuditEventType.SKILL_EXECUTED: AuditEventTypeEnum.SKILL_EXECUTE,
        AuditEventType.SKILL_FAILED: AuditEventTypeEnum.SKILL_EXECUTE,
        AuditEventType.DATA_READ: AuditEventTypeEnum.DATA_ACCESS,
        AuditEventType.DATA_WRITE: AuditEventTypeEnum.DATA_CREATE,
        AuditEventType.DATA_DELETE: AuditEventTypeEnum.DATA_DELETE,
        AuditEventType.AUTH_SUCCESS: AuditEventTypeEnum.AUTH_LOGIN,
        AuditEventType.AUTH_FAILURE: AuditEventTypeEnum.AUTH_LOGIN,
        AuditEventType.POLICY_VIOLATION: AuditEventTypeEnum.POLICY_VIOLATION,
        AuditEventType.CONFIG_CHANGED: AuditEventTypeEnum.SYSTEM_CONFIG,
    }
    return mapping.get(event_type, AuditEventTypeEnum.SYSTEM_ERROR)


def _convert_audit_event_to_response(
    event: "src.governance.audit.trail.AuditEvent",
) -> AuditEvent:
    """Convert internal audit event to API response model."""
    # Map outcome
    outcome_mapping = {
        "success": OutcomeEnum.SUCCESS,
        "failure": OutcomeEnum.FAILURE,
        "blocked": OutcomeEnum.BLOCKED,
        "error": OutcomeEnum.ERROR,
    }
    outcome = outcome_mapping.get(event.outcome, OutcomeEnum.ERROR)

    return AuditEvent(
        id=event.id,
        timestamp=event.timestamp,
        event_type=_map_event_type_to_enum(event.event_type),
        actor_id=event.actor_id,
        actor_type=event.actor_type,
        action=event.action,
        outcome=outcome,
        metadata=event.metadata,
        context_hash=event.context_hash,
        output_hash=event.output_hash,
        previous_hash=event.previous_hash,
        event_hash=event.event_hash,
    )


@router.get("/events", response_model=AuditEventListResponse)
@limiter.limit("100/minute")
async def list_audit_events(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    event_type: Optional[AuditEventTypeEnum] = Query(None, description="Filter by event type"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    outcome: Optional[OutcomeEnum] = Query(None, description="Filter by outcome"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
) -> AuditEventListResponse:
    """List audit events (EU AI Act Article 12).

    Supports pagination and filtering by:
    - event_type: Type of audit event
    - actor_id: Actor identifier (user, agent, system)
    - outcome: Event outcome (success, failure, blocked, error)
    - start_time/end_time: Time range

    All events are cryptographically linked via SHA-256 chain.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page (1-100)
        event_type: Filter by event type
        actor_id: Filter by actor
        outcome: Filter by outcome
        start_time: Start time filter
        end_time: End time filter

    Returns:
        Paginated list of audit events

    Performance:
        - P50: <100ms
        - P95: <250ms
        - P99: <500ms
    """
    logger.info(
        "list_audit_events_request",
        page=page,
        page_size=page_size,
        event_type=event_type,
        actor_id=actor_id,
        outcome=outcome,
    )

    try:
        audit_manager = get_audit_manager()

        # Query events (no limit for filtering)
        events = await audit_manager.storage.query(
            start_time=start_time,
            end_time=end_time,
            actor_id=actor_id,
            limit=100000,  # Large limit for comprehensive filtering
        )

        # Apply outcome filter
        if outcome:
            outcome_str = outcome.value
            events = [e for e in events if e.outcome == outcome_str]

        # Pagination
        total = len(events)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_events = events[start_idx:end_idx]

        # Convert to response models
        items = [_convert_audit_event_to_response(e) for e in page_events]

        logger.info("list_audit_events_success", total=total, page=page, items=len(items))

        return AuditEventListResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error("list_audit_events_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list audit events: {str(e)}",
        )


@router.get("/reports/{report_type}", response_model=AuditReportResponse)
@limiter.limit("10/minute")
async def generate_audit_report(
    request: Request,
    report_type: ReportTypeEnum = Path(..., description="Report type"),
    start_time: datetime = Query(..., description="Report start time"),
    end_time: datetime = Query(..., description="Report end time"),
) -> AuditReportResponse:
    """Generate compliance audit report.

    Report Types:
    - gdpr_compliance: GDPR Article 30 processing activities
    - security_audit: Security events (auth, violations)
    - skill_usage: Skill execution audit trail

    Args:
        report_type: Type of report to generate
        start_time: Report start time
        end_time: Report end time

    Returns:
        Compliance report with events and recommendations

    Performance:
        - P50: <1000ms
        - P95: <3000ms
        - P99: <5000ms
    """
    logger.info(
        "generate_audit_report_request",
        report_type=report_type,
        start_time=start_time,
        end_time=end_time,
    )

    try:
        audit_manager = get_audit_manager()

        # Generate compliance report
        report = await audit_manager.generate_compliance_report(
            report_type=report_type.value,
            start_time=start_time,
            end_time=end_time,
        )

        # Query events for response
        events = await audit_manager.storage.query(
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        # Convert events to response models
        event_items = [_convert_audit_event_to_response(e) for e in events]

        # Generate recommendations based on report type
        recommendations: List[str] = []
        if report_type == ReportTypeEnum.GDPR_COMPLIANCE:
            if report.get("total_events", 0) == 0:
                recommendations.append("No processing activities found in this period.")
            else:
                recommendations.append(
                    f"Processed {report['total_events']} events during this period."
                )
                if not report.get("integrity_verified", False):
                    recommendations.append(
                        "⚠️ Integrity violations detected - review chain breaks."
                    )

        elif report_type == ReportTypeEnum.SECURITY_AUDIT:
            security_data = report.get("security_summary", {})
            failed_auth = security_data.get("failed_auth", 0)
            violations = security_data.get("violations", 0)

            if failed_auth > 0:
                recommendations.append(
                    f"⚠️ {failed_auth} failed authentication attempts - review access logs."
                )
            if violations > 0:
                recommendations.append(
                    f"⚠️ {violations} policy violations detected - investigate incidents."
                )
            if failed_auth == 0 and violations == 0:
                recommendations.append("✅ No security issues detected in this period.")

        elif report_type == ReportTypeEnum.SKILL_USAGE:
            skill_data = report.get("skill_usage", {})
            failures = skill_data.get("failures", 0)
            total_executions = skill_data.get("total_executions", 0)

            if total_executions > 0:
                failure_rate = failures / total_executions * 100
                if failure_rate > 10:
                    recommendations.append(
                        f"⚠️ High skill failure rate: {failure_rate:.1f}% "
                        f"({failures}/{total_executions})"
                    )
                else:
                    recommendations.append(
                        f"✅ Skill failure rate within acceptable range: {failure_rate:.1f}%"
                    )

        # Create summary
        summary = AuditReportSummary(
            report_type=report_type,
            start_time=start_time,
            end_time=end_time,
            generated_at=datetime.utcnow(),
            total_events=report.get("total_events", 0),
            integrity_verified=report.get("integrity_verified", False),
            integrity_errors=report.get("integrity_errors", []),
        )

        logger.info(
            "generate_audit_report_success",
            report_type=report_type,
            total_events=summary.total_events,
        )

        return AuditReportResponse(
            report_type=report_type,
            generated_at=summary.generated_at,
            summary=summary,
            events=event_items,
            recommendations=recommendations,
            data=report,
        )

    except Exception as e:
        logger.error("generate_audit_report_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate audit report: {str(e)}",
        )


@router.get("/integrity", response_model=IntegrityCheckResponse)
@limiter.limit("10/minute")
async def verify_audit_integrity(
    request: Request,
    start_time: Optional[datetime] = Query(None, description="Verification start time"),
    end_time: Optional[datetime] = Query(None, description="Verification end time"),
) -> IntegrityCheckResponse:
    """Verify SHA-256 cryptographic chain integrity (EU AI Act Article 12).

    Checks:
    - Each event's hash matches computed hash
    - Each event's previous_hash matches prior event's hash
    - No gaps in chain

    Tamper detection: Any modification to an event will break the chain.

    Args:
        start_time: Verification start time (optional)
        end_time: Verification end time (optional)

    Returns:
        Integrity verification result

    Performance:
        - P50: <500ms
        - P95: <2000ms
        - P99: <4000ms
    """
    logger.info(
        "verify_audit_integrity_request",
        start_time=start_time,
        end_time=end_time,
    )

    try:
        audit_manager = get_audit_manager()

        # Start timing
        start = time.time()

        # Verify integrity
        is_valid, errors = await audit_manager.verify_integrity(
            start_time=start_time,
            end_time=end_time,
        )

        # End timing
        duration_ms = (time.time() - start) * 1000

        # Get event count
        events = await audit_manager.storage.query(
            start_time=start_time,
            end_time=end_time,
            limit=100000,
        )
        total_events = len(events)
        verified_events = total_events if is_valid else total_events - len(errors)

        # Convert errors to chain breaks
        chain_breaks = [{"error": error} for error in errors]

        logger.info(
            "verify_audit_integrity_success",
            is_valid=is_valid,
            total_events=total_events,
            verified_events=verified_events,
            duration_ms=duration_ms,
        )

        return IntegrityCheckResponse(
            is_valid=is_valid,
            total_events=total_events,
            verified_events=verified_events,
            chain_breaks=chain_breaks,
            last_verified_at=datetime.utcnow(),
            verification_duration_ms=duration_ms,
        )

    except Exception as e:
        logger.error("verify_audit_integrity_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify audit integrity: {str(e)}",
        )
