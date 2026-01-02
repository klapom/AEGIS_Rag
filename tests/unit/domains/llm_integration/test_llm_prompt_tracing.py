"""Unit tests for LLM Prompt Tracing feature.

Sprint 70 Feature 70.12: LLM Prompt Tracing

Tests automatic PhaseEvent emission for individual LLM prompt executions,
enabling granular tracking in the Real-Time Thinking Display.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.domains.llm_integration.models import (
    LLMTask,
    LLMResponse,
    TaskType,
    QualityRequirement,
)
from src.domains.llm_integration.proxy.aegis_llm_proxy import AegisLLMProxy
from src.models.phase_event import PhaseType, PhaseStatus


class TestPhaseTypeMapping:
    """Test _get_phase_type_from_task() prompt name mapping."""

    def test_graph_intent_prompt_mapping(self):
        """Test GRAPH_INTENT_PROMPT maps to LLM_PROMPT_INTENT."""
        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Test prompt",
            metadata={"prompt_name": "GRAPH_INTENT_PROMPT"},
        )

        phase_type = proxy._get_phase_type_from_task(task)

        assert phase_type == PhaseType.LLM_PROMPT_INTENT

    def test_decomposition_prompt_mapping(self):
        """Test DECOMPOSITION_PROMPT maps to LLM_PROMPT_DECOMPOSITION."""
        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test prompt",
            metadata={"prompt_name": "DECOMPOSITION_PROMPT"},
        )

        phase_type = proxy._get_phase_type_from_task(task)

        assert phase_type == PhaseType.LLM_PROMPT_DECOMPOSITION

    def test_expansion_prompt_mapping(self):
        """Test EXPANSION_PROMPT maps to LLM_PROMPT_EXPANSION."""
        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test prompt",
            metadata={"prompt_name": "QUERY_EXPANSION_PROMPT"},
        )

        phase_type = proxy._get_phase_type_from_task(task)

        assert phase_type == PhaseType.LLM_PROMPT_EXPANSION

    def test_refinement_prompt_mapping(self):
        """Test REFINEMENT_PROMPT maps to LLM_PROMPT_REFINEMENT."""
        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test prompt",
            metadata={"prompt_name": "QUERY_REFINEMENT_PROMPT"},
        )

        phase_type = proxy._get_phase_type_from_task(task)

        assert phase_type == PhaseType.LLM_PROMPT_REFINEMENT

    def test_unknown_prompt_fallback(self):
        """Test unknown prompt_name maps to LLM_PROMPT_OTHER."""
        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test prompt",
            metadata={"prompt_name": "UNKNOWN_PROMPT"},
        )

        phase_type = proxy._get_phase_type_from_task(task)

        assert phase_type == PhaseType.LLM_PROMPT_OTHER

    def test_no_prompt_name_returns_none(self):
        """Test task without prompt_name returns None (no tracing)."""
        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test prompt",
        )

        phase_type = proxy._get_phase_type_from_task(task)

        assert phase_type is None


@pytest.mark.asyncio
class TestPhaseEventEmission:
    """Test automatic PhaseEvent emission during generate()."""

    async def test_emit_in_progress_phase_event(self, mocker):
        """Test IN_PROGRESS phase event emitted before LLM execution."""
        # Mock dependencies
        mock_stream_phase_event = mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.stream_phase_event"
        )
        mock_execute = mocker.patch.object(
            AegisLLMProxy,
            "_execute_with_any_llm",
            return_value=LLMResponse(
                content="Test response",
                provider="local_ollama",
                model="test-model",
                tokens_used=10,
                tokens_input=5,
                tokens_output=5,
                cost_usd=0.0,
                latency_ms=100.0,
                routing_reason="test",
                fallback_used=False,
            ),
        )
        mocker.patch.object(AegisLLMProxy, "_route_task", return_value=("local_ollama", "test"))
        mocker.patch.object(AegisLLMProxy, "_track_metrics")

        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Test prompt",
            metadata={"prompt_name": "GRAPH_INTENT_PROMPT"},
        )

        # Execute
        await proxy.generate(task, use_cache=False, emit_phase_event=True)

        # Verify IN_PROGRESS event was emitted
        calls = mock_stream_phase_event.call_args_list
        assert len(calls) >= 2  # IN_PROGRESS + COMPLETED

        # Check first call (IN_PROGRESS)
        first_call = calls[0]
        assert first_call[1]["phase_type"] == PhaseType.LLM_PROMPT_INTENT
        assert first_call[1]["status"] == PhaseStatus.IN_PROGRESS
        assert "prompt_name" in first_call[1]["metadata"]
        assert first_call[1]["metadata"]["prompt_name"] == "GRAPH_INTENT_PROMPT"

    async def test_emit_completed_phase_event(self, mocker):
        """Test COMPLETED phase event emitted after successful LLM execution."""
        # Mock dependencies
        mock_stream_phase_event = mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.stream_phase_event"
        )
        mock_execute = mocker.patch.object(
            AegisLLMProxy,
            "_execute_with_any_llm",
            return_value=LLMResponse(
                content="Test response",
                provider="local_ollama",
                model="test-model",
                tokens_used=10,
                tokens_input=5,
                tokens_output=5,
                cost_usd=0.001,
                latency_ms=150.0,
                routing_reason="test",
                fallback_used=False,
            ),
        )
        mocker.patch.object(AegisLLMProxy, "_route_task", return_value=("local_ollama", "test"))
        mocker.patch.object(AegisLLMProxy, "_track_metrics")

        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Test prompt",
            metadata={"prompt_name": "DECOMPOSITION_PROMPT"},
        )

        # Execute
        await proxy.generate(task, use_cache=False, emit_phase_event=True)

        # Verify COMPLETED event was emitted
        calls = mock_stream_phase_event.call_args_list
        assert len(calls) >= 2  # IN_PROGRESS + COMPLETED

        # Check second call (COMPLETED)
        second_call = calls[1]
        assert second_call[1]["phase_type"] == PhaseType.LLM_PROMPT_DECOMPOSITION
        assert second_call[1]["status"] == PhaseStatus.COMPLETED
        assert second_call[1]["metadata"]["duration_ms"] == 150.0
        assert second_call[1]["metadata"]["provider"] == "local_ollama"
        assert second_call[1]["metadata"]["cost_usd"] == 0.001

    async def test_emit_failed_phase_event(self, mocker):
        """Test FAILED phase event emitted when all providers fail."""
        # Mock dependencies
        mock_stream_phase_event = mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.stream_phase_event"
        )
        mocker.patch.object(
            AegisLLMProxy,
            "_execute_with_any_llm",
            side_effect=Exception("Provider error"),
        )
        mocker.patch.object(AegisLLMProxy, "_route_task", return_value=("alibaba_cloud", "test"))

        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test prompt",
            metadata={"prompt_name": "ENTITY_EXTRACTION_PROMPT"},
        )

        # Execute and expect error
        with pytest.raises(Exception):
            await proxy.generate(task, use_cache=False, emit_phase_event=True)

        # Verify FAILED event was emitted
        calls = mock_stream_phase_event.call_args_list
        assert len(calls) >= 2  # IN_PROGRESS + FAILED

        # Check last call (FAILED)
        last_call = calls[-1]
        assert last_call[1]["phase_type"] == PhaseType.LLM_PROMPT_ENTITY_EXTRACTION
        assert last_call[1]["status"] == PhaseStatus.FAILED
        assert "error" in last_call[1]["metadata"]

    async def test_no_phase_event_when_disabled(self, mocker):
        """Test no phase events emitted when emit_phase_event=False."""
        # Mock dependencies
        mock_stream_phase_event = mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.stream_phase_event"
        )
        mock_execute = mocker.patch.object(
            AegisLLMProxy,
            "_execute_with_any_llm",
            return_value=LLMResponse(
                content="Test response",
                provider="local_ollama",
                model="test-model",
                tokens_used=10,
                tokens_input=5,
                tokens_output=5,
                cost_usd=0.0,
                latency_ms=100.0,
                routing_reason="test",
                fallback_used=False,
            ),
        )
        mocker.patch.object(AegisLLMProxy, "_route_task", return_value=("local_ollama", "test"))
        mocker.patch.object(AegisLLMProxy, "_track_metrics")

        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Test prompt",
            metadata={"prompt_name": "GRAPH_INTENT_PROMPT"},
        )

        # Execute with emit_phase_event=False
        await proxy.generate(task, use_cache=False, emit_phase_event=False)

        # Verify NO phase events were emitted
        assert not mock_stream_phase_event.called

    async def test_no_phase_event_when_no_prompt_name(self, mocker):
        """Test no phase events emitted when task has no prompt_name."""
        # Mock dependencies
        mock_stream_phase_event = mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.stream_phase_event"
        )
        mock_execute = mocker.patch.object(
            AegisLLMProxy,
            "_execute_with_any_llm",
            return_value=LLMResponse(
                content="Test response",
                provider="local_ollama",
                model="test-model",
                tokens_used=10,
                tokens_input=5,
                tokens_output=5,
                cost_usd=0.0,
                latency_ms=100.0,
                routing_reason="test",
                fallback_used=False,
            ),
        )
        mocker.patch.object(AegisLLMProxy, "_route_task", return_value=("local_ollama", "test"))
        mocker.patch.object(AegisLLMProxy, "_track_metrics")

        proxy = AegisLLMProxy()
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test prompt",
            # No metadata with prompt_name
        )

        # Execute
        await proxy.generate(task, use_cache=False, emit_phase_event=True)

        # Verify NO phase events were emitted (no prompt_name = no tracing)
        assert not mock_stream_phase_event.called
