"""
RAGAS Benchmark Dataset Builder

Sprint 82: Phase 1 - Text-Only Benchmark (500 samples)
ADR Reference: ADR-048

This package provides:
- Dataset loaders for HotpotQA, RAGBench, LogQA
- Stratified sampling with doc_type and question_type quotas
- Unanswerable question generation for anti-hallucination testing
- AegisRAG-compatible JSONL export
"""

from .models import NormalizedSample
from .dataset_loader import DatasetLoader
from .sampling import stratified_sample, classify_question_type, assign_difficulty
from .unanswerable import UnanswerableGenerator
from .export import export_jsonl, export_manifest

__version__ = "1.0.0"

__all__ = [
    "NormalizedSample",
    "DatasetLoader",
    "stratified_sample",
    "classify_question_type",
    "assign_difficulty",
    "UnanswerableGenerator",
    "export_jsonl",
    "export_manifest",
]
