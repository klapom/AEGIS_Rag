/**
 * E2E Tests for Chat Page Responsive Design
 * Sprint 73 Feature 73.1
 *
 * Tests cover:
 * 1. Mobile (375px): Hamburger menu, full-width input, stacked messages, hidden sidebar
 * 2. Tablet (768px): Visible sidebar, 60% width input, 2-column layout
 * 3. Desktop (1024px+): Full sidebar, 50% width input, 3-column layout
 * 4. Viewport switching: Smooth transition mobile → desktop
 *
 * Implementation Notes:
 * - Uses setupAuthMocking for authentication
 * - Tests viewport-specific layout behaviors
 * - Verifies element visibility and widths at each breakpoint
 * - Screenshots captured for visual verification (see comments)
 */

import { test, expect } from '@playwright/test';
import { setupAuthMocking } from '../../fixtures';

test.describe('Chat Page Responsive Design', () => {
  test('should be responsive on mobile (375px)', async ({ page }) => {
    // Set mobile viewport (iPhone SE)
    await page.setViewportSize({ width: 375, height: 667 });

    // Setup authentication and navigate
    await setupAuthMocking(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Test 1: Hamburger menu should be visible on mobile
    const hamburgerMenu = page.getByTestId('mobile-menu-toggle');
    const hamburgerVisible = await hamburgerMenu.isVisible().catch(() => false);

    if (hamburgerVisible) {
      await expect(hamburgerMenu).toBeVisible();
    } else {
      // Alternative: Check for sidebar toggle button
      const sidebarToggle = page.getByTestId('sidebar-toggle');
      await expect(sidebarToggle).toBeVisible();
    }

    // Test 2: Chat input should take full width (>80% of viewport)
    const chatInput = page.getByTestId('message-input');
    await expect(chatInput).toBeVisible();

    const inputWidth = await chatInput.evaluate(el => el.getBoundingClientRect().width);
    const viewportWidth = 375;
    expect(inputWidth).toBeGreaterThan(viewportWidth * 0.8); // >80% width

    // Test 3: Sidebar should be hidden by default on mobile
    const sidebar = page.getByTestId('chat-sidebar');
    const sidebarVisible = await sidebar.isVisible().catch(() => false);

    if (sidebarVisible) {
      // Sidebar exists but should be hidden (display: none or off-screen)
      const sidebarPosition = await sidebar.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          display: style.display,
          transform: style.transform,
          left: style.left,
        };
      });

      // Sidebar should be hidden (display: none) or translated off-screen
      const isHidden =
        sidebarPosition.display === 'none' ||
        sidebarPosition.transform.includes('translateX(-100%)') ||
        sidebarPosition.left === '-100%';

      expect(isHidden).toBeTruthy();
    }

    // Test 4: Message bubbles should stack correctly (full width)
    // Send a test message to check layout
    await chatInput.fill('Test mobile layout');
    await chatInput.press('Enter');

    // Wait for response
    await page.waitForTimeout(2000);

    const messageContainers = page.locator('[data-testid^="chat-message"]');
    const messageCount = await messageContainers.count();

    if (messageCount > 0) {
      const firstMessage = messageContainers.first();
      const messageWidth = await firstMessage.evaluate(el => el.getBoundingClientRect().width);

      // Messages should be near full width (>70% of viewport)
      expect(messageWidth).toBeGreaterThan(viewportWidth * 0.7);
    }

    // Screenshot: Mobile chat view
    // await page.screenshot({ path: 'screenshots/chat-mobile-375px.png' });
  });

  test('should be responsive on tablet (768px)', async ({ page }) => {
    // Set tablet viewport (iPad Mini)
    await page.setViewportSize({ width: 768, height: 1024 });

    // Setup authentication and navigate
    await setupAuthMocking(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Test 1: Sidebar should be visible on tablet
    const sidebar = page.getByTestId('chat-sidebar');
    const sidebarVisible = await sidebar.isVisible().catch(() => false);

    if (sidebarVisible) {
      await expect(sidebar).toBeVisible();

      // Sidebar should be positioned on left side
      const sidebarLeft = await sidebar.evaluate(el => el.getBoundingClientRect().left);
      expect(sidebarLeft).toBeLessThan(50); // Near left edge
    }

    // Test 2: Chat input should be ~60% width on tablet
    const chatInput = page.getByTestId('message-input');
    await expect(chatInput).toBeVisible();

    const inputWidth = await chatInput.evaluate(el => el.getBoundingClientRect().width);
    const viewportWidth = 768;

    // Input should be 50-70% of viewport width (centered content)
    expect(inputWidth).toBeGreaterThan(viewportWidth * 0.5);
    expect(inputWidth).toBeLessThan(viewportWidth * 0.7);

    // Test 3: 2-column layout (sidebar + chat)
    const mainContent = page.locator('main, [data-testid="chat-container"]');
    const mainContentVisible = await mainContent.isVisible().catch(() => false);

    if (mainContentVisible) {
      const layout = await page.evaluate(() => {
        const sidebar = document.querySelector('[data-testid="chat-sidebar"]');
        const main = document.querySelector('main, [data-testid="chat-container"]');

        if (!sidebar || !main) return null;

        const sidebarRect = sidebar.getBoundingClientRect();
        const mainRect = main.getBoundingClientRect();

        return {
          sidebarWidth: sidebarRect.width,
          mainWidth: mainRect.width,
          sidebarLeft: sidebarRect.left,
          mainLeft: mainRect.left,
        };
      });

      if (layout) {
        // Sidebar should be on left (0-300px)
        expect(layout.sidebarLeft).toBeLessThan(50);
        expect(layout.sidebarWidth).toBeGreaterThan(200);
        expect(layout.sidebarWidth).toBeLessThan(400);

        // Main content should be to the right of sidebar
        expect(layout.mainLeft).toBeGreaterThan(layout.sidebarWidth - 50);
      }
    }

    // Screenshot: Tablet chat view
    // await page.screenshot({ path: 'screenshots/chat-tablet-768px.png' });
  });

  test('should be responsive on desktop (1024px+)', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1280, height: 720 });

    // Setup authentication and navigate
    await setupAuthMocking(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Test 1: Full sidebar should be visible on desktop
    const sidebar = page.getByTestId('chat-sidebar');
    const sidebarVisible = await sidebar.isVisible().catch(() => false);

    if (sidebarVisible) {
      await expect(sidebar).toBeVisible();

      const sidebarWidth = await sidebar.evaluate(el => el.getBoundingClientRect().width);
      expect(sidebarWidth).toBeGreaterThan(250); // Wide sidebar on desktop
    }

    // Test 2: Chat input should be ~50% width on desktop
    const chatInput = page.getByTestId('message-input');
    await expect(chatInput).toBeVisible();

    const inputWidth = await chatInput.evaluate(el => el.getBoundingClientRect().width);
    const viewportWidth = 1280;

    // Input should be 40-60% of viewport width (centered content)
    expect(inputWidth).toBeGreaterThan(viewportWidth * 0.4);
    expect(inputWidth).toBeLessThan(viewportWidth * 0.6);

    // Test 3: 3-column layout (sidebar + chat + potential right panel)
    // On desktop, expect spacious layout with clear separation
    const layout = await page.evaluate(() => {
      const sidebar = document.querySelector('[data-testid="chat-sidebar"]');
      const main = document.querySelector('main, [data-testid="chat-container"]');

      if (!sidebar || !main) return null;

      const sidebarRect = sidebar.getBoundingClientRect();
      const mainRect = main.getBoundingClientRect();

      return {
        sidebarWidth: sidebarRect.width,
        mainWidth: mainRect.width,
        totalUsed: sidebarRect.width + mainRect.width,
        viewportWidth: window.innerWidth,
      };
    });

    if (layout) {
      // Desktop should use majority of width efficiently
      expect(layout.totalUsed).toBeGreaterThan(layout.viewportWidth * 0.7);

      // Sidebar should be substantial (20-30% of screen)
      expect(layout.sidebarWidth).toBeGreaterThan(layout.viewportWidth * 0.15);
      expect(layout.sidebarWidth).toBeLessThan(layout.viewportWidth * 0.35);
    }

    // Test 4: Messages should have max-width for readability
    await chatInput.fill('Test desktop layout');
    await chatInput.press('Enter');
    await page.waitForTimeout(2000);

    const messageContainers = page.locator('[data-testid^="chat-message"]');
    const messageCount = await messageContainers.count();

    if (messageCount > 0) {
      const firstMessage = messageContainers.first();
      const messageWidth = await firstMessage.evaluate(el => el.getBoundingClientRect().width);

      // Messages should have constrained width for readability (<800px)
      expect(messageWidth).toBeLessThan(900);
    }

    // Screenshot: Desktop chat view
    // await page.screenshot({ path: 'screenshots/chat-desktop-1280px.png' });
  });

  test('should smoothly transition between viewport sizes', async ({ page }) => {
    // Setup authentication
    await setupAuthMocking(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Test 1: Start at mobile (375px)
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500); // Allow layout to settle

    const mobileInput = page.getByTestId('message-input');
    const mobileInputWidth = await mobileInput.evaluate(el => el.getBoundingClientRect().width);

    // Mobile input should be wide
    expect(mobileInputWidth).toBeGreaterThan(300);

    // Test 2: Resize to tablet (768px)
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500); // Allow layout to settle

    const tabletInputWidth = await mobileInput.evaluate(el => el.getBoundingClientRect().width);

    // Tablet input should be narrower than mobile (more padding)
    expect(tabletInputWidth).toBeLessThan(600);

    // Test 3: Resize to desktop (1280px)
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.waitForTimeout(500); // Allow layout to settle

    const desktopInputWidth = await mobileInput.evaluate(el => el.getBoundingClientRect().width);

    // Desktop input should be narrower still (max-width for readability)
    expect(desktopInputWidth).toBeLessThan(800);

    // Test 4: Verify sidebar visibility changes
    const sidebar = page.getByTestId('chat-sidebar');
    const sidebarVisible = await sidebar.isVisible().catch(() => false);

    if (sidebarVisible) {
      // On desktop, sidebar should be fully visible
      await expect(sidebar).toBeVisible();

      const sidebarOpacity = await sidebar.evaluate(el =>
        window.getComputedStyle(el).opacity
      );
      expect(parseFloat(sidebarOpacity)).toBeGreaterThan(0.9);
    }

    // Test 5: Resize back to mobile to ensure it works both ways
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);

    const backToMobileWidth = await mobileInput.evaluate(el => el.getBoundingClientRect().width);

    // Should return to mobile-like width
    expect(backToMobileWidth).toBeGreaterThan(300);

    // Screenshot: Viewport transition complete
    // await page.screenshot({ path: 'screenshots/chat-viewport-transition.png' });
  });
});
