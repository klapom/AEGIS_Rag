"""Document Type Support for Sections - Feature 62.7.

This module provides document type detection, classification, and type-specific
section handling for ingestion pipeline.

Supported Document Types:
- PDF: Portable Document Format with page numbers and section headers
- DOCX: Microsoft Word with heading styles (Heading 1, 2, 3)
- HTML: Web documents with heading tags (h1, h2, h3)
- MD: Markdown with markdown headers (#, ##, ###)
- TXT: Plain text files
- XLSX: Excel spreadsheets
- PPTX: PowerPoint presentations
- Other formats with fallback handling

Features:
- Detect document type from file extension and MIME type
- Type-specific section extraction strategies
- Storage of document type in chunk metadata
- Filtering by document type in vector/graph stores
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# DOCUMENT TYPE ENUM
# =============================================================================


class DocumentType(str, Enum):
    """Supported document types for section handling.

    Attributes:
        PDF: Portable Document Format
        DOCX: Microsoft Word (.docx)
        HTML: HTML web documents
        MD: Markdown documents
        TXT: Plain text files
        XLSX: Excel spreadsheets
        PPTX: PowerPoint presentations
        UNKNOWN: Unsupported or unknown format
    """

    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MD = "markdown"
    TXT = "text"
    XLSX = "xlsx"
    PPTX = "pptx"
    UNKNOWN = "unknown"


# =============================================================================
# DOCUMENT TYPE MAPPING
# =============================================================================


# Map file extensions to DocumentType
EXTENSION_TO_TYPE: dict[str, DocumentType] = {
    # PDF
    ".pdf": DocumentType.PDF,
    # Word
    ".docx": DocumentType.DOCX,
    ".doc": DocumentType.DOCX,  # Legacy, treated as DOCX
    # HTML
    ".html": DocumentType.HTML,
    ".htm": DocumentType.HTML,
    ".xhtml": DocumentType.HTML,
    ".mhtml": DocumentType.HTML,
    # Markdown
    ".md": DocumentType.MD,
    ".markdown": DocumentType.MD,
    ".mdown": DocumentType.MD,
    # Text
    ".txt": DocumentType.TXT,
    ".text": DocumentType.TXT,
    ".plain": DocumentType.TXT,
    # Excel
    ".xlsx": DocumentType.XLSX,
    ".xls": DocumentType.XLSX,  # Legacy, treated as XLSX
    ".csv": DocumentType.XLSX,  # Tabular format
    # PowerPoint
    ".pptx": DocumentType.PPTX,
    ".ppt": DocumentType.PPTX,  # Legacy, treated as PPTX
}

# MIME type mapping
MIME_TO_TYPE: dict[str, DocumentType] = {
    "application/pdf": DocumentType.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,  # noqa: E501
    "application/msword": DocumentType.DOCX,
    "text/html": DocumentType.HTML,
    "application/xhtml+xml": DocumentType.HTML,
    "text/markdown": DocumentType.MD,
    "text/plain": DocumentType.TXT,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.XLSX,  # noqa: E501
    "application/vnd.ms-excel": DocumentType.XLSX,
    "text/csv": DocumentType.XLSX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": DocumentType.PPTX,  # noqa: E501
    "application/vnd.ms-powerpoint": DocumentType.PPTX,
}


# =============================================================================
# SECTION METADATA
# =============================================================================


@dataclass
class SectionMetadata:
    """Metadata about a section extracted from a document.

    Attributes:
        heading: Section heading/title
        level: Heading level (1-6, with 1 being top-level)
        document_type: Type of source document
        page_no: Page number (PDF only, 0-indexed)
        page_start: Starting page (for multi-page sections)
        page_end: Ending page (for multi-page sections)
        bbox: Bounding box for visual sections [x1, y1, x2, y2]
        line_no: Starting line number (for text files)
        style: Heading style (e.g., "Heading 1" for DOCX)
        content_position: Position in document (start, middle, end)
    """

    heading: str
    level: int
    document_type: DocumentType
    page_no: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    bbox: list[float] | None = None
    line_no: int | None = None
    style: str | None = None
    content_position: Literal["start", "middle", "end"] = "middle"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage in chunk metadata.

        Returns:
            Dictionary representation of section metadata
        """
        return {
            "heading": self.heading,
            "level": self.level,
            "document_type": self.document_type.value,
            "page_no": self.page_no,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "bbox": self.bbox,
            "line_no": self.line_no,
            "style": self.style,
            "content_position": self.content_position,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SectionMetadata":
        """Create from dictionary (for retrieval from storage).

        Args:
            data: Dictionary with section metadata

        Returns:
            SectionMetadata instance
        """
        doc_type_str = data.get("document_type", "unknown")
        try:
            document_type = DocumentType(doc_type_str)
        except ValueError:
            document_type = DocumentType.UNKNOWN

        return cls(
            heading=data.get("heading", ""),
            level=data.get("level", 1),
            document_type=document_type,
            page_no=data.get("page_no"),
            page_start=data.get("page_start"),
            page_end=data.get("page_end"),
            bbox=data.get("bbox"),
            line_no=data.get("line_no"),
            style=data.get("style"),
            content_position=data.get("content_position", "middle"),
        )


# =============================================================================
# DOCUMENT TYPE DETECTION
# =============================================================================


def detect_document_type(
    file_path: Path,
    mime_type: str | None = None,
) -> DocumentType:
    """Detect document type from file path and optional MIME type.

    Strategy:
    1. Try MIME type detection (if provided)
    2. Fall back to file extension
    3. Return UNKNOWN if format not recognized

    Args:
        file_path: Path to document file
        mime_type: Optional MIME type (e.g., "application/pdf")

    Returns:
        Detected DocumentType

    Example:
        >>> doc_type = detect_document_type(Path("report.pdf"))
        >>> assert doc_type == DocumentType.PDF

        >>> doc_type = detect_document_type(Path("doc.bin"), mime_type="application/pdf")
        >>> assert doc_type == DocumentType.PDF
    """
    # Try MIME type first (if provided)
    if mime_type:
        doc_type = MIME_TO_TYPE.get(mime_type.lower())
        if doc_type:
            logger.info(
                "document_type_detected_by_mime",
                file_path=str(file_path),
                mime_type=mime_type,
                document_type=doc_type.value,
            )
            return doc_type

    # Fall back to file extension
    extension = file_path.suffix.lower()
    doc_type = EXTENSION_TO_TYPE.get(extension, DocumentType.UNKNOWN)

    if doc_type == DocumentType.UNKNOWN:
        logger.warning(
            "document_type_unknown",
            file_path=str(file_path),
            extension=extension,
        )
    else:
        logger.info(
            "document_type_detected_by_extension",
            file_path=str(file_path),
            extension=extension,
            document_type=doc_type.value,
        )

    return doc_type


def get_document_type_description(doc_type: DocumentType) -> str:
    """Get human-readable description of document type.

    Args:
        doc_type: DocumentType enum value

    Returns:
        Human-readable description
    """
    descriptions: dict[DocumentType, str] = {
        DocumentType.PDF: "Portable Document Format (with page numbers and section headers)",
        DocumentType.DOCX: "Microsoft Word (with heading styles)",
        DocumentType.HTML: "HTML web document (with heading tags)",
        DocumentType.MD: "Markdown document (with markdown headers)",
        DocumentType.TXT: "Plain text file",
        DocumentType.XLSX: "Excel spreadsheet (with table structure)",
        DocumentType.PPTX: "PowerPoint presentation (with slide structure)",
        DocumentType.UNKNOWN: "Unknown or unsupported format",
    }
    return descriptions.get(doc_type, "Unknown format")


__all__ = [
    "DocumentType",
    "SectionMetadata",
    "detect_document_type",
    "get_document_type_description",
    "EXTENSION_TO_TYPE",
    "MIME_TO_TYPE",
]
