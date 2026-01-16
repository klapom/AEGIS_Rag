import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * Page Object for Admin Domain Training Page (Feature 45.3, 45.10, 45.12)
 * Handles domain management, training configuration, and classification workflows
 *
 * Supports:
 * - Domain creation with metadata and model selection
 * - Training dataset upload (JSONL format)
 * - Metric configuration (balanced, precision-focused, recall-focused, custom)
 * - Document domain classification
 * - Training status monitoring
 */
export class AdminDomainTrainingPage extends BasePage {
  // Main page elements
  readonly domainTrainingPage: Locator;
  readonly pageTitle: Locator;
  readonly newDomainButton: Locator;
  readonly domainList: Locator;
  readonly domainRow: (domainName: string) => Locator;

  // New Domain Wizard - Step 1 (Domain Configuration)
  readonly newDomainWizard: Locator;
  readonly wizardTitle: Locator;
  readonly domainNameInput: Locator;
  readonly domainDescriptionInput: Locator;
  readonly modelSelect: Locator;
  readonly nextStepButton: Locator;
  readonly cancelButton: Locator;
  readonly backButton: Locator;

  // Metric Configuration Panel
  readonly metricConfigPanel: Locator;
  readonly presetBalanced: Locator;
  readonly presetPrecisionFocused: Locator;
  readonly presetRecallFocused: Locator;
  readonly presetCustom: Locator;
  readonly weightSlider: Locator;
  readonly entityMetricSelect: Locator;
  readonly relationMetricSelect: Locator;
  readonly metricPreview: Locator;

  // New Domain Wizard - Step 2 (Dataset Upload)
  readonly datasetUploadSection: Locator;
  readonly datasetDropzone: Locator;
  readonly datasetFileInput: Locator;
  readonly samplePreviewContainer: Locator;
  readonly samplePreview: (sampleIndex: number) => Locator;
  readonly sampleCount: Locator;
  readonly uploadProgressBar: Locator;

  // Validation errors
  readonly validationError: Locator;
  readonly domainNameError: Locator;
  readonly datasetError: Locator;

  // Training related
  readonly trainingButton: Locator;
  readonly trainingStatusSection: Locator;
  readonly trainingProgress: Locator;
  readonly trainingCurrentStep: Locator;
  readonly trainingMetrics: Locator;
  readonly pauseTrainingButton: Locator;
  readonly cancelTrainingButton: Locator;

  // Domain detail view
  readonly domainDetail: Locator;
  readonly domainName: Locator;
  readonly domainDescription: Locator;
  readonly domainStatus: Locator;
  readonly llmModel: Locator;
  readonly createdAt: Locator;
  readonly trainedAt: Locator;
  readonly editDomainButton: Locator;
  readonly deleteDomainButton: Locator;

  // Domain auto-discovery
  readonly autoDiscoveryButton: Locator;
  readonly autoDiscoveryWizard: Locator;
  readonly autoDiscoverySampleInput: Locator;
  readonly autoDiscoveryAnalyzeButton: Locator;
  readonly autoDiscoverySuggestion: Locator;
  readonly autoDiscoverySuggestionName: Locator;
  readonly autoDiscoverySuggestionDescription: Locator;
  readonly autoDiscoverySuggestionConfidence: Locator;

  // Training data augmentation
  readonly augmentationButton: Locator;
  readonly augmentationWizard: Locator;
  readonly augmentationTargetCount: Locator;
  readonly augmentationGenerateButton: Locator;
  readonly augmentationProgress: Locator;
  readonly augmentationResults: Locator;

  constructor(page: Page) {
    super(page);

    // Main page elements
    this.domainTrainingPage = page.locator('[data-testid="domain-training-page"]');
    this.pageTitle = page.getByRole('heading', { name: /Domain Training/i });
    this.newDomainButton = page.locator('[data-testid="new-domain-button"]');
    // Sprint 106 Fix: Domain list can be empty or populated - handle both testids
    this.domainList = page.locator('[data-testid^="domain-list"]');
    this.domainRow = (domainName: string) =>
      page.locator(`[data-testid="domain-row-${domainName}"]`);

    // New Domain Wizard - Step 1
    this.newDomainWizard = page.locator('[data-testid="new-domain-wizard"]');
    this.wizardTitle = page.getByText(/Create New Domain/i);
    this.domainNameInput = page.locator('[data-testid="domain-name-input"]');
    this.domainDescriptionInput = page.locator('[data-testid="domain-description-input"]');
    this.modelSelect = page.locator('[data-testid="model-select"]');
    this.nextStepButton = page.locator('[data-testid="next-step-button"]');
    this.cancelButton = page.locator('[data-testid="cancel-button"]');
    this.backButton = page.locator('[data-testid="back-button"]');

    // Metric Configuration Panel
    this.metricConfigPanel = page.locator('[data-testid="metric-config-panel"]');
    this.presetBalanced = page.locator('[data-testid="preset-balanced"]');
    this.presetPrecisionFocused = page.locator('[data-testid="preset-precision_focused"]');
    this.presetRecallFocused = page.locator('[data-testid="preset-recall_focused"]');
    this.presetCustom = page.locator('[data-testid="preset-custom"]');
    this.weightSlider = page.locator('[data-testid="weight-slider"]');
    this.entityMetricSelect = page.locator('[data-testid="entity-metric-select"]');
    this.relationMetricSelect = page.locator('[data-testid="relation-metric-select"]');
    this.metricPreview = page.locator('[data-testid="metric-preview"]');

    // New Domain Wizard - Step 2
    this.datasetUploadSection = page.locator('[data-testid="dataset-upload-section"]');
    this.datasetDropzone = page.locator('[data-testid="dataset-dropzone"]');
    this.datasetFileInput = page.locator('[data-testid="dataset-file-input"]');
    this.samplePreviewContainer = page.locator('[data-testid="sample-preview-container"]');
    this.samplePreview = (sampleIndex: number) =>
      page.locator(`[data-testid="sample-preview-${sampleIndex}"]`);
    this.sampleCount = page.locator('[data-testid="sample-count"]');
    this.uploadProgressBar = page.locator('[data-testid="upload-progress-bar"]');

    // Validation errors
    this.validationError = page.locator('[data-testid="validation-error"]');
    this.domainNameError = page.locator('[data-testid="domain-name-error"]');
    this.datasetError = page.locator('[data-testid="dataset-error"]');

    // Training related
    this.trainingButton = page.locator('[data-testid="training-button"]');
    this.trainingStatusSection = page.locator('[data-testid="training-status-section"]');
    this.trainingProgress = page.locator('[data-testid="training-progress"]');
    this.trainingCurrentStep = page.locator('[data-testid="training-current-step"]');
    this.trainingMetrics = page.locator('[data-testid="training-metrics"]');
    this.pauseTrainingButton = page.locator('[data-testid="pause-training-button"]');
    this.cancelTrainingButton = page.locator('[data-testid="cancel-training-button"]');

    // Domain detail view
    this.domainDetail = page.locator('[data-testid="domain-detail"]');
    this.domainName = page.locator('[data-testid="domain-detail-name"]');
    this.domainDescription = page.locator('[data-testid="domain-detail-description"]');
    this.domainStatus = page.locator('[data-testid="domain-detail-status"]');
    this.llmModel = page.locator('[data-testid="domain-detail-llm-model"]');
    this.createdAt = page.locator('[data-testid="domain-detail-created-at"]');
    this.trainedAt = page.locator('[data-testid="domain-detail-trained-at"]');
    this.editDomainButton = page.locator('[data-testid="edit-domain-button"]');
    this.deleteDomainButton = page.locator('[data-testid="delete-domain-button"]');

    // Domain auto-discovery
    this.autoDiscoveryButton = page.locator('[data-testid="auto-discovery-button"]');
    this.autoDiscoveryWizard = page.locator('[data-testid="auto-discovery-wizard"]');
    this.autoDiscoverySampleInput = page.locator('[data-testid="auto-discovery-sample-input"]');
    this.autoDiscoveryAnalyzeButton = page.locator('[data-testid="auto-discovery-analyze-button"]');
    this.autoDiscoverySuggestion = page.locator('[data-testid="auto-discovery-suggestion"]');
    this.autoDiscoverySuggestionName = page.locator(
      '[data-testid="auto-discovery-suggestion-name"]'
    );
    this.autoDiscoverySuggestionDescription = page.locator(
      '[data-testid="auto-discovery-suggestion-description"]'
    );
    this.autoDiscoverySuggestionConfidence = page.locator(
      '[data-testid="auto-discovery-suggestion-confidence"]'
    );

    // Training data augmentation
    this.augmentationButton = page.locator('[data-testid="augmentation-button"]');
    this.augmentationWizard = page.locator('[data-testid="augmentation-wizard"]');
    this.augmentationTargetCount = page.locator('[data-testid="augmentation-target-count"]');
    this.augmentationGenerateButton = page.locator('[data-testid="augmentation-generate-button"]');
    this.augmentationProgress = page.locator('[data-testid="augmentation-progress"]');
    this.augmentationResults = page.locator('[data-testid="augmentation-results"]');
  }

  /**
   * Navigate to Domain Training page
   */
  async goto(): Promise<void> {
    await this.page.goto('/admin/domain-training');
    await this.pageTitle.waitFor({ state: 'visible', timeout: 10000 });
  }

  /**
   * Click "New Domain" button to start wizard
   */
  async clickNewDomain(): Promise<void> {
    await this.newDomainButton.click();
    await this.wizardTitle.waitFor({ state: 'visible' });
  }

  /**
   * Fill domain name input
   */
  async fillDomainName(name: string): Promise<void> {
    await this.domainNameInput.fill(name);
  }

  /**
   * Fill domain description input
   */
  async fillDomainDescription(description: string): Promise<void> {
    await this.domainDescriptionInput.fill(description);
  }

  /**
   * Select LLM model from dropdown
   */
  async selectModel(modelName: string): Promise<void> {
    await this.modelSelect.selectOption(modelName);
  }

  /**
   * Select metric preset
   */
  async selectMetricPreset(preset: 'balanced' | 'precision_focused' | 'recall_focused' | 'custom'): Promise<void> {
    const presetMap = {
      balanced: this.presetBalanced,
      precision_focused: this.presetPrecisionFocused,
      recall_focused: this.presetRecallFocused,
      custom: this.presetCustom,
    };
    await presetMap[preset].click();
  }

  /**
   * Set custom metric weight (0-1)
   */
  async setMetricWeight(weight: number): Promise<void> {
    await this.weightSlider.fill(weight.toString());
  }

  /**
   * Click Next button to proceed to next step
   */
  async clickNext(): Promise<void> {
    await this.nextStepButton.click();
  }

  /**
   * Click Back button to go to previous step
   */
  async clickBack(): Promise<void> {
    await this.backButton.click();
  }

  /**
   * Click Cancel to close wizard
   */
  async clickCancel(): Promise<void> {
    await this.cancelButton.click();
  }

  /**
   * Upload dataset file (JSONL format)
   * @param fileName Name of the file to create
   * @param jsonlContent JSONL content as string
   */
  async uploadDataset(fileName: string, jsonlContent: string): Promise<void> {
    await this.datasetDropzone.setInputFiles({
      name: fileName,
      mimeType: 'application/json',
      buffer: Buffer.from(jsonlContent),
    });
    // Wait for upload to complete
    await this.page.waitForTimeout(500);
  }

  /**
   * Get the number of samples loaded
   */
  async getSampleCount(): Promise<number> {
    const text = await this.sampleCount.textContent();
    const match = text?.match(/(\d+)\s+samples/);
    return match ? parseInt(match[1]) : 0;
  }

  /**
   * Click the Training button to start training
   */
  async clickTraining(): Promise<void> {
    await this.trainingButton.click();
    await this.trainingStatusSection.waitFor({ state: 'visible' });
  }

  /**
   * Get current training status
   */
  async getTrainingStatus(): Promise<string> {
    const text = await this.trainingProgress.textContent();
    return text?.trim() || '';
  }

  /**
   * Open domain auto-discovery
   */
  async openAutoDiscovery(): Promise<void> {
    await this.autoDiscoveryButton.click();
    await this.autoDiscoveryWizard.waitFor({ state: 'visible' });
  }

  /**
   * Add sample texts for auto-discovery (one per line)
   */
  async addAutoDiscoverySamples(samples: string[]): Promise<void> {
    for (const sample of samples) {
      await this.autoDiscoverySampleInput.fill(sample);
      await this.autoDiscoverySampleInput.press('Enter');
    }
  }

  /**
   * Click analyze button for auto-discovery
   */
  async clickAutoDiscoveryAnalyze(): Promise<void> {
    await this.autoDiscoveryAnalyzeButton.click();
    await this.autoDiscoverySuggestion.waitFor({ state: 'visible', timeout: 15000 });
  }

  /**
   * Get auto-discovery suggestion
   */
  async getAutoDiscoverySuggestion(): Promise<{
    name: string;
    description: string;
    confidence: number;
  }> {
    const name = (await this.autoDiscoverySuggestionName.textContent()) || '';
    const description = (await this.autoDiscoverySuggestionDescription.textContent()) || '';
    const confidenceText = (await this.autoDiscoverySuggestionConfidence.textContent()) || '';
    const confidence = parseFloat(confidenceText.replace('%', '')) / 100;

    return { name: name.trim(), description: description.trim(), confidence };
  }

  /**
   * Open training data augmentation
   */
  async openAugmentation(): Promise<void> {
    await this.augmentationButton.click();
    await this.augmentationWizard.waitFor({ state: 'visible' });
  }

  /**
   * Set target count for augmentation
   */
  async setAugmentationTarget(count: number): Promise<void> {
    await this.augmentationTargetCount.fill(count.toString());
  }

  /**
   * Click generate button for augmentation
   */
  async clickAugmentationGenerate(): Promise<void> {
    await this.augmentationGenerateButton.click();
    await this.augmentationProgress.waitFor({ state: 'visible' });
  }

  /**
   * Check if domain exists in list
   */
  async domainExists(domainName: string): Promise<boolean> {
    return await this.domainRow(domainName).isVisible().catch(() => false);
  }

  /**
   * Click on a domain in the list
   */
  async clickDomain(domainName: string): Promise<void> {
    await this.domainRow(domainName).click();
    await this.domainDetail.waitFor({ state: 'visible' });
  }

  /**
   * Get error message text
   */
  async getErrorMessage(): Promise<string> {
    const text = await this.validationError.textContent();
    return text?.trim() || '';
  }

  /**
   * Check if wizard is visible
   */
  async isWizardVisible(): Promise<boolean> {
    return await this.newDomainWizard.isVisible();
  }
}
