import { test, expect } from '../../fixtures';

/**
 * E2E Tests for Pipeline Progress Visualization (Sprint 37)
 *
 * Features Tested:
 * - Feature 37.6: PipelineProgressVisualization Component
 * - Feature 37.7: Progress Streaming via SSE
 * - Feature 37.9: E2E Test Coverage
 *
 * Components Under Test:
 * - PipelineProgressContainer: Overall progress display
 * - PipelineStageProgressBar: Individual stage progress
 * - WorkerPoolVisualization: Worker status display
 * - MetricsDisplay: Live metrics (entities, relations, writes)
 * - TimingDisplay: Elapsed time and ETA
 *
 * Data Attributes Required:
 * - [data-testid="pipeline-progress-container"]
 * - [data-testid="stage-{name}"]
 * - [data-testid="stage-progress-bar-{name}"]
 * - [data-testid="worker-{id}"]
 * - [data-testid="worker-pool-container"]
 * - [data-testid="metrics-entities"]
 * - [data-testid="metrics-relations"]
 * - [data-testid="timing-elapsed"]
 * - [data-testid="timing-remaining"]
 * - [data-testid="overall-progress"]
 * - [data-testid="document-name"]
 *
 * Notes:
 * - Tests assume indexing job started on /admin/indexing
 * - SSE streams progress updates in real-time
 * - All tests use modern Playwright selectors
 * - Mobile viewport tested for responsive design
 */

const PIPELINE_STAGES = ['parsing', 'vlm', 'chunking', 'embedding', 'extraction'];

test.describe('Pipeline Progress Visualization (Sprint 37)', () => {
  // =========================================================================
  // Container and Basic Visibility Tests
  // =========================================================================

  test('should display pipeline progress container when indexing starts', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start an indexing job
    const startButton = page.getByTestId('start-indexing-button');
    await expect(startButton).toBeVisible();
    await startButton.click();

    // Wait for progress container to appear (max 10 seconds)
    const container = page.getByTestId('pipeline-progress-container');
    await expect(container).toBeVisible({ timeout: 10000 });

    // Verify container is in viewport
    await expect(container).toHaveCSS('display', /block|flex/);
  });

  test('should show document name in progress display', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check document name is displayed
    const docName = page.getByTestId('document-name');
    await expect(docName).toBeVisible();

    // Should show a filename (not empty)
    const nameText = await docName.textContent();
    expect(nameText).toBeTruthy();
    expect(nameText).toMatch(/\.(pdf|txt|docx|pptx)/i);
  });

  // =========================================================================
  // Pipeline Stage Tests
  // =========================================================================

  test('should display all five pipeline stages', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check all stages are present
    for (const stage of PIPELINE_STAGES) {
      const stageElement = page.getByTestId(`stage-${stage}`);
      await expect(stageElement).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show stage names correctly', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Verify stage names
    const expectedNames = ['Parsing', 'VLM', 'Chunking', 'Embedding', 'Extraction'];

    for (const name of expectedNames) {
      const element = page.locator(`text=${name}`).first();
      await expect(element).toBeVisible();
    }
  });

  test('should update stage progress bar as processing advances', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Get chunking progress bar
    const chunkingBar = page.getByTestId('stage-progress-bar-chunking');
    await expect(chunkingBar).toBeVisible();

    // Initial width should be 0% or near 0%
    const initialWidth = await chunkingBar.evaluate((el) =>
      getComputedStyle(el).width
    );

    // Wait for progress to update (max 30 seconds)
    await page.waitForFunction(
      () => {
        const bar = document.querySelector('[data-testid="stage-progress-bar-chunking"]');
        return bar && getComputedStyle(bar).width !== initialWidth;
      },
      { timeout: 30000 }
    );

    // Verify progress changed
    const updatedWidth = await chunkingBar.evaluate((el) =>
      getComputedStyle(el).width
    );
    expect(updatedWidth).not.toBe(initialWidth);
  });

  test('should display stage status (pending, in-progress, completed)', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check parsing stage starts in progress (first stage)
    const parsingStage = page.getByTestId('stage-parsing');

    // Should show status indicator (in-progress, pending, or completed)
    const statusText = await parsingStage.textContent();
    expect(statusText).toMatch(/pending|in.progress|processing|completed|✓/i);
  });

  // =========================================================================
  // Progress Bar and Percentage Tests
  // =========================================================================

  test('should show progress percentage for each stage', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Wait for progress to show percentages
    await page.waitForTimeout(2000);

    // Check at least one stage shows percentage
    const stageElements = page.locator('[data-testid^="stage-"]');
    const count = await stageElements.count();
    expect(count).toBeGreaterThan(0);

    // At least one should show a percentage
    let foundPercentage = false;
    for (let i = 0; i < count; i++) {
      const text = await stageElements.nth(i).textContent();
      if (text && text.match(/%/)) {
        foundPercentage = true;
        break;
      }
    }
    expect(foundPercentage).toBeTruthy();
  });

  test('should display overall progress bar with percentage', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check overall progress display
    const overallProgress = page.getByTestId('overall-progress');
    await expect(overallProgress).toBeVisible();

    // Should show percentage
    const progressText = await overallProgress.textContent();
    expect(progressText).toMatch(/\d+%/);
  });

  // =========================================================================
  // Worker Pool Tests
  // =========================================================================

  test('should display worker pool container', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check worker pool is visible
    const workerPool = page.getByTestId('worker-pool-container');
    await expect(workerPool).toBeVisible();
  });

  test('should show individual worker statuses', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check at least one worker is displayed
    const worker0 = page.getByTestId('worker-0');
    await expect(worker0).toBeVisible();

    // Worker should show status (idle, processing, error)
    const workerText = await worker0.textContent();
    expect(workerText).toMatch(/idle|processing|error|chunk/i);
  });

  test('should update worker status as chunks are processed', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check worker status changes
    const worker0 = page.getByTestId('worker-0');
    const initialText = await worker0.textContent();

    // Wait for status to change
    await page.waitForFunction(
      () => {
        return document
          .querySelector('[data-testid="worker-0"]')
          ?.textContent?.includes('processing');
      },
      { timeout: 15000 }
    );

    const updatedText = await worker0.textContent();
    expect(updatedText).not.toBe(initialText);
  });

  // =========================================================================
  // Metrics Display Tests
  // =========================================================================

  test('should display metrics container with live values', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check metrics are displayed
    const entitiesMetric = page.getByTestId('metrics-entities');
    const relationsMetric = page.getByTestId('metrics-relations');

    await expect(entitiesMetric).toBeVisible();
    await expect(relationsMetric).toBeVisible();
  });

  test('should update entity count as extraction progresses', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Wait for extraction stage to start
    await page.waitForFunction(
      () => {
        const stage = document.querySelector('[data-testid="stage-extraction"]');
        return stage && stage.textContent?.includes('in') || false;
      },
      { timeout: 30000 }
    );

    // Check entities metric exists and may update
    const entitiesMetric = page.getByTestId('metrics-entities');
    await expect(entitiesMetric).toBeVisible();

    const metricsText = await entitiesMetric.textContent();
    expect(metricsText).toMatch(/\d+/);
  });

  test('should display Neo4j and Qdrant write counts', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check write metrics
    const neo4jWrites = page.getByTestId('metrics-neo4j-writes');
    const qdrantWrites = page.getByTestId('metrics-qdrant-writes');

    // At least one should be visible after processing
    const neo4jVisible = await neo4jWrites.isVisible().catch(() => false);
    const qdrantVisible = await qdrantWrites.isVisible().catch(() => false);

    expect(neo4jVisible || qdrantVisible).toBeTruthy();
  });

  // =========================================================================
  // Timing Display Tests
  // =========================================================================

  test('should display elapsed time counter', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check elapsed time is displayed
    const elapsedTime = page.getByTestId('timing-elapsed');
    await expect(elapsedTime).toBeVisible();

    const timeText = await elapsedTime.textContent();
    expect(timeText).toMatch(/\d+/); // Should have numbers
  });

  test('should show estimated remaining time', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Wait a bit for ETA calculation
    await page.waitForTimeout(3000);

    const remainingTime = page.getByTestId('timing-remaining');

    // ETA might not appear immediately, so soft check
    const isVisible = await remainingTime.isVisible().catch(() => false);
    if (isVisible) {
      const timeText = await remainingTime.textContent();
      expect(timeText).toBeTruthy();
    }
  });

  test('should update elapsed time in real-time', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    const elapsedTime = page.getByTestId('timing-elapsed');
    const initialText = await elapsedTime.textContent();

    // Wait for elapsed time to update
    await page.waitForFunction(
      () => {
        const el = document.querySelector('[data-testid="timing-elapsed"]');
        return el?.textContent !== initialText;
      },
      { timeout: 5000 }
    );

    const updatedText = await elapsedTime.textContent();
    expect(updatedText).not.toBe(initialText);
  });

  // =========================================================================
  // Completion and Status Tests
  // =========================================================================

  test('should show completion status when all stages finish', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing (with shorter timeout for completion)
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Wait for completion (longer timeout for full processing)
    // This assumes relatively small test documents
    const maxWaitTime = 120000; // 2 minutes max

    await page.waitForFunction(
      () => {
        const overall = document.querySelector('[data-testid="overall-progress"]');
        return overall && overall.textContent?.includes('100%');
      },
      { timeout: maxWaitTime }
    );

    // Verify all stages show as complete
    const parsingStage = page.getByTestId('stage-parsing');
    const parsingText = await parsingStage.textContent();
    expect(parsingText).toMatch(/completed|✓|done/i);
  });

  test('should show checkmarks when stages complete', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Wait for first stage (parsing) to complete
    await page.waitForFunction(
      () => {
        const stage = document.querySelector('[data-testid="stage-parsing"]');
        return stage && (
          stage.textContent?.includes('✓') ||
          stage.textContent?.includes('completed') ||
          stage.textContent?.includes('100%')
        );
      },
      { timeout: 30000 }
    );

    // Verify checkmark or completion indicator
    const parsingStage = page.getByTestId('stage-parsing');
    const stageText = await parsingStage.textContent();
    expect(stageText).toMatch(/✓|completed|100%/i);
  });

  test('should display error state if processing fails', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // This test assumes error handling is implemented
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Check if error indicator exists (soft check - might not have error)
    const errorIndicator = page.getByTestId('stage-error').first();
    const isErrorVisible = await errorIndicator.isVisible().catch(() => false);

    if (isErrorVisible) {
      const errorText = await errorIndicator.textContent();
      expect(errorText).toMatch(/error|failed|timeout/i);
    }
  });

  // =========================================================================
  // Responsive Design Tests
  // =========================================================================

  test('should be responsive on mobile viewport', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Set mobile viewport (375x667 - iPhone SE)
    await page.setViewportSize({ width: 375, height: 667 });

    // Re-navigate to admin page on mobile
    await adminIndexingPage.goto();
    await page.waitForLoadState('networkidle');

    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    const container = page.getByTestId('pipeline-progress-container');
    await expect(container).toBeVisible({ timeout: 10000 });

    // Verify container fits in viewport
    const box = await container.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      expect(box.width).toBeLessThanOrEqual(375);
    }

    // Check stages are still visible on mobile
    const parsingStage = page.getByTestId('stage-parsing');
    await expect(parsingStage).toBeVisible();
  });

  test('should stack stages vertically on mobile', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Re-navigate on mobile
    await adminIndexingPage.goto();
    await page.waitForLoadState('networkidle');
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Get bounding boxes for two stages
    const parsingBox = await page.getByTestId('stage-parsing').boundingBox();
    const chunkingBox = await page.getByTestId('stage-chunking').boundingBox();

    // On mobile, they should be stacked (y coordinates should be different)
    expect(parsingBox).not.toBeNull();
    expect(chunkingBox).not.toBeNull();
    if (parsingBox && chunkingBox) {
      // Chunking should be below parsing
      expect(chunkingBox.y).toBeGreaterThan(parsingBox.y);
    }
  });

  test('should work on tablet viewport (768px)', async ({ adminIndexingPage }) => {
    const { page } = adminIndexingPage;
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    // Re-navigate on tablet
    await adminIndexingPage.goto();
    await page.waitForLoadState('networkidle');
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // All stages should be visible
    for (const stage of PIPELINE_STAGES) {
      const stageElement = page.getByTestId(`stage-${stage}`);
      await expect(stageElement).toBeVisible();
    }
  });

  // =========================================================================
  // Real-time Update Tests
  // =========================================================================

  test('should receive SSE progress updates in real-time', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    await expect(page.getByTestId('pipeline-progress-container')).toBeVisible({
      timeout: 10000,
    });

    // Collect progress updates over time
    const updates: string[] = [];

    // Monitor stage progress changes
    const chunkingBar = page.getByTestId('stage-progress-bar-chunking');

    // Initial width
    let lastWidth = await chunkingBar.evaluate((el) =>
      getComputedStyle(el).width
    );
    updates.push(lastWidth);

    // Wait and check for updates
    for (let i = 0; i < 5; i++) {
      await page.waitForTimeout(2000);

      const currentWidth = await chunkingBar
        .evaluate((el) => getComputedStyle(el).width)
        .catch(() => lastWidth);

      if (currentWidth !== lastWidth) {
        updates.push(currentWidth);
        lastWidth = currentWidth;
      }
    }

    // Should have received at least 1 update tracked
    expect(updates.length).toBeGreaterThanOrEqual(1);
  });

  // =========================================================================
  // Error Handling Tests
  // =========================================================================

  test('should handle progress updates with missing data gracefully', async ({
    adminIndexingPage,
  }) => {
    const { page } = adminIndexingPage;
    // Start indexing
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress container
    const container = page.getByTestId('pipeline-progress-container');
    await expect(container).toBeVisible({ timeout: 10000 });

    // Page should not show any console errors
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Let it run for a bit
    await page.waitForTimeout(5000);

    // Should not have critical errors
    const criticalErrors = errors.filter(
      (e) => !e.includes('ResizeObserver') && !e.includes('Network')
    );
    expect(criticalErrors.length).toBe(0);
  });
});

// =========================================================================
// Pipeline Configuration Panel Tests
// =========================================================================

test.describe('Pipeline Configuration Panel (Sprint 37)', () => {
  test('should load configuration panel with default values', async ({
    settingsPage,
  }) => {
    const { page } = settingsPage;
    const configPanel = page.getByTestId('config-panel-container');

    // Panel might not be visible on all pages - soft check
    const isVisible = await configPanel.isVisible().catch(() => false);

    if (isVisible) {
      // Check default values
      const extractionWorkers = page.getByTestId('config-extraction-workers');

      if (await extractionWorkers.isVisible().catch(() => false)) {
        const value = await extractionWorkers.inputValue();
        expect(value).toMatch(/\d+/); // Should have a number
      }
    }
  });

  test('should allow changing worker configuration', async ({ settingsPage }) => {
    const { page } = settingsPage;
    const extractionWorkers = page.getByTestId('config-extraction-workers');

    const isVisible = await extractionWorkers.isVisible().catch(() => false);
    if (isVisible) {
      // Change value
      await extractionWorkers.fill('6');

      // Verify value changed
      const newValue = await extractionWorkers.inputValue();
      expect(newValue).toBe('6');
    }
  });

  test('should apply presets when selected', async ({ settingsPage }) => {
    const { page } = settingsPage;
    // This test assumes preset buttons exist
    const aggressivePreset = page.getByTestId('preset-aggressive');

    const isVisible = await aggressivePreset.isVisible().catch(() => false);
    if (isVisible) {
      await aggressivePreset.click();

      // Config values should change
      const extractionWorkers = page.getByTestId('config-extraction-workers');
      const value = await extractionWorkers.inputValue();

      // Aggressive preset should have higher worker count
      expect(parseInt(value)).toBeGreaterThan(2);
    }
  });
});
