# Sprint 21: Unified Ingestion Pipeline

**Status:** 📋 PLANNED
**Goal:** Build production-ready unified document ingestion pipeline with Docling
**Duration:** 7 days (estimated)
**Prerequisites:** Sprint 20 complete (Performance optimizations, LM Studio evaluation)
**Story Points:** 42 SP

---

## 🎯 Sprint Objectives

### **Primary Goals:**
1. Replace fragmented document loading with unified ingestion pipeline
2. Implement Docling for heavy documents (PDF, DOCX, PPTX, XLSX, HTML)
3. Add native parsers for simple formats (Markdown, TXT, JSON, CSV)
4. Implement code parsing with Tree-sitter (Python, JavaScript, etc.)
5. Add email support (EML, MSG, MBOX)
6. Build archive handler for recursive processing (ZIP, TAR)
7. Establish standardized ingestion API and repository pattern

### **Success Criteria:**
- ✅ Single unified `IngestionPipeline` class handles all document types
- ✅ Docling successfully extracts text from PDF, PPTX, DOCX, XLSX
- ✅ Code files parsed with AST metadata (functions, classes)
- ✅ Email archives processed and indexed
- ✅ Archives recursively unpacked and processed
- ✅ 100% test coverage for all parsers
- ✅ Performance: <5s for typical document ingestion
- ✅ Backward compatibility with existing indexing scripts

---

## 📦 Sprint Features

### Feature 21.1: Docling Parser for Heavy Documents (13 SP)
**Priority:** HIGH - Foundation for document processing
**Duration:** 3 days

#### **Problem:**
Currently using LlamaIndex `SimpleDirectoryReader` which has limitations:
- ❌ Poor table extraction from PDFs
- ❌ No layout-aware parsing
- ❌ Limited PowerPoint support
- ❌ Inconsistent extraction quality

**From Sprint 20 chunk analysis:**
```
PowerPoint pages extracted with SimpleDirectoryReader:
  Page 1: 94 chars (title slide - poor quality)
  Page 2: 198 chars (missing content)
  Average: 470 chars/page (significant data loss suspected)
```

#### **Solution:**
Integrate IBM Docling for production-grade document parsing with:
- ✅ Layout-aware extraction
- ✅ Table structure preservation
- ✅ Image extraction and OCR
- ✅ Markdown output (RAG-friendly)

#### **Supported Formats:**
- **PDF** (.pdf) - Text extraction, OCR, table parsing
- **PowerPoint** (.pptx) - Slide content, notes, layout
- **Word** (.docx) - Paragraphs, tables, headers
- **Excel** (.xlsx) - Sheets, cell values, formulas
- **HTML** (.html, .htm) - Clean text extraction
- **AsciiDoc** (.adoc) - Technical documentation

#### **Architecture:**

```python
# src/components/ingestion/parsers/docling_parser.py
from pathlib import Path
from docling.document_converter import DocumentConverter
from src.components.ingestion.parsers.base import DocumentParser, ParsedDocument

class DoclingParser(DocumentParser):
    """Heavy document parser using IBM Docling.

    Handles: PDF, DOCX, PPTX, XLSX, HTML, AsciiDoc

    Features:
    - Layout-aware extraction
    - Table structure preservation
    - Image extraction + OCR
    - Markdown output

    Performance:
    - PDF (10 pages): ~3-5s
    - PPTX (50 slides): ~8-12s
    - DOCX (100 pages): ~10-15s
    """

    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xlsx', '.html', '.htm', '.adoc'}

    def __init__(self):
        self.converter = DocumentConverter()
        logger.info("Docling parser initialized", formats=list(self.SUPPORTED_EXTENSIONS))

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse document with Docling."""
        logger.info("Parsing with Docling", file=file_path.name, size_mb=file_path.stat().st_size / 1_000_000)

        start_time = time.time()
        result = self.converter.convert(str(file_path))
        elapsed = time.time() - start_time

        # Extract markdown representation
        content = result.document.export_to_markdown()

        # Extract metadata
        metadata = {
            'parser': 'docling',
            'num_pages': len(result.document.pages) if hasattr(result.document, 'pages') else 0,
            'has_tables': bool(result.document.tables) if hasattr(result.document, 'tables') else False,
            'has_images': bool(result.document.pictures) if hasattr(result.document, 'pictures') else False,
            'extraction_time_seconds': elapsed,
            'content_length_chars': len(content),
        }

        logger.info(
            "Docling extraction complete",
            file=file_path.name,
            pages=metadata['num_pages'],
            chars=metadata['content_length_chars'],
            time_s=elapsed,
        )

        return ParsedDocument(
            content=content,
            metadata=metadata,
            source_path=str(file_path),
            file_type=file_path.suffix[1:],
        )
```

#### **Tasks:**
- [ ] **Install Docling**
  ```bash
  poetry add docling
  # Dependencies: pypdf, python-docx, openpyxl, beautifulsoup4
  ```

- [ ] **Implement DoclingParser**
  - `src/components/ingestion/parsers/docling_parser.py`
  - File type detection (extension-based)
  - Docling `DocumentConverter` integration
  - Markdown export
  - Metadata extraction (pages, tables, images)
  - Error handling (corrupted files, unsupported versions)

- [ ] **Base Parser Protocol**
  - `src/components/ingestion/parsers/base.py`
  - `ParsedDocument` Pydantic model (content, metadata, source_path)
  - `DocumentParser` Protocol (parse, supports)
  - Type hints and docstrings

- [ ] **Integration with Existing Scripts**
  - Update `scripts/index_one_doc_test.py` to use DoclingParser
  - Backward compatibility with SimpleDirectoryReader
  - Performance benchmarking (vs old pipeline)

- [ ] **Testing**
  - Unit tests with fixture documents
  - Test each supported format (PDF, PPTX, DOCX, XLSX, HTML)
  - Edge cases (empty files, corrupted PDFs, password-protected)
  - Performance regression tests

#### **Deliverables:**
```bash
src/components/ingestion/parsers/base.py
src/components/ingestion/parsers/docling_parser.py
tests/ingestion/test_docling_parser.py
tests/fixtures/sample.pdf
tests/fixtures/sample.pptx
tests/fixtures/sample.docx
docs/sprints/SPRINT_21_DOCLING_BENCHMARKS.md
```

#### **Acceptance Criteria:**
- ✅ Docling installed and verified (poetry show docling)
- ✅ All 6 formats successfully parsed
- ✅ Markdown output generated for each document
- ✅ Metadata extracted (pages, tables, images)
- ✅ Performance: <5s for typical documents (<10 pages)
- ✅ Error handling: Graceful failure for corrupted files
- ✅ 100% test coverage for parser

---

### Feature 21.2: Native Parsers for Simple Formats (5 SP)
**Priority:** MEDIUM - Common use cases
**Duration:** 1 day

#### **Problem:**
Markdown, plain text, JSON, and CSV files don't need heavy processing but still require standardized parsing.

#### **Solution:**
Lightweight native Python parsers without external dependencies (except frontmatter for MD).

#### **Supported Formats:**

**1. Markdown** (.md, .markdown)
- Extract frontmatter metadata (YAML header)
- Parse content with python-frontmatter
- Preserve formatting for RAG

**2. Plain Text** (.txt)
- UTF-8 encoding
- Line-by-line reading
- Basic statistics (word count, line count)

**3. JSON** (.json, .jsonl)
- Pretty-print JSON for readability
- Extract schema for structured data
- JSONL support (one JSON object per line)

**4. CSV/TSV** (.csv, .tsv)
- Pandas-based parsing
- Row-by-row text format for RAG
- Column metadata

#### **Implementation:**

```python
# src/components/ingestion/parsers/markdown_parser.py
import frontmatter
from pathlib import Path
from src.components.ingestion.parsers.base import DocumentParser, ParsedDocument

class MarkdownParser(DocumentParser):
    """Native Markdown/Text parser.

    Handles: .md, .markdown, .txt

    Features:
    - YAML frontmatter extraction
    - UTF-8 encoding
    - Preserves formatting
    """

    SUPPORTED_EXTENSIONS = {'.md', '.markdown', '.txt'}

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse Markdown/Text file."""

        # Try to parse frontmatter (Markdown)
        try:
            post = frontmatter.load(file_path)
            content = post.content
            metadata = dict(post.metadata)
            metadata['has_frontmatter'] = True
        except:
            # Fallback: Plain text
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            metadata = {'has_frontmatter': False}

        # Add statistics
        metadata.update({
            'parser': 'native_markdown',
            'word_count': len(content.split()),
            'char_count': len(content),
            'line_count': content.count('\n') + 1,
        })

        return ParsedDocument(
            content=content,
            metadata=metadata,
            source_path=str(file_path),
            file_type=file_path.suffix[1:],
        )
```

```python
# src/components/ingestion/parsers/structured_parser.py
import json
import pandas as pd
from pathlib import Path
from src.components.ingestion.parsers.base import DocumentParser, ParsedDocument

class StructuredParser(DocumentParser):
    """Parser for structured data: JSON, CSV.

    Handles: .json, .jsonl, .csv, .tsv

    Converts structured data to RAG-friendly text format.
    """

    SUPPORTED_EXTENSIONS = {'.json', '.jsonl', '.csv', '.tsv'}

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse structured data."""
        ext = file_path.suffix.lower()

        if ext == '.json':
            return self._parse_json(file_path)
        elif ext == '.jsonl':
            return self._parse_jsonl(file_path)
        elif ext in {'.csv', '.tsv'}:
            return self._parse_csv(file_path, ext)

    def _parse_json(self, file_path: Path) -> ParsedDocument:
        """Parse JSON file."""
        with open(file_path) as f:
            data = json.load(f)

        # Pretty-print for readability
        content = json.dumps(data, indent=2, ensure_ascii=False)

        metadata = {
            'parser': 'native_json',
            'structure': 'json',
            'top_level_keys': list(data.keys()) if isinstance(data, dict) else [],
        }

        return ParsedDocument(
            content=content,
            metadata=metadata,
            source_path=str(file_path),
            file_type='json',
        )

    def _parse_csv(self, file_path: Path, ext: str) -> ParsedDocument:
        """Parse CSV/TSV file."""
        sep = '\t' if ext == '.tsv' else ','
        df = pd.read_csv(file_path, sep=sep)

        # Convert to text: row-by-row format
        rows = []
        for idx, row in df.iterrows():
            row_text = f"Row {idx + 1}: " + ", ".join([f"{col}: {row[col]}" for col in df.columns])
            rows.append(row_text)

        content = "\n\n".join(rows)

        metadata = {
            'parser': 'native_csv',
            'num_rows': len(df),
            'num_columns': len(df.columns),
            'columns': list(df.columns),
        }

        return ParsedDocument(
            content=content,
            metadata=metadata,
            source_path=str(file_path),
            file_type=ext[1:],
        )
```

#### **Tasks:**
- [ ] Implement MarkdownParser (frontmatter support)
- [ ] Implement StructuredParser (JSON, CSV)
- [ ] Unit tests for each format
- [ ] Encoding edge cases (UTF-8, Latin-1)

#### **Deliverables:**
```bash
src/components/ingestion/parsers/markdown_parser.py
src/components/ingestion/parsers/structured_parser.py
tests/ingestion/test_markdown_parser.py
tests/ingestion/test_structured_parser.py
tests/fixtures/sample.md
tests/fixtures/sample.json
tests/fixtures/sample.csv
```

#### **Acceptance Criteria:**
- ✅ Markdown frontmatter correctly parsed
- ✅ Plain text with correct encoding
- ✅ JSON pretty-printed for RAG
- ✅ CSV converted to readable text format
- ✅ 100% test coverage

---

### Feature 21.3: Code Parser with Tree-sitter (8 SP)
**Priority:** MEDIUM - Developer documentation
**Duration:** 2 days

#### **Problem:**
Code files contain structured information (functions, classes) that should be extracted for better RAG:
- ❌ Treating code as plain text loses structure
- ❌ No function/class metadata for search
- ❌ Language-agnostic parsing needed

#### **Solution:**
Tree-sitter AST parsing for multiple programming languages.

#### **Supported Languages:**
- **Python** (.py) - Functions, classes, decorators
- **JavaScript** (.js, .jsx) - Functions, classes, exports
- **TypeScript** (.ts, .tsx) - Interfaces, types, classes
- **Java** (.java) - Classes, methods, packages
- **Go** (.go) - Functions, structs, interfaces
- **Rust** (.rs) - Functions, structs, traits

#### **Extracted Metadata:**
```python
{
    'language': 'python',
    'num_functions': 12,
    'num_classes': 3,
    'functions': [
        {'name': 'parse_document', 'start_line': 42, 'end_line': 67},
        {'name': 'extract_metadata', 'start_line': 70, 'end_line': 85}
    ],
    'classes': [
        {'name': 'DocumentParser', 'start_line': 10, 'end_line': 40}
    ],
    'imports': ['pathlib', 'typing', 'pydantic']
}
```

#### **Implementation:**

```python
# src/components/ingestion/parsers/code_parser.py
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript
# ... more language modules

from src.components.ingestion.parsers.base import DocumentParser, ParsedDocument

class CodeParser(DocumentParser):
    """AST-based code parser using Tree-sitter.

    Handles: .py, .js, .ts, .java, .go, .rs

    Features:
    - Function/class extraction
    - Docstring parsing
    - Import/dependency tracking
    - Syntax-aware chunking
    """

    LANGUAGE_MAP = {
        '.py': ('python', tree_sitter_python),
        '.js': ('javascript', tree_sitter_javascript),
        '.jsx': ('javascript', tree_sitter_javascript),
        # Add more as needed
    }

    def __init__(self):
        self.parsers = {}
        self._init_parsers()

    def _init_parsers(self):
        """Initialize Tree-sitter parsers for each language."""
        for ext, (lang_name, lang_module) in self.LANGUAGE_MAP.items():
            parser = Parser()
            language = Language(lang_module.language())
            parser.set_language(language)
            self.parsers[ext] = (parser, lang_name)

        logger.info("Tree-sitter parsers initialized", languages=list(self.LANGUAGE_MAP.keys()))

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.LANGUAGE_MAP

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse code file with AST extraction."""

        with open(file_path, 'rb') as f:
            code_bytes = f.read()

        parser, lang_name = self.parsers[file_path.suffix.lower()]
        tree = parser.parse(code_bytes)

        # Extract functions and classes
        functions, classes = self._extract_entities(tree.root_node, lang_name)

        metadata = {
            'parser': 'tree_sitter',
            'language': lang_name,
            'num_functions': len(functions),
            'num_classes': len(classes),
            'functions': [f['name'] for f in functions],
            'classes': [c['name'] for c in classes],
        }

        # Return full code + structure info
        return ParsedDocument(
            content=code_bytes.decode('utf-8'),
            metadata=metadata,
            source_path=str(file_path),
            file_type=file_path.suffix[1:],
        )

    def _extract_entities(self, node, language):
        """Extract functions and classes from AST."""
        functions = []
        classes = []

        def traverse(n):
            # Python: function_definition, class_definition
            # JavaScript: function_declaration, class_declaration
            if n.type in ('function_definition', 'function_declaration', 'method_definition'):
                name_node = n.child_by_field_name('name')
                if name_node:
                    functions.append({
                        'name': name_node.text.decode('utf-8'),
                        'start_line': n.start_point[0] + 1,
                        'end_line': n.end_point[0] + 1,
                    })
            elif n.type in ('class_definition', 'class_declaration'):
                name_node = n.child_by_field_name('name')
                if name_node:
                    classes.append({
                        'name': name_node.text.decode('utf-8'),
                        'start_line': n.start_point[0] + 1,
                        'end_line': n.end_point[0] + 1,
                    })

            for child in n.children:
                traverse(child)

        traverse(node)
        return functions, classes
```

#### **Tasks:**
- [ ] Install Tree-sitter language libraries
  ```bash
  poetry add tree-sitter tree-sitter-python tree-sitter-javascript
  # Optional: tree-sitter-java, tree-sitter-go, tree-sitter-rust
  ```
- [ ] Implement CodeParser with AST traversal
- [ ] Language-specific entity extraction
- [ ] Test with real code samples
- [ ] Docstring extraction (optional)

#### **Deliverables:**
```bash
src/components/ingestion/parsers/code_parser.py
tests/ingestion/test_code_parser.py
tests/fixtures/sample.py
tests/fixtures/sample.js
docs/sprints/SPRINT_21_CODE_PARSING.md
```

#### **Acceptance Criteria:**
- ✅ Python functions and classes extracted
- ✅ JavaScript functions and classes extracted
- ✅ Metadata includes line numbers
- ✅ Edge cases: Nested classes, async functions
- ✅ Performance: <1s for typical code files

---

### Feature 21.4: Email Parser (5 SP)
**Priority:** LOW - Enterprise use case
**Duration:** 1 day

#### **Problem:**
Email archives (EML, MSG, MBOX) contain valuable communication history but are not currently supported.

#### **Solution:**
Native Python email parser using `email` and `mailbox` libraries.

#### **Supported Formats:**
- **EML** (.eml) - Single email message
- **MSG** (.msg) - Outlook message (requires msg-extractor)
- **MBOX** (.mbox) - Multiple email archive

#### **Implementation:**

```python
# src/components/ingestion/parsers/email_parser.py
import email
from email import policy
from pathlib import Path
import mailbox
from src.components.ingestion.parsers.base import DocumentParser, ParsedDocument

class EmailParser(DocumentParser):
    """Email message parser.

    Handles: .eml, .msg, .mbox

    Extracts:
    - Subject, from, to, date
    - Body (text/plain)
    - Attachments (optional)
    """

    SUPPORTED_EXTENSIONS = {'.eml', '.msg', '.mbox'}

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse email file."""
        ext = file_path.suffix.lower()

        if ext == '.mbox':
            return self._parse_mbox(file_path)
        else:
            return self._parse_single_email(file_path)

    def _parse_single_email(self, file_path: Path) -> ParsedDocument:
        """Parse single email (EML)."""

        with open(file_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_content()
                    break
        else:
            body = msg.get_content()

        metadata = {
            'parser': 'native_email',
            'subject': msg.get('subject', ''),
            'from': msg.get('from', ''),
            'to': msg.get('to', ''),
            'date': msg.get('date', ''),
            'message_id': msg.get('message-id', ''),
        }

        # Combine subject + body for content
        content = f"Subject: {metadata['subject']}\n\n{body}"

        return ParsedDocument(
            content=content,
            metadata=metadata,
            source_path=str(file_path),
            file_type='email',
        )
```

#### **Tasks:**
- [ ] Implement EmailParser (EML, MBOX)
- [ ] Multipart message handling
- [ ] Test with email fixtures
- [ ] Optional: MSG support (requires msg-extractor)

#### **Deliverables:**
```bash
src/components/ingestion/parsers/email_parser.py
tests/ingestion/test_email_parser.py
tests/fixtures/sample.eml
tests/fixtures/sample.mbox
```

#### **Acceptance Criteria:**
- ✅ EML files correctly parsed
- ✅ MBOX archives processed (multiple emails)
- ✅ Subject, from, to extracted
- ✅ Body text extracted (text/plain)

---

### Feature 21.5: Archive Handler (5 SP)
**Priority:** MEDIUM - Bulk ingestion
**Duration:** 1 day

#### **Problem:**
Users upload ZIP/TAR archives containing multiple documents. Need recursive unpacking and processing.

#### **Solution:**
Archive handler that extracts files to temp directory and recursively processes each file through the main pipeline.

#### **Supported Formats:**
- **ZIP** (.zip)
- **TAR** (.tar, .tar.gz, .tgz)

#### **Implementation:**

```python
# src/components/ingestion/parsers/archive_parser.py
import zipfile
import tarfile
import tempfile
from pathlib import Path
from src.components.ingestion.parsers.base import ParsedDocument

class ArchiveParser:
    """Archive unpacker and recursive processor.

    Handles: .zip, .tar, .tar.gz, .tgz

    Recursively processes all files in archive using main pipeline.
    """

    SUPPORTED_EXTENSIONS = {'.zip', '.tar', '.tar.gz', '.tgz'}

    def __init__(self, pipeline):
        """Initialize with reference to main pipeline."""
        self.pipeline = pipeline

    def supports(self, file_path: Path) -> bool:
        return any(str(file_path).endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)

    def parse(self, file_path: Path) -> list[ParsedDocument]:
        """Parse archive and process each file.

        Returns list of ParsedDocument (one per file in archive).
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract archive
            if file_path.suffix == '.zip':
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
            elif '.tar' in file_path.suffixes:
                with tarfile.open(file_path, 'r:*') as tar_ref:
                    tar_ref.extractall(tmpdir)

            # Process each extracted file
            documents = []
            for extracted_file in Path(tmpdir).rglob('*'):
                if extracted_file.is_file():
                    try:
                        doc = self.pipeline.process_file(extracted_file)
                        # Add archive context to metadata
                        doc.metadata['from_archive'] = str(file_path)
                        documents.append(doc)
                    except Exception as e:
                        logger.warning(
                            "Failed to process file from archive",
                            archive=file_path.name,
                            file=extracted_file.name,
                            error=str(e),
                        )

            logger.info(
                "Archive processed",
                archive=file_path.name,
                files_extracted=len(documents),
            )

            return documents
```

#### **Tasks:**
- [ ] Implement ArchiveParser with tempfile extraction
- [ ] Recursive processing via main pipeline
- [ ] Handle nested archives
- [ ] Metadata propagation (from_archive field)

#### **Deliverables:**
```bash
src/components/ingestion/parsers/archive_parser.py
tests/ingestion/test_archive_parser.py
tests/fixtures/sample.zip
```

#### **Acceptance Criteria:**
- ✅ ZIP files correctly extracted and processed
- ✅ TAR/TAR.GZ files correctly extracted
- ✅ Each file in archive processed recursively
- ✅ Metadata includes archive provenance

---

### Feature 21.6: Main Ingestion Pipeline (6 SP)
**Priority:** HIGH - Core orchestration
**Duration:** 1.5 days

#### **Problem:**
Need unified entry point that routes documents to correct parser and manages the ingestion workflow.

#### **Solution:**
`IngestionPipeline` class with parser registry and smart routing.

#### **Architecture:**

```python
# src/components/ingestion/pipeline.py
from pathlib import Path
from typing import List
from src.components.ingestion.parsers.base import ParsedDocument
from src.components.ingestion.parsers.docling_parser import DoclingParser
from src.components.ingestion.parsers.markdown_parser import MarkdownParser
from src.components.ingestion.parsers.code_parser import CodeParser
from src.components.ingestion.parsers.email_parser import EmailParser
from src.components.ingestion.parsers.structured_parser import StructuredParser
from src.components.ingestion.parsers.archive_parser import ArchiveParser

class IngestionPipeline:
    """Main document ingestion orchestrator.

    Routes documents to appropriate parser based on file extension.

    Usage:
        pipeline = IngestionPipeline()

        # Single file
        doc = pipeline.process_file(Path("document.pdf"))

        # Directory (recursive)
        docs = pipeline.process_directory(Path("data/documents/"))

    Supported Formats:
        - PDF, DOCX, PPTX, XLSX, HTML (Docling)
        - MD, TXT (Native)
        - PY, JS, TS, JAVA (Tree-sitter)
        - EML, MBOX (Email)
        - JSON, CSV (Structured)
        - ZIP, TAR (Archive)
    """

    def __init__(self):
        # Initialize parsers in priority order
        self.parsers = [
            DoclingParser(),         # Heavy documents
            MarkdownParser(),        # Markdown/text
            CodeParser(),            # Code files
            EmailParser(),           # Email
            StructuredParser(),      # JSON/CSV
        ]

        # Archive parser needs reference to pipeline
        self.archive_parser = ArchiveParser(self)

        logger.info(
            "Ingestion pipeline initialized",
            parsers=[type(p).__name__ for p in self.parsers],
        )

    def process_file(self, file_path: Path) -> ParsedDocument | list[ParsedDocument]:
        """Process single file.

        Returns:
            ParsedDocument or list[ParsedDocument] (for archives)
        """

        # Check if archive first
        if self.archive_parser.supports(file_path):
            logger.info("Processing archive", file=file_path.name)
            return self.archive_parser.parse(file_path)

        # Find appropriate parser
        for parser in self.parsers:
            if parser.supports(file_path):
                logger.info(
                    "Processing file",
                    file=file_path.name,
                    parser=type(parser).__name__,
                )
                return parser.parse(file_path)

        raise ValueError(f"No parser found for {file_path.suffix}")

    def process_directory(
        self,
        directory: Path,
        recursive: bool = True,
        file_extensions: list[str] | None = None,
    ) -> List[ParsedDocument]:
        """Process all files in directory.

        Args:
            directory: Directory path
            recursive: Recursively process subdirectories
            file_extensions: Optional filter (e.g., ['.pdf', '.pptx'])

        Returns:
            List of ParsedDocument
        """

        documents = []
        pattern = '**/*' if recursive else '*'

        for file_path in directory.glob(pattern):
            if file_path.is_file():
                # Filter by extension if specified
                if file_extensions and file_path.suffix.lower() not in file_extensions:
                    continue

                try:
                    doc = self.process_file(file_path)

                    # Archive returns list, others return single doc
                    if isinstance(doc, list):
                        documents.extend(doc)
                    else:
                        documents.append(doc)

                except Exception as e:
                    logger.error(
                        "Failed to process file",
                        file=file_path.name,
                        error=str(e),
                    )

        logger.info(
            "Directory processing complete",
            directory=directory.name,
            files_processed=len(documents),
        )

        return documents
```

#### **Tasks:**
- [ ] Implement IngestionPipeline with parser registry
- [ ] Smart routing based on file extension
- [ ] Error handling and logging
- [ ] Directory processing (recursive)
- [ ] File extension filtering
- [ ] Integration with existing indexing scripts

#### **Deliverables:**
```bash
src/components/ingestion/pipeline.py
src/components/ingestion/__init__.py
tests/ingestion/test_pipeline.py
scripts/test_ingestion_pipeline.py (demo script)
```

#### **Acceptance Criteria:**
- ✅ All parsers correctly registered
- ✅ Files routed to correct parser
- ✅ Directory processing works (recursive)
- ✅ Error handling graceful
- ✅ Performance: <1s overhead per file

---

## Testing Strategy

### Unit Tests (>80% coverage)
```python
# tests/ingestion/test_docling_parser.py
@pytest.mark.asyncio
async def test_docling_pdf_parsing():
    parser = DoclingParser()
    doc = parser.parse(Path("tests/fixtures/sample.pdf"))

    assert doc.content is not None
    assert len(doc.content) > 0
    assert doc.metadata['parser'] == 'docling'
    assert doc.metadata['num_pages'] > 0

# tests/ingestion/test_pipeline.py
def test_pipeline_routes_to_correct_parser():
    pipeline = IngestionPipeline()

    # PDF → DoclingParser
    doc = pipeline.process_file(Path("tests/fixtures/sample.pdf"))
    assert doc.metadata['parser'] == 'docling'

    # Markdown → MarkdownParser
    doc = pipeline.process_file(Path("tests/fixtures/sample.md"))
    assert doc.metadata['parser'] == 'native_markdown'

    # Python → CodeParser
    doc = pipeline.process_file(Path("tests/fixtures/sample.py"))
    assert doc.metadata['parser'] == 'tree_sitter'
```

### Integration Tests
- Test full directory ingestion
- Test mixed file types in one directory
- Test archive with nested documents
- Performance benchmarking

### Performance Tests
```python
# tests/performance/test_ingestion_performance.py
@pytest.mark.benchmark
def test_docling_pdf_performance(benchmark):
    parser = DoclingParser()
    benchmark(parser.parse, Path("tests/fixtures/large.pdf"))

    # Target: <5s for 10-page PDF
```

---

## Sprint 21 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Supported file types | 15+ | Parser count |
| Docling extraction quality | >90% text captured | Manual review |
| Code parsing accuracy | >95% | Function/class detection |
| Ingestion speed (PDF) | <5s (10 pages) | Benchmark |
| Ingestion speed (PPTX) | <10s (50 slides) | Benchmark |
| Test coverage | >80% | Coverage report |
| Parser error rate | <1% | Error logs |

---

## Dependencies

### New Libraries
```bash
# Core ingestion
poetry add docling                    # IBM document parser
poetry add python-frontmatter         # Markdown metadata

# Code parsing
poetry add tree-sitter tree-sitter-python tree-sitter-javascript

# Structured data
poetry add pandas openpyxl            # CSV/Excel (already installed)

# Email (standard library: email, mailbox - no install needed)
```

---

## Migration Strategy

### Backward Compatibility
```python
# scripts/index_one_doc_test.py (UPDATED)

# OLD: SimpleDirectoryReader
# loader = SimpleDirectoryReader(input_files=[str(test_file)])
# documents = loader.load_data()

# NEW: IngestionPipeline
from src.components.ingestion.pipeline import IngestionPipeline

pipeline = IngestionPipeline()
parsed_doc = pipeline.process_file(test_file)

# Convert to LlamaIndex Document format (for compatibility)
from llama_index.core import Document
document = Document(
    text=parsed_doc.content,
    metadata=parsed_doc.metadata,
    doc_id=parsed_doc.metadata.get('doc_id'),
)
```

### Gradual Rollout
1. **Phase 1** (Sprint 21): Implement parsers, test in isolation
2. **Phase 2** (Sprint 22): Integrate with indexing scripts
3. **Phase 3** (Sprint 23): Replace SimpleDirectoryReader system-wide
4. **Phase 4** (Sprint 24): Admin UI for document upload (uses pipeline)

---

## Documentation

### ADR-026: Unified Ingestion Pipeline
```markdown
# ADR-026: Unified Ingestion Pipeline with Docling

## Status
Accepted

## Context
Current document loading uses LlamaIndex SimpleDirectoryReader which has:
- Limited format support
- Poor table extraction
- No code parsing
- No email support

## Decision
Implement unified ingestion pipeline with:
- Docling for heavy documents (PDF, Office, HTML)
- Native parsers for simple formats (MD, TXT, JSON)
- Tree-sitter for code files
- Email parser for EML/MBOX
- Archive handler for ZIP/TAR

## Consequences
**Positive:**
- Better extraction quality (tables, layout)
- Support for 15+ file types
- Code structure metadata
- Unified API

**Negative:**
- Additional dependencies (docling, tree-sitter)
- Migration effort
- Performance overhead (Docling slower than SimpleDirectoryReader)

## Alternatives Considered
- Keep SimpleDirectoryReader (rejected - poor quality)
- Use LlamaParse (rejected - requires API key, not offline)
- Custom parsers for everything (rejected - high dev cost)
```

---

## Deployment Checklist

- [ ] All dependencies installed (docling, tree-sitter, frontmatter)
- [ ] Parsers tested with fixture documents
- [ ] Integration tests passing
- [ ] Performance benchmarks run
- [ ] ADR-026 documented
- [ ] Migration guide written
- [ ] Existing scripts updated
- [ ] Documentation updated (README, CLAUDE.md)

---

**Sprint 21 Completion:** Unified ingestion pipeline operational with 15+ supported formats
**Next Sprint:** Sprint 22 - Multi-tenancy & Projects (Auth moved here, with ingestion integrated into project uploads)
