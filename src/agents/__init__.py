"""LangGraph Agent Orchestration Module.

This module contains the multi-agent orchestration system built with LangGraph.

Sprint 4: Multi-Agent Orchestration
- Feature 4.1: State Management & Base Graph (IMPLEMENTED)
- Feature 4.2: Query Router Agent (IMPLEMENTED)
- Feature 4.3: Vector Search Agent (IMPLEMENTED)
- Feature 4.4: Coordinator Agent with State Persistence (IMPLEMENTED)
- Feature 4.5: LangSmith Integration (IMPLEMENTED)
- Feature 4.6: Error Handling & Retry Logic (IMPLEMENTED)
"""

from src.agents.base_agent import BaseAgent
from src.agents.checkpointer import (
    clear_conversation_history,
    create_checkpointer,
    create_thread_config,
    get_conversation_history,
)
from src.agents.coordinator import CoordinatorAgent, get_coordinator
from src.agents.error_handler import (
    AgentExecutionError,
    LLMError,
    RetrievalError,
    RouterError,
    StateError,
    TimeoutError,
    clear_errors,
    get_error_summary,
    handle_agent_error,
)
from src.agents.graph import compile_graph, create_base_graph, invoke_graph
from src.agents.retry import retry_async_operation, retry_on_failure, retry_with_fallback
from src.agents.router import IntentClassifier, QueryIntent, get_classifier, route_query
from src.agents.state import (
    AgentState,
    QueryMetadata,
    RetrievedContext,
    SearchMetadata,
    create_initial_state,
    update_state_metadata,
)
from src.agents.vector_search_agent import VectorSearchAgent, vector_search_node

__all__ = [
    # State management
    "AgentState",
    "RetrievedContext",
    "SearchMetadata",
    "QueryMetadata",
    "create_initial_state",
    "update_state_metadata",
    # Base agent
    "BaseAgent",
    # Graph
    "create_base_graph",
    "compile_graph",
    "invoke_graph",
    # Router
    "QueryIntent",
    "IntentClassifier",
    "get_classifier",
    "route_query",
    # Vector Search Agent
    "VectorSearchAgent",
    "vector_search_node",
    # Coordinator Agent
    "CoordinatorAgent",
    "get_coordinator",
    # Checkpointing
    "create_checkpointer",
    "create_thread_config",
    "get_conversation_history",
    "clear_conversation_history",
    # Error Handling
    "AgentExecutionError",
    "RetrievalError",
    "LLMError",
    "StateError",
    "RouterError",
    "TimeoutError",
    "handle_agent_error",
    "get_error_summary",
    "clear_errors",
    # Retry Logic
    "retry_on_failure",
    "retry_with_fallback",
    "retry_async_operation",
]
