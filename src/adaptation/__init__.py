"""Adaptation Framework for AegisRAG.

Sprint 67 Feature 67.5-67.12: Tool-Level Adaptation (Paper 2512.16301).

This module implements the adaptation framework for continuous improvement
of RAG components through synthetic data generation, model training, and
online evaluation.

Components:
    - intent_data_generator: Generate labeled intent classification examples (Feature 67.10)
    - intent_trainer: Train SetFit model on synthetic data (Feature 67.11)
    - query_rewriter: Query rewriting for improved retrieval
    - dataset_builder: Convert traces to training data for reranker/rewriter
    - trace_logger: Unified trace format for all RAG stages
    - eval_harness: Quality gates for retrieval/generation metrics

Architecture:
    User Query → RAG Pipeline → Trace → Dataset Builder → Training → Improved Models

Related ADRs:
    - ADR-079: LLM Intent Classifier (C-LARA)
    - TD-075: Intent Classification Improvement (60% → 85-92%)

References:
    - Paper 2512.16301: Tool-Level LLM Adaptation
    - C-LARA Framework: Intent Detection in the Age of LLMs
"""

from src.adaptation.intent_data_generator import CLARADataGenerator, IntentExample
from src.adaptation.intent_trainer import IntentTrainer, TrainingConfig
from src.adaptation.query_rewriter import (
    QueryRewriter,
    RewriteResult,
    get_query_rewriter,
    rewrite_query,
)

__all__ = [
    "CLARADataGenerator",
    "IntentExample",
    "IntentTrainer",
    "TrainingConfig",
    "QueryRewriter",
    "RewriteResult",
    "get_query_rewriter",
    "rewrite_query",
]
