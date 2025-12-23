"""Pytest configuration and fixtures for E2E tests.

This module provides:
- Playwright browser setup
- Shared fixtures for database clients
- Test data cleanup
- E2E test markers
- Screenshot capture on failure
- Performance baselines
"""

import os
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from src.core.logging import get_logger

logger = get_logger(__name__)


@pytest_asyncio.fixture
async def playwright_instance() -> AsyncGenerator[Playwright, None]:
    """Start Playwright instance for the test."""
    async with async_playwright() as playwright:
        yield playwright


@pytest_asyncio.fixture
async def browser(playwright_instance: Playwright) -> AsyncGenerator[Browser, None]:
    """Launch browser for E2E tests.

    Using Chromium for consistency. Can be configured via environment variables:
    - HEADED=1 to run in headed mode (see browser UI)
    - SLOWMO=500 to slow down operations for debugging
    """

    browser = await playwright_instance.chromium.launch(
        headless=not os.getenv("HEADED"),
        slow_mo=int(os.getenv("SLOWMO", "0")),
    )
    yield browser
    await browser.close()


@pytest_asyncio.fixture
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create a new browser context for each test.

    Each context is isolated (separate cookies, storage, etc.)
    """
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="UTC",
    )
    yield context
    await context.close()


@pytest_asyncio.fixture
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a new page for each test."""
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for the application."""
    return os.getenv("BASE_URL", "http://localhost:5179")


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Base URL for the API."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


def pytest_configure(config):
    """Register custom markers and configure E2E testing."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (requires running services)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running (> 30 seconds)")
    config.addinivalue_line("markers", "sprint49: mark test as Sprint 49 feature validation")
    config.addinivalue_line("markers", "sprint50: mark test as Sprint 50 feature validation")


def pytest_runtest_makereport(item, call):
    """Store test result for use in fixtures."""
    if call.when == "call":
        item.rep_call = item.rep_call if hasattr(item, "rep_call") else call


# Screenshot and trace capture on test failure
@pytest.fixture(autouse=True)
async def capture_on_failure(request, page: Page = None):
    """Capture screenshot and browser traces on test failure.

    Screenshots and traces are saved for debugging failed tests.
    Traces are automatically recorded by Playwright when traces are enabled.
    """
    yield

    # Check if test failed
    if hasattr(request, "node") and hasattr(request.node, "rep_call"):
        if request.node.rep_call.failed and page is not None:
            try:
                screenshots_dir = Path("tests/e2e/screenshots")
                screenshots_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = screenshots_dir / f"{request.node.name}_{timestamp}.png"

                await page.screenshot(path=str(screenshot_path))
                logger.info(f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")


@pytest.fixture(autouse=True)
def test_start_marker(request):
    """Print test start marker for better log readability."""
    print(f"\n{'='*70}")
    print(f"Starting Test: {request.node.name}")
    print(f"{'='*70}")
    yield
    print(f"\n{'='*70}")
    print(f"Finished Test: {request.node.name}")
    print(f"{'='*70}\n")
