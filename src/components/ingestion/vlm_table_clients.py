"""VLM HTTP clients for table cross-validation.

Sprint 129.6c: Async clients for VLM table extraction services.
Sprint 129.6g (ADR-063): NemotronVLClient replaces Granite + DeepSeek as single VLM.

Active client:
- NemotronVLClient: Nemotron VL v1 8B FP4-QAD via vLLM (port 8002, P2 HTML prompt)

Legacy clients (kept for reference, unused since ADR-063):
- GraniteDoclingClient: Granite-Docling-258M via docling-serve (port 8083)
- DeepSeekOCRClient: DeepSeek-OCR-2 via vLLM OpenAI API (port 8002)
"""

import base64
import json
import re

import httpx
import structlog

logger = structlog.get_logger(__name__)

_TIMEOUT = 60.0  # Seconds per VLM call


class GraniteDoclingClient:
    """Client for Granite-Docling-258M via docling-serve container.

    Docling-serve exposes an OpenAPI at /v1/convert/source that accepts
    base64-encoded images and returns structured document JSON including
    table cells with row/col indices.
    """

    def __init__(self, base_url: str = "http://localhost:8083"):
        self.base_url = base_url.rstrip("/")
        self._healthy: bool | None = None

    async def health_check(self) -> bool:
        """Check if Granite docling-serve is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                self._healthy = resp.status_code == 200
        except Exception:
            self._healthy = False
        return self._healthy or False

    async def extract_tables_from_page(self, page_image_bytes: bytes) -> list[list[list[str]]]:
        """Extract tables from a page image via docling-serve.

        Args:
            page_image_bytes: PNG image bytes of a PDF page

        Returns:
            List of tables, each as a 2D list of cell strings (rows × cols).
            Empty list if extraction fails or no tables found.
        """
        b64_image = base64.b64encode(page_image_bytes).decode("utf-8")

        payload = {
            "options": {
                "from_formats": ["image"],
                "to_formats": ["md"],
                "do_table_structure": True,
                "do_ocr": True,
            },
            "sources": [
                {
                    "kind": "file",
                    "base64_string": b64_image,
                    "filename": "page.png",
                }
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/convert/source",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.warning("granite_vlm_timeout", base_url=self.base_url)
            return []
        except Exception as e:
            logger.warning("granite_vlm_error", error=repr(e))
            return []

        # Try structured JSON tables first, fall back to markdown parsing
        structured = self._parse_docling_tables(data)
        if structured:
            return structured

        # Fall back: parse markdown content with shared markdown table parser
        md_content = data.get("document", {}).get("md_content", "")
        if md_content:
            return _parse_markdown_tables(md_content)

        return []

    def _parse_docling_tables(self, data: dict) -> list[list[list[str]]]:
        """Parse docling-serve JSON response into 2D cell grids.

        Docling-serve returns a document JSON with tables containing
        'table_cells' (flat list with row/col offset indices) and
        'num_rows'/'num_cols' dimensions.
        """
        tables: list[list[list[str]]] = []

        # Navigate docling-serve response structure
        # Response can be nested: {document: {tables: [...]}} or {tables: [...]}
        doc = data.get("document", data)
        table_list = doc.get("tables", [])

        for table_data in table_list:
            cells = table_data.get("table_cells", [])
            num_rows = table_data.get("num_rows", 0)
            num_cols = table_data.get("num_cols", 0)

            if num_rows == 0 or num_cols == 0 or not cells:
                continue

            grid: list[list[str]] = [[""] * num_cols for _ in range(num_rows)]
            for cell in cells:
                row_idx = cell.get("start_row_offset_idx", -1)
                col_idx = cell.get("start_col_offset_idx", -1)
                if 0 <= row_idx < num_rows and 0 <= col_idx < num_cols:
                    grid[row_idx][col_idx] = cell.get("text", "")

            tables.append(grid)

        return tables


class DeepSeekOCRClient:
    """Client for DeepSeek-OCR-2 via vLLM OpenAI-compatible API.

    DeepSeek-OCR-2 is a 3B causal VLM that understands document layouts
    including tables. Accessed via vLLM's /v1/chat/completions endpoint
    with base64 image content.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        model: str = "deepseek-ai/DeepSeek-OCR-2",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._healthy: bool | None = None

    async def health_check(self) -> bool:
        """Check if DeepSeek vLLM instance is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                self._healthy = resp.status_code == 200
        except Exception:
            self._healthy = False
        return self._healthy or False

    async def extract_tables_from_page(self, page_image_bytes: bytes) -> list[list[list[str]]]:
        """Extract tables from a page image via DeepSeek-OCR-2.

        Sends the page image with a prompt asking to extract tables
        in markdown format, then parses the markdown into cell grids.

        Args:
            page_image_bytes: PNG image bytes of a PDF page

        Returns:
            List of tables, each as 2D list of cell strings.
            Empty list if extraction fails or no tables found.
        """
        b64_image = base64.b64encode(page_image_bytes).decode("utf-8")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}",
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract ALL tables from this image. "
                                "Output each table in markdown pipe format. "
                                "Use | to separate columns, one row per line. "
                                "Include header row and separator row (|---|). "
                                "Output ONLY the markdown tables, nothing else."
                            ),
                        },
                    ],
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.0,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.warning("deepseek_vlm_timeout", base_url=self.base_url)
            return []
        except Exception as e:
            logger.warning("deepseek_vlm_error", error=repr(e))
            return []

        # Extract text content from OpenAI-compatible response
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            logger.warning("deepseek_vlm_no_content")
            return []

        return _parse_markdown_tables(content)


def _parse_markdown_tables(markdown: str) -> list[list[list[str]]]:
    """Parse pipe-separated markdown tables into 2D cell grids.

    Handles standard markdown table format:
        | col1 | col2 | col3 |
        |------|------|------|
        | a    | b    | c    |

    Args:
        markdown: Raw markdown text potentially containing tables

    Returns:
        List of tables, each as 2D list of cell strings
    """
    tables: list[list[list[str]]] = []
    current_table: list[list[str]] = []

    for line in markdown.split("\n"):
        stripped = line.strip()

        # Check if line is a table row (contains pipes)
        if "|" in stripped:
            # Skip separator rows (|---|---|)
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                continue

            # Parse cells: split by | and strip whitespace
            cells = [cell.strip() for cell in stripped.split("|")]
            # Remove empty first/last from leading/trailing pipes
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]

            if cells:
                current_table.append(cells)
        else:
            # Non-table line: flush current table if any
            if current_table:
                tables.append(current_table)
                current_table = []

    # Flush last table
    if current_table:
        tables.append(current_table)

    return tables


# ============================================================================
# Sprint 129.6g (ADR-063): Nemotron VL v1 8B — Single VLM for table validation
# ============================================================================

# NVIDIA RD-TableBench official P2 prompt — cleanest, most parseable output
_NEMOTRON_P2_HTML_PROMPT = (
    "Convert the image to an HTML table. The output should begin with "
    "<table> and end with </table>. Specify rowspan and colspan attributes "
    "when they are greater than 1. Do not specify any other attributes. "
    "Only use the b, br, tr, th, td, sub and sup HTML tags. "
    "No additional formatting is required."
)


class NemotronVLClient:
    """Client for Nemotron VL v1 8B FP4-QAD via vLLM OpenAI-compatible API.

    ADR-063: Selected as single VLM for table cross-validation. 100% reliability
    (15/15 benchmark), 34.7 tok/s, ~5GB VRAM at gpu-memory-utilization=0.10.
    Uses P2 HTML table prompt (NVIDIA RD-TableBench official).

    Container: aegis-vlm-table (port 8002, same base image as extraction vLLM).
    """

    MODEL = "nvidia/Llama-3.1-Nemotron-Nano-VL-8B-V1-FP4-QAD"

    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url.rstrip("/")
        self._healthy: bool | None = None

    async def health_check(self) -> bool:
        """Check if Nemotron VLM vLLM instance is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                self._healthy = resp.status_code == 200
        except Exception:
            self._healthy = False
        return self._healthy or False

    async def extract_tables_from_page(
        self, page_image_bytes: bytes, timeout: float = _TIMEOUT
    ) -> list[list[list[str]]]:
        """Extract tables from a page image via Nemotron VL v1 (P2 HTML prompt).

        Args:
            page_image_bytes: PNG image bytes of a document page
            timeout: Request timeout in seconds (default 60s)

        Returns:
            List of tables, each as 2D list of cell strings (rows x cols).
            Empty list if extraction fails or no tables found.
        """
        b64_image = base64.b64encode(page_image_bytes).decode("utf-8")

        payload = {
            "model": self.MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}",
                            },
                        },
                        {
                            "type": "text",
                            "text": _NEMOTRON_P2_HTML_PROMPT,
                        },
                    ],
                }
            ],
            "max_tokens": 2048,
            "temperature": 0.0,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.warning("nemotron_vlm_timeout", base_url=self.base_url)
            return []
        except Exception as e:
            logger.warning("nemotron_vlm_error", error=repr(e))
            return []

        # Extract HTML content from OpenAI-compatible response
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            logger.warning("nemotron_vlm_no_content")
            return []

        return _parse_html_tables(content)


def _parse_html_tables(html: str) -> list[list[list[str]]]:
    """Parse HTML <table> output from Nemotron VL into 2D cell grids.

    Handles standard HTML table with tr/th/td and rowspan/colspan attributes.

    Args:
        html: Raw HTML string containing <table>...</table> elements

    Returns:
        List of tables, each as 2D list of cell strings
    """
    tables: list[list[list[str]]] = []

    # Find all <table>...</table> blocks
    table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.DOTALL | re.IGNORECASE)
    row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
    cell_pattern = re.compile(r"<(th|td)([^>]*)>(.*?)</(?:th|td)>", re.DOTALL | re.IGNORECASE)

    for table_match in table_pattern.finditer(html):
        table_html = table_match.group(1)
        rows: list[list[str]] = []

        for row_match in row_pattern.finditer(table_html):
            row_html = row_match.group(1)
            cells: list[str] = []

            for cell_match in cell_pattern.finditer(row_html):
                cell_text = cell_match.group(3)
                # Strip inner HTML tags, keep text
                clean_text = re.sub(r"<[^>]+>", " ", cell_text).strip()
                # Normalize whitespace
                clean_text = re.sub(r"\s+", " ", clean_text)
                cells.append(clean_text)

            if cells:
                rows.append(cells)

        if rows:
            tables.append(rows)

    # Fallback: if no HTML tables found, try markdown parsing
    if not tables and "|" in html:
        return _parse_markdown_tables(html)

    return tables
