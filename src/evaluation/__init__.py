"""Evaluation module for AEGIS RAG system.

This module provides evaluation capabilities using RAGAS (RAG Assessment).
RAGAS is loaded lazily to avoid importing the heavy 'ragas' package unless needed.
"""

from src.evaluation.custom_metrics import CustomMetricsEvaluator

__all__ = ["RAGASEvaluator", "CustomMetricsEvaluator"]


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
        from src.evaluation.ragas_eval import RAGASEvaluator

        return RAGASEvaluator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
