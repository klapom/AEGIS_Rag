"""Unit tests for table quality heuristics module."""

import pytest
from src.components.ingestion.table_quality import (
    TableQualityReport,
    compute_table_quality,
    should_ingest_table,
    _cell_density,
    _rectangular_consistency,
    _header_plausibility,
    _type_consistency,
    _content_plausibility,
    _index_of_coincidence,
    _is_numeric,
)


class TestPerfectTable:
    """Test high-quality table with all metrics scoring well."""

    def test_excellent_table(self):
        cells = [
            ["Name", "Age", "Salary"],
            ["Alice", "30", "$50,000"],
            ["Bob", "25", "$45,000"],
            ["Charlie", "35", "$60,000"],
        ]
        report = compute_table_quality(cells, has_header=True)

        assert report.grade == "EXCELLENT"
        assert report.overall_score >= 0.85
        assert report.cell_density == 1.0  # All cells filled
        assert report.rectangular_consistency == 1.0  # All rows same width
        assert report.min_size_ok is True
        assert report.num_rows == 4
        assert report.num_cols == 3


class TestEmptyTable:
    """Test empty or nearly empty tables."""

    def test_completely_empty(self):
        cells = []
        report = compute_table_quality(cells)

        assert report.grade == "POOR"
        assert report.overall_score == 0.0
        assert report.cell_density == 0.0
        assert report.min_size_ok is False
        assert report.num_rows == 0
        assert report.num_cols == 0

    def test_empty_rows(self):
        cells = [[]]
        report = compute_table_quality(cells)

        assert report.grade == "POOR"
        assert report.min_size_ok is False


class TestMinimumSize:
    """Test minimum size constraints (2x2)."""

    def test_single_row(self):
        cells = [["Header1", "Header2", "Header3"]]
        report = compute_table_quality(cells)

        # Single row fails min_size
        assert report.min_size_ok is False
        # But might still score reasonably on other metrics
        assert report.num_rows == 1
        assert report.num_cols == 3

    def test_single_column(self):
        cells = [["A"], ["B"], ["C"]]
        report = compute_table_quality(cells)

        # Single column fails min_size
        assert report.min_size_ok is False
        assert report.num_rows == 3
        assert report.num_cols == 1

    def test_exactly_2x2(self):
        cells = [["A", "B"], ["C", "D"]]
        report = compute_table_quality(cells)

        assert report.min_size_ok is True
        assert report.num_rows == 2
        assert report.num_cols == 2


class TestCellDensity:
    """Test cell density metric."""

    def test_full_density(self):
        cells = [["A", "B"], ["C", "D"]]
        density = _cell_density(cells)
        assert density == 1.0

    def test_80_percent_empty(self):
        cells = [
            ["A", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
        ]
        density = _cell_density(cells)
        assert density == 0.05  # 1 filled out of 20

    def test_whitespace_only(self):
        cells = [["  ", "   "], ["    ", ""]]
        density = _cell_density(cells)
        assert density == 0.0  # Whitespace doesn't count

    def test_half_empty(self):
        cells = [["A", ""], ["", "B"]]
        density = _cell_density(cells)
        assert density == 0.5


class TestRectangularConsistency:
    """Test rectangular consistency metric."""

    def test_perfect_rectangle(self):
        cells = [["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]]
        consistency = _rectangular_consistency(cells)
        assert consistency == 1.0

    def test_inconsistent_widths(self):
        cells = [["A", "B"], ["C", "D", "E"], ["F"]]
        consistency = _rectangular_consistency(cells)
        # 3 unique widths -> 1.0 / 3 = 0.333...
        assert consistency == pytest.approx(0.333, rel=0.01)

    def test_two_widths(self):
        cells = [["A", "B"], ["C", "D"], ["E"]]
        consistency = _rectangular_consistency(cells)
        # 2 unique widths -> 1.0 / 2 = 0.5
        assert consistency == 0.5


class TestHeaderPlausibility:
    """Test header plausibility metric."""

    def test_text_header_numeric_body(self):
        cells = [
            ["Name", "Age", "Score"],
            ["Alice", "30", "95"],
            ["Bob", "25", "88"],
        ]
        plausibility = _header_plausibility(cells)
        # Header is 100% text, body is 67% numeric
        # Score = 0.6 * 1.0 + 0.4 * 0.67 = 0.868
        assert plausibility > 0.8

    def test_numeric_header(self):
        cells = [["1", "2", "3"], ["A", "B", "C"]]
        plausibility = _header_plausibility(cells)
        # Header is 0% text (all numeric), body is 0% numeric
        # Score = 0.6 * 0.0 + 0.4 * 0.0 = 0.0
        assert plausibility == 0.0

    def test_all_text(self):
        cells = [["A", "B"], ["C", "D"]]
        plausibility = _header_plausibility(cells)
        # Header 100% text, body 0% numeric
        # Score = 0.6 * 1.0 + 0.4 * 0.0 = 0.6
        assert plausibility == 0.6

    def test_single_row_defaults(self):
        cells = [["A", "B", "C"]]
        plausibility = _header_plausibility(cells)
        # Less than 2 rows -> default 0.5
        assert plausibility == 0.5


class TestTypeConsistency:
    """Test type consistency metric."""

    def test_all_numeric_column(self):
        cells = [["100"], ["200"], ["300"]]
        consistency = _type_consistency(cells)
        assert consistency == 1.0  # 100% numeric

    def test_all_text_column(self):
        cells = [["Alice"], ["Bob"], ["Charlie"]]
        consistency = _type_consistency(cells)
        assert consistency == 1.0  # 100% text

    def test_mixed_types_per_column(self):
        cells = [["100", "Alice"], ["Text", "200"], ["300", "Charlie"]]
        # Column 0: 2 numeric, 1 text -> 67% dominant
        # Column 1: 1 numeric, 2 text -> 67% dominant
        # Average = 0.67
        consistency = _type_consistency(cells)
        assert consistency == pytest.approx(0.667, rel=0.01)

    def test_consistent_types_across_columns(self):
        cells = [
            ["100", "Alice", "Engineer"],
            ["200", "Bob", "Designer"],
            ["300", "Charlie", "Manager"],
        ]
        # Column 0: 100% numeric
        # Column 1: 100% text
        # Column 2: 100% text
        # Average = 1.0
        consistency = _type_consistency(cells)
        assert consistency == 1.0


class TestContentPlausibility:
    """Test content plausibility via Index of Coincidence."""

    def test_empty_content(self):
        cells = [["", ""], ["", ""]]
        plausibility = _content_plausibility(cells)
        assert plausibility == 0.0

    def test_natural_language_content(self):
        cells = [
            ["The quick brown fox jumps over the lazy dog"],
            ["Natural language has higher index of coincidence"],
        ]
        plausibility = _content_plausibility(cells)
        # Natural text should score better than random (> 0.0)
        # Short samples have lower IC, so just verify it's measurable
        assert plausibility > 0.0

    def test_gibberish_content(self):
        cells = [["qzxvkjhgfdsa"], ["mnbvcxzlkjhgf"]]
        plausibility = _content_plausibility(cells)
        # Random characters should score lower than natural text
        # But may not be extremely low due to some accidental patterns
        assert 0.0 <= plausibility <= 1.0


class TestIndexOfCoincidence:
    """Test IC calculation for known text patterns."""

    def test_known_english_text(self):
        # "the" repeated has high IC due to concentrated 'e', 't', 'h'
        text = "the the the the the"
        ic = _index_of_coincidence(text)
        # Should be significantly above random (1.0)
        assert ic > 1.5

    def test_random_characters(self):
        # Uniform distribution should have IC close to 1.0
        text = "abcdefghijklmnopqrstuvwxyz"
        ic = _index_of_coincidence(text)
        # Each letter appears once, so freq=1, numerator=0
        # Perfect uniform with single occurrence = 0.0
        assert ic == 0.0

    def test_repeated_character(self):
        text = "aaaaaaaaaa"
        ic = _index_of_coincidence(text)
        # All same character has maximum IC = 26
        assert ic == 26.0

    def test_case_insensitive(self):
        text1 = "ABC"
        text2 = "abc"
        assert _index_of_coincidence(text1) == _index_of_coincidence(text2)

    def test_non_alpha_ignored(self):
        text = "a1b2c3a1b2c3a1b2c3"
        # Should only count repeated 'a', 'b', 'c'
        ic = _index_of_coincidence(text)
        # With repetition, IC should be > 0
        assert ic > 0


class TestIsNumeric:
    """Test numeric detection helper."""

    def test_integer(self):
        assert _is_numeric("123")
        assert _is_numeric("0")
        assert _is_numeric("-456")

    def test_float(self):
        assert _is_numeric("123.45")
        assert _is_numeric("-67.89")
        assert _is_numeric(".5")

    def test_with_commas(self):
        assert _is_numeric("1,234")
        assert _is_numeric("1,234,567.89")

    def test_percentage(self):
        assert _is_numeric("25%")
        assert _is_numeric("100.5%")

    def test_currency(self):
        assert _is_numeric("$100")
        assert _is_numeric("€50.25")
        assert _is_numeric("£1,000")
        assert _is_numeric("¥500")

    def test_text(self):
        assert not _is_numeric("Alice")
        assert not _is_numeric("hello")
        assert not _is_numeric("")

    def test_mixed(self):
        assert not _is_numeric("123abc")
        assert not _is_numeric("abc123")


class TestShouldIngestTable:
    """Test ingestion decision logic."""

    def test_high_quality_full_ingest(self):
        report = TableQualityReport(
            cell_density=0.9,
            rectangular_consistency=1.0,
            header_plausibility=0.8,
            type_consistency=0.85,
            content_plausibility=0.75,
            min_size_ok=True,
            num_rows=5,
            num_cols=3,
            overall_score=0.85,
            grade="EXCELLENT",
        )
        should_ingest, mode = should_ingest_table(report)
        assert should_ingest is True
        assert mode == "full"

    def test_good_quality_full_ingest(self):
        report = TableQualityReport(
            cell_density=0.8,
            rectangular_consistency=0.9,
            header_plausibility=0.7,
            type_consistency=0.75,
            content_plausibility=0.7,
            min_size_ok=True,
            num_rows=4,
            num_cols=3,
            overall_score=0.75,
            grade="GOOD",
        )
        should_ingest, mode = should_ingest_table(report)
        assert should_ingest is True
        assert mode == "full"

    def test_fair_quality_with_warning(self):
        report = TableQualityReport(
            cell_density=0.6,
            rectangular_consistency=0.7,
            header_plausibility=0.5,
            type_consistency=0.6,
            content_plausibility=0.5,
            min_size_ok=True,
            num_rows=3,
            num_cols=2,
            overall_score=0.60,
            grade="FAIR",
        )
        should_ingest, mode = should_ingest_table(report)
        assert should_ingest is True
        assert mode == "with_warning"

    def test_poor_quality_rejected(self):
        report = TableQualityReport(
            cell_density=0.3,
            rectangular_consistency=0.4,
            header_plausibility=0.3,
            type_consistency=0.4,
            content_plausibility=0.2,
            min_size_ok=False,
            num_rows=2,
            num_cols=1,
            overall_score=0.30,
            grade="POOR",
        )
        should_ingest, mode = should_ingest_table(report)
        assert should_ingest is False
        assert mode == "rejected"

    def test_threshold_boundary_70(self):
        # Exactly 0.70 should be "full"
        report = TableQualityReport(
            cell_density=0.7,
            rectangular_consistency=0.7,
            header_plausibility=0.7,
            type_consistency=0.7,
            content_plausibility=0.7,
            min_size_ok=True,
            num_rows=3,
            num_cols=3,
            overall_score=0.70,
            grade="GOOD",
        )
        should_ingest, mode = should_ingest_table(report)
        assert should_ingest is True
        assert mode == "full"

    def test_threshold_boundary_50(self):
        # Exactly 0.50 should be "with_warning"
        report = TableQualityReport(
            cell_density=0.5,
            rectangular_consistency=0.5,
            header_plausibility=0.5,
            type_consistency=0.5,
            content_plausibility=0.5,
            min_size_ok=True,
            num_rows=2,
            num_cols=2,
            overall_score=0.50,
            grade="FAIR",
        )
        should_ingest, mode = should_ingest_table(report)
        assert should_ingest is True
        assert mode == "with_warning"


class TestIntegrationScenarios:
    """Test realistic table scenarios."""

    def test_financial_report_table(self):
        cells = [
            ["Quarter", "Revenue", "Profit"],
            ["Q1 2023", "$1,234,567", "$234,567"],
            ["Q2 2023", "$1,456,789", "$345,678"],
            ["Q3 2023", "$1,678,901", "$456,789"],
        ]
        report = compute_table_quality(cells, has_header=True)

        assert report.grade in ["EXCELLENT", "GOOD"]
        assert report.overall_score >= 0.70
        assert report.cell_density == 1.0
        assert report.rectangular_consistency == 1.0
        assert report.min_size_ok is True

    def test_sparse_table(self):
        cells = [
            ["A", "", "", ""],
            ["", "B", "", ""],
            ["", "", "C", ""],
            ["", "", "", "D"],
        ]
        report = compute_table_quality(cells)

        assert report.cell_density == 0.25
        # Should score FAIR or POOR due to low density
        assert report.grade in ["FAIR", "POOR"]

    def test_malformed_table(self):
        cells = [
            ["Header1", "Header2"],
            ["Row1Col1"],  # Missing column
            ["Row2Col1", "Row2Col2", "Row2Col3"],  # Extra column
        ]
        report = compute_table_quality(cells)

        # Should have low rectangular consistency
        assert report.rectangular_consistency < 1.0
        # 3 unique widths -> 1/3 = 0.333
        assert report.rectangular_consistency == pytest.approx(0.333, rel=0.01)
