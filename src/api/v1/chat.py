"""Chat API Endpoints for AEGIS RAG.

Sprint 10 Feature 10.1: FastAPI Chat Endpoints

This module provides RESTful chat endpoints for the Gradio UI and future React frontend.
It integrates the CoordinatorAgent for query processing and UnifiedMemoryAPI for session management.
"""

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.agents.coordinator import CoordinatorAgent
from src.components.memory import get_unified_memory_api
from src.core.exceptions import AegisRAGException

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize coordinator (singleton pattern)
_coordinator: CoordinatorAgent | None = None


def get_coordinator() -> CoordinatorAgent:
    """Get or create singleton CoordinatorAgent instance."""
    global _coordinator
    if _coordinator is None:
        _coordinator = CoordinatorAgent(use_persistence=True)
        logger.info("coordinator_initialized_for_chat_api")
    return _coordinator


# Request/Response Models

class ChatRequest(BaseModel):
    """Chat request model."""

    query: str = Field(..., min_length=1, max_length=5000, description="User query")
    session_id: str | None = Field(
        default=None,
        description="Session ID for conversation history. Auto-generated if not provided."
    )
    intent: str | None = Field(
        default=None,
        description="Optional intent override (graph, vector, hybrid)"
    )
    include_sources: bool = Field(
        default=True,
        description="Include source documents in response"
    )
    include_tool_calls: bool = Field(
        default=False,
        description="Include MCP tool call information in response"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Was ist AEGIS RAG?",
                "session_id": "user-123-session",
                "include_sources": True,
                "include_tool_calls": False
            }
        }


class SourceDocument(BaseModel):
    """Source document metadata."""

    text: str = Field(..., description="Document text content")
    title: str | None = Field(default=None, description="Document title")
    source: str | None = Field(default=None, description="Source file path")
    score: float | None = Field(default=None, description="Relevance score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ToolCallInfo(BaseModel):
    """MCP tool call information."""

    tool_name: str = Field(..., description="Name of the MCP tool called")
    server: str = Field(..., description="MCP server name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool call arguments")
    result: Any | None = Field(default=None, description="Tool call result")
    duration_ms: float = Field(..., description="Tool call duration in milliseconds")
    success: bool = Field(..., description="Whether tool call succeeded")
    error: str | None = Field(default=None, description="Error message if failed")


class ChatResponse(BaseModel):
    """Chat response model."""

    answer: str = Field(..., description="Generated answer")
    query: str = Field(..., description="Original user query")
    session_id: str = Field(..., description="Session ID for this conversation")
    intent: str | None = Field(default=None, description="Detected query intent")
    sources: list[SourceDocument] = Field(
        default_factory=list,
        description="Source documents used for answer generation"
    )
    tool_calls: list[ToolCallInfo] = Field(
        default_factory=list,
        description="MCP tool calls made during query processing"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata (latency, agent_path, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "AEGIS RAG ist ein agentisches RAG-System...",
                "query": "Was ist AEGIS RAG?",
                "session_id": "user-123-session",
                "intent": "vector",
                "sources": [
                    {
                        "text": "AEGIS RAG steht für...",
                        "title": "CLAUDE.md",
                        "source": "docs/core/CLAUDE.md",
                        "score": 0.92
                    }
                ],
                "tool_calls": [
                    {
                        "tool_name": "read_file",
                        "server": "filesystem-server",
                        "arguments": {"path": "/docs/CLAUDE.md"},
                        "result": {"content": "# CLAUDE.md - AegisRAG..."},
                        "duration_ms": 45.2,
                        "success": True,
                        "error": None
                    }
                ],
                "metadata": {
                    "latency_seconds": 1.23,
                    "agent_path": ["router", "vector_agent", "generator"]
                }
            }
        }


class ConversationHistoryResponse(BaseModel):
    """Conversation history response."""

    session_id: str
    messages: list[dict[str, Any]]
    message_count: int


class SessionDeleteResponse(BaseModel):
    """Session deletion response."""

    session_id: str
    status: str
    message: str


# API Endpoints

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat query through the RAG system.

    This endpoint:
    1. Validates the query
    2. Generates/validates session_id
    3. Processes query through CoordinatorAgent
    4. Extracts answer and sources
    5. Returns structured response

    Args:
        request: ChatRequest with query and optional session_id

    Returns:
        ChatResponse with answer, sources, and metadata

    Raises:
        HTTPException: If query processing fails
    """
    # Generate session_id if not provided
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(
        "chat_request_received",
        query=request.query[:100],  # Log first 100 chars
        session_id=session_id,
        intent_override=request.intent
    )

    try:
        # Get coordinator
        coordinator = get_coordinator()

        # Process query through multi-agent system
        result = await coordinator.process_query(
            query=request.query,
            session_id=session_id,
            intent=request.intent
        )

        # Extract answer from result
        answer = _extract_answer(result)

        # Extract sources if requested
        sources = []
        if request.include_sources:
            sources = _extract_sources(result)

        # Extract tool calls if requested
        tool_calls = []
        if request.include_tool_calls:
            tool_calls = _extract_tool_calls(result)

        # Extract metadata
        metadata = result.get("metadata", {})

        # Build response
        response = ChatResponse(
            answer=answer,
            query=request.query,
            session_id=session_id,
            intent=result.get("intent"),
            sources=sources,
            tool_calls=tool_calls,
            metadata=metadata
        )

        logger.info(
            "chat_request_completed",
            session_id=session_id,
            answer_length=len(answer),
            sources_count=len(sources),
            latency=metadata.get("latency_seconds")
        )

        return response

    except AegisRAGException as e:
        logger.error(
            "chat_request_failed_aegis_exception",
            session_id=session_id,
            error=str(e),
            details=e.details
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG system error: {e.message}"
        ) from e

    except Exception as e:
        logger.error(
            "chat_request_failed_unexpected",
            session_id=session_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error processing query: {str(e)}"
        ) from e


@router.get("/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str) -> ConversationHistoryResponse:
    """Retrieve conversation history for a session.

    Args:
        session_id: Session ID to retrieve history for

    Returns:
        ConversationHistoryResponse with message history

    Raises:
        HTTPException: If session not found or retrieval fails
    """
    logger.info("conversation_history_requested", session_id=session_id)

    try:
        # Get unified memory API
        memory_api = get_unified_memory_api()

        # Retrieve conversation history from memory
        # Note: UnifiedMemoryAPI uses namespace "conversation:{session_id}"
        history_key = f"conversation:{session_id}"

        # Try to retrieve from Redis (recent conversations)
        history_data = await memory_api.retrieve(
            key=history_key,
            namespace="memory"
        )

        messages = []
        if history_data:
            messages = history_data.get("messages", [])

        logger.info(
            "conversation_history_retrieved",
            session_id=session_id,
            message_count=len(messages)
        )

        return ConversationHistoryResponse(
            session_id=session_id,
            messages=messages,
            message_count=len(messages)
        )

    except Exception as e:
        logger.error(
            "conversation_history_retrieval_failed",
            session_id=session_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        ) from e


@router.delete("/history/{session_id}", response_model=SessionDeleteResponse)
async def delete_conversation_history(session_id: str) -> SessionDeleteResponse:
    """Delete conversation history for a session.

    Args:
        session_id: Session ID to delete

    Returns:
        SessionDeleteResponse with status

    Raises:
        HTTPException: If deletion fails
    """
    logger.info("conversation_history_delete_requested", session_id=session_id)

    try:
        # Get unified memory API
        memory_api = get_unified_memory_api()

        # Delete conversation history
        history_key = f"conversation:{session_id}"

        # Delete from Redis
        await memory_api.delete(
            key=history_key,
            namespace="memory"
        )

        logger.info("conversation_history_deleted", session_id=session_id)

        return SessionDeleteResponse(
            session_id=session_id,
            status="success",
            message=f"Conversation history for session '{session_id}' deleted successfully"
        )

    except Exception as e:
        logger.error(
            "conversation_history_deletion_failed",
            session_id=session_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation history: {str(e)}"
        ) from e


# Helper functions

def _extract_answer(result: dict[str, Any]) -> str:
    """Extract answer from coordinator result.

    Args:
        result: Result dictionary from CoordinatorAgent

    Returns:
        Answer string (or default message if not found)
    """
    # Try different possible locations for answer
    # 1. Check messages (LangGraph format)
    messages = result.get("messages", [])
    if messages:
        # Last message is typically the answer
        last_message = messages[-1]
        if isinstance(last_message, dict):
            return last_message.get("content", "No answer generated")
        return str(last_message)

    # 2. Check direct "answer" field
    if "answer" in result:
        return result["answer"]

    # 3. Check "response" field (alternative naming)
    if "response" in result:
        return result["response"]

    # 4. Fallback
    logger.warning("no_answer_found_in_result", result_keys=list(result.keys()))
    return "I'm sorry, I couldn't generate an answer. Please try rephrasing your question."


def _extract_sources(result: dict[str, Any]) -> list[SourceDocument]:
    """Extract source documents from coordinator result.

    Args:
        result: Result dictionary from CoordinatorAgent

    Returns:
        List of SourceDocument objects
    """
    sources: list[SourceDocument] = []

    # Get retrieved contexts
    contexts = result.get("retrieved_contexts", [])

    for ctx in contexts:
        if isinstance(ctx, dict):
            source = SourceDocument(
                text=ctx.get("text", ctx.get("content", ""))[:500],  # Limit to 500 chars
                title=ctx.get("title", ctx.get("source", "Unknown")),
                source=ctx.get("source", ctx.get("file_path", "Unknown")),
                score=ctx.get("score", ctx.get("relevance", None)),
                metadata=ctx.get("metadata", {})
            )
            sources.append(source)

    logger.debug("sources_extracted", count=len(sources))
    return sources[:5]  # Return top 5 sources


def _extract_tool_calls(result: dict[str, Any]) -> list[ToolCallInfo]:
    """Extract MCP tool call information from coordinator result.

    Args:
        result: Result dictionary from CoordinatorAgent

    Returns:
        List of ToolCallInfo objects
    """
    tool_calls: list[ToolCallInfo] = []

    # Check for tool calls in metadata
    metadata = result.get("metadata", {})
    tool_call_data = metadata.get("tool_calls", [])

    for call in tool_call_data:
        if isinstance(call, dict):
            tool_info = ToolCallInfo(
                tool_name=call.get("tool_name", "unknown"),
                server=call.get("server", "unknown"),
                arguments=call.get("arguments", {}),
                result=call.get("result"),
                duration_ms=call.get("duration_ms", 0.0),
                success=call.get("success", True),
                error=call.get("error")
            )
            tool_calls.append(tool_info)

    logger.debug("tool_calls_extracted", count=len(tool_calls))
    return tool_calls
