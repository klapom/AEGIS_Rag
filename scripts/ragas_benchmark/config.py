"""
Configuration for RAGAS benchmark dataset generation.

Sprint 82: Phase 1 - Text-Only Benchmark
ADR Reference: ADR-048

Quotas are designed for statistical significance:
- 500 samples → ±4% confidence interval at 95% confidence
- Per-category breakdown enables targeted analysis
"""

from typing import Dict

# =============================================================================
# Phase 1: Text-Only Benchmark (Sprint 82)
# =============================================================================

# Total samples for Phase 1
PHASE1_TOTAL_SAMPLES = 500
PHASE1_UNANSWERABLE_COUNT = 50  # 10% of total
PHASE1_ANSWERABLE_COUNT = 450  # 90% of total

# Doc type quotas (must sum to PHASE1_ANSWERABLE_COUNT)
DOC_TYPE_QUOTAS_PHASE1: Dict[str, int] = {
    "clean_text": 300,  # HotpotQA (200) + RAGBench (100)
    "log_ticket": 150,  # LogQA
}

# Question type distribution per doc_type
# Must sum to doc_type quota
QUESTION_TYPE_QUOTAS_PHASE1: Dict[str, Dict[str, int]] = {
    "clean_text": {
        "lookup": 60,       # Simple fact retrieval
        "definition": 40,   # "What is X?"
        "howto": 40,        # Procedural questions
        "multihop": 70,     # Multi-step reasoning (HotpotQA strength)
        "comparison": 50,   # "Which is X vs Y?"
        "policy": 20,       # Rule-based questions
        "numeric": 10,      # Number-based answers
        "entity": 10,       # Entity identification
    },  # Total: 300
    "log_ticket": {
        "lookup": 40,       # Log entry lookup
        "howto": 45,        # Troubleshooting steps
        "entity": 25,       # Component/service identification
        "multihop": 25,     # Cross-log reasoning
        "policy": 15,       # Operational procedures
    },  # Total: 150
}

# Difficulty distribution (applied across all samples)
DIFFICULTY_DISTRIBUTION: Dict[str, float] = {
    "D1": 0.40,  # Easy - single fact lookup
    "D2": 0.35,  # Medium - multi-fact reasoning
    "D3": 0.25,  # Hard - complex inference
}

# =============================================================================
# Dataset Configuration
# =============================================================================

# HuggingFace dataset identifiers
DATASET_CONFIGS = {
    "hotpot_qa": {
        "hf_name": "hotpot_qa",
        "subset": "distractor",
        "split": "train",  # Use train split (90K samples)
        "doc_type": "clean_text",
        "max_samples": 10000,  # Limit to speed up loading
    },
    # RAGBench has multiple subsets, we'll load specific ones
    "ragbench_covidqa": {
        "hf_name": "rungalileo/ragbench",
        "subset": "covidqa",
        "split": "test",
        "doc_type": "clean_text",
        "max_samples": 500,
    },
    "ragbench_techqa": {
        "hf_name": "rungalileo/ragbench",
        "subset": "techqa",
        "split": "test",
        "doc_type": "clean_text",
        "max_samples": 500,
    },
    "ragbench_msmarco": {
        "hf_name": "rungalileo/ragbench",
        "subset": "msmarco",
        "split": "test",
        "doc_type": "clean_text",
        "max_samples": 1000,
    },
    # Alternative log/technical dataset: use techqa from ragbench as log_ticket
    "ragbench_emanual": {
        "hf_name": "rungalileo/ragbench",
        "subset": "emanual",
        "split": "test",
        "doc_type": "log_ticket",  # Manual/documentation is similar to logs
        "max_samples": 500,
    },
}

# =============================================================================
# Question Type Classification Rules
# =============================================================================

# Keywords for heuristic question type classification
QUESTION_TYPE_KEYWORDS: Dict[str, list] = {
    "definition": [
        "what is", "what are", "define", "meaning of", "definition",
        "explain what", "describe what", "was ist", "erkläre",
    ],
    "howto": [
        "how to", "how do", "how can", "steps to", "procedure",
        "process for", "way to", "method to", "wie kann", "wie geht",
    ],
    "comparison": [
        "compare", "vs", "versus", "difference between", "which is",
        "better", "worse", "more", "less", "unterschied", "vergleich",
    ],
    "lookup": [
        "when", "where", "who", "which", "what year", "what date",
        "what time", "what place", "wann", "wo", "wer", "welche",
    ],
    "numeric": [
        "how many", "how much", "number of", "count", "total",
        "percentage", "rate", "wie viele", "wieviel",
    ],
    "entity": [
        "name of", "called", "identify", "list the", "who is",
        "what company", "what organization", "name", "identifiziere",
    ],
    "policy": [
        "should", "allowed", "permitted", "required", "must",
        "rule", "regulation", "policy", "guideline", "regel", "vorschrift",
    ],
    "multihop": [
        "both", "and also", "as well as", "in addition",
        "relationship between", "connected to", "led to",
    ],
}

# Default question type when no keywords match
DEFAULT_QUESTION_TYPE = "lookup"

# =============================================================================
# Unanswerable Generation Configuration
# =============================================================================

# Distribution of unanswerable generation methods
UNANSWERABLE_METHOD_DISTRIBUTION: Dict[str, float] = {
    "temporal_shift": 0.30,  # Future/past context
    "entity_swap": 0.30,     # Non-existent entities
    "negation": 0.20,        # NOT in corpus
    "cross_domain": 0.20,    # Unrelated domain
}

# Prefixes for temporal_shift method
TEMPORAL_SHIFT_PREFIXES = [
    "In version 9.9, ",
    "In the 2030 update, ",
    "For the deprecated feature, ",
    "When running on Solaris, ",
    "In the beta release, ",
    "According to the draft specification, ",
    "In the unreleased chapter, ",
    "Based on the 2035 projections, ",
]

# Fake entities for entity_swap method
FAKE_ENTITIES = [
    "Zephyrix Corp",
    "Quantumleaf Inc",
    "NovaStar Holdings",
    "Project AURORA",
    "Dr. Maximilian Thornberry",
    "Celestial Dynamics Ltd",
    "The Morpheus Protocol",
    "Hyperion Systems",
    "Operation Thunderstrike",
    "Professor Helena Vance",
]

# Cross-domain question templates
CROSS_DOMAIN_TEMPLATES = [
    "What is the chemical formula for {entity}?",
    "In which constellation is {entity} located?",
    "What is the atomic weight of {entity}?",
    "Who painted the famous portrait of {entity}?",
    "What is the boiling point of {entity}?",
]

# =============================================================================
# Validation Thresholds
# =============================================================================

# Maximum allowed deviation from target quotas (percentage)
QUOTA_TOLERANCE_PERCENT = 5.0

# Minimum context length (characters) to accept a sample
MIN_CONTEXT_LENGTH = 50

# Maximum context length (characters) - longer contexts are truncated
MAX_CONTEXT_LENGTH = 10000

# Minimum question length (characters)
MIN_QUESTION_LENGTH = 10

# Maximum dropout rate (percentage) before warning
MAX_DROPOUT_RATE = 5.0
