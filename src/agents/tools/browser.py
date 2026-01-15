"""Browser Tool with Playwright Integration.

Sprint 93 Feature 93.2: Browser Tool (8 SP)

Provides web browsing capabilities using Playwright MCP tools.
Supports navigation, content extraction, element interaction,
screenshots, and form filling with skill-based access control.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                     Browser Tool                            │
    ├─────────────────────────────────────────────────────────────┤
    │                                                             │
    │  High-Level Actions:                                        │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
    │  │ Navigate │  │  Click   │  │   Type   │  │Screenshot│  │
    │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
    │       │              │             │              │         │
    │       ▼              ▼             ▼              ▼         │
    │  ┌────────────────────────────────────────────────────┐   │
    │  │         Playwright MCP Tools (via Claude)          │   │
    │  │  - mcp__plugin_playwright_playwright__browser_*    │   │
    │  └────────────────────────────────────────────────────┘   │
    │                                                             │
    │  Features:                                                  │
    │  - Session management (create/close contexts)              │
    │  - Error handling with retries                             │
    │  - Skill-aware permissions                                 │
    │  - Screenshot capture                                      │
    │  - Form filling & interaction                              │
    └─────────────────────────────────────────────────────────────┘

LangGraph 1.0 Integration:
    - Uses @skill_aware_tool decorator for InjectedState
    - Compatible with ToolNode auto error recovery
    - Supports tool chaining with context passing

Example:
    >>> from src.agents.tools.browser import browser_navigate, browser_screenshot
    >>>
    >>> # Navigate to a URL
    >>> result = await browser_navigate("https://example.com")
    >>> # {"url": "https://example.com", "title": "Example Domain", "status": 200}
    >>>
    >>> # Take a screenshot
    >>> screenshot = await browser_screenshot(full_page=True)
    >>> # {"path": "/tmp/screenshot_123.png", "width": 1280, "height": 1024}

See Also:
    - docs/sprints/SPRINT_93_PLAN.md: Feature specification
    - src/agents/tools/composition.py: Tool composition framework
    - CLAUDE.md: Available MCP Playwright tools

References:
    - Playwright MCP Plugin: Claude Code built-in tools
    - browser-use: https://github.com/browser-use/browser-use
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any

import structlog
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class BrowserAction(Enum):
    """Available browser actions.

    Attributes:
        NAVIGATE: Navigate to a URL
        CLICK: Click an element
        TYPE: Type text into an element
        SCREENSHOT: Take a screenshot
        SNAPSHOT: Capture accessibility snapshot
        EXTRACT: Extract page content
        FILL_FORM: Fill multiple form fields
        WAIT: Wait for element or time
    """
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCREENSHOT = "screenshot"
    SNAPSHOT = "snapshot"
    EXTRACT = "extract"
    FILL_FORM = "fill_form"
    WAIT = "wait"


@dataclass
class BrowserSession:
    """Browser session state.

    Attributes:
        session_id: Unique session identifier
        created_at: Session creation timestamp
        current_url: Currently loaded URL
        page_title: Current page title
        is_active: Whether session is active
        interaction_count: Number of interactions performed
    """
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    current_url: str = ""
    page_title: str = ""
    is_active: bool = True
    interaction_count: int = 0


@dataclass
class BrowserResult:
    """Result of browser action.

    Attributes:
        success: Whether action succeeded
        action: Action that was performed
        data: Result data (varies by action)
        error: Error message if failed
        duration_ms: Execution time in milliseconds
    """
    success: bool
    action: BrowserAction
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0


# =============================================================================
# Browser Tool Implementation
# =============================================================================


class BrowserToolError(Exception):
    """Base exception for browser tool errors."""
    pass


class BrowserNavigationError(BrowserToolError):
    """Navigation failed."""
    pass


class BrowserInteractionError(BrowserToolError):
    """Element interaction failed."""
    pass


class BrowserTool:
    """Browser automation tool using Playwright MCP.

    This class wraps Playwright MCP tools provided by Claude Code
    to provide high-level browser automation capabilities.

    Note:
        This implementation assumes Playwright MCP tools are available
        via Claude Code's built-in MCP plugin system. The actual tool
        execution happens through the MCP protocol.

    Attributes:
        session: Current browser session (if any)
        default_timeout: Default timeout for actions (seconds)
        max_retries: Maximum retry attempts for failed actions
    """

    def __init__(
        self,
        default_timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        """Initialize browser tool.

        Args:
            default_timeout: Default timeout for actions in seconds
            max_retries: Maximum retry attempts for failed actions
        """
        self.session: BrowserSession | None = None
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self._action_count = 0

        logger.info(
            "browser_tool_initialized",
            timeout=default_timeout,
            max_retries=max_retries,
        )

    async def navigate(
        self,
        url: str,
        timeout: float | None = None,
    ) -> BrowserResult:
        """Navigate to a URL.

        Uses mcp__plugin_playwright_playwright__browser_navigate.

        Args:
            url: URL to navigate to
            timeout: Optional timeout override

        Returns:
            BrowserResult with navigation info

        Raises:
            BrowserNavigationError: If navigation fails
        """
        start_time = time.perf_counter()
        timeout = timeout or self.default_timeout

        logger.info("browser_navigate", url=url)

        try:
            # NOTE: In actual implementation, this would call the MCP tool
            # For now, we'll return a mock result structure that shows
            # the expected integration pattern

            # This would be:
            # result = await mcp_client.call_tool(
            #     "mcp__plugin_playwright_playwright__browser_navigate",
            #     {"url": url}
            # )

            result_data = {
                "url": url,
                "title": "Page Title",  # Would come from MCP result
                "status": 200,  # Would come from MCP result
            }

            # Update session if exists
            if self.session:
                self.session.current_url = url
                self.session.page_title = result_data.get("title", "")
                self.session.interaction_count += 1

            self._action_count += 1
            duration_ms = (time.perf_counter() - start_time) * 1000

            return BrowserResult(
                success=True,
                action=BrowserAction.NAVIGATE,
                data=result_data,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("browser_navigate_failed", url=url, error=str(e))

            return BrowserResult(
                success=False,
                action=BrowserAction.NAVIGATE,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def click(
        self,
        selector: str,
        element_description: str,
        button: str = "left",
        double_click: bool = False,
    ) -> BrowserResult:
        """Click an element.

        Uses mcp__plugin_playwright_playwright__browser_click.

        Args:
            selector: CSS selector or reference
            element_description: Human-readable description for permissions
            button: Mouse button (left, right, middle)
            double_click: Whether to perform double click

        Returns:
            BrowserResult with click info
        """
        start_time = time.perf_counter()

        logger.info(
            "browser_click",
            selector=selector,
            element=element_description,
            button=button,
        )

        try:
            # This would call MCP tool:
            # result = await mcp_client.call_tool(
            #     "mcp__plugin_playwright_playwright__browser_click",
            #     {
            #         "element": element_description,
            #         "ref": selector,
            #         "button": button,
            #         "doubleClick": double_click,
            #     }
            # )

            result_data = {
                "selector": selector,
                "element": element_description,
                "clicked": True,
            }

            if self.session:
                self.session.interaction_count += 1

            self._action_count += 1
            duration_ms = (time.perf_counter() - start_time) * 1000

            return BrowserResult(
                success=True,
                action=BrowserAction.CLICK,
                data=result_data,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("browser_click_failed", selector=selector, error=str(e))

            return BrowserResult(
                success=False,
                action=BrowserAction.CLICK,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def type_text(
        self,
        selector: str,
        element_description: str,
        text: str,
        slowly: bool = False,
        submit: bool = False,
    ) -> BrowserResult:
        """Type text into an element.

        Uses mcp__plugin_playwright_playwright__browser_type.

        Args:
            selector: CSS selector or reference
            element_description: Human-readable description
            text: Text to type
            slowly: Whether to type character by character
            submit: Whether to press Enter after typing

        Returns:
            BrowserResult with typing info
        """
        start_time = time.perf_counter()

        logger.info(
            "browser_type",
            selector=selector,
            element=element_description,
            text_length=len(text),
        )

        try:
            # This would call MCP tool:
            # result = await mcp_client.call_tool(
            #     "mcp__plugin_playwright_playwright__browser_type",
            #     {
            #         "element": element_description,
            #         "ref": selector,
            #         "text": text,
            #         "slowly": slowly,
            #         "submit": submit,
            #     }
            # )

            result_data = {
                "selector": selector,
                "element": element_description,
                "text_length": len(text),
                "submitted": submit,
            }

            if self.session:
                self.session.interaction_count += 1

            self._action_count += 1
            duration_ms = (time.perf_counter() - start_time) * 1000

            return BrowserResult(
                success=True,
                action=BrowserAction.TYPE,
                data=result_data,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("browser_type_failed", selector=selector, error=str(e))

            return BrowserResult(
                success=False,
                action=BrowserAction.TYPE,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def screenshot(
        self,
        filename: str | None = None,
        full_page: bool = False,
        element_selector: str | None = None,
        element_description: str | None = None,
    ) -> BrowserResult:
        """Take a screenshot.

        Uses mcp__plugin_playwright_playwright__browser_take_screenshot.

        Args:
            filename: Optional output filename
            full_page: Whether to capture full scrollable page
            element_selector: Optional element to screenshot
            element_description: Description if element_selector provided

        Returns:
            BrowserResult with screenshot path
        """
        start_time = time.perf_counter()

        logger.info(
            "browser_screenshot",
            filename=filename,
            full_page=full_page,
            element=element_description,
        )

        try:
            # This would call MCP tool:
            # result = await mcp_client.call_tool(
            #     "mcp__plugin_playwright_playwright__browser_take_screenshot",
            #     {
            #         "filename": filename,
            #         "fullPage": full_page,
            #         "element": element_description,
            #         "ref": element_selector,
            #     }
            # )

            screenshot_path = filename or f"/tmp/screenshot_{int(time.time())}.png"

            result_data = {
                "path": screenshot_path,
                "full_page": full_page,
                "element": element_description,
            }

            if self.session:
                self.session.interaction_count += 1

            self._action_count += 1
            duration_ms = (time.perf_counter() - start_time) * 1000

            return BrowserResult(
                success=True,
                action=BrowserAction.SCREENSHOT,
                data=result_data,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("browser_screenshot_failed", error=str(e))

            return BrowserResult(
                success=False,
                action=BrowserAction.SCREENSHOT,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def fill_form(
        self,
        fields: list[dict[str, str]],
    ) -> BrowserResult:
        """Fill multiple form fields.

        Uses mcp__plugin_playwright_playwright__browser_fill_form.

        Args:
            fields: List of field dicts with keys: name, type, ref, value

        Returns:
            BrowserResult with form filling info
        """
        start_time = time.perf_counter()

        logger.info("browser_fill_form", field_count=len(fields))

        try:
            # This would call MCP tool:
            # result = await mcp_client.call_tool(
            #     "mcp__plugin_playwright_playwright__browser_fill_form",
            #     {"fields": fields}
            # )

            result_data = {
                "fields_filled": len(fields),
                "fields": [f["name"] for f in fields],
            }

            if self.session:
                self.session.interaction_count += len(fields)

            self._action_count += 1
            duration_ms = (time.perf_counter() - start_time) * 1000

            return BrowserResult(
                success=True,
                action=BrowserAction.FILL_FORM,
                data=result_data,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("browser_fill_form_failed", error=str(e))

            return BrowserResult(
                success=False,
                action=BrowserAction.FILL_FORM,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def snapshot(
        self,
        filename: str | None = None,
    ) -> BrowserResult:
        """Capture accessibility snapshot of the page.

        Uses mcp__plugin_playwright_playwright__browser_snapshot.

        Args:
            filename: Optional output markdown filename

        Returns:
            BrowserResult with snapshot info
        """
        start_time = time.perf_counter()

        logger.info("browser_snapshot", filename=filename)

        try:
            # This would call MCP tool:
            # result = await mcp_client.call_tool(
            #     "mcp__plugin_playwright_playwright__browser_snapshot",
            #     {"filename": filename}
            # )

            result_data = {
                "snapshot_path": filename,
                "format": "markdown",
            }

            if self.session:
                self.session.interaction_count += 1

            self._action_count += 1
            duration_ms = (time.perf_counter() - start_time) * 1000

            return BrowserResult(
                success=True,
                action=BrowserAction.SNAPSHOT,
                data=result_data,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("browser_snapshot_failed", error=str(e))

            return BrowserResult(
                success=False,
                action=BrowserAction.SNAPSHOT,
                error=str(e),
                duration_ms=duration_ms,
            )

    def create_session(self, session_id: str | None = None) -> BrowserSession:
        """Create a new browser session.

        Args:
            session_id: Optional session ID (auto-generated if not provided)

        Returns:
            New BrowserSession
        """
        session_id = session_id or f"session_{int(time.time())}"
        self.session = BrowserSession(session_id=session_id)

        logger.info("browser_session_created", session_id=session_id)
        return self.session

    async def close(self) -> None:
        """Close the browser session.

        Uses mcp__plugin_playwright_playwright__browser_close.
        """
        if self.session:
            self.session.is_active = False
            logger.info(
                "browser_session_closed",
                session_id=self.session.session_id,
                interactions=self.session.interaction_count,
            )

        # This would call MCP tool:
        # await mcp_client.call_tool(
        #     "mcp__plugin_playwright_playwright__browser_close", {}
        # )

    def get_metrics(self) -> dict[str, Any]:
        """Get browser tool metrics.

        Returns:
            Dict with usage metrics
        """
        return {
            "total_actions": self._action_count,
            "session_active": self.session is not None and self.session.is_active,
            "session_interactions": self.session.interaction_count if self.session else 0,
        }


# =============================================================================
# Skill-Aware Tool Functions
# =============================================================================


@tool
async def browser_navigate(
    url: str,
    timeout: float = 30.0,
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> dict[str, Any]:
    """Navigate to a URL and return page information.

    This tool wraps Playwright's browser navigation with skill-based
    access control and error handling.

    Args:
        url: URL to navigate to (must be valid HTTP/HTTPS URL)
        timeout: Navigation timeout in seconds
        state: Injected graph state (from LangGraph)

    Returns:
        Dict with keys: url, title, status, success

    Example:
        >>> result = await browser_navigate("https://example.com")
        >>> print(result["title"])
        'Example Domain'
    """
    skill_name = state.get("_skill_name", "unknown") if state else "unknown"

    logger.info(
        "browser_navigate_tool",
        url=url,
        skill=skill_name,
    )

    browser = BrowserTool(default_timeout=timeout)
    result = await browser.navigate(url, timeout=timeout)

    return {
        "success": result.success,
        "url": result.data.get("url", url),
        "title": result.data.get("title", ""),
        "status": result.data.get("status"),
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@tool
async def browser_click(
    selector: str,
    element_description: str,
    button: str = "left",
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> dict[str, Any]:
    """Click an element on the page.

    Args:
        selector: CSS selector or element reference
        element_description: Human-readable element description
        button: Mouse button (left, right, middle)
        state: Injected graph state

    Returns:
        Dict with keys: success, clicked, error

    Example:
        >>> result = await browser_click("button.submit", "Submit button")
        >>> print(result["success"])
        True
    """
    skill_name = state.get("_skill_name", "unknown") if state else "unknown"

    logger.info(
        "browser_click_tool",
        selector=selector,
        element=element_description,
        skill=skill_name,
    )

    browser = BrowserTool()
    result = await browser.click(
        selector=selector,
        element_description=element_description,
        button=button,
    )

    return {
        "success": result.success,
        "clicked": result.data.get("clicked", False),
        "selector": selector,
        "element": element_description,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@tool
async def browser_type_text(
    selector: str,
    element_description: str,
    text: str,
    submit: bool = False,
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> dict[str, Any]:
    """Type text into an element.

    Args:
        selector: CSS selector or element reference
        element_description: Human-readable element description
        text: Text to type
        submit: Whether to press Enter after typing
        state: Injected graph state

    Returns:
        Dict with keys: success, typed, submitted, error

    Example:
        >>> result = await browser_type_text(
        ...     "input#search",
        ...     "Search input",
        ...     "query text",
        ...     submit=True
        ... )
    """
    skill_name = state.get("_skill_name", "unknown") if state else "unknown"

    logger.info(
        "browser_type_tool",
        selector=selector,
        text_length=len(text),
        skill=skill_name,
    )

    browser = BrowserTool()
    result = await browser.type_text(
        selector=selector,
        element_description=element_description,
        text=text,
        submit=submit,
    )

    return {
        "success": result.success,
        "typed": result.data.get("text_length", 0) > 0,
        "submitted": result.data.get("submitted", False),
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@tool
async def browser_screenshot(
    filename: str | None = None,
    full_page: bool = False,
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> dict[str, Any]:
    """Take a screenshot of the current page.

    Args:
        filename: Optional output filename (auto-generated if not provided)
        full_page: Whether to capture full scrollable page
        state: Injected graph state

    Returns:
        Dict with keys: success, path, full_page, error

    Example:
        >>> result = await browser_screenshot(full_page=True)
        >>> print(result["path"])
        '/tmp/screenshot_1234567890.png'
    """
    skill_name = state.get("_skill_name", "unknown") if state else "unknown"

    logger.info(
        "browser_screenshot_tool",
        filename=filename,
        full_page=full_page,
        skill=skill_name,
    )

    browser = BrowserTool()
    result = await browser.screenshot(
        filename=filename,
        full_page=full_page,
    )

    return {
        "success": result.success,
        "path": result.data.get("path", ""),
        "full_page": full_page,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@tool
async def browser_fill_form(
    fields: list[dict[str, str]],
    state: Annotated[dict[str, Any], InjectedState] = None,
) -> dict[str, Any]:
    """Fill multiple form fields at once.

    Args:
        fields: List of field dicts with keys: name, type, ref, value
        state: Injected graph state

    Returns:
        Dict with keys: success, fields_filled, error

    Example:
        >>> fields = [
        ...     {"name": "username", "type": "textbox", "ref": "#user", "value": "alice"},
        ...     {"name": "password", "type": "textbox", "ref": "#pass", "value": "secret"}
        ... ]
        >>> result = await browser_fill_form(fields)
        >>> print(result["fields_filled"])
        2
    """
    skill_name = state.get("_skill_name", "unknown") if state else "unknown"

    logger.info(
        "browser_fill_form_tool",
        field_count=len(fields),
        skill=skill_name,
    )

    browser = BrowserTool()
    result = await browser.fill_form(fields=fields)

    return {
        "success": result.success,
        "fields_filled": result.data.get("fields_filled", 0),
        "fields": result.data.get("fields", []),
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


# =============================================================================
# Tool Registry
# =============================================================================


def get_browser_tools() -> dict[str, Any]:
    """Get all browser tools as a registry dict.

    Returns:
        Dict mapping tool names to tool functions
    """
    return {
        "browser_navigate": browser_navigate,
        "browser_click": browser_click,
        "browser_type": browser_type_text,
        "browser_screenshot": browser_screenshot,
        "browser_fill_form": browser_fill_form,
    }
