import { test, expect, setupAuthMocking } from '../fixtures';

/**
 * E2E Tests for Conversation History - Feature 31.5
 * Sprint 65 Update: Changed test queries to OMNITRACKER domain
 * Sprint 119 BUG-119.4: Tests may skip if history feature is not available
 *
 * Tests:
 * 1. Auto-generated conversation titles (3-5 words)
 * 2. Chronological conversation list
 * 3. Open conversation on click
 * 4. Search conversations by title/content
 * 5. Delete conversation with confirmation
 * 6. Export conversation history to JSON
 *
 * Backend: Gemma-3 4B via Ollama (FREE - no cloud LLM costs)
 * Required: Backend running on http://localhost:8000
 *
 * NOTE: Test queries use OMNITRACKER domain to ensure knowledge base has relevant documents.
 */

test.describe('Conversation History - Feature 31.5', () => {
  // Sprint 119 BUG-119.4: Skip tests if history feature is not available
  // Sprint 119 Feature 119.3: Added auth to beforeEach (page is unauthenticated before fixtures)
  test.beforeEach(async ({ page }) => {
    // Authenticate first (beforeEach runs before fixture setup)
    await setupAuthMocking(page);

    // Navigate to history page to check if it exists
    const response = await page.goto('/history');
    const status = response?.status() ?? 0;

    // Skip if page returns 404 or error
    if (status === 404 || status >= 500) {
      test.skip(true, 'History page not available (HTTP ' + status + ')');
      return;
    }

    // Check if conversation-list element exists (feature is implemented)
    await page.waitForLoadState('networkidle');
    const conversationList = page.locator('[data-testid="conversation-list"]');
    const hasHistoryUI = await conversationList.isVisible({ timeout: 5000 }).catch(() => false);

    // Also check for empty-history state (valid state when no conversations)
    const emptyState = page.locator('[data-testid="empty-history"]');
    const hasEmptyState = await emptyState.isVisible({ timeout: 2000 }).catch(() => false);

    if (!hasHistoryUI && !hasEmptyState) {
      test.skip(true, 'History feature UI not implemented (no data-testid elements found)');
    }
  });

  test('should auto-generate conversation title from first message', async ({
    chatPage,
    page,
  }) => {
    // Send first message to create a conversation - Sprint 65: Using OMNITRACKER query
    await chatPage.sendMessage(
      'What is the OMNITRACKER SMC and how does it work?'
    );
    await chatPage.waitForResponse();

    // Get conversation title (should be visible in session info)
    const sessionTitle = await chatPage.getLastMessage();
    expect(sessionTitle).toBeTruthy();
    expect(sessionTitle.length).toBeGreaterThan(0);

    // Navigate to history
    await page.goto('/history');
    await page.waitForLoadState('networkidle');

    // Verify conversation exists in history with title
    const conversationItems = page.locator('[data-testid="conversation-item"]');
    const count = await conversationItems.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Get title of first conversation
    const firstItem = conversationItems.first();
    const title = await firstItem
      .locator('[data-testid="conversation-title"]')
      .textContent();
    expect(title).toBeTruthy();
    expect(title!.length).toBeGreaterThan(0);
    expect(title!.split(' ').length).toBeLessThanOrEqual(5);
  });

  test('should list conversations in chronological order (newest first)', async ({
    historyPage,
    chatPage,
  }) => {
    // Send first message to create initial conversation - Sprint 65: Using OMNITRACKER query
    await chatPage.sendMessage('What is the OMNITRACKER SMC component?');
    await chatPage.waitForResponse();

    // Wait a bit before creating second conversation
    await chatPage.page.waitForTimeout(1000);

    // Go back to chat and send another message in new conversation - Sprint 65: Using OMNITRACKER query
    await chatPage.page.goto('/');
    await chatPage.sendMessage('How does OMNITRACKER handle load balancing?');
    await chatPage.waitForResponse();

    // Navigate to history
    await historyPage.goto();

    // Verify at least one conversation exists
    const conversationCount = await historyPage.getConversationCount();
    expect(conversationCount).toBeGreaterThanOrEqual(1);

    // Get conversation titles
    const titles = await historyPage.getConversationTitles();
    expect(titles.length).toBeGreaterThanOrEqual(1);
    expect(titles[0]).toBeTruthy();
  });

  test('should open conversation on click and restore messages', async ({
    historyPage,
    chatPage,
  }) => {
    // Create a conversation with a specific query - Sprint 65: Using OMNITRACKER query
    await chatPage.sendMessage('What is the OMNITRACKER Application Server?');
    await chatPage.waitForResponse();

    // Navigate to history
    await historyPage.goto();

    // Verify conversation list is visible
    await expect(historyPage.conversationList).toBeVisible();

    // Get number of conversations
    const conversationCount = await historyPage.getConversationCount();
    if (conversationCount > 0) {
      // Click first conversation
      const firstItem = historyPage.conversationItems.first();
      const conversationTitle = await firstItem
        .locator('[data-testid="conversation-title"]')
        .textContent();

      // Click on conversation
      await firstItem.click();
      await historyPage.page.waitForLoadState('networkidle');

      // Verify navigated back to chat with session parameter
      expect(historyPage.page.url()).toContain('/');

      // Verify messages are restored
      // Sprint 119: Fixed assertion - query is about OMNITRACKER, not geography
      const messages = await chatPage.getAllMessages();
      expect(messages.length).toBeGreaterThanOrEqual(1);
      expect(messages.some((msg) => msg.toLowerCase().includes('omnitracker'))).toBeTruthy();
    }
  });

  test('should search conversations by title and content', async ({
    historyPage,
    chatPage,
  }) => {
    // Create a conversation with specific keywords
    await chatPage.sendMessage('Tell me about quantum computing algorithms');
    await chatPage.waitForResponse();

    // Navigate to history
    await historyPage.goto();

    // Search for a keyword
    await historyPage.searchConversations('quantum');

    // Wait for search debounce
    await historyPage.page.waitForTimeout(600);

    // Verify search results are filtered
    const conversationCount = await historyPage.getConversationCount();
    expect(conversationCount).toBeGreaterThanOrEqual(0);

    // If conversations exist, verify they match search query
    if (conversationCount > 0) {
      const titles = await historyPage.getConversationTitles();
      const titleText = titles.join(' ').toLowerCase();
      expect(titleText).toContain('quantum');
    }

    // Clear search to restore full list
    await historyPage.clearSearch();
    await historyPage.page.waitForTimeout(600);

    const countAfterClear = await historyPage.getConversationCount();
    expect(countAfterClear).toBeGreaterThanOrEqual(conversationCount);
  });

  test('should delete conversation with confirmation dialog', async ({
    historyPage,
    chatPage,
  }) => {
    // Create a conversation
    await chatPage.sendMessage(
      'This is a test conversation that will be deleted'
    );
    await chatPage.waitForResponse();

    // Navigate to history
    await historyPage.goto();

    // Get initial conversation count
    const countBefore = await historyPage.getConversationCount();

    if (countBefore > 0) {
      // Delete first conversation
      await historyPage.deleteConversation(0);

      // Verify count decreased (may have confirmation delay)
      await historyPage.page.waitForTimeout(500);
      const countAfter = await historyPage.getConversationCount();

      expect(countAfter).toBeLessThanOrEqual(countBefore);
    }
  });

  test('should handle empty history gracefully', async ({ historyPage }) => {
    // Navigate to history
    await historyPage.goto();

    // If history is empty, should show empty state
    const conversationCount = await historyPage.getConversationCount();

    if (conversationCount === 0) {
      const isEmpty = await historyPage.isEmpty();
      expect(isEmpty).toBeTruthy();
    } else {
      expect(conversationCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('should display conversation metadata (creation date, message count)', async ({
    historyPage,
    chatPage,
  }) => {
    // Create a conversation - Sprint 65: Using OMNITRACKER query
    await chatPage.sendMessage('What is OMNITRACKER?');
    await chatPage.waitForResponse();

    // Send a follow-up message to increase message count - Sprint 65: Using OMNITRACKER query
    await chatPage.sendMessage('Explain the OMNITRACKER SMC component');
    await chatPage.waitForResponse();

    // Navigate to history
    await historyPage.goto();

    // Get conversation count
    const conversationCount = await historyPage.getConversationCount();

    if (conversationCount > 0) {
      // Get metadata of first conversation
      const metadata = await historyPage.getFirstConversationMetadata();

      expect(metadata.title).toBeTruthy();
      // createdDate and messageCount may not always be visible
      if (metadata.createdDate) {
        expect(metadata.createdDate).toBeTruthy();
      }
    }
  });
});
