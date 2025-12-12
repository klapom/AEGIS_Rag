# Domain Training E2E Tests

E2E test suite for the Domain Training System (Sprint 45, Features 45.3, 45.10, 45.12).

## Test Files

### 1. `test_domain_training_flow.spec.ts`
UI/UX E2E tests for Domain Training page and workflows.

**Coverage:**
- Page navigation and display
- New Domain Wizard Step 1 (domain configuration)
- Metric configuration panel and presets
- Step 2 (dataset upload)
- Dataset preview and validation
- Auto-discovery of domains
- Model selection
- Complete workflow
- Error handling

**Test Groups:**
- `Domain Training - Page Navigation & Display`: Basic page loads and navigation
- `Domain Training - New Domain Wizard Step 1`: Domain creation input validation
- `Domain Training - Metric Configuration`: Preset selection and custom metrics
- `Domain Training - Step 2: Dataset Upload`: JSONL file upload and preview
- `Domain Training - Auto-Discovery`: Domain auto-discovery from samples
- `Domain Training - Model Selection`: LLM model selection
- `Domain Training - Complete Workflow`: End-to-end domain creation
- `Domain Training - Error Handling`: Input validation and error messages

**Key Tests:**
- Domain name regex validation (lowercase, underscores only)
- Description requirement validation
- Metric preset selection (balanced, precision-focused, recall-focused, custom)
- Custom metric weight adjustment
- JSONL dataset upload with 5+ samples
- Sample preview display
- Step navigation with state preservation
- Auto-discovery with 3-10 samples
- LLM model selection

### 2. `test_domain_training_api.spec.ts`
API endpoint tests for Domain Training REST endpoints.

**Coverage:**
- Domain CRUD operations
- Available models endpoint
- Document classification to domain
- Domain auto-discovery
- Training data augmentation
- Batch ingestion with domain routing
- Input validation
- Response format validation

**Test Groups:**
- `Domain Training API - Basic Operations`: List domains, get models, validation
- `Domain Training API - Classification`: Classify documents to domains
- `Domain Training API - Domain Auto-Discovery`: Discover domains from samples
- `Domain Training API - Training Data Augmentation`: Generate training samples
- `Domain Training API - Batch Ingestion`: Batch upload with domain routing
- `Domain Training API - Domain Detail Operations`: Get domain info and status
- `Domain Training API - Input Validation`: Request validation
- `Domain Training API - Response Format Validation`: Response structure checks

**Key Tests:**
- Domain name format validation (regex: `^[a-z][a-z0-9_]*$`)
- Classification with top_k parameter
- Auto-discovery requires 3-10 samples
- Training data augmentation with seed samples
- Batch ingestion groups by domain and model
- Concurrent request handling
- Response structure validation

### 3. `test_domain_upload_integration.spec.ts`
Integration tests for Domain Training with Upload page.

**Coverage:**
- Domain classification on file upload
- Domain suggestion display
- Confidence badge color coding
- Manual domain override
- Multiple file uploads with classification
- Domain description display
- Error handling and timeouts
- Domain dropdown display
- Batch ingestion with domain routing
- UX feedback during classification

**Test Groups:**
- `Upload Page - Domain Classification Integration`: File upload classification workflow
- `Batch Ingestion with Domain Routing`: Multi-domain batch processing
- `Domain Selection UX`: Visual feedback and confidence display

**Key Tests:**
- Automatic document classification on upload
- Domain suggestion based on confidence
- Confidence badge color coding (green/yellow/red)
- Manual domain override in dropdown
- Multiple documents with different domains
- Domain description display
- Batch ingestion optimizes by LLM model
- Loading indicators during classification
- Error handling with fallback to 'general' domain

## Running Tests

### Setup
Ensure services are running:
```bash
# Terminal 1: Backend API
cd .. && poetry run python -m src.api.main

# Terminal 2: Frontend
npm run dev

# Terminal 3: Tests
npm run test:e2e admin/test_domain_training_flow.spec.ts
```

### Run All Domain Training Tests
```bash
# Run all domain training tests
npm run test:e2e admin/test_domain_training_flow.spec.ts \
                  admin/test_domain_training_api.spec.ts \
                  admin/test_domain_upload_integration.spec.ts

# Or use pattern matching
npm run test:e2e admin/test_domain_training*.spec.ts
npm run test:e2e admin/test_domain_upload*.spec.ts
```

### Run Specific Test Group
```bash
# Run specific test file
npm run test:e2e admin/test_domain_training_flow.spec.ts

# Run specific test suite (uses describe block)
npm run test:e2e --grep "Domain Training - Page Navigation"

# Run single test
npm run test:e2e --grep "should display domain training page on load"
```

### Run in Different Modes
```bash
# Debug mode with headed browser
npm run test:e2e admin/test_domain_training_flow.spec.ts --headed --debug

# Watch mode
npm run test:e2e admin/test_domain_training_flow.spec.ts --watch

# Generate HTML report
npm run test:e2e admin/test_domain_training_flow.spec.ts
# Open: frontend/playwright-report/index.html
```

### Run with Traces
```bash
# Collect full traces on failure
npm run test:e2e admin/test_domain_training_flow.spec.ts --trace on

# View traces
npx playwright show-trace trace.zip
```

## Page Object Model (POM)

### `AdminDomainTrainingPage`
Located in `/e2e/pom/AdminDomainTrainingPage.ts`

**Methods:**
- `goto()`: Navigate to domain training page
- `clickNewDomain()`: Open new domain wizard
- `fillDomainName(name)`: Fill domain name input
- `fillDomainDescription(description)`: Fill description input
- `selectModel(modelName)`: Select LLM model
- `selectMetricPreset(preset)`: Select metric preset
- `setMetricWeight(weight)`: Set custom metric weight
- `clickNext()`: Go to next wizard step
- `clickBack()`: Go to previous step
- `clickCancel()`: Close wizard
- `uploadDataset(fileName, content)`: Upload JSONL file
- `getSampleCount()`: Get loaded sample count
- `clickTraining()`: Start training
- `getTrainingStatus()`: Get current training status
- `openAutoDiscovery()`: Open auto-discovery wizard
- `addAutoDiscoverySamples(samples)`: Add sample texts
- `clickAutoDiscoveryAnalyze()`: Analyze samples
- `getAutoDiscoverySuggestion()`: Get suggestion result
- `domainExists(name)`: Check if domain exists
- `clickDomain(name)`: Click domain in list
- `getErrorMessage()`: Get error message text

**Locators:**
- `pageTitle`: Page heading
- `newDomainButton`: Button to create new domain
- `domainList`: List of domains
- `domainNameInput`: Domain name input field
- `modelSelect`: Model selection dropdown
- `metricConfigPanel`: Metric configuration section
- `presetBalanced`: Balanced preset button
- `datasetDropzone`: File upload dropzone
- `trainingButton`: Training button
- `autoDiscoveryButton`: Auto-discovery button

## Fixtures

### `adminDomainTrainingPage` Fixture
Pre-configured Page Object Model with authentication and navigation:
```typescript
test('example', async ({ adminDomainTrainingPage }) => {
  // Already navigated to /admin/domain-training
  // Auth mocking set up
  await adminDomainTrainingPage.clickNewDomain();
  // ...
});
```

### Setup Authentication
All admin fixtures use `setupAuthMocking()` which:
- Sets `aegis_auth_token` in localStorage
- Mocks `/api/v1/auth/me` endpoint
- Mocks `/api/v1/auth/refresh` endpoint

## Test Data

### Sample JSONL Format
```jsonl
{"text": "Python is a programming language", "entities": ["Python", "language"]}
{"text": "FastAPI is a web framework", "entities": ["FastAPI", "framework"]}
```

### Valid Domain Names
- `software_development`
- `legal_documents`
- `tech_docs`
- `medical_records`

### Invalid Domain Names
- `tech-docs` (hyphens not allowed)
- `TechDocs` (uppercase not allowed)
- `tech docs` (spaces not allowed)
- `@tech#docs` (special characters)

## API Endpoints Tested

### Domain Management
- `GET /api/v1/admin/domains/` - List all domains
- `GET /api/v1/admin/domains/{name}` - Get domain detail
- `POST /api/v1/admin/domains/` - Create new domain
- `DELETE /api/v1/admin/domains/{name}` - Delete domain
- `GET /api/v1/admin/domains/{name}/training-status` - Get training status

### Classification & Discovery
- `POST /api/v1/admin/domains/classify` - Classify document to domain
- `POST /api/v1/admin/domains/discover` - Auto-discover domain
- `GET /api/v1/admin/domains/available-models` - List available LLM models

### Training & Ingestion
- `POST /api/v1/admin/domains/{name}/train` - Start training
- `POST /api/v1/admin/domains/augment` - Augment training data
- `POST /api/v1/admin/domains/ingest-batch` - Batch ingestion with routing

## Test Patterns

### Mocking API Responses
```typescript
test('should show suggestion after classification', async ({ page }) => {
  // Mock the API
  await page.route('**/api/v1/admin/domains/classify', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        recommended: 'software_development',
        confidence: 0.92,
      }),
    });
  });

  // Test code...
});
```

### File Upload Testing
```typescript
const jsonlContent = `{"text": "Sample 1", "entities": ["E1"]}
{"text": "Sample 2", "entities": ["E2"]}`;

await page.getByTestId('dataset-dropzone').setInputFiles({
  name: 'training_data.jsonl',
  mimeType: 'application/json',
  buffer: Buffer.from(jsonlContent),
});
```

### Validating Error Messages
```typescript
test('should validate domain name format', async ({ adminDomainTrainingPage }) => {
  await adminDomainTrainingPage.clickNewDomain();
  await adminDomainTrainingPage.fillDomainName('Invalid Name');
  await adminDomainTrainingPage.clickNext();

  const errorMessage = await adminDomainTrainingPage.getErrorMessage();
  expect(errorMessage.toLowerCase()).toContain('lowercase');
});
```

## Debugging

### Enable Headed Mode
See what's happening in the browser:
```bash
npm run test:e2e admin/test_domain_training_flow.spec.ts --headed
```

### Pause on Failure
```bash
npm run test:e2e admin/test_domain_training_flow.spec.ts --headed --debug
```

### View Traces
```bash
npm run test:e2e admin/test_domain_training_flow.spec.ts --trace on
npx playwright show-trace trace.zip
```

### Slow Motion
See interactions in slow motion:
```bash
npm run test:e2e admin/test_domain_training_flow.spec.ts --headed --slow-mo=1000
```

### Check Test Report
```bash
npm run test:e2e admin/test_domain_training_flow.spec.ts
npx playwright show-report
```

## Common Issues

### Tests Timeout
**Cause:** LLM taking too long to respond

**Solution:**
- Increase timeout in test: `{ timeout: 60000 }`
- Mock the response instead of calling real LLM
- Check if Ollama is running: `curl http://localhost:11434/api/tags`

### Domain Not Found
**Cause:** Database not initialized

**Solution:**
```bash
# Ensure backend is running and Neo4j is initialized
poetry run python -m src.api.main
```

### File Upload Not Triggering Classification
**Cause:** Frontend might need file to have minimum size/content

**Solution:**
- Ensure file content is > 10 characters
- Check console for validation errors
- Verify dropzone element exists

## Best Practices

1. **Use Page Object Models**: Interact through POM methods, not raw selectors
2. **Mock External APIs**: Don't rely on real LLM responses in tests
3. **Test Both Happy & Error Paths**: Include validation tests
4. **Use Fixtures**: Leverage `adminDomainTrainingPage` fixture
5. **Keep Tests Independent**: Each test should be runnable alone
6. **Clear Test Names**: Describe what the test validates
7. **Use await Properly**: Wait for elements before interacting

## Test Maintenance

When updating Domain Training features:
1. Update Page Object Model locators if UI changes
2. Add new test cases for new functionality
3. Update API endpoint tests if endpoints change
4. Run full suite before committing
5. Update this README with new test groups

## CI/CD Integration

Tests are designed for **LOCAL-ONLY execution** to avoid cloud LLM costs:
- Manual startup of services required
- No automatic CI/CD execution
- Perfect for pre-commit validation on development machines

## Sprint References

- **Sprint 45, Feature 45.3**: Domain Management API
- **Sprint 45, Feature 45.10**: Batch Ingestion with Domain Routing
- **Sprint 45, Feature 45.12**: Metric Configuration UI
- **ADR-024**: BGE-M3 Embeddings
- **ADR-033**: AegisLLMProxy Multi-Cloud
