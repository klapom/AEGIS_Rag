import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * Page Object for Chat Interface
 * Handles message input, sending, streaming responses, and citations
 */
export class ChatPage extends BasePage {
  readonly messageInput: Locator;
  readonly sendButton: Locator;
  readonly messages: Locator;
  readonly citations: Locator;
  readonly followupQuestions: Locator;
  readonly streamingIndicator: Locator;
  readonly sessionIdBadge: Locator;

  constructor(page: Page) {
    super(page);
    this.messageInput = page.locator('[data-testid="message-input"]');
    this.sendButton = page.locator('[data-testid="send-button"]');
    this.messages = page.locator('[data-testid="message"]');
    this.citations = page.locator('[data-testid="citation"]');
    this.followupQuestions = page.locator('[data-testid="followup-question"]');
    this.streamingIndicator = page.locator('[data-streaming="true"]');
    this.sessionIdBadge = page.locator('[data-testid="session-id"]');
  }

  /**
   * Navigate to chat page
   */
  async goto() {
    await super.goto('/');
    await this.waitForNetworkIdle();
  }

  /**
   * Send a message to the chat
   */
  async sendMessage(text: string) {
    // Ensure input is visible and focused
    await this.messageInput.waitFor({ state: 'visible' });
    await this.messageInput.fill(text);

    // Verify text was entered
    const inputValue = await this.messageInput.inputValue();
    if (inputValue !== text) {
      throw new Error(`Failed to enter message. Expected: "${text}", Got: "${inputValue}"`);
    }

    // Check if send button is enabled before clicking
    // Wait for React state to update after filling input
    await this.page.waitForTimeout(100);
    const isDisabled = await this.sendButton.isDisabled();
    if (isDisabled) {
      // Button is disabled (e.g., empty/whitespace input)
      // Don't attempt to send - this is expected behavior
      return;
    }

    // Click send button
    await this.sendButton.click();

    // Wait for message to appear in history
    await this.page.waitForTimeout(500);
  }

  /**
   * Wait for LLM to generate response
   * Handles SSE streaming and response completion
   * Sprint 46: Increased timeout to 90s for gpt-oss:20b model
   * Sprint 113: Increased to 150s to match BasePage.waitForLLMResponse
   *   - First Token: 120s (80% of 150s) for Entity Expansion + LLM warmup
   *   - Streaming Complete: 150s total
   */
  async waitForResponse(timeout = 150000) {
    // Wait for streaming to complete
    try {
      await this.waitForLLMResponse(timeout);
    } catch (error) {
      throw new Error(
        `Failed to receive LLM response within ${timeout}ms. Backend may be unreachable.`
      );
    }
  }

  /**
   * Get the last message in the chat
   */
  async getLastMessage(): Promise<string> {
    const lastMessage = this.messages.last();
    await lastMessage.waitFor({ state: 'visible' });
    return (await lastMessage.textContent()) || '';
  }

  /**
   * Get all messages in current conversation
   */
  async getAllMessages(): Promise<string[]> {
    const count = await this.messages.count();
    const messages: string[] = [];
    for (let i = 0; i < count; i++) {
      const text = await this.messages.nth(i).textContent();
      if (text) messages.push(text);
    }
    return messages;
  }

  /**
   * Get all citations in the last response
   */
  async getCitations(): Promise<string[]> {
    const citations: string[] = [];
    const count = await this.citations.count();
    for (let i = 0; i < count; i++) {
      const text = await this.citations.nth(i).textContent();
      if (text) citations.push(text);
    }
    return citations;
  }

  /**
   * Get citation count in last response
   */
  async getCitationCount(): Promise<number> {
    return await this.citations.count();
  }

  /**
   * Check if citations are displayed in response
   */
  async hasCitations(): Promise<boolean> {
    return (await this.citations.count()) > 0;
  }

  /**
   * Get follow-up questions suggested by the model
   */
  async getFollowupQuestions(): Promise<string[]> {
    const questions: string[] = [];
    const count = await this.followupQuestions.count();
    for (let i = 0; i < count; i++) {
      const text = await this.followupQuestions.nth(i).textContent();
      if (text) questions.push(text);
    }
    return questions;
  }

  /**
   * Get follow-up question count
   */
  async getFollowupQuestionCount(): Promise<number> {
    return await this.followupQuestions.count();
  }

  /**
   * Click on a follow-up question
   */
  async clickFollowupQuestion(index: number) {
    const question = this.followupQuestions.nth(index);
    await question.click();
    await this.waitForResponse();
  }

  /**
   * Click on a citation to see source
   */
  async clickCitation(index: number) {
    const citation = this.citations.nth(index);
    await citation.click();
  }

  /**
   * Get current session ID
   */
  async getSessionId(): Promise<string | null> {
    return await this.sessionIdBadge.getAttribute('data-session-id');
  }

  /**
   * Check if input field is ready
   */
  async isInputReady(): Promise<boolean> {
    try {
      await this.messageInput.waitFor({ state: 'visible', timeout: 1000 });
      const disabled = await this.messageInput.isDisabled();
      return !disabled;
    } catch {
      return false;
    }
  }

  /**
   * Clear the message input
   */
  async clearInput() {
    await this.messageInput.clear();
  }

  /**
   * Get streaming status
   */
  async isStreaming(): Promise<boolean> {
    try {
      await this.streamingIndicator.waitFor({ state: 'visible', timeout: 1000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Send message with Enter key
   */
  async sendMessageWithEnter(text: string) {
    await this.messageInput.fill(text);
    await this.messageInput.press('Enter');
    await this.page.waitForTimeout(500);
  }

  /**
   * Get full conversation text (all messages including assistant responses)
   */
  async getFullConversation(): Promise<string> {
    const messages = await this.getAllMessages();
    return messages.join('\n\n');
  }

  /**
   * Sprint 69 Feature 69.1: Get conversation context
   * Returns the last N messages for context verification
   */
  async getConversationContext(messageCount: number = 3): Promise<string[]> {
    const allMessages = await this.getAllMessages();
    return allMessages.slice(-messageCount);
  }

  /**
   * Sprint 69 Feature 69.1: Verify follow-up maintains context
   * Checks if response contains references to previous conversation
   */
  async verifyContextMaintained(contextKeywords: string[]): Promise<boolean> {
    const lastResponse = await this.getLastMessage();
    const lowerResponse = lastResponse.toLowerCase();

    // Check if response contains any context keywords
    return contextKeywords.some((keyword) => lowerResponse.includes(keyword.toLowerCase()));
  }

  /**
   * Sprint 69 Feature 69.1: Get message by index
   * Returns specific message from conversation history
   */
  async getMessageByIndex(index: number): Promise<string> {
    const message = this.messages.nth(index);
    await message.waitFor({ state: 'visible' });
    return (await message.textContent()) || '';
  }

  /**
   * Sprint 69 Feature 69.1: Wait for specific message count
   * Waits until conversation has expected number of messages
   */
  async waitForMessageCount(expectedCount: number, timeout: number = 10000): Promise<void> {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      const count = await this.messages.count();
      if (count >= expectedCount) return;
      await this.page.waitForTimeout(500);
    }
    throw new Error(`Message count did not reach ${expectedCount} within ${timeout}ms`);
  }

  /**
   * Sprint 69 Feature 69.1: Click follow-up and verify context preserved
   * Enhanced follow-up click with context verification
   */
  async clickFollowupAndVerifyContext(
    index: number,
    expectedContextKeywords: string[]
  ): Promise<void> {
    // Get initial message count
    const initialCount = await this.messages.count();

    // Click follow-up
    const question = this.followupQuestions.nth(index);
    await question.click();

    // Wait for response
    await this.waitForResponse();

    // Verify new messages added
    await this.waitForMessageCount(initialCount + 2); // User message + assistant response

    // Verify context maintained
    const contextMaintained = await this.verifyContextMaintained(expectedContextKeywords);
    if (!contextMaintained) {
      const lastResponse = await this.getLastMessage();
      throw new Error(
        `Context not maintained. Expected keywords: ${expectedContextKeywords.join(', ')}. Got: ${lastResponse.substring(0, 200)}...`
      );
    }
  }
}
