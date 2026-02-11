"""Tests for vlm_table_clients.py — VLM HTTP clients for table cross-validation.

Sprint 129.6c: Tests cover Granite and DeepSeek client behavior with mocked httpx.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# _parse_markdown_tables (standalone function, no HTTP needed)
# ============================================================================


class TestParseMarkdownTables:
    """Tests for _parse_markdown_tables()."""

    def test_single_table(self):
        from src.components.ingestion.vlm_table_clients import _parse_markdown_tables

        md = (
            "| Name | Age | City |\n"
            "|------|-----|------|\n"
            "| Alice | 30 | NYC |\n"
            "| Bob | 25 | LA |\n"
        )
        tables = _parse_markdown_tables(md)
        assert len(tables) == 1
        assert tables[0] == [
            ["Name", "Age", "City"],
            ["Alice", "30", "NYC"],
            ["Bob", "25", "LA"],
        ]

    def test_multiple_tables(self):
        from src.components.ingestion.vlm_table_clients import _parse_markdown_tables

        md = (
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n"
            "\n"
            "Some text between tables\n"
            "\n"
            "| X | Y | Z |\n"
            "|---|---|---|\n"
            "| a | b | c |\n"
        )
        tables = _parse_markdown_tables(md)
        assert len(tables) == 2
        assert tables[0] == [["A", "B"], ["1", "2"]]
        assert tables[1] == [["X", "Y", "Z"], ["a", "b", "c"]]

    def test_no_tables(self):
        from src.components.ingestion.vlm_table_clients import _parse_markdown_tables

        tables = _parse_markdown_tables("Just some text without any tables.")
        assert tables == []

    def test_empty_string(self):
        from src.components.ingestion.vlm_table_clients import _parse_markdown_tables

        tables = _parse_markdown_tables("")
        assert tables == []

    def test_separator_only_rows_excluded(self):
        from src.components.ingestion.vlm_table_clients import _parse_markdown_tables

        md = (
            "| H1 | H2 |\n"
            "|:---|---:|\n"  # alignment separators
            "| c1 | c2 |\n"
        )
        tables = _parse_markdown_tables(md)
        assert len(tables) == 1
        assert len(tables[0]) == 2  # Header + 1 data row, separator excluded


# ============================================================================
# GraniteDoclingClient
# ============================================================================


class TestGraniteDoclingClient:
    """Tests for GraniteDoclingClient with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        from src.components.ingestion.vlm_table_clients import GraniteDoclingClient

        client = GraniteDoclingClient(base_url="http://fake:8083")

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        from src.components.ingestion.vlm_table_clients import GraniteDoclingClient

        client = GraniteDoclingClient(base_url="http://fake:8083")

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_extract_tables_parses_response(self):
        from src.components.ingestion.vlm_table_clients import GraniteDoclingClient

        client = GraniteDoclingClient(base_url="http://fake:8083")

        docling_response = {
            "document": {
                "tables": [
                    {
                        "num_rows": 2,
                        "num_cols": 3,
                        "table_cells": [
                            {"start_row_offset_idx": 0, "start_col_offset_idx": 0, "text": "A"},
                            {"start_row_offset_idx": 0, "start_col_offset_idx": 1, "text": "B"},
                            {"start_row_offset_idx": 0, "start_col_offset_idx": 2, "text": "C"},
                            {"start_row_offset_idx": 1, "start_col_offset_idx": 0, "text": "1"},
                            {"start_row_offset_idx": 1, "start_col_offset_idx": 1, "text": "2"},
                            {"start_row_offset_idx": 1, "start_col_offset_idx": 2, "text": "3"},
                        ],
                    }
                ]
            }
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = docling_response

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            tables = await client.extract_tables_from_page(b"fake_png_bytes")
            assert len(tables) == 1
            assert tables[0] == [["A", "B", "C"], ["1", "2", "3"]]

    @pytest.mark.asyncio
    async def test_extract_tables_timeout(self):
        import httpx

        from src.components.ingestion.vlm_table_clients import GraniteDoclingClient

        client = GraniteDoclingClient(base_url="http://fake:8083")

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            tables = await client.extract_tables_from_page(b"fake_png")
            assert tables == []


# ============================================================================
# DeepSeekOCRClient
# ============================================================================


class TestDeepSeekOCRClient:
    """Tests for DeepSeekOCRClient with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        from src.components.ingestion.vlm_table_clients import DeepSeekOCRClient

        client = DeepSeekOCRClient(base_url="http://fake:8002")

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_extract_tables_parses_markdown(self):
        from src.components.ingestion.vlm_table_clients import DeepSeekOCRClient

        client = DeepSeekOCRClient(base_url="http://fake:8002")

        openai_response = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "| Name | Value |\n|------|-------|\n| X | 100 |\n| Y | 200 |\n"
                        )
                    }
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = openai_response

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            tables = await client.extract_tables_from_page(b"fake_png")
            assert len(tables) == 1
            assert tables[0] == [
                ["Name", "Value"],
                ["X", "100"],
                ["Y", "200"],
            ]

    @pytest.mark.asyncio
    async def test_extract_tables_no_content(self):
        from src.components.ingestion.vlm_table_clients import DeepSeekOCRClient

        client = DeepSeekOCRClient(base_url="http://fake:8002")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": []}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            tables = await client.extract_tables_from_page(b"fake_png")
            assert tables == []
