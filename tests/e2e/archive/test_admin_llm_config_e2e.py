"""E2E Tests for Admin LLM Configuration - Python Playwright.

Tests the full frontend LLM configuration workflow.
Compatible with existing pytest infrastructure.

Pytest markers:
  - @pytest.mark.e2e: End-to-end test marker
  - @pytest.mark.admin: Admin feature tests
  - @pytest.mark.ui: UI-focused tests

Usage:
  pytest tests/e2e/test_admin_llm_config_e2e.py -v
  pytest tests/e2e/test_admin_llm_config_e2e.py -k "persistence" -v
  pytest -m "e2e and not slow" tests/e2e/

Note:
  Requires playwright package: pip install playwright && playwright install
  Skipped automatically if playwright is not installed (e.g., on DGX Spark).
"""

import json

import pytest

# Skip entire module if playwright is not installed (e.g., on DGX Spark)
playwright_async = pytest.importorskip("playwright.async_api", reason="playwright not installed")
async_playwright = playwright_async.async_playwright
Page = playwright_async.Page
expect = playwright_async.expect


class TestAdminLLMConfigE2E:
    """E2E tests for Admin LLM Configuration page (Sprint 36, Feature 36.3)."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    @pytest.mark.ui
    async def test_llm_config_page_loads(self):
        """Test Admin LLM Config page loads correctly."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto(
                    "http://localhost:5179/admin/llm-config", wait_until="domcontentloaded"
                )

                # Wait for page to be visible
                llm_config = page.locator('[data-testid="llm-config-page"]')
                await expect(llm_config).to_be_visible(timeout=10000)

            finally:
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_all_use_cases_displayed(self):
        """Test all 6 use cases are displayed on the page."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto(
                    "http://localhost:5179/admin/llm-config", wait_until="domcontentloaded"
                )

                use_cases = [
                    "intent_classification",
                    "entity_extraction",
                    "answer_generation",
                    "followup_titles",
                    "query_decomposition",
                    "vision_vlm",
                ]

                for use_case in use_cases:
                    selector = page.locator(f'[data-testid="usecase-selector-{use_case}"]')
                    await expect(selector).to_be_visible(timeout=5000)

            finally:
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_model_dropdowns_exist(self):
        """Test that all model dropdowns exist and are enabled."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")

                use_cases = [
                    "intent_classification",
                    "entity_extraction",
                    "answer_generation",
                    "followup_titles",
                    "query_decomposition",
                    "vision_vlm",
                ]

                for use_case in use_cases:
                    dropdown = page.locator(f'[data-testid="model-dropdown-{use_case}"]')
                    await expect(dropdown).to_be_visible()
                    await expect(dropdown).to_be_enabled()

            finally:
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_model_selection_saves_to_localstorage(self):
        """Test that model selections are saved to localStorage."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")

                # Clear localStorage
                await page.evaluate("() => localStorage.clear()")

                # Select a model
                dropdown = page.locator('[data-testid="model-dropdown-intent_classification"]')
                await dropdown.select_option(index=1)

                # Click save button
                save_button = page.locator('[data-testid="save-config-button"]')
                await save_button.click()

                # Wait for save success message
                success_msg = page.get_by_text("Saved!", exact=False)
                await expect(success_msg).to_be_visible(timeout=5000)

                # Verify localStorage
                config_json = await page.evaluate(
                    "() => localStorage.getItem('aegis-rag-llm-config')"
                )

                assert config_json is not None, "Config not found in localStorage"
                config = json.loads(config_json)

                assert isinstance(config, list), "Config should be a list"
                assert len(config) == 6, "Config should have 6 use cases"
                assert any(
                    c["useCase"] == "intent_classification" for c in config
                ), "intent_classification should be in config"

            finally:
                await context.close()
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_configuration_persists_on_reload(self):
        """Test that configuration persists after page reload."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")

                # Clear localStorage to start fresh
                await page.evaluate("() => localStorage.clear()")

                # Select a specific model
                target_model = "ollama/llama3.2:8b"
                dropdown = page.locator('[data-testid="model-dropdown-entity_extraction"]')
                await dropdown.select_option(value=target_model)

                # Save
                save_button = page.locator('[data-testid="save-config-button"]')
                await save_button.click()

                # Wait for success
                await expect(page.get_by_text("Saved!")).to_be_visible(timeout=5000)

                # Reload page
                await page.reload(wait_until="domcontentloaded")

                # Verify selection persisted
                reloaded_dropdown = page.locator('[data-testid="model-dropdown-entity_extraction"]')
                selected_value = await reloaded_dropdown.input_value()

                assert (
                    selected_value == target_model
                ), f"Expected {target_model}, got {selected_value}"

            finally:
                await context.close()
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_vision_models_filtered_for_vlm_use_case(self):
        """Test that only vision-capable models appear for VLM use case."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")

                vlm_dropdown = page.locator('[data-testid="model-dropdown-vision_vlm"]')

                # Get all options
                options = await vlm_dropdown.locator("option").all_text_contents()

                assert len(options) > 0, "VLM dropdown should have options"

                # Check that at least some are vision models
                vision_options = [
                    opt
                    for opt in options
                    if any(
                        vl in opt
                        for vl in [
                            "VL",
                            "Vision",
                            "4o",
                            "vision",
                            "vl",
                        ]
                    )
                ]

                assert len(vision_options) > 0, "Should have vision-capable models"

            finally:
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_refresh_models_button_clickable(self):
        """Test that Refresh Models button is clickable."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")

                refresh_button = page.locator('[data-testid="refresh-models-button"]')
                await expect(refresh_button).to_be_visible()
                await expect(refresh_button).to_be_enabled()

                # Click should not throw
                await refresh_button.click()

            finally:
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_multiple_model_selections(self):
        """Test changing multiple model selections in one session."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")
                await page.evaluate("() => localStorage.clear()")

                # Change multiple use cases
                use_cases_to_change = [
                    ("intent_classification", "ollama/llama3.2:8b"),
                    ("entity_extraction", "ollama/qwen3:32b"),
                    ("answer_generation", "ollama/llama3.2:8b"),
                ]

                for use_case, model_id in use_cases_to_change:
                    dropdown = page.locator(f'[data-testid="model-dropdown-{use_case}"]')
                    await dropdown.select_option(value=model_id)

                # Save
                save_button = page.locator('[data-testid="save-config-button"]')
                await save_button.click()
                await expect(page.get_by_text("Saved!")).to_be_visible(timeout=5000)

                # Verify all saved
                config_json = await page.evaluate(
                    "() => localStorage.getItem('aegis-rag-llm-config')"
                )
                config = json.loads(config_json)

                for use_case, expected_model in use_cases_to_change:
                    found = next((c for c in config if c["useCase"] == use_case), None)
                    assert found is not None, f"{use_case} not in config"
                    assert (
                        found["modelId"] == expected_model
                    ), f"Expected {expected_model}, got {found['modelId']}"

            finally:
                await context.close()
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_navigation_via_sidebar_link(self):
        """Test navigating to LLM Config page via sidebar link."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                # Start at home
                await page.goto("http://localhost:5179/")

                # Look for sidebar link
                sidebar_link = page.locator('[data-testid="sidebar-llm-config-link"]')

                if await sidebar_link.is_visible():
                    await sidebar_link.click()

                    # Should navigate to /admin/llm-config
                    assert (
                        "/admin/llm-config" in page.url
                    ), f"Expected navigation to /admin/llm-config, got {page.url}"

                    # Page should load
                    llm_config_page = page.locator('[data-testid="llm-config-page"]')
                    await expect(llm_config_page).to_be_visible(timeout=10000)

            finally:
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_direct_url_navigation(self):
        """Test accessing LLM Config page via direct URL."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")

                # Page should load without errors
                llm_config_page = page.locator('[data-testid="llm-config-page"]')
                await expect(llm_config_page).to_be_visible(timeout=10000)

            finally:
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_dark_mode_support(self):
        """Test that LLM Config page works in dark mode."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")

                # Enable dark mode
                await page.evaluate("() => document.documentElement.classList.add('dark')")

                # Page should still be visible
                llm_config_page = page.locator('[data-testid="llm-config-page"]')
                await expect(llm_config_page).to_be_visible()

                # Dropdowns should still work
                dropdown = page.locator('[data-testid="model-dropdown-intent_classification"]')
                await expect(dropdown).to_be_visible()
                await expect(dropdown).to_be_enabled()

            finally:
                await browser.close()


class TestVLMIntegrationE2E:
    """E2E tests for VLM (Vision Language Model) integration."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_local_vlm_default(self):
        """Test that local VLM (Ollama) is the default."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")
                await page.evaluate("() => localStorage.clear()")
                await page.reload(wait_until="domcontentloaded")

                # Check Vision VLM default
                vlm_dropdown = page.locator('[data-testid="model-dropdown-vision_vlm"]')
                selected_value = await vlm_dropdown.input_value()

                assert "ollama" in selected_value, f"Expected Ollama default, got {selected_value}"

            finally:
                await context.close()
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_vlm_model_change_persistence(self):
        """Test that VLM model selection persists."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")
                await page.evaluate("() => localStorage.clear()")

                # Select a specific VLM model
                vlm_dropdown = page.locator('[data-testid="model-dropdown-vision_vlm"]')

                # Get available models
                options = await vlm_dropdown.locator("option").all_text_contents()

                if len(options) > 1:
                    # Select second option
                    await vlm_dropdown.select_option(index=1)

                    # Save
                    save_button = page.locator('[data-testid="save-config-button"]')
                    await save_button.click()
                    await expect(page.get_by_text("Saved!")).to_be_visible(timeout=5000)

                    # Get the selected value after save
                    saved_value = await vlm_dropdown.input_value()

                    # Reload
                    await page.reload(wait_until="domcontentloaded")

                    # Verify persistence
                    reloaded_dropdown = page.locator('[data-testid="model-dropdown-vision_vlm"]')
                    reloaded_value = await reloaded_dropdown.input_value()

                    assert (
                        reloaded_value == saved_value
                    ), f"VLM selection not persisted: {saved_value} != {reloaded_value}"

            finally:
                await context.close()
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_vlm_independent_from_text_models(self):
        """Test that VLM selection is independent from other models."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")
                await page.evaluate("() => localStorage.clear()")

                # Select different models for text and VLM
                text_model = "ollama/llama3.2:8b"
                vlm_model = "ollama/qwen3-vl:32b"

                # Change text model
                text_dropdown = page.locator('[data-testid="model-dropdown-entity_extraction"]')
                await text_dropdown.select_option(value=text_model)

                # Change VLM model
                vlm_dropdown = page.locator('[data-testid="model-dropdown-vision_vlm"]')
                await vlm_dropdown.select_option(value=vlm_model)

                # Save
                save_button = page.locator('[data-testid="save-config-button"]')
                await save_button.click()
                await expect(page.get_by_text("Saved!")).to_be_visible(timeout=5000)

                # Verify both are saved
                config_json = await page.evaluate(
                    "() => localStorage.getItem('aegis-rag-llm-config')"
                )
                config = json.loads(config_json)

                text_config = next((c for c in config if c["useCase"] == "entity_extraction"), None)
                vlm_config = next((c for c in config if c["useCase"] == "vision_vlm"), None)

                assert text_config["modelId"] == text_model
                assert vlm_config["modelId"] == vlm_model

            finally:
                await context.close()
                await browser.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.admin
    async def test_vlm_provider_badges(self):
        """Test that VLM provider badges display correctly."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto("http://localhost:5179/admin/llm-config")

                # Find the VLM use case selector
                vlm_selector = page.locator('[data-testid="usecase-selector-vision_vlm"]')

                # Look for provider badge
                vlm_selector.locator("span").filter(has_text="Local") or vlm_selector.locator(
                    "span"
                ).filter(has_text="Cloud")

                # Badge should exist
                badge_visible = await vlm_selector.locator("span").count() > 0
                assert badge_visible, "Provider badge should be visible for VLM"

            finally:
                await browser.close()
