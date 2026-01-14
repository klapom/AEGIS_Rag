---
name: planner
version: "1.0.0"
description: Task decomposition and execution planning for complex multi-step queries
author: AegisRAG Team
triggers:
  - plan
  - steps
  - how to
  - break down
  - decompose
  - strategy
  - approach
dependencies:
  - retrieval
permissions:
  - invoke_llm
  - read_documents
resources:
  docs: "https://docs.aegisrag.com/skills/planner"
  prompts: prompts/
---

# Planner Skill

## Overview

The Planner Skill provides intelligent task decomposition and execution planning for complex queries. It breaks down user requests into actionable subtasks, manages dependencies, and orchestrates parallel execution where possible.

**Key Capabilities:**
- **Query Decomposition**: Break complex requests into 3-10 subtasks
- **Dependency Tracking**: Understand which subtasks must run sequentially vs. parallel
- **Execution Planning**: Generate optimal execution order
- **Progress Monitoring**: Track completion of each subtask
- **Result Aggregation**: Combine results with proper citations
- **Error Handling**: Graceful degradation if subtasks fail

This skill is activated for requests requiring multiple steps, strategic planning, or multi-phase analysis.

## When to Activate

This skill is activated when:
- User query contains planning keywords: "plan", "steps", "how to", "break down", "strategy"
- Intent classifier returns PLANNING or ANALYSIS
- Query complexity score exceeds threshold (multi-phase required)
- Agent needs to coordinate multiple retrieval or reasoning operations
- Research requires systematic exploration of a topic

## Capabilities

### 1. Query Decomposition

**Input:** Complex user query or research objective
**Process:**
1. Analyze query intent and scope
2. Identify sub-questions or phases
3. Determine dependencies between tasks
4. Estimate effort per task

**Output:** Structured task plan with:
- Task ID and description
- Dependencies (which tasks must complete first)
- Estimated tokens/latency
- Execution mode (sequential, parallel, conditional)

### 2. Subtask Management

**Maximum subtasks:** 10 (configurable)
**Minimum subtasks:** 3 (otherwise skip planning)
**Execution modes:**
- `sequential`: Tasks run one after another (default for dependent tasks)
- `parallel`: Multiple tasks run simultaneously (no dependency)
- `conditional`: Task runs only if previous task succeeds/fails

### 3. Progress Tracking

**Tracked per subtask:**
- Status: pending → in_progress → completed/failed
- Output tokens consumed
- Latency (start→end time)
- Error details (if failed)
- Citation sources (which documents provided the answer)

### 4. Result Aggregation

**Combines subtask results with:**
- Proper hierarchical citations (which sources answered which sub-question)
- Conflict resolution (if different subtasks contradict)
- Coherence checking (do results form a cohesive answer?)
- Fallback synthesis (if some subtasks fail)

## Usage

### Input Requirements

**Required:**
- `query`: str - User's complex question or research objective (100+ chars)
- `namespace`: str - Document namespace to search (e.g., "ragas_phase2")

**Optional:**
- `max_subtasks`: int - Maximum number of subtasks (default: 10, range: 3-10)
- `execution_mode`: str - "greedy_parallel" (maximize parallelism) or "minimal_sequential" (default)
- `timeout_per_task`: int - Timeout per subtask in seconds (default: 60)
- `enable_gleaning`: bool - Apply gleaning to extracted information (default: true)
- `citation_required`: bool - Require citations for all facts (default: true)

### Output Format

```python
{
    "original_query": "How does BGE-M3 compare to other embedding models?",
    "plan": {
        "num_subtasks": 4,
        "estimated_tokens": 2400,
        "estimated_latency_ms": 3500,
        "tasks": [
            {
                "task_id": "1",
                "description": "Find BGE-M3 characteristics and architecture",
                "dependencies": [],
                "execution_mode": "parallel",
                "status": "completed"
            },
            {
                "task_id": "2",
                "description": "Find alternative embedding models (OpenAI, Cohere, Hugging Face)",
                "dependencies": [],
                "execution_mode": "parallel",
                "status": "completed"
            },
            {
                "task_id": "3",
                "description": "Compare performance metrics (speed, accuracy, cost)",
                "dependencies": ["1", "2"],
                "execution_mode": "sequential",
                "status": "completed"
            },
            {
                "task_id": "4",
                "description": "Synthesize findings into recommendation",
                "dependencies": ["3"],
                "execution_mode": "sequential",
                "status": "completed"
            }
        ]
    },
    "results": {
        "synthesis": "BGE-M3 excels in hybrid search (dense + sparse) compared to...",
        "subtask_results": {
            "1": {
                "answer": "BGE-M3 produces 1024-dim dense vectors and sparse lexical vectors...",
                "citations": ["doc_123:page_5", "doc_456:section_intro"],
                "latency_ms": 245,
                "status": "completed"
            },
            "2": {
                "answer": "OpenAI text-embedding-3-large (3072-dim), Cohere embed-v3 (768-dim)...",
                "citations": ["doc_789:page_12"],
                "latency_ms": 320,
                "status": "completed"
            },
            "3": {
                "answer": "Speed: BGE-M3 ~99ms vs OpenAI ~150ms. Accuracy: BGE-M3 NDCG@10 0.95 vs OpenAI 0.92...",
                "citations": ["doc_123:table_3", "doc_456:benchmark"],
                "latency_ms": 180,
                "status": "completed"
            },
            "4": {
                "answer": "BGE-M3 recommended for hybrid RAG (20% lower latency, 3% higher accuracy)...",
                "citations": ["doc_123:conclusion"],
                "latency_ms": 150,
                "status": "completed"
            }
        },
        "execution_stats": {
            "total_latency_ms": 3445,
            "total_tokens": 2350,
            "parallel_savings_ms": 850,
            "subtasks_failed": 0,
            "subtasks_completed": 4
        }
    }
}
```

## Configuration

```yaml
planner:
  # Task decomposition
  max_subtasks: 10
  min_subtasks: 3

  # Execution strategy
  execution_mode: greedy_parallel  # or minimal_sequential

  # Timeouts
  timeout_per_task: 60  # seconds
  max_total_latency: 300  # 5 minutes for entire plan

  # Quality control
  enable_gleaning: true
  citation_required: true
  conflict_detection: true

  # Parallelization
  max_parallel_tasks: 5

  # Prompt configuration
  prompts:
    decompose_model: "nemotron3"
    aggregate_model: "nemotron3"

  # Caching
  cache:
    enabled: true
    ttl_seconds: 600
    key_prefix: "planner"
```

## Prompts

### decompose.txt

Used to break down complex queries into subtasks.

**Inputs:**
- `{query}`: Original user query
- `{namespace}`: Document namespace
- `{context}`: Relevant background info

**Output:** JSON structured plan with subtasks and dependencies

### aggregate.txt

Used to combine subtask results into coherent answer.

**Inputs:**
- `{query}`: Original user query
- `{subtask_results}`: All completed subtask outputs
- `{conflicts}`: Any contradictions detected

**Output:** Synthesized answer with hierarchical citations

## Examples

### Example 1: Multi-Step Research Question

**Input:**
```python
query = "What are the key differences between vector-only search and hybrid vector-graph search in RAG systems? What are the tradeoffs?"
namespace = "ragas_phase2"
max_subtasks = 5
execution_mode = "greedy_parallel"
```

**Decomposition:**
```
Task 1: Define vector-only search architecture
Task 2: Define hybrid vector-graph search architecture
Task 3: Compare accuracy/relevance metrics (parallel with 1,2)
Task 4: Compare latency and cost (parallel with 1,2)
Task 5: Synthesize tradeoffs (depends on 3,4)
```

**Execution Timeline:**
```
T=0ms:    Start tasks 1,2 (parallel)
T=300ms:  Tasks 1,2 complete, start tasks 3,4 (parallel)
T=800ms:  Tasks 3,4 complete, start task 5
T=1200ms: Task 5 complete, return synthesis
```

**Output:**
```json
{
    "synthesis": "Vector-only search is fastest (150ms p95) but hybrid vector-graph provides 40% better recall at cost of 3x latency (450ms p95). Hybrid is recommended for accuracy-critical applications, vector-only for latency-critical applications.",
    "execution_stats": {
        "parallel_savings_ms": 480,
        "total_latency_ms": 1200
    }
}
```

### Example 2: Systematic Domain Analysis

**Input:**
```python
query = "Analyze the evolution of embedding models in RAG: early approaches, current state-of-the-art, and future directions"
namespace = "research_papers"
max_subtasks = 6
```

**Decomposition:**
```
Task 1: Find early embedding models (2020-2022)
Task 2: Find current SOTA models (2023-2025)
Task 3: Find benchmark comparisons (parallel with 1,2)
Task 4: Analyze performance trends (depends on 1,2,3)
Task 5: Find future research directions (parallel with 4)
Task 6: Write comprehensive timeline (depends on 4,5)
```

**Output:**
```json
{
    "synthesis": "Embedding evolution: Word2Vec→BERT (2018) showed 15% improvement. Then DensePassage (2020), ColBERT (2021). Current SOTA: BGE-M3 (2024) with hybrid dense+sparse achieving 3% better NDCG than text-embedding-3-large. Future: multimodal embeddings (image+text), domain-specific fine-tuning.",
    "subtask_results": {
        "1": {"answer": "Word2Vec, GloVe, FastText, ELMo fundamentals...", "citations": [...], "latency_ms": 245},
        "2": {"answer": "BGE-M3, text-embedding-3-large, Cohere embed-v3...", "citations": [...], "latency_ms": 320},
        "3": {"answer": "NDCG scores, recall@k comparisons...", "citations": [...], "latency_ms": 180},
        "4": {"answer": "20% improvement in accuracy over 5 years, 10x speedup...", "citations": [...], "latency_ms": 150},
        "5": {"answer": "Multimodal embeddings, efficient inference, domain adaptation...", "citations": [...], "latency_ms": 210},
        "6": {"answer": "[Comprehensive timeline synthesis]", "citations": [...], "latency_ms": 290}
    }
}
```

### Example 3: Comparative Analysis with Conditional Tasks

**Input:**
```python
query = "Compare BGE-M3 and OpenAI embeddings. Which is better for my use case: financial document search with 50K documents?"
namespace = "technical_docs"
execution_mode = "greedy_parallel"
```

**Decomposition:**
```
Task 1: Find BGE-M3 specs and performance
Task 2: Find OpenAI embedding specs and performance
Task 3: Analyze for financial domain (depends on 1,2)
Task 4: Calculate cost per 50K documents (depends on 1,2)
Task 5: Provide recommendation (depends on 3,4)
```

**Output:**
```json
{
    "synthesis": "For your financial use case: BGE-M3 recommended. Reasons: 20% lower latency (99ms vs 150ms), supports sparse vectors for keyword matching (important for financial terms), open-source (cost 0 vs $4 per 1M tokens), achieves 3% higher NDCG on domain data. Trade-off: requires self-hosting vs OpenAI's managed service.",
    "subtask_results": {...}
}
```

## Limitations

- **Task Complexity:** Decomposition limited to 10 subtasks. Very complex queries may need multiple planning passes.
- **LLM Dependency:** Decomposition quality depends on LLM reasoning capability
- **Citation Overhead:** Collecting citations for all facts adds ~20% latency
- **Conflict Resolution:** Automatic conflict detection works for factual contradictions, not interpretive disagreements
- **Token Budget:** Large plans with many subtasks may consume 2000+ tokens total
- **Context Window:** Retrieved documents per subtask limited to ~4000 tokens (half of 8K context window)

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Decomposition latency | 150-300ms |
| Per-subtask latency | 150-500ms |
| Parallelization speedup | 2-4x (depending on dependencies) |
| Citation overhead | +15-20% latency |
| Memory per plan | ~5MB (for 10 subtasks) |
| Average tokens per task | 200-400 |

## Error Handling

**If subtask fails (timeout, LLM error, etc.):**

1. **Retry:** Exponential backoff (1s → 2s → 4s → 8s) with tenacity
2. **Fallback:** If dependent tasks exist, skip to next independent task
3. **Degradation:** If critical task fails, skip dependent tasks and return partial results
4. **Reporting:** Include "subtasks_failed" in output with error details

**Example:**
```json
{
    "synthesis": "[Partial answer based on completed tasks 1,2,4. Task 3 failed: timeout.]",
    "subtask_results": {
        "1": {"status": "completed", ...},
        "2": {"status": "completed", ...},
        "3": {"status": "failed", "error": "Timeout after 60s", "attempts": 3},
        "4": {"status": "completed", ...}
    },
    "execution_stats": {
        "subtasks_completed": 3,
        "subtasks_failed": 1,
        "total_latency_ms": 2150
    }
}
```

## Version History

- 1.0.0 (2026-01-14): Initial release (Sprint 91)
  - Query decomposition with dependency tracking
  - Parallel and sequential execution modes
  - Subtask result aggregation with citations
  - Conflict detection and resolution
  - Error handling and graceful degradation
  - Based on ADR-050 (Skill Router Architecture) and ADR-051 (Recursive LLM Context)

## See Also

- [ADR-050: Intent-Based Skill Router Architecture](../../docs/adr/ADR-050-skill-router-architecture.md)
- [ADR-051: Recursive Language Model Context Processing](../../docs/adr/ADR-051-recursive-llm-context.md)
- [Retrieval Skill](../retrieval/SKILL.md)
- [Synthesis Skill](../synthesis/SKILL.md)
- [Sprint 91 Plan](../../docs/sprints/SPRINT_91_PLAN.md)
