"""Temporal Query Builder for Bi-Temporal Graph Queries.

This module provides a builder for constructing Cypher queries with temporal filters.
Implements bi-temporal model: valid_time (real-world) + transaction_time (database).
"""

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CypherQueryBuilder:
    """Base class for building Cypher queries."""

    def __init__(self):
        """Initialize query builder."""
        self._match: list[str] = []
        self._where: list[str] = []
        self._return: list[str] = []
        self._params: dict[str, Any] = {}
        self._order_by: list[str] = []
        self._limit: int | None = None
        self._skip: int | None = None

    def match(self, pattern: str) -> "CypherQueryBuilder":
        """Add MATCH clause.

        Args:
            pattern: Cypher pattern to match

        Returns:
            Self for method chaining
        """
        self._match.append(pattern)
        return self

    def where(self, condition: str) -> "CypherQueryBuilder":
        """Add WHERE condition.

        Args:
            condition: WHERE condition

        Returns:
            Self for method chaining
        """
        self._where.append(condition)
        return self

    def return_clause(self, expression: str) -> "CypherQueryBuilder":
        """Add RETURN expression.

        Args:
            expression: Expression to return

        Returns:
            Self for method chaining
        """
        self._return.append(expression)
        return self

    def order_by(self, expression: str) -> "CypherQueryBuilder":
        """Add ORDER BY clause.

        Args:
            expression: Expression to order by

        Returns:
            Self for method chaining
        """
        self._order_by.append(expression)
        return self

    def limit(self, count: int) -> "CypherQueryBuilder":
        """Set LIMIT.

        Args:
            count: Number of results to limit

        Returns:
            Self for method chaining
        """
        self._limit = count
        return self

    def skip(self, count: int) -> "CypherQueryBuilder":
        """Set SKIP.

        Args:
            count: Number of results to skip

        Returns:
            Self for method chaining
        """
        self._skip = count
        return self

    def set_param(self, key: str, value: Any) -> "CypherQueryBuilder":
        """Set query parameter.

        Args:
            key: Parameter key
            value: Parameter value

        Returns:
            Self for method chaining
        """
        self._params[key] = value
        return self

    def build(self) -> tuple[str, dict[str, Any]]:
        """Build the Cypher query.

        Returns:
            Tuple of (query_string, parameters)
        """
        parts = []

        # MATCH
        if self._match:
            parts.append("MATCH " + ", ".join(self._match))

        # WHERE
        if self._where:
            parts.append("WHERE " + " AND ".join(f"({cond})" for cond in self._where))

        # RETURN
        if self._return:
            parts.append("RETURN " + ", ".join(self._return))

        # ORDER BY
        if self._order_by:
            parts.append("ORDER BY " + ", ".join(self._order_by))

        # SKIP
        if self._skip is not None:
            parts.append(f"SKIP {self._skip}")

        # LIMIT
        if self._limit is not None:
            parts.append(f"LIMIT {self._limit}")

        query = "\n".join(parts)
        return query, self._params

    def reset(self) -> None:
        """Reset builder state."""
        self._match.clear()
        self._where.clear()
        self._return.clear()
        self._params.clear()
        self._order_by.clear()
        self._limit = None
        self._skip = None


class TemporalQueryBuilder(CypherQueryBuilder):
    """Builder for temporal Cypher queries with bi-temporal model support."""

    def __init__(self):
        """Initialize temporal query builder."""
        super().__init__()
        self._temporal_filters: list[str] = []

    def as_of(self, timestamp: datetime) -> "TemporalQueryBuilder":
        """Query as of a specific point in time (both valid and transaction time).

        Args:
            timestamp: Point in time to query

        Returns:
            Self for method chaining
        """
        param_name = f"as_of_time_{len(self._params)}"
        self._params[param_name] = timestamp.isoformat()

        # Entity must be valid and present in database at timestamp
        self._temporal_filters.append(
            f"e.valid_from <= datetime(${param_name}) "
            f"AND (e.valid_to IS NULL OR e.valid_to > datetime(${param_name})) "
            f"AND e.transaction_from <= datetime(${param_name}) "
            f"AND (e.transaction_to IS NULL OR e.transaction_to > datetime(${param_name}))"
        )

        logger.debug("Added as_of temporal filter", timestamp=timestamp.isoformat())
        return self

    def between(self, start: datetime, end: datetime) -> "TemporalQueryBuilder":
        """Query entities valid/present between start and end time.

        Args:
            start: Start time
            end: End time

        Returns:
            Self for method chaining
        """
        start_param = f"start_time_{len(self._params)}"
        end_param = f"end_time_{len(self._params) + 1}"
        self._params[start_param] = start.isoformat()
        self._params[end_param] = end.isoformat()

        # Entity valid/present overlaps with time range
        self._temporal_filters.append(
            f"e.valid_from <= datetime(${end_param}) "
            f"AND (e.valid_to IS NULL OR e.valid_to >= datetime(${start_param})) "
            f"AND e.transaction_from <= datetime(${end_param}) "
            f"AND (e.transaction_to IS NULL OR e.transaction_to >= datetime(${start_param}))"
        )

        logger.debug("Added between temporal filter", start=start.isoformat(), end=end.isoformat())
        return self

    def valid_during(self, start: datetime, end: datetime) -> "TemporalQueryBuilder":
        """Filter by valid time range only (real-world time).

        Args:
            start: Start of valid time range
            end: End of valid time range

        Returns:
            Self for method chaining
        """
        start_param = f"valid_start_{len(self._params)}"
        end_param = f"valid_end_{len(self._params) + 1}"
        self._params[start_param] = start.isoformat()
        self._params[end_param] = end.isoformat()

        self._temporal_filters.append(
            f"e.valid_from <= datetime(${end_param}) "
            f"AND (e.valid_to IS NULL OR e.valid_to >= datetime(${start_param}))"
        )

        logger.debug(
            "Added valid_during temporal filter", start=start.isoformat(), end=end.isoformat()
        )
        return self

    def transaction_during(self, start: datetime, end: datetime) -> "TemporalQueryBuilder":
        """Filter by transaction time range only (database time).

        Args:
            start: Start of transaction time range
            end: End of transaction time range

        Returns:
            Self for method chaining
        """
        start_param = f"trans_start_{len(self._params)}"
        end_param = f"trans_end_{len(self._params) + 1}"
        self._params[start_param] = start.isoformat()
        self._params[end_param] = end.isoformat()

        self._temporal_filters.append(
            f"e.transaction_from <= datetime(${end_param}) "
            f"AND (e.transaction_to IS NULL OR e.transaction_to >= datetime(${start_param}))"
        )

        logger.debug(
            "Added transaction_during temporal filter",
            start=start.isoformat(),
            end=end.isoformat(),
        )
        return self

    def current(self) -> "TemporalQueryBuilder":
        """Filter to current versions only (valid_to IS NULL).

        Returns:
            Self for method chaining
        """
        self._temporal_filters.append("e.valid_to IS NULL AND e.transaction_to IS NULL")
        logger.debug("Added current temporal filter")
        return self

    def with_history(self) -> "TemporalQueryBuilder":
        """Include all versions (no temporal filter).

        Returns:
            Self for method chaining
        """
        # No filter added - returns all versions
        logger.debug("Enabled history mode - no temporal filters")
        return self

    def at_valid_time(self, timestamp: datetime) -> "TemporalQueryBuilder":
        """Query by valid time only (real-world time).

        Args:
            timestamp: Valid time to query

        Returns:
            Self for method chaining
        """
        param_name = f"valid_time_{len(self._params)}"
        self._params[param_name] = timestamp.isoformat()

        self._temporal_filters.append(
            f"e.valid_from <= datetime(${param_name}) "
            f"AND (e.valid_to IS NULL OR e.valid_to > datetime(${param_name}))"
        )

        logger.debug("Added at_valid_time temporal filter", timestamp=timestamp.isoformat())
        return self

    def at_transaction_time(self, timestamp: datetime) -> "TemporalQueryBuilder":
        """Query by transaction time only (database time).

        Args:
            timestamp: Transaction time to query

        Returns:
            Self for method chaining
        """
        param_name = f"trans_time_{len(self._params)}"
        self._params[param_name] = timestamp.isoformat()

        self._temporal_filters.append(
            f"e.transaction_from <= datetime(${param_name}) "
            f"AND (e.transaction_to IS NULL OR e.transaction_to > datetime(${param_name}))"
        )

        logger.debug("Added at_transaction_time temporal filter", timestamp=timestamp.isoformat())
        return self

    def build(self) -> tuple[str, dict[str, Any]]:
        """Build the temporal Cypher query.

        Returns:
            Tuple of (query_string, parameters)
        """
        # Add temporal filters to WHERE clause
        for filter_cond in self._temporal_filters:
            self.where(filter_cond)

        return super().build()

    def reset(self) -> None:
        """Reset builder state including temporal filters."""
        super().reset()
        self._temporal_filters.clear()


# Singleton instance
_temporal_query_builder: TemporalQueryBuilder | None = None


def get_temporal_query_builder() -> TemporalQueryBuilder:
    """Get global temporal query builder instance (singleton).

    Returns:
        TemporalQueryBuilder instance
    """
    global _temporal_query_builder
    if _temporal_query_builder is None:
        _temporal_query_builder = TemporalQueryBuilder()
    return _temporal_query_builder
