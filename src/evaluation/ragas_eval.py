"""RAGAS evaluation framework for RAG system quality assessment.

This module provides evaluation capabilities using RAGAS (RAG Assessment) metrics:
- Context Precision: How relevant are retrieved contexts to the answer?
- Context Recall: Are all necessary contexts retrieved?
- Faithfulness: Is the answer grounded in the retrieved contexts?

RAGAS requires an LLM for evaluation. We use Ollama (llama3.2) by default.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import structlog
from datasets import Dataset
from pydantic import BaseModel, Field
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import context_precision, context_recall, faithfulness

from src.core.config import settings

logger = structlog.get_logger(__name__)


class EvaluationDataset(BaseModel):
    """Single evaluation example.

    Attributes:
        question: User query
        ground_truth: Expected/reference answer
        contexts: List of retrieved document texts
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
        default_factory=lambda: datetime.utcnow().isoformat(), description="Evaluation timestamp"
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
    ):
        """Initialize RAGAS evaluator.

        Args:
            llm_model: LLM model for evaluation (default: settings.ollama_model_query)
            llm_base_url: Ollama base URL (default: settings.ollama_base_url)
            metrics: List of metrics to evaluate (default: all supported metrics)
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

    def _get_langchain_llm(self):
        """Get LangChain LLM wrapper for RAGAS.

        Returns:
            LangChain LLM instance

        Note:
            RAGAS requires LangChain LLM interface. We wrap Ollama client.
        """
        from langchain_community.llms import Ollama

        llm = Ollama(
            model=self.llm_model,
            base_url=self.llm_base_url,
            temperature=0.0,  # Deterministic for evaluation
        )

        # Wrap in RAGAS LLM wrapper
        return LangchainLLMWrapper(llm)

    def _get_metrics(self) -> list:
        """Get RAGAS metric instances.

        Returns:
            List of RAGAS metric objects
        """
        metric_map = {
            "context_precision": context_precision,
            "context_recall": context_recall,
            "faithfulness": faithfulness,
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
            List of evaluation examples

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
            dataset: List of evaluation examples
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

        start_time = datetime.utcnow()

        # Convert to HuggingFace Dataset format
        data_dict = {
            "question": [ex.question for ex in dataset],
            "ground_truth": [ex.ground_truth for ex in dataset],
            "contexts": [ex.contexts for ex in dataset],
            "answer": [
                ex.answer or ex.ground_truth for ex in dataset
            ],  # Use ground truth if no answer
        }

        hf_dataset = Dataset.from_dict(data_dict)

        logger.debug(
            "converted_to_hf_dataset",
            num_rows=len(hf_dataset),
            columns=hf_dataset.column_names,
        )

        # Get LLM and metrics
        llm = self._get_langchain_llm()
        metrics = self._get_metrics()

        # Run evaluation (blocking, but RAGAS doesn't have async support)
        # We run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        eval_result = await loop.run_in_executor(
            None,
            lambda: evaluate(
                dataset=hf_dataset,
                metrics=metrics,
                llm=llm,
                raise_exceptions=False,  # Continue on errors
            ),
        )

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # Extract scores
        scores = eval_result.to_pandas().to_dict()
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

    async def run_benchmark(
        self,
        dataset: list[EvaluationDataset],
        scenarios: list[str] | None = None,
    ) -> dict[str, EvaluationResult]:
        """Run benchmark across multiple retrieval scenarios.

        Args:
            dataset: Evaluation dataset
            scenarios: List of scenario names to evaluate

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
            "timestamp": datetime.utcnow().isoformat(),
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
            f"**Timestamp**: {datetime.utcnow().isoformat()}",
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
        <p class="timestamp">Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>

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
