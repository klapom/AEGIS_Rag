"""Domain Classification State for LangGraph.

Sprint 117.2: C-LARA Hybrid Domain Classification (8 SP)

This module defines the state schema for the domain classification LangGraph.
The classifier uses a two-stage approach:
    Stage A: C-LARA SetFit classifier (~40ms, local, no LLM cost)
    Stage B: LLM Verification (optional, triggered when confidence < 0.85)

Architecture:
    classify_clara → route_by_confidence → {fast_return, llm_verify, llm_fallback}

Confidence Routing:
    conf >= 0.85  → Fast Return (no LLM, 70-80% of requests)
    0.60-0.85     → LLM Verify Top-K (15-25%)
    conf < 0.60   → LLM Fallback All Domains (5-10%)
    conf < 0.40   → Use "general" domain + flag "unclassified"
"""

from typing import Literal, TypedDict


class DomainCandidate(TypedDict, total=False):
    """Single domain classification candidate.

    Attributes:
        domain_id: Domain identifier (e.g., "medical", "legal", "technical")
        confidence: Classification confidence score (0.0-1.0)
        reasoning: Optional LLM reasoning for classification
        matched_entity_types: Entity types matched in document (LLM only)
        matched_intent: Detected intent for document (LLM only)
    """

    domain_id: str
    confidence: float
    reasoning: str | None
    matched_entity_types: list[str]
    matched_intent: str | None


class DomainClassificationState(TypedDict, total=False):
    """State for domain classification LangGraph.

    This state flows through the classification graph and tracks:
    - Input document context
    - C-LARA classification candidates
    - Confidence-based routing decisions
    - Optional LLM verification results
    - Final classification output

    Attributes:
        document_text: Document text to classify (required input)
        document_id: Optional document identifier for tracking
        chunk_ids: Optional chunk IDs associated with document
        top_k: Number of top candidates to return (default: 3)
        threshold: Minimum confidence threshold (default: 0.5)
        force_llm: Force LLM verification regardless of confidence (default: False)

        candidates: List of domain candidates from C-LARA (Stage A output)
        max_confidence: Highest confidence score from C-LARA
        classification_path: Path taken through graph (fast/verified/fallback)
        requires_review: Whether classification needs manual review
        final_domain_id: Final classified domain
        final_confidence: Final confidence score
        reasoning: LLM reasoning (if LLM was used)
        matched_entity_types: Matched entity types (if LLM was used)
        matched_intent: Detected intent (if LLM was used)
        latency_ms: Total classification latency
        alternative_domains: Alternative domain suggestions (top_k - 1)

        classification_status: Status of classification (confident/uncertain/unclassified)
        error: Error message if classification failed
    """

    # Input parameters
    document_text: str  # Required
    document_id: str | None
    chunk_ids: list[str] | None
    top_k: int
    threshold: float
    force_llm: bool

    # C-LARA Stage A outputs
    candidates: list[DomainCandidate]
    max_confidence: float

    # Routing decision
    classification_path: Literal["fast", "verified", "fallback"]

    # Final classification results
    requires_review: bool
    final_domain_id: str
    final_confidence: float
    reasoning: str | None
    matched_entity_types: list[str]
    matched_intent: str | None
    latency_ms: float
    alternative_domains: list[DomainCandidate]

    # Status tracking
    classification_status: Literal["confident", "uncertain", "unclassified"]
    error: str | None
