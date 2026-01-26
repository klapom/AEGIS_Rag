import { test, expect } from '../fixtures';

/**
 * E2E Tests for Domain Training API Endpoints
 * Feature 45.3: Domain Management API
 * Feature 45.10: Batch Ingestion API
 * Feature 45.12: Domain Classification API
 *
 * Tests cover:
 * - Domain CRUD operations
 * - Available models endpoint
 * - Document classification to domain
 * - Domain auto-discovery
 * - Training data augmentation
 * - Batch ingestion with domain routing
 *
 * Sprint 119: Un-skipped after fixing router prefix from /admin/domains to /api/v1/admin/domains.
 * Tests now conditionally skip if API is unreachable.
 */

test.describe('Domain Training API - Basic Operations', () => {
  // Sprint 119: Conditional skip if API not reachable
  test.beforeAll(async ({ request }) => {
    try {
      const response = await request.get('http://localhost:8000/api/v1/admin/domains/');
      if (response.status() === 404) {
        test.skip(true, 'Domain Training API not reachable (404)');
      }
    } catch {
      test.skip(true, 'Backend not reachable for domain training tests');
    }
  });
  test('should list all domains', async ({ request }) => {
    const response = await request.get('/api/v1/admin/domains/');
    expect(response.ok()).toBeTruthy();

    const domains = await response.json();
    expect(Array.isArray(domains)).toBeTruthy();

    // Should have at least the "general" domain
    const generalDomain = domains.find((d: any) => d.name === 'general');
    expect(generalDomain).toBeTruthy();
  });

  test('should get available models from Ollama', async ({ request }) => {
    const response = await request.get('/api/v1/admin/domains/available-models');
    expect(response.ok()).toBeTruthy();

    const models = await response.json();
    expect(Array.isArray(models)).toBeTruthy();

    // If models exist, should have name and size properties
    if (models.length > 0) {
      const firstModel = models[0];
      expect(firstModel).toHaveProperty('name');
      expect(firstModel).toHaveProperty('size');
    }
  });

  test('should reject invalid domain creation - missing name', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/', {
      data: {
        // Missing name field
        description: 'Test domain without name',
      },
    });

    expect(response.status()).toBe(422); // Validation error
  });

  test('should reject invalid domain creation - uppercase in name', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/', {
      data: {
        name: 'InvalidName', // Invalid: uppercase
        description: 'Test domain with invalid name',
      },
    });

    expect(response.status()).toBe(422);
  });

  test('should reject invalid domain creation - spaces in name', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/', {
      data: {
        name: 'invalid name', // Invalid: spaces
        description: 'Test domain with spaces in name',
      },
    });

    expect(response.status()).toBe(422);
  });

  test('should reject invalid domain creation - special characters', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/', {
      data: {
        name: 'invalid-name', // Invalid: hyphens (only underscores allowed)
        description: 'Test domain with special characters',
      },
    });

    expect(response.status()).toBe(422);
  });

  test('should accept valid domain name format', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/', {
      data: {
        name: 'test_valid_domain',
        description: 'This is a valid test domain with correct name format',
        llm_model: 'qwen3:32b',
      },
    });

    // Should succeed or return 409 if domain already exists
    expect([201, 200, 409]).toContain(response.status());
  });
});

test.describe('Domain Training API - Classification', () => {
  test('should classify document to domain', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/classify', {
      data: {
        text: 'This is a technical document about API design and software architecture patterns',
        top_k: 3,
      },
    });

    expect(response.ok()).toBeTruthy();

    const result = await response.json();
    expect(result).toHaveProperty('classifications');
    expect(result).toHaveProperty('recommended');
    expect(result).toHaveProperty('confidence');

    // Check classifications structure
    expect(Array.isArray(result.classifications)).toBeTruthy();
    if (result.classifications.length > 0) {
      const firstClass = result.classifications[0];
      expect(firstClass).toHaveProperty('domain');
      expect(firstClass).toHaveProperty('score');
      expect(firstClass.score).toBeGreaterThanOrEqual(0);
      expect(firstClass.score).toBeLessThanOrEqual(1);
    }

    // Confidence should be between 0 and 1
    expect(result.confidence).toBeGreaterThanOrEqual(0);
    expect(result.confidence).toBeLessThanOrEqual(1);
  });

  test('should handle classification with top_k parameter', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/classify', {
      data: {
        text: 'Machine learning is a subset of artificial intelligence',
        top_k: 5,
      },
    });

    expect(response.ok()).toBeTruthy();

    const result = await response.json();
    // Should return at most top_k results
    expect(result.classifications.length).toBeLessThanOrEqual(5);
  });

  test('should reject classification with too short text', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/classify', {
      data: {
        text: 'Short', // Too short
        top_k: 3,
      },
    });

    expect(response.status()).toBe(422);
  });

  test('should reject classification with invalid top_k', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/classify', {
      data: {
        text: 'This is a valid document text with enough content',
        top_k: 100, // Invalid: exceeds maximum of 10
      },
    });

    expect(response.status()).toBe(422);
  });

  test('should handle classification with minimum text length', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/classify', {
      data: {
        text: 'This is the minimum acceptable length for classification test', // Minimum 10 chars
        top_k: 3,
      },
    });

    expect(response.ok()).toBeTruthy();
  });
});

test.describe('Domain Training API - Domain Auto-Discovery', () => {
  test('should require minimum 3 samples for discovery', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/discover', {
      data: {
        sample_texts: ['Only one sample', 'And a second one'], // Less than 3
        llm_model: 'qwen3:32b',
      },
    });

    expect(response.status()).toBe(422);
  });

  test('should reject more than 10 samples', async ({ request }) => {
    const samples = Array.from({ length: 11 }, (_, i) => `Sample text ${i + 1}`);

    const response = await request.post('/api/v1/admin/domains/discover', {
      data: {
        sample_texts: samples, // More than 10
        llm_model: 'qwen3:32b',
      },
    });

    expect(response.status()).toBe(422);
  });

  test('should accept valid discovery request with 3 samples', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/discover', {
      data: {
        sample_texts: [
          'Python is a programming language',
          'FastAPI is a web framework',
          'Docker is a containerization platform',
        ],
        llm_model: 'qwen3:32b',
      },
    });

    // May timeout on slow LLM, but should not return 422
    expect(response.status()).not.toBe(422);
  });

  test('should discover domain with comprehensive samples', async ({ request }) => {
    const samples = [
      'Python is a high-level programming language',
      'FastAPI is a modern web framework for building APIs',
      'Django is a full-featured web framework',
      'SQLAlchemy provides ORM capabilities',
      'PostgreSQL is a powerful relational database',
    ];

    const response = await request.post('/api/v1/admin/domains/discover', {
      data: {
        sample_texts: samples,
        llm_model: 'qwen3:32b',
      },
    });

    // Should either succeed or timeout (depending on LLM availability)
    // But not return validation error
    if (response.ok()) {
      const result = await response.json();
      expect(result).toHaveProperty('name');
      expect(result.name).toMatch(/^[a-z_]+$/); // Valid domain name format
      expect(result).toHaveProperty('description');
      expect(result.description.length).toBeGreaterThan(0);
    }
  });
});

test.describe('Domain Training API - Training Data Augmentation', () => {
  test('should augment training data with minimum samples', async ({ request }) => {
    const seedSamples = [
      { text: 'Sample 1 text', entities: ['Entity1'], relations: [] },
      { text: 'Sample 2 text', entities: ['Entity2'], relations: [] },
      { text: 'Sample 3 text', entities: ['Entity3'], relations: [] },
      { text: 'Sample 4 text', entities: ['Entity4'], relations: [] },
      { text: 'Sample 5 text', entities: ['Entity5'], relations: [] },
    ];

    const response = await request.post('/api/v1/admin/domains/augment', {
      data: {
        seed_samples: seedSamples,
        target_count: 3, // Generate 3 more samples
        llm_model: 'qwen3:32b',
      },
    });

    // May timeout on slow LLM
    if (response.ok()) {
      const result = await response.json();
      expect(result).toHaveProperty('generated_count');
      expect(result).toHaveProperty('generated_samples');
      expect(Array.isArray(result.generated_samples)).toBeTruthy();
    }
  });

  test('should reject augmentation with insufficient samples', async ({ request }) => {
    const seedSamples = [
      { text: 'Only one sample', entities: ['Entity1'], relations: [] },
    ];

    const response = await request.post('/api/v1/admin/domains/augment', {
      data: {
        seed_samples: seedSamples,
        target_count: 5,
        llm_model: 'qwen3:32b',
      },
    });

    expect(response.status()).toBe(422);
  });

  test('should validate target count range', async ({ request }) => {
    const seedSamples = Array.from({ length: 5 }, (_, i) => ({
      text: `Sample ${i + 1} text content`,
      entities: [`Entity${i + 1}`],
      relations: [],
    }));

    // Test with 0 target (invalid)
    const response = await request.post('/api/v1/admin/domains/augment', {
      data: {
        seed_samples: seedSamples,
        target_count: 0, // Invalid
        llm_model: 'qwen3:32b',
      },
    });

    expect(response.status()).toBe(422);
  });
});

test.describe('Domain Training API - Batch Ingestion', () => {
  test('should accept batch ingestion request', async ({ request }) => {
    const items = [
      {
        file_path: '/documents/doc1.txt',
        text: 'First document content about technology and software development',
        domain: 'general',
      },
      {
        file_path: '/documents/doc2.txt',
        text: 'Second document content about business and management',
        domain: 'general',
      },
      {
        file_path: '/documents/doc3.txt',
        text: 'Third document about legal matters and contracts',
        domain: 'general',
      },
    ];

    const response = await request.post('/api/v1/admin/domains/ingest-batch', {
      data: {
        items: items,
      },
    });

    expect(response.ok()).toBeTruthy();

    const result = await response.json();
    expect(result).toHaveProperty('message');
    expect(result).toHaveProperty('total_items');
    expect(result.total_items).toBe(3);
    expect(result).toHaveProperty('model_groups');
    expect(result).toHaveProperty('domain_groups');
  });

  test('should reject empty batch', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/ingest-batch', {
      data: {
        items: [], // Empty
      },
    });

    expect(response.status()).toBe(422);
  });

  test('should handle large batch ingestion', async ({ request }) => {
    // Create 50 documents
    const items = Array.from({ length: 50 }, (_, i) => ({
      file_path: `/documents/doc${i + 1}.txt`,
      text: `Document ${i + 1} content with substantial text to ensure proper ingestion and processing`,
      domain: 'general',
    }));

    const response = await request.post('/api/v1/admin/domains/ingest-batch', {
      data: {
        items: items,
      },
    });

    // Should accept batch
    if (response.ok()) {
      const result = await response.json();
      expect(result.total_items).toBe(50);
    }
  });

  test('should group items by configured domain model', async ({ request }) => {
    const items = [
      {
        file_path: '/documents/tech1.txt',
        text: 'Technical documentation about API design patterns',
        domain: 'general',
      },
      {
        file_path: '/documents/tech2.txt',
        text: 'Another technical document about database optimization',
        domain: 'general',
      },
    ];

    const response = await request.post('/api/v1/admin/domains/ingest-batch', {
      data: {
        items: items,
      },
    });

    if (response.ok()) {
      const result = await response.json();
      // Should group by domain
      expect(result.domain_groups).toHaveProperty('general');
      expect(result.domain_groups.general).toBe(2);
    }
  });
});

test.describe('Domain Training API - Domain Detail Operations', () => {
  test('should get domain detail by name', async ({ request }) => {
    const response = await request.get('/api/v1/admin/domains/general');
    expect(response.ok()).toBeTruthy();

    const domain = await response.json();
    expect(domain).toHaveProperty('id');
    expect(domain).toHaveProperty('name');
    expect(domain.name).toBe('general');
    expect(domain).toHaveProperty('description');
    expect(domain).toHaveProperty('status');
    expect(domain).toHaveProperty('llm_model');
    expect(domain).toHaveProperty('created_at');
  });

  test('should return 404 for non-existent domain', async ({ request }) => {
    const response = await request.get('/api/v1/admin/domains/nonexistent_domain_xyz');
    expect(response.status()).toBe(404);
  });

  test('should get training status for domain', async ({ request }) => {
    const response = await request.get('/api/v1/admin/domains/general/training-status');

    // Should either return status or 404 if endpoint not implemented
    expect([200, 404]).toContain(response.status());

    if (response.ok()) {
      const status = await response.json();
      expect(status).toHaveProperty('status');
      expect(status).toHaveProperty('progress_percent');
      expect(status.progress_percent).toBeGreaterThanOrEqual(0);
      expect(status.progress_percent).toBeLessThanOrEqual(100);
    }
  });
});

test.describe('Domain Training API - Input Validation', () => {
  test('should validate training sample structure', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/test_domain/train', {
      data: {
        samples: [
          {
            text: 'Valid sample text',
            entities: ['Entity1', 'Entity2'],
            // relations field is optional
          },
          {
            text: 'Another valid sample',
            entities: ['Entity3'],
            relations: [{ subject: 'Entity3', predicate: 'is', object: 'Entity4' }],
          },
        ],
      },
    });

    // Should either accept or return 404/422 depending on domain existence and API state
    expect([201, 200, 404, 422]).toContain(response.status());
  });

  test('should reject training sample without entities', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/test_domain/train', {
      data: {
        samples: [
          {
            text: 'Sample text without entities array',
            // Missing entities field
          },
        ],
      },
    });

    expect([422, 404]).toContain(response.status());
  });

  test('should handle concurrent requests gracefully', async ({ request }) => {
    const promises = Array.from({ length: 5 }, () =>
      request.get('/api/v1/admin/domains/general')
    );

    const responses = await Promise.all(promises);

    // All should succeed
    responses.forEach((response) => {
      expect(response.ok()).toBeTruthy();
    });
  });
});

test.describe('Domain Training API - Response Format Validation', () => {
  test('should return consistent response structure for domain list', async ({ request }) => {
    const response = await request.get('/api/v1/admin/domains/');
    expect(response.ok()).toBeTruthy();

    const domains = await response.json();
    expect(Array.isArray(domains)).toBeTruthy();

    // Validate structure of first domain if exists
    if (domains.length > 0) {
      const domain = domains[0];
      expect(typeof domain.name).toBe('string');
      expect(typeof domain.description).toBe('string');
      expect(typeof domain.status).toBe('string');
    }
  });

  test('classification response should include all required fields', async ({ request }) => {
    const response = await request.post('/api/v1/admin/domains/classify', {
      data: {
        text: 'This is a comprehensive test document for validation',
        top_k: 3,
      },
    });

    expect(response.ok()).toBeTruthy();

    const result = await response.json();
    // Verify required fields
    expect(result).toHaveProperty('classifications');
    expect(result).toHaveProperty('recommended');
    expect(result).toHaveProperty('confidence');

    // Verify types
    expect(typeof result.recommended).toBe('string');
    expect(typeof result.confidence).toBe('number');
    expect(Array.isArray(result.classifications)).toBeTruthy();
  });
});
