"""Section Extraction from Docling Documents (Sprint 32 Feature 32.1).

This module implements section hierarchy extraction from Docling DoclingDocument
objects. It parses document structure to identify section boundaries and extract
metadata (headings, pages, bounding boxes, text).

Used by: Adaptive Section-Aware Chunking (ADR-039)
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _get_heading_level(heading_type: str) -> int:
    """Map Docling heading type to hierarchy level.

    Docling JSON uses heading types from DocItemLabel:
    - "title" → Level 1 (main section, e.g., slide title in PowerPoint)
    - "subtitle-level-1" → Level 2 (subsection)
    - "subtitle-level-2" → Level 3 (sub-subsection)

    Args:
        heading_type: Docling heading type string

    Returns:
        int: Hierarchy level (1-3)

    Example:
        >>> _get_heading_level("title")
        1
        >>> _get_heading_level("subtitle-level-1")
        2
        >>> _get_heading_level("subtitle-level-2")
        3
    """
    heading_map = {
        "title": 1,
        "subtitle-level-1": 2,
        "subtitle-level-2": 3,
    }
    return heading_map.get(heading_type, 1)


def extract_section_hierarchy(
    docling_document: Any,
    section_metadata_class: type,
) -> list[Any]:
    """Extract section hierarchy from Docling DoclingDocument object (ADR-039).

    Parses DoclingDocument to identify section boundaries based on heading types.
    Accumulates body text for each section until next heading is encountered.

    This function is the foundation for Adaptive Section-Aware Chunking (ADR-039),
    which merges small sections intelligently while preserving large sections.

    DoclingDocument Structure:
        - document.body: Recursive tree of DocItem nodes
        - Each DocItem has .label (type) and .text (content)
        - Heading types: "title", "subtitle-level-1", "subtitle-level-2"
        - Body types: "text", "paragraph", "list_item", etc.
        - Provenance: .prov[0].page_no, .prov[0].bbox

    Args:
        docling_document: DoclingDocument object from Docling parser
        section_metadata_class: SectionMetadata dataclass type

    Returns:
        List[SectionMetadata]: Ordered list of sections with headings and text

    Raises:
        ValueError: If document is None or has no body structure

    Example:
        >>> from src.components.ingestion.langgraph_nodes import SectionMetadata
        >>> doc = await docling.parse_document("presentation.pptx")
        >>> sections = extract_section_hierarchy(doc, SectionMetadata)
        >>> sections[0]
        SectionMetadata(
            heading="Multi-Server Architecture",
            level=1,
            page_no=1,
            bbox={"l": 50, "t": 30, "r": 670, "b": 80},
            text="A multi-server architecture distributes...",
            token_count=245,
            metadata={"source": "presentation.pptx"}
        )
    """
    if docling_document is None:
        raise ValueError("docling_document is None - cannot extract sections")

    if not hasattr(docling_document, "body") or docling_document.body is None:
        logger.warning(
            "docling_document_no_body",
            doc_type=type(docling_document).__name__,
            has_body=hasattr(docling_document, "body"),
        )
        return []

    sections: list[Any] = []
    current_section: Any | None = None

    # Helper: Count tokens using BGE-M3 tokenizer (same as chunking_node)
    def count_tokens(text: str) -> int:
        """Count tokens using BGE-M3 tokenizer."""
        try:
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
            tokens = tokenizer.encode(text, add_special_tokens=False)
            return len(tokens)
        except Exception:
            # Fallback: approximate token count (avg 4 chars/token)
            return max(1, len(text) // 4)

    # Helper: Extract provenance (page_no, bbox) from DocItem
    def get_provenance(doc_item: Any) -> tuple[int | None, dict[str, float] | None]:
        """Extract page_no and bbox from DocItem.prov."""
        if not hasattr(doc_item, "prov") or not doc_item.prov:
            return None, None

        prov = doc_item.prov[0] if isinstance(doc_item.prov, list) else doc_item.prov

        page_no = getattr(prov, "page_no", None)

        bbox_obj = getattr(prov, "bbox", None)
        bbox = None
        if bbox_obj:
            bbox = {
                "l": getattr(bbox_obj, "l", 0.0),
                "t": getattr(bbox_obj, "t", 0.0),
                "r": getattr(bbox_obj, "r", 0.0),
                "b": getattr(bbox_obj, "b", 0.0),
            }

        return page_no, bbox

    # Helper: Recursively traverse document body tree
    def traverse_body(node: Any) -> None:
        """Recursively traverse DoclingDocument.body tree."""
        nonlocal current_section

        # Check if this node is a heading
        label = getattr(node, "label", None)
        if label and isinstance(label, str):
            label_str = label
        elif label and hasattr(label, "value"):
            label_str = label.value
        else:
            label_str = None

        is_heading = label_str in ["title", "subtitle-level-1", "subtitle-level-2"]

        if is_heading:
            # Save current section (if any)
            if current_section:
                sections.append(current_section)

            # Start new section
            page_no, bbox = get_provenance(node)
            heading_text = getattr(node, "text", "").strip()

            current_section = section_metadata_class(
                heading=heading_text,
                level=_get_heading_level(label_str),
                page_no=page_no or 0,
                bbox=bbox or {"l": 0.0, "t": 0.0, "r": 0.0, "b": 0.0},
                text="",
                token_count=0,
                metadata={},
            )

            logger.debug(
                "section_detected",
                heading=heading_text,
                level=current_section.level,
                page_no=page_no,
            )

        else:
            # Accumulate body text in current section
            if current_section:
                node_text = getattr(node, "text", "").strip()
                if node_text:
                    current_section.text += node_text + "\n\n"
                    current_section.token_count = count_tokens(current_section.text)

        # Recurse into children (if any)
        if hasattr(node, "children") and node.children:
            for child in node.children:
                traverse_body(child)

    # Start traversal from document.body
    traverse_body(docling_document.body)

    # Don't forget last section
    if current_section:
        sections.append(current_section)

    logger.info(
        "section_extraction_complete",
        total_sections=len(sections),
        sections_with_text=sum(1 for s in sections if s.text.strip()),
        avg_tokens_per_section=(
            round(sum(s.token_count for s in sections) / len(sections), 1) if sections else 0
        ),
    )

    return sections
