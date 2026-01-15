"""Integration tests for Skill Management APIs (Feature 99.1).

Sprint 99: Backend API Integration

Tests cover full skill lifecycle:
- Create skill
- List/Get skill details
- Update configuration and status
- Manage tool authorizations
- Retrieve metrics
- Delete skill with cascade
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, UTC


class TestSkillLifecycleIntegration:
    """Full skill lifecycle integration tests."""

    def test_create_and_list_skill_flow(
        self, integration_test_client, admin_auth_headers, skill_lifecycle_data
    ):
        """Test complete skill creation and listing flow."""
        skill_create_data = {
            "name": "document_analyzer",
            "version": "1.0.0",
            "model": "qwen3:32b",
            "timeout": 30,
        }

        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.create_skill = AsyncMock(
                return_value=skill_lifecycle_data
            )
            mock_registry.return_value.list_skills = AsyncMock(
                return_value=[skill_lifecycle_data]
            )

            # Create skill
            create_response = integration_test_client.post(
                "/api/v1/skills",
                json=skill_create_data,
                headers=admin_auth_headers,
            )
            assert create_response.status_code == 201

            # List skills
            list_response = integration_test_client.get(
                "/api/v1/skills",
                headers=admin_auth_headers,
            )
            assert list_response.status_code == 200
            data = list_response.json()
            assert len(data["items"]) >= 1

    def test_get_skill_and_retrieve_config_flow(
        self, integration_test_client, admin_auth_headers, skill_lifecycle_data
    ):
        """Test retrieving skill details and its configuration."""
        skill_config = {
            "name": "document_analyzer",
            "model": "qwen3:32b",
            "timeout": 30,
        }

        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.get_skill = AsyncMock(
                return_value=skill_lifecycle_data
            )
            mock_registry.return_value.get_config = AsyncMock(
                return_value=skill_config
            )

            # Get skill details
            details_response = integration_test_client.get(
                "/api/v1/skills/document_analyzer",
                headers=admin_auth_headers,
            )
            assert details_response.status_code == 200

            # Get config
            config_response = integration_test_client.get(
                "/api/v1/skills/document_analyzer/config",
                headers=admin_auth_headers,
            )
            assert config_response.status_code == 200

    def test_update_skill_activation_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test activating and deactivating a skill."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            # Simulate activation
            mock_registry.return_value.update_skill = AsyncMock(
                return_value={"status": "active"}
            )

            activate_response = integration_test_client.put(
                "/api/v1/skills/document_analyzer",
                json={"status": "active"},
                headers=admin_auth_headers,
            )
            assert activate_response.status_code == 200

            # Simulate deactivation
            mock_registry.return_value.update_skill = AsyncMock(
                return_value={"status": "inactive"}
            )

            deactivate_response = integration_test_client.put(
                "/api/v1/skills/document_analyzer",
                json={"status": "inactive"},
                headers=admin_auth_headers,
            )
            assert deactivate_response.status_code == 200

    def test_update_and_verify_config_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test updating config and verifying changes."""
        updated_config = {
            "model": "qwen3:32b",
            "timeout": 45,
            "max_tokens": 2000,
        }

        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.update_config = AsyncMock(
                return_value=updated_config
            )
            mock_registry.return_value.get_config = AsyncMock(
                return_value=updated_config
            )

            # Update config
            update_response = integration_test_client.put(
                "/api/v1/skills/document_analyzer/config",
                json=updated_config,
                headers=admin_auth_headers,
            )
            assert update_response.status_code == 200

            # Verify update
            verify_response = integration_test_client.get(
                "/api/v1/skills/document_analyzer/config",
                headers=admin_auth_headers,
            )
            assert verify_response.status_code == 200
            assert verify_response.json()["timeout"] == 45

    def test_delete_skill_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test deleting a skill."""
        with patch(
            "src.components.skill_registry.get_skill_registry"
        ) as mock_registry:
            mock_registry.return_value.delete_skill = AsyncMock(return_value=True)

            response = integration_test_client.delete(
                "/api/v1/skills/document_analyzer",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200


class TestToolAuthorizationIntegration:
    """Tool authorization workflow integration tests."""

    def test_add_tool_authorization_flow(
        self, integration_test_client, admin_auth_headers, tool_authorization_flow_data
    ):
        """Test adding tool authorization to skill."""
        tool_auth_data = {
            "tool_id": "tool_pdf_parser",
            "access_level": "standard",
        }

        with patch(
            "src.components.tool_composition.get_tool_composer"
        ) as mock_composer:
            mock_composer.return_value.authorize_tool = AsyncMock(
                return_value=tool_auth_data
            )

            response = integration_test_client.post(
                "/api/v1/skills/document_analyzer/tools",
                json=tool_auth_data,
                headers=admin_auth_headers,
            )
            assert response.status_code == 201

    def test_list_and_manage_tools_flow(
        self, integration_test_client, admin_auth_headers, tool_authorization_flow_data
    ):
        """Test listing tools and removing authorization."""
        tools = tool_authorization_flow_data["tools"]

        with patch(
            "src.components.tool_composition.get_tool_composer"
        ) as mock_composer:
            # List tools
            mock_composer.return_value.list_tools = AsyncMock(return_value=tools)

            list_response = integration_test_client.get(
                "/api/v1/skills/document_analyzer/tools",
                headers=admin_auth_headers,
            )
            assert list_response.status_code == 200
            data = list_response.json()
            assert len(data["items"]) == 2

            # Remove tool
            mock_composer.return_value.revoke_tool = AsyncMock(return_value=True)

            remove_response = integration_test_client.delete(
                "/api/v1/skills/document_analyzer/tools/tool_pdf_parser",
                headers=admin_auth_headers,
            )
            assert remove_response.status_code == 200

    def test_concurrent_tool_updates(
        self, integration_test_client, admin_auth_headers
    ):
        """Test handling concurrent tool authorization updates."""
        with patch(
            "src.components.tool_composition.get_tool_composer"
        ) as mock_composer:
            mock_composer.return_value.authorize_tool = AsyncMock(
                return_value={"tool_id": "tool_1"}
            )

            # Simulate concurrent requests
            response1 = integration_test_client.post(
                "/api/v1/skills/skill_1/tools",
                json={"tool_id": "tool_1", "access_level": "standard"},
                headers=admin_auth_headers,
            )

            response2 = integration_test_client.post(
                "/api/v1/skills/skill_1/tools",
                json={"tool_id": "tool_2", "access_level": "elevated"},
                headers=admin_auth_headers,
            )

            assert response1.status_code == 201
            assert response2.status_code == 201


class TestSkillMetricsIntegration:
    """Skill metrics retrieval integration tests."""

    def test_get_metrics_after_skill_operations(
        self, integration_test_client, admin_auth_headers
    ):
        """Test retrieving metrics after skill operations."""
        metrics_data = {
            "invocations": 100,
            "success_rate": 0.95,
            "avg_latency_ms": 245,
        }

        with patch(
            "src.components.skill_lifecycle.get_skill_lifecycle_api"
        ) as mock_lifecycle:
            mock_lifecycle.return_value.get_metrics = AsyncMock(
                return_value=metrics_data
            )

            response = integration_test_client.get(
                "/api/v1/skills/document_analyzer/metrics",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["invocations"] == 100

    def test_get_activation_history_timeline(
        self, integration_test_client, admin_auth_headers
    ):
        """Test retrieving skill activation history."""
        history_data = {
            "events": [
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event_type": "activated",
                },
            ]
        }

        with patch(
            "src.components.skill_lifecycle.get_skill_lifecycle_api"
        ) as mock_lifecycle:
            mock_lifecycle.return_value.get_activation_history = AsyncMock(
                return_value=history_data
            )

            response = integration_test_client.get(
                "/api/v1/skills/document_analyzer/activation-history",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "events" in data


class TestSkillPermissionIntegration:
    """Skill API permission enforcement integration tests."""

    def test_unauthorized_skill_operations_rejected(
        self, integration_test_client
    ):
        """Test that unauthorized requests are rejected."""
        # No auth headers
        response = integration_test_client.get("/api/v1/skills")
        assert response.status_code == 401

    def test_insufficient_permission_operations_rejected(
        self, integration_test_client, user_auth_headers
    ):
        """Test that non-admin users cannot create skills."""
        skill_data = {"name": "skill", "model": "qwen3:32b"}

        # User token instead of admin
        response = integration_test_client.post(
            "/api/v1/skills",
            json=skill_data,
            headers=user_auth_headers,
        )
        assert response.status_code == 403
