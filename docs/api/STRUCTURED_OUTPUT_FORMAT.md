# Structured Output Format API Documentation

**Sprint 63 Feature 63.4: Structured Output Formatting (5 SP)**

## Overview

The AegisRAG API supports two response formats for chat and research endpoints:

1. **Natural Format** (default): Markdown text with inline citations [1], [2]
2. **Structured Format**: JSON with separate fields for answer, sources, and metadata

Both formats contain the same information, but structured format provides machine-readable output for programmatic consumption.

## Usage

### Chat Endpoint

```bash
# Natural format (default)
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is AegisRAG?",
    "response_format": "natural"
  }'

# Structured format
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is AegisRAG?",
    "response_format": "structured"
  }'
```

### Research Endpoint

```bash
# Structured format
curl -X POST http://localhost:8000/api/v1/research/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does hybrid search work in AegisRAG?",
    "response_format": "structured",
    "stream": false
  }'
```

## Response Formats

### Natural Format (Default)

```json
{
  "answer": "AegisRAG is an Agentic Enterprise Graph Intelligence System [1]. It combines vector search, graph reasoning, and temporal memory [2].",
  "query": "What is AegisRAG?",
  "session_id": "session-123",
  "intent": "hybrid",
  "sources": [
    {
      "text": "AegisRAG = Agentic Enterprise Graph Intelligence System",
      "title": "CLAUDE.md",
      "source": "docs/CLAUDE.md",
      "score": 0.92,
      "metadata": {}
    }
  ],
  "metadata": {
    "latency_seconds": 0.245,
    "agent_path": ["router", "vector_agent", "generator"]
  }
}
```

### Structured Format

```json
{
  "query": "What is AegisRAG?",
  "answer": "AegisRAG is an Agentic Enterprise Graph Intelligence System. It combines vector search, graph reasoning, and temporal memory.",
  "sources": [
    {
      "text": "AegisRAG = Agentic Enterprise Graph Intelligence System",
      "score": 0.92,
      "document_id": "doc_456",
      "chunk_id": "chunk_789",
      "source": "docs/CLAUDE.md",
      "title": "CLAUDE.md - Section: 'Project Overview' (Page 1)",
      "section": {
        "section_headings": ["Project Overview"],
        "section_pages": [1],
        "primary_section": "Project Overview"
      },
      "entities": ["AegisRAG", "LangGraph", "Qdrant"],
      "relationships": ["uses", "integrates_with"],
      "metadata": {
        "chunk_size": 800,
        "collection": "documents_v1"
      }
    }
  ],
  "metadata": {
    "latency_ms": 245.3,
    "search_type": "hybrid",
    "reranking_used": true,
    "graph_used": true,
    "total_sources": 10,
    "timestamp": "2025-12-23T10:30:00.123Z",
    "session_id": "session-123",
    "agent_path": ["router", "vector_agent", "graph_agent", "generator"]
  },
  "followup_questions": [
    "How does AegisRAG differ from traditional RAG?",
    "What are the main components of AegisRAG?"
  ]
}
```

## Schema Reference

### StructuredSource

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Source text content |
| `score` | float | Relevance score (0-1) |
| `document_id` | string? | Document identifier |
| `chunk_id` | string? | Chunk identifier |
| `source` | string? | Source file path |
| `title` | string? | Document/section title |
| `section` | SectionMetadata? | Section metadata (if available) |
| `entities` | string[] | Extracted entities |
| `relationships` | string[] | Extracted relationships |
| `metadata` | object | Additional metadata |

### SectionMetadata

| Field | Type | Description |
|-------|------|-------------|
| `section_headings` | string[] | Hierarchical section headings |
| `section_pages` | int[] | Page numbers |
| `primary_section` | string? | Primary section name |

### ResponseMetadata

| Field | Type | Description |
|-------|------|-------------|
| `latency_ms` | float | Total response latency in milliseconds |
| `search_type` | string | Search type used (vector, graph, hybrid, research) |
| `reranking_used` | boolean | Whether reranking was applied |
| `graph_used` | boolean | Whether graph search was used |
| `total_sources` | int | Total number of sources retrieved |
| `timestamp` | string | Response timestamp (ISO 8601) |
| `session_id` | string? | Session identifier (chat only) |
| `agent_path` | string[] | Agent execution path |

### StructuredChatResponse

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Original user query |
| `answer` | string | Generated answer text |
| `sources` | StructuredSource[] | Source documents |
| `metadata` | ResponseMetadata | Response metadata |
| `followup_questions` | string[] | Suggested follow-up questions |

### StructuredResearchResponse

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Original research question |
| `synthesis` | string | Synthesized research answer |
| `sources` | StructuredSource[] | Source documents |
| `metadata` | ResponseMetadata | Response metadata |
| `research_plan` | string[] | Search queries executed |
| `iterations` | int | Number of research iterations |
| `quality_metrics` | object | Research quality metrics |

## Use Cases

### API Client Integration

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/chat/",
    json={
        "query": "What is AegisRAG?",
        "response_format": "structured"
    }
)

data = response.json()

# Access structured fields
print(f"Query: {data['query']}")
print(f"Answer: {data['answer']}")
print(f"Latency: {data['metadata']['latency_ms']}ms")

# Process sources programmatically
for source in data['sources']:
    print(f"- {source['title']} (score: {source['score']:.2f})")
    if source['section']:
        print(f"  Section: {source['section']['primary_section']}")
```

### TypeScript/JavaScript

```typescript
interface StructuredChatResponse {
  query: string;
  answer: string;
  sources: StructuredSource[];
  metadata: ResponseMetadata;
  followup_questions: string[];
}

const response = await fetch('http://localhost:8000/api/v1/chat/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'What is AegisRAG?',
    response_format: 'structured'
  })
});

const data: StructuredChatResponse = await response.json();
console.log(`Answer: ${data.answer}`);
console.log(`Latency: ${data.metadata.latency_ms}ms`);
```

## Performance

- **Formatting Overhead**: <1ms per response
- **Response Size**: ~10-20% larger than natural format (due to additional metadata)
- **Latency**: No measurable impact on end-to-end latency

## Migration Guide

### From Natural to Structured

If you're currently using the natural format:

```python
# Before (natural format)
response = client.post("/chat/", json={"query": "..."})
answer = response.json()["answer"]
sources = response.json()["sources"]

# After (structured format)
response = client.post("/chat/", json={
    "query": "...",
    "response_format": "structured"
})
data = response.json()
answer = data["answer"]
sources = data["sources"]  # Now includes document_id, chunk_id, section, entities

# Access new fields
for source in sources:
    doc_id = source["document_id"]
    entities = source["entities"]
    if source["section"]:
        section = source["section"]["primary_section"]
```

## Validation

All structured responses are validated against Pydantic v2 schemas:

- **Field Types**: Enforced at runtime
- **Required Fields**: Cannot be null
- **Optional Fields**: Clearly marked with `?`
- **Nested Objects**: Fully typed and validated

## Examples

### Example 1: Simple Vector Search

**Request:**
```json
{
  "query": "What is Qdrant?",
  "response_format": "structured"
}
```

**Response:**
```json
{
  "query": "What is Qdrant?",
  "answer": "Qdrant is a vector database...",
  "sources": [
    {
      "text": "Qdrant is a vector similarity search engine...",
      "score": 0.95,
      "document_id": "doc_123",
      "chunk_id": "chunk_456",
      "source": "docs/TECH_STACK.md",
      "title": "TECH_STACK.md",
      "section": null,
      "entities": ["Qdrant"],
      "relationships": [],
      "metadata": {}
    }
  ],
  "metadata": {
    "latency_ms": 150.2,
    "search_type": "vector",
    "reranking_used": false,
    "graph_used": false,
    "total_sources": 5,
    "timestamp": "2025-12-23T10:30:00Z",
    "session_id": "session-abc",
    "agent_path": ["router", "vector_agent", "generator"]
  },
  "followup_questions": [
    "How does Qdrant compare to other vector databases?",
    "What is the performance of Qdrant?"
  ]
}
```

### Example 2: Research Query

**Request:**
```json
{
  "query": "How does hybrid search combine vector and keyword search?",
  "response_format": "structured",
  "stream": false
}
```

**Response:**
```json
{
  "query": "How does hybrid search combine vector and keyword search?",
  "synthesis": "Hybrid search combines vector similarity search with keyword-based BM25 search using Reciprocal Rank Fusion (RRF)...",
  "sources": [
    {
      "text": "Hybrid search uses RRF to merge vector and BM25 results...",
      "score": 0.88,
      "document_id": "doc_789",
      "chunk_id": "chunk_101",
      "source": "docs/ARCHITECTURE.md",
      "title": "ARCHITECTURE.md - Section: 'Hybrid Search'",
      "section": {
        "section_headings": ["Retrieval", "Hybrid Search"],
        "section_pages": [3],
        "primary_section": "Hybrid Search"
      },
      "entities": ["RRF", "BM25", "BGE-M3"],
      "relationships": ["combines", "uses"],
      "metadata": {}
    }
  ],
  "metadata": {
    "latency_ms": 1850.5,
    "search_type": "research",
    "reranking_used": true,
    "graph_used": true,
    "total_sources": 15,
    "timestamp": "2025-12-23T10:35:00Z",
    "session_id": null,
    "agent_path": ["research_planner", "multi_search", "synthesizer"]
  },
  "research_plan": [
    "vector search explanation",
    "BM25 keyword search",
    "RRF fusion algorithm"
  ],
  "iterations": 2,
  "quality_metrics": {
    "coverage": 0.85,
    "coherence": 0.92
  }
}
```

## FAQ

### When should I use structured format?

- Building API clients or SDKs
- Programmatic source analysis
- Citation tracking and provenance
- Performance monitoring and analytics
- Integration with other systems

### When should I use natural format?

- Human-readable output
- Markdown rendering
- Direct display in chat UI
- Minimal response size
- Legacy integrations

### Is there a performance difference?

No measurable difference in latency. Structured formatting adds <1ms overhead, which is negligible compared to the RAG pipeline execution time (100-500ms).

### Can I switch between formats dynamically?

Yes, the `response_format` parameter can be changed per-request. Both formats are always available.

### Are all fields always present?

Required fields are always present. Optional fields (marked with `?`) may be null or omitted. Check the schema reference for details.
