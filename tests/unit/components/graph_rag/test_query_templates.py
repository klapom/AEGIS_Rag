"""Unit tests for GraphQueryTemplates.

Tests cover:
- All 15+ pre-built query templates
- Parameter binding and validation
- Query validity and structure
- Cypher syntax correctness
"""

import pytest

from src.components.graph_rag.query_templates import GraphQueryTemplates


class TestGraphQueryTemplates:
    """Test GraphQueryTemplates pre-built queries."""

    @pytest.fixture
    def templates(self):
        """Create templates instance for testing."""
        return GraphQueryTemplates()

    def test_entity_lookup(self, templates):
        """Test entity lookup template."""
        result = templates.entity_lookup("John Doe").build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "WHERE (e.name = $name)" in result["query"]
        assert "RETURN e" in result["query"]
        assert result["parameters"]["name"] == "John Doe"

    def test_entity_neighbors_depth_1(self, templates):
        """Test entity neighbors with depth 1."""
        result = templates.entity_neighbors("entity-123", depth=1).build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "WHERE (e.id = $entity_id)" in result["query"]
        assert "*1..1" in result["query"]
        assert result["parameters"]["entity_id"] == "entity-123"

    def test_entity_neighbors_with_rel_type(self, templates):
        """Test entity neighbors with relationship type filter."""
        result = templates.entity_neighbors("entity-123", depth=2, rel_type="RELATES_TO").build()

        assert "RELATES_TO" in result["query"]
        assert "*1..2" in result["query"]
        assert result["parameters"]["depth"] == 2

    def test_shortest_path(self, templates):
        """Test shortest path template."""
        result = templates.shortest_path("entity-1", "entity-2", max_hops=5).build()

        assert "MATCH (source:Entity), (target:Entity)" in result["query"]
        assert "shortestPath" in result["query"]
        assert "WHERE (source.id = $source_id)" in result["query"]
        assert "WHERE (target.id = $target_id)" in result["query"]
        assert result["parameters"]["source_id"] == "entity-1"
        assert result["parameters"]["target_id"] == "entity-2"

    def test_entity_relationships_all_directions(self, templates):
        """Test entity relationships with all directions."""
        result = templates.entity_relationships("entity-123", direction="both").build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "(e)-[r]-(other:Entity)" in result["query"]
        assert result["parameters"]["entity_id"] == "entity-123"

    def test_entity_relationships_outgoing(self, templates):
        """Test entity relationships outgoing only."""
        result = templates.entity_relationships("entity-123", direction="outgoing").build()

        assert "(e)-[r]->(other:Entity)" in result["query"]

    def test_entity_relationships_incoming(self, templates):
        """Test entity relationships incoming only."""
        result = templates.entity_relationships("entity-123", direction="incoming").build()

        assert "(e)<-[r]-(other:Entity)" in result["query"]

    def test_entity_relationships_with_type(self, templates):
        """Test entity relationships with type filter."""
        result = templates.entity_relationships(
            "entity-123", rel_type="KNOWS", direction="outgoing"
        ).build()

        assert ":KNOWS" in result["query"]

    def test_subgraph_extraction(self, templates):
        """Test subgraph extraction template."""
        entity_ids = ["entity-1", "entity-2", "entity-3"]
        result = templates.subgraph_extraction(entity_ids, depth=2).build()

        assert "MATCH (seed:Entity)" in result["query"]
        assert "seed.id IN $entity_ids OR seed.name IN $entity_ids" in result["query"]
        assert "*0..2" in result["query"]
        assert result["parameters"]["entity_ids"] == entity_ids
        assert result["parameters"]["depth"] == 2

    def test_entity_by_type(self, templates):
        """Test entity by type template."""
        result = templates.entity_by_type("Person", limit=50).build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "WHERE (e.type = $entity_type)" in result["query"]
        assert "ORDER BY e.name" in result["query"]
        assert "LIMIT 50" in result["query"]
        assert result["parameters"]["entity_type"] == "Person"

    def test_relationship_by_type(self, templates):
        """Test relationship by type template."""
        result = templates.relationship_by_type("KNOWS", limit=100).build()

        assert "MATCH (source)-[r:KNOWS]->(target)" in result["query"]
        assert "RETURN source, r, target" in result["query"]
        assert "LIMIT 100" in result["query"]

    def test_entity_search(self, templates):
        """Test entity search template."""
        result = templates.entity_search("machine learning", limit=5).build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "CONTAINS" in result["query"]
        assert "toLower" in result["query"]
        assert "LIMIT 5" in result["query"]
        assert result["parameters"]["text_query"] == "machine learning"

    def test_entity_statistics(self, templates):
        """Test entity statistics template."""
        result = templates.entity_statistics().build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "RETURN e.type as entity_type, count(e) as count" in result["query"]
        assert "ORDER BY count DESC" in result["query"]

    def test_relationship_statistics(self, templates):
        """Test relationship statistics template."""
        result = templates.relationship_statistics().build()

        assert "MATCH ()-[r]->()" in result["query"]
        assert "RETURN type(r) as relationship_type, count(r) as count" in result["query"]
        assert "ORDER BY count DESC" in result["query"]

    def test_orphan_entities(self, templates):
        """Test orphan entities template."""
        result = templates.orphan_entities().build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "WHERE (NOT (e)-[]-()" in result["query"]
        assert "RETURN e" in result["query"]

    def test_highly_connected(self, templates):
        """Test highly connected entities template."""
        result = templates.highly_connected(min_degree=10).build()

        assert "MATCH (e:Entity)-[r]-()" in result["query"]
        assert "WITH e, count(r) as degree" in result["query"]
        assert "WHERE (degree >= $min_degree)" in result["query"]
        assert "ORDER BY degree DESC" in result["query"]
        assert result["parameters"]["min_degree"] == 10

    def test_recent_entities(self, templates):
        """Test recent entities template."""
        result = templates.recent_entities(days=30).build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "WHERE (e.created_at >= datetime() - duration({days: $days}))" in result["query"]
        assert "ORDER BY e.created_at DESC" in result["query"]
        assert result["parameters"]["days"] == 30

    def test_entity_evolution(self, templates):
        """Test entity evolution template."""
        result = templates.entity_evolution("entity-123").build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "WHERE (e.id = $entity_id)" in result["query"]
        assert "HAS_VERSION" in result["query"]
        assert "EntityVersion" in result["query"]
        assert result["parameters"]["entity_id"] == "entity-123"

    def test_community_entities(self, templates):
        """Test community entities template."""
        result = templates.community_entities("community-1").build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "WHERE (e.community_id = $community_id)" in result["query"]
        assert result["parameters"]["community_id"] == "community-1"

    def test_community_entities_numeric_id(self, templates):
        """Test community entities with numeric ID."""
        result = templates.community_entities(42).build()

        assert result["parameters"]["community_id"] == 42

    def test_entity_similarity(self, templates):
        """Test entity similarity template."""
        result = templates.entity_similarity("entity-123", min_common_neighbors=3, limit=10).build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "(e)-[]-(common)-[]-(similar:Entity)" in result["query"]
        assert "WHERE (e <> similar)" in result["query"]
        assert "common_count >= $min_common_neighbors" in result["query"]
        assert "ORDER BY common_count DESC" in result["query"]
        assert "LIMIT 10" in result["query"]
        assert result["parameters"]["min_common_neighbors"] == 3

    def test_relationship_path(self, templates):
        """Test relationship path template."""
        rel_types = ["KNOWS", "WORKS_WITH"]
        result = templates.relationship_path("entity-1", "entity-2", rel_types, max_hops=3).build()

        assert "MATCH (source:Entity), (target:Entity)" in result["query"]
        assert "KNOWS|WORKS_WITH" in result["query"]
        assert "*1..3" in result["query"]
        assert result["parameters"]["rel_types"] == rel_types
        assert result["parameters"]["max_hops"] == 3

    def test_entity_degree_distribution(self, templates):
        """Test entity degree distribution template."""
        result = templates.entity_degree_distribution().build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "WITH e, size((e)-[]-()) as degree" in result["query"]
        assert "RETURN degree, count(*) as entity_count" in result["query"]
        assert "ORDER BY degree ASC" in result["query"]

    def test_connected_components(self, templates):
        """Test connected components template."""
        result = templates.connected_components(min_size=5).build()

        assert "MATCH (e:Entity)" in result["query"]
        assert "WHERE (e.component_id IS NOT NULL)" in result["query"]
        assert "size(entities) >= $min_size" in result["query"]
        assert "ORDER BY component_size DESC" in result["query"]
        assert result["parameters"]["min_size"] == 5

    def test_template_returns_builder(self, templates):
        """Test that templates return CypherQueryBuilder for chaining."""
        builder = templates.entity_lookup("Test")

        # Should be able to chain additional methods
        result = builder.limit(5).order_by("e.name").build()

        assert "LIMIT 5" in result["query"]
        assert "ORDER BY e.name" in result["query"]

    def test_all_templates_generate_valid_queries(self, templates):
        """Test that all templates generate non-empty queries."""
        template_methods = [
            lambda: templates.entity_lookup("Test"),
            lambda: templates.entity_neighbors("entity-123"),
            lambda: templates.shortest_path("e1", "e2"),
            lambda: templates.entity_relationships("entity-123"),
            lambda: templates.subgraph_extraction(["e1", "e2"]),
            lambda: templates.entity_by_type("Person"),
            lambda: templates.relationship_by_type("KNOWS"),
            lambda: templates.entity_search("test"),
            lambda: templates.entity_statistics(),
            lambda: templates.relationship_statistics(),
            lambda: templates.orphan_entities(),
            lambda: templates.highly_connected(),
            lambda: templates.recent_entities(),
            lambda: templates.entity_evolution("entity-123"),
            lambda: templates.community_entities("comm-1"),
            lambda: templates.entity_similarity("entity-123"),
            lambda: templates.relationship_path("e1", "e2", ["KNOWS"]),
            lambda: templates.entity_degree_distribution(),
            lambda: templates.connected_components(),
        ]

        for template_method in template_methods:
            result = template_method().build()
            assert len(result["query"]) > 0
            assert "MATCH" in result["query"] or "CREATE" in result["query"]

    def test_parameterization_prevents_injection(self, templates):
        """Test that all parameters are properly parameterized."""
        # Try malicious input
        malicious = "'; DROP TABLE entities; --"
        result = templates.entity_lookup(malicious).build()

        # Malicious code should be in parameters, not query
        assert "DROP TABLE" not in result["query"]
        assert result["parameters"]["name"] == malicious

    def test_entity_lookup_with_name_instead_of_id(self, templates):
        """Test entity lookup works with names."""
        result = templates.entity_neighbors("John Doe", depth=1).build()

        # Should use name instead of id
        assert "e.name = $entity_id" in result["query"]
        assert result["parameters"]["entity_id"] == "John Doe"

    def test_shortest_path_with_names(self, templates):
        """Test shortest path with entity names instead of IDs."""
        result = templates.shortest_path("Alice", "Bob", max_hops=3).build()

        assert "source.name = $source_id" in result["query"]
        assert "target.name = $target_id" in result["query"]
        assert result["parameters"]["source_id"] == "Alice"
        assert result["parameters"]["target_id"] == "Bob"
