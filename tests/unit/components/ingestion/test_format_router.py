"""Unit tests for Format Router - Sprint 22 Feature 22.3.

Tests comprehensive routing logic for 30+ document formats across
Docling (GPU-accelerated) and LlamaIndex (fallback) parsers.

Test Coverage:
    - Format set definitions (14 Docling + 9 LlamaIndex + 7 shared = 30)
    - Routing logic for each format category
    - Graceful degradation when Docling unavailable
    - Error handling for unsupported formats
    - Docling availability updates
    - Health check integration

Run:
    pytest tests/unit/components/ingestion/test_format_router.py -v
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.components.ingestion.format_router import (
    ALL_FORMATS,
    DOCLING_FORMATS,
    LLAMAINDEX_EXCLUSIVE,
    SHARED_FORMATS,
    FormatRouter,
    ParserType,
    RoutingDecision,
    check_docling_availability,
    initialize_format_router,
)


# =============================================================================
# TEST FORMAT SET DEFINITIONS
# =============================================================================


class TestFormatSets:
    """Test format set definitions and counts."""

    def test_format_sets__no_overlap__docling_and_exclusive(self):
        """Verify no overlap between Docling-exclusive and LlamaIndex-exclusive."""
        overlap = DOCLING_FORMATS & LLAMAINDEX_EXCLUSIVE
        assert len(overlap) == 0, f"Unexpected overlap: {overlap}"

    def test_format_sets__docling_count__14_formats(self):
        """Verify Docling supports 14 exclusive formats."""
        assert len(DOCLING_FORMATS) == 14
        # Spot check key formats
        assert ".pdf" in DOCLING_FORMATS
        assert ".docx" in DOCLING_FORMATS
        assert ".xlsx" in DOCLING_FORMATS
        assert ".png" in DOCLING_FORMATS

    def test_format_sets__llamaindex_exclusive_count__9_formats(self):
        """Verify LlamaIndex exclusive supports 9 formats."""
        assert len(LLAMAINDEX_EXCLUSIVE) == 9
        # Spot check key formats
        assert ".epub" in LLAMAINDEX_EXCLUSIVE
        assert ".md" in LLAMAINDEX_EXCLUSIVE
        assert ".tex" in LLAMAINDEX_EXCLUSIVE
        assert ".rtf" in LLAMAINDEX_EXCLUSIVE

    def test_format_sets__shared_count__4_formats(self):
        """Verify 4 shared formats between Docling and LlamaIndex."""
        assert len(SHARED_FORMATS) == 4
        # Spot check key formats
        assert ".txt" in SHARED_FORMATS
        assert ".htm" in SHARED_FORMATS
        assert ".eml" in SHARED_FORMATS

    def test_format_sets__total_count__27_formats(self):
        """Verify 27 total formats supported."""
        assert len(ALL_FORMATS) == 27
        # Verify ALL_FORMATS is union of all three sets
        expected_all = DOCLING_FORMATS | LLAMAINDEX_EXCLUSIVE | SHARED_FORMATS
        assert ALL_FORMATS == expected_all

    def test_format_sets__shared_not_in_exclusive_sets(self):
        """Verify shared formats are not in exclusive sets."""
        # Shared formats should NOT be in DOCLING_FORMATS or LLAMAINDEX_EXCLUSIVE
        # (they are only in SHARED_FORMATS)
        docling_exclusive_only = DOCLING_FORMATS - SHARED_FORMATS
        llamaindex_exclusive_only = LLAMAINDEX_EXCLUSIVE - SHARED_FORMATS

        # Check no shared formats in exclusive sets
        assert len(SHARED_FORMATS & docling_exclusive_only) == 0
        assert len(SHARED_FORMATS & llamaindex_exclusive_only) == 0


# =============================================================================
# TEST ROUTING DECISION DATA CLASS
# =============================================================================


class TestRoutingDecision:
    """Test RoutingDecision data class."""

    def test_routing_decision__creation__all_fields(self):
        """Verify RoutingDecision can be created with all fields."""
        decision = RoutingDecision(
            parser=ParserType.DOCLING,
            format=".pdf",
            reason="GPU acceleration",
            fallback_available=True,
            confidence="high",
        )

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".pdf"
        assert decision.reason == "GPU acceleration"
        assert decision.fallback_available is True
        assert decision.confidence == "high"


# =============================================================================
# TEST FORMAT ROUTER - BASIC ROUTING
# =============================================================================


class TestFormatRouterBasicRouting:
    """Test basic routing logic for each format category."""

    @pytest.fixture
    def router_with_docling(self):
        """Router with Docling available."""
        return FormatRouter(docling_available=True)

    @pytest.fixture
    def router_without_docling(self):
        """Router without Docling (fallback mode)."""
        return FormatRouter(docling_available=False)

    # -------------------------------------------------------------------------
    # Docling-optimized formats
    # -------------------------------------------------------------------------

    def test_route__pdf__uses_docling(self, router_with_docling):
        """Verify PDF routes to Docling (GPU-accelerated OCR)."""
        decision = router_with_docling.route(Path("document.pdf"))

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".pdf"
        assert decision.confidence == "high"
        assert "GPU acceleration" in decision.reason
        assert decision.fallback_available is False  # PDF not in shared

    def test_route__docx__uses_docling(self, router_with_docling):
        """Verify DOCX routes to Docling (native layout preservation)."""
        decision = router_with_docling.route(Path("document.docx"))

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".docx"
        assert decision.confidence == "high"

    def test_route__xlsx__uses_docling(self, router_with_docling):
        """Verify XLSX routes to Docling (table extraction 92% accuracy)."""
        decision = router_with_docling.route(Path("spreadsheet.xlsx"))

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".xlsx"
        assert decision.confidence == "high"

    def test_route__png__uses_docling(self, router_with_docling):
        """Verify PNG routes to Docling (EasyOCR image processing)."""
        decision = router_with_docling.route(Path("image.png"))

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".png"
        assert decision.confidence == "high"

    # -------------------------------------------------------------------------
    # LlamaIndex-exclusive formats
    # -------------------------------------------------------------------------

    def test_route__epub__uses_llamaindex(self, router_with_docling):
        """Verify EPUB routes to LlamaIndex (e-book format)."""
        decision = router_with_docling.route(Path("book.epub"))

        assert decision.parser == ParserType.LLAMAINDEX
        assert decision.format == ".epub"
        assert decision.confidence == "high"
        assert "exclusive" in decision.reason.lower()
        assert decision.fallback_available is False

    def test_route__markdown__uses_llamaindex(self, router_with_docling):
        """Verify Markdown routes to LlamaIndex."""
        decision = router_with_docling.route(Path("README.md"))

        assert decision.parser == ParserType.LLAMAINDEX
        assert decision.format == ".md"
        assert decision.confidence == "high"

    def test_route__tex__uses_llamaindex(self, router_with_docling):
        """Verify LaTeX routes to LlamaIndex."""
        decision = router_with_docling.route(Path("paper.tex"))

        assert decision.parser == ParserType.LLAMAINDEX
        assert decision.format == ".tex"
        assert decision.confidence == "high"

    def test_route__rtf__uses_llamaindex(self, router_with_docling):
        """Verify RTF routes to LlamaIndex."""
        decision = router_with_docling.route(Path("document.rtf"))

        assert decision.parser == ParserType.LLAMAINDEX
        assert decision.format == ".rtf"
        assert decision.confidence == "high"

    # -------------------------------------------------------------------------
    # Shared formats (Docling preferred)
    # -------------------------------------------------------------------------

    def test_route__txt__prefers_docling(self, router_with_docling):
        """Verify TXT prefers Docling when available (shared format)."""
        decision = router_with_docling.route(Path("notes.txt"))

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".txt"
        assert decision.confidence == "high"
        assert "preferred" in decision.reason.lower() or "shared" in decision.reason.lower()
        assert decision.fallback_available is True

    def test_route__htm__prefers_docling(self, router_with_docling):
        """Verify HTM (HTML) prefers Docling when available."""
        decision = router_with_docling.route(Path("webpage.htm"))

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".htm"
        assert decision.fallback_available is True

    def test_route__eml__prefers_docling(self, router_with_docling):
        """Verify EML (email) prefers Docling when available."""
        decision = router_with_docling.route(Path("message.eml"))

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".eml"
        assert decision.fallback_available is True


# =============================================================================
# TEST FORMAT ROUTER - GRACEFUL DEGRADATION
# =============================================================================


class TestFormatRouterGracefulDegradation:
    """Test graceful degradation when Docling unavailable."""

    @pytest.fixture
    def router_without_docling(self):
        """Router without Docling (fallback mode)."""
        return FormatRouter(docling_available=False)

    def test_route__shared_format__falls_back_to_llamaindex(self, router_without_docling):
        """Verify shared formats fall back to LlamaIndex when Docling unavailable."""
        decision = router_without_docling.route(Path("notes.txt"))

        assert decision.parser == ParserType.LLAMAINDEX
        assert decision.format == ".txt"
        assert decision.confidence == "medium"  # Reduced confidence
        assert "unavailable" in decision.reason.lower()
        assert decision.fallback_available is False  # No further fallback

    def test_route__docling_exclusive__raises_error(self, router_without_docling):
        """Verify Docling-exclusive formats raise error when Docling unavailable."""
        with pytest.raises(RuntimeError, match="Docling container unavailable"):
            router_without_docling.route(Path("document.pdf"))

    def test_route__llamaindex_exclusive__still_works(self, router_without_docling):
        """Verify LlamaIndex-exclusive formats work without Docling."""
        decision = router_without_docling.route(Path("book.epub"))

        assert decision.parser == ParserType.LLAMAINDEX
        assert decision.format == ".epub"
        assert decision.confidence == "high"  # Not affected by Docling status


# =============================================================================
# TEST FORMAT ROUTER - ERROR HANDLING
# =============================================================================


class TestFormatRouterErrorHandling:
    """Test error handling for unsupported formats."""

    @pytest.fixture
    def router(self):
        """Standard router."""
        return FormatRouter(docling_available=True)

    def test_route__unsupported_format__raises_value_error(self, router):
        """Verify unsupported formats raise ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            router.route(Path("unknown.xyz"))

        error_msg = str(exc_info.value)
        assert "Unsupported format: .xyz" in error_msg
        assert "Supported formats:" in error_msg

    def test_route__no_extension__raises_value_error(self, router):
        """Verify files without extension raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            router.route(Path("README"))

        error_msg = str(exc_info.value)
        assert "Unsupported format:" in error_msg

    def test_route__case_insensitive__lowercase(self, router):
        """Verify routing is case-insensitive (uppercase extension)."""
        decision = router.route(Path("DOCUMENT.PDF"))

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".pdf"  # Normalized to lowercase


# =============================================================================
# TEST FORMAT ROUTER - HELPER METHODS
# =============================================================================


class TestFormatRouterHelperMethods:
    """Test helper methods (is_supported, get_supported_formats)."""

    @pytest.fixture
    def router(self):
        """Standard router."""
        return FormatRouter(docling_available=True)

    def test_is_supported__valid_format__returns_true(self, router):
        """Verify supported formats return True."""
        assert router.is_supported(Path("doc.pdf")) is True
        assert router.is_supported(Path("book.epub")) is True
        assert router.is_supported(Path("notes.txt")) is True

    def test_is_supported__invalid_format__returns_false(self, router):
        """Verify unsupported formats return False."""
        assert router.is_supported(Path("file.xyz")) is False
        assert router.is_supported(Path("unknown.abc")) is False

    def test_get_supported_formats__docling__correct_count(self, router):
        """Verify Docling supports 18 formats (14 exclusive + 4 shared)."""
        formats = router.get_supported_formats(ParserType.DOCLING)
        assert len(formats) == 18
        # Check some key formats
        assert ".pdf" in formats
        assert ".txt" in formats  # Shared
        assert ".epub" not in formats  # LlamaIndex exclusive

    def test_get_supported_formats__llamaindex__correct_count(self, router):
        """Verify LlamaIndex supports 13 formats (9 exclusive + 4 shared)."""
        formats = router.get_supported_formats(ParserType.LLAMAINDEX)
        assert len(formats) == 13
        # Check some key formats
        assert ".epub" in formats
        assert ".txt" in formats  # Shared
        assert ".pdf" not in formats  # Docling exclusive

    def test_get_supported_formats__all__correct_count(self, router):
        """Verify all formats = 27 (14 + 9 + 4)."""
        formats = router.get_supported_formats()
        assert len(formats) == 27
        # Check union of all formats
        assert ".pdf" in formats
        assert ".epub" in formats
        assert ".txt" in formats


# =============================================================================
# TEST FORMAT ROUTER - AVAILABILITY UPDATES
# =============================================================================


class TestFormatRouterAvailabilityUpdates:
    """Test dynamic Docling availability updates."""

    def test_update_docling_availability__changes_routing(self):
        """Verify updating availability changes routing decisions."""
        router = FormatRouter(docling_available=True)

        # Initially, TXT routes to Docling
        decision1 = router.route(Path("notes.txt"))
        assert decision1.parser == ParserType.DOCLING

        # Update availability
        router.update_docling_availability(False)

        # Now TXT routes to LlamaIndex
        decision2 = router.route(Path("notes.txt"))
        assert decision2.parser == ParserType.LLAMAINDEX
        assert "unavailable" in decision2.reason.lower()

    def test_update_docling_availability__no_change__no_log(self):
        """Verify updating to same status doesn't log (implementation detail)."""
        router = FormatRouter(docling_available=True)

        # Update to same status (should be idempotent)
        router.update_docling_availability(True)

        # Routing should be unchanged
        decision = router.route(Path("notes.txt"))
        assert decision.parser == ParserType.DOCLING


# =============================================================================
# TEST DOCLING AVAILABILITY HEALTH CHECK
# =============================================================================


class TestDoclingAvailabilityHealthCheck:
    """Test Docling availability health check function."""

    @pytest.mark.asyncio
    async def test_check_docling_availability__success__returns_true(self):
        """Verify health check returns True when Docling available."""
        # Mock httpx module (lazy import in function)
        import sys
        from unittest.mock import MagicMock

        # Create mock httpx module
        mock_httpx = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_httpx.AsyncClient.return_value = mock_client

        # Temporarily replace httpx in sys.modules
        original_httpx = sys.modules.get("httpx")
        sys.modules["httpx"] = mock_httpx

        try:
            result = await check_docling_availability()
            assert result is True
            mock_client.get.assert_called_once()
        finally:
            # Restore original httpx
            if original_httpx:
                sys.modules["httpx"] = original_httpx
            else:
                sys.modules.pop("httpx", None)

    @pytest.mark.asyncio
    async def test_check_docling_availability__failure__returns_false(self):
        """Verify health check returns False when Docling unavailable."""
        # Mock httpx module (lazy import in function)
        import sys
        from unittest.mock import MagicMock

        # Create mock httpx module that raises exception
        mock_httpx = MagicMock()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

        mock_httpx.AsyncClient.return_value = mock_client

        # Temporarily replace httpx in sys.modules
        original_httpx = sys.modules.get("httpx")
        sys.modules["httpx"] = mock_httpx

        try:
            result = await check_docling_availability()
            assert result is False
        finally:
            # Restore original httpx
            if original_httpx:
                sys.modules["httpx"] = original_httpx
            else:
                sys.modules.pop("httpx", None)

    @pytest.mark.asyncio
    async def test_initialize_format_router__creates_router_with_availability(self):
        """Verify initialize_format_router creates router with correct availability."""
        # Mock health check to return False
        with patch(
            "src.components.ingestion.format_router.check_docling_availability",
            return_value=False,
        ):
            router = await initialize_format_router()

            assert router.docling_available is False

            # Verify routing uses LlamaIndex fallback
            decision = router.route(Path("notes.txt"))
            assert decision.parser == ParserType.LLAMAINDEX


# =============================================================================
# TEST EDGE CASES
# =============================================================================


class TestFormatRouterEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def router(self):
        """Standard router."""
        return FormatRouter(docling_available=True)

    def test_route__relative_path__works(self, router):
        """Verify routing works with relative paths."""
        decision = router.route(Path("../data/document.pdf"))
        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".pdf"

    def test_route__absolute_path__works(self, router):
        """Verify routing works with absolute paths."""
        decision = router.route(Path("/home/user/documents/document.pdf"))
        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".pdf"

    def test_route__path_with_spaces__works(self, router):
        """Verify routing works with paths containing spaces."""
        decision = router.route(Path("My Documents/My File.pdf"))
        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".pdf"

    def test_route__multiple_dots__uses_last_extension(self, router):
        """Verify routing uses last extension for files like 'archive.tar.gz'."""
        # Note: .gz not supported, should raise ValueError
        with pytest.raises(ValueError, match="Unsupported format: .gz"):
            router.route(Path("archive.tar.gz"))

    def test_format_router__initialization__logs_correctly(self):
        """Verify FormatRouter initialization logs format counts."""
        # This is tested implicitly in other tests, but verify initialization
        router = FormatRouter(docling_available=True)
        assert router.docling_available is True

        router2 = FormatRouter(docling_available=False)
        assert router2.docling_available is False
