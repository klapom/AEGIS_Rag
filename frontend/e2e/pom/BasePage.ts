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
   */
  async waitForLLMResponse(timeout = 20000) {
    // Initial debounce to ensure streaming starts
    await this.page.waitForTimeout(500);

    // Wait for streaming indicator to disappear
    const streamingIndicator = '[data-streaming="true"]';
    try {
      await this.page.waitForFunction(
        () => !document.querySelector(streamingIndicator),
        { timeout }
      );
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
   */
  async expectPath(path: string) {
    const currentPath = this.page.url().split('localhost:5173')[1];
    if (currentPath !== path) {
      throw new Error(`Expected path ${path}, but got ${currentPath}`);
    }
  }

  /**
   * Wait for network to be idle
   */
  async waitForNetworkIdle(timeout = 5000) {
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
