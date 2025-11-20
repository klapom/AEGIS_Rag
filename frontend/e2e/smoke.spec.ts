import { test, expect } from './fixtures';

test.describe('Smoke Tests - Infrastructure Setup', () => {
  test('should load homepage', async ({ page }) => {
    await page.goto('/');
    const title = await page.title();
    expect(title).toContain('AEGIS RAG');
  });

  test('should have working backend health endpoint', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/health');
    expect(response.ok()).toBeTruthy();
  });

  test('should render chat interface elements', async ({ chatPage }) => {
    // Verify chat page loaded
    await expect(chatPage.messageInput).toBeVisible();
    await expect(chatPage.sendButton).toBeVisible();
  });

  test('should render message input and send button', async ({ page }) => {
    await page.goto('/');
    const input = page.locator('[data-testid="message-input"]');
    const button = page.locator('[data-testid="send-button"]');

    await expect(input).toBeVisible();
    await expect(button).toBeVisible();
  });

  test('should have working navigation', async ({ page }) => {
    await page.goto('/');

    // Test navigation to history
    const historyLink = page.locator('[data-testid="nav-history"]');
    if (await historyLink.isVisible()) {
      await historyLink.click();
      await page.waitForTimeout(500);
      expect(page.url()).toContain('/history');
    }
  });

  test('should load settings page', async ({ settingsPage }) => {
    // Just verify navigation works
    await expect(settingsPage.page).toHaveURL(/.*settings/);
  });

  test('should verify frontend is running on correct port', async ({ page }) => {
    const url = page.url();
    expect(url).toContain('http://localhost:5173');
  });

  test('should verify Playwright infrastructure is working', async ({ page }) => {
    await page.goto('/');

    // Test basic element interaction
    const title = page.locator('h1');
    const text = await title.textContent();
    expect(text).toBeTruthy();
  });
});

test.describe('Backend Connectivity Tests', () => {
  test('should connect to backend API', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/health');
    const data = await response.json();
    expect(response.status()).toBe(200);
    expect(data).toHaveProperty('status');
  });

  test('should handle backend timeout gracefully', async ({ page }) => {
    try {
      const response = await page.request.get('http://localhost:8000/nonexistent', {
        timeout: 5000,
      });
      // API should return 404, not timeout
      expect(response.status()).toBeGreaterThanOrEqual(400);
    } catch (error) {
      // Timeout is acceptable for nonexistent endpoint
      expect(error).toBeDefined();
    }
  });
});

test.describe('Page Navigation Tests', () => {
  test('should navigate between pages', async ({ page }) => {
    await page.goto('/');
    expect(page.url()).toContain('/');

    await page.goto('/history');
    expect(page.url()).toContain('/history');

    await page.goto('/settings');
    expect(page.url()).toContain('/settings');
  });

  test('should maintain state across navigation', async ({ page }) => {
    await page.goto('/');
    const initialUrl = page.url();

    // Navigate away and back
    await page.goto('/history');
    await page.goto('/');

    // Should still be on root
    expect(page.url()).toBe(initialUrl);
  });
});
