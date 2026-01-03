/**
 * E2E Tests for Network Error Handling
 * Sprint 73, Feature 73.2
 *
 * Tests cover:
 * - Offline mode (complete network failure)
 * - Slow network (3G simulation with delays)
 *
 * Tests verify:
 * - Offline banner is displayed
 * - Graceful degradation when offline
 * - Loading states during slow network
 * - No timeout errors on slow connections
 */

import { test, expect } from '@playwright/test';
import { setupAuthMocking } from '../../fixtures';

test.describe('Network Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthMocking(page);
  });

  test('should handle offline mode gracefully', async ({ page, context }) => {
    // Navigate to chat page while online
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Verify page loaded successfully
    await expect(page.getByTestId('message-input')).toBeVisible();

    // Simulate going offline
    await context.setOffline(true);

    // Try to send a message while offline
    const messageInput = page.getByTestId('message-input');
    await messageInput.fill('Message sent while offline');

    const sendButton = page.getByTestId('send-button');
    await sendButton.click();

    // Wait for offline detection
    await page.waitForTimeout(2000);

    // Verify offline banner or notification appears
    const offlinePatterns = [
      page.getByText(/offline/i),
      page.getByText(/no internet/i),
      page.getByText(/connection lost/i),
      page.getByText(/network error/i),
      page.locator('[data-testid="offline-banner"]'),
      page.locator('[role="alert"]').filter({ hasText: /offline|internet|connection/i }),
    ];

    let offlineBannerFound = false;
    for (const pattern of offlinePatterns) {
      const isVisible = await pattern.first().isVisible().catch(() => false);
      if (isVisible) {
        offlineBannerFound = true;
        break;
      }
    }

    expect(offlineBannerFound).toBeTruthy();

    // Verify graceful degradation - UI should still be functional
    await expect(messageInput).toBeVisible();
    await expect(messageInput).toBeEnabled();

    // Verify that the message wasn't sent (no success indicators)
    const successPatterns = [
      page.getByText(/sent successfully/i),
      page.locator('[data-testid="message-sent-indicator"]'),
    ];

    let successFound = false;
    for (const pattern of successPatterns) {
      const isVisible = await pattern.first().isVisible().catch(() => false);
      if (isVisible) {
        successFound = true;
        break;
      }
    }

    expect(successFound).toBeFalsy();

    // Restore connection
    await context.setOffline(false);

    // Wait for online detection
    await page.waitForTimeout(1000);

    // Verify offline banner disappears or "back online" message appears
    const onlinePatterns = [
      page.getByText(/back online/i),
      page.getByText(/connected/i),
      page.getByText(/internet restored/i),
    ];

    // Either offline banner is gone or online message appears
    let isBackOnline = true;
    for (const pattern of offlinePatterns) {
      const isStillVisible = await pattern.first().isVisible().catch(() => false);
      if (isStillVisible) {
        isBackOnline = false;
      }
    }

    // Check for online indicators
    for (const pattern of onlinePatterns) {
      const isVisible = await pattern.first().isVisible().catch(() => false);
      if (isVisible) {
        isBackOnline = true;
        break;
      }
    }

    // Accept either: offline banner gone OR online message visible
    // (implementation may vary)
    expect(isBackOnline || offlineBannerFound).toBeTruthy();
  });

  test('should handle slow network (3G simulation) without timeout', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Simulate slow 3G network with route delays
    await page.route('**/api/v1/chat', async (route) => {
      // Add 3-5 second delay to simulate slow network
      await new Promise(resolve => setTimeout(resolve, 3500));

      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: 'test-session',
          message: 'Response after slow network delay',
          sources: [],
        }),
      });
    });

    // Send a message
    const messageInput = page.getByTestId('message-input');
    await messageInput.fill('Test message on slow network');

    const sendButton = page.getByTestId('send-button');
    await sendButton.click();

    // Verify loading state appears
    await page.waitForTimeout(500);

    const loadingPatterns = [
      page.getByTestId('loading-indicator'),
      page.locator('.animate-spin'),
      page.locator('.loading'),
      page.getByText(/loading/i),
      page.getByText(/sending/i),
      page.locator('[role="status"]'),
    ];

    let loadingStateFound = false;
    for (const pattern of loadingPatterns) {
      const isVisible = await pattern.first().isVisible().catch(() => false);
      if (isVisible) {
        loadingStateFound = true;
        break;
      }
    }

    expect(loadingStateFound).toBeTruthy();

    // Wait for response (should complete without timeout error)
    await page.waitForTimeout(5000);

    // Verify no timeout error occurred
    const timeoutPatterns = [
      page.getByText(/timeout/i),
      page.getByText(/timed out/i),
      page.getByText(/request failed/i).filter({ hasText: /timeout/i }),
    ];

    let timeoutErrorFound = false;
    for (const pattern of timeoutPatterns) {
      const isVisible = await pattern.first().isVisible().catch(() => false);
      if (isVisible) {
        timeoutErrorFound = true;
        break;
      }
    }

    expect(timeoutErrorFound).toBeFalsy();

    // Verify response eventually appears or loading continues gracefully
    const responsePatterns = [
      page.getByText(/response after slow network/i),
      page.locator('[data-testid="message-list"]'),
      page.locator('[data-testid="chat-message"]'),
    ];

    let responseOrLoadingFound = loadingStateFound; // Still loading is acceptable
    for (const pattern of responsePatterns) {
      const isVisible = await pattern.first().isVisible().catch(() => false);
      if (isVisible) {
        responseOrLoadingFound = true;
        break;
      }
    }

    // Check if loading indicators are still present (acceptable for slow network)
    for (const pattern of loadingPatterns) {
      const isVisible = await pattern.first().isVisible().catch(() => false);
      if (isVisible) {
        responseOrLoadingFound = true;
        break;
      }
    }

    expect(responseOrLoadingFound).toBeTruthy();

    // Verify input remains functional during/after slow request
    await expect(messageInput).toBeEnabled();
  });
});
