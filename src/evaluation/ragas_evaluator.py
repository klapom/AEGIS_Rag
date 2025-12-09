"""RAGAS Evaluation Pipeline for AEGIS RAG System.

Sprint 41 Feature 41.7: Create a RAGAS-based evaluation pipeline that evaluates
AEGIS RAG's retrieval and generation quality using standard metrics.

This module provides:
- RAGAS integration with all 4 standard metrics (context precision, context recall,
  faithfulness, answer relevancy)
- Namespace-scoped evaluation (search only in benchmark namespace)
- Per-intent metric breakdown (vector, graph, hybrid)
- Batch evaluation support with configurable batch size
- Integration with FourWayHybridSearch for namespace filtering

Metrics:
    - Context Precision: Relevance of retrieved contexts to the answer
    - Context Recall: Coverage of ground truth information
    - Faithfulness: Answer is grounded in retrieved contexts
    - Answer Relevancy: Answer addresses the question

Usage:
    evaluator = RAGASEvaluator()

    # Load benchmark dataset
    dataset = evaluator.load_dataset("data/benchmarks/hotpotqa.jsonl")

    # Run evaluation with namespace filtering
    results = await evaluator.evaluate_rag_pipeline(
        dataset=dataset,
        namespace="eval_hotpotqa",
        sample_size=50
    )

    # Generate report
    report = evaluator.generate_report(results, output_path="reports/eval_results.json")
"""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from datasets import Dataset
from pydantic import BaseModel, Field
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from src.components.llm_proxy.aegis_llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import LLMTask, TaskType
from src.components.retrieval.four_way_hybrid_search import get_four_way_hybrid_search
from src.components.retrieval.intent_classifier import Intent
from src.components.shared.embedding_service import get_embedding_service
from src.core.exceptions import EvaluationError

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class BenchmarkSample(BaseModel):
    """Single benchmark evaluation sample.

    Attributes:
        question: User query
        ground_truth: Expected answer or reference information
        contexts: Optional pre-retrieved contexts (for retrieval-only eval)
        answer: Optional pre-generated answer (for generation-only eval)
        metadata: Additional metadata (e.g., intent, difficulty, source)
    """

    question: str = Field(..., description="User query")
    ground_truth: str = Field(..., description="Expected answer")
    contexts: list[str] = Field(default_factory=list, description="Pre-retrieved contexts")
    answer: str = Field(default="", description="Pre-generated answer")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Sample metadata")


@dataclass
class MetricScores:
    """RAGAS metric scores for a single sample or aggregated results."""

    context_precision: float
    context_recall: float
    faithfulness: float
    answer_relevancy: float


@dataclass
class IntentMetrics:
    """Per-intent metric breakdown."""

    intent: str
    sample_count: int
    metrics: MetricScores


@dataclass
class EvaluationResults:
    """Complete evaluation results with detailed breakdowns.

    Attributes:
        overall_metrics: Aggregated metrics across all samples
        per_intent_metrics: Breakdown by classified intent
        sample_count: Total samples evaluated
        namespace: Namespace used for evaluation
        duration_seconds: Total evaluation time
        metadata: Additional metadata (model names, config, etc.)
    """

    overall_metrics: MetricScores
    per_intent_metrics: list[IntentMetrics]
    sample_count: int
    namespace: str
    duration_seconds: float
    metadata: dict[str, Any]


# =============================================================================
# LangChain Wrapper for Ollama (RAGAS Compatibility)
# =============================================================================


class OllamaLangChainLLM:
    """LangChain-compatible LLM wrapper for AegisLLMProxy.

    RAGAS requires LangChain LLM interface. This wrapper adapts
    AegisLLMProxy to meet that requirement.
    """

    def __init__(self, model: str = "llama3.2:8b"):
        """Initialize LLM wrapper.

        Args:
            model: Ollama model name for evaluation
        """
        self.model = model
        self.llm_proxy = get_aegis_llm_proxy()

    async def agenerate(self, prompts: list[str], **kwargs: Any) -> list[str]:
        """Generate responses for multiple prompts (async).

        Args:
            prompts: List of prompts to generate responses for
            **kwargs: Additional generation parameters

        Returns:
            List of generated responses
        """
        results = []
        for prompt in prompts:
            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt=prompt,
                model_local=self.model,
            )
            response = await self.llm_proxy.generate(task)
            results.append(response.content)
        return results

    def generate(self, prompts: list[str], **kwargs: Any) -> list[str]:
        """Generate responses (sync wrapper).

        Args:
            prompts: List of prompts
            **kwargs: Additional parameters

        Returns:
            List of responses
        """
        return asyncio.run(self.agenerate(prompts, **kwargs))


class OllamaEmbeddings:
    """LangChain-compatible embeddings wrapper for UnifiedEmbeddingService."""

    def __init__(self):
        """Initialize embeddings wrapper."""
        self.embedding_service = get_embedding_service()

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents (async).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return await self.embedding_service.embed_batch(texts)

    async def aembed_query(self, text: str) -> list[float]:
        """Embed single query (async).

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        return await self.embedding_service.embed_single(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents (sync wrapper).

        Args:
            texts: List of texts

        Returns:
            List of embedding vectors
        """
        return asyncio.run(self.aembed_documents(texts))

    def embed_query(self, text: str) -> list[float]:
        """Embed query (sync wrapper).

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        return asyncio.run(self.aembed_query(text))


# =============================================================================
# RAGAS Evaluator
# =============================================================================


class RAGASEvaluator:
    """RAGAS-based evaluation pipeline for AEGIS RAG.

    This evaluator provides:
    - Namespace-scoped evaluation (isolate benchmark data)
    - Per-intent metric breakdown (factual, keyword, exploratory, summary)
    - Batch evaluation with progress tracking
    - Integration with FourWayHybridSearch
    - All 4 RAGAS metrics: context_precision, context_recall, faithfulness, answer_relevancy

    Example:
        evaluator = RAGASEvaluator(namespace="eval_hotpotqa")

        # Load benchmark dataset
        dataset = evaluator.load_dataset("data/benchmarks/hotpotqa.jsonl")

        # Run evaluation
        results = await evaluator.evaluate_rag_pipeline(
            dataset=dataset,
            sample_size=50,
            batch_size=10
        )

        # Print results
        print(f"Overall Faithfulness: {results.overall_metrics.faithfulness:.3f}")
        for intent_metrics in results.per_intent_metrics:
            print(f"{intent_metrics.intent}: {intent_metrics.metrics.faithfulness:.3f}")
    """

    def __init__(
        self,
        namespace: str = "eval_benchmark",
        llm_model: str = "llama3.2:8b",
        metrics: list[str] | None = None,
    ):
        """Initialize RAGAS evaluator.

        Args:
            namespace: Namespace for benchmark data (default: "eval_benchmark")
            llm_model: LLM model for RAGAS evaluation (default: llama3.2:8b)
            metrics: List of metrics to compute (default: all 4 metrics)
        """
        self.namespace = namespace
        self.llm_model = llm_model
        self.metrics_list = metrics or [
            "context_precision",
            "context_recall",
            "faithfulness",
            "answer_relevancy",
        ]

        # Initialize services
        self.search_engine = get_four_way_hybrid_search()
        self.llm_proxy = get_aegis_llm_proxy()

        # Create LangChain wrappers for RAGAS
        self.llm = LangchainLLMWrapper(OllamaLangChainLLM(model=llm_model))
        self.embeddings = LangchainEmbeddingsWrapper(OllamaEmbeddings())

        logger.info(
            "ragas_evaluator_initialized",
            namespace=namespace,
            llm_model=llm_model,
            metrics=self.metrics_list,
        )

    def load_dataset(self, dataset_path: str | Path) -> list[BenchmarkSample]:
        """Load benchmark dataset from JSONL file.

        Args:
            dataset_path: Path to JSONL dataset file

        Returns:
            List of benchmark samples

        Raises:
            FileNotFoundError: If dataset not found
            ValueError: If dataset format is invalid

        Example:
            dataset = evaluator.load_dataset("data/benchmarks/hotpotqa.jsonl")
        """
        dataset_path = Path(dataset_path)

        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")

        logger.info("loading_dataset", path=str(dataset_path))

        import json

        samples = []
        with open(dataset_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                try:
                    data = json.loads(line)
                    sample = BenchmarkSample(**data)
                    samples.append(sample)
                except Exception as e:
                    logger.warning(
                        "failed_to_parse_sample",
                        line_num=line_num,
                        error=str(e),
                    )

        logger.info("dataset_loaded", path=str(dataset_path), num_samples=len(samples))

        if not samples:
            raise ValueError(f"No valid samples in dataset: {dataset_path}")

        return samples

    async def retrieve_contexts(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[str]:
        """Retrieve contexts for a query using FourWayHybridSearch.

        Args:
            query: User query
            top_k: Number of contexts to retrieve

        Returns:
            List of retrieved context texts
        """
        # Search with namespace filtering
        search_results = await self.search_engine.search(
            query=query,
            top_k=top_k,
            allowed_namespaces=[self.namespace],
            use_reranking=True,
        )

        # Extract text from results
        contexts = []
        for result in search_results.get("results", []):
            text = result.get("text", "")
            if text:
                contexts.append(text)

        logger.debug(
            "retrieved_contexts",
            query=query[:50],
            num_contexts=len(contexts),
            namespace=self.namespace,
        )

        return contexts

    async def generate_answer(
        self,
        query: str,
        contexts: list[str],
    ) -> str:
        """Generate answer using retrieved contexts.

        Args:
            query: User query
            contexts: Retrieved contexts

        Returns:
            Generated answer
        """
        # Build prompt with contexts
        context_text = "\n\n".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)])
        prompt = f"""Answer the following question based on the provided contexts.

Question: {query}

Contexts:
{context_text}

Answer: """

        # Generate answer
        task = LLMTask(
            task_type=TaskType.ANSWER_GENERATION,
            prompt=prompt,
            model_local=self.llm_model,
            temperature=0.1,  # Low temperature for factual answers
        )

        response = await self.llm_proxy.generate(task)

        logger.debug(
            "answer_generated",
            query=query[:50],
            answer_length=len(response.content),
        )

        return response.content

    async def evaluate_rag_pipeline(
        self,
        dataset: list[BenchmarkSample],
        sample_size: int | None = None,
        batch_size: int = 10,
        top_k: int = 10,
    ) -> EvaluationResults:
        """Evaluate complete RAG pipeline (retrieval + generation).

        This method:
        1. Retrieves contexts for each query (namespace-filtered)
        2. Generates answers using retrieved contexts
        3. Computes all 4 RAGAS metrics
        4. Aggregates results overall and per-intent

        Args:
            dataset: List of benchmark samples
            sample_size: Number of samples to evaluate (None = all)
            batch_size: Batch size for evaluation
            top_k: Number of contexts to retrieve per query

        Returns:
            Complete evaluation results with per-intent breakdown

        Raises:
            EvaluationError: If evaluation fails
        """
        start_time = time.perf_counter()

        # Sample dataset if requested
        if sample_size and sample_size < len(dataset):
            import random

            dataset = random.sample(dataset, sample_size)
            logger.info("dataset_sampled", original_size=len(dataset), sample_size=sample_size)

        logger.info(
            "starting_rag_evaluation",
            num_samples=len(dataset),
            namespace=self.namespace,
            batch_size=batch_size,
        )

        # Process samples: retrieve contexts and generate answers
        evaluated_samples = []
        for i, sample in enumerate(dataset):
            logger.info(
                "evaluating_sample",
                sample_idx=i + 1,
                total_samples=len(dataset),
                question=sample.question[:50],
            )

            # Retrieve contexts if not provided
            if not sample.contexts:
                contexts = await self.retrieve_contexts(sample.question, top_k=top_k)
            else:
                contexts = sample.contexts

            # Generate answer if not provided
            if not sample.answer:
                answer = await self.generate_answer(sample.question, contexts)
            else:
                answer = sample.answer

            # Store evaluated sample
            evaluated_samples.append({
                "question": sample.question,
                "contexts": contexts,
                "answer": answer,
                "ground_truth": sample.ground_truth,
                "metadata": sample.metadata,
            })

        # Convert to RAGAS dataset format
        ragas_dataset = Dataset.from_dict({
            "question": [s["question"] for s in evaluated_samples],
            "contexts": [s["contexts"] for s in evaluated_samples],
            "answer": [s["answer"] for s in evaluated_samples],
            "ground_truth": [s["ground_truth"] for s in evaluated_samples],
        })

        # Get RAGAS metrics
        metrics = self._get_ragas_metrics()

        logger.info("running_ragas_evaluation", num_samples=len(evaluated_samples))

        # Run RAGAS evaluation (blocking, so run in executor)
        try:
            loop = asyncio.get_event_loop()
            eval_result = await loop.run_in_executor(
                None,
                lambda: evaluate(
                    dataset=ragas_dataset,
                    metrics=metrics,
                    llm=self.llm,
                    embeddings=self.embeddings,
                ),
            )
        except Exception as e:
            logger.error("ragas_evaluation_failed", error=str(e))
            raise EvaluationError(f"RAGAS evaluation failed: {e}") from e

        # Extract scores
        df = eval_result.to_pandas()

        overall_metrics = MetricScores(
            context_precision=float(df["context_precision"].mean()),
            context_recall=float(df["context_recall"].mean()),
            faithfulness=float(df["faithfulness"].mean()),
            answer_relevancy=float(df["answer_relevancy"].mean()),
        )

        # Compute per-intent breakdown
        per_intent_metrics = self._compute_per_intent_metrics(df, evaluated_samples)

        duration = time.perf_counter() - start_time

        results = EvaluationResults(
            overall_metrics=overall_metrics,
            per_intent_metrics=per_intent_metrics,
            sample_count=len(evaluated_samples),
            namespace=self.namespace,
            duration_seconds=duration,
            metadata={
                "llm_model": self.llm_model,
                "top_k": top_k,
                "batch_size": batch_size,
            },
        )

        logger.info(
            "rag_evaluation_complete",
            namespace=self.namespace,
            sample_count=results.sample_count,
            duration_seconds=round(duration, 2),
            context_precision=round(overall_metrics.context_precision, 3),
            context_recall=round(overall_metrics.context_recall, 3),
            faithfulness=round(overall_metrics.faithfulness, 3),
            answer_relevancy=round(overall_metrics.answer_relevancy, 3),
        )

        return results

    def _get_ragas_metrics(self) -> list:
        """Get RAGAS metric instances.

        Returns:
            List of RAGAS metric objects
        """
        metric_map = {
            "context_precision": ContextPrecision(),
            "context_recall": ContextRecall(),
            "faithfulness": Faithfulness(),
            "answer_relevancy": AnswerRelevancy(),
        }

        metrics = []
        for metric_name in self.metrics_list:
            if metric_name in metric_map:
                metrics.append(metric_map[metric_name])
            else:
                logger.warning("unknown_metric", metric=metric_name)

        return metrics

    def _compute_per_intent_metrics(
        self,
        df: Any,
        evaluated_samples: list[dict[str, Any]],
    ) -> list[IntentMetrics]:
        """Compute per-intent metric breakdown.

        Args:
            df: RAGAS results DataFrame
            evaluated_samples: List of evaluated samples with metadata

        Returns:
            List of per-intent metrics
        """
        # Group by intent (from metadata or classify on-the-fly)
        intent_groups: dict[str, list[int]] = {}

        for i, sample in enumerate(evaluated_samples):
            # Extract intent from metadata or default to "unknown"
            intent = sample.get("metadata", {}).get("intent", "unknown")
            if intent not in intent_groups:
                intent_groups[intent] = []
            intent_groups[intent].append(i)

        # Compute metrics for each intent
        per_intent = []
        for intent, indices in intent_groups.items():
            subset_df = df.iloc[indices]

            metrics = MetricScores(
                context_precision=float(subset_df["context_precision"].mean()),
                context_recall=float(subset_df["context_recall"].mean()),
                faithfulness=float(subset_df["faithfulness"].mean()),
                answer_relevancy=float(subset_df["answer_relevancy"].mean()),
            )

            per_intent.append(
                IntentMetrics(
                    intent=intent,
                    sample_count=len(indices),
                    metrics=metrics,
                )
            )

        return per_intent

    def generate_report(
        self,
        results: EvaluationResults,
        output_path: str | Path | None = None,
        format: str = "json",
    ) -> str:
        """Generate evaluation report.

        Args:
            results: Evaluation results
            output_path: Output file path (optional)
            format: Report format (json, markdown, html)

        Returns:
            Report content as string
        """
        import json
        from datetime import datetime

        if format == "json":
            report_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "namespace": results.namespace,
                "sample_count": results.sample_count,
                "duration_seconds": results.duration_seconds,
                "overall_metrics": {
                    "context_precision": results.overall_metrics.context_precision,
                    "context_recall": results.overall_metrics.context_recall,
                    "faithfulness": results.overall_metrics.faithfulness,
                    "answer_relevancy": results.overall_metrics.answer_relevancy,
                },
                "per_intent_metrics": [
                    {
                        "intent": im.intent,
                        "sample_count": im.sample_count,
                        "context_precision": im.metrics.context_precision,
                        "context_recall": im.metrics.context_recall,
                        "faithfulness": im.metrics.faithfulness,
                        "answer_relevancy": im.metrics.answer_relevancy,
                    }
                    for im in results.per_intent_metrics
                ],
                "metadata": results.metadata,
            }
            report = json.dumps(report_data, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            logger.info("report_saved", path=str(output_path))

        return report


# =============================================================================
# Singleton
# =============================================================================


_evaluator_instance: RAGASEvaluator | None = None


def get_ragas_evaluator(namespace: str = "eval_benchmark") -> RAGASEvaluator:
    """Get global RAGASEvaluator instance (singleton).

    Args:
        namespace: Namespace for benchmark data

    Returns:
        RAGASEvaluator instance
    """
    global _evaluator_instance
    if _evaluator_instance is None or _evaluator_instance.namespace != namespace:
        _evaluator_instance = RAGASEvaluator(namespace=namespace)
    return _evaluator_instance
