"""Pydantic models for Agent Monitoring APIs.

Sprint 99 Feature 99.2: Agent Monitoring APIs (16 SP)

This module defines request/response models for agent communication,
blackboard state, orchestration, and hierarchy monitoring endpoints.

Models:
    - AgentMessage: MessageBus message representation
    - BlackboardNamespace: Blackboard namespace state
    - OrchestrationSummary: Active orchestration summary
    - OrchestrationTrace: Orchestration timeline with events
    - CommunicationMetrics: Performance metrics for agent communication
    - HierarchyNode: Agent hierarchy tree node
    - AgentDetails: Detailed agent status and performance

See Also:
    - src/agents/messaging/message_bus.py: MessageBus implementation
    - src/agents/memory/shared_memory.py: Blackboard (SharedMemoryProtocol)
    - src/agents/orchestrator/skill_orchestrator.py: Orchestration
    - src/agents/hierarchy/skill_hierarchy.py: Agent hierarchy
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class MessageType(str, Enum):
    """Type of inter-agent message."""

    TASK_REQUEST = "task_request"
    RESULT_SHARE = "result_share"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    HANDOFF = "handoff"
    BROADCAST = "broadcast"


class MessagePriority(str, Enum):
    """Message priority level."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class OrchestrationStatus(str, Enum):
    """Status of orchestration workflow."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentLevel(str, Enum):
    """Hierarchical agent level."""

    EXECUTIVE = "executive"
    MANAGER = "manager"
    WORKER = "worker"


class AgentStatus(str, Enum):
    """Agent operational status."""

    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


# =============================================================================
# Message Models
# =============================================================================


class AgentMessage(BaseModel):
    """Agent-to-agent message from MessageBus.

    Example:
        ```json
        {
          "id": "msg_abc123",
          "sender": "coordinator",
          "recipient": "vector_agent",
          "message_type": "task_request",
          "payload": {"query": "What is RAG?", "top_k": 5},
          "priority": "normal",
          "timestamp": "2026-01-15T10:30:00Z",
          "correlation_id": "corr_xyz789"
        }
        ```
    """

    id: str = Field(..., description="Unique message identifier")
    sender: str = Field(..., description="Sending agent ID")
    recipient: str = Field(..., description="Receiving agent ID")
    message_type: MessageType = Field(..., description="Type of message")
    payload: dict[str, Any] = Field(..., description="Message content")
    priority: MessagePriority = Field(..., description="Message priority level")
    timestamp: datetime = Field(..., description="Message creation timestamp")
    correlation_id: str | None = Field(None, description="Correlation ID for request-response pairs")
    ttl_seconds: int = Field(60, description="Time-to-live in seconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MessageStreamRequest(BaseModel):
    """Request parameters for message streaming.

    Example:
        ```json
        {
          "agent_id": "vector_agent",
          "event_types": ["task_request", "result_share"],
          "since_timestamp": "2026-01-15T10:00:00Z"
        }
        ```
    """

    agent_id: str | None = Field(None, description="Filter by agent ID (sender or recipient)")
    event_types: list[MessageType] | None = Field(None, description="Filter by message types")
    since_timestamp: datetime | None = Field(None, description="Only messages after this timestamp")


# =============================================================================
# Blackboard Models
# =============================================================================


class BlackboardEntry(BaseModel):
    """Single entry in blackboard namespace.

    Example:
        ```json
        {
          "key": "research_findings",
          "value": {"papers": 10, "citations": 45},
          "owner_skill": "research",
          "timestamp": "2026-01-15T10:30:00Z",
          "ttl_remaining": 2400
        }
        ```
    """

    key: str = Field(..., description="Entry key")
    value: Any = Field(..., description="Entry value")
    owner_skill: str = Field(..., description="Skill that owns this entry")
    timestamp: datetime = Field(..., description="Entry creation timestamp")
    ttl_remaining: int | None = Field(None, description="Remaining TTL in seconds")


class BlackboardNamespace(BaseModel):
    """Blackboard namespace with all entries.

    Example:
        ```json
        {
          "namespace": "shared",
          "owner_skill": "coordinator",
          "entry_count": 5,
          "entries": [...]
        }
        ```
    """

    namespace: str = Field(..., description="Namespace name (private/shared/global)")
    owner_skill: str | None = Field(None, description="Owner skill (for private/shared)")
    entry_count: int = Field(..., description="Number of entries in namespace")
    entries: list[BlackboardEntry] = Field(default_factory=list, description="All entries")


class BlackboardResponse(BaseModel):
    """Response with all blackboard namespaces.

    Example:
        ```json
        {
          "namespaces": [...],
          "total_entries": 15
        }
        ```
    """

    namespaces: list[BlackboardNamespace] = Field(..., description="All namespaces")
    total_entries: int = Field(..., description="Total entries across all namespaces")


# =============================================================================
# Orchestration Models
# =============================================================================


class OrchestrationSummary(BaseModel):
    """Summary of active orchestration.

    Example:
        ```json
        {
          "orchestration_id": "orch_abc123",
          "skill_name": "research_workflow",
          "status": "running",
          "started_at": "2026-01-15T10:30:00Z",
          "duration_ms": 5000,
          "phase": "synthesis",
          "progress_percent": 65
        }
        ```
    """

    orchestration_id: str = Field(..., description="Unique orchestration identifier")
    skill_name: str = Field(..., description="Skill or workflow name")
    status: OrchestrationStatus = Field(..., description="Current status")
    started_at: datetime = Field(..., description="Orchestration start time")
    duration_ms: int | None = Field(None, description="Duration in milliseconds (for completed)")
    phase: str | None = Field(None, description="Current phase name")
    progress_percent: int | None = Field(None, description="Progress percentage (0-100)")


class TraceEvent(BaseModel):
    """Single event in orchestration trace.

    Example:
        ```json
        {
          "timestamp": "2026-01-15T10:30:05Z",
          "event_type": "skill_started",
          "skill_name": "web_search",
          "duration_ms": 1200,
          "success": true
        }
        ```
    """

    timestamp: datetime = Field(..., description="Event timestamp")
    event_type: str = Field(..., description="Event type (skill_started, skill_completed, etc.)")
    skill_name: str | None = Field(None, description="Skill name (if applicable)")
    duration_ms: int | None = Field(None, description="Duration in milliseconds")
    success: bool | None = Field(None, description="Whether event was successful")
    error: str | None = Field(None, description="Error message (if failed)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional event data")


class OrchestrationTrace(BaseModel):
    """Full orchestration trace with timeline.

    Example:
        ```json
        {
          "orchestration_id": "orch_abc123",
          "skill_name": "research_workflow",
          "events": [...],
          "total_duration_ms": 15300,
          "skill_count": 5,
          "success_rate": 0.8
        }
        ```
    """

    orchestration_id: str = Field(..., description="Orchestration identifier")
    skill_name: str = Field(..., description="Skill or workflow name")
    events: list[TraceEvent] = Field(..., description="Timeline of events")
    total_duration_ms: int = Field(..., description="Total orchestration duration")
    skill_count: int = Field(..., description="Number of skills executed")
    success_rate: float = Field(..., description="Success rate (0.0-1.0)")


class OrchestrationListResponse(BaseModel):
    """Paginated list of orchestrations.

    Example:
        ```json
        {
          "items": [...],
          "total": 42,
          "page": 1,
          "page_size": 20,
          "total_pages": 3
        }
        ```
    """

    items: list[OrchestrationSummary] = Field(..., description="Orchestration summaries")
    total: int = Field(..., description="Total number of orchestrations")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Page size")
    total_pages: int = Field(..., description="Total number of pages")


class OrchestrationMetrics(BaseModel):
    """Performance metrics for orchestrations.

    Example:
        ```json
        {
          "total_count": 150,
          "success_count": 142,
          "success_rate": 0.947,
          "avg_duration_ms": 8500,
          "p95_latency_ms": 15000,
          "error_rate": 0.053
        }
        ```
    """

    total_count: int = Field(..., description="Total orchestrations executed")
    success_count: int = Field(..., description="Successful orchestrations")
    success_rate: float = Field(..., description="Success rate (0.0-1.0)")
    avg_duration_ms: float = Field(..., description="Average duration in milliseconds")
    p95_latency_ms: float = Field(..., description="95th percentile latency")
    error_rate: float = Field(..., description="Error rate (0.0-1.0)")


# =============================================================================
# Agent Hierarchy Models
# =============================================================================


class HierarchyNode(BaseModel):
    """Node in agent hierarchy tree.

    Example:
        ```json
        {
          "agent_id": "executive_001",
          "name": "Executive Director",
          "level": "executive",
          "status": "active",
          "capabilities": ["planning", "coordination"],
          "child_count": 3
        }
        ```
    """

    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent display name")
    level: AgentLevel = Field(..., description="Hierarchical level")
    status: AgentStatus = Field(..., description="Operational status")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    child_count: int = Field(0, description="Number of child agents/skills")


class HierarchyEdge(BaseModel):
    """Edge in agent hierarchy tree (parent-child relationship).

    Example:
        ```json
        {
          "parent_id": "executive_001",
          "child_id": "research_manager_001",
          "relationship": "manages"
        }
        ```
    """

    parent_id: str = Field(..., description="Parent agent ID")
    child_id: str = Field(..., description="Child agent/skill ID")
    relationship: str = Field("manages", description="Relationship type")


class AgentHierarchyResponse(BaseModel):
    """Agent hierarchy tree (D3.js compatible format).

    Example:
        ```json
        {
          "nodes": [...],
          "edges": [...]
        }
        ```
    """

    nodes: list[HierarchyNode] = Field(..., description="Hierarchy nodes")
    edges: list[HierarchyEdge] = Field(..., description="Parent-child relationships")


# =============================================================================
# Agent Details Models
# =============================================================================


class ActiveTask(BaseModel):
    """Currently active task for an agent.

    Example:
        ```json
        {
          "task_id": "task_abc123",
          "skill_name": "web_search",
          "started_at": "2026-01-15T10:30:00Z",
          "duration_ms": 3000,
          "progress_percent": 45
        }
        ```
    """

    task_id: str = Field(..., description="Task identifier")
    skill_name: str = Field(..., description="Skill being executed")
    started_at: datetime = Field(..., description="Task start time")
    duration_ms: int = Field(..., description="Duration so far")
    progress_percent: int | None = Field(None, description="Progress percentage (0-100)")


class AgentPerformance(BaseModel):
    """Performance metrics for an agent.

    Example:
        ```json
        {
          "tasks_completed": 142,
          "tasks_failed": 8,
          "success_rate": 0.947,
          "avg_duration_ms": 5200,
          "queue_size": 3
        }
        ```
    """

    tasks_completed: int = Field(..., description="Total tasks completed")
    tasks_failed: int = Field(..., description="Total tasks failed")
    success_rate: float = Field(..., description="Success rate (0.0-1.0)")
    avg_duration_ms: float = Field(..., description="Average task duration")
    queue_size: int = Field(0, description="Pending tasks in queue")


class AgentDetails(BaseModel):
    """Detailed agent status and performance.

    Example:
        ```json
        {
          "agent_id": "research_manager_001",
          "name": "Research Manager",
          "type": "manager",
          "level": "manager",
          "status": "active",
          "capabilities": ["research", "information_gathering"],
          "skills": ["web_search", "retrieval", "graph_query"],
          "active_tasks": [...],
          "performance": {...}
        }
        ```
    """

    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent display name")
    type: str = Field(..., description="Agent type (supervisor/worker/manager)")
    level: AgentLevel = Field(..., description="Hierarchical level")
    status: AgentStatus = Field(..., description="Operational status")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    skills: list[str] = Field(default_factory=list, description="Available skills")
    active_tasks: list[ActiveTask] = Field(default_factory=list, description="Currently active tasks")
    performance: AgentPerformance | None = Field(None, description="Performance metrics")
