# Sprint 36 E2E Tests - Quick Start Guide

## Overview

Complete E2E test suite for Admin LLM Configuration page (Feature 36.3).

**Files Created:**
- 1 Page Object Model (POM)
- 2 TypeScript test specs (70+ tests)
- 1 Python test suite (17 tests)
- 1 Fixture integration
- 2 Documentation files

**Total Lines of Code:** 1,633 LOC (tests + POM)

## Quick Commands

### Run All Tests
```bash
# TypeScript E2E Tests
npx playwright test frontend/e2e/admin/llm-config.spec.ts
npx playwright test frontend/e2e/admin/vlm-integration.spec.ts

# Python E2E Tests
pytest tests/e2e/test_admin_llm_config_e2e.py -v

# All together
npx playwright test frontend/e2e/admin/llm-config.spec.ts && \
npx playwright test frontend/e2e/admin/vlm-integration.spec.ts && \
pytest tests/e2e/test_admin_llm_config_e2e.py -v
```

### Run Specific Test
```bash
# TypeScript - run by name
npx playwright test -g "should save configuration to localStorage"

# TypeScript - run by category
npx playwright test llm-config.spec.ts -g "Persistence"

# Python - run specific class
pytest tests/e2e/test_admin_llm_config_e2e.py::TestAdminLLMConfigE2E -v

# Python - run specific test
pytest tests/e2e/test_admin_llm_config_e2e.py::TestAdminLLMConfigE2E::test_llm_config_page_loads -v
```

### Run with Options
```bash
# Headed browser (see what's happening)
npx playwright test frontend/e2e/admin/llm-config.spec.ts --headed

# Debug mode
npx playwright test frontend/e2e/admin/llm-config.spec.ts --debug

# Specific browser
npx playwright test frontend/e2e/admin/llm-config.spec.ts --project=chromium

# Slow motion (500ms delay)
npx playwright test frontend/e2e/admin/llm-config.spec.ts --headed --project=chromium -g "persistence" --slow-mo=500
```

## File Locations

### Page Object Model
```
frontend/e2e/pom/AdminLLMConfigPage.ts (227 lines)
```
**Key Methods:**
- `goto()` - Navigate to page
- `selectModel(useCase, modelId)` - Select model
- `saveConfig()` - Save to localStorage
- `getStoredConfig()` - Retrieve config
- `getAvailableModels(useCase)` - Get options

### TypeScript Tests

**1. Admin LLM Config Tests**
```
frontend/e2e/admin/llm-config.spec.ts (439 lines, 30+ tests)
```
**Test Groups:**
- Basic Functionality (10 tests)
- Navigation (3 tests)
- Dark Mode (2 tests)
- Accessibility (3 tests)
- Responsive Design (3 tests)

**2. VLM Integration Tests**
```
frontend/e2e/admin/vlm-integration.spec.ts (422 lines, 20+ tests)
```
**Test Groups:**
- VLM Backend Config (5 tests)
- Admin Integration (4 tests)
- Cost Tracking (3 tests)
- Model Capabilities (2 tests)
- Fallback Strategy (3 tests)
- UI Integration (3 tests)

### Python Tests
```
tests/e2e/test_admin_llm_config_e2e.py (545 lines, 17 tests)
```
**Test Classes:**
- `TestAdminLLMConfigE2E` (12 tests)
- `TestVLMIntegrationE2E` (5 tests)

### Fixture Integration
```
frontend/e2e/fixtures/index.ts
```
**Added:**
- Import AdminLLMConfigPage
- adminLLMConfigPage fixture type
- adminLLMConfigPage fixture implementation

### Documentation
```
frontend/e2e/admin/SPRINT_36_E2E_TESTS.md (comprehensive guide)
frontend/e2e/admin/SPRINT_36_QUICK_START.md (this file)
```

## What's Tested

### Frontend LLM Configuration Page

✅ **Page Loading & Display**
- Page loads correctly
- All 6 use case selectors visible
- Model dropdowns present and enabled

✅ **Model Selection**
- Can select different models
- Multiple selections work
- Rapid changes handled

✅ **Data Persistence**
- Saves to localStorage
- Persists on reload
- Survives navigation

✅ **Vision Model Filtering**
- Vision models only in VLM dropdown
- Text models only in text use cases
- Filters work correctly

✅ **Navigation**
- Via sidebar link
- Direct URL access
- Proper routing

✅ **User Interface**
- Dark mode support
- Responsive design (mobile/tablet/desktop)
- Provider badges display
- All buttons clickable

✅ **Accessibility**
- data-testid attributes present
- Keyboard navigation works
- Focus management correct

✅ **VLM Integration**
- Local VLM default
- Cloud VLM switching
- Independent from text models
- Persistence across sessions

✅ **Cost Tracking**
- Indicates zero cost for local
- Shows cost info for cloud
- Dashboard integration

## Prerequisites

### Frontend E2E Tests
```bash
# Terminal 1: Start frontend
npm run dev

# Terminal 2: Run tests
npx playwright test frontend/e2e/admin/llm-config.spec.ts
```

**Requirements:**
- Frontend running on http://localhost:5173 (or configured port)
- Playwright browsers installed: `npx playwright install`
- No backend required (uses localStorage)

### Python E2E Tests
```bash
# Install dependencies (if needed)
pip install pytest pytest-asyncio playwright
playwright install

# Run tests
pytest tests/e2e/test_admin_llm_config_e2e.py -v
```

**Requirements:**
- Python 3.8+
- Frontend running on http://localhost:5173
- pytest and playwright installed

## Test Statistics

| Metric | Value |
|--------|-------|
| Total Tests | 70+ |
| TypeScript Tests | 50+ |
| Python Tests | 17 |
| Lines of Test Code | 1,633 |
| POM Methods | 15+ |
| Use Cases Covered | 6 |
| Test Groups | 15+ |
| Page Scenarios | 5 |
| VLM Scenarios | 5 |

## Common Test Scenarios

### Scenario 1: Basic Configuration
```typescript
test('should save configuration to localStorage', async ({ adminLLMConfigPage }) => {
  const dropdown = adminLLMConfigPage.answerGenerationDropdown;
  await dropdown.selectOption({ index: 1 });
  await adminLLMConfigPage.saveConfig();
  await adminLLMConfigPage.waitForSaveSuccess();

  const config = await adminLLMConfigPage.getStoredConfig();
  expect(config).not.toBeNull();
  expect(config.length).toBe(6);
});
```

### Scenario 2: VLM Persistence
```typescript
test('should persist VLM selection across reload', async ({ adminLLMConfigPage, page }) => {
  const targetModel = 'ollama/qwen3-vl:32b';
  await adminLLMConfigPage.selectModel('vision_vlm', targetModel);
  await adminLLMConfigPage.saveConfig();

  await page.reload();
  const selected = await adminLLMConfigPage.getSelectedModel('vision_vlm');
  expect(selected).toBe(targetModel);
});
```

### Scenario 3: Vision Filtering
```python
async def test_vision_models_filtered_for_vlm_use_case():
    """Test that only vision-capable models appear for VLM."""
    # Get all options
    options = await vlm_dropdown.locator("option").all_text_contents()

    # Check for vision models
    vision_options = [opt for opt in options if 'VL' in opt or 'Vision' in opt]
    assert len(vision_options) > 0
```

## Debugging Tests

### See what's happening (headed mode)
```bash
npx playwright test llm-config.spec.ts --headed
```

### Step through test
```bash
npx playwright test llm-config.spec.ts --debug
```

### Slow motion (500ms delay between actions)
```bash
npx playwright test llm-config.spec.ts --slow-mo=500 --headed
```

### Check selector in browser console
```javascript
// In browser console while test runs
document.querySelector('[data-testid="llm-config-page"]')
document.querySelector('[data-testid="model-dropdown-intent_classification"]')
```

## Troubleshooting

### Tests fail with "Port 5173 not accessible"
**Solution:** Ensure frontend is running
```bash
npm run dev  # In another terminal
```

### localStorage tests fail
**Solution:** Check that test is clearing localStorage properly
```typescript
// This should be in beforeEach
await adminLLMConfigPage.clearStoredConfig();
```

### Vision models not showing
**Solution:** Check AdminLLMConfigPage.tsx filtering logic
```typescript
const availableModels = getFilteredModels(useCaseConfig.useCase);
// Should filter by requiresVision and capabilities
```

### Tests timeout
**Solution:** Increase timeout or check frontend responsiveness
```typescript
await expect(element).toBeVisible({ timeout: 15000 });
```

## Next Steps

1. **Run Full Test Suite**
   ```bash
   npm run dev &
   npx playwright test frontend/e2e/admin/
   pytest tests/e2e/test_admin_llm_config_e2e.py -v
   ```

2. **Verify All Tests Pass**
   - Fix any failures
   - Document issues found

3. **Add to CI/CD**
   - Update GitHub Actions
   - Add test step to workflow

4. **Backend Integration** (Future)
   - Create `/api/v1/admin/llm/config` endpoint
   - Replace localStorage with API calls
   - Add backend E2E tests

## Support

- **TypeScript Tests:** See `frontend/e2e/admin/SPRINT_36_E2E_TESTS.md`
- **Python Tests:** See test docstrings in `tests/e2e/test_admin_llm_config_e2e.py`
- **POM Methods:** See comments in `frontend/e2e/pom/AdminLLMConfigPage.ts`
- **Feature Spec:** Sprint 36 Feature 36.3 (8 SP)

---

**Created:** 2025-12-05
**Testing Agent:** Haiku 4.5
**Total Test Coverage:** 70+ comprehensive E2E tests
