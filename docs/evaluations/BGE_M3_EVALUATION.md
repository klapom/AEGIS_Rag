# BGE-M3 Universal Embedding Model Evaluation

**Status:** 🔬 Evaluation Pending (Sprint 13 End)
**Created:** Sprint 13 (2025-10-22)
**Decision Required:** Sprint 14 Planning

---

## Context

During Sprint 13 Feature 13.2, we introduced **BGE-M3** as the embedding model for **Graphiti episodic memory (Layer 3)** due to Graphiti 0.3.21+ requiring exactly 1024-dimensional embeddings.

**Current State (Post-Sprint 13):**
- **Layer 1 (Redis):** No embeddings
- **Layer 2 (Qdrant):** nomic-embed-text (768-dim)
- **Layer 3 (Graphiti/Neo4j):** BGE-M3 (1024-dim) ✨ NEW

**Question for Evaluation:**
Should we **standardize on BGE-M3 across all layers** (replace nomic-embed-text + potentially BM25)?

---

## BGE-M3 Specifications

### Model Details
- **Name:** BAAI/bge-m3
- **Parameters:** 567M
- **Embedding Dimensions:** 1024 (native)
- **Model Size:** ~2.2 GB
- **Provider:** Beijing Academy of Artificial Intelligence (BAAI)
- **Ollama:** Available via `ollama pull bge-m3`

### Key Features
1. **Multilingual:** 100+ languages supported
2. **Multi-Functionality:**
   - Dense retrieval (semantic embeddings)
   - Sparse retrieval (lexical matching, BM25-like)
   - Multi-vector retrieval (ColBERT-style)
3. **Unified Model:** Single model for multiple retrieval strategies
4. **State-of-the-Art:** Top performance on MTEB benchmark (as of 2024)

### Performance Benchmarks
- **MTEB Average:** 66.1 (vs nomic-embed-text: 62.4)
- **Retrieval Tasks:** Outperforms nomic-embed-text by 3-5%
- **Multilingual Tasks:** Significantly better than English-only models
- **Inference Speed:** ~50-100ms per query (RTX 3060)

---

## Current Architecture Analysis

### Layer 2 (Qdrant Vector Search)

**Current Implementation:**
```python
# src/components/vector_search/embedding_service.py
embedder = HuggingFaceEmbeddings(
    model_name="nomic-ai/nomic-embed-text-v1",
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True}
)
# Embedding dimension: 768
```

**Hybrid Search Pattern:**
```python
# Qdrant Hybrid Search (Vector + BM25)
vector_results = qdrant.search(query_vector, limit=100)  # nomic-embed-text
bm25_results = qdrant.search_text(query, limit=100)      # BM25 keyword search
fused_results = reciprocal_rank_fusion(vector_results, bm25_results)
```

### Layer 3 (Graphiti Episodic Memory)

**New Implementation (Sprint 13):**
```python
# src/components/memory/graphiti_wrapper.py
embedder = OpenAIEmbedder(
    config=OpenAIEmbedderConfig(
        embedding_model="bge-m3",
        embedding_dim=1024,
        base_url="http://localhost:11434"  # Ollama
    )
)
```

---

## Evaluation Criteria

### 1. Retrieval Quality

**Question:** Does BGE-M3's sparse retrieval capability eliminate the need for separate BM25?

**Hypothesis:**
- BGE-M3's multi-functionality (dense + sparse) could replace:
  - nomic-embed-text (dense)
  - BM25 (sparse/keyword)
- Single model for hybrid search = simpler architecture

**Test Plan:**
```python
# Benchmark BGE-M3 vs Current Hybrid (nomic + BM25)
queries = load_test_queries()  # 100 diverse queries

# Current approach
results_current = []
for query in queries:
    vector = nomic_embed(query)
    vec_results = qdrant.search(vector)
    bm25_results = qdrant.search_text(query)
    results_current.append(rrf_fusion(vec_results, bm25_results))

# BGE-M3 approach
results_bgem3 = []
for query in queries:
    dense_vector = bgem3_dense_embed(query)
    sparse_vector = bgem3_sparse_embed(query)
    results_bgem3.append(qdrant.search_hybrid(dense_vector, sparse_vector))

# Compare metrics
compare_retrieval_quality(results_current, results_bgem3)
```

**Metrics to Track:**
- Recall@10, Recall@20
- MRR (Mean Reciprocal Rank)
- NDCG (Normalized Discounted Cumulative Gain)
- Query latency

### 2. Dimension Compatibility

**Current Challenge:**
- Layer 2 (Qdrant): 768-dim vectors stored
- Layer 3 (Graphiti): 1024-dim vectors stored
- **Incompatible for cross-layer similarity comparisons**

**BGE-M3 Benefit:**
- Standardize on 1024-dim across all layers
- Enable **cross-layer semantic similarity**:
  ```python
  # Find Qdrant docs similar to Graphiti episode
  episode_vector = graphiti_wrapper.get_episode_embedding(episode_uuid)
  similar_docs = qdrant.search(episode_vector, limit=10)  # Works if same dims!
  ```

**Migration Consideration:**
- Existing Qdrant collections have 768-dim vectors
- **Migration Path:**
  1. Create new 1024-dim collections
  2. Re-embed documents with BGE-M3
  3. Switch over (blue-green deployment)
  4. Or: Keep 768-dim for old data, 1024-dim for new (dual-index)

### 3. Performance & Resource Usage

**Inference Speed:**
| Model | Embedding Time (RTX 3060) | Throughput |
|-------|---------------------------|------------|
| nomic-embed-text | 20-30ms | ~40 docs/sec |
| BGE-M3 (dense only) | 50-100ms | ~15 docs/sec |
| BGE-M3 (dense + sparse) | 80-150ms | ~10 docs/sec |

**Memory Footprint:**
| Model | VRAM (GPU) | RAM (CPU) |
|-------|------------|-----------|
| nomic-embed-text | ~1 GB | ~2 GB |
| BGE-M3 | ~2.5 GB | ~4 GB |

**Considerations:**
- BGE-M3 is 2-3x slower than nomic-embed-text
- Acceptable for episodic memory (not real-time critical)
- **Question:** Is 2-3x slower acceptable for Layer 2 vector search?
  - Depends on query volume and latency requirements
  - Could batch embed documents offline (not real-time)

### 4. Cost-Benefit Analysis

**Benefits of Standardizing on BGE-M3:**
1. ✅ **Single Model:** Simpler deployment, fewer dependencies
2. ✅ **Cross-Layer Similarity:** 1024-dim enables semantic bridging between layers
3. ✅ **Better Quality:** 3-5% improvement in retrieval metrics
4. ✅ **Multilingual:** Future-proof for non-English content
5. ✅ **Sparse Retrieval Built-In:** Potentially replace BM25
6. ✅ **State-of-the-Art:** Top MTEB performance

**Costs of Migration:**
1. ⚠️ **Re-Embedding:** Need to re-embed all existing Qdrant documents
2. ⚠️ **Slower Inference:** 2-3x slower than nomic-embed-text
3. ⚠️ **Higher VRAM:** 2.5 GB vs 1 GB (may require GPU upgrade for scale)
4. ⚠️ **Migration Complexity:** Downtime or dual-index strategy needed
5. ⚠️ **Testing Overhead:** Validate retrieval quality across all use cases

---

## Decision Framework

### Scenario A: Keep Current Hybrid (nomic + BM25)

**When to Choose:**
- Latency is critical (<50ms query requirement)
- Existing 768-dim Qdrant data is large (>1M docs, expensive to re-embed)
- GPU VRAM is limited (<4GB available)
- Team bandwidth for migration is low

**Outcome:**
- Layer 2: nomic-embed-text (768-dim) + BM25
- Layer 3: BGE-M3 (1024-dim)
- **Trade-off:** No cross-layer similarity, but simpler migration

### Scenario B: Standardize on BGE-M3 (Dense + Sparse)

**When to Choose:**
- Retrieval quality is priority over latency
- Cross-layer semantic bridging is valuable
- GPU resources are adequate (RTX 3060+ with 8GB+ VRAM)
- Team can invest in migration (Sprint 14-15 effort)

**Outcome:**
- Layer 2: BGE-M3 (1024-dim, dense + sparse)
- Layer 3: BGE-M3 (1024-dim, dense + sparse)
- **Trade-off:** Migration effort, but unified architecture

### Scenario C: Hybrid Approach (BGE-M3 Dense + Keep BM25)

**When to Choose:**
- Want BGE-M3 quality but keep proven BM25
- Unsure if BGE-M3 sparse matches BM25 performance
- Risk-averse migration strategy

**Outcome:**
- Layer 2: BGE-M3 (1024-dim, dense only) + BM25 (existing)
- Layer 3: BGE-M3 (1024-dim, dense only)
- **Trade-off:** Keeps BM25 dependency, but lower risk

---

## Recommended Evaluation Plan (Sprint 13 End / Sprint 14 Start)

### Phase 1: Benchmarking (Sprint 14, Week 1)

1. **Setup Test Environment:**
   - Create duplicate Qdrant collection with 1024-dim
   - Re-embed 1000 representative documents with BGE-M3
   - Prepare 100 test queries (diverse intents)

2. **Run Comparative Benchmarks:**
   - Current: nomic + BM25 + RRF
   - Option A: BGE-M3 dense only + BM25 + RRF
   - Option B: BGE-M3 dense + sparse (no BM25)

3. **Measure:**
   - Retrieval quality (Recall, MRR, NDCG)
   - Latency (p50, p95, p99)
   - Resource usage (GPU VRAM, inference time)

### Phase 2: Decision (Sprint 14, Week 2)

**If BGE-M3 ≥ 5% better quality AND latency < 100ms:**
→ Recommend **Scenario B** (Full BGE-M3 standardization)

**If BGE-M3 2-4% better quality BUT latency > 100ms:**
→ Recommend **Scenario C** (BGE-M3 dense + keep BM25)

**If BGE-M3 < 2% better quality:**
→ Keep **Scenario A** (Current architecture)

### Phase 3: Migration (Sprint 14-15, if approved)

1. **Sprint 14:**
   - Create new 1024-dim Qdrant collections
   - Implement BGE-M3 embedding service
   - Re-embed all documents (offline batch job)

2. **Sprint 15:**
   - Blue-green deployment (switch to new collections)
   - Monitor retrieval quality in production
   - Deprecate old 768-dim collections after validation

---

## Open Questions

1. **BM25 Replacement:**
   - Can BGE-M3 sparse retrieval fully replace BM25?
   - Does Qdrant support BGE-M3 sparse vectors natively?
   - Or do we need custom sparse vector handling?

2. **Cross-Layer Similarity:**
   - What are the actual use cases for cross-layer semantic similarity?
   - Example: "Find Qdrant docs similar to this Graphiti episode"
   - Is this feature valuable enough to justify migration?

3. **Performance at Scale:**
   - How does BGE-M3 perform with 10M+ documents?
   - Does inference speed degrade with larger VRAM usage?

4. **Qdrant Multi-Vector Support:**
   - Does Qdrant natively support BGE-M3's multi-vector output?
   - Or do we need to store dense + sparse separately?

---

## References

- **BGE-M3 Paper:** https://arxiv.org/abs/2402.03216
- **MTEB Leaderboard:** https://huggingface.co/spaces/mteb/leaderboard
- **Ollama BGE-M3:** https://ollama.com/library/bge-m3
- **Qdrant Sparse Vectors:** https://qdrant.tech/documentation/concepts/vectors/#sparse-vectors
- **ADR-016:** BGE-M3 for Graphiti (Sprint 13)

---

## Decision Log

**Sprint 13 (2025-10-22):**
- ✅ BGE-M3 adopted for Graphiti Layer 3 (Pydantic requirement)
- ⏸️ Evaluation deferred to Sprint 13 end / Sprint 14 start

**Sprint 14 (TBD):**
- 🔬 Benchmarking: nomic vs BGE-M3 (dense + sparse)
- 🔬 Latency testing: <100ms target
- 🔬 Cross-layer similarity use case validation

**Sprint 15 (TBD):**
- Decision: Keep current or migrate to BGE-M3
- Migration plan (if approved)

---

**Document Status:** Evaluation Framework
**Next Action:** Run benchmarks in Sprint 14 Week 1
**Decision Date:** Sprint 14 Week 2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
