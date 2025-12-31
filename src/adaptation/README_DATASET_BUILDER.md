# Dataset Builder (Feature 67.7)

**Sprint 67 Feature 67.7**: Generate training datasets from production traces.

## Overview

The `DatasetBuilder` converts production query traces (from UnifiedTracer) into training datasets for:

1. **Intent Classification**: (query, intent) pairs for fine-tuning intent classifiers
2. **Reranking**: (query, pos_chunk, neg_chunk) triplets for training rerankers
3. **Query Rewriting**: (original, rewritten, success) pairs for query rewriter training

## Architecture

```
Production Traces (JSONL)
    ↓
DatasetBuilder (Filter by Quality)
    ↓
Training Examples (Intent/Rerank/Rewrite)
    ↓
JSONL Datasets
    ↓
Model Training (SetFit/Cross-Encoder)
```

## Features

- **Quality Filtering**: Filter traces by quality score threshold (0.0-1.0)
- **Deduplication**: Remove duplicate/similar queries, keeping highest quality
- **Hard Negative Mining**: Find challenging negative examples for reranker
- **In-Batch Negatives**: Pair cited with uncited chunks from same query
- **JSONL Output**: Efficient streaming format for large datasets
- **Statistics**: Detailed stats on dataset composition and quality

## Usage

### Programmatic API

```python
from src.adaptation.dataset_builder import DatasetBuilder

# Initialize builder
builder = DatasetBuilder(trace_path="data/traces/traces.jsonl")

# Build intent classification dataset
intent_examples = await builder.build_intent_dataset(
    min_quality=0.8,
    output_path="data/datasets/v1/intent_dataset.jsonl",
    deduplicate=True
)

# Build reranking dataset with hard negatives
rerank_examples = await builder.build_rerank_dataset(
    sampling="hard_negatives",
    min_score_diff=0.3,
    output_path="data/datasets/v1/rerank_pairs.jsonl"
)
```

### CLI Script

```bash
# Build intent dataset
python scripts/build_datasets.py \
    --intent \
    --min-quality 0.85 \
    --trace-path data/traces \
    --output-dir data/datasets/v1

# Build reranking dataset
python scripts/build_datasets.py \
    --rerank \
    --sampling hard_negatives \
    --min-score-diff 0.3 \
    --trace-path data/traces \
    --output-dir data/datasets/v1

# Build all datasets
python scripts/build_datasets.py \
    --all \
    --trace-path data/traces \
    --output-dir data/datasets/v1
```

## Dataset Formats

### Intent Classification Dataset

**File**: `intent_dataset.jsonl`

```jsonl
{"query": "What is RAG?", "intent": "factual", "quality_score": 0.92, "timestamp": "2025-12-31T10:00:00Z", "metadata": {...}}
{"query": "How does vector search work?", "intent": "exploratory", "quality_score": 0.88, "timestamp": "2025-12-31T10:05:00Z", "metadata": {...}}
```

**Fields**:
- `query`: Original user query
- `intent`: Classified intent (factual, keyword, exploratory, summary)
- `quality_score`: Quality score from eval harness (0.0-1.0)
- `timestamp`: When query was executed
- `metadata`: Additional context (request_id, latency_ms, model)

### Reranking Dataset

**File**: `rerank_pairs.jsonl`

```jsonl
{"query": "What is RAG?", "pos_chunk_id": "c1", "neg_chunk_id": "c3", "pos_score": 0.92, "neg_score": 0.65, "pos_rank": 1, "neg_rank": 7}
{"query": "vector search", "pos_chunk_id": "c5", "neg_chunk_id": "c8", "pos_score": 0.88, "neg_score": 0.70, "pos_rank": 2, "neg_rank": 5}
```

**Fields**:
- `query`: User query
- `pos_chunk_id`: Chunk ID of positive (cited in answer)
- `neg_chunk_id`: Chunk ID of negative (not cited)
- `pos_score`: Original retrieval score of positive
- `neg_score`: Original retrieval score of negative
- `pos_rank`: Original rank of positive chunk
- `neg_rank`: Original rank of negative chunk

## Sampling Strategies

### Hard Negatives

Finds high-ranked chunks that were **not** cited in the answer:

- Best for training robust rerankers
- Focuses on difficult cases (similar score to positives)
- Example: Chunk ranked #2 but not cited vs chunk ranked #5 and cited

```python
rerank_examples = await builder.build_rerank_dataset(
    sampling="hard_negatives",
    min_score_diff=0.3  # Minimum difference between pos/neg scores
)
```

### In-Batch Negatives

Pairs cited chunks with uncited chunks from the same query:

- Simpler, more pairs per query
- Good for initial training
- All combinations of pos/neg within query

```python
rerank_examples = await builder.build_rerank_dataset(
    sampling="in_batch",
    min_score_diff=0.1
)
```

## Quality Filtering

Control dataset quality with `min_quality` threshold:

```python
# High quality only (fewer examples, higher quality)
examples = await builder.build_intent_dataset(min_quality=0.9)

# Moderate quality (more examples, balanced)
examples = await builder.build_intent_dataset(min_quality=0.8)

# Include all (maximum data, variable quality)
examples = await builder.build_intent_dataset(min_quality=0.5)
```

**Recommendation**: Start with `min_quality=0.8` for good balance.

## Deduplication

Remove duplicate or highly similar queries:

```python
# With deduplication (default)
examples = await builder.build_intent_dataset(deduplicate=True)

# Without deduplication (keep all)
examples = await builder.build_intent_dataset(deduplicate=False)
```

**Algorithm**:
1. Exact match: Lowercase + strip whitespace
2. Similarity: Character-level overlap (90% threshold)
3. Keep highest quality example per duplicate group

**Note**: For production, consider using sentence embeddings for semantic similarity.

## Error Handling

The builder gracefully handles:

- **Malformed traces**: Skips traces with missing required fields
- **Invalid JSON**: Skips invalid JSONL lines with warning
- **Missing files**: Returns empty list if trace file not found
- **Empty traces**: Logs warning and returns empty dataset

All errors are logged with structured logging for debugging.

## Performance

- **Memory**: Loads all traces into memory (cache for multiple dataset builds)
- **Speed**: ~1000 traces/second for filtering and extraction
- **Disk**: JSONL format for efficient streaming (no memory limit)

For very large trace files (>1M traces), consider:
- Loading in batches
- Filtering by date range
- Using directory of smaller files

## Integration

### With UnifiedTracer (Feature 67.5)

```python
# 1. Generate traces during production
from src.adaptation.trace_telemetry import UnifiedTracer

tracer = UnifiedTracer(output_path="data/traces/traces.jsonl")
await tracer.log_trace(trace_event)

# 2. Build datasets from traces
builder = DatasetBuilder(trace_path="data/traces/traces.jsonl")
examples = await builder.build_intent_dataset(min_quality=0.8)
```

### With Eval Harness (Feature 67.6)

```python
# Eval Harness adds quality_score to traces
from src.adaptation.eval_harness import EvalHarness

eval_harness = EvalHarness()
quality_score = await eval_harness.evaluate(query, answer, sources)

# DatasetBuilder uses quality_score for filtering
builder = DatasetBuilder(trace_path="data/traces/traces.jsonl")
high_quality = await builder.build_intent_dataset(min_quality=0.85)
```

### With Adaptive Reranker (Feature 67.8)

```python
# 1. Build reranking dataset
builder = DatasetBuilder(trace_path="data/traces/traces.jsonl")
rerank_data = await builder.build_rerank_dataset(
    sampling="hard_negatives",
    output_path="data/datasets/v1/rerank_pairs.jsonl"
)

# 2. Train adaptive reranker (Feature 67.8)
from scripts.train_reranker import train_reranker

train_reranker(
    data_path="data/datasets/v1/rerank_pairs.jsonl",
    model_output="models/reranker_v1"
)
```

## Dataset Versioning

Use versioned directories for reproducibility:

```
data/datasets/
├── v1/
│   ├── intent_dataset.jsonl
│   ├── rerank_pairs.jsonl
│   └── stats.json
├── v2/
│   ├── intent_dataset.jsonl
│   ├── rerank_pairs.jsonl
│   └── stats.json
└── latest -> v2/
```

**Best Practice**: Include date and trace count in version metadata.

## Testing

Run unit tests:

```bash
# All tests
poetry run pytest tests/unit/adaptation/test_dataset_builder.py -v

# Specific test
poetry run pytest tests/unit/adaptation/test_dataset_builder.py::TestDatasetBuilder::test_build_intent_dataset__high_quality_threshold__filters_correctly -v

# With coverage
poetry run pytest tests/unit/adaptation/test_dataset_builder.py --cov=src/adaptation/dataset_builder --cov-report=term-missing
```

## Examples

### Example 1: Build Intent Dataset for C-LARA Training

```python
from src.adaptation.dataset_builder import DatasetBuilder

builder = DatasetBuilder(trace_path="data/traces")

# High quality intent examples for C-LARA fine-tuning
examples = await builder.build_intent_dataset(
    min_quality=0.85,  # Only high-quality traces
    output_path="data/datasets/v1/clara_intent_dataset.jsonl",
    deduplicate=True  # Remove duplicates
)

print(f"Built {len(examples)} intent examples")
print(f"Average quality: {sum(e.quality_score for e in examples) / len(examples):.2f}")
```

### Example 2: Hard Negative Mining for Reranker

```python
from src.adaptation.dataset_builder import DatasetBuilder

builder = DatasetBuilder(trace_path="data/traces/traces.jsonl")

# Hard negatives: high-ranked but not cited
hard_negatives = await builder.build_rerank_dataset(
    sampling="hard_negatives",
    min_score_diff=0.2,  # Challenging pairs (close scores)
    output_path="data/datasets/v1/hard_negatives.jsonl"
)

print(f"Mined {len(hard_negatives)} hard negative pairs")
```

### Example 3: Dataset Statistics

```python
from src.adaptation.dataset_builder import DatasetBuilder

builder = DatasetBuilder(trace_path="data/traces")

examples = await builder.build_intent_dataset(
    min_quality=0.8,
    output_path="data/datasets/v1/intent_dataset.jsonl"
)

# Compute statistics
from collections import Counter
intent_counts = Counter(e.intent for e in examples)

print("Intent Distribution:")
for intent, count in intent_counts.items():
    print(f"  {intent}: {count} ({count/len(examples)*100:.1f}%)")
```

## Related Features

- **Feature 67.5**: UnifiedTracer (trace generation)
- **Feature 67.6**: Eval Harness (quality scoring)
- **Feature 67.8**: Adaptive Reranker (uses rerank dataset)
- **Feature 67.9**: Query Rewriter (uses rewrite dataset)
- **Feature 67.10**: C-LARA Data Generation (synthetic intent data)
- **Feature 67.11**: C-LARA Model Training (uses intent dataset)

## References

- [Sprint 67 Plan](../../docs/sprints/SPRINT_67_PLAN.md)
- [Paper 2512.16301: Tool-Level LLM Adaptation](https://arxiv.org/abs/2512.16301)
- [TD-075: LLM Intent Classifier (C-LARA)](../../docs/technical-debt/TD-075_LLM_INTENT_CLASSIFIER_CLARA.md)

## License

Copyright 2025 AegisRAG Project
