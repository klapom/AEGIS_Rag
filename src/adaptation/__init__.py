"""Adaptation Framework for AegisRAG.

Sprint 67 Feature 67.5-67.12: Tool-Level Adaptation (Paper 2512.16301).
Sprint 69 Feature 69.4: Learned Adaptive Reranker Weights (8 SP).

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
    - training_data_extractor: Extract rerank pairs from traces (Sprint 69.4)
    - weight_optimizer: Optimize reranker weights via NDCG@5 (Sprint 69.4)

Architecture:
    User Query → RAG Pipeline → Trace → Dataset Builder → Training → Improved Models

Related ADRs:
    - ADR-079: LLM Intent Classifier (C-LARA)
    - TD-075: Intent Classification Improvement (60% → 85-92%)

References:
    - Paper 2512.16301: Tool-Level LLM Adaptation
    - C-LARA Framework: Intent Detection in the Age of LLMs
"""

from src.adaptation.dataset_builder import (
    DatasetBuilder,
    GraphExample,
    QAExample,
    RerankExample,
    TrainingExample,
)
from src.adaptation.eval_harness import EvalHarness, EvalResult, QualityCheck
from src.adaptation.intent_data_generator import CLARADataGenerator, IntentExample
from src.adaptation.intent_trainer import IntentTrainer, TrainingConfig
from src.adaptation.query_rewriter import (
    QueryRewriter,
    RewriteResult,
    get_query_rewriter,
    rewrite_query,
)
from src.adaptation.trace_telemetry import PipelineStage, TraceEvent, UnifiedTracer
from src.adaptation.training_data_extractor import (
    RerankTrainingPair,
    extract_rerank_pairs,
    load_training_pairs,
)
from src.adaptation.weight_optimizer import (
    OptimizedWeights,
    load_learned_weights,
    optimize_all_intents,
    optimize_weights,
    save_learned_weights,
)

__all__ = [
    # Intent generation & training
    "CLARADataGenerator",
    "IntentExample",
    "IntentTrainer",
    "TrainingConfig",
    # Query rewriting
    "QueryRewriter",
    "RewriteResult",
    "get_query_rewriter",
    "rewrite_query",
    # Dataset building
    "DatasetBuilder",
    "TrainingExample",
    "RerankExample",
    "QAExample",
    "GraphExample",
    # Evaluation
    "EvalHarness",
    "EvalResult",
    "QualityCheck",
    # Tracing
    "UnifiedTracer",
    "TraceEvent",
    "PipelineStage",
    # Reranker weight learning (Sprint 69.4)
    "RerankTrainingPair",
    "extract_rerank_pairs",
    "load_training_pairs",
    "OptimizedWeights",
    "optimize_weights",
    "optimize_all_intents",
    "save_learned_weights",
    "load_learned_weights",
]
