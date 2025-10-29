"""Chat API Endpoints for AEGIS RAG.

Sprint 10 Feature 10.1: FastAPI Chat Endpoints
Sprint 15 Feature 15.1: SSE Streaming Endpoint
Sprint 17 Feature 17.2: Conversation History Persistence

This module provides RESTful chat endpoints for the Gradio UI and React frontend.
It integrates the CoordinatorAgent for query processing and UnifiedMemoryAPI for session management.
Includes Server-Sent Events (SSE) streaming for real-time token-by-token responses.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.agents.coordinator import CoordinatorAgent
from src.components.memory import get_unified_memory_api
from src.core.exceptions import AegisRAGException
from src.models.profiling import ConversationSearchRequest, ConversationSearchResponse

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


# Sprint 17 Feature 17.2: Conversation persistence helpers


async def save_conversation_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
    intent: str | None = None,
    sources: list["SourceDocument"] | None = None,
) -> bool:
    """Save a conversation turn to Redis.

    Sprint 17 Feature 17.2: Conversation History Persistence

    Args:
        session_id: Session ID
        user_message: User's question
        assistant_message: Assistant's answer
        intent: Query intent (vector, graph, hybrid)
        sources: Source documents used

    Returns:
        True if saved successfully
    """
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        # Load existing conversation or create new one
        existing_conv = await redis_memory.retrieve(key=session_id, namespace="conversation")

        if existing_conv:
            # Extract value from Redis wrapper
            if isinstance(existing_conv, dict) and "value" in existing_conv:
                existing_conv = existing_conv["value"]

            # Append to existing conversation
            messages = existing_conv.get("messages", [])
            created_at = existing_conv.get("created_at")
        else:
            # New conversation
            messages = []
            created_at = datetime.now(timezone.utc).isoformat()

        # Add new messages
        messages.append(
            {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "intent": intent,
                "source_count": len(sources) if sources else 0,
            }
        )

        # Save updated conversation (7 days TTL)
        conversation_data = {
            "messages": messages,
            "created_at": created_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(messages),
        }

        success = await redis_memory.store(
            key=session_id,
            value=conversation_data,
            ttl_seconds=604800,  # 7 days
            namespace="conversation",
        )

        if success:
            logger.info(
                "conversation_saved",
                session_id=session_id,
                message_count=len(messages),
            )

        return success

    except Exception as e:
        logger.error("conversation_save_failed", session_id=session_id, error=str(e))
        return False


# Request/Response Models


class ChatRequest(BaseModel):
    """Chat request model."""

    query: str = Field(..., min_length=1, max_length=5000, description="User query")
    session_id: str | None = Field(
        default=None,
        description="Session ID for conversation history. Auto-generated if not provided.",
    )
    intent: str | None = Field(
        default=None, description="Optional intent override (graph, vector, hybrid)"
    )
    include_sources: bool = Field(default=True, description="Include source documents in response")
    include_tool_calls: bool = Field(
        default=False, description="Include MCP tool call information in response"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Was ist AEGIS RAG?",
                "session_id": "user-123-session",
                "include_sources": True,
                "include_tool_calls": False,
            }
        }
    )


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
        default_factory=list, description="Source documents used for answer generation"
    )
    tool_calls: list[ToolCallInfo] = Field(
        default_factory=list, description="MCP tool calls made during query processing"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata (latency, agent_path, etc.)"
    )

    model_config = ConfigDict(
        json_schema_extra={
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
                        "score": 0.92,
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
                        "error": None,
                    }
                ],
                "metadata": {
                    "latency_seconds": 1.23,
                    "agent_path": ["router", "vector_agent", "generator"],
                },
            }
        }
    )


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


class SessionInfo(BaseModel):
    """Session information."""

    session_id: str
    message_count: int
    last_activity: str | None = None
    created_at: str | None = None
    title: str | None = None  # Sprint 17 Feature 17.3: Auto-generated title


class SessionListResponse(BaseModel):
    """List of sessions response."""

    sessions: list[SessionInfo]
    total_count: int


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
        intent_override=request.intent,
    )

    try:
        # Get coordinator
        coordinator = get_coordinator()

        # Process query through multi-agent system
        result = await coordinator.process_query(
            query=request.query, session_id=session_id, intent=request.intent
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
            metadata=metadata,
        )

        logger.info(
            "chat_request_completed",
            session_id=session_id,
            answer_length=len(answer),
            sources_count=len(sources),
            latency=metadata.get("latency_seconds"),
        )

        # Sprint 17 Feature 17.2: Save conversation to Redis
        await save_conversation_turn(
            session_id=session_id,
            user_message=request.query,
            assistant_message=answer,
            intent=result.get("intent"),
            sources=sources,
        )

        return response

    except AegisRAGException as e:
        logger.error(
            "chat_request_failed_aegis_exception",
            session_id=session_id,
            error=str(e),
            details=e.details,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG system error: {e.message}",
        ) from e

    except Exception as e:
        logger.error("chat_request_failed_unexpected", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error processing query: {str(e)}",
        ) from e


@router.post("/stream", status_code=status.HTTP_200_OK)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream chat response using Server-Sent Events (SSE).

    Sprint 15 Feature 15.1: SSE Streaming Endpoint (ADR-020)

    This endpoint:
    1. Validates the query
    2. Generates/validates session_id
    3. Streams tokens and metadata from CoordinatorAgent in real-time
    4. Sends sources as they become available
    5. Returns SSE-formatted stream

    Args:
        request: ChatRequest with query and optional session_id

    Returns:
        StreamingResponse with text/event-stream media type

    SSE Message Format:
        data: {"type": "metadata", "session_id": "...", "timestamp": "..."}
        data: {"type": "token", "content": "Hello"}
        data: {"type": "source", "source": {...}}
        data: [DONE]
    """
    # Generate session_id if not provided
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(
        "chat_stream_request_received",
        query=request.query[:100],
        session_id=session_id,
        intent_override=request.intent,
    )

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate SSE-formatted stream of chat response.

        Sprint 17 Feature 17.2: Collect answer during streaming and save to Redis
        """
        # Sprint 17 Feature 17.2: Accumulate answer tokens and sources
        collected_answer = []
        collected_sources = []
        collected_intent = None

        try:
            # Send initial metadata
            yield _format_sse_message(
                {
                    "type": "metadata",
                    "session_id": session_id,
                    "timestamp": _get_iso_timestamp(),
                }
            )

            # Get coordinator
            coordinator = get_coordinator()

            # Check if coordinator has streaming method
            if hasattr(coordinator, "process_query_stream"):
                # Stream from CoordinatorAgent
                async for chunk in coordinator.process_query_stream(
                    query=request.query, session_id=session_id, intent=request.intent
                ):
                    # Sprint 17 Feature 17.2: Collect tokens and sources
                    if isinstance(chunk, dict):
                        if chunk.get("type") == "token" and "content" in chunk:
                            collected_answer.append(chunk["content"])
                        elif chunk.get("type") == "source" and "source" in chunk:
                            collected_sources.append(chunk["source"])
                        elif chunk.get("type") == "metadata" and "intent" in chunk.get("data", {}):
                            collected_intent = chunk["data"]["intent"]

                    yield _format_sse_message(chunk)
            else:
                # Fallback: Non-streaming mode (for backward compatibility)
                logger.warning(
                    "coordinator_streaming_not_available",
                    message="process_query_stream not implemented, falling back to non-streaming",
                )

                # Process query normally
                result = await coordinator.process_query(
                    query=request.query, session_id=session_id, intent=request.intent
                )

                # Extract answer and intent
                answer = _extract_answer(result)
                collected_intent = result.get("intent")

                # Send answer as tokens (simulate streaming)
                for token in answer.split():
                    collected_answer.append(token + " ")
                    yield _format_sse_message({"type": "token", "content": token + " "})

                # Send sources if available
                if request.include_sources:
                    sources = _extract_sources(result)
                    collected_sources = [
                        s.model_dump() if hasattr(s, "model_dump") else s for s in sources
                    ]
                    for source in sources:
                        yield _format_sse_message({"type": "source", "source": source.model_dump()})

            # Signal completion
            yield "data: [DONE]\n\n"

            logger.info("chat_stream_completed", session_id=session_id)

            # Sprint 17 Feature 17.2: Save conversation after streaming completes
            full_answer = "".join(collected_answer)
            if full_answer:
                await save_conversation_turn(
                    session_id=session_id,
                    user_message=request.query,
                    assistant_message=full_answer,
                    intent=collected_intent,
                    sources=collected_sources,
                )
                logger.info("conversation_saved_after_streaming", session_id=session_id)

        except AegisRAGException as e:
            logger.error(
                "chat_stream_failed_aegis_exception",
                session_id=session_id,
                error=str(e),
                details=e.details,
            )
            yield _format_sse_message(
                {"type": "error", "error": f"RAG system error: {e.message}", "code": "AEGIS_ERROR"}
            )

        except Exception as e:
            logger.error("chat_stream_failed_unexpected", session_id=session_id, error=str(e))
            yield _format_sse_message(
                {"type": "error", "error": f"Unexpected error: {str(e)}", "code": "INTERNAL_ERROR"}
            )

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",  # CORS for SSE
        },
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions() -> SessionListResponse:
    """List all active conversation sessions.

    Sprint 15 Feature 15.5: Session Management for History Sidebar
    Sprint 17 Feature 17.2: Implement proper session listing from Redis

    Returns:
        SessionListResponse with list of session information

    Raises:
        HTTPException: If listing fails
    """
    logger.info("session_list_requested")

    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        # Get Redis client for scanning
        redis_client = await redis_memory.client

        # Scan for conversation keys
        conversation_keys = []
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match="conversation:*", count=100)
            conversation_keys.extend(keys)
            if cursor == 0:
                break

        # Retrieve session info for each conversation
        sessions: list[SessionInfo] = []
        for key in conversation_keys:
            try:
                # Extract session_id from key (format: "conversation:{session_id}")
                session_id = key.split(":", 1)[1] if ":" in key else key

                # Retrieve conversation data
                conv_data = await redis_memory.retrieve(key=session_id, namespace="conversation")

                if conv_data:
                    # Extract value from Redis wrapper
                    if isinstance(conv_data, dict) and "value" in conv_data:
                        conv_data = conv_data["value"]

                    # Create SessionInfo (Sprint 17 Feature 17.3: Include title)
                    sessions.append(
                        SessionInfo(
                            session_id=session_id,
                            message_count=conv_data.get("message_count", 0),
                            last_activity=conv_data.get("updated_at"),
                            created_at=conv_data.get("created_at"),
                            title=conv_data.get("title"),  # Auto-generated or user-edited title
                        )
                    )
            except Exception as e:
                logger.warning("failed_to_retrieve_session", session_id=session_id, error=str(e))
                continue

        # Sort by last activity (most recent first)
        sessions.sort(key=lambda s: s.last_activity or "", reverse=True)

        logger.info("session_list_retrieved", count=len(sessions))

        return SessionListResponse(sessions=sessions, total_count=len(sessions))

    except Exception as e:
        logger.error("session_list_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        ) from e


@router.get("/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str) -> ConversationHistoryResponse:
    """Retrieve conversation history for a session.

    Sprint 17 Feature 17.2: Implement proper conversation history retrieval from Redis

    Args:
        session_id: Session ID to retrieve history for

    Returns:
        ConversationHistoryResponse with message history

    Raises:
        HTTPException: If session not found or retrieval fails
    """
    logger.info("conversation_history_requested", session_id=session_id)

    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        # Retrieve conversation from Redis
        history_data = await redis_memory.retrieve(key=session_id, namespace="conversation")

        messages = []
        if history_data:
            # Extract value from Redis wrapper
            if isinstance(history_data, dict) and "value" in history_data:
                history_data = history_data["value"]

            messages = history_data.get("messages", [])
        else:
            # Session not found
            logger.warning("conversation_history_not_found", session_id=session_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation history not found for session: {session_id}",
            )

        logger.info(
            "conversation_history_retrieved", session_id=session_id, message_count=len(messages)
        )

        return ConversationHistoryResponse(
            session_id=session_id, messages=messages, message_count=len(messages)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("conversation_history_retrieval_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation history: {str(e)}",
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
        await memory_api.delete(key=history_key, namespace="memory")

        logger.info("conversation_history_deleted", session_id=session_id)

        return SessionDeleteResponse(
            session_id=session_id,
            status="success",
            message=f"Conversation history for session '{session_id}' deleted successfully",
        )

    except Exception as e:
        logger.error("conversation_history_deletion_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation history: {str(e)}",
        ) from e


# Sprint 17 Feature 17.3: Auto-Generated Conversation Titles


class TitleGenerationRequest(BaseModel):
    """Request model for title generation."""

    session_id: str = Field(..., description="Session ID to generate title for")


class TitleResponse(BaseModel):
    """Response model for title generation."""

    session_id: str = Field(..., description="Session ID")
    title: str = Field(..., description="Generated conversation title")
    generated_at: str = Field(..., description="Timestamp when title was generated")


class UpdateTitleRequest(BaseModel):
    """Request model for updating conversation title."""

    title: str = Field(..., min_length=1, max_length=100, description="New conversation title")


@router.post("/sessions/{session_id}/generate-title", response_model=TitleResponse)
async def generate_conversation_title(session_id: str) -> TitleResponse:
    """Auto-generate concise conversation title from first Q&A.

    Sprint 17 Feature 17.3: Auto-Generated Conversation Titles

    Uses Ollama LLM to generate a 3-5 word title from the first question-answer exchange
    in a conversation. The title is stored in Redis conversation metadata.

    Args:
        session_id: Session ID to generate title for

    Returns:
        TitleResponse with generated title

    Raises:
        HTTPException: If session not found or title generation fails
    """
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        # Load conversation
        conversation_data = await redis_memory.retrieve(key=session_id, namespace="conversation")

        if not conversation_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{session_id}' not found",
            )

        # Extract value from Redis wrapper
        if isinstance(conversation_data, dict) and "value" in conversation_data:
            conversation_data = conversation_data["value"]

        messages = conversation_data.get("messages", [])

        # Need at least 2 messages (user + assistant)
        if len(messages) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation must have at least one Q&A exchange to generate title",
            )

        # Get first Q&A pair
        first_user_msg = None
        first_assistant_msg = None

        for msg in messages[:4]:  # Check first 4 messages to find the first Q&A pair
            if msg.get("role") == "user" and not first_user_msg:
                first_user_msg = msg.get("content", "")
            elif msg.get("role") == "assistant" and not first_assistant_msg and first_user_msg:
                first_assistant_msg = msg.get("content", "")
                break

        if not first_user_msg or not first_assistant_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not find first Q&A pair in conversation",
            )

        # Generate title using Ollama
        coordinator = get_coordinator()

        # Truncate messages to avoid token limits
        user_msg_short = first_user_msg[:200]
        assistant_msg_short = first_assistant_msg[:300]

        title_prompt = f"""Generate a very concise 3-5 word title for this conversation.
The title should capture the main topic.
Only return the title, nothing else.

Question: {user_msg_short}
Answer: {assistant_msg_short}

Title:"""

        try:
            # Use coordinator's LLM to generate title
            title_result = await coordinator.llm.ainvoke(
                title_prompt, temperature=0.3, max_tokens=20
            )

            # Extract title from result
            if hasattr(title_result, "content"):
                generated_title = title_result.content.strip()
            elif isinstance(title_result, str):
                generated_title = title_result.strip()
            else:
                generated_title = str(title_result).strip()

            # Clean up title (remove quotes, extra whitespace)
            generated_title = generated_title.strip("\"'").strip()

            # Fallback if title is empty or too long
            if not generated_title or len(generated_title) > 100:
                generated_title = user_msg_short[:50] + "..."

        except Exception as llm_error:
            logger.warning(
                "title_generation_failed_fallback_to_question",
                session_id=session_id,
                error=str(llm_error),
            )
            # Fallback: Use first few words of question
            generated_title = " ".join(first_user_msg.split()[:5])

        # Save title to conversation metadata
        conversation_data["title"] = generated_title
        conversation_data["title_generated_at"] = _get_iso_timestamp()

        await redis_memory.store(
            key=session_id,
            value=conversation_data,
            ttl_seconds=604800,  # 7 days
            namespace="conversation",
        )

        logger.info("conversation_title_generated", session_id=session_id, title=generated_title)

        return TitleResponse(
            session_id=session_id, title=generated_title, generated_at=_get_iso_timestamp()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("title_generation_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate title: {str(e)}",
        ) from e


@router.patch("/sessions/{session_id}", response_model=TitleResponse)
async def update_conversation_title(session_id: str, request: UpdateTitleRequest) -> TitleResponse:
    """Update conversation title manually.

    Sprint 17 Feature 17.3: Auto-Generated Conversation Titles

    Allows users to manually edit conversation titles. The new title is stored
    in Redis conversation metadata.

    Args:
        session_id: Session ID to update
        request: UpdateTitleRequest with new title

    Returns:
        TitleResponse with updated title

    Raises:
        HTTPException: If session not found or update fails
    """
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        # Load conversation
        conversation_data = await redis_memory.retrieve(key=session_id, namespace="conversation")

        if not conversation_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{session_id}' not found",
            )

        # Extract value from Redis wrapper
        if isinstance(conversation_data, dict) and "value" in conversation_data:
            conversation_data = conversation_data["value"]

        # Update title
        conversation_data["title"] = request.title
        conversation_data["title_updated_at"] = _get_iso_timestamp()

        # Save back to Redis
        await redis_memory.store(
            key=session_id,
            value=conversation_data,
            ttl_seconds=604800,  # 7 days
            namespace="conversation",
        )

        logger.info("conversation_title_updated", session_id=session_id, new_title=request.title)

        return TitleResponse(
            session_id=session_id, title=request.title, generated_at=_get_iso_timestamp()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("title_update_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update title: {str(e)}",
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
    # 1. Check direct "answer" field first (most reliable)
    if "answer" in result:
        return result["answer"]

    # 2. Check messages (LangGraph format)
    messages = result.get("messages", [])
    if messages:
        # Last message is typically the answer
        last_message = messages[-1]
        if isinstance(last_message, dict):
            return last_message.get("content", "No answer generated")
        # Handle LangChain message objects
        if hasattr(last_message, "content"):
            return last_message.content
        return str(last_message)

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
                metadata=ctx.get("metadata", {}),
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
                error=call.get("error"),
            )
            tool_calls.append(tool_info)

    logger.debug("tool_calls_extracted", count=len(tool_calls))
    return tool_calls


def _format_sse_message(data: dict[str, Any]) -> str:
    """Format data as Server-Sent Events (SSE) message.

    SSE Format:
        data: {json}\n\n

    Args:
        data: Dictionary to send as SSE message

    Returns:
        SSE-formatted string
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_iso_timestamp() -> str:
    """Get current timestamp in ISO 8601 format.

    Returns:
        ISO 8601 timestamp string
    """
    return datetime.now(timezone.utc).isoformat()


# Sprint 17 Feature 17.4 Phase 1: Conversation Archiving Pipeline


@router.post("/sessions/{session_id}/archive", status_code=status.HTTP_200_OK)
async def archive_conversation(session_id: str) -> dict[str, Any]:
    """Archive a conversation to Qdrant for semantic search.

    Sprint 17 Feature 17.4 Phase 1: Manual Archive Trigger

    This endpoint:
    1. Loads conversation from Redis
    2. Generates embedding from full conversation text
    3. Stores in Qdrant collection (archived_conversations)
    4. Removes from Redis (conversation is now archived)

    Args:
        session_id: Session ID to archive

    Returns:
        Archive confirmation with Qdrant point ID

    Raises:
        HTTPException: If archiving fails
    """
    logger.info("archive_conversation_requested", session_id=session_id)

    try:
        from src.components.profiling import get_conversation_archiver
        from src.models.profiling import ArchiveConversationResponse

        archiver = get_conversation_archiver()

        # Archive conversation
        point_id = await archiver.archive_conversation(
            session_id=session_id,
            user_id="default_user",  # TODO: Extract from auth context
            reason="manual_archive",
        )

        response = ArchiveConversationResponse(
            session_id=session_id,
            status="success",
            message=f"Conversation '{session_id}' archived successfully",
            archived_at=_get_iso_timestamp(),
            qdrant_point_id=point_id,
        )

        logger.info(
            "conversation_archived_successfully",
            session_id=session_id,
            point_id=point_id,
        )

        return response.model_dump()

    except Exception as e:
        logger.error("archive_conversation_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive conversation: {str(e)}",
        ) from e


@router.post("/search", status_code=status.HTTP_200_OK)
async def search_archived_conversations(
    request: ConversationSearchRequest,
) -> ConversationSearchResponse:
    """Search archived conversations using semantic similarity.

    Sprint 17 Feature 17.4 Phase 1: Semantic Conversation Search

    This endpoint:
    1. Generates embedding from search query
    2. Searches Qdrant archived_conversations collection
    3. Filters to current user only
    4. Returns conversation snippets with relevance scores

    Args:
        request: ConversationSearchRequest with query and filters

    Returns:
        ConversationSearchResponse with matching conversations

    Raises:
        HTTPException: If search fails
    """
    # Validate request
    if not isinstance(request, ConversationSearchRequest):
        request = ConversationSearchRequest(**request)

    logger.info(
        "search_archived_conversations_requested",
        query=request.query[:100],
        limit=request.limit,
    )

    try:
        from src.components.profiling import get_conversation_archiver

        archiver = get_conversation_archiver()

        # Search archived conversations
        results = await archiver.search_archived_conversations(
            request=request,
            user_id="default_user",  # TODO: Extract from auth context
        )

        logger.info(
            "search_archived_conversations_completed",
            query=request.query[:100],
            results_count=results.total_count,
        )

        return results

    except Exception as e:
        logger.error("search_archived_conversations_failed", query=request.query, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search archived conversations: {str(e)}",
        ) from e
