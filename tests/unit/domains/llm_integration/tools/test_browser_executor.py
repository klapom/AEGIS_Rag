"""Unit tests for browser executor tool.

Sprint 103 Feature 103.1: Browser automation with Playwright.

Tests cover:
- Navigation
- Clicking elements
- Screenshots
- JavaScript evaluation
- Text extraction
- Form filling
- Typing
- Error handling
- Timeout behavior
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domains.llm_integration.tools.builtin.browser_executor import (
    browser_click,
    browser_evaluate,
    browser_fill,
    browser_get_text,
    browser_navigate,
    browser_screenshot,
    browser_type,
    close_browser,
    get_browser,
)


@pytest.fixture
def mock_playwright_browser():
    """Mock Playwright browser instance."""
    browser = AsyncMock()
    browser.is_connected.return_value = True

    context = AsyncMock()
    page = AsyncMock()

    # Setup page mock
    page.goto = AsyncMock()
    page.title = AsyncMock(return_value="Example Domain")
    page.url = "https://example.com"
    page.click = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    page.evaluate = AsyncMock(return_value="Evaluation result")
    page.wait_for_selector = AsyncMock()
    page.fill = AsyncMock()
    page.type = AsyncMock()

    # Setup element mock
    element = AsyncMock()
    element.text_content = AsyncMock(return_value="Example text content")
    element.screenshot = AsyncMock(return_value=b"fake_element_screenshot")
    page.wait_for_selector.return_value = element

    # Setup browser.new_page() to return page
    browser.new_page = AsyncMock(return_value=page)

    # Setup context and pages
    context.pages = [page]
    browser.contexts = [context]

    return browser, page


@pytest.fixture
async def mock_browser_instance(mock_playwright_browser):
    """Mock the global browser instance."""
    browser, page = mock_playwright_browser
    with patch(
        "src.domains.llm_integration.tools.builtin.browser_executor.get_browser",
        return_value=browser,
    ):
        yield browser, page


class TestBrowserNavigate:
    """Test suite for browser_navigate function."""

    @pytest.mark.asyncio
    async def test_navigate_success(self, mock_browser_instance):
        """Test successful navigation."""
        browser, page = mock_browser_instance

        result = await browser_navigate("https://example.com")

        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert result["title"] == "Example Domain"
        page.goto.assert_called_once_with(
            "https://example.com",
            timeout=30000,
            wait_until="load",
        )

    @pytest.mark.asyncio
    async def test_navigate_with_custom_timeout(self, mock_browser_instance):
        """Test navigation with custom timeout."""
        browser, page = mock_browser_instance

        result = await browser_navigate("https://example.com", timeout=60)

        assert result["success"] is True
        page.goto.assert_called_once_with(
            "https://example.com",
            timeout=60000,
            wait_until="load",
        )

    @pytest.mark.asyncio
    async def test_navigate_timeout_clamped(self, mock_browser_instance):
        """Test that excessive timeout is clamped to maximum."""
        browser, page = mock_browser_instance

        result = await browser_navigate("https://example.com", timeout=120)

        assert result["success"] is True
        # Should clamp to 60 seconds max
        page.goto.assert_called_once_with(
            "https://example.com",
            timeout=60000,
            wait_until="load",
        )

    @pytest.mark.asyncio
    async def test_navigate_timeout_error(self, mock_browser_instance):
        """Test navigation timeout error handling."""
        browser, page = mock_browser_instance
        page.goto.side_effect = TimeoutError()

        result = await browser_navigate("https://example.com")

        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_navigate_generic_error(self, mock_browser_instance):
        """Test navigation generic error handling."""
        browser, page = mock_browser_instance
        page.goto.side_effect = Exception("Network error")

        result = await browser_navigate("https://example.com")

        assert result["success"] is False
        assert "Network error" in result["error"]


class TestBrowserClick:
    """Test suite for browser_click function."""

    @pytest.mark.asyncio
    async def test_click_success(self, mock_browser_instance):
        """Test successful element click."""
        browser, page = mock_browser_instance

        result = await browser_click("button.submit")

        assert result["success"] is True
        assert result["selector"] == "button.submit"
        page.click.assert_called_once_with("button.submit", timeout=30000)

    @pytest.mark.asyncio
    async def test_click_no_page_available(self):
        """Test click when no page is available."""
        browser = MagicMock()
        browser.contexts = []

        with patch(
            "src.domains.llm_integration.tools.builtin.browser_executor.get_browser",
            return_value=browser,
        ):
            result = await browser_click("button.submit")

        assert result["success"] is False
        assert "No page available" in result["error"]

    @pytest.mark.asyncio
    async def test_click_timeout(self, mock_browser_instance):
        """Test click timeout error."""
        browser, page = mock_browser_instance
        page.click.side_effect = TimeoutError()

        result = await browser_click("button.submit")

        assert result["success"] is False
        assert "not found or not clickable" in result["error"].lower()


class TestBrowserScreenshot:
    """Test suite for browser_screenshot function."""

    @pytest.mark.asyncio
    async def test_screenshot_full_page(self, mock_browser_instance):
        """Test full page screenshot."""
        browser, page = mock_browser_instance

        result = await browser_screenshot(full_page=True)

        assert result["success"] is True
        assert "data" in result
        assert result["format"] == "png"

        # Verify base64 encoding
        decoded = base64.b64decode(result["data"])
        assert decoded == b"fake_screenshot_data"

        page.screenshot.assert_called_once_with(full_page=True)

    @pytest.mark.asyncio
    async def test_screenshot_element(self, mock_browser_instance):
        """Test element screenshot."""
        browser, page = mock_browser_instance

        result = await browser_screenshot(selector="div.content")

        assert result["success"] is True
        assert "data" in result
        assert result["selector"] == "div.content"

        # Verify element screenshot was called
        page.wait_for_selector.assert_called_once_with("div.content", timeout=30000)

    @pytest.mark.asyncio
    async def test_screenshot_no_page(self):
        """Test screenshot when no page available."""
        browser = MagicMock()
        browser.contexts = []

        with patch(
            "src.domains.llm_integration.tools.builtin.browser_executor.get_browser",
            return_value=browser,
        ):
            result = await browser_screenshot()

        assert result["success"] is False
        assert "No page available" in result["error"]


class TestBrowserEvaluate:
    """Test suite for browser_evaluate function."""

    @pytest.mark.asyncio
    async def test_evaluate_success(self, mock_browser_instance):
        """Test successful JavaScript evaluation."""
        browser, page = mock_browser_instance

        result = await browser_evaluate("document.title")

        assert result["success"] is True
        assert result["result"] == "Evaluation result"
        page.evaluate.assert_called_once_with("document.title", timeout=30000)

    @pytest.mark.asyncio
    async def test_evaluate_timeout(self, mock_browser_instance):
        """Test evaluation timeout."""
        browser, page = mock_browser_instance
        page.evaluate.side_effect = TimeoutError()

        result = await browser_evaluate("document.title")

        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_evaluate_error(self, mock_browser_instance):
        """Test evaluation error."""
        browser, page = mock_browser_instance
        page.evaluate.side_effect = Exception("Invalid expression")

        result = await browser_evaluate("invalid.expression")

        assert result["success"] is False
        assert "Invalid expression" in result["error"]


class TestBrowserGetText:
    """Test suite for browser_get_text function."""

    @pytest.mark.asyncio
    async def test_get_text_success(self, mock_browser_instance):
        """Test successful text extraction."""
        browser, page = mock_browser_instance

        result = await browser_get_text("h1")

        assert result["success"] is True
        assert result["text"] == "Example text content"
        assert result["selector"] == "h1"

    @pytest.mark.asyncio
    async def test_get_text_empty(self, mock_browser_instance):
        """Test text extraction with empty content."""
        browser, page = mock_browser_instance
        element = AsyncMock()
        element.text_content = AsyncMock(return_value=None)
        page.wait_for_selector.return_value = element

        result = await browser_get_text("p.empty")

        assert result["success"] is True
        assert result["text"] == ""

    @pytest.mark.asyncio
    async def test_get_text_timeout(self, mock_browser_instance):
        """Test text extraction timeout."""
        browser, page = mock_browser_instance
        page.wait_for_selector.side_effect = TimeoutError()

        result = await browser_get_text("h1")

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestBrowserFill:
    """Test suite for browser_fill function."""

    @pytest.mark.asyncio
    async def test_fill_success(self, mock_browser_instance):
        """Test successful form fill."""
        browser, page = mock_browser_instance

        result = await browser_fill("input[name='email']", "test@example.com")

        assert result["success"] is True
        assert result["selector"] == "input[name='email']"
        page.fill.assert_called_once_with("input[name='email']", "test@example.com", timeout=30000)

    @pytest.mark.asyncio
    async def test_fill_timeout(self, mock_browser_instance):
        """Test fill timeout."""
        browser, page = mock_browser_instance
        page.fill.side_effect = TimeoutError()

        result = await browser_fill("input[name='email']", "test@example.com")

        assert result["success"] is False
        assert "not found or not fillable" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_fill_error(self, mock_browser_instance):
        """Test fill error."""
        browser, page = mock_browser_instance
        page.fill.side_effect = Exception("Element is not editable")

        result = await browser_fill("input[name='email']", "test@example.com")

        assert result["success"] is False
        assert "Element is not editable" in result["error"]


class TestBrowserType:
    """Test suite for browser_type function."""

    @pytest.mark.asyncio
    async def test_type_success(self, mock_browser_instance):
        """Test successful typing."""
        browser, page = mock_browser_instance

        result = await browser_type("input[name='search']", "hello world")

        assert result["success"] is True
        assert result["selector"] == "input[name='search']"
        page.type.assert_called_once_with(
            "input[name='search']",
            "hello world",
            delay=100,
            timeout=30000,
        )

    @pytest.mark.asyncio
    async def test_type_with_custom_delay(self, mock_browser_instance):
        """Test typing with custom delay."""
        browser, page = mock_browser_instance

        result = await browser_type("input[name='search']", "hello", delay=50)

        assert result["success"] is True
        page.type.assert_called_once_with(
            "input[name='search']",
            "hello",
            delay=50,
            timeout=30000,
        )

    @pytest.mark.asyncio
    async def test_type_timeout(self, mock_browser_instance):
        """Test typing timeout."""
        browser, page = mock_browser_instance
        page.type.side_effect = TimeoutError()

        result = await browser_type("input[name='search']", "hello")

        assert result["success"] is False
        assert "not found or not typable" in result["error"].lower()


class TestBrowserManagement:
    """Test suite for browser instance management."""

    @pytest.mark.asyncio
    async def test_get_browser_creates_new_instance(self):
        """Test that get_browser creates a new instance if none exists."""
        with patch(
            "src.domains.llm_integration.tools.builtin.browser_executor._browser_instance",
            None,
        ):
            with patch(
                "src.domains.llm_integration.tools.builtin.browser_executor.async_playwright"
            ) as mock_playwright:
                mock_pw = AsyncMock()
                mock_browser = AsyncMock()
                mock_browser.is_connected.return_value = True
                mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
                mock_playwright.return_value.start = AsyncMock(return_value=mock_pw)

                browser = await get_browser()

                assert browser is not None
                mock_pw.chromium.launch.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_browser(self):
        """Test closing the browser instance."""
        mock_browser = AsyncMock()

        with patch(
            "src.domains.llm_integration.tools.builtin.browser_executor._browser_instance",
            mock_browser,
        ):
            await close_browser()

            mock_browser.close.assert_called_once()


class TestTimeoutEnforcement:
    """Test suite for timeout enforcement."""

    @pytest.mark.asyncio
    async def test_all_tools_enforce_max_timeout(self, mock_browser_instance):
        """Test that all tools enforce maximum timeout of 60 seconds."""
        browser, page = mock_browser_instance

        # Test with excessive timeout (120 seconds)
        await browser_navigate("https://example.com", timeout=120)
        page.goto.assert_called_with(
            "https://example.com",
            timeout=60000,  # Should be clamped to 60 seconds
            wait_until="load",
        )

        await browser_click("button", timeout=120)
        page.click.assert_called_with("button", timeout=60000)

        await browser_evaluate("document.title", timeout=120)
        page.evaluate.assert_called_with("document.title", timeout=60000)
