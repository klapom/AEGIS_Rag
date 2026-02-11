"""Tests for VLM parallel pages API endpoints.

Sprint 129.6g: GET/PUT /admin/vlm/parallel-pages with Redis persistence.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.api.v1.admin_llm import (
    REDIS_KEY_VLM_PARALLEL_PAGES,
    VLMParallelPagesRequest,
    VLMParallelPagesResponse,
    get_vlm_parallel_pages,
    set_vlm_parallel_pages,
)


# ============================================================================
# Pydantic models
# ============================================================================


class TestModels:
    """Tests for Pydantic request/response models."""

    def test_response_model_defaults(self):
        resp = VLMParallelPagesResponse(enabled=False)
        assert resp.enabled is False
        assert resp.vlm_healthy is False

    def test_response_model_enabled(self):
        resp = VLMParallelPagesResponse(enabled=True, vlm_healthy=True)
        assert resp.enabled is True
        assert resp.vlm_healthy is True

    def test_request_model(self):
        req = VLMParallelPagesRequest(enabled=True)
        assert req.enabled is True


# ============================================================================
# GET /admin/vlm/parallel-pages
# ============================================================================


class TestGetVlmParallelPages:
    """Tests for GET endpoint."""

    @pytest.mark.asyncio
    async def test_default_disabled(self):
        """When Redis has no key, return disabled."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.close = AsyncMock()

        with (
            patch("redis.asyncio.from_url", return_value=mock_redis),
            patch("httpx.AsyncClient") as mock_httpx_cls,
        ):
            # VLM health check fails
            mock_httpx = AsyncMock()
            mock_httpx.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
            mock_httpx.__aexit__ = AsyncMock(return_value=None)
            mock_httpx_cls.return_value = mock_httpx

            result = await get_vlm_parallel_pages()

        assert result.enabled is False
        assert result.vlm_healthy is False

    @pytest.mark.asyncio
    async def test_enabled_from_redis(self):
        """When Redis has 'true', return enabled."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="true")
        mock_redis.close = AsyncMock()

        with (
            patch("redis.asyncio.from_url", return_value=mock_redis),
            patch("httpx.AsyncClient") as mock_httpx_cls,
        ):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_httpx = AsyncMock()
            mock_httpx.get = AsyncMock(return_value=mock_resp)
            mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
            mock_httpx.__aexit__ = AsyncMock(return_value=None)
            mock_httpx_cls.return_value = mock_httpx

            result = await get_vlm_parallel_pages()

        assert result.enabled is True
        assert result.vlm_healthy is True

    @pytest.mark.asyncio
    async def test_redis_failure_returns_disabled(self):
        """When Redis is down, return disabled (graceful degradation)."""
        with (
            patch("redis.asyncio.from_url", side_effect=ConnectionError("Redis down")),
            patch("httpx.AsyncClient") as mock_httpx_cls,
        ):
            mock_httpx = AsyncMock()
            mock_httpx.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
            mock_httpx.__aexit__ = AsyncMock(return_value=None)
            mock_httpx_cls.return_value = mock_httpx

            result = await get_vlm_parallel_pages()

        assert result.enabled is False


# ============================================================================
# PUT /admin/vlm/parallel-pages
# ============================================================================


class TestSetVlmParallelPages:
    """Tests for PUT endpoint."""

    @pytest.mark.asyncio
    async def test_enable(self):
        """Enable VLM parallel pages → Redis set to 'true'."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.close = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            request = VLMParallelPagesRequest(enabled=True)
            result = await set_vlm_parallel_pages(request)

        assert result["status"] == "success"
        assert result["enabled"] is True
        mock_redis.set.assert_called_once_with(REDIS_KEY_VLM_PARALLEL_PAGES, "true")

    @pytest.mark.asyncio
    async def test_disable(self):
        """Disable VLM parallel pages → Redis set to 'false'."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.close = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            request = VLMParallelPagesRequest(enabled=False)
            result = await set_vlm_parallel_pages(request)

        assert result["status"] == "success"
        assert result["enabled"] is False
        mock_redis.set.assert_called_once_with(REDIS_KEY_VLM_PARALLEL_PAGES, "false")

    @pytest.mark.asyncio
    async def test_redis_failure_raises_500(self):
        """When Redis fails, raise 500 error."""
        with patch("redis.asyncio.from_url", side_effect=ConnectionError("Redis down")):
            request = VLMParallelPagesRequest(enabled=True)

            with pytest.raises(Exception):  # HTTPException from FastAPI
                await set_vlm_parallel_pages(request)
