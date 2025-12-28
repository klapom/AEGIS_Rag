/**
 * E2E Test: Single Document Upload & Content Verification
 *
 * Test Document: D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf
 * Purpose: Verify complete ingestion pipeline and retrieval quality
 * Coverage: Vector Search (BGE-M3) + BM25 Search + Graph Reasoning
 *
 * Sprint 66 Feature 66.4: Single Document Upload User Journey
 */

import { test, expect } from '../fixtures';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);


test.describe('Single Document Upload & Verification - GenericAPI 13.0.0', () => {
  // Test document configuration
  const TEST_DOCUMENT = {
    filename: 'D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf',
    relativePath: '../../../data/omnitracker/D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf',
    namespace: 'omnitracker',
    expectedChunks: 50, // Estimated: 1.9MB PDF → ~50-100 chunks
    ingestionTimeout: 600000, // 10 minutes max (VLM processing for 85 images takes ~4 min)
  };

  // Test questions covering different retrieval methods
  const TEST_QUESTIONS = [
    {
      id: 'Q1',
      question: 'Was ist die OMNITRACKER GenericAPI?',
      retrieval: 'VECTOR', // Factual definition question
      expectedKeywords: ['genericapi', 'api', 'schnittstelle', 'rest', 'omnitracker'],
      minKeywords: 2,
      description: 'Factual definition - should use Vector Search (BGE-M3)'
    },
    {
      id: 'Q2',
      question: 'Welche HTTP-Methoden werden von der GenericAPI unterstützt?',
      retrieval: 'BM25', // List/enumeration question
      expectedKeywords: ['get', 'post', 'put', 'delete', 'patch'],
      minKeywords: 3,
      description: 'Enumeration - should use BM25 keyword search'
    },
    {
      id: 'Q3',
      question: 'Wie erfolgt die Authentifizierung bei der GenericAPI?',
      retrieval: 'HYBRID', // Technical how-to question
      expectedKeywords: ['authentifizierung', 'token', 'oauth', 'bearer', 'api key', 'login'],
      minKeywords: 2,
      description: 'How-to question - should use Hybrid Search (Vector + BM25)'
    },
    {
      id: 'Q4',
      question: 'Welche Beziehung besteht zwischen der GenericAPI und dem OMNITRACKER Application Server?',
      retrieval: 'GRAPH', // Relationship question
      expectedKeywords: ['application server', 'schnittstelle', 'verbindung', 'integration', 'kommunikation'],
      minKeywords: 2,
      description: 'Relationship - should use Graph Reasoning'
    },
    {
      id: 'Q5',
      question: 'Welche neuen Features wurden in Version 13.0.0 der GenericAPI eingeführt?',
      retrieval: 'VECTOR', // Specific version question
      expectedKeywords: ['13.0.0', 'version', 'neu', 'feature', 'änderung', 'update'],
      minKeywords: 2,
      description: 'Version-specific factual question - Vector Search'
    },
    {
      id: 'Q6',
      question: 'Welche Endpoints stellt die GenericAPI zur Verfügung?',
      retrieval: 'BM25', // List of endpoints
      expectedKeywords: ['endpoint', 'url', 'pfad', 'route', '/api/'],
      minKeywords: 2,
      description: 'Endpoint list - BM25 keyword matching'
    },
    {
      id: 'Q7',
      question: 'Welche Datenformate werden von der GenericAPI akzeptiert?',
      retrieval: 'BM25', // Technical specification
      expectedKeywords: ['json', 'xml', 'csv', 'format', 'content-type'],
      minKeywords: 1,
      description: 'Data format specification - BM25 search'
    },
    {
      id: 'Q8',
      question: 'Wie unterscheidet sich die GenericAPI von anderen OMNITRACKER APIs?',
      retrieval: 'GRAPH', // Comparison/relationship question
      expectedKeywords: ['unterschied', 'vergleich', 'andere', 'api', 'spezifisch', 'generic'],
      minKeywords: 2,
      description: 'Comparison - Graph Reasoning for relationships'
    },
    {
      id: 'Q9',
      question: 'Welche Use Cases werden in der GenericAPI Dokumentation beschrieben?',
      retrieval: 'HYBRID', // Use case extraction
      expectedKeywords: ['use case', 'anwendungsfall', 'beispiel', 'szenario', 'integration'],
      minKeywords: 2,
      description: 'Use case extraction - Hybrid Search'
    },
    {
      id: 'Q10',
      question: 'Welche Fehlerbehandlung implementiert die GenericAPI?',
      retrieval: 'VECTOR', // Technical implementation detail
      expectedKeywords: ['fehler', 'error', 'exception', 'status code', '400', '500', 'handling'],
      minKeywords: 2,
      description: 'Error handling - Vector Search for technical details'
    }
  ];

  test('should upload document via admin UI and verify ingestion', async ({ adminIndexingPage, page }) => {
    // Set extended timeout for this test (ingestion can take 2-5 minutes)
    test.setTimeout(TEST_DOCUMENT.ingestionTimeout);

    // ============================================
    // STEP 0: Already authenticated via fixture
    // ============================================

    // ============================================
    // STEP 1: Navigate to Admin Indexing Page
    // ============================================
    await adminIndexingPage.goto();
    await expect(page).toHaveURL(/\/admin\/indexing/);

    // ============================================
    // STEP 2: Select Test Document
    // ============================================
    const filePath = path.join(__dirname, TEST_DOCUMENT.relativePath);
    await adminIndexingPage.uploadLocalFiles([filePath]);

    // Verify file selected
    const selectedCount = await adminIndexingPage.getSelectedLocalFilesCount();
    expect(selectedCount).toBeGreaterThan(0);

    console.log(`✅ Selected document: ${TEST_DOCUMENT.filename}`);

    // ============================================
    // STEP 3: Upload Files to Server
    // ============================================
    await expect(adminIndexingPage.uploadFilesButton).toBeEnabled();
    await adminIndexingPage.clickUploadButton();

    console.log('🔄 Uploading file to server...');

    // Wait for upload to complete
    const uploadResult = await adminIndexingPage.waitForUploadComplete(30000);
    expect(uploadResult).toBe('success');

    console.log('✅ File uploaded to server');

    // ============================================
    // STEP 4: Start Indexing
    // ============================================
    await expect(adminIndexingPage.indexButton).toBeEnabled();
    await adminIndexingPage.startIndexing();

    console.log('🔄 Indexing started...');

    // Wait for indexing to complete
    await adminIndexingPage.waitForIndexingComplete(TEST_DOCUMENT.ingestionTimeout);

    console.log('✅ Indexing complete!');

    // ============================================
    // STEP 5: Navigate to Chat Page to Test Document
    // ============================================
    await page.goto('/');
    await page.waitForSelector('[data-testid="message-input"]', { timeout: 10000 });

    console.log('✅ Navigated to chat page - document should be searchable now');
  });

  // ============================================
  // STEP 5: Test Each Question
  // ============================================
  for (const testCase of TEST_QUESTIONS) {
    test(`${testCase.id}: ${testCase.question} (${testCase.retrieval})`, async ({ chatPage, page }) => {
      // Navigate to chat page (already handled by fixture)
      await chatPage.goto();

      // Send question
      const messageInput = page.locator('[data-testid="message-input"]');
      await messageInput.fill(testCase.question);

      console.log(`\n📝 Testing ${testCase.id}: ${testCase.question}`);
      console.log(`   Expected Retrieval: ${testCase.retrieval}`);

      // Send message
      const sendButton = page.locator('[data-testid="send-button"]');
      await sendButton.click();

      // Wait for response
      await page.waitForSelector('[data-testid="message-assistant"]', {
        timeout: 60000,
      });

      // Get response text
      const responseElement = page.locator('[data-testid="message-assistant"]').last();
      const responseText = await responseElement.textContent();

      // Verify response is not empty or error message
      expect(responseText).toBeTruthy();
      expect(responseText!.length).toBeGreaterThan(50);

      // Should NOT contain "not enough information" or similar error messages
      const lowerResponse = responseText!.toLowerCase();
      expect(lowerResponse).not.toContain('not enough information');
      expect(lowerResponse).not.toContain('keine informationen');
      expect(lowerResponse).not.toContain('i don\'t have');
      expect(lowerResponse).not.toContain('ich habe keine');

      console.log(`   ✓ Response received (${responseText!.length} characters)`);

      // ============================================
      // Keyword Verification
      // ============================================
      const foundKeywords: string[] = [];
      for (const keyword of testCase.expectedKeywords) {
        if (lowerResponse.includes(keyword.toLowerCase())) {
          foundKeywords.push(keyword);
        }
      }

      console.log(`   ✓ Found keywords (${foundKeywords.length}/${testCase.expectedKeywords.length}): ${foundKeywords.join(', ')}`);

      // Assert minimum keywords found
      expect(foundKeywords.length).toBeGreaterThanOrEqual(testCase.minKeywords);

      // ============================================
      // Intent Classification Verification (if visible)
      // ============================================
      // Check if intent classification badge is visible
      const intentBadge = page.locator('[data-testid="intent-badge"]');
      if (await intentBadge.isVisible({ timeout: 1000 }).catch(() => false)) {
        const intentText = await intentBadge.textContent();
        console.log(`   ℹ️  Detected Intent: ${intentText}`);

        // Verify expected retrieval method (loose check, as LLM may classify differently)
        if (testCase.retrieval === 'VECTOR') {
          // Vector search typically triggered for factual queries
          expect(intentText?.toLowerCase()).toMatch(/vector|faktenbezogen|factual/i);
        } else if (testCase.retrieval === 'GRAPH') {
          // Graph search for relationship questions
          expect(intentText?.toLowerCase()).toMatch(/graph|beziehung|relationship/i);
        } else if (testCase.retrieval === 'BM25') {
          // BM25 for keyword/list queries (though may be classified as VECTOR)
          // Looser assertion here as BM25 is often combined with Vector
        } else if (testCase.retrieval === 'HYBRID') {
          // Hybrid can be any combination
        }
      }

      // ============================================
      // Source Verification
      // ============================================
      // Check if sources are displayed
      const sourcesSection = page.locator('[data-testid="sources"]');
      if (await sourcesSection.isVisible({ timeout: 1000 }).catch(() => false)) {
        const sourcesText = await sourcesSection.textContent();

        // Verify source contains our test document
        expect(sourcesText?.toLowerCase()).toContain(TEST_DOCUMENT.filename.toLowerCase());
        console.log(`   ✓ Source verified: ${TEST_DOCUMENT.filename}`);
      }

      console.log(`✅ ${testCase.id} PASSED`);
    });
  }

  // ============================================
  // STEP 6: Comprehensive Test (All Questions)
  // ============================================
  test('should answer all 10 questions with consistent quality', async ({ chatPage, page }) => {
    await chatPage.goto();

    let passedQuestions = 0;
    const results: { question: string; passed: boolean; keywords: number }[] = [];

    for (const testCase of TEST_QUESTIONS) {
      // Send question
      const messageInput = page.locator('[data-testid="message-input"]');
      await messageInput.fill(testCase.question);
      await page.locator('[data-testid="send-button"]').click();

      // Wait for response
      await page.waitForSelector('[data-testid="message-assistant"]', {
        timeout: 60000,
      });

      const responseText = await page
        .locator('[data-testid="message-assistant"]')
        .last()
        .textContent();

      // Check keywords
      const foundKeywords = testCase.expectedKeywords.filter((kw) =>
        responseText?.toLowerCase().includes(kw.toLowerCase())
      );

      const passed =
        foundKeywords.length >= testCase.minKeywords &&
        !responseText?.toLowerCase().includes('not enough information');

      results.push({
        question: testCase.question,
        passed,
        keywords: foundKeywords.length,
      });

      if (passed) passedQuestions++;

      // Wait before next question to avoid rate limiting
      await page.waitForTimeout(2000);
    }

    // ============================================
    // Final Assertions
    // ============================================
    console.log('\n📊 Test Results Summary:');
    console.log(`   Passed: ${passedQuestions}/${TEST_QUESTIONS.length}`);
    console.log(`   Success Rate: ${((passedQuestions / TEST_QUESTIONS.length) * 100).toFixed(1)}%`);

    results.forEach((r, i) => {
      const status = r.passed ? '✅' : '❌';
      console.log(`   ${status} Q${i + 1}: ${r.keywords}/${TEST_QUESTIONS[i].expectedKeywords.length} keywords`);
    });

    // Assert at least 80% of questions passed
    const successRate = (passedQuestions / TEST_QUESTIONS.length) * 100;
    expect(successRate).toBeGreaterThanOrEqual(80);

    console.log(`\n✅ Overall Success: ${successRate.toFixed(1)}% (>= 80% required)`);
  });
});
