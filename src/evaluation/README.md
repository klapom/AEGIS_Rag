# RAGAS Evaluation Pipeline

Sprint 41 Feature 41.7: RAGAS-based evaluation pipeline for AEGIS RAG system.

## Overview

This module provides comprehensive evaluation of the AEGIS RAG system using RAGAS (RAG Assessment) metrics:

- **Context Precision**: Measures relevance of retrieved contexts to the answer
- **Context Recall**: Measures coverage of ground truth information
- **Faithfulness**: Measures if answer is grounded in retrieved contexts
- **Answer Relevancy**: Measures if answer addresses the question

## Features

### 1. Namespace-Scoped Evaluation
Evaluate RAG performance using namespace-isolated benchmark data:
```python
from src.evaluation import RAGASEvaluator

evaluator = RAGASEvaluator(namespace="eval_hotpotqa")
results = await evaluator.evaluate_rag_pipeline(dataset, sample_size=50)
```

### 2. Per-Intent Metric Breakdown
Get detailed metrics broken down by query intent (factual, keyword, exploratory, summary):
```python
for intent_metrics in results.per_intent_metrics:
    print(f"{intent_metrics.intent}: F1={intent_metrics.metrics.faithfulness:.3f}")
```

### 3. Integration with FourWayHybridSearch
Automatically uses namespace filtering for retrieval:
- Searches only in benchmark namespace
- Uses intent-weighted RRF fusion
- Supports reranking

### 4. Batch Evaluation
Process large datasets efficiently:
```python
results = await evaluator.evaluate_rag_pipeline(
    dataset=dataset,
    batch_size=10,  # Process 10 samples at a time
    top_k=10,       # Retrieve 10 contexts per query
)
```

## Usage

### CLI Script

The easiest way to run evaluation is using the CLI script:

```bash
# Evaluate on pre-defined benchmark (HotpotQA)
python scripts/run_evaluation.py \
    --benchmark hotpotqa \
    --namespace eval_hotpotqa \
    --sample-size 50 \
    --output-dir reports/evaluation

# Evaluate on custom dataset
python scripts/run_evaluation.py \
    --dataset data/benchmarks/custom.jsonl \
    --namespace eval_custom \
    --sample-size 100 \
    --batch-size 10 \
    --output-dir reports/evaluation
```

### Programmatic Usage

```python
from src.evaluation import RAGASEvaluator

# Initialize evaluator
evaluator = RAGASEvaluator(
    namespace="eval_hotpotqa",
    llm_model="llama3.2:8b",
)

# Load dataset
dataset = evaluator.load_dataset("data/benchmarks/hotpotqa.jsonl")

# Run evaluation
results = await evaluator.evaluate_rag_pipeline(
    dataset=dataset,
    sample_size=50,
    batch_size=10,
    top_k=10,
)

# Access results
print(f"Overall Faithfulness: {results.overall_metrics.faithfulness:.3f}")
print(f"Samples evaluated: {results.sample_count}")

# Per-intent breakdown
for intent_metrics in results.per_intent_metrics:
    print(f"{intent_metrics.intent} ({intent_metrics.sample_count} samples):")
    print(f"  Precision: {intent_metrics.metrics.context_precision:.3f}")
    print(f"  Recall: {intent_metrics.metrics.context_recall:.3f}")
    print(f"  Faithfulness: {intent_metrics.metrics.faithfulness:.3f}")
    print(f"  Relevancy: {intent_metrics.metrics.answer_relevancy:.3f}")

# Generate report
report = evaluator.generate_report(
    results=results,
    output_path="reports/eval_results.json",
    format="json"
)
```

## Dataset Format

Benchmark datasets should be JSONL files with one sample per line:

```jsonl
{"question": "What is the capital of France?", "ground_truth": "Paris", "metadata": {"intent": "factual"}}
{"question": "How does photosynthesis work?", "ground_truth": "Photosynthesis converts light energy...", "metadata": {"intent": "exploratory"}}
```

### Required Fields
- `question`: User query string
- `ground_truth`: Expected answer or reference information

### Optional Fields
- `contexts`: Pre-retrieved contexts (for retrieval-only evaluation)
- `answer`: Pre-generated answer (for generation-only evaluation)
- `metadata`: Additional metadata
  - `intent`: Query intent (factual, keyword, exploratory, summary)
  - `difficulty`: Difficulty level (easy, medium, hard)
  - `source`: Dataset source (hotpotqa, musique, squad)

## Pre-defined Benchmarks

The following benchmarks are configured in `scripts/run_evaluation.py`:

| Benchmark | Namespace | Description |
|-----------|-----------|-------------|
| hotpotqa | eval_hotpotqa | Multi-hop reasoning benchmark |
| musique | eval_musique | Multi-hop QA benchmark |
| squad | eval_squad | Single-hop QA benchmark |

## Output Format

Evaluation results are saved in JSON format:

```json
{
  "timestamp": "2025-12-09T10:00:00Z",
  "namespace": "eval_hotpotqa",
  "sample_count": 50,
  "duration_seconds": 245.67,
  "overall_metrics": {
    "context_precision": 0.85,
    "context_recall": 0.78,
    "faithfulness": 0.92,
    "answer_relevancy": 0.88
  },
  "per_intent_metrics": [
    {
      "intent": "factual",
      "sample_count": 30,
      "context_precision": 0.87,
      "context_recall": 0.81,
      "faithfulness": 0.94,
      "answer_relevancy": 0.90
    },
    {
      "intent": "exploratory",
      "sample_count": 20,
      "context_precision": 0.82,
      "context_recall": 0.74,
      "faithfulness": 0.89,
      "answer_relevancy": 0.85
    }
  ],
  "metadata": {
    "llm_model": "llama3.2:8b",
    "top_k": 10,
    "batch_size": 10
  }
}
```

## Architecture

### Components

1. **RAGASEvaluator** (`src/evaluation/ragas_evaluator.py`)
   - Main evaluation class
   - Integrates with FourWayHybridSearch
   - Computes all 4 RAGAS metrics
   - Provides per-intent breakdown

2. **OllamaLangChainLLM** (internal wrapper)
   - Adapts AegisLLMProxy to LangChain interface
   - Required by RAGAS library

3. **OllamaEmbeddings** (internal wrapper)
   - Adapts UnifiedEmbeddingService to LangChain interface
   - Required by RAGAS library

### Evaluation Flow

```
1. Load Dataset (JSONL)
   ↓
2. For each sample:
   - Retrieve contexts (namespace-filtered)
   - Generate answer (using contexts)
   ↓
3. Run RAGAS Evaluation
   - Context Precision
   - Context Recall
   - Faithfulness
   - Answer Relevancy
   ↓
4. Aggregate Results
   - Overall metrics
   - Per-intent breakdown
   ↓
5. Generate Report (JSON)
```

## Dependencies

This module requires the `evaluation` optional dependency group:

```bash
poetry install --with evaluation
```

This installs:
- `ragas ^0.3.7`: RAGAS evaluation framework
- `datasets ^4.0.0`: HuggingFace datasets library

**Warning**: The `datasets` library is VERY HEAVY (~600MB+). Only install for evaluation tasks, not in CI/CD.

## Performance Considerations

- **Batch Size**: Default 10. Increase for faster evaluation (more memory).
- **Sample Size**: Use `sample_size` to evaluate subset of dataset for quick feedback.
- **Top-K**: Default 10. Higher values = more contexts = better recall but slower.

## Error Handling

The evaluator raises `EvaluationError` when evaluation fails:

```python
from src.core.exceptions import EvaluationError

try:
    results = await evaluator.evaluate_rag_pipeline(dataset)
except EvaluationError as e:
    logger.error(f"Evaluation failed: {e.message}")
    print(f"Error details: {e.details}")
```

## Testing

Example test:

```python
import pytest
from src.evaluation import RAGASEvaluator

@pytest.mark.asyncio
async def test_ragas_evaluation():
    evaluator = RAGASEvaluator(namespace="test_eval")

    dataset = [
        {
            "question": "What is AEGIS RAG?",
            "ground_truth": "AEGIS RAG is an enterprise RAG system.",
            "metadata": {"intent": "factual"}
        }
    ]

    results = await evaluator.evaluate_rag_pipeline(
        dataset=dataset,
        sample_size=1
    )

    assert results.sample_count == 1
    assert 0 <= results.overall_metrics.faithfulness <= 1
```

## Related Documentation

- [RAGAS Documentation](https://docs.ragas.io/)
- [Sprint 41 Feature 41.7](../../docs/sprints/SPRINT_41.md)
- [FourWayHybridSearch](../components/retrieval/four_way_hybrid_search.py)
- [Namespace Management](../core/namespace.py)
