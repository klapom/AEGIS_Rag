"""Unit tests for Sprint 129.6a: Full table content extraction.

Tests the complete table extraction pipeline including:
- Markdown conversion from Docling format (table_cells, grid, num_rows, num_cols)
- Structured cell data
- Header detection via column_header field
- Edge cases (empty tables, merged cells, missing data)
"""

import pytest

from src.components.ingestion.docling_client import (
    DoclingParsedDocument,
    _convert_table_to_markdown,
)


# =============================================================================
# Test Data Fixtures — using actual Docling output format
# =============================================================================


@pytest.fixture
def simple_table_data():
    """Simple 3x2 table (3 rows, 2 cols) with header — Docling format."""
    return {
        "table_cells": [
            {
                "text": "Name",
                "row_span": 1,
                "col_span": 1,
                "start_row_offset_idx": 0,
                "end_row_offset_idx": 1,
                "start_col_offset_idx": 0,
                "end_col_offset_idx": 1,
                "column_header": True,
            },
            {
                "text": "Age",
                "row_span": 1,
                "col_span": 1,
                "start_row_offset_idx": 0,
                "end_row_offset_idx": 1,
                "start_col_offset_idx": 1,
                "end_col_offset_idx": 2,
                "column_header": True,
            },
            {
                "text": "Alice",
                "row_span": 1,
                "col_span": 1,
                "start_row_offset_idx": 1,
                "end_row_offset_idx": 2,
                "start_col_offset_idx": 0,
                "end_col_offset_idx": 1,
                "column_header": False,
            },
            {
                "text": "30",
                "row_span": 1,
                "col_span": 1,
                "start_row_offset_idx": 1,
                "end_row_offset_idx": 2,
                "start_col_offset_idx": 1,
                "end_col_offset_idx": 2,
                "column_header": False,
            },
            {
                "text": "Bob",
                "row_span": 1,
                "col_span": 1,
                "start_row_offset_idx": 2,
                "end_row_offset_idx": 3,
                "start_col_offset_idx": 0,
                "end_col_offset_idx": 1,
                "column_header": False,
            },
            {
                "text": "25",
                "row_span": 1,
                "col_span": 1,
                "start_row_offset_idx": 2,
                "end_row_offset_idx": 3,
                "start_col_offset_idx": 1,
                "end_col_offset_idx": 2,
                "column_header": False,
            },
        ],
        "num_rows": 3,
        "num_cols": 2,
        "grid": [
            [{"text": "Name"}, {"text": "Age"}],
            [{"text": "Alice"}, {"text": "30"}],
            [{"text": "Bob"}, {"text": "25"}],
        ],
    }


@pytest.fixture
def complex_table_data():
    """Complex table with pipe characters — Docling format."""
    return {
        "table_cells": [
            {
                "text": "Product",
                "start_row_offset_idx": 0,
                "start_col_offset_idx": 0,
                "column_header": True,
            },
            {
                "text": "Price ($)",
                "start_row_offset_idx": 0,
                "start_col_offset_idx": 1,
                "column_header": True,
            },
            {
                "text": "Stock",
                "start_row_offset_idx": 0,
                "start_col_offset_idx": 2,
                "column_header": True,
            },
            {
                "text": "Widget | A",
                "start_row_offset_idx": 1,
                "start_col_offset_idx": 0,
                "column_header": False,
            },
            {
                "text": "99.99",
                "start_row_offset_idx": 1,
                "start_col_offset_idx": 1,
                "column_header": False,
            },
            {
                "text": "150",
                "start_row_offset_idx": 1,
                "start_col_offset_idx": 2,
                "column_header": False,
            },
            {
                "text": "Gadget | B",
                "start_row_offset_idx": 2,
                "start_col_offset_idx": 0,
                "column_header": False,
            },
            {
                "text": "149.50",
                "start_row_offset_idx": 2,
                "start_col_offset_idx": 1,
                "column_header": False,
            },
            {
                "text": "42",
                "start_row_offset_idx": 2,
                "start_col_offset_idx": 2,
                "column_header": False,
            },
        ],
        "num_rows": 3,
        "num_cols": 3,
        "grid": [
            [{"text": "Product"}, {"text": "Price ($)"}, {"text": "Stock"}],
            [{"text": "Widget | A"}, {"text": "99.99"}, {"text": "150"}],
            [{"text": "Gadget | B"}, {"text": "149.50"}, {"text": "42"}],
        ],
    }


@pytest.fixture
def docling_response_with_tables():
    """Mock Docling JSON response with full table data — Docling format."""
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "pages": {"1": {"page_no": 1, "size": {"width": 595, "height": 842}}},
        "body": {},
        "tables": [
            {
                "self_ref": "#/tables/0",
                "label": "table",
                "captions": [{"text": "Financial Summary 2024"}],
                "prov": [
                    {
                        "page_no": 1,
                        "bbox": {"l": 50.0, "t": 100.0, "r": 550.0, "b": 300.0},
                    }
                ],
                "data": {
                    "table_cells": [
                        {
                            "text": "Quarter",
                            "start_row_offset_idx": 0,
                            "start_col_offset_idx": 0,
                            "column_header": True,
                        },
                        {
                            "text": "Revenue",
                            "start_row_offset_idx": 0,
                            "start_col_offset_idx": 1,
                            "column_header": True,
                        },
                        {
                            "text": "Profit",
                            "start_row_offset_idx": 0,
                            "start_col_offset_idx": 2,
                            "column_header": True,
                        },
                        {
                            "text": "Q1",
                            "start_row_offset_idx": 1,
                            "start_col_offset_idx": 0,
                            "column_header": False,
                        },
                        {
                            "text": "$1M",
                            "start_row_offset_idx": 1,
                            "start_col_offset_idx": 1,
                            "column_header": False,
                        },
                        {
                            "text": "$200K",
                            "start_row_offset_idx": 1,
                            "start_col_offset_idx": 2,
                            "column_header": False,
                        },
                        {
                            "text": "Q2",
                            "start_row_offset_idx": 2,
                            "start_col_offset_idx": 0,
                            "column_header": False,
                        },
                        {
                            "text": "$1.5M",
                            "start_row_offset_idx": 2,
                            "start_col_offset_idx": 1,
                            "column_header": False,
                        },
                        {
                            "text": "$300K",
                            "start_row_offset_idx": 2,
                            "start_col_offset_idx": 2,
                            "column_header": False,
                        },
                    ],
                    "num_rows": 3,
                    "num_cols": 3,
                    "grid": [
                        [{"text": "Quarter"}, {"text": "Revenue"}, {"text": "Profit"}],
                        [{"text": "Q1"}, {"text": "$1M"}, {"text": "$200K"}],
                        [{"text": "Q2"}, {"text": "$1.5M"}, {"text": "$300K"}],
                    ],
                },
            },
            {
                "self_ref": "#/tables/1",
                "label": "table",
                "captions": [],
                "prov": [],
                # No data field - backward compatibility test
            },
        ],
    }


# =============================================================================
# Markdown Conversion Tests
# =============================================================================


def test_convert_simple_table_to_markdown(simple_table_data):
    """Test markdown conversion for simple table."""
    markdown = _convert_table_to_markdown(simple_table_data)

    # Check structure
    lines = markdown.split("\n")
    assert len(lines) == 4, f"Should have header + separator + 2 data rows, got {lines}"

    # Check header
    assert "Name" in lines[0]
    assert "Age" in lines[0]

    # Check separator
    assert lines[1] == "|---|---|", f"Should have proper separator, got {lines[1]}"

    # Check data rows
    assert "Alice" in lines[2]
    assert "30" in lines[2]
    assert "Bob" in lines[3]
    assert "25" in lines[3]


def test_convert_table_escapes_pipes(complex_table_data):
    """Test that pipe characters in cells are escaped."""
    markdown = _convert_table_to_markdown(complex_table_data)

    # Pipes in cell text should be escaped
    assert r"Widget \| A" in markdown
    assert r"Gadget \| B" in markdown

    # Table structure pipes should NOT be escaped
    assert "| Product |" in markdown


def test_convert_empty_table():
    """Test conversion of empty table."""
    empty_table = {"table_cells": [], "grid": [], "num_rows": 0, "num_cols": 0}
    markdown = _convert_table_to_markdown(empty_table)
    assert markdown == ""


def test_convert_table_without_grid_uses_table_cells():
    """Test conversion using table_cells when grid is missing."""
    table_data = {
        "table_cells": [
            {"text": "A", "start_row_offset_idx": 0, "start_col_offset_idx": 0},
            {"text": "B", "start_row_offset_idx": 0, "start_col_offset_idx": 1},
            {"text": "C", "start_row_offset_idx": 1, "start_col_offset_idx": 0},
            {"text": "D", "start_row_offset_idx": 1, "start_col_offset_idx": 1},
        ],
        "num_rows": 2,
        "num_cols": 2,
        # No grid field — should use table_cells fallback
    }

    markdown = _convert_table_to_markdown(table_data)

    # Should still generate valid markdown
    assert markdown, "Should handle missing grid via table_cells fallback"
    assert "A" in markdown
    assert "B" in markdown
    assert "|---|---|" in markdown


def test_convert_table_flat_cells_fallback():
    """Test fallback when only flat table_cells are available."""
    table_data = {
        "table_cells": [
            {"text": "A"},
            {"text": "B"},
            {"text": "C"},
            {"text": "D"},
        ],
        "num_rows": 0,
        "num_cols": 0,
        # No grid, no row/col indices — last-resort flat list
    }

    markdown = _convert_table_to_markdown(table_data)

    # Should produce at least a single-row table from flat cells
    assert markdown, "Should handle flat cells via last-resort fallback"
    assert "A" in markdown
    assert "B" in markdown


# =============================================================================
# Full DoclingParsedDocument Integration Tests
# =============================================================================


def test_parsed_document_with_full_table_data(docling_response_with_tables):
    """Test DoclingParsedDocument extracts full table content."""
    # Simulate the extraction logic from docling_client.py
    json_content = docling_response_with_tables
    tables_data = []

    for table in json_content.get("tables", []):
        table_info = {
            "ref": table.get("self_ref", ""),
            "label": table.get("label", "table"),
            "captions": table.get("captions", []),
            "page_no": None,
            "bbox": None,
        }

        # Extract provenance
        prov = table.get("prov", [])
        if prov:
            p = prov[0] if isinstance(prov, list) else prov
            table_info["page_no"] = p.get("page_no")
            table_info["bbox"] = p.get("bbox")

        # Extract full table content (Docling format)
        table_data = table.get("data", {})
        if table_data:
            markdown = _convert_table_to_markdown(table_data)
            table_info["markdown"] = markdown
            table_info["cells"] = table_data.get("table_cells", [])
            table_info["num_rows"] = table_data.get("num_rows", 0)
            table_info["num_cols"] = table_data.get("num_cols", 0)
            table_info["grid"] = table_data.get("grid", [])
            has_header = any(c.get("column_header", False) for c in table_info["cells"])
            if not has_header and table_info["num_rows"] > 1:
                has_header = True
            table_info["has_header"] = has_header
        else:
            table_info["markdown"] = ""
            table_info["cells"] = []
            table_info["num_rows"] = 0
            table_info["num_cols"] = 0
            table_info["has_header"] = False

        tables_data.append(table_info)

    # Create DoclingParsedDocument
    parsed = DoclingParsedDocument(
        text="Sample document text",
        metadata={"filename": "test.pdf"},
        tables=tables_data,
        images=[],
        layout={},
        parse_time_ms=100.0,
        json_content=json_content,
        md_content="# Test Document",
    )

    # Assertions on first table (with data)
    assert len(parsed.tables) == 2
    table1 = parsed.tables[0]
    assert table1["ref"] == "#/tables/0"
    assert table1["page_no"] == 1
    assert table1["num_rows"] == 3
    assert table1["num_cols"] == 3
    assert table1["has_header"] is True
    assert len(table1["cells"]) == 9

    # Check markdown content
    markdown = table1["markdown"]
    assert "Quarter" in markdown
    assert "Revenue" in markdown
    assert "Profit" in markdown
    assert "Q1" in markdown
    assert "$1M" in markdown
    assert "|---|---|---|" in markdown

    # Assertions on second table (no data - backward compatibility)
    table2 = parsed.tables[1]
    assert table2["ref"] == "#/tables/1"
    assert table2["markdown"] == ""
    assert table2["cells"] == []
    assert table2["num_rows"] == 0
    assert table2["num_cols"] == 0
    assert table2["has_header"] is False


def test_backward_compatibility_without_data_field():
    """Test that tables without data field still work (backward compatibility)."""
    json_content = {
        "tables": [
            {
                "self_ref": "#/tables/0",
                "label": "table",
                "captions": [{"text": "Legacy Table"}],
                "prov": [{"page_no": 1, "bbox": {"l": 0, "t": 0, "r": 100, "b": 100}}],
                # No 'data' field
            }
        ]
    }

    tables_data = []
    for table in json_content.get("tables", []):
        table_info = {
            "ref": table.get("self_ref", ""),
            "label": table.get("label", "table"),
            "captions": table.get("captions", []),
            "page_no": None,
            "bbox": None,
        }

        prov = table.get("prov", [])
        if prov:
            p = prov[0] if isinstance(prov, list) else prov
            table_info["page_no"] = p.get("page_no")
            table_info["bbox"] = p.get("bbox")

        table_data = table.get("data", {})
        if table_data:
            markdown = _convert_table_to_markdown(table_data)
            table_info["markdown"] = markdown
            table_info["cells"] = table_data.get("table_cells", [])
            table_info["num_rows"] = table_data.get("num_rows", 0)
            table_info["num_cols"] = table_data.get("num_cols", 0)
            table_info["has_header"] = table_info["num_rows"] > 1
        else:
            table_info["markdown"] = ""
            table_info["cells"] = []
            table_info["num_rows"] = 0
            table_info["num_cols"] = 0
            table_info["has_header"] = False

        tables_data.append(table_info)

    parsed = DoclingParsedDocument(
        text="Test",
        metadata={},
        tables=tables_data,
        images=[],
        layout={},
        parse_time_ms=50.0,
        json_content=json_content,
        md_content="",
    )

    assert len(parsed.tables) == 1
    table = parsed.tables[0]
    assert table["ref"] == "#/tables/0"
    assert table["page_no"] == 1
    assert table["markdown"] == ""
    assert table["cells"] == []
    assert table["num_rows"] == 0
    assert table["num_cols"] == 0


# =============================================================================
# Edge Cases and Robustness Tests
# =============================================================================


def test_table_with_empty_cells():
    """Test table with empty cell text."""
    table_data = {
        "table_cells": [
            {"text": "Header1", "start_row_offset_idx": 0, "start_col_offset_idx": 0},
            {"text": "", "start_row_offset_idx": 0, "start_col_offset_idx": 1},
            {"text": "Data", "start_row_offset_idx": 1, "start_col_offset_idx": 0},
            {"text": "", "start_row_offset_idx": 1, "start_col_offset_idx": 1},
        ],
        "num_rows": 2,
        "num_cols": 2,
        "grid": [
            [{"text": "Header1"}, {"text": ""}],
            [{"text": "Data"}, {"text": ""}],
        ],
    }

    markdown = _convert_table_to_markdown(table_data)

    assert "Header1" in markdown
    assert "Data" in markdown
    assert "|  |" in markdown or "| |" in markdown, "Should have empty cells in markdown"


def test_table_with_merged_cells():
    """Test table with colspan (merged cells) in grid."""
    # Docling represents merged cells in grid by repeating or referencing
    table_data = {
        "table_cells": [
            {
                "text": "Merged Header",
                "start_row_offset_idx": 0,
                "start_col_offset_idx": 0,
                "col_span": 2,
            },
            {"text": "A", "start_row_offset_idx": 1, "start_col_offset_idx": 0},
            {"text": "B", "start_row_offset_idx": 1, "start_col_offset_idx": 1},
        ],
        "num_rows": 2,
        "num_cols": 2,
        "grid": [
            [{"text": "Merged Header"}, {"text": "Merged Header"}],  # Repeated in grid
            [{"text": "A"}, {"text": "B"}],
        ],
    }

    markdown = _convert_table_to_markdown(table_data)

    assert "Merged Header" in markdown
    assert "A" in markdown
    assert "B" in markdown


def test_table_single_row():
    """Test table with single row (no data rows, just header)."""
    table_data = {
        "table_cells": [
            {"text": "Only", "start_row_offset_idx": 0, "start_col_offset_idx": 0},
            {"text": "Row", "start_row_offset_idx": 0, "start_col_offset_idx": 1},
        ],
        "num_rows": 1,
        "num_cols": 2,
        "grid": [
            [{"text": "Only"}, {"text": "Row"}],
        ],
    }

    markdown = _convert_table_to_markdown(table_data)

    assert "Only" in markdown
    assert "Row" in markdown
    assert "|---|---|" in markdown


def test_table_single_column():
    """Test table with single column."""
    table_data = {
        "table_cells": [
            {"text": "Item 1", "start_row_offset_idx": 0, "start_col_offset_idx": 0},
            {"text": "Item 2", "start_row_offset_idx": 1, "start_col_offset_idx": 0},
            {"text": "Item 3", "start_row_offset_idx": 2, "start_col_offset_idx": 0},
        ],
        "num_rows": 3,
        "num_cols": 1,
        "grid": [
            [{"text": "Item 1"}],
            [{"text": "Item 2"}],
            [{"text": "Item 3"}],
        ],
    }

    markdown = _convert_table_to_markdown(table_data)

    lines = markdown.split("\n")
    assert len(lines) == 4, f"Should have header + separator + 2 data rows, got {lines}"
    assert "Item 1" in lines[0]
    assert lines[1] == "|---|", f"Should have single-column separator, got {lines[1]}"
    assert "Item 2" in lines[2]
    assert "Item 3" in lines[3]
