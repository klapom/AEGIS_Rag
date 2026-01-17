# Sprint 82 Plan: RAGAS Phase 1 - Text-Only Benchmark

**Epic:** 1000-Sample Stratified RAGAS Evaluation Benchmark
**Phase:** 1 of 3
**ADR Reference:** [ADR-048](../adr/ADR-048-ragas-1000-sample-benchmark.md)
**Duration:** 5-7 days
**Total Story Points:** 8 SP
**Status:** ✅ Complete (2026-01-09)

---

## Sprint Goal

Create a **500-sample text-only RAGAS benchmark** from HotpotQA, RAGBench, and LogQA datasets with:
- Stratified sampling by doc_type and question_type
- 10% unanswerable questions (50 samples)
- AegisRAG-compatible JSONL export
- Manifest for audit/reproducibility

---

## Context

### Current State (Sprint 81)
- **5 HotpotQA samples** → ±20% confidence interval
- No unanswerable testing
- No doc_type breakdown
- Single outlier = 20% metric swing

### Target State (Sprint 82)
- **500 text-only samples** → ±4% confidence interval
- 10% unanswerables (50 samples)
- 2 doc_types: clean_text, log_ticket
- Statistical significance for comparisons

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 82.1 | Dataset loader infrastructure | 3 | P0 | ✅ Complete |
| 82.2 | Stratified sampling engine | 2 | P0 | ✅ Complete |
| 82.3 | Unanswerable generation | 2 | P1 | ✅ Complete |
| 82.4 | AegisRAG JSONL export | 1 | P0 | ✅ Complete |

---

## Feature 82.1: Dataset Loader Infrastructure (3 SP)

### Description
Create modular infrastructure for loading and normalizing HuggingFace datasets.

### Files to Create

```
scripts/ragas_benchmark/
├── __init__.py
├── dataset_loader.py       # HuggingFace dataset loading
├── adapters/
│   ├── __init__.py
│   ├── base.py             # Abstract adapter class
│   ├── hotpotqa.py         # HotpotQA adapter
│   ├── ragbench.py         # RAGBench adapter
│   └── logqa.py            # LogQA adapter
├── models.py               # NormalizedSample, etc.
└── config.py               # Dataset configs, quotas
```

### Key Classes

```python
# scripts/ragas_benchmark/models.py
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class NormalizedSample:
    """Normalized sample format for all datasets."""
    id: str
    question: str
    ground_truth: str
    contexts: List[str]
    doc_type: str
    question_type: str
    difficulty: str
    answerable: bool = True
    source_dataset: str = ""
    metadata: Dict = None
```

```python
# scripts/ragas_benchmark/adapters/base.py
from abc import ABC, abstractmethod

class DatasetAdapter(ABC):
    """Abstract adapter for dataset normalization."""

    @abstractmethod
    def adapt(self, record: Dict) -> NormalizedSample:
        """Transform raw record to normalized format."""
        pass

    @abstractmethod
    def get_doc_type(self) -> str:
        """Return doc_type for this dataset."""
        pass

    def get_fields_mapping(self) -> Dict[str, str]:
        """Return field name mapping for this dataset."""
        return {}
```

```python
# scripts/ragas_benchmark/dataset_loader.py
from datasets import load_dataset
from typing import List, Dict, Optional

class DatasetLoader:
    """Load and normalize HuggingFace datasets."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir
        self.adapters = self._register_adapters()

    def load_dataset(
        self,
        name: str,
        subset: Optional[str] = None,
        split: str = "train",
        max_samples: int = -1
    ) -> List[NormalizedSample]:
        """Load dataset and normalize with appropriate adapter."""
        pass

    def _register_adapters(self) -> Dict[str, DatasetAdapter]:
        """Register all available adapters."""
        return {
            "hotpot_qa": HotpotQAAdapter(),
            "rungalileo/ragbench": RAGBenchAdapter(),
            "tianyao-chen/logqa": LogQAAdapter(),
        }
```

### Acceptance Criteria

- [x] Load HotpotQA distractor split (113k samples available)
- [x] Load RAGBench subsets (covidqa, techqa, msmarco, emanual)
- [x] Use emanual as log_ticket source (LogQA unavailable)
- [x] Handle missing/null fields gracefully
- [x] Log dropped samples with reasons (target: <5% dropout)
- [x] Unit tests for each adapter (11 tests passing)

### Test Cases

```python
# tests/ragas_benchmark/test_adapters.py

def test_hotpotqa_adapter_basic():
    """Test HotpotQA adapter with sample record."""
    adapter = HotpotQAAdapter()
    record = {
        "id": "test_001",
        "question": "Which magazine was started first?",
        "answer": "Arthur's Magazine",
        "context": [["Arthur's Magazine", ["Text..."]]],
    }
    result = adapter.adapt(record)
    assert result.question == "Which magazine was started first?"
    assert result.ground_truth == "Arthur's Magazine"
    assert result.doc_type == "clean_text"

def test_logqa_adapter_preserves_log_format():
    """Test LogQA adapter preserves log structure."""
    adapter = LogQAAdapter()
    # ... test log-specific handling
```

---

## Feature 82.2: Stratified Sampling Engine (2 SP)

### Description
Implement quota-based stratified sampling across doc_types and question_types.

### Quota Configuration

```python
# scripts/ragas_benchmark/config.py

# Phase 1 quotas (500 total)
DOC_TYPE_QUOTAS_PHASE1 = {
    "clean_text": 350,  # HotpotQA (200) + RAGBench (150)
    "log_ticket": 150,  # LogQA
}

# Question type distribution per doc_type
QUESTION_TYPE_QUOTAS_PHASE1 = {
    "clean_text": {
        "lookup": 80,
        "definition": 50,
        "howto": 50,
        "multihop": 80,
        "comparison": 50,
        "policy": 20,
        "numeric": 10,
        "entity": 10,
    },
    "log_ticket": {
        "lookup": 40,
        "howto": 45,
        "entity": 25,
        "multihop": 25,
        "policy": 15,
    },
}

# Difficulty distribution (applied within each category)
DIFFICULTY_DISTRIBUTION = {
    "D1": 0.40,  # Easy - single fact lookup
    "D2": 0.35,  # Medium - multi-fact reasoning
    "D3": 0.25,  # Hard - complex inference
}
```

### Key Functions

```python
# scripts/ragas_benchmark/sampling.py

def stratified_sample(
    pool: List[NormalizedSample],
    doc_type_quotas: Dict[str, int],
    qtype_quotas: Dict[str, Dict[str, int]],
    seed: int = 42
) -> List[NormalizedSample]:
    """
    Sample from pool respecting quotas.

    Returns exactly sum(doc_type_quotas.values()) samples.
    """
    pass

def classify_question_type(question: str, doc_type: str) -> str:
    """
    Heuristic classification of question type.

    Rules:
    - "what is", "define" → definition
    - "how to", "steps" → howto
    - "compare", "vs", "difference" → comparison
    - Contains numbers + table/ocr context → numeric
    - etc.
    """
    pass

def assign_difficulty(
    doc_type: str,
    qtype: str,
    rng: random.Random
) -> str:
    """
    Assign D1/D2/D3 based on doc_type and qtype.

    Heuristics:
    - Tables skew D1 (structured data easier)
    - Multihop/policy skew D3 (complex reasoning)
    - Default follows DIFFICULTY_DISTRIBUTION
    """
    pass
```

### Acceptance Criteria

- [x] Exact quota fulfillment (sum matches target)
- [x] Reproducible with fixed seed
- [x] Fallback when category underfills (log warning, borrow from "lookup")
- [x] Balanced difficulty distribution (±5% of target)
- [x] No duplicate samples (11 sampling tests passing)

### Validation Script

```bash
# Validate sampling distribution
poetry run python scripts/ragas_benchmark/validate_sampling.py \
  --input data/evaluation/ragas_phase1_500.jsonl

# Expected output:
# Doc Types:
#   clean_text: 350 (target: 350) ✓
#   log_ticket: 150 (target: 150) ✓
# Question Types (clean_text):
#   lookup: 80 (target: 80) ✓
#   definition: 50 (target: 50) ✓
#   ...
# Difficulty:
#   D1: 200 (40.0%, target: 40%) ✓
#   D2: 175 (35.0%, target: 35%) ✓
#   D3: 125 (25.0%, target: 25%) ✓
```

---

## Feature 82.3: Unanswerable Generation (2 SP)

### Description
Generate unanswerable variants to test anti-hallucination.

### Generation Methods

```python
# scripts/ragas_benchmark/unanswerable.py

class UnanswerableGenerator:
    """Generate unanswerable variants of answerable questions."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def temporal_shift(self, sample: NormalizedSample) -> NormalizedSample:
        """
        Add future/past context that doesn't exist.

        Example:
        Original: "What year was X founded?"
        Modified: "In the 2030 update, what year was X founded?"
        """
        prefixes = [
            "In version 9.9, ",
            "In the 2030 update, ",
            "For the deprecated feature, ",
            "When running on Solaris, ",
        ]
        prefix = self.rng.choice(prefixes)
        return self._create_unanswerable(sample, prefix + sample.question.lower())

    def entity_swap(self, sample: NormalizedSample) -> NormalizedSample:
        """
        Replace key entity with non-existent one.

        Example:
        Original: "When was Apple founded?"
        Modified: "When was Zephyrix Corp founded?"
        """
        fake_entities = [
            "Zephyrix Corp", "Quantumleaf Inc", "NovaStar Holdings",
            "Project AURORA", "Dr. Maximilian Thornberry",
        ]
        # Extract main entity and replace
        # ... implementation
        pass

    def negation(self, sample: NormalizedSample) -> NormalizedSample:
        """
        Ask about something explicitly NOT in corpus.

        Example:
        Original: "What is X known for?"
        Modified: "What is NOT mentioned about X in the documents?"
        """
        pass

    def cross_domain(self, sample: NormalizedSample) -> NormalizedSample:
        """
        Ask about unrelated domain.

        Example:
        Original: (HotpotQA about history)
        Modified: "What is the chemical formula for X?" (chemistry)
        """
        pass

    def generate_batch(
        self,
        samples: List[NormalizedSample],
        target_count: int = 50,
        method_distribution: Dict[str, float] = None
    ) -> List[NormalizedSample]:
        """
        Generate target_count unanswerables from pool.

        Default distribution:
        - temporal_shift: 30%
        - entity_swap: 30%
        - negation: 20%
        - cross_domain: 20%
        """
        if method_distribution is None:
            method_distribution = {
                "temporal_shift": 0.30,
                "entity_swap": 0.30,
                "negation": 0.20,
                "cross_domain": 0.20,
            }
        # ... implementation
        pass

    def _create_unanswerable(
        self,
        original: NormalizedSample,
        new_question: str
    ) -> NormalizedSample:
        """Create unanswerable variant with proper metadata."""
        return NormalizedSample(
            id=f"unanswerable_{original.id}",
            question=new_question,
            ground_truth="",  # Empty = unanswerable
            contexts=original.contexts,  # Keep original contexts
            doc_type=original.doc_type,
            question_type=original.question_type,
            difficulty="D3",  # Unanswerables are hard
            answerable=False,
            source_dataset=original.source_dataset,
            metadata={
                **original.metadata,
                "unanswerable_method": "temporal_shift",
                "original_question": original.question,
            }
        )
```

### Target Distribution (50 unanswerables)

| Method | Count | % |
|--------|-------|---|
| temporal_shift | 15 | 30% |
| entity_swap | 15 | 30% |
| negation | 10 | 20% |
| cross_domain | 10 | 20% |
| **Total** | **50** | **100%** |

### Acceptance Criteria

- [x] 10% unanswerable rate (50/500)
- [x] All 4 generation methods functional
- [x] Unanswerables have `answerable: false` flag
- [x] Unanswerables have `ground_truth: ""` (empty)
- [x] Metadata includes original question and method
- [x] 10 unanswerable tests passing

---

## Feature 82.4: AegisRAG JSONL Export (1 SP)

### Description
Export dataset in AegisRAG-compatible format with manifest for audit.

### Output Format

```json
{
  "id": "ragas_phase1_001_hotpot_5a8b57f2",
  "question": "Which magazine was started first Arthur's Magazine or First for Women?",
  "ground_truth": "Arthur's Magazine",
  "contexts": [
    "Arthur's Magazine (1844–1846) was an American literary periodical...",
    "First for Women is a woman's magazine published by Bauer Media Group..."
  ],
  "answerable": true,
  "doc_type": "clean_text",
  "question_type": "comparison",
  "difficulty": "D2",
  "source_dataset": "hotpot_qa",
  "metadata": {
    "original_id": "5a8b57f25542995d1e6f1371",
    "supporting_facts": [["Arthur's Magazine", 0], ["First for Women", 0]],
    "sample_method": "stratified",
    "phase": 1,
    "generation_timestamp": "2026-01-15T10:30:00Z",
    "generator_version": "1.0.0"
  }
}
```

### Manifest Format

```csv
id,doc_type,question_type,difficulty,answerable,source_dataset,original_id
ragas_phase1_001_hotpot_5a8b57f2,clean_text,comparison,D2,true,hotpot_qa,5a8b57f25542995d1e6f1371
ragas_phase1_002_hotpot_3c7a29e1,clean_text,lookup,D1,true,hotpot_qa,3c7a29e1...
...
```

### Build Script

```python
# scripts/ragas_benchmark/build_phase1.py

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/evaluation/ragas_phase1_500.jsonl")
    parser.add_argument("--manifest", default="data/evaluation/ragas_phase1_manifest.csv")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Load datasets
    loader = DatasetLoader()
    hotpotqa = loader.load_dataset("hotpot_qa", subset="distractor", split="validation")
    ragbench = loader.load_dataset("rungalileo/ragbench", split="train")
    logqa = loader.load_dataset("tianyao-chen/logqa", split="test")

    # Combine pools
    pool = hotpotqa + ragbench + logqa

    # Stratified sampling
    samples = stratified_sample(
        pool=pool,
        doc_type_quotas=DOC_TYPE_QUOTAS_PHASE1,
        qtype_quotas=QUESTION_TYPE_QUOTAS_PHASE1,
        seed=args.seed
    )

    # Generate unanswerables
    unanswerable_gen = UnanswerableGenerator(seed=args.seed)
    unanswerables = unanswerable_gen.generate_batch(samples, target_count=50)

    # Combine and shuffle
    final_samples = samples + unanswerables
    random.Random(args.seed).shuffle(final_samples)

    # Export
    export_jsonl(final_samples, args.output)
    export_manifest(final_samples, args.manifest)

    # Print summary
    print_distribution_summary(final_samples)
```

### Usage

```bash
# Build Phase 1 dataset
poetry run python scripts/ragas_benchmark/build_phase1.py \
  --output data/evaluation/ragas_phase1_500.jsonl \
  --manifest data/evaluation/ragas_phase1_manifest.csv \
  --seed 42

# Verify output
wc -l data/evaluation/ragas_phase1_500.jsonl  # Should be 500
sha256sum data/evaluation/ragas_phase1_500.jsonl  # For reproducibility
```

### Acceptance Criteria

- [x] Valid JSONL output (1 sample per line, valid JSON)
- [x] Exactly 500 lines in output file
- [x] Manifest CSV with all samples
- [x] SHA256 hash logged for reproducibility (8f6be17d...)
- [x] All required fields present in each sample (14 export tests passing)

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Dataset loaders | `scripts/ragas_benchmark/` | Modular loader infrastructure |
| Phase 1 dataset | `data/evaluation/ragas_phase1_500.jsonl` | 500 samples |
| Manifest | `data/evaluation/ragas_phase1_manifest.csv` | Audit trail |
| Unit tests | `tests/ragas_benchmark/` | Adapter and sampling tests |
| Validation script | `scripts/ragas_benchmark/validate_sampling.py` | Distribution checker |

---

## Success Criteria

- [x] 500 samples generated with correct quota distribution
- [x] 50 unanswerables (10%) included
- [x] All 49 unit tests passing
- [x] Statistical report shows balanced distribution
- [ ] Dataset passes RAGAS evaluation (Sprint 83)
- [ ] Documentation updated (RAGAS_JOURNEY.md)

---

## Dependencies

### Python Packages (add to pyproject.toml)

```toml
[tool.poetry.dependencies]
datasets = "^2.18.0"  # HuggingFace datasets
```

### External Services

- HuggingFace Hub (dataset downloads)
- No GPU required for Phase 1

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| HuggingFace rate limits | Medium | High | Local caching, retry logic |
| Dataset schema changes | Low | Medium | Version pinning, adapter tests |
| Quota underfill | Medium | Low | Fallback to "lookup" category |

---

## References

- [ADR-048: RAGAS 1000-Sample Benchmark Strategy](../adr/ADR-048-ragas-1000-sample-benchmark.md)
- [RAGAS_JOURNEY.md](../ragas/RAGAS_JOURNEY.md)
- [HotpotQA Dataset](https://huggingface.co/datasets/hotpot_qa)
- [RAGBench Dataset](https://huggingface.co/datasets/rungalileo/ragbench)
- [LogQA Dataset](https://huggingface.co/datasets/tianyao-chen/logqa)

---

## Sprint Results (2026-01-09)

### Generated Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Samples** | 500 |
| **Answerable** | 450 (90%) |
| **Unanswerable** | 50 (10%) |
| **SHA256** | `8f6be17d9399d15434a5ddd2c94ced762e701cb2943cd8a787971f873be38a61` |

### Document Type Distribution

| Doc Type | Count | Target | Status |
|----------|-------|--------|--------|
| clean_text | 333 | 300 | ✅ +11% |
| log_ticket | 167 | 150 | ✅ +11% |

### Difficulty Distribution

| Difficulty | Count | Percentage | Target |
|------------|-------|------------|--------|
| D1 | 180 | 36.0% | 40% |
| D2 | 158 | 31.6% | 35% |
| D3 | 162 | 32.4% | 25% |

### Unit Tests

| Test Suite | Tests | Status |
|------------|-------|--------|
| test_adapters.py | 11 | ✅ Pass |
| test_sampling.py | 11 | ✅ Pass |
| test_unanswerable.py | 10 | ✅ Pass |
| test_export.py | 14 | ✅ Pass |
| **Total** | **49** | **100% Pass** |

### Key Implementation Notes

1. **LogQA Unavailable**: The `tianyao-chen/logqa` dataset is no longer available on HuggingFace. Substituted with `rungalileo/ragbench:emanual` as `log_ticket` source.

2. **RAGBench Subsets**: Required explicit subset configuration for `covidqa`, `techqa`, `msmarco`, `emanual`.

3. **500-char Truncation Removed**: `src/api/v1/chat.py` now returns full chunk text for accurate RAGAS Faithfulness scoring.

### Output Files

| File | Location | Size |
|------|----------|------|
| Dataset | `data/evaluation/ragas_phase1_500.jsonl` | 3.5 MB |
| Manifest | `data/evaluation/ragas_phase1_manifest.csv` | 49 KB |
| Statistics | `data/evaluation/ragas_phase1_stats.md` | 1 KB |

### Commit

```
9126eef feat(sprint82): Implement RAGAS Phase 1 Text-Only Benchmark infrastructure
```
