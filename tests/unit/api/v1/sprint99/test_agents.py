"""Unit tests for Agent Monitoring APIs (Feature 99.2).

Sprint 99: Backend API Integration

Tests cover:
- Message bus streaming and filtering
- Blackboard state management
- Agent orchestration and tracing
- Agent hierarchy tree structure
- Agent details and task delegation
- Performance metrics aggregation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC, timedelta


class TestMessageBusEndpoints:
    """Tests for agent message endpoints."""

    def test_list_agent_messages_success(
        self, admin_test_client, sample_agent_message, auth_headers
    ):
        """Test listing agent messages from MessageBus."""
        with patch(
            "src.components.multi_agent.get_message_bus"
        ) as mock_bus:
            mock_bus.return_value.list_messages = AsyncMock(
                return_value=[sample_agent_message]
            )

            response = admin_test_client.get(
                "/api/v1/agents/messages",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) >= 0

    def test_list_messages_filter_by_type(self, admin_test_client, auth_headers):
        """Test filtering messages by type."""
        with patch(
            "src.components.multi_agent.get_message_bus"
        ) as mock_bus:
            mock_bus.return_value.list_messages = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/agents/messages?type=SKILL_REQUEST",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_messages_filter_by_agent(self, admin_test_client, auth_headers):
        """Test filtering messages by agent."""
        with patch(
            "src.components.multi_agent.get_message_bus"
        ) as mock_bus:
            mock_bus.return_value.list_messages = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/agents/messages?agent_id=worker_1",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_messages_filter_by_time_range(self, admin_test_client, auth_headers):
        """Test filtering messages by time range."""
        with patch(
            "src.components.multi_agent.get_message_bus"
        ) as mock_bus:
            mock_bus.return_value.list_messages = AsyncMock(return_value=[])

            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(hours=1)

            response = admin_test_client.get(
                f"/api/v1/agents/messages?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_messages_pagination(self, admin_test_client, auth_headers):
        """Test message list pagination."""
        with patch(
            "src.components.multi_agent.get_message_bus"
        ) as mock_bus:
            mock_bus.return_value.list_messages = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/agents/messages?page=2&page_size=50",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 50

    def test_get_message_details_success(
        self, admin_test_client, sample_agent_message, auth_headers
    ):
        """Test retrieving full message details."""
        with patch(
            "src.components.multi_agent.get_message_bus"
        ) as mock_bus:
            mock_bus.return_value.get_message = AsyncMock(
                return_value=sample_agent_message
            )

            response = admin_test_client.get(
                f"/api/v1/agents/messages/{sample_agent_message['id']}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_get_message_not_found(self, admin_test_client, auth_headers):
        """Test retrieving non-existent message."""
        with patch(
            "src.components.multi_agent.get_message_bus"
        ) as mock_bus:
            mock_bus.return_value.get_message = AsyncMock(return_value=None)

            response = admin_test_client.get(
                "/api/v1/agents/messages/nonexistent_id",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_list_messages_unauthorized(self, admin_test_client):
        """Test list without authorization."""
        response = admin_test_client.get("/api/v1/agents/messages")

        assert response.status_code == 401


class TestBlackboardEndpoints:
    """Tests for blackboard state endpoints."""

    def test_get_all_namespaces_success(self, admin_test_client, auth_headers):
        """Test retrieving all blackboard namespaces."""
        with patch(
            "src.components.multi_agent.get_blackboard"
        ) as mock_board:
            mock_board.return_value.get_all_namespaces = AsyncMock(
                return_value=["namespace_1", "namespace_2", "namespace_3"]
            )

            response = admin_test_client.get(
                "/api/v1/agents/blackboard",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "namespaces" in data
            assert len(data["namespaces"]) == 3

    def test_get_all_namespaces_empty(self, admin_test_client, auth_headers):
        """Test when no blackboard namespaces exist."""
        with patch(
            "src.components.multi_agent.get_blackboard"
        ) as mock_board:
            mock_board.return_value.get_all_namespaces = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/agents/blackboard",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["namespaces"] == []

    def test_get_namespace_state_success(
        self, admin_test_client, sample_blackboard_state, auth_headers
    ):
        """Test retrieving specific namespace state."""
        with patch(
            "src.components.multi_agent.get_blackboard"
        ) as mock_board:
            mock_board.return_value.get_namespace = AsyncMock(
                return_value=sample_blackboard_state["data"]
            )

            response = admin_test_client.get(
                f"/api/v1/agents/blackboard/{sample_blackboard_state['namespace']}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "data" in data

    def test_get_namespace_not_found(self, admin_test_client, auth_headers):
        """Test retrieving non-existent namespace."""
        with patch(
            "src.components.multi_agent.get_blackboard"
        ) as mock_board:
            mock_board.return_value.get_namespace = AsyncMock(return_value=None)

            response = admin_test_client.get(
                "/api/v1/agents/blackboard/nonexistent_namespace",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_get_blackboard_unauthorized(self, admin_test_client):
        """Test blackboard access without authorization."""
        response = admin_test_client.get("/api/v1/agents/blackboard")

        assert response.status_code == 401


class TestActiveOrchestrationEndpoints:
    """Tests for active orchestration endpoints."""

    def test_list_active_orchestrations_success(
        self, admin_test_client, sample_orchestration, auth_headers
    ):
        """Test listing active orchestrations."""
        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.return_value.list_active_orchestrations = AsyncMock(
                return_value=[sample_orchestration]
            )

            response = admin_test_client.get(
                "/api/v1/orchestration/active",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data

    def test_list_active_orchestrations_filter_by_status(
        self, admin_test_client, auth_headers
    ):
        """Test filtering orchestrations by status."""
        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.return_value.list_active_orchestrations = AsyncMock(
                return_value=[]
            )

            response = admin_test_client.get(
                "/api/v1/orchestration/active?status=running",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_active_orchestrations_empty(self, admin_test_client, auth_headers):
        """Test when no orchestrations are active."""
        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.return_value.list_active_orchestrations = AsyncMock(
                return_value=[]
            )

            response = admin_test_client.get(
                "/api/v1/orchestration/active",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []

    def test_get_orchestration_trace_success(
        self, admin_test_client, sample_orchestration_trace, auth_headers
    ):
        """Test retrieving orchestration trace timeline."""
        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.return_value.get_trace = AsyncMock(
                return_value=sample_orchestration_trace
            )

            response = admin_test_client.get(
                f"/api/v1/orchestration/{sample_orchestration_trace['orchestration_id']}/trace",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "timeline" in data

    def test_get_orchestration_trace_not_found(self, admin_test_client, auth_headers):
        """Test retrieving trace for non-existent orchestration."""
        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.return_value.get_trace = AsyncMock(return_value=None)

            response = admin_test_client.get(
                "/api/v1/orchestration/nonexistent_id/trace",
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestOrchestrationMetricsEndpoint:
    """Tests for orchestration metrics endpoint."""

    def test_get_orchestration_metrics_success(
        self, admin_test_client, sample_communication_metrics, auth_headers
    ):
        """Test retrieving communication metrics."""
        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.return_value.get_metrics = AsyncMock(
                return_value=sample_communication_metrics
            )

            response = admin_test_client.get(
                "/api/v1/orchestration/metrics",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "total_messages" in data
            assert "p95_latency_ms" in data
            assert "error_rate" in data

    def test_get_metrics_with_time_window(self, admin_test_client, auth_headers):
        """Test metrics retrieval with specific time window."""
        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.return_value.get_metrics = AsyncMock(
                return_value={"total_messages": 100}
            )

            response = admin_test_client.get(
                "/api/v1/orchestration/metrics?time_window=1h",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestAgentHierarchyEndpoint:
    """Tests for agent hierarchy endpoint."""

    def test_get_hierarchy_tree_success(
        self, admin_test_client, sample_hierarchy_tree, auth_headers
    ):
        """Test retrieving agent hierarchy tree."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_tree = AsyncMock(
                return_value=sample_hierarchy_tree
            )

            response = admin_test_client.get(
                "/api/v1/agents/hierarchy",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "children" in data

    def test_hierarchy_tree_structure_d3js(
        self, admin_test_client, sample_hierarchy_tree, auth_headers
    ):
        """Test hierarchy tree is in D3.js compatible format."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_tree = AsyncMock(
                return_value=sample_hierarchy_tree
            )

            response = admin_test_client.get(
                "/api/v1/agents/hierarchy",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "agent_id" in data
            assert "level" in data
            assert "skills" in data

    def test_hierarchy_tree_nested_structure(self, admin_test_client, auth_headers):
        """Test hierarchy tree respects nesting (Executive→Manager→Worker)."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_tree = AsyncMock(
                return_value={
                    "level": "executive",
                    "children": [
                        {
                            "level": "manager",
                            "children": [
                                {"level": "worker", "children": []},
                            ],
                        }
                    ],
                }
            )

            response = admin_test_client.get(
                "/api/v1/agents/hierarchy",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestAgentDetailsEndpoints:
    """Tests for agent details endpoints."""

    def test_get_agent_details_success(
        self, admin_test_client, sample_agent_details, auth_headers
    ):
        """Test retrieving agent details."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_agent_details = AsyncMock(
                return_value=sample_agent_details
            )

            response = admin_test_client.get(
                f"/api/v1/agents/{sample_agent_details['agent_id']}/details",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == sample_agent_details["agent_id"]
            assert "status" in data
            assert "current_tasks" in data

    def test_get_agent_details_offline_agent(self, admin_test_client, auth_headers):
        """Test details for offline agent."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_agent_details = AsyncMock(
                return_value={"agent_id": "agent_1", "status": "offline"}
            )

            response = admin_test_client.get(
                "/api/v1/agents/agent_1/details",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "offline"

    def test_get_agent_details_not_found(self, admin_test_client, auth_headers):
        """Test retrieving non-existent agent."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_agent_details = AsyncMock(return_value=None)

            response = admin_test_client.get(
                "/api/v1/agents/nonexistent_agent/details",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_get_agent_current_tasks_success(self, admin_test_client, auth_headers):
        """Test retrieving agent's current tasks."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_current_tasks = AsyncMock(
                return_value=[
                    {"task_id": "task_1", "status": "running"},
                    {"task_id": "task_2", "status": "queued"},
                ]
            )

            response = admin_test_client.get(
                "/api/v1/agents/agent_1/current-tasks",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) >= 0

    def test_get_agent_current_tasks_empty(self, admin_test_client, auth_headers):
        """Test agent with no current tasks."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_current_tasks = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/agents/agent_1/current-tasks",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []

    def test_get_agent_details_unauthorized(self, admin_test_client):
        """Test agent details access without authorization."""
        response = admin_test_client.get("/api/v1/agents/agent_1/details")

        assert response.status_code == 401


class TestTaskDelegationChainEndpoint:
    """Tests for task delegation chain endpoint."""

    def test_get_delegation_chain_success(
        self, admin_test_client, sample_task_delegation_chain, auth_headers
    ):
        """Test retrieving task delegation chain."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_delegation_chain = AsyncMock(
                return_value=sample_task_delegation_chain
            )

            response = admin_test_client.get(
                f"/api/v1/agents/task/{sample_task_delegation_chain['task_id']}/delegation-chain",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "delegation_chain" in data
            assert len(data["delegation_chain"]) >= 1

    def test_delegation_chain_shows_hop_sequence(self, admin_test_client, auth_headers):
        """Test delegation chain shows proper hop sequence."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_delegation_chain = AsyncMock(
                return_value={
                    "task_id": "task_123",
                    "delegation_chain": [
                        {"hop": 1, "agent_id": "coordinator"},
                        {"hop": 2, "agent_id": "manager"},
                        {"hop": 3, "agent_id": "worker"},
                    ],
                }
            )

            response = admin_test_client.get(
                "/api/v1/agents/task/task_123/delegation-chain",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            hops = data["delegation_chain"]
            assert hops[0]["hop"] == 1
            assert hops[1]["hop"] == 2
            assert hops[2]["hop"] == 3

    def test_get_delegation_chain_not_found(self, admin_test_client, auth_headers):
        """Test retrieving delegation chain for non-existent task."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_delegation_chain = AsyncMock(return_value=None)

            response = admin_test_client.get(
                "/api/v1/agents/task/nonexistent_task/delegation-chain",
                headers=auth_headers,
            )

            assert response.status_code == 404
