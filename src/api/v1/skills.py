"""Skill Management API endpoints.

Sprint Context:
    - Sprint 99 (2026-01-15): Feature 99.1 - Skill Management APIs (18 SP, 9 endpoints)

This module implements REST API endpoints for Skill Management, connecting
Sprint 97 frontend UI with Sprint 90-92 backend (Skill Registry & Lifecycle).

Architecture:
    Frontend (React) → FastAPI (/api/v1/skills) → SkillRegistry + SkillLifecycleManager

Endpoints:
    - GET /api/v1/skills - List all skills (paginated, filterable)
    - GET /api/v1/skills/:name - Get skill details
    - POST /api/v1/skills - Create new skill
    - PUT /api/v1/skills/:name - Update skill metadata
    - DELETE /api/v1/skills/:name - Delete skill
    - GET /api/v1/skills/:name/config - Get YAML config
    - PUT /api/v1/skills/:name/config - Update YAML config
    - GET /api/v1/skills/:name/tools - List authorized tools
    - POST /api/v1/skills/:name/tools - Add tool authorization

Based on: SPRINT_99_PLAN.md Feature 99.1

Example:
    >>> # List skills with filtering
    >>> GET /api/v1/skills?status=active&category=reasoning&page=1&page_size=20
    >>>
    >>> # Get skill details
    >>> GET /api/v1/skills/reflection
    >>>
    >>> # Create new skill
    >>> POST /api/v1/skills
    >>> {
    ...     "name": "custom_skill",
    ...     "category": "tools",
    ...     "description": "Custom tool integration",
    ...     "author": "User",
    ...     "skill_md": "# Custom Skill\\n\\n..."
    ... }

See Also:
    - docs/sprints/SPRINT_99_PLAN.md: Feature specification
    - src/agents/skills/registry.py: Skill Registry backend
    - src/agents/skills/lifecycle.py: Skill Lifecycle backend
    - src/api/models/skill_models.py: Pydantic models
"""

import math
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import structlog
import yaml
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from src.agents.skills import SkillLifecycleManager, get_skill_registry
from src.api.models.skill_models import (
    AccessLevel,
    ErrorResponse,
    ConfigValidationRequest,
    ConfigValidationResponse,
    SkillActivateResponse,
    SkillCategory,
    SkillConfigResponse,
    SkillConfigUpdateRequest,
    SkillCreateRequest,
    SkillCreateResponse,
    SkillDeactivateResponse,
    SkillDeleteResponse,
    SkillDetailResponse,
    SkillLifecycleInfo,
    SkillListResponse,
    SkillStatus,
    SkillSummary,
    SkillToolsResponse,
    SkillUpdateRequest,
    SkillUpdateResponse,
    ToolAuthorization,
    ToolAuthorizationRequest,
)
from src.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])

# Global skill managers (lazy initialization)
_skill_registry = None
_skill_lifecycle = None


def get_registry():
    """Get or create skill registry singleton."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = get_skill_registry(Path("skills"))
    return _skill_registry


def get_lifecycle():
    """Get or create skill lifecycle manager singleton."""
    global _skill_lifecycle
    if _skill_lifecycle is None:
        _skill_lifecycle = SkillLifecycleManager(
            skills_dir=Path("skills"),
            max_loaded_skills=20,
            max_active_skills=5,
            context_budget=10000,
        )
    return _skill_lifecycle


# ============================================================================
# Endpoint 1: GET /api/v1/skills - List all skills
# ============================================================================


@router.get("/registry", response_model=SkillListResponse)
async def list_skills(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=10, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (active, inactive, all)"),
    category: Optional[SkillCategory] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    search: Optional[str] = Query(None, description="Full-text search query"),
) -> SkillListResponse:
    """List all skills with pagination and filtering.

    Sprint 99 Feature 99.1: Skill Management APIs
    Endpoint: GET /api/v1/skills

    Query Parameters:
        - page: Page number (1-indexed, default: 1)
        - page_size: Items per page (10-100, default: 20)
        - status: Filter by status (discovered, loaded, active, inactive, error)
        - category: Filter by category (retrieval, reasoning, synthesis, etc.)
        - tags: Filter by tags (comma-separated, e.g., "validation,quality")
        - search: Full-text search query (matches name, description)

    Returns:
        SkillListResponse with paginated results

    Example:
        >>> GET /api/v1/skills?page=1&page_size=20&status=active&category=reasoning
        >>> {
        ...     "items": [
        ...         {
        ...             "name": "reflection",
        ...             "category": "reasoning",
        ...             "description": "Self-critique loop",
        ...             "version": "1.0.0",
        ...             "status": "active",
        ...             "tags": ["validation", "quality"],
        ...             "author": "AegisRAG Team",
        ...             "created_at": "2026-01-15T10:00:00Z",
        ...             "updated_at": "2026-01-15T10:00:00Z"
        ...         }
        ...     ],
        ...     "page": 1,
        ...     "page_size": 20,
        ...     "total": 45,
        ...     "total_pages": 3
        ... }

    Raises:
        HTTPException 500: If skill discovery or filtering fails
    """
    logger.info(
        "list_skills_endpoint_called",
        page=page,
        page_size=page_size,
        status=status,
        category=category,
        tags=tags,
        search=search,
    )

    try:
        registry = get_registry()
        lifecycle = get_lifecycle()

        # Normalize status parameter (Sprint 97 frontend compatibility)
        # Frontend sends: "active", "inactive", "all"
        # Backend uses: "discovered", "loaded", "active", "inactive", "error"
        normalized_status = None if status == "all" else status

        # Discover all available skills
        available_skills = registry.discover()

        # Build list of skill summaries
        all_skills = []
        for skill_name, metadata in available_skills.items():
            # Get lifecycle state
            skill_state = lifecycle.get_state(skill_name)

            # Map lifecycle state to API status
            api_status = _map_lifecycle_state_to_status(skill_state)

            # Sprint 99 Bug #8 Fix: Convert status enum to boolean for frontend
            # IMPORTANT: api_status is SkillStatus enum, not string!
            is_active = api_status == SkillStatus.ACTIVE

            # Apply status filter (now using boolean)
            if normalized_status == "active" and not is_active:
                continue
            if normalized_status == "inactive" and is_active:
                continue

            # Category filter (extract from metadata or default to OTHER)
            skill_category = _extract_category(metadata.description)
            if category and skill_category != category:
                continue

            # Tags filter
            if tags:
                requested_tags = {t.strip().lower() for t in tags.split(",")}
                skill_tags = {t.lower() for t in metadata.triggers}
                if not requested_tags.intersection(skill_tags):
                    continue

            # Search filter (name or description)
            if search:
                search_lower = search.lower()
                if (
                    search_lower not in skill_name.lower()
                    and search_lower not in metadata.description.lower()
                ):
                    continue

            # Count tools and triggers
            tools_count = len(metadata.tools) if hasattr(metadata, 'tools') else 0
            triggers_count = len(metadata.triggers)

            # Map category to emoji icon
            category_icons = {
                SkillCategory.RETRIEVAL: "🔍",
                SkillCategory.REASONING: "🧠",
                SkillCategory.SYNTHESIS: "✨",
                SkillCategory.VALIDATION: "✅",
                SkillCategory.RESEARCH: "📚",
                SkillCategory.TOOLS: "🔧",
                SkillCategory.OTHER: "⚙️",
            }
            icon = category_icons.get(skill_category, "⚙️")

            # Create summary (Frontend Sprint 97 compatible format)
            summary = SkillSummary(
                name=skill_name,
                version=metadata.version,
                description=metadata.description,
                author=metadata.author,
                is_active=is_active,
                tools_count=tools_count,
                triggers_count=triggers_count,
                icon=icon,
            )
            all_skills.append(summary)

        # Sort by name
        all_skills.sort(key=lambda s: s.name)

        # Apply pagination
        total = len(all_skills)
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_skills = all_skills[start_idx:end_idx]

        logger.info(
            "list_skills_success",
            total=total,
            page=page,
            page_size=page_size,
            returned_count=len(paginated_skills),
        )

        # Sprint 100 Fix #1: Return proper SkillListResponse with pagination metadata
        # Frontend expects: { items, page, page_size, total, total_pages }
        return SkillListResponse(
            items=paginated_skills,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error("list_skills_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list skills: {str(e)}",
        )


# ============================================================================
# Endpoint 2: GET /api/v1/skills/:name - Get skill details
# ============================================================================


@router.get("/registry/{skill_name}", response_model=SkillDetailResponse)
async def get_skill_detail(skill_name: str) -> SkillDetailResponse:
    """Get detailed information about a specific skill.

    Sprint 99 Feature 99.1: Skill Management APIs
    Endpoint: GET /api/v1/skills/:name

    Args:
        skill_name: Name of skill to retrieve

    Returns:
        SkillDetailResponse with full skill information

    Example:
        >>> GET /api/v1/skills/reflection
        >>> {
        ...     "name": "reflection",
        ...     "category": "reasoning",
        ...     "description": "Self-critique and validation loop",
        ...     "author": "AegisRAG Team",
        ...     "version": "1.0.0",
        ...     "status": "active",
        ...     "tags": ["validation", "quality"],
        ...     "skill_md": "# Reflection Skill\\n\\n...",
        ...     "config_yaml": "max_iterations: 3\\n...",
        ...     "tools": [],
        ...     "lifecycle": {
        ...         "state": "active",
        ...         "loaded_at": "2026-01-15T10:00:00Z",
        ...         "activated_at": "2026-01-15T10:01:00Z",
        ...         "invocation_count": 42
        ...     },
        ...     "created_at": "2026-01-15T10:00:00Z",
        ...     "updated_at": "2026-01-15T10:00:00Z"
        ... }

    Raises:
        HTTPException 404: If skill not found
        HTTPException 500: If retrieval fails
    """
    logger.info("get_skill_detail_endpoint_called", skill_name=skill_name)

    try:
        registry = get_registry()
        lifecycle = get_lifecycle()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        # Load skill to get full details
        loaded_skill = registry.load(skill_name)

        # Get lifecycle info
        skill_state = lifecycle.get_state(skill_name)
        api_status = _map_lifecycle_state_to_status(skill_state)

        # Get lifecycle events for timing info
        events = lifecycle.get_events(skill_name)
        loaded_at = None
        activated_at = None
        for event in events:
            if event.event_type == "load" and not loaded_at:
                loaded_at = event.timestamp
            if event.event_type == "activate" and not activated_at:
                activated_at = event.timestamp

        # Load config.yaml
        config_yaml = None
        config_path = loaded_skill.path / "config.yaml"
        if config_path.exists():
            config_yaml = config_path.read_text()

        # Get lifecycle info
        lifecycle_info = SkillLifecycleInfo(
            state=api_status,
            loaded_at=loaded_at,
            activated_at=activated_at,
            last_used=activated_at,  # TODO: Track real last usage
            invocation_count=0,  # TODO: Track real invocations
        )

        # Extract category
        skill_category = _extract_category(metadata.description)

        logger.info("get_skill_detail_success", skill_name=skill_name)

        return SkillDetailResponse(
            name=skill_name,
            category=skill_category,
            description=metadata.description,
            author=metadata.author,
            version=metadata.version,
            status=api_status,
            tags=metadata.triggers,
            skill_md=loaded_skill.instructions,
            config_yaml=config_yaml,
            tools=[],  # TODO: Integrate with tool authorization system
            lifecycle=lifecycle_info,
            created_at=datetime.now(),  # TODO: Get from filesystem
            updated_at=datetime.now(),  # TODO: Get from filesystem
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_skill_detail_failed", skill_name=skill_name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve skill: {str(e)}",
        )


# ============================================================================
# Endpoint 3: POST /api/v1/skills - Create new skill
# ============================================================================


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SkillCreateResponse)
async def create_skill(request: SkillCreateRequest) -> SkillCreateResponse:
    """Create a new skill.

    Sprint 99 Feature 99.1: Skill Management APIs
    Endpoint: POST /api/v1/skills

    Args:
        request: Skill creation request with name, description, skill_md, etc.

    Returns:
        SkillCreateResponse with creation status

    Example:
        >>> POST /api/v1/skills
        >>> {
        ...     "name": "custom_skill",
        ...     "category": "tools",
        ...     "description": "Custom tool integration",
        ...     "author": "User",
        ...     "version": "1.0.0",
        ...     "tags": ["custom", "tools"],
        ...     "skill_md": "# Custom Skill\\n\\nCustom skill instructions..."
        ... }
        >>>
        >>> Response:
        >>> {
        ...     "skill_name": "custom_skill",
        ...     "status": "created",
        ...     "message": "Skill created successfully",
        ...     "created_at": "2026-01-15T10:00:00Z"
        ... }

    Raises:
        HTTPException 409: If skill with same name already exists
        HTTPException 400: If validation fails
        HTTPException 500: If creation fails
    """
    logger.info("create_skill_endpoint_called", skill_name=request.name)

    try:
        registry = get_registry()

        # Check if skill already exists
        existing_metadata = registry.get_metadata(request.name)
        if existing_metadata:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Skill already exists: {request.name}",
            )

        # Create skill directory
        skill_dir = Path("skills") / request.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Create SKILL.md with frontmatter
        frontmatter = f"""---
name: {request.name}
version: {request.version}
description: {request.description}
author: {request.author}
triggers:
{chr(10).join(f"  - {tag}" for tag in request.tags)}
dependencies: []
permissions: []
---

{request.skill_md}
"""
        skill_md_path = skill_dir / "SKILL.md"
        skill_md_path.write_text(frontmatter)

        # Create config.yaml if provided
        if request.config_yaml:
            config_path = skill_dir / "config.yaml"
            config_path.write_text(request.config_yaml)

        # Re-discover skills to include new one
        registry.discover()

        logger.info("create_skill_success", skill_name=request.name, path=str(skill_dir))

        return SkillCreateResponse(
            skill_name=request.name,
            status="created",
            message="Skill created successfully",
            created_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_skill_failed", skill_name=request.name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create skill: {str(e)}",
        )


# ============================================================================
# Endpoint 4: PUT /api/v1/skills/:name - Update skill metadata
# ============================================================================


@router.put("/{skill_name}", response_model=SkillUpdateResponse)
async def update_skill(skill_name: str, request: SkillUpdateRequest) -> SkillUpdateResponse:
    """Update skill metadata (description, tags, status).

    Sprint 99 Feature 99.1: Skill Management APIs
    Endpoint: PUT /api/v1/skills/:name

    Args:
        skill_name: Name of skill to update
        request: Update request with new metadata

    Returns:
        SkillUpdateResponse with update status

    Example:
        >>> PUT /api/v1/skills/reflection
        >>> {
        ...     "description": "Updated description",
        ...     "tags": ["updated", "tags"],
        ...     "status": "active"
        ... }
        >>>
        >>> Response:
        >>> {
        ...     "skill_name": "reflection",
        ...     "status": "updated",
        ...     "message": "Skill updated successfully",
        ...     "updated_at": "2026-01-15T10:00:00Z"
        ... }

    Raises:
        HTTPException 404: If skill not found
        HTTPException 500: If update fails
    """
    logger.info("update_skill_endpoint_called", skill_name=skill_name, request=request.dict())

    try:
        registry = get_registry()
        lifecycle = get_lifecycle()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        # Load skill to get path
        loaded_skill = registry.load(skill_name)
        skill_md_path = loaded_skill.path / "SKILL.md"

        # Read current SKILL.md
        content = skill_md_path.read_text()

        # Parse frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_yaml = parts[1]
                instructions = parts[2].strip()
                frontmatter_dict = yaml.safe_load(frontmatter_yaml)

                # Update fields
                if request.description:
                    frontmatter_dict["description"] = request.description
                if request.tags is not None:
                    frontmatter_dict["triggers"] = request.tags

                # Reconstruct SKILL.md
                updated_frontmatter = yaml.dump(frontmatter_dict, sort_keys=False)
                updated_content = f"---\n{updated_frontmatter}---\n\n{instructions}"
                skill_md_path.write_text(updated_content)

        # Handle status update (lifecycle state change)
        if request.status:
            if request.status == SkillStatus.ACTIVE:
                await lifecycle.activate(skill_name)
            elif request.status == SkillStatus.INACTIVE:
                await lifecycle.deactivate(skill_name)

        # Re-discover to reload metadata
        registry.discover()

        logger.info("update_skill_success", skill_name=skill_name)

        return SkillUpdateResponse(
            skill_name=skill_name,
            status="updated",
            message="Skill updated successfully",
            updated_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_skill_failed", skill_name=skill_name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update skill: {str(e)}",
        )


# ============================================================================
# Endpoint 5: DELETE /api/v1/skills/:name - Delete skill
# ============================================================================


@router.delete("/{skill_name}", response_model=SkillDeleteResponse)
async def delete_skill(skill_name: str) -> SkillDeleteResponse:
    """Delete a skill and all its resources.

    Sprint 99 Feature 99.1: Skill Management APIs
    Endpoint: DELETE /api/v1/skills/:name

    Args:
        skill_name: Name of skill to delete

    Returns:
        SkillDeleteResponse with deletion status

    Example:
        >>> DELETE /api/v1/skills/custom_skill
        >>>
        >>> Response:
        >>> {
        ...     "skill_name": "custom_skill",
        ...     "status": "deleted",
        ...     "message": "Skill deleted successfully",
        ...     "deleted_at": "2026-01-15T10:00:00Z"
        ... }

    Raises:
        HTTPException 404: If skill not found
        HTTPException 500: If deletion fails
    """
    logger.info("delete_skill_endpoint_called", skill_name=skill_name)

    try:
        registry = get_registry()
        lifecycle = get_lifecycle()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        # Unload if loaded
        if skill_name in registry._loaded:
            await lifecycle.unload(skill_name)

        # Delete skill directory
        skill_dir = Path("skills") / skill_name
        if skill_dir.exists():
            import shutil

            shutil.rmtree(skill_dir)

        # Re-discover to update registry
        registry.discover()

        logger.info("delete_skill_success", skill_name=skill_name)

        return SkillDeleteResponse(
            skill_name=skill_name,
            status="deleted",
            message="Skill deleted successfully",
            deleted_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_skill_failed", skill_name=skill_name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete skill: {str(e)}",
        )


# ============================================================================
# Endpoint 6: GET /api/v1/skills/:name/config - Get YAML config
# ============================================================================


@router.get("/{skill_name}/config", response_model=SkillConfigResponse)
async def get_skill_config(skill_name: str) -> SkillConfigResponse:
    """Get skill YAML configuration.

    Sprint 99 Feature 99.1: Skill Management APIs
    Endpoint: GET /api/v1/skills/:name/config

    Args:
        skill_name: Name of skill

    Returns:
        SkillConfigResponse with YAML content and parsed config

    Example:
        >>> GET /api/v1/skills/reflection/config
        >>>
        >>> Response:
        >>> {
        ...     "skill_name": "reflection",
        ...     "yaml_content": "max_iterations: 3\\nconfidence_threshold: 0.85",
        ...     "parsed_config": {
        ...         "max_iterations": 3,
        ...         "confidence_threshold": 0.85
        ...     }
        ... }

    Raises:
        HTTPException 404: If skill or config not found
        HTTPException 500: If retrieval fails
    """
    logger.info("get_skill_config_endpoint_called", skill_name=skill_name)

    try:
        registry = get_registry()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        # Load skill
        loaded_skill = registry.load(skill_name)
        config_path = loaded_skill.path / "config.yaml"

        if not config_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config not found for skill: {skill_name}",
            )

        yaml_content = config_path.read_text()
        parsed_config = yaml.safe_load(yaml_content) or {}

        logger.info("get_skill_config_success", skill_name=skill_name)

        return SkillConfigResponse(
            skill_name=skill_name,
            yaml_content=yaml_content,
            parsed_config=parsed_config,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_skill_config_failed", skill_name=skill_name, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve config: {str(e)}",
        )


# ============================================================================
# Endpoint 7: PUT /api/v1/skills/:name/config - Update YAML config
# ============================================================================


@router.put("/{skill_name}/config", response_model=SkillUpdateResponse)
async def update_skill_config(
    skill_name: str, request: SkillConfigUpdateRequest
) -> SkillUpdateResponse:
    """Update skill YAML configuration.

    Sprint 99 Feature 99.1: Skill Management APIs
    Endpoint: PUT /api/v1/skills/:name/config

    Args:
        skill_name: Name of skill
        request: Config update request with YAML content

    Returns:
        SkillUpdateResponse with update status

    Example:
        >>> PUT /api/v1/skills/reflection/config
        >>> {
        ...     "yaml_content": "max_iterations: 5\\nconfidence_threshold: 0.9"
        ... }
        >>>
        >>> Response:
        >>> {
        ...     "skill_name": "reflection",
        ...     "status": "updated",
        ...     "message": "Config updated successfully",
        ...     "updated_at": "2026-01-15T10:00:00Z"
        ... }

    Raises:
        HTTPException 404: If skill not found
        HTTPException 400: If YAML validation fails
        HTTPException 500: If update fails
    """
    logger.info(
        "update_skill_config_endpoint_called",
        skill_name=skill_name,
        yaml_length=len(request.yaml_content),
    )

    try:
        registry = get_registry()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        # Validate YAML syntax
        try:
            yaml.safe_load(request.yaml_content)
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YAML syntax: {str(e)}",
            )

        # Load skill and write config
        loaded_skill = registry.load(skill_name)
        config_path = loaded_skill.path / "config.yaml"
        config_path.write_text(request.yaml_content)

        logger.info("update_skill_config_success", skill_name=skill_name)

        return SkillUpdateResponse(
            skill_name=skill_name,
            status="updated",
            message="Config updated successfully",
            updated_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "update_skill_config_failed", skill_name=skill_name, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update config: {str(e)}",
        )


# ============================================================================
# Endpoint 7.5: POST /api/v1/skills/:name/config/validate - Validate config
# ============================================================================


@router.post("/{skill_name}/config/validate", response_model=ConfigValidationResponse)
async def validate_skill_config(
    skill_name: str, request: ConfigValidationRequest
) -> ConfigValidationResponse:
    """Validate skill YAML configuration without saving.

    Sprint 100 Feature 100.8: Config Validation Endpoint
    Endpoint: POST /api/v1/skills/:name/config/validate

    Args:
        skill_name: Name of skill
        request: Config validation request with YAML content

    Returns:
        ConfigValidationResponse with validation results

    Example:
        >>> POST /api/v1/skills/reflection/config/validate
        >>> {
        ...     "yaml_content": "max_iterations: 5\\nconfidence_threshold: 0.9"
        ... }
        >>>
        >>> Response:
        >>> {
        ...     "valid": true,
        ...     "errors": [],
        ...     "warnings": []
        ... }

    Raises:
        HTTPException 404: If skill not found
    """
    logger.info(
        "validate_skill_config_endpoint_called",
        skill_name=skill_name,
        yaml_length=len(request.yaml_content),
    )

    try:
        registry = get_registry()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        errors: list[str] = []
        warnings: list[str] = []

        # Validate YAML syntax
        try:
            parsed_config = yaml.safe_load(request.yaml_content)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax: {str(e)}")
            return ConfigValidationResponse(valid=False, errors=errors, warnings=warnings)

        # Check if parsed config is a dict
        if not isinstance(parsed_config, dict):
            errors.append("Config must be a YAML dictionary/object")
            return ConfigValidationResponse(valid=False, errors=errors, warnings=warnings)

        # Check for empty config
        if not parsed_config:
            warnings.append("Config is empty - using default values")

        # Check for common config fields (non-exhaustive validation)
        # Real validation would check against skill-specific schema
        known_fields = {
            "max_iterations",
            "threshold",
            "confidence_threshold",
            "timeout",
            "max_retries",
            "temperature",
            "model",
        }
        for key in parsed_config.keys():
            if not isinstance(key, str):
                errors.append(f"Config key must be a string: {key}")
            elif key not in known_fields:
                warnings.append(f"Unknown config field: '{key}' (will be ignored if not used by skill)")

        valid = len(errors) == 0

        logger.info(
            "validate_skill_config_success",
            skill_name=skill_name,
            valid=valid,
            errors_count=len(errors),
            warnings_count=len(warnings),
        )

        return ConfigValidationResponse(valid=valid, errors=errors, warnings=warnings)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "validate_skill_config_failed",
            skill_name=skill_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate config: {str(e)}",
        )


# ============================================================================
# Endpoint 8: GET /api/v1/skills/:name/tools - List authorized tools
# ============================================================================


@router.get("/{skill_name}/tools", response_model=SkillToolsResponse)
async def get_skill_tools(skill_name: str) -> SkillToolsResponse:
    """Get list of tools authorized for a skill.

    Sprint 99 Feature 99.1: Skill Management APIs
    Endpoint: GET /api/v1/skills/:name/tools

    Args:
        skill_name: Name of skill

    Returns:
        SkillToolsResponse with list of authorized tools

    Example:
        >>> GET /api/v1/skills/research/tools
        >>>
        >>> Response:
        >>> {
        ...     "skill_name": "research",
        ...     "tools": [
        ...         {
        ...             "tool_name": "browser",
        ...             "access_level": "standard",
        ...             "permissions": ["read", "navigate"],
        ...             "authorized_at": "2026-01-15T10:00:00Z"
        ...         }
        ...     ],
        ...     "total": 1
        ... }

    Raises:
        HTTPException 404: If skill not found
        HTTPException 500: If retrieval fails
    """
    logger.info("get_skill_tools_endpoint_called", skill_name=skill_name)

    try:
        registry = get_registry()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        # TODO: Integrate with Sprint 93 Tool Composition system
        # For now, return empty list (no tool authorization system in place)
        tools = []

        logger.info("get_skill_tools_success", skill_name=skill_name, tool_count=len(tools))

        return SkillToolsResponse(
            skill_name=skill_name,
            tools=tools,
            total=len(tools),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_skill_tools_failed", skill_name=skill_name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tools: {str(e)}",
        )


# ============================================================================
# Endpoint 9: POST /api/v1/skills/:name/tools - Add tool authorization
# ============================================================================


@router.post("/{skill_name}/tools", status_code=status.HTTP_201_CREATED)
async def add_tool_authorization(
    skill_name: str, request: ToolAuthorizationRequest
) -> dict:
    """Add tool authorization for a skill.

    Sprint 99 Feature 99.1: Skill Management APIs
    Endpoint: POST /api/v1/skills/:name/tools

    Args:
        skill_name: Name of skill
        request: Tool authorization request

    Returns:
        Success response with authorization details

    Example:
        >>> POST /api/v1/skills/research/tools
        >>> {
        ...     "tool_name": "browser",
        ...     "access_level": "standard",
        ...     "permissions": ["read", "navigate"]
        ... }
        >>>
        >>> Response:
        >>> {
        ...     "skill_name": "research",
        ...     "tool_name": "browser",
        ...     "access_level": "standard",
        ...     "status": "authorized",
        ...     "message": "Tool authorized successfully",
        ...     "authorized_at": "2026-01-15T10:00:00Z"
        ... }

    Raises:
        HTTPException 404: If skill not found
        HTTPException 500: If authorization fails
    """
    logger.info(
        "add_tool_authorization_endpoint_called",
        skill_name=skill_name,
        tool_name=request.tool_name,
        access_level=request.access_level,
    )

    try:
        registry = get_registry()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        # TODO: Integrate with Sprint 93 Tool Composition system
        # For now, return success (no actual authorization system in place)

        logger.info(
            "add_tool_authorization_success",
            skill_name=skill_name,
            tool_name=request.tool_name,
        )

        return {
            "skill_name": skill_name,
            "tool_name": request.tool_name,
            "access_level": request.access_level.value,
            "status": "authorized",
            "message": "Tool authorized successfully",
            "authorized_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "add_tool_authorization_failed",
            skill_name=skill_name,
            tool_name=request.tool_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to authorize tool: {str(e)}",
        )


# ============================================================================
# Endpoint 10: POST /api/v1/skills/registry/:name/activate - Activate skill
# ============================================================================


@router.post("/registry/{skill_name}/activate", response_model=SkillActivateResponse)
async def activate_skill(skill_name: str) -> SkillActivateResponse:
    """Activate a skill (load and enable).

    Sprint 99 Bug #6 Fix: Implement activate/deactivate endpoints
    Endpoint: POST /api/v1/skills/registry/:name/activate

    Args:
        skill_name: Name of skill to activate

    Returns:
        SkillActivateResponse with activation status

    Example:
        >>> POST /api/v1/skills/registry/reflection/activate
        >>>
        >>> Response:
        >>> {
        ...     "skill_name": "reflection",
        ...     "status": "active",
        ...     "message": "Skill activated successfully",
        ...     "activated_at": "2026-01-15T19:00:00Z"
        ... }

    Raises:
        HTTPException 404: If skill not found
        HTTPException 500: If activation fails
    """
    logger.info("activate_skill_endpoint_called", skill_name=skill_name)

    try:
        registry = get_registry()
        lifecycle = get_lifecycle()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        # Load skill if not already loaded
        if skill_name not in registry._loaded:
            await lifecycle.load(skill_name)

        # Activate skill
        await lifecycle.activate(skill_name)

        logger.info("activate_skill_success", skill_name=skill_name)

        return SkillActivateResponse(
            skill_name=skill_name,
            status="active",
            message="Skill activated successfully",
            activated_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("activate_skill_failed", skill_name=skill_name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate skill: {str(e)}",
        )


# ============================================================================
# Endpoint 11: POST /api/v1/skills/registry/:name/deactivate - Deactivate skill
# ============================================================================


@router.post("/registry/{skill_name}/deactivate", response_model=SkillDeactivateResponse)
async def deactivate_skill(skill_name: str) -> SkillDeactivateResponse:
    """Deactivate a skill (unload and disable).

    Sprint 99 Bug #6 Fix: Implement activate/deactivate endpoints
    Endpoint: POST /api/v1/skills/registry/:name/deactivate

    Args:
        skill_name: Name of skill to deactivate

    Returns:
        SkillDeactivateResponse with deactivation status

    Example:
        >>> POST /api/v1/skills/registry/reflection/deactivate
        >>>
        >>> Response:
        >>> {
        ...     "skill_name": "reflection",
        ...     "status": "inactive",
        ...     "message": "Skill deactivated successfully",
        ...     "deactivated_at": "2026-01-15T19:00:00Z"
        ... }

    Raises:
        HTTPException 404: If skill not found
        HTTPException 500: If deactivation fails
    """
    logger.info("deactivate_skill_endpoint_called", skill_name=skill_name)

    try:
        registry = get_registry()
        lifecycle = get_lifecycle()

        # Check if skill exists
        metadata = registry.get_metadata(skill_name)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )

        # Unload skill if loaded
        if skill_name in registry._loaded:
            await lifecycle.unload(skill_name)

        logger.info("deactivate_skill_success", skill_name=skill_name)

        return SkillDeactivateResponse(
            skill_name=skill_name,
            status="inactive",
            message="Skill deactivated successfully",
            deactivated_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("deactivate_skill_failed", skill_name=skill_name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate skill: {str(e)}",
        )


# ============================================================================
# Helper Functions
# ============================================================================


def _map_lifecycle_state_to_status(lifecycle_state) -> SkillStatus:
    """Map SkillLifecycleManager state to API SkillStatus.

    Args:
        lifecycle_state: SkillState from lifecycle manager

    Returns:
        SkillStatus for API response
    """
    from src.agents.skills.lifecycle import SkillState

    mapping = {
        SkillState.DISCOVERED: SkillStatus.DISCOVERED,
        SkillState.LOADED: SkillStatus.LOADED,
        SkillState.ACTIVE: SkillStatus.ACTIVE,
        SkillState.UNLOADED: SkillStatus.INACTIVE,
        SkillState.ERROR: SkillStatus.ERROR,
    }
    return mapping.get(lifecycle_state, SkillStatus.DISCOVERED)


def _extract_category(description: str) -> SkillCategory:
    """Extract skill category from description.

    Args:
        description: Skill description text

    Returns:
        SkillCategory based on keywords in description
    """
    description_lower = description.lower()

    if any(kw in description_lower for kw in ["search", "find", "retrieval", "vector"]):
        return SkillCategory.RETRIEVAL
    elif any(kw in description_lower for kw in ["reason", "logic", "think", "analyze"]):
        return SkillCategory.REASONING
    elif any(kw in description_lower for kw in ["synthesis", "combine", "merge", "integrate"]):
        return SkillCategory.SYNTHESIS
    elif any(
        kw in description_lower for kw in ["validate", "verify", "check", "critique", "reflection"]
    ):
        return SkillCategory.VALIDATION
    elif any(kw in description_lower for kw in ["research", "investigate", "explore"]):
        return SkillCategory.RESEARCH
    elif any(kw in description_lower for kw in ["tool", "browser", "calculator"]):
        return SkillCategory.TOOLS
    else:
        return SkillCategory.OTHER
