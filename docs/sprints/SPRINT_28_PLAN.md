# Sprint 28 Plan: Frontend Integration & Performance

**Sprint:** 28 (Frontend Integration + Performance Testing)
**Target Duration:** 3-4 days
**Planned Story Points:** 18 SP
**Status:** 🔄 PLANNING

---

## Sprint Goal

Complete the frontend integration for Sprint 27 backend features (Follow-up Questions, Source Citations) and establish production readiness through performance testing and settings management.

---

## Sprint Objectives

1. **Frontend Integration (8 SP):** Complete UI for backend features from Sprint 27
2. **Settings Management (5 SP):** Implement user settings page and preferences
3. **Performance Testing (3 SP):** Load/stress testing and memory profiling
4. **Documentation (2 SP):** ADRs, architecture updates, API docs refresh

---

## Feature Breakdown

### Feature 28.1: Follow-up Questions Frontend ✨ (3 SP)

**Priority:** P0 (Critical - completes Feature 27.5)
**Complexity:** Medium
**Dependencies:** Feature 27.5 (Follow-up Questions Backend) ✅

**Scope:**
- Display follow-up questions below answer in StreamingAnswer
- Clickable questions trigger new query
- Loading states during question generation
- Empty state handling (no questions available)
- Error handling (generation failed)

**Implementation:**

1. **FollowUpQuestions Component** (`frontend/src/components/chat/FollowUpQuestions.tsx`)
   ```typescript
   interface FollowUpQuestionsProps {
     sessionId: string;
     onQuestionClick: (question: string) => void;
   }

   export function FollowUpQuestions({ sessionId, onQuestionClick }: FollowUpQuestionsProps) {
     // Fetch questions from /api/v1/chat/sessions/{sessionId}/followup-questions
     // Display as clickable cards
     // Handle loading/error states
   }
   ```

2. **Integration in StreamingAnswer**
   - Position: Below answer content, above metadata
   - Only display when streaming complete
   - Auto-fetch questions when answer finishes

3. **API Client**
   - Add `getFollowUpQuestions(sessionId)` to `src/api/chat.ts`
   - Type: `FollowUpQuestionsResponse = { followup_questions: string[] }`

**Acceptance Criteria:**
- [ ] FollowUpQuestions component renders 3-5 questions
- [ ] Clicking question triggers new query
- [ ] Loading state shows skeleton cards
- [ ] Error state shows "Keine Fragen verfügbar"
- [ ] TypeScript build: 0 errors
- [ ] E2E tests: 100% pass rate maintained

**Testing:**
- Unit tests: FollowUpQuestions component (5 tests)
- Integration test: Full flow from answer → questions → new query
- E2E test: User clicks follow-up question, sees new answer

**UI/UX:**
- Cards layout (horizontal scroll on mobile, grid on desktop)
- Hover effect: subtle shadow, cursor pointer
- Question icon prefix (?) for clarity
- Perplexity-inspired styling (clean, minimalist)

---

### Feature 28.2: Source Citations Frontend 📚 (3 SP)

**Priority:** P0 (Critical - completes Feature 27.10)
**Complexity:** Medium
**Dependencies:** Feature 27.10 (Source Citations Backend) ✅

**Scope:**
- Inline [1][2][3] citations in answer text
- Hover to preview source metadata
- Click to scroll to corresponding source card
- Citation numbering matches source order

**Implementation:**

1. **Citation Parser**
   ```typescript
   function parseCitationsInMarkdown(text: string, sources: Source[]): ReactNode {
     // Replace [1] with <Citation sourceId={1} />
     // Map citation numbers to source indices
   }
   ```

2. **Citation Component** (`frontend/src/components/chat/Citation.tsx`)
   ```typescript
   interface CitationProps {
     sourceIndex: number;
     source: Source;
     onClickScrollTo: (sourceId: string) => void;
   }

   export function Citation({ sourceIndex, source, onClickScrollTo }: CitationProps) {
     // Inline superscript number [1]
     // Hover tooltip: source title + snippet
     // Click: scroll to source card
   }
   ```

3. **Integration in StreamingAnswer**
   - Replace ReactMarkdown with custom renderer
   - Parse citations during markdown rendering
   - Link citations to SourceCardsScroll

**Acceptance Criteria:**
- [ ] Citations render as superscript [1][2][3]
- [ ] Hover shows source preview tooltip
- [ ] Click scrolls to source card
- [ ] Citation numbers match source order
- [ ] TypeScript build: 0 errors
- [ ] E2E tests: 100% pass rate maintained

**Testing:**
- Unit tests: Citation component (4 tests)
- Unit tests: parseCitationsInMarkdown (6 tests)
- E2E test: Hover citation, see tooltip
- E2E test: Click citation, scroll to source

**UI/UX:**
- Superscript styling: `[1]` with blue color
- Tooltip: White background, shadow, rounded corners
- Tooltip content: Title (bold) + first 100 chars of text
- Smooth scroll animation to source card

---

### Feature 28.3: Settings Page ⚙️ (5 SP)

**Priority:** P1 (High - user experience)
**Complexity:** High
**Dependencies:** Feature 27.9 (Quick Actions Bar - Settings button) ✅

**Scope:**
- User preferences (theme, language)
- API configuration (Ollama URL, model selection)
- Model selection (local vs cloud)
- Settings persistence (localStorage)
- QuickActionsBar integration

**Implementation:**

1. **Settings Page** (`frontend/src/pages/Settings.tsx`)
   ```typescript
   interface UserSettings {
     theme: 'light' | 'dark' | 'auto';
     language: 'de' | 'en';
     ollamaBaseUrl: string;
     defaultModel: string;
     cloudProvider: 'local' | 'alibaba' | 'openai';
   }

   export function Settings() {
     // Tabbed interface: General, Models, Advanced
     // Form with validation
     // Save to localStorage
     // Apply settings immediately
   }
   ```

2. **Settings Context** (`frontend/src/contexts/SettingsContext.tsx`)
   ```typescript
   export const SettingsContext = createContext<SettingsContextType>({
     settings: defaultSettings,
     updateSettings: (settings: Partial<UserSettings>) => {},
   });
   ```

3. **Navigation**
   - Update Sidebar QuickActionsBar: Enable settings button
   - Route: `/settings`
   - Back button to return to chat

**Sections:**

**General Tab:**
- Theme: Light / Dark / Auto (system)
- Language: Deutsch / English
- Auto-save conversations: Yes / No

**Models Tab:**
- Ollama Base URL (text input with validation)
- Local Models Dropdown (llama3.2:3b, llama3.2:8b, etc.)
- Cloud Provider: Local / Alibaba / OpenAI
- Cloud API Key (password input, masked)

**Advanced Tab:**
- Clear all conversations (danger zone)
- Export conversation history (JSON download)
- Import conversation history (JSON upload)
- Reset to defaults

**Acceptance Criteria:**
- [ ] Settings page accessible from QuickActionsBar
- [ ] All settings persist in localStorage
- [ ] Theme changes apply immediately
- [ ] Model selection updates API calls
- [ ] Validation for URLs and API keys
- [ ] TypeScript build: 0 errors
- [ ] E2E tests: Settings save and load

**Testing:**
- Unit tests: Settings page (8 tests)
- Unit tests: SettingsContext (5 tests)
- E2E test: Change theme, see UI update
- E2E test: Change model, make query, verify backend call

**UI/UX:**
- Tabbed interface (Material-UI style)
- Form inputs with labels and validation
- Save button: Disabled until changes made
- Success toast: "Einstellungen gespeichert"
- Danger zone: Red border, confirmation dialog

---

### Feature 28.4: Performance Testing 🚀 (3 SP)

**Priority:** P1 (High - production readiness)
**Complexity:** Medium
**Dependencies:** None

**Scope:**
- Load testing (50 QPS sustained)
- Stress testing (100 QPS peak)
- Memory profiling with py-spy
- Latency analysis (p50, p95, p99)
- Bottleneck identification

**Implementation:**

1. **Load Testing with Locust** (`tests/performance/locustfile.py`)
   ```python
   from locust import HttpUser, task, between

   class RAGUser(HttpUser):
       wait_time = between(1, 3)

       @task(3)
       def search_query(self):
           self.client.post("/api/v1/search", json={
               "query": "What is LangGraph?",
               "top_k": 5
           })

       @task(1)
       def chat_query(self):
           self.client.post("/api/v1/chat", json={
               "query": "Explain vector databases",
               "session_id": self.session_id
           })
   ```

2. **Test Scenarios**
   - Scenario 1: 50 QPS sustained for 5 minutes (production baseline)
   - Scenario 2: Ramp up from 0 to 100 QPS over 2 minutes (stress test)
   - Scenario 3: 100 QPS sustained for 1 minute (peak capacity)

3. **Memory Profiling**
   ```bash
   py-spy record -o profile.svg -- python -m uvicorn src.api.main:app
   ```

4. **Latency Analysis**
   - Prometheus metrics: `http_request_duration_seconds`
   - Grafana dashboard: p50, p95, p99 latencies
   - Identify slow endpoints (>1s p95)

**Deliverables:**
- Locust test suite (`tests/performance/`)
- Performance report: `docs/performance/SPRINT_28_PERFORMANCE_REPORT.md`
- Memory profile SVG: `docs/performance/memory_profile_sprint_28.svg`
- Grafana dashboard JSON: `config/grafana/performance_dashboard.json`

**Acceptance Criteria:**
- [ ] Load test: 50 QPS sustained with <500ms p95 latency
- [ ] Stress test: 100 QPS peak without crashes
- [ ] Memory profile: <2GB RAM usage at 50 QPS
- [ ] Bottleneck report: Top 3 slow operations identified
- [ ] Recommendations: 3+ optimization suggestions

**Metrics to Track:**
- Request latency (p50, p95, p99)
- Throughput (QPS)
- Error rate (4xx, 5xx)
- Memory usage (RSS, heap)
- Database connection pool usage (Qdrant, Neo4j, Redis)
- LLM token throughput (tokens/second)

---

### Feature 28.5: Documentation Backfill 📝 (2 SP)

**Priority:** P2 (Medium - team alignment)
**Complexity:** Low
**Dependencies:** None

**Scope:**
- Sprint 27 ADRs (3 decisions)
- Architecture diagram updates
- API documentation refresh (OpenAPI)
- TECH_DEBT.md update (5 legacy test failures documented)

**ADRs to Create:**

1. **ADR-034: Perplexity-Inspired UX Features**
   - Context: Sprint 27 introduced follow-up questions, copy button, quick actions
   - Decision: Adopt Perplexity-style UX patterns for better user engagement
   - Status: ACCEPTED
   - Consequences: Consistent UX, higher user satisfaction, modern feel

2. **ADR-035: Parallel Development with Specialized Agents**
   - Context: Sprint 27 tested parallel development (3 agents simultaneously)
   - Decision: Adopt parallel development for independent features
   - Status: ACCEPTED
   - Consequences: 3x faster delivery, zero conflicts, requires clear boundaries

3. **ADR-036: Settings Management via localStorage**
   - Context: User settings needed persistence (theme, models, API keys)
   - Decision: Use localStorage for client-side settings (no backend DB)
   - Status: ACCEPTED
   - Consequences: Fast, simple, but limited to browser (no sync across devices)

**Architecture Updates:**
- Update `docs/architecture/SYSTEM_OVERVIEW.md` with Frontend → Backend flow
- Add section on Settings Management
- Add section on Performance Testing setup

**API Documentation:**
- OpenAPI schema: Add `/sessions/{session_id}/followup-questions` endpoint
- Add examples for follow-up questions API
- Update Swagger UI with new endpoints

**TECH_DEBT.md:**
- Document 5 legacy test failures (CommunitySearch, LightRAG)
- Priority: P3 (Low - pre-Sprint 25 issues)
- Estimated fix: 3 SP in Sprint 29
- Root cause: ollama_client → aegis_llm_proxy migration incomplete

**Deliverables:**
- 3 ADRs created
- SYSTEM_OVERVIEW.md updated
- OpenAPI schema updated
- TECH_DEBT.md updated with Sprint 27/28 status

**Acceptance Criteria:**
- [ ] 3 ADRs created and reviewed
- [ ] Architecture diagram reflects current state
- [ ] API docs include new endpoints
- [ ] TECH_DEBT.md documents 5 test failures

---

## Sprint Metrics & Goals

### Story Point Distribution

| Priority | Feature | SP | Complexity |
|----------|---------|------|------------|
| P0 | Feature 28.1: Follow-up Questions Frontend | 3 SP | Medium |
| P0 | Feature 28.2: Source Citations Frontend | 3 SP | Medium |
| P1 | Feature 28.3: Settings Page | 5 SP | High |
| P1 | Feature 28.4: Performance Testing | 3 SP | Medium |
| P2 | Feature 28.5: Documentation Backfill | 2 SP | Low |
| **TOTAL** | | **18 SP** | |

### Quality Targets

**Test Coverage:**
- Maintain: ≥80% (from Sprint 27)
- Target: Add 20+ frontend tests

**E2E Tests:**
- Maintain: 100% pass rate (184/184)
- Target: Add 5+ E2E tests for new features

**TypeScript Build:**
- Maintain: 0 errors
- Target: Strict mode enforced

**Performance:**
- Target: 50 QPS sustained with <500ms p95 latency
- Target: <2GB RAM at load
- Target: 100 QPS peak without crashes

---

## Sprint Timeline (3-4 days)

### Day 1: Frontend Integration
- Morning: Feature 28.1 (Follow-up Questions Frontend)
- Afternoon: Feature 28.2 (Source Citations Frontend)
- Evening: E2E tests for both features

### Day 2: Settings & Testing
- Morning: Feature 28.3 (Settings Page - General & Models tabs)
- Afternoon: Feature 28.3 (Settings Page - Advanced tab)
- Evening: Feature 28.4 (Performance Testing setup)

### Day 3: Performance & Docs
- Morning: Feature 28.4 (Load/stress testing execution)
- Afternoon: Feature 28.4 (Memory profiling & analysis)
- Evening: Feature 28.5 (Documentation backfill)

### Day 4: Review & Polish (optional)
- Morning: Performance report review
- Afternoon: ADR review and merge
- Evening: Sprint 28 Completion Report

---

## Dependencies & Risks

### Dependencies (All Resolved ✅)
- ✅ Feature 27.5: Follow-up Questions Backend (completed)
- ✅ Feature 27.10: Source Citations Backend (completed)
- ✅ Feature 27.9: Quick Actions Bar with Settings button (completed)

### Risks

**Risk 1: Performance Testing Reveals Critical Issues**
- Likelihood: Medium
- Impact: High
- Mitigation: Run preliminary load tests before official sprint
- Contingency: Defer optimization to Sprint 29 if issues found

**Risk 2: Settings Page Scope Creep**
- Likelihood: High
- Impact: Medium
- Mitigation: Start with MVP (theme, language, model only)
- Contingency: Defer advanced settings (export/import) to Sprint 29

**Risk 3: Citation Parsing Complexity**
- Likelihood: Low
- Impact: Medium
- Mitigation: Use regex for simple [1][2][3] patterns
- Contingency: If complex, defer hover preview to Sprint 29

---

## Technical Stack

### Frontend (React 19 + TypeScript)
- **Components:** FollowUpQuestions, Citation, Settings
- **Context:** SettingsContext
- **API Client:** chat.ts (add 2 new methods)
- **Testing:** Vitest + React Testing Library
- **E2E:** Playwright

### Backend (Python 3.12)
- **Performance Testing:** Locust
- **Profiling:** py-spy
- **Metrics:** Prometheus + Grafana
- **Load Testing:** 50-100 QPS

### Documentation
- **ADRs:** Markdown (docs/adr/)
- **Architecture:** Mermaid diagrams
- **API Docs:** OpenAPI 3.0 (Swagger UI)

---

## Success Criteria

Sprint 28 is considered successful if:

1. ✅ **All P0 Features Delivered** (Follow-up Questions, Citations)
2. ✅ **Settings Page MVP Complete** (theme, language, models)
3. ✅ **Performance Baseline Established** (50 QPS @ <500ms p95)
4. ✅ **Documentation Current** (3 ADRs, architecture updated)
5. ✅ **Quality Maintained** (80% coverage, 100% E2E pass, 0 TS errors)

---

## Sprint 29 Preview (Tentative)

**Focus:** Optimization & Advanced Features

1. **Performance Optimization** (5 SP)
   - Address bottlenecks from Sprint 28 performance testing
   - Optimize slow endpoints (<500ms → <200ms)
   - Implement connection pooling improvements

2. **Advanced Settings** (3 SP)
   - Export/import conversations
   - Multi-device sync (backend required)
   - Custom prompt templates

3. **Legacy Test Fixes** (3 SP)
   - Fix 5 CommunitySearch/LightRAG test failures
   - Complete ollama_client → aegis_llm_proxy migration
   - Achieve 100% test pass rate (unit + integration)

4. **Multi-Hop Query Implementation** (5 SP)
   - Query decomposition UI
   - Sub-query visualization
   - Context aggregation display

**Total:** ~16 SP

---

## Sprint Handoff from Sprint 27

### Completed in Sprint 27 ✅
- Follow-up Questions Backend (API endpoint + LLM generation)
- Source Citations Backend ([1][2][3] support)
- Quick Actions Bar (New Chat, Clear History, Settings button)
- Copy Button (clipboard with visual feedback)
- Test Coverage 80% (69 tests added)
- E2E Tests 100% (184/184 passing)
- Monitoring (real health checks)

### Deferred to Sprint 28 ⏸️
- Follow-up Questions Frontend (UI component)
- Source Citations Frontend (inline [1][2][3] display)
- Settings Page (Settings button is placeholder)

---

## Notes

- Sprint 28 completes the "Perplexity-inspired UX" vision from Sprint 27
- Performance testing establishes production readiness baseline
- Settings page enables user customization (theme, models, API)
- Documentation backfill maintains project clarity

---

**Plan Created:** 2025-11-16
**Author:** Claude Code
**Sprint Lead:** Klaus Pommer
**Status:** PLANNING → READY FOR KICKOFF
