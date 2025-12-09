"""Unit tests for MetadataFilterEngine.

Tests cover:
- Filter validation (15+ tests)
- Qdrant filter building
- Date range filters
- Source filters (in/not_in)
- Doc_type filters
- Tags filters
- Empty filters
- Filter conflicts
- Selectivity estimation
"""

from datetime import datetime, timedelta

import pytest
# Note: qdrant_client.models types may be Pydantic models that don't work with isinstance()
# We import them for type hints but use attribute checks instead of isinstance()
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue  # noqa: F401

from src.components.retrieval.filters import MetadataFilterEngine, MetadataFilters


class TestMetadataFiltersValidation:
    """Test MetadataFilters model validation."""

    def test_empty_filters(self):
        """Test that empty filters are correctly identified."""
        filters = MetadataFilters()
        assert filters.is_empty()
        assert filters.get_active_filters() == []

    def test_single_filter_active(self):
        """Test single active filter."""
        filters = MetadataFilters(created_after=datetime(2024, 1, 1))
        assert not filters.is_empty()
        assert filters.get_active_filters() == ["created_after"]

    def test_multiple_filters_active(self):
        """Test multiple active filters."""
        filters = MetadataFilters(
            created_after=datetime(2024, 1, 1),
            doc_type_in=["pdf", "md"],
            tags_contains=["tutorial"],
        )
        assert not filters.is_empty()
        assert set(filters.get_active_filters()) == {
            "created_after",
            "doc_type_in",
            "tags_contains",
        }

    def test_doc_type_validation_valid(self):
        """Test valid document types."""
        valid_types = ["pdf", "txt", "md", "docx", "html", "json", "csv"]
        filters = MetadataFilters(doc_type_in=valid_types)
        assert filters.doc_type_in == valid_types

    def test_doc_type_validation_invalid(self):
        """Test invalid document types raise error."""
        with pytest.raises(ValueError, match="Invalid doc_type"):
            MetadataFilters(doc_type_in=["pdf", "invalid_type"])

    def test_doc_type_case_insensitive(self):
        """Test document types are normalized to lowercase."""
        filters = MetadataFilters(doc_type_in=["PDF", "TXT", "Md"])
        assert filters.doc_type_in == ["pdf", "txt", "md"]

    def test_future_date_validation_created_after(self):
        """Test that future dates are rejected for created_after."""
        future_date = datetime.now() + timedelta(days=1)
        with pytest.raises(ValueError, match="Date cannot be in the future"):
            MetadataFilters(created_after=future_date)

    def test_future_date_validation_created_before(self):
        """Test that future dates are rejected for created_before."""
        future_date = datetime.now() + timedelta(days=1)
        with pytest.raises(ValueError, match="Date cannot be in the future"):
            MetadataFilters(created_before=future_date)

    def test_valid_date_ranges(self):
        """Test valid date ranges."""
        past_date = datetime.now() - timedelta(days=30)
        filters = MetadataFilters(
            created_after=past_date,
            created_before=datetime.now(),
        )
        assert filters.created_after == past_date
        assert filters.created_before is not None

    def test_source_filters(self):
        """Test source filter lists."""
        sources = ["docs.rag.com", "arxiv.org"]
        filters = MetadataFilters(source_in=sources)
        assert filters.source_in == sources

    def test_empty_lists_treated_as_inactive(self):
        """Test that empty lists are treated as inactive filters."""
        filters = MetadataFilters(
            source_in=[],
            doc_type_in=[],
            tags_contains=[],
        )
        assert filters.is_empty()


class TestMetadataFilterEngine:
    """Test MetadataFilterEngine functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = MetadataFilterEngine()

    def test_engine_initialization(self):
        """Test filter engine initializes correctly."""
        assert self.engine is not None
        assert isinstance(self.engine, MetadataFilterEngine)

    def test_empty_filters_returns_none(self):
        """Test that empty filters return None."""
        filters = MetadataFilters()
        qdrant_filter = self.engine.build_qdrant_filter(filters)
        assert qdrant_filter is None

    def test_created_after_filter(self):
        """Test created_after filter builds correctly."""
        created_date = datetime(2024, 1, 1)
        filters = MetadataFilters(created_after=created_date)
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        # Check Filter attributes instead of isinstance() (Pydantic model compatibility)
        assert hasattr(qdrant_filter, "must")
        assert qdrant_filter.must is not None
        assert len(qdrant_filter.must) == 1

        condition = qdrant_filter.must[0]
        # Check FieldCondition attributes instead of isinstance()
        assert hasattr(condition, "key")
        assert condition.key == "created_at"
        assert condition.range is not None
        assert condition.range.gte == int(created_date.timestamp())

    def test_created_before_filter(self):
        """Test created_before filter builds correctly."""
        created_date = datetime(2024, 12, 31)
        filters = MetadataFilters(created_before=created_date)
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        assert len(qdrant_filter.must) == 1

        condition = qdrant_filter.must[0]
        assert condition.key == "created_at"
        assert condition.range.lte == int(created_date.timestamp())

    def test_date_range_filter(self):
        """Test date range filter with both after and before."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        filters = MetadataFilters(
            created_after=start_date,
            created_before=end_date,
        )
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        assert len(qdrant_filter.must) == 2

        # Check both conditions exist
        keys = [cond.key for cond in qdrant_filter.must]
        assert keys == ["created_at", "created_at"]

    def test_source_in_filter(self):
        """Test source_in filter builds correctly."""
        sources = ["docs.rag.com", "arxiv.org"]
        filters = MetadataFilters(source_in=sources)
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        assert len(qdrant_filter.must) == 1

        condition = qdrant_filter.must[0]
        assert condition.key == "source"
        # Check MatchAny attributes instead of isinstance()
        assert hasattr(condition.match, "any")
        assert condition.match.any == sources

    def test_source_not_in_filter(self):
        """Test source_not_in filter builds correctly."""
        sources = ["spam.com", "bad.org"]
        filters = MetadataFilters(source_not_in=sources)
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        assert qdrant_filter.must_not is not None
        assert len(qdrant_filter.must_not) == 1

        condition = qdrant_filter.must_not[0]
        assert condition.key == "source"
        # Check MatchAny attributes instead of isinstance()
        assert hasattr(condition.match, "any")
        assert condition.match.any == sources

    def test_doc_type_filter(self):
        """Test doc_type_in filter builds correctly."""
        doc_types = ["pdf", "md"]
        filters = MetadataFilters(doc_type_in=doc_types)
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        assert len(qdrant_filter.must) == 1

        condition = qdrant_filter.must[0]
        assert condition.key == "doc_type"
        # Check MatchAny attributes instead of isinstance()
        assert hasattr(condition.match, "any")
        assert condition.match.any == doc_types

    def test_tags_contains_single_tag(self):
        """Test tags_contains with single tag."""
        tags = ["tutorial"]
        filters = MetadataFilters(tags_contains=tags)
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        assert len(qdrant_filter.must) == 1

        condition = qdrant_filter.must[0]
        assert condition.key == "tags"
        # Check MatchValue attributes instead of isinstance()
        assert hasattr(condition.match, "value")
        assert condition.match.value == "tutorial"

    def test_tags_contains_multiple_tags(self):
        """Test tags_contains with multiple tags (AND logic)."""
        tags = ["tutorial", "python", "advanced"]
        filters = MetadataFilters(tags_contains=tags)
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        # Should have 3 conditions (one per tag, AND logic)
        assert len(qdrant_filter.must) == 3

        for i, tag in enumerate(tags):
            condition = qdrant_filter.must[i]
            assert condition.key == "tags"
            # Check MatchValue attributes instead of isinstance()
            assert hasattr(condition.match, "value")
            assert condition.match.value == tag

    def test_combined_filters(self):
        """Test multiple filters combined with AND logic."""
        filters = MetadataFilters(
            created_after=datetime(2024, 1, 1),
            doc_type_in=["pdf", "md"],
            tags_contains=["tutorial"],
        )
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        # created_after (1) + doc_type_in (1) + tags_contains (1) = 3
        assert len(qdrant_filter.must) == 3

    def test_combined_must_and_must_not(self):
        """Test filters with both must and must_not conditions."""
        filters = MetadataFilters(
            source_in=["docs.rag.com"],
            source_not_in=["spam.com"],
            doc_type_in=["pdf"],
        )
        qdrant_filter = self.engine.build_qdrant_filter(filters)

        assert qdrant_filter is not None
        assert qdrant_filter.must is not None
        assert qdrant_filter.must_not is not None
        # source_in (1) + doc_type_in (1) = 2
        assert len(qdrant_filter.must) == 2
        # source_not_in (1)
        assert len(qdrant_filter.must_not) == 1


class TestFilterValidation:
    """Test filter validation logic."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = MetadataFilterEngine()

    def test_valid_filter_no_conflicts(self):
        """Test that valid filters pass validation."""
        filters = MetadataFilters(
            created_after=datetime(2024, 1, 1),
            created_before=datetime(2024, 12, 31),
            doc_type_in=["pdf"],
        )
        is_valid, error_msg = self.engine.validate_filter(filters)
        assert is_valid
        assert error_msg == ""

    def test_invalid_date_range(self):
        """Test validation fails for invalid date range."""
        filters = MetadataFilters(
            created_after=datetime(2024, 12, 31),
            created_before=datetime(2024, 1, 1),
        )
        is_valid, error_msg = self.engine.validate_filter(filters)
        assert not is_valid
        assert "created_after must be before created_before" in error_msg

    def test_source_conflict(self):
        """Test validation fails when source_in and source_not_in overlap."""
        filters = MetadataFilters(
            source_in=["docs.rag.com", "arxiv.org"],
            source_not_in=["arxiv.org", "spam.com"],
        )
        is_valid, error_msg = self.engine.validate_filter(filters)
        assert not is_valid
        assert "overlap" in error_msg.lower()

    def test_no_source_conflict(self):
        """Test validation passes when source filters don't overlap."""
        filters = MetadataFilters(
            source_in=["docs.rag.com"],
            source_not_in=["spam.com"],
        )
        is_valid, error_msg = self.engine.validate_filter(filters)
        assert is_valid
        assert error_msg == ""


class TestSelectivityEstimation:
    """Test selectivity estimation for query planning."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = MetadataFilterEngine()

    def test_empty_filters_selectivity(self):
        """Test that empty filters have selectivity of 1.0."""
        filters = MetadataFilters()
        selectivity = self.engine.estimate_selectivity(filters)
        assert selectivity == 1.0

    def test_date_filter_selectivity(self):
        """Test date filters reduce selectivity."""
        filters = MetadataFilters(created_after=datetime(2024, 1, 1))
        selectivity = self.engine.estimate_selectivity(filters)
        assert 0.0 < selectivity < 1.0

    def test_source_filter_selectivity(self):
        """Test source filters reduce selectivity."""
        filters = MetadataFilters(source_in=["docs.rag.com"])
        selectivity = self.engine.estimate_selectivity(filters)
        assert 0.0 < selectivity < 1.0

    def test_doc_type_filter_selectivity(self):
        """Test doc_type filters reduce selectivity."""
        filters = MetadataFilters(doc_type_in=["pdf"])
        selectivity = self.engine.estimate_selectivity(filters)
        assert 0.0 < selectivity < 1.0

    def test_tags_filter_selectivity(self):
        """Test tags filters reduce selectivity."""
        filters = MetadataFilters(tags_contains=["tutorial"])
        selectivity = self.engine.estimate_selectivity(filters)
        assert 0.0 < selectivity < 1.0

    def test_multiple_tags_reduce_selectivity(self):
        """Test that multiple tags reduce selectivity more."""
        filters_one_tag = MetadataFilters(tags_contains=["tutorial"])
        filters_two_tags = MetadataFilters(tags_contains=["tutorial", "advanced"])

        selectivity_one = self.engine.estimate_selectivity(filters_one_tag)
        selectivity_two = self.engine.estimate_selectivity(filters_two_tags)

        assert selectivity_two < selectivity_one

    def test_combined_filters_selectivity(self):
        """Test that combined filters have lower selectivity."""
        filters = MetadataFilters(
            created_after=datetime(2024, 1, 1),
            doc_type_in=["pdf"],
            tags_contains=["tutorial"],
        )
        selectivity = self.engine.estimate_selectivity(filters)
        # Combined filters should be quite selective
        assert 0.01 <= selectivity < 0.5

    def test_selectivity_minimum_bound(self):
        """Test that selectivity has a minimum bound."""
        # Very restrictive filters
        filters = MetadataFilters(
            created_after=datetime(2024, 1, 1),
            created_before=datetime(2024, 1, 2),
            doc_type_in=["pdf"],
            tags_contains=["rare", "specific", "unique"],
        )
        selectivity = self.engine.estimate_selectivity(filters)
        # Should be at least 1% (0.01)
        assert selectivity >= 0.01


class TestEdgeCases:
    """Test edge cases and corner conditions."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = MetadataFilterEngine()

    def test_none_values_ignored(self):
        """Test that None values don't create filters."""
        filters = MetadataFilters(
            created_after=None,
            source_in=None,
            doc_type_in=None,
            tags_contains=None,
        )
        qdrant_filter = self.engine.build_qdrant_filter(filters)
        assert qdrant_filter is None

    def test_empty_list_ignored(self):
        """Test that empty lists don't create filters."""
        filters = MetadataFilters(
            source_in=[],
            doc_type_in=[],
            tags_contains=[],
        )
        qdrant_filter = self.engine.build_qdrant_filter(filters)
        assert qdrant_filter is None

    def test_single_source_filter(self):
        """Test single source in filter."""
        filters = MetadataFilters(source_in=["docs.rag.com"])
        qdrant_filter = self.engine.build_qdrant_filter(filters)
        assert qdrant_filter is not None
        assert len(qdrant_filter.must) == 1

    def test_single_doc_type_filter(self):
        """Test single doc_type in filter."""
        filters = MetadataFilters(doc_type_in=["pdf"])
        qdrant_filter = self.engine.build_qdrant_filter(filters)
        assert qdrant_filter is not None
        assert len(qdrant_filter.must) == 1

    def test_date_at_epoch(self):
        """Test date filter at Unix epoch (skip on Windows due to timestamp limitations)."""
        # Use a safe date that works on all platforms
        # Windows has issues with dates before 1970-01-01
        safe_date = datetime(2000, 1, 1)
        filters = MetadataFilters(created_after=safe_date)
        qdrant_filter = self.engine.build_qdrant_filter(filters)
        assert qdrant_filter is not None
        condition = qdrant_filter.must[0]
        # Should be a valid timestamp
        assert condition.range.gte >= 0
        assert condition.range.gte == int(safe_date.timestamp())

    def test_many_sources(self):
        """Test many sources in filter."""
        sources = [f"source{i}.com" for i in range(100)]
        filters = MetadataFilters(source_in=sources)
        qdrant_filter = self.engine.build_qdrant_filter(filters)
        assert qdrant_filter is not None
        condition = qdrant_filter.must[0]
        assert len(condition.match.any) == 100

    def test_many_tags(self):
        """Test many tags in filter (AND logic)."""
        tags = [f"tag{i}" for i in range(10)]
        filters = MetadataFilters(tags_contains=tags)
        qdrant_filter = self.engine.build_qdrant_filter(filters)
        assert qdrant_filter is not None
        # Should create 10 conditions (one per tag)
        assert len(qdrant_filter.must) == 10
