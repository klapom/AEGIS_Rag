# Sprint 44: Relation Deduplication & Full Pipeline Evaluation

**Status:** IN PROGRESS
**Start:** 2025-12-12
**Priority:** High (Knowledge Graph Quality + Benchmarking)
**Prerequisites:** Sprint 43 complete (Multi-Criteria Entity Deduplication)

---

## Objective

Implement Relation Deduplication (TD-063) to complete the deduplication pipeline, add production-grade monitoring, and evaluate the full pipeline across multiple LLM models with the same HotPotQA dataset.

---

## Reference Documents

| Document | Content |
|----------|---------|
| `docs/technical-debt/TD-063_RELATION_DEDUPLICATION.md` | Relation Dedup specification |
| `docs/adr/ADR-044_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md` | Entity Dedup architecture |
| `docs/sprints/SPRINT_43_PLAN.md` | Entity Dedup implementation |
| `reports/ragas_txt_pipeline_eval_20251211_160655.json` | Sprint 43 baseline (without Relation Dedup) |

---

## Part 1: Relation Deduplication (TD-063)

### Feature 44.1: RelationDeduplicator Implementation 📋
**Deliverables:**
- [ ] `RelationDeduplicator` class in new file
- [ ] 3-stage deduplication pipeline
- [ ] Integration with entity deduplication flow
- [ ] Config options for enabling/disabling

**Files:**
- `src/components/graph_rag/relation_deduplicator.py` (NEW)

**Technical Details:**
- Stage 1: Entity name normalization
- Stage 2: Type synonym resolution
- Stage 3: Bidirectional relation handling

---

### Feature 44.2: Entity Name Normalization for Relations 📋
**Deliverables:**
- [ ] Modify entity deduplicator to return `entity_mapping: dict[str, str]`
- [ ] `normalize_entity_references()` method
- [ ] Remap relation source/target to canonical entity names

**Example:**
```python
# Before entity dedup: relation references "nicolas cage"
# After entity dedup: "nicolas cage" → "Nicolas Cage"
# Relation must be updated: source="Nicolas Cage"
```

---

### Feature 44.3: Type Synonym Resolution 📋
**Deliverables:**
- [ ] `RELATION_TYPE_SYNONYMS` mapping
- [ ] `_normalize_relation_type()` method
- [ ] Configurable via external JSON file (optional)

**Type Synonym Mapping:**
```python
RELATION_TYPE_SYNONYMS = {
    "ACTED_IN": ["STARRED_IN", "PLAYED_IN", "APPEARED_IN", "PERFORMED_IN"],
    "DIRECTED": ["DIRECTED_BY", "HELMED", "MADE"],
    "WRITTEN_BY": ["WROTE", "AUTHORED", "PENNED"],
    "MARRIED_TO": ["SPOUSE_OF", "WED_TO", "HUSBAND_OF", "WIFE_OF"],
    "WORKS_FOR": ["EMPLOYED_BY", "WORKS_AT", "MEMBER_OF"],
    "LOCATED_IN": ["BASED_IN", "SITUATED_IN", "FOUND_IN"],
}
```

---

### Feature 44.4: Bidirectional Relation Handling 📋
**Deliverables:**
- [ ] `SYMMETRIC_RELATIONS` set
- [ ] Bidirectional deduplication for symmetric relations
- [ ] Only one direction stored (sorted by entity name)

**Symmetric Relations:**
```python
SYMMETRIC_RELATIONS = {
    "KNOWS", "RELATED_TO", "MARRIED_TO", "COLLABORATED_WITH",
    "WORKS_WITH", "FRIENDS_WITH", "SIBLING_OF"
}
```

**Example:**
```python
# ("Alice", "KNOWS", "Bob") + ("Bob", "KNOWS", "Alice")
# → Only ("Alice", "KNOWS", "Bob") stored (alphabetically sorted)
```

---

### Feature 44.5: Integration with lightrag_wrapper.py 📋
**Deliverables:**
- [ ] Call `RelationDeduplicator` after entity deduplication
- [ ] Pass `entity_mapping` from entity dedup to relation dedup
- [ ] Prometheus metrics for relation deduplication
- [ ] Structured logging

**Files Modified:**
- `src/components/graph_rag/lightrag_wrapper.py`
- `src/components/graph_rag/semantic_deduplicator.py` (add `deduplicate_with_mapping`)

**Integration Point:**
```python
# After entity deduplication
deduplicated_entities, entity_mapping = deduplicator.deduplicate_with_mapping(entities)

# Relation deduplication
if settings.enable_relation_dedup:
    relation_deduplicator = RelationDeduplicator()
    deduplicated_relations = relation_deduplicator.deduplicate(
        relations, entity_mapping=entity_mapping
    )
```

---

### Feature 44.6: Unit Tests for Relation Deduplication 📋
**Deliverables:**
- [ ] Test type synonym resolution
- [ ] Test entity name normalization
- [ ] Test bidirectional/symmetric handling
- [ ] Test edge cases (empty relations, unknown types)

**Files:**
- `tests/unit/components/graph_rag/test_relation_deduplicator.py` (NEW)

**Test Cases:**
```python
def test_type_synonym_resolution():
    # STARRED_IN + ACTED_IN → 1 relation (ACTED_IN)

def test_entity_name_normalization():
    # "nicolas cage" → "Nicolas Cage" in relations

def test_bidirectional_symmetric():
    # ("Alice", "KNOWS", "Bob") + ("Bob", "KNOWS", "Alice") → 1 relation

def test_asymmetric_not_merged():
    # ("Alice", "PARENT_OF", "Bob") + ("Bob", "PARENT_OF", "Alice") → 2 relations
```

---

## Part 2: Pipeline Monitoring & Logging Enhancement

### Feature 44.7: PipelineMonitor Class 📋
**Deliverables:**
- [ ] `PipelineMonitor` class to collect metrics across all stages
- [ ] Context manager for stage timing
- [ ] Aggregation of metrics from all stages

**Files:**
- `src/monitoring/pipeline_monitor.py` (NEW)

**API:**
```python
class PipelineMonitor:
    def __init__(self, run_id: str, model: str):
        ...

    def start_stage(self, stage: str) -> StageContext:
        ...

    def record_metric(self, stage: str, metric: str, value: Any):
        ...

    def generate_report(self) -> dict:
        ...
```

---

### Feature 44.8: Structured Event Logging 📋
**Deliverables:**
- [ ] JSON event format for each pipeline stage
- [ ] Timestamps for start/end of each stage
- [ ] Error capture with stack traces

**Event Format:**
```json
{
  "event": "stage_complete",
  "stage": "extraction",
  "run_id": "eval_20251212_120000",
  "model": "qwen3:8b",
  "duration_seconds": 45.2,
  "metrics": {
    "entities_raw": 35,
    "relations_raw": 28
  },
  "timestamp": "2025-12-12T12:00:45.200Z"
}
```

---

### Feature 44.9: Report Generator 📋
**Deliverables:**
- [ ] JSON report with all pipeline metrics
- [ ] Markdown summary for human review
- [ ] Per-sample breakdown + aggregated totals

**Files:**
- `src/monitoring/report_generator.py` (NEW or extend pipeline_monitor.py)

**Report Structure:**
```
reports/
├── pipeline_eval_<model>_<timestamp>.json    # Full metrics
└── pipeline_eval_<model>_<timestamp>.md      # Human-readable summary
```

---

### Feature 44.10: Model-Configurable Extraction 📋
**Deliverables:**
- [ ] `--model` CLI parameter for evaluation script
- [ ] Dynamic model switching via environment variable
- [ ] Model name in all reports and logs

**Files Modified:**
- `scripts/pipeline_model_evaluation.py` (NEW or extend existing)

**Usage:**
```bash
poetry run python scripts/pipeline_model_evaluation.py \
  --model qwen3:8b \
  --samples 10 \
  --output-dir reports/
```

---

## Part 3: Multi-Model Pipeline Evaluation

### Feature 44.11: Evaluation Script with Model Parameter 📋
**Deliverables:**
- [ ] Main evaluation script with full pipeline
- [ ] Configurable model, samples, output directory
- [ ] Resume capability for interrupted runs

**Files:**
- `scripts/pipeline_model_evaluation.py` (NEW)

---

### Feature 44.12: HotPotQA TXT Dataset 📋
**Deliverables:**
- [ ] 10 HotPotQA samples as TXT files
- [ ] Consistent dataset across all model runs
- [ ] Dataset metadata (total chars, questions, ground truth)

**Dataset:**
- Source: `reports/track_a_evaluation/datasets/hotpotqa_large.jsonl`
- Samples: 10
- Total chars: 68,126
- Output: `/tmp/hotpotqa_txt_samples/` or `data/eval/hotpotqa_txt/`

---

### Feature 44.13: Model Runs - High Priority 📋
**Deliverables:**
- [ ] qwen3:32b run (NEW BASELINE with Relation Dedup)
- [ ] qwen3:8b run
- [ ] qwen2.5:7b run
- [ ] nuextract:3.8b run

**Expected Duration:** ~2-3 hours total

---

### Feature 44.14: Model Runs - Medium Priority 📋
**Deliverables:**
- [ ] gemma3:4b run
- [ ] qwen2.5:3b run

**Expected Duration:** ~1 hour total

---

### Feature 44.15: Comparison Report Generator 📋
**Deliverables:**
- [ ] Aggregated comparison across all models
- [ ] Quality vs Speed vs Size matrix
- [ ] Recommendation for production model

**Files:**
- `scripts/generate_model_comparison.py` (NEW)
- `reports/model_comparison_summary_<timestamp>.md`

**Comparison Matrix:**
```markdown
| Model | Entities | Relations | Entity Dedup % | Relation Dedup % | Time/Sample | Recommendation |
|-------|----------|-----------|----------------|------------------|-------------|----------------|
| qwen3:32b | 311 | ~200 | 10.1% | ~30% | 280s | Quality |
| qwen3:8b | ~280 | ~180 | ~9% | ~28% | ~90s | Balanced |
| qwen2.5:7b | ~260 | ~170 | ~8% | ~25% | ~70s | Speed |
| nuextract:3.8b | ~300 | ~190 | ~10% | ~30% | ~50s | Best Value? |
```

---

## Test Matrix

| Model | Size | Priority | Expected Time | Status |
|-------|------|----------|---------------|--------|
| qwen3:32b | 20 GB | BASELINE | ~47 min | 📋 |
| qwen3:8b | 5 GB | HIGH | ~15-20 min | 📋 |
| qwen2.5:7b | 4 GB | HIGH | ~12-18 min | 📋 |
| nuextract:3.8b | 2 GB | HIGH | ~10-15 min | 📋 |
| gemma3:4b | 3 GB | MEDIUM | ~10-15 min | 📋 |
| qwen2.5:3b | 1 GB | MEDIUM | ~8-12 min | 📋 |

**WICHTIG:** Sprint 43 Baseline enthält KEINE Relation Deduplication!
Alle Modelle werden mit vollständiger Pipeline (Entity + Relation Dedup) getestet.

---

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Full Pipeline with Monitoring                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TXT Files ──► Chunking ──► Extraction ──► Entity Dedup ──► Relation Dedup  │
│      │            │             │              │                │            │
│      ▼            ▼             ▼              ▼                ▼            │
│  [metrics]    [metrics]     [metrics]      [metrics]        [metrics]       │
│                                                                              │
│                              PipelineMonitor                                 │
│                                    │                                         │
│                                    ▼                                         │
│                           JSON + MD Report                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Metrics per Stage:**
| Stage | Metrics |
|-------|---------|
| Input | file_count, total_chars, avg_chars_per_file |
| Chunking | chunks_created, avg_chunk_size, overlap_chars, duration |
| Extraction | entities_raw, relations_raw, entity_types, relation_types, duration |
| Entity Dedup | before, after, reduction_%, criteria_distribution, duration |
| Relation Dedup | before, after, reduction_%, type_merges, bidirectional_merges, duration |

---

## Story Points Summary

| Part | Features | SP |
|------|----------|-----|
| Part 1: Relation Dedup | 44.1-44.6 | 16 |
| Part 2: Monitoring | 44.7-44.10 | 10 |
| Part 3: Evaluation | 44.11-44.15 | 12 |
| **Total** | **15 Features** | **38** |

---

## Success Criteria

### Part 1: Relation Deduplication
- [ ] 25-40% relation reduction on multi-chunk documents
- [ ] Type synonyms correctly merged (STARRED_IN → ACTED_IN)
- [ ] Entity references remapped to canonical names
- [ ] Symmetric relations deduplicated (A↔B only once)
- [ ] All unit tests passing

### Part 2: Pipeline Monitoring
- [ ] All pipeline stages emit structured JSON metrics
- [ ] PipelineMonitor collects and aggregates all metrics
- [ ] JSON + Markdown reports generated automatically
- [ ] Model name included in all logs and reports

### Part 3: Model Evaluation
- [ ] 6 models evaluated on identical dataset (10 HotPotQA samples)
- [ ] Comparison matrix with Quality/Speed/Size trade-offs
- [ ] Clear recommendation for production model
- [ ] All reports saved in `reports/` directory

---

## Sprint 43 Reference (WITHOUT Relation Dedup)

| Metric | Value |
|--------|-------|
| Samples | 10 |
| Input Chars | 68,126 |
| Chunks | 18 |
| Entities (raw → dedup) | 346 → 311 (10.1%) |
| Relations (NOT deduplicated) | 287 |
| Total Time | 2802.6s (~47 min) |

**Expected After Sprint 44:**
- Relations after dedup: ~180-200 (25-40% reduction)
- New baseline with qwen3:32b required

---

## Dependencies

- Sprint 43: Multi-Criteria Entity Deduplication (complete)
- `python-Levenshtein`: For edit distance (already installed)
- Ollama models: qwen3:32b, qwen3:8b, qwen2.5:7b, nuextract:3.8b, gemma3:4b, qwen2.5:3b

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Type synonym over-merging | Start with conservative mappings, make configurable |
| Model instability (gemma3:4b) | Skip unstable samples, report success rate |
| Long evaluation time (~4-6h) | Run overnight, parallelize where possible |
| Relation dedup breaks existing tests | Feature flag `enable_relation_dedup` |

---

## Files Created/Modified

### New Files
| File | Description |
|------|-------------|
| `src/components/graph_rag/relation_deduplicator.py` | RelationDeduplicator class |
| `src/monitoring/pipeline_monitor.py` | Pipeline monitoring and reporting |
| `tests/unit/components/graph_rag/test_relation_deduplicator.py` | Unit tests |
| `scripts/pipeline_model_evaluation.py` | Main evaluation script |
| `scripts/generate_model_comparison.py` | Comparison report generator |

### Modified Files
| File | Changes |
|------|---------|
| `src/components/graph_rag/semantic_deduplicator.py` | Add `deduplicate_with_mapping()` |
| `src/components/graph_rag/lightrag_wrapper.py` | Integrate relation dedup |
| `src/core/config.py` | Add relation dedup config options |
| `src/monitoring/metrics.py` | Add relation dedup Prometheus metrics |

---

## Date
2025-12-12
