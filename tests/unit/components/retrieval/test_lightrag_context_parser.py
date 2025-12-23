"""Unit tests for LightRAG Context Parser.

Sprint 51 - Feature 51.7: Maximum Hybrid Search Foundation

Tests for parsing LightRAG local/global context strings into structured entities.
"""

from src.components.retrieval.lightrag_context_parser import (
    _infer_entity_type,
    extract_entity_names,
    parse_lightrag_global_context,
    parse_lightrag_local_context,
)


class TestParseLightRAGLocalContext:
    """Tests for parse_lightrag_local_context()."""

    def test_parse_empty_context(self):
        """Test parsing empty context string."""
        result = parse_lightrag_local_context("")
        assert result["entities"] == []
        assert result["relationships"] == []

    def test_parse_entities_section(self):
        """Test parsing entities from local context."""
        context = """# Entities
- Amsterdam: Capital city of the Netherlands
- Netherlands: Country in Western Europe
- Europe: Continent with 44 countries
"""
        result = parse_lightrag_local_context(context)

        assert len(result["entities"]) == 3
        assert result["entities"][0]["name"] == "Amsterdam"
        assert result["entities"][0]["description"] == "Capital city of the Netherlands"
        assert result["entities"][0]["type"] == "LOCATION"
        assert result["entities"][0]["source"] == "lightrag_local"

        assert result["entities"][1]["name"] == "Netherlands"
        assert result["entities"][2]["name"] == "Europe"

    def test_parse_relationships_section(self):
        """Test parsing relationships from local context."""
        context = """# Relationships
- Amsterdam -> Netherlands: Located in
- Netherlands -> Europe: Part of
"""
        result = parse_lightrag_local_context(context)

        assert len(result["relationships"]) == 2
        assert result["relationships"][0]["source"] == "Amsterdam"
        assert result["relationships"][0]["target"] == "Netherlands"
        assert result["relationships"][0]["description"] == "Located in"

    def test_parse_combined_context(self):
        """Test parsing context with both entities and relationships."""
        context = """# Entities
- Amsterdam: Capital city
- Netherlands: Country

# Relationships
- Amsterdam -> Netherlands: Located in
"""
        result = parse_lightrag_local_context(context)

        assert len(result["entities"]) == 2
        assert len(result["relationships"]) == 1

    def test_parse_malformed_lines(self):
        """Test handling malformed lines gracefully."""
        context = """# Entities
- Amsterdam: Capital city
This line has no dash
- Netherlands: Country
No colon here
"""
        result = parse_lightrag_local_context(context)

        # Should only parse valid lines
        assert len(result["entities"]) == 2
        assert result["entities"][0]["name"] == "Amsterdam"
        assert result["entities"][1]["name"] == "Netherlands"


class TestParseLightRAGGlobalContext:
    """Tests for parse_lightrag_global_context()."""

    def test_parse_empty_context(self):
        """Test parsing empty context string."""
        result = parse_lightrag_global_context("")
        assert result["communities"] == []
        assert result["entities"] == []

    def test_parse_single_community(self):
        """Test parsing single community."""
        context = """## Community 1
- Theme: European Geography
- Entities: Amsterdam, Netherlands, Europe
- Description: Major cities and countries in Europe
"""
        result = parse_lightrag_global_context(context)

        assert len(result["communities"]) == 1
        community = result["communities"][0]

        assert community["id"] == "community_1"
        assert community["theme"] == "European Geography"
        assert community["entities"] == ["Amsterdam", "Netherlands", "Europe"]
        assert community["description"] == "Major cities and countries in Europe"

        # Check flat entities list
        assert len(result["entities"]) == 3
        assert "Amsterdam" in result["entities"]

    def test_parse_multiple_communities(self):
        """Test parsing multiple communities."""
        context = """## Community 1
- Theme: Geography
- Entities: Amsterdam, Netherlands

## Community 2
- Theme: Technology
- Entities: Python, FastAPI
"""
        result = parse_lightrag_global_context(context)

        assert len(result["communities"]) == 2
        assert result["communities"][0]["theme"] == "Geography"
        assert result["communities"][1]["theme"] == "Technology"

        # Check all entities collected
        assert len(result["entities"]) == 4

    def test_parse_malformed_community(self):
        """Test handling malformed community sections."""
        context = """## Community 1
- Theme: Geography
This line is invalid
- Entities: Amsterdam
"""
        result = parse_lightrag_global_context(context)

        assert len(result["communities"]) == 1
        assert result["communities"][0]["theme"] == "Geography"


class TestInferEntityType:
    """Tests for _infer_entity_type() heuristic function."""

    def test_infer_location(self):
        """Test inferring LOCATION type."""
        assert _infer_entity_type("Amsterdam", "Capital city of Netherlands") == "LOCATION"
        assert _infer_entity_type("USA", "Country in North America") == "LOCATION"
        assert _infer_entity_type("California", "Province in the USA") == "LOCATION"

    def test_infer_person(self):
        """Test inferring PERSON type."""
        assert _infer_entity_type("John Doe", "CEO of Company X") == "PERSON"
        assert _infer_entity_type("Jane Smith", "Founder of startup") == "PERSON"

    def test_infer_organization(self):
        """Test inferring ORGANIZATION type."""
        assert _infer_entity_type("Google", "Technology company") == "ORGANIZATION"
        assert _infer_entity_type("NASA", "Space organization") == "ORGANIZATION"

    def test_infer_technology(self):
        """Test inferring TECHNOLOGY type."""
        assert _infer_entity_type("Python", "Programming language framework") == "TECHNOLOGY"
        assert _infer_entity_type("PostgreSQL", "Database system") == "TECHNOLOGY"

    def test_infer_concept(self):
        """Test inferring CONCEPT type."""
        assert _infer_entity_type("RAG", "Retrieval method for LLMs") == "CONCEPT"
        assert _infer_entity_type("Fusion", "Algorithm for combining results") == "CONCEPT"

    def test_infer_default(self):
        """Test default fallback type."""
        assert _infer_entity_type("Unknown", "No clear indicators") == "ENTITY"


class TestExtractEntityNames:
    """Tests for extract_entity_names() utility function."""

    def test_extract_from_local_result(self):
        """Test extracting entity names from local parsing result."""
        parsed = {
            "entities": [
                {"name": "Amsterdam", "type": "LOCATION"},
                {"name": "Netherlands", "type": "LOCATION"},
            ],
            "relationships": [],
        }

        entity_names = extract_entity_names(parsed)
        assert len(entity_names) == 2
        assert "Amsterdam" in entity_names
        assert "Netherlands" in entity_names

    def test_extract_from_global_result(self):
        """Test extracting entity names from global parsing result."""
        parsed = {
            "communities": [
                {"id": "1", "entities": ["Amsterdam", "Netherlands"]},
                {"id": "2", "entities": ["Python", "FastAPI"]},
            ],
            "entities": ["Amsterdam", "Netherlands", "Python", "FastAPI"],
        }

        entity_names = extract_entity_names(parsed)
        assert len(entity_names) == 4
        assert "Amsterdam" in entity_names
        assert "Python" in entity_names

    def test_extract_deduplicated(self):
        """Test that entity names are deduplicated."""
        parsed = {
            "entities": [
                {"name": "Amsterdam", "type": "LOCATION"},
                {"name": "Amsterdam", "type": "LOCATION"},  # Duplicate
            ],
        }

        entity_names = extract_entity_names(parsed)
        assert len(entity_names) == 1
        assert entity_names == ["Amsterdam"]

    def test_extract_from_empty_result(self):
        """Test extracting from empty result."""
        parsed = {"entities": [], "communities": []}
        entity_names = extract_entity_names(parsed)
        assert entity_names == []
