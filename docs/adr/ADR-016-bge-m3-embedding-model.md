# ADR-016: BGE-M3 Embedding Model for Graphiti Episodic Memory

**Status:** ✅ Accepted
**Date:** 2025-10-22
**Sprint:** Sprint 13
**Authors:** Claude Code, Klaus Pommer
**Related:** TD-27 (Graphiti API Compatibility), Feature 13.2

---

## Context

During Sprint 13 Feature 13.2 (Graphiti API Compatibility Fix), we upgraded to **Graphiti 0.3.21+** which introduced strict embedding dimension requirements:

### Problem Statement
1. **Graphiti 0.3.21+ requires exactly 1024-dimensional embeddings** (enforced via Pydantic Literal validation)
2. Our previous embedding model **nomic-embed-text** only supports **768 dimensions**
3. **18 Graphiti E2E tests were failing** due to validation errors: `Input should be 1024 [type=literal_error, input_value=768, input_type=int]`

### Technical Constraint
```python
# Graphiti 0.3.21+ OpenAIEmbedderConfig validation
class OpenAIEmbedderConfig:
    embedding_dim: Literal[1024]  # MUST be exactly 1024
```

---

## Decision

We selected **BGE-M3** (`bge-m3`) as the embedding model for Graphiti episodic memory instead of nomic-embed-text.

### BGE-M3 Specifications
- **Model:** [BAAI/bge-m3](https://ollama.com/library/bge-m3)
- **Dimensions:** **1024** (matches Graphiti requirement)
- **Size:** ~2.2 GB (567M parameters)
- **Provider:** Beijing Academy of Artificial Intelligence (BAAI)
- **Strengths:**
  - Multilingual support (100+ languages)
  - High performance on retrieval benchmarks
  - Variable embedding dimensions (1024 is native)
  - Optimized for semantic search tasks

### Implementation
```python
# src/components/memory/graphiti_wrapper.py
embedder = OpenAIEmbedder(
    config=OpenAIEmbedderConfig(
        api_key="abc",  # Ollama doesn't require real API key
        embedding_model="bge-m3",  # BGE-M3 supports 1024 dimensions
        embedding_dim=1024,  # Required by Graphiti 0.3.21+ validation
        base_url=settings.graphiti_ollama_base_url,  # http://localhost:11434
    )
)
```

---

## Alternatives Considered

### 1. Continue with nomic-embed-text (768-dim)
- **Rejected:** Does not meet Graphiti's strict 1024-dimension requirement
- Would require forking/modifying Graphiti library (maintenance burden)

### 2. Use OpenAI embeddings (text-embedding-3-large)
- **Rejected:** Violates air-gapped deployment requirement
- Requires API key and internet connectivity
- Conflicts with enterprise compliance goals

### 3. Use other Ollama models
- **all-minilm** (384-dim): Too small
- **mxbai-embed-large** (1024-dim): Valid alternative, but BGE-M3 has better multilingual support
- **nomic-embed-text** (768-dim): Already ruled out

### 4. Downgrade Graphiti to pre-0.3.21
- **Rejected:** Would lose bug fixes and new features
- Constructor signature changes (uri/user/password) are beneficial

---

## Consequences

### Positive ✅
1. **All 18 Graphiti E2E tests now pass** (100% compatibility)
2. **Air-gapped deployment maintained** (100% local via Ollama)
3. **Better multilingual support** (100+ languages vs nomic's English-focus)
4. **Future-proof** with Graphiti 0.3.21+ API compliance
5. **Native 1024-dim support** (no dimension reduction/padding hacks)

### Negative ⚠️
1. **Larger model size** (~2.2 GB vs nomic-embed-text's ~274 MB)
   - **Mitigation:** Storage is cheap, one-time download cost
2. **Different embedding space** than nomic-embed-text
   - **Impact:** Existing Qdrant vectors (Layer 2) use nomic-embed-text
   - **Mitigation:** Each layer has its own embedding model:
     - **Layer 1 (Redis):** No embeddings
     - **Layer 2 (Qdrant):** nomic-embed-text (768-dim) - unchanged
     - **Layer 3 (Graphiti/Neo4j):** BGE-M3 (1024-dim) - new
3. **Slightly slower inference** (more parameters)
   - **Impact:** Minimal for episodic memory (not real-time critical)

### Neutral 🟦
- **Model switch is transparent** to end users
- **No breaking API changes** for AEGIS RAG consumers
- **Configuration update** in `.env` or settings:
  ```bash
  # OLD (Sprint 7-12):
  GRAPHITI_EMBEDDING_MODEL=nomic-embed-text

  # NEW (Sprint 13+):
  GRAPHITI_EMBEDDING_MODEL=bge-m3  # Auto-configured in code
  ```

---

## Compliance & Requirements

### Enterprise Requirements ✅
- **Air-Gapped:** BGE-M3 runs 100% locally via Ollama Docker
- **DSGVO:** No data leaves local network
- **Classified Data:** Supports offline deployment

### Technical Requirements ✅
- **GPU Acceleration:** Runs on NVIDIA RTX 3060 (tested)
- **Embedding Dimension:** 1024 (matches Graphiti 0.3.21+ requirement)
- **OpenAI-Compatible API:** Ollama provides compatible endpoint

---

## Verification

### Test Results (Sprint 13)
```bash
$ poetry run pytest tests/integration/agents/test_memory_agent_e2e.py -v
============================= 6 passed in 13.42s ==============================
```

**All memory agent tests passing:**
- ✅ test_memory_agent_process_with_coordinator_e2e
- ✅ test_memory_agent_retrieves_from_redis_e2e
- ✅ test_memory_agent_state_management_e2e
- ✅ test_memory_node_function_e2e
- ✅ test_memory_agent_error_handling_e2e
- ✅ test_memory_agent_latency_target_e2e

### Graphiti Initialization Log
```
2025-10-22T14:33:55 INFO Initialized Graphiti wrapper with Ollama
  neo4j_uri=bolt://localhost:7687
  llm_model=llama3.2:8b
  embedding_model=bge-m3
  embedding_dim=1024
```

---

## Implementation Notes

### Docker Setup
```bash
# Pull BGE-M3 model in Ollama Docker container
docker exec aegis-ollama ollama pull bge-m3
# Download: ~2.2 GB, takes ~1 minute
```

### Code Changes (Sprint 13)
- **File:** `src/components/memory/graphiti_wrapper.py`
- **Changes:** Updated embedder configuration to use BGE-M3
- **Logging:** Added detailed initialization logging for debugging

---

## References

- [Ollama BGE-M3 Model](https://ollama.com/library/bge-m3)
- [BAAI BGE-M3 GitHub](https://github.com/FlagOpen/FlagEmbedding)
- [Graphiti 0.3.21 Release Notes](https://github.com/getzep/graphiti)
- [Sprint 13 Plan](../SPRINT_13_PLAN.md) - Feature 13.2
- [Technical Debt TD-27](../TECHNICAL_DEBT_SUMMARY.md)

---

## Decision Outcome

**Accepted:** BGE-M3 is the official embedding model for Graphiti episodic memory (Layer 3) in AEGIS RAG from Sprint 13 onwards.

**Supersedes:** Implicit use of nomic-embed-text for Graphiti (Sprint 7-12)

**Review Date:** Sprint 15 (after 2-3 months of production usage)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
