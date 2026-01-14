# Feature 62.7: Document Type Support for Sections

**Sprint:** 62
**Points:** 5 SP
**Status:** Implemented
**Date:** 2025-12-23

## Overview

Feature 62.7 extends the document processing pipeline to support document type metadata for sections, enabling type-specific section handling and filtering across PDF, DOCX, HTML, Markdown, and other formats.

## Problem Statement

Previously, the ingestion pipeline treated all documents generically without considering their format-specific characteristics. This limited:
- Type-specific section extraction strategies
- Filtering results by document type in retrieval
- Preserving format-specific metadata (page numbers, heading styles, HTML tags)
- Providing users with context about document source format

## Solution

Implemented comprehensive document type support including:
1. **DocumentType Enum** - Supported types: PDF, DOCX, HTML, MD, TXT, XLSX, PPTX
2. **Type Detection** - File extension and MIME type detection with fallback
3. **SectionMetadata** - Extensible metadata model capturing type-specific information
4. **Type-Specific Handlers** - Format-aware section extraction (PDF page tracking, DOCX heading styles, HTML tags, Markdown levels)
5. **Chunk Integration** - Document type stored in chunk metadata and storage payloads

## Architecture

### Document Type System

```
DocumentType Enum
├── PDF       → Page numbers, bounding boxes
├── DOCX      → Heading styles (Heading 1-6)
├── HTML      → Heading tags (h1-h6)
├── MD        → Markdown headers, line numbers
├── TXT       → Plain text fallback
├── XLSX      → Spreadsheet structure
├── PPTX      → Slide structure
└── UNKNOWN   → Unsupported formats
```

### Type Detection Strategy

```
detect_document_type(file_path, mime_type)
│
├─ If mime_type provided → Try MIME mapping
├─ Fallback to file extension mapping
└─ Return DocumentType.UNKNOWN if not found
```

### Section Handler Routing

```
get_section_handler(document_type)
│
├─ PDF    → PDFSectionHandler
├─ DOCX   → DocxSectionHandler
├─ HTML   → HTMLSectionHandler
├─ MD     → MarkdownSectionHandler
├─ Other  → GenericSectionHandler (fallback)
└─ All handlers implement SectionHandler protocol
```

## Implementation Details

### 1. Document Types Module (`document_types.py`)

Provides core type detection and metadata models:

```python
from src.domains.document_processing.document_types import (
    DocumentType,           # Enum with supported types
    SectionMetadata,        # Type-specific section info
    detect_document_type,   # File → DocumentType mapper
)

# Detect type from file
doc_type = detect_document_type(Path("report.pdf"))
# DocumentType.PDF

# With MIME type (overrides extension)
doc_type = detect_document_type(Path("file.bin"), mime_type="application/pdf")
# DocumentType.PDF

# Create section metadata
metadata = SectionMetadata(
    heading="Chapter 1",
    level=1,
    document_type=DocumentType.PDF,
    page_no=5,
    bbox=[10.5, 20.3, 100.5, 80.2]
)

# Convert to/from dict for storage
data = metadata.to_dict()
restored = SectionMetadata.from_dict(data)
```

### 2. Section Handlers Module (`section_handlers.py`)

Type-specific section extraction logic:

```python
from src.domains.document_processing.section_handlers import (
    get_section_handler,
    PDFSectionHandler,
    DocxSectionHandler,
    HTMLSectionHandler,
    MarkdownSectionHandler,
)

# Get appropriate handler
handler = get_section_handler(DocumentType.PDF)

# Extract sections with type-specific logic
sections = handler.extract_sections(parsed_content, DocumentType.PDF)

# Sections contain metadata with type-specific fields:
# PDF: page_no, page_start, page_end, bbox
# DOCX: style (Heading 1, 2, etc.)
# HTML: tag (h1, h2, etc.)
# MD: line_no
```

### 3. Chunk Model Update (`src/core/chunk.py`)

Added `document_type` field to track document format:

```python
from src.core.chunk import Chunk

chunk = Chunk(
    chunk_id="abc123",
    document_id="doc_001",
    chunk_index=0,
    content="Sample content",
    start_char=0,
    end_char=15,
    document_type="pdf",  # NEW: Document type
)

# Included in storage payloads
qdrant_payload = chunk.to_qdrant_payload()
# Contains: "document_type": "pdf"

bm25_doc = chunk.to_bm25_document()
# Contains: "document_type": "pdf"

neo4j_data = chunk.to_lightrag_format()
# Contains: "document_type": "pdf"
```

## Features

### 1. Document Type Detection

Automatic detection from file extension and MIME type:

```python
detect_document_type(Path("file.pdf"))                    # PDF
detect_document_type(Path("file.docx"))                   # DOCX
detect_document_type(Path("file.html"))                   # HTML
detect_document_type(Path("file.md"))                     # MD
detect_document_type(Path("unknown.bin"), "application/pdf")  # PDF (MIME priority)
```

**Supported Mappings:**
- Extensions: .pdf, .docx, .html, .md, .txt, .xlsx, .pptx, etc.
- MIME types: application/pdf, application/vnd.openxmlformats-*, text/*, etc.
- Legacy formats: .doc → DOCX, .xls → XLSX, .ppt → PPTX

### 2. Type-Specific Section Handlers

Each handler extracts sections optimally for its format:

#### PDF Handler
- Tracks page numbers for each section
- Extracts bounding boxes for visual layout
- Determines content position (start/middle/end)
- Preserves multi-page section boundaries

#### DOCX Handler
- Detects heading styles (Heading 1-6)
- Maps styles to hierarchy levels
- Preserves document outline structure
- Handles nested heading hierarchies

#### HTML Handler
- Parses heading tags (h1-h6)
- Extracts heading levels from tags
- Preserves semantic HTML structure
- Case-insensitive tag parsing

#### Markdown Handler
- Extracts markdown headers (#, ##, ###, etc.)
- Tracks line numbers for each section
- Preserves heading hierarchy
- Supports ATX format headers

#### Generic Handler (Fallback)
- Handles unsupported formats gracefully
- Creates default sections if needed
- Preserves available metadata

### 3. Section Metadata Model

Captures type-specific information:

```python
@dataclass
class SectionMetadata:
    heading: str                        # Section title
    level: int                          # Heading level (1-6)
    document_type: DocumentType         # Source document type
    page_no: int | None                 # PDF: page number
    page_start: int | None              # PDF: start page
    page_end: int | None                # PDF: end page
    bbox: list[float] | None            # PDF: bounding box
    line_no: int | None                 # Markdown: line number
    style: str | None                   # DOCX: heading style
    content_position: str               # start/middle/end
```

### 4. Storage Integration

Document type included in all storage payloads:

**Qdrant (Vector DB):**
```python
payload = chunk.to_qdrant_payload()
# {
#   "document_type": "pdf",
#   "section_headings": [...],
#   "section_pages": [...],
#   ...
# }
```

**BM25 (Text Search):**
```python
doc = chunk.to_bm25_document()
# {
#   "document_type": "pdf",
#   "text": "...",
#   ...
# }
```

**Neo4j (Graph DB):**
```python
lightrag_format = chunk.to_lightrag_format()
# {
#   "document_type": "pdf",
#   "text": "...",
#   ...
# }
```

### 5. Filtering by Document Type

Retrieve results filtered by source document type:

```python
# Vector search with document type filter
results = vector_store.search(
    query_text="machine learning",
    filters={"document_type": "pdf"}
)

# Graph queries with document type
graph_results = graph_store.query(
    "MATCH (e:Entity)-[:APPEARS_IN]->(c:Chunk)
     WHERE c.document_type = 'docx'
     RETURN e"
)

# BM25 search with type filtering
bm25_results = bm25_index.search(
    query="RAG systems",
    filters={"document_type": {"in": ["pdf", "docx"]}}
)
```

## Testing

### Unit Tests (89 tests, 98% coverage)

#### Document Type Tests (`test_document_types.py` - 53 tests)
- DocumentType enum validation
- File extension mapping (all formats)
- MIME type mapping (all types)
- Detection logic (with edge cases)
- SectionMetadata model operations
- Type descriptions

**Key Tests:**
- PDF/DOCX/HTML/MD detection from extensions
- MIME type priority over extensions
- Case-insensitive detection
- Legacy format support (.doc → DOCX)
- Metadata serialization (to_dict/from_dict)
- Round-trip conversion

#### Section Handler Tests (`test_section_handlers.py` - 36 tests)
- Handler type matching (should_handle)
- Section extraction for each type
- Heading hierarchy (DOCX styles, HTML tags)
- Content position detection (PDF)
- Line number tracking (Markdown)
- Handler routing and fallback
- Integration workflows

**Key Tests:**
- PDF: page tracking, content position
- DOCX: heading style mapping (1-6)
- HTML: heading tag extraction
- Markdown: header levels and line numbers
- Generic handler as fallback
- Complete extraction workflows

### Coverage Report

```
src/domains/document_processing/
├── document_types.py       100% (55 statements)
├── section_handlers.py      94% (104 statements)
│   Missing: 6 edge case branches
├── __init__.py             100%
├── protocols.py            100%
└── vlm_service.py          100%

Total: 98% coverage
```

## Usage Examples

### Basic Document Type Detection

```python
from pathlib import Path
from src.domains.document_processing.document_types import detect_document_type

# Detect from file path
pdf_type = detect_document_type(Path("report.pdf"))
assert pdf_type.value == "pdf"

# With MIME type override
doc_type = detect_document_type(Path("unknown"), mime_type="application/pdf")
assert doc_type.value == "pdf"
```

### Section Extraction Workflow

```python
from src.domains.document_processing.section_handlers import (
    get_section_handler,
)
from src.domains.document_processing.document_types import (
    detect_document_type,
)

# Detect document type
file_path = Path("document.docx")
doc_type = detect_document_type(file_path)

# Get appropriate handler
handler = get_section_handler(doc_type)

# Extract sections
sections = handler.extract_sections(parsed_content, doc_type)

# Each section has type-specific metadata
for section in sections:
    metadata = section["metadata"]
    print(f"{metadata.heading} (Level {metadata.level})")
    if metadata.style:  # DOCX
        print(f"  Style: {metadata.style}")
    if metadata.page_no is not None:  # PDF
        print(f"  Page: {metadata.page_no}")
```

### Chunk Creation with Document Type

```python
from src.core.chunk import Chunk
from src.domains.document_processing.document_types import (
    detect_document_type,
)

file_path = Path("document.pdf")
doc_type = detect_document_type(file_path)

chunk = Chunk(
    chunk_id="abc123",
    document_id="doc_001",
    chunk_index=0,
    content="Document content...",
    start_char=0,
    end_char=100,
    document_type=doc_type.value,  # Store document type
    section_headings=["Introduction"],
    metadata={"source": "document.pdf"}
)

# Document type included in storage
qdrant_payload = chunk.to_qdrant_payload()
assert qdrant_payload["document_type"] == "pdf"
```

### Filtering Retrieval Results by Document Type

```python
# Example: Vector search with document type filter
from src.core.chunk import Chunk

# Search only in PDF documents
pdf_chunks = [
    c for c in search_results
    if c.document_type == "pdf"
]

# Search in specific formats
supported_formats = ["pdf", "docx", "html"]
filtered_chunks = [
    c for c in search_results
    if c.document_type in supported_formats
]
```

## Integration with Ingestion Pipeline

The feature is designed for seamless integration with the existing ingestion pipeline:

1. **Document Detection** → Detect type during file upload
2. **Parsing** → Route to appropriate parser based on type
3. **Section Extraction** → Use type-specific handler
4. **Chunking** → Include document_type in chunk metadata
5. **Embedding** → Store type in Qdrant payload
6. **Graph Storage** → Include type in Neo4j nodes
7. **Retrieval** → Enable filtering by document type

## API Endpoints

Future endpoints for document type awareness:

```python
# Search with document type filter
POST /api/v1/retrieval/search
{
    "query": "machine learning",
    "document_types": ["pdf", "docx"],
    "top_k": 5
}

# Get document type statistics
GET /api/v1/documents/statistics
# Returns: {
#   "total_documents": 150,
#   "by_type": {
#     "pdf": 75,
#     "docx": 45,
#     "html": 30
#   }
# }

# Filter documents by type
GET /api/v1/documents?type=pdf
```

## Migration & Backward Compatibility

- **Chunk Model**: New `document_type` field defaults to "unknown"
- **Existing Chunks**: Will have `document_type="unknown"` until re-ingested
- **No Breaking Changes**: All existing APIs remain compatible
- **Optional Feature**: Detection and filtering are optional enhancements

## Performance Impact

- **Type Detection**: <1ms per file (extension/MIME lookup)
- **Section Extraction**: Minimal overhead (handler selection)
- **Storage**: Negligible (1 string field per chunk)
- **Filtering**: Efficient with indexed payload fields in Qdrant

## Future Enhancements

1. **Advanced Type Detection**
   - Content-based detection (magic numbers, structure analysis)
   - Multi-format validation

2. **Type-Specific Chunking**
   - Format-aware chunk boundaries
   - Preserve table structure in XLSX
   - Respect slide boundaries in PPTX

3. **Format-Specific Metadata**
   - Extract and store embedded metadata
   - Preserve formatting information
   - Track document structure trees

4. **Enhanced Filtering**
   - Complex queries: (type="pdf" AND pages>10)
   - Type-based aggregations and statistics
   - Document quality scores by type

5. **Type Conversion**
   - Detect and convert legacy formats (.doc → DOCX)
   - Multi-format document fusion

## Files Created/Modified

### Created Files
1. **`src/domains/document_processing/document_types.py`** (213 lines)
   - DocumentType enum
   - SectionMetadata model
   - detect_document_type function
   - Type mappings (extension, MIME)

2. **`src/domains/document_processing/section_handlers.py`** (435 lines)
   - SectionHandler base class
   - PDFSectionHandler
   - DocxSectionHandler
   - HTMLSectionHandler
   - MarkdownSectionHandler
   - GenericSectionHandler
   - get_section_handler router

3. **`tests/unit/domains/document_processing/test_document_types.py`** (515 lines)
   - 53 unit tests
   - 100% coverage of document_types module

4. **`tests/unit/domains/document_processing/test_section_handlers.py`** (565 lines)
   - 36 unit tests
   - 94% coverage of section_handlers module

### Modified Files
1. **`src/core/chunk.py`**
   - Added `document_type` field to Chunk model
   - Updated `to_qdrant_payload()` to include document_type
   - Updated `to_bm25_document()` to include document_type
   - Updated `to_lightrag_format()` to include document_type

## Test Results

```
Test Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Tests:     89
Passed:          89 (100%)
Failed:          0
Skipped:         0
Coverage:        98%

By Module:
  test_document_types.py:     53 tests ✓
  test_section_handlers.py:   36 tests ✓

Coverage by Module:
  document_types.py:          100% (55 stmts)
  section_handlers.py:         94% (104 stmts)
  Overall document_processing: 98%
```

## Success Criteria

- [x] Document type detected accurately for all formats (PDF, DOCX, HTML, MD, TXT, XLSX, PPTX)
- [x] Section extraction adapts to document type
- [x] Filtering by document type supported (in storage layer)
- [x] All tests pass (89/89)
- [x] Coverage >80% (98% achieved)
- [x] Chunk metadata includes document_type
- [x] Storage payloads include document_type
- [x] Backward compatible with existing chunks

## References

- **ADR-024**: BGE-M3 Embeddings
- **ADR-026**: Pure LLM Extraction Pipeline
- **ADR-027**: Docling CUDA Container
- **ADR-039**: Section-aware Chunking
- **Sprint 62**: Structured Output & Type Support
- **Sprint 56**: Domain-Driven Architecture

## Conclusion

Feature 62.7 successfully extends the AegisRAG system with comprehensive document type support, enabling format-aware section handling and flexible filtering throughout the retrieval pipeline. The implementation is fully tested (98% coverage), backward compatible, and ready for integration with the ingestion pipeline.
