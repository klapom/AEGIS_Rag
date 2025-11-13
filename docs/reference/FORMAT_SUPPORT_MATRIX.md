# AegisRAG Format Support Matrix

**Last Updated:** 2025-11-11 (Sprint 22 Phase 2)
**Total Supported Formats:** 30

---

## Quick Reference

| Category | Count | Parser | Key Features |
|----------|-------|--------|--------------|
| **Docling-Exclusive** | 14 | Docling CUDA Container | GPU-accelerated OCR (95%), Table extraction (92%), Layout preservation |
| **LlamaIndex-Exclusive** | 9 | LlamaIndex Parsers | Text-only, 300+ connectors, E-book support, LaTeX parsing |
| **Shared Formats** | 7 | Docling (preferred) | Both parsers support, Docling preferred for performance |

---

## Docling-Exclusive Formats (14)

**GPU-accelerated parsing with advanced extraction**

### Documents (4 formats)
- `.pdf` - 95% OCR accuracy with EasyOCR CUDA
- `.docx` - Native layout preservation, table detection
- `.pptx` - Slide structure + embedded images
- `.xlsx` - Table extraction with 92% accuracy

### Images (5 formats)
- `.png` - Image OCR with high accuracy
- `.jpg` / `.jpeg` - JPEG image OCR
- `.tiff` - High-resolution document scans
- `.bmp` - Bitmap images

### Structured (5 formats)
- `.html` - HTML with DOM structure
- `.xml` - XML with schema awareness
- `.json` - JSON with structure preservation
- `.csv` - Table-aware CSV parsing
- `.ipynb` - Jupyter notebooks with cell structure

**Performance:** 420s → 120s per document (3.5x faster than LlamaIndex)
**GPU Requirement:** 6GB VRAM for optimal performance

---

## LlamaIndex-Exclusive Formats (9)

**Text-only extraction with specialized connectors**

### E-books (1 format)
- `.epub` - E-book format (LlamaIndex EPUBReader)

### Markup Languages (5 formats)
- `.md` - Markdown (LlamaIndex MarkdownReader)
- `.rst` - reStructuredText (LlamaIndex RSTReader)
- `.adoc` - AsciiDoc (LlamaIndex AsciiDocReader)
- `.org` - Org-Mode (LlamaIndex OrgReader)
- `.tex` - LaTeX documents (LlamaIndex LaTeXReader)

### Office/Messaging (3 formats)
- `.odt` - OpenDocument Text (LlamaIndex ODTReader)
- `.rtf` - Rich Text Format (LlamaIndex RTFReader)
- `.msg` - Outlook messages (LlamaIndex MSGReader)

**Connector Ecosystem:** 300+ connectors for various data sources
**Use Case:** Text-heavy documents, technical documentation, e-books

---

## Shared Formats (7)

**Both parsers support, Docling preferred for performance**

### Legacy Office (3 formats)
- `.doc` - Legacy Word (LlamaIndex more reliable for old format)
- `.xls` - Legacy Excel (LlamaIndex more reliable)
- `.ppt` - Legacy PowerPoint (LlamaIndex more reliable)

### Text & Web (4 formats)
- `.txt` - Plain text (both support, Docling faster)
- `.htm` - HTML variant
- `.mhtml` - Web archive (MIME HTML)
- `.eml` - Email messages (RFC 822)

**Routing Logic:** Docling preferred when available, graceful degradation to LlamaIndex if Docling unavailable

---

## API Endpoints

### GET /api/v1/retrieval/formats

Get complete format support information.

**Response:**
```json
{
  "total_formats": 30,
  "formats": {
    "docling_exclusive": [14 formats],
    "llamaindex_exclusive": [9 formats],
    "shared": [7 formats]
  },
  "parser_info": {
    "docling": {
      "formats": 21,
      "features": ["GPU-accelerated OCR (95% accuracy)", ...]
    },
    "llamaindex": {
      "formats": 16,
      "features": ["Text-only extraction", ...]
    }
  },
  "all_formats": [30 formats sorted]
}
```

### POST /api/v1/retrieval/upload

Upload document for ingestion (30 formats supported).

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@document.pdf"
```

**Error Response (Unsupported Format):**
```json
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "Invalid file format: document.xyz",
    "details": {
      "filename": "document.xyz",
      "expected_formats": [30 formats listed]
    }
  }
}
```

---

## Routing Decision Tree

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

### Shared Formats:
- Plain text (.txt) → Docling (faster)
- HTML/MHTML → Docling (better DOM parsing)
- Email (.eml) → LlamaIndex (better RFC 822 support)
- Legacy Office → LlamaIndex (better compatibility)

---

## Architecture Decisions

- **ADR-027:** Docling CUDA Container vs. LlamaIndex (chose Docling for GPU OCR)
- **ADR-028:** LlamaIndex Deprecation Strategy (positioned as strategic fallback)
- **Feature 22.3:** Format Router implementation (30 formats, intelligent routing)
- **Feature 22.4:** LlamaIndex Parser integration (connector library)

---

## Testing

### Manual Testing
```bash
# Test all format categories
curl -F "file=@document.pdf" http://localhost:8000/api/v1/retrieval/upload
curl -F "file=@document.md" http://localhost:8000/api/v1/retrieval/upload
curl -F "file=@document.epub" http://localhost:8000/api/v1/retrieval/upload
curl -F "file=@document.txt" http://localhost:8000/api/v1/retrieval/upload

# Test unsupported format
curl -F "file=@document.xyz" http://localhost:8000/api/v1/retrieval/upload

# Get format support info
curl http://localhost:8000/api/v1/retrieval/formats
```

### Integration Tests
See: `tests/integration/api/test_format_router.py`

---

## Future Enhancements

1. **Additional Formats:** Expand to 50+ formats (e.g., `.mobi`, `.azw`, `.cbr`)
2. **Dynamic Router:** Health check Docling availability every 60s
3. **Format Analytics:** Track most-used formats for optimization
4. **Custom Parsers:** Allow user-defined parsers for proprietary formats
5. **Format Conversion:** Auto-convert legacy formats to modern equivalents

---

**For more information:**
- `src/components/ingestion/format_router.py` - Routing logic
- `src/api/v1/retrieval.py` - API integration
- `SPRINT_22_PHASE_2_COMPLETE.md` - Implementation details
