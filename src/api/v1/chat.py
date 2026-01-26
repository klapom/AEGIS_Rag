"""Chat API Endpoints for AEGIS RAG.

Sprint 10 Feature 10.1: FastAPI Chat Endpoints
Sprint 15 Feature 15.1: SSE Streaming Endpoint
Sprint 17 Feature 17.2: Conversation History Persistence
Sprint 48 Feature 48.4: Chat Stream API Enhancement (8 SP)
Sprint 48 Feature 48.5: Phase Events Redis Persistence (5 SP)
Sprint 120 Feature 120.14: SSE Tool Events in Chat Stream

This module provides RESTful chat endpoints for the Gradio UI and React frontend.
It integrates the CoordinatorAgent for query processing and UnifiedMemoryAPI for
session management. Includes Server-Sent Events (SSE) streaming for real-time
token-by-token responses with phase events.

Sprint 120 Feature 120.14: Tool Event Streaming
When tool execution occurs (via LangGraph tools_node), the SSE stream emits granular
tool-specific events in addition to the standard phase_event. This enables the
frontend to display tool execution progress in real-time.

Tool Event Types:
    - tool_use: Emitted when a tool starts executing (IN_PROGRESS status)
    - tool_result: Emitted when a tool completes successfully (COMPLETED status)
    - tool_error: Emitted when a tool execution fails (FAILED status)

Event Flow:
    1. tools_node emits PhaseEvent(TOOL_EXECUTION, IN_PROGRESS) → tool_use event
    2. tools_node executes tool via MCP
    3. tools_node emits PhaseEvent(TOOL_EXECUTION, COMPLETED/FAILED) → tool_result/
       tool_error event

Frontend Integration:
    The frontend's useStreamChat hook receives these events and updates the tool
    execution state, displaying progress bars, results, and errors in real-time
    during chat conversations.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.agents.coordinator import CoordinatorAgent
from src.agents.followup_generator import generate_followup_questions
from src.agents.reasoning_data import ReasoningData
from src.api.models.multi_turn import MultiTurnRequest, MultiTurnResponse
from src.api.v1.title_generator import generate_conversation_title
from src.components.memory import get_unified_memory_api
from src.core.exceptions import AegisRAGException
from src.models.phase_event import PhaseEvent
from src.models.profiling import ConversationSearchRequest, ConversationSearchResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Sprint 48 Feature 48.4: Timeout Constants
# Sprint 113: Increased timeouts based on LLM trace analysis:
#   - Entity Expansion: ~8.5s (Neo4j bottleneck)
#   - LLM Generation: 60-90s (Nemotron3 Nano on DGX Spark)
#   - Buffer for streaming: 30s
REQUEST_TIMEOUT_SECONDS = 180  # Total request timeout (was 90s)
PHASE_TIMEOUT_SECONDS = 30  # Individual phase timeout (not LLM)
LLM_TIMEOUT_SECONDS = 120  # LLM generation timeout (was 60s)

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
    follow_up_questions: list[str] | None = None,
    title: str | None = None,
) -> bool:
    """Save a conversation turn to Redis.

    Sprint 17 Feature 17.2: Conversation History Persistence
    Sprint 35 Feature 35.3: Follow-up Questions Redis Fix (TD-043)
    Sprint 35 Feature 35.4: Auto-Generated Conversation Titles

    Args:
        session_id: Session ID
        user_message: User's question
        assistant_message: Assistant's answer
        intent: Query intent (vector, graph, hybrid)
        sources: Source documents used
        follow_up_questions: Generated follow-up questions (3-5)
        title: Auto-generated or user-edited title (only for first message)

    Returns:
        True if saved successfully
    """
    try:
        logger.info(
            "save_conversation_turn_start",
            session_id=session_id,
            sources_count=len(sources) if sources else 0,
        )
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        logger.info("redis_memory_obtained", session_id=session_id)

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
            created_at = datetime.now(UTC).isoformat()

        # Add new messages
        messages.append(
            {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        # Serialize sources for storage (ensure they're dicts)
        serialized_sources = []
        if sources:
            for source in sources:
                if isinstance(source, dict):
                    # Already a dict, use as-is
                    serialized_sources.append(source)
                elif hasattr(source, "model_dump"):
                    # Pydantic v2
                    serialized_sources.append(source.model_dump())
                elif hasattr(source, "dict"):
                    # Pydantic v1
                    serialized_sources.append(source.dict())
                else:
                    # Fallback: try to convert to dict
                    serialized_sources.append(dict(source) if hasattr(source, "__iter__") else {})

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.now(UTC).isoformat(),
                "intent": intent,
                "source_count": len(sources) if sources else 0,
                "sources": serialized_sources,  # Store full sources for follow-up generation
            }
        )

        # Save updated conversation (7 days TTL)
        # Sprint 35 Feature 35.3: Include follow-up questions in conversation storage
        # Sprint 35 Feature 35.4: Include title in conversation storage
        conversation_data = {
            "messages": messages,
            "created_at": created_at,
            "updated_at": datetime.now(UTC).isoformat(),
            "message_count": len(messages),
            "follow_up_questions": follow_up_questions or [],
            "title": title if title else (existing_conv.get("title") if existing_conv else None),
        }

        logger.info(
            "storing_conversation_to_redis",
            session_id=session_id,
            message_count=len(messages),
            sources_in_last_msg=len(serialized_sources),
            follow_up_count=len(follow_up_questions) if follow_up_questions else 0,
        )

        success = await redis_memory.store(
            key=session_id,
            value=conversation_data,
            ttl_seconds=604800,  # 7 days
            namespace="conversation",
        )

        if success:
            logger.info(
                "conversation_saved_success",
                session_id=session_id,
                message_count=len(messages),
            )
        else:
            logger.error("conversation_save_failed_redis_returned_false", session_id=session_id)

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
    namespaces: list[str] | None = Field(
        default=None,
        description='Namespaces to search in. Defaults to ["default", "general"] if not specified.',
    )
    response_format: str = Field(
        default="natural",
        description='Response format: "natural" (markdown with citations) or "structured" (JSON)',
        pattern="^(natural|structured)$",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Was ist AEGIS RAG?",
                "session_id": "user-123-session",
                "include_sources": True,
                "include_tool_calls": False,
                "namespaces": ["default", "general"],
                "response_format": "natural",
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
    """list of sessions response."""

    sessions: list[SessionInfo]
    total_count: int


# API Endpoints


@router.post("/", status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest) -> ChatResponse | dict[str, Any]:
    """Process a chat query through the RAG system.

    Sprint 63 Feature 63.4: Structured Output Formatting

    This endpoint:
    1. Validates the query
    2. Generates/validates session_id
    3. Processes query through CoordinatorAgent
    4. Extracts answer and sources
    5. Returns response in requested format (natural or structured)

    Args:
        request: ChatRequest with query and optional session_id

    Returns:
        ChatResponse (natural format) or StructuredChatResponse (structured format)

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
        response_format=request.response_format,
    )

    try:
        # Track start time for latency calculation
        import time

        start_time = time.time()

        # Get coordinator
        coordinator = get_coordinator()

        # Process query through multi-agent system
        result = await coordinator.process_query(
            query=request.query,
            session_id=session_id,
            intent=request.intent,
            namespaces=request.namespaces,
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

        logger.info(
            "chat_request_completed",
            session_id=session_id,
            answer_length=len(answer),
            sources_count=len(sources),
            latency=metadata.get("latency_seconds"),
        )

        # Sprint 17 Feature 17.2: Save conversation to Redis
        # Sprint 35 Feature 35.3: Generate and store follow-up questions
        # Sprint 35 Feature 35.4: Generate title for first Q&A exchange
        # Sprint 65 Feature 65.1: Follow-up questions are generated asynchronously
        # Coordinator already triggered background task via _generate_followup_async()
        # Frontend polls GET /sessions/{session_id}/followup-questions after answer
        follow_up_questions = []  # Empty - async generation in background

        # Sprint 35 Feature 35.4: Check if this is first message and generate title
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        existing_conv = await redis_memory.retrieve(key=session_id, namespace="conversation")

        # Generate title only for first Q&A exchange
        title = None
        if not existing_conv or (
            isinstance(existing_conv, dict)
            and existing_conv.get("value", {}).get("message_count", 0) == 0
        ):
            title = await generate_conversation_title(
                query=request.query,
                answer=answer,
            )
            logger.info("title_generated_for_first_message", session_id=session_id, title=title)

        save_success = await save_conversation_turn(
            session_id=session_id,
            user_message=request.query,
            assistant_message=answer,
            intent=result.get("intent"),
            sources=sources,
            follow_up_questions=follow_up_questions,
            title=title,
        )

        if not save_success:
            logger.warning(
                "conversation_save_failed_nonstreaming",
                session_id=session_id,
                message="save_conversation_turn returned False",
            )

        # Sprint 63 Feature 63.4: Return structured format if requested
        if request.response_format == "structured":
            from src.api.services.response_formatter import format_chat_response_structured

            structured_response = format_chat_response_structured(
                query=request.query,
                answer=answer,
                sources=sources,
                metadata=metadata,
                session_id=session_id,
                followup_questions=follow_up_questions,
                start_time=start_time,
            )
            return structured_response.model_dump()

        # Build natural format response (default)
        response = ChatResponse(
            answer=answer,
            query=request.query,
            session_id=session_id,
            intent=result.get("intent"),
            sources=sources,
            tool_calls=tool_calls,
            metadata=metadata,
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
    Sprint 48 Feature 48.4: Chat Stream API Enhancement (8 SP)

    This endpoint:
    1. Validates the query
    2. Generates/validates session_id
    3. Streams phase events and tokens from CoordinatorAgent in real-time
    4. Handles timeouts and cancellation gracefully
    5. Returns SSE-formatted stream

    Args:
        request: ChatRequest with query and optional session_id

    Returns:
        StreamingResponse with text/event-stream media type

    SSE Message Format:
        data: {"type": "metadata", "session_id": "...", "timestamp": "..."}
        data: {"type": "phase_event", "data": {...}}
        data: {"type": "answer_chunk", "data": {"answer": "...", "citations": [...]}}
        data: {"type": "reasoning_complete", "data": {"phase_events": [...]}}
        data: {"type": "error", "error": "...", "code": "TIMEOUT"}
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
        Sprint 48 Feature 48.4: Phase events streaming with timeout handling
        Sprint 48 Feature 48.5: Phase events persistence
        Sprint 52: Real-time phase events via LangGraph custom stream
        """
        # Accumulate data for persistence
        reasoning_data = ReasoningData()
        collected_answer = []
        collected_sources = []
        collected_intent = None

        # Sprint 52: Track emitted phases to avoid duplicates
        emitted_phases: set[str] = set()

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

            # Sprint 48 Feature 48.4: Global request timeout (90s)
            # Sprint 52: Direct iteration - phase events now come through LangGraph stream
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                async for event in coordinator.process_query_stream(
                    query=request.query,
                    session_id=session_id,
                    intent=request.intent,
                    namespaces=request.namespaces,
                ):
                    # Sprint 52: Handle PhaseEvent objects directly from LangGraph custom stream
                    if isinstance(event, PhaseEvent):
                        event_key = f"{event.phase_type.value}_{event.status.value}"
                        if event_key not in emitted_phases:
                            emitted_phases.add(event_key)
                            reasoning_data.add_phase_event(event)
                            yield _format_sse_message(
                                {
                                    "type": "phase_event",
                                    "data": event.model_dump(mode="json"),
                                }
                            )

                            # Sprint 120 Feature 120.14: Emit tool events
                            from src.models.phase_event import PhaseType, PhaseStatus

                            if event.phase_type == PhaseType.TOOL_EXECUTION:
                                try:
                                    tool_name = event.metadata.get(
                                        "tool_name"
                                    ) or event.metadata.get("tool_action", "unknown")
                                    execution_id = f"{tool_name}_{event.start_time.isoformat()}"
                                    timestamp = event.start_time.isoformat()

                                    if event.status == PhaseStatus.IN_PROGRESS:
                                        # Emit tool_use event
                                        yield _format_sse_message(
                                            {
                                                "type": "tool_use",
                                                "data": {
                                                    "tool": tool_name,
                                                    "server": "mcp",
                                                    "parameters": event.metadata.get(
                                                        "parameters", {}
                                                    ),
                                                    "execution_id": execution_id,
                                                    "timestamp": timestamp,
                                                },
                                            }
                                        )
                                        logger.debug(
                                            "tool_use_event_emitted",
                                            tool=tool_name,
                                            execution_id=execution_id,
                                        )

                                    elif event.status == PhaseStatus.COMPLETED:
                                        # Emit tool_result event
                                        yield _format_sse_message(
                                            {
                                                "type": "tool_result",
                                                "data": {
                                                    "tool": tool_name,
                                                    "server": "mcp",
                                                    "result": event.metadata.get(
                                                        "result_preview", ""
                                                    ),
                                                    "success": True,
                                                    "duration_ms": event.duration_ms,
                                                    "execution_id": execution_id,
                                                    "timestamp": (
                                                        event.end_time.isoformat()
                                                        if event.end_time
                                                        else timestamp
                                                    ),
                                                },
                                            }
                                        )
                                        logger.debug(
                                            "tool_result_event_emitted",
                                            tool=tool_name,
                                            execution_id=execution_id,
                                            duration_ms=event.duration_ms,
                                        )

                                    elif event.status == PhaseStatus.FAILED:
                                        # Emit tool_error event
                                        yield _format_sse_message(
                                            {
                                                "type": "tool_error",
                                                "data": {
                                                    "tool": tool_name,
                                                    "error": event.error or "Tool execution failed",
                                                    "details": event.metadata.get(
                                                        "error_details", ""
                                                    ),
                                                    "execution_id": execution_id,
                                                    "timestamp": (
                                                        event.end_time.isoformat()
                                                        if event.end_time
                                                        else timestamp
                                                    ),
                                                },
                                            }
                                        )
                                        logger.debug(
                                            "tool_error_event_emitted",
                                            tool=tool_name,
                                            execution_id=execution_id,
                                            error=event.error,
                                        )

                                except Exception as e:
                                    logger.warning(
                                        "tool_event_emission_failed",
                                        error=str(e),
                                        event_type=event.status.value,
                                    )
                                    # Continue with normal phase_event emission

                        continue

                    # Handle dict events (backward compatibility)
                    if isinstance(event, dict):
                        event_type = event.get("type")

                        # Sprint 48 Feature 48.5: Accumulate phase events for persistence
                        if event_type == "phase_event":
                            phase_event = PhaseEvent(**event["data"])
                            event_key = f"{phase_event.phase_type.value}_{phase_event.status.value}"
                            if event_key not in emitted_phases:
                                emitted_phases.add(event_key)
                                reasoning_data.add_phase_event(phase_event)
                                yield _format_sse_message(event)

                                # Sprint 120 Feature 120.14: Emit tool events
                                from src.models.phase_event import PhaseType, PhaseStatus

                                if phase_event.phase_type == PhaseType.TOOL_EXECUTION:
                                    try:
                                        tool_name = phase_event.metadata.get(
                                            "tool_name"
                                        ) or phase_event.metadata.get("tool_action", "unknown")
                                        execution_id = (
                                            f"{tool_name}_{phase_event.start_time.isoformat()}"
                                        )
                                        timestamp = phase_event.start_time.isoformat()

                                        if phase_event.status == PhaseStatus.IN_PROGRESS:
                                            # Emit tool_use event
                                            yield _format_sse_message(
                                                {
                                                    "type": "tool_use",
                                                    "data": {
                                                        "tool": tool_name,
                                                        "server": "mcp",
                                                        "parameters": phase_event.metadata.get(
                                                            "parameters", {}
                                                        ),
                                                        "execution_id": execution_id,
                                                        "timestamp": timestamp,
                                                    },
                                                }
                                            )
                                            logger.debug(
                                                "tool_use_event_emitted_dict",
                                                tool=tool_name,
                                                execution_id=execution_id,
                                            )

                                        elif phase_event.status == PhaseStatus.COMPLETED:
                                            # Emit tool_result event
                                            yield _format_sse_message(
                                                {
                                                    "type": "tool_result",
                                                    "data": {
                                                        "tool": tool_name,
                                                        "server": "mcp",
                                                        "result": phase_event.metadata.get(
                                                            "result_preview", ""
                                                        ),
                                                        "success": True,
                                                        "duration_ms": phase_event.duration_ms,
                                                        "execution_id": execution_id,
                                                        "timestamp": (
                                                            phase_event.end_time.isoformat()
                                                            if phase_event.end_time
                                                            else timestamp
                                                        ),
                                                    },
                                                }
                                            )
                                            logger.debug(
                                                "tool_result_event_emitted_dict",
                                                tool=tool_name,
                                                execution_id=execution_id,
                                                duration_ms=phase_event.duration_ms,
                                            )

                                        elif phase_event.status == PhaseStatus.FAILED:
                                            # Emit tool_error event
                                            yield _format_sse_message(
                                                {
                                                    "type": "tool_error",
                                                    "data": {
                                                        "tool": tool_name,
                                                        "error": phase_event.error
                                                        or "Tool execution failed",
                                                        "details": phase_event.metadata.get(
                                                            "error_details", ""
                                                        ),
                                                        "execution_id": execution_id,
                                                        "timestamp": (
                                                            phase_event.end_time.isoformat()
                                                            if phase_event.end_time
                                                            else timestamp
                                                        ),
                                                    },
                                                }
                                            )
                                            logger.debug(
                                                "tool_error_event_emitted_dict",
                                                tool=tool_name,
                                                execution_id=execution_id,
                                                error=phase_event.error,
                                            )

                                    except Exception as e:
                                        logger.warning(
                                            "tool_event_emission_failed_dict",
                                            error=str(e),
                                            event_type=phase_event.status.value,
                                        )
                                        # Continue with normal phase_event emission

                            continue

                        # Sprint 52: Stream tokens to UI in real-time
                        elif event_type == "token":
                            token_data = event.get("data", {})
                            if "content" in token_data:
                                token_content = token_data["content"]
                                collected_answer.append(token_content)
                                # Stream token to frontend immediately
                                yield _format_sse_message(event)
                            continue

                        # Sprint 52: Stream citation map before tokens
                        elif event_type == "citation_map":
                            # Forward citation map to frontend
                            yield _format_sse_message(event)
                            continue

                        # Collect answer chunks (backward compatibility)
                        elif event_type == "answer_chunk":
                            answer_data = event.get("data", {})
                            if "answer" in answer_data:
                                collected_answer.append(answer_data["answer"])
                            if "intent" in answer_data:
                                collected_intent = answer_data["intent"]

                        # Collect sources
                        elif event_type == "source":
                            collected_sources.append(event.get("source", {}))

                        # Sprint 52 Fix: Handle answer event from coordinator
                        # Coordinator yields {"answer": ..., "citation_map": ..., "metadata": ...}
                        # without a "type" field, so we need to wrap it as answer_chunk
                        if event_type is None and "answer" in event:
                            # This is the final answer from coordinator
                            # Don't append to collected_answer if we streamed tokens
                            # (answer is already collected from tokens)
                            if not collected_answer:
                                collected_answer.append(event.get("answer", ""))
                            if "intent" in event:
                                collected_intent = event["intent"]
                            # Wrap as answer_chunk for frontend (contains metadata)
                            yield _format_sse_message(
                                {
                                    "type": "answer_chunk",
                                    "data": event,
                                }
                            )
                            continue

                        # Stream event to client
                        yield _format_sse_message(event)

            # Signal completion
            yield "data: [DONE]\n\n"

            logger.info("chat_stream_completed", session_id=session_id)

        except TimeoutError:
            logger.error(
                "chat_stream_timeout",
                session_id=session_id,
                timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            )
            yield _format_sse_message(
                {
                    "type": "error",
                    "error": f"Request timed out after {REQUEST_TIMEOUT_SECONDS} seconds",
                    "code": "TIMEOUT",
                    "recoverable": True,
                }
            )

        except asyncio.CancelledError:
            logger.info("chat_stream_cancelled", session_id=session_id)
            yield _format_sse_message(
                {
                    "type": "cancelled",
                    "message": "Request cancelled by user",
                }
            )
            raise  # Re-raise to ensure proper cleanup

        except AegisRAGException as e:
            logger.error(
                "chat_stream_failed_aegis_exception",
                session_id=session_id,
                error=str(e),
                details=e.details,
            )
            yield _format_sse_message(
                {
                    "type": "error",
                    "error": f"RAG system error: {e.message}",
                    "code": "AEGIS_ERROR",
                    "recoverable": False,
                }
            )

        except Exception as e:
            logger.error("chat_stream_failed_unexpected", session_id=session_id, error=str(e))
            yield _format_sse_message(
                {
                    "type": "error",
                    "error": f"Unexpected error: {str(e)}",
                    "code": "INTERNAL_ERROR",
                    "recoverable": False,
                }
            )

        finally:
            # Sprint 48 Feature 48.5: Save phase events to Redis after stream completes
            if reasoning_data.phase_events:
                try:
                    from src.components.memory import get_redis_memory

                    redis_memory = get_redis_memory()
                    await redis_memory.save_phase_events(
                        conversation_id=session_id,
                        phase_events=reasoning_data.phase_events,
                    )
                    logger.info(
                        "phase_events_saved_to_redis",
                        session_id=session_id,
                        event_count=len(reasoning_data.phase_events),
                    )
                except Exception as e:
                    logger.error(
                        "phase_events_save_failed",
                        session_id=session_id,
                        error=str(e),
                    )

            # Sprint 17 Feature 17.2: Save conversation after streaming completes
            full_answer = "".join(collected_answer)
            if full_answer:
                # Sprint 65 Feature 65.1: Follow-up questions generated asynchronously
                # Coordinator already triggered background task via _generate_followup_async()
                # Frontend polls GET /sessions/{session_id}/followup-questions after answer
                follow_up_questions = []  # Empty - async generation in background

                # Sprint 35 Feature 35.4: Check if this is first message and generate title
                from src.components.memory import get_redis_memory

                redis_memory = get_redis_memory()
                existing_conv = await redis_memory.retrieve(
                    key=session_id, namespace="conversation"
                )

                # Generate title only for first Q&A exchange
                title = None
                if not existing_conv or (
                    isinstance(existing_conv, dict)
                    and existing_conv.get("value", {}).get("message_count", 0) == 0
                ):
                    title = await generate_conversation_title(
                        query=request.query,
                        answer=full_answer,
                    )
                    logger.info(
                        "title_generated_for_first_message", session_id=session_id, title=title
                    )

                await save_conversation_turn(
                    session_id=session_id,
                    user_message=request.query,
                    assistant_message=full_answer,
                    intent=collected_intent,
                    sources=collected_sources,
                    follow_up_questions=follow_up_questions,
                    title=title,
                )
                logger.info(
                    "conversation_saved_after_streaming",
                    session_id=session_id,
                    follow_up_count=len(follow_up_questions) if follow_up_questions else 0,
                    title_generated=bool(title),
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
async def list_sessions(limit: int = 50, offset: int = 0) -> SessionListResponse:
    """list active conversation sessions with pagination.

    Sprint 15 Feature 15.5: Session Management for History Sidebar
    Sprint 17 Feature 17.2: Implement proper session listing from Redis
    Sprint 65 Feature 65.3: Added pagination to avoid timeout with >100 conversations

    Args:
        limit: Maximum number of sessions to return (default: 50, max: 100)
        offset: Number of sessions to skip (default: 0)

    Returns:
        SessionListResponse with list of session information (paginated)

    Raises:
        HTTPException: If listing fails
    """
    # Sprint 65: Validate pagination parameters
    limit = min(max(1, limit), 100)  # Clamp between 1 and 100
    offset = max(0, offset)

    logger.info("session_list_requested", limit=limit, offset=offset)

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

        # Sprint 65 Feature 65.3: Apply pagination
        total_count = len(sessions)
        paginated_sessions = sessions[offset : offset + limit]

        logger.info(
            "session_list_retrieved",
            total_count=total_count,
            returned_count=len(paginated_sessions),
            offset=offset,
            limit=limit,
        )

        return SessionListResponse(sessions=paginated_sessions, total_count=total_count)

    except Exception as e:
        logger.error("session_list_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        ) from e


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str) -> SessionInfo:
    """Get session information including title.

    Sprint 35 Feature 35.4: Get session info endpoint for title display

    Args:
        session_id: Session ID to retrieve info for

    Returns:
        SessionInfo with title, message count, and timestamps

    Raises:
        HTTPException: If session not found or retrieval fails
    """
    logger.info("session_info_requested", session_id=session_id)

    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        # Retrieve conversation from Redis
        conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found",
            )

        # Extract value from Redis wrapper
        if isinstance(conversation, dict) and "value" in conversation:
            conversation = conversation["value"]

        logger.info("session_info_retrieved", session_id=session_id)

        return SessionInfo(
            session_id=session_id,
            message_count=conversation.get("message_count", 0),
            last_activity=conversation.get("updated_at"),
            created_at=conversation.get("created_at"),
            title=conversation.get("title"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("session_info_retrieval_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session info: {str(e)}",
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


@router.get("/conversations/{conversation_id}/phase-events")
async def get_conversation_phase_events(conversation_id: str) -> list[dict]:
    """Retrieve phase events for a conversation.

    Sprint 48 Feature 48.5: Phase Events Redis Persistence (5 SP)

    This endpoint retrieves the phase events (thinking process) for a specific
    conversation from Redis. Phase events show which processing phases were
    executed (intent classification, vector search, graph query, LLM generation, etc.)
    with timing information and metadata.

    Args:
        conversation_id: Conversation identifier (session_id)

    Returns:
        List of phase event dictionaries with:
            - phase_type: Type of processing phase (e.g., "vector_search")
            - status: Execution status (pending, in_progress, completed, failed)
            - start_time: When the phase started (ISO timestamp)
            - end_time: When the phase completed (ISO timestamp, optional)
            - duration_ms: Phase execution time in milliseconds (optional)
            - metadata: Phase-specific data (e.g., docs_retrieved, top_k)
            - error: Error message if phase failed (optional)

    Raises:
        HTTPException: If retrieval fails

    Example Response:
        [
            {
                "phase_type": "intent_classification",
                "status": "completed",
                "start_time": "2025-12-16T10:00:00.000Z",
                "end_time": "2025-12-16T10:00:00.150Z",
                "duration_ms": 150.0,
                "metadata": {"detected_intent": "hybrid"},
                "error": null
            },
            {
                "phase_type": "vector_search",
                "status": "completed",
                "start_time": "2025-12-16T10:00:00.150Z",
                "end_time": "2025-12-16T10:00:00.350Z",
                "duration_ms": 200.0,
                "metadata": {"docs_retrieved": 10, "collection": "documents_v1"},
                "error": null
            }
        ]
    """
    logger.info("phase_events_retrieval_requested", conversation_id=conversation_id)

    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        events = await redis_memory.get_phase_events(conversation_id)

        logger.info(
            "phase_events_retrieved",
            conversation_id=conversation_id,
            event_count=len(events),
        )

        return [e.model_dump() for e in events]

    except Exception as e:
        logger.error(
            "phase_events_retrieval_failed",
            conversation_id=conversation_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve phase events: {str(e)}",
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
async def generate_title_for_session(session_id: str) -> TitleResponse:
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

        # Sprint 35 Feature 35.4: Use AegisLLMProxy for title generation
        generated_title = await generate_conversation_title(
            query=first_user_msg,
            answer=first_assistant_msg,
        )

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
        return result["answer"]  # type: ignore[no-any-return]

    # 2. Check messages (LangGraph format)
    messages = result.get("messages", [])
    if messages:
        # Last message is typically the answer
        last_message = messages[-1]
        if isinstance(last_message, dict):
            return last_message.get("content", "No answer generated")  # type: ignore[no-any-return]
        # Handle LangChain message objects
        if hasattr(last_message, "content"):
            return last_message.content
        return str(last_message)

    # 3. Check "response" field (alternative naming)
    if "response" in result:
        return result["response"]  # type: ignore[no-any-return]

    # 4. Fallback
    logger.warning("no_answer_found_in_result", result_keys=list(result.keys()))
    return "I'm sorry, I couldn't generate an answer. Please try rephrasing your question."


def _extract_sources(result: dict[str, Any]) -> list[SourceDocument]:
    """Extract source documents from coordinator result.

    Sprint 32 Feature 32.3: Enhanced with section metadata for precise citations

    Args:
        result: Result dictionary from CoordinatorAgent

    Returns:
        list of SourceDocument objects with section information
    """
    sources: list[SourceDocument] = []

    # Get retrieved contexts
    contexts = result.get("retrieved_contexts", [])

    for ctx in contexts:
        if isinstance(ctx, dict):
            # Sprint 32: Extract section metadata for citations
            section_headings = ctx.get("section_headings", [])
            section_pages = ctx.get("section_pages", [])
            primary_section = ctx.get("primary_section", "")

            # Build enhanced title with section information
            title = ctx.get("title", ctx.get("source", "Unknown"))

            # Format: "document.pdf - Section: 'Load Balancing' (Page 2)"
            if primary_section and section_pages:
                title = f"{title} - Section: '{primary_section}' (Page {section_pages[0]})"
            elif primary_section:
                title = f"{title} - Section: '{primary_section}'"

            # Add section metadata to metadata field
            enhanced_metadata = ctx.get("metadata", {})
            if section_headings:
                enhanced_metadata["section_headings"] = section_headings
            if section_pages:
                enhanced_metadata["section_pages"] = section_pages
            if primary_section:
                enhanced_metadata["primary_section"] = primary_section

            # Sprint 92 Fix: Add rank to metadata for frontend display
            # The rank field from RetrievedContext needs to be in metadata for SourceCard
            if "rank" in ctx and ctx["rank"] is not None:
                enhanced_metadata["rank"] = ctx["rank"]

            # Sprint 81: Removed 500-char truncation for full context in RAGAS evaluation
            # Full chunk text is needed for accurate Faithfulness metrics

            # Sprint 92: Normalize score for frontend display (0.0-1.0 range)
            # Priority: rerank_score > original score > weighted_rrf_score
            # - rerank_score: Cross-encoder score (0-1 range, most meaningful)
            # - score: Original channel score (vector=0-1, graph=entity_count)
            # - weighted_rrf_score: RRF fusion score (very small, ~0.01-0.05)
            raw_score = ctx.get("rerank_score")  # Best option: reranker score (0-1)
            if raw_score is None:
                raw_score = ctx.get("score", ctx.get("relevance"))

            # Normalize score to 0-1 range for display
            normalized_score = None
            if raw_score is not None:
                if raw_score > 1.0:
                    # Entity count from graph search (1, 2, 3...) - normalize to 0-1
                    # Use logarithmic scale: score of 5 entities ≈ 0.85
                    import math

                    normalized_score = min(1.0, math.log10(raw_score + 1) / math.log10(10))
                else:
                    # Already in 0-1 range (vector similarity or rerank score)
                    normalized_score = max(0.0, min(1.0, raw_score))

            source = SourceDocument(
                text=ctx.get("text", ctx.get("content", "")),  # Full chunk text (no truncation)
                title=title,  # Enhanced with section info
                source=ctx.get("source", ctx.get("file_path", "Unknown")),
                score=normalized_score,
                metadata=enhanced_metadata,
            )
            sources.append(source)

    # Sprint 92: Filter out sources with very low relevance scores (< 5%)
    # These are likely irrelevant matches from broad graph queries
    MIN_RELEVANCE_THRESHOLD = 0.05
    filtered_sources = [s for s in sources if s.score is None or s.score >= MIN_RELEVANCE_THRESHOLD]

    logger.debug(
        "sources_extracted",
        count=len(filtered_sources),
        filtered_out=len(sources) - len(filtered_sources),
        with_sections=sum(1 for s in filtered_sources if s.metadata.get("primary_section")),
    )
    return filtered_sources[:5]  # Return top 5 sources


def _extract_tool_calls(result: dict[str, Any]) -> list[ToolCallInfo]:
    """Extract MCP tool call information from coordinator result.

    Args:
        result: Result dictionary from CoordinatorAgent

    Returns:
        list of ToolCallInfo objects
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
    return datetime.now(UTC).isoformat()


# Sprint 38 Feature 38.3: Share Conversation Links


class ShareSettings(BaseModel):
    """Share link settings model."""

    expiry_hours: int = Field(
        default=24, ge=1, le=168, description="Hours until share link expires (1h to 7 days)"
    )


class ShareLinkResponse(BaseModel):
    """Share link response model."""

    share_url: str = Field(..., description="Full public URL for shared conversation")
    share_token: str = Field(..., description="Share token (URL-safe)")
    expires_at: str = Field(..., description="ISO timestamp when link expires")
    session_id: str = Field(..., description="Session ID being shared")


class SharedConversationResponse(BaseModel):
    """Shared conversation response (public, no auth required)."""

    session_id: str = Field(..., description="Session ID")
    title: str | None = Field(default=None, description="Conversation title")
    messages: list[dict[str, Any]] = Field(..., description="Conversation messages")
    message_count: int = Field(..., description="Number of messages")
    created_at: str | None = Field(default=None, description="When conversation was created")
    shared_at: str = Field(..., description="When link was generated")
    expires_at: str = Field(..., description="When link expires")


@router.post("/sessions/{session_id}/share", response_model=ShareLinkResponse)
async def create_share_link(
    session_id: str, settings: ShareSettings = ShareSettings()
) -> ShareLinkResponse:
    """Generate public share link for conversation.

    Sprint 38 Feature 38.3: Share Conversation Links

    This endpoint:
    1. Validates that session exists
    2. Generates secure URL-safe token
    3. Stores share metadata in Redis with TTL
    4. Returns full share URL and metadata

    Args:
        session_id: Session ID to share
        settings: Share settings (expiry duration)

    Returns:
        ShareLinkResponse with share URL and token

    Raises:
        HTTPException: If session not found or share creation fails

    Example Request:
        POST /chat/sessions/abc-123/share
        {
            "expiry_hours": 24
        }

    Example Response:
        {
            "share_url": "http://localhost:5173/share/Xk9f2mZ_pQrT1aB3",
            "share_token": "Xk9f2mZ_pQrT1aB3",
            "expires_at": "2025-12-09T10:30:00Z",
            "session_id": "abc-123"
        }
    """
    logger.info("share_link_requested", session_id=session_id, expiry_hours=settings.expiry_hours)

    try:
        import secrets

        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        # Verify session exists
        conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found",
            )

        # Generate secure token (16 bytes = 22 chars URL-safe)
        share_token = secrets.token_urlsafe(16)

        # Calculate expiry
        from datetime import timedelta

        expires_at_dt = datetime.now(UTC) + timedelta(hours=settings.expiry_hours)
        expires_at = expires_at_dt.isoformat()

        # Store share metadata in Redis
        share_data = {
            "session_id": session_id,
            "created_at": _get_iso_timestamp(),
            "expires_at": expires_at,
        }

        ttl_seconds = settings.expiry_hours * 3600

        await redis_memory.store(
            key=share_token, value=share_data, ttl_seconds=ttl_seconds, namespace="share"
        )

        # Build share URL (derive from app settings)
        # Use app settings for API host, default to localhost for local development
        from src.core.config import get_settings as get_app_settings

        app_settings = get_app_settings()
        base_url = (
            f"http://{app_settings.api_host}"
            if app_settings.api_host not in ("0.0.0.0", "localhost")
            else "http://localhost"
        )
        share_url = f"{base_url}:5173/share/{share_token}"

        logger.info(
            "share_link_created",
            session_id=session_id,
            share_token=share_token,
            expires_at=expires_at,
        )

        return ShareLinkResponse(
            share_url=share_url,
            share_token=share_token,
            expires_at=expires_at,
            session_id=session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("share_link_creation_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create share link: {str(e)}",
        ) from e


@router.get("/share/{share_token}", response_model=SharedConversationResponse)
async def get_shared_conversation(share_token: str) -> SharedConversationResponse:
    """Get shared conversation (no auth required).

    Sprint 38 Feature 38.3: Share Conversation Links

    This endpoint:
    1. Looks up share token in Redis
    2. Retrieves conversation data
    3. Returns read-only conversation view
    4. No authentication required (public link)

    Args:
        share_token: Share token from URL

    Returns:
        SharedConversationResponse with conversation data

    Raises:
        HTTPException: If token not found, expired, or invalid

    Example Request:
        GET /chat/share/Xk9f2mZ_pQrT1aB3

    Example Response:
        {
            "session_id": "abc-123",
            "title": "Discussion about AEGIS RAG",
            "messages": [
                {"role": "user", "content": "What is AEGIS RAG?", ...},
                {"role": "assistant", "content": "AEGIS RAG is...", ...}
            ],
            "message_count": 2,
            "created_at": "2025-12-08T10:00:00Z",
            "shared_at": "2025-12-08T10:30:00Z",
            "expires_at": "2025-12-09T10:30:00Z"
        }
    """
    logger.info("shared_conversation_requested", share_token=share_token[:8])

    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        # Lookup share token
        share_data = await redis_memory.retrieve(
            key=share_token, namespace="share", track_access=False
        )

        if not share_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share link not found or expired",
            )

        # Extract value from Redis wrapper
        if isinstance(share_data, dict) and "value" in share_data:
            share_data = share_data["value"]

        session_id = share_data.get("session_id")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid share data",
            )

        # Retrieve conversation
        conversation = await redis_memory.retrieve(
            key=session_id, namespace="conversation", track_access=False
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared conversation no longer exists",
            )

        # Extract value from Redis wrapper
        if isinstance(conversation, dict) and "value" in conversation:
            conversation = conversation["value"]

        logger.info("shared_conversation_retrieved", session_id=session_id)

        return SharedConversationResponse(
            session_id=session_id,
            title=conversation.get("title"),
            messages=conversation.get("messages", []),
            message_count=conversation.get("message_count", 0),
            created_at=conversation.get("created_at"),
            shared_at=share_data.get("created_at"),
            expires_at=share_data.get("expires_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "shared_conversation_retrieval_failed", share_token=share_token[:8], error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve shared conversation: {str(e)}",
        ) from e


# Sprint 27 Feature 27.5: Follow-up Question Suggestions


class FollowUpQuestionsResponse(BaseModel):
    """Follow-up questions response model."""

    session_id: str = Field(..., description="Session ID")
    followup_questions: list[str] = Field(
        default_factory=list, description="list of follow-up questions (3-5)"
    )
    generated_at: str = Field(..., description="Timestamp when questions were generated")
    from_cache: bool = Field(default=False, description="Whether questions were from cache")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "user-123-session",
                "followup_questions": [
                    "How does vector search work in AEGIS RAG?",
                    "What are the key components of the system?",
                    "How does it compare to traditional RAG?",
                ],
                "generated_at": "2025-11-18T10:30:00Z",
                "from_cache": False,
            }
        }
    )


@router.get("/sessions/{session_id}/followup-questions", response_model=FollowUpQuestionsResponse)
async def get_followup_questions(session_id: str) -> FollowUpQuestionsResponse:
    """Get follow-up question suggestions for the last answer.

    Sprint 27 Feature 27.5: Follow-up Question Suggestions
    Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)

    This endpoint:
    1. Checks if questions were pre-generated asynchronously (stored context)
    2. If not, falls back to synchronous generation from conversation
    3. Caches the questions in Redis for 5 minutes
    4. Returns questions to encourage deeper exploration

    CRITICAL: Frontend should poll this endpoint AFTER answer completes.
    Questions are generated asynchronously in the background.

    Args:
        session_id: Session ID to generate follow-up questions for

    Returns:
        FollowUpQuestionsResponse with 3-5 follow-up questions

    Raises:
        HTTPException: If session not found or generation fails

    Example Response:
        {
            "session_id": "session-123",
            "followup_questions": [
                "How does hybrid search combine vector and keyword search?",
                "What role does the graph database play in retrieval?",
                "Can you explain the memory consolidation process?"
            ],
            "generated_at": "2025-11-18T10:30:00Z",
            "from_cache": false
        }
    """
    logger.info("followup_questions_requested", session_id=session_id)

    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()
        cache_key = f"{session_id}:followup"

        # Sprint 118 Fix: Check cache FIRST - coordinator already stores questions here
        # This avoids expensive LLM regeneration on every request
        cached_questions = await redis_memory.retrieve(key=cache_key, namespace="cache")

        if cached_questions:
            # Extract value from Redis wrapper
            if isinstance(cached_questions, dict) and "value" in cached_questions:
                cached_questions = cached_questions["value"]

            questions = cached_questions.get("questions", [])
            if questions:
                logger.info(
                    "followup_questions_from_cache",
                    session_id=session_id,
                    count=len(questions),
                )
                return FollowUpQuestionsResponse(
                    session_id=session_id,
                    followup_questions=questions,
                    generated_at=_get_iso_timestamp(),
                    from_cache=True,
                )

        # Load conversation from Redis
        conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")

        if not conversation or (isinstance(conversation, dict) and "value" not in conversation):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found",
            )

        # Extract value from Redis wrapper
        if isinstance(conversation, dict) and "value" in conversation:
            conversation = conversation["value"]

        # Sprint 35 Feature 35.3: Return stored follow-up questions if available
        stored_questions = conversation.get("follow_up_questions", [])
        if stored_questions:
            logger.info(
                "followup_questions_from_storage",
                session_id=session_id,
                count=len(stored_questions),
            )
            return FollowUpQuestionsResponse(
                session_id=session_id,
                followup_questions=stored_questions,
                generated_at=conversation.get("updated_at", _get_iso_timestamp()),
                from_cache=False,
            )

        messages = conversation.get("messages", [])

        # Need at least one Q&A pair
        if len(messages) < 2:
            logger.info(
                "followup_questions_insufficient_messages",
                session_id=session_id,
                message_count=len(messages),
            )
            return FollowUpQuestionsResponse(
                session_id=session_id,
                followup_questions=[],
                generated_at=_get_iso_timestamp(),
                from_cache=False,
            )

        # Get last user query and assistant response
        last_user_msg = None
        last_assistant_msg = None

        for msg in reversed(messages):
            if msg.get("role") == "assistant" and not last_assistant_msg:
                last_assistant_msg = msg
            elif msg.get("role") == "user" and not last_user_msg:
                last_user_msg = msg

            if last_user_msg and last_assistant_msg:
                break

        if not last_user_msg or not last_assistant_msg:
            logger.warning(
                "followup_questions_no_qa_pair",
                session_id=session_id,
                has_user=bool(last_user_msg),
                has_assistant=bool(last_assistant_msg),
            )
            return FollowUpQuestionsResponse(
                session_id=session_id,
                followup_questions=[],
                generated_at=_get_iso_timestamp(),
                from_cache=False,
            )

        # Extract sources from assistant message (if available)
        sources = []
        if "sources" in last_assistant_msg:
            sources = last_assistant_msg["sources"]

        # Generate follow-up questions
        questions = await generate_followup_questions(
            query=last_user_msg.get("content", ""),
            answer=last_assistant_msg.get("content", ""),
            sources=sources,
        )

        # Cache questions in Redis (5min TTL)
        if questions:
            await redis_memory.store(
                key=cache_key,
                value={"questions": questions},
                namespace="cache",
                ttl_seconds=300,  # 5 minutes
            )

        logger.info(
            "followup_questions_generated",
            session_id=session_id,
            count=len(questions),
        )

        return FollowUpQuestionsResponse(
            session_id=session_id,
            followup_questions=questions,
            generated_at=_get_iso_timestamp(),
            from_cache=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "followup_questions_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate follow-up questions: {str(e)}",
        ) from e


@router.get("/sessions/{session_id}/followup-questions/stream")
async def stream_followup_questions(session_id: str) -> StreamingResponse:
    """Stream follow-up questions as they become available using SSE.

    Sprint 118 Feature: SSE Push for Follow-up Questions

    Instead of polling, frontend can subscribe to this endpoint and receive
    follow-up questions as soon as they're generated. This reduces latency
    and eliminates unnecessary polling requests.

    The endpoint polls internally (max 60s) and sends SSE events:
    - "waiting": Questions still being generated
    - "questions": Questions are ready (includes data)
    - "timeout": Max wait time exceeded
    - "error": Generation failed

    Args:
        session_id: Session ID to stream follow-up questions for

    Returns:
        StreamingResponse with SSE events

    Example SSE Response:
        event: waiting
        data: {"status": "generating", "elapsed_seconds": 5}

        event: questions
        data: {"questions": ["How does...", "What is..."], "count": 3}
    """
    import asyncio
    import json

    logger.info("followup_questions_stream_started", session_id=session_id)

    async def generate_sse_events():
        """Generate SSE events for follow-up questions.

        Sprint 118 Fix: Check cache FIRST before calling LLM.
        The coordinator already generates questions in background and stores in cache.
        We should check the cache to avoid duplicate LLM calls (30x per session!).
        """
        max_wait_seconds = 60
        poll_interval = 2  # Poll every 2 seconds
        elapsed = 0

        try:
            from src.components.memory import get_redis_memory
            from src.agents.followup_generator import generate_followup_questions_async

            redis_memory = get_redis_memory()
            cache_key = f"{session_id}:followup"

            while elapsed < max_wait_seconds:
                # Sprint 118 Fix: Check cache FIRST - coordinator stores questions here
                cached_questions = await redis_memory.retrieve(key=cache_key, namespace="cache")

                if cached_questions:
                    # Extract value from Redis wrapper
                    if isinstance(cached_questions, dict) and "value" in cached_questions:
                        cached_questions = cached_questions["value"]

                    questions = cached_questions.get("questions", [])
                    if questions and len(questions) > 0:
                        # Questions ready from cache - send and close
                        event_data = {
                            "questions": questions,
                            "count": len(questions),
                            "elapsed_seconds": elapsed,
                            "from_cache": True,
                        }
                        yield f"event: questions\ndata: {json.dumps(event_data)}\n\n"
                        logger.info(
                            "followup_questions_stream_from_cache",
                            session_id=session_id,
                            count=len(questions),
                            elapsed_seconds=elapsed,
                        )
                        return

                # Fallback: Try async generation (only if cache miss)
                # This is a safety net - ideally coordinator already cached
                async_questions = await generate_followup_questions_async(session_id)

                if async_questions and len(async_questions) > 0:
                    # Questions ready - send and close
                    event_data = {
                        "questions": async_questions,
                        "count": len(async_questions),
                        "elapsed_seconds": elapsed,
                    }
                    yield f"event: questions\ndata: {json.dumps(event_data)}\n\n"
                    logger.info(
                        "followup_questions_stream_complete",
                        session_id=session_id,
                        count=len(async_questions),
                        elapsed_seconds=elapsed,
                    )
                    return

                # Not ready yet - send waiting event
                waiting_data = {
                    "status": "generating",
                    "elapsed_seconds": elapsed,
                    "max_seconds": max_wait_seconds,
                }
                yield f"event: waiting\ndata: {json.dumps(waiting_data)}\n\n"

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            # Timeout reached
            timeout_data = {
                "status": "timeout",
                "elapsed_seconds": elapsed,
                "message": "Follow-up generation timed out",
            }
            yield f"event: timeout\ndata: {json.dumps(timeout_data)}\n\n"
            logger.warning(
                "followup_questions_stream_timeout",
                session_id=session_id,
                elapsed_seconds=elapsed,
            )

        except Exception as e:
            error_data = {
                "status": "error",
                "message": str(e),
            }
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
            logger.error(
                "followup_questions_stream_error",
                session_id=session_id,
                error=str(e),
            )

    return StreamingResponse(
        generate_sse_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# Sprint 17 Feature 17.4 Phase 1: Conversation Archiving Pipeline
# PLANNED FOR SPRINT 38: Frontend UI integration for conversation archiving


@router.post("/sessions/{session_id}/archive", status_code=status.HTTP_200_OK)
async def archive_conversation(session_id: str) -> dict[str, Any]:
    """Archive a conversation to Qdrant for semantic search.

    Sprint 17 Feature 17.4 Phase 1: Manual Archive Trigger
    Sprint 38 TODO: Integrate archive button in frontend conversation history

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


# PLANNED FOR SPRINT 38: Frontend search UI for archived conversations
@router.post("/search", status_code=status.HTTP_200_OK)
async def search_archived_conversations(
    request: ConversationSearchRequest,
) -> ConversationSearchResponse:
    """Search archived conversations using semantic similarity.

    Sprint 17 Feature 17.4 Phase 1: Semantic Conversation Search
    Sprint 38 TODO: Implement search bar UI in conversation history sidebar

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


# Sprint 63 Feature 63.1: Multi-Turn RAG Template


@router.post("/multi-turn", status_code=status.HTTP_200_OK)
async def multi_turn_chat(request: MultiTurnRequest) -> MultiTurnResponse:
    """Process multi-turn conversation with context tracking and contradiction detection.

    Sprint 63 Feature 63.1: Multi-Turn RAG Template (13 SP)

    This endpoint:
    1. Loads conversation history from Redis
    2. Enhances query with conversation context
    3. Retrieves relevant documents
    4. Detects contradictions with previous answers
    5. Generates context-aware answer
    6. Updates memory summary every 5 turns
    7. Saves updated conversation to Redis

    Args:
        request: MultiTurnRequest with query, conversation_id, and settings

    Returns:
        MultiTurnResponse with answer, sources, contradictions, and metadata

    Raises:
        HTTPException: If processing fails

    Example Request:
        POST /chat/multi-turn
        {
            "query": "What about the performance metrics?",
            "conversation_id": "conv-123",
            "namespace": "default",
            "detect_contradictions": true,
            "max_history_turns": 5
        }

    Example Response:
        {
            "answer": "Based on our previous discussion about the RAG system...",
            "query": "What about the performance metrics?",
            "conversation_id": "conv-123",
            "sources": [...],
            "contradictions": [],
            "memory_summary": "Discussion about RAG system architecture and components.",
            "turn_number": 3,
            "metadata": {...}
        }
    """
    from src.agents.multi_turn import MultiTurnAgent
    from src.api.models.multi_turn import MultiTurnResponse

    logger.info(
        "multi_turn_request_received",
        conversation_id=request.conversation_id,
        query=request.query[:100],
        namespace=request.namespace,
    )

    try:
        # Load conversation history from Redis
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        conversation_data = await redis_memory.retrieve(
            key=request.conversation_id, namespace="multi_turn_conversation"
        )

        conversation_history = []
        if conversation_data:
            # Extract value from Redis wrapper
            if isinstance(conversation_data, dict) and "value" in conversation_data:
                conversation_data = conversation_data["value"]
            conversation_history = conversation_data.get("turns", [])

        logger.info(
            "multi_turn_conversation_loaded",
            conversation_id=request.conversation_id,
            history_length=len(conversation_history),
        )

        # Initialize multi-turn agent
        agent = MultiTurnAgent()

        # Process turn
        result = await agent.process_turn(
            query=request.query,
            conversation_id=request.conversation_id,
            conversation_history=conversation_history,
            namespace=request.namespace,
            detect_contradictions=request.detect_contradictions,
            max_history_turns=request.max_history_turns,
        )

        # Save updated conversation to Redis
        # Add current turn to history
        from src.api.models.multi_turn import ConversationTurn

        current_turn = ConversationTurn(
            query=request.query,
            answer=result["answer"],
            sources=result["sources"],
            timestamp=datetime.now(UTC),
        )

        # Serialize sources for storage
        serialized_sources = [s.model_dump() for s in result["sources"]]

        conversation_history.append(
            {
                "query": request.query,
                "answer": result["answer"],
                "sources": serialized_sources,
                "timestamp": current_turn.timestamp.isoformat(),
            }
        )

        # Prune old turns (keep last 10)
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]

        # Save to Redis
        await redis_memory.store(
            key=request.conversation_id,
            value={"turns": conversation_history, "updated_at": datetime.now(UTC).isoformat()},
            namespace="multi_turn_conversation",
            ttl_seconds=604800,  # 7 days
        )

        logger.info(
            "multi_turn_conversation_saved",
            conversation_id=request.conversation_id,
            turn_number=result["turn_number"],
        )

        # Build response
        response = MultiTurnResponse(
            answer=result["answer"],
            query=request.query,
            conversation_id=request.conversation_id,
            sources=result["sources"],
            contradictions=result["contradictions"],
            memory_summary=result.get("memory_summary"),
            turn_number=result["turn_number"],
            metadata=result["metadata"],
        )

        return response

    except Exception as e:
        logger.error(
            "multi_turn_request_failed",
            conversation_id=request.conversation_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process multi-turn query: {str(e)}",
        ) from e
