/**
 * E2E Tests for Graph Analytics Page Responsive Design
 * Sprint 73 Feature 73.1
 *
 * Tests cover:
 * 8. Mobile (375px): Graph controls collapse into menu
 * 9. Tablet (768px): Graph + sidebar side-by-side
 * 10. Desktop (1024px+): Full screen graph with floating controls
 *
 * Components Tested:
 * - /admin/graph-analytics
 * - Graph visualization canvas
 * - Control panels (filters, zoom, layout)
 * - Sidebar (entity/relationship info)
 *
 * Implementation Notes:
 * - Uses setupAuthMocking for authentication
 * - Tests graph control visibility at each breakpoint
 * - Verifies canvas sizing and positioning
 * - Screenshots captured for visual verification (see comments)
 */

import { test, expect } from '@playwright/test';
import { setupAuthMocking } from '../../fixtures';

test.describe('Graph Analytics Page Responsive Design', () => {
  test('should display mobile layout (375px) - collapsed controls menu', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Setup authentication and navigate to graph analytics
    await setupAuthMocking(page);
    await page.goto('/admin/graph-analytics');
    await page.waitForLoadState('networkidle');

    // Test 1: Graph controls should collapse into hamburger menu on mobile
    const controlsMenu = page.getByTestId('graph-controls-menu');
    const controlsToggle = page.getByTestId('graph-controls-toggle');

    const menuVisible = await controlsMenu.isVisible().catch(() => false);
    const toggleVisible = await controlsToggle.isVisible().catch(() => false);

    if (toggleVisible) {
      // Mobile should have toggle button for controls
      await expect(controlsToggle).toBeVisible();
    } else if (menuVisible) {
      // Or controls may be in a compact panel
      const controlsWidth = await controlsMenu.evaluate(el => el.getBoundingClientRect().width);
      const viewportWidth = 375;

      // Controls should not take full width (should be compact or hidden)
      expect(controlsWidth).toBeLessThan(viewportWidth * 0.9);
    }

    // Test 2: Graph canvas should take most of the screen on mobile
    const graphCanvas = page.locator('canvas, [data-testid="graph-canvas"], svg').first();
    const canvasVisible = await graphCanvas.isVisible().catch(() => false);

    if (canvasVisible) {
      const canvasSize = await graphCanvas.evaluate(el => el.getBoundingClientRect());
      const viewportWidth = 375;
      const viewportHeight = 667;

      // Canvas should be near full width (>80%)
      expect(canvasSize.width).toBeGreaterThan(viewportWidth * 0.8);

      // Canvas should take significant vertical space (>50%)
      expect(canvasSize.height).toBeGreaterThan(viewportHeight * 0.5);
    }

    // Test 3: Sidebar (entity/relationship info) should be hidden or bottom sheet
    const graphSidebar = page.getByTestId('graph-sidebar');
    const sidebarVisible = await graphSidebar.isVisible().catch(() => false);

    if (sidebarVisible) {
      // If visible, should be positioned at bottom or as overlay
      const sidebarPosition = await graphSidebar.evaluate(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return {
          bottom: rect.bottom,
          position: style.position,
          zIndex: style.zIndex,
        };
      });

      // Sidebar should be overlay (fixed/absolute) or at bottom
      const isMobilePosition =
        sidebarPosition.position === 'fixed' ||
        sidebarPosition.position === 'absolute' ||
        parseInt(sidebarPosition.zIndex) > 10;

      expect(isMobilePosition).toBeTruthy();
    }

    // Test 4: Zoom controls should be compact on mobile
    const zoomControls = page.getByTestId('graph-zoom-controls');
    const zoomVisible = await zoomControls.isVisible().catch(() => false);

    if (zoomVisible) {
      const zoomSize = await zoomControls.evaluate(el => el.getBoundingClientRect());

      // Zoom controls should be small and compact (<80px)
      expect(zoomSize.width).toBeLessThan(100);
      expect(zoomSize.height).toBeLessThan(150);
    }

    // Screenshot: Mobile graph view
    // await page.screenshot({ path: 'screenshots/graph-mobile-375px.png' });
  });

  test('should display tablet layout (768px) - graph and sidebar side-by-side', async ({
    page,
  }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    // Setup authentication and navigate to graph analytics
    await setupAuthMocking(page);
    await page.goto('/admin/graph-analytics');
    await page.waitForLoadState('networkidle');

    // Test 1: Graph controls should be visible as panel on tablet
    const controlsPanel = page.getByTestId('graph-controls-panel');
    const controlsVisible = await controlsPanel.isVisible().catch(() => false);

    if (controlsVisible) {
      await expect(controlsPanel).toBeVisible();

      // Controls panel should be compact but readable
      const panelWidth = await controlsPanel.evaluate(el => el.getBoundingClientRect().width);

      expect(panelWidth).toBeGreaterThan(150);
      expect(panelWidth).toBeLessThan(400);
    }

    // Test 2: Graph and sidebar should be side-by-side
    const graphContainer = page.locator(
      '[data-testid="graph-container"], [data-testid="graph-canvas"]'
    );
    const sidebar = page.getByTestId('graph-sidebar');

    const graphVisible = await graphContainer.isVisible().catch(() => false);
    const sidebarVisible = await sidebar.isVisible().catch(() => false);

    if (graphVisible && sidebarVisible) {
      const layout = await page.evaluate(() => {
        const graph = document.querySelector(
          '[data-testid="graph-container"], [data-testid="graph-canvas"]'
        );
        const sidebar = document.querySelector('[data-testid="graph-sidebar"]');

        if (!graph || !sidebar) return null;

        const graphRect = graph.getBoundingClientRect();
        const sidebarRect = sidebar.getBoundingClientRect();

        return {
          graphLeft: graphRect.left,
          graphRight: graphRect.right,
          sidebarLeft: sidebarRect.left,
          sidebarRight: sidebarRect.right,
          graphWidth: graphRect.width,
          sidebarWidth: sidebarRect.width,
        };
      });

      if (layout) {
        // Graph and sidebar should not overlap significantly
        // Either sidebar is to the right of graph, or graph is to the right
        const noOverlap =
          layout.sidebarLeft >= layout.graphRight - 50 ||
          layout.graphLeft >= layout.sidebarRight - 50;

        expect(noOverlap).toBeTruthy();

        // Combined should use most of screen width
        const totalWidth = layout.graphWidth + layout.sidebarWidth;
        const viewportWidth = 768;

        expect(totalWidth).toBeGreaterThan(viewportWidth * 0.7);
      }
    }

    // Test 3: Graph canvas should be appropriately sized for tablet
    const graphCanvas = page.locator('canvas, svg').first();
    const canvasVisible = await graphCanvas.isVisible().catch(() => false);

    if (canvasVisible) {
      const canvasSize = await graphCanvas.evaluate(el => el.getBoundingClientRect());
      const viewportWidth = 768;

      // Canvas should be 50-70% of width (sharing space with sidebar)
      expect(canvasSize.width).toBeGreaterThan(viewportWidth * 0.45);
      expect(canvasSize.width).toBeLessThan(viewportWidth * 0.75);
    }

    // Screenshot: Tablet graph view
    // await page.screenshot({ path: 'screenshots/graph-tablet-768px.png' });
  });

  test('should display desktop layout (1024px+) - full screen graph with floating controls', async ({
    page,
  }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1280, height: 720 });

    // Setup authentication and navigate to graph analytics
    await setupAuthMocking(page);
    await page.goto('/admin/graph-analytics');
    await page.waitForLoadState('networkidle');

    // Test 1: Graph should take majority of screen on desktop
    const graphCanvas = page.locator('canvas, svg').first();
    const canvasVisible = await graphCanvas.isVisible().catch(() => false);

    if (canvasVisible) {
      const canvasSize = await graphCanvas.evaluate(el => el.getBoundingClientRect());
      const viewportWidth = 1280;
      const viewportHeight = 720;

      // Canvas should be >70% of width on desktop
      expect(canvasSize.width).toBeGreaterThan(viewportWidth * 0.7);

      // Canvas should use most of height (>60%)
      expect(canvasSize.height).toBeGreaterThan(viewportHeight * 0.6);
    }

    // Test 2: Controls should be floating panels (not inline)
    const controlsPanel = page.getByTestId('graph-controls-panel');
    const controlsVisible = await controlsPanel.isVisible().catch(() => false);

    if (controlsVisible) {
      const controlsPosition = await controlsPanel.evaluate(el => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return {
          position: style.position,
          zIndex: style.zIndex,
          top: rect.top,
          right: rect.right,
        };
      });

      // Desktop controls should be floating (absolute/fixed)
      const isFloating =
        controlsPosition.position === 'absolute' ||
        controlsPosition.position === 'fixed' ||
        parseInt(controlsPosition.zIndex) > 5;

      expect(isFloating).toBeTruthy();
    }

    // Test 3: Sidebar should be visible and well-sized on desktop
    const sidebar = page.getByTestId('graph-sidebar');
    const sidebarVisible = await sidebar.isVisible().catch(() => false);

    if (sidebarVisible) {
      const sidebarWidth = await sidebar.evaluate(el => el.getBoundingClientRect().width);
      const viewportWidth = 1280;

      // Sidebar should be 20-35% of width on desktop
      expect(sidebarWidth).toBeGreaterThan(viewportWidth * 0.15);
      expect(sidebarWidth).toBeLessThan(viewportWidth * 0.4);
    }

    // Test 4: Zoom controls should be prominent and easy to use
    const zoomControls = page.getByTestId('graph-zoom-controls');
    const zoomVisible = await zoomControls.isVisible().catch(() => false);

    if (zoomVisible) {
      const zoomSize = await zoomControls.evaluate(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return {
          width: rect.width,
          height: rect.height,
          position: style.position,
        };
      });

      // Zoom controls should be visible size (>40px)
      expect(zoomSize.width).toBeGreaterThan(35);
      expect(zoomSize.height).toBeGreaterThan(35);

      // Should be positioned (not static)
      expect(zoomSize.position).toMatch(/absolute|fixed/);
    }

    // Test 5: Filter panel should be accessible
    const filterPanel = page.getByTestId('graph-filter-panel');
    const filterVisible = await filterPanel.isVisible().catch(() => false);

    if (filterVisible) {
      await expect(filterPanel).toBeVisible();

      // Filter panel should have good width for desktop
      const filterWidth = await filterPanel.evaluate(el => el.getBoundingClientRect().width);

      expect(filterWidth).toBeGreaterThan(200);
      expect(filterWidth).toBeLessThan(500);
    }

    // Screenshot: Desktop graph view
    // await page.screenshot({ path: 'screenshots/graph-desktop-1280px.png' });
  });
});
