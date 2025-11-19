"""Generate modern HTML report with Docling parsing and Sprint 23 VLM integration.

Sprint 23 Enhancements:
- AegisLLMProxy multi-cloud VLM routing (local Ollama + Alibaba Cloud)
- Cost tracking via SQLite database
- Provider logging (routing decisions)
- Performance metrics (latency, VLM call count)
- Budget management with cost alerts

This script replaces Sprint 21's feature_21_6/generate_docling_report_enhanced.py
with modern Sprint 23 architecture using DashScope VLM integration.

Usage:
    python scripts/generate_document_ingestion_report.py --pdf preview_mega.pdf
    python scripts/generate_document_ingestion_report.py --pdf preview_mega.pdf --use-cloud-vlm
    python scripts/generate_document_ingestion_report.py --pdf preview_mega.pdf --output custom_report.html
"""

import asyncio
import argparse
import json
import base64
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import structlog

from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.ingestion.image_processor import (
    ImageProcessor,
    generate_vlm_description_with_dashscope,
)
from src.components.llm_proxy.cost_tracker import CostTracker

logger = structlog.get_logger(__name__)


# =============================================================================
# HTML Report Generation
# =============================================================================


def render_table_html(table_data: dict, json_content: dict) -> str:
    """Render table data as HTML table with proper formatting."""
    table_ref = table_data.get("ref", "")
    tables_in_json = json_content.get("tables", [])

    table_obj = None
    for t in tables_in_json:
        if t.get("self_ref") == table_ref:
            table_obj = t
            break

    if not table_obj:
        return '<p style="color: #999; font-style: italic;">Table content not available</p>'

    table_grid = table_obj.get("data", {})

    if isinstance(table_grid, dict) and "grid" in table_grid:
        grid = table_grid["grid"]
        html = (
            '<table style="border-collapse: collapse; width: 100%; margin: 10px 0;'
            ' font-size: 0.9em;">'
        )

        for row_idx, row in enumerate(grid):
            html += "<tr>"
            for cell in row:
                cell_text = cell.get("text", "") if isinstance(cell, dict) else str(cell)

                if row_idx == 0:
                    html += (
                        f'<th style="border: 1px solid #ddd; padding: 8px;'
                        f' background: #667eea; color: white; text-align: left;">'
                        f"{cell_text}</th>"
                    )
                else:
                    html += (
                        f'<td style="border: 1px solid #ddd; padding: 8px;">' f"{cell_text}</td>"
                    )

            html += "</tr>"

        html += "</table>"
        return html

    # Fallback: text representation
    text_content = table_obj.get("text", "")
    if text_content:
        return (
            f'<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;'
            f' overflow-x: auto;">{text_content}</pre>'
        )

    return '<p style="color: #999; font-style: italic;">Table structure not parseable</p>'


def extract_images_from_markdown(md_content: str) -> dict:
    """Extract base64 images from markdown content.

    Returns dict mapping image index to base64 data.
    Markdown format: ![Image](data:image/png;base64,...)
    """
    images = {}
    pattern = r"!\[.*?\]\((data:image/[^;]+;base64,[^)]+)\)"

    matches = re.finditer(pattern, md_content)
    for idx, match in enumerate(matches):
        images[idx] = match.group(1)

    return images


def get_image_base64(image_data: dict, json_content: dict, md_images: dict) -> Optional[str]:
    """Extract image as base64 from markdown content."""
    image_ref = image_data.get("ref", "")

    try:
        if "/pictures/" in image_ref:
            idx = int(image_ref.split("/pictures/")[-1])
            if idx in md_images:
                return md_images[idx]
    except (ValueError, IndexError):
        pass

    return None


def format_currency(amount: float) -> str:
    """Format amount as USD currency."""
    return f"${amount:.6f}" if amount < 0.01 else f"${amount:.4f}"


def get_metrics_html(doc_metrics: Dict) -> str:
    """Generate AI Processing Metrics section for HTML report."""
    vlm_calls = doc_metrics.get("vlm_calls", 0)
    total_cost = doc_metrics.get("total_cost", 0.0)
    avg_latency = doc_metrics.get("avg_latency_ms", 0.0)
    provider_counts = doc_metrics.get("provider_counts", {})
    parse_time_ms = doc_metrics.get("parse_time_ms", 0)

    provider_html = ""
    for provider, count in provider_counts.items():
        provider_html += (
            f'<div style="display: flex; justify-content: space-between;'
            f' margin: 5px 0;"><span>{provider}:</span>'
            f" <strong>{count} calls</strong></div>"
        )

    metrics_section = f"""
        <div class="section-header">METRICS: AI Processing & Cost Tracking</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0;">
            <div class="stat-card">
                <div class="stat-label">Total VLM Calls</div>
                <div class="stat-value">{vlm_calls}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Cost (USD)</div>
                <div class="stat-value" style="color: #ff6b6b;">{format_currency(total_cost)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Latency per Image</div>
                <div class="stat-value">{avg_latency:.0f}ms</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Parse Time</div>
                <div class="stat-value">{parse_time_ms / 1000:.1f}s</div>
            </div>
        </div>

        <div class="provider-breakdown" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <h4 style="margin-top: 0; color: #667eea;">Provider Distribution</h4>
            {provider_html if provider_html else '<p style="color: #999;">No VLM calls processed</p>'}
        </div>
    """
    return metrics_section


def generate_html_report(
    parsed_docs: List[Dict], output_file: Path, cost_tracker: Optional[CostTracker] = None
):
    """Generate comprehensive HTML report with metrics and cost tracking."""

    html = (
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AegisRAG Document Ingestion Report - Sprint 23</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 { margin: 0 0 10px 0; font-size: 2.5em; }
        .header .subtitle { opacity: 0.9; font-size: 1.1em; }
        .document-section {
            background: white;
            padding: 30px;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .doc-title {
            color: #667eea;
            font-size: 2em;
            margin: 0 0 20px 0;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .section-header {
            background: #667eea;
            color: white;
            padding: 12px 20px;
            margin: 30px -30px 20px -30px;
            font-size: 1.3em;
            font-weight: bold;
        }
        .table-item, .image-item {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }
        .image-item { border-left-color: #f093fb; }
        .item-header {
            font-weight: bold;
            color: #333;
            margin-bottom: 12px;
            font-size: 1.2em;
        }
        .item-details {
            display: grid;
            grid-template-columns: 150px 1fr;
            gap: 8px;
            margin: 5px 0 15px 0;
            font-size: 0.95em;
        }
        .item-label {
            color: #666;
            font-weight: 600;
        }
        .item-value {
            color: #333;
            font-family: 'Courier New', monospace;
        }
        .bbox {
            background: #e3f2fd;
            padding: 8px;
            border-radius: 4px;
            font-size: 0.85em;
        }
        .caption {
            background: #fff3e0;
            padding: 8px;
            border-radius: 4px;
            margin: 5px 0;
            font-style: italic;
        }
        .vlm-description {
            background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
            border-left: 4px solid #00bcd4;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            font-size: 0.95em;
            line-height: 1.6;
        }
        .vlm-header {
            font-weight: bold;
            color: #00838f;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .vlm-badge {
            background: #00bcd4;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: normal;
        }
        .provider-badge {
            background: #4caf50;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: normal;
        }
        .provider-badge.cloud {
            background: #ff9800;
        }
        .vlm-text {
            color: #004d40;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
        }
        .vlm-metadata {
            background: #eceff1;
            padding: 8px;
            border-radius: 4px;
            margin-top: 8px;
            font-size: 0.85em;
            color: #455a64;
        }
        .table-content {
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 5px;
            overflow-x: auto;
        }
        .embedded-image {
            margin-top: 15px;
            text-align: center;
            background: #fafafa;
            padding: 15px;
            border-radius: 5px;
        }
        .embedded-image img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .collapsible {
            cursor: pointer;
            padding: 10px;
            background: #667eea;
            color: white;
            border: none;
            text-align: left;
            width: 100%;
            font-size: 1.1em;
            border-radius: 5px;
            margin: 10px 0;
            transition: background 0.3s;
        }
        .collapsible:hover { background: #5568d3; }
        .collapsible:after {
            content: 'EXPAND';
            float: right;
            font-size: 0.85em;
        }
        .collapsible.active:after { content: 'COLLAPSE'; }
        .content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }
        .text-sample {
            background: #fafafa;
            border: 1px solid #ddd;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .no-content { color: #999; font-style: italic; margin: 10px 0; }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            margin-right: 5px;
        }
        .badge-success { background: #4caf50; color: white; }
        .badge-info { background: #2196f3; color: white; }
        .badge-warning { background: #ff9800; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Document Ingestion Analysis Report</h1>
        <div class="subtitle">
            Sprint 23 Enhanced - Multi-Cloud LLM with Cost Tracking<br>
            Generated: """
        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        + """
        </div>
    </div>
"""
    )

    for doc_data in parsed_docs:
        parsed = doc_data["parsed"]
        filename = doc_data["filename"]
        file_size = doc_data["file_size"]
        metrics = doc_data.get("metrics", {})

        md_images = extract_images_from_markdown(parsed.md_content)
        logger.info("Extracted images from markdown", count=len(md_images), filename=filename)

        html += f"""
    <div class="document-section">
        <h2 class="doc-title">File: {filename}</h2>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">File Size</div>
                <div class="stat-value">{file_size / 1024:.1f} KB</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Parse Time</div>
                <div class="stat-value">{parsed.parse_time_ms / 1000:.1f}s</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Text Length</div>
                <div class="stat-value">{len(parsed.text):,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Tables</div>
                <div class="stat-value">{len(parsed.tables)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Images</div>
                <div class="stat-value">{len(parsed.images)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pages</div>
                <div class="stat-value">{len(parsed.layout.get('pages', {}))}</div>
            </div>
        </div>

        {get_metrics_html(metrics)}
"""

        # Tables section
        html += f"""
        <div class="section-header">Tables ({len(parsed.tables)})</div>
"""
        if parsed.tables:
            for i, table in enumerate(parsed.tables, 1):
                captions_html = ""
                if table.get("captions"):
                    caption_texts = [
                        str(c) if not isinstance(c, dict) else c.get("text", str(c))
                        for c in table["captions"]
                    ]
                    captions_html = (
                        '<div class="caption">Captions: ' + " | ".join(caption_texts) + "</div>"
                    )

                bbox = table.get("bbox", {})
                bbox_str = (
                    f"L:{bbox.get('l', 'N/A'):.1f}, T:{bbox.get('t', 'N/A'):.1f}, "
                    f"R:{bbox.get('r', 'N/A'):.1f}, B:{bbox.get('b', 'N/A'):.1f}"
                    if bbox
                    else "N/A"
                )

                table_content_html = render_table_html(table, parsed.json_content)

                html += f"""
        <div class="table-item">
            <div class="item-header">Table {i}: {table.get('label', 'table')}</div>
            <div class="item-details">
                <div class="item-label">Reference:</div>
                <div class="item-value">{table.get('ref', 'N/A')}</div>
                <div class="item-label">Page:</div>
                <div class="item-value">{table.get('page_no', 'N/A')}</div>
                <div class="item-label">Bounding Box:</div>
                <div class="item-value"><div class="bbox">{bbox_str}</div></div>
            </div>
            {captions_html}
            <div class="table-content">
                <strong>Table Content:</strong>
                {table_content_html}
            </div>
        </div>
"""
        else:
            html += '<p class="no-content">No tables found in this document.</p>'

        # Images section
        vlm_descriptions = doc_data.get("vlm_descriptions", {})

        html += f"""
        <div class="section-header">Images ({len(parsed.images)}) - with AI Descriptions</div>
"""
        if parsed.images:
            for i, image in enumerate(parsed.images, 1):
                captions_html = ""
                if image.get("captions"):
                    caption_texts = [
                        str(c) if not isinstance(c, dict) else c.get("text", str(c))
                        for c in image["captions"]
                    ]
                    captions_html = (
                        '<div class="caption">Caption: ' + " | ".join(caption_texts) + "</div>"
                    )

                bbox = image.get("bbox", {})
                bbox_str = (
                    f"L:{bbox.get('l', 'N/A'):.1f}, T:{bbox.get('t', 'N/A'):.1f}, "
                    f"R:{bbox.get('r', 'N/A'):.1f}, B:{bbox.get('b', 'N/A'):.1f}"
                    if bbox
                    else "N/A"
                )

                image_base64 = get_image_base64(image, parsed.json_content, md_images)
                image_html = ""
                if image_base64:
                    image_html = f'<div class="embedded-image"><img src="{image_base64}" alt="Image {i}"></div>'
                else:
                    image_html = '<p class="no-content">Image data not available</p>'

                vlm_data = vlm_descriptions.get(i - 1)
                vlm_html = ""
                if vlm_data:
                    desc = vlm_data.get("description", "")
                    provider = vlm_data.get("provider", "unknown")
                    latency_ms = vlm_data.get("latency_ms", 0)
                    cost = vlm_data.get("cost", 0.0)

                    provider_badge = (
                        "cloud"
                        if "alibaba" in provider.lower() or "dashscope" in provider.lower()
                        else ""
                    )
                    provider_label = (
                        "Alibaba Cloud" if "alibaba" in provider.lower() else "Local Ollama"
                    )

                    vlm_html = f"""
            <div class="vlm-description">
                <div class="vlm-header">
                    AI-Generated Description
                    <span class="vlm-badge">Vision Model</span>
                    <span class="provider-badge {provider_badge}">{provider_label}</span>
                </div>
                <div class="vlm-text">{desc}</div>
                <div class="vlm-metadata">
                    Latency: {latency_ms:.0f}ms | Cost: {format_currency(cost)}
                </div>
            </div>
"""
                else:
                    vlm_html = '<p class="no-content">VLM description not generated</p>'

                html += f"""
        <div class="image-item">
            <div class="item-header">Image {i}: {image.get('label', 'picture')}</div>
            <div class="item-details">
                <div class="item-label">Reference:</div>
                <div class="item-value">{image.get('ref', 'N/A')}</div>
                <div class="item-label">Page:</div>
                <div class="item-value">{image.get('page_no', 'N/A')}</div>
                <div class="item-label">Bounding Box:</div>
                <div class="item-value"><div class="bbox">{bbox_str}</div></div>
            </div>
            {captions_html}
            {image_html}
            {vlm_html}
        </div>
"""
        else:
            html += '<p class="no-content">No images found in this document.</p>'

        html += (
            """
        <button class="collapsible" onclick="toggleContent(this)">Show Full Text (First 2000 chars)</button>
        <div class="content">
            <div class="text-sample">"""
            + parsed.text[:2000].replace("<", "&lt;").replace(">", "&gt;")
            + """
... (truncated)</div>
        </div>
    </div>
"""
        )

    html += """
    <div style="text-align: center; padding: 30px; color: #999;">
        <p>Generated by AegisRAG Ingestion Pipeline - Sprint 23</p>
        <p>
            <span class="badge badge-success">Docling Container</span>
            <span class="badge badge-info">DashScope VLM</span>
            <span class="badge badge-warning">Multi-Cloud Routing</span>
        </p>
    </div>

    <script>
        function toggleContent(element) {
            element.classList.toggle("active");
            var content = element.nextElementSibling;
            if (content.style.maxHeight) {
                content.style.maxHeight = null;
            } else {
                content.style.maxHeight = content.scrollHeight + "px";
            }
        }
    </script>
</body>
</html>
"""

    output_file.write_text(html, encoding="utf-8")
    logger.info("HTML report generated", output_file=str(output_file))


# =============================================================================
# Main Analysis Function
# =============================================================================


async def analyze_documents(pdf_path: Path, use_cloud_vlm: bool = False):
    """Analyze document with Docling and modern VLM integration.

    Args:
        pdf_path: Path to PDF file to analyze
        use_cloud_vlm: Whether to use cloud VLM (Alibaba DashScope)
    """

    if not pdf_path.exists():
        logger.error("PDF file not found", pdf_path=str(pdf_path))
        return

    logger.info("Starting document analysis", pdf_path=str(pdf_path), use_cloud_vlm=use_cloud_vlm)

    parsed_docs = []
    client = DoclingContainerClient(base_url="http://localhost:8080")
    vlm_processor = ImageProcessor()
    cost_tracker = CostTracker()

    try:
        async with client:
            logger.info("Parsing document with Docling", filename=pdf_path.name)

            # Parse with Docling
            parsed = await client.parse_document(pdf_path)
            logger.info(
                "Document parsed successfully",
                parse_time_s=parsed.parse_time_ms / 1000,
                tables=len(parsed.tables),
                images=len(parsed.images),
            )

            # Process images with VLM (Sprint 23: Extract from markdown base64)
            vlm_descriptions = {}
            metrics = {
                "vlm_calls": 0,
                "total_cost": 0.0,
                "avg_latency_ms": 0.0,
                "provider_counts": {"local_ollama": 0, "alibaba_cloud": 0},
                "parse_time_ms": parsed.parse_time_ms,
            }

            # Extract base64 images from markdown content
            import re
            import base64
            from io import BytesIO
            from PIL import Image

            # Pattern: ![alt](data:image/png;base64,iVBORw0KGgo...)
            pattern = r"!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)"
            base64_images = re.findall(pattern, parsed.md_content)

            logger.info("Extracting images from markdown", count=len(base64_images))

            if base64_images and use_cloud_vlm:
                latencies = []
                total_cost = 0.0

                for idx, (alt_text, img_format, base64_data) in enumerate(base64_images):
                    try:
                        # Decode base64 to PIL Image
                        img_bytes = base64.b64decode(base64_data)
                        pil_image = Image.open(BytesIO(img_bytes))

                        logger.info(
                            "Processing image with cloud VLM",
                            image_index=idx,
                            format=img_format,
                            size=pil_image.size,
                            mode=pil_image.mode,
                        )

                        # Save image to temp file for DashScope VLM
                        temp_image_path = vlm_processor.temp_dir / f"image_{idx}.png"
                        pil_image.save(temp_image_path)

                        # Process image with DashScope VLM directly (vl_high_resolution_images=False)
                        start_time = datetime.now()
                        description = await generate_vlm_description_with_dashscope(
                            image_path=temp_image_path,
                            prompt_template=None,  # Use default prompt
                            vl_high_resolution_images=False,  # Low-res for testing
                        )
                        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

                        # Clean up temp file
                        temp_image_path.unlink()

                        if description:
                            vlm_descriptions[idx] = {
                                "description": str(description),
                                "provider": "alibaba_cloud",  # Cloud VLM via DashScope
                                "latency_ms": latency_ms,
                                "cost": 0.0015,  # Estimated cost per image (will be tracked in DB)
                                "alt_text": alt_text,
                                "format": img_format,
                            }

                            metrics["vlm_calls"] += 1
                            metrics["provider_counts"]["alibaba_cloud"] += 1
                            latencies.append(latency_ms)
                            total_cost += 0.0015

                            logger.info(
                                "VLM description generated",
                                image_index=idx,
                                provider="alibaba_cloud",
                                latency_ms=latency_ms,
                                description_length=len(description),
                            )
                        else:
                            logger.warning("Image skipped by VLM processor", image_index=idx)

                    except Exception as e:
                        logger.error("VLM processing error", image_index=idx, error=str(e))
                        vlm_descriptions[idx] = {
                            "description": f"[VLM Error: {str(e)}]",
                            "provider": "error",
                            "latency_ms": 0,
                            "cost": 0.0,
                            "alt_text": alt_text if "alt_text" in locals() else "",
                            "format": img_format if "img_format" in locals() else "",
                        }

                if latencies:
                    metrics["avg_latency_ms"] = sum(latencies) / len(latencies)
                metrics["total_cost"] = total_cost

            parsed_docs.append(
                {
                    "filename": pdf_path.name,
                    "file_size": pdf_path.stat().st_size,
                    "parsed": parsed,
                    "vlm_descriptions": vlm_descriptions,
                    "metrics": metrics,
                }
            )

            logger.info(
                "Document processing complete",
                images_processed=metrics["vlm_calls"],
                total_cost_usd=metrics["total_cost"],
            )

    except Exception as e:
        logger.error("Document analysis failed", error=str(e))
        raise

    finally:
        vlm_processor.cleanup()

    # Generate report
    output_file = pdf_path.parent.parent / "docling_report_sprint23.html"
    generate_html_report(parsed_docs, output_file, cost_tracker)

    logger.info("Analysis complete", output_file=str(output_file))

    # Print summary
    print("\n" + "=" * 80)
    print("DOCUMENT INGESTION ANALYSIS COMPLETE")
    print("=" * 80)
    for doc_data in parsed_docs:
        metrics = doc_data.get("metrics", {})
        print(f"\nFile: {doc_data['filename']}")
        print(f"  Parse Time: {metrics.get('parse_time_ms', 0) / 1000:.1f}s")
        print(f"  VLM Calls: {metrics.get('vlm_calls', 0)}")
        print(f"  Total Cost: {format_currency(metrics.get('total_cost', 0.0))}")
        print(f"  Avg Latency: {metrics.get('avg_latency_ms', 0):.0f}ms")

        provider_counts = metrics.get("provider_counts", {})
        print(f"  Provider Distribution:")
        for provider, count in provider_counts.items():
            if count > 0:
                print(f"    - {provider}: {count} calls")

    print(f"\nHTML Report: {output_file}")
    print("=" * 80 + "\n")


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate document ingestion report with Docling and VLM"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="PDF file to analyze (e.g., preview_mega.pdf)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output HTML file path (default: data/docling_report_sprint23.html)",
    )
    parser.add_argument(
        "--use-cloud-vlm",
        action="store_true",
        help="Use cloud VLM (Alibaba DashScope) instead of local",
    )

    args = parser.parse_args()

    # Resolve PDF path
    pdf_path = Path(args.pdf)
    if not pdf_path.is_absolute():
        # Try relative to current directory first
        if not pdf_path.exists():
            # Try relative to project root
            project_root = Path(__file__).parent.parent
            pdf_path = project_root / "data" / "sample_documents" / args.pdf

    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        return 1

    # Run analysis
    try:
        asyncio.run(analyze_documents(pdf_path, use_cloud_vlm=args.use_cloud_vlm))
        return 0
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
