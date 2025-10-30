# Sprint 13: Entity/Relation Extraction Experiments

**Sprint Period**: 2025-10-17 to 2025-10-27
**Goal**: Optimize entity and relation extraction pipeline for LightRAG

## Context

Sprint 13 focused on improving the Three-Phase Entity/Relation Extraction Pipeline:
- Phase 1: SpaCy NER (Named Entity Recognition)
- Phase 2: Semantic Deduplication
- Phase 3: Gemma 3 4B Relation Extraction

## Archived Scripts (18 total)

### Model Comparison Tests

1. **test_all_models_lightrag.py**: Compare multiple LLM models for extraction
2. **test_smollm3.py**: Test SmolLM3 model performance
3. **quick_model_test.py**: Fast model validation

### Prompt Engineering Experiments

4. **test_lightrag_prompts.py**: Test different prompt formats
5. **test_lightrag_exact_prompts.py**: Exact LightRAG library prompts
6. **test_lightrag_format_with_logging.py**: Debug prompt formatting issues
7. **test_lightrag_original_prompts.py**: Original LightRAG prompts baseline

### NuExtract Model Tests

8. **test_nuextract_detailed_prompts.py**: Detailed prompt engineering for NuExtract
9. **test_nuextract_json_format.py**: JSON output format testing
10. **test_nuextract_two_pass_enhanced.py**: Enhanced two-pass extraction
11. **test_nuextract_two_pass_spacy.py**: Two-pass with SpaCy preprocessing

### Pipeline Tests

12. **test_spacy_only_gemma_relations.py**: SpaCy entities + Gemma relations
13. **test_three_phase_quick.py**: Quick validation of three-phase pipeline
14. **diagnose_lightrag_issue.py**: Debug LightRAG integration issues
15. **debug_dedup.py**: Debug semantic deduplication

## Key Findings

### Successful Approach (Final Implementation)

**Three-Phase Pipeline** (ADR-018):
- Phase 1: SpaCy NER (fast, accurate entity extraction)
- Phase 2: Semantic Deduplication (remove near-duplicates)
- Phase 3: Gemma 3 4B Q8_0 (relation extraction)

**Performance**: >300s → <30s (10x improvement)

### Models Tested

| Model | Performance | Result |
|-------|-------------|--------|
| Gemma 3 4B Q8_0 | Best accuracy | ✅ **SELECTED** |
| NuExtract | Good extraction | ❌ Too slow |
| SmolLM3 | Fast | ❌ Lower accuracy |
| llama3.2:3b | Decent | ❌ Slower than Gemma |

### Prompt Engineering Lessons

1. **Exact LightRAG Format**: Best results with original LightRAG JSON schema
2. **Two-Pass Extraction**: Not worth the complexity (Phase 1 + 3 sufficient)
3. **Structured Output**: JSON format works well with proper validation

## Related ADRs

- **ADR-017**: Semantic Deduplication Strategy
- **ADR-018**: LLM Model Selection for Entity/Relation Extraction

## Migration Notes

All learnings from these experiments were incorporated into:
- `src/components/graph_rag/extraction_pipeline.py`
- `src/components/graph_rag/lightrag_wrapper.py`

The production implementation uses:
```python
ExtractionPipelineFactory.create_pipeline(
    strategy="three_phase_spacy_gemma",
    llm_model="gemma3:4b-it-q8_0"
)
```

## Do Not Delete

These scripts provide valuable context for:
1. Understanding why Gemma 3 4B was selected
2. Debugging future extraction issues
3. Re-running experiments if we switch models

---

**Archived**: Sprint 19 (2025-10-30)
