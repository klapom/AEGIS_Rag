import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * Page Object for Conversation History
 * Handles session management, conversation list, and history operations
 */
export class HistoryPage extends BasePage {
  readonly conversationList: Locator;
  readonly conversationItems: Locator;
  readonly deleteButton: Locator;
  readonly emptyState: Locator;
  readonly searchBox: Locator;
  readonly sessionTitle: Locator;
  readonly sessionCreatedDate: Locator;
  readonly sessionMessageCount: Locator;

  constructor(page: Page) {
    super(page);
    this.conversationList = page.locator('[data-testid="conversation-list"]');
    this.conversationItems = page.locator('[data-testid="conversation-item"]');
    this.deleteButton = page.locator('[data-testid="delete-conversation"]');
    this.emptyState = page.locator('[data-testid="empty-history"]');
    this.searchBox = page.locator('[data-testid="search-history"]');
    this.sessionTitle = page.locator('[data-testid="session-title"]');
    this.sessionCreatedDate = page.locator('[data-testid="session-created-date"]');
    this.sessionMessageCount = page.locator('[data-testid="session-message-count"]');
  }

  /**
   * Navigate to history page
   */
  async goto() {
    await super.goto('/history');
    await this.waitForNetworkIdle();
  }

  /**
   * Get number of conversations
   */
  async getConversationCount(): Promise<number> {
    return await this.conversationItems.count();
  }

  /**
   * Click on a conversation by index
   */
  async clickConversation(index: number) {
    const conversation = this.conversationItems.nth(index);
    await conversation.click();
    await this.waitForNetworkIdle();
  }

  /**
   * Click on a conversation by title
   */
  async clickConversationByTitle(title: string) {
    const conversation = this.page.locator(
      `[data-testid="conversation-item"] >> text="${title}"`
    );
    await conversation.click();
    await this.waitForNetworkIdle();
  }

  /**
   * Get conversation titles
   */
  async getConversationTitles(): Promise<string[]> {
    const titles: string[] = [];
    const count = await this.conversationItems.count();
    for (let i = 0; i < count; i++) {
      const item = this.conversationItems.nth(i);
      const title = await item.locator('[data-testid="conversation-title"]').textContent();
      if (title) titles.push(title);
    }
    return titles;
  }

  /**
   * Delete a conversation by index
   */
  async deleteConversation(index: number) {
    const item = this.conversationItems.nth(index);
    await item.hover();
    const deleteBtn = item.locator('[data-testid="delete-conversation"]');
    await deleteBtn.click();

    // Confirm deletion if dialog appears
    const confirmBtn = this.page.locator('[data-testid="confirm-delete"]');
    if (await confirmBtn.isVisible()) {
      await confirmBtn.click();
    }

    await this.waitForNetworkIdle();
  }

  /**
   * Search for conversations
   */
  async searchConversations(query: string) {
    await this.searchBox.fill(query);
    await this.page.waitForTimeout(500); // Debounce delay
  }

  /**
   * Check if history is empty
   */
  async isEmpty(): Promise<boolean> {
    try {
      await this.emptyState.waitFor({ state: 'visible', timeout: 1000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Clear search box
   */
  async clearSearch() {
    await this.searchBox.clear();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get metadata of first conversation
   */
  async getFirstConversationMetadata(): Promise<{
    title: string | null;
    createdDate: string | null;
    messageCount: string | null;
  }> {
    const firstItem = this.conversationItems.first();
    return {
      title: await firstItem.locator('[data-testid="conversation-title"]').textContent(),
      createdDate: await firstItem
        .locator('[data-testid="conversation-created"]')
        .textContent(),
      messageCount: await firstItem
        .locator('[data-testid="conversation-message-count"]')
        .textContent(),
    };
  }

  /**
   * Export conversation
   */
  async exportConversation(index: number) {
    const item = this.conversationItems.nth(index);
    await item.hover();
    const exportBtn = item.locator('[data-testid="export-conversation"]');
    if (await exportBtn.isVisible()) {
      await exportBtn.click();
    }
  }

  /**
   * Check if conversation list is visible
   */
  async isListVisible(): Promise<boolean> {
    return await this.isVisible('[data-testid="conversation-list"]');
  }
}
