# Document Upload User Guide

**Sprint 22 Feature 22.5: Comprehensive Upload Guide for 30 Document Formats**

Complete guide for uploading and managing documents in AegisRAG with intelligent format routing.

---

## Quick Start

### Upload Your First Document

```bash
# Upload a PDF (most common)
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@your_document.pdf"

# Upload a Markdown file
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@documentation.md"

# Upload an Excel file
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@data_analysis.xlsx"
```

### Check Supported Formats

```bash
curl http://localhost:8000/api/v1/retrieval/formats
```

---

## Supported Formats

AegisRAG supports **30 document formats** across three categories:

### Category 1: Docling-Exclusive (14 formats)

**Best for:** Complex documents with tables, images, or special formatting

**Formats:**
- **Office Documents:** `.pdf`, `.docx`, `.pptx`, `.xlsx`
- **Images:** `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`
- **Structured:** `.html`, `.xml`, `.json`, `.csv`, `.ipynb`

**Features:**
- GPU-accelerated OCR (95% accuracy)
- Table extraction (92% accuracy)
- Image extraction with bounding boxes
- Layout preservation
- 3.5x faster than CPU parsing

**GPU Requirement:** 6GB VRAM

**Example:**
```bash
# Upload PDF with complex layout
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@research_paper_with_tables.pdf"

# Expected processing time: ~2 minutes
```

---

### Category 2: LlamaIndex-Exclusive (9 formats)

**Best for:** Text-heavy documents, technical documentation, e-books

**Formats:**
- **E-books:** `.epub`
- **Markup Languages:** `.md`, `.rst`, `.adoc`, `.org`, `.tex`
- **Office/Messaging:** `.odt`, `.rtf`, `.msg`

**Features:**
- Text-only extraction
- 300+ connector ecosystem
- E-book support
- LaTeX and Markdown parsing
- No GPU required

**Example:**
```bash
# Upload Markdown documentation
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@technical_docs.md"

# Upload E-book
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@learning_rag.epub"

# Expected processing time: ~30 seconds
```

---

### Category 3: Shared Formats (7 formats)

**Best for:** Legacy documents, plain text, emails

**Formats:**
- **Legacy Office:** `.doc`, `.xls`, `.ppt`
- **Text & Web:** `.txt`, `.htm`, `.mhtml`, `.eml`

**Routing Logic:**
- Docling preferred when available (faster)
- Automatic fallback to LlamaIndex if Docling unavailable
- No manual intervention needed

**Example:**
```bash
# Upload plain text (uses Docling for speed)
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@meeting_notes.txt"

# If Docling unavailable, automatically uses LlamaIndex
```

---

## Upload Workflow

### Step-by-Step Process

```
1. User uploads document
   ↓
2. Format validation (is it one of 30 formats?)
   ↓
3. Format routing (Docling or LlamaIndex?)
   ↓
4. Document parsing (extract text, tables, images)
   ↓
5. Chunking (1800-token strategy with overlap)
   ↓
6. Embedding generation (BGE-M3 multilingual embeddings)
   ↓
7. Vector indexing (Qdrant for semantic search)
   ↓
8. Graph extraction (Neo4j for entity relationships)
   ↓
9. Return statistics (chunks, entities, duration)
```

### Processing Time Estimates

| Document Type | Size | Parser | Estimated Time |
|---------------|------|--------|----------------|
| Simple PDF (text-only) | 10 pages | Docling (GPU) | 30-60s |
| Complex PDF (tables + images) | 10 pages | Docling (GPU) | 60-120s |
| Scanned PDF (OCR needed) | 10 pages | Docling (GPU) | 120-180s |
| Markdown file | 5,000 words | LlamaIndex (CPU) | 10-20s |
| EPUB e-book | 300 pages | LlamaIndex (CPU) | 60-120s |
| Excel spreadsheet | 50 rows | Docling (GPU) | 20-40s |

---

## Format-Specific Considerations

### PDF Files (.pdf)

**Parser:** Docling CUDA Container (GPU)

**Best Practices:**
- Use for scanned documents (high OCR accuracy: 95%)
- Tables are automatically extracted (92% detection rate)
- Images are extracted with bounding box coordinates
- Layout is preserved for better context

**Limitations:**
- Requires Docling container running (no fallback)
- Password-protected PDFs not supported
- Max file size: 100MB

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@scanned_contract.pdf"
```

**Expected Output:**
```json
{
  "status": "success",
  "documents_loaded": 1,
  "chunks_created": 85,
  "embeddings_generated": 85,
  "points_indexed": 85,
  "duration_seconds": 95.3,
  "neo4j_entities": 28,
  "neo4j_relationships": 42
}
```

---

### Markdown Files (.md)

**Parser:** LlamaIndex MarkdownReader

**Best Practices:**
- Use for technical documentation
- Headers are preserved for structure
- Code blocks are retained
- Links are extracted

**Limitations:**
- Images not processed (only text)
- No table extraction (tables rendered as text)

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@api_documentation.md"
```

**Expected Output:**
```json
{
  "status": "success",
  "documents_loaded": 1,
  "chunks_created": 42,
  "embeddings_generated": 42,
  "points_indexed": 42,
  "duration_seconds": 12.7,
  "neo4j_entities": 15,
  "neo4j_relationships": 23
}
```

---

### Excel Files (.xlsx)

**Parser:** Docling CUDA Container (GPU)

**Best Practices:**
- Tables are automatically extracted
- Multiple sheets supported
- Formulas are evaluated
- Cell formatting preserved

**Limitations:**
- Charts not processed
- Macros not executed
- Max 10,000 rows per sheet

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@sales_data_2024.xlsx"
```

---

### E-books (.epub)

**Parser:** LlamaIndex EPUBReader

**Best Practices:**
- Use for technical books
- Chapters are treated as separate documents
- Table of contents is preserved
- Metadata (author, title) is extracted

**Limitations:**
- Images not processed
- DRM-protected EPUBs not supported
- Large files (>50MB) may timeout

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@learning_python.epub"
```

---

### LaTeX Documents (.tex)

**Parser:** LlamaIndex LaTeXReader

**Best Practices:**
- Use for academic papers
- Math equations are preserved
- Citations are extracted
- Sections are preserved

**Limitations:**
- Requires standalone .tex file (no external dependencies)
- Complex packages may not be supported
- Images not processed

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@research_paper.tex"
```

---

### Images (.png, .jpg, .tiff)

**Parser:** Docling CUDA Container (GPU with EasyOCR)

**Best Practices:**
- Use for scanned documents
- High-resolution images (300+ DPI) recommended
- Clear text (not handwritten)
- Good contrast (black text on white background)

**Limitations:**
- OCR accuracy: 95% (may have errors)
- Handwriting not supported
- Low-resolution images (<150 DPI) may fail
- Max file size: 20MB per image

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@scanned_invoice.png"
```

---

### Plain Text Files (.txt)

**Parser:** Docling (preferred) or LlamaIndex (fallback)

**Best Practices:**
- Use for meeting notes, logs, transcripts
- UTF-8 encoding recommended
- Line breaks are preserved
- Fast processing (uses Docling for speed)

**Limitations:**
- No formatting (bold, italic, etc.)
- No structure detection (headers, lists)

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@meeting_transcript.txt"
```

---

### Legacy Office Formats (.doc, .xls, .ppt)

**Parser:** LlamaIndex (more reliable for old formats)

**Best Practices:**
- Convert to modern formats (.docx, .xlsx, .pptx) if possible
- Use for legacy documents only
- May have compatibility issues

**Limitations:**
- Limited table extraction
- No image extraction
- May lose formatting

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@old_presentation.ppt"
```

---

## Troubleshooting

### Error: Unsupported File Format

**Problem:**
```json
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "Invalid file format: document.xyz"
  }
}
```

**Solution:**
1. Check file extension (must be one of 30 formats)
2. List supported formats: `curl http://localhost:8000/api/v1/retrieval/formats`
3. Convert file to supported format (e.g., .zip → .pdf, .rar → .txt)

**Common Unsupported Formats:**
- Archives: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`
- Audio: `.mp3`, `.wav`, `.flac`
- Video: `.mp4`, `.avi`, `.mkv`
- Executables: `.exe`, `.dmg`, `.app`

---

### Error: File Too Large

**Problem:**
```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File too large: huge_document.pdf (150.00MB > 100MB)"
  }
}
```

**Solution:**
1. Check file size: `ls -lh document.pdf`
2. Maximum size: **100MB**
3. Split large PDF into smaller files:
   ```bash
   # Using pdftk
   pdftk large.pdf burst output page_%03d.pdf

   # Upload each page separately
   for file in page_*.pdf; do
     curl -X POST http://localhost:8000/api/v1/retrieval/upload \
       -F "file=@$file"
   done
   ```
4. Compress images in PDF before uploading (use Acrobat or Ghostscript)

---

### Error: Docling Container Unavailable

**Problem:**
```json
{
  "error": {
    "code": "INGESTION_FAILED",
    "message": "Docling container unavailable and no fallback for .pdf"
  }
}
```

**Solution:**
1. Check if Docling container is running:
   ```bash
   docker ps | grep docling
   ```

2. Start Docling container:
   ```bash
   docker compose up -d docling
   ```

3. Check container health:
   ```bash
   docker compose exec docling curl http://localhost:5000/health
   ```

4. Check container logs for errors:
   ```bash
   docker compose logs docling --tail=50
   ```

5. Verify GPU availability (for CUDA):
   ```bash
   nvidia-smi
   ```

**For Shared Formats:**
If you upload a shared format (`.txt`, `.doc`, `.htm`), the system automatically falls back to LlamaIndex if Docling is unavailable. No action needed!

---

### Error: Ingestion Timeout

**Problem:**
Upload hangs or times out after 5 minutes.

**Solution:**
1. Check document complexity:
   - Large number of images (>50)
   - Complex tables (>100 rows)
   - High-resolution scans (>300 DPI)

2. Reduce document complexity:
   - Compress images before uploading
   - Split into smaller documents
   - Reduce image resolution

3. Check Docling container logs:
   ```bash
   docker compose logs docling --tail=100
   ```

4. Increase timeout in config:
   ```bash
   # In .env file
   INGESTION_TIMEOUT_SECONDS=600  # 10 minutes
   ```

5. Verify GPU memory:
   ```bash
   nvidia-smi
   # Should show <6GB VRAM used
   ```

---

### Error: OCR Accuracy Too Low

**Problem:**
Scanned PDF text is garbled or incomplete.

**Solution:**
1. Check image quality:
   - Resolution: 300+ DPI recommended
   - Contrast: Clear black text on white background
   - Skew: Document should be straight (not tilted)

2. Pre-process image before upload:
   ```bash
   # Using ImageMagick
   convert input.jpg -density 300 -contrast-stretch 0 output.pdf
   ```

3. Use higher-quality scan settings:
   - Scan at 600 DPI for small text
   - Use "Black & White" mode (not grayscale)
   - Ensure good lighting

4. For handwritten text:
   - OCR does not support handwriting (95% accuracy for printed text only)
   - Manually transcribe handwritten sections

---

### Error: Rate Limit Exceeded

**Problem:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded: 5 requests per minute"
  }
}
```

**Solution:**
1. Wait 60 seconds before retrying
2. Default rate limit: **5 uploads per minute**
3. Batch multiple documents with delay:
   ```bash
   for file in documents/*.pdf; do
     curl -X POST http://localhost:8000/api/v1/retrieval/upload \
       -F "file=@$file"
     sleep 12  # 5 requests per minute = 1 request every 12s
   done
   ```

4. Contact admin to increase rate limit (production only)

---

## Best Practices

### 1. Choose the Right Format

| Use Case | Recommended Format | Reason |
|----------|-------------------|--------|
| Scanned documents | `.pdf`, `.png`, `.tiff` | High OCR accuracy (95%) |
| Technical docs | `.md`, `.rst` | Structure preserved |
| Research papers | `.pdf`, `.tex` | Layout + equations |
| Spreadsheets | `.xlsx`, `.csv` | Table extraction |
| E-books | `.epub` | Chapter structure |
| Meeting notes | `.txt`, `.md` | Fast processing |

---

### 2. Optimize File Size

**Large files slow down processing and may timeout.**

**Recommendations:**
- Compress images in PDFs (use Acrobat or Ghostscript)
- Remove unnecessary pages
- Convert scanned PDFs to text-based PDFs (if text is searchable)
- Split large documents (>100 pages) into chapters

**Example (compress PDF):**
```bash
# Using Ghostscript
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile=output_compressed.pdf input.pdf
```

---

### 3. Use Batch Upload

**Upload multiple documents efficiently:**

```bash
#!/bin/bash
# batch_upload.sh

API_URL="http://localhost:8000/api/v1/retrieval/upload"
DOCS_DIR="./documents"

for file in "$DOCS_DIR"/*; do
  echo "Uploading: $file"

  response=$(curl -s -X POST "$API_URL" -F "file=@$file")

  status=$(echo "$response" | jq -r '.status')

  if [ "$status" = "success" ]; then
    chunks=$(echo "$response" | jq -r '.chunks_created')
    echo "✓ Success: $chunks chunks created"
  else
    error=$(echo "$response" | jq -r '.error.message')
    echo "✗ Failed: $error"
  fi

  sleep 12  # Rate limit: 5 per minute
done
```

**Run:**
```bash
chmod +x batch_upload.sh
./batch_upload.sh
```

---

### 4. Monitor Processing Status

**Use structured logging for debugging:**

```bash
# Check upload logs
docker compose logs api | grep "upload_format_routing"

# Check ingestion logs
docker compose logs api | grep "file_ingestion_complete"
```

**Example log output:**
```json
{
  "event": "upload_format_routing",
  "filename": "research.pdf",
  "format": ".pdf",
  "parser": "docling",
  "reason": "GPU-accelerated OCR",
  "confidence": "high",
  "request_id": "abc123"
}
```

---

### 5. Verify Ingestion Results

**After upload, verify document was indexed:**

```bash
# Search for document
curl -X POST http://localhost:8000/api/v1/retrieval/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query from document", "top_k": 5}'

# Check collection statistics
curl http://localhost:8000/api/v1/retrieval/stats
```

**Expected response:**
```json
{
  "status": "success",
  "qdrant_stats": {
    "vectors_count": 1250,
    "indexed_vectors_count": 1250,
    "points_count": 1250
  },
  "bm25_corpus_size": 1250,
  "bm25_fitted": true
}
```

---

## Advanced Usage

### Upload with Authentication

If authentication is enabled, include JWT token:

```bash
# Get token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/retrieval/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | jq -r '.access_token')

# Upload with token
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"
```

---

### Upload with Custom Metadata

**Coming in Sprint 23:** Custom metadata for documents

```bash
# Future feature (not yet implemented)
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@document.pdf" \
  -F "metadata={\"department\":\"engineering\",\"tags\":[\"tutorial\"]}"
```

---

### Check Docling Container Health

**Before uploading, check if Docling is available:**

```bash
# Check container status
docker compose ps docling

# Expected output:
# NAME     IMAGE              STATUS         PORTS
# docling  ds4sd/docling:1.0  Up 5 minutes   0.0.0.0:5000->5000/tcp

# Check container health endpoint
curl http://localhost:5000/health

# Expected response:
# {"status": "healthy", "version": "1.0.0"}
```

---

## FAQ

### Q: What happens if I upload the same document twice?

**A:** Each upload creates new chunks and embeddings. Duplicate detection is not implemented yet. To avoid duplicates, track uploaded documents on your side.

---

### Q: Can I upload password-protected PDFs?

**A:** No, password-protected PDFs are not supported. Remove password before uploading:
```bash
qpdf --password=PASSWORD --decrypt input.pdf output.pdf
```

---

### Q: Does AegisRAG support OCR for handwritten text?

**A:** No, OCR is optimized for printed text (95% accuracy). Handwritten text is not supported.

---

### Q: What is the maximum file size?

**A:** Maximum file size is **100MB** per document. For larger documents, split into smaller files.

---

### Q: Can I upload ZIP archives?

**A:** No, archives (.zip, .rar, .7z) are not supported. Extract files first, then upload individual documents.

---

### Q: How long does processing take?

**A:** Depends on document type and size:
- Simple PDF (text-only): 30-60s
- Complex PDF (tables + images): 60-180s
- Markdown file: 10-20s
- EPUB e-book: 60-120s

---

### Q: What happens if Docling container is unavailable?

**A:**
- For **shared formats** (.txt, .doc, .htm): Automatic fallback to LlamaIndex
- For **Docling-exclusive formats** (.pdf, .docx): Upload fails with error

---

### Q: Can I upload documents from external URLs?

**A:** Not directly. Download first, then upload:
```bash
wget https://example.com/document.pdf
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@document.pdf"
```

---

## See Also

- **API Documentation:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\docs\api\UPLOAD_ENDPOINT.md`
- **Format Support Matrix:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\FORMAT_SUPPORT_MATRIX.md`
- **Error Responses:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\docs\api\ERROR_RESPONSES.md`
- **FormatRouter Implementation:** `C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\src\components\ingestion\format_router.py`
- **Architecture Decision:** ADR-027 (Docling CUDA Container Integration)
- **Architecture Decision:** ADR-028 (LlamaIndex Deprecation Strategy)

---

**Last Updated:** 2025-11-11 (Sprint 22 Feature 22.5)
**Total Supported Formats:** 30
**GPU Requirement:** 6GB VRAM (for Docling formats)
