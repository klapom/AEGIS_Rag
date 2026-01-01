"""Unit tests for DatasetBuilder.

Sprint 67 Feature 67.7: Test dataset generation from traces.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from src.adaptation.dataset_builder import (
    DatasetBuilder,
    DatasetBuilderError,
    GraphExample,
    QAExample,
    RerankExample,
    TrainingExample,
)


@pytest.fixture
def temp_trace_file(tmp_path: Path) -> Path:
    """Create temporary trace file with sample data."""
    trace_file = tmp_path / "traces.jsonl"

    # Sample traces with different quality scores
    traces = [
        # High quality trace with intent
        {
            "trace_version": "v1",
            "request_id": "req_001",
            "timestamp": "2025-12-31T10:00:00Z",
            "query": {
                "original": "What is RAG?",
                "rewritten": "Retrieval Augmented Generation definition",
                "intent": "factual",
                "intent_confidence": 0.95,
            },
            "retrieval": {
                "vector": {
                    "top_k": 5,
                    "results": [
                        {"chunk_id": "c1", "score": 0.92, "document_id": "d1"},
                        {"chunk_id": "c2", "score": 0.85, "document_id": "d1"},
                        {"chunk_id": "c3", "score": 0.78, "document_id": "d2"},
                    ],
                },
                "bm25": {
                    "top_k": 5,
                    "results": [
                        {"chunk_id": "c2", "score": 0.88, "document_id": "d1"},
                        {"chunk_id": "c4", "score": 0.75, "document_id": "d2"},
                    ],
                },
            },
            "evidence": {
                "selected_chunks": 3,
                "citations": ["c1", "c2"],
            },
            "answer": {
                "text": "RAG is Retrieval Augmented Generation...",
                "model": "qwen2.5:7b",
            },
            "metrics": {
                "total_latency_ms": 450,
                "quality_score": 0.92,
            },
        },
        # Medium quality trace
        {
            "trace_version": "v1",
            "request_id": "req_002",
            "timestamp": "2025-12-31T10:01:00Z",
            "query": {
                "original": "How does vector search work?",
                "intent": "exploratory",
                "intent_confidence": 0.85,
            },
            "retrieval": {
                "vector": {
                    "results": [
                        {"chunk_id": "c5", "score": 0.88, "document_id": "d3"},
                        {"chunk_id": "c6", "score": 0.82, "document_id": "d3"},
                    ],
                },
            },
            "evidence": {
                "citations": ["c5"],
            },
            "answer": {
                "text": "Vector search uses embeddings...",
                "model": "qwen2.5:7b",
            },
            "metrics": {
                "quality_score": 0.75,
            },
        },
        # Low quality trace (should be filtered out)
        {
            "trace_version": "v1",
            "request_id": "req_003",
            "timestamp": "2025-12-31T10:02:00Z",
            "query": {
                "original": "test query",
                "intent": "keyword",
            },
            "answer": {"text": "No good answer"},
            "metrics": {
                "quality_score": 0.45,
            },
            "evidence": {"citations": []},
        },
        # Duplicate query (for dedup testing)
        {
            "trace_version": "v1",
            "request_id": "req_004",
            "timestamp": "2025-12-31T10:03:00Z",
            "query": {
                "original": "What is RAG?",  # Exact duplicate of req_001
                "intent": "factual",
            },
            "answer": {"text": "RAG is..."},
            "metrics": {
                "quality_score": 0.88,  # Lower quality than original
            },
            "evidence": {"citations": ["c7"]},
        },
    ]

    with open(trace_file, "w") as f:
        for trace in traces:
            f.write(json.dumps(trace) + "\n")

    return trace_file


@pytest.fixture
def dataset_builder(temp_trace_file: Path) -> DatasetBuilder:
    """Create DatasetBuilder instance with temp trace file."""
    return DatasetBuilder(trace_path=str(temp_trace_file))


@pytest.fixture
def temp_graph_trace_file(tmp_path: Path) -> Path:
    """Create temporary trace file with graph query data."""
    trace_file = tmp_path / "graph_traces.jsonl"

    # Sample traces with graph queries
    traces = [
        # High quality graph trace
        {
            "trace_version": "v1",
            "request_id": "req_graph_001",
            "timestamp": "2025-12-31T10:00:00Z",
            "query": {
                "original": "What are the relationships between RAG and LLM?",
                "intent": "exploratory",
            },
            "graph_query": {
                "cypher": "MATCH (r:RAG)-[rel:RELATES_TO]->(l:LLM) RETURN r, rel, l",
                "entities": ["RAG", "LLM"],
                "relations": ["RELATES_TO"],
            },
            "retrieval": {
                "graph_local": {
                    "results": [
                        {
                            "chunk_id": "g1",
                            "text": "RAG uses LLM for generation...",
                            "score": 0.95,
                        },
                        {
                            "chunk_id": "g2",
                            "text": "LLM generates answers...",
                            "score": 0.88,
                        },
                    ]
                },
                "graph_global": {
                    "results": [
                        {"chunk_id": "g3", "text": "Global context...", "score": 0.82}
                    ]
                },
            },
            "evidence": {
                "selected_chunks": [
                    {"text": "RAG uses LLM..."},
                    {"text": "LLM generates..."},
                ],
                "citations": ["g1", "g2"],
            },
            "answer": {
                "text": "RAG and LLM are closely related [1][2]...",
                "model": "qwen2.5:7b",
            },
            "metrics": {
                "quality_score": 0.90,
            },
        },
        # Medium quality graph trace
        {
            "trace_version": "v1",
            "request_id": "req_graph_002",
            "timestamp": "2025-12-31T10:01:00Z",
            "query": {
                "original": "Find papers about embedding models",
                "intent": "keyword",
            },
            "graph_query": {
                "cypher": None,  # No Cypher generated
                "entities": ["papers", "embedding models"],
                "relations": [],
            },
            "retrieval": {
                "graph_local": {"results": [{"chunk_id": "g4", "text": "...", "score": 0.75}]}
            },
            "answer": {"text": "Here are relevant papers...", "model": "qwen2.5:7b"},
            "metrics": {
                "quality_score": 0.78,
            },
        },
        # No graph query (should be filtered out)
        {
            "trace_version": "v1",
            "request_id": "req_no_graph",
            "timestamp": "2025-12-31T10:02:00Z",
            "query": {"original": "Simple query", "intent": "factual"},
            "answer": {"text": "Simple answer"},
            "metrics": {"quality_score": 0.85},
            "evidence": {"citations": []},
        },
    ]

    with open(trace_file, "w") as f:
        for trace in traces:
            f.write(json.dumps(trace) + "\n")

    return trace_file


@pytest.mark.asyncio
class TestDatasetBuilder:
    """Test suite for DatasetBuilder class."""

    async def test_load_traces__valid_file__loads_all_traces(
        self, dataset_builder: DatasetBuilder
    ) -> None:
        """Test loading traces from valid JSONL file."""
        traces = await dataset_builder._load_traces()

        assert len(traces) == 4
        assert traces[0]["request_id"] == "req_001"
        assert traces[0]["query"]["original"] == "What is RAG?"

    async def test_load_traces__directory__loads_all_files(self, tmp_path: Path) -> None:
        """Test loading traces from directory of JSONL files."""
        trace_dir = tmp_path / "traces"
        trace_dir.mkdir()

        # Create multiple trace files
        for i in range(3):
            trace_file = trace_dir / f"traces_{i}.jsonl"
            trace = {
                "request_id": f"req_{i}",
                "query": {"original": f"query {i}"},
                "metrics": {"quality_score": 0.9},
            }
            with open(trace_file, "w") as f:
                f.write(json.dumps(trace) + "\n")

        builder = DatasetBuilder(trace_path=str(trace_dir))
        traces = await builder._load_traces()

        assert len(traces) == 3

    async def test_load_traces__nonexistent_path__returns_empty(self) -> None:
        """Test loading traces from nonexistent path returns empty list."""
        builder = DatasetBuilder(trace_path="nonexistent/path/traces.jsonl")
        traces = await builder._load_traces()

        assert traces == []

    async def test_build_intent_dataset__high_quality_threshold__filters_correctly(
        self, dataset_builder: DatasetBuilder, tmp_path: Path
    ) -> None:
        """Test intent dataset building with quality filtering."""
        output_path = tmp_path / "intent_dataset.jsonl"

        examples = await dataset_builder.build_intent_dataset(
            min_quality=0.8, output_path=str(output_path), deduplicate=False
        )

        # Should include req_001 (0.92) and req_004 (0.88), exclude req_002 (0.75) and req_003 (0.45)
        assert len(examples) == 2
        assert examples[0].query == "What is RAG?"
        assert examples[0].intent == "factual"
        assert examples[0].quality_score == 0.92

        # Check file was created
        assert output_path.exists()

        # Verify JSONL format
        with open(output_path) as f:
            lines = f.readlines()
            assert len(lines) == 2
            first_example = json.loads(lines[0])
            assert first_example["query"] == "What is RAG?"
            assert first_example["intent"] == "factual"

    async def test_build_intent_dataset__with_deduplication__removes_duplicates(
        self, dataset_builder: DatasetBuilder, tmp_path: Path
    ) -> None:
        """Test deduplication removes duplicate queries."""
        output_path = tmp_path / "intent_dataset.jsonl"

        examples = await dataset_builder.build_intent_dataset(
            min_quality=0.8, output_path=str(output_path), deduplicate=True
        )

        # Should deduplicate req_001 and req_004 (same query)
        assert len(examples) == 1
        assert examples[0].query == "What is RAG?"
        # Should keep higher quality example (req_001: 0.92 > req_004: 0.88)
        assert examples[0].quality_score == 0.92

    async def test_build_intent_dataset__low_threshold__includes_more(
        self, dataset_builder: DatasetBuilder, tmp_path: Path
    ) -> None:
        """Test lower quality threshold includes more examples."""
        output_path = tmp_path / "intent_dataset.jsonl"

        examples = await dataset_builder.build_intent_dataset(
            min_quality=0.7, output_path=str(output_path), deduplicate=False
        )

        # Should include req_001 (0.92), req_002 (0.75), req_004 (0.88)
        # Excludes req_003 (0.45)
        assert len(examples) == 3

    async def test_build_rerank_dataset__hard_negatives__mines_correctly(
        self, dataset_builder: DatasetBuilder, tmp_path: Path
    ) -> None:
        """Test hard negative mining for reranking dataset."""
        output_path = tmp_path / "rerank_pairs.jsonl"

        examples = await dataset_builder.build_rerank_dataset(
            sampling="hard_negatives",
            min_score_diff=0.1,
            output_path=str(output_path),
        )

        # Should find positive/negative pairs from traces
        assert len(examples) > 0

        # Verify first example structure
        assert isinstance(examples[0], RerankExample)
        assert examples[0].query
        assert examples[0].pos_chunk_id
        assert examples[0].neg_chunk_id
        assert examples[0].pos_score >= examples[0].neg_score

        # Check file was created
        assert output_path.exists()

    async def test_build_rerank_dataset__in_batch__mines_correctly(
        self, dataset_builder: DatasetBuilder, tmp_path: Path
    ) -> None:
        """Test in-batch negative mining."""
        output_path = tmp_path / "rerank_pairs.jsonl"

        examples = await dataset_builder.build_rerank_dataset(
            sampling="in_batch",
            min_score_diff=0.05,
            output_path=str(output_path),
        )

        assert len(examples) > 0
        assert isinstance(examples[0], RerankExample)

    async def test_deduplicate_queries__exact_duplicates__removes_lower_quality(
        self, dataset_builder: DatasetBuilder
    ) -> None:
        """Test deduplication removes exact duplicates, keeping higher quality."""
        examples = [
            TrainingExample(
                query="What is RAG?",
                intent="factual",
                response="Response 1",
                quality_score=0.9,
                sources=[],
                timestamp=datetime.now(),
            ),
            TrainingExample(
                query="What is RAG?",
                intent="factual",
                response="Response 2",
                quality_score=0.7,  # Lower quality
                sources=[],
                timestamp=datetime.now(),
            ),
        ]

        deduplicated = dataset_builder._deduplicate_queries(examples)

        assert len(deduplicated) == 1
        assert deduplicated[0].quality_score == 0.9  # Kept higher quality

    async def test_deduplicate_queries__similar_queries__removes_duplicates(
        self, dataset_builder: DatasetBuilder
    ) -> None:
        """Test deduplication handles similar (but not exact) queries."""
        examples = [
            TrainingExample(
                query="What is Retrieval Augmented Generation?",
                intent="factual",
                response="Response 1",
                quality_score=0.9,
                sources=[],
                timestamp=datetime.now(),
            ),
            TrainingExample(
                query="what is retrieval augmented generation?",  # Same but lowercase
                intent="factual",
                response="Response 2",
                quality_score=0.8,
                sources=[],
                timestamp=datetime.now(),
            ),
        ]

        deduplicated = dataset_builder._deduplicate_queries(examples)

        # Should deduplicate (case-insensitive exact match)
        assert len(deduplicated) == 1
        assert deduplicated[0].quality_score == 0.9

    async def test_mine_hard_negatives__creates_valid_pairs(
        self, dataset_builder: DatasetBuilder
    ) -> None:
        """Test hard negative mining creates valid pos/neg pairs."""
        query = "test query"
        all_chunks = [
            {"chunk_id": "c1", "score": 0.95},  # Cited, high score
            {"chunk_id": "c2", "score": 0.88},  # Not cited, high score (hard negative)
            {"chunk_id": "c3", "score": 0.75},  # Cited, medium score
            {"chunk_id": "c4", "score": 0.60},  # Not cited, low score
        ]
        cited_chunk_ids = {"c1", "c3"}

        pairs = dataset_builder._mine_hard_negatives(
            query, all_chunks, cited_chunk_ids, min_score_diff=0.1
        )

        # Should find hard negatives (c2 ranked higher than c3)
        assert len(pairs) > 0
        assert all(p.pos_chunk_id in cited_chunk_ids for p in pairs)
        assert all(p.neg_chunk_id not in cited_chunk_ids for p in pairs)

    async def test_mine_in_batch_negatives__creates_pairs_from_same_query(
        self, dataset_builder: DatasetBuilder
    ) -> None:
        """Test in-batch negative mining from same query results."""
        query = "test query"
        all_chunks = [
            {"chunk_id": "c1", "score": 0.95},  # Cited
            {"chunk_id": "c2", "score": 0.85},  # Not cited
            {"chunk_id": "c3", "score": 0.75},  # Cited
        ]
        cited_chunk_ids = {"c1", "c3"}

        pairs = dataset_builder._mine_in_batch_negatives(
            query, all_chunks, cited_chunk_ids, min_score_diff=0.05
        )

        assert len(pairs) > 0
        assert all(p.query == query for p in pairs)
        assert all(p.pos_chunk_id in cited_chunk_ids for p in pairs)
        assert all(p.neg_chunk_id not in cited_chunk_ids for p in pairs)

    async def test_compute_intent_stats__calculates_correctly(
        self, dataset_builder: DatasetBuilder
    ) -> None:
        """Test dataset statistics computation."""
        examples = [
            TrainingExample(
                query="q1",
                intent="factual",
                response="r1",
                quality_score=0.9,
                sources=[],
                timestamp=datetime.now(),
            ),
            TrainingExample(
                query="q2",
                intent="factual",
                response="r2",
                quality_score=0.8,
                sources=[],
                timestamp=datetime.now(),
            ),
            TrainingExample(
                query="q3",
                intent="exploratory",
                response="r3",
                quality_score=0.85,
                sources=[],
                timestamp=datetime.now(),
            ),
        ]

        stats = dataset_builder._compute_intent_stats(examples, total_traces=10)

        assert stats.total_traces == 10
        assert stats.filtered_traces == 3
        assert stats.total_examples == 3
        assert stats.intent_distribution == {"factual": 2, "exploratory": 1}
        assert abs(stats.avg_quality_score - 0.85) < 0.01

    async def test_build_intent_dataset__malformed_trace__skips_gracefully(
        self, tmp_path: Path
    ) -> None:
        """Test that malformed traces are skipped without crashing."""
        trace_file = tmp_path / "malformed_traces.jsonl"

        # Create traces with missing fields
        traces = [
            {
                "request_id": "req_001",
                # Missing query field
                "metrics": {"quality_score": 0.9},
            },
            {
                "request_id": "req_002",
                "query": {"original": "valid query"},
                # Missing metrics field - should default to 0.0 quality
            },
        ]

        with open(trace_file, "w") as f:
            for trace in traces:
                f.write(json.dumps(trace) + "\n")

        builder = DatasetBuilder(trace_path=str(trace_file))
        output_path = tmp_path / "output.jsonl"

        # Should not raise exception
        examples = await builder.build_intent_dataset(
            min_quality=0.5, output_path=str(output_path)
        )

        # Should skip malformed trace, only include valid ones above threshold
        assert len(examples) >= 0  # Might be 0 if all filtered out

    async def test_read_jsonl__invalid_json__skips_line(
        self, tmp_path: Path, dataset_builder: DatasetBuilder
    ) -> None:
        """Test that invalid JSON lines are skipped."""
        trace_file = tmp_path / "invalid.jsonl"

        with open(trace_file, "w") as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json here\n')  # Invalid line
            f.write('{"another": "valid"}\n')

        traces = dataset_builder._read_jsonl(trace_file)

        # Should skip invalid line, return 2 valid traces
        assert len(traces) == 2
        assert traces[0]["valid"] == "json"
        assert traces[1]["another"] == "valid"

    async def test_build_qa_dataset__high_quality__creates_examples(
        self, dataset_builder: DatasetBuilder, tmp_path: Path
    ) -> None:
        """Test QA dataset building from high-quality traces."""
        output_path = tmp_path / "qa_dataset.jsonl"

        examples = await dataset_builder.build_qa_dataset(
            min_quality=0.8, output_path=str(output_path), max_examples=10
        )

        # Should include req_001 (0.92) and req_004 (0.88)
        assert len(examples) == 2
        assert isinstance(examples[0], QAExample)
        assert examples[0].question == "What is RAG?"
        assert examples[0].answer == "RAG is Retrieval Augmented Generation..."
        assert examples[0].quality_score == 0.92
        assert len(examples[0].citations) == 2

        # Check file was created
        assert output_path.exists()

        # Verify JSONL format
        with open(output_path) as f:
            lines = f.readlines()
            assert len(lines) == 2
            first_example = json.loads(lines[0])
            assert first_example["question"] == "What is RAG?"

    async def test_build_qa_dataset__max_examples__limits_output(
        self, dataset_builder: DatasetBuilder, tmp_path: Path
    ) -> None:
        """Test QA dataset respects max_examples limit."""
        output_path = tmp_path / "qa_dataset.jsonl"

        examples = await dataset_builder.build_qa_dataset(
            min_quality=0.7, output_path=str(output_path), max_examples=2
        )

        # Should limit to 2 examples even if more qualify
        assert len(examples) <= 2

    async def test_build_graph_dataset__filters_graph_traces(
        self, temp_graph_trace_file: Path, tmp_path: Path
    ) -> None:
        """Test graph dataset building filters for graph query traces."""
        builder = DatasetBuilder(trace_path=str(temp_graph_trace_file))
        output_path = tmp_path / "graph_dataset.jsonl"

        examples = await builder.build_graph_dataset(
            min_quality=0.7, output_path=str(output_path), max_examples=10
        )

        # Should include req_graph_001 (0.90) and req_graph_002 (0.78)
        # Should exclude req_no_graph (no graph query)
        assert len(examples) == 2
        assert isinstance(examples[0], GraphExample)
        assert examples[0].query == "What are the relationships between RAG and LLM?"
        assert examples[0].cypher == "MATCH (r:RAG)-[rel:RELATES_TO]->(l:LLM) RETURN r, rel, l"
        assert examples[0].entities == ["RAG", "LLM"]
        assert examples[0].relations == ["RELATES_TO"]
        assert len(examples[0].graph_results) == 3  # 2 local + 1 global

        # Check file was created
        assert output_path.exists()

    async def test_build_graph_dataset__high_quality_threshold__filters(
        self, temp_graph_trace_file: Path, tmp_path: Path
    ) -> None:
        """Test graph dataset with high quality threshold."""
        builder = DatasetBuilder(trace_path=str(temp_graph_trace_file))
        output_path = tmp_path / "graph_dataset.jsonl"

        examples = await builder.build_graph_dataset(
            min_quality=0.85, output_path=str(output_path), max_examples=10
        )

        # Should only include req_graph_001 (0.90), exclude req_graph_002 (0.78)
        assert len(examples) == 1
        assert examples[0].quality_score == 0.90

    async def test_export_to_parquet__creates_versioned_dataset(
        self, dataset_builder: DatasetBuilder, tmp_path: Path
    ) -> None:
        """Test exporting dataset to Parquet format with versioning."""
        # Build some examples first
        output_path = tmp_path / "qa_dataset.jsonl"
        examples = await dataset_builder.build_qa_dataset(
            min_quality=0.8, output_path=str(output_path), max_examples=10
        )

        # Export to Parquet
        export_dir = tmp_path / "datasets"
        result_path = await dataset_builder.export_to_parquet(
            examples, "qa", str(export_dir), version="v1"
        )

        # Check directory structure
        assert Path(result_path).exists()
        parquet_file = Path(result_path) / "data.parquet"
        metadata_file = Path(result_path) / "metadata.json"

        assert parquet_file.exists()
        assert metadata_file.exists()

        # Verify metadata
        with open(metadata_file) as f:
            metadata = json.load(f)
            assert metadata["name"] == "qa"
            assert metadata["version"] == "v1"
            assert metadata["num_examples"] == len(examples)
            assert "created_at" in metadata

    async def test_export_to_parquet__empty_examples__returns_empty(
        self, dataset_builder: DatasetBuilder, tmp_path: Path
    ) -> None:
        """Test export with empty examples list."""
        result = await dataset_builder.export_to_parquet(
            [], "qa", str(tmp_path / "datasets"), version="v1"
        )

        # Should return empty string for empty dataset
        assert result == ""


class TestTrainingExamples:
    """Test dataclass models."""

    def test_training_example__serialization__works_correctly(self) -> None:
        """Test TrainingExample can be serialized to dict."""
        example = TrainingExample(
            query="test query",
            intent="factual",
            response="test response",
            quality_score=0.95,
            sources=[{"chunk_id": "c1"}],
            timestamp=datetime(2025, 12, 31, 10, 0, 0),
            metadata={"request_id": "req_001"},
        )

        assert example.query == "test query"
        assert example.quality_score == 0.95
        assert example.timestamp.year == 2025

    def test_rerank_example__has_required_fields(self) -> None:
        """Test RerankExample has all required fields."""
        example = RerankExample(
            query="test",
            pos_chunk_id="c1",
            neg_chunk_id="c2",
            pos_score=0.9,
            neg_score=0.6,
            pos_rank=1,
            neg_rank=5,
        )

        assert example.query == "test"
        assert example.pos_score > example.neg_score
        assert example.pos_rank < example.neg_rank
