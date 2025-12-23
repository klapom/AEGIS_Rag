# BM25 Cache Discrepancy - Technical Debt

**Status:** Open
**Priority:** Medium
**Sprint:** Post-58
**Discovered:** 2025-12-20 during Sprint 53-58 refactoring validation

## Issue Description

The BM25 index cache shows a significant discrepancy between the number of documents loaded from disk cache versus the number of documents actually indexed in Qdrant.

### Symptoms

**Backend startup logs:**
```
BM25 index loaded from disk - corpus_size=10
```

**Admin dashboard shows:**
- 43 documents indexed in Qdrant
- Collection: `documents_v1`
- Namespace: `default`

**Discrepancy:** 10 cached documents vs. 43 indexed documents = 33 documents missing from BM25 cache

## Impact

- **Hybrid search accuracy:** BM25 component only has access to 10/43 documents, reducing recall
- **Search quality:** Users may get incomplete results from hybrid queries
- **Performance:** BM25 cache should improve performance, but stale cache degrades results

## Root Cause Analysis

### Likely Causes

1. **Cache Invalidation Issue:** BM25 cache not being refreshed after document ingestion
2. **Race Condition:** Cache being saved before all documents are indexed
3. **Namespace Mismatch:** Cache saving/loading filtering by wrong namespace
4. **Partial Index:** Cache corruption or incomplete write

### Investigation Steps

1. Check `src/components/vector_search/bm25_retriever.py` cache save/load logic
2. Verify cache path and permissions: Check BM25 cache file location
3. Review ingestion pipeline to ensure cache refresh is called
4. Check if cache is namespace-aware

## Temporary Workaround

**Manual cache refresh:**
```bash
# Option 1: Delete cache and force rebuild
rm -f /path/to/bm25_cache/*.pkl

# Option 2: Restart backend to trigger rebuild
docker compose restart api
```

## Proposed Solution

### Short-term (Sprint 59)
1. Add cache validation on startup (compare cache size with Qdrant count)
2. Auto-refresh cache if discrepancy > 10% detected
3. Log warnings when cache is stale

### Long-term (Sprint 60+)
1. Implement namespace-aware BM25 caching
2. Add cache versioning and checksum validation
3. Implement incremental cache updates (don't rebuild entire cache on each insert)
4. Add admin API endpoint to manually trigger cache refresh

## Related Code

- `src/components/vector_search/bm25_retriever.py` - BM25 cache implementation
- `src/components/retrieval/four_way_hybrid_search.py` - Uses BM25 for hybrid search
- `src/components/ingestion/langgraph_pipeline.py` - Ingestion pipeline that should update cache

## Testing Considerations

- Add integration test to verify cache consistency after ingestion
- Test cache behavior across multiple namespaces
- Verify cache refresh on collection recreation

## References

- Sprint 41: Namespace isolation feature
- Sprint 53-58: Refactoring that may have affected cache logic
- ADR-039: Adaptive chunking (affects document count)

---

**Next Steps:**
1. Investigate cache save/load logic in BM25 retriever
2. Add cache validation and auto-refresh
3. Create unit tests for cache consistency
