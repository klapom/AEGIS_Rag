"""Unit Tests for Section Handlers - Feature 62.7.

Tests for:
- Type-specific section handlers
- Section extraction logic
- Handler selection and routing
- Edge cases and fallback behavior

Coverage target: >80%
"""

from src.domains.document_processing.document_types import DocumentType
from src.domains.document_processing.section_handlers import (
    DocxSectionHandler,
    GenericSectionHandler,
    HTMLSectionHandler,
    MarkdownSectionHandler,
    PDFSectionHandler,
    SectionHandler,
    get_section_handler,
)

# =============================================================================
# PDF SECTION HANDLER TESTS
# =============================================================================


class TestPDFSectionHandler:
    """Test PDF-specific section handling."""

    def test_handler_should_handle_pdf(self) -> None:
        """Test that handler claims to handle PDF documents."""
        handler = PDFSectionHandler()
        assert handler.should_handle(DocumentType.PDF) is True

    def test_handler_should_not_handle_other_types(self) -> None:
        """Test that handler doesn't claim to handle other types."""
        handler = PDFSectionHandler()
        assert handler.should_handle(DocumentType.DOCX) is False
        assert handler.should_handle(DocumentType.HTML) is False
        assert handler.should_handle(DocumentType.MD) is False

    def test_extract_basic_pdf_sections(self) -> None:
        """Test extracting basic PDF sections."""
        handler = PDFSectionHandler()
        parsed_content = {
            "total_pages": 10,
            "sections": [
                {
                    "heading": "Introduction",
                    "level": 1,
                    "text": "This is the introduction.",
                    "page_no": 0,
                    "page_start": 0,
                    "page_end": 2,
                    "bbox": [10, 20, 100, 80],
                }
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.PDF)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Introduction"
        assert sections[0]["level"] == 1
        assert sections[0]["metadata"].page_no == 0

    def test_extract_multiple_pdf_sections(self) -> None:
        """Test extracting multiple PDF sections."""
        handler = PDFSectionHandler()
        parsed_content = {
            "total_pages": 20,
            "sections": [
                {
                    "heading": "Chapter 1",
                    "level": 1,
                    "text": "Content 1",
                    "page_no": 1,
                    "page_start": 1,
                    "page_end": 5,
                    "bbox": [10, 20, 100, 80],
                },
                {
                    "heading": "Section 1.1",
                    "level": 2,
                    "text": "Content 1.1",
                    "page_no": 2,
                    "page_start": 2,
                    "page_end": 3,
                    "bbox": [10, 30, 100, 70],
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.PDF)
        assert len(sections) == 2
        assert sections[0]["level"] == 1
        assert sections[1]["level"] == 2

    def test_pdf_content_position_detection(self) -> None:
        """Test PDF content position detection (start/middle/end)."""
        handler = PDFSectionHandler()

        # Section at start
        parsed_content_start = {
            "total_pages": 100,
            "sections": [
                {
                    "heading": "Preface",
                    "level": 1,
                    "text": "Content",
                    "page_no": 0,  # Page 0-24 is start (< 25%)
                },
            ],
        }
        sections = handler.extract_sections(parsed_content_start, DocumentType.PDF)
        assert sections[0]["metadata"].content_position == "start"

        # Section in middle
        parsed_content_middle = {
            "total_pages": 100,
            "sections": [
                {
                    "heading": "Main Content",
                    "level": 1,
                    "text": "Content",
                    "page_no": 50,  # Page 50 is middle (25-75%)
                },
            ],
        }
        sections = handler.extract_sections(parsed_content_middle, DocumentType.PDF)
        assert sections[0]["metadata"].content_position == "middle"

        # Section at end
        parsed_content_end = {
            "total_pages": 100,
            "sections": [
                {
                    "heading": "Conclusion",
                    "level": 1,
                    "text": "Content",
                    "page_no": 90,  # Page 90-99 is end (> 75%)
                },
            ],
        }
        sections = handler.extract_sections(parsed_content_end, DocumentType.PDF)
        assert sections[0]["metadata"].content_position == "end"

    def test_pdf_no_sections_empty_response(self) -> None:
        """Test PDF with no sections returns empty list."""
        handler = PDFSectionHandler()
        parsed_content = {
            "total_pages": 5,
            "sections": [],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.PDF)
        assert len(sections) == 0

    def test_pdf_missing_sections_key(self) -> None:
        """Test PDF parsed content without sections key."""
        handler = PDFSectionHandler()
        parsed_content = {
            "total_pages": 5,
            "text": "Full document text",
        }

        sections = handler.extract_sections(parsed_content, DocumentType.PDF)
        assert len(sections) == 0


# =============================================================================
# DOCX SECTION HANDLER TESTS
# =============================================================================


class TestDocxSectionHandler:
    """Test DOCX-specific section handling."""

    def test_handler_should_handle_docx(self) -> None:
        """Test that handler claims to handle DOCX documents."""
        handler = DocxSectionHandler()
        assert handler.should_handle(DocumentType.DOCX) is True

    def test_handler_should_not_handle_other_types(self) -> None:
        """Test that handler doesn't claim to handle other types."""
        handler = DocxSectionHandler()
        assert handler.should_handle(DocumentType.PDF) is False
        assert handler.should_handle(DocumentType.HTML) is False

    def test_extract_basic_docx_sections(self) -> None:
        """Test extracting basic DOCX sections with heading styles."""
        handler = DocxSectionHandler()
        parsed_content = {
            "sections": [
                {
                    "heading": "Introduction",
                    "level": 1,
                    "text": "Introduction text",
                    "style": "Heading 1",
                    "position": "start",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.DOCX)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Introduction"
        assert sections[0]["style"] == "Heading 1"
        assert sections[0]["metadata"].style == "Heading 1"

    def test_extract_docx_heading_hierarchy(self) -> None:
        """Test DOCX section heading hierarchy extraction."""
        handler = DocxSectionHandler()
        parsed_content = {
            "sections": [
                {
                    "heading": "Chapter 1",
                    "text": "Content",
                    "style": "Heading 1",
                    "position": "middle",
                },
                {
                    "heading": "Section 1.1",
                    "text": "Content",
                    "style": "Heading 2",
                    "position": "middle",
                },
                {
                    "heading": "Subsection 1.1.1",
                    "text": "Content",
                    "style": "Heading 3",
                    "position": "middle",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.DOCX)
        assert sections[0]["level"] == 1
        assert sections[1]["level"] == 2
        assert sections[2]["level"] == 3

    def test_extract_docx_custom_styles(self) -> None:
        """Test DOCX with heading styles up to Heading 6."""
        handler = DocxSectionHandler()
        for heading_num in range(1, 7):
            parsed_content = {
                "sections": [
                    {
                        "heading": f"Heading {heading_num}",
                        "text": "Content",
                        "style": f"Heading {heading_num}",
                        "position": "middle",
                    },
                ],
            }
            sections = handler.extract_sections(parsed_content, DocumentType.DOCX)
            assert sections[0]["level"] == heading_num

    def test_extract_docx_unknown_style(self) -> None:
        """Test DOCX with unknown/custom heading style."""
        handler = DocxSectionHandler()
        parsed_content = {
            "sections": [
                {
                    "heading": "Custom Section",
                    "text": "Content",
                    "style": "Custom Style",
                    "position": "middle",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.DOCX)
        assert sections[0]["level"] == 1  # Default to level 1


# =============================================================================
# HTML SECTION HANDLER TESTS
# =============================================================================


class TestHTMLSectionHandler:
    """Test HTML-specific section handling."""

    def test_handler_should_handle_html(self) -> None:
        """Test that handler claims to handle HTML documents."""
        handler = HTMLSectionHandler()
        assert handler.should_handle(DocumentType.HTML) is True

    def test_extract_html_heading_tags(self) -> None:
        """Test extracting HTML sections with heading tags."""
        handler = HTMLSectionHandler()
        parsed_content = {
            "sections": [
                {
                    "heading": "Page Title",
                    "text": "Main content",
                    "tag": "h1",
                    "position": "start",
                },
                {
                    "heading": "Section Title",
                    "text": "Section content",
                    "tag": "h2",
                    "position": "middle",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.HTML)
        assert len(sections) == 2
        assert sections[0]["tag"] == "h1"
        assert sections[1]["tag"] == "h2"

    def test_html_heading_level_extraction(self) -> None:
        """Test extracting heading levels from HTML tags."""
        handler = HTMLSectionHandler()

        for h_level in range(1, 7):
            parsed_content = {
                "sections": [
                    {
                        "heading": f"H{h_level} Content",
                        "text": "Content",
                        "tag": f"h{h_level}",
                        "position": "middle",
                    },
                ],
            }
            sections = handler.extract_sections(parsed_content, DocumentType.HTML)
            assert sections[0]["level"] == h_level

    def test_html_invalid_tag_level(self) -> None:
        """Test HTML with invalid or non-heading tags."""
        handler = HTMLSectionHandler()
        parsed_content = {
            "sections": [
                {
                    "heading": "Content",
                    "text": "Content",
                    "tag": "div",  # Not a heading tag
                    "position": "middle",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.HTML)
        assert sections[0]["level"] == 1  # Default to level 1

    def test_html_case_insensitive_tags(self) -> None:
        """Test that HTML tag parsing is case-insensitive."""
        handler = HTMLSectionHandler()

        for tag in ["h1", "H1", "H2", "h2"]:
            level = handler._extract_level_from_tag(tag)
            expected = int(tag[-1])
            assert level == expected


# =============================================================================
# MARKDOWN SECTION HANDLER TESTS
# =============================================================================


class TestMarkdownSectionHandler:
    """Test Markdown-specific section handling."""

    def test_handler_should_handle_markdown(self) -> None:
        """Test that handler claims to handle Markdown documents."""
        handler = MarkdownSectionHandler()
        assert handler.should_handle(DocumentType.MD) is True

    def test_extract_markdown_headers(self) -> None:
        """Test extracting Markdown sections with headers."""
        handler = MarkdownSectionHandler()
        parsed_content = {
            "sections": [
                {
                    "heading": "Main Title",
                    "level": 1,
                    "text": "Content",
                    "line_no": 1,
                    "position": "start",
                },
                {
                    "heading": "Section",
                    "level": 2,
                    "text": "Content",
                    "line_no": 10,
                    "position": "middle",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.MD)
        assert len(sections) == 2
        assert sections[0]["level"] == 1
        assert sections[1]["level"] == 2

    def test_markdown_line_number_tracking(self) -> None:
        """Test that Markdown preserves line numbers."""
        handler = MarkdownSectionHandler()
        parsed_content = {
            "sections": [
                {
                    "heading": "Header 1",
                    "level": 1,
                    "text": "Content",
                    "line_no": 1,
                    "position": "start",
                },
                {
                    "heading": "Header 2",
                    "level": 2,
                    "text": "Content",
                    "line_no": 42,
                    "position": "middle",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.MD)
        assert sections[0]["metadata"].line_no == 1
        assert sections[1]["metadata"].line_no == 42

    def test_markdown_multiple_levels(self) -> None:
        """Test Markdown with all header levels (1-6)."""
        handler = MarkdownSectionHandler()

        for level in range(1, 7):
            parsed_content = {
                "sections": [
                    {
                        "heading": f"Level {level}",
                        "level": level,
                        "text": "Content",
                        "position": "middle",
                    },
                ],
            }
            sections = handler.extract_sections(parsed_content, DocumentType.MD)
            assert sections[0]["level"] == level


# =============================================================================
# GENERIC SECTION HANDLER TESTS
# =============================================================================


class TestGenericSectionHandler:
    """Test fallback generic section handling."""

    def test_handler_should_handle_all_types(self) -> None:
        """Test that generic handler claims to handle all types."""
        handler = GenericSectionHandler()
        for doc_type in DocumentType:
            assert handler.should_handle(doc_type) is True

    def test_extract_generic_sections(self) -> None:
        """Test extracting sections with generic handler."""
        handler = GenericSectionHandler()
        parsed_content = {
            "sections": [
                {
                    "heading": "Section 1",
                    "level": 1,
                    "text": "Content 1",
                    "position": "start",
                },
                {
                    "heading": "Section 2",
                    "level": 1,
                    "text": "Content 2",
                    "position": "end",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.UNKNOWN)
        assert len(sections) == 2

    def test_generic_handler_creates_default_section(self) -> None:
        """Test that generic handler creates default section if none found."""
        handler = GenericSectionHandler()
        parsed_content = {
            "text": "Full document text",
        }

        sections = handler.extract_sections(parsed_content, DocumentType.TXT)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Document Content"
        assert sections[0]["level"] == 1

    def test_generic_handler_empty_content(self) -> None:
        """Test generic handler with empty content."""
        handler = GenericSectionHandler()
        parsed_content = {}

        sections = handler.extract_sections(parsed_content, DocumentType.UNKNOWN)
        assert len(sections) == 1  # Creates default section
        assert sections[0]["heading"] == "Document Content"


# =============================================================================
# SECTION HANDLER ROUTING TESTS
# =============================================================================


class TestSectionHandlerRouting:
    """Test get_section_handler routing logic."""

    def test_route_to_pdf_handler(self) -> None:
        """Test routing PDF to PDFSectionHandler."""
        handler = get_section_handler(DocumentType.PDF)
        assert isinstance(handler, PDFSectionHandler)

    def test_route_to_docx_handler(self) -> None:
        """Test routing DOCX to DocxSectionHandler."""
        handler = get_section_handler(DocumentType.DOCX)
        assert isinstance(handler, DocxSectionHandler)

    def test_route_to_html_handler(self) -> None:
        """Test routing HTML to HTMLSectionHandler."""
        handler = get_section_handler(DocumentType.HTML)
        assert isinstance(handler, HTMLSectionHandler)

    def test_route_to_markdown_handler(self) -> None:
        """Test routing Markdown to MarkdownSectionHandler."""
        handler = get_section_handler(DocumentType.MD)
        assert isinstance(handler, MarkdownSectionHandler)

    def test_route_unsupported_to_generic(self) -> None:
        """Test routing unsupported types to generic handler."""
        for doc_type in [DocumentType.TXT, DocumentType.XLSX, DocumentType.PPTX]:
            handler = get_section_handler(doc_type)
            assert isinstance(handler, GenericSectionHandler)

    def test_route_unknown_to_generic(self) -> None:
        """Test routing unknown type to generic handler."""
        handler = get_section_handler(DocumentType.UNKNOWN)
        assert isinstance(handler, GenericSectionHandler)

    def test_all_types_have_handler(self) -> None:
        """Test that all DocumentType values have a handler."""
        for doc_type in DocumentType:
            handler = get_section_handler(doc_type)
            assert isinstance(handler, SectionHandler)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestSectionHandlerIntegration:
    """Integration tests for section handlers with real-world scenarios."""

    def test_complete_pdf_extraction_workflow(self) -> None:
        """Test complete PDF section extraction workflow."""
        handler = get_section_handler(DocumentType.PDF)

        parsed_content = {
            "total_pages": 20,
            "sections": [
                {
                    "heading": "Preface",
                    "level": 1,
                    "text": "Preface content",
                    "page_no": 0,
                    "page_start": 0,
                    "page_end": 1,
                    "bbox": [10, 20, 100, 80],
                },
                {
                    "heading": "Chapter 1: Introduction",
                    "level": 1,
                    "text": "Introduction content",
                    "page_no": 2,
                    "page_start": 2,
                    "page_end": 5,
                    "bbox": [10, 20, 100, 80],
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.PDF)
        assert len(sections) == 2
        assert sections[0]["metadata"].page_no == 0
        assert sections[1]["metadata"].page_no == 2

    def test_complete_docx_extraction_workflow(self) -> None:
        """Test complete DOCX section extraction workflow."""
        handler = get_section_handler(DocumentType.DOCX)

        parsed_content = {
            "sections": [
                {
                    "heading": "Executive Summary",
                    "level": 1,
                    "text": "Summary text",
                    "style": "Heading 1",
                    "position": "start",
                },
                {
                    "heading": "Key Points",
                    "level": 2,
                    "text": "Key points text",
                    "style": "Heading 2",
                    "position": "middle",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.DOCX)
        assert len(sections) == 2
        assert sections[0]["metadata"].style == "Heading 1"

    def test_fallback_handler_for_unsupported_format(self) -> None:
        """Test that unsupported formats fall back to generic handler."""
        handler = get_section_handler(DocumentType.XLSX)
        assert isinstance(handler, GenericSectionHandler)

        # Should still work with generic extraction
        parsed_content = {
            "sections": [
                {
                    "heading": "Sheet 1",
                    "level": 1,
                    "text": "Data",
                    "position": "start",
                },
            ],
        }

        sections = handler.extract_sections(parsed_content, DocumentType.XLSX)
        assert len(sections) == 1
