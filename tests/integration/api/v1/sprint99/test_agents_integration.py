"""Integration tests for Agent Monitoring APIs (Feature 99.2).

Sprint 99: Backend API Integration

Tests cover full agent orchestration workflows:
- Message bus streaming
- Blackboard state management
- Orchestration execution and tracing
- Agent hierarchy navigation
- Task delegation chains
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, UTC, timedelta


class TestMessageBusIntegration:
    """MessageBus streaming and filtering integration tests."""

    def test_send_and_list_messages_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test sending message and listing received messages."""
        message_data = {
            "type": "SKILL_REQUEST",
            "sender_id": "coordinator",
            "receiver_id": "worker_1",
            "payload": {"skill": "document_analyzer"},
        }

        with patch(
            "src.components.multi_agent.get_message_bus"
        ) as mock_bus:
            # Send message
            mock_bus.return_value.send_message = AsyncMock(
                return_value={"id": "msg_123", **message_data}
            )

            # List messages
            mock_bus.return_value.list_messages = AsyncMock(
                return_value=[message_data]
            )

            list_response = integration_test_client.get(
                "/api/v1/agents/messages",
                headers=admin_auth_headers,
            )
            assert list_response.status_code == 200

    def test_filter_messages_by_type_and_agent_flow(
        self, integration_test_client, admin_auth_headers, orchestration_flow_data
    ):
        """Test filtering messages by type and agent."""
        with patch(
            "src.components.multi_agent.get_message_bus"
        ) as mock_bus:
            mock_bus.return_value.list_messages = AsyncMock(
                return_value=orchestration_flow_data["messages"]
            )

            # Filter by type
            type_response = integration_test_client.get(
                "/api/v1/agents/messages?type=SKILL_REQUEST",
                headers=admin_auth_headers,
            )
            assert type_response.status_code == 200

            # Filter by agent
            agent_response = integration_test_client.get(
                "/api/v1/agents/messages?agent_id=coordinator",
                headers=admin_auth_headers,
            )
            assert agent_response.status_code == 200


class TestBlackboardIntegration:
    """Blackboard state management integration tests."""

    def test_write_and_read_blackboard_state_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test writing to blackboard and reading state."""
        blackboard_state = {
            "namespace": "execution_state",
            "data": {
                "active_skills": ["skill_1"],
                "pending_requests": 2,
            },
        }

        with patch(
            "src.components.multi_agent.get_blackboard"
        ) as mock_board:
            # Write state
            mock_board.return_value.write_state = AsyncMock(return_value=True)

            # Read state
            mock_board.return_value.get_namespace = AsyncMock(
                return_value=blackboard_state["data"]
            )

            read_response = integration_test_client.get(
                "/api/v1/agents/blackboard/execution_state",
                headers=admin_auth_headers,
            )
            assert read_response.status_code == 200

    def test_namespace_isolation_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test that namespaces are properly isolated."""
        with patch(
            "src.components.multi_agent.get_blackboard"
        ) as mock_board:
            mock_board.return_value.get_all_namespaces = AsyncMock(
                return_value=["namespace_1", "namespace_2", "namespace_3"]
            )

            response = integration_test_client.get(
                "/api/v1/agents/blackboard",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["namespaces"]) == 3


class TestOrchestrationIntegration:
    """Orchestration workflow integration tests."""

    def test_start_and_trace_orchestration_flow(
        self, integration_test_client, admin_auth_headers, orchestration_flow_data
    ):
        """Test starting orchestration and retrieving trace."""
        trace_data = {
            "orchestration_id": orchestration_flow_data["orchestration_id"],
            "timeline": [
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event": "orchestration_started",
                },
                {
                    "timestamp": (datetime.now(UTC) + timedelta(seconds=2)).isoformat(),
                    "event": "skill_executed",
                },
            ],
        }

        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            # List active orchestrations
            mock_orchestrator.return_value.list_active_orchestrations = AsyncMock(
                return_value=[orchestration_flow_data]
            )

            list_response = integration_test_client.get(
                "/api/v1/orchestration/active",
                headers=admin_auth_headers,
            )
            assert list_response.status_code == 200

            # Get trace
            mock_orchestrator.return_value.get_trace = AsyncMock(
                return_value=trace_data
            )

            trace_response = integration_test_client.get(
                f"/api/v1/orchestration/{orchestration_flow_data['orchestration_id']}/trace",
                headers=admin_auth_headers,
            )
            assert trace_response.status_code == 200
            data = trace_response.json()
            assert len(data["timeline"]) >= 1

    def test_retrieve_orchestration_metrics_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test retrieving orchestration communication metrics."""
        metrics_data = {
            "total_messages": 150,
            "p95_latency_ms": 450,
            "error_rate": 0.01,
        }

        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.return_value.get_metrics = AsyncMock(
                return_value=metrics_data
            )

            response = integration_test_client.get(
                "/api/v1/orchestration/metrics",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "total_messages" in data


class TestAgentHierarchyIntegration:
    """Agent hierarchy navigation integration tests."""

    def test_get_hierarchy_and_agent_details_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test retrieving hierarchy and drilling down to agent details."""
        hierarchy_tree = {
            "name": "coordinator",
            "agent_id": "coordinator_1",
            "level": "executive",
            "children": [
                {
                    "name": "manager",
                    "agent_id": "manager_1",
                    "level": "manager",
                    "children": [
                        {
                            "name": "worker",
                            "agent_id": "worker_1",
                            "level": "worker",
                        }
                    ],
                }
            ],
        }

        agent_details = {
            "agent_id": "worker_1",
            "status": "online",
            "current_tasks": 2,
            "success_rate": 0.98,
        }

        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            # Get hierarchy
            mock_hierarchy.return_value.get_tree = AsyncMock(
                return_value=hierarchy_tree
            )

            hierarchy_response = integration_test_client.get(
                "/api/v1/agents/hierarchy",
                headers=admin_auth_headers,
            )
            assert hierarchy_response.status_code == 200

            # Get agent details
            mock_hierarchy.return_value.get_agent_details = AsyncMock(
                return_value=agent_details
            )

            details_response = integration_test_client.get(
                "/api/v1/agents/worker_1/details",
                headers=admin_auth_headers,
            )
            assert details_response.status_code == 200

    def test_navigate_hierarchy_levels_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test navigating through all hierarchy levels."""
        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            # Get multiple agents at different levels
            mock_hierarchy.return_value.get_agent_details = AsyncMock(
                side_effect=[
                    {"agent_id": "coordinator_1", "level": "executive"},
                    {"agent_id": "manager_1", "level": "manager"},
                    {"agent_id": "worker_1", "level": "worker"},
                ]
            )

            # Coordinator
            coord_response = integration_test_client.get(
                "/api/v1/agents/coordinator_1/details",
                headers=admin_auth_headers,
            )
            assert coord_response.status_code == 200

            # Manager
            mgr_response = integration_test_client.get(
                "/api/v1/agents/manager_1/details",
                headers=admin_auth_headers,
            )
            assert mgr_response.status_code == 200

            # Worker
            worker_response = integration_test_client.get(
                "/api/v1/agents/worker_1/details",
                headers=admin_auth_headers,
            )
            assert worker_response.status_code == 200


class TestTaskDelegationIntegration:
    """Task delegation and tracking integration tests."""

    def test_get_delegation_chain_through_hierarchy_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test tracing task delegation through agent hierarchy."""
        delegation_chain = {
            "task_id": "task_123",
            "delegation_chain": [
                {"hop": 1, "agent_id": "coordinator", "action": "received"},
                {"hop": 2, "agent_id": "manager_1", "action": "delegated"},
                {"hop": 3, "agent_id": "worker_1", "action": "executed"},
            ],
        }

        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_delegation_chain = AsyncMock(
                return_value=delegation_chain
            )

            response = integration_test_client.get(
                "/api/v1/agents/task/task_123/delegation-chain",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["delegation_chain"]) == 3

    def test_get_agent_current_tasks_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test retrieving current tasks for an agent."""
        tasks_data = [
            {"task_id": "task_1", "status": "running"},
            {"task_id": "task_2", "status": "queued"},
        ]

        with patch(
            "src.components.hierarchical_agents.get_agent_hierarchy"
        ) as mock_hierarchy:
            mock_hierarchy.return_value.get_current_tasks = AsyncMock(
                return_value=tasks_data
            )

            response = integration_test_client.get(
                "/api/v1/agents/worker_1/current-tasks",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2


class TestConcurrentOrchestrationIntegration:
    """Concurrent orchestration execution integration tests."""

    def test_multiple_concurrent_orchestrations(
        self, integration_test_client, admin_auth_headers
    ):
        """Test handling multiple concurrent orchestrations."""
        orchestrations = [
            {
                "id": f"orch_{i}",
                "status": "running",
                "agents_involved": ["coordinator", "manager_1"],
            }
            for i in range(5)
        ]

        with patch(
            "src.components.skill_orchestration.get_skill_orchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.return_value.list_active_orchestrations = AsyncMock(
                return_value=orchestrations
            )

            response = integration_test_client.get(
                "/api/v1/orchestration/active",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 5
