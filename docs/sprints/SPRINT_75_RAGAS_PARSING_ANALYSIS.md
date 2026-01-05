# Sprint 75 - RAGAS Parsing Failure Analysis

**Date**: 2026-01-04
**Status**: In Progress (50% complete, 40/80 metrics)
**Evaluation Model**: gpt-oss:20b with 16K context window

---

## Executive Summary

The full 20-sample RAGAS evaluation is experiencing a **32.5% parsing failure rate** (13 failures out of 40 completed jobs). The primary issue is JSON schema incompatibility between gpt-oss:20b's output format and RAGAS's strict parser requirements.

### Key Findings

| Metric | Value |
|--------|-------|
| Total Jobs | 80 (20 samples × 4 metrics) |
| Completed | 40 (50%) |
| Failed | 13 (32.5% failure rate) |
| Most Problematic Prompt | `statement_generator_prompt` (69% of failures) |

---

## Failure Breakdown by Prompt Type

```
Prompt Type                              Count    % of Failures
─────────────────────────────────────────────────────────────
statement_generator_prompt                 9         69.2%
context_recall_classification_prompt       3         23.1%
context_precision_prompt                   1          7.7%
─────────────────────────────────────────────────────────────
TOTAL                                     13        100.0%
```

### Failed Job Numbers
```
1, 2, 6, 9, 10, 14, 18, 22, 28, 29, 30, 34, 38
```

---

## Dataset Question Mapping

### All 20 Evaluation Questions

| # | Question | Intent | Difficulty |
|---|----------|--------|------------|
| 1 | What is BGE-M3? | factual | easy |
| 2 | What is the main purpose of the AEGIS RAG system? | factual | medium |
| 3 | Which databases are used in AEGIS RAG? | factual | easy |
| 4 | What is the difference between vector search and hybrid search? | exploratory | medium |
| 5 | How does the four-way hybrid search work? | exploratory | hard |
| 6 | What is LangGraph used for in AEGIS RAG? | factual | medium |
| 7 | What is the role of Graphiti in the system? | factual | medium |
| 8 | What LLM models are used in AEGIS RAG? | factual | easy |
| 9 | How does the reranking process improve retrieval? | exploratory | hard |
| 10 | What is the purpose of intent classification? | exploratory | medium |
| 11 | What chunking strategy does AEGIS RAG use? | factual | medium |
| 12 | What is Docling and how is it used? | factual | easy |
| 13 | How does AEGIS RAG handle streaming responses? | factual | medium |
| 14 | What is the AegisLLMProxy used for? | factual | medium |
| 15 | What performance targets does AEGIS RAG aim for? | factual | easy |
| 16 | How does entity extraction work in AEGIS RAG? | exploratory | medium |
| 17 | What testing frameworks are used? | factual | easy |
| 18 | What monitoring tools are integrated? | factual | easy |
| 19 | How does query caching work? | exploratory | medium |
| 20 | What is the deployment architecture? | factual | medium |

**Note**: Question #4 has truncation issue in dataset (see Critical Issues section).

---

## Root Cause Analysis

### 1. statement_generator_prompt (9 failures - 69%)

**Purpose**: Generates atomic statements from ground truth answers for faithfulness evaluation.

**Expected Output Schema**:
```json
{
  "statements": [
    "statement 1",
    "statement 2",
    ...
  ]
}
```

**Hypothesis**: gpt-oss:20b may be:
- Adding extra fields (e.g., `reasoning`, `confidence`)
- Using different key names (e.g., `generated_statements` vs `statements`)
- Including markdown formatting or code blocks
- Producing malformed JSON (trailing commas, unescaped quotes)

### 2. context_recall_classification_prompt (3 failures - 23%)

**Purpose**: Classifies whether ground truth statements can be attributed to retrieved contexts.

**Expected Output Schema**:
```json
{
  "attributed": true,  // or false
  "reason": "explanation"
}
```

**Hypothesis**: Boolean serialization issues or extra fields.

### 3. context_precision_prompt (1 failure - 8%)

**Purpose**: Ranks contexts by relevance to ground truth.

**Expected Output Schema**:
```json
{
  "verdict": 1  // or 0
}
```

**Hypothesis**: Rare edge case, possibly numerical formatting.

---

## Error Pattern Analysis

### Retry Behavior
Each failed job attempts:
1. Initial prompt execution
2. Retry 1 with `fix_output_format` prompt
3. Retry 2 with `fix_output_format` prompt
4. Retry 3 with `fix_output_format` prompt
5. Final failure → `RagasOutputParserException`

**All retries fail**, indicating the issue is systematic, not transient.

### RAGAS Parser Expectations
RAGAS uses `pydantic` v2 strict JSON parsing:
- No extra fields allowed
- Exact key name matching
- Strict type enforcement
- No markdown formatting

---

## Impact Assessment

### Evaluation Completeness
With 32.5% failure rate:
- **Expected total failures**: ~26 out of 80 jobs
- **Usable metrics**: ~54 out of 80 (67.5%)
- **Per-sample impact**: Most samples will have 2-3 metrics instead of 4

### Metric Availability (Projected)

| Metric | Success Rate (est.) | Impact |
|--------|---------------------|--------|
| Context Precision | ~92% | Minimal (1 failure) |
| Context Recall | ~77% | Moderate (3 failures) |
| Faithfulness | ~31% | **SEVERE** (9 failures via statement_generator) |
| Answer Relevancy | Unknown | Pending analysis |

**Critical**: Faithfulness scores will be incomplete or unavailable for most samples due to `statement_generator_prompt` failures.

---

## Critical Infrastructure Issues (User-Identified)

Beyond parsing failures, the following issues were observed in evaluation logs:

### 1. Neo4j Schema Warning
```
UnknownPropertyKeyWarning: missing property name is: document_path
```
- **Location**: Graph search queries
- **Impact**: Null source fields in graph retrieval results
- **Fix**: Add `document_path` property to schema or change query to match existing field

### 2. IntentClassifier Model Missing
```
setfit_model_not_found ... fallback=embedding or rule_based path=models/intent_classifier
```
- **Impact**: Less accurate intent classification (factual/keyword/exploratory/summary)
- **Fix**: Train and save SetFit model or verify path

### 3. CPU-only Embeddings
```
native_embedding_service_initialized device=cpu ... vram_usage_gb=0.0
```
- **Expected**: GPU acceleration (10-80x faster)
- **Impact**: Significantly slower embedding generation
- **Fix**: Investigate CUDA initialization in sentence-transformers

### 4. Reranker Config Inconsistency
```
Hybrid search initialized ... reranker_enabled=False
[Later] reranking_complete ... cross_encoder_ms=...
```
- **Impact**: Unclear what is actually being evaluated
- **Fix**: Align configuration with actual behavior

### 5. Token Budget Violations
```
Input tokens: 22,571 (exceeds declared 16K limit)
```
- **Impact**: Possible silent truncation affecting metrics
- **Fix**: Investigate prompt construction and context preparation. Maybe it's not tokens but characters? If really tokens set limit to 32k

### 6. Dataset Truncation
```json
{"question": "What is the difference between vector search and h", ...}
```
- **Should be**: "... and hybrid search?"
- **Impact**: Invalid test case
- **Fix**: Repair dataset file

---

## Recommendations

### Immediate (After Evaluation Completes)

1. **Extract Sample Outputs**: Analyze actual gpt-oss:20b JSON outputs to identify exact formatting issues
2. **Test Alternative Models**: Try qwen3:8b or nemotron3 for comparison
3. **Custom Parser**: Consider implementing custom output parser for gpt-oss:20b quirks
4. **RAGAS Version**: Check if newer RAGAS version has more lenient parsing
5. **Fallback Strategy**: When parsing fails, log raw output for manual analysis

### Short-term (Sprint 75)

6. **Fix Dataset**: Repair truncated question #4
7. **Address Infrastructure Issues**: Fix 6 critical issues identified above
8. **Reduce num_predict**: Current 512 may still allow verbose outputs → try 256
9. **Add Structured Output Constraints**: Use Ollama's `format="json"` more strictly

### Long-term (Sprint 76+)

10. **Fine-tuned Evaluation Model**: Train model specifically for RAGAS output format
11. **Monitoring**: Add parsing success rate metrics to evaluation pipeline
12. **LLM-as-Judge Alternatives**: Explore Prometheus, AutoEval, or DeepEval
---

## Next Steps

1. ⏳ **Wait for evaluation completion** (~25-30 minutes remaining)
2. 📊 **Analyze final results**: Calculate actual metric completion rates
3. 🔍 **Extract failed outputs**: Identify exact JSON formatting patterns
4. 🐛 **Debug statement_generator**: Priority #1 (69% of failures)
5. ✅ **Fix critical infrastructure issues**: 6 items from user feedback
6. 📈 **Generate comparison report**: vs. Sprint 74 baseline

---

## Appendix: Evaluation Configuration

```python
# Model Configuration
llm_model = "gpt-oss:20b"
temperature = 0.0
top_p = 0.9
num_ctx = 16384  # Extended from 8192
num_predict = 512  # Reduced from 2048
format = "json"

# Evaluation Parameters
sample_size = 20
batch_size = 10
top_k = 5
metrics = ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]

# Dataset
factual_questions = 14
exploratory_questions = 6
easy = 7, medium = 11, hard = 2
```

---

**Status**: EVALUATION COMPLETE - CATASTROPHIC FAILURE
**Last Updated**: 2026-01-04 22:11 (evaluation finished)
**Duration**: 50 minutes (3000 seconds)

---

## 🚨 CRITICAL: Catastrophic Evaluation Results

```
Metric                Target    Actual    Status
────────────────────────────────────────────────
Context Precision     0.75      0.000     ❌ CATASTROPHIC FAILURE
Context Recall        0.70      0.000     ❌ CATASTROPHIC FAILURE
Faithfulness          0.90      0.750     ❌ Below Target (-17%)
Answer Relevancy      0.80      0.708     ❌ Below Target (-12%)
```

**Failure Analysis:**
- **25 out of 80 jobs failed** (31.25% failure rate)
- Context Precision/Recall both show **ZERO** - indicates catastrophic retrieval failure
- Faithfulness (0.75) and Answer Relevancy (0.71) show the RAG system IS generating answers
- **Paradox**: How can answers be 75% faithful if retrieved contexts have 0% precision/recall?

**ROOT CAUSE IDENTIFIED:** ✅

**The Qdrant collection contains COMPLETELY WRONG DOCUMENTS!**

```
Collection: documents_v1
Namespace: default
Document Count: 129 documents
Content: OMNITRACKER training documentation (German business software)

Expected Content: AEGIS RAG documentation
- BGE-M3 embeddings
- Four-way hybrid search
- Neo4j/Qdrant/Redis architecture
- LangGraph agents
- Graphiti memory

Overlap: ZERO - 0% relevance
```

**Why Context Precision/Recall = 0.0:**
- Evaluation asks: "What is BGE-M3?" → Retrieval finds: "OMNITRACKER Kanban Views"
- Evaluation asks: "How does four-way hybrid search work?" → Retrieval finds: "OMNITRACKER Admin Grundlagen"
- Ground truth expects technical RAG docs → Retrieved docs are business software training materials

**System is working correctly - it just has the wrong data!**
