"""PDF page image renderer using PyMuPDF for VLM cross-validation.

Sprint 129.6c: Renders individual PDF pages as PNG images for
VLM-based table cross-validation. Used by TableCrossValidator
to provide page images to Granite-Docling and DeepSeek-OCR VLMs.

Note: Docling uses 1-based page numbers, PyMuPDF uses 0-based.
"""

import structlog

logger = structlog.get_logger(__name__)


def render_page_image(pdf_path: str, page_no: int, dpi: int = 200) -> bytes:
    """Render a single PDF page as PNG bytes.

    Args:
        pdf_path: Path to PDF file
        page_no: 1-based page number (Docling convention)
        dpi: Resolution for rendering (default 200, balances quality vs size)

    Returns:
        PNG image bytes

    Raises:
        FileNotFoundError: If pdf_path does not exist
        ValueError: If page_no is out of range
        RuntimeError: If rendering fails
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    try:
        # Convert 1-based (Docling) to 0-based (fitz)
        page_idx = page_no - 1
        if page_idx < 0 or page_idx >= len(doc):
            raise ValueError(f"Page {page_no} out of range (PDF has {len(doc)} pages)")

        page = doc[page_idx]
        # zoom factor: 200 DPI / 72 default DPI ≈ 2.78
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")

        logger.debug(
            "page_image_rendered",
            pdf_path=pdf_path,
            page_no=page_no,
            dpi=dpi,
            image_size=len(png_bytes),
            width=pix.width,
            height=pix.height,
        )
        return png_bytes
    finally:
        doc.close()
