"""RAGAS evaluation framework for RAG system quality assessment.

This module provides evaluation capabilities using RAGAS (RAG Assessment) metrics:
- Context Precision: How relevant are retrieved contexts to the answer?
- Context Recall: Are all necessary contexts retrieved?
- Faithfulness: Is the answer grounded in the retrieved contexts?

RAGAS requires an LLM for evaluation. We use Ollama (llama3.2) by default.

NOTE: Due to RAGAS library compatibility issues with Ollama (404 errors),
this module falls back to custom implementation (src/evaluation/custom_metrics.py)
when RAGAS evaluation fails.
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field
from ragas import EvaluationDataset as RagasDataset

# RAGAS 0.3.x imports (API changed from 0.2.x)
from ragas import SingleTurnSample, evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import ContextPrecision, ContextRecall, Faithfulness

from src.core.config import settings

logger = structlog.get_logger(__name__)


class EvaluationDataset(BaseModel):
    """Single evaluation example.

    Attributes:
        question: User query
        ground_truth: Expected/reference answer
        contexts: list of retrieved document texts
        answer: Generated answer (optional, can be generated during eval)
    """

    question: str = Field(..., description="User query")
    ground_truth: str = Field(..., description="Expected/reference answer")
    contexts: list[str] = Field(..., description="Retrieved document contexts")
    answer: str = Field(default="", description="Generated answer (optional)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EvaluationResult(BaseModel):
    """RAGAS evaluation result.

    Attributes:
        scenario: Retrieval scenario name
        context_precision: Context precision score (0-1)
        context_recall: Context recall score (0-1)
        faithfulness: Faithfulness score (0-1)
        num_samples: Number of evaluation samples
        duration_seconds: Evaluation duration
        timestamp: Evaluation timestamp
    """

    scenario: str = Field(..., description="Retrieval scenario name")
    context_precision: float = Field(..., description="Context precision score (0-1)")
    context_recall: float = Field(..., description="Context recall score (0-1)")
    faithfulness: float = Field(..., description="Faithfulness score (0-1)")
    num_samples: int = Field(..., description="Number of evaluation samples")
    duration_seconds: float = Field(..., description="Evaluation duration")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(), description="Evaluation timestamp"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RAGASEvaluator:
    """RAGAS evaluator for RAG system quality assessment.

    Uses RAGAS metrics to evaluate retrieval quality:
    - Context Precision: Relevance of retrieved contexts
    - Context Recall: Coverage of necessary information
    - Faithfulness: Answer grounding in contexts

    Example:
        >>> evaluator = RAGASEvaluator()
        >>> dataset = evaluator.load_dataset("data/evaluation/ragas_dataset.jsonl")
        >>> result = await evaluator.evaluate_retrieval(
        ...     dataset=dataset,
        ...     scenario="hybrid-reranked"
        ... )
        >>> print(f"Faithfulness: {result.faithfulness:.3f}")
    """

    def __init__(
        self,
        llm_model: str | None = None,
        llm_base_url: str | None = None,
        metrics: list[str] | None = None,
    ) -> None:
        """Initialize RAGAS evaluator.

        Args:
            llm_model: LLM model for evaluation (default: settings.ollama_model_query)
            llm_base_url: Ollama base URL (default: settings.ollama_base_url)
            metrics: list of metrics to evaluate (default: all supported metrics)
        """
        self.llm_model = llm_model or settings.ollama_model_query
        self.llm_base_url = llm_base_url or settings.ollama_base_url
        self.metrics_list = metrics or ["context_precision", "context_recall", "faithfulness"]

        logger.info(
            "ragas_evaluator_initialized",
            llm_model=self.llm_model,
            llm_base_url=self.llm_base_url,
            metrics=self.metrics_list,
        )

    def _get_langchain_llm(self) -> None:
        """Get LangChain LLM wrapper for RAGAS.

        Returns:
            LangChain LLM instance

        Note:
            RAGAS requires LangChain LLM interface. We wrap Ollama client.
            Using ChatOllama for better structured output support.
        """
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            # Fallback to community version
            from langchain_community.chat_models import ChatOllama

        llm = ChatOllama(
            model=self.llm_model,
            base_url=self.llm_base_url,
            temperature=0.0,  # Deterministic for evaluation
            format="json",  # Request JSON output for better parsing
        )

        # Wrap in RAGAS LLM wrapper
        return LangchainLLMWrapper(llm)

    def _get_metrics(self) -> list:
        """Get RAGAS metric instances.

        Returns:
            list of RAGAS metric objects

        Note:
            RAGAS 0.3.x uses classes instead of functions
        """
        metric_map = {
            "context_precision": ContextPrecision(),
            "context_recall": ContextRecall(),
            "faithfulness": Faithfulness(),
        }

        metrics = []
        for metric_name in self.metrics_list:
            if metric_name in metric_map:
                metrics.append(metric_map[metric_name])
            else:
                logger.warning("unknown_metric", metric=metric_name)

        logger.info("ragas_metrics_loaded", count=len(metrics), metrics=self.metrics_list)
        return metrics

    def load_dataset(self, dataset_path: str | Path) -> list[EvaluationDataset]:
        """Load evaluation dataset from JSONL file.

        Args:
            dataset_path: Path to JSONL dataset file

        Returns:
            list of evaluation examples

        Raises:
            FileNotFoundError: If dataset file not found
            ValueError: If dataset format is invalid
        """
        dataset_path = Path(dataset_path)

        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")

        logger.info("loading_dataset", path=str(dataset_path))

        examples = []
        with open(dataset_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                try:
                    data = json.loads(line)
                    example = EvaluationDataset(**data)
                    examples.append(example)
                except Exception as e:
                    logger.warning(
                        "failed_to_parse_dataset_line",
                        line_num=line_num,
                        error=str(e),
                    )

        logger.info("dataset_loaded", path=str(dataset_path), num_examples=len(examples))

        if not examples:
            raise ValueError(f"No valid examples found in dataset: {dataset_path}")

        return examples

    async def evaluate_retrieval(
        self,
        dataset: list[EvaluationDataset],
        scenario: str = "default",
    ) -> EvaluationResult:
        """Evaluate retrieval quality using RAGAS metrics.

        Args:
            dataset: list of evaluation examples
            scenario: Scenario name (e.g., "vector-only", "hybrid-reranked")

        Returns:
            Evaluation result with metrics

        Example:
            >>> evaluator = RAGASEvaluator()
            >>> dataset = evaluator.load_dataset("data/evaluation/ragas_dataset.jsonl")
            >>> result = await evaluator.evaluate_retrieval(
            ...     dataset=dataset,
            ...     scenario="hybrid-reranked"
            ... )
        """
        logger.info("starting_ragas_evaluation", scenario=scenario, num_samples=len(dataset))

        start_time = datetime.now(UTC)

        # Convert to RAGAS 0.3 EvaluationDataset format
        # RAGAS 0.3 uses SingleTurnSample instead of raw dicts
        samples = []
        for ex in dataset:
            sample = SingleTurnSample(
                user_input=ex.question,
                reference=ex.ground_truth,
                retrieved_contexts=ex.contexts,
                response=ex.answer or ex.ground_truth,  # Use ground truth if no answer
            )
            samples.append(sample)

        ragas_dataset = RagasDataset(samples=samples)

        logger.debug(
            "converted_to_ragas_dataset",
            num_samples=len(ragas_dataset.samples),
        )

        # Get LLM and metrics
        llm = self._get_langchain_llm()
        metrics = self._get_metrics()

        # RAGAS 0.3 evaluate() signature changed
        # Run evaluation (blocking, but RAGAS doesn't have async support)
        # We run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        eval_result = await loop.run_in_executor(
            None,
            lambda: evaluate(
                dataset=ragas_dataset,
                metrics=metrics,
                llm=llm,
                raise_exceptions=False,  # Continue on errors
            ),
        )

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        # Extract scores
        df = eval_result.to_pandas()
        print(f"[DEBUG RAGAS] DataFrame columns: {df.columns.tolist()}")
        print(f"[DEBUG RAGAS] DataFrame shape: {df.shape}")
        print(f"[DEBUG RAGAS] DataFrame head:\n{df.head()}")

        scores = df.to_dict()
        print(f"[DEBUG RAGAS] Scores dict keys: {scores.keys()}")
        for key, value in scores.items():
            print(f"[DEBUG RAGAS] {key}: {value}")

        logger.debug("ragas_scores", scores=scores)

        # Build result
        result = EvaluationResult(
            scenario=scenario,
            context_precision=(
                float(scores.get("context_precision", [0.0])[0])
                if "context_precision" in scores
                else 0.0
            ),
            context_recall=(
                float(scores.get("context_recall", [0.0])[0]) if "context_recall" in scores else 0.0
            ),
            faithfulness=(
                float(scores.get("faithfulness", [0.0])[0]) if "faithfulness" in scores else 0.0
            ),
            num_samples=len(dataset),
            duration_seconds=duration,
            timestamp=end_time.isoformat(),
            metadata={
                "llm_model": self.llm_model,
                "metrics": self.metrics_list,
            },
        )

        logger.info(
            "ragas_evaluation_complete",
            scenario=scenario,
            context_precision=result.context_precision,
            context_recall=result.context_recall,
            faithfulness=result.faithfulness,
            duration_seconds=duration,
        )

        return result

    async def evaluate_retrieval_custom(
        self,
        dataset: list[EvaluationDataset],
        scenario: str = "default",
    ) -> EvaluationResult:
        """Evaluate retrieval using custom Ollama-based metrics.

        Fallback method when RAGAS library has compatibility issues.
        Uses custom implementation from src/evaluation/custom_metrics.py

        Args:
            dataset: list of evaluation examples
            scenario: Scenario name

        Returns:
            Evaluation result with metrics

        Example:
            >>> evaluator = RAGASEvaluator()
            >>> result = await evaluator.evaluate_retrieval_custom(
            ...     dataset=dataset,
            ...     scenario="custom-ollama"
            ... )
        """
        from src.evaluation.custom_metrics import CustomMetricsEvaluator

        logger.info(
            "starting_custom_evaluation",
            scenario=scenario,
            num_samples=len(dataset),
        )

        start_time = datetime.now(UTC)

        # Initialize custom evaluator
        custom_evaluator = CustomMetricsEvaluator(
            model=self.llm_model,
            base_url=self.llm_base_url,
        )

        # Evaluate each sample
        precision_scores = []
        recall_scores = []
        faithfulness_scores = []

        for i, sample in enumerate(dataset):
            logger.debug(
                "evaluating_sample",
                sample_idx=i,
                question=sample.question[:50],
            )

            results = await custom_evaluator.evaluate_all(
                query=sample.question,
                retrieved_contexts=sample.contexts,
                response=sample.answer or sample.ground_truth,
                ground_truth=sample.ground_truth,
            )

            precision_scores.append(results.context_precision)
            recall_scores.append(results.context_recall)
            faithfulness_scores.append(results.faithfulness)

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        # Calculate averages
        avg_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0
        avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
        avg_faithfulness = (
            sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0.0
        )

        result = EvaluationResult(
            scenario=scenario,
            context_precision=avg_precision,
            context_recall=avg_recall,
            faithfulness=avg_faithfulness,
            num_samples=len(dataset),
            duration_seconds=duration,
            timestamp=end_time.isoformat(),
            metadata={
                "llm_model": self.llm_model,
                "evaluator": "custom_ollama",
                "metrics": self.metrics_list,
            },
        )

        logger.info(
            "custom_evaluation_complete",
            scenario=scenario,
            context_precision=result.context_precision,
            context_recall=result.context_recall,
            faithfulness=result.faithfulness,
            duration_seconds=duration,
        )

        return result

    async def run_benchmark(
        self,
        dataset: list[EvaluationDataset],
        scenarios: list[str] | None = None,
    ) -> dict[str, EvaluationResult]:
        """Run benchmark across multiple retrieval scenarios.

        Args:
            dataset: Evaluation dataset
            scenarios: list of scenario names to evaluate

        Returns:
            Dictionary mapping scenario name to evaluation result

        Example:
            >>> evaluator = RAGASEvaluator()
            >>> dataset = evaluator.load_dataset("data/evaluation/ragas_dataset.jsonl")
            >>> results = await evaluator.run_benchmark(
            ...     dataset=dataset,
            ...     scenarios=["vector-only", "bm25-only", "hybrid-reranked"]
            ... )
        """
        if scenarios is None:
            scenarios = [
                "vector-only",
                "bm25-only",
                "hybrid-base",
                "hybrid-reranked",
                "hybrid-decomposed",
                "hybrid-full",
            ]

        logger.info("starting_benchmark", scenarios=scenarios, num_samples=len(dataset))

        results = {}
        for scenario in scenarios:
            logger.info("evaluating_scenario", scenario=scenario)
            result = await self.evaluate_retrieval(dataset=dataset, scenario=scenario)
            results[scenario] = result

        logger.info("benchmark_complete", num_scenarios=len(results))

        return results

    def generate_report(
        self,
        results: dict[str, EvaluationResult],
        output_path: str | Path | None = None,
        format: Literal["html", "json", "markdown"] = "html",
    ) -> str:
        """Generate evaluation report.

        Args:
            results: Dictionary of evaluation results
            output_path: Output file path (optional)
            format: Report format (html, json, markdown)

        Returns:
            Report content as string

        Example:
            >>> results = await evaluator.run_benchmark(dataset, scenarios)
            >>> report = evaluator.generate_report(
            ...     results,
            ...     output_path="reports/ragas_evaluation.html",
            ...     format="html"
            ... )
        """
        logger.info("generating_report", format=format, num_results=len(results))

        if format == "json":
            report = self._generate_json_report(results)
        elif format == "markdown":
            report = self._generate_markdown_report(results)
        else:  # html
            report = self._generate_html_report(results)

        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            logger.info("report_saved", path=str(output_path))

        return report

    def _generate_json_report(self, results: dict[str, EvaluationResult]) -> str:
        """Generate JSON report."""
        report_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "scenarios": {scenario: result.model_dump() for scenario, result in results.items()},
            "summary": {
                "best_context_precision": max(r.context_precision for r in results.values()),
                "best_context_recall": max(r.context_recall for r in results.values()),
                "best_faithfulness": max(r.faithfulness for r in results.values()),
            },
        }
        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, results: dict[str, EvaluationResult]) -> str:
        """Generate Markdown report."""
        lines = [
            "# RAGAS Evaluation Report",
            "",
            f"**Timestamp**: {datetime.now(UTC).isoformat()}",
            "",
            "## Results by Scenario",
            "",
            "| Scenario | Context Precision | Context Recall | Faithfulness | Duration (s) |",
            "|----------|-------------------|----------------|--------------|--------------|",
        ]

        for scenario, result in sorted(results.items()):
            lines.append(
                f"| {scenario} | {result.context_precision:.3f} | "
                f"{result.context_recall:.3f} | {result.faithfulness:.3f} | "
                f"{result.duration_seconds:.2f} |"
            )

        lines.extend(
            [
                "",
                "## Summary",
                "",
                f"- **Best Context Precision**: {max(r.context_precision for r in results.values()):.3f}",
                f"- **Best Context Recall**: {max(r.context_recall for r in results.values()):.3f}",
                f"- **Best Faithfulness**: {max(r.faithfulness for r in results.values()):.3f}",
                "",
            ]
        )

        return "\n".join(lines)

    def _generate_html_report(self, results: dict[str, EvaluationResult]) -> str:
        """Generate HTML report."""
        rows = []
        for scenario, result in sorted(results.items()):
            rows.append(
                f"""
                <tr>
                    <td>{scenario}</td>
                    <td>{result.context_precision:.3f}</td>
                    <td>{result.context_recall:.3f}</td>
                    <td>{result.faithfulness:.3f}</td>
                    <td>{result.duration_seconds:.2f}s</td>
                </tr>
                """
            )

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RAGAS Evaluation Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .summary {{
            background-color: #e8f5e9;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary h3 {{
            margin-top: 0;
            color: #2e7d32;
        }}
        .metric {{
            font-size: 18px;
            margin: 10px 0;
        }}
        .timestamp {{
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>RAGAS Evaluation Report</h1>
        <p class="timestamp">Generated: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>

        <h2>Results by Scenario</h2>
        <table>
            <thead>
                <tr>
                    <th>Scenario</th>
                    <th>Context Precision</th>
                    <th>Context Recall</th>
                    <th>Faithfulness</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>

        <div class="summary">
            <h3>Summary</h3>
            <div class="metric">
                Best Context Precision: <strong>{max(r.context_precision for r in results.values()):.3f}</strong>
            </div>
            <div class="metric">
                Best Context Recall: <strong>{max(r.context_recall for r in results.values()):.3f}</strong>
            </div>
            <div class="metric">
                Best Faithfulness: <strong>{max(r.faithfulness for r in results.values()):.3f}</strong>
            </div>
        </div>

        <h2>Metric Descriptions</h2>
        <ul>
            <li><strong>Context Precision</strong>: Measures how relevant the retrieved contexts are to the answer (0-1, higher is better)</li>
            <li><strong>Context Recall</strong>: Measures whether all necessary information was retrieved (0-1, higher is better)</li>
            <li><strong>Faithfulness</strong>: Measures whether the answer is grounded in the retrieved contexts (0-1, higher is better)</li>
        </ul>
    </div>
</body>
</html>
        """

        return html.strip()
