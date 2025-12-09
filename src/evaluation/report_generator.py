"""Report generation for RAGAS evaluation results.

This module provides comprehensive report generation for evaluation results:
- Console/CLI output with colored tables (using rich)
- Markdown export with regression detection
- JSON export with metadata
- Baseline comparison and regression alerts

Example:
    >>> from src.evaluation.report_generator import ReportGenerator
    >>> from src.evaluation.ragas_eval import RAGASEvaluator
    >>>
    >>> evaluator = RAGASEvaluator()
    >>> results = await evaluator.run_benchmark(dataset, scenarios=["vector", "graph"])
    >>>
    >>> generator = ReportGenerator(baseline_path="data/evaluation/baselines/hotpotqa.json")
    >>> generator.generate_console_report(results)
    >>> generator.generate_markdown_report(results, output_path="data/evaluation/reports/report.md")
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.evaluation.ragas_eval import EvaluationResult

logger = structlog.get_logger(__name__)


class RegressionAlert(BaseModel):
    """Regression alert for a metric.

    Attributes:
        metric: Metric name (e.g., "context_precision")
        scenario: Scenario name (e.g., "hybrid-reranked")
        current: Current metric value
        baseline: Baseline metric value
        delta: Difference (current - baseline)
        percentage_change: Percentage change
    """

    metric: str = Field(..., description="Metric name")
    scenario: str = Field(..., description="Scenario name")
    current: float = Field(..., description="Current metric value")
    baseline: float = Field(..., description="Baseline metric value")
    delta: float = Field(..., description="Difference (current - baseline)")
    percentage_change: float = Field(..., description="Percentage change")


class ReportMetadata(BaseModel):
    """Metadata for evaluation report.

    Attributes:
        benchmark: Benchmark name (e.g., "HotpotQA", "MSMARCO")
        sample_size: Number of samples evaluated
        timestamp: Report generation timestamp
        scenarios: List of evaluated scenarios
        has_baseline: Whether baseline comparison is available
    """

    benchmark: str = Field(..., description="Benchmark name")
    sample_size: int = Field(..., description="Number of samples evaluated")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(), description="Report timestamp"
    )
    scenarios: list[str] = Field(..., description="Evaluated scenarios")
    has_baseline: bool = Field(default=False, description="Whether baseline comparison is available")
    additional_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ReportGenerator:
    """Report generator for RAGAS evaluation results.

    Generates comprehensive reports with:
    - Console output using rich library (colored tables)
    - Markdown export with regression detection
    - JSON export with full metadata
    - Baseline comparison and regression alerts

    Example:
        >>> generator = ReportGenerator(
        ...     baseline_path="data/evaluation/baselines/hotpotqa.json",
        ...     regression_threshold=0.05
        ... )
        >>> results = {"vector": result1, "graph": result2}
        >>> generator.generate_console_report(results)
        >>> generator.save_as_baseline(results, benchmark="hotpotqa")
    """

    def __init__(
        self,
        baseline_path: str | Path | None = None,
        regression_threshold: float = 0.05,
    ) -> None:
        """Initialize report generator.

        Args:
            baseline_path: Path to baseline results JSON file (optional)
            regression_threshold: Threshold for regression detection (default: 0.05 = 5%)
        """
        self.baseline_path = Path(baseline_path) if baseline_path else None
        self.regression_threshold = regression_threshold
        self.baseline_results: dict[str, EvaluationResult] | None = None

        # Load baseline if provided
        if self.baseline_path and self.baseline_path.exists():
            self._load_baseline()

        logger.info(
            "report_generator_initialized",
            baseline_path=str(self.baseline_path) if self.baseline_path else None,
            regression_threshold=self.regression_threshold,
            has_baseline=self.baseline_results is not None,
        )

    def _load_baseline(self) -> None:
        """Load baseline results from JSON file.

        Raises:
            ValueError: If baseline file format is invalid
        """
        if not self.baseline_path:
            return

        logger.info("loading_baseline", path=str(self.baseline_path))

        try:
            with open(self.baseline_path, encoding="utf-8") as f:
                data = json.load(f)

            # Parse baseline results
            self.baseline_results = {}
            for scenario, result_data in data.get("scenarios", {}).items():
                self.baseline_results[scenario] = EvaluationResult(**result_data)

            logger.info(
                "baseline_loaded",
                path=str(self.baseline_path),
                num_scenarios=len(self.baseline_results),
            )

        except Exception as e:
            logger.error("failed_to_load_baseline", path=str(self.baseline_path), error=str(e))
            self.baseline_results = None

    def detect_regressions(
        self,
        current_results: dict[str, EvaluationResult],
    ) -> list[RegressionAlert]:
        """Detect regressions by comparing current results to baseline.

        Args:
            current_results: Current evaluation results

        Returns:
            List of regression alerts (empty if no baseline or no regressions)
        """
        if not self.baseline_results:
            return []

        alerts = []
        metrics = ["context_precision", "context_recall", "faithfulness"]

        for scenario, current_result in current_results.items():
            if scenario not in self.baseline_results:
                continue

            baseline_result = self.baseline_results[scenario]

            for metric in metrics:
                current_value = getattr(current_result, metric)
                baseline_value = getattr(baseline_result, metric)

                delta = current_value - baseline_value
                percentage_change = (delta / baseline_value * 100) if baseline_value > 0 else 0.0

                # Check if regression (negative change beyond threshold)
                if delta < 0 and abs(delta) >= self.regression_threshold:
                    alert = RegressionAlert(
                        metric=metric,
                        scenario=scenario,
                        current=current_value,
                        baseline=baseline_value,
                        delta=delta,
                        percentage_change=percentage_change,
                    )
                    alerts.append(alert)

        logger.info("regression_detection_complete", num_alerts=len(alerts))
        return alerts

    def generate_console_report(
        self,
        results: dict[str, EvaluationResult],
        benchmark: str = "Unknown",
    ) -> None:
        """Generate console report with colored tables using rich.

        Args:
            results: Evaluation results by scenario
            benchmark: Benchmark name (e.g., "HotpotQA")

        Note:
            This method prints directly to console. Rich library required.
        """
        try:
            from rich.console import Console
            from rich.table import Table
        except ImportError:
            logger.error(
                "rich_not_installed",
                message="rich library not installed. Install with: pip install rich",
            )
            # Fallback to simple print
            self._generate_simple_console_report(results, benchmark)
            return

        console = Console()

        # Header
        console.print("\n[bold cyan]AEGIS RAG Evaluation Report[/bold cyan]")
        console.print(f"[dim]Date:[/dim] {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        console.print(f"[dim]Benchmark:[/dim] {benchmark}")

        # Overall metrics table
        table = Table(title="Overall Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Scenario", style="cyan", no_wrap=True)
        table.add_column("Context Precision", justify="right")
        table.add_column("Context Recall", justify="right")
        table.add_column("Faithfulness", justify="right")
        table.add_column("Samples", justify="right")
        table.add_column("Duration (s)", justify="right")

        for scenario, result in sorted(results.items()):
            table.add_row(
                scenario,
                f"{result.context_precision:.3f}",
                f"{result.context_recall:.3f}",
                f"{result.faithfulness:.3f}",
                str(result.num_samples),
                f"{result.duration_seconds:.2f}",
            )

        console.print(table)

        # Baseline comparison if available
        if self.baseline_results:
            console.print("\n[bold yellow]Baseline Comparison[/bold yellow]")
            comparison_table = Table(show_header=True, header_style="bold yellow")
            comparison_table.add_column("Scenario", style="cyan")
            comparison_table.add_column("Metric", style="dim")
            comparison_table.add_column("Current", justify="right")
            comparison_table.add_column("Baseline", justify="right")
            comparison_table.add_column("Delta", justify="right")

            metrics = ["context_precision", "context_recall", "faithfulness"]
            for scenario in sorted(results.keys()):
                if scenario not in self.baseline_results:
                    continue

                current = results[scenario]
                baseline = self.baseline_results[scenario]

                for metric in metrics:
                    current_value = getattr(current, metric)
                    baseline_value = getattr(baseline, metric)
                    delta = current_value - baseline_value

                    # Color delta based on sign
                    if delta > 0:
                        delta_str = f"[green]+{delta:.3f}[/green]"
                    elif delta < 0:
                        delta_str = f"[red]{delta:.3f}[/red]"
                    else:
                        delta_str = "[dim]0.000[/dim]"

                    comparison_table.add_row(
                        scenario,
                        metric.replace("_", " ").title(),
                        f"{current_value:.3f}",
                        f"{baseline_value:.3f}",
                        delta_str,
                    )

            console.print(comparison_table)

        # Regression alerts
        alerts = self.detect_regressions(results)
        if alerts:
            console.print("\n[bold red]Regression Alerts[/bold red]")
            for alert in alerts:
                console.print(
                    f"  [red]⚠[/red] {alert.scenario} - {alert.metric}: "
                    f"{alert.current:.3f} (was {alert.baseline:.3f}, "
                    f"delta: {alert.delta:.3f}, {alert.percentage_change:.1f}%)"
                )
        else:
            console.print("\n[green]✓ No regressions detected[/green]")

        console.print("")

    def _generate_simple_console_report(
        self,
        results: dict[str, EvaluationResult],
        benchmark: str = "Unknown",
    ) -> None:
        """Generate simple console report without rich library (fallback).

        Args:
            results: Evaluation results by scenario
            benchmark: Benchmark name
        """
        print("\n" + "=" * 80)
        print("AEGIS RAG Evaluation Report")
        print("=" * 80)
        print(f"Date: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Benchmark: {benchmark}")
        print("")

        # Overall metrics
        print("Overall Metrics:")
        print("-" * 80)
        print(
            f"{'Scenario':<20} {'Precision':<12} {'Recall':<12} {'Faithfulness':<15} {'Samples':<10}"
        )
        print("-" * 80)

        for scenario, result in sorted(results.items()):
            print(
                f"{scenario:<20} "
                f"{result.context_precision:<12.3f} "
                f"{result.context_recall:<12.3f} "
                f"{result.faithfulness:<15.3f} "
                f"{result.num_samples:<10}"
            )

        print("")

        # Regression alerts
        alerts = self.detect_regressions(results)
        if alerts:
            print("Regression Alerts:")
            print("-" * 80)
            for alert in alerts:
                print(
                    f"  ⚠ {alert.scenario} - {alert.metric}: "
                    f"{alert.current:.3f} (was {alert.baseline:.3f}, delta: {alert.delta:.3f})"
                )
        else:
            print("✓ No regressions detected")

        print("")

    def generate_markdown_report(
        self,
        results: dict[str, EvaluationResult],
        benchmark: str = "Unknown",
        output_path: str | Path | None = None,
    ) -> str:
        """Generate markdown report with regression detection.

        Args:
            results: Evaluation results by scenario
            benchmark: Benchmark name (e.g., "HotpotQA")
            output_path: Output file path (optional)

        Returns:
            Markdown report as string
        """
        logger.info(
            "generating_markdown_report",
            benchmark=benchmark,
            num_scenarios=len(results),
            output_path=str(output_path) if output_path else None,
        )

        # Calculate sample size (use first result)
        sample_size = next(iter(results.values())).num_samples if results else 0

        lines = [
            "# AEGIS RAG Evaluation Report",
            "",
            f"**Date:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Benchmark:** {benchmark}",
            f"**Sample Size:** {sample_size}",
            "",
            "## Overall Metrics",
            "",
            "| Scenario | Context Precision | Context Recall | Faithfulness | Samples | Duration (s) |",
            "|----------|-------------------|----------------|--------------|---------|--------------|",
        ]

        for scenario, result in sorted(results.items()):
            lines.append(
                f"| {scenario} | {result.context_precision:.3f} | "
                f"{result.context_recall:.3f} | {result.faithfulness:.3f} | "
                f"{result.num_samples} | {result.duration_seconds:.2f} |"
            )

        # Baseline comparison if available
        if self.baseline_results:
            lines.extend(
                [
                    "",
                    "## Baseline Comparison",
                    "",
                    "| Scenario | Metric | Current | Baseline | Delta | Status |",
                    "|----------|--------|---------|----------|-------|--------|",
                ]
            )

            metrics = ["context_precision", "context_recall", "faithfulness"]
            for scenario in sorted(results.keys()):
                if scenario not in self.baseline_results:
                    continue

                current = results[scenario]
                baseline = self.baseline_results[scenario]

                for metric in metrics:
                    current_value = getattr(current, metric)
                    baseline_value = getattr(baseline, metric)
                    delta = current_value - baseline_value

                    # Determine status emoji
                    if delta > 0:
                        status = "✅"
                    elif delta < -self.regression_threshold:
                        status = "⚠️"
                    else:
                        status = "➖"

                    lines.append(
                        f"| {scenario} | {metric.replace('_', ' ').title()} | "
                        f"{current_value:.3f} | {baseline_value:.3f} | "
                        f"{delta:+.3f} | {status} |"
                    )

        # Regression alerts
        alerts = self.detect_regressions(results)
        if alerts:
            lines.extend(
                [
                    "",
                    "## Regression Alerts",
                    "",
                ]
            )

            for alert in alerts:
                lines.append(
                    f"⚠️ **{alert.scenario}** - {alert.metric.replace('_', ' ').title()} "
                    f"dropped from {alert.baseline:.3f} to {alert.current:.3f} "
                    f"(delta: {alert.delta:.3f}, {alert.percentage_change:.1f}%)"
                )
        else:
            lines.extend(
                [
                    "",
                    "## Regression Status",
                    "",
                    "✅ No regressions detected",
                ]
            )

        # Per-scenario breakdown
        lines.extend(
            [
                "",
                "## Per-Scenario Details",
                "",
            ]
        )

        for scenario, result in sorted(results.items()):
            lines.extend(
                [
                    f"### {scenario}",
                    "",
                    f"- **Context Precision:** {result.context_precision:.3f}",
                    f"- **Context Recall:** {result.context_recall:.3f}",
                    f"- **Faithfulness:** {result.faithfulness:.3f}",
                    f"- **Samples:** {result.num_samples}",
                    f"- **Duration:** {result.duration_seconds:.2f}s",
                    f"- **Timestamp:** {result.timestamp}",
                    "",
                ]
            )

            if result.metadata:
                lines.extend(["**Metadata:**", "```json", json.dumps(result.metadata, indent=2), "```", ""])

        # Footer
        lines.extend(
            [
                "---",
                "",
                "Generated by AEGIS RAG Evaluation System",
            ]
        )

        report = "\n".join(lines)

        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            logger.info("markdown_report_saved", path=str(output_path))

        return report

    def generate_json_report(
        self,
        results: dict[str, EvaluationResult],
        benchmark: str = "Unknown",
        output_path: str | Path | None = None,
    ) -> str:
        """Generate JSON report with full metadata.

        Args:
            results: Evaluation results by scenario
            benchmark: Benchmark name
            output_path: Output file path (optional)

        Returns:
            JSON report as string
        """
        logger.info(
            "generating_json_report",
            benchmark=benchmark,
            num_scenarios=len(results),
            output_path=str(output_path) if output_path else None,
        )

        # Calculate sample size
        sample_size = next(iter(results.values())).num_samples if results else 0

        # Build metadata
        metadata = ReportMetadata(
            benchmark=benchmark,
            sample_size=sample_size,
            scenarios=list(results.keys()),
            has_baseline=self.baseline_results is not None,
        )

        # Build report data
        report_data = {
            "metadata": metadata.model_dump(),
            "scenarios": {scenario: result.model_dump() for scenario, result in results.items()},
        }

        # Add baseline comparison if available
        if self.baseline_results:
            report_data["baseline_comparison"] = {
                scenario: {
                    "current": results[scenario].model_dump(),
                    "baseline": self.baseline_results[scenario].model_dump(),
                }
                for scenario in results
                if scenario in self.baseline_results
            }

        # Add regression alerts
        alerts = self.detect_regressions(results)
        if alerts:
            report_data["regression_alerts"] = [alert.model_dump() for alert in alerts]

        # Add summary statistics
        report_data["summary"] = {
            "best_context_precision": max(r.context_precision for r in results.values()),
            "best_context_recall": max(r.context_recall for r in results.values()),
            "best_faithfulness": max(r.faithfulness for r in results.values()),
            "avg_context_precision": sum(r.context_precision for r in results.values())
            / len(results),
            "avg_context_recall": sum(r.context_recall for r in results.values()) / len(results),
            "avg_faithfulness": sum(r.faithfulness for r in results.values()) / len(results),
        }

        report = json.dumps(report_data, indent=2)

        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            logger.info("json_report_saved", path=str(output_path))

        return report

    def save_as_baseline(
        self,
        results: dict[str, EvaluationResult],
        benchmark: str,
        baseline_dir: str | Path = "data/evaluation/baselines",
    ) -> Path:
        """Save current results as baseline for future comparisons.

        Args:
            results: Evaluation results to save as baseline
            benchmark: Benchmark name (used in filename)
            baseline_dir: Directory to save baseline (default: data/evaluation/baselines)

        Returns:
            Path to saved baseline file
        """
        baseline_dir = Path(baseline_dir)
        baseline_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{benchmark}_{timestamp}.json"
        baseline_path = baseline_dir / filename

        # Also save as latest
        latest_path = baseline_dir / f"{benchmark}_latest.json"

        # Build baseline data
        baseline_data = {
            "benchmark": benchmark,
            "timestamp": datetime.now(UTC).isoformat(),
            "scenarios": {scenario: result.model_dump() for scenario, result in results.items()},
        }

        # Save both timestamped and latest versions
        for path in [baseline_path, latest_path]:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(baseline_data, f, indent=2)

        logger.info(
            "baseline_saved",
            benchmark=benchmark,
            path=str(baseline_path),
            num_scenarios=len(results),
        )

        return baseline_path

    def generate_all_reports(
        self,
        results: dict[str, EvaluationResult],
        benchmark: str,
        output_dir: str | Path = "data/evaluation/reports",
        save_as_baseline: bool = False,
    ) -> dict[str, Path]:
        """Generate all report formats (console, markdown, json).

        Args:
            results: Evaluation results
            benchmark: Benchmark name
            output_dir: Output directory for reports
            save_as_baseline: Whether to save results as baseline

        Returns:
            Dictionary mapping format to output path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        base_filename = f"{benchmark}_{timestamp}"

        # Generate console report (prints to stdout)
        self.generate_console_report(results, benchmark=benchmark)

        # Generate markdown report
        markdown_path = output_dir / f"{base_filename}.md"
        self.generate_markdown_report(results, benchmark=benchmark, output_path=markdown_path)

        # Generate JSON report
        json_path = output_dir / f"{base_filename}.json"
        self.generate_json_report(results, benchmark=benchmark, output_path=json_path)

        output_paths = {
            "markdown": markdown_path,
            "json": json_path,
        }

        # Save as baseline if requested
        if save_as_baseline:
            baseline_path = self.save_as_baseline(results, benchmark=benchmark)
            output_paths["baseline"] = baseline_path

        logger.info(
            "all_reports_generated",
            benchmark=benchmark,
            output_dir=str(output_dir),
            formats=list(output_paths.keys()),
        )

        return output_paths
