"""Tests for page_image_renderer.py — PDF page rendering for VLM cross-validation.

Sprint 129.6c: Tests cover page rendering, page number conversion, and error handling.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_fitz():
    """Create a mock fitz module with required attributes."""
    mock_fitz = MagicMock()
    return mock_fitz


class TestRenderPageImage:
    """Tests for render_page_image()."""

    def test_render_page_basic(self):
        """Render page 1 of a 3-page PDF."""
        mock_fitz = _make_mock_fitz()
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=3)
        mock_fitz.open.return_value = mock_doc

        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"\x89PNG_FAKE_IMAGE_DATA"
        mock_pix.width = 1654
        mock_pix.height = 2339
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.Matrix.return_value = MagicMock()

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            from src.components.ingestion.page_image_renderer import render_page_image

            result = render_page_image("/path/to/test.pdf", page_no=1, dpi=200)

        assert result == b"\x89PNG_FAKE_IMAGE_DATA"
        mock_doc.__getitem__.assert_called_with(0)
        mock_doc.close.assert_called_once()

    def test_render_page_1based_to_0based(self):
        """Docling page_no=3 should access fitz page index=2."""
        mock_fitz = _make_mock_fitz()
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=5)
        mock_fitz.open.return_value = mock_doc

        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"PNG_DATA"
        mock_pix.width = 100
        mock_pix.height = 100
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.Matrix.return_value = MagicMock()

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            from src.components.ingestion.page_image_renderer import render_page_image

            render_page_image("/path/to/test.pdf", page_no=3)

        mock_doc.__getitem__.assert_called_with(2)  # 3 - 1 = 2

    def test_render_page_out_of_range(self):
        """Page number beyond document length raises ValueError."""
        mock_fitz = _make_mock_fitz()
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=3)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            from src.components.ingestion.page_image_renderer import render_page_image

            with pytest.raises(ValueError, match="Page 5 out of range"):
                render_page_image("/path/to/test.pdf", page_no=5)

        mock_doc.close.assert_called_once()

    def test_render_page_zero_raises(self):
        """Page number 0 (invalid for 1-based) raises ValueError."""
        mock_fitz = _make_mock_fitz()
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=3)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            from src.components.ingestion.page_image_renderer import render_page_image

            with pytest.raises(ValueError, match="Page 0 out of range"):
                render_page_image("/path/to/test.pdf", page_no=0)
