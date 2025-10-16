"""Fluent Cypher Query Builder for Neo4j.

This module provides a fluent API for building parameterized Cypher queries with:
- Type-safe query construction
- Multi-hop relationship patterns
- Automatic parameterization for security
- Support for complex graph patterns
- Method chaining for readability
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CypherQueryBuilder:
    """Fluent API for building parameterized Cypher queries.

    Example:
        >>> builder = CypherQueryBuilder()
        >>> result = (builder
        ...     .match("n:Entity")
        ...     .where("n.name = $name")
        ...     .return_("n")
        ...     .limit(10)
        ...     .build())
        >>> print(result["query"])
        MATCH (n:Entity) WHERE n.name = $name RETURN n LIMIT 10
        >>> print(result["parameters"])
        {'name': None}
    """

    def __init__(self) -> None:
        """Initialize query builder."""
        self._match_clauses: list[str] = []
        self._where_clauses: list[str] = []
        self._return_clauses: list[str] = []
        self._order_by_clauses: list[str] = []
        self._with_clauses: list[str] = []
        self._create_clauses: list[str] = []
        self._merge_clauses: list[str] = []
        self._set_clauses: list[str] = []
        self._delete_clauses: list[str] = []
        self._limit_value: int | None = None
        self._skip_value: int | None = None
        self._parameters: dict[str, Any] = {}

        logger.debug("CypherQueryBuilder initialized")

    def match(self, pattern: str) -> "CypherQueryBuilder":
        """Add MATCH clause to query.

        Args:
            pattern: Cypher pattern (e.g., "(n:Entity)", "(a)-[:RELATES_TO]->(b)")

        Returns:
            Self for method chaining

        Example:
            >>> builder.match("(n:Entity)")
            >>> builder.match("(a:Person)-[:KNOWS]->(b:Person)")
            >>> builder.match("(n:Entity)-[:RELATES_TO*1..3]->(m:Entity)")
        """
        if not pattern:
            raise ValueError("Match pattern cannot be empty")

        self._match_clauses.append(pattern)
        logger.debug("Added MATCH clause", pattern=pattern)
        return self

    def relationship(
        self,
        source_var: str,
        rel_type: str | None = None,
        target_var: str | None = None,
        direction: str = "->",
        min_hops: int | None = None,
        max_hops: int | None = None,
        rel_var: str | None = None,
    ) -> "CypherQueryBuilder":
        """Add relationship pattern to MATCH clause.

        Args:
            source_var: Source node variable
            rel_type: Relationship type (optional)
            target_var: Target node variable (optional)
            direction: Relationship direction ("->", "<-", "-") (default: "->")
            min_hops: Minimum hops for multi-hop pattern (optional)
            max_hops: Maximum hops for multi-hop pattern (optional)
            rel_var: Relationship variable name (optional)

        Returns:
            Self for method chaining

        Example:
            >>> builder.relationship("a", "KNOWS", "b")
            >>> builder.relationship("a", "RELATES_TO", "b", min_hops=1, max_hops=3)
            >>> builder.relationship("a", direction="-", target_var="b")
        """
        if not source_var:
            raise ValueError("Source variable cannot be empty")

        # Build relationship pattern
        rel_pattern = f"({source_var})"

        # Build relationship part
        if direction == "->":
            left_arrow = "-"
            right_arrow = "->"
        elif direction == "<-":
            left_arrow = "<-"
            right_arrow = "-"
        elif direction == "-":
            left_arrow = "-"
            right_arrow = "-"
        else:
            raise ValueError(f"Invalid direction: {direction}. Must be '->', '<-', or '-'")

        # Build relationship type
        rel_part = "["
        if rel_var:
            rel_part += rel_var
        if rel_type:
            rel_part += f":{rel_type}"

        # Add multi-hop pattern
        if min_hops is not None or max_hops is not None:
            if min_hops is not None and max_hops is not None:
                rel_part += f"*{min_hops}..{max_hops}"
            elif min_hops is not None:
                rel_part += f"*{min_hops}.."
            elif max_hops is not None:
                rel_part += f"*..{max_hops}"

        rel_part += "]"

        # Build full pattern
        if target_var:
            rel_pattern += f"{left_arrow}{rel_part}{right_arrow}({target_var})"
        else:
            rel_pattern += f"{left_arrow}{rel_part}{right_arrow}()"

        self._match_clauses.append(rel_pattern)
        logger.debug("Added relationship pattern", pattern=rel_pattern)
        return self

    def where(self, condition: str, **params: Any) -> "CypherQueryBuilder":
        """Add WHERE clause to query.

        Args:
            condition: Cypher condition (e.g., "n.name = $name")
            **params: Parameter values to bind

        Returns:
            Self for method chaining

        Example:
            >>> builder.where("n.name = $name", name="John")
            >>> builder.where("n.age > $min_age", min_age=18)
        """
        if not condition:
            raise ValueError("WHERE condition cannot be empty")

        self._where_clauses.append(condition)
        self._parameters.update(params)
        logger.debug("Added WHERE clause", condition=condition, params=list(params.keys()))
        return self

    def return_(self, *items: str) -> "CypherQueryBuilder":
        """Add RETURN clause to query.

        Args:
            *items: Items to return (e.g., "n", "count(n) as total")

        Returns:
            Self for method chaining

        Example:
            >>> builder.return_("n")
            >>> builder.return_("n", "m", "r")
            >>> builder.return_("count(n) as total")
        """
        if not items:
            raise ValueError("RETURN clause requires at least one item")

        self._return_clauses.extend(items)
        logger.debug("Added RETURN clause", items=items)
        return self

    def order_by(self, *fields: str) -> "CypherQueryBuilder":
        """Add ORDER BY clause to query.

        Args:
            *fields: Fields to order by (e.g., "n.name", "n.age DESC")

        Returns:
            Self for method chaining

        Example:
            >>> builder.order_by("n.name")
            >>> builder.order_by("n.age DESC", "n.name ASC")
        """
        if not fields:
            raise ValueError("ORDER BY clause requires at least one field")

        self._order_by_clauses.extend(fields)
        logger.debug("Added ORDER BY clause", fields=fields)
        return self

    def limit(self, count: int) -> "CypherQueryBuilder":
        """Add LIMIT clause to query.

        Args:
            count: Maximum number of results

        Returns:
            Self for method chaining

        Example:
            >>> builder.limit(10)
        """
        if count < 0:
            raise ValueError("LIMIT count must be non-negative")

        self._limit_value = count
        logger.debug("Added LIMIT clause", count=count)
        return self

    def skip(self, count: int) -> "CypherQueryBuilder":
        """Add SKIP clause to query.

        Args:
            count: Number of results to skip

        Returns:
            Self for method chaining

        Example:
            >>> builder.skip(10)
        """
        if count < 0:
            raise ValueError("SKIP count must be non-negative")

        self._skip_value = count
        logger.debug("Added SKIP clause", count=count)
        return self

    def with_(self, *items: str) -> "CypherQueryBuilder":
        """Add WITH clause to query.

        Args:
            *items: Items to pass to next query part

        Returns:
            Self for method chaining

        Example:
            >>> builder.with_("n", "count(m) as m_count")
        """
        if not items:
            raise ValueError("WITH clause requires at least one item")

        self._with_clauses.extend(items)
        logger.debug("Added WITH clause", items=items)
        return self

    def create(self, pattern: str) -> "CypherQueryBuilder":
        """Add CREATE clause to query.

        Args:
            pattern: Cypher pattern to create

        Returns:
            Self for method chaining

        Example:
            >>> builder.create("(n:Entity {name: $name})")
        """
        if not pattern:
            raise ValueError("CREATE pattern cannot be empty")

        self._create_clauses.append(pattern)
        logger.debug("Added CREATE clause", pattern=pattern)
        return self

    def merge(self, pattern: str) -> "CypherQueryBuilder":
        """Add MERGE clause to query.

        Args:
            pattern: Cypher pattern to merge

        Returns:
            Self for method chaining

        Example:
            >>> builder.merge("(n:Entity {name: $name})")
        """
        if not pattern:
            raise ValueError("MERGE pattern cannot be empty")

        self._merge_clauses.append(pattern)
        logger.debug("Added MERGE clause", pattern=pattern)
        return self

    def set_(self, *assignments: str, **properties: Any) -> "CypherQueryBuilder":
        """Add SET clause to query.

        Args:
            *assignments: Property assignments (e.g., "n.name = $name")
            **properties: Properties to set as parameters

        Returns:
            Self for method chaining

        Example:
            >>> builder.set_("n.name = $name", name="John")
            >>> builder.set_(updated="true")
        """
        if not assignments and not properties:
            raise ValueError("SET clause requires at least one assignment")

        self._set_clauses.extend(assignments)
        self._parameters.update(properties)
        logger.debug(
            "Added SET clause", assignments=assignments, properties=list(properties.keys())
        )
        return self

    def delete(self, *items: str) -> "CypherQueryBuilder":
        """Add DELETE clause to query.

        Args:
            *items: Items to delete

        Returns:
            Self for method chaining

        Example:
            >>> builder.delete("n")
            >>> builder.delete("n", "m")
        """
        if not items:
            raise ValueError("DELETE clause requires at least one item")

        self._delete_clauses.extend(items)
        logger.debug("Added DELETE clause", items=items)
        return self

    def param(self, name: str, value: Any) -> "CypherQueryBuilder":
        """Add a parameter to the query.

        Args:
            name: Parameter name
            value: Parameter value

        Returns:
            Self for method chaining

        Example:
            >>> builder.param("name", "John")
            >>> builder.param("age", 30)
        """
        if not name:
            raise ValueError("Parameter name cannot be empty")

        self._parameters[name] = value
        logger.debug("Added parameter", name=name)
        return self

    def build(self) -> dict[str, Any]:
        """Build the final query and parameters.

        Returns:
            Dictionary with "query" and "parameters" keys

        Raises:
            ValueError: If query is invalid

        Example:
            >>> result = builder.build()
            >>> print(result["query"])
            >>> print(result["parameters"])
        """
        query_parts: list[str] = []

        # Add MATCH clauses
        if self._match_clauses:
            query_parts.append(f"MATCH {', '.join(self._match_clauses)}")

        # Add CREATE clauses
        if self._create_clauses:
            query_parts.append(f"CREATE {', '.join(self._create_clauses)}")

        # Add MERGE clauses
        if self._merge_clauses:
            query_parts.append(f"MERGE {', '.join(self._merge_clauses)}")

        # Add WHERE clauses
        if self._where_clauses:
            where_expr = " AND ".join(f"({clause})" for clause in self._where_clauses)
            query_parts.append(f"WHERE {where_expr}")

        # Add SET clauses
        if self._set_clauses:
            query_parts.append(f"SET {', '.join(self._set_clauses)}")

        # Add DELETE clauses
        if self._delete_clauses:
            query_parts.append(f"DELETE {', '.join(self._delete_clauses)}")

        # Add WITH clauses
        if self._with_clauses:
            query_parts.append(f"WITH {', '.join(self._with_clauses)}")

        # Add RETURN clauses
        if self._return_clauses:
            query_parts.append(f"RETURN {', '.join(self._return_clauses)}")

        # Add ORDER BY clauses
        if self._order_by_clauses:
            query_parts.append(f"ORDER BY {', '.join(self._order_by_clauses)}")

        # Add SKIP clause
        if self._skip_value is not None:
            query_parts.append(f"SKIP {self._skip_value}")

        # Add LIMIT clause
        if self._limit_value is not None:
            query_parts.append(f"LIMIT {self._limit_value}")

        # Build final query
        query = " ".join(query_parts)

        if not query:
            raise ValueError("Cannot build empty query")

        logger.info(
            "Built Cypher query", query_length=len(query), param_count=len(self._parameters)
        )

        return {"query": query, "parameters": self._parameters}

    def reset(self) -> "CypherQueryBuilder":
        """Reset the query builder to initial state.

        Returns:
            Self for method chaining
        """
        self._match_clauses.clear()
        self._where_clauses.clear()
        self._return_clauses.clear()
        self._order_by_clauses.clear()
        self._with_clauses.clear()
        self._create_clauses.clear()
        self._merge_clauses.clear()
        self._set_clauses.clear()
        self._delete_clauses.clear()
        self._limit_value = None
        self._skip_value = None
        self._parameters.clear()

        logger.debug("Query builder reset")
        return self
