import { Page } from '@playwright/test';

/**
 * Base Page Object for all pages
 * Provides common methods for navigation, waiting, and assertions
 */
export class BasePage {
  constructor(public readonly page: Page) {}

  /**
   * Navigate to a path
   */
  async goto(path: string = '/') {
    await this.page.goto(path);
  }

  /**
   * Wait for SSE streaming to complete
   * Used for chat responses and real-time updates
   */
  async waitForSSE(selector: string, timeout = 10000) {
    try {
      await this.page.waitForSelector(selector, { state: 'visible', timeout });
    } catch (error) {
      throw new Error(
        `SSE element not found: ${selector}. Streaming may have failed.`
      );
    }
  }

  /**
   * Wait for LLM response generation
   * LLM calls can take 10-20 seconds, especially for streaming
   *
   * Sprint 46: Updated to work with new ConversationView/MessageBubble components
   * Waits for streaming to complete by checking for:
   * 1. An assistant message bubble to appear (confirms response started)
   * 2. The streaming indicator to show completion (data-streaming="false")
   */
  async waitForLLMResponse(timeout = 90000) {
    try {
      // Wait for an assistant message bubble to appear
      // This confirms the backend has started responding
      // Sprint 46: Allow 80% of timeout for first token (gpt-oss:20b is slow to start)
      await this.page.locator('[data-testid="message-bubble"][data-role="assistant"]').first().waitFor({
        state: 'visible',
        timeout: Math.floor(timeout * 0.8)
      });

      // Then wait for streaming to complete (data-streaming="false" on assistant message)
      // Poll for this state since attribute value changes during streaming
      await this.page.waitForFunction(
        () => {
          // Look for an assistant message that is no longer streaming
          const assistantMessages = document.querySelectorAll('[data-testid="message-bubble"][data-role="assistant"]');
          // Check if any assistant message has finished streaming
          for (const msg of assistantMessages) {
            if (msg.getAttribute('data-streaming') === 'false') {
              return true;
            }
          }
          return false;
        },
        { timeout }
      );

      // Buffer for React re-render with citations and sources
      await this.page.waitForTimeout(1000);
    } catch (error) {
      throw new Error(
        `LLM response timeout after ${timeout}ms. Check backend connectivity.`
      );
    }
  }

  /**
   * Wait for loading state to complete
   */
  async waitForLoadingComplete(timeout = 10000) {
    const loadingSpinner = '[data-testid="loading-spinner"]';
    try {
      await this.page.waitForFunction(
        () => !document.querySelector(loadingSpinner),
        { timeout }
      );
    } catch (error) {
      // Loading spinner may not exist for some operations
    }
  }

  /**
   * Get page title
   */
  async getTitle(): Promise<string> {
    return await this.page.title();
  }

  /**
   * Check if page is navigated to expected path
   * Sprint 65 Fix: Use dynamic port extraction instead of hardcoded 5173
   */
  async expectPath(path: string) {
    const url = new URL(this.page.url());
    const currentPath = url.pathname;
    if (currentPath !== path) {
      throw new Error(`Expected path ${path}, but got ${currentPath}`);
    }
  }

  /**
   * Wait for network to be idle
   * Increased timeout for LLM responses which can take 10-30 seconds
   */
  async waitForNetworkIdle(timeout = 30000) {
    await this.page.waitForLoadState('networkidle', { timeout });
  }

  /**
   * Take screenshot for debugging
   */
  async screenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png` });
  }

  /**
   * Get text content of an element
   */
  async getText(selector: string): Promise<string> {
    return (await this.page.locator(selector).textContent()) || '';
  }

  /**
   * Check if element is visible
   */
  async isVisible(selector: string): Promise<boolean> {
    try {
      await this.page.waitForSelector(selector, { state: 'visible', timeout: 1000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Click an element
   */
  async click(selector: string) {
    await this.page.locator(selector).click();
  }

  /**
   * Fill input field
   */
  async fill(selector: string, text: string) {
    await this.page.locator(selector).fill(text);
  }

  /**
   * Press key on focused element
   */
  async press(selector: string, key: string) {
    await this.page.locator(selector).press(key);
  }

  /**
   * Wait for backend health check
   */
  async waitForBackendHealth(timeout = 30000) {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      try {
        const response = await this.page.request.get('http://localhost:8000/health');
        if (response.ok()) {
          return;
        }
      } catch {
        // Backend not ready yet
      }
      await this.page.waitForTimeout(1000);
    }
    throw new Error('Backend health check failed after timeout');
  }
}
