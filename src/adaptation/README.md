# Adaptation Framework

**Sprint 67 Features 67.5-67.10**: Tool-Level Adaptation for AegisRAG

This module implements the adaptation framework for continuous improvement of RAG components through synthetic data generation, model training, and online evaluation.

## Architecture

```
User Query → RAG Pipeline → Trace Logger → Dataset Builder → Training → Improved Models
                                ↓
                         Eval Harness
                         (Quality Gates)
```

## Components

### 1. Intent Data Generator (Feature 67.10) - ✅ COMPLETE

Generate labeled intent classification examples using Qwen2.5:7b for training a SetFit model.

**Location:** `src/adaptation/intent_data_generator.py`

**Usage:**
```bash
# Generate 1000 training examples
python -m src.adaptation.intent_data_generator \
  --model qwen2.5:7b \
  --examples 1000 \
  --batch-size 10 \
  --output data/intent_training_v1.jsonl

# Quick test (20 examples)
python scripts/test_intent_classifier.py
```

**Intent Classes:**
- `factual`: Specific fact lookups (Who, What, When, Where)
- `procedural`: Step-by-step instructions (How-to guides)
- `comparison`: Compare multiple entities (A vs B)
- `recommendation`: Best practices, suggestions
- `navigation`: Find location/category

**Quality Targets:**
- 1000 labeled examples (200 per intent class)
- Balanced distribution across 5 intent classes
- Bilingual: 50% German, 50% English
- Confidence >0.8 for 90% of examples
- Duplicate rate <5%

**Example Output (JSONL):**
```json
{"query": "What is RAG?", "intent": "factual", "confidence": 0.95, "language": "en", "domain": "software"}
{"query": "How to install Docker?", "intent": "procedural", "confidence": 0.92, "language": "en", "domain": "software"}
{"query": "Unterschied zwischen REST und GraphQL?", "intent": "comparison", "confidence": 0.90, "language": "de", "domain": "software"}
```

**API:**
```python
from src.adaptation import CLARADataGenerator

generator = CLARADataGenerator(
    model="qwen2.5:7b",
    target_examples=1000
)

# Generate examples
examples = await generator.generate_examples()

# Validate quality
report = generator.validate_dataset(examples)
print(report)  # {"valid": True, "total_examples": 1000, ...}

# Save to JSONL
await generator.save_dataset(examples, "data/intent_training_v1.jsonl")
```

---

### 2. Dataset Builder (Feature 67.7) - PENDING

Convert RAG traces to training data for reranker and query rewriter.

**Planned Features:**
- Rerank pairs: (query, pos_chunk, neg_chunk) triplets
- Rewrite supervision: (query, rewrite, retrieval_outcome) pairs
- Sampling strategies: hard negatives, in-batch negatives
- Labeling rules: Hit@k, Eval-Score thresholds
- Deduplication and PII filtering

---

### 3. Unified Trace Logger (Feature 67.5) - PENDING

Unified trace format for all RAG stages (retrieval, reranking, generation).

**Planned Format:**
```json
{
  "trace_version": "v1",
  "request_id": "req_abc123",
  "query": {"original": "...", "rewritten": "...", "intent": "factual"},
  "retrieval": {"vector": {...}, "bm25": {...}, "graph_local": {...}, "graph_global": {...}},
  "rrf": {"weights": {...}, "fused_results": [...]},
  "rerank": {"method": "cross_encoder", "results": [...]},
  "answer": {"text": "...", "latency_ms": 450}
}
```

---

### 4. Eval Harness (Feature 67.6) - PENDING

Automatic quality checks as CI/CD gates.

**Planned Metrics:**
- Grounding score: How well is answer anchored in evidence?
- Citation coverage: % of claims with citations
- Format compliance: JSON schema validation
- Retrieval hit@k: % of relevant chunks in top-K
- Latency P95: End-to-end latency

**Planned Suites:**
- Canary: 20-50 critical queries (regression detection)
- Regression: 100-200 queries (full coverage)
- Stress: 500+ queries (load testing)

---

## Testing

### Unit Tests

```bash
# Run all adaptation tests
poetry run pytest tests/unit/adaptation/ -v

# Run with coverage
poetry run pytest tests/unit/adaptation/ --cov=src.adaptation --cov-report=term-missing
```

**Coverage Target:** >80%

### Integration Tests

```bash
# Test intent data generation with Qwen2.5:7b
poetry run python scripts/test_intent_classifier.py
```

**Prerequisites:**
- Ollama running on localhost:11434
- Qwen2.5:7b model available: `ollama pull qwen2.5:7b`

---

## File Structure

```
src/adaptation/
├── __init__.py                    # Module exports
├── intent_data_generator.py       # C-LARA data generator (Feature 67.10) ✅
├── dataset_builder.py             # Trace → Training data (Feature 67.7) - PENDING
├── trace_logger.py                # Unified trace format (Feature 67.5) - PENDING
├── eval_harness.py                # Quality gates (Feature 67.6) - PENDING
└── README.md                      # This file

tests/unit/adaptation/
├── __init__.py
├── test_intent_data_generator.py  # Unit tests for Feature 67.10 ✅
└── test_dataset_builder.py        # Unit tests for Feature 67.7 - PENDING

scripts/
└── test_intent_classifier.py      # Integration test for Feature 67.10 ✅
```

---

## Dependencies

### Python Packages (Already in pyproject.toml)
```toml
[tool.poetry.dependencies]
httpx = "^0.27.0"                  # HTTP client for Ollama
structlog = "^24.1.0"              # Structured logging
setfit = "^1.0.0"                  # SetFit training (Feature 67.11)
sentence-transformers = "^2.2.0"   # Base embeddings
```

### System Requirements
- Ollama: localhost:11434
- Model: qwen2.5:7b (87-95% intent benchmarks)
- Disk: ~2GB for model + training data

---

## References

### Papers
- [Paper 2512.16301: Tool-Level LLM Adaptation](https://arxiv.org/abs/2512.16301)
- [C-LARA: Intent Detection in the Age of LLMs](https://www.amazon.science/publications/intent-detection-in-the-age-of-llms)
- [SetFit: Efficient Few-Shot Learning](https://arxiv.org/abs/2209.11055)

### Documentation
- [SPRINT_67_PLAN.md](../../docs/sprints/SPRINT_67_PLAN.md) - Sprint 67 overview
- [TD-079: LLM Intent Classifier](../../docs/technical-debt/TD-079_LLM_INTENT_CLASSIFIER_CLARA.md)
- [TD_INDEX.md](../../docs/technical-debt/TD_INDEX.md) - Technical Debt Index

### Related Code
- [src/components/retrieval/intent_classifier.py](../components/retrieval/intent_classifier.py) - Current intent classifier
- [src/agents/](../agents/) - LangGraph agents
- [src/components/](../components/) - Core RAG components

---

## Progress

| Feature | Status | Story Points | Completion |
|---------|--------|--------------|------------|
| 67.5 Unified Trace & Telemetry | PENDING | 8 SP | 0% |
| 67.6 Eval Harness | PENDING | 10 SP | 0% |
| 67.7 Dataset Builder | PENDING | 8 SP | 0% |
| 67.8 Adaptive Reranker v1 | PENDING | 13 SP | 0% |
| 67.9 Query Rewriter v1 | PENDING | 10 SP | 0% |
| 67.10 C-LARA Data Generation | ✅ COMPLETE | 3 SP | 100% |
| **Total** | **IN PROGRESS** | **52 SP** | **6%** |

---

**Last Updated:** 2025-12-31 (Sprint 67 Feature 67.10 Complete)
**Next Steps:** Feature 67.11 - Train SetFit model on generated data
