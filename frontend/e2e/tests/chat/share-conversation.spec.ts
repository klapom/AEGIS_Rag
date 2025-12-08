/**
 * E2E Tests for Share Conversation Links
 * Sprint 38 Feature 38.3
 *
 * Tests cover:
 * - Share button visibility in session sidebar
 * - Share modal opening and configuration
 * - Share link generation
 * - Copy to clipboard functionality
 * - Shared conversation page (public access)
 * - Expired/invalid link handling
 */

import { test, expect, type Page } from '@playwright/test';

const API_BASE_URL = process.env.VITE_API_BASE_URL || 'http://localhost:8000';

test.describe('Share Conversation Links', () => {
  let sessionId: string;
  let shareToken: string;

  test.beforeEach(async ({ page }) => {
    // Navigate to home page
    await page.goto('/');

    // Create a test conversation
    const messageInput = page.locator('input[placeholder*="Ask"]');
    await messageInput.fill('What is AEGIS RAG?');
    await messageInput.press('Enter');

    // Wait for response to complete
    await page.waitForSelector('[data-testid="streaming-answer"]', { timeout: 30000 });
    await page.waitForTimeout(2000); // Allow time for message to be saved

    // Get session ID from page or API
    // For this test, we'll assume the session sidebar shows the session
    await page.click('[data-testid="sidebar-toggle"]');
    await page.waitForSelector('[data-testid="session-item"]');
  });

  test('should show share button on session hover', async ({ page }) => {
    // Open sidebar
    await page.click('[data-testid="sidebar-toggle"]');

    // Hover over session item
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();

    // Verify share button appears
    const shareButton = sessionItem.locator('[data-testid="share-session"]');
    await expect(shareButton).toBeVisible();

    // Verify share icon is present
    await expect(shareButton).toHaveAttribute('title', 'Share conversation');
  });

  test('should open share modal when share button clicked', async ({ page }) => {
    // Open sidebar
    await page.click('[data-testid="sidebar-toggle"]');

    // Hover and click share button
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();
    await page.click('[data-testid="share-session"]');

    // Verify modal is visible
    await expect(page.getByRole('heading', { name: 'Share Conversation' })).toBeVisible();

    // Verify expiry options are present
    await expect(page.getByText('1 hour')).toBeVisible();
    await expect(page.getByText('24 hours')).toBeVisible();
    await expect(page.getByText('3 days')).toBeVisible();
    await expect(page.getByText('7 days')).toBeVisible();

    // Verify generate button is present
    await expect(page.getByRole('button', { name: /Generate Share Link/i })).toBeVisible();
  });

  test('should generate share link with default expiry', async ({ page }) => {
    // Open share modal
    await page.click('[data-testid="sidebar-toggle"]');
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();
    await page.click('[data-testid="share-session"]');

    // Click generate button
    await page.click('button:has-text("Generate Share Link")');

    // Wait for link to be generated
    await page.waitForSelector('input[readonly][value*="/share/"]', { timeout: 10000 });

    // Verify share URL is displayed
    const shareUrlInput = page.locator('input[readonly]');
    const shareUrl = await shareUrlInput.inputValue();
    expect(shareUrl).toContain('/share/');
    expect(shareUrl.split('/share/')[1].length).toBeGreaterThan(10); // Token should be long

    // Extract share token for later tests
    shareToken = shareUrl.split('/share/')[1];

    // Verify expiry information is shown
    await expect(page.getByText(/Link expires on/i)).toBeVisible();

    // Verify copy button is present
    await expect(page.getByRole('button', { name: /Copy/i })).toBeVisible();
  });

  test('should generate share link with custom expiry', async ({ page }) => {
    // Open share modal
    await page.click('[data-testid="sidebar-toggle"]');
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();
    await page.click('[data-testid="share-session"]');

    // Select 7 days expiry
    await page.click('button:has-text("7 days")');

    // Verify 7 days is selected (has blue border)
    const sevenDaysButton = page.locator('button:has-text("7 days")');
    await expect(sevenDaysButton).toHaveClass(/border-blue-500/);

    // Generate link
    await page.click('button:has-text("Generate Share Link")');

    // Wait for link
    await page.waitForSelector('input[readonly][value*="/share/"]', { timeout: 10000 });

    // Verify link is generated
    const shareUrlInput = page.locator('input[readonly]');
    const shareUrl = await shareUrlInput.inputValue();
    expect(shareUrl).toContain('/share/');
  });

  test('should copy share link to clipboard', async ({ page, context }) => {
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    // Generate share link
    await page.click('[data-testid="sidebar-toggle"]');
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();
    await page.click('[data-testid="share-session"]');
    await page.click('button:has-text("Generate Share Link")');
    await page.waitForSelector('input[readonly][value*="/share/"]', { timeout: 10000 });

    // Get share URL before copying
    const shareUrlInput = page.locator('input[readonly]');
    const expectedUrl = await shareUrlInput.inputValue();

    // Click copy button
    await page.click('button:has-text("Copy")');

    // Verify "Copied!" feedback
    await expect(page.getByText('Copied!')).toBeVisible();

    // Verify clipboard content
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toBe(expectedUrl);
  });

  test('should close share modal', async ({ page }) => {
    // Open share modal
    await page.click('[data-testid="sidebar-toggle"]');
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();
    await page.click('[data-testid="share-session"]');

    // Verify modal is open
    await expect(page.getByRole('heading', { name: 'Share Conversation' })).toBeVisible();

    // Close modal
    await page.click('button[aria-label="Close"]');

    // Verify modal is closed
    await expect(page.getByRole('heading', { name: 'Share Conversation' })).not.toBeVisible();
  });

  test('should display shared conversation on public page', async ({ page }) => {
    // First, generate a share link
    await page.click('[data-testid="sidebar-toggle"]');
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();
    await page.click('[data-testid="share-session"]');
    await page.click('button:has-text("Generate Share Link")');
    await page.waitForSelector('input[readonly][value*="/share/"]', { timeout: 10000 });

    const shareUrlInput = page.locator('input[readonly]');
    const shareUrl = await shareUrlInput.inputValue();
    const token = shareUrl.split('/share/')[1];

    // Close modal
    await page.click('button:has-text("Done")');

    // Navigate to shared conversation page
    await page.goto(`/share/${token}`);

    // Verify read-only banner is shown
    await expect(page.getByText(/This is a shared conversation \(read-only\)/i)).toBeVisible();

    // Verify conversation title or "Shared Conversation" is shown
    await expect(page.locator('h1')).toContainText(/Shared Conversation|Discussion/i);

    // Verify messages are displayed
    await expect(page.locator('[data-testid="chat-message"]').first()).toBeVisible();

    // Verify user message is present
    await expect(page.getByText('What is AEGIS RAG?')).toBeVisible();

    // Verify expiry information is shown
    await expect(page.getByText(/Shared on/i)).toBeVisible();
    await expect(page.getByText(/Expires on/i)).toBeVisible();

    // Verify "Start Your Own Conversation" link is present
    await expect(page.getByRole('link', { name: /Start Your Own Conversation/i })).toBeVisible();
  });

  test('should show error for invalid share token', async ({ page }) => {
    // Navigate to page with invalid token
    await page.goto('/share/invalid-token-12345');

    // Wait for error message
    await page.waitForSelector('text=Link Not Found', { timeout: 10000 });

    // Verify error message
    await expect(page.getByText('Link Not Found')).toBeVisible();
    await expect(page.getByText(/This shared conversation could not be found/i)).toBeVisible();

    // Verify "Go to Home" link
    await expect(page.getByRole('link', { name: /Go to Home/i })).toBeVisible();
  });

  test('should navigate home from shared conversation page', async ({ page }) => {
    // Generate and visit shared conversation
    await page.click('[data-testid="sidebar-toggle"]');
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();
    await page.click('[data-testid="share-session"]');
    await page.click('button:has-text("Generate Share Link")');
    await page.waitForSelector('input[readonly][value*="/share/"]', { timeout: 10000 });

    const shareUrlInput = page.locator('input[readonly]');
    const shareUrl = await shareUrlInput.inputValue();
    const token = shareUrl.split('/share/')[1];

    await page.click('button:has-text("Done")');
    await page.goto(`/share/${token}`);

    // Click "Start Your Own Conversation" link
    await page.click('text=Start Your Own Conversation');

    // Verify navigation to home page
    await page.waitForURL('/');
    await expect(page.locator('input[placeholder*="Ask"]')).toBeVisible();
  });

  test('should handle share modal for different expiry durations', async ({ page }) => {
    await page.click('[data-testid="sidebar-toggle"]');
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();
    await page.click('[data-testid="share-session"]');

    const expiryOptions = ['1 hour', '24 hours', '3 days', '7 days'];

    for (const option of expiryOptions) {
      // Click expiry option
      await page.click(`button:has-text("${option}")`);

      // Verify it's selected
      const button = page.locator(`button:has-text("${option}")`);
      await expect(button).toHaveClass(/border-blue-500/);
    }
  });

  test('should show loading state while generating link', async ({ page }) => {
    await page.click('[data-testid="sidebar-toggle"]');
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    await sessionItem.hover();
    await page.click('[data-testid="share-session"]');

    // Click generate button
    const generateButton = page.getByRole('button', { name: /Generate Share Link/i });
    await generateButton.click();

    // Verify loading state appears briefly
    await expect(page.getByText('Generating...')).toBeVisible({ timeout: 5000 });

    // Wait for completion
    await page.waitForSelector('input[readonly][value*="/share/"]', { timeout: 10000 });
  });
});
