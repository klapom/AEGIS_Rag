# TD-099: Namespace Not Set During RAGAS Ingestion

**Priority:** High
**Effort:** 3 SP → 1 SP (actual)
**Sprint:** 81
**Status:** ✅ RESOLVED (2026-01-09)
**Created:** 2026-01-09 (Sprint 80)
**Resolved:** 2026-01-09 (Sprint 81)

## Problem

The `ingest_ragas_simple.py` script accepts a `--namespace` parameter but the namespace is **not persisted** in Qdrant payloads.

### Evidence

```bash
# Ingestion with namespace parameter
poetry run python scripts/ingest_ragas_simple.py \
  --dataset data/evaluation/ragas_hotpotqa_15.jsonl \
  --namespace ragas_eval \
  --max-docs 15

# Result: namespace is NULL in Qdrant
curl -s "http://localhost:6333/collections/documents_v1/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{"limit": 3, "with_payload": ["namespace", "document_id"]}' | jq

# Output:
{
  "namespace": null,   # <-- Expected: "ragas_eval"
  "doc_id": "ragas_f8f486f5b1d0"
}
```

### Root Cause Analysis

1. `create_initial_state()` correctly accepts `namespace_id` parameter
2. State is passed to `embedding_node()` for Qdrant upload
3. **BUG:** The `embedding_node` or underlying Qdrant uploader is NOT:
   - Reading `namespace_id` from state, OR
   - Setting `namespace` field in Qdrant payload

### Files to Investigate

```
src/components/ingestion/langgraph_nodes.py  # embedding_node()
src/components/ingestion/ingestion_state.py  # create_initial_state()
src/components/retrieval/qdrant_client.py    # upsert_points()
```

## Impact

- **RAGAS Evaluation:** Cannot filter by namespace → retrieves unrelated documents
- **Multi-tenant Isolation:** Namespace isolation (TD-084) is broken for RAGAS dataset
- **Domain Isolation:** Related DSPy domain-specific prompts cannot be scoped

## Acceptance Criteria

1. [x] `ingest_ragas_simple.py --namespace ragas_eval` stores `namespace_id: "ragas_eval"` in Qdrant ✅
2. [x] Verify with Qdrant scroll query that namespace_id field is populated ✅ (15 points)
3. [x] RAGAS evaluation with `--namespace ragas_eval` retrieves only RAGAS documents ✅
4. [ ] Unit test for namespace propagation through ingestion pipeline (deferred)

## Resolution (2026-01-09)

**Root Cause:** Field name mismatch between ingestion and retrieval:
- Ingestion wrote `namespace_id` to Qdrant payload ✅ (correct)
- Retrieval filtered by `namespace` ❌ (wrong field name)

**Fix:** Changed retrieval filters to use `namespace_id`:
- `src/components/retrieval/filters.py:222` - `key="namespace"` → `key="namespace_id"`
- `src/components/retrieval/four_way_hybrid_search.py:448` - `key="namespace"` → `key="namespace_id"`
- `scripts/ingest_ragas_simple.py:220,232` - verify function updated

**Verification:**
```bash
# Qdrant shows correct namespace_id
curl "http://localhost:6333/collections/documents_v1/points/count" \
  -d '{"filter":{"must":[{"key":"namespace_id","match":{"value":"ragas_eval"}}]}}'
# Result: {"count": 15}
```

## Workaround

Run RAGAS evaluation without namespace filtering (empty string):

```bash
poetry run python scripts/run_ragas_evaluation.py \
  --dataset data/evaluation/ragas_hotpotqa_15.jsonl \
  --namespace "" \
  --mode hybrid
```

## Related

- TD-084: Namespace Isolation (Sprint 75)
- TD-085: DSPy Domain-Specific Prompts
- `scripts/ingest_ragas_simple.py:117-124` - create_initial_state() call
