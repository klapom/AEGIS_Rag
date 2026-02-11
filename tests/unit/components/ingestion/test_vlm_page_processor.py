"""Tests for VLMPageProcessor — parallel VLM page processing.

Sprint 129.6g: Tests for VLMPageProcessor, VLMPageResult, VLMProcessingResult.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.components.ingestion.vlm_page_processor import (
    VLMPageProcessor,
    VLMPageResult,
    VLMProcessingResult,
)


# ============================================================================
# VLMPageResult / VLMProcessingResult dataclasses
# ============================================================================


class TestDataclasses:
    """Tests for VLM result dataclasses."""

    def test_page_result_defaults(self):
        pr = VLMPageResult(page_no=1, tables=[])
        assert pr.page_no == 1
        assert pr.tables == []
        assert pr.processing_time_ms == 0.0
        assert pr.error is None

    def test_page_result_with_tables(self):
        tables = [[["A", "B"], ["1", "2"]]]
        pr = VLMPageResult(page_no=2, tables=tables, processing_time_ms=150.5)
        assert len(pr.tables) == 1
        assert pr.tables[0][0] == ["A", "B"]
        assert pr.processing_time_ms == 150.5

    def test_page_result_with_error(self):
        pr = VLMPageResult(page_no=3, tables=[], error="timeout")
        assert pr.error == "timeout"

    def test_processing_result_defaults(self):
        result = VLMProcessingResult()
        assert result.page_results == {}
        assert result.total_pages == 0
        assert result.pages_with_tables == 0
        assert result.total_tables == 0
        assert result.total_processing_time_ms == 0.0
        assert result.vlm_available is False


# ============================================================================
# VLMPageProcessor
# ============================================================================


class TestVLMPageProcessor:
    """Tests for VLMPageProcessor HTTP interactions."""

    def test_init_default_url(self):
        proc = VLMPageProcessor()
        assert proc._client.base_url == "http://localhost:8002"

    def test_init_custom_url(self):
        proc = VLMPageProcessor(vlm_url="http://vlm:9000")
        assert proc._client.base_url == "http://vlm:9000"

    @pytest.mark.asyncio
    async def test_check_availability_healthy(self):
        proc = VLMPageProcessor()
        proc._client.health_check = AsyncMock(return_value=True)

        result = await proc.check_availability()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_availability_unhealthy(self):
        proc = VLMPageProcessor()
        proc._client.health_check = AsyncMock(return_value=False)

        result = await proc.check_availability()
        assert result is False

    @pytest.mark.asyncio
    async def test_process_empty_pages(self):
        proc = VLMPageProcessor()

        result = await proc.process_all_pages({})
        assert result.total_pages == 0
        assert result.vlm_available is False

    @pytest.mark.asyncio
    async def test_process_vlm_unavailable(self):
        proc = VLMPageProcessor()
        proc._client.health_check = AsyncMock(return_value=False)

        pages = {1: b"fake_png_1", 2: b"fake_png_2"}
        result = await proc.process_all_pages(pages)

        assert result.total_pages == 2
        assert result.vlm_available is False
        assert result.page_results == {}  # No processing happened

    @pytest.mark.asyncio
    async def test_process_all_pages_success(self):
        proc = VLMPageProcessor()
        proc._client.health_check = AsyncMock(return_value=True)

        # Page 1: one table, Page 2: no tables, Page 3: two tables
        _page_tables = {
            b"page1": [[["A", "B"], ["1", "2"]]],
            b"page2": [],
            b"page3": [[["X", "Y"]], [["P", "Q"], ["R", "S"]]],
        }

        async def mock_extract(image_bytes):
            return _page_tables.get(image_bytes, [])

        proc._client.extract_tables_from_page = mock_extract

        pages = {1: b"page1", 2: b"page2", 3: b"page3"}
        result = await proc.process_all_pages(pages)

        assert result.total_pages == 3
        assert result.vlm_available is True
        assert result.pages_with_tables == 2  # Pages 1 and 3
        assert result.total_tables == 3  # 1 + 0 + 2
        assert len(result.page_results) == 3

        # Check individual page results
        assert len(result.page_results[1].tables) == 1
        assert len(result.page_results[2].tables) == 0
        assert len(result.page_results[3].tables) == 2

    @pytest.mark.asyncio
    async def test_process_page_error_handled(self):
        proc = VLMPageProcessor()
        proc._client.health_check = AsyncMock(return_value=True)

        # Page 1 succeeds, Page 2 throws exception
        call_count = 0

        async def mock_extract(image_bytes):
            nonlocal call_count
            call_count += 1
            if image_bytes == b"page1":
                return [[["OK"]]]
            raise RuntimeError("GPU OOM")

        proc._client.extract_tables_from_page = mock_extract

        pages = {1: b"page1", 2: b"page2"}
        result = await proc.process_all_pages(pages)

        assert result.total_pages == 2
        assert result.vlm_available is True
        # Page 1 succeeded, Page 2 failed gracefully
        assert result.page_results[1].tables == [[["OK"]]]
        assert result.page_results[1].error is None
        assert result.page_results[2].tables == []
        assert result.page_results[2].error is not None
        assert "GPU OOM" in result.page_results[2].error

    @pytest.mark.asyncio
    async def test_process_pages_sorted_order(self):
        """Pages should be processed in sorted order."""
        proc = VLMPageProcessor()
        proc._client.health_check = AsyncMock(return_value=True)

        processed_order = []

        async def mock_extract(image_bytes):
            processed_order.append(image_bytes)
            return []

        proc._client.extract_tables_from_page = mock_extract

        # Provide pages out of order
        pages = {3: b"c", 1: b"a", 2: b"b"}
        await proc.process_all_pages(pages)

        # asyncio.gather preserves task creation order (which is sorted)
        assert processed_order == [b"a", b"b", b"c"]

    @pytest.mark.asyncio
    async def test_process_timing_recorded(self):
        proc = VLMPageProcessor()
        proc._client.health_check = AsyncMock(return_value=True)
        proc._client.extract_tables_from_page = AsyncMock(return_value=[])

        pages = {1: b"page1"}
        result = await proc.process_all_pages(pages)

        assert result.total_processing_time_ms > 0
        assert result.page_results[1].processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Verify semaphore parameter is respected (max_concurrent=1 forces sequential)."""
        proc = VLMPageProcessor()
        proc._client.health_check = AsyncMock(return_value=True)

        active_count = 0
        max_active = 0

        async def mock_extract(image_bytes):
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            # Small async yield to allow other tasks to start if allowed
            import asyncio

            await asyncio.sleep(0.01)
            active_count -= 1
            return []

        proc._client.extract_tables_from_page = mock_extract

        pages = {1: b"a", 2: b"b", 3: b"c", 4: b"d"}
        await proc.process_all_pages(pages, max_concurrent=1)

        assert max_active == 1  # Only 1 concurrent at a time
