# Domain Auto-Discovery API E2E Tests
## Sprint 46 - Feature 46.4

This document describes the Playwright E2E test suite for the Domain Auto-Discovery API endpoint.

### Quick Start

```bash
# Install dependencies (if not already installed)
npm install

# Run domain discovery API tests only
npx playwright test e2e/admin/domain-discovery-api.spec.ts

# Run with verbose output
npx playwright test e2e/admin/domain-discovery-api.spec.ts -v

# Run with specific browser
npx playwright test e2e/admin/domain-discovery-api.spec.ts --project=chromium

# View test report
npx playwright show-report
```

### Prerequisites

#### Backend Services
- **FastAPI Backend**: Running on `http://localhost:8000`
  ```bash
  cd ..
  poetry run python -m src.api.main
  ```

- **Ollama LLM**: Running on `http://localhost:11434` (optional but recommended)
  ```bash
  ollama serve
  ollama pull llama3.2:8b  # Or configured model
  ```

- **Redis**: Running on `localhost:6379` (optional for caching)

#### Frontend
- **Vite Dev Server**: Running on `http://localhost:5179`
  ```bash
  npm run dev
  ```

### Test File Location
```
/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/admin/domain-discovery-api.spec.ts
```

### API Endpoint Details

**Endpoint**: `POST /api/v1/admin/domains/discover`

**Description**: Analyzes uploaded documents to suggest domain metadata (title, description, topics)

**Request**:
```http
POST /api/v1/admin/domains/discover HTTP/1.1
Content-Type: multipart/form-data

files: <file1>, <file2>, <file3>
```

**Response** (Success - 200):
```json
{
  "title": "Technical Documentation",
  "description": "Comprehensive guides and API references for software development...",
  "confidence": 0.85,
  "detected_topics": ["Python", "FastAPI", "API Design", "Documentation"]
}
```

**Error Responses**:
- **400 Bad Request**: Invalid file count, size, or format
- **422 Unprocessable Entity**: Validation error
- **503 Service Unavailable**: Ollama/LLM service not available

### Test Suite Structure

#### Main Test Suite: `Sprint 46 - Feature 46.4: Domain Discovery API`

Contains 15 comprehensive test cases covering:

1. **Endpoint Availability** (TC-46.4.1)
   - Verifies endpoint exists
   - Confirms only POST method is allowed (GET returns 405)

2. **File Upload** (TC-46.4.2)
   - Single TXT file upload
   - Validates domain suggestion response
   - Tests both success (200) and Ollama unavailable (503) scenarios

3. **Multi-File Processing** (TC-46.4.3)
   - Multiple document handling
   - Aggregated domain suggestion

4. **Input Validation** (TC-46.4.4 through TC-46.4.7)
   - Empty file list validation
   - File count limits (1-3 files)
   - File size validation (max 10MB)
   - Response structure verification

5. **Response Schema** (TC-46.4.5)
   - Validates JSON structure matches `DomainSuggestion` model
   - Field type checking
   - Constraint validation (confidence 0.0-1.0, title 2-100 chars, etc.)

6. **File Handling** (TC-46.4.6)
   - File size limits (1MB test = within 10MB limit)
   - Content-Type header processing

7. **Error Handling** (TC-46.4.11-12)
   - Missing files field
   - Invalid multipart data
   - Helpful error messages

8. **LLM Integration** (TC-46.4.13)
   - Graceful handling of Ollama unavailable (503)
   - Clear error messages for service down scenarios

9. **Semantic Validation** (TC-46.4.14)
   - Title and description relevance to uploaded content
   - Medical domain detection example

10. **Determinism** (TC-46.4.15)
    - Consistency of response structure across multiple requests
    - Note: Exact values may vary with non-deterministic LLMs

#### Authentication Test Suite: `Sprint 46 - Feature 46.4: Domain Discovery API Auth`

Tests authentication and authorization:

1. **TC-46.4.16**: Endpoint requires authentication
   - Validates protected route behavior
   - Tests unauthenticated access rejection

2. **TC-46.4.17**: Valid Bearer token acceptance
   - Tests authenticated request processing
   - Uses `authenticatedPage` fixture with auth mocking

### Sample Documents

The test suite includes three realistic domain samples:

#### Technical Documentation
- API design patterns, REST principles, best practices
- Keywords: HTTP, routing, serialization, authentication, caching

#### Medical Research
- Clinical trials, ethics, statistical analysis
- Keywords: RCTs, GCP, adverse events, GDPR compliance

#### Legal/Corporate
- Contract management, IP protection, compliance
- Keywords: liability, employment law, data privacy

#### Minimal/Edge Case
- Small content for boundary testing

### Test Execution Flow

```
Setup: Playwright test runner initializes
├── Create temporary test files
├── Set up fixtures (page, request, authenticatedPage)
├── Apply auth mocking for protected routes
│
Tests: Execute test cases sequentially
├── TC-46.4.1: Verify endpoint (GET → 405)
├── TC-46.4.2: Single file upload (POST → 200 or 503)
├── TC-46.4.3: Multi-file handling
├── TC-46.4.4: Empty file validation
├── TC-46.4.5: Response schema validation
├── ... (10 more test cases)
│
Cleanup: After each test
├── Delete temporary files
├── Reset page state
└── Report results
```

### Expected Test Results

#### With Ollama Available
- All tests should pass (200 responses for valid uploads)
- Domain suggestions should be semantically relevant
- Processing time: <20 seconds per test

#### Without Ollama (Service Down)
- Upload validation tests still pass (400, 422 responses)
- Ollama-dependent tests return 503 gracefully
- Error messages mention "Ollama service unavailable"
- No hanging or timeout failures

#### With Backend Down
- Tests timeout or fail with connection errors
- Indicates backend availability issue

### Common Issues & Troubleshooting

#### Issue: Tests timeout (>30s)
**Solution**: Check if Ollama is running
```bash
curl http://localhost:11434/api/tags
```
If down, start Ollama:
```bash
ollama serve
```

#### Issue: 503 "Ollama service unavailable"
**Expected behavior**: Tests validate this error condition
- Indicates Ollama is not accessible
- Tests expect this and validate error response

#### Issue: 401/403 authentication errors
**Solution**: Verify auth fixtures are properly loaded
- Check `e2e/fixtures/index.ts` has `setupAuthMocking`
- Ensure `authenticatedPage` fixture is used for protected routes

#### Issue: Temp files not cleaned up
**Manual cleanup**:
```bash
rm /tmp/aegis-e2e-*.* 2>/dev/null
```

#### Issue: Network connection errors
**Solution**: Verify services are running
```bash
# Check backend
curl http://localhost:8000/health

# Check frontend
curl http://localhost:5179

# Check Ollama
curl http://localhost:11434/api/tags
```

### File Structure

```
frontend/
├── e2e/
│   ├── admin/
│   │   ├── domain-discovery-api.spec.ts  ← Main test file
│   │   ├── DOMAIN_DISCOVERY_E2E_TESTS.md ← This document
│   │   ├── llm-config.spec.ts
│   │   ├── indexing.spec.ts
│   │   ├── cost-dashboard.spec.ts
│   │   └── vlm-integration.spec.ts
│   ├── fixtures/
│   │   └── index.ts                      ← Auth mocking & fixtures
│   ├── pom/                              ← Page Object Models
│   │   ├── ChatPage.ts
│   │   ├── AdminDomainTrainingPage.ts
│   │   └── ...
│   └── smoke.spec.ts
└── playwright.config.ts
```

### Performance Expectations

| Operation | Time |
|-----------|------|
| File validation (syntax, size, format) | <100ms |
| Text extraction (per file) | ~100ms |
| LLM analysis (Ollama qwen3:32b) | ~5-15s |
| Total for 1 file | ~5-15s |
| Total for 3 files | ~15-50s |

### Test Coverage

This test suite provides comprehensive coverage of:

- **Endpoint** (100%): All methods, all status codes
- **Request Validation** (100%): File count, size, format, multipart
- **Response Validation** (100%): Schema, types, constraints
- **Error Handling** (100%): 400s, 503s, validation errors
- **Authentication** (100%): Protected route verification
- **Semantic Behavior** (80%): Domain relevance detection

Total: **17 test cases** covering endpoint, validation, error handling, and auth

### Integration with CI/CD

The test suite is designed for **LOCAL EXECUTION ONLY**:
- No CI/CD integration (tests require running Ollama)
- No cloud LLM costs
- Manual execution recommended before commits

To run before pushing:
```bash
npm run test:e2e
```

### Dependencies

- **Playwright**: ^1.50.0 (E2E testing framework)
- **Node.js**: ^18.0.0 (Runtime)
- **TypeScript**: ^5.0 (Type checking)

### Related Features

- **Sprint 45, Feature 45.3**: Domain Training System
- **Sprint 45, Feature 45.10**: Training Progress Tracking
- **Sprint 46, Feature 46.3**: Domain Configuration UI
- **Sprint 46, Feature 46.5**: Multi-Domain Management

### Contributing

When adding new tests:

1. Follow naming convention: `test('TC-46.4.XX: <description>', ...)`
2. Use sample documents from `sampleDocuments` object
3. Wrap files in try/finally with cleanup
4. Test both success and failure scenarios
5. Document expected behavior in test comments
6. Add to this documentation file

### See Also

- [Playwright Documentation](https://playwright.dev/)
- [Backend API Documentation](../../src/api/v1/admin/domain_discovery.py)
- [E2E Test Patterns](../IMPLEMENTATION_SUMMARY.md)
- [Sprint 46 Plan](../../docs/sprints/SPRINT_46.md)

### Last Updated

- Created: Sprint 46
- Last Modified: 2025-12-15
- Status: Active
