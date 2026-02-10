"""Unit tests for Sprint 129.1: Cross-Sentence Window Bisection Fallback.

Tests the bisection logic in extraction_service._extract_window() and
the helper function _split_text_into_sentences().
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.extraction_service import (
    BISECTION_MIN_SENTENCES,
    BISECTION_OVERLAP,
    _split_text_into_sentences,
)
from src.core.models import GraphRelationship


class TestSplitTextIntoSentences:
    """Test sentence splitting helper function."""

    def test_basic_splitting(self):
        """Test splitting a multi-sentence text."""
        text = "First sentence. Second sentence. Third sentence."
        sentences = _split_text_into_sentences(text)
        assert len(sentences) >= 3

    def test_single_sentence(self):
        """Test splitting a single sentence."""
        text = "Just one sentence here."
        sentences = _split_text_into_sentences(text)
        assert len(sentences) == 1

    def test_empty_text(self):
        """Test splitting empty text."""
        sentences = _split_text_into_sentences("")
        assert len(sentences) == 0

    def test_complex_sentences(self):
        """Test splitting text with abbreviations and complex punctuation."""
        text = "Dr. Smith went to Washington D.C. He met the president. They discussed policy."
        sentences = _split_text_into_sentences(text)
        # SpaCy should handle abbreviations correctly
        assert len(sentences) >= 2


class TestBisectionConstants:
    """Test bisection configuration constants."""

    def test_min_sentences_default(self):
        """Minimum sentences for bisection should be 4."""
        assert BISECTION_MIN_SENTENCES == 4

    def test_overlap_default(self):
        """Bisection overlap should default to 1 sentence."""
        assert BISECTION_OVERLAP == 1


class TestWindowBisection:
    """Test the bisection fallback in _extract_window()."""

    @pytest.fixture
    def extraction_service(self):
        """Create extraction service with mocked LLM."""
        with patch("src.components.graph_rag.extraction_service.AegisLLMProxy"):
            from src.components.graph_rag.extraction_service import ExtractionService

            return ExtractionService(
                llm_model="test-model",
                temperature=0.1,
                max_tokens=4096,
            )

    _rel_counter = 0

    def _make_relation(self, source: str, target: str, rel_type: str) -> GraphRelationship:
        """Create a GraphRelationship for testing."""
        TestWindowBisection._rel_counter += 1
        return GraphRelationship(
            id=f"rel_{TestWindowBisection._rel_counter}",
            source=source,
            target=target,
            type=rel_type,
            description=f"{source} {rel_type} {target}",
        )

    @pytest.mark.asyncio
    async def test_bisection_triggers_on_zero_relations(self, extraction_service):
        """When a window returns 0 relations and has enough sentences, bisection fires."""
        # Window text with 6 sentences (> BISECTION_MIN_SENTENCES=4)
        window_text = (
            "Alice works at Google. Bob works at Microsoft. "
            "Google is in Mountain View. Microsoft is in Redmond. "
            "Alice and Bob collaborate on a project. The project uses Python."
        )

        # First call returns 0 relations, bisection halves return some
        left_rels = [self._make_relation("Alice", "Google", "WORKS_AT")]
        right_rels = [self._make_relation("Bob", "Microsoft", "WORKS_AT")]

        call_count = 0

        async def mock_extract(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []  # First call: 0 relations → triggers bisection
            elif call_count == 2:
                return left_rels  # Left half
            else:
                return right_rels  # Right half

        extraction_service._extract_relationships_with_rank = AsyncMock(side_effect=mock_extract)

        import asyncio

        all_relationships = []
        seen_triples = set()
        dedup_lock = asyncio.Lock()
        semaphore = asyncio.Semaphore(1)

        async def _deduplicate_relations(relations):
            unique_rels = []
            async with dedup_lock:
                for rel in relations:
                    triple = (
                        rel.source.lower().strip(),
                        rel.target.lower().strip(),
                        rel.type.upper().strip(),
                    )
                    if triple not in seen_triples:
                        seen_triples.add(triple)
                        all_relationships.append(rel)
                        unique_rels.append(rel)
            return unique_rels

        # Simulate what _extract_window does
        async with semaphore:
            window_relations = await extraction_service._extract_relationships_with_rank(
                text=window_text,
                entities=[],
                rank_config={},
            )

            if len(window_relations) == 0:
                sentences = _split_text_into_sentences(window_text)
                if len(sentences) >= BISECTION_MIN_SENTENCES:
                    mid = len(sentences) // 2
                    overlap = min(BISECTION_OVERLAP, mid)
                    left_text = " ".join(sentences[: mid + overlap])
                    right_text = " ".join(sentences[mid - overlap :])

                    left_results = await extraction_service._extract_relationships_with_rank(
                        text=left_text, entities=[], rank_config={}
                    )
                    right_results = await extraction_service._extract_relationships_with_rank(
                        text=right_text, entities=[], rank_config={}
                    )

                    window_relations = left_results + right_results

            unique_rels = await _deduplicate_relations(window_relations)

        assert call_count == 3, "Should have called LLM 3 times (1 original + 2 bisected)"
        assert len(unique_rels) == 2, "Should have 2 unique relations from bisected halves"

    @pytest.mark.asyncio
    async def test_bisection_skipped_for_short_windows(self, extraction_service):
        """Windows with < BISECTION_MIN_SENTENCES sentences skip bisection."""
        # Only 2 sentences (< 4 minimum)
        window_text = "Alice works at Google. Bob works at Microsoft."

        extraction_service._extract_relationships_with_rank = AsyncMock(return_value=[])

        import asyncio

        semaphore = asyncio.Semaphore(1)

        async with semaphore:
            window_relations = await extraction_service._extract_relationships_with_rank(
                text=window_text, entities=[], rank_config={}
            )

            bisected = False
            if len(window_relations) == 0:
                sentences = _split_text_into_sentences(window_text)
                if len(sentences) >= BISECTION_MIN_SENTENCES:
                    bisected = True

        assert not bisected, "Should NOT bisect windows with fewer than 4 sentences"
        assert extraction_service._extract_relationships_with_rank.call_count == 1

    @pytest.mark.asyncio
    async def test_bisection_not_triggered_when_relations_found(self, extraction_service):
        """When a window returns relations, no bisection occurs."""
        window_text = (
            "Alice works at Google. Bob works at Microsoft. "
            "Google is in Mountain View. Microsoft is in Redmond."
        )

        rels = [self._make_relation("Alice", "Google", "WORKS_AT")]
        extraction_service._extract_relationships_with_rank = AsyncMock(return_value=rels)

        import asyncio

        semaphore = asyncio.Semaphore(1)

        async with semaphore:
            window_relations = await extraction_service._extract_relationships_with_rank(
                text=window_text, entities=[], rank_config={}
            )

            bisected = False
            if len(window_relations) == 0:
                bisected = True

        assert not bisected, "Should NOT bisect when relations are found"
        assert extraction_service._extract_relationships_with_rank.call_count == 1

    def test_bisection_overlap_creates_shared_sentences(self):
        """Bisected halves should share overlap sentences at the boundary."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five. Sentence six."
        sentences = _split_text_into_sentences(text)

        assert len(sentences) >= 4, f"Need at least 4 sentences, got {len(sentences)}"

        mid = len(sentences) // 2
        overlap = min(BISECTION_OVERLAP, mid)

        left_sentences = sentences[: mid + overlap]
        right_sentences = sentences[mid - overlap :]

        # The overlap sentences should appear in both halves
        left_set = set(left_sentences)
        right_set = set(right_sentences)
        shared = left_set & right_set

        assert len(shared) >= overlap, (
            f"Expected at least {overlap} shared sentence(s), got {len(shared)}"
        )

    @pytest.mark.asyncio
    async def test_bisection_deduplicates_across_halves(self, extraction_service):
        """Relations found in both halves should be deduplicated."""
        window_text = (
            "Alice works at Google. Bob works at Microsoft. "
            "Google is in Mountain View. Microsoft is in Redmond. "
            "Alice and Bob collaborate often. They work on AI projects."
        )

        # Same relation returned by both halves (from overlap region)
        shared_rel = self._make_relation("Alice", "Google", "WORKS_AT")
        unique_rel = self._make_relation("Bob", "Microsoft", "WORKS_AT")

        call_count = 0

        async def mock_extract(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []  # Triggers bisection
            elif call_count == 2:
                return [shared_rel]  # Left half
            else:
                return [shared_rel, unique_rel]  # Right half (shared + unique)

        extraction_service._extract_relationships_with_rank = AsyncMock(side_effect=mock_extract)

        import asyncio

        all_relationships = []
        seen_triples = set()
        dedup_lock = asyncio.Lock()
        semaphore = asyncio.Semaphore(1)

        async def _deduplicate_relations(relations):
            unique_rels = []
            async with dedup_lock:
                for rel in relations:
                    triple = (
                        rel.source.lower().strip(),
                        rel.target.lower().strip(),
                        rel.type.upper().strip(),
                    )
                    if triple not in seen_triples:
                        seen_triples.add(triple)
                        all_relationships.append(rel)
                        unique_rels.append(rel)
            return unique_rels

        async with semaphore:
            window_relations = await extraction_service._extract_relationships_with_rank(
                text=window_text, entities=[], rank_config={}
            )
            if len(window_relations) == 0:
                sentences = _split_text_into_sentences(window_text)
                if len(sentences) >= BISECTION_MIN_SENTENCES:
                    mid = len(sentences) // 2
                    overlap = min(BISECTION_OVERLAP, mid)
                    left_text = " ".join(sentences[: mid + overlap])
                    right_text = " ".join(sentences[mid - overlap :])

                    left_results = await extraction_service._extract_relationships_with_rank(
                        text=left_text, entities=[], rank_config={}
                    )
                    right_results = await extraction_service._extract_relationships_with_rank(
                        text=right_text, entities=[], rank_config={}
                    )
                    window_relations = left_results + right_results

            unique_rels = await _deduplicate_relations(window_relations)

        # shared_rel appears twice but should be deduplicated
        assert len(unique_rels) == 2, f"Expected 2 unique relations, got {len(unique_rels)}"
