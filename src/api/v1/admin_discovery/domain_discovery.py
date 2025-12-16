"""Domain Auto-Discovery API Endpoint for File Uploads.

Sprint 46 - Feature 46.4: Domain Auto-Discovery Backend

This module provides a FastAPI endpoint for domain auto-discovery from uploaded documents.
Users can upload 1-3 sample files to automatically generate domain title and description.

Key Features:
- File upload handling (max 3 files, 10MB each)
- Multi-format support (PDF, DOCX, TXT, HTML, etc.)
- LLM-based domain suggestion with confidence scoring
- Integration with DomainAnalyzer service

Endpoint:
    POST /api/v1/admin/domains/discover
    - Accepts: multipart/form-data with files
    - Returns: DomainSuggestion (title, description, confidence, topics)

Usage:
    >>> import httpx
    >>> files = [
    ...     ("files", open("sample1.pdf", "rb")),
    ...     ("files", open("sample2.docx", "rb")),
    ... ]
    >>> response = httpx.post(
    ...     "http://localhost:8000/api/v1/admin/domains/discover",
    ...     files=files
    ... )
    >>> suggestion = response.json()
    >>> print(f"Title: {suggestion['title']}")
    >>> print(f"Description: {suggestion['description']}")

Integration:
    - Frontend: Upload widget in domain creation dialog
    - Backend: DomainAnalyzer → DomainDiscoveryService → Ollama LLM

Performance:
- Text extraction: ~100ms per file
- LLM analysis: ~5-15s (qwen3:32b)
- Total: <20s for 3 files
"""

from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin/domains", tags=["Domain Discovery"])


# --- Response Models ---


class DomainSuggestion(BaseModel):
    """Suggested domain based on uploaded document analysis.

    This model represents the LLM's suggested domain configuration
    after analyzing uploaded sample documents.

    Attributes:
        title: Human-readable domain title (2-4 words)
        description: Detailed description (50-100 words)
        confidence: Confidence score (0.0-1.0)
        detected_topics: Key topics found in documents
    """

    title: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Human-readable domain title (2-4 words)",
        examples=["Technical Documentation", "Legal Contracts", "Medical Research"],
    )
    description: str = Field(
        ...,
        min_length=50,
        max_length=1000,
        description="Detailed domain description (50-100 words)",
        examples=[
            "Technical documentation for software development projects, "
            "including API references, developer guides, and README files. "
            "Focuses on programming languages, frameworks, and tools."
        ],
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)",
        examples=[0.85],
    )
    detected_topics: list[str] = Field(
        default_factory=list,
        description="Key topics detected in documents",
        examples=[["Python", "FastAPI", "API Design", "Documentation"]],
    )


# --- Endpoints ---


@router.post("/discover", response_model=DomainSuggestion)
async def discover_domain(
    files: Annotated[
        list[UploadFile],
        File(
            description="Upload 1-3 sample documents (max 10MB each). "
            "Supported formats: TXT, MD, DOCX, HTML. (PDF: export to TXT first)"
        ),
    ],
) -> DomainSuggestion:
    """Analyze uploaded documents and suggest domain metadata.

    Upload 1-3 representative documents from your domain, and the LLM will analyze
    them to suggest an appropriate domain title and description. This is useful
    when creating a new domain but unsure how to describe it.

    The LLM analyzes:
    - Document content and themes
    - Technical terminology and concepts
    - Writing style and domain-specific language
    - Common entities and relationships

    Process:
    1. Upload 1-3 sample files (PDF, DOCX, TXT, etc.)
    2. Text is extracted from each file (first 5000 chars)
    3. LLM analyzes content to identify domain characteristics
    4. Returns suggested title, description, and confidence score

    File Requirements:
    - Minimum: 1 file
    - Maximum: 3 files
    - Max size per file: 10MB
    - Supported formats: TXT, MD, RST, DOCX, DOC, HTML, HTM
    - PDF support: Export to TXT format first

    Args:
        files: List of uploaded document files (1-3 files)

    Returns:
        DomainSuggestion with title, description, confidence, and detected topics

    Raises:
        HTTPException 400: If file validation fails (count, size, format)
        HTTPException 503: If Ollama service is unavailable
        HTTPException 500: If text extraction or LLM analysis fails

    Example:
        ```python
        import httpx

        files = [
            ("files", open("sample1.pdf", "rb")),
            ("files", open("sample2.docx", "rb")),
        ]

        response = httpx.post(
            "http://localhost:8000/api/v1/admin/domains/discover",
            files=files
        )

        suggestion = response.json()
        print(f"Suggested title: {suggestion['title']}")
        print(f"Confidence: {suggestion['confidence']}")
        ```
    """
    logger.info(
        "discover_domain_from_files_request",
        file_count=len(files),
        filenames=[f.filename for f in files],
        file_sizes=[f.size for f in files if f.size],
    )

    try:
        from src.components.domain_training.domain_analyzer import get_domain_analyzer

        analyzer = get_domain_analyzer()

        # Analyze files and get domain suggestion
        suggestion = await analyzer.analyze_from_files(files)

        logger.info(
            "domain_discovered_from_files",
            file_count=len(files),
            suggested_title=suggestion.title,
            confidence=suggestion.confidence,
            topics_count=len(suggestion.entity_types),
        )

        # Map internal DomainSuggestion to API response model
        return DomainSuggestion(
            title=suggestion.title,
            description=suggestion.description,
            confidence=suggestion.confidence,
            detected_topics=suggestion.entity_types,  # Use entity_types as topics
        )

    except ValueError as e:
        # File validation errors (count, size, format)
        logger.warning(
            "discover_domain_validation_error",
            file_count=len(files),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except httpx.ConnectError as e:
        # Ollama connection error
        logger.error(
            "discover_domain_ollama_connection_error",
            file_count=len(files),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama service is not available. Please check if Ollama is running.",
        )

    except httpx.HTTPStatusError as e:
        # Ollama HTTP error
        logger.error(
            "discover_domain_ollama_http_error",
            file_count=len(files),
            status_code=e.response.status_code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama API error: {e.response.status_code}",
        )

    except Exception as e:
        # Unexpected errors (text extraction, LLM analysis)
        logger.error(
            "discover_domain_from_files_unexpected_error",
            file_count=len(files),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Domain discovery failed: {str(e)}",
        )
