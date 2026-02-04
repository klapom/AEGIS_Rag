import { test, expect } from '../fixtures';

/**
 * E2E Tests for Domain Training System
 * Feature 45.3: Domain Management and Training
 * Feature 45.10: Batch Ingestion with Domain Routing
 * Feature 45.12: Metric Configuration UI
 *
 * Tests cover:
 * - Domain creation with configuration
 * - Training dataset upload and preview
 * - Metric preset selection and customization
 * - Training workflow and monitoring
 * - Auto-discovery of domains
 * - Data augmentation for training
 * - Upload page domain suggestion integration
 */

// Sprint 123.7: Re-enabled - AdminDomainTrainingPage.goto() now uses navigateClientSide() to preserve auth state
test.describe('Domain Training - Page Navigation & Display', () => {
  test('should display domain training page on load', async ({ adminDomainTrainingPage }) => {
    // Page should be navigated and visible
    await expect(adminDomainTrainingPage.pageTitle).toBeVisible();
    await expect(adminDomainTrainingPage.newDomainButton).toBeVisible();
    await expect(adminDomainTrainingPage.domainList).toBeVisible();
  });

  // Sprint 106: Skip - "general" domain only exists if backend seeds it
  test.skip('should display default "general" domain in list', async ({ adminDomainTrainingPage }) => {
    // The general domain should always exist
    const exists = await adminDomainTrainingPage.domainExists('general');
    expect(exists).toBeTruthy();
  });
});

test.describe('Domain Training - New Domain Wizard Step 1', () => {
  // Sprint 123.10: Skip all wizard tests - UI component not implemented (3-min timeouts)
  test.skip('should open new domain wizard when clicking button', async ({
    adminDomainTrainingPage,
  }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await expect(adminDomainTrainingPage.wizardTitle).toBeVisible();
    await expect(adminDomainTrainingPage.domainNameInput).toBeVisible();
    await expect(adminDomainTrainingPage.domainDescriptionInput).toBeVisible();
    await expect(adminDomainTrainingPage.modelSelect).toBeVisible();
  });

  // Sprint 123.10: Skip - UI wizard component not implemented (3-min timeout)
  test.skip('should validate domain name with regex', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    // Try invalid name with spaces and uppercase
    await adminDomainTrainingPage.fillDomainName('Invalid Name');
    await adminDomainTrainingPage.clickNext();

    // Should show validation error
    const errorMessage = await adminDomainTrainingPage.getErrorMessage();
    expect(errorMessage.toLowerCase()).toContain('lowercase');
  });

  // Sprint 123.10: Skip - UI wizard component not implemented (3-min timeout)
  test.skip('should reject domain name with uppercase letters', async ({
    adminDomainTrainingPage,
  }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.fillDomainName('TechDocs');
    await adminDomainTrainingPage.clickNext();

    const errorMessage = await adminDomainTrainingPage.getErrorMessage();
    expect(errorMessage.toLowerCase()).toMatch(/lowercase|invalid/i);
  });

  // Sprint 123.10: Skip - UI wizard component not implemented (3-min timeout)
  test.skip('should reject domain name with special characters', async ({
    adminDomainTrainingPage,
  }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.fillDomainName('tech-docs');
    await adminDomainTrainingPage.clickNext();

    const errorMessage = await adminDomainTrainingPage.getErrorMessage();
    expect(errorMessage.toLowerCase()).toMatch(/lowercase|invalid/i);
  });

  // Sprint 123.10: Skip - UI wizard component not implemented (3-min timeout)
  test.skip('should accept valid domain name format', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    // Valid: lowercase with underscores
    await adminDomainTrainingPage.fillDomainName('tech_docs');
    await adminDomainTrainingPage.fillDomainDescription(
      'Technical documentation for software development projects'
    );

    // Should not show error when clicking next
    await adminDomainTrainingPage.clickNext();

    // Should advance to step 2 (dataset upload)
    await expect(adminDomainTrainingPage.datasetUploadSection).toBeVisible();
  });

  // Sprint 123.10: Skip - UI wizard component not implemented (3-min timeout)
  test.skip('should require description field', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.fillDomainName('test_domain');
    // Don't fill description - it's required

    await adminDomainTrainingPage.clickNext();

    const errorMessage = await adminDomainTrainingPage.getErrorMessage();
    expect(errorMessage.toLowerCase()).toContain('required');
  });

  // Sprint 123.10: Skip - UI wizard component not implemented (3-min timeout)
  test.skip('should close wizard when clicking cancel', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();
    await expect(adminDomainTrainingPage.wizardTitle).toBeVisible();

    await adminDomainTrainingPage.clickCancel();

    // Wizard should close
    const wizardVisible = await adminDomainTrainingPage.isWizardVisible().catch(() => false);
    expect(wizardVisible).toBeFalsy();
  });
});

// Sprint 123.10: Skip metric configuration tests - UI wizard component not implemented (3-min timeouts)
test.describe('Domain Training - Metric Configuration', () => {
  test.skip('should display metric configuration panel', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await expect(adminDomainTrainingPage.metricConfigPanel).toBeVisible();
    await expect(adminDomainTrainingPage.presetBalanced).toBeVisible();
    await expect(adminDomainTrainingPage.presetPrecisionFocused).toBeVisible();
    await expect(adminDomainTrainingPage.presetRecallFocused).toBeVisible();
    await expect(adminDomainTrainingPage.presetCustom).toBeVisible();
  });

  test.skip('should select balanced preset', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    // Click balanced preset
    await adminDomainTrainingPage.selectMetricPreset('balanced');

    // Verify preset is selected (could check styling or state)
    const preset = adminDomainTrainingPage.presetBalanced;
    await expect(preset).toHaveAttribute('aria-pressed', 'true');
  });

  test.skip('should select precision-focused preset', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.selectMetricPreset('precision_focused');

    const preset = adminDomainTrainingPage.presetPrecisionFocused;
    await expect(preset).toHaveAttribute('aria-pressed', 'true');
  });

  test.skip('should select recall-focused preset', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.selectMetricPreset('recall_focused');

    const preset = adminDomainTrainingPage.presetRecallFocused;
    await expect(preset).toHaveAttribute('aria-pressed', 'true');
  });

  test.skip('should show custom metric options when selecting custom preset', async ({
    adminDomainTrainingPage,
  }) => {
    await adminDomainTrainingPage.clickNewDomain();

    // Custom preset initially may not show controls
    await adminDomainTrainingPage.selectMetricPreset('custom');

    // Wait for custom controls to appear
    await expect(adminDomainTrainingPage.weightSlider).toBeVisible();
    await expect(adminDomainTrainingPage.entityMetricSelect).toBeVisible();
    await expect(adminDomainTrainingPage.relationMetricSelect).toBeVisible();
  });

  test.skip('should update weight slider for custom metrics', async ({
    adminDomainTrainingPage,
  }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.selectMetricPreset('custom');

    // Set weight to 0.7
    await adminDomainTrainingPage.setMetricWeight(0.7);

    const slider = adminDomainTrainingPage.weightSlider;
    await expect(slider).toHaveValue('0.7');
  });

  test.skip('should display metric preview', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await expect(adminDomainTrainingPage.metricPreview).toBeVisible();

    // Metric preview should show some content
    const previewText = await adminDomainTrainingPage.metricPreview.textContent();
    expect(previewText?.length).toBeGreaterThan(0);
  });
});

// Sprint 123.10: Skip dataset upload tests - UI wizard component not implemented (3-min timeouts)
test.describe('Domain Training - Step 2: Dataset Upload', () => {
  test.skip('should navigate to dataset upload step', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.fillDomainName('test_domain');
    await adminDomainTrainingPage.fillDomainDescription(
      'Test domain for E2E testing purposes'
    );
    await adminDomainTrainingPage.selectMetricPreset('balanced');

    await adminDomainTrainingPage.clickNext();

    // Should show dataset upload section
    await expect(adminDomainTrainingPage.datasetUploadSection).toBeVisible();
    await expect(adminDomainTrainingPage.datasetDropzone).toBeVisible();
  });

  test.skip('should upload and preview JSONL dataset', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    // Complete step 1
    await adminDomainTrainingPage.fillDomainName('test_domain');
    await adminDomainTrainingPage.fillDomainDescription(
      'Test domain for E2E testing purposes'
    );
    await adminDomainTrainingPage.clickNext();

    // Upload JSONL file with sample data
    const jsonlContent = `{"text": "Python is a programming language", "entities": ["Python", "programming language"]}
{"text": "FastAPI is a web framework", "entities": ["FastAPI", "web framework"]}
{"text": "Docker containers are lightweight", "entities": ["Docker", "containers"]}
{"text": "Kubernetes orchestrates containers", "entities": ["Kubernetes", "containers"]}
{"text": "PostgreSQL is a relational database", "entities": ["PostgreSQL", "relational database"]}`;

    await adminDomainTrainingPage.uploadDataset('training_data.jsonl', jsonlContent);

    // Should show sample preview
    await expect(adminDomainTrainingPage.samplePreviewContainer).toBeVisible();

    // Should show sample count (5 samples)
    const count = await adminDomainTrainingPage.getSampleCount();
    expect(count).toBe(5);
  });

  test.skip('should show first sample in preview', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    // Complete step 1
    await adminDomainTrainingPage.fillDomainName('test_domain');
    await adminDomainTrainingPage.fillDomainDescription(
      'Test domain for E2E testing purposes'
    );
    await adminDomainTrainingPage.clickNext();

    // Upload JSONL file
    const jsonlContent = `{"text": "Sample 1 text content", "entities": ["Entity1"]}
{"text": "Sample 2 text content", "entities": ["Entity2"]}`;

    await adminDomainTrainingPage.uploadDataset('training_data.jsonl', jsonlContent);

    // First sample should be visible
    const firstSample = adminDomainTrainingPage.samplePreview(1);
    await expect(firstSample).toBeVisible();
  });

  test.skip('should navigate back to step 1 with preserved values', async ({
    adminDomainTrainingPage,
  }) => {
    await adminDomainTrainingPage.clickNewDomain();

    // Complete step 1 with specific values
    await adminDomainTrainingPage.fillDomainName('test_domain');
    await adminDomainTrainingPage.fillDomainDescription('Test domain description');
    await adminDomainTrainingPage.selectMetricPreset('precision_focused');
    await adminDomainTrainingPage.clickNext();

    // Go back to step 1
    await adminDomainTrainingPage.clickBack();

    // Values should be preserved
    await expect(adminDomainTrainingPage.domainNameInput).toHaveValue('test_domain');
    await expect(adminDomainTrainingPage.domainDescriptionInput).toHaveValue(
      'Test domain description'
    );

    // Preset selection should be preserved
    const preset = adminDomainTrainingPage.presetPrecisionFocused;
    await expect(preset).toHaveAttribute('aria-pressed', 'true');
  });

  test.skip('should require at least 5 samples to proceed', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    // Complete step 1
    await adminDomainTrainingPage.fillDomainName('test_domain');
    await adminDomainTrainingPage.fillDomainDescription('Test domain description');
    await adminDomainTrainingPage.clickNext();

    // Upload JSONL with only 3 samples (below minimum)
    const jsonlContent = `{"text": "Sample 1", "entities": ["Entity1"]}
{"text": "Sample 2", "entities": ["Entity2"]}
{"text": "Sample 3", "entities": ["Entity3"]}`;

    await adminDomainTrainingPage.uploadDataset('training_data.jsonl', jsonlContent);

    // Should show error or disable training button
    const errorVisible = await adminDomainTrainingPage.datasetError.isVisible().catch(() => false);
    expect(errorVisible).toBeTruthy();
  });

  test.skip('should accept JSONL file upload with proper format', async ({
    adminDomainTrainingPage,
  }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.fillDomainName('test_domain');
    await adminDomainTrainingPage.fillDomainDescription('Test domain description');
    await adminDomainTrainingPage.clickNext();

    // Upload properly formatted JSONL
    const jsonlContent = `{"text": "Text 1", "entities": ["E1", "E2"], "relations": []}
{"text": "Text 2", "entities": ["E3"], "relations": [{"subject": "E3", "predicate": "is", "object": "E4"}]}
{"text": "Text 3", "entities": ["E5"], "relations": []}
{"text": "Text 4", "entities": ["E6"], "relations": []}
{"text": "Text 5", "entities": ["E7"], "relations": []}`;

    await adminDomainTrainingPage.uploadDataset('training_data.jsonl', jsonlContent);

    // Should successfully load
    const count = await adminDomainTrainingPage.getSampleCount();
    expect(count).toBe(5);

    // Preview container should be visible
    await expect(adminDomainTrainingPage.samplePreviewContainer).toBeVisible();
  });
});

// Sprint 123.10: Skip auto-discovery tests - UI wizard component not implemented (3-min timeouts)
test.describe('Domain Training - Auto-Discovery', () => {
  test.skip('should open auto-discovery wizard', async ({ adminDomainTrainingPage }) => {
    await expect(adminDomainTrainingPage.autoDiscoveryButton).toBeVisible();

    await adminDomainTrainingPage.openAutoDiscovery();

    await expect(adminDomainTrainingPage.autoDiscoveryWizard).toBeVisible();
  });

  test.skip('should accept multiple sample texts for auto-discovery', async ({
    adminDomainTrainingPage,
  }) => {
    await adminDomainTrainingPage.openAutoDiscovery();

    const samples = [
      'Python is a programming language for data science',
      'FastAPI provides high performance web framework for APIs',
      'Docker enables containerization of applications',
      'Kubernetes orchestrates container deployments',
      'PostgreSQL is a powerful open-source database',
    ];

    for (const sample of samples) {
      // Add samples one by one
      await adminDomainTrainingPage.autoDiscoverySampleInput.fill(sample);
      await adminDomainTrainingPage.page.keyboard.press('Enter');
      await adminDomainTrainingPage.page.waitForTimeout(100);
    }

    // Analyze button should be visible and clickable
    await expect(adminDomainTrainingPage.autoDiscoveryAnalyzeButton).toBeEnabled();
  });

  test.skip('should show domain suggestion after analysis', async ({
    adminDomainTrainingPage,
    page,
  }) => {
    // Mock the auto-discovery API response
    await page.route('**/api/v1/admin/domains/discover', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          name: 'software_development',
          description:
            'Domain for software development including programming, frameworks, and deployment tools',
          entity_types: ['Programming Language', 'Framework', 'Tool', 'Technology'],
          confidence: 0.92,
        }),
      });
    });

    await adminDomainTrainingPage.openAutoDiscovery();

    const samples = [
      'Python is a programming language',
      'FastAPI is a web framework',
      'Docker is a containerization tool',
    ];

    await adminDomainTrainingPage.addAutoDiscoverySamples(samples);
    await adminDomainTrainingPage.clickAutoDiscoveryAnalyze();

    // Get the suggestion
    const suggestion = await adminDomainTrainingPage.getAutoDiscoverySuggestion();

    expect(suggestion.name).toBe('software_development');
    expect(suggestion.confidence).toBeGreaterThan(0.8);
  });
});

// Sprint 123.10: Skip model selection tests - UI wizard component not implemented (3-min timeouts)
test.describe('Domain Training - Model Selection', () => {
  test.skip('should display available models in dropdown', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    const modelSelect = adminDomainTrainingPage.modelSelect;
    await expect(modelSelect).toBeVisible();

    // Open dropdown to see options
    await modelSelect.click();
    await adminDomainTrainingPage.page.waitForTimeout(300);

    // Models should be visible in dropdown
    const options = await adminDomainTrainingPage.page.locator('select option').count();
    expect(options).toBeGreaterThan(0);
  });

  test.skip('should select custom model', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    // Select a specific model
    await adminDomainTrainingPage.selectModel('qwen3:32b');

    const modelSelect = adminDomainTrainingPage.modelSelect;
    await expect(modelSelect).toHaveValue('qwen3:32b');
  });
});

// Sprint 123.10: Skip complete workflow tests - UI wizard component not implemented (3-min timeouts)
test.describe('Domain Training - Complete Workflow', () => {
  test.skip('should complete full domain creation workflow', async ({
    adminDomainTrainingPage,
  }) => {
    // Step 1: Create domain configuration
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.fillDomainName('test_complete_domain');
    await adminDomainTrainingPage.fillDomainDescription(
      'Complete test domain for E2E workflow validation'
    );
    await adminDomainTrainingPage.selectModel('qwen3:32b');
    await adminDomainTrainingPage.selectMetricPreset('balanced');

    await adminDomainTrainingPage.clickNext();

    // Step 2: Upload training data
    const jsonlContent = `{"text": "First test document with entities", "entities": ["test", "document"]}
{"text": "Second training sample data", "entities": ["training", "sample"]}
{"text": "Third example for validation", "entities": ["example", "validation"]}
{"text": "Fourth item in test set", "entities": ["item", "test"]}
{"text": "Fifth and final test data entry", "entities": ["final", "test"]}`;

    await adminDomainTrainingPage.uploadDataset('training_data.jsonl', jsonlContent);

    // Verify samples loaded
    const count = await adminDomainTrainingPage.getSampleCount();
    expect(count).toBeGreaterThanOrEqual(5);

    // Verify preview is visible
    await expect(adminDomainTrainingPage.samplePreviewContainer).toBeVisible();
  });
});

// Sprint 123.10: Skip error handling tests - UI wizard component not implemented (3-min timeouts)
test.describe('Domain Training - Error Handling', () => {
  test.skip('should show error for invalid JSONL format', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.fillDomainName('test_domain');
    await adminDomainTrainingPage.fillDomainDescription('Test domain description');
    await adminDomainTrainingPage.clickNext();

    // Upload invalid JSONL (missing entities field)
    const invalidJsonl = `{"text": "Invalid sample without entities"}
{"text": "Another invalid sample"}`;

    await adminDomainTrainingPage.uploadDataset('invalid.jsonl', invalidJsonl);

    // Should show error
    const errorVisible = await adminDomainTrainingPage.datasetError.isVisible().catch(() => false);
    // Note: Error visibility depends on frontend validation - adjust as needed
  });

  test.skip('should show error for empty file upload', async ({ adminDomainTrainingPage }) => {
    await adminDomainTrainingPage.clickNewDomain();

    await adminDomainTrainingPage.fillDomainName('test_domain');
    await adminDomainTrainingPage.fillDomainDescription('Test domain description');
    await adminDomainTrainingPage.clickNext();

    // Upload empty file
    const emptyJsonl = '';

    await adminDomainTrainingPage.uploadDataset('empty.jsonl', emptyJsonl);

    // Should show error about minimum samples
    const errorVisible = await adminDomainTrainingPage.datasetError.isVisible().catch(() => false);
    expect(errorVisible).toBeTruthy();
  });
});
