"""VLM cross-validation for table quality scores.

Sprint 129.6d: Cross-validates Docling's heuristic table quality with VLM.
Sprint 129.6g (ADR-063): Updated to use Nemotron VL v1 as single VLM.
Now supports both on-demand validation (borderline tables only) and
pre-computed VLM page results (when vlm_parallel_pages_enabled=true).

Scoring (2 sources):
- 0.50×heuristic + 0.50×VLM agreement
- 1 source: heuristic unchanged (graceful degradation if VLM unavailable)
"""

import time
from dataclasses import dataclass, field

import structlog

from src.components.ingestion.vlm_table_clients import NemotronVLClient

logger = structlog.get_logger(__name__)

# Borderline range for cross-validation
BORDERLINE_LOW = 0.50
BORDERLINE_HIGH = 0.85


@dataclass
class CrossValidationResult:
    """Result of VLM cross-validation for a single table."""

    adjusted_score: float
    original_heuristic_score: float
    vlm_agreement: float | None = None
    sources_used: list[str] = field(default_factory=list)
    cell_count_docling: int = 0
    cell_count_vlm: int = 0
    header_match: float | None = None
    content_similarity: float | None = None
    validation_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    used_precomputed: bool = False


class TableCrossValidator:
    """Cross-validates table extraction using Nemotron VL v1 (ADR-063).

    Supports two modes:
    1. On-demand: Renders page image and queries VLM for borderline tables
    2. Pre-computed: Uses VLM page results from parallel page processor

    Both modes compute cell agreement and blend with heuristic score.
    """

    def __init__(self, vlm_url: str = "http://localhost:8002"):
        self._vlm = NemotronVLClient(base_url=vlm_url)
        self._vlm_available: bool | None = None

    def should_cross_validate(self, score: float) -> bool:
        """Check if a table score falls in the borderline range.

        Args:
            score: Heuristic quality score (0.0-1.0)

        Returns:
            True if score is in [0.50, 0.85] range
        """
        return BORDERLINE_LOW <= score <= BORDERLINE_HIGH

    async def check_availability(self) -> None:
        """Probe VLM service and cache availability. Call once per batch."""
        self._vlm_available = await self._vlm.health_check()
        logger.info("vlm_availability_checked", nemotron_vlm=self._vlm_available)

    async def cross_validate(
        self,
        docling_cells_2d: list[list[str]],
        page_image_bytes: bytes | None = None,
        heuristic_score: float = 0.0,
        precomputed_vlm_tables: list[list[list[str]]] | None = None,
    ) -> CrossValidationResult:
        """Cross-validate a table using Nemotron VLM.

        Two modes:
        - precomputed_vlm_tables: Use pre-extracted VLM tables (from parallel processor)
        - page_image_bytes: Query VLM on-demand (fallback for borderline-only mode)

        Args:
            docling_cells_2d: 2D cell grid from Docling extraction
            page_image_bytes: PNG image of the page (on-demand mode)
            heuristic_score: Original heuristic quality score
            precomputed_vlm_tables: VLM-extracted tables for this page (parallel mode)

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

        vlm_tables: list[list[list[str]]] | None = None

        # Mode 1: Use pre-computed VLM tables (from parallel page processor)
        if precomputed_vlm_tables is not None:
            vlm_tables = precomputed_vlm_tables
            result.used_precomputed = True
        # Mode 2: On-demand VLM query
        elif page_image_bytes is not None:
            if self._vlm_available is None:
                await self.check_availability()
            if self._vlm_available:
                try:
                    vlm_tables = await self._vlm.extract_tables_from_page(page_image_bytes)
                except Exception as e:
                    result.errors.append(f"vlm_error: {repr(e)}")
                    logger.warning("vlm_cross_validation_failed", error=repr(e))

        # Compute agreement if VLM returned tables
        vlm_agreement: float | None = None
        if vlm_tables:
            best_grid = _find_best_matching_table(docling_cells_2d, vlm_tables)
            if best_grid:
                vlm_agreement = _compute_cell_agreement(docling_cells_2d, best_grid)
                result.vlm_agreement = vlm_agreement
                result.cell_count_vlm = sum(len(row) for row in best_grid)
                result.sources_used.append("nemotron_vlm")
            else:
                result.errors.append("vlm_no_matching_table")
        elif vlm_tables is not None:
            result.errors.append("vlm_no_tables_found")

        # Blend scores
        result.adjusted_score = _blend_scores(heuristic_score, vlm_agreement)

        elapsed_ms = (time.perf_counter() - start) * 1000
        result.validation_time_ms = round(elapsed_ms, 1)

        logger.info(
            "table_cross_validation_complete",
            heuristic=round(heuristic_score, 3),
            adjusted=round(result.adjusted_score, 3),
            vlm_agreement=(round(vlm_agreement, 3) if vlm_agreement is not None else None),
            sources=result.sources_used,
            time_ms=result.validation_time_ms,
            precomputed=result.used_precomputed,
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


def _blend_scores(heuristic: float, vlm_agreement: float | None) -> float:
    """Blend heuristic and VLM agreement scores (ADR-063: single VLM).

    Weighting:
    - 2 sources: 0.50×heuristic + 0.50×VLM
    - 1 source: heuristic unchanged (graceful degradation)
    """
    if vlm_agreement is None:
        return heuristic
    return 0.50 * heuristic + 0.50 * vlm_agreement
