"""Pydantic models for Skill Management APIs.

Sprint Context:
    - Sprint 99 (2026-01-15): Feature 99.1 - Skill Management APIs (18 SP)

This module defines all request/response models for the Skill Management API
endpoints that bridge Sprint 97 frontend with Sprint 90-92 backend.

Based on: SPRINT_99_PLAN.md Feature 99.1

Example:
    >>> from src.api.models.skill_models import SkillListRequest, SkillDetailResponse
    >>> request = SkillListRequest(page=1, page_size=20, status="active")
    >>> # Use in FastAPI endpoint
    >>> response = SkillDetailResponse(
    ...     name="reflection",
    ...     category="reasoning",
    ...     description="Self-critique and validation loop",
    ...     author="AegisRAG Team",
    ...     version="1.0.0",
    ...     status="active",
    ...     tags=["validation", "quality"],
    ...     skill_md="# Reflection Skill...",
    ...     config_yaml="max_iterations: 3",
    ...     tools=[],
    ...     lifecycle={}
    ... )

See Also:
    - docs/sprints/SPRINT_99_PLAN.md: Feature specification
    - src/agents/skills/registry.py: Backend Skill Registry
    - src/agents/skills/lifecycle.py: Backend Skill Lifecycle
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================


class SkillStatus(str, Enum):
    """Skill status enumeration.

    Based on SkillState from src/agents/skills/lifecycle.py
    """

    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class SkillCategory(str, Enum):
    """Skill category enumeration."""

    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    RESEARCH = "research"
    TOOLS = "tools"
    OTHER = "other"


class AccessLevel(str, Enum):
    """Tool access level enumeration."""

    STANDARD = "standard"
    ELEVATED = "elevated"
    ADMIN = "admin"


# ============================================================================
# Request Models
# ============================================================================


class SkillListRequest(BaseModel):
    """Request model for listing skills.

    Query parameters for GET /api/v1/skills

    Attributes:
        page: Page number (1-indexed)
        page_size: Items per page (10-100)
        status: Filter by skill status
        category: Filter by skill category
        tags: Filter by tags (comma-separated)
        search: Full-text search query

    Example:
        >>> request = SkillListRequest(
        ...     page=1,
        ...     page_size=20,
        ...     status=SkillStatus.ACTIVE,
        ...     category=SkillCategory.REASONING,
        ...     tags="validation,quality",
        ...     search="reflection"
        ... )
    """

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=10, le=100, description="Items per page")
    status: Optional[SkillStatus] = Field(None, description="Filter by status")
    category: Optional[SkillCategory] = Field(None, description="Filter by category")
    tags: Optional[str] = Field(None, description="Filter by tags (comma-separated)")
    search: Optional[str] = Field(None, description="Full-text search query")


class SkillCreateRequest(BaseModel):
    """Request model for creating a new skill.

    POST /api/v1/skills

    Attributes:
        name: Unique skill name (alphanumeric + underscores)
        category: Skill category
        description: Brief description
        author: Author name or organization
        version: Semantic version (e.g., "1.0.0")
        tags: List of tags
        skill_md: SKILL.md content (required)
        config_yaml: Optional config.yaml content

    Example:
        >>> request = SkillCreateRequest(
        ...     name="custom_skill",
        ...     category=SkillCategory.TOOLS,
        ...     description="Custom tool integration",
        ...     author="User",
        ...     version="1.0.0",
        ...     tags=["custom", "tools"],
        ...     skill_md="# Custom Skill\\n\\n..."
        ... )
    """

    name: str = Field(..., min_length=1, max_length=50, description="Unique skill name")
    category: SkillCategory = Field(..., description="Skill category")
    description: str = Field(..., min_length=1, max_length=500, description="Brief description")
    author: str = Field(..., min_length=1, max_length=100, description="Author name")
    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$", description="Semantic version")
    tags: List[str] = Field(default_factory=list, description="List of tags")
    skill_md: str = Field(..., min_length=10, description="SKILL.md content (required)")
    config_yaml: Optional[str] = Field(None, description="Optional config.yaml content")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate skill name is alphanumeric + underscores."""
        if not v.replace("_", "").isalnum():
            raise ValueError("Skill name must be alphanumeric with underscores")
        return v


class SkillUpdateRequest(BaseModel):
    """Request model for updating skill metadata.

    PUT /api/v1/skills/:name

    Attributes:
        description: Updated description
        tags: Updated tags
        status: Updated status

    Example:
        >>> request = SkillUpdateRequest(
        ...     description="Updated description",
        ...     tags=["updated", "tags"],
        ...     status=SkillStatus.ACTIVE
        ... )
    """

    description: Optional[str] = Field(None, min_length=1, max_length=500)
    tags: Optional[List[str]] = Field(None, description="Updated tags")
    status: Optional[SkillStatus] = Field(None, description="Updated status")


class SkillConfigUpdateRequest(BaseModel):
    """Request model for updating skill YAML config.

    PUT /api/v1/skills/:name/config

    Attributes:
        yaml_content: Updated YAML configuration

    Example:
        >>> request = SkillConfigUpdateRequest(
        ...     yaml_content="max_iterations: 5\\nthreshold: 0.9"
        ... )
    """

    yaml_content: str = Field(..., min_length=1, description="Updated YAML config")


class ToolAuthorizationRequest(BaseModel):
    """Request model for adding tool authorization.

    POST /api/v1/skills/:name/tools

    Attributes:
        tool_name: Name of tool to authorize
        access_level: Access level for tool
        permissions: List of permissions

    Example:
        >>> request = ToolAuthorizationRequest(
        ...     tool_name="browser",
        ...     access_level=AccessLevel.STANDARD,
        ...     permissions=["read", "navigate"]
        ... )
    """

    tool_name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    access_level: AccessLevel = Field(AccessLevel.STANDARD, description="Access level")
    permissions: List[str] = Field(default_factory=list, description="Tool permissions")


# ============================================================================
# Response Models
# ============================================================================


class SkillSummary(BaseModel):
    """Summary model for skill list view.

    Sprint 99 Bug #8 Fix: Align with Sprint 97 Frontend Interface

    Frontend (Sprint 97) expects:
        - is_active: boolean (not status enum)
        - tools_count: number
        - triggers_count: number
        - icon: string (emoji)

    Attributes:
        name: Skill name
        version: Current version
        description: Brief description
        author: Author name
        is_active: Whether skill is active (true) or inactive (false)
        tools_count: Number of authorized tools
        triggers_count: Number of trigger patterns
        icon: Emoji icon for display

    Example:
        >>> summary = SkillSummary(
        ...     name="reflection",
        ...     version="1.0.0",
        ...     description="Self-critique loop",
        ...     author="AegisRAG Team",
        ...     is_active=True,
        ...     tools_count=3,
        ...     triggers_count=5,
        ...     icon="🔍"
        ... )
    """

    name: str
    version: str
    description: str
    author: str
    is_active: bool
    tools_count: int
    triggers_count: int
    icon: str


class SkillListResponse(BaseModel):
    """Response model for skill list.

    GET /api/v1/skills

    Attributes:
        items: List of skill summaries
        page: Current page number
        page_size: Items per page
        total: Total number of skills
        total_pages: Total number of pages

    Example:
        >>> response = SkillListResponse(
        ...     items=[summary1, summary2],
        ...     page=1,
        ...     page_size=20,
        ...     total=45,
        ...     total_pages=3
        ... )
    """

    items: List[SkillSummary]
    page: int
    page_size: int
    total: int
    total_pages: int


class ToolAuthorization(BaseModel):
    """Tool authorization details.

    Attributes:
        tool_name: Name of tool
        access_level: Access level granted
        permissions: List of permissions
        authorized_at: Authorization timestamp
    """

    tool_name: str
    access_level: AccessLevel
    permissions: List[str]
    authorized_at: datetime


class SkillLifecycleInfo(BaseModel):
    """Skill lifecycle information.

    Attributes:
        state: Current lifecycle state
        loaded_at: When skill was loaded
        activated_at: When skill was activated
        last_used: Last usage timestamp
        invocation_count: Number of invocations
    """

    state: SkillStatus
    loaded_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    invocation_count: int = 0


class SkillDetailResponse(BaseModel):
    """Detailed skill information response.

    GET /api/v1/skills/:name

    Attributes:
        name: Skill name
        category: Skill category
        description: Description
        author: Author name
        version: Current version
        status: Current status
        tags: List of tags
        skill_md: SKILL.md content
        config_yaml: config.yaml content
        tools: List of authorized tools
        lifecycle: Lifecycle information
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> response = SkillDetailResponse(
        ...     name="reflection",
        ...     category=SkillCategory.REASONING,
        ...     description="Self-critique loop",
        ...     author="AegisRAG Team",
        ...     version="1.0.0",
        ...     status=SkillStatus.ACTIVE,
        ...     tags=["validation"],
        ...     skill_md="# Reflection Skill\\n\\n...",
        ...     config_yaml="max_iterations: 3",
        ...     tools=[],
        ...     lifecycle=SkillLifecycleInfo(state=SkillStatus.ACTIVE),
        ...     created_at=datetime.now(),
        ...     updated_at=datetime.now()
        ... )
    """

    name: str
    category: SkillCategory
    description: str
    author: str
    version: str
    status: SkillStatus
    tags: List[str]
    skill_md: str
    config_yaml: Optional[str]
    tools: List[ToolAuthorization]
    lifecycle: SkillLifecycleInfo
    created_at: datetime
    updated_at: datetime


class SkillConfigResponse(BaseModel):
    """Skill configuration response.

    GET /api/v1/skills/:name/config

    Attributes:
        skill_name: Skill name
        yaml_content: YAML configuration content
        parsed_config: Parsed configuration as dict

    Example:
        >>> response = SkillConfigResponse(
        ...     skill_name="reflection",
        ...     yaml_content="max_iterations: 3",
        ...     parsed_config={"max_iterations": 3}
        ... )
    """

    skill_name: str
    yaml_content: str
    parsed_config: Dict[str, Any]


class SkillToolsResponse(BaseModel):
    """Skill tools response.

    GET /api/v1/skills/:name/tools

    Attributes:
        skill_name: Skill name
        tools: List of authorized tools
        total: Total number of tools

    Example:
        >>> response = SkillToolsResponse(
        ...     skill_name="reflection",
        ...     tools=[tool1, tool2],
        ...     total=2
        ... )
    """

    skill_name: str
    tools: List[ToolAuthorization]
    total: int


class SkillCreateResponse(BaseModel):
    """Skill creation response.

    POST /api/v1/skills

    Attributes:
        skill_name: Created skill name
        status: Creation status
        message: Success message
        created_at: Creation timestamp

    Example:
        >>> response = SkillCreateResponse(
        ...     skill_name="custom_skill",
        ...     status="created",
        ...     message="Skill created successfully",
        ...     created_at=datetime.now()
        ... )
    """

    skill_name: str
    status: str
    message: str
    created_at: datetime


class SkillUpdateResponse(BaseModel):
    """Skill update response.

    PUT /api/v1/skills/:name

    Attributes:
        skill_name: Updated skill name
        status: Update status
        message: Success message
        updated_at: Update timestamp
    """

    skill_name: str
    status: str
    message: str
    updated_at: datetime


class SkillDeleteResponse(BaseModel):
    """Skill deletion response.

    DELETE /api/v1/skills/:name

    Attributes:
        skill_name: Deleted skill name
        status: Deletion status
        message: Success message
        deleted_at: Deletion timestamp
    """

    skill_name: str
    status: str
    message: str
    deleted_at: datetime


class SkillActivateResponse(BaseModel):
    """Skill activation response.

    POST /api/v1/skills/registry/:name/activate

    Attributes:
        skill_name: Activated skill name
        status: Activation status (active)
        message: Success message
        activated_at: Activation timestamp

    Example:
        >>> response = SkillActivateResponse(
        ...     skill_name="reflection",
        ...     status="active",
        ...     message="Skill activated successfully",
        ...     activated_at=datetime.now()
        ... )
    """

    skill_name: str
    status: str
    message: str
    activated_at: datetime


class SkillDeactivateResponse(BaseModel):
    """Skill deactivation response.

    POST /api/v1/skills/registry/:name/deactivate

    Attributes:
        skill_name: Deactivated skill name
        status: Deactivation status (inactive)
        message: Success message
        deactivated_at: Deactivation timestamp

    Example:
        >>> response = SkillDeactivateResponse(
        ...     skill_name="reflection",
        ...     status="inactive",
        ...     message="Skill deactivated successfully",
        ...     deactivated_at=datetime.now()
        ... )
    """

    skill_name: str
    status: str
    message: str
    deactivated_at: datetime


class ErrorResponse(BaseModel):
    """Error response model.

    Used for all error responses across skill management endpoints.

    Attributes:
        error: Error type
        message: Error message
        field: Optional field name (for validation errors)
        code: Optional error code

    Example:
        >>> error = ErrorResponse(
        ...     error="ValidationError",
        ...     message="Skill name already exists",
        ...     field="name",
        ...     code="DUPLICATE_SKILL"
        ... )
    """

    error: str
    message: str
    field: Optional[str] = None
    code: Optional[str] = None


class ConfigValidationRequest(BaseModel):
    """Request model for validating skill config.

    POST /api/v1/skills/:name/config/validate

    Attributes:
        yaml_content: YAML configuration to validate

    Example:
        >>> request = ConfigValidationRequest(
        ...     yaml_content="max_iterations: 3\\nthreshold: 0.9"
        ... )
    """

    yaml_content: str = Field(..., min_length=1, description="YAML config to validate")


class ConfigValidationResponse(BaseModel):
    """Response model for config validation.

    POST /api/v1/skills/:name/config/validate

    Attributes:
        valid: Whether config is valid
        errors: List of validation errors
        warnings: List of validation warnings

    Example:
        >>> response = ConfigValidationResponse(
        ...     valid=True,
        ...     errors=[],
        ...     warnings=["Using default value for 'timeout'"]
        ... )
    """

    valid: bool = Field(..., description="Whether config is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class SkillExecuteRequest(BaseModel):
    """Request model for executing a skill.

    Sprint 105 Feature 105.7: Skills Execute Endpoint

    POST /api/v1/skills/:name/execute

    Attributes:
        parameters: Execution parameters (skill-specific)
        timeout: Optional execution timeout in seconds
        context: Optional execution context

    Example:
        >>> request = SkillExecuteRequest(
        ...     parameters={"query": "What is RAG?", "max_tokens": 100},
        ...     timeout=30,
        ...     context={"user_id": "test-user", "session_id": "abc123"}
        ... )
    """

    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Skill execution parameters"
    )
    timeout: Optional[int] = Field(30, ge=1, le=300, description="Execution timeout (1-300s)")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional execution context"
    )


class SkillExecuteResponse(BaseModel):
    """Response model for skill execution.

    Sprint 105 Feature 105.7: Skills Execute Endpoint

    POST /api/v1/skills/:name/execute

    Attributes:
        skill_name: Executed skill name
        status: Execution status ("success" | "error" | "timeout")
        result: Execution result (skill-specific)
        error: Error message if execution failed
        executed_at: Execution timestamp
        execution_time: Execution duration in seconds

    Example:
        >>> response = SkillExecuteResponse(
        ...     skill_name="retrieval",
        ...     status="success",
        ...     result={"answer": "RAG is...", "sources": [...]},
        ...     error=None,
        ...     executed_at=datetime.now(),
        ...     execution_time=1.234
        ... )
    """

    skill_name: str
    status: str = Field(..., description="Execution status (success/error/timeout)")
    result: Optional[Any] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    executed_at: datetime
    execution_time: float = Field(..., description="Execution duration in seconds")
