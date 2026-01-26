/**
 * Performance Regression Test Suite - Sprint 120 Feature 120.6
 * Comprehensive performance testing for AEGIS RAG system
 *
 * This test suite validates performance across 5 categories:
 * 1. API Response Times
 * 2. Frontend Load Performance
 * 3. Search Performance
 * 4. UI Interaction Performance
 * 5. Memory/Resource Usage
 *
 * Total Tests: ~15
 * Target Execution Time: <5 minutes
 * Performance Thresholds: Based on system specifications
 *
 * Markers:
 * @performance - Indicates performance regression test
 * @slow - Tests that take >30s to run (full LLM responses)
 * @skip-ci - Tests requiring specific infrastructure (Docker services)
 *
 * Execution:
 * npx playwright test --grep @performance
 * PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test performance-regression.spec.ts
 */

import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * Helper: Measure time of an async operation
 */
async function measureAsync<T>(
  operation: () => Promise<T>,
  label?: string
): Promise<{ result: T; elapsed: number }> {
  const start = performance.now();
  const result = await operation();
  const elapsed = performance.now() - start;

  if (label) {
    console.log(`[PERF] ${label}: ${elapsed.toFixed(2)}ms`);
  }

  return { result, elapsed };
}

/**
 * Helper: Measure browser-side metrics using Performance API
 */
async function getBrowserMetrics(page: Page): Promise<{
  paintTiming: number | null;
  domInteractive: number | null;
  domComplete: number | null;
  pageLoadTime: number | null;
}> {
  return await page.evaluate(() => {
    const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;

    if (!perfData) {
      return {
        paintTiming: null,
        domInteractive: null,
        domComplete: null,
        pageLoadTime: null,
      };
    }

    // Get First Paint if available
    const paintEntries = performance.getEntriesByType('paint');
    const paintTiming = paintEntries.length > 0 ? paintEntries[0].startTime : null;

    return {
      paintTiming,
      domInteractive: perfData.domInteractive,
      domComplete: perfData.domComplete,
      pageLoadTime: perfData.loadEventEnd - perfData.fetchStart,
    };
  });
}

/**
 * GROUP 1: API RESPONSE TIMES
 * Tests for backend API response latency
 */

test('G1.1: Health endpoint responds in <500ms', async ({ page }) => {
  const { elapsed } = await measureAsync(
    () =>
      page.request.get('http://localhost:8000/api/v1/health/', {
        timeout: 5000,
      }),
    'Health endpoint'
  );

  expect(elapsed).toBeLessThan(500);
});

test('G1.2: Detailed health endpoint responds in <1s', async ({ page }) => {
  const { elapsed } = await measureAsync(
    () =>
      page.request.get('http://localhost:8000/api/v1/health/detailed', {
        timeout: 5000,
      }),
    'Detailed health endpoint'
  );

  // Includes dependency checks (Qdrant, embeddings)
  expect(elapsed).toBeLessThan(1000);
});

test('G1.3: Readiness check responds in <500ms', async ({ page }) => {
  const { elapsed } = await measureAsync(
    () =>
      page.request.get('http://localhost:8000/api/v1/health/ready', {
        timeout: 5000,
      }),
    'Readiness check'
  );

  expect(elapsed).toBeLessThan(500);
});

/**
 * GROUP 2: FRONTEND LOAD PERFORMANCE
 * Tests for frontend resource loading and Time to Interactive
 */

test('G2.1: Initial page load completes in <3s', async ({ page }) => {
  const { elapsed } = await measureAsync(
    async () => {
      await page.goto('/', { waitUntil: 'networkidle' });
    },
    'Initial page load'
  );

  // Page should be fully loaded including network idle
  expect(elapsed).toBeLessThan(3000);
});

test('G2.2: Time to Interactive (TTI) <5s', async ({ page }) => {
  await page.goto('/');

  const { result: metrics } = await measureAsync(
    () => getBrowserMetrics(page),
    'Browser metrics collection'
  );

  // DOM interactive indicates when page is interactive
  if (metrics.domInteractive !== null) {
    expect(metrics.domInteractive).toBeLessThan(5000);
  }
});

test('G2.3: Page navigation between routes <1s', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });

  // Measure navigation to history page
  const { elapsed } = await measureAsync(
    async () => {
      await page.goto('/history', { waitUntil: 'networkidle' });
    },
    'Navigation to /history'
  );

  expect(elapsed).toBeLessThan(1000);
});

test('G2.4: Settings page navigation <1s', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });

  const { elapsed } = await measureAsync(
    async () => {
      await page.goto('/settings', { waitUntil: 'networkidle' });
    },
    'Navigation to /settings'
  );

  expect(elapsed).toBeLessThan(1000);
});

/**
 * GROUP 3: SEARCH PERFORMANCE
 * Tests for retrieval system performance across different search modes
 *
 * Note: These tests require proper backend infrastructure and may be skipped
 * if backend services are not fully initialized
 */

test('G3.1: Vector search responds in <3s @slow @skip-ci', async ({ page }) => {
  test.skip(true, 'Skipped: Requires full backend infrastructure with indexed documents');

  // This test requires:
  // 1. Qdrant with indexed documents
  // 2. Embedding service initialized
  // 3. Test documents in database
  //
  // When implemented, would measure:
  // POST /api/v1/agents/search with vector_mode

  const { elapsed } = await measureAsync(
    async () => {
      const response = await page.request.post('http://localhost:8000/api/v1/agents/search', {
        data: {
          query: 'test query',
          mode: 'vector',
          top_k: 5,
        },
        timeout: 5000,
      });
      return response;
    },
    'Vector search'
  );

  // Vector search should be fast with proper indexing
  expect(elapsed).toBeLessThan(3000);
});

test('G3.2: Hybrid search responds in <5s @slow @skip-ci', async ({ page }) => {
  test.skip(true, 'Skipped: Requires full backend infrastructure with indexed documents');

  // Hybrid search (vector + graph) takes longer due to entity expansion
  // Expected: ~2-4s with proper indexing

  const { elapsed } = await measureAsync(
    async () => {
      const response = await page.request.post('http://localhost:8000/api/v1/agents/search', {
        data: {
          query: 'complex question requiring graph reasoning',
          mode: 'hybrid',
          top_k: 10,
        },
        timeout: 10000,
      });
      return response;
    },
    'Hybrid search'
  );

  expect(elapsed).toBeLessThan(5000);
});

test('G3.3: Graph search responds in <5s @slow @skip-ci', async ({ page }) => {
  test.skip(true, 'Skipped: Requires Neo4j with indexed graph data');

  // Graph search requires entity expansion and relationship traversal
  // Expected: ~1-4s with optimized queries

  const { elapsed } = await measureAsync(
    async () => {
      const response = await page.request.post('http://localhost:8000/api/v1/agents/search', {
        data: {
          query: 'entity relationships',
          mode: 'graph',
          top_k: 10,
        },
        timeout: 10000,
      });
      return response;
    },
    'Graph search'
  );

  expect(elapsed).toBeLessThan(5000);
});

/**
 * GROUP 4: UI INTERACTION PERFORMANCE
 * Tests for frontend responsiveness and interaction latency
 */

test('G4.1: Message input typing responsiveness', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });

  // Find message input
  const messageInput = page.locator('[data-testid="message-input"], textarea, input[type="text"]').first();

  // Measure time to type 100 characters
  const { elapsed } = await measureAsync(
    async () => {
      const testMessage = 'This is a performance test message for typing responsiveness check.';
      // Type slowly to measure keystroke handling
      await messageInput.type(testMessage, { delay: 10 });
    },
    'Typing 70 characters'
  );

  // Should complete quickly (browser should not lag)
  // At 10ms per keystroke: 70 chars * 10ms = 700ms expected
  // Allow 1s for React updates
  expect(elapsed).toBeLessThan(1500);
});

test('G4.2: Sidebar toggle animation smoothness', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });

  // Find sidebar toggle button
  const sidebarToggle = page.locator('[data-testid="sidebar-toggle"], button[aria-label*="menu" i]').first();
  const sidebarVisible = await sidebarToggle.isVisible().catch(() => false);

  if (sidebarVisible) {
    const { elapsed } = await measureAsync(
      async () => {
        await sidebarToggle.click();
        // Wait for animation to complete
        await page.waitForTimeout(350);
      },
      'Sidebar toggle with animation'
    );

    // Animation should complete quickly
    expect(elapsed).toBeLessThan(500);
  }
});

test('G4.3: Component rendering with scroll performance', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });

  const { elapsed } = await measureAsync(
    async () => {
      // Simulate scrolling through content
      await page.evaluate(() => {
        const container = document.querySelector('main') || document.body;
        container.scrollTop = 0;

        // Scroll to bottom
        return new Promise((resolve) => {
          const scrollStep = () => {
            container.scrollTop += 100;
            if (container.scrollTop < container.scrollHeight) {
              requestAnimationFrame(scrollStep);
            } else {
              resolve(null);
            }
          };
          scrollStep();
        });
      });

      await page.waitForTimeout(100); // Allow paint to complete
    },
    'Scroll to bottom'
  );

  // Scrolling should be smooth and responsive
  expect(elapsed).toBeLessThan(2000);
});

/**
 * GROUP 5: MEMORY/RESOURCE USAGE
 * Tests for memory leaks and resource stability
 */

test('G5.1: Memory usage stable during extended interaction', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });

  // Get initial memory info from performance API if available
  const initialMemory = await page.evaluate(() => {
    const perf = performance as any;
    if (perf.memory) {
      return {
        usedJSHeapSize: perf.memory.usedJSHeapSize / 1024 / 1024,
        totalJSHeapSize: perf.memory.totalJSHeapSize / 1024 / 1024,
      };
    }
    return null;
  });

  if (initialMemory) {
    console.log(`Initial heap: ${initialMemory.usedJSHeapSize.toFixed(2)} MB`);
  }

  // Simulate extended interaction (repeated navigation, input, etc.)
  const { elapsed } = await measureAsync(
    async () => {
      // Navigate to different pages
      for (let i = 0; i < 5; i++) {
        await page.goto('/', { waitUntil: 'networkidle' });
        await page.waitForTimeout(100);

        await page.goto('/history', { waitUntil: 'networkidle' });
        await page.waitForTimeout(100);

        await page.goto('/settings', { waitUntil: 'networkidle' });
        await page.waitForTimeout(100);
      }
    },
    'Extended navigation test'
  );

  // Get final memory info
  const finalMemory = await page.evaluate(() => {
    const perf = performance as any;
    if (perf.memory) {
      return {
        usedJSHeapSize: perf.memory.usedJSHeapSize / 1024 / 1024,
        totalJSHeapSize: perf.memory.totalJSHeapSize / 1024 / 1024,
      };
    }
    return null;
  });

  let memoryIncrease = 0;
  if (initialMemory && finalMemory) {
    memoryIncrease = finalMemory.usedJSHeapSize - initialMemory.usedJSHeapSize;
    console.log(`Final heap: ${finalMemory.usedJSHeapSize.toFixed(2)} MB`);
    console.log(`Memory increase: ${memoryIncrease.toFixed(2)} MB`);

    // Memory should not grow excessively (allow up to 50MB growth)
    expect(memoryIncrease).toBeLessThan(50);
  }

  expect(elapsed).toBeLessThan(10000);
});

test('G5.2: WebSocket/SSE connection stability @slow @skip-ci', async ({ page }) => {
  test.skip(true, 'Skipped: Requires authenticated user session for chat');

  // This test would verify:
  // 1. WebSocket connection establishment
  // 2. Message streaming stability
  // 3. Connection recovery after interruption
  //
  // When implemented, would:
  // - Connect to chat SSE stream
  // - Send test message
  // - Verify continuous streaming
  // - Check for reconnection capability
});

test('G5.3: Concurrent request handling performance', async ({ page }) => {
  // Test backend can handle multiple concurrent health checks
  const concurrentRequests = 10;
  const requests = [];

  const { elapsed } = await measureAsync(
    async () => {
      // Fire concurrent requests
      for (let i = 0; i < concurrentRequests; i++) {
        requests.push(
          page.request.get('http://localhost:8000/api/v1/health/', {
            timeout: 5000,
          })
        );
      }

      // Wait for all to complete
      await Promise.all(requests);
    },
    `Concurrent requests (${concurrentRequests})`
  );

  // All 10 requests should complete in reasonable time
  // Each takes ~100-200ms, so 10 concurrent should take ~200ms (parallel)
  // Allow up to 2s for overhead
  expect(elapsed).toBeLessThan(2000);

  // Verify all responses were successful
  const results = await Promise.all(requests);
  results.forEach((response) => {
    expect(response.ok()).toBeTruthy();
  });
});

test('G5.4: Network request waterfall analysis', async ({ page }) => {
  // Collect all network requests during page load
  const requestUrls: string[] = [];
  const requestStartTimes: Record<string, number> = {};

  // Intercept requests to collect metrics
  await page.on('request', (request) => {
    const url = request.url();
    requestUrls.push(url);
    requestStartTimes[url] = performance.now();
  });

  const { elapsed } = await measureAsync(
    async () => {
      await page.goto('/', { waitUntil: 'networkidle' });
    },
    'Page load with network analysis'
  );

  console.log(`Total requests: ${requestUrls.length}`);
  console.log(`Total load time: ${elapsed.toFixed(2)}ms`);

  // Verify page loaded within acceptable time
  expect(elapsed).toBeLessThan(3000);

  // Check that there are reasonable number of requests
  expect(requestUrls.length).toBeGreaterThan(0);
  expect(requestUrls.length).toBeLessThan(100); // Sanity check
});

/**
 * PERFORMANCE BASELINE & THRESHOLDS
 *
 * Based on Sprint 92 optimizations:
 * - Graph Search: 17-19s → <2s (89% faster) - Goal achieved
 * - FlagEmbedding Warmup: 40s → <1s
 * - Ollama GPU: 19 tok/s → 77 tok/s
 *
 * Current Performance Targets (Sprint 120):
 * - Health endpoint: <500ms
 * - Page load: <3s
 * - Vector search: <3s
 * - Hybrid search: <5s
 * - Graph search: <5s
 * - Navigation: <1s
 * - TTI: <5s
 * - Memory growth: <50MB for extended use
 *
 * When regressions occur:
 * 1. Check for new blocking operations in critical paths
 * 2. Verify database query optimization
 * 3. Confirm LLM inference isn't bottleneck
 * 4. Review recent changes to graph expansion logic
 * 5. Monitor LangSmith traces for phase timing
 */
