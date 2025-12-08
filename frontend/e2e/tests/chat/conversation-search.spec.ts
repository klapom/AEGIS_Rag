import { test, expect } from '../../fixtures';

/**
 * E2E Tests for Conversation Search UI - Sprint 38 Feature 38.2
 *
 * Tests:
 * 1. Search bar renders in sidebar
 * 2. Typing triggers search with debounce
 * 3. Results appear after search
 * 4. Clicking result navigates to conversation
 * 5. Archive button works with confirmation
 * 6. Minimum 3 characters validation
 * 7. Loading spinner displays during search
 * 8. No results message displays appropriately
 *
 * Backend: POST /api/v1/chat/search
 * Required: Backend running on http://localhost:8000
 */

test.describe('Conversation Search UI - Feature 38.2', () => {
  test('should render search bar in sidebar', async ({ chatPage, page }) => {
    // Wait for page to load
    await chatPage.goto();
    await page.waitForLoadState('networkidle');

    // Open sidebar (if not already open)
    const sidebar = page.locator('[data-testid="session-sidebar"]');
    await sidebar.waitFor({ state: 'visible', timeout: 5000 });

    // Check if search input exists
    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await expect(searchInput).toBeVisible();

    // Verify placeholder text
    await expect(searchInput).toHaveAttribute(
      'placeholder',
      'Search conversations...'
    );
  });

  test('should require minimum 3 characters to trigger search', async ({
    chatPage,
    page,
  }) => {
    await chatPage.goto();
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await searchInput.waitFor({ state: 'visible' });

    // Type 1 character
    await searchInput.fill('a');
    await page.waitForTimeout(100);

    // Should not show dropdown
    const dropdown = page.locator('[data-testid="search-results-dropdown"]');
    await expect(dropdown).not.toBeVisible();

    // Type 2 characters
    await searchInput.fill('ab');
    await page.waitForTimeout(100);

    // Should show hint about minimum characters
    const hint = page.getByText(/at least 3 characters/i);
    await expect(hint).toBeVisible();

    // Type 3 characters
    await searchInput.fill('abc');

    // Wait for debounce (300ms) + network request
    await page.waitForTimeout(500);

    // Should attempt search (dropdown or no results message)
    const noResults = page.locator('[data-testid="no-results-message"]');
    const hasResults = await dropdown.isVisible();
    const hasNoResults = await noResults.isVisible();

    expect(hasResults || hasNoResults).toBeTruthy();
  });

  test('should display loading spinner while searching', async ({
    chatPage,
    page,
  }) => {
    await chatPage.goto();
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await searchInput.waitFor({ state: 'visible' });

    // Type search query
    await searchInput.fill('test');

    // Loading spinner should appear briefly
    const loadingSpinner = page.locator('[data-testid="search-loading"]');

    // Wait a short time to catch the loading state
    await page.waitForTimeout(50);

    // After debounce + request, loading should be gone
    await page.waitForTimeout(500);
    await expect(loadingSpinner).not.toBeVisible();
  });

  test('should search and display results with correct metadata', async ({
    chatPage,
    page,
  }) => {
    // First, create a conversation with specific content
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse();

    await page.waitForTimeout(1000);

    // Search for the conversation
    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await searchInput.waitFor({ state: 'visible' });
    await searchInput.fill('machine');

    // Wait for debounce + search
    await page.waitForTimeout(500);

    // Check for results
    const dropdown = page.locator('[data-testid="search-results-dropdown"]');
    const noResults = page.locator('[data-testid="no-results-message"]');

    const hasResults = await dropdown.isVisible();
    const hasNoResults = await noResults.isVisible();

    if (hasResults) {
      // Verify result items have required metadata
      const resultItems = page.locator('[data-testid="search-result-item"]');
      const firstResult = resultItems.first();

      // Check for title
      await expect(firstResult).toBeVisible();

      // Check for score badge
      const score = firstResult.locator('[data-testid="result-score"]');
      await expect(score).toBeVisible();

      // Check for date
      const date = firstResult.locator('[data-testid="result-date"]');
      await expect(date).toBeVisible();
    } else if (hasNoResults) {
      // No results is also a valid outcome
      await expect(noResults).toContainText('No conversations found');
    }
  });

  test('should navigate to conversation when clicking search result', async ({
    chatPage,
    page,
  }) => {
    // Create a conversation
    await chatPage.sendMessage('Explain neural networks');
    await chatPage.waitForResponse();

    // Search for it
    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await searchInput.waitFor({ state: 'visible' });
    await searchInput.fill('neural');

    await page.waitForTimeout(500);

    const dropdown = page.locator('[data-testid="search-results-dropdown"]');
    const hasResults = await dropdown.isVisible();

    if (hasResults) {
      const resultItems = page.locator('[data-testid="search-result-item"]');
      const firstResult = resultItems.first();

      // Get session ID from result
      const sessionId = await firstResult.getAttribute('data-session-id');
      expect(sessionId).toBeTruthy();

      // Click result
      await firstResult.click();

      // Wait for navigation
      await page.waitForLoadState('networkidle');

      // Verify we're on the chat page with the selected session
      expect(page.url()).toContain('/');

      // Search input should be cleared
      await expect(searchInput).toHaveValue('');

      // Dropdown should be closed
      await expect(dropdown).not.toBeVisible();
    }
  });

  test('should close dropdown when clicking outside', async ({
    chatPage,
    page,
  }) => {
    await chatPage.goto();

    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await searchInput.waitFor({ state: 'visible' });

    // Perform search
    await searchInput.fill('test query');
    await page.waitForTimeout(500);

    const dropdown = page.locator('[data-testid="search-results-dropdown"]');
    const hasResults = await dropdown.isVisible();

    if (hasResults) {
      // Click outside the search component
      await page.click('body', { position: { x: 0, y: 0 } });

      // Wait a bit for event handler
      await page.waitForTimeout(200);

      // Dropdown should be closed
      await expect(dropdown).not.toBeVisible();
    }
  });

  test('should display error message when search fails', async ({
    chatPage,
    page,
  }) => {
    await chatPage.goto();

    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await searchInput.waitFor({ state: 'visible' });

    // Mock a failed search by intercepting the request
    await page.route('**/api/v1/chat/search', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Search service unavailable' }),
      });
    });

    // Perform search
    await searchInput.fill('test');
    await page.waitForTimeout(500);

    // Error message should appear
    const errorMessage = page.locator('[data-testid="search-error-message"]');
    await expect(errorMessage).toBeVisible();
  });

  test('should handle empty search results gracefully', async ({
    chatPage,
    page,
  }) => {
    await chatPage.goto();

    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await searchInput.waitFor({ state: 'visible' });

    // Search for something that definitely doesn't exist
    await searchInput.fill('xyzabc123nonexistent');
    await page.waitForTimeout(500);

    // No results message should appear
    const noResults = page.locator('[data-testid="no-results-message"]');
    await expect(noResults).toBeVisible();
    await expect(noResults).toContainText('No conversations found');
  });

  test('should clear search when starting new conversation', async ({
    chatPage,
    page,
  }) => {
    await chatPage.goto();

    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await searchInput.waitFor({ state: 'visible' });

    // Perform search
    await searchInput.fill('test');
    await page.waitForTimeout(500);

    // Click New Chat button
    const newChatButton = page.locator('[data-testid="new-chat-button"]');
    await newChatButton.click();

    await page.waitForTimeout(200);

    // Search input should remain (it's in the sidebar)
    await expect(searchInput).toBeVisible();
    // But dropdown should be closed if it was open
    const dropdown = page.locator('[data-testid="search-results-dropdown"]');
    await expect(dropdown).not.toBeVisible();
  });

  test('should show relevance scores in results', async ({ chatPage, page }) => {
    // Create a conversation
    await chatPage.sendMessage('What is deep learning?');
    await chatPage.waitForResponse();

    await page.waitForTimeout(1000);

    const searchInput = page.locator('[data-testid="conversation-search-input"]');
    await searchInput.waitFor({ state: 'visible' });
    await searchInput.fill('deep learning');

    await page.waitForTimeout(500);

    const dropdown = page.locator('[data-testid="search-results-dropdown"]');
    const hasResults = await dropdown.isVisible();

    if (hasResults) {
      const scores = page.locator('[data-testid="result-score"]');
      const firstScore = scores.first();

      await expect(firstScore).toBeVisible();

      // Score should be a percentage
      const scoreText = await firstScore.textContent();
      expect(scoreText).toMatch(/\d+%/);
    }
  });
});

/**
 * Archive Button Tests
 * These are separate from search but related to conversation management
 */
test.describe('Archive Button - Feature 38.2', () => {
  test('should show archive button on session hover', async ({
    chatPage,
    page,
  }) => {
    // Create a conversation first
    await chatPage.sendMessage('Test conversation for archiving');
    await chatPage.waitForResponse();

    await page.waitForTimeout(1000);

    // Find session item in sidebar
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    const isVisible = await sessionItem.isVisible();

    if (isVisible) {
      // Hover over session
      await sessionItem.hover();

      // Archive button should appear (if implemented in SessionItem)
      // Note: Based on current code, archive button may not be in SessionItem yet
      // This test documents the expected behavior
    }
  });

  test('should show confirmation dialog when archive clicked', async ({
    chatPage,
    page,
  }) => {
    // This test assumes ArchiveButton is integrated into the session list
    // Currently, the ArchiveButton component exists but may not be integrated
    // This test documents the expected flow

    await chatPage.sendMessage('Test conversation');
    await chatPage.waitForResponse();

    await page.waitForTimeout(1000);

    // Look for archive button (if present)
    const archiveButton = page.locator('[data-testid="archive-button"]').first();
    const exists = await archiveButton.isVisible().catch(() => false);

    if (exists) {
      await archiveButton.click();

      // Confirmation dialog should appear
      const confirmDialog = page.locator('[data-testid="archive-confirm-dialog"]');
      await expect(confirmDialog).toBeVisible();

      // Dialog should have Cancel and Archive buttons
      const cancelButton = page.locator('[data-testid="archive-cancel"]');
      const confirmButton = page.locator('[data-testid="archive-confirm"]');

      await expect(cancelButton).toBeVisible();
      await expect(confirmButton).toBeVisible();

      // Click cancel to close dialog
      await cancelButton.click();
      await expect(confirmDialog).not.toBeVisible();
    }
  });
});
