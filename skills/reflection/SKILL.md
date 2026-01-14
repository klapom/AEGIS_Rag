---
name: reflection
version: 1.0.0
description: Self-critique and validation loop for answer quality
author: AegisRAG Team
triggers:
  - validate
  - check
  - verify
  - critique
  - review
  - improve
dependencies: []
permissions:
  - read_contexts
  - invoke_llm
resources:
  prompts: prompts/
---

# Reflection Skill

## Overview

The Reflection Skill enables the agent to critically evaluate and improve its own responses through iterative self-critique. Based on the Reflexion framework (Shinn et al. 2023), this skill implements a multi-step validation loop that:
1. Generates an initial answer
2. Critiques the answer for accuracy, completeness, and hallucination
3. Scores confidence (0.0-1.0)
4. Improves the answer if confidence is below threshold
5. Repeats until confidence threshold is met or max iterations reached

This skill is particularly valuable for complex questions requiring multi-step reasoning or high accuracy.

## Capabilities

- **Self-Critique**: Evaluates answer quality against provided contexts
- **Factual Verification**: Checks alignment with source documents
- **Hallucination Detection**: Identifies unsupported or fabricated claims
- **Iterative Improvement**: Refines answers through multiple reflection cycles
- **Confidence Scoring**: Assigns 0.0-1.0 confidence score to each answer
- **Issue Tracking**: Logs specific problems found during critique

## Usage

### When to Activate

This skill is activated when:
- User query contains validation keywords: "validate", "verify", "check"
- Intent classifier returns RESEARCH or GRAPH (complex reasoning)
- Initial answer confidence is below 0.85
- User explicitly requests verification
- Query is flagged as high-stakes (medical, legal, financial)

Auto-activation rules:
```yaml
auto_activate_for:
  - RESEARCH intent
  - GRAPH intent
  - confidence < 0.85
  - high_stakes: true
```

### Input Requirements

**Required:**
- `query`: str - Original user query
- `answer`: str - Generated answer to critique
- `contexts`: list[str] - Source documents used to generate answer

**Optional:**
- `max_iterations`: int - Maximum reflection cycles (default: 3)
- `confidence_threshold`: float - Minimum acceptable confidence (default: 0.85)
- `strict_mode`: bool - Fail fast on hallucinations (default: false)

### Output Format

```python
{
    "original_answer": str,
    "final_answer": str,
    "critique": str,
    "confidence_score": float,
    "issues_found": list[str],
    "iterations": int,
    "improved": bool,
    "reflection_trace": [
        {
            "iteration": 1,
            "score": 0.65,
            "issues": ["Missing citation", "Incomplete coverage"],
            "action": "improved"
        },
        {
            "iteration": 2,
            "score": 0.88,
            "issues": [],
            "action": "accepted"
        }
    ]
}
```

## Configuration

```yaml
# Reflection Parameters
reflection:
  max_iterations: 3
  confidence_threshold: 0.85
  min_confidence_delta: 0.05  # Minimum improvement per iteration

# Critique Aspects
critique:
  check_factual_accuracy: true
  check_completeness: true
  check_hallucination: true
  check_clarity: true
  check_citations: true

# Auto-Activation Rules
auto_activate:
  intents:
    - RESEARCH
    - GRAPH
  min_confidence: 0.85
  high_stakes_domains:
    - medical
    - legal
    - financial

# Prompt Settings
prompts:
  critique_template: "prompts/critique.txt"
  improve_template: "prompts/improve.txt"
  temperature: 0.1  # Low temperature for consistency
  max_tokens: 1000

# Logging
logging:
  log_iterations: true
  log_confidence_scores: true
  log_issues: true
  verbose: false
```

## Examples

### Example 1: Basic Reflection

**Input:**
```python
query = "What is hybrid search?"
answer = "Hybrid search combines vector and keyword search."
contexts = [
    "Hybrid search combines vector similarity with keyword matching using Reciprocal Rank Fusion...",
    "BGE-M3 provides both dense and sparse vectors for hybrid retrieval..."
]
```

**Process:**
```
Iteration 1:
- Critique: "Answer is too brief, missing technical details"
- Score: 0.65
- Issues: ["Incomplete coverage", "Missing RRF explanation"]
- Action: Improve

Iteration 2:
- Improved Answer: "Hybrid search combines vector similarity (dense embeddings)
  with keyword matching (sparse vectors) using Reciprocal Rank Fusion (RRF) to
  merge results. BGE-M3 provides both vector types natively."
- Score: 0.92
- Issues: []
- Action: Accept
```

**Output:**
```json
{
    "original_answer": "Hybrid search combines vector and keyword search.",
    "final_answer": "Hybrid search combines vector similarity (dense embeddings) with keyword matching (sparse vectors) using Reciprocal Rank Fusion (RRF) to merge results...",
    "confidence_score": 0.92,
    "iterations": 2,
    "improved": true
}
```

### Example 2: Hallucination Detection

**Input:**
```python
query = "When was AegisRAG created?"
answer = "AegisRAG was created in 2020 by a team at Stanford University."
contexts = [
    "AegisRAG is an Agentic Enterprise Graph Intelligence System...",
    "The project implements LangGraph orchestration with multiple agents..."
]
```

**Process:**
```
Iteration 1:
- Critique: "CRITICAL: Answer contains hallucinated facts not supported by contexts"
- Score: 0.15
- Issues: ["Date (2020) not in contexts", "Stanford affiliation not in contexts"]
- Action: Reject and regenerate

Iteration 2:
- Improved Answer: "Based on the provided documentation, AegisRAG is an Agentic
  Enterprise Graph Intelligence System. The specific creation date is not mentioned
  in the available contexts."
- Score: 0.88
- Issues: []
- Action: Accept
```

**Output:**
```json
{
    "original_answer": "AegisRAG was created in 2020 by a team at Stanford University.",
    "final_answer": "Based on the provided documentation, AegisRAG is an Agentic Enterprise Graph Intelligence System...",
    "confidence_score": 0.88,
    "issues_found": ["Hallucinated date", "Hallucinated affiliation"],
    "iterations": 2,
    "improved": true
}
```

### Example 3: High-Confidence Answer (No Improvement)

**Input:**
```python
query = "What databases does AegisRAG use?"
answer = "AegisRAG uses Qdrant for vector storage, Neo4j for graph reasoning, and Redis for memory caching."
contexts = [
    "Vector storage is handled by Qdrant...",
    "Neo4j is used for the knowledge graph...",
    "Redis provides temporal memory and caching..."
]
```

**Process:**
```
Iteration 1:
- Critique: "Answer is accurate, complete, and well-aligned with contexts"
- Score: 0.95
- Issues: []
- Action: Accept (no improvement needed)
```

**Output:**
```json
{
    "original_answer": "AegisRAG uses Qdrant for vector storage, Neo4j for graph reasoning, and Redis for memory caching.",
    "final_answer": "AegisRAG uses Qdrant for vector storage, Neo4j for graph reasoning, and Redis for memory caching.",
    "confidence_score": 0.95,
    "iterations": 1,
    "improved": false
}
```

## Limitations

- **Latency**: Each reflection iteration adds 1-2 seconds (LLM inference time)
- **Cost**: Multiple LLM calls increase token usage and API costs
- **Diminishing Returns**: After 2-3 iterations, improvements plateau
- **Context Dependence**: Quality of critique depends on quality of provided contexts
- **False Positives**: May flag correct answers as uncertain if contexts are incomplete
- **LLM Variability**: Different LLMs may produce different critique styles

## Version History

- 1.0.0 (2026-01-14): Initial release (Sprint 90)
  - Core reflection loop implementation
  - Confidence scoring
  - Iterative improvement
  - Hallucination detection
  - Auto-activation rules
  - Based on Reflexion framework (Shinn et al. 2023)
