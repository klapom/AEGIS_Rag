# Document Type Support Quick Reference

**Feature:** 62.7 - Document Type Support for Sections
**Module:** `src/domains/document_processing/`
**Test Coverage:** 98%

## Quick Start

### Import the Core Components

```python
from src.domains.document_processing.document_types import (
    DocumentType,
    SectionMetadata,
    detect_document_type,
)
from src.domains.document_processing.section_handlers import (
    get_section_handler,
)
```

### Detect Document Type

```python
from pathlib import Path

# From file extension
doc_type = detect_document_type(Path("document.pdf"))
print(doc_type.value)  # "pdf"

# With MIME type override
doc_type = detect_document_type(Path("unknown.bin"), mime_type="application/pdf")

# Supported types
from src.domains.document_processing.document_types import DocumentType
DocumentType.PDF      # "pdf"
DocumentType.DOCX    # "docx"
DocumentType.HTML    # "html"
DocumentType.MD      # "markdown"
DocumentType.TXT     # "text"
DocumentType.XLSX    # "xlsx"
DocumentType.PPTX    # "pptx"
DocumentType.UNKNOWN # "unknown"
```

### Create Section Metadata

```python
from src.domains.document_processing.document_types import (
    DocumentType,
    SectionMetadata,
)

# Basic section
metadata = SectionMetadata(
    heading="Introduction",
    level=1,
    document_type=DocumentType.PDF,
)

# PDF with page numbers
pdf_meta = SectionMetadata(
    heading="Chapter 1",
    level=1,
    document_type=DocumentType.PDF,
    page_no=5,
    page_start=5,
    page_end=15,
    bbox=[10.5, 20.3, 100.5, 80.2],
)

# DOCX with heading style
docx_meta = SectionMetadata(
    heading="Section Title",
    level=1,
    document_type=DocumentType.DOCX,
    style="Heading 1",
)

# Markdown with line number
md_meta = SectionMetadata(
    heading="Overview",
    level=2,
    document_type=DocumentType.MD,
    line_no=42,
)

# Convert to/from dictionary
data = metadata.to_dict()
restored = SectionMetadata.from_dict(data)
```

### Extract Sections with Type-Specific Handler

```python
from src.domains.document_processing.section_handlers import (
    get_section_handler,
)
from src.domains.document_processing.document_types import (
    detect_document_type,
)

# Get handler
file_path = Path("document.pdf")
doc_type = detect_document_type(file_path)
handler = get_section_handler(doc_type)

# Extract sections
sections = handler.extract_sections(parsed_content, doc_type)

# Access type-specific metadata
for section in sections:
    print(f"{section['heading']} (Level {section['level']})")
    metadata = section['metadata']
    if metadata.page_no is not None:
        print(f"  PDF Page: {metadata.page_no}")
    if metadata.style:
        print(f"  DOCX Style: {metadata.style}")
    if metadata.line_no is not None:
        print(f"  Markdown Line: {metadata.line_no}")
```

### Include Document Type in Chunks

```python
from src.core.chunk import Chunk
from src.domains.document_processing.document_types import (
    detect_document_type,
)

doc_type = detect_document_type(Path("document.pdf"))

chunk = Chunk(
    chunk_id="abc123",
    document_id="doc_001",
    chunk_index=0,
    content="Text content",
    start_char=0,
    end_char=12,
    document_type=doc_type.value,  # Store as string
    metadata={"source": "document.pdf"}
)

# Document type included in storage payloads
qdrant_payload = chunk.to_qdrant_payload()
# {"document_type": "pdf", ...}

bm25_doc = chunk.to_bm25_document()
# {"document_type": "pdf", ...}

neo4j_data = chunk.to_lightrag_format()
# {"document_type": "pdf", ...}
```

## Supported Document Types

| Type | Extension | MIME Type | Handler | Features |
|------|-----------|-----------|---------|----------|
| PDF | .pdf | application/pdf | PDFSectionHandler | Page numbers, bounding boxes |
| DOCX | .docx, .doc | application/vnd.openxmlformats-*.wordprocessingml.document | DocxSectionHandler | Heading styles (1-6) |
| HTML | .html, .htm | text/html | HTMLSectionHandler | Heading tags (h1-h6) |
| Markdown | .md, .markdown | text/markdown | MarkdownSectionHandler | Header levels, line numbers |
| Text | .txt | text/plain | GenericSectionHandler | Plain text fallback |
| Excel | .xlsx, .csv | application/vnd.openxmlformats-*.spreadsheetml.sheet | GenericSectionHandler | Tabular data |
| PowerPoint | .pptx | application/vnd.openxmlformats-*.presentationml.presentation | GenericSectionHandler | Slide structure |
| Unknown | Other | Unmapped | GenericSectionHandler | Fallback handling |

## Type-Specific Handlers

### PDFSectionHandler
- Tracks page numbers (0-indexed)
- Extracts bounding boxes [x1, y1, x2, y2]
- Determines content position: start (0-25%), middle (25-75%), end (75-100%)

### DocxSectionHandler
- Maps heading styles to levels: Heading 1→1, Heading 2→2, ... Heading 6→6
- Preserves document outline structure
- Handles custom/unknown styles (defaults to level 1)

### HTMLSectionHandler
- Extracts heading levels from tags: h1→1, h2→2, ... h6→6
- Case-insensitive tag parsing
- Non-heading tags default to level 1

### MarkdownSectionHandler
- Extracts header levels from markdown (# → 1, ## → 2, etc.)
- Tracks line numbers for each section
- Supports ATX format (#, ##, ###, etc.)

### GenericSectionHandler
- Fallback for all unsupported types
- Creates default sections if none found
- Graceful error handling

## Filter by Document Type

### In Qdrant

```python
# Filter by single type
results = qdrant_client.search(
    collection_name="documents",
    query_vector=embedding,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="document_type",
                match=MatchValue(value="pdf")
            )
        ]
    )
)

# Filter by multiple types
results = qdrant_client.search(
    collection_name="documents",
    query_vector=embedding,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="document_type",
                match=MatchAny(any=["pdf", "docx"])
            )
        ]
    )
)
```

### In Neo4j

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687")
with driver.session() as session:
    # Find chunks by document type
    result = session.run(
        "MATCH (c:Chunk) WHERE c.document_type = $type RETURN c",
        type="pdf"
    )

    # Find entities in specific document types
    result = session.run(
        """
        MATCH (e:Entity)-[:APPEARS_IN]->(c:Chunk)
        WHERE c.document_type IN ['pdf', 'docx']
        RETURN e, COUNT(c) as count
        """
    )
```

### In Application

```python
# Filter retrieval results
pdf_results = [c for c in results if c.document_type == "pdf"]

# Multiple types
multi_format = [
    c for c in results
    if c.document_type in ["pdf", "docx", "html"]
]

# Exclude type
non_text = [
    c for c in results
    if c.document_type not in ["txt"]
]
```

## Type Detection Strategy

```
detect_document_type(file_path, mime_type)
│
├─ Check provided MIME type first
│  └─ If found → Return mapped type
│
├─ Fall back to file extension
│  └─ If found → Return mapped type
│
└─ Return DocumentType.UNKNOWN
```

**Priority:** MIME Type > File Extension > Unknown

## Handler Routing

```
get_section_handler(document_type)
│
├─ DocumentType.PDF      → PDFSectionHandler
├─ DocumentType.DOCX     → DocxSectionHandler
├─ DocumentType.HTML     → HTMLSectionHandler
├─ DocumentType.MD       → MarkdownSectionHandler
├─ DocumentType.TXT      → GenericSectionHandler
├─ DocumentType.XLSX     → GenericSectionHandler
├─ DocumentType.PPTX     → GenericSectionHandler
└─ DocumentType.UNKNOWN  → GenericSectionHandler
```

## Common Patterns

### Pattern 1: Detect and Extract

```python
from pathlib import Path
from src.domains.document_processing.document_types import (
    detect_document_type,
)
from src.domains.document_processing.section_handlers import (
    get_section_handler,
)

def extract_document_sections(file_path: Path, parsed_content: dict):
    # Detect type
    doc_type = detect_document_type(file_path)

    # Get handler
    handler = get_section_handler(doc_type)

    # Extract sections
    return handler.extract_sections(parsed_content, doc_type)
```

### Pattern 2: Create Chunk with Type

```python
from pathlib import Path
from src.core.chunk import Chunk
from src.domains.document_processing.document_types import (
    detect_document_type,
)

def create_typed_chunk(file_path: Path, content: str, doc_id: str, idx: int):
    doc_type = detect_document_type(file_path)

    return Chunk(
        chunk_id=Chunk.generate_chunk_id(doc_id, idx, content),
        document_id=doc_id,
        chunk_index=idx,
        content=content,
        start_char=0,
        end_char=len(content),
        document_type=doc_type.value,
        metadata={"source": file_path.name}
    )
```

### Pattern 3: Type-Aware Filtering

```python
def filter_by_document_types(
    results: list[Chunk],
    allowed_types: list[str]
) -> list[Chunk]:
    return [
        chunk for chunk in results
        if chunk.document_type in allowed_types
    ]

# Usage
pdf_only = filter_by_document_types(results, ["pdf"])
multi_format = filter_by_document_types(results, ["pdf", "docx", "html"])
```

### Pattern 4: Statistics by Type

```python
from collections import Counter
from src.core.chunk import Chunk

def count_documents_by_type(chunks: list[Chunk]) -> dict[str, int]:
    return dict(Counter(c.document_type for c in chunks))

# Usage
stats = count_documents_by_type(all_chunks)
print(f"PDF: {stats.get('pdf', 0)}")
print(f"DOCX: {stats.get('docx', 0)}")
```

## Extension Points

### Adding New Document Type

1. Add to DocumentType enum
2. Add extension/MIME mappings
3. Create type-specific handler (implement SectionHandler)
4. Register in get_section_handler()
5. Add unit tests

```python
# 1. Update DocumentType enum
class DocumentType(str, Enum):
    EPUB = "epub"  # NEW

# 2. Update mappings
EXTENSION_TO_TYPE[".epub"] = DocumentType.EPUB
MIME_TO_TYPE["application/epub+zip"] = DocumentType.EPUB

# 3. Create handler
class EpubSectionHandler(SectionHandler):
    def should_handle(self, document_type: DocumentType) -> bool:
        return document_type == DocumentType.EPUB

    def extract_sections(self, parsed_content, document_type):
        # EPUB-specific logic
        pass

# 4. Register handler
def get_section_handler(document_type: DocumentType) -> SectionHandler:
    # ...
    EpubSectionHandler(),  # Add here
    # ...
```

## Troubleshooting

### Document type detected as UNKNOWN

```python
# Provide MIME type explicitly
from pathlib import Path
from src.domains.document_processing.document_types import (
    detect_document_type,
)

path = Path("file.bin")
doc_type = detect_document_type(
    path,
    mime_type="application/pdf"  # Specify MIME type
)
```

### Handler not found for type

```python
# All types have handlers (defaults to GenericSectionHandler)
from src.domains.document_processing.section_handlers import (
    get_section_handler,
)
from src.domains.document_processing.document_types import (
    DocumentType,
)

handler = get_section_handler(DocumentType.UNKNOWN)
# Returns: GenericSectionHandler()
```

### Missing metadata fields

```python
# Check document type and metadata availability
metadata = section['metadata']

# Optional fields depend on document type
if metadata.page_no is not None:  # PDF
    print(f"Page: {metadata.page_no}")

if metadata.style:  # DOCX
    print(f"Style: {metadata.style}")

if metadata.line_no is not None:  # Markdown
    print(f"Line: {metadata.line_no}")
```

## Testing

Run unit tests:

```bash
# All document type tests
poetry run pytest tests/unit/domains/document_processing/test_document_types.py -v

# All section handler tests
poetry run pytest tests/unit/domains/document_processing/test_section_handlers.py -v

# Combined with coverage
poetry run pytest tests/unit/domains/document_processing/ --cov=src.domains.document_processing -q
```

## Resources

- **Feature Documentation**: `docs/sprints/FEATURE_62_7_DOCUMENT_TYPE_SUPPORT.md`
- **Source Code**: `src/domains/document_processing/document_types.py`
- **Section Handlers**: `src/domains/document_processing/section_handlers.py`
- **Tests**: `tests/unit/domains/document_processing/test_*.py`
- **Chunk Model**: `src/core/chunk.py`

## Version

- **Feature:** 62.7
- **Status:** Complete
- **Coverage:** 98%
- **Tests:** 89 passing
- **Release:** Sprint 62 (2025-12-23)
