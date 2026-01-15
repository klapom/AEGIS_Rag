"""GDPR Compliance API Endpoints.

Sprint 99 Feature 99.3: GDPR & Compliance APIs (12 SP, 5 endpoints)
Implements GDPR Articles 6,7,13-22,30 for EU legal compliance.

Endpoints:
    - GET /api/v1/gdpr/consents - List all consents (paginated, filterable)
    - POST /api/v1/gdpr/consent - Create new consent record
    - POST /api/v1/gdpr/request - Create data subject request (Access, Erasure, etc.)
    - GET /api/v1/gdpr/processing-activities - Article 30 processing activities log
    - GET/PUT /api/v1/gdpr/pii-settings - PII detection settings

Performance Targets:
    - GET endpoints: P50 <80ms, P95 <200ms, P99 <400ms
    - POST endpoints: P50 <150ms, P95 <400ms, P99 <800ms
"""

import math
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.models.gdpr_models import (
    ConsentCreateRequest,
    ConsentListResponse,
    ConsentRecord,
    ConsentStatusEnum,
    DataCategoryEnum,
    DataSubjectRequestCreate,
    DataSubjectRequestResponse,
    LegalBasisEnum,
    PIISettingsResponse,
    PIISettingsUpdate,
    ProcessingActivity,
    ProcessingActivityResponse,
    RequestStatusEnum,
)
from src.core.logging import get_logger
from src.governance.gdpr.compliance import (
    ConsentRecord as GDPRConsentRecord,
    DataCategory,
    LegalBasis,
)
from src.governance.gdpr.storage import ConsentStore, ProcessingLog

logger = get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/gdpr", tags=["gdpr"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize storage backends (singleton pattern)
_consent_store: Optional[ConsentStore] = None
_processing_log: Optional[ProcessingLog] = None
_pii_settings: Optional[PIISettingsResponse] = None


def get_consent_store() -> ConsentStore:
    """Get or create consent store singleton."""
    global _consent_store
    if _consent_store is None:
        _consent_store = ConsentStore()
    return _consent_store


def get_processing_log() -> ProcessingLog:
    """Get or create processing log singleton."""
    global _processing_log
    if _processing_log is None:
        _processing_log = ProcessingLog()
    return _processing_log


def get_pii_settings() -> PIISettingsResponse:
    """Get or create PII settings singleton."""
    global _pii_settings
    if _pii_settings is None:
        _pii_settings = PIISettingsResponse()
    return _pii_settings


def _map_legal_basis_to_enum(legal_basis: LegalBasis) -> LegalBasisEnum:
    """Map internal LegalBasis to API enum."""
    mapping = {
        LegalBasis.CONSENT: LegalBasisEnum.CONSENT,
        LegalBasis.CONTRACT: LegalBasisEnum.CONTRACT,
        LegalBasis.LEGAL_OBLIGATION: LegalBasisEnum.LEGAL_OBLIGATION,
        LegalBasis.VITAL_INTERESTS: LegalBasisEnum.VITAL_INTERESTS,
        LegalBasis.PUBLIC_TASK: LegalBasisEnum.PUBLIC_TASK,
        LegalBasis.LEGITIMATE_INTERESTS: LegalBasisEnum.LEGITIMATE_INTERESTS,
    }
    return mapping[legal_basis]


def _map_data_category_to_enum(category: DataCategory) -> DataCategoryEnum:
    """Map internal DataCategory to API enum."""
    mapping = {
        DataCategory.IDENTIFIER: DataCategoryEnum.IDENTIFIER,
        DataCategory.CONTACT: DataCategoryEnum.CONTACT,
        DataCategory.FINANCIAL: DataCategoryEnum.FINANCIAL,
        DataCategory.HEALTH: DataCategoryEnum.HEALTH,
        DataCategory.BEHAVIORAL: DataCategoryEnum.BEHAVIORAL,
        DataCategory.BIOMETRIC: DataCategoryEnum.BIOMETRIC,
        DataCategory.LOCATION: DataCategoryEnum.LOCATION,
        DataCategory.DEMOGRAPHIC: DataCategoryEnum.DEMOGRAPHIC,
    }
    return mapping.get(category, DataCategoryEnum.OTHER)


def _convert_consent_to_response(consent: GDPRConsentRecord) -> ConsentRecord:
    """Convert internal consent record to API response model."""
    # Determine status
    if consent.withdrawn_at:
        status = ConsentStatusEnum.WITHDRAWN
    elif consent.expires_at and datetime.utcnow() > consent.expires_at:
        status = ConsentStatusEnum.EXPIRED
    else:
        status = ConsentStatusEnum.GRANTED

    return ConsentRecord(
        consent_id=consent.consent_id,
        user_id=consent.data_subject_id,
        purpose=consent.purpose,
        legal_basis=_map_legal_basis_to_enum(consent.legal_basis),
        data_categories=[_map_data_category_to_enum(cat) for cat in consent.data_categories],
        granted_at=consent.granted_at,
        expires_at=consent.expires_at,
        withdrawn_at=consent.withdrawn_at,
        withdrawal_reason=consent.withdrawal_reason,
        status=status,
        metadata=consent.metadata,
    )


@router.get("/consents", response_model=ConsentListResponse)
@limiter.limit("100/minute")
async def list_consents(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    purpose: Optional[str] = Query(None, description="Filter by purpose"),
    legal_basis: Optional[LegalBasisEnum] = Query(None, description="Filter by legal basis"),
    status: Optional[ConsentStatusEnum] = Query(None, description="Filter by status"),
) -> ConsentListResponse:
    """List all consent records (GDPR Article 7).

    Supports pagination and filtering by:
    - user_id: Data subject user ID
    - purpose: Processing purpose
    - legal_basis: GDPR Article 6 legal basis
    - status: granted, withdrawn, expired

    Args:
        page: Page number (1-indexed)
        page_size: Items per page (1-100)
        user_id: Filter by user ID
        purpose: Filter by purpose
        legal_basis: Filter by legal basis
        status: Filter by status

    Returns:
        Paginated list of consent records

    Performance:
        - P50: <80ms
        - P95: <200ms
        - P99: <400ms
    """
    logger.info(
        "list_consents_request",
        page=page,
        page_size=page_size,
        user_id=user_id,
        purpose=purpose,
        legal_basis=legal_basis,
        status=status,
    )

    try:
        consent_store = get_consent_store()

        # Get all consents
        all_consents: List[GDPRConsentRecord] = []
        for subject_consents in consent_store._consents.values():
            all_consents.extend(subject_consents)

        # Apply filters
        if user_id:
            all_consents = [c for c in all_consents if c.data_subject_id == user_id]

        if purpose:
            all_consents = [c for c in all_consents if purpose.lower() in c.purpose.lower()]

        if legal_basis:
            all_consents = [
                c for c in all_consents
                if c.legal_basis.value == legal_basis.value
            ]

        if status:
            filtered = []
            for c in all_consents:
                consent_status = (
                    ConsentStatusEnum.WITHDRAWN if c.withdrawn_at
                    else ConsentStatusEnum.EXPIRED
                    if c.expires_at and datetime.utcnow() > c.expires_at
                    else ConsentStatusEnum.GRANTED
                )
                if consent_status == status:
                    filtered.append(c)
            all_consents = filtered

        # Pagination
        total = len(all_consents)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_consents = all_consents[start_idx:end_idx]

        # Convert to response models
        items = [_convert_consent_to_response(c) for c in page_consents]

        logger.info("list_consents_success", total=total, page=page, items=len(items))

        return ConsentListResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error("list_consents_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list consents: {str(e)}",
        )


@router.post("/consent", response_model=ConsentRecord, status_code=status.HTTP_201_CREATED)
@limiter.limit("50/minute")
async def create_consent(request: Request, consent_request: ConsentCreateRequest) -> ConsentRecord:
    """Create new consent record (GDPR Article 7).

    Consent must be:
    - Freely given
    - Specific
    - Informed
    - Unambiguous

    Args:
        request: Consent creation request

    Returns:
        Created consent record

    Raises:
        HTTPException: If validation fails

    Performance:
        - P50: <150ms
        - P95: <400ms
        - P99: <800ms
    """
    logger.info(
        "create_consent_request",
        user_id=consent_request.user_id,
        purpose=consent_request.purpose,
        legal_basis=consent_request.legal_basis,
    )

    try:
        # Map API enums to internal enums
        legal_basis_internal = LegalBasis(consent_request.legal_basis.value)
        data_categories_internal = [DataCategory(cat.value) for cat in consent_request.data_categories]

        # Calculate expiration
        expires_at = None
        if consent_request.retention_period:
            expires_at = datetime.utcnow() + timedelta(days=consent_request.retention_period)

        # Create consent record
        consent = GDPRConsentRecord(
            consent_id=str(uuid4()),
            data_subject_id=consent_request.user_id,
            purpose=consent_request.purpose,
            legal_basis=legal_basis_internal,
            data_categories=data_categories_internal,
            granted_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata={"explicit_consent": consent_request.explicit_consent},
        )

        # Store consent
        consent_store = get_consent_store()
        await consent_store.add(consent)

        logger.info(
            "create_consent_success",
            consent_id=consent.consent_id,
            user_id=consent_request.user_id,
        )

        return _convert_consent_to_response(consent)

    except ValueError as e:
        logger.warning("create_consent_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}",
        )
    except Exception as e:
        logger.error("create_consent_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create consent: {str(e)}",
        )


@router.post("/request", response_model=DataSubjectRequestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_data_subject_request(
    request: Request,
    subject_request: DataSubjectRequestCreate,
) -> DataSubjectRequestResponse:
    """Create data subject request (GDPR Articles 15-22).

    Request Types:
    - access: Article 15 - Right of access
    - erasure: Article 17 - Right to erasure ("right to be forgotten")
    - rectification: Article 16 - Right to rectification
    - portability: Article 20 - Right to data portability
    - restriction: Article 18 - Right to restriction of processing
    - objection: Article 21 - Right to object

    Args:
        request: Data subject request

    Returns:
        Created request with pending status

    Performance:
        - P50: <150ms
        - P95: <400ms
        - P99: <800ms
    """
    logger.info(
        "create_data_subject_request",
        request_type=subject_request.request_type,
        user_id=subject_request.user_id,
    )

    try:
        request_id = str(uuid4())
        now = datetime.utcnow()

        # Create request response
        response = DataSubjectRequestResponse(
            request_id=request_id,
            request_type=subject_request.request_type,
            user_id=subject_request.user_id,
            status=RequestStatusEnum.PENDING,
            details=subject_request.details,
            created_at=now,
            updated_at=now,
        )

        # Log processing activity (Article 30)
        processing_log = get_processing_log()
        from src.governance.gdpr.compliance import DataProcessingRecord

        processing_record = DataProcessingRecord(
            record_id=str(uuid4()),
            controller_name="AegisRAG",
            processing_purpose=f"GDPR Request: {subject_request.request_type.value}",
            legal_basis=LegalBasis.LEGAL_OBLIGATION,
            data_categories=[DataCategory.IDENTIFIER],
            data_subjects=[subject_request.user_id],
            metadata={
                "request_id": request_id,
                "request_type": subject_request.request_type.value,
            },
        )
        await processing_log.add(processing_record)

        logger.info(
            "create_data_subject_request_success",
            request_id=request_id,
            request_type=subject_request.request_type,
        )

        return response

    except Exception as e:
        logger.error("create_data_subject_request_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create data subject request: {str(e)}",
        )


@router.get("/processing-activities", response_model=ProcessingActivityResponse)
@limiter.limit("50/minute")
async def get_processing_activities(
    request: Request,
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    purpose: Optional[str] = Query(None, description="Filter by purpose"),
) -> ProcessingActivityResponse:
    """List processing activities (GDPR Article 30).

    Article 30 requires controllers to maintain records of processing activities.
    This endpoint provides the record-keeping log for compliance audits.

    Args:
        start_date: Filter by start date
        end_date: Filter by end date
        purpose: Filter by processing purpose

    Returns:
        List of processing activities

    Performance:
        - P50: <80ms
        - P95: <200ms
        - P99: <400ms
    """
    logger.info(
        "get_processing_activities_request",
        start_date=start_date,
        end_date=end_date,
        purpose=purpose,
    )

    try:
        processing_log = get_processing_log()

        # Query processing records
        if purpose:
            records = await processing_log.get_by_purpose(purpose, start_date, end_date)
        else:
            records = await processing_log.get_all(start_date, end_date)

        # Convert to API models
        activities = [
            ProcessingActivity(
                record_id=record.record_id,
                controller_name=record.controller_name,
                processing_purpose=record.processing_purpose,
                legal_basis=_map_legal_basis_to_enum(record.legal_basis),
                data_categories=[
                    _map_data_category_to_enum(cat) for cat in record.data_categories
                ],
                data_subjects=record.data_subjects,
                recipients=record.recipients,
                retention_period=record.retention_period,
                security_measures=record.security_measures,
                processed_at=record.processed_at,
                metadata=record.metadata,
            )
            for record in records
        ]

        logger.info("get_processing_activities_success", total=len(activities))

        return ProcessingActivityResponse(
            activities=activities,
            total=len(activities),
        )

    except Exception as e:
        logger.error("get_processing_activities_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing activities: {str(e)}",
        )


@router.get("/pii-settings", response_model=PIISettingsResponse)
@limiter.limit("100/minute")
async def get_pii_settings(request: Request) -> PIISettingsResponse:
    """Get PII detection settings.

    Returns current configuration for:
    - Entity types to detect (PERSON, EMAIL, SSN, etc.)
    - Confidence threshold (0.0-1.0)
    - Anonymization rules per category

    Returns:
        PII detection settings

    Performance:
        - P50: <50ms
        - P95: <100ms
        - P99: <200ms
    """
    logger.info("get_pii_settings_request")

    try:
        settings = get_pii_settings()
        logger.info("get_pii_settings_success")
        return settings

    except Exception as e:
        logger.error("get_pii_settings_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get PII settings: {str(e)}",
        )


@router.put("/pii-settings", response_model=PIISettingsResponse)
@limiter.limit("20/minute")
async def update_pii_settings(request: Request, settings_update: PIISettingsUpdate) -> PIISettingsResponse:
    """Update PII detection settings.

    Allows configuration of:
    - Entity types to detect
    - Confidence threshold
    - Anonymization rules

    Args:
        request: PII settings update

    Returns:
        Updated PII settings

    Performance:
        - P50: <150ms
        - P95: <400ms
        - P99: <800ms
    """
    logger.info("update_pii_settings_request", request=settings_update.model_dump())

    try:
        global _pii_settings
        current_settings = get_pii_settings()

        # Update settings
        if settings_update.entity_types is not None:
            current_settings.entity_types = settings_update.entity_types
        if settings_update.confidence_threshold is not None:
            current_settings.confidence_threshold = settings_update.confidence_threshold
        if settings_update.anonymization_rules is not None:
            current_settings.anonymization_rules = settings_update.anonymization_rules

        _pii_settings = current_settings

        logger.info("update_pii_settings_success")
        return current_settings

    except Exception as e:
        logger.error("update_pii_settings_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update PII settings: {str(e)}",
        )
