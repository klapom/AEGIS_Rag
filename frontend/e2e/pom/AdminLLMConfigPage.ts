import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';
import { navigateClientSide } from '../fixtures';

/**
 * Page Object for Admin LLM Configuration Page (Feature 36.3)
 * Handles model selection per use case, provider management, and configuration persistence
 */
export class AdminLLMConfigPage extends BasePage {
  // Page elements
  readonly llmConfigPage: Locator;
  readonly pageTitle: Locator;
  readonly pageDescription: Locator;

  // Use case selectors
  readonly intentClassificationSelector: Locator;
  readonly entityExtractionSelector: Locator;
  readonly answerGenerationSelector: Locator;
  readonly followupTitlesSelector: Locator;
  readonly queryDecompositionSelector: Locator;
  readonly visionVLMSelector: Locator;

  // Model dropdowns
  readonly intentClassificationDropdown: Locator;
  readonly entityExtractionDropdown: Locator;
  readonly answerGenerationDropdown: Locator;
  readonly followupTitlesDropdown: Locator;
  readonly queryDecompositionDropdown: Locator;
  readonly visionVLMDropdown: Locator;

  // Action buttons
  readonly refreshModelsButton: Locator;
  readonly saveConfigButton: Locator;

  // Status messages
  readonly saveSuccessMessage: Locator;
  readonly saveErrorMessage: Locator;

  constructor(page: Page) {
    super(page);

    // Page elements
    this.llmConfigPage = page.locator('[data-testid="llm-config-page"]');
    this.pageTitle = page.getByText('LLM Configuration').first();
    this.pageDescription = page.getByText('Configure which model to use for each use case');

    // Use case selectors
    this.intentClassificationSelector = page.locator(
      '[data-testid="usecase-selector-intent_classification"]'
    );
    this.entityExtractionSelector = page.locator(
      '[data-testid="usecase-selector-entity_extraction"]'
    );
    this.answerGenerationSelector = page.locator(
      '[data-testid="usecase-selector-answer_generation"]'
    );
    this.followupTitlesSelector = page.locator(
      '[data-testid="usecase-selector-followup_titles"]'
    );
    this.queryDecompositionSelector = page.locator(
      '[data-testid="usecase-selector-query_decomposition"]'
    );
    this.visionVLMSelector = page.locator('[data-testid="usecase-selector-vision_vlm"]');

    // Model dropdowns
    this.intentClassificationDropdown = page.locator(
      '[data-testid="model-dropdown-intent_classification"]'
    );
    this.entityExtractionDropdown = page.locator(
      '[data-testid="model-dropdown-entity_extraction"]'
    );
    this.answerGenerationDropdown = page.locator(
      '[data-testid="model-dropdown-answer_generation"]'
    );
    this.followupTitlesDropdown = page.locator(
      '[data-testid="model-dropdown-followup_titles"]'
    );
    this.queryDecompositionDropdown = page.locator(
      '[data-testid="model-dropdown-query_decomposition"]'
    );
    this.visionVLMDropdown = page.locator('[data-testid="model-dropdown-vision_vlm"]');

    // Action buttons
    this.refreshModelsButton = page.locator('[data-testid="refresh-models-button"]');
    this.saveConfigButton = page.locator('[data-testid="save-config-button"]');

    // Status messages
    this.saveSuccessMessage = page.getByText(/saved/i);
    this.saveErrorMessage = page.getByText(/error/i);
  }

  /**
   * Navigate to LLM Config page
   * Sprint 123.7: Use navigateClientSide to preserve auth state
   */
  async goto(path: string = '/admin/llm-config') {
    await navigateClientSide(this.page, path);
    await this.llmConfigPage.waitFor({ state: 'visible', timeout: 10000 });
  }

  /**
   * Get all use case selectors
   */
  getUseCaseSelectors() {
    return [
      this.intentClassificationSelector,
      this.entityExtractionSelector,
      this.answerGenerationSelector,
      this.followupTitlesSelector,
      this.queryDecompositionSelector,
      this.visionVLMSelector,
    ];
  }

  /**
   * Get all model dropdowns
   */
  getModelDropdowns() {
    return [
      this.intentClassificationDropdown,
      this.entityExtractionDropdown,
      this.answerGenerationDropdown,
      this.followupTitlesDropdown,
      this.queryDecompositionDropdown,
      this.visionVLMDropdown,
    ];
  }

  /**
   * Select a model for a use case
   */
  async selectModel(useCase: string, modelId: string) {
    const dropdown = this.page.locator(`[data-testid="model-dropdown-${useCase}"]`);
    await dropdown.selectOption(modelId);
  }

  /**
   * Get the current selected model for a use case
   */
  async getSelectedModel(useCase: string): Promise<string> {
    const dropdown = this.page.locator(`[data-testid="model-dropdown-${useCase}"]`);
    return await dropdown.inputValue();
  }

  /**
   * Save the configuration
   */
  async saveConfig() {
    await this.saveConfigButton.click();
  }

  /**
   * Refresh available models
   */
  async refreshModels() {
    await this.refreshModelsButton.click();
  }

  /**
   * Get configuration from localStorage
   */
  async getStoredConfig(): Promise<any> {
    const config = await this.page.evaluate(() => {
      return localStorage.getItem('aegis-rag-llm-config');
    });
    return config ? JSON.parse(config) : null;
  }

  /**
   * Clear configuration from localStorage
   */
  async clearStoredConfig() {
    await this.page.evaluate(() => {
      localStorage.removeItem('aegis-rag-llm-config');
    });
  }

  /**
   * Get all available model options for a use case
   */
  async getAvailableModels(useCase: string): Promise<string[]> {
    const dropdown = this.page.locator(`[data-testid="model-dropdown-${useCase}"]`);
    const options = await dropdown.locator('option').allTextContents();
    return options;
  }

  /**
   * Get provider badge text for a use case
   */
  async getProviderBadge(useCase: string): Promise<string> {
    const selector = this.page.locator(`[data-testid="usecase-selector-${useCase}"]`);
    const badge = selector.locator('span').filter({ hasText: /Local|Cloud/ });
    return await badge.textContent() || '';
  }

  /**
   * Wait for save success message
   */
  async waitForSaveSuccess(timeout: number = 5000) {
    await this.saveSuccessMessage.waitFor({ state: 'visible', timeout });
  }

  /**
   * Check if page is in dark mode
   */
  async isDarkMode(): Promise<boolean> {
    const htmlClass = await this.page.locator('html').getAttribute('class');
    return (htmlClass || '').includes('dark');
  }

  /**
   * Toggle dark mode
   */
  async toggleDarkMode() {
    await this.page.evaluate(() => {
      document.documentElement.classList.toggle('dark');
    });
  }

  /**
   * Get the model name text for display
   */
  async getDisplayedModelName(useCase: string): Promise<string> {
    const dropdown = this.page.locator(`[data-testid="model-dropdown-${useCase}"]`);
    const selectedValue = await dropdown.inputValue();
    const option = dropdown.locator(`option[value="${selectedValue}"]`);
    return await option.textContent() || '';
  }
}
