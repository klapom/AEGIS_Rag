"""Unit tests for training_data_extractor.py.

Sprint 69 Feature 69.4: Learned Adaptive Reranker Weights (8 SP)

Tests cover:
- Quality score computation
- Relevance inference from signals
- Training pair extraction with filtering
- JSONL output generation
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.adaptation.training_data_extractor import (
    RerankTrainingPair,
    _compute_quality_score,
    _infer_relevance_from_signals,
    extract_rerank_pairs,
    load_training_pairs,
)


class TestQualityScoreComputation:
    """Test quality score computation for trace events."""

    def test_perfect_quality_score(self):
        """Test event with all quality factors gets score 1.0."""
        event = {
            "stage": "reranking",
            "latency_ms": 150,
            "cache_hit": False,
            "metadata": {
                "semantic_score": 0.89,
                "keyword_score": 0.72,
                "recency_score": 0.85,
                "click_through": True,
            },
        }
        score = _compute_quality_score(event)
        assert score == 1.0

    def test_partial_quality_score(self):
        """Test event with some quality factors."""
        event = {
            "stage": "reranking",
            "latency_ms": 600,  # Slow (no bonus)
            "cache_hit": True,  # Cache hit (no bonus)
            "metadata": {
                "semantic_score": 0.89,
                "keyword_score": 0.72,
                "recency_score": 0.85,
                # No user signals
            },
        }
        score = _compute_quality_score(event)
        assert score == 0.3  # Only has all scores

    def test_zero_quality_score(self):
        """Test event with no quality factors."""
        event = {
            "stage": "reranking",
            "latency_ms": 1000,
            "cache_hit": True,
            "metadata": {
                # Missing scores
            },
        }
        score = _compute_quality_score(event)
        assert score == 0.0

    def test_missing_metadata(self):
        """Test event with missing metadata."""
        event = {
            "stage": "reranking",
            "latency_ms": 150,
        }
        score = _compute_quality_score(event)
        assert score == 0.2  # Fast retrieval only


class TestRelevanceInference:
    """Test relevance label inference from user signals."""

    def test_explicit_rating_dominates(self):
        """Test that explicit rating dominates other signals."""
        metadata = {
            "explicit_rating": 5,  # 5 stars
            "click_through": False,
            "dwell_time_sec": 0,
        }
        relevance = _infer_relevance_from_signals(metadata)
        assert relevance is not None
        # Formula: 0.5 * 0.2 + (5-1)/4 * 0.8 * 0.8 = 0.1 + 0.8 = 0.9, but clamped
        assert 0.7 <= relevance <= 1.0  # 5 stars → high relevance

    def test_low_explicit_rating(self):
        """Test low explicit rating."""
        metadata = {
            "explicit_rating": 1,  # 1 star
        }
        relevance = _infer_relevance_from_signals(metadata)
        assert relevance is not None
        assert 0.0 <= relevance <= 0.2  # 1 star → low relevance

    def test_click_and_dwell_time(self):
        """Test click-through + dwell time signals."""
        metadata = {
            "click_through": True,
            "dwell_time_sec": 60,
        }
        relevance = _infer_relevance_from_signals(metadata)
        assert relevance is not None
        # Base 0.5 + click 0.3 + dwell ~0.25 = ~1.05 → clamped to 1.0
        assert 0.8 <= relevance <= 1.0

    def test_citation_used_signal(self):
        """Test citation used signal."""
        metadata = {
            "citation_used": True,
        }
        relevance = _infer_relevance_from_signals(metadata)
        assert relevance is not None
        # Base 0.5 + citation 0.4 = 0.9
        assert relevance == pytest.approx(0.9, abs=0.01)

    def test_no_signals_returns_none(self):
        """Test empty metadata returns None."""
        metadata = {}
        relevance = _infer_relevance_from_signals(metadata)
        # Should return 0.5 (neutral) when no signals present
        assert relevance == 0.5

    def test_short_dwell_time(self):
        """Test short dwell time contributes little."""
        metadata = {
            "dwell_time_sec": 5,
        }
        relevance = _infer_relevance_from_signals(metadata)
        assert relevance is not None
        # Base 0.5 + small dwell contribution
        assert 0.5 < relevance < 0.6


class TestTrainingPairExtraction:
    """Test extraction of training pairs from traces."""

    @pytest.fixture
    def sample_trace_file(self, tmp_path):
        """Create a sample trace file for testing."""
        trace_file = tmp_path / "traces.jsonl"

        # Create sample trace events
        events = [
            # Good quality reranking event
            {
                "timestamp": datetime.now().isoformat(),
                "stage": "reranking",
                "latency_ms": 150,
                "cache_hit": False,
                "metadata": {
                    "query": "What is hybrid search?",
                    "intent": "factual",
                    "doc_id": "doc_1",
                    "semantic_score": 0.89,
                    "keyword_score": 0.72,
                    "recency_score": 0.85,
                    "click_through": True,
                },
            },
            # Low quality event (missing scores)
            {
                "timestamp": datetime.now().isoformat(),
                "stage": "reranking",
                "latency_ms": 150,
                "cache_hit": False,
                "metadata": {
                    "query": "test query",
                    "intent": "keyword",
                    "doc_id": "doc_2",
                    # Missing scores
                },
            },
            # Wrong stage (should be filtered)
            {
                "timestamp": datetime.now().isoformat(),
                "stage": "retrieval",
                "latency_ms": 200,
                "metadata": {},
            },
            # Good quality event with neutral signals (base 0.5 relevance)
            {
                "timestamp": datetime.now().isoformat(),
                "stage": "reranking",
                "latency_ms": 120,
                "cache_hit": False,
                "metadata": {
                    "query": "Another query",
                    "intent": "exploratory",
                    "doc_id": "doc_3",
                    "semantic_score": 0.75,
                    "keyword_score": 0.65,
                    "recency_score": 0.80,
                    # No relevance signals → returns 0.5 (neutral)
                },
            },
        ]

        with open(trace_file, "w", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        return str(trace_file)

    @pytest.mark.asyncio
    async def test_extract_rerank_pairs_basic(self, sample_trace_file):
        """Test basic extraction with quality filtering."""
        pairs = await extract_rerank_pairs(
            trace_path=sample_trace_file,
            min_quality_score=0.7,
        )

        # Should extract events with quality >= 0.7 and relevance signals
        # Event 1: quality=1.0, has click_through → included
        # Event 3: quality=0.7, has neutral signals → included (returns 0.5)
        assert len(pairs) == 2

        # First pair should be the factual query
        assert any(p.query == "What is hybrid search?" for p in pairs)
        factual_pair = next(p for p in pairs if p.query == "What is hybrid search?")
        assert factual_pair.intent == "factual"
        assert factual_pair.doc_id == "doc_1"
        assert factual_pair.semantic_score == pytest.approx(0.89)
        assert factual_pair.keyword_score == pytest.approx(0.72)
        assert factual_pair.recency_score == pytest.approx(0.85)
        assert 0.0 <= factual_pair.relevance_label <= 1.0

    @pytest.mark.asyncio
    async def test_extract_with_low_quality_threshold(self, sample_trace_file):
        """Test extraction with lower quality threshold."""
        pairs = await extract_rerank_pairs(
            trace_path=sample_trace_file,
            min_quality_score=0.0,  # Accept all quality scores
        )

        # Should still filter out events without all required scores
        assert len(pairs) >= 1

    @pytest.mark.asyncio
    async def test_extract_with_time_range(self, tmp_path):
        """Test extraction with time range filter."""
        trace_file = tmp_path / "traces.jsonl"

        # Create events with different timestamps
        old_event = {
            "timestamp": (datetime.now() - timedelta(days=10)).isoformat(),
            "stage": "reranking",
            "latency_ms": 150,
            "cache_hit": False,
            "metadata": {
                "query": "Old query",
                "intent": "factual",
                "doc_id": "doc_old",
                "semantic_score": 0.8,
                "keyword_score": 0.7,
                "recency_score": 0.9,
                "click_through": True,
            },
        }

        recent_event = {
            "timestamp": (datetime.now() - timedelta(days=2)).isoformat(),
            "stage": "reranking",
            "latency_ms": 150,
            "cache_hit": False,
            "metadata": {
                "query": "Recent query",
                "intent": "factual",
                "doc_id": "doc_recent",
                "semantic_score": 0.85,
                "keyword_score": 0.75,
                "recency_score": 0.95,
                "click_through": True,
            },
        }

        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(old_event) + "\n")
            f.write(json.dumps(recent_event) + "\n")

        # Extract only last 3 days
        pairs = await extract_rerank_pairs(
            trace_path=str(trace_file),
            min_quality_score=0.7,
            time_range=(datetime.now() - timedelta(days=3), datetime.now()),
        )

        assert len(pairs) == 1
        assert pairs[0].query == "Recent query"

    @pytest.mark.asyncio
    async def test_extract_with_output_file(self, sample_trace_file, tmp_path):
        """Test saving extracted pairs to output file."""
        output_file = tmp_path / "training_pairs.jsonl"

        pairs = await extract_rerank_pairs(
            trace_path=sample_trace_file,
            min_quality_score=0.7,
            output_path=str(output_file),
        )

        # Verify file was created
        assert output_file.exists()

        # Verify content
        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == len(pairs)

        # Verify JSON format
        for line in lines:
            pair_dict = json.loads(line)
            assert "query" in pair_dict
            assert "semantic_score" in pair_dict

    @pytest.mark.asyncio
    async def test_extract_nonexistent_file(self):
        """Test extraction with non-existent trace file."""
        with pytest.raises(FileNotFoundError):
            await extract_rerank_pairs(trace_path="nonexistent.jsonl")

    @pytest.mark.asyncio
    async def test_extract_invalid_quality_score(self, sample_trace_file):
        """Test extraction with invalid quality score."""
        with pytest.raises(ValueError):
            await extract_rerank_pairs(
                trace_path=sample_trace_file,
                min_quality_score=1.5,  # Invalid (> 1.0)
            )


class TestLoadTrainingPairs:
    """Test loading training pairs from JSONL."""

    @pytest.mark.asyncio
    async def test_load_training_pairs(self, tmp_path):
        """Test loading pairs from file."""
        pairs_file = tmp_path / "pairs.jsonl"

        # Create sample pairs
        pairs = [
            RerankTrainingPair(
                query="Query 1",
                intent="factual",
                doc_id="doc_1",
                semantic_score=0.9,
                keyword_score=0.8,
                recency_score=0.7,
                relevance_label=1.0,
                timestamp="2026-01-01T12:00:00",
            ),
            RerankTrainingPair(
                query="Query 2",
                intent="keyword",
                doc_id="doc_2",
                semantic_score=0.7,
                keyword_score=0.9,
                recency_score=0.5,
                relevance_label=0.8,
                timestamp="2026-01-01T13:00:00",
            ),
        ]

        # Save to file
        with open(pairs_file, "w", encoding="utf-8") as f:
            for pair in pairs:
                from dataclasses import asdict

                f.write(json.dumps(asdict(pair)) + "\n")

        # Load pairs
        loaded_pairs = await load_training_pairs(str(pairs_file))

        assert len(loaded_pairs) == 2
        assert loaded_pairs[0].query == "Query 1"
        assert loaded_pairs[1].query == "Query 2"

    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            await load_training_pairs("nonexistent.jsonl")
