"""Adaptive Chunking Strategy (Sprint 3, Feature 3.5).

This module provides document-type aware chunking strategies that optimize
chunk boundaries based on document structure. Different document types
benefit from different chunking approaches:

- PDFs/DOCX: Paragraph-based chunking (splits on double newlines)
- Markdown: Heading-based chunking (splits on # headers)
- Code files: Function-based chunking (splits on function definitions)
- Plain text: Sentence-based chunking (fallback)

This improves retrieval quality by preserving semantic units and avoiding
mid-sentence or mid-function splits.
"""

import re
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeRelationship, RelatedNodeInfo, TextNode

from src.core.config import settings

logger = structlog.get_logger(__name__)


class ChunkingStrategy(str, Enum):
    """Chunking strategy types for different document formats."""

    PARAGRAPH = "paragraph"  # Split on double newlines (PDF, DOCX)
    HEADING = "heading"  # Split on Markdown headers
    FUNCTION = "function"  # Split on function definitions (code)
    SENTENCE = "sentence"  # Default fallback (plain text)


class AdaptiveChunker:
    """Adaptive chunking that selects strategy based on document type.

    Document type detection uses file extension as primary signal,
    with content analysis as fallback for ambiguous cases.
    """

    def __init__(
        self,
        pdf_chunk_size: int | None = None,
        code_chunk_size: int | None = None,
        markdown_chunk_size: int | None = None,
        text_chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        """Initialize adaptive chunker with type-specific sizes.

        Args:
            pdf_chunk_size: Token limit for PDF/DOCX chunks (default: from settings)
            code_chunk_size: Token limit for code chunks (default: from settings)
            markdown_chunk_size: Token limit for Markdown chunks (default: from settings)
            text_chunk_size: Token limit for plain text chunks (default: from settings)
            chunk_overlap: Overlap between chunks in tokens (default: from settings)
        """
        self.pdf_chunk_size = pdf_chunk_size or settings.pdf_chunk_size
        self.code_chunk_size = code_chunk_size or settings.code_chunk_size
        self.markdown_chunk_size = markdown_chunk_size or settings.markdown_chunk_size
        self.text_chunk_size = text_chunk_size or settings.text_chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        # Fallback sentence splitter for when chunks are too large
        self._sentence_splitter = SentenceSplitter(
            chunk_size=self.text_chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        logger.info(
            "Adaptive chunker initialized",
            pdf_chunk_size=self.pdf_chunk_size,
            code_chunk_size=self.code_chunk_size,
            markdown_chunk_size=self.markdown_chunk_size,
            text_chunk_size=self.text_chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def detect_document_type(self, doc: Document) -> str:
        """Detect document type from extension and content.

        Detection hierarchy:
        1. File extension (primary signal)
        2. Content analysis (fallback)

        Args:
            doc: LlamaIndex Document object

        Returns:
            Document type string: 'pdf', 'markdown', 'code', or 'text'
        """
        # Extract file path/name from metadata
        file_path = doc.metadata.get("file_path", "")
        file_name = doc.metadata.get("file_name", "")
        source_path = file_path or file_name

        # Extension-based detection
        if source_path:
            path = Path(source_path)
            ext = path.suffix.lower()

            # PDF/DOCX documents
            if ext in {".pdf", ".docx", ".doc"}:
                return "pdf"

            # Markdown files
            if ext in {".md", ".markdown"}:
                return "markdown"

            # Code files
            if ext in {
                ".py",
                ".js",
                ".ts",
                ".java",
                ".cpp",
                ".c",
                ".go",
                ".rs",
                ".rb",
                ".php",
                ".cs",
                ".swift",
                ".kt",
            }:
                return "code"

            # Plain text
            if ext in {".txt", ".text"}:
                return "text"

        # Content-based fallback detection
        content = doc.get_content()[:1000]  # Sample first 1000 chars

        # Check for Markdown patterns (headers, links, code blocks)
        if re.search(r"^#{1,6}\s+.+$", content, re.MULTILINE):
            return "markdown"

        # Check for code patterns (function definitions, imports)
        code_patterns = [
            r"^def\s+\w+\s*\(",  # Python
            r"^function\s+\w+\s*\(",  # JavaScript
            r"^(public|private|protected)\s+\w+\s+\w+\s*\(",  # Java/C#
            r"^import\s+",  # Various languages
            r"^from\s+\w+\s+import\s+",  # Python
        ]
        if any(re.search(pattern, content, re.MULTILINE) for pattern in code_patterns):
            return "code"

        # Check for paragraph structure (PDF/DOCX often have this)
        if "\n\n" in content and len(content.split("\n\n")) > 2:
            return "pdf"

        # Default to plain text
        return "text"

    def select_strategy(self, doc_type: str) -> ChunkingStrategy:
        """Select chunking strategy based on document type.

        Args:
            doc_type: Document type string ('pdf', 'markdown', 'code', 'text')

        Returns:
            ChunkingStrategy enum value
        """
        strategy_map = {
            "pdf": ChunkingStrategy.PARAGRAPH,
            "markdown": ChunkingStrategy.HEADING,
            "code": ChunkingStrategy.FUNCTION,
            "text": ChunkingStrategy.SENTENCE,
        }

        strategy = strategy_map.get(doc_type, ChunkingStrategy.SENTENCE)
        logger.debug(
            "Strategy selected",
            doc_type=doc_type,
            strategy=strategy.value,
        )

        return strategy

    def chunk_by_paragraph(
        self,
        doc: Document,
        chunk_size: int,
    ) -> list[TextNode]:
        """Chunk document by paragraphs (double newlines).

        Args:
            doc: Document to chunk
            chunk_size: Maximum token size per chunk

        Returns:
            List of text nodes
        """
        content = doc.get_content()

        # Split on double newlines (paragraph boundaries)
        paragraphs = re.split(r"\n\n+", content)

        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        nodes: list[TextNode] = []
        current_chunk: list[str] = []
        current_size: int = 0

        for para in paragraphs:
            # Rough token estimate (1 token ≈ 4 chars)
            para_tokens = len(para) // 4

            # If single paragraph exceeds chunk size, split it with sentence splitter
            if para_tokens > chunk_size:
                # Flush current chunk first
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    nodes.append(self._create_node(doc, chunk_text, len(nodes)))
                    current_chunk = []
                    current_size = 0

                # Use sentence splitter for oversized paragraph
                para_doc = Document(
                    text=para,
                    metadata=doc.metadata,
                    doc_id=doc.doc_id,
                )
                para_nodes = self._sentence_splitter.get_nodes_from_documents([para_doc])
                for node in para_nodes:
                    nodes.append(self._create_node(doc, node.get_content(), len(nodes)))
                continue

            # Check if adding paragraph would exceed chunk size
            if current_size + para_tokens > chunk_size and current_chunk:
                # Create chunk from accumulated paragraphs
                chunk_text = "\n\n".join(current_chunk)
                nodes.append(self._create_node(doc, chunk_text, len(nodes)))
                current_chunk = []
                current_size = 0

            # Add paragraph to current chunk
            current_chunk.append(para)
            current_size += para_tokens

        # Flush remaining chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            nodes.append(self._create_node(doc, chunk_text, len(nodes)))

        logger.debug(
            "Paragraph chunking completed",
            paragraphs_count=len(paragraphs),
            chunks_created=len(nodes),
        )

        return nodes

    def chunk_by_heading(
        self,
        doc: Document,
        chunk_size: int,
    ) -> list[TextNode]:
        """Chunk Markdown document by headings.

        Args:
            doc: Document to chunk
            chunk_size: Maximum token size per chunk

        Returns:
            List of text nodes
        """
        content = doc.get_content()

        # Split on Markdown headers (# at line start)
        # Keep the header with the content
        sections = re.split(r"(^#{1,6}\s+.+$)", content, flags=re.MULTILINE)

        # Combine headers with following content
        chunks = []
        i = 0
        while i < len(sections):
            section = sections[i].strip()
            if not section:
                i += 1
                continue

            # If this is a header, combine with next section
            if re.match(r"^#{1,6}\s+", section):
                if i + 1 < len(sections):
                    chunks.append(section + "\n\n" + sections[i + 1].strip())
                    i += 2
                else:
                    chunks.append(section)
                    i += 1
            else:
                chunks.append(section)
                i += 1

        nodes: list[TextNode] = []
        for chunk in chunks:
            if not chunk.strip():
                continue

            # Check if chunk exceeds size
            chunk_tokens = len(chunk) // 4
            if chunk_tokens > chunk_size:
                # Use sentence splitter for oversized sections
                chunk_doc = Document(
                    text=chunk,
                    metadata=doc.metadata,
                    doc_id=doc.doc_id,
                )
                chunk_nodes = self._sentence_splitter.get_nodes_from_documents([chunk_doc])
                for node in chunk_nodes:
                    nodes.append(self._create_node(doc, node.get_content(), len(nodes)))
            else:
                nodes.append(self._create_node(doc, chunk, len(nodes)))

        logger.debug(
            "Heading chunking completed",
            sections_count=len(chunks),
            chunks_created=len(nodes),
        )

        return nodes

    def chunk_by_function(
        self,
        doc: Document,
        chunk_size: int,
    ) -> list[TextNode]:
        """Chunk code file by function definitions.

        Uses simple regex patterns to detect function boundaries.
        Supports Python, JavaScript, Java, C/C++, Go, and similar languages.

        Args:
            doc: Document to chunk
            chunk_size: Maximum token size per chunk

        Returns:
            List of text nodes
        """
        content = doc.get_content()

        # Function definition patterns for different languages
        patterns = [
            r"^def\s+\w+",  # Python
            r"^async\s+def\s+\w+",  # Python async
            r"^function\s+\w+",  # JavaScript
            r"^async\s+function\s+\w+",  # JavaScript async
            r"^(const|let|var)\s+\w+\s*=\s*(?:async\s+)?\(",  # JS arrow/const
            r"^(public|private|protected|static)\s+\w+\s+\w+\s*\(",  # Java/C#
            r"^func\s+\w+",  # Go
            r"^\w+\s+\w+\s*\([^)]*\)\s*\{",  # C/C++
        ]

        # Find all function starts
        function_starts = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if any(re.match(pattern, line.strip()) for pattern in patterns):
                function_starts.append(i)

        # If no functions found, fall back to sentence splitting
        if not function_starts:
            logger.debug("No functions detected, using sentence splitting")
            return self._sentence_splitter.get_nodes_from_documents([doc])

        # Split content by functions
        chunks: list[str] = []
        for i, start in enumerate(function_starts):
            end = function_starts[i + 1] if i + 1 < len(function_starts) else len(lines)
            function_lines = lines[start:end]
            chunks.append("\n".join(function_lines))

        # Add any content before first function
        if function_starts[0] > 0:
            preamble = "\n".join(lines[: function_starts[0]])
            if preamble.strip():
                chunks.insert(0, preamble)

        nodes: list[TextNode] = []
        for chunk in chunks:
            if not chunk.strip():
                continue

            # Check if chunk exceeds size
            chunk_tokens = len(chunk) // 4
            if chunk_tokens > chunk_size:
                # Split oversized function with sentence splitter
                chunk_doc = Document(
                    text=chunk,
                    metadata=doc.metadata,
                    doc_id=doc.doc_id,
                )
                chunk_nodes = self._sentence_splitter.get_nodes_from_documents([chunk_doc])
                for node in chunk_nodes:
                    nodes.append(self._create_node(doc, node.get_content(), len(nodes)))
            else:
                nodes.append(self._create_node(doc, chunk, len(nodes)))

        logger.debug(
            "Function chunking completed",
            functions_found=len(function_starts),
            chunks_created=len(nodes),
        )

        return nodes

    def chunk_by_sentence(
        self,
        doc: Document,
        chunk_size: int,
    ) -> list[TextNode]:
        """Chunk document by sentences using LlamaIndex SentenceSplitter.

        This is the fallback strategy for plain text documents.

        Args:
            doc: Document to chunk
            chunk_size: Maximum token size per chunk

        Returns:
            List of text nodes
        """
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        nodes = splitter.get_nodes_from_documents([doc])

        # Update chunk indices in metadata
        for i, node in enumerate(nodes):
            node.metadata["chunk_index"] = i

        logger.debug(
            "Sentence chunking completed",
            chunks_created=len(nodes),
        )

        return nodes

    def chunk_document(self, doc: Document) -> list[TextNode]:
        """Chunk a single document using adaptive strategy.

        Main entry point for adaptive chunking.

        Args:
            doc: Document to chunk

        Returns:
            List of text nodes
        """
        # Detect document type
        doc_type = self.detect_document_type(doc)

        # Select appropriate strategy
        strategy = self.select_strategy(doc_type)

        # Get chunk size for document type
        chunk_size_map = {
            "pdf": self.pdf_chunk_size,
            "markdown": self.markdown_chunk_size,
            "code": self.code_chunk_size,
            "text": self.text_chunk_size,
        }
        chunk_size = chunk_size_map.get(doc_type, self.text_chunk_size)

        logger.info(
            "Chunking document",
            doc_type=doc_type,
            strategy=strategy.value,
            chunk_size=chunk_size,
            source=doc.metadata.get("file_name", "unknown"),
        )

        # Apply appropriate chunking strategy
        if strategy == ChunkingStrategy.PARAGRAPH:
            return self.chunk_by_paragraph(doc, chunk_size)
        elif strategy == ChunkingStrategy.HEADING:
            return self.chunk_by_heading(doc, chunk_size)
        elif strategy == ChunkingStrategy.FUNCTION:
            return self.chunk_by_function(doc, chunk_size)
        else:  # SENTENCE
            return self.chunk_by_sentence(doc, chunk_size)

    def chunk_documents(self, documents: list[Document]) -> list[TextNode]:
        """Chunk multiple documents using adaptive strategies.

        Args:
            documents: List of documents to chunk

        Returns:
            List of all text nodes from all documents
        """
        all_nodes = []

        for doc in documents:
            nodes = self.chunk_document(doc)
            all_nodes.extend(nodes)

        logger.info(
            "Adaptive chunking completed",
            documents_count=len(documents),
            total_chunks=len(all_nodes),
            avg_chunks_per_doc=(round(len(all_nodes) / len(documents), 2) if documents else 0),
        )

        return all_nodes

    def _create_node(
        self,
        doc: Document,
        text: str,
        chunk_index: int,
    ) -> TextNode:
        """Create a TextNode with proper metadata.

        Args:
            doc: Original document
            text: Chunk text content
            chunk_index: Index of this chunk

        Returns:
            TextNode with metadata
        """
        return TextNode(
            text=text,
            metadata={
                **doc.metadata,
                "chunk_index": chunk_index,
            },
            id_=f"{doc.doc_id}_{chunk_index}",
            relationships={
                NodeRelationship.SOURCE: RelatedNodeInfo(node_id=doc.doc_id or "unknown")
            },
        )

    def get_chunker_info(self) -> dict[str, Any]:
        """Get information about chunker configuration.

        Returns:
            Dictionary with chunker settings
        """
        return {
            "pdf_chunk_size": self.pdf_chunk_size,
            "code_chunk_size": self.code_chunk_size,
            "markdown_chunk_size": self.markdown_chunk_size,
            "text_chunk_size": self.text_chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "strategies": {
                "pdf": ChunkingStrategy.PARAGRAPH.value,
                "markdown": ChunkingStrategy.HEADING.value,
                "code": ChunkingStrategy.FUNCTION.value,
                "text": ChunkingStrategy.SENTENCE.value,
            },
        }
