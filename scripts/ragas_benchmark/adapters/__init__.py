"""
Dataset adapters for RAGAS benchmark.

Each adapter normalizes a specific HuggingFace dataset to the
NormalizedSample format used by AegisRAG.
"""

from .base import DatasetAdapter
from .hotpotqa import HotpotQAAdapter
from .ragbench import RAGBenchAdapter
from .logqa import LogQAAdapter

__all__ = [
    "DatasetAdapter",
    "HotpotQAAdapter",
    "RAGBenchAdapter",
    "LogQAAdapter",
]
