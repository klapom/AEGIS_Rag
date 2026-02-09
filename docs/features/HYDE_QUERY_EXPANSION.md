# HyDE (Hypothetical Document Embeddings) Query Expansion

**Sprint 128 Feature 128.4**

## Overview

HyDE (Hypothetical Document Embeddings) is a query expansion technique that improves retrieval quality by generating a hypothetical answer document before performing the search. This produces embeddings that are semantically closer to actual relevant documents in the vector space, especially for abstract or complex queries.

## Architecture

```
User Query → LLM generates hypothetical answer → BGE-M3 embeds hypothetical → Qdrant search
          ↘ Original query embedding → Qdrant search (parallel)
          → RRF fusion of both result sets
```

### Integration with Maximum Hybrid Search

HyDE is integrated as the 5th signal in the Maximum Hybrid Search pipeline:

1. **Qdrant Embeddings** (semantic similarity)
2. **HyDE Embeddings** (hypothetical answer document) ← NEW
3. **BM25 Keywords** (exact keyword matching)
4. **Graph Local Search** (entity-level facts)
5. **Graph Global Search** (community/theme summaries)

All signals run in parallel and are fused using Reciprocal Rank Fusion (RRF).

## Configuration

HyDE can be configured via environment variables:

```bash
# Enable/disable HyDE (default: true)
HYDE_ENABLED=true

# Weight for HyDE results in RRF fusion (0.0-1.0, default: 0.5)
HYDE_WEIGHT=0.5

# Max tokens for hypothetical document generation (default: 512)
HYDE_MAX_TOKENS=512
```

## Usage

### Python API

```python
from src.components.retrieval.hyde import get_hyde_generator

# Get HyDE generator singleton
hyde = get_hyde_generator()

# Generate hypothetical document
hypothetical_doc = await hyde.generate_hypothetical_document(
    query="What are the benefits of HyDE?"
)
print(f"Hypothetical: {hypothetical_doc}")

# Search with HyDE
results = await hyde.hyde_search(
    query="What are the benefits of HyDE?",
    top_k=10,
    namespaces=["research_papers"]
)
print(f"Found {len(results)} results via HyDE")
```

### Maximum Hybrid Search

HyDE is automatically included when using Maximum Hybrid Search:

```python
from src.components.retrieval.maximum_hybrid_search import maximum_hybrid_search

result = await maximum_hybrid_search(
    query="What are the benefits of HyDE?",
    top_k=10,
    namespaces=["research_papers"]
)

# Check HyDE metadata
print(f"HyDE enabled: {result.hyde_enabled}")
print(f"HyDE results: {result.hyde_results_count}")
print(f"Hypothetical: {result.hypothetical_document}")
```

## Performance

### Target Metrics

- **Hypothetical Generation**: <100ms (with cache)
- **HyDE Search**: <200ms total (parallel with dense search)
- **Cache Hit Rate**: >90% for repeated queries

### Caching Strategy

HyDE uses Redis caching with a 24-hour TTL:

1. **Cache Key**: SHA256 hash of query
2. **Cache Location**: Redis key `hyde:{query_hash}`
3. **TTL**: 86400 seconds (24 hours)
4. **Cache Miss**: Generate hypothetical document via LLM

Cache hit rate is typically >90% for production workloads with repeated queries.

## When to Use HyDE

### HyDE Works Well For

✅ **Abstract queries** - "What are the philosophical implications of AI?"
✅ **Complex questions** - "How does climate change affect biodiversity?"
✅ **Information seeking** - "What are the benefits of meditation?"
✅ **Explanation requests** - "Explain quantum computing in simple terms"

### HyDE May Hurt Performance For

❌ **Keyword-heavy queries** - "amsterdam map pdf"
❌ **Entity lookups** - "John Smith contact info"
❌ **Code searches** - "function calculate_total"
❌ **Very specific facts** - "GDP of Netherlands in 2023"

For these cases, disable HyDE or reduce weight:

```bash
HYDE_ENABLED=false
# OR
HYDE_WEIGHT=0.2  # Reduce influence
```

## Academic Reference

**HyDE: Precise Zero-Shot Dense Retrieval without Relevance Labels**

- Authors: Gao et al., 2022
- arXiv: [2212.10496](https://arxiv.org/abs/2212.10496)
- Key Insight: Hypothetical documents are semantically closer to relevant documents than raw queries

## Implementation Details

### Hypothetical Document Generation

The LLM prompt for generating hypothetical documents:

```
Write a short passage (100-200 words) that would answer the following question:

{query}

Write as if you are providing a direct, informative answer. Be concise and factual.
```

**Key Parameters:**
- **Temperature**: 0.3 (low for consistent, factual output)
- **Max Tokens**: 512 (typical answers are 150-300 tokens)
- **Quality**: MEDIUM (not critical, but needs coherence)

### Embedding Strategy

HyDE uses **dense vectors only** (not sparse) because:
1. Hypothetical documents are semantic by nature (not keyword-based)
2. Dense embeddings capture meaning better than lexical matching
3. Simplifies fusion with other signals (all use dense + sparse)

### RRF Fusion

HyDE results are inserted into RRF fusion at position 2 (after dense search):

```python
rankings = [qdrant_chunks, hyde_chunks, bm25_chunks]
chunk_ranking = reciprocal_rank_fusion(rankings, k=60)
```

This ordering prioritizes semantic signals (dense + HyDE) over lexical (BM25).

## Testing

### Unit Tests

Run HyDE unit tests:

```bash
poetry run pytest tests/unit/components/retrieval/test_hyde.py -v
```

**Coverage:**
- Hypothetical document generation (with/without cache)
- Cache hit/miss scenarios
- Error handling (LLM failures, embedding failures, Qdrant failures)
- Cache key generation
- Singleton pattern
- Result format validation

### Integration Tests

Run Maximum Hybrid Search tests to verify HyDE integration:

```bash
poetry run pytest tests/unit/components/retrieval/test_maximum_hybrid_search.py -v
```

## Monitoring

### Logs

HyDE emits structured logs for monitoring:

```json
{
  "event": "hyde_generation_complete",
  "query": "What is Amsterdam?",
  "doc_length": 157,
  "tokens_used": 50,
  "provider": "local_ollama",
  "latency_ms": 95.3
}

{
  "event": "hyde_search_complete",
  "query": "What is Amsterdam?",
  "results_count": 10,
  "latency_ms": 187.2,
  "hypothetical_length": 157
}

{
  "event": "maximum_hybrid_search_complete",
  "hyde_count": 10,
  "hyde_enabled": true,
  "total_latency_ms": 312.5
}
```

### Metrics

Track these metrics in Prometheus/Grafana:

- `hyde_generation_latency_ms` - P50/P95/P99 latency
- `hyde_cache_hit_rate` - Percentage of cache hits
- `hyde_results_count` - Number of HyDE results per query
- `maximum_hybrid_search_latency_ms` - Total latency with HyDE

## Troubleshooting

### Issue: HyDE adds too much latency

**Solution:**
1. Check cache hit rate - should be >90%
2. Reduce `HYDE_MAX_TOKENS` to 256
3. Use faster LLM (llama3.2:3b instead of nemotron)
4. Disable HyDE for time-critical queries

### Issue: HyDE hurts precision for keyword queries

**Solution:**
1. Reduce `HYDE_WEIGHT` from 0.5 to 0.2
2. Disable HyDE for queries with >5 entities
3. Use query classification to toggle HyDE per query type

### Issue: Cache misses are high

**Solution:**
1. Check Redis connection/availability
2. Increase Redis memory limit
3. Check TTL is 24h (not shorter)
4. Verify cache key generation (SHA256 hash)

## Future Enhancements

Planned improvements for Sprint 129+:

1. **Query Classification** - Auto-enable HyDE for abstract queries only
2. **Adaptive Weight** - Adjust HyDE weight based on query complexity
3. **Multi-Turn HyDE** - Use conversation history for hypothetical generation
4. **Domain-Specific Prompts** - Customize hypothetical generation per domain
5. **RAGAS Evaluation** - Measure HyDE impact on Context Precision/Recall

## References

- [ADR-TBD] - HyDE Integration Decision Record (Sprint 128)
- [RAGAS Journey](../ragas/RAGAS_JOURNEY.md) - RAGAS metrics tracking
- [Maximum Hybrid Search](../../src/components/retrieval/maximum_hybrid_search.py) - Source code
- [HyDE Generator](../../src/components/retrieval/hyde.py) - Implementation
