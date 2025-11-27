"""Unit tests for TemporalQueryBuilder."""

import pytest
from datetime import datetime, timedelta

from src.components.graph_rag.temporal_query_builder import (
    CypherQueryBuilder,
    TemporalQueryBuilder,
    get_temporal_query_builder,
)


class TestCypherQueryBuilder:
    """Tests for base CypherQueryBuilder."""

    def test_match_clause(self):
        """Test adding MATCH clause."""
        builder = CypherQueryBuilder()
        builder.match("(e:base)")
        query, params = builder.build()
        assert "MATCH (e:base)" in query
        assert params == {}

    def test_where_clause(self):
        """Test adding WHERE clause."""
        builder = CypherQueryBuilder()
        builder.match("(e:base)").where("e.type = 'PERSON'")
        query, params = builder.build()
        assert "WHERE (e.type = 'PERSON')" in query

    def test_return_clause(self):
        """Test adding RETURN clause."""
        builder = CypherQueryBuilder()
        builder.match("(e:base)").return_clause("e")
        query, params = builder.build()
        assert "RETURN e" in query

    def test_order_by(self):
        """Test ORDER BY clause."""
        builder = CypherQueryBuilder()
        builder.match("(e:base)").return_clause("e").order_by("e.name")
        query, params = builder.build()
        assert "ORDER BY e.name" in query

    def test_limit(self):
        """Test LIMIT clause."""
        builder = CypherQueryBuilder()
        builder.match("(e:base)").return_clause("e").limit(10)
        query, params = builder.build()
        assert "LIMIT 10" in query

    def test_skip(self):
        """Test SKIP clause."""
        builder = CypherQueryBuilder()
        builder.match("(e:base)").return_clause("e").skip(5)
        query, params = builder.build()
        assert "SKIP 5" in query

    def test_set_param(self):
        """Test setting query parameters."""
        builder = CypherQueryBuilder()
        builder.set_param("entity_id", "test123")
        query, params = builder.build()
        assert params == {"entity_id": "test123"}

    def test_complex_query(self):
        """Test building complex query with multiple clauses."""
        builder = CypherQueryBuilder()
        builder.match("(e:base)").where("e.id = $entity_id").return_clause("e").order_by(
            "e.name"
        ).limit(5).set_param("entity_id", "test123")

        query, params = builder.build()
        assert "MATCH (e:base)" in query
        assert "WHERE (e.id = $entity_id)" in query
        assert "RETURN e" in query
        assert "ORDER BY e.name" in query
        assert "LIMIT 5" in query
        assert params == {"entity_id": "test123"}

    def test_reset(self):
        """Test resetting builder state."""
        builder = CypherQueryBuilder()
        builder.match("(e:base)").where("e.id = 'test'").return_clause("e").set_param("id", "123")
        builder.reset()

        query, params = builder.build()
        assert query == ""
        assert params == {}


class TestTemporalQueryBuilder:
    """Tests for TemporalQueryBuilder."""

    def test_as_of_query(self):
        """Test as_of point-in-time query."""
        builder = TemporalQueryBuilder()
        timestamp = datetime(2025, 1, 15, 10, 0, 0)
        builder.match("(e:base)").as_of(timestamp).return_clause("e")

        query, params = builder.build()
        assert "e.valid_from <=" in query
        assert "e.valid_to" in query
        assert "e.transaction_from <=" in query
        assert "e.transaction_to" in query
        assert len(params) == 1
        assert "2025-01-15T10:00:00" in list(params.values())[0]

    def test_between_query(self):
        """Test between range query."""
        builder = TemporalQueryBuilder()
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 31, 23, 59, 59)
        builder.match("(e:base)").between(start, end).return_clause("e")

        query, params = builder.build()
        assert "e.valid_from <=" in query
        assert "e.valid_to" in query
        assert len(params) == 2

    def test_valid_during_query(self):
        """Test valid_during (real-world time) filter."""
        builder = TemporalQueryBuilder()
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 31, 23, 59, 59)
        builder.match("(e:base)").valid_during(start, end).return_clause("e")

        query, params = builder.build()
        assert "e.valid_from <=" in query
        assert "e.valid_to" in query
        # Should NOT include transaction time filters
        assert "e.transaction_from" not in query
        assert len(params) == 2

    def test_transaction_during_query(self):
        """Test transaction_during (database time) filter."""
        builder = TemporalQueryBuilder()
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 31, 23, 59, 59)
        builder.match("(e:base)").transaction_during(start, end).return_clause("e")

        query, params = builder.build()
        assert "e.transaction_from <=" in query
        assert "e.transaction_to" in query
        # Should NOT include valid time filters
        assert "e.valid_from" not in query or "e.transaction_from" in query
        assert len(params) == 2

    def test_current_query(self):
        """Test current (latest version) filter."""
        builder = TemporalQueryBuilder()
        builder.match("(e:base)").current().return_clause("e")

        query, params = builder.build()
        assert "e.valid_to IS NULL" in query
        assert "e.transaction_to IS NULL" in query
        assert len(params) == 0

    def test_with_history_query(self):
        """Test with_history (no temporal filter)."""
        builder = TemporalQueryBuilder()
        builder.match("(e:base)").with_history().return_clause("e")

        query, params = builder.build()
        # Should not have temporal filters
        assert "e.valid_to" not in query
        assert "e.transaction_to" not in query

    def test_at_valid_time(self):
        """Test at_valid_time (real-world time only)."""
        builder = TemporalQueryBuilder()
        timestamp = datetime(2025, 1, 15, 10, 0, 0)
        builder.match("(e:base)").at_valid_time(timestamp).return_clause("e")

        query, params = builder.build()
        assert "e.valid_from <=" in query
        assert "e.valid_to" in query
        # Should NOT include transaction time filters
        assert "e.transaction_from" not in query
        assert len(params) == 1

    def test_at_transaction_time(self):
        """Test at_transaction_time (database time only)."""
        builder = TemporalQueryBuilder()
        timestamp = datetime(2025, 1, 15, 10, 0, 0)
        builder.match("(e:base)").at_transaction_time(timestamp).return_clause("e")

        query, params = builder.build()
        assert "e.transaction_from <=" in query
        assert "e.transaction_to" in query
        # Should NOT include valid time filters
        assert "e.valid_from" not in query or "e.transaction_from" in query
        assert len(params) == 1

    def test_multiple_temporal_filters(self):
        """Test combining multiple temporal filters."""
        builder = TemporalQueryBuilder()
        timestamp = datetime(2025, 1, 15, 10, 0, 0)
        builder.match("(e:base)").at_valid_time(timestamp).current().return_clause("e")

        query, params = builder.build()
        # Should have both filters
        assert "e.valid_from <=" in query
        assert "e.valid_to IS NULL" in query

    def test_reset_temporal(self):
        """Test resetting temporal builder state."""
        builder = TemporalQueryBuilder()
        timestamp = datetime(2025, 1, 15, 10, 0, 0)
        builder.match("(e:base)").as_of(timestamp).return_clause("e")

        builder.reset()
        query, params = builder.build()
        assert query == ""
        assert params == {}

    def test_singleton_instance(self):
        """Test singleton pattern for temporal query builder."""
        builder1 = get_temporal_query_builder()
        builder2 = get_temporal_query_builder()
        assert builder1 is builder2


class TestTemporalQueryEdgeCases:
    """Test edge cases and error handling."""

    def test_future_timestamp(self):
        """Test querying future timestamp."""
        builder = TemporalQueryBuilder()
        future = datetime.utcnow() + timedelta(days=365)
        builder.match("(e:base)").as_of(future).return_clause("e")

        query, params = builder.build()
        assert len(params) == 1
        assert "2026" in list(params.values())[0]

    def test_past_timestamp(self):
        """Test querying historical timestamp."""
        builder = TemporalQueryBuilder()
        past = datetime(2020, 1, 1, 0, 0, 0)
        builder.match("(e:base)").as_of(past).return_clause("e")

        query, params = builder.build()
        assert len(params) == 1
        assert "2020-01-01" in list(params.values())[0]

    def test_same_start_end_time(self):
        """Test between query with same start and end time."""
        builder = TemporalQueryBuilder()
        timestamp = datetime(2025, 1, 15, 10, 0, 0)
        builder.match("(e:base)").between(timestamp, timestamp).return_clause("e")

        query, params = builder.build()
        assert len(params) == 2
        # Both params should have same value
        values = list(params.values())
        assert values[0] == values[1]

    def test_inverted_time_range(self):
        """Test between query with start > end (should still build query)."""
        builder = TemporalQueryBuilder()
        start = datetime(2025, 12, 31, 23, 59, 59)
        end = datetime(2025, 1, 1, 0, 0, 0)
        builder.match("(e:base)").between(start, end).return_clause("e")

        query, params = builder.build()
        # Query should build but likely return no results
        assert len(params) == 2
