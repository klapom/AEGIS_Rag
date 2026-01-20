"""C-LARA Framework Components.

Sprint 67/81: C-LARA SetFit Intent Classification (95.22% accuracy)
Sprint 117.2: C-LARA Domain Classification (8 SP)

C-LARA (Context-aware LLM-Assisted RAG) Framework:
    - Intent Classification: Query intent detection (factual, procedural, etc.)
    - Domain Classification: Document-to-domain matching (NEW in Sprint 117.2)

Exports:
    - get_clara_domain_classifier: Singleton domain classifier
    - CLARADomainClassifier: Domain classifier class
    - reset_clara_classifier: Reset singleton (testing)
"""

from src.domains.llm_integration.clara.domain_classifier import (
    CLARADomainClassifier,
    get_clara_domain_classifier,
    reset_clara_classifier,
)

__all__ = [
    "CLARADomainClassifier",
    "get_clara_domain_classifier",
    "reset_clara_classifier",
]
