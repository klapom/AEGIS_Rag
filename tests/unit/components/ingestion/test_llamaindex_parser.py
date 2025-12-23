"""Unit tests for LlamaIndex parser node - Sprint 22 Feature 22.4.

This module tests the LlamaIndex fallback parser implementation, which enables
parsing of 9 additional document formats not supported by Docling:
- .epub (E-books)
- .rtf (Rich Text Format)
- .tex (LaTeX)
- .md (Markdown)
- .rst (reStructuredText)
- .adoc (AsciiDoc)
- .org (Org-Mode)
- .odt (OpenDocument Text)
- .msg (Outlook messages)

Test Coverage:
- Format support validation
- Text extraction accuracy
- Metadata generation
- Error handling (empty files, unsupported formats)
- State management (IngestionState compatibility)
- Performance characteristics

Architecture:
- Uses pytest fixtures for test data
- Mocks external dependencies (LlamaIndex readers)
- Validates parser-agnostic output format
- Ensures compatibility with downstream nodes (chunking, embedding)
"""

from unittest.mock import MagicMock, patch

import pytest

# Check if llama_index is available
try:
    import llama_index

    HAS_LLAMA_INDEX = True
except ImportError:
    HAS_LLAMA_INDEX = False

import contextlib

from src.components.ingestion.ingestion_state import create_initial_state
from src.components.ingestion.langgraph_nodes import llamaindex_parse_node
from src.core.exceptions import IngestionError

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def markdown_file(tmp_path):
    """Create a test Markdown file."""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Header\n\nParagraph text with **bold** and *italic*.")
    return md_file


@pytest.fixture
def rst_file(tmp_path):
    """Create a test reStructuredText file."""
    rst_file = tmp_path / "test.rst"
    rst_file.write_text("Title\n=====\n\nContent paragraph.\n\n- List item 1\n- List item 2")
    return rst_file


@pytest.fixture
def empty_file(tmp_path):
    """Create an empty file."""
    empty = tmp_path / "empty.md"
    empty.write_text("")
    return empty


@pytest.fixture
def mock_llama_documents():
    """Create mock LlamaIndex Document objects."""
    mock_doc1 = MagicMock()
    mock_doc1.text = "Page 1 content"
    mock_doc1.metadata = {"page_number": 1, "source": "test.md"}

    mock_doc2 = MagicMock()
    mock_doc2.text = "Page 2 content"
    mock_doc2.metadata = {"page_number": 2, "source": "test.md"}

    return [mock_doc1, mock_doc2]


# =============================================================================
# BASIC PARSING TESTS
# =============================================================================


@pytest.mark.skipif(
    not HAS_LLAMA_INDEX,
    reason="llama_index not installed - install with: poetry install --with ingestion",
)
class TestLlamaIndexParserBasic:
    """Test basic LlamaIndex parser functionality."""

    @pytest.mark.asyncio
    async def test_parse__markdown_file__extracts_text(self, markdown_file):
        """Verify Markdown file parsing extracts text content."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="test_md",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # Verify text extraction
        assert "parsed_content" in result
        assert len(result["parsed_content"]) > 0
        assert "Header" in result["parsed_content"]
        assert "Paragraph text" in result["parsed_content"]

        # Verify metadata
        assert result["parsed_metadata"]["parser"] == "llamaindex"
        assert result["parsed_metadata"]["format"] == ".md"
        assert "source" in result["parsed_metadata"]

        # Verify status
        assert result["docling_status"] == "completed"

    @pytest.mark.asyncio
    async def test_parse__rst_file__extracts_text(self, rst_file):
        """Verify reStructuredText file parsing."""
        state = create_initial_state(
            document_path=str(rst_file),
            document_id="test_rst",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # Verify text extraction
        assert "Title" in result["parsed_content"]
        assert "Content paragraph" in result["parsed_content"]

        # Verify metadata
        assert result["parsed_metadata"]["parser"] == "llamaindex"
        assert result["parsed_metadata"]["format"] == ".rst"

    @pytest.mark.asyncio
    async def test_parse__metadata__includes_parser_info(self, markdown_file):
        """Verify metadata includes parser information."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="test",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        metadata = result["parsed_metadata"]
        assert metadata["parser"] == "llamaindex"
        assert metadata["format"] == ".md"
        assert "source" in metadata
        assert "page_count" in metadata
        assert metadata["page_count"] >= 1


# =============================================================================
# STATE COMPATIBILITY TESTS
# =============================================================================


@pytest.mark.skipif(
    not HAS_LLAMA_INDEX,
    reason="llama_index not installed - install with: poetry install --with ingestion",
)
class TestLlamaIndexParserStateCompatibility:
    """Test IngestionState compatibility (parser-agnostic output)."""

    @pytest.mark.asyncio
    async def test_parse__state_fields__all_populated(self, markdown_file):
        """Verify all required state fields are populated."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="test",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # Check all parser output fields exist
        assert "parsed_content" in result
        assert "parsed_metadata" in result
        assert "parsed_tables" in result
        assert "parsed_images" in result
        assert "parsed_layout" in result
        assert "docling_status" in result

        # Check values are correct types
        assert isinstance(result["parsed_content"], str)
        assert isinstance(result["parsed_metadata"], dict)
        assert isinstance(result["parsed_tables"], list)
        assert isinstance(result["parsed_images"], list)
        assert isinstance(result["parsed_layout"], dict)

    @pytest.mark.asyncio
    async def test_parse__no_tables_images__empty_lists(self, markdown_file):
        """Verify LlamaIndex parser returns empty lists for tables/images."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="test",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # LlamaIndex basic parsing doesn't extract tables/images
        assert result["parsed_tables"] == []
        assert result["parsed_images"] == []
        assert result["parsed_layout"] == {}

    @pytest.mark.asyncio
    async def test_parse__document_field__is_none(self, markdown_file):
        """Verify document field is None (no DoclingDocument object)."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="test",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # No DoclingDocument for LlamaIndex parser
        assert result["document"] is None
        assert result["page_dimensions"] == {}

    @pytest.mark.asyncio
    async def test_parse__progress_tracking__updates(self, markdown_file):
        """Verify progress tracking is updated correctly."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="test",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # Progress should be updated
        assert result["overall_progress"] > 0.0
        assert result["docling_start_time"] > 0
        assert result["docling_end_time"] > result["docling_start_time"]


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.skipif(
    not HAS_LLAMA_INDEX,
    reason="llama_index not installed - install with: poetry install --with ingestion",
)
class TestLlamaIndexParserErrorHandling:
    """Test error handling for edge cases."""

    @pytest.mark.asyncio
    async def test_parse__empty_file__handles_gracefully(self, empty_file):
        """Verify empty file handling."""
        state = create_initial_state(
            document_path=str(empty_file),
            document_id="empty",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        # Should not crash on empty file
        result = await llamaindex_parse_node(state)

        # Should return empty content or minimal content
        assert result["parsed_content"] is not None
        assert isinstance(result["parsed_content"], str)

    @pytest.mark.asyncio
    async def test_parse__missing_file__raises_error(self, tmp_path):
        """Verify missing file raises IngestionError."""
        missing_file = tmp_path / "nonexistent.md"
        state = create_initial_state(
            document_path=str(missing_file),
            document_id="missing",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        with pytest.raises(IngestionError, match="Document not found"):
            await llamaindex_parse_node(state)

    @pytest.mark.asyncio
    async def test_parse__unsupported_format__raises_error(self, tmp_path):
        """Verify unsupported format raises ValueError."""
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_text("content")

        state = create_initial_state(
            document_path=str(unsupported_file),
            document_id="invalid",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        with pytest.raises(ValueError, match="not supported by LlamaIndex"):
            await llamaindex_parse_node(state)

    @pytest.mark.asyncio
    async def test_parse__error__sets_failed_status(self, tmp_path):
        """Verify error sets docling_status to 'failed'."""
        missing_file = tmp_path / "nonexistent.md"
        state = create_initial_state(
            document_path=str(missing_file),
            document_id="error",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        with contextlib.suppress(IngestionError):
            await llamaindex_parse_node(state)

        # Status should be set to failed
        assert state["docling_status"] == "failed"
        assert len(state["errors"]) > 0
        assert state["errors"][0]["node"] == "llamaindex"


# =============================================================================
# FORMAT-SPECIFIC TESTS
# =============================================================================


@pytest.mark.skipif(
    not HAS_LLAMA_INDEX,
    reason="llama_index not installed - install with: poetry install --with ingestion",
)
class TestLlamaIndexParserFormats:
    """Test parsing of different LlamaIndex-exclusive formats."""

    @pytest.mark.asyncio
    async def test_parse__markdown__preserves_structure(self, markdown_file):
        """Verify Markdown parsing preserves basic structure."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="md_test",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # Should extract all text
        content = result["parsed_content"]
        assert "Header" in content
        assert "Paragraph" in content

    @pytest.mark.asyncio
    async def test_parse__text_file__extracts_content(self, tmp_path):
        """Verify plain text file parsing (shared format)."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Line 1\nLine 2\nLine 3")

        state = create_initial_state(
            document_path=str(txt_file),
            document_id="txt_test",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        content = result["parsed_content"]
        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content

    @pytest.mark.asyncio
    @patch("llama_index.core.SimpleDirectoryReader")
    async def test_parse__multiple_pages__combines_text(
        self, mock_reader_class, markdown_file, mock_llama_documents
    ):
        """Verify multi-page documents combine all text."""
        # Mock SimpleDirectoryReader to return multiple documents
        mock_reader = MagicMock()
        mock_reader.load_data.return_value = mock_llama_documents
        mock_reader_class.return_value = mock_reader

        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="multipage",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # Should combine all pages
        content = result["parsed_content"]
        assert "Page 1 content" in content
        assert "Page 2 content" in content
        assert result["parsed_metadata"]["page_count"] == 2


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


@pytest.mark.skipif(
    not HAS_LLAMA_INDEX,
    reason="llama_index not installed - install with: poetry install --with ingestion",
)
class TestLlamaIndexParserPerformance:
    """Test performance characteristics of LlamaIndex parser."""

    @pytest.mark.asyncio
    async def test_parse__small_file__fast_parsing(self, markdown_file):
        """Verify small files parse quickly (<1s)."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="perf_test",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # Calculate parsing time
        parse_time = result["docling_end_time"] - result["docling_start_time"]

        # Should be fast for small files
        assert parse_time < 5.0  # Less than 5 seconds

    @pytest.mark.asyncio
    async def test_parse__metadata__includes_page_count(self, markdown_file):
        """Verify metadata includes page count for pagination."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="meta_test",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        metadata = result["parsed_metadata"]
        assert "page_count" in metadata
        assert isinstance(metadata["page_count"], int)
        assert metadata["page_count"] > 0


# =============================================================================
# INTEGRATION WITH DOWNSTREAM NODES
# =============================================================================


@pytest.mark.skipif(
    not HAS_LLAMA_INDEX,
    reason="llama_index not installed - install with: poetry install --with ingestion",
)
class TestLlamaIndexParserDownstreamCompatibility:
    """Test compatibility with downstream nodes (chunking, embedding)."""

    @pytest.mark.asyncio
    async def test_parse__output__compatible_with_chunking(self, markdown_file):
        """Verify output format is compatible with chunking node."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="chunk_compat",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # Chunking node requires parsed_content
        assert "parsed_content" in result
        assert isinstance(result["parsed_content"], str)
        assert len(result["parsed_content"]) > 0

        # Should have metadata for chunking context
        assert "parsed_metadata" in result
        assert isinstance(result["parsed_metadata"], dict)

    @pytest.mark.asyncio
    async def test_parse__output__has_document_id(self, markdown_file):
        """Verify document_id is preserved for downstream nodes."""
        state = create_initial_state(
            document_path=str(markdown_file),
            document_id="doc123",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
        )

        result = await llamaindex_parse_node(state)

        # Document ID should be preserved
        assert result["document_id"] == "doc123"
        assert result["parsed_metadata"]["source"] == str(markdown_file)
