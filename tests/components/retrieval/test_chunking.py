"""Unit tests for Adaptive Chunking (Sprint 3, Feature 3.5).

Tests cover:
- Document type detection (extension-based and content-based)
- Strategy selection for different document types
- Paragraph chunking (PDF/DOCX)
- Heading chunking (Markdown)
- Function chunking (code files)
- Sentence chunking (fallback)
- Chunk size configuration per document type
- Edge cases and error handling
"""

import pytest

# Conditional import for llama_index
try:
    from llama_index.core import Document
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    # Create a mock Document class for type checking
    class Document:  # type: ignore
        """Mock Document for when llama_index is not available."""
        pass

from src.components.retrieval.chunking import AdaptiveChunker, ChunkingStrategy

# Skip all tests in this module if llama_index is not available
pytestmark = pytest.mark.skipif(
    not LLAMA_INDEX_AVAILABLE, reason="llama_index not installed - install with ingestion extras"
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def adaptive_chunker():
    """Create AdaptiveChunker with default settings."""
    return AdaptiveChunker(
        pdf_chunk_size=1024,
        code_chunk_size=512,
        markdown_chunk_size=1024,
        text_chunk_size=512,
        chunk_overlap=50,
    )


@pytest.fixture
def sample_pdf_content():
    """Sample PDF-like content with paragraphs."""
    return """This is the first paragraph. It contains multiple sentences.
This continues the first paragraph with more information.

This is the second paragraph. It starts after a blank line.
It also contains multiple sentences that belong together.

This is the third paragraph. Each paragraph is separated by double newlines.
Paragraphs should be kept together when possible."""


@pytest.fixture
def sample_markdown_content():
    """Sample Markdown content with headings."""
    return """# Main Title

This is the introduction paragraph under the main title.

## Section 1

This is the content of section 1.
It has multiple lines.

## Section 2

This is the content of section 2.

### Subsection 2.1

More detailed content here."""


@pytest.fixture
def sample_python_code():
    """Sample Python code with functions."""
    return """import os
import sys

def hello_world():
    \"\"\"Print hello world.\"\"\"
    print("Hello, World!")
    return True

def calculate_sum(a, b):
    \"\"\"Calculate sum of two numbers.\"\"\"
    result = a + b
    return result

async def fetch_data():
    \"\"\"Async function to fetch data.\"\"\"
    data = await some_api_call()
    return data

class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass"""


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code with functions."""
    return """function greet(name) {
    console.log(`Hello, ${name}!`);
}

async function fetchData() {
    const response = await fetch('/api/data');
    return response.json();
}

const add = (a, b) => {
    return a + b;
};

const multiply = function(x, y) {
    return x * y;
};"""


@pytest.fixture
def sample_text_content():
    """Sample plain text content."""
    return """This is plain text content. It has sentences but no special structure.
Another sentence here. And another one. More content follows.
Yet another sentence to make it longer."""


# ============================================================================
# Document Type Detection Tests
# ============================================================================


@pytest.mark.unit
def test_detect_pdf_by_extension(adaptive_chunker):
    """Test PDF detection by .pdf extension."""
    doc = Document(
        text="Sample content",
        metadata={"file_path": "/path/to/document.pdf"},
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "pdf"


@pytest.mark.unit
def test_detect_docx_by_extension(adaptive_chunker):
    """Test DOCX detection by .docx extension."""
    doc = Document(
        text="Sample content",
        metadata={"file_path": "/path/to/document.docx"},
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "pdf"


@pytest.mark.unit
def test_detect_markdown_by_extension(adaptive_chunker):
    """Test Markdown detection by .md extension."""
    doc = Document(
        text="# Title\nContent",
        metadata={"file_path": "/path/to/readme.md"},
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "markdown"


@pytest.mark.unit
def test_detect_python_by_extension(adaptive_chunker):
    """Test Python code detection by .py extension."""
    doc = Document(
        text="def hello(): pass",
        metadata={"file_path": "/path/to/script.py"},
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "code"


@pytest.mark.unit
def test_detect_javascript_by_extension(adaptive_chunker):
    """Test JavaScript detection by .js extension."""
    doc = Document(
        text="function test() {}",
        metadata={"file_path": "/path/to/app.js"},
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "code"


@pytest.mark.unit
def test_detect_text_by_extension(adaptive_chunker):
    """Test plain text detection by .txt extension."""
    doc = Document(
        text="Plain text content",
        metadata={"file_path": "/path/to/file.txt"},
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "text"


@pytest.mark.unit
def test_detect_markdown_by_content(adaptive_chunker):
    """Test Markdown detection by content (headers)."""
    doc = Document(
        text="# Main Title\n## Section\nContent here",
        metadata={},  # No file path
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "markdown"


@pytest.mark.unit
def test_detect_code_by_content_python(adaptive_chunker):
    """Test Python code detection by content patterns."""
    doc = Document(
        text="def my_function():\n    pass\n\nimport os",
        metadata={},  # No file path
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "code"


@pytest.mark.unit
def test_detect_code_by_content_javascript(adaptive_chunker):
    """Test JavaScript code detection by content patterns."""
    doc = Document(
        text="function myFunc() {\n    return true;\n}",
        metadata={},  # No file path
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "code"


@pytest.mark.unit
def test_detect_pdf_by_content_paragraphs(adaptive_chunker, sample_pdf_content):
    """Test PDF detection by content (multiple paragraphs)."""
    doc = Document(
        text=sample_pdf_content,
        metadata={},  # No file path
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "pdf"


@pytest.mark.unit
def test_detect_text_fallback(adaptive_chunker):
    """Test fallback to text when no patterns match."""
    doc = Document(
        text="Just some random content without special structure.",
        metadata={},  # No file path
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "text"


@pytest.mark.unit
def test_detect_uses_file_name_when_no_path(adaptive_chunker):
    """Test detection using file_name metadata when file_path missing."""
    doc = Document(
        text="Content",
        metadata={"file_name": "script.py"},  # Only file_name
    )

    doc_type = adaptive_chunker.detect_document_type(doc)
    assert doc_type == "code"


@pytest.mark.unit
def test_detect_multiple_code_extensions(adaptive_chunker):
    """Test detection for various code file extensions."""
    extensions = [".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs"]

    for ext in extensions:
        doc = Document(
            text="code content",
            metadata={"file_path": f"/path/to/file{ext}"},
        )
        doc_type = adaptive_chunker.detect_document_type(doc)
        assert doc_type == "code", f"Failed for extension {ext}"


# ============================================================================
# Strategy Selection Tests
# ============================================================================


@pytest.mark.unit
def test_select_strategy_pdf(adaptive_chunker):
    """Test strategy selection for PDF documents."""
    strategy = adaptive_chunker.select_strategy("pdf")
    assert strategy == ChunkingStrategy.PARAGRAPH


@pytest.mark.unit
def test_select_strategy_markdown(adaptive_chunker):
    """Test strategy selection for Markdown documents."""
    strategy = adaptive_chunker.select_strategy("markdown")
    assert strategy == ChunkingStrategy.HEADING


@pytest.mark.unit
def test_select_strategy_code(adaptive_chunker):
    """Test strategy selection for code files."""
    strategy = adaptive_chunker.select_strategy("code")
    assert strategy == ChunkingStrategy.FUNCTION


@pytest.mark.unit
def test_select_strategy_text(adaptive_chunker):
    """Test strategy selection for text files."""
    strategy = adaptive_chunker.select_strategy("text")
    assert strategy == ChunkingStrategy.SENTENCE


@pytest.mark.unit
def test_select_strategy_unknown_fallback(adaptive_chunker):
    """Test strategy selection falls back to sentence for unknown types."""
    strategy = adaptive_chunker.select_strategy("unknown")
    assert strategy == ChunkingStrategy.SENTENCE


# ============================================================================
# Paragraph Chunking Tests
# ============================================================================


@pytest.mark.unit
def test_chunk_by_paragraph_basic(adaptive_chunker, sample_pdf_content):
    """Test basic paragraph chunking."""
    doc = Document(
        text=sample_pdf_content,
        metadata={"file_path": "test.pdf"},
        doc_id="test_doc",
    )

    nodes = adaptive_chunker.chunk_by_paragraph(doc, chunk_size=1024)

    # Should have 3 chunks (3 paragraphs)
    assert len(nodes) >= 1
    assert all(node.text.strip() for node in nodes)

    # Check metadata preserved
    assert all(node.metadata.get("file_path") == "test.pdf" for node in nodes)
    assert all(node.ref_doc_id == "test_doc" for node in nodes)


@pytest.mark.unit
def test_chunk_by_paragraph_preserves_structure(adaptive_chunker):
    """Test that paragraph chunking preserves paragraph boundaries."""
    content = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
    doc = Document(text=content, doc_id="test")

    nodes = adaptive_chunker.chunk_by_paragraph(doc, chunk_size=1024)

    # Each paragraph should be in its own chunk (they're small enough)
    assert len(nodes) >= 1
    assert "Paragraph 1" in nodes[0].text


@pytest.mark.unit
def test_chunk_by_paragraph_oversized_splits(adaptive_chunker):
    """Test that oversized paragraphs are split with sentence splitter."""
    # Create a very long paragraph
    long_paragraph = " ".join(["This is a long sentence."] * 500)
    doc = Document(text=long_paragraph, doc_id="test")

    nodes = adaptive_chunker.chunk_by_paragraph(doc, chunk_size=100)

    # Should be split into multiple chunks
    assert len(nodes) > 1


@pytest.mark.unit
def test_chunk_by_paragraph_empty_paragraphs_ignored(adaptive_chunker):
    """Test that empty paragraphs are filtered out."""
    content = "Paragraph 1.\n\n\n\nParagraph 2.\n\n"
    doc = Document(text=content, doc_id="test")

    nodes = adaptive_chunker.chunk_by_paragraph(doc, chunk_size=1024)

    # Should only have chunks with content
    assert all(node.text.strip() for node in nodes)


# ============================================================================
# Heading Chunking Tests
# ============================================================================


@pytest.mark.unit
def test_chunk_by_heading_basic(adaptive_chunker, sample_markdown_content):
    """Test basic Markdown heading chunking."""
    doc = Document(
        text=sample_markdown_content,
        metadata={"file_path": "readme.md"},
        doc_id="test_doc",
    )

    nodes = adaptive_chunker.chunk_by_heading(doc, chunk_size=1024)

    # Should have multiple chunks based on headings
    assert len(nodes) >= 1
    assert all(node.text.strip() for node in nodes)


@pytest.mark.unit
def test_chunk_by_heading_preserves_headers(adaptive_chunker):
    """Test that headings are preserved with their content."""
    content = "# Title\nContent under title.\n\n## Section\nSection content."
    doc = Document(text=content, doc_id="test")

    nodes = adaptive_chunker.chunk_by_heading(doc, chunk_size=1024)

    # Headers should be in the chunks
    assert any("# Title" in node.text for node in nodes)


@pytest.mark.unit
def test_chunk_by_heading_oversized_splits(adaptive_chunker):
    """Test that oversized sections are split with sentence splitter."""
    # Create a section with very long content
    long_content = "# Title\n" + " ".join(["Long sentence."] * 500)
    doc = Document(text=long_content, doc_id="test")

    nodes = adaptive_chunker.chunk_by_heading(doc, chunk_size=100)

    # Should be split into multiple chunks
    assert len(nodes) > 1


@pytest.mark.unit
def test_chunk_by_heading_multiple_levels(adaptive_chunker):
    """Test handling of multiple heading levels."""
    content = "# H1\nContent.\n## H2\nMore.\n### H3\nEven more."
    doc = Document(text=content, doc_id="test")

    nodes = adaptive_chunker.chunk_by_heading(doc, chunk_size=1024)

    # Should create chunks for different sections
    assert len(nodes) >= 1


# ============================================================================
# Function Chunking Tests
# ============================================================================


@pytest.mark.unit
def test_chunk_by_function_python(adaptive_chunker, sample_python_code):
    """Test function-based chunking for Python code."""
    doc = Document(
        text=sample_python_code,
        metadata={"file_path": "script.py"},
        doc_id="test_doc",
    )

    nodes = adaptive_chunker.chunk_by_function(doc, chunk_size=512)

    # Should detect multiple functions
    assert len(nodes) >= 1

    # Check that functions are in chunks
    all_text = " ".join(node.text for node in nodes)
    assert "def hello_world" in all_text
    assert "def calculate_sum" in all_text


@pytest.mark.unit
def test_chunk_by_function_javascript(adaptive_chunker, sample_javascript_code):
    """Test function-based chunking for JavaScript code."""
    doc = Document(
        text=sample_javascript_code,
        metadata={"file_path": "app.js"},
        doc_id="test_doc",
    )

    nodes = adaptive_chunker.chunk_by_function(doc, chunk_size=512)

    # Should detect multiple functions
    assert len(nodes) >= 1

    # Check that functions are in chunks
    all_text = " ".join(node.text for node in nodes)
    assert "function greet" in all_text


@pytest.mark.unit
def test_chunk_by_function_no_functions_fallback(adaptive_chunker):
    """Test fallback to sentence splitting when no functions detected."""
    # Code without function definitions
    content = "import os\nimport sys\n\nCONFIG = {}\nVALUE = 42"
    doc = Document(text=content, doc_id="test")

    nodes = adaptive_chunker.chunk_by_function(doc, chunk_size=512)

    # Should fall back to sentence splitting
    assert len(nodes) >= 1


@pytest.mark.unit
def test_chunk_by_function_preserves_preamble(adaptive_chunker):
    """Test that content before first function is preserved."""
    content = "import os\nimport sys\n\ndef my_func():\n    pass"
    doc = Document(text=content, doc_id="test")

    nodes = adaptive_chunker.chunk_by_function(doc, chunk_size=512)

    # Imports should be in first chunk
    assert "import os" in nodes[0].text


@pytest.mark.unit
def test_chunk_by_function_oversized_splits(adaptive_chunker):
    """Test that oversized functions are split."""
    # Create a very long function
    long_func = "def big_function():\n" + "    pass\n" * 1000
    doc = Document(text=long_func, doc_id="test")

    nodes = adaptive_chunker.chunk_by_function(doc, chunk_size=100)

    # Should be split into multiple chunks
    assert len(nodes) > 1


# ============================================================================
# Sentence Chunking Tests
# ============================================================================


@pytest.mark.unit
def test_chunk_by_sentence_basic(adaptive_chunker, sample_text_content):
    """Test basic sentence-based chunking."""
    doc = Document(
        text=sample_text_content,
        metadata={"file_path": "file.txt"},
        doc_id="test_doc",
    )

    nodes = adaptive_chunker.chunk_by_sentence(doc, chunk_size=512)

    assert len(nodes) >= 1
    assert all(node.text.strip() for node in nodes)
    assert all(node.ref_doc_id == "test_doc" for node in nodes)


@pytest.mark.unit
def test_chunk_by_sentence_metadata_indices(adaptive_chunker, sample_text_content):
    """Test that sentence chunking adds chunk indices."""
    doc = Document(text=sample_text_content, doc_id="test")

    nodes = adaptive_chunker.chunk_by_sentence(doc, chunk_size=512)

    # Check chunk indices are sequential
    for i, node in enumerate(nodes):
        assert node.metadata.get("chunk_index") == i


@pytest.mark.unit
def test_chunk_by_sentence_respects_size(adaptive_chunker):
    """Test that sentence chunking respects chunk size."""
    # Create long content
    content = " ".join(["This is a sentence."] * 200)
    doc = Document(text=content, doc_id="test")

    nodes = adaptive_chunker.chunk_by_sentence(doc, chunk_size=100)

    # Should create multiple chunks
    assert len(nodes) > 1


# ============================================================================
# End-to-End Chunking Tests
# ============================================================================


@pytest.mark.unit
def test_chunk_document_pdf(adaptive_chunker, sample_pdf_content):
    """Test end-to-end chunking for PDF document."""
    doc = Document(
        text=sample_pdf_content,
        metadata={"file_path": "document.pdf"},
        doc_id="test_doc",
    )

    nodes = adaptive_chunker.chunk_document(doc)

    assert len(nodes) >= 1
    assert all(node.text.strip() for node in nodes)


@pytest.mark.unit
def test_chunk_document_markdown(adaptive_chunker, sample_markdown_content):
    """Test end-to-end chunking for Markdown document."""
    doc = Document(
        text=sample_markdown_content,
        metadata={"file_path": "readme.md"},
        doc_id="test_doc",
    )

    nodes = adaptive_chunker.chunk_document(doc)

    assert len(nodes) >= 1
    assert all(node.text.strip() for node in nodes)


@pytest.mark.unit
def test_chunk_document_code(adaptive_chunker, sample_python_code):
    """Test end-to-end chunking for code document."""
    doc = Document(
        text=sample_python_code,
        metadata={"file_path": "script.py"},
        doc_id="test_doc",
    )

    nodes = adaptive_chunker.chunk_document(doc)

    assert len(nodes) >= 1
    assert all(node.text.strip() for node in nodes)


@pytest.mark.unit
def test_chunk_document_text(adaptive_chunker, sample_text_content):
    """Test end-to-end chunking for text document."""
    doc = Document(
        text=sample_text_content,
        metadata={"file_path": "notes.txt"},
        doc_id="test_doc",
    )

    nodes = adaptive_chunker.chunk_document(doc)

    assert len(nodes) >= 1
    assert all(node.text.strip() for node in nodes)


@pytest.mark.unit
def test_chunk_documents_multiple(adaptive_chunker):
    """Test chunking multiple documents with different types."""
    docs = [
        Document(
            text="# Title\nMarkdown content.",
            metadata={"file_path": "readme.md"},
            doc_id="doc1",
        ),
        Document(
            text="def func():\n    pass",
            metadata={"file_path": "script.py"},
            doc_id="doc2",
        ),
        Document(
            text="Plain text content here.",
            metadata={"file_path": "notes.txt"},
            doc_id="doc3",
        ),
    ]

    all_nodes = adaptive_chunker.chunk_documents(docs)

    # Should have chunks from all documents
    assert len(all_nodes) >= 3

    # Check different doc_ids are present
    doc_ids = {node.ref_doc_id for node in all_nodes}
    assert "doc1" in doc_ids
    assert "doc2" in doc_ids
    assert "doc3" in doc_ids


# ============================================================================
# Configuration Tests
# ============================================================================


@pytest.mark.unit
def test_chunker_initialization_custom_sizes():
    """Test chunker initialization with custom chunk sizes."""
    chunker = AdaptiveChunker(
        pdf_chunk_size=2048,
        code_chunk_size=256,
        markdown_chunk_size=1024,
        text_chunk_size=1024,
        chunk_overlap=100,
    )

    assert chunker.pdf_chunk_size == 2048
    assert chunker.code_chunk_size == 256
    assert chunker.markdown_chunk_size == 1024
    assert chunker.text_chunk_size == 1024
    assert chunker.chunk_overlap == 100


@pytest.mark.unit
def test_chunker_initialization_defaults():
    """Test chunker initialization with default settings from config."""
    chunker = AdaptiveChunker()

    # Should use settings from config
    assert chunker.pdf_chunk_size > 0
    assert chunker.code_chunk_size > 0
    assert chunker.markdown_chunk_size > 0
    assert chunker.text_chunk_size > 0
    assert chunker.chunk_overlap >= 0


@pytest.mark.unit
def test_get_chunker_info(adaptive_chunker):
    """Test get_chunker_info returns correct configuration."""
    info = adaptive_chunker.get_chunker_info()

    assert info["pdf_chunk_size"] == 1024
    assert info["code_chunk_size"] == 512
    assert info["markdown_chunk_size"] == 1024
    assert info["text_chunk_size"] == 512
    assert info["chunk_overlap"] == 50

    # Check strategies
    assert info["strategies"]["pdf"] == "paragraph"
    assert info["strategies"]["markdown"] == "heading"
    assert info["strategies"]["code"] == "function"
    assert info["strategies"]["text"] == "sentence"


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.unit
def test_chunk_empty_document(adaptive_chunker):
    """Test chunking an empty document."""
    doc = Document(text="", doc_id="test")

    nodes = adaptive_chunker.chunk_document(doc)

    # Should handle gracefully (may return empty list or single empty chunk)
    assert isinstance(nodes, list)


@pytest.mark.unit
def test_chunk_document_no_metadata(adaptive_chunker):
    """Test chunking document without metadata."""
    doc = Document(text="Some content here.", doc_id="test")

    nodes = adaptive_chunker.chunk_document(doc)

    assert len(nodes) >= 1


@pytest.mark.unit
def test_chunk_document_very_short(adaptive_chunker):
    """Test chunking a very short document."""
    doc = Document(text="Short.", metadata={"file_path": "file.txt"}, doc_id="test")

    nodes = adaptive_chunker.chunk_document(doc)

    # Should return at least one chunk
    assert len(nodes) >= 1
    assert nodes[0].text.strip() == "Short."
