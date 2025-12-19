"""Shared data models for ingestion nodes.

Sprint 54 Feature 54.1: Extracted from langgraph_nodes.py

These dataclasses define the core data structures used across
all ingestion pipeline nodes.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class SectionMetadata:
    """Section metadata extracted from Docling JSON (Feature 32.1).

    Represents a document section with hierarchical heading structure,
    bounding box coordinates, and token count for adaptive chunking.

    Attributes:
        heading: Section heading text (e.g., "Multi-Server Architecture")
        level: Heading level (1 = title, 2 = subtitle-level-1, 3 = subtitle-level-2)
        page_no: Page number where section starts
        bbox: Bounding box coordinates {"l": left, "t": top, "r": right, "b": bottom}
        text: Section body text (accumulated from cells)
        token_count: Number of tokens in section text
        metadata: Additional metadata (source, file_type, etc.)
    """

    heading: str
    level: int
    page_no: int
    bbox: dict[str, float]
    text: str
    token_count: int
    metadata: dict[str, Any]


@dataclass
class AdaptiveChunk:
    """Chunk with multi-section metadata (Feature 32.2).

    Created by adaptive_section_chunking() to merge small sections
    intelligently while preserving provenance chain.

    Attributes:
        text: Merged text from all sections
        token_count: Total tokens in chunk
        section_headings: List of all section headings in chunk
        section_pages: List of page numbers for each section
        section_bboxes: List of bounding boxes for each section
        primary_section: First section heading (main topic)
        metadata: Additional metadata (source, file_type, num_sections)
    """

    text: str
    token_count: int
    section_headings: list[str]
    section_pages: list[int]
    section_bboxes: list[dict[str, float]]
    primary_section: str
    metadata: dict[str, Any]
