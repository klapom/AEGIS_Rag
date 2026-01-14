---
name: hallucination_monitor
version: 1.0.0
description: Active hallucination detection and logging for generated answers
author: AegisRAG Team
triggers: []  # Auto-active skill, no explicit triggers
dependencies:
  - synthesis
permissions:
  - read_contexts
  - invoke_llm
  - write_logs
resources:
  prompts: prompts/
---

# Hallucination Monitor Skill

## Overview

The Hallucination Monitor Skill provides active detection and logging of hallucinations in generated answers. Unlike other skills, this is an **auto-active skill** that runs automatically after answer generation to verify factual accuracy.

This skill implements claim-level verification by:
1. Extracting individual claims from generated answers
2. Verifying each claim against provided contexts
3. Calculating a hallucination score (0.0 = perfect, 1.0 = severe)
4. Logging unsupported claims for analysis
5. Generating detailed reports for debugging

The skill is critical for RAGAS Faithfulness optimization and production quality assurance.

## Capabilities

- **Claim Extraction**: Breaks down answers into verifiable atomic claims
- **Claim Verification**: Checks each claim against source contexts
- **Hallucination Scoring**: Calculates percentage of unsupported claims
- **Detailed Logging**: Records all checks with verdicts (PASS/WARN/FAIL)
- **Metrics Tracking**: Accumulates statistics across all checks
- **Report Generation**: Produces structured reports for analysis

## Usage

### When to Activate

This skill is **auto-active** and runs automatically:
- After synthesis skill generates an answer
- After reflection skill improves an answer
- Before final answer is returned to user

Manual activation:
- User explicitly requests hallucination check: "verify this answer"
- Quality assurance mode: QA team reviewing answers
- RAGAS evaluation: Faithfulness metric calculation

### Input Requirements

**Required:**
- `answer`: str - Generated answer to check
- `contexts`: list[str] - Source documents used to generate answer

**Optional:**
- `threshold`: float - Hallucination score threshold (default: 0.1)
- `strict_mode`: bool - Fail fast on first hallucination (default: false)
- `log_level`: str - "minimal", "standard", "verbose" (default: "standard")

### Output Format

```python
{
    "answer": str,
    "hallucination_score": float,  # 0.0-1.0 (0.0 = no hallucination)
    "verdict": str,  # PASS | WARN | FAIL
    "num_claims": int,
    "num_verified": int,
    "num_unsupported": int,
    "unsupported_claims": list[str],
    "claim_details": [
        {
            "claim": str,
            "is_supported": bool,
            "confidence": float,
            "supporting_context": str | null
        }
    ],
    "metrics": {
        "total_checks": int,
        "hallucinations_detected": int,
        "claims_verified": int,
        "claims_unsupported": int
    }
}
```

## Configuration

```yaml
# Hallucination Detection
detection:
  enabled: true
  auto_active: true
  threshold: 0.1  # 10% unsupported claims triggers WARN
  critical_threshold: 0.3  # 30% unsupported claims triggers FAIL

# Claim Extraction
claims:
  method: "llm"  # "llm" or "spacy" (Sprint 90: LLM only)
  min_claim_length: 10
  max_claims_per_answer: 20
  ignore_meta_statements: true  # Ignore "I don't know", etc.

# Claim Verification
verification:
  method: "llm"  # "llm" or "embedding" (Sprint 90: LLM only)
  confidence_threshold: 0.7
  use_embeddings_for_similarity: false  # Sprint 90+: Use BGE-M3
  similarity_threshold: 0.85

# Verdict Thresholds
verdicts:
  PASS: 0.1  # <10% unsupported claims
  WARN: 0.3  # 10-30% unsupported claims
  FAIL: 0.3  # >30% unsupported claims

# Logging
logging:
  enabled: true
  log_all_checks: true
  log_unsupported_claims: true
  log_verdict: true
  log_metrics: true
  verbose: false

# Metrics
metrics:
  track_total_checks: true
  track_hallucinations: true
  track_claims: true
  reset_on_restart: false

# Performance
performance:
  parallel_verification: false  # Sprint 90: Sequential only
  cache_verifications: true
  cache_ttl_seconds: 600
```

## Examples

### Example 1: Clean Answer (PASS)

**Input:**
```python
answer = "AegisRAG uses Qdrant for vector storage, Neo4j for graph reasoning, and Redis for memory caching."
contexts = [
    "Vector storage is handled by Qdrant...",
    "Neo4j is used for the knowledge graph...",
    "Redis provides temporal memory and caching..."
]
```

**Process:**
```
Claims extracted: 3
1. "AegisRAG uses Qdrant for vector storage" → SUPPORTED by context[0]
2. "AegisRAG uses Neo4j for graph reasoning" → SUPPORTED by context[1]
3. "AegisRAG uses Redis for memory caching" → SUPPORTED by context[2]

Hallucination score: 0.0 / 3 = 0.00
Verdict: PASS
```

**Output:**
```json
{
    "hallucination_score": 0.0,
    "verdict": "PASS",
    "num_claims": 3,
    "num_verified": 3,
    "num_unsupported": 0,
    "unsupported_claims": []
}
```

### Example 2: Partial Hallucination (WARN)

**Input:**
```python
answer = "AegisRAG was created in 2020 by a team at Stanford University and uses GPT-4 for embeddings."
contexts = [
    "AegisRAG is an Agentic Enterprise Graph Intelligence System...",
    "BGE-M3 embeddings are used for vector search..."
]
```

**Process:**
```
Claims extracted: 3
1. "AegisRAG was created in 2020" → UNSUPPORTED (date not in contexts)
2. "AegisRAG was created by a team at Stanford University" → UNSUPPORTED (affiliation not in contexts)
3. "AegisRAG uses GPT-4 for embeddings" → UNSUPPORTED (contradicts context[1] about BGE-M3)

Hallucination score: 3 / 3 = 1.00
Verdict: FAIL
```

**Output:**
```json
{
    "hallucination_score": 1.0,
    "verdict": "FAIL",
    "num_claims": 3,
    "num_verified": 0,
    "num_unsupported": 3,
    "unsupported_claims": [
        "AegisRAG was created in 2020",
        "AegisRAG was created by a team at Stanford University",
        "AegisRAG uses GPT-4 for embeddings"
    ]
}
```

### Example 3: Mixed Claims (WARN)

**Input:**
```python
answer = "BGE-M3 produces 1024-dimensional vectors and supports 50 languages. It was trained on 100 billion tokens."
contexts = [
    "BGE-M3 is a multi-vector embedding model that produces 1024-dimensional dense vectors...",
    "The model supports over 100 languages..."
]
```

**Process:**
```
Claims extracted: 3
1. "BGE-M3 produces 1024-dimensional vectors" → SUPPORTED by context[0]
2. "BGE-M3 supports 50 languages" → UNSUPPORTED (context[1] says "over 100", not 50)
3. "BGE-M3 was trained on 100 billion tokens" → UNSUPPORTED (not mentioned in contexts)

Hallucination score: 2 / 3 = 0.67
Verdict: FAIL
```

**Output:**
```json
{
    "hallucination_score": 0.67,
    "verdict": "FAIL",
    "num_claims": 3,
    "num_verified": 1,
    "num_unsupported": 2,
    "unsupported_claims": [
        "BGE-M3 supports 50 languages",
        "BGE-M3 was trained on 100 billion tokens"
    ]
}
```

### Example 4: Metrics Accumulation

**After 100 checks:**
```json
{
    "metrics": {
        "total_checks": 100,
        "hallucinations_detected": 12,
        "claims_verified": 450,
        "claims_unsupported": 38,
        "pass_rate": 0.88,
        "average_hallucination_score": 0.08
    }
}
```

## Limitations

- **LLM Dependence**: Claim extraction quality depends on LLM capability
- **Context Quality**: Cannot detect hallucinations if contexts are wrong
- **Latency**: Each check adds 500-1000ms (LLM inference for extraction + verification)
- **False Positives**: May flag correct claims if contexts are incomplete or ambiguous
- **Language**: Optimized for English, performance may vary for other languages
- **Paraphrasing**: May struggle with heavily paraphrased claims
- **Implicit Knowledge**: Cannot verify claims requiring world knowledge not in contexts

## Version History

- 1.0.0 (2026-01-14): Initial release (Sprint 90)
  - LLM-based claim extraction
  - LLM-based claim verification
  - Hallucination scoring
  - Verdict system (PASS/WARN/FAIL)
  - Metrics tracking
  - Comprehensive logging
  - Auto-active integration with synthesis skill
  - Target: Improve RAGAS Faithfulness from 80% to 88%+
