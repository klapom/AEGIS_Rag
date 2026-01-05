# RAGAS Integration in E2E User Journey

**Version:** 1.0
**Date:** 2026-01-03
**Sprint Planning:** Sprint 74-75

---

## Executive Summary

AegisRAG bereits ein **vollständiges RAGAS-System** (Sprint 41) mit:

✅ **Backend Implementation:**
- `src/evaluation/ragas_evaluator.py`: Alle 4 RAGAS-Metriken
- `src/evaluation/benchmark_loader.py`: HuggingFace Dataset Loader
- `scripts/run_ragas_benchmark.py`: Retrieval-Methoden-Vergleich
- Namespace-basierte Evaluation
- Per-Intent Breakdown

✅ **Unterstützte Datasets:**
- Natural Questions (Track A: einfache Retrieval)
- HotpotQA (Track B: Multi-Hop Reasoning)
- MS MARCO (Track A: Passage Ranking)
- FEVER (Track B: Fact Verification)
- RAGBench (Track A: Allgemein)

✅ **RAGAS Metriken:**
- **Context Precision:** Relevanz der abgerufenen Dokumente
- **Context Recall:** Vollständigkeit (alle relevanten Docs?)
- **Faithfulness:** Antwort basiert auf Docs (keine Halluzination)
- **Answer Relevancy:** Antwort beantwortet die Frage

**Ziel:** Diese Implementation in die User Journey 1-7 integrieren

---

## Existing RAGAS System - Deep Dive

### 1. RAGASEvaluator Architecture

```python
# src/evaluation/ragas_evaluator.py

class RAGASEvaluator:
    """RAGAS-based evaluation pipeline for AEGIS RAG.

    Features:
    - Namespace-scoped evaluation (isolate benchmark data)
    - Per-intent metric breakdown (factual, keyword, exploratory, summary)
    - Batch evaluation with progress tracking
    - Integration with FourWayHybridSearch
    - All 4 RAGAS metrics
    """

    def __init__(
        self,
        namespace: str = "eval_benchmark",
        llm_model: str = "qwen3:8b",
        embedding_model: str = "bge-m3:latest",
    ):
        # Initialize services
        self.search_engine = get_four_way_hybrid_search()
        self.llm_proxy = get_aegis_llm_proxy()

        # Create LangChain Ollama instances for RAGAS
        self.llm = ChatOllama(
            model=llm_model,
            timeout=300,  # 5 minutes for RAGAS evaluation
            num_ctx=4096,
        )
        self.embeddings = OllamaEmbeddings(model=embedding_model)

    async def evaluate_rag_pipeline(
        self,
        dataset: list[BenchmarkSample],
        sample_size: int | None = None,
        batch_size: int = 10,
        top_k: int = 10,
    ) -> EvaluationResults:
        """Evaluate complete RAG pipeline.

        Flow:
        1. Retrieve contexts for each query (namespace-filtered)
        2. Generate answers using retrieved contexts
        3. Compute all 4 RAGAS metrics
        4. Aggregate results overall and per-intent
        """
        # Process samples
        for sample in dataset:
            # ALWAYS retrieve from Qdrant (tests actual retrieval)
            contexts = await self.retrieve_contexts(sample.question, top_k=top_k)

            # Generate answer if not provided
            answer = await self.generate_answer(sample.question, contexts)

            evaluated_samples.append({
                "question": sample.question,
                "contexts": contexts,
                "answer": answer,
                "ground_truth": sample.ground_truth,
            })

        # Run RAGAS evaluation
        eval_result = evaluate(
            dataset=ragas_dataset,
            metrics=[ContextPrecision(), ContextRecall(), Faithfulness(), AnswerRelevancy()],
            llm=self.llm,
            embeddings=self.embeddings,
        )

        return results
```

### 2. Benchmark Dataset Loader

```python
# src/evaluation/benchmark_loader.py

class BenchmarkDatasetLoader:
    """Loads standard RAG benchmarks from HuggingFace.

    Supported:
    - Natural Questions: Open-domain QA
    - HotpotQA: Multi-hop reasoning
    - MS MARCO: Passage ranking
    - FEVER: Fact verification
    - RAGBench: Comprehensive RAG eval
    """

    async def load_dataset(
        self,
        dataset_name: Literal["natural_questions", "hotpotqa", ...],
        sample_size: int | None = None,
    ) -> list[dict]:
        """Load and normalize a benchmark dataset.

        Returns normalized format:
        {
            'question': str,
            'answer': str,
            'contexts': list[str],
            'source': str,
            'question_id': str
        }
        """
```

### 3. Retrieval Method Comparison

```python
# scripts/run_ragas_benchmark.py

async def run_benchmark(
    dataset_path: str,
    output_dir: str,
    scenarios: list[str] | None = None,
) -> dict:
    """Run RAGAS benchmark across retrieval scenarios:

    - vector-only: Pure semantic search
    - bm25-only: Pure keyword search
    - hybrid-base: Vector + BM25 with RRF
    - hybrid-reranked: Hybrid + cross-encoder reranking
    - hybrid-decomposed: Hybrid + query decomposition
    - hybrid-full: All advanced features enabled
    """

    for scenario in scenarios:
        results[scenario] = await evaluator.run_benchmark(dataset, scenario)

    # Generate comparative report
    return results
```

---

## Integration in User Journey 7

### Mapping: RAGAS → User Journey

| User Journey Step | RAGAS Integration | Files |
|-------------------|-------------------|-------|
| **1. Domain definieren** | Create domain-specific namespace | `src/evaluation/ragas_evaluator.py` |
| **2. Domain Training** | Use training examples as test cases | `src/evaluation/benchmark_loader.py` |
| **3. Dokumente importieren** | Ingest to namespace for evaluation | `scripts/ingest_ragas_and_evaluate.py` |
| **4. Chat Quality Testing** | ✅ **RAGAS Benchmark here!** | `scripts/run_ragas_benchmark.py` |
| **5. Deep Research** | Multi-hop datasets (HotpotQA) | `src/evaluation/ragas_evaluator.py` |
| **6. Chat + Tool Use** | Tool-augmented datasets (future) | - |
| **7. RAGAS Benchmark** | ✅ **Already implemented!** | All of the above |

---

## Implementation Plan: E2E Integration

### Phase 1: Backend RAGAS Tests (Sprint 74.1) - 8 SP

**Goal:** Run existing RAGAS system in CI/CD

#### Task 1.1: Update pyproject.toml (1 SP)

```toml
# pyproject.toml

[tool.poetry.group.evaluation]
optional = true

[tool.poetry.group.evaluation.dependencies]
ragas = "^0.3.7"
datasets = "^4.0.0"  # WARNING: Very heavy (~600MB)
```

**Install:**
```bash
poetry install --with evaluation
```

#### Task 1.2: Create RAGAS Test Dataset (3 SP)

**Option A: Use existing HuggingFace datasets**

```python
# tests/ragas/conftest.py

import pytest
from src.evaluation.benchmark_loader import BenchmarkDatasetLoader

@pytest.fixture(scope="session")
async def hotpotqa_dataset():
    """Load HotpotQA dataset for testing."""
    loader = BenchmarkDatasetLoader()
    dataset = await loader.load_dataset("hotpotqa", sample_size=10)
    return dataset

@pytest.fixture(scope="session")
async def natural_questions_dataset():
    """Load Natural Questions for testing."""
    loader = BenchmarkDatasetLoader()
    dataset = await loader.load_dataset("natural_questions", sample_size=10)
    return dataset
```

**Option B: Create custom AegisRAG-specific dataset**

```python
# tests/ragas/data/aegis_ragas_dataset.jsonl

{"question": "What is AEGIS RAG?", "ground_truth": "AEGIS RAG (Agentic Enterprise Graph Intelligence System) is a multi-modal RAG system...", "metadata": {"intent": "factual", "domain": "system_architecture"}}
{"question": "How does hybrid search work in AEGIS?", "ground_truth": "Hybrid search combines vector search (semantic) with BM25 (keyword) using Reciprocal Rank Fusion...", "metadata": {"intent": "exploratory", "domain": "retrieval"}}
{"question": "Compare LightRAG and Graphiti", "ground_truth": "LightRAG focuses on graph-based retrieval while Graphiti provides temporal memory...", "metadata": {"intent": "summary", "domain": "graph_rag"}}
```

#### Task 1.3: Create Backend RAGAS Tests (3 SP)

```python
# tests/ragas/test_ragas_integration.py

import pytest
from src.evaluation.ragas_evaluator import RAGASEvaluator

@pytest.mark.ragas
@pytest.mark.asyncio
async def test_ragas_context_precision(hotpotqa_dataset):
    """Test Context Precision metric on HotpotQA.

    Context Precision measures if retrieved contexts are relevant.
    Target: >0.75 for production readiness.
    """
    evaluator = RAGASEvaluator(
        namespace="test_hotpotqa",
        llm_model="qwen3:8b",
    )

    results = await evaluator.evaluate_rag_pipeline(
        dataset=hotpotqa_dataset,
        sample_size=10,
        top_k=10,
    )

    # Assert quality threshold
    assert results.overall_metrics.context_precision > 0.75, (
        f"Context Precision ({results.overall_metrics.context_precision:.3f}) "
        f"below threshold 0.75"
    )

    # Log per-intent breakdown
    for intent_metrics in results.per_intent_metrics:
        print(f"{intent_metrics.intent}: {intent_metrics.metrics.context_precision:.3f}")


@pytest.mark.ragas
@pytest.mark.asyncio
async def test_ragas_faithfulness(natural_questions_dataset):
    """Test Faithfulness metric on Natural Questions.

    Faithfulness measures if answer is grounded in retrieved contexts (no hallucination).
    Target: >0.90 for production.
    """
    evaluator = RAGASEvaluator(namespace="test_nq")

    results = await evaluator.evaluate_rag_pipeline(
        dataset=natural_questions_dataset,
        sample_size=10,
    )

    assert results.overall_metrics.faithfulness > 0.90, (
        f"Faithfulness ({results.overall_metrics.faithfulness:.3f}) below threshold 0.90"
    )


@pytest.mark.ragas
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ragas_retrieval_comparison():
    """Compare retrieval methods: BM25 vs Vector vs Hybrid.

    This test verifies that hybrid search performs better than single methods.
    """
    dataset = [
        {
            "question": "What is machine learning?",
            "ground_truth": "Machine learning is a subset of AI...",
            "metadata": {"intent": "factual"}
        },
        # ... more test cases
    ]

    # Test 1: BM25 only
    evaluator_bm25 = RAGASEvaluator(namespace="test_bm25")
    # Configure for BM25-only (need to add config option)
    results_bm25 = await evaluator_bm25.evaluate_rag_pipeline(dataset)

    # Test 2: Vector only
    evaluator_vector = RAGASEvaluator(namespace="test_vector")
    results_vector = await evaluator_vector.evaluate_rag_pipeline(dataset)

    # Test 3: Hybrid (RRF)
    evaluator_hybrid = RAGASEvaluator(namespace="test_hybrid")
    results_hybrid = await evaluator_hybrid.evaluate_rag_pipeline(dataset)

    # Assert: Hybrid should perform best
    assert results_hybrid.overall_metrics.context_precision >= results_bm25.overall_metrics.context_precision
    assert results_hybrid.overall_metrics.context_precision >= results_vector.overall_metrics.context_precision

    # Generate comparison report
    report = {
        "bm25": results_bm25.overall_metrics,
        "vector": results_vector.overall_metrics,
        "hybrid": results_hybrid.overall_metrics,
    }
    print(f"Retrieval Comparison: {report}")
```

#### Task 1.4: Add RAGAS to CI/CD (1 SP)

```yaml
# .github/workflows/ci.yml

  ragas-evaluation:
    runs-on: ubuntu-latest
    needs: [test-backend]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies with evaluation group
        run: |
          poetry install --with evaluation

      - name: Run RAGAS evaluation tests
        run: |
          pytest tests/ragas/ -m ragas -v

      - name: Upload RAGAS report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: ragas-report
          path: reports/ragas_*.json
```

---

### Phase 2: Frontend E2E RAGAS Tests (Sprint 74.2) - 13 SP

**Goal:** Integrate RAGAS with Playwright E2E tests

#### Task 2.1: Create RAGAS E2E Test Data (3 SP)

```typescript
// frontend/e2e/tests/ragas/ragas-testcases.json

[
  {
    "question": "What is machine learning?",
    "ground_truth": "Machine learning is a subset of artificial intelligence...",
    "expected_contexts": [
      "Machine learning is a method of data analysis...",
      "ML algorithms build models based on sample data..."
    ],
    "expected_citations": ["[Source 1]", "[Source 2]"],
    "metadata": {
      "intent": "factual",
      "difficulty": "easy",
      "domain": "ai_ml"
    }
  },
  {
    "question": "How do neural networks work?",
    "ground_truth": "Neural networks consist of interconnected nodes...",
    "expected_contexts": [
      "Neural networks are inspired by biological neural networks...",
      "They consist of layers of nodes called neurons..."
    ],
    "expected_citations": ["[Source 3]", "[Source 4]"],
    "metadata": {
      "intent": "exploratory",
      "difficulty": "medium",
      "domain": "ai_ml"
    }
  },
  // ... 20 total test cases
]
```

#### Task 2.2: Create RAGAS E2E Helper Functions (5 SP)

```typescript
// frontend/e2e/helpers/ragas.ts

import type { Page } from '@playwright/test';

/**
 * RAGAS Metric Calculation Helpers for E2E Tests
 */

export interface RAGASTestCase {
  question: string;
  ground_truth: string;
  expected_contexts: string[];
  expected_citations: string[];
  metadata: {
    intent: string;
    difficulty: string;
    domain: string;
  };
}

export interface RAGASScores {
  context_precision: number;
  context_recall: number;
  faithfulness: number;
  answer_relevancy: number;
}

/**
 * Calculate Context Precision
 * Measures: How many retrieved contexts are relevant?
 * Formula: (Relevant contexts) / (Total retrieved contexts)
 */
export function calculateContextPrecision(
  retrieved_citations: string[],
  expected_contexts: string[]
): number {
  if (retrieved_citations.length === 0) return 0;

  // Simple heuristic: Check if citation text overlaps with expected contexts
  let relevant_count = 0;
  for (const citation of retrieved_citations) {
    const is_relevant = expected_contexts.some(expected =>
      citation.toLowerCase().includes(expected.toLowerCase().substring(0, 30))
    );
    if (is_relevant) relevant_count++;
  }

  return relevant_count / retrieved_citations.length;
}

/**
 * Calculate Context Recall
 * Measures: Were all expected contexts retrieved?
 * Formula: (Retrieved expected contexts) / (Total expected contexts)
 */
export function calculateContextRecall(
  retrieved_citations: string[],
  expected_contexts: string[]
): number {
  if (expected_contexts.length === 0) return 1.0;

  let found_count = 0;
  for (const expected of expected_contexts) {
    const is_found = retrieved_citations.some(citation =>
      citation.toLowerCase().includes(expected.toLowerCase().substring(0, 30))
    );
    if (is_found) found_count++;
  }

  return found_count / expected_contexts.length;
}

/**
 * Calculate Faithfulness (simplified heuristic)
 * Measures: Does answer come from retrieved contexts?
 * Heuristic: Check if answer keywords appear in citations
 */
export function calculateFaithfulness(
  answer: string,
  retrieved_citations: string[]
): number {
  const answer_keywords = answer
    .toLowerCase()
    .split(/\s+/)
    .filter(word => word.length > 4); // Filter short words

  if (answer_keywords.length === 0) return 1.0;

  const citation_text = retrieved_citations.join(' ').toLowerCase();
  let grounded_keywords = 0;

  for (const keyword of answer_keywords) {
    if (citation_text.includes(keyword)) {
      grounded_keywords++;
    }
  }

  return grounded_keywords / answer_keywords.length;
}

/**
 * Calculate Answer Relevancy (simplified heuristic)
 * Measures: Does answer address the question?
 * Heuristic: Check if question keywords appear in answer
 */
export function calculateAnswerRelevancy(
  question: string,
  answer: string
): number {
  const question_keywords = question
    .toLowerCase()
    .replace(/\?/g, '')
    .split(/\s+/)
    .filter(word => word.length > 3 && !['what', 'how', 'why', 'when', 'where'].includes(word));

  if (question_keywords.length === 0) return 1.0;

  const answer_lower = answer.toLowerCase();
  let addressed_keywords = 0;

  for (const keyword of question_keywords) {
    if (answer_lower.includes(keyword)) {
      addressed_keywords++;
    }
  }

  return addressed_keywords / question_keywords.length;
}

/**
 * Extract citations from chat response
 */
export async function extractCitations(page: Page): Promise<string[]> {
  const citationLocator = page.locator('[data-testid="citation"], .citation, [href^="#source"]');
  const count = await citationLocator.count();

  const citations: string[] = [];
  for (let i = 0; i < count; i++) {
    const text = await citationLocator.nth(i).textContent();
    if (text) citations.push(text);
  }

  return citations;
}

/**
 * Run complete RAGAS evaluation on a test case
 */
export async function evaluateRAGASTestCase(
  page: Page,
  testCase: RAGASTestCase
): Promise<RAGASScores> {
  // Send question
  const messageInput = page.locator('[data-testid="message-input"]');
  await messageInput.fill(testCase.question);
  await page.locator('[data-testid="send-button"]').click();

  // Wait for response
  await page.waitForSelector('[data-testid="message"]', { timeout: 60000 });

  // Extract answer
  const messages = page.locator('[data-testid="message"]');
  const lastMessage = await messages.last().textContent();
  const answer = lastMessage || '';

  // Extract citations
  const citations = await extractCitations(page);

  // Calculate metrics
  const context_precision = calculateContextPrecision(citations, testCase.expected_contexts);
  const context_recall = calculateContextRecall(citations, testCase.expected_contexts);
  const faithfulness = calculateFaithfulness(answer, citations);
  const answer_relevancy = calculateAnswerRelevancy(testCase.question, answer);

  return {
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
  };
}
```

#### Task 2.3: Create RAGAS E2E Tests (5 SP)

```typescript
// frontend/e2e/tests/ragas/ragas-e2e.spec.ts

import { test, expect } from '../../fixtures';
import { ragasTestCases } from './ragas-testcases.json';
import {
  evaluateRAGASTestCase,
  type RAGASScores,
} from '../../helpers/ragas';

test.describe('RAGAS E2E Benchmark - User Journey Step 7', () => {
  /**
   * Test 1: Context Precision >80% across all test cases
   *
   * Context Precision = Relevant Contexts / Total Retrieved Contexts
   * Measures if the retrieval system returns relevant documents.
   */
  test('should achieve >80% context precision', async ({ chatPage }) => {
    const results: Array<{ question: string; precision: number; passed: boolean }> = [];

    for (const testCase of ragasTestCases) {
      await chatPage.goto();

      const scores = await evaluateRAGASTestCase(chatPage.page, testCase);

      results.push({
        question: testCase.question,
        precision: scores.context_precision,
        passed: scores.context_precision > 0.80,
      });
    }

    // Calculate overall precision
    const avgPrecision = results.reduce((sum, r) => sum + r.precision, 0) / results.length;

    // Log results
    console.log('Context Precision Results:');
    results.forEach(r => {
      const icon = r.passed ? '✅' : '❌';
      console.log(`${icon} ${r.question.substring(0, 50)}: ${(r.precision * 100).toFixed(1)}%`);
    });

    // Assert overall metric
    expect(avgPrecision).toBeGreaterThan(0.80);

    // Assert individual failures
    const failures = results.filter(r => !r.passed);
    if (failures.length > 0) {
      console.log(`\nFailed ${failures.length}/${results.length} test cases`);
    }
  });

  /**
   * Test 2: Faithfulness >90% (no hallucination)
   *
   * Faithfulness = Answer grounded in retrieved contexts
   * Measures if LLM hallucinates information.
   */
  test('should achieve >90% faithfulness (no hallucination)', async ({ chatPage }) => {
    const results: Array<{ question: string; faithfulness: number; passed: boolean }> = [];

    for (const testCase of ragasTestCases) {
      await chatPage.goto();

      const scores = await evaluateRAGASTestCase(chatPage.page, testCase);

      results.push({
        question: testCase.question,
        faithfulness: scores.faithfulness,
        passed: scores.faithfulness > 0.90,
      });
    }

    // Calculate overall faithfulness
    const avgFaithfulness = results.reduce((sum, r) => sum + r.faithfulness, 0) / results.length;

    // Assert
    expect(avgFaithfulness).toBeGreaterThan(0.90);
  });

  /**
   * Test 3: Per-Domain Breakdown
   *
   * Verifies quality varies by domain (AI/ML vs System Architecture).
   */
  test('should provide per-domain RAGAS breakdown', async ({ chatPage }) => {
    const domainResults: Record<string, RAGASScores[]> = {};

    for (const testCase of ragasTestCases) {
      await chatPage.goto();

      const scores = await evaluateRAGASTestCase(chatPage.page, testCase);
      const domain = testCase.metadata.domain;

      if (!domainResults[domain]) {
        domainResults[domain] = [];
      }
      domainResults[domain].push(scores);
    }

    // Calculate per-domain averages
    for (const [domain, scores] of Object.entries(domainResults)) {
      const avgPrecision = scores.reduce((sum, s) => sum + s.context_precision, 0) / scores.length;
      const avgFaithfulness = scores.reduce((sum, s) => sum + s.faithfulness, 0) / scores.length;

      console.log(`\n${domain}:`);
      console.log(`  Context Precision: ${(avgPrecision * 100).toFixed(1)}%`);
      console.log(`  Faithfulness: ${(avgFaithfulness * 100).toFixed(1)}%`);

      // All domains should meet minimum threshold
      expect(avgPrecision).toBeGreaterThan(0.70); // 70% minimum
      expect(avgFaithfulness).toBeGreaterThan(0.85); // 85% minimum
    }
  });
});
```

---

### Phase 3: Retrieval Method Comparison E2E (Sprint 75) - 13 SP

**Goal:** Compare BM25 vs Vector vs Hybrid in frontend

#### Task 3.1: Add Retrieval Method Selector to Settings (5 SP)

```typescript
// frontend/src/pages/SettingsPage.tsx

export function SettingsPage() {
  const [retrievalMethod, setRetrievalMethod] = useState<'bm25' | 'vector' | 'hybrid'>('hybrid');

  return (
    <div>
      <h2>Retrieval Settings</h2>
      <select
        data-testid="retrieval-method-select"
        value={retrievalMethod}
        onChange={(e) => setRetrievalMethod(e.target.value as any)}
      >
        <option value="bm25">BM25 (Keyword Search)</option>
        <option value="vector">Vector (Semantic Search)</option>
        <option value="hybrid">Hybrid (RRF Fusion)</option>
      </select>
    </div>
  );
}
```

#### Task 3.2: Update API to Support Retrieval Method (3 SP)

```python
# src/api/v1/chat.py

from src.components.retrieval.four_way_hybrid_search import RetrievalMethod

@router.post("/chat")
async def chat(
    request: ChatRequest,
    retrieval_method: RetrievalMethod = RetrievalMethod.HYBRID,  # New parameter
):
    # Use specified retrieval method
    results = await search_engine.search(
        query=request.message,
        method=retrieval_method,
    )
```

#### Task 3.3: Create Retrieval Comparison E2E Tests (5 SP)

```typescript
// frontend/e2e/tests/ragas/retrieval-comparison.spec.ts

test.describe('Retrieval Method Comparison - User Journey Step 4', () => {
  /**
   * Test: BM25 vs Vector vs Hybrid
   *
   * Compares retrieval quality using same questions.
   */
  test('should compare BM25 vs Vector vs Hybrid retrieval', async ({ settingsPage, chatPage }) => {
    const testCases = ragasTestCases.slice(0, 5); // First 5 cases

    const results = {
      bm25: [] as RAGASScores[],
      vector: [] as RAGASScores[],
      hybrid: [] as RAGASScores[],
    };

    // Test each method
    for (const method of ['bm25', 'vector', 'hybrid'] as const) {
      // Configure retrieval method
      await settingsPage.goto();
      await settingsPage.selectRetrievalMethod(method);

      // Run test cases
      for (const testCase of testCases) {
        await chatPage.goto();
        const scores = await evaluateRAGASTestCase(chatPage.page, testCase);
        results[method].push(scores);
      }
    }

    // Calculate averages
    const avg = (scores: RAGASScores[]) => ({
      precision: scores.reduce((sum, s) => sum + s.context_precision, 0) / scores.length,
      recall: scores.reduce((sum, s) => sum + s.context_recall, 0) / scores.length,
      faithfulness: scores.reduce((sum, s) => sum + s.faithfulness, 0) / scores.length,
      relevancy: scores.reduce((sum, s) => sum + s.answer_relevancy, 0) / scores.length,
    });

    const bm25Avg = avg(results.bm25);
    const vectorAvg = avg(results.vector);
    const hybridAvg = avg(results.hybrid);

    // Log comparison
    console.log('Retrieval Method Comparison:');
    console.log(`BM25:   Precision=${(bm25Avg.precision * 100).toFixed(1)}%`);
    console.log(`Vector: Precision=${(vectorAvg.precision * 100).toFixed(1)}%`);
    console.log(`Hybrid: Precision=${(hybridAvg.precision * 100).toFixed(1)}%`);

    // Assert: Hybrid should be best (or at least not worse)
    expect(hybridAvg.precision).toBeGreaterThanOrEqual(bm25Avg.precision * 0.95); // Within 5%
    expect(hybridAvg.precision).toBeGreaterThanOrEqual(vectorAvg.precision * 0.95);
  });
});
```

---

## Success Metrics

### Sprint 74 Targets

| Metric | Current | Sprint 74 Target | Method |
|--------|---------|------------------|--------|
| Context Precision | - | 0.75 | RAGAS Backend Tests |
| Context Recall | - | 0.70 | RAGAS Backend Tests |
| Faithfulness | - | 0.90 | RAGAS Backend Tests |
| Answer Relevancy | - | 0.80 | RAGAS Backend Tests |
| E2E Test Coverage | 63% | 75% | +RAGAS E2E Tests |

### Sprint 75 Targets

| Metric | Sprint 74 | Sprint 75 Target | Method |
|--------|-----------|------------------|--------|
| Context Precision | 0.75 | 0.80 | Retrieval Optimization |
| Context Recall | 0.70 | 0.75 | Better chunking |
| Retrieval Comparison | Manual | Automated | E2E Tests |
| Test Cases | 10 | 50 | Expanded dataset |

---

## Existing Scripts - Ready to Use

### 1. Run RAGAS Benchmark

```bash
# Compare retrieval methods on HotpotQA
python scripts/run_ragas_benchmark.py \
  --dataset data/benchmarks/hotpotqa.jsonl \
  --output reports/ragas \
  --scenarios vector-only,bm25-only,hybrid-full

# Output: reports/ragas/ragas_evaluation_20260103_143052.html
```

### 2. Run Evaluation on Custom Dataset

```bash
# Evaluate on custom test cases
python scripts/run_evaluation.py \
  --dataset data/evaluation/aegis_ragas_dataset.jsonl \
  --namespace eval_aegis \
  --sample-size 50 \
  --output-dir reports/evaluation
```

### 3. Ingest and Evaluate

```bash
# Ingest benchmark data + run evaluation
python scripts/ingest_ragas_and_evaluate.py \
  --dataset hotpotqa \
  --namespace eval_hotpotqa \
  --sample-size 100
```

---

## Next Steps

### Immediate (Today)

1. **Test existing RAGAS system:**
   ```bash
   poetry install --with evaluation
   python scripts/run_evaluation.py --help
   ```

2. **Create minimal test dataset:**
   - `tests/ragas/data/aegis_test.jsonl` (10 samples)
   - Domain-specific questions about AegisRAG

3. **Run first RAGAS evaluation:**
   ```bash
   pytest tests/ragas/ -m ragas -v
   ```

### Sprint 74 (Next 2 weeks)

1. **Backend Tests (8 SP):**
   - Create 20 test cases
   - Add to CI/CD
   - Establish baselines (Precision, Recall, Faithfulness)

2. **E2E Integration (13 SP):**
   - RAGAS helper functions
   - 3 E2E test specs
   - Per-domain breakdown

### Sprint 75 (Following 2 weeks)

1. **Retrieval Comparison (13 SP):**
   - Add method selector to Settings UI
   - API support for method parameter
   - Comparison E2E tests

2. **Optimization (8 SP):**
   - Improve based on RAGAS metrics
   - Target: Precision 0.80+, Faithfulness 0.90+

---

## Conclusion

**RAGAS ist bereits komplett implementiert** (Sprint 41) und kann sofort verwendet werden für:

✅ **User Journey Step 4 (Chat Quality Testing):**
- Quantitative Bewertung der Retrieval-Qualität
- Vergleich verschiedener Methoden (BM25, Vector, Hybrid)

✅ **User Journey Step 7 (RAGAS Benchmark):**
- Objektive Metriken für Regression Testing
- Vergleichbar mit anderen RAG Systemen

**Nächster Schritt:** Sprint 74 Planning - RAGAS Integration in E2E Tests

---

**Document Version:** 1.0
**Dependencies:** Sprint 41 (RAGAS Foundation)
**Next Review:** Sprint 74 Kickoff
