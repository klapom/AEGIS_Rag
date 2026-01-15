"""Unit tests for Skill Management API endpoints.

Sprint Context:
    - Sprint 99 (2026-01-15): Feature 99.1 - Skill Management APIs (18 SP)

This module tests all 9 skill management endpoints with mocked dependencies.

Test Coverage:
    - GET /api/v1/skills (list with pagination/filtering)
    - GET /api/v1/skills/:name (get details)
    - POST /api/v1/skills (create)
    - PUT /api/v1/skills/:name (update)
    - DELETE /api/v1/skills/:name (delete)
    - GET /api/v1/skills/:name/config (get config)
    - PUT /api/v1/skills/:name/config (update config)
    - GET /api/v1/skills/:name/tools (list tools)
    - POST /api/v1/skills/:name/tools (add tool)

Based on: SPRINT_99_PLAN.md Feature 99.1

Example:
    pytest tests/unit/api/v1/sprint99/test_skills_api.py -v --cov
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
from fastapi.testclient import TestClient

from src.api.models.skill_models import (
    SkillCategory,
    SkillStatus,
    AccessLevel,
)
from src.agents.skills.registry import SkillMetadata
from src.agents.skills.lifecycle import SkillState


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_registry():
    """Mock SkillRegistry."""
    registry = MagicMock()

    # Mock available skills
    registry.discover.return_value = {
        "reflection": SkillMetadata(
            name="reflection",
            version="1.0.0",
            description="Self-critique and validation loop",
            author="AegisRAG Team",
            triggers=["validation", "quality"],
            dependencies=[],
            permissions=["read_contexts", "invoke_llm"],
        ),
        "retrieval": SkillMetadata(
            name="retrieval",
            version="1.0.0",
            description="Vector and graph retrieval skill",
            author="AegisRAG Team",
            triggers=["search", "find"],
            dependencies=[],
            permissions=["read_documents"],
        ),
    }

    # Mock get_metadata
    def get_metadata_side_effect(name):
        skills = registry.discover.return_value
        return skills.get(name)

    registry.get_metadata.side_effect = get_metadata_side_effect

    # Mock load
    def load_side_effect(name):
        loaded_skill = MagicMock()
        loaded_skill.metadata = get_metadata_side_effect(name)
        loaded_skill.path = Path(f"skills/{name}")
        loaded_skill.instructions = f"# {name.title()} Skill\n\nInstructions for {name}..."
        loaded_skill.config = {"max_iterations": 3}
        return loaded_skill

    registry.load.side_effect = load_side_effect
    registry._loaded = {}

    return registry


@pytest.fixture
def mock_lifecycle():
    """Mock SkillLifecycleManager."""
    lifecycle = MagicMock()
    lifecycle.get_state.return_value = SkillState.ACTIVE
    lifecycle.get_events.return_value = []
    lifecycle.activate = AsyncMock()
    lifecycle.deactivate = AsyncMock()
    lifecycle.unload = AsyncMock()
    return lifecycle


@pytest.fixture
def client(mock_registry, mock_lifecycle):
    """FastAPI test client with mocked dependencies."""
    with patch("src.api.v1.skills.get_registry", return_value=mock_registry):
        with patch("src.api.v1.skills.get_lifecycle", return_value=mock_lifecycle):
            from src.api.main import app
            return TestClient(app)


# ============================================================================
# Test: GET /api/v1/skills - List all skills
# ============================================================================


def test_list_skills_default(client, mock_registry):
    """Test listing skills with default pagination."""
    response = client.get("/api/v1/skills")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "page" in data
    assert "page_size" in data
    assert "total" in data
    assert "total_pages" in data

    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 2  # reflection + retrieval
    assert len(data["items"]) == 2


def test_list_skills_with_pagination(client):
    """Test pagination parameters."""
    response = client.get("/api/v1/skills?page=2&page_size=1")

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 2
    assert data["page_size"] == 1
    assert len(data["items"]) == 1  # Second page with 1 item


def test_list_skills_filter_by_status(client):
    """Test filtering by status."""
    response = client.get("/api/v1/skills?status=active")

    assert response.status_code == 200
    data = response.json()

    # All skills are active in mock
    assert len(data["items"]) == 2


def test_list_skills_filter_by_category(client):
    """Test filtering by category."""
    response = client.get("/api/v1/skills?category=validation")

    assert response.status_code == 200
    data = response.json()

    # Only reflection has "validation" in description
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "reflection"


def test_list_skills_filter_by_tags(client):
    """Test filtering by tags."""
    response = client.get("/api/v1/skills?tags=validation,quality")

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "reflection"


def test_list_skills_search(client):
    """Test full-text search."""
    response = client.get("/api/v1/skills?search=retrieval")

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "retrieval"


# ============================================================================
# Test: GET /api/v1/skills/:name - Get skill details
# ============================================================================


def test_get_skill_detail_success(client, mock_registry):
    """Test getting skill details."""
    response = client.get("/api/v1/skills/reflection")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "reflection"
    assert data["version"] == "1.0.0"
    assert data["author"] == "AegisRAG Team"
    assert "skill_md" in data
    assert "lifecycle" in data


def test_get_skill_detail_not_found(client, mock_registry):
    """Test getting non-existent skill."""
    mock_registry.get_metadata.return_value = None

    response = client.get("/api/v1/skills/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_skill_detail_with_config(client, mock_registry):
    """Test getting skill with config.yaml."""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.read_text", return_value="max_iterations: 3"):
            response = client.get("/api/v1/skills/reflection")

            assert response.status_code == 200
            data = response.json()
            assert data["config_yaml"] == "max_iterations: 3"


# ============================================================================
# Test: POST /api/v1/skills - Create new skill
# ============================================================================


def test_create_skill_success(client, mock_registry):
    """Test creating a new skill."""
    mock_registry.get_metadata.return_value = None  # Skill doesn't exist

    with patch("pathlib.Path.mkdir"):
        with patch("pathlib.Path.write_text") as mock_write:
            request_data = {
                "name": "custom_skill",
                "category": "tools",
                "description": "Custom tool integration",
                "author": "User",
                "version": "1.0.0",
                "tags": ["custom", "tools"],
                "skill_md": "# Custom Skill\n\nInstructions..."
            }

            response = client.post("/api/v1/skills", json=request_data)

            assert response.status_code == 201
            data = response.json()

            assert data["skill_name"] == "custom_skill"
            assert data["status"] == "created"
            assert "created_at" in data

            # Verify SKILL.md was written
            mock_write.assert_called()


def test_create_skill_duplicate(client, mock_registry):
    """Test creating a skill that already exists."""
    # Mock skill already exists
    mock_registry.get_metadata.return_value = SkillMetadata(
        name="reflection",
        version="1.0.0",
        description="Existing skill",
        author="AegisRAG",
        triggers=[],
    )

    request_data = {
        "name": "reflection",
        "category": "reasoning",
        "description": "Duplicate skill",
        "author": "User",
        "skill_md": "# Reflection"
    }

    response = client.post("/api/v1/skills", json=request_data)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_create_skill_invalid_name(client):
    """Test creating skill with invalid name."""
    request_data = {
        "name": "invalid-name!",  # Contains invalid characters
        "category": "tools",
        "description": "Invalid skill",
        "author": "User",
        "skill_md": "# Invalid"
    }

    response = client.post("/api/v1/skills", json=request_data)

    assert response.status_code == 422  # Validation error


# ============================================================================
# Test: PUT /api/v1/skills/:name - Update skill
# ============================================================================


def test_update_skill_success(client, mock_registry, mock_lifecycle):
    """Test updating skill metadata."""
    with patch("pathlib.Path.read_text", return_value="---\nname: reflection\n---\n\nInstructions"):
        with patch("pathlib.Path.write_text") as mock_write:
            request_data = {
                "description": "Updated description",
                "tags": ["updated", "tags"],
                "status": "active"
            }

            response = client.put("/api/v1/skills/reflection", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["skill_name"] == "reflection"
            assert data["status"] == "updated"

            # Verify activate was called
            mock_lifecycle.activate.assert_called()


def test_update_skill_not_found(client, mock_registry):
    """Test updating non-existent skill."""
    mock_registry.get_metadata.return_value = None

    request_data = {"description": "Updated"}

    response = client.put("/api/v1/skills/nonexistent", json=request_data)

    assert response.status_code == 404


# ============================================================================
# Test: DELETE /api/v1/skills/:name - Delete skill
# ============================================================================


def test_delete_skill_success(client, mock_registry, mock_lifecycle):
    """Test deleting a skill."""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("shutil.rmtree") as mock_rmtree:
            response = client.delete("/api/v1/skills/reflection")

            assert response.status_code == 200
            data = response.json()

            assert data["skill_name"] == "reflection"
            assert data["status"] == "deleted"

            # Verify directory was deleted
            mock_rmtree.assert_called()


def test_delete_skill_not_found(client, mock_registry):
    """Test deleting non-existent skill."""
    mock_registry.get_metadata.return_value = None

    response = client.delete("/api/v1/skills/nonexistent")

    assert response.status_code == 404


# ============================================================================
# Test: GET /api/v1/skills/:name/config - Get config
# ============================================================================


def test_get_skill_config_success(client, mock_registry):
    """Test getting skill config."""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.read_text", return_value="max_iterations: 3\nthreshold: 0.85"):
            response = client.get("/api/v1/skills/reflection/config")

            assert response.status_code == 200
            data = response.json()

            assert data["skill_name"] == "reflection"
            assert "yaml_content" in data
            assert "parsed_config" in data
            assert data["parsed_config"]["max_iterations"] == 3


def test_get_skill_config_not_found(client, mock_registry):
    """Test getting config for skill without config.yaml."""
    with patch("pathlib.Path.exists", return_value=False):
        response = client.get("/api/v1/skills/reflection/config")

        assert response.status_code == 404
        assert "config not found" in response.json()["detail"].lower()


# ============================================================================
# Test: PUT /api/v1/skills/:name/config - Update config
# ============================================================================


def test_update_skill_config_success(client, mock_registry):
    """Test updating skill config."""
    with patch("pathlib.Path.write_text") as mock_write:
        request_data = {
            "yaml_content": "max_iterations: 5\nthreshold: 0.9"
        }

        response = client.put("/api/v1/skills/reflection/config", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["skill_name"] == "reflection"
        assert data["status"] == "updated"

        # Verify config was written
        mock_write.assert_called()


def test_update_skill_config_invalid_yaml(client, mock_registry):
    """Test updating config with invalid YAML."""
    request_data = {
        "yaml_content": "invalid: yaml: syntax:"
    }

    response = client.put("/api/v1/skills/reflection/config", json=request_data)

    assert response.status_code == 400
    assert "invalid yaml" in response.json()["detail"].lower()


# ============================================================================
# Test: GET /api/v1/skills/:name/tools - List tools
# ============================================================================


def test_get_skill_tools_success(client, mock_registry):
    """Test getting skill tools."""
    response = client.get("/api/v1/skills/reflection/tools")

    assert response.status_code == 200
    data = response.json()

    assert data["skill_name"] == "reflection"
    assert "tools" in data
    assert "total" in data
    assert isinstance(data["tools"], list)


def test_get_skill_tools_not_found(client, mock_registry):
    """Test getting tools for non-existent skill."""
    mock_registry.get_metadata.return_value = None

    response = client.get("/api/v1/skills/nonexistent/tools")

    assert response.status_code == 404


# ============================================================================
# Test: POST /api/v1/skills/:name/tools - Add tool authorization
# ============================================================================


def test_add_tool_authorization_success(client, mock_registry):
    """Test adding tool authorization."""
    request_data = {
        "tool_name": "browser",
        "access_level": "standard",
        "permissions": ["read", "navigate"]
    }

    response = client.post("/api/v1/skills/reflection/tools", json=request_data)

    assert response.status_code == 201
    data = response.json()

    assert data["skill_name"] == "reflection"
    assert data["tool_name"] == "browser"
    assert data["access_level"] == "standard"
    assert data["status"] == "authorized"


def test_add_tool_authorization_not_found(client, mock_registry):
    """Test adding tool authorization to non-existent skill."""
    mock_registry.get_metadata.return_value = None

    request_data = {
        "tool_name": "browser",
        "access_level": "standard",
        "permissions": []
    }

    response = client.post("/api/v1/skills/nonexistent/tools", json=request_data)

    assert response.status_code == 404


# ============================================================================
# Test: Helper Functions
# ============================================================================


def test_map_lifecycle_state_to_status():
    """Test lifecycle state mapping."""
    from src.api.v1.skills import _map_lifecycle_state_to_status
    from src.agents.skills.lifecycle import SkillState
    from src.api.models.skill_models import SkillStatus

    assert _map_lifecycle_state_to_status(SkillState.ACTIVE) == SkillStatus.ACTIVE
    assert _map_lifecycle_state_to_status(SkillState.LOADED) == SkillStatus.LOADED
    assert _map_lifecycle_state_to_status(SkillState.ERROR) == SkillStatus.ERROR


def test_extract_category():
    """Test category extraction from description."""
    from src.api.v1.skills import _extract_category
    from src.api.models.skill_models import SkillCategory

    assert _extract_category("Vector search and retrieval") == SkillCategory.RETRIEVAL
    assert _extract_category("Reasoning and logic") == SkillCategory.REASONING
    assert _extract_category("Validation and critique") == SkillCategory.VALIDATION
    assert _extract_category("Browser tool integration") == SkillCategory.TOOLS
    assert _extract_category("Unknown skill type") == SkillCategory.OTHER


# ============================================================================
# Test: Error Handling
# ============================================================================


def test_list_skills_error_handling(client, mock_registry):
    """Test error handling in list_skills."""
    mock_registry.discover.side_effect = Exception("Database error")

    response = client.get("/api/v1/skills")

    assert response.status_code == 500
    assert "failed" in response.json()["detail"].lower()


def test_create_skill_validation_errors(client):
    """Test validation errors in create_skill."""
    # Missing required fields
    response = client.post("/api/v1/skills", json={})
    assert response.status_code == 422

    # Invalid version format
    request_data = {
        "name": "test",
        "category": "tools",
        "description": "Test",
        "author": "User",
        "version": "invalid",  # Should be X.Y.Z
        "skill_md": "# Test"
    }
    response = client.post("/api/v1/skills", json=request_data)
    assert response.status_code == 422


# ============================================================================
# Test: Performance & Edge Cases
# ============================================================================


def test_list_skills_empty_result(client, mock_registry):
    """Test listing when no skills available."""
    mock_registry.discover.return_value = {}

    response = client.get("/api/v1/skills")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert len(data["items"]) == 0
    assert data["total_pages"] == 1


def test_list_skills_large_page_size(client):
    """Test with page_size at maximum."""
    response = client.get("/api/v1/skills?page_size=100")

    assert response.status_code == 200
    data = response.json()

    assert data["page_size"] == 100


def test_list_skills_invalid_page_size(client):
    """Test with invalid page_size (too large)."""
    response = client.get("/api/v1/skills?page_size=500")

    # Should be rejected by validation
    assert response.status_code == 422
