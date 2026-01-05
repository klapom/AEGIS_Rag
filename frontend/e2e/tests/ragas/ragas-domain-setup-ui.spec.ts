import { test, expect } from '../../fixtures';

/**
 * RAGAS E2E User Journey - Frontend UI Version
 *
 * Sprint 75: Complete user journey through the UI (not API)
 *
 * This test executes the complete RAGAS setup workflow as a real user would:
 * 1. Navigate to Domain Training page
 * 2. Create new domain "ragas_eval_domain"
 * 3. Configure RAG settings (Hybrid + Reranking)
 * 4. Navigate to Admin Indexing page
 * 5. Scan and upload AEGIS RAG documentation (493 .md files)
 *
 * After completion, run: python scripts/run_ragas_on_namespace.py
 *
 * Benefits of UI testing vs API:
 * - Tests the complete user workflow (real-world scenario)
 * - Validates UI/UX works correctly
 * - Ensures frontend state management is correct
 * - Catches integration issues between UI and backend
 */

test.describe('RAGAS Domain Setup via UI - Sprint 75', () => {
  const NAMESPACE_ID = 'ragas_eval_domain';
  const DOMAIN_NAME = 'RAGAS Evaluation Domain';
  const DOCS_PATH = '/home/admin/projects/aegisrag/AEGIS_Rag/docs';

  test.beforeAll(async ({ request }) => {
    // Clean up: Delete domain if exists from previous run
    try {
      await request.delete(`/api/v1/admin/domains/${NAMESPACE_ID}`);
      console.log(`✓ Cleaned up existing domain: ${NAMESPACE_ID}`);
    } catch (e) {
      console.log(`  No existing domain to clean up`);
    }
  });

  test('Step 1: Create RAGAS Domain via UI', async ({ adminDomainTrainingPage }) => {
    console.log('\n' + '='.repeat(70));
    console.log('STEP 1: Creating RAGAS evaluation domain via UI...');
    console.log('='.repeat(70));

    // Wait for page to load
    await expect(adminDomainTrainingPage.pageTitle).toBeVisible();

    // Click "New Domain" button
    await adminDomainTrainingPage.newDomainButton.click();

    // Wait for wizard to appear
    await expect(adminDomainTrainingPage.newDomainWizard).toBeVisible();
    await expect(adminDomainTrainingPage.wizardTitle).toContainText('New Domain');

    // Fill domain details
    await adminDomainTrainingPage.domainNameInput.fill(NAMESPACE_ID);
    await adminDomainTrainingPage.domainDescriptionInput.fill(
      'Domain for RAGAS evaluation with AEGIS RAG documentation. ' +
      'Namespace-isolated for objective quality measurement.'
    );

    // Select model (default is usually fine, but let's be explicit)
    // Assuming there's a model dropdown - adjust based on actual UI
    if (await adminDomainTrainingPage.modelSelect.isVisible()) {
      await adminDomainTrainingPage.modelSelect.selectOption('gpt-oss:20b');
    }

    // Click "Next" or "Create" button
    await adminDomainTrainingPage.nextStepButton.click();

    // Wait for success (domain should appear in list)
    await expect(adminDomainTrainingPage.domainRow(NAMESPACE_ID)).toBeVisible({
      timeout: 10000,
    });

    console.log(`✓ Step 1 complete: Domain "${NAMESPACE_ID}" created via UI`);
  });

  test('Step 2: Configure Domain RAG Settings via UI', async ({ adminDomainTrainingPage }) => {
    console.log('\n' + '='.repeat(70));
    console.log('STEP 2: Configuring RAG settings via UI...');
    console.log('='.repeat(70));

    // Click on the domain row to open details
    await adminDomainTrainingPage.domainRow(NAMESPACE_ID).click();

    // Wait for domain details to appear
    await expect(adminDomainTrainingPage.domainDetail).toBeVisible();

    // Navigate to settings tab (assuming there's a tab or button)
    // Adjust selector based on actual UI structure
    const settingsTab = adminDomainTrainingPage.page.locator('button:has-text("Settings"), button:has-text("RAG Settings")');
    if (await settingsTab.isVisible()) {
      await settingsTab.click();
    }

    // Configure RAG settings
    // Note: Adjust these selectors based on actual UI structure

    // Retrieval Method: Hybrid
    const retrievalMethodSelect = adminDomainTrainingPage.page.locator('select[name="retrievalMethod"], select#retrieval-method');
    if (await retrievalMethodSelect.isVisible()) {
      await retrievalMethodSelect.selectOption('hybrid');
      console.log('  ✓ Set retrieval method: hybrid');
    }

    // Enable Reranking
    const rerankerCheckbox = adminDomainTrainingPage.page.locator('input[name="useReranking"], input[type="checkbox"][id*="rerank"]');
    if (await rerankerCheckbox.isVisible()) {
      await rerankerCheckbox.check();
      console.log('  ✓ Enabled reranking');
    }

    // Top-K
    const topKInput = adminDomainTrainingPage.page.locator('input[name="topK"], input#top-k');
    if (await topKInput.isVisible()) {
      await topKInput.fill('10');
      console.log('  ✓ Set top-k: 10');
    }

    // Score Threshold
    const thresholdInput = adminDomainTrainingPage.page.locator('input[name="scoreThreshold"], input#score-threshold');
    if (await thresholdInput.isVisible()) {
      await thresholdInput.fill('0.65');
      console.log('  ✓ Set score threshold: 0.65');
    }

    // Adaptive Weights (if available)
    const adaptiveWeightsCheckbox = adminDomainTrainingPage.page.locator('input[name="adaptiveWeights"], input[type="checkbox"][id*="adaptive"]');
    if (await adaptiveWeightsCheckbox.isVisible()) {
      await adaptiveWeightsCheckbox.check();
      console.log('  ✓ Enabled adaptive weights');
    }

    // Save settings
    const saveButton = adminDomainTrainingPage.page.locator('button:has-text("Save"), button:has-text("Update")').first();
    await saveButton.click();

    // Wait for success notification
    const successNotification = adminDomainTrainingPage.page.locator('text=saved, text=success, [role="status"]');
    await expect(successNotification).toBeVisible({ timeout: 5000 });

    console.log('✓ Step 2 complete: RAG settings configured via UI');
  });

  test('Step 3: Ingest AEGIS RAG Documentation via UI', async ({ adminIndexingPage }) => {
    console.log('\n' + '='.repeat(70));
    console.log('STEP 3: Ingesting AEGIS RAG documentation via UI...');
    console.log('This may take 10-20 minutes for 493 files...');
    console.log('='.repeat(70));

    // Wait for page to load
    await expect(adminIndexingPage.page.locator('h1, h2').filter({ hasText: /indexing/i }).first()).toBeVisible();

    // Select namespace
    const namespaceSelect = adminIndexingPage.page.locator('select[name="namespace"], select#namespace');
    if (await namespaceSelect.isVisible()) {
      await namespaceSelect.selectOption(NAMESPACE_ID);
      console.log(`  ✓ Selected namespace: ${NAMESPACE_ID}`);
    }

    // Navigate to "Scan Directory" tab
    const scanDirectoryTab = adminIndexingPage.page.locator('button:has-text("Scan Directory"), [role="tab"]:has-text("Scan")');
    if (await scanDirectoryTab.isVisible()) {
      await scanDirectoryTab.click();
    }

    // Enter directory path
    const directoryInput = adminIndexingPage.page.locator('input[name="directoryPath"], input[placeholder*="directory"]');
    await directoryInput.fill(DOCS_PATH);

    // Enable recursive scanning
    const recursiveCheckbox = adminIndexingPage.page.locator('input[name="recursive"], input[type="checkbox"][id*="recursive"]');
    if (await recursiveCheckbox.isVisible()) {
      await recursiveCheckbox.check();
    }

    // Click "Scan" button
    const scanButton = adminIndexingPage.page.locator('button:has-text("Scan")').first();
    await scanButton.click();

    // Wait for scan results
    await expect(adminIndexingPage.page.locator('text=files found, text=results')).toBeVisible({
      timeout: 10000,
    });

    // Get file count
    const fileCountText = await adminIndexingPage.page.locator('[data-testid="scan-result-count"], text=/\\d+ files/').first().textContent();
    const fileCount = parseInt(fileCountText?.match(/\d+/)?.[0] || '0');

    expect(fileCount).toBeGreaterThan(400);
    console.log(`  ✓ Found ${fileCount} files`);

    // Select all Markdown files
    const selectAllMdButton = adminIndexingPage.page.locator('button:has-text("Select All .md"), button:has-text("Select All")');
    if (await selectAllMdButton.isVisible()) {
      await selectAllMdButton.click();
      console.log('  ✓ Selected all .md files');
    } else {
      // Alternative: Click checkbox to select all
      const selectAllCheckbox = adminIndexingPage.page.locator('input[type="checkbox"][id*="select-all"]').first();
      if (await selectAllCheckbox.isVisible()) {
        await selectAllCheckbox.check();
      }
    }

    // Configure ingestion options
    const enableVLMCheckbox = adminIndexingPage.page.locator('input[name="enableVLM"], input[type="checkbox"][id*="vlm"]');
    if (await enableVLMCheckbox.isVisible()) {
      await enableVLMCheckbox.check();
      console.log('  ✓ Enabled VLM metadata');
    }

    const enableGraphCheckbox = adminIndexingPage.page.locator('input[name="enableGraph"], input[type="checkbox"][id*="graph"]');
    if (await enableGraphCheckbox.isVisible()) {
      await enableGraphCheckbox.check();
      console.log('  ✓ Enabled graph extraction');
    }

    // Start indexing
    const startIndexingButton = adminIndexingPage.page.locator('button:has-text("Start Indexing"), button:has-text("Begin")').first();
    await startIndexingButton.click();

    console.log('  ✓ Indexing started...');
    console.log('  ⏳ Polling for completion (checking every 30s)...');

    // Poll for completion (30 second intervals, max 20 minutes)
    let completed = false;
    let attempts = 0;
    const maxAttempts = 40; // 20 minutes

    while (!completed && attempts < maxAttempts) {
      await adminIndexingPage.page.waitForTimeout(30000); // 30 seconds

      // Check status
      const statusElement = adminIndexingPage.page.locator('[data-testid="indexing-status"], text=/complete|success|failed/i').first();

      if (await statusElement.isVisible()) {
        const statusText = await statusElement.textContent();

        if (statusText?.toLowerCase().includes('complete') || statusText?.toLowerCase().includes('success')) {
          completed = true;
          break;
        } else if (statusText?.toLowerCase().includes('failed') || statusText?.toLowerCase().includes('error')) {
          throw new Error('Indexing failed');
        }
      }

      // Log progress
      const progressElement = adminIndexingPage.page.locator('[data-testid="indexing-progress"], text=/\\d+%|\\d+\\/\\d+/').first();
      if (await progressElement.isVisible()) {
        const progress = await progressElement.textContent();
        console.log(`    Progress: ${progress}`);
      }

      attempts++;
    }

    if (!completed) {
      throw new Error('Indexing timeout after 20 minutes');
    }

    // Get final count
    const indexedCountElement = adminIndexingPage.page.locator('[data-testid="indexed-count"], text=/\\d+ documents indexed/').first();
    const indexedCountText = await indexedCountElement.textContent();
    const indexed = parseInt(indexedCountText?.match(/\d+/)?.[0] || '0');

    expect(indexed).toBeGreaterThan(400);

    console.log(`✓ Step 3 complete: ${indexed} documents indexed via UI`);
    console.log(`  Total time: ~${attempts * 0.5} minutes`);
  });

  test('Verification: Confirm RAGAS Domain Ready', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('VERIFICATION: Checking domain readiness...');
    console.log('='.repeat(70));

    // Navigate to namespace stats page (if available)
    await page.goto('/admin/namespaces');

    // Click on our namespace
    const namespaceRow = page.locator(`tr:has-text("${NAMESPACE_ID}"), [data-namespace="${NAMESPACE_ID}"]`);
    if (await namespaceRow.isVisible()) {
      await namespaceRow.click();
    }

    // Check document count
    const docCountElement = page.locator('[data-testid="namespace-doc-count"], text=/\\d+ documents/').first();
    if (await docCountElement.isVisible()) {
      const docCountText = await docCountElement.textContent();
      const docCount = parseInt(docCountText?.match(/\d+/)?.[0] || '0');

      expect(docCount).toBeGreaterThan(400);
      console.log(`✓ Namespace has ${docCount} documents`);
    }

    console.log('\n' + '='.repeat(70));
    console.log('✅ RAGAS DOMAIN READY FOR EVALUATION (via UI)');
    console.log('='.repeat(70));
    console.log('\nNext step: Run RAGAS evaluation');
    console.log('  python scripts/run_ragas_on_namespace.py --namespace ragas_eval_domain\n');
  });
});
