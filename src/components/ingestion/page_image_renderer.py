"""PDF page image renderer using PyMuPDF for VLM cross-validation.

Sprint 129.6c: Renders individual PDF pages as PNG images for
VLM-based table cross-validation.
Sprint 129.6g: Added render_all_pages() for parallel VLM page processing.

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


def render_all_pages(pdf_path: str, dpi: int = 200) -> dict[int, bytes]:
    """Render ALL pages of a PDF as PNG bytes.

    Sprint 129.6g: Used by VLM parallel page processor to send all pages
    to VLM for table extraction.

    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for rendering (default 200)

    Returns:
        Dict mapping 1-based page numbers to PNG image bytes.
        Empty dict if rendering fails.

    Raises:
        FileNotFoundError: If pdf_path does not exist
        RuntimeError: If rendering fails
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    try:
        pages: dict[int, bytes] = {}
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=mat)
            png_bytes = pix.tobytes("png")
            # 1-based page numbers (Docling convention)
            pages[page_idx + 1] = png_bytes

        logger.debug(
            "all_pages_rendered",
            pdf_path=pdf_path,
            num_pages=len(pages),
            dpi=dpi,
            total_bytes=sum(len(b) for b in pages.values()),
        )
        return pages
    finally:
        doc.close()
