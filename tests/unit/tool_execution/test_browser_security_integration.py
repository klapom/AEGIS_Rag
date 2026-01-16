"""Integration tests for browser tool security.

Sprint 103 Feature 103.2: Browser security integration tests.
"""

import pytest

from src.domains.llm_integration.tools.builtin.browser_executor import (
    browser_click,
    browser_evaluate,
    browser_fill,
    browser_get_text,
    browser_navigate,
    browser_screenshot,
    browser_type,
)


class TestBrowserNavigateSecurity:
    """Test browser_navigate security integration."""

    @pytest.mark.asyncio
    async def test_navigate_blocks_file_urls(self):
        """Test that file:// URLs are blocked."""
        result = await browser_navigate("file:///etc/passwd")
        assert result["success"] is False
        assert "blocked" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_navigate_blocks_localhost(self):
        """Test that localhost URLs are blocked."""
        result = await browser_navigate("http://localhost:8000")
        assert result["success"] is False
        assert "blocked" in result["error"].lower()


class TestBrowserClickSecurity:
    """Test browser_click security integration."""

    @pytest.mark.asyncio
    async def test_click_blocks_empty_selector(self):
        """Test that empty selectors are blocked."""
        result = await browser_click("")
        assert result["success"] is False
        assert "invalid" in result["error"].lower() or "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_click_blocks_too_long_selector(self):
        """Test that very long selectors are blocked."""
        long_selector = "div " * 200  # > 500 chars
        result = await browser_click(long_selector)
        assert result["success"] is False
        assert "too long" in result["error"].lower()


class TestBrowserEvaluateSecurity:
    """Test browser_evaluate security integration."""

    @pytest.mark.asyncio
    async def test_evaluate_blocks_fetch(self):
        """Test that fetch() calls are blocked."""
        result = await browser_evaluate("fetch('https://evil.com')")
        assert result["success"] is False
        assert "blocked" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_evaluate_blocks_cookie_access(self):
        """Test that cookie access is blocked."""
        result = await browser_evaluate("document.cookie")
        assert result["success"] is False
        assert "blocked" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_evaluate_blocks_window_location(self):
        """Test that window.location manipulation is blocked."""
        result = await browser_evaluate("window.location = 'https://evil.com'")
        assert result["success"] is False
        assert "blocked" in result["error"].lower()


class TestBrowserScreenshotSecurity:
    """Test browser_screenshot security integration."""

    @pytest.mark.asyncio
    async def test_screenshot_blocks_too_long_selector(self):
        """Test that very long selectors are blocked."""
        long_selector = "div " * 200  # > 500 chars
        result = await browser_screenshot(selector=long_selector, timeout=1)
        assert result["success"] is False
        assert "too long" in result["error"].lower()


class TestBrowserGetTextSecurity:
    """Test browser_get_text security integration."""

    @pytest.mark.asyncio
    async def test_get_text_blocks_empty_selector(self):
        """Test that empty selectors are blocked."""
        result = await browser_get_text("")
        assert result["success"] is False
        assert "invalid" in result["error"].lower() or "empty" in result["error"].lower()


class TestBrowserFillSecurity:
    """Test browser_fill security integration."""

    @pytest.mark.asyncio
    async def test_fill_blocks_empty_selector(self):
        """Test that empty selectors are blocked."""
        result = await browser_fill("", "value")
        assert result["success"] is False
        assert "invalid" in result["error"].lower() or "empty" in result["error"].lower()


class TestBrowserTypeSecurity:
    """Test browser_type security integration."""

    @pytest.mark.asyncio
    async def test_type_blocks_empty_selector(self):
        """Test that empty selectors are blocked."""
        result = await browser_type("", "text")
        assert result["success"] is False
        assert "invalid" in result["error"].lower() or "empty" in result["error"].lower()
