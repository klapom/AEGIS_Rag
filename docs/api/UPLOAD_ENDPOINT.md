# Document Upload & Format Support API

**Sprint 22 Feature 22.5: 30-Format Support with Hybrid Ingestion**

Complete documentation for document upload endpoints with intelligent format routing between Docling (GPU-accelerated) and LlamaIndex (fallback) parsers.

---

## Overview

AegisRAG supports **30 document formats** across three categories:
- **Docling-Exclusive (14 formats)**: GPU-accelerated OCR, table extraction, layout preservation
- **LlamaIndex-Exclusive (9 formats)**: E-books, markup languages, legacy formats
- **Shared Formats (7 formats)**: Both parsers support, Docling preferred for performance

The system intelligently routes documents to the optimal parser using the **FormatRouter**, which considers:
- Format capabilities (OCR, table extraction, layout preservation)
- Parser availability (Docling container health)
- Performance characteristics (GPU vs CPU)
- Fallback options (graceful degradation)

---

## Endpoints

### 1. POST /api/v1/retrieval/upload

Upload and index a single document file (30 formats supported).

#### Request

**Endpoint:** `POST /api/v1/retrieval/upload`

**Headers:**
```http
Content-Type: multipart/form-data
Authorization: Bearer <token>  (optional, if auth enabled)
```

**Body Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | File | Yes | Document file to upload (max 100MB) |

**Supported Formats:** See [Supported Formats](#supported-formats) section below.

#### Response (Success)

**Status Code:** `200 OK`

**Response Body:**
```json
{
  "status": "success",
  "documents_loaded": 1,
  "chunks_created": 42,
  "embeddings_generated": 42,
  "points_indexed": 42,
  "duration_seconds": 12.35,
  "collection_name": "aegis_rag_docs",
  "neo4j_entities": 15,
  "neo4j_relationships": 23
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| status | string | Ingestion status: "success" or "partial" |
| documents_loaded | integer | Number of documents loaded (always 1 for single upload) |
| chunks_created | integer | Number of text chunks generated (1800-token strategy) |
| embeddings_generated | integer | Number of embeddings created (BGE-M3) |
| points_indexed | integer | Number of vectors indexed in Qdrant |
| duration_seconds | float | Total processing time in seconds |
| collection_name | string | Qdrant collection name ("aegis_rag_docs") |
| neo4j_entities | integer | Entities extracted to Neo4j graph |
| neo4j_relationships | integer | Relationships extracted to Neo4j graph |

#### Error Responses

##### Invalid File Format (400)

**Scenario:** File format not in 30 supported formats

**Response:**
```json
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "Invalid file format: document.xyz",
    "details": {
      "filename": "document.xyz",
      "expected_formats": [
        ".adoc", ".bmp", ".csv", ".doc", ".docx", ".eml", ".epub",
        ".htm", ".html", ".ipynb", ".jpeg", ".jpg", ".json", ".md",
        ".mhtml", ".msg", ".odt", ".org", ".pdf", ".png", ".ppt",
        ".pptx", ".rst", ".rtf", ".tex", ".tiff", ".txt", ".xls",
        ".xlsx", ".xml"
      ]
    },
    "request_id": "e808db8f-63ea-4e11-b666-c1c770965a2d",
    "timestamp": "2025-11-11T14:47:32Z",
    "path": "/api/v1/retrieval/upload"
  }
}
```

##### File Too Large (413)

**Scenario:** File exceeds 100MB limit

**Response:**
```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File too large: huge_document.pdf (150.00MB > 100MB)",
    "details": {
      "filename": "huge_document.pdf",
      "size_mb": 150.0,
      "max_size_mb": 100.0
    },
    "request_id": "c3d4e5f6-g7h8-9i0j-1k2l-m3n4o5p6q7r8",
    "timestamp": "2025-11-11T14:32:30.789012Z",
    "path": "/api/v1/retrieval/upload"
  }
}
```

##### Ingestion Failed (500)

**Scenario:** Document processing failed (parsing, embedding, or indexing error)

**Response:**
```json
{
  "error": {
    "code": "INGESTION_FAILED",
    "message": "Document ingestion failed: Docling parsing timeout after 300s",
    "details": {
      "filename": "corrupt_document.pdf",
      "reason": "Docling parsing timeout after 300s",
      "stage": "parsing"
    },
    "request_id": "d4e5f6g7-h8i9-0j1k-2l3m-n4o5p6q7r8s9",
    "timestamp": "2025-11-11T14:35:00.123456Z",
    "path": "/api/v1/retrieval/upload"
  }
}
```

##### Rate Limit Exceeded (429)

**Scenario:** Too many upload requests (default: 5 per minute)

**Response:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded: 5 requests per minute",
    "details": {
      "limit": 5,
      "window": "minute"
    },
    "request_id": "e5f6g7h8-i9j0-1k2l-3m4n-o5p6q7r8s9t0",
    "timestamp": "2025-11-11T14:36:00.345678Z",
    "path": "/api/v1/retrieval/upload"
  }
}
```

#### Examples

##### Upload PDF (Docling GPU Parser)

```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@research_paper.pdf"
```

**Expected Routing:** Docling CUDA Container (GPU-accelerated OCR, 95% accuracy)

**Response:**
```json
{
  "status": "success",
  "documents_loaded": 1,
  "chunks_created": 128,
  "embeddings_generated": 128,
  "points_indexed": 128,
  "duration_seconds": 45.2,
  "collection_name": "aegis_rag_docs",
  "neo4j_entities": 42,
  "neo4j_relationships": 67
}
```

##### Upload Markdown (LlamaIndex Parser)

```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@technical_docs.md"
```

**Expected Routing:** LlamaIndex MarkdownReader (text-only extraction)

**Response:**
```json
{
  "status": "success",
  "documents_loaded": 1,
  "chunks_created": 35,
  "embeddings_generated": 35,
  "points_indexed": 35,
  "duration_seconds": 8.7,
  "collection_name": "aegis_rag_docs",
  "neo4j_entities": 12,
  "neo4j_relationships": 18
}
```

##### Upload Plain Text (Shared Format - Docling Preferred)

```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@notes.txt"
```

**Expected Routing:** Docling (faster processing for shared formats)

**Fallback:** If Docling unavailable, automatically uses LlamaIndex

##### Upload Unsupported Format (Error)

```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@archive.zip"
```

**Response (400 Bad Request):**
```json
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "Invalid file format: archive.zip",
    "details": {
      "filename": "archive.zip",
      "expected_formats": [
        ".adoc", ".bmp", ".csv", ".doc", ".docx", ".eml", ".epub",
        ".htm", ".html", ".ipynb", ".jpeg", ".jpg", ".json", ".md",
        ".mhtml", ".msg", ".odt", ".org", ".pdf", ".png", ".ppt",
        ".pptx", ".rst", ".rtf", ".tex", ".tiff", ".txt", ".xls",
        ".xlsx", ".xml"
      ]
    }
  }
}
```

---

### 2. GET /api/v1/retrieval/formats

Get comprehensive format support information including parser capabilities and routing logic.

#### Request

**Endpoint:** `GET /api/v1/retrieval/formats`

**Headers:** None required

**Query Parameters:** None

#### Response (Success)

**Status Code:** `200 OK`

**Response Body:**
```json
{
  "total_formats": 30,
  "formats": {
    "docling_exclusive": [
      ".bmp", ".csv", ".docx", ".html", ".ipynb", ".jpeg",
      ".jpg", ".json", ".pdf", ".png", ".pptx", ".tiff",
      ".xlsx", ".xml"
    ],
    "llamaindex_exclusive": [
      ".adoc", ".epub", ".md", ".msg", ".odt", ".org",
      ".rst", ".rtf", ".tex"
    ],
    "shared": [
      ".doc", ".eml", ".htm", ".mhtml", ".ppt", ".txt", ".xls"
    ]
  },
  "parser_info": {
    "docling": {
      "formats": 21,
      "features": [
        "GPU-accelerated OCR (95% accuracy)",
        "Table extraction (92% accuracy)",
        "Image extraction with BBox coordinates",
        "Layout preservation"
      ]
    },
    "llamaindex": {
      "formats": 16,
      "features": [
        "Text-only extraction",
        "300+ connector ecosystem",
        "E-book support (EPUB)",
        "LaTeX and Markdown parsing"
      ]
    }
  },
  "all_formats": [
    ".adoc", ".bmp", ".csv", ".doc", ".docx", ".eml", ".epub",
    ".htm", ".html", ".ipynb", ".jpeg", ".jpg", ".json", ".md",
    ".mhtml", ".msg", ".odt", ".org", ".pdf", ".png", ".ppt",
    ".pptx", ".rst", ".rtf", ".tex", ".tiff", ".txt", ".xls",
    ".xlsx", ".xml"
  ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| total_formats | integer | Total supported formats (30) |
| formats.docling_exclusive | array | Formats only Docling supports (14) |
| formats.llamaindex_exclusive | array | Formats only LlamaIndex supports (9) |
| formats.shared | array | Formats both parsers support (7) |
| parser_info.docling.formats | integer | Total formats Docling supports (21 = 14 + 7) |
| parser_info.docling.features | array | Docling parser capabilities |
| parser_info.llamaindex.formats | integer | Total formats LlamaIndex supports (16 = 9 + 7) |
| parser_info.llamaindex.features | array | LlamaIndex parser capabilities |
| all_formats | array | All 30 supported formats (sorted alphabetically) |

#### Example

```bash
curl http://localhost:8000/api/v1/retrieval/formats
```

---

## Supported Formats

### Docling-Exclusive Formats (14)

**GPU-accelerated parsing with advanced extraction**

#### Documents (4 formats)
- `.pdf` - 95% OCR accuracy with EasyOCR CUDA
- `.docx` - Native layout preservation, table detection
- `.pptx` - Slide structure + embedded images
- `.xlsx` - Table extraction with 92% accuracy

#### Images (5 formats)
- `.png` - Image OCR with high accuracy
- `.jpg` / `.jpeg` - JPEG image OCR
- `.tiff` - High-resolution document scans
- `.bmp` - Bitmap images

#### Structured (5 formats)
- `.html` - HTML with DOM structure
- `.xml` - XML with schema awareness
- `.json` - JSON with structure preservation
- `.csv` - Table-aware CSV parsing
- `.ipynb` - Jupyter notebooks with cell structure

**Performance:** 120s per document (GPU)
**GPU Requirement:** 6GB VRAM for optimal performance

---

### LlamaIndex-Exclusive Formats (9)

**Text-only extraction with specialized connectors**

#### E-books (1 format)
- `.epub` - E-book format (LlamaIndex EPUBReader)

#### Markup Languages (5 formats)
- `.md` - Markdown (LlamaIndex MarkdownReader)
- `.rst` - reStructuredText (LlamaIndex RSTReader)
- `.adoc` - AsciiDoc (LlamaIndex AsciiDocReader)
- `.org` - Org-Mode (LlamaIndex OrgReader)
- `.tex` - LaTeX documents (LlamaIndex LaTeXReader)

#### Office/Messaging (3 formats)
- `.odt` - OpenDocument Text (LlamaIndex ODTReader)
- `.rtf` - Rich Text Format (LlamaIndex RTFReader)
- `.msg` - Outlook messages (LlamaIndex MSGReader)

**Connector Ecosystem:** 300+ connectors for various data sources
**Use Case:** Text-heavy documents, technical documentation, e-books

---

### Shared Formats (7)

**Both parsers support, Docling preferred for performance**

#### Legacy Office (3 formats)
- `.doc` - Legacy Word (LlamaIndex more reliable for old format)
- `.xls` - Legacy Excel (LlamaIndex more reliable)
- `.ppt` - Legacy PowerPoint (LlamaIndex more reliable)

#### Text & Web (4 formats)
- `.txt` - Plain text (both support, Docling faster)
- `.htm` - HTML variant
- `.mhtml` - Web archive (MIME HTML)
- `.eml` - Email messages (RFC 822)

**Routing Logic:** Docling preferred when available, graceful degradation to LlamaIndex if Docling unavailable

---

## FormatRouter Behavior

The FormatRouter implements intelligent routing logic based on document format and parser availability:

### Routing Decision Tree

```
Document Upload
│
├─ Format Check
│  ├─ Supported? → Continue
│  └─ Not Supported? → Return 400 with 30 formats listed
│
├─ Parser Selection (FormatRouter)
│  ├─ Docling-Exclusive (.pdf, .docx, .png, etc.)
│  │  ├─ Docling Available? → Use Docling (GPU)
│  │  └─ Docling Unavailable? → Error (no fallback)
│  │
│  ├─ LlamaIndex-Exclusive (.md, .epub, .rst, etc.)
│  │  └─ Always use LlamaIndex
│  │
│  └─ Shared Format (.txt, .doc, .htm, etc.)
│     ├─ Docling Available? → Use Docling (prefer performance)
│     └─ Docling Unavailable? → Use LlamaIndex (fallback)
│
└─ Ingestion Pipeline
   ├─ Memory Check
   ├─ Document Parsing (Docling or LlamaIndex)
   ├─ Chunking (1800-token strategy)
   ├─ Embedding (BGE-M3)
   └─ Graph Extraction (Neo4j)
```

### Routing Examples

| File Extension | Docling Available | Selected Parser | Reason | Confidence |
|----------------|-------------------|-----------------|--------|------------|
| `.pdf` | Yes | Docling | GPU-accelerated OCR (95%) | High |
| `.pdf` | No | Error | No fallback available | N/A |
| `.md` | Yes | LlamaIndex | LlamaIndex-exclusive format | High |
| `.md` | No | LlamaIndex | LlamaIndex-exclusive format | High |
| `.txt` | Yes | Docling | Shared format, prefer performance | High |
| `.txt` | No | LlamaIndex | Shared format, fallback | Medium |
| `.epub` | Yes | LlamaIndex | E-books only in LlamaIndex | High |
| `.xyz` | Yes | Error | Format not supported | N/A |

### Graceful Degradation

For **shared formats** (.txt, .doc, .htm, etc.):
- If Docling container is unavailable or unhealthy, the system automatically falls back to LlamaIndex
- Logs include warning: `docling_unavailable_fallback`
- Response confidence level: `medium` (instead of `high`)

For **Docling-exclusive formats** (.pdf, .docx, .png, etc.):
- If Docling container is unavailable, ingestion fails with error
- No fallback available (LlamaIndex cannot handle GPU OCR tasks)
- User must start Docling container or use supported fallback format

---

## Performance Comparison

| Aspect | Docling | LlamaIndex |
|--------|---------|------------|
| **OCR Accuracy** | 95% (EasyOCR CUDA) | 70% (basic OCR) |
| **Table Extraction** | 92% detection rate | Limited |
| **Speed** | 120s/doc (GPU) | 420s/doc (CPU) |
| **Image Extraction** | Yes (with BBox) | Limited |
| **Layout Preservation** | Yes | No |
| **GPU Requirement** | 6GB VRAM | None |
| **Connector Ecosystem** | Limited | 300+ connectors |
| **E-book Support** | No | Yes (EPUB) |
| **LaTeX/Markdown** | No | Yes |

---

## Usage Recommendations

### Use Docling For:
- PDFs with complex layouts (tables, images)
- Scanned documents requiring OCR
- Office documents (DOCX, XLSX, PPTX)
- Image-based documents (PNG, JPG, TIFF)
- High-accuracy requirements (>90%)

### Use LlamaIndex For:
- E-books (EPUB)
- Markdown/reStructuredText documentation
- LaTeX papers
- Legacy Office formats (.doc, .xls)
- Text-heavy documents without complex layout

### Shared Formats Strategy:
- Plain text (.txt) → Docling (faster)
- HTML/MHTML → Docling (better DOM parsing)
- Email (.eml) → LlamaIndex (better RFC 822 support)
- Legacy Office → LlamaIndex (better compatibility)

---

## Rate Limiting

### Upload Endpoint
- **Limit:** 5 requests per minute per IP
- **Reason:** Document processing is resource-intensive
- **Exceeded:** Returns 429 with retry-after header

### Formats Endpoint
- **Limit:** None (read-only operation)

---

## Authentication

Both endpoints support optional authentication:
- If `AUTH_ENABLED=true` in config, JWT token required
- If `AUTH_ENABLED=false` (default), no authentication needed

**With Authentication:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document.pdf"
```

**Without Authentication:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@document.pdf"
```

---

## Logging

The system provides comprehensive logging for debugging and monitoring:

### Format Validation Logs
```json
{
  "level": "warning",
  "event": "unsupported_format_upload",
  "filename": "document.xyz",
  "format": ".xyz",
  "supported_count": 30,
  "request_id": "e808db8f-63ea-4e11-b666-c1c770965a2d"
}
```

### Routing Decision Logs
```json
{
  "level": "info",
  "event": "upload_format_routing",
  "filename": "research_paper.pdf",
  "format": ".pdf",
  "parser": "docling",
  "reason": "Docling-optimized format with GPU acceleration",
  "confidence": "high",
  "request_id": "d4e5f6g7-h8i9-0j1k-2l3m-n4o5p6q7r8s9"
}
```

### Ingestion Complete Logs
```json
{
  "level": "info",
  "event": "file_ingestion_complete",
  "filename": "research_paper.pdf",
  "documents": 1,
  "chunks_created": 128,
  "points_indexed": 128,
  "neo4j_entities": 42,
  "neo4j_relationships": 67,
  "duration": 45.2,
  "errors": 0,
  "request_id": "d4e5f6g7-h8i9-0j1k-2l3m-n4o5p6q7r8s9"
}
```

---

## Troubleshooting

### Issue: Unsupported Format Error

**Problem:** Upload returns 400 with "INVALID_FILE_FORMAT"

**Solution:**
1. Check file extension (must be one of 30 supported formats)
2. Call `GET /formats` endpoint to see all supported formats
3. Convert file to supported format if needed (e.g., .zip → .pdf)

### Issue: Docling Unavailable Error

**Problem:** PDF upload fails with "Docling container unavailable"

**Solution:**
1. Check if Docling container is running: `docker ps | grep docling`
2. Start Docling container: `docker compose up -d docling`
3. Check container health: `docker compose exec docling curl http://localhost:5000/health`
4. For shared formats, system auto-falls back to LlamaIndex

### Issue: File Too Large Error

**Problem:** Upload returns 413 "FILE_TOO_LARGE"

**Solution:**
1. Check file size: `ls -lh document.pdf`
2. Maximum size: 100MB
3. Split large PDF into smaller files
4. Or compress images before uploading

### Issue: Ingestion Timeout

**Problem:** Upload hangs or times out after 5 minutes

**Solution:**
1. Check Docling container logs: `docker compose logs docling`
2. Verify GPU availability: `nvidia-smi`
3. Reduce document complexity (fewer images, simpler layout)
4. Increase timeout in config: `INGESTION_TIMEOUT_SECONDS=600`

---

## See Also

- **FormatRouter Implementation:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\src\components\ingestion\format_router.py`
- **API Implementation:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\src\api\v1\retrieval.py`
- **Format Support Matrix:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\FORMAT_SUPPORT_MATRIX.md`
- **Error Responses:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\docs\api\ERROR_RESPONSES.md`
- **User Guide:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\docs\guides\DOCUMENT_UPLOAD_GUIDE.md`
- **Architecture Decision:** ADR-027 (Docling CUDA Container Integration)
- **Architecture Decision:** ADR-028 (LlamaIndex Deprecation Strategy)

---

**Last Updated:** 2025-11-11 (Sprint 22 Feature 22.5)
**API Version:** v1
**Total Supported Formats:** 30
