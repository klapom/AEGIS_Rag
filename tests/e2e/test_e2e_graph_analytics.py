"""E2E tests for Graph Analytics Page.

Sprint 52 Feature 52.2.1: Graph Analytics Dashboard

Tests cover:
- Page loading and navigation
- Analytics dashboard display
- Summary cards rendering
- Distribution charts
- Community size visualization
- Graph health indicators
- Refresh functionality
- Tab switching (Analytics/Visualization)
"""

import pytest
from playwright.async_api import Page, expect


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_graph_analytics_page_loads(page: Page, base_url: str):
    """Test that the Graph Analytics page loads successfully."""
    await page.goto(f"{base_url}/admin/graph")

    # Wait for page to load
    await page.wait_for_load_state("networkidle")

    # Check page title is present
    title = page.locator("h1")
    await expect(title).to_have_text("Knowledge Graph Analytics")

    # Check that tabs are present
    analytics_tab = page.locator('button[role="tab"]:has-text("Analytics")')
    visualization_tab = page.locator('button[role="tab"]:has-text("Visualization")')

    await expect(analytics_tab).to_be_visible()
    await expect(visualization_tab).to_be_visible()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analytics_dashboard_displays_summary_cards(page: Page, base_url: str):
    """Test that summary cards are displayed on the analytics dashboard."""
    await page.goto(f"{base_url}/admin/graph")

    # Wait for analytics dashboard to load
    await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=10000)

    # Check summary cards are present
    entities_card = page.locator('[data-testid="summary-entities"]')
    relationships_card = page.locator('[data-testid="summary-relationships"]')
    communities_card = page.locator('[data-testid="summary-communities"]')
    orphans_card = page.locator('[data-testid="summary-orphans"]')

    await expect(entities_card).to_be_visible()
    await expect(relationships_card).to_be_visible()
    await expect(communities_card).to_be_visible()
    await expect(orphans_card).to_be_visible()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analytics_dashboard_displays_charts(page: Page, base_url: str):
    """Test that distribution charts are displayed on the analytics dashboard."""
    await page.goto(f"{base_url}/admin/graph")

    # Wait for analytics dashboard to load
    await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=10000)

    # Check entity type chart is present
    entity_type_chart = page.locator('[data-testid="entity-type-chart"]')
    await expect(entity_type_chart).to_be_visible()

    # Check relationship type chart is present
    relationship_type_chart = page.locator('[data-testid="relationship-type-chart"]')
    await expect(relationship_type_chart).to_be_visible()

    # Check community size chart is present
    community_size_chart = page.locator('[data-testid="community-size-chart"]')
    await expect(community_size_chart).to_be_visible()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_graph_health_banner_displays(page: Page, base_url: str):
    """Test that the graph health banner is displayed."""
    await page.goto(f"{base_url}/admin/graph")

    # Wait for analytics dashboard to load
    await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=10000)

    # Check health banner is present
    health_banner = page.locator('[data-testid="graph-health-banner"]')
    await expect(health_banner).to_be_visible()

    # Health banner should contain health status text
    health_text = health_banner.locator("text=Graph Health")
    await expect(health_text).to_be_visible()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_refresh_button_works(page: Page, base_url: str):
    """Test that the refresh button triggers data reload."""
    await page.goto(f"{base_url}/admin/graph")

    # Wait for analytics dashboard to load
    await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=10000)

    # Find refresh button
    refresh_button = page.locator('[data-testid="refresh-button"]')
    await expect(refresh_button).to_be_visible()

    # Click refresh
    await refresh_button.click()

    # The button should show a spinning icon while loading
    # After clicking, the dashboard should remain visible
    await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=5000)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tab_switching(page: Page, base_url: str):
    """Test that switching between Analytics and Visualization tabs works."""
    await page.goto(f"{base_url}/admin/graph")

    # Wait for page to load (default is Analytics tab)
    await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=10000)

    # Click Visualization tab
    visualization_tab = page.locator('button[role="tab"]:has-text("Visualization")')
    await visualization_tab.click()

    # Wait for graph viewer to appear (sidebar should be visible)
    await page.wait_for_selector('[data-testid="graph-filters-section"]', timeout=10000)

    # Click back to Analytics tab
    analytics_tab = page.locator('button[role="tab"]:has-text("Analytics")')
    await analytics_tab.click()

    # Analytics dashboard should reappear
    await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=10000)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_summary_status_card_displays(page: Page, base_url: str):
    """Test that community summary status card is displayed."""
    await page.goto(f"{base_url}/admin/graph")

    # Wait for analytics dashboard to load
    await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=10000)

    # Check summary status card is present
    summary_status = page.locator('[data-testid="summary-status"]')
    await expect(summary_status).to_be_visible()

    # Should show Generated, Pending, and Completion
    generated_text = summary_status.locator("text=Generated")
    await expect(generated_text).to_be_visible()

    pending_text = summary_status.locator("text=Pending")
    await expect(pending_text).to_be_visible()

    completion_text = summary_status.locator("text=Completion")
    await expect(completion_text).to_be_visible()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_additional_metrics_display(page: Page, base_url: str):
    """Test that additional metric cards are displayed."""
    await page.goto(f"{base_url}/admin/graph")

    # Wait for analytics dashboard to load
    await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=10000)

    # Check metric cards are present
    avg_degree = page.locator('[data-testid="metric-avg-degree"]')
    density = page.locator('[data-testid="metric-density"]')
    timestamp = page.locator('[data-testid="metric-timestamp"]')

    await expect(avg_degree).to_be_visible()
    await expect(density).to_be_visible()
    await expect(timestamp).to_be_visible()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_back_to_admin_navigation(page: Page, base_url: str):
    """Test that the 'Back to Admin' link navigates correctly."""
    await page.goto(f"{base_url}/admin/graph")

    # Wait for page to load
    await page.wait_for_load_state("networkidle")

    # Find and click the back link
    back_link = page.locator("a:has-text('Back to Admin')")
    await expect(back_link).to_be_visible()

    await back_link.click()

    # Should navigate to admin dashboard
    await page.wait_for_url(f"{base_url}/admin")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_visualization_tab_shows_graph_filters(page: Page, base_url: str):
    """Test that the visualization tab shows graph filters in sidebar."""
    await page.goto(f"{base_url}/admin/graph")

    # Click Visualization tab
    visualization_tab = page.locator('button[role="tab"]:has-text("Visualization")')
    await visualization_tab.click()

    # Wait for filters section to appear
    filters_section = page.locator('[data-testid="graph-filters-section"]')
    await expect(filters_section).to_be_visible(timeout=10000)

    # Check that entity type stats are displayed
    entity_stats = page.locator('[data-testid="entity-type-stats"]')
    await expect(entity_stats).to_be_visible()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_graph_stats_endpoint(page: Page, api_base_url: str):
    """Test that the /api/v1/admin/graph/stats endpoint returns data."""
    # Make direct API call
    response = await page.request.get(f"{api_base_url}/api/v1/admin/graph/stats")

    assert response.ok, f"API returned status {response.status}"

    data = await response.json()

    # Verify response structure
    assert "total_entities" in data
    assert "total_relationships" in data
    assert "entity_types" in data
    assert "relationship_types" in data
    assert "community_count" in data
    assert "community_sizes" in data
    assert "orphan_nodes" in data
    assert "avg_degree" in data
    assert "summary_status" in data
    assert "graph_health" in data
    assert "timestamp" in data

    # Verify data types
    assert isinstance(data["total_entities"], int)
    assert isinstance(data["total_relationships"], int)
    assert isinstance(data["entity_types"], dict)
    assert isinstance(data["relationship_types"], dict)
    assert isinstance(data["community_count"], int)
    assert isinstance(data["community_sizes"], list)
    assert isinstance(data["orphan_nodes"], int)
    assert isinstance(data["avg_degree"], (int, float))
    assert isinstance(data["summary_status"], dict)
    assert data["graph_health"] in ["healthy", "warning", "critical", "unknown"]
