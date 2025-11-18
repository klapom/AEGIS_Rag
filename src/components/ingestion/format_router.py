"""Format Router - Sprint 22 Feature 22.3.

This module provides intelligent routing between Docling (GPU-accelerated) and
LlamaIndex (fallback) parsers based on document format.

Architecture:
    - 30+ supported formats across 3 categories:
      1. Docling-optimized (14 formats): PDF, DOCX, PPTX, XLSX, images, etc.
      2. LlamaIndex-exclusive (9 formats): EPUB, RTF, TEX, MD, etc.
      3. Shared formats (7 formats): TXT, DOC, XLS, PPT, etc.
    - Graceful degradation when Docling container unavailable
    - Confidence scoring for routing decisions
    - Health check integration for real-time availability

Routing Logic:
    1. Check if format is supported
    2. If Docling-exclusive or shared → prefer Docling (GPU acceleration)
    3. If LlamaIndex-exclusive → use LlamaIndex
    4. If Docling unavailable → graceful degradation to LlamaIndex (shared formats only)
    5. Raise error if no parser available for format

Example:
    >>> router = FormatRouter(docling_available=True)
    >>> decision = router.route(Path("document.pdf"))
    >>> print(f"Parser: {decision.parser}, Reason: {decision.reason}")
    Parser: docling, Reason: Docling-optimized format with GPU acceleration

    >>> # Check Docling availability at startup
    >>> docling_available = await check_docling_availability()
    >>> router = FormatRouter(docling_available=docling_available)

Integration with LangGraph:
    The FormatRouter is used in the ingestion pipeline to determine which parser
    to invoke for each document:

    >>> routing_decision = format_router.route(file_path)
    >>> if routing_decision.parser == ParserType.DOCLING:
    ...     parsed_document = await docling_parse_node(state)
    ... else:
    ...     parsed_document = await llamaindex_parse_node(state)

Sprint 22 Context:
    - ADR-027: Docling CUDA Container Integration (95% OCR accuracy, 3.5x faster)
    - ADR-028: LlamaIndex positioned as strategic fallback (NOT deprecated)
    - Feature 22.3: Hybrid ingestion strategy with intelligent routing
    - Feature 22.4: LlamaIndex parser implementation (next task)
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, Set

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# PARSER TYPE ENUM
# =============================================================================


class ParserType(str, Enum):
    """Parser types for document ingestion.

    Attributes:
        DOCLING: Docling CUDA Container (GPU-accelerated, 14 formats)
        LLAMAINDEX: LlamaIndex fallback (connector library, 16 formats)
    """

    DOCLING = "docling"
    LLAMAINDEX = "llamaindex"


# =============================================================================
# FORMAT SET DEFINITIONS (30 TOTAL FORMATS)
# =============================================================================

# Docling-optimized formats (14 formats)
# These formats benefit from Docling's GPU acceleration and advanced parsing
DOCLING_FORMATS: Set[str] = {
    # Documents (native layout preservation)
    ".pdf",  # 95% OCR accuracy with EasyOCR, GPU-accelerated
    ".docx",  # Native layout preservation, table detection
    ".pptx",  # Slide structure + embedded images
    ".xlsx",  # Table extraction with 92% accuracy
    # Images (via EasyOCR CUDA)
    ".png",  # Image OCR with high accuracy
    ".jpg",  # JPEG image OCR
    ".jpeg",  # JPEG variant
    ".tiff",  # High-resolution document scans
    ".bmp",  # Bitmap images
    # Web/Structured (layout-aware parsing)
    ".html",  # HTML with DOM structure
    ".xml",  # XML with schema awareness
    ".json",  # JSON with structure preservation
    # Other
    ".csv",  # Table-aware CSV parsing
    ".ipynb",  # Jupyter notebooks with cell structure
}

# LlamaIndex-exclusive formats (9 formats)
# These formats are ONLY supported by LlamaIndex connectors
LLAMAINDEX_EXCLUSIVE: Set[str] = {
    ".epub",  # E-books (LlamaIndex EPUBReader)
    ".rtf",  # Rich Text Format (LlamaIndex RTFReader)
    ".tex",  # LaTeX documents (LlamaIndex LaTeXReader)
    ".md",  # Markdown (LlamaIndex MarkdownReader)
    ".rst",  # reStructuredText (LlamaIndex RSTReader)
    ".adoc",  # AsciiDoc (LlamaIndex AsciiDocReader)
    ".org",  # Org-Mode (LlamaIndex OrgReader)
    ".odt",  # OpenDocument Text (LlamaIndex ODTReader)
    ".msg",  # Outlook messages (LlamaIndex MSGReader)
}

# Shared formats (7 formats)
# Both Docling and LlamaIndex support these, Docling preferred for performance
SHARED_FORMATS: Set[str] = {
    ".txt",  # Plain text (both support, Docling faster)
    ".doc",  # Legacy Word (LlamaIndex more reliable for old format)
    ".xls",  # Legacy Excel (LlamaIndex more reliable)
    ".ppt",  # Legacy PowerPoint (LlamaIndex more reliable)
    ".htm",  # HTML variant
    ".mhtml",  # Web archive (MIME HTML)
    ".eml",  # Email messages (RFC 822)
}

# Total supported formats: 30
# = 14 (Docling) + 9 (LlamaIndex exclusive) + 7 (shared)
ALL_FORMATS: Set[str] = DOCLING_FORMATS | LLAMAINDEX_EXCLUSIVE | SHARED_FORMATS


# =============================================================================
# ROUTING DECISION DATA CLASS
# =============================================================================


@dataclass
class RoutingDecision:
    """Format routing decision with reasoning.

    Contains the parser selection, format details, reasoning, fallback availability,
    and confidence score.

    Attributes:
        parser: Selected parser (DOCLING or LLAMAINDEX)
        format: File extension (e.g., ".pdf")
        reason: Human-readable explanation of why this parser was chosen
        fallback_available: Whether fallback parser available if primary fails
        confidence: Routing confidence (high/medium/low)
    """

    parser: ParserType
    format: str
    reason: str
    fallback_available: bool
    confidence: Literal["high", "medium", "low"]


# =============================================================================
# FORMAT ROUTER CLASS
# =============================================================================


class FormatRouter:
    """Intelligent router to select optimal parser for each document format.

    The FormatRouter implements a decision tree that considers:
    1. Document format support (30+ formats)
    2. Parser capabilities (GPU acceleration, connector availability)
    3. Docling container availability (with graceful degradation)
    4. Fallback options (shared formats have 2 parsers)

    Routing Logic:
        1. Check if format is supported at all (raise ValueError if not)
        2. If Docling-exclusive or shared → prefer Docling (GPU acceleration)
        3. If LlamaIndex-exclusive → use LlamaIndex
        4. If Docling unavailable → graceful degradation to LlamaIndex (shared formats)
        5. If no parser available → raise RuntimeError

    Attributes:
        docling_available: Whether Docling container is available and healthy
    """

    def __init__(self, docling_available: bool = True) -> None:
        """Initialize format router.

        Args:
            docling_available: Whether Docling container is available (default: True).
                Set to False to simulate Docling unavailability or during startup
                health check failures.
        """
        self.docling_available = docling_available
        logger.info(
            "format_router_initialized",
            docling_available=docling_available,
            supported_formats=len(ALL_FORMATS),
            docling_formats=len(DOCLING_FORMATS),
            llamaindex_exclusive=len(LLAMAINDEX_EXCLUSIVE),
            shared_formats=len(SHARED_FORMATS),
        )

    def route(self, file_path: Path) -> RoutingDecision:
        """Determine which parser to use for the given file.

        Implements the routing decision tree:
        1. Extract file extension
        2. Check if format is supported (raise ValueError if not)
        3. Apply routing logic based on format category and Docling availability
        4. Return RoutingDecision with parser, reasoning, and confidence

        Args:
            file_path: Path to document file (can be relative or absolute)

        Returns:
            RoutingDecision with parser choice, reasoning, and metadata

        Raises:
            ValueError: If format is not supported by any parser
            RuntimeError: If Docling unavailable and no fallback for format

        Example:
            >>> router = FormatRouter(docling_available=True)
            >>> decision = router.route(Path("document.pdf"))
            >>> assert decision.parser == ParserType.DOCLING
            >>> assert decision.confidence == "high"
            >>> assert "GPU acceleration" in decision.reason
        """
        file_extension = file_path.suffix.lower()

        # Step 1: Check if format is supported
        if file_extension not in ALL_FORMATS:
            logger.error(
                "unsupported_format",
                format=file_extension,
                file_path=str(file_path),
                supported_formats=sorted(ALL_FORMATS),
            )
            raise ValueError(
                f"Unsupported format: {file_extension}. "
                f"Supported formats: {', '.join(sorted(ALL_FORMATS))}"
            )

        # Step 2: Apply routing logic
        # Case 1: Docling-optimized formats
        if file_extension in DOCLING_FORMATS:
            if self.docling_available:
                return RoutingDecision(
                    parser=ParserType.DOCLING,
                    format=file_extension,
                    reason="Docling-optimized format with GPU acceleration",
                    fallback_available=file_extension in SHARED_FORMATS,
                    confidence="high",
                )
            else:
                # Graceful degradation for shared formats
                if file_extension in SHARED_FORMATS:
                    logger.warning(
                        "docling_unavailable_fallback",
                        format=file_extension,
                        file_path=str(file_path),
                        fallback="llamaindex",
                    )
                    return RoutingDecision(
                        parser=ParserType.LLAMAINDEX,
                        format=file_extension,
                        reason="Docling unavailable, using LlamaIndex fallback",
                        fallback_available=False,
                        confidence="medium",
                    )
                else:
                    # No fallback available
                    logger.error(
                        "docling_unavailable_no_fallback",
                        format=file_extension,
                        file_path=str(file_path),
                    )
                    raise RuntimeError(
                        f"Docling container unavailable and no fallback for {file_extension}. "
                        f"Please start Docling container or use a supported fallback format."
                    )

        # Case 2: LlamaIndex-exclusive formats
        elif file_extension in LLAMAINDEX_EXCLUSIVE:
            return RoutingDecision(
                parser=ParserType.LLAMAINDEX,
                format=file_extension,
                reason="LlamaIndex-exclusive format",
                fallback_available=False,
                confidence="high",
            )

        # Case 3: Shared formats (prefer Docling when available)
        elif file_extension in SHARED_FORMATS:
            if self.docling_available:
                return RoutingDecision(
                    parser=ParserType.DOCLING,
                    format=file_extension,
                    reason="Shared format, Docling preferred for performance",
                    fallback_available=True,
                    confidence="high",
                )
            else:
                logger.warning(
                    "docling_unavailable_shared_format",
                    format=file_extension,
                    file_path=str(file_path),
                )
                return RoutingDecision(
                    parser=ParserType.LLAMAINDEX,
                    format=file_extension,
                    reason="Shared format, Docling unavailable",
                    fallback_available=False,
                    confidence="medium",
                )

        else:
            # Should never reach here due to earlier check
            logger.error(
                "unknown_format_category",
                format=file_extension,
                file_path=str(file_path),
            )
            raise ValueError(f"Unknown format category: {file_extension}")

    def is_supported(self, file_path: Path) -> bool:
        """Check if format is supported by any parser.

        Args:
            file_path: Path to document file

        Returns:
            True if format is supported, False otherwise

        Example:
            >>> router = FormatRouter()
            >>> assert router.is_supported(Path("document.pdf")) is True
            >>> assert router.is_supported(Path("unknown.xyz")) is False
        """
        file_extension = file_path.suffix.lower()
        return file_extension in ALL_FORMATS

    def get_supported_formats(self, parser: ParserType | None = None) -> Set[str]:
        """Get supported formats for a specific parser or all parsers.

        Args:
            parser: Optional parser type to filter by (DOCLING or LLAMAINDEX).
                If None, returns all supported formats.

        Returns:
            Set of supported file extensions (e.g., {".pdf", ".docx", ...})

        Example:
            >>> router = FormatRouter()
            >>> docling_formats = router.get_supported_formats(ParserType.DOCLING)
            >>> assert len(docling_formats) == 21  # 14 + 7 shared
            >>> llamaindex_formats = router.get_supported_formats(ParserType.LLAMAINDEX)
            >>> assert len(llamaindex_formats) == 16  # 9 + 7 shared
            >>> all_formats = router.get_supported_formats()
            >>> assert len(all_formats) == 30
        """
        if parser == ParserType.DOCLING:
            # Docling supports: 14 exclusive + 7 shared = 21 formats
            return DOCLING_FORMATS | SHARED_FORMATS
        elif parser == ParserType.LLAMAINDEX:
            # LlamaIndex supports: 9 exclusive + 7 shared = 16 formats
            return LLAMAINDEX_EXCLUSIVE | SHARED_FORMATS
        else:
            # All formats: 14 + 9 + 7 = 30 formats
            return ALL_FORMATS

    def update_docling_availability(self, available: bool) -> None:
        """Update Docling container availability status.

        This method allows dynamic updating of Docling availability during runtime,
        useful for health check monitoring or container restart scenarios.

        Args:
            available: New availability status (True = available, False = unavailable)

        Example:
            >>> router = FormatRouter(docling_available=True)
            >>> # Docling container crashes
            >>> router.update_docling_availability(False)
            >>> # Future routes will use LlamaIndex fallback
        """
        if available != self.docling_available:
            logger.info(
                "docling_availability_changed",
                old_status=self.docling_available,
                new_status=available,
            )
            self.docling_available = available


# =============================================================================
# DOCLING AVAILABILITY HEALTH CHECK
# =============================================================================


async def check_docling_availability() -> bool:
    """Check if Docling container is available and healthy.

    Performs a health check by attempting to start the Docling container
    (no-op if already running). Used during startup and periodic health checks.

    Returns:
        True if Docling container is reachable and healthy, False otherwise

    Example:
        >>> # Check at startup
        >>> docling_available = await check_docling_availability()
        >>> router = FormatRouter(docling_available=docling_available)

        >>> # Periodic health check (every 60s)
        >>> async def health_check_loop():
        ...     while True:
        ...         available = await check_docling_availability()
        ...         router.update_docling_availability(available)
        ...         await asyncio.sleep(60)

    Note:
        - This is a non-blocking health check (uses async/await)
        - Logs warning if Docling unavailable (but doesn't raise exception)
        - Container start is idempotent (safe to call if already running)
    """
    try:
        from src.components.ingestion.docling_client import DoclingContainerClient

        client = DoclingContainerClient()

        # Simple health check: try to start container (no-op if already running)
        await client.start()

        logger.info("docling_health_check_passed")
        return True

    except Exception as e:
        logger.warning(
            "docling_health_check_failed",
            error=str(e),
            error_type=type(e).__name__,
            fallback="llamaindex",
        )
        return False


async def initialize_format_router() -> FormatRouter:
    """Initialize format router with Docling availability check.

    Convenience function that performs health check and creates FormatRouter
    with correct availability status. Use this at application startup.

    Returns:
        FormatRouter instance with accurate Docling availability status

    Example:
        >>> # At application startup
        >>> router = await initialize_format_router()
        >>> # Router now knows if Docling is available

        >>> # Use in FastAPI lifespan
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     global format_router
        ...     format_router = await initialize_format_router()
        ...     yield
        ...     # Cleanup
    """
    docling_available = await check_docling_availability()
    router = FormatRouter(docling_available=docling_available)

    logger.info(
        "format_router_initialized",
        docling_available=docling_available,
        supported_formats=len(ALL_FORMATS),
    )

    return router


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ParserType",
    "RoutingDecision",
    "FormatRouter",
    "DOCLING_FORMATS",
    "LLAMAINDEX_EXCLUSIVE",
    "SHARED_FORMATS",
    "ALL_FORMATS",
    "check_docling_availability",
    "initialize_format_router",
]
