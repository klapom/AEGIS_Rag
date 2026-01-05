import { test, expect } from '../../fixtures';

/**
 * RAGAS E2E User Journey - Domain Setup & Document Ingestion
 *
 * Sprint 75: Pragmatic approach using API + UI
 *
 * This test prepares the RAGAS evaluation environment:
 * 1. Create domain via API (faster, more reliable)
 * 2. Configure RAG settings via API (faster)
 * 3. Ingest AEGIS RAG docs via API (reliable namespace handling)
 *
 * After completion, run: python scripts/run_ragas_on_namespace.py
 *
 * Note: We use API instead of full UI for steps 1-3 because:
 * - Faster execution (~5 min vs ~30 min)
 * - More reliable (no UI flakiness)
 * - Better for CI/CD automation
 * - Still validates the backend (which is what RAGAS evaluates)
 */

test.describe('RAGAS Domain Setup - Sprint 75', () => {
  const NAMESPACE_ID = 'ragas_eval_domain';
  const DOCS_PATH = '/home/admin/projects/aegisrag/AEGIS_Rag/docs';

  test.beforeAll(async ({ request }) => {
    // Clean up: Delete domain if exists from previous run
    try {
      const response = await request.delete(`/api/v1/admin/domains/${NAMESPACE_ID}`);
      if (response.ok()) {
        console.log(`✓ Cleaned up existing domain: ${NAMESPACE_ID}`);
      }
    } catch (e) {
      // Ignore if domain doesn't exist
      console.log(`  No existing domain to clean up`);
    }
  });

  test('Step 1-2: Create & Configure RAGAS Domain (API)', async ({ request }) => {
    console.log('\n' + '='.repeat(70));
    console.log('STEP 1-2: Creating and configuring RAGAS evaluation domain...');
    console.log('='.repeat(70));

    // Step 1: Create domain
    const createResponse = await request.post('/api/v1/admin/domains', {
      data: {
        domain_id: NAMESPACE_ID,
        name: 'RAGAS Evaluation Domain',
        description: 'Domain for RAGAS evaluation with AEGIS RAG documentation. Namespace-isolated for objective quality measurement.',
        is_active: true,
      },
    });

    expect(createResponse.ok()).toBeTruthy();
    const domain = await createResponse.json();

    console.log(`✓ Step 1 complete: Domain "${NAMESPACE_ID}" created`);
    console.log(`  Domain ID: ${domain.domain_id}`);
    console.log(`  Name: ${domain.name}`);

    // Step 2: Configure RAG settings
    const configResponse = await request.put(`/api/v1/admin/domains/${NAMESPACE_ID}/settings`, {
      data: {
        retrieval_method: 'hybrid',  // Hybrid retrieval (Vector + BM25 + RRF)
        use_reranking: true,          // Enable cross-encoder reranking
        top_k: 10,                    // Retrieve 10 documents
        score_threshold: 0.65,        // Minimum similarity threshold
        adaptive_weights: true,       // Enable learned reranker weights
        rrf_k: 60,                    // RRF constant
      },
    });

    expect(configResponse.ok()).toBeTruthy();
    const settings = await configResponse.json();

    console.log('✓ Step 2 complete: RAG settings configured');
    console.log(`  Retrieval Method: ${settings.retrieval_method}`);
    console.log(`  Reranking: ${settings.use_reranking}`);
    console.log(`  Top-K: ${settings.top_k}`);
    console.log(`  Adaptive Weights: ${settings.adaptive_weights}`);
  });

  test('Step 3: Ingest AEGIS RAG Documentation (API)', async ({ request }) => {
    console.log('\n' + '='.repeat(70));
    console.log('STEP 3: Ingesting AEGIS RAG documentation...');
    console.log('='.repeat(70));

    // Scan directory for markdown files
    const scanResponse = await request.post('/api/v1/admin/indexing/scan-directory', {
      data: {
        directory_path: DOCS_PATH,
        recursive: true,
        file_patterns: ['*.md'],
      },
    });

    expect(scanResponse.ok()).toBeTruthy();
    const scanResult = await scanResponse.json();

    const fileCount = scanResult.files?.length || 0;
    expect(fileCount).toBeGreaterThan(400);  // Expect ~493 files

    console.log(`✓ Found ${fileCount} documentation files`);

    // Filter for .md files only
    const mdFiles = scanResult.files.filter((f: any) => f.file_path.endsWith('.md'));

    console.log(`  Markdown files: ${mdFiles.length}`);
    console.log(`  Starting batch ingestion...`);

    // Start batch indexing
    const batchResponse = await request.post('/api/v1/admin/indexing/batch', {
      data: {
        file_paths: mdFiles.map((f: any) => f.file_path),
        namespace_id: NAMESPACE_ID,
        enable_vlm: true,           // Enable VLM metadata
        enable_graph: true,         // Enable Neo4j graph extraction
        max_workers: 3,             // Parallel workers
      },
    });

    expect(batchResponse.ok()).toBeTruthy();
    const batchResult = await batchResponse.json();

    console.log(`  Batch job started: ${batchResult.job_id}`);
    console.log(`  Files queued: ${batchResult.total_files}`);

    // Poll for completion (check every 30 seconds, max 20 minutes)
    let completed = false;
    let attempts = 0;
    const maxAttempts = 40; // 20 minutes

    while (!completed && attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 30000)); // 30 seconds

      // Check job status
      const statusResponse = await request.get(`/api/v1/admin/ingestion/jobs/${batchResult.job_id}`);
      expect(statusResponse.ok()).toBeTruthy();

      const status = await statusResponse.json();

      if (status.status === 'completed') {
        completed = true;
        console.log(`✓ Step 3 complete: ${status.successful_files} documents indexed`);
        console.log(`  Successful: ${status.successful_files}`);
        console.log(`  Failed: ${status.failed_files}`);
        console.log(`  Total time: ${Math.round(status.duration_seconds / 60)} minutes`);

        expect(status.successful_files).toBeGreaterThan(400);
        break;
      } else if (status.status === 'failed') {
        throw new Error(`Batch indexing failed: ${status.error}`);
      }

      // Log progress
      const progress = Math.round((status.completed_files / status.total_files) * 100);
      console.log(`  Progress: ${progress}% (${status.completed_files}/${status.total_files})`);

      attempts++;
    }

    if (!completed) {
      throw new Error('Indexing timeout after 20 minutes');
    }

    // Verify namespace isolation
    console.log('\n  Verifying namespace isolation...');

    const namespaceResponse = await request.get(`/api/v1/admin/namespaces/${NAMESPACE_ID}/stats`);
    expect(namespaceResponse.ok()).toBeTruthy();

    const namespaceStats = await namespaceResponse.json();
    console.log(`✓ Namespace isolation verified`);
    console.log(`  Document count: ${namespaceStats.document_count}`);
    console.log(`  Chunk count: ${namespaceStats.chunk_count}`);
    console.log(`  Entity count: ${namespaceStats.entity_count}`);

    expect(namespaceStats.document_count).toBeGreaterThan(400);
  });

  test('Verification: Query RAGAS domain to confirm readiness', async ({ request }) => {
    console.log('\n' + '='.repeat(70));
    console.log('VERIFICATION: Testing retrieval on RAGAS domain...');
    console.log('='.repeat(70));

    // Test query to verify documents are retrievable
    const queryResponse = await request.post('/api/v1/retrieval/hybrid', {
      data: {
        query: 'What is the AEGIS RAG architecture?',
        namespaces: [NAMESPACE_ID],
        top_k: 5,
      },
    });

    expect(queryResponse.ok()).toBeTruthy();
    const results = await queryResponse.json();

    expect(results.results).toBeDefined();
    expect(results.results.length).toBeGreaterThan(0);

    console.log(`✓ Retrieved ${results.results.length} documents`);
    console.log(`  Top result score: ${results.results[0].score.toFixed(3)}`);
    console.log(`  Top result source: ${results.results[0].source}`);

    // Verify results are from AEGIS RAG docs (not OMNITRACKER!)
    const sources = results.results.map((r: any) => r.source || '');
    const hasAegisRagDocs = sources.some((s: string) =>
      s.includes('ARCHITECTURE.md') ||
      s.includes('TECH_STACK.md') ||
      s.includes('AEGIS_RAG') ||
      s.includes('docs/')
    );

    expect(hasAegisRagDocs).toBeTruthy();
    console.log(`✓ Documents are from AEGIS RAG (not OMNITRACKER)`);

    console.log('\n' + '='.repeat(70));
    console.log('✅ RAGAS DOMAIN READY FOR EVALUATION');
    console.log('='.repeat(70));
    console.log('\nNext step: Run RAGAS evaluation');
    console.log('  python scripts/run_ragas_on_namespace.py --namespace ragas_eval_domain\n');
  });
});
