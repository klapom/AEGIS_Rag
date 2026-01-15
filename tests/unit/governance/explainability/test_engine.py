"""
Unit tests for Explainability Engine.

Tests cover:
- Trace capture with skills, retrieval, tools, confidence
- 3-level explanations (USER, EXPERT, AUDIT)
- Source attribution extraction
- Claim-to-source matching
- Confidence scoring
- Timing metrics
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.governance.explainability.engine import (
    DecisionTrace,
    ExplanationLevel,
    ExplainabilityEngine,
    SkillSelectionReason,
    SourceAttribution,
)
from src.governance.explainability.storage import InMemoryTraceStorage


@pytest.fixture
def trace_storage():
    """Provide in-memory trace storage."""
    return InMemoryTraceStorage()


@pytest.fixture
def mock_llm():
    """Provide mock LLM for testing."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def explainability_engine(trace_storage, mock_llm):
    """Provide explainability engine instance."""
    return ExplainabilityEngine(trace_storage, mock_llm)


@pytest.fixture
def sample_skill_context():
    """Provide sample skill selection context."""
    return {
        "activated": ["research_agent", "synthesis_agent"],
        "confidence": 0.85,
        "hallucination_risk": 0.12,
        "total_ms": 450.0,
        "skill_times": {"research_agent": 280.0, "synthesis_agent": 170.0},
        "considered_skills": [
            {
                "name": "research_agent",
                "confidence": 0.92,
                "trigger": "find information",
                "intent": "research",
                "alternatives": ["search_agent"],
            },
            {
                "name": "synthesis_agent",
                "confidence": 0.78,
                "trigger": None,
                "intent": "synthesis",
                "alternatives": [],
            },
        ],
    }


@pytest.fixture
def sample_retrieval_context():
    """Provide sample retrieval context."""
    return {
        "mode": "hybrid",
        "total_retrieved": 15,
        "used_in_response": 8,
        "chunks_used": [
            {
                "doc_id": "doc_123",
                "doc_name": "Research Paper on AI Governance",
                "chunk_id": "chunk_1",
                "score": 0.92,
                "text": "The EU AI Act (2024/1689) establishes comprehensive governance requirements for high-risk AI systems, including transparency and explainability mandates.",
                "pages": [5, 6],
            },
            {
                "doc_id": "doc_456",
                "doc_name": "GDPR Compliance Guide",
                "chunk_id": "chunk_2",
                "score": 0.87,
                "text": "Article 13 of the EU AI Act requires providers of AI systems to ensure transparency about the decision-making process, including data sources used.",
                "pages": [12],
            },
            {
                "doc_id": "doc_789",
                "doc_name": "Best Practices for AI Auditing",
                "chunk_id": "chunk_3",
                "score": 0.74,
                "text": "Audit trails should capture complete decision traces, including skill selection, tool invocations, and source attributions for compliance verification.",
                "pages": [8, 9, 10],
            },
        ],
    }


@pytest.fixture
def sample_tool_context():
    """Provide sample tool invocation context."""
    return {
        "invocations": [
            {"tool": "vector_search", "outcome": "success", "duration_ms": 45.0},
            {"tool": "graph_traversal", "outcome": "success", "duration_ms": 120.0},
            {"tool": "reranker", "outcome": "success", "duration_ms": 30.0},
        ]
    }


# === Trace Capture Tests ===


@pytest.mark.asyncio
async def test_capture_trace_basic(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test basic trace capture with all contexts."""
    query = "What are the transparency requirements in the EU AI Act?"
    response = "The EU AI Act requires providers to ensure transparency..."

    trace = await explainability_engine.capture_trace(
        query=query,
        response=response,
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    assert trace.query == query
    assert trace.final_response == response
    assert len(trace.skills_activated) == 2
    assert "research_agent" in trace.skills_activated
    assert trace.overall_confidence == 0.85
    assert trace.hallucination_risk == 0.12


@pytest.mark.asyncio
async def test_capture_trace_skills_extraction(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test extraction of skill selection reasons."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    assert len(trace.skills_considered) == 2

    # Check first skill
    skill1 = trace.skills_considered[0]
    assert skill1.skill_name == "research_agent"
    assert skill1.confidence == 0.92
    assert skill1.trigger_matched == "find information"
    assert skill1.intent_classification == "research"
    assert "search_agent" in skill1.alternative_skills


@pytest.mark.asyncio
async def test_capture_trace_attributions_extraction(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test extraction of source attributions."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    assert len(trace.attributions) == 3

    # Check first attribution
    attr1 = trace.attributions[0]
    assert attr1.document_id == "doc_123"
    assert attr1.document_name == "Research Paper on AI Governance"
    assert attr1.chunk_ids == ["chunk_1"]
    assert attr1.relevance_score == 0.92
    assert "EU AI Act" in attr1.text_excerpt
    assert attr1.page_numbers == [5, 6]


@pytest.mark.asyncio
async def test_capture_trace_retrieval_metrics(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test capture of retrieval metrics."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    assert trace.retrieval_mode == "hybrid"
    assert trace.chunks_retrieved == 15
    assert trace.chunks_used == 8


@pytest.mark.asyncio
async def test_capture_trace_tools_invoked(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test capture of tool invocations."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    assert len(trace.tools_invoked) == 3
    assert trace.tools_invoked[0]["tool"] == "vector_search"
    assert trace.tools_invoked[1]["tool"] == "graph_traversal"
    assert trace.tools_invoked[2]["tool"] == "reranker"


@pytest.mark.asyncio
async def test_capture_trace_timing_metrics(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test capture of timing metrics."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    assert trace.total_duration_ms == 450.0
    assert trace.skill_durations["research_agent"] == 280.0
    assert trace.skill_durations["synthesis_agent"] == 170.0


@pytest.mark.asyncio
async def test_capture_trace_persists_to_storage(
    explainability_engine,
    trace_storage,
    sample_skill_context,
    sample_retrieval_context,
    sample_tool_context,
):
    """Test that captured traces are persisted to storage."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    # Verify trace was saved
    stored_trace = await trace_storage.get(trace.id)
    assert stored_trace is not None
    assert stored_trace.id == trace.id
    assert stored_trace.query == trace.query


# === USER Level Explanation Tests ===


@pytest.mark.asyncio
async def test_explain_user_level_format(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test USER level explanation format."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.USER)

    assert "How this answer was generated:" in explanation
    assert "confidence" in explanation.lower()
    assert "Research Paper on AI Governance" in explanation
    assert "specialized capabilities" in explanation


@pytest.mark.asyncio
async def test_explain_user_level_high_confidence(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test USER level explanation with high confidence."""
    sample_skill_context["confidence"] = 0.9

    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.USER)
    assert "high confidence" in explanation


@pytest.mark.asyncio
async def test_explain_user_level_moderate_confidence(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test USER level explanation with moderate confidence."""
    sample_skill_context["confidence"] = 0.65

    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.USER)
    assert "moderate confidence" in explanation


@pytest.mark.asyncio
async def test_explain_user_level_low_confidence(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test USER level explanation with low confidence."""
    sample_skill_context["confidence"] = 0.4

    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.USER)
    assert "lower confidence" in explanation


@pytest.mark.asyncio
async def test_explain_user_level_top_sources(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test USER level explanation shows top 3 sources."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.USER)

    # Should contain top 3 sources
    assert "Research Paper on AI Governance" in explanation
    assert "GDPR Compliance Guide" in explanation
    assert "Best Practices for AI Auditing" in explanation


# === EXPERT Level Explanation Tests ===


@pytest.mark.asyncio
async def test_explain_expert_level_format(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test EXPERT level explanation format."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.EXPERT)

    assert "Technical Decision Trace:" in explanation
    assert "Query Analysis:" in explanation
    assert "Skill Selection:" in explanation
    assert "Tools Invoked:" in explanation
    assert "Confidence Metrics:" in explanation
    assert "Performance:" in explanation


@pytest.mark.asyncio
async def test_explain_expert_level_retrieval_metrics(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test EXPERT level includes retrieval metrics."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.EXPERT)

    assert "Retrieval mode: hybrid" in explanation
    assert "Chunks retrieved: 15" in explanation
    assert "Chunks used: 8" in explanation


@pytest.mark.asyncio
async def test_explain_expert_level_skill_details(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test EXPERT level includes skill selection details."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.EXPERT)

    assert "research_agent" in explanation
    assert "92.0%" in explanation  # Confidence
    assert "find information" in explanation  # Trigger


@pytest.mark.asyncio
async def test_explain_expert_level_confidence_metrics(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test EXPERT level includes confidence metrics."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.EXPERT)

    assert "Overall confidence: 85.0%" in explanation
    assert "Hallucination risk: 12.0%" in explanation


@pytest.mark.asyncio
async def test_explain_expert_level_performance_metrics(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test EXPERT level includes performance metrics."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.EXPERT)

    assert "Total duration: 450ms" in explanation
    assert "research_agent" in explanation
    assert "synthesis_agent" in explanation


@pytest.mark.asyncio
async def test_explain_expert_level_no_tools(
    explainability_engine, sample_skill_context, sample_retrieval_context
):
    """Test EXPERT level handles no tools invoked."""
    tool_context = {"invocations": []}

    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.EXPERT)

    assert "Tools Invoked:" in explanation
    assert "None" in explanation


# === AUDIT Level Explanation Tests ===


@pytest.mark.asyncio
async def test_explain_audit_level_format(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test AUDIT level explanation format."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.AUDIT)

    assert "Audit Trail - Full Decision Trace" in explanation
    assert "```json" in explanation
    assert "EU AI Act compliance" in explanation


@pytest.mark.asyncio
async def test_explain_audit_level_json_structure(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test AUDIT level produces valid JSON."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.AUDIT)

    # Extract JSON from markdown code block
    json_start = explanation.find("```json") + 7
    json_end = explanation.find("```", json_start)
    json_content = explanation[json_start:json_end].strip()

    # Parse JSON to validate structure
    audit_data = json.loads(json_content)

    assert "trace_id" in audit_data
    assert "timestamp" in audit_data
    assert "skills" in audit_data
    assert "retrieval" in audit_data
    assert "attributions" in audit_data
    assert "confidence" in audit_data
    assert "timing" in audit_data


@pytest.mark.asyncio
async def test_explain_audit_level_complete_data(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test AUDIT level includes all trace data."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.AUDIT)

    # Extract and parse JSON
    json_start = explanation.find("```json") + 7
    json_end = explanation.find("```", json_start)
    json_content = explanation[json_start:json_end].strip()
    audit_data = json.loads(json_content)

    # Verify skills data
    assert len(audit_data["skills"]["considered"]) == 2
    assert audit_data["skills"]["activated"] == ["research_agent", "synthesis_agent"]

    # Verify retrieval data
    assert audit_data["retrieval"]["mode"] == "hybrid"
    assert audit_data["retrieval"]["chunks_retrieved"] == 15
    assert audit_data["retrieval"]["chunks_used"] == 8

    # Verify attributions
    assert len(audit_data["attributions"]) == 3
    assert audit_data["attributions"][0]["document_id"] == "doc_123"


# === Claim Attribution Tests ===


@pytest.mark.asyncio
async def test_get_attribution_for_claim_success(
    explainability_engine,
    mock_llm,
    sample_skill_context,
    sample_retrieval_context,
    sample_tool_context,
):
    """Test successful claim attribution."""
    # Setup mock LLM response
    mock_response = MagicMock()
    mock_response.content = "0, 1"
    mock_llm.ainvoke.return_value = mock_response

    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    attributions = await explainability_engine.get_attribution_for_claim(
        response="test response",
        claim="EU AI Act requires transparency",
        trace_id=trace.id,
    )

    assert len(attributions) == 2
    assert attributions[0].document_id == "doc_123"
    assert attributions[1].document_id == "doc_456"


@pytest.mark.asyncio
async def test_get_attribution_for_claim_unsupported(
    explainability_engine,
    mock_llm,
    sample_skill_context,
    sample_retrieval_context,
    sample_tool_context,
):
    """Test claim attribution when no sources support claim."""
    # Setup mock LLM response
    mock_response = MagicMock()
    mock_response.content = "UNSUPPORTED"
    mock_llm.ainvoke.return_value = mock_response

    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    attributions = await explainability_engine.get_attribution_for_claim(
        response="test response",
        claim="Unsupported claim",
        trace_id=trace.id,
    )

    assert len(attributions) == 0


@pytest.mark.asyncio
async def test_get_attribution_for_claim_trace_not_found(
    explainability_engine, mock_llm
):
    """Test claim attribution when trace not found."""
    attributions = await explainability_engine.get_attribution_for_claim(
        response="test response",
        claim="Some claim",
        trace_id="nonexistent_trace",
    )

    assert len(attributions) == 0


@pytest.mark.asyncio
async def test_get_attribution_for_claim_no_attributions(
    explainability_engine, mock_llm, sample_skill_context, sample_tool_context
):
    """Test claim attribution when trace has no attributions."""
    retrieval_context = {"mode": "vector", "total_retrieved": 0, "chunks_used": []}

    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=retrieval_context,
        tool_context=sample_tool_context,
    )

    attributions = await explainability_engine.get_attribution_for_claim(
        response="test response",
        claim="Some claim",
        trace_id=trace.id,
    )

    assert len(attributions) == 0


@pytest.mark.asyncio
async def test_get_attribution_for_claim_llm_parsing_failure(
    explainability_engine,
    mock_llm,
    sample_skill_context,
    sample_retrieval_context,
    sample_tool_context,
):
    """Test claim attribution with LLM parsing failure (fallback to all attributions)."""
    # Setup mock LLM response with invalid format
    mock_response = MagicMock()
    mock_response.content = "invalid response format"
    mock_llm.ainvoke.return_value = mock_response

    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    attributions = await explainability_engine.get_attribution_for_claim(
        response="test response",
        claim="Some claim",
        trace_id=trace.id,
    )

    # Should fallback to returning all attributions
    assert len(attributions) == 3


# === Edge Cases and Error Handling ===


@pytest.mark.asyncio
async def test_explain_nonexistent_trace(explainability_engine):
    """Test explanation for nonexistent trace."""
    explanation = await explainability_engine.explain(
        "nonexistent_trace", ExplanationLevel.USER
    )
    assert explanation == "Trace not found"


@pytest.mark.asyncio
async def test_capture_trace_empty_contexts(explainability_engine):
    """Test trace capture with empty contexts."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context={},
        retrieval_context={},
        tool_context={},
    )

    assert trace.skills_activated == []
    assert trace.chunks_retrieved == 0
    assert trace.chunks_used == 0
    assert len(trace.attributions) == 0
    assert len(trace.tools_invoked) == 0


@pytest.mark.asyncio
async def test_capture_trace_default_values(explainability_engine):
    """Test trace capture uses default values when context missing."""
    trace = await explainability_engine.capture_trace(
        query="test query",
        response="test response",
        skill_context={},
        retrieval_context={},
        tool_context={},
    )

    assert trace.retrieval_mode == "unknown"
    assert trace.overall_confidence == 0.5
    assert trace.hallucination_risk == 0.0
    assert trace.total_duration_ms == 0.0


# === Integration Tests ===


@pytest.mark.asyncio
async def test_full_workflow_user_explanation(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test full workflow: capture trace -> generate USER explanation."""
    # Capture trace
    trace = await explainability_engine.capture_trace(
        query="What are EU AI Act transparency requirements?",
        response="The EU AI Act requires AI systems to provide transparent decision-making...",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    # Generate explanation
    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.USER)

    assert "How this answer was generated:" in explanation
    assert "high confidence" in explanation
    assert len(explanation.split("\n")) > 5  # Multi-line explanation


@pytest.mark.asyncio
async def test_full_workflow_expert_explanation(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test full workflow: capture trace -> generate EXPERT explanation."""
    # Capture trace
    trace = await explainability_engine.capture_trace(
        query="What are EU AI Act transparency requirements?",
        response="The EU AI Act requires AI systems to provide transparent decision-making...",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    # Generate explanation
    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.EXPERT)

    assert "Technical Decision Trace:" in explanation
    assert "research_agent" in explanation
    assert "450ms" in explanation


@pytest.mark.asyncio
async def test_full_workflow_audit_explanation(
    explainability_engine, sample_skill_context, sample_retrieval_context, sample_tool_context
):
    """Test full workflow: capture trace -> generate AUDIT explanation."""
    # Capture trace
    trace = await explainability_engine.capture_trace(
        query="What are EU AI Act transparency requirements?",
        response="The EU AI Act requires AI systems to provide transparent decision-making...",
        skill_context=sample_skill_context,
        retrieval_context=sample_retrieval_context,
        tool_context=sample_tool_context,
    )

    # Generate explanation
    explanation = await explainability_engine.explain(trace.id, ExplanationLevel.AUDIT)

    assert "Audit Trail" in explanation
    assert "```json" in explanation
    assert "EU AI Act compliance" in explanation
    assert trace.id in explanation or "trace_" in explanation
