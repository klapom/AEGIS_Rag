"""Unit tests for Entity Canonicalization.

Sprint 85 Feature 85.4: Entity Canonicalization (Embedding-based)
"""

import pytest

from src.components.graph_rag.entity_canonicalization import (
    CanonicalEntity,
    EntityCanonicalizer,
    get_entity_canonicalizer,
)
from src.core.models import GraphEntity


class TestEntityCanonicalizer:
    """Test EntityCanonicalizer class."""

    @pytest.fixture
    def canonicalizer(self) -> EntityCanonicalizer:
        """Create canonicalizer instance (no embeddings for fast tests)."""
        return EntityCanonicalizer(use_embeddings=False)

    def test_normalize_basic(self, canonicalizer: EntityCanonicalizer) -> None:
        """Test basic normalization."""
        assert canonicalizer.normalize("NVIDIA RTX 3060") == "nvidia_rtx_3060"
        assert canonicalizer.normalize("Machine Learning") == "machine_learning"
        assert canonicalizer.normalize("  SpaCy  ") == "spacy"

    def test_normalize_special_chars(self, canonicalizer: EntityCanonicalizer) -> None:
        """Test special character removal."""
        assert canonicalizer.normalize("Machine Learning (ML)") == "machine_learning_ml"
        assert canonicalizer.normalize("C++") == "c"
        assert canonicalizer.normalize("Neo4j 5.24") == "neo4j_524"

    def test_normalize_unicode(self, canonicalizer: EntityCanonicalizer) -> None:
        """Test unicode handling."""
        assert canonicalizer.normalize("Königsberg") == "königsberg"
        assert canonicalizer.normalize("北京") == "北京"

    def test_levenshtein_distance(self, canonicalizer: EntityCanonicalizer) -> None:
        """Test Levenshtein distance calculation."""
        assert canonicalizer._levenshtein_distance("kitten", "sitting") == 3
        assert canonicalizer._levenshtein_distance("saturday", "sunday") == 3
        assert canonicalizer._levenshtein_distance("test", "test") == 0
        assert canonicalizer._levenshtein_distance("", "abc") == 3

    def test_create_canonical(self, canonicalizer: EntityCanonicalizer) -> None:
        """Test creating a canonical entity."""
        entity = GraphEntity(
            id="1",
            name="Machine Learning",
            type="CONCEPT",
            description="A field of AI",
            confidence=0.9,
        )

        canonical = canonicalizer.create_canonical(entity, chunk_id="chunk_001")

        assert canonical.canonical_id == "machine_learning"
        assert "Machine Learning" in canonical.surface_forms
        assert canonical.entity_type == "CONCEPT"
        assert "A field of AI" in canonical.merged_descriptions
        assert "chunk_001" in canonical.source_chunks

    def test_merge_entity(self, canonicalizer: EntityCanonicalizer) -> None:
        """Test merging entity into existing canonical."""
        canonical = CanonicalEntity(
            canonical_id="machine_learning",
            surface_forms={"Machine Learning"},
            entity_type="CONCEPT",
            merged_descriptions=["A field of AI"],
            source_chunks=["chunk_001"],
            confidence=0.9,
        )

        new_entity = GraphEntity(
            id="2",
            name="ML",  # Different surface form
            type="CONCEPT",
            description="Subset of artificial intelligence",
            confidence=0.8,
        )

        result = canonicalizer.merge_entity(new_entity, canonical, chunk_id="chunk_002")

        assert "ML" in result.surface_forms
        assert "Machine Learning" in result.surface_forms
        assert len(result.merged_descriptions) == 2
        assert "chunk_002" in result.source_chunks

    def test_primary_name_longest(self, canonicalizer: EntityCanonicalizer) -> None:
        """Test that primary_name returns longest surface form, alphabetically first if tie."""
        canonical = CanonicalEntity(
            canonical_id="ml",
            surface_forms={"ML", "Machine Learning", "machine-learning"},
        )

        # Both "Machine Learning" and "machine-learning" are 16 chars
        # Alphabetically (case-sensitive), "M" < "m", so "Machine Learning" wins
        assert canonical.primary_name == "Machine Learning"

    def test_to_graph_entity(self, canonicalizer: EntityCanonicalizer) -> None:
        """Test conversion back to GraphEntity."""
        canonical = CanonicalEntity(
            canonical_id="neo4j",
            surface_forms={"Neo4j Database", "neo4j"},  # Different lengths
            entity_type="TECHNOLOGY",
            merged_descriptions=["Graph database"],
            source_chunks=["chunk_001"],
            confidence=0.95,
        )

        graph_entity = canonical.to_graph_entity()

        assert graph_entity.name == "Neo4j Database"  # Longest surface form
        assert graph_entity.type == "TECHNOLOGY"
        assert graph_entity.properties["canonical_id"] == "neo4j"


class TestEntityCanonicalizerAsync:
    """Test async methods of EntityCanonicalizer."""

    @pytest.fixture
    def canonicalizer(self) -> EntityCanonicalizer:
        """Create canonicalizer without embeddings for fast tests."""
        return EntityCanonicalizer(use_embeddings=False)

    @pytest.mark.asyncio
    async def test_find_canonical_match_exact(
        self, canonicalizer: EntityCanonicalizer
    ) -> None:
        """Test exact match finding."""
        existing = [
            CanonicalEntity(
                canonical_id="machine_learning",
                surface_forms={"Machine Learning"},
            ),
        ]

        entity = GraphEntity(
            id="1",
            name="machine learning",  # Same when normalized
            type="CONCEPT",
        )

        match = await canonicalizer.find_canonical_match(entity, existing)

        assert match is not None
        assert match.canonical_id == "machine_learning"

    @pytest.mark.asyncio
    async def test_find_canonical_match_levenshtein(
        self, canonicalizer: EntityCanonicalizer
    ) -> None:
        """Test Levenshtein distance matching."""
        existing = [
            CanonicalEntity(
                canonical_id="test",
                surface_forms={"Test", "test"},
            ),
        ]

        entity = GraphEntity(
            id="1",
            name="Tets",  # Typo, distance = 1
            type="CONCEPT",
        )

        match = await canonicalizer.find_canonical_match(entity, existing)

        assert match is not None
        assert match.canonical_id == "test"

    @pytest.mark.asyncio
    async def test_canonicalize_entities_dedup(
        self, canonicalizer: EntityCanonicalizer
    ) -> None:
        """Test entity deduplication via canonicalization."""
        entities = [
            GraphEntity(id="1", name="Machine Learning", type="CONCEPT"),
            GraphEntity(id="2", name="machine learning", type="CONCEPT"),  # Duplicate
            GraphEntity(id="3", name="ML", type="CONCEPT"),  # Short name match
            GraphEntity(id="4", name="Deep Learning", type="CONCEPT"),  # Different
        ]

        canonicals, dupes = await canonicalizer.canonicalize_entities(entities)

        # Should deduplicate "Machine Learning" and "machine learning"
        # "ML" might match due to short name
        assert len(canonicals) <= 3  # At most 3 unique (ML might match machine_learning)
        assert dupes >= 1  # At least one duplicate


class TestGetEntityCanonicalizer:
    """Test singleton getter."""

    def test_singleton(self) -> None:
        """Test that singleton returns same instance."""
        c1 = get_entity_canonicalizer()
        c2 = get_entity_canonicalizer()

        assert c1 is c2
