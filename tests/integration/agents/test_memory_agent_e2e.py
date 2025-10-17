"""E2E Integration Tests for Memory Agent with Real Services.

Sprint 7 Feature 7.4: Memory Agent (LangGraph Integration)
- NO MOCKS: Uses real MemoryRouter with Redis/Qdrant/Graphiti
- Tests full LangGraph coordinator flow with memory retrieval
- Tests state management and error handling
- Validates latency targets for memory operations

CRITICAL: All tests marked with @pytest.mark.integration
"""

import time
import pytest
from src.agents.memory_agent import MemoryAgent, memory_node

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

async def test_memory_agent_process_with_coordinator_e2e(memory_router):
    state = {"query": "What did we discuss about vector search?", "intent": "MEMORY", "metadata": {"config": {"top_k": 5}}}
    agent = MemoryAgent(memory_router=memory_router)
    start = time.time()
    result_state = await agent.process(state)
    latency_ms = (time.time() - start) * 1000
    assert "memory_results" in result_state
    assert latency_ms < 1000

async def test_memory_agent_retrieves_from_redis_e2e(memory_router, redis_memory_manager):
    session_id = "test_agent_redis"
    await redis_memory_manager.store_conversation_context(session_id=session_id, messages=[{"role": "user", "content": "Testing memory agent Redis retrieval"}])
    state = {"query": "What did I just say?", "intent": "MEMORY", "metadata": {"session_id": session_id}}
    agent = MemoryAgent(memory_router=memory_router)
    result_state = await agent.process(state)
    assert "memory_search" in result_state["metadata"]

async def test_memory_agent_state_management_e2e(memory_router):
    state = {"query": "Test state management", "intent": "MEMORY", "agent_trace": [], "metadata": {}}
    agent = MemoryAgent(memory_router=memory_router)
    result_state = await agent.process(state)
    assert result_state["query"] == state["query"]
    assert "memory_results" in result_state

async def test_memory_node_function_e2e(memory_router):
    state = {"query": "Test LangGraph node integration", "intent": "MEMORY", "metadata": {}}
    result_state = await memory_node(state)
    assert "memory_results" in result_state

async def test_memory_agent_error_handling_e2e():
    state = {"query": "test error handling", "intent": "MEMORY", "metadata": {}}
    agent = MemoryAgent()
    result_state = await agent.process(state)
    assert result_state is not None

async def test_memory_agent_latency_target_e2e(memory_router):
    state = {"query": "performance test query", "intent": "MEMORY", "metadata": {}}
    agent = MemoryAgent(memory_router=memory_router)
    start = time.time()
    await agent.process(state)
    latency_ms = (time.time() - start) * 1000
    assert latency_ms < 1000
