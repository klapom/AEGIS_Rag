"""Unit Tests for Deep Research API Models.

Sprint 116.10: Deep Research Multi-Step (13 SP)

Tests for Pydantic models used in deep research API endpoints.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.api.models.deep_research import (
    CancelResearchRequest,
    DeepResearchRequest,
    DeepResearchResponse,
    DeepResearchStatusResponse,
    ExecutionStepModel,
    ExportResearchRequest,
    IntermediateAnswer,
)
from src.api.models.research import Source


class TestExecutionStepModel:
    """Tests for ExecutionStepModel."""

    def test_execution_step_valid(self):
        """Test creating a valid execution step."""
        step = ExecutionStepModel(
            step_name="decompose_query",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_ms=1500,
            status="completed",
            result={"sub_queries": ["query1", "query2"]},
            error=None,
        )

        assert step.step_name == "decompose_query"
        assert step.status == "completed"
        assert step.duration_ms == 1500

    def test_execution_step_running(self):
        """Test execution step in running state."""
        step = ExecutionStepModel(
            step_name="retrieve_context",
            started_at=datetime.utcnow(),
            completed_at=None,
            duration_ms=None,
            status="running",
            result={},
            error=None,
        )

        assert step.status == "running"
        assert step.completed_at is None
        assert step.duration_ms is None

    def test_execution_step_failed(self):
        """Test execution step in failed state."""
        step = ExecutionStepModel(
            step_name="synthesize_answer",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_ms=500,
            status="failed",
            result={},
            error="LLM timeout",
        )

        assert step.status == "failed"
        assert step.error == "LLM timeout"


class TestDeepResearchRequest:
    """Tests for DeepResearchRequest."""

    def test_request_valid(self):
        """Test creating a valid deep research request."""
        request = DeepResearchRequest(
            query="What is quantum computing?",
            namespace="physics_docs",
            max_iterations=3,
            timeout_seconds=180,
            step_timeout_seconds=60,
        )

        assert request.query == "What is quantum computing?"
        assert request.namespace == "physics_docs"
        assert request.max_iterations == 3

    def test_request_defaults(self):
        """Test request with default values."""
        request = DeepResearchRequest(query="Test query")

        assert request.namespace == "default"
        assert request.max_iterations == 3
        assert request.timeout_seconds == 180
        assert request.step_timeout_seconds == 60

    def test_request_empty_query_fails(self):
        """Test that empty query fails validation."""
        with pytest.raises(ValidationError):
            DeepResearchRequest(query="")

    def test_request_max_iterations_bounds(self):
        """Test max_iterations boundary validation."""
        # Valid bounds
        request = DeepResearchRequest(query="test", max_iterations=1)
        assert request.max_iterations == 1

        request = DeepResearchRequest(query="test", max_iterations=5)
        assert request.max_iterations == 5

        # Invalid bounds
        with pytest.raises(ValidationError):
            DeepResearchRequest(query="test", max_iterations=0)

        with pytest.raises(ValidationError):
            DeepResearchRequest(query="test", max_iterations=6)


class TestIntermediateAnswer:
    """Tests for IntermediateAnswer."""

    def test_intermediate_answer_valid(self):
        """Test creating a valid intermediate answer."""
        sources = [
            Source(
                text="Quantum computing uses qubits",
                score=0.95,
                source_type="vector",
                metadata={},
                entities=["quantum computing", "qubits"],
                relationships=[],
            )
        ]

        answer = IntermediateAnswer(
            sub_question="What are qubits?",
            answer="Qubits are quantum bits used in quantum computing.",
            contexts_count=5,
            sources=sources,
            confidence=0.85,
        )

        assert answer.sub_question == "What are qubits?"
        assert answer.contexts_count == 5
        assert answer.confidence == 0.85
        assert len(answer.sources) == 1


class TestDeepResearchResponse:
    """Tests for DeepResearchResponse."""

    def test_response_complete(self):
        """Test complete deep research response."""
        sources = [
            Source(
                text="Test source",
                score=0.9,
                source_type="vector",
                metadata={},
                entities=[],
                relationships=[],
            )
        ]

        intermediate = [
            IntermediateAnswer(
                sub_question="Sub Q1",
                answer="Answer 1",
                contexts_count=3,
                sources=sources,
                confidence=0.8,
            )
        ]

        response = DeepResearchResponse(
            id="research_abc123",
            query="What is ML?",
            status="complete",
            sub_questions=["Sub Q1", "Sub Q2"],
            intermediate_answers=intermediate,
            final_answer="Machine learning is...",
            sources=sources,
            execution_steps=[],
            total_time_ms=15000,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error=None,
        )

        assert response.id == "research_abc123"
        assert response.status == "complete"
        assert len(response.sub_questions) == 2
        assert len(response.intermediate_answers) == 1
        assert response.total_time_ms == 15000

    def test_response_error(self):
        """Test error deep research response."""
        response = DeepResearchResponse(
            id="research_error",
            query="Test",
            status="error",
            sub_questions=[],
            intermediate_answers=[],
            final_answer="",
            sources=[],
            execution_steps=[],
            total_time_ms=5000,
            created_at=datetime.utcnow(),
            completed_at=None,
            error="Research timeout",
        )

        assert response.status == "error"
        assert response.error == "Research timeout"


class TestDeepResearchStatusResponse:
    """Tests for DeepResearchStatusResponse."""

    def test_status_response(self):
        """Test deep research status response."""
        status = DeepResearchStatusResponse(
            id="research_abc123",
            status="retrieving",
            current_step="Searching contexts",
            progress_percent=40,
            estimated_time_remaining_ms=30000,
            execution_steps=[],
        )

        assert status.id == "research_abc123"
        assert status.status == "retrieving"
        assert status.progress_percent == 40
        assert status.estimated_time_remaining_ms == 30000


class TestCancelResearchRequest:
    """Tests for CancelResearchRequest."""

    def test_cancel_request_with_reason(self):
        """Test cancel request with reason."""
        request = CancelResearchRequest(reason="User cancelled")
        assert request.reason == "User cancelled"

    def test_cancel_request_no_reason(self):
        """Test cancel request without reason."""
        request = CancelResearchRequest()
        assert request.reason is None


class TestExportResearchRequest:
    """Tests for ExportResearchRequest."""

    def test_export_markdown(self):
        """Test export request for markdown."""
        request = ExportResearchRequest(format="markdown")
        assert request.format == "markdown"
        assert request.include_sources is True
        assert request.include_intermediate is False

    def test_export_pdf_with_intermediate(self):
        """Test export request for PDF with intermediate."""
        request = ExportResearchRequest(
            format="pdf",
            include_sources=True,
            include_intermediate=True,
        )
        assert request.format == "pdf"
        assert request.include_intermediate is True
