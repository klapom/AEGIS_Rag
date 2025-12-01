"""Section Extraction from Docling Documents (Sprint 32 Feature 32.1).

This module implements section hierarchy extraction from Docling DoclingDocument
objects. It parses document structure to identify section boundaries and extract
metadata (headings, pages, bounding boxes, text).

Used by: Adaptive Section-Aware Chunking (ADR-039)

=============================================================================
IMPORTANT: Docling JSON Structure (Sprint 33 - TD-044 Discovery)
=============================================================================

The Docling HTTP API returns JSON with a specific structure that differs from
native DoclingDocument objects. Understanding this is CRITICAL for section extraction.

Docling JSON Structure (from HTTP API):
```json
{
  "body": {
    "children": [{"$ref": "#/groups/0"}, {"$ref": "#/groups/1"}, ...]
  },
  "groups": [
    {"label": "chapter", "name": "slide-0", "children": [{"$ref": "#/texts/0"}, ...]},
    ...
  ],
  "texts": [
    {"label": "title", "text": "Slide Title", "prov": [{"page_no": 1, "bbox": {...}}]},
    {"label": "paragraph", "text": "Body text...", "prov": [...]},
    {"label": "list_item", "text": "Bullet point", "prov": [...]},
    ...
  ],
  "pictures": [...],
  "tables": [...],
  "pages": {"1": {"page_no": 1, "size": {"width": 612, "height": 792}}, ...}
}
```

KEY INSIGHT (TD-044):
- `body.children` contains ONLY JSON References ($ref) - NOT the actual content!
- The actual text content with labels is in the `texts` array
- `groups` are containers (slides/chapters) that reference texts via $ref
- Traversing `body.children` yields no labels/text because they're just $ref pointers

Label Types in `texts`:
- "title" → Slide/Section title (Level 1)
- "subtitle-level-1" → Subsection (Level 2)
- "subtitle-level-2" → Sub-subsection (Level 3)
- "paragraph" → Body text
- "list_item" → Bullet points
- "text" → Generic text

IMPORTANT: DOCX documents from Docling do NOT have "title" labels!
- DOCX only has: paragraph, list_item, text
- PPTX has: title, paragraph, list_item, text
- For DOCX: We detect headings via formatting.bold + heuristics (Sprint 33)

This module handles THREE extraction strategies:
1. PPTX/PDF: Use `texts` array with title labels (PRIMARY)
2. DOCX: Use formatting-based heading detection (bold + short text)
3. Native DoclingDocument objects (via `body` tree traversal - legacy)

References:
- Docling Documentation: https://docling-project.github.io/docling/concepts/docling_document/
- JSON Schema: https://github.com/docling-project/docling-core/blob/main/docs/DoclingDocument.json
- TD-044: docs/technical-debt/TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md
=============================================================================
"""

import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _safe_log_text(text: str, max_len: int = 50) -> str:
    """Make text safe for Windows console logging (CP1252 compatible).

    Windows console uses CP1252 encoding which cannot display many Unicode characters.
    This function replaces problematic characters with ASCII equivalents.

    Args:
        text: Text to sanitize
        max_len: Maximum length to return

    Returns:
        Sanitized text safe for console output
    """
    if not text:
        return ""
    # Truncate first
    truncated = text[:max_len]
    # Replace problematic Unicode with ASCII equivalents
    try:
        # Try to encode to cp1252 - if it fails, we need to sanitize
        truncated.encode("cp1252")
        return truncated
    except UnicodeEncodeError:
        # Replace characters that can't be encoded
        safe_text = truncated.encode("cp1252", errors="replace").decode("cp1252")
        return safe_text


def _is_likely_heading_by_formatting(text_item: dict[str, Any]) -> bool:
    """Detect if a text item is likely a heading based on formatting (DOCX fallback).

    DOCX documents don't have "title" labels - all text is labeled as "paragraph".
    However, the `formatting` field provides valuable information:
    - Bold text + short length → likely a heading
    - Bold text + no period at end → likely a heading

    This is used as a FALLBACK when no explicit title labels are found.

    Args:
        text_item: Text item from texts array with potential formatting field

    Returns:
        bool: True if the item looks like a heading based on formatting
    """
    text = text_item.get("text", "").strip()
    label = text_item.get("label", "")
    formatting = text_item.get("formatting")

    # Only consider paragraphs for heading detection
    if label != "paragraph":
        return False

    # Must have text content
    if not text or len(text) < 3:
        return False

    # Check formatting
    is_bold = False
    if formatting and isinstance(formatting, dict):
        is_bold = formatting.get("bold", False)

    # Heuristics for heading detection
    is_short = len(text) < 120  # Headings are typically short
    no_period = not text.rstrip().endswith(".")  # Headings don't end with period
    starts_upper = text[0].isupper() if text else False  # Headings start with capital
    no_bullet = not text.startswith(("-", "*", "•", "→"))  # Not a bullet point

    # Primary criterion: Bold + Short
    if is_bold and is_short and no_period:
        return True

    # Secondary criterion: Very short uppercase text (likely title)
    if len(text) < 60 and text.isupper() and no_period:
        return True

    # Tertiary criterion: Short paragraph with section keywords
    section_keywords = [
        "kapitel", "abschnitt", "teil", "section", "chapter",
        "overview", "introduction", "zusammenfassung", "fazit",
        "anhang", "appendix", "inhaltsverzeichnis", "agenda",
    ]
    if is_short and no_period and starts_upper and no_bullet:
        text_lower = text.lower()
        if any(kw in text_lower for kw in section_keywords):
            return True

    return False


def _detect_heading_strategy(texts: list[dict[str, Any]]) -> str:
    """Detect which heading extraction strategy to use.

    Args:
        texts: List of text items from json_content["texts"]

    Returns:
        str: "labels" if explicit title labels exist, "formatting" if DOCX-style
    """
    # Full list of Docling heading labels (from DocItemLabel enum):
    # - "title" → Document title / Slide title (PPTX)
    # - "section_header" → Word heading styles (Heading 1, 2, etc.) with level attribute
    # - "subtitle-level-1", "subtitle-level-2" → PowerPoint subtitles
    HEADING_LABELS = {"title", "section_header", "subtitle-level-1", "subtitle-level-2"}

    label_headings = sum(
        1 for t in texts
        if t.get("label", "") in HEADING_LABELS
    )

    formatting_headings = sum(
        1 for t in texts
        if _is_likely_heading_by_formatting(t)
    )

    # If we have explicit title labels, use them
    if label_headings > 0:
        return "labels"

    # If we have formatting-based headings, use those
    if formatting_headings > 0:
        return "formatting"

    # No headings found - will create single section
    return "none"


def _get_heading_level(heading_type: str, text_item: dict[str, Any] | None = None) -> int:
    """Map Docling heading type to hierarchy level.

    Docling JSON uses heading types from DocItemLabel:
    - "title" → Level 1 (main section, e.g., slide title in PowerPoint)
    - "section_header" → Level from item's "level" attribute (Word Heading 1, 2, etc.)
    - "subtitle-level-1" → Level 2 (subsection)
    - "subtitle-level-2" → Level 3 (sub-subsection)

    Args:
        heading_type: Docling heading type string
        text_item: Optional text item dict to extract level attribute for section_header

    Returns:
        int: Hierarchy level (1-3)

    Example:
        >>> _get_heading_level("title")
        1
        >>> _get_heading_level("section_header", {"level": 2})
        2
        >>> _get_heading_level("subtitle-level-1")
        2
    """
    # For section_header, use the item's level attribute if available
    # This corresponds to Word's Heading 1, Heading 2, etc.
    if heading_type == "section_header" and text_item:
        level = text_item.get("level")
        if level and isinstance(level, int) and 1 <= level <= 6:
            return level
        # Default to level 1 if level attribute is missing
        return 1

    heading_map = {
        "title": 1,
        "section_header": 1,  # Default if no level attribute
        "subtitle-level-1": 2,
        "subtitle-level-2": 3,
    }
    return heading_map.get(heading_type, 1)


def _extract_from_texts_array(
    texts: list[dict[str, Any]],
    section_metadata_class: type,
    count_tokens_func: callable,
) -> list[Any]:
    """Extract sections from Docling JSON `texts` array (Sprint 33 - TD-044 Fix).

    This is the PRIMARY extraction method for HTTP API responses.
    The `texts` array contains all text items with their labels directly accessible.

    JSON Structure of each text item:
    ```json
    {
      "self_ref": "#/texts/0",
      "parent": {"$ref": "#/groups/0"},
      "label": "title",           // <-- The key field for section detection!
      "text": "Slide Title",      // <-- The actual text content
      "prov": [{
        "page_no": 1,
        "bbox": {"l": 100, "t": 200, "r": 500, "b": 250, "coord_origin": "BOTTOMLEFT"}
      }],
      "formatting": {"bold": true, "italic": false, ...}  // DOCX only!
    }
    ```

    Extraction Strategies:
    1. PPTX/PDF: Use explicit "title"/"subtitle-level-*" labels
    2. DOCX: Use formatting.bold + heuristics (no title labels available)

    Algorithm:
    1. Detect heading strategy (labels vs. formatting)
    2. Iterate through `texts` array in order (preserves document flow)
    3. When heading detected → Start new section
    4. When content detected → Add to current section
    5. Extract page_no and bbox from prov array

    Args:
        texts: List of text items from json_content["texts"]
        section_metadata_class: SectionMetadata dataclass type
        count_tokens_func: Function to count tokens in text

    Returns:
        List of SectionMetadata objects
    """
    sections: list[Any] = []
    current_section: Any | None = None
    texts_processed = 0

    # Detect which heading strategy to use
    heading_strategy = _detect_heading_strategy(texts)

    logger.info(
        "heading_strategy_detected",
        strategy=heading_strategy,
        texts_count=len(texts),
    )

    # Heading labels that start new sections (for label-based strategy)
    # Includes section_header for DOCX with proper Word heading styles
    HEADING_LABELS = {"title", "section_header", "subtitle-level-1", "subtitle-level-2"}

    # Content labels to accumulate in sections
    CONTENT_LABELS = {"paragraph", "list_item", "text"}

    for text_item in texts:
        texts_processed += 1
        label = text_item.get("label", "")
        text_content = text_item.get("text", "").strip()

        # Extract provenance (page number and bounding box)
        page_no = None
        bbox = None
        prov = text_item.get("prov", [])
        if prov and isinstance(prov, list) and len(prov) > 0:
            first_prov = prov[0]
            if isinstance(first_prov, dict):
                page_no = first_prov.get("page_no")
                bbox_data = first_prov.get("bbox")
                if bbox_data and isinstance(bbox_data, dict):
                    bbox = {
                        "l": bbox_data.get("l", 0.0),
                        "t": bbox_data.get("t", 0.0),
                        "r": bbox_data.get("r", 0.0),
                        "b": bbox_data.get("b", 0.0),
                    }

        # Determine if this item is a heading
        is_heading = False
        if heading_strategy == "labels":
            # PPTX/PDF: Use explicit labels
            is_heading = label in HEADING_LABELS
        elif heading_strategy == "formatting":
            # DOCX: Use formatting-based detection
            is_heading = _is_likely_heading_by_formatting(text_item)

        if is_heading:
            # Save current section (if any) before starting new one
            if current_section:
                sections.append(current_section)

            # Start new section with this heading
            # Pass text_item for section_header to extract level attribute
            current_section = section_metadata_class(
                heading=text_content,
                level=_get_heading_level(label, text_item) if label in HEADING_LABELS else 1,
                page_no=page_no or 0,
                bbox=bbox or {"l": 0.0, "t": 0.0, "r": 0.0, "b": 0.0},
                text="",
                token_count=0,
                metadata={"heading_source": heading_strategy},
            )

            logger.debug(
                "section_detected_from_texts",
                heading=_safe_log_text(text_content, 50),
                level=current_section.level,
                page_no=page_no,
                label=label,
                strategy=heading_strategy,
            )

        elif label in CONTENT_LABELS and text_content:
            # Accumulate content in current section
            if current_section:
                current_section.text += text_content + "\n\n"
                current_section.token_count = count_tokens_func(current_section.text)
            else:
                # Content before first heading - create implicit section
                logger.debug(
                    "content_before_heading",
                    text_preview=_safe_log_text(text_content, 30),
                    label=label,
                )
                # Optionally: Create a default section for orphan content
                # For now, we skip content that appears before any heading

    # Don't forget the last section
    if current_section:
        sections.append(current_section)

    logger.info(
        "texts_array_extraction_complete",
        texts_processed=texts_processed,
        sections_found=len(sections),
        sections_with_text=sum(1 for s in sections if s.text.strip()),
        heading_strategy=heading_strategy,
    )

    return sections


def _extract_from_body_tree(
    body: Any,
    section_metadata_class: type,
    count_tokens_func: callable,
) -> list[Any]:
    """Extract sections by traversing DoclingDocument.body tree (Legacy method).

    This method is kept for compatibility with native DoclingDocument objects
    that have a proper body tree structure (not JSON $ref pointers).

    WARNING: This method does NOT work with HTTP API JSON responses!
    HTTP API JSON has body.children containing only $ref pointers like:
        {"$ref": "#/groups/0"}
    These $ref pointers don't have label/text attributes, so traversal yields nothing.

    Use _extract_from_texts_array() for HTTP API responses instead.

    Args:
        body: DoclingDocument.body tree structure
        section_metadata_class: SectionMetadata dataclass type
        count_tokens_func: Function to count tokens

    Returns:
        List of SectionMetadata objects
    """
    sections: list[Any] = []
    current_section: Any | None = None
    nodes_traversed = 0

    def get_provenance(doc_item: Any) -> tuple[int | None, dict[str, float] | None]:
        """Extract page_no and bbox from DocItem.prov."""
        # Handle dict format
        if isinstance(doc_item, dict):
            prov_data = doc_item.get("prov")
            if not prov_data:
                return None, None

            prov = prov_data[0] if isinstance(prov_data, list) else prov_data

            if isinstance(prov, dict):
                page_no = prov.get("page_no")
                bbox_data = prov.get("bbox")
                bbox = None
                if bbox_data and isinstance(bbox_data, dict):
                    bbox = {
                        "l": bbox_data.get("l", 0.0),
                        "t": bbox_data.get("t", 0.0),
                        "r": bbox_data.get("r", 0.0),
                        "b": bbox_data.get("b", 0.0),
                    }
                return page_no, bbox

        # Handle object format
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

    def traverse_body(node: Any) -> None:
        """Recursively traverse body tree."""
        nonlocal current_section, nodes_traversed
        nodes_traversed += 1

        is_dict = isinstance(node, dict)

        # Check for $ref pointer (HTTP API JSON format) - these can't be processed here
        if is_dict and "$ref" in node and len(node) == 1:
            # This is a JSON Reference pointer, not actual content
            # Log once at debug level to avoid spam
            return

        # Get label
        if is_dict:
            label = node.get("label", None)
        else:
            label = getattr(node, "label", None)

        if label and isinstance(label, str):
            label_str = label
        elif label and hasattr(label, "value"):
            label_str = label.value
        else:
            label_str = None

        is_heading = label_str in ["title", "subtitle-level-1", "subtitle-level-2"]

        if is_heading:
            if current_section:
                sections.append(current_section)

            page_no, bbox = get_provenance(node)

            if is_dict:
                heading_text = node.get("text", "").strip()
            else:
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
                "section_detected_from_body",
                heading=_safe_log_text(heading_text, 50),
                level=current_section.level,
                page_no=page_no,
            )

        else:
            if current_section:
                if is_dict:
                    node_text = node.get("text", "").strip()
                else:
                    node_text = getattr(node, "text", "").strip()

                if node_text:
                    current_section.text += node_text + "\n\n"
                    current_section.token_count = count_tokens_func(current_section.text)

        # Recurse into children
        children = None
        if is_dict:
            children = node.get("children", [])
        elif hasattr(node, "children"):
            children = node.children

        if children:
            for child in children:
                traverse_body(child)

    traverse_body(body)

    if current_section:
        sections.append(current_section)

    logger.info(
        "body_tree_extraction_complete",
        nodes_traversed=nodes_traversed,
        sections_found=len(sections),
    )

    return sections


def extract_section_hierarchy(
    docling_document: Any,
    section_metadata_class: type,
) -> list[Any]:
    """Extract section hierarchy from Docling DoclingDocument object (ADR-039).

    This function is the foundation for Adaptive Section-Aware Chunking (ADR-039),
    which merges small sections intelligently while preserving large sections.

    ==========================================================================
    EXTRACTION STRATEGY (Sprint 33 - TD-044):
    ==========================================================================

    We use TWO different extraction methods depending on the document source:

    1. HTTP API JSON Response (DoclingParsedDocument with json_content):
       → Use `texts` array directly (contains all text items with labels)
       → This is the PREFERRED method for HTTP API responses

    2. Native DoclingDocument objects:
       → Traverse body tree recursively
       → Legacy method, kept for compatibility

    Detection Logic:
    - If document has `json_content` with `texts` array → Use texts array
    - Otherwise → Fall back to body tree traversal

    ==========================================================================

    Args:
        docling_document: DoclingDocument or DoclingParsedDocument object
        section_metadata_class: SectionMetadata dataclass type

    Returns:
        List[SectionMetadata]: Ordered list of sections with headings and text

    Raises:
        ValueError: If document is None

    Example:
        >>> from src.components.ingestion.langgraph_nodes import SectionMetadata
        >>> doc = await docling.parse_document("presentation.pptx")
        >>> sections = extract_section_hierarchy(doc, SectionMetadata)
        >>> len(sections)  # Should be ~16 for 17-slide presentation
        16
    """
    extraction_start = time.perf_counter()

    if docling_document is None:
        raise ValueError("docling_document is None - cannot extract sections")

    # Token counting helper
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

    sections: list[Any] = []

    # ==========================================================================
    # STRATEGY 1: Extract from json_content["texts"] array (HTTP API Response)
    # ==========================================================================
    # This is the PRIMARY method for DoclingParsedDocument from HTTP API.
    # The texts array contains all text items with their labels directly accessible.
    #
    # Why this works:
    # - json_content["texts"] is a flat array of all text items
    # - Each item has "label" (title/paragraph/list_item) and "text" fields
    # - Items are in document order, so we can process sequentially
    #
    # Why body traversal fails for HTTP API:
    # - json_content["body"]["children"] contains only $ref pointers
    # - These $ref pointers reference items in "groups" array
    # - The actual text content is in "texts", not in body tree
    # ==========================================================================

    json_content = getattr(docling_document, "json_content", None)
    if json_content and isinstance(json_content, dict):
        texts = json_content.get("texts", [])
        if texts and isinstance(texts, list) and len(texts) > 0:
            logger.info(
                "using_texts_array_extraction",
                texts_count=len(texts),
                reason="json_content has texts array (HTTP API response)",
            )
            sections = _extract_from_texts_array(
                texts=texts,
                section_metadata_class=section_metadata_class,
                count_tokens_func=count_tokens,
            )

    # ==========================================================================
    # STRATEGY 2: Fall back to body tree traversal (Native DoclingDocument)
    # ==========================================================================
    # This is the FALLBACK method for native DoclingDocument objects.
    # Only used if texts array extraction didn't produce results.
    # ==========================================================================

    if not sections:
        if not hasattr(docling_document, "body") or docling_document.body is None:
            logger.warning(
                "docling_document_no_body",
                doc_type=type(docling_document).__name__,
                has_body=hasattr(docling_document, "body"),
                has_json_content=json_content is not None,
            )
            return []

        logger.info(
            "using_body_tree_extraction",
            reason="texts array empty or not available, falling back to body traversal",
        )
        sections = _extract_from_body_tree(
            body=docling_document.body,
            section_metadata_class=section_metadata_class,
            count_tokens_func=count_tokens,
        )

    # ==========================================================================
    # Logging and metrics
    # ==========================================================================

    extraction_end = time.perf_counter()
    extraction_duration_ms = (extraction_end - extraction_start) * 1000
    total_tokens = sum(s.token_count for s in sections)
    total_text_chars = sum(len(s.text) for s in sections)

    logger.info(
        "TIMING_section_extraction_complete",
        stage="section_extraction",
        duration_ms=round(extraction_duration_ms, 2),
        total_sections=len(sections),
        sections_with_text=sum(1 for s in sections if s.text.strip()),
        total_tokens=total_tokens,
        total_text_chars=total_text_chars,
        avg_tokens_per_section=(
            round(total_tokens / len(sections), 1) if sections else 0
        ),
        throughput_sections_per_sec=(
            round(len(sections) / (extraction_duration_ms / 1000), 2)
            if extraction_duration_ms > 0
            else 0
        ),
    )

    return sections
