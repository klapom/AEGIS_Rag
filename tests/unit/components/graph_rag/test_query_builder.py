"""Unit tests for CypherQueryBuilder.

Tests cover:
- Fluent API method chaining
- Multi-hop relationship patterns
- Query parameterization
- Input validation
- Query building and structure
"""

import pytest

from src.components.graph_rag.query_builder import CypherQueryBuilder


class TestCypherQueryBuilder:
    """Test CypherQueryBuilder fluent API."""

    def test_simple_match_return(self):
        """Test basic MATCH ... RETURN query."""
        builder = CypherQueryBuilder()
        result = builder.match("(n:base)").return_("n").build()

        assert result["query"] == "MATCH (n:base) RETURN n"
        assert result["parameters"] == {}

    def test_match_with_where(self):
        """Test MATCH with WHERE clause."""
        builder = CypherQueryBuilder()
        result = (
            builder.match("(n:base)").where("n.name = $name", name="John").return_("n").build()
        )

        assert "MATCH (n:base)" in result["query"]
        assert "WHERE (n.name = $name)" in result["query"]
        assert "RETURN n" in result["query"]
        assert result["parameters"]["name"] == "John"

    def test_multiple_where_clauses(self):
        """Test multiple WHERE conditions with AND."""
        builder = CypherQueryBuilder()
        result = (
            builder.match("(n:base)")
            .where("n.name = $name", name="John")
            .where("n.age > $min_age", min_age=18)
            .return_("n")
            .build()
        )

        assert "WHERE (n.name = $name) AND (n.age > $min_age)" in result["query"]
        assert result["parameters"]["name"] == "John"
        assert result["parameters"]["min_age"] == 18

    def test_order_by_limit(self):
        """Test ORDER BY and LIMIT clauses."""
        builder = CypherQueryBuilder()
        result = builder.match("(n:base)").return_("n").order_by("n.name DESC").limit(10).build()

        assert "ORDER BY n.name DESC" in result["query"]
        assert "LIMIT 10" in result["query"]

    def test_skip_and_limit(self):
        """Test SKIP and LIMIT for pagination."""
        builder = CypherQueryBuilder()
        result = builder.match("(n:base)").return_("n").skip(20).limit(10).build()

        assert "SKIP 20" in result["query"]
        assert "LIMIT 10" in result["query"]

    def test_relationship_pattern(self):
        """Test relationship pattern matching."""
        builder = CypherQueryBuilder()
        result = builder.relationship("a", "KNOWS", "b").return_("a", "b").build()

        assert "(a)-[:KNOWS]->(b)" in result["query"]

    def test_multi_hop_relationship(self):
        """Test multi-hop relationship pattern."""
        builder = CypherQueryBuilder()
        result = (
            builder.match("(a:base)")
            .relationship("a", "RELATES_TO", "b", min_hops=1, max_hops=3)
            .return_("b")
            .build()
        )

        assert "RELATES_TO*1..3" in result["query"]

    def test_bidirectional_relationship(self):
        """Test bidirectional relationship."""
        builder = CypherQueryBuilder()
        result = builder.relationship("a", "KNOWS", "b", direction="-").return_("a", "b").build()

        assert "-[:KNOWS]-" in result["query"]

    def test_incoming_relationship(self):
        """Test incoming relationship."""
        builder = CypherQueryBuilder()
        result = builder.relationship("a", "KNOWS", "b", direction="<-").return_("a", "b").build()

        assert "<-[:KNOWS]-" in result["query"]

    def test_create_node(self):
        """Test CREATE clause."""
        builder = CypherQueryBuilder()
        result = (
            builder.create("(n:base {name: $name})").param("name", "Test").return_("n").build()
        )

        assert "CREATE (n:base {name: $name})" in result["query"]
        assert result["parameters"]["name"] == "Test"

    def test_merge_node(self):
        """Test MERGE clause."""
        builder = CypherQueryBuilder()
        result = (
            builder.merge("(n:base {name: $name})").param("name", "Test").return_("n").build()
        )

        assert "MERGE (n:base {name: $name})" in result["query"]
        assert result["parameters"]["name"] == "Test"

    def test_set_properties(self):
        """Test SET clause."""
        builder = CypherQueryBuilder()
        result = (
            builder.match("(n:base)")
            .where("n.id = $id", id="123")
            .set_("n.updated = $updated", updated=True)
            .return_("n")
            .build()
        )

        assert "SET n.updated = $updated" in result["query"]
        assert result["parameters"]["updated"] is True

    def test_delete_node(self):
        """Test DELETE clause."""
        builder = CypherQueryBuilder()
        result = builder.match("(n:base)").where("n.id = $id", id="123").delete("n").build()

        assert "DELETE n" in result["query"]
        assert result["parameters"]["id"] == "123"

    def test_with_clause(self):
        """Test WITH clause for query chaining."""
        builder = CypherQueryBuilder()
        result = (
            builder.match("(n:base)")
            .with_("n", "count(*) as total")
            .where("total > $min", min=5)
            .return_("n", "total")
            .build()
        )

        assert "WITH n, count(*) as total" in result["query"]
        assert "WHERE (total > $min)" in result["query"]

    def test_complex_query(self):
        """Test complex query with multiple clauses."""
        builder = CypherQueryBuilder()
        result = (
            builder.match("(a:base)")
            .where("a.type = $type", type="Person")
            .relationship("a", "KNOWS", "b", min_hops=1, max_hops=2)
            .where("b.age > $min_age", min_age=18)
            .return_("a", "b", "count(*) as connection_count")
            .order_by("connection_count DESC")
            .limit(10)
            .build()
        )

        assert "MATCH (a:base)" in result["query"]
        assert "WHERE" in result["query"]
        assert "RETURN a, b, count(*) as connection_count" in result["query"]
        assert "ORDER BY connection_count DESC" in result["query"]
        assert "LIMIT 10" in result["query"]

    def test_reset_builder(self):
        """Test resetting the query builder."""
        builder = CypherQueryBuilder()
        builder.match("(n:base)").where("n.name = $name", name="John").return_("n")

        builder.reset()

        with pytest.raises(ValueError, match="Cannot build empty query"):
            builder.build()

    def test_empty_match_raises_error(self):
        """Test that empty match pattern raises error."""
        builder = CypherQueryBuilder()

        with pytest.raises(ValueError, match="Match pattern cannot be empty"):
            builder.match("")

    def test_empty_where_raises_error(self):
        """Test that empty WHERE condition raises error."""
        builder = CypherQueryBuilder()

        with pytest.raises(ValueError, match="WHERE condition cannot be empty"):
            builder.where("")

    def test_empty_return_raises_error(self):
        """Test that empty RETURN raises error."""
        builder = CypherQueryBuilder()

        with pytest.raises(ValueError, match="RETURN clause requires at least one item"):
            builder.return_()

    def test_negative_limit_raises_error(self):
        """Test that negative limit raises error."""
        builder = CypherQueryBuilder()

        with pytest.raises(ValueError, match="LIMIT count must be non-negative"):
            builder.limit(-1)

    def test_invalid_direction_raises_error(self):
        """Test that invalid relationship direction raises error."""
        builder = CypherQueryBuilder()

        with pytest.raises(ValueError, match="Invalid direction"):
            builder.relationship("a", "KNOWS", "b", direction="invalid")

    def test_parameterization(self):
        """Test query parameterization for security."""
        builder = CypherQueryBuilder()
        result = (
            builder.match("(n:base)")
            .where("n.name = $name", name="John'; DROP TABLE users; --")
            .return_("n")
            .build()
        )

        # Parameters should be separate from query
        assert "DROP TABLE" not in result["query"]
        assert result["parameters"]["name"] == "John'; DROP TABLE users; --"

    def test_multiple_return_items(self):
        """Test multiple RETURN items."""
        builder = CypherQueryBuilder()
        result = (
            builder.match("(n:base)")
            .return_("n.name", "n.type", "n.id", "count(*) as total")
            .build()
        )

        assert "RETURN n.name, n.type, n.id, count(*) as total" in result["query"]
