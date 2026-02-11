"""VLM cross-validation for borderline table quality scores.

Sprint 129.6d: Cross-validates Docling's heuristic table quality with
two VLM services (Granite-Docling-258M and DeepSeek-OCR-2). Only runs
for borderline tables (score 0.50-0.85) where heuristic confidence is low.

Scoring:
- 3 sources: 0.40×heuristic + 0.30×Granite + 0.30×DeepSeek
- 2 sources: 0.50×heuristic + 0.50×VLM
- 1 source: heuristic unchanged (graceful degradation)
- Agreement boost: +0.10 shift from heuristic to VLMs when both agree
"""

import time
from dataclasses import dataclass, field

import structlog

from src.components.ingestion.vlm_table_clients import (
    DeepSeekOCRClient,
    GraniteDoclingClient,
)

logger = structlog.get_logger(__name__)

# Borderline range for cross-validation
BORDERLINE_LOW = 0.50
BORDERLINE_HIGH = 0.85


@dataclass
class CrossValidationResult:
    """Result of VLM cross-validation for a single table."""

    adjusted_score: float
    original_heuristic_score: float
    granite_agreement: float | None = None
    deepseek_agreement: float | None = None
    sources_used: list[str] = field(default_factory=list)
    cell_count_docling: int = 0
    cell_count_granite: int = 0
    cell_count_deepseek: int = 0
    header_match: float | None = None
    content_similarity: float | None = None
    validation_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


class TableCrossValidator:
    """Cross-validates table extraction using VLM services.

    Orchestrates sequential calls to Granite and DeepSeek VLMs,
    computes cell agreement between Docling and VLM outputs,
    and blends scores for a more confident quality assessment.
    """

    def __init__(
        self,
        granite_url: str = "http://localhost:8083",
        deepseek_url: str = "http://localhost:8002",
    ):
        self._granite = GraniteDoclingClient(base_url=granite_url)
        self._deepseek = DeepSeekOCRClient(base_url=deepseek_url)
        self._granite_available: bool | None = None
        self._deepseek_available: bool | None = None

    def should_cross_validate(self, score: float) -> bool:
        """Check if a table score falls in the borderline range.

        Args:
            score: Heuristic quality score (0.0-1.0)

        Returns:
            True if score is in [0.50, 0.85] range
        """
        return BORDERLINE_LOW <= score <= BORDERLINE_HIGH

    async def check_availability(self) -> None:
        """Probe VLM services and cache availability. Call once per batch."""
        self._granite_available = await self._granite.health_check()
        self._deepseek_available = await self._deepseek.health_check()
        logger.info(
            "vlm_availability_checked",
            granite=self._granite_available,
            deepseek=self._deepseek_available,
        )

    async def cross_validate(
        self,
        docling_cells_2d: list[list[str]],
        page_image_bytes: bytes,
        heuristic_score: float,
    ) -> CrossValidationResult:
        """Cross-validate a table using VLM services.

        Sequential calls: Granite first, then DeepSeek (avoid peak GPU memory).

        Args:
            docling_cells_2d: 2D cell grid from Docling extraction
            page_image_bytes: PNG image of the PDF page containing the table
            heuristic_score: Original heuristic quality score

        Returns:
            CrossValidationResult with adjusted score and agreement metrics
        """
        start = time.perf_counter()
        result = CrossValidationResult(
            adjusted_score=heuristic_score,
            original_heuristic_score=heuristic_score,
            sources_used=["heuristic"],
            cell_count_docling=sum(len(row) for row in docling_cells_2d),
        )

        # Check availability if not yet probed
        if self._granite_available is None or self._deepseek_available is None:
            await self.check_availability()

        granite_agreement: float | None = None
        deepseek_agreement: float | None = None

        # Call Granite (sequential — not parallel, to avoid GPU peak)
        if self._granite_available:
            try:
                granite_tables = await self._granite.extract_tables_from_page(page_image_bytes)
                if granite_tables:
                    # Use first table (closest match to single-table validation)
                    best_grid = _find_best_matching_table(docling_cells_2d, granite_tables)
                    granite_agreement = _compute_cell_agreement(docling_cells_2d, best_grid)
                    result.granite_agreement = granite_agreement
                    result.cell_count_granite = sum(len(row) for row in best_grid)
                    result.sources_used.append("granite")
                else:
                    result.errors.append("granite_no_tables_found")
            except Exception as e:
                result.errors.append(f"granite_error: {repr(e)}")
                logger.warning("granite_cross_validation_failed", error=repr(e))

        # Call DeepSeek
        if self._deepseek_available:
            try:
                deepseek_tables = await self._deepseek.extract_tables_from_page(page_image_bytes)
                if deepseek_tables:
                    best_grid = _find_best_matching_table(docling_cells_2d, deepseek_tables)
                    deepseek_agreement = _compute_cell_agreement(docling_cells_2d, best_grid)
                    result.deepseek_agreement = deepseek_agreement
                    result.cell_count_deepseek = sum(len(row) for row in best_grid)
                    result.sources_used.append("deepseek")
                else:
                    result.errors.append("deepseek_no_tables_found")
            except Exception as e:
                result.errors.append(f"deepseek_error: {repr(e)}")
                logger.warning("deepseek_cross_validation_failed", error=repr(e))

        # Blend scores
        result.adjusted_score = _blend_scores(
            heuristic_score, granite_agreement, deepseek_agreement
        )

        elapsed_ms = (time.perf_counter() - start) * 1000
        result.validation_time_ms = round(elapsed_ms, 1)

        logger.info(
            "table_cross_validation_complete",
            heuristic=round(heuristic_score, 3),
            adjusted=round(result.adjusted_score, 3),
            granite_agreement=(
                round(granite_agreement, 3) if granite_agreement is not None else None
            ),
            deepseek_agreement=(
                round(deepseek_agreement, 3) if deepseek_agreement is not None else None
            ),
            sources=result.sources_used,
            time_ms=result.validation_time_ms,
            errors=result.errors,
        )

        return result


def _find_best_matching_table(
    docling_grid: list[list[str]],
    vlm_tables: list[list[list[str]]],
) -> list[list[str]]:
    """Find the VLM table that best matches the Docling grid by dimensions.

    When a VLM extracts multiple tables from a page, pick the one with
    the closest row/col dimensions to the Docling table.
    """
    if not vlm_tables:
        return []

    docling_rows = len(docling_grid)
    docling_cols = max((len(r) for r in docling_grid), default=0)

    best_table = vlm_tables[0]
    best_diff = float("inf")

    for table in vlm_tables:
        rows = len(table)
        cols = max((len(r) for r in table), default=0)
        diff = abs(rows - docling_rows) + abs(cols - docling_cols)
        if diff < best_diff:
            best_diff = diff
            best_table = table

    return best_table


def _compute_cell_agreement(grid_a: list[list[str]], grid_b: list[list[str]]) -> float:
    """Compute agreement between two table grids.

    Three components:
    - Dimension match (weight 0.3): min/max ratio of rows and cols
    - Content Jaccard (weight 0.5): set overlap of normalized cell texts
    - Header match (weight 0.2): first-row pairwise text match ratio

    Args:
        grid_a: First table grid (e.g., from Docling)
        grid_b: Second table grid (e.g., from VLM)

    Returns:
        Agreement score 0.0-1.0
    """
    if not grid_a or not grid_b:
        return 0.0

    rows_a, rows_b = len(grid_a), len(grid_b)
    cols_a = max((len(r) for r in grid_a), default=0)
    cols_b = max((len(r) for r in grid_b), default=0)

    if rows_a == 0 or rows_b == 0 or cols_a == 0 or cols_b == 0:
        return 0.0

    # 1. Dimension match (weight 0.3)
    row_ratio = min(rows_a, rows_b) / max(rows_a, rows_b)
    col_ratio = min(cols_a, cols_b) / max(cols_a, cols_b)
    dimension_match = (row_ratio + col_ratio) / 2.0

    # 2. Content Jaccard (weight 0.5)
    def _normalize(text: str) -> str:
        return text.strip().lower()

    cells_a = {_normalize(cell) for row in grid_a for cell in row if cell.strip()}
    cells_b = {_normalize(cell) for row in grid_b for cell in row if cell.strip()}

    if cells_a or cells_b:
        intersection = len(cells_a & cells_b)
        union = len(cells_a | cells_b)
        content_jaccard = intersection / union if union > 0 else 0.0
    else:
        content_jaccard = 0.0

    # 3. Header match (weight 0.2)
    header_a = [_normalize(c) for c in grid_a[0]] if grid_a else []
    header_b = [_normalize(c) for c in grid_b[0]] if grid_b else []

    if header_a and header_b:
        min_len = min(len(header_a), len(header_b))
        max_len = max(len(header_a), len(header_b))
        matches = sum(1 for i in range(min_len) if header_a[i] == header_b[i])
        header_match = matches / max_len if max_len > 0 else 0.0
    else:
        header_match = 0.0

    return 0.3 * dimension_match + 0.5 * content_jaccard + 0.2 * header_match


def _blend_scores(
    heuristic: float,
    granite_agreement: float | None,
    deepseek_agreement: float | None,
) -> float:
    """Blend heuristic and VLM agreement scores.

    Weighting by number of available sources:
    - 3 sources: 0.40×H + 0.30×G + 0.30×D
    - 2 sources (1 VLM): 0.50×H + 0.50×VLM
    - 1 source: H unchanged

    Agreement boost: If both VLMs agree (diff < 0.10),
    shift +0.10 from heuristic to VLMs.
    """
    vlms = []
    if granite_agreement is not None:
        vlms.append(granite_agreement)
    if deepseek_agreement is not None:
        vlms.append(deepseek_agreement)

    if len(vlms) == 0:
        return heuristic

    if len(vlms) == 1:
        return 0.50 * heuristic + 0.50 * vlms[0]

    # Both VLMs available
    g = granite_agreement  # type: ignore[assignment]
    d = deepseek_agreement  # type: ignore[assignment]

    # Base weights
    w_h, w_g, w_d = 0.40, 0.30, 0.30

    # Agreement boost: if VLMs agree closely, increase their weight
    if abs(g - d) < 0.10:
        w_h -= 0.10
        w_g += 0.05
        w_d += 0.05

    return w_h * heuristic + w_g * g + w_d * d
