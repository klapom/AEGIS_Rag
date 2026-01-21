"""Browser Tool Executor with Playwright.

Sprint 103 Feature 103.1: Execute browser automation tasks using Playwright.
Sprint 103 Feature 103.2: Security validation for browser operations.

This tool allows LLM agents to perform browser automation including navigation,
clicking, screenshots, and JavaScript evaluation with security controls.
"""

import asyncio
import base64
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from playwright.async_api import Browser, Page, async_playwright

from src.domains.llm_integration.tools.builtin.browser_security import (
    is_javascript_safe,
    is_url_safe,
    validate_selector,
)
from src.domains.llm_integration.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


class BrowserAction(str, Enum):
    """Supported browser actions."""

    NAVIGATE = "navigate"
    CLICK = "click"
    SCREENSHOT = "screenshot"
    EVALUATE = "evaluate"
    GET_TEXT = "get_text"
    FILL = "fill"
    TYPE = "type"


# Global browser instance for connection pooling
_browser_instance: Browser | None = None
_browser_lock = asyncio.Lock()


async def get_browser() -> Browser:
    """Get or create a shared browser instance.

    Returns:
        Browser instance

    Note:
        Uses connection pooling to avoid browser startup overhead.
    """
    global _browser_instance

    async with _browser_lock:
        if _browser_instance is None or not _browser_instance.is_connected():
            logger.info("browser_starting")
            playwright = await async_playwright().start()
            _browser_instance = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            logger.info("browser_started")

        return _browser_instance


async def close_browser() -> None:
    """Close the shared browser instance."""
    global _browser_instance

    async with _browser_lock:
        if _browser_instance is not None:
            logger.info("browser_closing")
            await _browser_instance.close()
            _browser_instance = None
            logger.info("browser_closed")


# Browser Tool Schemas

NAVIGATE_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "URL to navigate to",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30, max: 60)",
            "default": 30,
            "minimum": 1,
            "maximum": 60,
        },
        "wait_until": {
            "type": "string",
            "description": "When to consider navigation complete: load, domcontentloaded, networkidle",
            "default": "load",
            "enum": ["load", "domcontentloaded", "networkidle"],
        },
    },
    "required": ["url"],
}


CLICK_SCHEMA = {
    "type": "object",
    "properties": {
        "selector": {
            "type": "string",
            "description": "CSS selector of element to click",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30, max: 60)",
            "default": 30,
            "minimum": 1,
            "maximum": 60,
        },
    },
    "required": ["selector"],
}


SCREENSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "selector": {
            "type": "string",
            "description": "CSS selector of element to screenshot (optional, full page if not provided)",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30, max: 60)",
            "default": 30,
            "minimum": 1,
            "maximum": 60,
        },
        "full_page": {
            "type": "boolean",
            "description": "Capture full scrollable page (default: true)",
            "default": True,
        },
    },
    "required": [],
}


EVALUATE_SCHEMA = {
    "type": "object",
    "properties": {
        "expression": {
            "type": "string",
            "description": "JavaScript expression to evaluate",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30, max: 60)",
            "default": 30,
            "minimum": 1,
            "maximum": 60,
        },
    },
    "required": ["expression"],
}


GET_TEXT_SCHEMA = {
    "type": "object",
    "properties": {
        "selector": {
            "type": "string",
            "description": "CSS selector of element to get text from",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30, max: 60)",
            "default": 30,
            "minimum": 1,
            "maximum": 60,
        },
    },
    "required": ["selector"],
}


FILL_SCHEMA = {
    "type": "object",
    "properties": {
        "selector": {
            "type": "string",
            "description": "CSS selector of input element",
        },
        "value": {
            "type": "string",
            "description": "Value to fill",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30, max: 60)",
            "default": 30,
            "minimum": 1,
            "maximum": 60,
        },
    },
    "required": ["selector", "value"],
}


TYPE_SCHEMA = {
    "type": "object",
    "properties": {
        "selector": {
            "type": "string",
            "description": "CSS selector of input element",
        },
        "text": {
            "type": "string",
            "description": "Text to type character by character",
        },
        "delay": {
            "type": "integer",
            "description": "Delay between keystrokes in milliseconds (default: 100)",
            "default": 100,
            "minimum": 0,
            "maximum": 1000,
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30, max: 60)",
            "default": 30,
            "minimum": 1,
            "maximum": 60,
        },
    },
    "required": ["selector", "text"],
}


# Tool Registration


@ToolRegistry.register(
    name="browser_navigate",
    description="Navigate browser to a URL. Creates a new page if needed.",
    parameters=NAVIGATE_SCHEMA,
    requires_sandbox=False,
    metadata={
        "category": "browser",
        "danger_level": "low",
        "version": "1.0.0",
    },
)
async def browser_navigate(
    url: str,
    timeout: int = 30,
    wait_until: str = "load",
) -> dict[str, Any]:
    """Navigate browser to URL.

    Args:
        url: URL to navigate to
        timeout: Navigation timeout in seconds
        wait_until: When to consider navigation complete

    Returns:
        Dict with success status and page title

    Examples:
        >>> result = await browser_navigate("https://example.com")
        >>> result["success"]
        True
        >>> "title" in result
        True
    """
    logger.info("browser_navigate_called", url=url, timeout=timeout)

    # Security check: validate URL
    security_check = is_url_safe(url)
    if not security_check.safe:
        logger.error("url_blocked", url=url, reason=security_check.reason)
        return {
            "success": False,
            "error": f"URL blocked: {security_check.reason}",
        }

    # Enforce maximum timeout
    if timeout > 60:
        logger.warning("timeout_clamped", requested=timeout, clamped=60)
        timeout = 60

    try:
        browser = await get_browser()
        page = await browser.new_page()

        # Navigate to URL
        await page.goto(
            url,
            timeout=timeout * 1000,  # Playwright uses milliseconds
            wait_until=wait_until,
        )

        title = await page.title()

        logger.info("browser_navigate_success", url=url, title=title)

        return {
            "success": True,
            "url": page.url,
            "title": title,
        }

    except TimeoutError:
        logger.warning("browser_navigate_timeout", url=url, timeout=timeout)
        return {
            "success": False,
            "error": f"Navigation timed out after {timeout} seconds",
        }

    except Exception as e:
        logger.error("browser_navigate_failed", url=url, error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Navigation failed: {e}",
        }


@ToolRegistry.register(
    name="browser_click",
    description="Click an element on the current page using CSS selector.",
    parameters=CLICK_SCHEMA,
    requires_sandbox=False,
    metadata={
        "category": "browser",
        "danger_level": "low",
        "version": "1.0.0",
    },
)
async def browser_click(
    selector: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """Click element on page.

    Args:
        selector: CSS selector of element to click
        timeout: Operation timeout in seconds

    Returns:
        Dict with success status

    Examples:
        >>> result = await browser_click("button.submit")
        >>> result["success"]
        True
    """
    logger.info("browser_click_called", selector=selector, timeout=timeout)

    # Security check: validate selector
    selector_check = validate_selector(selector)
    if not selector_check.safe:
        logger.error("selector_invalid", selector=selector, reason=selector_check.reason)
        return {
            "success": False,
            "error": f"Invalid selector: {selector_check.reason}",
        }

    # Enforce maximum timeout
    if timeout > 60:
        logger.warning("timeout_clamped", requested=timeout, clamped=60)
        timeout = 60

    try:
        browser = await get_browser()
        pages = browser.contexts[0].pages if browser.contexts else []

        if not pages:
            return {
                "success": False,
                "error": "No page available. Navigate to a URL first.",
            }

        page = pages[-1]  # Use most recent page

        # Click element
        await page.click(selector, timeout=timeout * 1000)

        logger.info("browser_click_success", selector=selector)

        return {
            "success": True,
            "selector": selector,
        }

    except TimeoutError:
        logger.warning("browser_click_timeout", selector=selector, timeout=timeout)
        return {
            "success": False,
            "error": f"Element not found or not clickable after {timeout} seconds",
        }

    except Exception as e:
        logger.error("browser_click_failed", selector=selector, error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Click failed: {e}",
        }


@ToolRegistry.register(
    name="browser_screenshot",
    description="Take a screenshot of the current page or specific element.",
    parameters=SCREENSHOT_SCHEMA,
    requires_sandbox=False,
    metadata={
        "category": "browser",
        "danger_level": "low",
        "version": "1.0.0",
    },
)
async def browser_screenshot(
    selector: str | None = None,
    timeout: int = 30,
    full_page: bool = True,
) -> dict[str, Any]:
    """Take screenshot of page or element.

    Args:
        selector: CSS selector of element (optional, full page if not provided)
        timeout: Operation timeout in seconds
        full_page: Capture full scrollable page

    Returns:
        Dict with base64-encoded screenshot data

    Examples:
        >>> result = await browser_screenshot()
        >>> result["success"]
        True
        >>> "data" in result
        True
    """
    logger.info(
        "browser_screenshot_called", selector=selector, timeout=timeout, full_page=full_page
    )

    # Security check: validate selector if provided
    if selector:
        selector_check = validate_selector(selector)
        if not selector_check.safe:
            logger.error("selector_invalid", selector=selector, reason=selector_check.reason)
            return {
                "success": False,
                "error": f"Invalid selector: {selector_check.reason}",
            }

    # Enforce maximum timeout
    if timeout > 60:
        logger.warning("timeout_clamped", requested=timeout, clamped=60)
        timeout = 60

    try:
        browser = await get_browser()
        pages = browser.contexts[0].pages if browser.contexts else []

        if not pages:
            return {
                "success": False,
                "error": "No page available. Navigate to a URL first.",
            }

        page = pages[-1]  # Use most recent page

        if selector:
            # Screenshot specific element
            element = await page.wait_for_selector(selector, timeout=timeout * 1000)
            screenshot_bytes = await element.screenshot()
        else:
            # Screenshot full page
            screenshot_bytes = await page.screenshot(full_page=full_page)

        # Encode as base64
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        logger.info(
            "browser_screenshot_success",
            selector=selector,
            size_bytes=len(screenshot_bytes),
        )

        return {
            "success": True,
            "data": screenshot_base64,
            "format": "png",
            "selector": selector,
        }

    except TimeoutError:
        logger.warning("browser_screenshot_timeout", selector=selector, timeout=timeout)
        return {
            "success": False,
            "error": f"Element not found after {timeout} seconds",
        }

    except Exception as e:
        logger.error("browser_screenshot_failed", selector=selector, error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Screenshot failed: {e}",
        }


@ToolRegistry.register(
    name="browser_evaluate",
    description="Evaluate JavaScript expression on the current page.",
    parameters=EVALUATE_SCHEMA,
    requires_sandbox=False,
    metadata={
        "category": "browser",
        "danger_level": "medium",
        "version": "1.0.0",
    },
)
async def browser_evaluate(
    expression: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """Evaluate JavaScript expression on page.

    Args:
        expression: JavaScript expression to evaluate
        timeout: Operation timeout in seconds

    Returns:
        Dict with evaluation result

    Examples:
        >>> result = await browser_evaluate("document.title")
        >>> result["success"]
        True
        >>> "result" in result
        True
    """
    logger.info("browser_evaluate_called", expression=expression[:100], timeout=timeout)

    # Security check: validate JavaScript
    js_check = is_javascript_safe(expression)
    if not js_check.safe:
        logger.error("javascript_blocked", reason=js_check.reason)
        return {
            "success": False,
            "error": f"JavaScript blocked: {js_check.reason}",
        }

    # Enforce maximum timeout
    if timeout > 60:
        logger.warning("timeout_clamped", requested=timeout, clamped=60)
        timeout = 60

    try:
        browser = await get_browser()
        pages = browser.contexts[0].pages if browser.contexts else []

        if not pages:
            return {
                "success": False,
                "error": "No page available. Navigate to a URL first.",
            }

        page = pages[-1]  # Use most recent page

        # Evaluate expression (note: page.evaluate doesn't support timeout parameter)
        result = await page.evaluate(expression)

        logger.info("browser_evaluate_success", expression=expression[:100])

        return {
            "success": True,
            "result": result,
        }

    except TimeoutError:
        logger.warning("browser_evaluate_timeout", expression=expression[:100], timeout=timeout)
        return {
            "success": False,
            "error": f"Evaluation timed out after {timeout} seconds",
        }

    except Exception as e:
        logger.error(
            "browser_evaluate_failed",
            expression=expression[:100],
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": f"Evaluation failed: {e}",
        }


@ToolRegistry.register(
    name="browser_get_text",
    description="Get text content of an element using CSS selector.",
    parameters=GET_TEXT_SCHEMA,
    requires_sandbox=False,
    metadata={
        "category": "browser",
        "danger_level": "low",
        "version": "1.0.0",
    },
)
async def browser_get_text(
    selector: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """Get text content of element.

    Args:
        selector: CSS selector of element
        timeout: Operation timeout in seconds

    Returns:
        Dict with text content

    Examples:
        >>> result = await browser_get_text("h1")
        >>> result["success"]
        True
        >>> "text" in result
        True
    """
    logger.info("browser_get_text_called", selector=selector, timeout=timeout)

    # Security check: validate selector
    selector_check = validate_selector(selector)
    if not selector_check.safe:
        logger.error("selector_invalid", selector=selector, reason=selector_check.reason)
        return {
            "success": False,
            "error": f"Invalid selector: {selector_check.reason}",
        }

    # Enforce maximum timeout
    if timeout > 60:
        logger.warning("timeout_clamped", requested=timeout, clamped=60)
        timeout = 60

    try:
        browser = await get_browser()
        pages = browser.contexts[0].pages if browser.contexts else []

        if not pages:
            return {
                "success": False,
                "error": "No page available. Navigate to a URL first.",
            }

        page = pages[-1]  # Use most recent page

        # Get element and text
        element = await page.wait_for_selector(selector, timeout=timeout * 1000)
        text = await element.text_content()

        logger.info("browser_get_text_success", selector=selector, text_length=len(text or ""))

        return {
            "success": True,
            "text": text or "",
            "selector": selector,
        }

    except TimeoutError:
        logger.warning("browser_get_text_timeout", selector=selector, timeout=timeout)
        return {
            "success": False,
            "error": f"Element not found after {timeout} seconds",
        }

    except Exception as e:
        logger.error("browser_get_text_failed", selector=selector, error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Get text failed: {e}",
        }


@ToolRegistry.register(
    name="browser_fill",
    description="Fill an input element with a value.",
    parameters=FILL_SCHEMA,
    requires_sandbox=False,
    metadata={
        "category": "browser",
        "danger_level": "low",
        "version": "1.0.0",
    },
)
async def browser_fill(
    selector: str,
    value: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """Fill input element with value.

    Args:
        selector: CSS selector of input element
        value: Value to fill
        timeout: Operation timeout in seconds

    Returns:
        Dict with success status

    Examples:
        >>> result = await browser_fill("input[name='email']", "test@example.com")
        >>> result["success"]
        True
    """
    logger.info("browser_fill_called", selector=selector, timeout=timeout)

    # Security check: validate selector
    selector_check = validate_selector(selector)
    if not selector_check.safe:
        logger.error("selector_invalid", selector=selector, reason=selector_check.reason)
        return {
            "success": False,
            "error": f"Invalid selector: {selector_check.reason}",
        }

    # Enforce maximum timeout
    if timeout > 60:
        logger.warning("timeout_clamped", requested=timeout, clamped=60)
        timeout = 60

    try:
        browser = await get_browser()
        pages = browser.contexts[0].pages if browser.contexts else []

        if not pages:
            return {
                "success": False,
                "error": "No page available. Navigate to a URL first.",
            }

        page = pages[-1]  # Use most recent page

        # Fill element
        await page.fill(selector, value, timeout=timeout * 1000)

        logger.info("browser_fill_success", selector=selector)

        return {
            "success": True,
            "selector": selector,
        }

    except TimeoutError:
        logger.warning("browser_fill_timeout", selector=selector, timeout=timeout)
        return {
            "success": False,
            "error": f"Element not found or not fillable after {timeout} seconds",
        }

    except Exception as e:
        logger.error("browser_fill_failed", selector=selector, error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Fill failed: {e}",
        }


@ToolRegistry.register(
    name="browser_type",
    description="Type text into an input element character by character.",
    parameters=TYPE_SCHEMA,
    requires_sandbox=False,
    metadata={
        "category": "browser",
        "danger_level": "low",
        "version": "1.0.0",
    },
)
async def browser_type(
    selector: str,
    text: str,
    delay: int = 100,
    timeout: int = 30,
) -> dict[str, Any]:
    """Type text into input element.

    Args:
        selector: CSS selector of input element
        text: Text to type character by character
        delay: Delay between keystrokes in milliseconds
        timeout: Operation timeout in seconds

    Returns:
        Dict with success status

    Examples:
        >>> result = await browser_type("input[name='search']", "hello world", delay=50)
        >>> result["success"]
        True
    """
    logger.info("browser_type_called", selector=selector, timeout=timeout, delay=delay)

    # Security check: validate selector
    selector_check = validate_selector(selector)
    if not selector_check.safe:
        logger.error("selector_invalid", selector=selector, reason=selector_check.reason)
        return {
            "success": False,
            "error": f"Invalid selector: {selector_check.reason}",
        }

    # Enforce maximum timeout
    if timeout > 60:
        logger.warning("timeout_clamped", requested=timeout, clamped=60)
        timeout = 60

    try:
        browser = await get_browser()
        pages = browser.contexts[0].pages if browser.contexts else []

        if not pages:
            return {
                "success": False,
                "error": "No page available. Navigate to a URL first.",
            }

        page = pages[-1]  # Use most recent page

        # Type text
        await page.type(selector, text, delay=delay, timeout=timeout * 1000)

        logger.info("browser_type_success", selector=selector, text_length=len(text))

        return {
            "success": True,
            "selector": selector,
        }

    except TimeoutError:
        logger.warning("browser_type_timeout", selector=selector, timeout=timeout)
        return {
            "success": False,
            "error": f"Element not found or not typable after {timeout} seconds",
        }

    except Exception as e:
        logger.error("browser_type_failed", selector=selector, error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Type failed: {e}",
        }
