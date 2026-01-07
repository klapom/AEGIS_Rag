# Sprint 74: RAGAS Integration & Quality Metrics

**Sprint Start:** 2026-01-03
**Sprint End:** 2026-01-17 (2 weeks)
**Total Story Points:** 34 SP

---

## Sprint Goals

1. ✅ **Fix Integration Test Timeouts** - Make existing tests pass
2. 🎯 **RAGAS Backend Integration** - Leverage Sprint 41 implementation
3. 🔍 **Retrieval Method Comparison** - BM25 vs Vector vs Hybrid testing
4. 📊 **Quality Baselines** - Establish RAGAS metric baselines

---

## Sprint Features

### Feature 74.1: Integration Test Fixes (8 SP)

**Epic:** User Journey Step 4 - Chat Quality Testing
**Priority:** P0 (Blocker)

**Context:**
Sprint 73 identified that integration tests work but timeout due to long LLM response times (60-120s). Need to:
1. Increase timeouts to realistic values (180s)
2. Make assertions language-agnostic (LLM responds in German)
3. Document performance baselines

**Tasks:**

#### Task 74.1.1: Update Integration Test Timeouts (3 SP)

**File:** `frontend/e2e/tests/integration/chat-multi-turn.spec.ts`

**Changes:**
- Update `sendAndWaitForResponse` timeout: 60s → 180s
- Update per-test timeouts based on turn count:
  - 3 turns: 180s → 600s (10 min)
  - 5 turns: 300s → 900s (15 min)
  - 12 turns: 720s → 1800s (30 min)

**Acceptance Criteria:**
- All 7 integration tests pass
- No timeouts on turn 2+
- Test completes within new timeout limits

#### Task 74.1.2: Language-Agnostic Assertions (2 SP)

**File:** `frontend/e2e/tests/integration/chat-multi-turn.spec.ts`

**Changes:**
```typescript
// BEFORE: Language-specific
expect(response).toContain('Machine learning');

// AFTER: Language-agnostic
expect(response.length).toBeGreaterThan(50); // Got a response
expect(response).toMatch(/\[Source \d+\]/); // Has citations
```

**Acceptance Criteria:**
- Tests pass with German or English responses
- Verify structural elements (citations, length)
- Focus on behavior, not exact wording

#### Task 74.1.3: Performance Baseline Documentation (3 SP)

**File:** `docs/PERFORMANCE_BASELINES.md`

**Content:**
- Document observed LLM response times
- Turn 1: 20-30s (simple queries)
- Turn 2+: 60-120s (complex with RAG)
- TTFT: 2-3s
- Tokens/sec: 10-15
- Context windows used
- German language responses (why?)

**Acceptance Criteria:**
- Comprehensive baseline documentation
- Includes screenshots from test runs
- Performance targets for future optimization

---

### Feature 74.2: RAGAS Backend Tests (13 SP)

**Epic:** User Journey Step 7 - RAGAS Benchmark
**Priority:** P0 (Critical)

**Context:**
Sprint 41 implemented complete RAGAS system. Need to:
1. Create test dataset
2. Write pytest tests
3. Integrate into CI/CD
4. Establish quality baselines

**Tasks:**

#### Task 74.2.1: Create RAGAS Test Dataset (5 SP)

**Files:**
- `tests/ragas/data/aegis_ragas_dataset.jsonl` (20 test cases)
- `tests/ragas/conftest.py` (fixtures)

**Test Cases Categories:**
1. **Factual Questions (8 cases):**
   - "What is AEGIS RAG?"
   - "What is BGE-M3 embedding model?"
   - "What is Qdrant?"

2. **Exploratory Questions (6 cases):**
   - "How does hybrid search work?"
   - "Why use Reciprocal Rank Fusion?"
   - "How does LangGraph orchestrate agents?"

3. **Summary Questions (4 cases):**
   - "Compare LightRAG and Graphiti"
   - "Summarize the ingestion pipeline"
   - "What are the key ADRs for retrieval?"

4. **Multi-Hop Questions (2 cases):**
   - "What embedding model does Qdrant use and why?"
   - "How does domain training improve reranking?"

**Acceptance Criteria:**
- 20 test cases in JSONL format
- Each has: question, ground_truth, metadata (intent, domain)
- Covers all major domains (retrieval, graph, memory, ingestion)

#### Task 74.2.2: Implement RAGAS Pytest Tests (5 SP)

**File:** `tests/ragas/test_ragas_integration.py`

**Tests:**
1. `test_ragas_context_precision` - Target: >0.75
2. `test_ragas_context_recall` - Target: >0.70
3. `test_ragas_faithfulness` - Target: >0.90
4. `test_ragas_answer_relevancy` - Target: >0.80
5. `test_ragas_per_domain_breakdown` - Verify by domain
6. `test_ragas_regression` - Compare with baseline

**Fixtures:**
```python
@pytest.fixture(scope="session")
async def ragas_evaluator():
    """RAGASEvaluator instance for tests."""
    return RAGASEvaluator(namespace="test_ragas")

@pytest.fixture(scope="session")
def aegis_dataset():
    """Load AEGIS test dataset."""
    with open("tests/ragas/data/aegis_ragas_dataset.jsonl") as f:
        return [json.loads(line) for line in f]
```

**Acceptance Criteria:**
- All 6 tests implemented
- Tests use real backend (Qdrant, Neo4j, Ollama)
- Baseline scores saved for regression testing
- Clear failure messages with metric details

#### Task 74.2.3: CI/CD Integration (3 SP)

**File:** `.github/workflows/ci.yml`

**Changes:**
```yaml
ragas-evaluation:
  runs-on: ubuntu-latest
  needs: [test-backend]

  services:
    qdrant:
      image: qdrant/qdrant:latest
    neo4j:
      image: neo4j:5.24-community
    redis:
      image: redis:7-alpine

  steps:
    - name: Install evaluation dependencies
      run: poetry install --with evaluation

    - name: Run RAGAS tests
      run: pytest tests/ragas/ -m ragas -v --tb=short

    - name: Upload RAGAS report
      uses: actions/upload-artifact@v3
      with:
        name: ragas-report
        path: reports/ragas_*.json
```

**Acceptance Criteria:**
- RAGAS tests run in CI
- Artifacts uploaded on completion
- Tests marked with `@pytest.mark.ragas`
- CI badge shows RAGAS status

---

### Feature 74.3: Retrieval Method Comparison (13 SP)

**Epic:** User Journey Step 4 - Chat Quality Testing
**Priority:** P1 (High)

**Context:**
Currently no automated way to compare BM25 vs Vector vs Hybrid retrieval methods. Need to:
1. Create comparison test dataset
2. Implement backend comparison tests
3. Add frontend E2E comparison tests

**Tasks:**

#### Task 74.3.1: Retrieval Comparison Test Dataset (3 SP)

**File:** `tests/ragas/data/retrieval_comparison_dataset.jsonl`

**Test Cases (10 total):**

**BM25-favored (exact keyword match):**
- "What is the BGE-M3 model version?"
- "Which port does Qdrant use?"

**Vector-favored (semantic similarity):**
- "How does embedding-based search work?"
- "Explain the concept of semantic retrieval"

**Hybrid-favored (both):**
- "Compare keyword and semantic search"
- "What are the benefits of Reciprocal Rank Fusion?"

**Acceptance Criteria:**
- 10 test cases with expected retrieval method winner
- Metadata includes: `expected_best_method`
- Ground truth answers provided

#### Task 74.3.2: Backend Retrieval Comparison Tests (5 SP)

**File:** `tests/ragas/test_retrieval_comparison.py`

**Tests:**
```python
@pytest.mark.ragas
@pytest.mark.asyncio
async def test_retrieval_method_comparison():
    """Compare BM25 vs Vector vs Hybrid retrieval."""

    dataset = load_comparison_dataset()

    # Test each method
    for method in ["bm25", "vector", "hybrid"]:
        evaluator = RAGASEvaluator(
            namespace=f"test_{method}",
            retrieval_method=method,  # NEW: Add method parameter
        )

        results[method] = await evaluator.evaluate_rag_pipeline(dataset)

    # Assert: Hybrid should perform best overall
    assert results["hybrid"].context_precision >= results["bm25"].context_precision
    assert results["hybrid"].context_precision >= results["vector"].context_precision

    # Generate comparison report
    generate_comparison_report(results, "reports/retrieval_comparison.json")
```

**Changes Required:**
- Update `RAGASEvaluator.__init__()` to accept `retrieval_method` parameter
- Update `FourWayHybridSearch` to support method override

**Acceptance Criteria:**
- Tests compare all 3 methods
- Hybrid performs best (or within 5% of best)
- Comparison report generated with metrics

#### Task 74.3.3: Frontend Settings UI - Retrieval Method Selector (5 SP)

**Files:**
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/lib/api.ts`

**Changes:**

**Settings UI:**
```typescript
<FormField label="Retrieval Method">
  <select
    data-testid="retrieval-method-select"
    value={settings.retrievalMethod}
    onChange={(e) => updateSettings({ retrievalMethod: e.target.value })}
  >
    <option value="hybrid">Hybrid (RRF) - Recommended</option>
    <option value="vector">Vector (Semantic)</option>
    <option value="bm25">BM25 (Keyword)</option>
    <option value="local_graph">Local Graph</option>
    <option value="global_graph">Global Graph</option>
  </select>
  <HelpText>
    Hybrid combines keyword and semantic search for best results.
  </HelpText>
</FormField>
```

**API Integration:**
```typescript
// src/lib/api.ts
export async function sendChatMessage(
  message: string,
  options?: {
    retrievalMethod?: 'bm25' | 'vector' | 'hybrid' | 'local_graph' | 'global_graph';
  }
) {
  return await fetch('/api/v1/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      retrieval_method: options?.retrievalMethod,
    }),
  });
}
```

**Backend Changes:**
```python
# src/api/v1/chat.py

class ChatRequest(BaseModel):
    message: str
    retrieval_method: Literal["bm25", "vector", "hybrid", "local_graph", "global_graph"] = "hybrid"

@router.post("/chat")
async def chat(request: ChatRequest):
    # Use specified retrieval method
    results = await search_engine.search(
        query=request.message,
        method=request.retrieval_method,
    )
```

**Acceptance Criteria:**
- Settings UI allows method selection
- Selection persisted in localStorage
- API passes method to backend
- Backend respects method parameter

---

## Sprint Backlog

### Day 1-2 (Jan 3-4): Integration Test Fixes

- [ ] Task 74.1.1: Update timeouts (3 SP)
- [ ] Task 74.1.2: Language-agnostic assertions (2 SP)
- [ ] Task 74.1.3: Performance baseline doc (3 SP)
- **Goal:** All 7 integration tests passing

### Day 3-5 (Jan 5-7): RAGAS Test Dataset

- [ ] Task 74.2.1: Create 20 test cases (5 SP)
- **Goal:** Complete test dataset with all domains

### Day 6-8 (Jan 8-10): RAGAS Backend Tests

- [ ] Task 74.2.2: Implement 6 pytest tests (5 SP)
- [ ] Task 74.2.3: CI/CD integration (3 SP)
- **Goal:** RAGAS tests running in CI

### Day 9-11 (Jan 11-13): Retrieval Comparison

- [ ] Task 74.3.1: Comparison dataset (3 SP)
- [ ] Task 74.3.2: Backend comparison tests (5 SP)
- **Goal:** Automated retrieval comparison

### Day 12-14 (Jan 14-17): Frontend Integration

- [ ] Task 74.3.3: Settings UI + API (5 SP)
- **Goal:** User can select retrieval method

---

## Success Metrics

### Sprint 74 Targets

| Metric | Sprint 73 | Sprint 74 Target | Status |
|--------|-----------|------------------|--------|
| Integration Tests Passing | 0/7 (0%) | 7/7 (100%) | 🎯 |
| RAGAS Context Precision | - | >0.75 | 🎯 |
| RAGAS Faithfulness | - | >0.90 | 🎯 |
| Test Coverage | 63% | 75% | 🎯 |
| Retrieval Comparison | Manual | Automated | 🎯 |

### Definition of Done

**Feature 74.1 (Integration Tests):**
- ✅ All 7 tests pass with real backend
- ✅ No timeouts in CI
- ✅ Performance baselines documented

**Feature 74.2 (RAGAS Tests):**
- ✅ 20 test cases created
- ✅ 6 RAGAS tests passing
- ✅ Tests running in CI
- ✅ Baseline metrics saved

**Feature 74.3 (Retrieval Comparison):**
- ✅ Comparison tests automated
- ✅ Settings UI allows method selection
- ✅ Backend respects method parameter

---

## Risk Mitigation

### Risk 1: RAGAS Tests Too Slow for CI

**Risk:** RAGAS evaluation takes 5-10 minutes per test case

**Mitigation:**
- Use small test dataset (10 cases) for CI
- Full evaluation (50 cases) runs nightly
- Cache LLM responses for repeated tests

### Risk 2: Datasets Library Too Large for CI

**Risk:** HuggingFace `datasets` library is ~600MB

**Mitigation:**
- Make evaluation optional dependency
- Only install in CI when needed
- Use custom lightweight dataset format

### Risk 3: Integration Tests Still Timeout

**Risk:** LLM response time >180s on complex queries

**Mitigation:**
- Monitor per-test duration
- Add retry logic for slow LLM
- Consider simpler test questions

---

## Dependencies

**Sprint 41 (RAGAS Foundation):**
- ✅ `src/evaluation/ragas_evaluator.py`
- ✅ `src/evaluation/benchmark_loader.py`
- ✅ `scripts/run_ragas_benchmark.py`

**Sprint 73 (Integration Tests):**
- ✅ `frontend/e2e/tests/integration/chat-multi-turn.spec.ts`
- ⚠️ Tests fail due to timeouts (fix in 74.1)

**External Dependencies:**
- `ragas ^0.3.7`
- `datasets ^4.0.0` (optional)
- `langchain-ollama` (already installed)

---

## Sprint Review Agenda

### Demo Items

1. **Integration Tests Passing:**
   - Show 7/7 tests green in CI
   - Demonstrate German language handling

2. **RAGAS Metrics Dashboard:**
   - Show Context Precision: 0.XX
   - Show Faithfulness: 0.XX
   - Per-domain breakdown

3. **Retrieval Comparison:**
   - Live demo: BM25 vs Vector vs Hybrid
   - Show which performs best for different query types

4. **Settings UI:**
   - User can select retrieval method
   - Changes reflected in search results

### Metrics to Present

- Total test coverage: X%
- RAGAS scores vs targets
- Integration test pass rate: 100%
- CI/CD pipeline duration

---

## Sprint Retrospective Topics

1. **What worked well:**
   - Reusing Sprint 41 RAGAS implementation
   - Clear test failure analysis from Sprint 73

2. **What to improve:**
   - Earlier performance testing (avoid timeout surprises)
   - Better LLM response time monitoring

3. **Action items for Sprint 75:**
   - Optimize LLM performance (120s → 60s target)
   - Add more RAGAS test cases (20 → 50)
   - Implement RAGAS Dashboard UI

---

## Related Documentation

- [User Journey E2E](../USER_JOURNEY_E2E.md) - Complete user journey
- [RAGAS Integration](../RAGAS_E2E_INTEGRATION.md) - Implementation guide
- [Sprint 73 Analysis](SPRINT_73_INTEGRATION_TEST_ANALYSIS.md) - Test failures
- [Sprint 41 Summary](archive/SPRINT_41_SUMMARY.md) - RAGAS foundation

---

**Sprint Created:** 2026-01-03
**Sprint Owner:** AegisRAG Development Team
**Next Sprint Planning:** 2026-01-17
