"""
Certification API Router
Sprint 107 Feature 107.3: Certification status endpoint
Sprint 112: Skill certification dashboard endpoints

Provides certification compliance status for EU AI Act, GDPR, and ISO standards.
This is a wrapper around the explainability certification endpoint to provide
the expected /api/v1/certification/status URL path.

Sprint 112 adds skill-level certification management endpoints:
- GET /overview - Certification overview with counts by level/status
- GET /skills - All skill certifications with optional filtering
- GET /expiring - Skills with expiring certifications
- GET /skill/{skillName}/report - Validation report for specific skill
- POST /skill/{skillName}/validate - Trigger validation for skill
"""

from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.api.v1.explainability import (
    CertificationStatusResponse,
    get_certification_status,
)
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/certification", tags=["certification"])


# ============================================================================
# Pydantic Models (Sprint 112)
# ============================================================================


class CertificationCheck(BaseModel):
    """Individual certification check result."""

    check_name: str
    category: Literal["gdpr", "security", "audit", "explainability"]
    passed: bool
    details: Optional[str] = None


class SkillCertification(BaseModel):
    """Skill certification details."""

    skill_name: str
    version: str
    level: Literal["uncertified", "basic", "standard", "enterprise"]
    status: Literal["valid", "expiring_soon", "expired", "pending"]
    valid_until: Optional[str] = None
    last_validated: str
    checks: List[CertificationCheck]
    issues: Optional[List[str]] = None


class ValidationReport(BaseModel):
    """Validation report for a skill."""

    skill_name: str
    timestamp: str
    passed_checks: int
    total_checks: int
    checks: List[CertificationCheck]
    recommendations: List[str]
    certification_level: Literal["uncertified", "basic", "standard", "enterprise"]


class CertificationOverview(BaseModel):
    """Certification overview statistics."""

    enterprise_count: int = Field(..., description="Number of enterprise-certified skills")
    standard_count: int = Field(..., description="Number of standard-certified skills")
    basic_count: int = Field(..., description="Number of basic-certified skills")
    uncertified_count: int = Field(..., description="Number of uncertified skills")
    expiring_soon_count: int = Field(..., description="Skills expiring within 30 days")
    expired_count: int = Field(..., description="Number of expired certifications")


# ============================================================================
# Mock Data Helper Functions (Sprint 112)
# ============================================================================


def _generate_mock_skill_certifications() -> List[SkillCertification]:
    """
    Generate mock skill certifications.

    TODO: Replace with database query to fetch actual skill certification data.
    Integration points:
    - Query src.domains.skills.certification_service for real certification data
    - Load from Redis cache for fast repeated access
    - Trigger validation checks via background tasks
    """
    now = datetime.now(timezone.utc)
    certifications = []

    # Enterprise-level skills (3)
    for i in range(3):
        certifications.append(
            SkillCertification(
                skill_name=f"enterprise_skill_{i+1}",
                version="2.1.0",
                level="enterprise",
                status="valid",
                valid_until=(now + timedelta(days=180)).isoformat().replace("+00:00", "Z"),
                last_validated=now.isoformat().replace("+00:00", "Z"),
                checks=[
                    CertificationCheck(
                        check_name="GDPR Article 13 Transparency",
                        category="gdpr",
                        passed=True,
                        details="Full transparency reporting implemented",
                    ),
                    CertificationCheck(
                        check_name="ISO 27001 Security Controls",
                        category="security",
                        passed=True,
                        details="All security controls verified",
                    ),
                    CertificationCheck(
                        check_name="7-Year Audit Trail",
                        category="audit",
                        passed=True,
                        details="Complete audit trail with SHA-256 chaining",
                    ),
                    CertificationCheck(
                        check_name="3-Level Explainability",
                        category="explainability",
                        passed=True,
                        details="User/Expert/Audit explanations available",
                    ),
                ],
                issues=None,
            )
        )

    # Standard-level skills (4)
    for i in range(4):
        certifications.append(
            SkillCertification(
                skill_name=f"standard_skill_{i+1}",
                version="1.5.2",
                level="standard",
                status="valid",
                valid_until=(now + timedelta(days=90)).isoformat().replace("+00:00", "Z"),
                last_validated=now.isoformat().replace("+00:00", "Z"),
                checks=[
                    CertificationCheck(
                        check_name="GDPR Article 13 Transparency",
                        category="gdpr",
                        passed=True,
                    ),
                    CertificationCheck(
                        check_name="Basic Security Controls",
                        category="security",
                        passed=True,
                    ),
                    CertificationCheck(
                        check_name="Audit Trail",
                        category="audit",
                        passed=True,
                    ),
                    CertificationCheck(
                        check_name="3-Level Explainability",
                        category="explainability",
                        passed=False,
                        details="Only user-level explanations implemented",
                    ),
                ],
                issues=["Missing expert/audit-level explanations"],
            )
        )

    # Basic-level skills (5) - some expiring soon
    for i in range(5):
        days_until_expiry = 25 if i < 2 else 60  # First 2 expire soon
        certifications.append(
            SkillCertification(
                skill_name=f"basic_skill_{i+1}",
                version="1.0.0",
                level="basic",
                status="expiring_soon" if i < 2 else "valid",
                valid_until=(now + timedelta(days=days_until_expiry))
                .isoformat()
                .replace("+00:00", "Z"),
                last_validated=now.isoformat().replace("+00:00", "Z"),
                checks=[
                    CertificationCheck(
                        check_name="GDPR Article 13 Transparency",
                        category="gdpr",
                        passed=True,
                    ),
                    CertificationCheck(
                        check_name="Basic Security Controls",
                        category="security",
                        passed=True,
                    ),
                    CertificationCheck(
                        check_name="Audit Trail",
                        category="audit",
                        passed=False,
                        details="Incomplete audit logging",
                    ),
                    CertificationCheck(
                        check_name="3-Level Explainability",
                        category="explainability",
                        passed=False,
                    ),
                ],
                issues=["Incomplete audit trail", "Missing explainability"],
            )
        )

    # Uncertified skills (3)
    for i in range(3):
        certifications.append(
            SkillCertification(
                skill_name=f"uncertified_skill_{i+1}",
                version="0.9.0",
                level="uncertified",
                status="pending",
                valid_until=None,
                last_validated=now.isoformat().replace("+00:00", "Z"),
                checks=[
                    CertificationCheck(
                        check_name="GDPR Article 13 Transparency",
                        category="gdpr",
                        passed=False,
                    ),
                    CertificationCheck(
                        check_name="Basic Security Controls",
                        category="security",
                        passed=False,
                    ),
                    CertificationCheck(
                        check_name="Audit Trail",
                        category="audit",
                        passed=False,
                    ),
                    CertificationCheck(
                        check_name="3-Level Explainability",
                        category="explainability",
                        passed=False,
                    ),
                ],
                issues=[
                    "Missing GDPR compliance",
                    "No security controls",
                    "No audit trail",
                    "No explainability",
                ],
            )
        )

    # Expired skills (2)
    for i in range(2):
        certifications.append(
            SkillCertification(
                skill_name=f"expired_skill_{i+1}",
                version="0.8.0",
                level="basic",
                status="expired",
                valid_until=(now - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
                last_validated=(now - timedelta(days=100)).isoformat().replace("+00:00", "Z"),
                checks=[
                    CertificationCheck(
                        check_name="GDPR Article 13 Transparency",
                        category="gdpr",
                        passed=True,
                    ),
                    CertificationCheck(
                        check_name="Basic Security Controls",
                        category="security",
                        passed=True,
                    ),
                    CertificationCheck(
                        check_name="Audit Trail",
                        category="audit",
                        passed=False,
                    ),
                    CertificationCheck(
                        check_name="3-Level Explainability",
                        category="explainability",
                        passed=False,
                    ),
                ],
                issues=["Certification expired - re-validation required"],
            )
        )

    return certifications


# ============================================================================
# API Endpoints (Sprint 112)
# ============================================================================


@router.get("/overview", response_model=CertificationOverview)
async def get_certification_overview() -> CertificationOverview:
    """
    Get certification overview statistics.

    Returns counts of skills by certification level and status.
    Used for dashboard summary view.

    **Sprint 112 Feature 112.1: Certification Dashboard**

    Returns:
        CertificationOverview with counts by level (enterprise/standard/basic/uncertified)
        and status (expiring_soon/expired)

    TODO: Replace mock data with real skill certification database queries
    """
    logger.info("certification_overview_request")

    # Generate mock data
    all_certs = _generate_mock_skill_certifications()

    # Count by level
    enterprise_count = sum(1 for c in all_certs if c.level == "enterprise")
    standard_count = sum(1 for c in all_certs if c.level == "standard")
    basic_count = sum(1 for c in all_certs if c.level == "basic" and c.status != "expired")
    uncertified_count = sum(1 for c in all_certs if c.level == "uncertified")

    # Count by status
    expiring_soon_count = sum(1 for c in all_certs if c.status == "expiring_soon")
    expired_count = sum(1 for c in all_certs if c.status == "expired")

    return CertificationOverview(
        enterprise_count=enterprise_count,
        standard_count=standard_count,
        basic_count=basic_count,
        uncertified_count=uncertified_count,
        expiring_soon_count=expiring_soon_count,
        expired_count=expired_count,
    )


@router.get("/skills", response_model=List[SkillCertification])
async def get_skill_certifications(
    level: Optional[Literal["uncertified", "basic", "standard", "enterprise"]] = Query(
        None, description="Filter by certification level"
    ),
    status: Optional[Literal["valid", "expiring_soon", "expired", "pending"]] = Query(
        None, description="Filter by certification status"
    ),
) -> List[SkillCertification]:
    """
    Get all skill certifications with optional filtering.

    **Sprint 112 Feature 112.1: Certification Dashboard**

    Args:
        level: Optional filter by certification level
        status: Optional filter by certification status

    Returns:
        List of skill certifications (filtered if parameters provided)

    TODO: Replace mock data with database query
    Integration points:
    - Query src.domains.skills.certification_service.get_all_certifications()
    - Apply filters at database level for performance
    - Cache results in Redis for 5 minutes
    """
    logger.info(
        "skill_certifications_request",
        level=level,
        status=status,
    )

    # Generate mock data
    all_certs = _generate_mock_skill_certifications()

    # Apply filters
    filtered_certs = all_certs
    if level:
        filtered_certs = [c for c in filtered_certs if c.level == level]
    if status:
        filtered_certs = [c for c in filtered_certs if c.status == status]

    logger.info(
        "skill_certifications_response",
        total_count=len(filtered_certs),
        level_filter=level,
        status_filter=status,
    )

    return filtered_certs


@router.get("/expiring", response_model=List[SkillCertification])
async def get_expiring_certifications(
    days: int = Query(30, ge=1, le=365, description="Days threshold for expiration warning")
) -> List[SkillCertification]:
    """
    Get skills with certifications expiring within specified days.

    **Sprint 112 Feature 112.1: Certification Dashboard**

    Args:
        days: Number of days threshold (default: 30)

    Returns:
        List of skills with certifications expiring within the threshold

    TODO: Replace mock data with database query
    Integration points:
    - Query skills with valid_until < (now + days)
    - Order by valid_until ascending (soonest first)
    - Send email notifications for expiring certifications (background task)
    """
    logger.info("expiring_certifications_request", days=days)

    now = datetime.now(timezone.utc)
    threshold = now + timedelta(days=days)

    # Generate mock data
    all_certs = _generate_mock_skill_certifications()

    # Filter by expiring soon
    expiring = [
        c
        for c in all_certs
        if c.valid_until
        and datetime.fromisoformat(c.valid_until.replace("Z", "+00:00")) <= threshold
        and c.status != "expired"  # Exclude already expired
    ]

    # Sort by expiration date (soonest first)
    expiring.sort(
        key=lambda c: datetime.fromisoformat(c.valid_until.replace("Z", "+00:00"))
        if c.valid_until
        else now
    )

    logger.info(
        "expiring_certifications_response",
        count=len(expiring),
        days_threshold=days,
    )

    return expiring


@router.get("/skill/{skill_name}/report", response_model=ValidationReport)
async def get_skill_validation_report(skill_name: str) -> ValidationReport:
    """
    Get validation report for a specific skill.

    Returns detailed validation checks, passed/failed counts,
    recommendations for improvement, and current certification level.

    **Sprint 112 Feature 112.1: Certification Dashboard**

    Args:
        skill_name: Name of the skill to get report for

    Returns:
        ValidationReport with checks, recommendations, and certification level

    TODO: Replace mock data with real validation logic
    Integration points:
    - Query src.domains.skills.certification_service.validate_skill(skill_name)
    - Run all certification checks (GDPR, security, audit, explainability)
    - Generate recommendations based on failed checks
    - Cache report in Redis for 1 hour
    """
    logger.info("skill_validation_report_request", skill_name=skill_name)

    # Find skill in mock data
    all_certs = _generate_mock_skill_certifications()
    skill_cert = next((c for c in all_certs if c.skill_name == skill_name), None)

    if not skill_cert:
        # Generate a basic uncertified report for unknown skills
        skill_cert = SkillCertification(
            skill_name=skill_name,
            version="unknown",
            level="uncertified",
            status="pending",
            valid_until=None,
            last_validated=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            checks=[
                CertificationCheck(
                    check_name="GDPR Article 13 Transparency",
                    category="gdpr",
                    passed=False,
                ),
                CertificationCheck(
                    check_name="Basic Security Controls",
                    category="security",
                    passed=False,
                ),
                CertificationCheck(
                    check_name="Audit Trail",
                    category="audit",
                    passed=False,
                ),
                CertificationCheck(
                    check_name="3-Level Explainability",
                    category="explainability",
                    passed=False,
                ),
            ],
            issues=["Skill not found in certification database"],
        )

    # Calculate passed/total checks
    passed_checks = sum(1 for check in skill_cert.checks if check.passed)
    total_checks = len(skill_cert.checks)

    # Generate recommendations based on failed checks
    recommendations = []
    for check in skill_cert.checks:
        if not check.passed:
            if check.category == "gdpr":
                recommendations.append(
                    "Implement GDPR Article 13 transparency requirements "
                    "(data usage disclosure, user rights)"
                )
            elif check.category == "security":
                recommendations.append(
                    "Add security controls: input validation, rate limiting, "
                    "authentication checks"
                )
            elif check.category == "audit":
                recommendations.append(
                    "Implement 7-year audit trail with SHA-256 chaining "
                    "(EU AI Act Article 12)"
                )
            elif check.category == "explainability":
                recommendations.append(
                    "Add 3-level explainability: user (simple), expert (technical), "
                    "audit (complete trace)"
                )

    # Add level-specific recommendations
    if skill_cert.level == "uncertified":
        recommendations.append(
            "Start with basic certification: Focus on GDPR compliance and basic security"
        )
    elif skill_cert.level == "basic":
        recommendations.append(
            "Upgrade to standard: Add complete audit trail and expert-level explanations"
        )
    elif skill_cert.level == "standard":
        recommendations.append(
            "Upgrade to enterprise: Implement all explainability levels "
            "and ISO 27001 controls"
        )

    return ValidationReport(
        skill_name=skill_name,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        passed_checks=passed_checks,
        total_checks=total_checks,
        checks=skill_cert.checks,
        recommendations=recommendations,
        certification_level=skill_cert.level,
    )


@router.post("/skill/{skill_name}/validate", response_model=ValidationReport)
async def validate_skill(skill_name: str) -> ValidationReport:
    """
    Trigger validation for a specific skill.

    Runs all certification checks and returns updated validation report.
    This endpoint triggers background validation tasks and returns
    immediately with current/cached results.

    **Sprint 112 Feature 112.1: Certification Dashboard**

    Args:
        skill_name: Name of the skill to validate

    Returns:
        ValidationReport with updated checks and recommendations

    TODO: Replace mock data with real validation logic
    Integration points:
    - Trigger background task: celery_app.send_task('validate_skill', [skill_name])
    - Queue validation checks: GDPR, security, audit, explainability
    - Update certification database with results
    - Send notification email if certification status changes
    - Return cached report immediately, update asynchronously
    """
    logger.info("skill_validation_trigger", skill_name=skill_name)

    # For now, just return the same as get_report
    # In production, this would trigger background validation
    report = await get_skill_validation_report(skill_name)

    logger.info(
        "skill_validation_triggered",
        skill_name=skill_name,
        passed_checks=report.passed_checks,
        total_checks=report.total_checks,
        certification_level=report.certification_level,
    )

    return report


# ============================================================================
# Legacy Endpoint (Sprint 107)
# ============================================================================

# Re-export the certification status endpoint at /certification/status
# This allows both /api/v1/certification/status and
# /api/v1/explainability/certification/status to work
router.add_api_route(
    "/status",
    endpoint=get_certification_status,
    methods=["GET"],
    response_model=CertificationStatusResponse,
    summary="Get AI system certification status",
    description="""
    Get the current certification compliance status for various EU regulations
    and industry standards.

    **EU AI Act Article 43 - Conformity Assessment**

    Returns:
    - Certification level (basic/standard/advanced)
    - Active certifications (EU AI Act, GDPR, ISO standards)
    - Compliance score (0-100)
    - Last audit date

    **Certifications Tracked:**
    - EU AI Act Compliance
    - GDPR Compliance (Articles 6, 7, 13-22, 30)
    - ISO/IEC 27001 (Information Security)
    - ISO/IEC 42001 (AI Management System)
    """,
)
