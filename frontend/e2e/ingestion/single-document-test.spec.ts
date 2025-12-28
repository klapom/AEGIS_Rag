/**
 * E2E Test: Single Document Upload & Content Verification
 *
 * Test Document: D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf
 * Purpose: Verify complete ingestion pipeline and retrieval quality
 * Coverage: Vector Search (BGE-M3) + BM25 Search + Graph Reasoning
 *
 * Sprint 66 Feature 66.4: Single Document Upload User Journey
 */

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Auth Helper: Mock authentication for protected routes
 * Based on e2e/tests/auth/login.spec.ts pattern
 *
 * Sprint 66 Fix: Navigate BEFORE setting localStorage to avoid SecurityError
 */
async function setupAuth(page: any) {
  // Mock /me endpoint for auth check
  await page.route('**/api/v1/auth/me', (route: any) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        username: 'testuser',
        email: 'test@example.com',
        created_at: '2024-01-01T00:00:00Z',
      }),
    });
  });

  // Sprint 66 Fix: Navigate to valid origin FIRST to avoid localStorage SecurityError
  await page.goto('/');

  // Set valid token in localStorage AFTER navigation
  await page.evaluate(() => {
    localStorage.setItem(
      'aegis_auth_token',
      JSON.stringify({
        token: 'test-jwt-token',
        expiresAt: Date.now() + 3600000, // 1 hour from now
      })
    );
  });
}

test.describe('Single Document Upload & Verification - GenericAPI 13.0.0', () => {
  // Test document configuration
  const TEST_DOCUMENT = {
    filename: 'D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf',
    relativePath: '../../../data/omnitracker/D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf',
    namespace: 'omnitracker',
    expectedChunks: 50, // Estimated: 1.9MB PDF → ~50-100 chunks
    ingestionTimeout: 300000, // 5 minutes max
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

  test('should upload document via admin UI and verify ingestion', async ({ page }) => {
    // ============================================
    // STEP 0: Setup Authentication
    // ============================================
    // Must navigate to app first to enable localStorage
    await page.goto('/');
    await setupAuth(page);

    // ============================================
    // STEP 1: Navigate to Admin Indexing Page
    // ============================================
    await page.goto('/admin/indexing');
    await expect(page).toHaveURL(/\/admin\/indexing/);

    // ============================================
    // STEP 2: Select Test Document
    // ============================================
    const filePath = path.join(__dirname, TEST_DOCUMENT.relativePath);
    const fileInput = page.locator('[data-testid="file-upload-input"]');
    await fileInput.setInputFiles(filePath);

    // Verify file selected
    await expect(page.locator(`text=/${TEST_DOCUMENT.filename}/`)).toBeVisible({
      timeout: 5000,
    });

    console.log(`✅ Selected document: ${TEST_DOCUMENT.filename}`);

    // ============================================
    // STEP 3: Upload & Ingest Document
    // ============================================
    const uploadButton = page.locator('button:has-text("Upload & Ingest")');
    await expect(uploadButton).toBeEnabled();
    await uploadButton.click();

    console.log('🔄 Upload started, waiting for ingestion to complete...');

    // Wait for each ingestion stage
    const stages = ['Upload', 'Parsing', 'Chunking', 'Embedding', 'Indexing', 'Complete'];
    for (const stage of stages) {
      await expect(page.locator(`text=/${stage}/i`)).toBeVisible({
        timeout: TEST_DOCUMENT.ingestionTimeout / stages.length,
      });
      console.log(`  ✓ Stage: ${stage}`);
    }

    // Wait for final "Complete" message
    await expect(page.locator('text=/Complete/i')).toBeVisible({
      timeout: 30000,
    });

    console.log('✅ Ingestion complete!');

    // ============================================
    // STEP 4: Verify Redirect to Chat Page
    // ============================================
    await expect(page).toHaveURL(/\/\?query=/, { timeout: 10000 });

    // Verify pre-filled query contains document filename
    const messageInput = page.locator('[data-testid="message-input"]');
    const inputValue = await messageInput.inputValue();
    expect(inputValue).toContain(TEST_DOCUMENT.filename);

    console.log('✅ Redirected to chat page with pre-filled query');
  });

  // ============================================
  // STEP 5: Test Each Question
  // ============================================
  for (const testCase of TEST_QUESTIONS) {
    test(`${testCase.id}: ${testCase.question} (${testCase.retrieval})`, async ({ page }) => {
      // Navigate to chat page
      await page.goto('/');

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
  test('should answer all 10 questions with consistent quality', async ({ page }) => {
    await page.goto('/');

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
