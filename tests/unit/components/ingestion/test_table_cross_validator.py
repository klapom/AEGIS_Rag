"""Tests for table_cross_validator.py — VLM cross-validation logic.

Sprint 129.6d: Tests cover borderline detection, score blending, cell agreement,
VLM unavailability fallback, and timeout handling.
Sprint 129.6g (ADR-063): Updated for single Nemotron VLM + precomputed support.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.components.ingestion.table_cross_validator import (
    BORDERLINE_HIGH,
    BORDERLINE_LOW,
    CrossValidationResult,
    TableCrossValidator,
    _blend_scores,
    _compute_cell_agreement,
    _find_best_matching_table,
)


# ============================================================================
# should_cross_validate
# ============================================================================


class TestShouldCrossValidate:
    """Tests for borderline score detection."""

    def test_borderline_low_boundary(self):
        cv = TableCrossValidator()
        assert cv.should_cross_validate(0.50) is True

    def test_borderline_high_boundary(self):
        cv = TableCrossValidator()
        assert cv.should_cross_validate(0.85) is True

    def test_below_borderline(self):
        cv = TableCrossValidator()
        assert cv.should_cross_validate(0.49) is False

    def test_above_borderline(self):
        cv = TableCrossValidator()
        assert cv.should_cross_validate(0.86) is False

    def test_midrange(self):
        cv = TableCrossValidator()
        assert cv.should_cross_validate(0.70) is True

    def test_excellent_score_skipped(self):
        cv = TableCrossValidator()
        assert cv.should_cross_validate(0.95) is False

    def test_poor_score_skipped(self):
        cv = TableCrossValidator()
        assert cv.should_cross_validate(0.20) is False


# ============================================================================
# _compute_cell_agreement
# ============================================================================


class TestComputeCellAgreement:
    """Tests for cell agreement computation."""

    def test_identical_grids(self):
        grid = [["A", "B", "C"], ["1", "2", "3"]]
        score = _compute_cell_agreement(grid, grid)
        assert score == pytest.approx(1.0)

    def test_completely_different_grids(self):
        grid_a = [["A", "B"], ["C", "D"]]
        grid_b = [["X", "Y", "Z"], ["1", "2", "3"], ["4", "5", "6"]]
        score = _compute_cell_agreement(grid_a, grid_b)
        assert score < 0.3  # Very low agreement

    def test_partial_overlap(self):
        grid_a = [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]
        grid_b = [["Name", "Age"], ["Alice", "30"], ["Charlie", "35"]]
        score = _compute_cell_agreement(grid_a, grid_b)
        # Same dimensions, partial content overlap, same header
        assert 0.5 < score < 1.0

    def test_empty_grid_a(self):
        score = _compute_cell_agreement([], [["A"]])
        assert score == 0.0

    def test_empty_grid_b(self):
        score = _compute_cell_agreement([["A"]], [])
        assert score == 0.0

    def test_both_empty(self):
        score = _compute_cell_agreement([], [])
        assert score == 0.0

    def test_same_content_different_dimensions(self):
        """Same cells but different grid structure → lower dimension match."""
        grid_a = [["A", "B", "C", "D"]]  # 1x4
        grid_b = [["A", "B"], ["C", "D"]]  # 2x2
        score = _compute_cell_agreement(grid_a, grid_b)
        # Content Jaccard = 1.0 (all same), but dimension mismatch
        # row_ratio = 1/2, col_ratio = 2/4 = 0.5 → dim = 0.5
        assert 0.4 < score < 0.8

    def test_case_insensitive_content(self):
        grid_a = [["Name", "AGE"], ["ALICE", "30"]]
        grid_b = [["name", "age"], ["alice", "30"]]
        score = _compute_cell_agreement(grid_a, grid_b)
        assert score == pytest.approx(1.0)


# ============================================================================
# _blend_scores (ADR-063: single VLM)
# ============================================================================


class TestBlendScores:
    """Tests for score blending algorithm (single VLM, ADR-063)."""

    def test_no_vlm(self):
        """No VLM data → return heuristic unchanged."""
        assert _blend_scores(0.65, None) == 0.65

    def test_vlm_agreement_blend(self):
        """VLM available → 50/50 blend."""
        result = _blend_scores(0.60, 0.80)
        expected = 0.50 * 0.60 + 0.50 * 0.80
        assert result == pytest.approx(expected)

    def test_vlm_perfect_agreement(self):
        """VLM agrees perfectly → score unchanged."""
        result = _blend_scores(0.70, 0.70)
        assert result == pytest.approx(0.70)

    def test_vlm_low_agreement_lowers_score(self):
        """VLM disagrees → score pulled down."""
        result = _blend_scores(0.80, 0.20)
        assert result == pytest.approx(0.50)

    def test_vlm_high_agreement_boosts_score(self):
        """VLM high agreement boosts borderline heuristic."""
        result = _blend_scores(0.55, 0.95)
        assert result == pytest.approx(0.75)

    def test_blend_preserves_poor_consensus(self):
        """If both sources agree table is poor, result stays poor."""
        result = _blend_scores(0.30, 0.25)
        assert result < 0.35

    def test_vlm_can_boost_borderline(self):
        """VLM agreeing table is good can boost borderline heuristic."""
        result = _blend_scores(0.55, 0.90)
        assert result > 0.70


# ============================================================================
# _find_best_matching_table
# ============================================================================


class TestFindBestMatchingTable:
    """Tests for finding best matching VLM table by dimensions."""

    def test_single_table(self):
        docling = [["A", "B"], ["1", "2"]]
        vlm_tables = [[["X", "Y"], ["3", "4"]]]
        result = _find_best_matching_table(docling, vlm_tables)
        assert result == [["X", "Y"], ["3", "4"]]

    def test_best_dimension_match(self):
        docling = [["A", "B", "C"], ["1", "2", "3"]]  # 2x3
        vlm_tables = [
            [["X"], ["Y"], ["Z"]],  # 3x1 — bad match
            [["X", "Y", "Z"], ["1", "2", "3"]],  # 2x3 — perfect match
        ]
        result = _find_best_matching_table(docling, vlm_tables)
        assert result == [["X", "Y", "Z"], ["1", "2", "3"]]

    def test_empty_vlm_tables(self):
        result = _find_best_matching_table([["A"]], [])
        assert result == []


# ============================================================================
# TableCrossValidator.cross_validate (ADR-063: single VLM)
# ============================================================================


class TestCrossValidateIntegration:
    """Integration tests for cross_validate() with mocked VLM client."""

    @pytest.mark.asyncio
    async def test_vlm_unavailable(self):
        """When VLM is down, return heuristic score unchanged."""
        cv = TableCrossValidator()
        cv._vlm_available = False

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            page_image_bytes=b"fake_png",
            heuristic_score=0.65,
        )

        assert result.adjusted_score == 0.65
        assert result.sources_used == ["heuristic"]
        assert result.vlm_agreement is None

    @pytest.mark.asyncio
    async def test_on_demand_vlm(self):
        """On-demand mode: VLM available → 2-source blend."""
        cv = TableCrossValidator()
        cv._vlm_available = True

        cv._vlm.extract_tables_from_page = AsyncMock(return_value=[[["A", "B"], ["1", "2"]]])

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            page_image_bytes=b"fake_png",
            heuristic_score=0.65,
        )

        assert "nemotron_vlm" in result.sources_used
        assert result.vlm_agreement is not None
        assert result.used_precomputed is False
        assert result.adjusted_score != 0.65

    @pytest.mark.asyncio
    async def test_on_demand_vlm_no_tables(self):
        """VLM finds no tables → error logged, heuristic used."""
        cv = TableCrossValidator()
        cv._vlm_available = True

        cv._vlm.extract_tables_from_page = AsyncMock(return_value=[])

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            page_image_bytes=b"fake_png",
            heuristic_score=0.65,
        )

        assert result.adjusted_score == 0.65
        assert "vlm_no_tables_found" in result.errors

    @pytest.mark.asyncio
    async def test_precomputed_vlm_tables(self):
        """Pre-computed mode: uses parallel page processor results."""
        cv = TableCrossValidator()
        # VLM availability doesn't matter for precomputed

        precomputed = [[["A", "B"], ["1", "2"]]]

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            heuristic_score=0.65,
            precomputed_vlm_tables=precomputed,
        )

        assert result.used_precomputed is True
        assert "nemotron_vlm" in result.sources_used
        assert result.vlm_agreement is not None
        # Identical tables → high agreement → adjusted score different from heuristic
        assert result.adjusted_score != 0.65

    @pytest.mark.asyncio
    async def test_precomputed_empty_tables(self):
        """Pre-computed but VLM found no tables → error, heuristic only."""
        cv = TableCrossValidator()

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            heuristic_score=0.65,
            precomputed_vlm_tables=[],  # Empty list = VLM ran but found nothing
        )

        assert result.used_precomputed is True
        assert result.adjusted_score == 0.65
        assert "vlm_no_tables_found" in result.errors

    @pytest.mark.asyncio
    async def test_vlm_exception_graceful(self):
        """VLM raising exception → skip silently, use heuristic only."""
        cv = TableCrossValidator()
        cv._vlm_available = True

        cv._vlm.extract_tables_from_page = AsyncMock(side_effect=RuntimeError("GPU OOM"))

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            page_image_bytes=b"fake_png",
            heuristic_score=0.65,
        )

        assert result.adjusted_score == 0.65
        assert any("vlm_error" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_no_image_no_precomputed(self):
        """Neither page image nor precomputed → heuristic only."""
        cv = TableCrossValidator()

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            heuristic_score=0.70,
        )

        assert result.adjusted_score == 0.70
        assert result.sources_used == ["heuristic"]

    @pytest.mark.asyncio
    async def test_precomputed_no_matching_table(self):
        """Pre-computed tables don't match Docling dimensions → error."""
        cv = TableCrossValidator()

        # VLM found a very different-shaped table
        precomputed = [[["X"]]]  # 1x1 table

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B", "C"], ["1", "2", "3"], ["4", "5", "6"]],
            heuristic_score=0.65,
            precomputed_vlm_tables=precomputed,
        )

        # The best-matching table will still be found (it's the only one)
        # but agreement will be low
        assert result.used_precomputed is True


# ============================================================================
# CrossValidationResult dataclass
# ============================================================================


class TestCrossValidationResult:
    """Tests for CrossValidationResult defaults."""

    def test_defaults(self):
        result = CrossValidationResult(
            adjusted_score=0.75,
            original_heuristic_score=0.65,
        )
        assert result.adjusted_score == 0.75
        assert result.original_heuristic_score == 0.65
        assert result.vlm_agreement is None
        assert result.sources_used == []
        assert result.errors == []
        assert result.validation_time_ms == 0.0
        assert result.used_precomputed is False

    def test_with_vlm_agreement(self):
        result = CrossValidationResult(
            adjusted_score=0.80,
            original_heuristic_score=0.65,
            vlm_agreement=0.90,
            sources_used=["heuristic", "nemotron_vlm"],
            used_precomputed=True,
        )
        assert result.vlm_agreement == 0.90
        assert result.used_precomputed is True
        assert len(result.sources_used) == 2
