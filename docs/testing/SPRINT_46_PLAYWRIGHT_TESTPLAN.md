# Sprint 46 Playwright E2E Test Plan

**Created:** 2025-12-15
**Sprint:** 46 - Conversation UI & Domain Auto-Discovery
**Test Framework:** Playwright + Page Object Model

---

## Test Scope

| Feature | Component | Priority | Test Cases |
|---------|-----------|----------|------------|
| 46.1 | ConversationView | P0 | 8 tests |
| 46.2 | ReasoningPanel | P0 | 6 tests |
| 46.3 | SessionSidebar Fix | P0 | 3 tests (already done) |
| 46.4 | Domain Discovery API | P1 | 5 tests |
| 46.5 | DomainAutoDiscovery UI | P1 | 7 tests |
| 46.7 | Admin UI Polish | P2 | 4 tests |
| 46.8 | AdminDashboard | P1 | 8 tests |
| **Total** | | | **41 tests** |

---

## Feature 46.1: Chat-Style ConversationView

### Test Cases

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| TC-46.1.1 | Verify ConversationView renders | Component mounts, message container visible |
| TC-46.1.2 | Verify message order | Oldest messages at top, newest at bottom |
| TC-46.1.3 | Verify user message styling | Right-aligned, blue background |
| TC-46.1.4 | Verify assistant message styling | Left-aligned, gray background, avatar |
| TC-46.1.5 | Verify input fixed at bottom | Input always visible at viewport bottom |
| TC-46.1.6 | Verify auto-scroll | New messages auto-scroll into view |
| TC-46.1.7 | Verify send functionality | Enter key and button both send messages |
| TC-46.1.8 | Verify streaming indicator | Loading dots during response generation |

### Test Data
```typescript
const mockMessages = [
  { id: '1', role: 'user', content: 'Was ist RAG?' },
  { id: '2', role: 'assistant', content: 'RAG steht für Retrieval-Augmented Generation...' },
  { id: '3', role: 'user', content: 'Wie funktioniert das?' },
];
```

---

## Feature 46.2: ReasoningPanel (Transparent Retrieval)

### Test Cases

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| TC-46.2.1 | Verify reasoning button | "Reasoning anzeigen" button on assistant messages |
| TC-46.2.2 | Verify panel expansion | Panel expands on click, shows content |
| TC-46.2.3 | Verify panel collapse | Panel collapses on second click |
| TC-46.2.4 | Verify intent display | Intent type and confidence shown |
| TC-46.2.5 | Verify retrieval steps | All backend queries displayed with timing |
| TC-46.2.6 | Verify tools used | Tool usage section visible |

### Mock SSE Events
```typescript
const mockReasoningData = {
  intent: { type: 'factual', confidence: 0.92, reasoning: 'Direct question' },
  retrieval_steps: [
    { step: 1, source: 'qdrant', duration_ms: 45, result_count: 5 },
    { step: 2, source: 'bm25', duration_ms: 12, result_count: 8 },
    { step: 3, source: 'neo4j', duration_ms: 67, result_count: 3 },
    { step: 4, source: 'rrf_fusion', duration_ms: 2, result_count: 10 },
  ],
  tools_used: [],
};
```

---

## Feature 46.4: Domain Auto-Discovery API

### Test Cases

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| TC-46.4.1 | API endpoint exists | GET /api/v1/admin/domains/discover returns 405 (POST only) |
| TC-46.4.2 | Valid file upload | Returns DomainSuggestion with title, description |
| TC-46.4.3 | Max file count validation | >3 files returns 400 error |
| TC-46.4.4 | Empty file validation | Empty file returns 400 error |
| TC-46.4.5 | Response format | JSON with title, description, confidence, detected_topics |

### Test Files
```
test-files/
├── sample.txt (valid)
├── sample.md (valid)
├── empty.txt (invalid - empty)
└── large.pdf (invalid - >10MB, optional)
```

---

## Feature 46.5: DomainAutoDiscovery Frontend

### Test Cases

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| TC-46.5.1 | Render drag-drop area | Upload zone visible with instructions |
| TC-46.5.2 | File selection | Clicking opens file dialog |
| TC-46.5.3 | File type validation | Rejects unsupported formats (exe, etc.) |
| TC-46.5.4 | Max files validation | Shows error when >3 files selected |
| TC-46.5.5 | Analyze button | Triggers API call, shows loading state |
| TC-46.5.6 | Suggestion display | Shows title, description, confidence after analysis |
| TC-46.5.7 | Edit and accept | Can modify suggestion before accepting |

### UI Selectors
```typescript
const selectors = {
  dropZone: '[data-testid="domain-upload-zone"]',
  fileInput: 'input[type="file"]',
  analyzeButton: '[data-testid="analyze-button"]',
  suggestionTitle: '[data-testid="suggested-title"]',
  suggestionDesc: '[data-testid="suggested-description"]',
  acceptButton: '[data-testid="accept-button"]',
};
```

---

## Feature 46.7: Admin UI Polish

### Test Cases

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| TC-46.7.1 | Compact headers | Headers use text-lg instead of text-xl |
| TC-46.7.2 | Reduced padding | Cards use p-4 instead of p-6 |
| TC-46.7.3 | Smaller icons | Icons use w-4 h-4 instead of w-5 h-5 |
| TC-46.7.4 | Visual consistency | No visual regressions |

### Visual Regression
- Screenshot comparison before/after
- Check computed styles via JavaScript

---

## Feature 46.8: Admin Dashboard Consolidation

### Test Cases

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| TC-46.8.1 | Dashboard route | /admin loads AdminDashboard |
| TC-46.8.2 | Domain section renders | Shows domain list with status |
| TC-46.8.3 | Indexing section renders | Shows indexing stats |
| TC-46.8.4 | Settings section renders | Shows LLM/embedding config |
| TC-46.8.5 | Section collapse | Clicking header collapses content |
| TC-46.8.6 | Section expand | Clicking again expands content |
| TC-46.8.7 | Navigation links | Quick links navigate correctly |
| TC-46.8.8 | Data loading | Shows loading state, then data |

### Page Object Model
```typescript
class AdminDashboardPage extends BasePage {
  // Sections
  domainSection = '[data-testid="domain-section"]';
  indexingSection = '[data-testid="indexing-section"]';
  settingsSection = '[data-testid="settings-section"]';

  // Actions
  async toggleSection(name: string) { ... }
  async navigateToDetail(section: string) { ... }
}
```

---

## Test Execution Plan

### Prerequisites
1. Backend running: `poetry run uvicorn src.api.main:app --port 8000`
2. Frontend running: `npm run dev` (port 5179)
3. Services: Qdrant, Neo4j, Redis online
4. Ollama: Running with model loaded

### Execution Order
1. Smoke tests (verify infrastructure)
2. Admin Dashboard tests (46.8)
3. Conversation UI tests (46.1, 46.2)
4. Domain Discovery tests (46.4, 46.5)
5. Admin UI Polish tests (46.7)

### Commands
```bash
# Run all Sprint 46 tests
npm run test:e2e -- --grep "Sprint 46"

# Run specific feature
npm run test:e2e -- frontend/e2e/sprint46/*.spec.ts

# Run with UI
npm run test:e2e -- --ui
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| SSE streaming timeout | Increase timeout to 30s |
| LLM response variability | Mock API responses for deterministic tests |
| Backend not running | Add health check before test suite |
| File upload security | Use temp files, cleanup after tests |

---

## Success Criteria

- [ ] All 41 test cases pass
- [ ] No visual regressions
- [ ] Test execution time < 5 minutes
- [ ] Coverage of all new components
