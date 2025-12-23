"""Unit Tests for Document Type Support - Feature 62.7.

Tests for:
- Document type detection from file path and MIME type
- Section metadata models
- Document type enum and mappings
- Edge cases and error handling

Coverage target: >80%
"""

import pytest
from pathlib import Path

from src.domains.document_processing.document_types import (
    DocumentType,
    SectionMetadata,
    detect_document_type,
    get_document_type_description,
    EXTENSION_TO_TYPE,
    MIME_TO_TYPE,
)


# =============================================================================
# DOCUMENT TYPE ENUM TESTS
# =============================================================================


class TestDocumentTypeEnum:
    """Test DocumentType enum and values."""

    def test_all_document_types_exist(self) -> None:
        """Test that all required document types exist."""
        required_types = ["PDF", "DOCX", "HTML", "MD", "TXT", "XLSX", "PPTX", "UNKNOWN"]
        for type_name in required_types:
            assert hasattr(DocumentType, type_name)

    def test_document_type_values(self) -> None:
        """Test document type enum values."""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.DOCX.value == "docx"
        assert DocumentType.HTML.value == "html"
        assert DocumentType.MD.value == "markdown"
        assert DocumentType.TXT.value == "text"
        assert DocumentType.XLSX.value == "xlsx"
        assert DocumentType.PPTX.value == "pptx"
        assert DocumentType.UNKNOWN.value == "unknown"

    def test_document_type_string_conversion(self) -> None:
        """Test converting string to DocumentType."""
        assert DocumentType("pdf") == DocumentType.PDF
        assert DocumentType("docx") == DocumentType.DOCX
        assert DocumentType("html") == DocumentType.HTML

    def test_invalid_document_type(self) -> None:
        """Test that invalid type raises error."""
        with pytest.raises(ValueError):
            DocumentType("invalid")


# =============================================================================
# DOCUMENT TYPE MAPPING TESTS
# =============================================================================


class TestDocumentTypeMapping:
    """Test file extension and MIME type mappings."""

    def test_extension_mapping_pdf(self) -> None:
        """Test PDF file extension mappings."""
        assert EXTENSION_TO_TYPE[".pdf"] == DocumentType.PDF

    def test_extension_mapping_docx(self) -> None:
        """Test DOCX file extension mappings."""
        assert EXTENSION_TO_TYPE[".docx"] == DocumentType.DOCX
        assert EXTENSION_TO_TYPE[".doc"] == DocumentType.DOCX  # Legacy support

    def test_extension_mapping_html(self) -> None:
        """Test HTML file extension mappings."""
        assert EXTENSION_TO_TYPE[".html"] == DocumentType.HTML
        assert EXTENSION_TO_TYPE[".htm"] == DocumentType.HTML
        assert EXTENSION_TO_TYPE[".xhtml"] == DocumentType.HTML
        assert EXTENSION_TO_TYPE[".mhtml"] == DocumentType.HTML

    def test_extension_mapping_markdown(self) -> None:
        """Test Markdown file extension mappings."""
        assert EXTENSION_TO_TYPE[".md"] == DocumentType.MD
        assert EXTENSION_TO_TYPE[".markdown"] == DocumentType.MD
        assert EXTENSION_TO_TYPE[".mdown"] == DocumentType.MD

    def test_extension_mapping_text(self) -> None:
        """Test text file extension mappings."""
        assert EXTENSION_TO_TYPE[".txt"] == DocumentType.TXT
        assert EXTENSION_TO_TYPE[".text"] == DocumentType.TXT

    def test_extension_mapping_xlsx(self) -> None:
        """Test Excel file extension mappings."""
        assert EXTENSION_TO_TYPE[".xlsx"] == DocumentType.XLSX
        assert EXTENSION_TO_TYPE[".xls"] == DocumentType.XLSX  # Legacy support
        assert EXTENSION_TO_TYPE[".csv"] == DocumentType.XLSX

    def test_extension_mapping_pptx(self) -> None:
        """Test PowerPoint file extension mappings."""
        assert EXTENSION_TO_TYPE[".pptx"] == DocumentType.PPTX
        assert EXTENSION_TO_TYPE[".ppt"] == DocumentType.PPTX  # Legacy support

    def test_mime_type_mapping_pdf(self) -> None:
        """Test PDF MIME type mapping."""
        assert MIME_TO_TYPE["application/pdf"] == DocumentType.PDF

    def test_mime_type_mapping_docx(self) -> None:
        """Test DOCX MIME type mappings."""
        assert (
            MIME_TO_TYPE[
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # noqa: E501
            ]
            == DocumentType.DOCX
        )
        assert MIME_TO_TYPE["application/msword"] == DocumentType.DOCX

    def test_mime_type_mapping_html(self) -> None:
        """Test HTML MIME type mappings."""
        assert MIME_TO_TYPE["text/html"] == DocumentType.HTML
        assert MIME_TO_TYPE["application/xhtml+xml"] == DocumentType.HTML

    def test_mime_type_mapping_markdown(self) -> None:
        """Test Markdown MIME type mapping."""
        assert MIME_TO_TYPE["text/markdown"] == DocumentType.MD

    def test_mime_type_mapping_text(self) -> None:
        """Test text MIME type mapping."""
        assert MIME_TO_TYPE["text/plain"] == DocumentType.TXT

    def test_mime_type_mapping_xlsx(self) -> None:
        """Test Excel MIME type mappings."""
        assert (
            MIME_TO_TYPE[
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  # noqa: E501
            ]
            == DocumentType.XLSX
        )
        assert MIME_TO_TYPE["application/vnd.ms-excel"] == DocumentType.XLSX
        assert MIME_TO_TYPE["text/csv"] == DocumentType.XLSX

    def test_mime_type_mapping_pptx(self) -> None:
        """Test PowerPoint MIME type mappings."""
        assert (
            MIME_TO_TYPE[
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"  # noqa: E501
            ]
            == DocumentType.PPTX
        )
        assert MIME_TO_TYPE["application/vnd.ms-powerpoint"] == DocumentType.PPTX


# =============================================================================
# DOCUMENT TYPE DETECTION TESTS
# =============================================================================


class TestDocumentTypeDetection:
    """Test detect_document_type function."""

    def test_detect_pdf_from_extension(self) -> None:
        """Test detecting PDF from file extension."""
        doc_type = detect_document_type(Path("report.pdf"))
        assert doc_type == DocumentType.PDF

    def test_detect_docx_from_extension(self) -> None:
        """Test detecting DOCX from file extension."""
        doc_type = detect_document_type(Path("document.docx"))
        assert doc_type == DocumentType.DOCX

    def test_detect_html_from_extension(self) -> None:
        """Test detecting HTML from file extension."""
        assert detect_document_type(Path("page.html")) == DocumentType.HTML
        assert detect_document_type(Path("page.htm")) == DocumentType.HTML

    def test_detect_markdown_from_extension(self) -> None:
        """Test detecting Markdown from file extension."""
        assert detect_document_type(Path("README.md")) == DocumentType.MD
        assert detect_document_type(Path("guide.markdown")) == DocumentType.MD

    def test_detect_text_from_extension(self) -> None:
        """Test detecting TXT from file extension."""
        assert detect_document_type(Path("notes.txt")) == DocumentType.TXT

    def test_detect_xlsx_from_extension(self) -> None:
        """Test detecting XLSX from file extension."""
        assert detect_document_type(Path("data.xlsx")) == DocumentType.XLSX
        assert detect_document_type(Path("data.csv")) == DocumentType.XLSX

    def test_detect_pptx_from_extension(self) -> None:
        """Test detecting PPTX from file extension."""
        assert detect_document_type(Path("presentation.pptx")) == DocumentType.PPTX

    def test_detect_from_mime_type_priority(self) -> None:
        """Test that MIME type has priority over extension."""
        # File has .bin extension but MIME type is PDF
        doc_type = detect_document_type(Path("unknown.bin"), mime_type="application/pdf")
        assert doc_type == DocumentType.PDF

    def test_detect_mime_type_case_insensitive(self) -> None:
        """Test that MIME type detection is case-insensitive."""
        doc_type = detect_document_type(
            Path("file.bin"), mime_type="APPLICATION/PDF"
        )
        assert doc_type == DocumentType.PDF

    def test_detect_extension_case_insensitive(self) -> None:
        """Test that extension detection is case-insensitive."""
        assert detect_document_type(Path("file.PDF")) == DocumentType.PDF
        assert detect_document_type(Path("file.Pdf")) == DocumentType.PDF
        assert detect_document_type(Path("file.DOCX")) == DocumentType.DOCX

    def test_detect_unknown_extension(self) -> None:
        """Test detecting unknown file extension."""
        doc_type = detect_document_type(Path("file.xyz"))
        assert doc_type == DocumentType.UNKNOWN

    def test_detect_unknown_with_fallback_mime(self) -> None:
        """Test fallback when MIME type is unknown."""
        doc_type = detect_document_type(
            Path("file.xyz"), mime_type="application/unknown"
        )
        assert doc_type == DocumentType.UNKNOWN

    def test_detect_with_paths(self) -> None:
        """Test detection with various path formats."""
        # Absolute path
        assert (
            detect_document_type(Path("/home/user/documents/report.pdf"))
            == DocumentType.PDF
        )
        # Relative path
        assert detect_document_type(Path("../docs/guide.md")) == DocumentType.MD
        # Nested path
        assert (
            detect_document_type(Path("folder/subfolder/file.docx"))
            == DocumentType.DOCX
        )

    def test_detect_legacy_formats(self) -> None:
        """Test detection of legacy formats (treated as modern equivalents)."""
        assert detect_document_type(Path("file.doc")) == DocumentType.DOCX
        assert detect_document_type(Path("file.xls")) == DocumentType.XLSX
        assert detect_document_type(Path("file.ppt")) == DocumentType.PPTX


# =============================================================================
# SECTION METADATA TESTS
# =============================================================================


class TestSectionMetadata:
    """Test SectionMetadata model."""

    def test_create_basic_section_metadata(self) -> None:
        """Test creating basic section metadata."""
        metadata = SectionMetadata(
            heading="Introduction",
            level=1,
            document_type=DocumentType.PDF,
        )
        assert metadata.heading == "Introduction"
        assert metadata.level == 1
        assert metadata.document_type == DocumentType.PDF
        assert metadata.page_no is None
        assert metadata.bbox is None

    def test_create_pdf_section_metadata(self) -> None:
        """Test creating PDF section metadata with page numbers."""
        metadata = SectionMetadata(
            heading="Chapter 1",
            level=1,
            document_type=DocumentType.PDF,
            page_no=5,
            page_start=5,
            page_end=15,
            bbox=[10.5, 20.3, 100.5, 80.2],
        )
        assert metadata.heading == "Chapter 1"
        assert metadata.page_no == 5
        assert metadata.page_start == 5
        assert metadata.page_end == 15
        assert metadata.bbox == [10.5, 20.3, 100.5, 80.2]

    def test_create_docx_section_metadata(self) -> None:
        """Test creating DOCX section metadata with style."""
        metadata = SectionMetadata(
            heading="Section Title",
            level=1,
            document_type=DocumentType.DOCX,
            style="Heading 1",
        )
        assert metadata.heading == "Section Title"
        assert metadata.style == "Heading 1"

    def test_create_markdown_section_metadata(self) -> None:
        """Test creating Markdown section metadata with line number."""
        metadata = SectionMetadata(
            heading="Overview",
            level=2,
            document_type=DocumentType.MD,
            line_no=42,
        )
        assert metadata.heading == "Overview"
        assert metadata.level == 2
        assert metadata.line_no == 42

    def test_section_metadata_to_dict(self) -> None:
        """Test converting section metadata to dictionary."""
        metadata = SectionMetadata(
            heading="Chapter",
            level=1,
            document_type=DocumentType.PDF,
            page_no=3,
        )
        data = metadata.to_dict()
        assert data["heading"] == "Chapter"
        assert data["level"] == 1
        assert data["document_type"] == "pdf"
        assert data["page_no"] == 3

    def test_section_metadata_from_dict(self) -> None:
        """Test creating section metadata from dictionary."""
        data = {
            "heading": "Introduction",
            "level": 1,
            "document_type": "pdf",
            "page_no": 1,
            "page_start": 1,
            "page_end": 5,
        }
        metadata = SectionMetadata.from_dict(data)
        assert metadata.heading == "Introduction"
        assert metadata.level == 1
        assert metadata.document_type == DocumentType.PDF
        assert metadata.page_no == 1

    def test_section_metadata_from_dict_with_invalid_type(self) -> None:
        """Test creating from dict with invalid document type."""
        data = {
            "heading": "Section",
            "level": 1,
            "document_type": "invalid_type",
        }
        metadata = SectionMetadata.from_dict(data)
        assert metadata.document_type == DocumentType.UNKNOWN

    def test_section_metadata_round_trip(self) -> None:
        """Test round-trip conversion (to_dict -> from_dict)."""
        original = SectionMetadata(
            heading="Test Section",
            level=2,
            document_type=DocumentType.HTML,
            style="h2",
        )
        data = original.to_dict()
        restored = SectionMetadata.from_dict(data)
        assert restored.heading == original.heading
        assert restored.level == original.level
        assert restored.document_type == original.document_type
        assert restored.style == original.style

    def test_section_metadata_content_position(self) -> None:
        """Test content position tracking."""
        start = SectionMetadata(
            heading="Start", level=1, document_type=DocumentType.PDF,
            content_position="start"
        )
        middle = SectionMetadata(
            heading="Middle", level=1, document_type=DocumentType.PDF,
            content_position="middle"
        )
        end = SectionMetadata(
            heading="End", level=1, document_type=DocumentType.PDF,
            content_position="end"
        )
        assert start.content_position == "start"
        assert middle.content_position == "middle"
        assert end.content_position == "end"


# =============================================================================
# DOCUMENT TYPE DESCRIPTION TESTS
# =============================================================================


class TestDocumentTypeDescription:
    """Test get_document_type_description function."""

    def test_pdf_description(self) -> None:
        """Test PDF type description."""
        desc = get_document_type_description(DocumentType.PDF)
        assert "Portable Document Format" in desc
        assert "page numbers" in desc

    def test_docx_description(self) -> None:
        """Test DOCX type description."""
        desc = get_document_type_description(DocumentType.DOCX)
        assert "Microsoft Word" in desc
        assert "heading styles" in desc

    def test_html_description(self) -> None:
        """Test HTML type description."""
        desc = get_document_type_description(DocumentType.HTML)
        assert "HTML" in desc
        assert "heading tags" in desc

    def test_markdown_description(self) -> None:
        """Test Markdown type description."""
        desc = get_document_type_description(DocumentType.MD)
        assert "Markdown" in desc
        assert "markdown headers" in desc

    def test_text_description(self) -> None:
        """Test text type description."""
        desc = get_document_type_description(DocumentType.TXT)
        assert "Plain text" in desc

    def test_xlsx_description(self) -> None:
        """Test Excel type description."""
        desc = get_document_type_description(DocumentType.XLSX)
        assert "Excel" in desc
        assert "spreadsheet" in desc

    def test_pptx_description(self) -> None:
        """Test PowerPoint type description."""
        desc = get_document_type_description(DocumentType.PPTX)
        assert "PowerPoint" in desc

    def test_unknown_description(self) -> None:
        """Test unknown type description."""
        desc = get_document_type_description(DocumentType.UNKNOWN)
        assert "unknown" in desc.lower() or "unsupported" in desc.lower()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestDocumentTypeIntegration:
    """Integration tests for document type detection and metadata."""

    def test_pdf_document_workflow(self) -> None:
        """Test complete PDF document type workflow."""
        # Detect type
        doc_type = detect_document_type(Path("document.pdf"))
        assert doc_type == DocumentType.PDF

        # Create section metadata
        metadata = SectionMetadata(
            heading="Page 1",
            level=1,
            document_type=doc_type,
            page_no=0,
        )

        # Convert to/from dict
        data = metadata.to_dict()
        restored = SectionMetadata.from_dict(data)

        assert restored.document_type == DocumentType.PDF
        assert restored.heading == "Page 1"

    def test_docx_document_workflow(self) -> None:
        """Test complete DOCX document type workflow."""
        doc_type = detect_document_type(Path("report.docx"))
        assert doc_type == DocumentType.DOCX

        metadata = SectionMetadata(
            heading="Section 1",
            level=1,
            document_type=doc_type,
            style="Heading 1",
        )

        data = metadata.to_dict()
        restored = SectionMetadata.from_dict(data)

        assert restored.document_type == DocumentType.DOCX
        assert restored.style == "Heading 1"

    def test_multiple_format_detection(self) -> None:
        """Test detecting multiple document formats."""
        formats = {
            "file.pdf": DocumentType.PDF,
            "file.docx": DocumentType.DOCX,
            "file.html": DocumentType.HTML,
            "file.md": DocumentType.MD,
            "file.txt": DocumentType.TXT,
            "file.xlsx": DocumentType.XLSX,
            "file.pptx": DocumentType.PPTX,
        }

        for filename, expected_type in formats.items():
            detected_type = detect_document_type(Path(filename))
            assert detected_type == expected_type

    def test_mime_type_override(self) -> None:
        """Test that MIME type detection overrides extension."""
        # File has HTML extension but MIME says it's PDF
        doc_type = detect_document_type(
            Path("file.html"), mime_type="application/pdf"
        )
        assert doc_type == DocumentType.PDF

        # Verify we can create appropriate metadata
        metadata = SectionMetadata(
            heading="Content",
            level=1,
            document_type=doc_type,
        )
        assert metadata.document_type == DocumentType.PDF
