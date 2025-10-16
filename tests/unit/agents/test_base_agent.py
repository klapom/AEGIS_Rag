"""Unit tests for BaseAgent class.

Sprint 4 Feature 4.1: Base Agent Tests
"""

import time
from typing import Any

import pytest

from src.agents.base_agent import BaseAgent
from src.agents.state import create_initial_state


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Simple process implementation for testing."""
        self._add_trace(state, "processing")
        state["processed"] = True
        return state


class FailingAgent(BaseAgent):
    """Agent that always fails for testing error handling."""

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Raise an exception."""
        raise ValueError("Test error")


class TestBaseAgent:
    """Test BaseAgent class."""

    def test_init__creates_agent_with_name(self):
        """Test that agent is created with correct name."""
        agent = ConcreteAgent(name="test_agent")

        assert agent.name == "test_agent"
        assert agent.get_name() == "test_agent"

    def test_get_name__returns_agent_name(self):
        """Test get_name method."""
        agent = ConcreteAgent(name="my_agent")

        assert agent.get_name() == "my_agent"

    @pytest.mark.asyncio
    async def test_process__must_be_implemented(self):
        """Test that process method must be implemented."""
        # ConcreteAgent implements it, so this should work
        agent = ConcreteAgent(name="test")
        state = create_initial_state("test query")

        result = await agent.process(state)

        assert result["processed"] is True

    @pytest.mark.asyncio
    async def test_handle_error__adds_error_to_state(self):
        """Test that handle_error adds error information to state."""
        agent = ConcreteAgent(name="test_agent")
        state = create_initial_state("test")
        error = ValueError("Test error message")

        result = await agent.handle_error(state, error, "test context")

        assert "metadata" in result
        assert "error" in result["metadata"]
        assert result["metadata"]["error"]["agent"] == "test_agent"
        assert result["metadata"]["error"]["error_type"] == "ValueError"
        assert result["metadata"]["error"]["message"] == "Test error message"
        assert result["metadata"]["error"]["context"] == "test context"


class TestBaseAgentTracing:
    """Test agent tracing functionality."""

    def test_add_trace__adds_entry_to_agent_path(self):
        """Test that _add_trace adds entries to metadata."""
        agent = ConcreteAgent(name="test_agent")
        state = create_initial_state("test")

        agent._add_trace(state, "started")

        assert "metadata" in state
        assert "agent_path" in state["metadata"]
        assert "test_agent: started" in state["metadata"]["agent_path"]

    def test_add_trace__multiple_entries__maintains_order(self):
        """Test that multiple trace entries are kept in order."""
        agent = ConcreteAgent(name="test_agent")
        state = create_initial_state("test")

        agent._add_trace(state, "started")
        agent._add_trace(state, "processing")
        agent._add_trace(state, "completed")

        path = state["metadata"]["agent_path"]
        assert len(path) == 3
        assert path[0] == "test_agent: started"
        assert path[1] == "test_agent: processing"
        assert path[2] == "test_agent: completed"

    def test_add_trace__creates_metadata_if_missing(self):
        """Test that _add_trace creates metadata if not present."""
        agent = ConcreteAgent(name="test")
        state = {"query": "test"}

        agent._add_trace(state, "action")

        assert "metadata" in state
        assert "agent_path" in state["metadata"]

    def test_add_trace__duplicate_consecutive__not_added(self):
        """Test that duplicate consecutive traces are not added."""
        agent = ConcreteAgent(name="test")
        state = create_initial_state("test")

        agent._add_trace(state, "action")
        agent._add_trace(state, "action")

        assert len(state["metadata"]["agent_path"]) == 1


class TestBaseAgentLatency:
    """Test latency measurement functionality."""

    def test_measure_latency__returns_timing_dict(self):
        """Test that _measure_latency returns timing dict."""
        agent = ConcreteAgent(name="test")

        timing = agent._measure_latency()

        assert "start_time" in timing
        assert isinstance(timing["start_time"], float)

    def test_calculate_latency_ms__returns_correct_latency(self):
        """Test that latency calculation works correctly."""
        agent = ConcreteAgent(name="test")

        timing = agent._measure_latency()
        time.sleep(0.01)  # Sleep for 10ms
        latency = agent._calculate_latency_ms(timing)

        # Should be at least 10ms, but allow some variance
        assert latency >= 10.0
        assert latency < 100.0  # Sanity check

    def test_calculate_latency_ms__immediate__near_zero(self):
        """Test latency for immediate calculation."""
        agent = ConcreteAgent(name="test")

        timing = agent._measure_latency()
        latency = agent._calculate_latency_ms(timing)

        # Should be very small
        assert latency < 10.0


class TestBaseAgentLogging:
    """Test agent logging functionality."""

    def test_log_success__logs_without_error(self, caplog):
        """Test that _log_success works."""
        agent = ConcreteAgent(name="test")

        # Should not raise
        agent._log_success("test_operation", key="value")

    def test_log_error__logs_error_details(self, caplog):
        """Test that _log_error works."""
        agent = ConcreteAgent(name="test")
        error = ValueError("test error")

        # Should not raise
        agent._log_error("test_operation", error, context="test")


class TestBaseAgentErrorHandling:
    """Test error handling in BaseAgent."""

    def test_set_error__adds_error_to_metadata(self):
        """Test that _set_error adds error info to state."""
        agent = ConcreteAgent(name="test_agent")
        state = create_initial_state("test")
        error = RuntimeError("Something went wrong")

        agent._set_error(state, error, "processing failed")

        assert "metadata" in state
        assert "error" in state["metadata"]
        assert state["metadata"]["error"]["agent"] == "test_agent"
        assert state["metadata"]["error"]["error_type"] == "RuntimeError"
        assert state["metadata"]["error"]["message"] == "Something went wrong"
        assert state["metadata"]["error"]["context"] == "processing failed"

    def test_set_error__creates_metadata_if_missing(self):
        """Test that _set_error creates metadata if not present."""
        agent = ConcreteAgent(name="test")
        state = {"query": "test"}
        error = ValueError("error")

        agent._set_error(state, error, "test context")

        assert "metadata" in state
        assert "error" in state["metadata"]

    @pytest.mark.asyncio
    async def test_handle_error__full_flow(self):
        """Test complete error handling flow."""
        agent = FailingAgent(name="failing_agent")
        state = create_initial_state("test")

        try:
            await agent.process(state)
        except ValueError as e:
            result = await agent.handle_error(state, e, "process failed")

            assert "error" in result["metadata"]
            assert result["metadata"]["error"]["agent"] == "failing_agent"
            assert "Test error" in result["metadata"]["error"]["message"]


class TestBaseAgentIntegration:
    """Integration tests for BaseAgent with state flow."""

    @pytest.mark.asyncio
    async def test_full_agent_flow__with_tracing_and_timing(self):
        """Test complete agent flow with tracing and timing."""
        agent = ConcreteAgent(name="test_agent")
        state = create_initial_state("test query")

        # Start timing
        timing = agent._measure_latency()

        # Add initial trace
        agent._add_trace(state, "started")

        # Process
        result = await agent.process(state)

        # Calculate latency
        latency = agent._calculate_latency_ms(timing)

        # Verify result
        assert result["processed"] is True
        assert "test_agent: started" in result["metadata"]["agent_path"]
        assert "test_agent: processing" in result["metadata"]["agent_path"]
        assert latency >= 0

    @pytest.mark.asyncio
    async def test_multiple_agents__trace_chain(self):
        """Test that multiple agents create a trace chain."""
        agent1 = ConcreteAgent(name="agent1")
        agent2 = ConcreteAgent(name="agent2")
        state = create_initial_state("test")

        # Process through multiple agents
        state = await agent1.process(state)
        state = await agent2.process(state)

        # Verify trace chain
        path = state["metadata"]["agent_path"]
        assert "agent1: processing" in path
        assert "agent2: processing" in path
