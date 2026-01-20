"""Document Management API Endpoints.

Sprint 117 Feature 117.11: Manual Domain Override.

This module provides FastAPI endpoints for document management operations,
including manual domain override functionality.

Key Endpoints:
- PATCH /documents/{document_id}/domain - Override document domain classification
- GET /documents/{document_id}/domain/history - Get domain override history

Security:
- All endpoints require authentication (future Sprint)
- Rate limiting: 10 requests/minute per user
- Input validation with Pydantic v2 models

Performance:
- Domain override: <100ms (Neo4j transaction)
- History retrieval: <50ms (cached results)

Example:
    >>> # Override document domain
    >>> response = client.patch("/api/v1/documents/doc_abc123/domain", json={
    ...     "domain_id": "medical",
    ...     "reason": "Document contains medical terminology",
    ...     "reprocess_extraction": False
    ... })
"""

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from src.components.domain_training.domain_override_service import get_domain_override_service
from src.core.exceptions import DatabaseConnectionError
from src.core.models import ErrorCode
from src.core.models.domain_override import DomainOverrideRequest, DomainOverrideResponse
from src.core.models.response import ApiResponse
from src.core.response_utils import error_response_from_request, success_response_from_request

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.patch(
    "/{document_id}/domain",
    response_model=ApiResponse[DomainOverrideResponse],
    status_code=status.HTTP_200_OK,
    summary="Override document domain classification",
    description=(
        "Manually override the automatically detected domain classification for a document. "
        "This operation creates a full audit trail (who, when, why) and optionally triggers "
        "re-extraction of entities using the new domain's prompts."
    ),
    responses={
        200: {
            "description": "Domain override successful",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "document_id": "doc_abc123",
                            "previous_domain": {
                                "domain_id": "general",
                                "domain_name": "general",
                                "confidence": 0.42,
                                "classification_path": "auto",
                                "overridden_by": None,
                                "overridden_at": None,
                            },
                            "new_domain": {
                                "domain_id": "medical",
                                "domain_name": "medical",
                                "confidence": None,
                                "classification_path": "manual_override",
                                "overridden_by": "admin",
                                "overridden_at": "2026-01-21T12:00:00Z",
                            },
                            "reprocessing": None,
                        },
                        "message": "Domain override successful",
                        "request_id": "req_xyz789",
                    }
                }
            },
        },
        404: {
            "description": "Document or domain not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": "Document 'doc_abc123' not found",
                            "request_id": "req_xyz789",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_FAILED",
                            "message": "Invalid domain_id",
                            "request_id": "req_xyz789",
                        }
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTERNAL_SERVER_ERROR",
                            "message": "Domain override failed",
                            "request_id": "req_xyz789",
                        }
                    }
                }
            },
        },
    },
)
async def override_document_domain(
    document_id: str,
    override_request: DomainOverrideRequest,
    request: Request,
) -> ApiResponse[DomainOverrideResponse]:
    """Override document domain classification.

    Args:
        document_id: Document ID to override
        override_request: Override request with new domain_id, reason, reprocess_extraction
        request: FastAPI request object (for request_id)

    Returns:
        ApiResponse with DomainOverrideResponse

    Raises:
        HTTPException: If document/domain not found or database error
    """
    logger.info(
        "override_document_domain_request",
        document_id=document_id,
        new_domain_id=override_request.domain_id,
        reprocess_extraction=override_request.reprocess_extraction,
    )

    try:
        # Get domain override service
        service = get_domain_override_service()

        # Perform domain override
        result = await service.override_document_domain(
            document_id=document_id,
            new_domain_id=override_request.domain_id,
            reason=override_request.reason,
            reprocess_extraction=override_request.reprocess_extraction,
            user_id="admin",  # TODO Sprint 117.11: Get from auth context
        )

        logger.info(
            "domain_override_successful",
            document_id=document_id,
            previous_domain=result.previous_domain.domain_id,
            new_domain=result.new_domain.domain_id,
        )

        return success_response_from_request(
            request=request,
            data=result,
            message="Domain override successful",
        )

    except ValueError as e:
        # Document or domain not found
        logger.warning(
            "domain_override_validation_error",
            document_id=document_id,
            error=str(e),
        )

        return error_response_from_request(
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=str(e),
        )

    except DatabaseConnectionError as e:
        # Database connection error
        logger.error(
            "domain_override_database_error",
            document_id=document_id,
            error=str(e),
        )

        return error_response_from_request(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.DATABASE_CONNECTION_FAILED,
            message=f"Domain override failed: {e}",
        )

    except Exception as e:
        # Unexpected error
        logger.error(
            "domain_override_unexpected_error",
            document_id=document_id,
            error=str(e),
            exc_info=True,
        )

        return error_response_from_request(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=f"Unexpected error during domain override: {e}",
        )


@router.get(
    "/{document_id}/domain/history",
    response_model=ApiResponse[list[dict]],
    status_code=status.HTTP_200_OK,
    summary="Get domain override history",
    description=(
        "Retrieve the audit trail of domain overrides for a document, "
        "showing who changed the domain, when, and why."
    ),
    responses={
        200: {
            "description": "Domain override history retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "audit_123",
                                "previous_domain": "general",
                                "new_domain": "medical",
                                "user_id": "admin",
                                "reason": "Document contains medical terminology",
                                "timestamp": "2026-01-21T12:00:00Z",
                            }
                        ],
                        "message": "Domain override history retrieved",
                        "request_id": "req_xyz789",
                    }
                }
            },
        },
        404: {
            "description": "Document not found",
        },
        500: {
            "description": "Internal server error",
        },
    },
)
async def get_domain_override_history(
    document_id: str,
    request: Request,
    limit: int = 10,
) -> ApiResponse[list[dict]]:
    """Get domain override history for a document.

    Args:
        document_id: Document ID
        request: FastAPI request object (for request_id)
        limit: Maximum number of audit entries to return (default: 10)

    Returns:
        ApiResponse with list of audit entries

    Raises:
        HTTPException: If database error
    """
    logger.info(
        "get_domain_override_history_request",
        document_id=document_id,
        limit=limit,
    )

    try:
        # Get domain override service
        service = get_domain_override_service()

        # Retrieve override history
        history = await service.get_domain_override_history(
            document_id=document_id,
            limit=limit,
        )

        logger.info(
            "domain_override_history_retrieved",
            document_id=document_id,
            entries_count=len(history),
        )

        return success_response_from_request(
            request=request,
            data=history,
            message=f"Retrieved {len(history)} domain override entries",
        )

    except DatabaseConnectionError as e:
        # Database connection error
        logger.error(
            "domain_override_history_database_error",
            document_id=document_id,
            error=str(e),
        )

        return error_response_from_request(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.DATABASE_CONNECTION_FAILED,
            message=f"Failed to retrieve domain override history: {e}",
        )

    except Exception as e:
        # Unexpected error
        logger.error(
            "domain_override_history_unexpected_error",
            document_id=document_id,
            error=str(e),
            exc_info=True,
        )

        return error_response_from_request(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=f"Unexpected error retrieving domain override history: {e}",
        )
