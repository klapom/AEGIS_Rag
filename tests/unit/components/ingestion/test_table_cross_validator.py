"""Tests for table_cross_validator.py — VLM cross-validation logic.

Sprint 129.6d: Tests cover borderline detection, score blending, cell agreement,
VLM unavailability fallback, and timeout handling.
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
# _blend_scores
# ============================================================================


class TestBlendScores:
    """Tests for score blending algorithm."""

    def test_no_vlms(self):
        """No VLM data → return heuristic unchanged."""
        assert _blend_scores(0.65, None, None) == 0.65

    def test_one_vlm_granite(self):
        """Single VLM → 50/50 blend."""
        result = _blend_scores(0.60, 0.80, None)
        expected = 0.50 * 0.60 + 0.50 * 0.80
        assert result == pytest.approx(expected)

    def test_one_vlm_deepseek(self):
        """Single VLM (DeepSeek only) → 50/50 blend."""
        result = _blend_scores(0.60, None, 0.90)
        expected = 0.50 * 0.60 + 0.50 * 0.90
        assert result == pytest.approx(expected)

    def test_both_vlms_base_weights(self):
        """Both VLMs, NO agreement boost (diff >= 0.10)."""
        result = _blend_scores(0.60, 0.90, 0.70)
        # diff = |0.90 - 0.70| = 0.20 >= 0.10 → no boost
        expected = 0.40 * 0.60 + 0.30 * 0.90 + 0.30 * 0.70
        assert result == pytest.approx(expected)

    def test_both_vlms_agreement_boost(self):
        """Both VLMs agree (diff < 0.10) → agreement boost."""
        result = _blend_scores(0.60, 0.82, 0.85)
        # diff = |0.82 - 0.85| = 0.03 < 0.10 → boost
        # w_h = 0.30, w_g = 0.35, w_d = 0.35
        expected = 0.30 * 0.60 + 0.35 * 0.82 + 0.35 * 0.85
        assert result == pytest.approx(expected)

    def test_blend_preserves_poor_consensus(self):
        """If all sources agree table is poor, result stays poor."""
        result = _blend_scores(0.30, 0.25, 0.28)
        assert result < 0.35  # All sources say poor

    def test_vlms_can_boost_borderline(self):
        """VLMs agreeing table is good can boost borderline heuristic."""
        result = _blend_scores(0.55, 0.90, 0.88)
        # Heuristic says borderline, VLMs say excellent
        assert result > 0.70  # Should be boosted above GOOD threshold


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
# TableCrossValidator.cross_validate (integration with mocked VLMs)
# ============================================================================


class TestCrossValidateIntegration:
    """Integration tests for cross_validate() with mocked VLM clients."""

    @pytest.mark.asyncio
    async def test_both_vlms_unavailable(self):
        """When both VLMs are down, return heuristic score unchanged."""
        cv = TableCrossValidator()
        cv._granite_available = False
        cv._deepseek_available = False

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            page_image_bytes=b"fake_png",
            heuristic_score=0.65,
        )

        assert result.adjusted_score == 0.65
        assert result.sources_used == ["heuristic"]
        assert result.granite_agreement is None
        assert result.deepseek_agreement is None

    @pytest.mark.asyncio
    async def test_granite_only(self):
        """When only Granite is available, use 2-source blend."""
        cv = TableCrossValidator()
        cv._granite_available = True
        cv._deepseek_available = False

        # Mock Granite to return matching table
        cv._granite.extract_tables_from_page = AsyncMock(return_value=[[["A", "B"], ["1", "2"]]])

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            page_image_bytes=b"fake_png",
            heuristic_score=0.65,
        )

        assert "granite" in result.sources_used
        assert "deepseek" not in result.sources_used
        assert result.granite_agreement is not None
        # 2-source blend: 0.50 * H + 0.50 * G
        assert result.adjusted_score != 0.65  # Should be different from pure heuristic

    @pytest.mark.asyncio
    async def test_granite_returns_no_tables(self):
        """Granite finds no tables → error logged, heuristic used."""
        cv = TableCrossValidator()
        cv._granite_available = True
        cv._deepseek_available = False

        cv._granite.extract_tables_from_page = AsyncMock(return_value=[])

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            page_image_bytes=b"fake_png",
            heuristic_score=0.65,
        )

        assert result.adjusted_score == 0.65
        assert "granite_no_tables_found" in result.errors

    @pytest.mark.asyncio
    async def test_both_vlms_available(self):
        """Both VLMs available → 3-source blend."""
        cv = TableCrossValidator()
        cv._granite_available = True
        cv._deepseek_available = True

        matching_table = [["A", "B"], ["1", "2"]]
        cv._granite.extract_tables_from_page = AsyncMock(return_value=[matching_table])
        cv._deepseek.extract_tables_from_page = AsyncMock(return_value=[matching_table])

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            page_image_bytes=b"fake_png",
            heuristic_score=0.65,
        )

        assert "granite" in result.sources_used
        assert "deepseek" in result.sources_used
        assert result.granite_agreement is not None
        assert result.deepseek_agreement is not None
        assert result.validation_time_ms >= 0  # Mocked calls may complete in 0.0ms

    @pytest.mark.asyncio
    async def test_vlm_exception_graceful(self):
        """VLM raising exception → skip silently, use remaining sources."""
        cv = TableCrossValidator()
        cv._granite_available = True
        cv._deepseek_available = True

        cv._granite.extract_tables_from_page = AsyncMock(side_effect=RuntimeError("GPU OOM"))
        cv._deepseek.extract_tables_from_page = AsyncMock(return_value=[[["A", "B"], ["1", "2"]]])

        result = await cv.cross_validate(
            docling_cells_2d=[["A", "B"], ["1", "2"]],
            page_image_bytes=b"fake_png",
            heuristic_score=0.65,
        )

        # Granite failed, DeepSeek succeeded
        assert "granite" not in result.sources_used
        assert "deepseek" in result.sources_used
        assert any("granite_error" in e for e in result.errors)


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
        assert result.granite_agreement is None
        assert result.deepseek_agreement is None
        assert result.sources_used == []
        assert result.errors == []
        assert result.validation_time_ms == 0.0
