"""Evaluation module for AEGIS RAG system.

This module provides evaluation capabilities using RAGAS (RAG Assessment).
RAGAS is loaded lazily to avoid importing the heavy 'ragas' package unless needed.

Sprint 41 Feature 41.6: Benchmark Corpus Ingestion
- BenchmarkDatasetLoader: Load standard RAG datasets from HuggingFace
- BenchmarkCorpusIngestionPipeline: Ingest benchmark corpora with namespace isolation

Sprint 41 Feature 41.7: Enhanced RAGAS Evaluation Pipeline
- ragas_evaluator: New enhanced evaluator with namespace filtering and per-intent breakdown
- ragas_eval: Legacy RAGAS evaluator (backward compatibility)
"""

from src.evaluation.benchmark_loader import BenchmarkDatasetLoader, get_benchmark_loader
from src.evaluation.corpus_ingestion import (
    BenchmarkCorpusIngestionPipeline,
    get_corpus_ingestion_pipeline,
)
from src.evaluation.custom_metrics import CustomMetricsEvaluator
from src.evaluation.report_generator import ReportGenerator

__all__ = [
    "RAGASEvaluator",
    "CustomMetricsEvaluator",
    "ReportGenerator",
    "BenchmarkDatasetLoader",
    "get_benchmark_loader",
    "BenchmarkCorpusIngestionPipeline",
    "get_corpus_ingestion_pipeline",
]


def __getattr__(name: str):
    """Lazy import for RAGASEvaluator to avoid loading ragas unless needed.

    This prevents the 600MB+ ragas dependency from being loaded unless
    RAGASEvaluator is explicitly used.

    Args:
        name: Attribute name to load

    Returns:
        The requested attribute

    Raises:
        AttributeError: If attribute doesn't exist
    """
    if name == "RAGASEvaluator":
        # Sprint 41 Feature 41.7: Use new enhanced evaluator with namespace support
        from src.evaluation.ragas_evaluator import RAGASEvaluator

        return RAGASEvaluator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
