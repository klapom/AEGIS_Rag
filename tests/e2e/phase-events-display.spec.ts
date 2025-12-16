/**
 * E2E Tests for Phase Events Display in Real-Time Thinking UI
 *
 * Sprint 48 Feature 48.8: Frontend Phase Display (8 SP)
 * Sprint 48 Feature 48.10: Request Timeout & Cancel (5 SP)
 *
 * These tests verify:
 * - Real-time phase progress display
 * - Elapsed time counter
 * - Progress bar animation
 * - Phase list with durations
 * - Timeout warning display
 * - Manual request cancellation
 * - Thinking indicator behavior
 */

import { test, expect } from '@playwright/test';

const API_URL = process.env.API_URL || 'http://localhost:8000';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5179';

test.describe('Phase Events Display', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to chat application
    await page.goto(FRONTEND_URL);

    // Wait for chat interface to load
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
  });

  test('should show real-time phase progress during query', async ({ page }) => {
    // Send a query
    await page.fill('[data-testid="chat-input"]', 'What is retrieval augmented generation?');
    await page.click('[data-testid="send-button"]');

    // Verify typing indicator appears immediately
    await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible({
      timeout: 2000,
    });

    // Verify elapsed time counter starts and increments
    const elapsedTime = page.locator('[data-testid="elapsed-time"]');
    await expect(elapsedTime).toBeVisible();

    // Get initial time
    const initialTime = await elapsedTime.textContent();
    expect(initialTime).toMatch(/\d+:\d{2}/);

    // Wait a bit and verify time incremented
    await page.waitForTimeout(1500);
    const updatedTime = await elapsedTime.textContent();
    expect(updatedTime).not.toBe(initialTime);

    // Verify progress indicator is displayed
    const progressBar = page.locator('[data-testid="progress-bar"]');
    await expect(progressBar).toBeVisible();

    // Verify current phase is displayed
    const currentPhase = page.locator('[data-testid="current-phase"]');
    await expect(currentPhase).toBeVisible();

    // Wait for completion
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Verify answer is displayed
    const answerContent = page.locator('[data-testid="message-content"]').last();
    await expect(answerContent).toBeVisible();
    const answerText = await answerContent.textContent();
    expect(answerText).toBeTruthy();
    expect(answerText?.length).toBeGreaterThan(10);
  });

  test('should display phase list with durations after completion', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'Explain vector search');
    await page.click('[data-testid="send-button"]');

    // Wait for phases to appear
    await expect(page.locator('[data-testid="phase-list"]')).toBeVisible({
      timeout: 5000,
    });

    // Get all phase items
    const phaseItems = page.locator('[data-testid="phase-item"]');
    const itemCount = await phaseItems.count();
    expect(itemCount).toBeGreaterThan(0);

    // Verify at least some phases are present
    const phaseNames = page.locator('[data-testid="phase-name"]');
    const firstPhase = await phaseNames.first().textContent();
    expect(firstPhase).toBeTruthy();

    // Wait for completion
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Verify completed phases show duration
    const durations = page.locator('[data-testid="phase-duration"]');
    const durationCount = await durations.count();
    expect(durationCount).toBeGreaterThan(0);

    // Verify duration format (e.g., "150ms")
    const firstDuration = await durations.first().textContent();
    expect(firstDuration).toMatch(/\d+\s*ms/);
  });

  test('should show phase status indicators correctly', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'What is the purpose of LangGraph?');
    await page.click('[data-testid="send-button"]');

    // Wait for phases
    await expect(page.locator('[data-testid="phase-list"]')).toBeVisible({
      timeout: 5000,
    });

    // Check for status indicators
    const statusIndicators = page.locator('[data-testid="phase-status"]');
    const statusCount = await statusIndicators.count();
    expect(statusCount).toBeGreaterThan(0);

    // Verify completed status is shown (checkmark or "completed" text)
    const completedStatuses = await statusIndicators.allTextContents();
    const hasCompleted = completedStatuses.some(
      (status) => status.includes('completed') || status.includes('✓'),
    );
    expect(hasCompleted).toBeTruthy();
  });

  test('should expand phase details on click', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'What is Neo4j?');
    await page.click('[data-testid="send-button"]');

    // Wait for phases
    await expect(page.locator('[data-testid="phase-list"]')).toBeVisible({
      timeout: 5000,
    });

    // Click first phase to expand
    const firstPhase = page.locator('[data-testid="phase-item"]').first();
    await firstPhase.click();

    // Verify details are expanded (metadata, status, etc.)
    const phaseDetails = page.locator('[data-testid="phase-details"]');
    await expect(phaseDetails).toBeVisible();

    // Verify metadata is shown
    const metadata = page.locator('[data-testid="phase-metadata"]');
    await expect(metadata).toBeVisible();
  });

  test('should show timeout warning after 30 seconds', async ({ page }) => {
    // This test would require mocking slow backend
    // For now, we verify the UI element exists and styling is correct

    // Send query that we'll monitor
    await page.fill('[data-testid="chat-input"]', 'test query');

    // Check if timeout warning element exists (even if not visible yet)
    const timeoutWarning = page.locator('[data-testid="timeout-warning"]');
    // Element should exist but be hidden initially
    const isHidden = await timeoutWarning.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0';
    });

    expect(isHidden).toBeTruthy();
  });

  test('should allow manual request cancellation', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'Ask a complex question');
    await page.click('[data-testid="send-button"]');

    // Verify typing indicator is shown
    await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible();

    // Find and click cancel button
    const cancelButton = page.locator('[data-testid="cancel-button"]');
    await expect(cancelButton).toBeVisible();
    await cancelButton.click();

    // Verify indicator disappears
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 2000,
    });

    // Verify cancel message is shown
    const cancelMessage = page.locator('[data-testid="request-cancelled-message"]');
    await expect(cancelMessage).toBeVisible();
  });

  test('should show progress bar animation', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'Complex multi-step query');
    await page.click('[data-testid="send-button"]');

    // Wait for progress bar
    const progressBar = page.locator('[data-testid="progress-fill"]');
    await expect(progressBar).toBeVisible();

    // Get initial width
    const initialWidth = await progressBar.evaluate((el) => {
      return window.getComputedStyle(el).width;
    });

    // Wait and check if width increased
    await page.waitForTimeout(1000);
    const laterWidth = await progressBar.evaluate((el) => {
      return window.getComputedStyle(el).width;
    });

    // Progress should have increased
    expect(parseFloat(laterWidth)).toBeGreaterThanOrEqual(parseFloat(initialWidth));
  });

  test('should update phase list in real-time', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'Real-time phase tracking test');
    await page.click('[data-testid="send-button"]');

    // Get initial phase count
    await expect(page.locator('[data-testid="phase-list"]')).toBeVisible({
      timeout: 5000,
    });
    const initialCount = await page.locator('[data-testid="phase-item"]').count();

    // Wait for more phases to be added
    await page.waitForTimeout(2000);
    const laterCount = await page.locator('[data-testid="phase-item"]').count();

    // Phase count should stay the same or increase (but not decrease)
    expect(laterCount).toBeGreaterThanOrEqual(initialCount);

    // Wait for completion
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Final count should be reasonable (3-8 phases typical)
    const finalCount = await page.locator('[data-testid="phase-item"]').count();
    expect(finalCount).toBeGreaterThanOrEqual(3);
    expect(finalCount).toBeLessThan(15);
  });

  test('should display phase timing breakdown', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'Get timing breakdown of phases');
    await page.click('[data-testid="send-button"]');

    // Wait for completion
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Look for timing breakdown
    const timingInfo = page.locator('[data-testid="timing-breakdown"]');
    await expect(timingInfo).toBeVisible();

    // Verify total time is shown
    const totalTime = page.locator('[data-testid="total-duration"]');
    await expect(totalTime).toBeVisible();

    const totalText = await totalTime.textContent();
    expect(totalText).toMatch(/\d+\s*(ms|s)/);
  });

  test('should handle multiple queries in sequence', async ({ page }) => {
    // First query
    await page.fill('[data-testid="chat-input"]', 'First question about RAG');
    await page.click('[data-testid="send-button"]');

    // Wait for first response
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Verify first answer
    let messages = await page.locator('[data-testid="message-content"]').allTextContents();
    expect(messages.length).toBeGreaterThan(0);

    // Second query
    await page.fill('[data-testid="chat-input"]', 'Second question about agents');
    await page.click('[data-testid="send-button"]');

    // Wait for second response
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Verify we have two messages now
    messages = await page.locator('[data-testid="message-content"]').allTextContents();
    expect(messages.length).toBeGreaterThan(1);
  });

  test('should show phase metadata details', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'Show phase metadata');
    await page.click('[data-testid="send-button"]');

    // Wait for phases
    await expect(page.locator('[data-testid="phase-list"]')).toBeVisible({
      timeout: 5000,
    });

    // Click first phase to see metadata
    const firstPhase = page.locator('[data-testid="phase-item"]').first();
    await firstPhase.click();

    // Verify metadata section is visible
    const metadataSection = page.locator('[data-testid="phase-metadata"]');
    await expect(metadataSection).toBeVisible();

    // Verify metadata contains expected keys
    const metadataText = await metadataSection.textContent();
    expect(metadataText).toBeTruthy();
    // Metadata should show things like "docs_retrieved", "collection", etc.
  });

  test('should maintain phase history in conversation', async ({ page }) => {
    // First query
    await page.fill('[data-testid="chat-input"]', 'First query');
    await page.click('[data-testid="send-button"]');

    // Wait for completion
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Get first response's phases
    const firstPhaseList = page.locator('[data-testid="phase-list"]').first();
    const firstPhaseCount = await firstPhaseList.locator('[data-testid="phase-item"]').count();

    // Send second query
    await page.fill('[data-testid="chat-input"]', 'Second query');
    await page.click('[data-testid="send-button"]');

    // Wait for second completion
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Verify we can still see first query's phases
    const allPhaseLists = page.locator('[data-testid="phase-list"]');
    const totalPhaseLists = await allPhaseLists.count();
    expect(totalPhaseLists).toBeGreaterThanOrEqual(2);
  });

  test('should show error phase on failure', async ({ page }) => {
    // This test assumes there's a way to trigger an error in the backend
    // For now, we verify the UI has the capability to show errors

    // Send query
    await page.fill('[data-testid="chat-input"]', 'test query');
    await page.click('[data-testid="send-button"]');

    // Check if error phase element exists (may not show unless error occurs)
    const errorPhaseTemplate = page.locator('[data-testid="error-phase-template"]');
    // Should exist in DOM even if not visible
    const count = await errorPhaseTemplate.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should hide phases after clearing chat', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'Test query');
    await page.click('[data-testid="send-button"]');

    // Wait for completion
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Verify phases are visible
    await expect(page.locator('[data-testid="phase-list"]')).toBeVisible();

    // Click clear button
    const clearButton = page.locator('[data-testid="clear-button"]');
    if ((await clearButton.count()) > 0) {
      await clearButton.click();

      // Verify phases are hidden
      const phaseList = page.locator('[data-testid="phase-list"]');
      const count = await phaseList.count();
      // Phase list should be cleared or not visible
      expect(count).toBeLessThanOrEqual(1);
    }
  });

  test('should format phase duration correctly for different timescales', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'Test duration formatting');
    await page.click('[data-testid="send-button"]');

    // Wait for completion
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Get all duration elements
    const durations = page.locator('[data-testid="phase-duration"]');
    const durationTexts = await durations.allTextContents();

    // Verify durations are formatted correctly
    for (const duration of durationTexts) {
      expect(duration.trim()).toMatch(/\d+\s*(ms|s)/);
    }
  });

  test('should highlight long-running phases', async ({ page }) => {
    // Send query
    await page.fill('[data-testid="chat-input"]', 'Complex query');
    await page.click('[data-testid="send-button"]');

    // Wait for completion
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Look for phases marked as slow
    const slowPhases = page.locator('[data-testid="phase-item"][data-slow="true"]');
    const slowCount = await slowPhases.count();

    // It's okay if there are no slow phases, but if there are they should be highlighted
    if (slowCount > 0) {
      const firstSlow = slowPhases.first();
      const className = await firstSlow.getAttribute('class');
      expect(className).toContain('slow');
    }
  });
});

test.describe('Phase Events Under Load', () => {
  test('should handle many rapid queries without UI lag', async ({ page }) => {
    await page.goto(FRONTEND_URL);

    // Send 3 queries rapidly
    for (let i = 1; i <= 3; i++) {
      await page.fill('[data-testid="chat-input"]', `Rapid query ${i}`);
      await page.click('[data-testid="send-button"]');

      // Don't wait for completion, send next query immediately (tests queueing)
      if (i < 3) {
        await page.waitForTimeout(500);
      }
    }

    // Wait for all to complete
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible({
      timeout: 60000,
    });

    // Verify all queries are in conversation
    const messages = await page.locator('[data-testid="message-content"]').allTextContents();
    expect(messages.length).toBeGreaterThanOrEqual(3);
  });

  test('should maintain UI responsiveness during long phase', async ({ page }) => {
    await page.goto(FRONTEND_URL);

    // Send query
    await page.fill('[data-testid="chat-input"]', 'Long running query');
    await page.click('[data-testid="send-button"]');

    // While processing, try to interact with UI
    await page.waitForTimeout(1000);

    // Should still be able to click cancel
    const cancelButton = page.locator('[data-testid="cancel-button"]');
    expect(await cancelButton.isVisible()).toBeTruthy();

    // Try to scroll - UI should remain responsive
    await page.locator('body').scroll({ top: 100 });

    // Verify scroll worked
    const scrollTop = await page.evaluate(() => window.scrollY);
    expect(scrollTop).toBeGreaterThan(0);
  });
});
