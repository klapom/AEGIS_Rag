---
name: synthesis
version: 1.0.0
description: Answer generation and summarization from retrieved contexts
author: AegisRAG Team
triggers:
  - answer
  - summarize
  - explain
  - generate
  - synthesize
dependencies:
  - retrieval
permissions:
  - read_contexts
  - invoke_llm
resources:
  prompts: prompts/
---

# Synthesis Skill

## Overview

The Synthesis Skill generates comprehensive, well-structured answers from retrieved documents. It combines information from multiple sources, maintains citations, and produces coherent responses tailored to the user's query complexity and intent.

Key features:
- **Multi-Document Synthesis**: Combines information from multiple retrieved contexts
- **Citation Management**: Tracks and formats citations from source documents
- **Intent-Aware Formatting**: Adapts answer style based on query intent (SEARCH, RESEARCH, etc.)
- **Section-Aware**: Preserves document structure from section-aware chunking
- **Confidence Scoring**: Provides confidence estimates for generated answers

## Capabilities

- **Answer Generation**: Creates comprehensive answers from retrieved contexts
- **Summarization**: Condenses long documents into concise summaries
- **Explanation**: Provides detailed explanations of complex concepts
- **Citation Formatting**: Includes source citations in answers
- **Multi-Hop Reasoning**: Synthesizes information across multiple retrieval steps
- **Markdown Formatting**: Generates well-formatted markdown output

## Usage

### When to Activate

This skill is activated when:
- User query requires answer generation (after retrieval)
- Intent classifier returns SEARCH, RESEARCH, or CHAT
- Agent needs to synthesize information from multiple documents
- Summarization is explicitly requested

Auto-activation:
```yaml
auto_activate_after:
  - retrieval skill completes
  - contexts retrieved > 0
```

### Input Requirements

**Required:**
- `query`: str - Original user query
- `contexts`: list[dict] - Retrieved documents with metadata

**Optional:**
- `intent`: str - Query intent (SEARCH, RESEARCH, CHAT, etc.)
- `max_tokens`: int - Maximum answer length (default: 500)
- `include_citations`: bool - Add source citations (default: true)
- `format`: str - Output format: "markdown", "plain", "json" (default: "markdown")
- `temperature`: float - LLM temperature (default: 0.3)

### Output Format

```python
{
    "answer": str,  # Generated answer
    "citations": list[dict],  # Source citations
    "confidence": float,  # 0.0-1.0
    "num_contexts_used": int,
    "format": str,
    "metadata": {
        "intent": str,
        "tokens_used": int,
        "latency_ms": float
    }
}
```

## Configuration

```yaml
# Answer Generation
generation:
  max_tokens: 500
  temperature: 0.3
  top_p: 0.9
  presence_penalty: 0.0
  frequency_penalty: 0.0

# Citation Settings
citations:
  enabled: true
  format: "markdown"  # [1], [2], etc.
  include_source: true
  include_page: true
  include_section: true

# Intent-Specific Templates
templates:
  SEARCH:
    style: "concise"
    max_tokens: 300
    include_citations: true
  RESEARCH:
    style: "comprehensive"
    max_tokens: 800
    include_citations: true
  CHAT:
    style: "conversational"
    max_tokens: 400
    include_citations: false

# Formatting
formatting:
  markdown: true
  code_blocks: true
  lists: true
  headers: true

# Confidence Scoring
confidence:
  min_contexts_required: 2
  score_threshold: 0.7
  fallback_message: "I don't have enough information to answer this question."

# Logging
logging:
  log_synthesis: true
  log_citations: true
  log_confidence: true
  verbose: false
```

## Examples

### Example 1: Basic Answer Generation

**Input:**
```python
query = "What is BGE-M3?"
contexts = [
    {
        "text": "BGE-M3 is a multi-vector embedding model that produces 1024-dimensional dense vectors and learned sparse vectors.",
        "metadata": {"source": "embeddings.md", "page": 1}
    },
    {
        "text": "The BGE-M3 model supports hybrid search by combining dense semantic embeddings with sparse lexical matching.",
        "metadata": {"source": "search.md", "page": 3}
    }
]
intent = "SEARCH"
```

**Output:**
```json
{
    "answer": "BGE-M3 is a multi-vector embedding model that produces 1024-dimensional dense vectors and learned sparse vectors [1]. It supports hybrid search by combining dense semantic embeddings with sparse lexical matching [2].\n\nSources:\n[1] embeddings.md, page 1\n[2] search.md, page 3",
    "confidence": 0.92,
    "num_contexts_used": 2
}
```

### Example 2: Research-Style Synthesis

**Input:**
```python
query = "How does hybrid search work in AegisRAG?"
contexts = [
    {
        "text": "Hybrid search combines vector similarity with keyword matching using Reciprocal Rank Fusion (RRF)...",
        "metadata": {"source": "architecture.md", "section": "Search"}
    },
    {
        "text": "BGE-M3 embeddings provide both dense and sparse vectors natively...",
        "metadata": {"source": "embeddings.md", "section": "BGE-M3"}
    },
    {
        "text": "Server-side RRF fusion merges results from dense and sparse searches in Qdrant...",
        "metadata": {"source": "qdrant.md", "section": "RRF"}
    }
]
intent = "RESEARCH"
```

**Output:**
```json
{
    "answer": "# Hybrid Search in AegisRAG\n\nAegisRAG's hybrid search combines vector similarity with keyword matching using Reciprocal Rank Fusion (RRF) [1]. The system leverages BGE-M3 embeddings, which provide both dense (1024-dimensional) and sparse (learned lexical) vectors natively [2].\n\n## Technical Implementation\n\nServer-side RRF fusion merges results from dense and sparse searches directly in Qdrant, eliminating the need for client-side post-processing [3]. This architecture provides:\n\n- **Dense Search**: Semantic similarity matching\n- **Sparse Search**: Learned keyword matching (replaces BM25)\n- **RRF Fusion**: Weighted combination of both result sets\n\n## Performance\n\nThe hybrid approach achieves higher recall than pure vector search while maintaining low latency.\n\nSources:\n[1] architecture.md - Search\n[2] embeddings.md - BGE-M3\n[3] qdrant.md - RRF",
    "confidence": 0.95,
    "num_contexts_used": 3,
    "format": "markdown"
}
```

### Example 3: Insufficient Context

**Input:**
```python
query = "What is the capital of Mars?"
contexts = []
intent = "SEARCH"
```

**Output:**
```json
{
    "answer": "I don't have enough information to answer this question. No relevant contexts were retrieved.",
    "confidence": 0.0,
    "num_contexts_used": 0
}
```

### Example 4: Conversational Style

**Input:**
```python
query = "Thanks for the explanation!"
contexts = []
intent = "CHAT"
```

**Output:**
```json
{
    "answer": "You're welcome! Feel free to ask if you have any more questions.",
    "confidence": 1.0,
    "num_contexts_used": 0,
    "format": "plain"
}
```

## Limitations

- **Context Dependence**: Answer quality depends on retrieval quality
- **Citation Accuracy**: Citations may be imprecise if contexts are chunked
- **Hallucination Risk**: May generate unsupported claims if not used with reflection skill
- **Token Limits**: Long contexts may be truncated to fit LLM context window
- **Language**: Optimized for English, may perform worse in other languages
- **Complex Reasoning**: May struggle with multi-hop reasoning without graph support

## Version History

- 1.0.0 (2026-01-14): Initial release (Sprint 90)
  - Multi-document synthesis
  - Citation management
  - Intent-aware templates
  - Confidence scoring
  - Markdown formatting
  - Integration with retrieval and reflection skills
