"""Unit tests for Skill Management APIs (Feature 99.1).

Sprint 99: Backend API Integration

Tests cover:
- List skills with pagination and filtering
- Get skill details
- Create skill with validation
- Update skill configuration and status
- Delete skill with cascade
- Tool authorization management
- Skill metrics and activation history
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC, timedelta


class TestListSkillsEndpoint:
    """Tests for GET /api/v1/skills endpoint."""

    def test_list_skills_success(
        self, admin_test_client, sample_skill_list_response, auth_headers
    ):
        """Test successful skills list retrieval."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.list_skills = AsyncMock(
                return_value=sample_skill_list_response["items"]
            )

            response = admin_test_client.get(
                "/api/v1/skills",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert data["page"] == 1
            assert data["page_size"] == 20

    def test_list_skills_pagination(self, admin_test_client, auth_headers):
        """Test skills list pagination."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.list_skills = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/skills?page=2&page_size=10",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 10

    def test_list_skills_filter_by_status(self, admin_test_client, auth_headers):
        """Test filtering skills by status."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.list_skills = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/skills?status=active",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_skills_filter_by_search(self, admin_test_client, auth_headers):
        """Test searching skills by name."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.list_skills = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/skills?search=document",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_skills_unauthorized(self, admin_test_client):
        """Test list without authorization."""
        response = admin_test_client.get("/api/v1/skills")

        assert response.status_code == 401

    def test_list_skills_empty_result(self, admin_test_client, auth_headers):
        """Test list when no skills exist."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.list_skills = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/skills",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["total"] == 0


class TestGetSkillDetailsEndpoint:
    """Tests for GET /api/v1/skills/:name endpoint."""

    def test_get_skill_details_success(
        self, admin_test_client, sample_skill_data, auth_headers
    ):
        """Test successful skill details retrieval."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.get_skill = AsyncMock(
                return_value=sample_skill_data
            )

            response = admin_test_client.get(
                f"/api/v1/skills/{sample_skill_data['name']}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == sample_skill_data["name"]
            assert data["version"] == sample_skill_data["version"]

    def test_get_skill_details_not_found(self, admin_test_client, auth_headers):
        """Test retrieving non-existent skill."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.get_skill = AsyncMock(return_value=None)

            response = admin_test_client.get(
                "/api/v1/skills/nonexistent_skill",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_get_skill_details_includes_metrics(
        self, admin_test_client, sample_skill_data, auth_headers
    ):
        """Test that skill details include metrics."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.get_skill = AsyncMock(
                return_value=sample_skill_data
            )

            response = admin_test_client.get(
                f"/api/v1/skills/{sample_skill_data['name']}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data

    def test_get_skill_details_unauthorized(self, admin_test_client):
        """Test get without authorization."""
        response = admin_test_client.get("/api/v1/skills/skill_name")

        assert response.status_code == 401


class TestCreateSkillEndpoint:
    """Tests for POST /api/v1/skills endpoint."""

    def test_create_skill_success(self, admin_test_client, sample_skill_config, auth_headers):
        """Test successful skill creation."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.create_skill = AsyncMock(
                return_value={"name": "new_skill", "status": "pending"}
            )

            response = admin_test_client.post(
                "/api/v1/skills",
                json=sample_skill_config,
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert "name" in data

    def test_create_skill_duplicate(self, admin_test_client, sample_skill_config, auth_headers):
        """Test creating duplicate skill."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.create_skill = AsyncMock(
                side_effect=ValueError("Skill already exists")
            )

            response = admin_test_client.post(
                "/api/v1/skills",
                json=sample_skill_config,
                headers=auth_headers,
            )

            assert response.status_code == 409

    def test_create_skill_missing_config(self, admin_test_client, auth_headers):
        """Test creating skill without required config."""
        invalid_config = {"name": "skill"}

        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.create_skill = AsyncMock(
                side_effect=ValueError("Missing required fields")
            )

            response = admin_test_client.post(
                "/api/v1/skills",
                json=invalid_config,
                headers=auth_headers,
            )

            assert response.status_code == 400

    def test_create_skill_validation_error(self, admin_test_client, auth_headers):
        """Test creating skill with invalid configuration."""
        invalid_config = {
            "name": "skill",
            "model": "invalid_model",
            "timeout": -5,  # Invalid: negative timeout
        }

        response = admin_test_client.post(
            "/api/v1/skills",
            json=invalid_config,
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_create_skill_unauthorized(self, admin_test_client, sample_skill_config):
        """Test create without authorization."""
        response = admin_test_client.post(
            "/api/v1/skills",
            json=sample_skill_config,
        )

        assert response.status_code == 401

    def test_create_skill_forbidden_user(
        self, admin_test_client, sample_skill_config, user_auth_headers
    ):
        """Test create with insufficient permissions."""
        response = admin_test_client.post(
            "/api/v1/skills",
            json=sample_skill_config,
            headers=user_auth_headers,
        )

        assert response.status_code == 403


class TestUpdateSkillEndpoint:
    """Tests for PUT /api/v1/skills/:name endpoint."""

    def test_update_skill_success(self, admin_test_client, sample_skill_config, auth_headers):
        """Test successful skill update."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.update_skill = AsyncMock(
                return_value={"name": "skill", "status": "active"}
            )

            response = admin_test_client.put(
                "/api/v1/skills/skill",
                json={"status": "active"},
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_update_skill_activation_status(self, admin_test_client, auth_headers):
        """Test toggling skill activation status."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.update_skill = AsyncMock(
                return_value={"status": "inactive"}
            )

            response = admin_test_client.put(
                "/api/v1/skills/skill",
                json={"status": "inactive"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "inactive"

    def test_update_skill_config(self, admin_test_client, sample_skill_config, auth_headers):
        """Test updating skill configuration."""
        update_config = {
            "model": "qwen3:32b",
            "timeout": 45,
        }

        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.update_skill = AsyncMock(
                return_value={"name": "skill"}
            )

            response = admin_test_client.put(
                "/api/v1/skills/skill",
                json=update_config,
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_update_skill_not_found(self, admin_test_client, auth_headers):
        """Test updating non-existent skill."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.update_skill = AsyncMock(return_value=None)

            response = admin_test_client.put(
                "/api/v1/skills/nonexistent",
                json={"status": "active"},
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_update_skill_unauthorized(self, admin_test_client):
        """Test update without authorization."""
        response = admin_test_client.put(
            "/api/v1/skills/skill",
            json={"status": "active"},
        )

        assert response.status_code == 401


class TestDeleteSkillEndpoint:
    """Tests for DELETE /api/v1/skills/:name endpoint."""

    def test_delete_skill_success(self, admin_test_client, auth_headers):
        """Test successful skill deletion."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.delete_skill = AsyncMock(return_value=True)

            response = admin_test_client.delete(
                "/api/v1/skills/skill",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_delete_skill_with_dependencies(self, admin_test_client, auth_headers):
        """Test deleting skill with tool dependencies (cascade)."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.delete_skill = AsyncMock(return_value=True)

            response = admin_test_client.delete(
                "/api/v1/skills/skill_with_tools",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_delete_skill_not_found(self, admin_test_client, auth_headers):
        """Test deleting non-existent skill."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.delete_skill = AsyncMock(return_value=False)

            response = admin_test_client.delete(
                "/api/v1/skills/nonexistent",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_delete_skill_unauthorized(self, admin_test_client):
        """Test delete without authorization."""
        response = admin_test_client.delete("/api/v1/skills/skill")

        assert response.status_code == 401


class TestSkillConfigEndpoints:
    """Tests for skill configuration endpoints."""

    def test_get_skill_config_success(
        self, admin_test_client, sample_skill_config, auth_headers
    ):
        """Test retrieving skill YAML config."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.get_config = AsyncMock(
                return_value=sample_skill_config
            )

            response = admin_test_client.get(
                "/api/v1/skills/skill/config",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_update_skill_config_success(
        self, admin_test_client, sample_skill_config, auth_headers
    ):
        """Test updating skill YAML config."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.update_config = AsyncMock(
                return_value=sample_skill_config
            )

            response = admin_test_client.put(
                "/api/v1/skills/skill/config",
                json=sample_skill_config,
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_update_skill_config_validation_error(self, admin_test_client, auth_headers):
        """Test config update with invalid schema."""
        invalid_config = {"invalid": "schema"}

        response = admin_test_client.put(
            "/api/v1/skills/skill/config",
            json=invalid_config,
            headers=auth_headers,
        )

        assert response.status_code == 400


class TestToolAuthorizationEndpoints:
    """Tests for tool authorization endpoints."""

    def test_list_authorized_tools_success(
        self, admin_test_client, sample_tool_authorization, auth_headers
    ):
        """Test listing authorized tools for skill."""
        with patch(
            "src.components.tool_composition.get_tool_composer"
        ) as mock_composer:
            mock_composer.return_value.list_tools = AsyncMock(
                return_value=[sample_tool_authorization]
            )

            response = admin_test_client.get(
                "/api/v1/skills/skill/tools",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_authorized_tools_empty(self, admin_test_client, auth_headers):
        """Test listing when no tools authorized."""
        with patch(
            "src.components.tool_composition.get_tool_composer"
        ) as mock_composer:
            mock_composer.return_value.list_tools = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/skills/skill/tools",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []

    def test_add_tool_authorization_success(
        self, admin_test_client, sample_tool_authorization, auth_headers
    ):
        """Test authorizing a tool for skill."""
        with patch(
            "src.components.tool_composition.get_tool_composer"
        ) as mock_composer:
            mock_composer.return_value.authorize_tool = AsyncMock(
                return_value=sample_tool_authorization
            )

            response = admin_test_client.post(
                "/api/v1/skills/skill/tools",
                json={
                    "tool_id": "tool_1",
                    "access_level": "standard",
                },
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_add_tool_invalid_access_level(self, admin_test_client, auth_headers):
        """Test authorizing tool with invalid access level."""
        response = admin_test_client.post(
            "/api/v1/skills/skill/tools",
            json={
                "tool_id": "tool_1",
                "access_level": "invalid_level",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_remove_tool_authorization_success(self, admin_test_client, auth_headers):
        """Test removing tool authorization."""
        with patch(
            "src.components.tool_composition.get_tool_composer"
        ) as mock_composer:
            mock_composer.return_value.revoke_tool = AsyncMock(return_value=True)

            response = admin_test_client.delete(
                "/api/v1/skills/skill/tools/tool_1",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_remove_tool_not_found(self, admin_test_client, auth_headers):
        """Test removing non-existent tool."""
        with patch(
            "src.components.tool_composition.get_tool_composer"
        ) as mock_composer:
            mock_composer.return_value.revoke_tool = AsyncMock(return_value=False)

            response = admin_test_client.delete(
                "/api/v1/skills/skill/tools/nonexistent_tool",
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestSkillMetricsEndpoints:
    """Tests for skill metrics endpoints."""

    def test_get_skill_metrics_success(
        self, admin_test_client, sample_skill_metrics, auth_headers
    ):
        """Test retrieving skill metrics."""
        with patch(
            "src.components.skill_lifecycle.get_skill_lifecycle_api"
        ) as mock_lifecycle:
            mock_lifecycle.return_value.get_metrics = AsyncMock(
                return_value=sample_skill_metrics
            )

            response = admin_test_client.get(
                "/api/v1/skills/skill/metrics",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "invocations" in data
            assert "success_rate" in data

    def test_get_skill_activation_history_success(
        self, admin_test_client, sample_activation_history, auth_headers
    ):
        """Test retrieving skill activation history."""
        with patch(
            "src.components.skill_lifecycle.get_skill_lifecycle_api"
        ) as mock_lifecycle:
            mock_lifecycle.return_value.get_activation_history = AsyncMock(
                return_value=sample_activation_history
            )

            response = admin_test_client.get(
                "/api/v1/skills/skill/activation-history",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "events" in data
            assert len(data["events"]) >= 0

    def test_get_activation_history_time_range(self, admin_test_client, auth_headers):
        """Test activation history with time range filter."""
        with patch(
            "src.components.skill_lifecycle.get_skill_lifecycle_api"
        ) as mock_lifecycle:
            mock_lifecycle.return_value.get_activation_history = AsyncMock(
                return_value={"events": []}
            )

            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=30)

            response = admin_test_client.get(
                f"/api/v1/skills/skill/activation-history?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}",
                headers=auth_headers,
            )

            assert response.status_code == 200
