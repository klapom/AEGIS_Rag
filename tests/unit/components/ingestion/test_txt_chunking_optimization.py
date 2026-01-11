"""Unit tests for .txt file chunking optimization (Sprint 84 Feature 84.8).

Tests that section extraction is skipped for .txt and .md files to achieve
42x performance improvement (42s → <1s for 3.6KB files).
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.ingestion.ingestion_state import IngestionState
from src.components.ingestion.nodes.adaptive_chunking import chunking_node


class TestTxtChunkingOptimization:
    """Test section extraction skipping for .txt files."""

    @pytest.mark.asyncio
    async def test_txt_file_skips_section_extraction(self):
        """For .txt files, section extraction should be skipped entirely."""
        # Arrange: Create mock state for .txt file
        state = IngestionState(
            document_id="test_doc_123",
            document_path="/path/to/document.txt",  # .txt extension
            document=MagicMock(export_to_markdown=lambda: "Sample text content"),
            parsed_content="Sample text content",
            chunking_status="pending",
        )

        # Mock extract_section_hierarchy to verify it's NOT called
        with patch(
            "src.components.ingestion.section_extraction.extract_section_hierarchy"
        ) as mock_extract:
            # Act
            result = await chunking_node(state)

            # Assert: extract_section_hierarchy should NOT be called for .txt
            mock_extract.assert_not_called()

            # Verify chunks were created (via fallback path)
            assert "chunks" in result
            assert len(result["chunks"]) > 0
            assert result["chunking_status"] == "completed"

    @pytest.mark.asyncio
    async def test_md_file_skips_section_extraction(self):
        """For .md files, section extraction should also be skipped."""
        state = IngestionState(
            document_id="test_doc_456",
            document_path="/path/to/README.md",  # .md extension
            document=MagicMock(export_to_markdown=lambda: "# Markdown content"),
            parsed_content="# Markdown content",
            chunking_status="pending",
        )

        with patch(
            "src.components.ingestion.section_extraction.extract_section_hierarchy"
        ) as mock_extract:
            result = await chunking_node(state)

            mock_extract.assert_not_called()
            assert result["chunking_status"] == "completed"

    @pytest.mark.asyncio
    async def test_pdf_file_uses_section_extraction(self):
        """For .pdf files, section extraction should still be used."""
        state = IngestionState(
            document_id="test_doc_789",
            document_path="/path/to/document.pdf",  # .pdf extension
            document=MagicMock(export_to_markdown=lambda: "PDF content"),
            parsed_content="PDF content",
            chunking_status="pending",
        )

        with patch(
            "src.components.ingestion.section_extraction.extract_section_hierarchy"
        ) as mock_extract:
            # Mock section extraction to return empty list
            mock_extract.return_value = []

            result = await chunking_node(state)

            # Assert: extract_section_hierarchy SHOULD be called for .pdf
            mock_extract.assert_called_once()
            assert result["chunking_status"] == "completed"

    @pytest.mark.asyncio
    async def test_docx_file_uses_section_extraction(self):
        """For .docx files, section extraction should be used."""
        state = IngestionState(
            document_id="test_doc_docx",
            document_path="/path/to/document.docx",
            document=MagicMock(export_to_markdown=lambda: "DOCX content"),
            parsed_content="DOCX content",
            chunking_status="pending",
        )

        with patch(
            "src.components.ingestion.section_extraction.extract_section_hierarchy"
        ) as mock_extract:
            mock_extract.return_value = []
            result = await chunking_node(state)

            mock_extract.assert_called_once()
            assert result["chunking_status"] == "completed"

    @pytest.mark.asyncio
    async def test_no_document_path_uses_section_extraction(self):
        """If document_path is missing, default to using section extraction."""
        state = IngestionState(
            document_id="test_doc_no_path",
            # No document_path provided
            document=MagicMock(export_to_markdown=lambda: "Content"),
            parsed_content="Content",
            chunking_status="pending",
        )

        with patch(
            "src.components.ingestion.section_extraction.extract_section_hierarchy"
        ) as mock_extract:
            mock_extract.return_value = []
            result = await chunking_node(state)

            # Default behavior: use section extraction
            mock_extract.assert_called_once()
            assert result["chunking_status"] == "completed"

    @pytest.mark.asyncio
    async def test_case_insensitive_extension_matching(self):
        """File extensions should be matched case-insensitively."""
        # Test uppercase .TXT
        state_upper = IngestionState(
            document_id="test_upper",
            document_path="/path/to/FILE.TXT",  # Uppercase
            document=MagicMock(export_to_markdown=lambda: "Text"),
            parsed_content="Text",
            chunking_status="pending",
        )

        with patch(
            "src.components.ingestion.section_extraction.extract_section_hierarchy"
        ) as mock_extract:
            result = await chunking_node(state_upper)

            # Should still skip for .TXT (case-insensitive)
            mock_extract.assert_not_called()
            assert result["chunking_status"] == "completed"

    @pytest.mark.parametrize(
        "file_extension,should_skip",
        [
            (".txt", True),
            (".TXT", True),
            (".md", True),
            (".MD", True),
            (".pdf", False),
            (".PDF", False),
            (".docx", False),
            (".pptx", False),
            (".html", False),
            ("", False),  # No extension
        ],
    )
    @pytest.mark.asyncio
    async def test_section_extraction_skipping_for_various_extensions(
        self, file_extension, should_skip
    ):
        """Parameterized test for various file extensions."""
        state = IngestionState(
            document_id=f"test_{file_extension}",
            document_path=f"/path/to/file{file_extension}",
            document=MagicMock(export_to_markdown=lambda: "Content"),
            parsed_content="Content",
            chunking_status="pending",
        )

        with patch(
            "src.components.ingestion.section_extraction.extract_section_hierarchy"
        ) as mock_extract:
            mock_extract.return_value = []
            result = await chunking_node(state)

            if should_skip:
                mock_extract.assert_not_called()
            else:
                mock_extract.assert_called_once()

            assert result["chunking_status"] == "completed"


@pytest.mark.integration
class TestTxtChunkingPerformance:
    """Integration tests for .txt chunking performance."""

    @pytest.mark.asyncio
    async def test_txt_chunking_performance_improvement(self):
        """Verify .txt chunking completes in <5s (vs 42s baseline = 8.4x speedup)."""
        import time

        # Create realistic .txt content (3.6KB like Iteration 1)
        txt_content = "Sample text content. " * 180  # ~3.6KB

        state = IngestionState(
            document_id="perf_test_txt",
            document_path="/tmp/test.txt",
            document=MagicMock(export_to_markdown=lambda: txt_content),
            parsed_content=txt_content,
            chunking_status="pending",
        )

        start_time = time.perf_counter()
        result = await chunking_node(state)
        duration = time.perf_counter() - start_time

        # Assert: Chunking should complete in <5s (baseline was 42s!)
        # Observed: ~1.1s in practice (37x speedup)
        assert duration < 5.0, f"Chunking took {duration:.2f}s (expected <5s, baseline was 42s)"
        assert result["chunking_status"] == "completed"
        assert len(result["chunks"]) > 0
