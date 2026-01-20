"""Domain Classifier Agent Module.

Sprint 117.2: C-LARA Hybrid Domain Classification (8 SP)

This module provides LangGraph-based domain classification with a two-stage approach:
    - Stage A: C-LARA SetFit classifier (fast, local)
    - Stage B: LLM verification (optional, when confidence < 0.85)

Exports:
    - DomainClassificationState: State schema for LangGraph
    - DomainCandidate: Single domain candidate with confidence
    - create_domain_classification_graph: Factory function for graph
    - get_domain_classification_graph: Singleton graph instance
"""

from src.agents.domain_classifier.graph import (
    create_domain_classification_graph,
    get_domain_classification_graph,
)
from src.agents.domain_classifier.state import DomainCandidate, DomainClassificationState

__all__ = [
    "DomainClassificationState",
    "DomainCandidate",
    "create_domain_classification_graph",
    "get_domain_classification_graph",
]
