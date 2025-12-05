# ChunkingService Developer Guide

**Quick reference for using the Unified ChunkingService (Feature 36.6 - TD-054)**

---

## Quick Start

### Basic Usage
```python
from src.core import get_chunking_service

service = get_chunking_service()
chunks = await service.chunk_document(
    text="Your document text...",
    document_id="doc_123",
)
```

### With Section Metadata (Recommended)
```python
from src.core import get_chunking_service, SectionMetadata

sections = [
    SectionMetadata(
        heading="Introduction",
        level=1,
        page_no=1,
        bbox={"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
        text="Section text...",
        token_count=200,
        metadata={"source": "doc.pdf"},
    ),
]

service = get_chunking_service()
chunks = await service.chunk_document(
    text="Full document text...",
    document_id="doc_123",
    sections=sections,
    metadata={"source": "doc.pdf", "author": "Klaus"},
)
```

---

## Configuration

### Default Configuration
```python
# Uses adaptive strategy with these defaults:
# - strategy: ADAPTIVE (section-aware)
# - min_tokens: 800
# - max_tokens: 1800
# - overlap_tokens: 100
# - preserve_sections: True
# - large_section_threshold: 1200

service = get_chunking_service()
```

### Custom Configuration
```python
from src.core import ChunkingConfig, ChunkingService, ChunkStrategyEnum

config = ChunkingConfig(
    strategy=ChunkStrategyEnum.FIXED,
    max_tokens=1000,
    overlap_tokens=200,
)

service = ChunkingService(config)
```

---

## Chunking Strategies

### 1. Adaptive (Default, Recommended)
**Best for:** Documents with clear section structure (PPTX, PDF with headings, DOCX)

```python
config = ChunkingConfig(
    strategy=ChunkStrategyEnum.ADAPTIVE,
    min_tokens=800,
    max_tokens=1800,
    preserve_sections=True,
)
```

**Behavior:**
- Merges small sections intelligently
- Keeps large sections standalone
- Tracks multi-section metadata
- Optimizes for retrieval quality

**When to use:**
- PowerPoint presentations (slides → sections)
- PDFs with heading structure
- Word documents with proper formatting

### 2. Fixed
**Best for:** Simple documents, consistent chunking

```python
config = ChunkingConfig(
    strategy=ChunkStrategyEnum.FIXED,
    max_tokens=512,
    overlap_tokens=128,
)
```

**Behavior:**
- Fixed-size chunks with tiktoken
- Token-accurate counting
- Respects word boundaries

**When to use:**
- Plain text documents
- When you need predictable chunk sizes
- When section structure is not important

### 3. Sentence
**Best for:** Documents where sentence boundaries matter

```python
config = ChunkingConfig(
    strategy=ChunkStrategyEnum.SENTENCE,
    max_tokens=512,
)
```

**Behavior:**
- Splits on sentence boundaries (. ! ?)
- Groups sentences to target size
- Preserves sentence integrity

**When to use:**
- Legal documents
- Scientific papers
- Content where complete sentences matter

### 4. Paragraph
**Best for:** Documents with clear paragraph structure

```python
config = ChunkingConfig(
    strategy=ChunkStrategyEnum.PARAGRAPH,
    max_tokens=1000,
)
```

**Behavior:**
- Splits on double newlines (\\n\\n)
- Groups paragraphs to target size

**When to use:**
- Blog posts
- Articles
- Documentation

---

## Working with Chunks

### Chunk Model Fields
```python
chunk = Chunk(
    chunk_id="a1b2c3d4-...",        # UUID4-style unique ID
    document_id="doc_123",          # Source document
    chunk_index=0,                  # Position in document
    content="Chunk text...",        # Text content
    start_char=0,                   # Character offset (start)
    end_char=100,                   # Character offset (end)
    token_count=25,                 # Token count
    overlap_tokens=0,               # Overlap with previous
    metadata={"source": "..."},     # Document metadata

    # Section metadata (NEW in Feature 36.6)
    section_headings=["Intro", "Overview"],
    section_pages=[1, 2],
    section_bboxes=[{...}, {...}],
)
```

### Converting Chunks for Consumers

#### For Qdrant (Vector DB)
```python
payload = chunk.to_qdrant_payload()
# Contains: text, section_headings, section_pages, section_bboxes, etc.
await qdrant_client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=chunk.chunk_id,
            vector=embedding,
            payload=payload,
        )
    ],
)
```

#### For BM25 (Keyword Search)
```python
bm25_doc = chunk.to_bm25_document()
bm25_engine.add_document(
    doc_id=chunk.chunk_id,
    text=bm25_doc["text"],
)
```

#### For Neo4j/LightRAG (Graph DB)
```python
lightrag_data = chunk.to_lightrag_format()
await neo4j_client.create_chunk_node(
    chunk_id=lightrag_data["chunk_id"],
    text=lightrag_data["text"],
    metadata=lightrag_data,
)
```

---

## Section Metadata

### Extracting Sections from Docling
```python
from src.components.ingestion.section_extraction import extract_section_hierarchy
from src.components.ingestion.langgraph_nodes import SectionMetadata

# After Docling parsing
docling_document = await docling_client.parse_document("file.pdf")

# Extract sections
sections = extract_section_hierarchy(
    docling_document=docling_document,
    section_metadata_class=SectionMetadata,
)

# Use sections with ChunkingService
service = get_chunking_service()
chunks = await service.chunk_document(
    text=docling_document.export_to_text(),
    document_id="doc_123",
    sections=sections,
)
```

### Section Metadata Structure
```python
section = SectionMetadata(
    heading="Multi-Server Architecture",    # Section title
    level=1,                                # Heading level (1-6)
    page_no=2,                              # Page number
    bbox={                                  # Bounding box
        "l": 50.0,   # Left
        "t": 30.0,   # Top
        "r": 670.0,  # Right
        "b": 80.0,   # Bottom
    },
    text="Section text content...",
    token_count=250,
    metadata={"source": "doc.pdf"},
)
```

---

## Best Practices

### 1. Use Adaptive Strategy with Sections
**Recommended for production:**
```python
# Extract sections from Docling
sections = extract_section_hierarchy(docling_doc, SectionMetadata)

# Chunk with sections
service = get_chunking_service()
chunks = await service.chunk_document(
    text=full_text,
    document_id=doc_id,
    sections=sections,  # ← Include sections!
)
```

**Why:**
- Better retrieval quality (+10-15%)
- Reduces fragmentation (PowerPoint: 124 → 2-3 chunks)
- Preserves document structure
- Enables section-based re-ranking

### 2. Use Same Chunks for All Indexes
**CRITICAL for index consistency:**
```python
# Chunk ONCE
chunks = await chunking_service.chunk_document(text, doc_id, sections)

# Index to ALL systems with same chunks
await index_to_qdrant(chunks)
await index_to_bm25(chunks)
await index_to_neo4j(chunks)
```

**Why:**
- Guaranteed consistency (same chunk IDs)
- Graph-vector alignment works
- Hybrid search returns same results

### 3. Use Singleton Pattern
```python
# Good: Uses singleton (efficient)
service = get_chunking_service()

# Avoid: Creates new instance every time
service = ChunkingService()  # Don't do this in production!
```

**Why:**
- Reduces memory usage
- Shares tokenizer instance
- Faster initialization

### 4. Pass Metadata Through
```python
chunks = await service.chunk_document(
    text=text,
    document_id=doc_id,
    sections=sections,
    metadata={
        "source": "document.pdf",
        "author": "Klaus Pommer",
        "created_at": "2025-12-05",
        "file_type": "pdf",
    },
)
```

**Why:**
- Metadata flows to all chunks
- Available in Qdrant payloads
- Useful for filtering/re-ranking

---

## Troubleshooting

### Issue: Empty Chunks
**Symptom:** `ValueError: Content cannot be empty`

**Solution:**
```python
if text and text.strip():
    chunks = await service.chunk_document(text, doc_id)
```

### Issue: Too Many Small Chunks
**Symptom:** 100+ chunks for a small document

**Solution:** Increase max_tokens or use adaptive strategy
```python
config = ChunkingConfig(
    strategy=ChunkStrategyEnum.ADAPTIVE,
    max_tokens=1800,  # ← Increase
)
```

### Issue: Chunks Too Large
**Symptom:** Chunks exceed embedding model limits (e.g., 8192 tokens)

**Solution:** Decrease max_tokens
```python
config = ChunkingConfig(
    max_tokens=1000,  # ← Decrease to fit model
)
```

### Issue: No Section Metadata in Chunks
**Symptom:** `chunk.section_headings` is empty

**Solution:** Pass sections to chunk_document
```python
# Extract sections first
sections = extract_section_hierarchy(docling_doc, SectionMetadata)

# Pass to chunking service
chunks = await service.chunk_document(
    text=text,
    document_id=doc_id,
    sections=sections,  # ← Don't forget this!
)
```

---

## Testing

### Unit Test Example
```python
import pytest
from src.core import ChunkingService, ChunkingConfig, ChunkStrategyEnum

@pytest.mark.asyncio
async def test_adaptive_chunking():
    config = ChunkingConfig(strategy=ChunkStrategyEnum.ADAPTIVE)
    service = ChunkingService(config)

    text = "Sample document text..."
    chunks = await service.chunk_document(text, "test_doc_001")

    assert len(chunks) > 0
    assert all(c.token_count > 0 for c in chunks)
```

### Integration Test Example
```python
@pytest.mark.asyncio
async def test_end_to_end_chunking():
    # 1. Parse with Docling
    docling_doc = await docling_client.parse_document("test.pdf")

    # 2. Extract sections
    sections = extract_section_hierarchy(docling_doc, SectionMetadata)

    # 3. Chunk with ChunkingService
    service = get_chunking_service()
    chunks = await service.chunk_document(
        text=docling_doc.export_to_text(),
        document_id="test_doc",
        sections=sections,
    )

    # 4. Verify consistency
    assert len(chunks) > 0
    assert all(len(c.section_headings) > 0 for c in chunks)
```

---

## Migration Guide (For Existing Code)

### Before (Old Pattern)
```python
# Old: Direct section merging in langgraph_nodes.py
from src.components.ingestion.langgraph_nodes import adaptive_section_chunking

sections = extract_sections(...)
chunks = adaptive_section_chunking(sections, min_chunk=800, max_chunk=1800)
```

### After (New Pattern)
```python
# New: Unified ChunkingService
from src.core import get_chunking_service

sections = extract_sections(...)
service = get_chunking_service()
chunks = await service.chunk_document(
    text=full_text,
    document_id=doc_id,
    sections=sections,
)
```

**Benefits:**
- Same chunks go to Qdrant, BM25, and Neo4j
- Configuration-driven behavior
- Better observability (Prometheus metrics)

---

## Performance Tips

### 1. Reuse Service Instance
```python
# Good: Reuse singleton
service = get_chunking_service()
for doc in documents:
    chunks = await service.chunk_document(doc.text, doc.id)
```

### 2. Batch Processing
```python
# Process multiple documents efficiently
service = get_chunking_service()
all_chunks = []
for doc in documents:
    chunks = await service.chunk_document(doc.text, doc.id, doc.sections)
    all_chunks.extend(chunks)

# Index all at once
await qdrant_client.upsert_batch(all_chunks)
```

### 3. Use Appropriate Strategy
- **Adaptive:** Best quality, slightly slower (~50-100ms)
- **Fixed:** Fastest, predictable (~20-50ms)
- **Sentence/Paragraph:** Medium speed (~30-70ms)

---

## References

- **Implementation Details:** `FEATURE_36_6_IMPLEMENTATION.md`
- **Technical Debt:** `docs/technical-debt/TD-054_UNIFIED_CHUNKING_SERVICE.md`
- **ADR:** `docs/adr/ADR-039-adaptive-section-aware-chunking.md`
- **Tests:** `tests/unit/core/test_chunking_service.py`

---

**Last Updated:** 2025-12-05
**Feature:** Sprint 36 Feature 36.6 (TD-054)
