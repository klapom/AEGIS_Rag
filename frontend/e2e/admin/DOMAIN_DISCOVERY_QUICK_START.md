# Domain Discovery API E2E Tests - Quick Start Guide

## Files Created
- **Test Suite**: `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/admin/domain-discovery-api.spec.ts`
- **Documentation**: `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/admin/DOMAIN_DISCOVERY_E2E_TESTS.md`
- **Quick Start**: `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/admin/DOMAIN_DISCOVERY_QUICK_START.md` (this file)

## Total Test Cases: 17

### Test Coverage Summary

| Category | Tests | Details |
|----------|-------|---------|
| Endpoint Availability | 1 | TC-46.4.1 - GET returns 405 |
| File Upload | 1 | TC-46.4.2 - Single TXT file |
| Multi-File Processing | 1 | TC-46.4.3 - Multiple documents |
| Input Validation | 5 | TC-46.4.4-7.8 - File count/size/format |
| Response Schema | 1 | TC-46.4.5 - JSON structure validation |
| Error Handling | 3 | TC-46.4.11-13 - Error scenarios & Ollama unavailable |
| Semantic Validation | 1 | TC-46.4.14 - Content relevance |
| Determinism | 1 | TC-46.4.15 - Consistency checks |
| Authentication | 2 | TC-46.4.16-17 - Auth required & token acceptance |
| **Total** | **17** | |

## Running Tests

### Prerequisites
Before running any tests, ensure these services are available:

```bash
# Terminal 1: Backend API (required)
cd /home/admin/projects/aegisrag/AEGIS_Rag
poetry run python -m src.api.main

# Terminal 2: Frontend (required)
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend
npm run dev

# Terminal 3: Ollama (optional but recommended)
ollama serve
ollama pull llama3.2:8b
```

### Running All Tests

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend

# Run all domain discovery tests
npx playwright test e2e/admin/domain-discovery-api.spec.ts

# Run with verbose output
npx playwright test e2e/admin/domain-discovery-api.spec.ts -v

# Run with UI (interactive mode)
npx playwright test e2e/admin/domain-discovery-api.spec.ts --ui
```

### Running Specific Test Cases

```bash
# Run single test by name
npx playwright test -g "TC-46.4.1"

# Run endpoint tests only
npx playwright test -g "Endpoint exists"

# Run validation tests only
npx playwright test -g "validation"

# Run authentication tests only
npx playwright test -g "Auth"
```

### Running with Different Browsers

```bash
# Chromium (default)
npx playwright test e2e/admin/domain-discovery-api.spec.ts --project=chromium

# Firefox
npx playwright test e2e/admin/domain-discovery-api.spec.ts --project=firefox

# WebKit (Safari)
npx playwright test e2e/admin/domain-discovery-api.spec.ts --project=webkit

# All browsers
npx playwright test e2e/admin/domain-discovery-api.spec.ts
```

### Debugging Failed Tests

```bash
# Enable debug mode (opens inspector)
PWDEBUG=1 npx playwright test e2e/admin/domain-discovery-api.spec.ts

# Run single test with debug
PWDEBUG=1 npx playwright test -g "TC-46.4.2"

# Generate trace for debugging
npx playwright test e2e/admin/domain-discovery-api.spec.ts --trace on

# View trace
npx playwright show-trace trace.zip
```

### Viewing Test Results

```bash
# Generate HTML report
npx playwright test e2e/admin/domain-discovery-api.spec.ts

# View report
npx playwright show-report

# Show test report in default browser
npx playwright show-report test-results/
```

## Expected Behavior

### With All Services Available
```
✓ All 17 tests pass
- Valid file uploads return 200 with domain suggestions
- Invalid inputs return 400/422 with error details
- Auth tests verify protected route behavior
- Processing time: 1-2 minutes for full suite
```

### With Ollama Down
```
✓ 12 tests pass (validation, structure, error handling)
⊙ 5 tests return 503 (expected behavior)
- Upload validation tests still pass
- Error handling tests validate 503 responses
- Auth tests verify token acceptance
- Processing time: 30-45 seconds
```

### With Backend Down
```
✗ All tests fail with connection errors
- Indicates backend service not running
- Check that API server is started
- Verify http://localhost:8000/health returns 200
```

## Key Test Cases Explained

### TC-46.4.1: Endpoint Exists
- **What**: Verifies endpoint only accepts POST, rejects GET with 405
- **Why**: Security - confirm only expected HTTP method works
- **Expected**: GET → 405 Method Not Allowed

### TC-46.4.2: Valid File Upload
- **What**: Upload single TXT file with technical content
- **Why**: Main feature - domain auto-discovery from documents
- **Expected**: 200 OK with DomainSuggestion JSON or 503 if Ollama down

### TC-46.4.5: Response Schema
- **What**: Validates response structure matches API contract
- **Why**: Client compatibility - ensure frontend can parse response
- **Expected**: All required fields present, correct types, valid ranges

### TC-46.4.13: Ollama Unavailable
- **What**: Tests graceful handling when LLM service is down
- **Why**: Robustness - handle service degradation gracefully
- **Expected**: 503 with "Ollama service unavailable" message

### TC-46.4.16-17: Authentication
- **What**: Verifies endpoint requires valid authentication
- **Why**: Security - admin endpoints must be protected
- **Expected**: Unauthenticated → 401/403, Authenticated → 200 or LLM error

## Troubleshooting

### Tests Timeout (>30s)
**Problem**: Tests hang waiting for response
**Solution**:
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not running:
ollama serve
```

### 503 Service Unavailable
**Problem**: Tests return 503 errors
**Solution**: This is expected if Ollama not available - tests validate this gracefully
```bash
# To avoid 503:
ollama serve
```

### 401/403 Authentication Errors
**Problem**: Auth tests fail with authentication errors
**Solution**:
```bash
# Verify auth fixtures loaded
grep -n "setupAuthMocking" e2e/fixtures/index.ts

# Check test uses authenticatedPage fixture
grep -n "authenticatedPage" e2e/admin/domain-discovery-api.spec.ts
```

### Connection Refused
**Problem**: Can't connect to backend or Ollama
**Solution**:
```bash
# Check services running
curl http://localhost:8000/health        # Backend
curl http://localhost:5179              # Frontend
curl http://localhost:11434/api/tags    # Ollama

# Start any missing services
```

### Temp Files Not Cleaned Up
**Problem**: /tmp/aegis-e2e-* files accumulate
**Solution**:
```bash
# Manual cleanup
rm /tmp/aegis-e2e-* 2>/dev/null

# Or let tests clean automatically (try/finally blocks)
npx playwright test e2e/admin/domain-discovery-api.spec.ts
```

## Performance Metrics

| Test | Expected Time | Notes |
|------|----------------|-------|
| TC-46.4.1 | <1s | No file processing |
| TC-46.4.2 | 5-15s | Includes LLM analysis |
| TC-46.4.3 | 5-15s | Single file tested |
| TC-46.4.4 | <1s | Validation only |
| TC-46.4.5 | 5-15s | Includes LLM |
| TC-46.4.6-8 | 5-15s | Includes LLM |
| TC-46.4.9-10 | 5-15s | Includes LLM |
| TC-46.4.11-13 | <2s | Validation/error paths |
| TC-46.4.14 | 5-15s | Includes LLM |
| TC-46.4.15 | 10-30s | Two uploads (2x LLM) |
| TC-46.4.16-17 | 5-15s | Auth + LLM |
| **Total** | **60-120s** | ~1-2 minutes for full run |

## Test Examples

### Minimal Test Run
```bash
# Just verify endpoint exists (no LLM)
npx playwright test -g "TC-46.4.1"
# Expected: <1 second, 1 test passed
```

### Quick Validation
```bash
# Endpoint + validation + error handling (no LLM)
npx playwright test -g "(TC-46.4.1|TC-46.4.4|TC-46.4.11|TC-46.4.12)"
# Expected: <5 seconds, 4 tests passed
```

### Full Suite
```bash
# All tests including LLM
npx playwright test e2e/admin/domain-discovery-api.spec.ts
# Expected: 60-120s, 17 tests passed/skipped
```

## Integration with Development Workflow

### Before Committing Code
```bash
# Run quick smoke tests
npx playwright test -g "TC-46.4.1"

# Run full suite before pushing
npx playwright test e2e/admin/domain-discovery-api.spec.ts
```

### Debugging API Issues
```bash
# Run specific test with debug mode
PWDEBUG=1 npx playwright test -g "TC-46.4.2"

# Inspect requests/responses
curl -v -X POST \
  -F "files=@test.txt" \
  http://localhost:8000/api/v1/admin/domains/discover
```

### Recording New Tests
```bash
# Use Playwright inspector to create new test
npx playwright codegen http://localhost:5179

# Modify and save to domain-discovery-api.spec.ts
```

## CI/CD Notes

**Current Status**: LOCAL EXECUTION ONLY
- Tests require running Ollama (LLM service)
- Cloud LLM costs would be high
- Not integrated into CI/CD pipeline
- Manual execution recommended

**To Enable CI/CD**:
1. Set up self-hosted Ollama server
2. Or use test mode that mocks LLM responses
3. Update test environment variables
4. Configure test timeout (currently 30s)

## Related Documentation

- **Full Docs**: [DOMAIN_DISCOVERY_E2E_TESTS.md](./DOMAIN_DISCOVERY_E2E_TESTS.md)
- **Backend API**: [domain_discovery.py](../../src/api/v1/admin/domain_discovery.py)
- **Playwright**: https://playwright.dev/docs/intro
- **Sprint 46**: [SPRINT_46.md](../../docs/sprints/SPRINT_46.md)

## Support

For test issues:
1. Check prerequisites are running
2. Review test output with `-v` flag
3. Use `PWDEBUG=1` for interactive debugging
4. Check documentation above
5. Review backend logs for errors

---

**Last Updated**: 2025-12-15
**Test Count**: 17 tests
**Status**: Ready for execution
