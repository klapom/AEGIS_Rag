"""Pytest configuration and fixtures for unit tests of Chat API endpoints.

This module provides:
- Async HTTP client fixture for testing FastAPI endpoints
- Mocked dependencies (coordinator, memory, generators)
- Proper patching of lazy imports
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
async def async_client():
    """Fixture for async HTTP client to test chat endpoints.

    This fixture:
    1. Patches ALL external dependencies before app startup
    2. Creates FastAPI app with dependencies mocked
    3. Returns AsyncClient for making requests

    Returns:
        AsyncClient: Async HTTP client connected to test app
    """
    # Patch all external dependencies BEFORE importing the app
    with patch("src.agents.coordinator.compile_graph") as mock_compile_graph, \
         patch("src.agents.coordinator.create_checkpointer") as mock_create_checkpointer, \
         patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_llm_proxy_followup, \
         patch("src.api.v1.title_generator.get_aegis_llm_proxy") as mock_get_llm_proxy_title:

        # Configure graph mock
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock()
        mock_compile_graph.return_value = mock_graph

        # Configure checkpointer mock
        mock_create_checkpointer.return_value = MagicMock()

        # Configure LLM proxy mocks for follow-up and title generation
        mock_llm_proxy = AsyncMock()
        mock_llm_proxy.invoke = AsyncMock(return_value="Generated follow-up question?")
        mock_get_llm_proxy_followup.return_value = mock_llm_proxy
        mock_get_llm_proxy_title.return_value = mock_llm_proxy

        # Now import app after dependencies are patched
        from src.api.main import app

        # Patch coordinator singleton in the chat module
        with patch("src.api.v1.chat.get_coordinator") as mock_get_coordinator, \
             patch("src.components.memory.get_redis_memory") as mock_get_redis_memory, \
             patch("src.components.memory.get_unified_memory_api") as mock_get_unified_memory, \
             patch("src.agents.followup_generator.generate_followup_questions") as mock_generate_followup, \
             patch("src.api.v1.title_generator.generate_conversation_title") as mock_generate_title:

            # Configure coordinator mock
            mock_coordinator = AsyncMock()
            mock_coordinator.process_query = AsyncMock()
            mock_coordinator.process_query_stream = None  # No streaming by default
            mock_get_coordinator.return_value = mock_coordinator

            # Configure Redis memory mock
            mock_redis_memory = AsyncMock()
            mock_redis_memory.retrieve = AsyncMock(return_value=None)
            mock_redis_memory.store = AsyncMock(return_value=True)
            mock_redis_memory.delete = AsyncMock(return_value=True)
            mock_get_redis_memory.return_value = mock_redis_memory

            # Configure unified memory API mock
            mock_unified_memory = AsyncMock()
            mock_unified_memory.delete = AsyncMock(return_value=True)
            mock_get_unified_memory.return_value = mock_unified_memory

            # Configure follow-up questions generator
            mock_generate_followup.return_value = ["Follow-up question 1?", "Follow-up question 2?"]

            # Configure title generator
            mock_generate_title.return_value = "Test Conversation Title"

            # Create async client with the app
            async with AsyncClient(
                app=app,
                base_url="http://test"
            ) as client:
                yield client
