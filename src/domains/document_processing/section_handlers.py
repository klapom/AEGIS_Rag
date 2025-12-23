"""Type-Specific Section Handlers - Feature 62.7.

This module provides type-specific section extraction and handling strategies
for different document formats.

Handlers:
- PDFSectionHandler: Extracts sections using page numbers and headers
- DocxSectionHandler: Extracts sections using heading styles
- HTMLSectionHandler: Extracts sections using heading tags
- MarkdownSectionHandler: Extracts sections using markdown headers
- GenericSectionHandler: Fallback for other formats
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import structlog

from src.domains.document_processing.document_types import (
    DocumentType,
    SectionMetadata,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# SECTION HANDLER PROTOCOL
# =============================================================================


class SectionHandler(ABC):
    """Base class for document type-specific section handling.

    Each handler implements type-specific logic for:
    - Extracting sections from parsed documents
    - Identifying section boundaries
    - Determining heading levels
    - Preserving document-specific metadata
    """

    @abstractmethod
    def extract_sections(
        self,
        parsed_content: dict[str, Any],
        document_type: DocumentType,
    ) -> list[dict[str, Any]]:
        """Extract sections from parsed document content.

        Args:
            parsed_content: Output from document parser (Docling/LlamaIndex)
            document_type: Type of source document

        Returns:
            List of sections with:
            - heading: str - Section heading
            - level: int - Heading level (1-6)
            - text: str - Section content
            - metadata: SectionMetadata - Type-specific metadata
        """
        pass

    @abstractmethod
    def should_handle(self, document_type: DocumentType) -> bool:
        """Check if handler supports this document type.

        Args:
            document_type: Type of document

        Returns:
            True if handler can process this type
        """
        pass


# =============================================================================
# PDF SECTION HANDLER
# =============================================================================


class PDFSectionHandler(SectionHandler):
    """Extracts sections from PDF documents using page numbers and headers.

    PDF-specific features:
    - Track page numbers for each section
    - Extract bounding boxes for visual sections
    - Detect section headers from layout analysis
    - Preserve page-level boundaries
    """

    def should_handle(self, document_type: DocumentType) -> bool:
        """Check if document is PDF.

        Args:
            document_type: Document type to check

        Returns:
            True if PDF
        """
        return document_type == DocumentType.PDF

    def extract_sections(
        self,
        parsed_content: dict[str, Any],
        document_type: DocumentType,
    ) -> list[dict[str, Any]]:
        """Extract sections from PDF with page tracking.

        PDF sections are determined by:
        1. Page boundaries
        2. Heading detection from layout
        3. Visual structure analysis

        Args:
            parsed_content: Docling-parsed PDF content
            document_type: Document type (should be PDF)

        Returns:
            List of PDF sections with page metadata
        """
        sections = []

        # Extract sections from parsed content if available
        if "sections" in parsed_content:
            for section_data in parsed_content["sections"]:
                metadata = SectionMetadata(
                    heading=section_data.get("heading", "Untitled Section"),
                    level=section_data.get("level", 1),
                    document_type=document_type,
                    page_no=section_data.get("page_no"),
                    page_start=section_data.get("page_start"),
                    page_end=section_data.get("page_end"),
                    bbox=section_data.get("bbox"),
                    content_position=self._determine_position(
                        section_data.get("page_no"),
                        parsed_content.get("total_pages", 1),
                    ),
                )

                sections.append(
                    {
                        "heading": metadata.heading,
                        "level": metadata.level,
                        "text": section_data.get("text", ""),
                        "page_no": metadata.page_no,
                        "metadata": metadata,
                    }
                )

        logger.info(
            "pdf_sections_extracted",
            section_count=len(sections),
            total_pages=parsed_content.get("total_pages"),
        )

        return sections

    @staticmethod
    def _determine_position(
        page_no: int | None,
        total_pages: int,
    ) -> str:
        """Determine content position based on page number.

        Args:
            page_no: Current page number
            total_pages: Total number of pages

        Returns:
            Position string: "start", "middle", or "end"
        """
        if page_no is None:
            return "middle"

        if page_no < total_pages * 0.25:
            return "start"
        elif page_no > total_pages * 0.75:
            return "end"
        else:
            return "middle"


# =============================================================================
# DOCX SECTION HANDLER
# =============================================================================


class DocxSectionHandler(SectionHandler):
    """Extracts sections from DOCX documents using heading styles.

    DOCX-specific features:
    - Detect section levels from heading styles (Heading 1, 2, 3, etc.)
    - Preserve style information
    - Track document outline structure
    - Handle nested heading hierarchies
    """

    # Standard Word heading styles
    HEADING_STYLES = {
        "Heading 1": 1,
        "Heading 2": 2,
        "Heading 3": 3,
        "Heading 4": 4,
        "Heading 5": 5,
        "Heading 6": 6,
    }

    def should_handle(self, document_type: DocumentType) -> bool:
        """Check if document is DOCX.

        Args:
            document_type: Document type to check

        Returns:
            True if DOCX
        """
        return document_type == DocumentType.DOCX

    def extract_sections(
        self,
        parsed_content: dict[str, Any],
        document_type: DocumentType,
    ) -> list[dict[str, Any]]:
        """Extract sections from DOCX with heading styles.

        DOCX sections are determined by:
        1. Heading style (Heading 1, 2, 3, etc.)
        2. Document outline structure
        3. Nested hierarchy

        Args:
            parsed_content: Parsed DOCX content
            document_type: Document type (should be DOCX)

        Returns:
            List of DOCX sections with style metadata
        """
        sections = []

        # Extract sections from parsed content if available
        if "sections" in parsed_content:
            for section_data in parsed_content["sections"]:
                style = section_data.get("style", "")
                level = self.HEADING_STYLES.get(style, 1)

                metadata = SectionMetadata(
                    heading=section_data.get("heading", "Untitled Section"),
                    level=level,
                    document_type=document_type,
                    style=style,
                    content_position=section_data.get("position", "middle"),
                )

                sections.append(
                    {
                        "heading": metadata.heading,
                        "level": metadata.level,
                        "text": section_data.get("text", ""),
                        "style": style,
                        "metadata": metadata,
                    }
                )

        logger.info(
            "docx_sections_extracted",
            section_count=len(sections),
            style_count=len({s.get("style") for s in sections}),
        )

        return sections


# =============================================================================
# HTML SECTION HANDLER
# =============================================================================


class HTMLSectionHandler(SectionHandler):
    """Extracts sections from HTML documents using heading tags.

    HTML-specific features:
    - Parse heading tags (h1, h2, h3, h4, h5, h6)
    - Preserve heading hierarchy
    - Detect semantic structure from tags
    - Handle nested sections
    """

    def should_handle(self, document_type: DocumentType) -> bool:
        """Check if document is HTML.

        Args:
            document_type: Document type to check

        Returns:
            True if HTML
        """
        return document_type == DocumentType.HTML

    def extract_sections(
        self,
        parsed_content: dict[str, Any],
        document_type: DocumentType,
    ) -> list[dict[str, Any]]:
        """Extract sections from HTML with heading tags.

        HTML sections are determined by:
        1. Heading tags (h1-h6)
        2. Semantic structure
        3. Nesting level

        Args:
            parsed_content: Parsed HTML content
            document_type: Document type (should be HTML)

        Returns:
            List of HTML sections with tag information
        """
        sections = []

        # Extract sections from parsed content if available
        if "sections" in parsed_content:
            for section_data in parsed_content["sections"]:
                tag = section_data.get("tag", "div")
                level = self._extract_level_from_tag(tag)

                metadata = SectionMetadata(
                    heading=section_data.get("heading", "Untitled Section"),
                    level=level,
                    document_type=document_type,
                    style=tag,
                    content_position=section_data.get("position", "middle"),
                )

                sections.append(
                    {
                        "heading": metadata.heading,
                        "level": metadata.level,
                        "text": section_data.get("text", ""),
                        "tag": tag,
                        "metadata": metadata,
                    }
                )

        logger.info(
            "html_sections_extracted",
            section_count=len(sections),
            tags=list({s.get("tag") for s in sections}),
        )

        return sections

    @staticmethod
    def _extract_level_from_tag(tag: str) -> int:
        """Extract heading level from HTML tag.

        Args:
            tag: HTML tag (e.g., "h1", "h2")

        Returns:
            Heading level (1-6), default 1 if not a heading
        """
        tag_lower = tag.lower()
        if tag_lower.startswith("h") and len(tag_lower) > 1:
            try:
                level = int(tag_lower[1])
                return max(1, min(level, 6))  # Clamp to 1-6
            except ValueError:
                pass
        return 1  # Default to level 1


# =============================================================================
# MARKDOWN SECTION HANDLER
# =============================================================================


class MarkdownSectionHandler(SectionHandler):
    """Extracts sections from Markdown documents using markdown headers.

    Markdown-specific features:
    - Parse markdown headers (#, ##, ###, etc.)
    - Detect level from number of hashes
    - Preserve markdown structure
    - Handle both ATX (#) and Setext (underline) headers
    """

    def should_handle(self, document_type: DocumentType) -> bool:
        """Check if document is Markdown.

        Args:
            document_type: Document type to check

        Returns:
            True if Markdown
        """
        return document_type == DocumentType.MD

    def extract_sections(
        self,
        parsed_content: dict[str, Any],
        document_type: DocumentType,
    ) -> list[dict[str, Any]]:
        """Extract sections from Markdown with header support.

        Markdown sections are determined by:
        1. ATX headers (#, ##, ###, etc.)
        2. Header level (number of hashes)
        3. Content hierarchy

        Args:
            parsed_content: Parsed Markdown content
            document_type: Document type (should be Markdown)

        Returns:
            List of Markdown sections with level information
        """
        sections = []

        # Extract sections from parsed content if available
        if "sections" in parsed_content:
            for section_data in parsed_content["sections"]:
                level = section_data.get("level", 1)

                metadata = SectionMetadata(
                    heading=section_data.get("heading", "Untitled Section"),
                    level=level,
                    document_type=document_type,
                    line_no=section_data.get("line_no"),
                    content_position=section_data.get("position", "middle"),
                )

                sections.append(
                    {
                        "heading": metadata.heading,
                        "level": metadata.level,
                        "text": section_data.get("text", ""),
                        "line_no": metadata.line_no,
                        "metadata": metadata,
                    }
                )

        logger.info(
            "markdown_sections_extracted",
            section_count=len(sections),
            max_level=max((s.get("level", 1) for s in sections), default=1),
        )

        return sections


# =============================================================================
# GENERIC SECTION HANDLER (FALLBACK)
# =============================================================================


class GenericSectionHandler(SectionHandler):
    """Generic fallback handler for unsupported or unknown document types.

    Implements basic section detection:
    - Use document structure if available
    - Extract generic metadata
    - Handle edge cases gracefully
    """

    def should_handle(self, document_type: DocumentType) -> bool:
        """Handle any document type (fallback).

        Args:
            document_type: Document type to check

        Returns:
            Always True (universal handler)
        """
        return True

    def extract_sections(
        self,
        parsed_content: dict[str, Any],
        document_type: DocumentType,
    ) -> list[dict[str, Any]]:
        """Extract sections using generic logic.

        Generic sections:
        1. Use document structure if available
        2. Treat entire document as single section if needed
        3. Extract basic metadata

        Args:
            parsed_content: Parsed content (format varies)
            document_type: Document type

        Returns:
            List of generic sections
        """
        sections = []

        # Try to extract sections if available
        if "sections" in parsed_content:
            for section_data in parsed_content["sections"]:
                metadata = SectionMetadata(
                    heading=section_data.get("heading", "Section"),
                    level=section_data.get("level", 1),
                    document_type=document_type,
                    content_position=section_data.get("position", "middle"),
                )

                sections.append(
                    {
                        "heading": metadata.heading,
                        "level": metadata.level,
                        "text": section_data.get("text", ""),
                        "metadata": metadata,
                    }
                )

        # If no sections found, create default section
        if not sections:
            metadata = SectionMetadata(
                heading="Document Content",
                level=1,
                document_type=document_type,
            )

            sections.append(
                {
                    "heading": "Document Content",
                    "level": 1,
                    "text": parsed_content.get("text", ""),
                    "metadata": metadata,
                }
            )

        logger.info(
            "generic_sections_extracted",
            section_count=len(sections),
            document_type=document_type.value,
        )

        return sections


# =============================================================================
# SECTION HANDLER REGISTRY
# =============================================================================


def get_section_handler(document_type: DocumentType) -> SectionHandler:
    """Get appropriate section handler for document type.

    Strategy:
    1. Match document type to specific handler
    2. Fall back to generic handler
    3. Log selection

    Args:
        document_type: Type of document

    Returns:
        Appropriate SectionHandler instance

    Example:
        >>> handler = get_section_handler(DocumentType.PDF)
        >>> assert isinstance(handler, PDFSectionHandler)

        >>> handler = get_section_handler(DocumentType.TXT)
        >>> assert isinstance(handler, GenericSectionHandler)
    """
    handlers: list[SectionHandler] = [
        PDFSectionHandler(),
        DocxSectionHandler(),
        HTMLSectionHandler(),
        MarkdownSectionHandler(),
        GenericSectionHandler(),  # Must be last (fallback)
    ]

    for handler in handlers:
        if handler.should_handle(document_type):
            logger.info(
                "section_handler_selected",
                document_type=document_type.value,
                handler_type=type(handler).__name__,
            )
            return handler

    # Should never reach here due to GenericSectionHandler
    return GenericSectionHandler()


__all__ = [
    "SectionHandler",
    "PDFSectionHandler",
    "DocxSectionHandler",
    "HTMLSectionHandler",
    "MarkdownSectionHandler",
    "GenericSectionHandler",
    "get_section_handler",
]
