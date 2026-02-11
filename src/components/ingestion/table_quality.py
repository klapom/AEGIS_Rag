"""Table quality heuristics for evaluating extracted tables without ground truth.

This module provides composite scoring for table quality based on:
- Cell density (non-empty cells ratio)
- Rectangular consistency (uniform column count)
- Header plausibility (first row looks like header)
- Type consistency (columns have consistent data types)
- Content plausibility (no gibberish via Index of Coincidence)
- Minimum size constraints
"""

from dataclasses import dataclass
from collections import Counter


@dataclass
class TableQualityReport:
    """Comprehensive quality metrics for an extracted table."""

    cell_density: float
    rectangular_consistency: float
    header_plausibility: float
    type_consistency: float
    content_plausibility: float
    min_size_ok: bool
    num_rows: int
    num_cols: int
    overall_score: float
    grade: str


def compute_table_quality(cells: list[list[str]], has_header: bool = True) -> TableQualityReport:
    """Compute quality metrics for a table represented as 2D cell list.

    Args:
        cells: 2D list of cell text values (rows × cols)
        has_header: Whether first row should be treated as header

    Returns:
        TableQualityReport with all metrics and overall grade
    """
    if not cells or not cells[0]:
        return TableQualityReport(
            cell_density=0.0,
            rectangular_consistency=0.0,
            header_plausibility=0.0,
            type_consistency=0.0,
            content_plausibility=0.0,
            min_size_ok=False,
            num_rows=0,
            num_cols=0,
            overall_score=0.0,
            grade="POOR",
        )

    num_rows = len(cells)
    num_cols = max(len(row) for row in cells) if cells else 0

    # Compute individual metrics
    density = _cell_density(cells)
    rectangular = _rectangular_consistency(cells)
    header = _header_plausibility(cells) if has_header and num_rows > 1 else 0.5
    type_cons = _type_consistency(cells)
    content = _content_plausibility(cells)
    min_size = num_rows >= 2 and num_cols >= 2

    # Weighted composite score
    overall = (
        0.20 * density
        + 0.20 * rectangular
        + 0.20 * type_cons
        + 0.15 * content
        + 0.15 * header
        + 0.10 * (1.0 if min_size else 0.3)
    )

    # Grade assignment
    if overall >= 0.85:
        grade = "EXCELLENT"
    elif overall >= 0.70:
        grade = "GOOD"
    elif overall >= 0.50:
        grade = "FAIR"
    else:
        grade = "POOR"

    return TableQualityReport(
        cell_density=density,
        rectangular_consistency=rectangular,
        header_plausibility=header,
        type_consistency=type_cons,
        content_plausibility=content,
        min_size_ok=min_size,
        num_rows=num_rows,
        num_cols=num_cols,
        overall_score=overall,
        grade=grade,
    )


def should_ingest_table(report: TableQualityReport) -> tuple[bool, str]:
    """Determine if a table should be ingested based on quality score.

    Args:
        report: TableQualityReport from compute_table_quality

    Returns:
        Tuple of (should_ingest: bool, mode: str)
        Modes: "full", "with_warning", "rejected"
    """
    if report.overall_score >= 0.70:
        return (True, "full")
    elif report.overall_score >= 0.50:
        return (True, "with_warning")
    else:
        return (False, "rejected")


def _cell_density(cells: list[list[str]]) -> float:
    """Ratio of non-empty cells to total cells."""
    if not cells:
        return 0.0

    total = sum(len(row) for row in cells)
    if total == 0:
        return 0.0

    non_empty = sum(1 for row in cells for cell in row if cell.strip())
    return non_empty / total


def _rectangular_consistency(cells: list[list[str]]) -> float:
    """Check if all rows have the same column count."""
    if not cells:
        return 0.0

    row_widths = [len(row) for row in cells]
    unique_widths = set(row_widths)

    if len(unique_widths) == 1:
        return 1.0
    else:
        return 1.0 / len(unique_widths)


def _header_plausibility(cells: list[list[str]]) -> float:
    """Check if first row looks like a header (text-dominant while body has numbers)."""
    if len(cells) < 2:
        return 0.5

    header_row = cells[0]
    body_rows = cells[1:]

    # Header should be mostly text
    header_text_ratio = sum(
        1 for cell in header_row if cell.strip() and not _is_numeric(cell.strip())
    ) / max(len(header_row), 1)

    # Body should have some numeric content
    body_cells = [cell for row in body_rows for cell in row if cell.strip()]
    if not body_cells:
        return 0.5

    body_numeric_ratio = sum(1 for cell in body_cells if _is_numeric(cell)) / len(body_cells)

    # Combine: high header text + some body numbers = plausible header
    return (header_text_ratio * 0.6) + (body_numeric_ratio * 0.4)


def _type_consistency(cells: list[list[str]]) -> float:
    """Check if columns have consistent data types (numeric vs text)."""
    if not cells:
        return 0.0

    # Transpose to get columns
    num_cols = max(len(row) for row in cells)
    if num_cols == 0:
        return 0.0

    col_scores = []
    for col_idx in range(num_cols):
        col_cells = [
            row[col_idx].strip() for row in cells if col_idx < len(row) and row[col_idx].strip()
        ]
        if not col_cells:
            continue

        # Count numeric vs text
        numeric_count = sum(1 for cell in col_cells if _is_numeric(cell))
        text_count = len(col_cells) - numeric_count

        # Dominant type ratio
        dominant_ratio = max(numeric_count, text_count) / len(col_cells)
        col_scores.append(dominant_ratio)

    return sum(col_scores) / len(col_scores) if col_scores else 0.0


def _content_plausibility(cells: list[list[str]]) -> float:
    """Check if content looks like natural language using Index of Coincidence."""
    # Concatenate all cell text
    text = " ".join(" ".join(row) for row in cells)
    if not text.strip():
        return 0.0

    ic = _index_of_coincidence(text)

    # Normalize: English/German text ~1.7, random ~1.0
    # Scale to 0.0-1.0 where 1.7 = 1.0 and 1.0 = 0.0
    normalized = min(1.0, max(0.0, (ic - 1.0) / 0.7))
    return normalized


def _index_of_coincidence(text: str) -> float:
    """Calculate Index of Coincidence for text.

    IC measures character frequency distribution.
    English/German text: ~1.7
    Random characters: ~1.0
    """
    # Use only alphabetic characters, case-insensitive
    alpha_text = "".join(c.lower() for c in text if c.isalpha())
    length = len(alpha_text)

    if length < 2:
        return 0.0

    # Count character frequencies
    freq = Counter(alpha_text)

    # IC formula: sum(freq * (freq - 1)) / (L * (L - 1))
    numerator = sum(count * (count - 1) for count in freq.values())
    denominator = length * (length - 1)

    if denominator == 0:
        return 0.0

    # Multiply by 26 to normalize to expected IC for 26-letter alphabet
    return 26 * (numerator / denominator)


def _is_numeric(text: str) -> bool:
    """Check if text represents a numeric value (int, float, percentage, currency)."""
    # Remove common numeric formatting
    cleaned = text.replace(",", "").replace(" ", "").strip()

    # Handle currency symbols
    if cleaned and cleaned[0] in "$€£¥":
        cleaned = cleaned[1:]

    # Handle percentage
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]

    # Try to parse as float
    try:
        float(cleaned)
        return True
    except ValueError:
        return False
