# TD-098: Cross-Encoder Fine-tuning in Domain Training UI/API

**Status:** OPEN
**Priority:** MEDIUM
**Story Points:** 8 SP
**Created:** 2026-01-09
**Sprint:** Sprint 82+ (planned)

---

## Problem Statement

**Cross-encoder reranker cannot be domain-fine-tuned** - The `BAAI/bge-reranker-v2-m3` model is currently used as-is without any domain-specific fine-tuning. For specialized domains (legal, medical, technical documentation), fine-tuning could significantly improve:
- Context Precision (+10-20% expected)
- Faithfulness (+5-10% through better context selection)

### Current State

```python
# src/components/retrieval/reranker.py:293-298
self._model = CrossEncoder(
    self.model_name,  # BAAI/bge-reranker-v2-m3
    max_length=512,
    device="cpu",  # CPU sufficient for inference
    cache_dir=str(self.cache_dir),
)
```

**Missing**:
1. Fine-tuning pipeline for cross-encoder with domain-specific data
2. Integration with Domain Training UI (existing: `/api/v1/domains/domain_id/train`)
3. Per-domain model selection (domain → fine-tuned reranker model path)
4. Evaluation metrics for fine-tuned vs base model

---

## Impact

### Without Domain Fine-tuning

**Current limitations**:
1. Reranker uses generic model trained on MS-MARCO / general web data
2. Domain-specific terminology may not be optimally ranked
3. Multi-lingual domains (DE/EN) might not achieve optimal rankings
4. Specialized jargon (legal, medical, technical) not prioritized

### Expected Improvements with Fine-tuning

| Metric | Base Model | Fine-tuned (Est.) | Improvement |
|--------|------------|-------------------|-------------|
| Context Precision | 0.717 | 0.80-0.85 | +12-18% |
| Faithfulness | 0.520 | 0.55-0.60 | +6-15% |
| Answer Relevancy | 0.859 | 0.88-0.92 | +2-7% |

---

## Proposed Solution

### Phase 1: Fine-tuning Pipeline (5 SP)

**Create training pipeline**:

```python
# scripts/fine_tune_reranker.py (NEW)
from sentence_transformers import CrossEncoder, InputExample
from sentence_transformers.cross_encoder import CrossEncoderTrainingArguments

def fine_tune_cross_encoder(
    domain_id: str,
    training_data: list[InputExample],
    base_model: str = "BAAI/bge-reranker-v2-m3",
    output_dir: str = "data/models/rerankers/{domain_id}",
):
    """Fine-tune cross-encoder on domain-specific data."""
    model = CrossEncoder(base_model)

    args = CrossEncoderTrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=16,
        learning_rate=2e-5,
        num_train_epochs=3,
        warmup_ratio=0.1,
    )

    model.fit(
        train_dataloader=training_data,
        training_args=args,
    )
    return output_dir
```

**Training data format** (from Domain Training UI exports):

```python
# InputExample for cross-encoder fine-tuning
examples = [
    InputExample(texts=[query, positive_passage], label=1.0),  # Relevant
    InputExample(texts=[query, negative_passage], label=0.0),  # Not relevant
]
```

### Phase 2: Domain Training API Integration (2 SP)

**Extend existing Domain Training endpoint**:

```python
# src/api/v1/domains/routes.py

@router.post("/{domain_id}/train/reranker")
async def train_domain_reranker(
    domain_id: str,
    training_config: RerankerTrainingConfig,
) -> RerankerTrainingResponse:
    """Fine-tune cross-encoder for a specific domain."""
    # 1. Load domain chunks as training data
    # 2. Generate positive/negative pairs from search logs
    # 3. Run fine-tuning pipeline
    # 4. Save to domain-specific path
    # 5. Update domain config to use fine-tuned model
```

### Phase 3: Model Selection & Caching (1 SP)

**Per-domain model loading**:

```python
# src/components/retrieval/reranker.py

def get_reranker_model(domain_id: str | None = None) -> CrossEncoder:
    """Load domain-specific reranker if available."""
    if domain_id:
        domain_model_path = f"data/models/rerankers/{domain_id}"
        if Path(domain_model_path).exists():
            return CrossEncoder(domain_model_path)

    # Fallback to base model
    return CrossEncoder(settings.reranker_model)
```

---

## Training Data Sources

### 1. Search Logs (Implicit Feedback)

**Source**: Click-through data from chat sessions
```sql
-- Extract query-document pairs with implicit relevance
SELECT query, chunk_id,
       CASE WHEN clicked THEN 1.0 ELSE 0.0 END as relevance
FROM search_logs
WHERE domain_id = :domain_id
```

### 2. RAGAS Evaluations (Explicit Feedback)

**Source**: RAGAS ground truth data
```python
# From ragas_eval_*.jsonl files
# Positive: contexts mentioned in ground_truth
# Negative: contexts NOT mentioned in ground_truth
```

### 3. Domain Expert Annotations (Gold Standard)

**Source**: Manual labeling via Domain Training UI
- Query + Document + Relevance score (1-5)
- Export as training pairs

---

## Testing Strategy

### Evaluation Metrics

| Metric | Measurement Method |
|--------|-------------------|
| **NDCG@5** | Compare rankings vs expert labels |
| **Context Precision** | RAGAS evaluation (before/after fine-tuning) |
| **Inference Latency** | Must stay <20ms/pair |
| **Model Size** | Must fit in memory (<1GB) |

### A/B Testing

```python
# 50/50 traffic split for new domains
if random.random() < 0.5:
    reranker = fine_tuned_model
else:
    reranker = base_model
# Log metrics for comparison
```

---

## Dependencies

- **TD-097:** Settings UI Integration (for training config UI)
- **Domain Training UI:** Already exists at `/admin/domains`
- **Search Logs:** Requires logging click-through data (not implemented)

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `scripts/fine_tune_reranker.py` | CREATE | Fine-tuning pipeline script |
| `src/api/v1/domains/routes.py` | MODIFY | Add `/train/reranker` endpoint |
| `src/components/retrieval/reranker.py` | MODIFY | Per-domain model selection |
| `src/core/schemas/domain.py` | MODIFY | Add `reranker_model_path` to DomainConfig |
| `frontend/src/pages/DomainTraining.tsx` | MODIFY | Add reranker training UI |

---

## Related

- **Feature 80.3:** Cross-Encoder Reranking (COMPLETE) - Base implementation
- **TD-097:** Settings UI Integration - Admin toggles
- **RAGAS_JOURNEY.md Experiment #4:** Reranking evaluation results
- **ADR-024:** BGE-M3 Embeddings (same model family)

---

## Sprint Allocation

| Phase | SP | Sprint |
|-------|-----|--------|
| Phase 1: Fine-tuning Pipeline | 5 | Sprint 82 |
| Phase 2: API Integration | 2 | Sprint 82 |
| Phase 3: Model Selection | 1 | Sprint 82 |
| **Total** | **8** | **Sprint 82** |

---

## Success Criteria

1. ✅ Fine-tuning pipeline works with domain data
2. ✅ API endpoint triggers training for a domain
3. ✅ Domain-specific model loaded when available
4. ✅ RAGAS Context Precision improves +10% for fine-tuned domains
5. ✅ Inference latency remains <20ms/pair
