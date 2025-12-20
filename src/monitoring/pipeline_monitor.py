"""Pipeline Monitoring and Reporting.

Sprint 44 Feature 44.7-44.9: Production-grade pipeline monitoring
Collects metrics from all pipeline stages and generates structured reports.

Pipeline Stages:
1. Input - File loading and text extraction
2. Chunking - Text segmentation
3. Extraction - Entity and relation extraction (LLM)
4. Entity Dedup - Entity deduplication
5. Relation Dedup - Relation deduplication
6. Storage - Neo4j/Qdrant insertion

Author: Claude Code
Date: 2025-12-12
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""

    stage: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "stage": self.stage,
            "duration_seconds": round(self.duration_seconds, 3),
            "metrics": self.metrics,
            "errors": self.errors,
        }


@dataclass
class SampleResult:
    """Result for a single sample/document processed."""

    sample_id: str
    question: str = ""
    ground_truth: str = ""
    status: str = "pending"  # pending, success, error
    stages: dict[str, StageMetrics] = field(default_factory=dict)
    total_time_seconds: float = 0.0
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "sample_id": self.sample_id,
            "question": self.question,
            "ground_truth": self.ground_truth,
            "status": self.status,
            "stages": {name: stage.to_dict() for name, stage in self.stages.items()},
            "total_time_seconds": round(self.total_time_seconds, 3),
            "error_message": self.error_message,
        }


class PipelineMonitor:
    """Monitors and reports on pipeline execution.

    Collects metrics from all pipeline stages for multiple samples,
    then generates comprehensive JSON and Markdown reports.

    Example:
        >>> monitor = PipelineMonitor(run_id="eval_20251212", model="qwen3:8b")
        >>> with monitor.sample("sample_001", question="What is...?"):
        ...     with monitor.stage("chunking") as stage:
        ...         chunks = chunk_text(text)
        ...         stage.record("chunks_created", len(chunks))
        ...     with monitor.stage("extraction") as stage:
        ...         entities = extract_entities(chunks)
        ...         stage.record("entities_raw", len(entities))
        >>> report = monitor.generate_report()
    """

    def __init__(
        self,
        run_id: str | None = None,
        model: str = "unknown",
        dataset: str = "unknown",
    ) -> None:
        """Initialize pipeline monitor.

        Args:
            run_id: Unique identifier for this run (auto-generated if None)
            model: LLM model used for extraction
            dataset: Dataset name (e.g., "hotpotqa")
        """
        self.run_id = run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.model = model
        self.dataset = dataset
        self.start_time = time.time()
        self.samples: list[SampleResult] = []
        self._current_sample: SampleResult | None = None
        self._current_stage: StageMetrics | None = None

        logger.info(
            "pipeline_monitor_initialized",
            run_id=self.run_id,
            model=model,
            dataset=dataset,
        )

    @contextmanager
    def sample(
        self,
        sample_id: str,
        question: str = "",
        ground_truth: str = "",
    ) -> Generator[SampleResult, None, None]:
        """Context manager for processing a sample.

        Args:
            sample_id: Unique identifier for the sample
            question: Optional question (for QA datasets)
            ground_truth: Optional ground truth answer

        Yields:
            SampleResult object for this sample
        """
        sample = SampleResult(
            sample_id=sample_id,
            question=question,
            ground_truth=ground_truth,
        )
        sample_start = time.time()
        self._current_sample = sample

        try:
            yield sample
            sample.status = "success"
        except Exception as e:
            sample.status = "error"
            sample.error_message = str(e)
            logger.error(
                "sample_processing_failed",
                sample_id=sample_id,
                error=str(e),
            )
        finally:
            sample.total_time_seconds = time.time() - sample_start
            self.samples.append(sample)
            self._current_sample = None

            logger.info(
                "sample_complete",
                sample_id=sample_id,
                status=sample.status,
                duration_seconds=round(sample.total_time_seconds, 2),
            )

    @contextmanager
    def stage(self, stage_name: str) -> Generator[StageMetrics, None, None]:
        """Context manager for a pipeline stage.

        Args:
            stage_name: Name of the stage (e.g., "chunking", "extraction")

        Yields:
            StageMetrics object for recording metrics
        """
        if self._current_sample is None:
            raise RuntimeError("stage() must be called within a sample() context")

        stage = StageMetrics(stage=stage_name)
        stage.start_time = time.time()
        self._current_stage = stage

        try:
            yield stage
        except Exception as e:
            stage.errors.append(str(e))
            raise
        finally:
            stage.end_time = time.time()
            stage.duration_seconds = stage.end_time - stage.start_time
            self._current_sample.stages[stage_name] = stage
            self._current_stage = None

    def record(self, metric_name: str, value: Any) -> None:
        """Record a metric for the current stage.

        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        if self._current_stage is None:
            logger.warning(
                "record_called_outside_stage",
                metric_name=metric_name,
            )
            return

        self._current_stage.metrics[metric_name] = value

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive report from collected metrics.

        Returns:
            Report dictionary with metadata, summaries, and per-sample results
        """
        total_time = time.time() - self.start_time
        successful = sum(1 for s in self.samples if s.status == "success")
        failed = sum(1 for s in self.samples if s.status == "error")

        # Aggregate metrics across all samples
        aggregated = self._aggregate_metrics()

        report = {
            "metadata": {
                "run_id": self.run_id,
                "model": self.model,
                "dataset": self.dataset,
                "timestamp": datetime.now().isoformat(),
                "total_samples": len(self.samples),
                "successful": successful,
                "failed": failed,
                "total_time_seconds": round(total_time, 2),
            },
            "summary": aggregated,
            "results": [s.to_dict() for s in self.samples],
        }

        logger.info(
            "report_generated",
            run_id=self.run_id,
            samples=len(self.samples),
            successful=successful,
            failed=failed,
        )

        return report

    def _aggregate_metrics(self) -> dict[str, Any]:
        """Aggregate metrics across all samples."""
        if not self.samples:
            return {}

        # Collect all stage names
        all_stages: set[str] = set()
        for sample in self.samples:
            all_stages.update(sample.stages.keys())

        summary: dict[str, Any] = {}

        for stage_name in sorted(all_stages):
            stage_data = []
            for sample in self.samples:
                if stage_name in sample.stages:
                    stage_data.append(sample.stages[stage_name])

            if not stage_data:
                continue

            # Aggregate common metrics
            stage_summary: dict[str, Any] = {
                "samples_with_stage": len(stage_data),
                "total_duration_seconds": sum(s.duration_seconds for s in stage_data),
                "avg_duration_seconds": sum(s.duration_seconds for s in stage_data) / len(stage_data),
                "errors": sum(len(s.errors) for s in stage_data),
            }

            # Aggregate numeric metrics
            numeric_metrics: dict[str, list[float]] = {}
            for stage in stage_data:
                for key, value in stage.metrics.items():
                    if isinstance(value, (int, float)):
                        if key not in numeric_metrics:
                            numeric_metrics[key] = []
                        numeric_metrics[key].append(value)

            for key, values in numeric_metrics.items():
                stage_summary[f"total_{key}"] = sum(values)
                stage_summary[f"avg_{key}"] = sum(values) / len(values)

            summary[stage_name] = stage_summary

        # Calculate overall stats
        summary["overall"] = {
            "total_samples": len(self.samples),
            "successful": sum(1 for s in self.samples if s.status == "success"),
            "failed": sum(1 for s in self.samples if s.status == "error"),
            "avg_time_per_sample": sum(s.total_time_seconds for s in self.samples) / len(self.samples),
        }

        return summary

    def save_json_report(self, output_path: str | Path) -> Path:
        """Save report as JSON file.

        Args:
            output_path: Path for output JSON file

        Returns:
            Path to saved file
        """
        report = self.generate_report()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("json_report_saved", path=str(output_path))
        return output_path

    def save_markdown_report(self, output_path: str | Path) -> Path:
        """Save report as Markdown file.

        Args:
            output_path: Path for output Markdown file

        Returns:
            Path to saved file
        """
        report = self.generate_report()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        md_content = self._generate_markdown(report)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        logger.info("markdown_report_saved", path=str(output_path))
        return output_path

    def _generate_markdown(self, report: dict[str, Any]) -> str:
        """Generate Markdown content from report."""
        meta = report["metadata"]
        summary = report["summary"]

        lines = [
            f"# Pipeline Evaluation Report: {meta['model']}",
            "",
            f"**Run ID:** {meta['run_id']}",
            f"**Model:** {meta['model']}",
            f"**Dataset:** {meta['dataset']}",
            f"**Timestamp:** {meta['timestamp']}",
            "",
            "---",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Samples | {meta['total_samples']} |",
            f"| Successful | {meta['successful']} |",
            f"| Failed | {meta['failed']} |",
            f"| Total Time | {meta['total_time_seconds']:.1f}s |",
            f"| Avg Time/Sample | {summary.get('overall', {}).get('avg_time_per_sample', 0):.1f}s |",
            "",
        ]

        # Stage summaries
        if summary:
            lines.extend([
                "## Stage Metrics",
                "",
            ])

            for stage_name, stage_data in summary.items():
                if stage_name == "overall":
                    continue

                lines.extend([
                    f"### {stage_name.title()}",
                    "",
                    "| Metric | Value |",
                    "|--------|-------|",
                ])

                for key, value in stage_data.items():
                    if isinstance(value, float):
                        lines.append(f"| {key} | {value:.2f} |")
                    else:
                        lines.append(f"| {key} | {value} |")

                lines.append("")

        # Per-sample results table
        lines.extend([
            "## Sample Results",
            "",
            "| Sample | Status | Time (s) | Entities | Relations |",
            "|--------|--------|----------|----------|-----------|",
        ])

        for result in report["results"]:
            sample_id = result["sample_id"]
            status = "✅" if result["status"] == "success" else "❌"
            time_s = result["total_time_seconds"]

            # Extract entity/relation counts from stages
            entities = "-"
            relations = "-"
            if "extraction" in result["stages"]:
                ext = result["stages"]["extraction"]["metrics"]
                entities = ext.get("entities_raw", "-")
                relations = ext.get("relations_raw", "-")

            lines.append(f"| {sample_id} | {status} | {time_s:.1f} | {entities} | {relations} |")

        lines.extend([
            "",
            "---",
            "",
            f"*Generated by PipelineMonitor on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])

        return "\n".join(lines)


class ModelComparisonReport:
    """Generates comparison reports across multiple model runs."""

    def __init__(self) -> None:
        """Initialize comparison report generator."""
        self.model_reports: dict[str, dict[str, Any]] = {}

    def add_report(self, model_name: str, report: dict[str, Any]) -> None:
        """Add a model's report to the comparison.

        Args:
            model_name: Name of the model
            report: Report dictionary from PipelineMonitor.generate_report()
        """
        self.model_reports[model_name] = report

    def load_report(self, model_name: str, json_path: str | Path) -> None:
        """Load a model's report from JSON file.

        Args:
            model_name: Name of the model
            json_path: Path to JSON report file
        """
        with open(json_path, encoding="utf-8") as f:
            report = json.load(f)
        self.model_reports[model_name] = report

    def generate_comparison(self) -> dict[str, Any]:
        """Generate comparison across all loaded models.

        Returns:
            Comparison dictionary with metrics per model
        """
        if not self.model_reports:
            return {}

        comparison = {
            "models": list(self.model_reports.keys()),
            "timestamp": datetime.now().isoformat(),
            "metrics": {},
        }

        # Extract key metrics for each model
        for model_name, report in self.model_reports.items():
            meta = report.get("metadata", {})
            summary = report.get("summary", {})

            model_metrics = {
                "samples": meta.get("total_samples", 0),
                "successful": meta.get("successful", 0),
                "failed": meta.get("failed", 0),
                "total_time_seconds": meta.get("total_time_seconds", 0),
                "avg_time_per_sample": summary.get("overall", {}).get("avg_time_per_sample", 0),
            }

            # Extract stage-specific metrics
            if "extraction" in summary:
                ext = summary["extraction"]
                model_metrics["total_entities"] = ext.get("total_entities_raw", 0)
                model_metrics["total_relations"] = ext.get("total_relations_raw", 0)

            if "entity_dedup" in summary:
                dedup = summary["entity_dedup"]
                model_metrics["entity_dedup_reduction"] = dedup.get("avg_reduction_percent", 0)

            if "relation_dedup" in summary:
                rel_dedup = summary["relation_dedup"]
                model_metrics["relation_dedup_reduction"] = rel_dedup.get("avg_reduction_percent", 0)

            comparison["metrics"][model_name] = model_metrics

        return comparison

    def save_comparison_markdown(self, output_path: str | Path) -> Path:
        """Save comparison as Markdown table.

        Args:
            output_path: Path for output Markdown file

        Returns:
            Path to saved file
        """
        comparison = self.generate_comparison()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Model Comparison Report",
            "",
            f"**Generated:** {comparison['timestamp']}",
            "",
            "## Comparison Matrix",
            "",
            "| Model | Samples | Success | Time (s) | Time/Sample | Entities | Relations |",
            "|-------|---------|---------|----------|-------------|----------|-----------|",
        ]

        for model_name in comparison["models"]:
            m = comparison["metrics"][model_name]
            lines.append(
                f"| {model_name} | {m['samples']} | {m['successful']} | "
                f"{m['total_time_seconds']:.0f} | {m['avg_time_per_sample']:.1f} | "
                f"{m.get('total_entities', '-')} | {m.get('total_relations', '-')} |"
            )

        lines.extend([
            "",
            "## Recommendations",
            "",
            "*(To be filled based on analysis)*",
            "",
        ])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info("comparison_markdown_saved", path=str(output_path))
        return output_path
