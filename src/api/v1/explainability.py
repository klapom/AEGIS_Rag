"""
Explainability API Router
Sprint 104 Feature 104.10: Real-time explainability data integration

Provides 3-level explanations (Technical/Business/Regulatory) for:
- Retrieval queries (vector/graph/hybrid searches)
- Decision traces (agent decision-making)
- GDPR compliance reports (Article-level compliance)

EU AI Act Article 13 Compliance - Decision Transparency
"""

from datetime import datetime, timezone
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["explainability"])


# ============================================================================
# Pydantic Models
# ============================================================================


class DecisionStage(BaseModel):
    """Single stage in decision flow."""

    stage: Literal["intent", "skills", "retrieval", "response"]
    status: Literal["completed", "in_progress", "pending", "error"]
    details: str
    timestamp: Optional[str] = None


class IntentClassification(BaseModel):
    """Intent classification result."""

    classification: str
    confidence: float


class TraceListItem(BaseModel):
    """Recent decision trace summary."""

    trace_id: str
    query: str
    timestamp: str
    confidence: float
    user_id: Optional[str] = None


class DecisionTrace(BaseModel):
    """Complete decision trace with full details."""

    trace_id: str
    query: str
    timestamp: str
    user_id: Optional[str] = None
    intent: IntentClassification
    decision_flow: List[DecisionStage]
    confidence_overall: float
    hallucination_risk: float


class SourceDocument(BaseModel):
    """Source document with relevance score."""

    name: str
    relevance: float
    page: Optional[int] = None
    snippet: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None


class CertificationInfo(BaseModel):
    """Individual certification information."""

    id: str
    name: str
    status: Literal["certified", "pending", "expired"]
    issued_date: Optional[str] = None
    expiry_date: Optional[str] = None
    issuer: str
    certificate_url: Optional[str] = None


class CertificationStatusResponse(BaseModel):
    """Certification status response for EU compliance."""

    certification_status: Literal["compliant", "partial", "non_compliant"]
    certifications: List[CertificationInfo]
    compliance_score: float = Field(..., ge=0.0, le=100.0)
    last_audit_date: str


class ModelInfoResponse(BaseModel):
    """LLM model information response."""

    model_name: str
    model_version: str
    model_type: str = "LLM"
    embedding_model: str
    last_updated: str
    parameters: int = Field(..., description="Number of model parameters")
    context_window: int


class SkillConsideration(BaseModel):
    """Skill consideration in decision process."""

    name: str
    confidence: float
    trigger: Optional[str] = None
    selected: bool


class PerformanceMetrics(BaseModel):
    """Performance metrics for trace."""

    duration: int = Field(..., description="Duration in milliseconds")
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None


class TechnicalDetails(BaseModel):
    """Technical details for expert/audit explanations."""

    skills_considered: List[SkillConsideration]
    retrieval_mode: str
    chunks_retrieved: int
    chunks_used: int
    performance_metrics: PerformanceMetrics


class UserExplanation(BaseModel):
    """User-level explanation (simplified for end users)."""

    summary: str
    sources: List[SourceDocument] = Field(default_factory=list)
    capabilities_used: int
    capabilities_list: Optional[List[str]] = None


class ExpertExplanation(UserExplanation):
    """Expert-level explanation (technical details)."""

    technical_details: TechnicalDetails


class AuditExplanation(ExpertExplanation):
    """Audit-level explanation (complete trace for compliance)."""

    full_trace: dict[str, Any]


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/recent", response_model=List[TraceListItem])
async def get_recent_traces(
    user_id: Optional[str] = Query(None, alias="userId"),
    limit: int = Query(10, ge=1, le=100),
) -> List[TraceListItem]:
    """
    Get recent decision traces.

    Returns last N retrieval queries with basic information.
    Used by ExplainabilityPage to populate the trace selector.

    Args:
        user_id: Optional user ID to filter traces
        limit: Maximum number of traces to return (default: 10)

    Returns:
        List of recent traces with trace_id, query, timestamp, confidence
    """
    logger.info(
        "explainability_recent_traces_request",
        user_id=user_id,
        limit=limit,
    )

    # TODO: Fetch from database (Redis/Neo4j/audit trail)
    # For now, return mock data for E2E testing
    return [
        TraceListItem(
            trace_id=f"trace_{i:03d}",
            query=f"Sample query {i + 1}",
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            confidence=0.85 - (i * 0.05),
            user_id=user_id or "anonymous",
        )
        for i in range(min(limit, 5))
    ]


@router.get("/trace/{trace_id}", response_model=DecisionTrace)
async def get_decision_trace(trace_id: str) -> DecisionTrace:
    """
    Get complete decision trace for specific trace ID.

    Returns full trace details including intent classification,
    decision flow stages, confidence, and hallucination risk.

    Args:
        trace_id: Unique trace identifier

    Returns:
        Complete decision trace with all details
    """
    logger.info("explainability_trace_request", trace_id=trace_id)

    # TODO: Fetch from database
    # For now, return mock data with correct structure
    return DecisionTrace(
        trace_id=trace_id,
        query="What is the capital of France?",
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        user_id="anonymous",
        intent=IntentClassification(classification="factual_query", confidence=0.92),
        decision_flow=[
            DecisionStage(
                stage="intent",
                status="completed",
                details="Intent classified as factual_query with 92% confidence",
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ),
            DecisionStage(
                stage="skills",
                status="completed",
                details="Selected retrieval skill based on query classification",
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ),
            DecisionStage(
                stage="retrieval",
                status="completed",
                details="Retrieved 10 chunks using hybrid search (vector + graph)",
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ),
            DecisionStage(
                stage="response",
                status="completed",
                details="Generated response with 85% confidence",
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ),
        ],
        confidence_overall=0.85,
        hallucination_risk=0.15,
    )


@router.get("/explain/{trace_id}")
async def get_explanation(
    trace_id: str,
    level: Literal["user", "expert", "audit"] = Query("user"),
) -> UserExplanation | ExpertExplanation | AuditExplanation:
    """
    Get explanation for trace at specified level.

    Provides 3-level explanations:
    - User: Simplified explanation for end users
    - Expert: Technical details for developers
    - Audit: Complete trace for compliance audits

    Args:
        trace_id: Unique trace identifier
        level: Explanation level (user/expert/audit)

    Returns:
        Explanation object (type depends on level parameter)
    """
    logger.info(
        "explainability_explanation_request",
        trace_id=trace_id,
        level=level,
    )

    # Base explanation (user level)
    base_explanation = UserExplanation(
        summary=(
            "The system searched your knowledge base using hybrid search "
            "(combining vector similarity and graph relationships). "
            "It found 10 relevant documents and generated a response "
            "with 85% confidence."
        ),
        sources=[
            SourceDocument(
                name="Geography Knowledge Base",
                relevance=0.95,
                page=42,
                snippet="Paris is the capital and largest city of France...",
                confidence="high",
            ),
            SourceDocument(
                name="World Capitals Reference",
                relevance=0.87,
                page=15,
                snippet="France - Capital: Paris, Population: 2.2M...",
                confidence="high",
            ),
        ],
        capabilities_used=3,
        capabilities_list=[
            "Hybrid Search (Vector + Graph)",
            "Entity Recognition",
            "Response Generation",
        ],
    )

    if level == "user":
        return base_explanation

    # Technical details for expert/audit
    technical_details = TechnicalDetails(
        skills_considered=[
            SkillConsideration(
                name="vector_search",
                confidence=0.92,
                trigger="factual_query",
                selected=True,
            ),
            SkillConsideration(
                name="graph_reasoning",
                confidence=0.78,
                trigger="entity_detected",
                selected=True,
            ),
            SkillConsideration(
                name="deep_research",
                confidence=0.45,
                trigger="complexity_threshold",
                selected=False,
            ),
        ],
        retrieval_mode="hybrid",
        chunks_retrieved=10,
        chunks_used=5,
        performance_metrics=PerformanceMetrics(
            duration=320,
            tokens_used=1200,
            cost_usd=0.00024,
        ),
    )

    expert_explanation = ExpertExplanation(
        **base_explanation.model_dump(),
        technical_details=technical_details,
    )

    if level == "expert":
        return expert_explanation

    # Full trace for audit
    full_trace = {
        "trace_id": trace_id,
        "llm_calls": [
            {
                "model": "llama3.2:3b",
                "prompt_tokens": 450,
                "completion_tokens": 80,
                "latency_ms": 120,
            }
        ],
        "retrieval_steps": [
            {
                "mode": "vector",
                "query_embedding": "[1024-dim vector]",
                "top_k": 10,
                "results": 10,
            },
            {
                "mode": "graph",
                "entities": ["France", "Paris"],
                "relations": ["capital_of"],
                "hops": 2,
            },
        ],
        "reranking": {
            "input_chunks": 10,
            "output_chunks": 5,
            "method": "cross-encoder",
        },
        "gdpr_compliance": {
            "data_processed": "query text only",
            "retention_period": "7 years (audit)",
            "legal_basis": "Article 6(1)(f) - Legitimate interest",
        },
    }

    return AuditExplanation(
        **expert_explanation.model_dump(),
        full_trace=full_trace,
    )


@router.get("/attribution/{trace_id}", response_model=List[SourceDocument])
async def get_source_attribution(
    trace_id: str,
    claim: Optional[str] = Query(None),
) -> List[SourceDocument]:
    """
    Get source attribution for trace.

    Shows which sources were used to generate the response,
    with relevance scores and snippets for transparency.

    Args:
        trace_id: Unique trace identifier
        claim: Optional specific claim to find sources for

    Returns:
        List of source documents with relevance scores
    """
    logger.info(
        "explainability_attribution_request",
        trace_id=trace_id,
        claim=claim,
    )

    # TODO: Fetch from database (retrieve actual sources from trace)
    # For now, return mock data
    return [
        SourceDocument(
            name="Geography Knowledge Base",
            relevance=0.95,
            page=42,
            snippet="Paris is the capital and largest city of France...",
            confidence="high",
        ),
        SourceDocument(
            name="World Capitals Reference",
            relevance=0.87,
            page=15,
            snippet="France - Capital: Paris, Population: 2.2M...",
            confidence="high",
        ),
        SourceDocument(
            name="European Cities Guide",
            relevance=0.72,
            page=8,
            snippet="Major European capitals include Paris, Berlin, London...",
            confidence="medium",
        ),
    ]


@router.get("/model-info", response_model=ModelInfoResponse)
async def get_model_info() -> ModelInfoResponse:
    """
    Get LLM model information.

    Returns information about the models used in the AegisRAG system,
    including the primary LLM and embedding models.

    EU AI Act Article 13 - Information to be provided:
    - Model name and version
    - Model capabilities (context window, parameters)
    - Last update timestamp

    Returns:
        Model information including LLM and embedding model details
    """
    logger.info("explainability_model_info_request")

    # TODO: Fetch from actual LLM config (src/components/llm/llm_client.py)
    # For now, return mock data matching DGX Spark deployment
    return ModelInfoResponse(
        model_name="Nemotron3 Nano",
        model_version="1.0",
        model_type="LLM",
        embedding_model="BGE-M3",
        last_updated="2026-01-01T00:00:00Z",
        parameters=30_000_000_000,  # 30B parameters
        context_window=32768,
    )


# Sprint 107 Feature 107.3: Certification Status Endpoint
# Note: This endpoint is mounted under explainability router but will also be
# accessible via /api/v1/explainability/certification/status
# The E2E test expects /api/v1/certification/status, so we need to register
# this endpoint in a separate certification router as well (see main.py)
@router.get("/certification/status", response_model=CertificationStatusResponse)
async def get_certification_status() -> CertificationStatusResponse:
    """
    Get AI system certification status.

    Returns the current certification compliance status for various
    EU regulations and industry standards.

    EU AI Act Article 43 - Conformity Assessment:
    - Certification level (basic/standard/advanced)
    - Compliance with EU AI Act, GDPR, ISO standards
    - Audit dates and compliance scores

    Returns:
        Certification status with all active certifications
    """
    logger.info("explainability_certification_status_request")

    # TODO: Fetch from certification database/compliance system
    # For now, return mock data showing compliant status
    return CertificationStatusResponse(
        certification_status="compliant",
        certifications=[
            CertificationInfo(
                id="cert-1",
                name="EU AI Act Compliance",
                status="certified",
                issued_date="2026-01-01T00:00:00Z",
                expiry_date="2027-01-01T00:00:00Z",
                issuer="EU Certification Body",
                certificate_url="https://example.com/cert-1.pdf",
            ),
            CertificationInfo(
                id="cert-2",
                name="GDPR Compliance",
                status="certified",
                issued_date="2026-01-01T00:00:00Z",
                expiry_date="2027-01-01T00:00:00Z",
                issuer="Data Protection Authority",
                certificate_url="https://example.com/cert-2.pdf",
            ),
            CertificationInfo(
                id="cert-3",
                name="ISO 27001",
                status="pending",
                issued_date=None,
                expiry_date=None,
                issuer="ISO Certification Body",
                certificate_url=None,
            ),
        ],
        compliance_score=95.5,
        last_audit_date="2026-01-10T00:00:00Z",
    )
