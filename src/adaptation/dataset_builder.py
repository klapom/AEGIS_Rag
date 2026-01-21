"""Dataset Builder for training data generation from production traces.

Sprint 67 Feature 67.7: Generate training datasets from UnifiedTracer logs.

This module builds training datasets from production query traces for:
- Intent classification (query → intent)
- Reranking (query, pos_chunk, neg_chunk) triplets
- Query rewriting (original → rewritten → retrieval_outcome)

Architecture:
    Traces (JSONL) → Filter by Quality → Extract Examples → Deduplicate → Save Dataset

Features:
    - Quality-based filtering (min_quality threshold)
    - Hard negative mining for reranker training
    - Query deduplication with similarity detection
    - JSONL output format for efficient streaming
    - Dataset versioning and statistics

Related:
    - Feature 67.5: UnifiedTracer (trace generation)
    - Feature 67.6: Eval Harness (quality scoring)
    - Feature 67.8: Adaptive Reranker (uses rerank dataset)
    - Feature 67.9: Query Rewriter (uses rewrite dataset)

References:
    - Paper 2512.16301: Tool-Level LLM Adaptation
    - TD-075: LLM Intent Classifier (C-LARA)
"""

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from src.core.exceptions import AegisRAGException


class DatasetBuilderError(AegisRAGException):
    """Raised when dataset building fails."""

    def __init__(self, operation: str, reason: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Dataset builder operation '{operation}' failed: {reason}",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=500,
            details={"operation": operation, "reason": reason},
        )


@dataclass
class TrainingExample:
    """Training example extracted from production trace.

    Attributes:
        query: Original user query
        intent: Classified intent (factual, keyword, exploratory, summary)
        response: Generated answer
        quality_score: Quality score from eval harness (0.0-1.0)
        sources: List of source chunks used in answer
        timestamp: When the query was executed
        metadata: Additional trace metadata (latency, model, etc.)
    """

    query: str
    intent: str
    response: str
    quality_score: float
    sources: list[dict[str, Any]]
    timestamp: datetime
    metadata: dict[str, Any] | None = None


@dataclass
class RerankExample:
    """Reranking training example (query, positive, negative triplet).

    Attributes:
        query: User query
        pos_chunk_id: Chunk ID of positive (relevant) result
        neg_chunk_id: Chunk ID of negative (irrelevant) result
        pos_score: Original retrieval score of positive chunk
        neg_score: Original retrieval score of negative chunk
        pos_rank: Original rank of positive chunk
        neg_rank: Original rank of negative chunk
    """

    query: str
    pos_chunk_id: str
    neg_chunk_id: str
    pos_score: float
    neg_score: float
    pos_rank: int
    neg_rank: int


@dataclass
class RewriteExample:
    """Query rewriting training example.

    Attributes:
        original_query: Original user query
        rewritten_query: Rewritten query for retrieval
        retrieval_hit_at_k: Whether retrieval succeeded (0.0-1.0)
        label: "positive" if rewrite improved retrieval, else "negative"
        graph_intent: Optional graph traversal hints
    """

    original_query: str
    rewritten_query: str
    retrieval_hit_at_k: float
    label: str
    graph_intent: dict[str, Any] | None = None


@dataclass
class QAExample:
    """Question-answering training example.

    Attributes:
        question: User query/question
        context: Retrieved context (concatenated chunks)
        answer: Generated answer
        quality_score: Quality score from eval harness (0.0-1.0)
        citations: List of source chunk IDs cited
        metadata: Additional trace metadata
    """

    question: str
    context: str
    answer: str
    quality_score: float
    citations: list[str]
    metadata: dict[str, Any] | None = None


@dataclass
class GraphExample:
    """Graph RAG training example.

    Attributes:
        query: User query
        cypher: Generated Cypher query (if any)
        entities: Extracted entities from query
        relations: Extracted relations from query
        graph_results: Graph traversal results
        answer: Generated answer incorporating graph data
        quality_score: Quality score from eval harness (0.0-1.0)
        metadata: Additional trace metadata
    """

    query: str
    cypher: str | None
    entities: list[str]
    relations: list[str]
    graph_results: list[dict[str, Any]]
    answer: str
    quality_score: float
    metadata: dict[str, Any] | None = None


@dataclass
class DatasetStats:
    """Dataset statistics for reporting.

    Attributes:
        total_traces: Total number of traces loaded
        filtered_traces: Number of traces after quality filtering
        total_examples: Total training examples generated
        intent_distribution: Distribution of intent labels
        avg_quality_score: Average quality score of examples
        query_duplicates_removed: Number of duplicate queries removed
    """

    total_traces: int
    filtered_traces: int
    total_examples: int
    intent_distribution: dict[str, int]
    avg_quality_score: float
    query_duplicates_removed: int


class DatasetBuilder:
    """Build training datasets from production traces.

    This class loads UnifiedTracer JSONL files, filters by quality thresholds,
    extracts training examples, and saves datasets in JSONL format.

    Example:
        >>> builder = DatasetBuilder(trace_path="data/traces/traces.jsonl")
        >>> # Build intent classification dataset
        >>> intent_examples = await builder.build_intent_dataset(
        ...     min_quality=0.8,
        ...     output_path="data/datasets/v1/intent_dataset.jsonl"
        ... )
        >>> # Build reranking dataset with hard negatives
        >>> rerank_examples = await builder.build_rerank_dataset(
        ...     sampling="hard_negatives",
        ...     output_path="data/datasets/v1/rerank_pairs.jsonl"
        ... )
    """

    def __init__(
        self,
        trace_path: str = "data/traces/traces.jsonl",
        eval_harness: Any | None = None,
    ) -> None:
        """Initialize dataset builder.

        Args:
            trace_path: Path to UnifiedTracer JSONL file or directory.
                       If directory, loads all .jsonl files.
            eval_harness: Optional EvalHarness instance for quality scoring.
                         If None, quality scores are read from traces.
        """
        self.logger = structlog.get_logger(__name__)
        self.trace_path = Path(trace_path)
        self._trace_cache: list[dict[str, Any]] = []
        self._eval_harness = eval_harness

    async def build_intent_dataset(
        self,
        min_quality: float = 0.8,
        output_path: str = "data/datasets/v1/intent_dataset.jsonl",
        deduplicate: bool = True,
    ) -> list[TrainingExample]:
        """Build intent classification dataset from traces.

        Filters traces by quality score, extracts (query, intent) pairs,
        optionally deduplicates similar queries, and saves to JSONL.

        Args:
            min_quality: Minimum quality score (0.0-1.0) to include trace.
                        Higher threshold = higher quality but fewer examples.
            output_path: Output file path for JSONL dataset
            deduplicate: If True, remove duplicate/similar queries

        Returns:
            List of TrainingExample objects

        Raises:
            DatasetBuilderError: If trace loading or dataset building fails

        Example:
            >>> examples = await builder.build_intent_dataset(
            ...     min_quality=0.85,
            ...     output_path="data/intent_v1.jsonl"
            ... )
            >>> print(f"Generated {len(examples)} intent examples")
        """
        try:
            # 1. Load traces
            self.logger.info(
                "loading_traces",
                trace_path=str(self.trace_path),
                min_quality=min_quality,
            )
            traces = await self._load_traces()

            if not traces:
                self.logger.warning("no_traces_found", trace_path=str(self.trace_path))
                return []

            # 2. Filter by quality threshold
            high_quality = [
                t for t in traces if t.get("metrics", {}).get("quality_score", 0.0) >= min_quality
            ]

            self.logger.info(
                "traces_filtered",
                total_traces=len(traces),
                high_quality_traces=len(high_quality),
                threshold=min_quality,
            )

            # 3. Extract training examples
            examples = []
            for trace in high_quality:
                try:
                    example = TrainingExample(
                        query=trace.get("query", {}).get("original", ""),
                        intent=trace.get("query", {}).get("intent", "unknown"),
                        response=trace.get("answer", {}).get("text", ""),
                        quality_score=trace.get("metrics", {}).get("quality_score", 0.0),
                        sources=trace.get("evidence", {}).get("citations", []),
                        timestamp=datetime.fromisoformat(
                            trace.get("timestamp", datetime.now().isoformat())
                        ),
                        metadata={
                            "request_id": trace.get("request_id"),
                            "latency_ms": trace.get("metrics", {}).get("total_latency_ms"),
                            "model": trace.get("answer", {}).get("model"),
                        },
                    )
                    examples.append(example)
                except (KeyError, ValueError) as e:
                    self.logger.warning(
                        "trace_parsing_failed",
                        trace_id=trace.get("request_id", "unknown"),
                        error=str(e),
                    )
                    continue

            # 4. Deduplicate similar queries
            if deduplicate:
                original_count = len(examples)
                examples = self._deduplicate_queries(examples)
                duplicates_removed = original_count - len(examples)
                self.logger.info(
                    "queries_deduplicated",
                    original_count=original_count,
                    deduplicated_count=len(examples),
                    duplicates_removed=duplicates_removed,
                )

            # 5. Save dataset
            await self._save_intent_dataset(examples, output_path)

            # 6. Generate statistics
            stats = self._compute_intent_stats(examples, len(traces))
            self.logger.info(
                "intent_dataset_built",
                **asdict(stats),
                output_path=output_path,
            )

            return examples

        except Exception as e:
            self.logger.error("intent_dataset_build_failed", error=str(e), exc_info=True)
            raise DatasetBuilderError(operation="build_intent_dataset", reason=str(e)) from e

    async def build_rerank_dataset(
        self,
        sampling: str = "hard_negatives",
        min_score_diff: float = 0.3,
        output_path: str = "data/datasets/v1/rerank_pairs.jsonl",
    ) -> list[RerankExample]:
        """Build reranking dataset with positive/negative chunk pairs.

        Extracts (query, pos_chunk, neg_chunk) triplets from retrieval traces.
        Uses hard negative mining to find challenging negative examples.

        Args:
            sampling: Sampling strategy - "hard_negatives" (top-K misses) or
                     "in_batch" (within same query results)
            min_score_diff: Minimum score difference between pos and neg chunks
            output_path: Output file path for JSONL dataset

        Returns:
            List of RerankExample objects

        Raises:
            DatasetBuilderError: If dataset building fails

        Example:
            >>> examples = await builder.build_rerank_dataset(
            ...     sampling="hard_negatives",
            ...     min_score_diff=0.3
            ... )
            >>> print(f"Generated {len(examples)} rerank pairs")
        """
        try:
            # 1. Load traces
            traces = await self._load_traces()

            if not traces:
                self.logger.warning("no_traces_for_rerank", trace_path=str(self.trace_path))
                return []

            # 2. Extract rerank pairs
            examples: list[RerankExample] = []
            for trace in traces:
                try:
                    query = trace.get("query", {}).get("original", "")
                    retrieval = trace.get("retrieval", {})
                    citations = trace.get("evidence", {}).get("citations", [])

                    # Get all retrieved chunks with scores
                    all_chunks: list[dict[str, Any]] = []
                    for source in ["vector", "bm25", "graph_local", "graph_global"]:
                        chunks = retrieval.get(source, {}).get("results", [])
                        all_chunks.extend(chunks)

                    if not all_chunks or not citations:
                        continue

                    # Identify positive chunks (cited in answer)
                    cited_chunk_ids = {c for c in citations if isinstance(c, str)}

                    # Hard negative mining: high-ranked but not cited
                    if sampling == "hard_negatives":
                        pairs = self._mine_hard_negatives(
                            query, all_chunks, cited_chunk_ids, min_score_diff
                        )
                        examples.extend(pairs)
                    # In-batch negatives: pair cited with uncited from same query
                    elif sampling == "in_batch":
                        pairs = self._mine_in_batch_negatives(
                            query, all_chunks, cited_chunk_ids, min_score_diff
                        )
                        examples.extend(pairs)

                except (KeyError, ValueError) as e:
                    self.logger.warning(
                        "rerank_trace_parsing_failed",
                        trace_id=trace.get("request_id", "unknown"),
                        error=str(e),
                    )
                    continue

            # 3. Save dataset
            await self._save_rerank_dataset(examples, output_path)

            self.logger.info(
                "rerank_dataset_built",
                total_examples=len(examples),
                sampling_strategy=sampling,
                min_score_diff=min_score_diff,
                output_path=output_path,
            )

            return examples

        except Exception as e:
            self.logger.error("rerank_dataset_build_failed", error=str(e), exc_info=True)
            raise DatasetBuilderError(operation="build_rerank_dataset", reason=str(e)) from e

    async def build_qa_dataset(
        self,
        min_quality: float = 0.8,
        output_path: str = "data/datasets/v1/qa_dataset.jsonl",
        max_examples: int = 10000,
    ) -> list[QAExample]:
        """Build question-answering dataset from traces.

        Extracts (question, context, answer) triples from high-quality traces.
        Useful for fine-tuning generative models or RAG systems.

        Args:
            min_quality: Minimum quality score (0.0-1.0) to include trace
            output_path: Output file path for JSONL dataset
            max_examples: Maximum number of examples to include

        Returns:
            List of QAExample objects

        Raises:
            DatasetBuilderError: If dataset building fails

        Example:
            >>> examples = await builder.build_qa_dataset(
            ...     min_quality=0.85,
            ...     output_path="data/qa_v1.jsonl",
            ...     max_examples=5000
            ... )
            >>> print(f"Generated {len(examples)} QA examples")
        """
        try:
            # 1. Load traces
            self.logger.info(
                "loading_traces_for_qa",
                trace_path=str(self.trace_path),
                min_quality=min_quality,
            )
            traces = await self._load_traces()

            if not traces:
                self.logger.warning("no_traces_found", trace_path=str(self.trace_path))
                return []

            # 2. Filter by quality threshold and score with EvalHarness if available
            high_quality = []
            for trace in traces:
                quality_score = trace.get("metrics", {}).get("quality_score", 0.0)

                # Use EvalHarness if available and no quality score in trace
                if quality_score == 0.0 and self._eval_harness:
                    try:
                        query = trace.get("query", {}).get("original", "")
                        answer = trace.get("answer", {}).get("text", "")
                        sources = trace.get("evidence", {}).get("citations", [])

                        results = await self._eval_harness.evaluate_response(
                            query=query, answer=answer, sources=sources
                        )
                        quality_score = sum(r.score for r in results) / len(results)
                        trace["metrics"]["quality_score"] = quality_score
                    except Exception as e:
                        self.logger.warning(
                            "eval_harness_failed",
                            trace_id=trace.get("request_id"),
                            error=str(e),
                        )

                if quality_score >= min_quality:
                    high_quality.append(trace)

            self.logger.info(
                "traces_filtered_for_qa",
                total_traces=len(traces),
                high_quality_traces=len(high_quality),
                threshold=min_quality,
            )

            # 3. Extract QA examples
            examples = []
            for trace in high_quality[:max_examples]:
                try:
                    # Get question
                    question = trace.get("query", {}).get("original", "")

                    # Get context from selected chunks
                    chunks = trace.get("evidence", {}).get("selected_chunks", [])
                    # Handle both list of chunks and integer count
                    if isinstance(chunks, list):
                        context = "\n\n".join(
                            chunk.get("text", chunk.get("content", "")) for chunk in chunks
                        )
                    else:
                        # If selected_chunks is a count, fallback to empty context
                        context = ""

                    # Get answer
                    answer = trace.get("answer", {}).get("text", "")

                    # Get citations
                    citations = trace.get("evidence", {}).get("citations", [])
                    # Handle both string IDs and dict citations
                    citation_ids = [
                        c if isinstance(c, str) else c.get("chunk_id", "") for c in citations
                    ]

                    example = QAExample(
                        question=question,
                        context=context,
                        answer=answer,
                        quality_score=trace.get("metrics", {}).get("quality_score", 0.0),
                        citations=citation_ids,
                        metadata={
                            "request_id": trace.get("request_id"),
                            "timestamp": trace.get("timestamp"),
                            "model": trace.get("answer", {}).get("model"),
                            "latency_ms": trace.get("metrics", {}).get("total_latency_ms"),
                        },
                    )
                    examples.append(example)
                except (KeyError, ValueError) as e:
                    self.logger.warning(
                        "qa_trace_parsing_failed",
                        trace_id=trace.get("request_id", "unknown"),
                        error=str(e),
                    )
                    continue

            # 4. Save dataset
            await self._save_qa_dataset(examples, output_path)

            self.logger.info(
                "qa_dataset_built",
                total_examples=len(examples),
                avg_quality_score=(
                    sum(e.quality_score for e in examples) / len(examples) if examples else 0.0
                ),
                output_path=output_path,
            )

            return examples

        except Exception as e:
            self.logger.error("qa_dataset_build_failed", error=str(e), exc_info=True)
            raise DatasetBuilderError(operation="build_qa_dataset", reason=str(e)) from e

    async def build_graph_dataset(
        self,
        min_quality: float = 0.8,
        output_path: str = "data/datasets/v1/graph_dataset.jsonl",
        max_examples: int = 10000,
    ) -> list[GraphExample]:
        """Build graph RAG dataset from traces with graph queries.

        Extracts (query, cypher, entities, graph_results, answer) examples.
        Useful for training graph query generation and entity extraction.

        Args:
            min_quality: Minimum quality score (0.0-1.0) to include trace
            output_path: Output file path for JSONL dataset
            max_examples: Maximum number of examples to include

        Returns:
            List of GraphExample objects

        Raises:
            DatasetBuilderError: If dataset building fails

        Example:
            >>> examples = await builder.build_graph_dataset(
            ...     min_quality=0.85,
            ...     output_path="data/graph_v1.jsonl"
            ... )
            >>> print(f"Generated {len(examples)} graph examples")
        """
        try:
            # 1. Load traces
            self.logger.info(
                "loading_traces_for_graph",
                trace_path=str(self.trace_path),
                min_quality=min_quality,
            )
            traces = await self._load_traces()

            if not traces:
                self.logger.warning("no_traces_found", trace_path=str(self.trace_path))
                return []

            # 2. Filter by quality and graph query presence
            high_quality_graph = []
            for trace in traces:
                # Skip traces without graph queries
                if "graph_query" not in trace or not trace.get("retrieval", {}).get("graph_local"):
                    continue

                quality_score = trace.get("metrics", {}).get("quality_score", 0.0)

                # Use EvalHarness if available and no quality score
                if quality_score == 0.0 and self._eval_harness:
                    try:
                        query = trace.get("query", {}).get("original", "")
                        answer = trace.get("answer", {}).get("text", "")
                        sources = trace.get("evidence", {}).get("citations", [])

                        results = await self._eval_harness.evaluate_response(
                            query=query, answer=answer, sources=sources
                        )
                        quality_score = sum(r.score for r in results) / len(results)
                        trace["metrics"]["quality_score"] = quality_score
                    except Exception as e:
                        self.logger.warning(
                            "eval_harness_failed",
                            trace_id=trace.get("request_id"),
                            error=str(e),
                        )

                if quality_score >= min_quality:
                    high_quality_graph.append(trace)

            self.logger.info(
                "traces_filtered_for_graph",
                total_traces=len(traces),
                graph_traces=len([t for t in traces if "graph_query" in t]),
                high_quality_graph_traces=len(high_quality_graph),
                threshold=min_quality,
            )

            # 3. Extract graph examples
            examples = []
            for trace in high_quality_graph[:max_examples]:
                try:
                    query = trace.get("query", {}).get("original", "")
                    graph_query_data = trace.get("graph_query", {})

                    # Get Cypher query if available
                    cypher = graph_query_data.get("cypher")

                    # Get entities and relations
                    entities = graph_query_data.get("entities", [])
                    relations = graph_query_data.get("relations", [])

                    # Get graph results
                    graph_local = trace.get("retrieval", {}).get("graph_local", {})
                    graph_global = trace.get("retrieval", {}).get("graph_global", {})

                    graph_results = []
                    if graph_local.get("results"):
                        graph_results.extend(graph_local["results"])
                    if graph_global.get("results"):
                        graph_results.extend(graph_global["results"])

                    # Get answer
                    answer = trace.get("answer", {}).get("text", "")

                    example = GraphExample(
                        query=query,
                        cypher=cypher,
                        entities=entities,
                        relations=relations,
                        graph_results=graph_results,
                        answer=answer,
                        quality_score=trace.get("metrics", {}).get("quality_score", 0.0),
                        metadata={
                            "request_id": trace.get("request_id"),
                            "timestamp": trace.get("timestamp"),
                            "graph_local_count": len(graph_local.get("results", [])),
                            "graph_global_count": len(graph_global.get("results", [])),
                            "model": trace.get("answer", {}).get("model"),
                        },
                    )
                    examples.append(example)
                except (KeyError, ValueError) as e:
                    self.logger.warning(
                        "graph_trace_parsing_failed",
                        trace_id=trace.get("request_id", "unknown"),
                        error=str(e),
                    )
                    continue

            # 4. Save dataset
            await self._save_graph_dataset(examples, output_path)

            self.logger.info(
                "graph_dataset_built",
                total_examples=len(examples),
                avg_quality_score=(
                    sum(e.quality_score for e in examples) / len(examples) if examples else 0.0
                ),
                output_path=output_path,
            )

            return examples

        except Exception as e:
            self.logger.error("graph_dataset_build_failed", error=str(e), exc_info=True)
            raise DatasetBuilderError(operation="build_graph_dataset", reason=str(e)) from e

    async def _load_traces(self) -> list[dict[str, Any]]:
        """Load all traces from JSONL file(s).

        Supports both single file and directory of JSONL files.
        Caches loaded traces to avoid reloading.

        Returns:
            List of trace dictionaries

        Raises:
            DatasetBuilderError: If file reading fails
        """
        if self._trace_cache:
            return self._trace_cache

        traces: list[dict[str, Any]] = []

        try:
            # Handle directory of JSONL files
            if self.trace_path.is_dir():
                trace_files = list(self.trace_path.glob("*.jsonl"))
                self.logger.info(
                    "loading_trace_directory",
                    directory=str(self.trace_path),
                    files_found=len(trace_files),
                )
                for trace_file in trace_files:
                    traces.extend(self._read_jsonl(trace_file))
            # Handle single JSONL file
            elif self.trace_path.exists():
                traces = self._read_jsonl(self.trace_path)
            else:
                self.logger.warning(
                    "trace_path_not_found",
                    path=str(self.trace_path),
                )
                return []

            self._trace_cache = traces
            return traces

        except Exception as e:
            raise DatasetBuilderError(
                operation="load_traces",
                reason=f"Failed to read traces: {e}",
            ) from e

    def _read_jsonl(self, file_path: Path) -> list[dict[str, Any]]:
        """Read JSONL file line by line.

        Args:
            file_path: Path to JSONL file

        Returns:
            List of parsed JSON objects
        """
        traces: list[dict[str, Any]] = []
        with open(file_path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    traces.append(json.loads(line))
                except json.JSONDecodeError as e:
                    self.logger.warning(
                        "jsonl_parse_error",
                        file=str(file_path),
                        line_number=line_num,
                        error=str(e),
                    )
        return traces

    def _deduplicate_queries(
        self, examples: list[TrainingExample], similarity_threshold: float = 0.9
    ) -> list[TrainingExample]:
        """Remove duplicate or highly similar queries.

        Uses simple character-level similarity (normalized edit distance).
        For production, consider using sentence embeddings for semantic similarity.

        Args:
            examples: List of training examples
            similarity_threshold: Similarity threshold (0.0-1.0) for deduplication

        Returns:
            Deduplicated list of examples
        """
        seen_queries: dict[str, TrainingExample] = {}
        deduplicated: list[TrainingExample] = []

        for example in examples:
            query_lower = example.query.lower().strip()

            # Exact match deduplication
            if query_lower in seen_queries:
                # Keep example with higher quality score
                if example.quality_score > seen_queries[query_lower].quality_score:
                    seen_queries[query_lower] = example
                continue

            # Simple character-level similarity check (cheap heuristic)
            is_duplicate = False
            for seen_query in seen_queries:
                # Quick length check
                len_ratio = min(len(query_lower), len(seen_query)) / max(
                    len(query_lower), len(seen_query)
                )
                if len_ratio < similarity_threshold:
                    continue

                # Character overlap ratio (simple heuristic)
                common_chars = len(set(query_lower) & set(seen_query))
                total_chars = len(set(query_lower) | set(seen_query))
                similarity = common_chars / total_chars if total_chars > 0 else 0.0

                if similarity >= similarity_threshold:
                    is_duplicate = True
                    # Keep higher quality example
                    if example.quality_score > seen_queries[seen_query].quality_score:
                        seen_queries[seen_query] = example
                    break

            if not is_duplicate:
                seen_queries[query_lower] = example
                deduplicated.append(example)

        return deduplicated

    def _mine_hard_negatives(
        self,
        query: str,
        all_chunks: list[dict[str, Any]],
        cited_chunk_ids: set[str],
        min_score_diff: float,
    ) -> list[RerankExample]:
        """Mine hard negative examples (high-ranked but not cited).

        Args:
            query: User query
            all_chunks: All retrieved chunks with scores
            cited_chunk_ids: Set of chunk IDs cited in answer
            min_score_diff: Minimum score difference between pos and neg

        Returns:
            List of RerankExample objects
        """
        examples: list[RerankExample] = []

        # Sort by score (descending)
        sorted_chunks = sorted(all_chunks, key=lambda x: x.get("score", 0.0), reverse=True)

        # Find positive and negative chunks
        positive_chunks = [c for c in sorted_chunks if c.get("chunk_id") in cited_chunk_ids]
        negative_chunks = [c for c in sorted_chunks if c.get("chunk_id") not in cited_chunk_ids]

        # Create pairs: cited chunk (positive) vs high-ranked uncited (hard negative)
        for pos_chunk in positive_chunks:
            pos_score = pos_chunk.get("score", 0.0)
            pos_rank = sorted_chunks.index(pos_chunk)

            # Find hard negatives (ranked higher or similar score)
            for neg_chunk in negative_chunks:
                neg_score = neg_chunk.get("score", 0.0)
                neg_rank = sorted_chunks.index(neg_chunk)

                # Hard negative: ranked higher than positive or similar score
                if neg_rank < pos_rank or abs(pos_score - neg_score) < min_score_diff:
                    examples.append(
                        RerankExample(
                            query=query,
                            pos_chunk_id=pos_chunk.get("chunk_id", ""),
                            neg_chunk_id=neg_chunk.get("chunk_id", ""),
                            pos_score=pos_score,
                            neg_score=neg_score,
                            pos_rank=pos_rank,
                            neg_rank=neg_rank,
                        )
                    )

        return examples

    def _mine_in_batch_negatives(
        self,
        query: str,
        all_chunks: list[dict[str, Any]],
        cited_chunk_ids: set[str],
        min_score_diff: float,
    ) -> list[RerankExample]:
        """Mine in-batch negatives (pair cited with uncited from same query).

        Args:
            query: User query
            all_chunks: All retrieved chunks
            cited_chunk_ids: Set of chunk IDs cited in answer
            min_score_diff: Minimum score difference

        Returns:
            List of RerankExample objects
        """
        examples: list[RerankExample] = []

        # Sort by score
        sorted_chunks = sorted(all_chunks, key=lambda x: x.get("score", 0.0), reverse=True)

        positive_chunks = [c for c in sorted_chunks if c.get("chunk_id") in cited_chunk_ids]
        negative_chunks = [c for c in sorted_chunks if c.get("chunk_id") not in cited_chunk_ids]

        # Create all combinations of pos/neg pairs
        for pos_chunk in positive_chunks:
            pos_score = pos_chunk.get("score", 0.0)
            pos_rank = sorted_chunks.index(pos_chunk)

            for neg_chunk in negative_chunks:
                neg_score = neg_chunk.get("score", 0.0)
                neg_rank = sorted_chunks.index(neg_chunk)

                # Ensure minimum score difference
                if abs(pos_score - neg_score) >= min_score_diff:
                    examples.append(
                        RerankExample(
                            query=query,
                            pos_chunk_id=pos_chunk.get("chunk_id", ""),
                            neg_chunk_id=neg_chunk.get("chunk_id", ""),
                            pos_score=pos_score,
                            neg_score=neg_score,
                            pos_rank=pos_rank,
                            neg_rank=neg_rank,
                        )
                    )

        return examples

    async def _save_intent_dataset(self, examples: list[TrainingExample], output_path: str) -> None:
        """Save intent dataset to JSONL format.

        Args:
            examples: List of training examples
            output_path: Output file path
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w") as f:
            for ex in examples:
                f.write(
                    json.dumps(
                        {
                            "query": ex.query,
                            "intent": ex.intent,
                            "quality_score": ex.quality_score,
                            "timestamp": ex.timestamp.isoformat(),
                            "metadata": ex.metadata,
                        }
                    )
                    + "\n"
                )

        self.logger.info("intent_dataset_saved", output_path=output_path, count=len(examples))

    async def _save_rerank_dataset(self, examples: list[RerankExample], output_path: str) -> None:
        """Save rerank dataset to JSONL format.

        Args:
            examples: List of rerank examples
            output_path: Output file path
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w") as f:
            for ex in examples:
                f.write(json.dumps(asdict(ex)) + "\n")

        self.logger.info("rerank_dataset_saved", output_path=output_path, count=len(examples))

    async def _save_qa_dataset(self, examples: list[QAExample], output_path: str) -> None:
        """Save QA dataset to JSONL format.

        Args:
            examples: List of QA examples
            output_path: Output file path
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w") as f:
            for ex in examples:
                f.write(json.dumps(asdict(ex)) + "\n")

        self.logger.info("qa_dataset_saved", output_path=output_path, count=len(examples))

    async def _save_graph_dataset(self, examples: list[GraphExample], output_path: str) -> None:
        """Save graph dataset to JSONL format.

        Args:
            examples: List of graph examples
            output_path: Output file path
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w") as f:
            for ex in examples:
                f.write(json.dumps(asdict(ex)) + "\n")

        self.logger.info("graph_dataset_saved", output_path=output_path, count=len(examples))

    def _compute_intent_stats(
        self, examples: list[TrainingExample], total_traces: int
    ) -> DatasetStats:
        """Compute dataset statistics for reporting.

        Args:
            examples: List of training examples
            total_traces: Total number of traces loaded

        Returns:
            DatasetStats object
        """
        intent_counts: defaultdict[str, int] = defaultdict(int)
        for ex in examples:
            intent_counts[ex.intent] += 1

        avg_quality = sum(ex.quality_score for ex in examples) / len(examples) if examples else 0.0

        return DatasetStats(
            total_traces=total_traces,
            filtered_traces=len(examples),
            total_examples=len(examples),
            intent_distribution=dict(intent_counts),
            avg_quality_score=avg_quality,
            query_duplicates_removed=0,  # Updated in build_intent_dataset
        )

    async def export_to_parquet(
        self,
        examples: list[Any],
        dataset_type: str,
        output_dir: str = "data/datasets",
        version: str = "v1",
    ) -> str:
        """Export dataset to Parquet format with versioning.

        Args:
            examples: List of dataset examples (any dataclass type)
            dataset_type: Dataset type (intent, rerank, qa, graph)
            output_dir: Base output directory
            version: Dataset version (e.g., v1, v2)

        Returns:
            Path to exported dataset directory

        Example:
            >>> builder = DatasetBuilder()
            >>> examples = await builder.build_qa_dataset(min_quality=0.8)
            >>> path = await builder.export_to_parquet(examples, "qa", version="v1")
            >>> print(f"Dataset exported to {path}")
        """
        try:
            import pandas as pd
        except ImportError:
            # Sprint 118 Fix: B904 - raise from None to distinguish from handler errors
            raise DatasetBuilderError(
                operation="export_to_parquet",
                reason="pandas is required for Parquet export. Install with: pip install pandas pyarrow",
            ) from None

        if not examples:
            self.logger.warning("no_examples_to_export", dataset_type=dataset_type)
            return ""

        # Create versioned directory
        export_path = Path(output_dir) / dataset_type / version
        export_path.mkdir(parents=True, exist_ok=True)

        # Convert examples to DataFrame
        data = [asdict(ex) for ex in examples]
        df = pd.DataFrame(data)

        # Save as Parquet
        parquet_file = export_path / "data.parquet"
        df.to_parquet(parquet_file, index=False, engine="pyarrow")

        # Compute statistics
        avg_quality = 0.0
        if "quality_score" in df.columns:
            avg_quality = df["quality_score"].mean()

        # Save metadata
        metadata = {
            "name": dataset_type,
            "version": version,
            "created_at": datetime.now().isoformat(),
            "num_examples": len(examples),
            "columns": list(df.columns),
            "avg_quality_score": float(avg_quality),
            "source_traces": str(self.trace_path),
        }

        metadata_file = export_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        self.logger.info(
            "dataset_exported_to_parquet",
            dataset_type=dataset_type,
            version=version,
            path=str(export_path),
            num_examples=len(examples),
            avg_quality=avg_quality,
        )

        return str(export_path)
