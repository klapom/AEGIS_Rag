"""Unit tests for table pipeline integration (Sprint 129.6e).

Tests that table chunks are created with quality scoring and properly
integrated into the chunking pipeline.

Uses Docling format: table_cells with start_row_offset_idx/start_col_offset_idx,
grid (pre-built 2D array), num_rows, num_cols.
"""

import pytest
from src.components.ingestion.nodes.adaptive_chunking import (
    _build_cells_2d,
    _create_table_chunks,
)


# ---------------------------------------------------------------------------
# Helper: build a Docling-style cell dict with row/col position indices
# ---------------------------------------------------------------------------
def _cell(text: str, row: int, col: int, *, column_header: bool = False) -> dict:
    return {
        "text": text,
        "start_row_offset_idx": row,
        "start_col_offset_idx": col,
        "column_header": column_header,
    }


class TestBuildCells2D:
    """Test 2D cell grid construction from Docling table data."""

    def test_grid_preferred_over_cells(self):
        """When grid is present, it takes priority over cells."""
        table = {
            "grid": [
                [{"text": "Name"}, {"text": "Age"}],
                [{"text": "Alice"}, {"text": "30"}],
            ],
            "cells": [_cell("WRONG", 0, 0)],
            "num_rows": 2,
            "num_cols": 2,
        }
        grid = _build_cells_2d(table)
        assert grid == [["Name", "Age"], ["Alice", "30"]]

    def test_dict_cells_with_dimensions(self):
        """Docling cells with start_row/col_offset_idx are placed correctly."""
        table = {
            "cells": [
                _cell("Name", 0, 0),
                _cell("Age", 0, 1),
                _cell("Alice", 1, 0),
                _cell("30", 1, 1),
            ],
            "num_rows": 2,
            "num_cols": 2,
        }
        grid = _build_cells_2d(table)
        assert grid == [["Name", "Age"], ["Alice", "30"]]

    def test_empty_cells(self):
        table = {"cells": [], "num_rows": 0, "num_cols": 0}
        assert _build_cells_2d(table) == []

    def test_no_cells_key(self):
        table = {"num_rows": 2, "num_cols": 2}
        assert _build_cells_2d(table) == []

    def test_string_cells_in_grid(self):
        """Grid with plain strings instead of dicts."""
        table = {
            "grid": [["A", "B"], ["C", "D"]],
            "num_rows": 2,
            "num_cols": 2,
        }
        grid = _build_cells_2d(table)
        assert grid == [["A", "B"], ["C", "D"]]

    def test_zero_dimensions_fallback(self):
        """When num_rows/num_cols are 0, falls back to flat list."""
        table = {
            "cells": [{"text": "X"}, {"text": "Y"}],
            "num_rows": 0,
            "num_cols": 0,
        }
        grid = _build_cells_2d(table)
        assert grid == [["X", "Y"]]

    def test_more_cells_than_grid(self):
        """Extra cells beyond grid dimensions are ignored."""
        table = {
            "cells": [
                _cell("A", 0, 0),
                _cell("B", 0, 1),
                _cell("C", 0, 2),
                _cell("EXTRA", 1, 0),  # row 1 doesn't exist (num_rows=1)
            ],
            "num_rows": 1,
            "num_cols": 3,
        }
        grid = _build_cells_2d(table)
        assert grid == [["A", "B", "C"]]

    def test_fewer_cells_than_grid(self):
        """Missing cells filled with empty strings."""
        table = {
            "cells": [_cell("A", 0, 0)],
            "num_rows": 2,
            "num_cols": 2,
        }
        grid = _build_cells_2d(table)
        assert grid == [["A", ""], ["", ""]]

    def test_grid_with_mixed_cell_types(self):
        """Grid containing dicts, strings, and other types."""
        table = {
            "grid": [
                [{"text": "Header"}, "Plain"],
                [42, None],
            ],
        }
        grid = _build_cells_2d(table)
        assert grid == [["Header", "Plain"], ["", ""]]


class TestCreateTableChunks:
    """Test table chunk creation with quality scoring."""

    def test_high_quality_table_creates_chunk(self):
        merged_chunks = []
        parsed_tables = [
            {
                "ref": "#/tables/0",
                "captions": [{"text": "Revenue Summary"}],
                "page_no": 1,
                "markdown": "| Quarter | Revenue |\n|---|---|\n| Q1 | $100K |\n| Q2 | $150K |",
                "cells": [
                    _cell("Quarter", 0, 0, column_header=True),
                    _cell("Revenue", 0, 1, column_header=True),
                    _cell("Q1", 1, 0),
                    _cell("$100K", 1, 1),
                    _cell("Q2", 2, 0),
                    _cell("$150K", 2, 1),
                ],
                "num_rows": 3,
                "num_cols": 2,
                "has_header": True,
            }
        ]

        created, rejected = _create_table_chunks(
            parsed_tables=parsed_tables,
            document_id="doc_001",
            document_type="pdf",
            merged_chunks=merged_chunks,
            start_index=5,
        )

        assert created == 1
        assert rejected == 0
        assert len(merged_chunks) == 1

        chunk = merged_chunks[0]["chunk"]
        assert "Revenue Summary" in chunk.content
        assert "Quarter" in chunk.content
        assert chunk.metadata["is_table"] is True
        assert chunk.metadata["table_quality_score"] is not None
        assert chunk.metadata["table_quality_grade"] in [
            "EXCELLENT",
            "GOOD",
            "FAIR",
        ]
        assert chunk.chunk_index == 5
        assert chunk.document_id == "doc_001"
        assert chunk.document_type == "pdf"

    def test_empty_markdown_skipped(self):
        merged_chunks = []
        parsed_tables = [
            {
                "ref": "#/tables/0",
                "captions": [],
                "markdown": "",
                "cells": [],
                "num_rows": 0,
                "num_cols": 0,
            }
        ]

        created, rejected = _create_table_chunks(
            parsed_tables=parsed_tables,
            document_id="doc_001",
            document_type="pdf",
            merged_chunks=merged_chunks,
            start_index=0,
        )

        assert created == 0
        assert rejected == 0
        assert len(merged_chunks) == 0

    def test_poor_quality_table_rejected(self):
        merged_chunks = []
        # Single cell, 1x1 table — fails min_size and density heuristics
        parsed_tables = [
            {
                "ref": "#/tables/0",
                "captions": [],
                "markdown": "| x |",
                "cells": [_cell("x", 0, 0)],
                "num_rows": 1,
                "num_cols": 1,
            }
        ]

        created, rejected = _create_table_chunks(
            parsed_tables=parsed_tables,
            document_id="doc_001",
            document_type="pdf",
            merged_chunks=merged_chunks,
            start_index=0,
        )

        # 1x1 table should be rejected (below quality threshold)
        assert created == 0
        assert rejected == 1

    def test_multiple_tables_mixed_quality(self):
        merged_chunks = []
        parsed_tables = [
            # Good table (3x3 with grid)
            {
                "ref": "#/tables/0",
                "captions": [{"text": "Good Table"}],
                "page_no": 1,
                "markdown": "| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |",
                "grid": [
                    [{"text": "A"}, {"text": "B"}, {"text": "C"}],
                    [{"text": "1"}, {"text": "2"}, {"text": "3"}],
                    [{"text": "4"}, {"text": "5"}, {"text": "6"}],
                ],
                "num_rows": 3,
                "num_cols": 3,
            },
            # Bad table — single row, single col
            {
                "ref": "#/tables/1",
                "captions": [],
                "markdown": "| x |",
                "cells": [_cell("x", 0, 0)],
                "num_rows": 1,
                "num_cols": 1,
            },
        ]

        created, rejected = _create_table_chunks(
            parsed_tables=parsed_tables,
            document_id="doc_001",
            document_type="pdf",
            merged_chunks=merged_chunks,
            start_index=10,
        )

        assert created == 1  # Only good table
        assert rejected == 1  # Bad table rejected
        assert len(merged_chunks) == 1
        assert "Good Table" in merged_chunks[0]["chunk"].content

    def test_caption_as_string(self):
        merged_chunks = []
        parsed_tables = [
            {
                "ref": "#/tables/0",
                "captions": ["String Caption"],
                "markdown": "| A | B |\n|---|---|\n| 1 | 2 |",
                "grid": [
                    [{"text": "A"}, {"text": "B"}],
                    [{"text": "1"}, {"text": "2"}],
                ],
                "num_rows": 2,
                "num_cols": 2,
            }
        ]

        created, _ = _create_table_chunks(
            parsed_tables=parsed_tables,
            document_id="doc_001",
            document_type="pdf",
            merged_chunks=merged_chunks,
            start_index=0,
        )

        assert created == 1
        assert "String Caption" in merged_chunks[0]["chunk"].content

    def test_no_parsed_tables(self):
        merged_chunks = []
        created, rejected = _create_table_chunks(
            parsed_tables=[],
            document_id="doc_001",
            document_type="pdf",
            merged_chunks=merged_chunks,
            start_index=0,
        )
        assert created == 0
        assert rejected == 0

    def test_table_metadata_fields(self):
        merged_chunks = []
        parsed_tables = [
            {
                "ref": "#/tables/0",
                "captions": [],
                "page_no": 3,
                "markdown": "| X | Y |\n|---|---|\n| a | b |\n| c | d |",
                "grid": [
                    [{"text": "X"}, {"text": "Y"}],
                    [{"text": "a"}, {"text": "b"}],
                    [{"text": "c"}, {"text": "d"}],
                ],
                "num_rows": 3,
                "num_cols": 2,
            }
        ]

        _create_table_chunks(
            parsed_tables=parsed_tables,
            document_id="doc_test",
            document_type="docx",
            merged_chunks=merged_chunks,
            start_index=0,
        )

        meta = merged_chunks[0]["chunk"].metadata
        assert meta["is_table"] is True
        assert meta["table_ref"] == "#/tables/0"
        assert meta["table_num_rows"] == 3
        assert meta["table_num_cols"] == 2
        assert meta["table_ingest_mode"] in ["full", "with_warning"]

    def test_chunk_has_image_bboxes_empty(self):
        """Table chunks should have empty image_bboxes."""
        merged_chunks = []
        parsed_tables = [
            {
                "ref": "#/tables/0",
                "captions": [],
                "markdown": "| A | B |\n|---|---|\n| 1 | 2 |",
                "grid": [
                    [{"text": "A"}, {"text": "B"}],
                    [{"text": "1"}, {"text": "2"}],
                ],
                "num_rows": 2,
                "num_cols": 2,
            }
        ]

        _create_table_chunks(
            parsed_tables=parsed_tables,
            document_id="doc_001",
            document_type="pdf",
            merged_chunks=merged_chunks,
            start_index=0,
        )

        assert merged_chunks[0]["image_bboxes"] == []
