# Sprint 44 Model Comparison Report

**Date:** 2025-12-12
**Dataset:** HotPotQA (10 samples per model)
**Pipeline:** Chunking → LLM Extraction → Entity Dedup → Relation Dedup

---

## Executive Summary

| Model | Total Time | Avg/Sample | Entities | Relations | Entity Dedup | Rel Dedup | Reliability |
|-------|------------|------------|----------|-----------|--------------|-----------|-------------|
| **qwen2.5:3b** | 195s (3.3min) | 19.3s | 301 | 88 | 15.0% | 4.8% | Excellent |
| **qwen2.5:7b** | 407s (6.8min) | 40.5s | 234 | 145 | 2.4% | 0.8% | Excellent |
| **qwen3:8b** | 455s (7.6min) | 45.3s | 204 | 216 | 2.7% | 2.7% | Excellent |
| **qwen3:32b** | 2383s (39.7min) | 238.1s | 292 | 241 | 4.4% | 1.2% | Excellent |
| **nuextract:3.8b** | 1952s (32.5min) | 195.0s | 33 | 25 | 0.0% | 5.0% | Variable |
| **gemma3:4b** | N/A (partial) | ~38s | ~36 | ~27 | N/A | N/A | **Unreliable** |

---

## Key Findings

### 1. Speed Performance (Fastest to Slowest)
1. **qwen2.5:3b** - 19.3s/sample (12.3x faster than qwen3:32b)
2. **qwen2.5:7b** - 40.5s/sample (5.9x faster than qwen3:32b)
3. **qwen3:8b** - 45.3s/sample (5.3x faster than qwen3:32b)
4. **nuextract:3.8b** - 195.0s/sample (highly variable: 21s-484s)
5. **qwen3:32b** - 238.1s/sample (baseline)

### 2. Extraction Quality (Entities + Relations)

| Model | Entities/Sample | Relations/Sample | Quality Assessment |
|-------|-----------------|------------------|-------------------|
| qwen3:32b | 29.2 | 24.1 | **Highest quality** - balanced extraction |
| qwen2.5:3b | 30.1 | 8.8 | Most entities, fewer relations |
| qwen2.5:7b | 23.4 | 14.5 | Balanced |
| qwen3:8b | 20.4 | 21.6 | Good relation coverage |
| nuextract:3.8b | 3.3 | 2.5 | **Very poor** - not suitable |
| gemma3:4b | ~3.6 | ~2.7 | Partial data (unreliable) |

### 3. Deduplication Effectiveness

| Model | Entity Dedup % | Relation Dedup % | Notes |
|-------|----------------|------------------|-------|
| qwen2.5:3b | 15.0% | 4.8% | Best entity dedup |
| qwen3:32b | 4.4% | 1.2% | Low - high quality extraction |
| qwen3:8b | 2.7% | 2.7% | Balanced dedup |
| qwen2.5:7b | 2.4% | 0.8% | Very clean extraction |
| nuextract:3.8b | 0.0% | 5.0% | Too few entities to dedup |

---

## Detailed Model Analysis

### qwen3:32b (Baseline - Highest Quality)
- **Strengths:** Best extraction quality, most relations per entity
- **Weaknesses:** Very slow (238s/sample)
- **Use Case:** Quality-critical batch processing, training data generation
- **Recommendation:** Use for quality benchmarks, not production

### qwen2.5:7b (Best Balance)
- **Strengths:** Good quality (23.4 entities, 14.5 relations), fast (40.5s)
- **Weaknesses:** Fewer relations than qwen3 models
- **Use Case:** Production workloads, real-time ingestion
- **Recommendation:** **PRIMARY CHOICE** for production

### qwen3:8b (Good Quality)
- **Strengths:** Good relation extraction (21.6/sample), reliable
- **Weaknesses:** Slightly slower than qwen2.5:7b
- **Use Case:** Relation-heavy knowledge graphs
- **Recommendation:** Alternative to qwen2.5:7b when relations matter

### qwen2.5:3b (Speed Champion)
- **Strengths:** Fastest (19.3s), most entities (30.1)
- **Weaknesses:** Fewer relations (8.8/sample)
- **Use Case:** Entity-focused extraction, high-volume processing
- **Recommendation:** Use for speed-critical scenarios

### nuextract:3.8b (Not Recommended)
- **Strengths:** Specialized extraction model
- **Weaknesses:** Very low extraction (3.3 entities), highly variable timing
- **Use Case:** Not suitable for general entity extraction
- **Recommendation:** **AVOID** - insufficient extraction quality

### gemma3:4b (Unreliable)
- **Strengths:** Fast when working (~38s/sample)
- **Weaknesses:** Hangs during relation extraction, unreliable
- **Use Case:** Not suitable for production
- **Recommendation:** **AVOID** - stability issues

---

## Recommendations

### Production Configuration
```yaml
# Primary model for production
EXTRACTION_MODEL: qwen2.5:7b

# Fallback for speed-critical scenarios
EXTRACTION_MODEL_FAST: qwen2.5:3b

# Quality validation model
EXTRACTION_MODEL_QUALITY: qwen3:32b
```

### Expected Performance
| Scenario | Model | Expected Time/Sample | Expected Quality |
|----------|-------|---------------------|------------------|
| Real-time | qwen2.5:7b | ~40s | Good (23 entities, 14 relations) |
| Batch | qwen3:32b | ~238s | Excellent (29 entities, 24 relations) |
| High-volume | qwen2.5:3b | ~19s | Moderate (30 entities, 9 relations) |

---

## Data Files
- `pipeline_eval_qwen3_32b_20251211_230359.json`
- `pipeline_eval_qwen3_8b_20251211_235936.json`
- `pipeline_eval_qwen2.5_7b_20251212_000759.json`
- `pipeline_eval_qwen2.5_3b_20251212_011618.json`
- `pipeline_eval_nuextract_3.8b_20251212_001455.json`

---

*Generated: 2025-12-12 01:20 CET*
*Sprint 44 Part 3 Evaluation*
