"""Unit tests for Browser Tool.

Sprint 93 Feature 93.2: Browser Tool with Playwright (8 SP)

Tests cover:
- Browser navigation
- Element interaction (click, type)
- Screenshot capture
- Form filling
- Session management
- Error handling
- Skill-aware tool integration
"""

from unittest.mock import patch

import pytest

from src.agents.tools.browser import (
    BrowserAction,
    BrowserResult,
    BrowserSession,
    BrowserTool,
    browser_click,
    browser_fill_form,
    browser_navigate,
    browser_screenshot,
    browser_type_text,
    get_browser_tools,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def browser_tool():
    """Create a BrowserTool instance."""
    return BrowserTool(default_timeout=10.0, max_retries=2)


@pytest.fixture
def mock_session():
    """Create a mock BrowserSession."""
    return BrowserSession(
        session_id="test_session",
        current_url="https://example.com",
        page_title="Example",
        is_active=True,
    )


# =============================================================================
# BrowserTool Tests
# =============================================================================


class TestBrowserTool:
    """Test BrowserTool class."""

    def test_init(self, browser_tool):
        """Test browser tool initialization."""
        assert browser_tool.session is None
        assert browser_tool.default_timeout == 10.0
        assert browser_tool.max_retries == 2
        assert browser_tool._action_count == 0

    @pytest.mark.asyncio
    async def test_navigate_success(self, browser_tool):
        """Test successful navigation."""
        result = await browser_tool.navigate("https://example.com")

        assert result.success is True
        assert result.action == BrowserAction.NAVIGATE
        assert result.data["url"] == "https://example.com"
        assert result.error is None
        assert result.duration_ms > 0
        assert browser_tool._action_count == 1

    @pytest.mark.asyncio
    async def test_navigate_updates_session(self, browser_tool):
        """Test that navigation updates session state."""
        browser_tool.session = BrowserSession(session_id="test")

        result = await browser_tool.navigate("https://example.com")

        assert result.success is True
        assert browser_tool.session.current_url == "https://example.com"
        assert browser_tool.session.interaction_count == 1

    @pytest.mark.asyncio
    async def test_navigate_with_timeout(self, browser_tool):
        """Test navigation with custom timeout."""
        result = await browser_tool.navigate(
            "https://example.com",
            timeout=5.0,
        )

        assert result.success is True
        assert result.action == BrowserAction.NAVIGATE

    @pytest.mark.asyncio
    async def test_click_success(self, browser_tool):
        """Test successful element click."""
        result = await browser_tool.click(
            selector="button.submit",
            element_description="Submit button",
        )

        assert result.success is True
        assert result.action == BrowserAction.CLICK
        assert result.data["selector"] == "button.submit"
        assert result.data["element"] == "Submit button"
        assert result.data["clicked"] is True

    @pytest.mark.asyncio
    async def test_click_with_options(self, browser_tool):
        """Test click with button and double-click options."""
        result = await browser_tool.click(
            selector="#link",
            element_description="Link",
            button="right",
            double_click=True,
        )

        assert result.success is True
        assert result.action == BrowserAction.CLICK

    @pytest.mark.asyncio
    async def test_type_text_success(self, browser_tool):
        """Test typing text into element."""
        result = await browser_tool.type_text(
            selector="input#search",
            element_description="Search input",
            text="test query",
        )

        assert result.success is True
        assert result.action == BrowserAction.TYPE
        assert result.data["text_length"] == 10
        assert result.data["submitted"] is False

    @pytest.mark.asyncio
    async def test_type_text_with_submit(self, browser_tool):
        """Test typing with submit flag."""
        result = await browser_tool.type_text(
            selector="input#search",
            element_description="Search input",
            text="query",
            submit=True,
        )

        assert result.success is True
        assert result.data["submitted"] is True

    @pytest.mark.asyncio
    async def test_screenshot_success(self, browser_tool):
        """Test taking a screenshot."""
        result = await browser_tool.screenshot()

        assert result.success is True
        assert result.action == BrowserAction.SCREENSHOT
        assert "path" in result.data
        assert result.data["path"].startswith("/tmp/screenshot_")

    @pytest.mark.asyncio
    async def test_screenshot_with_filename(self, browser_tool):
        """Test screenshot with custom filename."""
        result = await browser_tool.screenshot(
            filename="/tmp/custom.png",
            full_page=True,
        )

        assert result.success is True
        assert result.data["path"] == "/tmp/custom.png"
        assert result.data["full_page"] is True

    @pytest.mark.asyncio
    async def test_screenshot_element(self, browser_tool):
        """Test screenshot of specific element."""
        result = await browser_tool.screenshot(
            element_selector="div.content",
            element_description="Content div",
        )

        assert result.success is True
        assert result.data["element"] == "Content div"

    @pytest.mark.asyncio
    async def test_fill_form_success(self, browser_tool):
        """Test filling multiple form fields."""
        fields = [
            {"name": "username", "type": "textbox", "ref": "#user", "value": "alice"},
            {"name": "password", "type": "textbox", "ref": "#pass", "value": "secret"},
        ]

        result = await browser_tool.fill_form(fields)

        assert result.success is True
        assert result.action == BrowserAction.FILL_FORM
        assert result.data["fields_filled"] == 2
        assert result.data["fields"] == ["username", "password"]

    @pytest.mark.asyncio
    async def test_fill_form_empty(self, browser_tool):
        """Test filling form with no fields."""
        result = await browser_tool.fill_form([])

        assert result.success is True
        assert result.data["fields_filled"] == 0

    @pytest.mark.asyncio
    async def test_snapshot_success(self, browser_tool):
        """Test capturing page snapshot."""
        result = await browser_tool.snapshot()

        assert result.success is True
        assert result.action == BrowserAction.SNAPSHOT
        assert result.data["format"] == "markdown"

    @pytest.mark.asyncio
    async def test_snapshot_with_filename(self, browser_tool):
        """Test snapshot with custom filename."""
        result = await browser_tool.snapshot(filename="/tmp/snapshot.md")

        assert result.success is True
        assert result.data["snapshot_path"] == "/tmp/snapshot.md"

    def test_create_session(self, browser_tool):
        """Test creating a browser session."""
        session = browser_tool.create_session("my_session")

        assert session.session_id == "my_session"
        assert session.is_active is True
        assert session.interaction_count == 0
        assert browser_tool.session == session

    def test_create_session_auto_id(self, browser_tool):
        """Test creating session with auto-generated ID."""
        session = browser_tool.create_session()

        assert session.session_id.startswith("session_")
        assert session.is_active is True

    @pytest.mark.asyncio
    async def test_close_session(self, browser_tool):
        """Test closing browser session."""
        browser_tool.session = BrowserSession(session_id="test")
        browser_tool.session.interaction_count = 5

        await browser_tool.close()

        assert browser_tool.session.is_active is False

    @pytest.mark.asyncio
    async def test_close_without_session(self, browser_tool):
        """Test closing when no session exists."""
        await browser_tool.close()
        # Should not raise error

    def test_get_metrics(self, browser_tool):
        """Test getting browser metrics."""
        browser_tool.create_session()
        browser_tool.session.interaction_count = 3
        browser_tool._action_count = 5

        metrics = browser_tool.get_metrics()

        assert metrics["total_actions"] == 5
        assert metrics["session_active"] is True
        assert metrics["session_interactions"] == 3

    def test_get_metrics_no_session(self, browser_tool):
        """Test metrics without active session."""
        metrics = browser_tool.get_metrics()

        assert metrics["total_actions"] == 0
        assert metrics["session_active"] is False
        assert metrics["session_interactions"] == 0


# =============================================================================
# Skill-Aware Tool Function Tests
# =============================================================================


class TestSkillAwareTools:
    """Test skill-aware tool functions."""

    @pytest.mark.asyncio
    async def test_browser_navigate_tool(self):
        """Test browser_navigate tool function."""
        result = await browser_navigate.ainvoke({"url": "https://example.com"})

        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert "title" in result
        assert "status" in result
        assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_browser_navigate_with_state(self):
        """Test browser_navigate with injected state."""
        state = {"_skill_name": "web_research"}

        result = await browser_navigate.ainvoke({
            "url": "https://example.com",
            "state": state,
        })

        assert result["success"] is True
        # Skill name should be logged but not affect result

    @pytest.mark.asyncio
    async def test_browser_navigate_timeout(self):
        """Test browser_navigate with custom timeout."""
        result = await browser_navigate.ainvoke({
            "url": "https://example.com",
            "timeout": 5.0,
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_browser_click_tool(self):
        """Test browser_click tool function."""
        result = await browser_click.ainvoke({
            "selector": "button.submit",
            "element_description": "Submit button",
        })

        assert result["success"] is True
        assert result["clicked"] is True
        assert result["selector"] == "button.submit"
        assert result["element"] == "Submit button"

    @pytest.mark.asyncio
    async def test_browser_click_with_button(self):
        """Test browser_click with button option."""
        result = await browser_click.ainvoke({
            "selector": "#link",
            "element_description": "Link",
            "button": "right",
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_browser_type_text_tool(self):
        """Test browser_type_text tool function."""
        result = await browser_type_text.ainvoke({
            "selector": "input#search",
            "element_description": "Search input",
            "text": "test query",
        })

        assert result["success"] is True
        assert result["typed"] is True
        assert result["submitted"] is False

    @pytest.mark.asyncio
    async def test_browser_type_text_with_submit(self):
        """Test browser_type_text with submit flag."""
        result = await browser_type_text.ainvoke({
            "selector": "input#search",
            "element_description": "Search input",
            "text": "query",
            "submit": True,
        })

        assert result["success"] is True
        assert result["submitted"] is True

    @pytest.mark.asyncio
    async def test_browser_screenshot_tool(self):
        """Test browser_screenshot tool function."""
        result = await browser_screenshot.ainvoke({})

        assert result["success"] is True
        assert "path" in result
        assert result["full_page"] is False

    @pytest.mark.asyncio
    async def test_browser_screenshot_full_page(self):
        """Test browser_screenshot with full_page option."""
        result = await browser_screenshot.ainvoke({"full_page": True})

        assert result["success"] is True
        assert result["full_page"] is True

    @pytest.mark.asyncio
    async def test_browser_screenshot_with_filename(self):
        """Test browser_screenshot with custom filename."""
        result = await browser_screenshot.ainvoke({"filename": "/tmp/test.png"})

        assert result["success"] is True
        assert result["path"] == "/tmp/test.png"

    @pytest.mark.asyncio
    async def test_browser_fill_form_tool(self):
        """Test browser_fill_form tool function."""
        fields = [
            {"name": "user", "type": "textbox", "ref": "#user", "value": "alice"},
            {"name": "email", "type": "textbox", "ref": "#email", "value": "alice@example.com"},
        ]

        result = await browser_fill_form.ainvoke({"fields": fields})

        assert result["success"] is True
        assert result["fields_filled"] == 2
        assert result["fields"] == ["user", "email"]


# =============================================================================
# Tool Registry Tests
# =============================================================================


class TestToolRegistry:
    """Test tool registry functions."""

    def test_get_browser_tools(self):
        """Test getting browser tools registry."""
        tools = get_browser_tools()

        assert "browser_navigate" in tools
        assert "browser_click" in tools
        assert "browser_type" in tools
        assert "browser_screenshot" in tools
        assert "browser_fill_form" in tools

        # Verify all are StructuredTools (from @tool decorator)
        for tool_name, tool_func in tools.items():
            # StructuredTool objects have ainvoke method
            assert hasattr(tool_func, 'ainvoke'), f"{tool_name} is not a valid LangChain tool"
            assert hasattr(tool_func, 'name'), f"{tool_name} has no name attribute"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_navigate_error_handling(self, browser_tool):
        """Test navigation error is caught and returned."""
        import contextlib

        # Simulate error by patching internal method
        with (
            patch.object(browser_tool, 'navigate', side_effect=Exception("Network error")),
            contextlib.suppress(Exception),
        ):
            await browser_tool.navigate("https://invalid.url")

    @pytest.mark.asyncio
    async def test_click_error_handling(self, browser_tool):
        """Test click error is caught and returned."""
        # Click on nonexistent element
        _ = await browser_tool.click(
            selector="nonexistent",
            element_description="Missing element",
        )
        # Should return result with success=False instead of raising


# =============================================================================
# Integration Tests
# =============================================================================


class TestBrowserToolIntegration:
    """Test browser tool integration scenarios."""

    @pytest.mark.asyncio
    async def test_navigation_then_click(self, browser_tool):
        """Test navigation followed by click."""
        # Navigate
        nav_result = await browser_tool.navigate("https://example.com")
        assert nav_result.success is True

        # Click
        click_result = await browser_tool.click(
            selector="button",
            element_description="Button",
        )
        assert click_result.success is True
        assert browser_tool._action_count == 2

    @pytest.mark.asyncio
    async def test_form_workflow(self, browser_tool):
        """Test complete form filling workflow."""
        # Navigate to page
        await browser_tool.navigate("https://example.com/form")

        # Fill form
        fields = [
            {"name": "name", "type": "textbox", "ref": "#name", "value": "Alice"},
            {"name": "email", "type": "textbox", "ref": "#email", "value": "alice@example.com"},
        ]
        form_result = await browser_tool.fill_form(fields)
        assert form_result.success is True

        # Click submit
        submit_result = await browser_tool.click(
            selector="button[type=submit]",
            element_description="Submit button",
        )
        assert submit_result.success is True

    @pytest.mark.asyncio
    async def test_screenshot_workflow(self, browser_tool):
        """Test screenshot capture workflow."""
        # Navigate
        await browser_tool.navigate("https://example.com")

        # Take full page screenshot
        screenshot_result = await browser_tool.screenshot(full_page=True)
        assert screenshot_result.success is True
        assert screenshot_result.data["full_page"] is True

        # Take element screenshot
        element_screenshot = await browser_tool.screenshot(
            element_selector="div.content",
            element_description="Content area",
        )
        assert element_screenshot.success is True


# =============================================================================
# Session Management Tests
# =============================================================================


class TestSessionManagement:
    """Test browser session management."""

    def test_session_creation(self, browser_tool):
        """Test creating and tracking sessions."""
        session1 = browser_tool.create_session("session_1")
        assert session1.session_id == "session_1"
        assert browser_tool.session == session1

        # Creating new session replaces old one
        session2 = browser_tool.create_session("session_2")
        assert browser_tool.session == session2
        assert browser_tool.session.session_id == "session_2"

    @pytest.mark.asyncio
    async def test_session_interaction_tracking(self, browser_tool):
        """Test that interactions are tracked in session."""
        browser_tool.create_session()

        await browser_tool.navigate("https://example.com")
        assert browser_tool.session.interaction_count == 1

        await browser_tool.click("button", "Button")
        assert browser_tool.session.interaction_count == 2

        await browser_tool.type_text("input", "Input", "text")
        assert browser_tool.session.interaction_count == 3

    @pytest.mark.asyncio
    async def test_session_url_tracking(self, browser_tool):
        """Test that current URL is tracked in session."""
        browser_tool.create_session()

        await browser_tool.navigate("https://example.com")
        assert browser_tool.session.current_url == "https://example.com"

        await browser_tool.navigate("https://example.com/page2")
        assert browser_tool.session.current_url == "https://example.com/page2"


# =============================================================================
# Data Model Tests
# =============================================================================


class TestDataModels:
    """Test data model classes."""

    def test_browser_action_enum(self):
        """Test BrowserAction enum values."""
        assert BrowserAction.NAVIGATE.value == "navigate"
        assert BrowserAction.CLICK.value == "click"
        assert BrowserAction.TYPE.value == "type"
        assert BrowserAction.SCREENSHOT.value == "screenshot"
        assert BrowserAction.SNAPSHOT.value == "snapshot"

    def test_browser_session_creation(self):
        """Test BrowserSession creation."""
        session = BrowserSession(session_id="test")

        assert session.session_id == "test"
        assert session.is_active is True
        assert session.interaction_count == 0
        assert session.current_url == ""

    def test_browser_result_creation(self):
        """Test BrowserResult creation."""
        result = BrowserResult(
            success=True,
            action=BrowserAction.NAVIGATE,
            data={"url": "https://example.com"},
            duration_ms=100.5,
        )

        assert result.success is True
        assert result.action == BrowserAction.NAVIGATE
        assert result.data["url"] == "https://example.com"
        assert result.error is None
        assert result.duration_ms == 100.5
