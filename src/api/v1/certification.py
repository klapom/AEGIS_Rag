"""
Certification API Router
Sprint 107 Feature 107.3: Certification status endpoint

Provides certification compliance status for EU AI Act, GDPR, and ISO standards.
This is a wrapper around the explainability certification endpoint to provide
the expected /api/v1/certification/status URL path.
"""

from fastapi import APIRouter

from src.api.v1.explainability import (
    CertificationStatusResponse,
    get_certification_status,
)

router = APIRouter(prefix="/certification", tags=["certification"])

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
