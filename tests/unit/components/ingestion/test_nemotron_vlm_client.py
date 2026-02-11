"""Tests for NemotronVLClient and _parse_html_tables.

Sprint 129.6g (ADR-063): Tests for the Nemotron VL v1 8B client and HTML table parser.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.components.ingestion.vlm_table_clients import (
    NemotronVLClient,
    _parse_html_tables,
)


# ============================================================================
# _parse_html_tables
# ============================================================================


class TestParseHtmlTables:
    """Tests for _parse_html_tables() — HTML table output from Nemotron VL."""

    def test_simple_table(self):
        html = (
            "<table>"
            "<tr><th>Name</th><th>Age</th></tr>"
            "<tr><td>Alice</td><td>30</td></tr>"
            "<tr><td>Bob</td><td>25</td></tr>"
            "</table>"
        )
        tables = _parse_html_tables(html)
        assert len(tables) == 1
        assert tables[0] == [
            ["Name", "Age"],
            ["Alice", "30"],
            ["Bob", "25"],
        ]

    def test_multiple_tables(self):
        html = (
            "<table><tr><td>A</td><td>B</td></tr></table>"
            "<p>text between</p>"
            "<table><tr><td>X</td><td>Y</td><td>Z</td></tr></table>"
        )
        tables = _parse_html_tables(html)
        assert len(tables) == 2
        assert tables[0] == [["A", "B"]]
        assert tables[1] == [["X", "Y", "Z"]]

    def test_inner_html_stripped(self):
        html = "<table><tr><td><b>Bold</b> text</td><td>Normal</td></tr></table>"
        tables = _parse_html_tables(html)
        assert len(tables) == 1
        assert tables[0][0][0] == "Bold text"

    def test_empty_html(self):
        assert _parse_html_tables("") == []

    def test_no_tables(self):
        assert _parse_html_tables("<p>No tables here</p>") == []

    def test_table_with_th_and_td(self):
        html = (
            "<table>"
            "<tr><th>Header1</th><th>Header2</th></tr>"
            "<tr><td>Data1</td><td>Data2</td></tr>"
            "</table>"
        )
        tables = _parse_html_tables(html)
        assert len(tables) == 1
        assert tables[0][0] == ["Header1", "Header2"]
        assert tables[0][1] == ["Data1", "Data2"]

    def test_whitespace_normalization(self):
        html = "<table><tr><td>  lots   of   spaces  </td></tr></table>"
        tables = _parse_html_tables(html)
        assert tables[0][0][0] == "lots of spaces"

    def test_br_tag_handling(self):
        html = "<table><tr><td>Line1<br>Line2</td></tr></table>"
        tables = _parse_html_tables(html)
        # <br> becomes space after strip
        assert "Line1" in tables[0][0][0]

    def test_fallback_to_markdown(self):
        """If no HTML tables found but markdown pipes present, fallback to markdown parser."""
        md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
        tables = _parse_html_tables(md)
        assert len(tables) == 1
        assert tables[0][0] == ["A", "B"]

    def test_case_insensitive_tags(self):
        html = "<TABLE><TR><TD>cell</TD></TR></TABLE>"
        tables = _parse_html_tables(html)
        assert len(tables) == 1
        assert tables[0][0][0] == "cell"


# ============================================================================
# NemotronVLClient
# ============================================================================


class TestNemotronVLClient:
    """Tests for NemotronVLClient HTTP interactions."""

    def test_default_url(self):
        client = NemotronVLClient()
        assert client.base_url == "http://localhost:8002"

    def test_custom_url(self):
        client = NemotronVLClient(base_url="http://vlm:9000/")
        assert client.base_url == "http://vlm:9000"

    def test_model_constant(self):
        assert "Nemotron" in NemotronVLClient.MODEL
        assert "VL" in NemotronVLClient.MODEL

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        client = NemotronVLClient()
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await client.health_check()
            assert result is True
            assert client._healthy is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        client = NemotronVLClient()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_extract_tables_success(self):
        client = NemotronVLClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<table>"
                            "<tr><th>Col1</th><th>Col2</th></tr>"
                            "<tr><td>A</td><td>B</td></tr>"
                            "</table>"
                        )
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            tables = await client.extract_tables_from_page(b"fake_png_bytes")
            assert len(tables) == 1
            assert tables[0][0] == ["Col1", "Col2"]
            assert tables[0][1] == ["A", "B"]

    @pytest.mark.asyncio
    async def test_extract_tables_timeout(self):
        client = NemotronVLClient()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            tables = await client.extract_tables_from_page(b"fake_png_bytes")
            assert tables == []

    @pytest.mark.asyncio
    async def test_extract_tables_no_content(self):
        client = NemotronVLClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"choices": []}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            tables = await client.extract_tables_from_page(b"fake_png_bytes")
            assert tables == []

    @pytest.mark.asyncio
    async def test_extract_tables_no_tables_in_page(self):
        client = NemotronVLClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "No tables found in this image."}}]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            tables = await client.extract_tables_from_page(b"fake_png_bytes")
            assert tables == []
